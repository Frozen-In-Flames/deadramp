"""HTTP service exposing the Cloud Infrastructure & Hosting
functions over a JSON REST API.

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

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent) [L3]:

- **Unsuccessful logon lockout (AC-7).** ``make_server`` accepts
  ``max_failures`` / ``lockout_seconds``. Consecutive authentication
  failures (unknown user or role mismatch) are tracked per
  username; at ``max_failures`` the username locks for
  ``lockout_seconds`` and any further attempt for it -- even with
  the correct role -- is answered 403 and audited with action
  ``"auth:locked"``. A successful authentication resets that user's
  counter; lock expiry lets the user in again. Permission denials
  (an authenticated 403) never count as failures.
- **Audit verification & reduction (AU-9 / AU-7).** ``GET
  /audit/verify`` (audit_read) reports the hash-chain verification
  result; ``GET /audit`` accepts optional ``actor``, ``action``,
  ``target``, ``since`` and ``until`` query parameters passed to
  :meth:`AuditLog.query`. An unfiltered ``GET /audit`` keeps the
  founding shape.
- **Fail closed (AU-5).** An :class:`AuditWriteError` from the
  audit log is never swallowed by this layer: the request is
  answered exactly 500 ``{"error": "audit write failed"}`` and the
  operation does not proceed.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .errors import (
    AuditWriteError,
    CloudInfraError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "dana": "auditor",
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
    max_failures = 3
    lockout_seconds = 300
    # Per-username consecutive-authentication-failure state (AC-7):
    # name -> {"failures": int, "locked_until": float | None}.
    auth_state = {}
    auth_lock = threading.Lock()
    server_version = "CloudInfra/0.1"
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
        """Return the User, or send the error and return None.

        AC-7 [L3]: consecutive authentication failures are counted
        per username; at ``max_failures`` the username locks for
        ``lockout_seconds`` and attempts during the lock -- even
        with the correct role -- are refused 403 and audited
        ``auth:locked``. A successful authentication resets the
        counter; an expired lock clears itself. Unlocked failures
        are answered 401 and audited as denied, as at founding.
        """
        name = self.headers.get("X-User")
        role = self.headers.get("X-Role")
        if name:
            with self.auth_lock:
                state = self.auth_state.get(name)
                locked_until = state["locked_until"] if state else None
                if locked_until is not None \
                        and time.monotonic() >= locked_until:
                    # Lock expired: clear it before judging.
                    self.auth_state.pop(name, None)
                    locked_until = None
            if locked_until is not None:
                self._audit(name, "auth:locked", target)
                self._error(403, "account locked: too many failed logons")
                return None
        if not name or self.users.get(name) is None or self.users.get(name) != role:
            if name:
                with self.auth_lock:
                    state = self.auth_state.setdefault(
                        name, {"failures": 0, "locked_until": None})
                    state["failures"] += 1
                    if state["failures"] >= self.max_failures:
                        state["locked_until"] = (
                            time.monotonic() + self.lockout_seconds)
            self._audit_denied(name or "anonymous", action, target)
            self._error(401, "unauthorized")
            return None
        with self.auth_lock:
            self.auth_state.pop(name, None)  # Success resets the counter.
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
            self._dispatch_inner(method, parts, params, action, target)
        except AuditWriteError:
            # AU-5 fail closed [L3]: a failed audit write (including
            # one raised while recording a denied attempt) means the
            # operation does not proceed; the answer is exactly 500.
            self._error(500, "audit write failed")

    def _dispatch_inner(self, method, parts, params, action, target):
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
        except AuditWriteError:
            raise  # AU-5 [L3]: handled by _dispatch as exactly 500.
        except CloudInfraError as exc:
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

        if parts == ["audit", "verify"] and method == "GET":
            # AU-9 [L3]: report the hash-chain verification result.
            # The count is read before this read's own audit entry
            # is recorded, so it is the pre-request trail length.
            require(user, "audit_read")
            if self.audit is not None:
                ok, first_bad = self.audit.verify_chain()
                count = len(self.audit.entries())
            else:
                ok, first_bad, count = True, None, 0
            self._audit(user.name, "audit_read", "audit/verify")
            return 200, {"ok": ok, "entries": count,
                         "first_bad_index": first_bad}

        if parts == ["audit"] and method == "GET":
            require(user, "audit_read")
            # AU-7 [L3]: optional actor/action/target/since/until
            # query parameters reduce the trail via AuditLog.query;
            # with no parameters the full trail is returned in the
            # founding shape.
            filters = {key: _first_param(params, key) for key in
                       ("actor", "action", "target", "since", "until")}
            if self.audit is not None and any(
                    value is not None for value in filters.values()):
                entries = self.audit.query(**filters)
                payload = {"entries": entries, "count": len(entries)}
                self._audit(user.name, "audit_read", "audit")
            else:
                # Founding order: the read is recorded before the
                # trail is read back, so the response includes this
                # read's own audit_read entry.
                self._audit(user.name, "audit_read", "audit")
                payload = {"entries": self.audit.entries() if self.audit else []}
            return 200, payload

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

        org = parts[1] if len(parts) >= 2 and parts[0] == "organizations" else None
        resource = parts[2] if len(parts) >= 3 and org else None

        if resource == "tenancies" and len(parts) == 3 and method == "POST":
            tenancy = store.create_tenancy(
                org, body.get("tenancy_ref"), body.get("label"),
                body.get("hosting_model"), user,
                provider_id=body.get("provider_id"))
            return 201, tenancy
        if resource == "tenancies" and len(parts) == 3 and method == "GET":
            return 200, {"tenancies": store.list_tenancies(org, user)}
        if resource == "tenancies" and len(parts) == 4 and method == "GET":
            return 200, store.get_tenancy(org, parts[3], user)

        if resource == "environments" and len(parts) == 3 and method == "POST":
            environment = store.create_environment(
                org, body.get("environment_ref"), body.get("label"), user,
                tenancy_id=body.get("tenancy_id"),
                residency_label=body.get("residency_label"))
            return 201, environment
        if resource == "environments" and len(parts) == 3 and method == "GET":
            return 200, {"environments": store.list_environments(org, user)}
        if resource == "environments" and len(parts) == 4 and method == "GET":
            return 200, store.get_environment(org, parts[3], user)
        if resource == "environments" and len(parts) == 5 \
                and parts[4] == "status" and method == "POST":
            return 200, store.set_environment_status(
                org, parts[3], body.get("status"), user)

        if resource == "providers" and len(parts) == 3 and method == "POST":
            provider = store.register_provider(
                org, body.get("provider_ref"), body.get("label"), user)
            return 201, provider
        if resource == "providers" and len(parts) == 3 and method == "GET":
            return 200, {"providers": store.list_providers(org, user)}
        if resource == "providers" and len(parts) == 4 and method == "GET":
            return 200, store.get_provider(org, parts[3], user)

        if resource == "deployments" and len(parts) == 3 and method == "POST":
            deployment = store.create_deployment(
                org, body.get("tenancy_id"), body.get("deployment_ref"),
                body.get("workload_ref"), user,
                environment_id=body.get("environment_id"),
                template_id=body.get("template_id"),
                encryption_label=body.get("encryption_label"))
            return 201, deployment
        if resource == "deployments" and len(parts) == 3 and method == "GET":
            return 200, {"deployments": store.list_deployments(
                org, user, tenancy_id=_first_param(params, "tenancy_id"))}
        if resource == "deployments" and len(parts) == 4 and method == "GET":
            return 200, store.get_deployment(org, parts[3], user)
        if resource == "deployments" and len(parts) == 5 \
                and parts[4] == "activate" and method == "POST":
            return 200, store.activate_deployment(org, parts[3], user)
        if resource == "deployments" and len(parts) == 5 \
                and parts[4] == "stop" and method == "POST":
            return 200, store.stop_deployment(org, parts[3], user)

        if resource == "templates" and len(parts) == 3 and method == "POST":
            template = store.register_template(
                org, body.get("template_ref"), body.get("label"),
                body.get("settings_text"), user)
            return 201, template
        if resource == "templates" and len(parts) == 3 and method == "GET":
            return 200, {"templates": store.list_templates(org, user)}
        if resource == "templates" and len(parts) == 4 and method == "GET":
            return 200, store.get_template(org, parts[3], user)

        if resource == "monitors" and len(parts) == 3 and method == "POST":
            monitor = store.register_monitor(
                org, body.get("monitor_ref"), body.get("kind"),
                body.get("target_ref"), body.get("label"), user)
            return 201, monitor
        if resource == "monitors" and len(parts) == 3 and method == "GET":
            return 200, {"monitors": store.list_monitors(org, user)}
        if resource == "monitors" and len(parts) == 4 and method == "GET":
            return 200, store.get_monitor(org, parts[3], user)

        if resource == "security-services" and len(parts) == 3 and method == "POST":
            service = store.register_security_service(
                org, body.get("service_ref"), body.get("kind"),
                body.get("target_ref"), body.get("label"), user)
            return 201, service
        if resource == "security-services" and len(parts) == 3 and method == "GET":
            return 200, {"security_services": store.list_security_services(org, user)}
        if resource == "security-services" and len(parts) == 4 and method == "GET":
            return 200, store.get_security_service(org, parts[3], user)

        if resource == "protection-records" and len(parts) == 3 and method == "POST":
            record = store.record_protection(
                org, body.get("protection_ref"), body.get("kind"),
                body.get("target_ref"), body.get("label"), user,
                occurred_at=body.get("occurred_at"))
            return 201, record
        if resource == "protection-records" and len(parts) == 3 and method == "GET":
            return 200, {"protection_records": store.list_protection_records(org, user)}
        if resource == "protection-records" and len(parts) == 4 and method == "GET":
            return 200, store.get_protection_record(org, parts[3], user)

        if resource == "identity-configs" and len(parts) == 3 and method == "POST":
            config = store.register_identity_config(
                org, body.get("identity_ref"), body.get("kind"),
                body.get("label"), user, provider_ref=body.get("provider_ref"))
            return 201, config
        if resource == "identity-configs" and len(parts) == 3 and method == "GET":
            return 200, {"identity_configs": store.list_identity_configs(org, user)}
        if resource == "identity-configs" and len(parts) == 4 and method == "GET":
            return 200, store.get_identity_config(org, parts[3], user)

        if resource == "operations-tasks" and len(parts) == 3 and method == "POST":
            task = store.create_operations_task(
                org, body.get("task_ref"), body.get("kind"),
                body.get("target_ref"), body.get("label"),
                body.get("due_at"), user)
            return 201, task
        if resource == "operations-tasks" and len(parts) == 3 and method == "GET":
            return 200, {"operations_tasks": store.list_operations_tasks(
                org, user, at=_first_param(params, "at"))}
        if resource == "operations-tasks" and len(parts) == 4 and method == "GET":
            return 200, store.get_operations_task(
                org, parts[3], user, at=_first_param(params, "at"))
        if resource == "operations-tasks" and len(parts) == 5 \
                and parts[4] == "status" and method == "POST":
            return 200, store.set_operations_task_status(
                org, parts[3], body.get("status"), user)

        if resource == "accounts" and len(parts) == 3 and method == "POST":
            account = store.open_account(
                org, body.get("account_ref"), body.get("label"), user)
            return 201, account
        if resource == "accounts" and len(parts) == 3 and method == "GET":
            return 200, {"accounts": store.list_accounts(org, user)}
        if resource == "accounts" and len(parts) == 4 and method == "GET":
            return 200, store.get_account(org, parts[3], user)
        if resource == "accounts" and len(parts) == 5 \
                and parts[4] == "close" and method == "POST":
            return 200, store.close_account(org, parts[3], user)
        if resource == "accounts" and len(parts) == 5 \
                and parts[4] == "utilization" and method == "POST":
            record = store.record_utilization(
                org, parts[3], body.get("period"), body.get("units"), user)
            return 201, record
        if resource == "accounts" and len(parts) == 5 \
                and parts[4] == "utilization" and method == "GET":
            return 200, {"utilization": store.list_utilization(
                org, user, account_id=parts[3])}

        if resource == "recommendations" and len(parts) == 3 and method == "POST":
            record = store.record_recommendation(
                org, body.get("recommendation_ref"), body.get("kind"),
                body.get("target_ref"), body.get("label"), user,
                detail=body.get("detail"))
            return 201, record
        if resource == "recommendations" and len(parts) == 3 and method == "GET":
            return 200, {"recommendations": store.list_recommendations(org, user)}
        if resource == "recommendations" and len(parts) == 4 and method == "GET":
            return 200, store.get_recommendation(org, parts[3], user)

        if resource == "report" and len(parts) == 3 and method == "GET":
            return 200, store.org_report(org, user, at=_first_param(params, "at"))
        if resource == "search" and len(parts) == 3 and method == "GET":
            return 200, store.search(org, _first_param(params, "q") or "", user)

        raise NotFoundError("no such route: %s /%s" % (method, "/".join(parts)))


def make_server(host, port, store, audit, users, max_failures=3,
                lockout_seconds=300):
    """Build (but do not start) the cloudinfra HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler [L3]; the
    failure state is scoped to this server instance.
    """
    handler = type("CloudInfraHandler", (_Handler,), {})
    handler.store = store
    handler.audit = audit
    handler.users = dict(users)
    handler.max_failures = max_failures
    handler.lockout_seconds = lockout_seconds
    handler.auth_state = {}
    handler.auth_lock = threading.Lock()
    return ThreadingHTTPServer((host, port), handler)
