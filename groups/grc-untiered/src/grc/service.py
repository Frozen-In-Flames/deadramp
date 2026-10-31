"""HTTP service exposing the GRC records substrate over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider (IA-2).

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
from .errors import GrcError, NotFoundError, PermissionDenied, ValidationError


class _Handler(BaseHTTPRequestHandler):
    # Injected by make_server.
    store = None
    audit = None
    users = {}
    server_version = "Grc/0.1"
    protocol_version = "HTTP/1.1"

    # -- plumbing -----------------------------------------------------

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

    # -- audit helpers --------------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            try:
                self.audit.record(actor, action, target, details=details)
            except Exception:
                pass  # Auditing must never break the request path.

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    # -- auth -------------------------------------------------------------

    def _authenticate(self, action, target):
        """Return the User, or send 401 (audited as denied) and return None."""
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        actor = name if name else "anonymous"
        if not name or not role or name not in self.users or self.users[name] != role:
            self._audit_denied(actor, action, target)
            self._error(401, "unauthorized")
            return None
        return User(name=name, role=role)

    def _authorize(self, user, action, target):
        """Return True, or send 403 (audited as denied) and return False."""
        try:
            require(user, action)
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
            return False
        return True

    # -- routing ------------------------------------------------------------

    def _route(self, method, parts):
        """Return (route, permission_action, ids) for a known route,
        or (None, None, ()) for unknown routes."""
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["posture"]:
            return ("posture", "read", ())
        if parts and parts[0] == "frameworks":
            if len(parts) == 1:
                if method == "GET":
                    return ("framework_list", "read", ())
                if method == "POST":
                    return ("framework_create", "manage_frameworks", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("framework_get", "read", (parts[1],))
            elif len(parts) == 3 and parts[2] == "controls":
                if method == "GET":
                    return ("control_list", "read", (parts[1],))
                if method == "POST":
                    return ("control_create", "manage_frameworks", (parts[1],))
            elif len(parts) == 4 and parts[2] == "controls":
                if method == "GET":
                    return ("control_get", "read", (parts[1], parts[3]))
            return (None, None, ())
        if parts and parts[0] == "controls":
            if len(parts) == 1 and method == "GET":
                return ("control_list_all", "read", ())
            return (None, None, ())
        if parts and parts[0] == "systems":
            if len(parts) == 1:
                if method == "GET":
                    return ("system_list", "read", ())
                if method == "POST":
                    return ("system_create", "manage_systems", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("system_get", "read", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "indicators":
            if len(parts) == 1:
                if method == "GET":
                    return ("indicator_list", "read", ())
                if method == "POST":
                    return ("indicator_create", "manage_indicators", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("indicator_get", "read", (parts[1],))
            elif len(parts) == 3 and parts[2] == "results":
                if method == "GET":
                    return ("result_list", "read", (parts[1],))
                if method == "POST":
                    return ("result_record", "record_results", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "results":
            if len(parts) == 1 and method == "GET":
                return ("result_list_all", "read", ())
            return (None, None, ())
        if parts and parts[0] == "evidence":
            if len(parts) == 1:
                if method == "GET":
                    return ("evidence_list", "read", ())
                if method == "POST":
                    return ("evidence_create", "manage_evidence", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("evidence_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "verify":
                    return ("evidence_verify", "read", (parts[1],))
                if method == "POST" and parts[2] == "review":
                    return ("evidence_review", "review_evidence", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "findings":
            if len(parts) == 1:
                if method == "GET":
                    return ("finding_list", "read", ())
                if method == "POST":
                    return ("finding_create", "manage_findings", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("finding_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "transition":
                    return ("finding_transition", "manage_findings", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "assessments":
            if len(parts) == 1:
                if method == "GET":
                    return ("assessment_list", "read", ())
                if method == "POST":
                    return ("assessment_create", "manage_assessments", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("assessment_get", "read", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "authorizations":
            if len(parts) == 1:
                if method == "GET":
                    return ("authorization_list", "read", ())
                if method == "POST":
                    return ("authorization_create", "manage_authorizations", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("authorization_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "transition":
                    return (
                        "authorization_transition",
                        "manage_authorizations",
                        (parts[1],),
                    )
            return (None, None, ())
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
            # A store-raised denial: audit it here (the store audits
            # successes only, so this is recorded exactly once).
            actor = self.headers.get("X-User") or "anonymous"
            if action:
                self._audit_denied(actor, action, target)
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except GrcError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    # -- endpoint handlers ---------------------------------------------------

    def _execute(self, route, user, ids, parsed):
        store = self.store
        params = parse_qs(parsed.query)

        def param(name):
            values = params.get(name)
            return values[0] if values else None

        if route == "audit_read":
            entries = self.audit.entries() if self.audit is not None else []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "posture":
            self._send_json(200, store.posture_summary(user, as_of=param("as_of")))
            return
        if route == "framework_list":
            self._send_json(200, {"frameworks": store.list_frameworks(user)})
            return
        if route == "framework_create":
            body = self._read_json_body()
            framework = store.create_framework(
                body.get("id"),
                body.get("name"),
                body.get("version"),
                user,
                description=body.get("description", ""),
            )
            self._send_json(201, framework)
            return
        if route == "framework_get":
            self._send_json(200, store.get_framework(ids[0], user))
            return
        if route == "control_list":
            controls = store.list_controls(user, framework_id=ids[0])
            self._send_json(200, {"controls": controls})
            return
        if route == "control_list_all":
            self._send_json(200, {"controls": store.list_controls(user)})
            return
        if route == "control_create":
            body = self._read_json_body()
            control = store.create_control(
                ids[0],
                body.get("id"),
                body.get("title"),
                user,
                family=body.get("family"),
            )
            self._send_json(201, control)
            return
        if route == "control_get":
            self._send_json(200, store.get_control(ids[0], ids[1], user))
            return
        if route == "system_list":
            self._send_json(200, {"systems": store.list_systems(user)})
            return
        if route == "system_create":
            body = self._read_json_body()
            system = store.create_system(
                body.get("ref"),
                body.get("name"),
                user,
                description=body.get("description", ""),
            )
            self._send_json(201, system)
            return
        if route == "system_get":
            self._send_json(200, store.get_system(ids[0], user))
            return
        if route == "indicator_list":
            self._send_json(200, {"indicators": store.list_indicators(user)})
            return
        if route == "indicator_create":
            body = self._read_json_body()
            indicator = store.create_indicator(
                body.get("id"),
                body.get("name"),
                body.get("control_ids"),
                user,
                description=body.get("description", ""),
            )
            self._send_json(201, indicator)
            return
        if route == "indicator_get":
            self._send_json(200, store.get_indicator(ids[0], user))
            return
        if route == "result_list":
            results = store.list_indicator_results(user, indicator_id=ids[0])
            self._send_json(200, {"results": results})
            return
        if route == "result_list_all":
            results = store.list_indicator_results(
                user, system_ref=param("system")
            )
            self._send_json(200, {"results": results})
            return
        if route == "result_record":
            body = self._read_json_body()
            result = store.record_indicator_result(
                ids[0],
                body.get("system_ref"),
                body.get("status"),
                user,
                timestamp=body.get("timestamp"),
                note=body.get("note", ""),
            )
            self._send_json(201, result)
            return
        if route == "evidence_list":
            evidence = store.list_evidence(
                user, system_ref=param("system"), control_id=param("control")
            )
            self._send_json(200, {"evidence": evidence})
            return
        if route == "evidence_create":
            body = self._read_json_body()
            evidence = store.create_evidence(
                body.get("name"),
                body.get("content"),
                body.get("control_ids"),
                body.get("system_refs"),
                user,
                description=body.get("description", ""),
            )
            self._send_json(201, evidence)
            return
        if route == "evidence_get":
            self._send_json(200, store.get_evidence(ids[0], user))
            return
        if route == "evidence_verify":
            body = self._read_json_body()
            verified = store.verify_evidence(ids[0], body.get("content"), user)
            self._send_json(200, {"verified": verified})
            return
        if route == "evidence_review":
            body = self._read_json_body()
            evidence = store.review_evidence(
                ids[0],
                body.get("validation_status"),
                user,
                note=body.get("note", ""),
            )
            self._send_json(200, evidence)
            return
        if route == "finding_list":
            findings = store.list_findings(
                user,
                system_ref=param("system"),
                status=param("status"),
                as_of=param("as_of"),
            )
            self._send_json(200, {"findings": findings})
            return
        if route == "finding_create":
            body = self._read_json_body()
            finding = store.create_finding(
                body.get("title"),
                body.get("system_ref"),
                body.get("severity"),
                body.get("source"),
                body.get("due_date"),
                user,
                description=body.get("description", ""),
                control_ids=body.get("control_ids"),
            )
            self._send_json(201, finding)
            return
        if route == "finding_get":
            finding = store.get_finding(ids[0], user, as_of=param("as_of"))
            self._send_json(200, finding)
            return
        if route == "finding_transition":
            body = self._read_json_body()
            finding = store.transition_finding(
                ids[0], body.get("status"), user, rationale=body.get("rationale")
            )
            self._send_json(200, finding)
            return
        if route == "assessment_list":
            assessments = store.list_assessments(
                user, system_ref=param("system"), framework_id=param("framework")
            )
            self._send_json(200, {"assessments": assessments})
            return
        if route == "assessment_create":
            body = self._read_json_body()
            assessment = store.create_assessment(
                body.get("system_ref"),
                body.get("framework_id"),
                body.get("scope"),
                body.get("assessor"),
                body.get("date"),
                body.get("result"),
                user,
                notes=body.get("notes", ""),
            )
            self._send_json(201, assessment)
            return
        if route == "assessment_get":
            self._send_json(200, store.get_assessment(ids[0], user))
            return
        if route == "authorization_list":
            records = store.list_authorizations(
                user, system_ref=param("system"), status=param("status")
            )
            self._send_json(200, {"authorizations": records})
            return
        if route == "authorization_create":
            body = self._read_json_body()
            status = body.get("status")
            record = store.create_authorization(
                body.get("system_ref"),
                body.get("framework_id"),
                user,
                status=status if status is not None else "not_started",
                note=body.get("note", ""),
            )
            self._send_json(201, record)
            return
        if route == "authorization_get":
            self._send_json(200, store.get_authorization(ids[0], user))
            return
        if route == "authorization_transition":
            body = self._read_json_body()
            record = store.transition_authorization(
                ids[0], body.get("status"), user, note=body.get("note")
            )
            self._send_json(200, record)
            return
        self._error(404, "not found")

    # -- verbs -----------------------------------------------------------------

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
    """Create (but do not start) the grc HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "GrcHandler",
        (_Handler,),
        {
            "store": store,
            "audit": audit,
            "users": dict(users or {}),
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
