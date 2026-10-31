"""ERP store: organization and application registries; access
configuration records; general-ledger, procurement, expense,
person, time, absence, payroll, asset, work-order, inventory, and
document records; integration and workflow registries.

Clean-room implementation of the union spec's implementation
contract.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see :mod:`erp.access`). A plain
string actor carries identity (for provenance) but no role, so
role enforcement for those happens in the service layer (the
sibling builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``app-``, ``acc-``, ``led-``, ``po-``, ``exp-``, ``per-``,
``tim-``, ``abs-``, ``pay-``, ``ast-``, ``wo-``, ``inv-``,
``doc-``, ``int-``, ``wfl-``).

Money discipline: every amount in this store is an integer number
of cents. A boolean, float, or string where an amount is required
raises :class:`ValidationError` at the boundary. No record carries
a computed total: purchase-order and expense totals are derived
at read from their lines, so a total can never drift from the
lines it sums. The fork's description states no amount, rate, or
fee; the amounts here are caller-recorded values, not the fork's.

Ledger discipline (the signature invariant): a general-ledger
entry is recorded only when it balances -- every line carries a
debit or a credit but never both and never neither, total debits
equal total credits, and the total is positive. The whole rule
lives in the single seam :func:`_check_entry_balanced`, which the
entry view's derived totals also answer to, so the gate and the
reported totals can never disagree about what an entry is.

People discipline: a person record is the system of record for a
person *reference*. It holds an opaque ``person_ref``, a
department label, and a role label -- and no field that could
hold a name, an email address, a phone number, or any other real
identifier. The shape is pinned by test. Time, absence, payroll,
and expense records name a person only by a reference to a person
record in the same organization.

Content discipline: a document record holds metadata about a
business document -- an opaque reference, a label, a
business-purpose label. It stores no document content: there is
no field on the shape that could hold any.

Scoring discipline: nothing in this store computes a score, a
rating, or a ranking of any organization, person, supplier, or
asset, and no record shape carries a field for one. The summary
returns counts and recorded values only.

Registry discipline: integration, workflow, and
access-configuration records describe connections, processes, and
identity configuration; the registries never perform any of them.
Recording an integration connects nothing, recording a workflow
executes nothing, and recording an access configuration
authenticates no one -- identity itself stays with the embedding
organization (IA-2).

Lifecycle discipline: event-driven lifecycle state (an expense
report's outcome, a purchase order's receipt state, a work
order's assignment state, a registry record's active/inactive
state) is stored and changes only through recorded actions, as in
the sibling builds' record lifecycles. Anything computed from
other records -- order totals, expense totals, derived ledger
totals -- is computed at read and never stored.

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
from .errors import NotFoundError, ValidationError

REGISTRY_STATES = ("active", "inactive")
EXPENSE_STATES = ("submitted", "approved", "rejected")
PURCHASE_ORDER_STATES = ("open", "received", "closed")
WORK_ORDER_KINDS = ("preventive", "corrective")
WORK_ORDER_STATES = ("open", "assigned", "completed")
INTEGRATION_KINDS = ("integration_platform", "api_gateway")


def _utc_now():
    return datetime.now(timezone.utc)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _integer(value, field, minimum=None):
    """An integer amount/quantity: booleans, floats, and strings
    are rejected whole at the boundary."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (field, minimum))
    return value


