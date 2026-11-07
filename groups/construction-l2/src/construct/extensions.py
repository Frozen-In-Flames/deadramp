"""Final GAPS batch extensions for Construction L2 (Group 19).

Clean-room, standard-library-only extensions for the 9 open
entries of the "Group 19 — Construction L2 (4 forks)" section of
GAPS.md (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`ConstructStore`; every core module is untouched and
byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** this build holds records about construction work. It
runs no estimating engine over proprietary data, senses no
position, monitors no vehicle, executes no workflow or
signature, and runs no model. Every entity shape in this module
carries metadata and opaque caller-supplied references only,
plus figures and outcomes stored exactly as reported by the
external systems and people who actually did the work. Methods
accept only their named parameters, so a caller cannot smuggle
an unlisted field into a record (pinned by tests: an unexpected
keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records over the group's OWN records (core
records and extension records), plus deterministic derivations
at read:

- Cost estimating is estimate records over core projects:
  line items hold a recorded quantity and a recorded unit
  price; line totals and the estimate total are derived
  deterministically at read (integer cents, exact). The
  proprietary cost DATA behind vendor engines is held as a
  source reference only (``data_held_here`` is False); no cost
  database is fabricated.
- GPS / field collection is field-report records: a reported
  position label and an observation label stored verbatim as
  reported. Positions are caller-reported data, never sensed
  (``tracked_here`` / ``collected_here`` are False), and no
  continuous tracking state exists — each report is a
  standalone record.
- Prevailing wage is built genuinely where arithmetic
  suffices: rate tables are held as data; wage lines hold
  recorded inputs only (rate-table reference, worker
  reference, integer minutes); base, fringe, and gross amounts
  are computed deterministically at read by the single seam
  :func:`_compute_wage_amounts` using exact rational
  arithmetic (:class:`fractions.Fraction`), never stored.
  Certified-payroll report records reference wage lines; the
  report's totals exist only in its read view, derived from
  the same seam. E-filing ships as a labeled reference record
  (``filed_here`` is False).
- Dispatch routing is route records held as data (an ordered
  list of stop labels in the caller's recorded order) plus
  verbatim reported outcomes. ``optimized_here`` is False: a
  route is a recorded plan, not a computed one, and recording
  one leaves the core dispatch record byte-identical.
- Stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub:
  True`` and state ``recorded_reference_only``. Telematics
  holds reported vehicle/driver records verbatim — a driver
  score is a REPORTED label only; no score is computed and no
  numeric score field exists. Contract lifecycle holds
  template/clause/playbook records as metadata plus reported
  negotiation outcomes (``redlined_here`` is False).
  E-signature holds request/outcome records in the house form
  (``signed_here`` is False; no signature-value field exists).
  AI/ML holds opaque result references (``inference_here`` is
  False; no extracted-text field exists). Workflow definitions
  are held as data and the registry never executes them
  (``executed_here`` is False, pinned).

Doctrines carried from the core: derived-never-stored for every
computed value (estimate totals, wage amounts, certified-
payroll totals); money is integer cents, with booleans and
floats rejected at the boundary; append-only audit on the core
store's log with ``ext_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a
``:denied`` suffix; RBAC via :mod:`construct.access` with the
core's existing actions, enforced before any state change or
id allocation, so a failed operation consumes no id and
changes nothing.
"""

import copy
import threading
from datetime import datetime, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

TELEMATICS_REPORT_LABELS = (
    "reported_ok",
    "reported_idling",
    "reported_speeding",
    "reported_harsh_braking",
)
NEGOTIATION_OUTCOME_LABELS = (
    "reported_agreed",
    "reported_countered",
    "reported_stalled",
)
SIGNATURE_OUTCOME_LABELS = (
    "reported_signed",
    "reported_declined",
    "reported_expired",
)
WORKFLOW_OUTCOME_LABELS = (
    "reported_completed",
    "reported_failed",
    "reported_cancelled",
)
ROUTE_OUTCOME_LABELS = (
    "reported_completed",
    "reported_delayed",
    "reported_cancelled",
)
EFILING_STATE_LABEL = "recorded_reference_only"

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


