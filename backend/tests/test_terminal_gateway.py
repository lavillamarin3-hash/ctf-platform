"""Terminal authorization and cookie regressions; no external systems contacted."""

from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.responses import Response

from app.api import terminal
from app.core import now_utc
from app.domain.instances.states import InstanceState
from app.models import Challenge, ChallengeRun, User, VMAsset


class MemorySession:
    def __init__(self, user, run, challenge, instance):
        self.objects = {User: user, ChallengeRun: run, Challenge: challenge}
        self.instance = instance

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, model, identifier):
        return self.objects.get(model)

    async def scalar(self, statement):
        return self.instance


class TerminalAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, username="student-fixture", role="player", is_active=True)
        self.run = SimpleNamespace(id=101, user_id=7, challenge_id=11, status="active", expires_at=now_utc() + timedelta(minutes=20))
        self.challenge = SimpleNamespace(id=11, is_published=True)
        self.instance = SimpleNamespace(user_id=7, state=InstanceState.IN_USE.value, guacamole_connection_id="reserved-fixture-id")
        self.session = MemorySession(self.user, self.run, self.challenge, self.instance)
        self.app = SimpleNamespace(state=SimpleNamespace(session_factory=lambda: self.session))

    async def test_target_comes_from_reserved_instance(self):
        with patch.object(terminal, "_assigned", AsyncMock(return_value=True)):
            connection_id, expires_at, username = await terminal.authorized_target(self.app, 101, 7)
        self.assertEqual(connection_id, "reserved-fixture-id")
        self.assertEqual(expires_at, self.run.expires_at)
        self.assertEqual(username, self.user.username)

    async def test_other_owner_and_inactive_or_nonplayer_are_rejected(self):
        for mutation in (
            lambda: setattr(self.run, "user_id", 8),
            lambda: setattr(self.user, "is_active", False),
            lambda: setattr(self.user, "role", "admin"),
        ):
            with self.subTest(mutation=mutation):
                self.setUp()
                mutation()
                with self.assertRaises(HTTPException) as raised:
                    await terminal.authorized_target(self.app, 101, 7)
                self.assertEqual(raised.exception.status_code, 404)

    async def test_closed_and_expired_runs_are_rejected(self):
        for status, expiry in (("closed", now_utc() + timedelta(minutes=1)), ("active", now_utc() - timedelta(seconds=1))):
            with self.subTest(status=status):
                self.run.status, self.run.expires_at = status, expiry
                with self.assertRaises(HTTPException) as raised:
                    await terminal.authorized_target(self.app, 101, 7)
                self.assertEqual(raised.exception.status_code, 409)

    async def test_unpublished_or_unassigned_challenge_is_rejected(self):
        with patch.object(terminal, "_assigned", AsyncMock(return_value=False)):
            with self.assertRaises(HTTPException) as raised:
                await terminal.authorized_target(self.app, 101, 7)
            self.assertEqual(raised.exception.status_code, 403)
        self.challenge.is_published = False
        with self.assertRaises(HTTPException) as raised:
            await terminal.authorized_target(self.app, 101, 7)
        self.assertEqual(raised.exception.status_code, 403)

    async def test_unavailable_instance_is_rejected(self):
        for mutation in (
            lambda: setattr(self.instance, "user_id", 8),
            lambda: setattr(self.instance, "state", "available"),
            lambda: setattr(self.instance, "guacamole_connection_id", None),
        ):
            with self.subTest(mutation=mutation):
                self.setUp()
                mutation()
                with patch.object(terminal, "_assigned", AsyncMock(return_value=True)):
                    with self.assertRaises(HTTPException) as raised:
                        await terminal.authorized_target(self.app, 101, 7)
                self.assertEqual(raised.exception.status_code, 409)

    async def test_legacy_target_resolution_uses_application_request_adapter(self):
        self.session.instance = None
        vm = SimpleNamespace(id=71)
        resolve = AsyncMock(return_value=SimpleNamespace(identifier="legacy-fixture-id"))
        with patch.object(terminal, "_assigned", AsyncMock(return_value=True)), patch.object(terminal, "_find_challenge_vm", AsyncMock(return_value=(None, vm))), patch.object(terminal, "_resolve_guacamole_connection", resolve):
            target = await terminal.authorized_target(self.app, 101, 7)
        self.assertEqual(target[0], "legacy-fixture-id")
        self.assertIs(resolve.call_args.args[0].app, self.app)
        self.assertIs(resolve.call_args.args[1], vm)

    async def test_rdp_choice_is_limited_to_reserved_vm_host(self):
        self.instance.vm_asset_id = 71
        self.session.objects[VMAsset] = SimpleNamespace(id=71, ip_address="10.20.30.40")
        connections = [
            SimpleNamespace(identifier="reserved-fixture-id", protocol="ssh", hostname="10.20.30.40"),
            SimpleNamespace(identifier="rdp-same-vm", protocol="rdp", hostname="10.20.30.40"),
            SimpleNamespace(identifier="rdp-other-vm", protocol="rdp", hostname="10.20.30.41"),
        ]
        self.app.state.guacamole_admin = SimpleNamespace(list_connections=AsyncMock(return_value=connections))
        with patch.object(terminal, "_assigned", AsyncMock(return_value=True)):
            connection_id, _, _ = await terminal.authorized_target(self.app, 101, 7, "rdp")
            options = await terminal.terminal_options(101, SimpleNamespace(app=self.app), self.user)
        self.assertEqual(connection_id, "rdp-same-vm")
        self.assertEqual(options, {"protocols": ["ssh", "rdp"]})

    async def test_unconfigured_protocol_does_not_fall_back_to_other_vm(self):
        self.instance.vm_asset_id = 71
        self.session.objects[VMAsset] = SimpleNamespace(id=71, ip_address="10.20.30.40")
        self.app.state.guacamole_admin = SimpleNamespace(list_connections=AsyncMock(return_value=[
            SimpleNamespace(identifier="reserved-fixture-id", protocol="ssh", hostname="10.20.30.40"),
            SimpleNamespace(identifier="rdp-other-vm", protocol="rdp", hostname="10.20.30.41"),
        ]))
        with patch.object(terminal, "_assigned", AsyncMock(return_value=True)):
            with self.assertRaises(HTTPException) as raised:
                await terminal.authorized_target(self.app, 101, 7, "rdp")
        self.assertEqual(raised.exception.status_code, 409)


class TerminalCookieTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sessions = SimpleNamespace(get_user=AsyncMock(return_value={"username": "student-fixture"}), issue=AsyncMock(return_value="fixture-one-use-ticket"))
        self.user = SimpleNamespace(id=7, username="student-fixture")
        self.app = SimpleNamespace(state=SimpleNamespace(redis=object(), terminal_sessions=self.sessions))
        self.request = SimpleNamespace(app=self.app)
        self.target = AsyncMock(return_value=("fixture-id", now_utc() + timedelta(minutes=10), self.user.username))

    async def call_session(self, response, origin="https://ctf.example.invalid", selection=None):
        with patch.object(terminal, "authorized_target", self.target), patch.object(terminal, "check_rate_limit", AsyncMock()), patch.object(terminal, "get_settings", return_value=SimpleNamespace(public_origin=origin)):
            return await terminal.terminal_session(101, self.request, response, self.user, selection)

    async def test_secure_httponly_ticket_scoped_to_run_and_no_secret_in_payload(self):
        response = Response()
        payload = await self.call_session(response)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertIn("Max-Age=60", cookie)
        self.assertIn("Path=/api/v1/runs/101/terminal", cookie)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(set(payload), {"websocket_path", "expires_at"})
        self.assertEqual(payload["websocket_path"], "/api/v1/runs/101/terminal/ws")
        self.assertNotIn("ticket", payload)
        self.assertNotIn("token", payload)
        self.sessions.issue.assert_awaited_once_with(101, 7)

    async def test_local_http_cookie_is_still_httponly_and_strict(self):
        response = Response()
        await self.call_session(response, "http://localhost:8081")
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=strict", response.headers["set-cookie"])
        self.assertNotIn("Secure", response.headers["set-cookie"])

    async def test_missing_delegated_login_does_not_issue_ticket(self):
        self.sessions.get_user.return_value = None
        with self.assertRaises(HTTPException) as raised:
            await self.call_session(Response())
        self.assertEqual(raised.exception.status_code, 428)
        self.sessions.issue.assert_not_awaited()

    async def test_closing_run_does_not_issue_successful_session(self):
        self.sessions.issue.side_effect = ValueError("closing")
        with self.assertRaises(HTTPException) as raised:
            await self.call_session(Response())
        self.assertEqual(raised.exception.status_code, 409)

    async def test_protocol_choice_is_bound_to_one_use_ticket(self):
        await self.call_session(Response(), selection=terminal.TerminalSelection(protocol="rdp"))
        self.target.assert_awaited_once_with(self.app, 101, 7, "rdp")
        self.sessions.issue.assert_awaited_once_with(101, 7, "rdp")


