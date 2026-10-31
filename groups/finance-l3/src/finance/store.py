"""Finance store: programs, participants, earned-wage accruals and
access requests, disbursements, travel bookings, budgets, financial
wellness offerings and enrollments, and program reporting.

Clean-room implementation of the union spec's implementation contract.

Two boundaries are enforced on every program-scoped operation:

1. Membership -- the actor must be a member of the program, or hold
   the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`finance.access`) when
   the actor is a User-like object. A plain string actor carries
   identity (for provenance) but no role, so role enforcement for
   those happens in the service layer.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``prog-``, ``part-``, ``acc-``,
``req-``, ``dis-``, ``bkg-``, ``bud-``, ``wel-``, ``enr-``).

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.

All money is integer cents: any amount that is not a Python ``int``
(booleans and floats included, even integral floats) raises
:class:`ValidationError`. A missing object (including an id that
belongs to another program) raises :class:`NotFoundError`; a
malformed reference or value inside a payload raises
:class:`ValidationError`.

High-baseline uplift [L3] (AU-5 fail closed): every mutating method
is wrapped by :func:`_fail_closed` -- it runs against a snapshot of
the store state, and if its audit write raises
:class:`~finance.errors.AuditWriteError` (the entry could not be durably
recorded), the snapshot is restored in full (records and id
counters) and the error propagates, so an operation whose audit
write fails does not proceed. The snapshot pattern is the proven
one from ``groups/accounting-l3`` / ``groups/ai-l3`` (our own
Apache-2.0 code), applied to this store's nine record dicts and
program-order list.
"""

import copy
import functools
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

PARTICIPANT_KINDS = ("employee", "traveler")
PARTICIPANT_STATUSES = ("active", "inactive")
ACCESS_STATUSES = ("requested", "approved", "denied", "disbursed", "void")
BOOKING_KINDS = ("air", "hotel")
BOOKING_STATUSES = ("recorded", "confirmed", "cancelled")
WELLNESS_KINDS = ("education", "coaching", "budgeting", "savings", "counseling")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _is_admin(actor):
    return getattr(actor, "role", None) == "admin"


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _require_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % (what,))
    return value


def _validate_cents_nonnegative(value, what):
    _require_int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _validate_cents_positive(value, what):
    _require_int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _validate_date(value, what="date"):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("%s is not a valid calendar date: %r" % (what, value)) from exc
    return value


