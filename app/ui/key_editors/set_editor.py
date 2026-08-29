from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, format_redis_error


class SetRow(ctk.CTkFrame):
    def __init__(self, master, member: str, on_remove):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=member, anchor="w").pack(side="left", fill="x", expand=True, padx=(4, 8))
        ctk.CTkButton(self, text="✕", width=28, fg_color="transparent", border_width=1, text_color="#e74c3c",
                      command=lambda: on_remove(member)).pack(side="right", padx=4)


class SetEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, status_bar, on_change):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.status_bar = status_bar
        self.on_change = on_change

        ctk.CTkLabel(self, text=f"Key: {key} (Set)", font=("Segoe UI", 15, "bold")).pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=340)
        self.scroll.pack(fill="both", expand=True, pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.value_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.value_var, placeholder_text="member").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Add", fg_color="#2ecc71", hover_color="#27ae60", command=self._add).pack(side="left", padx=(4, 0))

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
        self.status_bar.set_text(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
