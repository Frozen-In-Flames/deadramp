"""HTTP service layer over :class:`manufacturing.store.ManufacturingStore`.

Clean-room implementation. A REST router with a route table,
per-route permission enforcement, and a JSON response envelope.
Errors are always JSON of the form ``{"error": ...}`` -- never a
stack trace.

Authentication is an embedder seam, deliberately minimal: the
caller must send ``X-User`` / ``X-Role`` headers matching a user
in the server's registry. Demo identities are hooks, not an
identity provider.
"""

import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .access import ROLES, User
from .audit import AuditLog
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import ManufacturingStore


# ---------------------------------------------------------------------------
# Handlers -- (store, user, body, path_params, query) -> (status, payload)


def _health(store, user, body, params, query):
    return 200, {"status": "ok", "service": "manufacturing"}


def _list_organizations(store, user, body, params, query):
    return 200, {"organizations": store.list_organizations(user)}


def _create_organization(store, user, body, params, query):
    organization = store.create_organization(
        user, body.get("ref"), body.get("label"))
    return 201, organization


def _get_organization(store, user, body, params, query):
    return 200, store.get_organization(user, params["id"])


def _list_intents(store, user, body, params, query):
    intents = store.list_intents(
        user,
        org_id=query.get("org_id", [None])[0],
        status=query.get("status", [None])[0])
    return 200, {"intents": intents}


def _record_intent(store, user, body, params, query):
    intent = store.record_intent(
        user, body.get("org_id"), body.get("label"),
        body.get("statement"), body.get("author_ref"))
    return 201, intent


def _get_intent(store, user, body, params, query):
    return 200, store.get_intent(user, params["id"])


def _list_decisions(store, user, body, params, query):
    decisions = store.list_decisions(
        user,
        org_id=query.get("org_id", [None])[0],
        intent_id=query.get("intent_id", [None])[0])
    return 200, {"decisions": decisions}


def _record_decision(store, user, body, params, query):
    decision = store.record_decision(
        user, body.get("org_id"), body.get("label"),
        body.get("statement"), body.get("basis_intent_ids"),
        body.get("decided_by_ref"), decided_at=body.get("decided_at"))
    return 201, decision


def _get_decision(store, user, body, params, query):
    return 200, store.get_decision(user, params["id"])


def _search(store, user, body, params, query):
    q = query.get("q", [None])[0]
    if q is None:
        raise ValidationError("query parameter 'q' is required")
    return 200, store.search(user, q)


def _summary(store, user, body, params, query):
    return 200, store.summary(user)


def _audit(store, user, body, params, query):
    return 200, store.audit_read(user)


# ---------------------------------------------------------------------------
# Route table -- (method, path pattern, permission, handler)

ROUTES = [
    ("GET", ("health",), None, _health),
    ("GET", ("organizations",), "read", _list_organizations),
    ("POST", ("organizations",), "register", _create_organization),
    ("GET", ("organizations", "{id}"), "read", _get_organization),
    ("GET", ("intents",), "read", _list_intents),
    ("POST", ("intents",), "intents", _record_intent),
    ("GET", ("intents", "{id}"), "read", _get_intent),
    ("GET", ("decisions",), "read", _list_decisions),
    ("POST", ("decisions",), "decisions", _record_decision),
    ("GET", ("decisions", "{id}"), "read", _get_decision),
    ("GET", ("search",), "read", _search),
    ("GET", ("summary",), "read", _summary),
    ("GET", ("audit",), "audit_read", _audit),
]


def _match(method, segments):
    """Find a route for (method, path segments).

    Returns (permission, handler, params) or None. A literal path
    segment always wins over a ``{param}`` segment, so e.g. a
    concrete endpoint can never be shadowed by an id capture.
    """
    literal = []
    parameterized = []
    for route_method, pattern, permission, handler in ROUTES:
        if route_method != method or len(pattern) != len(segments):
            continue
        entry = (pattern, permission, handler)
        if any(seg.startswith("{") for seg in pattern):
            parameterized.append(entry)
        else:
            literal.append(entry)
    for pattern, permission, handler in literal + parameterized:
        params = {}
        ok = True
        for want, got in zip(pattern, segments):
            if want.startswith("{"):
                params[want[1:-1]] = got
            elif want != got:
                ok = False
                break
        if ok:
            return permission, handler, params
    return None


