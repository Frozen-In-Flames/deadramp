"""HTTP service exposing the analytics functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that user,
otherwise the request is rejected with 401. These are hooks for the
embedding organization's identity system, not an identity provider.

Every successful ingest / query / describe / export / chart operation
is audited, and every denied attempt (401 / 403) is audited with the
action name suffixed ``":denied"``. Errors are JSON ``{error: msg}``
with 400 (validation), 401 (auth), 403 (permission) or 404 (not
found); handlers never leak a stack trace to the client.

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent):

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
  ``since`` and ``until`` query parameters passed to
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
from .audit import AuditLog
from .charts import chart_svg
from .errors import (
    AnalyticsError,
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from .query import describe, run_query
from .reports import result_to_csv, result_to_json


def _lower_layer_audited(store, audit):
    """True when the store's own audit log is the server's audit log.

    In that wiring the store / query layer already records ingest,
    query and describe, so the service must not double-record them.
    """
    return audit is not None and getattr(store, "audit", None) is audit


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
    server_version = "Analytics/0.1"
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

    def _audit_success(self, actor, action, target):
        if action in ("ingest", "query", "describe") and _lower_layer_audited(
            self.store, self.audit
        ):
            return  # Already recorded by the store / query layer.
        self._audit(actor, action, target)

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

    def _route(self, method, parsed):
        """Return (action, dataset_id) for known routes, else (None, None)."""
        path = parsed.path.rstrip("/") or "/"
        parts = [p for p in path.split("/") if p != ""]
        if method == "GET" and path == "/health":
            return ("health", None)
        if method == "GET" and path == "/audit/verify":
            return ("audit_verify", None)
        if method == "GET" and path == "/audit":
            return ("audit_read", None)
        if parts and parts[0] == "datasets":
            if len(parts) == 1:
                if method == "GET":
                    return ("query", None)
                if method == "POST":
                    return ("ingest", None)
            elif len(parts) == 2:
                if method == "GET":
                    return ("query", parts[1])
            elif len(parts) == 3:
                dataset_id = parts[1]
                if method == "POST" and parts[2] == "query":
                    return ("query", dataset_id)
                if method == "POST" and parts[2] == "describe":
                    return ("describe", dataset_id)
                if method == "GET" and parts[2] == "export":
                    return ("export", dataset_id)
                if method == "GET" and parts[2] == "chart":
                    return ("chart", dataset_id)
        return (None, None)

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        action, dataset_id = self._route(method, parsed)
        try:
            if action is None:
                self._error(404, "not found")
                return
            if action == "health":
                self._send_json(200, {"status": "ok"})
                return

            target = dataset_id if dataset_id is not None else parsed.path
            user = self._authenticate(action, target)
            if user is None:
                return
            # describe rides on the query permission and chart on the
            # export permission; their audit action names stay
            # "describe" / "chart". Chain verification rides on the
            # audit_read permission.
            permission_action = {
                "describe": "query",
                "chart": "export",
                "audit_verify": "audit_read",
            }.get(action, action)
            if not self._authorize(user, permission_action, target):
                return

            if action == "audit_verify":
                if self.audit is not None:
                    ok, first_bad = self.audit.verify_chain()
                    count = len(self.audit.entries())
                else:
                    ok, first_bad, count = True, None, 0
                self._audit(user.name, "audit_read", target)
                self._send_json(
                    200,
                    {"ok": ok, "entries": count, "first_bad_index": first_bad},
                )
                return
            if action == "audit_read":
                self._handle_audit(user, target, parsed)
                return
            if method == "GET" and dataset_id is None and action == "query":
                self._send_json(200, {"datasets": self.store.list()})
                return
            if action == "ingest":
                self._handle_ingest(user)
                return
            if method == "GET" and dataset_id is not None and action == "query" and parsed.path.rstrip("/").count("/") == 2:
                dataset = self.store.get(dataset_id)
                self._send_json(200, dataset)
                return
            if action == "query":
                self._handle_query(user, dataset_id)
                return
            if action == "describe":
                self._handle_describe(user, dataset_id)
                return
            if action == "export":
                self._handle_export(user, dataset_id, parsed)
                return
            if action == "chart":
                self._handle_chart(user, dataset_id, parsed)
                return
            self._error(404, "not found")
        except ValidationError as exc:
            self._safe_error(400, exc)
        except PermissionDenied as exc:
            self._safe_error(403, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except AnalyticsError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    # -- endpoint handlers ---------------------------------------------------

    def _handle_audit(self, user, target, parsed):
        """GET /audit (AU-7): the trail, optionally reduced by the
        ``actor`` / ``action`` / ``since`` / ``until`` query parameters
        passed through to :meth:`AuditLog.query`. With no parameters
        the unfiltered trail is returned, as before."""
        params = parse_qs(parsed.query)

        def _first(key):
            values = params.get(key)
            return values[0] if values else None

        actor = _first("actor")
        action_filter = _first("action")
        since = _first("since")
        until = _first("until")
        if self.audit is None:
            entries = []
        elif any(
            value is not None
            for value in (actor, action_filter, since, until)
        ):
            entries = self.audit.query(
                actor=actor, action=action_filter, since=since, until=until
            )
        else:
            entries = self.audit.entries()
        self._audit(user.name, "audit_read", target)
        self._send_json(200, {"entries": entries})

    def _handle_ingest(self, user):
        body = self._read_json_body()
        name = body.get("name")
        fmt = body.get("format")
        data = body.get("data")
        if fmt not in ("csv", "json"):
            raise ValidationError("format must be 'csv' or 'json'")
        if data is None:
            raise ValidationError("request body is missing 'data'")
        if not isinstance(data, str):
            if fmt == "json":
                data = json.dumps(data)
            else:
                raise ValidationError("'data' must be a string for csv format")
        if fmt == "csv":
            dataset = self.store.ingest_csv(name, data, user)
        else:
            dataset = self.store.ingest_json(name, data, user)
        self._audit_success(user.name, "ingest", dataset["id"])
        self._send_json(201, dataset)

    def _handle_query(self, user, dataset_id):
        body = self._read_json_body()
        result = run_query(self.store, dataset_id, body, user)
        self._audit_success(user.name, "query", dataset_id)
        self._send_json(200, result)

    def _handle_describe(self, user, dataset_id):
        body = self._read_json_body()
        column = body.get("column")
        if not isinstance(column, str) or not column:
            raise ValidationError("request body is missing 'column'")
        result = describe(self.store, dataset_id, column, user)
        self._audit_success(user.name, "describe", dataset_id)
        self._send_json(200, result)

    def _dataset_result(self, dataset_id):
        dataset = self.store.get(dataset_id)
        rows = self.store.rows(dataset_id)
        return {"columns": dataset["columns"], "rows": rows, "row_count": len(rows)}

    def _handle_export(self, user, dataset_id, parsed):
        params = parse_qs(parsed.query)
        fmt = (params.get("format") or ["csv"])[0]
        if fmt not in ("csv", "json"):
            raise ValidationError("format must be 'csv' or 'json'")
        result = self._dataset_result(dataset_id)
        self._audit_success(user.name, "export", dataset_id)
        if fmt == "csv":
            self._send(200, result_to_csv(result), "text/csv")
        else:
            self._send(200, result_to_json(result), "application/json")

    def _handle_chart(self, user, dataset_id, parsed):
        params = parse_qs(parsed.query)
        kind = (params.get("kind") or ["bar"])[0]
        label = (params.get("label") or [None])[0]
        value = (params.get("value") or [None])[0]
        if not label or not value:
            raise ValidationError("chart requires 'label' and 'value' parameters")
        result = self._dataset_result(dataset_id)
        svg = chart_svg(result, label, value, kind=kind)
        self._audit_success(user.name, "chart", dataset_id)
        self._send(200, svg, "image/svg+xml")

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
    """Create (but do not start) the analytics HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "AnalyticsHandler",
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
