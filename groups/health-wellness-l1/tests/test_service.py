"""REST API service tests.

Traces to: the service layer for Group 18 -- ``health/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:clinician, carol:member,
dana:auditor}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin+auditor,
and the privacy discipline: any JSON key outside an endpoint's named
field list -> 400 before the store is called.
Covers Core functions 1-10 over HTTP, including derived plan /
enrollment / eligibility status via the ``as_of`` query parameter.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from health_helpers import USERS
from health.audit import AuditLog
from health.service import make_server
from health.store import HealthStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "clinician"}
CAROL = {"X-User": "carol", "X-Role": "member"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Core 1-10 over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = HealthStore(audit=cls.audit)
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

    def make_program_and_participant(self, suffix):
        """REST helper creating a program + participant as admin."""
        status, _, program = self.request(
            "POST", "/programs", headers=ALICE, body={"title": "Program %s" % suffix}
        )
        self.assertEqual(status, 201)
        status, _, participant = self.request(
            "POST", "/participants", headers=ALICE,
            body={"participant_ref": "ref-%s" % suffix},
        )
        self.assertEqual(status, 201)
        return program, participant


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
                        {"X-User": "alice", "X-Role": "member"},
                        {"X-User": "carol", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/programs", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """REST: unknown route -> 404 JSON, no stack trace; DELETE has no route either."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)
        status, _, _ = self.request("DELETE", "/programs", headers=ALICE)
        self.assertEqual(status, 404)


