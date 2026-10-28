"""Regression tests for group POST registration and optional learning policies."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.api.groups import router as groups_router
from app.schemas import LearningPolicy
from app.services.learning import expired


class GroupRoutingTests(unittest.TestCase):
    def test_group_creation_has_post_route(self):
        routes = [(r.path, getattr(r, "methods", set())) for r in groups_router.routes]
        self.assertTrue(any(path == "/api/v1/groups" and "POST" in methods
                            for path, methods in routes))


class OptionalLearningTests(unittest.TestCase):
    def test_disabled_timer_without_hints_is_supported(self):
        policy = LearningPolicy.model_validate({
            "duration_minutes": 60, "timer_enabled": False,
            "expired_points_percent": 25, "hints": [],
        })
        self.assertFalse(policy.timer_enabled)
        self.assertEqual(policy.hints, [])

    def test_timer_is_opt_out_and_does_not_reveal_expired_solution(self):
        deadline = datetime.now(timezone.utc) - timedelta(minutes=1)
        with_clock = SimpleNamespace(deadline=deadline,
                                     policy_snapshot={"timer_enabled": True})
        without_clock = SimpleNamespace(deadline=deadline,
                                        policy_snapshot={"timer_enabled": False})
        self.assertTrue(expired(with_clock))
        self.assertFalse(expired(without_clock))
