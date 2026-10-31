"""Core function 11: the REST API, exercised over real HTTP.

Includes the denied-attempt audit discipline: unauthenticated and
forbidden requests are audited with a ``:denied`` suffix, and an
audit read is itself audited (AU-2/AU-3, Low side).
"""

import http.client
import json
import unittest

from energy.service import make_server

from energy_helpers import CLOSES, IN_WINDOW, OPENS

USERS = {"alice": "admin", "bob": "member", "carol": "viewer"}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0, users=USERS)
        self.port = self.server.server_address[1]
        import threading
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

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
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, payload

    def seed(self):
        status, customer = self.call("POST", "/customers", "alice", "admin",
                                     {"ref": "CUST-0001", "label": "Utility"})
        self.assertEqual(status, 201)
        status, provider = self.call("POST", "/providers", "alice", "admin",
                                     {"ref": "PROV-0001", "label": "SupplyCo"})
        self.assertEqual(status, 201)
        status, auction = self.call(
            "POST", "/auctions", "bob", "member",
            {"customer_id": customer["id"], "commodity": "electricity",
             "region": "ERCOT-North", "unit_label": "kWh",
             "quantity_units": 1000, "opens_at": OPENS, "closes_at": CLOSES})
        self.assertEqual(status, 201)
        return customer, provider, auction

    def test_health_is_public(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual((status, payload), (200, {"status": "ok"}))

    def test_full_flow(self):
        customer, provider, auction = self.seed()
        status, bid = self.call(
            "POST", "/auctions/%s/bids" % auction["id"], "bob", "member",
            {"provider_id": provider["id"], "price_cents_per_unit": 420,
             "at": IN_WINDOW})
        self.assertEqual(status, 201)
        self.assertEqual(bid["price_cents_per_unit"], 420)
        status, outcome = self.call(
            "GET", "/auctions/%s/outcome?now=2024-06-05" % auction["id"],
            "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(outcome["winning_bid_id"], bid["id"])
        self.assertEqual(outcome["lowest_price_cents_per_unit"], 420)
        status, summary = self.call("GET", "/summary?now=2024-06-05",
                                    "carol", "viewer")
        self.assertEqual(summary["bids"], 1)

    def test_float_price_rejected_over_http(self):
        _, provider, auction = self.seed()
        status, payload = self.call(
            "POST", "/auctions/%s/bids" % auction["id"], "bob", "member",
            {"provider_id": provider["id"], "price_cents_per_unit": 4.2,
             "at": IN_WINDOW})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_auth_and_denied_auditing(self):
        status, _ = self.call("GET", "/customers")
        self.assertEqual(status, 401)
        status, _ = self.call("POST", "/customers", "carol", "viewer",
                              {"ref": "X", "label": "Y"})
        self.assertEqual(status, 403)
        status, _ = self.call("GET", "/customers", "alice", "member")
        self.assertEqual(status, 401)  # role does not match registry
        status, audit = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        denied = [e for e in audit["entries"]
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 3)
        status, _ = self.call("GET", "/audit", "bob", "member")
        self.assertEqual(status, 403)

    def test_unknown_route_and_object(self):
        status, _ = self.call("GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/customers/cust-99", "alice", "admin")
        self.assertEqual(status, 404)

    def test_engagement_and_alert_over_http(self):
        customer, _, _ = self.seed()
        status, eng = self.call(
            "POST", "/engagements", "bob", "member",
            {"customer_id": customer["id"], "kind": "budgeting",
             "note": "Budget review"})
        self.assertEqual(status, 201)
        status, closed = self.call(
            "POST", "/engagements/%s/close" % eng["id"], "bob", "member", {})
        self.assertEqual(closed["status"], "closed")
        status, alert = self.call(
            "POST", "/alerts", "bob", "member",
            {"customer_id": customer["id"], "kind": "market_update",
             "subject": "Weekly update"})
        self.assertEqual(status, 201)
        status, found = self.call("GET", "/search?q=budget", "carol", "viewer")
        self.assertEqual(len(found["engagements"]), 1)


if __name__ == "__main__":
    unittest.main()
