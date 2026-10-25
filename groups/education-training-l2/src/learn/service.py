"""HTTP service exposing the education & training records over JSON.

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
from .errors import LearnError, NotFoundError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "instructor",
    "carol": "learner",
    "dana": "auditor",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "Learn/0.1"
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
        if parts and parts[0] == "courses":
            if len(parts) == 1:
                if method == "GET":
                    return ("course_list", "catalog_read", ())
                if method == "POST":
                    return ("course_create", "catalog_write", ())
            if len(parts) == 2 and method == "GET":
                return ("course_get", "catalog_read", (parts[1],))
        if parts and parts[0] == "enrollments":
            if len(parts) == 1:
                if method == "GET":
                    return ("enrollment_list", "enrollment_read", ())
                if method == "POST":
                    return ("enrollment_create", "enrollment_write", ())
            if len(parts) == 2 and method == "GET":
                return ("enrollment_get", "enrollment_read", (parts[1],))
        if parts and parts[0] == "progress":
            if len(parts) == 1:
                if method == "GET":
                    return ("progress_list", "progress_read", ())
                if method == "POST":
                    return ("progress_create", "progress_write", ())
            if len(parts) == 2 and method == "GET":
                return ("progress_get", "progress_read", (parts[1],))
        if parts and parts[0] == "assessments":
            if len(parts) == 1:
                if method == "GET":
                    return ("assessment_list", "assessment_read", ())
                if method == "POST":
                    return ("assessment_create", "assessment_write", ())
            if len(parts) == 2 and method == "GET":
                return ("assessment_get", "assessment_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "responses":
                return ("assessment_response", "assessment_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("assessment_state", "assessment_write", (parts[1],))
        if parts and parts[0] == "credentials":
            if len(parts) == 1:
                if method == "GET":
                    return ("credential_list", "credential_read", ())
                if method == "POST":
                    return ("credential_create", "credential_write", ())
            if len(parts) == 2 and method == "GET":
                return ("credential_get", "credential_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("credential_status", "credential_write", (parts[1],))
        if parts and parts[0] == "compliance":
            if len(parts) == 1:
                if method == "GET":
                    return ("compliance_list", "compliance_read", ())
                if method == "POST":
                    return ("compliance_create", "compliance_write", ())
            if len(parts) == 2 and method == "GET":
                return ("compliance_get", "compliance_read", (parts[1],))
            if len(parts) == 3 and method == "GET" and parts[2] == "status":
                return ("compliance_status", "compliance_read", (parts[1],))
        if parts and parts[0] == "sessions":
            if len(parts) == 1:
                if method == "GET":
                    return ("session_list", "schedule_read", ())
                if method == "POST":
                    return ("session_create", "schedule_write", ())
            if len(parts) == 2 and method == "GET":
                return ("session_get", "schedule_read", (parts[1],))
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
        except LearnError as exc:
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
        if route == "course_list":
            self._send_json(200, {"courses": store.list_courses(user)})
            return
        if route == "course_create":
            body = self._read_json_body()
            course = store.create_course(
                body.get("title"), user,
                kind=body.get("kind") or "course",
                code=body.get("code"),
                description=body.get("description") or "",
            )
            self._send_json(201, course)
            return
        if route == "course_get":
            self._send_json(200, store.get_course(ids[0], user))
            return
        if route == "enrollment_list":
            enrollments = store.list_enrollments(
                user,
                learner_id=self._param(parsed, "learner_id"),
                course_id=self._param(parsed, "course_id"),
            )
            self._send_json(200, {"enrollments": enrollments})
            return
        if route == "enrollment_create":
            body = self._read_json_body()
            enrollment = store.create_enrollment(
                body.get("learner_id"), body.get("course_id"), user,
                kind=body.get("kind") or "enrollment",
            )
            self._send_json(201, enrollment)
            return
        if route == "enrollment_get":
            self._send_json(200, store.get_enrollment(ids[0], user))
            return
        if route == "progress_list":
            records = store.list_progress(
                user,
                learner_id=self._param(parsed, "learner_id"),
                course_id=self._param(parsed, "course_id"),
            )
            self._send_json(200, {"progress": records})
            return
        if route == "progress_create":
            body = self._read_json_body()
            record = store.record_progress(
                body.get("learner_id"), body.get("course_id"), body.get("status"), user,
                readiness=body.get("readiness"),
                percent_complete=body.get("percent_complete"),
                note=body.get("note") or "",
            )
            self._send_json(201, record)
            return
        if route == "progress_get":
            self._send_json(200, store.get_progress(ids[0], user))
            return
        if route == "assessment_list":
            records = store.list_assessments(
                user,
                learner_id=self._param(parsed, "learner_id"),
                course_id=self._param(parsed, "course_id"),
            )
            self._send_json(200, {"assessments": records})
            return
        if route == "assessment_create":
            body = self._read_json_body()
            record = store.create_assessment(
                body.get("title"), body.get("learner_id"), user,
                course_id=body.get("course_id"),
                session_id=body.get("session_id"),
                state=body.get("state") or "scheduled",
            )
            self._send_json(201, record)
            return
        if route == "assessment_get":
            self._send_json(200, store.get_assessment(ids[0], user))
            return
        if route == "assessment_response":
            body = self._read_json_body()
            record = store.add_assessment_response(
                ids[0], body.get("item_id"), body.get("response"), user
            )
            self._send_json(200, record)
            return
        if route == "assessment_state":
            body = self._read_json_body()
            self._send_json(200, store.set_assessment_state(ids[0], body.get("state"), user))
            return
        if route == "credential_list":
            records = store.list_credentials(user, learner_id=self._param(parsed, "learner_id"))
            self._send_json(200, {"credentials": records})
            return
        if route == "credential_create":
            body = self._read_json_body()
            record = store.create_credential(
                body.get("learner_id"), body.get("name"), user,
                kind=body.get("kind") or "certification",
                status=body.get("status") or "active",
                issued_date=body.get("issued_date"),
                expiry_date=body.get("expiry_date"),
            )
            self._send_json(201, record)
            return
        if route == "credential_get":
            self._send_json(200, store.get_credential(ids[0], user))
            return
        if route == "credential_status":
            body = self._read_json_body()
            self._send_json(200, store.set_credential_status(ids[0], body.get("status"), user))
            return
        if route == "compliance_list":
            records = store.list_compliance(
                user,
                as_of=self._param(parsed, "as_of"),
                learner_id=self._param(parsed, "learner_id"),
            )
            self._send_json(200, {"compliance": records})
            return
        if route == "compliance_create":
            body = self._read_json_body()
            record = store.create_compliance_assignment(
                body.get("learner_id"), body.get("course_id"), body.get("due_date"), user
            )
            self._send_json(201, record)
            return
        if route == "compliance_get":
            record = store.get_compliance_assignment(
                ids[0], user, as_of=self._param(parsed, "as_of")
            )
            self._send_json(200, record)
            return
        if route == "compliance_status":
            status = store.compliance_status(ids[0], user, as_of=self._param(parsed, "as_of"))
            self._send_json(200, status)
            return
        if route == "session_list":
            records = store.list_sessions(user, course_id=self._param(parsed, "course_id"))
            self._send_json(200, {"sessions": records})
            return
        if route == "session_create":
            body = self._read_json_body()
            record = store.create_session(
                body.get("title"), body.get("course_id"), body.get("starts_at"), user,
                ends_at=body.get("ends_at"),
                kind=body.get("kind") or "training",
                location=body.get("location") or "",
                learner_ids=body.get("learner_ids"),
            )
            self._send_json(201, record)
            return
        if route == "session_get":
            self._send_json(200, store.get_session(ids[0], user))
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
    """Create (but do not start) the learn HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "LearnHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
