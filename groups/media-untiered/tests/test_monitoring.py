"""Status snapshots and derived status views (core function 8):
current status is the most recently recorded snapshot's word,
derived at read, never stored."""

import unittest

from media_helpers import (ADMIN, AT, OPERATOR, VIEWER, make_device,
                           make_org, make_route, make_store)

from media.errors import NotFoundError, ValidationError

LATER = "2026-01-10T12:00:00+00:00"


class SnapshotTests(unittest.TestCase):
    def test_snapshot_shape_and_vocabularies(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        snap = store.record_status_snapshot(
            OPERATOR, "route", route["id"], "up", at=AT)
        self.assertEqual(snap["status"], "up")
        with self.assertRaises(ValidationError):
            store.record_status_snapshot(OPERATOR, "route", route["id"],
                                         "flaky")
        with self.assertRaises(ValidationError):
            store.record_status_snapshot(OPERATOR, "satellite",
                                         route["id"], "up")
        with self.assertRaises(NotFoundError):
            store.record_status_snapshot(OPERATOR, "route", "rou-99",
                                         "up")

    def test_current_status_is_none_without_snapshots(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        result = store.current_status(VIEWER, "route", route["id"])
        self.assertIsNone(result["status"])
        self.assertIsNone(result["snapshot_id"])

    def test_current_status_follows_recording_order(self):
        """The derivation reads recording order in the store, not
        the caller's timestamps: a later-recorded snapshot wins
        even when its stated moment is earlier."""
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        store.record_status_snapshot(OPERATOR, "route", route["id"],
                                     "down", at=LATER)
        store.record_status_snapshot(OPERATOR, "route", route["id"],
                                     "up", at=AT)
        result = store.current_status(VIEWER, "route", route["id"])
        self.assertEqual(result["status"], "up")

    def test_device_subjects_have_their_own_status(self):
        store, _audit = make_store()
        org = make_org(store)
        device = make_device(store, org)
        store.record_status_snapshot(OPERATOR, "device", device["id"],
                                     "degraded", at=AT)
        result = store.current_status(VIEWER, "device", device["id"])
        self.assertEqual(result["status"], "degraded")

    def test_network_status_view(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        store.record_status_snapshot(OPERATOR, "route", route["id"],
                                     "up", at=AT)
        session = store.start_session(OPERATOR, route["id"])
        view = store.network_status(VIEWER, org["id"])
        self.assertEqual(view["routes_by_state"], {"idle": 0, "live": 1})
        self.assertEqual(view["routes_by_status"]["up"], 1)
        self.assertEqual(view["routes_unreported"], 0)
        self.assertEqual(view["routes"][0]["status"], "up")
        self.assertEqual(view["routes"][0]["state"], "live")
        store.stop_session(OPERATOR, session["id"])
        with self.assertRaises(NotFoundError):
            store.network_status(VIEWER, "org-99")


if __name__ == "__main__":
    unittest.main()
