"""Add/edit connection profile dialog."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.connection_manager import ConnectionProfile
from app.ui import theme


class ConnectionDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save: Callable[[ConnectionProfile], None], profile: Optional[ConnectionProfile] = None):
        super().__init__(master)
        self.title("Edit Connection" if profile else "New Connection")
        self.geometry("380x480")
        self.minsize(380, 480)
        self.resizable(False, True)
        self.on_save = on_save
        self.profile = profile or ConnectionProfile()

        self.configure(fg_color=theme.BACKGROUND)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_row, text="Cancel", corner_radius=theme.RADIUS_SM,
                      command=self.destroy, **theme.ghost_button_style()).pack(side="left")
        ctk.CTkButton(btn_row, text="Save", corner_radius=theme.RADIUS_SM,
                      command=self._save, **theme.primary_button_style()).pack(side="right")

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.name_var = ctk.StringVar(value=self.profile.name)
        self.host_var = ctk.StringVar(value=self.profile.host)
        self.port_var = ctk.StringVar(value=str(self.profile.port))
        self.password_var = ctk.StringVar(value=self.profile.password)
        self.db_var = ctk.StringVar(value=str(self.profile.db))
        self.ssl_var = ctk.BooleanVar(value=self.profile.use_ssl)

        rows = [
            ("Name", self.name_var, {}),
            ("Host", self.host_var, {}),
            ("Port", self.port_var, {}),
            ("Password", self.password_var, {"show": "*"}),
            ("DB index", self.db_var, {}),
        ]
        for label, var, opts in rows:
            ctk.CTkLabel(frame, text=label, anchor="w").pack(fill="x", pady=(6, 2))
            ctk.CTkEntry(frame, textvariable=var, **opts).pack(fill="x")

        ctk.CTkSwitch(frame, text="Use SSL/TLS", variable=self.ssl_var).pack(anchor="w", pady=(16, 12))

        self.error_label = ctk.CTkLabel(frame, text="", text_color=theme.DESTRUCTIVE)
        self.error_label.pack(anchor="w", pady=(0, 8))

        self.transient(master)
        self.after(50, self.grab_set)

    def _save(self) -> None:
        name = self.name_var.get().strip()
        host = self.host_var.get().strip()
        if not name or not host:
            self.error_label.configure(text="Name and host are required.")
            return
        try:
            port = int(self.port_var.get())
            db = int(self.db_var.get())
        except ValueError:
            self.error_label.configure(text="Port and DB index must be numbers.")
            return

        self.profile.name = name
        self.profile.host = host
        self.profile.port = port
        self.profile.password = self.password_var.get()
        self.profile.db = db
        self.profile.use_ssl = self.ssl_var.get()

        self.on_save(self.profile)
        self.destroy()
