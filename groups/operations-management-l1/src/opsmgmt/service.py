"""HTTP service exposing the operations-management functions over a JSON REST API.

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

List/get work-order and report endpoints accept a ``?now=``
ISO-8601 query parameter so derived overdue values are
deterministic for callers and tests.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import NotFoundError, OpsError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "operator",
    "carol": "viewer",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "OpsMgmt/0.1"
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
            return ("search", "project_read", ())
        if method == "GET" and parts == ["report"]:
            return ("report", "report_read", ())
        if parts and parts[0] == "persons":
            if len(parts) == 1:
                if method == "GET":
                    return ("person_list", "directory_read", ())
                if method == "POST":
                    return ("person_create", "directory_write", ())
            if len(parts) == 2 and method == "GET":
                return ("person_get", "directory_read", (parts[1],))
        if parts and parts[0] == "organizations":
            if len(parts) == 1:
                if method == "GET":
                    return ("organization_list", "directory_read", ())
                if method == "POST":
                    return ("organization_create", "directory_write", ())
            if len(parts) == 2 and method == "GET":
                return ("organization_get", "directory_read", (parts[1],))
        if parts and parts[0] == "projects":
            if len(parts) == 1:
                if method == "GET":
                    return ("project_list", "project_read", ())
                if method == "POST":
                    return ("project_create", "project_write", ())
            if len(parts) == 2 and method == "GET":
                return ("project_get", "project_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "members":
                if method == "GET":
                    return ("project_members", "project_read", (parts[1],))
                if method == "POST":
                    return ("project_add_member", "project_write", (parts[1],))
        if parts and parts[0] == "assets":
            if len(parts) == 1:
                if method == "GET":
                    return ("asset_list", "asset_read", ())
                if method == "POST":
                    return ("asset_create", "asset_write", ())
            if len(parts) == 2 and method == "GET":
                return ("asset_get", "asset_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("asset_transition", "asset_write", (parts[1],))
        if parts and parts[0] == "work-orders":
            if len(parts) == 1:
                if method == "GET":
                    return ("work_order_list", "work_read", ())
                if method == "POST":
                    return ("work_order_create", "work_write", ())
            if len(parts) == 2 and method == "GET":
                return ("work_order_get", "work_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "assign":
                return ("work_order_assign", "work_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("work_order_transition", "work_write", (parts[1],))
        if parts and parts[0] == "inspections":
            if len(parts) == 1:
                if method == "GET":
                    return ("inspection_list", "inspection_read", ())
                if method == "POST":
                    return ("inspection_create", "inspection_write", ())
            if len(parts) == 2 and method == "GET":
                return ("inspection_get", "inspection_read", (parts[1],))
        if parts and parts[0] == "usage":
            if len(parts) == 1:
                if method == "GET":
                    return ("usage_list", "usage_read", ())
                if method == "POST":
                    return ("usage_create", "usage_write", ())
        if parts and parts[0] == "workflows":
            if len(parts) == 1:
                if method == "GET":
                    return ("workflow_list", "workflow_read", ())
                if method == "POST":
                    return ("workflow_create", "workflow_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("workflow_get", "workflow_read", (parts[1],))
                if method == "PATCH":
                    return ("workflow_update", "workflow_write", (parts[1],))
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
        except OpsError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    @staticmethod
    def _now_param(parsed):
        params = parse_qs(parsed.query)
        values = params.get("now")
        return values[0] if values else None

    @staticmethod
    def _param(parsed, name):
        params = parse_qs(parsed.query)
        return (params.get(name) or [None])[0]

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
        if route == "report":
            self._send_json(200, store.report(user, now=self._now_param(parsed)))
            return
        if route == "person_list":
            self._send_json(200, {"persons": store.list_persons(user)})
            return
        if route == "person_create":
            body = self._read_json_body()
            self._send_json(201, store.create_person(
                body.get("name"), user,
                reference=body.get("reference"), attributes=body.get("attributes")))
            return
        if route == "person_get":
            self._send_json(200, store.get_person(ids[0], user))
            return
        if route == "organization_list":
            self._send_json(200, {"organizations": store.list_organizations(user)})
            return
        if route == "organization_create":
            body = self._read_json_body()
            self._send_json(201, store.create_organization(
                body.get("name"), user,
                reference=body.get("reference"), attributes=body.get("attributes")))
            return
        if route == "organization_get":
            self._send_json(200, store.get_organization(ids[0], user))
            return
        if route == "project_list":
            self._send_json(200, {"projects": store.list_projects(user)})
            return
        if route == "project_create":
            body = self._read_json_body()
            self._send_json(201, store.create_project(
                body.get("name"), user,
                org_id=body.get("org_id"), attributes=body.get("attributes")))
            return
        if route == "project_get":
            self._send_json(200, store.get_project(ids[0], user))
            return
        if route == "project_members":
            self._send_json(200, {"members": store.list_project_members(ids[0], user)})
            return
        if route == "project_add_member":
            body = self._read_json_body()
            project = store.add_person_to_project(ids[0], body.get("person_id"), user)
            self._send_json(201, project)
            return
        if route == "asset_list":
            self._send_json(200, {"assets": store.list_assets(
                user, status=self._param(parsed, "status"),
                project_id=self._param(parsed, "project_id"))})
            return
        if route == "asset_create":
            body = self._read_json_body()
            self._send_json(201, store.create_asset(
                body.get("name"), user,
                kind=body.get("kind", "equipment") or "equipment",
                project_id=body.get("project_id"), attributes=body.get("attributes")))
            return
        if route == "asset_get":
            self._send_json(200, store.get_asset(ids[0], user))
            return
        if route == "asset_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_asset(ids[0], user, to_status))
            return
        if route == "work_order_list":
            self._send_json(200, {"work_orders": store.list_work_orders(
                user, now=self._now_param(parsed),
                status=self._param(parsed, "status"),
                project_id=self._param(parsed, "project_id"),
                work_type=self._param(parsed, "work_type"))})
            return
        if route == "work_order_create":
            body = self._read_json_body()
            work_order = store.create_work_order(
                user, body.get("work_type"), body.get("subject"),
                project_id=body.get("project_id"), asset_id=body.get("asset_id"),
                person_id=body.get("person_id"),
                priority=body.get("priority", "normal") or "normal",
                due_at=body.get("due_at"))
            self._send_json(201, work_order)
            return
        if route == "work_order_get":
            self._send_json(200, store.get_work_order(
                ids[0], user, now=self._now_param(parsed)))
            return
        if route == "work_order_assign":
            body = self._read_json_body()
            self._send_json(200, store.assign_work_order(
                ids[0], user, person_id=body.get("person_id"),
                project_id=body.get("project_id")))
            return
        if route == "work_order_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_work_order(ids[0], user, to_status))
            return
        if route == "inspection_list":
            self._send_json(200, {"inspections": store.list_inspections(
                user, asset_id=self._param(parsed, "asset_id"),
                work_order_id=self._param(parsed, "work_order_id"))})
            return
        if route == "inspection_create":
            body = self._read_json_body()
            self._send_json(201, store.record_inspection(
                user, body.get("summary"),
                asset_id=body.get("asset_id"), work_order_id=body.get("work_order_id"),
                inspector_id=body.get("inspector_id"),
                outcome=body.get("outcome", "not_recorded") or "not_recorded"))
            return
        if route == "inspection_get":
            self._send_json(200, store.get_inspection(ids[0], user))
            return
        if route == "usage_list":
            self._send_json(200, {"usage": store.list_usage(
                user, project_id=self._param(parsed, "project_id"),
                metric=self._param(parsed, "metric"))})
            return
        if route == "usage_create":
            body = self._read_json_body()
            self._send_json(201, store.record_usage(
                user, body.get("project_id"), body.get("metric"),
                body.get("quantity"), body.get("period")))
            return
        if route == "workflow_list":
            self._send_json(200, {"workflows": store.list_workflows(user)})
            return
        if route == "workflow_create":
            body = self._read_json_body()
            self._send_json(201, store.create_workflow(
                user, body.get("name"), body.get("work_type"),
                body.get("trigger_text"), body.get("action_text")))
            return
        if route == "workflow_get":
            self._send_json(200, store.get_workflow(ids[0], user))
            return
        if route == "workflow_update":
            body = self._read_json_body()
            self._send_json(200, store.update_workflow(
                ids[0], user, trigger_text=body.get("trigger_text"),
                action_text=body.get("action_text"), enabled=body.get("enabled")))
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
    """Create (but do not start) the opsmgmt HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "OpsMgmtHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
