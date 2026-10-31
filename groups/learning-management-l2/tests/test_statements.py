"""Experience statement (LRS-style) tests.

Traces to: Core function 8 (Experience statements) --
record_statement (``stm-``) stores a learner/verb/object statement
whose record keys are EXACTLY {id, learner_ref, verb, object_ref,
context, result_text, recorded_by, recorded_utc}. result_text is
stored verbatim and never parsed: there is deliberately NO score
field anywhere in the substrate. Learner scope applies under Core
function 12.
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError

STATEMENT_KEYS = {
    "id", "learner_ref", "verb", "object_ref",
    "context", "result_text", "recorded_by", "recorded_utc",
}

RESULT_WITH_SCORE_TEXT = "score: 88/100 — pass"


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


class TestStatements(unittest.TestCase):
    """Core 8: experience statement records."""

    def test_record_shape_exact_keys(self):
        """Core 8: a statement record carries EXACTLY the contract key set, with stm- id and provenance."""
        store, _, course = make_store()
        stmt = store.record_statement("carol", "completed", course["id"], INSTRUCTOR,
                                      context="Safety Basics run 1")
        self.assertEqual(set(stmt), STATEMENT_KEYS)
        self.assertEqual(stmt["id"], "stm-1")
        self.assertEqual(stmt["learner_ref"], "carol")
        self.assertEqual(stmt["verb"], "completed")
        self.assertEqual(stmt["object_ref"], course["id"])
        self.assertEqual(stmt["context"], "Safety Basics run 1")
        self.assertIsNone(stmt["result_text"])
        self.assertEqual(stmt["recorded_by"], "bob")
        bare = store.record_statement("carol", "experienced", "https://example.test/x",
                                      INSTRUCTOR)
        self.assertEqual(bare["context"], "")
        self.assertEqual(set(store.get_statement(bare["id"], ADMIN)), STATEMENT_KEYS)

    def test_result_text_verbatim_never_parsed(self):
        """Core 8: result_text is stored verbatim as the exact string given -- a score-looking string stays a string in result_text and produces NO 'score' key on the record."""
        store, _, course = make_store()
        stmt = store.record_statement("carol", "completed", course["id"], INSTRUCTOR,
                                      result_text=RESULT_WITH_SCORE_TEXT)
        self.assertEqual(stmt["result_text"], RESULT_WITH_SCORE_TEXT)
        self.assertIsInstance(stmt["result_text"], str)
        self.assertNotIn("score", stmt)
        stored = store.get_statement(stmt["id"], ADMIN)
        self.assertEqual(stored["result_text"], RESULT_WITH_SCORE_TEXT)
        self.assertEqual(set(stored), STATEMENT_KEYS)

    def test_no_score_field_across_shapes(self):
        """Core 8 (no-scoring pin): recursively, no dict key named 'score' / 'score_*' / '*_score' exists on a statement, a progress record, a learner-competency record, or a report (report count keys are fine)."""
        store, _, course = make_store()
        comp = store.create_competency("Safety Awareness", INSTRUCTOR)
        stmt = store.record_statement("carol", "completed", course["id"], INSTRUCTOR,
                                      result_text=RESULT_WITH_SCORE_TEXT)
        progress = store.record_progress("carol", course["id"], "completed", INSTRUCTOR,
                                         percent_complete=88)
        learner_comp = store.record_learner_competency(
            "carol", comp["id"], "Level 3 (vendor scale)", INSTRUCTOR)
        report = store.report(ADMIN, as_of="2026-06-15")
        for label, record in (("statement", stmt), ("progress", progress),
                              ("learner_competency", learner_comp),
                              ("report", report)):
            with self.subTest(record=label):
                self.assertEqual(_score_keys(record), set())

    def test_unknown_learner_and_validation(self):
        """Core 8: an unknown learner_ref -> NotFoundError; empty learner_ref/verb/object_ref -> ValidationError; no id consumed by failures."""
        store, _, course = make_store()
        with self.assertRaises(NotFoundError):
            store.record_statement("ghost", "completed", course["id"], INSTRUCTOR)
        for verb, obj in (("", course["id"]), ("completed", "")):
            with self.subTest(verb=verb, object_ref=obj):
                with self.assertRaises(ValidationError):
                    store.record_statement("carol", verb, obj, INSTRUCTOR)
        stmt = store.record_statement("carol", "completed", course["id"], INSTRUCTOR)
        self.assertEqual(stmt["id"], "stm-1")
        with self.assertRaises(NotFoundError):
            store.get_statement("stm-999", ADMIN)

    def test_learner_scope_and_write_denied(self):
        """Core 8 / Core 12: a learner may not record statements; a learner reads her own statements only, and list filters by learner_ref/object_ref for staff."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.record_statement("carol", "completed", course["id"], LEARNER)
        own = store.record_statement("carol", "completed", course["id"], INSTRUCTOR)
        other = store.record_statement("erin", "completed", course["id"], INSTRUCTOR)
        self.assertEqual(store.get_statement(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_statement(other["id"], LEARNER)
        self.assertEqual([s["id"] for s in store.list_statements(LEARNER)], [own["id"]])
        self.assertEqual(
            len(store.list_statements(ADMIN, object_ref=course["id"])), 2
        )
        self.assertEqual(
            len(store.list_statements(ADMIN, learner_ref="erin")), 1
        )


if __name__ == "__main__":
    unittest.main()
