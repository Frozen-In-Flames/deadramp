"""Final GAPS batch extensions for the Operations Management
untiered set.

Clean-room, standard-library-only records/derivation extensions
for the 9 open Extended entries of this set's union spec
(``UNION-SPEC.md`` "Gaps registered for this set", GAPS.md section
"Untiered Set 2 -- Operations Management (20 forks, tier null)"):
8 built as in-substrate records plus deterministic derivations
over the substrate's own records, and 1 shipped as a labeled
reference implementation (AI assistants & agents, re-judged from
its drafted build-extension disposition -- see ``BATCH.md``).
See ``BATCH.md`` in the group directory for the per-entry
disposition and the adjudication notes.

Design, following the core's doctrines and this set's tier
discipline:

- This module is a wrapper around :class:`OpsStore`; the core
  modules are untouched (byte-identical). Core record existence
  (assets, projects, organizations) is always checked through the
  core store's public API, never re-implemented.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every record
  and view recursively for one (and for floats and numeric lists).
  The forks' documented control claims stay where the union spec
  put them -- in the spec, as the forks' claims about themselves.
- RBAC goes through :mod:`opsmgmt.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like
  actors, and records denied attempts on the core audit log with
  the extension action name suffixed ``:denied``. Plain-string
  actors carry identity but no role, mirroring the core
  convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to people, organizations, suppliers, vehicles,
  and outputs are opaque ``*_ref`` strings or core record ids.
  No record shape in this module can hold a payload, content, a
  prompt, or a computed score; counts and amounts that describe
  an external platform's work are stored as reported, never
  computed here. Money-shaped amounts are integer cents and
  energy amounts integer watt-hours, floats and bools rejected
  at the boundary, mirroring the core's usage discipline.
- Derived values are derived at read and never stored: program
  work-order counts, produced/reported totals, current state
  labels, portfolio counts. Stored records carry no derived key;
  tests pin that. The current-state derivation lives at a
  single named seam (``_latest_label``): the latest recorded
  label wins. The seam is the batch's fresh negative control.
- Nothing here executes against an external system or operates
  a device: maintenance is performed elsewhere, production is
  not run, awards are recorded as reported outcomes, charging
  sessions are not controlled, lockers are not unlocked, and no
  payment moves. Every record that touches an execution-shaped
  function carries its ``*_here: False`` label; the one
  control-shaped component (charging-session control requests)
  and the whole AI-assistant family additionally carry
  ``reference_stub: True``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import KNOWN_WORK_TYPES, WORK_TYPES


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


def _int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _nonneg_int(value, what):
    _int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _pos_int(value, what):
    _int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _components(value):
    """Validate bill-of-materials components.

    A list of dicts, each exactly ``{"part_ref", "quantity"}``:
    an opaque part reference and a positive integer quantity.
    Anything else -- extra keys, float quantities, bare numbers
    -- is rejected whole.
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("components must be a list of component dicts")
    if len(value) > 100:
        raise ValidationError("components may hold at most 100 entries")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("each component must be a dict")
        if set(item.keys()) != {"part_ref", "quantity"}:
            raise ValidationError(
                "each component must carry exactly part_ref and quantity")
        _non_empty(item["part_ref"], "component part_ref")
        _pos_int(item["quantity"], "component quantity")
        result.append({"part_ref": item["part_ref"],
                       "quantity": item["quantity"]})
    return result


