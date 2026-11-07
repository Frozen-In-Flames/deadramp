"""Final GAPS batch, second unit — Remainder Addition verticals.

Clean-room extension surface for the 13 OPEN entries of the
"Remainder Addition — Operations Management L2 (+20 forks)"
section of the repo-root ``GAPS.md``. See ``BATCH-ADDITION.md``
in the group directory for the per-entry disposition. The first
batch unit for this group lives in ``opsmgmt/extensions.py``
(the original Group 36 section); this module is independent of
it and touches nothing in it.

Design, following the core's and the first batch unit's
doctrines:

- This module wraps :class:`opsmgmt.store.OpsStore`; every core
  module and the first unit's ``extensions.py`` are untouched
  (byte-identical). Core records (projects, persons, assets,
  work orders) are always read through the core store's public
  API, never re-implemented.
- Each of the twelve build-extension entries is a named vendor
  vertical carried as a **records surface over the group's own
  substrate concepts** (directory, projects, assets, work
  orders, inspections, usage): domain records with lifecycles
  held as recorded states, and counts/totals derived at read.
  Nothing executes in any domain: no print job prints, no
  shipment moves, no ticket auto-resolves, no package is
  tracked live, no ERP transaction posts. Financial-shaped
  records, where a vertical has them (leases, ERP entries,
  contract finance views), are integer-cents data records with
  recorded states, never execution; floats and booleans are
  rejected at the boundary.
- Case management (EEO/FOIA) follows the data-management
  precedent: case records with evidence held as opaque
  references only (no content field exists), a
  decider-not-opener separation-of-duties seam
  (``_check_decider_not_opener``), and FOIA release/production
  held as a recorded reported state — nothing is released.
- Process mining is reported-analysis records only: counts
  exactly as reported by an external analysis, with
  ``computed_here: False``; no event log is ingested and no
  mining happens here.
- The one stub-engine entry (enterprise asset management
  depth: predictive maintenance / asset health / IoT telemetry
  analytics) ships as a **labeled reference implementation**:
  every record carries ``reference_stub: True``; predictive and
  asset-health claims are recorded as reported labels exactly
  as an external engine reported them, and no prediction,
  health score, or analytics value is computed here.
- RBAC reuses the founding 16-action matrix with **no new
  actions**; each operation maps onto an existing core action,
  checked before any state change or id allocation for
  User-like actors, mirroring the core store's convention
  (plain-string actors carry identity but no role). Successful
  mutations are recorded on the core audit log with a
  ``vert_``-prefixed action name; denied attempts are recorded
  with the same name suffixed ``:denied`` before the denial
  propagates:

  ============================  ===============  ================
  surface                       write action     read action
  ============================  ===============  ================
  print devices                 asset_write      asset_read
  print meter readings          usage_write      usage_read
  print jobs                    work_write       work_read
  supply chain / ITSM / infra   work_write       work_read
  material inventory            usage_write      usage_read
  PLM products / portfolio /    project_write    project_read
  contract progress
  facilities / spaces           asset_write      asset_read
  leases / moves / cases /      work_write       work_read
  mail items / ERP entries
  process models                workflow_write   workflow_read
  reported analyses / Maximo    work_write       report_read
  derived summaries             --               report_read
  ============================  ===============  ================

- Derived values are derived at read and never stored:
  per-vertical summaries (counts by kind/status/stage, meter
  and inventory totals, lease and journal totals in integer
  cents). Stored records carry no derived key; tests pin that.
- All ``*_ref`` parameters naming things outside this build are
  opaque tokens: whitespace, URLs, hostnames, and IP-shaped
  values are rejected at the boundary, so a record cannot
  quietly carry a real system's address, a real identifier, or
  document content. Links into the core substrate use core ids
  (``proj-``, ``per-``, ``ast-``, ``wo-``), validated through
  the core store.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

PRINT_DEVICE_KINDS = ("printer", "scanner", "multifunction", "other")
PRINT_JOB_STATUSES = (
    "recorded_queued",
    "reported_printing",
    "reported_completed",
    "reported_held",
    "reported_cancelled",
)
SHIPMENT_STATUSES = (
    "planned",
    "reported_in_transit",
    "reported_delivered",
    "reported_exception",
    "cancelled",
)
ORDER_STATUSES = ("recorded_open", "reported_fulfilled", "reported_partial", "cancelled")
PLM_STAGES = ("concept", "design", "validation", "production", "retired")
PLM_REVISION_STATUSES = ("draft", "recorded_released", "superseded")
CHANGE_STATUSES = ("recorded_open", "reported_approved", "reported_applied", "cancelled")
TICKET_KINDS = ("incident", "problem", "change", "request")
TICKET_STATUSES = (
    "recorded_open",
    "recorded_in_progress",
    "reported_resolved",
    "recorded_closed",
    "cancelled",
)
TICKET_PRIORITIES = ("low", "normal", "high", "critical")
MAINTENANCE_PLAN_STATUSES = ("active", "suspended", "retired")
ISSUE_STATUSES = ("recorded_open", "recorded_in_progress", "reported_resolved", "recorded_closed")
SPACE_KINDS = ("office", "lab", "warehouse", "meeting", "other")
LEASE_STATUSES = ("recorded_active", "recorded_expired", "recorded_terminated")
MOVE_STATUSES = ("recorded_requested", "reported_scheduled", "reported_completed", "cancelled")
CASE_TYPES = ("eeo", "foia", "general", "investigation", "correspondence")
CASE_STATUSES = ("recorded_open", "recorded_in_review", "recorded_decided", "recorded_closed")
CASE_DECISION_OUTCOMES = ("favorable_reported", "unfavorable_reported", "partial_reported", "dismissed_reported")
FOIA_PRODUCTION_STATUSES = ("reported_prepared", "reported_released", "reported_withheld")
PROCESS_MODEL_KINDS = ("process", "architecture", "value_chain", "other")
INITIATIVE_STATUSES = ("proposed", "active", "reported_complete", "cancelled")
ROADMAP_STATUSES = ("planned", "in_progress_reported", "reported_done", "deferred")
JOURNAL_KINDS = ("debit", "credit")
JOURNAL_STATUSES = ("draft", "recorded", "reported_posted")
PAYROLL_STATUSES = ("recorded", "reported_processed")
MILESTONE_STATUSES = ("planned", "reported_in_progress", "reported_complete", "reported_missed")
HEALTH_LABEL_KINDS = ("asset_health", "predictive_maintenance", "telemetry_analytics")

# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token (same rule as the
    first batch unit): never an address, never an identifier
    issued by a real system."""
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError("%s must be an opaque reference, not an address" % (what,))
    if "." in value:
        raise ValidationError("%s must be an opaque reference, not a hostname" % (what,))
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(options)))
    return value


