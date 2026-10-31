"""Care / wellness plan record tests.

Traces to: Core function 5 (Care / wellness plan records with derived
status; AU-6, CA-7, CM-6; claim families care_guidance 1/5 and
measurement_data 3/5 objectives) -- plan records with a due date and an
optional completion date; status (current/overdue/completed) derived
deterministically.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError

AS_OF = "2026-06-15"


class TestPlans(unittest.TestCase):
    """Core 5: plan records and deterministic status derivation."""

    def _setup(self):
        store, program, participant = make_store()
        plan = store.create_plan(participant["id"], program["id"], "Daily checks",
                                 "2026-06-01", CLINICIAN)
        return store, program, participant, plan

    def test_create_shape(self):
        """Core 5: created plan carries a pln- id, completed_on None, and the read view adds derived_status."""
        _, _, _, plan = self._setup()
        self.assertEqual(plan["id"], "pln-1")
        self.assertIsNone(plan["completed_on"])
        self.assertEqual(plan["kind"], "care_plan")
        self.assertIn("derived_status", plan)

    def test_derived_overdue_current_completed(self):
        """Core 5 (CA-7): past due + incomplete -> overdue; on the due date -> current; after complete_plan -> completed even past due; completing before the due date is allowed."""
        store, _, _, plan = self._setup()
        self.assertEqual(store.get_plan(plan["id"], ADMIN, as_of=AS_OF)["derived_status"],
                         "overdue")
        self.assertEqual(store.get_plan(plan["id"], ADMIN, as_of="2026-06-01")["derived_status"],
                         "current")
        self.assertEqual(store.get_plan(plan["id"], ADMIN, as_of="2026-05-01")["derived_status"],
                         "current")
        done = store.complete_plan(plan["id"], "2026-05-20", CLINICIAN)
        self.assertEqual(done["completed_on"], "2026-05-20")
        self.assertEqual(store.get_plan(plan["id"], ADMIN, as_of=AS_OF)["derived_status"],
                         "completed")

    def test_complete_twice_and_validation(self):
        """Core 5 (SI-10): completing an already completed plan -> ValidationError; bad dates/kinds/refs -> ValidationError/NotFoundError."""
        store, program, participant, plan = self._setup()
        store.complete_plan(plan["id"], "2026-06-02", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.complete_plan(plan["id"], "2026-06-03", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.create_plan(participant["id"], program["id"], "X", "June 1", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.create_plan(participant["id"], program["id"], "X", "2026-06-01",
                              CLINICIAN, kind="alien")
        with self.assertRaises(NotFoundError):
            store.create_plan("par-999", program["id"], "X", "2026-06-01", CLINICIAN)
        with self.assertRaises(NotFoundError):
            store.complete_plan("pln-999", "2026-06-02", CLINICIAN)

    def test_kinds(self):
        """Core 5: kinds care_plan/wellness_plan/education accepted."""
        store, program, participant = make_store()
        for kind in ("care_plan", "wellness_plan", "education"):
            rec = store.create_plan(participant["id"], program["id"], "T %s" % kind,
                                    "2026-06-01", CLINICIAN, kind=kind)
            self.assertEqual(rec["kind"], kind)

    def test_list_derives_each_and_member_scope(self):
        """Core 5 + member scope: list_plans derives each plan at as_of; member sees only own plans and is denied another's; member write denied."""
        store, program, participant, plan = self._setup()
        other = store.create_participant("erin", ADMIN)
        foreign = store.create_plan(other["id"], program["id"], "Foreign",
                                    "2026-12-01", CLINICIAN)
        views = store.list_plans(ADMIN, as_of=AS_OF)
        by_id = {v["id"]: v["derived_status"] for v in views}
        self.assertEqual(by_id[plan["id"]], "overdue")
        self.assertEqual(by_id[foreign["id"]], "current")
        own = store.list_plans(MEMBER, as_of=AS_OF)
        self.assertEqual([v["id"] for v in own], [plan["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_plan(foreign["id"], MEMBER, as_of=AS_OF)
        with self.assertRaises(PermissionDenied):
            store.create_plan(participant["id"], program["id"], "X", "2026-06-01", MEMBER)


if __name__ == "__main__":
    unittest.main()
