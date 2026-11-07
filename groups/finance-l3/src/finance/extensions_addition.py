"""Final GAPS batch extensions (second unit) for the Finance
L3-adjacent build (Group 42): the remainder-addition section.

Clean-room, standard-library-only records extensions for the 3
open entries the remainder addition (OneStream Cloud - High)
registered in this group's GAPS.md section: the corporate
performance management (CPM) engine, the data integration &
connector surface, and the solution marketplace & application
extensibility (see ``ADDENDUM.md`` section 5 and
``BATCH-ADDITION.md`` in the group directory for the per-entry
disposition). The first batch unit's surface lives in
:mod:`finance.extensions`; this module is the second wrapper and
leaves that module — and every core module — untouched.

Design, following the core's doctrines, the first unit's
conventions, and the Finance L2 addition module's proven forms:

- This module is a wrapper around :class:`FinanceStore`; core
  state is always read through the core store's public API,
  never re-implemented, and no extension operation writes core
  state. Audit actions carry this unit's own ``exta_`` prefix,
  distinct from the first unit's ``ext_``.
- **Money is integer cents, everywhere.** Every ``*_cents``
  field is a Python ``int``; booleans and floats are rejected at
  the boundary, so all arithmetic is exact. Plan line amounts
  are *signed* integer cents — the sign is structural, because
  consolidation eliminations and plan adjustments are negative
  lines by nature; the validation is type-only, never a
  rounding or a conversion.
- **Currency is a label, never converted.** Entities and plans
  carry a ``currency_label`` held as data. Consolidation sums
  are computed **per currency label** by the seam
  :func:`_totals_by_currency` and never across labels: no
  cross-currency sum exists anywhere on this surface, pinned
  by test.
- **Forecasts are recorded, never computed.** A forecast figure
  is the planning system's own figure, stored verbatim as
  reported on a forecast record (``computed_here: False``);
  this surface runs no forecasting model. Consolidation totals,
  by contrast, are exact integer sums over values *recorded on
  this surface*, derived at read and never stored — the same
  posture as Core 7 reporting over the core's own records.
- **The connector family is a labeled reference
  implementation**: every record it creates carries
  ``reference_stub: True`` and ``reference_transport: True``.
  A sync receipt reports what an external connector moved; it
  imports nothing here (``imported_here: False``), pinned by
  test against unchanged core counts.
- **The marketplace is a catalog, not a storefront.** Listing
  and adoption records are records about solutions; the
  marketplace itself — distribution, installation, delivery —
  is a deployment property (PLATFORM-LAYER.md decision 6) and
  happens elsewhere (``distributed_here`` /
  ``installed_here`` are False on every record).
- **No bank details, no identifiers, no scores.** No record
  shape has a field that could hold a real name, a government
  identifier, or any bank or account identifier, and no
  derived view carries a rate, trend, forecast, average, or
  grand-total key — pinned by exact key-set tests and recursive
  key scans. The category's standing named absences stand:
  trading & investment execution above all — this class has no
  order, execution, or payment operation, pinned by test.
- RBAC goes through :mod:`finance.access` exactly as the core
  and the first unit enforce it: operations map onto existing
  core actions (creates/registrations -> ``enter``, outcome
  and adoption reports -> ``record``, reads and derived views
  -> ``read``), checked *before* any state change or id
  allocation for User-like actors, with denied attempts
  recorded on the core audit log as ``exta_<action>:denied``.
  Program membership is enforced through the core store's own
  access-checked program read. The High apparatus binds the
  surface through the core: extension actions land on the
  hash-chained, fail-closed audit log, and the separated
  ``auditor`` role is denied every extension read and write
  while its core audit duty works unchanged. If an audit write
  raises, the record insertion and its id roll back before the
  error propagates.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PLAN_KINDS = (
    "planning",
    "budgeting",
)
KNOWN_PLAN_KINDS = frozenset(PLAN_KINDS)
CONNECTOR_SOURCE_KINDS = (
    "erp_system",
    "financial_system",
    "office_spreadsheet",
    "other",
)
KNOWN_CONNECTOR_SOURCE_KINDS = frozenset(CONNECTOR_SOURCE_KINDS)
SYNC_DIRECTIONS = (
    "inbound",
    "outbound",
)
KNOWN_SYNC_DIRECTIONS = frozenset(SYNC_DIRECTIONS)
SYNC_REPORT_OUTCOMES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
KNOWN_SYNC_REPORT_OUTCOMES = frozenset(SYNC_REPORT_OUTCOMES)
PUBLISHER_KINDS = (
    "platform",
    "third_party",
)
KNOWN_PUBLISHER_KINDS = frozenset(PUBLISHER_KINDS)
ADOPTION_REPORT_OUTCOMES = (
    "reported_installed",
    "reported_removed",
    "reported_failed",
)
KNOWN_ADOPTION_REPORT_OUTCOMES = frozenset(ADOPTION_REPORT_OUTCOMES)


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


def _cents(value, what):
    """Integer cents, exactly as the core validates amounts.

    Booleans and floats are rejected even when integral, so all
    arithmetic over recorded values is exact by construction.
    Signed values are accepted: plan lines carry eliminations
    and adjustments as negative lines, the sign structural in
    the value itself.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents"
                              % (what,))
    return value