class OpsExtensions:
    """GAPS-batch extension surface over a core OpsStore."""

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
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
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

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _asset(self, asset_id):
        """Return the core asset record (NotFoundError if absent)."""
        return self.store.get_asset(asset_id)

    def _project(self, project_id):
        """Return the core project record (NotFoundError if absent)."""
        return self.store.get_project(project_id)

    def _organization(self, organization_id):
        """Return the core organization record (NotFoundError if absent)."""
        return self.store.get_organization(organization_id)

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
    def _latest_label(labels):
        """The current state of a record: its latest recorded label.

        State and event records are append-only and kept in
        recording order; the current state is the LAST label
        recorded, or ``recorded`` when no label has been recorded
        yet. This derivation is the batch's fresh negative-control
        seam (see tests/README.md): reading the earliest label
        instead would resurrect superseded states.
        """
        if not labels:
            return "recorded"
        return labels[-1]

    # -- CMMS / EAM depth (records over core assets & work orders) ----
    # A maintenance program is a definition: a name, an optional
    # core asset binding, a work type, and a reported interval.
    # Nothing is scheduled or performed here. Custody events are
    # append-only reported labels over a core asset; no custody
    # moves. The program view derives its counts at read from the
    # core's own work-order views (overdue included, through the
    # core's own seam) -- nothing is stored on the program record.

    def define_maintenance_program(self, name, actor, asset_id=None,
                                   work_type="maintenance",
                                   interval_days_reported=None):
        """Register a maintenance-program definition. Action: work_write.

        ``interval_days_reported`` is the owning platform's
        reported interval -- a property of the definition, stored
        as reported. No preventive-maintenance run is scheduled
        or performed (``performed_here`` / ``executed_here``
        False).
        """
        self._guard(actor, "work_write", "ext_maintenance_program_define",
                    asset_id)
        _non_empty(name, "program name")
        if work_type not in KNOWN_WORK_TYPES:
            raise ValidationError(
                "work_type must be one of %s" % (", ".join(WORK_TYPES),))
        if interval_days_reported is not None:
            _pos_int(interval_days_reported, "interval_days_reported")
        with self._lock:
            if asset_id is not None:
                self._asset(asset_id)
            return self._create(
                "maintenance_program", "pm",
                {"name": name, "asset_id": asset_id,
                 "work_type": work_type,
                 "interval_days_reported": interval_days_reported,
                 "definition_only": True,
                 "performed_here": False,
                 "executed_here": False},
                actor, "ext_maintenance_program_define")

    def get_maintenance_program(self, program_id, actor=None):
        """Return one maintenance-program definition. Action: work_read."""
        self._guard_read(actor, "work_read",
                         "ext_maintenance_program_read", program_id)
        return self._fetch("maintenance_program", program_id)

    def list_maintenance_programs(self, asset_id=None, actor=None):
        """Return maintenance-program definitions. Action: work_read."""
        self._guard_read(actor, "work_read",
                         "ext_maintenance_program_read", asset_id)
        if asset_id is not None:
            self._asset(asset_id)
        return self._list("maintenance_program", asset_id=asset_id)

    def record_custody_event(self, asset_id, event_label, actor,
                             counterparty_ref=None):
        """Record a chain-of-custody event over a core asset.

        Action: work_write. The label and counterparty reference
        are recorded verbatim as reported; no custody is
        transferred by this build (``custody_transferred_here``
        is False).
        """
        self._guard(actor, "work_write", "ext_custody_event_record",
                    asset_id)
        _non_empty(event_label, "event_label")
        _string_or_none(counterparty_ref, "counterparty_ref")
        with self._lock:
            self._asset(asset_id)
            return self._create(
                "custody_event", "cus",
                {"asset_id": asset_id, "event_label": event_label,
                 "counterparty_ref": counterparty_ref,
                 "custody_transferred_here": False,
                 "recorded_only": True},
                actor, "ext_custody_event_record")

    def list_custody_events(self, asset_id=None, actor=None):
        """Return custody-event records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_custody_event_read",
                         asset_id)
        if asset_id is not None:
            self._asset(asset_id)
        return self._list("custody_event", asset_id=asset_id)

    def maintenance_program_view(self, program_id, actor=None, now=None):
        """Program record plus counts derived at read. Action: work_read.

        Counts derive from the core's work-order views for the
        program's asset and work type (``overdue`` through the
        core's own derivation) and from this surface's custody
        events for the asset. An unbound program (no asset)
        derives zero counts. Nothing derived is stored: the
        stored program record carries no count key.
        """
        self._guard_read(actor, "work_read",
                         "ext_maintenance_program_read", program_id)
        with self._lock:
            program = self._fetch("maintenance_program", program_id)
            matching = []
            if program["asset_id"] is not None:
                orders = self.store.list_work_orders(actor=actor, now=now)
                matching = [w for w in orders
                            if w["asset_id"] == program["asset_id"]
                            and w["work_type"] == program["work_type"]]
            view = dict(program)
            view["work_order_count"] = len(matching)
            view["open_work_order_count"] = len(
                [w for w in matching
                 if w["status"] in ("open", "in_progress")])
            view["overdue_work_order_count"] = len(
                [w for w in matching if w["overdue"]])
            view["custody_event_count"] = len(self._list(
                "custody_event", asset_id=program["asset_id"])) \
                if program["asset_id"] is not None else 0
            view["derived"] = True
            view["stored"] = False
            return view

    # -- Manufacturing execution & ERP/MRP (records form) -------------
    # A bill of materials is a definition: component part
    # references with integer quantities, held as data. A
    # production order records an intent against a BOM; outcomes
    # (including produced counts) are stored exactly as reported.
    # No production is executed (``executed_here`` is False) and
    # no MRP run computes anything: the order view's produced
    # total is a sum of reported counts, derived at read.

    def define_bill_of_materials(self, name, actor, project_id=None,
                                 components=None):
        """Register a bill-of-materials definition. Action: work_write."""
        self._guard(actor, "work_write", "ext_bom_define", project_id)
        _non_empty(name, "bill of materials name")
        components = _components(components)
        with self._lock:
            if project_id is not None:
                self._project(project_id)
            return self._create(
                "bill_of_materials", "bom",
                {"name": name, "project_id": project_id,
                 "components": components,
                 "definition_only": True,
                 "executed_here": False},
                actor, "ext_bom_define")

    def get_bill_of_materials(self, bom_id, actor=None):
        """Return one bill-of-materials definition. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_bom_read", bom_id)
        return self._fetch("bill_of_materials", bom_id)

    def list_bills_of_materials(self, project_id=None, actor=None):
        """Return bill-of-materials definitions. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_bom_read", project_id)
        if project_id is not None:
            self._project(project_id)
        return self._list("bill_of_materials", project_id=project_id)

    def create_production_order(self, bom_id, actor, project_id=None,
                                quantity=1):
        """Record a production order against a BOM. Action: work_write.

        ``quantity`` is a positive integer count of units the
        order covers, recorded as stated. The order is a record;
        no production run starts (``executed_here`` is False).
        The project defaults to the BOM's project when not given.
        """
        self._guard(actor, "work_write", "ext_production_order_create",
                    bom_id)
        _pos_int(quantity, "quantity")
        with self._lock:
            bom = self._get("bill_of_materials", bom_id)
            if project_id is None:
                project_id = bom["project_id"]
            if project_id is not None:
                self._project(project_id)
            return self._create(
                "production_order", "po",
                {"bom_id": bom_id, "project_id": project_id,
                 "quantity": quantity,
                 "status": "recorded",
                 "executed_here": False},
                actor, "ext_production_order_create")

    def get_production_order(self, order_id, actor=None):
        """Return one production-order record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_production_order_read",
                         order_id)
        return self._fetch("production_order", order_id)

    def record_production_outcome(self, order_id, outcome_label, actor,
                                  produced_reported=None):
        """Record a production outcome exactly as reported.

        Action: work_write. ``produced_reported`` is the owning
        platform's reported produced count, stored verbatim;
        this build produced nothing (``executed_here`` False).
        """
        self._guard(actor, "work_write", "ext_production_outcome_record",
                    order_id)
        _non_empty(outcome_label, "outcome_label")
        if produced_reported is not None:
            _nonneg_int(produced_reported, "produced_reported")
        with self._lock:
            self._get("production_order", order_id)
            return self._create(
                "production_outcome", "pout",
                {"order_id": order_id, "outcome_label": outcome_label,
                 "produced_reported": produced_reported,
                 "outcome_reported": True,
                 "executed_here": False},
                actor, "ext_production_outcome_record")

    def list_production_outcomes(self, order_id=None, actor=None):
        """Return production-outcome records. Action: work_read."""
        self._guard_read(actor, "work_read",
                         "ext_production_outcome_read", order_id)
        if order_id is not None:
            self._get("production_order", order_id)
        return self._list("production_outcome", order_id=order_id)

    def production_order_view(self, order_id, actor=None):
        """Order record plus outcome rollup derived at read.

        Action: work_read. ``produced_total_reported`` is the sum
        of the outcomes' reported produced counts -- a sum of
        reports, not a production figure computed here. The
        stored order record carries no total.
        """
        self._guard_read(actor, "work_read", "ext_production_order_read",
                         order_id)
        with self._lock:
            order = self._fetch("production_order", order_id)
            outcomes = self._list("production_outcome", order_id=order_id)
            view = dict(order)
            view["outcomes"] = outcomes
            view["outcome_count"] = len(outcomes)
            view["produced_total_reported"] = sum(
                o["produced_reported"] for o in outcomes
                if o["produced_reported"] is not None)
            view["derived"] = True
            view["stored"] = False
            return view

    # -- Procurement & sourcing platforms (records form) --------------
    # A requisition is a record bound to core organization /
    # project records. Sourcing events are append-only reported
    # labels; the requisition's current state derives from the
    # latest label at read (the ``_latest_label`` seam) and is
    # never stored. Awards are reported outcomes: the decision
    # was made elsewhere (``decided_here`` is False); amounts are
    # integer cents exactly as reported.

    def create_requisition(self, subject, actor, org_id=None,
                           project_id=None):
        """Create a requisition record. Action: project_write."""
        self._guard(actor, "project_write", "ext_requisition_create",
                    project_id)
        _non_empty(subject, "requisition subject")
        with self._lock:
            if org_id is not None:
                self._organization(org_id)
            if project_id is not None:
                self._project(project_id)
            return self._create(
                "requisition", "req",
                {"subject": subject, "org_id": org_id,
                 "project_id": project_id,
                 "decided_here": False},
                actor, "ext_requisition_create")

    def get_requisition(self, requisition_id, actor=None):
        """Return one requisition record. Action: project_read."""
        self._guard_read(actor, "project_read", "ext_requisition_read",
                         requisition_id)
        return self._fetch("requisition", requisition_id)

    def record_sourcing_event(self, requisition_id, event_label, actor,
                              supplier_ref=None):
        """Append a reported sourcing event label. Action: project_write."""
        self._guard(actor, "project_write", "ext_sourcing_event_record",
                    requisition_id)
        _non_empty(event_label, "event_label")
        _string_or_none(supplier_ref, "supplier_ref")
        with self._lock:
            self._get("requisition", requisition_id)
            return self._create(
                "sourcing_event", "sev",
                {"requisition_id": requisition_id,
                 "event_label": event_label,
                 "supplier_ref": supplier_ref,
                 "recorded_only": True},
                actor, "ext_sourcing_event_record")

    def list_sourcing_events(self, requisition_id=None, actor=None):
        """Return sourcing-event records. Action: project_read."""
        self._guard_read(actor, "project_read", "ext_sourcing_event_read",
                         requisition_id)
        if requisition_id is not None:
            self._get("requisition", requisition_id)
        return self._list("sourcing_event", requisition_id=requisition_id)

    def record_award(self, requisition_id, supplier_ref, actor,
                     amount_cents_reported=None):
        """Record an award as a reported outcome. Action: project_write.

        The award decision was made on the owning platform; this
        build records it (``decided_here`` is False).
        ``amount_cents_reported`` is integer cents exactly as
        reported.
        """
        self._guard(actor, "project_write", "ext_award_record",
                    requisition_id)
        _non_empty(supplier_ref, "supplier_ref")
        if amount_cents_reported is not None:
            _nonneg_int(amount_cents_reported, "amount_cents_reported")
        with self._lock:
            self._get("requisition", requisition_id)
            return self._create(
                "award", "awd",
                {"requisition_id": requisition_id,
                 "supplier_ref": supplier_ref,
                 "amount_cents_reported": amount_cents_reported,
                 "outcome_reported": True,
                 "decided_here": False},
                actor, "ext_award_record")

    def list_awards(self, requisition_id=None, actor=None):
        """Return award records. Action: project_read."""
        self._guard_read(actor, "project_read", "ext_award_read",
                         requisition_id)
        if requisition_id is not None:
            self._get("requisition", requisition_id)
        return self._list("award", requisition_id=requisition_id)

    def requisition_view(self, requisition_id, actor=None):
        """Requisition plus state derived at read. Action: project_read.

        ``current_state_label`` is the latest recorded sourcing
        event label (the ``_latest_label`` seam); the stored
        requisition record carries no state key.
        ``awarded_total_cents_reported`` sums the awards' reported
        amounts -- a sum of reports, derived at read.
        """
        self._guard_read(actor, "project_read", "ext_requisition_read",
                         requisition_id)
        with self._lock:
            requisition = self._fetch("requisition", requisition_id)
            events = self._list("sourcing_event",
                                requisition_id=requisition_id)
            awards = self._list("award", requisition_id=requisition_id)
            view = dict(requisition)
            view["current_state_label"] = self._latest_label(
                [e["event_label"] for e in events])
            view["event_count"] = len(events)
            view["award_count"] = len(awards)
            view["awarded_total_cents_reported"] = sum(
                a["amount_cents_reported"] for a in awards
                if a["amount_cents_reported"] is not None)
            view["derived"] = True
            view["stored"] = False
            return view

    # -- Contract execution management (records form) -----------------
    # An agreement is a record; its execution states are
    # append-only reported labels whose latest value derives at
    # read (the ``_latest_label`` seam). Surveillance and
    # obligation tracking are these records; no contract is
    # executed here (``executed_here`` is False).

    def create_agreement(self, subject, actor, org_id=None,
                         counterparty_ref=None):
        """Create an agreement record. Action: work_write."""
        self._guard(actor, "work_write", "ext_agreement_create", org_id)
        _non_empty(subject, "agreement subject")
        _string_or_none(counterparty_ref, "counterparty_ref")
        with self._lock:
            if org_id is not None:
                self._organization(org_id)
            return self._create(
                "agreement", "agr",
                {"subject": subject, "org_id": org_id,
                 "counterparty_ref": counterparty_ref,
                 "executed_here": False},
                actor, "ext_agreement_create")

    def get_agreement(self, agreement_id, actor=None):
        """Return one agreement record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_agreement_read",
                         agreement_id)
        return self._fetch("agreement", agreement_id)

    def record_agreement_state(self, agreement_id, state_label, actor):
        """Append a reported agreement state label. Action: work_write."""
        self._guard(actor, "work_write", "ext_agreement_state_record",
                    agreement_id)
        _non_empty(state_label, "state_label")
        with self._lock:
            self._get("agreement", agreement_id)
            return self._create(
                "agreement_state", "ags",
                {"agreement_id": agreement_id,
                 "state_label": state_label,
                 "recorded_only": True,
                 "executed_here": False},
                actor, "ext_agreement_state_record")

    def list_agreement_states(self, agreement_id=None, actor=None):
        """Return agreement state records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_agreement_state_read",
                         agreement_id)
        if agreement_id is not None:
            self._get("agreement", agreement_id)
        return self._list("agreement_state", agreement_id=agreement_id)

    def agreement_view(self, agreement_id, actor=None):
        """Agreement plus current state derived at read. Action: work_read.

        ``current_state_label`` is the latest recorded state
        label (the ``_latest_label`` seam); the stored agreement
        record carries no state key.
        """
        self._guard_read(actor, "work_read", "ext_agreement_read",
                         agreement_id)
        with self._lock:
            agreement = self._fetch("agreement", agreement_id)
            states = self._list("agreement_state",
                                agreement_id=agreement_id)
            view = dict(agreement)
            view["current_state_label"] = self._latest_label(
                [s["state_label"] for s in states])
            view["state_count"] = len(states)
            view["derived"] = True
            view["stored"] = False
            return view

    # -- EV charging network management (records form) ----------------
    # A charging station is a record, optionally bound to a core
    # asset. Sessions record energy exactly as reported, in
    # integer watt-hours (the core's usage discipline). Session
    # totals derive at read. Session CONTROL is the entry's
    # execution-shaped component and ships in reference form
    # in-record: a control request is a labeled reference record
    # (``reference_stub: True``, ``controlled_here: False``) --
    # no station is started, stopped, or throttled here.

    def register_charging_station(self, name, actor, asset_id=None,
                                  connector_label=None):
        """Register a charging-station record. Action: usage_write."""
        self._guard(actor, "usage_write", "ext_charging_station_register",
                    asset_id)
        _non_empty(name, "station name")
        _string_or_none(connector_label, "connector_label")
        with self._lock:
            if asset_id is not None:
                self._asset(asset_id)
            return self._create(
                "charging_station", "evs",
                {"name": name, "asset_id": asset_id,
                 "connector_label": connector_label,
                 "controlled_here": False},
                actor, "ext_charging_station_register")

    def get_charging_station(self, station_id, actor=None):
        """Return one charging-station record. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_charging_station_read",
                         station_id)
        return self._fetch("charging_station", station_id)

    def record_charging_session(self, station_id, actor,
                                energy_wh_reported=0, vehicle_ref=None):
        """Record a charging session as reported. Action: usage_write.

        ``energy_wh_reported`` is integer watt-hours exactly as
        reported by the network; this build meters nothing and
        controls no session (``controlled_here`` is False).
        """
        self._guard(actor, "usage_write", "ext_charging_session_record",
                    station_id)
        _nonneg_int(energy_wh_reported, "energy_wh_reported")
        _string_or_none(vehicle_ref, "vehicle_ref")
        with self._lock:
            self._get("charging_station", station_id)
            return self._create(
                "charging_session", "evse",
                {"station_id": station_id,
                 "energy_wh_reported": energy_wh_reported,
                 "vehicle_ref": vehicle_ref,
                 "controlled_here": False,
                 "recorded_only": True},
                actor, "ext_charging_session_record")

    def list_charging_sessions(self, station_id=None, actor=None):
        """Return charging-session records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_charging_session_read",
                         station_id)
        if station_id is not None:
            self._get("charging_station", station_id)
        return self._list("charging_session", station_id=station_id)

    def record_session_control_request(self, station_id, action_label,
                                       actor):
        """Record a session-control request in reference form.

        Action: usage_write. Controlling a live charging session
        is an operation against an external network; this build
        records the request as a labeled reference
        (``reference_stub: True``) and controls nothing
        (``controlled_here`` is False).
        """
        self._guard(actor, "usage_write", "ext_session_control_request",
                    station_id)
        _non_empty(action_label, "action_label")
        with self._lock:
            self._get("charging_station", station_id)
            return self._create(
                "session_control_request", "evc",
                {"station_id": station_id,
                 "action_label": action_label,
                 "reference_stub": True,
                 "controlled_here": False},
                actor, "ext_session_control_request")

    def list_session_control_requests(self, station_id=None, actor=None):
        """Return session-control request records. Action: usage_read."""
        self._guard_read(actor, "usage_read",
                         "ext_session_control_request_read", station_id)
        if station_id is not None:
            self._get("charging_station", station_id)
        return self._list("session_control_request",
                          station_id=station_id)

    def charging_station_view(self, station_id, actor=None):
        """Station plus session rollup derived at read. Action: usage_read.

        ``energy_wh_total_reported`` sums the sessions' reported
        energy -- a sum of reports, derived at read; the stored
        station record carries no total.
        """
        self._guard_read(actor, "usage_read", "ext_charging_station_read",
                         station_id)
        with self._lock:
            station = self._fetch("charging_station", station_id)
            sessions = self._list("charging_session",
                                  station_id=station_id)
            requests = self._list("session_control_request",
                                  station_id=station_id)
            view = dict(station)
            view["session_count"] = len(sessions)
            view["energy_wh_total_reported"] = sum(
                s["energy_wh_reported"] for s in sessions)
            view["control_request_count"] = len(requests)
            view["derived"] = True
            view["stored"] = False
            return view

    # -- Real-estate / facilities portfolio platform (records form) ---
    # Properties and leases are records bound to core
    # organizations and projects. The portfolio view derives its
    # counts at read over those records; no property is managed
    # and no lease is administered beyond its record.

    def register_property(self, name, actor, org_id=None,
                          kind_label=None):
        """Register a property record. Action: asset_write."""
        self._guard(actor, "asset_write", "ext_property_register", org_id)
        _non_empty(name, "property name")
        _string_or_none(kind_label, "kind_label")
        with self._lock:
            if org_id is not None:
                self._organization(org_id)
            return self._create(
                "property", "prop",
                {"name": name, "org_id": org_id,
                 "kind_label": kind_label},
                actor, "ext_property_register")

    def get_property(self, property_id, actor=None):
        """Return one property record. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_property_read",
                         property_id)
        return self._fetch("property", property_id)

    def list_properties(self, org_id=None, actor=None):
        """Return property records. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_property_read", org_id)
        if org_id is not None:
            self._organization(org_id)
        return self._list("property", org_id=org_id)

    def create_lease(self, property_id, actor, tenant_ref=None,
                     project_id=None):
        """Create a lease record over a property. Action: asset_write."""
        self._guard(actor, "asset_write", "ext_lease_create", property_id)
        _string_or_none(tenant_ref, "tenant_ref")
        with self._lock:
            self._get("property", property_id)
            if project_id is not None:
                self._project(project_id)
            return self._create(
                "lease", "lease",
                {"property_id": property_id,
                 "tenant_ref": tenant_ref,
                 "project_id": project_id},
                actor, "ext_lease_create")

    def list_leases(self, property_id=None, actor=None):
        """Return lease records. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_lease_read",
                         property_id)
        if property_id is not None:
            self._get("property", property_id)
        return self._list("lease", property_id=property_id)

    def portfolio_view(self, org_id, actor=None):
        """Portfolio counts for an organization, derived at read.

        Action: asset_read. Counts derive over this surface's
        property and lease records for the organization; nothing
        is stored on any record.
        """
        self._guard_read(actor, "asset_read", "ext_portfolio_read", org_id)
        with self._lock:
            self._organization(org_id)
            properties = self._list("property", org_id=org_id)
            property_ids = {p["id"] for p in properties}
            leases = [l for l in self._list("lease")
                      if l["property_id"] in property_ids]
            view = {"org_id": org_id,
                    "property_count": len(properties),
                    "lease_count": len(leases),
                    "leased_property_count": len(
                        {l["property_id"] for l in leases}),
                    "derived": True,
                    "stored": False}
            return view

    # -- Kiosk & locker access management (records form) --------------
    # Devices, access grants, and access events are records.
    # A grant here is a record of an authorization decision made
    # by the owning platform's operators: it is granted in the
    # record only (``granted_in_record_only`` True) -- no device
    # is unlocked, opened, or administered by this build
    # (``unlocked_here`` / ``device_controlled_here`` False).
    # Access events are reported labels, stored verbatim.

    def register_access_device(self, name, actor, asset_id=None,
                               location_label=None):
        """Register an access-device record. Action: asset_write."""
        self._guard(actor, "asset_write", "ext_access_device_register",
                    asset_id)
        _non_empty(name, "device name")
        _string_or_none(location_label, "location_label")
        with self._lock:
            if asset_id is not None:
                self._asset(asset_id)
            return self._create(
                "access_device", "dev",
                {"name": name, "asset_id": asset_id,
                 "location_label": location_label,
                 "unlocked_here": False,
                 "device_controlled_here": False},
                actor, "ext_access_device_register")

    def get_access_device(self, device_id, actor=None):
        """Return one access-device record. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_access_device_read",
                         device_id)
        return self._fetch("access_device", device_id)

    def record_access_grant(self, device_id, grantee_ref, actor,
                            purpose_label=None):
        """Record an access grant over a device. Action: asset_write.

        The grant exists in this record only; no device is
        unlocked by it (``unlocked_here`` is False).
        ``grantee_ref`` is an opaque reference, never resolved.
        """
        self._guard(actor, "asset_write", "ext_access_grant_record",
                    device_id)
        _non_empty(grantee_ref, "grantee_ref")
        _string_or_none(purpose_label, "purpose_label")
        with self._lock:
            self._get("access_device", device_id)
            return self._create(
                "access_grant", "acg",
                {"device_id": device_id,
                 "grantee_ref": grantee_ref,
                 "purpose_label": purpose_label,
                 "granted_in_record_only": True,
                 "unlocked_here": False},
                actor, "ext_access_grant_record")

    def record_access_event(self, device_id, event_label, actor,
                            grantee_ref=None):
        """Record a reported access event. Action: asset_write.

        The event is the owning platform's report, stored
        verbatim; this build observed nothing at the device
        (``reported_only`` True, ``unlocked_here`` False).
        """
        self._guard(actor, "asset_write", "ext_access_event_record",
                    device_id)
        _non_empty(event_label, "event_label")
        _string_or_none(grantee_ref, "grantee_ref")
        with self._lock:
            self._get("access_device", device_id)
            return self._create(
                "access_event", "ace",
                {"device_id": device_id,
                 "event_label": event_label,
                 "grantee_ref": grantee_ref,
                 "reported_only": True,
                 "unlocked_here": False},
                actor, "ext_access_event_record")

    def access_device_view(self, device_id, actor=None):
        """Device plus grant/event counts derived at read.

        Action: asset_read. The stored device record carries no
        counts.
        """
        self._guard_read(actor, "asset_read", "ext_access_device_read",
                         device_id)
        with self._lock:
            device = self._fetch("access_device", device_id)
            view = dict(device)
            view["grant_count"] = len(self._list(
                "access_grant", device_id=device_id))
            view["event_count"] = len(self._list(
                "access_event", device_id=device_id))
            view["derived"] = True
            view["stored"] = False
            return view

    # -- AI assistants & agents (labeled reference implementation) ----
    # RE-JUDGED from the drafted build-extension disposition
    # (grounds in BATCH.md): the forks' assistant layer -- an
    # agentic platform, natural-language querying over portfolio
    # data, a retrieval-based acquisition assistant -- is a
    # running inference surface, and this substrate holds no
    # model. What ships is the labeled reference form, exactly
    # as the house AI precedent ships it: assistant declarations,
    # request records holding an opaque request reference only
    # (no parameter can accept prompt text -- the record shape
    # has no field that could hold it), and outcome records
    # holding an opaque result reference only. Every record
    # carries ``reference_stub: True``; ``inference_here`` is
    # False throughout. Registration maps to the admin-only core
    # ``workflow_write`` action, as assistants are
    # automation-shaped declarations in this substrate.

    def register_assistant(self, name, actor, capability_label=None):
        """Register an assistant declaration. Action: workflow_write."""
        self._guard(actor, "workflow_write", "ext_assistant_register",
                    None)
        _non_empty(name, "assistant name")
        _string_or_none(capability_label, "capability_label")
        with self._lock:
            return self._create(
                "assistant", "asst",
                {"name": name, "capability_label": capability_label,
                 "reference_stub": True,
                 "inference_here": False},
                actor, "ext_assistant_register")

    def get_assistant(self, assistant_id, actor=None):
        """Return one assistant declaration. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_assistant_read",
                         assistant_id)
        return self._fetch("assistant", assistant_id)

    def list_assistants(self, actor=None):
        """Return assistant declarations. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_assistant_read",
                         None)
        return self._list("assistant")

    def record_assistant_request(self, assistant_id, actor,
                                 request_ref=None):
        """Record an assistant request by opaque reference.

        Action: workflow_write. The request's content lives on
        the owning platform; this record holds only its
        reference (``prompt_held`` is False -- there is no field
        that could hold prompt text).
        """
        self._guard(actor, "workflow_write",
                    "ext_assistant_request_record", assistant_id)
        _string_or_none(request_ref, "request_ref")
        with self._lock:
            self._get("assistant", assistant_id)
            return self._create(
                "assistant_request", "asrq",
                {"assistant_id": assistant_id,
                 "request_ref": request_ref,
                 "reference_stub": True,
                 "prompt_held": False,
                 "inference_here": False},
                actor, "ext_assistant_request_record")

    def record_assistant_outcome(self, request_id, outcome_label, actor,
                                 result_ref=None):
        """Record an assistant outcome exactly as reported.

        Action: workflow_write. The outcome label is the owning
        platform's report; any result is held as an opaque
        ``result_ref`` only -- no result content exists in this
        record (``inference_here`` is False).
        """
        self._guard(actor, "workflow_write",
                    "ext_assistant_outcome_record", request_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._get("assistant_request", request_id)
            return self._create(
                "assistant_outcome", "asoc",
                {"request_id": request_id,
                 "outcome_label": outcome_label,
                 "result_ref": result_ref,
                 "reference_stub": True,
                 "inference_here": False},
                actor, "ext_assistant_outcome_record")

    def list_assistant_requests(self, assistant_id=None, actor=None):
        """Return assistant-request records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read",
                         "ext_assistant_request_read", assistant_id)
        if assistant_id is not None:
            self._get("assistant", assistant_id)
        return self._list("assistant_request", assistant_id=assistant_id)

    # -- Supply-chain risk & payments orchestration (records form) ----
    # Shipments are records. Risk reports carry the reporter's
    # label verbatim -- no risk score is computed anywhere in
    # this surface (``score_computed_here`` is False, and no
    # numeric field exists on a risk record). Payment
    # instructions are records over integer-cent amounts; no
    # payment is executed or settled here (``paid_here`` /
    # ``settled_here`` / ``executed_here`` False). The shipment
    # view derives its totals and latest risk label at read.

    def record_shipment(self, subject, actor, project_id=None,
                        supplier_ref=None):
        """Record a shipment. Action: project_write."""
        self._guard(actor, "project_write", "ext_shipment_record",
                    project_id)
        _non_empty(subject, "shipment subject")
        _string_or_none(supplier_ref, "supplier_ref")
        with self._lock:
            if project_id is not None:
                self._project(project_id)
            return self._create(
                "shipment", "shp",
                {"subject": subject, "project_id": project_id,
                 "supplier_ref": supplier_ref,
                 "paid_here": False},
                actor, "ext_shipment_record")

    def get_shipment(self, shipment_id, actor=None):
        """Return one shipment record. Action: project_read."""
        self._guard_read(actor, "project_read", "ext_shipment_read",
                         shipment_id)
        return self._fetch("shipment", shipment_id)

    def record_risk_report(self, shipment_id, risk_label, actor,
                           source_ref=None):
        """Record a supply-chain risk report verbatim.

        Action: project_write. ``risk_label`` is the reporter's
        label, stored exactly as supplied; no score is computed
        from it or stored beside it (``score_computed_here`` is
        False).
        """
        self._guard(actor, "project_write", "ext_risk_report_record",
                    shipment_id)
        _non_empty(risk_label, "risk_label")
        _string_or_none(source_ref, "source_ref")
        with self._lock:
            self._get("shipment", shipment_id)
            return self._create(
                "risk_report", "rsk",
                {"shipment_id": shipment_id,
                 "risk_label": risk_label,
                 "source_ref": source_ref,
                 "reported_only": True,
                 "score_computed_here": False},
                actor, "ext_risk_report_record")

    def list_risk_reports(self, shipment_id=None, actor=None):
        """Return risk-report records. Action: project_read."""
        self._guard_read(actor, "project_read", "ext_risk_report_read",
                         shipment_id)
        if shipment_id is not None:
            self._get("shipment", shipment_id)
        return self._list("risk_report", shipment_id=shipment_id)

    def record_payment_instruction(self, shipment_id, actor, amount_cents,
                                   payee_ref=None):
        """Record a payment instruction over a shipment.

        Action: usage_write. ``amount_cents`` is a positive
        integer number of cents. The instruction is a record;
        no payment is executed or settled (``paid_here`` /
        ``settled_here`` / ``executed_here`` False).
        """
        self._guard(actor, "usage_write",
                    "ext_payment_instruction_record", shipment_id)
        _pos_int(amount_cents, "amount_cents")
        _string_or_none(payee_ref, "payee_ref")
        with self._lock:
            self._get("shipment", shipment_id)
            return self._create(
                "payment_instruction", "pay",
                {"shipment_id": shipment_id,
                 "amount_cents": amount_cents,
                 "payee_ref": payee_ref,
                 "paid_here": False,
                 "settled_here": False,
                 "executed_here": False},
                actor, "ext_payment_instruction_record")

    def list_payment_instructions(self, shipment_id=None, actor=None):
        """Return payment-instruction records. Action: usage_read."""
        self._guard_read(actor, "usage_read",
                         "ext_payment_instruction_read", shipment_id)
        if shipment_id is not None:
            self._get("shipment", shipment_id)
        return self._list("payment_instruction",
                          shipment_id=shipment_id)

    def shipment_view(self, shipment_id, actor=None):
        """Shipment plus risk/payment rollup derived at read.

        Action: project_read. ``latest_risk_label`` is the
        latest recorded risk label (the ``_latest_label`` seam);
        ``payment_total_cents_reported`` sums the instructions'
        recorded amounts. The stored shipment record carries
        neither.
        """
        self._guard_read(actor, "project_read", "ext_shipment_read",
                         shipment_id)
        with self._lock:
            shipment = self._fetch("shipment", shipment_id)
            risks = self._list("risk_report", shipment_id=shipment_id)
            payments = self._list("payment_instruction",
                                  shipment_id=shipment_id)
            view = dict(shipment)
            view["risk_report_count"] = len(risks)
            view["latest_risk_label"] = self._latest_label(
                [r["risk_label"] for r in risks])
            view["payment_count"] = len(payments)
            view["payment_total_cents_reported"] = sum(
                p["amount_cents"] for p in payments)
            view["derived"] = True
            view["stored"] = False
            return view
