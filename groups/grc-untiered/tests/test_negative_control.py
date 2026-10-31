"""Negative control: the suite must reject a derivation that never fires.

Traces to: Core function 5 (finding / remediation records) — the
traced claim is that the date-based status is DERIVED at read time:
an open finding past its due date derives "overdue", and the same
finding before its due date does not. The mutant below replaces the
overdue branch with one that never fires — it returns the lifecycle
status unconditionally, exactly the defect of storing a static status
and never deriving.

Each canonical case asserts three things: (1) the real
``derive_finding_status`` separates the pair (before due -> "open",
after due -> "overdue"); (2) the mutant collapses the pair to "open";
and (3) a literal ``assertRaises(AssertionError)`` demonstration that
treating the mutant's output as the expected output fails. An
end-to-end arm repeats the separation through the store: a past-due
open finding read with ``as_of`` carries derived_status "overdue",
which the mutant's prediction cannot satisfy. The mutation drill
against the live ``src/grc/store.py`` derivation is recorded in
``tests/README.md``.
"""

import unittest

from grc_helpers import MEMBER, make_finding, make_store
from grc.store import derive_finding_status

FINDING = {"status": "open", "due_date": "2026-06-30"}


def mutant_derive_finding_status(finding, as_of=None):
    """The defect under control: the overdue branch never fires.

    Mirrors the real function's contract — a status string derived
    from a finding record and an as-of date — but returns the stored
    lifecycle status unconditionally, so no finding is ever overdue.
    """
    return finding["status"]


class TestNegativeControlMutantDerivation(unittest.TestCase):
    """Core 5: negative control for a never-firing overdue derivation,
    traced claim: overdue must be derived from due date + state."""

    def test_real_derivation_separates_the_canonical_pair(self):
        """Core 5 derivation, traced claim: overdue is derived at read
        time. Canonical: the open finding due 2026-06-30 derives
        "open" at as_of 2026-06-30 and "overdue" at as_of 2026-07-01
        — same record, different as-of, different derived status."""
        before = derive_finding_status(FINDING, "2026-06-30")
        after = derive_finding_status(FINDING, "2026-07-01")
        self.assertEqual(before, "open")
        self.assertEqual(after, "overdue")
        self.assertNotEqual(before, after)

    def test_mutant_collapses_the_canonical_pair(self):
        """Core 5 derivation, traced claim: overdue is derived at read
        time. The never-firing mutant returns "open" for both as-of
        dates: the separation the claim requires is exactly what the
        mutant destroys."""
        self.assertEqual(mutant_derive_finding_status(FINDING, "2026-06-30"), "open")
        self.assertEqual(mutant_derive_finding_status(FINDING, "2026-07-01"), "open")
        self.assertEqual(
            mutant_derive_finding_status(FINDING, "2026-06-30"),
            mutant_derive_finding_status(FINDING, "2026-07-01"),
        )

    def test_mutant_output_fails_the_canonical_expectation(self):
        """Core 5 derivation, traced claim: overdue is derived at read
        time. Treating the mutant's output for the past-due case as
        the expected "overdue" is a test failure — shown via a literal
        assertRaises(AssertionError)."""
        mutant = mutant_derive_finding_status(FINDING, "2026-07-01")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, "overdue")
        with self.assertRaises(AssertionError):
            self.assertNotEqual(
                mutant_derive_finding_status(FINDING, "2026-06-30"),
                mutant_derive_finding_status(FINDING, "2026-07-01"),
            )

    def test_mutant_also_collapses_in_progress(self):
        """Core 5 derivation, traced claim: overdue is derived at read
        time. For an in_progress finding the mutant likewise collapses
        before/after the due date to one value, while the real
        derivation separates them ("in_progress" vs "overdue")."""
        finding = {"status": "in_progress", "due_date": "2026-06-30"}
        self.assertEqual(
            mutant_derive_finding_status(finding, "2026-06-29"),
            mutant_derive_finding_status(finding, "2026-07-01"),
        )
        self.assertEqual(derive_finding_status(finding, "2026-06-29"), "in_progress")
        self.assertEqual(derive_finding_status(finding, "2026-07-01"), "overdue")
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant_derive_finding_status(finding, "2026-07-01"), "overdue"
            )


class TestNegativeControlEndToEnd(unittest.TestCase):
    """Core 5: the derivation holds end-to-end through the store."""

    def test_past_due_open_finding_reads_overdue_in_store(self):
        """Core 5 derivation, traced claim: overdue is derived at
        read time. End-to-end arm: an open finding due 2026-06-30
        created in the store reads derived_status "overdue" at
        as_of 2026-12-31 and "open" at as_of 2026-01-01 — so a store
        whose derivation never fired could not satisfy this test, and
        the mutant's prediction ("open") fails as an expectation for
        the past-due read."""
        store, _, _ = make_store()
        finding = make_finding(store, due_date="2026-06-30")
        late = store.get_finding(finding["id"], actor=MEMBER, as_of="2026-12-31")
        early = store.get_finding(finding["id"], actor=MEMBER, as_of="2026-01-01")
        self.assertEqual(late["derived_status"], "overdue")
        self.assertEqual(early["derived_status"], "open")
        with self.assertRaises(AssertionError):
            self.assertEqual(
                late["derived_status"],
                mutant_derive_finding_status(finding, "2026-12-31"),
            )


if __name__ == "__main__":
    unittest.main()
