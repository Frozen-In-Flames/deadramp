"""Dispatch tests.

Traces to: Core function -- Dispatch with receipts / scheduling;
contract for ``dispatch_due/dispatch_message``. The reference
transport is a deterministic stub (labelled reference_transport).
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, make_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError

FUTURE = "2999-01-01T00:00:00+00:00"
PAST = "2000-01-01T00:00:00+00:00"


class TestDispatch(unittest.TestCase):
    """Core: Dispatch with receipts."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()

    def _compose(self, **kw):
        kw.setdefault("subject", "Hi")
        kw.setdefault("body", "B")
        kw.setdefault("contact_ids", [self.contact["id"]])
        kw.setdefault("channel_kinds", ["email"])
        return self.store.compose_message(OPERATOR, **kw)

    def test_dispatch_due_delivers_with_reference_receipt(self):
        """Core: Dispatch. Enabled channel -> delivered, attempts 1, receipt labelled reference transport."""
        msg = self._compose()
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary, {"dispatched": 1, "delivered": 1, "failed": 0})
        d = self.store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "delivered")
        self.assertEqual(d["attempts"], 1)
        self.assertEqual(d["receipt"]["transport"], "reference")
        self.assertTrue(d["receipt"]["reference_transport"])
        self.assertTrue(d["receipt"]["delivered_utc"])

    def test_dispatch_due_no_enabled_channel_fails(self):
        """Core: Dispatch. No enabled channel -> failed, failure_reason no_enabled_channel, attempts 1."""
        self.store.set_channel_enabled(self.channel["id"], False, ADMIN)
        msg = self._compose()
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary, {"dispatched": 1, "delivered": 0, "failed": 1})
        d = self.store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["failure_reason"], "no_enabled_channel")
        self.assertEqual(d["attempts"], 1)

    def test_dispatch_due_absent_channel_fails(self):
        """Core: Dispatch. Absent channel (sms with no sms channel config) -> failed no_enabled_channel."""
        msg = self._compose(channel_kinds=["sms"])
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary["failed"], 1)
        d = self.store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["failure_reason"], "no_enabled_channel")

    def test_dispatch_respects_send_at_gate(self):
        """Core: Dispatch / Scheduling. Future send_at is not due; explicit now after send_at dispatches it; past send_at is due."""
        msg = self._compose(send_at=FUTURE)
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary, {"dispatched": 0, "delivered": 0, "failed": 0})
        self.assertEqual(
            self.store.list_deliveries(msg["id"], OPERATOR)[0]["status"], "queued"
        )
        summary = self.store.dispatch_due(OPERATOR, now="2999-01-02T00:00:00+00:00")
        self.assertEqual(summary["delivered"], 1)
        msg2 = self._compose(send_at=PAST)
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary["delivered"], 1)

    def test_dispatch_due_now_as_datetime_and_bad_now(self):
        """Core: Dispatch. now accepts a datetime; malformed now -> ValidationError."""
        from datetime import datetime, timezone
        self._compose(send_at=FUTURE)
        summary = self.store.dispatch_due(
            OPERATOR, now=datetime(2999, 1, 2, tzinfo=timezone.utc)
        )
        self.assertEqual(summary["delivered"], 1)
        with self.assertRaises(ValidationError):
            self.store.dispatch_due(OPERATOR, now="junk")

    def test_dispatch_message_and_future_validation(self):
        """Core: Dispatch. dispatch_message dispatches one message; future send_at -> ValidationError; unknown -> NotFoundError."""
        msg = self._compose()
        other = self._compose()
        summary = self.store.dispatch_message(msg["id"], OPERATOR)
        self.assertEqual(summary["delivered"], 1)
        self.assertEqual(
            self.store.list_deliveries(other["id"], OPERATOR)[0]["status"], "queued"
        )
        future = self._compose(send_at=FUTURE)
        with self.assertRaises(ValidationError):
            self.store.dispatch_message(future["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.dispatch_message("msg-999", OPERATOR)

    def test_dispatch_not_requeued(self):
        """Core: Dispatch. Already-delivered deliveries are not dispatched again."""
        self._compose()
        self.store.dispatch_due(OPERATOR)
        summary = self.store.dispatch_due(OPERATOR)
        self.assertEqual(summary, {"dispatched": 0, "delivered": 0, "failed": 0})

    def test_viewer_cannot_dispatch(self):
        """Core: Dispatch / Access control. Viewer dispatch denied before any state change."""
        msg = self._compose()
        with self.assertRaises(PermissionDenied):
            self.store.dispatch_due(VIEWER)
        with self.assertRaises(PermissionDenied):
            self.store.dispatch_message(msg["id"], VIEWER)
        self.assertEqual(
            self.store.list_deliveries(msg["id"], OPERATOR)[0]["status"], "queued"
        )


if __name__ == "__main__":
    unittest.main()
