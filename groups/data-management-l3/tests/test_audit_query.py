"""Audit reduction & search tests (L3 High uplift, AU-7).

Traces to: UNION-SPEC Core function 12 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-7 (audit reduction and report generation):
``AuditLog.query(actor, action, target, since, until)`` returns the
entries matching all given filters, and ``GET /audit`` passes the
``actor`` / ``action`` / ``target`` / ``since`` / ``until`` query
parameters through to it. With no parameters the unfiltered trail is
returned, unchanged from the L2 behavior.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from datamgmt_helpers import USERS, make_store
from datamgmt.audit import AuditLog
from datamgmt.service import make_server
from datamgmt.store import DataMgmtStore


def _populated_log():
    """A log with a known mix of actors, actions, and targets."""
    log = AuditLog()
    log.record("alice", "dataset_create", "ds-1")
    log.record("bob", "dataset_create", "ds-2")
    log.record("alice", "search", "claims")
    log.record("carol", "access_request", "ar-1")
    log.record("bob", "access_decide", "ar-1")
    return log


class TestAuditQuery(unittest.TestCase):
    """AU-7: AuditLog.query filters."""

    def test_query_no_filters_returns_all(self):
        """AU-7: query() with no filters returns every entry, in order."""
        log = _populated_log()
        self.assertEqual(log.query(), log.entries())
        self.assertEqual(len(log.query()), 5)

    def test_query_by_actor(self):
        """AU-7: the actor filter returns only that actor's entries."""
        result = _populated_log().query(actor="alice")
        self.assertEqual([e["action"] for e in result], ["dataset_create", "search"])
        self.assertTrue(all(e["actor"] == "alice" for e in result))

    def test_query_by_action(self):
        """AU-7: the action filter returns only that action's entries."""
        result = _populated_log().query(action="dataset_create")
        self.assertEqual([e["target"] for e in result], ["ds-1", "ds-2"])

    def test_query_by_target(self):
        """AU-7: the target filter returns only that target's entries."""
        result = _populated_log().query(target="ar-1")
        self.assertEqual(
            [e["action"] for e in result], ["access_request", "access_decide"]
        )

    def test_query_combined_filters(self):
        """AU-7: filters combine (all must match)."""
        result = _populated_log().query(actor="bob", action="dataset_create")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "ds-2")
        self.assertEqual(_populated_log().query(actor="alice", action="export_create"), [])

    def test_query_since_until_window(self):
        """AU-7: since/until bound the ts window inclusively, compared
        as ISO strings against each entry's ts."""
        log = _populated_log()
        entries = log.entries()
        first_ts, last_ts = entries[0]["ts"], entries[-1]["ts"]
        self.assertEqual(len(log.query(since=first_ts)), 5)
        self.assertEqual(len(log.query(until=last_ts)), 5)
        # A window pinned to the middle entry's ts includes exactly it.
        mid_ts = entries[2]["ts"]
        windowed = log.query(since=mid_ts, until=mid_ts)
        self.assertEqual([e["action"] for e in windowed], ["search"])
        # A window before everything / after everything is empty.
        self.assertEqual(log.query(until="1970-01-01T00:00:00+00:00"), [])
        self.assertEqual(log.query(since="2999-01-01T00:00:00+00:00"), [])

    def test_query_returns_copies(self):
        """AU-7 / AU-9: mutating a query result does not mutate the log."""
        log = _populated_log()
        log.query(actor="alice")[0]["actor"] = "mallory"
        self.assertEqual(log.entries()[0]["actor"], "alice")
        self.assertEqual(log.verify_chain(), (True, None))


class TestAuditQueryEndpoint(unittest.TestCase):
    """AU-7 over HTTP: GET /audit filter pass-through."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = DataMgmtStore(audit=cls.audit)
        # Seed the trail (bob's dataset_create + source_register) so
        # every filter test is self-sufficient regardless of order.
        make_store(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS)
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

    def _get_audit(self, query="", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(
            "GET",
            "/audit" + query,
            headers=headers or {"X-User": "alice", "X-Role": "admin"},
        )
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def test_audit_filter_actor(self):
        """AU-7: GET /audit?actor=bob returns only bob's entries."""
        status, payload = self._get_audit("?actor=bob")
        self.assertEqual(status, 200)
        self.assertTrue(payload["entries"])
        self.assertTrue(all(e["actor"] == "bob" for e in payload["entries"]))

    def test_audit_filter_action(self):
        """AU-7: GET /audit?action=dataset_create returns only creates."""
        status, payload = self._get_audit("?action=dataset_create")
        self.assertEqual(status, 200)
        self.assertTrue(payload["entries"])
        self.assertTrue(
            all(e["action"] == "dataset_create" for e in payload["entries"])
        )

    def test_audit_unfiltered_unchanged(self):
        """AU-7: GET /audit with no parameters returns the full trail,
        exactly as the L2 endpoint did."""
        before = len(self.audit.entries())
        status, payload = self._get_audit()
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), before)

    def test_audit_filter_requires_audit_read(self):
        """AU-6: the filtered read is still audit_read-gated (viewer 403)."""
        status, payload = self._get_audit(
            "?actor=bob", headers={"X-User": "carol", "X-Role": "viewer"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", payload)

    def test_audit_filter_since_until_over_http(self):
        """AU-7: since/until pass through over HTTP (a future window
        is empty; the URL-encoded ts of the first entry bounds all)."""
        first_ts = self.audit.entries()[0]["ts"]
        query = "?since=" + urllib.parse.quote(first_ts, safe="")
        status, payload = self._get_audit(query)
        self.assertEqual(status, 200)
        self.assertTrue(payload["entries"])
        status, payload = self._get_audit("?since=2999-01-01T00:00:00%2B00:00")
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])


if __name__ == "__main__":
    unittest.main()
