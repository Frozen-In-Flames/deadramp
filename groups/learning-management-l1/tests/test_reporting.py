"""Reporting & search tests.

Traces to: Core function 11 (Reporting & search) -- report(actor,
as_of=None) requires report_read and counts every record family with
registrations_by_state / authorizations_by_state / progress_by_status
breakdowns and compliance_by_status derived at as_of; search(query,
actor) requires report_read and matches substrings case-insensitively
over course title/code, content title, learner ref/label and event
title. At L1 the report additionally counts organizations,
certificates and continuing_education_records (Core functions
15-17), and search additionally covers organizations (match on ref,
label, portal_label) returned under ``"organizations"``.
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, fresh_store, make_store
from lms.errors import PermissionDenied, ValidationError

AS_OF = "2026-06-15"

COUNT_KEYS = (
    "learners", "courses", "content_items", "lesson_plans", "events",
    "registrations", "authorizations", "development_plans",
    "competencies", "learner_competency_records", "progress_records",
    "statements", "compliance_assignments", "workflows", "notifications",
    "organizations", "certificates", "continuing_education_records",
)


def _populated():
    store, learner, course = make_store()
    store.create_learner("erin", "Erin Learner", ADMIN)
    other = store.create_course("Second Course", ADMIN)
    item = store.create_content_item("Safety Video", "mp4", ADMIN,
                                     course_id=course["id"])
    store.create_lesson_plan("Week 1", course["id"], ADMIN,
                             item_refs=[item["id"]])
    event = store.create_event("Safety Briefing", "2026-07-01T09:00:00Z",
                               INSTRUCTOR, course_id=course["id"], capacity=1)
    store.register_learner(event["id"], "carol", INSTRUCTOR)
    store.register_learner(event["id"], "erin", INSTRUCTOR)  # waitlisted
    auth = store.create_authorization("carol", "SF-182", INSTRUCTOR,
                                      course_id=course["id"])
    store.decide_authorization(auth["id"], "approved", ADMIN)
    store.create_authorization("erin", "SF-182 B", INSTRUCTOR, course_id=course["id"])
    store.create_development_plan("carol", "Grow", INSTRUCTOR)
    comp = store.create_competency("Safety Awareness", INSTRUCTOR)
    store.record_learner_competency("carol", comp["id"], "L2", INSTRUCTOR)
    store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
    store.record_progress("erin", course["id"], "in_progress", INSTRUCTOR)
    store.record_statement("carol", "completed", course["id"], INSTRUCTOR)
    store.create_compliance_assignment("carol", course["id"], "2026-06-01", ADMIN)
    store.create_compliance_assignment("erin", course["id"], "2026-06-01", ADMIN)
    store.create_compliance_assignment("erin", other["id"], "2026-12-01", ADMIN)
    store.create_workflow("Onboarding", ["step one"], INSTRUCTOR)
    store.record_notification("carol", "Hello", INSTRUCTOR)
    store.create_organization("acme", "Acme Health", ADMIN,
                              portal_label="Acme Portal")
    store.record_certificate("carol", "Safety Certificate", INSTRUCTOR,
                             course_id=course["id"], awarded_on="2026-06-10")
    store.record_continuing_education("carol", "act-1", "3.5 credits",
                                      INSTRUCTOR, recorded_on="2026-06-11")
    return store, course, other


class TestReporting(unittest.TestCase):
    """Core 11: report counts and derived compliance breakdown."""

    def test_empty_report_shape(self):
        """Core 11: an empty store reports zeroes with the full key shape, including all four breakdown dicts."""
        report = fresh_store().report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["as_of"], AS_OF)
        for key in COUNT_KEYS:
            with self.subTest(key=key):
                self.assertEqual(report[key], 0)
        self.assertEqual(report["registrations_by_state"],
                         {"registered": 0, "waitlisted": 0,
                          "cancelled": 0, "attended": 0})
        self.assertEqual(report["authorizations_by_state"],
                         {"requested": 0, "approved": 0, "declined": 0})
        self.assertEqual(report["progress_by_status"],
                         {"not_started": 0, "in_progress": 0, "completed": 0})
        self.assertEqual(report["compliance_by_status"],
                         {"current": 0, "overdue": 0, "completed": 0})

    def test_report_counts(self):
        """Core 11: a populated store reports counts for every family and the state/status breakdowns."""
        store, _, _ = _populated()
        report = store.report(ADMIN, as_of=AS_OF)
        expected = {
            "learners": 2, "courses": 2, "content_items": 1, "lesson_plans": 1,
            "events": 1, "registrations": 2, "authorizations": 2,
            "development_plans": 1, "competencies": 1, "learner_competency_records": 1,
            "progress_records": 2, "statements": 1, "compliance_assignments": 3,
            "workflows": 1, "notifications": 1,
            "organizations": 1, "certificates": 1,
            "continuing_education_records": 1,
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(report[key], value)
        self.assertEqual(report["registrations_by_state"],
                         {"registered": 1, "waitlisted": 1,
                          "cancelled": 0, "attended": 0})
        self.assertEqual(report["authorizations_by_state"],
                         {"requested": 1, "approved": 1, "declined": 0})
        self.assertEqual(report["progress_by_status"],
                         {"not_started": 0, "in_progress": 1, "completed": 1})

    def test_report_compliance_uses_derived_status(self):
        """Core 11 / Core 9: compliance counts in the report are the derived statuses at as_of (carol completed, erin overdue on course 1, current on course 2), and change with as_of."""
        store, _, _ = _populated()
        report = store.report(ADMIN, as_of=AS_OF)
        self.assertEqual(report["compliance_by_status"],
                         {"current": 1, "overdue": 1, "completed": 1})
        earlier = store.report(ADMIN, as_of="2026-05-01")
        self.assertEqual(earlier["compliance_by_status"],
                         {"current": 2, "overdue": 0, "completed": 1})

    def test_report_permissions(self):
        """Core 11 / Core 13: admin, instructor and auditor may report; a learner may not (report_read is not a learner permission)."""
        store, _, _ = _populated()
        self.assertEqual(store.report(INSTRUCTOR, as_of=AS_OF)["courses"], 2)
        self.assertEqual(store.report(AUDITOR, as_of=AS_OF)["courses"], 2)
        with self.assertRaises(PermissionDenied):
            store.report(LEARNER, as_of=AS_OF)


class TestSearch(unittest.TestCase):
    """Core 11: substring search over catalog, learners and events."""

    def test_search_matches_case_insensitively(self):
        """Core 11: search matches substrings case-insensitively over course title/code, content title, learner ref/label, event title and organization ref/label/portal_label, returning exactly the five result families."""
        store, course, _other = _populated()
        learner = store.list_learners(ADMIN)[0]
        results = store.search("safety", ADMIN)
        self.assertEqual(set(results),
                         {"courses", "content_items", "learners", "events",
                          "organizations"})
        self.assertIn(course["id"], [c["id"] for c in results["courses"]])
        self.assertEqual(len(results["content_items"]), 1)
        self.assertEqual(len(results["events"]), 1)
        by_code = store.search("safe-101", AUDITOR)
        self.assertEqual([c["id"] for c in by_code["courses"]], [course["id"]])
        by_label = store.search("CAROL LEARNER", INSTRUCTOR)
        self.assertEqual([l["id"] for l in by_label["learners"]], [learner["id"]])
        by_ref = store.search("erin", ADMIN)
        self.assertEqual(len(by_ref["learners"]), 1)
        self.assertEqual(by_ref["learners"][0]["ref"], "erin")
        by_org_ref = store.search("ACME", ADMIN)
        self.assertEqual([o["ref"] for o in by_org_ref["organizations"]],
                         ["acme"])
        by_portal = store.search("acme portal", AUDITOR)
        self.assertEqual(len(by_portal["organizations"]), 1)
        self.assertEqual(by_portal["organizations"][0]["portal_label"],
                         "Acme Portal")

    def test_search_no_match_and_empty_query(self):
        """Core 11: a non-matching query returns empty families; an empty/blank query -> ValidationError."""
        store, _, _ = _populated()
        results = store.search("zzz-no-match", ADMIN)
        self.assertEqual(results, {"courses": [], "content_items": [],
                                   "learners": [], "events": [],
                                   "organizations": []})
        for bad in ("", "   "):
            with self.subTest(query=bad):
                with self.assertRaises(ValidationError):
                    store.search(bad, ADMIN)

    def test_search_requires_report_read(self):
        """Core 11 / Core 13: search requires report_read -- a learner is denied; instructor and auditor may search."""
        store, course, _other = _populated()
        with self.assertRaises(PermissionDenied):
            store.search("safety", LEARNER)
        self.assertIn(course["id"],
                      [c["id"] for c in store.search("safety", AUDITOR)["courses"]])


if __name__ == "__main__":
    unittest.main()
