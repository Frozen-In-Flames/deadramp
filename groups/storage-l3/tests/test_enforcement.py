"""Core function 8: enforcement action records. A record changes
nothing outside the store -- in particular an ``extend_retention``
record does not alter the retention derivation, which answers only
to the collection's policy record.
"""

import unittest

from storage.errors import ValidationError

from storage_helpers import (ADMIN, BEFORE_BOUNDARY, OPERATOR, VIEWER,
                             make_archive, make_message, make_store)


class EnforcementTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)

    def test_record_shape_and_kinds(self):
        record = self.store.record_enforcement(
            OPERATOR, "block_export", self.message["message_ref"],
            "POLICY-REF-7", note="matter hold pending review")
        self.assertEqual(record["id"], "enf-1")
        self.assertEqual(record["action"], "block_export")
        for action in ("block_access", "extend_retention",
                       "block_disposition", "flag_for_review"):
            self.store.record_enforcement(OPERATOR, action, "T", "P")
        self.assertEqual(len(self.store.list_enforcements(ADMIN)), 5)
        self.assertEqual(
            len(self.store.list_enforcements(ADMIN, action="block_access")),
            1)

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.store.record_enforcement(OPERATOR, "delete_message",
                                          "T", "P")
        with self.assertRaises(ValidationError):
            self.store.record_enforcement(OPERATOR, "block_access", "", "P")
        with self.assertRaises(ValidationError):
            self.store.list_enforcements(ADMIN, action="delete_message")
        self.assertEqual(self.store.list_enforcements(ADMIN), [])

    def test_enforcement_record_does_not_change_derivation(self):
        self.store.record_enforcement(
            OPERATOR, "extend_retention", self.message["message_ref"],
            "POLICY-REF-7")
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=BEFORE_BOUNDARY)
        self.assertEqual(view["retention_state"], "retained")
        self.assertEqual(view["retention_until"], "2024-01-31T00:00:00+00:00")

    def test_viewer_cannot_enforce(self):
        from storage.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.store.record_enforcement(VIEWER, "block_access", "T", "P")


if __name__ == "__main__":
    unittest.main()
