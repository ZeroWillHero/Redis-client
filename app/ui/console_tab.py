from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, format_redis_error


class ConsoleTab(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, status_bar):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.status_bar = status_bar
        self.history: list[str] = []
        self.history_index = -1

        self.output = ctk.CTkTextbox(self, font=("Consolas", 12), state="disabled")
        self.output.pack(fill="both", expand=True)

        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(fill="x", pady=(8, 0))
        self.entry = ctk.CTkEntry(entry_row, font=("Consolas", 12), placeholder_text="e.g. SET foo bar")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self._run())
        self.entry.bind("<Up>", self._history_prev)
        self.entry.bind("<Down>", self._history_next)
        ctk.CTkButton(entry_row, text="Run", width=70, command=self._run).pack(side="left", padx=(6, 0))
        ctk.CTkButton(entry_row, text="Clear", width=70, fg_color="transparent", border_width=1, command=self._clear).pack(side="left", padx=(6, 0))

        self._write("Type a raw Redis command, e.g. SET foo bar, then press Enter.\n")

    def _write(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _clear(self) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _run(self) -> None:
        command = self.entry.get().strip()
        if not command:
            return
        self.history.append(command)
        self.history_index = len(self.history)
        self.entry.delete(0, "end")
        self._write(f"> {command}\n")
        self.runner.run(self.client.execute_raw, self._on_result, self._on_error, command)

    def _on_result(self, result) -> None:
        self._write(f"{decode_bytes(result)}\n\n")
        self.status_bar.set_text("Command executed.", "success")

    def _on_error(self, exc: Exception) -> None:
        self._write(f"ERROR: {format_redis_error(exc)}\n\n")
        self.status_bar.set_text(format_redis_error(exc), "error")

    def _history_prev(self, _event) -> None:
        if not self.history:
            return
        self.history_index = max(0, self.history_index - 1)
        self.entry.delete(0, "end")
        self.entry.insert(0, self.history[self.history_index])

    def _history_next(self, _event) -> None:
        if not self.history:
            return
        self.history_index = min(len(self.history), self.history_index + 1)
        self.entry.delete(0, "end")
        if self.history_index < len(self.history):
            self.entry.insert(0, self.history[self.history_index])
