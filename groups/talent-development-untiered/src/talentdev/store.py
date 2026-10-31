"""Talent Development store: organization registry; development
program and participation records; assessment and assessment
result records; aggregate insight snapshot records; decision
records.

Clean-room implementation of the union spec's implementation
contract. This category is new — no tiered group exists — and the
core is claim-driven: every record type traces to a claim in the
set's spec sheets (see UNION-SPEC.md), except the organization
registry, search/summary, and API/access/audit substrate every
DeadRamp build carries, whose reason is stated in the spec.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see :mod:`talentdev.access`).
A plain string actor carries identity (for provenance) but no
role, so role enforcement for those happens in the service layer
(the sibling builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``prg-``, ``enr-``, ``asm-``, ``res-``, ``ins-``, ``dec-``).

Reference discipline: records name people only by **opaque
references** supplied by the caller. A person reference is
validated to be incapable of holding an email address (no ``@``,
no whitespace); this store holds no real names, no email
addresses, and no free-text about any individual. Insight
snapshots hold no person reference at all: they are aggregate
counts over a cohort, which is what the privacy guard below
protects.

Development kinds: the two development families the set's forks
claim — ``talent_development`` (FORGE's phrase) and
``behavioral_mindset_development`` (BetterUp's phrase) — are kept
as separate kinds on the program record, because each fork
claims its development function in its own words. The records
machinery is one; the kinds are not merged.

Derivation discipline: a participation's status is derived at
read time and never stored. The single seam
:func:`_derive_participation_status` computes ``enrolled`` /
``completed`` from the record's completion moment. The stored
participation record carries no status key.

Small-cohort guard (the signature invariant): an insight snapshot
may not be recorded for a cohort smaller than
:data:`MIN_COHORT_SIZE`. BetterUp's description asserts its
dashboard works "while fully safeguarding the privacy of
individual program participants"; an aggregate count over a tiny
cohort is not aggregate in any meaningful sense, so the guard is
the records form of that assertion. The gate is the single seam
:func:`_check_cohort_allowed`, read by the snapshot operation
only; a refusal records nothing and consumes no id. The guard is
this build's own rule, stated here — it is not a claim that any
fork implements it.

Scoring discipline: nothing in this store computes a score, a
rating, a ranking, or a rate. Neither description uses scoring
vocabulary. Assessment results record the *administration*
outcome from a fixed vocabulary (``completed`` / ``partial`` /
``not_completed``) — a fact about the sitting, not a judgment of
the person — and the record shape carries no numeric result
field at all.

Money discipline: no record in this store carries money. Neither
description states a price, a fee, a budget, or a spend figure,
so no money shape was built — the same deliberate omission the
Event Management and Marketing & Sales builds recorded.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

PROGRAM_KINDS = ("talent_development", "behavioral_mindset_development")
RESULT_OUTCOMES = ("completed", "partial", "not_completed")
DECISIONS = ("approved", "deferred", "declined")
PARTICIPATION_STATES = ("enrolled", "completed")

MIN_COHORT_SIZE = 5


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                moment = datetime.strptime(text, "%Y-%m-%d")
            else:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _count(value, field):
    """A non-negative integer count. Booleans, floats, and strings
    are rejected at the boundary."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if value < 0:
        raise ValidationError("%s must be zero or greater" % field)
    return value


