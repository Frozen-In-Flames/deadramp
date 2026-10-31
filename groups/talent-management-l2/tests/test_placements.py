"""Core 5 Placements & stage movements — the stage bounds seam.

Traces to: UNION-SPEC.md Core 5 and the signature invariant: a
movement's stage_index must satisfy 0 <= stage_index <
len(stages), enforced by the store's _check_stage_bounds seam
before anything is stored; a placement's current stage is derived
from its append-only movement records at read and is never a
stored field.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import NotFoundError, ValidationError


class TestPlacements(unittest.TestCase):
    """Core 5: placements, movements, and the derived stage."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)
        self.requisition = H.make_requisition(self.store, self.org)
        self.pipeline = H.make_pipeline(self.store, self.org, self.requisition)
        self.placement = H.make_placement(self.store, self.org, self.pipeline)

    def test_stored_placement_has_no_stage_keys(self):
        """Core 5: the stored placement carries exactly the
        contract's keys — no stage field is ever stored."""
        self.assertEqual(set(self.placement), {
            "id", "org_id", "pipeline_id", "placement_ref",
            "candidate_ref", "status", "created_by", "created_utc"})
        self.assertEqual(self.placement["status"], "active")
        stored = self.store._placements[self.placement["id"]]
        self.assertNotIn("current_stage", stored)
        self.assertNotIn("current_stage_index", stored)

    def test_initial_stage_is_first_stage(self):
        """Core 5: with no movements, the derived current stage is
        index 0 — the pipeline's first stage."""
        view = self.store.get_placement(self.org["id"], self.placement["id"],
                                        H.MEMBER)
        self.assertEqual(view["current_stage_index"], 0)
        self.assertEqual(view["current_stage"], "Applied")

    def test_movement_shape_and_derivation(self):
        """Core 5: a movement record has the contract's shape, and
        the derived stage follows the most recent movement."""
        movement = self.store.record_movement(
            self.org["id"], self.placement["id"], "MOV-1", 2, H.MEMBER,
            label="Panel scheduled")
        self.assertEqual(set(movement), {
            "id", "org_id", "placement_id", "movement_ref",
            "stage_index", "label", "created_by", "created_utc"})
        view = self.store.get_placement(self.org["id"], self.placement["id"],
                                        H.MEMBER)
        self.assertEqual((view["current_stage_index"],
                          view["current_stage"]), (2, "Interview"))
        self.store.record_movement(
            self.org["id"], self.placement["id"], "MOV-2", 1, H.MEMBER)
        view = self.store.get_placement(self.org["id"], self.placement["id"],
                                        H.MEMBER)
        self.assertEqual((view["current_stage_index"],
                          view["current_stage"]), (1, "Screen"))

    def test_last_stage_is_reachable(self):
        """Core 5: index len(stages) - 1 is in bounds (the bound
        is inclusive at the top stage)."""
        self.store.record_movement(
            self.org["id"], self.placement["id"], "MOV-TOP", 3, H.MEMBER)
        view = self.store.get_placement(self.org["id"], self.placement["id"],
                                        H.MEMBER)
        self.assertEqual(view["current_stage"], "Decision")

    def test_out_of_bounds_indices_rejected_whole(self):
        """Core 5 / SI-10 (the seam): index == len(stages), a
        larger index, and a negative index each raise
        ValidationError, record nothing, and consume no id."""
        for bad in (4, 99, -1):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.record_movement(
                    self.org["id"], self.placement["id"],
                    "MOV-BAD-%s" % bad, bad, H.MEMBER)
        self.assertEqual(self.store.list_movements(
            self.org["id"], self.placement["id"], H.MEMBER), [])
        movement = self.store.record_movement(
            self.org["id"], self.placement["id"], "MOV-OK", 1, H.MEMBER)
        self.assertEqual(movement["id"], "mov-1")

    def test_non_integer_indices_rejected(self):
        """Core 5 / SI-10 (the seam): booleans, floats, and
        strings are not stage indices."""
        for bad in (True, 1.0, "2", None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.record_movement(
                    self.org["id"], self.placement["id"], "MOV-T", bad,
                    H.MEMBER)
        self.assertEqual(self.store.list_movements(
            self.org["id"], self.placement["id"], H.MEMBER), [])

    def test_duplicate_movement_ref_rejected(self):
        """Core 5 / SI-10: movement_ref is unique within the
        placement."""
        self.store.record_movement(
            self.org["id"], self.placement["id"], "MOV-1", 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_movement(
                self.org["id"], self.placement["id"], "MOV-1", 2, H.MEMBER)

    def test_movement_against_withdrawn_placement_rejected(self):
        """Core 5: withdrawing a placement ends its movements;
        withdrawing twice is also rejected."""
        self.store.withdraw_placement(self.org["id"], self.placement["id"],
                                      H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_movement(
                self.org["id"], self.placement["id"], "MOV-1", 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.withdraw_placement(
                self.org["id"], self.placement["id"], H.MEMBER)

    def test_duplicate_active_placement_rejected_replace_after_withdraw(self):
        """Core 5: one active placement per candidate per
        pipeline; after withdrawal the candidate can be placed
        again."""
        with self.assertRaises(ValidationError):
            H.make_placement(self.store, self.org, self.pipeline,
                             placement_ref="PLC-2")
        self.store.withdraw_placement(self.org["id"], self.placement["id"],
                                      H.MEMBER)
        replaced = H.make_placement(self.store, self.org, self.pipeline,
                                    placement_ref="PLC-2")
        self.assertEqual(replaced["status"], "active")

    def test_unregistered_candidate_cannot_be_placed(self):
        """Core 5: placement requires a registered candidate
        reference."""
        with self.assertRaises(ValidationError):
            H.make_placement(self.store, self.org, self.pipeline,
                             placement_ref="PLC-9",
                             candidate_ref="CAN-GHOST")

    def test_cross_org_placement_not_found(self):
        """Core 5: a placement read through another organization
        raises NotFoundError."""
        other = self.store.create_organization("ORG-X", "X", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_placement(other["id"], self.placement["id"],
                                     H.ADMIN)


if __name__ == "__main__":
    unittest.main()
