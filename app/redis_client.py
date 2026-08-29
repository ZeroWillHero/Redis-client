"""Thin wrapper around redis-py plus a background worker for non-blocking calls."""
from __future__ import annotations

import shlex
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import redis

from app.config import DEFAULT_CONNECT_TIMEOUT, DEFAULT_SCAN_COUNT, DEFAULT_SOCKET_TIMEOUT
from app.connection_manager import ConnectionProfile


class RedisClient:
    """Wraps a redis.Redis connection. Blocking calls should be dispatched
    through TaskRunner rather than called directly on the Tk main thread."""

    def __init__(self, profile: ConnectionProfile):
        self.profile = profile
        self._conn = redis.Redis(
            host=profile.host,
            port=profile.port,
            password=profile.password or None,
            db=profile.db,
            ssl=profile.use_ssl,
            socket_connect_timeout=DEFAULT_CONNECT_TIMEOUT,
            socket_timeout=DEFAULT_SOCKET_TIMEOUT,
            decode_responses=False,
        )

    def ping(self) -> bool:
        return self._conn.ping()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ---- key browsing ----
    def scan_keys(self, pattern: str = "*", count: int = DEFAULT_SCAN_COUNT, limit: int = 5000) -> list:
        keys: list = []
        cursor = 0
        while True:
            cursor, batch = self._conn.scan(cursor=cursor, match=pattern, count=count)
            keys.extend(batch)
            if cursor == 0 or len(keys) >= limit:
                break
        return keys[:limit]

    def get_type(self, key: bytes | str) -> str:
        t = self._conn.type(key)
        return t.decode() if isinstance(t, bytes) else str(t)

    def get_ttl(self, key: bytes | str) -> int:
        return self._conn.ttl(key)

    def set_ttl(self, key: bytes | str, seconds: int | None) -> None:
        if seconds is None or seconds < 0:
            self._conn.persist(key)
        else:
            self._conn.expire(key, seconds)

    def delete_key(self, key: bytes | str) -> None:
        self._conn.delete(key)

    def rename_key(self, old: bytes | str, new: str) -> None:
        self._conn.rename(old, new)

    def key_exists(self, key: str) -> bool:
        return bool(self._conn.exists(key))

    # ---- string ----
    def get_string(self, key: bytes | str):
        return self._conn.get(key)

    def set_string(self, key: str, value: str) -> None:
        self._conn.set(key, value)

    # ---- hash ----
    def hgetall(self, key: bytes | str) -> dict:
        return self._conn.hgetall(key)

    def hset(self, key: str, field_name: str, value: str) -> None:
        self._conn.hset(key, field_name, value)

    def hdel(self, key: str, field_name: str) -> None:
        self._conn.hdel(key, field_name)

    # ---- list ----
    def lrange(self, key: bytes | str, start: int = 0, end: int = -1) -> list:
        return self._conn.lrange(key, start, end)

    def rpush(self, key: str, value: str) -> None:
        self._conn.rpush(key, value)

    def lset(self, key: str, index: int, value: str) -> None:
        self._conn.lset(key, index, value)

    def lrem_index(self, key: str, index: int) -> None:
        sentinel = f"__DELETED__{id(self)}__"
        self._conn.lset(key, index, sentinel)
        self._conn.lrem(key, 1, sentinel)

    # ---- set ----
    def smembers(self, key: bytes | str) -> set:
        return self._conn.smembers(key)

    def sadd(self, key: str, member: str) -> None:
        self._conn.sadd(key, member)

    def srem(self, key: str, member: str) -> None:
        self._conn.srem(key, member)

    # ---- sorted set ----
    def zrange_withscores(self, key: bytes | str) -> list:
        return self._conn.zrange(key, 0, -1, withscores=True)

    def zadd(self, key: str, member: str, score: float) -> None:
        self._conn.zadd(key, {member: score})

    def zrem(self, key: str, member: str) -> None:
        self._conn.zrem(key, member)

    # ---- console / raw ----
    def execute_raw(self, command_str: str) -> Any:
        parts = shlex.split(command_str)
        if not parts:
            return None
        return self._conn.execute_command(*parts)

    # ---- server info ----
    def info(self) -> dict:
        return self._conn.info()

    def dbsize(self) -> int:
        return self._conn.dbsize()


class TaskRunner:
    """Runs blocking callables on a background thread pool and delivers
    results back to the Tk main loop via root.after, so the UI never blocks."""

    def __init__(self, tk_root):
        self._root = tk_root
        self._executor = ThreadPoolExecutor(max_workers=4)

    def run(self, func: Callable, on_success: Callable[[Any], None], on_error: Callable[[Exception], None], *args, **kwargs) -> None:
        def worker():
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                self._root.after(0, lambda: on_error(exc))
            else:
                self._root.after(0, lambda: on_success(result))

        self._executor.submit(worker)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
