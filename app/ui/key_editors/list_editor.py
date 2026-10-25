from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.widgets import KeyMetaBar
from app.utils import decode_bytes, format_redis_error


class ListRow(ctk.CTkFrame):
    def __init__(self, master, index: int, value: str, on_click, on_remove, selected: bool):
        super().__init__(master, fg_color=theme.SURFACE_HOVER if selected else "transparent")
        self.index = index
        ctk.CTkLabel(self, text=str(index), width=40, text_color=theme.MUTED_FOREGROUND).pack(side="left", padx=(4, 8))
        label = ctk.CTkLabel(self, text=value, anchor="w")
        label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self, text="✕", width=28, command=lambda: on_remove(index),
                      corner_radius=theme.RADIUS_SM, **theme.ghost_button_style()).pack(side="right", padx=4)
        for widget in (self, label):
            widget.bind("<Button-1>", lambda _e: on_click(index, value))


class ListEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, toast, on_change, on_key_renamed, on_key_deleted):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.toast = toast
        self.on_change = on_change
        self.selected_index: int | None = None
        self.page_size = 100
        self.page_start = 0

        self.meta_bar = KeyMetaBar(self, client, task_runner, key, "list", toast,
                                    on_renamed=on_key_renamed, on_deleted=on_key_deleted)
        self.meta_bar.pack(fill="x", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, height=300, **theme.card_style())
        self.scroll.pack(fill="both", expand=True, pady=8)

        self.load_more_btn = ctk.CTkButton(self, text="Load more", corner_radius=theme.RADIUS_SM,
                                            command=self._load_more, **theme.ghost_button_style())

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.value_var, placeholder_text="value").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Append", corner_radius=theme.RADIUS_SM,
                      command=self._append, **theme.success_button_style()).pack(side="left", padx=(4, 0))
        ctk.CTkButton(row, text="Update selected", corner_radius=theme.RADIUS_SM,
                      command=self._update_selected, **theme.ghost_button_style()).pack(side="left", padx=4)

        self._items_cache: list = []
        self.load()

    def load(self) -> None:
        self.page_start = 0
        self.runner.run(self.client.lrange, self._on_loaded, self._on_error, self.key, 0, self.page_size - 1)

    def _load_more(self) -> None:
        next_start = self.page_start + self.page_size
        self.runner.run(self.client.lrange, self._on_more_loaded, self._on_error, self.key, next_start, next_start + self.page_size - 1)

    def _on_loaded(self, items: list) -> None:
        self._items_cache = decode_bytes(items)
        self._render()

    def _on_more_loaded(self, items: list) -> None:
        decoded = decode_bytes(items)
        if decoded:
            self._items_cache.extend(decoded)
            self.page_start += self.page_size
        self._render()

    def _render(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        for i, item in enumerate(self._items_cache):
            ListRow(self.scroll, i, item, on_click=self._select_row, on_remove=self._remove_index,
                    selected=(i == self.selected_index)).pack(fill="x", pady=1)
        self.load_more_btn.pack_forget()
        if len(self._items_cache) >= self.page_start + self.page_size:
            self.load_more_btn.pack(pady=(0, 4))

    def _select_row(self, index: int, value: str) -> None:
        self.selected_index = index
        self.value_var.set(value)
        self._render()

    def _append(self) -> None:
        value = self.value_var.get()
        if not value:
            return
        self.runner.run(self.client.rpush, lambda _: self._on_saved(), self._on_error, self.key, value)

    def _update_selected(self) -> None:
        if self.selected_index is None:
            self.toast.show("Select a row to update.", "error")
            return
        value = self.value_var.get()
        self.runner.run(self.client.lset, lambda _: self._on_saved(), self._on_error, self.key, self.selected_index, value)

    def _remove_index(self, index: int) -> None:
        self.runner.run(self.client.lrem_index, lambda _: self._on_saved(), self._on_error, self.key, index)

    def _on_saved(self) -> None:
        self.value_var.set("")
        self.selected_index = None
        self.toast.show(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
