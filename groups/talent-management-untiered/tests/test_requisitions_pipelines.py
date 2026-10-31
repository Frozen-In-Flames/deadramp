"""Core 3 Requisitions & Core 4 Pipeline definitions.

Traces to: UNION-SPEC.md Core 3-4 — requisitions with optional
open/close times and a derived past_close that lives only on read
views; pipelines as ordered stage-label lists against one
requisition (a definition is a record; nothing about it executes
or moves anyone).
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import NotFoundError, ValidationError

FAR_PAST = "2020-01-01T00:00:00+00:00"
FAR_FUTURE = "2030-01-01T00:00:00+00:00"


class TestRequisitions(unittest.TestCase):
    """Core 3: requisition records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_stored_shape_has_no_derived_key(self):
        """Core 3: the stored record carries exactly the
        contract's keys — past_close is not among them."""
        requisition = H.make_requisition(self.store, self.org)
        self.assertEqual(set(requisition), {
            "id", "org_id", "requisition_ref", "title", "opens_at",
            "closes_at", "status", "created_by", "created_utc"})
        self.assertEqual(requisition["status"], "open")
        stored = self.store._requisitions[requisition["id"]]
        self.assertNotIn("past_close", stored)

    def test_past_close_derived_at_read(self):
        """Core 3: past_close flips with the read clock — false
        before the close time, true after it, false with no
        close time — and is computed on the view only."""
        timed = H.make_requisition(self.store, self.org,
                                   closes_at="2026-06-01")
        self.assertFalse(self.store.get_requisition(
            self.org["id"], timed["id"], H.MEMBER, now="2026-05-01")["past_close"])
        self.assertTrue(self.store.get_requisition(
            self.org["id"], timed["id"], H.MEMBER, now="2026-07-01")["past_close"])
        open_ended = H.make_requisition(
            self.store, self.org, requisition_ref="REQ-OPEN")
        self.assertFalse(self.store.get_requisition(
            self.org["id"], open_ended["id"], H.MEMBER,
            now="2999-01-01")["past_close"])

    def test_closes_before_opens_rejected(self):
        """Core 3 / SI-10: a close time preceding the open time is
        rejected, as is an unparseable time."""
        with self.assertRaises(ValidationError):
            H.make_requisition(self.store, self.org, opens_at=FAR_FUTURE,
                               closes_at=FAR_PAST)
        with self.assertRaises(ValidationError):
            H.make_requisition(self.store, self.org, closes_at="not-a-date")

    def test_duplicate_ref_rejected(self):
        """Core 3 / SI-10: requisition_ref is unique within the
        organization."""
        H.make_requisition(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_requisition(self.store, self.org)

    def test_close_lifecycle_guarded(self):
        """Core 3: close moves open -> closed exactly once; a
        second close raises ValidationError."""
        requisition = H.make_requisition(self.store, self.org)
        closed = self.store.close_requisition(
            self.org["id"], requisition["id"], H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_requisition(
                self.org["id"], requisition["id"], H.MEMBER)

    def test_cross_org_requisition_not_found(self):
        """Core 3: a requisition read through another organization
        raises NotFoundError."""
        requisition = H.make_requisition(self.store, self.org)
        other = self.store.create_organization("ORG-X", "X", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_requisition(other["id"], requisition["id"],
                                       H.ADMIN)


class TestPipelines(unittest.TestCase):
    """Core 4: pipeline definitions."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.requisition = H.make_requisition(self.store, self.org)

    def test_pipeline_shape_and_stages(self):
        """Core 4: the pipeline dict carries the ordered stage
        list verbatim."""
        pipeline = H.make_pipeline(self.store, self.org, self.requisition)
        self.assertEqual(set(pipeline), {
            "id", "org_id", "pipeline_ref", "requisition_id", "stages",
            "label", "created_by", "created_utc"})
        self.assertEqual(pipeline["stages"], H.STAGES)
        self.assertEqual(pipeline["id"], "pip-1")

    def test_stages_view_is_a_copy(self):
        """Core 4: mutating a returned stage list does not corrupt
        the stored definition."""
        pipeline = H.make_pipeline(self.store, self.org, self.requisition)
        pipeline["stages"].append("Hacked")
        fresh = self.store.get_pipeline(self.org["id"], pipeline["id"],
                                        H.MEMBER)
        self.assertEqual(fresh["stages"], H.STAGES)

    def test_stage_list_validation(self):
        """Core 4 / SI-10: stages must be a non-empty list of
        non-empty, unique labels."""
        for bad in ([], "Applied", ["Applied", ""], ["Applied", "Applied"],
                    [None], [7]):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                H.make_pipeline(self.store, self.org, self.requisition,
                                stages=bad)

    def test_requisition_link_must_exist(self):
        """Core 4: a pipeline against a missing requisition raises
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            H.make_pipeline(self.store, self.org, self.requisition,
                            requisition_id="req-999")

    def test_duplicate_pipeline_ref_rejected(self):
        """Core 4 / SI-10: pipeline_ref is unique within the
        organization."""
        H.make_pipeline(self.store, self.org, self.requisition)
        with self.assertRaises(ValidationError):
            H.make_pipeline(self.store, self.org, self.requisition)

    def test_list_pipelines_filter_by_requisition(self):
        """Core 4: listing can be scoped to one requisition."""
        H.make_pipeline(self.store, self.org, self.requisition)
        other_req = H.make_requisition(self.store, self.org,
                                       requisition_ref="REQ-2")
        self.assertEqual(self.store.list_pipelines(
            self.org["id"], H.MEMBER, requisition_id=other_req["id"]), [])
        self.assertEqual(len(self.store.list_pipelines(
            self.org["id"], H.MEMBER,
            requisition_id=self.requisition["id"])), 1)


if __name__ == "__main__":
    unittest.main()
