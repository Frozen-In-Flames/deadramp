"""REST API service tests.

Traces to: the service layer for Group 21 -- ``hr/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:hr_specialist, carol:employee,
dana:auditor}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin+auditor.
Covers Core functions 1-10 over HTTP, including derived lifecycle
status in lifecycle-case views.
"""

import http.client
import json
import threading
import unittest

from hr_helpers import USERS
from hr.audit import AuditLog
from hr.service import make_server
from hr.store import HrStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "hr_specialist"}
CAROL = {"X-User": "carol", "X-Role": "employee"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Core 1-10 over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = HrStore(audit=cls.audit)
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

    def make_position(self, title="Program Analyst"):
        """REST helper creating a position via POST /positions as admin."""
        status, _, parsed = self.request(
            "POST", "/positions", headers=ALICE,
            body={"title": title, "series": "0343", "grade": "13"},
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
                        {"X-User": "alice", "X-Role": "employee"},
                        {"X-User": "carol", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/positions", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """REST: unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """REST: full human-resources flow over HTTP (Core 1-10)."""

    def test_full_flow(self):
        """Core 1-10 over REST: person -> position -> vacancy -> application -> evaluation+entry -> lifecycle (derived in_progress, then complete) -> performance -> benefits -> case -> report."""
        status, _, person = self.request(
            "POST", "/persons", headers=ALICE, body={"person_ref": "carol", "kind": "employee"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(person["id"].startswith("per-"))
        self.assertEqual(
            set(person), {"id", "person_ref", "kind", "status", "created_by", "created_utc"}
        )

        position = self.make_position()
        self.assertTrue(position["id"].startswith("pos-"))

        status, _, vacancy = self.request(
            "POST", "/vacancies", headers=BOB,
            body={"position_id": position["id"], "title": "Analyst Opening",
                  "opens_on": "2026-07-01", "closes_on": "2026-07-31"},
        )
        self.assertEqual(status, 201)
        status, _, vacancy = self.request(
            "POST", "/vacancies/%s/status" % vacancy["id"], headers=BOB, body={"status": "posted"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(vacancy["status"], "posted")

        status, _, app = self.request(
            "POST", "/applications", headers=BOB,
            body={"person_ref": "carol", "vacancy_id": vacancy["id"]},
        )
        # NOTE: vacancy variable was rebound to the status response above,
        # which carries the same id.
        self.assertEqual(status, 201)
        status, _, app = self.request(
            "POST", "/applications/%s/stage" % app["id"], headers=BOB, body={"stage": "screened"}
        )
        self.assertEqual(app["stage"], "screened")

        status, _, evl = self.request(
            "POST", "/evaluations", headers=BOB,
            body={"application_id": app["id"], "kind": "panel", "title": "Panel Review"},
        )
        self.assertEqual(status, 201)
        status, _, evl = self.request(
            "POST", "/evaluations/%s/entries" % evl["id"], headers=BOB,
            body={"rater_ref": "rater-1", "rating": 4, "comment": "Solid"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(evl["entries"], [{"rater_ref": "rater-1", "rating": 4, "comment": "Solid"}])
        self.assertNotIn("score", evl)

        status, _, lifecycle = self.request(
            "POST", "/lifecycle-cases", headers=BOB,
            body={"person_ref": "carol", "kind": "onboarding", "task_titles": ["Badge", "Laptop"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(lifecycle["status"], "not_started")
        status, _, lifecycle = self.request(
            "POST", "/lifecycle-cases/%s/tasks/t-1/state" % lifecycle["id"],
            headers=BOB, body={"state": "done"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(lifecycle["status"], "in_progress")
        status, _, lifecycle = self.request(
            "POST", "/lifecycle-cases/%s/tasks/t-2/state" % lifecycle["id"],
            headers=BOB, body={"state": "waived"},
        )
        self.assertEqual(lifecycle["status"], "complete")
        self.assertTrue(lifecycle["complete"])

        status, _, review = self.request(
            "POST", "/performance-reviews", headers=BOB,
            body={"person_ref": "carol", "cycle": "2026-annual",
                  "period_start": "2026-01-01", "period_end": "2026-12-31"},
        )
        self.assertEqual(status, 201)
        status, _, review = self.request(
            "POST", "/performance-reviews/%s/state" % review["id"], headers=BOB,
            body={"state": "completed", "outcome": "meets"},
        )
        self.assertEqual(review["outcome"], "meets")

        status, _, benefits = self.request(
            "POST", "/benefits", headers=BOB,
            body={"person_ref": "carol", "kind": "benefit_enrollment", "plan_ref": "plan-a"},
        )
        self.assertEqual(status, 201)
        status, _, benefits = self.request(
            "POST", "/benefits/%s/state" % benefits["id"], headers=BOB, body={"state": "active"}
        )
        self.assertEqual(benefits["state"], "active")

        status, _, case = self.request(
            "POST", "/cases", headers=BOB,
            body={"person_ref": "carol", "kind": "award", "title": "Service Award"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(case["id"].startswith("cas-"))

        status, _, report = self.request("GET", "/report", headers=DANA)
        self.assertEqual(status, 200)
        self.assertEqual(report["lifecycle_cases_by_status"]["complete"], 1)
        self.assertEqual(report["applications"], 1)
        self.assertEqual(report["persons"], 1)

        # The employee reads her own records over HTTP.
        status, _, own = self.request("GET", "/applications/%s" % app["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(own["person_ref"], "carol")


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404, employee scope, and denied-audit behaviour."""

    def test_employee_write_is_403_and_denied_audited(self):
        """Core 11/12 (AC-3/AU-2): employee POST /positions -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/positions", headers=CAROL, body={"title": "Nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_employee_scope_over_http(self):
        """Core 11: carol reading erin's application over HTTP -> 403; her list shows only her own."""
        # Seed erin + an application for her via the store-level fixture path over HTTP.
        status, _, _ = self.request(
            "POST", "/persons", headers=ALICE, body={"person_ref": "erin", "kind": "applicant"}
        )
        self.assertEqual(status, 201)
        position = self.make_position("Scope Position %s" % self.id())
        status, _, vacancy = self.request(
            "POST", "/vacancies", headers=BOB,
            body={"position_id": position["id"], "title": "Scope Opening"},
        )
        self.assertEqual(status, 201)
        status, _, other = self.request(
            "POST", "/applications", headers=BOB,
            body={"person_ref": "erin", "vacancy_id": vacancy["id"]},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.request("GET", "/applications/%s" % other["id"], headers=CAROL)
        self.assertEqual(status, 403)
        status, _, listing = self.request("GET", "/applications", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertTrue(all(a["person_ref"] == "carol" for a in listing["applications"]))
        # Org-level records are NOT person-scoped: carol may read the vacancy.
        status, _, _ = self.request("GET", "/vacancies/%s" % vacancy["id"], headers=CAROL)
        self.assertEqual(status, 200)

    def test_validation_400_and_not_found_404(self):
        """REST (SI-10): bad position -> 400; unknown position -> 404."""
        status, _, parsed = self.request("POST", "/positions", headers=ALICE, body={"title": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/positions/pos-999999", headers=ALICE)
        self.assertEqual(status, 404)

    def test_audit_access(self):
        """REST / Core 12 (AU-6): GET /audit -> 200 for admin and auditor, 403 for hr_specialist and employee."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        for headers in (ALICE, DANA):
            status, _, payload = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("entries", payload)

    def test_report_employee_403(self):
        """Core 10/11: GET /report -> 403 for employee (no report_read)."""
        status, _, _ = self.request("GET", "/report", headers=CAROL)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
