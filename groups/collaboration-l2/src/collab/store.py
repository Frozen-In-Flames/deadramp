"""Collaboration store: workspaces, channels, messages, files, events,
presence, boards, search, and notifications.

Clean-room implementation of the union spec's implementation contract.

Two boundaries are enforced on every workspace-scoped operation:

1. Membership -- the actor must be a member of the workspace, or hold
   the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`collab.access`).

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing, including the
notification queue. Ids are sequential per object type with fixed
prefixes (``ws-``, ``ch-``, ``msg-``, ``file-``, ``evt-``, ``bd-``,
``card-``, ``ntf-``).

The store records every successful mutation and every search to its
audit log (when one is attached). Reads other than search are not
audited here; denied attempts and audit reads are the HTTP layer's
responsibility, so nothing is recorded twice.
"""

import hashlib
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PRESENCE_STATUSES = ("available", "busy", "dnd", "offline")

_MENTION_RE = re.compile(r"@([A-Za-z0-9_.\-]+)")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _is_admin(actor):
    return getattr(actor, "role", None) == "admin"


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a number" % (what,))
    return value


def _parse_iso_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    return parsed


class CollabStore:
    """In-memory store for the collaboration service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._workspaces = {}  # id -> workspace dict
        self._workspace_order = []
        self._channels = {}  # id -> channel dict
        self._messages = {}  # id -> message dict
        self._files = {}  # id -> file dict (plus private "content" key)
        self._events = {}  # id -> event dict
        self._boards = {}  # id -> board dict
        self._cards = {}  # id -> card dict
        self._notifications = {}  # id -> notification dict
        self._notification_order = []
        self._presence = {}  # username -> presence dict
        self._counters = {
            "ws": 0,
            "ch": 0,
            "msg": 0,
            "file": 0,
            "evt": 0,
            "bd": 0,
            "card": 0,
            "ntf": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_workspace_record(self, workspace_id):
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("workspace not found: %r" % (workspace_id,))
        return workspace

    def _require_workspace_access(self, workspace_id, actor, action):
        """Return the workspace, enforcing membership then role permission."""
        workspace = self._get_workspace_record(workspace_id)
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        if actor_name(actor) not in workspace["members"] and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r is not a member of workspace %r"
                % (actor_name(actor), workspace_id)
            )
        _maybe_require(actor, action)
        return workspace

    @staticmethod
    def _copy_workspace(workspace):
        copied = dict(workspace)
        copied["members"] = list(workspace["members"])
        return copied

    @staticmethod
    def _copy_file(record, include_content=False):
        copied = {k: v for k, v in record.items() if k != "content"}
        if include_content:
            copied["content"] = record["content"]
        return copied

    @staticmethod
    def _copy_event(event):
        copied = dict(event)
        copied["attendees"] = list(event["attendees"])
        return copied

    def _notify(self, username, kind, workspace_id, ref_id):
        """Create one notification. Callers hold the lock and have
        already validated the triggering operation in full."""
        notification_id = self._next_id("ntf")
        notification = {
            "id": notification_id,
            "user": username,
            "kind": kind,
            "workspace_id": workspace_id,
            "ref_id": ref_id,
            "created_utc": _utc_now(),
            "read": False,
        }
        self._notifications[notification_id] = notification
        self._notification_order.append(notification_id)
        return notification

    def _get_channel_record(self, workspace_id, channel_id):
        channel = self._channels.get(channel_id)
        if channel is None or channel["workspace_id"] != workspace_id:
            raise NotFoundError("channel not found: %r" % (channel_id,))
        return channel

    def _get_board_record(self, workspace_id, board_id):
        board = self._boards.get(board_id)
        if board is None or board["workspace_id"] != workspace_id:
            raise NotFoundError("board not found: %r" % (board_id,))
        return board

    # -- workspaces ----------------------------------------------------

    def create_workspace(self, name, actor):
        """Create a workspace; the creator is owner and first member."""
        _validate_non_empty(name, "workspace name")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "create_workspace")
        owner = actor_name(actor)
        with self._lock:
            workspace_id = self._next_id("ws")
            workspace = {
                "id": workspace_id,
                "name": name,
                "owner": owner,
                "members": [owner],
                "created_by": owner,
                "created_utc": _utc_now(),
            }
            self._workspaces[workspace_id] = workspace
            self._workspace_order.append(workspace_id)
            self._audit(actor, "workspace_create", workspace_id, details={"name": name})
            return self._copy_workspace(workspace)

    def list_workspaces(self, actor):
        """Return the workspace dicts ``actor`` may see."""
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "read")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            return [
                self._copy_workspace(self._workspaces[ws_id])
                for ws_id in self._workspace_order
                if admin or name in self._workspaces[ws_id]["members"]
            ]

    def get_workspace(self, workspace_id, actor):
        """Return one workspace dict visible to ``actor``."""
        with self._lock:
            workspace = self._require_workspace_access(workspace_id, actor, "read")
            return self._copy_workspace(workspace)

    def add_member(self, workspace_id, username, actor):
        """Add ``username`` to a workspace. Owner or platform admin only."""
        _validate_non_empty(username, "username")
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        with self._lock:
            workspace = self._get_workspace_record(workspace_id)
            if workspace["owner"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: only the workspace owner or a platform "
                    "admin may add members to workspace %r" % (workspace_id,)
                )
            if username in workspace["members"]:
                raise ValidationError(
                    "user %r is already a member of workspace %r" % (username, workspace_id)
                )
            workspace["members"].append(username)
            self._audit(
                actor, "member_add", workspace_id, details={"username": username}
            )
            return self._copy_workspace(workspace)

    # -- channels and messages ------------------------------------------

    def create_channel(self, workspace_id, name, actor):
        """Create a channel inside a workspace."""
        _validate_non_empty(name, "channel name")
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "post")
            channel_id = self._next_id("ch")
            channel = {
                "id": channel_id,
                "workspace_id": workspace_id,
                "name": name,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._channels[channel_id] = channel
            self._audit(actor, "channel_create", channel_id, details={"name": name})
            return dict(channel)

    def list_channels(self, workspace_id, actor):
        """Return the channels of a workspace, in creation order."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            return [
                dict(channel)
                for channel in self._channels.values()
                if channel["workspace_id"] == workspace_id
            ]

    def post_message(self, workspace_id, channel_id, text, actor, parent_id=None):
        """Post a message to a channel, notifying mentioned members."""
        _validate_non_empty(text, "message text")
        if parent_id is not None and not isinstance(parent_id, str):
            raise ValidationError("parent_id must be a message id string")
        with self._lock:
            workspace = self._require_workspace_access(workspace_id, actor, "post")
            self._get_channel_record(workspace_id, channel_id)
            if parent_id is not None:
                parent = self._messages.get(parent_id)
                if (
                    parent is None
                    or parent["channel_id"] != channel_id
                    or parent["workspace_id"] != workspace_id
                ):
                    raise ValidationError(
                        "parent_id must name a message in the same channel: %r"
                        % (parent_id,)
                    )
            author = actor_name(actor)
            message_id = self._next_id("msg")
            message = {
                "id": message_id,
                "workspace_id": workspace_id,
                "channel_id": channel_id,
                "author": author,
                "text": text,
                "parent_id": parent_id,
                "created_utc": _utc_now(),
            }
            self._messages[message_id] = message
            mentioned = []
            for token in _MENTION_RE.findall(text):
                if (
                    token in workspace["members"]
                    and token != author
                    and token not in mentioned
                ):
                    mentioned.append(token)
            for username in mentioned:
                self._notify(username, "mention", workspace_id, message_id)
            self._audit(actor, "message_post", message_id, details={"channel_id": channel_id})
            return dict(message)

    def list_messages(self, workspace_id, channel_id, actor, limit=None):
        """Return a channel's messages, chronological, optionally limited
        to the most recent ``limit`` messages."""
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValidationError("limit must be a non-negative integer")
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            self._get_channel_record(workspace_id, channel_id)
            messages = [
                dict(message)
                for message in self._messages.values()
                if message["workspace_id"] == workspace_id
                and message["channel_id"] == channel_id
            ]
            if limit is not None:
                messages = messages[-limit:] if limit > 0 else []
            return messages

    def get_message(self, workspace_id, message_id, actor):
        """Return one message dict from a workspace."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            message = self._messages.get(message_id)
            if message is None or message["workspace_id"] != workspace_id:
                raise NotFoundError("message not found: %r" % (message_id,))
            return dict(message)

    # -- files -----------------------------------------------------------

    def share_file(self, workspace_id, name, content, actor, content_type="text/plain"):
        """Share ``content`` (a str, stored as UTF-8) into a workspace.

        Re-sharing the same name in the same workspace creates the next
        version. Every other workspace member is notified.
        """
        _validate_non_empty(name, "file name")
        if not isinstance(content, str):
            raise ValidationError("file content must be a string")
        _validate_non_empty(content_type, "content_type")
        with self._lock:
            workspace = self._require_workspace_access(workspace_id, actor, "share")
            encoded = content.encode("utf-8")
            version = 1 + sum(
                1
                for record in self._files.values()
                if record["workspace_id"] == workspace_id and record["name"] == name
            )
            file_id = self._next_id("file")
            record = {
                "id": file_id,
                "workspace_id": workspace_id,
                "name": name,
                "version": version,
                "size_bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "content_type": content_type,
                "shared_by": actor_name(actor),
                "created_utc": _utc_now(),
                "content": content,
            }
            self._files[file_id] = record
            for username in workspace["members"]:
                if username != actor_name(actor):
                    self._notify(username, "file_share", workspace_id, file_id)
            self._audit(
                actor, "file_share", file_id, details={"name": name, "version": version}
            )
            return self._copy_file(record)

    def list_files(self, workspace_id, actor):
        """Return a workspace's file dicts (without content), in share order."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            return [
                self._copy_file(record)
                for record in self._files.values()
                if record["workspace_id"] == workspace_id
            ]

    def get_file(self, workspace_id, file_id, actor):
        """Return one file dict, including its ``content``."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            record = self._files.get(file_id)
            if record is None or record["workspace_id"] != workspace_id:
                raise NotFoundError("file not found: %r" % (file_id,))
            return self._copy_file(record, include_content=True)

    # -- events ------------------------------------------------------------

    def create_event(self, workspace_id, title, start, end, attendees, actor, location=""):
        """Create a workspace event; member attendees are notified."""
        _validate_non_empty(title, "event title")
        if attendees is None:
            attendees = []
        if not isinstance(attendees, (list, tuple)) or any(
            not isinstance(a, str) for a in attendees
        ):
            raise ValidationError("attendees must be a list of usernames")
        if not isinstance(location, str):
            raise ValidationError("location must be a string")
        start_dt = _parse_iso_datetime(start, "start")
        end_dt = _parse_iso_datetime(end, "end")
        try:
            in_order = end_dt > start_dt
        except TypeError as exc:
            raise ValidationError("start and end must be comparable datetimes") from exc
        if not in_order:
            raise ValidationError("end must be after start")
        attendees = list(attendees)
        with self._lock:
            workspace = self._require_workspace_access(workspace_id, actor, "schedule")
            event_id = self._next_id("evt")
            event = {
                "id": event_id,
                "workspace_id": workspace_id,
                "title": title,
                "start": start,
                "end": end,
                "location": location,
                "attendees": attendees,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._events[event_id] = event
            notified = []
            for username in attendees:
                if (
                    username in workspace["members"]
                    and username != actor_name(actor)
                    and username not in notified
                ):
                    notified.append(username)
                    self._notify(username, "event_invite", workspace_id, event_id)
            self._audit(actor, "event_create", event_id, details={"title": title})
            return self._copy_event(event)

    def list_events(self, workspace_id, actor):
        """Return a workspace's events, in creation order."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            return [
                self._copy_event(event)
                for event in self._events.values()
                if event["workspace_id"] == workspace_id
            ]

    # -- presence ------------------------------------------------------------

    def set_presence(self, username, status, actor, note=""):
        """Set a user's presence. The user themself, or a platform admin."""
        _validate_non_empty(username, "username")
        if status not in PRESENCE_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(PRESENCE_STATUSES),)
            )
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        if actor_name(actor) != username and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r may not set presence for %r"
                % (actor_name(actor), username)
            )
        with self._lock:
            presence = {
                "user": username,
                "status": status,
                "note": note,
                "updated_utc": _utc_now(),
            }
            self._presence[username] = presence
            self._audit(actor, "presence_set", username, details={"status": status})
            return dict(presence)

    def get_presence(self, username):
        """Return a user's presence dict, or raise NotFoundError."""
        with self._lock:
            presence = self._presence.get(username)
            if presence is None:
                raise NotFoundError("presence not found for user: %r" % (username,))
            return dict(presence)

    # -- boards and cards ------------------------------------------------------

    def create_board(self, workspace_id, name, actor):
        """Create a board inside a workspace."""
        _validate_non_empty(name, "board name")
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "board_edit")
            board_id = self._next_id("bd")
            board = {
                "id": board_id,
                "workspace_id": workspace_id,
                "name": name,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._boards[board_id] = board
            self._audit(actor, "board_create", board_id, details={"name": name})
            return dict(board)

    def list_boards(self, workspace_id, actor):
        """Return a workspace's boards, in creation order."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            return [
                dict(board)
                for board in self._boards.values()
                if board["workspace_id"] == workspace_id
            ]

    def add_card(self, workspace_id, board_id, text, x, y, actor):
        """Add a positioned text card to a board."""
        _validate_non_empty(text, "card text")
        _validate_number(x, "x")
        _validate_number(y, "y")
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "board_edit")
            self._get_board_record(workspace_id, board_id)
            card_id = self._next_id("card")
            card = {
                "id": card_id,
                "board_id": board_id,
                "workspace_id": workspace_id,
                "text": text,
                "x": x,
                "y": y,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cards[card_id] = card
            self._audit(actor, "card_add", card_id, details={"board_id": board_id})
            return dict(card)

    def move_card(self, workspace_id, board_id, card_id, x, y, actor):
        """Move a card to a new x/y position."""
        _validate_number(x, "x")
        _validate_number(y, "y")
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "board_edit")
            self._get_board_record(workspace_id, board_id)
            card = self._cards.get(card_id)
            if (
                card is None
                or card["board_id"] != board_id
                or card["workspace_id"] != workspace_id
            ):
                raise NotFoundError("card not found: %r" % (card_id,))
            card["x"] = x
            card["y"] = y
            self._audit(actor, "card_move", card_id, details={"board_id": board_id})
            return dict(card)

    def list_cards(self, workspace_id, board_id, actor):
        """Return a board's cards, in creation order."""
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            self._get_board_record(workspace_id, board_id)
            return [
                dict(card)
                for card in self._cards.values()
                if card["workspace_id"] == workspace_id and card["board_id"] == board_id
            ]

    # -- search ------------------------------------------------------------------

    def search(self, workspace_id, query_text, actor):
        """Literal case-insensitive substring search within one workspace."""
        if not isinstance(query_text, str):
            raise ValidationError("query text must be a string")
        needle = query_text.lower()
        with self._lock:
            self._require_workspace_access(workspace_id, actor, "read")
            result = {
                "messages": [
                    dict(message)
                    for message in self._messages.values()
                    if message["workspace_id"] == workspace_id
                    and needle in message["text"].lower()
                ],
                "files": [
                    self._copy_file(record)
                    for record in self._files.values()
                    if record["workspace_id"] == workspace_id
                    and needle in record["name"].lower()
                ],
                "events": [
                    self._copy_event(event)
                    for event in self._events.values()
                    if event["workspace_id"] == workspace_id
                    and needle in event["title"].lower()
                ],
                "cards": [
                    dict(card)
                    for card in self._cards.values()
                    if card["workspace_id"] == workspace_id
                    and needle in card["text"].lower()
                ],
            }
            self._audit(actor, "search", workspace_id, details={"query": query_text})
            return result

    # -- notifications --------------------------------------------------------------

    def notifications_for(self, username):
        """Return a user's notifications, oldest first."""
        with self._lock:
            return [
                dict(self._notifications[ntf_id])
                for ntf_id in self._notification_order
                if self._notifications[ntf_id]["user"] == username
            ]

    def mark_read(self, notification_id, actor):
        """Mark a notification read. Its user, or a platform admin, only."""
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                raise NotFoundError("notification not found: %r" % (notification_id,))
            if notification["user"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: user %r may not mark notification %r read"
                    % (actor_name(actor), notification_id)
                )
            notification["read"] = True
            self._audit(actor, "notification_read", notification_id)
            return dict(notification)