class TunnelURLTests(unittest.TestCase):
    def test_destination_and_token_cannot_be_overridden_by_browser_query(self):
        delegated = {"token": "fixture-upstream-token", "data_source": "postgresql"}
        result = terminal.tunnel_url("https://guacamole.example.invalid/guacamole/", delegated, "reserved-id", {"width": "999999", "height": "1", "GUAC_ID": "attacker-id", "token": "attacker-token"})
        parts = urlsplit(result)
        query = parse_qs(parts.query)
        self.assertEqual(parts.scheme, "wss")
        self.assertEqual(parts.path, "/guacamole/websocket-tunnel")
        self.assertEqual(query["GUAC_ID"], ["reserved-id"])
        self.assertEqual(query["token"], ["fixture-upstream-token"])
        self.assertEqual(query["GUAC_WIDTH"], ["3840"])
        self.assertEqual(query["GUAC_HEIGHT"], ["240"])

    def test_unsupported_scheme_and_embedded_credentials_are_rejected(self):
        for url in ("file:///tmp/guacamole", "ftp://guacamole.example.invalid", "https://user:password@guacamole.example.invalid"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                terminal.tunnel_url(url, {"token": "fixture", "data_source": "fixture"}, "id", {})


class WebSocketGateTests(unittest.IsolatedAsyncioTestCase):
    def make_socket(self, origin):
        sessions = SimpleNamespace(consume=AsyncMock(return_value=None))
        app = SimpleNamespace(state=SimpleNamespace(terminal_sessions=sessions))
        socket = SimpleNamespace(headers={"origin": origin}, app=app, cookies={}, query_params={"token": "ignored-fixture"}, close=AsyncMock())
        return socket, sessions

    async def test_cross_origin_is_rejected_before_consuming_ticket(self):
        socket, sessions = self.make_socket("https://external.example.invalid")
        with patch.object(terminal, "get_settings", return_value=SimpleNamespace(public_origin="https://ctf.example.invalid")):
            await terminal.terminal_websocket(101, socket)
        socket.close.assert_awaited_once_with(code=1008)
        sessions.consume.assert_not_awaited()

    async def test_url_token_without_httponly_cookie_is_rejected(self):
        socket, sessions = self.make_socket("https://ctf.example.invalid")
        with patch.object(terminal, "get_settings", return_value=SimpleNamespace(public_origin="https://ctf.example.invalid")), patch.object(terminal, "connect") as upstream:
            await terminal.terminal_websocket(101, socket)
        sessions.consume.assert_awaited_once_with(None, 101)
        upstream.assert_not_called()
        self.assertEqual(socket.close.await_args_list[0].kwargs["code"], 1008)

    async def test_delegated_user_mismatch_is_rejected_before_upstream(self):
        socket, sessions = self.make_socket("https://ctf.example.invalid")
        sessions.consume.return_value = {"user_id": 7}
        sessions.get_user = AsyncMock(return_value={"username": "other-fixture", "token": "fixture", "data_source": "fixture"})
        with patch.object(terminal, "get_settings", return_value=SimpleNamespace(public_origin="https://ctf.example.invalid")), patch.object(terminal, "authorized_target", AsyncMock(return_value=("reserved-id", now_utc(), "student-fixture"))), patch.object(terminal, "connect") as upstream:
            await terminal.terminal_websocket(101, socket)
        upstream.assert_not_called()
        self.assertEqual(socket.close.await_args_list[0].kwargs["code"], 1008)

    async def test_websocket_revalidates_protocol_from_ticket_not_query_string(self):
        socket, sessions = self.make_socket("https://ctf.example.invalid")
        sessions.consume.return_value = {"user_id": 7, "protocol": "rdp"}
        sessions.get_user = AsyncMock(return_value={"username": "student-fixture", "token": "fixture", "data_source": "fixture"})
        target = AsyncMock(return_value=("rdp-same-vm", now_utc(), "student-fixture"))
        with patch.object(terminal, "get_settings", return_value=SimpleNamespace(public_origin="https://ctf.example.invalid")), patch.object(terminal, "authorized_target", target), patch.object(terminal, "tunnel_url", side_effect=ValueError("stop before upstream")):
            await terminal.terminal_websocket(101, socket)
        target.assert_awaited_once_with(socket.app, 101, 7, "rdp")
        self.assertEqual(socket.close.await_args_list[0].kwargs["code"], 1011)


if __name__ == "__main__":
    unittest.main()
