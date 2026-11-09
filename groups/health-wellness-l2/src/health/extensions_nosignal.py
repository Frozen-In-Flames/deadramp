"""Final GAPS batch extensions, THIRD unit -- Health & Wellness
L2 no-signal addition (CirrusMD).

Implements the records and labeled-reference surface for the one
open entry of the GAPS.md section "No-Signal Addition -- Health &
Wellness L2 (CirrusMD, FR2220549818)" (see ``../../BATCH-
NOSIGNAL.md`` for the per-entry disposition):

* idx 968 -- chat-based virtual care channel (CirrusMD): chat
  channel definition records, chat encounter records and
  reported-outcome records, all labeled reference. The fork's
  marketplace listing carried no usable signal; the classified
  function was established from the vendor's own public
  documentation in the no-signal research pass (ADDENDUM section
  7): a chat channel through which a multidisciplinary care team
  delivers physician-first care and guidance. The ADDENDUM's
  core-delta already carries the chat VISIT as a Core 6 activity
  record and care-team guidance / follow-up as Core plans and
  enrollment; what has no records form in the substrate is the
  channel itself -- delivery and routing of a clinical
  conversation -- and the conversation's content. So this surface
  holds records ABOUT the channel and its encounters: no message
  is delivered or routed here, no transcript or message content
  is held in any shape, no clinical decision is made here, and
  reported outcomes are held verbatim, exactly as reported by
  the platform.

Honesty rules carried from the founding build and both prior
batch units, unchanged:

* NO REAL PHI / PII, ever: participants are opaque references;
  no diagnosis, clinical-note, transcript, message-content or
  identifier-shaped field exists anywhere on this surface, and
  no method signature can accept one.
* Chat delivery never happens here: every record states
  ``channel_operated_here: False``, ``messages_delivered_here:
  False`` and ``routed_here: False``, carries
  ``reference_stub: True`` and ``reference_transport: True`` and
  sits in the state ``recorded_reference_only``.
* Clinical decisions never happen here: encounter and report
  records state ``decided_here: False``; outcomes are the
  platform's own labels, held verbatim, never reinterpreted.
* An encounter record may bind to the participant's OWN Core 6
  activity (chat visit) record by id -- never to another
  participant's -- through the ownership seam
  ``_check_chat_activity_belongs``, this unit's
  mutation-verified negative control.
* Derived values are never stored: a channel view's encounter
  count, report count and current (latest reported) outcome
  label are derived at read over the recorded reports.

Tier discipline: this group is L2 / Moderate. The surface uses
the same append-only audit with the distinct ``extn_`` action
prefix, the same four-role permission matrix and the same member
scope as the core. No baseline apparatus is imported from any
other tier, and no new permission is invented.
"""

import copy

from .errors import NotFoundError, ValidationError
from .extensions import (
    _REFERENCE_STATE, _count, _non_empty, _utc_now, _validate_date)
from .extensions_addition import HealthExtensionsAddition

#: Reported outcome labels for a chat encounter, held verbatim.
#: These are the PLATFORM's lifecycle labels for a chat-based
#: care encounter, recorded as reported -- never a clinical
#: judgement made here.
CHAT_OUTCOME_LABELS = (
    "initiated",
    "responded",
    "guidance_provided",
    "follow_up_scheduled",
    "escalated",
    "completed",
)


