"""HTTP service exposing the mdm functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
provider.

The store records every successful mutation. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and
``audit_read``. Errors are JSON ``{error: msg}`` with 400
(validation), 401 (auth), 403 (permission) or 404 (not found);
handlers never leak a stack trace to the client.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .errors import MdmError, NotFoundError, PermissionDenied, ValidationError


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
    server_version = "Mdm/0.1"
    protocol_version = "HTTP/1.1"

    # -- plumbing ---------------------------------------------------------

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

    # -- audit / auth ---------------------------------------------------------

    def _audit(self, actor, action, target):
        if self.audit is not None:
            self.audit.record(actor, action, target)

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _authenticate(self, action, target):
        """Return the User, or send 401 (audited as denied) and return None."""
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        if not name or self.users.get(name) is None or self.users.get(name) != role:
            self._audit_denied(name or "anonymous", action, target)
            self._error(401, "unauthorized")
            return None
        return User(name, role)

    # -- dispatch ----------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.split("/") if p != ""]
        params = parse_qs(parsed.query)
        action, target = self._route_name(method, parts)
        try:
            if parts == ["health"] and method == "GET":
                self._send_json(200, {"status": "ok"})
                return
            user = self._authenticate(action, target)
            if user is None:
                return
            body = self._read_json_body() if method == "POST" else {}
            status, payload = self._route(method, parts, params, user, body)
            self._send_json(status, payload)
        except PermissionDenied as exc:
            self._audit_denied(self.headers.get("X-User") or "anonymous", action, target)
            self._error(403, exc)
        except NotFoundError as exc:
            self._error(404, exc)
        except ValidationError as exc:
            self._error(400, exc)
        except MdmError as exc:
            self._error(400, exc)
        except Exception as exc:  # never leak a stack trace
            self._error(500, "internal error: %s" % (exc,))

    @staticmethod
    def _route_name(method, parts):
        label = "/".join(parts) if parts else "root"
        return "%s %s" % (method.lower(), label), label

    # -- routes -------------------------------------------------------------

    def _route(self, method, parts, params, user, body):
        store = self.store

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            self._audit(user.name, "audit_read", "audit")
            return 200, {"entries": self.audit.entries() if self.audit else []}

        if parts == ["search"] and method == "GET":
            return 200, store.search(user, _first_param(params, "q") or "")

        if parts == ["organizations"] and method == "POST":
            return 201, store.create_organization(
                user, body.get("ref"), body.get("label"))
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}
        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(user, parts[1])
        if len(parts) == 2 and parts[0] == "organizations" and method == "POST":
            return 200, store.update_organization(user, parts[1], body.get("label"))
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "members" and method == "POST":
            return 200, store.add_member(user, parts[1], body.get("username"))
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "summary" and method == "GET":
            return 200, store.organization_summary(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "inventory" and method == "POST":
            item = store.create_inventory_item(
                user, parts[1], body.get("ref"), body.get("service_kind"),
                body.get("label"), body.get("plan_ref"),
                body.get("monthly_recurring_cents"))
            return 201, item
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "inventory" and method == "GET":
            return 200, {"inventory": store.list_inventory(
                user, parts[1], service_kind=_first_param(params, "service_kind"),
                state=_first_param(params, "state"))}
        if len(parts) == 2 and parts[0] == "inventory" and method == "GET":
            return 200, store.get_inventory_item(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "orders" and method == "POST":
            order = store.create_order(
                user, parts[1], body.get("order_type"), body.get("detail"),
                inventory_id=body.get("inventory_id"))
            return 201, order
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "orders" and method == "GET":
            return 200, {"orders": store.list_orders(
                user, parts[1], status=_first_param(params, "status"))}
        if len(parts) == 2 and parts[0] == "orders" and method == "GET":
            return 200, store.get_order(user, parts[1])
        if len(parts) == 3 and parts[0] == "orders" and method == "POST":
            order_id, verb = parts[1], parts[2]
            if verb == "approve":
                return 200, store.decide_order(user, order_id, True)
            if verb == "reject":
                return 200, store.decide_order(user, order_id, False)
            if verb == "cancel":
                return 200, store.cancel_order(user, order_id)
            if verb == "fulfill":
                return 200, store.fulfill_order(user, order_id)

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "workflows" and method == "POST":
            return 201, store.create_workflow(
                user, parts[1], body.get("name"), body.get("steps"))
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "workflows" and method == "GET":
            return 200, {"workflows": store.list_workflows(user, parts[1])}
        if len(parts) == 2 and parts[0] == "workflows" and method == "GET":
            return 200, store.get_workflow(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "contracts" and method == "POST":
            contract = store.create_contract(
                user, parts[1], body.get("ref"), body.get("label"),
                body.get("starts_on"), ends_on=body.get("ends_on"))
            return 201, contract
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "contracts" and method == "GET":
            return 200, {"contracts": store.list_contracts(user, parts[1])}
        if len(parts) == 2 and parts[0] == "contracts" and method == "GET":
            return 200, store.get_contract(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "quotes" and method == "POST":
            quote = store.create_quote(
                user, parts[1], body.get("contract_id"), body.get("amount_cents"),
                inventory_id=body.get("inventory_id"), note=body.get("note", ""))
            return 201, quote
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "quotes" and method == "GET":
            return 200, {"quotes": store.list_quotes(user, parts[1])}

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "bills" and method == "POST":
            bill = store.create_bill(
                user, parts[1], body.get("contract_id"), body.get("period"),
                body.get("stated_cents"))
            return 201, bill
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "bills" and method == "GET":
            return 200, {"bills": store.list_bills(user, parts[1])}
        if len(parts) == 2 and parts[0] == "bills" and method == "GET":
            return 200, store.get_bill(user, parts[1])
        if len(parts) == 3 and parts[0] == "bills" and parts[2] == "validate" and method == "POST":
            return 201, store.validate_bill(user, parts[1])
        if len(parts) == 3 and parts[0] == "bills" and parts[2] == "validations" and method == "GET":
            return 200, {"validations": store.list_validations(user, parts[1])}
        if len(parts) == 3 and parts[0] == "bills" and parts[2] == "disputes" and method == "POST":
            dispute = store.create_dispute(
                user, parts[1], body.get("amount_cents"), body.get("reason"))
            return 201, dispute
        if len(parts) == 3 and parts[0] == "bills" and parts[2] == "disputes" and method == "GET":
            return 200, {"disputes": store.list_disputes(user, parts[1])}
        if len(parts) == 2 and parts[0] == "disputes" and method == "GET":
            return 200, store.get_dispute(user, parts[1])
        if len(parts) == 3 and parts[0] == "disputes" and method == "POST":
            dispute_id, verb = parts[1], parts[2]
            if verb == "start":
                return 200, store.start_dispute(user, dispute_id)
            if verb == "resolve":
                return 200, store.resolve_dispute(
                    user, dispute_id, body.get("resolution"))

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "budgets" and method == "POST":
            budget = store.create_budget(
                user, parts[1], body.get("period"), body.get("budget_cents"),
                projection_cents=body.get("projection_cents"),
                note=body.get("note", ""))
            return 201, budget
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "budgets" and method == "GET":
            return 200, {"budgets": store.list_budgets(user, parts[1])}
        if len(parts) == 2 and parts[0] == "budgets" and method == "GET":
            return 200, store.get_budget(user, parts[1])
        if len(parts) == 3 and parts[0] == "budgets" and parts[2] == "obligations" and method == "POST":
            obligation = store.record_obligation(
                user, parts[1], body.get("kind"), body.get("amount_cents"),
                note=body.get("note", ""))
            return 201, obligation
        if len(parts) == 3 and parts[0] == "budgets" and parts[2] == "obligations" and method == "GET":
            return 200, {"obligations": store.list_obligations(user, parts[1])}
        if len(parts) == 3 and parts[0] == "budgets" and parts[2] == "chargebacks" and method == "POST":
            chargeback = store.create_chargeback(
                user, parts[1], body.get("unit_ref"), body.get("amount_cents"),
                note=body.get("note", ""))
            return 201, chargeback
        if len(parts) == 3 and parts[0] == "budgets" and parts[2] == "chargebacks" and method == "GET":
            return 200, {"chargebacks": store.list_chargebacks(user, parts[1])}

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "alerts" and method == "POST":
            alert = store.create_alert(
                user, parts[1], body.get("kind"), body.get("message"),
                budget_id=body.get("budget_id"))
            return 201, alert
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "alerts" and method == "GET":
            return 200, {"alerts": store.list_alerts(user, parts[1])}
        if len(parts) == 3 and parts[0] == "alerts" and parts[2] == "acknowledge" and method == "POST":
            return 200, store.acknowledge_alert(user, parts[1])

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the mdm HTTP server."""
    handler = type("MdmHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
