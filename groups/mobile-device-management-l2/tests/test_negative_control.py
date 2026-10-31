"""Negative control: the derived-availability invariant must be
load-bearing.

The group's signature invariant is that a budget's available value
is *derived at read* — budget minus obligated minus spent, computed
from the obligation records every time, never stored. The canonical
expectation: with a 1,000,000-cent budget, 300,000 obligated and
200,000 spent, availability is 500,000. The mutant is an MdmStore
subclass whose derivation ignores the obligations and returns the
bare budget: if the suite still passed against the mutant, the
budget tests would be testing that code ran, not that the
derivation holds. (The fleet/asset sibling groups verified the
same derivation discipline with the same drill shape.)
"""

import unittest

import mdm_helpers as H
from mdm.store import MdmStore


class MutantMdmStore(MdmStore):
    """A store whose availability derivation ignores obligations."""

    def _available_cents(self, budget):
        return budget["budget_cents"]


def _fixture(store):
    org = H.make_org(store)
    store.add_member(H.ADMIN, org["id"], H.STAFF.name)
    budget = H.make_budget(store, org)
    store.record_obligation(H.MEMBER, budget["id"], "obligated",
                            H.OBLIGATED_CENTS)
    store.record_obligation(H.MEMBER, budget["id"], "spent", H.SPENT_CENTS)
    return org, budget


class TestNegativeControlDerivedAvailability(unittest.TestCase):
    def test_canonical_expectation(self):
        """Canonical: 1,000,000 − 300,000 − 200,000 = 500,000."""
        store = H.fresh_store()
        org, budget = _fixture(store)
        view = store.get_budget(H.MEMBER, budget["id"])
        self.assertEqual(view["available_cents"], H.AVAILABLE_CENTS)

    def test_implementation_matches_canonical_in_summary(self):
        """Implementation: the org summary's availability total is
        the same derived figure, not a second stored number."""
        store = H.fresh_store()
        org, budget = _fixture(store)
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["budget_available_cents"], H.AVAILABLE_CENTS)

    def test_mutant_would_not_derive(self):
        """Mutant: with the derivation stubbed, availability reads
        as the full budget — so the canonical expectation, applied
        to the mutant's output, fails (asserted literally)."""
        store = MutantMdmStore()
        org, budget = _fixture(store)
        view = store.get_budget(H.MEMBER, budget["id"])
        self.assertEqual(view["available_cents"], H.BUDGET_CENTS)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["available_cents"], H.AVAILABLE_CENTS)


if __name__ == "__main__":
    unittest.main()
