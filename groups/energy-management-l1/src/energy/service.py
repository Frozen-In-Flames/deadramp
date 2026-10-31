"""HTTP service exposing the energy store as a JSON REST API.

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
from .errors import EnergyError, NotFoundError, PermissionDenied, ValidationError
from .store import EnergyStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("customers",), "register", "_create_customer"),
    ("GET", ("customers",), "read", "_list_customers"),
    ("GET", ("customers", "{id}"), "read", "_get_customer"),
    ("POST", ("providers",), "register", "_create_provider"),
    ("GET", ("providers",), "read", "_list_providers"),
    ("GET", ("providers", "{id}"), "read", "_get_provider"),
    ("POST", ("auctions",), "conduct", "_create_auction"),
    ("GET", ("auctions",), "read", "_list_auctions"),
    ("GET", ("auctions", "{id}"), "read", "_get_auction"),
    ("POST", ("auctions", "{id}", "close"), "conduct", "_close_auction"),
    ("POST", ("auctions", "{id}", "bids"), "conduct", "_record_bid"),
    ("GET", ("auctions", "{id}", "bids"), "read", "_list_bids"),
    ("GET", ("auctions", "{id}", "outcome"), "read", "_auction_outcome"),
    ("POST", ("observations",), "observe", "_record_observation"),
    ("GET", ("observations",), "read", "_list_observations"),
    ("POST", ("subscriptions",), "alert", "_create_subscription"),
    ("POST", ("subscriptions", "{id}", "deactivate"), "alert",
     "_deactivate_subscription"),
    ("GET", ("subscriptions",), "read", "_list_subscriptions"),
    ("POST", ("alerts",), "alert", "_record_alert"),
    ("GET", ("alerts",), "read", "_list_alerts"),
    ("POST", ("engagements",), "advise", "_create_engagement"),
    ("GET", ("engagements",), "read", "_list_engagements"),
    ("GET", ("engagements", "{id}"), "read", "_get_engagement"),
    ("POST", ("engagements", "{id}", "close"), "advise", "_close_engagement"),
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
        store = EnergyStore(audit=audit)

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
            except EnergyError as exc:
                self._send(400, {"error": str(exc)})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        # -- handlers -------------------------------------------------------

        def _health(self):
            self._send(200, {"status": "ok"})

        def _create_customer(self, user, ident, query):
            body = self._read_body()
            party = store.create_customer(user, body.get("ref"), body.get("label"))
            self._send(201, party)

        def _list_customers(self, user, ident, query):
            self._send(200, {"customers": store.list_customers(user)})

        def _get_customer(self, user, ident, query):
            self._send(200, store.get_customer(user, ident))

        def _create_provider(self, user, ident, query):
            body = self._read_body()
            party = store.create_provider(user, body.get("ref"), body.get("label"))
            self._send(201, party)

        def _list_providers(self, user, ident, query):
            self._send(200, {"providers": store.list_providers(user)})

        def _get_provider(self, user, ident, query):
            self._send(200, store.get_provider(user, ident))

        def _create_auction(self, user, ident, query):
            body = self._read_body()
            auction = store.create_auction(
                user, body.get("customer_id"), body.get("commodity"),
                body.get("region"), body.get("unit_label"),
                body.get("quantity_units"), body.get("opens_at"),
                body.get("closes_at"))
            self._send(201, auction)

        def _list_auctions(self, user, ident, query):
            auctions = store.list_auctions(
                user, customer_id=query.get("customer_id"),
                status=query.get("status"), now=query.get("now"))
            self._send(200, {"auctions": auctions})

        def _get_auction(self, user, ident, query):
            self._send(200, store.get_auction(user, ident, now=query.get("now")))

        def _close_auction(self, user, ident, query):
            body = self._read_body()
            self._send(200, store.close_auction(
                user, ident, closed_at=body.get("closed_at")))

        def _record_bid(self, user, ident, query):
            body = self._read_body()
            bid = store.record_bid(
                user, ident, body.get("provider_id"),
                body.get("price_cents_per_unit"), at=body.get("at"))
            self._send(201, bid)

        def _list_bids(self, user, ident, query):
            self._send(200, {"bids": store.list_bids(user, ident)})

        def _auction_outcome(self, user, ident, query):
            self._send(200, store.auction_outcome(
                user, ident, now=query.get("now")))

        def _record_observation(self, user, ident, query):
            body = self._read_body()
            observation = store.record_observation(
                user, body.get("region"), body.get("commodity"),
                body.get("price_cents_per_unit"),
                observed_at=body.get("observed_at"))
            self._send(201, observation)

        def _list_observations(self, user, ident, query):
            observations = store.list_observations(
                user, region=query.get("region"),
                commodity=query.get("commodity"))
            self._send(200, {"observations": observations})

        def _create_subscription(self, user, ident, query):
            body = self._read_body()
            subscription = store.create_subscription(
                user, body.get("customer_id"), body.get("kind"),
                threshold_cents_per_unit=body.get("threshold_cents_per_unit"),
                region=body.get("region"), commodity=body.get("commodity"))
            self._send(201, subscription)

        def _deactivate_subscription(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_subscription(user, ident))

        def _list_subscriptions(self, user, ident, query):
            active = query.get("active")
            subscriptions = store.list_subscriptions(
                user, customer_id=query.get("customer_id"),
                active=None if active is None else active.lower() == "true")
            self._send(200, {"subscriptions": subscriptions})

        def _record_alert(self, user, ident, query):
            body = self._read_body()
            alert = store.record_alert(
                user, body.get("customer_id"), body.get("kind"),
                body.get("subject"),
                subscription_id=body.get("subscription_id"))
            self._send(201, alert)

        def _list_alerts(self, user, ident, query):
            alerts = store.list_alerts(
                user, customer_id=query.get("customer_id"),
                kind=query.get("kind"))
            self._send(200, {"alerts": alerts})

        def _create_engagement(self, user, ident, query):
            body = self._read_body()
            engagement = store.create_engagement(
                user, body.get("customer_id"), body.get("kind"),
                body.get("note"))
            self._send(201, engagement)

        def _list_engagements(self, user, ident, query):
            engagements = store.list_engagements(
                user, customer_id=query.get("customer_id"),
                kind=query.get("kind"), status=query.get("status"))
            self._send(200, {"engagements": engagements})

        def _get_engagement(self, user, ident, query):
            self._send(200, store.get_engagement(user, ident))

        def _close_engagement(self, user, ident, query):
            self._read_body()
            self._send(200, store.close_engagement(user, ident))

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
