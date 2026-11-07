"""Final GAPS batch extensions for Fleet Management L1 (Group 32).

Clean-room, standard-library-only extensions for the 8 open
entries of the "Group 32 — Fleet Management L1 (2 forks)"
section of GAPS.md (see ``BATCH.md`` in the group directory for
the per-entry disposition). This module is a wrapper around
:class:`FleetStore`; every core module is untouched and
byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** this build holds records about fleet operations. It
streams no telemetry, senses no position, dispatches no
vehicle, optimizes no route, connects to no logging device,
forecasts nothing, talks to no charging station, moves no
money, and runs no analytics engine. Every entity shape in
this module carries metadata and opaque caller-supplied
references only, plus figures and outcomes stored exactly as
reported by the external systems and people who actually did
the work. Methods accept only their named parameters, so a
caller cannot smuggle an unlisted field into a record (pinned
by tests: an unexpected keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records over the group's OWN records (core
records and extension records), plus deterministic derivations
at read:

- Live telematics & GPS streaming ships as a labeled reference
  implementation: stream-subscription records held as data plus
  caller-REPORTED position/status records, each holding the
  reported position label verbatim (``tracked_here`` /
  ``sensed_here`` are False). Each record is standalone — no
  track/trail/history structure exists.
- Dispatch routing & optimization is dispatch-assignment
  records over core reservations: the assignment is the record
  form of a dispatch decision made elsewhere
  (``dispatched_here`` False in the control sense — no vehicle
  is directed or controlled); route-plan records are held as
  data with ``optimized_here`` False and nothing anywhere
  compares, ranks, or scores candidate routes.
- ELD / hours-of-service integrations ship as a labeled
  reference implementation: device-binding records plus
  hours-of-service records holding reported figures and
  reported compliance labels verbatim. No limit is evaluated
  and no status is computed here (``evaluated_here`` False).
- Demand & capacity forecasting is forecast-input records
  (reported figures, stored verbatim) plus a read-time
  DERIVATION of recorded demand against recorded capacity —
  counts and sums of recorded values only, rendered as
  integers or exact ``"num/den"`` fractions, never rounded.
  Nothing is projected: no future value is estimated and no
  model is fit (``projected_here`` / ``modeled_here`` False).
  The derivation seam is :func:`_recorded_demand_totals`
  plus the view's exact-fraction rendering — the batch's fresh
  negative control target.
- EV charging station communication & session control rides
  in-record as labeled reference components on extension
  session-control request records bound to core charging
  sessions: ``reference_stub: True``,
  ``communicated_here`` / ``controlled_here`` False. The core
  session record is never touched by this surface (pinned).
- Payment processing is payment records bound to core charging
  sessions: integer cents, reported authorization/outcome
  labels verbatim, ``moved_here`` / ``settled_here`` False.
  Payment references are opaque; no field can hold a card or
  account number.
- Analytics & utilization-optimization engines beyond registry
  reporting is report-run records that store NO figures, plus
  read-time deterministic derivations over the substrate's own
  records (counts, sums of recorded watt-hours, latest recorded
  odometer, completed-share and closed-share rendered as exact
  fractions or ``None``). No score, rating, ranking, or index
  key exists anywhere on this surface (pinned by recursive
  scan); utilization optimization itself is a labeled
  reference component (``optimized_here`` False).
- Hosted platform operations ships as a labeled reference
  implementation: operations records holding reported status
  labels verbatim (``operated_here`` / ``hosted_here`` False).
  PLATFORM-LAYER.md decision 6 stands beside it and is not
  re-argued here: hosting is a deployment property, and these
  records close only the records surface of the entry.

Doctrines carried from the core: derived-never-stored for
every computed value (demand totals, utilization shares,
plan assignment counts); money is integer cents and energy
integer watt-hours, with booleans and floats rejected at the
boundary; append-only audit on the core store's log with
``ext_``-prefixed actions for every successful mutation, and
denied write attempts recorded with a ``:denied`` suffix;
RBAC via :mod:`fleet.access` with the core's existing actions
(``read`` / ``write``), enforced before any state change or id
allocation, so a failed operation consumes no id and changes
nothing. Baseline stays Low / L1 as written for the core:
audit traces to AU-2/AU-3 on the FedRAMP Low side only, and no
Moderate/High apparatus is imported.
"""

