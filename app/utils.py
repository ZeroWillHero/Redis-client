"""Shared formatting and error-handling helpers."""
from __future__ import annotations

import json

import redis.exceptions as rexc


def format_redis_error(exc: Exception) -> str:
    if isinstance(exc, rexc.AuthenticationError):
        return "Authentication failed: incorrect password."
    if isinstance(exc, rexc.ConnectionError):
        return f"Could not connect to Redis server: {exc}"
    if isinstance(exc, rexc.TimeoutError):
        return "Connection timed out. Check host/port and that Redis is running."
    if isinstance(exc, rexc.ResponseError):
        return f"Redis error: {exc}"
    return f"Unexpected error: {exc}"


def decode_bytes(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return repr(value)
    if isinstance(value, list):
        return [decode_bytes(v) for v in value]
    if isinstance(value, dict):
        return {decode_bytes(k): decode_bytes(v) for k, v in value.items()}
    if isinstance(value, set):
        return {decode_bytes(v) for v in value}
    if isinstance(value, tuple):
        return tuple(decode_bytes(v) for v in value)
    return value


def try_pretty_json(text: str) -> str | None:
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def human_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.2f}{unit}"
        size /= 1024
    return f"{size:.2f}PB"
