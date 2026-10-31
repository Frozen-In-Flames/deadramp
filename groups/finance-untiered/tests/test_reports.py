"""Program reporting tests.

Traces to: UNION-SPEC Core function 7 (Reporting — a per-period
program summary computed on read from records only: participant count,
earned / accessed / disbursed / pending wage totals, booking counts and
totals by kind, wellness enrollment count); Implementation contract
for ``finance/store.py`` ``program_summary``.

The coherent scenario used across this module (period 2026-01): two
employees and one traveler; accruals of 100000 and 50000 in the period;
one approved + disbursed access request (20000), one pending (10000),
one denied (5000); an air booking (30000, recorded) and a hotel
booking (25000, confirmed) in the period, plus a cancelled air booking
(12000); and two wellness enrollments. Therefore the January summary
is: participants 3, earned 150000, accessed 20000, disbursed 20000,
pending 10000, air {count 1, total 30000}, hotel {count 1, total
25000}, wellness_enrollments 2. February decoy records (an extra
accrual pair, an approved February request, a February hotel booking)
must not move the January numbers.
"""

import unittest

from finance_helpers import (
    ADMIN,
    MEMBER,
    PERIOD,
    PERIOD_OTHER,
    approved_request,
    disbursed_request,
    make_accrual,
    make_booking,
    make_employee,
    make_request,
    make_store,
    make_traveler,
)
from finance.errors import ValidationError

SUMMARY_KEYS = {
    "program_id", "period", "participants", "earned_cents",
    "accessed_cents", "disbursed_cents", "pending_cents", "bookings",
    "wellness_enrollments",
}
BOOKING_SUMMARY_KEYS = {"count", "total_cents"}


