"""Audit reduction & search tests (L3 High uplift, AU-7/AU-6).

Traces to: UNION-SPEC Core function 11 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-7 (audit reduction and report
generation): ``AuditLog.query(actor, action, target, since, until)``
returns the entries matching all given filters, with since/until
compared against the ISO ``ts`` string (inclusive on both ends);
AU-6: ``GET /audit`` (audit_read) passes the actor / action /
target / since / until query parameters through to it.
"""

import http.client
import json
import threading
import unittest
from urllib.parse import urlencode

from collab_helpers import USERS_REGISTRY
from collab.audit import AuditLog
from collab.service import make_server
from collab.store import CollabStore

# Fixed timestamps make the since/until windows deterministic: the
# query layer compares against the stored ts strings, so pinning them
# here exercises exactly that comparison.
_TS = [
    "2026-01-01T00:00:00+00:00",
    "2026-01-02T00:00:00+00:00",
    "2026-01-03T00:00:00+00:00",
    "2026-01-04T00:00:00+00:00",
]


def _pinned_log():
    """Four entries with known actors/actions/targets/timestamps."""
    log = AuditLog()
    log.record("alice", "workspace_create", "ws-1")
    log.record("bob", "message_post", "ws-1")
    log.record("alice", "file_share", "ws-1")
    log.record("carol", "message_post", "ws-2")
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
            ["workspace_create", "message_post", "file_share", "message_post"],
        )

    def test_query_filters_by_actor(self):
        """AU-7: actor filter returns only that actor's entries."""
        result = self.log.query(actor="alice")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(e["actor"] == "alice" for e in result))
        self.assertEqual(
            [e["action"] for e in result], ["workspace_create", "file_share"]
        )

    def test_query_filters_by_action(self):
        """AU-7: action filter returns only entries with that action."""
        result = self.log.query(action="message_post")
        self.assertEqual(len(result), 2)
        self.assertEqual([e["actor"] for e in result], ["bob", "carol"])

    def test_query_filters_by_target(self):
        """AU-7: target filter returns only entries for that target."""
        result = self.log.query(target="ws-2")
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
        result = self.log.query(actor="alice", action="file_share")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "ws-1")
        self.assertEqual(self.log.query(actor="alice", action="message_post"), [])
        result = self.log.query(actor="bob", target="ws-1", since=_TS[0], until=_TS[1])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "message_post")


class TestAuditQueryEndpoint(unittest.TestCase):
    """AU-7/AU-6 over HTTP: GET /audit passes the filter parameters
    through to AuditLog.query (audit_read required)."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CollabStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS_REGISTRY)
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()
        # Seed a known trail directly on the shared log.
        cls.audit.record("alice", "workspace_create", "ws-1")
        cls.audit.record("bob", "message_post", "ws-1")
        cls.audit.record("alice", "file_share", "ws-1")
        cls.audit.record("bob", "workspace_create", "ws-2")

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
        conn.request(
            "GET", path, headers=headers or {"X-User": "alice", "X-Role": "admin"}
        )
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
            ["message_post", "workspace_create"],
        )

    def test_audit_endpoint_filters_by_action(self):
        """AU-7: GET /audit?action=workspace_create returns only
        workspace_create entries."""
        status, payload = self._get_audit({"action": "workspace_create"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(e["action"] == "workspace_create" for e in entries))
        self.assertEqual(
            sorted(e["actor"] for e in entries), ["alice", "bob"]
        )

    def test_audit_endpoint_filters_by_target_and_window(self):
        """AU-7: GET /audit honours target and the since/until
        window -- a window after all activity is empty."""
        status, payload = self._get_audit({"target": "ws-2"})
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["actor"], "bob")

        status, payload = self._get_audit(
            {"since": "2999-01-01T00:00:00+00:00"}
        )
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
        self.assertTrue(
            all(e["actor"] == "bob" for e in payload["entries"])
        )


if __name__ == "__main__":
    unittest.main()
