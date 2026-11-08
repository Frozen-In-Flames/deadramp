"""Final GAPS batch extensions for the Human Resources L1 singleton.

Clean-room, standard-library-only extension for the 1 open entry of
Remainder Singleton 62 (see ``BATCH.md`` in the group directory for
the disposition and its grounds). This module is a wrapper around
:class:`HrStore`; every core module is untouched and byte-identical.

The entry names the fork's whole function: a workforce scheduling
& call-scheduling engine -- deciding who works when, in advance,
for healthcare organizations. Its in-substrate form, following this
category's own adjudicated scheduling precedent (Untiered Set 16,
idx 907: schedule assignments held as data, no assignment computed)
and the sibling units' definitions-as-data forms, is records:

- **Shift definitions** (``shf-``) and **rotation definitions**
  (``rot-``) are definitions held as data. A shift definition is a
  kind label plus start/end clock labels; a rotation definition
  binds an ordered list of opaque ``person_ref`` values to a core
  position. Nothing expands a definition into dated assignments:
  ``generated_here`` / ``optimized_here`` / ``automated_here`` are
  False on every definition record, and no method on this surface
  generates, optimizes, or auto-assigns anything.
- **Roster assignments** (``ros-``) are caller-recorded assignment
  records: a date, a shift definition, a core position, and one
  opaque ``person_ref``, entered one at a time by the caller
  (``source: "recorded"``). The decision an assignment embodies is
  the caller's; this substrate records it (``decided_here`` False,
  ``assigned_automatically`` False). A duplicate active assignment
  for the same person, date, and shift is rejected whole.
- **Coverage is derived at read, never stored.** A rotation view
  derives, per shift definition, whether the rotation's position
  has a recorded active assignment on a date, through the single
  seam :func:`_derive_pair_state`. The stored rotation record
  carries no coverage or status key (pinned by test).

What is NOT here, stated plainly: no schedule construction, no
coverage optimization, no call-rotation generation, and none of
the automation machinery the fork's one claim names. The records
state that absence on their face rather than absorbing the
engine's name.

Doctrines carried from the core: opaque ``*_ref`` strings only --
the founding privacy discipline binds this surface exactly as it
binds the core, so no record shape here can hold a real name, SSN,
DOB, salary, address, phone, or email (the core privacy test's
forbidden-key set is pinned over these shapes too, and no public
method on this surface accepts a name-, identifier-, or
content-shaped argument); roster assignments are person-bound and
employee-scoped exactly as the core scopes person-bound records;
rotation definitions are scoped for employee readers to rotations
they are a member of; derived-never-stored for every computed
value (pair states, coverage counts, summaries); append-only
audit on the core store's log with ``ext_``-prefixed actions for
every successful extension mutation (denied operations record
nothing, the store-level convention -- denial auditing lives in
the service layer); RBAC via :mod:`hr.access` with the core's
existing actions, enforced before any state change or id
allocation, so a failed operation consumes no id and changes
nothing. L1 tier discipline: the core's plain append-only audit
and four-role matrix ride as they are; no hash chain, lockout, or
other higher-tier apparatus is imported.

RBAC action mapping (the core action set is fixed): shift
definitions, rotation definitions, and roster assignments ride
the performance family (per-person work records, per the untiered
set's mapping for time entries and schedule assignments);
aggregate and cross-record views (rotation coverage view,
schedule summary) require ``report_read``, as in the core report.
"""

import re
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SHIFT_KINDS = ("day", "evening", "night", "call")

# The core privacy test's forbidden-key set (tests/test_privacy.py):
# no extension record shape may carry any of these keys either.
FORBIDDEN_KEYS = {
    "name", "ssn", "social_security_number", "salary", "compensation",
    "pay", "dob", "date_of_birth", "address", "phone", "email",
}
# Argument names no public method on this surface may accept: the
# no-PII / no-content invariant at the signature level.
FORBIDDEN_PARAMS = {
    "name", "ssn", "social_security_number", "dob", "date_of_birth",
    "address", "phone", "email", "salary", "compensation",
    "content", "message_text", "body",
}

