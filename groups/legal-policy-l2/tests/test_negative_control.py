"""Negative control: the single-use sandbox rule must be load-bearing.

Traces to: the contract's required negative control for Group 49
(Core functions 3/4, SI-10). The group's signature invariant is the
single-use rule: a sandbox session accepts exactly one execution
record, enforced by the store's ``_check_sandbox_unused`` seam.

Canonical expectation: a second execution against a sandbox session
is rejected with ``ValidationError``, consumes no id, and changes
nothing. The mutant is a ``LegalPolStore`` subclass whose
``_check_sandbox_unused`` does nothing: if the suite still passed
against the mutant, the single-use tests would be testing that code
ran, not that the invariant holds. Each test asserts (1) the
canonical expectation from the real implementation, (2) the mutant
would NOT produce that expectation, and (3) a literal
``assertRaises(AssertionError)`` showing that treating the mutant's
outcome as the expected outcome fails.
"""

import unittest

import legalpol_helpers as H
from legalpol.errors import ValidationError
from legalpol.store import LegalPolStore


class MutantLegalPolStore(LegalPolStore):
    """A store with the single-use sandbox check removed (the mutant)."""

    def _check_sandbox_unused(self, session_id):
        return None


def _sandbox_session(store):
    agency = store.create_agency(H.AGENCY_REF, H.AGENCY_LABEL, H.ADMIN)
    store.add_member(agency["id"], H.MEMBER.name, H.ADMIN)
    workspace = store.create_workspace(
        agency["id"], H.WORKSPACE_REF, H.WORKSPACE_TITLE, H.MEMBER)
    session = store.create_session(
        agency["id"], workspace["id"], "SES-SBX-1", H.MEMBER, sandbox=True)
    return agency, workspace, session


class TestNegativeControlSandboxSingleUse(unittest.TestCase):
    """Canonical: the second sandbox execution is rejected; the
    mutant waves it through."""

    def test_canonical_expectation_rejects_second_execution(self):
        """Canonical (Core 4): first execution recorded; the second
        raises ValidationError and the recorded set is unchanged."""
        store = H.fresh_store()
        agency, _ws, session = _sandbox_session(store)
        store.record_execution(agency["id"], session["id"], "EXE-1", H.MEMBER)
        with self.assertRaises(ValidationError):
            store.record_execution(agency["id"], session["id"], "EXE-2",
                                   H.MEMBER)
        recorded = store.list_executions(agency["id"], session["id"], H.MEMBER)
        self.assertEqual([e["execution_ref"] for e in recorded], ["EXE-1"])

    def test_mutant_would_not_reject(self):
        """Mutant: with the seam removed, the same second execution
        succeeds and two executions are recorded — so the canonical
        expectation, applied to the mutant's outcome, fails
        (asserted literally with assertRaises)."""
        store = MutantLegalPolStore()
        agency, _ws, session = _sandbox_session(store)
        store.record_execution(agency["id"], session["id"], "EXE-1", H.MEMBER)
        second = store.record_execution(agency["id"], session["id"], "EXE-2",
                                        H.MEMBER)
        self.assertEqual(second["execution_ref"], "EXE-2")
        recorded = store.list_executions(agency["id"], session["id"], H.MEMBER)
        self.assertEqual(len(recorded), 2)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(recorded), 1)

    def test_mutant_also_breaks_derived_consumption_semantics(self):
        """Mutant contrast: the real store's report counts exactly
        one execution for the sandbox session after the rejected
        second attempt; the mutant's counts two."""
        real = H.fresh_store()
        agency, _ws, session = _sandbox_session(real)
        real.record_execution(agency["id"], session["id"], "EXE-1", H.MEMBER)
        with self.assertRaises(ValidationError):
            real.record_execution(agency["id"], session["id"], "EXE-2",
                                  H.MEMBER)
        report = real.agency_report(agency["id"], H.ADMIN)
        self.assertEqual(report["execution_count"], 1)
        self.assertEqual(report["sandbox_sessions_consumed"], 1)

        mutant = MutantLegalPolStore()
        agency, _ws, session = _sandbox_session(mutant)
        mutant.record_execution(agency["id"], session["id"], "EXE-1", H.MEMBER)
        mutant.record_execution(agency["id"], session["id"], "EXE-2", H.MEMBER)
        mutant_report = mutant.agency_report(agency["id"], H.ADMIN)
        self.assertEqual(mutant_report["execution_count"], 2)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_report["execution_count"], 1)


if __name__ == "__main__":
    unittest.main()