def _validate_int(value, what, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    if maximum is not None and value > maximum:
        raise ValidationError("%s must be at most %d" % (what, maximum))
    return value


def _validate_cents(value, what):
    """Money as data: integer cents only, never negative here;
    floats and booleans are rejected at the boundary."""
    return _validate_int(value, what, minimum=0)


def _validate_counts(counts, what):
    if not isinstance(counts, dict) or not counts:
        raise ValidationError("%s must be a non-empty object of counts" % (what,))
    cleaned = {}
    for key, value in counts.items():
        _validate_non_empty(key, "%s key" % (what,))
        cleaned[key] = _validate_int(value, "%s[%s]" % (what, key), minimum=0)
    return cleaned


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


def _validate_string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


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


# -- guards (named seams) -------------------------------------------------


def _check_decider_not_opener(opened_by, decider):
    """Separation-of-duties seam for case decisions.

    The actor who records a decision on a case may never be the
    actor who opened the case. This is the load-bearing
    invariant behind ``record_case_decision`` and the fresh
    negative control's mutation target for this unit (see
    tests/README.md).
    """
    if opened_by is not None and decider is not None and opened_by == decider:
        raise ValidationError(
            "case decider must differ from the case's opener (%r)" % (opened_by,)
        )


class OpsVerticals:
    """Remainder-addition verticals over a core OpsStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}
        self._order = []
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
                    "permission denied: no user supplied for %r" % (core_action,))
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

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            record["updated_utc"] = record["created_utc"]
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, collection, **filters):
        result = []
        for key in self._order:
            if key[0] != collection:
                continue
            record = self._records[key]
            if all(record.get(name) == value
                   for name, value in filters.items() if value is not None):
                result.append(copy.deepcopy(record))
        return result

    def _touch(self, record, actor, audit_action):
        record["updated_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    def _core_person(self, person_id):
        return self.store.get_person(person_id)

    def _core_asset(self, asset_id):
        return self.store.get_asset(asset_id)

    def _core_work_order(self, work_order_id):
        return self.store.get_work_order(work_order_id)

    def _core_organization(self, organization_id):
        return self.store.get_organization(organization_id)

    # -- Managed print services engine (Canon, Xerox) -----------------
    # Records form: print-device records over opaque references,
    # integer meter readings, and print-job records whose status
    # is stored exactly as reported. No job prints here.

    def register_print_device(self, device_ref, kind, actor, asset_id=None):
        """Register a managed-print device record. Action: asset_write."""
        self._guard(actor, "asset_write", "vert_print_device_register", device_ref)
        _validate_ref(device_ref, "device_ref")
        _validate_choice(kind, PRINT_DEVICE_KINDS, "kind")
        if asset_id is not None:
            self._core_asset(asset_id)
        return self._create(
            "print_device", "pdv",
            {"device_ref": device_ref, "kind": kind, "asset_id": asset_id,
             "printed_here": False},
            actor, "vert_print_device_register")

    def record_meter_reading(self, device_id, pages, actor, period=None):
        """Record an integer meter reading as reported for a print
        device. Action: usage_write. Readings are data; nothing is
        collected or billed here."""
        self._guard(actor, "usage_write", "vert_meter_record", device_id)
        self._get("print_device", device_id)
        _validate_int(pages, "pages", minimum=0)
        _validate_optional_text(period, "period")
        return self._create(
            "meter_reading", "mtr",
            {"device_id": device_id, "pages": pages, "period": period,
             "collected_here": False},
            actor, "vert_meter_record")

    def record_print_job(self, device_id, actor, pages=1, reported_status="recorded_queued",
                         project_id=None, note=None):
        """Record a print job with its status as reported. Action:
        work_write. The job is a record only: ``printed_here`` is
        False and recording it prints nothing."""
        self._guard(actor, "work_write", "vert_print_job_record", device_id)
        self._get("print_device", device_id)
        _validate_int(pages, "pages", minimum=1)
        _validate_choice(reported_status, PRINT_JOB_STATUSES, "reported_status")
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "print_job", "pjb",
            {"device_id": device_id, "pages": pages,
             "reported_status": reported_status, "project_id": project_id,
             "note": note, "printed_here": False},
            actor, "vert_print_job_record")

    def get_print_device(self, device_id, actor=None):
        self._guard_read(actor, "asset_read", "vert_print_device_read", device_id)
        return self._fetch("print_device", device_id)

    def list_print_devices(self, actor=None, kind=None):
        self._guard_read(actor, "asset_read", "vert_print_device_read")
        return self._list("print_device", kind=kind)

    def list_meter_readings(self, actor=None, device_id=None):
        self._guard_read(actor, "usage_read", "vert_meter_read")
        return self._list("meter_reading", device_id=device_id)

    def list_print_jobs(self, actor=None, device_id=None, reported_status=None):
        self._guard_read(actor, "work_read", "vert_print_job_read")
        return self._list("print_job", device_id=device_id,
                          reported_status=reported_status)

    def print_summary(self, actor=None):
        """Derived print counts: devices by kind, jobs by reported
        status, meter pages summed. Derived at read. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_print_summary")
        devices = self._list("print_device")
        jobs = self._list("print_job")
        readings = self._list("meter_reading")
        by_kind = {}
        for d in devices:
            by_kind[d["kind"]] = by_kind.get(d["kind"], 0) + 1
        by_status = {}
        for j in jobs:
            by_status[j["reported_status"]] = by_status.get(j["reported_status"], 0) + 1
        return {"devices": len(devices), "devices_by_kind": by_kind,
                "jobs": len(jobs), "jobs_by_reported_status": by_status,
                "job_pages_total": sum(j["pages"] for j in jobs),
                "meter_pages_total": sum(r["pages"] for r in readings),
                "printed_here": False}

    # -- Supply chain & logistics execution suite (Manhattan) ---------
    # Records form: shipment, order, and inventory records with
    # recorded/reported states. No shipment moves here.

    def record_shipment(self, shipment_ref, actor, origin_ref=None, destination_ref=None,
                        status="planned", project_id=None):
        """Record a shipment with its status as recorded/reported.
        Action: work_write. ``moved_here`` is False throughout."""
        self._guard(actor, "work_write", "vert_shipment_record", shipment_ref)
        _validate_ref(shipment_ref, "shipment_ref")
        if origin_ref is not None:
            _validate_ref(origin_ref, "origin_ref")
        if destination_ref is not None:
            _validate_ref(destination_ref, "destination_ref")
        _validate_choice(status, SHIPMENT_STATUSES, "status")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "shipment", "shp",
            {"shipment_ref": shipment_ref, "origin_ref": origin_ref,
             "destination_ref": destination_ref, "status": status,
             "project_id": project_id, "moved_here": False},
            actor, "vert_shipment_record")

    def update_shipment_status(self, shipment_id, status, actor):
        """Record a new reported status for a shipment. Action:
        work_write. The status is stored as reported; updating it
        moves nothing."""
        self._guard(actor, "work_write", "vert_shipment_status", shipment_id)
        record = self._get("shipment", shipment_id)
        _validate_choice(status, SHIPMENT_STATUSES, "status")
        with self._lock:
            record["status"] = status
            self._touch(record, actor, "vert_shipment_status")
            return copy.deepcopy(record)

    def record_supply_order(self, order_ref, actor, status="recorded_open", project_id=None):
        """Record a supply/distributed order. Action: work_write."""
        self._guard(actor, "work_write", "vert_supply_order_record", order_ref)
        _validate_ref(order_ref, "order_ref")
        _validate_choice(status, ORDER_STATUSES, "status")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "supply_order", "sod",
            {"order_ref": order_ref, "status": status, "project_id": project_id,
             "fulfilled_here": False},
            actor, "vert_supply_order_record")

    def record_inventory(self, sku_ref, quantity, actor, location_ref=None):
        """Record an inventory quantity for an opaque SKU reference.
        Action: usage_write. Quantity is an integer; floats/bools rejected."""
        self._guard(actor, "usage_write", "vert_inventory_record", sku_ref)
        _validate_ref(sku_ref, "sku_ref")
        _validate_int(quantity, "quantity")
        if location_ref is not None:
            _validate_ref(location_ref, "location_ref")
        return self._create(
            "inventory", "inv",
            {"sku_ref": sku_ref, "quantity": quantity, "location_ref": location_ref},
            actor, "vert_inventory_record")

    def list_shipments(self, actor=None, status=None):
        self._guard_read(actor, "work_read", "vert_shipment_read")
        return self._list("shipment", status=status)

    def list_supply_orders(self, actor=None, status=None):
        self._guard_read(actor, "work_read", "vert_supply_order_read")
        return self._list("supply_order", status=status)

    def list_inventory(self, actor=None, sku_ref=None):
        self._guard_read(actor, "usage_read", "vert_inventory_read")
        return self._list("inventory", sku_ref=sku_ref)

    def supply_chain_summary(self, actor=None):
        """Derived counts: shipments/orders by status, inventory
        quantity summed by SKU. Derived at read. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_supply_summary")
        shipments = self._list("shipment")
        orders = self._list("supply_order")
        inventory = self._list("inventory")
        ship_by = {}
        for s in shipments:
            ship_by[s["status"]] = ship_by.get(s["status"], 0) + 1
        order_by = {}
        for o in orders:
            order_by[o["status"]] = order_by.get(o["status"], 0) + 1
        qty_by_sku = {}
        for i in inventory:
            qty_by_sku[i["sku_ref"]] = qty_by_sku.get(i["sku_ref"], 0) + i["quantity"]
        return {"shipments": len(shipments), "shipments_by_status": ship_by,
                "orders": len(orders), "orders_by_status": order_by,
                "inventory_records": len(inventory),
                "inventory_quantity_by_sku": qty_by_sku, "moved_here": False}

    # -- Product lifecycle management (PLM) platform (PTC) ------------
    # Records form: product records with a lifecycle stage held
    # as data, revision records, and change records. No product
    # data is created or collaborated on here beyond records.

    def create_product(self, product_ref, name, actor, stage="concept", project_id=None):
        """Create a product record with its lifecycle stage as
        data. Action: project_write."""
        self._guard(actor, "project_write", "vert_product_create", product_ref)
        _validate_ref(product_ref, "product_ref")
        _validate_non_empty(name, "product name")
        _validate_choice(stage, PLM_STAGES, "stage")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "product", "prd",
            {"product_ref": product_ref, "name": name, "stage": stage,
             "project_id": project_id},
            actor, "vert_product_create")

    def advance_product_stage(self, product_id, stage, actor):
        """Record a product's lifecycle stage as reported. Action:
        project_write. Any stage may be recorded; the stage is
        data, not a computed lifecycle."""
        self._guard(actor, "project_write", "vert_product_stage", product_id)
        record = self._get("product", product_id)
        _validate_choice(stage, PLM_STAGES, "stage")
        with self._lock:
            record["stage"] = stage
            self._touch(record, actor, "vert_product_stage")
            return copy.deepcopy(record)

    def record_product_revision(self, product_id, revision_label, actor,
                                status="draft", note=None):
        """Record a product revision with its label verbatim.
        Action: project_write."""
        self._guard(actor, "project_write", "vert_revision_record", product_id)
        self._get("product", product_id)
        _validate_non_empty(revision_label, "revision_label")
        _validate_choice(status, PLM_REVISION_STATUSES, "status")
        _validate_optional_text(note, "note")
        return self._create(
            "product_revision", "rev",
            {"product_id": product_id, "revision_label": revision_label,
             "status": status, "note": note},
            actor, "vert_revision_record")

    def record_product_change(self, product_id, summary, actor, status="recorded_open"):
        """Record a lifecycle change request over a product.
        Action: project_write. The change is a record; nothing is
        applied to any product data here."""
        self._guard(actor, "project_write", "vert_change_record", product_id)
        self._get("product", product_id)
        _validate_non_empty(summary, "summary")
        _validate_choice(status, CHANGE_STATUSES, "status")
        return self._create(
            "product_change", "chg",
            {"product_id": product_id, "summary": summary, "status": status,
             "applied_here": False},
            actor, "vert_change_record")

    def get_product(self, product_id, actor=None):
        self._guard_read(actor, "project_read", "vert_product_read", product_id)
        return self._fetch("product", product_id)

    def list_products(self, actor=None, stage=None):
        self._guard_read(actor, "project_read", "vert_product_read")
        return self._list("product", stage=stage)

    def list_product_revisions(self, actor=None, product_id=None):
        self._guard_read(actor, "project_read", "vert_revision_read")
        return self._list("product_revision", product_id=product_id)

    def plm_summary(self, actor=None):
        """Derived counts: products by stage, revisions, changes.
        Derived at read. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_plm_summary")
        products = self._list("product")
        by_stage = {}
        for p in products:
            by_stage[p["stage"]] = by_stage.get(p["stage"], 0) + 1
        return {"products": len(products), "products_by_stage": by_stage,
                "revisions": len(self._list("product_revision")),
                "changes": len(self._list("product_change"))}

    # -- IT service management (ITSM) suite (Ivanti) ------------------
    # Records form: ticket records (incident/problem/change/
    # request) with recorded/reported lifecycle states. No
    # ticket auto-resolves; a change's approval is recorded by
    # an approver who may not be its requester.

    def create_ticket(self, kind, subject, actor, priority="normal",
                      project_id=None, asset_id=None, person_id=None):
        """Create a service ticket record. Action: work_write."""
        self._guard(actor, "work_write", "vert_ticket_create", subject)
        _validate_choice(kind, TICKET_KINDS, "kind")
        _validate_non_empty(subject, "subject")
        _validate_choice(priority, TICKET_PRIORITIES, "priority")
        if project_id is not None:
            self._core_project(project_id)
        if asset_id is not None:
            self._core_asset(asset_id)
        if person_id is not None:
            self._core_person(person_id)
        return self._create(
            "ticket", "tkt",
            {"kind": kind, "subject": subject, "priority": priority,
             "status": "recorded_open", "project_id": project_id,
             "asset_id": asset_id, "person_id": person_id,
             "approved_by": None, "resolved_here": False},
            actor, "vert_ticket_create")

    def transition_ticket(self, ticket_id, to_status, actor):
        """Record a ticket status transition as reported. Action:
        work_write. Terminal recorded_closed/cancelled tickets
        accept no further transition."""
        self._guard(actor, "work_write", "vert_ticket_transition", ticket_id)
        record = self._get("ticket", ticket_id)
        _validate_choice(to_status, TICKET_STATUSES, "to_status")
        if record["status"] in ("recorded_closed", "cancelled"):
            raise ValidationError(
                "ticket %r is %r and accepts no further transition"
                % (ticket_id, record["status"]))
        with self._lock:
            record["status"] = to_status
            self._touch(record, actor, "vert_ticket_transition")
            return copy.deepcopy(record)

    def approve_change(self, ticket_id, actor):
        """Record an approval on a change ticket. Action:
        work_write. Separation of duties: the approver may never
        be the ticket's creator (checked inline; a recorded
        approval changes no system here)."""
        self._guard(actor, "work_write", "vert_ticket_approve", ticket_id)
        record = self._get("ticket", ticket_id)
        if record["kind"] != "change":
            raise ValidationError("only change tickets carry approvals")
        if record["created_by"] is not None and actor_name(actor) == record["created_by"]:
            raise ValidationError(
                "change approver must differ from the ticket's creator (%r)"
                % (record["created_by"],))
        with self._lock:
            record["approved_by"] = actor_name(actor)
            self._touch(record, actor, "vert_ticket_approve")
            return copy.deepcopy(record)

    def get_ticket(self, ticket_id, actor=None):
        self._guard_read(actor, "work_read", "vert_ticket_read", ticket_id)
        return self._fetch("ticket", ticket_id)

    def list_tickets(self, actor=None, kind=None, status=None):
        self._guard_read(actor, "work_read", "vert_ticket_read")
        return self._list("ticket", kind=kind, status=status)

    def itsm_summary(self, actor=None):
        """Derived counts: tickets by kind and by status.
        Derived at read. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_itsm_summary")
        tickets = self._list("ticket")
        by_kind = {}
        by_status = {}
        for t in tickets:
            by_kind[t["kind"]] = by_kind.get(t["kind"], 0) + 1
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        return {"tickets": len(tickets), "tickets_by_kind": by_kind,
                "tickets_by_status": by_status, "resolved_here": False}

    # -- Infrastructure maintenance management system (InfraLink) -----
    # Records form: maintenance-plan records over core assets,
    # issue records, and material-inventory quantity records.
    # Scheduling substance is recorded; nothing is scheduled
    # or dispatched here.

    def create_maintenance_plan(self, name, actor, asset_id=None, interval_days=None,
                                status="active"):
        """Create a maintenance-plan record, optionally over a
        core asset. Action: work_write. ``interval_days``, when
        given, is an integer >= 1 held as data."""
        self._guard(actor, "work_write", "vert_maint_plan_create", name)
        _validate_non_empty(name, "plan name")
        if asset_id is not None:
            self._core_asset(asset_id)
        if interval_days is not None:
            _validate_int(interval_days, "interval_days", minimum=1)
        _validate_choice(status, MAINTENANCE_PLAN_STATUSES, "status")
        return self._create(
            "maintenance_plan", "mpl",
            {"name": name, "asset_id": asset_id, "interval_days": interval_days,
             "status": status, "scheduled_here": False},
            actor, "vert_maint_plan_create")

    def record_maintenance_issue(self, summary, actor, plan_id=None, asset_id=None,
                                 status="recorded_open", work_order_id=None):
        """Record a maintenance issue. Action: work_write.
        Optionally links a core work order, validated through
        the core store."""
        self._guard(actor, "work_write", "vert_issue_record", summary)
        _validate_non_empty(summary, "summary")
        if plan_id is not None:
            self._get("maintenance_plan", plan_id)
        if asset_id is not None:
            self._core_asset(asset_id)
        if work_order_id is not None:
            self._core_work_order(work_order_id)
        _validate_choice(status, ISSUE_STATUSES, "status")
        return self._create(
            "maintenance_issue", "mis",
            {"summary": summary, "plan_id": plan_id, "asset_id": asset_id,
             "status": status, "work_order_id": work_order_id},
            actor, "vert_issue_record")

    def record_material(self, material_ref, quantity, actor, plan_id=None):
        """Record a materials-inventory quantity. Action: usage_write."""
        self._guard(actor, "usage_write", "vert_material_record", material_ref)
        _validate_ref(material_ref, "material_ref")
        _validate_int(quantity, "quantity")
        if plan_id is not None:
            self._get("maintenance_plan", plan_id)
        return self._create(
            "material", "mat",
            {"material_ref": material_ref, "quantity": quantity, "plan_id": plan_id},
            actor, "vert_material_record")

    def list_maintenance_plans(self, actor=None, status=None):
        self._guard_read(actor, "work_read", "vert_maint_plan_read")
        return self._list("maintenance_plan", status=status)

    def list_maintenance_issues(self, actor=None, status=None):
        self._guard_read(actor, "work_read", "vert_issue_read")
        return self._list("maintenance_issue", status=status)

    def list_materials(self, actor=None, material_ref=None):
        self._guard_read(actor, "usage_read", "vert_material_read")
        return self._list("material", material_ref=material_ref)

    def infra_summary(self, actor=None):
        """Derived counts: plans by status, issues by status,
        material quantities summed by reference. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_infra_summary")
        plans = self._list("maintenance_plan")
        issues = self._list("maintenance_issue")
        materials = self._list("material")
        plan_by = {}
        for p in plans:
            plan_by[p["status"]] = plan_by.get(p["status"], 0) + 1
        issue_by = {}
        for i in issues:
            issue_by[i["status"]] = issue_by.get(i["status"], 0) + 1
        qty = {}
        for m in materials:
            qty[m["material_ref"]] = qty.get(m["material_ref"], 0) + m["quantity"]
        return {"plans": len(plans), "plans_by_status": plan_by,
                "issues": len(issues), "issues_by_status": issue_by,
                "material_quantity_by_ref": qty, "scheduled_here": False}

    # -- Facilities & real property management suite / IWMS -----------
    # Records form: facility and space records, lease records
    # (integer cents as data, nothing paid), and move-request
    # records with reported states.

    def create_facility(self, facility_ref, name, actor, project_id=None):
        """Create a facility record. Action: asset_write."""
        self._guard(actor, "asset_write", "vert_facility_create", facility_ref)
        _validate_ref(facility_ref, "facility_ref")
        _validate_non_empty(name, "facility name")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "facility", "fac",
            {"facility_ref": facility_ref, "name": name, "project_id": project_id},
            actor, "vert_facility_create")

    def create_space(self, facility_id, space_ref, actor, kind="office", capacity=None):
        """Create a space record on a facility. Action: asset_write.
        ``capacity``, when given, is an integer >= 0 held as data."""
        self._guard(actor, "asset_write", "vert_space_create", space_ref)
        self._get("facility", facility_id)
        _validate_ref(space_ref, "space_ref")
        _validate_choice(kind, SPACE_KINDS, "kind")
        if capacity is not None:
            _validate_int(capacity, "capacity", minimum=0)
        return self._create(
            "space", "spc",
            {"facility_id": facility_id, "space_ref": space_ref, "kind": kind,
             "capacity": capacity},
            actor, "vert_space_create")

    def record_lease(self, facility_id, actor, amount_cents=0, status="recorded_active",
                     counterparty_ref=None):
        """Record a lease as data: integer cents, recorded status.
        Action: work_write. Nothing is paid or collected here
        (``paid_here`` is False)."""
        self._guard(actor, "work_write", "vert_lease_record", facility_id)
        self._get("facility", facility_id)
        _validate_cents(amount_cents, "amount_cents")
        _validate_choice(status, LEASE_STATUSES, "status")
        if counterparty_ref is not None:
            _validate_ref(counterparty_ref, "counterparty_ref")
        return self._create(
            "lease", "lea",
            {"facility_id": facility_id, "amount_cents": amount_cents,
             "status": status, "counterparty_ref": counterparty_ref,
             "paid_here": False},
            actor, "vert_lease_record")

    def record_move_request(self, facility_id, actor, summary, status="recorded_requested"):
        """Record a move request with its status as reported.
        Action: work_write. No move is performed here."""
        self._guard(actor, "work_write", "vert_move_record", facility_id)
        self._get("facility", facility_id)
        _validate_non_empty(summary, "summary")
        _validate_choice(status, MOVE_STATUSES, "status")
        return self._create(
            "move_request", "mov",
            {"facility_id": facility_id, "summary": summary, "status": status,
             "moved_here": False},
            actor, "vert_move_record")

    def get_facility(self, facility_id, actor=None):
        self._guard_read(actor, "asset_read", "vert_facility_read", facility_id)
        return self._fetch("facility", facility_id)

    def list_facilities(self, actor=None):
        self._guard_read(actor, "asset_read", "vert_facility_read")
        return self._list("facility")

    def list_spaces(self, actor=None, facility_id=None, kind=None):
        self._guard_read(actor, "asset_read", "vert_space_read")
        return self._list("space", facility_id=facility_id, kind=kind)

    def list_leases(self, actor=None, facility_id=None, status=None):
        self._guard_read(actor, "work_read", "vert_lease_read")
        return self._list("lease", facility_id=facility_id, status=status)

    def facilities_summary(self, actor=None):
        """Derived counts: spaces by kind, leases by status, lease
        cents summed (data total, not a payment). Action: report_read."""
        self._guard_read(actor, "report_read", "vert_facilities_summary")
        spaces = self._list("space")
        leases = self._list("lease")
        by_kind = {}
        for s in spaces:
            by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
        by_status = {}
        for lea in leases:
            by_status[lea["status"]] = by_status.get(lea["status"], 0) + 1
        return {"facilities": len(self._list("facility")),
                "spaces": len(spaces), "spaces_by_kind": by_kind,
                "leases": len(leases), "leases_by_status": by_status,
                "lease_cents_total": sum(lea["amount_cents"] for lea in leases),
                "moves": len(self._list("move_request")), "paid_here": False}

    # -- Case management platforms incl. EEO + FOIA -------------------
    # Records form, following the data-management precedent:
    # case records, evidence held as opaque references only
    # (no content field exists on any case record), decision
    # records under the decider-not-opener seam, and FOIA
    # production records whose release state is a recorded
    # reported state — nothing is released or produced here.

    def open_case(self, case_ref, case_type, subject, actor, project_id=None):
        """Open a case record. Action: work_write."""
        self._guard(actor, "work_write", "vert_case_open", case_ref)
        _validate_ref(case_ref, "case_ref")
        _validate_choice(case_type, CASE_TYPES, "case_type")
        _validate_non_empty(subject, "subject")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "case", "cas",
            {"case_ref": case_ref, "case_type": case_type, "subject": subject,
             "status": "recorded_open", "project_id": project_id,
             "released_here": False},
            actor, "vert_case_open")

    def record_case_evidence_ref(self, case_id, evidence_ref, actor, note=None):
        """Record an evidence reference on a case. Action:
        work_write. Only the opaque reference is held; no
        evidence content can be stored on this surface."""
        self._guard(actor, "work_write", "vert_case_evidence", case_id)
        self._get("case", case_id)
        _validate_ref(evidence_ref, "evidence_ref")
        _validate_optional_text(note, "note")
        return self._create(
            "case_evidence", "cev",
            {"case_id": case_id, "evidence_ref": evidence_ref, "note": note,
             "content_held_here": False},
            actor, "vert_case_evidence")

    def transition_case(self, case_id, to_status, actor):
        """Record a case status transition. Action: work_write.
        recorded_closed is terminal."""
        self._guard(actor, "work_write", "vert_case_transition", case_id)
        record = self._get("case", case_id)
        _validate_choice(to_status, CASE_STATUSES, "to_status")
        if record["status"] == "recorded_closed":
            raise ValidationError("case %r is recorded_closed and terminal" % (case_id,))
        with self._lock:
            record["status"] = to_status
            self._touch(record, actor, "vert_case_transition")
            return copy.deepcopy(record)

    def record_case_decision(self, case_id, outcome, actor, note=None):
        """Record a decision on a case. Action: work_write.
        Separation of duties: the decider may never be the
        case's opener (``_check_decider_not_opener``). The
        decision is a record; it effects nothing outside it."""
        self._guard(actor, "work_write", "vert_case_decision", case_id)
        case = self._get("case", case_id)
        _check_decider_not_opener(case["created_by"], actor_name(actor))
        _validate_choice(outcome, CASE_DECISION_OUTCOMES, "outcome")
        _validate_optional_text(note, "note")
        return self._create(
            "case_decision", "cdc",
            {"case_id": case_id, "outcome": outcome, "note": note,
             "effected_here": False},
            actor, "vert_case_decision")

    def record_foia_production(self, case_id, actor, reported_status="reported_prepared",
                               pages_reported=None, note=None):
        """Record a FOIA production state as reported. Action:
        work_write. FOIA cases only. The production/release is a
        recorded reported state: ``released_here`` is False and
        nothing is released or produced by this build."""
        self._guard(actor, "work_write", "vert_foia_production", case_id)
        case = self._get("case", case_id)
        if case["case_type"] != "foia":
            raise ValidationError("FOIA production records require a foia case")
        _validate_choice(reported_status, FOIA_PRODUCTION_STATUSES, "reported_status")
        if pages_reported is not None:
            _validate_int(pages_reported, "pages_reported", minimum=0)
        _validate_optional_text(note, "note")
        return self._create(
            "foia_production", "foi",
            {"case_id": case_id, "reported_status": reported_status,
             "pages_reported": pages_reported, "note": note,
             "released_here": False},
            actor, "vert_foia_production")

    def get_case(self, case_id, actor=None):
        self._guard_read(actor, "work_read", "vert_case_read", case_id)
        return self._fetch("case", case_id)

    def list_cases(self, actor=None, case_type=None, status=None):
        self._guard_read(actor, "work_read", "vert_case_read")
        return self._list("case", case_type=case_type, status=status)

    def list_case_evidence(self, actor=None, case_id=None):
        self._guard_read(actor, "work_read", "vert_case_evidence_read")
        return self._list("case_evidence", case_id=case_id)

    def list_case_decisions(self, actor=None, case_id=None):
        self._guard_read(actor, "work_read", "vert_case_decision_read")
        return self._list("case_decision", case_id=case_id)

    def list_foia_productions(self, actor=None, case_id=None):
        self._guard_read(actor, "work_read", "vert_foia_read")
        return self._list("foia_production", case_id=case_id)

    def case_summary(self, actor=None):
        """Derived counts: cases by type and status, decisions,
        FOIA productions by reported status. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_case_summary")
        cases = self._list("case")
        by_type = {}
        by_status = {}
        for c in cases:
            by_type[c["case_type"]] = by_type.get(c["case_type"], 0) + 1
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        productions = self._list("foia_production")
        prod_by = {}
        for p in productions:
            prod_by[p["reported_status"]] = prod_by.get(p["reported_status"], 0) + 1
        return {"cases": len(cases), "cases_by_type": by_type,
                "cases_by_status": by_status,
                "evidence_refs": len(self._list("case_evidence")),
                "decisions": len(self._list("case_decision")),
                "foia_productions": len(productions),
                "foia_productions_by_reported_status": prod_by,
                "released_here": False}

    # -- Business process modeling, process mining & EA ---------------
    # Records form: process/architecture model records with
    # elements held as data, plus reported-analysis records.
    # Process mining is reported-analysis records only: no
    # event log is ingested and nothing is mined here.

    def create_process_model(self, model_ref, name, actor, kind="process",
                             element_labels=None, project_id=None):
        """Create a process/architecture model record. Action:
        workflow_write (configuration, as the core workflow
        registry). Elements are labels held as data."""
        self._guard(actor, "workflow_write", "vert_model_create", model_ref)
        _validate_ref(model_ref, "model_ref")
        _validate_non_empty(name, "model name")
        _validate_choice(kind, PROCESS_MODEL_KINDS, "kind")
        element_labels = _validate_string_list(element_labels, "element_labels")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "process_model", "pmd",
            {"model_ref": model_ref, "name": name, "kind": kind,
             "element_labels": element_labels, "project_id": project_id,
             "version": 1, "modeled_here": True, "executed_here": False},
            actor, "vert_model_create")

    def update_process_model(self, model_id, actor, element_labels=None):
        """Replace a model record's element labels, bumping its
        version. Action: workflow_write. Data only."""
        self._guard(actor, "workflow_write", "vert_model_update", model_id)
        record = self._get("process_model", model_id)
        cleaned = None
        if element_labels is not None:
            cleaned = _validate_string_list(element_labels, "element_labels")
        with self._lock:
            if cleaned is not None:
                record["element_labels"] = cleaned
            record["version"] += 1
            self._touch(record, actor, "vert_model_update")
            return copy.deepcopy(record)

    def record_reported_analysis(self, model_id, counts, actor, note=None):
        """Record a process-mining / architecture analysis
        exactly as reported by an external tool. Action:
        work_write. Counts are stored as reported with
        ``computed_here: False``; no event log is ingested and
        no mining happens here."""
        self._guard(actor, "work_write", "vert_analysis_record", model_id)
        self._get("process_model", model_id)
        counts = _validate_counts(counts, "counts")
        _validate_optional_text(note, "note")
        return self._create(
            "reported_analysis", "ana",
            {"model_id": model_id, "counts": counts, "note": note,
             "computed_here": False,
             "mined_here": False},
            actor, "vert_analysis_record")

    def get_process_model(self, model_id, actor=None):
        self._guard_read(actor, "workflow_read", "vert_model_read", model_id)
        return self._fetch("process_model", model_id)

    def list_process_models(self, actor=None, kind=None):
        self._guard_read(actor, "workflow_read", "vert_model_read")
        return self._list("process_model", kind=kind)

    def list_reported_analyses(self, actor=None, model_id=None):
        self._guard_read(actor, "report_read", "vert_analysis_read")
        return self._list("reported_analysis", model_id=model_id)

    def process_summary(self, actor=None):
        """Derived counts: models by kind, analyses. The model's
        stored record carries no analysis count (derived at
        read). Action: report_read."""
        self._guard_read(actor, "report_read", "vert_process_summary")
        models = self._list("process_model")
        by_kind = {}
        for m in models:
            by_kind[m["kind"]] = by_kind.get(m["kind"], 0) + 1
        return {"models": len(models), "models_by_kind": by_kind,
                "analyses": len(self._list("reported_analysis")),
                "mined_here": False, "computed_here": False}

    # -- Mail & package operations (Pitney Bowes) ---------------------
    # Records form: mail/package item records with recorded/
    # reported states and locker records. No package is tracked
    # live and nothing is shipped here.

    def record_mail_item(self, item_ref, actor, kind="package", status="recorded_received",
                         carrier_ref=None, project_id=None):
        """Record a mail/package item with its status as
        recorded/reported. Action: work_write. ``kind`` is
        ``letter`` or ``package``. No live tracking exists here
        (``tracked_live_here`` is False)."""
        self._guard(actor, "work_write", "vert_mail_record", item_ref)
        _validate_ref(item_ref, "item_ref")
        if kind not in ("letter", "package"):
            raise ValidationError("kind must be one of letter, package")
        _validate_choice(status, ("recorded_received", "reported_in_transit",
                                  "reported_delivered", "reported_returned"), "status")
        if carrier_ref is not None:
            _validate_ref(carrier_ref, "carrier_ref")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "mail_item", "mai",
            {"item_ref": item_ref, "kind": kind, "status": status,
             "carrier_ref": carrier_ref, "project_id": project_id,
             "tracked_live_here": False, "shipped_here": False},
            actor, "vert_mail_record")

    def update_mail_item_status(self, item_id, status, actor):
        """Record a new reported status for a mail item. Action:
        work_write. Stored as reported; delivers nothing."""
        self._guard(actor, "work_write", "vert_mail_status", item_id)
        record = self._get("mail_item", item_id)
        _validate_choice(status, ("recorded_received", "reported_in_transit",
                                  "reported_delivered", "reported_returned"), "status")
        with self._lock:
            record["status"] = status
            self._touch(record, actor, "vert_mail_status")
            return copy.deepcopy(record)

    def register_locker(self, locker_ref, actor, facility_ref=None):
        """Register a smart-locker record. Action: work_write."""
        self._guard(actor, "work_write", "vert_locker_register", locker_ref)
        _validate_ref(locker_ref, "locker_ref")
        if facility_ref is not None:
            _validate_ref(facility_ref, "facility_ref")
        return self._create(
            "locker", "lck",
            {"locker_ref": locker_ref, "facility_ref": facility_ref,
             "operated_here": False},
            actor, "vert_locker_register")

    def list_mail_items(self, actor=None, status=None, kind=None):
        self._guard_read(actor, "work_read", "vert_mail_read")
        return self._list("mail_item", status=status, kind=kind)

    def list_lockers(self, actor=None):
        self._guard_read(actor, "work_read", "vert_locker_read")
        return self._list("locker")

    def mail_summary(self, actor=None):
        """Derived counts: items by kind and status, lockers.
        Derived at read. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_mail_summary")
        items = self._list("mail_item")
        by_kind = {}
        by_status = {}
        for i in items:
            by_kind[i["kind"]] = by_kind.get(i["kind"], 0) + 1
            by_status[i["status"]] = by_status.get(i["status"], 0) + 1
        return {"items": len(items), "items_by_kind": by_kind,
                "items_by_status": by_status,
                "lockers": len(self._list("locker")),
                "tracked_live_here": False}

    # -- Strategic portfolio & agile planning (Clarity, Rally) --------
    # Records form: portfolio, initiative, and roadmap-item
    # records. Priority is stored verbatim as data; no score,
    # ranking, or prioritization is computed here.

    def create_portfolio(self, name, actor, project_id=None):
        """Create a portfolio record. Action: project_write."""
        self._guard(actor, "project_write", "vert_portfolio_create", name)
        _validate_non_empty(name, "portfolio name")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "portfolio", "ptf",
            {"name": name, "project_id": project_id},
            actor, "vert_portfolio_create")

    def create_initiative(self, portfolio_id, name, actor, status="proposed",
                          priority_label=None, project_id=None):
        """Create an initiative record on a portfolio. Action:
        project_write. ``priority_label`` is stored verbatim as
        data; nothing ranks it."""
        self._guard(actor, "project_write", "vert_initiative_create", portfolio_id)
        self._get("portfolio", portfolio_id)
        _validate_non_empty(name, "initiative name")
        _validate_choice(status, INITIATIVE_STATUSES, "status")
        _validate_optional_text(priority_label, "priority_label")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "initiative", "ini",
            {"portfolio_id": portfolio_id, "name": name, "status": status,
             "priority_label": priority_label, "project_id": project_id,
             "ranked_here": False},
            actor, "vert_initiative_create")

    def record_roadmap_item(self, portfolio_id, title, actor, status="planned",
                            iteration_label=None):
        """Record a roadmap item. Action: project_write."""
        self._guard(actor, "project_write", "vert_roadmap_record", portfolio_id)
        self._get("portfolio", portfolio_id)
        _validate_non_empty(title, "title")
        _validate_choice(status, ROADMAP_STATUSES, "status")
        _validate_optional_text(iteration_label, "iteration_label")
        return self._create(
            "roadmap_item", "rdm",
            {"portfolio_id": portfolio_id, "title": title, "status": status,
             "iteration_label": iteration_label},
            actor, "vert_roadmap_record")

    def get_portfolio(self, portfolio_id, actor=None):
        self._guard_read(actor, "project_read", "vert_portfolio_read", portfolio_id)
        return self._fetch("portfolio", portfolio_id)

    def list_portfolios(self, actor=None):
        self._guard_read(actor, "project_read", "vert_portfolio_read")
        return self._list("portfolio")

    def list_initiatives(self, actor=None, portfolio_id=None, status=None):
        self._guard_read(actor, "project_read", "vert_initiative_read")
        return self._list("initiative", portfolio_id=portfolio_id, status=status)

    def list_roadmap_items(self, actor=None, portfolio_id=None):
        self._guard_read(actor, "project_read", "vert_roadmap_read")
        return self._list("roadmap_item", portfolio_id=portfolio_id)

    def portfolio_summary(self, actor=None):
        """Derived counts: initiatives by status, roadmap items
        by status. No score or ranking key appears. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_portfolio_summary")
        initiatives = self._list("initiative")
        roadmap = self._list("roadmap_item")
        init_by = {}
        for i in initiatives:
            init_by[i["status"]] = init_by.get(i["status"], 0) + 1
        road_by = {}
        for r in roadmap:
            road_by[r["status"]] = road_by.get(r["status"], 0) + 1
        return {"portfolios": len(self._list("portfolio")),
                "initiatives": len(initiatives), "initiatives_by_status": init_by,
                "roadmap_items": len(roadmap), "roadmap_items_by_status": road_by,
                "ranked_here": False}

    # -- Back-office ERP suite (Accenture) ----------------------------
    # Records form: journal-entry records in integer cents with
    # recorded states and payroll records over core persons.
    # No transaction posts here: a ``reported_posted`` status is
    # a state reported by an external ERP, stored as reported,
    # with ``posted_here`` False on every record.

    def record_journal_entry(self, account_ref, kind, amount_cents, actor,
                             status="recorded", project_id=None, note=None):
        """Record one journal line as data. Action: work_write.
        Amount is integer cents; floats/bools rejected."""
        self._guard(actor, "work_write", "vert_journal_record", account_ref)
        _validate_ref(account_ref, "account_ref")
        _validate_choice(kind, JOURNAL_KINDS, "kind")
        _validate_cents(amount_cents, "amount_cents")
        _validate_choice(status, JOURNAL_STATUSES, "status")
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "journal_entry", "jrn",
            {"account_ref": account_ref, "kind": kind,
             "amount_cents": amount_cents, "status": status,
             "project_id": project_id, "note": note, "posted_here": False},
            actor, "vert_journal_record")

    def record_payroll_record(self, person_id, actor, amount_cents=0,
                              status="recorded", period=None):
        """Record a payroll-shaped data record over a core
        person. Action: work_write. Integer cents as data;
        nothing is paid here (``paid_here`` is False)."""
        self._guard(actor, "work_write", "vert_payroll_record", person_id)
        self._core_person(person_id)
        _validate_cents(amount_cents, "amount_cents")
        _validate_choice(status, PAYROLL_STATUSES, "status")
        _validate_optional_text(period, "period")
        return self._create(
            "payroll_record", "pay",
            {"person_id": person_id, "amount_cents": amount_cents,
             "status": status, "period": period, "paid_here": False},
            actor, "vert_payroll_record")

    def list_journal_entries(self, actor=None, account_ref=None, kind=None):
        self._guard_read(actor, "work_read", "vert_journal_read")
        return self._list("journal_entry", account_ref=account_ref, kind=kind)

    def list_payroll_records(self, actor=None, person_id=None):
        self._guard_read(actor, "work_read", "vert_payroll_read")
        return self._list("payroll_record", person_id=person_id)

    def erp_summary(self, actor=None):
        """Derived ERP totals: debit and credit cents summed at
        read (data totals, not postings), payroll cents summed.
        The stored entries carry no total. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_erp_summary")
        entries = self._list("journal_entry")
        payroll = self._list("payroll_record")
        debits = sum(e["amount_cents"] for e in entries if e["kind"] == "debit")
        credits = sum(e["amount_cents"] for e in entries if e["kind"] == "credit")
        return {"journal_entries": len(entries),
                "debit_cents_total": debits, "credit_cents_total": credits,
                "payroll_records": len(payroll),
                "payroll_cents_total": sum(p["amount_cents"] for p in payroll),
                "posted_here": False, "paid_here": False}

    # -- Contract progress management application (iSite) -------------
    # Records form: contract records over core projects,
    # milestone records with reported states, progress-report
    # records whose percent is stored exactly as reported, and
    # finance-view records in integer cents as data.

    def create_contract(self, contract_ref, name, actor, project_id=None,
                        org_id=None):
        """Create a contract-progress record. Action: project_write.
        ``org_id``, when given, must reference an existing core
        organization, validated through the core store."""
        self._guard(actor, "project_write", "vert_contract_create", contract_ref)
        _validate_ref(contract_ref, "contract_ref")
        _validate_non_empty(name, "contract name")
        if project_id is not None:
            self._core_project(project_id)
        if org_id is not None:
            self._core_organization(org_id)
        return self._create(
            "contract", "ctr",
            {"contract_ref": contract_ref, "name": name,
             "project_id": project_id, "org_id": org_id},
            actor, "vert_contract_create")

    def record_milestone(self, contract_id, title, actor, status="planned",
                         due_at=None):
        """Record a contract milestone with its status as
        reported. Action: project_write."""
        self._guard(actor, "project_write", "vert_milestone_record", contract_id)
        self._get("contract", contract_id)
        _validate_non_empty(title, "title")
        _validate_choice(status, MILESTONE_STATUSES, "status")
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        return self._create(
            "milestone", "mil",
            {"contract_id": contract_id, "title": title, "status": status,
             "due_at": due_at},
            actor, "vert_milestone_record")

    def record_progress_report(self, contract_id, percent_reported, actor, note=None):
        """Record a progress report: the percent exactly as
        reported by the contract team. Action: project_write.
        Integer 0-100; ``computed_here`` is False — no progress
        is calculated from milestones here."""
        self._guard(actor, "project_write", "vert_progress_record", contract_id)
        self._get("contract", contract_id)
        _validate_int(percent_reported, "percent_reported", minimum=0, maximum=100)
        _validate_optional_text(note, "note")
        return self._create(
            "progress_report", "prg",
            {"contract_id": contract_id, "percent_reported": percent_reported,
             "note": note, "computed_here": False},
            actor, "vert_progress_record")

    def record_contract_finance(self, contract_id, amount_cents, actor,
                                label="reported_amount", project_id=None):
        """Record a contract finance view line as data. Action:
        project_write. Integer cents; nothing is billed or paid."""
        self._guard(actor, "project_write", "vert_contract_finance", contract_id)
        self._get("contract", contract_id)
        _validate_non_empty(label, "label")
        _validate_cents(amount_cents, "amount_cents")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "contract_finance", "fin",
            {"contract_id": contract_id, "label": label,
             "amount_cents": amount_cents, "project_id": project_id,
             "paid_here": False},
            actor, "vert_contract_finance")

    def get_contract(self, contract_id, actor=None):
        self._guard_read(actor, "project_read", "vert_contract_read", contract_id)
        return self._fetch("contract", contract_id)

    def list_contracts(self, actor=None, project_id=None):
        self._guard_read(actor, "project_read", "vert_contract_read")
        return self._list("contract", project_id=project_id)

    def list_milestones(self, actor=None, contract_id=None, status=None):
        self._guard_read(actor, "project_read", "vert_milestone_read")
        return self._list("milestone", contract_id=contract_id, status=status)

    def list_progress_reports(self, actor=None, contract_id=None):
        self._guard_read(actor, "project_read", "vert_progress_read")
        return self._list("progress_report", contract_id=contract_id)

    def contract_summary(self, actor=None):
        """Derived counts: milestones by status, finance cents
        summed as data. Progress percents are never averaged or
        otherwise computed here. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_contract_summary")
        milestones = self._list("milestone")
        by_status = {}
        for m in milestones:
            by_status[m["status"]] = by_status.get(m["status"], 0) + 1
        finance = self._list("contract_finance")
        return {"contracts": len(self._list("contract")),
                "milestones": len(milestones), "milestones_by_status": by_status,
                "progress_reports": len(self._list("progress_report")),
                "finance_records": len(finance),
                "finance_cents_total": sum(f["amount_cents"] for f in finance),
                "paid_here": False}

    # -- Enterprise asset management depth (IBM Maximo) — STUB --------
    # Labeled reference implementation: predictive-maintenance,
    # asset-health, and telemetry-analytics claims are recorded
    # as reported labels / reported counts from an external
    # engine. Every record carries ``reference_stub: True``; no
    # prediction, health score, or analytics value is computed
    # here, and no record shape carries a score field.

    def register_health_reference(self, asset_ref, kind, reported_label, actor,
                                  asset_id=None):
        """Register a reference record of an external asset-health
        / predictive-maintenance label. Action: work_write.
        The label is stored exactly as reported; the record
        carries ``reference_stub: True``, ``predicted_here:
        False``, and ``computed_here: False``."""
        self._guard(actor, "work_write", "vert_health_reference", asset_ref)
        _validate_ref(asset_ref, "asset_ref")
        _validate_choice(kind, HEALTH_LABEL_KINDS, "kind")
        _validate_non_empty(reported_label, "reported_label")
        if asset_id is not None:
            self._core_asset(asset_id)
        return self._create(
            "health_reference", "hlr",
            {"asset_ref": asset_ref, "kind": kind,
             "reported_label": reported_label, "asset_id": asset_id,
             "reference_stub": True, "predicted_here": False,
             "computed_here": False},
            actor, "vert_health_reference")

    def record_telemetry_analytics_reference(self, asset_ref, counts, actor, note=None):
        """Record a reference to external telemetry analytics:
        counts exactly as reported. Action: work_write. Carries
        ``reference_stub: True`` and ``reference_transport:
        True``; no telemetry is collected and no analytics is
        computed here."""
        self._guard(actor, "work_write", "vert_telemetry_reference", asset_ref)
        _validate_ref(asset_ref, "asset_ref")
        counts = _validate_counts(counts, "counts")
        _validate_optional_text(note, "note")
        return self._create(
            "telemetry_analytics_reference", "tar",
            {"asset_ref": asset_ref, "counts": counts, "note": note,
             "reference_stub": True, "reference_transport": True,
             "computed_here": False, "collected_here": False},
            actor, "vert_telemetry_reference")

    def list_health_references(self, actor=None, kind=None):
        self._guard_read(actor, "report_read", "vert_health_read")
        return self._list("health_reference", kind=kind)

    def list_telemetry_analytics_references(self, actor=None, asset_ref=None):
        self._guard_read(actor, "report_read", "vert_telemetry_ref_read")
        return self._list("telemetry_analytics_reference", asset_ref=asset_ref)

    def maximo_summary(self, actor=None):
        """Derived counts only: health references by kind,
        analytics references. No score, rate, or grade key
        appears anywhere in the view. Action: report_read."""
        self._guard_read(actor, "report_read", "vert_maximo_summary")
        health = self._list("health_reference")
        by_kind = {}
        for h in health:
            by_kind[h["kind"]] = by_kind.get(h["kind"], 0) + 1
        return {"health_references": len(health),
                "health_references_by_kind": by_kind,
                "telemetry_analytics_references":
                    len(self._list("telemetry_analytics_reference")),
                "predicted_here": False, "computed_here": False}
