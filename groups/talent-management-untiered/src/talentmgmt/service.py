"""HTTP service exposing the Talent Management functions over a
JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
provider.

The store records every successful mutation. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and
``audit_read``. Errors are JSON ``{error: msg}`` with 400
(validation), 401 (auth), 403 (permission) or 404 (not found);
handlers never leak a stack trace to the client.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .errors import (
    NotFoundError,
    PermissionDenied,
    TalentMgmtError,
    ValidationError,
)

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
}
DEMO_USERS = USERS


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
    server_version = "TalentMgmt/0.1"
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
        except TalentMgmtError as exc:
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

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            self._audit(user.name, "audit_read", "audit")
            return 200, {"entries": self.audit.entries() if self.audit else []}

        if parts == ["search"] and method == "GET":
            return 200, store.search_registry(user, _first_param(params, "q") or "")

        if parts == ["organizations"] and method == "POST":
            return 201, store.create_organization(
                body.get("org_ref"), body.get("label"), user)
        if parts == ["organizations"] and method == "GET":
            return 200, {"organizations": store.list_organizations(user)}
        if len(parts) == 2 and parts[0] == "organizations" and method == "GET":
            return 200, store.get_organization(parts[1], user)
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "members" and method == "POST":
            return 200, store.add_member(parts[1], body.get("username"), user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "candidates" and method == "GET":
            return 200, {"candidates": store.list_candidates(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "candidates" and method == "POST":
            candidate = store.register_candidate(
                parts[1], body.get("candidate_ref"), body.get("label"), user)
            return 201, candidate

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "requisitions" and method == "GET":
            return 200, {"requisitions": store.list_requisitions(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "requisitions" and method == "POST":
            requisition = store.create_requisition(
                parts[1], body.get("requisition_ref"), body.get("title"), user,
                opens_at=body.get("opens_at"), closes_at=body.get("closes_at"))
            return 201, requisition
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "requisitions" and parts[4] == "close" \
                and method == "POST":
            return 200, store.close_requisition(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "pipelines" and method == "GET":
            return 200, {"pipelines": store.list_pipelines(
                parts[1], user,
                requisition_id=_first_param(params, "requisition_id"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "pipelines" and method == "POST":
            pipeline = store.create_pipeline(
                parts[1], body.get("pipeline_ref"), body.get("requisition_id"),
                body.get("stages"), user, label=body.get("label"))
            return 201, pipeline
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "pipelines" and parts[4] == "placements" \
                and method == "POST":
            placement = store.place_candidate(
                parts[1], parts[3], body.get("placement_ref"),
                body.get("candidate_ref"), user)
            return 201, placement

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "placements" and method == "GET":
            return 200, {"placements": store.list_placements(
                parts[1], user,
                pipeline_id=_first_param(params, "pipeline_id"))}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "placements" and parts[4] == "movements" \
                and method == "GET":
            return 200, {"movements": store.list_movements(
                parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "placements" and parts[4] == "movements" \
                and method == "POST":
            movement = store.record_movement(
                parts[1], parts[3], body.get("movement_ref"),
                body.get("stage_index"), user, label=body.get("label"))
            return 201, movement
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "placements" and parts[4] == "withdraw" \
                and method == "POST":
            return 200, store.withdraw_placement(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "events" and method == "GET":
            return 200, {"events": store.list_events(
                parts[1], user, kind=_first_param(params, "kind"),
                requisition_id=_first_param(params, "requisition_id"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "events" and method == "POST":
            event = store.create_event(
                parts[1], body.get("event_ref"), body.get("title"),
                body.get("kind"), body.get("starts_at"), user,
                requisition_id=body.get("requisition_id"),
                label=body.get("label"))
            return 201, event
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "events" and parts[4] == "complete" \
                and method == "POST":
            return 200, store.complete_event(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "events" and parts[4] == "cancel" \
                and method == "POST":
            return 200, store.cancel_event(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "events" and parts[4] == "registrations" \
                and method == "GET":
            return 200, {"registrations": store.list_registrations(
                parts[1], parts[3], user)}
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "events" and parts[4] == "registrations" \
                and method == "POST":
            registration = store.register_for_event(
                parts[1], parts[3], body.get("registration_ref"),
                body.get("candidate_ref"), user)
            return 201, registration
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "registrations" and parts[4] == "check-in" \
                and method == "POST":
            return 200, store.check_in_registration(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "assessments" and method == "GET":
            return 200, {"assessments": store.list_assessments(
                parts[1], user,
                candidate_ref=_first_param(params, "candidate_ref"),
                status=_first_param(params, "status"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "assessments" and method == "POST":
            assessment = store.record_assessment(
                parts[1], body.get("assessment_ref"),
                body.get("candidate_ref"), body.get("instrument_label"),
                user, requisition_id=body.get("requisition_id"))
            return 201, assessment
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "assessments" and parts[4] == "complete" \
                and method == "POST":
            return 200, store.complete_assessment(
                parts[1], parts[3], body.get("outcome_label"), user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "interviews" and method == "GET":
            return 200, {"interviews": store.list_interviews(
                parts[1], user,
                candidate_ref=_first_param(params, "candidate_ref"),
                kind=_first_param(params, "kind"))}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "interviews" and method == "POST":
            interview = store.schedule_interview(
                parts[1], body.get("interview_ref"),
                body.get("candidate_ref"), body.get("kind"), user,
                requisition_id=body.get("requisition_id"),
                scheduled_at=body.get("scheduled_at"))
            return 201, interview
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "interviews" and parts[4] == "complete" \
                and method == "POST":
            return 200, store.complete_interview(parts[1], parts[3], user)
        if len(parts) == 5 and parts[0] == "organizations" \
                and parts[2] == "interviews" and parts[4] == "cancel" \
                and method == "POST":
            return 200, store.cancel_interview(parts[1], parts[3], user)

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "workflows" and method == "GET":
            return 200, {"workflows": store.list_workflows(parts[1], user)}
        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "workflows" and method == "POST":
            workflow = store.register_workflow(
                parts[1], body.get("workflow_ref"), body.get("label"), user)
            return 201, workflow

        if len(parts) == 3 and parts[0] == "organizations" \
                and parts[2] == "report" and method == "GET":
            return 200, store.org_report(parts[1], user)

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users):
    """Build (but do not start) the talentmgmt HTTP server."""
    handler = type("TalentMgmtHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    return ThreadingHTTPServer((host, port), handler)
