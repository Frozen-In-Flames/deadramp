"""Mutation-verified negative control for the balanced-entry
rule.

An oracle that passes whether or not a ledger entry balances is
testing that code ran, not that balance is enforced. So the
canonical balance expectation is asserted here against a MUTANT
seam that accepts every entry -- under the mutant, unbalanced,
two-sided, and zero entries all record -- and the test asserts
the canonical check FAILS against the mutant. If the ledger tests
ever stopped discriminating, this test fails.

The external drill (the same patch applied to the real
``src/erp/store.py``, suite re-run, file restored byte-identical)
is recorded in tests/README.md and scratch/mutation-run.txt.
"""

import unittest

import erp.store as store_module

from erp.errors import ValidationError

from erp_helpers import (BALANCED_LINES, OPERATOR, UNBALANCED_LINES,
                         make_org, make_store)


def _mutant_check(lines):
    """Mutant seam: every entry 'balances'."""
    return None


def canonical_entry_balances(store, org):
    """The ledger suite's core expectation, stated once.

    Raises AssertionError (or lets a ValidationError escape, which
    the control wraps) when a balanced entry does not record with
    equal derived totals, or when an unbalanced entry is recorded
    instead of refused.
    """
    entry = store.create_ledger_entry(
        OPERATOR, org["id"], "JE-CANON", "Canonical", BALANCED_LINES)
    assert entry["total_debits_cents"] == entry["total_credits_cents"] == 12500, (
        "derived totals are %s / %s, expected 12500 / 12500"
        % (entry["total_debits_cents"], entry["total_credits_cents"]))
    refused = False
    try:
        store.create_ledger_entry(
            OPERATOR, org["id"], "JE-BAD", "Unbalanced", UNBALANCED_LINES)
    except ValidationError:
        refused = True
    assert refused, "an unbalanced entry was recorded"
    assert len(store.list_ledger_entries(OPERATOR)) == 1, (
        "the store holds %d entries, expected exactly the balanced one"
        % len(store.list_ledger_entries(OPERATOR)))


class NegativeControlTests(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_store(self):
        store, _audit = make_store()
        org = make_org(store)
        canonical_entry_balances(store, org)

    def test_canonical_check_fails_on_the_mutant(self):
        store, _audit = make_store()
        org = make_org(store)
        original = store_module._check_entry_balanced
        store_module._check_entry_balanced = _mutant_check
        try:
            with self.assertRaises((AssertionError, ValidationError)):
                canonical_entry_balances(store, org)
        finally:
            store_module._check_entry_balanced = original

    def test_unbalanced_entry_refused_on_the_real_store(self):
        """The other arm discriminates too: on the real store the
        unbalanced entry is refused and nothing is recorded, so
        the invariant is not simply 'entries always record'."""
        store, _audit = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            store.create_ledger_entry(
                OPERATOR, org["id"], "JE-BAD", "Unbalanced",
                UNBALANCED_LINES)
        self.assertEqual(store.list_ledger_entries(OPERATOR), [])


ORACLE_EXPECTED = (
    "External drill (patch _check_entry_balanced in "
    "src/erp/store.py to a no-op, re-run the suite, restore): "
    "exactly 7 tests did not pass (7 failures, 0 errors) -- "
    "test_ledger.LedgerEntryTests."
    "test_unbalanced_entry_is_refused_whole, "
    "test_ledger.SeamTests.test_seam_refuses_a_zero_total, "
    "test_ledger.SeamTests."
    "test_seam_refuses_two_sided_and_zero_lines, "
    "test_ledger.SeamTests.test_seam_refuses_unequal_totals, "
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_negative_control.NegativeControlTests."
    "test_unbalanced_entry_refused_on_the_real_store, "
    "test_service.ServiceTests.test_full_flow_with_balance_gate "
    "-- then the file restored byte-identical (SHA-256 verified) "
    "and the full suite green again. Recorded in tests/README.md "
    "and scratch/mutation-run.txt."
)

if __name__ == "__main__":
    unittest.main()
