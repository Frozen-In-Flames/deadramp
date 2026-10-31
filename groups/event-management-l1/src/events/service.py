"""HTTP service exposing the events store as a JSON REST API.

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
from .errors import EventsError, NotFoundError, PermissionDenied, ValidationError
from .store import EventsStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("organizers",), "register", "_create_organizer"),
    ("GET", ("organizers",), "read", "_list_organizers"),
    ("GET", ("organizers", "{id}"), "read", "_get_organizer"),
    ("POST", ("vendors",), "register", "_create_vendor"),
    ("GET", ("vendors",), "read", "_list_vendors"),
    ("GET", ("vendors", "{id}"), "read", "_get_vendor"),
    ("POST", ("events",), "manage", "_create_event"),
    ("GET", ("events",), "read", "_list_events"),
    ("GET", ("events", "{id}"), "read", "_get_event"),
    ("POST", ("events", "{id}", "preparation"), "manage",
     "_add_preparation_task"),
    ("GET", ("events", "{id}", "preparation"), "read",
     "_list_preparation_tasks"),
    ("POST", ("preparation", "{id}", "complete"), "manage",
     "_complete_preparation_task"),
    ("POST", ("sessions",), "manage", "_create_session"),
    ("GET", ("sessions",), "read", "_list_sessions"),
    ("GET", ("sessions", "{id}"), "read", "_get_session"),
    ("POST", ("outreach",), "outreach", "_record_outreach"),
    ("GET", ("outreach",), "read", "_list_outreach"),
    ("POST", ("rounds",), "matchmake", "_create_round"),
    ("GET", ("rounds",), "read", "_list_rounds"),
    ("GET", ("rounds", "{id}"), "read", "_get_round"),
    ("POST", ("rounds", "{id}", "close"), "matchmake", "_close_round"),
    ("POST", ("rounds", "{id}", "participations"), "matchmake",
     "_record_participation"),
    ("GET", ("rounds", "{id}", "participations"), "read",
     "_list_participations"),
    ("GET", ("rounds", "{id}", "matches"), "read", "_round_matches"),
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
    ``alice=admin, bob=member, carol=viewer`` for local
    demonstration. When ``certfile``/``keyfile`` are supplied the
    socket is wrapped in TLS.
    """
    if users is None:
        users = {"alice": "admin", "bob": "member", "carol": "viewer"}
    if audit is None:
        audit = AuditLog()
    if store is None:
        store = EventsStore(audit=audit)

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
            except EventsError as exc:
                self._send(400, {"error": str(exc)})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        # -- handlers -------------------------------------------------------

        def _health(self):
            self._send(200, {"status": "ok"})

        def _create_organizer(self, user, ident, query):
            body = self._read_body()
            party = store.create_organizer(user, body.get("ref"), body.get("label"))
            self._send(201, party)

        def _list_organizers(self, user, ident, query):
            self._send(200, {"organizers": store.list_organizers(user)})

        def _get_organizer(self, user, ident, query):
            self._send(200, store.get_organizer(user, ident))

        def _create_vendor(self, user, ident, query):
            body = self._read_body()
            party = store.create_vendor(user, body.get("ref"), body.get("label"))
            self._send(201, party)

        def _list_vendors(self, user, ident, query):
            self._send(200, {"vendors": store.list_vendors(user)})

        def _get_vendor(self, user, ident, query):
            self._send(200, store.get_vendor(user, ident))

        def _create_event(self, user, ident, query):
            body = self._read_body()
            event = store.create_event(
                user, body.get("organizer_id"), body.get("title"),
                body.get("format"), body.get("starts_at"),
                body.get("ends_at"),
                location_note=body.get("location_note"))
            self._send(201, event)

        def _list_events(self, user, ident, query):
            events = store.list_events(
                user, organizer_id=query.get("organizer_id"),
                format=query.get("format"), status=query.get("status"),
                now=query.get("now"))
            self._send(200, {"events": events})

        def _get_event(self, user, ident, query):
            self._send(200, store.get_event(user, ident, now=query.get("now")))

        def _add_preparation_task(self, user, ident, query):
            body = self._read_body()
            task = store.add_preparation_task(user, ident, body.get("label"))
            self._send(201, task)

        def _list_preparation_tasks(self, user, ident, query):
            done = query.get("done")
            tasks = store.list_preparation_tasks(
                user, ident,
                done=None if done is None else done.lower() == "true")
            self._send(200, {"preparation_tasks": tasks})

        def _complete_preparation_task(self, user, ident, query):
            self._read_body()
            self._send(200, store.complete_preparation_task(user, ident))

        def _create_session(self, user, ident, query):
            body = self._read_body()
            session = store.create_session(
                user, body.get("event_id"), body.get("kind"),
                body.get("title"), body.get("starts_at"),
                body.get("ends_at"), speaker_ref=body.get("speaker_ref"))
            self._send(201, session)

        def _list_sessions(self, user, ident, query):
            sessions = store.list_sessions(
                user, event_id=query.get("event_id"),
                kind=query.get("kind"), status=query.get("status"),
                now=query.get("now"))
            self._send(200, {"sessions": sessions})

        def _get_session(self, user, ident, query):
            self._send(200, store.get_session(user, ident, now=query.get("now")))

        def _record_outreach(self, user, ident, query):
            body = self._read_body()
            outreach = store.record_outreach(
                user, body.get("organizer_id"), body.get("vendor_id"),
                body.get("event_id"), body.get("channel"),
                body.get("subject"))
            self._send(201, outreach)

        def _list_outreach(self, user, ident, query):
            outreach = store.list_outreach(
                user, organizer_id=query.get("organizer_id"),
                vendor_id=query.get("vendor_id"),
                event_id=query.get("event_id"))
            self._send(200, {"outreach": outreach})

        def _create_round(self, user, ident, query):
            body = self._read_body()
            round_ = store.create_round(
                user, body.get("event_id"), body.get("required_tags"))
            self._send(201, round_)

        def _list_rounds(self, user, ident, query):
            rounds = store.list_rounds(
                user, event_id=query.get("event_id"),
                status=query.get("status"))
            self._send(200, {"rounds": rounds})

        def _get_round(self, user, ident, query):
            self._send(200, store.get_round(user, ident))

        def _close_round(self, user, ident, query):
            self._read_body()
            self._send(200, store.close_round(user, ident))

        def _record_participation(self, user, ident, query):
            body = self._read_body()
            participation = store.record_participation(
                user, ident, body.get("vendor_id"),
                body.get("capability_tags"))
            self._send(201, participation)

        def _list_participations(self, user, ident, query):
            self._send(200, {"participations":
                             store.list_participations(user, ident)})

        def _round_matches(self, user, ident, query):
            self._send(200, store.round_matches(user, ident))

        def _search(self, user, ident, query):
            self._send(200, store.search(user, query.get("q")))

        def _summary(self, user, ident, query):
            self._send(200, store.summary(user, now=query.get("now")))

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
