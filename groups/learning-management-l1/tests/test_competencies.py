"""Competency tests.

Traces to: Core function 6 (Competencies) -- competency definitions
(``cpt-``) and learner-competency records (``lcr-``) whose level is
recorded verbatim (vendor scales are not normalised). competency_write
is an instructor write; learner scope applies (Core function 13).
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestCompetencies(unittest.TestCase):
    """Core 6: competency definitions."""

    def test_create_competency_shape_and_list(self):
        """Core 6: creation returns a cpt- record with name/description and provenance; list returns all definitions."""
        store, _, _ = make_store()
        first = store.create_competency("Safety Awareness", INSTRUCTOR,
                                        description="Hazard recognition")
        second = store.create_competency("Leadership", ADMIN)
        self.assertEqual(first["id"], "cpt-1")
        self.assertEqual(second["id"], "cpt-2")
        self.assertEqual(first["description"], "Hazard recognition")
        self.assertEqual(second["description"], "")
        self.assertEqual(first["created_by"], "bob")
        self.assertEqual([c["id"] for c in store.list_competencies(LEARNER)],
                         ["cpt-1", "cpt-2"])
        self.assertEqual(store.get_competency("cpt-1", ADMIN)["name"], "Safety Awareness")

    def test_competency_validation(self):
        """Core 6: an empty competency name -> ValidationError and consumes no id; unknown competency -> NotFoundError."""
        store, _, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_competency("", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.get_competency("cpt-999", ADMIN)
        comp = store.create_competency("Ok", INSTRUCTOR)
        self.assertEqual(comp["id"], "cpt-1")


class TestLearnerCompetencies(unittest.TestCase):
    """Core 6: learner-competency records with verbatim levels."""

    def test_record_shape_and_verbatim_level(self):
        """Core 6: recording returns an lcr- record whose level is stored verbatim (e.g. a vendor-scale string), with note and provenance."""
        store, _, _ = make_store()
        comp = store.create_competency("Safety Awareness", INSTRUCTOR)
        rec = store.record_learner_competency(
            "carol", comp["id"], "Level 3 (vendor scale)", INSTRUCTOR,
            note="assessed in the field",
        )
        self.assertEqual(rec["id"], "lcr-1")
        self.assertEqual(rec["learner_ref"], "carol")
        self.assertEqual(rec["competency_id"], comp["id"])
        self.assertEqual(rec["level"], "Level 3 (vendor scale)")
        self.assertEqual(rec["note"], "assessed in the field")
        self.assertEqual(rec["recorded_by"], "bob")
        stored = store.get_learner_competency(rec["id"], ADMIN)
        self.assertEqual(stored["level"], "Level 3 (vendor scale)")

    def test_unknown_learner_or_competency(self):
        """Core 6: recording against an unknown learner_ref or competency_id -> NotFoundError; no id consumed."""
        store, _, _ = make_store()
        comp = store.create_competency("Safety Awareness", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.record_learner_competency("ghost", comp["id"], "L1", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.record_learner_competency("carol", "cpt-999", "L1", INSTRUCTOR)
        rec = store.record_learner_competency("carol", comp["id"], "L1", INSTRUCTOR)
        self.assertEqual(rec["id"], "lcr-1")

    def test_list_filters_and_learner_scope(self):
        """Core 6 / Core 13: list filters by learner_ref and competency_id; a learner may not record competencies and reads only her own records."""
        store, _, _ = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        comp = store.create_competency("Safety Awareness", INSTRUCTOR)
        other_comp = store.create_competency("Leadership", INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            store.record_learner_competency("carol", comp["id"], "L1", LEARNER)
        own = store.record_learner_competency("carol", comp["id"], "L2", INSTRUCTOR)
        store.record_learner_competency("erin", comp["id"], "L1", INSTRUCTOR)
        second_own = store.record_learner_competency("carol", other_comp["id"], "L1",
                                                     INSTRUCTOR)
        self.assertEqual(
            len(store.list_learner_competencies(ADMIN, learner_ref="carol")), 2
        )
        self.assertEqual(
            len(store.list_learner_competencies(ADMIN, competency_id=comp["id"])), 2
        )
        self.assertEqual([r["id"] for r in store.list_learner_competencies(LEARNER)],
                         [own["id"], second_own["id"]])
        other = store.list_learner_competencies(ADMIN, learner_ref="erin")[0]
        with self.assertRaises(PermissionDenied):
            store.get_learner_competency(other["id"], LEARNER)


if __name__ == "__main__":
    unittest.main()
