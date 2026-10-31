"""Core function 3: auction records with DERIVED status.

The stored auction record never carries a status key and never an
outcome key; status is computed at read from the recorded window
(and any recorded early close) against the read clock (CM-6,
AU-2/AU-3 Low side).
"""

import unittest

from energy.errors import NotFoundError, PermissionDenied, ValidationError

from energy_helpers import (AFTER, BEFORE, CLOSES, IN_WINDOW, MEMBER,
                            OPENS, VIEWER, make_customer, make_open_auction,
                            make_providers, make_store, ADMIN)


class AuctionTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)

    def open_auction(self):
        return make_open_auction(self.store, self.customer)

    def test_create_shape(self):
        auction = self.open_auction()
        self.assertEqual(auction["id"], "auc-1")
        self.assertEqual(auction["customer_id"], self.customer["id"])
        self.assertEqual(auction["commodity"], "electricity")
        self.assertEqual(auction["region"], "ERCOT-North")
        self.assertEqual(auction["unit_label"], "kWh")
        self.assertEqual(auction["quantity_units"], 100000)
        self.assertIsNone(auction["closed_at"])
        self.assertEqual(auction["status"], "closed")  # real clock is past window
        self.assertEqual(auction["bid_count"], 0)

    def test_stored_record_has_no_status_or_winner(self):
        auction = self.open_auction()
        raw = self.store._auctions[auction["id"]]
        self.assertNotIn("status", raw)
        self.assertNotIn("winning_bid_id", raw)
        self.assertNotIn("winning_provider_id", raw)
        self.assertNotIn("lowest_price_cents_per_unit", raw)

    def test_status_derived_from_window(self):
        auction = self.open_auction()
        view = lambda now: self.store.get_auction(ADMIN, auction["id"], now=now)
        self.assertEqual(view(BEFORE)["status"], "upcoming")
        self.assertEqual(view(IN_WINDOW)["status"], "open")
        self.assertEqual(view(AFTER)["status"], "closed")

    def test_close_records_event_and_derives_closed(self):
        auction = self.open_auction()
        closed = self.store.close_auction(ADMIN, auction["id"],
                                          closed_at=IN_WINDOW)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["closed_at"], IN_WINDOW)
        # Even before the window opens, the recorded close wins.
        view = self.store.get_auction(ADMIN, auction["id"], now=BEFORE)
        self.assertEqual(view["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_auction(ADMIN, auction["id"])

    def test_create_validation(self):
        cid = self.customer["id"]
        with self.assertRaises(NotFoundError):
            self.store.create_auction(ADMIN, "cust-99", "electricity", "R",
                                      "kWh", 10, OPENS, CLOSES)
        for qty in (0, -5, 2.5, True, "10"):
            with self.assertRaises(ValidationError):
                self.store.create_auction(ADMIN, cid, "electricity", "R",
                                          "kWh", qty, OPENS, CLOSES)
        with self.assertRaises(ValidationError):
            self.store.create_auction(ADMIN, cid, "electricity", "R", "kWh",
                                      10, CLOSES, OPENS)  # closes before opens
        with self.assertRaises(ValidationError):
            self.store.create_auction(ADMIN, cid, "", "R", "kWh", 10,
                                      OPENS, CLOSES)

    def test_roles(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_auction(VIEWER, self.customer["id"],
                                      "electricity", "R", "kWh", 10,
                                      OPENS, CLOSES)
        auction = make_open_auction(self.store, self.customer, actor=MEMBER)
        self.assertEqual(auction["id"], "auc-1")

    def test_list_filters(self):
        auction = self.open_auction()
        self.store.create_auction(ADMIN, self.customer["id"], "natural gas",
                                  "ERCOT-South", "MMBtu", 500, OPENS, CLOSES)
        self.assertEqual(len(self.store.list_auctions(ADMIN)), 2)
        self.assertEqual(
            len(self.store.list_auctions(
                ADMIN, customer_id=self.customer["id"])), 2)
        open_now = self.store.list_auctions(ADMIN, status="open", now=IN_WINDOW)
        self.assertEqual(len(open_now), 2)
        self.assertEqual(
            self.store.list_auctions(ADMIN, status="closed", now=IN_WINDOW), [])
        with self.assertRaises(ValidationError):
            self.store.list_auctions(ADMIN, status="paused")
        make_providers(self.store)  # providers do not affect auction lists
        self.assertEqual(
            self.store.get_auction(ADMIN, auction["id"])["bid_count"], 0)


if __name__ == "__main__":
    unittest.main()
