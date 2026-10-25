"""HTTP service exposing the cybersecurity functions over a JSON REST API.

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

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent), carried from
the Group 3 (Analytics L3-adjacent) pattern:

- **Unsuccessful logon lockout (AC-7).** ``make_server`` accepts
  ``max_failures`` / ``lockout_seconds``. Consecutive authentication
  failures (unknown user or role mismatch) are tracked per username;
  at ``max_failures`` the username locks for ``lockout_seconds`` and
  any further attempt for it -- even with the correct role -- is
  answered 403 and audited with action ``"auth:locked"``. A successful
  authentication resets that user's counter; lock expiry lets the
  user in again.
- **Audit verification & reduction (AU-9 / AU-7).** ``GET
  /audit/verify`` (audit_read) reports the hash-chain verification
  result; ``GET /audit`` accepts optional ``actor``, ``action``,
  ``target``, ``since`` and ``until`` query parameters passed to
  :meth:`AuditLog.query`.
- **Fail closed (AU-5).** An :class:`AuditWriteError` from the audit
  log is never swallowed by this layer: it propagates (surfacing as a
  400 via the package error mapping) so the operation being audited
  does not proceed.
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
    CyberError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)


class _Handler(BaseHTTPRequestHandler):
    # Injected by make_server.
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
    server_version = "Cyber/0.1"
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
            except AuditWriteError:
                # AU-5 fail closed: a failed audit write propagates so
                # the operation being audited does not proceed.
                raise
            except Exception:
                pass  # Non-durability audit issues never break requests.

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    # -- auth -------------------------------------------------------------

    def _authenticate(self, action, target):
        """Return the User, or send an error and return None.

        Ordinary failures (missing headers, unknown user, role
        mismatch) are 401, audited as denied, and counted per username
        (AC-7). A username at ``max_failures`` consecutive failures is
        locked until ``lockout_seconds`` elapse: attempts during the
        lock -- even with the correct role -- are 403 and audited with
        action ``"auth:locked"``. A successful authentication resets
        the counter; an expired lock clears itself.
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
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["posture"]:
            return ("posture", "read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "read", ())
        if parts and parts[0] == "assets":
            if len(parts) == 1:
                if method == "GET":
                    return ("asset_list", "read", ())
                if method == "POST":
                    return ("asset_create", "manage_assets", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("asset_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "update":
                    return ("asset_update", "manage_assets", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "findings":
            if len(parts) == 1:
                if method == "GET":
                    return ("finding_list", "read", ())
                if method == "POST":
                    return ("finding_ingest", "ingest", ())
            elif len(parts) == 2:
                if method == "POST" and parts[1] == "bulk":
                    return ("finding_bulk", "ingest", ())
                if method == "POST" and parts[1] == "csv":
                    return ("finding_csv", "ingest", ())
                if method == "GET":
                    return ("finding_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "transition":
                    return ("finding_transition", "triage", (parts[1],))
                if method == "POST" and parts[2] == "assign":
                    return ("finding_assign", "triage", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "risks":
            if len(parts) == 1:
                if method == "GET":
                    return ("risk_list", "read", ())
                if method == "POST":
                    return ("risk_create", "manage_risks", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("risk_get", "read", (parts[1],))
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "transition":
                    return ("risk_transition", "manage_risks", (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "controls":
            if len(parts) == 1:
                if method == "GET":
                    return ("control_list", "read", ())
            elif len(parts) == 3:
                if method == "POST" and parts[2] == "assess":
                    return ("control_assess", "assess_controls", (parts[1],))
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
                try:
                    self._audit_denied(actor, action, target)
                except AuditWriteError as audit_exc:
                    # AU-5 fail closed: the denial stands (nothing
                    # proceeded), but a broken audit trail is itself
                    # the reportable failure.
                    self._safe_error(400, audit_exc)
                    return
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except CyberError as exc:
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

        if route == "audit_verify":
            # AU-9: report chain integrity. Count and verification are
            # read before this request's own audit_read entry lands.
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
            # AU-7: optional reduction filters, passed to AuditLog.query.
            actor_f = param("actor")
            action_f = param("action")
            target_f = param("target")
            since = param("since")
            until = param("until")
            if self.audit is None:
                entries = []
            elif any(
                value is not None
                for value in (actor_f, action_f, target_f, since, until)
            ):
                entries = self.audit.query(
                    actor=actor_f,
                    action=action_f,
                    target=target_f,
                    since=since,
                    until=until,
                )
            else:
                entries = self.audit.entries()
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "posture":
            self._send_json(200, store.posture_summary(user))
            return
        if route == "search":
            query_text = param("q")
            if query_text is None:
                query_text = ""
            self._send_json(200, store.search(user, query_text))
            return
        if route == "asset_list":
            self._send_json(200, {"assets": store.list_assets(user, q=param("q"))})
            return
        if route == "asset_create":
            body = self._read_json_body()
            asset = store.create_asset(
                body.get("name"),
                body.get("kind"),
                body.get("owner"),
                body.get("criticality"),
                user,
                tags=body.get("tags"),
            )
            self._send_json(201, asset)
            return
        if route == "asset_get":
            self._send_json(200, store.get_asset(ids[0], user))
            return
        if route == "asset_update":
            body = self._read_json_body()
            asset = store.update_asset(
                ids[0],
                user,
                owner=body.get("owner"),
                criticality=body.get("criticality"),
                tags=body.get("tags"),
            )
            self._send_json(200, asset)
            return
        if route == "finding_list":
            findings = store.list_findings(
                user,
                severity=param("severity"),
                status=param("status"),
                asset_id=param("asset_id"),
                source=param("source"),
                q=param("q"),
            )
            self._send_json(200, {"findings": findings})
            return
        if route == "finding_ingest":
            body = self._read_json_body()
            self._send_json(201, store.ingest_finding(body, user))
            return
        if route == "finding_bulk":
            body = self._read_json_body()
            findings = store.ingest_findings(body.get("findings"), user)
            self._send_json(201, {"findings": findings})
            return
        if route == "finding_csv":
            body = self._read_json_body()
            findings = store.ingest_findings_csv(body.get("csv"), user)
            self._send_json(201, {"findings": findings})
            return
        if route == "finding_get":
            self._send_json(200, store.get_finding(ids[0], user))
            return
        if route == "finding_transition":
            body = self._read_json_body()
            finding = store.transition_finding(ids[0], body.get("status"), user)
            self._send_json(200, finding)
            return
        if route == "finding_assign":
            body = self._read_json_body()
            finding = store.assign_finding(ids[0], body.get("assignee"), user)
            self._send_json(200, finding)
            return
        if route == "risk_list":
            risks = store.list_risks(user, status=param("status"), q=param("q"))
            self._send_json(200, {"risks": risks})
            return
        if route == "risk_create":
            body = self._read_json_body()
            description = body.get("description")
            if description is None:
                description = ""
            owner = body.get("owner", "")
            if owner is None:
                owner = ""
            risk = store.create_risk(
                body.get("title"),
                description,
                body.get("likelihood"),
                body.get("impact"),
                user,
                owner=owner,
                finding_ids=body.get("finding_ids"),
            )
            self._send_json(201, risk)
            return
        if route == "risk_get":
            self._send_json(200, store.get_risk(ids[0], user))
            return
        if route == "risk_transition":
            body = self._read_json_body()
            risk = store.transition_risk(ids[0], body.get("status"), user)
            self._send_json(200, risk)
            return
        if route == "control_list":
            self._send_json(200, {"controls": store.list_controls(user)})
            return
        if route == "control_assess":
            body = self._read_json_body()
            evidence = body.get("evidence", "")
            if evidence is None:
                evidence = ""
            control = store.assess_control(
                ids[0], body.get("status"), user, evidence=evidence
            )
            self._send_json(200, control)
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


def make_server(host, port, store, audit, users, max_failures=3,
                lockout_seconds=300):
    """Create (but do not start) the cyber HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "CyberHandler",
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
