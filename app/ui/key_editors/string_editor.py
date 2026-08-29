from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, human_bytes, try_pretty_json, format_redis_error


class StringEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, status_bar, on_change):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.status_bar = status_bar
        self.on_change = on_change

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=f"Key: {key}", font=("Segoe UI", 15, "bold")).pack(side="left")
        self.size_label = ctk.CTkLabel(top, text="", text_color="gray60")
        self.size_label.pack(side="right")

        self.text = ctk.CTkTextbox(self, height=380, font=("Consolas", 12))
        self.text.pack(fill="both", expand=True, pady=8)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Pretty-print JSON", fg_color="transparent", border_width=1, command=self._pretty).pack(side="left")
        ctk.CTkButton(btns, text="Save", fg_color="#2ecc71", hover_color="#27ae60", command=self._save).pack(side="right")
        ctk.CTkButton(btns, text="Revert", fg_color="transparent", border_width=1, command=self.load).pack(side="right", padx=8)

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
            self.status_bar.set_text("Value is not valid JSON.", "error")
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", pretty)

    def _save(self) -> None:
        value = self.text.get("1.0", "end-1c")
        self.runner.run(self.client.set_string, lambda _: self._on_saved(), self._on_error, self.key, value)

    def _on_saved(self) -> None:
        self.status_bar.set_text(f"Saved '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
