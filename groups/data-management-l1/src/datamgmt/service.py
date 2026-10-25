"""HTTP service exposing the data management functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

The store records every successful mutation and every search. This
layer never duplicates those records: it audits only denied attempts
(401 and 403, with the action name suffixed ``":denied"``) and
``audit_read``. Errors are JSON ``{error: msg}`` with 400
(validation), 401 (auth), 403 (permission) or 404 (not found);
handlers never leak a stack trace to the client.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import DataMgmtError, NotFoundError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "steward",
    "carol": "viewer",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "DataMgmt/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002
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

    def _route(self, method, parts):
        """Return (route, permission_action, ids)."""
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "catalog_read", ())
        if method == "GET" and parts == ["retention-due"]:
            return ("retention_due", "retention_read", ())
        if parts and parts[0] == "datasets":
            if len(parts) == 1:
                if method == "GET":
                    return ("dataset_list", "dataset_read", ())
                if method == "POST":
                    return ("dataset_create", "dataset_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("dataset_get", "dataset_read", (parts[1],))
                if method == "POST":
                    return ("dataset_update", "dataset_write", (parts[1],))
            if len(parts) == 3:
                if parts[2] == "schema" and method == "POST":
                    return ("dataset_schema_update", "dataset_write", (parts[1],))
                if parts[2] == "ingestions":
                    if method == "GET":
                        return ("dataset_ingestions", "ingest_read", (parts[1],))
                    if method == "POST":
                        return ("dataset_ingestion_create", "ingest_record", (parts[1],))
                if parts[2] == "provenance" and method == "GET":
                    return ("dataset_provenance", "ingest_read", (parts[1],))
                if parts[2] == "quality-rules":
                    if method == "GET":
                        return ("dataset_quality_rules", "quality_read", (parts[1],))
                    if method == "POST":
                        return ("dataset_quality_rule_create", "quality_write", (parts[1],))
                if parts[2] == "access-requests":
                    if method == "GET":
                        return ("dataset_access_requests", "access_read", (parts[1],))
                    if method == "POST":
                        return ("dataset_access_request_create", "access_request", (parts[1],))
                if parts[2] == "exports":
                    if method == "GET":
                        return ("dataset_exports", "dataset_read", (parts[1],))
                    if method == "POST":
                        return ("dataset_export_create", "export", (parts[1],))
                if parts[2] == "retention-policy":
                    if method == "GET":
                        return ("dataset_retention_policy", "retention_read", (parts[1],))
                    if method == "POST":
                        return ("dataset_retention_policy_set", "retention_write", (parts[1],))
        if parts and parts[0] == "sources":
            if len(parts) == 1:
                if method == "GET":
                    return ("source_list", "source_read", ())
                if method == "POST":
                    return ("source_create", "source_write", ())
            if len(parts) == 2 and method == "GET":
                return ("source_get", "source_read", (parts[1],))
        if parts and parts[0] == "ingestions":
            if len(parts) == 2 and method == "GET":
                return ("ingestion_get", "ingest_read", (parts[1],))
        if parts and parts[0] == "quality-rules":
            if len(parts) == 2 and method == "GET":
                return ("quality_rule_get", "quality_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "checks":
                if method == "POST":
                    return ("quality_check_run", "quality_run", (parts[1],))
                if method == "GET":
                    return ("quality_rule_checks", "quality_read", (parts[1],))
        if parts and parts[0] == "quality-checks":
            if len(parts) == 2 and method == "GET":
                return ("quality_check_get", "quality_read", (parts[1],))
        if parts and parts[0] == "access-requests":
            if len(parts) == 1 and method == "GET":
                return ("access_request_list", "access_read", ())
            if len(parts) == 2 and method == "GET":
                return ("access_request_get", "access_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "decide" and method == "POST":
                return ("access_decide", "access_decide", (parts[1],))
        if parts and parts[0] == "grants":
            if len(parts) == 1 and method == "GET":
                return ("grant_list", "access_read", ())
            if len(parts) == 2 and method == "GET":
                return ("grant_get", "access_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "revoke" and method == "POST":
                return ("grant_revoke", "access_decide", (parts[1],))
        if parts and parts[0] == "retention-policies":
            if len(parts) == 1 and method == "GET":
                return ("retention_policy_list", "retention_read", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("retention_policy_get", "retention_read", (parts[1],))
                if method == "POST":
                    return ("retention_policy_update", "retention_write", (parts[1],))
        if parts and parts[0] == "exports":
            if len(parts) == 2 and method == "GET":
                return ("export_get", "dataset_read", (parts[1],))
        return (None, None, ())

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [unquote(p) for p in path.split("/") if p != ""]
        route, action, ids = self._route(method, parts)
        target = ids[-1] if ids else path
        try:
            if route is None:
                self._error(404, "not found")
                return
            if route == "health":
                self._send_json(200, {"status": "ok"})
                return
            user = self._authenticate(action, target)
            if user is None:
                return
            if action is not None and not self._authorize(user, action, target):
                return
            self._execute(route, user, ids, parsed)
        except ValidationError as exc:
            self._safe_error(400, exc)
        except PermissionDenied as exc:
            actor = self.headers.get("X-User") or "anonymous"
            if action:
                self._audit_denied(actor, action, target)
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except DataMgmtError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    def _execute(self, route, user, ids, parsed):
        store = self.store
        if route == "audit_read":
            entries = self.audit.entries() if self.audit is not None else []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "search":
            params = parse_qs(parsed.query)
            query_text = (params.get("q") or [""])[0]
            self._send_json(200, store.search(query_text, user))
            return
        if route == "dataset_list":
            self._send_json(200, {"datasets": store.list_datasets(user)})
            return
        if route == "dataset_create":
            body = self._read_json_body()
            dataset = store.create_dataset(
                body.get("name"),
                body.get("description"),
                user,
                owner=body.get("owner"),
                classification=body.get("classification", "internal"),
                tags=body.get("tags"),
                schema=body.get("schema"),
            )
            self._send_json(201, dataset)
            return
        if route == "dataset_get":
            self._send_json(200, store.get_dataset(ids[0], user))
            return
        if route == "dataset_update":
            body = self._read_json_body()
            dataset = store.update_dataset(
                ids[0],
                user,
                description=body.get("description"),
                tags=body.get("tags"),
                classification=body.get("classification"),
            )
            self._send_json(200, dataset)
            return
        if route == "dataset_schema_update":
            body = self._read_json_body()
            dataset = store.update_schema(ids[0], body.get("schema"), user)
            self._send_json(200, dataset)
            return
        if route == "dataset_ingestions":
            self._send_json(200, {"ingestions": store.list_ingestions(dataset_id=ids[0], actor=user)})
            return
        if route == "dataset_ingestion_create":
            body = self._read_json_body()
            ingestion = store.record_ingestion(
                ids[0],
                body.get("source_id"),
                user,
                mode=body.get("mode", "full"),
                record_count=body.get("record_count", 0),
                checksum=body.get("checksum"),
                status=body.get("status", "completed"),
                notes=body.get("notes"),
            )
            self._send_json(201, ingestion)
            return
        if route == "dataset_provenance":
            self._send_json(200, store.dataset_provenance(ids[0], user))
            return
        if route == "dataset_quality_rules":
            self._send_json(200, {"quality_rules": store.list_quality_rules(dataset_id=ids[0], actor=user)})
            return
        if route == "dataset_quality_rule_create":
            body = self._read_json_body()
            rule = store.create_quality_rule(
                ids[0],
                body.get("name"),
                body.get("kind"),
                body.get("field"),
                user,
                params=body.get("params"),
            )
            self._send_json(201, rule)
            return
        if route == "dataset_access_requests":
            self._send_json(200, {"access_requests": store.list_access_requests(dataset_id=ids[0], actor=user)})
            return
        if route == "dataset_access_request_create":
            body = self._read_json_body()
            request = store.request_access(
                ids[0],
                body.get("purpose"),
                user,
                duration_days=body.get("duration_days", 30),
            )
            self._send_json(201, request)
            return
        if route == "dataset_exports":
            self._send_json(200, {"exports": store.list_exports(dataset_id=ids[0], actor=user)})
            return
        if route == "dataset_export_create":
            body = self._read_json_body()
            export = store.export_dataset(
                ids[0],
                user,
                format=body.get("format", "json"),
                records=body.get("records"),
            )
            self._send_json(201, export)
            return
        if route == "dataset_retention_policy":
            policy = store.retention_policy_for(ids[0], user)
            if policy is None:
                self._error(404, "no retention policy for dataset")
                return
            self._send_json(200, policy)
            return
        if route == "dataset_retention_policy_set":
            body = self._read_json_body()
            policy = store.set_retention_policy(
                ids[0],
                body.get("retention_days"),
                body.get("disposition"),
                user,
                legal_hold=body.get("legal_hold", False),
            )
            self._send_json(201, policy)
            return
        if route == "source_list":
            self._send_json(200, {"sources": store.list_sources(user)})
            return
        if route == "source_create":
            body = self._read_json_body()
            source = store.register_source(
                body.get("name"), body.get("kind"), user,
                location=body.get("location"),
            )
            self._send_json(201, source)
            return
        if route == "source_get":
            self._send_json(200, store.get_source(ids[0], user))
            return
        if route == "ingestion_get":
            self._send_json(200, store.get_ingestion(ids[0], user))
            return
        if route == "quality_rule_get":
            self._send_json(200, store.get_quality_rule(ids[0], user))
            return
        if route == "quality_check_run":
            body = self._read_json_body()
            check = store.run_quality_check(
                ids[0], body.get("records"), user, now=body.get("now")
            )
            self._send_json(201, check)
            return
        if route == "quality_rule_checks":
            self._send_json(200, {"quality_checks": store.list_quality_checks(rule_id=ids[0], actor=user)})
            return
        if route == "quality_check_get":
            self._send_json(200, store.get_quality_check(ids[0], user))
            return
        if route == "access_request_list":
            self._send_json(200, {"access_requests": store.list_access_requests(actor=user)})
            return
        if route == "access_request_get":
            self._send_json(200, store.get_access_request(ids[0], user))
            return
        if route == "access_decide":
            body = self._read_json_body()
            request = store.decide_access_request(
                ids[0], body.get("approve"), user, reason=body.get("reason")
            )
            self._send_json(200, request)
            return
        if route == "grant_list":
            params = parse_qs(parsed.query)
            dataset_id = (params.get("dataset_id") or [None])[0]
            grantee = (params.get("grantee") or [None])[0]
            self._send_json(200, {"grants": store.list_grants(dataset_id=dataset_id, grantee=grantee, actor=user)})
            return
        if route == "grant_get":
            self._send_json(200, store.get_grant(ids[0], user))
            return
        if route == "grant_revoke":
            self._send_json(200, store.revoke_grant(ids[0], user))
            return
        if route == "retention_policy_list":
            self._send_json(200, {"retention_policies": store.list_retention_policies(user)})
            return
        if route == "retention_policy_get":
            self._send_json(200, store.get_retention_policy(ids[0], user))
            return
        if route == "retention_policy_update":
            body = self._read_json_body()
            policy = store.update_retention_policy(
                ids[0],
                user,
                retention_days=body.get("retention_days"),
                disposition=body.get("disposition"),
                legal_hold=body.get("legal_hold"),
            )
            self._send_json(200, policy)
            return
        if route == "retention_due":
            params = parse_qs(parsed.query)
            now = (params.get("now") or [None])[0]
            self._send_json(200, {"due": store.retention_due(actor=user, now=now)})
            return
        if route == "export_get":
            self._send_json(200, store.get_export(ids[0], user))
            return
        self._error(404, "not found")

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


def make_server(host, port, store, audit, users):
    """Create (but do not start) the datamgmt HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "DataMgmtHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
