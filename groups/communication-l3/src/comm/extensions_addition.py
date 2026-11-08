"""Final GAPS batch, second unit: Remainder Addition extensions
for the Communication L3-adjacent merged build (Group 14).

Covers the 2 OPEN entries of the GAPS.md section "Remainder
Addition -- Communication L3-adjacent (+1 fork)" (inventory
idx 658-659), the gaps registered by the GovSlack addition
(ADDENDUM.md section 5):

- idx 658 (drafted stub-engine, closes reference): an app
  integration & connector platform. Ships as connector definition
  records plus reported exchange records, every record labeled
  ``reference_stub: True`` and ``reference_transport: True``; no
  third-party tool is connected, nothing is synced, and no
  payload is held in any field shape.
- idx 659 (drafted build-extension, closes built in records
  form): a persistent channel / workspace collaboration surface
  -- channels as persistent team rooms, distinct from the core's
  delivery-channel configuration records (``ch-``). Ships as
  room records, membership records binding core contacts, and
  activity records binding core messages by id only. What is
  built is the registry / membership / activity records surface;
  the workspace substrate proper (documents, files, canvas --
  the Collaboration groups' builds), real-time transport, and
  message content are stated absent on every record.

Design follows the first batch unit (``comm.extensions``) and
the core's doctrines:

- Wrapper around :class:`CommStore`; all existing modules,
  including ``extensions.py``, are byte-identical. Core records
  are read through the core store's public API only.
- RBAC through :mod:`comm.access`, checked before any state
  change or id allocation; denied attempts audited with a
  ``:denied`` suffix; successful mutations audited with an
  ``exta_`` prefix.
- Fail closed (AU-5): audit-before-commit; an audit write
  failure leaves the addition store unchanged, no id consumed.
- Opaque ``*_ref`` strings and core record ids only. No record
  shape can hold message content, a payload, or a document: the
  signatures accept no such parameter (a ``content=`` /
  ``body=`` / ``payload=`` / ``document=`` call raises
  ``TypeError``), and tests pin exact key sets plus a recursive
  no-content scan.
- Derived values are derived at read and never stored: a
  connector's current outcome and reported-records total, a
  room's member list/count and current activity. Stored records
  carry no derived key; tests pin that.
- Nothing is sent or transmitted: ``sent_here`` /
  ``transmitted_here`` are False on every surface that could be
  mistaken for a sending path.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CONNECTOR_KINDS = (
    "app_integration",
    "api_connector",
    "webhook_connector",
    "data_sync",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % what)
    return value


def _latest_label(records, key):
    """THE addition seam (fresh negative control): the current
    reported label of an append-only record stream is its LATEST
    record's label. Reading the earliest record instead would
    silently resurrect superseded outcomes on every derived view
    while leaving the stored shapes intact. Mutating this seam
    must fail the suite."""
    if not records:
        return None
    return records[-1][key]


class CommExtensionsAddition:
    """Second batch extension surface wrapping a CommStore."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.RLock()
        self._counters = {}
        self._connectors = {}
        self._exchanges = {}
        self._rooms = {}
        self._memberships = {}
        self._activities = {}

    # -- plumbing ---------------------------------------------------

    def _require(self, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                if self.audit is not None:
                    self.audit.record(
                        actor_name(actor), "exta_%s:denied" % action, "extensions_addition"
                    )
                raise

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), "exta_" + action, target, details=details)

    def _commit(self, actor, action, prefix, table, record):
        n = self._counters.get(prefix, 0) + 1
        record["id"] = "%s-%d" % (prefix, n)
        self._audit(actor, action, record["id"])
        self._counters[prefix] = n
        table[record["id"]] = record
        return dict(record)

    def _get(self, table, obj_id, what):
        rec = table.get(obj_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return rec

    def _base(self, actor):
        return {"created_by": actor_name(actor), "created_utc": _utc_now()}

    # -- 658 APP INTEGRATION & CONNECTOR PLATFORM (reference) -------

    def record_connector_definition(self, connector_ref, label, connector_kind, actor):
        """Connector definition record. The third-party tool is
        named only by an opaque ref and a verbatim label; no
        connection is opened, no credential is held, and no API
        is called (PLATFORM-LAYER: integration transport is an
        engine over external systems, shipped labeled)."""
        self._require(actor, "message_compose")
        _non_empty(connector_ref, "connector_ref")
        _non_empty(label, "label")
        if connector_kind not in CONNECTOR_KINDS:
            raise ValidationError(
                "connector_kind must be one of %s" % (", ".join(CONNECTOR_KINDS),))
        with self._lock:
            for existing in self._connectors.values():
                if existing["connector_ref"] == connector_ref:
                    raise ValidationError(
                        "connector_ref %r is already registered" % (connector_ref,))
            rec = {"connector_ref": connector_ref, "label": label,
                   "connector_kind": connector_kind,
                   "reference_stub": True, "reference_transport": True,
                   "connected_here": False, "synced_here": False,
                   "credentials_held": False, "sent_here": False,
                   "transmitted_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "connector_definition_record",
                                "acn", self._connectors, rec)

    def record_connector_exchange(self, connector_id, outcome_label, actor,
                                  records_reported=None):
        """Reported exchange record: an outcome label reported
        about a sync / connection event that happened elsewhere,
        plus an optional count of records as reported. Nothing is
        imported, exported, or transmitted here."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        if records_reported is not None:
            if isinstance(records_reported, bool) or not isinstance(records_reported, int):
                raise ValidationError("records_reported must be an integer")
            if records_reported < 0:
                raise ValidationError("records_reported must be >= 0")
        with self._lock:
            self._get(self._connectors, connector_id, "connector definition")
            rec = {"connector_id": connector_id, "outcome_label": outcome_label,
                   "records_reported": records_reported,
                   "reference_stub": True, "reference_transport": True,
                   "imported_here": False, "exported_here": False,
                   "transmitted_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "connector_exchange_record",
                                "aex", self._exchanges, rec)

    def connector_view(self, connector_id, actor):
        self._require(actor, "records_read")
        with self._lock:
            definition = dict(self._get(self._connectors, connector_id,
                                        "connector definition"))
            exchanges = [dict(r) for r in self._exchanges.values()
                         if r["connector_id"] == connector_id]
            current = _latest_label(exchanges, "outcome_label")
            total = sum(r["records_reported"] for r in exchanges
                        if r["records_reported"] is not None)
            uncounted = sum(1 for r in exchanges if r["records_reported"] is None)
            return {"definition": definition, "exchanges": exchanges,
                    "exchange_count": len(exchanges),
                    "current_outcome": current if current is not None else "unreported",
                    "total_records_reported": total,
                    "exchanges_without_count": uncounted}

    # -- 659 PERSISTENT ROOM / WORKSPACE SURFACE (built, records) ---

    def create_workspace_room(self, room_ref, label, actor):
        """Persistent team room record: a room is a named,
        persistent registry entry that membership and activity
        bind to -- NOT a core delivery channel (``ch-``), whose
        configuration gates dispatch. No message content is held
        and no real-time transport exists here."""
        self._require(actor, "message_compose")
        _non_empty(room_ref, "room_ref")
        _non_empty(label, "label")
        with self._lock:
            for existing in self._rooms.values():
                if existing["room_ref"] == room_ref:
                    raise ValidationError("room_ref %r is already registered" % (room_ref,))
            rec = {"room_ref": room_ref, "label": label,
                   "records_surface": True,
                   "content_held": False, "real_time_transport_here": False,
                   "sent_here": False, "transmitted_here": False,
                   "workspace_substrate_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "workspace_room_create",
                                "wsr", self._rooms, rec)

    def record_room_membership(self, room_id, contact_id, actor):
        """Membership record binding a core contact to a room.
        The contact is validated through the core store and read
        from it, never supplied as data; a duplicate membership
        is refused and consumes no id."""
        self._require(actor, "group_write")
        with self._lock:
            self._get(self._rooms, room_id, "workspace room")
            self.store.get_contact(contact_id, actor)
            for existing in self._memberships.values():
                if (existing["room_id"] == room_id
                        and existing["contact_id"] == contact_id):
                    raise ValidationError(
                        "contact %r is already a member of room %r" % (contact_id, room_id))
            rec = {"room_id": room_id, "contact_id": contact_id,
                   "content_held": False}
            rec.update(self._base(actor))
            return self._commit(actor, "room_membership_record",
                                "wmb", self._memberships, rec)

    def record_room_activity(self, room_id, activity_label, actor, message_id=None):
        """Room activity record: a verbatim activity label, with
        an optional binding to a core message by id only. The
        message is validated through the core store; its content
        is never copied onto this surface, and recording activity
        sends and dispatches nothing."""
        self._require(actor, "message_compose")
        _non_empty(activity_label, "activity_label")
        with self._lock:
            self._get(self._rooms, room_id, "workspace room")
            if message_id is not None:
                self.store.get_message(message_id, actor)
            rec = {"room_id": room_id, "activity_label": activity_label,
                   "message_id": message_id,
                   "content_held": False, "sent_here": False,
                   "transmitted_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "room_activity_record",
                                "wra", self._activities, rec)

    def workspace_room_view(self, room_id, actor):
        self._require(actor, "records_read")
        with self._lock:
            room = dict(self._get(self._rooms, room_id, "workspace room"))
            memberships = [dict(r) for r in self._memberships.values()
                           if r["room_id"] == room_id]
            activities = [dict(r) for r in self._activities.values()
                          if r["room_id"] == room_id]
            current = _latest_label(activities, "activity_label")
            return {"room": room, "memberships": memberships,
                    "member_contact_ids": [m["contact_id"] for m in memberships],
                    "member_count": len(memberships),
                    "activities": activities,
                    "activity_count": len(activities),
                    "current_activity": current if current is not None else "none_recorded"}

    def addition_report_summary(self, actor):
        """Deterministic counts over the addition surface,
        computed at read on every call; nothing stored, no score."""
        self._require(actor, "records_read")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "connectors": len(self._connectors),
                "connector_exchanges": len(self._exchanges),
                "workspace_rooms": len(self._rooms),
                "room_memberships": len(self._memberships),
                "room_activities": len(self._activities),
            }
