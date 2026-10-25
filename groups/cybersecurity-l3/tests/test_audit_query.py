"""Audit reduction & search tests (L3 High uplift, AU-7).

Traces to: UNION-SPEC Core function 11 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-7 (audit reduction and report generation):
``AuditLog.query(actor, action, target, since, until)`` returns the
entries matching all given filters, with since/until compared against
the ISO ``ts`` string; and ``GET /audit`` passes the actor / action /
target / since / until query parameters through to it.
"""

import http.client
import json
import threading
import unittest
from urllib.parse import urlencode

from cyber.audit import AuditLog
from cyber.service import make_server
from cyber.store import CyberStore

# Fixed timestamps make the since/until windows deterministic: the
# query layer compares against the stored ts strings, so pinning them
# here exercises exactly that comparison. (Pinning ts after recording
# breaks these entries' hash chains by construction; chain integrity
# is covered in test_audit_chain.py, not here.)
_TS = [
    "2026-01-01T00:00:00+00:00",
    "2026-01-02T00:00:00+00:00",
    "2026-01-03T00:00:00+00:00",
    "2026-01-04T00:00:00+00:00",
]


def _pinned_log():
    """Four entries with known actors/actions/targets/timestamps."""
    log = AuditLog()
    log.record("alice", "asset_create", "asset-1")
    log.record("bob", "finding_ingest", "find-1")
    log.record("alice", "control_assess", "AC-2")
    log.record("carol", "search", "openssl")
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
            ["asset_create", "finding_ingest", "control_assess", "search"],
        )

    def test_query_filters_by_actor(self):
        """AU-7: actor filter returns only that actor's entries."""
        result = self.log.query(actor="alice")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(e["actor"] == "alice" for e in result))
        self.assertEqual(
            [e["action"] for e in result],
            ["asset_create", "control_assess"],
        )

    def test_query_filters_by_action(self):
        """AU-7: action filter returns only entries with that action."""
        result = self.log.query(action="finding_ingest")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actor"], "bob")

    def test_query_filters_by_target(self):
        """AU-7: target filter returns only entries for that target."""
        result = self.log.query(target="AC-2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actor"], "alice")

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
        the intersection."""
        result = self.log.query(actor="alice", action="control_assess")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "AC-2")
        self.assertEqual(
            self.log.query(actor="alice", action="finding_ingest"), []
        )


class TestAuditQueryEndpoint(unittest.TestCase):
    """AU-7 over HTTP: GET /audit passes actor/action/target/since/
    until through to AuditLog.query (audit_read required)."""

    @classmethod
    def setUpClass(cls):
        cls.audit = _pinned_log()
        cls.store = CyberStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1",
            0,
            cls.store,
            cls.audit,
            {"alice": "admin", "bob": "analyst", "dana": "auditor"},
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path, headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def test_audit_endpoint_unfiltered_returns_all(self):
        """AU-7: GET /audit with no parameters returns the trail as
        recorded before this request (the request's own audit_read
        entry lands after the response is computed)."""
        status, payload = self._get(
            "/audit", {"X-User": "alice", "X-Role": "admin"}
        )
        self.assertEqual(status, 200)
        actions = [e["action"] for e in payload["entries"]]
        self.assertEqual(
            actions[:4],
            ["asset_create", "finding_ingest", "control_assess", "search"],
        )

    def test_audit_endpoint_filters_by_actor(self):
        """AU-7: GET /audit?actor=alice returns only alice's entries:
        her two pinned entries are present, bob's and carol's are not.
        (The class shares one audit log, so alice may also carry
        audit_read entries recorded by sibling tests in this class --
        the filter's guarantee is about the actor, asserted exactly.)"""
        path = "/audit?" + urlencode({"actor": "alice"})
        status, payload = self._get(
            path, {"X-User": "dana", "X-Role": "auditor"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["entries"])
        self.assertTrue(
            all(e["actor"] == "alice" for e in payload["entries"])
        )
        actions = [e["action"] for e in payload["entries"]]
        self.assertIn("asset_create", actions)
        self.assertIn("control_assess", actions)
        self.assertNotIn("finding_ingest", actions)  # bob's
        self.assertNotIn("search", actions)  # carol's

    def test_audit_endpoint_filters_by_action_and_window(self):
        """AU-7: GET /audit composes action and since/until filters."""
        path = "/audit?" + urlencode(
            {"action": "search", "since": _TS[0], "until": _TS[3]}
        )
        status, payload = self._get(
            path, {"X-User": "alice", "X-Role": "admin"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["actor"], "carol")

    def test_audit_endpoint_denies_analyst(self):
        """AU-6: an analyst (no audit_read in this build's matrix)
        gets 403 on GET /audit, filtered or not."""
        status, payload = self._get(
            "/audit", {"X-User": "bob", "X-Role": "analyst"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
