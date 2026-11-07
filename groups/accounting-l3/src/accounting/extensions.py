"""Final GAPS batch extensions for the Accounting L3-adjacent build.

This module is the extension surface built for the group's Extended
families (see ``UNION-SPEC.md`` function ranking, rows 13-25 and the
AI/analytics family in row 1). It is a NEW module added by the final
GAPS batch: every pre-existing core module in this package stays
byte-identical, and nothing here weakens the High-baseline uplifts
(hash-chained audit, fail-closed writes, the auditor role, logon
lockout). The extension store writes to the same hash-chained
:class:`~accounting.audit.AuditLog` the core uses, through the same
fail-closed discipline: if an audit write raises
:class:`~accounting.errors.AuditWriteError`, the whole extension
mutation rolls back (no object created, no id consumed).

Doctrines, carried from the core and applied unchanged:

- **Money is integer cents.** Every amount field is ``*_cents`` and
  must be a Python ``int``; booleans and floats are rejected at the
  boundary, even integral floats (core validators, reused verbatim).
- **Opaque references only.** People, suppliers, wallets, documents
  and signers are caller-supplied opaque ``*_ref`` strings. No field
  can hold a name-and-address pair, an email, a bank account, a card
  number, or any other real PII; the record shapes are pinned by
  tests exactly as the core pins its shapes.
- **Derived, never stored, where a value is a derivation.** Report
  totals, remaining amounts, utilization, depreciation, risk scores,
  fulfillment status, custody heads and retention due-ness are all
  computed at read time in the ``*_view`` / summary functions and are
  never keys on a stored record (pinned by tests).
- **Separation of duties (AC-5).** Approving, activating, closing or
  filing a record is never done by its creator, where a workflow has
  an approval step.
- **Append-only audit (AU).** Every successful mutation is recorded.
  Following the core store's convention, denied attempts at this
  layer are not double-recorded here; the service layer owns denied
  attempt recording.
- **Records, not execution.** Nothing in this module moves money,
  submits a filing, traces a chain, transmits a document, or talks
  to any external system. The e-signature family goes one step
  further and ships as a labeled reference implementation: every
  signature record carries ``reference_stub: True`` and its status
  vocabulary contains no state that claims a document was sent or
  signed through a signing service.
"""

import copy
import functools
import re
import threading
from datetime import date

