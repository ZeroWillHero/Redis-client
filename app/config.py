"""App-level constants and file paths."""
from pathlib import Path

APP_NAME = "Redis GUI Client"
APP_DIR = Path.home() / ".redis_gui_client"
CONNECTIONS_FILE = APP_DIR / "connections.json"

DEFAULT_SCAN_COUNT = 300
DEFAULT_CONNECT_TIMEOUT = 4.0
DEFAULT_SOCKET_TIMEOUT = 6.0

APPEARANCE_LIGHT = "light"
APPEARANCE_DARK = "dark"
COLOR_THEME = "blue"

APP_DIR.mkdir(parents=True, exist_ok=True)
