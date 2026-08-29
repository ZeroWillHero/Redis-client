"""Unit tests for RedisClient using fakeredis (no real server needed)."""
import fakeredis
import pytest

from app.connection_manager import ConnectionProfile
from app.redis_client import RedisClient


@pytest.fixture()
def client():
    profile = ConnectionProfile(name="test", host="localhost", port=6379)
    rc = RedisClient(profile)
    rc._conn = fakeredis.FakeRedis()
    return rc


def test_string_roundtrip(client):
    client.set_string("greeting", "hello")
    assert client.get_string("greeting") == b"hello"
    assert client.get_type("greeting") == "string"


def test_hash_roundtrip(client):
    client.hset("user:1", "name", "Ada")
    client.hset("user:1", "role", "engineer")
    data = client.hgetall("user:1")
    assert data == {b"name": b"Ada", b"role": b"engineer"}
    client.hdel("user:1", "role")
    assert client.hgetall("user:1") == {b"name": b"Ada"}


def test_list_roundtrip(client):
    client.rpush("queue", "a")
    client.rpush("queue", "b")
    assert client.lrange("queue") == [b"a", b"b"]
    client.lset("queue", 0, "z")
    assert client.lrange("queue") == [b"z", b"b"]
    client.lrem_index("queue", 0)
    assert client.lrange("queue") == [b"b"]


def test_set_roundtrip(client):
    client.sadd("tags", "python")
    client.sadd("tags", "redis")
    assert client.smembers("tags") == {b"python", b"redis"}
    client.srem("tags", "python")
    assert client.smembers("tags") == {b"redis"}


def test_zset_roundtrip(client):
    client.zadd("leaderboard", "alice", 10)
    client.zadd("leaderboard", "bob", 20)
    assert client.zrange_withscores("leaderboard") == [(b"alice", 10.0), (b"bob", 20.0)]
    client.zrem("leaderboard", "alice")
    assert client.zrange_withscores("leaderboard") == [(b"bob", 20.0)]


def test_scan_and_delete(client):
    client.set_string("a", "1")
    client.set_string("b", "2")
    keys = set(client.scan_keys("*"))
    assert keys == {b"a", b"b"}
    client.delete_key("a")
    assert set(client.scan_keys("*")) == {b"b"}


def test_ttl(client):
    client.set_string("temp", "x")
    client.set_ttl("temp", 100)
    assert client.get_ttl("temp") > 0
    client.set_ttl("temp", None)
    assert client.get_ttl("temp") == -1


def test_execute_raw(client):
    result = client.execute_raw("SET foo bar")
    assert result is True or result == b"OK"
    assert client.execute_raw("GET foo") == b"bar"


def test_rename_key(client):
    client.set_string("old", "v")
    client.rename_key("old", "new")
    assert client.get_string("new") == b"v"
    assert not client.key_exists("old")
