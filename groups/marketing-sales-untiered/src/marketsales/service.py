"""HTTP service exposing the marketsales store as a JSON REST API.

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
from .errors import (MarketSalesError, NotFoundError, PermissionDenied,
                     ValidationError)
from .store import MarketSalesStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("organizations",), "register", "_create_organization"),
    ("GET", ("organizations",), "read", "_list_organizations"),
    ("GET", ("organizations", "{id}"), "read", "_get_organization"),
    ("POST", ("opportunities",), "register", "_create_opportunity"),
    ("GET", ("opportunities",), "read", "_list_opportunities"),
    ("GET", ("opportunities", "{id}"), "read", "_get_opportunity"),
    ("POST", ("evaluations",), "evaluate", "_record_evaluation"),
    ("GET", ("evaluations",), "read", "_list_evaluations"),
    ("POST", ("pipeline",), "pipeline", "_create_pipeline_entry"),
    ("GET", ("pipeline",), "read", "_list_pipeline"),
    ("GET", ("pipeline", "{id}"), "read", "_get_pipeline_entry"),
    ("POST", ("pipeline", "{id}", "transition"), "pipeline",
     "_transition_pipeline"),
    ("POST", ("content",), "propose", "_create_content_version"),
    ("GET", ("content",), "read", "_list_content"),
    ("POST", ("workflows",), "workflow", "_create_workflow"),
    ("GET", ("workflows",), "read", "_list_workflows"),
    ("POST", ("workflows", "{id}", "activation"), "workflow",
     "_set_workflow_active"),
    ("POST", ("lists",), "lists", "_create_contact_list"),
    ("GET", ("lists",), "read", "_list_contact_lists"),
    ("GET", ("lists", "{id}"), "read", "_get_contact_list"),
    ("POST", ("segments",), "segments", "_create_segment"),
    ("GET", ("segments",), "read", "_list_segments"),
    ("POST", ("campaigns",), "campaigns", "_create_campaign"),
    ("GET", ("campaigns",), "read", "_list_campaigns"),
    ("GET", ("campaigns", "{id}"), "read", "_get_campaign"),
    ("GET", ("campaigns", "{id}", "report"), "read", "_engagement_report"),
    ("POST", ("suppressions",), "suppress", "_record_suppression"),
    ("GET", ("suppressions",), "read", "_list_suppressions"),
    ("POST", ("suppressions", "{id}", "release"), "suppress",
     "_release_suppression"),
    ("GET", ("suppression-check",), "read", "_suppression_check"),
    ("POST", ("deliveries",), "deliver", "_record_delivery"),
    ("GET", ("deliveries",), "read", "_list_deliveries"),
    ("POST", ("engagements",), "engage", "_record_engagement"),
    ("GET", ("engagements",), "read", "_list_engagements"),
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
        store = MarketSalesStore(audit=audit)

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
            except MarketSalesError as exc:
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

        def _create_opportunity(self, user, ident, query):
            body = self._read_body()
            opportunity = store.create_opportunity(
                user, body.get("org_id"), body.get("ref"),
                body.get("agency_label"), body.get("title_label"),
                body.get("posted_at"), due_at=body.get("due_at"),
                kind_label=body.get("kind_label"))
            self._send(201, opportunity)

        def _list_opportunities(self, user, ident, query):
            opportunities = store.list_opportunities(
                user, org_id=query.get("org_id"))
            self._send(200, {"opportunities": opportunities})

        def _get_opportunity(self, user, ident, query):
            self._send(200, store.get_opportunity(user, ident))

        def _record_evaluation(self, user, ident, query):
            body = self._read_body()
            evaluation = store.record_evaluation(
                user, body.get("opportunity_id"), body.get("evaluator_ref"),
                body.get("decision"), note=body.get("note"))
            self._send(201, evaluation)

        def _list_evaluations(self, user, ident, query):
            evaluations = store.list_evaluations(
                user, opportunity_id=query.get("opportunity_id"))
            self._send(200, {"evaluations": evaluations})

        def _create_pipeline_entry(self, user, ident, query):
            body = self._read_body()
            entry = store.create_pipeline_entry(
                user, body.get("opportunity_id"),
                stage=body.get("stage", "identified"))
            self._send(201, entry)

        def _list_pipeline(self, user, ident, query):
            entries = store.list_pipeline(
                user, opportunity_id=query.get("opportunity_id"),
                stage=query.get("stage"))
            self._send(200, {"pipeline": entries})

        def _get_pipeline_entry(self, user, ident, query):
            self._send(200, store.get_pipeline_entry(user, ident))

        def _transition_pipeline(self, user, ident, query):
            body = self._read_body()
            entry = store.transition_pipeline(
                user, ident, body.get("stage"))
            self._send(200, entry)

        def _create_content_version(self, user, ident, query):
            body = self._read_body()
            content = store.create_content_version(
                user, body.get("opportunity_id"), body.get("item_label"),
                body.get("kind_label"), body.get("version"),
                body.get("size_bytes"), pipeline_id=body.get("pipeline_id"))
            self._send(201, content)

        def _list_content(self, user, ident, query):
            content = store.list_content(
                user, opportunity_id=query.get("opportunity_id"))
            self._send(200, {"content": content})

        def _create_workflow(self, user, ident, query):
            body = self._read_body()
            workflow = store.create_workflow(
                user, body.get("org_id"), body.get("label"),
                body.get("trigger_label"),
                cadence_label=body.get("cadence_label"))
            self._send(201, workflow)

        def _list_workflows(self, user, ident, query):
            workflows = store.list_workflows(
                user, org_id=query.get("org_id"))
            self._send(200, {"workflows": workflows})

        def _set_workflow_active(self, user, ident, query):
            body = self._read_body()
            workflow = store.set_workflow_active(
                user, ident, body.get("active"))
            self._send(200, workflow)

        def _create_contact_list(self, user, ident, query):
            body = self._read_body()
            contact_list = store.create_contact_list(
                user, body.get("org_id"), body.get("label"),
                body.get("contact_count"), loaded_at=body.get("loaded_at"))
            self._send(201, contact_list)

        def _list_contact_lists(self, user, ident, query):
            lists = store.list_contact_lists(
                user, org_id=query.get("org_id"))
            self._send(200, {"lists": lists})

        def _get_contact_list(self, user, ident, query):
            self._send(200, store.get_contact_list(user, ident))

        def _create_segment(self, user, ident, query):
            body = self._read_body()
            segment = store.create_segment(
                user, body.get("org_id"), body.get("label"),
                body.get("basis_label"), body.get("member_count"))
            self._send(201, segment)

        def _list_segments(self, user, ident, query):
            segments = store.list_segments(
                user, org_id=query.get("org_id"))
            self._send(200, {"segments": segments})

        def _create_campaign(self, user, ident, query):
            body = self._read_body()
            campaign = store.create_campaign(
                user, body.get("org_id"), body.get("label"),
                body.get("segment_id"), body.get("list_id"),
                scheduled_for=body.get("scheduled_for"))
            self._send(201, campaign)

        def _list_campaigns(self, user, ident, query):
            campaigns = store.list_campaigns(
                user, org_id=query.get("org_id"),
                status=query.get("status"))
            self._send(200, {"campaigns": campaigns})

        def _get_campaign(self, user, ident, query):
            self._send(200, store.get_campaign(user, ident))

        def _engagement_report(self, user, ident, query):
            self._send(200, store.engagement_report(user, ident))

        def _record_suppression(self, user, ident, query):
            body = self._read_body()
            suppression = store.record_suppression(
                user, body.get("list_id"), body.get("contact_ref"),
                body.get("reason"), at=body.get("at"))
            self._send(201, suppression)

        def _list_suppressions(self, user, ident, query):
            suppressions = store.list_suppressions(
                user, list_id=query.get("list_id"),
                state=query.get("state"))
            self._send(200, {"suppressions": suppressions})

        def _release_suppression(self, user, ident, query):
            self._read_body()
            self._send(200, store.release_suppression(user, ident))

        def _suppression_check(self, user, ident, query):
            result = store.is_suppressed(
                user, query.get("list_id"), query.get("contact_ref"))
            self._send(200, {"suppressed": result})

        def _record_delivery(self, user, ident, query):
            body = self._read_body()
            delivery = store.record_delivery(
                user, body.get("campaign_id"), body.get("contact_ref"),
                body.get("outcome"), body.get("occurred_at"))
            self._send(201, delivery)

        def _list_deliveries(self, user, ident, query):
            deliveries = store.list_deliveries(
                user, campaign_id=query.get("campaign_id"),
                outcome=query.get("outcome"))
            self._send(200, {"deliveries": deliveries})

        def _record_engagement(self, user, ident, query):
            body = self._read_body()
            engagement = store.record_engagement(
                user, body.get("campaign_id"), body.get("contact_ref"),
                body.get("kind"), body.get("occurred_at"))
            self._send(201, engagement)

        def _list_engagements(self, user, ident, query):
            engagements = store.list_engagements(
                user, campaign_id=query.get("campaign_id"),
                kind=query.get("kind"))
            self._send(200, {"engagements": engagements})

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
