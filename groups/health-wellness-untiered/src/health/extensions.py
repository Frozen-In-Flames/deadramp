"""Final GAPS batch extensions for the Health & Wellness untiered set.

Clean-room, standard-library-only extensions for the 15 open
entries of Untiered Set 11 (see ``BATCH.md`` in the group directory
for the per-entry disposition). This module is a wrapper around
:class:`HealthStore`; every core module is untouched and
byte-identical to the shipped set build.

**Tier discipline carries into the extension:** this set is
untiered -- every member's FedRAMP impact level is "Unknown" in
the source dataset -- so nothing here asserts a baseline, a tier,
or a CMMC equivalence either. The extension builds to the set's
own records, exactly as the core does. This build is **not a
medical device and claims no FDA status**.

**The category's HARD PRIVACY RULE binds absolutely, here as in
the core:** records and opaque caller-supplied references only.
No entity shape in this module has a name, contact, date-of-birth,
member-number, insurer, diagnosis, or free-text clinical field --
those fields **do not exist**. Survey answers are numeric values
keyed by opaque question references; claim and verification
outcomes are recorded labels; guideline content is held elsewhere
and referenced by opaque reference. Methods accept only their
named parameters, so a caller cannot smuggle a forbidden field
into a record (pinned by tests: an unexpected keyword raises
``TypeError`` and a smuggled key inside a survey answer raises
``ValidationError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the set's OWN records (core records and extension records).

- Claims adjudication is claim RECORDS with outcomes recorded as
  reported and counts derived at read: this build adjudicates
  nothing and pays nothing (``adjudicated_here`` /
  ``paid_here`` are False on every claim record).
- Clinical decision support is guideline REFERENCE records (held
  as data, never applied) plus the clinician's own recorded
  decision labels, stored verbatim: the build generates no
  advice, no recommendation, and no alert of its own
  (``advice_generated_here`` is False on every decision record).
- Telehealth visit support is visit records -- opaque references,
  scheduling metadata, a recorded modality label. No media
  channel exists or is implied (``media_channel_here`` is False).
- Device connectivity is device-pairing and sync-status records
  with opaque device references: no data flows through this
  substrate (``data_flows_here`` is False).
- Engagement channels ship as receipts: every message record
  carries ``reference_transport: True`` and state
  ``recorded_reference_only``. Nothing is sent, ever.
- Analytics are deterministic count/aggregate derivations over
  held measurement records, method-labeled
  ``deterministic_aggregates`` / ``deterministic_counts`` --
  never a learned model and never a clinical interpretation (no
  thresholds, no flags, no normal/abnormal labels anywhere).
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing connects, infers, executes,
  or hosts.

Doctrines carried from the core: derived-never-stored for every
computed value (engagement counts, survey aggregates, claim
outcome counts and current outcome, navigation step counts,
slot booked/remaining counts, therapy totals, analytics, device
latest status, app-access counts); append-only audit on the core
store's log with ``ext_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a ``:denied``
suffix; RBAC via :mod:`health.access` with the core's existing
actions, enforced before any state change or id allocation, so a
failed operation consumes no id and changes nothing; member scope
mirrors the store's -- a member-role actor may only read records
whose participant's ``participant_ref`` is their own name.
"""

import math
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CHANNEL_KINDS = ("portal_message", "sms", "email_message", "app_push",
                 "voice_call")
