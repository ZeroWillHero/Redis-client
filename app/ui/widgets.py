"""Shared modern widgets: toolbar, status bar, busy spinner, toast notifications."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import theme

STATUS_COLORS = theme.STATUS_COLORS


class Toolbar(ctk.CTkFrame):
    def __init__(self, master, on_refresh, on_theme_toggle):
        super().__init__(master, corner_radius=0, height=52, fg_color=theme.SURFACE)
        self.grid_propagate(False)

        self.status_dot = ctk.CTkLabel(self, text="●", text_color=theme.DESTRUCTIVE, font=theme.font_body(16))
        self.status_dot.pack(side="left", padx=(16, 4), pady=10)
        self.status_label = ctk.CTkLabel(self, text="Not connected", font=theme.font_body(13, "bold"))
        self.status_label.pack(side="left")

        self.spinner = Spinner(self, width=90)
        self.spinner.pack(side="left", padx=(16, 0))

        self.theme_btn = ctk.CTkButton(
            self, text="◐ Theme", width=90, command=on_theme_toggle, corner_radius=theme.RADIUS_SM,
            **theme.ghost_button_style(),
        )
        self.theme_btn.pack(side="right", padx=(4, 16), pady=10)
        self.refresh_btn = ctk.CTkButton(
            self, text="⟳ Refresh", width=100, command=on_refresh, corner_radius=theme.RADIUS_SM,
            **theme.ghost_button_style(),
        )
        self.refresh_btn.pack(side="right", padx=4, pady=10)

    def set_connected(self, name: str | None) -> None:
        if name:
            self.status_dot.configure(text_color=theme.SUCCESS)
            self.status_label.configure(text=f"Connected: {name}")
        else:
            self.status_dot.configure(text_color=theme.DESTRUCTIVE)
            self.status_label.configure(text="Not connected")


class StatusBar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0, height=32, fg_color=theme.SURFACE)
        self.grid_propagate(False)
        self.label = ctk.CTkLabel(self, text="Ready", anchor="w", text_color=STATUS_COLORS["info"])
        self.label.pack(side="left", fill="x", expand=True, padx=12, pady=4)

    def set_text(self, text: str, kind: str = "info") -> None:
        self.label.configure(text=text, text_color=STATUS_COLORS.get(kind, theme.MUTED_FOREGROUND))


class Spinner(ctk.CTkFrame):
    """A small indeterminate busy indicator, hidden until start() is called."""

    def __init__(self, master, width: int = 80):
        super().__init__(master, fg_color="transparent")
        self._bar = ctk.CTkProgressBar(self, mode="indeterminate", width=width)
        self._label = ctk.CTkLabel(self, text="Working…", text_color=theme.MUTED_FOREGROUND, font=theme.font_body(11))
        self._visible = False

    def start(self) -> None:
        if self._visible:
            return
        self._visible = True
        self._label.pack(side="left", padx=(0, 6))
        self._bar.pack(side="left")
        self._bar.start()

    def stop(self) -> None:
        if not self._visible:
            return
        self._visible = False
        self._bar.stop()
        self._bar.pack_forget()
        self._label.pack_forget()


def busy_scope(widgets: list, spinner: Spinner | None = None) -> tuple[Callable[[], None], Callable[[], None]]:
    """Returns (start, stop) callables that disable the given widgets and toggle a spinner
    while a TaskRunner call is in flight, guarding against double-submits."""
    originals: dict = {}

    def start() -> None:
        for w in widgets:
            try:
                originals[id(w)] = w.cget("state")
                w.configure(state="disabled")
            except Exception:
                pass
        if spinner:
            spinner.start()

    def stop() -> None:
        for w in widgets:
            try:
                w.configure(state=originals.get(id(w), "normal"))
            except Exception:
                pass
        if spinner:
            spinner.stop()

    return start, stop


class Toast(ctk.CTkFrame):
    _ACCENT = {
        "error": theme.DESTRUCTIVE,
        "success": theme.SUCCESS,
        "info": theme.PRIMARY,
    }

    def __init__(self, master, message: str, kind: str, on_close: Callable[["Toast"], None]):
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_MD, border_width=1, border_color=theme.BORDER)
        accent = self._ACCENT.get(kind, theme.PRIMARY)
        bar = ctk.CTkFrame(self, fg_color=accent, width=4, corner_radius=0)
        bar.pack(side="left", fill="y")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(10, 4), pady=8)
        ctk.CTkLabel(
            body, text=message, anchor="w", justify="left", wraplength=280,
            text_color=theme.FOREGROUND, font=theme.font_body(12),
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            self, text="✕", width=24, height=24, fg_color="transparent", hover_color=theme.SURFACE_HOVER,
            text_color=theme.MUTED_FOREGROUND, command=lambda: on_close(self),
        ).pack(side="right", padx=6, pady=6)


class KeyMetaBar(ctk.CTkFrame):
    """Shared header for type editors: key name, type badge, TTL editor, memory usage,
    rename/duplicate/delete actions. Centralizes key-management essentials so every
    editor gets them for free."""

    def __init__(self, master, client, runner, key: str, type_name: str, toast: "ToastManager",
                 on_renamed: Callable[[str], None], on_deleted: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = runner
        self.key = key
        self.toast = toast
        self.on_renamed = on_renamed
        self.on_deleted = on_deleted

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=key, font=theme.font_heading(15)).pack(side="left")
        badge_color = theme.TYPE_BADGE_COLORS.get(type_name, theme.MUTED_FOREGROUND)
        ctk.CTkLabel(top, text=type_name, fg_color=badge_color, text_color=theme.PRIMARY_FOREGROUND,
                     corner_radius=theme.RADIUS_SM, font=theme.font_body(10), width=56).pack(side="left", padx=(8, 0))
        self.memory_label = ctk.CTkLabel(top, text="", text_color=theme.MUTED_FOREGROUND, font=theme.font_body(11))
        self.memory_label.pack(side="right")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(actions, text="TTL (s, -1=none):", text_color=theme.MUTED_FOREGROUND, font=theme.font_body(11)).pack(side="left")
        self.ttl_var = ctk.StringVar(value="-1")
        ctk.CTkEntry(actions, textvariable=self.ttl_var, width=80).pack(side="left", padx=(6, 4))
        ctk.CTkButton(actions, text="Set TTL", width=80, corner_radius=theme.RADIUS_SM,
                      command=self._set_ttl, **theme.ghost_button_style()).pack(side="left", padx=(0, 12))
        ctk.CTkButton(actions, text="Rename", width=80, corner_radius=theme.RADIUS_SM,
                      command=self._rename, **theme.ghost_button_style()).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Duplicate", width=80, corner_radius=theme.RADIUS_SM,
                      command=self._duplicate, **theme.ghost_button_style()).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Delete", width=80, corner_radius=theme.RADIUS_SM,
                      command=self._delete, **theme.destructive_button_style()).pack(side="right")

        self._load_meta()

    def _load_meta(self) -> None:
        self.runner.run(self.client.get_ttl, self._on_ttl_loaded, lambda _e: None, self.key)
        self.runner.run(self.client.memory_usage, self._on_memory_loaded, lambda _e: None, self.key)

    def _on_ttl_loaded(self, ttl: int) -> None:
        self.ttl_var.set(str(ttl))

    def _on_memory_loaded(self, size: int | None) -> None:
        if size is not None:
            from app.utils import human_bytes
            self.memory_label.configure(text=human_bytes(size))

    def _set_ttl(self) -> None:
        try:
            seconds = int(self.ttl_var.get())
        except ValueError:
            self.toast.show("TTL must be a whole number of seconds.", "error")
            return
        self.runner.run(self.client.set_ttl, lambda _: self.toast.show("TTL updated.", "success"), self._on_error, self.key, seconds)

    def _rename(self) -> None:
        from tkinter.simpledialog import askstring
        new_name = askstring("Rename Key", "New key name:", initialvalue=self.key)
        if not new_name or new_name == self.key:
            return
        self.runner.run(self.client.rename_key, lambda _: self._on_renamed(new_name), self._on_error, self.key, new_name)

    def _on_renamed(self, new_name: str) -> None:
        self.toast.show(f"Renamed to '{new_name}'.", "success")
        self.on_renamed(new_name)

    def _duplicate(self) -> None:
        from tkinter.simpledialog import askstring
        new_name = askstring("Duplicate Key", "New key name:", initialvalue=f"{self.key}_copy")
        if not new_name:
            return
        self.runner.run(self.client.copy_key, lambda ok: self._on_duplicated(ok, new_name), self._on_error, self.key, new_name)

    def _on_duplicated(self, ok: bool, new_name: str) -> None:
        if ok:
            self.toast.show(f"Duplicated to '{new_name}'.", "success")
            self.on_renamed(self.key)  # refresh browser, keep current key open
        else:
            self.toast.show(f"'{new_name}' already exists.", "error")

    def _delete(self) -> None:
        self.runner.run(self.client.delete_key, lambda _: self._on_deleted(), self._on_error, self.key)

    def _on_deleted(self) -> None:
        self.toast.show(f"Deleted '{self.key}'.", "success")
        self.on_deleted()

    def _on_error(self, exc: Exception) -> None:
        from app.utils import format_redis_error
        self.toast.show(format_redis_error(exc), "error")


class ToastManager(ctk.CTkFrame):
    """Stacking, auto-dismissing notifications anchored to the bottom-right of the window."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-44)
        self._toasts: list[Toast] = []

    def show(self, message: str, kind: str = "info", duration_ms: int = 5000) -> None:
        toast = Toast(self, message, kind, on_close=self._dismiss)
        toast.pack(fill="x", pady=(0, 6), ipady=2)
        toast.pack_configure(anchor="e")
        self._toasts.append(toast)
        self.after(duration_ms, lambda: self._dismiss(toast))

    def _dismiss(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            toast.destroy()
