"""Final GAPS batch extensions for the Education & Training untiered set.

Clean-room, standard-library-only extensions for the 16 open entries
of Untiered Set 8 (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`LearnStore`; every core module is untouched and
byte-identical to the shipped set build.

**Tier discipline carries into the extension:** this set is
untiered — every member's FedRAMP impact level is "Unknown" in the
source dataset — so nothing here asserts a baseline, a tier, or a
CMMC equivalence either. The extension builds to the set's own
records, exactly as the core does.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over the
set's OWN records (core records and extension records).

- Delivery is delivery-session records whose status is DERIVED at
  read from the core progress records; no content is served to
  anyone and there is no LMS runtime here.
- Notification transport ships as receipts: every receipt carries
  ``reference_transport: True`` and state ``recorded_reference_only``.
  Nothing is sent, ever.
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing executes, syncs, routes, or
  hosts.
- The AI assistant surface is a deterministic lookup over the
  registered guidance-flow records, method-labeled
  ``deterministic_record_lookup`` and stub-labeled on every return;
  there is no learned model and no generated text — the "answer" is
  the held records themselves, returned verbatim.
- Proctoring and identity proofing are records of outcomes reported
  by an external provider, stored verbatim. They carry
  ``decision_made: False`` (and ``identity_provider: False`` on
  proofing records): this substrate makes no decision and is not an
  identity provider, per PLATFORM-LAYER.md decision 1.

**The founding scoring doctrine binds absolutely:** deterministic
scoring/grading was claimed by no fork in this category, so
assessments are administration records only and **no score or grade
field appears anywhere in this surface** — pinned by a recursive key
scan in the tests, exactly as the core pins it for assessment
records. The scoring entry is therefore built in its records form
(DECISION.md re-judgment option (a), grounds in ``BATCH.md``):
scoring-RULE records held as data and never applied, plus
reported-outcome records whose outcome text is stored verbatim as
reported by an external assessor. Dossier's "proficiency ratings"
are, in the union spec's own words, a fork's recorded data — this
surface records such ratings as reported data and computes nothing
from them.

Doctrines carried from the core: opaque ``*_ref`` / ``learner_id``
strings only (no record shape here can hold a name, email, phone, or
identifier for a real person beyond the core's own learner-id
convention); derived-never-stored for every computed value (delivery
status, campaign outcome counts, clinical totals, ladder progress,
matching results, pipeline counts); append-only audit on the core
store's log with ``ext_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a ``:denied``
suffix; RBAC via :mod:`learn.access` with the core's existing
actions, enforced before any state change or id allocation, so a
failed operation consumes no id and changes nothing; learner scope
mirrors the store's — a learner-role actor may only read records
whose ``learner_id`` (or ``user_ref``, for guidance events) is their
own name.
"""

import threading
from datetime import date, datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DELIVERY_MODES = ("self_paced", "instructor_led", "virtual", "live")
CLINICAL_LOG_KINDS = ("clinical_hours", "procedure", "patient_encounter")
SIM_RESOURCE_KINDS = ("room", "equipment", "scenario")
NOTIFICATION_TRIGGERS = (
    "assignment_overdue",
    "assignment_due_within_days",
    "assessment_upcoming",
)
APPLICATION_STAGES = (
    "applied", "screening", "interview", "offer", "hired", "closed",
)
PROGRESSION_OUTCOMES = ("advanced", "returned")

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


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _coerce_as_of(as_of):
    if as_of is None:
        return date.today()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        return _validate_date(as_of, "as_of")
    raise ValidationError("as_of must be an ISO date string or date")


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


