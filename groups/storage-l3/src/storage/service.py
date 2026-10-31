"""HTTP service exposing the storage store as a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers against a fixed user registry
supplied at construction; the presented role must match the
registry entry. Denied attempts are audited (action name with a
``:denied`` suffix), as are successful audit-log reads.

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent) [L3]:

- **Unsuccessful logon lockout (AC-7).** ``make_server`` accepts
  ``max_failures`` / ``lockout_seconds``. Consecutive authentication
  failures (unknown user or role mismatch) are tracked per username;
  at ``max_failures`` the username locks for ``lockout_seconds`` and
  any further attempt for it -- even with the correct role -- is
  answered 403 and audited with action ``"auth:locked"``. A
  successful authentication resets that user's counter; lock expiry
  lets the user in again.
- **Audit verification & reduction (AU-9 / AU-7).** ``GET
  /audit/verify`` (audit_read) reports the hash-chain verification
  result; ``GET /audit`` accepts optional ``actor``, ``action``,
  ``target``, ``since`` and ``until`` query parameters passed to
  :meth:`AuditLog.query`.
- **Fail closed (AU-5).** An :class:`AuditWriteError` from the audit
  log is never swallowed by the service layer: the request is
  answered exactly 500 ``{"error": "audit write failed"}`` and the
  operation does not proceed.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, permissions_for, require
from .audit import AuditLog
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    StorageError,
    ValidationError,
)
from .store import StorageStore

# method -> (path pattern, required permission, handler name)
ROUTES = [
    ("GET", ("health",), None, "_health"),
    ("POST", ("organizations",), "register", "_create_organization"),
    ("GET", ("organizations",), "read", "_list_organizations"),
    ("GET", ("organizations", "{id}"), "read", "_get_organization"),
    ("POST", ("policies",), "register", "_create_policy"),
    ("GET", ("policies",), "read", "_list_policies"),
    ("GET", ("policies", "{id}"), "read", "_get_policy"),
    ("POST", ("collections",), "register", "_create_collection"),
    ("GET", ("collections",), "read", "_list_collections"),
    ("GET", ("collections", "{id}"), "read", "_get_collection"),
    ("POST", ("messages",), "archive", "_archive_message"),
    ("GET", ("messages",), "read", "_list_messages"),
    ("GET", ("messages", "{id}"), "read", "_get_message"),
    ("POST", ("messages", "{id}", "dispositions"), "archive",
     "_record_disposition"),
    ("GET", ("messages", "{id}", "dispositions"), "read",
     "_list_dispositions"),
    ("POST", ("discoveries",), "discover", "_record_discovery"),
    ("GET", ("discoveries",), "read", "_list_discoveries"),
    ("POST", ("supervision",), "supervise", "_create_review"),
    ("GET", ("supervision",), "read", "_list_reviews"),
    ("POST", ("supervision", "{id}", "outcome"), "supervise",
     "_review_outcome"),
    ("POST", ("enforcement",), "enforce", "_record_enforcement"),
    ("GET", ("enforcement",), "read", "_list_enforcements"),
    ("POST", ("retrievals",), "retrieve", "_create_retrieval"),
    ("GET", ("retrievals",), "read", "_list_retrievals"),
    ("POST", ("retrievals", "{id}", "complete"), "retrieve",
     "_complete_retrieval"),
    ("POST", ("custody",), "custody", "_create_custody"),
    ("GET", ("custody",), "read", "_list_custodies"),
    ("POST", ("custody", "{id}", "retire"), "custody", "_retire_custody"),
    ("POST", ("integrations",), "register", "_create_integration"),
    ("GET", ("integrations",), "read", "_list_integrations"),
    ("POST", ("integrations", "{id}", "deactivate"), "register",
     "_deactivate_integration"),
    ("GET", ("search",), "read", "_search"),
    ("GET", ("summary",), "read", "_summary"),
    ("GET", ("audit",), "audit_read", "_audit"),
    ("GET", ("audit", "verify"), "audit_read", "_audit_verify"),
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
                certfile=None, keyfile=None, max_failures=3,
                lockout_seconds=300):
    """Build (but do not start) the HTTP server.

    ``users`` maps a username to its role; the default registry is
    ``alice=admin, bob=operator, carol=viewer, dana=auditor`` for
    local demonstration. When ``certfile``/``keyfile`` are supplied
    the socket is wrapped in TLS. ``max_failures`` /
    ``lockout_seconds`` configure the AC-7 unsuccessful-logon
    lockout enforced by the handler [L3].
    """
    if users is None:
        users = {"alice": "admin", "bob": "operator", "carol": "viewer",
                 "dana": "auditor"}
    if audit is None:
        audit = AuditLog()
    if store is None:
        store = StorageStore(audit=audit)
    # Per-username consecutive-authentication-failure state (AC-7):
    # name -> {"failures": int, "locked_until": float | None}.
    # Scoped to this server instance via the closure.
    auth_state = {}
    auth_lock = threading.Lock()

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
            """Return the User, or None (error sent by the caller).

            AC-7 [L3]: consecutive authentication failures are
            counted per username; at ``max_failures`` the username
            locks for ``lockout_seconds`` and attempts during the
            lock -- even with the correct role -- are refused with
            ``self._auth_locked`` set, so the caller answers 403
            and audits ``auth:locked``. A successful authentication
            resets the counter; an expired lock clears itself.
            """
            name = self.headers.get("X-User")
            role = self.headers.get("X-Role")
            self._auth_locked = False
            if name:
                with auth_lock:
                    state = auth_state.get(name)
                    locked_until = state["locked_until"] if state else None
                    if locked_until is not None \
                            and time.monotonic() >= locked_until:
                        # Lock expired: clear it before judging.
                        auth_state.pop(name, None)
                        locked_until = None
                if locked_until is not None:
                    self._auth_locked = True
                    return None
            if not name or not role or name not in users \
                    or users[name] != role:
                if name:
                    with auth_lock:
                        state = auth_state.setdefault(
                            name, {"failures": 0, "locked_until": None})
                        state["failures"] += 1
                        if state["failures"] >= max_failures:
                            state["locked_until"] = (
                                time.monotonic() + lockout_seconds)
                return None
            with auth_lock:
                auth_state.pop(name, None)  # Success resets the counter.
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
            try:
                user = self._authenticate()
                if user is None:
                    if self._auth_locked:
                        audit.record(
                            self.headers.get("X-User") or "anonymous",
                            "auth:locked", parsed.path,
                            {"reason": "account locked: too many "
                                       "failed logons"})
                        self._send(403, {
                            "error": "account locked: too many "
                                     "failed logons"})
                        return
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
                except AuditWriteError:
                    # Must precede the StorageError clause: an audit
                    # failure is a 500, never a 400 (AU-5) [L3].
                    self._send(500, {"error": "audit write failed"})
                except StorageError as exc:
                    self._send(400, {"error": str(exc)})
            except AuditWriteError:
                # AU-5 fail closed [L3]: a failed audit write means
                # the operation does not proceed; the answer is
                # exactly 500 {"error": "audit write failed"}.
                self._send(500, {"error": "audit write failed"})

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

        def _create_policy(self, user, ident, query):
            body = self._read_body()
            policy = store.create_policy(
                user, body.get("label"), body.get("retention_days"))
            self._send(201, policy)

        def _list_policies(self, user, ident, query):
            self._send(200, {"policies": store.list_policies(user)})

        def _get_policy(self, user, ident, query):
            self._send(200, store.get_policy(user, ident))

        def _create_collection(self, user, ident, query):
            body = self._read_body()
            collection = store.create_collection(
                user, body.get("org_id"), body.get("label"),
                body.get("policy_id"), body.get("format_label"))
            self._send(201, collection)

        def _list_collections(self, user, ident, query):
            collections = store.list_collections(
                user, org_id=query.get("org_id"))
            self._send(200, {"collections": collections})

        def _get_collection(self, user, ident, query):
            self._send(200, store.get_collection(user, ident))

        def _archive_message(self, user, ident, query):
            body = self._read_body()
            message = store.archive_message(
                user, body.get("collection_id"), body.get("message_ref"),
                body.get("sender_ref"), body.get("recipient_refs"),
                body.get("archived_at"), body.get("size_bytes"),
                body.get("format_label"), custody_id=body.get("custody_id"))
            self._send(201, message)

        def _list_messages(self, user, ident, query):
            messages = store.list_messages(
                user, collection_id=query.get("collection_id"),
                retention_state=query.get("retention_state"),
                now=query.get("now"))
            self._send(200, {"messages": messages})

        def _get_message(self, user, ident, query):
            self._send(200, store.get_message(
                user, ident, now=query.get("now")))

        def _record_disposition(self, user, ident, query):
            body = self._read_body()
            disposition = store.record_disposition(
                user, ident, body.get("method_label"), at=body.get("at"))
            self._send(201, disposition)

        def _list_dispositions(self, user, ident, query):
            dispositions = store.list_dispositions(user, message_id=ident)
            self._send(200, {"dispositions": dispositions})

        def _record_discovery(self, user, ident, query):
            body = self._read_body()
            discovery = store.record_discovery(
                user, body.get("matter_ref"), body.get("collection_id"),
                sender_ref=body.get("sender_ref"),
                from_at=body.get("from_at"), to_at=body.get("to_at"))
            self._send(201, discovery)

        def _list_discoveries(self, user, ident, query):
            discoveries = store.list_discoveries(
                user, collection_id=query.get("collection_id"))
            self._send(200, {"discoveries": discoveries})

        def _create_review(self, user, ident, query):
            body = self._read_body()
            review = store.create_review(
                user, body.get("message_id"), body.get("reviewer_ref"))
            self._send(201, review)

        def _list_reviews(self, user, ident, query):
            reviews = store.list_reviews(
                user, message_id=query.get("message_id"),
                status=query.get("status"))
            self._send(200, {"supervision": reviews})

        def _review_outcome(self, user, ident, query):
            body = self._read_body()
            review = store.record_review_outcome(
                user, ident, body.get("outcome"), note=body.get("note"))
            self._send(200, review)

        def _record_enforcement(self, user, ident, query):
            body = self._read_body()
            enforcement = store.record_enforcement(
                user, body.get("action"), body.get("target_ref"),
                body.get("policy_ref"), note=body.get("note"))
            self._send(201, enforcement)

        def _list_enforcements(self, user, ident, query):
            enforcements = store.list_enforcements(
                user, action=query.get("action"))
            self._send(200, {"enforcement": enforcements})

        def _create_retrieval(self, user, ident, query):
            body = self._read_body()
            retrieval = store.create_retrieval(
                user, body.get("message_id"), body.get("mode"),
                body.get("destination"), body.get("requester_ref"))
            self._send(201, retrieval)

        def _list_retrievals(self, user, ident, query):
            retrievals = store.list_retrievals(
                user, message_id=query.get("message_id"),
                status=query.get("status"))
            self._send(200, {"retrievals": retrievals})

        def _complete_retrieval(self, user, ident, query):
            self._read_body()
            self._send(200, store.complete_retrieval(user, ident))

        def _create_custody(self, user, ident, query):
            body = self._read_body()
            custody = store.create_custody(
                user, body.get("org_id"), body.get("collection_id"),
                body.get("custodian_ref"), body.get("key_label"))
            self._send(201, custody)

        def _list_custodies(self, user, ident, query):
            custodies = store.list_custodies(
                user, collection_id=query.get("collection_id"),
                status=query.get("status"))
            self._send(200, {"custody": custodies})

        def _retire_custody(self, user, ident, query):
            self._read_body()
            self._send(200, store.retire_custody(user, ident))

        def _create_integration(self, user, ident, query):
            body = self._read_body()
            integration = store.create_integration(
                user, body.get("org_id"), body.get("kind"),
                body.get("label"))
            self._send(201, integration)

        def _list_integrations(self, user, ident, query):
            integrations = store.list_integrations(
                user, org_id=query.get("org_id"), kind=query.get("kind"))
            self._send(200, {"integrations": integrations})

        def _deactivate_integration(self, user, ident, query):
            self._read_body()
            self._send(200, store.deactivate_integration(user, ident))

        def _search(self, user, ident, query):
            self._send(200, store.search(user, query.get("q")))

        def _summary(self, user, ident, query):
            self._send(200, store.summary(user, now=query.get("now")))

        def _audit(self, user, ident, query):
            # AU-7 [L3]: optional actor/action/target/since/until
            # query parameters reduce the trail via AuditLog.query;
            # with no parameters the full trail is returned, as at L2.
            filters = {key: query.get(key) for key in
                       ("actor", "action", "target", "since", "until")}
            if any(value is not None for value in filters.values()):
                entries = audit.query(**filters)
                result = {"entries": entries, "count": len(entries)}
            else:
                result = store.audit_read(user)
            audit.record(user.name, "audit_read", "/audit",
                         {"count": result["count"]})
            self._send(200, result)

        def _audit_verify(self, user, ident, query):
            # AU-9 [L3]: report the hash-chain verification result.
            # The count is read before this read's own audit entry
            # is recorded, so it is the pre-request trail length.
            ok, first_bad = audit.verify_chain()
            count = len(audit.entries())
            audit.record(user.name, "audit_read", "/audit/verify",
                         {"count": count})
            self._send(200, {"ok": ok, "entries": count,
                             "first_bad_index": first_bad})

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
