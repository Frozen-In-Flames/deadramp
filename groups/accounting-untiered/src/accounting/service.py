"""HTTP service exposing the accounting functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

The store records every successful mutation. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and ``audit_read``.
Errors are JSON ``{error: msg}`` with 400 (validation), 401 (auth),
403 (permission) or 404 (not found); handlers never leak a stack
trace to the client.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import AccountingError, NotFoundError, PermissionDenied, ValidationError


def _first_param(params, name):
    values = params.get(name)
    if not values:
        return None
    return values[0]


class _Handler(BaseHTTPRequestHandler):
    # Injected by make_server.
    store = None
    audit = None
    users = {}
    server_version = "Accounting/0.1"
    protocol_version = "HTTP/1.1"

    # -- plumbing -----------------------------------------------------

    def log_message(self, format, *args):  # noqa: A002 - stdlib name
        pass

    def _send(self, status, body, content_type):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, status, obj):
        self._send(status, json.dumps(obj), "application/json")

    def _error(self, status, message):
        self._send_json(status, {"error": str(message)})

    def _read_json_body(self):
        length = self.headers.get("Content-Length")
        if length is None:
            return {}
        try:
            size = int(length)
        except ValueError:
            raise ValidationError("invalid Content-Length")
        raw = self.rfile.read(size) if size > 0 else b""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValidationError("request body must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValidationError("request body must be a JSON object")
        return parsed

    def _read_optional_body(self):
        """Read a POST action body that may be empty; its content is ignored."""
        return self._read_json_body()

    # -- audit helpers --------------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            try:
                self.audit.record(actor, action, target, details=details)
            except Exception:
                pass  # Auditing must never break the request path.

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    # -- auth -------------------------------------------------------------

    def _authenticate(self, action, target):
        """Return the User, or send 401 (audited as denied) and return None."""
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        actor = name if name else "anonymous"
        if not name or not role or name not in self.users or self.users[name] != role:
            self._audit_denied(actor, action, target)
            self._error(401, "unauthorized")
            return None
        return User(name=name, role=role)

    def _authorize(self, user, action, target):
        """Return True, or send 403 (audited as denied) and return False."""
        try:
            require(user, action)
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
            return False
        return True

    # -- routing ------------------------------------------------------------

    def _route(self, method, parts):
        """Return (route, permission_action, ids) for a known route.

        ``permission_action`` is None only for ``POST /books/{id}/members``:
        any authenticated user may call it and the store enforces
        owner-or-admin. Returns (None, None, ()) for unknown routes.
        """
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if parts and parts[0] == "books":
            if len(parts) == 1:
                if method == "GET":
                    return ("book_list", "read", ())
                if method == "POST":
                    return ("book_create", "create_book", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("book_get", "read", (parts[1],))
            elif len(parts) == 3:
                book_id, sub = parts[1], parts[2]
                if method == "POST" and sub == "members":
                    return ("member_add", None, (book_id,))
                if method == "GET" and sub == "accounts":
                    return ("account_list", "read", (book_id,))
                if method == "POST" and sub == "accounts":
                    return ("account_create", "enter", (book_id,))
                if method == "GET" and sub == "entries":
                    return ("entry_list", "read", (book_id,))
                if method == "POST" and sub == "entries":
                    return ("entry_create", "enter", (book_id,))
                if method == "GET" and sub == "invoices":
                    return ("invoice_list", "read", (book_id,))
                if method == "POST" and sub == "invoices":
                    return ("invoice_create", "enter", (book_id,))
                if method == "GET" and sub == "payments":
                    return ("payment_list", "read", (book_id,))
                if method == "GET" and sub == "expenses":
                    return ("expense_list", "read", (book_id,))
                if method == "POST" and sub == "expenses":
                    return ("expense_create", "enter", (book_id,))
            elif len(parts) == 4:
                book_id, sub, item_id = parts[1], parts[2], parts[3]
                if method == "GET" and sub == "accounts":
                    return ("account_get", "read", (book_id, item_id))
                if method == "GET" and sub == "entries":
                    return ("entry_get", "read", (book_id, item_id))
                if method == "GET" and sub == "invoices":
                    return ("invoice_get", "read", (book_id, item_id))
                if method == "GET" and sub == "expenses":
                    return ("expense_get", "read", (book_id, item_id))
                if sub == "budgets":
                    if method == "PUT":
                        return ("budget_set", "enter", (book_id, item_id))
                    if method == "GET":
                        return ("budget_get", "read", (book_id, item_id))
                if sub == "reports":
                    if method == "GET" and item_id == "trial-balance":
                        return ("report_trial_balance", "read", (book_id,))
                    if method == "GET" and item_id == "income-statement":
                        return ("report_income_statement", "read", (book_id,))
                    if method == "GET" and item_id == "balance-sheet":
                        return ("report_balance_sheet", "read", (book_id,))
            elif len(parts) == 5:
                book_id, sub, item_id, tail = parts[1], parts[2], parts[3], parts[4]
                if sub == "accounts" and method == "GET" and tail == "balance":
                    return ("account_balance", "read", (book_id, item_id))
                if sub == "accounts" and method == "GET" and tail == "activity":
                    return ("account_activity", "read", (book_id, item_id))
                if sub == "accounts" and method == "POST" and tail == "reconcile":
                    return ("account_reconcile", "close", (book_id, item_id))
                if sub == "entries" and method == "POST":
                    if tail == "submit":
                        return ("entry_submit", "submit", (book_id, item_id))
                    if tail == "approve":
                        return ("entry_approve", "approve", (book_id, item_id))
                    if tail == "reject":
                        return ("entry_reject", "approve", (book_id, item_id))
                    if tail == "void":
                        return ("entry_void", "enter", (book_id, item_id))
                if sub == "invoices" and method == "POST":
                    if tail == "submit":
                        return ("invoice_submit", "submit", (book_id, item_id))
                    if tail == "approve":
                        return ("invoice_approve", "approve", (book_id, item_id))
                    if tail == "reject":
                        return ("invoice_reject", "approve", (book_id, item_id))
                    if tail == "void":
                        return ("invoice_void", "enter", (book_id, item_id))
                    if tail == "payments":
                        return ("payment_create", "pay", (book_id, item_id))
                if sub == "expenses" and method == "POST":
                    if tail == "submit":
                        return ("expense_submit", "submit", (book_id, item_id))
                    if tail == "approve":
                        return ("expense_approve", "approve", (book_id, item_id))
                    if tail == "reject":
                        return ("expense_reject", "approve", (book_id, item_id))
                    if tail == "void":
                        return ("expense_void", "enter", (book_id, item_id))
                    if tail == "reimburse":
                        return ("expense_reimburse", "pay", (book_id, item_id))
                if sub == "budgets" and method == "GET" and tail == "vs-actual":
                    return ("budget_vs_actual", "read", (book_id, item_id))
                if sub == "periods" and method == "POST" and tail == "close":
                    return ("period_close", "close", (book_id, item_id))
        return (None, None, ())

    # Action names used when auditing a denial for a route whose HTTP
    # permission differs from the operation name (or has none).
    _DENIAL_ACTION = {"member_add": "member_add"}

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [unquote(p) for p in path.split("/") if p != ""]
        route, action, ids = self._route(method, parts)
        denial_action = self._DENIAL_ACTION.get(route, action)
        target = ids[-1] if ids else path
        try:
            if route is None:
                self._error(404, "not found")
                return
            if route == "health":
                self._send_json(200, {"status": "ok"})
                return

            user = self._authenticate(denial_action, target)
            if user is None:
                return
            if action is not None and not self._authorize(user, action, target):
                return

            self._execute(route, user, ids, parsed)
        except ValidationError as exc:
            self._safe_error(400, exc)
        except PermissionDenied as exc:
            # A store-raised denial: audit it here (the store audits
            # successes only, so this is recorded exactly once).
            actor = self.headers.get("X-User") or "anonymous"
            if denial_action:
                self._audit_denied(actor, denial_action, target)
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except AccountingError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    # -- endpoint handlers ---------------------------------------------------

    def _execute(self, route, user, ids, parsed):
        store = self.store
        params = parse_qs(parsed.query)
        if route == "audit_read":
            entries = self.audit.entries() if self.audit is not None else []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "book_list":
            self._send_json(200, {"books": store.list_books(user)})
            return
        if route == "book_create":
            body = self._read_json_body()
            book = store.create_book(body.get("name"), user)
            self._send_json(201, book)
            return
        if route == "book_get":
            self._send_json(200, store.get_book(ids[0], user))
            return
        if route == "member_add":
            body = self._read_json_body()
            book = store.add_member(ids[0], body.get("username"), user)
            self._send_json(200, book)
            return
        if route == "account_list":
            self._send_json(200, {"accounts": store.list_accounts(ids[0], user)})
            return
        if route == "account_create":
            body = self._read_json_body()
            account = store.create_account(
                ids[0], body.get("code"), body.get("name"), body.get("type"), user
            )
            self._send_json(201, account)
            return
        if route == "account_get":
            self._send_json(200, store.get_account(ids[0], ids[1], user))
            return
        if route == "account_balance":
            period = _first_param(params, "period")
            self._send_json(
                200, store.account_balance(ids[0], ids[1], user, period=period)
            )
            return
        if route == "account_activity":
            period = _first_param(params, "period")
            self._send_json(
                200, store.account_activity(ids[0], ids[1], user, period=period)
            )
            return
        if route == "account_reconcile":
            body = self._read_json_body()
            record = store.reconcile_account(
                ids[0], ids[1], body.get("period"), body.get("expected_balance_cents"), user
            )
            self._send_json(201, record)
            return
        if route == "entry_list":
            status = _first_param(params, "status")
            entries = store.list_entries(ids[0], user, status=status)
            self._send_json(200, {"entries": entries})
            return
        if route == "entry_create":
            body = self._read_json_body()
            memo = body.get("memo", "")
            if memo is None:
                memo = ""
            entry = store.create_entry(ids[0], body.get("date"), memo, body.get("lines"), user)
            self._send_json(201, entry)
            return
        if route == "entry_get":
            self._send_json(200, store.get_entry(ids[0], ids[1], user))
            return
        if route == "entry_submit":
            self._read_optional_body()
            self._send_json(200, store.submit_entry(ids[0], ids[1], user))
            return
        if route == "entry_approve":
            self._read_optional_body()
            self._send_json(200, store.approve_entry(ids[0], ids[1], user))
            return
        if route == "entry_reject":
            self._read_optional_body()
            self._send_json(200, store.reject_entry(ids[0], ids[1], user))
            return
        if route == "entry_void":
            self._read_optional_body()
            self._send_json(200, store.void_entry(ids[0], ids[1], user))
            return
        if route == "invoice_list":
            status = _first_param(params, "status")
            invoices = store.list_invoices(ids[0], user, status=status)
            self._send_json(200, {"invoices": invoices})
            return
        if route == "invoice_create":
            body = self._read_json_body()
            invoice = store.create_invoice(
                ids[0],
                body.get("customer"),
                body.get("date"),
                body.get("due_date"),
                body.get("lines"),
                user,
            )
            self._send_json(201, invoice)
            return
        if route == "invoice_get":
            self._send_json(200, store.get_invoice(ids[0], ids[1], user))
            return
        if route == "invoice_submit":
            self._read_optional_body()
            self._send_json(200, store.submit_invoice(ids[0], ids[1], user))
            return
        if route == "invoice_approve":
            self._read_optional_body()
            self._send_json(200, store.approve_invoice(ids[0], ids[1], user))
            return
        if route == "invoice_reject":
            self._read_optional_body()
            self._send_json(200, store.reject_invoice(ids[0], ids[1], user))
            return
        if route == "invoice_void":
            self._read_optional_body()
            self._send_json(200, store.void_invoice(ids[0], ids[1], user))
            return
        if route == "payment_list":
            invoice_id = _first_param(params, "invoice_id")
            payments = store.list_payments(ids[0], user, invoice_id=invoice_id)
            self._send_json(200, {"payments": payments})
            return
        if route == "payment_create":
            body = self._read_json_body()
            method = body.get("method", "")
            if method is None:
                method = ""
            payment = store.record_payment(
                ids[0], ids[1], body.get("amount_cents"), body.get("date"), user, method=method
            )
            self._send_json(201, payment)
            return
        if route == "expense_list":
            status = _first_param(params, "status")
            expenses = store.list_expenses(ids[0], user, status=status)
            self._send_json(200, {"expenses": expenses})
            return
        if route == "expense_create":
            body = self._read_json_body()
            expense = store.create_expense(
                ids[0],
                body.get("date"),
                body.get("category"),
                body.get("description"),
                body.get("amount_cents"),
                user,
            )
            self._send_json(201, expense)
            return
        if route == "expense_get":
            self._send_json(200, store.get_expense(ids[0], ids[1], user))
            return
        if route == "expense_submit":
            self._read_optional_body()
            self._send_json(200, store.submit_expense(ids[0], ids[1], user))
            return
        if route == "expense_approve":
            self._read_optional_body()
            self._send_json(200, store.approve_expense(ids[0], ids[1], user))
            return
        if route == "expense_reject":
            self._read_optional_body()
            self._send_json(200, store.reject_expense(ids[0], ids[1], user))
            return
        if route == "expense_void":
            self._read_optional_body()
            self._send_json(200, store.void_expense(ids[0], ids[1], user))
            return
        if route == "expense_reimburse":
            self._read_optional_body()
            self._send_json(200, store.reimburse_expense(ids[0], ids[1], user))
            return
        if route == "budget_set":
            body = self._read_json_body()
            budget = store.set_budget(ids[0], ids[1], body.get("lines"), user)
            self._send_json(200, budget)
            return
        if route == "budget_get":
            self._send_json(200, store.get_budget(ids[0], ids[1], user))
            return
        if route == "budget_vs_actual":
            self._send_json(200, store.budget_vs_actual(ids[0], ids[1], user))
            return
        if route == "report_trial_balance":
            period = _first_param(params, "period")
            self._send_json(200, store.trial_balance(ids[0], user, period=period))
            return
        if route == "report_income_statement":
            period = _first_param(params, "period")
            if period is None:
                raise ValidationError("period is required")
            self._send_json(200, store.income_statement(ids[0], period, user))
            return
        if route == "report_balance_sheet":
            through = _first_param(params, "through_period")
            self._send_json(
                200, store.balance_sheet(ids[0], user, through_period=through)
            )
            return
        if route == "period_close":
            self._read_optional_body()
            self._send_json(200, store.close_period(ids[0], ids[1], user))
            return
        self._error(404, "not found")

    # -- verbs -----------------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")


def make_server(host, port, store, audit, users):
    """Create (but do not start) the accounting HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "AccountingHandler",
        (_Handler,),
        {
            "store": store,
            "audit": audit,
            "users": dict(users or {}),
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
