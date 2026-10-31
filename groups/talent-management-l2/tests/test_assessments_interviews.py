"""Core 8 Assessments & Core 9 Interviews.

Traces to: UNION-SPEC.md Core 8-9 and the HireVue claims —
assessment records whose only outcome is the caller's verbatim
label (no content, no computed score, per the privacy discipline
and the checked absence of any scoring vocabulary), and interview
records of the descriptions' kinds (video / in_person) holding
metadata only: no recording, transcript, or notes field exists.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import ValidationError


class TestAssessments(unittest.TestCase):
    """Core 8: assessment records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)

    def _assess(self, **overrides):
        kwargs = {"assessment_ref": "ASM-1",
                  "candidate_ref": H.CANDIDATE_REF,
                  "instrument_label": "Work Style Inventory"}
        kwargs.update(overrides)
        return self.store.record_assessment(self.org["id"], actor=H.MEMBER,
                                            **kwargs)

    def test_assessment_shape_outcome_starts_empty(self):
        """Core 8: the assessment dict has exactly the contract's
        keys; status starts assigned and outcome_label None — and
        no score-shaped key exists."""
        assessment = self._assess()
        self.assertEqual(set(assessment), {
            "id", "org_id", "assessment_ref", "candidate_ref",
            "instrument_label", "requisition_id", "status",
            "outcome_label", "created_by", "created_utc"})
        self.assertEqual(assessment["status"], "assigned")
        self.assertIsNone(assessment["outcome_label"])

    def test_completion_records_the_callers_label_verbatim(self):
        """Core 8: completion stores the caller-supplied outcome
        label exactly as given — recorded, never computed."""
        assessment = self._assess()
        done = self.store.complete_assessment(
            self.org["id"], assessment["id"],
            "Meets the validated benchmark", H.MEMBER)
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["outcome_label"],
                         "Meets the validated benchmark")
        with self.assertRaises(ValidationError):
            self.store.complete_assessment(
                self.org["id"], assessment["id"], "Again", H.MEMBER)

    def test_completion_requires_a_label(self):
        """Core 8 / SI-10: an empty outcome label is rejected and
        the assessment stays assigned."""
        assessment = self._assess()
        with self.assertRaises(ValidationError):
            self.store.complete_assessment(
                self.org["id"], assessment["id"], "  ", H.MEMBER)
        self.assertEqual(self.store.get_assessment(
            self.org["id"], assessment["id"], H.MEMBER)["status"],
            "assigned")

    def test_assessment_requires_registered_candidate(self):
        """Core 8: an assessment against an unregistered
        candidate reference is rejected."""
        with self.assertRaises(ValidationError):
            self._assess(candidate_ref="CAN-GHOST")

    def test_assessment_filters(self):
        """Core 8: listing filters by candidate and by status;
        an unknown status filter is rejected."""
        first = self._assess()
        self.store.complete_assessment(
            self.org["id"], first["id"], "Done", H.MEMBER)
        self._assess(assessment_ref="ASM-2")
        self.assertEqual(len(self.store.list_assessments(
            self.org["id"], H.MEMBER, status="assigned")), 1)
        self.assertEqual(len(self.store.list_assessments(
            self.org["id"], H.MEMBER,
            candidate_ref=H.CANDIDATE_REF)), 2)
        with self.assertRaises(ValidationError):
            self.store.list_assessments(self.org["id"], H.MEMBER,
                                        status="scored")


class TestInterviews(unittest.TestCase):
    """Core 9: interview records (metadata only)."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)

    def _schedule(self, **overrides):
        kwargs = {"interview_ref": "INT-1",
                  "candidate_ref": H.CANDIDATE_REF, "kind": "video"}
        kwargs.update(overrides)
        return self.store.schedule_interview(self.org["id"], actor=H.MEMBER,
                                             **kwargs)

    def test_interview_shape(self):
        """Core 9: the interview dict has exactly the contract's
        keys — kind, candidate reference, optional time; no
        recording or transcript field exists."""
        interview = self._schedule(
            scheduled_at="2030-04-02T14:00:00+00:00")
        self.assertEqual(set(interview), {
            "id", "org_id", "interview_ref", "candidate_ref", "kind",
            "requisition_id", "scheduled_at", "status", "created_by",
            "created_utc"})
        self.assertEqual(interview["status"], "scheduled")
        self.assertEqual(interview["kind"], "video")

    def test_kinds_are_the_descriptions_vocabulary(self):
        """Core 9: video (HireVue) and in_person (Yello's events
        surface) are the kinds; anything else is rejected."""
        in_person = self._schedule(interview_ref="INT-2", kind="in_person")
        self.assertEqual(in_person["kind"], "in_person")
        with self.assertRaises(ValidationError):
            self._schedule(interview_ref="INT-3", kind="phone")

    def test_interview_lifecycle_guarded(self):
        """Core 9: complete and cancel are one-way transitions
        out of scheduled."""
        interview = self._schedule()
        done = self.store.complete_interview(
            self.org["id"], interview["id"], H.MEMBER)
        self.assertEqual(done["status"], "completed")
        with self.assertRaises(ValidationError):
            self.store.cancel_interview(
                self.org["id"], interview["id"], H.MEMBER)
        second = self._schedule(interview_ref="INT-2")
        gone = self.store.cancel_interview(
            self.org["id"], second["id"], H.MEMBER)
        self.assertEqual(gone["status"], "cancelled")

    def test_interview_requires_registered_candidate(self):
        """Core 9: an interview against an unregistered candidate
        reference is rejected."""
        with self.assertRaises(ValidationError):
            self._schedule(candidate_ref="CAN-GHOST")


if __name__ == "__main__":
    unittest.main()
