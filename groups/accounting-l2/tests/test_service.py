"""REST API service tests.

Traces to: UNION-SPEC Core function 11 (API access) / ranking row 1
(APIs, integrations & interoperability, 13 siblings), plus Core
function 12 (Access control) and Core function 13 (Audit log) as
enforced over HTTP; Implementation contract for
``accounting/service.py``: make_server(host, port, store, audit,
users), auth via X-User / X-Role headers matched against the registry,
errors as JSON {error} with 400/401/403/404, denied attempts audited
with the action name suffixed ``:denied``.
"""

import http.client
import json
import threading
import unittest

from accounting_helpers import USERS_REGISTRY
from accounting.audit import AuditLog
from accounting.service import make_server
from accounting.store import AccountingStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}

CASH_LINE = {"description": "Consulting", "quantity": 1,
             "unit_price_cents": 5000}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = AccountingStore(audit=cls.audit)
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
    def create_book(self, name, headers=None):
        status, _, parsed = self.request(
            "POST", "/books", headers=headers or BOB, body={"name": name},
        )
        self.assertEqual(status, 201, "book creation failed")
        self.assertIsInstance(parsed, dict)
        return parsed

    def add_member(self, book_id, username, headers=None):
        status, _, parsed = self.request(
            "POST", "/books/%s/members" % book_id,
            headers=headers or BOB, body={"username": username},
        )
        self.assertIn(status, (200, 201))
        return parsed

    def create_account(self, book_id, code, name, account_type,
                       headers=None):
        status, _, parsed = self.request(
            "POST", "/books/%s/accounts" % book_id,
            headers=headers or BOB,
            body={"code": code, "name": name, "type": account_type},
        )
        self.assertEqual(status, 201, "account creation failed")
        return parsed

    def create_chart(self, book_id, headers=None):
        """The Cash/Equity pair (enough for the HTTP flows)."""
        cash = self.create_account(
            book_id, "1000", "Cash", "asset", headers=headers
        )
        equity = self.create_account(
            book_id, "3000", "OwnersEquity", "equity", headers=headers
        )
        return cash, equity

    def invest_lines(self, cash, equity, amount=100000):
        return [
            {"account_id": cash["id"], "debit_cents": amount},
            {"account_id": equity["id"], "credit_cents": amount},
        ]

    def create_entry(self, book_id, cash, equity, amount=100000,
                     headers=None):
        status, _, parsed = self.request(
            "POST", "/books/%s/entries" % book_id,
            headers=headers or BOB,
            body={"date": "2026-01-05", "memo": "Owner investment",
                  "lines": self.invest_lines(cash, equity, amount)},
        )
        self.assertEqual(status, 201, "entry creation failed")
        return parsed

    def transition(self, path, headers=None):
        status, _, parsed = self.request(
            "POST", path, headers=headers or BOB, body={},
        )
        self.assertIn(status, (200, 201))
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core 11: API access — health, header auth, error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core 11: API access. Contract: GET /health (no auth) ->
        {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_headers_is_401(self):
        """Core 11: API access + Core 12 Access control (IA-2). No
        X-User/X-Role headers -> 401 with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/books")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core 11: API access (IA-2). Contract: an unknown user ->
        401."""
        status, _, parsed = self.request(
            "GET", "/books",
            headers={"X-User": "mallory", "X-Role": "admin"},
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core 11: API access (IA-2). Contract: 'the role must match
        the registry' — a mismatched X-Role -> 401 (alice claiming
        viewer, bob claiming admin, carol claiming member)."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "member"}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/books",
                                                 headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_json_without_stack_trace(self):
        """Core 11: API access. Unknown routes return JSON {error}
        404, and 'no stack trace is ever returned'."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core 11: API access — the whole accounting surface over HTTP."""

    def test_full_flow_book_to_paid_invoice(self):
        """Core 11: API access + Core 1/2/3/4/5/9. Full flow: create
        book -> add member -> accounts -> entry -> submit -> approve
        by another user -> trial balance shows balanced -> invoice ->
        submit -> issue -> payment -> invoice paid."""
        book = self.create_book("flow-books")
        book_id = book["id"]
        self.assertTrue(book_id.startswith("book-"))
        self.assertEqual(book["owner"], "bob")
        self.assertEqual(book["members"], ["bob"])
        self.assertEqual(book["closed_periods"], [])

        book = self.add_member(book_id, "carol")
        self.assertIn("carol", book["members"])

        cash, equity = self.create_chart(book_id)
        self.assertTrue(cash["id"].startswith("acct-"))
        self.assertEqual(cash["type"], "asset")

        entry = self.create_entry(book_id, cash, equity)
        self.assertTrue(entry["id"].startswith("je-"))
        self.assertEqual(entry["status"], "draft")
        self.assertEqual(entry["total_cents"], 100000)

        entry = self.transition(
            "/books/%s/entries/%s/submit" % (book_id, entry["id"])
        )
        self.assertEqual(entry["status"], "pending")

        entry = self.transition(
            "/books/%s/entries/%s/approve" % (book_id, entry["id"]),
            headers=ALICE,
        )
        self.assertEqual(entry["status"], "posted")
        self.assertEqual(entry["approved_by"], "alice")

        status, _, trial = self.request(
            "GET", "/books/%s/reports/trial-balance" % book_id,
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertIs(trial["balanced"], True)
        self.assertEqual(trial["total_debits_cents"], 100000)
        self.assertEqual(trial["total_credits_cents"], 100000)

        status, _, invoice = self.request(
            "POST", "/books/%s/invoices" % book_id, headers=BOB,
            body={"customer": "Customer Co", "date": "2026-01-06",
                  "due_date": "2026-02-05", "lines": [CASH_LINE]},
        )
        self.assertEqual(status, 201)
        invoice_id = invoice["id"]
        self.assertTrue(invoice_id.startswith("inv-"))
        self.assertEqual(invoice["total_cents"], 5000)
        self.assertEqual(invoice["status"], "draft")

        invoice = self.transition(
            "/books/%s/invoices/%s/submit" % (book_id, invoice_id)
        )
        self.assertEqual(invoice["status"], "pending")
        invoice = self.transition(
            "/books/%s/invoices/%s/approve" % (book_id, invoice_id),
            headers=ALICE,
        )
        self.assertEqual(invoice["status"], "issued")

        status, _, payment = self.request(
            "POST", "/books/%s/invoices/%s/payments" % (book_id, invoice_id),
            headers=BOB,
            body={"amount_cents": 5000, "date": "2026-01-20",
                  "method": "wire"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(payment["id"].startswith("pay-"))
        self.assertEqual(payment["amount_cents"], 5000)

        status, _, invoice = self.request(
            "GET", "/books/%s/invoices/%s" % (book_id, invoice_id),
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        self.assertEqual(invoice["status"], "paid")
        self.assertEqual(invoice["paid_cents"], 5000)

    def test_list_and_get_book(self):
        """Core 11: API access + Core 1 Books. GET /books lists the
        caller's books as {"books": [...]}; GET /books/{id} returns
        one book dict."""
        book = self.create_book("listable-books")
        status, _, payload = self.request("GET", "/books", headers=BOB)
        self.assertEqual(status, 200)
        items = payload["books"] if isinstance(payload, dict) else payload
        self.assertIn(book["id"], [b["id"] for b in items])

        status, _, got = self.request(
            "GET", "/books/%s" % book["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], book["id"])
        self.assertEqual(got["name"], "listable-books")

    def test_entries_list_endpoint(self):
        """Core 11: API access + Core 3 Journal. GET
        /books/{id}/entries returns {"entries": [...]} and honours the
        status filter."""
        book = self.create_book("entries-books")
        cash, equity = self.create_chart(book["id"])
        entry = self.create_entry(book["id"], cash, equity)
        status, _, payload = self.request(
            "GET", "/books/%s/entries" % book["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [e["id"] for e in payload["entries"]], [entry["id"]]
        )
        status, _, payload = self.request(
            "GET", "/books/%s/entries?status=posted" % book["id"],
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])


class TestServiceAccessControl(ServiceBase):
    """Core 11/12: API access + access control over HTTP."""

    def test_viewer_creating_an_account_is_403(self):
        """Core 12: Access control (AC-3). A viewer book member POSTing
        an account -> 403 JSON {error} (viewer lacks enter)."""
        book = self.create_book("viewer-account-books")
        self.add_member(book["id"], "carol")
        status, _, parsed = self.request(
            "POST", "/books/%s/accounts" % book["id"], headers=CAROL,
            body={"code": "1000", "name": "Cash", "type": "asset"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_approving_an_entry_is_403(self):
        """Core 12: Access control (AC-3/AC-6). A viewer book member
        POSTing an entry approval -> 403 (viewer lacks approve)."""
        book = self.create_book("viewer-approve-books")
        self.add_member(book["id"], "carol")
        cash, equity = self.create_chart(book["id"])
        entry = self.create_entry(book["id"], cash, equity)
        self.transition(
            "/books/%s/entries/%s/submit" % (book["id"], entry["id"])
        )
        status, _, parsed = self.request(
            "POST",
            "/books/%s/entries/%s/approve" % (book["id"], entry["id"]),
            headers=CAROL, body={},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_creator_approving_own_entry_is_403_separation_of_duties(self):
        """Core 11/10: API access + workflow (AC-5). Over HTTP the SoD
        rule surfaces as 403: bob created and submitted the entry, so
        bob's own approve is denied and the entry stays pending."""
        book = self.create_book("sod-books")
        cash, equity = self.create_chart(book["id"])
        entry = self.create_entry(book["id"], cash, equity)
        self.transition(
            "/books/%s/entries/%s/submit" % (book["id"], entry["id"])
        )
        status, _, parsed = self.request(
            "POST",
            "/books/%s/entries/%s/approve" % (book["id"], entry["id"]),
            headers=BOB, body={},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        status, _, got = self.request(
            "GET", "/books/%s/entries/%s" % (book["id"], entry["id"]),
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["status"], "pending")

    def test_viewer_cannot_create_a_book(self):
        """Core 12: Access control. Viewer POST /books -> 403 (viewer
        lacks create_book)."""
        status, _, parsed = self.request(
            "POST", "/books", headers=CAROL, body={"name": "nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_get_unknown_book_is_404(self):
        """Core 11: API access. Unknown book id -> 404 JSON {error}."""
        status, _, parsed = self.request(
            "GET", "/books/book-999999", headers=ALICE
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


class TestServiceValidation(ServiceBase):
    """Core 11: API access — validation failures map to 400 (SI-10)."""

    def test_unbalanced_entry_over_http_is_400_and_creates_nothing(self):
        """Core 11 + Core 3: API access + journal (SI-10). An
        unbalanced entry POST -> 400 JSON {error}, and the book's
        entry list stays empty — the rejection is whole."""
        book = self.create_book("unbalanced-books")
        cash, equity = self.create_chart(book["id"])
        lines = [
            {"account_id": cash["id"], "debit_cents": 10000},
            {"account_id": equity["id"], "credit_cents": 9999},
        ]
        status, _, parsed = self.request(
            "POST", "/books/%s/entries" % book["id"], headers=BOB,
            body={"date": "2026-01-05", "memo": "Off by one",
                  "lines": lines},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, payload = self.request(
            "GET", "/books/%s/entries" % book["id"], headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])

    def test_income_statement_without_period_is_400(self):
        """Core 11 + Core 9: API access + reporting. Contract: GET
        income-statement requires a period — 'a missing period ->
        400'."""
        book = self.create_book("statement-books")
        status, _, parsed = self.request(
            "GET", "/books/%s/reports/income-statement" % book["id"],
            headers=BOB,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request(
            "GET",
            "/books/%s/reports/income-statement?period=2026-01"
            % book["id"],
            headers=BOB,
        )
        self.assertEqual(status, 200)
        self.assertEqual(parsed["period"], "2026-01")
        self.assertEqual(parsed["net_income_cents"], 0)


class TestServiceAudit(ServiceBase):
    """Core 11/13: API access + audit log over HTTP."""

    def test_audit_endpoint_is_admin_only(self):
        """Core 13: Audit log (AU-6). Contract: GET /audit requires
        audit_read — a member (and a viewer) get 403, the admin gets
        200 with {"entries": [...]}."""
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

    def test_denied_attempt_appears_in_audit_with_denied_suffix(self):
        """Core 13: Audit log. Contract: 'denied attempts (401 and
        403) are audited with the action name suffixed :denied' —
        after carol's 403 account-creation attempt, the admin's audit
        read contains a carol entry whose action ends with :denied."""
        book = self.create_book("denied-books")
        self.add_member(book["id"], "carol")

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
            "POST", "/books/%s/accounts" % book["id"], headers=CAROL,
            body={"code": "1000", "name": "Cash", "type": "asset"},
        )
        self.assertEqual(status, 403)
        self.assertGreater(carol_denied_count(), before)


if __name__ == "__main__":
    unittest.main()
