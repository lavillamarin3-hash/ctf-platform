"""Pruebas aisladas del bloqueo de sesión web, sin servidor Redis real."""
import unittest
from fastapi import HTTPException

from app.services.single_session import reserve, validate, release, redis_key


class MemoryRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def eval(self, script, keys, key, sid):
        if self.values.get(key) == sid:
            self.values.pop(key, None)
            return 1
        return 0


class SingleSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_login_is_denied(self):
        redis = MemoryRedis()
        await reserve(redis, 12, "session-A", 1200)
        with self.assertRaises(HTTPException) as blocked:
            await reserve(redis, 12, "session-B", 1200)
        self.assertEqual(blocked.exception.status_code, 409)
        await validate(redis, 12, "session-A")
        with self.assertRaises(HTTPException) as expired:
            await validate(redis, 12, "session-B")
        self.assertEqual(expired.exception.status_code, 401)

    async def test_logout_cannot_delete_new_session(self):
        redis = MemoryRedis()
        await reserve(redis, 12, "session-A", 1200)
        await release(redis, 12, "session-B")
        self.assertEqual(redis.values[redis_key(12)], "session-A")
        await release(redis, 12, "session-A")
        await reserve(redis, 12, "session-B", 1200)
        await validate(redis, 12, "session-B")

    async def test_missing_session_is_not_accepted(self):
        redis = MemoryRedis()
        with self.assertRaises(HTTPException) as denied:
            await validate(redis, 99, None)
        self.assertEqual(denied.exception.status_code, 401)