class ReportBase(unittest.TestCase):
    """The canonical reports scenario, built in setUp."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.emp1 = make_employee(self.store, self.program_id, ref="emp-1")
        self.emp2 = make_employee(self.store, self.program_id, ref="emp-2")
        self.traveler = make_traveler(self.store, self.program_id,
                                      ref="trav-1")

        # January accruals: 100000 + 50000 = 150000 earned.
        make_accrual(self.store, self.program_id, self.emp1["id"], PERIOD,
                     100000)
        make_accrual(self.store, self.program_id, self.emp2["id"], PERIOD,
                     50000)
        # February decoy accruals (excluded from the January summary).
        make_accrual(self.store, self.program_id, self.emp1["id"],
                     PERIOD_OTHER, 99999)
        make_accrual(self.store, self.program_id, self.emp2["id"],
                     PERIOD_OTHER, 20000)

        # January requests: disbursed 20000, pending 10000, denied 5000.
        disbursed_request(
            self.store, self.program_id, self.emp1["id"], period=PERIOD,
            amount_cents=20000, request_date="2026-01-10",
            disbursement_date="2026-01-20",
        )
        make_request(self.store, self.program_id, self.emp2["id"],
                     period=PERIOD, amount_cents=10000)
        denied = make_request(self.store, self.program_id, self.emp1["id"],
                              period=PERIOD, amount_cents=5000)
        self.store.decide_access(self.program_id, denied["id"], False, ADMIN)
        # February decoy request: approved 7777 against the Feb accrual.
        approved_request(self.store, self.program_id, self.emp2["id"],
                         period=PERIOD_OTHER, amount_cents=7777,
                         date="2026-02-10")

        # January bookings: air 30000 recorded, hotel 25000 confirmed,
        # air 12000 cancelled (excluded). February decoy: hotel 8888.
        make_booking(self.store, self.program_id, self.traveler["id"],
                     kind="air", start_date="2026-01-10",
                     end_date="2026-01-12", amount_cents=30000)
        hotel = make_booking(self.store, self.program_id,
                             self.traveler["id"], kind="hotel",
                             start_date="2026-01-15",
                             end_date="2026-01-17", amount_cents=25000)
        self.store.confirm_booking(self.program_id, hotel["id"], MEMBER)
        cancelled = make_booking(self.store, self.program_id,
                                 self.traveler["id"], kind="air",
                                 start_date="2026-01-05",
                                 end_date="2026-01-06", amount_cents=12000)
        self.store.cancel_booking(self.program_id, cancelled["id"], MEMBER)
        make_booking(self.store, self.program_id, self.traveler["id"],
                     kind="hotel", start_date="2026-02-05",
                     end_date="2026-02-07", amount_cents=8888)

        # Wellness: one offering, two enrollments.
        offering = self.store.create_wellness_offering(
            self.program_id, "Budgeting Basics", "budgeting", MEMBER
        )
        self.store.enroll_participant(
            self.program_id, offering["id"], self.emp1["id"], MEMBER
        )
        self.store.enroll_participant(
            self.program_id, offering["id"], self.traveler["id"], MEMBER
        )


class TestProgramSummary(ReportBase):
    """Core 7: Reporting — the per-period program summary."""

    def test_summary_returns_the_contract_dict(self):
        """Core 7: Reporting. Contract: program_summary returns
        {program_id, period, participants, earned_cents,
        accessed_cents, disbursed_cents, pending_cents, bookings,
        wellness_enrollments}; bookings is {"air": {count,
        total_cents}, "hotel": {...}} with both kinds always present."""
        summary = self.store.program_summary(self.program_id, PERIOD, MEMBER)
        self.assertEqual(set(summary.keys()), SUMMARY_KEYS)
        self.assertEqual(summary["program_id"], self.program_id)
        self.assertEqual(summary["period"], PERIOD)
        self.assertEqual(set(summary["bookings"].keys()), {"air", "hotel"})
        for kind in ("air", "hotel"):
            self.assertEqual(
                set(summary["bookings"][kind].keys()), BOOKING_SUMMARY_KEYS
            )

    def test_summary_participant_and_wellness_counts(self):
        """Core 7: Reporting. participants is the count of
        participants in the program (2 employees + 1 traveler = 3);
        wellness_enrollments is the total enrollment count (2)."""
        summary = self.store.program_summary(self.program_id, PERIOD, MEMBER)
        self.assertEqual(summary["participants"], 3)
        self.assertEqual(summary["wellness_enrollments"], 2)

    def test_summary_wage_totals(self):
        """Core 7: Reporting. Scenario wage totals for 2026-01:
        earned 150000 (both January accruals), accessed 20000 (the
        disbursed request; approved-or-disbursed), disbursed 20000
        (the disbursement dated in the period), pending 10000 (the
        still-requested request). The denied 5000 counts nowhere."""
        summary = self.store.program_summary(self.program_id, PERIOD, MEMBER)
        self.assertEqual(summary["earned_cents"], 150000)
        self.assertEqual(summary["accessed_cents"], 20000)
        self.assertEqual(summary["disbursed_cents"], 20000)
        self.assertEqual(summary["pending_cents"], 10000)

    def test_summary_bookings_by_kind_with_cancelled_excluded(self):
        """Core 7: Reporting. Bookings are counted over non-cancelled
        bookings whose start_date falls in the period: air {count 1,
        total 30000} (the cancelled 12000 air booking excluded),
        hotel {count 1, total 25000}."""
        summary = self.store.program_summary(self.program_id, PERIOD, MEMBER)
        self.assertEqual(
            summary["bookings"]["air"], {"count": 1, "total_cents": 30000}
        )
        self.assertEqual(
            summary["bookings"]["hotel"], {"count": 1, "total_cents": 25000}
        )

    def test_summary_for_the_other_period_excludes_january_records(self):
        """Core 7: Reporting. The summary covers exactly the given
        period: February shows only the February records — earned
        99999 + 20000 = 119999, accessed 7777 (the approved February
        request), disbursed 0, pending 0, hotel {count 1, total 8888},
        air {count 0, total 0} — while the participant and enrollment
        counts are program-wide."""
        summary = self.store.program_summary(
            self.program_id, PERIOD_OTHER, MEMBER
        )
        self.assertEqual(summary["period"], PERIOD_OTHER)
        self.assertEqual(summary["participants"], 3)
        self.assertEqual(summary["earned_cents"], 119999)
        self.assertEqual(summary["accessed_cents"], 7777)
        self.assertEqual(summary["disbursed_cents"], 0)
        self.assertEqual(summary["pending_cents"], 0)
        self.assertEqual(
            summary["bookings"]["air"], {"count": 0, "total_cents": 0}
        )
        self.assertEqual(
            summary["bookings"]["hotel"], {"count": 1, "total_cents": 8888}
        )
        self.assertEqual(summary["wellness_enrollments"], 2)

    def test_summary_for_an_empty_period_is_zero(self):
        """Core 7: Reporting. A period with no records reports zero
        money and zero bookings, with both booking kinds present."""
        summary = self.store.program_summary(self.program_id, "2026-03",
                                             MEMBER)
        self.assertEqual(summary["earned_cents"], 0)
        self.assertEqual(summary["accessed_cents"], 0)
        self.assertEqual(summary["disbursed_cents"], 0)
        self.assertEqual(summary["pending_cents"], 0)
        self.assertEqual(
            summary["bookings"],
            {"air": {"count": 0, "total_cents": 0},
             "hotel": {"count": 0, "total_cents": 0}},
        )

    def test_summary_bad_period_is_a_validation_error(self):
        """Core 7: Reporting. Contract: 'period must be valid' — a
        malformed YYYY-MM raises ValidationError."""
        for bad in ("2026-13", "2026-00", "2026-1", "Jan 2026", ""):
            with self.subTest(period=bad):
                with self.assertRaises(ValidationError):
                    self.store.program_summary(self.program_id, bad, MEMBER)


if __name__ == "__main__":
    unittest.main()
