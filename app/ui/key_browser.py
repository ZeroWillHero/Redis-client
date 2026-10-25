from __future__ import annotations

import json
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.utils import decode_bytes, format_redis_error


class KeyRow(ctk.CTkFrame):
    def __init__(self, master, key: str, on_click: Callable[[str], None], on_toggle_select: Callable[[str, bool], None]):
        super().__init__(master, fg_color="transparent", corner_radius=theme.RADIUS_SM)
        self.key = key
        self.on_click = on_click
        self.selected = False

        self.check_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text="", variable=self.check_var, width=20, checkbox_width=18, checkbox_height=18,
                         command=lambda: on_toggle_select(key, self.check_var.get())).pack(side="left", padx=(4, 0))
        self.name_label = ctk.CTkLabel(self, text=key, anchor="w", font=theme.font_body(12))
        self.name_label.pack(side="left", fill="x", expand=True, padx=(4, 4), pady=4)
        self.type_label = ctk.CTkLabel(self, text="…", width=52, fg_color=theme.SURFACE_MUTED, corner_radius=8, font=theme.font_body(10))
        self.type_label.pack(side="right", padx=(4, 8), pady=4)

        for widget in (self, self.name_label, self.type_label):
            widget.bind("<Button-1>", lambda _e: self._click())

    def _click(self) -> None:
        self.on_click(self.key)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.configure(fg_color=theme.SURFACE_HOVER if selected else "transparent")

    def set_type(self, type_name: str) -> None:
        color = theme.TYPE_BADGE_COLORS.get(type_name, theme.MUTED_FOREGROUND)
        self.type_label.configure(text=type_name or "?", fg_color=color, text_color=theme.PRIMARY_FOREGROUND)


