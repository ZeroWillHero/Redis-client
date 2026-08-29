# Redis GUI Client

A modern, cross-platform (macOS, Windows, Linux) desktop GUI client for Redis, built with Python, Tkinter, and `ttkbootstrap`. Designed for local development/testing: run raw commands, browse and edit keys of every type, watch server stats, and manage multiple saved connections.

## Features
- Multiple saved connection profiles (host, port, password, DB index, SSL)
- Key browser with `SCAN`-based search/filter, type badges, create/delete
- Type-aware editors: String (with JSON pretty-print), Hash, List, Set, Sorted Set
- TTL / expiry management and key rename/delete
- Raw command console with history (↑/↓)
- Server Info tab (memory, clients, stats, replication, keyspace)
- Light/dark theme toggle
- All Redis calls run on a background thread pool so the UI never freezes

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

For running tests (uses `fakeredis`, no real server required):

```bash
pip install -r requirements-dev.txt
pytest
```

## Usage
1. Launch the app, click **+** in the sidebar to add a connection (e.g. `localhost:6379`).
2. Double-click (or select + **Connect**) to connect.
3. Browse keys on the left; click a key to view/edit it in the **Data** tab.
4. Use the **Console** tab to run any raw Redis command.
5. Use the **Server Info** tab to inspect `INFO` output; click **Refresh Info** to update.

Connection profiles (including passwords) are stored locally in `~/.redis_gui_client/connections.json` in plain JSON — convenient for local testing, but not intended for storing sensitive production credentials.

## Building standalone binaries

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name redis-gui-client main.py
```

Run this on each target OS (macOS, Windows, Linux) to produce a native binary for that platform; PyInstaller does not cross-compile.