_CLOCK_LABEL = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_date(value, what):
    """Validate an ISO date string (YYYY-MM-DD); return a date object."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _validate_clock_label(value, what):
    """Validate a shift clock label (HH:MM, 24-hour) held as data.

    The label is recorded verbatim; no duration or interval is
    ever computed from it on this surface.
    """
    if not isinstance(value, str) or not _CLOCK_LABEL.match(value.strip()):
        raise ValidationError("%s must be a clock label (HH:MM, 24-hour)" % (what,))
    return value.strip()


def _maybe_require(actor, action):
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _derive_pair_state(assignments):
    """Coverage seam: the single point where a (rotation position,
    shift, date) pair's state is derived -- ``"filled"`` when at
    least one non-cancelled roster assignment is recorded for the
    pair, ``"unfilled"`` otherwise. The result is a read-time view
    value; it is never stored on any record.

    MUTATION DRILL NOTE: this seam is the batch unit's fresh
    negative-control target -- reading every pair as filled would
    silently corrupt every coverage view while leaving the stored
    record shapes intact (see tests/README.md).
    """
    active = [a for a in assignments if not a["cancelled"]]
    return "filled" if active else "unfilled"


class HrExtensions:
    """Extension surface over an :class:`HrStore` (final GAPS batch)."""

    def __init__(self, store):
        self.store = store
        self._shift_definitions = {}
        self._rotation_definitions = {}
        self._roster_assignments = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), "ext_" + action, target, details=details)

    @staticmethod
    def _is_employee(actor):
        return actor is not None and getattr(actor, "role", None) == "employee"

    def _scope_check(self, actor, person_ref):
        if self._is_employee(actor) and getattr(actor, "name", None) != person_ref:
            raise PermissionDenied(
                "permission denied: employee %r may not access records of person %r"
                % (getattr(actor, "name", None), person_ref)
            )

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _person_exists(self, person_ref):
        return any(
            p["person_ref"] == person_ref
            for p in self.store.list_persons(actor=None)
        )

    def _require_person_ref(self, person_ref):
        if not self._person_exists(person_ref):
            raise NotFoundError("person not found: %r" % (person_ref,))

    def _require_position(self, position_id):
        # Raises NotFoundError for an unknown position (core store).
        return self.store.get_position(position_id, actor=None)

    def _get_shift_definition(self, shift_id):
        record = self._shift_definitions.get(shift_id)
        if record is None:
            raise NotFoundError("shift definition not found: %r" % (shift_id,))
        return record

    def _get_rotation(self, rotation_id):
        record = self._rotation_definitions.get(rotation_id)
        if record is None:
            raise NotFoundError("rotation definition not found: %r" % (rotation_id,))
        return record

    def _get_assignment(self, assignment_id):
        record = self._roster_assignments.get(assignment_id)
        if record is None:
            raise NotFoundError("roster assignment not found: %r" % (assignment_id,))
        return record

    @staticmethod
    def _copy_rotation(record):
        copied = dict(record)
        copied["person_refs"] = list(record["person_refs"])
        return copied

    # -- shift definitions (definitions as data) -----------------------
    # A shift definition is a kind label plus clock labels, held as
    # data. It generates nothing: no dated assignment is ever
    # produced from a definition on this surface.

    def create_shift_definition(self, kind, start_label, end_label, actor, title=""):
        """Create a shift definition record. Action: performance_write."""
        _require_actor(actor, "performance_write")
        if kind not in SHIFT_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(SHIFT_KINDS),))
        start = _validate_clock_label(start_label, "start_label")
        end = _validate_clock_label(end_label, "end_label")
        _validate_string(title, "title")
        with self._lock:
            shift_id = self._next_id("shf")
            record = {
                "id": shift_id,
                "kind": kind,
                "start_label": start,
                "end_label": end,
                "title": title,
                "definition_only": True,
                "generated_here": False,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._shift_definitions[shift_id] = record
            self._audit(actor, "shift_create", shift_id,
                        details={"kind": kind})
            return dict(record)

    def get_shift_definition(self, shift_id, actor=None):
        """Return one shift definition. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            return dict(self._get_shift_definition(shift_id))

    def list_shift_definitions(self, actor=None):
        """Return shift definitions sorted by id. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            return [dict(r) for r in self._sorted(self._shift_definitions.values())]

    # -- rotation definitions (definitions as data) --------------------
    # A rotation definition binds an ordered list of opaque
    # person_refs to a core position. The ordering is the caller's,
    # recorded verbatim; nothing rotates, expands, or schedules
    # from it here.

    def create_rotation(self, position_id, title, person_refs, actor):
        """Create a rotation definition bound to a core position.

        Action: performance_write. The position must exist in the
        core and every person_ref must name a core person record;
        person_refs must be a non-empty list with no duplicates.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(title, "rotation title")
        if not isinstance(person_refs, (list, tuple)) or not person_refs:
            raise ValidationError("person_refs must be a non-empty list")
        refs = []
        for ref in person_refs:
            _validate_non_empty(ref, "person_ref")
            if ref in refs:
                raise ValidationError("person_refs contains a duplicate: %r" % (ref,))
            refs.append(ref)
        with self._lock:
            self._require_position(position_id)
            for ref in refs:
                self._require_person_ref(ref)
            rotation_id = self._next_id("rot")
            record = {
                "id": rotation_id,
                "position_id": position_id,
                "title": title,
                "person_refs": refs,
                "definition_only": True,
                "generated_here": False,
                "optimized_here": False,
                "automated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rotation_definitions[rotation_id] = record
            self._audit(actor, "rotation_create", rotation_id,
                        details={"position_id": position_id})
            return self._copy_rotation(record)

    def _rotation_visible(self, actor, record):
        """Employee readers see only rotations they are a member of."""
        if self._is_employee(actor):
            return getattr(actor, "name", None) in record["person_refs"]
        return True

    def get_rotation(self, rotation_id, actor=None):
        """Return one rotation definition. Action: performance_read.

        Employee scope: an employee who is not a member of the
        rotation is denied, as with other person-bound reads.
        """
        _maybe_require(actor, "performance_read")
        with self._lock:
            record = self._get_rotation(rotation_id)
            if not self._rotation_visible(actor, record):
                raise PermissionDenied(
                    "permission denied: employee %r is not a member of rotation %r"
                    % (getattr(actor, "name", None), rotation_id)
                )
            return self._copy_rotation(record)

    def list_rotations(self, actor=None):
        """Return rotation definitions sorted by id. Action: performance_read.

        Employee readers see only rotations they are a member of.
        """
        _maybe_require(actor, "performance_read")
        with self._lock:
            records = [r for r in self._sorted(self._rotation_definitions.values())
                       if self._rotation_visible(actor, r)]
            return [self._copy_rotation(r) for r in records]

    # -- roster assignments (caller-recorded records) ------------------
    # An assignment record states that one person is recorded as
    # working one shift at one position on one date. It is entered
    # by the caller; the substrate decided nothing.

    def record_roster_assignment(self, date_value, shift_id, position_id,
                                 person_ref, actor):
        """Record one roster assignment. Action: performance_write.

        The date must be an ISO date, the shift definition and the
        core position must exist, and the person_ref must name a
        core person. A duplicate active assignment (same person,
        date, and shift) is a validation error; re-recording is
        allowed once the earlier assignment is cancelled.
        """
        _require_actor(actor, "performance_write")
        _validate_date(date_value, "date")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            self._get_shift_definition(shift_id)
            self._require_position(position_id)
            self._require_person_ref(person_ref)
            for existing in self._roster_assignments.values():
                if (
                    not existing["cancelled"]
                    and existing["person_ref"] == person_ref
                    and existing["date"] == date_value
                    and existing["shift_id"] == shift_id
                ):
                    raise ValidationError(
                        "person %r already has an active assignment to shift %r on %r"
                        % (person_ref, shift_id, date_value)
                    )
            assignment_id = self._next_id("ros")
            record = {
                "id": assignment_id,
                "date": date_value,
                "shift_id": shift_id,
                "position_id": position_id,
                "person_ref": person_ref,
                "source": "recorded",
                "decided_here": False,
                "assigned_automatically": False,
                "optimized_here": False,
                "cancelled": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._roster_assignments[assignment_id] = record
            self._audit(actor, "assignment_create", assignment_id,
                        details={"person_ref": person_ref, "date": date_value,
                                 "shift_id": shift_id})
            return dict(record)

    def cancel_roster_assignment(self, assignment_id, actor):
        """Cancel a roster assignment (a recorded event).

        Action: performance_write. Cancellation is a flag on the
        record, mirroring the core lifecycle convention; the record
        itself is never deleted.
        """
        _require_actor(actor, "performance_write")
        with self._lock:
            record = self._get_assignment(assignment_id)
            if record["cancelled"]:
                raise ValidationError(
                    "roster assignment already cancelled: %r" % (assignment_id,)
                )
            record["cancelled"] = True
            self._audit(actor, "assignment_cancel", assignment_id, details={})
            return dict(record)

    def get_roster_assignment(self, assignment_id, actor=None):
        """Return one roster assignment. Action: performance_read (+ scope)."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            record = self._get_assignment(assignment_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_roster_assignments(self, actor=None, date=None, person_ref=None,
                                position_id=None, shift_id=None):
        """Return roster assignments, optionally filtered.

        Action: performance_read. Employee readers see only their
        own assignments, exactly as the core scopes person-bound
        records.
        """
        _maybe_require(actor, "performance_read")
        if date is not None:
            _validate_date(date, "date")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._roster_assignments.values())
            if date is not None:
                records = [r for r in records if r["date"] == date]
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if position_id is not None:
                records = [r for r in records if r["position_id"] == position_id]
            if shift_id is not None:
                records = [r for r in records if r["shift_id"] == shift_id]
            if self._is_employee(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if r["person_ref"] == name]
            return [dict(r) for r in self._sorted(records)]

    # -- derived views (derived at read, never stored) -----------------

    def rotation_view(self, rotation_id, on_date, actor):
        """Coverage view for one rotation on one date.

        Action: report_read. For every shift definition, the pair
        state derives through :func:`_derive_pair_state` from the
        recorded assignments matching the rotation's position, the
        shift, the date, and rotation membership. The view is a
        derivation over the records; the stored rotation record
        carries no coverage or status key.
        """
        _require_actor(actor, "report_read")
        _validate_date(on_date, "on_date")
        with self._lock:
            rotation = self._get_rotation(rotation_id)
            coverage = []
            for shift in self._sorted(self._shift_definitions.values()):
                matching = [
                    a for a in self._roster_assignments.values()
                    if a["date"] == on_date
                    and a["shift_id"] == shift["id"]
                    and a["position_id"] == rotation["position_id"]
                    and a["person_ref"] in rotation["person_refs"]
                ]
                active = [a for a in matching if not a["cancelled"]]
                coverage.append({
                    "shift_id": shift["id"],
                    "kind": shift["kind"],
                    "state": _derive_pair_state(matching),
                    "assignment_count": len(active),
                    "person_refs": sorted(a["person_ref"] for a in active),
                })
            return {
                "rotation": self._copy_rotation(rotation),
                "date": on_date,
                "coverage": coverage,
                "filled_count": sum(1 for c in coverage if c["state"] == "filled"),
                "unfilled_count": sum(1 for c in coverage if c["state"] == "unfilled"),
            }

    def schedule_summary(self, actor):
        """Counts over the scheduling records, derived at read.

        Action: report_read. Counts only -- no schedule is
        constructed and no figure is stored anywhere.
        """
        _require_actor(actor, "report_read")
        with self._lock:
            assignments = list(self._roster_assignments.values())
            active = [a for a in assignments if not a["cancelled"]]
            by_kind = {kind: 0 for kind in SHIFT_KINDS}
            shift_kinds = {s["id"]: s["kind"]
                           for s in self._shift_definitions.values()}
            for assignment in active:
                by_kind[shift_kinds[assignment["shift_id"]]] += 1
            return {
                "shift_definitions": len(self._shift_definitions),
                "rotation_definitions": len(self._rotation_definitions),
                "roster_assignments": len(assignments),
                "active_assignments": len(active),
                "cancelled_assignments": len(assignments) - len(active),
                "assignments_by_shift_kind": by_kind,
                "method": "deterministic_counts",
            }
