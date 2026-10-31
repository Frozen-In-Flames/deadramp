"""[L3] Audit reduction & search (Core function 10; AU-7).

``AuditLog.query`` filters by actor / action / target / since / until;
``GET /audit`` exposes the same filters as query parameters. The
auditor role can use the reduced search (it holds audit_read).
"""

import http.client
import json
import threading
import unittest

from custsvc.audit import AuditLog
from custsvc.service import USERS, make_server
from custsvc.store import CustsvcStore

ADMIN_H = {"X-User": "alice", "X-Role": "admin"}
AGENT_H = {"X-User": "bob", "X-Role": "agent"}
AUDITOR_H = {"X-User": "dana", "X-Role": "auditor"}


def _seeded_log():
    log = AuditLog()
    log.record("alice", "requester_create", "req-1")
    log.record("bob", "case_create", "case-1")
    log.record("bob", "case_status", "case-1")
    log.record("alice", "rule_create", "rule-1")
    return log


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.log = _seeded_log()

    def test_no_filters_returns_all(self):
        self.assertEqual(len(self.log.query()), 4)

    def test_filter_by_actor(self):
        rows = self.log.query(actor="bob")
        self.assertEqual([r["action"] for r in rows],
                         ["case_create", "case_status"])

    def test_filter_by_action(self):
        rows = self.log.query(action="case_create")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor"], "bob")

    def test_filter_by_target(self):
        rows = self.log.query(target="case-1")
        self.assertEqual(len(rows), 2)

    def test_combined_filters(self):
        rows = self.log.query(actor="bob", target="case-1",
                              action="case_status")
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.log.query(actor="carol"), [])

    def test_since_until_window(self):
        entries = self.log.entries()
        mid = entries[1]["ts"]
        last = entries[-1]["ts"]
        rows = self.log.query(since=mid, until=last)
        self.assertGreaterEqual(len(rows), 2)
        self.assertTrue(all(mid <= r["ts"] <= last for r in rows))
        future = "2999-01-01T00:00:00+00:00"
        self.assertEqual(self.log.query(since=future), [])


class QueryEndpointFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store = CustsvcStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        # Seed through the API: one requester, one responder, one case.
        self.call("POST", "/requesters", headers=ADMIN_H,
                  body={"ref": "citizen-001", "label": "Citizen One"})
        self.call("POST", "/responders", headers=ADMIN_H,
                  body={"label": "Responder One", "team": "tier-1"})
        self.call("POST", "/cases", headers=AGENT_H, body={
            "title": "Cannot access portal", "body": "Login fails.",
            "requester_ref": "citizen-001"})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        hdrs = dict(headers or {})
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestQueryEndpoint(QueryEndpointFixture):
    def test_unfiltered_returns_all(self):
        status, body = self.call("GET", "/audit", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["entries"]), 3)

    def test_filter_actor_param(self):
        status, body = self.call("GET", "/audit?actor=bob", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertTrue(body["entries"])
        self.assertTrue(all(e["actor"] == "bob" for e in body["entries"]))

    def test_filter_action_param(self):
        status, body = self.call("GET", "/audit?action=case_create",
                                 headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertEqual(len(body["entries"]), 1)

    def test_filter_since_param(self):
        status, body = self.call(
            "GET", "/audit?since=2999-01-01T00:00:00+00:00", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertEqual(body["entries"], [])

    def test_auditor_can_use_reduced_search(self):
        status, body = self.call("GET", "/audit?action=case_create",
                                 headers=AUDITOR_H)
        self.assertEqual(status, 200)
        self.assertEqual(len(body["entries"]), 1)

    def test_agent_cannot_query(self):
        status, _ = self.call("GET", "/audit?actor=bob", headers=AGENT_H)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
