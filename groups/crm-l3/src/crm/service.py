"""HTTP service exposing the CRM functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks
for the embedding organization's identity system, not an identity
provider.

The store records every successful mutation and every search. This
layer never duplicates those records: it audits only denied attempts
(401 and 403, with the action name suffixed ``":denied"``) and
``audit_read``. Errors are JSON ``{error: msg}`` with 400
(validation), 401 (auth), 403 (permission) or 404 (not found);
handlers never leak a stack trace to the client.

Case list/get and report endpoints accept a ``?now=`` ISO-8601
query parameter so derived breach values are deterministic for
callers and tests.

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent) [L3]:

- **Unsuccessful logon lockout (AC-7).** ``make_server`` accepts
  ``max_failures`` / ``lockout_seconds``. Consecutive authentication
  failures (unknown user or role mismatch) are tracked per username;
  at ``max_failures`` the username locks for ``lockout_seconds`` and
  any further attempt for it -- even with the correct role -- is
  answered 403 and audited with action ``"auth:locked"``. A
  successful authentication resets that user's counter; lock expiry
  lets the user in again.
- **Audit verification & reduction (AU-9 / AU-7).** ``GET
  /audit/verify`` (audit_read) reports the hash-chain verification
  result; ``GET /audit`` accepts optional ``actor``, ``action``,
  ``target``, ``since`` and ``until`` query parameters passed to
  :meth:`AuditLog.query`.
- **Fail closed (AU-5).** An :class:`AuditWriteError` from the audit
  log is never swallowed by the service layer: it propagates and the
  operation does not proceed.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import (
    AuditWriteError,
    CrmError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "operator",
    "carol": "viewer",
    "dana": "auditor",
}
DEMO_USERS = USERS


class _Handler(BaseHTTPRequestHandler):
    store = None
    audit = None
    users = {}
    max_failures = 3
    lockout_seconds = 300
    # Per-username consecutive-authentication-failure state (AC-7):
    # name -> {"failures": int, "locked_until": float | None}.
    # Lives on the handler class make_server builds, so it is scoped
    # to one server instance even though handlers are per-request.
    _auth_state = {}
    _auth_lock = threading.Lock()
    server_version = "Crm/0.1"
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
            except AuditWriteError:
                # AU-5 fail closed: a failed audit write propagates so
                # the operation being audited does not proceed.
                raise
            except Exception:
                pass

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _authenticate(self, action, target):
        """Return the User, or send an error and return None.

        Ordinary failures (missing headers, unknown user, role
        mismatch) are 401, audited as denied, and counted per
        username (AC-7). A username at ``max_failures`` consecutive
        failures is locked until ``lockout_seconds`` elapse: attempts
        during the lock -- even with the correct role -- are 403 and
        audited with action ``"auth:locked"``. A successful
        authentication resets the counter; an expired lock clears
        itself.
        """
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        actor = name if name else "anonymous"

        if name:
            with self._auth_lock:
                state = self._auth_state.get(name)
                locked_until = state["locked_until"] if state else None
                if locked_until is not None and time.monotonic() >= locked_until:
                    # Lock expired: clear it before judging this attempt.
                    self._auth_state.pop(name, None)
                    locked_until = None
            if locked_until is not None:
                self._audit(actor, "auth:locked", target)
                self._error(403, "account locked: too many failed logons")
                return None

        if not name or not role or name not in self.users or self.users[name] != role:
            if name:
                with self._auth_lock:
                    state = self._auth_state.setdefault(
                        name, {"failures": 0, "locked_until": None}
                    )
                    state["failures"] += 1
                    if state["failures"] >= self.max_failures:
                        state["locked_until"] = (
                            time.monotonic() + self.lockout_seconds
                        )
            self._audit_denied(actor, action, target)
            self._error(401, "unauthorized")
            return None

        if name:
            with self._auth_lock:
                self._auth_state.pop(name, None)  # Success resets the counter.
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
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "case_read", ())
        if method == "GET" and parts == ["report"]:
            return ("report", "report_read", ())
        if parts and parts[0] == "accounts":
            if len(parts) == 1:
                if method == "GET":
                    return ("account_list", "registry_read", ())
                if method == "POST":
                    return ("account_create", "registry_write", ())
            if len(parts) == 2 and method == "GET":
                return ("account_get", "registry_read", (parts[1],))
        if parts and parts[0] == "contacts":
            if len(parts) == 1:
                if method == "GET":
                    return ("contact_list", "registry_read", ())
                if method == "POST":
                    return ("contact_create", "registry_write", ())
            if len(parts) == 2 and method == "GET":
                return ("contact_get", "registry_read", (parts[1],))
        if parts and parts[0] == "cases":
            if len(parts) == 1:
                if method == "GET":
                    return ("case_list", "case_read", ())
                if method == "POST":
                    return ("case_create", "case_write", ())
            if len(parts) == 2 and method == "GET":
                return ("case_get", "case_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "assign":
                return ("case_assign", "case_write", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("case_transition", "case_write", (parts[1],))
        if parts and parts[0] == "interactions":
            if len(parts) == 1:
                if method == "GET":
                    return ("interaction_list", "interaction_read", ())
                if method == "POST":
                    return ("interaction_create", "interaction_write", ())
            if len(parts) == 2 and method == "GET":
                return ("interaction_get", "interaction_read", (parts[1],))
        if parts and parts[0] == "guides":
            if len(parts) == 1:
                if method == "GET":
                    return ("guide_list", "guide_read", ())
                if method == "POST":
                    return ("guide_create", "guide_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("guide_get", "guide_read", (parts[1],))
                if method == "PATCH":
                    return ("guide_update", "guide_write", (parts[1],))
        if parts and parts[0] == "findings":
            if len(parts) == 1:
                if method == "GET":
                    return ("finding_list", "finding_read", ())
                if method == "POST":
                    return ("finding_create", "finding_write", ())
            if len(parts) == 2 and method == "GET":
                return ("finding_get", "finding_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "transition":
                return ("finding_transition", "finding_write", (parts[1],))
        if parts and parts[0] == "modules":
            if len(parts) == 1:
                if method == "GET":
                    return ("module_list", "config_read", ())
                if method == "POST":
                    return ("module_create", "config_write", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("module_get", "config_read", (parts[1],))
                if method == "PATCH":
                    return ("module_update", "config_write", (parts[1],))
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
        except CrmError as exc:
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

    def _execute(self, route, user, ids, parsed):
        store = self.store
        if route == "audit_verify":
            if self.audit is not None:
                ok, first_bad = self.audit.verify_chain()
                count = len(self.audit.entries())
            else:
                ok, first_bad, count = True, None, 0
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(
                200,
                {"ok": ok, "entries": count, "first_bad_index": first_bad},
            )
            return
        if route == "audit_read":
            params = parse_qs(parsed.query)

            def _first(key):
                values = params.get(key)
                return values[0] if values else None

            actor_f = _first("actor")
            action_f = _first("action")
            target_f = _first("target")
            since = _first("since")
            until = _first("until")
            if self.audit is None:
                entries = []
            elif any(
                value is not None
                for value in (actor_f, action_f, target_f, since, until)
            ):
                entries = self.audit.query(
                    actor=actor_f, action=action_f, target=target_f,
                    since=since, until=until,
                )
            else:
                entries = self.audit.entries()
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
        if route == "account_list":
            self._send_json(200, {"accounts": store.list_accounts(user)})
            return
        if route == "account_create":
            body = self._read_json_body()
            self._send_json(201, store.create_account(
                user, body.get("reference"),
                label=body.get("label"), attributes=body.get("attributes")))
            return
        if route == "account_get":
            self._send_json(200, store.get_account(ids[0], user))
            return
        if route == "contact_list":
            params = parse_qs(parsed.query)
            account_id = (params.get("account_id") or [None])[0]
            self._send_json(200, {"contacts": store.list_contacts(
                user, account_id=account_id)})
            return
        if route == "contact_create":
            body = self._read_json_body()
            self._send_json(201, store.create_contact(
                user, body.get("account_id"), body.get("reference"),
                label=body.get("label"), attributes=body.get("attributes")))
            return
        if route == "contact_get":
            self._send_json(200, store.get_contact(ids[0], user))
            return
        if route == "case_list":
            params = parse_qs(parsed.query)
            status = (params.get("status") or [None])[0]
            case_type = (params.get("case_type") or [None])[0]
            account_id = (params.get("account_id") or [None])[0]
            self._send_json(200, {"cases": store.list_cases(
                user, now=self._now_param(parsed), status=status,
                case_type=case_type, account_id=account_id)})
            return
        if route == "case_create":
            body = self._read_json_body()
            case = store.create_case(
                user, body.get("case_type"), body.get("subject"),
                account_id=body.get("account_id"), contact_id=body.get("contact_id"),
                assignee_ref=body.get("assignee_ref"),
                priority=body.get("priority", "normal") or "normal",
                due_at=body.get("due_at"))
            self._send_json(201, case)
            return
        if route == "case_get":
            self._send_json(200, store.get_case(ids[0], user, now=self._now_param(parsed)))
            return
        if route == "case_assign":
            body = self._read_json_body()
            self._send_json(200, store.assign_case(
                ids[0], user, body.get("assignee_ref")))
            return
        if route == "case_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_case(ids[0], user, to_status))
            return
        if route == "interaction_list":
            params = parse_qs(parsed.query)
            case_id = (params.get("case_id") or [None])[0]
            account_id = (params.get("account_id") or [None])[0]
            self._send_json(200, {"interactions": store.list_interactions(
                user, case_id=case_id, account_id=account_id)})
            return
        if route == "interaction_create":
            body = self._read_json_body()
            self._send_json(201, store.record_interaction(
                user, body.get("channel"), body.get("direction"), body.get("summary"),
                account_id=body.get("account_id"), contact_id=body.get("contact_id"),
                case_id=body.get("case_id"), guide_id=body.get("guide_id"),
                outcome=body.get("outcome"), external_ref=body.get("external_ref")))
            return
        if route == "interaction_get":
            self._send_json(200, store.get_interaction(ids[0], user))
            return
        if route == "guide_list":
            self._send_json(200, {"guides": store.list_guides(user)})
            return
        if route == "guide_create":
            body = self._read_json_body()
            self._send_json(201, store.create_guide(
                user, body.get("title"), body.get("kind"), body.get("target_ref"),
                steps=body.get("steps"),
                enabled=body.get("enabled", True)))
            return
        if route == "guide_get":
            self._send_json(200, store.get_guide(ids[0], user))
            return
        if route == "guide_update":
            body = self._read_json_body()
            self._send_json(200, store.update_guide(
                ids[0], user, steps=body.get("steps"),
                enabled=body.get("enabled"), target_ref=body.get("target_ref")))
            return
        if route == "finding_list":
            params = parse_qs(parsed.query)
            status = (params.get("status") or [None])[0]
            account_id = (params.get("account_id") or [None])[0]
            self._send_json(200, {"findings": store.list_findings(
                user, status=status, account_id=account_id)})
            return
        if route == "finding_create":
            body = self._read_json_body()
            self._send_json(201, store.create_finding(
                user, body.get("title"), detail=body.get("detail"),
                severity=body.get("severity", "info") or "info",
                account_id=body.get("account_id"), source=body.get("source")))
            return
        if route == "finding_get":
            self._send_json(200, store.get_finding(ids[0], user))
            return
        if route == "finding_transition":
            body = self._read_json_body()
            to_status = body.get("to_status", body.get("status"))
            self._send_json(200, store.transition_finding(ids[0], user, to_status))
            return
        if route == "module_list":
            self._send_json(200, {"modules": store.list_modules(user)})
            return
        if route == "module_create":
            body = self._read_json_body()
            self._send_json(201, store.create_module(
                user, body.get("label"), body.get("scope"), body.get("settings_text"),
                enabled=body.get("enabled", True)))
            return
        if route == "module_get":
            self._send_json(200, store.get_module(ids[0], user))
            return
        if route == "module_update":
            body = self._read_json_body()
            self._send_json(200, store.update_module(
                ids[0], user, settings_text=body.get("settings_text"),
                enabled=body.get("enabled")))
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


def make_server(host, port, store, audit, users, max_failures=3,
                lockout_seconds=300):
    """Create (but do not start) the CRM HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "CrmHandler",
        (_Handler,),
        {
            "store": store,
            "audit": audit,
            "users": dict(users or {}),
            "max_failures": max_failures,
            "lockout_seconds": lockout_seconds,
            "_auth_state": {},
            "_auth_lock": threading.Lock(),
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
