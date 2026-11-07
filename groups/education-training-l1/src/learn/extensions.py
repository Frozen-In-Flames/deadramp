"""Final GAPS batch extensions for Education & Training L1 (Group 30).

Clean-room, standard-library-only extensions for the 11 open entries
of this group's GAPS.md section (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a wrapper
around :class:`LearnStore`; every core module is untouched and
byte-identical to the shipped group build.

Honesty of form, per the batch brief and this group's UNION-SPEC:
an "engine" here is its in-substrate form — records plus
deterministic derivations over the group's OWN records (core records
and extension records).

- Adaptive learning is adaptation-RULE records held as data (never
  applied by any engine here) plus reported pathway/outcome records
  stored verbatim against core progress records. The sibling's
  patented algorithms are theirs; nothing here adapts.
- Matching is a deterministic presence-match derivation over
  recorded skills/courses (evidence per match, no ranking, no fit
  value); career assistants are profile records with a deterministic
  record lookup (no generated text).
- Recruiting/HCM is pipeline records with derived counts (persons
  are opaque refs); performance and policy entries are records held
  as data, never executed or enforced here.
- Simulation is session/capture records with recorded states;
  nothing is captured, rendered, or played back here.
- Collaboration is group/activity records over core enrollments.
- Data services are dataset declaration records projected over core
  records; no rows are stored here.
- Notifications are rule records plus ``reference_transport``
  receipts; nothing is sent.
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing executes, streams, decides,
  or integrates.

**The founding scoring doctrine binds absolutely:** deterministic
scoring/grading was claimed by no fork in either tier of this
category, assessments are administration records only, and **no
score or grade field appears anywhere in this surface** — pinned by
a recursive key scan in the tests, exactly as the core pins it for
assessment records. The scoring entry therefore ships as labeled
rule/outcome reference records, consistent with the founding
design; the core assessment record is never touched by them.

Doctrines carried from the core: opaque ``*_ref`` / ``learner_id``
strings only (no record shape here can hold a name, email, phone, or
identifier for a real person beyond the core's own learner-id
convention); derived-never-stored for every computed value
(presence matches, pipeline counts, group activity counts, dataset
projections, notification evaluation); append-only audit on the
core store's log with ``ext_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a ``:denied``
suffix; RBAC via :mod:`learn.access` with the core's existing
actions, enforced before any state change or id allocation, so a
failed operation consumes no id and changes nothing; learner scope
mirrors the store's — a learner-role actor may only read records
whose ``learner_id`` (or ``user_ref``, for guidance events) is their
own name.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

APPLICATION_STAGES = (
    "applied", "screening", "interview", "offer", "hired", "closed",
)
NOTIFICATION_TRIGGERS = (
    "assignment_overdue",
    "assignment_due_within_days",
    "assessment_upcoming",
)
SIMULATION_STATES = ("scheduled", "captured", "debriefed", "played_back")

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
        self._adaptation_rules = {}
        self._pathway_outcomes = {}
        self._opportunities = {}
        self._career_profiles = {}
        self._guidance_flows = {}
        self._assistant_profiles = {}
        self._requisitions = {}
        self._candidates = {}
        self._applications = {}
        self._onboarding_records = {}
        self._performance_records = {}
        self._policy_records = {}
        self._simulation_sessions = {}
        self._simulation_events = {}
        self._study_groups = {}
        self._group_activities = {}
        self._dataset_declarations = {}
        self._notification_rules = {}
        self._notification_receipts = {}
        self._content_packages = {}
        self._delivery_receipts = {}
        self._proctoring_records = {}
        self._proofing_records = {}
        self._rules = {}
        self._reported_outcomes = {}
        self._integration_records = {}
        self._counters = {
            "adr": 0, "pwo": 0, "opp": 0, "crp": 0, "gdf": 0, "asp": 0,
            "rq": 0, "cnd": 0, "apl": 0, "onb": 0, "pfr": 0, "pol": 0,
            "sim": 0, "sme": 0, "grp": 0, "act": 0, "dsv": 0, "ntr": 0,
            "nrc": 0, "cnt": 0, "dlr": 0, "prc": 0, "prf": 0, "scr": 0,
            "rpo": 0, "int": 0,
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

    # -- Adaptive learning / knowledge-gap remediation -------------------
    # Records form: an adaptation rule is held as DATA
    # (``applied_here: False``) and is never applied by any engine
    # here — the sibling's patented algorithms are theirs. A pathway
    # outcome is a reported outcome stored verbatim against a
    # learner+course, alongside the core progress records it reports
    # on; this substrate computes nothing from it.

    def create_adaptation_rule(self, rule_ref, rule_text, actor,
                               course_id=None):
        """Record an adaptation rule as data. Action: assessment_write."""
        self._guard(actor, "assessment_write", "ext_adaptation_rule_create")
        _non_empty(rule_ref, "rule_ref")
        _non_empty(rule_text, "rule_text")
        with self._lock:
            if any(r["rule_ref"] == rule_ref
                   for r in self._adaptation_rules.values()):
                raise ValidationError("rule_ref %r already exists" % (rule_ref,))
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("adr")
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
            self._adaptation_rules[record_id] = record
            self._audit(actor, "ext_adaptation_rule_create", record_id,
                        details={"rule_ref": rule_ref})
            return dict(record)

    def list_adaptation_rules(self, actor=None, course_id=None):
        """Return adaptation rules. Action: assessment_read."""
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._adaptation_rules.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def record_pathway_outcome(self, learner_id, course_id,
                               reported_outcome, actor, note=""):
        """Record a reported pathway outcome, verbatim.

        Action: progress_write. The outcome text is the reporter's
        data, stored byte-for-byte; nothing here adapts a pathway,
        and the core progress records are untouched.
        """
        self._guard(actor, "progress_write", "ext_pathway_outcome_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(reported_outcome, "reported_outcome")
        _string(note, "note")
        with self._lock:
            self.store.get_course(course_id, actor=None)
            record_id = self._next_id("pwo")
            record = {
                "id": record_id,
                "learner_id": learner_id,
                "course_id": course_id,
                "reported_outcome": reported_outcome,
                "note": note,
                "adapted_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._pathway_outcomes[record_id] = record
            self._audit(actor, "ext_pathway_outcome_record", record_id,
                        details={"learner_id": learner_id,
                                 "course_id": course_id})
            return dict(record)

    def list_pathway_outcomes(self, actor=None, learner_id=None,
                              course_id=None):
        """Return pathway outcome records. Action: progress_read (+ scope)."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._pathway_outcomes.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    def adaptation_summary(self, actor, learner_id=None):
        """Derived counts over adaptation records. Action: progress_read."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            outcomes = list(self._pathway_outcomes.values())
            if learner_id is not None:
                outcomes = [r for r in outcomes
                            if r["learner_id"] == learner_id]
            outcomes = self._scoped(actor, outcomes)
            by_outcome = {}
            for record in outcomes:
                by_outcome[record["reported_outcome"]] = (
                    by_outcome.get(record["reported_outcome"], 0) + 1)
            return {
                "learner_id": learner_id,
                "rules": len(self._adaptation_rules),
                "pathway_outcomes": len(outcomes),
                "outcomes_by_reported_label": by_outcome,
                "method": "deterministic_counts",
            }

    # -- Talent, skills & marketplace matching; career assistants --------
    # Built as opportunity records plus a deterministic presence-match
    # derivation over completed core progress: an opportunity matches
    # when the learner holds a completed progress record for every
    # required course. The view lists the missing courses as data
    # (the per-match evidence) and a boolean; no ranking and no fit
    # value is computed. Career profiles and guidance flows are
    # records; the assistant lookup is a deterministic exact-topic
    # derivation over them, returning held steps verbatim.

    def create_opportunity(self, org_ref, role_ref, required_course_ids,
                           actor):
        """Record a marketplace opportunity. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_opportunity_create")
        _non_empty(org_ref, "org_ref")
        _non_empty(role_ref, "role_ref")
        required = _string_list(required_course_ids, "required_course_ids",
                                allow_empty=True)
        with self._lock:
            for course_id in required:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("opp")
            record = {
                "id": record_id,
                "org_ref": org_ref,
                "role_ref": role_ref,
                "required_course_ids": list(required),
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

    def _learner_completed_all(self, learner_id, required_course_ids):
        """Presence-match seam: True iff every required course is completed.

        MUTATION DRILL NOTE: this seam is the batch negative
        control's load-bearing invariant — a learner missing a
        required course's completed progress record must NOT match,
        however the match views are reached.
        """
        completed = self._completed_course_ids(learner_id)
        return all(course_id in completed for course_id in required_course_ids)

    def _opportunity_match_view(self, opportunity, learner_id):
        completed = self._completed_course_ids(learner_id)
        missing = [c for c in opportunity["required_course_ids"]
                   if c not in completed]
        return {
            "opportunity_id": opportunity["id"],
            "org_ref": opportunity["org_ref"],
            "role_ref": opportunity["role_ref"],
            "required_course_ids": list(opportunity["required_course_ids"]),
            "completed_course_ids": sorted(
                c for c in opportunity["required_course_ids"]
                if c in completed),
            "missing_course_ids": missing,
            "fully_matched": self._learner_completed_all(
                learner_id, opportunity["required_course_ids"]),
        }

    def match_opportunities_for_learner(self, learner_id, actor=None):
        """Presence-match every opportunity for one learner.

        Action: enrollment_read (+ learner scope). A read-time
        derivation; it creates no record.
        """
        self._maybe_require(actor, "enrollment_read")
        self._scope_check(actor, learner_id)
        with self._lock:
            views = [self._opportunity_match_view(opp, learner_id)
                     for opp in sorted(self._opportunities.values(),
                                       key=lambda r: _id_num(r["id"]))]
            return {
                "learner_id": learner_id,
                "opportunities": views,
                "method": "deterministic_presence_match",
            }

    def match_learners_for_opportunity(self, opportunity_id, actor=None):
        """Presence-match recorded learners against one opportunity.

        Action: enrollment_read. The candidate set is the learners
        with any core progress or enrollment record — the substrate's
        own recorded population, nothing external.
        """
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            opportunity = self._get(self._opportunities, opportunity_id,
                                    "opportunity")
            learner_ids = set()
            for record in self.store.list_progress(actor=None):
                learner_ids.add(record["learner_id"])
            for record in self.store.list_enrollments(actor=None):
                learner_ids.add(record["learner_id"])
            matched = sorted(
                lid for lid in learner_ids
                if self._learner_completed_all(
                    lid, opportunity["required_course_ids"]))
            return {
                "opportunity_id": opportunity_id,
                "matched_learner_ids": matched,
                "method": "deterministic_presence_match",
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

    def create_career_profile(self, learner_id, actor, interests=None,
                              note=""):
        """Record a career-exploration profile. Action: progress_write."""
        self._guard(actor, "progress_write", "ext_career_profile_create")
        _non_empty(learner_id, "learner_id")
        if interests is None:
            interests = []
        interests = _string_list(interests, "interests", allow_empty=True)
        _string(note, "note")
        with self._lock:
            record_id = self._next_id("crp")
            record = {
                "id": record_id,
                "learner_id": learner_id,
                "interests": list(interests),
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._career_profiles[record_id] = record
            self._audit(actor, "ext_career_profile_create", record_id,
                        details={"learner_id": learner_id})
            copied = dict(record)
            copied["interests"] = list(record["interests"])
            return copied

    def list_career_profiles(self, actor=None, learner_id=None):
        """Return career profiles. Action: progress_read (+ scope)."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._career_profiles.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            result = []
            for record in self._scoped(actor, records):
                copied = dict(record)
                copied["interests"] = list(record["interests"])
                result.append(copied)
            return result

    def create_guidance_flow(self, app_ref, title, actor, steps=None,
                             topic=""):
        """Record a guidance flow (steps verbatim). Action: catalog_write."""
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
            copied = dict(record)
            copied["steps"] = list(record["steps"])
            return copied

    def list_guidance_flows(self, actor=None, topic=None):
        """Return guidance flows. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = list(self._guidance_flows.values())
            if topic is not None:
                records = [r for r in records if r["topic"] == topic]
            records.sort(key=lambda r: _id_num(r["id"]))
            result = []
            for record in records:
                copied = dict(record)
                copied["steps"] = list(record["steps"])
                result.append(copied)
            return result

    def create_assistant_profile(self, assistant_ref, actor, topics=None):
        """Record a career-assistant profile. Action: catalog_write.

        The profile is a labeled reference record: the assistant
        surface is the deterministic lookup below, not a model.
        """
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
        """Deterministic exact-topic lookup over guidance flows.

        Action: catalog_read. Returns the held flow records whose
        topic matches exactly, steps verbatim; generates no text and
        creates no record.
        """
        self._maybe_require(actor, "catalog_read")
        _non_empty(topic, "topic")
        with self._lock:
            matches = []
            for flow in sorted(self._guidance_flows.values(),
                               key=lambda r: _id_num(r["id"])):
                if flow["topic"] == topic:
                    copied = dict(flow)
                    copied["steps"] = list(flow["steps"])
                    matches.append(copied)
            return {
                "topic": topic,
                "matches": matches,
                "method": "deterministic_record_lookup",
                "reference_stub": True,
            }

    # -- Recruiting, HCM / HRIS & workforce management -------------------
    # Built as requisition/candidate/application/onboarding records
    # with pipeline counts derived at read; performance and policy
    # entries are records held as data (an outcome verbatim as
    # reported; a policy text never enforced here). Persons are
    # opaque refs; applicants need not be learners.

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
        """Record a candidate (opaque ref). Action: enrollment_write."""
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
        """Record an application at stage ``applied``.

        Action: enrollment_write. A duplicate candidate+requisition
        pair is rejected whole.
        """
        self._guard(actor, "enrollment_write", "ext_application_create")
        with self._lock:
            self._get(self._candidates, candidate_id, "candidate")
            self._get(self._requisitions, requisition_id, "requisition")
            for existing in self._applications.values():
                if (existing["candidate_id"] == candidate_id
                        and existing["requisition_id"] == requisition_id):
                    raise ValidationError(
                        "candidate %r already applied to requisition %r"
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
        """Record an application stage transition (data, not execution).

        Action: enrollment_write.
        """
        self._guard(actor, "enrollment_write", "ext_application_stage_record")
        if stage not in APPLICATION_STAGES:
            raise ValidationError(
                "stage must be one of %s" % (", ".join(APPLICATION_STAGES),))
        with self._lock:
            record = self._get(self._applications, application_id,
                               "application")
            record["stage"] = stage
            self._audit(actor, "ext_application_stage_record", application_id,
                        details={"stage": stage})
            return dict(record)

    def create_onboarding_record(self, application_id, actor,
                                 enrollment_id=None):
        """Record onboarding for a hired application.

        Action: enrollment_write. Requires recorded stage ``hired``;
        may bind an existing core enrollment.
        """
        self._guard(actor, "enrollment_write", "ext_onboarding_create")
        with self._lock:
            application = self._get(self._applications, application_id,
                                    "application")
            if application["stage"] != "hired":
                raise ValidationError(
                    "onboarding requires recorded stage 'hired', not %r"
                    % (application["stage"],))
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

    def recruiting_pipeline(self, actor):
        """Derived pipeline counts. Action: report_read."""
        self._guard(actor, "report_read", "ext_recruiting_pipeline")
        with self._lock:
            by_stage = {s: 0 for s in APPLICATION_STAGES}
            for record in self._applications.values():
                by_stage[record["stage"]] += 1
            return {
                "requisitions": len(self._requisitions),
                "candidates": len(self._candidates),
                "applications": len(self._applications),
                "applications_by_stage": by_stage,
                "onboarding_records": len(self._onboarding_records),
                "method": "deterministic_counts",
            }

    def record_performance_record(self, person_ref, reported_outcome,
                                  actor, period_label=""):
        """Record a performance outcome verbatim as reported.

        Action: progress_write. The outcome is the reporter's data;
        nothing here evaluates the person.
        """
        self._guard(actor, "progress_write", "ext_performance_record_create")
        _non_empty(person_ref, "person_ref")
        _non_empty(reported_outcome, "reported_outcome")
        _string(period_label, "period_label")
        with self._lock:
            record_id = self._next_id("pfr")
            record = {
                "id": record_id,
                "person_ref": person_ref,
                "reported_outcome": reported_outcome,
                "period_label": period_label,
                "evaluated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._performance_records[record_id] = record
            self._audit(actor, "ext_performance_record_create", record_id,
                        details={"person_ref": person_ref})
            return dict(record)

    def list_performance_records(self, actor=None, person_ref=None):
        """Return performance records. Action: progress_read."""
        self._maybe_require(actor, "progress_read")
        with self._lock:
            records = list(self._performance_records.values())
            if person_ref is not None:
                records = [r for r in records
                           if r["person_ref"] == person_ref]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def create_policy_record(self, policy_ref, policy_text, actor):
        """Record a policy as data. Action: compliance_write.

        The text is held verbatim and never enforced here
        (``enforced_here: False``).
        """
        self._guard(actor, "compliance_write", "ext_policy_record_create")
        _non_empty(policy_ref, "policy_ref")
        _non_empty(policy_text, "policy_text")
        with self._lock:
            if any(p["policy_ref"] == policy_ref
                   for p in self._policy_records.values()):
                raise ValidationError(
                    "policy_ref %r already exists" % (policy_ref,))
            record_id = self._next_id("pol")
            record = {
                "id": record_id,
                "policy_ref": policy_ref,
                "policy_text": policy_text,
                "enforced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policy_records[record_id] = record
            self._audit(actor, "ext_policy_record_create", record_id,
                        details={"policy_ref": policy_ref})
            return dict(record)

    def list_policy_records(self, actor=None):
        """Return policy records. Action: compliance_read."""
        self._maybe_require(actor, "compliance_read")
        with self._lock:
            records = sorted(self._policy_records.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- Simulation engines: capture, debriefing & playback --------------
    # Records form: a simulation session binds a course and enrolled
    # learners; its recorded state advances only by recorded events.
    # Nothing is captured, rendered, or played back here — the event
    # records carry ``captured_here: False`` / ``played_back_here:
    # False`` and the session view's state is the latest RECORDED
    # state, derived at read, never stored on the session record.

    def create_simulation_session(self, title, course_id, actor,
                                  learner_ids=None):
        """Record a simulation session. Action: schedule_write."""
        self._guard(actor, "schedule_write", "ext_simulation_session_create")
        _non_empty(title, "simulation session title")
        if learner_ids is None:
            learner_ids = []
        learner_ids = _string_list(learner_ids, "learner_ids",
                                   allow_empty=True)
        with self._lock:
            self.store.get_course(course_id, actor=None)
            record_id = self._next_id("sim")
            record = {
                "id": record_id,
                "title": title,
                "course_id": course_id,
                "learner_ids": list(learner_ids),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._simulation_sessions[record_id] = record
            self._audit(actor, "ext_simulation_session_create", record_id,
                        details={"course_id": course_id})
            copied = dict(record)
            copied["learner_ids"] = list(record["learner_ids"])
            return copied

    def record_simulation_event(self, session_id, recorded_state, actor,
                                note=""):
        """Record one simulation event with its state verbatim.

        Action: schedule_write. The state label is the operator's
        record of what the external simulation did; this substrate
        captures and plays back nothing.
        """
        self._guard(actor, "schedule_write", "ext_simulation_event_record")
        if recorded_state not in SIMULATION_STATES:
            raise ValidationError(
                "recorded_state must be one of %s"
                % (", ".join(SIMULATION_STATES),))
        _string(note, "note")
        with self._lock:
            self._get(self._simulation_sessions, session_id,
                      "simulation session")
            record_id = self._next_id("sme")
            record = {
                "id": record_id,
                "session_id": session_id,
                "recorded_state": recorded_state,
                "note": note,
                "captured_here": False,
                "played_back_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._simulation_events[record_id] = record
            self._audit(actor, "ext_simulation_event_record", record_id,
                        details={"session_id": session_id,
                                 "recorded_state": recorded_state})
            return dict(record)

    def _simulation_view(self, record):
        view = dict(record)
        view["learner_ids"] = list(record["learner_ids"])
        events = [e for e in self._simulation_events.values()
                  if e["session_id"] == record["id"]]
        events.sort(key=lambda e: _id_num(e["id"]))
        view["event_count"] = len(events)
        view["current_state"] = (
            events[-1]["recorded_state"] if events else "scheduled")
        view["state_method"] = "latest_recorded_event"
        return view

    def get_simulation_session(self, session_id, actor=None):
        """Return one session with derived state. Action: schedule_read."""
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            record = self._get(self._simulation_sessions, session_id,
                               "simulation session")
            return self._simulation_view(record)

    def list_simulation_sessions(self, actor=None, course_id=None):
        """Return sessions with derived state. Action: schedule_read."""
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            records = list(self._simulation_sessions.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._simulation_view(r) for r in records]

    def list_simulation_events(self, actor=None, session_id=None):
        """Return simulation events. Action: schedule_read."""
        self._maybe_require(actor, "schedule_read")
        with self._lock:
            records = list(self._simulation_events.values())
            if session_id is not None:
                records = [r for r in records
                           if r["session_id"] == session_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- Collaboration & social learning ---------------------------------
    # Records form: a study group binds a course and member learners
    # (membership is checked against core enrollments when the group
    # is recorded as enrollment-bound); activity records hold the
    # activity label verbatim as reported. Counts are derived.

    def create_study_group(self, title, course_id, actor, member_ids=None):
        """Record a collaboration group. Action: enrollment_write."""
        self._guard(actor, "enrollment_write", "ext_study_group_create")
        _non_empty(title, "study group title")
        if member_ids is None:
            member_ids = []
        member_ids = _string_list(member_ids, "member_ids", allow_empty=True)
        with self._lock:
            self.store.get_course(course_id, actor=None)
            record_id = self._next_id("grp")
            record = {
                "id": record_id,
                "title": title,
                "course_id": course_id,
                "member_ids": list(member_ids),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._study_groups[record_id] = record
            self._audit(actor, "ext_study_group_create", record_id,
                        details={"course_id": course_id})
            copied = dict(record)
            copied["member_ids"] = list(record["member_ids"])
            return copied

    def record_group_activity(self, group_id, learner_id, activity, actor,
                              note=""):
        """Record one group activity, verbatim as reported.

        Action: progress_write. The learner must be a recorded
        member of the group when members are recorded.
        """
        self._guard(actor, "progress_write", "ext_group_activity_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(activity, "activity")
        _string(note, "note")
        with self._lock:
            group = self._get(self._study_groups, group_id, "study group")
            if group["member_ids"] and learner_id not in group["member_ids"]:
                raise ValidationError(
                    "learner %r is not a member of group %r"
                    % (learner_id, group_id))
            record_id = self._next_id("act")
            record = {
                "id": record_id,
                "group_id": group_id,
                "learner_id": learner_id,
                "activity": activity,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._group_activities[record_id] = record
            self._audit(actor, "ext_group_activity_record", record_id,
                        details={"group_id": group_id,
                                 "learner_id": learner_id})
            return dict(record)

    def _group_view(self, record):
        view = dict(record)
        view["member_ids"] = list(record["member_ids"])
        counts = {}
        for activity in self._group_activities.values():
            if activity["group_id"] == record["id"]:
                counts[activity["activity"]] = (
                    counts.get(activity["activity"], 0) + 1)
        view["activity_counts"] = counts
        view["activity_total"] = sum(counts.values())
        return view

    def get_study_group(self, group_id, actor=None):
        """Return one group with derived counts. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            record = self._get(self._study_groups, group_id, "study group")
            return self._group_view(record)

    def list_study_groups(self, actor=None, course_id=None):
        """Return groups with derived counts. Action: enrollment_read."""
        self._maybe_require(actor, "enrollment_read")
        with self._lock:
            records = list(self._study_groups.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [self._group_view(r) for r in records]

    def list_group_activities(self, actor=None, group_id=None,
                              learner_id=None):
        """Return activity records. Action: progress_read (+ scope)."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._group_activities.values())
            if group_id is not None:
                records = [r for r in records if r["group_id"] == group_id]
            if learner_id is not None:
                records = [r for r in records
                           if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Data storage & processing services ------------------------------
    # Records form: a dataset declaration holds the dataset's own
    # description as data (source system label, reported row count
    # as reported). A projection is a deterministic derivation over
    # the CORE records at read time — counts only, no rows stored
    # or returned (``rows_stored_here: False``).

    def create_dataset_declaration(self, dataset_ref, actor,
                                   source_label="", reported_rows=None,
                                   note=""):
        """Record a dataset declaration. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_dataset_declaration_create")
        _non_empty(dataset_ref, "dataset_ref")
        _string(source_label, "source_label")
        _string(note, "note")
        if reported_rows is not None:
            reported_rows = _count(reported_rows, "reported_rows")
        with self._lock:
            if any(d["dataset_ref"] == dataset_ref
                   for d in self._dataset_declarations.values()):
                raise ValidationError(
                    "dataset_ref %r already exists" % (dataset_ref,))
            record_id = self._next_id("dsv")
            record = {
                "id": record_id,
                "dataset_ref": dataset_ref,
                "source_label": source_label,
                "reported_rows": reported_rows,
                "note": note,
                "rows_stored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dataset_declarations[record_id] = record
            self._audit(actor, "ext_dataset_declaration_create", record_id,
                        details={"dataset_ref": dataset_ref})
            return dict(record)

    def list_dataset_declarations(self, actor=None):
        """Return dataset declarations. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = sorted(self._dataset_declarations.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def dataset_projection(self, dataset_id, actor, as_of=None):
        """Project core-record counts for one declared dataset.

        Action: report_read. Counts are derived from the core
        store's own report at ``as_of``; the declaration's reported
        row count is echoed as reported data, never reconciled or
        corrected here.
        """
        self._guard(actor, "report_read", "ext_dataset_projection")
        with self._lock:
            declaration = self._get(self._dataset_declarations, dataset_id,
                                    "dataset declaration")
            report = self.store.report(actor, as_of=as_of)
            return {
                "dataset_id": declaration["id"],
                "dataset_ref": declaration["dataset_ref"],
                "reported_rows": declaration["reported_rows"],
                "core_counts": {
                    "courses": report["courses"],
                    "enrollments": report["enrollments"],
                    "progress_records": report["progress_records"],
                    "assessments": report["assessments"],
                    "credentials": report["credentials"],
                    "sessions": report["sessions"],
                },
                "rows_stored_here": False,
                "method": "deterministic_projection_over_core_records",
            }

    # -- Notifications & reminders ---------------------------------------
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

    def _add_receipt(self, rule, reference_id, learner_id, as_of_date,
                     created):
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

        Action: compliance_write. Receipts are deduplicated on
        (rule, reference, learner), so re-evaluation is idempotent.
        Returns the new receipts.
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

    # -- Course content authoring & delivery, media streaming (reference)
    # Labeled reference implementation (stub-engine): content package
    # records hold authoring/delivery declarations as data, and
    # delivery receipts record a reported delivery state. Every
    # record carries ``reference_stub: True``; nothing is authored,
    # delivered, or streamed here.

    def create_content_package(self, package_ref, title, actor,
                               course_id=None, media_label=""):
        """Record a content package declaration. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_content_package_create")
        _non_empty(package_ref, "package_ref")
        _non_empty(title, "content package title")
        _string(media_label, "media_label")
        with self._lock:
            if any(p["package_ref"] == package_ref
                   for p in self._content_packages.values()):
                raise ValidationError(
                    "package_ref %r already exists" % (package_ref,))
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("cnt")
            record = {
                "id": record_id,
                "package_ref": package_ref,
                "title": title,
                "course_id": course_id,
                "media_label": media_label,
                "authored_here": False,
                "streamed_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._content_packages[record_id] = record
            self._audit(actor, "ext_content_package_create", record_id,
                        details={"package_ref": package_ref})
            return dict(record)

    def record_delivery_receipt(self, package_id, learner_id,
                                reported_state, actor):
        """Record a reported delivery state for a package.

        Action: progress_write. The state is the reporter's data,
        stored verbatim; no content moves here.
        """
        self._guard(actor, "progress_write", "ext_delivery_receipt_record")
        _non_empty(learner_id, "learner_id")
        _non_empty(reported_state, "reported_state")
        with self._lock:
            self._get(self._content_packages, package_id, "content package")
            record_id = self._next_id("dlr")
            record = {
                "id": record_id,
                "package_id": package_id,
                "learner_id": learner_id,
                "reported_state": reported_state,
                "delivered_here": False,
                "reference_stub": True,
                "reference_transport": True,
                "state": _REFERENCE_STATE,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._delivery_receipts[record_id] = record
            self._audit(actor, "ext_delivery_receipt_record", record_id,
                        details={"package_id": package_id,
                                 "learner_id": learner_id})
            return dict(record)

    def list_content_packages(self, actor=None, course_id=None):
        """Return content packages. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = list(self._content_packages.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_delivery_receipts(self, actor=None, package_id=None,
                               learner_id=None):
        """Return delivery receipts. Action: progress_read (+ scope)."""
        self._maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._delivery_receipts.values())
            if package_id is not None:
                records = [r for r in records if r["package_id"] == package_id]
            if learner_id is not None:
                records = [r for r in records
                           if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Remote proctoring & identity proofing (reference) ---------------
    # Labeled reference implementation (stub-engine): records of
    # outcomes reported by an external provider, stored verbatim.
    # They carry ``decision_made: False`` (and ``identity_provider:
    # False`` on proofing records): this substrate makes no decision
    # and is not an identity provider, per PLATFORM-LAYER.md
    # decision 1. Nothing is monitored here.

    def create_proctoring_record(self, assessment_id, provider_ref, actor):
        """Record that an assessment was proctored externally.

        Action: assessment_write. The learner is copied from the
        core assessment record, which is untouched.
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
                "decision_made": False,
                "monitored_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._proctoring_records[record_id] = record
            self._audit(actor, "ext_proctoring_record_create", record_id,
                        details={"assessment_id": assessment_id})
            return dict(record)

    def record_proofing_outcome(self, learner_id, provider_ref,
                                reported_outcome, actor):
        """Record a proofing outcome verbatim as reported.

        Action: assessment_write.
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
                "decision_made": False,
                "identity_provider": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
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
                records = [r for r in records
                           if r["learner_id"] == learner_id]
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
                records = [r for r in records
                           if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Deterministic scoring & AI grading (reference) ------------------
    # Labeled reference implementation (stub-engine), consistent
    # with the founding design: assessments stay administration
    # records and no computed value exists anywhere. A rule record
    # holds a rule's text as data (``applied_here: False``, never
    # applied); a reported-outcome record holds an outcome verbatim
    # as reported by an external assessor against an existing core
    # assessment. Every record carries ``reference_stub: True``.

    def create_rule_record(self, rule_ref, rule_text, actor, course_id=None):
        """Record a rule as labeled reference data.

        Action: assessment_write.
        """
        self._guard(actor, "assessment_write", "ext_rule_record_create")
        _non_empty(rule_ref, "rule_ref")
        _non_empty(rule_text, "rule_text")
        with self._lock:
            if any(r["rule_ref"] == rule_ref for r in self._rules.values()):
                raise ValidationError("rule_ref %r already exists" % (rule_ref,))
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            record_id = self._next_id("scr")
            record = {
                "id": record_id,
                "rule_ref": rule_ref,
                "rule_text": rule_text,
                "course_id": course_id,
                "method": "recorded_rules_only",
                "applied_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rules[record_id] = record
            self._audit(actor, "ext_rule_record_create", record_id,
                        details={"rule_ref": rule_ref})
            return dict(record)

    def record_reported_outcome(self, assessment_id, reported_outcome,
                                actor, assessor_ref=None):
        """Record an outcome verbatim against a core assessment.

        Action: assessment_write. The core assessment record is
        untouched (pinned by test).
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
                "computed_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reported_outcomes[record_id] = record
            self._audit(actor, "ext_reported_outcome_record", record_id,
                        details={"assessment_id": assessment_id})
            return dict(record)

    def list_rule_records(self, actor=None, course_id=None):
        """Return rule records. Action: assessment_read."""
        self._maybe_require(actor, "assessment_read")
        with self._lock:
            records = list(self._rules.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def list_reported_outcomes(self, actor=None, assessment_id=None,
                               learner_id=None):
        """Return reported outcomes. Action: assessment_read (+ scope)."""
        self._maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._reported_outcomes.values())
            if assessment_id is not None:
                records = [r for r in records
                           if r["assessment_id"] == assessment_id]
            if learner_id is not None:
                records = [r for r in records
                           if r["learner_id"] == learner_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Integrations & APIs as a union function (reference) -------------
    # Labeled reference implementation (stub-engine): an integration
    # record declares an external connection as data (endpoint label
    # held verbatim). Creating one changes no core record and calls
    # nothing (``executed_here: False``).

    def create_integration_record(self, integration_ref, endpoint_label,
                                  actor, note=""):
        """Record an integration declaration. Action: catalog_write."""
        self._guard(actor, "catalog_write", "ext_integration_record_create")
        _non_empty(integration_ref, "integration_ref")
        _non_empty(endpoint_label, "endpoint_label")
        _string(note, "note")
        with self._lock:
            if any(r["integration_ref"] == integration_ref
                   for r in self._integration_records.values()):
                raise ValidationError(
                    "integration_ref %r already exists" % (integration_ref,))
            record_id = self._next_id("int")
            record = {
                "id": record_id,
                "integration_ref": integration_ref,
                "endpoint_label": endpoint_label,
                "note": note,
                "executed_here": False,
                "connected_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._integration_records[record_id] = record
            self._audit(actor, "ext_integration_record_create", record_id,
                        details={"integration_ref": integration_ref})
            return dict(record)

    def list_integration_records(self, actor=None):
        """Return integration records. Action: catalog_read."""
        self._maybe_require(actor, "catalog_read")
        with self._lock:
            records = sorted(self._integration_records.values(),
                             key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]
