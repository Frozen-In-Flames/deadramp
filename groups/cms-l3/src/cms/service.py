"""HTTP service exposing the content management functions over a JSON REST API.

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

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent) [L3]:

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
  log is never swallowed by the service layer: it propagates to the
  dispatcher, which answers 500, and the operation does not proceed.
"""

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .access import User, require
from .audit import AuditLog
from .errors import (
    AuditWriteError,
    CmsError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

# Demo registry (documented demo identities, not an IdP).
USERS = {
    "alice": "admin",
    "bob": "publisher",
    "carol": "editor",
    "dave": "author",
    "erin": "viewer",
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
    server_version = "CMS/0.1"
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
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["search"]:
            return ("search", "search", ())
        if method == "GET" and parts == ["report"]:
            return ("report", "report_read", ())
        if method == "GET" and parts == ["publishes"]:
            return ("publish_list", "item_read", ())
        if parts and parts[0] == "sites":
            if len(parts) == 1:
                if method == "GET":
                    return ("site_list", "site_read", ())
                if method == "POST":
                    return ("site_create", "site_write", ())
            if len(parts) == 2 and method == "GET":
                return ("site_get", "site_read", (parts[1],))
            if len(parts) == 3 and parts[2] == "sections":
                if method == "GET":
                    return ("section_list", "section_read", (parts[1],))
                if method == "POST":
                    return ("section_create", "section_write", (parts[1],))
        if parts and parts[0] == "types":
            if len(parts) == 1:
                if method == "GET":
                    return ("type_list", "type_read", ())
                if method == "POST":
                    return ("type_create", "type_write", ())
            if len(parts) == 2 and method == "GET":
                return ("type_get", "type_read", (parts[1],))
        if parts and parts[0] == "items":
            if len(parts) == 1:
                if method == "GET":
                    return ("item_list", "item_read", ())
                if method == "POST":
                    return ("item_create", "item_create", ())
            if len(parts) == 2:
                if method == "GET":
                    return ("item_get", "item_read", (parts[1],))
                if method in ("PATCH", "POST"):
                    return ("item_update", "item_edit", (parts[1],))
            if len(parts) == 3:
                if parts[2] == "revisions" and method == "GET":
                    return ("item_revisions", "item_read", (parts[1],))
                if parts[2] == "submit" and method == "POST":
                    return ("item_submit", "item_submit", (parts[1],))
                if parts[2] == "approve" and method == "POST":
                    return ("item_approve", "item_review", (parts[1],))
                if parts[2] == "return" and method == "POST":
                    return ("item_return", "item_review", (parts[1],))
                if parts[2] == "publish" and method == "POST":
                    return ("item_publish", "item_publish", (parts[1],))
                if parts[2] == "archive" and method == "POST":
                    return ("item_archive", "item_archive", (parts[1],))
        if parts and parts[0] == "assets":
            if len(parts) == 1:
                if method == "GET":
                    return ("asset_list", "asset_read", ())
                if method == "POST":
                    return ("asset_create", "asset_write", ())
            if len(parts) == 2 and method == "GET":
                return ("asset_get", "asset_read", (parts[1],))
        if parts and parts[0] == "tags":
            if len(parts) == 1:
                if method == "GET":
                    return ("tag_list", "tag_read", ())
                if method == "POST":
                    return ("tag_create", "tag_write", ())
            if len(parts) == 2 and method == "GET":
                return ("tag_get", "tag_read", (parts[1],))
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
            # AU-5 fail closed: the operation did not proceed.
            self._safe_error(500, "audit write failed")
        except CmsError as exc:
            self._safe_error(400, exc)
        except Exception:
            self._safe_error(500, "internal error")

    def _safe_error(self, status, message):
        try:
            self._error(status, message)
        except Exception:
            pass

    def _execute(self, route, user, ids, parsed):
        store = self.store
        params = parse_qs(parsed.query)
        if route == "audit_verify":
            # Read the count and verify BEFORE appending this request's
            # own audit_read entry, so the answer describes the trail
            # as the caller left it.
            if self.audit is not None:
                count = len(self.audit.entries())
                ok, first_bad = self.audit.verify_chain()
            else:
                count, ok, first_bad = 0, True, None
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(
                200, {"ok": ok, "entries": count, "first_bad_index": first_bad}
            )
            return
        if route == "audit_read":
            filters = {
                key: (params.get(key) or [None])[0]
                for key in ("actor", "action", "target", "since", "until")
            }
            if self.audit is not None and any(
                value is not None for value in filters.values()
            ):
                entries = self.audit.query(**filters)
            elif self.audit is not None:
                entries = self.audit.entries()
            else:
                entries = []
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "search":
            query_text = (params.get("q") or [""])[0]
            self._send_json(200, store.search(user, query_text))
            return
        if route == "report":
            self._send_json(200, store.registry_report(user))
            return
        if route == "publish_list":
            item_id = (params.get("item_id") or [None])[0]
            self._send_json(200, {"publishes": store.list_publish_records(item_id=item_id, actor=user)})
            return
        if route == "site_list":
            self._send_json(200, {"sites": store.list_sites(user)})
            return
        if route == "site_create":
            body = self._read_json_body()
            site = store.create_site(user, body.get("name"), body.get("slug"),
                                     description=body.get("description", ""))
            self._send_json(201, site)
            return
        if route == "site_get":
            self._send_json(200, store.get_site(ids[0], user))
            return
        if route == "section_list":
            self._send_json(200, {"sections": store.list_sections(ids[0], user)})
            return
        if route == "section_create":
            body = self._read_json_body()
            section = store.create_section(user, ids[0], body.get("name"), body.get("slug"),
                                           parent_id=body.get("parent_id"))
            self._send_json(201, section)
            return
        if route == "type_list":
            self._send_json(200, {"types": store.list_types(user)})
            return
        if route == "type_create":
            body = self._read_json_body()
            ctype = store.create_type(user, body.get("name"),
                                      description=body.get("description", ""))
            self._send_json(201, ctype)
            return
        if route == "type_get":
            self._send_json(200, store.get_type(ids[0], user))
            return
        if route == "item_list":
            site_id = (params.get("site_id") or [None])[0]
            status_filter = (params.get("status") or [None])[0]
            now = (params.get("now") or [None])[0]
            self._send_json(200, {"items": store.list_items(site_id=site_id, status=status_filter, actor=user, now=now)})
            return
        if route == "item_create":
            body = self._read_json_body()
            item = store.create_item(
                user, body.get("site_id"), body.get("type_id"), body.get("title"),
                body.get("slug"), body=body.get("body", ""),
                section_id=body.get("section_id"), metadata=body.get("metadata"),
                tag_ids=body.get("tag_ids"),
            )
            self._send_json(201, item)
            return
        if route == "item_get":
            now = (params.get("now") or [None])[0]
            self._send_json(200, store.get_item(ids[0], user, now=now))
            return
        if route == "item_update":
            body = self._read_json_body()
            item = store.update_item(
                user, ids[0], title=body.get("title"), body=body.get("body"),
                metadata=body.get("metadata"), tag_ids=body.get("tag_ids"),
            )
            self._send_json(200, item)
            return
        if route == "item_revisions":
            self._send_json(200, {"revisions": store.list_revisions(ids[0], user)})
            return
        if route == "item_submit":
            self._send_json(200, store.submit_item(user, ids[0]))
            return
        if route == "item_approve":
            self._send_json(200, store.approve_item(user, ids[0]))
            return
        if route == "item_return":
            body = self._read_json_body()
            self._send_json(200, store.return_item(user, ids[0], note=body.get("note", "")))
            return
        if route == "item_publish":
            body = self._read_json_body()
            item = store.publish_item(user, ids[0], publish_at=body.get("publish_at"),
                                      expire_at=body.get("expire_at"))
            self._send_json(200, item)
            return
        if route == "item_archive":
            self._send_json(200, store.archive_item(user, ids[0]))
            return
        if route == "asset_list":
            site_id = (params.get("site_id") or [None])[0]
            self._send_json(200, {"assets": store.list_assets(site_id=site_id, actor=user)})
            return
        if route == "asset_create":
            body = self._read_json_body()
            data = None
            if body.get("data_base64") is not None:
                try:
                    data = base64.b64decode(body["data_base64"], validate=True)
                except Exception as exc:
                    raise ValidationError("data_base64 must be valid base64") from exc
            elif isinstance(body.get("data"), str):
                data = body["data"].encode("utf-8")
            asset = store.register_asset(
                user, body.get("site_id"), body.get("filename"), body.get("kind"),
                body.get("byte_size"), mime_type=body.get("mime_type", ""),
                content_sha256=body.get("content_sha256"), data=data,
            )
            self._send_json(201, asset)
            return
        if route == "asset_get":
            self._send_json(200, store.get_asset(ids[0], user))
            return
        if route == "tag_list":
            self._send_json(200, {"tags": store.list_tags(user)})
            return
        if route == "tag_create":
            body = self._read_json_body()
            tag = store.create_tag(user, body.get("name"), body.get("slug"))
            self._send_json(201, tag)
            return
        if route == "tag_get":
            self._send_json(200, store.get_tag(ids[0], user))
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
    """Create (but do not start) the cms HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler [L3].
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "CmsHandler",
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
