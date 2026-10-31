"""Core function 6: discovery request records and metadata search
scope -- a recorded matter, collection, and optional sender/date
scope, with the result set computed from the archive records.
There is no free-text query field on the record, by design.
"""

import unittest

from storage.errors import ValidationError

from storage_helpers import (ADMIN, OPERATOR, VIEWER, make_archive,
                             make_message, make_store)

DISCOVERY_KEYS = {"id", "matter_ref", "collection_id", "sender_ref",
                  "from_at", "to_at", "result_count", "result_message_ids",
                  "created_by", "created_utc"}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.first = make_message(self.store, self.collection, ref="MSG-1")
        self.second = self.store.archive_message(
            OPERATOR, self.collection["id"], "MSG-2", "SENDER-REF-2",
            ["RECIP-REF-9"], "2024-02-10T00:00:00+00:00", 512, "native")

    def test_discovery_record_shape_has_no_query_text(self):
        discovery = self.store.record_discovery(
            OPERATOR, "MATTER-1", self.collection["id"])
        self.assertEqual(set(discovery), DISCOVERY_KEYS)
        self.assertNotIn("query", discovery)
        self.assertNotIn("query_text", discovery)
        self.assertEqual(discovery["result_count"], 2)
        self.assertEqual(discovery["result_message_ids"],
                         [self.first["id"], self.second["id"]])

    def test_scope_filters(self):
        by_sender = self.store.record_discovery(
            OPERATOR, "MATTER-2", self.collection["id"],
            sender_ref="SENDER-REF-2")
        self.assertEqual(by_sender["result_message_ids"], [self.second["id"]])
        by_window = self.store.record_discovery(
            OPERATOR, "MATTER-3", self.collection["id"],
            from_at="2024-02-01", to_at="2024-02-29")
        self.assertEqual(by_window["result_message_ids"],
                         [self.second["id"]])
        empty = self.store.record_discovery(
            OPERATOR, "MATTER-4", self.collection["id"],
            sender_ref="SENDER-UNKNOWN")
        self.assertEqual(empty["result_count"], 0)
        self.assertEqual(empty["result_message_ids"], [])

    def test_window_validation(self):
        with self.assertRaises(ValidationError):
            self.store.record_discovery(
                OPERATOR, "MATTER-X", self.collection["id"],
                from_at="2024-03-01", to_at="2024-01-01")
        with self.assertRaises(ValidationError):
            self.store.record_discovery(OPERATOR, "", self.collection["id"])
        self.assertEqual(self.store.list_discoveries(ADMIN), [])

    def test_list_and_permissions(self):
        self.store.record_discovery(OPERATOR, "MATTER-1",
                                    self.collection["id"])
        listed = self.store.list_discoveries(
            VIEWER, collection_id=self.collection["id"])
        self.assertEqual(len(listed), 1)
        from storage.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.store.record_discovery(VIEWER, "MATTER-2",
                                        self.collection["id"])


if __name__ == "__main__":
    unittest.main()
