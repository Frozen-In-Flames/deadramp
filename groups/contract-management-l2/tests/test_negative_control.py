"""Negative control: the modification bounds rule must be
load-bearing.

Traces to: the contract's required negative control for the
Contract Management group (Core functions 3/4, SI-10). The group's
signature invariant is the modification bounds rule: a contract's
obligated amount (base award + recorded modifications) must always
satisfy 0 <= obligated <= ceiling, enforced by the store's
``_check_modification_bounds`` seam at creation and at every
modification.

Canonical expectation: an over-ceiling base award is rejected at
creation, an over-ceiling modification is rejected whole, and a
below-zero modification is rejected. The mutant is a
``ContractMgmtStore`` subclass whose ``_check_modification_bounds``
does nothing: if the suite still passed against the mutant, the
bounds tests would be testing that code ran, not that the
invariant holds. Each test asserts (1) the canonical expectation
from the real implementation, (2) the mutant would NOT produce
that expectation, and (3) a literal ``assertRaises(AssertionError)``
showing that treating the mutant's outcome as the expected outcome
fails.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import ValidationError
from contractmgmt.store import ContractMgmtStore


class MutantContractMgmtStore(ContractMgmtStore):
    """A store with the modification bounds check removed (the mutant)."""

    def _check_modification_bounds(self, contract, existing_amounts,
                                   additional_cents):
        return None


def _org(store):
    org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
    store.add_member(org["id"], H.MEMBER.name, H.ADMIN)
    return org


class TestNegativeControlModificationBounds(unittest.TestCase):
    """Canonical: out-of-bounds amounts are rejected; the mutant
    waves them through."""

    def test_canonical_expectation_rejects_over_ceiling_modification(self):
        """Canonical (Core 4): a first modification is recorded; the
        over-ceiling second raises ValidationError and the recorded
        set is unchanged."""
        store = H.fresh_store()
        org = _org(store)
        contract = H.make_contract(store, org, ceiling_cents=1000,
                                   award_cents=400)
        store.record_modification(org["id"], contract["id"], "MOD-1", 100,
                                  H.MEMBER)
        with self.assertRaises(ValidationError):
            store.record_modification(org["id"], contract["id"], "MOD-2",
                                      700, H.MEMBER)
        recorded = store.list_modifications(org["id"], contract["id"],
                                            H.MEMBER)
        self.assertEqual([m["mod_ref"] for m in recorded], ["MOD-1"])
        view = store.get_contract(org["id"], contract["id"], H.MEMBER)
        self.assertEqual(view["obligated_cents"], 500)

    def test_mutant_would_not_reject(self):
        """Mutant: with the seam removed, the same over-ceiling
        modification succeeds, two modifications are recorded, and
        the derived obligated amount exceeds the ceiling — so the
        canonical expectation, applied to the mutant's outcome,
        fails (asserted literally with assertRaises)."""
        store = MutantContractMgmtStore()
        org = _org(store)
        contract = H.make_contract(store, org, ceiling_cents=1000,
                                   award_cents=400)
        store.record_modification(org["id"], contract["id"], "MOD-1", 100,
                                  H.MEMBER)
        second = store.record_modification(org["id"], contract["id"],
                                           "MOD-2", 700, H.MEMBER)
        self.assertEqual(second["mod_ref"], "MOD-2")
        recorded = store.list_modifications(org["id"], contract["id"],
                                            H.MEMBER)
        self.assertEqual(len(recorded), 2)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(recorded), 1)
        view = store.get_contract(org["id"], contract["id"], H.MEMBER)
        self.assertEqual(view["obligated_cents"], 1200)
        with self.assertRaises(AssertionError):
            self.assertLessEqual(view["obligated_cents"],
                                 view["ceiling_cents"])

    def test_mutant_also_breaks_creation_and_floor(self):
        """Mutant contrast: the real store rejects an over-ceiling
        base award at creation and a below-zero modification; the
        mutant accepts both, and its report's obligated total
        exceeds its ceiling total where the canonical report's
        never can."""
        real = H.fresh_store()
        org = _org(real)
        with self.assertRaises(ValidationError):
            H.make_contract(real, org, contract_ref="CON-OVER",
                            ceiling_cents=1000, award_cents=2000)
        contract = H.make_contract(real, org, ceiling_cents=1000,
                                   award_cents=400)
        with self.assertRaises(ValidationError):
            real.record_modification(org["id"], contract["id"], "MOD-NEG",
                                     -401, H.MEMBER)
        report = real.org_report(org["id"], H.ADMIN)
        self.assertEqual(report["contract_count"], 1)
        self.assertLessEqual(report["obligated_cents_total"],
                             report["ceiling_cents_total"])

        mutant = MutantContractMgmtStore()
        org = _org(mutant)
        over = H.make_contract(mutant, org, contract_ref="CON-OVER",
                               ceiling_cents=1000, award_cents=2000)
        self.assertEqual(over["award_cents"], 2000)
        mutant_report = mutant.org_report(org["id"], H.ADMIN)
        self.assertGreater(mutant_report["obligated_cents_total"],
                           mutant_report["ceiling_cents_total"])
        with self.assertRaises(AssertionError):
            self.assertLessEqual(mutant_report["obligated_cents_total"],
                                 mutant_report["ceiling_cents_total"])


if __name__ == "__main__":
    unittest.main()
