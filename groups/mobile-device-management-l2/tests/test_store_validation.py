"""Cross-cutting: SI-10 atomicity, money boundary, no-score shapes."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestAtomicity(unittest.TestCase):
    def test_failed_operation_consumes_no_id(self):
        store, org = H.make_store()
        with self.assertRaises(ValidationError):
            store.create_order(H.MEMBER, org["id"], "suspend", "No target")
        order = store.create_order(H.MEMBER, org["id"], "new", "First")
        self.assertEqual(order["id"], "ord-1")
        with self.assertRaises(ValidationError):
            store.create_budget(H.MEMBER, org["id"], "2026-13", 100)
        budget = store.create_budget(H.MEMBER, org["id"], "2026-06", 100)
        self.assertEqual(budget["id"], "bud-1")

    def test_money_boundary_everywhere(self):
        store, org = H.make_store()
        contract = H.make_contract(store, org)
        for bad in (1.5, True, "100", None):
            with self.assertRaises(ValidationError):
                store.create_quote(H.MEMBER, org["id"], contract["id"], bad)
            with self.assertRaises(ValidationError):
                store.create_bill(H.MEMBER, org["id"], contract["id"],
                                  "2026-06", bad)


class TestNoComputedScores(unittest.TestCase):
    def test_no_score_field_on_any_view(self):
        """Nothing in the build scores, rates, ranks, or optimizes:
        no returned record carries such a field."""
        store, org = H.make_store()
        item = H.make_inventory(store, org)
        contract = H.make_contract(store, org)
        bill = H.make_bill(store, org, contract)
        budget = H.make_funded_budget(store, org)
        views = [
            org, item, contract, bill, budget,
            store.validate_bill(H.MEMBER, bill["id"]),
            store.create_dispute(H.MEMBER, bill["id"], 100, "Check"),
            store.organization_summary(H.MEMBER, org["id"]),
        ]
        for view in views:
            for key in view.keys():
                lowered = key.lower()
                for forbidden in ("score", "rating", "rank", "grade",
                                  "optimi", "forecast"):
                    self.assertNotIn(forbidden, lowered,
                                     "%s on %r" % (forbidden, view))


if __name__ == "__main__":
    unittest.main()
