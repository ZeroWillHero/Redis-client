"""CRUD for saved Redis connection profiles, persisted as JSON."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

from app.config import CONNECTIONS_FILE


@dataclass
class ConnectionProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Connection"
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    use_ssl: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionProfile":
        known = {f: data[f] for f in cls.__dataclass_fields__ if data.get(f) is not None}
        return cls(**known)


class ConnectionManager:
    def __init__(self, path=CONNECTIONS_FILE):
        self.path = path
        self._profiles: list[ConnectionProfile] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._profiles = []
            return
        try:
            raw = json.loads(self.path.read_text())
            self._profiles = [ConnectionProfile.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            self._profiles = []

    def save(self) -> None:
        self.path.write_text(json.dumps([p.to_dict() for p in self._profiles], indent=2))

    def list_profiles(self) -> list[ConnectionProfile]:
        return list(self._profiles)

    def get(self, profile_id: str) -> Optional[ConnectionProfile]:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def add(self, profile: ConnectionProfile) -> None:
        self._profiles.append(profile)
        self.save()

    def update(self, profile: ConnectionProfile) -> None:
        for i, p in enumerate(self._profiles):
            if p.id == profile.id:
                self._profiles[i] = profile
                break
        self.save()

    def delete(self, profile_id: str) -> None:
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self.save()

    def duplicate(self, profile_id: str) -> Optional[ConnectionProfile]:
        original = self.get(profile_id)
        if original is None:
            return None
        clone = ConnectionProfile(
            name=f"{original.name} (copy)",
            host=original.host,
            port=original.port,
            password=original.password,
            db=original.db,
            use_ssl=original.use_ssl,
        )
        self.add(clone)
        return clone
