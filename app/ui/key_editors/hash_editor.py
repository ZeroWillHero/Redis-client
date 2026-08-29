from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, format_redis_error


class HashRow(ctk.CTkFrame):
    def __init__(self, master, field_name: str, value: str, on_delete):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=field_name, anchor="w", font=("Segoe UI", 11, "bold"), width=140).pack(side="left", padx=(4, 8))
        ctk.CTkLabel(self, text=value, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self, text="✕", width=28, fg_color="transparent", border_width=1, text_color="#e74c3c",
                      command=lambda: on_delete(field_name)).pack(side="right", padx=4)


class HashEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, status_bar, on_change):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.status_bar = status_bar
        self.on_change = on_change

        ctk.CTkLabel(self, text=f"Key: {key} (Hash)", font=("Segoe UI", 15, "bold")).pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=340)
        self.scroll.pack(fill="both", expand=True, pady=8)

        add_row = ctk.CTkFrame(self, fg_color="transparent")
        add_row.pack(fill="x", pady=4)
        self.field_var = ctk.StringVar()
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self.field_var, placeholder_text="field", width=160).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(add_row, textvariable=self.value_var, placeholder_text="value").pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(add_row, text="Add / Update", fg_color="#2ecc71", hover_color="#27ae60", command=self._add).pack(side="left", padx=(4, 0))

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.hgetall, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, data: dict) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        decoded = decode_bytes(data)
        for field_name, value in decoded.items():
            HashRow(self.scroll, field_name, value, on_delete=self._delete_field).pack(fill="x", pady=1)

    def _add(self) -> None:
        field_name = self.field_var.get().strip()
        value = self.value_var.get()
        if not field_name:
            self.status_bar.set_text("Field name is required.", "error")
            return
        self.runner.run(self.client.hset, lambda _: self._on_saved(), self._on_error, self.key, field_name, value)

    def _delete_field(self, field_name: str) -> None:
        self.runner.run(self.client.hdel, lambda _: self._on_saved(), self._on_error, self.key, field_name)

    def _on_saved(self) -> None:
        self.field_var.set("")
        self.value_var.set("")
        self.status_bar.set_text(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