class HealthExtensionsNoSignal(HealthExtensionsAddition):
    """Third-unit extension surface over the core ``HealthStore``.

    Subclasses the second unit's ``HealthExtensionsAddition``
    (which subclasses the first unit's ``HealthExtensions``), so
    the whole extension surface is reachable from one object.
    Every pre-existing module is untouched; this class adds only
    its own tables, counters and ``extn_``-prefixed audit
    actions.
    """

    def __init__(self, store):
        super().__init__(store)
        self._counters.update({"chc": 0, "che": 0, "chr": 0})
        self._chat_channels = {}
        self._chat_encounters = {}
        self._chat_reports = {}

    # ----------------------------------------------------------
    # Internal helpers (this unit)
    # ----------------------------------------------------------

    def _check_chat_activity_belongs(self, activity, participant_id):
        """Ownership seam: a bound Core activity (the chat visit
        record) must belong to the encounter's participant.

        Without this check a chat encounter could bind to ANOTHER
        participant's Core visit record, attaching this channel's
        records to a visit that is not theirs. This seam is this
        unit's mutation-verified negative control (see
        tests/README.md).
        """
        if activity["participant_id"] != participant_id:
            raise ValidationError(
                "activity %s does not belong to participant %s"
                % (activity["id"], participant_id))

    def _check_channel(self, channel_id):
        channel = self._chat_channels.get(channel_id)
        if channel is None:
            raise NotFoundError("no chat channel with id %s" % channel_id)
        return channel

    def _check_encounter(self, encounter_id):
        encounter = self._chat_encounters.get(encounter_id)
        if encounter is None:
            raise NotFoundError(
                "no chat encounter with id %s" % encounter_id)
        return encounter

    def _encounters_of(self, channel_id):
        return [e for e in self._chat_encounters.values()
                if e["channel_id"] == channel_id]

    def _reports_of(self, encounter_id):
        return [r for r in self._chat_reports.values()
                if r["encounter_id"] == encounter_id]

    @staticmethod
    def _latest_outcome_label(reports):
        """The current outcome label of an encounter: the label
        of its most recently recorded report, derived at read,
        never stored."""
        if not reports:
            return None
        return reports[-1]["outcome_label"]

    def _chat_channel_view(self, channel):
        """A read view of a channel record: the stored record
        plus values derived at read (encounter count, report
        count, current outcome label across its encounters).
        Nothing derived is ever written back to the stored
        record."""
        view = copy.deepcopy(channel)
        encounters = self._encounters_of(channel["id"])
        reports = [r for r in self._chat_reports.values()
                   if r["channel_id"] == channel["id"]]
        view["encounter_count"] = len(encounters)
        view["report_count"] = len(reports)
        view["current_outcome_label"] = self._latest_outcome_label(reports)
        return view

    def _chat_encounter_view(self, encounter):
        """A read view of an encounter record plus its report
        count and current outcome label, derived at read."""
        view = copy.deepcopy(encounter)
        reports = self._reports_of(encounter["id"])
        view["report_count"] = len(reports)
        view["current_outcome_label"] = self._latest_outcome_label(reports)
        return view

    # ----------------------------------------------------------
    # idx 968 -- chat channel definitions (CirrusMD)
    # ----------------------------------------------------------

    def create_chat_channel(self, participant_id, channel_ref, actor,
                            program_id=None):
        """Register a chat channel definition for a participant.

        A DEFINITION of the fork's chat-based virtual care
        channel, held as a labeled reference: the channel is not
        operated here, no message is delivered or routed here,
        and no transcript or message content can be held -- no
        parameter or field shape exists for one.
        """
        self._guard(actor, "activity_write", "extn_chat_channel_create")
        self._check_participant(participant_id, actor)
        if program_id is not None:
            self._check_program(program_id, actor)
        channel_ref = _non_empty(channel_ref, "channel_ref")
        self._check_unique(self._chat_channels, "channel_ref",
                           channel_ref, "chat channel")
        with self._lock:
            record = {
                "id": self._next_id("chc"),
                "participant_id": participant_id,
                "program_id": program_id,
                "channel_ref": channel_ref,
                "state": _REFERENCE_STATE,
                "reference_stub": True,
                "reference_transport": True,
                "channel_operated_here": False,
                "messages_delivered_here": False,
                "routed_here": False,
                "transcript_held_here": False,
                "content_held_here": False,
                "created_utc": _utc_now(),
                "created_by": getattr(actor, "name", str(actor)),
            }
            self._chat_channels[record["id"]] = record
            self._audit(actor, "extn_chat_channel_create", record["id"])
            return copy.deepcopy(record)

    def get_chat_channel(self, channel_id, actor):
        self._maybe_require(actor, "activity_read")
        channel = self._check_channel(channel_id)
        self._scope_check_record(actor, channel)
        return self._chat_channel_view(channel)

    def list_chat_channels(self, actor, participant_id=None):
        self._maybe_require(actor, "activity_read")
        records = [self._chat_channel_view(c)
                   for c in self._chat_channels.values()]
        records = self._scoped(actor, records)
        if participant_id is not None:
            records = [r for r in records
                       if r["participant_id"] == participant_id]
        return records

    # ----------------------------------------------------------
    # idx 968 -- chat encounter records (CirrusMD)
    # ----------------------------------------------------------

    def create_chat_encounter(self, channel_id, encounter_ref, actor,
                              activity_id=None, recorded_on=None):
        """Record a chat encounter held against a channel.

        A record ABOUT an encounter on the fork's chat channel:
        the encounter is not conducted here, no messages are
        exchanged here, and no clinical decision is made here.
        ``activity_id`` may bind the encounter to the channel
        participant's OWN Core 6 activity (chat visit) record;
        binding to another participant's activity is refused by
        the ownership seam.
        """
        self._guard(actor, "activity_write", "extn_chat_encounter_create")
        channel = self._check_channel(channel_id)
        encounter_ref = _non_empty(encounter_ref, "encounter_ref")
        self._check_unique(self._chat_encounters, "encounter_ref",
                           encounter_ref, "chat encounter")
        if activity_id is not None:
            activity = self.store.get_activity(activity_id, actor)
            self._check_chat_activity_belongs(
                activity, channel["participant_id"])
        if recorded_on is not None:
            recorded_on = _validate_date(recorded_on, "recorded_on")
        with self._lock:
            record = {
                "id": self._next_id("che"),
                "channel_id": channel["id"],
                "participant_id": channel["participant_id"],
                "encounter_ref": encounter_ref,
                "activity_id": activity_id,
                "recorded_on": recorded_on,
                "state": _REFERENCE_STATE,
                "reference_stub": True,
                "reference_transport": True,
                "chat_conducted_here": False,
                "messages_exchanged_here": False,
                "transcript_held_here": False,
                "decided_here": False,
                "created_utc": _utc_now(),
                "created_by": getattr(actor, "name", str(actor)),
            }
            self._chat_encounters[record["id"]] = record
            self._audit(actor, "extn_chat_encounter_create", record["id"])
            return copy.deepcopy(record)

    def get_chat_encounter(self, encounter_id, actor):
        self._maybe_require(actor, "activity_read")
        encounter = self._check_encounter(encounter_id)
        self._scope_check_record(actor, encounter)
        return self._chat_encounter_view(encounter)

    def list_chat_encounters(self, actor, participant_id=None,
                             channel_id=None):
        self._maybe_require(actor, "activity_read")
        records = [self._chat_encounter_view(e)
                   for e in self._chat_encounters.values()]
        records = self._scoped(actor, records)
        if participant_id is not None:
            records = [r for r in records
                       if r["participant_id"] == participant_id]
        if channel_id is not None:
            records = [r for r in records if r["channel_id"] == channel_id]
        return records

    # ----------------------------------------------------------
    # idx 968 -- reported chat encounter outcomes (CirrusMD)
    # ----------------------------------------------------------

    def record_chat_encounter_report(self, encounter_id, outcome_label,
                                     actor, recorded_on=None,
                                     reported_message_count=None):
        """Record an outcome of a chat encounter, as reported.

        The outcome label and any reported message count are
        held VERBATIM, exactly as the platform reported them:
        nothing is measured, delivered or decided here, and the
        count is never reinterpreted (no rate, duration or
        clinical figure is derived from it anywhere).
        """
        self._guard(actor, "activity_write", "extn_chat_report_record")
        encounter = self._check_encounter(encounter_id)
        if outcome_label not in CHAT_OUTCOME_LABELS:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(CHAT_OUTCOME_LABELS),))
        if recorded_on is not None:
            recorded_on = _validate_date(recorded_on, "recorded_on")
        if reported_message_count is not None:
            reported_message_count = _count(
                reported_message_count, "reported_message_count")
        with self._lock:
            record = {
                "id": self._next_id("chr"),
                "encounter_id": encounter["id"],
                "channel_id": encounter["channel_id"],
                "participant_id": encounter["participant_id"],
                "outcome_label": outcome_label,
                "outcome_basis": "platform_reported",
                "reported_message_count": reported_message_count,
                "recorded_on": recorded_on,
                "reference_transport": True,
                "measured_here": False,
                "delivered_here": False,
                "decided_here": False,
                "created_utc": _utc_now(),
                "created_by": getattr(actor, "name", str(actor)),
            }
            self._chat_reports[record["id"]] = record
            self._audit(actor, "extn_chat_report_record", record["id"])
            return copy.deepcopy(record)

    def list_chat_encounter_reports(self, actor, encounter_id=None):
        self._maybe_require(actor, "activity_read")
        records = [copy.deepcopy(r) for r in self._chat_reports.values()]
        records = self._scoped(actor, records)
        if encounter_id is not None:
            records = [r for r in records
                       if r["encounter_id"] == encounter_id]
        return records

    # ----------------------------------------------------------
    # idx 968 -- derived summary
    # ----------------------------------------------------------

    def chat_channel_summary(self, actor, participant_id=None):
        """Deterministic counts over the recorded chat channel
        reference records. Counts only: no outcome is scored, no
        rate is computed, and nothing about the channel's
        operation is claimed -- it is not operated here."""
        self._maybe_require(actor, "activity_read")
        channels = self._scoped(
            actor, list(self._chat_channels.values()))
        if participant_id is not None:
            channels = [c for c in channels
                        if c["participant_id"] == participant_id]
        channel_ids = {c["id"] for c in channels}
        encounters = [e for e in self._chat_encounters.values()
                      if e["channel_id"] in channel_ids]
        reports = [r for r in self._chat_reports.values()
                   if r["channel_id"] in channel_ids]
        by_outcome = {}
        for report in reports:
            label = report["outcome_label"]
            by_outcome[label] = by_outcome.get(label, 0) + 1
        return {
            "channels": len(channels),
            "encounters": len(encounters),
            "reports": len(reports),
            "reports_by_outcome": by_outcome,
            "channel_operated_here": False,
            "messages_delivered_here": False,
        }
