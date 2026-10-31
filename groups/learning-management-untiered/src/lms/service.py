"""HTTP service exposing the learning management records over JSON.

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
from .errors import LmsError, NotFoundError, PermissionDenied, ValidationError

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
    server_version = "LMS/0.1"
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
        if method == "GET" and parts == ["search"]:
            return ("search", "report_read", ())
        if parts and parts[0] == "learners":
            if len(parts) == 1:
                if method == "GET":
                    return ("learner_list", "learner_read", ())
                if method == "POST":
                    return ("learner_create", "learner_write", ())
            if len(parts) == 2 and method == "GET":
                return ("learner_get", "learner_read", (parts[1],))
        if parts and parts[0] == "courses":
            if len(parts) == 1:
                if method == "GET":
                    return ("course_list", "catalog_read", ())
                if method == "POST":
                    return ("course_create", "catalog_write", ())
            if len(parts) == 2 and method == "GET":
                return ("course_get", "catalog_read", (parts[1],))
        if parts and parts[0] == "content-items":
            if len(parts) == 1:
                if method == "GET":
                    return ("content_list", "catalog_read", ())
                if method == "POST":
                    return ("content_create", "catalog_write", ())
            if len(parts) == 2 and method == "GET":
                return ("content_get", "catalog_read", (parts[1],))
        if parts and parts[0] == "lesson-plans":
            if len(parts) == 1:
                if method == "GET":
                    return ("lesson_plan_list", "catalog_read", ())
                if method == "POST":
                    return ("lesson_plan_create", "catalog_write", ())
            if len(parts) == 2 and method == "GET":
                return ("lesson_plan_get", "catalog_read", (parts[1],))
        if parts and parts[0] == "events":
            if len(parts) == 1:
                if method == "GET":
                    return ("event_list", "registration_read", ())
                if method == "POST":
                    return ("event_create", "registration_write", ())
            if len(parts) == 2 and method == "GET":
                return ("event_get", "registration_read", (parts[1],))
        if parts and parts[0] == "registrations":
            if len(parts) == 1:
                if method == "GET":
                    return ("registration_list", "registration_read", ())
                if method == "POST":
                    return ("registration_create", "registration_write", ())
            if len(parts) == 2 and method == "GET":
                return ("registration_get", "registration_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("registration_state", "registration_write", (parts[1],))
        if parts and parts[0] == "authorizations":
            if len(parts) == 1:
                if method == "GET":
                    return ("authorization_list", "authorization_read", ())
                if method == "POST":
                    return ("authorization_create", "authorization_write", ())
            if len(parts) == 2 and method == "GET":
                return ("authorization_get", "authorization_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "decide":
                return ("authorization_decide", "authorization_write", (parts[1],))
        if parts and parts[0] == "development-plans":
            if len(parts) == 1:
                if method == "GET":
                    return ("plan_list", "plan_read", ())
                if method == "POST":
                    return ("plan_create", "plan_write", ())
            if len(parts) == 2 and method == "GET":
                return ("plan_get", "plan_read", (parts[1],))
        if parts and parts[0] == "competencies":
            if len(parts) == 1:
                if method == "GET":
                    return ("competency_list", "competency_read", ())
                if method == "POST":
                    return ("competency_create", "competency_write", ())
            if len(parts) == 2 and method == "GET":
                return ("competency_get", "competency_read", (parts[1],))
        if parts and parts[0] == "learner-competencies":
            if len(parts) == 1:
                if method == "GET":
                    return ("learner_competency_list", "competency_read", ())
                if method == "POST":
                    return ("learner_competency_create", "competency_write", ())
            if len(parts) == 2 and method == "GET":
                return ("learner_competency_get", "competency_read", (parts[1],))
        if parts and parts[0] == "progress":
            if len(parts) == 1:
                if method == "GET":
                    return ("progress_list", "progress_read", ())
                if method == "POST":
                    return ("progress_create", "progress_write", ())
            if len(parts) == 2 and method == "GET":
                return ("progress_get", "progress_read", (parts[1],))
        if parts and parts[0] == "statements":
            if len(parts) == 1:
                if method == "GET":
                    return ("statement_list", "experience_read", ())
                if method == "POST":
                    return ("statement_create", "experience_write", ())
            if len(parts) == 2 and method == "GET":
                return ("statement_get", "experience_read", (parts[1],))
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
        if parts and parts[0] == "workflows":
            if len(parts) == 1:
                if method == "GET":
                    return ("workflow_list", "workflow_read", ())
                if method == "POST":
                    return ("workflow_create", "workflow_write", ())
            if len(parts) == 2 and method == "GET":
                return ("workflow_get", "workflow_read", (parts[1],))
        if parts and parts[0] == "notifications":
            if len(parts) == 1:
                if method == "GET":
                    return ("notification_list", "workflow_read", ())
                if method == "POST":
                    return ("notification_create", "workflow_write", ())
            if len(parts) == 2 and method == "GET":
                return ("notification_get", "workflow_read", (parts[1],))
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
        except LmsError as exc:
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
        if route == "search":
            self._send_json(200, store.search(self._param(parsed, "q"), user))
            return
        if route == "learner_list":
            self._send_json(200, {"learners": store.list_learners(user)})
            return
        if route == "learner_create":
            body = self._read_json_body()
            learner = store.create_learner(body.get("ref"), body.get("label"), user)
            self._send_json(201, learner)
            return
        if route == "learner_get":
            self._send_json(200, store.get_learner(ids[0], user))
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
        if route == "content_list":
            items = store.list_content_items(
                user, course_id=self._param(parsed, "course_id")
            )
            self._send_json(200, {"content_items": items})
            return
        if route == "content_create":
            body = self._read_json_body()
            item = store.create_content_item(
                body.get("title"), body.get("standard"), user,
                course_id=body.get("course_id"),
            )
            self._send_json(201, item)
            return
        if route == "content_get":
            self._send_json(200, store.get_content_item(ids[0], user))
            return
        if route == "lesson_plan_list":
            plans = store.list_lesson_plans(
                user, course_id=self._param(parsed, "course_id")
            )
            self._send_json(200, {"lesson_plans": plans})
            return
        if route == "lesson_plan_create":
            body = self._read_json_body()
            plan = store.create_lesson_plan(
                body.get("title"), body.get("course_id"), user,
                item_refs=body.get("item_refs"),
            )
            self._send_json(201, plan)
            return
        if route == "lesson_plan_get":
            self._send_json(200, store.get_lesson_plan(ids[0], user))
            return
        if route == "event_list":
            events = store.list_events(user, course_id=self._param(parsed, "course_id"))
            self._send_json(200, {"events": events})
            return
        if route == "event_create":
            body = self._read_json_body()
            event = store.create_event(
                body.get("title"), body.get("starts_at"), user,
                course_id=body.get("course_id"),
                ends_at=body.get("ends_at"),
                kind=body.get("kind") or "live",
                capacity=body.get("capacity"),
                location=body.get("location") or "",
            )
            self._send_json(201, event)
            return
        if route == "event_get":
            self._send_json(200, store.get_event(ids[0], user))
            return
        if route == "registration_list":
            registrations = store.list_registrations(
                user,
                event_id=self._param(parsed, "event_id"),
                learner_ref=self._param(parsed, "learner_ref"),
            )
            self._send_json(200, {"registrations": registrations})
            return
        if route == "registration_create":
            body = self._read_json_body()
            registration = store.register_learner(
                body.get("event_id"), body.get("learner_ref"), user
            )
            self._send_json(201, registration)
            return
        if route == "registration_get":
            self._send_json(200, store.get_registration(ids[0], user))
            return
        if route == "registration_state":
            body = self._read_json_body()
            self._send_json(200, store.set_registration_state(ids[0], body.get("state"), user))
            return
        if route == "authorization_list":
            records = store.list_authorizations(
                user, learner_ref=self._param(parsed, "learner_ref")
            )
            self._send_json(200, {"authorizations": records})
            return
        if route == "authorization_create":
            body = self._read_json_body()
            record = store.create_authorization(
                body.get("learner_ref"), body.get("subject"), user,
                course_id=body.get("course_id"),
                event_id=body.get("event_id"),
            )
            self._send_json(201, record)
            return
        if route == "authorization_get":
            self._send_json(200, store.get_authorization(ids[0], user))
            return
        if route == "authorization_decide":
            body = self._read_json_body()
            record = store.decide_authorization(
                ids[0], body.get("decision"), user, note=body.get("note") or ""
            )
            self._send_json(200, record)
            return
        if route == "plan_list":
            records = store.list_development_plans(
                user, learner_ref=self._param(parsed, "learner_ref")
            )
            self._send_json(200, {"development_plans": records})
            return
        if route == "plan_create":
            body = self._read_json_body()
            record = store.create_development_plan(
                body.get("learner_ref"), body.get("goal"), user,
                target_date=body.get("target_date"),
                activities=body.get("activities"),
            )
            self._send_json(201, record)
            return
        if route == "plan_get":
            self._send_json(200, store.get_development_plan(ids[0], user))
            return
        if route == "competency_list":
            self._send_json(200, {"competencies": store.list_competencies(user)})
            return
        if route == "competency_create":
            body = self._read_json_body()
            record = store.create_competency(
                body.get("name"), user, description=body.get("description") or ""
            )
            self._send_json(201, record)
            return
        if route == "competency_get":
            self._send_json(200, store.get_competency(ids[0], user))
            return
        if route == "learner_competency_list":
            records = store.list_learner_competencies(
                user,
                learner_ref=self._param(parsed, "learner_ref"),
                competency_id=self._param(parsed, "competency_id"),
            )
            self._send_json(200, {"learner_competencies": records})
            return
        if route == "learner_competency_create":
            body = self._read_json_body()
            record = store.record_learner_competency(
                body.get("learner_ref"), body.get("competency_id"),
                body.get("level"), user, note=body.get("note") or "",
            )
            self._send_json(201, record)
            return
        if route == "learner_competency_get":
            self._send_json(200, store.get_learner_competency(ids[0], user))
            return
        if route == "progress_list":
            records = store.list_progress(
                user,
                learner_ref=self._param(parsed, "learner_ref"),
                course_id=self._param(parsed, "course_id"),
            )
            self._send_json(200, {"progress": records})
            return
        if route == "progress_create":
            body = self._read_json_body()
            record = store.record_progress(
                body.get("learner_ref"), body.get("course_id"), body.get("status"), user,
                readiness=body.get("readiness"),
                percent_complete=body.get("percent_complete"),
                note=body.get("note") or "",
            )
            self._send_json(201, record)
            return
        if route == "progress_get":
            self._send_json(200, store.get_progress(ids[0], user))
            return
        if route == "statement_list":
            records = store.list_statements(
                user,
                learner_ref=self._param(parsed, "learner_ref"),
                object_ref=self._param(parsed, "object_ref"),
            )
            self._send_json(200, {"statements": records})
            return
        if route == "statement_create":
            body = self._read_json_body()
            record = store.record_statement(
                body.get("learner_ref"), body.get("verb"), body.get("object_ref"), user,
                context=body.get("context") or "",
                result_text=body.get("result_text"),
            )
            self._send_json(201, record)
            return
        if route == "statement_get":
            self._send_json(200, store.get_statement(ids[0], user))
            return
        if route == "compliance_list":
            records = store.list_compliance(
                user,
                as_of=self._param(parsed, "as_of"),
                learner_ref=self._param(parsed, "learner_ref"),
            )
            self._send_json(200, {"compliance": records})
            return
        if route == "compliance_create":
            body = self._read_json_body()
            record = store.create_compliance_assignment(
                body.get("learner_ref"), body.get("course_id"), body.get("due_date"), user
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
        if route == "workflow_list":
            self._send_json(200, {"workflows": store.list_workflows(user)})
            return
        if route == "workflow_create":
            body = self._read_json_body()
            record = store.create_workflow(
                body.get("name"), body.get("steps"), user,
                scope=body.get("scope") or "",
            )
            self._send_json(201, record)
            return
        if route == "workflow_get":
            self._send_json(200, store.get_workflow(ids[0], user))
            return
        if route == "notification_list":
            records = store.list_notifications(
                user, recipient_ref=self._param(parsed, "recipient_ref")
            )
            self._send_json(200, {"notifications": records})
            return
        if route == "notification_create":
            body = self._read_json_body()
            record = store.record_notification(
                body.get("recipient_ref"), body.get("subject"), user,
                body=body.get("body") or "",
                kind=body.get("kind") or "general",
            )
            self._send_json(201, record)
            return
        if route == "notification_get":
            self._send_json(200, store.get_notification(ids[0], user))
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
    """Create (but do not start) the lms HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "LmsHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