CONTENT_KINDS = ("article", "video", "exercise", "education_module")
EMR_SYSTEM_KINDS = ("ehr", "emr", "practice_management")
SYNC_DIRECTIONS = ("inbound", "outbound")
VERIFICATION_OUTCOMES = ("verified", "not_verified", "pending")
CLAIM_OUTCOMES = ("approved", "denied", "pending")
NAVIGATION_STEP_KINDS = (
    "referral_recorded",
    "handoff_recorded",
    "follow_up_recorded",
    "resource_link_recorded",
)
TELEHEALTH_MODALITIES = ("video", "audio", "chat")
VISIT_STATES = ("scheduled", "completed", "cancelled")
MODEL_KINDS = ("risk_model", "recommendation_model", "personalization_model")
APP_PLATFORMS = ("ios", "android", "web")

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _string_list(value, what, allow_empty=False):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not allow_empty and not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    return items


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _positive_int(value, what):
    """A positive integer; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a positive integer" % (what,))
    if value < 1:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _number(value, what):
    """A finite int/float; booleans, strings, NaN and inf rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a number" % (what,))
    if not math.isfinite(value):
        raise ValidationError("%s must be finite" % (what,))
    return value


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _parse_iso_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class HealthExtensions:
    """Extension surface wrapping one :class:`HealthStore`."""

    def __init__(self, store):
        self.store = store
        self._channels = {}
        self._content_items = {}
        self._engagement_messages = {}
        self._survey_instruments = {}
        self._survey_responses = {}
        self._emr_integrations = {}
        self._emr_sync_events = {}
        self._verification_checks = {}
        self._claims = {}
        self._claim_outcomes = {}
        self._navigation_cases = {}
        self._navigation_steps = {}
        self._schedule_slots = {}
        self._slot_bookings = {}
        self._therapy_sessions = {}
        self._telehealth_visits = {}
        self._guideline_references = {}
        self._clinician_decisions = {}
        self._device_links = {}
        self._sync_statuses = {}
        self._model_profiles = {}
        self._model_outputs = {}
        self._workflow_definitions = {}
        self._workflow_runs = {}
        self._app_access = {}
        self._deployment_records = {}
        self._counters = {
            "chn": 0, "cnt": 0, "msg": 0, "svi": 0, "svr": 0,
            "emr": 0, "esy": 0, "vrf": 0, "clm": 0, "clo": 0,
            "nav": 0, "nst": 0, "slt": 0, "bkg": 0, "ths": 0,
            "tlv": 0, "gdl": 0, "cds": 0, "dvl": 0, "dsy": 0,
            "mdl": 0, "mdo": 0, "wfd": 0, "wfr": 0, "app": 0,
            "dep": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core store's convention (a User-like actor is
        checked via :func:`health.access.require`; a plain string
        carries identity but no role). A denied attempt is recorded
        on the audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    @staticmethod
    def _is_member(actor):
        return actor is not None and getattr(actor, "role", None) == "member"

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_participant(self, participant_id, actor):
        """Validate that a participant exists (core getter; the
        core enforces the actor's participant_read and, for a
        member actor, member scope)."""
        return self.store.get_participant(participant_id, actor)

    def _check_program(self, program_id, actor):
        return self.store.get_program(program_id, actor)

    def _member_participant_ids(self, actor):
        """The participant ids a member actor may read (their own)."""
        return {p["id"] for p in self.store.list_participants(actor)}

    def _scoped(self, actor, records, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            return [r for r in records if r.get(key) in own]
        return list(records)

    def _scope_check_record(self, actor, record, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            if record.get(key) not in own:
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _check_unique(self, table, field, value, what):
        for existing in table.values():
            if existing[field] == value:
                raise ValidationError("%s %r is already registered" % (what, value))

    # -- Patient engagement channels & content --------------------------
    # Records form: a channel is a configuration record, a content
    # item is a registry record for content held elsewhere (only its
    # opaque reference and a label live here), and a message is a
    # send RECEIPT. This substrate sends nothing -- every message
    # record carries ``reference_transport: True`` and state
    # ``recorded_reference_only``.

    def create_engagement_channel(self, channel_ref, kind, actor):
        """Register an engagement channel configuration. Action: program_write."""
        self._guard(actor, "program_write", "ext_engagement_channel_create")
        _non_empty(channel_ref, "channel_ref")
        if kind not in CHANNEL_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(CHANNEL_KINDS),))
        with self._lock:
            self._check_unique(self._channels, "channel_ref", channel_ref,
                               "channel_ref")
            record_id = self._next_id("chn")
            record = {
                "id": record_id,
                "channel_ref": channel_ref,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._channels[record_id] = record
            self._audit(actor, "ext_engagement_channel_create", record_id,
                        details={"channel_ref": channel_ref, "kind": kind})
            return dict(record)

    def create_content_item(self, content_ref, title, kind, actor, program_id=None):
        """Register a content item held elsewhere. Action: program_write.

        Only the opaque ``content_ref``, a label, and a kind live
        here; the content itself is never held by this substrate.
        """
        self._guard(actor, "program_write", "ext_content_item_create")
        _non_empty(content_ref, "content_ref")
        _non_empty(title, "content item title")
        if kind not in CONTENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(CONTENT_KINDS),))
        with self._lock:
            if program_id is not None:
                self._check_program(program_id, actor)
            self._check_unique(self._content_items, "content_ref", content_ref,
                               "content_ref")
            record_id = self._next_id("cnt")
            record = {
                "id": record_id,
                "content_ref": content_ref,
                "title": title,
                "kind": kind,
                "program_id": program_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._content_items[record_id] = record
            self._audit(actor, "ext_content_item_create", record_id,
                        details={"content_ref": content_ref, "kind": kind})
            return dict(record)

    def record_engagement_message(self, participant_id, channel_id, content_ref,
                                  actor):
        """Record an engagement message receipt. Action: activity_write.

        A receipt only: the record carries
        ``reference_transport: True`` and ``sent_here: False`` --
        nothing is sent by this substrate.
        """
        self._guard(actor, "activity_write", "ext_engagement_message_record")
        _non_empty(content_ref, "content_ref")
        with self._lock:
            self._check_participant(participant_id, actor)
            channel = self._get(self._channels, channel_id, "engagement channel")
            record_id = self._next_id("msg")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "channel_id": channel_id,
                "channel_kind": channel["kind"],
                "content_ref": content_ref,
                "reference_transport": True,
                "sent_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._engagement_messages[record_id] = record
            self._audit(actor, "ext_engagement_message_record", record_id,
                        details={"participant_id": participant_id,
                                 "channel_id": channel_id})
            return dict(record)

    def list_engagement_messages(self, actor=None, participant_id=None,
                                 channel_id=None):
        """Return message receipts, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._engagement_messages.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if channel_id is not None:
                records = [r for r in records if r["channel_id"] == channel_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def engagement_summary(self, participant_id, actor):
        """Derived engagement counts for one participant.

        Action: report_read (+ member scope). Counts of recorded
        message receipts by channel kind, computed at read --
        ``method: deterministic_counts``. Never stored.
        """
        self._guard(actor, "report_read", "ext_engagement_summary")
        with self._lock:
            participant = self._check_participant(participant_id, actor)
            if self._is_member(actor) and \
                    participant["participant_ref"] != getattr(actor, "name", None):
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))
            by_kind = {kind: 0 for kind in CHANNEL_KINDS}
            total = 0
            for record in self._engagement_messages.values():
                if record["participant_id"] == participant_id:
                    by_kind[record["channel_kind"]] += 1
                    total += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "messages": total,
                "by_channel_kind": by_kind,
            }

    # -- Survey instruments depth ---------------------------------------
    # Records form: an instrument is a registry record whose
    # questions are opaque references held as data; a response is a
    # set of NUMERIC values keyed by those references (the substrate
    # holds no free-text answer field). Summaries are deterministic
    # aggregates derived at read.

    def create_survey_instrument(self, instrument_ref, title, question_refs,
                                 actor):
        """Register a survey instrument. Action: program_write."""
        self._guard(actor, "program_write", "ext_survey_instrument_create")
        _non_empty(instrument_ref, "instrument_ref")
        _non_empty(title, "survey instrument title")
        question_refs = _string_list(question_refs, "question_refs")
        if len(set(question_refs)) != len(question_refs):
            raise ValidationError("question_refs must be duplicate-free")
        with self._lock:
            self._check_unique(self._survey_instruments, "instrument_ref",
                               instrument_ref, "instrument_ref")
            record_id = self._next_id("svi")
            record = {
                "id": record_id,
                "instrument_ref": instrument_ref,
                "title": title,
                "question_refs": list(question_refs),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._survey_instruments[record_id] = record
            self._audit(actor, "ext_survey_instrument_create", record_id,
                        details={"instrument_ref": instrument_ref})
            return dict(record)

    def record_survey_response(self, participant_id, instrument_id, answers,
                               actor, recorded_on=None):
        """Record one survey response. Action: measurement_write.

        ``answers`` is a list of ``{"question_ref", "value"}``
        dicts -- exactly those two keys; any other key (a smuggled
        diagnosis, a note, an identifier) is refused with
        ValidationError before anything is stored. Values are
        numeric only.
        """
        self._guard(actor, "measurement_write", "ext_survey_response_record")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        if not isinstance(answers, (list, tuple)) or not answers:
            raise ValidationError("answers must be a non-empty list")
        cleaned = []
        seen = set()
        for answer in answers:
            if not isinstance(answer, dict):
                raise ValidationError("each answer must be an object")
            if set(answer.keys()) != {"question_ref", "value"}:
                raise ValidationError(
                    "each answer must have exactly the keys "
                    "'question_ref' and 'value'")
            question_ref = _non_empty(answer["question_ref"], "question_ref")
            value = _number(answer["value"], "answer value")
            if question_ref in seen:
                raise ValidationError(
                    "duplicate answer for question_ref %r" % (question_ref,))
            seen.add(question_ref)
            cleaned.append({"question_ref": question_ref, "value": value})
        with self._lock:
            self._check_participant(participant_id, actor)
            instrument = self._get(self._survey_instruments, instrument_id,
                                   "survey instrument")
            for answer in cleaned:
                if answer["question_ref"] not in instrument["question_refs"]:
                    raise ValidationError(
                        "question_ref %r is not part of instrument %r"
                        % (answer["question_ref"], instrument_id))
            record_id = self._next_id("svr")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "instrument_id": instrument_id,
                "answers": cleaned,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._survey_responses[record_id] = record
            self._audit(actor, "ext_survey_response_record", record_id,
                        details={"participant_id": participant_id,
                                 "instrument_id": instrument_id})
            return dict(record)

    def list_survey_responses(self, actor=None, participant_id=None,
                              instrument_id=None):
        """Return survey responses, optionally filtered. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._survey_responses.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if instrument_id is not None:
                records = [r for r in records
                           if r["instrument_id"] == instrument_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def survey_summary(self, instrument_id, actor):
        """Derived per-question aggregates over recorded responses.

        Action: report_read. Count/min/max/mean per question
        reference, computed at read -- ``method:
        deterministic_aggregates``. Never stored, and no threshold
        or interpretation is applied to the values.
        """
        self._guard(actor, "report_read", "ext_survey_summary")
        with self._lock:
            instrument = self._get(self._survey_instruments, instrument_id,
                                   "survey instrument")
            values = {ref: [] for ref in instrument["question_refs"]}
            responses = 0
            for record in self._survey_responses.values():
                if record["instrument_id"] == instrument_id:
                    responses += 1
                    for answer in record["answers"]:
                        values[answer["question_ref"]].append(answer["value"])
            per_question = {}
            for ref in instrument["question_refs"]:
                vals = values[ref]
                if vals:
                    per_question[ref] = {
                        "count": len(vals),
                        "min": min(vals),
                        "max": max(vals),
                        "mean": sum(vals) / len(vals),
                    }
                else:
                    per_question[ref] = {
                        "count": 0, "min": None, "max": None, "mean": None,
                    }
            return {
                "instrument_id": instrument_id,
                "method": "deterministic_aggregates",
                "responses": responses,
                "per_question": per_question,
            }

    # -- EMR/EHR integration engines (labeled reference implementation) --
    # Stub-engine: an integration record is a labeled reference
    # record of an external system this substrate does not connect
    # to. Every record carries ``reference_stub: True`` and state
    # ``recorded_reference_only``; sync events are counts as
    # reported by the external system. Nothing connects, nothing
    # flows.

    def create_emr_integration(self, integration_ref, system_kind, actor):
        """Register a reference record for an external EMR/EHR system.

        Action: program_write. Labeled reference implementation:
        ``connected_here`` is False -- this substrate holds no
        connection to any clinical system.
        """
        self._guard(actor, "program_write", "ext_emr_integration_create")
        _non_empty(integration_ref, "integration_ref")
        if system_kind not in EMR_SYSTEM_KINDS:
            raise ValidationError(
                "system_kind must be one of %s" % (", ".join(EMR_SYSTEM_KINDS),))
        with self._lock:
            self._check_unique(self._emr_integrations, "integration_ref",
                               integration_ref, "integration_ref")
            record_id = self._next_id("emr")
            record = {
                "id": record_id,
                "integration_ref": integration_ref,
                "system_kind": system_kind,
                "reference_stub": True,
                "connected_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._emr_integrations[record_id] = record
            self._audit(actor, "ext_emr_integration_create", record_id,
                        details={"integration_ref": integration_ref,
                                 "system_kind": system_kind})
            return dict(record)

    def record_emr_sync_event(self, integration_id, direction, record_count,
                              actor, recorded_on=None):
        """Record a sync event as reported by the external system.

        Action: activity_write. The count is the external system's
        own reported number, held as data; no record moves through
        this substrate.
        """
        self._guard(actor, "activity_write", "ext_emr_sync_event_record")
        if direction not in SYNC_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s" % (", ".join(SYNC_DIRECTIONS),))
        record_count = _count(record_count, "record_count")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._emr_integrations, integration_id,
                      "EMR integration")
            record_id = self._next_id("esy")
            record = {
                "id": record_id,
                "integration_id": integration_id,
                "direction": direction,
                "record_count": record_count,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._emr_sync_events[record_id] = record
            self._audit(actor, "ext_emr_sync_event_record", record_id,
                        details={"integration_id": integration_id,
                                 "direction": direction})
            return dict(record)

    def list_emr_integrations(self, actor=None):
        """Return EMR integration reference records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r) for r in self._sorted(self._emr_integrations.values())]

    def list_emr_sync_events(self, actor=None, integration_id=None):
        """Return EMR sync events, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._emr_sync_events.values())
            if integration_id is not None:
                records = [r for r in records
                           if r["integration_id"] == integration_id]
            return [dict(r) for r in records]

    # -- Insurance verification, benefits discovery & claims -----------
    # Records form: a verification check records an outcome label
    # as reported against an existing core eligibility record; a
    # claim is a record under an opaque claim reference whose
    # outcomes are recorded as reported by the payer. This build
    # verifies nothing itself, adjudicates nothing, and pays
    # nothing -- ``adjudicated_here`` and ``paid_here`` are False
    # on every claim record, and the claim's current outcome is
    # derived at read from its outcome records, never stored.

    def record_verification_check(self, participant_id, eligibility_id,
                                  outcome, actor, checked_on):
        """Record an insurance-verification outcome as reported.

        Action: eligibility_write. The eligibility record must
        belong to the participant. The outcome is a recorded
        label, not a determination by this build.
        """
        self._guard(actor, "eligibility_write", "ext_verification_check_record")
        if outcome not in VERIFICATION_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(VERIFICATION_OUTCOMES),))
        _validate_date(checked_on, "checked_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            if eligibility["participant_id"] != participant_id:
                raise ValidationError(
                    "eligibility record %r does not belong to participant %r"
                    % (eligibility_id, participant_id))
            record_id = self._next_id("vrf")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "eligibility_id": eligibility_id,
                "outcome": outcome,
                "checked_on": checked_on,
                "verified_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._verification_checks[record_id] = record
            self._audit(actor, "ext_verification_check_record", record_id,
                        details={"participant_id": participant_id,
                                 "eligibility_id": eligibility_id,
                                 "outcome": outcome})
            return dict(record)

    def list_verification_checks(self, actor=None, participant_id=None):
        """Return verification checks, optionally filtered.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            records = self._sorted(self._verification_checks.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def create_claim_record(self, participant_id, eligibility_id, claim_ref,
                            actor, submitted_on):
        """Record a claim under an opaque claim reference.

        Action: eligibility_write. The record holds no amount, no
        insurer name, and no member number -- those fields do not
        exist here. ``adjudicated_here`` and ``paid_here`` are
        False: outcomes arrive as reported records.
        """
        self._guard(actor, "eligibility_write", "ext_claim_record_create")
        _non_empty(claim_ref, "claim_ref")
        _validate_date(submitted_on, "submitted_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            if eligibility["participant_id"] != participant_id:
                raise ValidationError(
                    "eligibility record %r does not belong to participant %r"
                    % (eligibility_id, participant_id))
            self._check_unique(self._claims, "claim_ref", claim_ref,
                               "claim_ref")
            record_id = self._next_id("clm")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "eligibility_id": eligibility_id,
                "claim_ref": claim_ref,
                "submitted_on": submitted_on,
                "adjudicated_here": False,
                "paid_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._claims[record_id] = record
            self._audit(actor, "ext_claim_record_create", record_id,
                        details={"participant_id": participant_id,
                                 "claim_ref": claim_ref})
            return dict(record)

    def record_claim_outcome(self, claim_id, outcome, actor, decided_on):
        """Record a claim outcome as reported by the payer.

        Action: eligibility_write. The outcome is stored as a
        separate record; the claim's current outcome is derived
        at read from its latest outcome record.
        """
        self._guard(actor, "eligibility_write", "ext_claim_outcome_record")
        if outcome not in CLAIM_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(CLAIM_OUTCOMES),))
        _validate_date(decided_on, "decided_on")
        with self._lock:
            self._get(self._claims, claim_id, "claim record")
            record_id = self._next_id("clo")
            record = {
                "id": record_id,
                "claim_id": claim_id,
                "outcome": outcome,
                "decided_on": decided_on,
                "reported_by_ref": actor_name(actor),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._claim_outcomes[record_id] = record
            self._audit(actor, "ext_claim_outcome_record", record_id,
                        details={"claim_id": claim_id, "outcome": outcome})
            return dict(record)

    def _claim_view(self, claim):
        view = dict(claim)
        outcomes = [o for o in self._sorted(self._claim_outcomes.values())
                    if o["claim_id"] == claim["id"]]
        view["outcome_count"] = len(outcomes)
        view["current_outcome"] = outcomes[-1]["outcome"] if outcomes else None
        return view

    def get_claim_record(self, claim_id, actor=None):
        """Return one claim view with its derived current outcome.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            claim = self._get(self._claims, claim_id, "claim record")
            self._scope_check_record(actor, claim)
            return self._claim_view(claim)

    def list_claim_records(self, actor=None, participant_id=None):
        """Return claim views, optionally filtered.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            records = self._sorted(self._claims.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            return [self._claim_view(r) for r in records]

    def claims_summary(self, actor, participant_id=None):
        """Derived claim counts by current outcome.

        Action: report_read (+ member scope when a participant is
        named). Computed at read -- ``method: deterministic_counts``.
        Counts of recorded outcomes only; no amount is summed
        anywhere, because no amount exists in this substrate.
        """
        self._guard(actor, "report_read", "ext_claims_summary")
        with self._lock:
            if participant_id is not None:
                participant = self._check_participant(participant_id, actor)
                if self._is_member(actor) and \
                        participant["participant_ref"] != getattr(actor, "name", None):
                    raise PermissionDenied(
                        "permission denied: member %r may not access records "
                        "of another participant" % (getattr(actor, "name", None),))
            claims = list(self._claims.values())
            if participant_id is not None:
                claims = [c for c in claims
                          if c["participant_id"] == participant_id]
            by_outcome = {outcome: 0 for outcome in CLAIM_OUTCOMES}
            undecided = 0
            for claim in claims:
                current = self._claim_view(claim)["current_outcome"]
                if current is None:
                    undecided += 1
                else:
                    by_outcome[current] += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "claims": len(claims),
                "by_current_outcome": by_outcome,
                "undecided": undecided,
            }

    # -- Care coordination & navigation platform depth ------------------
    # Records form: a navigation case binds a participant to an
    # opaque coordinator reference; steps are recorded events with
    # kind labels and opaque target references. Counts and the
    # current step are derived at read. No referral is sent and no
    # handoff is performed -- steps record that one was recorded.

    def create_navigation_case(self, participant_id, coordinator_ref, actor,
                               program_id=None):
        """Open a care-navigation case record. Action: plan_write."""
        self._guard(actor, "plan_write", "ext_navigation_case_create")
        _non_empty(coordinator_ref, "coordinator_ref")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            record_id = self._next_id("nav")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "coordinator_ref": coordinator_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._navigation_cases[record_id] = record
            self._audit(actor, "ext_navigation_case_create", record_id,
                        details={"participant_id": participant_id})
            return dict(record)

    def record_navigation_step(self, case_id, step_kind, target_ref, actor):
        """Record one navigation step. Action: plan_write."""
        self._guard(actor, "plan_write", "ext_navigation_step_record")
        if step_kind not in NAVIGATION_STEP_KINDS:
            raise ValidationError(
                "step_kind must be one of %s"
                % (", ".join(NAVIGATION_STEP_KINDS),))
        _non_empty(target_ref, "target_ref")
        with self._lock:
            self._get(self._navigation_cases, case_id, "navigation case")
            record_id = self._next_id("nst")
            record = {
                "id": record_id,
                "case_id": case_id,
                "step_kind": step_kind,
                "target_ref": target_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._navigation_steps[record_id] = record
            self._audit(actor, "ext_navigation_step_record", record_id,
                        details={"case_id": case_id, "step_kind": step_kind})
            return dict(record)

    def _navigation_case_view(self, case):
        view = dict(case)
        steps = [s for s in self._sorted(self._navigation_steps.values())
                 if s["case_id"] == case["id"]]
        by_kind = {kind: 0 for kind in NAVIGATION_STEP_KINDS}
        for step in steps:
            by_kind[step["step_kind"]] += 1
        view["step_count"] = len(steps)
        view["steps_by_kind"] = by_kind
        view["current_step_kind"] = steps[-1]["step_kind"] if steps else None
        return view

    def get_navigation_case(self, case_id, actor=None):
        """Return one navigation case view. Action: plan_read (+ scope)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            case = self._get(self._navigation_cases, case_id, "navigation case")
            self._scope_check_record(actor, case)
            return self._navigation_case_view(case)

    def list_navigation_cases(self, actor=None, participant_id=None):
        """Return navigation case views. Action: plan_read (+ scope)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._navigation_cases.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            return [self._navigation_case_view(r) for r in records]

    def list_navigation_steps(self, actor=None, case_id=None):
        """Return navigation steps. Action: plan_read (+ scope via case)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._navigation_steps.values())
            if case_id is not None:
                records = [r for r in records if r["case_id"] == case_id]
            if self._is_member(actor):
                own_cases = {c["id"] for c in self._navigation_cases.values()
                             if c["participant_id"]
                             in self._member_participant_ids(actor)}
                records = [r for r in records if r["case_id"] in own_cases]
            return [dict(r) for r in records]

    # -- Integrated scheduling engines ----------------------------------
    # Records form: a schedule slot is a capacity record over a
    # core program; a booking binds a participant to a slot. The
    # booked count is derived at read from booking records in
    # state ``booked`` -- it is never stored on the slot -- and
    # the capacity guard refuses a booking that would exceed the
    # slot's recorded capacity, whole, consuming no id.

    def create_schedule_slot(self, program_id, starts_at, ends_at, capacity,
                             actor):
        """Create a schedule slot record. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_schedule_slot_create")
        capacity = _positive_int(capacity, "capacity")
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at")
        if end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        with self._lock:
            self._check_program(program_id, actor)
            record_id = self._next_id("slt")
            record = {
                "id": record_id,
                "program_id": program_id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "capacity": capacity,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._schedule_slots[record_id] = record
            self._audit(actor, "ext_schedule_slot_create", record_id,
                        details={"program_id": program_id,
                                 "capacity": capacity})
            return dict(record)

    def _booked_count(self, slot_id):
        return sum(1 for b in self._slot_bookings.values()
                   if b["slot_id"] == slot_id and b["state"] == "booked")

    def _check_slot_capacity(self, slot, booked_count):
        """Capacity guard seam for slot bookings.

        MUTATION DRILL NOTE: this guard is the load-bearing
        invariant of the batch's fresh negative control -- a
        booking that would take a slot's derived booked count to
        or past its recorded capacity must be refused whole. An
        implementation that lets the booking through is the
        mutant the drill and ``test_gaps_batch.py`` reject.
        """
        if booked_count >= slot["capacity"]:
            raise ValidationError(
                "schedule slot %r is at its recorded capacity (%d)"
                % (slot["id"], slot["capacity"]))

    def book_schedule_slot(self, slot_id, participant_id, actor):
        """Book a participant into a schedule slot. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_slot_booking_create")
        with self._lock:
            slot = self._get(self._schedule_slots, slot_id, "schedule slot")
            self._check_participant(participant_id, actor)
            for existing in self._slot_bookings.values():
                if (existing["slot_id"] == slot_id
                        and existing["participant_id"] == participant_id
                        and existing["state"] == "booked"):
                    raise ValidationError(
                        "participant %r already holds a booking on slot %r"
                        % (participant_id, slot_id))
            self._check_slot_capacity(slot, self._booked_count(slot_id))
            record_id = self._next_id("bkg")
            record = {
                "id": record_id,
                "slot_id": slot_id,
                "participant_id": participant_id,
                "state": "booked",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._slot_bookings[record_id] = record
            self._audit(actor, "ext_slot_booking_create", record_id,
                        details={"slot_id": slot_id,
                                 "participant_id": participant_id})
            return dict(record)

    def cancel_slot_booking(self, booking_id, actor):
        """Cancel a slot booking record. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_slot_booking_cancel")
        with self._lock:
            record = self._get(self._slot_bookings, booking_id, "slot booking")
            if record["state"] != "booked":
                raise ValidationError(
                    "booking %r is not in state 'booked'" % (booking_id,))
            record["state"] = "cancelled"
            self._audit(actor, "ext_slot_booking_cancel", booking_id,
                        details={"slot_id": record["slot_id"]})
            return dict(record)

    def _schedule_slot_view(self, slot):
        view = dict(slot)
        booked = self._booked_count(slot["id"])
        view["booked_count"] = booked
        view["remaining_capacity"] = slot["capacity"] - booked
        return view

    def get_schedule_slot(self, slot_id, actor=None):
        """Return one slot view with derived counts. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            slot = self._get(self._schedule_slots, slot_id, "schedule slot")
            return self._schedule_slot_view(slot)

    def list_schedule_slots(self, actor=None, program_id=None):
        """Return slot views, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._schedule_slots.values())
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            return [self._schedule_slot_view(r) for r in records]

    def list_slot_bookings(self, actor=None, slot_id=None, participant_id=None):
        """Return slot bookings, optionally filtered.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._slot_bookings.values())
            if slot_id is not None:
                records = [r for r in records if r["slot_id"] == slot_id]
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- At-home therapy delivery & session-metrics analytics -----------
    # Records form: a therapy session is a record under an opaque
    # session reference with an integer duration in minutes. The
    # session-metrics summary is a deterministic derivation over
    # the held session records -- counts and totals only, no
    # clinical interpretation of any value.

    def record_therapy_session(self, participant_id, session_ref,
                               duration_minutes, actor, recorded_on,
                               program_id=None):
        """Record an at-home therapy session. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_therapy_session_record")
        _non_empty(session_ref, "session_ref")
        duration_minutes = _positive_int(duration_minutes, "duration_minutes")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            self._check_unique(self._therapy_sessions, "session_ref",
                               session_ref, "session_ref")
            record_id = self._next_id("ths")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "session_ref": session_ref,
                "duration_minutes": duration_minutes,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._therapy_sessions[record_id] = record
            self._audit(actor, "ext_therapy_session_record", record_id,
                        details={"participant_id": participant_id,
                                 "session_ref": session_ref})
            return dict(record)

    def list_therapy_sessions(self, actor=None, participant_id=None,
                              program_id=None):
        """Return therapy sessions, optionally filtered.

        Action: measurement_read (+ member scope).
        """
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._therapy_sessions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def therapy_summary(self, participant_id, actor):
        """Derived session-metrics summary for one participant.

        Action: measurement_read (+ member scope). Session count
        and total minutes computed at read -- ``method:
        deterministic_counts``. Never stored.
        """
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            participant = self._check_participant(participant_id, actor)
            if self._is_member(actor) and \
                    participant["participant_ref"] != getattr(actor, "name", None):
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))
            sessions = [r for r in self._therapy_sessions.values()
                        if r["participant_id"] == participant_id]
            by_program = {}
            for record in sessions:
                key = record["program_id"]
                by_program[key] = by_program.get(key, 0) + 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "sessions": len(sessions),
                "total_minutes": sum(r["duration_minutes"] for r in sessions),
                "sessions_by_program": by_program,
            }

    # -- Telehealth visit support ---------------------------------------
    # Records form: a visit record binds a participant to a
    # scheduled window with a recorded modality label. There is
    # no media channel here -- ``media_channel_here`` is False on
    # every visit record -- and no visit is conducted by this
    # substrate; the lifecycle state is recorded data, mirroring
    # the core activity states.

    def create_telehealth_visit(self, participant_id, starts_at, modality,
                                actor, program_id=None, ends_at=None):
        """Record a telehealth visit. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_telehealth_visit_create")
        if modality not in TELEHEALTH_MODALITIES:
            raise ValidationError(
                "modality must be one of %s"
                % (", ".join(TELEHEALTH_MODALITIES),))
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = (_parse_iso_datetime(ends_at, "ends_at")
                  if ends_at is not None else None)
        if end_dt is not None and end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            record_id = self._next_id("tlv")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "modality": modality,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "state": "scheduled",
                "media_channel_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telehealth_visits[record_id] = record
            self._audit(actor, "ext_telehealth_visit_create", record_id,
                        details={"participant_id": participant_id,
                                 "modality": modality})
            return dict(record)

    def set_telehealth_visit_state(self, visit_id, state, actor):
        """Set a telehealth visit record's lifecycle state.

        Action: activity_write.
        """
        self._guard(actor, "activity_write",
                    "ext_telehealth_visit_set_state")
        if state not in VISIT_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(VISIT_STATES),))
        with self._lock:
            record = self._get(self._telehealth_visits, visit_id,
                               "telehealth visit")
            record["state"] = state
            self._audit(actor, "ext_telehealth_visit_set_state", visit_id,
                        details={"state": state})
            return dict(record)

    def get_telehealth_visit(self, visit_id, actor=None):
        """Return one telehealth visit record. Action: activity_read (+ scope)."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            record = self._get(self._telehealth_visits, visit_id,
                               "telehealth visit")
            self._scope_check_record(actor, record)
            return dict(record)

    def list_telehealth_visits(self, actor=None, participant_id=None,
                               program_id=None):
        """Return telehealth visit records, optionally filtered.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._telehealth_visits.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Measurement & outcome analytics engines ------------------------
    # Records form: a deterministic derivation over the CORE
    # measurement records (read through the core store's own list
    # API). Per-metric count/min/max/mean plus the first and last
    # recorded values by date -- computed at read, labeled
    # ``deterministic_aggregates``. No threshold, flag, or
    # clinical interpretation is applied to any value.

    def measurement_analytics(self, actor, metric_name=None, program_id=None):
        """Derived aggregates over the core measurement records.

        Action: report_read.
        """
        self._guard(actor, "report_read", "ext_measurement_analytics")
        with self._lock:
            records = self.store.list_measurements(
                actor, program_id=program_id, metric_name=metric_name)
            by_metric = {}
            for record in records:
                by_metric.setdefault(record["metric_name"], []).append(record)
            metrics = {}
            for name in sorted(by_metric):
                rows = sorted(by_metric[name],
                              key=lambda r: (r["recorded_on"], _id_num(r["id"])))
                values = [r["value"] for r in rows]
                metrics[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "first_value": values[0],
                    "last_value": values[-1],
                    "change_first_to_last": values[-1] - values[0],
                }
            return {
                "method": "deterministic_aggregates",
                "measurements": len(records),
                "participants_with_measurements":
                    len({r["participant_id"] for r in records}),
                "metrics": metrics,
            }

    # -- Clinical decision support --------------------------------------
    # Records form ONLY: a guideline REFERENCE record holds an
    # opaque reference and labels as data -- the guideline content
    # lives elsewhere and is never applied here
    # (``applied_here`` is False). A clinician decision record
    # holds the clinician's own decision label, stored verbatim.
    # This build generates no advice, no recommendation, and no
    # alert of its own: ``advice_generated_here`` is False on
    # every decision record.

    def create_guideline_reference(self, guideline_ref, title, topic_ref,
                                   actor):
        """Register a guideline reference record. Action: program_write."""
        self._guard(actor, "program_write", "ext_guideline_reference_create")
        _non_empty(guideline_ref, "guideline_ref")
        _non_empty(title, "guideline title")
        _non_empty(topic_ref, "topic_ref")
        with self._lock:
            self._check_unique(self._guideline_references, "guideline_ref",
                               guideline_ref, "guideline_ref")
            record_id = self._next_id("gdl")
            record = {
                "id": record_id,
                "guideline_ref": guideline_ref,
                "title": title,
                "topic_ref": topic_ref,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._guideline_references[record_id] = record
            self._audit(actor, "ext_guideline_reference_create", record_id,
                        details={"guideline_ref": guideline_ref})
            return dict(record)

    def record_clinician_decision(self, participant_id, guideline_id,
                                  decision_label, actor, recorded_on):
        """Record a clinician's own decision against a guideline reference.

        Action: plan_write. The label is the clinician's,
        recorded verbatim; this build contributes no advice of
        its own to the record.
        """
        self._guard(actor, "plan_write", "ext_clinician_decision_record")
        _non_empty(decision_label, "decision_label")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._get(self._guideline_references, guideline_id,
                      "guideline reference")
            record_id = self._next_id("cds")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "guideline_id": guideline_id,
                "decision_label": decision_label,
                "recorded_on": recorded_on,
                "advice_generated_here": False,
                "recorded_by_ref": actor_name(actor),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._clinician_decisions[record_id] = record
            self._audit(actor, "ext_clinician_decision_record", record_id,
                        details={"participant_id": participant_id,
                                 "guideline_id": guideline_id})
            return dict(record)

    def list_guideline_references(self, actor=None):
        """Return guideline reference records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._guideline_references.values())]

    def list_clinician_decisions(self, actor=None, participant_id=None,
                                 guideline_id=None):
        """Return clinician decision records, optionally filtered.

        Action: plan_read (+ member scope).
        """
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._clinician_decisions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if guideline_id is not None:
                records = [r for r in records
                           if r["guideline_id"] == guideline_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Device connectivity / sync pipelines ---------------------------
    # Records form: a device link is a pairing record under an
    # opaque device reference; a sync status is a status label and
    # a count as reported by the device side. No data flows
    # through this substrate -- ``data_flows_here`` is False on
    # every link record -- and a link's latest status is derived
    # at read from its status records, never stored.

    def register_device_link(self, participant_id, device_ref, actor):
        """Record a device pairing under an opaque device reference.

        Action: measurement_write.
        """
        self._guard(actor, "measurement_write", "ext_device_link_register")
        _non_empty(device_ref, "device_ref")
        with self._lock:
            self._check_participant(participant_id, actor)
            for existing in self._device_links.values():
                if (existing["participant_id"] == participant_id
                        and existing["device_ref"] == device_ref):
                    raise ValidationError(
                        "device_ref %r is already linked for participant %r"
                        % (device_ref, participant_id))
            record_id = self._next_id("dvl")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "device_ref": device_ref,
                "data_flows_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._device_links[record_id] = record
            self._audit(actor, "ext_device_link_register", record_id,
                        details={"participant_id": participant_id,
                                 "device_ref": device_ref})
            return dict(record)

    def record_sync_status(self, device_link_id, status_label, record_count,
                           actor, recorded_on):
        """Record a sync status as reported by the device side.

        Action: measurement_write. The label is stored verbatim
        as reported; the count is the device side's own number.
        """
        self._guard(actor, "measurement_write", "ext_sync_status_record")
        _non_empty(status_label, "status_label")
        record_count = _count(record_count, "record_count")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._device_links, device_link_id, "device link")
            record_id = self._next_id("dsy")
            record = {
                "id": record_id,
                "device_link_id": device_link_id,
                "status_label": status_label,
                "record_count": record_count,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sync_statuses[record_id] = record
            self._audit(actor, "ext_sync_status_record", record_id,
                        details={"device_link_id": device_link_id,
                                 "status_label": status_label})
            return dict(record)

    def _device_link_view(self, link):
        view = dict(link)
        statuses = [s for s in self._sorted(self._sync_statuses.values())
                    if s["device_link_id"] == link["id"]]
        view["sync_count"] = len(statuses)
        view["latest_status_label"] = (
            statuses[-1]["status_label"] if statuses else None)
        return view

    def get_device_link(self, device_link_id, actor=None):
        """Return one device link view. Action: measurement_read (+ scope)."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            link = self._get(self._device_links, device_link_id, "device link")
            self._scope_check_record(actor, link)
            return self._device_link_view(link)

    def list_device_links(self, actor=None, participant_id=None):
        """Return device link views. Action: measurement_read (+ scope)."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._device_links.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            return [self._device_link_view(r) for r in records]

    def list_sync_statuses(self, actor=None, device_link_id=None):
        """Return sync status records. Action: measurement_read (+ scope)."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._sync_statuses.values())
            if device_link_id is not None:
                records = [r for r in records
                           if r["device_link_id"] == device_link_id]
            if self._is_member(actor):
                own_links = {link["id"] for link in self._device_links.values()
                             if link["participant_id"]
                             in self._member_participant_ids(actor)}
                records = [r for r in records
                           if r["device_link_id"] in own_links]
            return [dict(r) for r in records]

    # -- AI/ML models & personalization engines (labeled reference) -----
    # Stub-engine: a model profile is a labeled reference record
    # of an external model. Every record carries
    # ``reference_stub: True`` and state
    # ``recorded_reference_only``; an output is held only as an
    # opaque reference -- the output content never enters this
    # substrate. Nothing is trained, run, or inferred here
    # (``inference_here`` is False).

    def create_model_profile(self, model_ref, kind, actor):
        """Register a reference record for an external AI/ML model.

        Action: program_write.
        """
        self._guard(actor, "program_write", "ext_model_profile_create")
        _non_empty(model_ref, "model_ref")
        if kind not in MODEL_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(MODEL_KINDS),))
        with self._lock:
            self._check_unique(self._model_profiles, "model_ref", model_ref,
                               "model_ref")
            record_id = self._next_id("mdl")
            record = {
                "id": record_id,
                "model_ref": model_ref,
                "kind": kind,
                "reference_stub": True,
                "inference_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_profiles[record_id] = record
            self._audit(actor, "ext_model_profile_create", record_id,
                        details={"model_ref": model_ref, "kind": kind})
            return dict(record)

    def record_model_output_reference(self, profile_id, participant_id,
                                      output_ref, actor, recorded_on):
        """Record an opaque reference to an external model's output.

        Action: plan_write. Only the reference is held; the
        output itself never enters this substrate, and nothing
        here acts on it.
        """
        self._guard(actor, "plan_write", "ext_model_output_record")
        _non_empty(output_ref, "output_ref")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._model_profiles, profile_id, "model profile")
            self._check_participant(participant_id, actor)
            record_id = self._next_id("mdo")
            record = {
                "id": record_id,
                "profile_id": profile_id,
                "participant_id": participant_id,
                "output_ref": output_ref,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_outputs[record_id] = record
            self._audit(actor, "ext_model_output_record", record_id,
                        details={"profile_id": profile_id,
                                 "participant_id": participant_id})
            return dict(record)

    def list_model_profiles(self, actor=None):
        """Return model profile reference records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r) for r in self._sorted(self._model_profiles.values())]

    def list_model_output_references(self, actor=None, participant_id=None,
                                     profile_id=None):
        """Return model output references. Action: plan_read (+ scope)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._model_outputs.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if profile_id is not None:
                records = [r for r in records if r["profile_id"] == profile_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Automation / workflow engines (labeled reference) --------------
    # Stub-engine: a workflow definition holds its step references
    # as DATA; a run record is a run as reported by an external
    # engine. Every record carries ``reference_stub: True`` and
    # state ``recorded_reference_only`` -- definitions are never
    # executed here (``executed_here`` is False), mirroring the
    # category's standing rule that workflow registries hold
    # definitions only.

    def create_workflow_definition(self, workflow_ref, step_refs, actor):
        """Register a workflow definition as data. Action: program_write."""
        self._guard(actor, "program_write", "ext_workflow_definition_create")
        _non_empty(workflow_ref, "workflow_ref")
        step_refs = _string_list(step_refs, "step_refs")
        with self._lock:
            self._check_unique(self._workflow_definitions, "workflow_ref",
                               workflow_ref, "workflow_ref")
            record_id = self._next_id("wfd")
            record = {
                "id": record_id,
                "workflow_ref": workflow_ref,
                "step_refs": list(step_refs),
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_definitions[record_id] = record
            self._audit(actor, "ext_workflow_definition_create", record_id,
                        details={"workflow_ref": workflow_ref})
            return dict(record)

    def record_workflow_run_reference(self, definition_id, participant_id,
                                      outcome_label, actor, recorded_on):
        """Record a workflow run as reported by an external engine.

        Action: activity_write. The outcome label is stored
        verbatim as reported; the run did not happen here.
        """
        self._guard(actor, "activity_write", "ext_workflow_run_record")
        _non_empty(outcome_label, "outcome_label")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._workflow_definitions, definition_id,
                      "workflow definition")
            self._check_participant(participant_id, actor)
            record_id = self._next_id("wfr")
            record = {
                "id": record_id,
                "definition_id": definition_id,
                "participant_id": participant_id,
                "outcome_label": outcome_label,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_runs[record_id] = record
            self._audit(actor, "ext_workflow_run_record", record_id,
                        details={"definition_id": definition_id,
                                 "participant_id": participant_id})
            return dict(record)

    def list_workflow_definitions(self, actor=None):
        """Return workflow definition records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._workflow_definitions.values())]

    def list_workflow_run_references(self, actor=None, participant_id=None,
                                     definition_id=None):
        """Return workflow run references. Action: activity_read (+ scope)."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._workflow_runs.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if definition_id is not None:
                records = [r for r in records
                           if r["definition_id"] == definition_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Multi-device native apps ---------------------------------------
    # Records form (the family is a platform/access property in
    # the union spec): an app-access record registers that a
    # participant is recorded as using an app endpoint under an
    # opaque app reference on a named platform. No app is built,
    # served, or tracked here -- the record holds a registration
    # and a last-activity date as reported, nothing else.

    def register_app_access(self, participant_id, app_ref, platform, actor,
                            registered_on):
        """Record a participant's app-access registration.

        Action: activity_write.
        """
        self._guard(actor, "activity_write", "ext_app_access_register")
        _non_empty(app_ref, "app_ref")
        if platform not in APP_PLATFORMS:
            raise ValidationError(
                "platform must be one of %s" % (", ".join(APP_PLATFORMS),))
        _validate_date(registered_on, "registered_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            for existing in self._app_access.values():
                if (existing["participant_id"] == participant_id
                        and existing["app_ref"] == app_ref):
                    raise ValidationError(
                        "app_ref %r is already registered for participant %r"
                        % (app_ref, participant_id))
            record_id = self._next_id("app")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "app_ref": app_ref,
                "platform": platform,
                "registered_on": registered_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._app_access[record_id] = record
            self._audit(actor, "ext_app_access_register", record_id,
                        details={"participant_id": participant_id,
                                 "app_ref": app_ref, "platform": platform})
            return dict(record)

    def list_app_access(self, actor=None, participant_id=None, platform=None):
        """Return app-access records, optionally filtered.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._app_access.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if platform is not None:
                records = [r for r in records if r["platform"] == platform]
            return [dict(r) for r in self._scoped(actor, records)]

    def app_access_summary(self, actor):
        """Derived app-access counts by platform. Action: report_read.

        Computed at read -- ``method: deterministic_counts``.
        """
        self._guard(actor, "report_read", "ext_app_access_summary")
        with self._lock:
            by_platform = {platform: 0 for platform in APP_PLATFORMS}
            for record in self._app_access.values():
                by_platform[record["platform"]] += 1
            return {
                "method": "deterministic_counts",
                "registrations": len(self._app_access),
                "by_platform": by_platform,
            }

    # -- Hosting platform layer (labeled reference implementation) ------
    # Stub-engine, per PLATFORM-LAYER.md decision 6: a fork's
    # hosting substrate does not transfer to the build. A
    # deployment record holds tenancy/region LABELS verbatim as
    # data; the summary states the build's own posture plainly
    # (single-tenant reference deployment). Recording a posture
    # hosts nothing -- ``hosted_here`` is False on every record.

    def create_deployment_record(self, deployment_ref, tenancy_label,
                                 region_label, actor):
        """Record a deployment posture as data. Action: program_write."""
        self._guard(actor, "program_write", "ext_deployment_record_create")
        _non_empty(deployment_ref, "deployment_ref")
        _non_empty(tenancy_label, "tenancy_label")
        _non_empty(region_label, "region_label")
        with self._lock:
            self._check_unique(self._deployment_records, "deployment_ref",
                               deployment_ref, "deployment_ref")
            record_id = self._next_id("dep")
            record = {
                "id": record_id,
                "deployment_ref": deployment_ref,
                "tenancy_label": tenancy_label,
                "region_label": region_label,
                "reference_stub": True,
                "hosted_here": False,
                "multi_tenant_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deployment_records[record_id] = record
            self._audit(actor, "ext_deployment_record_create", record_id,
                        details={"deployment_ref": deployment_ref})
            return dict(record)

    def list_deployment_records(self, actor=None):
        """Return deployment posture records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._deployment_records.values())]

    def deployment_summary(self, actor):
        """Derived deployment summary stating the build's own posture.

        Action: program_read. ``build_tenancy`` is
        ``single_tenant_reference`` -- this build is a
        single-tenant reference deployment and performs no cloud
        hosting, whatever posture a fork's records describe.
        """
        self._maybe_require(actor, "program_read")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "records": len(self._deployment_records),
                "build_tenancy": "single_tenant_reference",
                "hosted_here": False,
            }
