"""Core function 16: the REST API, exercised over real HTTP.

The full flow exercises the balanced-entry gate end to end:
register, record a balanced entry (201), post an unbalanced entry
(400), post a float amount (400), derive a purchase-order total,
and run an expense outcome. Denied attempts are audited with a
``:denied`` suffix; an audit read is itself audited (AU-2/AU-3/
AU-6 at the Moderate baseline).
"""

import http.client
import json
import threading
import unittest

from erp.service import make_server

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}

BALANCED = [
    {"account_ref": "ACCT-1000", "debit_cents": 5000, "credit_cents": 0},
    {"account_ref": "ACCT-2000", "debit_cents": 0, "credit_cents": 5000},
]
UNBALANCED = [
    {"account_ref": "ACCT-1000", "debit_cents": 5000, "credit_cents": 0},
    {"account_ref": "ACCT-2000", "debit_cents": 0, "credit_cents": 4999},
]


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0, users=USERS)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.audit = self.server.audit

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

    def seed_org(self):
        status, org = self.call("POST", "/organizations", "alice", "admin",
                                {"ref": "ORG-0001", "label": "Agency"})
        self.assertEqual(status, 201)
        return org

    def test_health_is_public(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual((status, payload), (200, {"status": "ok"}))

    def test_full_flow_with_balance_gate(self):
        org = self.seed_org()
        status, entry = self.call(
            "POST", "/ledger-entries", "bob", "operator",
            {"org_id": org["id"], "entry_ref": "JE-1",
             "memo_label": "Close", "lines": BALANCED})
        self.assertEqual(status, 201)
        self.assertEqual(entry["total_debits_cents"], 5000)
        status, payload = self.call(
            "POST", "/ledger-entries", "bob", "operator",
            {"org_id": org["id"], "entry_ref": "JE-2",
             "memo_label": "Bad", "lines": UNBALANCED})
        self.assertEqual(status, 400)
        self.assertIn("does not balance", payload["error"])
        status, order = self.call(
            "POST", "/purchase-orders", "bob", "operator",
            {"org_id": org["id"], "po_ref": "PO-1",
             "supplier_ref": "SUPPLIER-1",
             "lines": [{"item_label": "Toner", "quantity": 2,
                        "unit_price_cents": 2500}]})
        self.assertEqual(status, 201)
        self.assertEqual(order["total_cents"], 5000)
        status, person = self.call(
            "POST", "/persons", "bob", "operator",
            {"org_id": org["id"], "person_ref": "PERSON-1",
             "department_label": "Finance", "role_label": "Accountant"})
        self.assertEqual(status, 201)
        status, report = self.call(
            "POST", "/expense-reports", "bob", "operator",
            {"org_id": org["id"], "person_ref": "PERSON-1",
             "report_ref": "EXP-1",
             "lines": [{"category_label": "Travel", "amount_cents": 4200}]})
        self.assertEqual(status, 201)
        self.assertEqual(report["total_cents"], 4200)
        status, done = self.call(
            "POST", "/expense-reports/%s/outcome" % report["id"],
            "bob", "operator", {"outcome": "approved"})
        self.assertEqual(status, 200)
        self.assertEqual(done["status"], "approved")
        status, summary = self.call("GET", "/summary", "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(summary["ledger_entries"], 1)
        self.assertEqual(summary["expense_reports_by_status"]["approved"], 1)

    def test_float_amount_is_a_400(self):
        org = self.seed_org()
        lines = [
            {"account_ref": "A", "debit_cents": 10.5, "credit_cents": 0},
            {"account_ref": "B", "debit_cents": 0, "credit_cents": 10.5},
        ]
        status, payload = self.call(
            "POST", "/ledger-entries", "bob", "operator",
            {"org_id": org["id"], "entry_ref": "JE-F",
             "memo_label": "Float", "lines": lines})
        self.assertEqual(status, 400)
        self.assertIn("integer", payload["error"])

    def test_auth_failures_and_denied_audit(self):
        status, _ = self.call("GET", "/organizations")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations", "mallory", "admin")
        self.assertEqual(status, 401)
        status, _ = self.call("POST", "/persons", "carol", "viewer",
                              {"org_id": "org-1", "person_ref": "P",
                               "department_label": "D", "role_label": "R"})
        self.assertEqual(status, 403)
        status, _ = self.call("GET", "/audit", "bob", "operator")
        self.assertEqual(status, 403)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 4)
        status, payload = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 4)
        reads = [e for e in self.audit.entries()
                 if e["action"] == "audit_read"]
        self.assertEqual(len(reads), 1)

    def test_not_found_is_a_404(self):
        status, _ = self.call("GET", "/organizations/org-99",
                              "alice", "admin")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/no-such-route", "alice", "admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
