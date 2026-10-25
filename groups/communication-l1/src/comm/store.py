"""Communications store: contacts, groups, channels, templates,
messages, per-recipient deliveries, dispatch, acknowledgements,
and search.

Clean-room implementation of the contract.

Permission convention (mirrors the collaboration group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`comm.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``ct-``, ``grp-``, ``ch-``,
``tpl-``, ``msg-``, ``dlv-``).

The store records every successful mutation and every search to its
audit log (when one is attached).

Reference transport honesty: dispatch does NOT transmit anything over
any real network. The reference transport is a deterministic stub: it
records a delivery locally (status ``delivered`` plus a receipt that
is explicitly labelled ``reference_transport: True``) when an enabled
channel of the delivery's kind exists, and fails the delivery with
``failure_reason='no_enabled_channel'`` when none does. See the group
README's honesty section.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CHANNEL_KINDS = ("email", "sms", "voice", "push")
KNOWN_CHANNEL_KINDS = frozenset(CHANNEL_KINDS)

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role,
    so there is nothing to enforce against; enforcement for those
    happens in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    """For writes: an actor must be present, then _maybe_require."""
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
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
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_now(now, what="now"):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    if isinstance(now, str):
        return _parse_iso_datetime(now, what)
    raise ValidationError("%s must be an ISO-8601 string or datetime" % (what,))


def _render_text(text, variables, what):
    def _sub(match):
        key = match.group(1)
        if key not in variables:
            raise ValidationError("missing variable %r for %s" % (key, what))
        return str(variables[key])

    return _PLACEHOLDER_RE.sub(_sub, text)


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class CommStore:
    """In-memory store for the communications service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._contacts = {}
        self._groups = {}
        self._channels = {}
        self._templates = {}
        self._messages = {}
        self._deliveries = {}
        self._counters = {"ct": 0, "grp": 0, "ch": 0, "tpl": 0, "msg": 0, "dlv": 0}
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _copy_contact(contact):
        copied = dict(contact)
        copied["addresses"] = dict(contact["addresses"])
        return copied

    @staticmethod
    def _copy_group(group):
        copied = dict(group)
        copied["members"] = list(group["members"])
        return copied

    @staticmethod
    def _copy_message(message):
        copied = dict(message)
        copied["skipped_recipients"] = list(message["skipped_recipients"])
        return copied

    @staticmethod
    def _copy_delivery(delivery):
        copied = dict(delivery)
        if isinstance(copied.get("receipt"), dict):
            copied["receipt"] = dict(copied["receipt"])
        return copied

    def _get_contact_record(self, contact_id):
        contact = self._contacts.get(contact_id)
        if contact is None:
            raise NotFoundError("contact not found: %r" % (contact_id,))
        return contact

    def _get_group_record(self, group_id):
        group = self._groups.get(group_id)
        if group is None:
            raise NotFoundError("group not found: %r" % (group_id,))
        return group

    def _get_channel_record(self, channel_id):
        channel = self._channels.get(channel_id)
        if channel is None:
            raise NotFoundError("channel not found: %r" % (channel_id,))
        return channel

    def _get_template_record(self, template_id):
        template = self._templates.get(template_id)
        if template is None:
            raise NotFoundError("template not found: %r" % (template_id,))
        return template

    def _get_message_record(self, message_id):
        message = self._messages.get(message_id)
        if message is None:
            raise NotFoundError("message not found: %r" % (message_id,))
        return message

    def _get_delivery_record(self, delivery_id):
        delivery = self._deliveries.get(delivery_id)
        if delivery is None:
            raise NotFoundError("delivery not found: %r" % (delivery_id,))
        return delivery

    # -- contacts ------------------------------------------------------

    def create_contact(self, name, addresses, actor):
        """Create a contact. Action: contact_write."""
        _require_actor(actor, "contact_write")
        _validate_non_empty(name, "contact name")
        if not isinstance(addresses, dict) or not addresses:
            raise ValidationError("addresses must be a non-empty dict of kind -> address")
        for kind, address in addresses.items():
            if kind not in KNOWN_CHANNEL_KINDS:
                raise ValidationError("unknown channel kind: %r" % (kind,))
            if not isinstance(address, str) or not address.strip():
                raise ValidationError("address for kind %r must be a non-empty string" % (kind,))
        with self._lock:
            contact_id = self._next_id("ct")
            contact = {
                "id": contact_id,
                "name": name,
                "addresses": dict(addresses),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._contacts[contact_id] = contact
            self._audit(actor, "contact_create", contact_id, details={"name": name})
            return self._copy_contact(contact)

    def get_contact(self, contact_id, actor=None):
        """Return one contact. Action: contact_read."""
        _maybe_require(actor, "contact_read")
        with self._lock:
            return self._copy_contact(self._get_contact_record(contact_id))

    def list_contacts(self, actor=None):
        """Return contacts sorted by id. Action: contact_read."""
        _maybe_require(actor, "contact_read")
        with self._lock:
            contacts = sorted(self._contacts.values(), key=lambda c: _id_num(c["id"]))
            return [self._copy_contact(c) for c in contacts]

    # -- groups ----------------------------------------------------------

    def create_group(self, name, actor):
        """Create a contact group. Action: group_write."""
        _require_actor(actor, "group_write")
        _validate_non_empty(name, "group name")
        with self._lock:
            group_id = self._next_id("grp")
            group = {
                "id": group_id,
                "name": name,
                "members": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._groups[group_id] = group
            self._audit(actor, "group_create", group_id, details={"name": name})
            return self._copy_group(group)

    def add_to_group(self, group_id, contact_id, actor):
        """Add a contact to a group. Action: group_write."""
        _require_actor(actor, "group_write")
        with self._lock:
            group = self._get_group_record(group_id)
            self._get_contact_record(contact_id)
            if contact_id in group["members"]:
                raise ValidationError(
                    "contact %r is already a member of group %r" % (contact_id, group_id)
                )
            group["members"].append(contact_id)
            self._audit(actor, "group_add_member", group_id, details={"contact_id": contact_id})
            return self._copy_group(group)

    # Backwards-friendly alias matching the service wording.
    add_member = add_to_group

    def list_groups(self, actor=None):
        """Return groups in creation order. Action: contact_read."""
        _maybe_require(actor, "contact_read")
        with self._lock:
            return [self._copy_group(g) for g in self._groups.values()]

    def get_group(self, group_id, actor=None):
        """Return one group. Action: contact_read."""
        _maybe_require(actor, "contact_read")
        with self._lock:
            return self._copy_group(self._get_group_record(group_id))

    def list_group_members(self, group_id, actor=None):
        """Return the group's member contact dicts. Action: contact_read."""
        _maybe_require(actor, "contact_read")
        with self._lock:
            group = self._get_group_record(group_id)
            return [self._copy_contact(self._contacts[cid]) for cid in group["members"]]

    # -- channels ----------------------------------------------------------

    def create_channel(self, kind, name, actor, enabled=True):
        """Create a channel config. Action: channel_write (admin only)."""
        _require_actor(actor, "channel_write")
        if kind not in KNOWN_CHANNEL_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(CHANNEL_KINDS),))
        _validate_non_empty(name, "channel name")
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            channel_id = self._next_id("ch")
            channel = {
                "id": channel_id,
                "kind": kind,
                "name": name,
                "enabled": enabled,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._channels[channel_id] = channel
            self._audit(actor, "channel_create", channel_id, details={"kind": kind, "name": name})
            return dict(channel)

    def get_channel(self, channel_id, actor=None):
        """Return one channel. Action: channel_read."""
        _maybe_require(actor, "channel_read")
        with self._lock:
            return dict(self._get_channel_record(channel_id))

    def list_channels(self, actor=None):
        """Return channels in creation order. Action: channel_read."""
        _maybe_require(actor, "channel_read")
        with self._lock:
            return [dict(c) for c in self._channels.values()]

    def set_channel_enabled(self, channel_id, enabled, actor):
        """Enable/disable a channel. Action: channel_write (admin only)."""
        _require_actor(actor, "channel_write")
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            channel = self._get_channel_record(channel_id)
            channel["enabled"] = enabled
            self._audit(actor, "channel_set_enabled", channel_id, details={"enabled": enabled})
            return dict(channel)

    # -- templates -----------------------------------------------------------

    def create_template(self, name, subject, body, actor):
        """Create a template. Action: template_write."""
        _require_actor(actor, "template_write")
        _validate_non_empty(name, "template name")
        if not isinstance(subject, str):
            raise ValidationError("subject must be a string")
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        with self._lock:
            template_id = self._next_id("tpl")
            template = {
                "id": template_id,
                "name": name,
                "subject": subject,
                "body": body,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._templates[template_id] = template
            self._audit(actor, "template_create", template_id, details={"name": name})
            return dict(template)

    def get_template(self, template_id, actor=None):
        """Return one template. Action: template_read."""
        _maybe_require(actor, "template_read")
        with self._lock:
            return dict(self._get_template_record(template_id))

    def list_templates(self, actor=None):
        """Return templates in creation order. Action: template_read."""
        _maybe_require(actor, "template_read")
        with self._lock:
            return [dict(t) for t in self._templates.values()]

    def render_template(self, template_id, variables=None, actor=None):
        """Render a template -> (subject, body).

        Every {placeholder} must have a variable; missing variables
        raise ValidationError. Extra variables are ignored.
        Action: template_read.
        """
        _maybe_require(actor, "template_read")
        if variables is None:
            variables = {}
        if not isinstance(variables, dict):
            raise ValidationError("variables must be a dict")
        with self._lock:
            template = self._get_template_record(template_id)
            subject = _render_text(template["subject"], variables, "subject")
            body = _render_text(template["body"], variables, "body")
            return (subject, body)

    # -- messages and deliveries ----------------------------------------------

    def compose_message(self, actor, subject=None, body=None, template_id=None,
                        variables=None, contact_ids=None, group_ids=None,
                        channel_kinds=None, send_at=None, require_ack=False):
        """Compose a message and its per-recipient deliveries.

        Action: message_compose. Validates fully before allocating
        any id: a failed compose persists no message, creates no
        delivery, and consumes no id.
        """
        _require_actor(actor, "message_compose")
        if not isinstance(require_ack, bool):
            raise ValidationError("require_ack must be a bool")
        # Subject / body source.
        if template_id is not None:
            if subject is not None or body is not None:
                raise ValidationError(
                    "subject/body must be None when template_id is given"
                )
            # Render now (raises NotFoundError / ValidationError before ids).
            rendered_subject, rendered_body = self.render_template(
                template_id, variables=variables
            )
            subject, body = rendered_subject, rendered_body
        else:
            if variables is not None:
                # Variables without a template are ignored for rendering,
                # but must still be a dict if supplied.
                if not isinstance(variables, dict):
                    raise ValidationError("variables must be a dict")
            _validate_non_empty(subject, "subject")
            _validate_non_empty(body, "body")
        # send_at validation (no state yet).
        if send_at is not None:
            _parse_iso_datetime(send_at, "send_at")
        # Channel kinds.
        if channel_kinds is None:
            kinds = list(CHANNEL_KINDS)
        else:
            if not isinstance(channel_kinds, (list, tuple)) or not channel_kinds:
                raise ValidationError("channel_kinds must be a non-empty list")
            kinds = []
            for kind in channel_kinds:
                if kind not in KNOWN_CHANNEL_KINDS:
                    raise ValidationError("unknown channel kind: %r" % (kind,))
                if kind not in kinds:
                    kinds.append(kind)
        if contact_ids is None:
            contact_ids = []
        if group_ids is None:
            group_ids = []
        if not isinstance(contact_ids, (list, tuple)):
            raise ValidationError("contact_ids must be a list")
        if not isinstance(group_ids, (list, tuple)):
            raise ValidationError("group_ids must be a list")

        with self._lock:
            # Recipients: union, deduplicated, order-stable.
            recipient_ids = []
            seen = set()
            for cid in contact_ids:
                contact = self._contacts.get(cid)
                if contact is None:
                    raise NotFoundError("contact not found: %r" % (cid,))
                if cid not in seen:
                    seen.add(cid)
                    recipient_ids.append(cid)
            for gid in group_ids:
                group = self._groups.get(gid)
                if group is None:
                    raise NotFoundError("group not found: %r" % (gid,))
                for cid in group["members"]:
                    if cid not in seen:
                        seen.add(cid)
                        recipient_ids.append(cid)
            if not recipient_ids:
                raise ValidationError("message must have at least one recipient")
            # Plan deliveries before allocating any id.
            planned = []  # (contact_id, kind, address)
            skipped = []
            for cid in recipient_ids:
                contact = self._contacts[cid]
                reachable = False
                for kind in kinds:
                    address = contact["addresses"].get(kind)
                    if address is not None:
                        planned.append((cid, kind, address))
                        reachable = True
                if not reachable:
                    skipped.append(cid)
            if not planned:
                raise ValidationError("no recipient is reachable on any selected channel kind")
            # All validation passed -- allocate.
            message_id = self._next_id("msg")
            now = _utc_now()
            message = {
                "id": message_id,
                "subject": subject,
                "body": body,
                "template_id": template_id,
                "require_ack": require_ack,
                "send_at": send_at,
                "created_by": actor_name(actor),
                "created_utc": now,
                "skipped_recipients": skipped,
            }
            self._messages[message_id] = message
            for cid, kind, address in planned:
                delivery_id = self._next_id("dlv")
                delivery = {
                    "id": delivery_id,
                    "message_id": message_id,
                    "contact_id": cid,
                    "channel_kind": kind,
                    "address": address,
                    "status": "queued",
                    "attempts": 0,
                    "receipt": None,
                    "failure_reason": None,
                    "acked_utc": None,
                    "created_utc": now,
                    "updated_utc": now,
                }
                self._deliveries[delivery_id] = delivery
            self._audit(actor, "message_compose", message_id,
                        details={"deliveries": len(planned), "skipped": len(skipped)})
            return self._copy_message(message)

    def get_message(self, message_id, actor=None):
        """Return one message. Action: records_read."""
        _maybe_require(actor, "records_read")
        with self._lock:
            return self._copy_message(self._get_message_record(message_id))

    def list_messages(self, actor=None):
        """Return messages in creation order. Action: records_read."""
        _maybe_require(actor, "records_read")
        with self._lock:
            return [self._copy_message(m) for m in self._messages.values()]

    def get_delivery(self, delivery_id, actor=None):
        """Return one delivery. Action: records_read."""
        _maybe_require(actor, "records_read")
        with self._lock:
            return self._copy_delivery(self._get_delivery_record(delivery_id))

    def list_deliveries(self, message_id=None, actor=None):
        """Return deliveries, optionally for one message.

        Action: records_read.
        """
        _maybe_require(actor, "records_read")
        with self._lock:
            if message_id is not None:
                self._get_message_record(message_id)
            return [
                self._copy_delivery(d)
                for d in self._deliveries.values()
                if message_id is None or d["message_id"] == message_id
            ]

    # -- dispatch ---------------------------------------------------------------

    def _first_enabled_channel(self, kind):
        """First enabled channel config of ``kind``, or None."""
        for channel in self._channels.values():
            if channel["kind"] == kind and channel["enabled"]:
                return channel
        return None

    def _dispatch_deliveries(self, deliveries, actor, now_dt):
        """Dispatch queued deliveries through the reference transport.

        Reference transport (deterministic stub, NOT a real network
        transport): a delivery is marked ``delivered`` with a labelled
        receipt if an enabled channel of its kind exists, otherwise
        ``failed`` with ``failure_reason='no_enabled_channel'``.

        MUTATION DRILL NOTE: the send gate is the condition
        ``if channel is None:`` in this function
        (``CommStore._dispatch_deliveries`` in ``src/comm/store.py``).
        """
        delivered = 0
        failed = 0
        for delivery in deliveries:
            channel = self._first_enabled_channel(delivery["channel_kind"])
            delivery["attempts"] += 1
            delivery["updated_utc"] = _utc_now()
            if channel is None:
                delivery["status"] = "failed"
                delivery["failure_reason"] = "no_enabled_channel"
                delivery["receipt"] = None
                failed += 1
            else:
                delivery["status"] = "delivered"
                delivery["failure_reason"] = None
                delivery["receipt"] = {
                    "transport": "reference",
                    "reference_transport": True,
                    "delivered_utc": _utc_now(),
                }
                delivered += 1
            self._audit(actor, "delivery_dispatch", delivery["id"],
                        details={"message_id": delivery["message_id"],
                                 "status": delivery["status"]})
        return {"dispatched": delivered + failed, "delivered": delivered, "failed": failed}

    def dispatch_due(self, actor, now=None):
        """Dispatch every due queued delivery. Action: dispatch."""
        _require_actor(actor, "dispatch")
        now_dt = _coerce_now(now)
        with self._lock:
            due = []
            for delivery in self._deliveries.values():
                if delivery["status"] != "queued":
                    continue
                message = self._messages[delivery["message_id"]]
                if message["send_at"] is not None:
                    send_dt = _parse_iso_datetime(message["send_at"], "send_at")
                    if send_dt > now_dt:
                        continue
                due.append(delivery)
            return self._dispatch_deliveries(due, actor, now_dt)

    def dispatch_message(self, message_id, actor, now=None):
        """Dispatch one message's queued deliveries. Action: dispatch.

        If the message's send_at is in the future -> ValidationError.
        ``now`` is accepted for deterministic testing; it defaults to
        the current UTC time.
        """
        _require_actor(actor, "dispatch")
        now_dt = _coerce_now(now)
        with self._lock:
            message = self._get_message_record(message_id)
            if message["send_at"] is not None:
                send_dt = _parse_iso_datetime(message["send_at"], "send_at")
                if send_dt > now_dt:
                    raise ValidationError("message %r is not due yet (send_at is in the future)" % (message_id,))
            due = [
                d for d in self._deliveries.values()
                if d["message_id"] == message_id and d["status"] == "queued"
            ]
            return self._dispatch_deliveries(due, actor, now_dt)

    # -- acknowledgement -----------------------------------------------------------

    def acknowledge(self, delivery_id, actor):
        """Acknowledge a delivered delivery. Action: ack_record."""
        _require_actor(actor, "ack_record")
        with self._lock:
            delivery = self._get_delivery_record(delivery_id)
            if delivery["status"] != "delivered":
                raise ValidationError(
                    "delivery %r must be 'delivered' to acknowledge (status is %r)"
                    % (delivery_id, delivery["status"])
                )
            message = self._get_message_record(delivery["message_id"])
            if not message["require_ack"]:
                raise ValidationError(
                    "message %r does not require acknowledgement" % (message["id"],)
                )
            delivery["status"] = "acknowledged"
            delivery["acked_utc"] = _utc_now()
            delivery["updated_utc"] = delivery["acked_utc"]
            self._audit(actor, "delivery_ack", delivery_id,
                        details={"message_id": delivery["message_id"]})
            return self._copy_delivery(delivery)

    def ack_status(self, message_id, actor=None):
        """Acknowledgement summary for a message. Action: records_read."""
        _maybe_require(actor, "records_read")
        with self._lock:
            message = self._get_message_record(message_id)
            deliveries = [
                d for d in self._deliveries.values() if d["message_id"] == message_id
            ]
            acknowledged = sum(1 for d in deliveries if d["status"] == "acknowledged")
            pending = []
            for d in deliveries:
                if d["status"] != "acknowledged" and d["contact_id"] not in pending:
                    pending.append(d["contact_id"])
            return {
                "message_id": message_id,
                "require_ack": message["require_ack"],
                "total": len(deliveries),
                "acknowledged": acknowledged,
                "pending_contact_ids": pending,
            }

    # -- search -----------------------------------------------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search.

        Over contacts (name + address values), messages (subject +
        body), and deliveries (address). Returns
        {contacts, messages, deliveries}. Action: records_read.
        Records a 'search' audit entry.
        """
        _require_actor(actor, "records_read")
        if not isinstance(query, str):
            raise ValidationError("query must be a string")
        needle = query.lower()
        with self._lock:
            result = {
                "contacts": [
                    self._copy_contact(c)
                    for c in self._contacts.values()
                    if needle in c["name"].lower()
                    or any(needle in addr.lower() for addr in c["addresses"].values())
                ],
                "messages": [
                    self._copy_message(m)
                    for m in self._messages.values()
                    if needle in m["subject"].lower() or needle in m["body"].lower()
                ],
                "deliveries": [
                    self._copy_delivery(d)
                    for d in self._deliveries.values()
                    if needle in d["address"].lower()
                ],
            }
            self._audit(actor, "search", "search", details={"query": query})
            return result
