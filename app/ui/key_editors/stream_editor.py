from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.widgets import KeyMetaBar
from app.utils import decode_bytes, format_redis_error


class StreamRow(ctk.CTkFrame):
    def __init__(self, master, entry_id: str, fields: dict, on_remove):
        super().__init__(master, **theme.card_style())
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(top, text=entry_id, font=theme.font_body(11, "bold")).pack(side="left")
        ctk.CTkButton(top, text="✕", width=24, height=24, command=lambda: on_remove(entry_id),
                      corner_radius=theme.RADIUS_SM, **theme.ghost_button_style()).pack(side="right")
        body = ", ".join(f"{k}={v}" for k, v in fields.items())
        ctk.CTkLabel(self, text=body, anchor="w", justify="left", wraplength=520,
                     text_color=theme.MUTED_FOREGROUND).pack(fill="x", padx=8, pady=(0, 6))


class StreamEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, toast, on_change, on_key_renamed, on_key_deleted):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.toast = toast
        self.on_change = on_change

        self.meta_bar = KeyMetaBar(self, client, task_runner, key, "stream", toast,
                                    on_renamed=on_key_renamed, on_deleted=on_key_deleted)
        self.meta_bar.pack(fill="x", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=300)
        self.scroll.pack(fill="both", expand=True, pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.fields_var = ctk.StringVar()
        entry = ctk.CTkEntry(row, textvariable=self.fields_var, placeholder_text="field1=value1,field2=value2")
        entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Add entry (XADD)", corner_radius=theme.RADIUS_SM,
                      command=self._add, **theme.success_button_style()).pack(side="left", padx=(4, 0))

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.xrange, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, entries: list) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        for entry_id, fields in decode_bytes(entries):
            StreamRow(self.scroll, entry_id, fields, on_remove=self._remove_entry).pack(fill="x", pady=4)

    def _add(self) -> None:
        raw = self.fields_var.get().strip()
        if not raw:
            self.toast.show("Enter at least one field=value pair.", "error")
            return
        fields = {}
        for pair in raw.split(","):
            if "=" not in pair:
                self.toast.show("Use field=value pairs separated by commas.", "error")
                return
            k, v = pair.split("=", 1)
            fields[k.strip()] = v.strip()
        self.runner.run(self.client.xadd, lambda _: self._on_saved(), self._on_error, self.key, fields)

    def _remove_entry(self, entry_id: str) -> None:
        self.runner.run(self.client.xdel, lambda _: self._on_saved(), self._on_error, self.key, entry_id)

    def _on_saved(self) -> None:
        self.fields_var.set("")
        self.toast.show(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
