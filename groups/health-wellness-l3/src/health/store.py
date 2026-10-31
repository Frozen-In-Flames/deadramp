"""Health & wellness records store: participant registry (opaque
references only), program registry, enrollments with derived status,
measurement/outcome records, care/wellness plan records with derived
status, activity/appointment records, eligibility/coverage records
with derived status, and population scorecard reporting over the
records.

Clean-room implementation of the union spec's 10 Core functions.
Records and opaque references only: there is no diagnosis field, no
free-text clinical note field, and no real-identifier field anywhere
in this substrate (the privacy discipline in UNION-SPEC.md is
constitutive, not decorative). Each vendor's clinical, device, AI
and workflow engines on top of this substrate are Extended functions.

Permission convention (mirrors the education group): store methods
take an ``actor``. When the actor is a User-like object (it has a
``role`` attribute) the store calls :func:`health.access.require`
for the method's action *before* any state change or id allocation,
so a denied operation consumes no id and changes nothing. Where a
plain string is passed it carries identity (for provenance) but no
role, so there is nothing to enforce against at this layer; the
service layer, which knows the role registry, is responsible for
enforcement in that case -- and it always passes User objects.

Member scope: a ``member``-role actor may only read records whose
participant's ``participant_ref`` equals the actor's name; reading
another participant's record raises :class:`PermissionDenied`, and
list methods return only the member's own records. Programs are
registry records and are readable by all roles without scoping.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``par-``, ``prg-``, ``enr-``,
``msr-``, ``pln-``, ``act-``, ``elg-``).

Derived status is computed at read time, deterministically, from the
stored record and an explicit ``as_of`` reference date -- plan status
from due/completion dates, eligibility status from coverage dates,
and enrollment status from the participant's plan records for the
enrollment's program (see :meth:`_derive_plan_status` and the
contract's derived-status rules). Tests always pass an explicit
``as_of`` and never depend on the wall clock.

Store methods accept only the contract's named parameters. The HTTP
layer rejects any JSON key outside an endpoint's named field list
with :class:`ValidationError` before calling the store, so extra
fields (a diagnosis, a note, an identifier) are refused at the
boundary.

The store records every successful mutation and every report /
scorecard read to its audit log (when one is attached).

High-baseline uplift [L3] (AU-5 fail closed): every mutating method
is wrapped by :func:`_fail_closed` -- it runs against a snapshot of
the store state, and if its audit write raises
:class:`~health.errors.AuditWriteError` (the entry could not be
durably recorded), the snapshot is restored in full (records and id
counters) and the error propagates, so an operation whose audit
write fails does not proceed. The snapshot pattern is the proven
one from ``groups/accounting-l3`` / ``groups/crm-l3`` (our own
Apache-2.0 code), applied to this store's seven record dicts.
"""

import copy
import functools
import math
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

PARTICIPANT_KINDS = ("patient", "caregiver", "professional")
PROGRAM_KINDS = ("program", "clinic", "care_journey")
ENROLLMENT_KINDS = ("enrollment", "registration")
PLAN_KINDS = ("care_plan", "wellness_plan", "education")
ACTIVITY_KINDS = ("appointment", "activity", "session")
ACTIVITY_STATES = ("scheduled", "completed", "cancelled")


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


