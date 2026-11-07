"""Final GAPS batch extensions for the Mobile Device Management
(MDM) L2 build.

Clean-room, standard-library-only extensions for the 15 open
Extended entries of Singleton 50 (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a wrapper
around :class:`MdmStore`; every core module is untouched.

Honesty of form, per the batch brief: an "engine" or "plane" here
is its in-substrate form -- records plus deterministic derivations
over the group's OWN records.

- The founding fork is a Telecommunication Expense Management
  system filed under MDM; its taxonomy contains no
  device-management family, and the addition fork (a genuine MDM
  platform) claimed zero families for exactly that reason (see
  ``../ADDENDUM.md`` section 3). The device-surface entries below
  are therefore claim-driven records work over **opaque
  caller-supplied device references only** -- never an identifier
  registry. No record shape in this module has a field that could
  hold an IMEI, a serial number, a phone number, a MAC address,
  or any location data (coordinate, address, or place label);
  that is the founding privacy invariant (UNION-SPEC core
  function 2) carried over verbatim, and it is pinned by test
  over every stored extension record.
- The device-command plane is command RECORDS: a request, a
  confirmation by someone other than the requester (separation
  of duties, the batch's fresh negative-control seam), and an
  outcome recorded as reported. Every command record carries
  ``executed_here: False`` -- this build issues no command to
  any device, ever.
- Device location & tracking is tracking-service configuration
  and status records: an opaque device reference, a service
  label, and reported service-state labels (active / inactive /
  suspended). There is no location field of any kind;
  ``location_data_held`` is False on every tracking record and
  view.
- Enrollment & provisioning, workflow execution, carrier
  integration, and alert delivery ship as labeled reference
  implementations: records carry ``reference_stub: True``
  (transport receipts also ``reference_transport: True``) and
  state ``recorded_reference_only``. Creating one changes no
  core record; pinned by test.
- The optimization entry rests on the founding fork's product
  *name* only -- no description sentence claims an optimization
  function (UNION-SPEC wording-artifact log). What is built is
  recorded optimization RECOMMENDATION records: the
  recommender's action label, rationale, and optional estimated
  saving, all recorded verbatim as data. No optimizer runs and
  nothing is optimized; ``computed_here`` is False.
- The forecasting entry's own text binds it: projections are
  recorded verbatim, never computed. Forecast records hold
  caller-supplied projected amounts exactly as supplied; the
  forecast *view* places them beside the budget's derived
  actuals, each figure labeled with its source.
- Compliance state, reconciliation totals, analytic views,
  operations summaries, and tracking current state are
  derivations computed at read over recorded data, labeled
  with their method, stored nowhere.

Doctrines carried from the core: opaque ``*_ref`` strings only;
money is integer cents with floats and booleans rejected at the
boundary (the core store's own validators are reused);
derived-never-stored for every computed value; append-only
audit on the core store's log with ``ext_``-prefixed actions
for every successful extension mutation (denied operations
record nothing -- the store-level convention; denial auditing
lives in the service layer); RBAC via :mod:`mdm.access` through
the core store's scoping seam (role permission plus
organization membership), enforced before any state change or
id allocation, so a failed operation consumes no id and changes
nothing.

RBAC action mapping (the core action set is fixed): most
extension creates ride ``record`` (the registry/record family);
forecasts ride ``enter`` with the budget family; service
operations open on ``enter`` and transition on ``record``;
device commands are requested on ``enter``, confirmed on
``decide``, and closed by a reported outcome on ``record``;
device policies and app catalog records ride ``enter``; all
reads ride ``read``.
"""

import threading
from datetime import datetime, timezone

from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import _money, _text

# No stored extension record may carry any of these keys: the
# founding privacy invariant, extended from the inventory pin to
# the whole extension surface. Devices are opaque references;
# there is no identifier field and no location field, of any
# kind, anywhere in this module.
FORBIDDEN_KEYS = {
    "imei", "serial", "serial_number", "phone", "phone_number",
    "mac", "mac_address", "latitude", "longitude", "lat", "lon",
    "lng", "coordinate", "coordinates", "address", "gps",
    "location", "device_id", "device_identifier",
}

RECOMMENDATION_METHOD = "recorded_recommendation"
RECONCILIATION_METHOD = "recorded_lines_derived_totals"
FORECAST_METHOD = "recorded_verbatim"
ANALYTIC_METHOD = "deterministic_derivation"
COMPLIANCE_METHOD = "derived_from_recorded_checks"
TRACKING_METHOD = "derived_from_recorded_status_reports"

CARRIER_CONNECTOR_KINDS = ("order_execution", "bill_feed", "data_integration")
CARRIER_EVENT_KINDS = (
    "order_execution_requested", "bill_feed_received", "data_sync_reported",
)
RECONCILIATION_LINE_STATUSES = ("matched", "variance", "unmatched")
ANALYTIC_KINDS = (
    "spending_by_period", "recurring_by_kind", "open_dispute_exposure",
)
REPORT_SECTIONS = ("inventory", "orders", "bills", "budgets", "alerts", "chargebacks")
DELIVERY_CHANNELS = ("email", "sms", "push")
OPERATION_KINDS = (
    "line_audit", "rate_review", "estate_cleanup", "vendor_coordination", "other",
)
OPERATION_TRANSITIONS = {
    "open": ("in_progress", "cancelled"),
    "in_progress": ("completed", "cancelled"),
    "completed": (),
    "cancelled": (),
}
COMMAND_KINDS = ("wipe", "lock", "unlock")
COMMAND_OUTCOMES = ("reported_completed", "reported_failed")
TRACKING_STATES = ("active", "inactive", "suspended")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _ref(value, field):
    return _text(value, field)