def _count_nonnegative(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _totals_by_currency(amounts):
    """Sum recorded integer-cent amounts per currency label.

    ``amounts`` is an iterable of ``(currency_label,
    amount_cents)`` pairs over values recorded on this surface.
    The result maps each label that occurs to the exact sum of
    its own amounts; labels never mix — no cross-currency sum
    is computed anywhere. This is the negative control's
    target.
    """
    totals = {}
    for label, amount in amounts:
        totals[label] = totals.get(label, 0) + amount
    return totals


class FinanceExtensionsAddition:
    """Second GAPS-batch extension surface over a core FinanceStore."""

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
        """Enforce a permission, auditing a denial (first-unit form)."""
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
        """Core access-checked program read (membership + read role)."""
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

    # -- CPM engine: entities, plans, lines, forecasts (built) ---------
    #
    # The addition fork's headline function — consolidation,
    # planning, budgeting, and forecasting as computation — in
    # its records form. What lands: consolidation entity
    # structure records, plan definitions held as data, plan
    # line values recorded in integer cents, and forecast
    # figures recorded verbatim as reported. Consolidation
    # totals are exact integer sums over the values recorded
    # here, derived at read per currency label; no plan is
    # modeled and no forecast is computed here
    # (``modeled_here`` / ``computed_here`` are False), and no
    # source-system data enters this surface.

    def register_cpm_entity(self, program_id, entity_ref, currency_label,
                            actor, parent_entity_id=None, name_label=None):
        """Register one consolidation entity as a structure record.

        ``entity_ref`` is the caller's opaque reference for the
        entity, unique within the program; ``currency_label``
        names the entity's reporting currency, held as data and
        never converted; ``parent_entity_id`` optionally binds
        the entity under another registered entity of the same
        program (the consolidation structure).
        """
        self._guard(actor, "enter", "exta_cpm_entity_register")
        self._program(program_id, actor)
        _non_empty(entity_ref, "entity_ref")
        _non_empty(currency_label, "currency_label")
        _string_or_none(name_label, "name_label")
        for existing in self._list("cpm_entity", program_id):
            if existing["entity_ref"] == entity_ref:
                raise ValidationError(
                    "entity ref %r already exists in program %r"
                    % (entity_ref, program_id)
                )
        if parent_entity_id is not None:
            self._get("cpm_entity", parent_entity_id, program_id)
        return self._create(
            "cpm_entity", "cent",
            {"program_id": program_id, "entity_ref": entity_ref,
             "currency_label": currency_label,
             "parent_entity_id": parent_entity_id,
             "name_label": name_label, "modeled_here": False,
             "state": "recorded_structure_only"},
            actor, "exta_cpm_entity_register")

    def create_cpm_plan(self, program_id, entity_id, plan_ref, plan_kind,
                        period_label, actor):
        """Record a plan definition against a registered entity.

        The definition is held as data (``plan_kind`` over
        planning / budgeting; ``period_label`` verbatim); its
        values arrive as plan line records. Nothing is modeled
        here.
        """
        self._guard(actor, "enter", "exta_cpm_plan_create",
                    target=entity_id)
        self._program(program_id, actor)
        _non_empty(plan_ref, "plan_ref")
        _one_of(plan_kind, KNOWN_PLAN_KINDS, PLAN_KINDS, "plan_kind")
        _non_empty(period_label, "period_label")
        entity = self._get("cpm_entity", entity_id, program_id)
        for existing in self._list("cpm_plan", program_id):
            if existing["plan_ref"] == plan_ref:
                raise ValidationError(
                    "plan ref %r already exists in program %r"
                    % (plan_ref, program_id)
                )
        return self._create(
            "cpm_plan", "cpln",
            {"program_id": program_id, "entity_id": entity_id,
             "plan_ref": plan_ref, "plan_kind": plan_kind,
             "period_label": period_label,
             "currency_label": entity["currency_label"],
             "modeled_here": False, "state": "recorded_definition_only"},
            actor, "exta_cpm_plan_create")

    def record_cpm_plan_line(self, program_id, plan_id, line_label,
                             amount_cents, actor):
        """Record one plan line value, in integer cents.

        ``amount_cents`` is a signed integer: eliminations and
        adjustments are negative lines. The value is recorded
        data; the plan record itself is never changed by
        recording a line (pinned by test).
        """
        self._guard(actor, "enter", "exta_cpm_plan_line_record",
                    target=plan_id)
        self._program(program_id, actor)
        _non_empty(line_label, "line_label")
        _cents(amount_cents, "amount_cents")
        self._get("cpm_plan", plan_id, program_id)
        return self._create(
            "cpm_plan_line", "clin",
            {"program_id": program_id, "plan_id": plan_id,
             "line_label": line_label, "amount_cents": amount_cents},
            actor, "exta_cpm_plan_line_record")

    def record_cpm_forecast(self, program_id, entity_id, period_label,
                            reported_amount_cents, actor, basis_label=None):
        """Record a forecast figure, verbatim as reported.

        The figure is the planning system's own: stored exactly
        as reported in integer cents under the entity's currency
        label, and never computed, adjusted, or converted here
        (``computed_here: False``).
        """
        self._guard(actor, "record", "exta_cpm_forecast_record",
                    target=entity_id)
        self._program(program_id, actor)
        _non_empty(period_label, "period_label")
        _cents(reported_amount_cents, "reported_amount_cents")
        _string_or_none(basis_label, "basis_label")
        entity = self._get("cpm_entity", entity_id, program_id)
        return self._create(
            "cpm_forecast", "cfct",
            {"program_id": program_id, "entity_id": entity_id,
             "period_label": period_label,
             "reported_amount_cents": reported_amount_cents,
             "currency_label": entity["currency_label"],
             "basis_label": basis_label, "computed_here": False,
             "state": "recorded_as_reported"},
            actor, "exta_cpm_forecast_record")

    def get_cpm_entity(self, program_id, entity_id, actor):
        """One consolidation entity record. Action: read."""
        self._guard(actor, "read", "exta_cpm_entity_get", target=entity_id)
        self._program(program_id, actor)
        return self._fetch("cpm_entity", entity_id, program_id)

    def list_cpm_entities(self, program_id, actor):
        """All consolidation entity records of a program. Action: read."""
        self._guard(actor, "read", "exta_cpm_entity_list")
        self._program(program_id, actor)
        return self._list("cpm_entity", program_id)

    def list_cpm_plans(self, program_id, actor, entity_id=None):
        """Plan records, optionally of one entity. Action: read."""
        self._guard(actor, "read", "exta_cpm_plan_list")
        self._program(program_id, actor)
        filters = {}
        if entity_id is not None:
            filters["entity_id"] = entity_id
        return self._list("cpm_plan", program_id, **filters)

    def list_cpm_plan_lines(self, program_id, plan_id, actor):
        """Plan line records of one plan. Action: read."""
        self._guard(actor, "read", "exta_cpm_plan_line_list",
                    target=plan_id)
        self._program(program_id, actor)
        self._get("cpm_plan", plan_id, program_id)
        return self._list("cpm_plan_line", program_id, plan_id=plan_id)

    def list_cpm_forecasts(self, program_id, actor, entity_id=None):
        """Forecast records, optionally of one entity. Action: read."""
        self._guard(actor, "read", "exta_cpm_forecast_list")
        self._program(program_id, actor)
        filters = {}
        if entity_id is not None:
            filters["entity_id"] = entity_id
        return self._list("cpm_forecast", program_id, **filters)

    def cpm_plan_view(self, program_id, plan_id, actor):
        """Derived at read: one plan plus its line count and the
        exact sum of its recorded line values. The stored plan
        record carries no total. Action: read."""
        self._guard(actor, "read", "exta_cpm_plan_view", target=plan_id)
        self._program(program_id, actor)
        plan = self._fetch("cpm_plan", plan_id, program_id)
        lines = self._list("cpm_plan_line", program_id, plan_id=plan_id)
        plan["line_count"] = len(lines)
        plan["plan_total_cents"] = sum(
            line["amount_cents"] for line in lines)
        plan["derived"] = True
        plan["method"] = "sum_over_recorded_plan_lines"
        return plan

    def cpm_consolidation_view(self, program_id, period_label, actor):
        """Derived at read: consolidation over the period's
        recorded plan lines and recorded forecast figures,
        summed **per currency label** — totals never mix
        currencies. Plan totals are exact sums over values
        recorded on this surface; forecast totals are sums of
        figures recorded verbatim as reported, stated as such.
        Nothing is stored. Action: read."""
        self._guard(actor, "read", "exta_cpm_consolidation_view")
        self._program(program_id, actor)
        _non_empty(period_label, "period_label")
        plans = [p for p in self._list("cpm_plan", program_id)
                 if p["period_label"] == period_label]
        plan_amounts = []
        for plan in plans:
            lines = self._list(
                "cpm_plan_line", program_id, plan_id=plan["id"])
            for line in lines:
                plan_amounts.append(
                    (plan["currency_label"], line["amount_cents"]))
        forecasts = [f for f in self._list("cpm_forecast", program_id)
                     if f["period_label"] == period_label]
        forecast_amounts = [
            (f["currency_label"], f["reported_amount_cents"])
            for f in forecasts]
        return {
            "program_id": program_id,
            "period_label": period_label,
            "plan_count": len(plans),
            "forecast_count": len(forecasts),
            "plan_totals_by_currency": _totals_by_currency(plan_amounts),
            "forecast_totals_by_currency": _totals_by_currency(
                forecast_amounts),
            "computed_here": False,
            "derived": True,
            "method": "recorded_values_summed_per_currency_label",
        }

    # -- Data integration & connector surface (reference) --------------
    #
    # Labeled reference implementation (the drafted stub-engine
    # entry). Integration with ERP and financial systems and the
    # Office / spreadsheet add-in surface are external transport:
    # what lands is the records layer in front of it — connector
    # definition records and sync receipt records holding what a
    # connector reported. Every record carries
    # ``reference_stub: True`` and ``reference_transport: True``;
    # ``connected_here`` / ``synced_here`` / ``imported_here``
    # are False and a receipt imports nothing into the core.

    def register_connector(self, program_id, connector_ref, source_kind,
                           actor, label=None):
        """Register a connector definition reference (stub).

        ``connector_ref`` is the caller's opaque reference for
        the connector, unique within the program; ``source_kind``
        names the class of system on the other end (ERP system,
        financial system, Office / spreadsheet add-in surface,
        other), held as data.
        """
        self._guard(actor, "enter", "exta_connector_register")
        self._program(program_id, actor)
        _non_empty(connector_ref, "connector_ref")
        _one_of(source_kind, KNOWN_CONNECTOR_SOURCE_KINDS,
                CONNECTOR_SOURCE_KINDS, "source_kind")
        _string_or_none(label, "label")
        for existing in self._list("connector", program_id):
            if existing["connector_ref"] == connector_ref:
                raise ValidationError(
                    "connector ref %r already exists in program %r"
                    % (connector_ref, program_id)
                )
        return self._create(
            "connector", "conn",
            {"program_id": program_id, "connector_ref": connector_ref,
             "source_kind": source_kind, "label": label,
             "reference_stub": True, "reference_transport": True,
             "connected_here": False, "synced_here": False,
             "state": "recorded_definition_only"},
            actor, "exta_connector_register")

    def record_sync_receipt(self, program_id, connector_id, direction,
                            outcome, actor, records_reported=None,
                            detail=None):
        """Record a sync receipt, as reported (stub).

        ``outcome`` is the connector's reported outcome label
        from the fixed vocabulary; ``records_reported`` is the
        record count the connector reported moving, stored as
        reported — validated as a non-negative integer count,
        booleans and floats rejected. Nothing was imported by
        this build.
        """
        self._guard(actor, "record", "exta_sync_receipt_record",
                    target=connector_id)
        self._program(program_id, actor)
        _one_of(direction, KNOWN_SYNC_DIRECTIONS, SYNC_DIRECTIONS,
                "direction")
        _one_of(outcome, KNOWN_SYNC_REPORT_OUTCOMES,
                SYNC_REPORT_OUTCOMES, "outcome")
        if records_reported is not None:
            _count_nonnegative(records_reported, "records_reported")
        _string_or_none(detail, "detail")
        self._get("connector", connector_id, program_id)
        return self._create(
            "sync_receipt", "csyn",
            {"program_id": program_id, "connector_id": connector_id,
             "direction": direction, "outcome": outcome,
             "records_reported": records_reported, "detail": detail,
             "reference_stub": True, "reference_transport": True,
             "imported_here": False, "synced_here": False},
            actor, "exta_sync_receipt_record")

    def get_connector(self, program_id, connector_id, actor):
        """One connector definition record. Action: read."""
        self._guard(actor, "read", "exta_connector_get",
                    target=connector_id)
        self._program(program_id, actor)
        return self._fetch("connector", connector_id, program_id)

    def list_connectors(self, program_id, actor):
        """All connector definition records of a program. Action: read."""
        self._guard(actor, "read", "exta_connector_list")
        self._program(program_id, actor)
        return self._list("connector", program_id)

    def list_sync_receipts(self, program_id, actor, connector_id=None):
        """Sync receipt records, optionally of one connector.

        Action: read.
        """
        self._guard(actor, "read", "exta_sync_receipt_list")
        self._program(program_id, actor)
        filters = {}
        if connector_id is not None:
            filters["connector_id"] = connector_id
        return self._list("sync_receipt", program_id, **filters)

    def integration_summary(self, program_id, actor):
        """Derived at read: connector/receipt counts, per-outcome
        counts, and the total of reported record counts (a total
        of *reported* counts, stated as such). Nothing is stored.
        Action: read."""
        self._guard(actor, "read", "exta_integration_summary")
        self._program(program_id, actor)
        connectors = self._list("connector", program_id)
        receipts = self._list("sync_receipt", program_id)
        by_outcome = {label: 0 for label in SYNC_REPORT_OUTCOMES}
        for receipt in receipts:
            by_outcome[receipt["outcome"]] += 1
        return {
            "program_id": program_id,
            "connectors": len(connectors),
            "receipts": len(receipts),
            "receipts_by_outcome": by_outcome,
            "total_records_reported": sum(
                r["records_reported"] for r in receipts
                if r["records_reported"] is not None),
            "reference_stub": True,
            "imported_here": False,
            "derived": True,
            "method": "counts_over_connector_sync_receipt_records",
        }

    # -- Solution marketplace & extensibility (built) ------------------
    #
    # The fork's Solution Exchange, in its records form: solution
    # listing records held as catalog data and adoption records
    # with reported outcomes. The marketplace itself —
    # distribution, installation, delivery of the listed
    # solutions — is a deployment property (PLATFORM-LAYER.md
    # decision 6) and happens elsewhere: ``distributed_here`` /
    # ``installed_here`` are False on every record, and recording
    # an adoption outcome leaves the listing record
    # byte-identical.

    def register_solution_listing(self, program_id, listing_ref,
                                  publisher_kind, actor, category_label=None,
                                  version_label=None, title_label=None):
        """Register one marketplace solution listing as a catalog
        record.

        ``listing_ref`` is the caller's opaque reference for the
        listing, unique within the program; ``publisher_kind``
        names whether the solution is the platform's own or a
        third party's (the fork's marketplace carries both),
        held as data; category, version, and title labels are
        held verbatim as data.
        """
        self._guard(actor, "enter", "exta_solution_listing_register")
        self._program(program_id, actor)
        _non_empty(listing_ref, "listing_ref")
        _one_of(publisher_kind, KNOWN_PUBLISHER_KINDS, PUBLISHER_KINDS,
                "publisher_kind")
        _string_or_none(category_label, "category_label")
        _string_or_none(version_label, "version_label")
        _string_or_none(title_label, "title_label")
        for existing in self._list("solution_listing", program_id):
            if existing["listing_ref"] == listing_ref:
                raise ValidationError(
                    "listing ref %r already exists in program %r"
                    % (listing_ref, program_id)
                )
        return self._create(
            "solution_listing", "slst",
            {"program_id": program_id, "listing_ref": listing_ref,
             "publisher_kind": publisher_kind,
             "category_label": category_label,
             "version_label": version_label, "title_label": title_label,
             "distributed_here": False, "installed_here": False,
             "state": "recorded_listing_only"},
            actor, "exta_solution_listing_register")

    def record_solution_adoption(self, program_id, listing_id, adopter_ref,
                                 actor):
        """Record an adoption of a listed solution.

        ``adopter_ref`` is the caller's opaque reference for the
        adopting deployment or organization. The adoption is a
        record; nothing is installed by this build.
        """
        self._guard(actor, "enter", "exta_solution_adoption_record",
                    target=listing_id)
        self._program(program_id, actor)
        _non_empty(adopter_ref, "adopter_ref")
        self._get("solution_listing", listing_id, program_id)
        return self._create(
            "solution_adoption", "sado",
            {"program_id": program_id, "listing_id": listing_id,
             "adopter_ref": adopter_ref, "installed_here": False,
             "state": "recorded_adoption_only"},
            actor, "exta_solution_adoption_record")

    def record_adoption_report(self, program_id, adoption_id, outcome,
                               actor, detail=None):
        """Record an adoption outcome, verbatim as reported.

        ``outcome`` is the installing side's reported label from
        the fixed vocabulary; the installation happened there,
        not here.
        """
        self._guard(actor, "record", "exta_adoption_report_record",
                    target=adoption_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_ADOPTION_REPORT_OUTCOMES,
                ADOPTION_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("solution_adoption", adoption_id, program_id)
        return self._create(
            "adoption_report", "sadr",
            {"program_id": program_id, "adoption_id": adoption_id,
             "outcome": outcome, "detail": detail,
             "installed_here": False},
            actor, "exta_adoption_report_record")

    def get_solution_listing(self, program_id, listing_id, actor):
        """One solution listing record. Action: read."""
        self._guard(actor, "read", "exta_solution_listing_get",
                    target=listing_id)
        self._program(program_id, actor)
        return self._fetch("solution_listing", listing_id, program_id)

    def list_solution_listings(self, program_id, actor):
        """All solution listing records of a program. Action: read."""
        self._guard(actor, "read", "exta_solution_listing_list")
        self._program(program_id, actor)
        return self._list("solution_listing", program_id)

    def list_solution_adoptions(self, program_id, actor, listing_id=None):
        """Adoption records, optionally of one listing. Action: read."""
        self._guard(actor, "read", "exta_solution_adoption_list")
        self._program(program_id, actor)
        filters = {}
        if listing_id is not None:
            filters["listing_id"] = listing_id
        return self._list("solution_adoption", program_id, **filters)

    def list_adoption_reports(self, program_id, actor, adoption_id=None):
        """Adoption report records, optionally of one adoption.

        Action: read.
        """
        self._guard(actor, "read", "exta_adoption_report_list")
        self._program(program_id, actor)
        filters = {}
        if adoption_id is not None:
            filters["adoption_id"] = adoption_id
        return self._list("adoption_report", program_id, **filters)

    def marketplace_summary(self, program_id, actor):
        """Derived at read: listing counts (overall and per
        publisher kind), adoption counts, and per-outcome report
        counts. Counts only — no adoption rate or popularity
        figure is computed. Nothing is stored. Action: read."""
        self._guard(actor, "read", "exta_marketplace_summary")
        self._program(program_id, actor)
        listings = self._list("solution_listing", program_id)
        adoptions = self._list("solution_adoption", program_id)
        reports = self._list("adoption_report", program_id)
        by_publisher = {label: 0 for label in PUBLISHER_KINDS}
        for listing in listings:
            by_publisher[listing["publisher_kind"]] += 1
        by_outcome = {label: 0 for label in ADOPTION_REPORT_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {
            "program_id": program_id,
            "listings": len(listings),
            "listings_by_publisher_kind": by_publisher,
            "adoptions": len(adoptions),
            "adoption_reports": len(reports),
            "adoption_reports_by_outcome": by_outcome,
            "distributed_here": False,
            "installed_here": False,
            "derived": True,
            "method": "counts_over_solution_listing_adoption_records",
        }
