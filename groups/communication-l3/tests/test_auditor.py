"""Auditor role tests (L3 High uplift, AC-5).

Traces to: Core function -- Access control, as uplifted to the High
baseline -- AC-5 (separation of duties): the ``auditor`` role holds
{ audit_read } ONLY; demo user dana=auditor can read and verify the
audit trail over HTTP, and is denied every operational permission
at the access-matrix, store, and service layers.
"""

import http.client
import json
import threading
import unittest

from comm_helpers import AUDITOR, OPERATOR, USERS, make_store
from comm.access import PERMISSIONS, can, permissions_for, require
from comm.audit import AuditLog
from comm.errors import PermissionDenied
from comm.service import make_server
from comm.store import CommStore

ALL_ACTIONS = {
    "contact_read", "channel_read", "template_read", "records_read",
    "contact_write", "group_write", "template_write", "message_compose",
    "dispatch", "ack_record", "channel_write", "audit_read",
}
DANA = {"X-User": "dana", "X-Role": "auditor"}
ALICE = {"X-User": "alice", "X-Role": "admin"}


class TestAuditorMatrix(unittest.TestCase):
    """AC-5: the auditor permission set is exactly {audit_read}."""

    def test_auditor_matrix_exactness(self):
        """AC-5: PERMISSIONS["auditor"] and permissions_for("auditor")
        are exactly {"audit_read"}; can() grants only that action."""
        self.assertEqual(set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(set(permissions_for("auditor")), {"audit_read"})
        self.assertTrue(can(AUDITOR, "audit_read"))
        require(AUDITOR, "audit_read")  # must not raise
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)


class TestAuditorStoreDenials(unittest.TestCase):
    """AC-5 at the store layer: AUDITOR is denied operational reads
    and writes (the store has no audit_read-gated method; the audit
    trail itself is read via AuditLog, not via CommStore)."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()

    def test_auditor_store_reads_denied(self):
        """AC-5: AUDITOR cannot list/get contacts, groups, channels,
        templates, messages, deliveries, or search at store level."""
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
        )
        attempts = [
            lambda: self.store.list_contacts(AUDITOR),
            lambda: self.store.get_contact(self.contact["id"], AUDITOR),
            lambda: self.store.list_groups(AUDITOR),
            lambda: self.store.list_group_members(self.group["id"], AUDITOR),
            lambda: self.store.list_channels(AUDITOR),
            lambda: self.store.get_channel(self.channel["id"], AUDITOR),
            lambda: self.store.list_templates(AUDITOR),
            lambda: self.store.list_messages(AUDITOR),
            lambda: self.store.get_message(msg["id"], AUDITOR),
            lambda: self.store.list_deliveries(msg["id"], AUDITOR),
            lambda: self.store.ack_status(msg["id"], AUDITOR),
            lambda: self.store.search("dana", AUDITOR),
        ]
        for attempt in attempts:
            with self.subTest(attempt=attempt):
                with self.assertRaises(PermissionDenied):
                    attempt()

    def test_auditor_store_writes_denied(self):
        """AC-5: AUDITOR cannot create contacts/groups/channels/
        templates, compose, dispatch, or acknowledge at store level,
        and the denials change nothing."""
        attempts = [
            lambda: self.store.create_contact("X", {"email": "x@y.z"}, AUDITOR),
            lambda: self.store.create_group("x", AUDITOR),
            lambda: self.store.create_channel("email", "x", AUDITOR),
            lambda: self.store.set_channel_enabled(self.channel["id"], False, AUDITOR),
            lambda: self.store.create_template("x", "s", "b", AUDITOR),
            lambda: self.store.compose_message(
                AUDITOR, subject="S", body="B",
                contact_ids=[self.contact["id"]], channel_kinds=["email"],
            ),
            lambda: self.store.dispatch_due(AUDITOR),
            lambda: self.store.acknowledge("dlv-1", AUDITOR),
        ]
        for attempt in attempts:
            with self.subTest(attempt=attempt):
                with self.assertRaises(PermissionDenied):
                    attempt()
        # Nothing changed: the canonical fixture is intact.
        self.assertEqual(len(self.store.list_contacts(OPERATOR)), 1)
        self.assertEqual(self.store.list_messages(OPERATOR), [])


class TestAuditorOverHttp(unittest.TestCase):
    """AC-5 over HTTP: dana reads the audit trail, and is denied
    every operational endpoint."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CommStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        """AC-5: helper performing a real HTTP request."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = None
        hdrs = dict(headers or {})
        if body is not None:
            payload = json.dumps(body)
            hdrs.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            parsed = None
        return status, parsed

    def test_auditor_can_read_audit(self):
        """AC-5/AU-6: dana GET /audit -> 200 with {entries}."""
        status, payload = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)

    def test_auditor_can_verify_audit(self):
        """AC-5/AU-9: dana GET /audit/verify -> 200 with ok True."""
        status, payload = self.request("GET", "/audit/verify", headers=DANA)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["first_bad_index"])

    def test_auditor_operational_gets_are_403(self):
        """AC-5: dana GET on operational endpoints -> 403 (contacts,
        channels, templates, messages, search)."""
        for path in ("/contacts", "/channels", "/templates", "/messages",
                     "/groups", "/search?q=dana"):
            with self.subTest(path=path):
                status, parsed = self.request("GET", path, headers=DANA)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)

    def test_auditor_operational_posts_are_403(self):
        """AC-5: dana POST on operational endpoints -> 403 (create
        contact, create channel, dispatch-due)."""
        for method, path, body in (
            ("POST", "/contacts", {"name": "X", "addresses": {"email": "x@y.z"}}),
            ("POST", "/channels", {"kind": "email", "name": "x"}),
            ("POST", "/dispatch-due", {}),
        ):
            with self.subTest(path=path):
                status, parsed = self.request(method, path, headers=DANA, body=body)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
