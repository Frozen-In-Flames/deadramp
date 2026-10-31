"""HTTP service exposing the travel functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
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
from .errors import NotFoundError, PermissionDenied, TravelError, ValidationError


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
    server_version = "Travel/0.1"
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

    # -- audit / auth -------------------------------------------------------

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

    # -- dispatch -----------------------------------------------------------

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
            self._audit_denied(self.headers.get("X-User") or "anonymous",
                               action, target)
            self._error(403, exc)
        except NotFoundError as exc:
            self._error(404, exc)
        except ValidationError as exc:
            self._error(400, exc)
        except TravelError as exc:
            self._error(400, exc)
        except Exception as exc:  # never leak a stack trace
            self._error(500, "internal error: %s" % (exc,))

    @staticmethod
    def _route_name(method, parts):
        label = "/".join(parts) if parts else "root"
        return "%s %s" % (method.lower(), label), label

    # -- routes ---------------------------------------------------------------

    def _route(self, method, parts, params, user, body):
        store = self.store
        now = _first_param(params, "now")

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            self._audit(user.name, "audit_read", "audit")
            return 200, {"entries": self.audit.entries() if self.audit else []}

        if parts == ["search"] and method == "GET":
            org_id = _first_param(params, "org_id")
            query = _first_param(params, "q") or ""
            return 200, store.search(user, org_id, query)

        if parts == ["organizations"] and method == "POST":
            org = store.create_organization(user, body.get("ref"),
                                            body.get("label"))
            return 201, org
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}

        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(user, parts[1])
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "members" and method == "POST":
            org = store.add_member(user, parts[1], body.get("username"))
            return 200, org
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "members" and method == "GET":
            return 200, {"members": store.list_members(user, parts[1])}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "summary" and method == "GET":
            return 200, store.summary(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "travelers" and method == "POST":
            traveler = store.create_traveler(user, parts[1],
                                             body.get("traveler_ref"),
                                             body.get("label"))
            return 201, traveler
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "travelers" and method == "GET":
            return 200, {"travelers": store.list_travelers(user, parts[1])}
        if len(parts) == 2 and parts[0] == "travelers" and method == "GET":
            return 200, store.get_traveler(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "authorizations" and method == "POST":
            auth = store.create_authorization(
                user, parts[1], body.get("traveler_id"),
                body.get("destination_label"), body.get("purpose"),
                body.get("depart_date"), body.get("return_date"),
                body.get("authorized_cents"))
            return 201, auth
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "authorizations" and method == "GET":
            return 200, {"authorizations":
                         store.list_authorizations(user, parts[1], as_of=now)}
        if len(parts) == 2 and parts[0] == "authorizations" and method == "GET":
            return 200, store.get_authorization(user, parts[1], as_of=now)
        if len(parts) == 3 and parts[0] == "authorizations" \
                and parts[2] == "submit" and method == "POST":
            return 200, store.submit_authorization(user, parts[1])
        if len(parts) == 3 and parts[0] == "authorizations" \
                and parts[2] == "decide" and method == "POST":
            result = store.decide_authorization(user, parts[1],
                                                body.get("approve"),
                                                body.get("note", ""))
            return 200, result
        if len(parts) == 3 and parts[0] == "authorizations" \
                and parts[2] == "decisions" and method == "GET":
            return 200, {"decisions":
                         store.list_decisions(user,
                                              store.get_authorization(
                                                  user, parts[1])["org_id"],
                                              target_id=parts[1])}

        if len(parts) == 3 and parts[0] == "authorizations" \
                and parts[2] == "expense-reports" and method == "POST":
            report = store.create_expense_report(user, parts[1],
                                                 body.get("title"))
            return 201, report
        if len(parts) == 3 and parts[0] == "authorizations" \
                and parts[2] == "expense-reports" and method == "GET":
            return 200, {"expense_reports":
                         store.list_expense_reports(user, parts[1])}
        if len(parts) == 2 and parts[0] == "expense-reports" and method == "GET":
            return 200, store.get_expense_report(user, parts[1])
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "items" and method == "POST":
            item = store.add_expense_item(user, parts[1],
                                          body.get("category"),
                                          body.get("amount_cents"),
                                          body.get("item_date"),
                                          body.get("note", ""))
            return 201, item
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "items" and method == "GET":
            return 200, {"items": store.list_expense_items(user, parts[1])}
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "submit" and method == "POST":
            return 200, store.submit_expense_report(user, parts[1])
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "decide" and method == "POST":
            result = store.decide_expense_report(user, parts[1],
                                                 body.get("approve"),
                                                 body.get("note", ""))
            return 200, result
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "vouchers" and method == "POST":
            voucher = store.record_voucher(user, parts[1],
                                           body.get("amount_cents"),
                                           body.get("note", ""))
            return 201, voucher
        if len(parts) == 3 and parts[0] == "expense-reports" \
                and parts[2] == "vouchers" and method == "GET":
            return 200, {"vouchers": store.list_vouchers(user, parts[1])}

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "notifications" and method == "POST":
            note_rec = store.create_notification(
                user, parts[1], body.get("kind"), body.get("recipient_ref"),
                body.get("target_kind", ""), body.get("target_id", ""),
                body.get("note", ""))
            return 201, note_rec
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "notifications" and method == "GET":
            return 200, {"notifications":
                         store.list_notifications(user, parts[1])}

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "integrations" and method == "POST":
            integration = store.register_integration(
                user, parts[1], body.get("name"), body.get("kind"),
                body.get("target_label"))
            return 201, integration
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "integrations" and method == "GET":
            return 200, {"integrations":
                         store.list_integrations(user, parts[1])}

        raise NotFoundError("no such route: %s /%s"
                            % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build the HTTP server with its store, audit log, and user registry."""
    handler = type("TravelHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = users
    return ThreadingHTTPServer((host, port), handler)
