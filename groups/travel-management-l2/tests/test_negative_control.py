"""Negative control for the signature invariant (the voucher cap).

The canonical tests assert that the real store refuses a voucher
that would push cumulative vouchers past an expense report's total.
The mutant subclass below removes exactly one seam --
``TravelStore._check_voucher_cap`` -- and the SAME over-cap voucher
succeeds, proving the check (not some incidental validation) is what
enforces the cap. The external drill record (patching the real
store.py, running the full suite, restoring it SHA-256-verified) is
in tests/README.md.
"""

import unittest

from travel.errors import ValidationError
from travel.store import TravelStore

from travel_helpers import (ADMIN, DECIDER, MEMBER,
                            make_approved_authorization, make_approved_report,
                            make_store, make_traveler)


class _NoCapStore(TravelStore):
    """Mutant: the voucher cap check is a no-op."""

    def _check_voucher_cap(self, report, amount_cents):
        return None


def _approved_report(store):
    """Build an approved 100,000-cent report on a bare store."""
    org = store.create_organization(ADMIN, "ORG-NC", "Control Org")
    store.add_member(ADMIN, org["id"], MEMBER.name)
    store.add_member(ADMIN, org["id"], DECIDER.name)
    traveler = store.create_traveler(MEMBER, org["id"], "TRV-NC",
                                     "Control Traveler")
    auth = store.create_authorization(
        MEMBER, org["id"], traveler["id"], "Denver, CO", "Site review",
        "2026-06-10", "2026-06-12", 500_000)
    store.submit_authorization(MEMBER, auth["id"])
    store.decide_authorization(DECIDER, auth["id"], True)
    report = store.create_expense_report(MEMBER, auth["id"], "Expenses")
    store.add_expense_item(MEMBER, report["id"], "lodging", 100_000,
                           "2026-06-10")
    store.submit_expense_report(MEMBER, report["id"])
    store.decide_expense_report(DECIDER, report["id"], True)
    return report


class TestVoucherCapNegativeControl(unittest.TestCase):
    def test_canonical_store_rejects_over_cap_voucher(self):
        store, org = make_store()
        traveler = make_traveler(store, org)
        auth = make_approved_authorization(store, org, traveler)
        report = make_approved_report(store, auth)  # total 150,000
        with self.assertRaises(ValidationError):
            store.record_voucher(MEMBER, report["id"], 150_001)

    def test_mutant_store_allows_the_same_voucher(self):
        store = _NoCapStore()
        report = _approved_report(store)
        voucher = store.record_voucher(MEMBER, report["id"], 100_001)
        self.assertEqual(voucher["amount_cents"], 100_001)
        view = store.get_expense_report(MEMBER, report["id"])
        self.assertEqual(view["reimbursed_cents"], 100_001)
        self.assertEqual(view["remaining_cents"], -1)


if __name__ == "__main__":
    unittest.main()
