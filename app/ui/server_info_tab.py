from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.utils import format_redis_error

SECTIONS = {
    "Server": ["redis_version", "os", "process_id", "tcp_port", "uptime_in_seconds"],
    "Clients": ["connected_clients", "blocked_clients"],
    "Memory": ["used_memory_human", "used_memory_peak_human", "maxmemory_human"],
    "Persistence": ["rdb_last_save_time", "rdb_changes_since_last_save", "aof_enabled"],
    "Stats": ["total_connections_received", "total_commands_processed", "instantaneous_ops_per_sec", "expired_keys", "evicted_keys"],
    "Replication": ["role", "connected_slaves"],
    "Keyspace": [],
}

AUTO_REFRESH_MS = 10000


class ServerInfoTab(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, toast):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.toast = toast
        self.auto_refresh = ctk.BooleanVar(value=False)
        self._auto_job = None

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        self.dbsize_label = ctk.CTkLabel(top, text="", text_color=theme.MUTED_FOREGROUND, font=theme.font_body(12, "bold"))
        self.dbsize_label.pack(side="left")
        ctk.CTkSwitch(top, text="Auto-refresh (10s)", variable=self.auto_refresh,
                      command=self._toggle_auto_refresh).pack(side="right", padx=(0, 8))
        ctk.CTkButton(top, text="⟳ Refresh Info", corner_radius=theme.RADIUS_SM,
                      command=self.load, **theme.ghost_button_style()).pack(side="right")

        self.tabs = ctk.CTkTabview(self, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_LG)
        self.tabs.pack(fill="both", expand=True, pady=8)
        self.info_tab = self.tabs.add("Info")
        self.slowlog_tab = self.tabs.add("Slow Log")

        self.scroll = ctk.CTkScrollableFrame(self.info_tab, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        self.slowlog_scroll = ctk.CTkScrollableFrame(self.slowlog_tab, fg_color="transparent")
        self.slowlog_scroll.pack(fill="both", expand=True, pady=(4, 0))
        ctk.CTkButton(self.slowlog_tab, text="⟳ Refresh Slow Log", corner_radius=theme.RADIUS_SM,
                      command=self._load_slowlog, **theme.ghost_button_style()).pack(anchor="w")

        self.load()
        self._load_slowlog()

    def load(self) -> None:
        self.runner.run(self.client.info, self._on_loaded, self._on_error)
        self.runner.run(self.client.dbsize, self._on_dbsize, lambda _e: None)

    def _on_dbsize(self, size: int) -> None:
        self.dbsize_label.configure(text=f"{size} keys in current DB")

    def _toggle_auto_refresh(self) -> None:
        if self.auto_refresh.get():
            self._schedule_auto_refresh()
        elif self._auto_job:
            self.after_cancel(self._auto_job)
            self._auto_job = None

    def _schedule_auto_refresh(self) -> None:
        if not self.auto_refresh.get():
            return
        self.load()
        self._auto_job = self.after(AUTO_REFRESH_MS, self._schedule_auto_refresh)

    def _on_loaded(self, info: dict) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()

        for section, fields in SECTIONS.items():
            frame = ctk.CTkFrame(self.scroll, corner_radius=theme.RADIUS_MD, fg_color=theme.SURFACE_MUTED)
            frame.pack(fill="x", pady=6, padx=2)
            ctk.CTkLabel(frame, text=section, font=theme.font_heading(13)).grid(
                row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6)
            )

            if section == "Keyspace":
                keyspace_keys = [k for k in info if k.startswith("db")]
                if not keyspace_keys:
                    ctk.CTkLabel(frame, text="(empty)", text_color=theme.MUTED_FOREGROUND).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
                for i, k in enumerate(keyspace_keys, start=1):
                    ctk.CTkLabel(frame, text=k, font=theme.font_body(11, "bold")).grid(row=i, column=0, sticky="w", padx=(12, 20), pady=2)
                    ctk.CTkLabel(frame, text=str(info[k])).grid(row=i, column=1, sticky="w", pady=2)
                ctk.CTkLabel(frame, text="").grid(row=len(keyspace_keys) + 1, column=0, pady=(0, 6))
                continue

            for i, field_name in enumerate(fields, start=1):
                value = info.get(field_name, "-")
                ctk.CTkLabel(frame, text=field_name, font=theme.font_body(11, "bold")).grid(row=i, column=0, sticky="w", padx=(12, 20), pady=2)
                ctk.CTkLabel(frame, text=str(value)).grid(row=i, column=1, sticky="w", pady=2)
            ctk.CTkLabel(frame, text="").grid(row=len(fields) + 1, column=0, pady=(0, 6))

    def _load_slowlog(self) -> None:
        self.runner.run(self.client.slowlog_get, self._on_slowlog_loaded, self._on_error)

    def _on_slowlog_loaded(self, entries: list) -> None:
        for child in self.slowlog_scroll.winfo_children():
            child.destroy()
        if not entries:
            ctk.CTkLabel(self.slowlog_scroll, text="No slow log entries.", text_color=theme.MUTED_FOREGROUND).pack(anchor="w", pady=8)
            return
        for entry in entries:
            command = " ".join(
                p.decode() if isinstance(p, bytes) else str(p) for p in entry.get("command", [])
            )
            row = ctk.CTkFrame(self.slowlog_scroll, corner_radius=theme.RADIUS_SM, fg_color=theme.SURFACE_MUTED)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{entry.get('duration', 0)} µs", width=90,
                         text_color=theme.WARNING, font=theme.font_body(11, "bold")).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=command, anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _on_error(self, exc: Exception) -> None:
        self.toast.show(format_redis_error(exc), "error")
