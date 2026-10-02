"""Una cuenta compartida CTF/Guacamole nunca debe borrarse a medias."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.guacamole import guacamole_delete_user
from app.api.users import delete_user
from app.guacamole import GuacamoleApiError


def request_with_session():
    session = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    guacamole_admin = SimpleNamespace(list_users=AsyncMock(return_value=[]), delete_user=AsyncMock())
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: context, guacamole_admin=guacamole_admin))
    )
    return session, guacamole_admin, request


class UserDeleteSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_guacamole_only_delete_rejects_linked_ctf_user(self):
        session, remote, request = request_with_session()
        session.scalar.return_value = 17
        with patch("app.api.guacamole.get_settings", return_value=SimpleNamespace(guacamole_service_account="service")):
            with self.assertRaises(HTTPException) as error:
                await guacamole_delete_user("kevin", request, SimpleNamespace(id=1))
        self.assertEqual(error.exception.status_code, 409)
        remote.delete_user.assert_not_awaited()

    async def test_guacamole_only_delete_still_allows_remote_only_user(self):
        session, remote, request = request_with_session()
        session.scalar.return_value = None
        with patch("app.api.guacamole.get_settings", return_value=SimpleNamespace(guacamole_service_account="service")):
            with patch("app.api.guacamole.write_audit", new_callable=AsyncMock):
                result = await guacamole_delete_user("remote-only", request, SimpleNamespace(id=1))
        self.assertEqual(result.status_code, 204)
        remote.delete_user.assert_awaited_once_with("remote-only")
        session.commit.assert_awaited_once()

    async def test_ctf_delete_with_history_does_not_touch_guacamole(self):
        session, remote, request = request_with_session()
        session.get.return_value = SimpleNamespace(id=20, username="kevin", role="player")
        session.scalar.return_value = 7  # Primera referencia histórica encontrada.
        with self.assertRaises(HTTPException) as error:
            await delete_user(20, request, SimpleNamespace(id=1))
        self.assertEqual(error.exception.status_code, 409)
        self.assertIn("Deshabilítalo", error.exception.detail)
        session.delete.assert_not_awaited()
        remote.delete_user.assert_not_awaited()

    async def test_ctf_delete_sql_failure_rolls_back_before_remote_delete(self):
        session, remote, request = request_with_session()
        session.get.return_value = SimpleNamespace(id=20, username="kevin", role="player")
        session.scalar.return_value = None
        session.flush.side_effect = IntegrityError("DELETE users", {}, RuntimeError("foreign key"))
        with self.assertRaises(HTTPException) as error:
            await delete_user(20, request, SimpleNamespace(id=1))
        self.assertEqual(error.exception.status_code, 409)
        session.rollback.assert_awaited_once()
        remote.list_users.assert_not_awaited()
        remote.delete_user.assert_not_awaited()

    async def test_ctf_delete_guacamole_error_rolls_back_pending_sql(self):
        session, remote, request = request_with_session()
        session.get.return_value = SimpleNamespace(id=20, username="kevin", role="player")
        session.scalar.return_value = None
        remote.list_users.side_effect = GuacamoleApiError("unavailable", status_code=503)
        with self.assertRaises(HTTPException) as error:
            await delete_user(20, request, SimpleNamespace(id=1))
        self.assertEqual(error.exception.status_code, 502)
        session.flush.assert_awaited_once()
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_ctf_delete_succeeds_when_remote_account_already_absent(self):
        session, remote, request = request_with_session()
        session.get.return_value = SimpleNamespace(id=20, username="kevin", role="player")
        session.scalar.return_value = None
        with patch("app.api.users.write_audit", new_callable=AsyncMock):
            result = await delete_user(20, request, SimpleNamespace(id=1))
        self.assertEqual(result.status_code, 204)
        session.flush.assert_awaited_once()
        session.commit.assert_awaited_once()
        remote.delete_user.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
