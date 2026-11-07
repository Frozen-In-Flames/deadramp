"""Final GAPS batch extensions for the Finance L2 merged build
(Group 31).

Clean-room, standard-library-only records extensions for the 10
open entries this group's GAPS.md section carries: 7 built as
in-substrate execution-*request* records plus verbatim outcome
reports over the core's own records, and 3 shipped as labeled
reference implementations (the drafted stub-engine families). See
``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`FinanceStore`; the core
  modules are untouched (byte-identical). Core state (programs,
  participants, accruals, access requests, bookings, wellness
  offerings and enrollments) is always read through the core
  store's public API, never re-implemented, and no extension
  operation writes core state.
- **Records, not execution** is the founding discipline and this
  surface does not repeal it: nothing here moves money, books
  travel, lends, trades, remits, verifies an account, calculates
  wages, or streams anything. Every execution remainder lands as a
  request record (``state: recorded_*_only``) plus outcome reports
  stored verbatim as reported by the external system that actually
  acted. Each record carries its honesty label on its face
  (``paid_here`` / ``booked_here`` / ``ticketed_here`` /
  ``delivered_here`` / ``disbursed_here`` / ``executed_here`` /
  ``filed_here`` / ``remitted_here`` / ``verified_here`` /
  ``streamed_here`` / ``computed_here`` — all ``False``).
- **Money is integer cents, everywhere.** Every ``*_cents`` field
  is validated exactly as the core validates: a Python ``int``,
  booleans and floats rejected at the boundary, and a rejected
  operation consumes no id and stores nothing.
- **The earned cap extends to disbursement execution requests.**
  A disbursement execution request draws against the same
  (participant, period) accrual as a core access request: its
  amount, plus the amounts of this surface's still-outstanding
  requests for that accrual, may not exceed the accrual view's
  derived ``available_cents`` (earned minus the core's accessed
  and pending totals). The comparison lives in the module-level
  seam :func:`_check_disbursement_cap` — the batch's fresh
  negative-control target. A request whose latest report is
  ``reported_failed`` stops counting as outstanding: the rail
  reported that nothing moved, so the cap is released for a new
  request; every other request keeps counting, because this build
  cannot verify a release it did not observe.
- RBAC goes through :mod:`finance.access` exactly as the core
  enforces it: each extension operation maps onto an existing core
  action — creates / requests / registrations onto ``enter``,
  outcome reports and receipts onto ``record``, reads and derived
  views onto ``read`` — checked *before* any state change or id
  allocation for User-like actors, with denied attempts recorded
  on the core audit log as ``ext_<action>:denied``. Program
  membership (the second boundary) is enforced through the core
  store's own access-checked program read. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If the
  audit write raises, the record insertion and its id roll back
  before the error propagates: no extension record exists whose
  audit entry does not.
- People are known only by the core's opaque-reference
  participants: every person-shaped field on this surface is a
  core ``participant_id`` whose record must exist in the same
  program, so the core's pinned participant shape — which cannot
  hold a real name, bank account number, card number, or
  government identifier — governs this surface too. **No record
  shape in this module has a field that could hold a real account
  identifier, and no record shape carries a credit score field**;
  both absences are pinned by exact key-set tests and recursive
  key scans in ``tests/test_gaps_batch.py``.
- Derived values are derived at read and never stored: GRC
  posture counts, streaming totals, payroll sync totals,
  disbursement and wellness rollups. Stored records carry no
  derived key; tests pin that.
- The stub-engine families ship as labeled reference
  implementations: every record they create carries
  ``reference_stub: True`` (streaming receipts additionally carry
  ``reference_transport: True``).
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

RAILS = ("ach", "wire", "card")
KNOWN_RAILS = frozenset(RAILS)
DISBURSEMENT_REPORT_OUTCOMES = (
    "reported_paid",
    "reported_failed",
    "reported_pending",
)
KNOWN_DISBURSEMENT_REPORT_OUTCOMES = frozenset(DISBURSEMENT_REPORT_OUTCOMES)
BOOKING_EXECUTION_ACTIONS = (
    "inventory_hold",
    "ticket_issue",
    "reservation_confirm",
)
KNOWN_BOOKING_EXECUTION_ACTIONS = frozenset(BOOKING_EXECUTION_ACTIONS)
BOOKING_REPORT_OUTCOMES = (
    "reported_booked",
    "reported_ticketed",
    "reported_confirmed",
    "reported_failed",
)
KNOWN_BOOKING_REPORT_OUTCOMES = frozenset(BOOKING_REPORT_OUTCOMES)
WELLNESS_SESSION_OUTCOMES = (
    "reported_attended",
    "reported_completed",
    "reported_missed",
    "reported_cancelled",
)
KNOWN_WELLNESS_SESSION_OUTCOMES = frozenset(WELLNESS_SESSION_OUTCOMES)
TRADE_SIDES = ("buy", "sell")
KNOWN_TRADE_SIDES = frozenset(TRADE_SIDES)
TRADE_REPORT_OUTCOMES = (
    "reported_executed",
    "reported_rejected",
    "reported_pending",
    "reported_cancelled",
)
KNOWN_TRADE_REPORT_OUTCOMES = frozenset(TRADE_REPORT_OUTCOMES)
TAX_REPORT_OUTCOMES = (
    "reported_filed",
    "reported_accepted",
    "reported_rejected",
)
KNOWN_TAX_REPORT_OUTCOMES = frozenset(TAX_REPORT_OUTCOMES)
VERIFICATION_OUTCOMES = (
    "reported_verified",
    "reported_failed",
    "reported_pending",
)
KNOWN_VERIFICATION_OUTCOMES = frozenset(VERIFICATION_OUTCOMES)
MAPPABLE_RECORD_KINDS = (
    "participant",
    "booking",
    "accrual",
    "access_request",
    "wellness_offering",
)
KNOWN_MAPPABLE_RECORD_KINDS = frozenset(MAPPABLE_RECORD_KINDS)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _require_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % (what,))
    return value


def _cents_positive(value, what):
    _require_int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _cents_nonnegative(value, what):
    _require_int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _count_nonnegative(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _validate_period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError(
            "%s must be a period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid period: %r" % (what, value)) from exc
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _check_disbursement_cap(available_cents, committed_cents, amount_cents):
    """Enforce the earned cap for one disbursement execution request.

    ``available_cents`` is the accrual view's derived available
    amount (earned minus the core's accessed and pending totals);
    ``committed_cents`` is the total of this surface's outstanding
    disbursement execution requests against the same accrual. A
    request that would push the committed total even one cent over
    the available amount is rejected whole. This is the negative
    control's target.
    """
    if committed_cents + amount_cents > available_cents:
        raise ValidationError(
            "disbursement execution request exceeds earned wages "
            "available for the period: available %d, committed %d, "
            "requested %d" % (available_cents, committed_cents, amount_cents)
        )
    return True


class FinanceExtensions:
    """GAPS-batch extension surface over a core FinanceStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a permission, auditing a denial.

        Mirrors the core convention: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _program(self, program_id, actor):
        """Core access-checked program read (membership + read role).

        Raises NotFoundError for an unknown program and
        PermissionDenied for a non-member, exactly as the core does.
        """
        return self.store.get_program(program_id, actor)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed: an operation whose audit write fails
                # does not proceed -- the insertion and the id roll
                # back before the error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id, program_id):
        record = self._records.get((kind, record_id))
        if record is None or record["program_id"] != program_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, program_id):
        return copy.deepcopy(self._get(kind, record_id, program_id))

    def _list(self, kind, program_id, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["program_id"] != program_id:
                continue
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    def _participant(self, program_id, participant_id, actor):
        """Return the core participant (NotFoundError if absent)."""
        return self.store.get_participant(program_id, participant_id, actor)

    def _accrual_view(self, program_id, participant_id, period, actor):
        """Return the core accrual view for (participant, period)."""
        for view in self.store.list_accruals(
            program_id, actor, participant_id=participant_id
        ):
            if view["period"] == period:
                return view
        return None

    def _latest_disbursement_report(self, request_id):
        latest = None
        for key in self._order:
            if key[0] != "disbursement_execution_report":
                continue
            record = self._records[key]
            if record["request_id"] == request_id:
                latest = record
        return latest

    def _disbursement_committed(self, program_id, participant_id, period):
        """Outstanding disbursement-execution total for one accrual.

        A request counts unless its latest report is
        ``reported_failed`` (the rail reported nothing moved).
        """
        total = 0
        for key in self._order:
            if key[0] != "disbursement_execution_request":
                continue
            record = self._records[key]
            if (
                record["program_id"] != program_id
                or record["participant_id"] != participant_id
                or record["period"] != period
            ):
                continue
            latest = self._latest_disbursement_report(record["id"])
            if latest is not None and latest["outcome"] == "reported_failed":
                continue
            total += record["amount_cents"]
        return total

    # -- Instant disbursement execution / payment rails ----------------
    #
    # The execution remainder of earned wage access. The core
    # records disbursements and moves no money; this surface records
    # that a disbursement was *requested* against a named external
    # rail and stores, verbatim, the outcome the rail reported.
    # ``paid_here`` is False on every record.

    def request_disbursement_execution(
        self, program_id, participant_id, period, amount_cents, rail, actor
    ):
        """Record a request to disburse earned wages over a rail.

        The participant must be a core ``employee`` with an accrual
        for ``period``; the amount is integer cents and is capped by
        the earned cap (see :func:`_check_disbursement_cap`).
        Nothing is paid: the request is lodged as a record with
        ``paid_here: False``.
        """
        self._guard(actor, "enter", "ext_disbursement_execution_request",
                    target=participant_id)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _cents_positive(amount_cents, "amount_cents")
        _one_of(rail, KNOWN_RAILS, RAILS, "rail")
        participant = self._participant(program_id, participant_id, actor)
        if participant["kind"] != "employee":
            raise ValidationError(
                "disbursement execution may only be requested for "
                "participants of kind 'employee'"
            )
        view = self._accrual_view(program_id, participant_id, period, actor)
        if view is None:
            raise ValidationError(
                "no accrual exists for participant %r in period %r"
                % (participant_id, period)
            )
        committed = self._disbursement_committed(
            program_id, participant_id, period)
        _check_disbursement_cap(
            view["available_cents"], committed, amount_cents)
        return self._create(
            "disbursement_execution_request", "dexc",
            {"program_id": program_id, "participant_id": participant_id,
             "period": period, "amount_cents": amount_cents, "rail": rail,
             "paid_here": False, "state": "recorded_request_only"},
            actor, "ext_disbursement_execution_request")

    def record_disbursement_execution_report(
        self, program_id, request_id, outcome, actor, detail=None
    ):
        """Record a rail's reported outcome for an execution request.

        The outcome is stored verbatim as reported; the build paid
        nothing, so the report itself also carries
        ``paid_here: False``.
        """
        self._guard(actor, "record", "ext_disbursement_execution_report",
                    target=request_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_DISBURSEMENT_REPORT_OUTCOMES,
                DISBURSEMENT_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("disbursement_execution_request", request_id, program_id)
        return self._create(
            "disbursement_execution_report", "drep",
            {"program_id": program_id, "request_id": request_id,
             "outcome": outcome, "detail": detail, "paid_here": False},
            actor, "ext_disbursement_execution_report")

    def get_disbursement_execution_request(self, program_id, request_id, actor):
        self._guard(actor, "read", "ext_disbursement_execution_get",
                    target=request_id)
        self._program(program_id, actor)
        return self._fetch(
            "disbursement_execution_request", request_id, program_id)

    def list_disbursement_execution_requests(
        self, program_id, actor, participant_id=None
    ):
        self._guard(actor, "read", "ext_disbursement_execution_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list(
            "disbursement_execution_request", program_id, **filters)

    def list_disbursement_execution_reports(
        self, program_id, actor, request_id=None
    ):
        self._guard(actor, "read", "ext_disbursement_execution_report_list")
        self._program(program_id, actor)
        filters = {}
        if request_id is not None:
            filters["request_id"] = request_id
        return self._list(
            "disbursement_execution_report", program_id, **filters)

    def disbursement_execution_summary(self, program_id, actor):
        """Derived at read: request/report counts and totals over
        this surface's disbursement records. Nothing is stored."""
        self._guard(actor, "read", "ext_disbursement_execution_summary")
        self._program(program_id, actor)
        requests = self._list("disbursement_execution_request", program_id)
        reports = self._list("disbursement_execution_report", program_id)
        by_outcome = {o: 0 for o in DISBURSEMENT_REPORT_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {
            "program_id": program_id,
            "requests": len(requests),
            "reports": len(reports),
            "reports_by_outcome": by_outcome,
            "total_requested_cents": sum(
                r["amount_cents"] for r in requests),
            "paid_here": False,
            "derived": True,
            "method": "counts_over_disbursement_execution_records",
        }

    # -- Travel booking execution engines ------------------------------
    #
    # The execution remainder of travel booking. The core holds
    # booking records; this surface records that an execution action
    # was *requested* against an existing core booking and stores,
    # verbatim, the outcome the external system reported.
    # ``booked_here`` / ``ticketed_here`` are False on every record,
    # and a request plus a report leaves the core booking untouched.

    def request_booking_execution(
        self, program_id, booking_id, action_label, actor
    ):
        """Record a request to execute an action on a core booking.

        The booking must exist in the core. Nothing is booked and
        no ticket is issued: the request is a record with
        ``booked_here: False`` and ``ticketed_here: False``.
        """
        self._guard(actor, "enter", "ext_booking_execution_request",
                    target=booking_id)
        self._program(program_id, actor)
        _one_of(action_label, KNOWN_BOOKING_EXECUTION_ACTIONS,
                BOOKING_EXECUTION_ACTIONS, "action_label")
        booking = self.store.get_booking(program_id, booking_id, actor)
        return self._create(
            "booking_execution_request", "bexc",
            {"program_id": program_id, "booking_id": booking_id,
             "participant_id": booking["participant_id"],
             "action_label": action_label, "booked_here": False,
             "ticketed_here": False, "state": "recorded_request_only"},
            actor, "ext_booking_execution_request")

    def record_booking_execution_report(
        self, program_id, request_id, outcome, actor, detail=None
    ):
        """Record an external system's reported outcome, verbatim."""
        self._guard(actor, "record", "ext_booking_execution_report",
                    target=request_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_BOOKING_REPORT_OUTCOMES,
                BOOKING_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        request = self._get(
            "booking_execution_request", request_id, program_id)
        return self._create(
            "booking_execution_report", "brep",
            {"program_id": program_id, "request_id": request_id,
             "booking_id": request["booking_id"], "outcome": outcome,
             "detail": detail, "booked_here": False,
             "ticketed_here": False},
            actor, "ext_booking_execution_report")

    def get_booking_execution_request(self, program_id, request_id, actor):
        self._guard(actor, "read", "ext_booking_execution_get",
                    target=request_id)
        self._program(program_id, actor)
        return self._fetch("booking_execution_request", request_id, program_id)

    def list_booking_execution_requests(
        self, program_id, actor, booking_id=None
    ):
        self._guard(actor, "read", "ext_booking_execution_list")
        self._program(program_id, actor)
        filters = {}
        if booking_id is not None:
            filters["booking_id"] = booking_id
        return self._list("booking_execution_request", program_id, **filters)

    def list_booking_execution_reports(self, program_id, actor, request_id=None):
        self._guard(actor, "read", "ext_booking_execution_report_list")
        self._program(program_id, actor)
        filters = {}
        if request_id is not None:
            filters["request_id"] = request_id
        return self._list("booking_execution_report", program_id, **filters)

    # -- Financial wellness delivery tools -----------------------------
    #
    # The execution remainder of financial wellness. The core
    # registers offerings and enrollments; this surface records
    # delivery *sessions* scheduled against an existing core
    # enrollment and stores, verbatim, the outcome the delivering
    # party reported. Session content is delivered by others;
    # ``delivered_here`` is False on every record.

    def schedule_wellness_session(
        self, program_id, enrollment_id, session_label, actor
    ):
        """Record a wellness delivery session over a core enrollment.

        The enrollment must exist in the core; the session record
        copies its offering and participant ids. Nothing is
        delivered here.
        """
        self._guard(actor, "enter", "ext_wellness_session_schedule",
                    target=enrollment_id)
        self._program(program_id, actor)
        _non_empty(session_label, "session_label")
        enrollment = None
        for candidate in self.store.list_wellness_enrollments(
            program_id, actor
        ):
            if candidate["id"] == enrollment_id:
                enrollment = candidate
                break
        if enrollment is None:
            raise NotFoundError("enrollment not found: %r" % (enrollment_id,))
        return self._create(
            "wellness_session", "wses",
            {"program_id": program_id, "enrollment_id": enrollment_id,
             "offering_id": enrollment["offering_id"],
             "participant_id": enrollment["participant_id"],
             "session_label": session_label, "delivered_here": False,
             "state": "scheduled_record_only"},
            actor, "ext_wellness_session_schedule")

    def record_wellness_session_report(
        self, program_id, session_id, outcome, actor, detail=None
    ):
        """Record a delivering party's reported session outcome."""
        self._guard(actor, "record", "ext_wellness_session_report",
                    target=session_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_WELLNESS_SESSION_OUTCOMES,
                WELLNESS_SESSION_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        session = self._get("wellness_session", session_id, program_id)
        return self._create(
            "wellness_session_report", "wsrp",
            {"program_id": program_id, "session_id": session_id,
             "enrollment_id": session["enrollment_id"],
             "outcome": outcome, "detail": detail,
             "delivered_here": False},
            actor, "ext_wellness_session_report")

    def get_wellness_session(self, program_id, session_id, actor):
        self._guard(actor, "read", "ext_wellness_session_get",
                    target=session_id)
        self._program(program_id, actor)
        return self._fetch("wellness_session", session_id, program_id)

    def list_wellness_sessions(self, program_id, actor, enrollment_id=None):
        self._guard(actor, "read", "ext_wellness_session_list")
        self._program(program_id, actor)
        filters = {}
        if enrollment_id is not None:
            filters["enrollment_id"] = enrollment_id
        return self._list("wellness_session", program_id, **filters)

    def list_wellness_session_reports(self, program_id, actor, session_id=None):
        self._guard(actor, "read", "ext_wellness_session_report_list")
        self._program(program_id, actor)
        filters = {}
        if session_id is not None:
            filters["session_id"] = session_id
        return self._list("wellness_session_report", program_id, **filters)

    def wellness_delivery_summary(self, program_id, actor):
        """Derived at read: session/report counts over this
        surface's wellness records. Nothing is stored."""
        self._guard(actor, "read", "ext_wellness_delivery_summary")
        self._program(program_id, actor)
        sessions = self._list("wellness_session", program_id)
        reports = self._list("wellness_session_report", program_id)
        by_outcome = {o: 0 for o in WELLNESS_SESSION_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {
            "program_id": program_id,
            "sessions": len(sessions),
            "reports": len(reports),
            "reports_by_outcome": by_outcome,
            "delivered_here": False,
            "derived": True,
            "method": "counts_over_wellness_delivery_records",
        }

    # -- Lending & credit engines (0 claims) ---------------------------
    #
    # Named in the union spec as claimed by neither sibling. The
    # founding line stands: earned wage access is access to
    # *already-earned* wages only, and nothing on this surface
    # creates a credit product. What lands is the records layer in
    # front of a lender elsewhere: application records (amounts are
    # integer-cents data) plus decision reports whose label is
    # stored verbatim as the external lender reported it. No
    # underwriting is computed, no decision is made here
    # (``decided_here: False``), nothing is disbursed
    # (``disbursed_here: False``), and no record shape carries a
    # credit score field — pinned by test.

    def create_loan_application(
        self, program_id, participant_id, amount_cents, purpose_label, actor
    ):
        """Record a loan application as received for a participant.

        The application is a record only: it is not evaluated,
        approved, or funded here, and it draws against no accrual —
        the earned cap governs wage access, not this registry.
        """
        self._guard(actor, "enter", "ext_loan_application_create",
                    target=participant_id)
        self._program(program_id, actor)
        _cents_positive(amount_cents, "amount_cents")
        _non_empty(purpose_label, "purpose_label")
        self._participant(program_id, participant_id, actor)
        return self._create(
            "loan_application", "loan",
            {"program_id": program_id, "participant_id": participant_id,
             "amount_cents": amount_cents, "purpose_label": purpose_label,
             "disbursed_here": False, "underwriting_computed_here": False,
             "state": "recorded_application_only"},
            actor, "ext_loan_application_create")

    def record_loan_decision_report(
        self, program_id, application_id, decision_label, actor, detail=None
    ):
        """Record a lender's reported decision, verbatim.

        ``decision_label`` is the external lender's own words,
        stored as reported; this build decided nothing
        (``decided_here: False``) and the application record is
        left byte-identical.
        """
        self._guard(actor, "record", "ext_loan_decision_report",
                    target=application_id)
        self._program(program_id, actor)
        _non_empty(decision_label, "decision_label")
        _string_or_none(detail, "detail")
        self._get("loan_application", application_id, program_id)
        return self._create(
            "loan_decision_report", "ldec",
            {"program_id": program_id, "application_id": application_id,
             "decision_label": decision_label, "detail": detail,
             "disbursed_here": False, "decided_here": False},
            actor, "ext_loan_decision_report")

    def get_loan_application(self, program_id, application_id, actor):
        self._guard(actor, "read", "ext_loan_application_get",
                    target=application_id)
        self._program(program_id, actor)
        return self._fetch("loan_application", application_id, program_id)

    def list_loan_applications(self, program_id, actor, participant_id=None):
        self._guard(actor, "read", "ext_loan_application_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list("loan_application", program_id, **filters)

    def list_loan_decision_reports(
        self, program_id, actor, application_id=None
    ):
        self._guard(actor, "read", "ext_loan_decision_report_list")
        self._program(program_id, actor)
        filters = {}
        if application_id is not None:
            filters["application_id"] = application_id
        return self._list("loan_decision_report", program_id, **filters)

    # -- Trading & investment execution (0 claims) ---------------------
    #
    # Claimed by neither sibling. Order records against an opaque
    # instrument reference, plus execution reports stored verbatim.
    # Nothing is executed, priced, or settled here
    # (``executed_here: False`` on every record).

    def create_trade_order(
        self, program_id, participant_id, instrument_ref, side,
        amount_cents, actor
    ):
        """Record a trade order as received for a participant.

        ``instrument_ref`` is an opaque caller label held as data;
        the amount is integer-cents data about the order. The order
        is not routed, priced, or executed here.
        """
        self._guard(actor, "enter", "ext_trade_order_create",
                    target=participant_id)
        self._program(program_id, actor)
        _non_empty(instrument_ref, "instrument_ref")
        _one_of(side, KNOWN_TRADE_SIDES, TRADE_SIDES, "side")
        _cents_positive(amount_cents, "amount_cents")
        self._participant(program_id, participant_id, actor)
        return self._create(
            "trade_order", "tord",
            {"program_id": program_id, "participant_id": participant_id,
             "instrument_ref": instrument_ref, "side": side,
             "amount_cents": amount_cents, "executed_here": False,
             "state": "recorded_order_only"},
            actor, "ext_trade_order_create")

    def record_trade_execution_report(
        self, program_id, order_id, outcome, actor, detail=None
    ):
        """Record a broker's reported execution outcome, verbatim."""
        self._guard(actor, "record", "ext_trade_execution_report",
                    target=order_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_TRADE_REPORT_OUTCOMES,
                TRADE_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("trade_order", order_id, program_id)
        return self._create(
            "trade_execution_report", "trpt",
            {"program_id": program_id, "order_id": order_id,
             "outcome": outcome, "detail": detail,
             "executed_here": False},
            actor, "ext_trade_execution_report")

    def get_trade_order(self, program_id, order_id, actor):
        self._guard(actor, "read", "ext_trade_order_get", target=order_id)
        self._program(program_id, actor)
        return self._fetch("trade_order", order_id, program_id)

    def list_trade_orders(self, program_id, actor, participant_id=None):
        self._guard(actor, "read", "ext_trade_order_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list("trade_order", program_id, **filters)

    def list_trade_execution_reports(self, program_id, actor, order_id=None):
        self._guard(actor, "read", "ext_trade_execution_report_list")
        self._program(program_id, actor)
        filters = {}
        if order_id is not None:
            filters["order_id"] = order_id
        return self._list("trade_execution_report", program_id, **filters)

    # -- Tax reporting & remittance (0 claims) -------------------------
    #
    # Claimed by neither sibling. Preparation records (form label
    # held as data; amounts are integer-cents data) plus filing
    # reports stored verbatim. Nothing is filed and nothing is
    # remitted here (``filed_here`` / ``remitted_here`` False on
    # every record).

    def create_tax_preparation(
        self, program_id, participant_id, period, form_label,
        amount_cents, actor
    ):
        """Record a tax preparation as received for a participant."""
        self._guard(actor, "enter", "ext_tax_preparation_create",
                    target=participant_id)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _non_empty(form_label, "form_label")
        _cents_nonnegative(amount_cents, "amount_cents")
        self._participant(program_id, participant_id, actor)
        return self._create(
            "tax_preparation", "tax",
            {"program_id": program_id, "participant_id": participant_id,
             "period": period, "form_label": form_label,
             "amount_cents": amount_cents, "filed_here": False,
             "remitted_here": False, "state": "recorded_preparation_only"},
            actor, "ext_tax_preparation_create")

    def record_tax_filing_report(
        self, program_id, preparation_id, outcome, actor, detail=None
    ):
        """Record a filing system's reported outcome, verbatim."""
        self._guard(actor, "record", "ext_tax_filing_report",
                    target=preparation_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_TAX_REPORT_OUTCOMES,
                TAX_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("tax_preparation", preparation_id, program_id)
        return self._create(
            "tax_filing_report", "tfil",
            {"program_id": program_id, "preparation_id": preparation_id,
             "outcome": outcome, "detail": detail, "filed_here": False,
             "remitted_here": False},
            actor, "ext_tax_filing_report")

    def get_tax_preparation(self, program_id, preparation_id, actor):
        self._guard(actor, "read", "ext_tax_preparation_get",
                    target=preparation_id)
        self._program(program_id, actor)
        return self._fetch("tax_preparation", preparation_id, program_id)

    def list_tax_preparations(self, program_id, actor, participant_id=None):
        self._guard(actor, "read", "ext_tax_preparation_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list("tax_preparation", program_id, **filters)

    def list_tax_filing_reports(self, program_id, actor, preparation_id=None):
        self._guard(actor, "read", "ext_tax_filing_report_list")
        self._program(program_id, actor)
        filters = {}
        if preparation_id is not None:
            filters["preparation_id"] = preparation_id
        return self._list("tax_filing_report", program_id, **filters)

    # -- GRC platform functions (0 claims in text) ---------------------
    #
    # Present in the source data only as a category label on one
    # sibling's record; no descriptive sentence claims them.
    # Framework and control records are operator label sets, plus
    # mapping records binding core records to controls. Posture is
    # counts derived at read; registering a record asserts no
    # compliance (``compliance_asserted: False`` on every record)
    # and no control is evaluated.

    def register_framework(self, program_id, name, actor, version_label=None):
        """Register a framework record (a label set, not an
        assessment)."""
        self._guard(actor, "enter", "ext_framework_register")
        self._program(program_id, actor)
        _non_empty(name, "name")
        _string_or_none(version_label, "version_label")
        return self._create(
            "framework", "gfw",
            {"program_id": program_id, "name": name,
             "version_label": version_label, "compliance_asserted": False},
            actor, "ext_framework_register")

    def register_control(self, program_id, framework_id, control_ref,
                         title, actor):
        """Register a control record under a framework.

        ``control_ref`` is the caller's own opaque label for the
        control, held as data.
        """
        self._guard(actor, "enter", "ext_control_register",
                    target=framework_id)
        self._program(program_id, actor)
        _non_empty(control_ref, "control_ref")
        _non_empty(title, "title")
        self._get("framework", framework_id, program_id)
        return self._create(
            "control", "gctl",
            {"program_id": program_id, "framework_id": framework_id,
             "control_ref": control_ref, "title": title,
             "compliance_asserted": False},
            actor, "ext_control_register")

    def map_record_to_control(
        self, program_id, control_id, record_kind, record_id, actor
    ):
        """Record a mapping from an existing core record to a
        control. Both ends must exist; the mapping asserts nothing
        about the record's compliance."""
        self._guard(actor, "enter", "ext_control_mapping_create",
                    target=control_id)
        self._program(program_id, actor)
        _one_of(record_kind, KNOWN_MAPPABLE_RECORD_KINDS,
                MAPPABLE_RECORD_KINDS, "record_kind")
        self._get("control", control_id, program_id)
        if record_kind == "participant":
            self.store.get_participant(program_id, record_id, actor)
        elif record_kind == "booking":
            self.store.get_booking(program_id, record_id, actor)
        elif record_kind == "accrual":
            self.store.get_accrual(program_id, record_id, actor)
        elif record_kind == "access_request":
            self.store.get_access_request(program_id, record_id, actor)
        elif record_kind == "wellness_offering":
            self.store.get_wellness_offering(program_id, record_id, actor)
        return self._create(
            "control_mapping", "gmap",
            {"program_id": program_id, "control_id": control_id,
             "record_kind": record_kind, "record_id": record_id,
             "compliance_asserted": False},
            actor, "ext_control_mapping_create")

    def get_framework(self, program_id, framework_id, actor):
        self._guard(actor, "read", "ext_framework_get", target=framework_id)
        self._program(program_id, actor)
        return self._fetch("framework", framework_id, program_id)

    def list_frameworks(self, program_id, actor):
        self._guard(actor, "read", "ext_framework_list")
        self._program(program_id, actor)
        return self._list("framework", program_id)

    def list_controls(self, program_id, actor, framework_id=None):
        self._guard(actor, "read", "ext_control_list")
        self._program(program_id, actor)
        filters = {}
        if framework_id is not None:
            filters["framework_id"] = framework_id
        return self._list("control", program_id, **filters)

    def list_control_mappings(self, program_id, actor, control_id=None):
        self._guard(actor, "read", "ext_control_mapping_list")
        self._program(program_id, actor)
        filters = {}
        if control_id is not None:
            filters["control_id"] = control_id
        return self._list("control_mapping", program_id, **filters)

    def framework_posture(self, program_id, actor):
        """Derived at read: counts over frameworks, controls, and
        mappings. Counts only — no aggregate evaluation is computed
        and no framework is assessed."""
        self._guard(actor, "read", "ext_framework_posture")
        self._program(program_id, actor)
        frameworks = self._list("framework", program_id)
        controls = self._list("control", program_id)
        mappings = self._list("control_mapping", program_id)
        by_kind = {k: 0 for k in MAPPABLE_RECORD_KINDS}
        for mapping in mappings:
            by_kind[mapping["record_kind"]] += 1
        return {
            "program_id": program_id,
            "frameworks": len(frameworks),
            "controls": len(controls),
            "mappings": len(mappings),
            "mappings_by_record_kind": by_kind,
            "compliance_asserted": False,
            "derived": True,
            "method": "counts_over_framework_control_mapping_records",
        }

    # -- Streaming / real-time reporting pipelines (stub) --------------
    #
    # Labeled reference implementation. The core computes summaries
    # on read from records; a streaming pipeline is an engine over
    # external transport. What lands is the records layer in front
    # of one: stream registrations and delivery receipts whose
    # event counts are stored as reported. Every record carries
    # ``reference_stub: True``; receipts additionally carry
    # ``reference_transport: True``; ``streamed_here`` is False on
    # every record and nothing is streamed.

    def register_reporting_stream(self, program_id, stream_ref, actor):
        """Register a reporting-stream reference (stub)."""
        self._guard(actor, "enter", "ext_stream_register")
        self._program(program_id, actor)
        _non_empty(stream_ref, "stream_ref")
        return self._create(
            "reporting_stream", "strm",
            {"program_id": program_id, "stream_ref": stream_ref,
             "reference_stub": True, "streamed_here": False},
            actor, "ext_stream_register")

    def record_stream_receipt(
        self, program_id, stream_id, events_reported, actor, detail=None
    ):
        """Record a pipeline's reported delivery receipt (stub).

        ``events_reported`` is a count stored as reported by the
        external pipeline; no event moved through this build.
        """
        self._guard(actor, "record", "ext_stream_receipt", target=stream_id)
        self._program(program_id, actor)
        _count_nonnegative(events_reported, "events_reported")
        _string_or_none(detail, "detail")
        self._get("reporting_stream", stream_id, program_id)
        return self._create(
            "stream_receipt", "strc",
            {"program_id": program_id, "stream_id": stream_id,
             "events_reported": events_reported, "detail": detail,
             "reference_stub": True, "reference_transport": True,
             "streamed_here": False},
            actor, "ext_stream_receipt")

    def get_reporting_stream(self, program_id, stream_id, actor):
        self._guard(actor, "read", "ext_stream_get", target=stream_id)
        self._program(program_id, actor)
        return self._fetch("reporting_stream", stream_id, program_id)

    def list_reporting_streams(self, program_id, actor):
        self._guard(actor, "read", "ext_stream_list")
        self._program(program_id, actor)
        return self._list("reporting_stream", program_id)

    def list_stream_receipts(self, program_id, actor, stream_id=None):
        self._guard(actor, "read", "ext_stream_receipt_list")
        self._program(program_id, actor)
        filters = {}
        if stream_id is not None:
            filters["stream_id"] = stream_id
        return self._list("stream_receipt", program_id, **filters)

    def streaming_summary(self, program_id, actor):
        """Derived at read: stream/receipt counts and the total of
        reported event counts. Nothing is stored."""
        self._guard(actor, "read", "ext_streaming_summary")
        self._program(program_id, actor)
        streams = self._list("reporting_stream", program_id)
        receipts = self._list("stream_receipt", program_id)
        return {
            "program_id": program_id,
            "streams": len(streams),
            "receipts": len(receipts),
            "total_events_reported": sum(
                r["events_reported"] for r in receipts),
            "reference_stub": True,
            "streamed_here": False,
            "derived": True,
            "method": "counts_over_stream_receipt_records",
        }

    # -- Banking integration & account verification (stub; 0 claims) ---
    #
    # Labeled reference implementation. No sentence claims linking
    # or verifying real bank accounts, and the entity shapes forbid
    # real account identifiers by design — that design carries into
    # this surface: a verification request names a core participant
    # and a method label held as data, and a verification report
    # stores the external system's reported outcome label verbatim.
    # No record shape has a field that could hold an account
    # identifier; the exact key sets are pinned by test. Nothing is
    # verified here (``verified_here: False`` on every record).

    def record_verification_request(
        self, program_id, participant_id, method_label, actor
    ):
        """Record a request to verify a participant's account
        externally (stub)."""
        self._guard(actor, "enter", "ext_verification_request",
                    target=participant_id)
        self._program(program_id, actor)
        _non_empty(method_label, "method_label")
        self._participant(program_id, participant_id, actor)
        return self._create(
            "verification_request", "bver",
            {"program_id": program_id, "participant_id": participant_id,
             "method_label": method_label, "reference_stub": True,
             "verified_here": False},
            actor, "ext_verification_request")

    def record_verification_report(
        self, program_id, verification_id, outcome, actor, detail=None
    ):
        """Record a verification system's reported outcome (stub),
        stored verbatim as a label."""
        self._guard(actor, "record", "ext_verification_report",
                    target=verification_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_VERIFICATION_OUTCOMES,
                VERIFICATION_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("verification_request", verification_id, program_id)
        return self._create(
            "verification_report", "bvrp",
            {"program_id": program_id, "verification_id": verification_id,
             "outcome": outcome, "detail": detail,
             "reference_stub": True, "verified_here": False},
            actor, "ext_verification_report")

    def get_verification_request(self, program_id, verification_id, actor):
        self._guard(actor, "read", "ext_verification_get",
                    target=verification_id)
        self._program(program_id, actor)
        return self._fetch("verification_request", verification_id, program_id)

    def list_verification_requests(
        self, program_id, actor, participant_id=None
    ):
        self._guard(actor, "read", "ext_verification_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list("verification_request", program_id, **filters)

    def list_verification_reports(
        self, program_id, actor, verification_id=None
    ):
        self._guard(actor, "read", "ext_verification_report_list")
        self._program(program_id, actor)
        filters = {}
        if verification_id is not None:
            filters["verification_id"] = verification_id
        return self._list("verification_report", program_id, **filters)

    # -- Payroll system integration & wage calculation (stub; 0 claims)
    #
    # Labeled reference implementation. The core's accruals are
    # records of amounts computed elsewhere — the employer's payroll
    # is the source of earned wages, and no payroll function is
    # claimed. What lands is sync receipts: counts stored as
    # reported by the external payroll system. No wage amount is
    # computed here (``computed_here: False``) and no sync record
    # carries a cents field at all; the core accrual a sync reports
    # about is still recorded through the core, with its amount
    # supplied by the caller.

    def record_payroll_sync(
        self, program_id, source_ref, period, participants_reported,
        accruals_reported, actor
    ):
        """Record a payroll sync receipt (stub): counts as
        reported, amounts computed elsewhere."""
        self._guard(actor, "record", "ext_payroll_sync_record")
        self._program(program_id, actor)
        _non_empty(source_ref, "source_ref")
        _validate_period(period, "period")
        _count_nonnegative(participants_reported, "participants_reported")
        _count_nonnegative(accruals_reported, "accruals_reported")
        return self._create(
            "payroll_sync", "psyn",
            {"program_id": program_id, "source_ref": source_ref,
             "period": period,
             "participants_reported": participants_reported,
             "accruals_reported": accruals_reported,
             "reference_stub": True, "computed_here": False},
            actor, "ext_payroll_sync_record")

    def get_payroll_sync(self, program_id, sync_id, actor):
        self._guard(actor, "read", "ext_payroll_sync_get", target=sync_id)
        self._program(program_id, actor)
        return self._fetch("payroll_sync", sync_id, program_id)

    def list_payroll_syncs(self, program_id, actor, period=None):
        self._guard(actor, "read", "ext_payroll_sync_list")
        self._program(program_id, actor)
        filters = {}
        if period is not None:
            filters["period"] = period
        return self._list("payroll_sync", program_id, **filters)

    def payroll_sync_summary(self, program_id, actor):
        """Derived at read: sync counts and totals of the reported
        counts. No wage amount is computed or held here."""
        self._guard(actor, "read", "ext_payroll_sync_summary")
        self._program(program_id, actor)
        syncs = self._list("payroll_sync", program_id)
        return {
            "program_id": program_id,
            "syncs": len(syncs),
            "total_participants_reported": sum(
                s["participants_reported"] for s in syncs),
            "total_accruals_reported": sum(
                s["accruals_reported"] for s in syncs),
            "reference_stub": True,
            "computed_here": False,
            "derived": True,
            "method": "counts_over_payroll_sync_records",
        }
