"""Mutation-verified negative control — the decision-basis guard.

The signature invariant is the decision-basis guard: a decision
record may not be recorded without at least one basis intent that
exists and belongs to the same organization, because the function
this set claims is the transformation of engineering intent into
decisions, and a decision resting on no intent transforms
nothing. An oracle that passes whether or not the guard enforces
would be testing that code ran, not that the guard holds.

This module carries the drill's in-tree form: the canonical check
on the real store, the same check against a monkeypatched mutant
of the guard seam (``_check_decision_basis`` replaced with a
no-op), and the discriminating other arm — a decision resting on
exactly one valid basis intent IS recorded on the real store, so
the invariant is a floor of one, not a ban. The live drill
(patching the seam in ``src/manufacturing/store.py`` and re-running
the whole suite) is recorded in tests/README.md.
"""

import unittest
from unittest import mock

from manufacturing import store as store_module
from manufacturing.errors import ValidationError

import manufacturing_helpers as H


def _mutant_check_decision_basis(intents_by_id, org_id, basis_intent_ids):
    """The mutant: the guard seam with its body replaced by a
    no-op — every basis (including none) is waved through."""
    return None


class TestNegativeControl(unittest.TestCase):
    def test_canonical_guard_refuses_basisless_decision(self):
        store, audit, org = H.make_store()
        H.make_intent(store, org)
        with self.assertRaises(ValidationError):
            store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                  [], "eng-2")
        self.assertEqual(store.list_decisions(H.ADMIN), [])

    def test_mutant_waves_basisless_decision_through(self):
        store, audit, org = H.make_store()
        with mock.patch.object(store_module, "_check_decision_basis",
                               _mutant_check_decision_basis):
            decision = store.record_decision(
                H.OPERATOR, org["id"], "L", "S", [], "eng-2")
        # The mutant recorded a decision resting on nothing: the
        # guard, not the plumbing, is what refuses it.
        self.assertEqual(decision["basis_intent_ids"], [])

    def test_treating_mutant_outcome_as_expected_fails(self):
        store, audit, org = H.make_store()
        with mock.patch.object(store_module, "_check_decision_basis",
                               _mutant_check_decision_basis):
            with self.assertRaises(AssertionError):
                with self.assertRaises(ValidationError):
                    store.record_decision(H.OPERATOR, org["id"], "L",
                                          "S", [], "eng-2")

    def test_single_valid_basis_is_recorded_on_the_real_store(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        decision = H.make_decision(store, org, intent)
        self.assertEqual(decision["basis_intent_ids"], [intent["id"]])


if __name__ == "__main__":
    unittest.main()
