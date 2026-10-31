"""Reporting tests.

Traces to: Core function 10 (Reporting over the records; AU-6,
CA-7). Reports read substrate records only; dashboard/predictive
engines are Extended. Lifecycle counts use the DERIVED status.
"""

import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store
from hr.errors import PermissionDenied


def _populated():
    store, position, person = make_store()
    store.create_person("erin", ADMIN, kind="applicant")
    vacancy = store.create_vacancy(position["id"], "Opening", ADMIN)
    store.set_vacancy_status(vacancy["id"], "posted", SPECIALIST)
    app = store.create_application("carol", vacancy["id"], SPECIALIST)
    store.set_application_stage(app["id"], "screened", SPECIALIST)
    evl = store.create_evaluation(app["id"], "assessment", "Quiz", SPECIALIST)
    done_case = store.create_lifecycle_case("carol", "onboarding", SPECIALIST, task_titles=["Badge"])
    store.set_task_state(done_case["id"], "t-1", "done", SPECIALIST)
    store.create_lifecycle_case("carol", "separation", SPECIALIST)
    review = store.create_performance_review("carol", "2026", SPECIALIST)
    store.set_review_state(review["id"], "in_progress", SPECIALIST)
    ben = store.create_benefits_record("carol", "benefit_enrollment", "plan-a", SPECIALIST)
    store.set_benefits_state(ben["id"], "active", SPECIALIST)
    case = store.create_case("carol", "award", "Award", SPECIALIST)
    store.set_case_state(case["id"], "in_review", SPECIALIST)
    store.set_position_status(position["id"], "filled", SPECIALIST)
    return store


class TestReporting(unittest.TestCase):
    """Core 10: counts/summaries over all record families."""

    def test_report_counts(self):
        """Core 10 (AU-6/CA-7): report counts every record family and breaks each down by status/stage/state."""
        report = _populated().report(ADMIN)
        self.assertEqual(report["persons"], 2)
        self.assertEqual(report["persons_by_status"]["active"], 1)
        self.assertEqual(report["persons_by_status"]["applicant"], 1)
        self.assertEqual(report["positions"], 1)
        self.assertEqual(report["positions_by_status"]["filled"], 1)
        self.assertEqual(report["vacancies"], 1)
        self.assertEqual(report["vacancies_by_status"]["posted"], 1)
        self.assertEqual(report["applications"], 1)
        self.assertEqual(report["applications_by_stage"]["screened"], 1)
        self.assertEqual(report["evaluations"], 1)
        self.assertEqual(report["evaluations_by_state"]["scheduled"], 1)
        self.assertEqual(report["performance_reviews"], 1)
        self.assertEqual(report["performance_reviews_by_state"]["in_progress"], 1)
        self.assertEqual(report["benefits_records"], 1)
        self.assertEqual(report["benefits_records_by_state"]["active"], 1)
        self.assertEqual(report["cases"], 1)
        self.assertEqual(report["cases_by_state"]["in_review"], 1)

    def test_report_lifecycle_uses_derived_status(self):
        """Core 10 / Core 6: lifecycle counts in the report are the derived statuses (one complete, one not_started)."""
        report = _populated().report(ADMIN)
        self.assertEqual(report["lifecycle_cases"], 2)
        self.assertEqual(
            report["lifecycle_cases_by_status"],
            {"cancelled": 0, "not_started": 1, "in_progress": 0, "complete": 1},
        )

    def test_report_permissions(self):
        """Core 10 / Core 11: admin, hr_specialist and auditor may report; an employee may not (report_read is not an employee permission)."""
        store = _populated()
        self.assertEqual(store.report(SPECIALIST)["persons"], 2)
        self.assertEqual(store.report(AUDITOR)["persons"], 2)
        with self.assertRaises(PermissionDenied):
            store.report(EMPLOYEE)

    def test_empty_report_shape(self):
        """Core 10: an empty store reports zeroes with the full key shape."""
        from hr_helpers import fresh_store
        report = fresh_store().report(ADMIN)
        self.assertEqual(report["persons"], 0)
        self.assertEqual(
            report["lifecycle_cases_by_status"],
            {"cancelled": 0, "not_started": 0, "in_progress": 0, "complete": 0},
        )
        self.assertEqual(report["applications_by_stage"]["applied"], 0)


if __name__ == "__main__":
    unittest.main()
