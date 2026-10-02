"""Preflight de red sin contactar una VM ni revelar credenciales."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.infrastructure.injection.ssh import FlagInjectionError, SSHFlagInjector


class SSHPreflightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            flag_injector_enabled=True,
            flag_injector_ssh_port=22,
            flag_injector_connect_timeout=2,
        )
        with patch("app.infrastructure.injection.ssh.get_settings", return_value=self.settings):
            self.injector = SSHFlagInjector()

    async def test_open_port_succeeds_without_authentication(self):
        writer = SimpleNamespace(close=Mock(), wait_closed=AsyncMock())
        with patch("app.infrastructure.injection.ssh.asyncio.open_connection", new=AsyncMock(return_value=(None, writer))) as connect:
            await self.injector.preflight("192.0.2.14")
        connect.assert_awaited_once_with("192.0.2.14", 22)
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    async def test_unreachable_port_is_redacted(self):
        with patch("app.infrastructure.injection.ssh.asyncio.open_connection", new=AsyncMock(side_effect=OSError("internal route detail"))):
            with self.assertRaises(FlagInjectionError) as raised:
                await self.injector.preflight("192.0.2.14")
        self.assertIn("no acepta SSH", str(raised.exception))
        self.assertNotIn("internal route detail", str(raised.exception))

    async def test_remote_close_after_tcp_handshake_still_counts_as_reachable(self):
        writer = SimpleNamespace(close=Mock(), wait_closed=AsyncMock(side_effect=ConnectionResetError()))
        with patch("app.infrastructure.injection.ssh.asyncio.open_connection", new=AsyncMock(return_value=(None, writer))):
            await self.injector.preflight("192.0.2.14")

    async def test_authentication_probe_uses_read_only_remote_command(self):
        with patch("app.infrastructure.injection.ssh.asyncio.to_thread", new=AsyncMock()) as run:
            await self.injector.probe_authentication("192.0.2.14")
        run.assert_awaited_once_with(self.injector._run_sync, "192.0.2.14", "", None, clear=False, probe_auth=True)


if __name__ == "__main__":
    unittest.main()
