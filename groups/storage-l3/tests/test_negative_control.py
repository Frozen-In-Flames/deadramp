"""Mutation-verified negative control for the retention
derivation.

An oracle that passes whether or not retention has expired is
testing that code ran, not that retention is enforced. So the
canonical retention expectation is asserted here against a MUTANT
seam that reports every non-disposed message as ``retained``
forever -- under the mutant, the disposition gate never opens --
and the test asserts the canonical check FAILS against the
mutant. If the retention tests ever stopped discriminating, this
test fails.

The external drill (the same patch applied to the real
``src/storage/store.py``, suite re-run, file restored
byte-identical) is recorded in tests/README.md and
scratch/mutation-run.txt.
"""

import unittest

import storage.store as store_module

from storage.errors import ValidationError

from storage_helpers import (ADMIN, AFTER_BOUNDARY, BEFORE_BOUNDARY,
                             make_archive, make_message, make_store)


def _mutant_state(archived_at, retention_days, disposed, now):
    """Mutant seam: retention never expires."""
    if disposed:
        return "disposed"
    return "retained"


def canonical_gate_opens_after_retention(store, collection, message_id):
    """The retention suite's core expectation, stated once.

    Raises AssertionError (or lets a ValidationError escape, which
    the control wraps) when a message past its retention boundary
    does not read disposition_eligible and cannot be disposed of.
    """
    view = store.get_message(ADMIN, message_id, now=AFTER_BOUNDARY)
    assert view["retention_state"] == "disposition_eligible", (
        "state past the boundary is %s, expected disposition_eligible"
        % (view["retention_state"],))
    disposition = store.record_disposition(ADMIN, message_id, "shredded",
                                           at=AFTER_BOUNDARY)
    assert disposition["message_id"] == message_id
    view = store.get_message(ADMIN, message_id, now=BEFORE_BOUNDARY)
    assert view["retention_state"] == "disposed", (
        "state after disposition is %s, expected disposed"
        % (view["retention_state"],))


class NegativeControlTests(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_store(self):
        store, _audit = make_store()
        _org, _policy, collection = make_archive(store)
        message = make_message(store, collection)
        canonical_gate_opens_after_retention(store, collection,
                                             message["id"])

    def test_canonical_check_fails_on_the_mutant(self):
        store, _audit = make_store()
        _org, _policy, collection = make_archive(store)
        message = make_message(store, collection)
        original = store_module._derive_retention_state
        store_module._derive_retention_state = _mutant_state
        try:
            with self.assertRaises((AssertionError, ValidationError)):
                canonical_gate_opens_after_retention(store, collection,
                                                     message["id"])
        finally:
            store_module._derive_retention_state = original

    def test_gate_stays_shut_before_the_boundary_on_the_real_store(self):
        """The other arm discriminates too: inside the retention
        period the canonical store refuses disposition, so the
        invariant is not simply 'disposition always works'."""
        store, _audit = make_store()
        _org, _policy, collection = make_archive(store)
        message = make_message(store, collection)
        with self.assertRaises(ValidationError):
            store.record_disposition(ADMIN, message["id"], "shredded",
                                     at=BEFORE_BOUNDARY)


ORACLE_EXPECTED = (
    "External drill (patch _derive_retention_state in "
    "src/storage/store.py so the boundary comparison "
    "'if now >= boundary:' becomes 'if False:', re-run the "
    "suite, restore): exactly 10 tests did not pass "
    "(7 failures, 3 errors) -- "
    "test_retention.SeamTests.test_seam_states, "
    "test_retention.RetentionViewTests."
    "test_state_is_derived_at_read_and_never_stored, "
    "test_retention.RetentionViewTests."
    "test_exact_boundary_is_eligible, "
    "test_retention.RetentionViewTests."
    "test_list_filter_by_derived_state, "
    "test_retention.DispositionGateTests."
    "test_disposition_at_and_after_boundary (error), "
    "test_retention.DispositionGateTests."
    "test_double_disposition_is_refused (error), "
    "test_reporting.ReportingTests."
    "test_summary_retention_counts_follow_the_clock, "
    "test_service.ServiceTests.test_full_flow_with_retention_gate, "
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_singleton_spec.CarriedSubstrateCaseTests."
    "test_custody_linked_archival_reaches_the_disposition_gate "
    "(error) -- then the file restored byte-identical (SHA-256 "
    "verified) and the full suite green again. The tenth test, "
    "the singleton substrate case, is this tier's addition to the "
    "parent group's 9. A second drill on the audit hash seam is "
    "recorded alongside. Both are recorded in tests/README.md "
    "and scratch/mutation-run.txt."
)

if __name__ == "__main__":
    unittest.main()
