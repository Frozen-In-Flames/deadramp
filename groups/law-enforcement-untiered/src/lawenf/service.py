"""HTTP service exposing the legal research records substrate over a
JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

Digest discipline: this layer is the only place query text or note
text may appear. ``query_text`` / ``note_text`` request fields are
SHA-256-hashed here, before the store is called; the text itself is
never stored, logged, or audited. The store has no parameter that
could accept it.

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
from .errors import LawEnfError, NotFoundError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "LawEnf/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002
        pass

    # -- plumbing ------------------------------------------------------

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

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            try:
                self.audit.record(actor, action, target, details=details)
            except Exception:
                pass

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _authenticate(self, action, target):
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        actor = name if name else "anonymous"
        if not name or not role or name not in self.users or self.users[name] != role:
            self._audit_denied(actor, action, target)
            self._error(401, "unauthorized")
            return None
        return User(name=name, role=role)

    def _authorize(self, user, action, target):
        try:
            require(user, action)
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
            return False
        return True

    # -- routing ---------------------------------------------------------

    def _route(self, method, parts):
        """Return (route, permission_action, ids) or (None, None, ())."""
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("registry_search", "matter_read", ())
        if parts[:1] == ["matters"]:
            if len(parts) == 1:
                if method == "GET":
                    return ("list_matters", "matter_read", ())
                if method == "POST":
                    return ("create_matter", "matter_write", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("get_matter", "matter_read", (parts[1],))
            elif len(parts) == 3:
                mid, sub = parts[1], parts[2]
                table = {
                    ("POST", "members"): ("add_member", "matter_write"),
                    ("POST", "close"): ("close_matter", "matter_write"),
                    ("POST", "reopen"): ("reopen_matter", "matter_write"),
                    ("GET", "sources"): ("list_sources", "matter_read"),
                    ("POST", "sources"): ("create_source", "source_write"),
                    ("GET", "documents"): ("list_documents", "matter_read"),
                    ("POST", "documents"): ("register_document", "document_write"),
                    ("GET", "searches"): ("list_searches", "matter_read"),
                    ("POST", "searches"): ("save_search", "search_write"),
                    ("GET", "annotations"): ("list_annotations", "matter_read"),
                    ("POST", "annotations"): ("add_annotation", "annotation_write"),
                    ("GET", "citation-checks"): ("list_citation_checks", "matter_read"),
                    ("POST", "citation-checks"): ("record_citation_check", "citation_write"),
                    ("GET", "report"): ("matter_report", "report_read"),
                }
                if (method, sub) in table:
                    name, action = table[(method, sub)]
                    return (name, action, (mid,))
            elif len(parts) == 4:
                mid, sub, cid = parts[1], parts[2], parts[3]
                if method == "GET" and sub == "sources":
                    return ("get_source", "matter_read", (mid, cid))
                if method == "GET" and sub == "documents":
                    return ("get_document", "matter_read", (mid, cid))
                if method == "GET" and sub == "searches":
                    return ("get_search", "matter_read", (mid, cid))
            elif len(parts) == 5 and parts[2] == "documents" and method == "POST":
                mid, did, verb = parts[1], parts[3], parts[4]
                table = {
                    "begin-review": ("begin_review", "document_write"),
                    "complete-review": ("complete_review", "document_write"),
                    "verify": ("verify_document", "matter_read"),
                }
                if verb in table:
                    name, action = table[verb]
                    return (name, action, (mid, did))
        return (None, None, ())

    # -- dispatch ----------------------------------------------------------

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.split("/") if p != ""]
        query = parse_qs(parsed.query)
        target = parsed.path
        route, action, ids = self._route(method, parts)
        if route is None:
            self._error(404, "no such route")
            return
        if route == "health":
            self._send_json(200, {"status": "ok"})
            return
        user = self._authenticate(action, target)
        if user is None:
            return
        if not self._authorize(user, action, target):
            return
        try:
            body = self._read_json_body() if method == "POST" else {}
            self._handle(route, user, ids, query, body)
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
        except NotFoundError as exc:
            self._error(404, str(exc))
        except ValidationError as exc:
            self._error(400, str(exc))
        except LawEnfError as exc:
            self._error(400, str(exc))

    def _handle(self, route, user, ids, query, body):
        store = self.store

        def q1(name):
            values = query.get(name)
            return values[0] if values else None

        if route == "audit_read":
            if self.audit is not None:
                self._audit(user.name, "audit_read", "/audit")
            entries = self.audit.entries() if self.audit is not None else []
            self._send_json(200, {"entries": entries})
        elif route == "registry_search":
            result = store.search_registry(user, q1("q") or "")
            self._send_json(200, result)
        elif route == "list_matters":
            self._send_json(200, {"matters": store.list_matters(user)})
        elif route == "create_matter":
            self._send_json(201, store.create_matter(body.get("matter_ref"), user))
        elif route == "get_matter":
            self._send_json(200, store.get_matter(ids[0], user))
        elif route == "add_member":
            self._send_json(200, store.add_member(ids[0], body.get("username"), user))
        elif route == "close_matter":
            self._send_json(200, store.close_matter(ids[0], user))
        elif route == "reopen_matter":
            self._send_json(200, store.reopen_matter(ids[0], user))
        elif route == "list_sources":
            self._send_json(200, {"sources": store.list_sources(
                ids[0], user, kind=q1("kind"))})
        elif route == "create_source":
            self._send_json(201, store.create_source(
                ids[0], body.get("source_ref"), body.get("kind"), user,
                jurisdiction_ref=body.get("jurisdiction_ref"),
                citation_ref=body.get("citation_ref")))
        elif route == "get_source":
            self._send_json(200, store.get_source(ids[0], ids[1], user))
        elif route == "list_documents":
            self._send_json(200, {"documents": store.list_documents(
                ids[0], user, status=q1("status"))})
        elif route == "register_document":
            self._send_json(201, store.register_document(
                ids[0], body.get("doc_ref"), body.get("sha256"),
                body.get("size_bytes"), user))
        elif route == "get_document":
            self._send_json(200, store.get_document(ids[0], ids[1], user))
        elif route == "begin_review":
            self._send_json(200, store.begin_review(ids[0], ids[1], user))
        elif route == "complete_review":
            self._send_json(200, store.complete_review(ids[0], ids[1], user))
        elif route == "verify_document":
            raw = body.get("content_b64")
            if not isinstance(raw, str):
                raise ValidationError("content_b64 must be a base64 string")
            try:
                content = base64.b64decode(raw.encode("ascii"), validate=True)
            except (ValueError, UnicodeEncodeError) as exc:
                raise ValidationError("content_b64 must be valid base64") from exc
            self._send_json(200, store.verify_document(ids[0], ids[1], content, user))
        elif route == "list_searches":
            self._send_json(200, {"searches": store.list_searches(ids[0], user)})
        elif route == "save_search":
            digest = body.get("query_sha256")
            if body.get("query_text") is not None:
                text = body["query_text"]
                if not isinstance(text, str):
                    raise ValidationError("query_text must be a string")
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._send_json(201, store.save_search(
                ids[0], body.get("search_ref"), digest,
                body.get("result_count"), user))
        elif route == "get_search":
            self._send_json(200, store.get_search(ids[0], ids[1], user))
        elif route == "list_annotations":
            self._send_json(200, {"annotations": store.list_annotations(
                ids[0], user, target_id=q1("target_id"))})
        elif route == "add_annotation":
            digest = body.get("note_sha256")
            if body.get("note_text") is not None:
                text = body["note_text"]
                if not isinstance(text, str):
                    raise ValidationError("note_text must be a string")
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._send_json(201, store.add_annotation(
                ids[0], body.get("target_kind"), body.get("target_id"),
                body.get("annotation_ref"), digest, user))
        elif route == "list_citation_checks":
            self._send_json(200, {"citation_checks":
                                  store.list_citation_checks(ids[0], user)})
        elif route == "record_citation_check":
            self._send_json(201, store.record_citation_check(
                ids[0], body.get("citation_ref"), body.get("treatment"), user,
                source_id=body.get("source_id")))
        elif route == "matter_report":
            self._send_json(200, store.matter_report(ids[0], user))
        else:  # pragma: no cover - routing guarantees a handler
            self._error(404, "no such route")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def make_server(host, port, store, audit, users):
    """Build (but do not start) the HTTP server."""
    handler = type("LawEnfHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
