"""Negative control: the suite must reject mutant derivations.

Traces to: the contract's required negative control for Group 19.

The traced claims: **compliance derivation at read time** -- a
participant with an open violation must read ``noncompliant`` and a
participant with nothing must read ``no_records`` (both via
``ConstructStore._contractor_compliance``); and **contract expiry
derivation at read time** -- an executed contract past its
``end_at`` must read ``expiry_state='expired'`` (via
``ConstructStore._contract_expiry_state``). Both values are derived
at read time; they are never stored.

The mutant below is a ConstructStore subclass overriding both
derivation points: ``_contractor_compliance`` always returns
``"compliant"`` and ``_contract_expiry_state`` always returns
``"active"``.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing that treating
the mutant's outcome as the expected outcome fails.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, make_store
from construct.audit import AuditLog
from construct.store import ConstructStore

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"
PS = "2025-01-01T00:00:00Z"
PE = "2025-01-15T00:00:00Z"


class MutantConstructStore(ConstructStore):
    """Mutant derivation: compliance and expiry derivation suppressed."""

    def _contractor_compliance(self, project_id, org_id):
        """Compliance (negative control mutant) -- always compliant."""
        return "compliant"

    def _contract_expiry_state(self, contract, now_dt):
        """Expiry (negative control mutant) -- always active."""
        return "active"


def _make(store_cls):
    """Build a store of the given class on the canonical fixture.

    Traces to: negative control -- shared fixture for canonical and
    mutant stores. Returns (store, project, prime_org, sub_org).
    """
    audit = AuditLog()
    store = store_cls(audit=audit)
    prime_org = store.create_org("Prime Builders", ADMIN, reference="PRIME-1")
    sub_org = store.create_org("Sub Trades", ADMIN, reference="SUB-1")
    project = store.create_project("Tower One", ADMIN, location="Dallas")
    store.transition_project(project["id"], ADMIN, "active")
    store.add_participant(project["id"], prime_org["id"], ADMIN, tier=1, role="prime")
    store.add_participant(project["id"], sub_org["id"], ADMIN, tier=2, role="sub")
    project = store.get_project(project["id"], ADMIN)
    return store, project, prime_org, sub_org


class TestNegativeControlMutantDerivation(unittest.TestCase):
    """Compliance/Expiry: negative control for read-time derivation."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Negative control. Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_open_violation_noncompliant_canonical_but_mutant_not(self):
        """Compliance, traced claim: compliance derivation at read time.
        Canonical: (a) participant with an open violation reads noncompliant.
        Mutant: same setup reads compliant."""
        store, project, prime, sub = _make(ConstructStore)
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=True)
        store.create_violation(ADMIN, project["id"], prime["id"], "wage", "Issue")
        canonical = store.contractor_compliance(project["id"], prime["id"], ADMIN)
        self.assertEqual(canonical["status"], "noncompliant")
        self.assertEqual(canonical["open_violations"], 1)

        mstore, mproject, mprime, msub = _make(MutantConstructStore)
        mstore.create_payroll(OPERATOR, mproject["id"], mprime["id"], PS, PE, certified=True)
        mstore.create_violation(ADMIN, mproject["id"], mprime["id"], "wage", "Issue")
        mutant = mstore.contractor_compliance(mproject["id"], mprime["id"], ADMIN)
        self.assertEqual(mutant["status"], "compliant")  # mutant did NOT derive noncompliance
        self._assert_mutant_rejected(mutant["status"], "noncompliant")

    def test_no_records_canonical_but_mutant_not(self):
        """Compliance, traced claim: compliance derivation at read time.
        Canonical: (b) participant with nothing reads no_records.
        Mutant: same setup reads compliant."""
        store, project, prime, sub = _make(ConstructStore)
        canonical = store.contractor_compliance(project["id"], prime["id"], ADMIN)
        self.assertEqual(canonical["status"], "no_records")
        self.assertEqual(store.report(ADMIN, now=NOW)["compliance"]["no_records"], 2)

        mstore, mproject, mprime, msub = _make(MutantConstructStore)
        mutant = mstore.contractor_compliance(mproject["id"], mprime["id"], ADMIN)
        self.assertEqual(mutant["status"], "compliant")  # mutant did NOT derive no_records
        self.assertEqual(mstore.report(ADMIN, now=NOW)["compliance"]["no_records"], 0)
        self._assert_mutant_rejected(mutant["status"], "no_records")

    def test_expired_contract_canonical_but_mutant_not(self):
        """Expiry, traced claim: expiry derivation at read time.
        Canonical: (c) an executed contract past end_at reads expiry_state 'expired'.
        Mutant: same setup reads 'active'."""
        store, project, prime, sub = _make(ConstructStore)
        con = store.create_contract(OPERATOR, "Deal", project["id"], end_at=PAST)
        store.transition_contract(con["id"], OPERATOR, "in_review")
        store.transition_contract(con["id"], OPERATOR, "executed")
        canonical = store.get_contract(con["id"], ADMIN, now=NOW)
        self.assertEqual(canonical["expiry_state"], "expired")

        mstore, mproject, mprime, msub = _make(MutantConstructStore)
        mcon = mstore.create_contract(OPERATOR, "Deal", mproject["id"], end_at=PAST)
        mstore.transition_contract(mcon["id"], OPERATOR, "in_review")
        mstore.transition_contract(mcon["id"], OPERATOR, "executed")
        mutant = mstore.get_contract(mcon["id"], ADMIN, now=NOW)
        self.assertEqual(mutant["expiry_state"], "active")  # mutant did NOT derive expiry
        self._assert_mutant_rejected(mutant["expiry_state"], "expired")


if __name__ == "__main__":
    unittest.main()
