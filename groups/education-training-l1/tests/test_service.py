"""REST API service tests.

Traces to: the service layer for Group 30 -- ``learn/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:instructor, carol:learner,
dana:auditor}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin+auditor.
Covers Core functions 1-9 over HTTP, including derived compliance
status via the ``as_of`` query parameter.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from learn_helpers import USERS
from learn.audit import AuditLog
from learn.service import make_server
from learn.store import LearnStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "instructor"}
CAROL = {"X-User": "carol", "X-Role": "learner"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Core 1-9 over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = LearnStore(audit=cls.audit)
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

    def make_course(self, title="Safety Basics"):
        """REST helper creating a course via POST /courses as admin."""
        status, _, parsed = self.request(
            "POST", "/courses", headers=ALICE, body={"title": title, "code": "SAFE-101"}
        )
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
        """REST (IA-2): unknown user or role mismatch -> 401 JSON error."""
        for headers in ({"X-User": "mallory", "X-Role": "admin"},
                        {"X-User": "alice", "X-Role": "learner"},
                        {"X-User": "carol", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/courses", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """REST: unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """REST: full education-records flow over HTTP (Core 1-8)."""

    def test_full_flow(self):
        """Core 1-8 over REST: course -> enroll -> progress -> session -> assessment+response -> credential -> compliance (derived overdue, then completed) -> report."""
        course = self.make_course()
        self.assertTrue(course["id"].startswith("crs-"))

        status, _, enr = self.request(
            "POST", "/enrollments", headers=BOB,
            body={"learner_id": "carol", "course_id": course["id"]},
        )
        self.assertEqual(status, 201)

        status, _, session = self.request(
            "POST", "/sessions", headers=BOB,
            body={"title": "Session 1", "course_id": course["id"],
                  "starts_at": "2026-07-01T09:00:00Z", "kind": "assessment",
                  "learner_ids": ["carol"]},
        )
        self.assertEqual(status, 201)

        status, _, asm = self.request(
            "POST", "/assessments", headers=BOB,
            body={"title": "Safety Quiz", "learner_id": "carol",
                  "course_id": course["id"], "session_id": session["id"]},
        )
        self.assertEqual(status, 201)
        status, _, asm = self.request(
            "POST", "/assessments/%s/responses" % asm["id"], headers=BOB,
            body={"item_id": "q1", "response": "b"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(asm["responses"], [{"item_id": "q1", "response": "b"}])
        self.assertNotIn("score", asm)

        status, _, cred = self.request(
            "POST", "/credentials", headers=ALICE,
            body={"learner_id": "carol", "name": "Safety Certification"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(cred["id"].startswith("cred-"))

        status, _, cmp_rec = self.request(
            "POST", "/compliance", headers=ALICE,
            body={"learner_id": "carol", "course_id": course["id"], "due_date": "2026-06-01"},
        )
        self.assertEqual(status, 201)
        self.assertNotIn("status", cmp_rec)

        query = urllib.parse.urlencode({"as_of": "2026-06-15"})
        status, _, derived = self.request(
            "GET", "/compliance/%s/status?%s" % (cmp_rec["id"], query), headers=DANA
        )
        self.assertEqual(status, 200)
        self.assertEqual(derived["status"], "overdue")

        status, _, prog = self.request(
            "POST", "/progress", headers=BOB,
            body={"learner_id": "carol", "course_id": course["id"], "status": "completed"},
        )
        self.assertEqual(status, 201)
        status, _, derived = self.request(
            "GET", "/compliance/%s/status?%s" % (cmp_rec["id"], query), headers=DANA
        )
        self.assertEqual(derived["status"], "completed")

        status, _, report = self.request("GET", "/report?%s" % query, headers=DANA)
        self.assertEqual(status, 200)
        self.assertEqual(report["compliance_by_status"]["completed"], 1)
        self.assertEqual(report["enrollments"], 1)

        # The learner reads her own records over HTTP.
        status, _, own = self.request("GET", "/enrollments/%s" % enr["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(own["learner_id"], "carol")


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404, learner scope, and denied-audit behaviour."""

    def test_learner_write_is_403_and_denied_audited(self):
        """Core 9/10 (AC-3/AU-2): learner POST /courses -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/courses", headers=CAROL, body={"title": "Nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_learner_scope_over_http(self):
        """Core 9: carol reading erin's enrollment over HTTP -> 403; her list shows only her own."""
        course = self.make_course("Scope Course %s" % self.id())
        status, _, other = self.request(
            "POST", "/enrollments", headers=BOB,
            body={"learner_id": "erin", "course_id": course["id"]},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.request("GET", "/enrollments/%s" % other["id"], headers=CAROL)
        self.assertEqual(status, 403)
        status, _, listing = self.request("GET", "/enrollments", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertTrue(all(e["learner_id"] == "carol" for e in listing["enrollments"]))

    def test_validation_400_and_not_found_404(self):
        """REST (SI-10): bad course -> 400; unknown course -> 404."""
        status, _, parsed = self.request("POST", "/courses", headers=ALICE, body={"title": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/courses/crs-999999", headers=ALICE)
        self.assertEqual(status, 404)

    def test_audit_access(self):
        """REST / Core 10 (AU-6): GET /audit -> 200 for admin and auditor, 403 for instructor and learner."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        for headers in (ALICE, DANA):
            status, _, payload = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("entries", payload)

    def test_report_learner_403(self):
        """Core 8/9: GET /report -> 403 for learner (no report_read)."""
        status, _, _ = self.request("GET", "/report", headers=CAROL)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
