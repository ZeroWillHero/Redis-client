from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.widgets import KeyMetaBar
from app.utils import decode_bytes, format_redis_error


class SetRow(ctk.CTkFrame):
    def __init__(self, master, member: str, on_remove):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=member, anchor="w").pack(side="left", fill="x", expand=True, padx=(4, 8))
        ctk.CTkButton(self, text="✕", width=28, command=lambda: on_remove(member),
                      corner_radius=theme.RADIUS_SM, **theme.ghost_button_style()).pack(side="right", padx=4)


class SetEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, toast, on_change, on_key_renamed, on_key_deleted):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.toast = toast
        self.on_change = on_change

        self.meta_bar = KeyMetaBar(self, client, task_runner, key, "set", toast,
                                    on_renamed=on_key_renamed, on_deleted=on_key_deleted)
        self.meta_bar.pack(fill="x", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, height=340, **theme.card_style())
        self.scroll.pack(fill="both", expand=True, pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.value_var, placeholder_text="member").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Add", corner_radius=theme.RADIUS_SM,
                      command=self._add, **theme.success_button_style()).pack(side="left", padx=(4, 0))

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.smembers, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, members: set) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        for member in sorted(decode_bytes(members)):
            SetRow(self.scroll, member, on_remove=self._remove_member).pack(fill="x", pady=1)

    def _add(self) -> None:
        value = self.value_var.get()
        if not value:
            return
        self.runner.run(self.client.sadd, lambda _: self._on_saved(), self._on_error, self.key, value)

    def _remove_member(self, member: str) -> None:
        self.runner.run(self.client.srem, lambda _: self._on_saved(), self._on_error, self.key, member)

    def _on_saved(self) -> None:
        self.value_var.set("")
        self.toast.show(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
