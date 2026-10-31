"""Negative control: the stage bounds rule must be load-bearing.

Traces to: the contract's required negative control for the Talent
Management group (Core function 5, SI-10). The group's signature
invariant is the stage bounds rule: a stage movement's stage_index
must always satisfy 0 <= stage_index < len(stages) for the
placement's pipeline, enforced by the store's
``_check_stage_bounds`` seam before any movement is stored, so a
placement's derived current stage always names a real stage.

Canonical expectation: a movement to index len(stages) is rejected
whole, a negative index is rejected, and a boolean is rejected.
The mutant is a ``TalentMgmtStore`` subclass whose
``_check_stage_bounds`` does nothing: if the suite still passed
against the mutant, the bounds tests would be testing that code
ran, not that the invariant holds. Each test asserts (1) the
canonical expectation from the real implementation, (2) the mutant
would NOT produce that expectation, and (3) a literal
``assertRaises(AssertionError)`` showing that treating the mutant's
outcome as the expected outcome fails.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import ValidationError
from talentmgmt.store import TalentMgmtStore


class MutantTalentMgmtStore(TalentMgmtStore):
    """A store with the stage bounds check removed (the mutant)."""

    def _check_stage_bounds(self, pipeline, stage_index):
        return None


def _placement(store):
    org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
    store.add_member(org["id"], H.MEMBER.name, H.ADMIN)
    store.register_candidate(org["id"], H.CANDIDATE_REF, H.CANDIDATE_LABEL,
                             H.MEMBER)
    requisition = store.create_requisition(org["id"], H.REQUISITION_REF,
                                           H.REQUISITION_TITLE, H.MEMBER)
    pipeline = store.create_pipeline(org["id"], H.PIPELINE_REF,
                                     requisition["id"], list(H.STAGES),
                                     H.MEMBER)
    placement = store.place_candidate(org["id"], pipeline["id"],
                                      H.PLACEMENT_REF, H.CANDIDATE_REF,
                                      H.MEMBER)
    return org, placement


class TestNegativeControlStageBounds(unittest.TestCase):
    """Canonical: out-of-bounds stage movements are rejected; the
    mutant waves them through and its derived stage breaks."""

    def test_canonical_expectation_rejects_out_of_bounds_movement(self):
        """Canonical (Core 5): an in-bounds movement is recorded;
        the index == len(stages) movement raises ValidationError
        and the recorded set and derived stage are unchanged."""
        store = H.fresh_store()
        org, placement = _placement(store)
        store.record_movement(org["id"], placement["id"], "MOV-1", 2,
                              H.MEMBER)
        with self.assertRaises(ValidationError):
            store.record_movement(org["id"], placement["id"], "MOV-2",
                                  len(H.STAGES), H.MEMBER)
        recorded = store.list_movements(org["id"], placement["id"],
                                        H.MEMBER)
        self.assertEqual([m["movement_ref"] for m in recorded], ["MOV-1"])
        view = store.get_placement(org["id"], placement["id"], H.MEMBER)
        self.assertEqual(view["current_stage"], "Interview")

    def test_mutant_would_not_reject(self):
        """Mutant: with the seam removed, the same out-of-bounds
        movement is stored — and the placement's derived view then
        raises IndexError, because the stored index names no
        stage. The canonical expectation, applied to the mutant's
        outcome, fails (asserted literally with assertRaises)."""
        store = MutantTalentMgmtStore()
        org, placement = _placement(store)
        store.record_movement(org["id"], placement["id"], "MOV-1", 2,
                              H.MEMBER)
        second = store.record_movement(org["id"], placement["id"], "MOV-2",
                                       len(H.STAGES), H.MEMBER)
        self.assertEqual(second["stage_index"], len(H.STAGES))
        recorded = store.list_movements(org["id"], placement["id"],
                                        H.MEMBER)
        self.assertEqual(len(recorded), 2)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(recorded), 1)
        with self.assertRaises(IndexError):
            store.get_placement(org["id"], placement["id"], H.MEMBER)

    def test_mutant_also_breaks_negative_and_boolean_indices(self):
        """Mutant contrast: the real store rejects a negative
        index and a boolean index; the mutant accepts a negative
        index, whose derived view silently resolves to the
        pipeline's LAST stage (Python negative indexing) — the
        placement appears to sit at "Decision" without ever
        passing a single stage gate."""
        real = H.fresh_store()
        org, placement = _placement(real)
        with self.assertRaises(ValidationError):
            real.record_movement(org["id"], placement["id"], "MOV-NEG",
                                 -1, H.MEMBER)
        with self.assertRaises(ValidationError):
            real.record_movement(org["id"], placement["id"], "MOV-BOOL",
                                 True, H.MEMBER)
        view = real.get_placement(org["id"], placement["id"], H.MEMBER)
        self.assertEqual(view["current_stage"], "Applied")

        mutant = MutantTalentMgmtStore()
        org, placement = _placement(mutant)
        accepted = mutant.record_movement(org["id"], placement["id"],
                                          "MOV-NEG", -1, H.MEMBER)
        self.assertEqual(accepted["stage_index"], -1)
        mutant_view = mutant.get_placement(org["id"], placement["id"],
                                           H.MEMBER)
        self.assertEqual(mutant_view["current_stage"], "Decision")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_view["current_stage"], "Applied")


if __name__ == "__main__":
    unittest.main()
