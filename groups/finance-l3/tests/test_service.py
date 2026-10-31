"""REST API service tests.

Traces to: UNION-SPEC Core function 9 (API access), Core function 10
(Access control) and Core function 11 (Audit log) as enforced over
HTTP; Implementation contract for ``finance/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
headers matched against the registry, errors as JSON {error} with
400/401/403/404, denied attempts audited with the action name suffixed
``:denied``.
"""

import http.client
import json
import threading
import unittest

from finance_helpers import USERS_REGISTRY
from finance.audit import AuditLog
from finance.service import make_server
from finance.store import FinanceStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = FinanceStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS_REGISTRY)
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    # -- low-level helpers -------------------------------------------------
    def request(self, method, path, headers=None, body=None):
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

    # -- flow helpers --------------------------------------------------------
    def create_program(self, name, headers=None):
        status, _, parsed = self.request(
            "POST", "/programs", headers=headers or BOB, body={"name": name},
        )
        self.assertEqual(status, 201, "program creation failed")
        self.assertIsInstance(parsed, dict)
        return parsed

    def add_member(self, program_id, username, headers=None):
        status, _, parsed = self.request(
            "POST", "/programs/%s/members" % program_id,
            headers=headers or BOB, body={"username": username},
        )
        self.assertIn(status, (200, 201))
        return parsed

    def create_participant(self, program_id, ref, kind, headers=None):
        status, _, parsed = self.request(
            "POST", "/programs/%s/participants" % program_id,
            headers=headers or BOB, body={"ref": ref, "kind": kind},
        )
        self.assertEqual(status, 201, "participant creation failed")
        return parsed

    def create_accrual(self, program_id, participant_id, earned=100000,
                       period="2026-01", headers=None):
        status, _, parsed = self.request(
            "POST", "/programs/%s/accruals" % program_id,
            headers=headers or BOB,
            body={"participant_id": participant_id, "period": period,
                  "earned_cents": earned},
        )
        self.assertEqual(status, 201, "accrual creation failed")
        return parsed

    def create_request(self, program_id, participant_id, amount=10000,
                       period="2026-01", date="2026-01-10", headers=None):
        status, _, parsed = self.request(
            "POST", "/programs/%s/access-requests" % program_id,
            headers=headers or BOB,
            body={"participant_id": participant_id, "period": period,
                  "amount_cents": amount, "date": date},
        )
        self.assertEqual(status, 201, "access request creation failed")
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core 9: API access — health, header auth, error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core 9: API access. Contract: GET /health (no auth) ->
        {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_headers_is_401(self):
        """Core 9: API access + Core 10 Access control (IA-2). No
        X-User/X-Role headers -> 401 with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/programs")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core 9: API access (IA-2). Contract: an unknown user ->
        401."""
        status, _, parsed = self.request(
            "GET", "/programs",
            headers={"X-User": "mallory", "X-Role": "admin"},
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core 9: API access (IA-2). Contract: 'the role must match
        the registry' — a mismatched X-Role -> 401 (alice claiming
        viewer, bob claiming admin, carol claiming member)."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "member"}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/programs",
                                                 headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_json_without_stack_trace(self):
        """Core 9: API access. Unknown routes return JSON {error}
        404, and 'no stack trace is ever returned'."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core 9: API access — the whole finance surface over HTTP."""

    def test_full_flow_program_to_summary(self):
        """Core 9: API access + Core 1/2/3/4/5/7. Full flow: create
        program -> participant (employee + traveler) -> accrual ->
        access request -> approve by another user -> disbursement ->
        booking -> budget -> spend-vs-budget -> program summary."""
        program = self.create_program("flow-program")
        program_id = program["id"]
        self.assertTrue(program_id.startswith("prog-"))
        self.assertEqual(program["owner"], "bob")
        self.assertEqual(program["members"], ["bob"])

        program = self.add_member(program_id, "carol")
        self.assertIn("carol", program["members"])

        employee = self.create_participant(program_id, "emp-1", "employee")
        traveler = self.create_participant(program_id, "trav-1", "traveler")
        self.assertTrue(employee["id"].startswith("part-"))
        self.assertEqual(employee["status"], "active")

        accrual = self.create_accrual(program_id, employee["id"])
        self.assertTrue(accrual["id"].startswith("acc-"))
        self.assertEqual(accrual["earned_cents"], 100000)

        status, _, view = self.request(
            "GET", "/programs/%s/accruals/%s" % (program_id, accrual["id"]),
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(view["available_cents"], 100000)

        request = self.create_request(program_id, employee["id"],
                                      amount=20000)
        self.assertTrue(request["id"].startswith("req-"))
        self.assertEqual(request["status"], "requested")

        status, _, decided = self.request(
            "POST",
            "/programs/%s/access-requests/%s/approve"
            % (program_id, request["id"]),
            headers=ALICE, body={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "alice")

        status, _, disbursement = self.request(
            "POST",
            "/programs/%s/access-requests/%s/disbursements"
            % (program_id, request["id"]),
            headers=BOB, body={"date": "2026-01-20", "method": "payroll"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(disbursement["id"].startswith("dis-"))
        self.assertEqual(disbursement["amount_cents"], 20000)

        status, _, booking = self.request(
            "POST", "/programs/%s/bookings" % program_id, headers=BOB,
            body={"participant_id": traveler["id"], "kind": "air",
                  "start_date": "2026-01-10", "end_date": "2026-01-12",
                  "amount_cents": 30000},
        )
        self.assertEqual(status, 201)
        self.assertTrue(booking["id"].startswith("bkg-"))
        self.assertEqual(booking["status"], "recorded")

        status, _, budget = self.request(
            "PUT", "/programs/%s/budgets/2026-01" % program_id, headers=BOB,
            body={"lines": [{"category": "air", "limit_cents": 50000},
                            {"category": "earned_wage",
                             "limit_cents": 25000}]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(budget["id"].startswith("bud-"))
        self.assertEqual(budget["total_cents"], 75000)

        status, _, vs_actual = self.request(
            "GET", "/programs/%s/budgets/2026-01/vs-actual" % program_id,
            headers=BOB,
        )
        self.assertEqual(status, 200)
        spent = {line["category"]: line["spent_cents"]
                 for line in vs_actual["lines"]}
        self.assertEqual(spent, {"air": 30000, "earned_wage": 20000})
        self.assertEqual(vs_actual["total_spent_cents"], 50000)
        self.assertEqual(vs_actual["total_variance_cents"], 75000 - 50000)

        status, _, summary = self.request(
            "GET",
            "/programs/%s/reports/summary?period=2026-01" % program_id,
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(summary["participants"], 2)
        self.assertEqual(summary["earned_cents"], 100000)
        self.assertEqual(summary["accessed_cents"], 20000)
        self.assertEqual(summary["disbursed_cents"], 20000)
        self.assertEqual(summary["pending_cents"], 0)
        self.assertEqual(summary["bookings"]["air"],
                         {"count": 1, "total_cents": 30000})

    def test_list_and_get_program(self):
        """Core 9: API access + Core 1 Programs. GET /programs lists
        the caller's programs as {"programs": [...]}; GET
        /programs/{id} returns one program dict."""
        program = self.create_program("listable-program")
        status, _, payload = self.request("GET", "/programs", headers=BOB)
        self.assertEqual(status, 200)
        items = payload["programs"] if isinstance(payload, dict) else payload
        self.assertIn(program["id"], [p["id"] for p in items])

        status, _, got = self.request(
            "GET", "/programs/%s" % program["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], program["id"])
        self.assertEqual(got["name"], "listable-program")

    def test_get_unknown_program_is_404(self):
        """Core 9: API access. Unknown program id -> 404 JSON
        {error}."""
        status, _, parsed = self.request(
            "GET", "/programs/prog-999999", headers=ALICE
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


class TestServiceAccessControl(ServiceBase):
    """Core 9/10: API access + access control over HTTP."""

    def test_viewer_creating_a_participant_is_403(self):
        """Core 10: Access control (AC-3). A viewer program member
        POSTing a participant -> 403 JSON {error} (viewer lacks
        enter)."""
        program = self.create_program("viewer-participant-program")
        self.add_member(program["id"], "carol")
        status, _, parsed = self.request(
            "POST", "/programs/%s/participants" % program["id"],
            headers=CAROL, body={"ref": "emp-1", "kind": "employee"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_deciding_a_request_is_403(self):
        """Core 10: Access control (AC-3/AC-6). A viewer program
        member POSTing an access-request approval -> 403 (viewer
        lacks decide), and the request stays requested."""
        program = self.create_program("viewer-decide-program")
        self.add_member(program["id"], "carol")
        employee = self.create_participant(program["id"], "emp-1",
                                           "employee")
        self.create_accrual(program["id"], employee["id"])
        request = self.create_request(program["id"], employee["id"])
        status, _, parsed = self.request(
            "POST",
            "/programs/%s/access-requests/%s/approve"
            % (program["id"], request["id"]),
            headers=CAROL, body={},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        status, _, got = self.request(
            "GET",
            "/programs/%s/access-requests/%s"
            % (program["id"], request["id"]),
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["status"], "requested")

    def test_creator_approving_own_request_is_403_separation_of_duties(self):
        """Core 9/8: API access + workflow (AC-5). Over HTTP the SoD
        rule surfaces as 403: bob created the request, so bob's own
        approve is denied and the request stays requested."""
        program = self.create_program("sod-program")
        employee = self.create_participant(program["id"], "emp-1",
                                           "employee")
        self.create_accrual(program["id"], employee["id"])
        request = self.create_request(program["id"], employee["id"])
        status, _, parsed = self.request(
            "POST",
            "/programs/%s/access-requests/%s/approve"
            % (program["id"], request["id"]),
            headers=BOB, body={},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        status, _, got = self.request(
            "GET",
            "/programs/%s/access-requests/%s"
            % (program["id"], request["id"]),
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["status"], "requested")

    def test_viewer_cannot_create_a_program(self):
        """Core 10: Access control. Viewer POST /programs -> 403
        (viewer lacks create_program)."""
        status, _, parsed = self.request(
            "POST", "/programs", headers=CAROL, body={"name": "nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)


class TestServiceValidation(ServiceBase):
    """Core 9: API access — validation failures map to 400 (SI-10)."""

    def test_over_cap_request_over_http_is_400_and_creates_nothing(self):
        """Core 9 + Core 3: API access + earned-wage access (SI-10).
        An access request one cent over the period's earned amount
        POSTed over HTTP -> 400 JSON {error}, and the program's
        access-request list stays empty — the earned-cap rejection is
        whole, with no request created."""
        program = self.create_program("overcap-program")
        employee = self.create_participant(program["id"], "emp-1",
                                           "employee")
        self.create_accrual(program["id"], employee["id"], earned=10000)
        status, _, parsed = self.request(
            "POST", "/programs/%s/access-requests" % program["id"],
            headers=BOB,
            body={"participant_id": employee["id"], "period": "2026-01",
                  "amount_cents": 10001, "date": "2026-01-10"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, payload = self.request(
            "GET", "/programs/%s/access-requests" % program["id"],
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["access_requests"], [])

    def test_summary_without_period_is_400(self):
        """Core 9 + Core 7: API access + reporting. Contract: GET
        reports/summary requires a period — 'a missing period -> 400';
        with the period it returns 200."""
        program = self.create_program("summary-program")
        status, _, parsed = self.request(
            "GET", "/programs/%s/reports/summary" % program["id"],
            headers=BOB,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request(
            "GET",
            "/programs/%s/reports/summary?period=2026-01" % program["id"],
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["period"], "2026-01")
        self.assertEqual(parsed["earned_cents"], 0)


class TestServiceAudit(ServiceBase):
    """Core 9/11: API access + audit log over HTTP."""

    def test_audit_endpoint_is_admin_only(self):
        """Core 11: Audit log (AU-6). Among L2 roles, GET /audit is
        admin-only. Contract: GET /audit requires audit_read — a
        member (and a viewer) get 403, the admin gets 200 with
        {"entries": [...]}."""
        for headers in (BOB, CAROL):
            with self.subTest(headers=headers):
                status, _, parsed = self.request(
                    "GET", "/audit", headers=headers
                )
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)
        self.assertIsInstance(payload["entries"], list)
        for entry in payload["entries"]:
            for key in ("ts", "actor", "action", "target"):
                self.assertIn(key, entry)

    def test_audit_read_auditor_allowed_programs_denied(self):
        """Core 11 [L3] (AC-5 / AU-6): dana the auditor CAN read
        GET /audit (200 with {"entries": [...]}) but holds no
        operational permission — GET /programs is 403 for her
        (auditor holds no read)."""
        status, _, payload = self.request("GET", "/audit", headers=DANA)
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)
        self.assertIsInstance(payload["entries"], list)
        status, _, parsed = self.request("GET", "/programs", headers=DANA)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_denied_attempt_appears_in_audit_with_denied_suffix(self):
        """Core 11: Audit log. Contract: 'denied attempts (401 and
        403) are audited with the action name suffixed :denied' —
        after carol's 403 participant-creation attempt, the admin's
        audit read contains a carol entry whose action ends with
        :denied."""
        program = self.create_program("denied-program")
        self.add_member(program["id"], "carol")

        def carol_denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            entries = (payload["entries"] if isinstance(payload, dict)
                       else payload)
            return len([
                e for e in entries
                if e["actor"] == "carol"
                and str(e["action"]).endswith(":denied")
            ])

        before = carol_denied_count()
        status, _, _ = self.request(
            "POST", "/programs/%s/participants" % program["id"],
            headers=CAROL, body={"ref": "emp-1", "kind": "employee"},
        )
        self.assertEqual(status, 403)
        self.assertGreater(carol_denied_count(), before)


if __name__ == "__main__":
    unittest.main()
