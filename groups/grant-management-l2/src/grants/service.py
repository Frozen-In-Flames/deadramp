"""HTTP service exposing the grants functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
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
from .errors import GrantsError, NotFoundError, PermissionDenied, ValidationError


def _first_param(params, name):
    values = params.get(name)
    if not values:
        return None
    return values[0]


class _Handler(BaseHTTPRequestHandler):
    # Injected by make_server.
    store = None
    audit = None
    users = {}
    server_version = "Grants/0.1"
    protocol_version = "HTTP/1.1"

    # -- plumbing ---------------------------------------------------------

    def log_message(self, format, *args):  # noqa: A002 - stdlib name
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

    # -- audit / auth ---------------------------------------------------------

    def _audit(self, actor, action, target):
        if self.audit is not None:
            self.audit.record(actor, action, target)

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _authenticate(self, action, target):
        """Return the User, or send 401 (audited as denied) and return None."""
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        if not name or self.users.get(name) is None or self.users.get(name) != role:
            self._audit_denied(name or "anonymous", action, target)
            self._error(401, "unauthorized")
            return None
        return User(name, role)

    # -- dispatch ----------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.split("/") if p != ""]
        params = parse_qs(parsed.query)
        action, target = self._route_name(method, parts)
        try:
            if parts == ["health"] and method == "GET":
                self._send_json(200, {"status": "ok"})
                return
            user = self._authenticate(action, target)
            if user is None:
                return
            body = self._read_json_body() if method == "POST" else {}
            status, payload = self._route(method, parts, params, user, body)
            self._send_json(status, payload)
        except PermissionDenied as exc:
            self._audit_denied(self.headers.get("X-User") or "anonymous", action, target)
            self._error(403, exc)
        except NotFoundError as exc:
            self._error(404, exc)
        except ValidationError as exc:
            self._error(400, exc)
        except GrantsError as exc:
            self._error(400, exc)
        except Exception as exc:  # never leak a stack trace
            self._error(500, "internal error: %s" % (exc,))

    @staticmethod
    def _route_name(method, parts):
        label = "/".join(parts) if parts else "root"
        return "%s %s" % (method.lower(), label), label

    # -- routes -------------------------------------------------------------

    def _route(self, method, parts, params, user, body):
        store = self.store
        now = _first_param(params, "now")

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            self._audit(user.name, "audit_read", "audit")
            return 200, {"entries": self.audit.entries() if self.audit else []}

        if parts == ["search"] and method == "GET":
            return 200, store.search(user, _first_param(params, "q") or "")

        if parts == ["programs"] and method == "POST":
            program = store.create_program(
                user, body.get("name"), body.get("title"), body.get("sponsor_ref"),
                body.get("opens_at"), body.get("closes_at"), body.get("budget_cents"))
            return 201, program
        if parts == ["programs"] and method == "GET":
            return 200, {"programs": store.list_programs(user, now=now)}
        if len(parts) == 2 and parts[0] == "programs" and method == "GET":
            return 200, store.get_program(user, parts[1], now=now)
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "members" and method == "POST":
            return 200, store.add_member(user, parts[1], body.get("username"))
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "summary" and method == "GET":
            return 200, store.program_summary(user, parts[1], now=now)

        if parts == ["organizations"] and method == "POST":
            return 201, store.create_organization(user, body.get("ref"), body.get("label"))
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}
        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(user, parts[1])
        if len(parts) == 2 and parts[0] == "organizations" and method == "POST":
            return 200, store.update_organization(user, parts[1], body.get("label"))

        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "applications" and method == "POST":
            app = store.create_application(
                user, parts[1], body.get("org_id"), body.get("requested_cents"),
                body.get("summary"), form_id=body.get("form_id"),
                responses=body.get("responses"))
            return 201, app
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "applications" and method == "GET":
            return 200, {"applications": store.list_applications(
                user, parts[1], status=_first_param(params, "status"))}
        if len(parts) == 2 and parts[0] == "applications" and method == "GET":
            return 200, store.get_application(user, parts[1])
        if len(parts) == 3 and parts[0] == "applications" and method == "POST":
            app_id, verb = parts[1], parts[2]
            if verb == "submit":
                return 200, store.submit_application(user, app_id)
            if verb == "start-review":
                return 200, store.start_review(user, app_id)
            if verb == "withdraw":
                return 200, store.withdraw_application(user, app_id)
            if verb == "reviews":
                review = store.add_review(user, app_id, body.get("recommendation"),
                                          body.get("note"))
                return 201, review
            if verb == "decide":
                result = store.decide_application(
                    user, app_id, body.get("approve"),
                    amount_cents=body.get("amount_cents"),
                    note=body.get("note", ""))
                return 201, result
            if verb == "notes":
                note = store.create_note(user, app_id, body.get("body"))
                return 201, note
            if verb == "documents":
                doc = store.create_document(
                    user, "application", app_id, body.get("name"), body.get("kind"),
                    body.get("sha256"), body.get("size_bytes"))
                return 201, doc
        if len(parts) == 3 and parts[0] == "applications" and method == "GET":
            app_id, verb = parts[1], parts[2]
            if verb == "reviews":
                return 200, {"reviews": store.list_reviews(user, app_id)}
            if verb == "notes":
                return 200, {"notes": store.list_notes(user, app_id)}
            if verb == "documents":
                return 200, {"documents": store.list_documents(user, "application", app_id)}

        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "awards" and method == "GET":
            return 200, {"awards": store.list_awards(user, parts[1])}
        if len(parts) == 2 and parts[0] == "awards" and method == "GET":
            return 200, store.get_award(user, parts[1])
        if len(parts) == 3 and parts[0] == "awards" and method == "POST":
            award_id, verb = parts[1], parts[2]
            if verb == "reports":
                report = store.create_report(user, award_id, body.get("kind"),
                                             body.get("due_at"))
                return 201, report
            if verb == "documents":
                doc = store.create_document(
                    user, "award", award_id, body.get("name"), body.get("kind"),
                    body.get("sha256"), body.get("size_bytes"))
                return 201, doc
        if len(parts) == 3 and parts[0] == "awards" and method == "GET":
            award_id, verb = parts[1], parts[2]
            if verb == "reports":
                return 200, {"reports": store.list_reports(user, award_id, now=now)}
            if verb == "documents":
                return 200, {"documents": store.list_documents(user, "award", award_id)}
        if len(parts) == 2 and parts[0] == "reports" and method == "GET":
            return 200, store.get_report(user, parts[1], now=now)
        if len(parts) == 3 and parts[0] == "reports" and parts[2] == "submit" and method == "POST":
            return 200, store.submit_report(user, parts[1], body.get("summary"),
                                            submitted_at=body.get("submitted_at"))

        if len(parts) == 2 and parts[0] == "documents" and method == "GET":
            return 200, store.get_document(user, parts[1])
        if len(parts) == 3 and parts[0] == "documents" and parts[2] == "sign" and method == "POST":
            return 200, store.sign_document(user, parts[1])

        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "forms" and method == "POST":
            form = store.create_form(user, parts[1], body.get("name"), body.get("fields"))
            return 201, form
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "forms" and method == "GET":
            return 200, {"forms": store.list_forms(user, parts[1])}
        if len(parts) == 2 and parts[0] == "forms" and method == "GET":
            return 200, store.get_form(user, parts[1])
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "workflows" and method == "POST":
            workflow = store.create_workflow(user, parts[1], body.get("name"),
                                             body.get("steps"))
            return 201, workflow
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "workflows" and method == "GET":
            return 200, {"workflows": store.list_workflows(user, parts[1])}
        if len(parts) == 2 and parts[0] == "workflows" and method == "GET":
            return 200, store.get_workflow(user, parts[1])

        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "messages" and method == "POST":
            message = store.create_message(user, parts[1], body.get("org_id"),
                                           body.get("direction"), body.get("body"))
            return 201, message
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "messages" and method == "GET":
            return 200, {"messages": store.list_messages(
                user, parts[1], org_id=_first_param(params, "org_id"))}
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "notifications" and method == "POST":
            notification = store.create_notification(user, parts[1], body.get("org_id"),
                                                     body.get("text"))
            return 201, notification
        if len(parts) == 3 and parts[0] == "programs" and parts[2] == "notifications" and method == "GET":
            return 200, {"notifications": store.list_notifications(user, parts[1])}

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the grants HTTP server."""
    handler = type("GrantsHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
