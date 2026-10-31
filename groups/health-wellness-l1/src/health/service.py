"""HTTP service exposing the health & wellness records over JSON.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

Privacy discipline at this boundary: every POST body is checked
against its endpoint's named field list before the store is called;
any JSON key outside that list is rejected with ``ValidationError``
(HTTP 400), so a caller cannot smuggle a diagnosis, a note, or an
identifier into a record by adding a field.

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
from .errors import HealthError, NotFoundError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "clinician",
    "carol": "member",
    "dana": "auditor",
}
DEMO_USERS = USERS


def _reject_extra_keys(body, allowed):
    """Refuse any JSON key outside the endpoint's named field list."""
    extra = sorted(set(body) - set(allowed))
    if extra:
        raise ValidationError("unknown field(s): %s" % (", ".join(extra),))


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "Health/0.1"
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
        if method == "GET" and parts == ["report"]:
            return ("report", "report_read", ())
        if method == "GET" and len(parts) == 2 and parts[0] == "scorecard":
            return ("scorecard", "report_read", (parts[1],))
        if parts and parts[0] == "participants":
            if len(parts) == 1:
                if method == "GET":
                    return ("participant_list", "participant_read", ())
                if method == "POST":
                    return ("participant_create", "participant_write", ())
            if len(parts) == 2 and method == "GET":
                return ("participant_get", "participant_read", (parts[1],))
        if parts and parts[0] == "programs":
            if len(parts) == 1:
                if method == "GET":
                    return ("program_list", "program_read", ())
                if method == "POST":
                    return ("program_create", "program_write", ())
            if len(parts) == 2 and method == "GET":
                return ("program_get", "program_read", (parts[1],))
        if parts and parts[0] == "enrollments":
            if len(parts) == 1:
                if method == "GET":
                    return ("enrollment_list", "enrollment_read", ())
                if method == "POST":
                    return ("enrollment_create", "enrollment_write", ())
            if len(parts) == 2 and method == "GET":
                return ("enrollment_get", "enrollment_read", (parts[1],))
        if parts and parts[0] == "measurements":
            if len(parts) == 1:
                if method == "GET":
                    return ("measurement_list", "measurement_read", ())
                if method == "POST":
                    return ("measurement_create", "measurement_write", ())
            if len(parts) == 2 and method == "GET":
                return ("measurement_get", "measurement_read", (parts[1],))
        if parts and parts[0] == "plans":
            if len(parts) == 1:
                if method == "GET":
                    return ("plan_list", "plan_read", ())
                if method == "POST":
                    return ("plan_create", "plan_write", ())
            if len(parts) == 2 and method == "GET":
                return ("plan_get", "plan_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "complete":
                return ("plan_complete", "plan_write", (parts[1],))
        if parts and parts[0] == "activities":
            if len(parts) == 1:
                if method == "GET":
                    return ("activity_list", "activity_read", ())
                if method == "POST":
                    return ("activity_create", "activity_write", ())
            if len(parts) == 2 and method == "GET":
                return ("activity_get", "activity_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("activity_state", "activity_write", (parts[1],))
        if parts and parts[0] == "eligibility":
            if len(parts) == 1:
                if method == "GET":
                    return ("eligibility_list", "eligibility_read", ())
                if method == "POST":
                    return ("eligibility_create", "eligibility_write", ())
            if len(parts) == 2 and method == "GET":
                return ("eligibility_get", "eligibility_read", (parts[1],))
            if len(parts) == 3 and method == "GET" and parts[2] == "status":
                return ("eligibility_status", "eligibility_read", (parts[1],))
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
        except HealthError as exc:
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
        if route == "report":
            self._send_json(200, store.report(user, as_of=self._param(parsed, "as_of")))
            return
        if route == "scorecard":
            self._send_json(200, store.scorecard(ids[0], user,
                                                 as_of=self._param(parsed, "as_of")))
            return
        if route == "participant_list":
            self._send_json(200, {"participants": store.list_participants(user)})
            return
        if route == "participant_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_ref", "kind"})
            record = store.create_participant(
                body.get("participant_ref"), user,
                kind=body.get("kind") or "patient",
            )
            self._send_json(201, record)
            return
        if route == "participant_get":
            self._send_json(200, store.get_participant(ids[0], user))
            return
        if route == "program_list":
            self._send_json(200, {"programs": store.list_programs(user)})
            return
        if route == "program_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"title", "kind", "code", "description"})
            record = store.create_program(
                body.get("title"), user,
                kind=body.get("kind") or "program",
                code=body.get("code"),
                description=body.get("description") or "",
            )
            self._send_json(201, record)
            return
        if route == "program_get":
            self._send_json(200, store.get_program(ids[0], user))
            return
        if route == "enrollment_list":
            enrollments = store.list_enrollments(
                user,
                participant_id=self._param(parsed, "participant_id"),
                program_id=self._param(parsed, "program_id"),
                as_of=self._param(parsed, "as_of"),
            )
            self._send_json(200, {"enrollments": enrollments})
            return
        if route == "enrollment_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_id", "program_id", "kind"})
            record = store.create_enrollment(
                body.get("participant_id"), body.get("program_id"), user,
                kind=body.get("kind") or "enrollment",
            )
            self._send_json(201, record)
            return
        if route == "enrollment_get":
            record = store.get_enrollment(ids[0], user,
                                          as_of=self._param(parsed, "as_of"))
            self._send_json(200, record)
            return
        if route == "measurement_list":
            records = store.list_measurements(
                user,
                participant_id=self._param(parsed, "participant_id"),
                program_id=self._param(parsed, "program_id"),
                metric_name=self._param(parsed, "metric_name"),
            )
            self._send_json(200, {"measurements": records})
            return
        if route == "measurement_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_id", "metric_name", "value",
                                      "unit", "recorded_on", "program_id"})
            record = store.record_measurement(
                body.get("participant_id"), body.get("metric_name"),
                body.get("value"), body.get("unit"), body.get("recorded_on"),
                user,
                program_id=body.get("program_id"),
            )
            self._send_json(201, record)
            return
        if route == "measurement_get":
            self._send_json(200, store.get_measurement(ids[0], user))
            return
        if route == "plan_list":
            records = store.list_plans(
                user,
                participant_id=self._param(parsed, "participant_id"),
                program_id=self._param(parsed, "program_id"),
                as_of=self._param(parsed, "as_of"),
            )
            self._send_json(200, {"plans": records})
            return
        if route == "plan_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_id", "program_id", "title",
                                      "due_date", "kind"})
            record = store.create_plan(
                body.get("participant_id"), body.get("program_id"),
                body.get("title"), body.get("due_date"), user,
                kind=body.get("kind") or "care_plan",
            )
            self._send_json(201, record)
            return
        if route == "plan_get":
            record = store.get_plan(ids[0], user, as_of=self._param(parsed, "as_of"))
            self._send_json(200, record)
            return
        if route == "plan_complete":
            body = self._read_json_body()
            _reject_extra_keys(body, {"completed_on"})
            self._send_json(200, store.complete_plan(ids[0], body.get("completed_on"), user))
            return
        if route == "activity_list":
            records = store.list_activities(
                user,
                participant_id=self._param(parsed, "participant_id"),
                program_id=self._param(parsed, "program_id"),
            )
            self._send_json(200, {"activities": records})
            return
        if route == "activity_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_id", "title", "starts_at",
                                      "program_id", "ends_at", "kind"})
            record = store.create_activity(
                body.get("participant_id"), body.get("title"),
                body.get("starts_at"), user,
                program_id=body.get("program_id"),
                ends_at=body.get("ends_at"),
                kind=body.get("kind") or "appointment",
            )
            self._send_json(201, record)
            return
        if route == "activity_get":
            self._send_json(200, store.get_activity(ids[0], user))
            return
        if route == "activity_state":
            body = self._read_json_body()
            _reject_extra_keys(body, {"state"})
            self._send_json(200, store.set_activity_state(ids[0], body.get("state"), user))
            return
        if route == "eligibility_list":
            records = store.list_eligibilities(
                user,
                participant_id=self._param(parsed, "participant_id"),
                as_of=self._param(parsed, "as_of"),
            )
            self._send_json(200, {"eligibility": records})
            return
        if route == "eligibility_create":
            body = self._read_json_body()
            _reject_extra_keys(body, {"participant_id", "plan_ref", "coverage_start",
                                      "program_id", "coverage_end"})
            record = store.create_eligibility(
                body.get("participant_id"), body.get("plan_ref"),
                body.get("coverage_start"), user,
                program_id=body.get("program_id"),
                coverage_end=body.get("coverage_end"),
            )
            self._send_json(201, record)
            return
        if route == "eligibility_get":
            record = store.get_eligibility(ids[0], user,
                                            as_of=self._param(parsed, "as_of"))
            self._send_json(200, record)
            return
        if route == "eligibility_status":
            status = store.eligibility_status(ids[0], user,
                                               as_of=self._param(parsed, "as_of"))
            self._send_json(200, status)
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
    """Create (but do not start) the health HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "HealthHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
