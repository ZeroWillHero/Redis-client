from __future__ import annotations

import customtkinter as ctk

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


class ServerInfoTab(ctk.CTkFrame):
    def __init__(self, master, client, task_runner, status_bar):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = task_runner
        self.status_bar = status_bar

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkButton(top, text="⟳ Refresh Info", command=self.load).pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, pady=8)

        self.load()

    def load(self) -> None:
        self.runner.run(self.client.info, self._on_loaded, self._on_error)

    def _on_loaded(self, info: dict) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()

        for section, fields in SECTIONS.items():
            frame = ctk.CTkFrame(self.scroll, corner_radius=8)
            frame.pack(fill="x", pady=6, padx=2)
            ctk.CTkLabel(frame, text=section, font=("Segoe UI", 13, "bold")).grid(
                row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6)
            )

            if section == "Keyspace":
                keyspace_keys = [k for k in info if k.startswith("db")]
                if not keyspace_keys:
                    ctk.CTkLabel(frame, text="(empty)", text_color="gray60").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
                for i, k in enumerate(keyspace_keys, start=1):
                    ctk.CTkLabel(frame, text=k, font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", padx=(12, 20), pady=2)
                    ctk.CTkLabel(frame, text=str(info[k])).grid(row=i, column=1, sticky="w", pady=2)
                ctk.CTkLabel(frame, text="").grid(row=len(keyspace_keys) + 1, column=0, pady=(0, 6))
                continue

            for i, field_name in enumerate(fields, start=1):
                value = info.get(field_name, "-")
                ctk.CTkLabel(frame, text=field_name, font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", padx=(12, 20), pady=2)
                ctk.CTkLabel(frame, text=str(value)).grid(row=i, column=1, sticky="w", pady=2)
            ctk.CTkLabel(frame, text="").grid(row=len(fields) + 1, column=0, pady=(0, 6))

    def _on_error(self, exc: Exception) -> None:
        self.status_bar.set_text(format_redis_error(exc), "error")
