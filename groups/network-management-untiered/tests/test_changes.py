"""Core function 4: configuration change records -- lifecycle,
AC-5 separation of duties, and the pin that closing a change
modifies no device or network record.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import PermissionDenied, ValidationError

CREATION_KEYS = {"id", "org_id", "network_id", "device_id",
                 "change_kind", "summary", "status", "created_by",
                 "created_utc"}


class TestChanges(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.network, self.device = H.make_estate(self.store, self.org)

    def test_create_shape_at_creation(self):
        change = H.make_change(self.store, self.org, self.network,
                               device_id=self.device["id"])
        self.assertEqual(set(change.keys()), CREATION_KEYS)
        self.assertTrue(change["id"].startswith("chg-"))
        self.assertEqual(change["status"], "requested")
        stored = self.store._changes[change["id"]]
        self.assertEqual(set(stored.keys()), CREATION_KEYS)

    def test_invalid_kind_and_cross_network_device_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_change(self.store, self.org, self.network,
                          change_kind="restart")
        other_network = H.make_network(
            self.store, self.org, ref="NET-BR", label="Branch",
            site_ref="SITE-BR")
        with self.assertRaises(ValidationError):
            H.make_change(self.store, self.org, other_network,
                          device_id=self.device["id"])

    def test_decide_approve_adds_decision_fields(self):
        change = H.make_change(self.store, self.org, self.network)
        decided = self.store.decide_change(H.STAFF, change["id"], True)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "erin")
        self.assertIsNotNone(decided["decided_utc"])

    def test_decider_is_never_the_requester(self):
        change = H.make_change(self.store, self.org, self.network)
        with self.assertRaises(PermissionDenied):
            self.store.decide_change(H.MEMBER, change["id"], True)
        # The failed decision changed nothing.
        view = self.store.get_change(H.MEMBER, change["id"])
        self.assertEqual(view["status"], "requested")
        self.assertNotIn("decided_by", view)

    def test_reject_and_non_boolean_decision(self):
        change = H.make_change(self.store, self.org, self.network)
        with self.assertRaises(ValidationError):
            self.store.decide_change(H.STAFF, change["id"], "yes")
        decided = self.store.decide_change(H.STAFF, change["id"], False)
        self.assertEqual(decided["status"], "rejected")
        with self.assertRaises(ValidationError):
            self.store.decide_change(H.STAFF, change["id"], True)

    def test_close_approved_change_modifies_no_device_or_network(self):
        change = H.make_change(self.store, self.org, self.network,
                               device_id=self.device["id"])
        device_before = dict(self.store._devices[self.device["id"]])
        network_before = dict(self.store._networks[self.network["id"]])
        self.store.decide_change(H.STAFF, change["id"], True)
        closed = self.store.close_change(H.MEMBER, change["id"])
        self.assertEqual(closed["status"], "closed")
        self.assertIsNotNone(closed["closed_utc"])
        self.assertEqual(dict(self.store._devices[self.device["id"]]),
                         device_before)
        self.assertEqual(dict(self.store._networks[self.network["id"]]),
                         network_before)

    def test_close_requires_approved(self):
        change = H.make_change(self.store, self.org, self.network)
        with self.assertRaises(ValidationError):
            self.store.close_change(H.MEMBER, change["id"])

    def test_cancel_by_requester(self):
        change = H.make_change(self.store, self.org, self.network)
        cancelled = self.store.cancel_change(H.MEMBER, change["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        with self.assertRaises(ValidationError):
            self.store.cancel_change(H.MEMBER, change["id"])

    def test_cancel_by_non_requester_member_denied_but_admin_allowed(self):
        change = H.make_change(self.store, self.org, self.network)
        with self.assertRaises(PermissionDenied):
            self.store.cancel_change(H.STAFF, change["id"])
        cancelled = self.store.cancel_change(H.ADMIN, change["id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_list_changes_filtered_by_status(self):
        first = H.make_change(self.store, self.org, self.network)
        H.make_change(self.store, self.org, self.network,
                      summary="Second change")
        self.store.decide_change(H.STAFF, first["id"], True)
        approved = self.store.list_changes(H.MEMBER, self.org["id"],
                                           status="approved")
        self.assertEqual([c["id"] for c in approved], [first["id"]])
        self.assertEqual(
            len(self.store.list_changes(H.MEMBER, self.org["id"])), 2)


if __name__ == "__main__":
    unittest.main()