class LearnExtensions:
    """Extension surface wrapping one :class:`LearnStore`."""

    def __init__(self, store):
        self.store = store
        self._phishing_campaigns = {}
        self._phishing_outcomes = {}
        self._delivery_sessions = {}
        self._competencies = {}
        self._assessment_cycles = {}
        self._signoffs = {}
        self._notification_rules = {}
        self._notification_receipts = {}
        self._clinical_logs = {}
        self._sim_resources = {}
        self._sim_bookings = {}
        self._guidance_flows = {}
        self._guidance_events = {}
        self._assistant_profiles = {}
        self._directory_syncs = {}
        self._ladders = {}
        self._evidence_submissions = {}
        self._progression_reviews = {}
        self._accreditation_workflows = {}
        self._workflow_evidence = {}
        self._credentialing_applications = {}
        self._scoring_rules = {}
        self._reported_outcomes = {}
        self._requisitions = {}
        self._candidates = {}
        self._applications = {}
        self._onboarding_records = {}
        self._opportunities = {}
        self._proctoring_records = {}
        self._proofing_records = {}
        self._deployment_records = {}
        self._counters = {
            "psc": 0, "pso": 0, "dls": 0, "cpd": 0, "cyc": 0, "sgn": 0,
            "ntr": 0, "nrc": 0, "clg": 0, "smr": 0, "smb": 0, "gdf": 0,
            "gde": 0, "asp": 0, "dsy": 0, "ldr": 0, "evs": 0, "pgr": 0,
            "acw": 0, "awe": 0, "cra": 0, "scr": 0, "rpo": 0, "rq": 0,
            "cnd": 0, "apl": 0, "onb": 0, "opp": 0, "prc": 0, "prf": 0,
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
        checked via :func:`learn.access.require`; a plain string
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
    def _is_learner(actor):
        return actor is not None and getattr(actor, "role", None) == "learner"

    def _scope_check(self, actor, owner_id, what="learner_id"):
        if self._is_learner(actor) and getattr(actor, "name", None) != owner_id:
            raise PermissionDenied(
                "permission denied: learner %r may not access records of %s %r"
                % (getattr(actor, "name", None), what, owner_id)
            )

    def _scoped(self, actor, records, key="learner_id"):
        if self._is_learner(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get(key) == name]
        return list(records)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- Phishing simulation & security-awareness engines ----------------
    # Records form: a campaign is a record of a planned simulation and
    # outcome records are events as reported by the operator. This
    # substrate sends nothing — no message is composed or delivered
    # here (``executed_here`` is False on every campaign record).

    def create_phishing_campaign(self, title, course_id, actor,
                                 learner_ids=None, template_ref=None):
        """Record a phishing-simulation campaign. Action: assessment_write."""
        self._guard(actor, "assessment_write", "ext_phishing_campaign_create")
        _non_empty(title, "campaign title")
        if learner_ids is None:
            learner_ids = []
        learner_ids = _string_list(learner_ids, "learner_ids", allow_empty=True)
        if template_ref is not None:
            _non_empty(template_ref, "template_ref")
        with self._lock:
            self.store.get_course(course_id, actor=None)
            campaign_id = self._next_id("psc")
            record = {
                "id": campaign_id,
                "title": title,
                "course_id": course_id,
                "learner_ids": list(learner_ids),
                "template_ref": template_ref,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._phishing_campaigns[campaign_id] = record
            self._audit(actor, "ext_phishing_campaign_create", campaign_id,
                        details={"course_id": course_id})
            return self._copy_campaign(record)

    @staticmethod
    def _copy_campaign(record):
        copied = dict(record)
        copied["learner_ids"] = list(record["learner_ids"])
        return copied

    def record_phishing_outcome(self, campaign_id, learner_id, outcome, actor,
                                note=""):
        """Record one learner outcome, verbatim as reported.

        Action: assessment_write. The outcome label is the operator's
        report, stored as data; nothing here evaluates the learner.
        """
        self._guard(actor, "assessment_write", "ext_phishing_outcome_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(outcome, "outcome")
        _string(note, "note")
        with self._lock:
            campaign = self._get(self._phishing_campaigns, campaign_id,
                                 "phishing campaign")
            if campaign["learner_ids"] and learner_id not in campaign["learner_ids"]:
                raise ValidationError(
                    "learner %r is not a target of campaign %r"
                    % (learner_id, campaign_id))
            outcome_id = self._next_id("pso")
            record = {
                "id": outcome_id,
                "campaign_id": campaign_id,
                "learner_id": learner_id,
                "outcome": outcome,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._phishing_outcomes[outcome_id] = record
            self._audit(actor, "ext_phishing_outcome_record", outcome_id,
                        details={"campaign_id": campaign_id,
                                 "learner_id": learner_id})
            return dict(record)

    def _campaign_view(self, record):
        view = self._copy_campaign(record)
        counts = {}
        learners = set()
        for outcome in self._phishing_outcomes.values():
            if outcome["campaign_id"] == record["id"]:
                counts[outcome["outcome"]] = counts.get(outcome["outcome"], 0) + 1
                learners.add(outcome["learner_id"])
        view["outcome_counts"] = counts
        view["learners_with_outcomes"] = len(learners)
        return view

    def get_phishing_campaign(self, campaign_id, actor=None):
        """Return one campaign with derived outcome counts.

        Action: assessment_read.
        """
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            record = self._get(self._phishing_campaigns, campaign_id,
                               "phishing campaign")
            return self._campaign_view(record)

    def list_phishing_campaigns(self, actor=None, course_id=None):
        """Return campaigns with derived outcome counts.

        Action: assessment_read.
        """
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._phishing_campaigns.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._campaign_view(r) for r in records]

    def list_phishing_outcomes(self, actor=None, campaign_id=None,
                               learner_id=None):
        """Return outcome records, optionally filtered.

        Action: assessment_read (+ learner scope).
        """
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._phishing_outcomes.values())
            if campaign_id is not None:
                records = [r for r in records if r["campaign_id"] == campaign_id]
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Training content delivery & LMS engines -------------------------
    # Records form: a delivery session binds a learner to a course
    # (and optionally a core session). The stored record carries NO
    # status: delivery status is derived at read from the core
    # progress records, the founding derivation discipline. No
    # content is served by this substrate.

    def create_delivery_session(self, learner_id, course_id, actor,
                                session_id=None, mode="self_paced"):
        """Record a delivery session. Action: progress_write."""
        self._guard(actor, "progress_write", "ext_delivery_session_create")
        _non_empty(learner_id, "learner_id")
        if mode not in DELIVERY_MODES:
            raise ValidationError(
                "mode must be one of %s" % (", ".join(DELIVERY_MODES),))
        with self._lock:
            self.store.get_course(course_id, actor=None)
            if session_id is not None:
                session = self.store.get_session(session_id, actor=None)
                if session["course_id"] != course_id:
                    raise ValidationError(
                        "session %r does not belong to course %r"
                        % (session_id, course_id))
            record_id = self._next_id("dls")
            record = {
                "id": record_id,
                "learner_id": learner_id,
                "course_id": course_id,
                "session_id": session_id,
                "mode": mode,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_sessions[record_id] = record
            self._audit(actor, "ext_delivery_session_create", record_id,
                        details={"learner_id": learner_id,
                                 "course_id": course_id, "mode": mode})
            return dict(record)

    def _derive_delivery_status(self, learner_id, course_id):
        """Derive delivery status from core records. Never stored.

        MUTATION DRILL NOTE: the completed branch of this derivation
        is the batch negative control's load-bearing invariant — a
        learner with a completed core progress record for the course
        must read ``completed``, never ``in_progress``.
        """
        progress = self.store.list_progress(actor=None, learner_id=learner_id,
                                            course_id=course_id)
        if any(p["status"] == "completed" for p in progress):
            return "completed"
        if progress:
            return "in_progress"
        enrollments = self.store.list_enrollments(
            actor=None, learner_id=learner_id, course_id=course_id)
        sessions = [s for s in self._delivery_sessions.values()
                    if s["learner_id"] == learner_id
                    and s["course_id"] == course_id]
        if enrollments or sessions:
            return "enrolled"
        return "not_started"

    def _delivery_view(self, record):
        view = dict(record)
        view["status"] = self._derive_delivery_status(
            record["learner_id"], record["course_id"])
        view["status_method"] = "derived_from_core_progress_records"
        return view

    def get_delivery_session(self, session_id, actor=None):
        """Return one delivery session with derived status.

        Action: progress_read (+ learner scope).
        """
        self._maybe_require(actor, "progress_read")
        with self._lock:
            record = self._get(self._delivery_sessions, session_id,
                               "delivery session")
            self._scope_check(actor, record["learner_id"])
            return self._delivery_view(record)

    def list_delivery_sessions(self, actor=None, learner_id=None,
                               course_id=None):
        """Return delivery sessions with derived status.

        Action: progress_read (+ learner scope).
        """
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._delivery_sessions.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._delivery_view(r)
                    for r in self._scoped(actor, records)]

    def delivery_status(self, learner_id, course_id, actor=None):
        """Return the derived delivery status for a learner+course.

        Action: progress_read (+ learner scope).
        """
        self._maybe_require(actor, "progress_read")
        self._scope_check(actor, learner_id)
        with self._lock:
            self.store.get_course(course_id, actor=None)
            return {
                "learner_id": learner_id,
                "course_id": course_id,
                "status": self._derive_delivery_status(learner_id, course_id),
                "method": "derived_from_core_progress_records",
            }

    # -- Competency management & assessment-cycle engines (reference) ----
    # Labeled reference implementation (stub-engine): competency
    # definitions, reassessment cycles, and assessor sign-off records
    # held as data. Every record carries ``reference_stub: True``.
    # A sign-off records the assessor's reported outcome verbatim —
    # Dossier's proficiency ratings are recorded data in its own
    # prose — and computes nothing from it.

    def create_competency_definition(self, role_ref, name, actor,
                                     level_labels=None):
        """Record a competency definition. Action: assessment_write."""
        self._guard(actor, "assessment_write", "ext_competency_create")
        _non_empty(role_ref, "role_ref")
        _non_empty(name, "competency name")
        if level_labels is None:
            level_labels = []
        level_labels = _string_list(level_labels, "level_labels",
                                    allow_empty=True)
        with self._lock:
            record_id = self._next_id("cpd")
            record = {
                "id": record_id,
                "role_ref": role_ref,
                "name": name,
                "level_labels": list(level_labels),
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._competencies[record_id] = record
            self._audit(actor, "ext_competency_create", record_id,
                        details={"role_ref": role_ref})
            return self._copy_competency(record)

    @staticmethod
    def _copy_competency(record):
        copied = dict(record)
        copied["level_labels"] = list(record["level_labels"])
        return copied

    def create_assessment_cycle(self, competency_id, actor, period_label="",
                                interval_months=None):
        """Record a reassessment cycle for a competency.

        Action: assessment_write.
        """
        self._guard(actor, "assessment_write", "ext_assessment_cycle_create")
        _string(period_label, "period_label")
        if interval_months is not None:
            interval_months = _count(interval_months, "interval_months")
            if interval_months == 0:
                raise ValidationError("interval_months must be positive")
        with self._lock:
            self._get(self._competencies, competency_id, "competency definition")
            record_id = self._next_id("cyc")
            record = {
                "id": record_id,
                "competency_id": competency_id,
                "period_label": period_label,
                "interval_months": interval_months,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessment_cycles[record_id] = record
            self._audit(actor, "ext_assessment_cycle_create", record_id,
                        details={"competency_id": competency_id})
            return dict(record)

    def record_assessor_signoff(self, cycle_id, learner_id, assessor_ref,
                                reported_outcome, actor):
        """Record an assessor sign-off with its outcome verbatim.

        Action: assessment_write. The outcome is the assessor's
        reported data, stored byte-for-byte; it is never parsed,
        ranked, or converted into any computed value.
        """
        self._guard(actor, "assessment_write", "ext_assessor_signoff_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(assessor_ref, "assessor_ref")
        _non_empty(reported_outcome, "reported_outcome")
        with self._lock:
            self._get(self._assessment_cycles, cycle_id, "assessment cycle")
            record_id = self._next_id("sgn")
            record = {
                "id": record_id,
                "cycle_id": cycle_id,
                "learner_id": learner_id,
                "assessor_ref": assessor_ref,
                "reported_outcome": reported_outcome,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._signoffs[record_id] = record
            self._audit(actor, "ext_assessor_signoff_record", record_id,
                        details={"cycle_id": cycle_id,
                                 "learner_id": learner_id})
            return dict(record)

    def list_competency_definitions(self, actor=None, role_ref=None):
        """Return competency definitions. Action: assessment_read."""
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._competencies.values())
            if role_ref is not None:
                records = [r for r in records if r["role_ref"] == role_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._copy_competency(r) for r in records]

    def list_assessment_cycles(self, actor=None, competency_id=None):
        """Return assessment cycles. Action: assessment_read."""
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._assessment_cycles.values())
            if competency_id is not None:
                records = [r for r in records
                           if r["competency_id"] == competency_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_assessor_signoffs(self, actor=None, cycle_id=None, learner_id=None):
        """Return sign-off records. Action: assessment_read (+ scope)."""
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._signoffs.values())
            if cycle_id is not None:
                records = [r for r in records if r["cycle_id"] == cycle_id]
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Notification & reminder engine ----------------------------------
    # Built as rules plus a deterministic evaluation over the core
    # records. Evaluation produces RECEIPTS: records of notifications
    # that a transport would carry. Every receipt carries
    # ``reference_transport: True`` — nothing is sent, ever.

    def create_notification_rule(self, trigger, actor, learner_id=None,
                                 within_days=None):
        """Record a notification rule. Action: compliance_write."""
        self._guard(actor, "compliance_write", "ext_notification_rule_create")
        if trigger not in NOTIFICATION_TRIGGERS:
            raise ValidationError(
                "trigger must be one of %s" % (", ".join(NOTIFICATION_TRIGGERS),))
        if learner_id is not None:
            _non_empty(learner_id, "learner_id")
        if trigger == "assignment_due_within_days":
            if within_days is None:
                raise ValidationError(
                    "within_days is required for assignment_due_within_days")
            within_days = _count(within_days, "within_days")
        elif within_days is not None:
            raise ValidationError(
                "within_days applies only to assignment_due_within_days")
        with self._lock:
            record_id = self._next_id("ntr")
            record = {
                "id": record_id,
                "trigger": trigger,
                "learner_id": learner_id,
                "within_days": within_days,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._notification_rules[record_id] = record
            self._audit(actor, "ext_notification_rule_create", record_id,
                        details={"trigger": trigger})
            return dict(record)

    def list_notification_rules(self, actor=None):
        """Return notification rules. Action: compliance_read."""
        self._maybe_require(actor, "compliance_read")
        with self._lock:
            records = sorted(self._notification_rules.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def _receipt_exists(self, rule_id, reference_id, learner_id):
        return any(
            r["rule_id"] == rule_id and r["reference_id"] == reference_id
            and r["learner_id"] == learner_id
            for r in self._notification_receipts.values()
        )

    def _add_receipt(self, rule, reference_id, learner_id, as_of_date, created):
        if self._receipt_exists(rule["id"], reference_id, learner_id):
            return
        record_id = self._next_id("nrc")
        record = {
            "id": record_id,
            "rule_id": rule["id"],
            "trigger": rule["trigger"],
            "learner_id": learner_id,
            "reference_id": reference_id,
            "reference_transport": True,
            "state": _REFERENCE_STATE,
            "evaluated_as_of": as_of_date.isoformat(),
            "created_utc": _utc_now(),
        }
        self._notification_receipts[record_id] = record
        created.append(dict(record))

    def evaluate_notifications(self, actor, as_of=None):
        """Run one deterministic evaluation pass over the core records.

        Action: compliance_write. For each rule, receipts are
        produced for the core records the rule matches at ``as_of``:
        compliance assignments whose DERIVED core status is
        ``overdue``; assignments due within the rule's window and not
        completed; learners booked on upcoming assessment sessions.
        Receipts are deduplicated on (rule, reference, learner), so
        re-evaluation is idempotent. Returns the new receipts.
        """
        self._guard(actor, "compliance_write", "ext_notification_evaluate")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            created = []
            assignments = self.store.list_compliance(
                actor=None, as_of=as_of_date)
            sessions = self.store.list_sessions(actor=None)
            for rule in sorted(self._notification_rules.values(),
                               key=lambda r: _id_num(r["id"])):
                if rule["trigger"] in ("assignment_overdue",
                                       "assignment_due_within_days"):
                    for view in assignments:
                        if (rule["learner_id"] is not None
                                and view["learner_id"] != rule["learner_id"]):
                            continue
                        if rule["trigger"] == "assignment_overdue":
                            matched = view["status"] == "overdue"
                        else:
                            due = _validate_date(view["due_date"], "due_date")
                            delta = (due - as_of_date).days
                            matched = (view["status"] != "completed"
                                       and 0 <= delta <= rule["within_days"])
                        if matched:
                            self._add_receipt(rule, view["id"],
                                              view["learner_id"], as_of_date,
                                              created)
                else:  # assessment_upcoming
                    for session in sessions:
                        if session["kind"] != "assessment":
                            continue
                        start = _parse_iso_datetime(
                            session["starts_at"], "starts_at").date()
                        if start < as_of_date:
                            continue
                        for learner_id in session["learner_ids"]:
                            if (rule["learner_id"] is not None
                                    and learner_id != rule["learner_id"]):
                                continue
                            self._add_receipt(rule, session["id"], learner_id,
                                              as_of_date, created)
            self._audit(actor, "ext_notification_evaluate", "notifications",
                        details={"as_of": as_of_date.isoformat(),
                                 "receipts_created": len(created)})
            return created

    def list_notification_receipts(self, actor=None, learner_id=None,
                                   rule_id=None):
        """Return notification receipts. Action: compliance_read (+ scope)."""
        self._maybe_require(actor, "compliance_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._notification_receipts.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if rule_id is not None:
                records = [r for r in records if r["rule_id"] == rule_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Medical education management engines ----------------------------
    # Records form: clinical log entries (hours / procedures /
    # patient encounters) as records over the set's own learners;
    # totals are counts and sums of recorded minutes, derived at
    # read. No clinical system is touched.

    def record_clinical_log(self, learner_id, kind, minutes, actor,
                            course_id=None, note=""):
        """Record one clinical log entry. Action: progress_write."""
        self._guard(actor, "progress_write", "ext_clinical_log_record")
        _non_empty(learner_id, "learner_id")
        if kind not in CLINICAL_LOG_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(CLINICAL_LOG_KINDS),))
        minutes = _count(minutes, "minutes")
        _string(note, "note")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("clg")
            record = {
                "id": record_id,
                "learner_id": learner_id,
                "kind": kind,
                "minutes": minutes,
                "course_id": course_id,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._clinical_logs[record_id] = record
            self._audit(actor, "ext_clinical_log_record", record_id,
                        details={"learner_id": learner_id, "kind": kind})
            return dict(record)

    def list_clinical_logs(self, actor=None, learner_id=None, kind=None):
        """Return clinical log entries. Action: progress_read (+ scope)."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._clinical_logs.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    def clinical_summary(self, actor, learner_id=None):
        """Derived totals over the clinical log. Action: progress_read."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._clinical_logs.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records = self._scoped(actor, records)
            by_kind = {k: 0 for k in CLINICAL_LOG_KINDS}
            total_minutes = 0
            for record in records:
                by_kind[record["kind"]] += 1
                total_minutes += record["minutes"]
            return {
                "learner_id": learner_id,
                "entries": len(records),
                "by_kind": by_kind,
                "total_minutes": total_minutes,
                "method": "deterministic_counts",
            }

    # -- Simulation-center operations engines ----------------------------
    # Records form: resource records (rooms, equipment, scenarios)
    # and booking records against them. An overlapping booking for
    # the same resource is rejected whole — a records rule, not a
    # scheduling engine. Nothing is captured or replayed here.

    def create_sim_resource(self, resource_ref, kind, actor, label=""):
        """Record a simulation-center resource. Action: schedule_write."""
        self._guard(actor, "schedule_write", "ext_sim_resource_create")
        _non_empty(resource_ref, "resource_ref")
        if kind not in SIM_RESOURCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(SIM_RESOURCE_KINDS),))
        _string(label, "label")
        with self._lock:
            if any(r["resource_ref"] == resource_ref
                   for r in self._sim_resources.values()):
                raise ValidationError(
                    "resource_ref %r already exists" % (resource_ref,))
            record_id = self._next_id("smr")
            record = {
                "id": record_id,
                "resource_ref": resource_ref,
                "kind": kind,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sim_resources[record_id] = record
            self._audit(actor, "ext_sim_resource_create", record_id,
                        details={"resource_ref": resource_ref, "kind": kind})
            return dict(record)

    def record_sim_booking(self, resource_id, starts_at, ends_at, actor,
                           course_id=None, title=""):
        """Record a booking against a resource. Action: schedule_write."""
        self._guard(actor, "schedule_write", "ext_sim_booking_record")
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at")
        if end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        _string(title, "title")
        with self._lock:
            self._get(self._sim_resources, resource_id, "simulation resource")
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            for existing in self._sim_bookings.values():
                if existing["resource_id"] != resource_id:
                    continue
                other_start = _parse_iso_datetime(existing["starts_at"],
                                                  "starts_at")
                other_end = _parse_iso_datetime(existing["ends_at"], "ends_at")
                if start_dt < other_end and other_start < end_dt:
                    raise ValidationError(
                        "booking overlaps existing booking %r for resource %r"
                        % (existing["id"], resource_id))
            record_id = self._next_id("smb")
            record = {
                "id": record_id,
                "resource_id": resource_id,
                "course_id": course_id,
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sim_bookings[record_id] = record
            self._audit(actor, "ext_sim_booking_record", record_id,
                        details={"resource_id": resource_id})
            return dict(record)

    def list_sim_resources(self, actor=None, kind=None):
        """Return simulation resources. Action: schedule_read."""
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            records = list(self._sim_resources.values())
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_sim_bookings(self, actor=None, resource_id=None):
        """Return simulation bookings. Action: schedule_read."""
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            records = list(self._sim_bookings.values())
            if resource_id is not None:
                records = [r for r in records if r["resource_id"] == resource_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def sim_resource_schedule(self, resource_id, actor=None):
        """Return one resource with its bookings derived in time order.

        Action: schedule_read.
        """
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            resource = dict(self._get(self._sim_resources, resource_id,
                                      "simulation resource"))
            bookings = [dict(b) for b in self._sim_bookings.values()
                        if b["resource_id"] == resource_id]
            bookings.sort(key=lambda b: (b["starts_at"], _id_num(b["id"])))
            resource["bookings"] = bookings
            resource["booking_count"] = len(bookings)
            return resource

    # -- Digital adoption & in-app guidance engines ----------------------
    # Records form: guidance flows are step records held as data
    # (steps stored verbatim) and guidance events are usage records
    # as reported. Nothing is overlaid on any application here.

    def create_guidance_flow(self, app_ref, title, actor, steps=None,
                             topic=""):
        """Record a guidance flow. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_guidance_flow_create")
        _non_empty(app_ref, "app_ref")
        _non_empty(title, "guidance flow title")
        if steps is None:
            steps = []
        steps = _string_list(steps, "steps", allow_empty=True)
        _string(topic, "topic")
        with self._lock:
            record_id = self._next_id("gdf")
            record = {
                "id": record_id,
                "app_ref": app_ref,
                "title": title,
                "topic": topic,
                "steps": list(steps),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._guidance_flows[record_id] = record
            self._audit(actor, "ext_guidance_flow_create", record_id,
                        details={"app_ref": app_ref, "topic": topic})
            return self._copy_flow(record)

    @staticmethod
    def _copy_flow(record):
        copied = dict(record)
        copied["steps"] = list(record["steps"])
        return copied

    def record_guidance_event(self, flow_id, user_ref, event, actor,
                              step_index=None):
        """Record one guidance usage event, verbatim as reported.

        Action: progress_write.
        """
        self._guard(actor, "progress_write", "ext_guidance_event_record")
        _non_empty(user_ref, "user_ref")
        _non_empty(event, "event")
        if step_index is not None:
            step_index = _count(step_index, "step_index")
        with self._lock:
            flow = self._get(self._guidance_flows, flow_id, "guidance flow")
            if step_index is not None and step_index >= len(flow["steps"]):
                raise ValidationError(
                    "step_index %r is outside flow %r" % (step_index, flow_id))
            record_id = self._next_id("gde")
            record = {
                "id": record_id,
                "flow_id": flow_id,
                "user_ref": user_ref,
                "event": event,
                "step_index": step_index,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._guidance_events[record_id] = record
            self._audit(actor, "ext_guidance_event_record", record_id,
                        details={"flow_id": flow_id, "user_ref": user_ref})
            return dict(record)

    def _flow_view(self, record):
        view = self._copy_flow(record)
        counts = {}
        for event in self._guidance_events.values():
            if event["flow_id"] == record["id"]:
                counts[event["event"]] = counts.get(event["event"], 0) + 1
        view["event_counts"] = counts
        return view

    def get_guidance_flow(self, flow_id, actor=None):
        """Return one flow with derived event counts. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            record = self._get(self._guidance_flows, flow_id, "guidance flow")
            return self._flow_view(record)

    def list_guidance_flows(self, actor=None, app_ref=None, topic=None):
        """Return guidance flows with derived event counts.

        Action: catalog_read.
        """
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = list(self._guidance_flows.values())
            if app_ref is not None:
                records = [r for r in records if r["app_ref"] == app_ref]
            if topic is not None:
                records = [r for r in records if r["topic"] == topic]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._flow_view(r) for r in records]

    def list_guidance_events(self, actor=None, flow_id=None, user_ref=None):
        """Return guidance events. Action: progress_read (+ scope on user_ref)."""
        self._maybe_require(actor, "progress_read")
        if user_ref is not None:
            self._scope_check(actor, user_ref, what="user_ref")
        with self._lock:
            records = list(self._guidance_events.values())
            if flow_id is not None:
                records = [r for r in records if r["flow_id"] == flow_id]
            if user_ref is not None:
                records = [r for r in records if r["user_ref"] == user_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records, key="user_ref")]

    # -- AI assistants & guidance bots -----------------------------------
    # Labeled reference in substance, per the batch brief: an
    # assistant profile is a record, and a lookup is a DETERMINISTIC
    # derivation over the registered guidance-flow records — exact
    # topic match, held steps returned verbatim, method labeled.
    # No learned model, no generated text. A lookup creates no
    # record; it is a read-time derivation only.

    def create_assistant_profile(self, assistant_ref, actor, topics=None):
        """Record an assistant profile. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_assistant_profile_create")
        _non_empty(assistant_ref, "assistant_ref")
        if topics is None:
            topics = []
        topics = _string_list(topics, "topics", allow_empty=True)
        with self._lock:
            if any(p["assistant_ref"] == assistant_ref
                   for p in self._assistant_profiles.values()):
                raise ValidationError(
                    "assistant_ref %r already exists" % (assistant_ref,))
            record_id = self._next_id("asp")
            record = {
                "id": record_id,
                "assistant_ref": assistant_ref,
                "topics": list(topics),
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assistant_profiles[record_id] = record
            self._audit(actor, "ext_assistant_profile_create", record_id,
                        details={"assistant_ref": assistant_ref})
            copied = dict(record)
            copied["topics"] = list(record["topics"])
            return copied

    def list_assistant_profiles(self, actor=None):
        """Return assistant profiles. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = sorted(self._assistant_profiles.values(),
                             key=lambda r: _id_num(r["id"]))
            result = []
            for record in records:
                copied = dict(record)
                copied["topics"] = list(record["topics"])
                result.append(copied)
            return result

    def guidance_lookup(self, topic, actor=None):
        """Deterministic guidance lookup over the held flow records.

        Action: progress_read. Returns the guidance flows whose
        recorded topic matches ``topic`` exactly, steps verbatim.
        The result is labeled as what it is: a reference lookup over
        records, ``method: deterministic_record_lookup`` — not an
        inference and not generated guidance.
        """
        self._maybe_require(actor, "progress_read")
        _non_empty(topic, "topic")
        with self._lock:
            matches = []
            for flow in sorted(self._guidance_flows.values(),
                               key=lambda r: _id_num(r["id"])):
                if flow["topic"] == topic:
                    matches.append({
                        "flow_id": flow["id"],
                        "app_ref": flow["app_ref"],
                        "title": flow["title"],
                        "steps": list(flow["steps"]),
                    })
            return {
                "topic": topic,
                "method": "deterministic_record_lookup",
                "reference_stub": True,
                "matches": matches,
            }

    # -- Directory integration & provisioning sync (reference) -----------
    # Labeled reference implementation (stub-engine): a sync record
    # is a snapshot of counts as reported by an external directory
    # integration. Every record carries ``reference_stub: True`` and
    # creating one changes NO core record — nothing is provisioned,
    # added, changed, or archived here.

    def create_directory_sync_record(self, directory_ref, actor, added=0,
                                     changed=0, archived=0, note=""):
        """Record a directory sync snapshot. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_directory_sync_create")
        _non_empty(directory_ref, "directory_ref")
        added = _count(added, "added")
        changed = _count(changed, "changed")
        archived = _count(archived, "archived")
        _string(note, "note")
        with self._lock:
            record_id = self._next_id("dsy")
            record = {
                "id": record_id,
                "directory_ref": directory_ref,
                "added": added,
                "changed": changed,
                "archived": archived,
                "note": note,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._directory_syncs[record_id] = record
            self._audit(actor, "ext_directory_sync_create", record_id,
                        details={"directory_ref": directory_ref})
            return dict(record)

    def list_directory_sync_records(self, actor=None, directory_ref=None):
        """Return directory sync records. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = list(self._directory_syncs.values())
            if directory_ref is not None:
                records = [r for r in records
                           if r["directory_ref"] == directory_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- Career development & clinical ladder engines --------------------
    # Records form: ladder programs hold their levels as an ordered
    # record; evidence submissions are records against a level;
    # progression reviews are recorded decisions (data) with
    # separation of duties. A learner's current level is DERIVED at
    # read from the review records — presence match over held
    # records, never a stored value and never a computed rating.

    def create_ladder_program(self, role_ref, title, levels, actor):
        """Record a career/clinical ladder program. Action: progress_write."""
        self._guard(actor, "progress_write", "ext_ladder_program_create")
        _non_empty(role_ref, "role_ref")
        _non_empty(title, "ladder program title")
        levels = _string_list(levels, "levels")
        if len(set(levels)) != len(levels):
            raise ValidationError("levels must not repeat a level label")
        with self._lock:
            record_id = self._next_id("ldr")
            record = {
                "id": record_id,
                "role_ref": role_ref,
                "title": title,
                "levels": list(levels),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ladders[record_id] = record
            self._audit(actor, "ext_ladder_program_create", record_id,
                        details={"role_ref": role_ref})
            copied = dict(record)
            copied["levels"] = list(record["levels"])
            return copied

    def record_evidence_submission(self, ladder_id, learner_id, level,
                                   evidence_ref, actor):
        """Record an advancement-evidence submission.

        Action: progress_write. ``evidence_ref`` is opaque; the
        evidence itself is never held here.
        """
        self._guard(actor, "progress_write", "ext_evidence_submission_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(level, "level")
        _non_empty(evidence_ref, "evidence_ref")
        with self._lock:
            ladder = self._get(self._ladders, ladder_id, "ladder program")
            if level not in ladder["levels"]:
                raise ValidationError(
                    "level %r is not a level of ladder %r" % (level, ladder_id))
            record_id = self._next_id("evs")
            record = {
                "id": record_id,
                "ladder_id": ladder_id,
                "learner_id": learner_id,
                "level": level,
                "evidence_ref": evidence_ref,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._evidence_submissions[record_id] = record
            self._audit(actor, "ext_evidence_submission_record", record_id,
                        details={"ladder_id": ladder_id,
                                 "learner_id": learner_id, "level": level})
            return dict(record)

    def record_progression_review(self, submission_id, outcome, actor):
        """Record a progression review of one evidence submission.

        Action: progress_write. Separation of duties: the reviewer
        may not be the actor who recorded the submission. One review
        per submission. The outcome is a recorded decision (data);
        its effect on ladder progress is derived at read.
        """
        self._guard(actor, "progress_write", "ext_progression_review_record")
        if outcome not in PROGRESSION_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(PROGRESSION_OUTCOMES),))
        with self._lock:
            submission = self._get(self._evidence_submissions, submission_id,
                                   "evidence submission")
            if actor_name(actor) == submission["recorded_by"]:
                raise ValidationError(
                    "the reviewer may not be the actor who recorded "
                    "submission %r (separation of duties)" % (submission_id,))
            if any(r["submission_id"] == submission_id
                   for r in self._progression_reviews.values()):
                raise ValidationError(
                    "submission %r already has a progression review"
                    % (submission_id,))
            record_id = self._next_id("pgr")
            record = {
                "id": record_id,
                "submission_id": submission_id,
                "outcome": outcome,
                "reviewed_by": actor_name(actor),
                "reviewed_utc": _utc_now(),
            }
            self._progression_reviews[record_id] = record
            self._audit(actor, "ext_progression_review_record", record_id,
                        details={"submission_id": submission_id,
                                 "outcome": outcome})
            return dict(record)

    def list_ladder_programs(self, actor=None, role_ref=None):
        """Return ladder programs. Action: progress_read."""
        self._maybe_require(actor, "progress_read")
        with self._lock:
            records = list(self._ladders.values())
            if role_ref is not None:
                records = [r for r in records if r["role_ref"] == role_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            result = []
            for record in records:
                copied = dict(record)
                copied["levels"] = list(record["levels"])
                result.append(copied)
            return result

    def ladder_progress(self, learner_id, ladder_id, actor=None):
        """Derived ladder progress for one learner. Action: progress_read.

        For each level in ladder order: how many evidence
        submissions the learner holds and whether any carries an
        ``advanced`` review. ``current_level`` is the highest level,
        in ladder order, with an advanced review — derived at read,
        never stored (``method: deterministic_presence_match``).
        """
        self._maybe_require(actor, "progress_read")
        self._scope_check(actor, learner_id)
        with self._lock:
            ladder = self._get(self._ladders, ladder_id, "ladder program")
            advanced_submissions = set()
            for review in self._progression_reviews.values():
                if review["outcome"] == "advanced":
                    advanced_submissions.add(review["submission_id"])
            per_level = []
            current_level = None
            for level in ladder["levels"]:
                submissions = [s for s in self._evidence_submissions.values()
                               if s["ladder_id"] == ladder_id
                               and s["learner_id"] == learner_id
                               and s["level"] == level]
                advanced = any(s["id"] in advanced_submissions
                               for s in submissions)
                if advanced:
                    current_level = level
                per_level.append({
                    "level": level,
                    "submissions": len(submissions),
                    "advanced": advanced,
                })
            return {
                "learner_id": learner_id,
                "ladder_id": ladder_id,
                "levels": per_level,
                "current_level": current_level,
                "method": "deterministic_presence_match",
            }

    # -- Credentialing & accreditation workflow engines (reference) ------
    # Labeled reference implementation (stub-engine): workflow,
    # evidence, and application records held as data. Credential
    # RECORDS stay Core; this surface records that a workflow step
    # or an application exists — it accredits nothing and issues
    # nothing. Every record carries ``reference_stub: True``.

    def create_accreditation_workflow(self, program_ref, standard_label,
                                      actor):
        """Record an accreditation workflow. Action: credential_write."""
        self._guard(actor, "credential_write", "ext_accreditation_workflow_create")
        _non_empty(program_ref, "program_ref")
        _non_empty(standard_label, "standard_label")
        with self._lock:
            record_id = self._next_id("acw")
            record = {
                "id": record_id,
                "program_ref": program_ref,
                "standard_label": standard_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._accreditation_workflows[record_id] = record
            self._audit(actor, "ext_accreditation_workflow_create", record_id,
                        details={"program_ref": program_ref})
            return dict(record)

    def record_workflow_evidence(self, workflow_id, evidence_ref, label,
                                 actor):
        """Record one evidence item against a workflow.

        Action: credential_write. ``evidence_ref`` is opaque; the
        evidence itself is never held here.
        """
        self._guard(actor, "credential_write", "ext_workflow_evidence_record")
        _non_empty(evidence_ref, "evidence_ref")
        _non_empty(label, "label")
        with self._lock:
            self._get(self._accreditation_workflows, workflow_id,
                      "accreditation workflow")
            record_id = self._next_id("awe")
            record = {
                "id": record_id,
                "workflow_id": workflow_id,
                "evidence_ref": evidence_ref,
                "label": label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._workflow_evidence[record_id] = record
            self._audit(actor, "ext_workflow_evidence_record", record_id,
                        details={"workflow_id": workflow_id})
            return dict(record)

    def record_credentialing_application(self, workflow_id, learner_id,
                                         credential_id, actor):
        """Record a credentialing application against a Core credential.

        Action: credential_write. The credential must be an existing
        core credential record held by ``learner_id``; the
        application is a record about the workflow, and changes no
        core record.
        """
        self._guard(actor, "credential_write",
                    "ext_credentialing_application_record")
        _non_empty(learner_id, "learner_id")
        with self._lock:
            self._get(self._accreditation_workflows, workflow_id,
                      "accreditation workflow")
            credential = self.store.get_credential(credential_id, actor=None)
            if credential["learner_id"] != learner_id:
                raise ValidationError(
                    "credential %r is not held by learner %r"
                    % (credential_id, learner_id))
            record_id = self._next_id("cra")
            record = {
                "id": record_id,
                "workflow_id": workflow_id,
                "learner_id": learner_id,
                "credential_id": credential_id,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._credentialing_applications[record_id] = record
            self._audit(actor, "ext_credentialing_application_record",
                        record_id,
                        details={"workflow_id": workflow_id,
                                 "learner_id": learner_id})
            return dict(record)

    def list_accreditation_workflows(self, actor=None, program_ref=None):
        """Return accreditation workflows. Action: credential_read."""
        self._maybe_require(actor, "credential_read")
        with self._lock:
            records = list(self._accreditation_workflows.values())
            if program_ref is not None:
                records = [r for r in records if r["program_ref"] == program_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_workflow_evidence(self, actor=None, workflow_id=None):
        """Return workflow evidence records. Action: credential_read."""
        self._maybe_require(actor, "credential_read")
        with self._lock:
            records = list(self._workflow_evidence.values())
            if workflow_id is not None:
                records = [r for r in records if r["workflow_id"] == workflow_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_credentialing_applications(self, actor=None, learner_id=None,
                                        workflow_id=None):
        """Return credentialing applications.

        Action: credential_read (+ learner scope).
        """
        self._maybe_require(actor, "credential_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._credentialing_applications.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if workflow_id is not None:
                records = [r for r in records if r["workflow_id"] == workflow_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Deterministic scoring & proficiency-rating engines --------------
    # Built in its records form only (DECISION.md re-judgment option
    # (a); grounds in BATCH.md). The founding doctrine — scoring was
    # claimed by no fork in this category, assessments are
    # administration records, and no score/grade field exists
    # anywhere in the build — binds this surface exactly as it binds
    # the core. What an "engine" can honestly be here:
    #
    # * scoring-RULE records: the text of a rule held as data
    #   (``method: recorded_rules_only``, ``applied_here: False``).
    #   Rules are never applied to any record by this substrate.
    # * reported-outcome records: an outcome — including a
    #   proficiency rating in Dossier's sense — recorded VERBATIM as
    #   reported by an external assessor against a core assessment
    #   record. Stored byte-for-byte, never parsed, never ranked,
    #   never converted into a number, never fed back into the core
    #   assessment record (which stays exactly as the core holds it).

    def create_scoring_rule(self, rule_ref, rule_text, actor, course_id=None):
        """Record a scoring rule as data. Action: assessment_write."""
        self._guard(actor, "assessment_write", "ext_scoring_rule_create")
        _non_empty(rule_ref, "rule_ref")
        _non_empty(rule_text, "rule_text")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            if any(r["rule_ref"] == rule_ref
                   for r in self._scoring_rules.values()):
                raise ValidationError("rule_ref %r already exists" % (rule_ref,))
            record_id = self._next_id("scr")
            record = {
                "id": record_id,
                "rule_ref": rule_ref,
                "rule_text": rule_text,
                "course_id": course_id,
                "method": "recorded_rules_only",
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scoring_rules[record_id] = record
            self._audit(actor, "ext_scoring_rule_create", record_id,
                        details={"rule_ref": rule_ref})
            return dict(record)

    def record_reported_outcome(self, assessment_id, reported_outcome, actor,
                                assessor_ref=None):
        """Record an outcome reported by an external assessor, verbatim.

        Action: assessment_write. The assessment must be an existing
        core assessment record. The outcome text is stored exactly
        as reported; this substrate computes nothing from it and the
        core assessment record is not modified.
        """
        self._guard(actor, "assessment_write", "ext_reported_outcome_record")
        _non_empty(reported_outcome, "reported_outcome")
        if assessor_ref is not None:
            _non_empty(assessor_ref, "assessor_ref")
        with self._lock:
            assessment = self.store.get_assessment(assessment_id, actor=None)
            record_id = self._next_id("rpo")
            record = {
                "id": record_id,
                "assessment_id": assessment_id,
                "learner_id": assessment["learner_id"],
                "reported_outcome": reported_outcome,
                "assessor_ref": assessor_ref,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reported_outcomes[record_id] = record
            self._audit(actor, "ext_reported_outcome_record", record_id,
                        details={"assessment_id": assessment_id})
            return dict(record)

    def list_scoring_rules(self, actor=None, course_id=None):
        """Return scoring-rule records. Action: assessment_read."""
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._scoring_rules.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_reported_outcomes(self, actor=None, assessment_id=None,
                               learner_id=None):
        """Return reported-outcome records.

        Action: assessment_read (+ learner scope).
        """
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._reported_outcomes.values())
            if assessment_id is not None:
                records = [r for r in records
                           if r["assessment_id"] == assessment_id]
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Recruiting/HCM suite --------------------------------------------
    # Records form: requisitions, candidates (opaque refs —
    # applicants need not be learners), applications with a recorded
    # stage, and onboarding records that may bind a core enrollment.
    # Pipeline views are counts derived at read. No external HRIS is
    # touched and no candidate is ranked or matched here (matching
    # is the separate entry below).

    def create_requisition(self, role_ref, title, actor):
        """Record a requisition. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_requisition_create")
        _non_empty(role_ref, "role_ref")
        _non_empty(title, "requisition title")
        with self._lock:
            record_id = self._next_id("rq")
            record = {
                "id": record_id,
                "role_ref": role_ref,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._requisitions[record_id] = record
            self._audit(actor, "ext_requisition_create", record_id,
                        details={"role_ref": role_ref})
            return dict(record)

    def create_candidate(self, candidate_ref, actor):
        """Record a candidate by opaque reference. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_candidate_create")
        _non_empty(candidate_ref, "candidate_ref")
        with self._lock:
            if any(c["candidate_ref"] == candidate_ref
                   for c in self._candidates.values()):
                raise ValidationError(
                    "candidate_ref %r already exists" % (candidate_ref,))
            record_id = self._next_id("cnd")
            record = {
                "id": record_id,
                "candidate_ref": candidate_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._candidates[record_id] = record
            self._audit(actor, "ext_candidate_create", record_id,
                        details={"candidate_ref": candidate_ref})
            return dict(record)

    def create_application(self, candidate_id, requisition_id, actor):
        """Record an application of a candidate to a requisition.

        Action: enrollment_write. The recorded stage starts at
        ``applied``; later stages are recorded transitions (data),
        not workflow execution.
        """
        self._guard(actor, "enrollment_write", "ext_application_create")
        with self._lock:
            self._get(self._candidates, candidate_id, "candidate")
            self._get(self._requisitions, requisition_id, "requisition")
            if any(a["candidate_id"] == candidate_id
                   and a["requisition_id"] == requisition_id
                   for a in self._applications.values()):
                raise ValidationError(
                    "candidate %r already has an application to requisition %r"
                    % (candidate_id, requisition_id))
            record_id = self._next_id("apl")
            record = {
                "id": record_id,
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "stage": "applied",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._applications[record_id] = record
            self._audit(actor, "ext_application_create", record_id,
                        details={"candidate_id": candidate_id,
                                 "requisition_id": requisition_id})
            return dict(record)

    def record_application_stage(self, application_id, stage, actor):
        """Record an application stage transition. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_application_stage_record")
        if stage not in APPLICATION_STAGES:
            raise ValidationError(
                "stage must be one of %s" % (", ".join(APPLICATION_STAGES),))
        with self._lock:
            record = self._get(self._applications, application_id, "application")
            record["stage"] = stage
            self._audit(actor, "ext_application_stage_record", application_id,
                        details={"stage": stage})
            return dict(record)

    def create_onboarding_record(self, application_id, actor,
                                 enrollment_id=None):
        """Record onboarding for a hired application.

        Action: enrollment_write. The application's recorded stage
        must be ``hired``; a core enrollment may be bound by id.
        """
        self._guard(actor, "enrollment_write", "ext_onboarding_create")
        with self._lock:
            application = self._get(self._applications, application_id,
                                    "application")
            if application["stage"] != "hired":
                raise ValidationError(
                    "onboarding requires an application at stage 'hired', "
                    "not %r" % (application["stage"],))
            if enrollment_id is not None:
                self.store.get_enrollment(enrollment_id, actor=None)
            record_id = self._next_id("onb")
            record = {
                "id": record_id,
                "application_id": application_id,
                "enrollment_id": enrollment_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._onboarding_records[record_id] = record
            self._audit(actor, "ext_onboarding_create", record_id,
                        details={"application_id": application_id})
            return dict(record)

    def list_requisitions(self, actor=None, role_ref=None):
        """Return requisitions. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = list(self._requisitions.values())
            if role_ref is not None:
                records = [r for r in records if r["role_ref"] == role_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_candidates(self, actor=None):
        """Return candidates. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = sorted(self._candidates.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_applications(self, actor=None, candidate_id=None,
                          requisition_id=None, stage=None):
        """Return applications, optionally filtered. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = list(self._applications.values())
            if candidate_id is not None:
                records = [r for r in records if r["candidate_id"] == candidate_id]
            if requisition_id is not None:
                records = [r for r in records
                           if r["requisition_id"] == requisition_id]
            if stage is not None:
                records = [r for r in records if r["stage"] == stage]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def recruiting_pipeline(self, actor):
        """Derived pipeline counts over the recruiting records.

        Action: report_read. Counts only — applications by recorded
        stage; no candidate is ranked, rated, or matched here.
        """
        self._guard(actor, "report_read", "ext_recruiting_pipeline")
        with self._lock:
            by_stage = {s: 0 for s in APPLICATION_STAGES}
            for application in self._applications.values():
                by_stage[application["stage"]] += 1
            return {
                "requisitions": len(self._requisitions),
                "candidates": len(self._candidates),
                "applications": len(self._applications),
                "applications_by_stage": by_stage,
                "onboarding_records": len(self._onboarding_records),
                "method": "deterministic_counts",
            }

    # -- Talent & marketplace matching ------------------------------------
    # Records plus a deterministic presence-match derivation: an
    # opportunity's required courses are matched when the learner
    # holds a COMPLETED core progress record for each. Nothing is
    # ranked and no fit value is computed — a match is a boolean
    # over held records, and the missing courses are listed as data
    # (``method: deterministic_presence_match``). The family stands
    # at 0 claimants in this set; the derivation is substrate logic
    # over the set's own records, claimed for no fork.

    def create_opportunity(self, org_ref, role_ref, required_course_ids,
                           actor):
        """Record a marketplace opportunity. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_opportunity_create")
        _non_empty(org_ref, "org_ref")
        _non_empty(role_ref, "role_ref")
        required_course_ids = _string_list(required_course_ids,
                                           "required_course_ids")
        with self._lock:
            for course_id in required_course_ids:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("opp")
            record = {
                "id": record_id,
                "org_ref": org_ref,
                "role_ref": role_ref,
                "required_course_ids": list(required_course_ids),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._opportunities[record_id] = record
            self._audit(actor, "ext_opportunity_create", record_id,
                        details={"org_ref": org_ref, "role_ref": role_ref})
            copied = dict(record)
            copied["required_course_ids"] = list(record["required_course_ids"])
            return copied

    def _completed_course_ids(self, learner_id):
        progress = self.store.list_progress(actor=None, learner_id=learner_id)
        return {p["course_id"] for p in progress if p["status"] == "completed"}

    def _opportunity_match_view(self, record, completed_ids):
        missing = [c for c in record["required_course_ids"]
                   if c not in completed_ids]
        view = dict(record)
        view["required_course_ids"] = list(record["required_course_ids"])
        view["missing_course_ids"] = missing
        view["fully_matched"] = not missing
        return view

    def match_opportunities_for_learner(self, learner_id, actor=None):
        """Derived opportunity matches for one learner.

        Action: progress_read (+ learner scope).
        """
        self._maybe_require(actor, "progress_read")
        self._scope_check(actor, learner_id)
        with self._lock:
            completed = self._completed_course_ids(learner_id)
            views = [self._opportunity_match_view(r, completed)
                     for r in sorted(self._opportunities.values(),
                                     key=lambda r: _id_num(r["id"]))]
            return {
                "learner_id": learner_id,
                "method": "deterministic_presence_match",
                "opportunities": views,
            }

    def match_learners_for_opportunity(self, opportunity_id, actor=None):
        """Derived list of learners fully matching one opportunity.

        Action: progress_read. The learner universe is the set of
        learner ids holding core progress records. A learner-role
        actor sees only their own entry, per learner scope.
        """
        self._maybe_require(actor, "progress_read")
        with self._lock:
            record = self._get(self._opportunities, opportunity_id,
                               "opportunity")
            learner_ids = sorted({p["learner_id"] for p in
                                  self.store.list_progress(actor=None)})
            matched = []
            for learner_id in learner_ids:
                completed = self._completed_course_ids(learner_id)
                if all(c in completed for c in record["required_course_ids"]):
                    matched.append(learner_id)
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                matched = [m for m in matched if m == name]
            return {
                "opportunity_id": opportunity_id,
                "method": "deterministic_presence_match",
                "matched_learner_ids": matched,
            }

    def list_opportunities(self, actor=None, org_ref=None):
        """Return opportunity records. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = list(self._opportunities.values())
            if org_ref is not None:
                records = [r for r in records if r["org_ref"] == org_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            result = []
            for record in records:
                copied = dict(record)
                copied["required_course_ids"] = list(
                    record["required_course_ids"])
                result.append(copied)
            return result

    # -- Remote proctoring & identity proofing (reference) ----------------
    # Labeled reference implementation (stub-engine), and at 0
    # claimants in this set. Records of sessions and outcomes as
    # reported by an external provider, stored verbatim. Per
    # PLATFORM-LAYER.md decision 1, identity proofing stays with the
    # embedding organization: these records are not identity
    # evidence, make no decision (``decision_made: False``), and
    # this substrate is not an identity provider
    # (``identity_provider: False``). Nothing is monitored here.

    def create_proctoring_record(self, assessment_id, provider_ref, actor):
        """Record a proctoring session against a core assessment.

        Action: assessment_write.
        """
        self._guard(actor, "assessment_write", "ext_proctoring_record_create")
        _non_empty(provider_ref, "provider_ref")
        with self._lock:
            assessment = self.store.get_assessment(assessment_id, actor=None)
            record_id = self._next_id("prc")
            record = {
                "id": record_id,
                "assessment_id": assessment_id,
                "learner_id": assessment["learner_id"],
                "provider_ref": provider_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "decision_made": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._proctoring_records[record_id] = record
            self._audit(actor, "ext_proctoring_record_create", record_id,
                        details={"assessment_id": assessment_id})
            return dict(record)

    def record_proofing_outcome(self, learner_id, provider_ref,
                                reported_outcome, actor):
        """Record an identity-proofing outcome as reported, verbatim.

        Action: assessment_write. The outcome is the provider's
        report, stored as data; this substrate performs no proofing
        and decides nothing from it.
        """
        self._guard(actor, "assessment_write", "ext_proofing_outcome_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(provider_ref, "provider_ref")
        _non_empty(reported_outcome, "reported_outcome")
        with self._lock:
            record_id = self._next_id("prf")
            record = {
                "id": record_id,
                "learner_id": learner_id,
                "provider_ref": provider_ref,
                "reported_outcome": reported_outcome,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "decision_made": False,
                "identity_provider": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._proofing_records[record_id] = record
            self._audit(actor, "ext_proofing_outcome_record", record_id,
                        details={"learner_id": learner_id})
            return dict(record)

    def list_proctoring_records(self, actor=None, assessment_id=None,
                                learner_id=None):
        """Return proctoring records. Action: assessment_read (+ scope)."""
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._proctoring_records.values())
            if assessment_id is not None:
                records = [r for r in records
                           if r["assessment_id"] == assessment_id]
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    def list_proofing_records(self, actor=None, learner_id=None):
        """Return proofing records. Action: assessment_read (+ scope)."""
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._proofing_records.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Hosting / multi-tenancy platform layer (reference) ---------------
    # Labeled reference implementation (stub-engine), following the
    # entry's drafted disposition. Per PLATFORM-LAYER.md decision 6,
    # a fork's hosting substrate does not transfer to the build and
    # multi-tenancy is a deployment property: what lands here is a
    # deployment-posture RECORD (labels held as data,
    # ``multi_tenant_here: False``) and a derived summary that states
    # plainly what the merged build is — a single-tenant reference
    # deployment. Nothing is hosted by recording a record.

    def create_deployment_record(self, deployment_ref, tenancy_label, actor,
                                 region_label=""):
        """Record a deployment posture. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_deployment_record_create")
        _non_empty(deployment_ref, "deployment_ref")
        _non_empty(tenancy_label, "tenancy_label")
        _string(region_label, "region_label")
        with self._lock:
            if any(r["deployment_ref"] == deployment_ref
                   for r in self._deployment_records.values()):
                raise ValidationError(
                    "deployment_ref %r already exists" % (deployment_ref,))
            record_id = self._next_id("dep")
            record = {
                "id": record_id,
                "deployment_ref": deployment_ref,
                "tenancy_label": tenancy_label,
                "region_label": region_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "multi_tenant_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deployment_records[record_id] = record
            self._audit(actor, "ext_deployment_record_create", record_id,
                        details={"deployment_ref": deployment_ref})
            return dict(record)

    def list_deployment_records(self, actor=None):
        """Return deployment records. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = sorted(self._deployment_records.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def deployment_summary(self, actor=None):
        """Derived deployment-posture summary. Action: catalog_read.

        States the build's own posture plainly, whatever records
        exist: this merged build is a single-tenant reference
        deployment; recorded fork postures are data about the forks,
        not properties of the build.
        """
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            return {
                "deployment_records": len(self._deployment_records),
                "build_tenancy": "single_tenant_reference",
                "method": "recorded_deployment_posture",
            }
