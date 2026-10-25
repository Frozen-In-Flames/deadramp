"""HTTP service exposing the human resources records over JSON.

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
from .errors import HRError, NotFoundError, PermissionDenied, ValidationError

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "hr_specialist",
    "carol": "employee",
    "dana": "auditor",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    server_version = "HR/0.1"
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
        if parts and parts[0] == "persons":
            if len(parts) == 1:
                if method == "GET":
                    return ("person_list", "person_read", ())
                if method == "POST":
                    return ("person_create", "person_write", ())
            if len(parts) == 2 and method == "GET":
                return ("person_get", "person_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("person_status", "person_write", (parts[1],))
        if parts and parts[0] == "positions":
            if len(parts) == 1:
                if method == "GET":
                    return ("position_list", "position_read", ())
                if method == "POST":
                    return ("position_create", "position_write", ())
            if len(parts) == 2 and method == "GET":
                return ("position_get", "position_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("position_status", "position_write", (parts[1],))
        if parts and parts[0] == "vacancies":
            if len(parts) == 1:
                if method == "GET":
                    return ("vacancy_list", "vacancy_read", ())
                if method == "POST":
                    return ("vacancy_create", "vacancy_write", ())
            if len(parts) == 2 and method == "GET":
                return ("vacancy_get", "vacancy_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("vacancy_status", "vacancy_write", (parts[1],))
        if parts and parts[0] == "applications":
            if len(parts) == 1:
                if method == "GET":
                    return ("application_list", "application_read", ())
                if method == "POST":
                    return ("application_create", "application_write", ())
            if len(parts) == 2 and method == "GET":
                return ("application_get", "application_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "stage":
                return ("application_stage", "application_write", (parts[1],))
        if parts and parts[0] == "evaluations":
            if len(parts) == 1:
                if method == "GET":
                    return ("evaluation_list", "evaluation_read", ())
                if method == "POST":
                    return ("evaluation_create", "evaluation_write", ())
            if len(parts) == 2 and method == "GET":
                return ("evaluation_get", "evaluation_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "entries":
                return ("evaluation_entry", "evaluation_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("evaluation_state", "evaluation_write", (parts[1],))
        if parts and parts[0] == "lifecycle-cases":
            if len(parts) == 1:
                if method == "GET":
                    return ("lifecycle_list", "lifecycle_read", ())
                if method == "POST":
                    return ("lifecycle_create", "lifecycle_write", ())
            if len(parts) == 2 and method == "GET":
                return ("lifecycle_get", "lifecycle_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "tasks":
                return ("lifecycle_task_add", "lifecycle_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "cancel":
                return ("lifecycle_cancel", "lifecycle_write", (parts[1],))
            if len(parts) == 5 and method == "POST" and parts[2] == "tasks" and parts[4] == "state":
                return ("lifecycle_task_state", "lifecycle_write", (parts[1], parts[3]))
        if parts and parts[0] == "performance-reviews":
            if len(parts) == 1:
                if method == "GET":
                    return ("performance_list", "performance_read", ())
                if method == "POST":
                    return ("performance_create", "performance_write", ())
            if len(parts) == 2 and method == "GET":
                return ("performance_get", "performance_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("performance_state", "performance_write", (parts[1],))
        if parts and parts[0] == "benefits":
            if len(parts) == 1:
                if method == "GET":
                    return ("benefits_list", "benefits_read", ())
                if method == "POST":
                    return ("benefits_create", "benefits_write", ())
            if len(parts) == 2 and method == "GET":
                return ("benefits_get", "benefits_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("benefits_state", "benefits_write", (parts[1],))
        if parts and parts[0] == "cases":
            if len(parts) == 1:
                if method == "GET":
                    return ("case_list", "case_read", ())
                if method == "POST":
                    return ("case_create", "case_write", ())
            if len(parts) == 2 and method == "GET":
                return ("case_get", "case_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("case_state", "case_write", (parts[1],))
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
        except HRError as exc:
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
            self._send_json(200, store.report(user))
            return
        if route == "person_list":
            self._send_json(200, {"persons": store.list_persons(user)})
            return
        if route == "person_create":
            body = self._read_json_body()
            record = store.create_person(
                body.get("person_ref"), user, kind=body.get("kind") or "applicant"
            )
            self._send_json(201, record)
            return
        if route == "person_get":
            self._send_json(200, store.get_person(ids[0], user))
            return
        if route == "person_status":
            body = self._read_json_body()
            self._send_json(200, store.set_person_status(ids[0], body.get("status"), user))
            return
        if route == "position_list":
            self._send_json(200, {"positions": store.list_positions(user)})
            return
        if route == "position_create":
            body = self._read_json_body()
            record = store.create_position(
                body.get("title"), user,
                series=body.get("series"),
                grade=body.get("grade"),
                organization=body.get("organization") or "",
            )
            self._send_json(201, record)
            return
        if route == "position_get":
            self._send_json(200, store.get_position(ids[0], user))
            return
        if route == "position_status":
            body = self._read_json_body()
            self._send_json(200, store.set_position_status(ids[0], body.get("status"), user))
            return
        if route == "vacancy_list":
            records = store.list_vacancies(user, position_id=self._param(parsed, "position_id"))
            self._send_json(200, {"vacancies": records})
            return
        if route == "vacancy_create":
            body = self._read_json_body()
            record = store.create_vacancy(
                body.get("position_id"), body.get("title"), user,
                opens_on=body.get("opens_on"),
                closes_on=body.get("closes_on"),
            )
            self._send_json(201, record)
            return
        if route == "vacancy_get":
            self._send_json(200, store.get_vacancy(ids[0], user))
            return
        if route == "vacancy_status":
            body = self._read_json_body()
            self._send_json(200, store.set_vacancy_status(ids[0], body.get("status"), user))
            return
        if route == "application_list":
            records = store.list_applications(
                user,
                person_ref=self._param(parsed, "person_ref"),
                vacancy_id=self._param(parsed, "vacancy_id"),
            )
            self._send_json(200, {"applications": records})
            return
        if route == "application_create":
            body = self._read_json_body()
            record = store.create_application(body.get("person_ref"), body.get("vacancy_id"), user)
            self._send_json(201, record)
            return
        if route == "application_get":
            self._send_json(200, store.get_application(ids[0], user))
            return
        if route == "application_stage":
            body = self._read_json_body()
            self._send_json(200, store.set_application_stage(ids[0], body.get("stage"), user))
            return
        if route == "evaluation_list":
            records = store.list_evaluations(user, application_id=self._param(parsed, "application_id"))
            self._send_json(200, {"evaluations": records})
            return
        if route == "evaluation_create":
            body = self._read_json_body()
            record = store.create_evaluation(
                body.get("application_id"), body.get("kind"), body.get("title"), user
            )
            self._send_json(201, record)
            return
        if route == "evaluation_get":
            self._send_json(200, store.get_evaluation(ids[0], user))
            return
        if route == "evaluation_entry":
            body = self._read_json_body()
            record = store.add_evaluation_entry(
                ids[0], body.get("rater_ref"), body.get("rating"), body.get("comment"), user
            )
            self._send_json(200, record)
            return
        if route == "evaluation_state":
            body = self._read_json_body()
            self._send_json(200, store.set_evaluation_state(ids[0], body.get("state"), user))
            return
        if route == "lifecycle_list":
            records = store.list_lifecycle_cases(user, person_ref=self._param(parsed, "person_ref"))
            self._send_json(200, {"lifecycle_cases": records})
            return
        if route == "lifecycle_create":
            body = self._read_json_body()
            record = store.create_lifecycle_case(
                body.get("person_ref"), body.get("kind"), user,
                task_titles=body.get("task_titles"),
            )
            self._send_json(201, record)
            return
        if route == "lifecycle_get":
            self._send_json(200, store.get_lifecycle_case(ids[0], user))
            return
        if route == "lifecycle_task_add":
            body = self._read_json_body()
            self._send_json(200, store.add_task(ids[0], body.get("title"), user))
            return
        if route == "lifecycle_task_state":
            body = self._read_json_body()
            self._send_json(200, store.set_task_state(ids[0], ids[1], body.get("state"), user))
            return
        if route == "lifecycle_cancel":
            self._read_json_body()
            self._send_json(200, store.cancel_case(ids[0], user))
            return
        if route == "performance_list":
            records = store.list_performance_reviews(user, person_ref=self._param(parsed, "person_ref"))
            self._send_json(200, {"performance_reviews": records})
            return
        if route == "performance_create":
            body = self._read_json_body()
            record = store.create_performance_review(
                body.get("person_ref"), body.get("cycle"), user,
                period_start=body.get("period_start"),
                period_end=body.get("period_end"),
            )
            self._send_json(201, record)
            return
        if route == "performance_get":
            self._send_json(200, store.get_performance_review(ids[0], user))
            return
        if route == "performance_state":
            body = self._read_json_body()
            self._send_json(200, store.set_review_state(
                ids[0], body.get("state"), user, outcome=body.get("outcome")
            ))
            return
        if route == "benefits_list":
            records = store.list_benefits_records(user, person_ref=self._param(parsed, "person_ref"))
            self._send_json(200, {"benefits": records})
            return
        if route == "benefits_create":
            body = self._read_json_body()
            record = store.create_benefits_record(
                body.get("person_ref"), body.get("kind"), body.get("plan_ref"), user
            )
            self._send_json(201, record)
            return
        if route == "benefits_get":
            self._send_json(200, store.get_benefits_record(ids[0], user))
            return
        if route == "benefits_state":
            body = self._read_json_body()
            self._send_json(200, store.set_benefits_state(ids[0], body.get("state"), user))
            return
        if route == "case_list":
            records = store.list_cases(user, person_ref=self._param(parsed, "person_ref"))
            self._send_json(200, {"cases": records})
            return
        if route == "case_create":
            body = self._read_json_body()
            record = store.create_case(
                body.get("person_ref"), body.get("kind"), body.get("title"), user
            )
            self._send_json(201, record)
            return
        if route == "case_get":
            self._send_json(200, store.get_case(ids[0], user))
            return
        if route == "case_state":
            body = self._read_json_body()
            self._send_json(200, store.set_case_state(ids[0], body.get("state"), user))
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
    """Create (but do not start) the hr HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "HRHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
