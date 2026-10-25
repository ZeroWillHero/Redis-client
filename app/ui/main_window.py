from __future__ import annotations

import customtkinter as ctk

from app.config import APP_NAME, APPEARANCE_DARK, COLOR_THEME
from app.connection_manager import ConnectionManager, ConnectionProfile
from app.redis_client import RedisClient, TaskRunner
from app.settings import load_settings
from app.utils import format_redis_error
from app.ui import theme
from app.ui.widgets import Toolbar, StatusBar, ToastManager, busy_scope
from app.ui.connection_dialog import ConnectionDialog
from app.ui.key_browser import KeyBrowser
from app.ui.console_tab import ConsoleTab
from app.ui.server_info_tab import ServerInfoTab
from app.ui.key_editors.string_editor import StringEditor
from app.ui.key_editors.hash_editor import HashEditor
from app.ui.key_editors.list_editor import ListEditor
from app.ui.key_editors.set_editor import SetEditor
from app.ui.key_editors.zset_editor import ZSetEditor
from app.ui.key_editors.stream_editor import StreamEditor

TYPE_EDITORS = {
    "string": StringEditor,
    "hash": HashEditor,
    "list": ListEditor,
    "set": SetEditor,
    "zset": ZSetEditor,
    "stream": StreamEditor,
}

_settings = load_settings()
_initial_mode = _settings.get("appearance_mode", "light")
ctk.set_appearance_mode(_initial_mode)
ctk.set_default_color_theme(COLOR_THEME)


