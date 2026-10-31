"""Pinned record shapes: a recursive scan over a fully populated
store proves no forbidden key exists anywhere — no field can
hold media content, a score, money, or a real identifier."""

import unittest

from media_helpers import (ADMIN, AT, OPERATOR, STARTED, STOPPED,
                           make_device, make_org, make_route,
                           make_store)

FORBIDDEN_KEY_PARTS = (
    "score", "grade", "rank", "email", "payload", "video", "audio",
    "ssn", "password", "secret", "price", "money", "cents",
    "latency", "bitrate",
)


def walk_keys(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            walk_keys(value, found)
    elif isinstance(node, list):
        for item in node:
            walk_keys(item, found)


class ShapeTests(unittest.TestCase):
    def _populated(self):
        store, _audit = make_store()
        org = make_org(store)
        route, source, _d = make_route(store, org)
        session = store.start_session(OPERATOR, route["id"],
                                      started_at=STARTED)
        store.stop_session(OPERATOR, session["id"], stopped_at=STOPPED)
        store.start_session(OPERATOR, route["id"])
        device = make_device(store, org, endpoint=source)
        store.record_control_action(OPERATOR, device["id"], "start",
                                    note="begin", at=AT)
        store.create_optimization_profile(
            OPERATOR, org["id"], "profile", "mode=ll",
            route_id=route["id"])
        store.record_status_snapshot(OPERATOR, "route", route["id"],
                                     "up", at=AT)
        return store, org

    def test_no_forbidden_key_anywhere(self):
        store, org = self._populated()
        found = set()
        walk_keys(store.list_organizations(ADMIN), found)
        walk_keys(store.list_endpoints(ADMIN), found)
        walk_keys(store.list_routes(ADMIN), found)
        walk_keys(store.list_sessions(ADMIN), found)
        walk_keys(store.list_devices(ADMIN), found)
        walk_keys(store.list_control_actions(ADMIN), found)
        walk_keys(store.list_profiles(ADMIN), found)
        walk_keys(store.list_snapshots(ADMIN), found)
        # Per-route status view entries are records; the aggregate
        # count maps keyed by vocabulary words are covered by the
        # counts-only test below, not by this field scan.
        walk_keys(store.network_status(ADMIN, org["id"])["routes"],
                  found)
        walk_keys(store.search(ADMIN, "ORG"), found)
        for key in found:
            for part in FORBIDDEN_KEY_PARTS:
                self.assertNotIn(part, key.lower(),
                                 "forbidden key part %r in key %r"
                                 % (part, key))

    def test_summary_is_counts_only(self):
        store, _org = self._populated()
        summary = store.summary(ADMIN)
        for value in summary.values():
            if isinstance(value, dict):
                for inner in value.values():
                    self.assertIsInstance(inner, int)
            else:
                self.assertIsInstance(value, int)


if __name__ == "__main__":
    unittest.main()
