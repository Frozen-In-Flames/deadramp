"""Core function 11: search & summary reporting (counts/sums only)."""

import unittest

import mdm_helpers as H


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        H.make_inventory(self.store, self.org)
        self.contract = H.make_contract(self.store, self.org)
        H.make_bill(self.store, self.org, self.contract)

    def test_search_finds_by_ref_label_period(self):
        hits = self.store.search(H.MEMBER, "svc-100")
        self.assertEqual(len(hits["inventory"]), 1)
        hits = self.store.search(H.MEMBER, "master telecom")
        self.assertEqual(len(hits["contracts"]), 1)
        hits = self.store.search(H.MEMBER, "2026-06")
        self.assertEqual(len(hits["bills"]), 1)
        hits = self.store.search(H.MEMBER, "agency-1")
        self.assertEqual(len(hits["organizations"]), 1)

    def test_outsider_searches_see_nothing(self):
        hits = self.store.search(H.OUTSIDER, "svc")
        self.assertEqual(hits["inventory"], [])
        self.assertEqual(hits["organizations"], [])

    def test_empty_query_lists_accessible_orgs(self):
        hits = self.store.search(H.MEMBER, "")
        self.assertEqual(len(hits["organizations"]), 1)
        self.assertEqual(hits["inventory"], [])


class TestSummary(unittest.TestCase):
    def test_summary_counts_and_sums(self):
        store, org = H.make_store()
        H.make_inventory(store, org)
        H.make_inventory(store, org, ref="SVC-200", service_kind="mobility",
                         label="Field lines", plan_ref="PLAN-MOB-1",
                         monthly_recurring_cents=25_000)
        contract = H.make_contract(store, org)
        bill = H.make_bill(store, org, contract, stated_cents=80_000)
        store.create_dispute(H.MEMBER, bill["id"], 5_000, "Duplicate charge")
        budget = H.make_funded_budget(store, org)
        store.create_chargeback(H.MEMBER, budget["id"], "UNIT-A", 7_500)
        store.create_alert(H.MEMBER, org["id"], "general", "Review June spend")
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["inventory_by_kind"],
                         {"wireline": 1, "mobility": 1, "other": 0})
        self.assertEqual(summary["inventory_by_state"]["active"], 2)
        self.assertEqual(summary["bills"], 1)
        self.assertEqual(summary["bills_stated_cents"], 80_000)
        self.assertEqual(summary["disputes_by_status"]["open"], 1)
        self.assertEqual(summary["open_disputed_cents"], 5_000)
        self.assertEqual(summary["budget_available_cents"], H.AVAILABLE_CENTS)
        self.assertEqual(summary["chargebacks_cents"], 7_500)
        self.assertEqual(summary["alerts_unacknowledged"], 1)


if __name__ == "__main__":
    unittest.main()
