"""Core function 8: budgets, obligations & derived availability."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError

RAW_BUDGET_KEYS = {
    "id", "org_id", "period", "budget_cents", "projection_cents",
    "note", "created_by", "created_utc",
}


class TestBudgets(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_availability_is_derived_at_read(self):
        budget = H.make_funded_budget(self.store, self.org)
        self.assertEqual(budget["obligated_cents"], H.OBLIGATED_CENTS)
        self.assertEqual(budget["spent_cents"], H.SPENT_CENTS)
        self.assertEqual(budget["available_cents"], H.AVAILABLE_CENTS)

    def test_stored_record_carries_no_derived_keys(self):
        """Twice-pinned derivation: the raw stored budget has no
        obligated / spent / available key at all."""
        budget = H.make_funded_budget(self.store, self.org)
        raw = self.store._budgets[budget["id"]]
        self.assertEqual(set(raw.keys()), RAW_BUDGET_KEYS)
        for derived in ("obligated_cents", "spent_cents", "available_cents"):
            self.assertNotIn(derived, raw)

    def test_one_budget_per_period(self):
        H.make_budget(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_budget(self.store, self.org)
        other = H.make_budget(self.store, self.org, period="2026-07")
        self.assertEqual(other["period"], "2026-07")

    def test_projection_is_recorded_verbatim_never_computed(self):
        budget = H.make_budget(self.store, self.org, projection_cents=975_000)
        self.assertEqual(budget["projection_cents"], 975_000)
        plain = H.make_budget(self.store, self.org, period="2026-07")
        self.assertIsNone(plain["projection_cents"])
        with self.assertRaises(ValidationError):
            H.make_budget(self.store, self.org, period="2026-08",
                          projection_cents=1.5)

    def test_obligation_validation(self):
        budget = H.make_budget(self.store, self.org)
        for kind, amount in (("planned", 100), ("obligated", 0),
                             ("spent", -5), ("spent", 10.5), ("spent", True)):
            with self.assertRaises(ValidationError):
                self.store.record_obligation(H.MEMBER, budget["id"], kind, amount)

    def test_money_boundary_on_budget(self):
        for bad in (1_000_000.0, True, "1000000", -1):
            with self.assertRaises(ValidationError):
                H.make_budget(self.store, self.org, budget_cents=bad)


if __name__ == "__main__":
    unittest.main()
