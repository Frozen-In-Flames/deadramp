"""HTTP service exposing the Legal & Policy functions over a JSON
REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
provider.

Digest discipline: this layer is the only place query text may
appear. A ``query_text`` request field is SHA-256-hashed here,
before the store is called; the text itself is never stored, logged,
or audited. The store has no parameter that could accept it.

The store records every successful mutation. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and ``audit_read``.
Errors are JSON ``{error: msg}`` with 400 (validation), 401 (auth),
403 (permission) or 404 (not found); handlers never leak a stack
trace to the client.
"""

import base64
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .errors import LegalPolError, NotFoundError, PermissionDenied, ValidationError

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
    server_version = "LegalPol/0.1"
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
        except LegalPolError as exc:
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

        if parts == ["library"] and method == "GET":
            return 200, {"sources": store.list_library_sources(
                user, kind=_first_param(params, "kind"))}
        if parts == ["library"] and method == "POST":
            source = store.register_library_source(
                body.get("source_ref"), body.get("kind"), user,
                title=body.get("title"),
                jurisdiction_ref=body.get("jurisdiction_ref"))
            return 201, source

        if parts == ["agencies"] and method == "POST":
            return 201, store.create_agency(
                body.get("agency_ref"), body.get("label"), user)
        if parts == ["agencies"] and method == "GET":
            return 200, {"agencies": store.list_agencies(user)}
        if len(parts) == 2 and parts[0] == "agencies" and method == "GET":
            return 200, store.get_agency(parts[1], user)
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "members" \
                and method == "POST":
            return 200, store.add_member(parts[1], body.get("username"), user)

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "workspaces" \
                and method == "POST":
            workspace = store.create_workspace(
                parts[1], body.get("workspace_ref"), body.get("title"), user)
            return 201, workspace
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "workspaces" \
                and method == "GET":
            return 200, {"workspaces": store.list_workspaces(parts[1], user)}

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "sessions" \
                and method == "POST":
            session = store.create_session(
                parts[1], body.get("workspace_id"), body.get("session_ref"), user,
                purpose=body.get("purpose"),
                sandbox=body.get("sandbox", False),
                expires_at=body.get("expires_at"))
            return 201, session
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "sessions" \
                and method == "GET":
            return 200, {"sessions": store.list_sessions(
                parts[1], user, workspace_id=_first_param(params, "workspace_id"))}
        if len(parts) == 5 and parts[0] == "agencies" and parts[2] == "sessions" \
                and parts[4] == "close" and method == "POST":
            return 200, store.close_session(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "agencies" and parts[2] == "sessions" \
                and parts[4] == "executions" and method == "GET":
            return 200, {"executions": store.list_executions(
                parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "agencies" and parts[2] == "sessions" \
                and parts[4] == "executions" and method == "POST":
            execution = store.record_execution(
                parts[1], parts[3], body.get("execution_ref"), user,
                kind=body.get("kind", "code"), language=body.get("language"))
            return 201, execution

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "searches" \
                and method == "GET":
            return 200, {"searches": store.list_searches(
                parts[1], user, workspace_id=_first_param(params, "workspace_id"))}
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "searches" \
                and method == "POST":
            digest = body.get("query_sha256")
            if body.get("query_text") is not None:
                text = body["query_text"]
                if not isinstance(text, str):
                    raise ValidationError("query_text must be a string")
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            search = store.save_search(
                parts[1], body.get("search_ref"), digest,
                body.get("result_count"), user,
                workspace_id=body.get("workspace_id"))
            return 201, search

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "documents" \
                and method == "GET":
            return 200, {"documents": store.list_documents(
                parts[1], user, workspace_id=_first_param(params, "workspace_id"))}
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "documents" \
                and method == "POST":
            document = store.register_document(
                parts[1], body.get("workspace_id"), body.get("doc_ref"),
                body.get("sha256"), body.get("size_bytes"), user,
                kind=body.get("kind", "generated"),
                session_id=body.get("session_id"))
            return 201, document
        if len(parts) == 5 and parts[0] == "agencies" and parts[2] == "documents" \
                and parts[4] == "verify" and method == "POST":
            raw = body.get("content_b64")
            if not isinstance(raw, str):
                raise ValidationError("content_b64 must be a base64 string")
            try:
                content = base64.b64decode(raw.encode("ascii"), validate=True)
            except (ValueError, UnicodeEncodeError) as exc:
                raise ValidationError("content_b64 must be valid base64") from exc
            return 200, store.verify_document(parts[1], parts[3], content, user)

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "usage" \
                and method == "GET":
            return 200, {"usage": store.list_usage(
                parts[1], user, kind=_first_param(params, "kind"))}
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "usage" \
                and method == "POST":
            usage = store.record_usage(
                parts[1], body.get("usage_ref"), body.get("kind"),
                body.get("quantity"), user,
                session_id=body.get("session_id"),
                workspace_id=body.get("workspace_id"))
            return 201, usage

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "exports" \
                and method == "GET":
            return 200, {"exports": store.list_exports(parts[1], user)}
        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "exports" \
                and method == "POST":
            export = store.export_usage(
                parts[1], body.get("export_ref"), user,
                since=body.get("since"), until=body.get("until"))
            return 201, export

        if len(parts) == 3 and parts[0] == "agencies" and parts[2] == "report" \
                and method == "GET":
            return 200, store.agency_report(parts[1], user)

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the legalpol HTTP server."""
    handler = type("LegalPolHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
