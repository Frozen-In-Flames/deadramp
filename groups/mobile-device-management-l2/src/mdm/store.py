"""MDM store: customer organizations, telecom service inventory,
service orders, workflow definitions, contracts, quotes, bills,
validation runs, disputes, budgets, obligations, chargebacks, and
alert records.

Clean-room implementation of the union spec's implementation
contract. The single fork in this category is a Telecommunication
Expense Management (TEM) and Managed Mobility system filed under
Mobile Device Management (MDM); this store implements the records
substrate its description actually claims, and nothing else.

Two boundaries are enforced on every organization-scoped operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see :mod:`mdm.access`)
   when the actor is a User-like object. A plain string actor
   carries identity (for provenance) but no role, so role
   enforcement for those happens in the service layer.

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``inv-``, ``ord-``, ``wfl-``, ``con-``, ``quo-``, ``bil-``,
``val-``, ``dis-``, ``bud-``, ``obl-``, ``chg-``, ``alr-``).

Derivation discipline: a budget's obligated, spent, and available
values are computed at read from its obligation records and never
stored -- the stored budget record carries no such key. An
inventory item's provisioning state, by contrast, is event-driven
(it changes only when a service order is fulfilled), so it is
stored, as in the sibling builds' record lifecycles.

Money discipline: amounts are integer cents. Any amount that is
not a Python ``int`` (booleans and floats included, even integral
floats) raises :class:`ValidationError`. Inventory recurring
charges are integer cents per month for the same reason.

Scoring discipline: nothing in this store computes a score, a
rating, an optimization, or a projection. Validation runs record
deterministic arithmetic over registered records (a bill's stated
total against the sum of the inventory's registered recurring
charges); a budget's projection value is caller-supplied and
recorded verbatim. No record shape carries a field for a computed
score or forecast.

Privacy discipline: organizations and inventory items are known
only by caller-supplied opaque references and labels. The
inventory record shape is pinned -- it has no field that could
hold a phone number, an IMEI, a serial number, or any other real
device identifier -- and the pin is enforced by tests.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SERVICE_KINDS = ("wireline", "mobility", "other")
PROVISIONING_STATES = ("active", "suspended", "disconnected")
ORDER_TYPES = ("new", "macd", "port", "suspend", "restore", "disconnect")
ORDER_STATUSES = ("requested", "approved", "rejected", "cancelled", "fulfilled")
# Fulfillment of an order moves its linked inventory item to this
# provisioning state (registry mechanics of the substrate).
FULFILL_STATE = {
    "new": "active",
    "macd": "active",
    "port": "active",
    "suspend": "suspended",
    "restore": "active",
    "disconnect": "disconnected",
}
DISPUTE_STATUSES = ("open", "in_progress", "resolved")
OBLIGATION_KINDS = ("obligated", "spent")
ALERT_KINDS = ("budget_threshold", "budget_projection", "general")

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _utc_now():
    return datetime.now(timezone.utc)


def _money(value, field, allow_zero=True):
    """Validate an integer-cents amount; floats and bools are rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _period(value, field="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError("%s must be a YYYY-MM period: %r" % (field, value))
    return value


class MdmStore:
    """In-memory telecom expense / managed mobility records store."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._inventory = {}
        self._orders = {}
        self._workflows = {}
        self._contracts = {}
        self._quotes = {}
        self._bills = {}
        self._validations = {}
        self._disputes = {}
        self._budgets = {}
        self._obligations = {}
        self._chargebacks = {}
        self._alerts = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _check_org_access(self, actor, org):
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        if role == "admin" or name in org["members"]:
            return
        raise PermissionDenied(
            "permission denied: user %r is not a member of organization %r"
            % (name, org["id"])
        )

    def _scoped(self, actor, org_id, action):
        """Role check + org lookup + membership check, in that order."""
        self._check_role(actor, action)
        org = self._organization(org_id)
        self._check_org_access(actor, org)
        return org

    # -- customer organizations -------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register a customer organization by opaque reference.

        The creator becomes owner and first member.
        """
        self._check_role(actor, "create_org")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError("organization ref already exists: %r" % (ref,))
            org = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "owner": actor_name(actor),
                "members": [actor_name(actor)],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"ref": ref})
        return self._org_view(org)

    @staticmethod
    def _org_view(org):
        view = dict(org)
        view["members"] = list(org["members"])
        return view

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        org = self._organization(org_id)
        self._check_org_access(actor, org)
        return self._org_view(org)

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        return [
            self._org_view(org) for org in self._organizations.values()
            if role == "admin" or name in org["members"]
        ]

    def update_organization(self, actor, org_id, label):
        """Update an organization's profile label."""
        org = self._scoped(actor, org_id, "enter")
        _text(label, "label")
        with self._lock:
            org["label"] = label
        self._record(actor, "organization_update", org_id, {})
        return self._org_view(org)

    def add_member(self, actor, org_id, username):
        """Add a member (by username) to an organization."""
        org = self._scoped(actor, org_id, "manage_members")
        _text(username, "username")
        with self._lock:
            if username not in org["members"]:
                org["members"].append(username)
        self._record(actor, "member_add", org_id, {"username": username})
        return self._org_view(org)

    # -- telecom service inventory -----------------------------------------

    def create_inventory_item(self, actor, org_id, ref, service_kind, label,
                              plan_ref, monthly_recurring_cents):
        """Register one telecom service in an organization's inventory.

        ``ref`` is the caller-supplied opaque service reference; it
        is unique within the organization. The record shape is
        pinned (see the module docstring's privacy discipline).
        """
        self._scoped(actor, org_id, "enter")
        _text(ref, "ref")
        if service_kind not in SERVICE_KINDS:
            raise ValidationError("service_kind must be one of %r" % (SERVICE_KINDS,))
        _text(label, "label")
        _text(plan_ref, "plan_ref")
        _money(monthly_recurring_cents, "monthly_recurring_cents")
        with self._lock:
            for existing in self._inventory.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "inventory ref already exists in this organization: %r" % (ref,))
            item = {
                "id": self._mint("inv-"),
                "org_id": org_id,
                "ref": ref,
                "service_kind": service_kind,
                "label": label,
                "plan_ref": plan_ref,
                "monthly_recurring_cents": monthly_recurring_cents,
                "provisioning_state": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._inventory[item["id"]] = item
        self._record(actor, "inventory_create", item["id"], {"ref": ref})
        return dict(item)

    def _inventory_item(self, item_id):
        item = self._inventory.get(item_id)
        if item is None:
            raise NotFoundError("no such inventory item: %r" % (item_id,))
        return item

    def get_inventory_item(self, actor, item_id):
        self._check_role(actor, "read")
        item = self._inventory_item(item_id)
        self._check_org_access(actor, self._organizations[item["org_id"]])
        return dict(item)

    def list_inventory(self, actor, org_id, service_kind=None, state=None):
        self._scoped(actor, org_id, "read")
        result = []
        for item in self._inventory.values():
            if item["org_id"] != org_id:
                continue
            if service_kind is not None and item["service_kind"] != service_kind:
                continue
            if state is not None and item["provisioning_state"] != state:
                continue
            result.append(dict(item))
        return result

    # -- service orders ------------------------------------------------------

    def create_order(self, actor, org_id, order_type, detail, inventory_id=None):
        """Record a service order (MACD, port, suspend, restore, ...)."""
        self._scoped(actor, org_id, "enter")
        if order_type not in ORDER_TYPES:
            raise ValidationError("order_type must be one of %r" % (ORDER_TYPES,))
        _text(detail, "detail")
        if inventory_id is not None:
            item = self._inventory_item(inventory_id)
            if item["org_id"] != org_id:
                raise ValidationError("inventory item belongs to another organization")
            if order_type == "new":
                raise ValidationError("a 'new' order does not target an existing item")
        elif order_type != "new":
            raise ValidationError("order_type %r requires an inventory item" % (order_type,))
        with self._lock:
            order = {
                "id": self._mint("ord-"),
                "org_id": org_id,
                "order_type": order_type,
                "inventory_id": inventory_id,
                "detail": detail,
                "status": "requested",
                "requested_by": actor_name(actor),
                "decided_by": None,
                "created_utc": _utc_now().isoformat(),
                "decided_utc": None,
                "fulfilled_utc": None,
            }
            self._orders[order["id"]] = order
        self._record(actor, "order_create", order["id"], {"order_type": order_type})
        return dict(order)

    def _order(self, order_id):
        order = self._orders.get(order_id)
        if order is None:
            raise NotFoundError("no such service order: %r" % (order_id,))
        return order

    def get_order(self, actor, order_id):
        self._check_role(actor, "read")
        order = self._order(order_id)
        self._check_org_access(actor, self._organizations[order["org_id"]])
        return dict(order)

    def list_orders(self, actor, org_id, status=None):
        self._scoped(actor, org_id, "read")
        return [
            dict(o) for o in self._orders.values()
            if o["org_id"] == org_id and (status is None or o["status"] == status)
        ]

    def decide_order(self, actor, order_id, approve):
        """Approve or reject a requested order.

        Separation of duties: the decider is never the requester.
        """
        order = self._order(order_id)
        self._scoped(actor, order["org_id"], "decide")
        if order["status"] != "requested":
            raise ValidationError("order is not awaiting decision: %r" % (order["status"],))
        if actor_name(actor) == order["requested_by"]:
            raise PermissionDenied("the decider of an order is never its requester")
        with self._lock:
            order["status"] = "approved" if approve else "rejected"
            order["decided_by"] = actor_name(actor)
            order["decided_utc"] = _utc_now().isoformat()
        self._record(actor, "order_decide", order_id, {"approve": bool(approve)})
        return dict(order)

    def cancel_order(self, actor, order_id):
        """Cancel a requested or approved order."""
        order = self._order(order_id)
        self._scoped(actor, order["org_id"], "enter")
        if order["status"] not in ("requested", "approved"):
            raise ValidationError("order cannot be cancelled from %r" % (order["status"],))
        with self._lock:
            order["status"] = "cancelled"
        self._record(actor, "order_cancel", order_id, {})
        return dict(order)

    def fulfill_order(self, actor, order_id):
        """Mark an approved order fulfilled.

        Fulfilling an order is the only event that changes a linked
        inventory item's provisioning state, per FULFILL_STATE.
        """
        order = self._order(order_id)
        self._scoped(actor, order["org_id"], "record")
        if order["status"] != "approved":
            raise ValidationError("only an approved order can be fulfilled")
        with self._lock:
            order["status"] = "fulfilled"
            order["fulfilled_utc"] = _utc_now().isoformat()
            if order["inventory_id"] is not None:
                item = self._inventory[order["inventory_id"]]
                item["provisioning_state"] = FULFILL_STATE[order["order_type"]]
        self._record(actor, "order_fulfill", order_id, {})
        return dict(order)

    # -- workflow definitions (registered, never executed) -------------------

    def create_workflow(self, actor, org_id, name, steps):
        """Register a workflow definition as data. Never executed."""
        self._scoped(actor, org_id, "record")
        _text(name, "name")
        if not isinstance(steps, list) or not steps:
            raise ValidationError("steps must be a non-empty list of step names")
        for step in steps:
            _text(step, "step")
        with self._lock:
            workflow = {
                "id": self._mint("wfl-"),
                "org_id": org_id,
                "name": name,
                "steps": list(steps),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[workflow["id"]] = workflow
        self._record(actor, "workflow_create", workflow["id"], {"name": name})
        view = dict(workflow)
        view["steps"] = list(workflow["steps"])
        return view

    def get_workflow(self, actor, workflow_id):
        self._check_role(actor, "read")
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        self._check_org_access(actor, self._organizations[workflow["org_id"]])
        view = dict(workflow)
        view["steps"] = list(workflow["steps"])
        return view

    def list_workflows(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        result = []
        for workflow in self._workflows.values():
            if workflow["org_id"] == org_id:
                view = dict(workflow)
                view["steps"] = list(workflow["steps"])
                result.append(view)
        return result

    # -- contracts & quotes ---------------------------------------------------

    def create_contract(self, actor, org_id, ref, label, starts_on, ends_on=None):
        """Register a telecom contract by opaque reference."""
        self._scoped(actor, org_id, "enter")
        _text(ref, "ref")
        _text(label, "label")
        _text(starts_on, "starts_on")
        if ends_on is not None:
            _text(ends_on, "ends_on")
            if ends_on < starts_on:
                raise ValidationError("ends_on must not precede starts_on")
        with self._lock:
            for existing in self._contracts.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "contract ref already exists in this organization: %r" % (ref,))
            contract = {
                "id": self._mint("con-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "starts_on": starts_on,
                "ends_on": ends_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._contracts[contract["id"]] = contract
        self._record(actor, "contract_create", contract["id"], {"ref": ref})
        return dict(contract)

    def _contract(self, contract_id):
        contract = self._contracts.get(contract_id)
        if contract is None:
            raise NotFoundError("no such contract: %r" % (contract_id,))
        return contract

    def get_contract(self, actor, contract_id):
        self._check_role(actor, "read")
        contract = self._contract(contract_id)
        self._check_org_access(actor, self._organizations[contract["org_id"]])
        return dict(contract)

    def list_contracts(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(c) for c in self._contracts.values() if c["org_id"] == org_id]

    def create_quote(self, actor, org_id, contract_id, amount_cents,
                     inventory_id=None, note=""):
        """Record a quote against a contract (and optionally an item)."""
        self._scoped(actor, org_id, "enter")
        contract = self._contract(contract_id)
        if contract["org_id"] != org_id:
            raise ValidationError("contract belongs to another organization")
        _money(amount_cents, "amount_cents")
        if inventory_id is not None:
            item = self._inventory_item(inventory_id)
            if item["org_id"] != org_id:
                raise ValidationError("inventory item belongs to another organization")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            quote = {
                "id": self._mint("quo-"),
                "org_id": org_id,
                "contract_id": contract_id,
                "inventory_id": inventory_id,
                "amount_cents": amount_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._quotes[quote["id"]] = quote
        self._record(actor, "quote_create", quote["id"], {})
        return dict(quote)

    def list_quotes(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(q) for q in self._quotes.values() if q["org_id"] == org_id]

    # -- bills & validation runs ----------------------------------------------

    def create_bill(self, actor, org_id, contract_id, period, stated_cents):
        """Record a telecom bill as received, with its stated total."""
        self._scoped(actor, org_id, "enter")
        contract = self._contract(contract_id)
        if contract["org_id"] != org_id:
            raise ValidationError("contract belongs to another organization")
        _period(period)
        _money(stated_cents, "stated_cents")
        with self._lock:
            bill = {
                "id": self._mint("bil-"),
                "org_id": org_id,
                "contract_id": contract_id,
                "period": period,
                "stated_cents": stated_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._bills[bill["id"]] = bill
        self._record(actor, "bill_create", bill["id"], {"period": period})
        return dict(bill)

    def _bill(self, bill_id):
        bill = self._bills.get(bill_id)
        if bill is None:
            raise NotFoundError("no such bill: %r" % (bill_id,))
        return bill

    def get_bill(self, actor, bill_id):
        self._check_role(actor, "read")
        bill = self._bill(bill_id)
        self._check_org_access(actor, self._organizations[bill["org_id"]])
        return dict(bill)

    def list_bills(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(b) for b in self._bills.values() if b["org_id"] == org_id]

    def _expected_bill_cents(self, org_id):
        """Sum of registered recurring charges for billable inventory.

        The check's stated rule: every inventory item in the
        organization whose provisioning state is not ``disconnected``
        contributes its registered monthly recurring charge.
        """
        return sum(
            item["monthly_recurring_cents"]
            for item in self._inventory.values()
            if item["org_id"] == org_id
            and item["provisioning_state"] != "disconnected"
        )

    def validate_bill(self, actor, bill_id):
        """Run a validation check on a bill and record the run.

        Deterministic arithmetic over registered records: the
        bill's stated total against the expected total from the
        inventory registry. The run is an event record; the bill
        itself is never modified.
        """
        bill = self._bill(bill_id)
        self._scoped(actor, bill["org_id"], "record")
        expected = self._expected_bill_cents(bill["org_id"])
        variance = bill["stated_cents"] - expected
        with self._lock:
            run = {
                "id": self._mint("val-"),
                "org_id": bill["org_id"],
                "bill_id": bill_id,
                "stated_cents": bill["stated_cents"],
                "expected_cents": expected,
                "variance_cents": variance,
                "result": "match" if variance == 0 else "variance",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._validations[run["id"]] = run
        self._record(actor, "bill_validate", bill_id,
                     {"validation_id": run["id"], "result": run["result"]})
        return dict(run)

    def list_validations(self, actor, bill_id):
        self._check_role(actor, "read")
        bill = self._bill(bill_id)
        self._check_org_access(actor, self._organizations[bill["org_id"]])
        return [dict(v) for v in self._validations.values()
                if v["bill_id"] == bill_id]

    # -- disputes ----------------------------------------------------------------

    def _check_dispute_within_bill(self, bill, amount_cents):
        """A dispute can never exceed the bill it disputes."""
        if amount_cents > bill["stated_cents"]:
            raise ValidationError(
                "dispute amount %d exceeds the bill's stated total %d"
                % (amount_cents, bill["stated_cents"]))

    def create_dispute(self, actor, bill_id, amount_cents, reason):
        """Open a dispute on a bill, tracked through resolution."""
        bill = self._bill(bill_id)
        self._scoped(actor, bill["org_id"], "enter")
        _money(amount_cents, "amount_cents", allow_zero=False)
        _text(reason, "reason")
        self._check_dispute_within_bill(bill, amount_cents)
        with self._lock:
            dispute = {
                "id": self._mint("dis-"),
                "org_id": bill["org_id"],
                "bill_id": bill_id,
                "amount_cents": amount_cents,
                "reason": reason,
                "status": "open",
                "resolution": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "resolved_utc": None,
            }
            self._disputes[dispute["id"]] = dispute
        self._record(actor, "dispute_create", dispute["id"], {"bill_id": bill_id})
        return dict(dispute)

    def _dispute(self, dispute_id):
        dispute = self._disputes.get(dispute_id)
        if dispute is None:
            raise NotFoundError("no such dispute: %r" % (dispute_id,))
        return dispute

    def get_dispute(self, actor, dispute_id):
        self._check_role(actor, "read")
        dispute = self._dispute(dispute_id)
        self._check_org_access(actor, self._organizations[dispute["org_id"]])
        return dict(dispute)

    def list_disputes(self, actor, bill_id):
        self._check_role(actor, "read")
        bill = self._bill(bill_id)
        self._check_org_access(actor, self._organizations[bill["org_id"]])
        return [dict(d) for d in self._disputes.values()
                if d["bill_id"] == bill_id]

    def start_dispute(self, actor, dispute_id):
        """Move an open dispute to in_progress."""
        dispute = self._dispute(dispute_id)
        self._scoped(actor, dispute["org_id"], "record")
        if dispute["status"] != "open":
            raise ValidationError("only an open dispute can be started")
        with self._lock:
            dispute["status"] = "in_progress"
        self._record(actor, "dispute_start", dispute_id, {})
        return dict(dispute)

    def resolve_dispute(self, actor, dispute_id, resolution):
        """Resolve a dispute, recording the resolution verbatim."""
        dispute = self._dispute(dispute_id)
        self._scoped(actor, dispute["org_id"], "decide")
        _text(resolution, "resolution")
        if dispute["status"] == "resolved":
            raise ValidationError("dispute is already resolved")
        with self._lock:
            dispute["status"] = "resolved"
            dispute["resolution"] = resolution
            dispute["resolved_utc"] = _utc_now().isoformat()
        self._record(actor, "dispute_resolve", dispute_id, {})
        return dict(dispute)

    # -- budgets, obligations, chargebacks ---------------------------------------

    def create_budget(self, actor, org_id, period, budget_cents,
                      projection_cents=None, note=""):
        """Record a budget for one organization and period.

        ``projection_cents`` is a caller-supplied forecast recorded
        verbatim; the build never computes a projection.
        """
        self._scoped(actor, org_id, "enter")
        _period(period)
        _money(budget_cents, "budget_cents")
        if projection_cents is not None:
            _money(projection_cents, "projection_cents")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            for existing in self._budgets.values():
                if existing["org_id"] == org_id and existing["period"] == period:
                    raise ValidationError(
                        "a budget already exists for period %r" % (period,))
            budget = {
                "id": self._mint("bud-"),
                "org_id": org_id,
                "period": period,
                "budget_cents": budget_cents,
                "projection_cents": projection_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._budgets[budget["id"]] = budget
        self._record(actor, "budget_create", budget["id"], {"period": period})
        return self._budget_view(budget)

    def _budget(self, budget_id):
        budget = self._budgets.get(budget_id)
        if budget is None:
            raise NotFoundError("no such budget: %r" % (budget_id,))
        return budget

    def _available_cents(self, budget):
        """Derived availability: budget minus obligated minus spent.

        Computed at read from the obligation records; never stored.
        This is the group's signature derivation (see the negative
        control in tests/test_negative_control.py).
        """
        obligated = 0
        spent = 0
        for obligation in self._obligations.values():
            if obligation["budget_id"] != budget["id"]:
                continue
            if obligation["kind"] == "obligated":
                obligated += obligation["amount_cents"]
            else:
                spent += obligation["amount_cents"]
        return budget["budget_cents"] - obligated - spent

    def _budget_view(self, budget):
        obligated = sum(
            o["amount_cents"] for o in self._obligations.values()
            if o["budget_id"] == budget["id"] and o["kind"] == "obligated")
        spent = sum(
            o["amount_cents"] for o in self._obligations.values()
            if o["budget_id"] == budget["id"] and o["kind"] == "spent")
        view = dict(budget)
        view["obligated_cents"] = obligated
        view["spent_cents"] = spent
        view["available_cents"] = self._available_cents(budget)
        return view

    def get_budget(self, actor, budget_id):
        self._check_role(actor, "read")
        budget = self._budget(budget_id)
        self._check_org_access(actor, self._organizations[budget["org_id"]])
        return self._budget_view(budget)

    def list_budgets(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [self._budget_view(b) for b in self._budgets.values()
                if b["org_id"] == org_id]

    def record_obligation(self, actor, budget_id, kind, amount_cents, note=""):
        """Record an obligated or spent amount against a budget."""
        budget = self._budget(budget_id)
        self._scoped(actor, budget["org_id"], "record")
        if kind not in OBLIGATION_KINDS:
            raise ValidationError("kind must be one of %r" % (OBLIGATION_KINDS,))
        _money(amount_cents, "amount_cents", allow_zero=False)
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            obligation = {
                "id": self._mint("obl-"),
                "org_id": budget["org_id"],
                "budget_id": budget_id,
                "kind": kind,
                "amount_cents": amount_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._obligations[obligation["id"]] = obligation
        self._record(actor, "obligation_create", obligation["id"],
                     {"budget_id": budget_id, "kind": kind})
        return dict(obligation)

    def list_obligations(self, actor, budget_id):
        self._check_role(actor, "read")
        budget = self._budget(budget_id)
        self._check_org_access(actor, self._organizations[budget["org_id"]])
        return [dict(o) for o in self._obligations.values()
                if o["budget_id"] == budget_id]

    def create_chargeback(self, actor, budget_id, unit_ref, amount_cents, note=""):
        """Record an internal customer chargeback against a budget."""
        budget = self._budget(budget_id)
        self._scoped(actor, budget["org_id"], "record")
        _text(unit_ref, "unit_ref")
        _money(amount_cents, "amount_cents", allow_zero=False)
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            chargeback = {
                "id": self._mint("chg-"),
                "org_id": budget["org_id"],
                "budget_id": budget_id,
                "unit_ref": unit_ref,
                "amount_cents": amount_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._chargebacks[chargeback["id"]] = chargeback
        self._record(actor, "chargeback_create", chargeback["id"],
                     {"budget_id": budget_id})
        return dict(chargeback)

    def list_chargebacks(self, actor, budget_id):
        self._check_role(actor, "read")
        budget = self._budget(budget_id)
        self._check_org_access(actor, self._organizations[budget["org_id"]])
        return [dict(c) for c in self._chargebacks.values()
                if c["budget_id"] == budget_id]

    # -- alert records -------------------------------------------------------------

    def create_alert(self, actor, org_id, kind, message, budget_id=None):
        """Record a budget alert. Delivery is Extended; this is the record."""
        self._scoped(actor, org_id, "record")
        if kind not in ALERT_KINDS:
            raise ValidationError("kind must be one of %r" % (ALERT_KINDS,))
        _text(message, "message")
        if budget_id is not None:
            budget = self._budget(budget_id)
            if budget["org_id"] != org_id:
                raise ValidationError("budget belongs to another organization")
        with self._lock:
            alert = {
                "id": self._mint("alr-"),
                "org_id": org_id,
                "budget_id": budget_id,
                "kind": kind,
                "message": message,
                "acknowledged_by": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._alerts[alert["id"]] = alert
        self._record(actor, "alert_create", alert["id"], {"kind": kind})
        return dict(alert)

    def list_alerts(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(a) for a in self._alerts.values() if a["org_id"] == org_id]

    def acknowledge_alert(self, actor, alert_id):
        """Record acknowledgement of an alert by the calling user."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("no such alert: %r" % (alert_id,))
        self._scoped(actor, alert["org_id"], "record")
        if alert["acknowledged_by"] is not None:
            raise ValidationError("alert is already acknowledged")
        with self._lock:
            alert["acknowledged_by"] = actor_name(actor)
        self._record(actor, "alert_acknowledge", alert_id, {})
        return dict(alert)

    # -- search & summary reporting --------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over accessible records."""
        self._check_role(actor, "read")
        needle = (query or "").strip().lower()
        orgs = self.list_organizations(actor)
        org_ids = {org["id"] for org in orgs}
        result = {"organizations": [], "inventory": [], "orders": [],
                  "bills": [], "contracts": []}
        if not needle:
            result["organizations"] = orgs
            return result
        for org in orgs:
            if needle in org["ref"].lower() or needle in org["label"].lower():
                result["organizations"].append(org)
        for item in self._inventory.values():
            if item["org_id"] in org_ids and (
                    needle in item["ref"].lower()
                    or needle in item["label"].lower()
                    or needle in item["plan_ref"].lower()):
                result["inventory"].append(dict(item))
        for order in self._orders.values():
            if order["org_id"] in org_ids and needle in order["detail"].lower():
                result["orders"].append(dict(order))
        for bill in self._bills.values():
            if bill["org_id"] in org_ids and needle in bill["period"].lower():
                result["bills"].append(dict(bill))
        for contract in self._contracts.values():
            if contract["org_id"] in org_ids and (
                    needle in contract["ref"].lower()
                    or needle in contract["label"].lower()):
                result["contracts"].append(dict(contract))
        return result

    def organization_summary(self, actor, org_id):
        """Counts and money sums for one organization, computed on read."""
        self._scoped(actor, org_id, "read")
        inventory_by_kind = {kind: 0 for kind in SERVICE_KINDS}
        inventory_by_state = {state: 0 for state in PROVISIONING_STATES}
        for item in self._inventory.values():
            if item["org_id"] == org_id:
                inventory_by_kind[item["service_kind"]] += 1
                inventory_by_state[item["provisioning_state"]] += 1
        orders_by_status = {status: 0 for status in ORDER_STATUSES}
        for order in self._orders.values():
            if order["org_id"] == org_id:
                orders_by_status[order["status"]] += 1
        bills = [b for b in self._bills.values() if b["org_id"] == org_id]
        disputes_by_status = {status: 0 for status in DISPUTE_STATUSES}
        open_disputed = 0
        for dispute in self._disputes.values():
            if dispute["org_id"] == org_id:
                disputes_by_status[dispute["status"]] += 1
                if dispute["status"] != "resolved":
                    open_disputed += dispute["amount_cents"]
        budgets = [self._budget_view(b) for b in self._budgets.values()
                   if b["org_id"] == org_id]
        return {
            "org_id": org_id,
            "inventory_by_kind": inventory_by_kind,
            "inventory_by_state": inventory_by_state,
            "orders_by_status": orders_by_status,
            "bills": len(bills),
            "bills_stated_cents": sum(b["stated_cents"] for b in bills),
            "validations": sum(1 for v in self._validations.values()
                               if v["org_id"] == org_id),
            "disputes_by_status": disputes_by_status,
            "open_disputed_cents": open_disputed,
            "budgets": budgets,
            "budget_available_cents": sum(b["available_cents"] for b in budgets),
            "chargebacks_cents": sum(
                c["amount_cents"] for c in self._chargebacks.values()
                if c["org_id"] == org_id),
            "alerts_unacknowledged": sum(
                1 for a in self._alerts.values()
                if a["org_id"] == org_id and a["acknowledged_by"] is None),
        }
