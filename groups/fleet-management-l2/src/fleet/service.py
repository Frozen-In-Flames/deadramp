"""HTTP service exposing the fleet-management records over JSON.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

The store records every successful mutation. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and ``audit_read``.
Errors are JSON ``{error: msg}`` with 400 (validation), 401 (auth),
403 (permission) or 404 (not found); handlers never leak a stack
trace to the client.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import FleetError, NotFoundError, PermissionDenied, ValidationError

USERS = {
    "alice": "admin",
    "bob": "manager",
    "carol": "viewer",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "Fleet/0.1"
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
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "search", ())
        if method == "GET" and parts == ["reports", "summary"]:
            return ("report_summary", "read", ())
        if parts and parts[0] == "vehicles":
            if len(parts) == 1:
                if method == "GET":
                    return ("vehicle_list", "read", ())
                if method == "POST":
                    return ("vehicle_create", "write", ())
            if len(parts) == 2 and method == "GET":
                return ("vehicle_get", "read", (parts[1],))
        if parts and parts[0] == "operators":
            if len(parts) == 1:
                if method == "GET":
                    return ("operator_list", "read", ())
                if method == "POST":
                    return ("operator_create", "write", ())
            if len(parts) == 2 and method == "GET":
                return ("operator_get", "read", (parts[1],))
        if parts and parts[0] == "reservations":
            if len(parts) == 1:
                if method == "GET":
                    return ("reservation_list", "read", ())
                if method == "POST":
                    return ("reservation_create", "write", ())
            if len(parts) == 2 and method == "GET":
                return ("reservation_get", "read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("reservation_status", "write", (parts[1],))
        if parts and parts[0] == "checkins":
            if len(parts) == 1:
                if method == "GET":
                    return ("checkin_list", "read", ())
                if method == "POST":
                    return ("checkin_create", "write", ())
        if parts and parts[0] == "usage":
            if len(parts) == 1:
                if method == "GET":
                    return ("usage_list", "read", ())
                if method == "POST":
                    return ("usage_create", "write", ())
        if parts and parts[0] == "maintenance":
            if len(parts) == 1:
                if method == "GET":
                    return ("maintenance_list", "read", ())
                if method == "POST":
                    return ("maintenance_create", "write", ())
            if len(parts) == 2 and method == "GET":
                return ("maintenance_get", "read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "complete":
                return ("maintenance_complete", "write", (parts[1],))
        if parts and parts[0] == "charging-sessions":
            if len(parts) == 1:
                if method == "GET":
                    return ("charging_list", "read", ())
                if method == "POST":
                    return ("charging_create", "write", ())
            if len(parts) == 2 and method == "GET":
                return ("charging_get", "read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "close":
                return ("charging_close", "write", (parts[1],))
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
        except FleetError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    @staticmethod
    def _param(parsed, name):
        params = parse_qs(parsed.query)
        values = params.get(name)
        return values[0] if values else None

    def _execute(self, route, user, ids, parsed):
        store = self.store
        if route == "audit_read":
            entries = self.audit.entries() if self.audit is not None else []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "search":
            self._send_json(200, store.search(self._param(parsed, "q"), user))
            return
        if route == "report_summary":
            self._send_json(200, store.summary_report(user))
            return
        if route == "vehicle_list":
            self._send_json(200, {"vehicles": store.list_vehicles(user)})
            return
        if route == "vehicle_create":
            body = self._read_json_body()
            rec = store.create_vehicle(body.get("label"), body.get("vehicle_type"), user,
                                       status=body.get("status") or "active")
            self._send_json(201, rec)
            return
        if route == "vehicle_get":
            self._send_json(200, store.get_vehicle(ids[0], user))
            return
        if route == "operator_list":
            self._send_json(200, {"operators": store.list_operators(user)})
            return
        if route == "operator_create":
            body = self._read_json_body()
            rec = store.create_operator(body.get("operator_ref"), body.get("credential_kind"), user,
                                        credential_status=body.get("credential_status") or "active")
            self._send_json(201, rec)
            return
        if route == "operator_get":
            self._send_json(200, store.get_operator(ids[0], user))
            return
        if route == "reservation_list":
            recs = store.list_reservations(vehicle_id=self._param(parsed, "vehicle_id"),
                                           status=self._param(parsed, "status"), actor=user)
            self._send_json(200, {"reservations": recs})
            return
        if route == "reservation_create":
            body = self._read_json_body()
            rec = store.create_reservation(body.get("vehicle_id"), body.get("operator_ref"),
                                           body.get("start"), body.get("end"), user)
            self._send_json(201, rec)
            return
        if route == "reservation_get":
            self._send_json(200, store.get_reservation(ids[0], user))
            return
        if route == "reservation_status":
            body = self._read_json_body()
            self._send_json(200, store.set_reservation_status(ids[0], body.get("status"), user))
            return
        if route == "checkin_list":
            recs = store.list_checkins(reservation_id=self._param(parsed, "reservation_id"), actor=user)
            self._send_json(200, {"checkins": recs})
            return
        if route == "checkin_create":
            body = self._read_json_body()
            rec = store.record_checkin(body.get("reservation_id"), body.get("kind"),
                                       body.get("odometer"), user)
            self._send_json(201, rec)
            return
        if route == "usage_list":
            recs = store.list_usage(vehicle_id=self._param(parsed, "vehicle_id"), actor=user)
            self._send_json(200, {"usage": recs})
            return
        if route == "usage_create":
            body = self._read_json_body()
            rec = store.record_usage(body.get("vehicle_id"), body.get("odometer_reading"), user)
            self._send_json(201, rec)
            return
        if route == "maintenance_list":
            recs = store.list_maintenance(vehicle_id=self._param(parsed, "vehicle_id"),
                                          actor=user, as_of=self._param(parsed, "as_of"))
            self._send_json(200, {"maintenance": recs})
            return
        if route == "maintenance_create":
            body = self._read_json_body()
            rec = store.create_maintenance(body.get("vehicle_id"), body.get("kind"),
                                           body.get("due_date"), user)
            self._send_json(201, rec)
            return
        if route == "maintenance_get":
            self._send_json(200, store.get_maintenance(ids[0], user,
                                                       as_of=self._param(parsed, "as_of")))
            return
        if route == "maintenance_complete":
            body = self._read_json_body()
            self._send_json(200, store.complete_maintenance(ids[0], user,
                                                            completed_date=body.get("completed_date")))
            return
        if route == "charging_list":
            self._send_json(200, {"charging_sessions": store.list_charging_sessions(user)})
            return
        if route == "charging_create":
            body = self._read_json_body()
            watt_hours = body.get("watt_hours")
            rec = store.create_charging_session(body.get("station_ref"), body.get("operator_ref"), user,
                                                started_utc=body.get("started_utc"),
                                                watt_hours=0 if watt_hours is None else watt_hours)
            self._send_json(201, rec)
            return
        if route == "charging_get":
            self._send_json(200, store.get_charging_session(ids[0], user))
            return
        if route == "charging_close":
            body = self._read_json_body()
            self._send_json(200, store.close_charging_session(ids[0], user,
                                                              ended_utc=body.get("ended_utc"),
                                                              watt_hours=body.get("watt_hours")))
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
    """Create (but do not start) the fleet HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "FleetHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
