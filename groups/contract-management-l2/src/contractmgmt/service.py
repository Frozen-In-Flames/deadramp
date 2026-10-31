"""HTTP service exposing the Contract Management functions over a
JSON REST API.

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
from .errors import (
    ContractMgmtError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
}
DEMO_USERS = USERS


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
    server_version = "ContractMgmt/0.1"
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
        except ContractMgmtError as exc:
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
            return 200, store.search_registry(user, _first_param(params, "q") or "")

        if parts == ["participants"] and method == "GET":
            return 200, {"participants": store.list_participants(user)}
        if parts == ["participants"] and method == "POST":
            participant = store.register_participant(
                body.get("participant_ref"), body.get("label"), user)
            return 201, participant

        if parts == ["organizations"] and method == "POST":
            return 201, store.create_organization(
                body.get("org_ref"), body.get("label"), user)
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}
        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(parts[1], user)
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "members" and method == "POST":
            return 200, store.add_member(parts[1], body.get("username"), user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "contracts" and method == "POST":
            contract = store.create_contract(
                parts[1], body.get("contract_ref"), body.get("title"),
                body.get("counterparty_ref"), body.get("ceiling_cents"),
                body.get("award_cents"), user,
                period_start=body.get("period_start"),
                period_end=body.get("period_end"))
            return 201, contract
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "contracts" and method == "GET":
            return 200, {"contracts": store.list_contracts(parts[1], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "contracts" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_contract(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "contracts" and parts[4] == "modifications" \
                and method == "GET":
            return 200, {"modifications": store.list_modifications(
                parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "contracts" and parts[4] == "modifications" \
                and method == "POST":
            modification = store.record_modification(
                parts[1], parts[3], body.get("mod_ref"),
                body.get("amount_cents"), user, label=body.get("label"))
            return 201, modification

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "requirements" and method == "GET":
            return 200, {"requirements": store.list_requirements(
                parts[1], user, status=_first_param(params, "status"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "requirements" and method == "POST":
            requirement = store.create_requirement(
                parts[1], body.get("requirement_ref"), body.get("label"), user)
            return 201, requirement
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "requirements" and parts[4] == "satisfy" \
                and method == "POST":
            return 200, store.satisfy_requirement(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "requirements" and parts[4] == "waive" \
                and method == "POST":
            return 200, store.waive_requirement(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "protests" and method == "GET":
            return 200, {"protests": store.list_protests(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "protests" and method == "POST":
            protest = store.create_protest(
                parts[1], body.get("protest_ref"), body.get("label"),
                body.get("due_at"), user,
                contract_id=body.get("contract_id"),
                opportunity_id=body.get("opportunity_id"))
            return 201, protest
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "protests" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_protest(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "datacalls" and method == "GET":
            return 200, {"datacalls": store.list_datacalls(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "datacalls" and method == "POST":
            datacall = store.create_datacall(
                parts[1], body.get("datacall_ref"), body.get("requester_ref"),
                body.get("label"), body.get("due_at"), user)
            return 201, datacall
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "datacalls" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_datacall(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "risks" and method == "GET":
            return 200, {"risks": store.list_risks(
                parts[1], user,
                contract_id=_first_param(params, "contract_id"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "risks" and method == "POST":
            risk = store.create_risk(
                parts[1], body.get("risk_ref"), body.get("label"), user,
                contract_id=body.get("contract_id"))
            return 201, risk
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "risks" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_risk(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "communications" and method == "GET":
            return 200, {"communications": store.list_communications(
                parts[1], user, direction=_first_param(params, "direction"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "communications" and method == "POST":
            communication = store.record_communication(
                parts[1], body.get("comm_ref"), body.get("counterparty_ref"),
                body.get("direction"), body.get("label"), user)
            return 201, communication

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and method == "GET":
            return 200, {"opportunities": store.list_opportunities(
                parts[1], user, kind=_first_param(params, "kind"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and method == "POST":
            opportunity = store.create_opportunity(
                parts[1], body.get("opportunity_ref"), body.get("title"),
                body.get("kind"), user,
                audience=body.get("audience", "public"),
                directed_to=body.get("directed_to"),
                closes_at=body.get("closes_at"))
            return 201, opportunity
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_opportunity(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and parts[4] == "submissions" \
                and method == "GET":
            return 200, {"submissions": store.list_submissions(
                parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and parts[4] == "submissions" \
                and method == "POST":
            submission = store.record_submission(
                parts[1], parts[3], body.get("submission_ref"),
                body.get("participant_ref"), user)
            return 201, submission
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and parts[4] == "awards" \
                and method == "GET":
            return 200, {"awards": store.list_awards(parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "opportunities" and parts[4] == "awards" \
                and method == "POST":
            award = store.record_award(
                parts[1], parts[3], body.get("submission_id"),
                body.get("award_ref"), body.get("amount_cents"), user)
            return 201, award

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "payments" and method == "GET":
            return 200, {"payments": store.list_payments(
                parts[1], user, kind=_first_param(params, "kind"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "payments" and method == "POST":
            payment = store.record_payment(
                parts[1], body.get("payment_ref"), body.get("kind"),
                body.get("amount_cents"), user,
                opportunity_id=body.get("opportunity_id"),
                award_id=body.get("award_id"))
            return 201, payment

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "workflows" and method == "GET":
            return 200, {"workflows": store.list_workflows(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "workflows" and method == "POST":
            workflow = store.register_workflow(
                parts[1], body.get("workflow_ref"), body.get("label"), user)
            return 201, workflow

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "integrations" and method == "GET":
            return 200, {"integrations": store.list_integrations(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "integrations" and method == "POST":
            integration = store.register_integration(
                parts[1], body.get("integration_ref"), body.get("system_ref"),
                body.get("label"), user)
            return 201, integration

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "report" and method == "GET":
            return 200, store.org_report(parts[1], user)

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the contractmgmt HTTP server."""
    handler = type("ContractMgmtHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
