"""HTTP service exposing the finance functions over a JSON REST API.

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
from .errors import FinanceError, NotFoundError, PermissionDenied, ValidationError


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
    server_version = "Finance/0.1"
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

    def _read_optional_body(self):
        """Read a POST action body that may be empty; its content is ignored."""
        return self._read_json_body()

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
        """Return (route, permission_action, ids) for a known route.

        ``permission_action`` is None only for ``POST /programs/{id}/members``:
        any authenticated user may call it and the store enforces
        owner-or-admin. Returns (None, None, ()) for unknown routes.
        """
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if parts and parts[0] == "programs":
            if len(parts) == 1:
                if method == "GET":
                    return ("program_list", "read", ())
                if method == "POST":
                    return ("program_create", "create_program", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("program_get", "read", (parts[1],))
            elif len(parts) == 3:
                program_id, sub = parts[1], parts[2]
                if method == "POST" and sub == "members":
                    return ("member_add", None, (program_id,))
                if method == "GET" and sub == "participants":
                    return ("participant_list", "read", (program_id,))
                if method == "POST" and sub == "participants":
                    return ("participant_create", "enter", (program_id,))
                if method == "GET" and sub == "accruals":
                    return ("accrual_list", "read", (program_id,))
                if method == "POST" and sub == "accruals":
                    return ("accrual_create", "enter", (program_id,))
                if method == "GET" and sub == "access-requests":
                    return ("access_list", "read", (program_id,))
                if method == "POST" and sub == "access-requests":
                    return ("access_create", "enter", (program_id,))
                if method == "GET" and sub == "disbursements":
                    return ("disbursement_list", "read", (program_id,))
                if method == "GET" and sub == "bookings":
                    return ("booking_list", "read", (program_id,))
                if method == "POST" and sub == "bookings":
                    return ("booking_create", "enter", (program_id,))
                if method == "GET" and sub == "wellness-offerings":
                    return ("wellness_list", "read", (program_id,))
                if method == "POST" and sub == "wellness-offerings":
                    return ("wellness_create", "enter", (program_id,))
                if method == "GET" and sub == "wellness-enrollments":
                    return ("enrollment_list", "read", (program_id,))
            elif len(parts) == 4:
                program_id, sub, item_id = parts[1], parts[2], parts[3]
                if method == "GET" and sub == "participants":
                    return ("participant_get", "read", (program_id, item_id))
                if method == "GET" and sub == "accruals":
                    return ("accrual_get", "read", (program_id, item_id))
                if method == "GET" and sub == "access-requests":
                    return ("access_get", "read", (program_id, item_id))
                if method == "GET" and sub == "bookings":
                    return ("booking_get", "read", (program_id, item_id))
                if sub == "budgets":
                    if method == "PUT":
                        return ("budget_set", "enter", (program_id, item_id))
                    if method == "GET":
                        return ("budget_get", "read", (program_id, item_id))
                if method == "GET" and sub == "wellness-offerings":
                    return ("wellness_get", "read", (program_id, item_id))
                if sub == "reports" and method == "GET" and item_id == "summary":
                    return ("report_summary", "read", (program_id,))
            elif len(parts) == 5:
                program_id, sub, item_id, tail = parts[1], parts[2], parts[3], parts[4]
                if sub == "participants" and method == "POST" and tail == "status":
                    return ("participant_status", "enter", (program_id, item_id))
                if sub == "access-requests" and method == "POST":
                    if tail == "approve":
                        return ("access_approve", "decide", (program_id, item_id))
                    if tail == "deny":
                        return ("access_deny", "decide", (program_id, item_id))
                    if tail == "void":
                        return ("access_void", "enter", (program_id, item_id))
                    if tail == "disbursements":
                        return ("disbursement_create", "record", (program_id, item_id))
                if sub == "bookings" and method == "POST":
                    if tail == "confirm":
                        return ("booking_confirm", "record", (program_id, item_id))
                    if tail == "cancel":
                        return ("booking_cancel", "enter", (program_id, item_id))
                if sub == "budgets" and method == "GET" and tail == "vs-actual":
                    return ("budget_vs_actual", "read", (program_id, item_id))
                if sub == "wellness-offerings" and method == "POST" and tail == "enrollments":
                    return ("enrollment_create", "enter", (program_id, item_id))
        return (None, None, ())

    # Action names used when auditing a denial for a route whose HTTP
    # permission differs from the operation name (or has none).
    _DENIAL_ACTION = {"member_add": "member_add"}

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [unquote(p) for p in path.split("/") if p != ""]
        route, action, ids = self._route(method, parts)
        denial_action = self._DENIAL_ACTION.get(route, action)
        target = ids[-1] if ids else path
        try:
            if route is None:
                self._error(404, "not found")
                return
            if route == "health":
                self._send_json(200, {"status": "ok"})
                return

            user = self._authenticate(denial_action, target)
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
            if denial_action:
                self._audit_denied(actor, denial_action, target)
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except FinanceError as exc:
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
        if route == "audit_read":
            entries = self.audit.entries() if self.audit is not None else []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "program_list":
            self._send_json(200, {"programs": store.list_programs(user)})
            return
        if route == "program_create":
            body = self._read_json_body()
            program = store.create_program(body.get("name"), user)
            self._send_json(201, program)
            return
        if route == "program_get":
            self._send_json(200, store.get_program(ids[0], user))
            return
        if route == "member_add":
            body = self._read_json_body()
            program = store.add_member(ids[0], body.get("username"), user)
            self._send_json(200, program)
            return
        if route == "participant_list":
            kind = _first_param(params, "kind")
            participants = store.list_participants(ids[0], user, kind=kind)
            self._send_json(200, {"participants": participants})
            return
        if route == "participant_create":
            body = self._read_json_body()
            participant = store.create_participant(
                ids[0], body.get("ref"), body.get("kind"), user
            )
            self._send_json(201, participant)
            return
        if route == "participant_get":
            self._send_json(200, store.get_participant(ids[0], ids[1], user))
            return
        if route == "participant_status":
            body = self._read_json_body()
            participant = store.set_participant_status(
                ids[0], ids[1], body.get("status"), user
            )
            self._send_json(200, participant)
            return
        if route == "accrual_list":
            participant_id = _first_param(params, "participant_id")
            accruals = store.list_accruals(ids[0], user, participant_id=participant_id)
            self._send_json(200, {"accruals": accruals})
            return
        if route == "accrual_create":
            body = self._read_json_body()
            accrual = store.record_accrual(
                ids[0],
                body.get("participant_id"),
                body.get("period"),
                body.get("earned_cents"),
                user,
            )
            self._send_json(201, accrual)
            return
        if route == "accrual_get":
            self._send_json(200, store.get_accrual(ids[0], ids[1], user))
            return
        if route == "access_list":
            status = _first_param(params, "status")
            requests = store.list_access_requests(ids[0], user, status=status)
            self._send_json(200, {"access_requests": requests})
            return
        if route == "access_create":
            body = self._read_json_body()
            request = store.request_access(
                ids[0],
                body.get("participant_id"),
                body.get("period"),
                body.get("amount_cents"),
                body.get("date"),
                user,
            )
            self._send_json(201, request)
            return
        if route == "access_get":
            self._send_json(200, store.get_access_request(ids[0], ids[1], user))
            return
        if route == "access_approve":
            self._read_optional_body()
            self._send_json(200, store.decide_access(ids[0], ids[1], True, user))
            return
        if route == "access_deny":
            self._read_optional_body()
            self._send_json(200, store.decide_access(ids[0], ids[1], False, user))
            return
        if route == "access_void":
            self._read_optional_body()
            self._send_json(200, store.void_access(ids[0], ids[1], user))
            return
        if route == "disbursement_create":
            body = self._read_json_body()
            method = body.get("method", "")
            if method is None:
                method = ""
            disbursement = store.record_disbursement(
                ids[0], ids[1], body.get("date"), user, method=method
            )
            self._send_json(201, disbursement)
            return
        if route == "disbursement_list":
            request_id = _first_param(params, "request_id")
            disbursements = store.list_disbursements(ids[0], user, request_id=request_id)
            self._send_json(200, {"disbursements": disbursements})
            return
        if route == "booking_list":
            status = _first_param(params, "status")
            kind = _first_param(params, "kind")
            bookings = store.list_bookings(ids[0], user, status=status, kind=kind)
            self._send_json(200, {"bookings": bookings})
            return
        if route == "booking_create":
            body = self._read_json_body()
            booking = store.create_booking(
                ids[0],
                body.get("participant_id"),
                body.get("kind"),
                body.get("start_date"),
                body.get("end_date"),
                body.get("amount_cents"),
                user,
            )
            self._send_json(201, booking)
            return
        if route == "booking_get":
            self._send_json(200, store.get_booking(ids[0], ids[1], user))
            return
        if route == "booking_confirm":
            self._read_optional_body()
            self._send_json(200, store.confirm_booking(ids[0], ids[1], user))
            return
        if route == "booking_cancel":
            self._read_optional_body()
            self._send_json(200, store.cancel_booking(ids[0], ids[1], user))
            return
        if route == "budget_set":
            body = self._read_json_body()
            budget = store.set_budget(ids[0], ids[1], body.get("lines"), user)
            self._send_json(200, budget)
            return
        if route == "budget_get":
            self._send_json(200, store.get_budget(ids[0], ids[1], user))
            return
        if route == "budget_vs_actual":
            self._send_json(200, store.spend_vs_budget(ids[0], ids[1], user))
            return
        if route == "wellness_list":
            offerings = store.list_wellness_offerings(ids[0], user)
            self._send_json(200, {"offerings": offerings})
            return
        if route == "wellness_create":
            body = self._read_json_body()
            offering = store.create_wellness_offering(
                ids[0], body.get("title"), body.get("kind"), user
            )
            self._send_json(201, offering)
            return
        if route == "wellness_get":
            self._send_json(200, store.get_wellness_offering(ids[0], ids[1], user))
            return
        if route == "enrollment_create":
            body = self._read_json_body()
            enrollment = store.enroll_participant(
                ids[0], ids[1], body.get("participant_id"), user
            )
            self._send_json(201, enrollment)
            return
        if route == "enrollment_list":
            offering_id = _first_param(params, "offering_id")
            enrollments = store.list_wellness_enrollments(
                ids[0], user, offering_id=offering_id
            )
            self._send_json(200, {"enrollments": enrollments})
            return
        if route == "report_summary":
            period = _first_param(params, "period")
            if period is None:
                raise ValidationError("period is required")
            self._send_json(200, store.program_summary(ids[0], period, user))
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
    """Create (but do not start) the finance HTTP server."""
    if audit is None:
        audit = AuditLog()
    handler = type(
        "FinanceHandler",
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
