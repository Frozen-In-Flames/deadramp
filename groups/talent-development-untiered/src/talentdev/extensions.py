"""Final GAPS batch extensions — Untiered Set 20 (Talent Development).

Records-form implementations and labeled reference implementations
for the four open gap entries of this set, built over the founding
Talent Development substrate in :mod:`talentdev.store`. This module
is the only code the batch adds; every core module is unchanged.

Tier discipline: this set is untiered and this module keeps it
that way. No record, view, or summary here carries a tier, a
baseline, an impact level, or a CMMC equivalence key or value;
tier stays null, exactly as the set's spec sheets record it. The
forks' one documented control claim (BetterUp's privacy sentence,
at prose weight) remains the fork's claim about itself, recorded
in UNION-SPEC.md; nothing here converts it into a build
attainment or a baseline.

Talent-area discipline, per the founding build and the house
precedents: people appear only as opaque references validated to
be incapable of being an email address; no record shape can hold
a real name, contact detail, session content, assessment content,
or model content; **no score is computed anywhere** — outcomes are
reported labels recorded verbatim, and every derived figure is a
count or a sum of recorded counts, computed at read and stored
nowhere.

Honesty labels, per entry:

- **Live development delivery** (idx 930) is built in its records
  form: delivery session records bound to a core program, and
  attendance records bound to a core participation of that same
  program, with a per-program delivery view derived at read. No
  session is delivered here: every session record carries
  ``delivered_here: False`` and ``content_held_here: False`` —
  neither description names the delivery form, and none was
  invented. What is built is the records layer a delivery's
  operation would be recorded through.
- **Assessment instruments and their administration / scoring
  engines** (idx 931) ships as a **labeled reference
  implementation**: instrument reference records bound to a core
  assessment (the instrument label is the core's own recorded
  label, held as data), plus administration report records
  holding the administering system's outcome labels verbatim.
  Every record carries ``reference_stub: True``; no instrument
  is held, nothing is administered, and no outcome is judged
  here (``instrument_held_here: False``,
  ``administered_here: False``, ``judged_here: False``). The
  core's result records remain the administration-outcome
  records; recording a reference or a report changes no core
  record — pinned by test.
- **Analytics / trend-computation engine behind the dashboard**
  (idx 932) is built in its records-and-derivation form: trend
  definition records held as data (``definition_only: True``),
  and a trend view that derives, at read, deterministic sums and
  counts over the core's OWN recorded insight snapshots for the
  definition's organization and metric (snapshot count, total
  recorded cohort, total recorded exhibiting count, latest
  recorded period label). No trend is computed over any raw
  workforce data, no dashboard is rendered, and no figure beyond
  sums of recorded aggregates is produced — the engine that
  computes trends from live data is not built, and the stored
  definition carries no totals (pinned by test). The definition
  record states ``computed_here: False`` for the trend engine
  itself; the view's sums are derivations over records, the same
  distinction the founding summary draws.
- **AI models** (idx 933) ships as a **labeled reference
  implementation**: model reference records holding a model
  label and a purpose label as data, plus report records holding
  reported outcome labels verbatim. Every record carries
  ``reference_stub: True`` and ``inference_here: False``; no
  model is held, trained, or run here. The entry's own text
  bounds it — no fork describes an AI model; it was registered
  for completeness only — so the reference form records that the
  surface exists and claims nothing behind it. The class
  deliberately has no inference-shaped method at all — pinned
  by test.

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: delivery sessions and attendance
use ``programs``; instrument references and administration
reports use ``assess``; trend definitions use ``insights``;
model references and reports use ``insights``; all reads and the
summary use ``read``. Enforcement mirrors the core store's
``_check_role``: a User-like actor is checked against the matrix
and denials are recorded in the core audit log under a
``:denied`` suffix; a plain string actor carries identity
without a role, as in the core. Successful extension mutations
audit with ``ext_``-prefixed actions.

Ids are sequential per object type with fixed prefixes
(``ses-``, ``att-``, ``itr-``, ``adr-``, ``trd-``, ``mod-``,
``mdr-``). A failed operation consumes no id and changes
nothing: all validation happens before any mutation. All
timestamps are UTC ISO-8601. Records returned are copies;
mutating a returned record changes nothing stored.

The single derivation seam for "latest reported label" views is
:meth:`TalentDevExtensions._latest_label`: the label of the most
recently **recorded** record in a list, in this register's
recording order. It is the seam the batch's fresh negative
control mutates (see tests/README.md).
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["TalentDevExtensions", "ATTENDANCE_LABELS"]

ATTENDANCE_LABELS = ("attended", "missed", "partial")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _person_ref(value, field="person_ref"):
    """An opaque person reference, mirroring the core store's
    rule: non-empty, no whitespace, no ``@`` — a value of that
    shape cannot be an email address."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')"
            % field)
    return value


