"""HTTP service layer for the custsvc substrate (stdlib http.server).

Authentication is by ``X-User`` / ``X-Role`` headers against a fixed
demo user registry (alice=admin, bob=agent, carol=viewer). These are
demo identities -- hooks, not an identity provider; production
identity belongs to the embedding organization (IA-2).

The store audits successful mutations itself. This layer never
duplicates those records: it audits only denied attempts (401 and
403, with the action name suffixed ``":denied"``) and reads of the
audit log.

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
from urllib.parse import parse_qs, urlparse

from .access import User, require
from .errors import (
    AuditWriteError,
    CustsvcError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

USERS = {
    "alice": "admin",
    "bob": "agent",
    "carol": "viewer",
    "dana": "auditor",
}

# (method, path segments, action, handler) -- "{id}" matches one segment.
ROUTES = [
    ("POST", ("requesters",), "requester_write", "_create_requester"),
    ("GET", ("requesters",), "requester_read", "_list_requesters"),
    ("GET", ("requesters", "{id}"), "requester_read", "_get_requester"),
    ("POST", ("responders",), "responder_write", "_create_responder"),
    ("GET", ("responders",), "responder_read", "_list_responders"),
    ("POST", ("cases",), "case_write", "_create_case"),
    ("GET", ("cases",), "case_read", "_list_cases"),
    ("GET", ("cases", "{id}"), "case_read", "_get_case"),
    ("POST", ("cases", "{id}", "status"), "case_write", "_set_case_status"),
    ("POST", ("cases", "{id}", "assign"), "case_write", "_assign_case"),
    ("POST", ("cases", "{id}", "updates"), "case_write", "_add_case_update"),
    ("GET", ("cases", "{id}", "updates"), "case_read", "_list_case_updates"),
    ("POST", ("alerts",), "alert_write", "_ingest_alert"),
    ("POST", ("alerts", "bulk"), "alert_write", "_ingest_alerts_bulk"),
    ("GET", ("alerts",), "alert_read", "_list_alerts"),
    ("POST", ("alerts", "{id}", "acknowledge"), "alert_write", "_ack_alert"),
    ("POST", ("alerts", "{id}", "resolve"), "alert_write", "_resolve_alert"),
    ("POST", ("alerts", "{id}", "link"), "alert_write", "_link_alert"),
    ("POST", ("schedules",), "schedule_write", "_create_schedule"),
    ("GET", ("schedules",), "schedule_read", "_list_schedules"),
    ("GET", ("schedules", "{id}", "on-call"), "schedule_read", "_on_call"),
    ("POST", ("rules",), "rule_write", "_create_rule"),
    ("GET", ("rules",), "rule_read", "_list_rules"),
    ("POST", ("rules", "{id}", "enabled"), "rule_write", "_set_rule_enabled"),
    ("GET", ("status",), "case_read", "_public_status"),
    ("GET", ("reports", "summary"), "report_read", "_report_summary"),
    ("GET", ("search",), "case_read", "_search_cases"),
    ("GET", ("audit",), "audit_read", "_audit_entries"),
    ("GET", ("audit", "verify"), "audit_read", "_audit_verify"),
]


def _match(route_parts, parts):
    if len(route_parts) != len(parts):
        return None
    ids = []
    for rp, p in zip(route_parts, parts):
        if rp == "{id}":
            ids.append(p)
        elif rp != p:
            return None
    return ids


class _Handler(BaseHTTPRequestHandler):
    server_version = "custsvc/1.0"
    protocol_version = "HTTP/1.1"

    # -- plumbing ------------------------------------------------------

    def log_message(self, format, *args):  # noqa: A002
        pass

    def _send(self, status, body, content_type):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status, obj):
        self._send(status, json.dumps(obj), "application/json")

    def _error(self, status, message):
        self._send_json(status, {"error": message})

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("request body is not valid JSON")
        if not isinstance(body, dict):
            raise ValidationError("request body must be a JSON object")
        return body

    # -- audit / auth ----------------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.server.audit is not None:
            self.server.audit.record(actor, action, target, details)

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

        if name:
            with self.server._auth_lock:
                state = self.server._auth_state.get(name)
                locked_until = state["locked_until"] if state else None
                if locked_until is not None and time.monotonic() >= locked_until:
                    # Lock expired: clear it before judging this attempt.
                    self.server._auth_state.pop(name, None)
                    locked_until = None
            if locked_until is not None:
                self._audit(name, "auth:locked", target)
                self._error(403, "account locked: too many failed logons")
                return None

        if not name or not role or self.server.users.get(name) != role:
            if name:
                with self.server._auth_lock:
                    state = self.server._auth_state.setdefault(
                        name, {"failures": 0, "locked_until": None}
                    )
                    state["failures"] += 1
                    if state["failures"] >= self.server.max_failures:
                        state["locked_until"] = (
                            time.monotonic() + self.server.lockout_seconds
                        )
            self._audit_denied(name, action, target)
            self._error(401, "authentication required: X-User / X-Role headers "
                             "must match a registered demo user")
            return None

        if name:
            with self.server._auth_lock:
                self.server._auth_state.pop(name, None)  # Success resets.
        return User(name=name, role=role)

    def _authorize(self, user, action, target):
        try:
            require(user, action)
            return True
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
            return False

    # -- routing ---------------------------------------------------------

    def _route(self, method, parts):
        for rmethod, rparts, action, handler_name in ROUTES:
            if rmethod != method:
                continue
            ids = _match(rparts, parts)
            if ids is not None:
                return action, handler_name, ids
        return None, None, None

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        parts = tuple(p for p in parsed.path.split("/") if p)
        if parts == ("health",) and method == "GET":
            self._send_json(200, {"status": "ok"})
            return
        action, handler_name, ids = self._route(method, parts)
        if handler_name is None:
            self._error(404, "no such route: %s %s" % (method, parsed.path))
            return
        target = "/".join(parts)
        user = self._authenticate(action, target)
        if user is None:
            return
        if not self._authorize(user, action, target):
            return
        try:
            body = self._read_json_body() if method in ("POST", "PUT", "PATCH") else {}
            result, status = getattr(self, handler_name)(user, ids, parsed, body)
            self._send_json(status, result)
        except AuditWriteError:
            # AU-5 fail closed: a failed audit write propagates so
            # the operation being audited does not proceed.
            raise
        except ValidationError as exc:
            self._error(400, str(exc))
        except NotFoundError as exc:
            self._error(404, str(exc))
        except PermissionDenied as exc:
            self._audit_denied(user.name, action, target)
            self._error(403, str(exc))
        except CustsvcError as exc:
            self._error(400, str(exc))

    # -- handlers --------------------------------------------------------

    def _create_requester(self, user, ids, parsed, body):
        rec = self.server.store.create_requester(
            body.get("ref"), body.get("label"), user)
        return rec, 201

    def _list_requesters(self, user, ids, parsed, body):
        return {"requesters": self.server.store.list_requesters(user)}, 200

    def _get_requester(self, user, ids, parsed, body):
        return self.server.store.get_requester(ids[0], user), 200

    def _create_responder(self, user, ids, parsed, body):
        rec = self.server.store.create_responder(
            body.get("label"), body.get("team"), user)
        return rec, 201

    def _list_responders(self, user, ids, parsed, body):
        return {"responders": self.server.store.list_responders(user)}, 200

    def _create_case(self, user, ids, parsed, body):
        rec = self.server.store.create_case(
            body.get("title"), body.get("body", ""), body.get("requester_ref"),
            user, priority=body.get("priority", "normal"),
            channel=body.get("channel"), due_at=body.get("due_at"),
            assignee=body.get("assignee"))
        return rec, 201

    def _list_cases(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        cases = self.server.store.list_cases(
            user, now=_qs1(qs, "now"), status=_qs1(qs, "status"),
            priority=_qs1(qs, "priority"), assignee=_qs1(qs, "assignee"))
        return {"cases": cases}, 200

    def _get_case(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        return self.server.store.get_case(ids[0], user, now=_qs1(qs, "now")), 200

    def _set_case_status(self, user, ids, parsed, body):
        return self.server.store.set_case_status(ids[0], body.get("status"), user), 200

    def _assign_case(self, user, ids, parsed, body):
        return self.server.store.assign_case(ids[0], body.get("responder_id"), user), 200

    def _add_case_update(self, user, ids, parsed, body):
        rec = self.server.store.add_case_update(
            ids[0], body.get("body"), user, public=bool(body.get("public", False)))
        return rec, 201

    def _list_case_updates(self, user, ids, parsed, body):
        return {"updates": self.server.store.list_case_updates(ids[0], user)}, 200

    def _ingest_alert(self, user, ids, parsed, body):
        rec = self.server.store.ingest_alert(
            body.get("source_ref"), body.get("summary"), body.get("severity"),
            user, case_id=body.get("case_id"))
        return rec, 201

    def _ingest_alerts_bulk(self, user, ids, parsed, body):
        created = self.server.store.ingest_alerts(body.get("alerts"), user)
        return {"alerts": created}, 201

    def _list_alerts(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        alerts = self.server.store.list_alerts(
            user, state=_qs1(qs, "state"), case_id=_qs1(qs, "case_id"))
        return {"alerts": alerts}, 200

    def _ack_alert(self, user, ids, parsed, body):
        return self.server.store.acknowledge_alert(ids[0], user), 200

    def _resolve_alert(self, user, ids, parsed, body):
        return self.server.store.resolve_alert(ids[0], user), 200

    def _link_alert(self, user, ids, parsed, body):
        return self.server.store.link_alert(ids[0], body.get("case_id"), user), 200

    def _create_schedule(self, user, ids, parsed, body):
        rec = self.server.store.create_schedule(
            body.get("name"), body.get("responder_ids"), user,
            period_days=body.get("period_days", 7), anchor=body.get("anchor"))
        return rec, 201

    def _list_schedules(self, user, ids, parsed, body):
        return {"schedules": self.server.store.list_schedules(user)}, 200

    def _on_call(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        return self.server.store.on_call(ids[0], user, at=_qs1(qs, "at")), 200

    def _create_rule(self, user, ids, parsed, body):
        rec = self.server.store.create_rule(
            body.get("name"), body.get("trigger"), body.get("condition"),
            body.get("action_text"), user)
        return rec, 201

    def _list_rules(self, user, ids, parsed, body):
        return {"rules": self.server.store.list_rules(user)}, 200

    def _set_rule_enabled(self, user, ids, parsed, body):
        return self.server.store.set_rule_enabled(
            ids[0], bool(body.get("enabled")), user), 200

    def _public_status(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        return self.server.store.public_status(user, now=_qs1(qs, "now")), 200

    def _report_summary(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        return self.server.store.report_summary(user, now=_qs1(qs, "now")), 200

    def _search_cases(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)
        q = _qs1(qs, "q")
        if q is None:
            raise ValidationError("query parameter q is required")
        return {"cases": self.server.store.search_cases(q, user)}, 200

    def _audit_entries(self, user, ids, parsed, body):
        qs = parse_qs(parsed.query)

        def _first(key):
            values = qs.get(key)
            return values[0] if values else None

        actor_f = _first("actor")
        action_f = _first("action")
        target_f = _first("target")
        since = _first("since")
        until = _first("until")
        if self.server.audit is None:
            entries = []
        elif any(value is not None
                 for value in (actor_f, action_f, target_f, since, until)):
            entries = self.server.audit.query(
                actor=actor_f, action=action_f, target=target_f,
                since=since, until=until)
        else:
            entries = self.server.audit.entries()
        return {"entries": entries}, 200

    def _audit_verify(self, user, ids, parsed, body):
        if self.server.audit is not None:
            ok, first_bad = self.server.audit.verify_chain()
            count = len(self.server.audit.entries())
        else:
            ok, first_bad, count = True, None, 0
        return {"ok": ok, "entries": count, "first_bad_index": first_bad}, 200

    # -- verbs -------------------------------------------------------------

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


def _qs1(qs, name):
    values = qs.get(name)
    return values[0] if values else None


def make_server(host, port, store, audit, users, max_failures=3,
                lockout_seconds=300):
    """Build (but do not start) the HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    server = ThreadingHTTPServer((host, port), _Handler)
    server.store = store
    server.audit = audit
    server.users = users
    server.max_failures = max_failures
    server.lockout_seconds = lockout_seconds
    # Per-username consecutive-authentication-failure state (AC-7):
    # name -> {"failures": int, "locked_until": float | None}.
    server._auth_state = {}
    server._auth_lock = threading.Lock()
    server.daemon_threads = True
    return server
