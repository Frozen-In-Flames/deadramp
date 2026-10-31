"""Core: Search & summary reporting. Traces to UNION-SPEC core
function 10 (reporting, opportunity_exploration). Summaries are
counts and money sums computed on read from records only — never
scores, never stored."""

import unittest

import grants_helpers as H


class TestProgramSummary(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_empty_program_summary(self):
        summary = self.store.program_summary(H.MEMBER, self.program["id"],
                                             now=H.NOW_OPEN)
        self.assertEqual(summary["status"], "open")
        self.assertEqual(summary["awarded_cents"], 0)
        self.assertEqual(summary["remaining_cents"], H.BUDGET_CENTS)
        self.assertEqual(summary["applications_by_status"]["draft"], 0)
        self.assertEqual(summary["awards"], 0)

    def test_summary_counts_from_records(self):
        app, result = H.make_award(self.store, self.program, self.org,
                                   amount_cents=400_000)
        award = result["award"]
        declined = H.make_under_review(self.store, self.program, self.org,
                                       summary="Second project")
        self.store.decide_application(H.STAFF, declined["id"], False,
                                      note="Out of scope")
        H.make_application(self.store, self.program, self.org,
                           summary="Third project, still drafting")
        self.store.create_report(H.MEMBER, award["id"], "progress",
                                 "2026-09-30")
        final = self.store.create_report(H.MEMBER, award["id"], "final",
                                         "2027-03-31")
        self.store.submit_report(H.MEMBER, final["id"], "All done",
                                 submitted_at="2027-03-01")
        summary = self.store.program_summary(H.MEMBER, self.program["id"],
                                             now="2026-10-15")
        self.assertEqual(summary["applications_by_status"]["awarded"], 1)
        self.assertEqual(summary["applications_by_status"]["declined"], 1)
        self.assertEqual(summary["applications_by_status"]["draft"], 1)
        self.assertEqual(summary["awards"], 1)
        self.assertEqual(summary["awarded_cents"], 400_000)
        self.assertEqual(summary["remaining_cents"], 600_000)
        self.assertEqual(summary["reports_by_status"],
                         {"pending": 0, "overdue": 1, "submitted": 1})


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()
        H.make_application(self.store, self.program, self.org,
                           summary="After-school tutoring expansion")

    def test_search_finds_all_three_kinds(self):
        hits = self.store.search(H.MEMBER, "community")
        self.assertEqual(len(hits["programs"]), 1)
        self.assertEqual(len(hits["organizations"]), 1)  # "Community Builders"
        hits = self.store.search(H.MEMBER, "tutoring")
        self.assertEqual(len(hits["applications"]), 1)

    def test_search_is_case_insensitive(self):
        hits = self.store.search(H.MEMBER, "TUTORING")
        self.assertEqual(len(hits["applications"]), 1)

    def test_outsider_search_sees_no_program_content(self):
        hits = self.store.search(H.OUTSIDER, "community")
        self.assertEqual(hits["programs"], [])
        self.assertEqual(hits["applications"], [])
        # Organizations are a global registry, visible to any reader.
        self.assertEqual(len(hits["organizations"]), 1)


if __name__ == "__main__":
    unittest.main()