def _person_ref(value, field="person_ref"):
    """An opaque person reference. It must be a non-empty string
    with no whitespace and no ``@`` — a value of that shape cannot
    be an email address, so no record keyed by it can hold one."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')" % field)
    return value


def _derive_participation_status(participation):
    """Participation status derivation seam: ``completed`` once a
    completion moment is recorded, ``enrolled`` otherwise. Pure
    function over the recorded value; nothing about the status is
    stored anywhere."""
    if participation.get("completed_at") is not None:
        return "completed"
    return "enrolled"


def _check_cohort_allowed(cohort_size):
    """Small-cohort guard seam: the single check the snapshot
    operation reads before recording an insight snapshot.

    A cohort smaller than :data:`MIN_COHORT_SIZE` is refused: an
    aggregate count over a handful of people can single out an
    individual, which is precisely what the analytics family's
    source sentence says the dashboard avoids. Any cohort at or
    above the floor is allowed.
    """
    if cohort_size < MIN_COHORT_SIZE:
        raise ValidationError(
            "cohort_size %d is below the minimum cohort of %d; an "
            "aggregate snapshot over a smaller cohort could single "
            "out an individual participant"
            % (cohort_size, MIN_COHORT_SIZE))


class TalentDevStore:
    """In-memory Talent Development records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._programs = {}
        self._participations = {}
        self._assessments = {}
        self._results = {}
        self._snapshots = {}
        self._decisions = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organization(self, org_id):
        organization = self._organizations.get(org_id)
        if organization is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return organization

    def _program(self, program_id):
        program = self._programs.get(program_id)
        if program is None:
            raise NotFoundError("no such program: %r" % (program_id,))
        return program

    def _participation(self, participation_id):
        participation = self._participations.get(participation_id)
        if participation is None:
            raise NotFoundError(
                "no such participation: %r" % (participation_id,))
        return participation

    def _assessment(self, assessment_id):
        assessment = self._assessments.get(assessment_id)
        if assessment is None:
            raise NotFoundError("no such assessment: %r" % (assessment_id,))
        return assessment

    def _snapshot(self, snapshot_id):
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise NotFoundError("no such snapshot: %r" % (snapshot_id,))
        return snapshot

    # -- organizations ---------------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "organization ref already registered: %r" % (ref,))
            record = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[record["id"]] = record
        self._record(actor, "create_organization", record["id"],
                     {"ref": ref})
        return dict(record)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- development programs ---------------------------------------------------

    def create_program(self, actor, org_id, label, kind, goal_label=None):
        """Record a development program.

        ``kind`` names which development family the program
        belongs to, in the claiming fork's own words:
        ``talent_development`` or
        ``behavioral_mindset_development``. ``goal_label`` records
        the agency goal the program is aligned to, as a label —
        BetterUp's description aligns development "to each
        agency's unique goals"; the label records that alignment,
        it measures nothing.
        """
        self._check_role(actor, "programs")
        _text(label, "label")
        if kind not in PROGRAM_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (PROGRAM_KINDS,))
        _optional_text(goal_label, "goal_label")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("prg-"),
                "org_id": org_id,
                "label": label,
                "kind": kind,
                "goal_label": goal_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._programs[record["id"]] = record
        self._record(actor, "create_program", record["id"],
                     {"org_id": org_id, "kind": kind})
        return dict(record)

    def get_program(self, actor, program_id):
        self._check_role(actor, "read")
        return dict(self._program(program_id))

    def list_programs(self, actor, org_id=None, kind=None):
        self._check_role(actor, "read")
        if kind is not None and kind not in PROGRAM_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (PROGRAM_KINDS,))
        return [dict(p) for p in self._programs.values()
                if (org_id is None or p["org_id"] == org_id)
                and (kind is None or p["kind"] == kind)]

    # -- participations -----------------------------------------------------------

    def enroll(self, actor, program_id, participant_ref, enrolled_at=None):
        """Record one participant's enrollment in a program.

        The participant is an opaque reference only. The stored
        record carries no status key: status is derived at read
        (see :func:`_derive_participation_status`). The same
        participant may not be enrolled twice in the same program.
        """
        self._check_role(actor, "programs")
        _person_ref(participant_ref, "participant_ref")
        enrolled = None
        if enrolled_at is not None:
            enrolled = _parse_moment(enrolled_at, "enrolled_at")
        with self._lock:
            self._program(program_id)
            for existing in self._participations.values():
                if (existing["program_id"] == program_id
                        and existing["participant_ref"] == participant_ref):
                    raise ValidationError(
                        "participant %r is already enrolled in program "
                        "%r" % (participant_ref, program_id))
            record = {
                "id": self._mint("enr-"),
                "program_id": program_id,
                "participant_ref": participant_ref,
                "enrolled_at": (enrolled.isoformat() if enrolled is not None
                                else _utc_now().isoformat()),
                "completed_at": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._participations[record["id"]] = record
        self._record(actor, "enroll", record["id"],
                     {"program_id": program_id})
        return self._participation_view(record)

    def complete_participation(self, actor, participation_id,
                               completed_at=None):
        """Record a participation's completion moment. Completing
        an already completed participation is refused, as is a
        completion moment before the enrollment moment."""
        self._check_role(actor, "programs")
        completed = None
        if completed_at is not None:
            completed = _parse_moment(completed_at, "completed_at")
        with self._lock:
            participation = self._participation(participation_id)
            if participation["completed_at"] is not None:
                raise ValidationError(
                    "participation %r is already completed"
                    % (participation_id,))
            moment = completed if completed is not None else _utc_now()
            enrolled = _parse_moment(participation["enrolled_at"],
                                     "enrolled_at")
            if moment < enrolled:
                raise ValidationError(
                    "completed_at precedes the enrollment moment")
            participation["completed_at"] = moment.isoformat()
            result = self._participation_view(participation)
        self._record(actor, "complete_participation", participation_id, {})
        return result

    def _participation_view(self, participation):
        view = dict(participation)
        view["status"] = _derive_participation_status(participation)
        return view

    def get_participation(self, actor, participation_id):
        self._check_role(actor, "read")
        return self._participation_view(self._participation(participation_id))

    def list_participations(self, actor, program_id=None, status=None):
        self._check_role(actor, "read")
        if status is not None and status not in PARTICIPATION_STATES:
            raise ValidationError(
                "status must be one of %r" % (PARTICIPATION_STATES,))
        result = []
        for participation in self._participations.values():
            if (program_id is not None
                    and participation["program_id"] != program_id):
                continue
            view = self._participation_view(participation)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    # -- assessments -----------------------------------------------------------

    def create_assessment(self, actor, org_id, label, instrument_label):
        """Record a workforce assessment: a label and the
        instrument's label. Administering the instrument and
        interpreting its results are Extended (see UNION-SPEC.md);
        this is the record those operations presuppose."""
        self._check_role(actor, "assess")
        _text(label, "label")
        _text(instrument_label, "instrument_label")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("asm-"),
                "org_id": org_id,
                "label": label,
                "instrument_label": instrument_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._assessments[record["id"]] = record
        self._record(actor, "create_assessment", record["id"],
                     {"org_id": org_id})
        return dict(record)

    def get_assessment(self, actor, assessment_id):
        self._check_role(actor, "read")
        return dict(self._assessment(assessment_id))

    def list_assessments(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(a) for a in self._assessments.values()
                if org_id is None or a["org_id"] == org_id]

    def record_result(self, actor, assessment_id, subject_ref, outcome,
                      administered_at):
        """Record one assessment administration for one subject.

        ``outcome`` is the administration outcome from a fixed
        vocabulary (``completed`` / ``partial`` /
        ``not_completed``): a fact about the sitting. There is no
        score, rating, or band field on this record, and none is
        computed — the instrument's judgments are its own and are
        Extended.
        """
        self._check_role(actor, "assess")
        _person_ref(subject_ref, "subject_ref")
        if outcome not in RESULT_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (RESULT_OUTCOMES,))
        administered = _parse_moment(administered_at, "administered_at")
        with self._lock:
            self._assessment(assessment_id)
            record = {
                "id": self._mint("res-"),
                "assessment_id": assessment_id,
                "subject_ref": subject_ref,
                "outcome": outcome,
                "administered_at": administered.isoformat(),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._results[record["id"]] = record
        self._record(actor, "record_result", record["id"],
                     {"assessment_id": assessment_id, "outcome": outcome})
        return dict(record)

    def list_results(self, actor, assessment_id=None, outcome=None):
        self._check_role(actor, "read")
        if outcome is not None and outcome not in RESULT_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (RESULT_OUTCOMES,))
        return [dict(r) for r in self._results.values()
                if (assessment_id is None
                    or r["assessment_id"] == assessment_id)
                and (outcome is None or r["outcome"] == outcome)]

    # -- insight snapshots -----------------------------------------------------------

    def record_snapshot(self, actor, org_id, metric_label, period_label,
                        cohort_size, value_count, recorded_at=None):
        """Record one aggregate insight snapshot: a metric label, a
        period label, the cohort size, and the count of cohort
        members exhibiting the metric.

        Aggregate counts only — the record names no participant.
        The small-cohort guard binds here: a cohort below
        :data:`MIN_COHORT_SIZE` is refused and changes nothing
        (see :func:`_check_cohort_allowed`). ``value_count`` is a
        subset count and may not exceed the cohort.
        """
        self._check_role(actor, "insights")
        _text(metric_label, "metric_label")
        _text(period_label, "period_label")
        cohort = _count(cohort_size, "cohort_size")
        value = _count(value_count, "value_count")
        recorded = None
        if recorded_at is not None:
            recorded = _parse_moment(recorded_at, "recorded_at")
        with self._lock:
            self._organization(org_id)
            _check_cohort_allowed(cohort)
            if value > cohort:
                raise ValidationError(
                    "value_count %d exceeds the cohort size %d; a "
                    "subset count cannot exceed its cohort"
                    % (value, cohort))
            record = {
                "id": self._mint("ins-"),
                "org_id": org_id,
                "metric_label": metric_label,
                "period_label": period_label,
                "cohort_size": cohort,
                "value_count": value,
                "recorded_at": (recorded.isoformat() if recorded is not None
                                else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._snapshots[record["id"]] = record
        self._record(actor, "record_snapshot", record["id"],
                     {"org_id": org_id, "metric_label": metric_label})
        return dict(record)

    def list_snapshots(self, actor, org_id=None, metric_label=None):
        self._check_role(actor, "read")
        return [dict(s) for s in self._snapshots.values()
                if (org_id is None or s["org_id"] == org_id)
                and (metric_label is None
                     or s["metric_label"] == metric_label)]

    # -- decisions -----------------------------------------------------------

    def record_decision(self, actor, org_id, label, decision,
                        decided_by_ref, basis_assessment_ids=None,
                        basis_snapshot_ids=None, decided_at=None):
        """Record one organizational decision and its stated basis.

        The decision is a recorded value from a fixed vocabulary
        (``approved`` / ``deferred`` / ``declined``) with the
        decider's opaque reference and the assessments and
        snapshots it rests on — each basis id must exist and
        belong to the same organization. The build records
        decisions; it makes none and recommends none.
        """
        self._check_role(actor, "decide")
        _text(label, "label")
        if decision not in DECISIONS:
            raise ValidationError(
                "decision must be one of %r" % (DECISIONS,))
        _person_ref(decided_by_ref, "decided_by_ref")
        decided = None
        if decided_at is not None:
            decided = _parse_moment(decided_at, "decided_at")
        basis_assessments = list(basis_assessment_ids or [])
        basis_snapshots = list(basis_snapshot_ids or [])
        for basis_id in basis_assessments + basis_snapshots:
            _text(basis_id, "basis id")
        with self._lock:
            self._organization(org_id)
            for assessment_id in basis_assessments:
                if self._assessment(assessment_id)["org_id"] != org_id:
                    raise ValidationError(
                        "basis assessment %r does not belong to "
                        "organization %r" % (assessment_id, org_id))
            for snapshot_id in basis_snapshots:
                if self._snapshot(snapshot_id)["org_id"] != org_id:
                    raise ValidationError(
                        "basis snapshot %r does not belong to "
                        "organization %r" % (snapshot_id, org_id))
            record = {
                "id": self._mint("dec-"),
                "org_id": org_id,
                "label": label,
                "decision": decision,
                "decided_by_ref": decided_by_ref,
                "basis_assessment_ids": basis_assessments,
                "basis_snapshot_ids": basis_snapshots,
                "decided_at": (decided.isoformat() if decided is not None
                               else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[record["id"]] = record
        self._record(actor, "record_decision", record["id"],
                     {"org_id": org_id, "decision": decision})
        return dict(record)

    def list_decisions(self, actor, org_id=None, decision=None):
        self._check_role(actor, "read")
        if decision is not None and decision not in DECISIONS:
            raise ValidationError(
                "decision must be one of %r" % (DECISIONS,))
        return [dict(d) for d in self._decisions.values()
                if (org_id is None or d["org_id"] == org_id)
                and (decision is None or d["decision"] == decision)]

    # -- search, summary, audit ---------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over the
        registered metadata: organizations, programs, assessments,
        and decisions."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()

        def hit(*fields):
            return any(needle in (f or "").lower() for f in fields)

        return {
            "organizations": [dict(o) for o in self._organizations.values()
                              if hit(o["ref"], o["label"])],
            "programs": [dict(p) for p in self._programs.values()
                         if hit(p["label"], p["kind"], p["goal_label"])],
            "assessments": [dict(a) for a in self._assessments.values()
                            if hit(a["label"], a["instrument_label"])],
            "decisions": [dict(d) for d in self._decisions.values()
                          if hit(d["label"])],
        }

    def summary(self, actor):
        """Counts computed on read from the records. Counts only:
        no scores, no rates, no rankings."""
        self._check_role(actor, "read")
        programs_by_kind = {k: 0 for k in PROGRAM_KINDS}
        for program in self._programs.values():
            programs_by_kind[program["kind"]] += 1
        participations_by_status = {s: 0 for s in PARTICIPATION_STATES}
        for participation in self._participations.values():
            participations_by_status[
                _derive_participation_status(participation)] += 1
        results_by_outcome = {o: 0 for o in RESULT_OUTCOMES}
        for result in self._results.values():
            results_by_outcome[result["outcome"]] += 1
        decisions_by_decision = {d: 0 for d in DECISIONS}
        for record in self._decisions.values():
            decisions_by_decision[record["decision"]] += 1
        return {
            "organizations": len(self._organizations),
            "programs": len(self._programs),
            "programs_by_kind": programs_by_kind,
            "participations": len(self._participations),
            "participations_by_status": participations_by_status,
            "assessments": len(self._assessments),
            "results": len(self._results),
            "results_by_outcome": results_by_outcome,
            "snapshots": len(self._snapshots),
            "decisions": len(self._decisions),
            "decisions_by_decision": decisions_by_decision,
        }

    def audit_read(self, actor):
        """Return the audit entries (requires ``audit_read``)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"count": len(entries), "entries": entries}
