"""HTTP service exposing the erp store as a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers against a fixed user registry
supplied at construction; the presented role must match the
registry entry. Denied attempts are audited (action name with a
``:denied`` suffix), as are successful audit-log reads.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import ErpError, NotFoundError, PermissionDenied, ValidationError
from .store import ErpStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("organizations",), "register", "_create_organization"),
    ("GET", ("organizations",), "read", "_list_organizations"),
    ("GET", ("organizations", "{id}"), "read", "_get_organization"),
    ("POST", ("applications",), "register", "_create_application"),
    ("GET", ("applications",), "read", "_list_applications"),
    ("POST", ("applications", "{id}", "deactivate"), "register",
     "_deactivate_application"),
    ("POST", ("access-configs",), "register", "_create_access_config"),
    ("GET", ("access-configs",), "read", "_list_access_configs"),
    ("POST", ("access-configs", "{id}", "deactivate"), "register",
     "_deactivate_access_config"),
    ("POST", ("ledger-entries",), "record", "_create_ledger_entry"),
    ("GET", ("ledger-entries",), "read", "_list_ledger_entries"),
    ("GET", ("ledger-entries", "{id}"), "read", "_get_ledger_entry"),
    ("POST", ("purchase-orders",), "record", "_create_purchase_order"),
    ("GET", ("purchase-orders",), "read", "_list_purchase_orders"),
    ("GET", ("purchase-orders", "{id}"), "read", "_get_purchase_order"),
    ("POST", ("purchase-orders", "{id}", "transition"), "approve",
     "_transition_purchase_order"),
    ("POST", ("expense-reports",), "record", "_create_expense_report"),
    ("GET", ("expense-reports",), "read", "_list_expense_reports"),
    ("GET", ("expense-reports", "{id}"), "read", "_get_expense_report"),
    ("POST", ("expense-reports", "{id}", "outcome"), "approve",
     "_expense_outcome"),
    ("POST", ("persons",), "record", "_create_person"),
    ("GET", ("persons",), "read", "_list_persons"),
    ("GET", ("persons", "{id}"), "read", "_get_person"),
    ("POST", ("time-entries",), "record", "_create_time_entry"),
    ("GET", ("time-entries",), "read", "_list_time_entries"),
    ("POST", ("absence-records",), "record", "_create_absence"),
    ("GET", ("absence-records",), "read", "_list_absences"),
    ("POST", ("payroll-runs",), "record", "_create_payroll_run"),
    ("GET", ("payroll-runs",), "read", "_list_payroll_runs"),
    ("POST", ("assets",), "record", "_create_asset"),
    ("GET", ("assets",), "read", "_list_assets"),
    ("GET", ("assets", "{id}"), "read", "_get_asset"),
    ("POST", ("work-orders",), "record", "_create_work_order"),
    ("GET", ("work-orders",), "read", "_list_work_orders"),
    ("POST", ("work-orders", "{id}", "transition"), "record",
     "_transition_work_order"),
    ("POST", ("inventory",), "record", "_create_inventory_item"),
    ("GET", ("inventory",), "read", "_list_inventory"),
    ("POST", ("inventory", "{id}", "adjust"), "record",
     "_adjust_inventory"),
    ("POST", ("documents",), "record", "_create_document"),
    ("GET", ("documents",), "read", "_list_documents"),
    ("POST", ("integrations",), "register", "_create_integration"),
    ("GET", ("integrations",), "read", "_list_integrations"),
    ("POST", ("integrations", "{id}", "deactivate"), "register",
     "_deactivate_integration"),
    ("POST", ("workflows",), "register", "_create_workflow"),
    ("GET", ("workflows",), "read", "_list_workflows"),
    ("POST", ("workflows", "{id}", "deactivate"), "register",
     "_deactivate_workflow"),
    ("GET", ("search",), "read", "_search"),
    ("GET", ("summary",), "read", "_summary"),
    ("GET", ("audit",), "audit_read", "_audit"),
]


def _match(pattern, parts):
    """Match a path pattern against path segments; return id or None."""
    if len(pattern) != len(parts):
        return False
    ident = None
    for want, got in zip(pattern, parts):
        if want == "{id}":
            ident = got
        elif want != got:
            return False
    return ident if ident is not None else True


def make_server(host, port, store=None, audit=None, users=None,
                certfile=None, keyfile=None):
    """Build (but do not start) the HTTP server.

    ``users`` maps a username to its role; the default registry is
    ``alice=admin, bob=operator, carol=viewer`` for local
    demonstration. When ``certfile``/``keyfile`` are supplied the
    socket is wrapped in TLS.
    """
    if users is None:
        users = {"alice": "admin", "bob": "operator", "carol": "viewer"}
    if audit is None:
        audit = AuditLog()
    if store is None:
        store = ErpStore(audit=audit)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # -- plumbing ---------------------------------------------------

        def log_message(self, *args):  # keep test output clean
            pass

        def _send(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = self.headers.get("Content-Length")
            if length is None:
                return {}
            try:
                count = int(length)
            except ValueError:
                raise ValidationError("invalid Content-Length header")
            raw = self.rfile.read(count) if count > 0 else b""
            if not raw:
                return {}
            try:
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ValidationError("request body is not valid JSON")
            if not isinstance(data, dict):
                raise ValidationError("request body must be a JSON object")
            return data

        def _authenticate(self):
            name = self.headers.get("X-User")
            role = self.headers.get("X-Role")
            if not name or name not in users or users[name] != role:
                return None
            return User(name=name, role=role)

        # -- dispatch -----------------------------------------------------

        def _dispatch(self, method):
            parsed = urlparse(self.path)
            parts = tuple(unquote(p) for p in parsed.path.split("/") if p)
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            route = None
            ident = None
            for m, pattern, permission, handler_name in ROUTES:
                if m != method:
                    continue
                matched = _match(pattern, parts)
                if matched is not False:
                    route = (permission, handler_name)
                    ident = matched if isinstance(matched, str) else None
                    break
            if route is None:
                self._send(404, {"error": "not found: %s %s" % (method, parsed.path)})
                return
            permission, handler_name = route
            if permission is None:  # health is public
                getattr(self, handler_name)()
                return
            user = self._authenticate()
            if user is None:
                audit.record(self.headers.get("X-User") or "anonymous",
                             "%s:denied" % handler_name, parsed.path,
                             {"reason": "unauthenticated"})
                self._send(401, {"error": "authentication required"})
                return
            try:
                require(user, permission)
            except PermissionDenied as exc:
                audit.record(user.name, "%s:denied" % handler_name,
                             parsed.path, {"reason": str(exc)})
                self._send(403, {"error": str(exc)})
                return
            try:
                getattr(self, handler_name)(user, ident, query)
            except NotFoundError as exc:
                self._send(404, {"error": str(exc)})
            except ValidationError as exc:
                self._send(400, {"error": str(exc)})
            except PermissionDenied as exc:
                audit.record(user.name, "%s:denied" % handler_name,
                             parsed.path, {"reason": str(exc)})
                self._send(403, {"error": str(exc)})
            except ErpError as exc:
                self._send(400, {"error": str(exc)})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        # -- handlers -------------------------------------------------------

        def _health(self):
            self._send(200, {"status": "ok"})

        def _create_organization(self, user, ident, query):
            body = self._read_body()
            organization = store.create_organization(
                user, body.get("ref"), body.get("label"))
            self._send(201, organization)

        def _list_organizations(self, user, ident, query):
            self._send(200, {"organizations": store.list_organizations(user)})

        def _get_organization(self, user, ident, query):
            self._send(200, store.get_organization(user, ident))

        def _create_application(self, user, ident, query):
            body = self._read_body()
            application = store.create_application(
                user, body.get("org_id"), body.get("app_ref"),
                body.get("label"), body.get("suite_label"))
            self._send(201, application)

        def _list_applications(self, user, ident, query):
            applications = store.list_applications(
                user, org_id=query.get("org_id"), status=query.get("status"))
            self._send(200, {"applications": applications})

        def _deactivate_application(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_application(user, ident))

        def _create_access_config(self, user, ident, query):
            body = self._read_body()
            config = store.create_access_config(
                user, body.get("org_id"), body.get("provider_label"),
                body.get("mfa_label"))
            self._send(201, config)

        def _list_access_configs(self, user, ident, query):
            configs = store.list_access_configs(
                user, org_id=query.get("org_id"), status=query.get("status"))
            self._send(200, {"access_configs": configs})

        def _deactivate_access_config(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_access_config(user, ident))

        def _create_ledger_entry(self, user, ident, query):
            body = self._read_body()
            entry = store.create_ledger_entry(
                user, body.get("org_id"), body.get("entry_ref"),
                body.get("memo_label"), body.get("lines"))
            self._send(201, entry)

        def _list_ledger_entries(self, user, ident, query):
            entries = store.list_ledger_entries(
                user, org_id=query.get("org_id"))
            self._send(200, {"ledger_entries": entries})

        def _get_ledger_entry(self, user, ident, query):
            self._send(200, store.get_ledger_entry(user, ident))

        def _create_purchase_order(self, user, ident, query):
            body = self._read_body()
            order = store.create_purchase_order(
                user, body.get("org_id"), body.get("po_ref"),
                body.get("supplier_ref"), body.get("lines"))
            self._send(201, order)

        def _list_purchase_orders(self, user, ident, query):
            orders = store.list_purchase_orders(
                user, org_id=query.get("org_id"), status=query.get("status"))
            self._send(200, {"purchase_orders": orders})

        def _get_purchase_order(self, user, ident, query):
            self._send(200, store.get_purchase_order(user, ident))

        def _transition_purchase_order(self, user, ident, query):
            body = self._read_body()
            order = store.transition_purchase_order(
                user, ident, body.get("status"))
            self._send(200, order)

        def _create_expense_report(self, user, ident, query):
            body = self._read_body()
            report = store.create_expense_report(
                user, body.get("org_id"), body.get("person_ref"),
                body.get("report_ref"), body.get("lines"))
            self._send(201, report)

        def _list_expense_reports(self, user, ident, query):
            reports = store.list_expense_reports(
                user, org_id=query.get("org_id"), status=query.get("status"))
            self._send(200, {"expense_reports": reports})

        def _get_expense_report(self, user, ident, query):
            self._send(200, store.get_expense_report(user, ident))

        def _expense_outcome(self, user, ident, query):
            body = self._read_body()
            report = store.record_expense_outcome(
                user, ident, body.get("outcome"), note=body.get("note"))
            self._send(200, report)

        def _create_person(self, user, ident, query):
            body = self._read_body()
            person = store.create_person(
                user, body.get("org_id"), body.get("person_ref"),
                body.get("department_label"), body.get("role_label"))
            self._send(201, person)

        def _list_persons(self, user, ident, query):
            persons = store.list_persons(user, org_id=query.get("org_id"))
            self._send(200, {"persons": persons})

        def _get_person(self, user, ident, query):
            self._send(200, store.get_person(user, ident))

        def _create_time_entry(self, user, ident, query):
            body = self._read_body()
            entry = store.create_time_entry(
                user, body.get("org_id"), body.get("person_ref"),
                body.get("work_date"), body.get("minutes"))
            self._send(201, entry)

        def _list_time_entries(self, user, ident, query):
            entries = store.list_time_entries(
                user, org_id=query.get("org_id"),
                person_ref=query.get("person_ref"))
            self._send(200, {"time_entries": entries})

        def _create_absence(self, user, ident, query):
            body = self._read_body()
            absence = store.create_absence(
                user, body.get("org_id"), body.get("person_ref"),
                body.get("kind_label"), body.get("from_date"),
                body.get("to_date"))
            self._send(201, absence)

        def _list_absences(self, user, ident, query):
            absences = store.list_absences(
                user, org_id=query.get("org_id"),
                person_ref=query.get("person_ref"))
            self._send(200, {"absence_records": absences})

        def _create_payroll_run(self, user, ident, query):
            body = self._read_body()
            run = store.create_payroll_run(
                user, body.get("org_id"), body.get("person_ref"),
                body.get("run_ref"), body.get("period_label"),
                body.get("gross_cents"))
            self._send(201, run)

        def _list_payroll_runs(self, user, ident, query):
            runs = store.list_payroll_runs(
                user, org_id=query.get("org_id"),
                person_ref=query.get("person_ref"))
            self._send(200, {"payroll_runs": runs})

        def _create_asset(self, user, ident, query):
            body = self._read_body()
            asset = store.create_asset(
                user, body.get("org_id"), body.get("asset_ref"),
                body.get("label"), body.get("criticality_label"))
            self._send(201, asset)

        def _list_assets(self, user, ident, query):
            assets = store.list_assets(user, org_id=query.get("org_id"))
            self._send(200, {"assets": assets})

        def _get_asset(self, user, ident, query):
            self._send(200, store.get_asset(user, ident))

        def _create_work_order(self, user, ident, query):
            body = self._read_body()
            order = store.create_work_order(
                user, body.get("org_id"), body.get("asset_id"),
                body.get("wo_ref"), body.get("kind"))
            self._send(201, order)

        def _list_work_orders(self, user, ident, query):
            orders = store.list_work_orders(
                user, org_id=query.get("org_id"),
                asset_id=query.get("asset_id"), status=query.get("status"))
            self._send(200, {"work_orders": orders})

        def _transition_work_order(self, user, ident, query):
            body = self._read_body()
            order = store.transition_work_order(
                user, ident, body.get("action"),
                assignee_ref=body.get("assignee_ref"))
            self._send(200, order)

        def _create_inventory_item(self, user, ident, query):
            body = self._read_body()
            item = store.create_inventory_item(
                user, body.get("org_id"), body.get("item_ref"),
                body.get("label"), body.get("quantity"))
            self._send(201, item)

        def _list_inventory(self, user, ident, query):
            items = store.list_inventory_items(
                user, org_id=query.get("org_id"))
            self._send(200, {"inventory": items})

        def _adjust_inventory(self, user, ident, query):
            body = self._read_body()
            item = store.adjust_inventory(user, ident, body.get("delta"))
            self._send(200, item)

        def _create_document(self, user, ident, query):
            body = self._read_body()
            document = store.create_document(
                user, body.get("org_id"), body.get("doc_ref"),
                body.get("label"), body.get("purpose_label"))
            self._send(201, document)

        def _list_documents(self, user, ident, query):
            documents = store.list_documents(
                user, org_id=query.get("org_id"))
            self._send(200, {"documents": documents})

        def _create_integration(self, user, ident, query):
            body = self._read_body()
            integration = store.create_integration(
                user, body.get("org_id"), body.get("kind"),
                body.get("label"))
            self._send(201, integration)

        def _list_integrations(self, user, ident, query):
            integrations = store.list_integrations(
                user, org_id=query.get("org_id"), kind=query.get("kind"))
            self._send(200, {"integrations": integrations})

        def _deactivate_integration(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_integration(user, ident))

        def _create_workflow(self, user, ident, query):
            body = self._read_body()
            workflow = store.create_workflow(
                user, body.get("org_id"), body.get("label"),
                body.get("trigger_label"))
            self._send(201, workflow)

        def _list_workflows(self, user, ident, query):
            workflows = store.list_workflows(
                user, org_id=query.get("org_id"), status=query.get("status"))
            self._send(200, {"workflows": workflows})

        def _deactivate_workflow(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_workflow(user, ident))

        def _search(self, user, ident, query):
            self._send(200, store.search(user, query.get("q")))

        def _summary(self, user, ident, query):
            self._send(200, store.summary(user))

        def _audit(self, user, ident, query):
            result = store.audit_read(user)
            audit.record(user.name, "audit_read", "/audit",
                         {"count": result["count"]})
            self._send(200, result)

    server = ThreadingHTTPServer((host, port), Handler)
    server.store = store
    server.audit = audit
    server.users = dict(users)
    if certfile and keyfile:
        import ssl

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
