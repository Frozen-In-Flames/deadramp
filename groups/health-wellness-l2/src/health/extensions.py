"""Final GAPS batch extensions for Health & Wellness L2 (Group 18).

Clean-room, standard-library-only extensions for the 11 open
entries of the Group 18 section (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a wrapper
around :class:`HealthStore`; every core module is untouched and
byte-identical to the shipped group build. The records forms
mirror the adjudicated forms of the Health & Wellness untiered
set's batch unit (``groups/health-wellness-untiered``), adapted to
this group's own spec: where the two groups' wording differs --
telehealth, whose named absence at THIS tier was retired by the
remainder-addition fork GTS VirtualHealth's own words -- this
group's spec governs.

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
``ValidationError``). This build is **not a medical device and
claims no FDA status**.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records (core records and extension records).

- Medical claims adjudication is claim RECORDS with outcomes
  recorded as reported and the current outcome derived at read:
  this build adjudicates nothing and pays nothing
  (``adjudicated_here`` / ``paid_here`` are False on every claim
  record). A verification check or claim record may only bind to
  a core eligibility record of the SAME participant -- the
  ownership seam :meth:`HealthExtensions._check_eligibility_belongs`.
- Clinical decision support is guideline REFERENCE records (held
  as data, never applied) plus the clinician's own recorded
  decision labels, stored verbatim: the build generates no
  advice, no recommendation, and no alert of its own
  (``advice_generated_here`` is False on every decision record).
- Telehealth media is visit records -- opaque references,
  scheduling metadata, a recorded modality label. No media
  channel exists or is implied (``media_channel_here`` is False).
- Device connectivity is device-pairing and sync-status records
  with opaque device references: no data flows through this
  substrate (``data_flows_here`` is False).
- Engagement channels ship as receipts: every message record
  carries ``reference_transport: True`` and state
  ``recorded_reference_only``. Nothing is sent, ever.
- Analytics are deterministic count/aggregate derivations over
  held records, method-labeled ``deterministic_aggregates`` /
  ``deterministic_counts`` -- never a learned model and never a
  clinical interpretation (no thresholds, no flags, no
  normal/abnormal labels anywhere).
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing connects, infers, executes,
  generates, or hosts.

Doctrines carried from the core: derived-never-stored for every
computed value (engagement counts, survey aggregates, claim
current outcome and counts, device latest status, app-access
counts); append-only audit on the core store's log with
``ext_``-prefixed actions for every successful mutation, and
denied write attempts recorded with a ``:denied`` suffix; RBAC
via :mod:`health.access` with the core's existing actions,
enforced before any state change or id allocation, so a failed
operation consumes no id and changes nothing; member scope
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
        self._documentation_references = {}
        self._verification_checks = {}
        self._claims = {}
        self._claim_outcomes = {}
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
            "emr": 0, "esy": 0, "doc": 0, "vrf": 0, "clm": 0,
            "clo": 0, "tlv": 0, "gdl": 0, "cds": 0, "dvl": 0,
            "dsy": 0, "mdl": 0, "mdo": 0, "wfd": 0, "wfr": 0,
            "app": 0, "dep": 0,
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

    # -- EMR / EHR integration engines & documentation depth -----------
    # STUB-ENGINE, reference implementation: an integration record
    # describes a connection as data; nothing connects
    # (``reference_stub: True``, ``connected_here: False``). Sync
    # events and documentation references are recorded as reported
    # by an external engine; documentation is held only as opaque
    # references to documents that live elsewhere, never generated
    # here (``generated_here: False``). No patient record payload
    # exists in any shape: a sync event carries a direction and a
    # count only; a documentation reference carries an opaque
    # ``document_ref`` and its integration.

    def create_emr_integration(self, system_ref, system_kind, actor):
        """Register an EMR/EHR integration record. Action: program_write."""
        self._guard(actor, "program_write", "ext_emr_integration_create")
        _non_empty(system_ref, "system_ref")
        if system_kind not in EMR_SYSTEM_KINDS:
            raise ValidationError(
                "system_kind must be one of %s" % (", ".join(EMR_SYSTEM_KINDS),))
        with self._lock:
            self._check_unique(self._emr_integrations, "system_ref", system_ref,
                               "system_ref")
            record_id = self._next_id("emr")
            record = {
                "id": record_id,
                "system_ref": system_ref,
                "system_kind": system_kind,
                "reference_stub": True,
                "connected_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._emr_integrations[record_id] = record
            self._audit(actor, "ext_emr_integration_create", record_id,
                        details={"system_ref": system_ref,
                                 "system_kind": system_kind})
            return dict(record)

    def record_emr_sync_event(self, integration_id, direction, record_count,
                              actor, occurred_on=None):
        """Record a reported sync event. Action: activity_write.

        Carries a direction and a record count as reported by an
        external engine -- never record payloads.
        """
        self._guard(actor, "activity_write", "ext_emr_sync_event_record")
        if direction not in SYNC_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s" % (", ".join(SYNC_DIRECTIONS),))
        record_count = _count(record_count, "record_count")
        if occurred_on is not None:
            _validate_date(occurred_on, "occurred_on")
        with self._lock:
            self._get(self._emr_integrations, integration_id, "EMR integration")
            record_id = self._next_id("esy")
            record = {
                "id": record_id,
                "integration_id": integration_id,
                "direction": direction,
                "record_count": record_count,
                "occurred_on": occurred_on,
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

    def record_documentation_reference(self, integration_id, document_ref,
                                       actor, recorded_on=None):
        """Record an EMR documentation reference. Action: activity_write.

        The documentation-depth half of the entry: a document (for
        example a visit document produced in the EHR) is held only
        as an opaque ``document_ref`` against its integration. The
        document itself lives in the external system; nothing is
        generated or stored here (``generated_here: False``).
        """
        self._guard(actor, "activity_write", "ext_documentation_reference_record")
        _non_empty(document_ref, "document_ref")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._emr_integrations, integration_id, "EMR integration")
            record_id = self._next_id("doc")
            record = {
                "id": record_id,
                "integration_id": integration_id,
                "document_ref": document_ref,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "generated_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._documentation_references[record_id] = record
            self._audit(actor, "ext_documentation_reference_record", record_id,
                        details={"integration_id": integration_id,
                                 "document_ref": document_ref})
            return dict(record)

    def list_emr_integrations(self, actor=None):
        """Return integration records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r) for r in self._sorted(self._emr_integrations.values())]

    def list_emr_sync_events(self, actor=None, integration_id=None):
        """Return sync events, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._emr_sync_events.values())
            if integration_id is not None:
                records = [r for r in records
                           if r["integration_id"] == integration_id]
            return [dict(r) for r in records]

    def list_documentation_references(self, actor=None, integration_id=None):
        """Return documentation references, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._documentation_references.values())
            if integration_id is not None:
                records = [r for r in records
                           if r["integration_id"] == integration_id]
            return [dict(r) for r in records]

    # -- Medical claims adjudication ------------------------------------
    # Records form of the adjudication surface over the core's
    # eligibility / coverage records: a verification check records
    # an externally reported outcome for a participant's eligibility
    # record; a claim record binds an opaque claim reference to
    # that same participant's eligibility record; an outcome record
    # records an adjudication outcome as reported. Claims carry NO
    # amount, insurer, or member-number field -- those fields do
    # not exist. This build adjudicates nothing and pays nothing:
    # ``adjudicated_here`` / ``paid_here`` are False on every claim.

    def _check_eligibility_belongs(self, eligibility, participant_id):
        """Ownership seam for verification checks and claim records.

        A verification check or claim record may only bind to an
        eligibility record of the SAME participant it is filed for.
        MUTATION DRILL NOTE: neutralizing this check (making the
        refusal unreachable) is the batch unit's negative-control
        mutation; the suite's refusal tests then fail (see
        tests/README.md for the verified record).
        """
        if eligibility["participant_id"] != participant_id:
            raise ValidationError(
                "eligibility record %r belongs to a different participant"
                % (eligibility["id"],))

    def record_verification_check(self, participant_id, eligibility_id, outcome,
                                  actor, checked_on):
        """Record an eligibility verification outcome. Action: eligibility_write.

        The outcome is recorded as reported; this build verifies
        nothing itself (``verified_here`` is False).
        """
        self._guard(actor, "eligibility_write", "ext_verification_check_record")
        if outcome not in VERIFICATION_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(VERIFICATION_OUTCOMES),))
        _validate_date(checked_on, "checked_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            self._check_eligibility_belongs(eligibility, participant_id)
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

    def create_claim_record(self, participant_id, eligibility_id, claim_ref,
                            actor, submitted_on):
        """Create a claim record. Action: eligibility_write.

        Binds an opaque ``claim_ref`` to the participant's own
        eligibility record. The record carries no amount field.
        """
        self._guard(actor, "eligibility_write", "ext_claim_record_create")
        _non_empty(claim_ref, "claim_ref")
        _validate_date(submitted_on, "submitted_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            self._check_eligibility_belongs(eligibility, participant_id)
            self._check_unique(self._claims, "claim_ref", claim_ref, "claim_ref")
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
        """Record an adjudication outcome as reported. Action: eligibility_write."""
        self._guard(actor, "eligibility_write", "ext_claim_outcome_record")
        if outcome not in CLAIM_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(CLAIM_OUTCOMES),))
        _validate_date(decided_on, "decided_on")
        with self._lock:
            claim = self._get(self._claims, claim_id, "claim")
            record_id = self._next_id("clo")
            record = {
                "id": record_id,
                "claim_id": claim_id,
                "participant_id": claim["participant_id"],
                "outcome": outcome,
                "decided_on": decided_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._claim_outcomes[record_id] = record
            self._audit(actor, "ext_claim_outcome_record", record_id,
                        details={"claim_id": claim_id, "outcome": outcome})
            return dict(record)

    def _claim_view(self, claim):
        outcomes = self._sorted(
            [o for o in self._claim_outcomes.values()
             if o["claim_id"] == claim["id"]])
        view = dict(claim)
        view["outcome_count"] = len(outcomes)
        view["current_outcome"] = outcomes[-1]["outcome"] if outcomes else None
        return view

    def get_claim_record(self, claim_id, actor=None):
        """One claim record with its derived outcome state. Action: eligibility_read."""
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            claim = self._get(self._claims, claim_id, "claim")
            self._scope_check_record(actor, claim)
            return self._claim_view(claim)

    def list_claim_records(self, actor=None, participant_id=None):
        """Return claim records with derived outcome state. Action: eligibility_read."""
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            records = self._sorted(self._claims.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._claim_view(r) for r in self._scoped(actor, records)]

    def claims_summary(self, actor, participant_id=None):
        """Derived claim counts by current outcome.

        Action: report_read (+ member scope). Deterministic counts
        over held claim records; no amount is summed anywhere (no
        amount field exists).
        """
        self._guard(actor, "report_read", "ext_claims_summary")
        with self._lock:
            records = list(self._claims.values())
            if participant_id is not None:
                self._check_participant(participant_id, actor)
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            by_outcome = {outcome: 0 for outcome in CLAIM_OUTCOMES}
            undecided = 0
            for record in records:
                view = self._claim_view(record)
                if view["current_outcome"] is None:
                    undecided += 1
                else:
                    by_outcome[view["current_outcome"]] += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "claims": len(records),
                "by_current_outcome": by_outcome,
                "undecided": undecided,
            }

    # -- Telehealth media ------------------------------------------------
    # Records form: a visit record is the visit's registry -- opaque
    # references, scheduling metadata, and the modality as a
    # RECORDED LABEL. No media channel exists in this substrate:
    # ``media_channel_here`` is False on every visit record and the
    # modality label implies no capability. At this tier the
    # founding section's named absence was retired by the remainder
    # addition fork GTS VirtualHealth's own words (their listing
    # claims a telehealth offering); the records form follows THIS
    # group's spec either way -- visit records, never a media
    # engine. State transitions are explicit records-form moves:
    # ``scheduled`` -> ``completed`` / ``cancelled`` set by a
    # clinician or admin via the state setter; nothing about the
    # actual session is observed or recorded.

    def create_telehealth_visit(self, participant_id, visit_ref, modality,
                                starts_at, ends_at, actor):
        """Schedule a telehealth visit record. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_telehealth_visit_create")
        _non_empty(visit_ref, "visit_ref")
        if modality not in TELEHEALTH_MODALITIES:
            raise ValidationError(
                "modality must be one of %s" % (", ".join(TELEHEALTH_MODALITIES),))
        start = _parse_iso_datetime(starts_at, "starts_at")
        end = _parse_iso_datetime(ends_at, "ends_at")
        if end < start:
            raise ValidationError("ends_at must not precede starts_at")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._telehealth_visits, "visit_ref", visit_ref,
                               "visit_ref")
            record_id = self._next_id("tlv")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "visit_ref": visit_ref,
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
        """Move a visit record to a new state. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_telehealth_visit_set_state")
        if state not in VISIT_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(VISIT_STATES),))
        with self._lock:
            visit = self._get(self._telehealth_visits, visit_id, "telehealth visit")
            visit["state"] = state
            self._audit(actor, "ext_telehealth_visit_set_state", visit_id,
                        details={"state": state})
            return dict(visit)

    def list_telehealth_visits(self, actor=None, participant_id=None):
        """Return visit records, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._telehealth_visits.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Clinical decision support ---------------------------------------
    # Records form: a guideline reference is a citation RECORD --
    # the guideline itself is held elsewhere and is never applied
    # here (``applied_here`` is False). A clinician decision record
    # stores the clinician's OWN decision LABEL, verbatim, against
    # a guideline reference; the build generates no advice, no
    # recommendation, and no alert of its own
    # (``advice_generated_here`` is False on every decision
    # record). There is deliberately no score, threshold, or
    # alert field in either shape.

    def create_guideline_reference(self, guideline_ref, title, actor,
                                   program_id=None):
        """Register a clinical guideline reference. Action: program_write."""
        self._guard(actor, "program_write", "ext_guideline_reference_create")
        _non_empty(guideline_ref, "guideline_ref")
        _non_empty(title, "guideline title")
        with self._lock:
            if program_id is not None:
                self._check_program(program_id, actor)
            self._check_unique(self._guideline_references, "guideline_ref",
                               guideline_ref, "guideline_ref")
            record_id = self._next_id("gdl")
            record = {
                "id": record_id,
                "guideline_ref": guideline_ref,
                "title": title,
                "program_id": program_id,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._guideline_references[record_id] = record
            self._audit(actor, "ext_guideline_reference_create", record_id,
                        details={"guideline_ref": guideline_ref})
            return dict(record)

    def record_clinician_decision(self, participant_id, guideline_id,
                                  decision_label, actor, decided_on):
        """Record a clinician's decision label. Action: plan_write.

        The label is the clinician's own, stored verbatim; the
        build offers no advice of its own
        (``advice_generated_here`` is False).
        """
        self._guard(actor, "plan_write", "ext_clinician_decision_record")
        _non_empty(decision_label, "decision_label")
        _validate_date(decided_on, "decided_on")
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
                "decided_on": decided_on,
                "advice_generated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._clinician_decisions[record_id] = record
            self._audit(actor, "ext_clinician_decision_record", record_id,
                        details={"participant_id": participant_id,
                                 "guideline_id": guideline_id})
            return dict(record)

    def list_clinician_decisions(self, actor=None, participant_id=None):
        """Return clinician decision records. Action: plan_read."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._clinician_decisions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def list_guideline_references(self, actor=None):
        """Return guideline reference records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r) for r in self._sorted(self._guideline_references.values())]

    # -- Device connectivity / sync pipelines ---------------------------
    # Records form: a device link pairs an opaque device reference
    # with a participant; a sync status records the status LABELS
    # and record counts an external pipeline reports. No device
    # data flows through this substrate (``data_flows_here`` is
    # False) and the device itself is identified only by the
    # caller's opaque reference -- no serial, IMEI, or hardware
    # identifier field exists. The link's view derives sync_count
    # and latest_status_label at read.

    def create_device_link(self, participant_id, device_ref, actor, linked_on=None):
        """Register a device link record. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_device_link_create")
        _non_empty(device_ref, "device_ref")
        if linked_on is not None:
            _validate_date(linked_on, "linked_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            for existing in self._device_links.values():
                if (existing["participant_id"] == participant_id
                        and existing["device_ref"] == device_ref):
                    raise ValidationError(
                        "device_ref %r is already linked to this participant"
                        % (device_ref,))
            record_id = self._next_id("dvl")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "device_ref": device_ref,
                "linked_on": linked_on,
                "data_flows_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._device_links[record_id] = record
            self._audit(actor, "ext_device_link_create", record_id,
                        details={"participant_id": participant_id,
                                 "device_ref": device_ref})
            return dict(record)

    def record_sync_status(self, link_id, status_label, record_count, actor,
                           recorded_on=None):
        """Record a reported sync status. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_device_sync_status_record")
        _non_empty(status_label, "status_label")
        record_count = _count(record_count, "record_count")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            link = self._get(self._device_links, link_id, "device link")
            record_id = self._next_id("dsy")
            record = {
                "id": record_id,
                "link_id": link_id,
                "participant_id": link["participant_id"],
                "status_label": status_label,
                "record_count": record_count,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sync_statuses[record_id] = record
            self._audit(actor, "ext_device_sync_status_record", record_id,
                        details={"link_id": link_id,
                                 "status_label": status_label})
            return dict(record)

    def _link_view(self, link):
        statuses = self._sorted(
            [s for s in self._sync_statuses.values()
             if s["link_id"] == link["id"]])
        view = dict(link)
        view["sync_count"] = len(statuses)
        view["latest_status_label"] = (
            statuses[-1]["status_label"] if statuses else None)
        return view

    def list_device_links(self, actor=None, participant_id=None):
        """Return device links with derived sync state. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._device_links.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._link_view(r) for r in self._scoped(actor, records)]

    # -- AI/ML models & personalization engines --------------------------
    # STUB-ENGINE, reference implementation: a model profile is a
    # registry record describing a model as data; an output
    # reference records that a model produced an output, identified
    # by an opaque reference the substrate never inspects. Nothing
    # infers, scores, or personalizes here (``reference_stub:
    # True``, ``inference_here: False``). Output content never
    # enters this substrate -- only the reference does.

    def create_model_profile(self, model_ref, kind, actor):
        """Register a model profile record. Action: program_write."""
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

    def record_model_output(self, participant_id, model_id, output_ref, actor,
                            recorded_on=None):
        """Record a model output reference. Action: plan_write.

        Only the opaque ``output_ref`` is held; the output itself
        lives in the external model system.
        """
        self._guard(actor, "plan_write", "ext_model_output_record")
        _non_empty(output_ref, "output_ref")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._get(self._model_profiles, model_id, "model profile")
            record_id = self._next_id("mdo")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "model_id": model_id,
                "output_ref": output_ref,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "inference_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_outputs[record_id] = record
            self._audit(actor, "ext_model_output_record", record_id,
                        details={"participant_id": participant_id,
                                 "model_id": model_id})
            return dict(record)

    def list_model_outputs(self, actor=None, participant_id=None):
        """Return model output references. Action: plan_read."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._model_outputs.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Automation / workflow engines -----------------------------------
    # STUB-ENGINE, reference implementation: a workflow definition
    # is a registry record whose steps are opaque references held
    # as data (``reference_stub: True``, ``executed_here: False``);
    # a run reference records a run outcome as reported by an
    # external engine. This substrate executes nothing.

    def create_workflow_definition(self, workflow_ref, title, step_refs, actor):
        """Register a workflow definition record. Action: program_write."""
        self._guard(actor, "program_write", "ext_workflow_definition_create")
        _non_empty(workflow_ref, "workflow_ref")
        _non_empty(title, "workflow title")
        step_refs = _string_list(step_refs, "step_refs")
        with self._lock:
            self._check_unique(self._workflow_definitions, "workflow_ref",
                               workflow_ref, "workflow_ref")
            record_id = self._next_id("wfd")
            record = {
                "id": record_id,
                "workflow_ref": workflow_ref,
                "title": title,
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

    def record_workflow_run(self, participant_id, workflow_id, outcome_label,
                            actor, recorded_on=None):
        """Record a workflow run reference. Action: activity_write.

        The outcome label is recorded as reported by the external
        engine; nothing ran here.
        """
        self._guard(actor, "activity_write", "ext_workflow_run_record")
        _non_empty(outcome_label, "outcome_label")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._get(self._workflow_definitions, workflow_id,
                      "workflow definition")
            record_id = self._next_id("wfr")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "workflow_id": workflow_id,
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
                        details={"participant_id": participant_id,
                                 "workflow_id": workflow_id})
            return dict(record)

    def list_workflow_runs(self, actor=None, participant_id=None):
        """Return workflow run references. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._workflow_runs.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Multi-device native apps ----------------------------------------
    # Records form: an app-access record registers that a
    # participant reaches the program through a labelled platform
    # with an opaque app reference. No application is built,
    # distributed, or updated here; the summary derives per-platform
    # registration counts at read.

    def register_app_access(self, participant_id, app_ref, platform, actor,
                            registered_on=None):
        """Register an app-access record. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_app_access_register")
        _non_empty(app_ref, "app_ref")
        if platform not in APP_PLATFORMS:
            raise ValidationError(
                "platform must be one of %s" % (", ".join(APP_PLATFORMS),))
        if registered_on is not None:
            _validate_date(registered_on, "registered_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            for existing in self._app_access.values():
                if (existing["participant_id"] == participant_id
                        and existing["app_ref"] == app_ref):
                    raise ValidationError(
                        "app_ref %r is already registered for this participant"
                        % (app_ref,))
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
                                 "platform": platform})
            return dict(record)

    def app_access_summary(self, actor, participant_id=None):
        """Derived app-access counts by platform. Action: report_read."""
        self._guard(actor, "report_read", "ext_app_access_summary")
        with self._lock:
            records = list(self._app_access.values())
            if participant_id is not None:
                self._check_participant(participant_id, actor)
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            by_platform = {platform: 0 for platform in APP_PLATFORMS}
            for record in records:
                by_platform[record["platform"]] += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "registrations": len(records),
                "by_platform": by_platform,
            }

    # -- Hosting platform -------------------------------------------------
    # STUB-ENGINE, reference implementation, per
    # PLATFORM-LAYER.md decision 6: hosting substrate and
    # multi-tenancy are deployment-layer properties of the
    # embedding organization. A deployment record describes a
    # deployment as data (tenancy label, region label, as given);
    # nothing is hosted here (``reference_stub: True``,
    # ``hosted_here: False``, ``multi_tenant_here: False``), and
    # the summary states the build's own posture honestly: a
    # single-tenant reference deployment, matching this group's
    # README ("a single-tenant reference deployment").

    def create_deployment_record(self, deployment_ref, tenancy_label, region_label,
                                 actor):
        """Register a deployment record. Action: program_write."""
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

    def deployment_summary(self, actor):
        """Derived deployment record counts and the build's posture.

        Action: report_read. States honestly that this build is a
        single-tenant reference deployment and hosts nothing.
        """
        self._guard(actor, "report_read", "ext_deployment_summary")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "records": len(self._deployment_records),
                "build_tenancy": "single_tenant_reference",
                "hosted_here": False,
            }
