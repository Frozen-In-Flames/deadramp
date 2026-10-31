"""HTTP service exposing the communications functions over a JSON REST API.

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
from .errors import CommError, NotFoundError, PermissionDenied, ValidationError

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
    server_version = "Comm/0.1"
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
            return ("search", "records_read", ())
        if method == "POST" and parts == ["dispatch-due"]:
            return ("dispatch_due", "dispatch", ())
        if parts and parts[0] == "contacts":
            if len(parts) == 1:
                if method == "GET":
                    return ("contact_list", "contact_read", ())
                if method == "POST":
                    return ("contact_create", "contact_write", ())
            if len(parts) == 2 and method == "GET":
                return ("contact_get", "contact_read", (parts[1],))
        if parts and parts[0] == "groups":
            if len(parts) == 1:
                if method == "GET":
                    return ("group_list", "contact_read", ())
                if method == "POST":
                    return ("group_create", "group_write", ())
            if len(parts) == 3 and parts[2] == "members":
                if method == "GET":
                    return ("group_members", "contact_read", (parts[1],))
                if method == "POST":
                    return ("group_add_member", "group_write", (parts[1],))
        if parts and parts[0] == "channels":
            if len(parts) == 1:
                if method == "GET":
                    return ("channel_list", "channel_read", ())
                if method == "POST":
                    return ("channel_create", "channel_write", ())
            if len(parts) == 2 and method == "GET":
                return ("channel_get", "channel_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "enabled" and method == "POST":
                return ("channel_set_enabled", "channel_write", (parts[1],))
        if parts and parts[0] == "templates":
            if len(parts) == 1:
                if method == "GET":
                    return ("template_list", "template_read", ())
                if method == "POST":
                    return ("template_create", "template_write", ())
            if len(parts) == 2 and method == "GET":
                return ("template_get", "template_read", (parts[1],))
        if parts and parts[0] == "messages":
            if len(parts) == 1:
                if method == "GET":
                    return ("message_list", "records_read", ())
                if method == "POST":
                    return ("message_create", "message_compose", ())
            if len(parts) == 2 and method == "GET":
                return ("message_get", "records_read", (parts[1],))
            if len(parts) == 3:
                if method == "GET" and parts[2] == "deliveries":
                    return ("message_deliveries", "records_read", (parts[1],))
                if method == "GET" and parts[2] == "ack-status":
                    return ("message_ack_status", "records_read", (parts[1],))
                if method == "POST" and parts[2] == "dispatch":
                    return ("message_dispatch", "dispatch", (parts[1],))
        if parts and parts[0] == "deliveries":
            if len(parts) == 3 and parts[2] == "ack" and method == "POST":
                return ("delivery_ack", "ack_record", (parts[1],))
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
        except CommError as exc:
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
        if route == "contact_list":
            self._send_json(200, {"contacts": store.list_contacts(user)})
            return
        if route == "contact_create":
            body = self._read_json_body()
            self._send_json(201, store.create_contact(body.get("name"), body.get("addresses"), user))
            return
        if route == "contact_get":
            self._send_json(200, store.get_contact(ids[0], user))
            return
        if route == "group_list":
            self._send_json(200, {"groups": store.list_groups(user)})
            return
        if route == "group_create":
            body = self._read_json_body()
            self._send_json(201, store.create_group(body.get("name"), user))
            return
        if route == "group_members":
            self._send_json(200, {"members": store.list_group_members(ids[0], user)})
            return
        if route == "group_add_member":
            body = self._read_json_body()
            group = store.add_to_group(ids[0], body.get("contact_id"), user)
            self._send_json(201, group)
            return
        if route == "channel_list":
            self._send_json(200, {"channels": store.list_channels(user)})
            return
        if route == "channel_create":
            body = self._read_json_body()
            enabled = body.get("enabled", True)
            if enabled is None:
                enabled = True
            self._send_json(201, store.create_channel(body.get("kind"), body.get("name"), user, enabled=enabled))
            return
        if route == "channel_get":
            self._send_json(200, store.get_channel(ids[0], user))
            return
        if route == "channel_set_enabled":
            body = self._read_json_body()
            self._send_json(200, store.set_channel_enabled(ids[0], body.get("enabled"), user))
            return
        if route == "template_list":
            self._send_json(200, {"templates": store.list_templates(user)})
            return
        if route == "template_create":
            body = self._read_json_body()
            self._send_json(201, store.create_template(body.get("name"), body.get("subject"), body.get("body"), user))
            return
        if route == "template_get":
            self._send_json(200, store.get_template(ids[0], user))
            return
        if route == "message_list":
            self._send_json(200, {"messages": store.list_messages(user)})
            return
        if route == "message_create":
            body = self._read_json_body()
            message = store.compose_message(
                user,
                subject=body.get("subject"),
                body=body.get("body"),
                template_id=body.get("template_id"),
                variables=body.get("variables"),
                contact_ids=body.get("contact_ids"),
                group_ids=body.get("group_ids"),
                channel_kinds=body.get("channel_kinds"),
                send_at=body.get("send_at"),
                require_ack=body.get("require_ack", False) or False,
            )
            self._send_json(201, message)
            return
        if route == "message_get":
            self._send_json(200, store.get_message(ids[0], user))
            return
        if route == "message_deliveries":
            self._send_json(200, {"deliveries": store.list_deliveries(ids[0], user)})
            return
        if route == "message_ack_status":
            self._send_json(200, store.ack_status(ids[0], user))
            return
        if route == "message_dispatch":
            # Body may optionally carry {"now": ...} for testing.
            body = self._read_json_body() if self.headers.get("Content-Length") else {}
            now = body.get("now") if isinstance(body, dict) else None
            self._send_json(200, store.dispatch_message(ids[0], user, now=now))
            return
        if route == "dispatch_due":
            body = self._read_json_body() if self.headers.get("Content-Length") else {}
            now = body.get("now") if isinstance(body, dict) else None
            self._send_json(200, store.dispatch_due(user, now=now))
            return
        if route == "delivery_ack":
            self._send_json(200, store.acknowledge(ids[0], user))
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
    """Create (but do not start) the comm HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "CommHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
