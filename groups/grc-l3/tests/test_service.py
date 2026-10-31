"""REST API service tests.

Traces to: Core function 8 (REST API — service layer over HTTP
exposing the substrate, JSON, standard error shape {error} with
400/401/403/404, denied attempts audited) plus functions 9 (RBAC) and
10 (Audit log) as enforced over HTTP; implementation contract for
``grc/service.py``: make_server(host, port, store, audit, users), auth
via X-User / X-Role headers matched against the registry.
"""

import http.client
import json
import threading
import unittest

from grc_helpers import USERS_REGISTRY
from grc.audit import AuditLog
from grc.service import make_server
from grc.store import GrcStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = GrcStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS_REGISTRY)
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        """One raw HTTP request; returns (status, text, parsed_json)."""
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
        text = raw.decode("utf-8", "replace")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        return status, text, parsed

    def create_system(self, ref="SYS-001", headers=None):
        """POST /systems as bob (member) and assert 201."""
        status, _, parsed = self.request(
            "POST", "/systems", headers=headers or BOB,
            body={"ref": ref, "name": "example portal"},
        )
        self.assertEqual(status, 201, "system creation failed")
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core 8 API access: health, header auth, and the error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core 8. GET /health (no auth) -> {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_headers_is_401(self):
        """Core 8 + Core 9 (IA-2). No X-User/X-Role headers -> 401
        with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/systems")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core 8 (IA-2). An unknown user -> 401."""
        status, _, parsed = self.request(
            "GET", "/systems", headers={"X-User": "mallory", "X-Role": "admin"}
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core 8 (IA-2). A role header that does not match the
        registry for that user -> 401."""
        status, _, parsed = self.request(
            "GET", "/systems", headers={"X-User": "alice", "X-Role": "viewer"}
        )
        self.assertEqual(status, 401)

    def test_unknown_route_is_404_json(self):
        """Core 8. An unknown route -> 404 with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_validation_error_is_400_json(self):
        """Core 8. A malformed creation body -> 400 with {error}."""
        status, _, parsed = self.request(
            "POST", "/systems", headers=BOB, body={"ref": "", "name": "x"}
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_missing_object_is_404_json(self):
        """Core 8. A well-formed request for a missing object -> 404
        with {error}."""
        status, _, parsed = self.request("GET", "/systems/NOPE", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


class TestRbacOverHttp(ServiceBase):
    """Core 8 + Core 9 RBAC over HTTP, and Core 10 denied auditing."""

    def test_viewer_posting_is_403(self):
        """Core 9 RBAC over HTTP. A viewer creating a system -> 403
        with {error}."""
        status, _, parsed = self.request(
            "POST", "/systems", headers=CAROL, body={"ref": "SYS-V", "name": "v"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_member_cannot_register_framework_403(self):
        """Core 9 RBAC over HTTP. A member registering a framework
        (admin-only manage_frameworks) -> 403."""
        status, _, _ = self.request(
            "POST", "/frameworks", headers=BOB,
            body={"id": "ORG-FW-1", "name": "One", "version": "1"},
        )
        self.assertEqual(status, 403)

    def test_member_cannot_review_evidence_403(self):
        """Core 9 RBAC over HTTP. A member reviewing evidence
        (admin-only review_evidence) -> 403, while the admin review
        succeeds."""
        self.create_system("SYS-REV")
        status, _, evidence = self.request(
            "POST", "/evidence", headers=BOB,
            body={"name": "e", "content": "text", "control_ids": [],
                  "system_refs": ["SYS-REV"]},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.request(
            "POST", "/evidence/%s/review" % evidence["id"], headers=BOB,
            body={"validation_status": "accepted"},
        )
        self.assertEqual(status, 403)
        status, _, reviewed = self.request(
            "POST", "/evidence/%s/review" % evidence["id"], headers=ALICE,
            body={"validation_status": "accepted"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["validation_status"], "accepted")

    def test_member_cannot_manage_authorizations_403(self):
        """Core 9 RBAC over HTTP. A member creating an authorization
        record (admin-only manage_authorizations) -> 403."""
        self.create_system("SYS-AUTHZ")
        status, _, _ = self.request(
            "POST", "/authorizations", headers=BOB,
            body={"system_ref": "SYS-AUTHZ", "framework_id": "NIST-SP-800-53"},
        )
        self.assertEqual(status, 403)

    def test_audit_read_is_admin_only(self):
        """Core 9 + Core 10 over HTTP. GET /audit requires audit_read:
        among the L2 roles, member and viewer -> 403; admin -> 200
        with {"entries": [...]}. (The [L3] auditor role also holds
        audit_read — see the additive test below.)"""
        status, _, _ = self.request("GET", "/audit", headers=BOB)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/audit", headers=CAROL)
        self.assertEqual(status, 403)
        status, _, parsed = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", parsed)

    def test_audit_read_auditor_allowed_records_denied(self):
        """Core 9 + Core 10 over HTTP [L3] (AC-5). The auditor role
        (dana) may read the audit trail — and nothing else: record
        reads (systems, posture) are 403 for her."""
        status, _, parsed = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIn("entries", parsed)
        status, _, _ = self.request("GET", "/systems", headers=DANA)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/posture", headers=DANA)
        self.assertEqual(status, 403)

    def test_denied_attempts_are_audited(self):
        """Core 10 over HTTP. Denied attempts (401 and 403) are
        recorded in the audit log with the action name suffixed
        ":denied"."""
        before = len(self.audit.entries())
        self.request("GET", "/systems")  # 401, no headers
        self.request(
            "POST", "/systems", headers=CAROL, body={"ref": "SYS-D", "name": "d"}
        )  # 403, viewer
        denied = [
            e for e in self.audit.entries()[before:]
            if e["action"].endswith(":denied")
        ]
        self.assertEqual(len(denied), 2)
        actions = {e["action"] for e in denied}
        self.assertIn("read:denied", actions)
        self.assertIn("manage_systems:denied", actions)


class TestFullFlow(ServiceBase):
    """Core 8: the whole substrate over HTTP, end to end."""

    def test_full_flow(self):
        """Core 8. Frameworks/controls -> system -> indicator ->
        recorded result -> evidence + verify -> finding + derived
        status -> transition -> assessment -> authorization ->
        posture, all over real HTTP with the documented status codes
        and wrappers."""
        # Seed catalog is readable.
        status, _, parsed = self.request("GET", "/frameworks", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(parsed["frameworks"][0]["id"], "NIST-SP-800-53")
        status, _, parsed = self.request("GET", "/controls", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(parsed["controls"]), 21)
        status, _, parsed = self.request(
            "GET", "/frameworks/NIST-SP-800-53/controls/AC-2", headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["family"], "AC")

        # Admin registers a framework and a control.
        status, _, parsed = self.request(
            "POST", "/frameworks", headers=ALICE,
            body={"id": "ORG-FW-1", "name": "House Set", "version": "1"},
        )
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "POST", "/frameworks/ORG-FW-1/controls", headers=ALICE,
            body={"id": "GV-1", "title": "Governance"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(parsed["family"], "GV")

        # System, indicator, recorded result.
        system = self.create_system("SYS-FLOW")
        status, _, indicator = self.request(
            "POST", "/indicators", headers=BOB,
            body={"id": "KSI-F", "name": "flow indicator", "control_ids": ["IA-2"]},
        )
        self.assertEqual(status, 201)
        status, _, result = self.request(
            "POST", "/indicators/KSI-F/results", headers=BOB,
            body={"system_ref": "SYS-FLOW", "status": "reported-pass",
                  "timestamp": "2026-10-01T00:00:00Z"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(result["recorded_by"], "bob")
        status, _, parsed = self.request("GET", "/results?system=SYS-FLOW", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(parsed["results"]), 1)

        # Evidence + verify-by-content.
        status, _, evidence = self.request(
            "POST", "/evidence", headers=BOB,
            body={"name": "worksheet", "content": "flow content",
                  "control_ids": ["AC-2"], "system_refs": ["SYS-FLOW"]},
        )
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "POST", "/evidence/%s/verify" % evidence["id"], headers=CAROL,
            body={"content": "flow content"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"verified": True})
        status, _, parsed = self.request(
            "POST", "/evidence/%s/verify" % evidence["id"], headers=CAROL,
            body={"content": "tampered"},
        )
        self.assertEqual(parsed, {"verified": False})

        # Finding, derived status at read time, transition.
        status, _, finding = self.request(
            "POST", "/findings", headers=BOB,
            body={"title": "flow finding", "system_ref": "SYS-FLOW",
                  "severity": "high", "source": "review",
                  "due_date": "2026-06-30"},
        )
        self.assertEqual(status, 201)
        self.assertNotIn("derived_status", finding)
        status, _, parsed = self.request(
            "GET", "/findings/%s?as_of=2026-12-31" % finding["id"], headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["derived_status"], "overdue")
        status, _, parsed = self.request(
            "POST", "/findings/%s/transition" % finding["id"], headers=BOB,
            body={"status": "in_progress"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["status"], "in_progress")
        # Illegal transition over HTTP -> 400.
        status, _, parsed = self.request(
            "POST", "/findings/%s/transition" % finding["id"], headers=BOB,
            body={"status": "closed"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

        # Assessment and authorization.
        status, _, assessment = self.request(
            "POST", "/assessments", headers=BOB,
            body={"system_ref": "SYS-FLOW", "framework_id": "NIST-SP-800-53",
                  "scope": "full", "assessor": "assessor-7",
                  "date": "2026-09-15", "result": "Satisfied (as reported)"},
        )
        self.assertEqual(status, 201)
        status, _, auth = self.request(
            "POST", "/authorizations", headers=ALICE,
            body={"system_ref": "SYS-FLOW", "framework_id": "NIST-SP-800-53"},
        )
        self.assertEqual(status, 201)
        status, _, auth = self.request(
            "POST", "/authorizations/%s/transition" % auth["id"], headers=ALICE,
            body={"status": "in_progress"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(auth["status"], "in_progress")

        # Posture: counts only.
        status, _, posture = self.request(
            "GET", "/posture?as_of=2026-12-31", headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(posture["findings"]["total"], 1)
        self.assertEqual(posture["findings"]["overdue"], 1)
        self.assertEqual(posture["systems"]["total"], 1)
        self.assertEqual(posture["evidence"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
