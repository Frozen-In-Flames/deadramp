"""Final GAPS batch extensions for the Communication untiered set.

Clean-room, standard-library-only records extensions for the 9 open
entries of this set's union spec gap list: 5 built as in-substrate
records plus deterministic derivations over the core's own records,
and 4 shipped as labeled reference implementations. See
``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines and this set's tier
discipline:

- This module is a wrapper around :class:`CommStore`; the core
  modules are untouched (byte-identical). Contact, group, template,
  and message existence is always read through the core store's
  public API, never re-implemented.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every record
  and view recursively for one (and for floats and numeric lists).
  The forks' documented control claims stay where the union spec
  put them -- in the spec, as the forks' claims about themselves.
- RBAC goes through :mod:`comm.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Extension record
  writes map to the core ``message_compose`` action (the
  substrate's produce-records write); transport channel
  configuration maps to ``channel_write``, matching the core's
  channel discipline (admin only); reads map to ``records_read``.
  Plain-string actors carry identity but no role, mirroring the
  core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to people, networks, and content are opaque
  ``*_ref`` / ``*_label`` strings or core record ids. No record
  shape in this module can hold message content, shared content,
  audio, or media: content and media exist only as opaque
  references, and there is no parameter that could accept them.
- Current-state values (a contact's presence, a contact's
  accountability status and location) are **derived at read** from
  the append-only report records, never stored: stored report
  records carry no current-state key, and the derivation lives at
  a single named seam (``_latest_report``: the latest recorded
  report wins). The seam is the batch's fresh negative control.
- Nothing here executes against an external system or transmits
  anything. The four stub-engine families ship as labeled
  reference implementations: every record they create carries
  ``reference_stub: True``. Federation exchanges and channel
  dispatch records carry ``reference_transport: True`` with
  ``transmitted_here: False``, in the founding adjudicated form:
  the core's reference transport remains the only transport.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import KNOWN_CHANNEL_KINDS

PRESENCE_STATES = ("available", "busy", "away", "do_not_disturb", "offline")
KNOWN_PRESENCE_STATES = frozenset(PRESENCE_STATES)
ACCOUNTABILITY_STATUSES = ("safe", "injured", "missing", "unaccounted",
                           "evacuated")
KNOWN_ACCOUNTABILITY_STATUSES = frozenset(ACCOUNTABILITY_STATUSES)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _validate_iso(value, what):
    """Validate an ISO-8601 datetime string (mirrors the core)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    return value


def _contact_id_list(value, what):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of contact ids" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        if item not in result:
            result.append(item)
    return result


