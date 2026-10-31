"""Core 4 (Service request records) and Core 5 (Derived request
status) / SI-10: pinned creation shape, lifecycle, due-date
validation, application linkage, and the overdue derivation --
derived at read, never stored.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import PermissionDenied, ValidationError

REQUEST_KEYS = {"id", "org_id", "system_id", "application_id",
                "request_kind", "summary", "status", "due_date",
                "created_by", "created_utc"}


class TestRequests(unittest.TestCase):
    def test_creation_shape_pinned_and_view_adds_overdue_only(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        stored = store._requests[request["id"]]
        self.assertEqual(set(stored.keys()), REQUEST_KEYS)
        self.assertNotIn("overdue", stored)
        self.assertEqual(request["status"], "open")
        # The creation view derives overdue against the real read
        # clock: the fixture due date (2026-06-10) precedes it, so
        # the open request reads overdue. The pinned as_of cases
        # are in test_overdue_derived_at_read.
        self.assertTrue(request["overdue"])

    def test_due_date_validation(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        for bad in ("06/10/2026", "2026-6-1", "2026-02-30", "soon", 20260610):
            with self.assertRaises(ValidationError):
                H.make_request(store, org, system, due_date=bad)

    def test_invalid_kind_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        with self.assertRaises(ValidationError):
            H.make_request(store, org, system, request_kind="emergency")

    def test_application_linkage_validated(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        request = H.make_request(store, org, system,
                                 application_id=application["id"])
        self.assertEqual(request["application_id"], application["id"])
        other_system = H.make_system(store, org, ref="SYS-OS-2")
        with self.assertRaises(ValidationError):
            H.make_request(store, org, other_system,
                           application_id=application["id"])

    def test_lifecycle_start_and_resolve(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        started = store.start_request(H.MEMBER, request["id"])
        self.assertEqual(started["status"], "in_progress")
        resolved = store.resolve_request(H.STAFF, request["id"])
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["resolved_by"], "erin")
        self.assertIn("resolved_utc", store._requests[request["id"]])
        with self.assertRaises(ValidationError):
            store.resolve_request(H.STAFF, request["id"])

    def test_cancel_restricted_to_requester_or_admin(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        with self.assertRaises(PermissionDenied):
            store.cancel_request(H.STAFF, request["id"])
        cancelled = store.cancel_request(H.MEMBER, request["id"])
        self.assertEqual(cancelled["status"], "cancelled")

    def test_overdue_derived_at_read(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        before = store.get_request(H.MEMBER, request["id"],
                                   as_of=H.AS_OF_BEFORE_DUE)
        self.assertFalse(before["overdue"])
        after = store.get_request(H.MEMBER, request["id"],
                                  as_of=H.AS_OF_AFTER_DUE)
        self.assertTrue(after["overdue"])
        self.assertNotIn("overdue", store._requests[request["id"]])

    def test_resolved_request_is_never_overdue(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        store.resolve_request(H.MEMBER, request["id"])
        view = store.get_request(H.MEMBER, request["id"],
                                 as_of=H.AS_OF_AFTER_DUE)
        self.assertFalse(view["overdue"])

    def test_due_today_is_not_overdue(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        request = H.make_request(store, org, system)
        view = store.get_request(H.MEMBER, request["id"],
                                 as_of=H.REQUEST_DUE_DATE)
        self.assertFalse(view["overdue"])


if __name__ == "__main__":
    unittest.main()