class TalentDevExtensions:
    """Extension register wrapping a core
    :class:`talentdev.store.TalentDevStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._sessions = {}
        self._attendances = {}
        self._instrument_refs = {}
        self._admin_reports = {}
        self._trend_definitions = {}
        self._model_refs = {}
        self._model_reports = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    def _require(self, actor, action, audit_action, target=None):
        """Write/read enforcement, mirroring the core store's
        ``_check_role``: User-like actors are checked against the
        founding matrix; denials are audited with a ``:denied``
        suffix before the error propagates."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % audit_action, target)
                raise

    def _get(self, collection, obj_id, what):
        record = collection.get(obj_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return record

    @staticmethod
    def _latest_label(records, key):
        """Latest-label derivation seam: the value of ``key`` on
        the most recently recorded record in ``records`` (this
        register's recording order), or None when the list is
        empty. Derived at read; nothing about it is stored."""
        return records[-1][key] if records else None

    # -- core lookups (existence + binding checks) -------------------

    def _core_organization(self, actor, org_id):
        return self.store.get_organization(actor, org_id)

    def _core_program(self, actor, program_id):
        return self.store.get_program(actor, program_id)

    def _core_participation(self, actor, participation_id):
        return self.store.get_participation(actor, participation_id)

    def _core_assessment(self, actor, assessment_id):
        return self.store.get_assessment(actor, assessment_id)

    # ================================================================
    # Live development delivery (idx 930) — built, records form
    # ================================================================

    def schedule_delivery_session(self, actor, program_id, label,
                                  mode_label, scheduled_at=None):
        """Record one delivery session for a core program.

        Action: programs. Id prefix: ses-. The session is a
        record of a scheduled delivery: its label, a delivery
        mode label held as data (neither description names the
        delivery form, so the mode is the caller's label, never
        an invented taxonomy), and its scheduled moment. No
        session is delivered here and no session content is held
        (``delivered_here: False``, ``content_held_here:
        False``).
        """
        self._require(actor, "programs", "ext_session_record",
                      target=program_id)
        _text(label, "label")
        _text(mode_label, "mode_label")
        _optional_text(scheduled_at, "scheduled_at")
        with self._lock:
            program = self._core_program(actor, program_id)
            record = {
                "id": self._next_id("ses"),
                "program_id": program_id,
                "org_id": program["org_id"],
                "label": label,
                "mode_label": mode_label,
                "scheduled_at": scheduled_at,
                "delivered_here": False,
                "content_held_here": False,
                "state": "recorded_session_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sessions[record["id"]] = record
        self._audit(actor, "ext_session_record", record["id"],
                    {"program_id": program_id})
        return dict(record)

    def record_attendance(self, actor, session_id, participation_id,
                          attendance_label):
        """Record one attendance report for a session, bound to a
        core participation of the session's program.

        Action: programs. Id prefix: att-. The participation must
        belong to the session's program (a participation in
        another program is refused and consumes no id), and one
        participation has at most one attendance record per
        session. ``attendance_label`` is from the fixed
        vocabulary :data:`ATTENDANCE_LABELS` — a fact about the
        sitting, reported by the caller; nothing about the
        participant is judged here.
        """
        self._require(actor, "programs", "ext_attendance_record",
                      target=session_id)
        if attendance_label not in ATTENDANCE_LABELS:
            raise ValidationError(
                "attendance_label must be one of %r"
                % (ATTENDANCE_LABELS,))
        with self._lock:
            session = self._get(self._sessions, session_id,
                                "delivery session")
            participation = self._core_participation(
                actor, participation_id)
            if participation["program_id"] != session["program_id"]:
                raise ValidationError(
                    "participation %r does not belong to program %r"
                    % (participation_id, session["program_id"]))
            for existing in self._attendances.values():
                if (existing["session_id"] == session_id
                        and existing["participation_id"]
                        == participation_id):
                    raise ValidationError(
                        "participation %r already has an attendance "
                        "record for session %r (%s)"
                        % (participation_id, session_id,
                           existing["id"]))
            record = {
                "id": self._next_id("att"),
                "session_id": session_id,
                "program_id": session["program_id"],
                "participation_id": participation_id,
                "participant_ref": participation["participant_ref"],
                "attendance_label": attendance_label,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._attendances[record["id"]] = record
        self._audit(actor, "ext_attendance_record", record["id"],
                    {"session_id": session_id})
        return dict(record)

    def get_session(self, session_id, actor=None):
        """One delivery session record. Action: read."""
        self._require(actor, "read", "ext_session_read",
                      target=session_id)
        return dict(self._get(self._sessions, session_id,
                              "delivery session"))

    def list_sessions(self, actor=None, program_id=None):
        """Delivery session records, optionally for one program.
        Action: read."""
        self._require(actor, "read", "ext_session_read")
        return [dict(s) for s in self._sessions.values()
                if program_id is None or s["program_id"] == program_id]

    def list_attendances(self, session_id, actor=None):
        """Attendance records for one session. Action: read."""
        self._require(actor, "read", "ext_attendance_read",
                      target=session_id)
        with self._lock:
            self._get(self._sessions, session_id, "delivery session")
            return [dict(a) for a in self._attendances.values()
                    if a["session_id"] == session_id]

    def program_delivery_view(self, program_id, actor=None):
        """A program's delivery picture, derived at read: the
        session count, the attendance count, attendance counts by
        recorded label, the count of distinct participants with
        an attendance record, and the latest recorded attendance
        label. Counts over recorded values only; nothing is
        stored, and the stored session records carry none of it.
        Action: read.
        """
        self._require(actor, "read", "ext_session_read",
                      target=program_id)
        with self._lock:
            self._core_program(actor, program_id)
            sessions = [s for s in self._sessions.values()
                        if s["program_id"] == program_id]
            attendances = [a for a in self._attendances.values()
                           if a["program_id"] == program_id]
            by_label = {}
            for attendance in attendances:
                label = attendance["attendance_label"]
                by_label[label] = by_label.get(label, 0) + 1
            return {
                "program_id": program_id,
                "session_count": len(sessions),
                "attendance_count": len(attendances),
                "attendances_by_label": by_label,
                "distinct_participants": len(
                    {a["participant_ref"] for a in attendances}),
                "latest_attendance_label": self._latest_label(
                    attendances, "attendance_label"),
                "derived": True,
            }

    # ================================================================
    # Assessment instruments / administration / scoring engines
    # (idx 931) — reference
    # ================================================================

    def register_instrument_reference(self, actor, assessment_id):
        """Record an instrument reference for a core assessment.

        Action: assess. Id prefix: itr-. Reference
        implementation: the record names the assessment and holds
        its instrument label exactly as the core recorded it, as
        data. The instrument itself — its items, its
        administration, its judgments — is the fork's engine, not
        held and not run here (``instrument_held_here: False``,
        ``administered_here: False``, ``judged_here: False``).
        One reference per assessment: a second registration is
        refused and consumes no id. Recording a reference changes
        no core record.
        """
        self._require(actor, "assess", "ext_instrument_reference_record",
                      target=assessment_id)
        with self._lock:
            assessment = self._core_assessment(actor, assessment_id)
            for existing in self._instrument_refs.values():
                if existing["assessment_id"] == assessment_id:
                    raise ValidationError(
                        "assessment %r already has an instrument "
                        "reference (%s)"
                        % (assessment_id, existing["id"]))
            record = {
                "id": self._next_id("itr"),
                "assessment_id": assessment_id,
                "org_id": assessment["org_id"],
                "instrument_label": assessment["instrument_label"],
                "reference_stub": True,
                "instrument_held_here": False,
                "administered_here": False,
                "judged_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._instrument_refs[record["id"]] = record
        self._audit(actor, "ext_instrument_reference_record",
                    record["id"], {"assessment_id": assessment_id})
        return dict(record)

    def record_administration_report(self, actor, instrument_ref_id,
                                     subject_ref, reported_outcome_label):
        """Record an administration report for an instrument
        reference, verbatim as reported by the administering
        system.

        Action: assess. Id prefix: adr-. ``subject_ref`` is an
        opaque reference validated exactly as the core validates
        person references. ``reported_outcome_label`` is the
        administering system's own label, held verbatim — this
        build administers nothing and judges no outcome
        (``administered_here: False``, ``judged_here: False``),
        and the record carries no numeric field of any kind.
        Recording a report creates no core result record.
        """
        self._require(actor, "assess", "ext_admin_report_record",
                      target=instrument_ref_id)
        _person_ref(subject_ref, "subject_ref")
        _text(reported_outcome_label, "reported_outcome_label")
        with self._lock:
            self._get(self._instrument_refs, instrument_ref_id,
                      "instrument reference")
            record = {
                "id": self._next_id("adr"),
                "instrument_ref_id": instrument_ref_id,
                "subject_ref": subject_ref,
                "reported_outcome_label": reported_outcome_label,
                "reference_stub": True,
                "administered_here": False,
                "judged_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._admin_reports[record["id"]] = record
        self._audit(actor, "ext_admin_report_record", record["id"],
                    {"instrument_ref_id": instrument_ref_id})
        return dict(record)

    def get_instrument_reference(self, instrument_ref_id, actor=None):
        """One instrument reference record. Action: read."""
        self._require(actor, "read", "ext_instrument_reference_read",
                      target=instrument_ref_id)
        return dict(self._get(self._instrument_refs, instrument_ref_id,
                              "instrument reference"))

    def list_instrument_references(self, actor=None, assessment_id=None):
        """Instrument reference records, optionally for one
        assessment. Action: read."""
        self._require(actor, "read", "ext_instrument_reference_read")
        return [dict(r) for r in self._instrument_refs.values()
                if assessment_id is None
                or r["assessment_id"] == assessment_id]

    def list_administration_reports(self, instrument_ref_id, actor=None):
        """Administration report records for one instrument
        reference. Action: read."""
        self._require(actor, "read", "ext_admin_report_read",
                      target=instrument_ref_id)
        with self._lock:
            self._get(self._instrument_refs, instrument_ref_id,
                      "instrument reference")
            return [dict(r) for r in self._admin_reports.values()
                    if r["instrument_ref_id"] == instrument_ref_id]

    def instrument_view(self, instrument_ref_id, actor=None):
        """An instrument reference with its derived report
        summary: report count, report counts by reported label,
        and the latest reported outcome label, derived at read.
        Action: read."""
        self._require(actor, "read", "ext_instrument_reference_read",
                      target=instrument_ref_id)
        with self._lock:
            reference = self._get(self._instrument_refs,
                                  instrument_ref_id,
                                  "instrument reference")
            reports = [r for r in self._admin_reports.values()
                       if r["instrument_ref_id"] == instrument_ref_id]
            by_label = {}
            for report in reports:
                label = report["reported_outcome_label"]
                by_label[label] = by_label.get(label, 0) + 1
            view = dict(reference)
            view["report_count"] = len(reports)
            view["reports_by_label"] = by_label
            view["latest_reported_label"] = self._latest_label(
                reports, "reported_outcome_label")
            view["derived"] = True
            return view

    # ================================================================
    # Analytics / trend-computation engine (idx 932) — built,
    # records-and-derivation form
    # ================================================================

    def create_trend_definition(self, actor, org_id, label,
                                metric_label):
        """Record one trend definition as data: an organization, a
        definition label, and the core snapshot metric label the
        definition is stated over.

        Action: insights. Id prefix: trd-. The definition is held
        as data only (``definition_only: True``): the trend
        engine that would compute trends from live workforce data
        is not built and nothing is computed at definition time
        (``computed_here: False``). The stored record carries no
        totals — the trend view derives them at read from the
        core's recorded snapshots (pinned by test).
        """
        self._require(actor, "insights", "ext_trend_definition_record",
                      target=org_id)
        _text(label, "label")
        _text(metric_label, "metric_label")
        with self._lock:
            self._core_organization(actor, org_id)
            record = {
                "id": self._next_id("trd"),
                "org_id": org_id,
                "label": label,
                "metric_label": metric_label,
                "definition_only": True,
                "computed_here": False,
                "state": "recorded_definition_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._trend_definitions[record["id"]] = record
        self._audit(actor, "ext_trend_definition_record", record["id"],
                    {"org_id": org_id, "metric_label": metric_label})
        return dict(record)

    def get_trend_definition(self, definition_id, actor=None):
        """One trend definition record. Action: read."""
        self._require(actor, "read", "ext_trend_definition_read",
                      target=definition_id)
        return dict(self._get(self._trend_definitions, definition_id,
                              "trend definition"))

    def list_trend_definitions(self, actor=None, org_id=None):
        """Trend definition records, optionally for one
        organization. Action: read."""
        self._require(actor, "read", "ext_trend_definition_read")
        return [dict(d) for d in self._trend_definitions.values()
                if org_id is None or d["org_id"] == org_id]

    def trend_view(self, actor, definition_id):
        """A trend definition's picture over the core's recorded
        snapshots, derived at read: the count of core snapshots
        recorded for the definition's organization and metric,
        the sum of their recorded cohort sizes, the sum of their
        recorded exhibiting counts, and the latest recorded
        period label. These are sums of recorded aggregates —
        deterministic derivations over this substrate's own
        records — not a trend computed from raw data, and no
        proportion or change figure of any kind is produced.
        Action: read.
        """
        self._require(actor, "read", "ext_trend_definition_read",
                      target=definition_id)
        with self._lock:
            definition = self._get(self._trend_definitions,
                                   definition_id, "trend definition")
            snapshots = self.store.list_snapshots(
                actor, org_id=definition["org_id"],
                metric_label=definition["metric_label"])
            view = dict(definition)
            view["snapshot_count"] = len(snapshots)
            view["total_recorded_cohort"] = sum(
                s["cohort_size"] for s in snapshots)
            view["total_recorded_value"] = sum(
                s["value_count"] for s in snapshots)
            view["latest_period_label"] = self._latest_label(
                snapshots, "period_label")
            view["derived"] = True
            return view

    # ================================================================
    # AI models (idx 933) — reference
    # ================================================================

    def register_model_reference(self, actor, org_id, model_label,
                                 purpose_label):
        """Record an AI model reference for an organization.

        Action: insights. Id prefix: mod-. Reference
        implementation: ``model_label`` and ``purpose_label``
        name a model as data, exactly as a caller states them.
        No model is held, trained, or run here
        (``reference_stub: True``, ``inference_here: False``,
        ``model_held_here: False``). No fork in this set
        describes an AI model — the entry was registered for
        completeness only — so the reference records the surface
        and claims nothing behind it. Recording a reference
        changes no core record.
        """
        self._require(actor, "insights", "ext_model_reference_record",
                      target=org_id)
        _text(model_label, "model_label")
        _text(purpose_label, "purpose_label")
        with self._lock:
            self._core_organization(actor, org_id)
            record = {
                "id": self._next_id("mod"),
                "org_id": org_id,
                "model_label": model_label,
                "purpose_label": purpose_label,
                "reference_stub": True,
                "inference_here": False,
                "model_held_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_refs[record["id"]] = record
        self._audit(actor, "ext_model_reference_record", record["id"],
                    {"org_id": org_id})
        return dict(record)

    def record_model_report(self, actor, model_ref_id, outcome_label):
        """Record a model report, verbatim as reported by the
        external model's operator.

        Action: insights. Id prefix: mdr-. The label is the
        operator's own report; no inference produced it here
        (``inference_here: False``).
        """
        self._require(actor, "insights", "ext_model_report_record",
                      target=model_ref_id)
        _text(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._model_refs, model_ref_id,
                      "model reference")
            record = {
                "id": self._next_id("mdr"),
                "model_ref_id": model_ref_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "inference_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_reports[record["id"]] = record
        self._audit(actor, "ext_model_report_record", record["id"],
                    {"model_ref_id": model_ref_id})
        return dict(record)

    def get_model_reference(self, model_ref_id, actor=None):
        """One model reference record. Action: read."""
        self._require(actor, "read", "ext_model_reference_read",
                      target=model_ref_id)
        return dict(self._get(self._model_refs, model_ref_id,
                              "model reference"))

    def list_model_references(self, actor=None, org_id=None):
        """Model reference records, optionally for one
        organization. Action: read."""
        self._require(actor, "read", "ext_model_reference_read")
        return [dict(r) for r in self._model_refs.values()
                if org_id is None or r["org_id"] == org_id]

    def list_model_reports(self, model_ref_id, actor=None):
        """Report records for one model reference. Action: read."""
        self._require(actor, "read", "ext_model_report_read",
                      target=model_ref_id)
        with self._lock:
            self._get(self._model_refs, model_ref_id, "model reference")
            return [dict(r) for r in self._model_reports.values()
                    if r["model_ref_id"] == model_ref_id]

    def model_view(self, model_ref_id, actor=None):
        """A model reference with its derived report summary:
        report count, report counts by reported label, and the
        latest reported outcome label, derived at read.
        Action: read."""
        self._require(actor, "read", "ext_model_reference_read",
                      target=model_ref_id)
        with self._lock:
            reference = self._get(self._model_refs, model_ref_id,
                                  "model reference")
            reports = [r for r in self._model_reports.values()
                       if r["model_ref_id"] == model_ref_id]
            by_label = {}
            for report in reports:
                label = report["outcome_label"]
                by_label[label] = by_label.get(label, 0) + 1
            view = dict(reference)
            view["report_count"] = len(reports)
            view["reports_by_label"] = by_label
            view["latest_reported_label"] = self._latest_label(
                reports, "outcome_label")
            view["derived"] = True
            return view

    # ================================================================
    # Extension summary — counts only, derived at read
    # ================================================================

    def extension_summary(self, actor=None):
        """Counts over the extension register, derived at read.
        Counts only: no score, no proportion, no tier or baseline
        key of any kind. Action: read.
        """
        self._require(actor, "read", "ext_summary_read")
        with self._lock:
            return {
                "delivery_sessions": len(self._sessions),
                "attendances": len(self._attendances),
                "instrument_references": len(self._instrument_refs),
                "administration_reports": len(self._admin_reports),
                "trend_definitions": len(self._trend_definitions),
                "model_references": len(self._model_refs),
                "model_reports": len(self._model_reports),
            }
