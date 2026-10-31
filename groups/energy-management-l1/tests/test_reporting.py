"""Core function 10: search and summary reporting.

The summary is counts and recorded values computed on read. The
latest price per series is a recorded value selected by observed
moment. A recursive scan pins the no-scoring discipline: no key
anywhere in the summary, an outcome, or a stored record may name a
score, rating, rank, or index.
"""

import unittest

from energy.errors import ValidationError

from energy_helpers import (AFTER, BEFORE, IN_WINDOW, VIEWER, make_customer,
                            make_open_auction, make_providers, make_store,
                            ADMIN)

BANNED = ("score", "rating", "rank", "index")


def scan(obj, path="root"):
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if any(bad in lowered for bad in BANNED):
                hits.append("%s.%s" % (path, key))
            hits.extend(scan(value, "%s.%s" % (path, key)))
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            hits.extend(scan(value, "%s[%d]" % (path, i)))
    return hits


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)
        self.pa, self.pb = make_providers(self.store)
        self.auction = make_open_auction(self.store, self.customer)

    def populate(self):
        self.store.record_bid(ADMIN, self.auction["id"], self.pa["id"],
                              500, at=IN_WINDOW)
        self.store.record_bid(ADMIN, self.auction["id"], self.pb["id"],
                              420, at=IN_WINDOW)
        self.store.record_observation(ADMIN, "ERCOT-North", "electricity",
                                      380,
                                      observed_at="2024-06-02T00:00:00+00:00")
        self.store.record_observation(ADMIN, "ERCOT-North", "electricity",
                                      350,
                                      observed_at="2024-06-04T00:00:00+00:00")
        sub = self.store.create_subscription(ADMIN, self.customer["id"],
                                             "price_change",
                                             threshold_cents_per_unit=400)
        self.store.record_alert(ADMIN, self.customer["id"], "price_change",
                                "Price crossed threshold",
                                subscription_id=sub["id"])
        self.store.record_alert(ADMIN, self.customer["id"], "market_update",
                                "Weekly market update")
        self.store.create_engagement(ADMIN, self.customer["id"], "budgeting",
                                     "Budget review")
        eng = self.store.create_engagement(ADMIN, self.customer["id"],
                                           "risk_management", "Hedge review")
        self.store.close_engagement(ADMIN, eng["id"])

    def test_summary_counts(self):
        self.populate()
        summary = self.store.summary(ADMIN, now=IN_WINDOW)
        self.assertEqual(summary["customers"], 1)
        self.assertEqual(summary["providers"], 2)
        self.assertEqual(summary["auctions_by_status"],
                         {"upcoming": 0, "open": 1, "closed": 0})
        self.assertEqual(summary["bids"], 2)
        self.assertEqual(summary["observations"], 2)
        self.assertEqual(summary["subscriptions_active"], 1)
        self.assertEqual(summary["alerts_by_kind"],
                         {"price_change": 1, "contract_change": 0,
                          "market_update": 1})
        self.assertEqual(summary["engagements_by_kind"],
                         {"budgeting": 1, "market_intelligence": 0,
                          "risk_management": 1})
        self.assertEqual(summary["engagements_open"], 1)

    def test_summary_status_uses_read_clock(self):
        self.assertEqual(
            self.store.summary(ADMIN, now=BEFORE)["auctions_by_status"],
            {"upcoming": 1, "open": 0, "closed": 0})
        self.assertEqual(
            self.store.summary(ADMIN, now=AFTER)["auctions_by_status"],
            {"upcoming": 0, "open": 0, "closed": 1})

    def test_latest_price_is_latest_recorded_value(self):
        self.populate()
        latest = self.store.summary(ADMIN)["latest_prices"]
        entry = latest["ERCOT-North|electricity"]
        self.assertEqual(entry["price_cents_per_unit"], 350)
        self.assertEqual(entry["observed_at"], "2024-06-04T00:00:00+00:00")

    def test_search(self):
        self.populate()
        found = self.store.search(VIEWER, "budget")
        self.assertEqual(len(found["engagements"]), 1)
        found = self.store.search(VIEWER, "ercot")
        self.assertEqual(len(found["auctions"]), 1)
        found = self.store.search(VIEWER, "cust-0001")
        self.assertEqual(len(found["customers"]), 1)
        found = self.store.search(VIEWER, "supplyco")
        self.assertEqual(len(found["providers"]), 2)
        with self.assertRaises(ValidationError):
            self.store.search(VIEWER, "  ")

    def test_no_scores_anywhere(self):
        self.populate()
        self.assertEqual(scan(self.store.summary(ADMIN, now=IN_WINDOW)), [])
        self.assertEqual(
            scan(self.store.auction_outcome(ADMIN, self.auction["id"],
                                            now=IN_WINDOW)), [])
        self.assertEqual(scan(self.store._auctions), [])
        self.assertEqual(scan(self.store._bids), [])
        self.assertEqual(scan(self.store._customers), [])
        self.assertEqual(scan(self.store._engagements), [])


if __name__ == "__main__":
    unittest.main()
