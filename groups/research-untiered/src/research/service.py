"""HTTP service exposing the research functions over a JSON REST API.

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
from .errors import NotFoundError, PermissionDenied, ResearchError, ValidationError


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
    server_version = "Research/0.1"
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
        except ResearchError as exc:
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
        now = _first_param(params, "now")

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            self._audit(user.name, "audit_read", "audit")
            return 200, {"entries": self.audit.entries() if self.audit else []}

        if parts == ["search"] and method == "GET":
            return 200, store.search(user, _first_param(params, "q") or "")

        if parts == ["commons"] and method == "POST":
            commons = store.create_commons(
                user, body.get("name"), body.get("title"), body.get("kind"),
                body.get("sponsor_ref"))
            return 201, commons
        if parts == ["commons"] and method == "GET":
            return 200, {"commons": store.list_commons(user)}
        if len(parts) == 2 and parts[0] == "commons" and method == "GET":
            return 200, store.get_commons(user, parts[1])
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "members" and method == "POST":
            return 200, store.add_member(user, parts[1], body.get("username"))
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "activate" and method == "POST":
            return 200, store.activate_commons(user, parts[1])
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "retire" and method == "POST":
            return 200, store.retire_commons(user, parts[1])
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "summary" and method == "GET":
            return 200, store.commons_summary(user, parts[1], now=now)

        if parts == ["organizations"] and method == "POST":
            return 201, store.create_organization(user, body.get("ref"), body.get("label"))
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}
        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(user, parts[1])
        if len(parts) == 2 and parts[0] == "organizations" and method == "POST":
            return 200, store.update_organization(user, parts[1], body.get("label"))

        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "workspaces" and method == "POST":
            workspace = store.create_workspace(
                user, parts[1], body.get("name"), body.get("purpose"))
            return 201, workspace
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "workspaces" and method == "GET":
            return 200, {"workspaces": store.list_workspaces(user, parts[1])}
        if len(parts) == 2 and parts[0] == "workspaces" and method == "GET":
            return 200, store.get_workspace(user, parts[1])

        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "datasets" and method == "POST":
            dataset = store.register_dataset(
                user, parts[1], body.get("name"), body.get("description"),
                body.get("access_tier"), body.get("sha256"), body.get("size_bytes"))
            return 201, dataset
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "datasets" and method == "GET":
            return 200, {"datasets": store.list_datasets(
                user, parts[1], access_tier=_first_param(params, "access_tier"))}
        if len(parts) == 2 and parts[0] == "datasets" and method == "GET":
            return 200, store.get_dataset(user, parts[1])
        if len(parts) == 3 and parts[0] == "datasets" and parts[2] == "verify" and method == "POST":
            content = body.get("content")
            if isinstance(content, str):
                content = content.encode("utf-8")
            return 200, store.verify_dataset(user, parts[1], content)

        if len(parts) == 3 and parts[0] == "datasets" and parts[2] == "access-requests" and method == "POST":
            request = store.create_access_request(
                user, parts[1], body.get("purpose"), body.get("duration_days"))
            return 201, request
        if len(parts) == 3 and parts[0] == "datasets" and parts[2] == "access-requests" and method == "GET":
            return 200, {"access_requests": store.list_access_requests(user, parts[1])}
        if len(parts) == 2 and parts[0] == "access-requests" and method == "GET":
            return 200, store.get_access_request(user, parts[1])
        if len(parts) == 3 and parts[0] == "access-requests" and method == "POST":
            request_id, verb = parts[1], parts[2]
            if verb == "decide":
                result = store.decide_access_request(
                    user, request_id, body.get("approve"),
                    note=body.get("note", ""), starts_at=body.get("starts_at"))
                return 201, result
            if verb == "withdraw":
                return 200, store.withdraw_access_request(user, request_id)

        if len(parts) == 2 and parts[0] == "grants" and method == "GET":
            return 200, store.get_grant(user, parts[1], now=now)
        if len(parts) == 3 and parts[0] == "commons" and parts[2] == "grants" and method == "GET":
            return 200, {"grants": store.list_grants(
                user, parts[1], status=_first_param(params, "status"), now=now)}
        if len(parts) == 3 and parts[0] == "grants" and parts[2] == "revoke" and method == "POST":
            return 200, store.revoke_grant(user, parts[1])

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the research HTTP server."""
    handler = type("ResearchHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
