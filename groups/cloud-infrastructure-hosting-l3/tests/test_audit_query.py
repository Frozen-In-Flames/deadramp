"""[L3] AU-7: audit review, analysis & reduction.

AuditLog.query filters by actor, action, target and an inclusive
ISO timestamp window (since / until), conjunctively. GET /audit
passes the same filters as query parameters and adds a count; an
unfiltered GET /audit keeps the founding shape exactly.
"""

import http.client
import json
import threading
import unittest

import cloudinfra_helpers as H
from cloudinfra.audit import AuditLog
from cloudinfra.service import USERS, make_server
from cloudinfra.store import CloudInfraStore


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


def _pinned_log():
    log = AuditLog()
    log.record("alice", "organization_create", "org-1",
               ts="2026-01-01T10:00:00+00:00")
    log.record("bob", "tenancy_create", "ten-1",
               ts="2026-01-02T10:00:00+00:00")
    log.record("alice", "tenancy_create", "ten-2",
               ts="2026-01-03T10:00:00+00:00")
    log.record("alice", "deployment_status", "dep-1",
               ts="2026-01-04T10:00:00+00:00")
    return log


class TestAuditQuery(unittest.TestCase):
    def setUp(self):
        self.log = _pinned_log()

    def test_query_unfiltered_returns_all(self):
        self.assertEqual(len(self.log.query()), 4)

    def test_query_by_actor(self):
        got = self.log.query(actor="alice")
        self.assertEqual([e["action"] for e in got],
                         ["organization_create", "tenancy_create",
                          "deployment_status"])

    def test_query_by_action_and_target(self):
        got = self.log.query(action="tenancy_create")
        self.assertEqual([e["target"] for e in got], ["ten-1", "ten-2"])
        got = self.log.query(target="dep-1")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["actor"], "alice")

    def test_query_window_is_inclusive(self):
        got = self.log.query(since="2026-01-02T10:00:00+00:00",
                             until="2026-01-03T10:00:00+00:00")
        self.assertEqual([e["target"] for e in got], ["ten-1", "ten-2"])

    def test_query_filters_are_conjunctive(self):
        got = self.log.query(actor="alice", action="tenancy_create",
                             since="2026-01-03T00:00:00+00:00")
        self.assertEqual([e["target"] for e in got], ["ten-2"])
        self.assertEqual(
            self.log.query(actor="bob", action="deployment_status"), [])


class TestAuditQueryEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CloudInfraStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        call(cls.port, "POST", "/organizations", user="alice",
             role="admin", body={"org_ref": "org-query", "label": "Q"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_filtered_audit_read(self):
        status, body = call(
            self.port, "GET", "/audit?action=organization_create",
            user="alice", role="admin")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["entries"]), 1)
        self.assertEqual(body["entries"][0]["action"],
                         "organization_create")

    def test_filtered_audit_read_for_auditor(self):
        status, body = call(
            self.port, "GET", "/audit?actor=alice", user="dana",
            role="auditor")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["count"], 1)
        self.assertTrue(all(e["actor"] == "alice"
                            for e in body["entries"]))

    def test_unfiltered_audit_read_keeps_founding_shape(self):
        status, body = call(self.port, "GET", "/audit",
                            user="alice", role="admin")
        self.assertEqual(status, 200)
        self.assertIn("entries", body)
        self.assertNotIn("count", body)


if __name__ == "__main__":
    unittest.main()
