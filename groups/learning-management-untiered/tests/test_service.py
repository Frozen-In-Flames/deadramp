"""REST API service tests.

Traces to: the service layer for Group 48 -- ``lms/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:instructor, carol:learner,
dana:auditor}, errors JSON {error} 400/401/403/404, creates 201,
PermissionDenied -> 403 with a '<action>:denied' audit entry,
audit_read admin+auditor. Covers Core functions 1-11 over HTTP,
including derived compliance status via the ``as_of`` query parameter
and the statement no-score pin.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from lms_helpers import USERS
from lms.audit import AuditLog
from lms.service import make_server
from lms.store import LmsStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "instructor"}
CAROL = {"X-User": "carol", "X-Role": "learner"}
DANA = {"X-User": "dana", "X-Role": "auditor"}

STATEMENT_KEYS = {
    "id", "learner_ref", "verb", "object_ref",
    "context", "result_text", "recorded_by", "recorded_utc",
}


class ServiceBase(unittest.TestCase):
    """Core 1-11 over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = LmsStore(audit=cls.audit)
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

    def make_learner(self, ref="carol", label="Carol Learner"):
        """REST helper creating a learner via POST /learners as admin."""
        status, _, parsed = self.request(
            "POST", "/learners", headers=ALICE, body={"ref": ref, "label": label}
        )
        self.assertEqual(status, 201)
        return parsed

    def make_course(self, title="Safety Basics"):
        """REST helper creating a course via POST /courses as admin."""
        status, _, parsed = self.request(
            "POST", "/courses", headers=ALICE, body={"title": title, "code": "SAFE-101"}
        )
        self.assertEqual(status, 201)
        return parsed


