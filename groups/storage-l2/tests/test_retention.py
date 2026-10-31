"""Core function 5: the signature invariant -- retention state is
derived at read by the single seam ``_derive_retention_state``,
never stored, and disposition is gated on the derived state.

Fixture arithmetic: archived 2024-01-01, retention 30 days, so the
boundary is 2024-01-31T00:00:00Z exactly.
"""

import unittest

from storage.errors import ValidationError
from storage.store import _derive_retention_state
from datetime import datetime, timezone

from storage_helpers import (ADMIN, AFTER_BOUNDARY, ARCHIVED, AT_BOUNDARY,
                             BEFORE_BOUNDARY, make_archive, make_message,
                             make_store)


class SeamTests(unittest.TestCase):
    def test_seam_states(self):
        archived = datetime(2024, 1, 1, tzinfo=timezone.utc)
        before = datetime(2024, 1, 15, tzinfo=timezone.utc)
        boundary = datetime(2024, 1, 31, tzinfo=timezone.utc)
        after = datetime(2024, 3, 1, tzinfo=timezone.utc)
        self.assertEqual(
            _derive_retention_state(archived, 30, False, before), "retained")
        self.assertEqual(
            _derive_retention_state(archived, 30, False, boundary),
            "disposition_eligible")
        self.assertEqual(
            _derive_retention_state(archived, 30, False, after),
            "disposition_eligible")
        # a recorded disposition dominates at any clock, even before
        # the boundary the message was disposed under
        self.assertEqual(
            _derive_retention_state(archived, 30, True, before), "disposed")


class RetentionViewTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)

    def test_state_is_derived_at_read_and_never_stored(self):
        raw = self.store._messages[self.message["id"]]
        self.assertNotIn("retention_state", raw)
        self.assertNotIn("retention_until", raw)
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=BEFORE_BOUNDARY)
        self.assertEqual(view["retention_state"], "retained")
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=AFTER_BOUNDARY)
        self.assertEqual(view["retention_state"], "disposition_eligible")

    def test_retention_until_is_the_derived_boundary(self):
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=BEFORE_BOUNDARY)
        self.assertEqual(view["retention_until"], AT_BOUNDARY)

    def test_exact_boundary_is_eligible(self):
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=AT_BOUNDARY)
        self.assertEqual(view["retention_state"], "disposition_eligible")

    def test_list_filter_by_derived_state(self):
        retained = self.store.list_messages(
            ADMIN, retention_state="retained", now=BEFORE_BOUNDARY)
        self.assertEqual([m["id"] for m in retained], [self.message["id"]])
        eligible = self.store.list_messages(
            ADMIN, retention_state="disposition_eligible", now=AFTER_BOUNDARY)
        self.assertEqual([m["id"] for m in eligible], [self.message["id"]])
        with self.assertRaises(ValidationError):
            self.store.list_messages(ADMIN, retention_state="gone")


class DispositionGateTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)

    def test_gate_refuses_disposition_inside_retention(self):
        with self.assertRaises(ValidationError):
            self.store.record_disposition(ADMIN, self.message["id"],
                                          "shredded", at=BEFORE_BOUNDARY)
        self.assertEqual(self.store.list_dispositions(ADMIN), [])
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=BEFORE_BOUNDARY)
        self.assertEqual(view["retention_state"], "retained")

    def test_disposition_at_and_after_boundary(self):
        disposition = self.store.record_disposition(
            ADMIN, self.message["id"], "shredded", at=AT_BOUNDARY)
        self.assertEqual(disposition["id"], "dsp-1")
        self.assertEqual(disposition["message_id"], self.message["id"])
        self.assertEqual(disposition["disposed_at"], AT_BOUNDARY)
        view = self.store.get_message(ADMIN, self.message["id"],
                                      now=BEFORE_BOUNDARY)
        self.assertEqual(view["retention_state"], "disposed")
        listed = self.store.list_dispositions(
            ADMIN, message_id=self.message["id"])
        self.assertEqual([d["id"] for d in listed], ["dsp-1"])

    def test_double_disposition_is_refused(self):
        self.store.record_disposition(ADMIN, self.message["id"],
                                      "shredded", at=AFTER_BOUNDARY)
        with self.assertRaises(ValidationError):
            self.store.record_disposition(ADMIN, self.message["id"],
                                          "shredded", at=AFTER_BOUNDARY)
        self.assertEqual(len(self.store.list_dispositions(ADMIN)), 1)

    def test_gate_uses_each_collections_own_policy(self):
        long_policy = self.store.create_policy(ADMIN, "Long retention", 3650)
        vault = self.store.create_collection(
            ADMIN, self.org["id"], "Vault archive", long_policy["id"],
            "native")
        kept = make_message(self.store, vault, ref="MSG-KEPT")
        with self.assertRaises(ValidationError):
            self.store.record_disposition(ADMIN, kept["id"], "shredded",
                                          at=AFTER_BOUNDARY)


if __name__ == "__main__":
    unittest.main()
