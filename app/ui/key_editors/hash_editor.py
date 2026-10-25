from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.widgets import KeyMetaBar
from app.utils import decode_bytes, format_redis_error


class HashRow(ctk.CTkFrame):
    def __init__(self, master, field_name: str, value: str, on_delete):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=field_name, anchor="w", font=theme.font_body(11, "bold"), width=140).pack(side="left", padx=(4, 8))
        ctk.CTkLabel(self, text=value, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(self, text="✕", width=28, command=lambda: on_delete(field_name),
                      corner_radius=theme.RADIUS_SM, **theme.ghost_button_style()).pack(side="right", padx=4)


class HashEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, toast, on_change, on_key_renamed, on_key_deleted):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.toast = toast
        self.on_change = on_change

        self.meta_bar = KeyMetaBar(self, client, task_runner, key, "hash", toast,
                                    on_renamed=on_key_renamed, on_deleted=on_key_deleted)
        self.meta_bar.pack(fill="x", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, height=340, **theme.card_style())
        self.scroll.pack(fill="both", expand=True, pady=8)

        add_row = ctk.CTkFrame(self, fg_color="transparent")
        add_row.pack(fill="x", pady=4)
        self.field_var = ctk.StringVar()
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self.field_var, placeholder_text="field", width=160).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(add_row, textvariable=self.value_var, placeholder_text="value").pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(add_row, text="Add / Update", corner_radius=theme.RADIUS_SM,
                      command=self._add, **theme.success_button_style()).pack(side="left", padx=(4, 0))

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
            self.toast.show("Field name is required.", "error")
            return
        self.runner.run(self.client.hset, lambda _: self._on_saved(), self._on_error, self.key, field_name, value)

    def _delete_field(self, field_name: str) -> None:
        self.runner.run(self.client.hdel, lambda _: self._on_saved(), self._on_error, self.key, field_name)

    def _on_saved(self) -> None:
        self.field_var.set("")
        self.value_var.set("")
        self.toast.show(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