from .access import require
from .audit import actor_name
from .errors import AuditWriteError, NotFoundError, PermissionDenied, ValidationError
from .store import (
    _maybe_require,
    _require_int,
    _validate_cents_any,
    _validate_cents_nonnegative,
    _validate_cents_positive,
    _validate_date,
    _validate_non_empty,
    _validate_period,
    _validate_string,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SEVERITIES = ("low", "medium", "high", "critical")
COST_TYPES = ("direct", "indirect")
SIGNATURE_EVENT_TYPES = ("prepared", "viewed", "signed_declared")


def _fail_closed(method):
    """Roll the extension state back if the audit write fails (AU-5)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = (copy.deepcopy(self._data), dict(self._counters))
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._data, self._counters = snapshot
            raise

    return wrapper


def _validate_choice(value, choices, what):
    if value not in choices:
        raise ValidationError("%s must be one of %r: %r" % (what, choices, value))
    return value


def _validate_int_range(value, what, low, high):
    _require_int(value, what)
    if value < low or value > high:
        raise ValidationError("%s must be between %d and %d" % (what, low, high))
    return value


def _validate_ref(value, what):
    return _validate_non_empty(value, what)


def _add_months(date_str, months):
    """Return the ISO date ``months`` calendar months after ``date_str``."""
    year, month, day = (int(part) for part in date_str.split("-"))
    total = (year * 12 + (month - 1)) + months
    new_year, new_month_zero = divmod(total, 12)
    new_month = new_month_zero + 1
    # Clamp the day to the target month's length.
    if new_month == 12:
        next_first = date(new_year + 1, 1, 1)
    else:
        next_first = date(new_year, new_month + 1, 1)
    last_day = (next_first - date(new_year, new_month, 1)).days
    return date(new_year, new_month, min(day, last_day)).isoformat()


class ExtensionStore:
    """In-memory records substrate for the group's Extended families."""

    _COLLECTIONS = (
        "datasets", "insights", "projects", "project_spend", "risks",
        "risk_controls", "engagements", "findings", "assets",
        "retention_policies", "retention_assignments", "dispositions",
        "forecasts", "suppliers", "purchase_orders", "receipts",
        "awards", "award_costs", "crypto_cases", "wallet_observations",
        "time_entries", "payroll_runs", "pay_items", "tax_filings",
        "tax_lines", "forensic_cases", "evidence_items",
        "signature_requests", "signature_events",
    )

    _PREFIXES = {
        "datasets": "ana", "insights": "ins", "projects": "prj",
        "project_spend": "psp", "risks": "rsk", "risk_controls": "rct",
        "engagements": "eng", "findings": "fnd", "assets": "ast",
        "retention_policies": "rtp", "retention_assignments": "rta",
        "dispositions": "dsp", "forecasts": "fct", "suppliers": "sup",
        "purchase_orders": "po", "receipts": "rcp", "awards": "awd",
        "award_costs": "awc", "crypto_cases": "crc",
        "wallet_observations": "wob", "time_entries": "tim",
        "payroll_runs": "prl", "pay_items": "pay", "tax_filings": "tax",
        "tax_lines": "txl", "forensic_cases": "for",
        "evidence_items": "evd", "signature_requests": "sig",
        "signature_events": "sge",
    }

    def __init__(self, audit=None):
        self.audit = audit
        self._data = {name: {} for name in self._COLLECTIONS}
        self._counters = {name: 0 for name in self._COLLECTIONS}
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, collection):
        self._counters[collection] += 1
        return "%s-%d" % (self._PREFIXES[collection], self._counters[collection])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _require(self, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, action)

    def _get(self, collection, record_id, what):
        record = self._data[collection].get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_book(self, record, book_id):
        if record["book_id"] != book_id:
            raise NotFoundError("record not found in book %r" % (book_id,))

    @staticmethod
    def _check_not_creator(record, actor, what):
        if actor_name(actor) == record["created_by"]:
            raise PermissionDenied(
                "separation of duties: the creator may not %s their own record"
                % (what,)
            )

    def _create(self, collection, fields, actor, action):
        record_id = self._next_id(collection)
        record = {"id": record_id}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        self._data[collection][record_id] = record
        self._audit(actor, action, record_id, {"book_id": record["book_id"]})
        return copy.deepcopy(record)

    # -- 1. AI / analytics & BI (Extended, claimed by ACQBOT) --------

    @_fail_closed
    def create_dataset(self, book_id, name, source_ref, actor):
        """Register an analytics dataset by opaque source reference."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(name, "dataset name")
        _validate_ref(source_ref, "source_ref")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "datasets",
                {"book_id": book_id, "name": name, "source_ref": source_ref},
                actor, "ext_dataset_create",
            )

    @_fail_closed
    def record_insight(self, book_id, dataset_id, title, metric_name,
                       metric_value_cents, actor):
        """Record one analytics insight over a registered dataset.

        The insight is a record of an analytic result; this substrate
        performs no inference and no model execution.
        """
        _validate_non_empty(title, "insight title")
        _validate_non_empty(metric_name, "metric_name")
        _validate_cents_any(metric_value_cents, "metric_value_cents")
        self._require(actor, "enter")
        with self._lock:
            dataset = self._get("datasets", dataset_id, "dataset")
            self._check_book(dataset, book_id)
            return self._create(
                "insights",
                {"book_id": book_id, "dataset_id": dataset_id,
                 "title": title, "metric_name": metric_name,
                 "metric_value_cents": metric_value_cents},
                actor, "ext_insight_create",
            )

    def analytics_summary(self, book_id, actor):
        """Derived at read: dataset/insight counts and metric total."""
        self._require(actor, "read")
        with self._lock:
            datasets = [r for r in self._data["datasets"].values()
                        if r["book_id"] == book_id]
            insights = [r for r in self._data["insights"].values()
                        if r["book_id"] == book_id]
            return {
                "book_id": book_id,
                "dataset_count": len(datasets),
                "insight_count": len(insights),
                "total_metric_cents": sum(
                    r["metric_value_cents"] for r in insights),
            }

    # -- 2. Project / program / portfolio management ----------------

    @_fail_closed
    def create_project(self, book_id, name, sponsor_ref, budget_cents, actor):
        """Create a project record in ``draft`` with a budget in cents."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(name, "project name")
        _validate_ref(sponsor_ref, "sponsor_ref")
        _validate_cents_positive(budget_cents, "budget_cents")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "projects",
                {"book_id": book_id, "name": name,
                 "sponsor_ref": sponsor_ref, "budget_cents": budget_cents,
                 "status": "draft"},
                actor, "ext_project_create",
            )

    @_fail_closed
    def activate_project(self, book_id, project_id, actor):
        """Activate a draft project; approver is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            project = self._get("projects", project_id, "project")
            self._check_book(project, book_id)
            self._check_not_creator(project, actor, "activate")
            if project["status"] != "draft":
                raise ValidationError("only a draft project can be activated")
            project["status"] = "active"
            project["activated_by"] = actor_name(actor)
            self._audit(actor, "ext_project_activate", project_id,
                        {"book_id": book_id})
            return copy.deepcopy(project)

    @_fail_closed
    def record_project_spend(self, book_id, project_id, amount_cents,
                             description, actor):
        """Record spend against an active project, capped at its budget."""
        _validate_cents_positive(amount_cents, "amount_cents")
        _validate_non_empty(description, "spend description")
        self._require(actor, "enter")
        with self._lock:
            project = self._get("projects", project_id, "project")
            self._check_book(project, book_id)
            if project["status"] != "active":
                raise ValidationError("spend can only be recorded on an active project")
            spent = sum(r["amount_cents"]
                        for r in self._data["project_spend"].values()
                        if r["project_id"] == project_id)
            if spent + amount_cents > project["budget_cents"]:
                raise ValidationError("project spend would exceed the project budget")
            return self._create(
                "project_spend",
                {"book_id": book_id, "project_id": project_id,
                 "amount_cents": amount_cents, "description": description},
                actor, "ext_project_spend",
            )

    def project_view(self, book_id, project_id, actor):
        """Derived at read: spent, remaining, utilization basis points."""
        self._require(actor, "read")
        with self._lock:
            project = self._get("projects", project_id, "project")
            self._check_book(project, book_id)
            spent = sum(r["amount_cents"]
                        for r in self._data["project_spend"].values()
                        if r["project_id"] == project_id)
            view = copy.deepcopy(project)
            view["spent_cents"] = spent
            view["remaining_cents"] = project["budget_cents"] - spent
            view["utilization_bps"] = (
                spent * 10000 // project["budget_cents"])
            return view

    # -- 3. Risk register & GRC suites -------------------------------

    @_fail_closed
    def create_risk(self, book_id, title, category, likelihood,
                    impact_cents, owner_ref, actor):
        """Register a risk. Likelihood is an integer scale 1..5."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(title, "risk title")
        _validate_non_empty(category, "risk category")
        _validate_int_range(likelihood, "likelihood", 1, 5)
        _validate_cents_nonnegative(impact_cents, "impact_cents")
        _validate_ref(owner_ref, "owner_ref")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "risks",
                {"book_id": book_id, "title": title, "category": category,
                 "likelihood": likelihood, "impact_cents": impact_cents,
                 "owner_ref": owner_ref, "status": "open"},
                actor, "ext_risk_create",
            )

    @_fail_closed
    def add_risk_control(self, book_id, risk_id, description, actor):
        """Attach a mitigation/control record to a risk."""
        _validate_non_empty(description, "control description")
        self._require(actor, "enter")
        with self._lock:
            risk = self._get("risks", risk_id, "risk")
            self._check_book(risk, book_id)
            return self._create(
                "risk_controls",
                {"book_id": book_id, "risk_id": risk_id,
                 "description": description},
                actor, "ext_risk_control_create",
            )

    @_fail_closed
    def accept_risk(self, book_id, risk_id, actor):
        """Accept an open risk; the accepter is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            risk = self._get("risks", risk_id, "risk")
            self._check_book(risk, book_id)
            self._check_not_creator(risk, actor, "accept")
            if risk["status"] != "open":
                raise ValidationError("only an open risk can be accepted")
            risk["status"] = "accepted"
            risk["accepted_by"] = actor_name(actor)
            self._audit(actor, "ext_risk_accept", risk_id, {"book_id": book_id})
            return copy.deepcopy(risk)

    def risk_view(self, book_id, risk_id, actor):
        """Derived at read: score (likelihood x impact) and control count."""
        self._require(actor, "read")
        with self._lock:
            risk = self._get("risks", risk_id, "risk")
            self._check_book(risk, book_id)
            view = copy.deepcopy(risk)
            view["risk_score_cents"] = risk["likelihood"] * risk["impact_cents"]
            view["control_count"] = sum(
                1 for r in self._data["risk_controls"].values()
                if r["risk_id"] == risk_id)
            return view

    # -- 4. Audit-management workbenches -----------------------------

    @_fail_closed
    def create_engagement(self, book_id, title, scope, period, actor):
        """Open an audit engagement for a fiscal period (YYYY-MM)."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(title, "engagement title")
        _validate_non_empty(scope, "engagement scope")
        _validate_period(period, "period")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "engagements",
                {"book_id": book_id, "title": title, "scope": scope,
                 "period": period, "closed": False},
                actor, "ext_engagement_create",
            )

    @_fail_closed
    def add_finding(self, book_id, engagement_id, title, severity, actor):
        """Add a finding to an open engagement."""
        _validate_non_empty(title, "finding title")
        _validate_choice(severity, SEVERITIES, "severity")
        self._require(actor, "enter")
        with self._lock:
            engagement = self._get("engagements", engagement_id, "engagement")
            self._check_book(engagement, book_id)
            if engagement["closed"]:
                raise ValidationError("findings cannot be added to a closed engagement")
            return self._create(
                "findings",
                {"book_id": book_id, "engagement_id": engagement_id,
                 "title": title, "severity": severity, "status": "open",
                 "resolution": None},
                actor, "ext_finding_create",
            )

    @_fail_closed
    def resolve_finding(self, book_id, finding_id, resolution, actor):
        """Resolve a finding; the resolver is never its creator (SoD)."""
        _validate_non_empty(resolution, "resolution")
        self._require(actor, "approve")
        with self._lock:
            finding = self._get("findings", finding_id, "finding")
            self._check_book(finding, book_id)
            self._check_not_creator(finding, actor, "resolve")
            if finding["status"] != "open":
                raise ValidationError("only an open finding can be resolved")
            finding["status"] = "resolved"
            finding["resolution"] = resolution
            finding["resolved_by"] = actor_name(actor)
            self._audit(actor, "ext_finding_resolve", finding_id,
                        {"book_id": book_id})
            return copy.deepcopy(finding)

    @_fail_closed
    def close_engagement(self, book_id, engagement_id, actor):
        """Close an engagement only when it has no open findings."""
        self._require(actor, "approve")
        with self._lock:
            engagement = self._get("engagements", engagement_id, "engagement")
            self._check_book(engagement, book_id)
            self._check_not_creator(engagement, actor, "close")
            open_count = sum(
                1 for r in self._data["findings"].values()
                if r["engagement_id"] == engagement_id and r["status"] == "open")
            if open_count:
                raise ValidationError(
                    "engagement cannot close with %d open finding(s)" % open_count)
            engagement["closed"] = True
            engagement["closed_by"] = actor_name(actor)
            self._audit(actor, "ext_engagement_close", engagement_id,
                        {"book_id": book_id})
            return copy.deepcopy(engagement)

    def engagement_view(self, book_id, engagement_id, actor):
        """Derived at read: finding counts by state."""
        self._require(actor, "read")
        with self._lock:
            engagement = self._get("engagements", engagement_id, "engagement")
            self._check_book(engagement, book_id)
            findings = [r for r in self._data["findings"].values()
                        if r["engagement_id"] == engagement_id]
            view = copy.deepcopy(engagement)
            view["finding_count"] = len(findings)
            view["open_finding_count"] = sum(
                1 for r in findings if r["status"] == "open")
            return view

    # -- 5. Fixed-asset registers ------------------------------------

    @_fail_closed
    def register_fixed_asset(self, book_id, name, cost_cents, salvage_cents,
                             useful_life_months, placed_date, actor):
        """Register a fixed asset. Salvage may not exceed cost."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(name, "asset name")
        _validate_cents_positive(cost_cents, "cost_cents")
        _validate_cents_nonnegative(salvage_cents, "salvage_cents")
        if salvage_cents > cost_cents:
            raise ValidationError("salvage_cents may not exceed cost_cents")
        _require_int(useful_life_months, "useful_life_months")
        if useful_life_months <= 0:
            raise ValidationError("useful_life_months must be positive")
        _validate_date(placed_date, "placed_date")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "assets",
                {"book_id": book_id, "name": name, "cost_cents": cost_cents,
                 "salvage_cents": salvage_cents,
                 "useful_life_months": useful_life_months,
                 "placed_date": placed_date, "disposed": False},
                actor, "ext_asset_create",
            )

    @_fail_closed
    def dispose_fixed_asset(self, book_id, asset_id, actor):
        """Mark an asset disposed; approver is never its registrar."""
        self._require(actor, "approve")
        with self._lock:
            asset = self._get("assets", asset_id, "asset")
            self._check_book(asset, book_id)
            self._check_not_creator(asset, actor, "dispose")
            if asset["disposed"]:
                raise ValidationError("asset is already disposed")
            asset["disposed"] = True
            asset["disposed_by"] = actor_name(actor)
            self._audit(actor, "ext_asset_dispose", asset_id, {"book_id": book_id})
            return copy.deepcopy(asset)

    def asset_view(self, book_id, asset_id, months_elapsed, actor):
        """Derived at read: straight-line depreciation and book value.

        Monthly depreciation is the integer floor of the depreciable
        base over the useful life; accumulated depreciation is capped
        at the depreciable base, so book value never falls below
        salvage. Nothing derived is stored.
        """
        _validate_int_range(months_elapsed, "months_elapsed", 0, 12000)
        self._require(actor, "read")
        with self._lock:
            asset = self._get("assets", asset_id, "asset")
            self._check_book(asset, book_id)
            base = asset["cost_cents"] - asset["salvage_cents"]
            monthly = base // asset["useful_life_months"]
            accumulated = min(base, monthly * months_elapsed)
            view = copy.deepcopy(asset)
            view["monthly_depreciation_cents"] = monthly
            view["accumulated_depreciation_cents"] = accumulated
            view["book_value_cents"] = asset["cost_cents"] - accumulated
            return view

    # -- 6. Records retention beyond the audit seed ------------------

    @_fail_closed
    def create_retention_policy(self, book_id, record_type, retention_months,
                                actor):
        """Create a retention policy: a record type and a month count."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(record_type, "record_type")
        _require_int(retention_months, "retention_months")
        if retention_months <= 0:
            raise ValidationError("retention_months must be positive")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "retention_policies",
                {"book_id": book_id, "record_type": record_type,
                 "retention_months": retention_months},
                actor, "ext_retention_policy_create",
            )

    @_fail_closed
    def assign_retention(self, book_id, policy_id, record_ref, created_date,
                         actor):
        """Assign a policy to an opaque record reference."""
        _validate_ref(record_ref, "record_ref")
        _validate_date(created_date, "created_date")
        self._require(actor, "enter")
        with self._lock:
            policy = self._get("retention_policies", policy_id, "retention policy")
            self._check_book(policy, book_id)
            return self._create(
                "retention_assignments",
                {"book_id": book_id, "policy_id": policy_id,
                 "record_ref": record_ref, "created_date": created_date},
                actor, "ext_retention_assign",
            )

    @_fail_closed
    def record_disposition(self, book_id, assignment_id, actor):
        """Record a disposition decision for an assignment.

        This records the decision only: the assignment record itself
        is append-only history and is never deleted by this substrate
        (retention enforcement is the deployment layer's, per the
        platform-layer decision on AU-11).
        """
        self._require(actor, "approve")
        with self._lock:
            assignment = self._get(
                "retention_assignments", assignment_id, "retention assignment")
            self._check_book(assignment, book_id)
            self._check_not_creator(assignment, actor, "record a disposition for")
            existing = [r for r in self._data["dispositions"].values()
                        if r["assignment_id"] == assignment_id]
            if existing:
                raise ValidationError("a disposition is already recorded for this assignment")
            return self._create(
                "dispositions",
                {"book_id": book_id, "assignment_id": assignment_id},
                actor, "ext_disposition_record",
            )

    def retention_view(self, book_id, assignment_id, as_of_date, actor):
        """Derived at read: due date and whether disposition is due."""
        _validate_date(as_of_date, "as_of_date")
        self._require(actor, "read")
        with self._lock:
            assignment = self._get(
                "retention_assignments", assignment_id, "retention assignment")
            self._check_book(assignment, book_id)
            policy = self._get(
                "retention_policies", assignment["policy_id"], "retention policy")
            due = _add_months(assignment["created_date"],
                              policy["retention_months"])
            view = copy.deepcopy(assignment)
            view["disposition_due_date"] = due
            view["disposition_due"] = as_of_date >= due
            view["disposition_recorded"] = any(
                r["assignment_id"] == assignment_id
                for r in self._data["dispositions"].values())
            return view

    # -- 7. Forecasting / EPM ----------------------------------------

    @_fail_closed
    def create_forecast(self, book_id, period, lines, actor):
        """Create a forecast from labeled cent lines for a period."""
        _validate_non_empty(book_id, "book_id")
        _validate_period(period, "period")
        if not isinstance(lines, list) or not lines:
            raise ValidationError("forecast lines must be a non-empty list")
        clean = []
        seen = set()
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("forecast lines must be objects")
            label = _validate_non_empty(line.get("label"), "forecast line label")
            if label in seen:
                raise ValidationError("duplicate forecast line label: %r" % (label,))
            seen.add(label)
            amount = _validate_cents_any(line.get("amount_cents"),
                                          "forecast line amount_cents")
            clean.append({"label": label, "amount_cents": amount})
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "forecasts",
                {"book_id": book_id, "period": period, "lines": clean,
                 "status": "draft"},
                actor, "ext_forecast_create",
            )

    @_fail_closed
    def approve_forecast(self, book_id, forecast_id, actor):
        """Approve a draft forecast; approver is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            forecast = self._get("forecasts", forecast_id, "forecast")
            self._check_book(forecast, book_id)
            self._check_not_creator(forecast, actor, "approve")
            if forecast["status"] != "draft":
                raise ValidationError("only a draft forecast can be approved")
            forecast["status"] = "approved"
            forecast["approved_by"] = actor_name(actor)
            self._audit(actor, "ext_forecast_approve", forecast_id,
                        {"book_id": book_id})
            return copy.deepcopy(forecast)

    def forecast_variance(self, book_id, forecast_id, actual_lines, actor):
        """Derived at read: per-label and total variance vs actuals.

        Actuals are an input to the derivation only; they are never
        stored by this function.
        """
        if not isinstance(actual_lines, list):
            raise ValidationError("actual_lines must be a list")
        actuals = {}
        for line in actual_lines:
            if not isinstance(line, dict):
                raise ValidationError("actual lines must be objects")
            label = _validate_non_empty(line.get("label"), "actual line label")
            actuals[label] = _validate_cents_any(
                line.get("amount_cents"), "actual line amount_cents")
        self._require(actor, "read")
        with self._lock:
            forecast = self._get("forecasts", forecast_id, "forecast")
            self._check_book(forecast, book_id)
            rows = []
            total_forecast = 0
            total_actual = 0
            for line in forecast["lines"]:
                actual = actuals.get(line["label"], 0)
                rows.append({
                    "label": line["label"],
                    "forecast_cents": line["amount_cents"],
                    "actual_cents": actual,
                    "variance_cents": actual - line["amount_cents"],
                })
                total_forecast += line["amount_cents"]
                total_actual += actual
            return {
                "book_id": book_id,
                "forecast_id": forecast_id,
                "rows": rows,
                "total_forecast_cents": total_forecast,
                "total_actual_cents": total_actual,
                "total_variance_cents": total_actual - total_forecast,
            }

    # -- 8. Supply chain ----------------------------------------------

    @_fail_closed
    def register_supplier(self, book_id, supplier_ref, name, actor):
        """Register a supplier under an opaque reference."""
        _validate_non_empty(book_id, "book_id")
        _validate_ref(supplier_ref, "supplier_ref")
        _validate_non_empty(name, "supplier name")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "suppliers",
                {"book_id": book_id, "supplier_ref": supplier_ref,
                 "name": name},
                actor, "ext_supplier_create",
            )

    @_fail_closed
    def create_purchase_order(self, book_id, supplier_id, item_description,
                              quantity, unit_price_cents, actor):
        """Create a purchase order record. Totals are derived, not stored."""
        _validate_non_empty(item_description, "item_description")
        _require_int(quantity, "quantity")
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        _validate_cents_nonnegative(unit_price_cents, "unit_price_cents")
        self._require(actor, "enter")
        with self._lock:
            supplier = self._get("suppliers", supplier_id, "supplier")
            self._check_book(supplier, book_id)
            return self._create(
                "purchase_orders",
                {"book_id": book_id, "supplier_id": supplier_id,
                 "item_description": item_description, "quantity": quantity,
                 "unit_price_cents": unit_price_cents, "status": "draft"},
                actor, "ext_purchase_order_create",
            )

    @_fail_closed
    def approve_purchase_order(self, book_id, order_id, actor):
        """Approve a draft purchase order; approver is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            order = self._get("purchase_orders", order_id, "purchase order")
            self._check_book(order, book_id)
            self._check_not_creator(order, actor, "approve")
            if order["status"] != "draft":
                raise ValidationError("only a draft purchase order can be approved")
            order["status"] = "approved"
            order["approved_by"] = actor_name(actor)
            self._audit(actor, "ext_purchase_order_approve", order_id,
                        {"book_id": book_id})
            return copy.deepcopy(order)

    @_fail_closed
    def record_receipt(self, book_id, order_id, quantity, actor):
        """Record a receipt against an approved order, capped at quantity."""
        _require_int(quantity, "quantity")
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        self._require(actor, "enter")
        with self._lock:
            order = self._get("purchase_orders", order_id, "purchase order")
            self._check_book(order, book_id)
            if order["status"] != "approved":
                raise ValidationError("receipts require an approved purchase order")
            received = sum(r["quantity"] for r in self._data["receipts"].values()
                           if r["order_id"] == order_id)
            if received + quantity > order["quantity"]:
                raise ValidationError("receipt would exceed the ordered quantity")
            return self._create(
                "receipts",
                {"book_id": book_id, "order_id": order_id,
                 "quantity": quantity},
                actor, "ext_receipt_create",
            )

    def purchase_order_view(self, book_id, order_id, actor):
        """Derived at read: total, received, remaining, fulfillment."""
        self._require(actor, "read")
        with self._lock:
            order = self._get("purchase_orders", order_id, "purchase order")
            self._check_book(order, book_id)
            received = sum(r["quantity"] for r in self._data["receipts"].values()
                           if r["order_id"] == order_id)
            view = copy.deepcopy(order)
            view["total_cents"] = order["quantity"] * order["unit_price_cents"]
            view["received_quantity"] = received
            view["remaining_quantity"] = order["quantity"] - received
            if received == 0:
                view["fulfillment"] = "unreceived"
            elif received < order["quantity"]:
                view["fulfillment"] = "partially_received"
            else:
                view["fulfillment"] = "received"
            return view

    # -- 9. GovCon / grants specifics ---------------------------------

    @_fail_closed
    def create_award(self, book_id, award_ref, sponsor_ref, ceiling_cents,
                     actor):
        """Create a grant/contract award record with a ceiling in cents."""
        _validate_non_empty(book_id, "book_id")
        _validate_ref(award_ref, "award_ref")
        _validate_ref(sponsor_ref, "sponsor_ref")
        _validate_cents_positive(ceiling_cents, "ceiling_cents")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "awards",
                {"book_id": book_id, "award_ref": award_ref,
                 "sponsor_ref": sponsor_ref, "ceiling_cents": ceiling_cents,
                 "status": "draft"},
                actor, "ext_award_create",
            )

    @_fail_closed
    def activate_award(self, book_id, award_id, actor):
        """Activate a draft award; activator is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            award = self._get("awards", award_id, "award")
            self._check_book(award, book_id)
            self._check_not_creator(award, actor, "activate")
            if award["status"] != "draft":
                raise ValidationError("only a draft award can be activated")
            award["status"] = "active"
            award["activated_by"] = actor_name(actor)
            self._audit(actor, "ext_award_activate", award_id, {"book_id": book_id})
            return copy.deepcopy(award)

    @_fail_closed
    def record_award_cost(self, book_id, award_id, amount_cents, cost_type,
                          actor):
        """Record a cost against an active award, capped at its ceiling."""
        _validate_cents_positive(amount_cents, "amount_cents")
        _validate_choice(cost_type, COST_TYPES, "cost_type")
        self._require(actor, "enter")
        with self._lock:
            award = self._get("awards", award_id, "award")
            self._check_book(award, book_id)
            if award["status"] != "active":
                raise ValidationError("costs can only be recorded on an active award")
            total = sum(r["amount_cents"]
                        for r in self._data["award_costs"].values()
                        if r["award_id"] == award_id)
            if total + amount_cents > award["ceiling_cents"]:
                raise ValidationError("award costs would exceed the award ceiling")
            return self._create(
                "award_costs",
                {"book_id": book_id, "award_id": award_id,
                 "amount_cents": amount_cents, "cost_type": cost_type},
                actor, "ext_award_cost_create",
            )

    def award_view(self, book_id, award_id, actor):
        """Derived at read: direct/indirect totals, remaining ceiling."""
        self._require(actor, "read")
        with self._lock:
            award = self._get("awards", award_id, "award")
            self._check_book(award, book_id)
            costs = [r for r in self._data["award_costs"].values()
                     if r["award_id"] == award_id]
            direct = sum(r["amount_cents"] for r in costs
                         if r["cost_type"] == "direct")
            indirect = sum(r["amount_cents"] for r in costs
                           if r["cost_type"] == "indirect")
            view = copy.deepcopy(award)
            view["direct_cents"] = direct
            view["indirect_cents"] = indirect
            view["total_cost_cents"] = direct + indirect
            view["remaining_cents"] = award["ceiling_cents"] - (direct + indirect)
            return view

    # -- 10. Crypto investigation (records only) -----------------------

    @_fail_closed
    def create_crypto_case(self, book_id, case_ref, title, actor):
        """Open a crypto-investigation case record.

        Records only: this substrate performs no chain tracing, no
        address clustering, and no external lookup of any kind.
        Wallet identifiers enter only as opaque caller references.
        """
        _validate_non_empty(book_id, "book_id")
        _validate_ref(case_ref, "case_ref")
        _validate_non_empty(title, "case title")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "crypto_cases",
                {"book_id": book_id, "case_ref": case_ref, "title": title,
                 "status": "open"},
                actor, "ext_crypto_case_create",
            )

    @_fail_closed
    def add_wallet_observation(self, book_id, case_id, wallet_ref,
                               observed_value_cents, actor):
        """Record an observation about an opaque wallet reference."""
        _validate_ref(wallet_ref, "wallet_ref")
        _validate_cents_nonnegative(observed_value_cents, "observed_value_cents")
        self._require(actor, "enter")
        with self._lock:
            case = self._get("crypto_cases", case_id, "crypto case")
            self._check_book(case, book_id)
            if case["status"] != "open":
                raise ValidationError("observations require an open case")
            return self._create(
                "wallet_observations",
                {"book_id": book_id, "case_id": case_id,
                 "wallet_ref": wallet_ref,
                 "observed_value_cents": observed_value_cents},
                actor, "ext_wallet_observation_create",
            )

    @_fail_closed
    def close_crypto_case(self, book_id, case_id, actor):
        """Close a case; the closer is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            case = self._get("crypto_cases", case_id, "crypto case")
            self._check_book(case, book_id)
            self._check_not_creator(case, actor, "close")
            if case["status"] != "open":
                raise ValidationError("only an open case can be closed")
            case["status"] = "closed"
            case["closed_by"] = actor_name(actor)
            self._audit(actor, "ext_crypto_case_close", case_id,
                        {"book_id": book_id})
            return copy.deepcopy(case)

    def crypto_case_view(self, book_id, case_id, actor):
        """Derived at read: observation count, distinct wallets, total."""
        self._require(actor, "read")
        with self._lock:
            case = self._get("crypto_cases", case_id, "crypto case")
            self._check_book(case, book_id)
            observations = [r for r in self._data["wallet_observations"].values()
                            if r["case_id"] == case_id]
            view = copy.deepcopy(case)
            view["observation_count"] = len(observations)
            view["distinct_wallet_count"] = len(
                {r["wallet_ref"] for r in observations})
            view["total_observed_cents"] = sum(
                r["observed_value_cents"] for r in observations)
            return view

    # -- 11. Time tracking ---------------------------------------------

    @_fail_closed
    def record_time_entry(self, book_id, worker_ref, project_ref, entry_date,
                          minutes, actor):
        """Record a time entry in whole minutes for an opaque worker ref."""
        _validate_non_empty(book_id, "book_id")
        _validate_ref(worker_ref, "worker_ref")
        _validate_ref(project_ref, "project_ref")
        _validate_date(entry_date, "entry_date")
        _validate_int_range(minutes, "minutes", 1, 1440)
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "time_entries",
                {"book_id": book_id, "worker_ref": worker_ref,
                 "project_ref": project_ref, "entry_date": entry_date,
                 "minutes": minutes, "status": "recorded"},
                actor, "ext_time_entry_create",
            )

    @_fail_closed
    def approve_time_entry(self, book_id, entry_id, actor):
        """Approve a time entry; approver is never its creator (SoD)."""
        self._require(actor, "approve")
        with self._lock:
            entry = self._get("time_entries", entry_id, "time entry")
            self._check_book(entry, book_id)
            self._check_not_creator(entry, actor, "approve")
            if entry["status"] != "recorded":
                raise ValidationError("only a recorded time entry can be approved")
            entry["status"] = "approved"
            entry["approved_by"] = actor_name(actor)
            self._audit(actor, "ext_time_entry_approve", entry_id,
                        {"book_id": book_id})
            return copy.deepcopy(entry)

    def time_summary(self, book_id, worker_ref, actor):
        """Derived at read: total and approved minutes for a worker ref."""
        _validate_ref(worker_ref, "worker_ref")
        self._require(actor, "read")
        with self._lock:
            entries = [r for r in self._data["time_entries"].values()
                       if r["book_id"] == book_id
                       and r["worker_ref"] == worker_ref]
            return {
                "book_id": book_id,
                "worker_ref": worker_ref,
                "entry_count": len(entries),
                "total_minutes": sum(r["minutes"] for r in entries),
                "approved_minutes": sum(
                    r["minutes"] for r in entries if r["status"] == "approved"),
            }

    # -- 12. Payroll ----------------------------------------------------

    @_fail_closed
    def create_payroll_run(self, book_id, period, actor):
        """Create a payroll run for a period. A run is a record set,
        not a payment rail: no money moves through this substrate."""
        _validate_non_empty(book_id, "book_id")
        _validate_period(period, "period")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "payroll_runs",
                {"book_id": book_id, "period": period, "status": "draft"},
                actor, "ext_payroll_run_create",
            )

    @_fail_closed
    def add_pay_item(self, book_id, run_id, worker_ref, gross_cents,
                     deductions_cents, actor):
        """Add a pay item to a draft run. Net is derived, never stored."""
        _validate_ref(worker_ref, "worker_ref")
        _validate_cents_nonnegative(gross_cents, "gross_cents")
        _validate_cents_nonnegative(deductions_cents, "deductions_cents")
        if deductions_cents > gross_cents:
            raise ValidationError("deductions_cents may not exceed gross_cents")
        self._require(actor, "enter")
        with self._lock:
            run = self._get("payroll_runs", run_id, "payroll run")
            self._check_book(run, book_id)
            if run["status"] != "draft":
                raise ValidationError("pay items can only be added to a draft run")
            return self._create(
                "pay_items",
                {"book_id": book_id, "run_id": run_id,
                 "worker_ref": worker_ref, "gross_cents": gross_cents,
                 "deductions_cents": deductions_cents},
                actor, "ext_pay_item_create",
            )

    @_fail_closed
    def approve_payroll_run(self, book_id, run_id, actor):
        """Approve a draft run with at least one item; SoD applies."""
        self._require(actor, "approve")
        with self._lock:
            run = self._get("payroll_runs", run_id, "payroll run")
            self._check_book(run, book_id)
            self._check_not_creator(run, actor, "approve")
            if run["status"] != "draft":
                raise ValidationError("only a draft payroll run can be approved")
            if not any(r["run_id"] == run_id
                       for r in self._data["pay_items"].values()):
                raise ValidationError("a payroll run with no pay items cannot be approved")
            run["status"] = "approved"
            run["approved_by"] = actor_name(actor)
            self._audit(actor, "ext_payroll_run_approve", run_id,
                        {"book_id": book_id})
            return copy.deepcopy(run)

    @_fail_closed
    def record_payroll_disbursement(self, book_id, run_id, actor):
        """Record (not execute) disbursement of an approved run."""
        self._require(actor, "pay")
        with self._lock:
            run = self._get("payroll_runs", run_id, "payroll run")
            self._check_book(run, book_id)
            if run["status"] != "approved":
                raise ValidationError("only an approved payroll run can be disbursed")
            run["status"] = "disbursed_recorded"
            run["disbursed_by"] = actor_name(actor)
            self._audit(actor, "ext_payroll_disburse_record", run_id,
                        {"book_id": book_id})
            return copy.deepcopy(run)

    def payroll_view(self, book_id, run_id, actor):
        """Derived at read: gross, deductions, and net totals."""
        self._require(actor, "read")
        with self._lock:
            run = self._get("payroll_runs", run_id, "payroll run")
            self._check_book(run, book_id)
            items = [r for r in self._data["pay_items"].values()
                     if r["run_id"] == run_id]
            gross = sum(r["gross_cents"] for r in items)
            deductions = sum(r["deductions_cents"] for r in items)
            view = copy.deepcopy(run)
            view["item_count"] = len(items)
            view["total_gross_cents"] = gross
            view["total_deductions_cents"] = deductions
            view["total_net_cents"] = gross - deductions
            return view

    # -- 13. Tax support -------------------------------------------------

    @_fail_closed
    def create_tax_filing(self, book_id, jurisdiction, period, actor):
        """Create a tax-preparation record. Preparation only: this
        substrate never transmits anything to a tax authority."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(jurisdiction, "jurisdiction")
        _validate_period(period, "period")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "tax_filings",
                {"book_id": book_id, "jurisdiction": jurisdiction,
                 "period": period, "status": "draft"},
                actor, "ext_tax_filing_create",
            )

    @_fail_closed
    def add_tax_line(self, book_id, filing_id, label, amount_cents, actor):
        """Add a labeled line to a draft filing record."""
        _validate_non_empty(label, "tax line label")
        _validate_cents_any(amount_cents, "amount_cents")
        self._require(actor, "enter")
        with self._lock:
            filing = self._get("tax_filings", filing_id, "tax filing")
            self._check_book(filing, book_id)
            if filing["status"] != "draft":
                raise ValidationError("tax lines can only be added to a draft filing")
            return self._create(
                "tax_lines",
                {"book_id": book_id, "filing_id": filing_id,
                 "label": label, "amount_cents": amount_cents},
                actor, "ext_tax_line_create",
            )

    @_fail_closed
    def finalize_tax_filing(self, book_id, filing_id, actor):
        """Finalize a filing record; finalizer is never its creator.

        Finalizing marks the preparation record complete in this
        substrate. It is not a submission to any authority.
        """
        self._require(actor, "approve")
        with self._lock:
            filing = self._get("tax_filings", filing_id, "tax filing")
            self._check_book(filing, book_id)
            self._check_not_creator(filing, actor, "finalize")
            if filing["status"] != "draft":
                raise ValidationError("only a draft filing can be finalized")
            filing["status"] = "finalized"
            filing["finalized_by"] = actor_name(actor)
            self._audit(actor, "ext_tax_filing_finalize", filing_id,
                        {"book_id": book_id})
            return copy.deepcopy(filing)

    def tax_filing_view(self, book_id, filing_id, actor):
        """Derived at read: line count and total."""
        self._require(actor, "read")
        with self._lock:
            filing = self._get("tax_filings", filing_id, "tax filing")
            self._check_book(filing, book_id)
            lines = [r for r in self._data["tax_lines"].values()
                     if r["filing_id"] == filing_id]
            view = copy.deepcopy(filing)
            view["line_count"] = len(lines)
            view["total_cents"] = sum(r["amount_cents"] for r in lines)
            return view

    # -- 14. Forensic investigation --------------------------------------

    @_fail_closed
    def create_forensic_case(self, book_id, title, matter_ref, actor):
        """Open a forensic case under an opaque matter reference."""
        _validate_non_empty(book_id, "book_id")
        _validate_non_empty(title, "case title")
        _validate_ref(matter_ref, "matter_ref")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "forensic_cases",
                {"book_id": book_id, "title": title,
                 "matter_ref": matter_ref, "status": "open"},
                actor, "ext_forensic_case_create",
            )

    @_fail_closed
    def add_evidence_item(self, book_id, case_id, evidence_ref, description,
                          custodian_ref, actor):
        """Register an evidence item with its initial custodian.

        The custody chain is an append-only list of custodian events
        stored on the item; the current custodian is derived from its
        last event at read time, never stored as a separate field.
        """
        _validate_ref(evidence_ref, "evidence_ref")
        _validate_non_empty(description, "evidence description")
        _validate_ref(custodian_ref, "custodian_ref")
        self._require(actor, "enter")
        with self._lock:
            case = self._get("forensic_cases", case_id, "forensic case")
            self._check_book(case, book_id)
            if case["status"] != "open":
                raise ValidationError("evidence requires an open case")
            return self._create(
                "evidence_items",
                {"book_id": book_id, "case_id": case_id,
                 "evidence_ref": evidence_ref, "description": description,
                 "custody_events": [
                     {"custodian_ref": custodian_ref,
                      "recorded_by": actor_name(actor)}]},
                actor, "ext_evidence_create",
            )

    @_fail_closed
    def transfer_custody(self, book_id, evidence_id, new_custodian_ref, actor):
        """Append a custody transfer event to an evidence item."""
        _validate_ref(new_custodian_ref, "new_custodian_ref")
        self._require(actor, "enter")
        with self._lock:
            item = self._get("evidence_items", evidence_id, "evidence item")
            self._check_book(item, book_id)
            case = self._get("forensic_cases", item["case_id"], "forensic case")
            if case["status"] != "open":
                raise ValidationError("custody transfers require an open case")
            item["custody_events"].append(
                {"custodian_ref": new_custodian_ref,
                 "recorded_by": actor_name(actor)})
            self._audit(actor, "ext_custody_transfer", evidence_id,
                        {"book_id": book_id})
            return copy.deepcopy(item)

    @_fail_closed
    def close_forensic_case(self, book_id, case_id, actor):
        """Close a forensic case; closer is never its creator."""
        self._require(actor, "approve")
        with self._lock:
            case = self._get("forensic_cases", case_id, "forensic case")
            self._check_book(case, book_id)
            self._check_not_creator(case, actor, "close")
            if case["status"] != "open":
                raise ValidationError("only an open case can be closed")
            case["status"] = "closed"
            case["closed_by"] = actor_name(actor)
            self._audit(actor, "ext_forensic_case_close", case_id,
                        {"book_id": book_id})
            return copy.deepcopy(case)

    def evidence_view(self, book_id, evidence_id, actor):
        """Derived at read: current custodian and chain length."""
        self._require(actor, "read")
        with self._lock:
            item = self._get("evidence_items", evidence_id, "evidence item")
            self._check_book(item, book_id)
            view = copy.deepcopy(item)
            view["custody_length"] = len(item["custody_events"])
            view["current_custodian_ref"] = (
                item["custody_events"][-1]["custodian_ref"]
                if item["custody_events"] else None)
            return view

    # -- 15. E-signature (STUB-ENGINE: labeled reference implementation)

    @_fail_closed
    def create_signature_request(self, book_id, document_ref, signer_ref,
                                 actor):
        """Record a signature request as a reference stub.

        REFERENCE IMPLEMENTATION ONLY: nothing is sent to any signing
        service, no envelope exists outside this record, and the
        record's status is ``recorded`` -- a statement about this
        substrate, not about any document's legal state. Every record
        carries ``reference_stub: True``.
        """
        _validate_non_empty(book_id, "book_id")
        _validate_ref(document_ref, "document_ref")
        _validate_ref(signer_ref, "signer_ref")
        self._require(actor, "enter")
        with self._lock:
            return self._create(
                "signature_requests",
                {"book_id": book_id, "document_ref": document_ref,
                 "signer_ref": signer_ref, "status": "recorded",
                 "reference_stub": True},
                actor, "ext_signature_request_record",
            )

    @_fail_closed
    def record_signature_event(self, book_id, request_id, event_type, actor):
        """Record a signature-lifecycle event on a stub request.

        Events are caller-asserted records (for example that a signer
        declared signing outside this system); the stub verifies
        nothing and executes nothing. Every event also carries
        ``reference_stub: True``.
        """
        _validate_choice(event_type, SIGNATURE_EVENT_TYPES, "event_type")
        self._require(actor, "enter")
        with self._lock:
            request = self._get(
                "signature_requests", request_id, "signature request")
            self._check_book(request, book_id)
            return self._create(
                "signature_events",
                {"book_id": book_id, "request_id": request_id,
                 "event_type": event_type, "reference_stub": True},
                actor, "ext_signature_event_record",
            )

    def signature_request_view(self, book_id, request_id, actor):
        """Derived at read: the stub record plus its recorded events."""
        self._require(actor, "read")
        with self._lock:
            request = self._get(
                "signature_requests", request_id, "signature request")
            self._check_book(request, book_id)
            events = [copy.deepcopy(r)
                      for r in self._data["signature_events"].values()
                      if r["request_id"] == request_id]
            view = copy.deepcopy(request)
            view["events"] = events
            view["event_count"] = len(events)
            return view
