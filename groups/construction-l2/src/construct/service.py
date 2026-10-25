"""HTTP service exposing the construction functions over a JSON REST API.

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

List/get contract, submittal, RFI, milestone, punch-item, alerts and
report endpoints accept a ``?now=`` ISO-8601 query parameter so
derived expiry/overdue/due-state values are deterministic for
callers and tests.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import ConstructError, NotFoundError, PermissionDenied, ValidationError

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
    server_version = "Construct/0.1"
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
        if method == "GET" and parts == ["alerts"]:
            return ("alerts_list", "report_read", ())
        if parts and parts[0] == "orgs":
            if len(parts) == 1:
                if method == "GET":
                    return ("org_list", "org_read", ())
                if method == "POST":
                    return ("org_create", "org_write", ())
            if len(parts) == 2 and method == "GET":
                return ("org_get", "org_read", (parts[1],))
        if parts and parts[0] == "projects":
            if len(parts) == 1:
                if method == "GET":
                    return ("project_list", "project_read", ())
                if method == "POST":
                    return ("project_create", "project_write", ())
            if len(parts) == 2 and method == "GET":
                return ("project_get", "project_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("project_transition", "project_write", (parts[1],))
            if len(parts) == 3 and parts[2] == "participants":
                if method == "GET":
                    return ("participant_list", "project_read", (parts[1],))
                if method == "POST":
                    return ("participant_add", "project_write", (parts[1],))
            if len(parts) == 3 and method == "GET" and parts[2] == "compliance":
                return ("compliance", "workforce_read", (parts[1],))
            if len(parts) == 3 and method == "GET" and parts[2] == "cost-summary":
                return ("cost_summary", "cost_read", (parts[1],))
        if parts and parts[0] == "documents":
            if len(parts) == 1:
                if method == "GET":
                    return ("document_list", "document_read", ())
                if method == "POST":
                    return ("document_create", "document_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("document_get", "document_read", (parts[1],))
                if method == "PATCH":
                    return ("document_update", "document_write", (parts[1],))
        if parts and parts[0] == "contracts":
            if len(parts) == 1:
                if method == "GET":
                    return ("contract_list", "contract_read", ())
                if method == "POST":
                    return ("contract_create", "contract_write", ())
            if len(parts) == 2 and method == "GET":
                return ("contract_get", "contract_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("contract_transition", "contract_write", (parts[1],))
        if parts and parts[0] == "submittals":
            if len(parts) == 1:
                if method == "GET":
                    return ("submittal_list", "record_read", ())
                if method == "POST":
                    return ("submittal_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("submittal_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("submittal_transition", "record_write", (parts[1],))
        if parts and parts[0] == "rfis":
            if len(parts) == 1:
                if method == "GET":
                    return ("rfi_list", "record_read", ())
                if method == "POST":
                    return ("rfi_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("rfi_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("rfi_transition", "record_write", (parts[1],))
        if parts and parts[0] == "milestones":
            if len(parts) == 1:
                if method == "GET":
                    return ("milestone_list", "record_read", ())
                if method == "POST":
                    return ("milestone_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("milestone_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "complete":
                return ("milestone_complete", "record_write", (parts[1],))
        if parts and parts[0] == "dispatches":
            if len(parts) == 1:
                if method == "GET":
                    return ("dispatch_list", "record_read", ())
                if method == "POST":
                    return ("dispatch_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("dispatch_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("dispatch_transition", "record_write", (parts[1],))
        if parts and parts[0] == "inspections":
            if len(parts) == 1:
                if method == "GET":
                    return ("inspection_list", "record_read", ())
                if method == "POST":
                    return ("inspection_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("inspection_get", "record_read", (parts[1],))
        if parts and parts[0] == "punch-items":
            if len(parts) == 1:
                if method == "GET":
                    return ("punch_list", "record_read", ())
                if method == "POST":
                    return ("punch_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("punch_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("punch_transition", "record_write", (parts[1],))
        if parts and parts[0] == "incidents":
            if len(parts) == 1:
                if method == "GET":
                    return ("incident_list", "record_read", ())
                if method == "POST":
                    return ("incident_create", "record_write", ())
            if len(parts) == 2 and method == "GET":
                return ("incident_get", "record_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("incident_transition", "record_write", (parts[1],))
        if parts and parts[0] == "workers":
            if len(parts) == 1:
                if method == "GET":
                    return ("worker_list", "workforce_read", ())
                if method == "POST":
                    return ("worker_create", "workforce_write", ())
            if len(parts) == 2 and method == "GET":
                return ("worker_get", "workforce_read", (parts[1],))
        if parts and parts[0] == "time-entries":
            if len(parts) == 1:
                if method == "GET":
                    return ("time_list", "workforce_read", ())
                if method == "POST":
                    return ("time_create", "workforce_write", ())
            if len(parts) == 2 and method == "GET":
                return ("time_get", "workforce_read", (parts[1],))
        if parts and parts[0] == "payrolls":
            if len(parts) == 1:
                if method == "GET":
                    return ("payroll_list", "workforce_read", ())
                if method == "POST":
                    return ("payroll_create", "workforce_write", ())
            if len(parts) == 2 and method == "GET":
                return ("payroll_get", "workforce_read", (parts[1],))
        if parts and parts[0] == "violations":
            if len(parts) == 1:
                if method == "GET":
                    return ("violation_list", "workforce_read", ())
                if method == "POST":
                    return ("violation_create", "violation_write", ())
            if len(parts) == 2 and method == "GET":
                return ("violation_get", "workforce_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "resolve":
                return ("violation_resolve", "violation_write", (parts[1],))
        if parts and parts[0] == "costs":
            if len(parts) == 1:
                if method == "GET":
                    return ("cost_list", "cost_read", ())
                if method == "POST":
                    return ("cost_create", "cost_write", ())
            if len(parts) == 2 and method == "GET":
                return ("cost_get", "cost_read", (parts[1],))
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
        except ConstructError as exc:
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
            params = parse_qs(parsed.query)
            query_text = (params.get("q") or [""])[0]
            self._send_json(200, store.search(query_text, user))
            return
        if route == "report":
            self._send_json(200, store.report(user, now=self._now_param(parsed)))
            return
        if route == "alerts_list":
            self._send_json(200, {"alerts": store.list_alerts(user, now=self._now_param(parsed))})
            return
        if route == "org_list":
            self._send_json(200, {"orgs": store.list_orgs(user)})
            return
        if route == "org_create":
            body = self._read_json_body()
            self._send_json(201, store.create_org(
                body.get("name"), user,
                reference=body.get("reference"), attributes=body.get("attributes")))
            return
        if route == "org_get":
            self._send_json(200, store.get_org(ids[0], user))
            return
        if route == "project_list":
            self._send_json(200, {"projects": store.list_projects(
                user, status=self._param(parsed, "status"))})
            return
        if route == "project_create":
            body = self._read_json_body()
            self._send_json(201, store.create_project(
                body.get("name"), user,
                agency_ref=body.get("agency_ref"), location=body.get("location"),
                start_at=body.get("start_at"), end_at=body.get("end_at")))
            return
        if route == "project_get":
            self._send_json(200, store.get_project(ids[0], user))
            return
        if route == "project_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_project(ids[0], user, to_status))
            return
        if route == "participant_list":
            self._send_json(200, {"participants": store.list_participants(ids[0], user)})
            return
        if route == "participant_add":
            body = self._read_json_body()
            self._send_json(201, store.add_participant(
                ids[0], body.get("org_id"), user,
                tier=body.get("tier"), role=body.get("role")))
            return
        if route == "compliance":
            org_id = self._param(parsed, "org_id")
            if not org_id:
                raise ValidationError("org_id query parameter is required")
            self._send_json(200, store.contractor_compliance(ids[0], org_id, user))
            return
        if route == "cost_summary":
            self._send_json(200, store.project_cost_summary(ids[0], user))
            return
        if route == "document_list":
            self._send_json(200, {"documents": store.list_documents(
                user, project_id=self._param(parsed, "project_id"))})
            return
        if route == "document_create":
            body = self._read_json_body()
            self._send_json(201, store.create_document(
                user, body.get("title"),
                project_id=body.get("project_id"),
                doc_type=body.get("doc_type", "other") or "other",
                checksum=body.get("checksum"), note=body.get("note")))
            return
        if route == "document_get":
            self._send_json(200, store.get_document(ids[0], user))
            return
        if route == "document_update":
            body = self._read_json_body()
            self._send_json(200, store.update_document(
                ids[0], user, checksum=body.get("checksum"), note=body.get("note")))
            return
        if route == "contract_list":
            self._send_json(200, {"contracts": store.list_contracts(
                user, now=self._now_param(parsed),
                project_id=self._param(parsed, "project_id"),
                status=self._param(parsed, "status"))})
            return
        if route == "contract_create":
            body = self._read_json_body()
            self._send_json(201, store.create_contract(
                user, body.get("title"), body.get("project_id"),
                org_id=body.get("org_id"), value_cents=body.get("value_cents"),
                start_at=body.get("start_at"), end_at=body.get("end_at"),
                key_dates=body.get("key_dates")))
            return
        if route == "contract_get":
            self._send_json(200, store.get_contract(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "contract_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_contract(ids[0], user, to_status))
            return
        if route == "submittal_list":
            self._send_json(200, {"submittals": store.list_submittals(
                user, now=self._now_param(parsed),
                project_id=self._param(parsed, "project_id"),
                status=self._param(parsed, "status"))})
            return
        if route == "submittal_create":
            body = self._read_json_body()
            self._send_json(201, store.create_submittal(
                user, body.get("project_id"), body.get("title"),
                org_id=body.get("org_id"), due_at=body.get("due_at")))
            return
        if route == "submittal_get":
            self._send_json(200, store.get_submittal(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "submittal_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_submittal(ids[0], user, to_status))
            return
        if route == "rfi_list":
            self._send_json(200, {"rfis": store.list_rfis(
                user, now=self._now_param(parsed),
                project_id=self._param(parsed, "project_id"),
                status=self._param(parsed, "status"))})
            return
        if route == "rfi_create":
            body = self._read_json_body()
            self._send_json(201, store.create_rfi(
                user, body.get("project_id"), body.get("question"),
                org_id=body.get("org_id"), due_at=body.get("due_at")))
            return
        if route == "rfi_get":
            self._send_json(200, store.get_rfi(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "rfi_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_rfi(ids[0], user, to_status))
            return
        if route == "milestone_list":
            self._send_json(200, {"milestones": store.list_milestones(
                user, now=self._now_param(parsed),
                project_id=self._param(parsed, "project_id"))})
            return
        if route == "milestone_create":
            body = self._read_json_body()
            self._send_json(201, store.create_milestone(
                user, body.get("project_id"), body.get("name"), body.get("due_at")))
            return
        if route == "milestone_get":
            self._send_json(200, store.get_milestone(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "milestone_complete":
            body = self._read_json_body() if self.headers.get("Content-Length") else {}
            self._send_json(200, store.complete_milestone(
                ids[0], user, completed_at=body.get("completed_at")))
            return
        if route == "dispatch_list":
            self._send_json(200, {"dispatches": store.list_dispatches(
                user, project_id=self._param(parsed, "project_id"))})
            return
        if route == "dispatch_create":
            body = self._read_json_body()
            self._send_json(201, store.create_dispatch(
                user, body.get("project_id"), body.get("task"),
                org_id=body.get("org_id"), worker_ref=body.get("worker_ref"),
                scheduled_for=body.get("scheduled_for")))
            return
        if route == "dispatch_get":
            self._send_json(200, store.get_dispatch(ids[0], user))
            return
        if route == "dispatch_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_dispatch(ids[0], user, to_status))
            return
        if route == "inspection_list":
            self._send_json(200, {"inspections": store.list_inspections(
                user, project_id=self._param(parsed, "project_id"))})
            return
        if route == "inspection_create":
            body = self._read_json_body()
            self._send_json(201, store.create_inspection(
                user, body.get("project_id"), body.get("inspection_type"),
                inspector_ref=body.get("inspector_ref"),
                occurred_at=body.get("occurred_at"), result=body.get("result")))
            return
        if route == "inspection_get":
            self._send_json(200, store.get_inspection(ids[0], user))
            return
        if route == "punch_list":
            self._send_json(200, {"punch_items": store.list_punch_items(
                user, now=self._now_param(parsed),
                project_id=self._param(parsed, "project_id"))})
            return
        if route == "punch_create":
            body = self._read_json_body()
            self._send_json(201, store.create_punch_item(
                user, body.get("project_id"), body.get("description"),
                inspection_id=body.get("inspection_id"), org_id=body.get("org_id"),
                due_at=body.get("due_at")))
            return
        if route == "punch_get":
            self._send_json(200, store.get_punch_item(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "punch_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_punch_item(ids[0], user, to_status))
            return
        if route == "incident_list":
            self._send_json(200, {"incidents": store.list_incidents(
                user, project_id=self._param(parsed, "project_id"),
                status=self._param(parsed, "status"))})
            return
        if route == "incident_create":
            body = self._read_json_body()
            self._send_json(201, store.create_incident(
                user, body.get("project_id"), body.get("category"), body.get("description"),
                severity=body.get("severity", "info") or "info",
                occurred_at=body.get("occurred_at")))
            return
        if route == "incident_get":
            self._send_json(200, store.get_incident(ids[0], user))
            return
        if route == "incident_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_incident(ids[0], user, to_status))
            return
        if route == "worker_list":
            self._send_json(200, {"workers": store.list_workers(
                user, project_id=self._param(parsed, "project_id"),
                org_id=self._param(parsed, "org_id"))})
            return
        if route == "worker_create":
            body = self._read_json_body()
            self._send_json(201, store.create_worker(
                user, body.get("project_id"), body.get("org_id"), body.get("reference"),
                trade=body.get("trade"), attributes=body.get("attributes")))
            return
        if route == "worker_get":
            self._send_json(200, store.get_worker(ids[0], user))
            return
        if route == "time_list":
            self._send_json(200, {"time_entries": store.list_time_entries(
                user, worker_id=self._param(parsed, "worker_id"),
                project_id=self._param(parsed, "project_id"))})
            return
        if route == "time_create":
            body = self._read_json_body()
            self._send_json(201, store.create_time_entry(
                user, body.get("worker_id"), body.get("minutes"),
                occurred_on=body.get("occurred_on"), note=body.get("note")))
            return
        if route == "time_get":
            self._send_json(200, store.get_time_entry(ids[0], user))
            return
        if route == "payroll_list":
            self._send_json(200, {"payrolls": store.list_payrolls(
                user, project_id=self._param(parsed, "project_id"),
                org_id=self._param(parsed, "org_id"))})
            return
        if route == "payroll_create":
            body = self._read_json_body()
            certified = body.get("certified", False)
            self._send_json(201, store.create_payroll(
                user, body.get("project_id"), body.get("org_id"),
                body.get("period_start"), body.get("period_end"),
                certified=certified, worker_count=body.get("worker_count"),
                total_wages_cents=body.get("total_wages_cents")))
            return
        if route == "payroll_get":
            self._send_json(200, store.get_payroll(ids[0], user))
            return
        if route == "violation_list":
            self._send_json(200, {"violations": store.list_violations(
                user, project_id=self._param(parsed, "project_id"),
                org_id=self._param(parsed, "org_id"),
                status=self._param(parsed, "status"))})
            return
        if route == "violation_create":
            body = self._read_json_body()
            self._send_json(201, store.create_violation(
                user, body.get("project_id"), body.get("org_id"),
                body.get("kind"), body.get("description")))
            return
        if route == "violation_get":
            self._send_json(200, store.get_violation(ids[0], user))
            return
        if route == "violation_resolve":
            body = self._read_json_body() if self.headers.get("Content-Length") else {}
            self._send_json(200, store.resolve_violation(
                ids[0], user, resolution=body.get("resolution")))
            return
        if route == "cost_list":
            self._send_json(200, {"costs": store.list_cost_entries(
                user, project_id=self._param(parsed, "project_id"),
                kind=self._param(parsed, "kind"))})
            return
        if route == "cost_create":
            body = self._read_json_body()
            self._send_json(201, store.create_cost_entry(
                user, body.get("project_id"), body.get("category"), body.get("description"),
                kind=body.get("kind", "actual") or "actual",
                budgeted_cents=body.get("budgeted_cents"),
                actual_cents=body.get("actual_cents")))
            return
        if route == "cost_get":
            self._send_json(200, store.get_cost_entry(ids[0], user))
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
    """Create (but do not start) the construct HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "ConstructHandler",
        (_Handler,),
        {"store": store, "audit": audit, "users": dict(users or {})},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
