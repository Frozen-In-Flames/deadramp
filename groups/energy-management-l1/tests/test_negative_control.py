"""Mutation-verified negative control for the outcome derivation.

An oracle that passes with both min and max is testing that code
ran, not that a reverse auction's lowest bid wins. So the canonical
outcome expectation is asserted here against a MUTANT store whose
``_derive_winner`` seam selects the *highest*-priced bid (ties by
latest sequence) instead of the lowest, and the test asserts the
canonical check FAILS against the mutant. If the canonical outcome
tests ever stopped discriminating -- if they would pass against the
mutant -- this test fails.

The external drill (the same patch applied to the real
``src/energy/store.py``, suite re-run, file restored byte-identical)
is recorded in tests/README.md and scratch/mutation-run.txt.
"""

import unittest

import energy.store as store_module

from energy_helpers import (IN_WINDOW, make_customer, make_open_auction,
                            make_providers, make_store, ADMIN)


class HighestBidStore(store_module.EnergyStore):
    """Mutant: the winner seam selects the highest bid."""

    pass


def _mutant_winner(bids):
    if not bids:
        return None
    return max(bids, key=lambda b: (b["price_cents_per_unit"], b["seq"]))


def canonical_lowest_bid_wins(store, auction, providers, expected_winner_id):
    """The outcome suite's core expectation, stated once.

    Raises AssertionError when the store's outcome derivation does
    not select the lowest-priced bid.
    """
    pa, pb = providers
    store.record_bid(ADMIN, auction["id"], pa["id"], 500, at=IN_WINDOW)
    cheap = store.record_bid(ADMIN, auction["id"], pb["id"], 420, at=IN_WINDOW)
    store.record_bid(ADMIN, auction["id"], pa["id"], 460, at=IN_WINDOW)
    assert cheap["id"] == expected_winner_id, "fixture drift"
    outcome = store.auction_outcome(ADMIN, auction["id"], now=IN_WINDOW)
    assert outcome["winning_bid_id"] == expected_winner_id, (
        "winner is %s, expected the lowest bid %s"
        % (outcome["winning_bid_id"], expected_winner_id))
    assert outcome["lowest_price_cents_per_unit"] == 420, (
        "lowest price is %s, expected 420"
        % (outcome["lowest_price_cents_per_unit"],))
    assert outcome["winning_provider_id"] == pb["id"]


class NegativeControlTests(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_store(self):
        store, _audit = make_store()
        customer = make_customer(store)
        providers = make_providers(store)
        auction = make_open_auction(store, customer)
        canonical_lowest_bid_wins(store, auction, providers, "bid-2")

    def test_canonical_check_fails_on_the_mutant(self):
        audit_holder = {}

        def mutant_store():
            from energy.audit import AuditLog
            audit = AuditLog()
            audit_holder["audit"] = audit
            return HighestBidStore(audit=audit)

        store = mutant_store()
        customer = make_customer(store)
        providers = make_providers(store)
        auction = make_open_auction(store, customer)
        original = store_module._derive_winner
        store_module._derive_winner = _mutant_winner
        try:
            with self.assertRaises(AssertionError):
                canonical_lowest_bid_wins(store, auction, providers, "bid-2")
        finally:
            store_module._derive_winner = original

    def test_tie_break_discriminates_too(self):
        """The tie arm of the invariant also discriminates: under the
        mutant (latest sequence wins ties) the earliest tied bid is
        NOT selected."""
        store, _audit = make_store()
        customer = make_customer(store)
        pa, pb = make_providers(store)
        auction = make_open_auction(store, customer)
        early = store.record_bid(ADMIN, auction["id"], pa["id"], 420,
                                 at=IN_WINDOW)
        store.record_bid(ADMIN, auction["id"], pb["id"], 420, at=IN_WINDOW)
        original = store_module._derive_winner
        store_module._derive_winner = _mutant_winner
        try:
            outcome = store.auction_outcome(ADMIN, auction["id"],
                                            now=IN_WINDOW)
            self.assertNotEqual(outcome["winning_bid_id"], early["id"])
        finally:
            store_module._derive_winner = original


ORACLE_EXPECTED = (
    "External drill (patch _derive_winner in src/energy/store.py to "
    "select the highest-priced bid, re-run the suite, restore): "
    "exactly 4 test failures -- "
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_outcome.OutcomeTests.test_lowest_bid_wins, "
    "test_outcome.OutcomeTests.test_outcome_is_derived_not_stored, "
    "test_outcome.OutcomeTests.test_tie_breaks_by_earliest_sequence "
    "-- then the file restored byte-identical (SHA-256 verified) "
    "and the full suite green again. Recorded in tests/README.md "
    "and scratch/mutation-run.txt."
)

if __name__ == "__main__":
    unittest.main()
