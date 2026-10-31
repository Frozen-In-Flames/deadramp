"""Core 11 Registry reporting & Core 12 Registry search.

Traces to: UNION-SPEC.md Core 11-12 and Yello's applicant
metrics & analytics claim — the report is counts computed on
read, including the current-stage distribution of active
placements derived from their movement records; no score,
ranking, ratio, or ROI figure is computed anywhere. Search is a
literal substring match over registry metadata, scoped by
membership.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import ValidationError

REPORT_KEYS = {
    "org_id", "candidate_count", "requisition_count",
    "requisitions_by_status", "pipeline_count", "placement_count",
    "placements_by_stage", "event_count", "events_by_kind",
    "events_by_status", "registration_count", "checked_in_count",
    "assessment_count", "assessments_by_status", "interview_count",
    "interviews_by_kind", "interviews_by_status", "workflow_count",
}

BANNED_KEYS = {"score", "scores", "rating", "rank", "ranking",
               "match", "roi", "ratio", "percentile"}


def _scan(obj, path="$"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key
            yield from _scan(value, path + "." + str(key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _scan(value, "%s[%d]" % (path, index))


class TestReport(unittest.TestCase):
    """Core 11: reporting is counts only, computed on read."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)
        H.make_candidate(self.store, self.org,
                         candidate_ref=H.CANDIDATE2_REF)
        self.requisition = H.make_requisition(self.store, self.org)
        self.pipeline = H.make_pipeline(self.store, self.org,
                                        self.requisition)
        self.placement = H.make_placement(self.store, self.org,
                                          self.pipeline)
        self.store.record_movement(self.org["id"], self.placement["id"],
                                   "MOV-1", 2, H.MEMBER)
        second = H.make_placement(self.store, self.org, self.pipeline,
                                  placement_ref="PLC-2",
                                  candidate_ref=H.CANDIDATE2_REF)
        self.store.record_movement(self.org["id"], second["id"], "MOV-1",
                                   2, H.MEMBER)
        self.store.withdraw_placement(self.org["id"], second["id"],
                                      H.MEMBER)
        self.event = H.make_event(self.store, self.org)
        registration = self.store.register_for_event(
            self.org["id"], self.event["id"], "REG-1", H.CANDIDATE_REF,
            H.MEMBER)
        self.store.check_in_registration(self.org["id"],
                                         registration["id"], H.MEMBER)
        assessment = self.store.record_assessment(
            self.org["id"], "ASM-1", H.CANDIDATE_REF, "Inventory",
            H.MEMBER)
        self.store.complete_assessment(self.org["id"], assessment["id"],
                                       "Complete", H.MEMBER)
        self.store.schedule_interview(self.org["id"], "INT-1",
                                      H.CANDIDATE_REF, "video", H.MEMBER)
        self.store.register_workflow(self.org["id"], "WFL-1", "Auto",
                                     H.MEMBER)

    def test_report_shape_is_pinned(self):
        """Core 11: the report carries exactly the contract's 18
        keys."""
        report = self.store.org_report(self.org["id"], H.MEMBER)
        self.assertEqual(set(report), REPORT_KEYS)
        self.assertEqual(len(report), 18)

    def test_report_counts(self):
        """Core 11 (Yello's analytics claim): counts reflect the
        recorded substrate, including check-ins and by-kind /
        by-status breakdowns."""
        report = self.store.org_report(self.org["id"], H.MEMBER)
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["requisition_count"], 1)
        self.assertEqual(report["requisitions_by_status"],
                         {"open": 1, "closed": 0})
        self.assertEqual(report["pipeline_count"], 1)
        self.assertEqual(report["placement_count"], 2)
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(report["events_by_kind"],
                         {"in_person": 1, "virtual": 0})
        self.assertEqual(report["registration_count"], 1)
        self.assertEqual(report["checked_in_count"], 1)
        self.assertEqual(report["assessment_count"], 1)
        self.assertEqual(report["assessments_by_status"],
                         {"assigned": 0, "completed": 1})
        self.assertEqual(report["interview_count"], 1)
        self.assertEqual(report["interviews_by_kind"],
                         {"video": 1, "in_person": 0})
        self.assertEqual(report["workflow_count"], 1)

    def test_stage_distribution_counts_active_placements_only(self):
        """Core 11: placements_by_stage is the derived current
        stage of active placements — the withdrawn placement's
        stage is excluded even though its movements remain."""
        report = self.store.org_report(self.org["id"], H.MEMBER)
        self.assertEqual(report["placements_by_stage"],
                         {"Interview": 1})

    def test_report_computes_no_score(self):
        """Core 11 / privacy: a recursive key scan finds no
        score-shaped key anywhere in the report."""
        report = self.store.org_report(self.org["id"], H.MEMBER)
        for path, key in _scan(report):
            self.assertNotIn(str(key).lower(), BANNED_KEYS,
                             "%s.%s" % (path, key))


class TestSearch(unittest.TestCase):
    """Core 12: registry search."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)
        requisition = H.make_requisition(self.store, self.org)
        H.make_pipeline(self.store, self.org, requisition)
        H.make_event(self.store, self.org)

    def test_search_matches_refs_titles_and_stage_labels(self):
        """Core 12: substring match is case-insensitive and
        reaches references, titles, and pipeline stage labels."""
        by_ref = self.store.search_registry(H.MEMBER, "can-ref")
        self.assertEqual(len(by_ref["candidates"]), 1)
        by_title = self.store.search_registry(H.MEMBER, "program analyst")
        self.assertEqual(len(by_title["requisitions"]), 1)
        by_stage = self.store.search_registry(H.MEMBER, "interview")
        self.assertEqual(len(by_stage["pipelines"]), 1)
        by_event = self.store.search_registry(H.MEMBER, "recruiting fair")
        self.assertEqual(len(by_event["events"]), 1)

    def test_search_is_membership_scoped(self):
        """Core 12 / AC-3: an outsider's search sees nothing; a
        platform admin sees the organization's records."""
        outsider = self.store.search_registry(H.OUTSIDER, "CAN")
        for key, hits in outsider.items():
            self.assertEqual(hits, [], key)
        admin = self.store.search_registry(H.ADMIN, "CAN-REF")
        self.assertEqual(len(admin["candidates"]), 1)

    def test_empty_query_rejected(self):
        """Core 12 / SI-10: an empty or blank query raises
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.search_registry(H.MEMBER, "   ")


if __name__ == "__main__":
    unittest.main()
