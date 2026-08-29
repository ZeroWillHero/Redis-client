"""Shared modern widgets: toolbar, status bar."""
from __future__ import annotations

import customtkinter as ctk

STATUS_COLORS = {
    "info": "gray60",
    "error": "#e74c3c",
    "success": "#2ecc71",
}


class Toolbar(ctk.CTkFrame):
    def __init__(self, master, on_refresh, on_theme_toggle):
        super().__init__(master, corner_radius=0, height=52)
        self.grid_propagate(False)

        self.status_dot = ctk.CTkLabel(self, text="●", text_color="#e74c3c", font=("Segoe UI", 16))
        self.status_dot.pack(side="left", padx=(16, 4), pady=10)
        self.status_label = ctk.CTkLabel(self, text="Not connected", font=("Segoe UI", 13, "bold"))
        self.status_label.pack(side="left")

        self.theme_btn = ctk.CTkButton(self, text="◐ Theme", width=90, fg_color="transparent", border_width=1, command=on_theme_toggle)
        self.theme_btn.pack(side="right", padx=(4, 16), pady=10)
        self.refresh_btn = ctk.CTkButton(self, text="⟳ Refresh", width=100, fg_color="transparent", border_width=1, command=on_refresh)
        self.refresh_btn.pack(side="right", padx=4, pady=10)

    def set_connected(self, name: str | None) -> None:
        if name:
            self.status_dot.configure(text_color="#2ecc71")
            self.status_label.configure(text=f"Connected: {name}")
        else:
            self.status_dot.configure(text_color="#e74c3c")
            self.status_label.configure(text="Not connected")


class StatusBar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0, height=32)
        self.grid_propagate(False)
        self.label = ctk.CTkLabel(self, text="Ready", anchor="w", text_color=STATUS_COLORS["info"])
        self.label.pack(side="left", fill="x", expand=True, padx=12, pady=4)

    def set_text(self, text: str, kind: str = "info") -> None:
        self.label.configure(text=text, text_color=STATUS_COLORS.get(kind, "gray60"))
