"""Tras limpiar una corrida vencida, iniciar recupera el lock del reto."""
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api import runs
from app.core import now_utc


class DeletionStartLockTests(unittest.IsolatedAsyncioTestCase):
    async def test_deleted_while_expired_cleanup_commits_does_not_restart_resources(self):
        await self.assert_rejected_after_cleanup(None, 404)

    async def test_assignment_revoked_while_cleanup_commits_does_not_restart_resources(self):
        challenge = SimpleNamespace(id=3, code='QA-RELOCK', flags=[])
        await self.assert_rejected_after_cleanup(challenge, 403)

    async def assert_rejected_after_cleanup(self, relocked, expected):
        challenge = SimpleNamespace(id=3, code='QA-RELOCK', flags=[])
        active_run = SimpleNamespace(id=10, expires_at=now_utc() - timedelta(minutes=1))
        session = AsyncMock()
        session.scalar.side_effect = [challenge, active_run, relocked]
        context = AsyncMock()
        context.__aenter__.return_value = session
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            session_factory=lambda: context, redis=SimpleNamespace())))
        with patch('app.api.runs.check_rate_limit', new_callable=AsyncMock), \
             patch('app.api.runs._assigned', new_callable=AsyncMock, side_effect=[True, False]), \
             patch('app.api.runs._cleanup_run', new_callable=AsyncMock) as cleanup:
            with self.assertRaises(HTTPException) as error:
                await runs.start_challenge('QA-RELOCK', request, SimpleNamespace(id=1))
        self.assertEqual(error.exception.status_code, expected)
        cleanup.assert_awaited_once()
        statement = session.scalar.call_args_list[2].args[0]
        self.assertIsNotNone(statement._for_update_arg)
        session.add.assert_not_called()
