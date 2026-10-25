from __future__ import annotations

import customtkinter as ctk

from app.settings import load_settings, update_settings
from app.ui import theme
from app.utils import decode_bytes, format_redis_error


class ConsoleTab(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, toast):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.toast = toast
        self.history: list[str] = []
        self.history_index = -1
        self.favorites: list[str] = load_settings().get("console_favorites", [])

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(top, text="Favorites:", text_color=theme.MUTED_FOREGROUND, font=theme.font_body(11)).pack(side="left")
        self.favorites_menu = ctk.CTkOptionMenu(top, values=self.favorites or ["(none saved)"], width=220,
                                                 command=self._use_favorite)
        self.favorites_menu.pack(side="left", padx=(6, 6))
        self.star_btn = ctk.CTkButton(top, text="☆ Save current", width=120, corner_radius=theme.RADIUS_SM,
                                       command=self._save_favorite, **theme.ghost_button_style())
        self.star_btn.pack(side="left")

        self.output = ctk.CTkTextbox(self, font=theme.font_mono(12), state="disabled", **theme.card_style())
        self.output.pack(fill="both", expand=True)

        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(fill="x", pady=(8, 0))
        self.entry = ctk.CTkEntry(entry_row, font=theme.font_mono(12), placeholder_text="e.g. SET foo bar")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self._run())
        self.entry.bind("<Control-Return>", lambda _e: self._run())
        self.entry.bind("<Up>", self._history_prev)
        self.entry.bind("<Down>", self._history_next)
        ctk.CTkButton(entry_row, text="Run", width=70, corner_radius=theme.RADIUS_SM,
                      command=self._run, **theme.primary_button_style()).pack(side="left", padx=(6, 0))
        ctk.CTkButton(entry_row, text="Clear", width=70, corner_radius=theme.RADIUS_SM,
                      command=self._clear, **theme.ghost_button_style()).pack(side="left", padx=(6, 0))

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
        self.toast.show("Command executed.", "success", duration_ms=2000)

    def _on_error(self, exc: Exception) -> None:
        self._write(f"ERROR: {format_redis_error(exc)}\n\n")
        self.toast.show(format_redis_error(exc), "error")

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

    def _save_favorite(self) -> None:
        command = self.entry.get().strip()
        if not command:
            self.toast.show("Type a command first to save it as a favorite.", "error")
            return
        if command not in self.favorites:
            self.favorites.append(command)
            update_settings(console_favorites=self.favorites)
            self.favorites_menu.configure(values=self.favorites)
        self.favorites_menu.set(command)
        self.toast.show("Saved to favorites.", "success", duration_ms=2000)

    def _use_favorite(self, command: str) -> None:
        if command in self.favorites:
            self.entry.delete(0, "end")
            self.entry.insert(0, command)
