"""REST API tests against a live HTTP server.

Traces to: Core 10 (REST API + RBAC enforcement at the service
layer) -- 401 unknown user / role mismatch, 403 forbidden (denied
attempts audited with ':denied'), the full flow, audit_read
admin-only, 400/404 envelopes, ?now= derivation.
"""

import http.client
import json
import unittest

import crm_helpers as H
from crm.audit import AuditLog
from crm.service import USERS, make_server
from crm.store import CrmStore

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, user=None, role=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            parsed = {}
        return resp.status, parsed


class TestService(unittest.TestCase):
    """Core 10: the HTTP surface."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CrmStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        import threading
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health(self):
        """Core 10: GET /health needs no auth."""
        status, body = self.client.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_401_unknown_user_and_role_mismatch(self):
        """Core 10 (IA-2 hooks): unknown user and role mismatch -> 401."""
        status, _ = self.client.request("GET", "/accounts",
                                        user="mallory", role="admin")
        self.assertEqual(status, 401)
        status, _ = self.client.request("GET", "/accounts",
                                        user="alice", role="viewer")
        self.assertEqual(status, 401)
        status, _ = self.client.request("GET", "/accounts")
        self.assertEqual(status, 401)

    def test_403_viewer_write_and_denied_audited(self):
        """Core 10 (AC-3): viewer write -> 403, and the denied
        attempt is audited with ':denied'."""
        status, _ = self.client.request(
            "POST", "/accounts", body={"reference": "ACCT-X"},
            user="carol", role="viewer")
        self.assertEqual(status, 403)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "registry_write:denied"]
        self.assertTrue(denied)

    def test_403_operator_config_write(self):
        """Core 10 (AC-6): module create is admin-only -- operator
        gets 403."""
        status, _ = self.client.request(
            "POST", "/modules",
            body={"label": "m", "scope": "service", "settings_text": "x=1"},
            user="bob", role="operator")
        self.assertEqual(status, 403)

    def test_full_flow(self):
        """Core 1-9 over HTTP: account -> contact -> case ->
        assign/transition -> interaction -> guide -> finding ->
        module -> report/search -> audit."""
        c = self.client
        status, acct = c.request("POST", "/accounts",
                                 body={"reference": "ACCT-FLOW", "label": "Flow"},
                                 user="alice", role="admin")
        self.assertEqual(status, 201)
        status, contact = c.request(
            "POST", "/contacts",
            body={"account_id": acct["id"], "reference": "PERSON-FLOW"},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        status, case = c.request(
            "POST", "/cases",
            body={"case_type": "problem", "subject": "Flow outage",
                  "account_id": acct["id"], "contact_id": contact["id"],
                  "due_at": PAST},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        status, case = c.request("POST", "/cases/%s/assign" % case["id"],
                                 body={"assignee_ref": "STAFF-1"},
                                 user="bob", role="operator")
        self.assertEqual(status, 200)
        self.assertEqual(case["assignee_ref"], "STAFF-1")
        status, case = c.request("POST", "/cases/%s/transition" % case["id"],
                                 body={"to_status": "in_progress"},
                                 user="bob", role="operator")
        self.assertEqual(case["status"], "in_progress")
        status, got = c.request("GET", "/cases/%s?now=%s" % (case["id"], NOW),
                                user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertTrue(got["breached"])  # derived via ?now=
        status, rec = c.request(
            "POST", "/interactions",
            body={"channel": "guidance_session", "direction": "outbound",
                  "summary": "Tour run", "case_id": case["id"],
                  "guide_id": None},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        status, guide = c.request(
            "POST", "/guides",
            body={"title": "Flow tour", "kind": "walkthrough",
                  "target_ref": "surface:portal", "steps": ["Open"]},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        status, guide = c.request("PATCH", "/guides/%s" % guide["id"],
                                  body={"steps": ["Open", "Start"]},
                                  user="bob", role="operator")
        self.assertEqual(guide["version"], 2)
        status, finding = c.request(
            "POST", "/findings",
            body={"title": "Flow gap", "severity": "warning",
                  "detail": "verbatim text"},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        status, finding = c.request(
            "POST", "/findings/%s/transition" % finding["id"],
            body={"to_status": "acknowledged"}, user="bob", role="operator")
        self.assertEqual(finding["status"], "acknowledged")
        status, module = c.request(
            "POST", "/modules",
            body={"label": "flow", "scope": "service", "settings_text": "x=1"},
            user="alice", role="admin")
        self.assertEqual(status, 201)
        status, report = c.request("GET", "/report?now=%s" % NOW,
                                   user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertEqual(report["cases"]["breached"], 1)
        status, found = c.request("GET", "/search?q=Flow",
                                  user="bob", role="operator")
        self.assertEqual(status, 200)
        self.assertEqual(len(found["cases"]), 1)

    def test_audit_read_admin_only(self):
        """Core 9/10 (AU-6): /audit is admin-only."""
        status, _ = self.client.request("GET", "/audit",
                                        user="bob", role="operator")
        self.assertEqual(status, 403)
        status, body = self.client.request("GET", "/audit",
                                           user="alice", role="admin")
        self.assertEqual(status, 200)
        self.assertIn("entries", body)

    def test_400_and_404_envelopes(self):
        """Core 10 (SI-10): validation -> 400 {error}; unknown object
        and unknown route -> 404 {error}; no stack traces."""
        status, body = self.client.request(
            "POST", "/cases", body={"case_type": "ticket", "subject": "x"},
            user="bob", role="operator")
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        status, body = self.client.request("GET", "/cases/case-99",
                                           user="alice", role="admin")
        self.assertEqual(status, 404)
        self.assertIn("error", body)
        status, body = self.client.request("GET", "/nope",
                                           user="alice", role="admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