class CommExtensions:
    """GAPS-batch extension surface over a core CommStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    def _contact(self, contact_id):
        """Return the core contact record (NotFoundError if absent)."""
        return self.store.get_contact(contact_id)

    @staticmethod
    def _latest_report(reports):
        """The current-state derivation seam.

        ``reports`` is one contact's report records in recording
        order (the extension's records are append-only). The
        current state is the **latest recorded** report, or None
        when nothing has been reported. This is the single
        derivation point behind :meth:`presence_view`,
        :meth:`accountability_view`, and :meth:`muster_summary` --
        the batch's fresh negative control mutates it (see
        tests/README.md): reading the earliest report instead
        would resurrect superseded states.
        """
        if not reports:
            return None
        return reports[-1]

    # -- Presence & availability (built) -------------------------------
    # Presence reports are append-only records over a core contact;
    # the stored record holds exactly one reported label. The
    # contact's current presence is derived at read by the seam and
    # is stored nowhere.

    def record_presence(self, contact_id, state, actor, reported_utc=None):
        """Record one presence report for a core contact.

        Action: message_compose (extension write). Audit:
        ext_presence_record.
        """
        self._guard(actor, "message_compose", "ext_presence_record",
                    target=contact_id)
        _one_of(state, KNOWN_PRESENCE_STATES, PRESENCE_STATES,
                "presence state")
        if reported_utc is not None:
            _validate_iso(reported_utc, "reported_utc")
        self._contact(contact_id)
        return self._create(
            "presence_report", "prs",
            {"contact_id": contact_id, "state": state,
             "reported_utc": reported_utc},
            actor, "ext_presence_record")

    def list_presence_reports(self, contact_id, actor=None):
        """Return a contact's presence reports in recording order."""
        self._guard_read(actor, "records_read", "ext_presence_list",
                         target=contact_id)
        self._contact(contact_id)
        return self._list("presence_report", contact_id=contact_id)

    def presence_view(self, contact_id, actor=None):
        """Derive a contact's current presence at read.

        The view is computed from the report records by the seam
        ``_latest_report``; the stored reports carry no derived
        key. With no reports the state reads ``unreported``.
        """
        self._guard_read(actor, "records_read", "ext_presence_view",
                         target=contact_id)
        self._contact(contact_id)
        reports = self._list("presence_report", contact_id=contact_id)
        latest = self._latest_report(reports)
        return {
            "contact_id": contact_id,
            "current_state": latest["state"] if latest else "unreported",
            "report_count": len(reports),
            "last_report_id": latest["id"] if latest else None,
            "derived": True,
        }

    # -- Desktop sharing & collaboration content sharing (built) -------
    # A share record binds a core contact (the sharer) to an opaque
    # content reference and optional core-contact recipients. The
    # content itself is never held and never rendered: there is no
    # parameter that could accept it.

    def record_content_share(self, sharer_contact_id, content_ref, actor,
                             recipient_contact_ids=None):
        """Record one content share. Action: message_compose.

        Audit: ext_share_record.
        """
        self._guard(actor, "message_compose", "ext_share_record",
                    target=sharer_contact_id)
        _non_empty(content_ref, "content_ref")
        recipients = _contact_id_list(recipient_contact_ids,
                                      "recipient_contact_ids")
        self._contact(sharer_contact_id)
        for recipient_id in recipients:
            self._contact(recipient_id)
        return self._create(
            "content_share", "shr",
            {"sharer_contact_id": sharer_contact_id,
             "content_ref": content_ref,
             "recipient_contact_ids": recipients,
             "content_held_here": False,
             "rendered_here": False},
            actor, "ext_share_record")

    def list_content_shares(self, actor=None, sharer_contact_id=None):
        """Return share records, optionally for one sharer."""
        self._guard_read(actor, "records_read", "ext_share_list")
        if sharer_contact_id is not None:
            self._contact(sharer_contact_id)
        return self._list("content_share",
                          sharer_contact_id=sharer_contact_id)

    # -- Personnel accountability & field reporting (built) ------------
    # Status reports are append-only records over a core contact.
    # The location is a caller-reported label, held verbatim as
    # reported: nothing here senses or tracks a location
    # (tracked_here is False on every record). Current status and
    # location derive at read by the seam; muster counts derive at
    # read from the recorded reports -- counts only, no score.

    def record_status_report(self, contact_id, status, location_label,
                             actor, reported_utc=None):
        """Record one accountability/status report for a contact.

        Action: message_compose. Audit: ext_status_report_record.
        """
        self._guard(actor, "message_compose", "ext_status_report_record",
                    target=contact_id)
        _one_of(status, KNOWN_ACCOUNTABILITY_STATUSES,
                ACCOUNTABILITY_STATUSES, "accountability status")
        _non_empty(location_label, "location_label")
        if reported_utc is not None:
            _validate_iso(reported_utc, "reported_utc")
        self._contact(contact_id)
        return self._create(
            "status_report", "acc",
            {"contact_id": contact_id, "status": status,
             "location_label": location_label,
             "location_source": "caller_reported",
             "tracked_here": False,
             "reported_utc": reported_utc},
            actor, "ext_status_report_record")

    def accountability_view(self, contact_id, actor=None):
        """Derive a contact's current accountability state at read."""
        self._guard_read(actor, "records_read", "ext_accountability_view",
                         target=contact_id)
        self._contact(contact_id)
        reports = self._list("status_report", contact_id=contact_id)
        latest = self._latest_report(reports)
        return {
            "contact_id": contact_id,
            "current_status": latest["status"] if latest else "unreported",
            "current_location_label": (
                latest["location_label"] if latest else None),
            "report_count": len(reports),
            "last_report_id": latest["id"] if latest else None,
            "derived": True,
        }

    def muster_summary(self, actor=None, group_id=None):
        """Derive accountability counts at read over recorded reports.

        Scope is every core contact, or one core group's members
        when ``group_id`` is given. Counts only: totals and a
        per-current-status breakdown, each contact's current status
        derived by the seam from its own reports.
        """
        self._guard_read(actor, "records_read", "ext_muster_summary",
                         target=group_id)
        if group_id is not None:
            contacts = self.store.list_group_members(group_id)
        else:
            contacts = self.store.list_contacts()
        by_status = {}
        reported = 0
        for contact in contacts:
            reports = self._list("status_report",
                                 contact_id=contact["id"])
            latest = self._latest_report(reports)
            if latest is None:
                continue
            reported += 1
            by_status[latest["status"]] = by_status.get(
                latest["status"], 0) + 1
        return {
            "scope_group_id": group_id,
            "total_contacts": len(contacts),
            "reported_contacts": reported,
            "unreported_contacts": len(contacts) - reported,
            "by_current_status": by_status,
            "derived": True,
        }

    # -- Inter-organizational federated communication (built) ----------
    # Federation links and exchanges are records: a link names an
    # external network by opaque reference and a peer label; an
    # exchange binds a link to an optional core message and stores
    # the outcome verbatim as reported. No live network is formed
    # and nothing is transmitted (reference transport only).

    def record_federation_link(self, network_ref, peer_label, actor):
        """Record one federation link. Action: message_compose.

        Audit: ext_federation_link_record.
        """
        self._guard(actor, "message_compose",
                    "ext_federation_link_record", target=network_ref)
        _non_empty(network_ref, "network_ref")
        _non_empty(peer_label, "peer_label")
        return self._create(
            "federation_link", "fed",
            {"network_ref": network_ref, "peer_label": peer_label,
             "reference_transport": True,
             "live_network_here": False},
            actor, "ext_federation_link_record")

    def record_federation_exchange(self, link_id, outcome_label, actor,
                                   message_id=None):
        """Record one reported exchange over a federation link.

        Action: message_compose. Audit: ext_federation_exchange_record.
        """
        self._guard(actor, "message_compose",
                    "ext_federation_exchange_record", target=link_id)
        _non_empty(outcome_label, "outcome_label")
        self._get("federation_link", link_id)
        if message_id is not None:
            self.store.get_message(message_id)
        return self._create(
            "federation_exchange", "fxg",
            {"link_id": link_id, "message_id": message_id,
             "outcome_label": outcome_label,
             "reference_transport": True,
             "transmitted_here": False},
            actor, "ext_federation_exchange_record")

    def federation_link_view(self, link_id, actor=None):
        """Return a federation link with its exchange count derived."""
        self._guard_read(actor, "records_read", "ext_federation_link_view",
                         target=link_id)
        link = self._fetch("federation_link", link_id)
        exchanges = self._list("federation_exchange", link_id=link_id)
        link["exchange_count"] = len(exchanges)
        link["derived"] = True
        return link

    def list_federation_exchanges(self, link_id, actor=None):
        """Return a link's exchange records in recording order."""
        self._guard_read(actor, "records_read",
                         "ext_federation_exchange_list", target=link_id)
        self._get("federation_link", link_id)
        return self._list("federation_exchange", link_id=link_id)

    # -- Real channel transports (built records surface) ---------------
    # The records surface for channel transports: configuration
    # records (admin-only, matching the core's channel discipline)
    # and dispatch records bound to core messages. Every record
    # carries the founding label: the transport is the core's
    # reference transport, a deterministic stub -- no real channel
    # exists here and nothing is transmitted. See BATCH.md for the
    # adjudication note on this entry's token.

    def configure_transport_channel(self, kind, name, actor):
        """Record one transport channel configuration.

        Action: channel_write (admin only, as in the core).
        Audit: ext_transport_configure.
        """
        self._guard(actor, "channel_write", "ext_transport_configure")
        _one_of(kind, KNOWN_CHANNEL_KINDS,
                tuple(sorted(KNOWN_CHANNEL_KINDS)), "channel kind")
        _non_empty(name, "channel name")
        return self._create(
            "transport_channel", "trc",
            {"kind": kind, "name": name,
             "reference_transport": True,
             "real_channel_here": False,
             "transmitted_here": False},
            actor, "ext_transport_configure")

    def record_channel_dispatch(self, transport_id, message_id, actor):
        """Record one dispatch of a core message over a configured
        transport record. Action: message_compose.

        Audit: ext_channel_dispatch_record.
        """
        self._guard(actor, "message_compose",
                    "ext_channel_dispatch_record", target=transport_id)
        self._get("transport_channel", transport_id)
        self.store.get_message(message_id)
        return self._create(
            "channel_dispatch", "trd",
            {"transport_id": transport_id, "message_id": message_id,
             "reference_transport": True,
             "transmitted_here": False,
             "status": "recorded_reference_only"},
            actor, "ext_channel_dispatch_record")

    def list_transport_channels(self, actor=None):
        """Return transport channel configuration records."""
        self._guard_read(actor, "records_read", "ext_transport_list")
        return self._list("transport_channel")

    # -- Video conferencing & meetings (reference stub) ----------------
    # Session records only: who, when, an opaque title label. No
    # media is carried, connected, or rendered -- there is no
    # parameter that could accept it.

    def record_meeting_session(self, title_label, actor,
                               organizer_contact_id=None,
                               participant_contact_ids=None,
                               scheduled_utc=None):
        """Record one meeting session (reference implementation).

        Action: message_compose. Audit: ext_meeting_session_record.
        """
        self._guard(actor, "message_compose",
                    "ext_meeting_session_record")
        _non_empty(title_label, "title_label")
        participants = _contact_id_list(participant_contact_ids,
                                        "participant_contact_ids")
        if scheduled_utc is not None:
            _validate_iso(scheduled_utc, "scheduled_utc")
        if organizer_contact_id is not None:
            self._contact(organizer_contact_id)
        for participant_id in participants:
            self._contact(participant_id)
        return self._create(
            "meeting_session", "mtg",
            {"title_label": title_label,
             "organizer_contact_id": organizer_contact_id,
             "participant_contact_ids": participants,
             "scheduled_utc": scheduled_utc,
             "reference_stub": True,
             "media_here": False,
             "connected_here": False},
            actor, "ext_meeting_session_record")

    # -- Voice / telephony (reference stub) -----------------------------
    # Call records only: two core contacts and an outcome label
    # stored verbatim as reported. No call is placed or connected.

    def record_call(self, caller_contact_id, callee_contact_id,
                    outcome_label, actor):
        """Record one call outcome (reference implementation).

        Action: message_compose. Audit: ext_call_record.
        """
        self._guard(actor, "message_compose", "ext_call_record",
                    target=caller_contact_id)
        _non_empty(outcome_label, "outcome_label")
        self._contact(caller_contact_id)
        self._contact(callee_contact_id)
        return self._create(
            "call_record", "cal",
            {"caller_contact_id": caller_contact_id,
             "callee_contact_id": callee_contact_id,
             "outcome_label": outcome_label,
             "reference_stub": True,
             "connected_here": False,
             "media_here": False},
            actor, "ext_call_record")

    # -- Crisis-communication orchestration (reference stub) ------------
    # Campaign definitions are held as data and dispatch requests
    # are recorded; the registry never executes: defining a campaign
    # and recording requests composes, dispatches, and changes
    # nothing in the core store (pinned by test).

    def define_alert_campaign(self, name, channel_kinds, actor,
                              template_id=None):
        """Define one alert campaign as data (reference impl.).

        Action: message_compose. Audit: ext_campaign_define.
        """
        self._guard(actor, "message_compose", "ext_campaign_define")
        _non_empty(name, "campaign name")
        if not isinstance(channel_kinds, (list, tuple)) or not channel_kinds:
            raise ValidationError("channel_kinds must be a non-empty list")
        kinds = []
        for kind in channel_kinds:
            _one_of(kind, KNOWN_CHANNEL_KINDS,
                    tuple(sorted(KNOWN_CHANNEL_KINDS)), "channel kind")
            if kind not in kinds:
                kinds.append(kind)
        if template_id is not None:
            self.store.get_template(template_id)
        return self._create(
            "alert_campaign", "cmp",
            {"name": name, "channel_kinds": kinds,
             "template_id": template_id,
             "definition_only": True,
             "reference_stub": True,
             "orchestrated_here": False,
             "executed_here": False},
            actor, "ext_campaign_define")

    def record_campaign_dispatch_request(self, campaign_id, actor,
                                         note_label=None):
        """Record one dispatch request against a campaign definition.

        Action: message_compose. Audit: ext_campaign_request_record.
        """
        self._guard(actor, "message_compose",
                    "ext_campaign_request_record", target=campaign_id)
        _string_or_none(note_label, "note_label")
        self._get("alert_campaign", campaign_id)
        return self._create(
            "campaign_request", "cdr",
            {"campaign_id": campaign_id, "note_label": note_label,
             "reference_stub": True,
             "reference_transport": True,
             "dispatched_here": False},
            actor, "ext_campaign_request_record")

    # -- Voicemail & unified messaging (reference stub) -----------------
    # Voicemail records only: a recipient contact, a caller label,
    # and an opaque media reference. No audio is recorded or held --
    # there is no parameter that could accept it.

    def record_voicemail(self, recipient_contact_id, caller_label,
                         media_ref, actor):
        """Record one voicemail (reference implementation).

        Action: message_compose. Audit: ext_voicemail_record.
        """
        self._guard(actor, "message_compose", "ext_voicemail_record",
                    target=recipient_contact_id)
        _non_empty(caller_label, "caller_label")
        _non_empty(media_ref, "media_ref")
        self._contact(recipient_contact_id)
        return self._create(
            "voicemail", "vm",
            {"recipient_contact_id": recipient_contact_id,
             "caller_label": caller_label,
             "media_ref": media_ref,
             "reference_stub": True,
             "recorded_here": False,
             "media_held_here": False},
            actor, "ext_voicemail_record")

    def list_voicemail(self, actor=None, recipient_contact_id=None):
        """Return voicemail records, optionally for one recipient."""
        self._guard_read(actor, "records_read", "ext_voicemail_list")
        if recipient_contact_id is not None:
            self._contact(recipient_contact_id)
        return self._list("voicemail",
                          recipient_contact_id=recipient_contact_id)
