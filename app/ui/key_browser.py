from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.utils import format_redis_error

TYPE_BADGE_COLORS = {
    "string": "#3498db",
    "hash": "#9b59b6",
    "list": "#e67e22",
    "set": "#1abc9c",
    "zset": "#e74c3c",
}


class KeyRow(ctk.CTkFrame):
    def __init__(self, master, key: str, on_click: Callable[[str], None]):
        super().__init__(master, fg_color="transparent", corner_radius=6)
        self.key = key
        self.on_click = on_click
        self.selected = False

        self.name_label = ctk.CTkLabel(self, text=key, anchor="w", font=("Segoe UI", 12))
        self.name_label.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)
        self.type_label = ctk.CTkLabel(self, text="…", width=52, fg_color="gray30", corner_radius=8, font=("Segoe UI", 10))
        self.type_label.pack(side="right", padx=(4, 8), pady=4)

        for widget in (self, self.name_label, self.type_label):
            widget.bind("<Button-1>", lambda _e: self._click())

    def _click(self) -> None:
        self.on_click(self.key)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.configure(fg_color="gray25" if selected else "transparent")

    def set_type(self, type_name: str) -> None:
        color = TYPE_BADGE_COLORS.get(type_name, "gray40")
        self.type_label.configure(text=type_name or "?", fg_color=color)


class KeyBrowser(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, status_bar, on_select: Callable[[str], None]):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.status_bar = status_bar
        self.on_select = on_select
        self.rows: dict[str, KeyRow] = {}
        self.selected_key: str | None = None

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 6))
        self.pattern_var = ctk.StringVar(value="*")
        entry = ctk.CTkEntry(search_row, textvariable=self.pattern_var, placeholder_text="Search pattern (e.g. user:*)")
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _e: self.refresh())
        ctk.CTkButton(search_row, text="Search", width=70, command=self.refresh).pack(side="left", padx=(6, 0))

        self.count_label = ctk.CTkLabel(self, text="0 keys", text_color="gray60", anchor="w")
        self.count_label.pack(fill="x", pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(actions, text="+ New Key", fg_color="#2ecc71", hover_color="#27ae60", command=self._new_key).pack(side="left")
        ctk.CTkButton(actions, text="Delete", fg_color="#e74c3c", hover_color="#c0392b", command=self._delete_selected).pack(side="right")

        self._keys_cache: list[str] = []

    def refresh(self) -> None:
        pattern = self.pattern_var.get().strip() or "*"
        self.runner.run(self.client.scan_keys, self._on_scanned, self._on_error, pattern)

    def _on_scanned(self, keys: list) -> None:
        decoded = sorted(k.decode() if isinstance(k, bytes) else k for k in keys)
        self._keys_cache = decoded
        self.count_label.configure(text=f"{len(decoded)} keys")

        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.rows.clear()

        for key in decoded:
            row = KeyRow(self.scroll, key, on_click=self._select_key)
            row.pack(fill="x", pady=1)
            self.rows[key] = row
            self.runner.run(self.client.get_type, lambda t, k=key: self._set_type(k, t), lambda _e: None, key)

        if self.selected_key in self.rows:
            self.rows[self.selected_key].set_selected(True)
        else:
            self.selected_key = None

    def _set_type(self, key: str, type_name: str) -> None:
        row = self.rows.get(key)
        if row:
            row.set_type(type_name)

    def _select_key(self, key: str) -> None:
        if self.selected_key and self.selected_key in self.rows:
            self.rows[self.selected_key].set_selected(False)
        self.selected_key = key
        if key in self.rows:
            self.rows[key].set_selected(True)
        self.on_select(key)

    def _new_key(self) -> None:
        from tkinter.simpledialog import askstring

        name = askstring("New Key", "Key name:")
        if not name:
            return
        self.runner.run(self.client.set_string, lambda _: self._after_create(name), self._on_error, name, "")

    def _after_create(self, name: str) -> None:
        self.status_bar.set_text(f"Created '{name}'", "success")
        self.refresh()
        self.selected_key = name
        self.on_select(name)

    def _delete_selected(self) -> None:
        if not self.selected_key:
            self.status_bar.set_text("Select a key to delete.", "error")
            return
        key = self.selected_key
        self.runner.run(self.client.delete_key, lambda _: self._after_delete(key), self._on_error, key)

    def _after_delete(self, key: str) -> None:
        self.status_bar.set_text(f"Deleted '{key}'", "success")
        self.selected_key = None
        self.refresh()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
