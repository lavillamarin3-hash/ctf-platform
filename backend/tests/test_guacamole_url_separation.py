"""Garantías de separación entre la API Guacamole interna y su portal web."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.guacamole import ManagedGuacamoleAdapter


def settings(api_url):
    return SimpleNamespace(
        guacamole_api_url=api_url,
        guacamole_base_url="http://10.195.20.22:8080/guacamole",
        guacamole_service_account="ctf_guac_service",
        guacamole_service_password="secret-used-only-in-test",
    )


class GuacamoleUrlTests(unittest.IsolatedAsyncioTestCase):
    def test_internal_api_preferred(self):
        with patch("app.guacamole.get_settings", return_value=settings(
            "http://10.10.10.10:8080/guacamole")):
            adapter = ManagedGuacamoleAdapter()
        self.assertEqual(adapter.base_url, "http://10.10.10.10:8080/guacamole")

    def test_fallback_when_api_unset(self):
        with patch("app.guacamole.get_settings", return_value=settings(None)):
            adapter = ManagedGuacamoleAdapter()
        self.assertEqual(adapter.base_url, "http://10.195.20.22:8080/guacamole")

    async def test_administration_status_only_exposes_browser_url(self):
        with patch("app.guacamole.get_settings", return_value=settings(
                "http://10.10.10.10:8080/guacamole")):
            adapter = ManagedGuacamoleAdapter()
            adapter.list_users = AsyncMock(return_value=[])
            adapter._post_token = AsyncMock(return_value=("hidden-token", "mysql"))
            status = await adapter.status()
        self.assertEqual(status["base_url"], "http://10.195.20.22:8080/guacamole")
        self.assertNotIn("hidden-token", str(status))
        self.assertNotIn("10.10.10.10", str(status))
