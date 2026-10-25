"""Audit reduction & search tests (L3 High uplift, AU-7/AU-6).

Traces to: Core function -- Append-only audit log, as uplifted to the
High baseline -- AU-7 (audit reduction and report generation):
``AuditLog.query(actor, action, target, since, until)`` returns the
entries matching all given filters, with since/until compared
against the ISO ``ts`` string (inclusive on both ends); AU-6:
``GET /audit`` (audit_read) passes the actor / action / target /
since / until query parameters through to it.
"""

import http.client
import json
import threading
import unittest
from urllib.parse import urlencode

from comm_helpers import USERS
from comm.audit import AuditLog
from comm.service import make_server
from comm.store import CommStore

_TS = [
    "2026-01-01T00:00:00+00:00",
    "2026-01-02T00:00:00+00:00",
    "2026-01-03T00:00:00+00:00",
    "2026-01-04T00:00:00+00:00",
]


def _pinned_log():
    """Four entries with known actors/actions/targets/timestamps.

    The ts values are pinned directly on the stored entries so the
    since/until windows are deterministic; pinning ts after record()
    deliberately does not recompute hashes (query does not verify).
    """
    log = AuditLog()
    log.record("alice", "contact_create", "ct-1")
    log.record("bob", "message_compose", "msg-1")
    log.record("alice", "channel_create", "ch-1")
    log.record("carol", "message_compose", "msg-2")
    for entry, ts in zip(log._entries, _TS):
        entry["ts"] = ts
    return log


class TestAuditQuery(unittest.TestCase):
    """AU-7: AuditLog.query filters the trail."""

    def setUp(self):
        self.log = _pinned_log()

    def test_query_no_filters_returns_all(self):
        """AU-7: query() with no filters is the full trail, in order."""
        result = self.log.query()
        self.assertEqual(len(result), 4)
        self.assertEqual(
            [e["action"] for e in result],
            ["contact_create", "message_compose", "channel_create", "message_compose"],
        )

    def test_query_filters_by_actor(self):
        """AU-7: actor filter returns only that actor's entries."""
        result = self.log.query(actor="alice")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(e["actor"] == "alice" for e in result))
        self.assertEqual(
            [e["action"] for e in result], ["contact_create", "channel_create"]
        )

    def test_query_filters_by_action(self):
        """AU-7: action filter returns only entries with that action."""
        result = self.log.query(action="message_compose")
        self.assertEqual(len(result), 2)
        self.assertEqual([e["actor"] for e in result], ["bob", "carol"])

    def test_query_filters_by_target(self):
        """AU-7: target filter returns only entries for that target."""
        result = self.log.query(target="msg-2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actor"], "carol")

    def test_query_since_is_inclusive(self):
        """AU-7: since compares against the ts string, inclusively --
        entries at or after the bound are kept."""
        result = self.log.query(since=_TS[1])
        self.assertEqual([e["ts"] for e in result], _TS[1:])

    def test_query_until_is_inclusive(self):
        """AU-7: until compares against the ts string, inclusively --
        entries at or before the bound are kept."""
        result = self.log.query(until=_TS[2])
        self.assertEqual([e["ts"] for e in result], _TS[:3])

    def test_query_window_since_and_until(self):
        """AU-7: since+until together select the window between them."""
        result = self.log.query(since=_TS[1], until=_TS[2])
        self.assertEqual([e["ts"] for e in result], _TS[1:3])
        self.assertEqual([e["actor"] for e in result], ["bob", "alice"])

    def test_query_combines_filters(self):
        """AU-7: filters compose (AND) -- actor plus action narrows to
        the intersection; a non-matching combination is empty."""
        result = self.log.query(actor="alice", action="channel_create")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "ch-1")
        self.assertEqual(self.log.query(actor="alice", action="message_compose"), [])
        result = self.log.query(actor="bob", target="msg-1", since=_TS[0], until=_TS[1])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "message_compose")


class TestAuditQueryEndpoint(unittest.TestCase):
    """AU-7/AU-6 over HTTP: GET /audit passes the filter parameters
    through to AuditLog.query (audit_read required)."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CommStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.audit.record("alice", "contact_create", "ct-1")
        cls.audit.record("bob", "message_compose", "msg-1")
        cls.audit.record("alice", "channel_create", "ch-1")
        cls.audit.record("bob", "contact_create", "ct-2")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get_audit(self, params=None, headers=None):
        path = "/audit"
        if params:
            path += "?" + urlencode(params)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers or {"X-User": "alice", "X-Role": "admin"})
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def test_audit_endpoint_filters_by_actor(self):
        """AU-7: GET /audit?actor=bob returns only bob's entries."""
        status, payload = self._get_audit({"actor": "bob"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(e["actor"] == "bob" for e in entries))
        self.assertEqual(
            sorted(e["action"] for e in entries),
            ["contact_create", "message_compose"],
        )

    def test_audit_endpoint_filters_by_action(self):
        """AU-7: GET /audit?action=contact_create returns only
        contact_create entries."""
        status, payload = self._get_audit({"action": "contact_create"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(e["action"] == "contact_create" for e in entries))
        self.assertEqual(sorted(e["actor"] for e in entries), ["alice", "bob"])

    def test_audit_endpoint_filters_by_target_and_window(self):
        """AU-7: GET /audit honours target and the since/until
        window -- a window after all activity is empty."""
        status, payload = self._get_audit({"target": "ct-2"})
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["actor"], "bob")

        status, payload = self._get_audit({"since": "2999-01-01T00:00:00+00:00"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])

    def test_audit_endpoint_filters_usable_by_auditor(self):
        """AC-5/AU-7: the auditor role can use the reduced audit
        search, not just administrators."""
        status, payload = self._get_audit(
            {"actor": "bob"},
            headers={"X-User": "dana", "X-Role": "auditor"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["entries"])
        self.assertTrue(all(e["actor"] == "bob" for e in payload["entries"]))


if __name__ == "__main__":
    unittest.main()
