"""HTTP service exposing the collaboration functions over a JSON REST API.

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

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent):

- **Unsuccessful logon lockout (AC-7).** ``make_server`` accepts
  ``max_failures`` / ``lockout_seconds``. Consecutive authentication
  failures are tracked per username; at ``max_failures`` the username
  locks for ``lockout_seconds`` and any further attempt for it -- even
  with the correct role -- is answered 403 and audited with action
  ``"auth:locked"``. A successful authentication resets that user's
  counter; lock expiry lets the user in again.
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
    CollabError,
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
    server_version = "Collab/0.1"
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
                pass  # Auditing must never break the request path.

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
        """Return (route, permission_action, ids) for a known route.

        ``permission_action`` is None only for ``PUT /presence/{user}``:
        any authenticated user may call it and the store enforces
        self-or-admin. Returns (None, None, ()) for unknown routes.
        """
        if method == "GET" and parts == ["health"]:
            return ("health", None, ())
        if method == "GET" and parts == ["audit"]:
            return ("audit_read", "audit_read", ())
        if method == "GET" and parts == ["audit", "verify"]:
            return ("audit_verify", "audit_read", ())
        if method == "GET" and parts == ["notifications"]:
            return ("notifications_list", "read", ())
        if len(parts) == 3 and parts[0] == "notifications" and parts[2] == "read":
            if method == "POST":
                return ("notification_read", "read", (parts[1],))
            return (None, None, ())
        if len(parts) == 2 and parts[0] == "presence":
            if method == "GET":
                return ("presence_get", "read", (parts[1],))
            if method == "PUT":
                return ("presence_put", None, (parts[1],))
            return (None, None, ())
        if parts and parts[0] == "workspaces":
            if len(parts) == 1:
                if method == "GET":
                    return ("workspace_list", "read", ())
                if method == "POST":
                    return ("workspace_create", "create_workspace", ())
            elif len(parts) == 2:
                if method == "GET":
                    return ("workspace_get", "read", (parts[1],))
            elif len(parts) == 3:
                ws_id, sub = parts[1], parts[2]
                if method == "POST" and sub == "members":
                    return ("member_add", "post", (ws_id,))
                if method == "GET" and sub == "channels":
                    return ("channel_list", "read", (ws_id,))
                if method == "POST" and sub == "channels":
                    return ("channel_create", "post", (ws_id,))
                if method == "GET" and sub == "files":
                    return ("file_list", "read", (ws_id,))
                if method == "POST" and sub == "files":
                    return ("file_share", "share", (ws_id,))
                if method == "GET" and sub == "events":
                    return ("event_list", "read", (ws_id,))
                if method == "POST" and sub == "events":
                    return ("event_create", "schedule", (ws_id,))
                if method == "GET" and sub == "boards":
                    return ("board_list", "read", (ws_id,))
                if method == "POST" and sub == "boards":
                    return ("board_create", "board_edit", (ws_id,))
                if method == "GET" and sub == "search":
                    return ("search", "read", (ws_id,))
            elif len(parts) == 4:
                ws_id, sub, item_id = parts[1], parts[2], parts[3]
                if method == "GET" and sub == "files":
                    return ("file_get", "read", (ws_id, item_id))
            elif len(parts) == 5:
                ws_id, sub, item_id, tail = parts[1], parts[2], parts[3], parts[4]
                if sub == "channels" and tail == "messages":
                    if method == "GET":
                        return ("message_list", "read", (ws_id, item_id))
                    if method == "POST":
                        return ("message_post", "post", (ws_id, item_id))
                if sub == "boards" and tail == "cards":
                    if method == "GET":
                        return ("card_list", "read", (ws_id, item_id))
                    if method == "POST":
                        return ("card_add", "board_edit", (ws_id, item_id))
            elif len(parts) == 7:
                ws_id, sub, board_id, tail, card_id, verb = (
                    parts[1],
                    parts[2],
                    parts[3],
                    parts[4],
                    parts[5],
                    parts[6],
                )
                if (
                    method == "POST"
                    and sub == "boards"
                    and tail == "cards"
                    and verb == "move"
                ):
                    return ("card_move", "board_edit", (ws_id, board_id, card_id))
        return (None, None, ())

    # Action names used when auditing a denial for a route whose HTTP
    # permission differs from the operation name (or has none).
    _DENIAL_ACTION = {"presence_put": "presence_set"}

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
        except AuditWriteError:
            self._safe_error(500, "audit write failed")
        except CollabError as exc:
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
            if self.audit is not None:
                ok, first_bad = self.audit.verify_chain()
                count = len(self.audit.entries())
            else:
                ok, first_bad, count = True, None, 0
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(
                200, {"ok": ok, "entries": count, "first_bad_index": first_bad}
            )
            return
        if route == "audit_read":
            params = parse_qs(parsed.query)

            def _first(key):
                values = params.get(key)
                return values[0] if values else None

            actor_filter = _first("actor")
            action_filter = _first("action")
            target_filter = _first("target")
            since = _first("since")
            until = _first("until")
            filters = {}
            if actor_filter is not None:
                filters["actor"] = actor_filter
            if action_filter is not None:
                filters["action"] = action_filter
            if target_filter is not None:
                filters["target"] = target_filter
            if since is not None:
                filters["since"] = since
            if until is not None:
                filters["until"] = until
            if self.audit is None:
                entries = []
            elif filters:
                entries = self.audit.query(**filters)
            else:
                entries = self.audit.entries()
            self._audit(user.name, "audit_read", parsed.path)
            self._send_json(200, {"entries": entries})
            return
        if route == "workspace_list":
            self._send_json(200, {"workspaces": store.list_workspaces(user)})
            return
        if route == "workspace_create":
            body = self._read_json_body()
            workspace = store.create_workspace(body.get("name"), user)
            self._send_json(201, workspace)
            return
        if route == "workspace_get":
            self._send_json(200, store.get_workspace(ids[0], user))
            return
        if route == "member_add":
            body = self._read_json_body()
            workspace = store.add_member(ids[0], body.get("username"), user)
            self._send_json(200, workspace)
            return
        if route == "channel_list":
            self._send_json(200, {"channels": store.list_channels(ids[0], user)})
            return
        if route == "channel_create":
            body = self._read_json_body()
            channel = store.create_channel(ids[0], body.get("name"), user)
            self._send_json(201, channel)
            return
        if route == "message_list":
            params = parse_qs(parsed.query)
            limit = None
            if "limit" in params:
                raw_limit = params["limit"][0]
                try:
                    limit = int(raw_limit)
                except (TypeError, ValueError):
                    raise ValidationError("limit must be an integer")
            messages = store.list_messages(ids[0], ids[1], user, limit=limit)
            self._send_json(200, {"messages": messages})
            return
        if route == "message_post":
            body = self._read_json_body()
            if "text" not in body:
                raise ValidationError("request body is missing 'text'")
            message = store.post_message(
                ids[0], ids[1], body.get("text"), user, parent_id=body.get("parent_id")
            )
            self._send_json(201, message)
            return
        if route == "file_list":
            self._send_json(200, {"files": store.list_files(ids[0], user)})
            return
        if route == "file_share":
            body = self._read_json_body()
            content_type = body.get("content_type", "text/plain")
            if content_type is None:
                content_type = "text/plain"
            record = store.share_file(
                ids[0],
                body.get("name"),
                body.get("content"),
                user,
                content_type=content_type,
            )
            self._send_json(201, record)
            return
        if route == "file_get":
            self._send_json(200, store.get_file(ids[0], ids[1], user))
            return
        if route == "event_list":
            self._send_json(200, {"events": store.list_events(ids[0], user)})
            return
        if route == "event_create":
            body = self._read_json_body()
            location = body.get("location", "")
            if location is None:
                location = ""
            event = store.create_event(
                ids[0],
                body.get("title"),
                body.get("start"),
                body.get("end"),
                body.get("attendees", []),
                user,
                location=location,
            )
            self._send_json(201, event)
            return
        if route == "board_list":
            self._send_json(200, {"boards": store.list_boards(ids[0], user)})
            return
        if route == "board_create":
            body = self._read_json_body()
            board = store.create_board(ids[0], body.get("name"), user)
            self._send_json(201, board)
            return
        if route == "card_list":
            cards = store.list_cards(ids[0], ids[1], user)
            self._send_json(200, {"cards": cards})
            return
        if route == "card_add":
            body = self._read_json_body()
            card = store.add_card(
                ids[0], ids[1], body.get("text"), body.get("x"), body.get("y"), user
            )
            self._send_json(201, card)
            return
        if route == "card_move":
            body = self._read_json_body()
            card = store.move_card(
                ids[0], ids[1], ids[2], body.get("x"), body.get("y"), user
            )
            self._send_json(200, card)
            return
        if route == "search":
            params = parse_qs(parsed.query)
            query_text = (params.get("q") or [""])[0]
            self._send_json(200, store.search(ids[0], query_text, user))
            return
        if route == "presence_get":
            self._send_json(200, store.get_presence(ids[0]))
            return
        if route == "presence_put":
            body = self._read_json_body()
            note = body.get("note", "")
            if note is None:
                note = ""
            presence = store.set_presence(ids[0], body.get("status"), user, note=note)
            self._send_json(200, presence)
            return
        if route == "notifications_list":
            self._send_json(200, {"notifications": store.notifications_for(user.name)})
            return
        if route == "notification_read":
            notification = store.mark_read(ids[0], user)
            self._send_json(200, notification)
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
    """Create (but do not start) the collab HTTP server.

    ``max_failures`` / ``lockout_seconds`` configure the AC-7
    unsuccessful-logon lockout enforced by the handler.
    """
    if audit is None:
        audit = AuditLog()
    handler = type(
        "CollabHandler",
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
