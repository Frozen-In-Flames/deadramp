"""Negative control: the suite must reject a mutant cap check.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant cap check (one that sums the committed and
requested amounts but never compares the total against the period's
earned amount, treating every request as within cap) whose behavior
the canonical expectation is shown to reject — a request that would
push a period's committed total even one cent over its earned amount
must raise ValidationError from the real store and store nothing, and
the mutant is demonstrated to wave it through — proving the suite
catches that defect class rather than merely passing.'

The traced claim: **the earned-cap invariant is the SI-10 / Core 3
integrity boundary of earned-wage access.** Pending plus approved plus
disbursed amounts for a period must never exceed that period's earned
amount (accruals are wages already earned — nothing here lends or
advances unearned money). The cap comparison lives in the module-level
helper ``_check_access_cap(earned_cents, committed_cents,
amount_cents)`` in ``finance/store.py``; the mutant below replaces that
comparison with one that sums the committed and requested amounts and
then returns True unconditionally.

Each test asserts three things, per the canonical pattern: (1) the
canonical expectation — the real implementation raises ValidationError
for the over-cap request, stores nothing, and consumes no id; (2) the
mutant would NOT raise — run through the same gate shape, it waves the
over-cap request through as "within cap"; and (3) a literal
assertRaises(AssertionError) demonstration that treating the mutant's
outcome as the expected outcome is a test failure.
"""

import unittest

from finance_helpers import MEMBER, PERIOD, make_accrual, make_employee, make_store
from finance.errors import ValidationError
from finance.store import _check_access_cap

EARNED = 10000


def mutant_check(earned_cents, committed_cents, amount_cents):
    """The defect under control: the total is summed, never compared."""
    total = committed_cents + amount_cents
    # The mutant computes the committed total — and then never compares
    # it against the period's earned amount, treating every request as
    # within cap regardless of the numbers.
    _ = (earned_cents, total)
    return True


def mutant_gate(earned_cents, committed_cents, amount_cents):
    """The cap gate as the mutant would run it.

    Mirrors the real ``_check_access_cap`` gate's shape — raise
    ValidationError when the check fails, otherwise proceed — but with
    the mutant check inside, so it returns "within cap" for an
    over-cap request instead of raising.
    """
    if not mutant_check(earned_cents, committed_cents, amount_cents):
        raise ValidationError("access request exceeds earned cap")
    return "within cap"


class TestNegativeControlMutantCapCheck(unittest.TestCase):
    """Core 3: Earned-wage access (SI-10) — negative control for the
    earned-cap invariant, traced claim: the earned-cap invariant is
    the SI-10/core-3 integrity boundary of earned-wage access."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.employee = make_employee(self.store, self.program_id)
        self.emp_id = self.employee["id"]
        self.accrual = make_accrual(
            self.store, self.program_id, self.emp_id, PERIOD, EARNED
        )

    def _assert_mutant_rejected(self, mutant_outcome):
        """The mutant's 'within cap' must fail the canonical expectation."""
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")

    def test_single_request_one_cent_over_earned(self):
        """Core 3: Earned-wage access (SI-10), traced claim: the
        earned-cap invariant is the SI-10/core-3 integrity boundary.
        Canonical case (a): a single request of earned + 1 cent
        (10001 against 10000 earned, nothing yet committed) — the real
        store raises ValidationError, stores nothing, and consumes no
        request id (the next good request is req-1). Mutant: the same
        numbers are waved through as within cap."""
        with self.assertRaises(ValidationError):
            _check_access_cap(EARNED, 0, EARNED + 1)
        with self.assertRaises(ValidationError):
            self.store.request_access(
                self.program_id, self.emp_id, PERIOD, EARNED + 1,
                "2026-01-10", MEMBER,
            )
        self.assertEqual(
            self.store.list_access_requests(self.program_id, MEMBER), []
        )

        mutant_outcome = mutant_gate(EARNED, 0, EARNED + 1)
        self.assertEqual(mutant_outcome, "within cap")  # mutant did not raise
        self._assert_mutant_rejected(mutant_outcome)

        good = self.store.request_access(
            self.program_id, self.emp_id, PERIOD, 5000, "2026-01-10", MEMBER,
        )
        self.assertEqual(good["id"], "req-1")

    def test_two_requests_each_within_earned_whose_sum_exceeds_it(self):
        """Core 3: Earned-wage access (SI-10), traced claim: the
        earned-cap invariant is the SI-10/core-3 integrity boundary.
        Canonical case (b): two requests of 6000 each — each is
        individually within the 10000 earned amount, but their sum
        (12000) exceeds it, so the *second* request is the case: the
        real store raises ValidationError, stores nothing for it, and
        consumes no request id (the next good request is req-2).
        Mutant: with the first request's 6000 committed, the second
        6000 is waved through as within cap."""
        first = self.store.request_access(
            self.program_id, self.emp_id, PERIOD, 6000, "2026-01-10", MEMBER,
        )
        self.assertEqual(first["id"], "req-1")

        with self.assertRaises(ValidationError):
            _check_access_cap(EARNED, 6000, 6000)
        with self.assertRaises(ValidationError):
            self.store.request_access(
                self.program_id, self.emp_id, PERIOD, 6000,
                "2026-01-11", MEMBER,
            )
        requests = self.store.list_access_requests(self.program_id, MEMBER)
        self.assertEqual([r["id"] for r in requests], ["req-1"])

        mutant_outcome = mutant_gate(EARNED, 6000, 6000)
        self.assertEqual(mutant_outcome, "within cap")
        self._assert_mutant_rejected(mutant_outcome)

        good = self.store.request_access(
            self.program_id, self.emp_id, PERIOD, 4000, "2026-01-12", MEMBER,
        )
        self.assertEqual(good["id"], "req-2")

    def test_request_exactly_at_cap_passes_both_real_store_and_mutant(self):
        """Core 3: Earned-wage access (SI-10), traced claim: the
        earned-cap invariant is the SI-10/core-3 integrity boundary.
        Canonical case (c), the control sanity check: a request exactly
        at the cap (amount == earned, committed 0) passes BOTH the
        real store (created as req-1 in status requested, with the
        real ``_check_access_cap`` not raising) and the mutant check —
        the mutant is a weakened gate, not a broken one, so agreement
        on valid input is expected."""
        _check_access_cap(EARNED, 0, EARNED)  # real helper must not raise
        request = self.store.request_access(
            self.program_id, self.emp_id, PERIOD, EARNED, "2026-01-10",
            MEMBER,
        )
        self.assertEqual(request["id"], "req-1")
        self.assertEqual(request["status"], "requested")
        self.assertEqual(request["amount_cents"], EARNED)
        self.assertTrue(mutant_check(EARNED, 0, EARNED))
        self.assertEqual(mutant_gate(EARNED, 0, EARNED), "within cap")


if __name__ == "__main__":
    unittest.main()
