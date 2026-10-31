"""Audit log reduction and search tests (L3 High uplift).

Traces to: Core function 14 (audit log) as uplifted to the FedRAMP
High baseline -- AU-7 (audit reduction and report generation):
``AuditLog.query(actor=, action=, target=, since=, until=)``
returns the entries matching ALL provided filters, and the
``GET /audit`` endpoint accepts the same filters as query
parameters. Timestamps are pinned explicitly so since/until
behaviour is deterministic.
"""

import http.client
import json
import threading
import unittest

from storage.audit import AuditLog
from storage.service import make_server
from storage.store import StorageStore

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer",
         "dana": "auditor"}


def _pinned_log():
    log = AuditLog()
    log.record("alice", "organization_create", "org-1",
               ts="2026-01-01T00:00:00+00:00")
    log.record("bob", "message_archive", "msg-1",
               ts="2026-01-02T00:00:00+00:00")
    log.record("alice", "disposition_record", "dsp-1",
               ts="2026-01-03T00:00:00+00:00")
    log.record("carol", "audit_read", "/audit",
               ts="2026-01-04T00:00:00+00:00")
    return log


class TestAuditQuery(unittest.TestCase):
    """AU-7: query() applies ALL provided filters, inclusively."""

    def setUp(self):
        self.log = _pinned_log()

    def test_query_no_filters_returns_all(self):
        """AU-7: query() with no filters returns every entry."""
        self.assertEqual(len(self.log.query()), 4)

    def test_query_actor(self):
        """AU-7: actor filter keeps only that actor's entries."""
        entries = self.log.query(actor="alice")
        self.assertEqual([e["action"] for e in entries],
                         ["organization_create", "disposition_record"])

    def test_query_action(self):
        """AU-7: action filter keeps only that action."""
        entries = self.log.query(action="message_archive")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["target"], "msg-1")

    def test_query_target(self):
        """AU-7: target filter keeps only entries on that target."""
        entries = self.log.query(target="/audit")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["actor"], "carol")

    def test_query_since_inclusive(self):
        """AU-7: since is an inclusive lower bound on ts."""
        entries = self.log.query(since="2026-01-02T00:00:00+00:00")
        self.assertEqual(len(entries), 3)

    def test_query_until_inclusive(self):
        """AU-7: until is an inclusive upper bound on ts."""
        entries = self.log.query(until="2026-01-02T00:00:00+00:00")
        self.assertEqual(len(entries), 2)

    def test_query_since_until_window(self):
        """AU-7: since+until together select the closed window."""
        entries = self.log.query(
            since="2026-01-02T00:00:00+00:00",
            until="2026-01-03T00:00:00+00:00")
        self.assertEqual([e["actor"] for e in entries], ["bob", "alice"])

    def test_query_combined_filters_require_all(self):
        """AU-7: filters conjoin -- actor matches but action does not
        yields nothing."""
        self.assertEqual(
            self.log.query(actor="alice", action="message_archive"), [])
        entries = self.log.query(actor="alice", action="organization_create")
        self.assertEqual(len(entries), 1)

    def test_query_returns_chain_fields(self):
        """AU-7 / AU-3: reduced entries are full entries, including
        the chain fields."""
        entry = self.log.query(action="message_archive")[0]
        self.assertIn("hash", entry)
        self.assertIn("prev_hash", entry)
        self.assertEqual(entry["seq"], 1)


class TestAuditQueryEndpoint(unittest.TestCase):
    """AU-7 over HTTP: GET /audit?<filters> reduces the trail; the
    auditor role may query (AC-5 slice: audit_read is its only
    permission, and reduction is part of review)."""

    @classmethod
    def setUpClass(cls):
        cls.audit = _pinned_log()
        cls.store = StorageStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, store=cls.store, audit=cls.audit, users=USERS)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path, user, role):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers={"X-User": user, "X-Role": role})
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def test_endpoint_actor_filter(self):
        """AU-7: ?actor=alice returns only alice's entries (the
        endpoint's own audit_read entry is recorded after)."""
        status, payload = self._get("/audit?actor=alice", "alice", "admin")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 2)
        self.assertEqual([e["action"] for e in payload["entries"]],
                         ["organization_create", "disposition_record"])

    def test_endpoint_window_filter(self):
        """AU-7: ?since=&until= narrows to the closed window."""
        status, payload = self._get(
            "/audit?since=2026-01-02T00:00:00%2B00:00"
            "&until=2026-01-03T00:00:00%2B00:00", "alice", "admin")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 2)

    def test_endpoint_no_filters_unchanged_shape(self):
        """AU-7: an unfiltered GET /audit keeps the L2 shape --
        {entries, count} with the whole trail (plus none of the
        endpoint's own entry, which is recorded after the read)."""
        status, payload = self._get("/audit", "alice", "admin")
        self.assertEqual(status, 200)
        self.assertEqual(set(payload.keys()), {"entries", "count"})
        self.assertEqual(payload["count"], len(payload["entries"]))
        self.assertGreaterEqual(payload["count"], 4)

    def test_endpoint_auditor_can_query(self):
        """AC-5 / AU-7: the auditor may reduce the trail too."""
        status, payload = self._get(
            "/audit?action=message_archive", "dana", "auditor")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 1)


if __name__ == "__main__":
    unittest.main()
