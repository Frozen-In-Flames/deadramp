"""Certificate award record tests.

Traces to: Core function 16 (Certificate award records) --
record_certificate (``crt-``): a learner reference, an optional
course, a title, an optional award date, a note, and the recording
actor; append-only facts. certificate_write is an instructor write
and certificate_read a record read; learner scope applies (Core
function 13). Also traces to boundary decision 4 (scores: none,
anywhere): recursively, no score key exists on a certificate, a
continuing-education record, or a statement record. Control
families: AC-3, AC-6, SI-10.
"""

import unittest

from lms_helpers import (
    ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_ce_record, make_certificate,
    make_store,
)
from lms.errors import NotFoundError, PermissionDenied, ValidationError

CERTIFICATE_KEYS = {
    "id", "learner_ref", "course_id", "title", "awarded_on", "note",
    "created_by", "created_utc",
}


def _all_keys(obj):
    """Collect every dict key appearing anywhere in a nested structure."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def _score_keys(obj):
    """Keys that would constitute a score field: exactly 'score', or starting 'score_' / ending '_score' (case-insensitive)."""
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if lowered == "score" or lowered.startswith("score_") or lowered.endswith("_score"):
            bad.add(key)
    return bad


class TestCertificates(unittest.TestCase):
    """Core 16: certificate award records."""

    def test_record_get_list_round_trip(self):
        """Core 16: recording returns a crt- record with EXACTLY the contract key set; get returns the stored record; list returns all awards and filters by learner_ref; ids are sequential."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        first = make_certificate(
            store, course_id=course["id"], awarded_on="2026-06-10",
            note="completed with the June cohort")
        second = store.record_certificate("erin", "Erin Award", ADMIN)
        self.assertEqual(first["id"], "crt-1")
        self.assertEqual(second["id"], "crt-2")
        self.assertEqual(set(first), CERTIFICATE_KEYS)
        self.assertEqual(first["learner_ref"], "carol")
        self.assertEqual(first["course_id"], course["id"])
        self.assertEqual(first["title"], "Safety Certificate")
        self.assertEqual(first["awarded_on"], "2026-06-10")
        self.assertEqual(first["note"], "completed with the June cohort")
        self.assertEqual(first["created_by"], "bob")
        self.assertIn("created_utc", first)
        self.assertEqual(store.get_certificate(first["id"], ADMIN), first)
        self.assertEqual(set(store.get_certificate(second["id"], AUDITOR)),
                         CERTIFICATE_KEYS)
        self.assertEqual(
            [c["id"] for c in store.list_certificates(ADMIN)],
            ["crt-1", "crt-2"])
        self.assertEqual(
            [c["id"] for c in store.list_certificates(
                ADMIN, learner_ref="erin")],
            ["crt-2"])
        with self.assertRaises(NotFoundError):
            store.get_certificate("crt-999", ADMIN)

    def test_defaults(self):
        """Core 16: course_id and awarded_on default to None and note to '' when not given."""
        store, _, _ = make_store()
        cert = store.record_certificate("carol", "Bare Award", INSTRUCTOR)
        self.assertIsNone(cert["course_id"])
        self.assertIsNone(cert["awarded_on"])
        self.assertEqual(cert["note"], "")

    def test_bad_awarded_on_rejected(self):
        """Core 16 / SI-10: an awarded_on that is not an ISO calendar date -> ValidationError; failed records consume no id."""
        store, _, _ = make_store()
        for bad in ("June 10", "2026-13-01", "2026-02-30", "10-06-2026"):
            with self.subTest(awarded_on=bad):
                with self.assertRaises(ValidationError):
                    store.record_certificate("carol", "Award", INSTRUCTOR,
                                             awarded_on=bad)
        cert = store.record_certificate("carol", "Award", INSTRUCTOR,
                                        awarded_on="2026-06-10")
        self.assertEqual(cert["id"], "crt-1")

    def test_unknown_course_and_learner(self):
        """Core 16: an unknown course_id -> NotFoundError (the store's semantics for an optional course binding, as in Core 4/7); an unknown learner_ref -> NotFoundError; no id consumed."""
        store, _, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.record_certificate("carol", "Award", INSTRUCTOR,
                                     course_id="crs-999")
        with self.assertRaises(NotFoundError):
            store.record_certificate("ghost", "Award", INSTRUCTOR)
        cert = store.record_certificate("carol", "Award", INSTRUCTOR)
        self.assertEqual(cert["id"], "crt-1")

    def test_learner_scope_and_write_permissions(self):
        """Core 16 / Core 13: a learner reads only her own certificates (get of another's -> PermissionDenied; list shows only her own); a learner and an auditor may not record certificates; instructor and admin may."""
        store, _, _ = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.record_certificate("carol", "Nope", LEARNER)
        with self.assertRaises(PermissionDenied):
            store.record_certificate("carol", "Nope", AUDITOR)
        own = store.record_certificate("carol", "Mine", INSTRUCTOR)
        other = store.record_certificate("erin", "Theirs", ADMIN)
        self.assertEqual(store.get_certificate(own["id"], LEARNER)["id"],
                         own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_certificate(other["id"], LEARNER)
        self.assertEqual([c["id"] for c in store.list_certificates(LEARNER)],
                         [own["id"]])
        self.assertEqual(
            len(store.list_certificates(AUDITOR, learner_ref="erin")), 1)

    def test_no_score_key_across_new_records(self):
        """Decision 4 (no-scoring pin): recursively, no dict key named 'score' / 'score_*' / '*_score' exists on a certificate record, a continuing-education record, or a statement record."""
        store, _, course = make_store()
        cert = make_certificate(store, course_id=course["id"],
                                awarded_on="2026-06-10")
        ce = make_ce_record(store, credit_text="score: 3.5 credits")
        stmt = store.record_statement(
            "carol", "completed", course["id"], INSTRUCTOR,
            result_text="score: 88/100 — pass")
        for label, record in (("certificate", cert),
                              ("continuing_education", ce),
                              ("statement", stmt)):
            with self.subTest(record=label):
                self.assertEqual(_score_keys(record), set())
        # The score-looking texts stay verbatim caller-supplied text.
        self.assertEqual(ce["credit_text"], "score: 3.5 credits")
        self.assertEqual(stmt["result_text"], "score: 88/100 — pass")


if __name__ == "__main__":
    unittest.main()