def _date(value, field):
    """Validate an ISO calendar date string; returned unchanged."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD)" % field)
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValidationError("%s is not a real calendar date: %r" % (field, value))
    return value.strip()


def _check_entry_balanced(lines):
    """Balanced-entry seam: the general-ledger rule, stated once.

    ``lines`` is a non-empty list of validated line dicts with
    integer-cent ``debit_cents`` / ``credit_cents`` amounts. The
    rule: every line carries a debit or a credit but never both
    and never neither; total debits equal total credits; the
    total is positive. Raises :class:`ValidationError` on any
    violation. The ledger gate reads this seam and nothing else,
    so there is exactly one statement of what a balanced entry
    is.
    """
    total_debits = 0
    total_credits = 0
    for line in lines:
        debit = line["debit_cents"]
        credit = line["credit_cents"]
        if (debit > 0) == (credit > 0):
            raise ValidationError(
                "each ledger line must carry a debit or a credit, "
                "never both and never neither")
        total_debits += debit
        total_credits += credit
    if total_debits != total_credits:
        raise ValidationError(
            "ledger entry does not balance: debits %d != credits %d"
            % (total_debits, total_credits))
    if total_debits <= 0:
        raise ValidationError("ledger entry total must be positive")


class ErpStore:
    """In-memory enterprise-suite records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._applications = {}
        self._access_configs = {}
        self._ledger_entries = {}
        self._purchase_orders = {}
        self._expense_reports = {}
        self._persons = {}
        self._time_entries = {}
        self._absences = {}
        self._payroll_runs = {}
        self._assets = {}
        self._work_orders = {}
        self._inventory_items = {}
        self._documents = {}
        self._integrations = {}
        self._workflows = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

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
        organization = self._organizations.get(org_id)
        if organization is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return organization

    def _application(self, application_id):
        application = self._applications.get(application_id)
        if application is None:
            raise NotFoundError("no such application: %r" % (application_id,))
        return application

    def _access_config(self, config_id):
        config = self._access_configs.get(config_id)
        if config is None:
            raise NotFoundError("no such access configuration: %r" % (config_id,))
        return config

    def _ledger_entry(self, entry_id):
        entry = self._ledger_entries.get(entry_id)
        if entry is None:
            raise NotFoundError("no such ledger entry: %r" % (entry_id,))
        return entry

    def _purchase_order(self, order_id):
        order = self._purchase_orders.get(order_id)
        if order is None:
            raise NotFoundError("no such purchase order: %r" % (order_id,))
        return order

    def _expense_report(self, report_id):
        report = self._expense_reports.get(report_id)
        if report is None:
            raise NotFoundError("no such expense report: %r" % (report_id,))
        return report

    def _person(self, org_id, person_ref):
        for person in self._persons.values():
            if person["org_id"] == org_id and person["person_ref"] == person_ref:
                return person
        raise NotFoundError(
            "no person record with ref %r in organization %s"
            % (person_ref, org_id))

    def _person_by_id(self, person_id):
        person = self._persons.get(person_id)
        if person is None:
            raise NotFoundError("no such person record: %r" % (person_id,))
        return person

    def _asset(self, asset_id):
        asset = self._assets.get(asset_id)
        if asset is None:
            raise NotFoundError("no such asset: %r" % (asset_id,))
        return asset

    def _work_order(self, order_id):
        order = self._work_orders.get(order_id)
        if order is None:
            raise NotFoundError("no such work order: %r" % (order_id,))
        return order

    def _inventory_item(self, item_id):
        item = self._inventory_items.get(item_id)
        if item is None:
            raise NotFoundError("no such inventory item: %r" % (item_id,))
        return item

    def _integration(self, integration_id):
        integration = self._integrations.get(integration_id)
        if integration is None:
            raise NotFoundError("no such integration: %r" % (integration_id,))
        return integration

    def _workflow(self, workflow_id):
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        return workflow

    # -- organizations ---------------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "organization ref already exists: %r" % (ref,))
            organization = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[organization["id"]] = organization
        self._record(actor, "organization_create", organization["id"],
                     {"ref": ref})
        return dict(organization)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- application registry (records only) --------------------------------------

    def create_application(self, actor, org_id, app_ref, label, suite_label):
        """Register one of the suite's applications for an
        organization. Records only: registering an application
        installs nothing and runs nothing -- it records that the
        suite, as the organization has it, includes this
        application. ``app_ref`` is unique within the
        organization."""
        self._check_role(actor, "register")
        self._organization(org_id)
        _text(app_ref, "app_ref")
        _text(label, "label")
        _text(suite_label, "suite_label")
        with self._lock:
            for existing in self._applications.values():
                if existing["org_id"] == org_id \
                        and existing["app_ref"] == app_ref:
                    raise ValidationError(
                        "app_ref %r already exists in organization %s"
                        % (app_ref, org_id))
            application = {
                "id": self._mint("app-"),
                "org_id": org_id,
                "app_ref": app_ref,
                "label": label,
                "suite_label": suite_label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._applications[application["id"]] = application
        self._record(actor, "application_create", application["id"],
                     {"org_id": org_id, "app_ref": app_ref})
        return dict(application)

    def deactivate_application(self, actor, application_id):
        """Deactivate an application record by recorded action."""
        self._check_role(actor, "register")
        application = self._application(application_id)
        with self._lock:
            if application["status"] == "inactive":
                raise ValidationError(
                    "application %s is already inactive" % application_id)
            application["status"] = "inactive"
        self._record(actor, "application_deactivate", application_id, {})
        return dict(application)

    def list_applications(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if status is not None and status not in REGISTRY_STATES:
            raise ValidationError("unknown application status: %r" % (status,))
        return [
            dict(a) for a in self._applications.values()
            if (org_id is None or a["org_id"] == org_id)
            and (status is None or a["status"] == status)
        ]

    # -- access configuration records (records only) ---------------------------

    def create_access_config(self, actor, org_id, provider_label, mfa_label):
        """Record a federated-access configuration for an
        organization: the identity provider it federates with and
        the multi-factor arrangement it synchronizes with, each
        named by a caller-stated label. Records only: this
        authenticates no one and provisions nothing. Identity
        itself stays with the embedding organization (IA-2); the
        fork's federated-security claim is answered here at the
        configuration-records level, and the build's own
        role-based enforcement lives in :mod:`erp.access`."""
        self._check_role(actor, "register")
        self._organization(org_id)
        _text(provider_label, "provider_label")
        _text(mfa_label, "mfa_label")
        with self._lock:
            config = {
                "id": self._mint("acc-"),
                "org_id": org_id,
                "provider_label": provider_label,
                "mfa_label": mfa_label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._access_configs[config["id"]] = config
        self._record(actor, "access_config_create", config["id"],
                     {"org_id": org_id})
        return dict(config)

    def deactivate_access_config(self, actor, config_id):
        """Deactivate an access configuration record by recorded
        action."""
        self._check_role(actor, "register")
        config = self._access_config(config_id)
        with self._lock:
            if config["status"] == "inactive":
                raise ValidationError(
                    "access configuration %s is already inactive" % config_id)
            config["status"] = "inactive"
        self._record(actor, "access_config_deactivate", config_id, {})
        return dict(config)

    def list_access_configs(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if status is not None and status not in REGISTRY_STATES:
            raise ValidationError(
                "unknown access configuration status: %r" % (status,))
        return [
            dict(c) for c in self._access_configs.values()
            if (org_id is None or c["org_id"] == org_id)
            and (status is None or c["status"] == status)
        ]

    # -- general ledger records (the balanced-entry rule) -----------------------

    @staticmethod
    def _validate_lines(lines):
        if not isinstance(lines, (list, tuple)) or not lines:
            raise ValidationError("lines must be a non-empty list")
        validated = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each line must be an object")
            account_ref = _text(line.get("account_ref"), "account_ref")
            debit = _integer(line.get("debit_cents"), "debit_cents", minimum=0)
            credit = _integer(line.get("credit_cents"), "credit_cents", minimum=0)
            validated.append({
                "account_ref": account_ref,
                "debit_cents": debit,
                "credit_cents": credit,
            })
        return validated

    def _ledger_view(self, entry):
        view = dict(entry)
        view["lines"] = [dict(line) for line in entry["lines"]]
        view["total_debits_cents"] = sum(
            line["debit_cents"] for line in entry["lines"])
        view["total_credits_cents"] = sum(
            line["credit_cents"] for line in entry["lines"])
        return view

    def create_ledger_entry(self, actor, org_id, entry_ref, memo_label, lines):
        """Record a general-ledger entry: an opaque entry
        reference, a memo label, and debit/credit lines against
        opaque account references, in integer cents.

        The balanced-entry rule (the signature invariant): the
        entry is recorded only when :func:`_check_entry_balanced`
        accepts its lines -- every line one-sided, total debits
        equal to total credits, total positive. An unbalanced
        entry is refused whole: nothing is recorded and no id is
        consumed. Amounts are caller-recorded values; this store
        performs no posting to any external ledger.
        """
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(entry_ref, "entry_ref")
        _text(memo_label, "memo_label")
        validated = self._validate_lines(lines)
        _check_entry_balanced(validated)
        with self._lock:
            for existing in self._ledger_entries.values():
                if existing["org_id"] == org_id \
                        and existing["entry_ref"] == entry_ref:
                    raise ValidationError(
                        "entry_ref %r already exists in organization %s"
                        % (entry_ref, org_id))
            entry = {
                "id": self._mint("led-"),
                "org_id": org_id,
                "entry_ref": entry_ref,
                "memo_label": memo_label,
                "lines": validated,
                "seq": self._counters["led-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._ledger_entries[entry["id"]] = entry
        self._record(actor, "ledger_entry_create", entry["id"],
                     {"org_id": org_id, "entry_ref": entry_ref})
        return self._ledger_view(entry)

    def get_ledger_entry(self, actor, entry_id):
        self._check_role(actor, "read")
        return self._ledger_view(self._ledger_entry(entry_id))

    def list_ledger_entries(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        result = [
            self._ledger_view(e) for e in self._ledger_entries.values()
            if org_id is None or e["org_id"] == org_id
        ]
        result.sort(key=lambda e: e["seq"])
        return result

    # -- procurement records --------------------------------------------------------

    @staticmethod
    def _validate_order_lines(lines):
        if not isinstance(lines, (list, tuple)) or not lines:
            raise ValidationError("lines must be a non-empty list")
        validated = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each line must be an object")
            item_label = _text(line.get("item_label"), "item_label")
            quantity = _integer(line.get("quantity"), "quantity", minimum=1)
            unit_price = _integer(
                line.get("unit_price_cents"), "unit_price_cents", minimum=0)
            validated.append({
                "item_label": item_label,
                "quantity": quantity,
                "unit_price_cents": unit_price,
            })
        return validated

    def _order_view(self, order):
        view = dict(order)
        view["lines"] = [dict(line) for line in order["lines"]]
        view["total_cents"] = sum(
            line["quantity"] * line["unit_price_cents"]
            for line in order["lines"])
        return view

    def create_purchase_order(self, actor, org_id, po_ref, supplier_ref, lines):
        """Record a purchase order against a supplier named by
        opaque reference, with quantity / unit-price lines in
        integer cents. The order total is derived at read from
        the lines and never stored. This records the order; the
        source-to-settle execution machinery (matching, payment)
        is Extended."""
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(po_ref, "po_ref")
        _text(supplier_ref, "supplier_ref")
        validated = self._validate_order_lines(lines)
        with self._lock:
            for existing in self._purchase_orders.values():
                if existing["org_id"] == org_id \
                        and existing["po_ref"] == po_ref:
                    raise ValidationError(
                        "po_ref %r already exists in organization %s"
                        % (po_ref, org_id))
            order = {
                "id": self._mint("po-"),
                "org_id": org_id,
                "po_ref": po_ref,
                "supplier_ref": supplier_ref,
                "lines": validated,
                "status": "open",
                "seq": self._counters["po-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "status_by": None,
                "status_utc": None,
            }
            self._purchase_orders[order["id"]] = order
        self._record(actor, "purchase_order_create", order["id"],
                     {"org_id": org_id, "po_ref": po_ref})
        return self._order_view(order)

    def transition_purchase_order(self, actor, order_id, status):
        """Record a purchase order's lifecycle transition by
        recorded action: ``open -> received``,
        ``open -> closed``, ``received -> closed``. ``closed``
        is terminal."""
        self._check_role(actor, "approve")
        order = self._purchase_order(order_id)
        if status not in PURCHASE_ORDER_STATES:
            raise ValidationError("unknown purchase order status: %r" % (status,))
        allowed = {
            "open": ("received", "closed"),
            "received": ("closed",),
            "closed": (),
        }
        with self._lock:
            if status not in allowed[order["status"]]:
                raise ValidationError(
                    "purchase order %s is %r; status %r is not reachable"
                    % (order_id, order["status"], status))
            order["status"] = status
            order["status_by"] = actor_name(actor)
            order["status_utc"] = _utc_now().isoformat()
        self._record(actor, "purchase_order_transition", order_id,
                     {"status": status})
        return self._order_view(order)

    def get_purchase_order(self, actor, order_id):
        self._check_role(actor, "read")
        return self._order_view(self._purchase_order(order_id))

    def list_purchase_orders(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if status is not None and status not in PURCHASE_ORDER_STATES:
            raise ValidationError("unknown purchase order status: %r" % (status,))
        result = [
            self._order_view(o) for o in self._purchase_orders.values()
            if (org_id is None or o["org_id"] == org_id)
            and (status is None or o["status"] == status)
        ]
        result.sort(key=lambda o: o["seq"])
        return result

    # -- expense records --------------------------------------------------------------

    @staticmethod
    def _validate_expense_lines(lines):
        if not isinstance(lines, (list, tuple)) or not lines:
            raise ValidationError("lines must be a non-empty list")
        validated = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each line must be an object")
            category = _text(line.get("category_label"), "category_label")
            amount = _integer(line.get("amount_cents"), "amount_cents",
                              minimum=0)
            validated.append({
                "category_label": category,
                "amount_cents": amount,
            })
        return validated

    def _expense_view(self, report):
        view = dict(report)
        view["lines"] = [dict(line) for line in report["lines"]]
        view["total_cents"] = sum(
            line["amount_cents"] for line in report["lines"])
        return view

    def create_expense_report(self, actor, org_id, person_ref, report_ref,
                              lines):
        """Record an expense report for a person (who must have a
        person record in the organization), with categorized
        amount lines in integer cents. The report total is
        derived at read and never stored. Policy enforcement and
        fraud detection over reports are Extended engines; this
        is the report record and its recorded outcome."""
        self._check_role(actor, "record")
        self._organization(org_id)
        self._person(org_id, person_ref)
        _text(report_ref, "report_ref")
        validated = self._validate_expense_lines(lines)
        with self._lock:
            for existing in self._expense_reports.values():
                if existing["org_id"] == org_id \
                        and existing["report_ref"] == report_ref:
                    raise ValidationError(
                        "report_ref %r already exists in organization %s"
                        % (report_ref, org_id))
            report = {
                "id": self._mint("exp-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "report_ref": report_ref,
                "lines": validated,
                "status": "submitted",
                "seq": self._counters["exp-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "outcome_by": None,
                "outcome_utc": None,
                "outcome_note": None,
            }
            self._expense_reports[report["id"]] = report
        self._record(actor, "expense_report_create", report["id"],
                     {"org_id": org_id, "report_ref": report_ref})
        return self._expense_view(report)

    def record_expense_outcome(self, actor, report_id, outcome, note=None):
        """Record an expense report's outcome by recorded action:
        ``submitted -> approved`` or ``submitted -> rejected``.
        Both outcomes are terminal."""
        self._check_role(actor, "approve")
        report = self._expense_report(report_id)
        if outcome not in ("approved", "rejected"):
            raise ValidationError("unknown expense outcome: %r" % (outcome,))
        _optional_text(note, "note")
        with self._lock:
            if report["status"] != "submitted":
                raise ValidationError(
                    "expense report %s is %r; outcome %r is not reachable"
                    % (report_id, report["status"], outcome))
            report["status"] = outcome
            report["outcome_by"] = actor_name(actor)
            report["outcome_utc"] = _utc_now().isoformat()
            report["outcome_note"] = note
        self._record(actor, "expense_report_outcome", report_id,
                     {"outcome": outcome})
        return self._expense_view(report)

    def get_expense_report(self, actor, report_id):
        self._check_role(actor, "read")
        return self._expense_view(self._expense_report(report_id))

    def list_expense_reports(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if status is not None and status not in EXPENSE_STATES:
            raise ValidationError("unknown expense status: %r" % (status,))
        result = [
            self._expense_view(r) for r in self._expense_reports.values()
            if (org_id is None or r["org_id"] == org_id)
            and (status is None or r["status"] == status)
        ]
        result.sort(key=lambda r: r["seq"])
        return result

    # -- person records (the system of record) --------------------------------------

    def create_person(self, actor, org_id, person_ref, department_label,
                      role_label):
        """Record a person in the system of record: an opaque
        ``person_ref`` (unique within the organization), a
        department label, and a role label. The shape is pinned:
        no field can hold a name, an email address, a phone
        number, or any other real identifier -- the record is a
        reference, and everything else about the person stays
        with the embedding organization."""
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(person_ref, "person_ref")
        _text(department_label, "department_label")
        _text(role_label, "role_label")
        with self._lock:
            for existing in self._persons.values():
                if existing["org_id"] == org_id \
                        and existing["person_ref"] == person_ref:
                    raise ValidationError(
                        "person_ref %r already exists in organization %s"
                        % (person_ref, org_id))
            person = {
                "id": self._mint("per-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "department_label": department_label,
                "role_label": role_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._persons[person["id"]] = person
        self._record(actor, "person_create", person["id"],
                     {"org_id": org_id, "person_ref": person_ref})
        return dict(person)

    def get_person(self, actor, person_id):
        self._check_role(actor, "read")
        return dict(self._person_by_id(person_id))

    def list_persons(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(p) for p in self._persons.values()
            if org_id is None or p["org_id"] == org_id
        ]

    # -- time & absence records -------------------------------------------------------

    def create_time_entry(self, actor, org_id, person_ref, work_date, minutes):
        """Record a time entry for a person: a calendar date and
        a whole number of minutes (integers only)."""
        self._check_role(actor, "record")
        self._organization(org_id)
        self._person(org_id, person_ref)
        day = _date(work_date, "work_date")
        _integer(minutes, "minutes", minimum=1)
        with self._lock:
            entry = {
                "id": self._mint("tim-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "work_date": day,
                "minutes": minutes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._time_entries[entry["id"]] = entry
        self._record(actor, "time_entry_create", entry["id"],
                     {"org_id": org_id, "person_ref": person_ref})
        return dict(entry)

    def list_time_entries(self, actor, org_id=None, person_ref=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(t) for t in self._time_entries.values()
            if (org_id is None or t["org_id"] == org_id)
            and (person_ref is None or t["person_ref"] == person_ref)
        ]

    def create_absence(self, actor, org_id, person_ref, kind_label,
                       from_date, to_date):
        """Record an absence for a person: a caller-stated kind
        label and an inclusive date range."""
        self._check_role(actor, "record")
        self._organization(org_id)
        self._person(org_id, person_ref)
        _text(kind_label, "kind_label")
        start = _date(from_date, "from_date")
        end = _date(to_date, "to_date")
        if end < start:
            raise ValidationError("to_date must not precede from_date")
        with self._lock:
            absence = {
                "id": self._mint("abs-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "kind_label": kind_label,
                "from_date": start,
                "to_date": end,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._absences[absence["id"]] = absence
        self._record(actor, "absence_create", absence["id"],
                     {"org_id": org_id, "person_ref": person_ref})
        return dict(absence)

    def list_absences(self, actor, org_id=None, person_ref=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(a) for a in self._absences.values()
            if (org_id is None or a["org_id"] == org_id)
            and (person_ref is None or a["person_ref"] == person_ref)
        ]

    # -- payroll run records --------------------------------------------------------------

    def create_payroll_run(self, actor, org_id, person_ref, run_ref,
                           period_label, gross_cents):
        """Record a payroll run for a person: a run reference, a
        period label, and a gross amount in integer cents. The
        amount is caller-recorded: this store performs no pay
        calculation, no job costing, and no disbursement -- the
        payroll calculation engine is Extended."""
        self._check_role(actor, "record")
        self._organization(org_id)
        self._person(org_id, person_ref)
        _text(run_ref, "run_ref")
        _text(period_label, "period_label")
        _integer(gross_cents, "gross_cents", minimum=0)
        with self._lock:
            for existing in self._payroll_runs.values():
                if existing["org_id"] == org_id \
                        and existing["run_ref"] == run_ref:
                    raise ValidationError(
                        "run_ref %r already exists in organization %s"
                        % (run_ref, org_id))
            run = {
                "id": self._mint("pay-"),
                "org_id": org_id,
                "person_ref": person_ref,
                "run_ref": run_ref,
                "period_label": period_label,
                "gross_cents": gross_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._payroll_runs[run["id"]] = run
        self._record(actor, "payroll_run_create", run["id"],
                     {"org_id": org_id, "run_ref": run_ref})
        return dict(run)

    def list_payroll_runs(self, actor, org_id=None, person_ref=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(r) for r in self._payroll_runs.values()
            if (org_id is None or r["org_id"] == org_id)
            and (person_ref is None or r["person_ref"] == person_ref)
        ]

    # -- asset records ------------------------------------------------------------------------

    def create_asset(self, actor, org_id, asset_ref, label, criticality_label):
        """Record an asset: an opaque ``asset_ref`` (unique
        within the organization), a label, and a caller-stated
        criticality label (a label, not a computed assessment --
        this store computes no condition or criticality score)."""
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(asset_ref, "asset_ref")
        _text(label, "label")
        _text(criticality_label, "criticality_label")
        with self._lock:
            for existing in self._assets.values():
                if existing["org_id"] == org_id \
                        and existing["asset_ref"] == asset_ref:
                    raise ValidationError(
                        "asset_ref %r already exists in organization %s"
                        % (asset_ref, org_id))
            asset = {
                "id": self._mint("ast-"),
                "org_id": org_id,
                "asset_ref": asset_ref,
                "label": label,
                "criticality_label": criticality_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._assets[asset["id"]] = asset
        self._record(actor, "asset_create", asset["id"],
                     {"org_id": org_id, "asset_ref": asset_ref})
        return dict(asset)

    def get_asset(self, actor, asset_id):
        self._check_role(actor, "read")
        return dict(self._asset(asset_id))

    def list_assets(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(a) for a in self._assets.values()
            if org_id is None or a["org_id"] == org_id
        ]

    # -- work order records ----------------------------------------------------------------------

    def create_work_order(self, actor, org_id, asset_id, wo_ref, kind):
        """Open a maintenance work order against an asset of the
        organization. ``kind`` is the fork's own vocabulary --
        ``preventive`` or ``corrective``. Scheduling, dispatch,
        and the maintenance execution itself are Extended; this
        is the work order record and its recorded lifecycle."""
        self._check_role(actor, "record")
        self._organization(org_id)
        asset = self._asset(asset_id)
        if asset["org_id"] != org_id:
            raise ValidationError(
                "asset %s does not belong to organization %s"
                % (asset_id, org_id))
        _text(wo_ref, "wo_ref")
        if kind not in WORK_ORDER_KINDS:
            raise ValidationError("unknown work order kind: %r" % (kind,))
        with self._lock:
            for existing in self._work_orders.values():
                if existing["org_id"] == org_id \
                        and existing["wo_ref"] == wo_ref:
                    raise ValidationError(
                        "wo_ref %r already exists in organization %s"
                        % (wo_ref, org_id))
            order = {
                "id": self._mint("wo-"),
                "org_id": org_id,
                "asset_id": asset_id,
                "wo_ref": wo_ref,
                "kind": kind,
                "status": "open",
                "assignee_ref": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "status_by": None,
                "status_utc": None,
            }
            self._work_orders[order["id"]] = order
        self._record(actor, "work_order_create", order["id"],
                     {"org_id": org_id, "asset_id": asset_id})
        return dict(order)

    def transition_work_order(self, actor, order_id, action, assignee_ref=None):
        """Record a work order transition by recorded action:
        ``assign`` (``open -> assigned``, naming the assignee by
        opaque reference) or ``complete`` (``open -> completed``
        or ``assigned -> completed``). ``completed`` is
        terminal."""
        self._check_role(actor, "record")
        order = self._work_order(order_id)
        if action not in ("assign", "complete"):
            raise ValidationError("unknown work order action: %r" % (action,))
        if action == "assign":
            _text(assignee_ref, "assignee_ref")
        with self._lock:
            if action == "assign":
                if order["status"] != "open":
                    raise ValidationError(
                        "work order %s is %r; only an open work order "
                        "can be assigned" % (order_id, order["status"]))
                order["status"] = "assigned"
                order["assignee_ref"] = assignee_ref
            else:
                if order["status"] == "completed":
                    raise ValidationError(
                        "work order %s is already completed" % order_id)
                order["status"] = "completed"
            order["status_by"] = actor_name(actor)
            order["status_utc"] = _utc_now().isoformat()
        self._record(actor, "work_order_transition", order_id,
                     {"action": action})
        return dict(order)

    def list_work_orders(self, actor, org_id=None, asset_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if asset_id is not None:
            self._asset(asset_id)
        if status is not None and status not in WORK_ORDER_STATES:
            raise ValidationError("unknown work order status: %r" % (status,))
        return [
            dict(w) for w in self._work_orders.values()
            if (org_id is None or w["org_id"] == org_id)
            and (asset_id is None or w["asset_id"] == asset_id)
            and (status is None or w["status"] == status)
        ]

    # -- inventory records ---------------------------------------------------------------------------

    def create_inventory_item(self, actor, org_id, item_ref, label, quantity):
        """Record an inventory item: an opaque ``item_ref``
        (unique within the organization), a label, and an opening
        quantity on hand (a non-negative integer). Quantities
        change only through recorded adjustments."""
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(item_ref, "item_ref")
        _text(label, "label")
        _integer(quantity, "quantity", minimum=0)
        with self._lock:
            for existing in self._inventory_items.values():
                if existing["org_id"] == org_id \
                        and existing["item_ref"] == item_ref:
                    raise ValidationError(
                        "item_ref %r already exists in organization %s"
                        % (item_ref, org_id))
            item = {
                "id": self._mint("inv-"),
                "org_id": org_id,
                "item_ref": item_ref,
                "label": label,
                "quantity_on_hand": quantity,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._inventory_items[item["id"]] = item
        self._record(actor, "inventory_item_create", item["id"],
                     {"org_id": org_id, "item_ref": item_ref})
        return dict(item)

    def adjust_inventory(self, actor, item_id, delta):
        """Record an inventory adjustment: a signed integer delta
        applied to the quantity on hand. The resulting quantity
        may not go negative -- stock cannot be issued that the
        records do not hold."""
        self._check_role(actor, "record")
        item = self._inventory_item(item_id)
        _integer(delta, "delta")
        if delta == 0:
            raise ValidationError("delta must not be zero")
        with self._lock:
            new_quantity = item["quantity_on_hand"] + delta
            if new_quantity < 0:
                raise ValidationError(
                    "adjustment of %d would take item %s below zero "
                    "(%d on hand)" % (delta, item_id, item["quantity_on_hand"]))
            item["quantity_on_hand"] = new_quantity
        self._record(actor, "inventory_adjust", item_id, {"delta": delta})
        return dict(item)

    def list_inventory_items(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(i) for i in self._inventory_items.values()
            if org_id is None or i["org_id"] == org_id
        ]

    # -- document records (metadata only) --------------------------------------------------------------

    def create_document(self, actor, org_id, doc_ref, label, purpose_label):
        """Record a business document's metadata: an opaque
        ``doc_ref`` (unique within the organization), a label,
        and a business-purpose label. Metadata only -- the shape
        has no field that could hold document content, and
        capture/conversion machinery is Extended."""
        self._check_role(actor, "record")
        self._organization(org_id)
        _text(doc_ref, "doc_ref")
        _text(label, "label")
        _text(purpose_label, "purpose_label")
        with self._lock:
            for existing in self._documents.values():
                if existing["org_id"] == org_id \
                        and existing["doc_ref"] == doc_ref:
                    raise ValidationError(
                        "doc_ref %r already exists in organization %s"
                        % (doc_ref, org_id))
            document = {
                "id": self._mint("doc-"),
                "org_id": org_id,
                "doc_ref": doc_ref,
                "label": label,
                "purpose_label": purpose_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._documents[document["id"]] = document
        self._record(actor, "document_create", document["id"],
                     {"org_id": org_id, "doc_ref": doc_ref})
        return dict(document)

    def list_documents(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(d) for d in self._documents.values()
            if org_id is None or d["org_id"] == org_id
        ]

    # -- integration & workflow registries (records only) ------------------------------------------------

    def create_integration(self, actor, org_id, kind, label):
        """Register an integration record for an organization:
        an ``integration_platform`` record (the suite's
        integration platform) or an ``api_gateway`` record (its
        API gateway and policy surface). Records only:
        registering an integration connects nothing, routes no
        call, and enforces no policy -- the runtimes are
        Extended."""
        self._check_role(actor, "register")
        self._organization(org_id)
        if kind not in INTEGRATION_KINDS:
            raise ValidationError("unknown integration kind: %r" % (kind,))
        _text(label, "label")
        with self._lock:
            integration = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "kind": kind,
                "label": label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._integrations[integration["id"]] = integration
        self._record(actor, "integration_create", integration["id"],
                     {"org_id": org_id, "kind": kind})
        return dict(integration)

    def deactivate_integration(self, actor, integration_id):
        """Deactivate an integration record by recorded action."""
        self._check_role(actor, "register")
        integration = self._integration(integration_id)
        with self._lock:
            if integration["status"] == "inactive":
                raise ValidationError(
                    "integration %s is already inactive" % integration_id)
            integration["status"] = "inactive"
        self._record(actor, "integration_deactivate", integration_id, {})
        return dict(integration)

    def list_integrations(self, actor, org_id=None, kind=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if kind is not None and kind not in INTEGRATION_KINDS:
            raise ValidationError("unknown integration kind: %r" % (kind,))
        return [
            dict(i) for i in self._integrations.values()
            if (org_id is None or i["org_id"] == org_id)
            and (kind is None or i["kind"] == kind)
        ]

    def create_workflow(self, actor, org_id, label, trigger_label):
        """Register a business-process workflow record: a label
        and a caller-stated trigger label. Records only: the
        registry defines the shape of a process record and never
        executes one -- there is no run, fire, or execute
        operation anywhere in this build, pinned by test. The
        automation runtime is Extended."""
        self._check_role(actor, "register")
        self._organization(org_id)
        _text(label, "label")
        _text(trigger_label, "trigger_label")
        with self._lock:
            workflow = {
                "id": self._mint("wfl-"),
                "org_id": org_id,
                "label": label,
                "trigger_label": trigger_label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[workflow["id"]] = workflow
        self._record(actor, "workflow_create", workflow["id"],
                     {"org_id": org_id})
        return dict(workflow)

    def deactivate_workflow(self, actor, workflow_id):
        """Deactivate a workflow record by recorded action."""
        self._check_role(actor, "register")
        workflow = self._workflow(workflow_id)
        with self._lock:
            if workflow["status"] == "inactive":
                raise ValidationError(
                    "workflow %s is already inactive" % workflow_id)
            workflow["status"] = "inactive"
        self._record(actor, "workflow_deactivate", workflow_id, {})
        return dict(workflow)

    def list_workflows(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if status is not None and status not in REGISTRY_STATES:
            raise ValidationError("unknown workflow status: %r" % (status,))
        return [
            dict(w) for w in self._workflows.values()
            if (org_id is None or w["org_id"] == org_id)
            and (status is None or w["status"] == status)
        ]

    def audit_read(self, actor):
        """Return the audit trail. Requires the ``audit_read``
        permission (admin-only in the permission matrix)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"entries": entries, "count": len(entries)}

    # -- search and summary ---------------------------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over
        organizations (ref and label), applications (reference
        and label), persons (reference, department and role
        labels), assets (reference and label), and documents
        (reference and label). Record metadata only."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        organizations = [
            dict(o) for o in self._organizations.values()
            if needle in o["ref"].lower() or needle in o["label"].lower()
        ]
        applications = [
            dict(a) for a in self._applications.values()
            if needle in a["app_ref"].lower()
            or needle in a["label"].lower()
        ]
        persons = [
            dict(p) for p in self._persons.values()
            if needle in p["person_ref"].lower()
            or needle in p["department_label"].lower()
            or needle in p["role_label"].lower()
        ]
        assets = [
            dict(a) for a in self._assets.values()
            if needle in a["asset_ref"].lower()
            or needle in a["label"].lower()
        ]
        documents = [
            dict(d) for d in self._documents.values()
            if needle in d["doc_ref"].lower()
            or needle in d["label"].lower()
        ]
        return {
            "organizations": organizations,
            "applications": applications,
            "persons": persons,
            "assets": assets,
            "documents": documents,
        }

    def summary(self, actor):
        """Counts over the whole registry, computed on read from
        records only. Counts and recorded values -- never
        scores."""
        self._check_role(actor, "read")
        applications_by_status = {state: 0 for state in REGISTRY_STATES}
        for application in self._applications.values():
            applications_by_status[application["status"]] += 1
        orders_by_status = {state: 0 for state in PURCHASE_ORDER_STATES}
        for order in self._purchase_orders.values():
            orders_by_status[order["status"]] += 1
        expenses_by_status = {state: 0 for state in EXPENSE_STATES}
        for report in self._expense_reports.values():
            expenses_by_status[report["status"]] += 1
        work_orders_by_status = {state: 0 for state in WORK_ORDER_STATES}
        for order in self._work_orders.values():
            work_orders_by_status[order["status"]] += 1
        integrations_by_kind = {kind: 0 for kind in INTEGRATION_KINDS}
        for integration in self._integrations.values():
            integrations_by_kind[integration["kind"]] += 1
        return {
            "organizations": len(self._organizations),
            "applications": len(self._applications),
            "applications_by_status": applications_by_status,
            "access_configs": len(self._access_configs),
            "ledger_entries": len(self._ledger_entries),
            "purchase_orders": len(self._purchase_orders),
            "purchase_orders_by_status": orders_by_status,
            "expense_reports": len(self._expense_reports),
            "expense_reports_by_status": expenses_by_status,
            "persons": len(self._persons),
            "time_entries": len(self._time_entries),
            "absence_records": len(self._absences),
            "payroll_runs": len(self._payroll_runs),
            "assets": len(self._assets),
            "work_orders": len(self._work_orders),
            "work_orders_by_status": work_orders_by_status,
            "inventory_items": len(self._inventory_items),
            "documents": len(self._documents),
            "integrations_by_kind": integrations_by_kind,
            "workflows": len(self._workflows),
        }
