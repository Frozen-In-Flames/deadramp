"""Negative control: the suite must reject a mutant dispatch gate.

Traces to: the contract's required negative control for Group 37.

The traced claim: **dispatch honors the send gate** -- a delivery may
only be marked delivered (by the reference transport) when an enabled
channel of its kind exists; a disabled or absent channel must fail
the delivery with ``failure_reason='no_enabled_channel'``, and a
viewer (who lacks the ``dispatch`` permission) must not dispatch at
all.

The mutant below is a CommStore subclass whose
``_first_enabled_channel`` always returns a fake enabled channel --
the enabled-channel check is skipped -- so the mutant delivers even
when every real channel is disabled or absent.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation (it delivers
anyway), and (3) a literal assertRaises(AssertionError) showing that
treating the mutant's outcome as the expected outcome fails.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, make_store
from comm.access import require
from comm.errors import PermissionDenied
from comm.store import CommStore


class MutantCommStore(CommStore):
    """Mutant dispatch path: the enabled-channel check is skipped."""

    def _first_enabled_channel(self, kind):
        """Core: Dispatch (negative control mutant) -- always returns a fake enabled channel."""
        return {"id": "ch-mutant", "kind": kind, "name": "mutant", "enabled": True}


def mutant_gate(user, action):
    """The permission gate as a no-check mutant would run it."""
    return "allowed"


def _make(store_cls):
    """Build a store of the given class with contact/group/channel.

    Traces to: Core Dispatch negative control -- shared fixture for
    canonical and mutant stores (enabled email channel, one contact).
    """
    from comm.audit import AuditLog
    store = store_cls(audit=AuditLog())
    contact = store.create_contact(
        "Dana Example", {"email": "dana@example.com"}, OPERATOR
    )
    channel = store.create_channel("email", "primary-email", ADMIN, enabled=True)
    return store, contact, channel


class TestNegativeControlMutantDispatch(unittest.TestCase):
    """Core: Dispatch -- negative control for the send gate, traced
    claim: dispatch honors the send gate (enabled channel required,
    viewer cannot dispatch)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core: Dispatch (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_disabled_channel_fails_canonical_but_mutant_delivers(self):
        """Core: Dispatch, traced claim: dispatch honors the send gate.
        Canonical: disabled channel -> delivery failed/no_enabled_channel.
        Mutant: same setup delivers anyway."""
        store, contact, channel = _make(CommStore)
        store.set_channel_enabled(channel["id"], False, ADMIN)
        msg = store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[contact["id"]], channel_kinds=["email"],
        )
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary["failed"], 1)
        canonical = store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(canonical["status"], "failed")
        self.assertEqual(canonical["failure_reason"], "no_enabled_channel")

        mstore, mcontact, mchannel = _make(MutantCommStore)
        mstore.set_channel_enabled(mchannel["id"], False, ADMIN)
        mmsg = mstore.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[mcontact["id"]], channel_kinds=["email"],
        )
        msummary = mstore.dispatch_due(OPERATOR)
        self.assertEqual(msummary["delivered"], 1)  # mutant did NOT fail it
        mutant_status = mstore.list_deliveries(mmsg["id"], OPERATOR)[0]["status"]
        self.assertEqual(mutant_status, "delivered")
        self._assert_mutant_rejected(mutant_status, "failed")

    def test_absent_channel_fails_canonical_but_mutant_delivers(self):
        """Core: Dispatch, traced claim: dispatch honors the send gate.
        Canonical: no channel config at all for the kind -> failed.
        Mutant: delivers anyway."""
        from comm_helpers import fresh_store
        from comm.audit import AuditLog
        store = CommStore(audit=AuditLog())
        contact = store.create_contact("Dana", {"email": "d@x.y"}, OPERATOR)
        msg = store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[contact["id"]], channel_kinds=["email"],
        )
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary["failed"], 1)
        canonical_status = store.list_deliveries(msg["id"], OPERATOR)[0]["status"]
        self.assertEqual(canonical_status, "failed")

        mstore = MutantCommStore(audit=AuditLog())
        mcontact = mstore.create_contact("Dana", {"email": "d@x.y"}, OPERATOR)
        mmsg = mstore.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[mcontact["id"]], channel_kinds=["email"],
        )
        mstore.dispatch_due(OPERATOR)
        mutant_status = mstore.list_deliveries(mmsg["id"], OPERATOR)[0]["status"]
        self.assertEqual(mutant_status, "delivered")
        self._assert_mutant_rejected(mutant_status, "failed")

    def test_viewer_must_not_dispatch(self):
        """Core: Dispatch / Access control, traced claim: dispatch
        honors the send gate -- a viewer must not dispatch.
        Canonical: dispatch_due(VIEWER) raises PermissionDenied and
        the delivery stays queued. Mutant gate: waves the viewer
        through, which the canonical expectation rejects."""
        store, contact, group, channel = make_store()
        msg = store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[contact["id"]], channel_kinds=["email"],
        )
        with self.assertRaises(PermissionDenied):
            store.dispatch_due(VIEWER)
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "dispatch")
        self.assertEqual(
            store.list_deliveries(msg["id"], OPERATOR)[0]["status"], "queued"
        )
        mutant_outcome = mutant_gate(VIEWER, "dispatch")
        self.assertEqual(mutant_outcome, "allowed")  # mutant did not raise
        self._assert_mutant_rejected(mutant_outcome, "denied")


if __name__ == "__main__":
    unittest.main()
