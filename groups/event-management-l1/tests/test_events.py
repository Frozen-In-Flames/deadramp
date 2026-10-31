"""Core functions 3-4: event records and preparation task records.

Claims traced: event_preparation, conference_management,
event_formats. An event's status (upcoming / live / concluded) is
derived at read from its recorded window and never stored -- the
stored record's key set is pinned to prove it (CM-6, AU-2/AU-3 Low
side).
"""

import unittest

from events.errors import NotFoundError, PermissionDenied, ValidationError

from events_helpers import (AFTER, BEFORE, DURING, ENDS, STARTS, ADMIN,
                            MEMBER, VIEWER, make_event, make_organizer,
                            make_store)

EVENT_KEYS = {"id", "organizer_id", "title", "format", "starts_at",
              "ends_at", "location_note", "created_by", "created_utc"}


class EventTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)

    def test_create_event_view(self):
        event = make_event(self.store, self.organizer)
        self.assertEqual(event["id"], "evt-1")
        self.assertEqual(event["format"], "hybrid")
        self.assertIn("status", event)  # derived view field; see below
        self.assertEqual(event["session_count"], 0)
        self.assertEqual(event["round_count"], 0)

    def test_status_is_derived_never_stored(self):
        event = make_event(self.store, self.organizer)
        stored = self.store._events[event["id"]]
        self.assertEqual(set(stored), EVENT_KEYS)
        self.assertNotIn("status", stored)
        self.assertEqual(
            self.store.get_event(ADMIN, event["id"], now=BEFORE)["status"],
            "upcoming")
        self.assertEqual(
            self.store.get_event(ADMIN, event["id"], now=DURING)["status"],
            "live")
        self.assertEqual(
            self.store.get_event(ADMIN, event["id"], now=AFTER)["status"],
            "concluded")

    def test_all_claimed_formats_accepted(self):
        for fmt in ("onsite", "hybrid", "virtual"):
            event = self.store.create_event(
                MEMBER, self.organizer["id"], "Day " + fmt, fmt,
                STARTS, ENDS)
            self.assertEqual(event["format"], fmt)

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_event(MEMBER, self.organizer["id"], "X",
                                    "telepathic", STARTS, ENDS)

    def test_window_must_not_run_backwards(self):
        with self.assertRaises(ValidationError):
            self.store.create_event(MEMBER, self.organizer["id"], "X",
                                    "onsite", ENDS, STARTS)

    def test_unknown_organizer_rejected(self):
        with self.assertRaises(NotFoundError):
            self.store.create_event(MEMBER, "org-99", "X", "onsite",
                                    STARTS, ENDS)

    def test_viewer_cannot_create_events(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_event(VIEWER, self.organizer["id"], "X",
                                    "onsite", STARTS, ENDS)

    def test_list_filters(self):
        make_event(self.store, self.organizer)
        self.store.create_event(MEMBER, self.organizer["id"], "Virtual Day",
                                "virtual", STARTS, ENDS)
        self.assertEqual(len(self.store.list_events(VIEWER)), 2)
        self.assertEqual(
            len(self.store.list_events(VIEWER, format="virtual")), 1)
        self.assertEqual(
            len(self.store.list_events(VIEWER, status="live", now=DURING)),
            2)
        self.assertEqual(
            len(self.store.list_events(VIEWER, status="concluded",
                                       now=DURING)), 0)
        with self.assertRaises(ValidationError):
            self.store.list_events(VIEWER, format="smoke-signal")


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.event = make_event(self.store, self.organizer)

    def test_task_lifecycle(self):
        task = self.store.add_preparation_task(
            MEMBER, self.event["id"], "Confirm room booking")
        self.assertEqual(task["id"], "prep-1")
        self.assertFalse(task["done"])
        done = self.store.complete_preparation_task(ADMIN, task["id"])
        self.assertTrue(done["done"])
        with self.assertRaises(ValidationError):
            self.store.complete_preparation_task(ADMIN, task["id"])

    def test_tasks_are_per_event_and_filterable(self):
        self.store.add_preparation_task(MEMBER, self.event["id"], "A")
        task_b = self.store.add_preparation_task(MEMBER, self.event["id"], "B")
        self.store.complete_preparation_task(MEMBER, task_b["id"])
        self.assertEqual(
            len(self.store.list_preparation_tasks(VIEWER, self.event["id"])),
            2)
        self.assertEqual(
            len(self.store.list_preparation_tasks(
                VIEWER, self.event["id"], done=False)), 1)
        with self.assertRaises(NotFoundError):
            self.store.list_preparation_tasks(VIEWER, "evt-99")
        with self.assertRaises(NotFoundError):
            self.store.complete_preparation_task(ADMIN, "prep-99")


if __name__ == "__main__":
    unittest.main()
