"""REST API service tests.

Traces to: the service layer for Group 32 -- ``fleet/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
against USERS {alice:admin, bob:manager, carol:viewer}, errors JSON
{error} 400/401/403/404, denied attempts audited.
"""

import http.client
import json
import threading
import unittest

from fleet_helpers import USERS
from fleet.audit import AuditLog
from fleet.service import make_server
from fleet.store import FleetStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "manager"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Core functions over REST: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = FleetStore(audit=cls.audit)
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

    def make_vehicle(self, label="Pool Sedan 1"):
        """REST helper creating a vehicle via POST /vehicles as admin."""
        status, _, parsed = self.request("POST", "/vehicles", headers=ALICE,
                                         body={"label": label, "vehicle_type": "sedan"})
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
                status, _, parsed = self.request("GET", "/vehicles", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404(self):
        """REST: unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """REST: full fleet-records flow over HTTP."""

    def test_full_flow(self):
        """Core 1-9 over REST: vehicle -> operator -> reservation -> check_out/check_in -> usage -> maintenance + complete -> charging + close -> search -> report."""
        vehicle = self.make_vehicle()
        self.assertTrue(vehicle["id"].startswith("veh-"))

        status, _, operator = self.request("POST", "/operators", headers=BOB,
                                           body={"operator_ref": "OP-REF-001", "credential_kind": "license"})
        self.assertEqual(status, 201)
        self.assertEqual(set(operator), {"id", "operator_ref", "credential_kind",
                                         "credential_status", "created_by", "created_utc"})

        status, _, res = self.request("POST", "/reservations", headers=BOB,
                                      body={"vehicle_id": vehicle["id"], "operator_ref": "OP-REF-001",
                                            "start": "2026-11-01", "end": "2026-11-03"})
        self.assertEqual(status, 201)
        self.assertEqual(res["status"], "reserved")

        status, _, chk = self.request("POST", "/checkins", headers=BOB,
                                      body={"reservation_id": res["id"], "kind": "check_out", "odometer": 12000})
        self.assertEqual(status, 201)
        status, _, got = self.request("GET", "/reservations/%s" % res["id"], headers=CAROL)
        self.assertEqual(got["status"], "checked_out")
        status, _, chk = self.request("POST", "/checkins", headers=BOB,
                                      body={"reservation_id": res["id"], "kind": "check_in", "odometer": 12150})
        self.assertEqual(status, 201)
        status, _, got = self.request("GET", "/reservations/%s" % res["id"], headers=CAROL)
        self.assertEqual(got["status"], "returned")

        status, _, use = self.request("POST", "/usage", headers=BOB,
                                      body={"vehicle_id": vehicle["id"], "odometer_reading": 12150})
        self.assertEqual(status, 201)
        status, _, _ = self.request("POST", "/usage", headers=BOB,
                                    body={"vehicle_id": vehicle["id"], "odometer_reading": 12000})
        self.assertEqual(status, 400)  # monotonic rule over HTTP

        status, _, mnt = self.request("POST", "/maintenance", headers=BOB,
                                      body={"vehicle_id": vehicle["id"], "kind": "inspection",
                                            "due_date": "2026-12-01"})
        self.assertEqual(status, 201)
        self.assertNotIn("status", mnt)  # stored record has no status; only the derived view field
        status, _, view = self.request("GET", "/maintenance/%s?as_of=2026-12-02" % mnt["id"], headers=CAROL)
        self.assertEqual(view["derived_status"], "overdue")
        status, _, done = self.request("POST", "/maintenance/%s/complete" % mnt["id"], headers=BOB,
                                       body={"completed_date": "2026-11-20"})
        self.assertEqual(status, 200)
        self.assertEqual(done["derived_status"], "completed")

        status, _, chg = self.request("POST", "/charging-sessions", headers=BOB,
                                      body={"station_ref": "STN-1", "operator_ref": "OP-REF-001"})
        self.assertEqual(status, 201)
        self.assertIsNone(chg["ended_utc"])
        status, _, chg = self.request("POST", "/charging-sessions/%s/close" % chg["id"], headers=BOB,
                                      body={"watt_hours": 22500})
        self.assertEqual(status, 200)
        self.assertEqual(chg["watt_hours"], 22500)
        self.assertIsNotNone(chg["ended_utc"])

        status, _, found = self.request("GET", "/search?q=pool", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(found["vehicles"]), 1)

        status, _, report = self.request("GET", "/reports/summary", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(report["counts"]["vehicles"], 1)
        self.assertEqual(report["total_watt_hours"], 22500)
        self.assertEqual(report["vehicles"][0]["latest_odometer"], 12150)


class TestServiceAccessAndErrors(ServiceBase):
    """REST: 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """Core 10 (AC-3/AU-2): viewer POST /vehicles -> 403, and a ':denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"] if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request("POST", "/vehicles", headers=CAROL,
                                         body={"label": "Nope", "vehicle_type": "sedan"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400_and_not_found_404(self):
        """REST (SI-10): bad vehicle -> 400; unknown vehicle -> 404; illegal reservation transition -> 400; second active reservation -> 400."""
        status, _, parsed = self.request("POST", "/vehicles", headers=ALICE,
                                         body={"label": "", "vehicle_type": "sedan"})
        self.assertEqual(status, 400)
        status, _, _ = self.request("GET", "/vehicles/veh-999999", headers=ALICE)
        self.assertEqual(status, 404)
        vehicle = self.make_vehicle("GateCar %s" % self.id())
        status, _, res = self.request("POST", "/reservations", headers=ALICE,
                                      body={"vehicle_id": vehicle["id"], "operator_ref": "OP",
                                            "start": "2026-11-01", "end": "2026-11-02"})
        self.assertEqual(status, 201)
        status, _, _ = self.request("POST", "/reservations/%s/status" % res["id"], headers=ALICE,
                                    body={"status": "returned"})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/reservations", headers=ALICE,
                                    body={"vehicle_id": vehicle["id"], "operator_ref": "OP2",
                                          "start": "2026-12-01", "end": "2026-12-02"})
        self.assertEqual(status, 400)

    def test_audit_access_admin_only(self):
        """REST / Core 10: GET /audit -> 200 for admin, 403 for manager and viewer (no audit_read)."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)

    def test_search_empty_query_400(self):
        """REST / Core 9 (SI-10): GET /search without q -> 400."""
        status, _, _ = self.request("GET", "/search", headers=ALICE)
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
