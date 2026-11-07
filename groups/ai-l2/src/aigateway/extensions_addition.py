"""Final GAPS batch additions for Artificial Intelligence (AI) L2.

Second batch unit in this group directory: clean-room,
standard-library-only records extensions for the 3 gap entries the
remainder addition fork (Secunetics / Gobo, FR2214346691)
registered from its own surface (see ``ADDENDUM.md`` section 5 and
``BATCH-ADDITION.md`` in the group directory). The first batch
unit's module is ``extensions.py``; this module is separate and
every existing module, that one included, is untouched.

The newcomer is an IT-infrastructure automation product filed
into this category on its own AI wording; the three entries are
its fork excess beyond the group's taxonomy. What this substrate
-- the platform layer around models, per UNION-SPEC.md -- can
honestly hold for each:

- **Infrastructure Digital Twin & performance management**
  (idx 649, built): twin profile records and performance
  observation records whose figures are the twin operator's
  reports, held verbatim and never aggregated into a computed
  figure; views derive counts, label sets, and the latest report
  at read. The twin itself -- a live mirror of an infrastructure
  ecosystem, continuously measuring it -- is not operated here
  and is stated absent on every record.
- **Service transition management** (idx 650, built): transition
  plan records with steps held as data, step-status records,
  configuration-change records (recorded, never applied), and
  capacity-report records whose figures are reported verbatim
  and never computed here. Plan views derive the per-step
  current status at read; the stored plan carries no status.
- **EIS service management suite** (idx 651, reference):
  service-inventory records with lifecycle status records, and
  SLA / CLIN / invoice / reconciliation / dispute / credit
  records -- all labeled reference implementations
  (``reference_stub: True``). The suite is a telecom-contract
  administration vertical; amounts, determinations, and
  recoveries are the suite operator's, named here only by opaque
  references and verbatim reported labels.

Design, following the group's doctrines and the first unit's
forms:

- This module is a second wrapper around
  :class:`AIGatewayStore`; the core modules are untouched
  (byte-identical). Model existence is always checked through
  the core store's public API, never re-implemented.
- **No learned model runs here and no content is held.** No
  parameter anywhere on this surface accepts telemetry payloads,
  configuration bodies, invoice documents, or any other content;
  subjects, services, lines, and invoices are named only by
  opaque ``*_ref`` strings, and reported figures are verbatim
  strings, never parsed, summed, averaged, or projected.
- RBAC goes through :mod:`aigateway.access` exactly as the core
  and the first extension module enforce it: each operation maps
  onto an existing core action (profile/plan/service
  registrations -> ``registry_write``; observation, status,
  change, report, and suite records -> ``invoke``; views and the
  summary -> ``read``), checked *before* any state change or id
  allocation for User-like actors. Denied attempts are recorded
  on the core audit log under this unit's own ``exta_`` action
  prefix (distinct from the first unit's ``ext_``), and every
  successful mutation as ``exta_<action>``.
- Derived values are derived at read and never stored: the
  twin view's counts and latest report, the transition view's
  per-step current status, the EIS view's counts and current
  lifecycle status, and the addition summary. Stored records
  carry no derived key; tests pin that.
- The latest-record rule lives at a single named seam
  (``_latest_record``): the current state of a twin, a plan
  step, or a service is the *last* record reported for it. The
  seam is this unit's fresh negative control.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


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


def _string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


class AIGatewayExtensionsAddition:
    """Second GAPS-batch extension surface over a core store."""

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

    def _guard_read(self, actor, core_action, audit_action, target=None):
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _core_model(self, name, version=None):
        return self.store.get_model(name, None, version)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    @staticmethod
    def _latest_record(records):
        """The latest-record seam: current state is the LAST record.

        Every "current" derivation on this surface -- a twin's
        latest performance report, a plan step's current status,
        a service's current lifecycle status -- takes the last
        record in creation order. This is the single derivation
        point for currency; this unit's fresh negative control
        mutates it (reading the earliest record instead must
        misstate every current-state view and fail the suite).
        """
        return records[-1] if records else None

    # -- Infrastructure Digital Twin & performance mgmt (built) -----
    # Gobo's IDT surface (ADDENDUM section 5): deep, continuous
    # visibility into IT ecosystems and real-time performance
    # tracking. What a records substrate honestly holds is the
    # registry side: a twin profile for an infrastructure scope
    # (named only by an opaque scope_ref) and performance
    # observation records whose metric labels and figures are the
    # twin operator's reports, held verbatim. The twin itself --
    # a live, continuously measuring mirror of the ecosystem --
    # is not operated here: nothing is mirrored, probed, or
    # measured (twin_operated_here / measured_here False on every
    # record), and no reported figure is ever aggregated into a
    # computed one.

    def register_twin(self, name, scope_ref, actor, model_name=None):
        """Register an infrastructure digital twin profile.

        Action: registry_write. Ids: ``idt-``. ``scope_ref`` is
        the operator's opaque reference for the infrastructure
        scope the twin mirrors; an optional ``model_name`` binds
        the twin to a registered core model. The twin is not
        operated here.
        """
        self._guard(actor, "registry_write", "exta_twin_register")
        _non_empty(name, "twin name")
        _non_empty(scope_ref, "scope_ref")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "twin", "idt",
                {"name": name, "scope_ref": scope_ref, "model": model,
                 "twin_operated_here": False, "measured_here": False,
                 "state": "recorded_profile"},
                actor, "exta_twin_register")

    def record_performance_observation(self, twin_id, metric_label,
                                       reported_value, actor):
        """Record a twin's performance report, verbatim as reported.

        Action: invoke. Ids: ``ipo-``. ``metric_label`` and
        ``reported_value`` are the twin operator's own report,
        stored verbatim as strings; the figure is never parsed,
        aggregated, or recomputed here (``computed_here``
        False).
        """
        self._guard(actor, "invoke", "exta_performance_observation_record",
                    twin_id)
        _non_empty(metric_label, "metric_label")
        _non_empty(reported_value, "reported_value")
        with self._lock:
            self._get("twin", twin_id)
            return self._create(
                "performance_observation", "ipo",
                {"twin_id": twin_id, "metric_label": metric_label,
                 "reported_value": reported_value,
                 "measured_here": False, "computed_here": False},
                actor, "exta_performance_observation_record")

    def get_twin(self, twin_id, actor=None):
        """Return one twin profile record. Action: read."""
        self._guard_read(actor, "read", "exta_twin_read", twin_id)
        return self._fetch("twin", twin_id)

    def list_twins(self, actor=None):
        """Return twin profile records. Action: read."""
        self._guard_read(actor, "read", "exta_twin_read")
        return self._list("twin")

    def list_performance_observations(self, twin_id=None, actor=None):
        """Return performance observation records. Action: read."""
        self._guard_read(actor, "read",
                         "exta_performance_observation_read", twin_id)
        if twin_id is not None:
            self._get("twin", twin_id)
        return self._list("performance_observation", twin_id=twin_id)

    def twin_view(self, twin_id, actor=None):
        """A twin profile plus derivations over its own reports.

        Action: read. The observation count, the distinct metric
        labels, and the latest report (via the latest-record
        seam) are derived at read from the twin's own observation
        records; the stored profile carries no totals and no
        latest-report key.
        """
        self._guard_read(actor, "read", "exta_twin_read", twin_id)
        with self._lock:
            profile = self._fetch("twin", twin_id)
            observations = self._list("performance_observation",
                                      twin_id=twin_id)
            latest = self._latest_record(observations)
            view = dict(profile)
            view["observation_total"] = len(observations)
            view["metric_labels"] = sorted(
                {o["metric_label"] for o in observations})
            view["latest_observation"] = (
                {"metric_label": latest["metric_label"],
                 "reported_value": latest["reported_value"]}
                if latest is not None else None)
            view["derived"] = True
            return view

    # -- Service transition management (built) -----------------------
    # Migration planning and tracking (the addendum's example is
    # the IPv6 transition), with automated configuration
    # management and capacity planning as the fork groups them.
    # Planning and tracking are genuinely records-shaped: plan
    # records whose steps are held as data, step-status records
    # reported against those steps, and plan views whose per-step
    # current status derives at read. The execution halves are
    # stated absent: a configuration change is recorded, never
    # applied (applied_here False), and a capacity figure is the
    # planner's report held verbatim, never computed here
    # (computed_here False).

    def create_transition_plan(self, name, actor, subject_ref=None,
                               steps=None, model_name=None):
        """Record a service transition plan as data.

        Action: registry_write. Ids: ``stp-``. ``steps`` are step
        labels held verbatim as data; ``subject_ref`` names the
        transitioning service or mandate by opaque reference; an
        optional ``model_name`` binds the plan to a registered
        core model. Nothing is migrated or executed here.
        """
        self._guard(actor, "registry_write", "exta_transition_plan_create")
        _non_empty(name, "plan name")
        _string_or_none(subject_ref, "subject_ref")
        steps = _string_list(steps, "steps")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "transition_plan", "stp",
                {"name": name, "subject_ref": subject_ref,
                 "steps": steps, "model": model,
                 "definition_only": True, "executed_here": False,
                 "state": "recorded_plan"},
                actor, "exta_transition_plan_create")

    def record_transition_step_status(self, plan_id, step_label,
                                      status_label, actor):
        """Record a transition step's reported status.

        Action: invoke. Ids: ``sts-``. When the plan declares
        steps, ``step_label`` must be one of them (a status for
        an undeclared step is refused and consumes no id). The
        status label is the tracker's report, stored verbatim;
        the step itself is not performed here.
        """
        self._guard(actor, "invoke", "exta_transition_step_status_record",
                    plan_id)
        _non_empty(step_label, "step_label")
        _non_empty(status_label, "status_label")
        with self._lock:
            plan = self._get("transition_plan", plan_id)
            if plan["steps"] and step_label not in plan["steps"]:
                raise ValidationError(
                    "step_label %r is not a declared step of plan %r"
                    % (step_label, plan_id))
            return self._create(
                "transition_step_status", "sts",
                {"plan_id": plan_id, "step_label": step_label,
                 "status_label": status_label, "executed_here": False},
                actor, "exta_transition_step_status_record")

    def record_configuration_change(self, plan_id, change_label, actor,
                                    target_ref=None):
        """Record a configuration change under a transition plan.

        Action: invoke. Ids: ``stc-``. The change is recorded as
        reported; it is never applied here (``applied_here``
        False) and no configuration body is accepted by any
        parameter. ``target_ref`` names the affected
        configuration item by opaque reference.
        """
        self._guard(actor, "invoke", "exta_configuration_change_record",
                    plan_id)
        _non_empty(change_label, "change_label")
        _string_or_none(target_ref, "target_ref")
        with self._lock:
            self._get("transition_plan", plan_id)
            return self._create(
                "configuration_change", "stc",
                {"plan_id": plan_id, "change_label": change_label,
                 "target_ref": target_ref, "applied_here": False,
                 "automated_here": False},
                actor, "exta_configuration_change_record")

    def record_capacity_report(self, plan_id, metric_label,
                               reported_value, actor):
        """Record a capacity figure for a plan, verbatim as reported.

        Action: invoke. Ids: ``scp-``. ``reported_value`` is the
        capacity planner's own figure, stored verbatim as a
        string; no capacity is computed, projected, or planned
        here (``computed_here`` False).
        """
        self._guard(actor, "invoke", "exta_capacity_report_record", plan_id)
        _non_empty(metric_label, "metric_label")
        _non_empty(reported_value, "reported_value")
        with self._lock:
            self._get("transition_plan", plan_id)
            return self._create(
                "capacity_report", "scp",
                {"plan_id": plan_id, "metric_label": metric_label,
                 "reported_value": reported_value,
                 "computed_here": False},
                actor, "exta_capacity_report_record")

    def get_transition_plan(self, plan_id, actor=None):
        """Return one transition plan record. Action: read."""
        self._guard_read(actor, "read", "exta_transition_plan_read", plan_id)
        return self._fetch("transition_plan", plan_id)

    def list_transition_plans(self, actor=None):
        """Return transition plan records. Action: read."""
        self._guard_read(actor, "read", "exta_transition_plan_read")
        return self._list("transition_plan")

    def list_transition_step_statuses(self, plan_id=None, actor=None):
        """Return step-status records. Action: read."""
        self._guard_read(actor, "read", "exta_transition_step_status_read",
                         plan_id)
        if plan_id is not None:
            self._get("transition_plan", plan_id)
        return self._list("transition_step_status", plan_id=plan_id)

    def list_configuration_changes(self, plan_id=None, actor=None):
        """Return configuration-change records. Action: read."""
        self._guard_read(actor, "read", "exta_configuration_change_read",
                         plan_id)
        if plan_id is not None:
            self._get("transition_plan", plan_id)
        return self._list("configuration_change", plan_id=plan_id)

    def list_capacity_reports(self, plan_id=None, actor=None):
        """Return capacity-report records. Action: read."""
        self._guard_read(actor, "read", "exta_capacity_report_read", plan_id)
        if plan_id is not None:
            self._get("transition_plan", plan_id)
        return self._list("capacity_report", plan_id=plan_id)

    def transition_plan_view(self, plan_id, actor=None):
        """A plan plus its tracking derivations, at read.

        Action: read. Each declared step's current status is the
        status label of its latest status record (via the
        latest-record seam; a step with no status record reads
        ``None``); configuration-change and capacity-report
        counts derive from the plan's own records. The stored
        plan carries no status and no totals.
        """
        self._guard_read(actor, "read", "exta_transition_plan_read", plan_id)
        with self._lock:
            plan = self._fetch("transition_plan", plan_id)
            statuses = self._list("transition_step_status", plan_id=plan_id)
            by_step = {}
            for record in statuses:
                by_step.setdefault(record["step_label"], []).append(record)
            step_status = {}
            for step in plan["steps"]:
                latest = self._latest_record(by_step.get(step, []))
                step_status[step] = (
                    latest["status_label"] if latest is not None else None)
            view = dict(plan)
            view["step_status"] = step_status
            view["status_records_total"] = len(statuses)
            view["configuration_changes_total"] = len(
                self._list("configuration_change", plan_id=plan_id))
            view["capacity_reports_total"] = len(
                self._list("capacity_report", plan_id=plan_id))
            view["derived"] = True
            return view

    # -- EIS service management suite (reference) --------------------
    # GSA Enterprise Infrastructure Solutions oversight -- a
    # telecom-contract administration vertical (ADDENDUM section
    # 5): monitoring how well providers meet promised service
    # levels, CLIN and invoice management, service inventory
    # lifecycle management, and recovery of provider credits.
    # The suite's determinations are the operator's; what ships
    # is the labeled records form: a service record keyed by an
    # opaque reference, lifecycle status records (current status
    # derived at read), and SLA / line-item / invoice /
    # reconciliation / dispute / credit records whose labels and
    # figures are reported verbatim. Nothing is monitored,
    # reconciled, disputed, or recovered here, and no amount is
    # held in any field shape -- this substrate holds no money.

    def register_eis_service(self, service_ref, actor, provider_label=None):
        """Register an EIS service record by opaque reference.

        Action: registry_write. Ids: ``esi-``.
        ``service_ref`` is the suite operator's opaque service
        reference; ``provider_label`` is the provider's name as
        the operator records it, held verbatim. The service is
        not operated or monitored here.
        """
        self._guard(actor, "registry_write", "exta_eis_service_register")
        _non_empty(service_ref, "service_ref")
        _string_or_none(provider_label, "provider_label")
        with self._lock:
            return self._create(
                "eis_service", "esi",
                {"service_ref": service_ref,
                 "provider_label": provider_label,
                 "reference_stub": True, "operated_here": False,
                 "monitored_here": False, "state": "recorded_reference_only"},
                actor, "exta_eis_service_register")

    def record_eis_lifecycle_status(self, service_id, status_label, actor):
        """Record a service's lifecycle status, verbatim as reported.

        Action: invoke. Ids: ``est-``. The current status is
        derived at read from the latest of these records (via
        the latest-record seam); no lifecycle transition is
        enacted here.
        """
        self._guard(actor, "invoke", "exta_eis_lifecycle_status_record",
                    service_id)
        _non_empty(status_label, "status_label")
        with self._lock:
            self._get("eis_service", service_id)
            return self._create(
                "eis_lifecycle_status", "est",
                {"service_id": service_id, "status_label": status_label,
                 "reference_stub": True, "executed_here": False},
                actor, "exta_eis_lifecycle_status_record")

    def record_sla_report(self, service_id, metric_label, reported_value,
                          actor):
        """Record an SLA measurement report, verbatim as reported.

        Action: invoke. Ids: ``esla-``. ``reported_value`` is the
        monitoring operator's own figure, stored verbatim as a
        string; nothing is monitored or measured here
        (``monitored_here`` / ``computed_here`` False), and no
        attainment is determined.
        """
        self._guard(actor, "invoke", "exta_sla_report_record", service_id)
        _non_empty(metric_label, "metric_label")
        _non_empty(reported_value, "reported_value")
        with self._lock:
            self._get("eis_service", service_id)
            return self._create(
                "sla_report", "esla",
                {"service_id": service_id, "metric_label": metric_label,
                 "reported_value": reported_value,
                 "reference_stub": True, "monitored_here": False,
                 "computed_here": False, "attainment_determined_here": False},
                actor, "exta_sla_report_record")

    def record_clin_line(self, service_id, clin_ref, actor,
                         status_label=None):
        """Record a CLIN line-item record under a service.

        Action: invoke. Ids: ``ecl-``. The line is named only by
        its opaque ``clin_ref``; its reported status label is
        held verbatim. No amount is accepted by any parameter:
        this substrate holds no money.
        """
        self._guard(actor, "invoke", "exta_clin_line_record", service_id)
        _non_empty(clin_ref, "clin_ref")
        _string_or_none(status_label, "status_label")
        with self._lock:
            self._get("eis_service", service_id)
            return self._create(
                "clin_line", "ecl",
                {"service_id": service_id, "clin_ref": clin_ref,
                 "status_label": status_label, "reference_stub": True,
                 "managed_here": False},
                actor, "exta_clin_line_record")

    def record_invoice(self, service_id, invoice_ref, actor,
                       status_label=None):
        """Record an invoice record under a service.

        Action: invoke. Ids: ``einv-``. The invoice is named
        only by its opaque ``invoice_ref`` and its reported
        status label; the invoice document and any amount are
        never held here.
        """
        self._guard(actor, "invoke", "exta_invoice_record", service_id)
        _non_empty(invoice_ref, "invoice_ref")
        _string_or_none(status_label, "status_label")
        with self._lock:
            self._get("eis_service", service_id)
            return self._create(
                "invoice", "einv",
                {"service_id": service_id, "invoice_ref": invoice_ref,
                 "status_label": status_label, "reference_stub": True,
                 "managed_here": False, "paid_here": False},
                actor, "exta_invoice_record")

    def record_reconciliation(self, invoice_id, outcome_label, actor):
        """Record an invoice reconciliation outcome, as reported.

        Action: invoke. Ids: ``erec-``. The outcome label is the
        suite operator's report; no reconciliation is performed
        here (``reconciled_here`` False) and no figures are
        compared or held.
        """
        self._guard(actor, "invoke", "exta_reconciliation_record", invoice_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get("invoice", invoice_id)
            return self._create(
                "reconciliation", "erec",
                {"invoice_id": invoice_id, "outcome_label": outcome_label,
                 "reference_stub": True, "reconciled_here": False},
                actor, "exta_reconciliation_record")

    def record_dispute(self, invoice_id, outcome_label, actor):
        """Record an invoice dispute outcome, as reported.

        Action: invoke. Ids: ``edis-``. The outcome label is the
        dispute process's report; no dispute is conducted or
        resolved here (``resolved_here`` False).
        """
        self._guard(actor, "invoke", "exta_dispute_record", invoice_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get("invoice", invoice_id)
            return self._create(
                "dispute", "edis",
                {"invoice_id": invoice_id, "outcome_label": outcome_label,
                 "reference_stub": True, "resolved_here": False},
                actor, "exta_dispute_record")

    def record_credit_recovery(self, service_id, outcome_label, actor,
                               credit_ref=None):
        """Record a provider credit recovery outcome, as reported.

        Action: invoke. Ids: ``ecr-``. The outcome label is the
        suite operator's report and any credit is named only by
        an opaque ``credit_ref``; nothing is recovered here
        (``recovered_here`` False) and no amount is held.
        """
        self._guard(actor, "invoke", "exta_credit_recovery_record",
                    service_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(credit_ref, "credit_ref")
        with self._lock:
            self._get("eis_service", service_id)
            return self._create(
                "credit_recovery", "ecr",
                {"service_id": service_id, "outcome_label": outcome_label,
                 "credit_ref": credit_ref, "reference_stub": True,
                 "recovered_here": False},
                actor, "exta_credit_recovery_record")

    def get_eis_service(self, service_id, actor=None):
        """Return one EIS service record. Action: read."""
        self._guard_read(actor, "read", "exta_eis_service_read", service_id)
        return self._fetch("eis_service", service_id)

    def list_eis_services(self, actor=None):
        """Return EIS service records. Action: read."""
        self._guard_read(actor, "read", "exta_eis_service_read")
        return self._list("eis_service")

    def list_eis_lifecycle_statuses(self, service_id=None, actor=None):
        """Return service lifecycle status records. Action: read."""
        self._guard_read(actor, "read", "exta_eis_lifecycle_status_read",
                         service_id)
        if service_id is not None:
            self._get("eis_service", service_id)
        return self._list("eis_lifecycle_status", service_id=service_id)

    def list_sla_reports(self, service_id=None, actor=None):
        """Return SLA report records. Action: read."""
        self._guard_read(actor, "read", "exta_sla_report_read", service_id)
        if service_id is not None:
            self._get("eis_service", service_id)
        return self._list("sla_report", service_id=service_id)

    def list_clin_lines(self, service_id=None, actor=None):
        """Return CLIN line-item records. Action: read."""
        self._guard_read(actor, "read", "exta_clin_line_read", service_id)
        if service_id is not None:
            self._get("eis_service", service_id)
        return self._list("clin_line", service_id=service_id)

    def list_invoices(self, service_id=None, actor=None):
        """Return invoice records. Action: read."""
        self._guard_read(actor, "read", "exta_invoice_read", service_id)
        if service_id is not None:
            self._get("eis_service", service_id)
        return self._list("invoice", service_id=service_id)

    def list_reconciliations(self, invoice_id=None, actor=None):
        """Return reconciliation records. Action: read."""
        self._guard_read(actor, "read", "exta_reconciliation_read", invoice_id)
        if invoice_id is not None:
            self._get("invoice", invoice_id)
        return self._list("reconciliation", invoice_id=invoice_id)

    def list_disputes(self, invoice_id=None, actor=None):
        """Return dispute records. Action: read."""
        self._guard_read(actor, "read", "exta_dispute_read", invoice_id)
        if invoice_id is not None:
            self._get("invoice", invoice_id)
        return self._list("dispute", invoice_id=invoice_id)

    def list_credit_recoveries(self, service_id=None, actor=None):
        """Return credit recovery records. Action: read."""
        self._guard_read(actor, "read", "exta_credit_recovery_read",
                         service_id)
        if service_id is not None:
            self._get("eis_service", service_id)
        return self._list("credit_recovery", service_id=service_id)

    def eis_service_view(self, service_id, actor=None):
        """A service record plus counts and current status, at read.

        Action: read. The current lifecycle status is the status
        label of the service's latest lifecycle record (via the
        latest-record seam); the per-kind counts derive from the
        service's own records. The stored service record carries
        no status and no totals. No figure is computed: SLA
        values stay on their own records, verbatim.
        """
        self._guard_read(actor, "read", "exta_eis_service_read", service_id)
        with self._lock:
            service = self._fetch("eis_service", service_id)
            statuses = self._list("eis_lifecycle_status",
                                  service_id=service_id)
            latest = self._latest_record(statuses)
            invoices = self._list("invoice", service_id=service_id)
            invoice_ids = {inv["id"] for inv in invoices}
            view = dict(service)
            view["current_status"] = (
                latest["status_label"] if latest is not None else None)
            view["lifecycle_records_total"] = len(statuses)
            view["sla_reports_total"] = len(
                self._list("sla_report", service_id=service_id))
            view["clin_lines_total"] = len(
                self._list("clin_line", service_id=service_id))
            view["invoices_total"] = len(invoices)
            view["reconciliations_total"] = sum(
                1 for r in self._list("reconciliation")
                if r["invoice_id"] in invoice_ids)
            view["disputes_total"] = sum(
                1 for r in self._list("dispute")
                if r["invoice_id"] in invoice_ids)
            view["credit_recoveries_total"] = len(
                self._list("credit_recovery", service_id=service_id))
            view["derived"] = True
            return view

    # -- Addition summary ----------------------------------------------

    def addition_summary(self, actor=None):
        """Counts of every addition record kind, derived at read.

        Action: read. A census of this unit's surface only --
        counts of records, nothing about any external system.
        """
        self._guard_read(actor, "read", "exta_summary_read")
        with self._lock:
            by_kind = {}
            for kind, _record_id in self._order:
                by_kind[kind] = by_kind.get(kind, 0) + 1
            return {
                "records_total": len(self._order),
                "by_kind": by_kind,
                "derived": True,
            }