class ConnectionRow(ctk.CTkFrame):
    def __init__(self, master, profile: ConnectionProfile, on_click, on_context_menu):
        super().__init__(master, fg_color="transparent", corner_radius=theme.RADIUS_SM)
        self.profile = profile
        self.on_click = on_click
        label = ctk.CTkLabel(
            self, text=f"{profile.name}\n{profile.host}:{profile.port}", anchor="w", justify="left", font=theme.font_body(12)
        )
        label.pack(fill="x", padx=8, pady=6)
        for widget in (self, label):
            widget.bind("<Button-1>", lambda _e: on_click(profile.id))
            widget.bind("<Double-Button-1>", lambda _e: on_click(profile.id, connect=True))
            widget.bind("<Button-2>", lambda e: on_context_menu(e, profile.id))
            widget.bind("<Button-3>", lambda e: on_context_menu(e, profile.id))

    def set_selected(self, selected: bool) -> None:
        self.configure(fg_color=theme.SURFACE_HOVER if selected else "transparent")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1280x800")
        self.configure(fg_color=theme.BACKGROUND)
        self._dark = _initial_mode == APPEARANCE_DARK

        self.conn_manager = ConnectionManager()
        self.client: RedisClient | None = None
        self.runner = TaskRunner(self)
        self.active_key: str | None = None
        self.selected_conn_id: str | None = None
        self.conn_rows: dict[str, ConnectionRow] = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.toolbar = Toolbar(self, on_refresh=self._refresh_all, on_theme_toggle=self._toggle_theme)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color=theme.SURFACE)
        self.sidebar.grid(row=1, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        self.main_pane = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_pane.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)

        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.toast_manager = ToastManager(self)

        self._build_sidebar_connections()
        self.key_browser_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.key_browser = None

        self._build_main_tabs_placeholder()
        self._bind_shortcuts()
        self._ping_loop()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Keyboard shortcuts ----------
    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-k>", lambda _e: self._focus_key_search())
        self.bind_all("<Control-d>", lambda _e: self._toggle_theme())
        self.bind_all("<Control-r>", lambda _e: self._refresh_all())

    def _focus_key_search(self) -> None:
        if self.key_browser:
            self.key_browser.focus_search()

    # ---------- Connection health ----------
    def _ping_loop(self) -> None:
        if self.client:
            self.runner.run(self.client.ping, lambda _ok: None, lambda _e: self._on_connect_error(_e, silent=True))
        self.after(15000, self._ping_loop)

    # ---------- Sidebar: connection list ----------
    def _build_sidebar_connections(self) -> None:
        pad = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        pad.pack(fill="x", padx=12, pady=(12, 0))

        header = ctk.CTkFrame(pad, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Connections", font=theme.font_heading(14)).pack(side="left")
        ctk.CTkButton(header, text="+", width=28, corner_radius=theme.RADIUS_SM,
                      command=self._add_connection, **theme.primary_button_style()).pack(side="right")

        self.conn_scroll = ctk.CTkScrollableFrame(pad, fg_color="transparent", height=140)
        self.conn_scroll.pack(fill="x", pady=(8, 8))
        self._reload_connection_list()

        btn_row = ctk.CTkFrame(pad, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 12))
        self.connect_btn = ctk.CTkButton(btn_row, text="Connect", corner_radius=theme.RADIUS_SM,
                                          command=self._connect_selected, **theme.primary_button_style())
        self.connect_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(btn_row, text="Edit", width=60, corner_radius=theme.RADIUS_SM,
                      command=self._edit_selected, **theme.ghost_button_style()).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Del", width=50, corner_radius=theme.RADIUS_SM,
                      command=self._delete_selected_conn, **theme.destructive_button_style()).pack(side="left")

        self._sidebar_content_pad = pad

    def _reload_connection_list(self) -> None:
        for child in self.conn_scroll.winfo_children():
            child.destroy()
        self.conn_rows.clear()
        for profile in self.conn_manager.list_profiles():
            row = ConnectionRow(self.conn_scroll, profile, on_click=self._on_conn_row_click, on_context_menu=self._show_conn_context_menu)
            row.pack(fill="x", pady=1)
            self.conn_rows[profile.id] = row
        if self.selected_conn_id in self.conn_rows:
            self.conn_rows[self.selected_conn_id].set_selected(True)

    def _on_conn_row_click(self, profile_id: str, connect: bool = False) -> None:
        if self.selected_conn_id and self.selected_conn_id in self.conn_rows:
            self.conn_rows[self.selected_conn_id].set_selected(False)
        self.selected_conn_id = profile_id
        if profile_id in self.conn_rows:
            self.conn_rows[profile_id].set_selected(True)
        if connect:
            self._connect_selected()

    def _selected_profile(self) -> ConnectionProfile | None:
        if not self.selected_conn_id:
            return None
        return self.conn_manager.get(self.selected_conn_id)

    def _add_connection(self) -> None:
        ConnectionDialog(self, on_save=self._on_profile_saved)

    def _edit_selected(self) -> None:
        profile = self._selected_profile()
        if not profile:
            self.toast_manager.show("Select a connection to edit.", "error")
            return
        ConnectionDialog(self, on_save=self._on_profile_saved, profile=profile)

    def _on_profile_saved(self, profile: ConnectionProfile) -> None:
        if self.conn_manager.get(profile.id):
            self.conn_manager.update(profile)
        else:
            self.conn_manager.add(profile)
        self._reload_connection_list()

    def _delete_selected_conn(self) -> None:
        profile = self._selected_profile()
        if not profile:
            return
        self.conn_manager.delete(profile.id)
        self.selected_conn_id = None
        self._reload_connection_list()

    def _show_conn_context_menu(self, event, profile_id: str) -> None:
        import tkinter as tk

        self._on_conn_row_click(profile_id)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Connect", command=self._connect_selected)
        menu.add_command(label="Edit", command=self._edit_selected)
        menu.add_command(label="Duplicate", command=self._duplicate_selected)
        menu.add_command(label="Delete", command=self._delete_selected_conn)
        menu.tk_popup(event.x_root, event.y_root)

    def _duplicate_selected(self) -> None:
        profile = self._selected_profile()
        if not profile:
            return
        self.conn_manager.duplicate(profile.id)
        self._reload_connection_list()

    def _connect_selected(self) -> None:
        profile = self._selected_profile()
        if not profile:
            self.toast_manager.show("Select a connection first.", "error")
            return
        if self.client:
            self.client.close()
            self.runner = TaskRunner(self)
        self.client = RedisClient(profile)
        start, stop = busy_scope([self.connect_btn], self.toolbar.spinner)
        self.runner.run(
            self.client.ping, lambda _ok: self._on_connected(profile), self._on_connect_error,
            on_start=start, on_done=stop,
        )

    def _on_connected(self, profile: ConnectionProfile) -> None:
        self.toolbar.set_connected(profile.name)
        self.toast_manager.show(f"Connected to {profile.host}:{profile.port}", "success")
        self._build_key_browser()
        self._build_main_tabs()

    def _on_connect_error(self, exc: Exception, silent: bool = False) -> None:
        self.toolbar.set_connected(None)
        if not silent:
            self.toast_manager.show(format_redis_error(exc), "error")
        self.client = None

    # ---------- Sidebar: key browser ----------
    def _build_key_browser(self) -> None:
        if self.key_browser is not None:
            self.key_browser_frame.destroy()
        self.key_browser_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.key_browser_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.key_browser = KeyBrowser(
            self.key_browser_frame, self.client, self.runner, self.toast_manager,
            self.toolbar.spinner, on_select=self._on_key_selected,
        )
        self.key_browser.pack(fill="both", expand=True)
        self.key_browser.refresh()

    # ---------- Main pane: tabs ----------
    def _build_main_tabs_placeholder(self) -> None:
        ctk.CTkLabel(
            self.main_pane,
            text="Add or select a connection to get started.",
            font=theme.font_body(14),
            text_color=theme.MUTED_FOREGROUND,
        ).pack(expand=True)

    def _build_main_tabs(self) -> None:
        for child in self.main_pane.winfo_children():
            child.destroy()

        self.tabview = ctk.CTkTabview(self.main_pane, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_LG)
        self.tabview.pack(fill="both", expand=True)
        self.data_tab = self.tabview.add("Data")
        self.tabview.add("Console")
        self.tabview.add("Server Info")

        ctk.CTkLabel(self.data_tab, text="Select a key from the browser to view/edit it.", text_color=theme.MUTED_FOREGROUND).pack(pady=20)

        console_container = self.tabview.tab("Console")
        self.console_tab = ConsoleTab(console_container, self.client, self.runner, self.toast_manager)
        self.console_tab.pack(fill="both", expand=True)

        info_container = self.tabview.tab("Server Info")
        self.info_tab = ServerInfoTab(info_container, self.client, self.runner, self.toast_manager)
        self.info_tab.pack(fill="both", expand=True)

    def _on_key_selected(self, key: str) -> None:
        self.active_key = key
        for child in self.data_tab.winfo_children():
            child.destroy()
        self.runner.run(self.client.get_type, lambda t: self._render_editor(key, t), self._on_editor_error, key)
        self.tabview.set("Data")

    def _render_editor(self, key: str, type_name: str) -> None:
        editor_cls = TYPE_EDITORS.get(type_name)
        if editor_cls is None:
            ctk.CTkLabel(self.data_tab, text=f"Type '{type_name}' is not yet supported for editing.", text_color=theme.MUTED_FOREGROUND).pack(pady=20)
            return
        editor = editor_cls(
            self.data_tab, self.client, self.runner, key, self.toast_manager,
            on_change=self._on_data_changed, on_key_renamed=self._on_key_renamed, on_key_deleted=self._on_key_deleted,
        )
        editor.pack(fill="both", expand=True)

    def _on_editor_error(self, exc: Exception) -> None:
        self.toast_manager.show(format_redis_error(exc), "error")

    def _on_data_changed(self) -> None:
        if self.key_browser:
            self.key_browser.refresh()

    def _on_key_renamed(self, new_name: str) -> None:
        self.active_key = new_name
        if self.key_browser:
            self.key_browser.refresh()
        self._on_key_selected(new_name)

    def _on_key_deleted(self) -> None:
        self.active_key = None
        for child in self.data_tab.winfo_children():
            child.destroy()
        ctk.CTkLabel(self.data_tab, text="Select a key from the browser to view/edit it.", text_color=theme.MUTED_FOREGROUND).pack(pady=20)
        if self.key_browser:
            self.key_browser.refresh()

    def _refresh_all(self) -> None:
        if not self.client:
            self.toast_manager.show("Not connected.", "error")
            return
        if self.key_browser:
            self.key_browser.refresh()
        if hasattr(self, "info_tab"):
            self.info_tab.load()
        if self.active_key:
            self._on_key_selected(self.active_key)

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        theme.apply_appearance_mode(APPEARANCE_DARK if self._dark else "light")

    def _on_close(self) -> None:
        if self.client:
            self.client.close()
        self.runner.shutdown()
        self.destroy()
