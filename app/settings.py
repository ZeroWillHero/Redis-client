"""Small persisted app settings (theme, console favorites), stored as JSON."""
from __future__ import annotations

import json

from app.config import SETTINGS_FILE

_DEFAULTS = {
    "appearance_mode": "light",
    "console_favorites": [],
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def update_settings(**kwargs) -> dict:
    data = load_settings()
    data.update(kwargs)
    save_settings(data)
    return data
