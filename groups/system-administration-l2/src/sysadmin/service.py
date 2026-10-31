"""HTTP service exposing the sysadmin functions over a JSON REST API.

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
from .errors import NotFoundError, PermissionDenied, SysadminError, ValidationError


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
    server_version = "Sysadmin/0.1"
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
        except SysadminError as exc:
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

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "systems" and method == "POST":
            system = store.create_system(
                user, parts[1], body.get("ref"), body.get("label"),
                body.get("kind"), body.get("platform_ref"))
            return 201, system
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "systems" and method == "GET":
            return 200, {"systems": store.list_systems(
                user, parts[1], kind=_first_param(params, "kind"),
                state=_first_param(params, "state"))}
        if len(parts) == 2 and parts[0] == "systems" and method == "GET":
            return 200, store.get_system(user, parts[1])
        if len(parts) == 3 and parts[0] == "systems" and parts[2] == "retire" and method == "POST":
            return 200, store.retire_system(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "applications" and method == "POST":
            application = store.create_application(
                user, parts[1], body.get("system_id"), body.get("ref"),
                body.get("label"))
            return 201, application
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "applications" and method == "GET":
            return 200, {"applications": store.list_applications(
                user, parts[1], system_id=_first_param(params, "system_id"),
                state=_first_param(params, "state"))}
        if len(parts) == 2 and parts[0] == "applications" and method == "GET":
            return 200, store.get_application(user, parts[1])
        if len(parts) == 3 and parts[0] == "applications" and parts[2] == "retire" and method == "POST":
            return 200, store.retire_application(user, parts[1])

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "requests" and method == "POST":
            request = store.create_request(
                user, parts[1], body.get("system_id"),
                body.get("request_kind"), body.get("summary"),
                body.get("due_date"), application_id=body.get("application_id"))
            return 201, request
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "requests" and method == "GET":
            return 200, {"requests": store.list_requests(
                user, parts[1], as_of=_first_param(params, "as_of"),
                status=_first_param(params, "status"),
                system_id=_first_param(params, "system_id"))}
        if len(parts) == 2 and parts[0] == "requests" and method == "GET":
            return 200, store.get_request(
                user, parts[1], as_of=_first_param(params, "as_of"))
        if len(parts) == 3 and parts[0] == "requests" and method == "POST":
            request_id, verb = parts[1], parts[2]
            if verb == "start":
                return 200, store.start_request(user, request_id)
            if verb == "resolve":
                return 200, store.resolve_request(user, request_id)
            if verb == "cancel":
                return 200, store.cancel_request(user, request_id)

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "changes" and method == "POST":
            change = store.create_change(
                user, parts[1], body.get("system_id"),
                body.get("change_kind"), body.get("summary"),
                application_id=body.get("application_id"))
            return 201, change
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "changes" and method == "GET":
            return 200, {"changes": store.list_changes(
                user, parts[1], status=_first_param(params, "status"))}
        if len(parts) == 2 and parts[0] == "changes" and method == "GET":
            return 200, store.get_change(user, parts[1])
        if len(parts) == 3 and parts[0] == "changes" and method == "POST":
            change_id, verb = parts[1], parts[2]
            if verb == "decide":
                return 200, store.decide_change(
                    user, change_id, body.get("approve"))
            if verb == "close":
                return 200, store.close_change(user, change_id)
            if verb == "cancel":
                return 200, store.cancel_change(user, change_id)

        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "controls" and method == "POST":
            control = store.create_control(
                user, parts[1], body.get("system_id"),
                body.get("control_ref"), body.get("source"),
                note=body.get("note") or "")
            return 201, control
        if len(parts) == 3 and parts[0] == "organizations" and parts[2] == "controls" and method == "GET":
            return 200, {"controls": store.list_controls(
                user, parts[1], system_id=_first_param(params, "system_id"),
                source=_first_param(params, "source"))}
        if len(parts) == 2 and parts[0] == "controls" and method == "GET":
            return 200, store.get_control(user, parts[1])

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the sysadmin HTTP server."""
    handler = type("SysadminHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
