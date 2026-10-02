"""Autenticación del ranking en vivo sin JWT en URLs, con dobles aislados."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException, WebSocketDisconnect
from fastapi.responses import Response

from app.api import reports


class UserSession:
    def __init__(self, user):
        self.user = user
        self.get = AsyncMock(return_value=user)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class RankingSocketTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(public_origin="http://localhost:8081", access_token_minutes=20)
        self.settings_patch = patch.object(reports, "get_settings", return_value=self.settings)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.rate_patch = patch.object(reports, "check_rate_limit", new=AsyncMock())
        self.rate_patch.start()
        self.addCleanup(self.rate_patch.stop)
        self.user = SimpleNamespace(id=8, is_active=True)
        self.session = UserSession(self.user)
        self.tickets = SimpleNamespace(issue=AsyncMock(return_value="opaque-one-use-ticket"),
                                       consume=AsyncMock(return_value={"run_id": 0, "user_id": self.user.id}))
        self.sockets = SimpleNamespace(connect=AsyncMock(), disconnect=Mock())
        self.app = SimpleNamespace(state=SimpleNamespace(
            terminal_sessions=self.tickets, session_factory=lambda: self.session,
            redis=SimpleNamespace(), sockets=self.sockets,
        ))

    def websocket(self):
        return SimpleNamespace(
            app=self.app, headers={"origin": self.settings.public_origin}, query_params={},
            cookies={"ctf-ranking": "opaque-one-use-ticket"}, close=AsyncMock(),
            send_json=AsyncMock(), receive_text=AsyncMock(side_effect=WebSocketDisconnect()),
        )

    async def test_session_cookie_is_http_only_strict_scoped_and_not_in_response_body(self):
        response = Response()
        result = await reports.ranking_session(SimpleNamespace(app=self.app), response, self.user)
        self.tickets.issue.assert_awaited_once_with(0, self.user.id)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertIn("Path=/api/v1/ws/ranking", cookie)
        self.assertIn("Max-Age=60", cookie)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(set(result), {"websocket_path", "expires_at"})
        self.assertEqual(result["websocket_path"], "/api/v1/ws/ranking")
        self.assertNotIn("ticket", result)
        self.assertNotIn("token", result)

    async def test_https_session_cookie_is_secure(self):
        self.settings.public_origin = "https://ctf.test"
        response = Response()
        await reports.ranking_session(SimpleNamespace(app=self.app), response, self.user)
        self.assertIn("Secure", response.headers["set-cookie"])

    async def test_ticket_infrastructure_error_is_sanitized(self):
        self.tickets.issue.side_effect = RuntimeError("internal credential must stay private")
        with self.assertRaises(HTTPException) as raised:
            await reports.ranking_session(SimpleNamespace(app=self.app), Response(), self.user)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("credential", raised.exception.detail)

    async def test_foreign_origin_is_rejected_before_ticket_consumption(self):
        websocket = self.websocket()
        websocket.headers["origin"] = "https://foreign.test"
        await reports.ranking_socket(websocket)
        websocket.close.assert_awaited_once_with(code=1008)
        self.tickets.consume.assert_not_awaited()
        self.sockets.connect.assert_not_awaited()

    async def test_legacy_jwt_query_is_rejected_even_with_cookie(self):
        websocket = self.websocket()
        websocket.query_params["token"] = "never-place-a-jwt-in-url"
        await reports.ranking_socket(websocket)
        websocket.close.assert_awaited_once_with(code=1008)
        self.tickets.consume.assert_not_awaited()

    async def test_missing_or_replayed_ticket_cannot_join_observer(self):
        self.tickets.consume.return_value = None
        websocket = self.websocket()
        websocket.cookies.clear()
        await reports.ranking_socket(websocket)
        self.tickets.consume.assert_awaited_once_with(None, 0)
        websocket.close.assert_awaited_once_with(code=1008)
        self.sockets.connect.assert_not_awaited()
        self.session.get.assert_not_awaited()

    async def test_inactive_or_removed_user_cannot_open_ranking(self):
        for user in (SimpleNamespace(id=8, is_active=False), None):
            with self.subTest(user_exists=user is not None):
                self.session.get.return_value = user
                websocket = self.websocket()
                await reports.ranking_socket(websocket)
                websocket.close.assert_awaited_once_with(code=1008)
                self.sockets.connect.assert_not_awaited()

    async def test_active_user_receives_initial_ranking_and_disconnect_removes_observer(self):
        websocket = self.websocket()
        rows = [{"position": 1, "username": "student-test", "total_points": 100, "challenges_completed": 1}]
        with patch.object(reports, "ranking_rows", new=AsyncMock(return_value=rows)):
            await reports.ranking_socket(websocket)
        self.tickets.consume.assert_awaited_once_with("opaque-one-use-ticket", 0)
        self.sockets.connect.assert_awaited_once_with(websocket)
        websocket.send_json.assert_awaited_once_with({"type": "ranking.updated", "rows": rows})
        self.sockets.disconnect.assert_called_once_with(websocket)
        websocket.close.assert_awaited_once_with(code=1000)

    async def test_socket_lifetime_is_bounded_by_session_duration(self):
        self.settings.access_token_minutes = 0.0001
        websocket = self.websocket()

        async def wait_for_message():
            await asyncio.Event().wait()

        websocket.receive_text = AsyncMock(side_effect=wait_for_message)
        with patch.object(reports, "ranking_rows", new=AsyncMock(return_value=[])):
            await asyncio.wait_for(reports.ranking_socket(websocket), timeout=1)
        self.sockets.disconnect.assert_called_once_with(websocket)
        websocket.close.assert_awaited_once_with(code=1000)

    async def test_initial_ranking_error_also_removes_observer(self):
        websocket = self.websocket()
        with patch.object(reports, "ranking_rows", new=AsyncMock(side_effect=RuntimeError("Database unavailable"))):
            await reports.ranking_socket(websocket)
        self.sockets.disconnect.assert_called_once_with(websocket)
        websocket.close.assert_any_await(code=1011)


if __name__ == "__main__":
    unittest.main()
