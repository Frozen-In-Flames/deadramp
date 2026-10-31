"""Core functions 7-8: matchmaking round and participation records.

Claim traced: business_matchmaking (records form). A round records
the organizer's required capability tags; a participation records
a vendor's own tags. Tags are normalized caller-stated text.
Participations are immutable, one per vendor per round, and are
recorded only while the round is open.
"""

import unittest

from events.errors import NotFoundError, PermissionDenied, ValidationError

from events_helpers import (ADMIN, MEMBER, VIEWER, make_event,
                            make_organizer, make_round, make_store,
                            make_vendors)


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.event = make_event(self.store, self.organizer)

    def test_create_round_normalizes_tags(self):
        round_ = self.store.create_round(
            MEMBER, self.event["id"], [" Cloud ", "SECURITY", "cloud"])
        self.assertEqual(round_["id"], "rnd-1")
        self.assertEqual(round_["required_tags"], ["cloud", "security"])
        self.assertEqual(round_["status"], "open")

    def test_tags_must_be_a_list_of_strings(self):
        with self.assertRaises(ValidationError):
            self.store.create_round(MEMBER, self.event["id"], "cloud")
        with self.assertRaises(ValidationError):
            self.store.create_round(MEMBER, self.event["id"], ["cloud", 7])
        with self.assertRaises(ValidationError):
            self.store.create_round(MEMBER, self.event["id"], ["  "])
        with self.assertRaises(ValidationError):
            self.store.create_round(MEMBER, self.event["id"], None)

    def test_close_round_lifecycle(self):
        round_ = make_round(self.store, self.event)
        closed = self.store.close_round(ADMIN, round_["id"])
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_round(ADMIN, round_["id"])
        with self.assertRaises(NotFoundError):
            self.store.close_round(ADMIN, "rnd-99")

    def test_viewer_cannot_matchmake(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_round(VIEWER, self.event["id"], ["cloud"])


class ParticipationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.vendors = make_vendors(self.store)
        self.event = make_event(self.store, self.organizer)
        self.round = make_round(self.store, self.event)

    def test_record_participation(self):
        part = self.store.record_participation(
            MEMBER, self.round["id"], self.vendors[0]["id"],
            ["Cloud", "security", "support"])
        self.assertEqual(part["id"], "part-1")
        self.assertEqual(part["capability_tags"],
                         ["cloud", "security", "support"])
        self.assertEqual(part["seq"], 1)

    def test_one_participation_per_vendor_per_round(self):
        self.store.record_participation(
            MEMBER, self.round["id"], self.vendors[0]["id"], ["cloud"])
        with self.assertRaises(ValidationError):
            self.store.record_participation(
                MEMBER, self.round["id"], self.vendors[0]["id"],
                ["security"])
        # The same vendor in a different round is a different record.
        other = make_round(self.store, self.event)
        part = self.store.record_participation(
            MEMBER, other["id"], self.vendors[0]["id"], ["cloud"])
        self.assertEqual(part["round_id"], other["id"])

    def test_participations_only_while_round_open(self):
        self.store.close_round(ADMIN, self.round["id"])
        with self.assertRaises(ValidationError):
            self.store.record_participation(
                MEMBER, self.round["id"], self.vendors[0]["id"], ["cloud"])

    def test_participations_are_immutable(self):
        self.store.record_participation(
            MEMBER, self.round["id"], self.vendors[0]["id"], ["cloud"])
        self.assertFalse(hasattr(self.store, "update_participation"))
        self.assertFalse(hasattr(self.store, "delete_participation"))
        listed = self.store.list_participations(VIEWER, self.round["id"])
        listed[0]["capability_tags"].append("forged")
        again = self.store.list_participations(VIEWER, self.round["id"])
        self.assertEqual(again[0]["capability_tags"], ["cloud"])

    def test_list_is_in_sequence_order(self):
        for vendor in reversed(self.vendors):
            self.store.record_participation(
                MEMBER, self.round["id"], vendor["id"], ["cloud"])
        listed = self.store.list_participations(VIEWER, self.round["id"])
        self.assertEqual([p["seq"] for p in listed], [1, 2, 3])
        self.assertEqual(listed[0]["vendor_id"], self.vendors[2]["id"])


if __name__ == "__main__":
    unittest.main()
