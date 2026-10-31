"""Core function 6: vendor outreach records.

Claim traced: vendor_outreach. An outreach is a record, never a
sent message -- delivery transport is Extended. The organizer may
only record outreach about its own events (cross-organizer guard).
"""

import unittest

from events.errors import NotFoundError, PermissionDenied, ValidationError

from events_helpers import (ADMIN, MEMBER, VIEWER, make_event,
                            make_organizer, make_store, make_vendors)


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.vendors = make_vendors(self.store)
        self.event = make_event(self.store, self.organizer)

    def test_record_outreach(self):
        outreach = self.store.record_outreach(
            MEMBER, self.organizer["id"], self.vendors[0]["id"],
            self.event["id"], "portal", "Invitation: Spring Vendor Day")
        self.assertEqual(outreach["id"], "out-1")
        self.assertEqual(outreach["subject"],
                         "Invitation: Spring Vendor Day")
        self.assertNotIn("sent", outreach)
        self.assertNotIn("delivered", outreach)

    def test_event_must_belong_to_organizer(self):
        other = self.store.create_organizer(ADMIN, "ORG-0002", "Other")
        with self.assertRaises(ValidationError):
            self.store.record_outreach(
                MEMBER, other["id"], self.vendors[0]["id"],
                self.event["id"], "portal", "Not your event")

    def test_unknown_parties_rejected(self):
        with self.assertRaises(NotFoundError):
            self.store.record_outreach(
                MEMBER, self.organizer["id"], "ven-99", self.event["id"],
                "portal", "Hello")
        with self.assertRaises(ValidationError):
            self.store.record_outreach(
                MEMBER, self.organizer["id"], self.vendors[0]["id"],
                self.event["id"], "", "Hello")

    def test_viewer_cannot_record_outreach(self):
        with self.assertRaises(PermissionDenied):
            self.store.record_outreach(
                VIEWER, self.organizer["id"], self.vendors[0]["id"],
                self.event["id"], "portal", "Hello")

    def test_list_filters(self):
        self.store.record_outreach(
            MEMBER, self.organizer["id"], self.vendors[0]["id"],
            self.event["id"], "portal", "One")
        self.store.record_outreach(
            MEMBER, self.organizer["id"], self.vendors[1]["id"],
            self.event["id"], "portal", "Two")
        self.assertEqual(len(self.store.list_outreach(VIEWER)), 2)
        self.assertEqual(
            len(self.store.list_outreach(
                VIEWER, vendor_id=self.vendors[1]["id"])), 1)


if __name__ == "__main__":
    unittest.main()
