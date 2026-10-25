"""Reporting tests.

Traces to: Core function 8 (Reporting over the records; claim family
reporting_analytics 0/2 in this group, carried under the core-
boundary decision (3/8 at L2); AU-2). Reports read substrate records
only; dashboard/predictive engines are Extended.
"""

import unittest

from learn_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store
from learn.errors import PermissionDenied

AS_OF = "2026-06-15"


def _populated():
    store, course = make_store()
    other = store.create_course("Second Course", ADMIN)
    store.create_enrollment("carol", course["id"], INSTRUCTOR)
    store.create_enrollment("erin", course["id"], INSTRUCTOR)
    store.create_enrollment("erin", other["id"], INSTRUCTOR)
    store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
    store.record_progress("erin", course["id"], "in_progress", INSTRUCTOR)
    store.create_assessment("Quiz", "carol", INSTRUCTOR, course_id=course["id"], state="administered")
    store.create_credential("carol", "Cert", ADMIN)
    store.create_compliance_assignment("carol", course["id"], "2026-06-01", ADMIN)
    store.create_compliance_assignment("erin", course["id"], "2026-06-01", ADMIN)
    store.create_compliance_assignment("erin", other["id"], "2026-12-01", ADMIN)
    store.create_session("Session", course["id"], "2026-07-01T09:00:00Z", INSTRUCTOR)
    return store, course, other


class TestReporting(unittest.TestCase):
    """Core 8: counts/summaries over registry, enrollments, progress, assessments, credentials, compliance, sessions."""

    def test_report_counts(self):
        """Core 8 (AU-6/CA-7): report counts every record family and breaks progress/assessments/credentials down by status."""
        store, course, other = _populated()
        report = store.report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["courses"], 2)
        self.assertEqual(report["enrollments"], 3)
        self.assertEqual(report["enrollments_by_course"], {course["id"]: 2, other["id"]: 1})
        self.assertEqual(report["progress_records"], 2)
        self.assertEqual(report["progress_by_status"]["completed"], 1)
        self.assertEqual(report["progress_by_status"]["in_progress"], 1)
        self.assertEqual(report["assessments"], 1)
        self.assertEqual(report["assessments_by_state"]["administered"], 1)
        self.assertEqual(report["credentials"], 1)
        self.assertEqual(report["credentials_by_status"]["active"], 1)
        self.assertEqual(report["sessions"], 1)

    def test_report_compliance_uses_derived_status(self):
        """Core 8 / Core 6: compliance counts in the report are the derived statuses at as_of (carol completed, erin overdue on course 1, current on course 2)."""
        store, _, _ = _populated()
        report = store.report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["compliance_assignments"], 3)
        self.assertEqual(
            report["compliance_by_status"], {"current": 1, "overdue": 1, "completed": 1}
        )
        earlier = store.report(ADMIN, as_of="2026-05-01")
        self.assertEqual(
            earlier["compliance_by_status"], {"current": 2, "overdue": 0, "completed": 1}
        )

    def test_report_permissions(self):
        """Core 8 / Core 9: admin, instructor and auditor may report; a learner may not (report_read is not a learner permission)."""
        store, _, _ = _populated()
        self.assertEqual(store.report(INSTRUCTOR, as_of=AS_OF)["courses"], 2)
        self.assertEqual(store.report(AUDITOR, as_of=AS_OF)["courses"], 2)
        with self.assertRaises(PermissionDenied):
            store.report(LEARNER, as_of=AS_OF)

    def test_empty_report_shape(self):
        """Core 8: an empty store reports zeroes with the full key shape."""
        from learn_helpers import fresh_store
        report = fresh_store().report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["courses"], 0)
        self.assertEqual(report["compliance_by_status"], {"current": 0, "overdue": 0, "completed": 0})
        self.assertEqual(report["as_of"], AS_OF)


if __name__ == "__main__":
    unittest.main()