class _Handler(BaseHTTPRequestHandler):
    server_version = "manufacturing/0.1"
    protocol_version = "HTTP/1.1"

    # -- plumbing ---------------------------------------------------------

    def log_message(self, format, *args):  # noqa: A002 - stdlib name
        pass

    def _send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("request body is not valid JSON")
        if not isinstance(body, dict):
            raise ValidationError("request body must be a JSON object")
        return body

    def _authenticate(self):
        """Resolve X-User / X-Role headers against the user registry.

        The headers must name a registered user *with that user's
        role*. Anything else (missing headers, unknown user, role
        mismatch, unknown role) is rejected by raising
        :class:`PermissionDenied`, so a caller can never self-assign
        a role the registry did not give them.
        """
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        if not name or not role:
            raise PermissionDenied(
                "missing X-User / X-Role authentication headers")
        registered = self.server.users.get(name)
        if registered is None or registered.role != role:
            raise PermissionDenied("unknown user or role mismatch")
        return registered

    def _audit_denied(self, handler_name, status, detail):
        audit = getattr(self.server, "audit", None)
        if audit is not None:
            try:
                audit.record(self.headers.get("X-User"),
                             "%s:denied" % handler_name,
                             self.path, {"status": status, "detail": detail})
            except Exception:
                pass

    # -- routing ------------------------------------------------------------

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        segments = tuple(s for s in parsed.path.split("/") if s)
        query = parse_qs(parsed.query)
        try:
            body = self._read_body() if method in ("POST", "PUT", "PATCH") else {}
        except ValidationError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        matched = _match(method, segments)
        if matched is None:
            # Distinguish "no such path" from "path exists, wrong method".
            if any(len(pattern) == len(segments)
                   and all(w == g or w.startswith("{")
                           for w, g in zip(pattern, segments))
                   for _, pattern, _, _ in ROUTES):
                self._send_json(405, {"error": "method not allowed"})
            else:
                self._send_json(404, {"error": "not found"})
            return
        permission, handler, params = matched
        if permission is None:  # public route (health)
            try:
                status, payload = handler(
                    self.server.store, None, body, params, query)
            except Exception as exc:  # pragma: no cover - defensive
                self._send_json(500, {"error": "internal error: %s" % exc})
                return
            self._send_json(status, payload)
            return
        try:
            user = self._authenticate()
        except PermissionDenied as exc:
            self._audit_denied(handler.__name__, 401, str(exc))
            self._send_json(401, {"error": str(exc)})
            return
        # Service-layer permission enforcement: the store also
        # enforces when handed a User, but the HTTP 403 contract (and
        # its audit entry) lives here so a denial is recorded even if
        # a store method were reached with a string actor elsewhere.
        from .access import permissions_for

        if permission not in permissions_for(user.role):
            detail = (
                "permission denied: user %r with role %r may not "
                "perform %r" % (user.name, user.role, permission))
            self._audit_denied(handler.__name__, 403, detail)
            self._send_json(403, {"error": detail})
            return
        try:
            status, payload = handler(
                self.server.store, user, body, params, query)
        except PermissionDenied as exc:
            self._audit_denied(handler.__name__, 403, str(exc))
            self._send_json(403, {"error": str(exc)})
            return
        except NotFoundError as exc:
            self._send_json(404, {"error": str(exc)})
            return
        except ValidationError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        # Record reads of the audit log itself in the audit log.
        if handler is _audit and getattr(self.server, "audit", None) is not None:
            try:
                self.server.audit.record(user, "audit_read", "/audit",
                                         {"count": payload.get("count")})
            except Exception:
                pass
        self._send_json(status, payload)

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


def make_server(host, port, store=None, audit=None, users=None,
                certfile=None, keyfile=None):
    """Build (but do not start) the HTTP server.

    ``users`` maps user names to :class:`manufacturing.access.User`
    objects. ``certfile`` / ``keyfile`` enable HTTPS when both are
    given; passing only one is a configuration error.
    """
    if (certfile is None) != (keyfile is None):
        raise ValidationError("certfile and keyfile must be given together")
    server = ThreadingHTTPServer((host, port), _Handler)
    server.store = store if store is not None else ManufacturingStore()
    server.audit = audit if audit is not None else getattr(server.store, "audit", None)
    registry = {}
    for user in (users or {}).values():
        if not isinstance(user, User):
            raise ValidationError("users must map names to User objects")
        if user.role not in ROLES:
            raise ValidationError("unknown role: %r" % (user.role,))
        registry[user.name] = user
    server.users = registry
    if certfile is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
