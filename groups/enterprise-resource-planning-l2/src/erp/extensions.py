"""Final GAPS batch extensions for the Enterprise Resource
Planning L2 singleton build.

Clean-room, standard-library-only extensions for the 16 Extended
gaps the union spec named but the core did not implement. See
``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`ErpStore`; the core
  modules are untouched. Organization and referenced-record
  existence is enforced by delegating to the core store's public
  read operations, and role permissions are enforced with
  :mod:`erp.access` exactly as the core enforces them for
  User-like actors (a plain-string actor carries identity only).
- All money is integer cents: a boolean, float, or string where
  an amount is required raises ``ValidationError`` at the
  boundary; a failed operation consumes no id and changes
  nothing. Quantities and minutes are integers under the same
  rule.
- People, suppliers, and accounts are opaque ``*_ref`` strings
  only. No record shape in this module can hold a name, email,
  phone number, or any real identifier, and nothing computes a
  score, rating, or ranking.
- Derived values are derived at read time and never stored:
  portal layouts, schema-on-read rows, close balances,
  consolidation totals, settlement state, production completion,
  exchange feeds, pipeline counts, schedule coverage and
  conflicts, payroll gross/net, dashboard metrics, plan
  actuals/variance/forecast, and risk exposure. Stored records
  carry no derived key; tests pin that.
- Every successful mutation is recorded on the core store's
  audit log (when one is attached), with action names prefixed
  ``ext_``. Denied attempts are the HTTP layer's responsibility,
  as in the core, so nothing is recorded twice.
- Nothing here executes against an external system. The four
  stub-engine entries (identity federation, orchestration
  runtime, API gateway runtime, expense policy enforcement)
  ship as labeled reference implementations: every record they
  create carries ``reference_stub: True`` and status
  ``recorded_reference_only``. Per PLATFORM-LAYER.md decision 1,
  the federation records are configuration hooks only -- this
  substrate is never an identity provider and authenticates
  no one.
"""

import re
import threading
from datetime import datetime, timezone

from .access import PERMISSIONS, require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

LAKE_SOURCES = (
    "ledger_entries",
    "purchase_orders",
    "expense_reports",
    "persons",
    "time_entries",
    "payroll_runs",
    "inventory_items",
    "documents",
)
NOTICE_KINDS = ("demand", "advance_ship_notice", "collaboration")
TALENT_STAGES = ("identified", "hired", "developed", "rewarded", "retained")
METRIC_KINDS = (
    "organization_counts",
    "ledger_totals",
    "purchase_order_totals",
    "expense_totals",
    "payroll_totals",
    "inventory_levels",
)
CHECK_OUTCOMES = ("pass", "fail")
STUB_STATUS = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _integer(value, field, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (field, minimum))
    return value


def _date(value, field):
    if not isinstance(value, str) \
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD)" % field)
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            "%s is not a real calendar date: %r" % (field, value))
    return value.strip()


def _check_instruction_within_total(instructed_cents, amount_cents,
                                    total_cents):
    """Settlement guard seam: the source-to-settle rule, stated
    once. Recorded payment instructions against a settle cycle
    may never instruct more than the purchase order's derived
    total: ``instructed_cents`` already recorded plus the new
    ``amount_cents`` must not exceed ``total_cents``. Raises
    :class:`ValidationError` on any violation. Recording an
    instruction disburses nothing; this guard is about what the
    records may claim, not about moving money."""
    if instructed_cents + amount_cents > total_cents:
        raise ValidationError(
            "payment instructions would total %d, above the "
            "purchase order total %d"
            % (instructed_cents + amount_cents, total_cents))


