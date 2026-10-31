"""Core function 4: bid records.

Bids are recorded only while the auction is open (derived at the
bid's moment), are immutable once recorded, and carry integer-cent
prices -- floats and booleans are rejected at the boundary
(SI-10; the house integer-cents doctrine).
"""

import unittest

from energy.errors import NotFoundError, PermissionDenied, ValidationError

from energy_helpers import (AFTER, BEFORE, IN_WINDOW, IN_WINDOW_LATE,
                            MEMBER, VIEWER, make_customer, make_open_auction,
                            make_providers, make_store, ADMIN)


class BidTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)
        self.pa, self.pb = make_providers(self.store)
        self.auction = make_open_auction(self.store, self.customer)

    def bid(self, provider, price, at=IN_WINDOW, actor=ADMIN):
        return self.store.record_bid(actor, self.auction["id"],
                                     provider["id"], price, at=at)

    def test_bid_recorded_with_sequence(self):
        first = self.bid(self.pa, 500)
        second = self.bid(self.pb, 450)
        self.assertEqual((first["id"], first["seq"]), ("bid-1", 1))
        self.assertEqual((second["id"], second["seq"]), ("bid-2", 2))
        self.assertEqual(first["price_cents_per_unit"], 500)
        self.assertEqual(first["created_utc"], IN_WINDOW)

    def test_bid_only_while_open(self):
        with self.assertRaises(ValidationError):
            self.bid(self.pa, 500, at=BEFORE)   # upcoming
        with self.assertRaises(ValidationError):
            self.bid(self.pa, 500, at=AFTER)    # closed by window
        self.store.close_auction(ADMIN, self.auction["id"],
                                 closed_at=IN_WINDOW)
        with self.assertRaises(ValidationError):
            self.bid(self.pa, 500, at=IN_WINDOW_LATE)  # closed early

    def test_non_integer_prices_rejected(self):
        for bad in (4.5, 500.0, True, False, "500", None, -10, 0):
            with self.assertRaises(ValidationError):
                self.bid(self.pa, bad)
        # A failed bid consumes no id.
        ok = self.bid(self.pa, 500)
        self.assertEqual(ok["id"], "bid-1")

    def test_unknown_parties(self):
        with self.assertRaises(NotFoundError):
            self.store.record_bid(ADMIN, "auc-99", self.pa["id"], 500,
                                  at=IN_WINDOW)
        with self.assertRaises(NotFoundError):
            self.bid({"id": "prov-99"}, 500)

    def test_bids_are_immutable(self):
        self.bid(self.pa, 500)
        self.assertFalse(hasattr(self.store, "update_bid"))
        self.assertFalse(hasattr(self.store, "delete_bid"))
        bids = self.store.list_bids(VIEWER, self.auction["id"])
        bids[0]["price_cents_per_unit"] = 1
        again = self.store.list_bids(VIEWER, self.auction["id"])
        self.assertEqual(again[0]["price_cents_per_unit"], 500)

    def test_list_bids_in_sequence_order(self):
        self.bid(self.pb, 700)
        self.bid(self.pa, 600)
        listed = self.store.list_bids(ADMIN, self.auction["id"])
        self.assertEqual([b["seq"] for b in listed], [1, 2])
        self.assertEqual(
            self.store.get_auction(ADMIN, self.auction["id"])["bid_count"], 2)

    def test_roles(self):
        with self.assertRaises(PermissionDenied):
            self.bid(self.pa, 500, actor=VIEWER)
        ok = self.bid(self.pa, 500, actor=MEMBER)
        self.assertEqual(ok["created_by"], "bob")


if __name__ == "__main__":
    unittest.main()
