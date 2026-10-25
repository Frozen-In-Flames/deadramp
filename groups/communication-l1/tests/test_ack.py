"""Acknowledgement tests.

Traces to: Core function -- Acknowledgement tracking; contract for
``acknowledge/ack_status``.
"""

import unittest

from comm_helpers import OPERATOR, VIEWER, make_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestAck(unittest.TestCase):
    """Core: Acknowledgement tracking."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()

    def _delivered(self, require_ack=True):
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
            require_ack=require_ack,
        )
        self.store.dispatch_due(OPERATOR)
        delivery = self.store.list_deliveries(msg["id"], OPERATOR)[0]
        return msg, delivery

    def test_acknowledge_happy_path(self):
        """Core: Ack. Delivered + require_ack -> acknowledged with acked_utc."""
        msg, d = self._delivered()
        acked = self.store.acknowledge(d["id"], OPERATOR)
        self.assertEqual(acked["status"], "acknowledged")
        self.assertTrue(acked["acked_utc"])
        self.assertEqual(self.store.get_delivery(d["id"], OPERATOR)["status"], "acknowledged")

    def test_ack_status_counts(self):
        """Core: Ack. ack_status returns {message_id, require_ack, total, acknowledged, pending_contact_ids}."""
        msg, d = self._delivered()
        status = self.store.ack_status(msg["id"], OPERATOR)
        self.assertEqual(status["message_id"], msg["id"])
        self.assertTrue(status["require_ack"])
        self.assertEqual(status["total"], 1)
        self.assertEqual(status["acknowledged"], 0)
        self.assertEqual(status["pending_contact_ids"], [self.contact["id"]])
        self.store.acknowledge(d["id"], OPERATOR)
        status = self.store.ack_status(msg["id"], OPERATOR)
        self.assertEqual(status["acknowledged"], 1)
        self.assertEqual(status["pending_contact_ids"], [])

    def test_ack_requires_delivered(self):
        """Core: Ack. Queued delivery -> ValidationError."""
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[self.contact["id"]], channel_kinds=["email"], require_ack=True,
        )
        d = self.store.list_deliveries(msg["id"], OPERATOR)[0]
        with self.assertRaises(ValidationError):
            self.store.acknowledge(d["id"], OPERATOR)

    def test_ack_requires_require_ack_message(self):
        """Core: Ack. Delivered delivery on a require_ack=False message -> ValidationError."""
        msg, d = self._delivered(require_ack=False)
        with self.assertRaises(ValidationError):
            self.store.acknowledge(d["id"], OPERATOR)

    def test_ack_unknown_and_viewer_denied(self):
        """Core: Ack. Unknown delivery -> NotFoundError; viewer ack_record denied; unknown message ack_status -> NotFoundError."""
        msg, d = self._delivered()
        with self.assertRaises(NotFoundError):
            self.store.acknowledge("dlv-999", OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.store.acknowledge(d["id"], VIEWER)
        with self.assertRaises(NotFoundError):
            self.store.ack_status("msg-999", OPERATOR)
        # Viewer denial left it delivered, not acknowledged.
        self.assertEqual(self.store.get_delivery(d["id"], OPERATOR)["status"], "delivered")


if __name__ == "__main__":
    unittest.main()
