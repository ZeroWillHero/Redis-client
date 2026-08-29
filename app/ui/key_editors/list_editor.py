from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, format_redis_error


class ListRow(ctk.CTkFrame):
    def __init__(self, master, index: int, value: str, on_click, on_remove, selected: bool):
        super().__init__(master, fg_color="gray25" if selected else "transparent")
        self.index = index
        ctk.CTkLabel(self, text=str(index), width=40, text_color="gray60").pack(side="left", padx=(4, 8))
        label = ctk.CTkLabel(self, text=value, anchor="w")
        label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self, text="✕", width=28, fg_color="transparent", border_width=1, text_color="#e74c3c",
                      command=lambda: on_remove(index)).pack(side="right", padx=4)
        for widget in (self, label):
            widget.bind("<Button-1>", lambda _e: on_click(index, value))


class ListEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, status_bar, on_change):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.status_bar = status_bar
        self.on_change = on_change
        self.selected_index: int | None = None

        ctk.CTkLabel(self, text=f"Key: {key} (List)", font=("Segoe UI", 15, "bold")).pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=320)
        self.scroll.pack(fill="both", expand=True, pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.value_var, placeholder_text="value").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Append", fg_color="#2ecc71", hover_color="#27ae60", command=self._append).pack(side="left", padx=(4, 0))
        ctk.CTkButton(row, text="Update selected", fg_color="transparent", border_width=1, command=self._update_selected).pack(side="left", padx=4)

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.lrange, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, items: list) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        for i, item in enumerate(decode_bytes(items)):
            ListRow(self.scroll, i, item, on_click=self._select_row, on_remove=self._remove_index,
                    selected=(i == self.selected_index)).pack(fill="x", pady=1)

    def _select_row(self, index: int, value: str) -> None:
        self.selected_index = index
        self.value_var.set(value)
        self.load()

    def _append(self) -> None:
        value = self.value_var.get()
        if not value:
            return
        self.runner.run(self.client.rpush, lambda _: self._on_saved(), self._on_error, self.key, value)

    def _update_selected(self) -> None:
        if self.selected_index is None:
            self.status_bar.set_text("Select a row to update.", "error")
            return
        value = self.value_var.get()
        self.runner.run(self.client.lset, lambda _: self._on_saved(), self._on_error, self.key, self.selected_index, value)

    def _remove_index(self, index: int) -> None:
        self.runner.run(self.client.lrem_index, lambda _: self._on_saved(), self._on_error, self.key, index)

    def _on_saved(self) -> None:
        self.value_var.set("")
        self.selected_index = None
        self.status_bar.set_text(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
