"""Audit reduction & search tests (L3 High uplift, AU-7).

Traces to: UNION-SPEC.md Core function 12 (Audit log) as uplifted to
the FedRAMP High baseline -- AU-7 (audit reduction and report
generation): ``AuditLog.query(actor, action, target, since, until)``
filters the trail, and ``GET /audit`` exposes the same filters as
query parameters. Timestamps in the window tests are pinned by
rewriting stored ``ts`` values, so windows are deterministic (the
hash chain is not under test here; query reads stored fields only).
"""

import http.client
import json
import threading
import unittest

from cms_helpers import USERS
from cms.audit import AuditLog
from cms.service import make_server
from cms.store import CmsStore


def _log():
    log = AuditLog()
    log.record("alice", "site_create", "site-1")
    log.record("bob", "item_create", "ci-1")
    log.record("alice", "item_create", "ci-2")
    log.record("carol", "search", "hello")
    # Pin timestamps deterministically.
    stamps = [
        "2026-01-01T10:00:00+00:00",
        "2026-01-02T10:00:00+00:00",
        "2026-01-03T10:00:00+00:00",
        "2026-01-04T10:00:00+00:00",
    ]
    for entry, ts in zip(log._entries, stamps):
        entry["ts"] = ts
    return log


class TestAuditQuery(unittest.TestCase):
    """[L3] AU-7: AuditLog.query filters."""

    def test_no_filters_returns_all(self):
        """[L3] AU-7: query() with no filters returns every entry in order."""
        self.assertEqual(len(_log().query()), 4)

    def test_filter_by_actor(self):
        """[L3] AU-7: actor filter matches exactly."""
        result = _log().query(actor="alice")
        self.assertEqual([e["target"] for e in result], ["site-1", "ci-2"])

    def test_filter_by_action(self):
        """[L3] AU-7: action filter matches exactly."""
        result = _log().query(action="item_create")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(e["action"] == "item_create" for e in result))

    def test_filter_by_target(self):
        """[L3] AU-7: target filter matches exactly."""
        result = _log().query(target="ci-1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actor"], "bob")

    def test_filter_since_inclusive(self):
        """[L3] AU-7: since is an inclusive lower bound on ts."""
        result = _log().query(since="2026-01-03T10:00:00+00:00")
        self.assertEqual(len(result), 2)

    def test_filter_until_inclusive(self):
        """[L3] AU-7: until is an inclusive upper bound on ts."""
        result = _log().query(until="2026-01-02T10:00:00+00:00")
        self.assertEqual(len(result), 2)

    def test_filter_window(self):
        """[L3] AU-7: since+until together select the window."""
        result = _log().query(
            since="2026-01-02T00:00:00+00:00", until="2026-01-03T23:59:59+00:00"
        )
        self.assertEqual([e["target"] for e in result], ["ci-1", "ci-2"])

    def test_filters_combine(self):
        """[L3] AU-7: actor+action combine (AND)."""
        result = _log().query(actor="alice", action="item_create")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "ci-2")

    def test_no_match_returns_empty(self):
        """[L3] AU-7: a filter matching nothing returns an empty list."""
        self.assertEqual(_log().query(actor="mallory"), [])


class TestAuditQueryEndpoint(unittest.TestCase):
    """[L3] AU-7: GET /audit query parameters over HTTP."""

    ALICE = {"X-User": "alice", "X-Role": "admin"}
    DANA = {"X-User": "dana", "X-Role": "auditor"}
    BOB = {"X-User": "bob", "X-Role": "publisher"}

    def setUp(self):
        self.audit = AuditLog()
        self.store = CmsStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit, dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        from cms_helpers import ADMIN, PUBLISHER
        self.store.create_site(ADMIN, "Main", "main")
        self.store.create_site(PUBLISHER, "Two", "two")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _get(self, path, headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        parsed = json.loads(resp.read().decode("utf-8"))
        status = resp.status
        conn.close()
        return status, parsed

    def test_audit_no_params_returns_all(self):
        """[L3] AU-7: GET /audit without params returns the full trail."""
        status, parsed = self._get("/audit", self.ALICE)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(parsed["entries"]), 2)

    def test_audit_filter_actor(self):
        """[L3] AU-7: GET /audit?actor=alice returns only alice's entries."""
        status, parsed = self._get("/audit?actor=alice", self.ALICE)
        self.assertEqual(status, 200)
        self.assertTrue(parsed["entries"])
        self.assertTrue(all(e["actor"] == "alice" for e in parsed["entries"]))

    def test_audit_filter_action(self):
        """[L3] AU-7: GET /audit?action=site_create returns only site_create entries."""
        status, parsed = self._get("/audit?action=site_create", self.ALICE)
        self.assertEqual(status, 200)
        self.assertTrue(all(e["action"] == "site_create" for e in parsed["entries"]))

    def test_audit_filter_no_match(self):
        """[L3] AU-7: a non-matching filter returns an empty entries list."""
        status, parsed = self._get("/audit?actor=mallory", self.ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(parsed["entries"], [])

    def test_audit_query_auditor_allowed_publisher_denied(self):
        """[L3] AU-6/AC-5: auditor may query the trail; publisher (no audit_read) gets 403."""
        status, _ = self._get("/audit?actor=alice", self.DANA)
        self.assertEqual(status, 200)
        status, _ = self._get("/audit?actor=alice", self.BOB)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
