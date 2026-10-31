"""Core 6 (Change records) / AC-5, SI-10: pinned creation shape,
separation of duties (the decider is never the requester),
decision/close fields added at transition, and the records-only
close -- closing a change modifies no system or application
record.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import PermissionDenied, ValidationError

CHANGE_KEYS = {"id", "org_id", "system_id", "application_id",
               "change_kind", "summary", "status", "created_by",
               "created_utc"}


class TestChanges(unittest.TestCase):
    def test_creation_shape_pinned(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        self.assertEqual(set(change.keys()), CHANGE_KEYS)
        self.assertEqual(change["status"], "requested")
        self.assertEqual(change["change_kind"], "patch")

    def test_invalid_kind_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        with self.assertRaises(ValidationError):
            H.make_change(store, org, system, change_kind="reboot")

    def test_requester_cannot_decide_own_change(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        with self.assertRaises(PermissionDenied):
            store.decide_change(H.MEMBER, change["id"], True)
        self.assertEqual(store.get_change(H.MEMBER, change["id"])["status"],
                         "requested")

    def test_other_member_decides_and_fields_are_added(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        decided = store.decide_change(H.STAFF, change["id"], True)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "erin")
        self.assertIn("decided_utc", decided)
        with self.assertRaises(ValidationError):
            store.decide_change(H.STAFF, change["id"], True)

    def test_rejection_path(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        decided = store.decide_change(H.STAFF, change["id"], False)
        self.assertEqual(decided["status"], "rejected")
        with self.assertRaises(ValidationError):
            store.close_change(H.MEMBER, change["id"])

    def test_close_approved_change_modifies_no_system_or_application(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        change = H.make_change(store, org, system,
                               application_id=application["id"])
        before_system = dict(store._systems[system["id"]])
        before_application = dict(store._applications[application["id"]])
        store.decide_change(H.STAFF, change["id"], True)
        closed = store.close_change(H.MEMBER, change["id"])
        self.assertEqual(closed["status"], "closed")
        self.assertIn("closed_utc", closed)
        self.assertEqual(store._systems[system["id"]], before_system)
        self.assertEqual(store._applications[application["id"]],
                         before_application)

    def test_cancel_restricted_to_requester_or_admin(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        with self.assertRaises(PermissionDenied):
            store.cancel_change(H.STAFF, change["id"])
        cancelled = store.cancel_change(H.ADMIN, change["id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_approve_must_be_boolean(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        change = H.make_change(store, org, system)
        with self.assertRaises(ValidationError):
            store.decide_change(H.STAFF, change["id"], "yes")


if __name__ == "__main__":
    unittest.main()
