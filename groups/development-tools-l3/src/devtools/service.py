"""HTTP service exposing the development-tools records over JSON.

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
    DevToolsError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

USERS = {
    "alice": "admin",
    "bob": "developer",
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
    server_version = "DevTools/0.1"
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
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "search", ())
        if parts and parts[0] == "projects":
            if len(parts) == 1:
                if method == "GET":
                    return ("project_list", "project_read", ())
                if method == "POST":
                    return ("project_create", "project_write", ())
            if len(parts) == 2 and method == "GET":
                return ("project_get", "project_read", (parts[1],))
        if parts and parts[0] == "issues":
            if len(parts) == 1:
                if method == "GET":
                    return ("issue_list", "issue_read", ())
                if method == "POST":
                    return ("issue_create", "issue_write", ())
            if len(parts) == 2 and method == "GET":
                return ("issue_get", "issue_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "status":
                return ("issue_status", "issue_write", (parts[1],))
        if parts and parts[0] == "reviews":
            if len(parts) == 1:
                if method == "GET":
                    return ("review_list", "review_read", ())
                if method == "POST":
                    return ("review_create", "review_write", ())
            if len(parts) == 2 and method == "GET":
                return ("review_get", "review_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "state":
                return ("review_state", "review_write", (parts[1],))
        if parts and parts[0] == "builds":
            if len(parts) == 1:
                if method == "GET":
                    return ("build_list", "build_read", ())
                if method == "POST":
                    return ("build_create", "build_write", ())
            if len(parts) == 2 and method == "GET":
                return ("build_get", "build_read", (parts[1],))
        if parts and parts[0] == "releases":
            if len(parts) == 1:
                if method == "GET":
                    return ("release_list", "release_read", ())
                if method == "POST":
                    return ("release_create", "release_write", ())
            if len(parts) == 2 and method == "GET":
                return ("release_get", "release_read", (parts[1],))
        if parts and parts[0] == "artifacts":
            if len(parts) == 1:
                if method == "GET":
                    return ("artifact_list", "artifact_read", ())
                if method == "POST":
                    return ("artifact_create", "artifact_write", ())
            if len(parts) == 2 and method == "GET":
                return ("artifact_get", "artifact_read", (parts[1],))
            if len(parts) == 3 and method == "POST" and parts[2] == "verify":
                return ("artifact_verify", "artifact_read", (parts[1],))
        if parts and parts[0] == "environments":
            if len(parts) == 1:
                if method == "GET":
                    return ("environment_list", "deployment_read", ())
                if method == "POST":
                    return ("environment_create", "deployment_write", ())
        if parts and parts[0] == "deployments":
            if len(parts) == 1:
                if method == "GET":
                    return ("deployment_list", "deployment_read", ())
                if method == "POST":
                    return ("deployment_create", "deployment_write", ())
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
        except AuditWriteError:
            self._safe_error(500, "audit write failed")
        except DevToolsError as exc:
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
            self._send_json(200, store.search(self._param(parsed, "q"), user))
            return
        if route == "project_list":
            self._send_json(200, {"projects": store.list_projects(user)})
            return
        if route == "project_create":
            body = self._read_json_body()
            rec = store.create_project(body.get("name"), user, description=body.get("description"), repo_url=body.get("repo_url"))
            self._send_json(201, rec)
            return
        if route == "project_get":
            self._send_json(200, store.get_project(ids[0], user))
            return
        if route == "issue_list":
            recs = store.list_issues(project_id=self._param(parsed, "project_id"), status=self._param(parsed, "status"), actor=user)
            self._send_json(200, {"issues": recs})
            return
        if route == "issue_create":
            body = self._read_json_body()
            rec = store.create_issue(body.get("project_id"), body.get("title"), user, description=body.get("description"), kind=body.get("kind") or "issue", priority=body.get("priority") or "medium")
            self._send_json(201, rec)
            return
        if route == "issue_get":
            self._send_json(200, store.get_issue(ids[0], user))
            return
        if route == "issue_status":
            body = self._read_json_body()
            self._send_json(200, store.set_issue_status(ids[0], body.get("status"), user))
            return
        if route == "review_list":
            recs = store.list_reviews(project_id=self._param(parsed, "project_id"), actor=user)
            self._send_json(200, {"reviews": recs})
            return
        if route == "review_create":
            body = self._read_json_body()
            rec = store.create_review(body.get("project_id"), body.get("title"), user, source_ref=body.get("source_ref"))
            self._send_json(201, rec)
            return
        if route == "review_get":
            self._send_json(200, store.get_review(ids[0], user))
            return
        if route == "review_state":
            body = self._read_json_body()
            self._send_json(200, store.set_review_state(ids[0], body.get("state"), user))
            return
        if route == "build_list":
            recs = store.list_builds(project_id=self._param(parsed, "project_id"), actor=user)
            self._send_json(200, {"builds": recs})
            return
        if route == "build_create":
            body = self._read_json_body()
            rec = store.record_build(body.get("project_id"), user, ref=body.get("ref"), status=body.get("status") or "succeeded", config=body.get("config"))
            self._send_json(201, rec)
            return
        if route == "build_get":
            self._send_json(200, store.get_build(ids[0], user))
            return
        if route == "release_list":
            recs = store.list_releases(project_id=self._param(parsed, "project_id"), actor=user)
            self._send_json(200, {"releases": recs})
            return
        if route == "release_create":
            body = self._read_json_body()
            rec = store.create_release(body.get("project_id"), body.get("version"), user, notes=body.get("notes"), build_id=body.get("build_id"))
            self._send_json(201, rec)
            return
        if route == "release_get":
            self._send_json(200, store.get_release(ids[0], user))
            return
        if route == "artifact_list":
            recs = store.list_artifacts(project_id=self._param(parsed, "project_id"), actor=user)
            self._send_json(200, {"artifacts": recs})
            return
        if route == "artifact_create":
            body = self._read_json_body()
            rec = store.register_artifact(body.get("project_id"), body.get("name"), user, version=body.get("version"), checksum=body.get("checksum"), content=body.get("content"))
            self._send_json(201, rec)
            return
        if route == "artifact_get":
            self._send_json(200, store.get_artifact(ids[0], user))
            return
        if route == "artifact_verify":
            body = self._read_json_body()
            match = store.verify_artifact(ids[0], body.get("content"), user)
            self._send_json(200, {"match": match})
            return
        if route == "environment_list":
            self._send_json(200, {"environments": store.list_environments(user)})
            return
        if route == "environment_create":
            body = self._read_json_body()
            rec = store.create_environment(body.get("name"), user, tier=body.get("tier"))
            self._send_json(201, rec)
            return
        if route == "deployment_list":
            recs = store.list_deployments(environment_id=self._param(parsed, "environment_id"), project_id=self._param(parsed, "project_id"), actor=user)
            self._send_json(200, {"deployments": recs})
            return
        if route == "deployment_create":
            body = self._read_json_body()
            rec = store.record_deployment(body.get("environment_id"), body.get("project_id"), user, release_id=body.get("release_id"), artifact_id=body.get("artifact_id"), status=body.get("status") or "deployed")
            self._send_json(201, rec)
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
    """Create (but do not start) the devtools HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "DevToolsHandler",
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
