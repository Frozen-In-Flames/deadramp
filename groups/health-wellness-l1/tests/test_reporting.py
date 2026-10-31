"""Population scorecard reporting tests.

Traces to: Core function 8 (Population scorecard reporting;
AU-6, CA-7; claim family analysis_reporting 3/5 -- scorecards "for
individual patients and across populations"). Reports aggregate the
substrate records only; pattern/trend engines are Extended.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, fresh_store, make_store
from health.errors import NotFoundError, PermissionDenied

AS_OF = "2026-06-15"


def _populated():
    store, program, participant = make_store()
    other_prog = store.create_program("Second Program", ADMIN)
    other = store.create_participant("erin", ADMIN)
    store.create_enrollment(participant["id"], program["id"], CLINICIAN)
    store.create_enrollment(other["id"], program["id"], CLINICIAN)
    store.create_enrollment(other["id"], other_prog["id"], CLINICIAN)
    store.record_measurement(participant["id"], "glucose", 100, "mg/dL",
                             "2026-06-10", CLINICIAN, program_id=program["id"])
    store.record_measurement(participant["id"], "glucose", 140, "mg/dL",
                             "2026-06-11", CLINICIAN, program_id=program["id"])
    store.record_measurement(other["id"], "glucose", 200, "mg/dL",
                             "2026-06-10", CLINICIAN, program_id=other_prog["id"])
    store.record_measurement(other["id"], "weight", 80, "kg",
                             "2026-06-10", CLINICIAN)
    plan = store.create_plan(participant["id"], program["id"], "Goal",
                             "2026-06-01", CLINICIAN)
    store.complete_plan(plan["id"], "2026-05-20", CLINICIAN)
    store.create_plan(other["id"], program["id"], "Late goal", "2026-06-01", CLINICIAN)
    store.create_plan(other["id"], other_prog["id"], "Future goal", "2026-12-01", CLINICIAN)
    act = store.create_activity(participant["id"], "Visit", "2026-07-01T09:00:00Z",
                                CLINICIAN, program_id=program["id"])
    store.set_activity_state(act["id"], "completed", CLINICIAN)
    store.create_activity(other["id"], "Visit 2", "2026-07-02T09:00:00Z", CLINICIAN)
    store.create_eligibility(participant["id"], "plan-alpha", "2026-01-01", ADMIN,
                             coverage_end="2026-05-31")
    store.create_eligibility(other["id"], "plan-beta", "2026-07-01", ADMIN)
    return store, program, other_prog


class TestReporting(unittest.TestCase):
    """Core 8: population report over all record families."""

    def test_report_counts_and_aggregates(self):
        """Core 8 (AU-6/CA-7): report counts every family, aggregates measurements per metric (count/min/max/mean), breaks plans/activities/eligibility down by derived status, and counts enrollments per program."""
        store, program, other_prog = _populated()
        report = store.report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["as_of"], AS_OF)
        self.assertEqual(report["participants"], 2)
        self.assertEqual(report["programs"], 2)
        self.assertEqual(report["enrollments"], 3)
        self.assertEqual(report["enrollments_by_program"],
                         {program["id"]: 2, other_prog["id"]: 1})
        self.assertEqual(report["measurements"], 4)
        glucose = report["measurements_by_metric"]["glucose"]
        self.assertEqual(glucose["count"], 3)
        self.assertEqual(glucose["min"], 100)
        self.assertEqual(glucose["max"], 200)
        self.assertAlmostEqual(glucose["mean"], 440 / 3)
        self.assertEqual(report["plans"], 3)
        self.assertEqual(report["plans_by_status"],
                         {"current": 1, "overdue": 1, "completed": 1})
        self.assertEqual(report["activities"], 2)
        self.assertEqual(report["activities_by_state"],
                         {"scheduled": 1, "completed": 1, "cancelled": 0})
        self.assertEqual(report["eligibility"], 2)
        self.assertEqual(report["eligibility_by_status"],
                         {"upcoming": 1, "current": 0, "ended": 1})

    def test_report_exact_keys_and_empty_shape(self):
        """Core 8: report returns exactly the contract keys; an empty store reports zeroes with the full shape."""
        report = fresh_store().report(ADMIN, as_of=AS_OF)
        self.assertEqual(set(report), {"as_of", "participants", "programs", "enrollments",
                                       "measurements", "measurements_by_metric", "plans",
                                       "plans_by_status", "activities",
                                       "activities_by_state", "eligibility",
                                       "eligibility_by_status", "enrollments_by_program"})
        self.assertEqual(report["participants"], 0)
        self.assertEqual(report["measurements_by_metric"], {})
        self.assertEqual(report["plans_by_status"],
                         {"current": 0, "overdue": 0, "completed": 0})
        self.assertEqual(report["eligibility_by_status"],
                         {"upcoming": 0, "current": 0, "ended": 0})

    def test_report_permissions(self):
        """Core 8 / Core 9: admin, clinician and auditor may report; a member may not (report_read is not a member permission)."""
        store, _, _ = _populated()
        self.assertEqual(store.report(CLINICIAN, as_of=AS_OF)["participants"], 2)
        self.assertEqual(store.report(AUDITOR, as_of=AS_OF)["participants"], 2)
        with self.assertRaises(PermissionDenied):
            store.report(MEMBER, as_of=AS_OF)


class TestScorecard(unittest.TestCase):
    """Core 8: per-program scorecard (the individual/population split)."""

    def test_scorecard_scoped_to_program(self):
        """Core 8: scorecard counts only the program's measurements/plans, aggregates per metric, and counts distinct participants with a measurement or plan in the program."""
        store, program, _ = _populated()
        card = store.scorecard(program["id"], AUDITOR, as_of=AS_OF)
        self.assertEqual(set(card), {"program_id", "as_of", "participants", "measurements",
                                     "measurements_by_metric", "plans", "plans_by_status"})
        self.assertEqual(card["program_id"], program["id"])
        self.assertEqual(card["participants"], 2)
        self.assertEqual(card["measurements"], 2)
        glucose = card["measurements_by_metric"]["glucose"]
        self.assertEqual(glucose, {"count": 2, "min": 100, "max": 140, "mean": 120.0})
        self.assertEqual(card["plans"], 2)
        self.assertEqual(card["plans_by_status"],
                         {"current": 0, "overdue": 1, "completed": 1})

    def test_scorecard_unknown_program_and_permissions(self):
        """Core 8 (SI-10 / AC-3): unknown program -> NotFoundError; member -> PermissionDenied."""
        store, _, _ = _populated()
        with self.assertRaises(NotFoundError):
            store.scorecard("prg-999", ADMIN, as_of=AS_OF)
        with self.assertRaises(PermissionDenied):
            store.scorecard("prg-1", MEMBER, as_of=AS_OF)


if __name__ == "__main__":
    unittest.main()