def _choice(value, choices, field):
    if value not in choices:
        raise ValidationError("%s must be one of %r" % (field, choices))
    return value


def _text_list(value, field):
    if not isinstance(value, list) or not value:
        raise ValidationError("%s must be a non-empty list of names" % field)
    for item in value:
        _text(item, field)
    return list(value)


class MdmExtensions:
    """GAPS-batch extension surface wrapping a core :class:`MdmStore`."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        self._recommendations = {}
        self._workflow_executions = {}
        self._carrier_connectors = {}
        self._carrier_events = {}
        self._reconciliations = {}
        self._forecasts = {}
        self._analytics = {}
        self._report_definitions = {}
        self._report_runs = {}
        self._deliveries = {}
        self._portal_pages = {}
        self._operations = {}
        self._enrollments = {}
        self._commands = {}
        self._policies = {}
        self._compliance_checks = {}
        self._apps = {}
        self._app_distributions = {}
        self._tracking = {}
        self._tracking_reports = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _scoped(self, actor, org_id, action):
        return self.store._scoped(actor, org_id, action)

    def _record(self, actor, action, target, details=None):
        self.store._record(actor, "ext_" + action, target, details)

    def _fetch(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("no such %s: %r" % (what, record_id))
        return record

    def _get_scoped(self, actor, table, record_id, what):
        self.store._check_role(actor, "read")
        record = self._fetch(table, record_id, what)
        self._scoped(actor, record["org_id"], "read")
        return record

    def _list_scoped(self, actor, table, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(r) for r in table.values() if r["org_id"] == org_id]

    # -- optimization recommendations (idx 470, built) ---------------------
    # Named from the founding fork's product name only; no claim
    # exists. Recorded recommendations: data, never an optimizer.

    def create_optimization_recommendation(self, actor, org_id, subject_ref,
                                           action_label, rationale,
                                           estimated_saving_cents=None):
        """Record an optimization recommendation as data.

        The recommendation is a human or external analyst's
        recorded judgment: subject (an opaque reference), the
        recommended action label, the rationale verbatim, and an
        optional estimated saving recorded verbatim. Nothing is
        computed and nothing is optimized here.
        """
        self._scoped(actor, org_id, "record")
        _ref(subject_ref, "subject_ref")
        _text(action_label, "action_label")
        _text(rationale, "rationale")
        if estimated_saving_cents is not None:
            _money(estimated_saving_cents, "estimated_saving_cents")
        with self._lock:
            record = {
                "id": self._mint("opt-"),
                "org_id": org_id,
                "subject_ref": subject_ref,
                "action_label": action_label,
                "rationale": rationale,
                "estimated_saving_cents": estimated_saving_cents,
                "method": RECOMMENDATION_METHOD,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._recommendations[record["id"]] = record
        self._record(actor, "optimization_recommendation_create",
                     record["id"], {"subject_ref": subject_ref})
        return dict(record)

    def get_optimization_recommendation(self, actor, recommendation_id):
        return dict(self._get_scoped(
            actor, self._recommendations, recommendation_id,
            "optimization recommendation"))

    def list_optimization_recommendations(self, actor, org_id):
        return self._list_scoped(actor, self._recommendations, org_id)

    # -- workflow execution reference (idx 471, stub-engine) ---------------

    def record_workflow_execution(self, actor, workflow_id):
        """Record a reference execution request for a workflow.

        Labeled reference implementation: the core registry holds
        definitions and never executes them; this record states
        that an execution was requested of an external engine.
        Nothing executes here and no core record changes.
        """
        workflow = self.store._workflows.get(workflow_id)
        if workflow is None:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        self._scoped(actor, workflow["org_id"], "record")
        with self._lock:
            record = {
                "id": self._mint("wex-"),
                "org_id": workflow["org_id"],
                "workflow_id": workflow_id,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "executed": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_executions[record["id"]] = record
        self._record(actor, "workflow_execution_record", record["id"],
                     {"workflow_id": workflow_id})
        return dict(record)

    def get_workflow_execution(self, actor, execution_id):
        return dict(self._get_scoped(
            actor, self._workflow_executions, execution_id,
            "workflow execution record"))

    def list_workflow_executions(self, actor, org_id):
        return self._list_scoped(actor, self._workflow_executions, org_id)

    # -- carrier & network integration reference (idx 472, stub-engine) ----

    def create_carrier_connector(self, actor, org_id, carrier_ref, kind):
        """Register a carrier connector as a reference record.

        No carrier is connected to; the record names the
        integration surface an external engine would serve.
        """
        self._scoped(actor, org_id, "record")
        _ref(carrier_ref, "carrier_ref")
        _choice(kind, CARRIER_CONNECTOR_KINDS, "kind")
        with self._lock:
            record = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "carrier_ref": carrier_ref,
                "kind": kind,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._carrier_connectors[record["id"]] = record
        self._record(actor, "carrier_connector_create", record["id"],
                     {"carrier_ref": carrier_ref, "kind": kind})
        return dict(record)

    def record_carrier_event(self, actor, connector_id, event_kind, detail):
        """Record a carrier event as reported / requested.

        Order executions are recorded as requested of the
        carrier, feed arrivals as reported receipts. Nothing is
        executed against, or received from, any carrier here.
        """
        connector = self._fetch(self._carrier_connectors, connector_id,
                                "carrier connector")
        self._scoped(actor, connector["org_id"], "record")
        _choice(event_kind, CARRIER_EVENT_KINDS, "event_kind")
        _text(detail, "detail")
        with self._lock:
            record = {
                "id": self._mint("cev-"),
                "org_id": connector["org_id"],
                "connector_id": connector_id,
                "event_kind": event_kind,
                "detail": detail,
                "reference_stub": True,
                "reference_transport": True,
                "status": "recorded_reference_only",
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._carrier_events[record["id"]] = record
        self._record(actor, "carrier_event_record", record["id"],
                     {"connector_id": connector_id, "event_kind": event_kind})
        return dict(record)

    def get_carrier_connector(self, actor, connector_id):
        return dict(self._get_scoped(
            actor, self._carrier_connectors, connector_id, "carrier connector"))

    def list_carrier_connectors(self, actor, org_id):
        return self._list_scoped(actor, self._carrier_connectors, org_id)

    def list_carrier_events(self, actor, org_id):
        return self._list_scoped(actor, self._carrier_events, org_id)

    # -- bill reconciliation beyond registry validation (idx 473, built) ---
    # Line-level matching against carrier data happens outside
    # this build; what lands here is the reconciliation case:
    # lines recorded verbatim (amounts and the reconciler's
    # reported line status), with totals derived at read.

    def create_reconciliation(self, actor, bill_id, lines):
        """Record a line-level reconciliation case for a bill.

        Each line is recorded verbatim: a label, the billed and
        expected amounts in integer cents, and the reconciler's
        reported status for the line. The case record stores no
        totals; totals are derived at read (see the view).
        Recording a case never modifies the bill.
        """
        bill = self.store._bill(bill_id)
        self._scoped(actor, bill["org_id"], "record")
        if not isinstance(lines, list) or not lines:
            raise ValidationError("lines must be a non-empty list")
        cleaned = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each reconciliation line must be an object")
            _text(line.get("label"), "line label")
            _money(line.get("billed_cents"), "line billed_cents")
            _money(line.get("expected_cents"), "line expected_cents")
            _choice(line.get("status"), RECONCILIATION_LINE_STATUSES,
                    "line status")
            cleaned.append({
                "label": line["label"],
                "billed_cents": line["billed_cents"],
                "expected_cents": line["expected_cents"],
                "status": line["status"],
            })
        with self._lock:
            record = {
                "id": self._mint("rec-"),
                "org_id": bill["org_id"],
                "bill_id": bill_id,
                "lines": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reconciliations[record["id"]] = record
        self._record(actor, "reconciliation_create", record["id"],
                     {"bill_id": bill_id, "lines": len(cleaned)})
        view = dict(record)
        view["lines"] = [dict(line) for line in record["lines"]]
        return view

    def get_reconciliation(self, actor, reconciliation_id):
        record = self._get_scoped(actor, self._reconciliations,
                                  reconciliation_id, "reconciliation")
        view = dict(record)
        view["lines"] = [dict(line) for line in record["lines"]]
        return view

    def list_reconciliations(self, actor, org_id):
        return [self.get_reconciliation(actor, r["id"])
                for r in self._list_scoped(actor, self._reconciliations, org_id)]

    def reconciliation_view(self, actor, reconciliation_id):
        """Derived totals over a case's recorded lines.

        Deterministic arithmetic over the recorded lines only:
        summed billed / expected / variance and counts by the
        lines' reported statuses. Computed at read, stored
        nowhere.
        """
        record = self._get_scoped(actor, self._reconciliations,
                                  reconciliation_id, "reconciliation")
        billed = sum(line["billed_cents"] for line in record["lines"])
        expected = sum(line["expected_cents"] for line in record["lines"])
        by_status = {status: 0 for status in RECONCILIATION_LINE_STATUSES}
        for line in record["lines"]:
            by_status[line["status"]] += 1
        return {
            "reconciliation_id": record["id"],
            "bill_id": record["bill_id"],
            "line_count": len(record["lines"]),
            "billed_cents": billed,
            "expected_cents": expected,
            "variance_cents": billed - expected,
            "lines_by_status": by_status,
            "method": RECONCILIATION_METHOD,
            "derived": True,
            "stored": False,
        }

    # -- budget forecasts, recorded verbatim (idx 474, built) ---------------
    # The entry's own text binds the form: projections are
    # recorded verbatim, never computed.

    def create_forecast(self, actor, budget_id, projected_obligated_cents,
                        projected_spent_cents, basis):
        """Record a caller-supplied projection for a budget.

        Both projected amounts are recorded verbatim, exactly as
        supplied, with the caller's stated basis. This build
        computes no projection; validation is the money boundary
        only.
        """
        budget = self.store._budget(budget_id)
        self._scoped(actor, budget["org_id"], "enter")
        _money(projected_obligated_cents, "projected_obligated_cents")
        _money(projected_spent_cents, "projected_spent_cents")
        _text(basis, "basis")
        with self._lock:
            record = {
                "id": self._mint("for-"),
                "org_id": budget["org_id"],
                "budget_id": budget_id,
                "period": budget["period"],
                "projected_obligated_cents": projected_obligated_cents,
                "projected_spent_cents": projected_spent_cents,
                "basis": basis,
                "method": FORECAST_METHOD,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._forecasts[record["id"]] = record
        self._record(actor, "forecast_create", record["id"],
                     {"budget_id": budget_id})
        return dict(record)

    def get_forecast(self, actor, forecast_id):
        return dict(self._get_scoped(actor, self._forecasts, forecast_id,
                                     "forecast"))

    def list_forecasts(self, actor, org_id):
        return self._list_scoped(actor, self._forecasts, org_id)

    def forecast_view(self, actor, forecast_id):
        """The recorded projection beside the budget's derived actuals.

        The projection is echoed verbatim (source labeled
        ``recorded_verbatim``); obligated / spent / available
        are the core budget view's read-time derivations
        (source labeled ``derived_from_obligations``). The
        projected available is arithmetic over the *recorded*
        projection and the budget amount -- a derivation over
        held records, not a computed forecast.
        """
        record = self._get_scoped(actor, self._forecasts, forecast_id,
                                  "forecast")
        budget = self.store.get_budget(actor, record["budget_id"])
        projected_available = (
            budget["budget_cents"]
            - record["projected_obligated_cents"]
            - record["projected_spent_cents"])
        return {
            "forecast_id": record["id"],
            "budget_id": record["budget_id"],
            "period": record["period"],
            "budget_cents": budget["budget_cents"],
            "projected_obligated_cents": record["projected_obligated_cents"],
            "projected_spent_cents": record["projected_spent_cents"],
            "projected_available_cents": projected_available,
            "projection_source": FORECAST_METHOD,
            "obligated_cents": budget["obligated_cents"],
            "spent_cents": budget["spent_cents"],
            "available_cents": budget["available_cents"],
            "actuals_source": "derived_from_obligations",
            "computed_here": False,
            "derived": True,
            "stored": False,
        }

    # -- analytics beyond registry summaries (idx 475, built) ---------------

    def create_analytic(self, actor, org_id, name, kind):
        """Register an analytic definition (a named derivation)."""
        self._scoped(actor, org_id, "record")
        _text(name, "name")
        _choice(kind, ANALYTIC_KINDS, "kind")
        with self._lock:
            record = {
                "id": self._mint("ana-"),
                "org_id": org_id,
                "name": name,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._analytics[record["id"]] = record
        self._record(actor, "analytic_create", record["id"], {"kind": kind})
        return dict(record)

    def get_analytic(self, actor, analytic_id):
        return dict(self._get_scoped(actor, self._analytics, analytic_id,
                                     "analytic"))

    def list_analytics(self, actor, org_id):
        return self._list_scoped(actor, self._analytics, org_id)

    def analytic_view(self, actor, analytic_id):
        """Compute an analytic's derivation over core records, at read.

        Counts and money sums only -- never a score. The view is
        computed from the core store's current records on every
        call and stored nowhere.
        """
        record = self._get_scoped(actor, self._analytics, analytic_id,
                                  "analytic")
        org_id = record["org_id"]
        if record["kind"] == "spending_by_period":
            periods = {}
            for bill in self.store.list_bills(actor, org_id):
                row = periods.setdefault(
                    bill["period"], {"period": bill["period"], "bills": 0,
                                     "stated_cents": 0})
                row["bills"] += 1
                row["stated_cents"] += bill["stated_cents"]
            rows = [periods[key] for key in sorted(periods)]
        elif record["kind"] == "recurring_by_kind":
            kinds = {}
            for item in self.store.list_inventory(actor, org_id):
                if item["provisioning_state"] == "disconnected":
                    continue
                row = kinds.setdefault(
                    item["service_kind"],
                    {"service_kind": item["service_kind"], "items": 0,
                     "monthly_recurring_cents": 0})
                row["items"] += 1
                row["monthly_recurring_cents"] += item["monthly_recurring_cents"]
            rows = [kinds[key] for key in sorted(kinds)]
        else:  # open_dispute_exposure
            by_status = {}
            open_cents = 0
            for bill in self.store.list_bills(actor, org_id):
                for dispute in self.store.list_disputes(actor, bill["id"]):
                    by_status[dispute["status"]] = \
                        by_status.get(dispute["status"], 0) + 1
                    if dispute["status"] != "resolved":
                        open_cents += dispute["amount_cents"]
            rows = [{"disputes_by_status": by_status,
                     "open_disputed_cents": open_cents}]
        return {
            "analytic_id": record["id"],
            "kind": record["kind"],
            "rows": rows,
            "method": ANALYTIC_METHOD,
            "derived": True,
            "stored": False,
        }

    # -- report generation (idx 476, built) ----------------------------------
    # A report run is an event record of deterministic
    # derivations over the registry at run time -- the same
    # shape as a core validation run. Definitions are data.

    def create_report_definition(self, actor, org_id, name, sections):
        """Register a report definition: a name and its sections."""
        self._scoped(actor, org_id, "record")
        _text(name, "name")
        sections = _text_list(sections, "sections")
        for section in sections:
            _choice(section, REPORT_SECTIONS, "section")
        with self._lock:
            record = {
                "id": self._mint("rep-"),
                "org_id": org_id,
                "name": name,
                "sections": sections,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_definitions[record["id"]] = record
        self._record(actor, "report_definition_create", record["id"],
                     {"name": name})
        view = dict(record)
        view["sections"] = list(record["sections"])
        return view

    def get_report_definition(self, actor, definition_id):
        record = self._get_scoped(actor, self._report_definitions,
                                  definition_id, "report definition")
        view = dict(record)
        view["sections"] = list(record["sections"])
        return view

    def list_report_definitions(self, actor, org_id):
        return [self.get_report_definition(actor, r["id"])
                for r in self._list_scoped(actor, self._report_definitions,
                                           org_id)]

    def generate_report(self, actor, definition_id):
        """Generate a report run from a definition, over core records.

        The run record holds the figures derived at generation
        time for the definition's sections, computed from the
        core organization summary. A later records change does
        not rewrite an earlier run.
        """
        definition = self._fetch(self._report_definitions, definition_id,
                                 "report definition")
        self._scoped(actor, definition["org_id"], "record")
        summary = self.store.organization_summary(actor, definition["org_id"])
        figures = {}
        for section in definition["sections"]:
            if section == "inventory":
                figures["inventory"] = {
                    "by_kind": summary["inventory_by_kind"],
                    "by_state": summary["inventory_by_state"],
                }
            elif section == "orders":
                figures["orders"] = {"by_status": summary["orders_by_status"]}
            elif section == "bills":
                figures["bills"] = {
                    "count": summary["bills"],
                    "stated_cents": summary["bills_stated_cents"],
                    "validations": summary["validations"],
                    "disputes_by_status": summary["disputes_by_status"],
                    "open_disputed_cents": summary["open_disputed_cents"],
                }
            elif section == "budgets":
                figures["budgets"] = {
                    "count": len(summary["budgets"]),
                    "available_cents": summary["budget_available_cents"],
                }
            elif section == "alerts":
                figures["alerts"] = {
                    "unacknowledged": summary["alerts_unacknowledged"],
                }
            elif section == "chargebacks":
                figures["chargebacks"] = {"cents": summary["chargebacks_cents"]}
        with self._lock:
            record = {
                "id": self._mint("rpr-"),
                "org_id": definition["org_id"],
                "definition_id": definition_id,
                "sections": list(definition["sections"]),
                "figures": figures,
                "method": ANALYTIC_METHOD,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_runs[record["id"]] = record
        self._record(actor, "report_generate", record["id"],
                     {"definition_id": definition_id})
        return dict(record)

    def get_report_run(self, actor, run_id):
        return dict(self._get_scoped(actor, self._report_runs, run_id,
                                     "report run"))

    def list_report_runs(self, actor, org_id):
        return self._list_scoped(actor, self._report_runs, org_id)

    # -- alert delivery transport reference (idx 477, stub-engine) ----------

    def record_alert_delivery(self, actor, alert_id, channel):
        """Record an alert delivery as a reference transport receipt.

        Alerts in the core are records; delivery belongs to an
        external transport. This receipt states that a delivery
        was handed to that transport -- nothing is delivered
        here, and the core alert record is unchanged.
        """
        alert = self.store._alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("no such alert: %r" % (alert_id,))
        self._scoped(actor, alert["org_id"], "record")
        _choice(channel, DELIVERY_CHANNELS, "channel")
        with self._lock:
            record = {
                "id": self._mint("dlv-"),
                "org_id": alert["org_id"],
                "alert_id": alert_id,
                "channel": channel,
                "reference_stub": True,
                "reference_transport": True,
                "status": "recorded_reference_only",
                "delivered": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deliveries[record["id"]] = record
        self._record(actor, "alert_delivery_record", record["id"],
                     {"alert_id": alert_id, "channel": channel})
        return dict(record)

    def get_alert_delivery(self, actor, delivery_id):
        return dict(self._get_scoped(actor, self._deliveries, delivery_id,
                                     "alert delivery record"))

    def list_alert_deliveries(self, actor, org_id):
        return self._list_scoped(actor, self._deliveries, org_id)

    # -- web portal / single-pane configuration (idx 478, built) ------------
    # The substrate the single-pane view runs on is Core; the
    # portal itself is configuration records here. Nothing is
    # rendered or served by this build.

    def create_portal_page(self, actor, org_id, page_ref, title, sections):
        """Record a portal page configuration as data."""
        self._scoped(actor, org_id, "record")
        _ref(page_ref, "page_ref")
        _text(title, "title")
        sections = _text_list(sections, "sections")
        with self._lock:
            for existing in self._portal_pages.values():
                if existing["org_id"] == org_id \
                        and existing["page_ref"] == page_ref:
                    raise ValidationError(
                        "portal page ref already exists in this "
                        "organization: %r" % (page_ref,))
            record = {
                "id": self._mint("por-"),
                "org_id": org_id,
                "page_ref": page_ref,
                "title": title,
                "sections": sections,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portal_pages[record["id"]] = record
        self._record(actor, "portal_page_create", record["id"],
                     {"page_ref": page_ref})
        view = dict(record)
        view["sections"] = list(record["sections"])
        return view

    def get_portal_page(self, actor, page_id):
        record = self._get_scoped(actor, self._portal_pages, page_id,
                                  "portal page")
        view = dict(record)
        view["sections"] = list(record["sections"])
        return view

    def list_portal_pages(self, actor, org_id):
        return [self.get_portal_page(actor, r["id"])
                for r in self._list_scoped(actor, self._portal_pages, org_id)]

    def portal_view(self, actor, org_id):
        """The single-pane configuration for one organization.

        The recorded page configurations, as data, plus the core
        summary counts the view would present. No page is
        rendered or served; ``served_here`` is False.
        """
        self._scoped(actor, org_id, "read")
        summary = self.store.organization_summary(actor, org_id)
        return {
            "org_id": org_id,
            "pages": self.list_portal_pages(actor, org_id),
            "summary": {
                "inventory_by_state": summary["inventory_by_state"],
                "orders_by_status": summary["orders_by_status"],
                "budget_available_cents": summary["budget_available_cents"],
                "alerts_unacknowledged": summary["alerts_unacknowledged"],
            },
            "served_here": False,
            "derived": True,
            "stored": False,
        }

    # -- Managed Mobility services operations (idx 479, built) --------------
    # The human/service operations the fork's MM offering wraps
    # around the system, in their records form: work records
    # with a recorded lifecycle, and derived counts.

    def create_service_operation(self, actor, org_id, kind, subject_ref,
                                 detail):
        """Open a managed-services operation work record."""
        self._scoped(actor, org_id, "enter")
        _choice(kind, OPERATION_KINDS, "kind")
        _ref(subject_ref, "subject_ref")
        _text(detail, "detail")
        with self._lock:
            record = {
                "id": self._mint("ops-"),
                "org_id": org_id,
                "kind": kind,
                "subject_ref": subject_ref,
                "detail": detail,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "closed_utc": None,
            }
            self._operations[record["id"]] = record
        self._record(actor, "service_operation_create", record["id"],
                     {"kind": kind})
        return dict(record)

    def set_service_operation_status(self, actor, operation_id, status):
        """Move an operation through its recorded lifecycle."""
        operation = self._fetch(self._operations, operation_id,
                                "service operation")
        self._scoped(actor, operation["org_id"], "record")
        if status not in OPERATION_TRANSITIONS[operation["status"]]:
            raise ValidationError(
                "operation cannot move from %r to %r"
                % (operation["status"], status))
        with self._lock:
            operation["status"] = status
            if status in ("completed", "cancelled"):
                operation["closed_utc"] = _utc_now()
        self._record(actor, "service_operation_status", operation_id,
                     {"status": status})
        return dict(operation)

    def get_service_operation(self, actor, operation_id):
        return dict(self._get_scoped(actor, self._operations, operation_id,
                                     "service operation"))

    def list_service_operations(self, actor, org_id):
        return self._list_scoped(actor, self._operations, org_id)

    def operations_summary(self, actor, org_id):
        """Counts of operation records by kind and status, at read."""
        self._scoped(actor, org_id, "read")
        by_kind = {kind: 0 for kind in OPERATION_KINDS}
        by_status = {status: 0 for status in OPERATION_TRANSITIONS}
        for operation in self._operations.values():
            if operation["org_id"] == org_id:
                by_kind[operation["kind"]] += 1
                by_status[operation["status"]] += 1
        return {
            "org_id": org_id,
            "operations_by_kind": by_kind,
            "operations_by_status": by_status,
            "method": ANALYTIC_METHOD,
            "derived": True,
            "stored": False,
        }

    # -- device enrollment & provisioning reference (idx 480, stub-engine) --
    # Devices are held by opaque caller-supplied references
    # only. No identifier field exists on this record, by the
    # founding invariant (ADDENDUM.md section 3).

    def record_enrollment(self, actor, org_id, device_ref, program_label):
        """Record a device enrollment as a reference record.

        Provisioning happens on an external plane; this record
        states that an enrollment was recorded for an opaque
        device reference under a program label. Nothing is
        provisioned here and no core record changes.
        """
        self._scoped(actor, org_id, "record")
        _ref(device_ref, "device_ref")
        _text(program_label, "program_label")
        with self._lock:
            record = {
                "id": self._mint("enr-"),
                "org_id": org_id,
                "device_ref": device_ref,
                "program_label": program_label,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "provisioned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrollments[record["id"]] = record
        self._record(actor, "enrollment_record", record["id"],
                     {"device_ref": device_ref})
        return dict(record)

    def get_enrollment(self, actor, enrollment_id):
        return dict(self._get_scoped(actor, self._enrollments, enrollment_id,
                                     "enrollment record"))

    def list_enrollments(self, actor, org_id):
        return self._list_scoped(actor, self._enrollments, org_id)

    # -- device command plane, records form (idx 481, built) -----------------
    # Command records with a separation-of-duties confirmation
    # seam. executed_here is False on every record: this build
    # issues no command to any device.

    def _check_command_confirmer_not_requester(self, command, actor):
        """Separation of duties for device commands.

        The actor confirming a device command is never the actor
        who requested it. This seam is the batch's fresh
        negative-control target (see tests/README.md).
        """
        if actor_name(actor) == command["requested_by"]:
            raise PermissionDenied(
                "the confirmer of a device command is never its requester")

    def request_device_command(self, actor, org_id, device_ref, command_kind,
                               reason):
        """Record a device command request (wipe / lock / unlock).

        A record only: requesting a command here sends nothing
        to any device.
        """
        self._scoped(actor, org_id, "enter")
        _ref(device_ref, "device_ref")
        _choice(command_kind, COMMAND_KINDS, "command_kind")
        _text(reason, "reason")
        with self._lock:
            record = {
                "id": self._mint("cmd-"),
                "org_id": org_id,
                "device_ref": device_ref,
                "command_kind": command_kind,
                "reason": reason,
                "status": "requested",
                "requested_by": actor_name(actor),
                "confirmed_by": None,
                "reported_outcome": None,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._commands[record["id"]] = record
        self._record(actor, "device_command_request", record["id"],
                     {"command_kind": command_kind})
        return dict(record)

    def confirm_device_command(self, actor, command_id):
        """Confirm a requested command. Never the requester (AC-5)."""
        command = self._fetch(self._commands, command_id, "device command")
        self._scoped(actor, command["org_id"], "decide")
        if command["status"] != "requested":
            raise ValidationError(
                "command is not awaiting confirmation: %r" % (command["status"],))
        self._check_command_confirmer_not_requester(command, actor)
        with self._lock:
            command["status"] = "confirmed"
            command["confirmed_by"] = actor_name(actor)
        self._record(actor, "device_command_confirm", command_id, {})
        return dict(command)

    def record_command_outcome(self, actor, command_id, outcome):
        """Record the outcome reported by the external plane.

        The outcome is a label as reported; recording it changes
        no device. ``executed_here`` stays False: any execution
        happened elsewhere.
        """
        command = self._fetch(self._commands, command_id, "device command")
        self._scoped(actor, command["org_id"], "record")
        _choice(outcome, COMMAND_OUTCOMES, "outcome")
        if command["status"] != "confirmed":
            raise ValidationError(
                "only a confirmed command can record an outcome: %r"
                % (command["status"],))
        with self._lock:
            command["status"] = "reported_closed"
            command["reported_outcome"] = outcome
        self._record(actor, "device_command_outcome", command_id,
                     {"outcome": outcome})
        return dict(command)

    def get_device_command(self, actor, command_id):
        return dict(self._get_scoped(actor, self._commands, command_id,
                                     "device command"))

    def list_device_commands(self, actor, org_id):
        return self._list_scoped(actor, self._commands, org_id)

    # -- device policy & compliance records (idx 482, built) -----------------
    # Policies are recorded requirement labels; compliance
    # checks are results as reported; compliance state is
    # derived at read. Nothing is enforced on any device.

    def create_device_policy(self, actor, org_id, policy_ref, name,
                             requirements):
        """Record a device policy: a name and requirement labels."""
        self._scoped(actor, org_id, "enter")
        _ref(policy_ref, "policy_ref")
        _text(name, "name")
        requirements = _text_list(requirements, "requirements")
        with self._lock:
            for existing in self._policies.values():
                if existing["org_id"] == org_id \
                        and existing["policy_ref"] == policy_ref:
                    raise ValidationError(
                        "policy ref already exists in this organization: %r"
                        % (policy_ref,))
            record = {
                "id": self._mint("pol-"),
                "org_id": org_id,
                "policy_ref": policy_ref,
                "name": name,
                "requirements": requirements,
                "enforced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policies[record["id"]] = record
        self._record(actor, "device_policy_create", record["id"],
                     {"policy_ref": policy_ref})
        view = dict(record)
        view["requirements"] = list(record["requirements"])
        return view

    def get_device_policy(self, actor, policy_id):
        record = self._get_scoped(actor, self._policies, policy_id,
                                  "device policy")
        view = dict(record)
        view["requirements"] = list(record["requirements"])
        return view

    def list_device_policies(self, actor, org_id):
        return [self.get_device_policy(actor, r["id"])
                for r in self._list_scoped(actor, self._policies, org_id)]

    def record_compliance_check(self, actor, policy_id, device_ref, results):
        """Record a compliance check's results, as reported.

        ``results`` maps the policy's requirement labels to the
        reported ``pass`` / ``fail`` labels. Recording a result
        enforces nothing; it is the reported state of one check.
        """
        policy = self._fetch(self._policies, policy_id, "device policy")
        self._scoped(actor, policy["org_id"], "record")
        _ref(device_ref, "device_ref")
        if not isinstance(results, dict) or not results:
            raise ValidationError("results must be a non-empty object")
        cleaned = {}
        for label, outcome in results.items():
            if label not in policy["requirements"]:
                raise ValidationError(
                    "result label is not a requirement of this policy: %r"
                    % (label,))
            _choice(outcome, ("pass", "fail"), "result")
            cleaned[label] = outcome
        with self._lock:
            record = {
                "id": self._mint("chk-"),
                "org_id": policy["org_id"],
                "policy_id": policy_id,
                "device_ref": device_ref,
                "results": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._compliance_checks[record["id"]] = record
        self._record(actor, "compliance_check_record", record["id"],
                     {"policy_id": policy_id, "device_ref": device_ref})
        view = dict(record)
        view["results"] = dict(record["results"])
        return view

    def list_compliance_checks(self, actor, org_id):
        result = []
        for record in self._list_scoped(actor, self._compliance_checks, org_id):
            view = dict(record)
            view["results"] = dict(record["results"])
            result.append(view)
        return result

    def compliance_view(self, actor, policy_id, device_ref):
        """Derive one device's compliance state under one policy.

        From the recorded checks only: no checks reads
        ``unknown``; the latest check decides -- every recorded
        result a ``pass`` reads ``compliant``, any ``fail``
        reads ``non_compliant``. Derived at read, stored
        nowhere; nothing is enforced here.
        """
        policy = self._get_scoped(actor, self._policies, policy_id,
                                  "device policy")
        _ref(device_ref, "device_ref")
        checks = [c for c in self._compliance_checks.values()
                  if c["policy_id"] == policy_id
                  and c["device_ref"] == device_ref]
        if not checks:
            state = "unknown"
            latest = None
        else:
            latest = checks[-1]
            state = ("compliant"
                     if all(v == "pass" for v in latest["results"].values())
                     else "non_compliant")
        return {
            "policy_id": policy["id"],
            "device_ref": device_ref,
            "state": state,
            "checks": len(checks),
            "latest_check_id": latest["id"] if latest else None,
            "method": COMPLIANCE_METHOD,
            "enforced_here": False,
            "derived": True,
            "stored": False,
        }

    # -- mobile application management records (idx 483, built) --------------
    # Catalog and distribution records. Nothing is distributed
    # to, installed on, or wrapped around any device here.

    def create_app_record(self, actor, org_id, app_ref, label, version_label):
        """Record an application in the organization's catalog."""
        self._scoped(actor, org_id, "enter")
        _ref(app_ref, "app_ref")
        _text(label, "label")
        _text(version_label, "version_label")
        with self._lock:
            for existing in self._apps.values():
                if existing["org_id"] == org_id \
                        and existing["app_ref"] == app_ref:
                    raise ValidationError(
                        "app ref already exists in this organization: %r"
                        % (app_ref,))
            record = {
                "id": self._mint("app-"),
                "org_id": org_id,
                "app_ref": app_ref,
                "label": label,
                "version_label": version_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._apps[record["id"]] = record
        self._record(actor, "app_create", record["id"], {"app_ref": app_ref})
        return dict(record)

    def get_app_record(self, actor, app_id):
        return dict(self._get_scoped(actor, self._apps, app_id, "app record"))

    def list_app_records(self, actor, org_id):
        return self._list_scoped(actor, self._apps, org_id)

    def record_app_distribution(self, actor, app_id, device_ref, channel_label):
        """Record an app distribution assignment, as data.

        The assignment names an opaque device reference and a
        recorded channel label; nothing is delivered or
        installed here.
        """
        app = self._fetch(self._apps, app_id, "app record")
        self._scoped(actor, app["org_id"], "record")
        _ref(device_ref, "device_ref")
        _text(channel_label, "channel_label")
        with self._lock:
            record = {
                "id": self._mint("dst-"),
                "org_id": app["org_id"],
                "app_id": app_id,
                "device_ref": device_ref,
                "channel_label": channel_label,
                "status": "recorded",
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._app_distributions[record["id"]] = record
        self._record(actor, "app_distribution_record", record["id"],
                     {"app_id": app_id, "device_ref": device_ref})
        return dict(record)

    def list_app_distributions(self, actor, org_id):
        return self._list_scoped(actor, self._app_distributions, org_id)

    def app_summary(self, actor, org_id):
        """Counts over the app catalog and distribution records."""
        self._scoped(actor, org_id, "read")
        distributions = [d for d in self._app_distributions.values()
                         if d["org_id"] == org_id]
        return {
            "org_id": org_id,
            "apps": sum(1 for a in self._apps.values()
                        if a["org_id"] == org_id),
            "distributions": len(distributions),
            "devices_with_distributions": len(
                {d["device_ref"] for d in distributions}),
            "method": ANALYTIC_METHOD,
            "derived": True,
            "stored": False,
        }

    # -- device location & tracking service records (idx 484, built) ----------
    # Tracking-service configuration and status records ONLY.
    # This build holds no location data: no field on any record
    # here can hold a coordinate, an address, or a place label.
    # A device's current state derives at read from its recorded
    # status reports (service-state labels, as reported).

    def create_tracking_record(self, actor, org_id, device_ref, service_label):
        """Open a tracking-service record for an opaque device ref."""
        self._scoped(actor, org_id, "record")
        _ref(device_ref, "device_ref")
        _text(service_label, "service_label")
        with self._lock:
            for existing in self._tracking.values():
                if existing["org_id"] == org_id \
                        and existing["device_ref"] == device_ref:
                    raise ValidationError(
                        "a tracking record already exists for this device "
                        "reference in this organization: %r" % (device_ref,))
            record = {
                "id": self._mint("trk-"),
                "org_id": org_id,
                "device_ref": device_ref,
                "service_label": service_label,
                "location_data_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._tracking[record["id"]] = record
        self._record(actor, "tracking_record_create", record["id"],
                     {"device_ref": device_ref})
        return dict(record)

    def get_tracking_record(self, actor, tracking_id):
        return dict(self._get_scoped(actor, self._tracking, tracking_id,
                                     "tracking record"))

    def list_tracking_records(self, actor, org_id):
        return self._list_scoped(actor, self._tracking, org_id)

    def record_tracking_status(self, actor, tracking_id, reported_state):
        """Record a tracking service-state label, as reported.

        The label is a service state (active / inactive /
        suspended) -- never a place. Recording it locates
        nothing.
        """
        tracking = self._fetch(self._tracking, tracking_id, "tracking record")
        self._scoped(actor, tracking["org_id"], "record")
        _choice(reported_state, TRACKING_STATES, "reported_state")
        with self._lock:
            record = {
                "id": self._mint("tsr-"),
                "org_id": tracking["org_id"],
                "tracking_id": tracking_id,
                "reported_state": reported_state,
                "location_data_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._tracking_reports[record["id"]] = record
        self._record(actor, "tracking_status_record", record["id"],
                     {"tracking_id": tracking_id,
                      "reported_state": reported_state})
        return dict(record)

    def list_tracking_reports(self, actor, org_id):
        return self._list_scoped(actor, self._tracking_reports, org_id)

    def tracking_view(self, actor, tracking_id):
        """Derive a tracking record's current service state, at read.

        The current state is the latest recorded status report's
        label, or ``unreported`` when none exists. No location
        data exists to derive from; ``location_data_held`` is
        False.
        """
        record = self._get_scoped(actor, self._tracking, tracking_id,
                                  "tracking record")
        reports = [r for r in self._tracking_reports.values()
                   if r["tracking_id"] == tracking_id]
        return {
            "tracking_id": record["id"],
            "device_ref": record["device_ref"],
            "service_label": record["service_label"],
            "current_state": reports[-1]["reported_state"] if reports
            else "unreported",
            "reports": len(reports),
            "location_data_held": False,
            "method": TRACKING_METHOD,
            "derived": True,
            "stored": False,
        }