class TestHealthAuth(ServiceBase):
    """REST: health and header auth."""

    def test_health(self):
        """REST: GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_401(self):
        """REST: unknown user or role mismatch -> 401 JSON error."""
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
    """REST: full learning-management flow over HTTP (Core 1-11)."""

    def test_full_flow(self):
        """Core 1-11 over REST: learner -> course -> content item -> lesson plan -> event (derived seats) -> register -> authorization create+decide by a different actor -> IDP -> competency + learner competency -> progress -> statement (no score) -> compliance derived overdue then completed -> report -> search."""
        learner = self.make_learner()
        self.assertTrue(learner["id"].startswith("lrn-"))

        course = self.make_course()
        self.assertTrue(course["id"].startswith("crs-"))

        status, _, item = self.request(
            "POST", "/content-items", headers=ALICE,
            body={"title": "Safety Video", "standard": "mp4",
                  "course_id": course["id"]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(item["id"].startswith("cnt-"))

        status, _, plan = self.request(
            "POST", "/lesson-plans", headers=ALICE,
            body={"title": "Week 1 Plan", "course_id": course["id"],
                  "item_refs": [item["id"]]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(plan["id"].startswith("les-"))

        status, _, event = self.request(
            "POST", "/events", headers=BOB,
            body={"title": "Safety Briefing", "starts_at": "2026-07-01T09:00:00Z",
                  "course_id": course["id"], "capacity": 1},
        )
        self.assertEqual(status, 201)
        self.assertTrue(event["id"].startswith("evt-"))
        status, _, view = self.request("GET", "/events/%s" % event["id"], headers=ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(view["seats_open"], 1)
        self.assertEqual(view["seats_taken"], 0)

        status, _, reg = self.request(
            "POST", "/registrations", headers=BOB,
            body={"event_id": event["id"], "learner_ref": "carol"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(reg["id"].startswith("reg-"))
        self.assertEqual(reg["state"], "registered")
        status, _, view = self.request("GET", "/events/%s" % event["id"], headers=ALICE)
        self.assertEqual(view["seats_open"], 0)

        status, _, auth = self.request(
            "POST", "/authorizations", headers=BOB,
            body={"learner_ref": "carol", "subject": "SF-182 Safety Training",
                  "course_id": course["id"]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(auth["id"].startswith("aut-"))
        self.assertEqual(auth["state"], "requested")
        # Decided by a different actor than the creator (bob created).
        status, _, decided = self.request(
            "POST", "/authorizations/%s/decide" % auth["id"], headers=ALICE,
            body={"decision": "approved"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(decided["state"], "approved")

        status, _, idp = self.request(
            "POST", "/development-plans", headers=BOB,
            body={"learner_ref": "carol", "goal": "Become safety lead",
                  "activities": [{"activity": "Take Safety Basics",
                                  "course_id": course["id"]}]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(idp["id"].startswith("idp-"))

        status, _, comp = self.request(
            "POST", "/competencies", headers=BOB,
            body={"name": "Safety Awareness"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(comp["id"].startswith("cpt-"))
        status, _, lcr = self.request(
            "POST", "/learner-competencies", headers=BOB,
            body={"learner_ref": "carol", "competency_id": comp["id"],
                  "level": "Level 3 (vendor scale)"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(lcr["id"].startswith("lcr-"))
        self.assertEqual(lcr["level"], "Level 3 (vendor scale)")

        status, _, prog = self.request(
            "POST", "/progress", headers=BOB,
            body={"learner_ref": "carol", "course_id": course["id"],
                  "status": "in_progress"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(prog["id"].startswith("prg-"))

        status, _, stmt = self.request(
            "POST", "/statements", headers=BOB,
            body={"learner_ref": "carol", "verb": "completed",
                  "object_ref": course["id"],
                  "result_text": "score: 88/100 — pass"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(stmt["id"].startswith("stm-"))
        self.assertEqual(set(stmt), STATEMENT_KEYS)
        self.assertEqual(stmt["result_text"], "score: 88/100 — pass")
        self.assertNotIn("score", stmt)

        status, _, cmp_rec = self.request(
            "POST", "/compliance", headers=ALICE,
            body={"learner_ref": "carol", "course_id": course["id"],
                  "due_date": "2026-06-01"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(cmp_rec["id"].startswith("asg-"))
        self.assertNotIn("status", cmp_rec)

        query = urllib.parse.urlencode({"as_of": "2026-06-15"})
        status, _, derived = self.request(
            "GET", "/compliance/%s/status?%s" % (cmp_rec["id"], query), headers=DANA
        )
        self.assertEqual(status, 200)
        self.assertEqual(derived["status"], "overdue")

        status, _, _ = self.request(
            "POST", "/progress", headers=BOB,
            body={"learner_ref": "carol", "course_id": course["id"],
                  "status": "completed"},
        )
        self.assertEqual(status, 201)
        status, _, derived = self.request(
            "GET", "/compliance/%s/status?%s" % (cmp_rec["id"], query), headers=DANA
        )
        self.assertEqual(derived["status"], "completed")

        status, _, workflow = self.request(
            "POST", "/workflows", headers=BOB,
            body={"name": "Onboarding", "steps": ["assign safety course"]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(workflow["id"].startswith("wfl-"))
        status, _, note = self.request(
            "POST", "/notifications", headers=BOB,
            body={"recipient_ref": "carol", "subject": "Briefing tomorrow"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(note["id"].startswith("ntf-"))

        status, _, report = self.request("GET", "/report?%s" % query, headers=DANA)
        self.assertEqual(status, 200)
        self.assertEqual(report["compliance_by_status"]["completed"], 1)
        self.assertEqual(report["registrations_by_state"]["registered"], 1)
        self.assertEqual(report["authorizations_by_state"]["approved"], 1)

        status, _, found = self.request("GET", "/search?q=safety", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIn(course["id"], [c["id"] for c in found["courses"]])

        # The learner reads her own records over HTTP.
        status, _, own = self.request("GET", "/registrations/%s" % reg["id"],
                                      headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(own["learner_ref"], "carol")


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404, learner scope, and denied-audit behaviour."""

    def test_learner_write_is_403_and_denied_audited(self):
        """Core 12/13: learner POST /courses -> 403, and a '<action>:denied' audit entry appears for carol."""
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
        """Core 12: carol reading erin's registration over HTTP -> 403."""
        self.make_learner("erin", "Erin Learner")
        course = self.make_course("Scope Course %s" % self.id())
        status, _, event = self.request(
            "POST", "/events", headers=BOB,
            body={"title": "Scoped Briefing", "starts_at": "2026-07-01T09:00:00Z",
                  "course_id": course["id"]},
        )
        self.assertEqual(status, 201)
        status, _, other = self.request(
            "POST", "/registrations", headers=BOB,
            body={"event_id": event["id"], "learner_ref": "erin"},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.request("GET", "/registrations/%s" % other["id"],
                                    headers=CAROL)
        self.assertEqual(status, 403)

    def test_registration_state_route(self):
        """REST / Core 3: POST /registrations/{id}/state moves a registration through its states over HTTP."""
        self.make_learner()
        course = self.make_course("State Course %s" % self.id())
        status, _, event = self.request(
            "POST", "/events", headers=BOB,
            body={"title": "State Briefing", "starts_at": "2026-07-01T09:00:00Z",
                  "course_id": course["id"]},
        )
        self.assertEqual(status, 201)
        status, _, reg = self.request(
            "POST", "/registrations", headers=BOB,
            body={"event_id": event["id"], "learner_ref": "carol"},
        )
        self.assertEqual(status, 201)
        status, _, updated = self.request(
            "POST", "/registrations/%s/state" % reg["id"], headers=BOB,
            body={"state": "attended"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["state"], "attended")
        status, _, parsed = self.request(
            "POST", "/registrations/%s/state" % reg["id"], headers=BOB,
            body={"state": "bogus"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_validation_400_and_not_found_404(self):
        """REST: bad course -> 400; unknown course -> 404, both with {error} envelopes."""
        status, _, parsed = self.request("POST", "/courses", headers=ALICE,
                                         body={"title": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/courses/crs-999999", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_audit_access(self):
        """REST / Core 13: GET /audit -> 200 for admin and auditor, 403 for instructor and learner."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        for headers in (ALICE, DANA):
            status, _, payload = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("entries", payload)

    def test_report_and_search_learner_403(self):
        """Core 11/12: GET /report and GET /search -> 403 for learner (no report_read)."""
        status, _, _ = self.request("GET", "/report", headers=CAROL)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/search?q=safety", headers=CAROL)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
