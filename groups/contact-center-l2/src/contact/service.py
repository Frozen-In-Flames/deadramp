"""HTTP service exposing the contact-center functions over a JSON REST API.

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

List/get case, callback, and report endpoints accept a ``?now=``
ISO-8601 query parameter so derived breach/state values are
deterministic for callers and tests.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import ContactError, NotFoundError, PermissionDenied, ValidationError

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
    server_version = "Contact/0.1"
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
            return ("search", "case_read", ())
        if method == "GET" and parts == ["report"]:
            return ("report", "report_read", ())
        if parts and parts[0] == "agents":
            if len(parts) == 1:
                if method == "GET":
                    return ("agent_list", "directory_read", ())
                if method == "POST":
                    return ("agent_create", "directory_write", ())
            if len(parts) == 2 and method == "GET":
                return ("agent_get", "directory_read", (parts[1],))
        if parts and parts[0] == "contacts":
            if len(parts) == 1:
                if method == "GET":
                    return ("contact_list", "directory_read", ())
                if method == "POST":
                    return ("contact_create", "directory_write", ())
            if len(parts) == 2 and method == "GET":
                return ("contact_get", "directory_read", (parts[1],))
        if parts and parts[0] == "queues":
            if len(parts) == 1:
                if method == "GET":
                    return ("queue_list", "queue_read", ())
                if method == "POST":
                    return ("queue_create", "queue_write", ())
            if len(parts) == 2 and method == "GET":
                return ("queue_get", "queue_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "members":
                if method == "GET":
                    return ("queue_members", "queue_read", (parts[1],))
                if method == "POST":
                    return ("queue_add_member", "queue_write", (parts[1],))
        if parts and parts[0] == "cases":
            if len(parts) == 1:
                if method == "GET":
                    return ("case_list", "case_read", ())
                if method == "POST":
                    return ("case_create", "case_write", ())
            if len(parts) == 2 and method == "GET":
                return ("case_get", "case_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "assign":
                return ("case_assign", "case_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("case_transition", "case_write", (parts[1],))
        if parts and parts[0] == "callbacks":
            if len(parts) == 1:
                if method == "GET":
                    return ("callback_list", "callback_read", ())
                if method == "POST":
                    return ("callback_create", "callback_write", ())
            if len(parts) == 2 and method == "GET":
                return ("callback_get", "callback_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "complete":
                return ("callback_complete", "callback_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "cancel":
                return ("callback_cancel", "callback_write", (parts[1],))
        if parts and parts[0] == "interactions":
            if len(parts) == 1:
                if method == "GET":
                    return ("interaction_list", "interaction_read", ())
                if method == "POST":
                    return ("interaction_create", "interaction_write", ())
            if len(parts) == 2 and method == "GET":
                return ("interaction_get", "interaction_read", (parts[1],))
        if parts and parts[0] == "alerts":
            if len(parts) == 1:
                if method == "GET":
                    return ("alert_list", "alert_read", ())
                if method == "POST":
                    return ("alert_create", "alert_write", ())
            if len(parts) == 2 and method == "GET":
                return ("alert_get", "alert_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "ack":
                return ("alert_ack", "alert_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "resolve":
                return ("alert_resolve", "alert_write", (parts[1],))
        if parts and parts[0] == "rules":
            if len(parts) == 1:
                if method == "GET":
                    return ("rule_list", "rule_read", ())
                if method == "POST":
                    return ("rule_create", "rule_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("rule_get", "rule_read", (parts[1],))
                if method == "PATCH":
                    return ("rule_update", "rule_write", (parts[1],))
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
        except ContactError as exc:
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
        if route == "agent_list":
            self._send_json(200, {"agents": store.list_agents(user)})
            return
        if route == "agent_create":
            body = self._read_json_body()
            self._send_json(201, store.create_agent(
                body.get("name"), user,
                skills=body.get("skills"), attributes=body.get("attributes")))
            return
        if route == "agent_get":
            self._send_json(200, store.get_agent(ids[0], user))
            return
        if route == "contact_list":
            self._send_json(200, {"contacts": store.list_contacts(user)})
            return
        if route == "contact_create":
            body = self._read_json_body()
            self._send_json(201, store.create_contact(
                body.get("name"), user,
                reference=body.get("reference"), attributes=body.get("attributes")))
            return
        if route == "contact_get":
            self._send_json(200, store.get_contact(ids[0], user))
            return
        if route == "queue_list":
            self._send_json(200, {"queues": store.list_queues(user)})
            return
        if route == "queue_create":
            body = self._read_json_body()
            self._send_json(201, store.create_queue(body.get("name"), user))
            return
        if route == "queue_get":
            self._send_json(200, store.get_queue(ids[0], user))
            return
        if route == "queue_members":
            self._send_json(200, {"members": store.list_queue_members(ids[0], user)})
            return
        if route == "queue_add_member":
            body = self._read_json_body()
            queue = store.add_agent_to_queue(ids[0], body.get("agent_id"), user)
            self._send_json(201, queue)
            return
        if route == "case_list":
            params = parse_qs(parsed.query)
            status = (params.get("status") or [None])[0]
            queue_id = (params.get("queue_id") or [None])[0]
            case_type = (params.get("case_type") or [None])[0]
            self._send_json(200, {"cases": store.list_cases(
                user, now=self._now_param(parsed), status=status,
                queue_id=queue_id, case_type=case_type)})
            return
        if route == "case_create":
            body = self._read_json_body()
            case = store.create_case(
                user, body.get("case_type"), body.get("subject"),
                contact_id=body.get("contact_id"), queue_id=body.get("queue_id"),
                agent_id=body.get("agent_id"),
                priority=body.get("priority", "normal") or "normal",
                due_at=body.get("due_at"))
            self._send_json(201, case)
            return
        if route == "case_get":
            self._send_json(200, store.get_case(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "case_assign":
            body = self._read_json_body()
            self._send_json(200, store.assign_case(
                ids[0], user, agent_id=body.get("agent_id"),
                queue_id=body.get("queue_id")))
            return
        if route == "case_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_case(ids[0], user, to_status))
            return
        if route == "callback_list":
            self._send_json(200, {"callbacks": store.list_callbacks(
                user, now=self._now_param(parsed))})
            return
        if route == "callback_create":
            body = self._read_json_body()
            self._send_json(201, store.schedule_callback(
                user, body.get("contact_id"), body.get("requested_for"),
                case_id=body.get("case_id"), agent_id=body.get("agent_id"),
                note=body.get("note")))
            return
        if route == "callback_get":
            self._send_json(200, store.get_callback(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "callback_complete":
            body = self._read_json_body() if self.headers.get("Content-Length") else {}
            self._send_json(200, store.complete_callback(ids[0], user, outcome=body.get("outcome")))
            return
        if route == "callback_cancel":
            self._send_json(200, store.cancel_callback(ids[0], user))
            return
        if route == "interaction_list":
            params = parse_qs(parsed.query)
            case_id = (params.get("case_id") or [None])[0]
            self._send_json(200, {"interactions": store.list_interactions(user, case_id=case_id)})
            return
        if route == "interaction_create":
            body = self._read_json_body()
            self._send_json(201, store.record_interaction(
                user, body.get("channel"), body.get("direction"), body.get("summary"),
                case_id=body.get("case_id"), contact_id=body.get("contact_id"),
                agent_id=body.get("agent_id"), outcome=body.get("outcome"),
                external_ref=body.get("external_ref")))
            return
        if route == "interaction_get":
            self._send_json(200, store.get_interaction(ids[0], user))
            return
        if route == "alert_list":
            self._send_json(200, {"alerts": store.list_alerts(user)})
            return
        if route == "alert_create":
            body = self._read_json_body()
            self._send_json(201, store.raise_alert(
                user, body.get("severity"), body.get("message"),
                source=body.get("source"), case_id=body.get("case_id")))
            return
        if route == "alert_get":
            self._send_json(200, store.get_alert(ids[0], user))
            return
        if route == "alert_ack":
            self._send_json(200, store.acknowledge_alert(ids[0], user))
            return
        if route == "alert_resolve":
            self._send_json(200, store.resolve_alert(ids[0], user))
            return
        if route == "rule_list":
            self._send_json(200, {"rules": store.list_rules(user)})
            return
        if route == "rule_create":
            body = self._read_json_body()
            self._send_json(201, store.create_rule(
                user, body.get("name"), body.get("case_type"),
                body.get("condition"), body.get("action_text")))
            return
        if route == "rule_get":
            self._send_json(200, store.get_rule(ids[0], user))
            return
        if route == "rule_update":
            body = self._read_json_body()
            self._send_json(200, store.update_rule(
                ids[0], user, condition=body.get("condition"),
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
    """Create (but do not start) the contact HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "ContactHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
