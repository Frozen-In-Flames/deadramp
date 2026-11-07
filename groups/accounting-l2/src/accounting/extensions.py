"""Final GAPS batch extensions for the Accounting L2 merged build.

Clean-room, standard-library-only records/derivation extensions for the
14 Extended families the union spec ranked but the core did not
implement, plus one labeled reference implementation (e-signature).
See ``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`AccountingStore`; the core
  modules are untouched. Book membership is enforced by delegating to
  the core store's public ``get_book`` (membership or platform admin),
  and role permissions are enforced with :mod:`accounting.access`
  exactly as the core enforces them for User-like actors.
- All money is integer cents: any amount that is not a Python ``int``
  (booleans and floats included) raises ``ValidationError``; nothing
  is partially applied and a failed operation consumes no id.
- People, vendors, workers, wallets and customers are opaque
  ``*_ref`` strings only. No record shape in this module can hold a
  name, email, phone number, or government identifier.
- Derived values are derived at read time and never stored:
  analytics ratios, fixed-asset book value, forecast projections,
  risk exposure, project spend, grant amounts drawn, payroll net,
  tax due, retention eligibility, supply-order fulfilment status,
  time totals. Stored records carry no derived key; tests pin that.
- Every successful mutation is recorded on the core store's audit
  log (when one is attached), with action names prefixed ``ext_``.
- Nothing here executes against an external system. The e-signature
  surface is a labeled reference implementation: every record it
  creates carries ``reference_stub: True`` and no signing ever
  happens.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_HASH_RE = re.compile(r"^[0-9a-fA-F]{8,128}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _positive(value, what):
    _int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _nonnegative(value, what):
    _int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _bps(value, what="rate_bps"):
    _int(value, what)
    if value < 0 or value > 10000:
        raise ValidationError("%s must be between 0 and 10000" % (what,))
    return value


def _score_1_5(value, what):
    _int(value, what)
    if value < 1 or value > 5:
        raise ValidationError("%s must be between 1 and 5" % (what,))
    return value


def _date(value, what="date"):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("%s is not a valid calendar date: %r" % (what, value)) from exc
    return value


def _period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError("%s must be a fiscal period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError("%s is not a valid fiscal period: %r" % (what, value)) from exc
    return value


def _months_between(start_period, end_period):
    """Whole months from start_period to end_period (negative if before)."""
    sy, sm = int(start_period[:4]), int(start_period[5:7])
    ey, em = int(end_period[:4]), int(end_period[5:7])
    return (ey - sy) * 12 + (em - sm)


def _check_draw_within_ceiling(drawn_cents, amount_cents, ceiling_cents):
    """Signature guard: a grant draw may never exceed the award ceiling."""
    if drawn_cents + amount_cents > ceiling_cents:
        raise ValidationError(
            "draw of %d cents would exceed the award ceiling "
            "(already drawn %d of %d cents)" % (amount_cents, drawn_cents, ceiling_cents)
        )


class AccountingExtensions:
    """GAPS-batch extension surface, scoped to books in a core store."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _access(self, book_id, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        # Membership (or platform admin) + read, via the core store.
        self.store.get_book(book_id, actor)
        if hasattr(actor, "role"):
            require(actor, action)

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _create(self, kind, prefix, book_id, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id, "book_id": book_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"book_id": book_id, "kind": kind})
            return dict(record)

    def _get(self, kind, book_id, record_id, actor, action="read"):
        self._access(book_id, actor, action)
        record = self._records.get((kind, record_id))
        if record is None or record["book_id"] != book_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _list(self, kind, book_id, actor):
        self._access(book_id, actor, "read")
        return [dict(self._records[key]) for key in self._order
                if key[0] == kind and self._records[key]["book_id"] == book_id]

    # -- AI / analytics & BI (deterministic rules, no learned model) --

    def analytics_summary(self, book_id, period, actor):
        """Derived analytics over the core's exact statements.

        Ratios are integer basis points computed at read; nothing is
        stored. The method is deterministic rules over posted figures
        and is labeled as such in the result — no learned model, no
        inference is claimed.
        """
        _period(period)
        self._access(book_id, actor, "read")
        income = self.store.income_statement(book_id, period, actor)
        trial = self.store.trial_balance(book_id, actor, period=period)
        revenue = income["total_revenue_cents"]
        expenses = income["total_expense_cents"]
        net = income["net_income_cents"]
        return {
            "book_id": book_id,
            "period": period,
            "method": "deterministic_rules",
            "total_revenue_cents": revenue,
            "total_expense_cents": expenses,
            "net_income_cents": net,
            "net_margin_bps": (net * 10000 // revenue) if revenue > 0 else 0,
            "expense_ratio_bps": (expenses * 10000 // revenue) if revenue > 0 else 0,
            "accounts_with_movement": len(trial["accounts"]),
            "trial_balanced": trial["balanced"],
        }

    def detect_anomalies(self, book_id, period, prior_period, threshold_bps, actor):
        """Flag accounts whose movement changed by >= threshold_bps.

        Movement per account is debits+credits from the trial balance
        of each period; the change is derived at read, never stored.
        """
        _period(period)
        _period(prior_period)
        _bps(threshold_bps, "threshold_bps")
        self._access(book_id, actor, "read")

        def movement(p):
            rows = self.store.trial_balance(book_id, actor, period=p)["accounts"]
            return {r["account_id"]: r["debit_cents"] + r["credit_cents"] for r in rows}

        current, prior = movement(period), movement(prior_period)
        flags = []
        for account_id in sorted(set(current) | set(prior)):
            cur, pri = current.get(account_id, 0), prior.get(account_id, 0)
            if pri <= 0:
                continue
            change_bps = abs(cur - pri) * 10000 // pri
            if change_bps >= threshold_bps:
                flags.append({"account_id": account_id, "period": period,
                              "prior_movement_cents": pri,
                              "movement_cents": cur, "change_bps": change_bps})
        return {"book_id": book_id, "period": period, "prior_period": prior_period,
                "threshold_bps": threshold_bps, "flags": flags}

    # -- Project / program / portfolio management ----------------------

    def create_project(self, book_id, code, name, budget_cents, actor):
        _non_empty(code, "project code")
        _non_empty(name, "project name")
        _nonnegative(budget_cents, "budget_cents")
        self._access(book_id, actor, "enter")
        for key in self._order:
            rec = self._records[key]
            if key[0] == "project" and rec["book_id"] == book_id and rec["code"] == code:
                raise ValidationError("project code %r already exists in this book" % (code,))
        return self._create("project", "proj", book_id,
                            {"code": code, "name": name, "budget_cents": budget_cents},
                            actor, "ext_project_create")

    def record_project_cost(self, book_id, project_id, date, description, amount_cents, actor):
        _date(date)
        _non_empty(description, "description")
        _positive(amount_cents, "amount_cents")
        self._get("project", book_id, project_id, actor, "enter")
        return self._create("project_cost", "pcost", book_id,
                            {"project_id": project_id, "date": date,
                             "period": date[:7], "description": description,
                             "amount_cents": amount_cents},
                            actor, "ext_project_cost_create")

    def project_status(self, book_id, project_id, actor):
        """Spend and remaining budget, derived at read from cost records."""
        project = self._get("project", book_id, project_id, actor)
        spent = sum(r["amount_cents"] for r in self._list("project_cost", book_id, actor)
                    if r["project_id"] == project_id)
        budget = project["budget_cents"]
        return {"project_id": project_id, "book_id": book_id,
                "budget_cents": budget, "spent_cents": spent,
                "remaining_cents": budget - spent,
                "over_budget": spent > budget}

    def list_projects(self, book_id, actor):
        return self._list("project", book_id, actor)

    # -- Risk register / GRC -------------------------------------------

    def create_risk(self, book_id, title, category, likelihood, impact, owner_ref, actor):
        _non_empty(title, "risk title")
        _non_empty(category, "risk category")
        _score_1_5(likelihood, "likelihood")
        _score_1_5(impact, "impact")
        _non_empty(owner_ref, "owner_ref")
        self._access(book_id, actor, "enter")
        return self._create("risk", "risk", book_id,
                            {"title": title, "category": category,
                             "likelihood": likelihood, "impact": impact,
                             "owner_ref": owner_ref, "status": "open"},
                            actor, "ext_risk_create")

    def risk_exposure(self, book_id, risk_id, actor):
        """Exposure = likelihood x impact, derived at read, never stored."""
        risk = self._get("risk", book_id, risk_id, actor)
        exposure = risk["likelihood"] * risk["impact"]
        band = "high" if exposure >= 15 else "medium" if exposure >= 6 else "low"
        return {"risk_id": risk_id, "book_id": book_id, "exposure": exposure, "band": band}

    def mitigate_risk(self, book_id, risk_id, note, actor):
        _non_empty(note, "mitigation note")
        with self._lock:
            risk = self._get("risk", book_id, risk_id, actor, "enter")
            if risk["status"] != "open":
                raise ValidationError("only an open risk can be mitigated")
            risk["status"] = "mitigated"
            risk["mitigation_note"] = note
            self._audit(actor, "ext_risk_mitigate", risk_id, details={"book_id": book_id})
            return dict(risk)

    def list_risks(self, book_id, actor):
        return self._list("risk", book_id, actor)

    # -- Audit management workbenches ----------------------------------

    def create_audit_plan(self, book_id, title, period, actor):
        _non_empty(title, "audit plan title")
        _period(period)
        self._access(book_id, actor, "enter")
        return self._create("audit_plan", "aplan", book_id,
                            {"title": title, "period": period}, actor, "ext_audit_plan_create")

    def add_workpaper(self, book_id, plan_id, title, document_ref, actor):
        _non_empty(title, "workpaper title")
        _non_empty(document_ref, "document_ref")
        self._get("audit_plan", book_id, plan_id, actor, "enter")
        return self._create("workpaper", "wp", book_id,
                            {"plan_id": plan_id, "title": title, "document_ref": document_ref},
                            actor, "ext_workpaper_create")

    def create_finding(self, book_id, plan_id, title, severity, actor):
        _non_empty(title, "finding title")
        if severity not in ("low", "medium", "high", "critical"):
            raise ValidationError("severity must be low, medium, high, or critical")
        self._get("audit_plan", book_id, plan_id, actor, "enter")
        return self._create("finding", "find", book_id,
                            {"plan_id": plan_id, "title": title, "severity": severity,
                             "status": "open"},
                            actor, "ext_finding_create")

    def close_finding(self, book_id, finding_id, resolution, actor):
        """Close a finding; the closer may not be its creator (SoD, AC-5)."""
        _non_empty(resolution, "resolution")
        with self._lock:
            finding = self._get("finding", book_id, finding_id, actor, "approve")
            if actor_name(actor) == finding["created_by"]:
                raise PermissionDenied("separation of duties: the finding's creator may not close it")
            if finding["status"] != "open":
                raise ValidationError("only an open finding can be closed")
            finding["status"] = "closed"
            finding["resolution"] = resolution
            finding["closed_by"] = actor_name(actor)
            self._audit(actor, "ext_finding_close", finding_id, details={"book_id": book_id})
            return dict(finding)

    def list_findings(self, book_id, actor, plan_id=None):
        rows = self._list("finding", book_id, actor)
        return [r for r in rows if plan_id is None or r["plan_id"] == plan_id]

    # -- Fixed-asset registers ------------------------------------------

    def register_fixed_asset(self, book_id, tag, description, cost_cents,
                             salvage_cents, life_months, placed_period, actor):
        _non_empty(tag, "asset tag")
        _non_empty(description, "description")
        _positive(cost_cents, "cost_cents")
        _nonnegative(salvage_cents, "salvage_cents")
        if salvage_cents >= cost_cents:
            raise ValidationError("salvage_cents must be less than cost_cents")
        _positive(life_months, "life_months")
        _period(placed_period, "placed_period")
        self._access(book_id, actor, "enter")
        return self._create("fixed_asset", "asset", book_id,
                            {"tag": tag, "description": description,
                             "cost_cents": cost_cents, "salvage_cents": salvage_cents,
                             "life_months": life_months, "placed_period": placed_period},
                            actor, "ext_fixed_asset_create")

    def asset_book_value(self, book_id, asset_id, through_period, actor):
        """Straight-line book value derived at read; never stored."""
        _period(through_period, "through_period")
        asset = self._get("fixed_asset", book_id, asset_id, actor)
        months = min(max(_months_between(asset["placed_period"], through_period), 0),
                     asset["life_months"])
        monthly = (asset["cost_cents"] - asset["salvage_cents"]) // asset["life_months"]
        accumulated = min(monthly * months,
                          asset["cost_cents"] - asset["salvage_cents"])
        return {"asset_id": asset_id, "book_id": book_id, "through_period": through_period,
                "months_depreciated": months, "accumulated_cents": accumulated,
                "book_value_cents": asset["cost_cents"] - accumulated}

    def list_fixed_assets(self, book_id, actor):
        return self._list("fixed_asset", book_id, actor)

    # -- Records retention ----------------------------------------------

    def create_retention_record(self, book_id, record_ref, category,
                                record_period, retain_months, actor):
        _non_empty(record_ref, "record_ref")
        _non_empty(category, "category")
        _period(record_period, "record_period")
        _positive(retain_months, "retain_months")
        self._access(book_id, actor, "enter")
        return self._create("retention", "ret", book_id,
                            {"record_ref": record_ref, "category": category,
                             "record_period": record_period, "retain_months": retain_months},
                            actor, "ext_retention_create")

    def retention_disposition(self, book_id, retention_id, as_of_period, actor):
        """Eligibility derived at read: age in months vs the policy term.

        This records eligibility only; disposition itself is the
        embedding organization's records schedule (PLATFORM-LAYER.md).
        """
        _period(as_of_period, "as_of_period")
        rec = self._get("retention", book_id, retention_id, actor)
        age = _months_between(rec["record_period"], as_of_period)
        return {"retention_id": retention_id, "book_id": book_id,
                "age_months": max(age, 0), "retain_months": rec["retain_months"],
                "eligible_for_disposition": age >= rec["retain_months"]}

    # -- Forecasting / EPM ----------------------------------------------

    def create_forecast(self, book_id, name, base_period, growth_bps, actor):
        _non_empty(name, "forecast name")
        _period(base_period, "base_period")
        _bps(growth_bps, "growth_bps")
        self._access(book_id, actor, "enter")
        return self._create("forecast", "fcst", book_id,
                            {"name": name, "base_period": base_period,
                             "growth_bps": growth_bps},
                            actor, "ext_forecast_create")

    def derive_forecast(self, book_id, forecast_id, periods_ahead, actor):
        """Project the base period's net forward; derived, never stored."""
        _positive(periods_ahead, "periods_ahead")
        fcst = self._get("forecast", book_id, forecast_id, actor)
        income = self.store.income_statement(book_id, fcst["base_period"], actor)
        value = income["net_income_cents"]
        projection = []
        year, month = int(fcst["base_period"][:4]), int(fcst["base_period"][5:7])
        for _ in range(periods_ahead):
            value = value * (10000 + fcst["growth_bps"]) // 10000
            month += 1
            if month > 12:
                month, year = 1, year + 1
            projection.append({"period": "%04d-%02d" % (year, month),
                               "projected_net_cents": value})
        return {"forecast_id": forecast_id, "book_id": book_id,
                "base_period": fcst["base_period"],
                "base_net_cents": income["net_income_cents"],
                "projection": projection}

    # -- Supply chain -----------------------------------------------------

    def create_purchase_order(self, book_id, vendor_ref, date, lines, actor):
        _non_empty(vendor_ref, "vendor_ref")
        _date(date)
        if not isinstance(lines, list) or not lines:
            raise ValidationError("lines must be a non-empty list")
        norm = []
        total = 0
        for line in lines:
            if not isinstance(line, dict):
                raise ValidationError("each line must be a dict")
            desc = _non_empty(line.get("description"), "line description")
            qty = _positive(line.get("quantity"), "line quantity")
            price = _nonnegative(line.get("unit_price_cents"), "line unit_price_cents")
            amount = qty * price
            total += amount
            norm.append({"description": desc, "quantity": qty,
                         "unit_price_cents": price, "amount_cents": amount})
        self._access(book_id, actor, "enter")
        return self._create("purchase_order", "po", book_id,
                            {"vendor_ref": vendor_ref, "date": date, "lines": norm,
                             "total_cents": total},
                            actor, "ext_purchase_order_create")

    def record_receipt(self, book_id, po_id, line_index, quantity, date, actor):
        _positive(quantity, "quantity")
        _date(date)
        po = self._get("purchase_order", book_id, po_id, actor, "enter")
        _int(line_index, "line_index")
        if line_index < 0 or line_index >= len(po["lines"]):
            raise ValidationError("line_index out of range")
        received = self._received_qty(book_id, po_id, line_index, actor)
        if received + quantity > po["lines"][line_index]["quantity"]:
            raise ValidationError("receipt would exceed the ordered quantity")
        return self._create("receipt", "rcpt", book_id,
                            {"po_id": po_id, "line_index": line_index,
                             "quantity": quantity, "date": date},
                            actor, "ext_receipt_create")

    def _received_qty(self, book_id, po_id, line_index, actor):
        return sum(r["quantity"] for r in self._list("receipt", book_id, actor)
                   if r["po_id"] == po_id and r["line_index"] == line_index)

    def purchase_order_status(self, book_id, po_id, actor):
        """Fulfilment status derived at read from receipt records."""
        po = self._get("purchase_order", book_id, po_id, actor)
        lines = []
        for idx, line in enumerate(po["lines"]):
            received = self._received_qty(book_id, po_id, idx, actor)
            lines.append({"line_index": idx, "ordered": line["quantity"],
                          "received": received})
        if all(l["received"] == 0 for l in lines):
            status = "ordered"
        elif all(l["received"] == l["ordered"] for l in lines):
            status = "fulfilled"
        else:
            status = "partially_received"
        return {"po_id": po_id, "book_id": book_id, "status": status, "lines": lines}

    # -- GovCon / grants ---------------------------------------------------

    def create_grant_award(self, book_id, award_ref, sponsor_ref, ceiling_cents,
                           indirect_rate_bps, period, actor):
        _non_empty(award_ref, "award_ref")
        _non_empty(sponsor_ref, "sponsor_ref")
        _positive(ceiling_cents, "ceiling_cents")
        _bps(indirect_rate_bps, "indirect_rate_bps")
        _period(period)
        self._access(book_id, actor, "enter")
        return self._create("grant_award", "grant", book_id,
                            {"award_ref": award_ref, "sponsor_ref": sponsor_ref,
                             "ceiling_cents": ceiling_cents,
                             "indirect_rate_bps": indirect_rate_bps, "period": period},
                            actor, "ext_grant_award_create")

    def record_grant_draw(self, book_id, award_id, date, direct_cents, actor):
        _date(date)
        _positive(direct_cents, "direct_cents")
        award = self._get("grant_award", book_id, award_id, actor, "enter")
        indirect = direct_cents * award["indirect_rate_bps"] // 10000
        drawn = self._grant_drawn(book_id, award_id, actor)
        _check_draw_within_ceiling(drawn, direct_cents + indirect,
                                   award["ceiling_cents"])
        return self._create("grant_draw", "draw", book_id,
                            {"award_id": award_id, "date": date, "period": date[:7],
                             "direct_cents": direct_cents, "indirect_cents": indirect},
                            actor, "ext_grant_draw_create")

    def _grant_drawn(self, book_id, award_id, actor):
        return sum(r["direct_cents"] + r["indirect_cents"]
                   for r in self._list("grant_draw", book_id, actor)
                   if r["award_id"] == award_id)

    def grant_status(self, book_id, award_id, actor):
        """Drawn / remaining amounts derived at read from draw records."""
        award = self._get("grant_award", book_id, award_id, actor)
        drawn = self._grant_drawn(book_id, award_id, actor)
        return {"award_id": award_id, "book_id": book_id,
                "ceiling_cents": award["ceiling_cents"], "drawn_cents": drawn,
                "remaining_cents": award["ceiling_cents"] - drawn}

    # -- Crypto investigation (records only; no chain access) -------------

    def create_crypto_case(self, book_id, title, wallet_ref, actor):
        _non_empty(title, "case title")
        _non_empty(wallet_ref, "wallet_ref")
        self._access(book_id, actor, "enter")
        return self._create("crypto_case", "ccase", book_id,
                            {"title": title, "wallet_ref": wallet_ref, "status": "open"},
                            actor, "ext_crypto_case_create")

    def record_crypto_transaction(self, book_id, case_id, date, direction,
                                  amount_units, counterparty_ref, actor):
        _date(date)
        if direction not in ("in", "out"):
            raise ValidationError("direction must be 'in' or 'out'")
        _positive(amount_units, "amount_units")
        _non_empty(counterparty_ref, "counterparty_ref")
        self._get("crypto_case", book_id, case_id, actor, "enter")
        return self._create("crypto_txn", "ctxn", book_id,
                            {"case_id": case_id, "date": date, "direction": direction,
                             "amount_units": amount_units,
                             "counterparty_ref": counterparty_ref},
                            actor, "ext_crypto_txn_create")

    def crypto_case_summary(self, book_id, case_id, actor):
        """In/out unit totals derived at read; units are the asset's
        smallest unit as recorded, never converted or priced here."""
        self._get("crypto_case", book_id, case_id, actor)
        txns = [r for r in self._list("crypto_txn", book_id, actor)
                if r["case_id"] == case_id]
        in_units = sum(r["amount_units"] for r in txns if r["direction"] == "in")
        out_units = sum(r["amount_units"] for r in txns if r["direction"] == "out")
        return {"case_id": case_id, "book_id": book_id, "transaction_count": len(txns),
                "in_units": in_units, "out_units": out_units,
                "net_units": in_units - out_units}

    # -- Time tracking ------------------------------------------------------

    def record_time_entry(self, book_id, worker_ref, date, minutes, project_ref, actor):
        _non_empty(worker_ref, "worker_ref")
        _date(date)
        _positive(minutes, "minutes")
        if minutes > 1440:
            raise ValidationError("minutes must not exceed one day (1440)")
        _string(project_ref, "project_ref")
        self._access(book_id, actor, "enter")
        return self._create("time_entry", "time", book_id,
                            {"worker_ref": worker_ref, "date": date,
                             "period": date[:7], "minutes": minutes,
                             "project_ref": project_ref},
                            actor, "ext_time_entry_create")

    def time_summary(self, book_id, period, actor):
        """Total minutes for a period, derived at read from entries."""
        _period(period)
        rows = [r for r in self._list("time_entry", book_id, actor)
                if r["period"] == period]
        by_worker = {}
        for r in rows:
            by_worker[r["worker_ref"]] = by_worker.get(r["worker_ref"], 0) + r["minutes"]
        return {"book_id": book_id, "period": period, "entry_count": len(rows),
                "total_minutes": sum(r["minutes"] for r in rows),
                "by_worker_ref": by_worker}

    # -- E-signature (STUB-ENGINE: labeled reference implementation) -------

    def create_signature_request(self, book_id, document_ref, signer_ref, actor):
        """Record a signature request. REFERENCE STUB: no signing
        service is contacted and nothing is signed; the record exists
        so workflows can reference the request, and it is labeled."""
        _non_empty(document_ref, "document_ref")
        _non_empty(signer_ref, "signer_ref")
        self._access(book_id, actor, "enter")
        return self._create("signature_request", "sig", book_id,
                            {"document_ref": document_ref, "signer_ref": signer_ref,
                             "reference_stub": True,
                             "status": "recorded_reference_only"},
                            actor, "ext_signature_request_create")

    def list_signature_requests(self, book_id, actor):
        return self._list("signature_request", book_id, actor)

    # -- Payroll --------------------------------------------------------------

    def create_payroll_run(self, book_id, period, actor):
        _period(period)
        self._access(book_id, actor, "enter")
        return self._create("payroll_run", "payrun", book_id,
                            {"period": period}, actor, "ext_payroll_run_create")

    def add_pay_line(self, book_id, run_id, worker_ref, gross_cents,
                     deduction_cents, actor):
        _non_empty(worker_ref, "worker_ref")
        _positive(gross_cents, "gross_cents")
        _nonnegative(deduction_cents, "deduction_cents")
        if deduction_cents > gross_cents:
            raise ValidationError("deductions may not exceed gross pay")
        self._get("payroll_run", book_id, run_id, actor, "enter")
        return self._create("pay_line", "payline", book_id,
                            {"run_id": run_id, "worker_ref": worker_ref,
                             "gross_cents": gross_cents,
                             "deduction_cents": deduction_cents},
                            actor, "ext_pay_line_create")

    def payroll_summary(self, book_id, run_id, actor):
        """Gross / deductions / net totals derived at read; the net is
        never stored on a pay line. This records pay; it pays nobody —
        disbursement is an external rail, not this substrate."""
        self._get("payroll_run", book_id, run_id, actor)
        lines = [r for r in self._list("pay_line", book_id, actor)
                 if r["run_id"] == run_id]
        gross = sum(r["gross_cents"] for r in lines)
        deductions = sum(r["deduction_cents"] for r in lines)
        return {"run_id": run_id, "book_id": book_id, "line_count": len(lines),
                "gross_cents": gross, "deduction_cents": deductions,
                "net_cents": gross - deductions}

    # -- Tax --------------------------------------------------------------------

    def create_tax_filing(self, book_id, jurisdiction_ref, period,
                          taxable_base_cents, rate_bps, actor):
        _non_empty(jurisdiction_ref, "jurisdiction_ref")
        _period(period)
        _nonnegative(taxable_base_cents, "taxable_base_cents")
        _bps(rate_bps, "rate_bps")
        self._access(book_id, actor, "enter")
        return self._create("tax_filing", "tax", book_id,
                            {"jurisdiction_ref": jurisdiction_ref, "period": period,
                             "taxable_base_cents": taxable_base_cents,
                             "rate_bps": rate_bps},
                            actor, "ext_tax_filing_create")

    def tax_due(self, book_id, filing_id, actor):
        """Tax due = base x rate, derived at read, never stored. This
        computes a recorded liability figure; it files nothing."""
        filing = self._get("tax_filing", book_id, filing_id, actor)
        due = filing["taxable_base_cents"] * filing["rate_bps"] // 10000
        return {"filing_id": filing_id, "book_id": book_id, "period": filing["period"],
                "taxable_base_cents": filing["taxable_base_cents"],
                "rate_bps": filing["rate_bps"], "tax_due_cents": due}

    # -- Forensic investigation -------------------------------------------------

    def create_forensic_case(self, book_id, title, actor):
        _non_empty(title, "case title")
        self._access(book_id, actor, "enter")
        return self._create("forensic_case", "fcase", book_id,
                            {"title": title, "status": "open"},
                            actor, "ext_forensic_case_create")

    def add_evidence_item(self, book_id, case_id, description, content_hash, actor):
        _non_empty(description, "description")
        if not isinstance(content_hash, str) or not _HASH_RE.match(content_hash):
            raise ValidationError("content_hash must be a hex string of 8-128 characters")
        self._get("forensic_case", book_id, case_id, actor, "enter")
        return self._create("evidence", "evid", book_id,
                            {"case_id": case_id, "description": description,
                             "content_hash": content_hash, "custody": []},
                            actor, "ext_evidence_create")

    def record_custody_transfer(self, book_id, evidence_id, to_ref, date, actor):
        """Append a chain-of-custody transfer; the custody list is
        append-only within the record and every transfer is audited."""
        _non_empty(to_ref, "to_ref")
        _date(date)
        with self._lock:
            item = self._get("evidence", book_id, evidence_id, actor, "enter")
            item["custody"].append({"to_ref": to_ref, "date": date,
                                    "recorded_by": actor_name(actor)})
            self._audit(actor, "ext_custody_transfer", evidence_id,
                        details={"book_id": book_id, "to_ref": to_ref})
            copied = dict(item)
            copied["custody"] = [dict(c) for c in item["custody"]]
            return copied

    def forensic_case_summary(self, book_id, case_id, actor):
        """Evidence and custody counts derived at read."""
        self._get("forensic_case", book_id, case_id, actor)
        items = [r for r in self._list("evidence", book_id, actor)
                 if r["case_id"] == case_id]
        return {"case_id": case_id, "book_id": book_id,
                "evidence_count": len(items),
                "custody_transfers": sum(len(r["custody"]) for r in items)}
