"""Continuing education record tests.

Traces to: Core function 17 (Continuing education records) --
record_continuing_education (``ceu-``): a learner reference, an
opaque activity reference, a caller-supplied credit text recorded
**verbatim** (never parsed, summed, or converted -- boundary
decision 4), and an optional recorded-on date. continuing_ed_write
is an instructor write and continuing_ed_read a record read; learner
scope applies (Core function 13). Control families: AC-3, AC-6,
SI-10.
"""

import unittest

from lms_helpers import (
    ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_ce_record, make_store,
)
from lms.errors import NotFoundError, PermissionDenied, ValidationError

CE_KEYS = {
    "id", "learner_ref", "activity_ref", "credit_text", "recorded_on",
    "created_by", "created_utc",
}


class TestContinuingEducation(unittest.TestCase):
    """Core 17: continuing-education records with verbatim credit text."""

    def test_record_get_list_round_trip(self):
        """Core 17: recording returns a ceu- record with EXACTLY the contract key set; get returns the stored record; list returns all records and filters by learner_ref; ids are sequential."""
        store, _, _ = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        first = make_ce_record(store, recorded_on="2026-06-11")
        second = store.record_continuing_education(
            "erin", "act-9", "10 contact hours", ADMIN,
            recorded_on="2026-06-12")
        self.assertEqual(first["id"], "ceu-1")
        self.assertEqual(second["id"], "ceu-2")
        self.assertEqual(set(first), CE_KEYS)
        self.assertEqual(first["learner_ref"], "carol")
        self.assertEqual(first["activity_ref"], "act-1")
        self.assertEqual(first["recorded_on"], "2026-06-11")
        self.assertEqual(first["created_by"], "bob")
        self.assertIn("created_utc", first)
        self.assertEqual(store.get_continuing_education(first["id"], ADMIN),
                         first)
        self.assertEqual(
            set(store.get_continuing_education(second["id"], AUDITOR)),
            CE_KEYS)
        self.assertEqual(
            [r["id"] for r in store.list_continuing_education(ADMIN)],
            ["ceu-1", "ceu-2"])
        self.assertEqual(
            [r["id"] for r in store.list_continuing_education(
                ADMIN, learner_ref="erin")],
            ["ceu-2"])
        with self.assertRaises(NotFoundError):
            store.get_continuing_education("ceu-999", ADMIN)

    def test_credit_text_stored_verbatim_never_parsed(self):
        """Core 17 / decision 4: credit_text is stored verbatim as the exact string given -- numeric-looking text like '3.5 credits' stays that exact string (type str) and NO numeric field appears on the record (the key set is exactly the contract set)."""
        store, _, _ = make_store()
        for text in ("3.5 credits", "10 contact hours", "0.5 CEU", "42"):
            with self.subTest(credit_text=text):
                rec = store.record_continuing_education(
                    "carol", "act-x", text, INSTRUCTOR)
                self.assertEqual(rec["credit_text"], text)
                self.assertIsInstance(rec["credit_text"], str)
                self.assertEqual(set(rec), CE_KEYS)
                stored = store.get_continuing_education(rec["id"], ADMIN)
                self.assertEqual(stored["credit_text"], text)
                for key in ("credits", "credit", "credit_value", "amount",
                            "hours", "value", "total"):
                    self.assertNotIn(key, stored)

    def test_defaults_and_bad_recorded_on(self):
        """Core 17 / SI-10: recorded_on defaults to None; a recorded_on that is not an ISO calendar date -> ValidationError; failed records consume no id."""
        store, _, _ = make_store()
        bare = store.record_continuing_education("carol", "act-1", "1 credit",
                                                 INSTRUCTOR)
        self.assertIsNone(bare["recorded_on"])
        for bad in ("June 11", "2026-13-01", "2026-02-30", "11-06-2026"):
            with self.subTest(recorded_on=bad):
                with self.assertRaises(ValidationError):
                    store.record_continuing_education(
                        "carol", "act-1", "1 credit", INSTRUCTOR,
                        recorded_on=bad)
        rec = store.record_continuing_education(
            "carol", "act-1", "1 credit", INSTRUCTOR,
            recorded_on="2026-06-11")
        self.assertEqual(rec["id"], "ceu-2")

    def test_unknown_learner_and_validation(self):
        """Core 17: an unknown learner_ref -> NotFoundError; an empty activity_ref or credit_text -> ValidationError; no id consumed by failures."""
        store, _, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.record_continuing_education("ghost", "act-1", "1 credit",
                                              INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.record_continuing_education("carol", "", "1 credit",
                                              INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.record_continuing_education("carol", "act-1", "",
                                              INSTRUCTOR)
        rec = store.record_continuing_education("carol", "act-1", "1 credit",
                                                INSTRUCTOR)
        self.assertEqual(rec["id"], "ceu-1")

    def test_learner_scope_and_write_permissions(self):
        """Core 17 / Core 13: a learner reads only her own CE records (get of another's -> PermissionDenied; list shows only her own); a learner and an auditor may not record CE records; instructor and admin may."""
        store, _, _ = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.record_continuing_education("carol", "act-1", "1 credit",
                                              LEARNER)
        with self.assertRaises(PermissionDenied):
            store.record_continuing_education("carol", "act-1", "1 credit",
                                              AUDITOR)
        own = store.record_continuing_education("carol", "act-1", "1 credit",
                                                INSTRUCTOR)
        other = store.record_continuing_education("erin", "act-2", "2 credits",
                                                  ADMIN)
        self.assertEqual(
            store.get_continuing_education(own["id"], LEARNER)["id"],
            own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_continuing_education(other["id"], LEARNER)
        self.assertEqual(
            [r["id"] for r in store.list_continuing_education(LEARNER)],
            [own["id"]])
        self.assertEqual(
            len(store.list_continuing_education(AUDITOR,
                                                learner_ref="erin")), 1)


if __name__ == "__main__":
    unittest.main()
