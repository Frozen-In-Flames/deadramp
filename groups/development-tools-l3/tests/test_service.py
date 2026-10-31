"""REST API service tests.

Traces to: the service layer for Group 17 -- ``devtools/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:developer, carol:viewer, dana:auditor},
errors JSON {error} 400/401/403/404, denied attempts audited.
"""

import http.client
import json
import threading
import unittest

from devtools_helpers import USERS
from devtools.audit import AuditLog
from devtools.service import make_server
from devtools.store import DevToolsStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "developer"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Core functions over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = DevToolsStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        """REST helper performing a real HTTP request."""
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

    def make_project(self, name="Widget Service"):
        """REST helper creating a project via POST /projects as admin."""
        status, _, parsed = self.request("POST", "/projects", headers=ALICE, body={"name": name})
        self.assertEqual(status, 201)
        return parsed


class TestHealthAuth(ServiceBase):
    """REST: health and header auth (IA-2 hooks)."""

    def test_health(self):
        """REST: GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_401(self):
        """REST (IA-2): unknown user or role mismatch (must match registry exactly) -> 401 JSON error."""
        for headers in ({"X-User": "mallory", "X-Role": "admin"},
                        {"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "carol", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/projects", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404(self):
        """REST: unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """REST: full devtools-records flow over HTTP."""

    def test_full_flow(self):
        """Core 1-8 over REST: project -> issue+lifecycle -> review -> build -> release -> artifact+verify -> env -> deployment -> search."""
        project = self.make_project()
        self.assertTrue(project["id"].startswith("prj-"))

        status, _, issue = self.request("POST", "/issues", headers=BOB, body={"project_id": project["id"], "title": "Widget bug"})
        self.assertEqual(status, 201)
        status, _, issue = self.request("POST", "/issues/%s/status" % issue["id"], headers=BOB, body={"status": "in_progress"})
        self.assertEqual(status, 200)
        self.assertEqual(issue["status"], "in_progress")

        status, _, rev = self.request("POST", "/reviews", headers=BOB, body={"project_id": project["id"], "title": "Widget review"})
        self.assertEqual(status, 201)
        status, _, bld = self.request("POST", "/builds", headers=BOB, body={"project_id": project["id"], "ref": "main"})
        self.assertEqual(status, 201)
        status, _, rel = self.request("POST", "/releases", headers=BOB, body={"project_id": project["id"], "version": "v1.0", "build_id": bld["id"]})
        self.assertEqual(status, 201)
        status, _, art = self.request("POST", "/artifacts", headers=BOB, body={"project_id": project["id"], "name": "widget-pkg", "content": "payload"})
        self.assertEqual(status, 201)
        self.assertNotIn("content", art)
        status, _, verdict = self.request("POST", "/artifacts/%s/verify" % art["id"], headers=CAROL, body={"content": "payload"})
        self.assertEqual(status, 200)
        self.assertEqual(verdict, {"match": True})
        status, _, verdict = self.request("POST", "/artifacts/%s/verify" % art["id"], headers=CAROL, body={"content": "tampered"})
        self.assertEqual(verdict, {"match": False})

        status, _, env = self.request("POST", "/environments", headers=BOB, body={"name": "prod", "tier": "production"})
        self.assertEqual(status, 201)
        status, _, dep = self.request("POST", "/deployments", headers=BOB, body={"environment_id": env["id"], "project_id": project["id"], "release_id": rel["id"], "artifact_id": art["id"]})
        self.assertEqual(status, 201)
        self.assertTrue(dep["id"].startswith("dep-"))

        status, _, found = self.request("GET", "/search?q=widget", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(found["projects"]), 1)
        self.assertEqual(len(found["issues"]), 1)


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """Core 9/10 (AC-3/AU-2): viewer POST /projects -> 403, and a ':denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"] if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request("POST", "/projects", headers=CAROL, body={"name": "Nope"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400_and_not_found_404(self):
        """REST (SI-10): bad project -> 400; unknown project -> 404; illegal lifecycle -> 400."""
        status, _, parsed = self.request("POST", "/projects", headers=ALICE, body={"name": ""})
        self.assertEqual(status, 400)
        status, _, _ = self.request("GET", "/projects/prj-999999", headers=ALICE)
        self.assertEqual(status, 404)
        project = self.make_project("GateProj %s" % self.id())
        status, _, issue = self.request("POST", "/issues", headers=ALICE, body={"project_id": project["id"], "title": "G"})
        self.assertEqual(status, 201)
        status, _, _ = self.request("POST", "/issues/%s/status" % issue["id"], headers=ALICE, body={"status": "resolved"})
        self.assertEqual(status, 400)

    def test_audit_access_admin_only(self):
        """REST / Core 10 [L3]: GET /audit -> 200 for admin and auditor (dana), 403 for developer and viewer (no audit_read, denied audited)."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)
        status, _, payload = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)

    def test_auditor_denied_operational_endpoint(self):
        """REST / Core 10 [L3] (AC-5): auditor (dana) -> 403 on an operational endpoint, GET /projects."""
        status, _, parsed = self.request("GET", "/projects", headers=DANA)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_search_empty_query_400(self):
        """REST / Core 8 (SI-10): GET /search without q -> 400."""
        status, _, _ = self.request("GET", "/search", headers=ALICE)
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