def _validate_date(value, what):
    """Validate an ISO date string (YYYY-MM-DD); return a date object."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _coerce_as_of(as_of, what="as_of"):
    """Coerce an as_of reference (date, datetime, or ISO string) to a date.

    ``None`` means today (UTC), per the contract; deterministic
    callers (tests, reporting reads) always pass an explicit value.
    """
    if as_of is None:
        return datetime.now(timezone.utc).date()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        # Accept a full ISO datetime too; its date part governs.
        text = as_of.strip()
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
        candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError as exc:
            raise ValidationError("%s is not a valid ISO date: %r" % (what, as_of)) from exc
    raise ValidationError("%s must be an ISO date string or date" % (what,))


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


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _fail_closed(method):
    """Wrap a store operation so an audit write failure rolls it back.

    High-baseline uplift (AU-5) [L3]: the wrapped method runs against a
    snapshot of the store state; if it raises
    :class:`~health.errors.AuditWriteError` (its audit entry could not be
    durably recorded), the snapshot is restored and the error
    propagates. Other exceptions keep the store's existing guarantee
    (validation happens before mutation, so nothing is half-applied).
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class HealthStore:
    """In-memory store for the health & wellness records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._participants = {}
        self._programs = {}
        self._enrollments = {}
        self._measurements = {}
        self._plans = {}
        self._activities = {}
        self._eligibility = {}
        self._counters = {
            "par": 0, "prg": 0, "enr": 0, "msr": 0, "pln": 0, "act": 0, "elg": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _snapshot_state(self):
        """Deep-copy the mutable store state (AU-5 rollback image) [L3]."""
        return (
            copy.deepcopy(self._participants),
            copy.deepcopy(self._programs),
            copy.deepcopy(self._enrollments),
            copy.deepcopy(self._measurements),
            copy.deepcopy(self._plans),
            copy.deepcopy(self._activities),
            copy.deepcopy(self._eligibility),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        """Restore a snapshot taken by :meth:`_snapshot_state` [L3]."""
        (
            self._participants,
            self._programs,
            self._enrollments,
            self._measurements,
            self._plans,
            self._activities,
            self._eligibility,
            self._counters,
        ) = snapshot

    @staticmethod
    def _is_member(actor):
        return actor is not None and getattr(actor, "role", None) == "member"

    def _participant_ref_for(self, participant_id):
        """Return the participant_ref for a participant id, or None."""
        participant = self._participants.get(participant_id)
        if participant is None:
            return None
        return participant["participant_ref"]

    def _scope_check_ref(self, actor, participant_ref):
        """A member-role actor may only touch their own records."""
        if self._is_member(actor) and getattr(actor, "name", None) != participant_ref:
            raise PermissionDenied(
                "permission denied: member %r may not access records of participant %r"
                % (getattr(actor, "name", None), participant_ref)
            )

    def _scope_check_participant(self, actor, participant_id):
        """Scope check for a record bound to ``participant_id``."""
        if self._is_member(actor):
            self._scope_check_ref(actor, self._participant_ref_for(participant_id))

    def _check_filter_scope(self, actor, participant_id):
        """Scope check for a caller-supplied participant_id filter."""
        if participant_id is not None:
            self._scope_check_participant(actor, participant_id)
            if self._is_member(actor) and self._participant_ref_for(participant_id) is None:
                raise PermissionDenied(
                    "permission denied: member %r may not access records of participant %r"
                    % (getattr(actor, "name", None), participant_id)
                )

    def _scoped_participant_records(self, actor, records):
        """Filter participant-bound records to a member actor's own."""
        if self._is_member(actor):
            name = getattr(actor, "name", None)
            return [r for r in records
                    if self._participant_ref_for(r.get("participant_id")) == name]
        return list(records)

    def _get_participant_record(self, participant_id):
        record = self._participants.get(participant_id)
        if record is None:
            raise NotFoundError("participant not found: %r" % (participant_id,))
        return record

    def _get_program_record(self, program_id):
        record = self._programs.get(program_id)
        if record is None:
            raise NotFoundError("program not found: %r" % (program_id,))
        return record

    def _get_enrollment_record(self, enrollment_id):
        record = self._enrollments.get(enrollment_id)
        if record is None:
            raise NotFoundError("enrollment not found: %r" % (enrollment_id,))
        return record

    def _get_measurement_record(self, measurement_id):
        record = self._measurements.get(measurement_id)
        if record is None:
            raise NotFoundError("measurement not found: %r" % (measurement_id,))
        return record

    def _get_plan_record(self, plan_id):
        record = self._plans.get(plan_id)
        if record is None:
            raise NotFoundError("plan record not found: %r" % (plan_id,))
        return record

    def _get_activity_record(self, activity_id):
        record = self._activities.get(activity_id)
        if record is None:
            raise NotFoundError("activity not found: %r" % (activity_id,))
        return record

    def _get_eligibility_record(self, eligibility_id):
        record = self._eligibility.get(eligibility_id)
        if record is None:
            raise NotFoundError("eligibility record not found: %r" % (eligibility_id,))
        return record

    # -- derived status (contract section 6) ---------------------------

    def _derive_plan_status(self, plan, as_of_date):
        """Derive current/overdue/completed plan status deterministically.

        MUTATION DRILL NOTE: the overdue branch of this function
        (``HealthStore._derive_plan_status`` in ``src/health/store.py``)
        is the load-bearing invariant for the negative-control drill:
        an incomplete plan whose due date is before ``as_of`` must
        read ``overdue``, never ``current``.
        """
        if plan["completed_on"] is not None:
            return "completed"
        due = _validate_date(plan["due_date"], "due_date")
        if as_of_date > due:
            return "overdue"
        return "current"

    def _derive_eligibility_status(self, record, as_of_date):
        """Derive upcoming/current/ended eligibility status."""
        if record["coverage_end"] is not None:
            end = _validate_date(record["coverage_end"], "coverage_end")
            if as_of_date > end:
                return "ended"
        start = _validate_date(record["coverage_start"], "coverage_start")
        if as_of_date < start:
            return "upcoming"
        return "current"

    def _derive_enrollment_status(self, enrollment, as_of_date):
        """Derive enrolled/completed/overdue enrollment status.

        Computed from the participant's plan records for the
        enrollment's program, each derived with the same ``as_of``:
        overdue if any such plan is overdue; else completed if any
        such plan is completed; else enrolled.
        """
        plans = [p for p in self._plans.values()
                 if p["participant_id"] == enrollment["participant_id"]
                 and p["program_id"] == enrollment["program_id"]]
        statuses = [self._derive_plan_status(p, as_of_date) for p in plans]
        if "overdue" in statuses:
            return "overdue"
        if "completed" in statuses:
            return "completed"
        return "enrolled"

    def _plan_view(self, plan, as_of_date):
        view = dict(plan)
        view["derived_status"] = self._derive_plan_status(plan, as_of_date)
        return view

    def _eligibility_view(self, record, as_of_date):
        view = dict(record)
        view["derived_status"] = self._derive_eligibility_status(record, as_of_date)
        return view

    def _enrollment_view(self, enrollment, as_of_date):
        view = dict(enrollment)
        view["derived_status"] = self._derive_enrollment_status(enrollment, as_of_date)
        return view

    # -- participant registry (Core 1) ---------------------------------

    @_fail_closed
    def create_participant(self, participant_ref, actor, kind="patient"):
        """Register a participant under an opaque reference only.

        Action: participant_write. No name, contact, date-of-birth or
        other identifier field exists in this shape; a duplicate
        ``participant_ref`` raises ValidationError.
        """
        _require_actor(actor, "participant_write")
        _validate_non_empty(participant_ref, "participant_ref")
        if kind not in PARTICIPANT_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(PARTICIPANT_KINDS),))
        with self._lock:
            for existing in self._participants.values():
                if existing["participant_ref"] == participant_ref:
                    raise ValidationError(
                        "participant_ref %r is already registered" % (participant_ref,)
                    )
            participant_id = self._next_id("par")
            record = {
                "id": participant_id,
                "participant_ref": participant_ref,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._participants[participant_id] = record
            self._audit(actor, "participant_create", participant_id,
                        details={"participant_ref": participant_ref, "kind": kind})
            return dict(record)

    def get_participant(self, participant_id, actor=None):
        """Return one participant record. Action: participant_read (+ member scope)."""
        _maybe_require(actor, "participant_read")
        with self._lock:
            record = self._get_participant_record(participant_id)
            self._scope_check_ref(actor, record["participant_ref"])
            return dict(record)

    def list_participants(self, actor=None):
        """Return participant records sorted by id. Action: participant_read."""
        _maybe_require(actor, "participant_read")
        with self._lock:
            records = sorted(self._participants.values(), key=lambda r: _id_num(r["id"]))
            if self._is_member(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if r["participant_ref"] == name]
            return [dict(r) for r in records]

    # -- program registry (Core 2) ---------------------------------------

    @_fail_closed
    def create_program(self, title, actor, kind="program", code=None, description=""):
        """Create a program/clinic/care-journey registry entry. Action: program_write."""
        _require_actor(actor, "program_write")
        _validate_non_empty(title, "program title")
        if kind not in PROGRAM_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(PROGRAM_KINDS),))
        if code is not None and not isinstance(code, str):
            raise ValidationError("code must be a string")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        with self._lock:
            program_id = self._next_id("prg")
            record = {
                "id": program_id,
                "title": title,
                "kind": kind,
                "code": code,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._programs[program_id] = record
            self._audit(actor, "program_create", program_id,
                        details={"title": title, "kind": kind})
            return dict(record)

    def get_program(self, program_id, actor=None):
        """Return one registry entry. Action: program_read (unscoped)."""
        _maybe_require(actor, "program_read")
        with self._lock:
            return dict(self._get_program_record(program_id))

    def list_programs(self, actor=None):
        """Return registry entries sorted by id. Action: program_read."""
        _maybe_require(actor, "program_read")
        with self._lock:
            records = sorted(self._programs.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- enrollments with derived status (Core 3) -------------------------

    @_fail_closed
    def create_enrollment(self, participant_id, program_id, actor, kind="enrollment"):
        """Enroll/register a participant in a program.

        Action: enrollment_write. A duplicate active enrollment for
        the same participant+program+kind is a validation error. The
        stored status is always ``enrolled``; reads add a derived
        status computed from the participant's plan records.
        """
        _require_actor(actor, "enrollment_write")
        _validate_non_empty(participant_id, "participant_id")
        _validate_non_empty(program_id, "program_id")
        if kind not in ENROLLMENT_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(ENROLLMENT_KINDS),))
        with self._lock:
            self._get_participant_record(participant_id)
            self._get_program_record(program_id)
            for existing in self._enrollments.values():
                if (
                    existing["participant_id"] == participant_id
                    and existing["program_id"] == program_id
                    and existing["kind"] == kind
                    and existing["status"] == "enrolled"
                ):
                    raise ValidationError(
                        "participant %r is already enrolled in program %r"
                        % (participant_id, program_id)
                    )
            enrollment_id = self._next_id("enr")
            record = {
                "id": enrollment_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "kind": kind,
                "status": "enrolled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrollments[enrollment_id] = record
            self._audit(actor, "enrollment_create", enrollment_id,
                        details={"participant_id": participant_id, "program_id": program_id})
            return self._enrollment_view(record, _coerce_as_of(None))

    def get_enrollment(self, enrollment_id, actor=None, as_of=None):
        """Return one enrollment view with derived status.

        Action: enrollment_read (+ member scope).
        """
        _maybe_require(actor, "enrollment_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_enrollment_record(enrollment_id)
            self._scope_check_participant(actor, record["participant_id"])
            return self._enrollment_view(record, as_of_date)

    def list_enrollments(self, actor=None, participant_id=None, program_id=None, as_of=None):
        """Return enrollment views, optionally filtered. Action: enrollment_read."""
        _maybe_require(actor, "enrollment_read")
        self._check_filter_scope(actor, participant_id)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = sorted(self._enrollments.values(), key=lambda r: _id_num(r["id"]))
            if participant_id is not None:
                records = [r for r in records if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            records = self._scoped_participant_records(actor, records)
            return [self._enrollment_view(r, as_of_date) for r in records]

    # -- measurement / outcome records (Core 4) ----------------------------

    @_fail_closed
    def record_measurement(self, participant_id, metric_name, value, unit, recorded_on,
                             actor, program_id=None):
        """Record a numeric measurement/outcome value. Action: measurement_write.

        Holds a metric name, a numeric value, a unit and a date --
        nothing else. No diagnosis field, no note field.
        """
        _require_actor(actor, "measurement_write")
        _validate_non_empty(participant_id, "participant_id")
        _validate_non_empty(metric_name, "metric_name")
        _validate_non_empty(unit, "unit")
        _validate_date(recorded_on, "recorded_on")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError("value must be a number")
        if not math.isfinite(value):
            raise ValidationError("value must be finite")
        with self._lock:
            self._get_participant_record(participant_id)
            if program_id is not None:
                self._get_program_record(program_id)
            measurement_id = self._next_id("msr")
            record = {
                "id": measurement_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._measurements[measurement_id] = record
            self._audit(actor, "measurement_record", measurement_id,
                        details={"participant_id": participant_id,
                                 "metric_name": metric_name, "program_id": program_id})
            return dict(record)

    def get_measurement(self, measurement_id, actor=None):
        """Return one measurement record. Action: measurement_read (+ scope)."""
        _maybe_require(actor, "measurement_read")
        with self._lock:
            record = self._get_measurement_record(measurement_id)
            self._scope_check_participant(actor, record["participant_id"])
            return dict(record)

    def list_measurements(self, actor=None, participant_id=None, program_id=None,
                          metric_name=None):
        """Return measurement records, optionally filtered. Action: measurement_read."""
        _maybe_require(actor, "measurement_read")
        self._check_filter_scope(actor, participant_id)
        with self._lock:
            records = sorted(self._measurements.values(), key=lambda r: _id_num(r["id"]))
            if participant_id is not None:
                records = [r for r in records if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            if metric_name is not None:
                records = [r for r in records if r["metric_name"] == metric_name]
            return [dict(r) for r in self._scoped_participant_records(actor, records)]

    # -- care / wellness plan records (Core 5) ------------------------------

    @_fail_closed
    def create_plan(self, participant_id, program_id, title, due_date, actor,
                    kind="care_plan"):
        """Create a care/wellness plan record. Action: plan_write."""
        _require_actor(actor, "plan_write")
        _validate_non_empty(participant_id, "participant_id")
        _validate_non_empty(program_id, "program_id")
        _validate_non_empty(title, "plan title")
        _validate_date(due_date, "due_date")
        if kind not in PLAN_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(PLAN_KINDS),))
        with self._lock:
            self._get_participant_record(participant_id)
            self._get_program_record(program_id)
            plan_id = self._next_id("pln")
            record = {
                "id": plan_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "title": title,
                "kind": kind,
                "due_date": due_date,
                "completed_on": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._plans[plan_id] = record
            self._audit(actor, "plan_create", plan_id,
                        details={"participant_id": participant_id,
                                 "program_id": program_id, "due_date": due_date})
            return self._plan_view(record, _coerce_as_of(None))

    @_fail_closed
    def complete_plan(self, plan_id, completed_on, actor):
        """Record completion of a plan record. Action: plan_write.

        Completing an already completed plan raises ValidationError.
        ``completed_on`` may be any valid date, including before the
        due date.
        """
        _require_actor(actor, "plan_write")
        _validate_date(completed_on, "completed_on")
        with self._lock:
            record = self._get_plan_record(plan_id)
            if record["completed_on"] is not None:
                raise ValidationError("plan %r is already completed" % (plan_id,))
            record["completed_on"] = completed_on
            self._audit(actor, "plan_complete", plan_id,
                        details={"completed_on": completed_on})
            return self._plan_view(record, _coerce_as_of(None))

    def get_plan(self, plan_id, actor=None, as_of=None):
        """Return one plan view with derived status. Action: plan_read (+ scope)."""
        _maybe_require(actor, "plan_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_plan_record(plan_id)
            self._scope_check_participant(actor, record["participant_id"])
            return self._plan_view(record, as_of_date)

    def list_plans(self, actor=None, participant_id=None, program_id=None, as_of=None):
        """Return plan views, optionally filtered. Action: plan_read."""
        _maybe_require(actor, "plan_read")
        self._check_filter_scope(actor, participant_id)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = sorted(self._plans.values(), key=lambda r: _id_num(r["id"]))
            if participant_id is not None:
                records = [r for r in records if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            records = self._scoped_participant_records(actor, records)
            return [self._plan_view(r, as_of_date) for r in records]

    # -- activity / appointment records (Core 6) ------------------------------

    @_fail_closed
    def create_activity(self, participant_id, title, starts_at, actor, program_id=None,
                          ends_at=None, kind="appointment"):
        """Create an activity/appointment record. Action: activity_write."""
        _require_actor(actor, "activity_write")
        _validate_non_empty(participant_id, "participant_id")
        _validate_non_empty(title, "activity title")
        if kind not in ACTIVITY_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(ACTIVITY_KINDS),))
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at") if ends_at is not None else None
        if end_dt is not None and end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        with self._lock:
            self._get_participant_record(participant_id)
            if program_id is not None:
                self._get_program_record(program_id)
            activity_id = self._next_id("act")
            record = {
                "id": activity_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "title": title,
                "kind": kind,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "state": "scheduled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._activities[activity_id] = record
            self._audit(actor, "activity_create", activity_id,
                        details={"participant_id": participant_id, "kind": kind})
            return dict(record)

    @_fail_closed
    def set_activity_state(self, activity_id, state, actor):
        """Set an activity record's lifecycle state. Action: activity_write."""
        _require_actor(actor, "activity_write")
        if state not in ACTIVITY_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(ACTIVITY_STATES),))
        with self._lock:
            record = self._get_activity_record(activity_id)
            record["state"] = state
            self._audit(actor, "activity_set_state", activity_id, details={"state": state})
            return dict(record)

    def get_activity(self, activity_id, actor=None):
        """Return one activity record. Action: activity_read (+ scope)."""
        _maybe_require(actor, "activity_read")
        with self._lock:
            record = self._get_activity_record(activity_id)
            self._scope_check_participant(actor, record["participant_id"])
            return dict(record)

    def list_activities(self, actor=None, participant_id=None, program_id=None):
        """Return activity records, optionally filtered. Action: activity_read."""
        _maybe_require(actor, "activity_read")
        self._check_filter_scope(actor, participant_id)
        with self._lock:
            records = sorted(self._activities.values(), key=lambda r: _id_num(r["id"]))
            if participant_id is not None:
                records = [r for r in records if r["participant_id"] == participant_id]
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            return [dict(r) for r in self._scoped_participant_records(actor, records)]

    # -- eligibility / coverage records (Core 7) ------------------------------

    @_fail_closed
    def create_eligibility(self, participant_id, plan_ref, coverage_start, actor,
                           program_id=None, coverage_end=None):
        """Create an eligibility/coverage record. Action: eligibility_write.

        Holds an opaque ``plan_ref`` only -- no insurer name, member
        number or benefit details exist in this shape.
        """
        _require_actor(actor, "eligibility_write")
        _validate_non_empty(participant_id, "participant_id")
        _validate_non_empty(plan_ref, "plan_ref")
        start = _validate_date(coverage_start, "coverage_start")
        end = _validate_date(coverage_end, "coverage_end") if coverage_end is not None else None
        if end is not None and end < start:
            raise ValidationError("coverage_end must not be before coverage_start")
        with self._lock:
            self._get_participant_record(participant_id)
            if program_id is not None:
                self._get_program_record(program_id)
            eligibility_id = self._next_id("elg")
            record = {
                "id": eligibility_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "plan_ref": plan_ref,
                "coverage_start": coverage_start,
                "coverage_end": coverage_end,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._eligibility[eligibility_id] = record
            self._audit(actor, "eligibility_create", eligibility_id,
                        details={"participant_id": participant_id, "plan_ref": plan_ref})
            return self._eligibility_view(record, _coerce_as_of(None))

    def get_eligibility(self, eligibility_id, actor=None, as_of=None):
        """Return one eligibility view with derived status.

        Action: eligibility_read (+ member scope).
        """
        _maybe_require(actor, "eligibility_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_eligibility_record(eligibility_id)
            self._scope_check_participant(actor, record["participant_id"])
            return self._eligibility_view(record, as_of_date)

    def list_eligibilities(self, actor=None, participant_id=None, as_of=None):
        """Return eligibility views, optionally filtered. Action: eligibility_read."""
        _maybe_require(actor, "eligibility_read")
        self._check_filter_scope(actor, participant_id)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = sorted(self._eligibility.values(), key=lambda r: _id_num(r["id"]))
            if participant_id is not None:
                records = [r for r in records if r["participant_id"] == participant_id]
            records = self._scoped_participant_records(actor, records)
            return [self._eligibility_view(r, as_of_date) for r in records]

    # Alias matching the HTTP layer's pluralisation in the contract
    # (GET /eligibility returns {"eligibility": [...]}).
    list_eligibility = list_eligibilities

    def eligibility_status(self, eligibility_id, actor=None, as_of=None):
        """Return the derived-status summary for one eligibility record.

        Action: eligibility_read (+ member scope).
        """
        _maybe_require(actor, "eligibility_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_eligibility_record(eligibility_id)
            self._scope_check_participant(actor, record["participant_id"])
            return {
                "id": record["id"],
                "derived_status": self._derive_eligibility_status(record, as_of_date),
            }

    # -- population scorecard reporting (Core 8) ------------------------------

    @staticmethod
    def _aggregate_measurements(records):
        """Aggregate measurement records per metric: count/min/max/mean."""
        by_metric = {}
        for record in records:
            bucket = by_metric.setdefault(record["metric_name"], [])
            bucket.append(record["value"])
        result = {}
        for metric_name in sorted(by_metric):
            values = by_metric[metric_name]
            result[metric_name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
        return result

    def report(self, actor, as_of=None):
        """Population counts/aggregates over the substrate records only.

        Action: report_read. Plan and eligibility counts use the
        same derived statuses as the record reads, against ``as_of``.
        """
        _require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            plans_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for record in self._plans.values():
                plans_by_status[self._derive_plan_status(record, as_of_date)] += 1
            activities_by_state = {s: 0 for s in ACTIVITY_STATES}
            for record in self._activities.values():
                activities_by_state[record["state"]] += 1
            eligibility_by_status = {"upcoming": 0, "current": 0, "ended": 0}
            for record in self._eligibility.values():
                eligibility_by_status[
                    self._derive_eligibility_status(record, as_of_date)
                ] += 1
            enrollments_by_program = {}
            for record in self._enrollments.values():
                enrollments_by_program[record["program_id"]] = (
                    enrollments_by_program.get(record["program_id"], 0) + 1
                )
            result = {
                "as_of": as_of_date.isoformat(),
                "participants": len(self._participants),
                "programs": len(self._programs),
                "enrollments": len(self._enrollments),
                "measurements": len(self._measurements),
                "measurements_by_metric": self._aggregate_measurements(
                    list(self._measurements.values())
                ),
                "plans": len(self._plans),
                "plans_by_status": plans_by_status,
                "activities": len(self._activities),
                "activities_by_state": activities_by_state,
                "eligibility": len(self._eligibility),
                "eligibility_by_status": eligibility_by_status,
                "enrollments_by_program": enrollments_by_program,
            }
            self._audit(actor, "report", "report", details={"as_of": result["as_of"]})
            return result

    def scorecard(self, program_id, actor, as_of=None):
        """Per-program scorecard over the substrate records only.

        Action: report_read; unknown program raises NotFoundError.
        ``participants`` counts distinct participants with at least
        one measurement or plan in this program.
        """
        _require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            self._get_program_record(program_id)
            measurements = [r for r in self._measurements.values()
                            if r["program_id"] == program_id]
            plans = [r for r in self._plans.values()
                     if r["program_id"] == program_id]
            participant_ids = {r["participant_id"] for r in measurements}
            participant_ids |= {r["participant_id"] for r in plans}
            plans_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for record in plans:
                plans_by_status[self._derive_plan_status(record, as_of_date)] += 1
            result = {
                "program_id": program_id,
                "as_of": as_of_date.isoformat(),
                "participants": len(participant_ids),
                "measurements": len(measurements),
                "measurements_by_metric": self._aggregate_measurements(measurements),
                "plans": len(plans),
                "plans_by_status": plans_by_status,
            }
            self._audit(actor, "scorecard", program_id,
                        details={"as_of": result["as_of"]})
            return result