class ErpExtensions:
    """Final-GAPS-batch extension surface over an ``ErpStore``."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        self._portal_pages = {}
        self._lake_datasets = {}
        self._close_periods = {}
        self._settle_cycles = {}
        self._payment_instructions = {}
        self._production_orders = {}
        self._production_outputs = {}
        self._supplier_notices = {}
        self._talent_cycles = {}
        self._schedules = {}
        self._shifts = {}
        self._payroll_calculations = {}
        self._dashboards = {}
        self._plans = {}
        self._risk_records = {}
        self._control_checks = {}
        self._federation_records = {}
        self._orchestration_records = {}
        self._gateway_routes = {}
        self._expense_policies = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(
                actor, "ext_" + action, target, details)

    def _org(self, actor, org_id):
        return self.store.get_organization(actor, org_id)

    @staticmethod
    def _fetch(table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("no such %s: %r" % (what, record_id))
        return record

    def _check_unique(self, table, org_id, field, value, what):
        for existing in table.values():
            if existing["org_id"] == org_id and existing[field] == value:
                raise ValidationError(
                    "%s %r already exists in organization %s"
                    % (what, value, org_id))

    def _person(self, actor, org_id, person_ref):
        for person in self.store.list_persons(actor, org_id=org_id):
            if person["person_ref"] == person_ref:
                return person
        raise NotFoundError(
            "no person record with ref %r in organization %s"
            % (person_ref, org_id))

    @staticmethod
    def _copy(record):
        copied = dict(record)
        for key, value in copied.items():
            if isinstance(value, list):
                copied[key] = [dict(v) if isinstance(v, dict) else v
                               for v in value]
        return copied

    # -- suite platform & portal presentation layer -----------------------
    # In-substrate form: page and widget configuration records,
    # and a layout derived at read from them. No page is rendered
    # and no portal is served; the presentation surface itself
    # stays with the embedding organization's platform.

    def create_portal_page(self, actor, org_id, page_ref, title_label):
        """Record a portal page configuration for an
        organization: an opaque page reference and a title
        label. Widget configuration records attach to the page;
        the layout is derived at read, never stored."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(page_ref, "page_ref")
        _text(title_label, "title_label")
        with self._lock:
            self._check_unique(self._portal_pages, org_id, "page_ref",
                               page_ref, "page_ref")
            page = {
                "id": self._mint("por-"),
                "org_id": org_id,
                "page_ref": page_ref,
                "title_label": title_label,
                "widgets": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portal_pages[page["id"]] = page
        self._audit(actor, "portal_page_create", page["id"],
                    {"org_id": org_id, "page_ref": page_ref})
        return self._copy(page)

    def add_portal_widget(self, actor, page_id, widget_ref, kind_label,
                          position):
        """Attach a widget configuration record to a portal
        page: an opaque widget reference, a caller-stated kind
        label, and an integer position (unique within the page).
        Positions order the derived layout; the stored widget
        list keeps recording order."""
        self._check_role(actor, "register")
        page = self._fetch(self._portal_pages, page_id, "portal page")
        _text(widget_ref, "widget_ref")
        _text(kind_label, "kind_label")
        _integer(position, "position", minimum=1)
        with self._lock:
            for widget in page["widgets"]:
                if widget["widget_ref"] == widget_ref:
                    raise ValidationError(
                        "widget_ref %r already exists on page %s"
                        % (widget_ref, page_id))
                if widget["position"] == position:
                    raise ValidationError(
                        "position %d is already taken on page %s"
                        % (position, page_id))
            page["widgets"].append({
                "widget_ref": widget_ref,
                "kind_label": kind_label,
                "position": position,
            })
        self._audit(actor, "portal_widget_add", page_id,
                    {"widget_ref": widget_ref})
        return self._copy(page)

    def portal_layout(self, actor, org_id):
        """The portal layout for an organization, derived at
        read from the page and widget configuration records:
        each page's widgets ordered by recorded position. The
        derivation is returned, never stored."""
        self._check_role(actor, "read")
        self._org(actor, org_id)
        layout = []
        for page in self._portal_pages.values():
            if page["org_id"] != org_id:
                continue
            widgets = sorted(page["widgets"],
                             key=lambda w: w["position"])
            layout.append({
                "page_ref": page["page_ref"],
                "title_label": page["title_label"],
                "widgets": [dict(w) for w in widgets],
            })
        return {"org_id": org_id, "pages": layout}

    def list_portal_pages(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(p) for p in self._portal_pages.values()
                if org_id is None or p["org_id"] == org_id]

    # -- data lake & schema-on-read engine --------------------------------
    # In-substrate form: dataset records naming a core record
    # kind and a caller-declared field list. The schema is
    # applied at read over the core store's current records;
    # nothing is copied into a lake and no row is materialized.

    def register_lake_dataset(self, actor, org_id, dataset_ref,
                              source_kind, fields):
        """Register a data-lake dataset record: an opaque
        dataset reference, one of the core record kinds, and
        the declared schema -- a non-empty list of unique field
        names applied at read. The stored record holds the
        declaration only; it holds no rows."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(dataset_ref, "dataset_ref")
        if source_kind not in LAKE_SOURCES:
            raise ValidationError(
                "unknown lake source kind: %r" % (source_kind,))
        if not isinstance(fields, (list, tuple)) or not fields:
            raise ValidationError("fields must be a non-empty list")
        validated_fields = []
        for field in fields:
            _text(field, "field")
            if field in validated_fields:
                raise ValidationError("duplicate field: %r" % (field,))
            validated_fields.append(field)
        with self._lock:
            self._check_unique(self._lake_datasets, org_id,
                               "dataset_ref", dataset_ref, "dataset_ref")
            dataset = {
                "id": self._mint("lak-"),
                "org_id": org_id,
                "dataset_ref": dataset_ref,
                "source_kind": source_kind,
                "fields": validated_fields,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._lake_datasets[dataset["id"]] = dataset
        self._audit(actor, "lake_dataset_register", dataset["id"],
                    {"org_id": org_id, "dataset_ref": dataset_ref})
        return self._copy(dataset)

    def _lake_rows(self, actor, dataset):
        org_id = dataset["org_id"]
        source = dataset["source_kind"]
        if source == "ledger_entries":
            records = self.store.list_ledger_entries(actor, org_id=org_id)
        elif source == "purchase_orders":
            records = self.store.list_purchase_orders(actor, org_id=org_id)
        elif source == "expense_reports":
            records = self.store.list_expense_reports(actor, org_id=org_id)
        elif source == "persons":
            records = self.store.list_persons(actor, org_id=org_id)
        elif source == "time_entries":
            records = self.store.list_time_entries(actor, org_id=org_id)
        elif source == "payroll_runs":
            records = self.store.list_payroll_runs(actor, org_id=org_id)
        elif source == "inventory_items":
            records = self.store.list_inventory_items(actor, org_id=org_id)
        else:  # documents
            records = self.store.list_documents(actor, org_id=org_id)
        fields = dataset["fields"]
        return [
            {field: record[field] for field in fields if field in record}
            for record in records
        ]

    def lake_query(self, actor, dataset_id):
        """Schema-on-read over the core store's CURRENT records
        for the dataset's organization: each record projected
        onto the declared fields, derived at read. Because
        nothing is materialized, records recorded after the
        dataset was registered appear in later queries."""
        self._check_role(actor, "read")
        dataset = self._fetch(self._lake_datasets, dataset_id,
                              "lake dataset")
        rows = self._lake_rows(actor, dataset)
        return {
            "dataset_id": dataset_id,
            "dataset_ref": dataset["dataset_ref"],
            "source_kind": dataset["source_kind"],
            "fields": list(dataset["fields"]),
            "rows": rows,
            "row_count": len(rows),
            "materialized": False,
        }

    def list_lake_datasets(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(d) for d in self._lake_datasets.values()
                if org_id is None or d["org_id"] == org_id]

    # -- financial close & consolidation engine ---------------------------
    # In-substrate form: a close record referencing ledger
    # entries of one organization, and derivations over them.
    # Balance is answered by the same arithmetic the core's
    # balanced-entry seam enforces; no close process executes
    # and nothing posts anywhere.

    def create_close_period(self, actor, org_id, close_ref, period_label,
                            entry_ids):
        """Record a financial close period: an opaque close
        reference, a period label, and the ledger entry ids the
        close covers. Every entry must exist and belong to the
        organization. The close record stores the references
        only; its balance is derived at read."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(close_ref, "close_ref")
        _text(period_label, "period_label")
        if not isinstance(entry_ids, (list, tuple)) or not entry_ids:
            raise ValidationError("entry_ids must be a non-empty list")
        validated_ids = []
        for entry_id in entry_ids:
            entry = self.store.get_ledger_entry(actor, entry_id)
            if entry["org_id"] != org_id:
                raise ValidationError(
                    "ledger entry %s does not belong to organization %s"
                    % (entry_id, org_id))
            if entry_id in validated_ids:
                raise ValidationError(
                    "duplicate entry id: %r" % (entry_id,))
            validated_ids.append(entry_id)
        with self._lock:
            self._check_unique(self._close_periods, org_id, "close_ref",
                               close_ref, "close_ref")
            close = {
                "id": self._mint("clo-"),
                "org_id": org_id,
                "close_ref": close_ref,
                "period_label": period_label,
                "entry_ids": validated_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._close_periods[close["id"]] = close
        self._audit(actor, "close_period_create", close["id"],
                    {"org_id": org_id, "close_ref": close_ref})
        return self._copy(close)

    def close_status(self, actor, close_id):
        """The close derivation, at read: totals over the
        covered ledger entries and whether they balance in
        aggregate (debits equal credits, total positive)."""
        self._check_role(actor, "read")
        close = self._fetch(self._close_periods, close_id, "close period")
        debits = 0
        credits = 0
        for entry_id in close["entry_ids"]:
            view = self.store.get_ledger_entry(actor, entry_id)
            debits += view["total_debits_cents"]
            credits += view["total_credits_cents"]
        return {
            "close_id": close_id,
            "close_ref": close["close_ref"],
            "period_label": close["period_label"],
            "entry_count": len(close["entry_ids"]),
            "total_debits_cents": debits,
            "total_credits_cents": credits,
            "balanced": debits == credits and debits > 0,
        }

    def consolidation_view(self, actor, org_ids):
        """Consolidation derived at read across organizations:
        per-account debit / credit / net totals summed over
        every ledger entry of every listed organization, rows
        sorted by account reference, plus grand totals. Nothing
        is stored; the view answers from the current entries."""
        self._check_role(actor, "read")
        if not isinstance(org_ids, (list, tuple)) or not org_ids:
            raise ValidationError("org_ids must be a non-empty list")
        seen = []
        for org_id in org_ids:
            self._org(actor, org_id)
            if org_id in seen:
                raise ValidationError("duplicate org id: %r" % (org_id,))
            seen.append(org_id)
        per_account = {}
        for org_id in seen:
            for view in self.store.list_ledger_entries(actor,
                                                       org_id=org_id):
                for line in view["lines"]:
                    row = per_account.setdefault(
                        line["account_ref"],
                        {"account_ref": line["account_ref"],
                         "debit_cents": 0, "credit_cents": 0})
                    row["debit_cents"] += line["debit_cents"]
                    row["credit_cents"] += line["credit_cents"]
        rows = []
        for account_ref in sorted(per_account):
            row = per_account[account_ref]
            row["net_cents"] = row["debit_cents"] - row["credit_cents"]
            rows.append(row)
        return {
            "org_ids": seen,
            "accounts": rows,
            "total_debits_cents": sum(r["debit_cents"] for r in rows),
            "total_credits_cents": sum(r["credit_cents"] for r in rows),
        }

    def list_close_periods(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(c) for c in self._close_periods.values()
                if org_id is None or c["org_id"] == org_id]

    # -- source-to-settle execution engine --------------------------------
    # In-substrate form: a settle cycle over a recorded purchase
    # order, payment *instruction* records capped by the guard
    # seam at the order's derived total, and match state derived
    # from the order's recorded lifecycle. Recording an
    # instruction disburses nothing and pays no one.

    def create_settle_cycle(self, actor, org_id, cycle_ref, po_id):
        """Record a source-to-settle cycle over a purchase
        order of the organization. The cycle record stores the
        order reference only; its totals and match state are
        derived at read from the order record."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(cycle_ref, "cycle_ref")
        order = self.store.get_purchase_order(actor, po_id)
        if order["org_id"] != org_id:
            raise ValidationError(
                "purchase order %s does not belong to organization %s"
                % (po_id, org_id))
        with self._lock:
            self._check_unique(self._settle_cycles, org_id, "cycle_ref",
                               cycle_ref, "cycle_ref")
            cycle = {
                "id": self._mint("set-"),
                "org_id": org_id,
                "cycle_ref": cycle_ref,
                "po_id": po_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._settle_cycles[cycle["id"]] = cycle
        self._audit(actor, "settle_cycle_create", cycle["id"],
                    {"org_id": org_id, "cycle_ref": cycle_ref})
        return self._copy(cycle)

    def _instructed_cents(self, cycle_id):
        return sum(
            i["amount_cents"] for i in self._payment_instructions.values()
            if i["cycle_id"] == cycle_id)

    def record_payment_instruction(self, actor, cycle_id, instruction_ref,
                                   amount_cents):
        """Record a payment instruction against a settle cycle:
        an opaque instruction reference and an integer-cent
        amount. The guard seam
        :func:`_check_instruction_within_total` refuses, whole,
        any instruction that would take the cycle's instructed
        total above the purchase order's derived total.
        Recording an instruction performs no payment."""
        self._check_role(actor, "record")
        cycle = self._fetch(self._settle_cycles, cycle_id, "settle cycle")
        _text(instruction_ref, "instruction_ref")
        _integer(amount_cents, "amount_cents", minimum=1)
        order = self.store.get_purchase_order(actor, cycle["po_id"])
        with self._lock:
            for existing in self._payment_instructions.values():
                if existing["cycle_id"] == cycle_id \
                        and existing["instruction_ref"] == instruction_ref:
                    raise ValidationError(
                        "instruction_ref %r already exists on cycle %s"
                        % (instruction_ref, cycle_id))
            _check_instruction_within_total(
                self._instructed_cents(cycle_id), amount_cents,
                order["total_cents"])
            instruction = {
                "id": self._mint("pin-"),
                "cycle_id": cycle_id,
                "org_id": cycle["org_id"],
                "instruction_ref": instruction_ref,
                "amount_cents": amount_cents,
                "payment_executed": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payment_instructions[instruction["id"]] = instruction
        self._audit(actor, "payment_instruction_record", instruction["id"],
                    {"cycle_id": cycle_id,
                     "instruction_ref": instruction_ref})
        return self._copy(instruction)

    def settle_status(self, actor, cycle_id):
        """The settlement derivation, at read: the order's
        recorded lifecycle state, its derived total, the
        instructed total, the remaining amount, and the match
        state -- matched once the order's recorded state is
        ``received`` or ``closed``, awaiting receipt while it is
        ``open``. Nothing here is stored on the cycle record."""
        self._check_role(actor, "read")
        cycle = self._fetch(self._settle_cycles, cycle_id, "settle cycle")
        order = self.store.get_purchase_order(actor, cycle["po_id"])
        instructed = self._instructed_cents(cycle_id)
        return {
            "cycle_id": cycle_id,
            "cycle_ref": cycle["cycle_ref"],
            "po_id": cycle["po_id"],
            "po_status": order["status"],
            "po_total_cents": order["total_cents"],
            "instructed_cents": instructed,
            "remaining_cents": order["total_cents"] - instructed,
            "match_state": ("awaiting_receipt"
                            if order["status"] == "open" else "matched"),
        }

    def list_settle_cycles(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(c) for c in self._settle_cycles.values()
                if org_id is None or c["org_id"] == org_id]

    def list_payment_instructions(self, actor, cycle_id):
        self._check_role(actor, "read")
        self._fetch(self._settle_cycles, cycle_id, "settle cycle")
        return [self._copy(i)
                for i in self._payment_instructions.values()
                if i["cycle_id"] == cycle_id]

    # -- manufacturing production engine ----------------------------------
    # In-substrate form: production orders over the core's
    # inventory records, with output recorded through recorded
    # inventory adjustments on the core store. No planning,
    # scheduling, configuration, or shop-floor machinery is
    # performed; completion is derived from recorded outputs.

    def create_production_order(self, actor, org_id, order_ref, item_id,
                                planned_quantity):
        """Record a production order: an opaque order reference,
        the inventory item it produces, and a planned quantity
        (a positive integer). The order record stores the plan
        only; produced quantity is derived from output
        records."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(order_ref, "order_ref")
        _integer(planned_quantity, "planned_quantity", minimum=1)
        item = None
        for candidate in self.store.list_inventory_items(actor,
                                                         org_id=org_id):
            if candidate["id"] == item_id:
                item = candidate
                break
        if item is None:
            raise NotFoundError(
                "no inventory item %r in organization %s"
                % (item_id, org_id))
        with self._lock:
            self._check_unique(self._production_orders, org_id,
                               "order_ref", order_ref, "order_ref")
            order = {
                "id": self._mint("prd-"),
                "org_id": org_id,
                "order_ref": order_ref,
                "item_id": item_id,
                "planned_quantity": planned_quantity,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._production_orders[order["id"]] = order
        self._audit(actor, "production_order_create", order["id"],
                    {"org_id": org_id, "order_ref": order_ref})
        return self._copy(order)

    def _produced_quantity(self, order_id):
        return sum(
            o["quantity"] for o in self._production_outputs.values()
            if o["order_id"] == order_id)

    def record_production_output(self, actor, order_id, quantity):
        """Record production output against an order: a
        positive integer quantity that may not take the
        produced total above the planned quantity (refused
        whole). The output is also applied to the core
        inventory record through the core store's recorded
        adjustment, so stock reflects recorded production."""
        self._check_role(actor, "record")
        order = self._fetch(self._production_orders, order_id,
                            "production order")
        _integer(quantity, "quantity", minimum=1)
        with self._lock:
            produced = self._produced_quantity(order_id)
            if produced + quantity > order["planned_quantity"]:
                raise ValidationError(
                    "output of %d would take order %s to %d, above "
                    "the planned %d"
                    % (quantity, order_id, produced + quantity,
                       order["planned_quantity"]))
            self.store.adjust_inventory(actor, order["item_id"], quantity)
            output = {
                "id": self._mint("out-"),
                "order_id": order_id,
                "org_id": order["org_id"],
                "quantity": quantity,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._production_outputs[output["id"]] = output
        self._audit(actor, "production_output_record", output["id"],
                    {"order_id": order_id, "quantity": quantity})
        return self._copy(output)

    def production_status(self, actor, order_id):
        """The production derivation, at read: produced and
        remaining quantities summed from output records, the
        completion flag, and the item's current quantity on
        hand from the core inventory record."""
        self._check_role(actor, "read")
        order = self._fetch(self._production_orders, order_id,
                            "production order")
        produced = self._produced_quantity(order_id)
        on_hand = None
        for item in self.store.list_inventory_items(
                actor, org_id=order["org_id"]):
            if item["id"] == order["item_id"]:
                on_hand = item["quantity_on_hand"]
                break
        return {
            "order_id": order_id,
            "order_ref": order["order_ref"],
            "item_id": order["item_id"],
            "planned_quantity": order["planned_quantity"],
            "produced_quantity": produced,
            "remaining_quantity": order["planned_quantity"] - produced,
            "complete": produced >= order["planned_quantity"],
            "inventory_quantity_on_hand": on_hand,
        }

    def list_production_orders(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(o) for o in self._production_orders.values()
                if org_id is None or o["org_id"] == org_id]

    # -- supplier exchange network ----------------------------------------
    # In-substrate form: exchange notice records (demand and
    # Advance Ship Notice publications, collaboration notes)
    # and a feed derived at read from them plus the
    # organization's purchase order records for that supplier.
    # No notice leaves this substrate: every notice record
    # carries reference_transport: True and delivery_state
    # "recorded_only".

    def publish_supplier_notice(self, actor, org_id, notice_ref,
                                supplier_ref, kind, label):
        """Record a supplier-exchange notice for a supplier
        named by opaque reference. ``kind`` is one of the
        exchange's own record kinds -- ``demand``,
        ``advance_ship_notice``, ``collaboration``. The record
        is the publication's in-substrate form; delivering it
        to a live network is the embedding organization's
        transport, not this build's."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(notice_ref, "notice_ref")
        _text(supplier_ref, "supplier_ref")
        if kind not in NOTICE_KINDS:
            raise ValidationError("unknown notice kind: %r" % (kind,))
        _text(label, "label")
        with self._lock:
            self._check_unique(self._supplier_notices, org_id,
                               "notice_ref", notice_ref, "notice_ref")
            notice = {
                "id": self._mint("not-"),
                "org_id": org_id,
                "notice_ref": notice_ref,
                "supplier_ref": supplier_ref,
                "kind": kind,
                "label": label,
                "reference_transport": True,
                "delivery_state": "recorded_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._supplier_notices[notice["id"]] = notice
        self._audit(actor, "supplier_notice_publish", notice["id"],
                    {"org_id": org_id, "notice_ref": notice_ref})
        return self._copy(notice)

    def supplier_exchange_feed(self, actor, org_id, supplier_ref):
        """The exchange feed for one supplier, derived at read:
        its recorded notices, plus summaries of the
        organization's purchase orders naming that supplier
        (reference and recorded status, total derived by the
        core at read)."""
        self._check_role(actor, "read")
        self._org(actor, org_id)
        _text(supplier_ref, "supplier_ref")
        notices = [
            self._copy(n) for n in self._supplier_notices.values()
            if n["org_id"] == org_id and n["supplier_ref"] == supplier_ref
        ]
        orders = [
            {"po_ref": o["po_ref"], "status": o["status"],
             "total_cents": o["total_cents"]}
            for o in self.store.list_purchase_orders(actor, org_id=org_id)
            if o["supplier_ref"] == supplier_ref
        ]
        return {"org_id": org_id, "supplier_ref": supplier_ref,
                "notices": notices, "purchase_orders": orders}

    def list_supplier_notices(self, actor, org_id=None, supplier_ref=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(n) for n in self._supplier_notices.values()
                if (org_id is None or n["org_id"] == org_id)
                and (supplier_ref is None
                     or n["supplier_ref"] == supplier_ref)]

    # -- talent management engine -----------------------------------------
    # In-substrate form: talent cycle records over person
    # records, in the fork's own stage vocabulary (identify /
    # hire / develop / reward / retain), moving forward only
    # through recorded actions. Stages are recorded states,
    # never scores or rankings.

    def create_talent_cycle(self, actor, org_id, person_ref, cycle_ref):
        """Open a talent cycle for a person record: an opaque
        cycle reference. The cycle starts at the ``identified``
        stage; later stages arrive through recorded actions."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        self._person(actor, org_id, person_ref)
        _text(cycle_ref, "cycle_ref")
        with self._lock:
            self._check_unique(self._talent_cycles, org_id, "cycle_ref",
                               cycle_ref, "cycle_ref")
            cycle = {
                "id": self._mint("tal-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "cycle_ref": cycle_ref,
                "stage": "identified",
                "stage_history": [{
                    "stage": "identified",
                    "by": actor_name(actor),
                    "utc": _utc_now(),
                }],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._talent_cycles[cycle["id"]] = cycle
        self._audit(actor, "talent_cycle_create", cycle["id"],
                    {"org_id": org_id, "cycle_ref": cycle_ref})
        return self._copy(cycle)

    def record_talent_stage(self, actor, cycle_id, stage):
        """Record a talent cycle's stage transition by recorded
        action. Stages move strictly forward in the vocabulary
        order; skipping ahead is allowed, going back or
        repeating the current stage is not."""
        self._check_role(actor, "record")
        cycle = self._fetch(self._talent_cycles, cycle_id, "talent cycle")
        if stage not in TALENT_STAGES:
            raise ValidationError("unknown talent stage: %r" % (stage,))
        with self._lock:
            current = TALENT_STAGES.index(cycle["stage"])
            if TALENT_STAGES.index(stage) <= current:
                raise ValidationError(
                    "talent cycle %s is at stage %r; stage %r is not "
                    "forward" % (cycle_id, cycle["stage"], stage))
            cycle["stage"] = stage
            cycle["stage_history"].append({
                "stage": stage,
                "by": actor_name(actor),
                "utc": _utc_now(),
            })
        self._audit(actor, "talent_stage_record", cycle_id,
                    {"stage": stage})
        return self._copy(cycle)

    def talent_pipeline(self, actor, org_id):
        """The pipeline derivation, at read: how many of the
        organization's talent cycles currently sit at each
        stage, every stage named including zeros. Counts only."""
        self._check_role(actor, "read")
        self._org(actor, org_id)
        counts = {stage: 0 for stage in TALENT_STAGES}
        for cycle in self._talent_cycles.values():
            if cycle["org_id"] == org_id:
                counts[cycle["stage"]] += 1
        return {"org_id": org_id, "cycles_by_stage": counts}

    def list_talent_cycles(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(c) for c in self._talent_cycles.values()
                if org_id is None or c["org_id"] == org_id]

    # -- workforce scheduling optimizer -----------------------------------
    # In-substrate form: schedule records holding caller-recorded
    # demand (required minutes per date) and recorded shifts.
    # What the build computes is a deterministic derivation over
    # those records -- coverage, gaps, and double-bookings. It
    # performs no optimization search and claims none: method is
    # labeled deterministic_coverage in every view.

    def create_schedule(self, actor, org_id, schedule_ref, demands):
        """Record a workforce schedule: an opaque schedule
        reference and the recorded demand -- a non-empty list
        of ``{work_date, required_minutes}`` with at most one
        demand per date. Demand is caller-recorded; deriving
        demand from forecasts is not performed."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(schedule_ref, "schedule_ref")
        if not isinstance(demands, (list, tuple)) or not demands:
            raise ValidationError("demands must be a non-empty list")
        validated = []
        seen_dates = []
        for demand in demands:
            if not isinstance(demand, dict):
                raise ValidationError("each demand must be an object")
            day = _date(demand.get("work_date"), "work_date")
            required = _integer(demand.get("required_minutes"),
                                "required_minutes", minimum=1)
            if day in seen_dates:
                raise ValidationError("duplicate demand date: %r" % (day,))
            seen_dates.append(day)
            validated.append({"work_date": day,
                              "required_minutes": required})
        with self._lock:
            self._check_unique(self._schedules, org_id, "schedule_ref",
                               schedule_ref, "schedule_ref")
            schedule = {
                "id": self._mint("sch-"),
                "org_id": org_id,
                "schedule_ref": schedule_ref,
                "demands": validated,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._schedules[schedule["id"]] = schedule
        self._audit(actor, "schedule_create", schedule["id"],
                    {"org_id": org_id, "schedule_ref": schedule_ref})
        return self._copy(schedule)

    def add_shift(self, actor, schedule_id, person_ref, work_date,
                  minutes):
        """Record a shift on a schedule for a person record of
        the schedule's organization: a calendar date and whole
        minutes (1 to 1440). Recording a shift assigns nothing
        and notifies no one; coverage is derived at read."""
        self._check_role(actor, "record")
        schedule = self._fetch(self._schedules, schedule_id, "schedule")
        self._person(actor, schedule["org_id"], person_ref)
        day = _date(work_date, "work_date")
        _integer(minutes, "minutes", minimum=1)
        if minutes > 1440:
            raise ValidationError("minutes must not exceed 1440")
        with self._lock:
            shift = {
                "id": self._mint("shf-"),
                "schedule_id": schedule_id,
                "org_id": schedule["org_id"],
                "person_ref": person_ref,
                "work_date": day,
                "minutes": minutes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._shifts[shift["id"]] = shift
        self._audit(actor, "shift_add", shift["id"],
                    {"schedule_id": schedule_id,
                     "person_ref": person_ref})
        return self._copy(shift)

    def schedule_view(self, actor, schedule_id):
        """The scheduling derivation, at read: per demand date,
        required minutes, scheduled minutes summed from shift
        records, and the coverage gap; double-bookings (a
        person with more than one shift on one date) flagged
        deterministically; and per-person total minutes. All of
        it is computed from the records, none of it stored, and
        no assignment is proposed or optimized."""
        self._check_role(actor, "read")
        schedule = self._fetch(self._schedules, schedule_id, "schedule")
        shifts = [s for s in self._shifts.values()
                  if s["schedule_id"] == schedule_id]
        coverage = []
        for demand in sorted(schedule["demands"],
                             key=lambda d: d["work_date"]):
            scheduled = sum(s["minutes"] for s in shifts
                            if s["work_date"] == demand["work_date"])
            coverage.append({
                "work_date": demand["work_date"],
                "required_minutes": demand["required_minutes"],
                "scheduled_minutes": scheduled,
                "gap_minutes": demand["required_minutes"] - scheduled,
            })
        by_person_date = {}
        per_person = {}
        for shift in shifts:
            key = (shift["person_ref"], shift["work_date"])
            by_person_date[key] = by_person_date.get(key, 0) + 1
            per_person[shift["person_ref"]] = (
                per_person.get(shift["person_ref"], 0) + shift["minutes"])
        conflicts = [
            {"person_ref": person_ref, "work_date": day,
             "shift_count": count}
            for (person_ref, day), count in sorted(by_person_date.items())
            if count > 1
        ]
        return {
            "schedule_id": schedule_id,
            "schedule_ref": schedule["schedule_ref"],
            "method": "deterministic_coverage",
            "coverage": coverage,
            "conflicts": conflicts,
            "per_person": [
                {"person_ref": ref, "total_minutes": per_person[ref]}
                for ref in sorted(per_person)
            ],
        }

    def list_schedules(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(s) for s in self._schedules.values()
                if org_id is None or s["org_id"] == org_id]

    # -- payroll calculation engine ---------------------------------------
    # In-substrate form: a calculation record holding inputs
    # only -- a person, an inclusive date range, an hourly rate
    # in integer cents, and deduction lines in basis points of
    # gross. Gross, deductions, and net are derived at read
    # from the core's time entries, so a calculation answers
    # from the current records and stores no computed amount.
    # Disbursement is not performed.

    def create_payroll_calculation(self, actor, org_id, person_ref,
                                   calc_ref, from_date, to_date,
                                   hourly_rate_cents, deductions):
        """Record a payroll calculation's inputs. Deductions
        are a list of ``{label, rate_bps}`` lines whose rates
        sum to at most 10000 bps of gross. The record stores
        inputs only -- no minutes, gross, or net key exists on
        it; the amounts live in the derived view."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        self._person(actor, org_id, person_ref)
        _text(calc_ref, "calc_ref")
        start = _date(from_date, "from_date")
        end = _date(to_date, "to_date")
        if end < start:
            raise ValidationError("to_date must not precede from_date")
        _integer(hourly_rate_cents, "hourly_rate_cents", minimum=0)
        if not isinstance(deductions, (list, tuple)):
            raise ValidationError("deductions must be a list")
        validated = []
        total_bps = 0
        for line in deductions:
            if not isinstance(line, dict):
                raise ValidationError("each deduction must be an object")
            label = _text(line.get("label"), "label")
            rate_bps = _integer(line.get("rate_bps"), "rate_bps",
                                minimum=0)
            if rate_bps > 10000:
                raise ValidationError("rate_bps must not exceed 10000")
            total_bps += rate_bps
            validated.append({"label": label, "rate_bps": rate_bps})
        if total_bps > 10000:
            raise ValidationError(
                "deduction rates total %d bps, above 10000" % total_bps)
        with self._lock:
            self._check_unique(self._payroll_calculations, org_id,
                               "calc_ref", calc_ref, "calc_ref")
            calculation = {
                "id": self._mint("cal-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "calc_ref": calc_ref,
                "from_date": start,
                "to_date": end,
                "hourly_rate_cents": hourly_rate_cents,
                "deductions": validated,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payroll_calculations[calculation["id"]] = calculation
        self._audit(actor, "payroll_calculation_create", calculation["id"],
                    {"org_id": org_id, "calc_ref": calc_ref})
        return self._copy(calculation)

    def payroll_calculation_view(self, actor, calc_id):
        """The payroll derivation, at read: minutes summed
        from the person's core time entries inside the recorded
        date range; gross as ``minutes * hourly_rate_cents //
        60`` (integer floor arithmetic, stated so the rounding
        is part of the contract); each deduction as ``gross *
        rate_bps // 10000``; net as gross minus total
        deductions. Derived from current records every time."""
        self._check_role(actor, "read")
        calculation = self._fetch(self._payroll_calculations, calc_id,
                                  "payroll calculation")
        minutes = sum(
            t["minutes"]
            for t in self.store.list_time_entries(
                actor, org_id=calculation["org_id"],
                person_ref=calculation["person_ref"])
            if calculation["from_date"] <= t["work_date"]
            <= calculation["to_date"])
        gross = (minutes * calculation["hourly_rate_cents"]) // 60
        deduction_rows = [
            {"label": line["label"], "rate_bps": line["rate_bps"],
             "amount_cents": (gross * line["rate_bps"]) // 10000}
            for line in calculation["deductions"]
        ]
        total_deductions = sum(r["amount_cents"] for r in deduction_rows)
        return {
            "calc_id": calc_id,
            "calc_ref": calculation["calc_ref"],
            "person_ref": calculation["person_ref"],
            "from_date": calculation["from_date"],
            "to_date": calculation["to_date"],
            "total_minutes": minutes,
            "hourly_rate_cents": calculation["hourly_rate_cents"],
            "gross_cents": gross,
            "deductions": deduction_rows,
            "total_deductions_cents": total_deductions,
            "net_cents": gross - total_deductions,
        }

    def list_payroll_calculations(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(c)
                for c in self._payroll_calculations.values()
                if org_id is None or c["org_id"] == org_id]

    # -- business intelligence platform -----------------------------------
    # In-substrate form: dashboard definition records naming
    # metric kinds, and metric values derived at read from the
    # core store's records for the dashboard's organization.
    # There is no semantic layer, warehouse, or external data;
    # the metrics are counts and recorded totals over this
    # build's own records, computed the same way every time.

    def create_dashboard(self, actor, org_id, dashboard_ref, title_label,
                         metric_kinds):
        """Record a dashboard definition: an opaque reference,
        a title label, and a non-empty list of unique metric
        kinds from the build's own metric vocabulary. The
        definition stores no metric values."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(dashboard_ref, "dashboard_ref")
        _text(title_label, "title_label")
        if not isinstance(metric_kinds, (list, tuple)) or not metric_kinds:
            raise ValidationError("metric_kinds must be a non-empty list")
        validated = []
        for kind in metric_kinds:
            if kind not in METRIC_KINDS:
                raise ValidationError("unknown metric kind: %r" % (kind,))
            if kind in validated:
                raise ValidationError("duplicate metric kind: %r" % (kind,))
            validated.append(kind)
        with self._lock:
            self._check_unique(self._dashboards, org_id, "dashboard_ref",
                               dashboard_ref, "dashboard_ref")
            dashboard = {
                "id": self._mint("dsh-"),
                "org_id": org_id,
                "dashboard_ref": dashboard_ref,
                "title_label": title_label,
                "metric_kinds": validated,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[dashboard["id"]] = dashboard
        self._audit(actor, "dashboard_create", dashboard["id"],
                    {"org_id": org_id, "dashboard_ref": dashboard_ref})
        return self._copy(dashboard)

    def _metric(self, actor, org_id, kind):
        if kind == "organization_counts":
            return {
                "applications": len(self.store.list_applications(
                    actor, org_id=org_id)),
                "persons": len(self.store.list_persons(
                    actor, org_id=org_id)),
                "assets": len(self.store.list_assets(
                    actor, org_id=org_id)),
                "documents": len(self.store.list_documents(
                    actor, org_id=org_id)),
                "inventory_items": len(self.store.list_inventory_items(
                    actor, org_id=org_id)),
            }
        if kind == "ledger_totals":
            entries = self.store.list_ledger_entries(actor, org_id=org_id)
            return {
                "entry_count": len(entries),
                "total_debits_cents": sum(
                    e["total_debits_cents"] for e in entries),
                "total_credits_cents": sum(
                    e["total_credits_cents"] for e in entries),
            }
        if kind == "purchase_order_totals":
            orders = self.store.list_purchase_orders(actor, org_id=org_id)
            return {
                "order_count": len(orders),
                "total_cents": sum(o["total_cents"] for o in orders),
            }
        if kind == "expense_totals":
            reports = self.store.list_expense_reports(actor, org_id=org_id)
            return {
                "report_count": len(reports),
                "total_cents": sum(r["total_cents"] for r in reports),
            }
        if kind == "payroll_totals":
            runs = self.store.list_payroll_runs(actor, org_id=org_id)
            return {
                "run_count": len(runs),
                "gross_cents": sum(r["gross_cents"] for r in runs),
            }
        # inventory_levels
        items = self.store.list_inventory_items(actor, org_id=org_id)
        return {
            "item_count": len(items),
            "quantity_on_hand": sum(i["quantity_on_hand"] for i in items),
        }

    def dashboard_view(self, actor, dashboard_id):
        """The dashboard derivation, at read: each named
        metric computed from the core store's current records
        for the dashboard's organization. Values are returned,
        never stored on the definition record."""
        self._check_role(actor, "read")
        dashboard = self._fetch(self._dashboards, dashboard_id,
                                "dashboard")
        metrics = {
            kind: self._metric(actor, dashboard["org_id"], kind)
            for kind in dashboard["metric_kinds"]
        }
        return {
            "dashboard_id": dashboard_id,
            "dashboard_ref": dashboard["dashboard_ref"],
            "title_label": dashboard["title_label"],
            "metrics": metrics,
        }

    def list_dashboards(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(d) for d in self._dashboards.values()
                if org_id is None or d["org_id"] == org_id]

    # -- enterprise performance management engine --------------------------
    # In-substrate form: plan records (planned debit/credit per
    # account, integer cents) and derivations over them --
    # actuals from the core ledger, variance, and a forecast
    # applying a recorded growth rate with integer arithmetic.
    # Planning here is records and arithmetic over this build's
    # own ledger, not an in-memory consolidation platform.

    def create_plan(self, actor, org_id, plan_ref, label, lines):
        """Record a performance plan: an opaque plan reference,
        a label, and plan lines -- one per account reference,
        each a planned debit and a planned credit in integer
        cents, at least one of them positive per line. The
        record stores the plan only; actuals and variance are
        derived at read."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(plan_ref, "plan_ref")
        _text(label, "label")
        if not isinstance(lines, (list, tuple)) or not lines:
            raise ValidationError("lines must be a non-empty list")
        validated = []
        seen_accounts = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each plan line must be an object")
            account_ref = _text(line.get("account_ref"), "account_ref")
            debit = _integer(line.get("planned_debit_cents"),
                             "planned_debit_cents", minimum=0)
            credit = _integer(line.get("planned_credit_cents"),
                              "planned_credit_cents", minimum=0)
            if debit == 0 and credit == 0:
                raise ValidationError(
                    "each plan line must plan a debit or a credit")
            if account_ref in seen_accounts:
                raise ValidationError(
                    "duplicate account_ref in plan: %r" % (account_ref,))
            seen_accounts.append(account_ref)
            validated.append({
                "account_ref": account_ref,
                "planned_debit_cents": debit,
                "planned_credit_cents": credit,
            })
        with self._lock:
            self._check_unique(self._plans, org_id, "plan_ref", plan_ref,
                               "plan_ref")
            plan = {
                "id": self._mint("pln-"),
                "org_id": org_id,
                "plan_ref": plan_ref,
                "label": label,
                "lines": validated,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._plans[plan["id"]] = plan
        self._audit(actor, "plan_create", plan["id"],
                    {"org_id": org_id, "plan_ref": plan_ref})
        return self._copy(plan)

    def _plan_actuals(self, actor, plan):
        actuals = {}
        for view in self.store.list_ledger_entries(
                actor, org_id=plan["org_id"]):
            for line in view["lines"]:
                row = actuals.setdefault(
                    line["account_ref"],
                    {"debit_cents": 0, "credit_cents": 0})
                row["debit_cents"] += line["debit_cents"]
                row["credit_cents"] += line["credit_cents"]
        return actuals

    def plan_view(self, actor, plan_id):
        """The plan derivation, at read: per account, planned
        net (debit minus credit), actual net from the
        organization's current ledger entries, and variance
        (actual minus planned). Accounts appearing only in
        actuals are included with planned zeros. Rows sorted by
        account reference; nothing is stored."""
        self._check_role(actor, "read")
        plan = self._fetch(self._plans, plan_id, "plan")
        actuals = self._plan_actuals(actor, plan)
        planned = {
            line["account_ref"]: line for line in plan["lines"]
        }
        rows = []
        for account_ref in sorted(set(planned) | set(actuals)):
            plan_line = planned.get(account_ref)
            planned_net = 0
            if plan_line is not None:
                planned_net = (plan_line["planned_debit_cents"]
                               - plan_line["planned_credit_cents"])
            actual = actuals.get(
                account_ref, {"debit_cents": 0, "credit_cents": 0})
            actual_net = actual["debit_cents"] - actual["credit_cents"]
            rows.append({
                "account_ref": account_ref,
                "planned_net_cents": planned_net,
                "actual_net_cents": actual_net,
                "variance_cents": actual_net - planned_net,
            })
        return {
            "plan_id": plan_id,
            "plan_ref": plan["plan_ref"],
            "accounts": rows,
            "planned_net_cents": sum(r["planned_net_cents"] for r in rows),
            "actual_net_cents": sum(r["actual_net_cents"] for r in rows),
            "variance_cents": sum(r["variance_cents"] for r in rows),
        }

    def plan_forecast(self, actor, plan_id, growth_bps, periods):
        """The forecast derivation, at read: starting from the
        plan's total planned net, apply ``growth_bps`` per
        period with integer arithmetic (each step adds
        ``value * growth_bps // 10000``, floor division) for
        ``periods`` periods. A deterministic projection of the
        recorded plan -- derived, never stored."""
        self._check_role(actor, "read")
        plan = self._fetch(self._plans, plan_id, "plan")
        _integer(growth_bps, "growth_bps")
        if growth_bps < -10000:
            raise ValidationError("growth_bps must be at least -10000")
        _integer(periods, "periods", minimum=1)
        if periods > 36:
            raise ValidationError("periods must not exceed 36")
        value = sum(line["planned_debit_cents"]
                    - line["planned_credit_cents"]
                    for line in plan["lines"])
        projection = []
        for index in range(1, periods + 1):
            value = value + (value * growth_bps) // 10000
            projection.append({"period_index": index,
                               "projected_net_cents": value})
        return {"plan_id": plan_id, "plan_ref": plan["plan_ref"],
                "growth_bps": growth_bps, "projection": projection}

    def list_plans(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(p) for p in self._plans.values()
                if org_id is None or p["org_id"] == org_id]

    # -- governance, risk & compliance engine ------------------------------
    # In-substrate form: risk records with caller-stated
    # likelihood / impact, control check records with recorded
    # outcomes, and derivations -- exposure and band at read,
    # summary counts, and a permission verification that reads
    # the build's own access matrix. Exposure is a derivation
    # over two recorded integers, never stored; no workflow
    # executes and no permission is changed by verifying it.

    def create_risk_record(self, actor, org_id, risk_ref, title_label,
                           likelihood, impact):
        """Record a risk: an opaque risk reference, a title
        label, and caller-stated likelihood and impact, each an
        integer from 1 to 5. The record stores the two stated
        values only; exposure is derived at read."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(risk_ref, "risk_ref")
        _text(title_label, "title_label")
        _integer(likelihood, "likelihood", minimum=1)
        if likelihood > 5:
            raise ValidationError("likelihood must be between 1 and 5")
        _integer(impact, "impact", minimum=1)
        if impact > 5:
            raise ValidationError("impact must be between 1 and 5")
        with self._lock:
            self._check_unique(self._risk_records, org_id, "risk_ref",
                               risk_ref, "risk_ref")
            risk = {
                "id": self._mint("rsk-"),
                "org_id": org_id,
                "risk_ref": risk_ref,
                "title_label": title_label,
                "likelihood": likelihood,
                "impact": impact,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._risk_records[risk["id"]] = risk
        self._audit(actor, "risk_record_create", risk["id"],
                    {"org_id": org_id, "risk_ref": risk_ref})
        return self._copy(risk)

    @staticmethod
    def _exposure_band(exposure):
        if exposure <= 4:
            return "low"
        if exposure <= 9:
            return "moderate"
        if exposure <= 16:
            return "high"
        return "critical"

    def risk_exposure(self, actor, risk_id):
        """The exposure derivation, at read: likelihood times
        impact, and the band the product falls in (low up to 4,
        moderate up to 9, high up to 16, critical above).
        Deterministic arithmetic over the two recorded values;
        nothing is stored on the risk record."""
        self._check_role(actor, "read")
        risk = self._fetch(self._risk_records, risk_id, "risk record")
        exposure = risk["likelihood"] * risk["impact"]
        return {
            "risk_id": risk_id,
            "risk_ref": risk["risk_ref"],
            "likelihood": risk["likelihood"],
            "impact": risk["impact"],
            "exposure": exposure,
            "band": self._exposure_band(exposure),
        }

    def create_control_check(self, actor, org_id, check_ref, label,
                             subject_label):
        """Record a control check: an opaque check reference, a
        label, and a caller-stated subject label. The check
        starts open; its outcome arrives through a recorded
        action."""
        self._check_role(actor, "record")
        self._org(actor, org_id)
        _text(check_ref, "check_ref")
        _text(label, "label")
        _text(subject_label, "subject_label")
        with self._lock:
            self._check_unique(self._control_checks, org_id, "check_ref",
                               check_ref, "check_ref")
            check = {
                "id": self._mint("chk-"),
                "org_id": org_id,
                "check_ref": check_ref,
                "label": label,
                "subject_label": subject_label,
                "status": "open",
                "outcome": None,
                "outcome_by": None,
                "outcome_utc": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._control_checks[check["id"]] = check
        self._audit(actor, "control_check_create", check["id"],
                    {"org_id": org_id, "check_ref": check_ref})
        return self._copy(check)

    def record_check_result(self, actor, check_id, outcome):
        """Record a control check's outcome by recorded action:
        ``pass`` or ``fail``, exactly once, from the open
        state."""
        self._check_role(actor, "approve")
        check = self._fetch(self._control_checks, check_id,
                            "control check")
        if outcome not in CHECK_OUTCOMES:
            raise ValidationError("unknown check outcome: %r" % (outcome,))
        with self._lock:
            if check["status"] != "open":
                raise ValidationError(
                    "control check %s already has outcome %r"
                    % (check_id, check["outcome"]))
            check["status"] = "recorded"
            check["outcome"] = outcome
            check["outcome_by"] = actor_name(actor)
            check["outcome_utc"] = _utc_now()
        self._audit(actor, "control_check_result", check_id,
                    {"outcome": outcome})
        return self._copy(check)

    def grc_summary(self, actor, org_id):
        """The GRC derivation, at read: risk counts by derived
        exposure band, control check counts by recorded
        outcome, and a permission verification -- the build's
        own role permission matrix, read from
        :mod:`erp.access`, so what each role may do can be
        checked against the records. Counts and the matrix
        only; nothing is changed by verifying."""
        self._check_role(actor, "read")
        self._org(actor, org_id)
        bands = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        risk_count = 0
        for risk in self._risk_records.values():
            if risk["org_id"] != org_id:
                continue
            risk_count += 1
            bands[self._exposure_band(
                risk["likelihood"] * risk["impact"])] += 1
        outcomes = {"pass": 0, "fail": 0, "open": 0}
        for check in self._control_checks.values():
            if check["org_id"] != org_id:
                continue
            if check["status"] == "open":
                outcomes["open"] += 1
            else:
                outcomes[check["outcome"]] += 1
        return {
            "org_id": org_id,
            "risk_count": risk_count,
            "risks_by_band": bands,
            "checks_by_outcome": outcomes,
            "permission_matrix": {
                role: sorted(permissions)
                for role, permissions in PERMISSIONS.items()
            },
        }

    def list_risk_records(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(r) for r in self._risk_records.values()
                if org_id is None or r["org_id"] == org_id]

    def list_control_checks(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(c) for c in self._control_checks.values()
                if org_id is None or c["org_id"] == org_id]

    # -- identity federation service (reference implementation) ------------
    # Stub-engine entry. Federation configuration records only,
    # labeled as a reference implementation. Per PLATFORM-LAYER
    # decision 1, identity stays with the embedding
    # organization: this substrate is never an IdP, performs no
    # authentication, and provisions nothing. hook_only states
    # that on the record itself.

    def create_federation_record(self, actor, org_id, record_ref,
                                 provider_label, protocol_label):
        """Record a federation configuration as a labeled
        reference record: the identity provider and protocol
        the suite would federate with, each by caller-stated
        label. Every record carries ``reference_stub: True``
        and ``hook_only: True``; recording one federates
        nothing."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(record_ref, "record_ref")
        _text(provider_label, "provider_label")
        _text(protocol_label, "protocol_label")
        with self._lock:
            self._check_unique(self._federation_records, org_id,
                               "record_ref", record_ref, "record_ref")
            record = {
                "id": self._mint("fed-"),
                "org_id": org_id,
                "record_ref": record_ref,
                "provider_label": provider_label,
                "protocol_label": protocol_label,
                "reference_stub": True,
                "hook_only": True,
                "status": STUB_STATUS,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._federation_records[record["id"]] = record
        self._audit(actor, "federation_record_create", record["id"],
                    {"org_id": org_id, "record_ref": record_ref})
        return self._copy(record)

    def list_federation_records(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(r) for r in self._federation_records.values()
                if org_id is None or r["org_id"] == org_id]

    # -- integration execution & orchestration runtime (reference) ---------
    # Stub-engine entry. A record describing an orchestration
    # runtime, referencing a core workflow record. The build's
    # registries store records and never execute, so the record
    # is labeled reference_stub and there is no operation here
    # that runs, fires, or executes anything.

    def create_orchestration_record(self, actor, org_id, record_ref,
                                    workflow_id, label):
        """Record an orchestration-runtime reference record
        against a core workflow record of the organization.
        Every record carries ``reference_stub: True``; the
        runtime it names is not present in this substrate and
        recording it executes no process."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(record_ref, "record_ref")
        _text(label, "label")
        workflow = None
        for candidate in self.store.list_workflows(actor, org_id=org_id):
            if candidate["id"] == workflow_id:
                workflow = candidate
                break
        if workflow is None:
            raise NotFoundError(
                "no workflow record %r in organization %s"
                % (workflow_id, org_id))
        with self._lock:
            self._check_unique(self._orchestration_records, org_id,
                               "record_ref", record_ref, "record_ref")
            record = {
                "id": self._mint("orc-"),
                "org_id": org_id,
                "record_ref": record_ref,
                "workflow_id": workflow_id,
                "label": label,
                "reference_stub": True,
                "status": STUB_STATUS,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._orchestration_records[record["id"]] = record
        self._audit(actor, "orchestration_record_create", record["id"],
                    {"org_id": org_id, "record_ref": record_ref})
        return self._copy(record)

    def list_orchestration_records(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(r)
                for r in self._orchestration_records.values()
                if org_id is None or r["org_id"] == org_id]

    # -- API gateway runtime (reference implementation) ---------------------
    # Stub-engine entry. Route and policy records against a core
    # api_gateway integration record, labeled as a reference
    # implementation. No call is routed, no policy enforced, and
    # nothing is throttled by recording one.

    def create_gateway_route_record(self, actor, org_id, record_ref,
                                    integration_id, route_label,
                                    policy_label):
        """Record a gateway route/policy reference record
        against an ``api_gateway`` integration record of the
        organization. Every record carries
        ``reference_stub: True``; the gateway runtime it names
        is not present in this substrate."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(record_ref, "record_ref")
        _text(route_label, "route_label")
        _text(policy_label, "policy_label")
        integration = None
        for candidate in self.store.list_integrations(actor,
                                                      org_id=org_id):
            if candidate["id"] == integration_id:
                integration = candidate
                break
        if integration is None:
            raise NotFoundError(
                "no integration record %r in organization %s"
                % (integration_id, org_id))
        if integration["kind"] != "api_gateway":
            raise ValidationError(
                "integration %s is kind %r, not 'api_gateway'"
                % (integration_id, integration["kind"]))
        with self._lock:
            self._check_unique(self._gateway_routes, org_id,
                               "record_ref", record_ref, "record_ref")
            record = {
                "id": self._mint("gwr-"),
                "org_id": org_id,
                "record_ref": record_ref,
                "integration_id": integration_id,
                "route_label": route_label,
                "policy_label": policy_label,
                "reference_stub": True,
                "status": STUB_STATUS,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gateway_routes[record["id"]] = record
        self._audit(actor, "gateway_route_record_create", record["id"],
                    {"org_id": org_id, "record_ref": record_ref})
        return self._copy(record)

    def list_gateway_route_records(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(r) for r in self._gateway_routes.values()
                if org_id is None or r["org_id"] == org_id]

    # -- expense policy enforcement & fraud detection (reference) ----------
    # Stub-engine entry. Policy records (a category and a limit
    # in integer cents) and an evaluation derived at read: the
    # deterministic limit check over a recorded expense report's
    # lines. The evaluation is labeled reference_stub and its
    # method is stated on it. A finding is a recorded limit
    # breach only -- this build determines no fraud, and no
    # finding asserts any.

    def create_expense_policy(self, actor, org_id, policy_ref,
                              category_label, limit_cents):
        """Record an expense policy as a labeled reference
        record: a category label and a per-line limit in
        integer cents. Every record carries
        ``reference_stub: True``; recording a policy enforces
        nothing against any report."""
        self._check_role(actor, "register")
        self._org(actor, org_id)
        _text(policy_ref, "policy_ref")
        _text(category_label, "category_label")
        _integer(limit_cents, "limit_cents", minimum=0)
        with self._lock:
            self._check_unique(self._expense_policies, org_id,
                               "policy_ref", policy_ref, "policy_ref")
            policy = {
                "id": self._mint("pol-"),
                "org_id": org_id,
                "policy_ref": policy_ref,
                "category_label": category_label,
                "limit_cents": limit_cents,
                "reference_stub": True,
                "status": STUB_STATUS,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._expense_policies[policy["id"]] = policy
        self._audit(actor, "expense_policy_create", policy["id"],
                    {"org_id": org_id, "policy_ref": policy_ref})
        return self._copy(policy)

    def expense_policy_evaluation(self, actor, policy_id, report_id):
        """The reference evaluation, derived at read: the
        expense report's lines in the policy's category whose
        amount exceeds the policy's recorded limit, each with
        its excess. Carries ``reference_stub: True`` and method
        ``deterministic_limit_check``. A finding states a limit
        breach in the records -- nothing more; fraud is a
        determination this build does not make."""
        self._check_role(actor, "read")
        policy = self._fetch(self._expense_policies, policy_id,
                             "expense policy")
        report = self.store.get_expense_report(actor, report_id)
        if report["org_id"] != policy["org_id"]:
            raise ValidationError(
                "expense report %s does not belong to organization %s"
                % (report_id, policy["org_id"]))
        findings = [
            {"category_label": line["category_label"],
             "amount_cents": line["amount_cents"],
             "limit_cents": policy["limit_cents"],
             "excess_cents": line["amount_cents"] - policy["limit_cents"]}
            for line in report["lines"]
            if line["category_label"] == policy["category_label"]
            and line["amount_cents"] > policy["limit_cents"]
        ]
        return {
            "policy_id": policy_id,
            "policy_ref": policy["policy_ref"],
            "report_id": report_id,
            "reference_stub": True,
            "method": "deterministic_limit_check",
            "findings": findings,
            "finding_count": len(findings),
            "report_total_cents": report["total_cents"],
        }

    def list_expense_policies(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._org(actor, org_id)
        return [self._copy(p) for p in self._expense_policies.values()
                if org_id is None or p["org_id"] == org_id]
