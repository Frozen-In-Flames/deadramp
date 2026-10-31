"""Core function 5: the outcome derivation -- THE SIGNATURE
INVARIANT of this group.

The outcome of a reverse auction is derived at read from the bid
records alone: the winning bid is the LOWEST-priced bid, ties
broken by earliest sequence. Nothing about the outcome is stored.
Selecting the lowest recorded bid is a minimum over recorded
values, not a score or rating of any provider; the outcome view
returns the single winning selection plus counts, and deliberately
no provider ranking.
"""

import unittest

from energy.errors import NotFoundError

from energy_helpers import (AFTER, BEFORE, IN_WINDOW, IN_WINDOW_LATE,
                            VIEWER, make_customer, make_open_auction,
                            make_providers, make_store, ADMIN)

OUTCOME_KEYS = {"auction_id", "status", "is_final", "bid_count",
                "provider_count", "lowest_price_cents_per_unit",
                "winning_bid_id", "winning_provider_id"}


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)
        self.pa, self.pb = make_providers(self.store)
        self.auction = make_open_auction(self.store, self.customer)

    def bid(self, provider, price, at=IN_WINDOW):
        return self.store.record_bid(ADMIN, self.auction["id"],
                                     provider["id"], price, at=at)

    def outcome(self, now=IN_WINDOW):
        return self.store.auction_outcome(ADMIN, self.auction["id"], now=now)

    def test_empty_auction_has_no_winner(self):
        result = self.outcome()
        self.assertEqual(set(result.keys()), OUTCOME_KEYS)
        self.assertEqual(result["bid_count"], 0)
        self.assertEqual(result["provider_count"], 0)
        self.assertIsNone(result["lowest_price_cents_per_unit"])
        self.assertIsNone(result["winning_bid_id"])
        self.assertIsNone(result["winning_provider_id"])
        self.assertFalse(result["is_final"])

    def test_lowest_bid_wins(self):
        self.bid(self.pa, 500)
        cheap = self.bid(self.pb, 420)
        self.bid(self.pa, 460)
        result = self.outcome()
        self.assertEqual(result["winning_bid_id"], cheap["id"])
        self.assertEqual(result["winning_provider_id"], self.pb["id"])
        self.assertEqual(result["lowest_price_cents_per_unit"], 420)
        self.assertEqual(result["bid_count"], 3)
        self.assertEqual(result["provider_count"], 2)

    def test_tie_breaks_by_earliest_sequence(self):
        early = self.bid(self.pa, 420)
        self.bid(self.pb, 420, at=IN_WINDOW_LATE)
        self.assertEqual(self.outcome()["winning_bid_id"], early["id"])

    def test_outcome_is_derived_not_stored(self):
        self.bid(self.pa, 500)
        first = self.outcome()
        self.bid(self.pb, 300, at=IN_WINDOW_LATE)
        second = self.outcome()
        self.assertEqual(first["lowest_price_cents_per_unit"], 500)
        self.assertEqual(second["lowest_price_cents_per_unit"], 300)
        raw = self.store._auctions[self.auction["id"]]
        for key in ("winning_bid_id", "winning_provider_id",
                    "lowest_price_cents_per_unit", "status"):
            self.assertNotIn(key, raw)

    def test_finality_follows_derived_status(self):
        self.bid(self.pa, 500)
        self.assertFalse(self.outcome(now=BEFORE)["is_final"])
        self.assertEqual(self.outcome(now=BEFORE)["status"], "upcoming")
        final = self.outcome(now=AFTER)
        self.assertTrue(final["is_final"])
        self.assertEqual(final["status"], "closed")
        self.store.close_auction(ADMIN, self.auction["id"],
                                 closed_at=IN_WINDOW_LATE)
        closed = self.outcome(now=IN_WINDOW_LATE)
        self.assertTrue(closed["is_final"])

    def test_no_ranking_is_produced(self):
        self.bid(self.pa, 500)
        self.bid(self.pb, 420)
        result = self.outcome()
        for key in result:
            self.assertNotIn("rank", key.lower())
            self.assertNotIn("score", key.lower())
            self.assertNotIn("leaderboard", key.lower())

    def test_unknown_auction(self):
        with self.assertRaises(NotFoundError):
            self.store.auction_outcome(VIEWER, "auc-99")


if __name__ == "__main__":
    unittest.main()