def _money(value, what):
    """The house money rule: integer cents (not bool) >= 0."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if value < 0:
        raise ValidationError("%s must be >= 0" % (what,))
    return value


def _positive_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _rate_cents(value, what, allow_zero):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if allow_zero:
        if value < 0:
            raise ValidationError("%s must be >= 0" % (what,))
    elif value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _compute_wage_amounts(base_rate_cents_per_hour, fringe_rate_cents_per_hour,
                          minutes):
    """Prevailing-wage derivation seam: the single point where
    wage amounts are computed.

    Given a recorded base rate and fringe rate (integer cents
    per hour) and recorded integer minutes, return
    ``(base_cents, fringe_cents, gross_cents)`` as exact
    :class:`~fractions.Fraction` values: ``rate * minutes /
    60``, with the gross the exact sum. Nothing is rounded and
    nothing is stored — views render an exact Fraction as an
    ``int`` when it is whole, else as a ``"num/den"`` string.
    This seam is the negative control's target: dropping the
    fringe term must fail the wage tests.
    """
    base = Fraction(base_rate_cents_per_hour * minutes, 60)
    fringe = Fraction(fringe_rate_cents_per_hour * minutes, 60)
    return base, fringe, base + fringe


def _cents_out(amount):
    """Render an exact Fraction of cents for a view: an int when
    whole, else the exact ``"numerator/denominator"`` string."""
    if amount.denominator == 1:
        return amount.numerator
    return "%d/%d" % (amount.numerator, amount.denominator)


class ConstructExtensions:
    """Extension surface wrapping one :class:`ConstructStore`."""

    def __init__(self, store):
        self.store = store
        self._estimates = {}
        self._estimate_lines = {}
        self._field_reports = {}
        self._rate_tables = {}
        self._wage_lines = {}
        self._payroll_reports = {}
        self._efilings = {}
        self._routes = {}
        self._route_outcomes = {}
        self._vehicles = {}
        self._telematics = {}
        self._templates = {}
        self._clauses = {}
        self._playbooks = {}
        self._negotiations = {}
        self._signature_requests = {}
        self._signature_outcomes = {}
        self._extractions = {}
        self._assistances = {}
        self._workflow_definitions = {}
        self._workflow_outcomes = {}
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
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`construct.access.require`; a plain string
        carries identity but no role). A denied attempt is
        recorded on the audit log with a ``:denied`` suffix
        before the error propagates; a missing actor is denied
        outright.
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

    # -- cost estimating (entry 204, built) ------------------------------

    def create_estimate(self, actor, project_id, title,
                        cost_data_source_ref=None):
        """Record an estimate against a core project. Action:
        cost_write. The estimate holds line items (recorded
        quantities and unit prices); its totals are derived at
        read in :meth:`estimate_view`. The proprietary cost DATA
        behind vendor engines is held as a source reference
        only — ``data_held_here`` is False and no cost database
        exists here."""
        self._guard(actor, "cost_write", "ext_estimate_create")
        _non_empty(title, "estimate title")
        _optional_text(cost_data_source_ref, "cost_data_source_ref")
        self.store.get_project(project_id, actor)
        with self._lock:
            estimate = {
                "id": self._next_id("est-"),
                "project_id": project_id,
                "title": title,
                "cost_data_source_ref": cost_data_source_ref,
                "data_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._estimates[estimate["id"]] = estimate
        self._audit(actor, "ext_estimate_create", estimate["id"],
                    {"project_id": project_id})
        return copy.deepcopy(estimate)

    def add_estimate_line(self, actor, estimate_id, description,
                          quantity, unit_price_cents):
        """Add a line item to an estimate. Action: cost_write.
        The line holds a recorded quantity and a recorded unit
        price (integer cents, house money rule); its line total
        is derived at read and never stored — the stored line
        carries no total key."""
        self._guard(actor, "cost_write", "ext_estimate_line_create")
        _non_empty(description, "line description")
        _positive_int(quantity, "quantity")
        _money(unit_price_cents, "unit_price_cents")
        with self._lock:
            self._get(self._estimates, estimate_id, "estimate")
            line = {
                "id": self._next_id("estl-"),
                "estimate_id": estimate_id,
                "description": description,
                "quantity": quantity,
                "unit_price_cents": unit_price_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._estimate_lines[line["id"]] = line
        self._audit(actor, "ext_estimate_line_create", line["id"],
                    {"estimate_id": estimate_id})
        return copy.deepcopy(line)

    def get_estimate(self, actor, estimate_id):
        """The stored estimate record — it carries no total key;
        totals exist only in :meth:`estimate_view`."""
        self._maybe_require(actor, "cost_read")
        return copy.deepcopy(self._get(self._estimates, estimate_id,
                                       "estimate"))

    def list_estimates(self, actor, project_id=None):
        self._maybe_require(actor, "cost_read")
        return [
            copy.deepcopy(e) for e in self._estimates.values()
            if project_id is None or e["project_id"] == project_id
        ]

    def list_estimate_lines(self, actor, estimate_id=None):
        self._maybe_require(actor, "cost_read")
        return [
            copy.deepcopy(line) for line in self._estimate_lines.values()
            if estimate_id is None or line["estimate_id"] == estimate_id
        ]

    def estimate_view(self, actor, estimate_id):
        """The estimate record plus its lines, each with its line
        total derived at read (quantity x unit price, integer
        cents, exact), and the estimate total derived as their
        sum. Nothing here is stored."""
        self._maybe_require(actor, "cost_read")
        estimate = self._get(self._estimates, estimate_id, "estimate")
        lines = []
        total = 0
        for line in self.list_estimate_lines(actor, estimate_id):
            line_total = line["quantity"] * line["unit_price_cents"]
            total += line_total
            rendered = dict(line)
            rendered["line_total_cents"] = line_total
            lines.append(rendered)
        view = copy.deepcopy(estimate)
        view["lines"] = lines
        view["line_count"] = len(lines)
        view["total_cents"] = total
        return view

    # -- GPS / field data collection (entry 205, built) -------------------

    def record_field_report(self, actor, project_id,
                            reported_position_label, observation_label,
                            worker_ref=None, dispatch_id=None,
                            form_ref=None, reported_at=None):
        """Record a field report for a core project. Action:
        record_write. The reported position label and the
        observation label are stored verbatim as the field
        system reported them — positions are caller-reported
        data, never sensed (``tracked_here`` /
        ``collected_here`` are False). Each report is a
        standalone record; no continuous tracking state exists.
        An optional dispatch reference must name a core dispatch
        of the same project."""
        self._guard(actor, "record_write", "ext_field_report_create")
        _non_empty(reported_position_label, "reported_position_label")
        _non_empty(observation_label, "observation_label")
        _optional_text(worker_ref, "worker_ref")
        _optional_text(form_ref, "form_ref")
        _optional_text(reported_at, "reported_at")
        self.store.get_project(project_id, actor)
        if dispatch_id is not None:
            dispatch = self.store.get_dispatch(dispatch_id, actor)
            if dispatch["project_id"] != project_id:
                raise ValidationError(
                    "dispatch %s does not belong to project %s"
                    % (dispatch_id, project_id))
        with self._lock:
            report = {
                "id": self._next_id("fld-"),
                "project_id": project_id,
                "dispatch_id": dispatch_id,
                "worker_ref": worker_ref,
                "form_ref": form_ref,
                "reported_position_label": reported_position_label,
                "observation_label": observation_label,
                "reported_at": reported_at,
                "tracked_here": False,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._field_reports[report["id"]] = report
        self._audit(actor, "ext_field_report_create", report["id"],
                    {"project_id": project_id})
        return copy.deepcopy(report)

    def get_field_report(self, actor, report_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._field_reports, report_id,
                                       "field report"))

    def list_field_reports(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(r) for r in self._field_reports.values()
            if project_id is None or r["project_id"] == project_id
        ]

    # -- prevailing wage (entry 211, built) --------------------------------

    def create_rate_table(self, actor, jurisdiction_label, trade_label,
                          base_rate_cents_per_hour,
                          fringe_rate_cents_per_hour,
                          effective_label=None):
        """Record a prevailing-wage rate table as data. Action:
        workforce_write. Rates are integer cents per hour (base
        positive, fringe may be zero); the table determines
        nothing by itself — amounts are computed at read from a
        wage line's recorded minutes by
        :func:`_compute_wage_amounts`."""
        self._guard(actor, "workforce_write", "ext_rate_table_create")
        _non_empty(jurisdiction_label, "jurisdiction_label")
        _non_empty(trade_label, "trade_label")
        _rate_cents(base_rate_cents_per_hour, "base_rate_cents_per_hour",
                    allow_zero=False)
        _rate_cents(fringe_rate_cents_per_hour, "fringe_rate_cents_per_hour",
                    allow_zero=True)
        _optional_text(effective_label, "effective_label")
        with self._lock:
            table = {
                "id": self._next_id("rate-"),
                "jurisdiction_label": jurisdiction_label,
                "trade_label": trade_label,
                "base_rate_cents_per_hour": base_rate_cents_per_hour,
                "fringe_rate_cents_per_hour": fringe_rate_cents_per_hour,
                "effective_label": effective_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rate_tables[table["id"]] = table
        self._audit(actor, "ext_rate_table_create", table["id"],
                    {"trade_label": trade_label})
        return copy.deepcopy(table)

    def record_wage_line(self, actor, project_id, org_id, worker_ref,
                         rate_table_id, minutes, period_label):
        """Record one wage line: recorded inputs only. Action:
        workforce_write. The line holds a rate-table reference,
        an opaque worker reference, and integer minutes — no
        amount is stored; base, fringe, and gross are derived
        at read in :meth:`wage_line_view`. The project and org
        must exist in the core."""
        self._guard(actor, "workforce_write", "ext_wage_line_create")
        _non_empty(worker_ref, "worker_ref")
        _non_empty(period_label, "period_label")
        _positive_int(minutes, "minutes")
        self.store.get_project(project_id, actor)
        self.store.get_org(org_id, actor)
        with self._lock:
            self._get(self._rate_tables, rate_table_id, "rate table")
            line = {
                "id": self._next_id("wage-"),
                "project_id": project_id,
                "org_id": org_id,
                "worker_ref": worker_ref,
                "rate_table_id": rate_table_id,
                "minutes": minutes,
                "period_label": period_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._wage_lines[line["id"]] = line
        self._audit(actor, "ext_wage_line_create", line["id"],
                    {"project_id": project_id, "org_id": org_id})
        return copy.deepcopy(line)

    def get_rate_table(self, actor, table_id):
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._rate_tables, table_id,
                                       "rate table"))

    def list_rate_tables(self, actor):
        self._maybe_require(actor, "workforce_read")
        return [copy.deepcopy(t) for t in self._rate_tables.values()]

    def get_wage_line(self, actor, line_id):
        """The stored wage line — it carries no amount key;
        amounts exist only in :meth:`wage_line_view`."""
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._wage_lines, line_id,
                                       "wage line"))

    def list_wage_lines(self, actor, project_id=None, org_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(line) for line in self._wage_lines.values()
            if (project_id is None or line["project_id"] == project_id)
            and (org_id is None or line["org_id"] == org_id)
        ]

    def wage_line_view(self, actor, line_id):
        """The wage line plus the amounts derived at read from
        its rate table and recorded minutes by
        :func:`_compute_wage_amounts`: ``base_cents``,
        ``fringe_cents``, and ``gross_cents``, each rendered
        exactly (an int when whole, else a ``"num/den"``
        string). Nothing here is stored."""
        self._maybe_require(actor, "workforce_read")
        line = self._get(self._wage_lines, line_id, "wage line")
        table = self._get(self._rate_tables, line["rate_table_id"],
                          "rate table")
        base, fringe, gross = _compute_wage_amounts(
            table["base_rate_cents_per_hour"],
            table["fringe_rate_cents_per_hour"],
            line["minutes"])
        view = copy.deepcopy(line)
        view["base_cents"] = _cents_out(base)
        view["fringe_cents"] = _cents_out(fringe)
        view["gross_cents"] = _cents_out(gross)
        return view

    def generate_certified_payroll_report(self, actor, project_id, org_id,
                                          period_label, line_ids):
        """Generate a certified-payroll report record over wage
        lines. Action: workforce_write. What is derived here is
        exactly this: the report record references the given
        wage lines (each must belong to the project and org),
        and its totals are derived at read in
        :meth:`certified_payroll_view` from the same wage seam
        — the stored report carries no totals. No core payroll
        record is created or changed."""
        self._guard(actor, "workforce_write", "ext_payroll_report_create")
        _non_empty(period_label, "period_label")
        if not isinstance(line_ids, (list, tuple)) or not line_ids:
            raise ValidationError("line_ids must be a non-empty list")
        line_ids = list(line_ids)
        if len(set(line_ids)) != len(line_ids):
            raise ValidationError("line_ids must not contain duplicates")
        self.store.get_project(project_id, actor)
        self.store.get_org(org_id, actor)
        with self._lock:
            for line_id in line_ids:
                line = self._get(self._wage_lines, line_id, "wage line")
                if line["project_id"] != project_id \
                        or line["org_id"] != org_id:
                    raise ValidationError(
                        "wage line %s does not belong to project %s / org %s"
                        % (line_id, project_id, org_id))
            report = {
                "id": self._next_id("cpr-"),
                "project_id": project_id,
                "org_id": org_id,
                "period_label": period_label,
                "line_ids": line_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payroll_reports[report["id"]] = report
        self._audit(actor, "ext_payroll_report_create", report["id"],
                    {"project_id": project_id, "org_id": org_id})
        return copy.deepcopy(report)

    def get_certified_payroll_report(self, actor, report_id):
        """The stored report record — it carries no totals;
        totals exist only in :meth:`certified_payroll_view`."""
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._payroll_reports, report_id,
                                       "certified payroll report"))

    def list_certified_payroll_reports(self, actor, project_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(r) for r in self._payroll_reports.values()
            if project_id is None or r["project_id"] == project_id
        ]

    def certified_payroll_view(self, actor, report_id):
        """The report record plus its totals derived at read:
        the exact sum over its wage lines of the seam's base,
        fringe, and gross amounts (each rendered exactly), the
        line count, and the distinct recorded worker references
        count. Nothing here is stored."""
        self._maybe_require(actor, "workforce_read")
        report = self._get(self._payroll_reports, report_id,
                           "certified payroll report")
        total_base = Fraction(0)
        total_fringe = Fraction(0)
        total_gross = Fraction(0)
        workers = set()
        for line_id in report["line_ids"]:
            line = self._wage_lines[line_id]
            table = self._rate_tables[line["rate_table_id"]]
            base, fringe, gross = _compute_wage_amounts(
                table["base_rate_cents_per_hour"],
                table["fringe_rate_cents_per_hour"],
                line["minutes"])
            total_base += base
            total_fringe += fringe
            total_gross += gross
            workers.add(line["worker_ref"])
        view = copy.deepcopy(report)
        view["line_count"] = len(report["line_ids"])
        view["worker_count"] = len(workers)
        view["total_base_cents"] = _cents_out(total_base)
        view["total_fringe_cents"] = _cents_out(total_fringe)
        view["total_gross_cents"] = _cents_out(total_gross)
        return view

    def record_efiling(self, actor, report_id, filing_ref):
        """Record an e-filing of a certified-payroll report, as
        a labeled reference implementation. Action:
        workforce_write. ``filed_here`` is False: filing happens
        on the receiving agency's system; what is recorded here
        is the filing reference exactly as reported."""
        self._guard(actor, "workforce_write", "ext_efiling_create")
        _non_empty(filing_ref, "filing_ref")
        with self._lock:
            self._get(self._payroll_reports, report_id,
                      "certified payroll report")
            filing = {
                "id": self._next_id("efl-"),
                "report_id": report_id,
                "filing_ref": filing_ref,
                "reference_stub": True,
                "filed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._efilings[filing["id"]] = filing
        self._audit(actor, "ext_efiling_create", filing["id"],
                    {"report_id": report_id})
        return copy.deepcopy(filing)

    def get_efiling(self, actor, filing_id):
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._efilings, filing_id,
                                       "e-filing"))

    def list_efilings(self, actor, report_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(f) for f in self._efilings.values()
            if report_id is None or f["report_id"] == report_id
        ]

    # -- dispatch routing (entry 212, built) -------------------------------

    def create_route_plan(self, actor, dispatch_id, stops):
        """Record a route plan for a core dispatch, held as
        data. Action: record_write. ``stops`` is an ordered list
        of stop labels stored verbatim in the caller's recorded
        order — ``optimized_here`` is False: no optimizer runs,
        and the plan's order is the recorded order, not a
        computed one. Recording a plan changes no core record."""
        self._guard(actor, "record_write", "ext_route_create")
        if not isinstance(stops, (list, tuple)) or not stops:
            raise ValidationError("stops must be a non-empty list")
        stops = list(stops)
        for stop in stops:
            _non_empty(stop, "route stop")
        dispatch = self.store.get_dispatch(dispatch_id, actor)
        with self._lock:
            route = {
                "id": self._next_id("rte-"),
                "dispatch_id": dispatch_id,
                "project_id": dispatch["project_id"],
                "stops": stops,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._routes[route["id"]] = route
        self._audit(actor, "ext_route_create", route["id"],
                    {"dispatch_id": dispatch_id})
        return copy.deepcopy(route)

    def record_route_outcome(self, actor, route_id, outcome_label):
        """Record a route outcome exactly as reported. Action:
        record_write. The label is stored verbatim;
        ``optimized_here`` is False."""
        self._guard(actor, "record_write", "ext_route_outcome_create")
        if outcome_label not in ROUTE_OUTCOME_LABELS:
            raise ValidationError(
                "unknown route outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._routes, route_id, "route plan")
            outcome = {
                "id": self._next_id("rto-"),
                "route_id": route_id,
                "outcome_label": outcome_label,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._route_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_route_outcome_create", outcome["id"],
                    {"route_id": route_id})
        return copy.deepcopy(outcome)

    def get_route_plan(self, actor, route_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._routes, route_id,
                                       "route plan"))

    def list_route_plans(self, actor, dispatch_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(r) for r in self._routes.values()
            if dispatch_id is None or r["dispatch_id"] == dispatch_id
        ]

    def list_route_outcomes(self, actor, route_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(o) for o in self._route_outcomes.values()
            if route_id is None or o["route_id"] == route_id
        ]

    def route_view(self, actor, route_id):
        """The route plan, its reported outcomes, and the core
        dispatch record side by side — the dispatch is read from
        the core at read time, untouched by the plan."""
        self._maybe_require(actor, "record_read")
        route = self._get(self._routes, route_id, "route plan")
        view = copy.deepcopy(route)
        view["outcomes"] = self.list_route_outcomes(actor, route_id)
        view["dispatch"] = self.store.get_dispatch(
            route["dispatch_id"], actor)
        return view

    # -- fleet & vehicle telematics (entry 206, reference stub) ------------

    def register_vehicle(self, actor, project_id, vehicle_ref):
        """Register a vehicle record, as a labeled reference
        implementation. Action: record_write. The record holds
        an opaque vehicle reference only;
        ``monitored_here`` is False — no vehicle is monitored
        by this build."""
        self._guard(actor, "record_write", "ext_vehicle_create")
        _non_empty(vehicle_ref, "vehicle_ref")
        self.store.get_project(project_id, actor)
        with self._lock:
            vehicle = {
                "id": self._next_id("veh-"),
                "project_id": project_id,
                "vehicle_ref": vehicle_ref,
                "reference_stub": True,
                "monitored_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vehicles[vehicle["id"]] = vehicle
        self._audit(actor, "ext_vehicle_create", vehicle["id"],
                    {"project_id": project_id})
        return copy.deepcopy(vehicle)

    def record_telematics_report(self, actor, vehicle_id, report_label,
                                 reported_driver_score_label=None):
        """Record a telematics report exactly as the telematics
        platform reported it. Action: record_write. The report
        label and the driver-behavior score label are REPORTED
        labels stored verbatim — no score is computed here and
        no numeric score field exists on the record."""
        self._guard(actor, "record_write", "ext_telematics_create")
        if report_label not in TELEMATICS_REPORT_LABELS:
            raise ValidationError(
                "unknown telematics report label: %r" % (report_label,))
        _optional_text(reported_driver_score_label,
                       "reported_driver_score_label")
        with self._lock:
            vehicle = self._get(self._vehicles, vehicle_id, "vehicle")
            report = {
                "id": self._next_id("tel-"),
                "vehicle_id": vehicle_id,
                "project_id": vehicle["project_id"],
                "report_label": report_label,
                "reported_driver_score_label": reported_driver_score_label,
                "reference_stub": True,
                "monitored_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telematics[report["id"]] = report
        self._audit(actor, "ext_telematics_create", report["id"],
                    {"vehicle_id": vehicle_id})
        return copy.deepcopy(report)

    def get_vehicle(self, actor, vehicle_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._vehicles, vehicle_id,
                                       "vehicle"))

    def list_vehicles(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(v) for v in self._vehicles.values()
            if project_id is None or v["project_id"] == project_id
        ]

    def list_telematics_reports(self, actor, vehicle_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(r) for r in self._telematics.values()
            if vehicle_id is None or r["vehicle_id"] == vehicle_id
        ]

    # -- contract lifecycle (entry 207, reference stub) ---------------------

    def create_template_record(self, actor, title, template_ref):
        """Record a contract template as metadata, as a labeled
        reference implementation. Action: contract_write. The
        record holds a title and an opaque template reference
        only — no template content field exists."""
        self._guard(actor, "contract_write", "ext_template_create")
        _non_empty(title, "template title")
        _non_empty(template_ref, "template_ref")
        with self._lock:
            template = {
                "id": self._next_id("tpl-"),
                "title": title,
                "template_ref": template_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._templates[template["id"]] = template
        self._audit(actor, "ext_template_create", template["id"],
                    {"title": title})
        return copy.deepcopy(template)

    def create_clause_record(self, actor, clause_label, template_id=None):
        """Record a clause-library entry as metadata. Action:
        contract_write. The record holds a clause label (and an
        optional template reference) only — no clause text field
        exists."""
        self._guard(actor, "contract_write", "ext_clause_create")
        _non_empty(clause_label, "clause_label")
        with self._lock:
            if template_id is not None:
                self._get(self._templates, template_id, "template")
            clause = {
                "id": self._next_id("cls-"),
                "template_id": template_id,
                "clause_label": clause_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._clauses[clause["id"]] = clause
        self._audit(actor, "ext_clause_create", clause["id"],
                    {"clause_label": clause_label})
        return copy.deepcopy(clause)

    def create_playbook_record(self, actor, title, playbook_ref):
        """Record a negotiation playbook as metadata. Action:
        contract_write. The record holds a title and an opaque
        playbook reference only — no playbook content field
        exists."""
        self._guard(actor, "contract_write", "ext_playbook_create")
        _non_empty(title, "playbook title")
        _non_empty(playbook_ref, "playbook_ref")
        with self._lock:
            playbook = {
                "id": self._next_id("pbk-"),
                "title": title,
                "playbook_ref": playbook_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._playbooks[playbook["id"]] = playbook
        self._audit(actor, "ext_playbook_create", playbook["id"],
                    {"title": title})
        return copy.deepcopy(playbook)

    def record_negotiation_outcome(self, actor, contract_id, outcome_label,
                                   playbook_id=None):
        """Record a negotiation outcome against a core contract
        exactly as reported. Action: contract_write. Redlining
        happens in the parties' own tools — ``redlined_here``
        is False and the outcome label is stored verbatim.
        Recording an outcome changes no core record."""
        self._guard(actor, "contract_write", "ext_negotiation_create")
        if outcome_label not in NEGOTIATION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown negotiation outcome label: %r" % (outcome_label,))
        self.store.get_contract(contract_id, actor)
        with self._lock:
            if playbook_id is not None:
                self._get(self._playbooks, playbook_id, "playbook")
            outcome = {
                "id": self._next_id("neg-"),
                "contract_id": contract_id,
                "playbook_id": playbook_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "redlined_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._negotiations[outcome["id"]] = outcome
        self._audit(actor, "ext_negotiation_create", outcome["id"],
                    {"contract_id": contract_id})
        return copy.deepcopy(outcome)

    def get_template(self, actor, template_id):
        self._maybe_require(actor, "contract_read")
        return copy.deepcopy(self._get(self._templates, template_id,
                                       "template"))

    def list_templates(self, actor):
        self._maybe_require(actor, "contract_read")
        return [copy.deepcopy(t) for t in self._templates.values()]

    def list_clauses(self, actor, template_id=None):
        self._maybe_require(actor, "contract_read")
        return [
            copy.deepcopy(c) for c in self._clauses.values()
            if template_id is None or c["template_id"] == template_id
        ]

    def list_playbooks(self, actor):
        self._maybe_require(actor, "contract_read")
        return [copy.deepcopy(p) for p in self._playbooks.values()]

    def list_negotiation_outcomes(self, actor, contract_id=None):
        self._maybe_require(actor, "contract_read")
        return [
            copy.deepcopy(o) for o in self._negotiations.values()
            if contract_id is None or o["contract_id"] == contract_id
        ]

    # -- e-signature execution (entry 208, reference stub) -------------------

    def record_signature_request(self, actor, signer_ref,
                                 contract_id=None, document_id=None):
        """Record a signature request, as a labeled reference
        implementation. Action: contract_write. Exactly one of
        a core contract or a core document must be named;
        ``signed_here`` is False and no signature-value field
        exists — execution happens in the signing service."""
        self._guard(actor, "contract_write", "ext_signature_request_create")
        _non_empty(signer_ref, "signer_ref")
        if (contract_id is None) == (document_id is None):
            raise ValidationError(
                "exactly one of contract_id, document_id must be given")
        if contract_id is not None:
            self.store.get_contract(contract_id, actor)
        if document_id is not None:
            self.store.get_document(document_id, actor)
        with self._lock:
            request = {
                "id": self._next_id("sig-"),
                "contract_id": contract_id,
                "document_id": document_id,
                "signer_ref": signer_ref,
                "reference_stub": True,
                "signed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signature_requests[request["id"]] = request
        self._audit(actor, "ext_signature_request_create", request["id"],
                    {"signer_ref": signer_ref})
        return copy.deepcopy(request)

    def record_signature_outcome(self, actor, request_id, outcome_label):
        """Record a signature outcome exactly as the signing
        service reported it. Action: contract_write. The label
        is stored verbatim; ``signed_here`` is False."""
        self._guard(actor, "contract_write", "ext_signature_outcome_create")
        if outcome_label not in SIGNATURE_OUTCOME_LABELS:
            raise ValidationError(
                "unknown signature outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._signature_requests, request_id,
                      "signature request")
            outcome = {
                "id": self._next_id("sigo-"),
                "request_id": request_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "signed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signature_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_signature_outcome_create", outcome["id"],
                    {"request_id": request_id})
        return copy.deepcopy(outcome)

    def get_signature_request(self, actor, request_id):
        self._maybe_require(actor, "contract_read")
        return copy.deepcopy(self._get(self._signature_requests, request_id,
                                       "signature request"))

    def list_signature_requests(self, actor, contract_id=None):
        self._maybe_require(actor, "contract_read")
        return [
            copy.deepcopy(r) for r in self._signature_requests.values()
            if contract_id is None or r["contract_id"] == contract_id
        ]

    def list_signature_outcomes(self, actor, request_id=None):
        self._maybe_require(actor, "contract_read")
        return [
            copy.deepcopy(o) for o in self._signature_outcomes.values()
            if request_id is None or o["request_id"] == request_id
        ]

    # -- AI/ML models (entry 209, reference stub) -------------------------------

    def record_extraction_result(self, actor, document_id, model_label,
                                 result_ref):
        """Record an AI data-extraction result against a core
        document, as a labeled reference implementation.
        Action: document_write. The result is held as an opaque
        reference only — ``inference_here`` is False and no
        extracted-text field exists."""
        self._guard(actor, "document_write", "ext_extraction_create")
        _non_empty(model_label, "model_label")
        _non_empty(result_ref, "result_ref")
        self.store.get_document(document_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("aix-"),
                "document_id": document_id,
                "model_label": model_label,
                "result_ref": result_ref,
                "reference_stub": True,
                "inference_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._extractions[record["id"]] = record
        self._audit(actor, "ext_extraction_create", record["id"],
                    {"document_id": document_id})
        return copy.deepcopy(record)

    def record_negotiation_assistance(self, actor, contract_id, model_label,
                                      result_ref):
        """Record an AI negotiation-assistance result against a
        core contract, as a labeled reference implementation.
        Action: contract_write. The result is held as an opaque
        reference only — ``inference_here`` is False and no
        generated-text or advice field exists."""
        self._guard(actor, "contract_write", "ext_assistance_create")
        _non_empty(model_label, "model_label")
        _non_empty(result_ref, "result_ref")
        self.store.get_contract(contract_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("ain-"),
                "contract_id": contract_id,
                "model_label": model_label,
                "result_ref": result_ref,
                "reference_stub": True,
                "inference_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assistances[record["id"]] = record
        self._audit(actor, "ext_assistance_create", record["id"],
                    {"contract_id": contract_id})
        return copy.deepcopy(record)

    def list_extraction_results(self, actor, document_id=None):
        self._maybe_require(actor, "document_read")
        return [
            copy.deepcopy(r) for r in self._extractions.values()
            if document_id is None or r["document_id"] == document_id
        ]

    def list_negotiation_assistance(self, actor, contract_id=None):
        self._maybe_require(actor, "contract_read")
        return [
            copy.deepcopy(r) for r in self._assistances.values()
            if contract_id is None or r["contract_id"] == contract_id
        ]

    # -- workflow / process automation (entry 210, reference stub) --------------

    def create_workflow_definition(self, actor, label, steps):
        """Record a workflow definition as data, as a labeled
        reference implementation. Action: record_write.
        ``steps`` is an ordered list of step labels stored
        verbatim; the core's lifecycle state machines are the
        in-core seed this definition describes. The registry
        never executes a definition — ``executed_here`` is
        False and there is no run API."""
        self._guard(actor, "record_write", "ext_workflow_definition_create")
        _non_empty(label, "workflow label")
        if not isinstance(steps, (list, tuple)) or not steps:
            raise ValidationError("steps must be a non-empty list")
        steps = list(steps)
        for step in steps:
            _non_empty(step, "workflow step")
        with self._lock:
            definition = {
                "id": self._next_id("wfd-"),
                "label": label,
                "steps": steps,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_definitions[definition["id"]] = definition
        self._audit(actor, "ext_workflow_definition_create", definition["id"],
                    {"label": label})
        return copy.deepcopy(definition)

    def record_workflow_outcome(self, actor, definition_id, outcome_label):
        """Record a workflow outcome exactly as the executing
        system reported it. Action: record_write. The label is
        stored verbatim; ``executed_here`` is False — recording
        an outcome executes nothing and changes no definition
        and no core record."""
        self._guard(actor, "record_write", "ext_workflow_outcome_create")
        if outcome_label not in WORKFLOW_OUTCOME_LABELS:
            raise ValidationError(
                "unknown workflow outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._workflow_definitions, definition_id,
                      "workflow definition")
            outcome = {
                "id": self._next_id("wfo-"),
                "definition_id": definition_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_workflow_outcome_create", outcome["id"],
                    {"definition_id": definition_id})
        return copy.deepcopy(outcome)

    def get_workflow_definition(self, actor, definition_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._workflow_definitions,
                                       definition_id, "workflow definition"))

    def list_workflow_definitions(self, actor):
        self._maybe_require(actor, "record_read")
        return [copy.deepcopy(d) for d in self._workflow_definitions.values()]

    def list_workflow_outcomes(self, actor, definition_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(o) for o in self._workflow_outcomes.values()
            if definition_id is None or o["definition_id"] == definition_id
        ]
