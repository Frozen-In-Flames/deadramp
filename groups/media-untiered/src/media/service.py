"""HTTP service exposing the media store as a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers against a fixed user registry
supplied at construction; the presented role must match the
registry entry. Denied attempts are audited (action name with a
``:denied`` suffix), as are successful audit-log reads.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, permissions_for, require
from .audit import AuditLog
from .errors import MediaError, NotFoundError, PermissionDenied, ValidationError
from .store import MediaStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("organizations",), "register", "_create_organization"),
    ("GET", ("organizations",), "read", "_list_organizations"),
    ("GET", ("organizations", "{id}"), "read", "_get_organization"),
    ("POST", ("endpoints",), "register", "_create_endpoint"),
    ("GET", ("endpoints",), "read", "_list_endpoints"),
    ("GET", ("endpoints", "{id}"), "read", "_get_endpoint"),
    ("POST", ("routes",), "routes", "_create_route"),
    ("GET", ("routes",), "read", "_list_routes"),
    ("GET", ("routes", "{id}"), "read", "_get_route"),
    ("POST", ("sessions",), "sessions", "_start_session"),
    ("GET", ("sessions",), "read", "_list_sessions"),
    ("GET", ("sessions", "{id}"), "read", "_get_session"),
    ("POST", ("sessions", "{id}", "stop"), "sessions", "_stop_session"),
    ("POST", ("devices",), "devices", "_create_device"),
    ("GET", ("devices",), "read", "_list_devices"),
    ("GET", ("devices", "{id}"), "read", "_get_device"),
    ("POST", ("control-actions",), "control", "_record_control_action"),
    ("GET", ("control-actions",), "read", "_list_control_actions"),
    ("POST", ("profiles",), "optimize", "_create_profile"),
    ("GET", ("profiles",), "read", "_list_profiles"),
    ("POST", ("profiles", "{id}", "activation"), "optimize",
     "_set_profile_enabled"),
    ("POST", ("snapshots",), "monitor", "_record_snapshot"),
    ("GET", ("snapshots",), "read", "_list_snapshots"),
    ("GET", ("current-status",), "read", "_current_status"),
    ("GET", ("network-status",), "read", "_network_status"),
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
        store = MediaStore(audit=audit)

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
            except MediaError as exc:
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

        def _create_endpoint(self, user, ident, query):
            body = self._read_body()
            endpoint = store.create_endpoint(
                user, body.get("org_id"), body.get("ref"),
                body.get("label"), body.get("kind"))
            self._send(201, endpoint)

        def _list_endpoints(self, user, ident, query):
            endpoints = store.list_endpoints(
                user, org_id=query.get("org_id"), kind=query.get("kind"))
            self._send(200, {"endpoints": endpoints})

        def _get_endpoint(self, user, ident, query):
            self._send(200, store.get_endpoint(user, ident))

        def _create_route(self, user, ident, query):
            body = self._read_body()
            route = store.create_route(
                user, body.get("org_id"), body.get("label"),
                body.get("source_endpoint_id"),
                body.get("destination_endpoint_id"),
                encryption=body.get("encryption", "aes_256"),
                protocol_label=body.get("protocol_label"))
            self._send(201, route)

        def _list_routes(self, user, ident, query):
            routes = store.list_routes(
                user, org_id=query.get("org_id"), state=query.get("state"))
            self._send(200, {"routes": routes})

        def _get_route(self, user, ident, query):
            self._send(200, store.get_route(user, ident))

        def _start_session(self, user, ident, query):
            body = self._read_body()
            session = store.start_session(
                user, body.get("route_id"),
                started_at=body.get("started_at"))
            self._send(201, session)

        def _list_sessions(self, user, ident, query):
            sessions = store.list_sessions(
                user, route_id=query.get("route_id"),
                state=query.get("state"))
            self._send(200, {"sessions": sessions})

        def _get_session(self, user, ident, query):
            self._send(200, store.get_session(user, ident))

        def _stop_session(self, user, ident, query):
            body = self._read_body()
            session = store.stop_session(
                user, ident, stopped_at=body.get("stopped_at"))
            self._send(200, session)

        def _create_device(self, user, ident, query):
            body = self._read_body()
            device = store.create_device(
                user, body.get("org_id"), body.get("ref"),
                body.get("label"), kind_label=body.get("kind_label"),
                endpoint_id=body.get("endpoint_id"))
            self._send(201, device)

        def _list_devices(self, user, ident, query):
            devices = store.list_devices(user, org_id=query.get("org_id"))
            self._send(200, {"devices": devices})

        def _get_device(self, user, ident, query):
            self._send(200, store.get_device(user, ident))

        def _record_control_action(self, user, ident, query):
            body = self._read_body()
            control = store.record_control_action(
                user, body.get("device_id"), body.get("action"),
                note=body.get("note"), at=body.get("at"))
            self._send(201, control)

        def _list_control_actions(self, user, ident, query):
            controls = store.list_control_actions(
                user, device_id=query.get("device_id"),
                action=query.get("action"))
            self._send(200, {"control_actions": controls})

        def _create_profile(self, user, ident, query):
            body = self._read_body()
            profile = store.create_optimization_profile(
                user, body.get("org_id"), body.get("label"),
                body.get("settings_text"), route_id=body.get("route_id"),
                enabled=body.get("enabled", True))
            self._send(201, profile)

        def _list_profiles(self, user, ident, query):
            profiles = store.list_profiles(
                user, org_id=query.get("org_id"))
            self._send(200, {"profiles": profiles})

        def _set_profile_enabled(self, user, ident, query):
            body = self._read_body()
            profile = store.set_profile_enabled(
                user, ident, body.get("enabled"))
            self._send(200, profile)

        def _record_snapshot(self, user, ident, query):
            body = self._read_body()
            snapshot = store.record_status_snapshot(
                user, body.get("subject_kind"), body.get("subject_id"),
                body.get("status"), at=body.get("at"))
            self._send(201, snapshot)

        def _list_snapshots(self, user, ident, query):
            snapshots = store.list_snapshots(
                user, subject_kind=query.get("subject_kind"),
                subject_id=query.get("subject_id"))
            self._send(200, {"snapshots": snapshots})

        def _current_status(self, user, ident, query):
            result = store.current_status(
                user, query.get("subject_kind"), query.get("subject_id"))
            self._send(200, result)

        def _network_status(self, user, ident, query):
            result = store.network_status(user, query.get("org_id"))
            self._send(200, result)

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