def _validate_period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError("%s must be a period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError("%s is not a valid period: %r" % (what, value)) from exc
    return value


def _check_access_cap(earned_cents, committed_cents, amount_cents):
    """Enforce the earned cap for one (participant, period) accrual.

    ``committed_cents`` is the period's already-committed total
    (pending plus accessed amounts). A request that would push the
    committed total even one cent over the period's earned amount is
    rejected whole.
    """
    if committed_cents + amount_cents > earned_cents:
        raise ValidationError(
            "access request exceeds earned wages for the period: "
            "earned %d, committed %d, requested %d"
            % (earned_cents, committed_cents, amount_cents)
        )
    return True


def _fail_closed(method):
    """Wrap a store operation so an audit write failure rolls it back.

    High-baseline uplift (AU-5) [L3]: the wrapped method runs against a
    snapshot of the store state; if it raises
    :class:`~finance.errors.AuditWriteError` (its audit entry could not be
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


class FinanceStore:
    """In-memory store for the finance service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._programs = {}
        self._program_order = []
        self._participants = {}
        self._accruals = {}
        self._access_requests = {}
        self._disbursements = {}
        self._bookings = {}
        self._budgets = {}  # (program_id, period) -> budget dict
        self._wellness_offerings = {}
        self._enrollments = {}
        self._counters = {
            "prog": 0,
            "part": 0,
            "acc": 0,
            "req": 0,
            "dis": 0,
            "bkg": 0,
            "bud": 0,
            "wel": 0,
            "enr": 0,
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
            copy.deepcopy(self._programs),
            copy.deepcopy(self._program_order),
            copy.deepcopy(self._participants),
            copy.deepcopy(self._accruals),
            copy.deepcopy(self._access_requests),
            copy.deepcopy(self._disbursements),
            copy.deepcopy(self._bookings),
            copy.deepcopy(self._budgets),
            copy.deepcopy(self._wellness_offerings),
            copy.deepcopy(self._enrollments),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        """Restore a snapshot taken by :meth:`_snapshot_state` [L3]."""
        (
            self._programs,
            self._program_order,
            self._participants,
            self._accruals,
            self._access_requests,
            self._disbursements,
            self._bookings,
            self._budgets,
            self._wellness_offerings,
            self._enrollments,
            self._counters,
        ) = snapshot

    def _get_program_record(self, program_id):
        program = self._programs.get(program_id)
        if program is None:
            raise NotFoundError("program not found: %r" % (program_id,))
        return program

    def _require_program_access(self, program_id, actor, action):
        """Return the program, enforcing membership then role permission."""
        program = self._get_program_record(program_id)
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        if actor_name(actor) not in program["members"] and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r is not a member of program %r"
                % (actor_name(actor), program_id)
            )
        _maybe_require(actor, action)
        return program

    @staticmethod
    def _copy_program(program):
        copied = dict(program)
        copied["members"] = list(program["members"])
        return copied

    @staticmethod
    def _copy_budget(budget):
        copied = dict(budget)
        copied["lines"] = [dict(line) for line in budget["lines"]]
        return copied

    def _get_participant_record(self, program_id, participant_id):
        participant = self._participants.get(participant_id)
        if participant is None or participant["program_id"] != program_id:
            raise NotFoundError("participant not found: %r" % (participant_id,))
        return participant

    def _get_accrual_record(self, program_id, accrual_id):
        accrual = self._accruals.get(accrual_id)
        if accrual is None or accrual["program_id"] != program_id:
            raise NotFoundError("accrual not found: %r" % (accrual_id,))
        return accrual

    def _get_access_request_record(self, program_id, request_id):
        request = self._access_requests.get(request_id)
        if request is None or request["program_id"] != program_id:
            raise NotFoundError("access request not found: %r" % (request_id,))
        return request

    def _get_booking_record(self, program_id, booking_id):
        booking = self._bookings.get(booking_id)
        if booking is None or booking["program_id"] != program_id:
            raise NotFoundError("booking not found: %r" % (booking_id,))
        return booking

    def _get_wellness_offering_record(self, program_id, offering_id):
        offering = self._wellness_offerings.get(offering_id)
        if offering is None or offering["program_id"] != program_id:
            raise NotFoundError("wellness offering not found: %r" % (offering_id,))
        return offering

    def _find_accrual(self, program_id, participant_id, period):
        for accrual in self._accruals.values():
            if (
                accrual["program_id"] == program_id
                and accrual["participant_id"] == participant_id
                and accrual["period"] == period
            ):
                return accrual
        return None

    def _accrual_totals(self, program_id, participant_id, period):
        """Return (accessed_cents, pending_cents) for one accrual key."""
        accessed = 0
        pending = 0
        for request in self._access_requests.values():
            if (
                request["program_id"] != program_id
                or request["participant_id"] != participant_id
                or request["period"] != period
            ):
                continue
            if request["status"] in ("approved", "disbursed"):
                accessed += request["amount_cents"]
            elif request["status"] == "requested":
                pending += request["amount_cents"]
        return accessed, pending

    def _accrual_view(self, accrual):
        """Return the accrual record plus fields derived on read."""
        view = dict(accrual)
        accessed, pending = self._accrual_totals(
            accrual["program_id"], accrual["participant_id"], accrual["period"]
        )
        view["accessed_cents"] = accessed
        view["pending_cents"] = pending
        view["available_cents"] = accrual["earned_cents"] - accessed - pending
        return view

    # -- programs and members ------------------------------------------

    @_fail_closed
    def create_program(self, name, actor):
        """Create a program; the creator is owner and first member."""
        _validate_non_empty(name, "program name")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "create_program")
        owner = actor_name(actor)
        with self._lock:
            program_id = self._next_id("prog")
            program = {
                "id": program_id,
                "name": name,
                "owner": owner,
                "members": [owner],
                "created_by": owner,
                "created_utc": _utc_now(),
            }
            self._programs[program_id] = program
            self._program_order.append(program_id)
            self._audit(actor, "program_create", program_id, details={"name": name})
            return self._copy_program(program)

    def list_programs(self, actor):
        """Return the program dicts ``actor`` may see."""
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "read")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            return [
                self._copy_program(self._programs[pid])
                for pid in self._program_order
                if admin or name in self._programs[pid]["members"]
            ]

    def get_program(self, program_id, actor):
        """Return one program dict visible to ``actor``."""
        with self._lock:
            program = self._require_program_access(program_id, actor, "read")
            return self._copy_program(program)

    @_fail_closed
    def add_member(self, program_id, username, actor):
        """Add ``username`` to a program. Owner or platform admin only."""
        _validate_non_empty(username, "username")
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        with self._lock:
            program = self._get_program_record(program_id)
            if program["owner"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: only the program owner or a platform "
                    "admin may add members to program %r" % (program_id,)
                )
            if username in program["members"]:
                raise ValidationError(
                    "user %r is already a member of program %r" % (username, program_id)
                )
            program["members"].append(username)
            self._audit(actor, "member_add", program_id, details={"username": username})
            return self._copy_program(program)

    # -- participants ---------------------------------------------------

    @_fail_closed
    def create_participant(self, program_id, ref, kind, actor):
        """Create a participant known only by an opaque ``ref``."""
        _validate_non_empty(ref, "participant ref")
        if kind not in PARTICIPANT_KINDS:
            raise ValidationError(
                "participant kind must be one of %s" % (", ".join(PARTICIPANT_KINDS),)
            )
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            for existing in self._participants.values():
                if existing["program_id"] == program_id and existing["ref"] == ref:
                    raise ValidationError(
                        "participant ref %r already exists in program %r"
                        % (ref, program_id)
                    )
            participant_id = self._next_id("part")
            participant = {
                "id": participant_id,
                "program_id": program_id,
                "ref": ref,
                "kind": kind,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._participants[participant_id] = participant
            self._audit(
                actor, "participant_create", participant_id, details={"kind": kind}
            )
            return dict(participant)

    def get_participant(self, program_id, participant_id, actor):
        """Return one participant dict from a program."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return dict(self._get_participant_record(program_id, participant_id))

    def list_participants(self, program_id, actor, kind=None):
        """Return a program's participants, in creation order."""
        if kind is not None and kind not in PARTICIPANT_KINDS:
            raise ValidationError("unknown participant kind: %r" % (kind,))
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(p)
                for p in self._participants.values()
                if p["program_id"] == program_id and (kind is None or p["kind"] == kind)
            ]

    @_fail_closed
    def set_participant_status(self, program_id, participant_id, status, actor):
        """Set a participant's status to ``active`` or ``inactive``."""
        if status not in PARTICIPANT_STATUSES:
            raise ValidationError(
                "participant status must be one of %s"
                % (", ".join(PARTICIPANT_STATUSES),)
            )
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            participant = self._get_participant_record(program_id, participant_id)
            participant["status"] = status
            self._audit(
                actor, "participant_status", participant_id, details={"status": status}
            )
            return dict(participant)

    # -- accruals --------------------------------------------------------

    @_fail_closed
    def record_accrual(self, program_id, participant_id, period, earned_cents, actor):
        """Record wages already earned by an employee for one period."""
        _validate_period(period, "period")
        _validate_cents_nonnegative(earned_cents, "earned_cents")
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            participant = self._get_participant_record(program_id, participant_id)
            if participant["kind"] != "employee":
                raise ValidationError(
                    "accruals may only be recorded for participants of kind 'employee'"
                )
            if self._find_accrual(program_id, participant_id, period) is not None:
                raise ValidationError(
                    "an accrual already exists for participant %r in period %r"
                    % (participant_id, period)
                )
            accrual_id = self._next_id("acc")
            accrual = {
                "id": accrual_id,
                "program_id": program_id,
                "participant_id": participant_id,
                "period": period,
                "earned_cents": earned_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._accruals[accrual_id] = accrual
            self._audit(actor, "accrual_record", accrual_id, details={"period": period})
            return dict(accrual)

    def get_accrual(self, program_id, accrual_id, actor):
        """Return one accrual view (record plus derived fields)."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return self._accrual_view(self._get_accrual_record(program_id, accrual_id))

    def list_accruals(self, program_id, actor, participant_id=None):
        """Return a program's accrual views, in creation order."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                self._accrual_view(a)
                for a in self._accruals.values()
                if a["program_id"] == program_id
                and (participant_id is None or a["participant_id"] == participant_id)
            ]

    # -- access requests ---------------------------------------------------

    @_fail_closed
    def request_access(self, program_id, participant_id, period, amount_cents, date, actor):
        """Request access to earned wages, enforcing the earned cap."""
        _validate_period(period, "period")
        _validate_cents_positive(amount_cents, "amount_cents")
        _validate_date(date, "date")
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            participant = self._get_participant_record(program_id, participant_id)
            if participant["kind"] != "employee":
                raise ValidationError(
                    "access may only be requested for participants of kind 'employee'"
                )
            accrual = self._find_accrual(program_id, participant_id, period)
            if accrual is None:
                raise ValidationError(
                    "no accrual exists for participant %r in period %r"
                    % (participant_id, period)
                )
            accessed, pending = self._accrual_totals(program_id, participant_id, period)
            _check_access_cap(accrual["earned_cents"], accessed + pending, amount_cents)
            request_id = self._next_id("req")
            request = {
                "id": request_id,
                "program_id": program_id,
                "participant_id": participant_id,
                "period": period,
                "amount_cents": amount_cents,
                "date": date,
                "status": "requested",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "decided_by": None,
                "decided_utc": None,
                "disbursement_id": None,
            }
            self._access_requests[request_id] = request
            self._audit(actor, "access_request", request_id, details={"period": period})
            return dict(request)

    def get_access_request(self, program_id, request_id, actor):
        """Return one access request dict from a program."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return dict(self._get_access_request_record(program_id, request_id))

    def list_access_requests(self, program_id, actor, status=None):
        """Return a program's access requests, in creation order."""
        if status is not None and status not in ACCESS_STATUSES:
            raise ValidationError("unknown access request status: %r" % (status,))
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(r)
                for r in self._access_requests.values()
                if r["program_id"] == program_id
                and (status is None or r["status"] == status)
            ]

    @_fail_closed
    def decide_access(self, program_id, request_id, approve, actor):
        """Approve or deny a ``requested`` access request.

        Separation of duties: the decider is never the request's
        creator.
        """
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        with self._lock:
            self._require_program_access(program_id, actor, "decide")
            request = self._get_access_request_record(program_id, request_id)
            if request["status"] != "requested":
                raise ValidationError(
                    "access request in status %r cannot be decided"
                    % (request["status"],)
                )
            if actor_name(actor) == request["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not decide their own "
                    "access request"
                )
            request["status"] = "approved" if approve else "denied"
            request["decided_by"] = actor_name(actor)
            request["decided_utc"] = _utc_now()
            self._audit(
                actor,
                "access_approve" if approve else "access_deny",
                request_id,
            )
            return dict(request)

    @_fail_closed
    def void_access(self, program_id, request_id, actor):
        """Move an access request ``requested``/``denied`` -> ``void``."""
        with self._lock:
            program = self._require_program_access(program_id, actor, "enter")
            request = self._get_access_request_record(program_id, request_id)
            if request["status"] not in ("requested", "denied"):
                raise ValidationError(
                    "access request in status %r cannot be voided"
                    % (request["status"],)
                )
            if (
                actor_name(actor) != request["created_by"]
                and actor_name(actor) != program["owner"]
                and not _is_admin(actor)
            ):
                raise PermissionDenied(
                    "permission denied: only the creator, the program owner, or a "
                    "platform admin may void this access request"
                )
            request["status"] = "void"
            self._audit(actor, "access_void", request_id)
            return dict(request)

    # -- disbursements -----------------------------------------------------

    @_fail_closed
    def record_disbursement(self, program_id, request_id, date, actor, method=""):
        """Record that an approved access amount was disbursed externally.

        This build records disbursements; it executes nothing. The
        amount, participant and period are copied from the request,
        whose status becomes ``disbursed``.
        """
        _validate_date(date, "date")
        if method is None:
            method = ""
        _validate_string(method, "method")
        with self._lock:
            self._require_program_access(program_id, actor, "record")
            request = self._get_access_request_record(program_id, request_id)
            if request["status"] != "approved":
                raise ValidationError(
                    "disbursements may only be recorded against an approved "
                    "access request"
                )
            disbursement_id = self._next_id("dis")
            disbursement = {
                "id": disbursement_id,
                "program_id": program_id,
                "request_id": request_id,
                "participant_id": request["participant_id"],
                "period": request["period"],
                "amount_cents": request["amount_cents"],
                "date": date,
                "method": method,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._disbursements[disbursement_id] = disbursement
            request["status"] = "disbursed"
            request["disbursement_id"] = disbursement_id
            self._audit(
                actor,
                "disbursement_record",
                disbursement_id,
                details={"request_id": request_id},
            )
            return dict(disbursement)

    def list_disbursements(self, program_id, actor, request_id=None):
        """Return a program's disbursements, in creation order."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(d)
                for d in self._disbursements.values()
                if d["program_id"] == program_id
                and (request_id is None or d["request_id"] == request_id)
            ]

    # -- bookings ------------------------------------------------------------

    @_fail_closed
    def create_booking(self, program_id, participant_id, kind, start_date, end_date, amount_cents, actor):
        """Create a booking record for a traveler participant."""
        if kind not in BOOKING_KINDS:
            raise ValidationError(
                "booking kind must be one of %s" % (", ".join(BOOKING_KINDS),)
            )
        _validate_date(start_date, "start_date")
        _validate_date(end_date, "end_date")
        if end_date < start_date:
            raise ValidationError("end_date must not be before start_date")
        _validate_cents_nonnegative(amount_cents, "amount_cents")
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            participant = self._get_participant_record(program_id, participant_id)
            if participant["kind"] != "traveler":
                raise ValidationError(
                    "bookings may only be created for participants of kind 'traveler'"
                )
            booking_id = self._next_id("bkg")
            booking = {
                "id": booking_id,
                "program_id": program_id,
                "participant_id": participant_id,
                "kind": kind,
                "start_date": start_date,
                "end_date": end_date,
                "amount_cents": amount_cents,
                "status": "recorded",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._bookings[booking_id] = booking
            self._audit(actor, "booking_create", booking_id, details={"kind": kind})
            return dict(booking)

    def get_booking(self, program_id, booking_id, actor):
        """Return one booking dict from a program."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return dict(self._get_booking_record(program_id, booking_id))

    def list_bookings(self, program_id, actor, status=None, kind=None):
        """Return a program's bookings, in creation order."""
        if status is not None and status not in BOOKING_STATUSES:
            raise ValidationError("unknown booking status: %r" % (status,))
        if kind is not None and kind not in BOOKING_KINDS:
            raise ValidationError("unknown booking kind: %r" % (kind,))
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(b)
                for b in self._bookings.values()
                if b["program_id"] == program_id
                and (status is None or b["status"] == status)
                and (kind is None or b["kind"] == kind)
            ]

    @_fail_closed
    def confirm_booking(self, program_id, booking_id, actor):
        """Move a booking ``recorded`` -> ``confirmed``."""
        with self._lock:
            self._require_program_access(program_id, actor, "record")
            booking = self._get_booking_record(program_id, booking_id)
            if booking["status"] != "recorded":
                raise ValidationError(
                    "booking in status %r cannot be confirmed" % (booking["status"],)
                )
            booking["status"] = "confirmed"
            self._audit(actor, "booking_confirm", booking_id)
            return dict(booking)

    @_fail_closed
    def cancel_booking(self, program_id, booking_id, actor):
        """Move a booking ``recorded``/``confirmed`` -> ``cancelled``."""
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            booking = self._get_booking_record(program_id, booking_id)
            if booking["status"] not in ("recorded", "confirmed"):
                raise ValidationError(
                    "booking in status %r cannot be cancelled" % (booking["status"],)
                )
            booking["status"] = "cancelled"
            self._audit(actor, "booking_cancel", booking_id)
            return dict(booking)

    # -- budgets ---------------------------------------------------------------

    @_fail_closed
    def set_budget(self, program_id, period, lines, actor):
        """Set (or replace the lines of) the budget for a period."""
        _validate_period(period, "period")
        if not isinstance(lines, (list, tuple)) or len(lines) < 1:
            raise ValidationError("budget lines must be a list of at least one line")
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            normalized = []
            seen = set()
            total = 0
            for line in lines:
                if not isinstance(line, dict):
                    raise ValidationError("budget line must be an object")
                category = line.get("category")
                _validate_non_empty(category, "budget line category")
                if category in seen:
                    raise ValidationError(
                        "budget line repeats category %r" % (category,)
                    )
                seen.add(category)
                limit = line.get("limit_cents")
                _validate_cents_nonnegative(limit, "limit_cents")
                total += limit
                normalized.append({"category": category, "limit_cents": limit})
            key = (program_id, period)
            existing = self._budgets.get(key)
            now = _utc_now()
            if existing is not None:
                existing["lines"] = normalized
                existing["total_cents"] = total
                existing["updated_utc"] = now
                budget = existing
            else:
                budget_id = self._next_id("bud")
                budget = {
                    "id": budget_id,
                    "program_id": program_id,
                    "period": period,
                    "lines": normalized,
                    "total_cents": total,
                    "created_by": actor_name(actor),
                    "created_utc": now,
                    "updated_utc": now,
                }
                self._budgets[key] = budget
            self._audit(actor, "budget_set", budget["id"], details={"period": period})
            return self._copy_budget(budget)

    def get_budget(self, program_id, period, actor):
        """Return the budget for a period, or raise NotFoundError."""
        _validate_period(period, "period")
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            budget = self._budgets.get((program_id, period))
            if budget is None:
                raise NotFoundError(
                    "no budget set for period %r in program %r" % (period, program_id)
                )
            return self._copy_budget(budget)

    def _period_spend(self, program_id, period):
        """Return {category: spent_cents} for one period, from records.

        Booking kinds contribute the non-cancelled (recorded or
        confirmed) bookings starting in the period; disbursements
        dated in the period contribute under ``earned_wage``.
        """
        spent = {}
        for booking in self._bookings.values():
            if booking["program_id"] != program_id:
                continue
            if booking["status"] not in ("recorded", "confirmed"):
                continue
            if booking["start_date"][:7] != period:
                continue
            spent[booking["kind"]] = spent.get(booking["kind"], 0) + booking["amount_cents"]
        for disbursement in self._disbursements.values():
            if disbursement["program_id"] != program_id:
                continue
            if disbursement["date"][:7] != period:
                continue
            spent["earned_wage"] = (
                spent.get("earned_wage", 0) + disbursement["amount_cents"]
            )
        return spent

    def spend_vs_budget(self, program_id, period, actor):
        """Compare budgeted amounts against spend computed from records."""
        _validate_period(period, "period")
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            budget = self._budgets.get((program_id, period))
            if budget is None:
                raise NotFoundError(
                    "no budget set for period %r in program %r" % (period, program_id)
                )
            spent_by_category = self._period_spend(program_id, period)
            budgeted = {line["category"] for line in budget["lines"]}
            lines = []
            total_budgeted = 0
            total_spent = 0
            for line in budget["lines"]:
                spent = spent_by_category.get(line["category"], 0)
                variance = line["limit_cents"] - spent
                lines.append(
                    {
                        "category": line["category"],
                        "limit_cents": line["limit_cents"],
                        "spent_cents": spent,
                        "variance_cents": variance,
                        "over_budget": spent > line["limit_cents"],
                    }
                )
                total_budgeted += line["limit_cents"]
                total_spent += spent
            unbudgeted = []
            for category in sorted(spent_by_category):
                if category in budgeted:
                    continue
                unbudgeted.append(
                    {"category": category, "spent_cents": spent_by_category[category]}
                )
                total_spent += spent_by_category[category]
            return {
                "program_id": program_id,
                "period": period,
                "lines": lines,
                "total_budgeted_cents": total_budgeted,
                "total_spent_cents": total_spent,
                "total_variance_cents": total_budgeted - total_spent,
                "unbudgeted": unbudgeted,
            }

    # -- wellness offerings and enrollments -------------------------------------

    @_fail_closed
    def create_wellness_offering(self, program_id, title, kind, actor):
        """Register a financial wellness offering for a program."""
        _validate_non_empty(title, "offering title")
        if kind not in WELLNESS_KINDS:
            raise ValidationError(
                "wellness kind must be one of %s" % (", ".join(WELLNESS_KINDS),)
            )
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            offering_id = self._next_id("wel")
            offering = {
                "id": offering_id,
                "program_id": program_id,
                "title": title,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._wellness_offerings[offering_id] = offering
            self._audit(actor, "wellness_create", offering_id, details={"kind": kind})
            return dict(offering)

    def get_wellness_offering(self, program_id, offering_id, actor):
        """Return one wellness offering dict from a program."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return dict(self._get_wellness_offering_record(program_id, offering_id))

    def list_wellness_offerings(self, program_id, actor):
        """Return a program's wellness offerings, in creation order."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(o)
                for o in self._wellness_offerings.values()
                if o["program_id"] == program_id
            ]

    @_fail_closed
    def enroll_participant(self, program_id, offering_id, participant_id, actor):
        """Enroll a participant in a wellness offering."""
        with self._lock:
            self._require_program_access(program_id, actor, "enter")
            self._get_wellness_offering_record(program_id, offering_id)
            self._get_participant_record(program_id, participant_id)
            for existing in self._enrollments.values():
                if (
                    existing["program_id"] == program_id
                    and existing["offering_id"] == offering_id
                    and existing["participant_id"] == participant_id
                ):
                    raise ValidationError(
                        "participant %r is already enrolled in offering %r"
                        % (participant_id, offering_id)
                    )
            enrollment_id = self._next_id("enr")
            enrollment = {
                "id": enrollment_id,
                "program_id": program_id,
                "offering_id": offering_id,
                "participant_id": participant_id,
                "status": "enrolled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrollments[enrollment_id] = enrollment
            self._audit(
                actor,
                "wellness_enroll",
                enrollment_id,
                details={"offering_id": offering_id},
            )
            return dict(enrollment)

    def list_wellness_enrollments(self, program_id, actor, offering_id=None):
        """Return a program's wellness enrollments, in creation order."""
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            return [
                dict(e)
                for e in self._enrollments.values()
                if e["program_id"] == program_id
                and (offering_id is None or e["offering_id"] == offering_id)
            ]

    # -- reporting ----------------------------------------------------------------

    def program_summary(self, program_id, period, actor):
        """Compute a per-period program summary on read, from records."""
        _validate_period(period, "period")
        with self._lock:
            self._require_program_access(program_id, actor, "read")
            participants = sum(
                1 for p in self._participants.values() if p["program_id"] == program_id
            )
            earned = sum(
                a["earned_cents"]
                for a in self._accruals.values()
                if a["program_id"] == program_id and a["period"] == period
            )
            accessed = 0
            pending = 0
            for request in self._access_requests.values():
                if request["program_id"] != program_id or request["period"] != period:
                    continue
                if request["status"] in ("approved", "disbursed"):
                    accessed += request["amount_cents"]
                elif request["status"] == "requested":
                    pending += request["amount_cents"]
            disbursed = sum(
                d["amount_cents"]
                for d in self._disbursements.values()
                if d["program_id"] == program_id and d["date"][:7] == period
            )
            bookings = {
                "air": {"count": 0, "total_cents": 0},
                "hotel": {"count": 0, "total_cents": 0},
            }
            for booking in self._bookings.values():
                if booking["program_id"] != program_id:
                    continue
                if booking["status"] == "cancelled":
                    continue
                if booking["start_date"][:7] != period:
                    continue
                bucket = bookings[booking["kind"]]
                bucket["count"] += 1
                bucket["total_cents"] += booking["amount_cents"]
            enrollments = sum(
                1 for e in self._enrollments.values() if e["program_id"] == program_id
            )
            return {
                "program_id": program_id,
                "period": period,
                "participants": participants,
                "earned_cents": earned,
                "accessed_cents": accessed,
                "disbursed_cents": disbursed,
                "pending_cents": pending,
                "bookings": bookings,
                "wellness_enrollments": enrollments,
            }
