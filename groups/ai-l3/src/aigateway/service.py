"""HTTP service exposing the AI gateway functions over a JSON REST API.

Standard library only (``http.server``). Authentication is by
``X-User`` / ``X-Role`` headers checked against the server's user
registry: the role header must match the registered role for that
user, otherwise the request is rejected with 401. These are hooks for
the embedding organization's identity system, not an identity
provider.

The invocation endpoint is OpenAI-*flavored* (a model name and a
prompt in, a completion-shaped response out); it is this build's own
API, not OpenAI's. The responder behind it is a deterministic
reference stub, labeled as such in every response.

The store records every successful mutation, every completed
invocation, and every policy block. This layer never duplicates those
records: it audits only denied attempts (401, 403, 422, 429, with the
action name suffixed ``":denied"``) and ``audit_read``. Errors are
JSON ``{error: msg}`` with 400 (validation), 401 (auth), 403
(permission), 404 (not found), 422 (policy blocked), or 429 (quota
exceeded); handlers never leak a stack trace to the client.

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent), carried from
the Analytics / Cybersecurity / Collaboration L3 pattern:

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
  :meth:`AuditLog.query`. ``GET /audit`` keeps this build's L2
  ordering: the ``audit_read`` entry is recorded first, so the
  returned trail includes the read itself.
- **Fail closed (AU-5).** An :class:`AuditWriteError` from the audit
  log is never swallowed by this layer: it propagates (surfacing as a
  500 ``audit write failed``) so the operation being audited does not
  proceed.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import (
    AIGatewayError,
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    PolicyBlocked,
    QuotaExceeded,
    ValidationError,
)


def _parse_version(segment):
    try:
        return int(segment)
    except (TypeError, ValueError):
        raise ValidationError("version must be an integer: %r" % (segment,))


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
    server_version = "AIGateway/0.1"
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
        if action:
            self._audit(actor, "%s:denied" % (action,), target)

    def _audit_denial_or_fail(self, actor, action, target):
        """Audit a store-raised denial; on an audit write failure
        (AU-5) send the 500 and return False -- the denial stands
        (nothing proceeded), but a broken audit trail is itself the
        reportable failure (mirrors the cyber-l3 handler)."""
        try:
            self._audit_denied(actor, action, target)
        except AuditWriteError:
            self._safe_error(500, "audit write failed")
            return False
        return True

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
        """Return (route, permission_action, ids) for a known route.

        Returns (None, None, ()) for unknown routes.
        """
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if parts == ["models"]:
            if method == "GET":
                return ("model_list", "read", ())
            if method == "POST":
                return ("model_create", "registry_write", ())
            return (None, None, ())
        if parts == ["templates"]:
            if method == "GET":
                return ("template_list", "read", ())
            if method == "POST":
                return ("template_create", "registry_write", ())
            return (None, None, ())
        if parts == ["keys"]:
            if method == "GET":
                return ("key_list", "read", ())
            if method == "POST":
                return ("key_create", "registry_write", ())
            return (None, None, ())
        if parts == ["quotas"]:
            if method == "POST":
                return ("quota_set", "admin", ())
            return (None, None, ())
        if len(parts) == 2 and parts[0] == "usage":
            if method == "GET":
                return ("usage_get", "usage_read", (parts[1],))
            return (None, None, ())
        if parts == ["v1", "completions"]:
            if method == "POST":
                return ("completion_create", "invoke", ())
            return (None, None, ())
        if parts == ["requests"]:
            if method == "GET":
                return ("request_list", "read", ())
            return (None, None, ())
        if len(parts) == 2 and parts[0] == "requests":
            if method == "GET":
                return ("request_get", "read", (parts[1],))
            return (None, None, ())
        if parts == ["sessions"]:
            if method == "GET":
                return ("session_list", "read", ())
            if method == "POST":
                return ("session_create", "invoke", ())
            return (None, None, ())
        if len(parts) == 2 and parts[0] == "sessions":
            if method == "GET":
                return ("session_get", "read", (parts[1],))
            return (None, None, ())
        if parts == ["policy", "rules"]:
            if method == "GET":
                return ("rule_list", "read", ())
            if method == "POST":
                return ("rule_create", "policy_write", ())
            return (None, None, ())
        if len(parts) == 3 and parts[0] == "policy" and parts[1] == "rules":
            if method == "DELETE":
                return ("rule_delete", "policy_write", (parts[2],))
            return (None, None, ())
        if parts == ["eval", "datasets"]:
            if method == "GET":
                return ("eval_dataset_list", "read", ())
            if method == "POST":
                return ("eval_dataset_create", "eval_run", ())
            return (None, None, ())
        if len(parts) == 3 and parts[0] == "eval" and parts[1] == "datasets":
            if method == "GET":
                return ("eval_dataset_get", "read", (parts[2],))
            return (None, None, ())
        if len(parts) == 4 and parts[0] == "eval" and parts[1] == "datasets" \
                and parts[3] == "runs":
            if method == "POST":
                return ("eval_run_create", "eval_run", (parts[2],))
            return (None, None, ())
        if len(parts) == 3 and parts[0] == "eval" and parts[1] == "runs":
            if method == "GET":
                return ("eval_run_get", "read", (parts[2],))
            return (None, None, ())
        if parts and parts[0] == "models":
            if len(parts) == 2 and method == "GET":
                return ("model_get", "read", (parts[1],))
            if len(parts) == 4 and parts[2] == "versions":
                if method == "GET":
                    return ("model_version_get", "read", (parts[1], parts[3]))
                return (None, None, ())
            if len(parts) == 5 and parts[2] == "versions" and parts[4] == "status":
                if method == "POST":
                    return ("model_status", "registry_write",
                            (parts[1], parts[3]))
                return (None, None, ())
        return (None, None, ())

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [unquote(p) for p in path.split("/") if p != ""]
        route, action, ids = self._route(method, parts)
        target = ids[-1] if ids else path
        actor_for_denial = self.headers.get("X-User") or "anonymous"
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
            # successes only, so this is recorded exactly once, as a
            # denial).
            if not self._audit_denial_or_fail(actor_for_denial, action, target):
                return
            self._safe_error(403, exc)
        except PolicyBlocked as exc:
            if not self._audit_denial_or_fail(actor_for_denial, action, target):
                return
            self._safe_error(422, exc)
        except QuotaExceeded as exc:
            if not self._audit_denial_or_fail(actor_for_denial, action, target):
                return
            self._safe_error(429, exc)
        except NotFoundError as exc:
            self._safe_error(404, exc)
        except AuditWriteError:
            # AU-5 fail closed: an operation whose audit write failed
            # does not proceed; the failure itself is the response.
            self._safe_error(500, "audit write failed")
        except AIGatewayError as exc:
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
            # Record the read first, so the returned trail includes
            # this audit_read entry itself (the L2 ordering, kept).
            self._audit(user.name, "audit_read", parsed.path)
            # AU-7: optional reduction filters, passed to
            # AuditLog.query when any are present.
            params = parse_qs(parsed.query)

            def _first(key):
                values = params.get(key)
                return values[0] if values else None

            filters = {}
            for key in ("actor", "action", "target", "since", "until"):
                value = _first(key)
                if value is not None:
                    filters[key] = value
            if self.audit is None:
                entries = []
            elif filters:
                entries = self.audit.query(**filters)
            else:
                entries = self.audit.entries()
            self._send_json(200, {"entries": entries})
            return
        if route == "model_list":
            self._send_json(200, {"models": store.list_models(user)})
            return
        if route == "model_create":
            body = self._read_json_body()
            model = store.register_model(
                body.get("name"), body.get("responder"), user,
                version=body.get("version"),
                provider=body.get("provider") or "",
                capabilities=body.get("capabilities"),
                config=body.get("config"),
            )
            self._send_json(201, model)
            return
        if route == "model_get":
            self._send_json(200, store.get_model(ids[0], user))
            return
        if route == "model_version_get":
            self._send_json(
                200, store.get_model(ids[0], user, version=_parse_version(ids[1]))
            )
            return
        if route == "model_status":
            body = self._read_json_body()
            model = store.set_model_status(
                ids[0], _parse_version(ids[1]), body.get("status"), user
            )
            self._send_json(200, model)
            return
        if route == "template_list":
            self._send_json(200, {"templates": store.list_templates(user)})
            return
        if route == "template_create":
            body = self._read_json_body()
            template = store.register_template(
                body.get("name"), body.get("text"), user,
                version=body.get("version"),
            )
            self._send_json(201, template)
            return
        if route == "key_list":
            self._send_json(200, {"keys": store.list_api_keys(user)})
            return
        if route == "key_create":
            body = self._read_json_body()
            key = store.create_api_key(body.get("owner"), user)
            self._send_json(201, key)
            return
        if route == "quota_set":
            body = self._read_json_body()
            quota = store.set_quota(body.get("owner"), body.get("token_limit"), user)
            self._send_json(200, quota)
            return
        if route == "usage_get":
            self._send_json(200, store.usage_for(ids[0], user))
            return
        if route == "completion_create":
            body = self._read_json_body()
            record = store.invoke(
                body.get("model"), body.get("prompt"), user,
                version=body.get("version"),
                key_id=body.get("key_id"),
                session_id=body.get("session_id"),
                template_name=body.get("template"),
            )
            self._send_json(201, record)
            return
        if route == "request_list":
            params = parse_qs(parsed.query)
            session_id = (params.get("session_id") or [None])[0]
            self._send_json(
                200, {"requests": store.list_requests(user, session_id=session_id)}
            )
            return
        if route == "request_get":
            self._send_json(200, store.get_request(ids[0], user))
            return
        if route == "session_list":
            self._send_json(200, {"sessions": store.list_sessions(user)})
            return
        if route == "session_create":
            body = self._read_json_body()
            session = store.create_session(body.get("title"), user)
            self._send_json(201, session)
            return
        if route == "session_get":
            self._send_json(200, store.get_session(ids[0], user))
            return
        if route == "rule_list":
            self._send_json(200, {"rules": store.list_rules(user)})
            return
        if route == "rule_create":
            body = self._read_json_body()
            rule = store.add_rule(
                body.get("scope"), body.get("kind"), body.get("value"), user
            )
            self._send_json(201, rule)
            return
        if route == "rule_delete":
            rule = store.remove_rule(ids[0], user)
            self._send_json(200, rule)
            return
        if route == "eval_dataset_list":
            self._send_json(200, {"datasets": store.list_eval_datasets(user)})
            return
        if route == "eval_dataset_create":
            body = self._read_json_body()
            dataset = store.create_eval_dataset(
                body.get("name"), body.get("cases"), user
            )
            self._send_json(201, dataset)
            return
        if route == "eval_dataset_get":
            self._send_json(200, store.get_eval_dataset(ids[0], user))
            return
        if route == "eval_run_create":
            body = self._read_json_body()
            run = store.run_eval(
                ids[0], body.get("model"), user, version=body.get("version")
            )
            self._send_json(201, run)
            return
        if route == "eval_run_get":
            self._send_json(200, store.get_eval_run(ids[0], user))
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
    """Create (but do not start) the aigateway HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "AIGatewayHandler",
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
