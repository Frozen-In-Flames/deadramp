"""Core 3 (contract records) and Core 4 (modification records),
including the modification bounds seam — the group's signature
invariant — and the derived-at-read discipline.

Traces to: UNION-SPEC.md core functions 3-4, the signature
invariant (0 <= obligated <= ceiling), and SI-10.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, PermissionDenied, ValidationError

STORED_KEYS = {
    "id", "org_id", "contract_ref", "title", "counterparty_ref",
    "ceiling_cents", "award_cents", "period_start", "period_end",
    "status", "created_by", "created_utc",
}


class TestContracts(unittest.TestCase):
    """Core 3: contract records, lifecycle, derived views."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_stored_shape_pinned_and_no_derived_keys(self):
        """Core 3: the stored record carries exactly the contract's
        keys — no obligated_cents, no period_elapsed."""
        contract = H.make_contract(self.store, self.org)
        self.assertEqual(set(contract.keys()), STORED_KEYS)
        raw = self.store._contracts[contract["id"]]
        self.assertEqual(set(raw.keys()), STORED_KEYS)
        self.assertNotIn("obligated_cents", raw)
        self.assertNotIn("period_elapsed", raw)
        self.assertEqual(contract["status"], "active")

    def test_derived_obligated_and_period_elapsed(self):
        """Core 3: read views derive obligated_cents (base award +
        modifications) and period_elapsed (read clock past the
        period end); the stored record changes in neither case."""
        contract = H.make_contract(
            self.store, self.org,
            period_start="2026-01-01", period_end="2026-12-31")
        view = self.store.get_contract(self.org["id"], contract["id"],
                                       H.MEMBER, now="2026-06-01")
        self.assertEqual(view["obligated_cents"], H.AWARD)
        self.assertFalse(view["period_elapsed"])
        later = self.store.get_contract(self.org["id"], contract["id"],
                                        H.MEMBER, now="2027-06-01")
        self.assertTrue(later["period_elapsed"])
        self.store.record_modification(
            self.org["id"], contract["id"], "MOD-1", 250_000, H.MEMBER)
        view = self.store.get_contract(self.org["id"], contract["id"],
                                       H.MEMBER, now="2026-06-01")
        self.assertEqual(view["obligated_cents"], H.AWARD + 250_000)
        raw = self.store._contracts[contract["id"]]
        self.assertNotIn("obligated_cents", raw)

    def test_money_discipline(self):
        """Core 3 / SI-10: ceiling and award are integer cents —
        booleans, floats, strings, and negatives are rejected."""
        for bad in (True, 1.5, "1000", -1, None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                H.make_contract(self.store, self.org, ceiling_cents=bad)
            with self.assertRaises(ValidationError, msg=repr(bad)):
                H.make_contract(self.store, self.org, award_cents=bad)
        self.assertEqual(self.store.list_contracts(self.org["id"], H.MEMBER),
                         [])

    def test_base_award_above_ceiling_rejected_at_creation(self):
        """Signature invariant at creation: the bounds seam runs
        before the record exists; no id is consumed."""
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org,
                            ceiling_cents=100, award_cents=200)
        ok = H.make_contract(self.store, self.org)
        self.assertEqual(ok["id"], "con-1")

    def test_period_end_before_start_rejected(self):
        """Core 3 / SI-10: a period that ends before it starts is
        rejected; a malformed period is rejected."""
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org,
                            period_start="2026-12-31",
                            period_end="2026-01-01")
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org, period_end="not-a-date")

    def test_duplicate_contract_ref_rejected_within_org_only(self):
        """Core 3: contract refs are unique within an organization,
        reusable across organizations."""
        H.make_contract(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org, title="Clone")
        other = self.store.create_organization("ORG-2", "Second", H.ADMIN)
        self.store.add_member(other["id"], "bob", H.ADMIN)
        clone = H.make_contract(self.store, other)
        self.assertEqual(clone["contract_ref"], H.CONTRACT_REF)

    def test_close_contract_guarded(self):
        """Core 3: the lifecycle is active -> closed, guarded —
        closing twice is a validation error."""
        contract = H.make_contract(self.store, self.org)
        closed = self.store.close_contract(self.org["id"], contract["id"],
                                            H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_contract(self.org["id"], contract["id"], H.MEMBER)

    def test_cross_org_contract_id_is_not_found(self):
        """Core 3: a contract id from another organization reads as
        NotFound in this one."""
        contract = H.make_contract(self.store, self.org)
        other = self.store.create_organization("ORG-2", "Second", H.ADMIN)
        self.store.add_member(other["id"], "bob", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_contract(other["id"], contract["id"], H.MEMBER)

    def test_viewer_cannot_create_contract(self):
        """AC: contract_write is not held by viewer."""
        with self.assertRaises(PermissionDenied):
            H.make_contract(self.store, self.org, actor=H.VIEWER)


class TestModifications(unittest.TestCase):
    """Core 4: modification records and the bounds seam."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)

    def _mod(self, ref, amount, actor=H.MEMBER, **kw):
        return self.store.record_modification(
            self.org["id"], self.contract["id"], ref, amount, actor, **kw)

    def test_modification_shape_pinned(self):
        """Core 4: the modification record carries exactly the
        contract's keys."""
        mod = self._mod("MOD-1", 100_000, label="Funding increase")
        self.assertEqual(
            set(mod.keys()),
            {"id", "org_id", "contract_id", "mod_ref", "amount_cents",
             "label", "created_by", "created_utc"},
        )
        self.assertEqual(mod["id"], "mod-1")

    def test_modification_up_to_ceiling_exactly(self):
        """Signature invariant: obligated may reach the ceiling
        exactly (the bound is inclusive)."""
        self._mod("MOD-1", H.CEILING - H.AWARD)
        view = self.store.get_contract(self.org["id"], self.contract["id"],
                                       H.MEMBER)
        self.assertEqual(view["obligated_cents"], H.CEILING)

    def test_over_ceiling_modification_rejected_whole(self):
        """Signature invariant: one cent past the ceiling is
        rejected whole — no record, no id consumed, store
        unchanged."""
        with self.assertRaises(ValidationError):
            self._mod("MOD-OVER", H.CEILING - H.AWARD + 1)
        self.assertEqual(
            self.store.list_modifications(
                self.org["id"], self.contract["id"], H.MEMBER), [])
        mod = self._mod("MOD-1", 1)
        self.assertEqual(mod["id"], "mod-1")

    def test_cumulative_mods_checked_together(self):
        """Signature invariant: the seam sums the base award and
        ALL existing modifications, not just the new one."""
        self._mod("MOD-1", 300_000)
        self._mod("MOD-2", 300_000)
        with self.assertRaises(ValidationError):
            self._mod("MOD-3", 1)

    def test_below_zero_modification_rejected(self):
        """Signature invariant: de-obligation may reach zero exactly
        but never below it."""
        self._mod("MOD-DOWN", -H.AWARD)
        view = self.store.get_contract(self.org["id"], self.contract["id"],
                                       H.MEMBER)
        self.assertEqual(view["obligated_cents"], 0)
        with self.assertRaises(ValidationError):
            self._mod("MOD-DOWN-2", -1)

    def test_modification_amount_must_be_int(self):
        """Core 4 / SI-10: modification amounts are integer cents —
        booleans, floats, and strings are rejected (zero is a valid
        administrative modification)."""
        for bad in (True, 2.5, "500"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self._mod("MOD-BAD", bad)
        zero = self._mod("MOD-ZERO", 0)
        self.assertEqual(zero["amount_cents"], 0)

    def test_modification_against_closed_contract_rejected(self):
        """Core 4: modifications are recorded against active
        contracts only."""
        self.store.close_contract(self.org["id"], self.contract["id"],
                                   H.MEMBER)
        with self.assertRaises(ValidationError):
            self._mod("MOD-LATE", 1)

    def test_duplicate_mod_ref_rejected(self):
        """Core 4: mod refs are unique within the contract."""
        self._mod("MOD-1", 1)
        with self.assertRaises(ValidationError):
            self._mod("MOD-1", 2)


if __name__ == "__main__":
    unittest.main()
