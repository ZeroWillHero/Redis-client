from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.widgets import KeyMetaBar, busy_scope
from app.utils import decode_bytes, human_bytes, try_pretty_json, format_redis_error


class StringEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, toast, on_change, on_key_renamed, on_key_deleted):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.toast = toast
        self.on_change = on_change

        self.meta_bar = KeyMetaBar(self, client, task_runner, key, "string", toast,
                                    on_renamed=on_key_renamed, on_deleted=on_key_deleted)
        self.meta_bar.pack(fill="x", pady=(0, 8))

        size_row = ctk.CTkFrame(self, fg_color="transparent")
        size_row.pack(fill="x")
        self.size_label = ctk.CTkLabel(size_row, text="", text_color=theme.MUTED_FOREGROUND)
        self.size_label.pack(side="right")

        self.text = ctk.CTkTextbox(self, height=380, font=theme.font_mono(12), **theme.card_style())
        self.text.pack(fill="both", expand=True, pady=8)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Pretty-print JSON", corner_radius=theme.RADIUS_SM,
                      command=self._pretty, **theme.ghost_button_style()).pack(side="left")
        self.save_btn = ctk.CTkButton(btns, text="Save", corner_radius=theme.RADIUS_SM,
                                       command=self._save, **theme.success_button_style())
        self.save_btn.pack(side="right")
        ctk.CTkButton(btns, text="Revert", corner_radius=theme.RADIUS_SM,
                      command=self.load, **theme.ghost_button_style()).pack(side="right", padx=8)

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.get_string, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, value) -> None:
        text = decode_bytes(value) or ""
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.size_label.configure(text=human_bytes(len(value) if value else 0))

    def _pretty(self) -> None:
        current = self.text.get("1.0", "end-1c")
        pretty = try_pretty_json(current)
        if pretty is None:
            self.toast.show("Value is not valid JSON.", "error")
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", pretty)

    def _save(self) -> None:
        value = self.text.get("1.0", "end-1c")
        start, stop = busy_scope([self.save_btn])
        self.runner.run(self.client.set_string, lambda _: self._on_saved(), self._on_error, self.key, value, on_start=start, on_done=stop)

    def _on_saved(self) -> None:
        self.toast.show(f"Saved '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
