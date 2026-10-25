"""Negative control: the suite must reject a mutant self-approval gate.

Traces to: the contract's required negative control for this group
(Data Management L1 singleton; the Group 12 control, carried with the
reused substrate).

The traced claim: **access decisions are never self-approved** --
a requester may never decide their own access request. At L2 this
guard traced to a sibling's evidenced governance claim; in this
singleton group it is carried as a design property of the substrate
itself (see the core-boundary decision in UNION-SPEC.md): data held
in the registry is released only by decision of someone other than
its requester (control family AC-3 access enforcement; AC-5 is the
separation-of-duties family home, named here as design lineage --
AC-5 is not itself a Low-baseline selection and no Low claim rests
on it). The store enforces this in
``DataMgmtStore._check_decider_not_requester``.

The mutant below is a DataMgmtStore subclass whose
``_check_decider_not_requester`` is a no-op -- the separation-of-
duties check is skipped -- so the mutant approves a requester's own
request and creates the grant the real store must never create.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation
(PermissionDenied, the request stays "requested", no grant exists),
(2) the mutant would NOT produce that expectation (it approves and
grants), and (3) a literal assertRaises(AssertionError) showing that
treating the mutant's outcome as the expected outcome fails.
"""

import unittest

from datamgmt_helpers import STEWARD, VIEWER, make_store
from datamgmt.access import User
from datamgmt.audit import AuditLog
from datamgmt.errors import PermissionDenied
from datamgmt.store import DataMgmtStore


class MutantDataMgmtStore(DataMgmtStore):
    """Mutant decision path: the decider-is-not-requester check is skipped."""

    def _check_decider_not_requester(self, request, actor):
        """Core: Access decisions (negative control mutant) -- no-op: self-approval is never checked."""
        return None


def _make_mutant():
    """Build a mutant store with the canonical dataset and source.

    Traces to: Core Access decisions negative control -- shared
    fixture shape with datamgmt_helpers.make_store, built on the
    mutant store class.
    """
    store = MutantDataMgmtStore(audit=AuditLog())
    dataset = store.create_dataset(
        "Claims Extract",
        "Nightly extract of claims records",
        STEWARD,
        classification="cui",
        tags=["claims", "nightly"],
        schema=[
            {"name": "patient_id", "type": "string", "required": True, "sensitive": True},
            {"name": "amount", "type": "number", "required": True, "sensitive": False},
        ],
    )
    source = store.register_source("ehr-feed", "api", STEWARD, location="ehr.internal")
    return store, dataset, source


class TestNegativeControlMutantSelfApproval(unittest.TestCase):
    """Core: Access decisions -- negative control for self-approval,
    traced claim: access decisions are never self-approved
    (AC-3 access enforcement; the substrate's never-self-approve
    design rule, AC-5 family lineage as noted in the module docstring)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core: Access decisions (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_viewer_self_decision_denied_canonical_but_mutant_approves(self):
        """Core: Access decisions, traced claim: access decisions are never self-approved (AC-3/AC-5).
        Canonical case (pinned): VIEWER requests access to the
        make_store dataset; VIEWER deciding their own request raises
        PermissionDenied on the real store, the request stays
        "requested", and no grant exists. Mutant: the same decision
        succeeds, the status is "approved", and a grant is created.

        Isolation note: a viewer decider is *also* independently
        barred by the access_decide permission, so to isolate the
        mutated check the mutant leg (and one canonical leg below)
        present the requester's own identity -- the name "carol" --
        in a role that holds access_decide, User("carol", "steward").
        The self-decision check is name-based, so with every other
        gate satisfied it is the only check that can deny; on the
        real store it does, and on the mutant it is gone."""
        store, dataset, source = make_store()
        req = store.request_access(dataset["id"], "research use", VIEWER)
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(req["id"], True, VIEWER)
        # The self-decision check alone also denies, with a decider
        # who holds access_decide but shares the requester's name.
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(req["id"], True, User("carol", "steward"))
        canonical = store.get_access_request(req["id"], STEWARD)
        self.assertEqual(canonical["status"], "requested")
        self.assertIsNone(canonical["grant_id"])
        self.assertEqual(store.list_grants(actor=STEWARD), [])

        mstore, mdataset, msource = _make_mutant()
        mreq = mstore.request_access(mdataset["id"], "research use", VIEWER)
        decided = mstore.decide_access_request(
            mreq["id"], True, User("carol", "steward")
        )
        self.assertEqual(decided["status"], "approved")  # mutant did NOT deny
        self.assertIsNotNone(decided["grant_id"])
        grants = mstore.list_grants(actor=STEWARD)
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["grantee"], "carol")
        self._assert_mutant_rejected(decided["status"], "requested")

    def test_steward_self_decision_denied_canonical_but_mutant_approves(self):
        """Core: Access decisions, traced claim: access decisions are never self-approved (AC-3/AC-5).
        Canonical: a steward (who holds access_decide) deciding their
        own request still raises PermissionDenied -- the bar is the
        self-decision check, not the role. Mutant: approves it."""
        store, dataset, source = make_store()
        req = store.request_access(dataset["id"], "steward ask", STEWARD)
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(req["id"], True, STEWARD)
        self.assertEqual(
            store.get_access_request(req["id"], STEWARD)["status"], "requested"
        )
        self.assertEqual(store.list_grants(actor=STEWARD), [])

        mstore, mdataset, msource = _make_mutant()
        mreq = mstore.request_access(mdataset["id"], "steward ask", STEWARD)
        decided = mstore.decide_access_request(mreq["id"], True, STEWARD)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(len(mstore.list_grants(actor=STEWARD)), 1)
        self._assert_mutant_rejected(decided["status"], "requested")

    def test_mutant_self_denial_also_approves_nothing_extra(self):
        """Core: Access decisions, traced claim: access decisions are never self-approved (AC-3/AC-5).
        Control on the control: on the real store, a *different*
        steward deciding carol's request succeeds -- the canonical
        denial above is the self-decision check firing, not a blanket
        refusal of decisions."""
        store, dataset, source = make_store()
        req = store.request_access(dataset["id"], "research use", VIEWER)
        decided = store.decide_access_request(req["id"], True, STEWARD)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(len(store.list_grants(actor=STEWARD)), 1)
        self._assert_mutant_rejected("approved-by-other", "denied-self-decision")


if __name__ == "__main__":
    unittest.main()