class KeyBrowser(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, toast, spinner, on_select: Callable[[str], None]):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.toast = toast
        self.spinner = spinner
        self.on_select = on_select
        self.rows: dict[str, KeyRow] = {}
        self.selected_key: str | None = None
        self.checked_keys: set[str] = set()

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 6))
        self.pattern_var = ctk.StringVar(value="*")
        self.search_entry = ctk.CTkEntry(search_row, textvariable=self.pattern_var, placeholder_text="Search pattern (e.g. user:*)")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _e: self.refresh())
        ctk.CTkButton(search_row, text="Search", width=70, corner_radius=theme.RADIUS_SM,
                      command=self.refresh, **theme.ghost_button_style()).pack(side="left", padx=(6, 0))

        self.count_label = ctk.CTkLabel(self, text="0 keys", text_color=theme.MUTED_FOREGROUND, anchor="w")
        self.count_label.pack(fill="x", pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        bulk_row = ctk.CTkFrame(self, fg_color="transparent")
        bulk_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(bulk_row, text="Export", width=70, corner_radius=theme.RADIUS_SM,
                      command=self._export_checked, **theme.ghost_button_style()).pack(side="left")
        ctk.CTkButton(bulk_row, text="Import", width=70, corner_radius=theme.RADIUS_SM,
                      command=self._import_keys, **theme.ghost_button_style()).pack(side="left", padx=4)
        self.bulk_delete_btn = ctk.CTkButton(bulk_row, text="Delete selected (0)", corner_radius=theme.RADIUS_SM,
                                              command=self._delete_checked, **theme.destructive_button_style())
        self.bulk_delete_btn.pack(side="right")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(actions, text="+ New Key", corner_radius=theme.RADIUS_SM,
                      command=self._new_key, **theme.success_button_style()).pack(side="left", fill="x", expand=True)

        self._keys_cache: list[str] = []

    def focus_search(self) -> None:
        self.search_entry.focus_set()

    def refresh(self) -> None:
        pattern = self.pattern_var.get().strip() or "*"
        start, stop = self._busy()
        self.runner.run(self.client.scan_keys, self._on_scanned, self._on_error, pattern, on_start=start, on_done=stop)

    def _busy(self):
        from app.ui.widgets import busy_scope
        return busy_scope([self.search_entry], self.spinner)

    def _on_scanned(self, keys: list) -> None:
        decoded = sorted(k.decode() if isinstance(k, bytes) else k for k in keys)
        self._keys_cache = decoded
        self.count_label.configure(text=f"{len(decoded)} keys")

        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.rows.clear()
        self.checked_keys &= set(decoded)

        for key in decoded:
            row = KeyRow(self.scroll, key, on_click=self._select_key, on_toggle_select=self._toggle_checked)
            row.pack(fill="x", pady=1)
            self.rows[key] = row
            if key in self.checked_keys:
                row.check_var.set(True)
            self.runner.run(self.client.get_type, lambda t, k=key: self._set_type(k, t), lambda _e: None, key)

        if self.selected_key in self.rows:
            self.rows[self.selected_key].set_selected(True)
        else:
            self.selected_key = None
        self._update_bulk_button()

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

    def _toggle_checked(self, key: str, checked: bool) -> None:
        if checked:
            self.checked_keys.add(key)
        else:
            self.checked_keys.discard(key)
        self._update_bulk_button()

    def _update_bulk_button(self) -> None:
        self.bulk_delete_btn.configure(text=f"Delete selected ({len(self.checked_keys)})")

    def _new_key(self) -> None:
        from tkinter.simpledialog import askstring

        name = askstring("New Key", "Key name:")
        if not name:
            return
        self.runner.run(self.client.set_string, lambda _: self._after_create(name), self._on_error, name, "")

    def _after_create(self, name: str) -> None:
        self.toast.show(f"Created '{name}'", "success")
        self.refresh()
        self.selected_key = name
        self.on_select(name)

    def _delete_checked(self) -> None:
        if not self.checked_keys:
            self.toast.show("Select one or more keys first.", "error")
            return
        keys = list(self.checked_keys)
        remaining = len(keys)

        def after_one(_result=None):
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                self.toast.show(f"Deleted {len(keys)} key(s).", "success")
                self.checked_keys.clear()
                self.selected_key = None
                self.refresh()

        for key in keys:
            self.runner.run(self.client.delete_key, after_one, lambda e: (self._on_error(e), after_one()), key)

    def _export_checked(self) -> None:
        keys = list(self.checked_keys) or ([self.selected_key] if self.selected_key else [])
        if not keys:
            self.toast.show("Select one or more keys to export.", "error")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        remaining = len(keys)
        results: dict[str, dict] = {}

        def collect(key, ttl):
            def on_type(type_name):
                loaders = {
                    "string": self.client.get_string,
                    "hash": self.client.hgetall,
                    "list": self.client.lrange,
                    "set": self.client.smembers,
                    "zset": self.client.zrange_withscores,
                }
                loader = loaders.get(type_name)
                if loader is None:
                    finish(key, {"type": type_name, "ttl": ttl, "value": None})
                    return
                self.runner.run(loader, lambda v: finish(key, {"type": type_name, "ttl": ttl, "value": decode_bytes(v)}), self._on_error, key)
            self.runner.run(self.client.get_type, on_type, self._on_error, key)

        def finish(key, data):
            nonlocal remaining
            results[key] = data
            remaining -= 1
            if remaining <= 0:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, default=str)
                self.toast.show(f"Exported {len(results)} key(s) to {path}", "success")

        for key in keys:
            self.runner.run(self.client.get_ttl, lambda ttl, k=key: collect(k, ttl), self._on_error, key)

    def _import_keys(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            self.toast.show(f"Could not read import file: {exc}", "error")
            return

        writers = {
            "string": lambda k, v: self.client.set_string(k, v or ""),
            "hash": lambda k, v: [self.client.hset(k, fk, fv) for fk, fv in (v or {}).items()],
            "list": lambda k, v: [self.client.rpush(k, item) for item in (v or [])],
            "set": lambda k, v: [self.client.sadd(k, item) for item in (v or [])],
            "zset": lambda k, v: [self.client.zadd(k, m, s) for m, s in (v or [])],
        }

        def do_import():
            count = 0
            for key, entry in data.items():
                writer = writers.get(entry.get("type"))
                if writer is None:
                    continue
                writer(key, entry.get("value"))
                ttl = entry.get("ttl")
                if ttl and ttl > 0:
                    self.client.set_ttl(key, ttl)
                count += 1
            return count

        start, stop = self._busy()
        self.runner.run(do_import, lambda count: (self.toast.show(f"Imported {count} key(s).", "success"), self.refresh()),
                         self._on_error, on_start=start, on_done=stop)

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
