"""Core: Communications records — messages, notifications, and
internal notes. Traces to UNION-SPEC core function 9
(messaging_communications, system_notifications, internal_notes).
Internal notes are internal: a read-only role cannot read them even
when it is a program member."""

import unittest

import grants_helpers as H
from grants.errors import PermissionDenied, ValidationError


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_message_records_both_directions(self):
        self.store.create_message(H.MEMBER, self.program["id"],
                                  self.org["id"], "inbound",
                                  "Question about the deadline")
        self.store.create_message(H.MEMBER, self.program["id"],
                                  self.org["id"], "outbound",
                                  "Deadline is March 1")
        messages = self.store.list_messages(H.MEMBER, self.program["id"])
        self.assertEqual([m["direction"] for m in messages],
                         ["inbound", "outbound"])

    def test_bad_direction_and_empty_body(self):
        with self.assertRaises(ValidationError):
            self.store.create_message(H.MEMBER, self.program["id"],
                                      self.org["id"], "sideways", "hi")
        with self.assertRaises(ValidationError):
            self.store.create_message(H.MEMBER, self.program["id"],
                                      self.org["id"], "inbound", " ")

    def test_filter_by_org(self):
        other = self.store.create_organization(H.MEMBER, "ORG-200", "Beta")
        self.store.create_message(H.MEMBER, self.program["id"],
                                  self.org["id"], "inbound", "one")
        self.store.create_message(H.MEMBER, self.program["id"],
                                  other["id"], "inbound", "two")
        mine = self.store.list_messages(H.MEMBER, self.program["id"],
                                        org_id=self.org["id"])
        self.assertEqual(len(mine), 1)


class TestNotes(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()
        self.app = H.make_application(self.store, self.program, self.org)

    def test_note_roundtrip(self):
        note = self.store.create_note(H.STAFF, self.app["id"],
                                      "Verify fiscal sponsorship")
        self.assertTrue(note["id"].startswith("note-"))
        notes = self.store.list_notes(H.MEMBER, self.app["id"])
        self.assertEqual(notes[0]["body"], "Verify fiscal sponsorship")

    def test_notes_stay_internal_for_read_only_members(self):
        self.store.create_note(H.STAFF, self.app["id"], "internal only")
        self.store.add_member(H.ADMIN, self.program["id"], H.VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.store.list_notes(H.VIEWER, self.app["id"])
        with self.assertRaises(PermissionDenied):
            self.store.create_note(H.VIEWER, self.app["id"], "sneaky")


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_notification_records(self):
        targeted = self.store.create_notification(
            H.MEMBER, self.program["id"], self.org["id"],
            "Your report is due Sept 30")
        self.assertTrue(targeted["id"].startswith("ntf-"))
        self.store.create_notification(
            H.MEMBER, self.program["id"], None, "Program window closes Dec 31")
        notes = self.store.list_notifications(H.MEMBER, self.program["id"])
        self.assertEqual(len(notes), 2)
        self.assertIsNone(notes[1]["org_id"])


if __name__ == "__main__":
    unittest.main()