class TestFullFlow(ServiceBase):
    """REST: full health-records flow over HTTP (Core 1-8)."""

    def test_full_flow(self):
        """Core 1-8 over REST: program -> participant (opaque ref 'carol') -> enroll -> measurement -> plan (derived overdue, then completed; enrollment follows) -> activity -> eligibility -> scorecard + report."""
        status, _, program = self.request(
            "POST", "/programs", headers=ALICE, body={"title": "Diabetes Care"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(program["id"].startswith("prg-"))

        status, _, participant = self.request(
            "POST", "/participants", headers=ALICE, body={"participant_ref": "carol"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(participant["id"].startswith("par-"))

        status, _, enr = self.request(
            "POST", "/enrollments", headers=BOB,
            body={"participant_id": participant["id"], "program_id": program["id"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(enr["derived_status"], "enrolled")

        status, _, msr = self.request(
            "POST", "/measurements", headers=BOB,
            body={"participant_id": participant["id"], "metric_name": "glucose",
                  "value": 120, "unit": "mg/dL", "recorded_on": "2026-06-10",
                  "program_id": program["id"]},
        )
        self.assertEqual(status, 201)
        self.assertTrue(msr["id"].startswith("msr-"))
        self.assertNotIn("diagnosis", msr)

        status, _, plan = self.request(
            "POST", "/plans", headers=BOB,
            body={"participant_id": participant["id"], "program_id": program["id"],
                  "title": "Daily checks", "due_date": "2026-06-01"},
        )
        self.assertEqual(status, 201)

        query = urllib.parse.urlencode({"as_of": "2026-06-15"})
        status, _, derived = self.request(
            "GET", "/plans/%s?%s" % (plan["id"], query), headers=DANA
        )
        self.assertEqual(status, 200)
        self.assertEqual(derived["derived_status"], "overdue")
        status, _, enr_view = self.request(
            "GET", "/enrollments/%s?%s" % (enr["id"], query), headers=DANA
        )
        self.assertEqual(enr_view["derived_status"], "overdue")

        status, _, act = self.request(
            "POST", "/activities", headers=BOB,
            body={"participant_id": participant["id"], "title": "Clinic visit",
                  "starts_at": "2026-07-01T09:00:00Z", "program_id": program["id"]},
        )
        self.assertEqual(status, 201)
        status, _, act = self.request(
            "POST", "/activities/%s/state" % act["id"], headers=BOB,
            body={"state": "completed"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(act["state"], "completed")

        status, _, elg = self.request(
            "POST", "/eligibility", headers=ALICE,
            body={"participant_id": participant["id"], "plan_ref": "plan-alpha",
                  "coverage_start": "2026-01-01", "coverage_end": "2026-12-31"},
        )
        self.assertEqual(status, 201)
        status, _, elg_status = self.request(
            "GET", "/eligibility/%s/status?%s" % (elg["id"], query), headers=DANA
        )
        self.assertEqual(status, 200)
        self.assertEqual(elg_status, {"id": elg["id"], "derived_status": "current"})

        status, _, done = self.request(
            "POST", "/plans/%s/complete" % plan["id"], headers=BOB,
            body={"completed_on": "2026-06-14"},
        )
        self.assertEqual(status, 200)
        status, _, derived = self.request(
            "GET", "/plans/%s?%s" % (plan["id"], query), headers=DANA
        )
        self.assertEqual(derived["derived_status"], "completed")

        status, _, card = self.request(
            "GET", "/scorecard/%s?%s" % (program["id"], query), headers=DANA
        )
        self.assertEqual(status, 200)
        self.assertEqual(card["measurements"], 1)
        self.assertEqual(card["plans_by_status"]["completed"], 1)

        status, _, report = self.request("GET", "/report?%s" % query, headers=DANA)
        self.assertEqual(status, 200)
        self.assertEqual(report["participants"], 1)
        self.assertEqual(report["enrollments"], 1)

        # The member reads her own records over HTTP (ref == user name).
        status, _, own = self.request("GET", "/enrollments/%s" % enr["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(own["participant_id"], participant["id"])


class TestPrivacyBoundary(ServiceBase):
    """REST: privacy discipline -- unknown/extra JSON keys are refused."""

    def test_extra_fields_rejected_400(self):
        """Privacy discipline (SI-10/SI-12): smuggling 'diagnosis', 'note', 'name' or 'dob' into any POST body -> 400 and nothing is stored."""
        program, participant = self.make_program_and_participant("privacy")
        cases = [
            ("/participants", ALICE,
             {"participant_ref": "ref-x", "name": "Real Name"}),
            ("/participants", ALICE,
             {"participant_ref": "ref-y", "dob": "2000-01-01"}),
            ("/measurements", BOB,
             {"participant_id": participant["id"], "metric_name": "glucose",
              "value": 1, "unit": "mg/dL", "recorded_on": "2026-06-10",
              "diagnosis": "diabetes"}),
            ("/measurements", BOB,
             {"participant_id": participant["id"], "metric_name": "glucose",
              "value": 1, "unit": "mg/dL", "recorded_on": "2026-06-10",
              "note": "clinical note"}),
            ("/plans", BOB,
             {"participant_id": participant["id"], "program_id": program["id"],
              "title": "T", "due_date": "2026-06-01", "note": "x"}),
            ("/eligibility", ALICE,
             {"participant_id": participant["id"], "plan_ref": "p",
              "coverage_start": "2026-01-01", "member_number": "123"}),
            ("/programs", ALICE, {"title": "T", "diagnosis": "x"}),
        ]
        for path, headers, body in cases:
            with self.subTest(path=path, body=body):
                status, _, parsed = self.request("POST", path, headers=headers, body=body)
                self.assertEqual(status, 400)
                self.assertIn("error", parsed)
        # Nothing smuggled was stored: only the helper's own records exist.
        status, _, listing = self.request("GET", "/measurements", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(listing["measurements"], [])


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404, member scope, and denied-audit behaviour."""

    def test_member_write_is_403_and_denied_audited(self):
        """Core 9/10 (AC-3/AU-2): member POST /programs -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/programs", headers=CAROL, body={"title": "Nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_member_scope_over_http(self):
        """Core 9 + member scope: carol reading another participant's enrollment over HTTP -> 403; her list shows only her own."""
        program, participant = self.make_program_and_participant("scope")
        # participant here has ref 'ref-scope', not 'carol': create carol too.
        status, _, carol = self.request(
            "POST", "/participants", headers=ALICE, body={"participant_ref": "carol"}
        )
        self.assertEqual(status, 201)
        status, _, other_enr = self.request(
            "POST", "/enrollments", headers=BOB,
            body={"participant_id": participant["id"], "program_id": program["id"]},
        )
        self.assertEqual(status, 201)
        status, _, own_enr = self.request(
            "POST", "/enrollments", headers=BOB,
            body={"participant_id": carol["id"], "program_id": program["id"]},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.request("GET", "/enrollments/%s" % other_enr["id"], headers=CAROL)
        self.assertEqual(status, 403)
        status, _, listing = self.request("GET", "/enrollments", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([e["id"] for e in listing["enrollments"]], [own_enr["id"]])

    def test_validation_400_and_not_found_404(self):
        """REST (SI-10): bad program -> 400; unknown program -> 404."""
        status, _, parsed = self.request("POST", "/programs", headers=ALICE, body={"title": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/programs/prg-999999", headers=ALICE)
        self.assertEqual(status, 404)

    def test_audit_access(self):
        """REST / Core 10 (AU-6): GET /audit -> 200 for admin and auditor, 403 for clinician and member."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        for headers in (ALICE, DANA):
            status, _, payload = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 200)
            self.assertIn("entries", payload)

    def test_report_member_403(self):
        """Core 8/9: GET /report -> 403 for member (no report_read)."""
        status, _, _ = self.request("GET", "/report", headers=CAROL)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
