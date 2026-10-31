import http.client
import json
import threading
import unittest

from travel.audit import AuditLog
from travel.service import make_server
from travel.store import TravelStore

USERS = {"alice": "admin", "bob": "member", "carol": "viewer",
         "dana": "member"}


class Client:
    def __init__(self, port):
        self.port = port

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        conn.request(method, path,
                     body=json.dumps(body) if body is not None else None,
                     headers=headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = TravelStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.client = Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_no_auth(self):
        status, body = self.client.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_unauthorized_without_headers(self):
        status, _ = self.client.call("GET", "/organizations")
        self.assertEqual(status, 401)

    def test_unauthorized_on_role_mismatch(self):
        status, _ = self.client.call("GET", "/organizations",
                                     user="bob", role="admin")
        self.assertEqual(status, 401)

    def test_full_flow(self):
        c = self.client
        status, org = c.call("POST", "/organizations", "alice", "admin",
                             {"ref": "ORG-HTTP", "label": "HTTP Agency"})
        self.assertEqual(status, 201)
        org_id = org["id"]
        for name in ("bob", "carol", "dana"):
            status, _ = c.call("POST", "/organizations/%s/members" % org_id,
                               "alice", "admin", {"username": name})
            self.assertEqual(status, 200)

        status, traveler = c.call(
            "POST", "/organizations/%s/travelers" % org_id, "bob", "member",
            {"traveler_ref": "TRV-HTTP", "label": "HTTP Traveler"})
        self.assertEqual(status, 201)

        status, auth = c.call(
            "POST", "/organizations/%s/authorizations" % org_id,
            "bob", "member",
            {"traveler_id": traveler["id"],
             "destination_label": "Denver, CO", "purpose": "Site review",
             "depart_date": "2026-06-10", "return_date": "2026-06-12",
             "authorized_cents": 500000})
        self.assertEqual(status, 201)
        auth_id = auth["id"]

        # The creator cannot decide his own authorization (403).
        status, _ = c.call("POST", "/authorizations/%s/submit" % auth_id,
                           "bob", "member", {})
        self.assertEqual(status, 200)
        status, _ = c.call("POST", "/authorizations/%s/decide" % auth_id,
                           "bob", "member", {"approve": True})
        self.assertEqual(status, 403)
        status, result = c.call("POST",
                                "/authorizations/%s/decide" % auth_id,
                                "dana", "member", {"approve": True})
        self.assertEqual(status, 200)
        self.assertEqual(result["authorization"]["status"], "approved")

        status, report = c.call(
            "POST", "/authorizations/%s/expense-reports" % auth_id,
            "bob", "member", {"title": "Denver expenses"})
        self.assertEqual(status, 201)
        report_id = report["id"]
        status, _ = c.call("POST", "/expense-reports/%s/items" % report_id,
                           "bob", "member",
                           {"category": "lodging", "amount_cents": 120000,
                            "item_date": "2026-06-10"})
        self.assertEqual(status, 201)
        status, _ = c.call("POST", "/expense-reports/%s/items" % report_id,
                           "bob", "member",
                           {"category": "meals", "amount_cents": 30000,
                            "item_date": "2026-06-11"})
        self.assertEqual(status, 201)
        status, view = c.call("GET", "/expense-reports/%s" % report_id,
                              "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(view["total_cents"], 150000)

        status, _ = c.call("POST", "/expense-reports/%s/submit" % report_id,
                           "bob", "member", {})
        self.assertEqual(status, 200)
        status, _ = c.call("POST", "/expense-reports/%s/decide" % report_id,
                           "dana", "member", {"approve": True})
        self.assertEqual(status, 200)

        status, voucher = c.call(
            "POST", "/expense-reports/%s/vouchers" % report_id,
            "bob", "member", {"amount_cents": 150000})
        self.assertEqual(status, 201)
        # One cent over the report total is a 400.
        status, _ = c.call("POST", "/expense-reports/%s/vouchers" % report_id,
                           "bob", "member", {"amount_cents": 1})
        self.assertEqual(status, 400)

        status, summary = c.call("GET",
                                 "/organizations/%s/summary" % org_id,
                                 "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(summary["reimbursed_cents"], 150000)

    def test_viewer_cannot_record_voucher_gets_403_and_denial_audited(self):
        c = self.client
        before = len(self.audit.entries())
        status, _ = c.call("POST", "/expense-reports/exp-999/vouchers",
                           "carol", "viewer", {"amount_cents": 1})
        self.assertEqual(status, 403)
        denied = [e for e in self.audit.entries()[before:]
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

    def test_audit_read_requires_admin(self):
        status, _ = self.client.call("GET", "/audit", "carol", "viewer")
        self.assertEqual(status, 403)
        status, body = self.client.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        self.assertIn("entries", body)

    def test_unknown_route_404(self):
        status, _ = self.client.call("GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)

    def test_missing_object_404(self):
        status, _ = self.client.call("GET", "/expense-reports/exp-999",
                                     "alice", "admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
