"""Requester records (Core function 2): opaque references ONLY.

Privacy discipline is structural: the record shape has no field that
could hold a phone number, email address or real identifier, and the
suite pins the exact key set so a future field cannot slip in quietly.
"""

import unittest

from custsvc.errors import NotFoundError, ValidationError
from custsvc_helpers import ADMIN, AGENT, VIEWER, make_store


class TestRequesters(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_record_shape_is_exactly_the_privacy_shape(self):
        self.assertEqual(
            set(self.requester.keys()),
            {"id", "ref", "label", "created_utc", "created_by"})
        self.assertTrue(self.requester["id"].startswith("req-"))

    def test_no_contact_fields_exist(self):
        for forbidden in ("phone", "email", "name", "address", "ssn", "contact"):
            self.assertNotIn(forbidden, self.requester)

    def test_get_by_ref(self):
        got = self.store.get_requester_by_ref("citizen-001", VIEWER)
        self.assertEqual(got["id"], self.requester["id"])
        with self.assertRaises(NotFoundError):
            self.store.get_requester_by_ref("nobody", VIEWER)

    def test_duplicate_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_requester("citizen-001", "Duplicate", ADMIN)

    def test_empty_ref_or_label_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_requester("", "Label", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.create_requester("ref-2", "  ", ADMIN)

    def test_viewer_cannot_create(self):
        from custsvc.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.store.create_requester("ref-3", "Nope", VIEWER)


if __name__ == "__main__":
    unittest.main()