import copy
import threading
from datetime import datetime, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

TELEMATICS_STREAM_KINDS = (
    "gps_stream",
    "telematics_feed",
    "status_feed",
)
TELEMATICS_REPORT_KINDS = (
    "position_report",
    "status_report",
)
ROUTE_PLAN_KINDS = (
    "reported_route",
    "planned_route",
)
DISPATCH_OUTCOME_LABELS = (
    "reported_completed",
    "reported_cancelled",
    "reported_failed",
)
ELD_DEVICE_KINDS = (
    "eld",
    "aobrd",
    "telematics_unit",
)
HOS_COMPLIANCE_LABELS = (
    "reported_compliant",
    "reported_violation",
    "reported_exempt",
)
FORECAST_INPUT_KINDS = (
    "demand",
    "capacity",
)
SESSION_CONTROL_KINDS = (
    "start_session",
    "stop_session",
    "set_limit",
)
SESSION_CONTROL_OUTCOME_LABELS = (
    "reported_accepted",
    "reported_rejected",
    "reported_completed",
    "reported_failed",
)
PAYMENT_KINDS = (
    "authorization",
    "capture",
    "refund",
)
PAYMENT_OUTCOME_LABELS = (
    "reported_authorized",
    "reported_captured",
    "reported_declined",
    "reported_refunded",
    "reported_failed",
)
PLATFORM_OPERATION_KINDS = (
    "deployment",
    "maintenance_window",
    "incident",
    "status_report",
)
PLATFORM_STATUS_LABELS = (
    "reported_operational",
    "reported_degraded",
    "reported_outage",
    "reported_maintenance",
    "reported_resolved",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _optional_text(value, what):
    if value is None:
        return None
    return _non_empty(value, what)


def _non_negative_int(value, what):
    """Integer >= 0 (not bool); floats rejected at the boundary."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _money(value, what):
    """The house money rule: integer cents (not bool) >= 0."""
    return _non_negative_int(value, what)


def _fraction_out(amount):
    """Render an exact Fraction for a view: an int when whole,
    else the exact ``"num/den"`` string. Nothing is rounded."""
    if amount.denominator == 1:
        return amount.numerator
    return "%d/%d" % (amount.numerator, amount.denominator)


def _recorded_demand_totals(inputs):
    """Demand/capacity derivation seam: the single point where
    recorded forecast inputs are totalled.

    Given the forecast-input records of one subject (in
    recording order), return ``(total_demand, total_capacity)``
    as exact integers: the sum of the recorded ``reported_units``
    of the demand-kind inputs and of the capacity-kind inputs
    respectively. The figures are sums of values recorded
    verbatim from reporters — nothing is projected, estimated,
    or fitted here.

    MUTATION DRILL NOTE: this seam is the batch unit's fresh
    negative control target — summing the capacity records into
    the demand total (or vice versa) would silently corrupt
    every demand view while leaving the record shapes intact
    (see tests/README.md).
    """
    total_demand = sum(r["reported_units"] for r in inputs
                       if r["kind"] == "demand")
    total_capacity = sum(r["reported_units"] for r in inputs
                         if r["kind"] == "capacity")
    return total_demand, total_capacity


class FleetExtensions:
    """Extension surface wrapping one :class:`FleetStore`."""

    def __init__(self, store):
        self.store = store
        self._telematics_streams = {}
        self._telematics_reports = {}
        self._route_plans = {}
        self._dispatch_assignments = {}
        self._dispatch_outcomes = {}
        self._eld_bindings = {}
        self._hos_records = {}
        self._forecast_inputs = {}
        self._session_controls = {}
        self._session_outcomes = {}
        self._payments = {}
        self._report_runs = {}
        self._optimization_requests = {}
        self._platform_operations = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`fleet.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on
        the audit log with a ``:denied`` suffix before the error
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

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- telematics & GPS streaming (entry: Live telematics & GPS
    #    streaming — labeled reference implementation) ----------------

    def create_telematics_stream(self, actor, vehicle_id, kind,
                                 source_ref):
        """Record a telematics stream subscription. Action: write.

        Reference implementation only: the record states that an
        external stream exists; no stream is opened and nothing
        is received through this surface. ``source_ref`` is an
        opaque reference to the external stream.
        """
        self._guard(actor, "write", "ext_telematics_stream_create")
        if kind not in TELEMATICS_STREAM_KINDS:
            raise ValidationError(
                "unknown telematics stream kind: %r" % (kind,))
        _non_empty(source_ref, "source_ref")
        self.store.get_vehicle(vehicle_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("tlm-"),
                "vehicle_id": vehicle_id,
                "kind": kind,
                "source_ref": source_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "streamed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telematics_streams[record["id"]] = record
        self._audit(actor, "ext_telematics_stream_create", record["id"],
                    {"vehicle_id": vehicle_id})
        return copy.deepcopy(record)

    def record_telematics_report(self, actor, stream_id, kind,
                                 position_label, status_label=None):
        """Record a telematics report exactly as reported. Action:
        write.

        The position and status labels are caller-reported data,
        stored verbatim; nothing here senses, locates, or tracks
        a vehicle (``tracked_here`` / ``sensed_here`` are False).
        Each report is a standalone record — there is no track,
        trail, or history structure.
        """
        self._guard(actor, "write", "ext_telematics_report_create")
        if kind not in TELEMATICS_REPORT_KINDS:
            raise ValidationError(
                "unknown telematics report kind: %r" % (kind,))
        _non_empty(position_label, "position_label")
        _optional_text(status_label, "status_label")
        with self._lock:
            self._get(self._telematics_streams, stream_id,
                      "telematics stream")
            record = {
                "id": self._next_id("tlr-"),
                "stream_id": stream_id,
                "kind": kind,
                "position_label": position_label,
                "status_label": status_label,
                "tracked_here": False,
                "sensed_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telematics_reports[record["id"]] = record
        self._audit(actor, "ext_telematics_report_create", record["id"],
                    {"stream_id": stream_id})
        return copy.deepcopy(record)

    def telematics_stream_view(self, actor, stream_id):
        """A stream record plus its report count, derived at read.
        Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            stream = self._get(self._telematics_streams, stream_id,
                               "telematics stream")
            view = copy.deepcopy(stream)
            reports = [r for r in self._telematics_reports.values()
                       if r["stream_id"] == stream_id]
            view["report_count"] = len(reports)
            return view

    # -- dispatch routing & optimization (entry: Dispatch routing
    #    & optimization) ---------------------------------------------

    def create_route_plan(self, actor, label, kind, step_labels=()):
        """Record a route plan as data. Action: write.

        ``step_labels`` is an ordered list of stop/leg labels
        stored verbatim, exactly as supplied by whoever planned
        the route. Nothing here computes, compares, ranks, or
        optimizes a route (``optimized_here`` is False).
        """
        self._guard(actor, "write", "ext_route_plan_create")
        _non_empty(label, "route plan label")
        if kind not in ROUTE_PLAN_KINDS:
            raise ValidationError("unknown route plan kind: %r" % (kind,))
        if isinstance(step_labels, str) or not isinstance(
                step_labels, (list, tuple)):
            raise ValidationError("step_labels must be a list of labels")
        steps = []
        for step in step_labels:
            steps.append(_non_empty(step, "route plan step label"))
        with self._lock:
            record = {
                "id": self._next_id("rtp-"),
                "label": label,
                "kind": kind,
                "step_labels": steps,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._route_plans[record["id"]] = record
        self._audit(actor, "ext_route_plan_create", record["id"],
                    {"label": label})
        return copy.deepcopy(record)

    def create_dispatch_assignment(self, actor, reservation_id,
                                   operator_ref, route_plan_id=None):
        """Record a dispatch assignment over a core reservation.
        Action: write.

        The assignment is the record form of a dispatch decision
        made elsewhere: it binds a reservation to an operator
        reference (and optionally a route-plan record) and
        directs nothing — no vehicle is dispatched, routed, or
        controlled from here (``dispatched_here`` /
        ``controlled_here`` are False).
        """
        self._guard(actor, "write", "ext_dispatch_create")
        _non_empty(operator_ref, "operator_ref")
        self.store.get_reservation(reservation_id, actor)
        with self._lock:
            if route_plan_id is not None:
                self._get(self._route_plans, route_plan_id, "route plan")
            record = {
                "id": self._next_id("dsp-"),
                "reservation_id": reservation_id,
                "operator_ref": operator_ref,
                "route_plan_id": route_plan_id,
                "dispatched_here": False,
                "controlled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dispatch_assignments[record["id"]] = record
        self._audit(actor, "ext_dispatch_create", record["id"],
                    {"reservation_id": reservation_id})
        return copy.deepcopy(record)

    def record_dispatch_outcome(self, actor, assignment_id, outcome_label):
        """Record a dispatch outcome exactly as reported. Action:
        write. The label is stored verbatim; nothing here
        determines an outcome."""
        self._guard(actor, "write", "ext_dispatch_outcome_create")
        if outcome_label not in DISPATCH_OUTCOME_LABELS:
            raise ValidationError(
                "unknown dispatch outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._dispatch_assignments, assignment_id,
                      "dispatch assignment")
            record = {
                "id": self._next_id("dso-"),
                "assignment_id": assignment_id,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dispatch_outcomes[record["id"]] = record
        self._audit(actor, "ext_dispatch_outcome_create", record["id"],
                    {"assignment_id": assignment_id})
        return copy.deepcopy(record)

    def route_plan_view(self, actor, route_plan_id):
        """A route-plan record plus its assignment count, derived
        at read. Action: read. The stored plan carries no count."""
        self._maybe_require(actor, "read")
        with self._lock:
            plan = self._get(self._route_plans, route_plan_id,
                             "route plan")
            view = copy.deepcopy(plan)
            view["assignment_count"] = len(
                [a for a in self._dispatch_assignments.values()
                 if a["route_plan_id"] == route_plan_id])
            return view

    # -- ELD / hours of service (entry: ELD / hours-of-service
    #    integrations — labeled reference implementation) ------------

    def create_eld_binding(self, actor, operator_id, device_kind,
                           device_ref):
        """Record a binding between a core operator record and
        an external logging device. Action: write.

        Reference implementation only: ``device_ref`` is an
        opaque reference; nothing here connects to, reads from,
        or writes to a device (``connected_here`` is False).
        """
        self._guard(actor, "write", "ext_eld_binding_create")
        if device_kind not in ELD_DEVICE_KINDS:
            raise ValidationError(
                "unknown ELD device kind: %r" % (device_kind,))
        _non_empty(device_ref, "device_ref")
        self.store.get_operator(operator_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("eld-"),
                "operator_id": operator_id,
                "device_kind": device_kind,
                "device_ref": device_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._eld_bindings[record["id"]] = record
        self._audit(actor, "ext_eld_binding_create", record["id"],
                    {"operator_id": operator_id})
        return copy.deepcopy(record)

    def record_hours_of_service(self, actor, binding_id,
                                reported_driving_minutes,
                                reported_on_duty_minutes,
                                compliance_label):
        """Record hours-of-service figures exactly as reported.
        Action: write.

        The minute figures and the compliance label are stored
        verbatim, as reported by the device or operator they
        came from. No hours-of-service limit is evaluated and
        no compliance status is computed here
        (``evaluated_here`` is False); the label is a report,
        not a determination.
        """
        self._guard(actor, "write", "ext_hos_record_create")
        _non_negative_int(reported_driving_minutes,
                          "reported_driving_minutes")
        _non_negative_int(reported_on_duty_minutes,
                          "reported_on_duty_minutes")
        if compliance_label not in HOS_COMPLIANCE_LABELS:
            raise ValidationError(
                "unknown HOS compliance label: %r" % (compliance_label,))
        with self._lock:
            self._get(self._eld_bindings, binding_id, "ELD binding")
            record = {
                "id": self._next_id("hos-"),
                "binding_id": binding_id,
                "reported_driving_minutes": reported_driving_minutes,
                "reported_on_duty_minutes": reported_on_duty_minutes,
                "compliance_label": compliance_label,
                "evaluated_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._hos_records[record["id"]] = record
        self._audit(actor, "ext_hos_record_create", record["id"],
                    {"binding_id": binding_id})
        return copy.deepcopy(record)

    # -- demand & capacity forecasting (entry: Demand & capacity
    #    forecasting engine) ------------------------------------------

    def record_forecast_input(self, actor, subject_label, kind,
                              period_label, reported_units):
        """Record one forecast input exactly as reported. Action:
        write.

        A demand or capacity figure for a named subject and
        period, stored verbatim (integer units). Inputs are
        data; the forecast view derives recorded totals from
        them and projects nothing.
        """
        self._guard(actor, "write", "ext_forecast_input_create")
        _non_empty(subject_label, "subject_label")
        if kind not in FORECAST_INPUT_KINDS:
            raise ValidationError(
                "unknown forecast input kind: %r" % (kind,))
        _non_empty(period_label, "period_label")
        _non_negative_int(reported_units, "reported_units")
        with self._lock:
            record = {
                "id": self._next_id("fci-"),
                "subject_label": subject_label,
                "kind": kind,
                "period_label": period_label,
                "reported_units": reported_units,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._forecast_inputs[record["id"]] = record
        self._audit(actor, "ext_forecast_input_create", record["id"],
                    {"subject_label": subject_label, "kind": kind})
        return copy.deepcopy(record)

    def forecast_view(self, actor, subject_label):
        """Derived view of the recorded forecast inputs for one
        subject. Action: read.

        ``recorded_demand`` and ``recorded_capacity`` are the
        exact sums of the recorded inputs (via the seam
        :func:`_recorded_demand_totals`); ``recorded_balance``
        is their exact difference; ``demand_to_capacity`` is
        their exact ratio rendered as an int when whole, else
        as an exact ``"num/den"`` string — or ``None`` when no
        capacity has been recorded. These are derivations over
        recorded figures only: no future value is estimated, no
        trend is fitted, and nothing is projected
        (``projected_here`` / ``modeled_here`` are False).
        """
        self._maybe_require(actor, "read")
        with self._lock:
            inputs = [r for r in self._forecast_inputs.values()
                      if r["subject_label"] == subject_label]
            total_demand, total_capacity = _recorded_demand_totals(inputs)
            if total_capacity:
                ratio = _fraction_out(Fraction(total_demand,
                                               total_capacity))
            else:
                ratio = None
            return {
                "subject_label": subject_label,
                "input_count": len(inputs),
                "recorded_demand": total_demand,
                "recorded_capacity": total_capacity,
                "recorded_balance": total_demand - total_capacity,
                "demand_to_capacity": ratio,
                "projected_here": False,
                "modeled_here": False,
            }

    # -- EV charging session control (entry: EV charging station
    #    communication & session control) ------------------------------

    def record_session_control(self, actor, session_id, kind,
                               requested_limit_watt_hours=None):
        """Record a charging-session control request bound to a
        core charging session. Action: write.

        The request rides in-record as a labeled reference
        component: nothing is transmitted to a station and no
        session is started, stopped, or limited from here
        (``reference_stub`` True; ``communicated_here`` /
        ``controlled_here`` False). The core session record is
        not read for update and never modified by this surface.
        """
        self._guard(actor, "write", "ext_session_control_create")
        if kind not in SESSION_CONTROL_KINDS:
            raise ValidationError(
                "unknown session control kind: %r" % (kind,))
        if requested_limit_watt_hours is not None:
            _non_negative_int(requested_limit_watt_hours,
                              "requested_limit_watt_hours")
        self.store.get_charging_session(session_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("sctl-"),
                "session_id": session_id,
                "kind": kind,
                "requested_limit_watt_hours": requested_limit_watt_hours,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "communicated_here": False,
                "controlled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._session_controls[record["id"]] = record
        self._audit(actor, "ext_session_control_create", record["id"],
                    {"session_id": session_id})
        return copy.deepcopy(record)

    def record_session_control_outcome(self, actor, control_id,
                                       outcome_label):
        """Record a session-control outcome exactly as reported.
        Action: write. The label is stored verbatim; the outcome
        was produced by the station or platform that actually
        acted, not here."""
        self._guard(actor, "write", "ext_session_outcome_create")
        if outcome_label not in SESSION_CONTROL_OUTCOME_LABELS:
            raise ValidationError(
                "unknown session control outcome label: %r"
                % (outcome_label,))
        with self._lock:
            self._get(self._session_controls, control_id,
                      "session control request")
            record = {
                "id": self._next_id("sout-"),
                "control_id": control_id,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._session_outcomes[record["id"]] = record
        self._audit(actor, "ext_session_outcome_create", record["id"],
                    {"control_id": control_id})
        return copy.deepcopy(record)

    def session_control_view(self, actor, control_id):
        """A control request plus its outcome count, derived at
        read. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            control = self._get(self._session_controls, control_id,
                                "session control request")
            view = copy.deepcopy(control)
            view["outcome_count"] = len(
                [o for o in self._session_outcomes.values()
                 if o["control_id"] == control_id])
            return view

    # -- payment processing (entry: Payment processing) ---------------

    def record_payment(self, actor, session_id, kind, amount_cents,
                       payment_ref, outcome_label):
        """Record a payment against a core charging session.
        Action: write.

        Money is integer cents. ``payment_ref`` is an opaque
        reference to a payment held elsewhere — no field in
        this record can hold a card number, an account number,
        or any other payment credential. The outcome label is
        stored verbatim as reported by the processor that
        actually acted; no money moves and nothing settles
        here (``moved_here`` / ``settled_here`` are False).
        """
        self._guard(actor, "write", "ext_payment_create")
        if kind not in PAYMENT_KINDS:
            raise ValidationError("unknown payment kind: %r" % (kind,))
        _money(amount_cents, "amount_cents")
        _non_empty(payment_ref, "payment_ref")
        if outcome_label not in PAYMENT_OUTCOME_LABELS:
            raise ValidationError(
                "unknown payment outcome label: %r" % (outcome_label,))
        self.store.get_charging_session(session_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("pay-"),
                "session_id": session_id,
                "kind": kind,
                "amount_cents": amount_cents,
                "payment_ref": payment_ref,
                "outcome_label": outcome_label,
                "moved_here": False,
                "settled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payments[record["id"]] = record
        self._audit(actor, "ext_payment_create", record["id"],
                    {"session_id": session_id})
        return copy.deepcopy(record)

    def session_payments_view(self, actor, session_id):
        """Derived view of the payments recorded against one core
        charging session. Action: read.

        Totals are sums of recorded amounts, grouped by the
        recorded outcome label and in total; they derive at read
        and are stored nowhere.
        """
        self._maybe_require(actor, "read")
        self.store.get_charging_session(session_id, actor)
        with self._lock:
            payments = [p for p in self._payments.values()
                        if p["session_id"] == session_id]
            by_outcome = {}
            for payment in payments:
                label = payment["outcome_label"]
                by_outcome[label] = (by_outcome.get(label, 0)
                                     + payment["amount_cents"])
            return {
                "session_id": session_id,
                "payment_count": len(payments),
                "total_cents": sum(p["amount_cents"] for p in payments),
                "cents_by_outcome": by_outcome,
                "moved_here": False,
                "settled_here": False,
            }

    # -- analytics beyond registry reporting (entry: Analytics &
    #    utilization-optimization engines beyond registry
    #    reporting) -----------------------------------------------------

    def record_report_run(self, actor, label):
        """Record an analytics report run. Action: write.

        The run record stores NO figures — pinned to exactly
        ``{id, label, created_by, created_utc}``. Every figure
        in the analytics view is derived at read from the
        substrate's own records, so a run recorded earlier
        reports the registry as it stands when read.
        """
        self._guard(actor, "write", "ext_report_run_create")
        _non_empty(label, "report run label")
        with self._lock:
            record = {
                "id": self._next_id("rpt-"),
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_runs[record["id"]] = record
        self._audit(actor, "ext_report_run_create", record["id"],
                    {"label": label})
        return copy.deepcopy(record)

    def analytics_view(self, actor, run_id):
        """Derived analytics view for one report run. Action:
        read.

        Deterministic derivations over the substrate's own
        records only: counts per record set (core and
        extension), aggregate recorded charging energy in
        integer watt-hours, the fleet's latest recorded
        odometer (the maximum recorded reading, or ``None``),
        and the completed share of maintenance records and
        closed share of charging sessions, each rendered as an
        exact int/``"num/den"`` fraction or ``None`` when the
        denominator set is empty. No score, rating, ranking,
        or index is computed anywhere on this surface, and no
        utilization is optimized (``optimized_here`` False).
        """
        self._maybe_require(actor, "read")
        with self._lock:
            run = self._get(self._report_runs, run_id, "report run")
            summary = self.store.summary_report(actor)
            counts = dict(summary["counts"])
            counts["telematics_streams"] = len(self._telematics_streams)
            counts["telematics_reports"] = len(self._telematics_reports)
            counts["route_plans"] = len(self._route_plans)
            counts["dispatch_assignments"] = len(
                self._dispatch_assignments)
            counts["eld_bindings"] = len(self._eld_bindings)
            counts["hos_records"] = len(self._hos_records)
            counts["forecast_inputs"] = len(self._forecast_inputs)
            counts["session_controls"] = len(self._session_controls)
            counts["payments"] = len(self._payments)
            counts["report_runs"] = len(self._report_runs)
            counts["optimization_requests"] = len(
                self._optimization_requests)
            counts["platform_operations"] = len(
                self._platform_operations)
            maintenance = self.store.list_maintenance(actor=actor)
            if maintenance:
                completed = len([m for m in maintenance
                                 if m["derived_status"] == "completed"])
                completed_share = _fraction_out(
                    Fraction(completed, len(maintenance)))
            else:
                completed_share = None
            sessions = self.store.list_charging_sessions(actor=actor)
            if sessions:
                closed = len([s for s in sessions
                              if s["ended_utc"] is not None])
                closed_share = _fraction_out(
                    Fraction(closed, len(sessions)))
            else:
                closed_share = None
            usage = self.store.list_usage(actor=actor)
            readings = [u["odometer_reading"] for u in usage]
            view = copy.deepcopy(run)
            view["counts"] = counts
            view["total_watt_hours"] = summary["total_watt_hours"]
            view["latest_odometer"] = max(readings) if readings else None
            view["maintenance_completed_share"] = completed_share
            view["charging_closed_share"] = closed_share
            view["optimized_here"] = False
            return view

    def record_optimization_request(self, actor, subject_label):
        """Record a utilization-optimization request. Action:
        write.

        Labeled reference component inside the analytics entry:
        the request is held as data for an optimizer that lives
        elsewhere; nothing here optimizes anything
        (``reference_stub`` True, ``optimized_here`` False).
        """
        self._guard(actor, "write", "ext_optimization_request_create")
        _non_empty(subject_label, "subject_label")
        with self._lock:
            record = {
                "id": self._next_id("opt-"),
                "subject_label": subject_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._optimization_requests[record["id"]] = record
        self._audit(actor, "ext_optimization_request_create",
                    record["id"], {"subject_label": subject_label})
        return copy.deepcopy(record)

    # -- hosted platform operations (entry: Hosted platform
    #    operations — labeled reference implementation) -----------------

    def record_platform_operation(self, actor, kind, status_label,
                                  detail_ref=None):
        """Record a hosted-platform operation exactly as reported.
        Action: write.

        Reference implementation only: the record states what
        the hosting platform's operator reported; this build
        operates and hosts nothing (``operated_here`` /
        ``hosted_here`` are False). ``detail_ref`` is an opaque
        reference to the operator's own record.
        """
        self._guard(actor, "write", "ext_platform_operation_create")
        if kind not in PLATFORM_OPERATION_KINDS:
            raise ValidationError(
                "unknown platform operation kind: %r" % (kind,))
        if status_label not in PLATFORM_STATUS_LABELS:
            raise ValidationError(
                "unknown platform status label: %r" % (status_label,))
        _optional_text(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._next_id("plt-"),
                "kind": kind,
                "status_label": status_label,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "operated_here": False,
                "hosted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._platform_operations[record["id"]] = record
        self._audit(actor, "ext_platform_operation_create", record["id"],
                    {"kind": kind})
        return copy.deepcopy(record)

    def platform_operations_view(self, actor):
        """Derived view over the platform-operation records.
        Action: read. Counts by recorded kind and by reported
        status label, derived at read — counts only."""
        self._maybe_require(actor, "read")
        with self._lock:
            by_kind = {}
            by_status = {}
            for record in self._platform_operations.values():
                by_kind[record["kind"]] = by_kind.get(record["kind"], 0) + 1
                by_status[record["status_label"]] = (
                    by_status.get(record["status_label"], 0) + 1)
            return {
                "operation_count": len(self._platform_operations),
                "counts_by_kind": by_kind,
                "counts_by_status": by_status,
                "operated_here": False,
                "hosted_here": False,
            }
