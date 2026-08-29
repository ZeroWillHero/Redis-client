from __future__ import annotations

import customtkinter as ctk

from app.utils import decode_bytes, format_redis_error


class ZSetRow(ctk.CTkFrame):
    def __init__(self, master, member: str, score: float, on_remove):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=member, anchor="w").pack(side="left", fill="x", expand=True, padx=(4, 8))
        ctk.CTkLabel(self, text=str(score), width=80, text_color="gray60").pack(side="left", padx=(0, 8))
        ctk.CTkButton(self, text="✕", width=28, fg_color="transparent", border_width=1, text_color="#e74c3c",
                      command=lambda: on_remove(member)).pack(side="right", padx=4)


class ZSetEditor(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, key: str, status_bar, on_change):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.key = key
        self.status_bar = status_bar
        self.on_change = on_change
        self._rows_cache: list[tuple[str, float]] = []
        self._sort_ascending = True

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"Key: {key} (Sorted Set)", font=("Segoe UI", 15, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Sort by score", width=110, fg_color="transparent", border_width=1,
                      command=self._sort_by_score).pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=310)
        self.scroll.pack(fill="both", expand=True, pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        self.member_var = ctk.StringVar()
        self.score_var = ctk.StringVar(value="0")
        ctk.CTkEntry(row, textvariable=self.member_var, placeholder_text="member").pack(side="left", fill="x", expand=True)
        ctk.CTkEntry(row, textvariable=self.score_var, placeholder_text="score", width=90).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Add / Update", fg_color="#2ecc71", hover_color="#27ae60", command=self._add).pack(side="left", padx=(4, 0))

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.zrange_withscores, self._on_loaded, self._on_error, self.key)

    def _on_loaded(self, items: list) -> None:
        self._rows_cache = [(m, s) for m, s in decode_bytes(items)]
        self._render()

    def _render(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        for member, score in self._rows_cache:
            ZSetRow(self.scroll, member, score, on_remove=self._remove_member).pack(fill="x", pady=1)

    def _sort_by_score(self) -> None:
        self._rows_cache.sort(key=lambda r: r[1], reverse=not self._sort_ascending)
        self._sort_ascending = not self._sort_ascending
        self._render()

    def _add(self) -> None:
        member = self.member_var.get().strip()
        if not member:
            return
        try:
            score = float(self.score_var.get())
        except ValueError:
            self.status_bar.set_text("Score must be a number.", "error")
            return
        self.runner.run(self.client.zadd, lambda _: self._on_saved(), self._on_error, self.key, member, score)

    def _remove_member(self, member: str) -> None:
        self.runner.run(self.client.zrem, lambda _: self._on_saved(), self._on_error, self.key, member)

    def _on_saved(self) -> None:
        self.member_var.set("")
        self.score_var.set("0")
        self.status_bar.set_text(f"Updated '{self.key}'", "success")
        self.load()
        self.on_change()

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
