"""Final GAPS batch extensions for the Finance untiered set
(Untiered Set 24).

Clean-room, standard-library-only records extensions for the 2
open entries this set's GAPS.md section carries. See ``BATCH.md``
in the group directory for the per-entry disposition, including
the one re-judgment recorded there under
``gaps-batch/DECISION.md`` qualification 1.

This set is **untiered**: the member fork's FedRAMP impact level
is Unknown in the source, tier stays null, no baseline is
asserted, and no CMMC equivalence is drawn. Nothing in this
module names a tier, a baseline, or an impact level; the records
and views it produces carry no such key (pinned by recursive scan
in ``tests/test_gaps_batch.py``).

Design, following the core's doctrines and the founding Finance
L2 batch unit's extension pattern:

- This module is a wrapper around :class:`FinanceStore`; the core
  modules are untouched (byte-identical). Core state (programs,
  participants) is read through the core store's public API, never
  re-implemented, and no extension operation writes core state.
- **Records, not execution** is the founding discipline and this
  surface does not repeal it: nothing here pays, reimburses,
  settles, or moves money. An approved expense report gains a
  *reimbursement record* -- a record, after the fact, that money
  moved on external rails, exactly the core's disbursement-record
  doctrine -- carrying ``paid_here: False`` and
  ``settled_here: False`` on its face.
- **Money is integer cents, everywhere.** Every ``*_cents`` field
  is validated exactly as the core validates: a Python ``int``,
  booleans and floats rejected at the boundary, and a rejected
  operation consumes no id and stores nothing.
- The expense workflow is the core's own workflow shape (Core 8)
  carried to expense records: ``draft -> submitted -> approved /
  denied``, ``approved -> reimbursed`` via a reimbursement record,
  ``draft / submitted / denied -> void`` -- with **separation of
  duties**: the decider of a report is never its creator, exactly
  as the core's ``decide_access`` enforces.
- Policy enforcement is rules-as-data plus a deterministic
  derivation: a policy record holds declared rules (a per-category
  line cap, a report total cap) and an evaluation derives
  compliance at read from the policy's recorded rules and a
  report's recorded lines, through the comparison seam
  :meth:`FinanceExtensions._exceeds` -- the batch's fresh
  negative-control target. An evaluation is a view, never stored;
  it flags, and blocks nothing (no payment exists here to block:
  ``blocked_here: False``). A line exactly at a cap complies --
  exceeding is strictly greater, mirroring the core's earned-cap
  boundary where exactly-at-cap passes.
- Totals are derived at read and never stored: an expense
  report's stored record carries no total; its view adds
  ``total_cents`` summed from the recorded lines. The period
  summary's counts and totals likewise derive at read over this
  surface's own records and state their basis.
- RBAC goes through :mod:`finance.access` exactly as the core
  enforces it: each extension operation maps onto an existing core
  action -- creates onto ``enter``, decisions onto ``decide``,
  reimbursement records onto ``record``, reads and derived views
  onto ``read`` -- checked *before* any state change or id
  allocation for User-like actors, with role denials recorded on
  the core audit log as ``ext_<action>:denied``. Program
  membership (the second boundary) is enforced through the core
  store's own access-checked program read. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If the
  audit write raises, the mutation and its id roll back before
  the error propagates: no extension record or transition exists
  whose audit entry does not.
- People are known only by the core's opaque-reference
  participants: every person-shaped field on this surface is a
  core ``participant_id`` whose record must exist in the same
  program, so the core's pinned participant shape -- which cannot
  hold a real name, bank account number, card number, or
  government identifier -- governs this surface too. **No record
  shape in this module has a field that could hold a real account
  identifier**; the absence is pinned by exact key-set tests and
  recursive key scans.
- Expense and policy layers stay distinct from the core's other
  finance layers: expense totals never enter the core's budgets,
  accruals, or program summary, and a full expense flow leaves
  every core record byte-identical (pinned by test). The general
  ledger / CPM / federal-system-of-record surfaces of the tiered
  finance builds are separate builds, not merged here.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

EXPENSE_STATUSES = (
    "draft",
    "submitted",
    "approved",
    "denied",
    "reimbursed",
    "void",
)
KNOWN_EXPENSE_STATUSES = frozenset(EXPENSE_STATUSES)

POLICY_RULE_KINDS = ("category_line_cap", "report_total_cap")
KNOWN_POLICY_RULE_KINDS = frozenset(POLICY_RULE_KINDS)

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _require_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % (what,))
    return value


def _cents_positive(value, what):
    _require_int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _cents_nonnegative(value, what):
    _require_int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _validate_period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError(
            "%s must be a period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid period: %r" % (what, value)) from exc
    return value


def _validate_date(value, what="date"):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValidationError(
            "%s must be an ISO date (YYYY-MM-DD): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid calendar date: %r" % (what, value)) from exc
    return value


def _validate_expense_lines(lines):
    """Validate expense lines; return a normalized deep copy.

    A line is ``{"category": <non-empty label>, "amount_cents":
    <positive int>}`` -- exactly those keys. Categories are
    unique within a report, mirroring the core's budget-line
    rule.
    """
    if not isinstance(lines, list) or not lines:
        raise ValidationError("expense lines must be a non-empty list")
    seen = set()
    normalized = []
    for line in lines:
        if not isinstance(line, dict) or set(line) != {"category", "amount_cents"}:
            raise ValidationError(
                "each expense line must have exactly the keys "
                "'category' and 'amount_cents'")
        category = _validate_non_empty(line["category"], "expense line category")
        amount = _cents_positive(line["amount_cents"], "expense line amount_cents")
        if category in seen:
            raise ValidationError(
                "duplicate expense line category: %r" % (category,))
        seen.add(category)
        normalized.append({"category": category, "amount_cents": amount})
    return normalized


def _validate_policy_rules(rules):
    """Validate policy rules; return a normalized deep copy.

    A rule is ``{"kind": ..., "category": ..., "limit_cents":
    ...}`` -- exactly those keys. ``category_line_cap`` rules
    name a category; ``report_total_cap`` rules carry
    ``category: None``. (kind, category) pairs are unique within
    a policy.
    """
    if not isinstance(rules, list) or not rules:
        raise ValidationError("policy rules must be a non-empty list")
    seen = set()
    normalized = []
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"kind", "category", "limit_cents"}:
            raise ValidationError(
                "each policy rule must have exactly the keys "
                "'kind', 'category' and 'limit_cents'")
        kind = rule["kind"]
        if kind not in KNOWN_POLICY_RULE_KINDS:
            raise ValidationError(
                "policy rule kind must be one of %s"
                % (", ".join(POLICY_RULE_KINDS),))
        if kind == "category_line_cap":
            category = _validate_non_empty(rule["category"], "policy rule category")
        else:
            if rule["category"] is not None:
                raise ValidationError(
                    "a report_total_cap rule carries no category")
            category = None
        limit = _cents_nonnegative(rule["limit_cents"], "policy rule limit_cents")
        key = (kind, category)
        if key in seen:
            raise ValidationError(
                "duplicate policy rule: %r for category %r" % (kind, category))
        seen.add(key)
        normalized.append(
            {"kind": kind, "category": category, "limit_cents": limit})
    return normalized


class FinanceExtensions:
    """GAPS-batch extension surface over a core FinanceStore."""

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
        """Enforce a permission, auditing a denial.

        Mirrors the core convention: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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

    def _program(self, program_id, actor):
        """Core access-checked program read (membership + read role).

        Raises NotFoundError for an unknown program and
        PermissionDenied for a non-member, exactly as the core does.
        """
        return self.store.get_program(program_id, actor)

    def _participant(self, program_id, participant_id, actor):
        """Return the core participant (NotFoundError if absent)."""
        return self.store.get_participant(program_id, participant_id, actor)

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

    def _transition(self, record, changes, actor, audit_action, target):
        """Apply ``changes`` to a stored record, auditing the move.

        If the audit write raises, the record is restored whole
        before the error propagates: no transition exists whose
        audit entry does not.
        """
        snapshot = copy.deepcopy(record)
        record.update(changes)
        try:
            self._audit(actor, audit_action, target,
                        details={"status": changes.get("status")})
        except Exception:
            record.clear()
            record.update(snapshot)
            raise
        return copy.deepcopy(record)

    def _get(self, kind, record_id, program_id):
        record = self._records.get((kind, record_id))
        if record is None or record["program_id"] != program_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

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

    @staticmethod
    def _report_total(record):
        """Derive a report's total from its recorded lines."""
        return sum(line["amount_cents"] for line in record["lines"])

    def _report_view(self, record):
        """Return the expense report record plus its derived total."""
        view = copy.deepcopy(record)
        view["total_cents"] = self._report_total(record)
        return view

    # -- expense reports (idx 948) --------------------------------------

    def create_expense_report(self, program_id, participant_id, period,
                              lines, actor):
        """Create an expense report in status ``draft``.

        The participant must be a core participant of the same
        program (either kind: employees and travelers both file
        expenses). The report's total is NOT stored; it derives at
        read from the recorded lines.
        """
        self._guard(actor, "enter", "ext_expense_create")
        self._program(program_id, actor)
        self._participant(program_id, participant_id, actor)
        _validate_period(period)
        lines = _validate_expense_lines(lines)
        fields = {
            "program_id": program_id,
            "participant_id": participant_id,
            "period": period,
            "lines": lines,
            "status": "draft",
        }
        return self._create(
            "expense_report", "exp", fields, actor, "ext_expense_create")

    def get_expense_report(self, program_id, report_id, actor):
        """Return one expense report view (record + derived total)."""
        self._guard(actor, "read", "ext_expense_read", target=report_id)
        self._program(program_id, actor)
        with self._lock:
            return self._report_view(
                self._get("expense_report", report_id, program_id))

    def list_expense_reports(self, program_id, actor, status=None,
                             participant_id=None):
        """Return a program's expense report views, in creation order."""
        if status is not None and status not in KNOWN_EXPENSE_STATUSES:
            raise ValidationError("unknown expense report status: %r" % (status,))
        self._guard(actor, "read", "ext_expense_read")
        self._program(program_id, actor)
        filters = {}
        if status is not None:
            filters["status"] = status
        if participant_id is not None:
            filters["participant_id"] = participant_id
        with self._lock:
            return [
                self._report_view(record)
                for record in self._list("expense_report", program_id, **filters)
            ]

    def _check_report_actor(self, program, record, actor, what):
        """Mirror the core's void rule: creator, owner, or admin."""
        if (
            actor_name(actor) != record["created_by"]
            and actor_name(actor) != program["owner"]
            and getattr(actor, "role", None) != "admin"
        ):
            raise PermissionDenied(
                "permission denied: only the creator, the program owner, or "
                "a platform admin may %s this expense report" % (what,)
            )

    def submit_expense_report(self, program_id, report_id, actor):
        """Move a ``draft`` expense report to ``submitted``."""
        self._guard(actor, "enter", "ext_expense_submit", target=report_id)
        program = self._program(program_id, actor)
        with self._lock:
            record = self._get("expense_report", report_id, program_id)
            if record["status"] != "draft":
                raise ValidationError(
                    "expense report in status %r cannot be submitted"
                    % (record["status"],))
            self._check_report_actor(program, record, actor, "submit")
            return self._transition(
                record, {"status": "submitted"}, actor,
                "ext_expense_submit", report_id)

    def decide_expense_report(self, program_id, report_id, approve, actor):
        """Approve or deny a ``submitted`` expense report.

        Separation of duties: the decider is never the report's
        creator, exactly as the core's ``decide_access`` enforces.
        """
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        self._guard(actor, "decide", "ext_expense_decide", target=report_id)
        self._program(program_id, actor)
        with self._lock:
            record = self._get("expense_report", report_id, program_id)
            if record["status"] != "submitted":
                raise ValidationError(
                    "expense report in status %r cannot be decided"
                    % (record["status"],))
            if actor_name(actor) == record["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not decide their own "
                    "expense report")
            changes = {
                "status": "approved" if approve else "denied",
                "decided_by": actor_name(actor),
                "decided_utc": _utc_now(),
            }
            return self._transition(
                record, changes, actor,
                "ext_expense_approve" if approve else "ext_expense_deny",
                report_id)

    def void_expense_report(self, program_id, report_id, actor):
        """Move a ``draft``/``submitted``/``denied`` report to ``void``."""
        self._guard(actor, "enter", "ext_expense_void", target=report_id)
        program = self._program(program_id, actor)
        with self._lock:
            record = self._get("expense_report", report_id, program_id)
            if record["status"] not in ("draft", "submitted", "denied"):
                raise ValidationError(
                    "expense report in status %r cannot be voided"
                    % (record["status"],))
            self._check_report_actor(program, record, actor, "void")
            return self._transition(
                record, {"status": "void"}, actor,
                "ext_expense_void", report_id)

    def record_reimbursement(self, program_id, report_id, date, actor,
                             method=""):
        """Record that an approved report was reimbursed externally.

        This build records reimbursements; it executes nothing.
        The amount, participant and period are taken from the
        report (its total derived from its recorded lines), whose
        status becomes ``reimbursed``.
        """
        _validate_date(date, "date")
        if method is None:
            method = ""
        _validate_string(method, "method")
        self._guard(actor, "record", "ext_reimbursement_record",
                    target=report_id)
        self._program(program_id, actor)
        with self._lock:
            record = self._get("expense_report", report_id, program_id)
            if record["status"] != "approved":
                raise ValidationError(
                    "reimbursements may only be recorded against an "
                    "approved expense report")
            fields = {
                "program_id": program_id,
                "report_id": report_id,
                "participant_id": record["participant_id"],
                "period": record["period"],
                "amount_cents": self._report_total(record),
                "date": date,
                "method": method,
                "paid_here": False,
                "settled_here": False,
            }
            reimbursement = self._create(
                "reimbursement", "rei", fields, actor,
                "ext_reimbursement_record")
            try:
                self._transition(
                    record,
                    {"status": "reimbursed",
                     "reimbursement_id": reimbursement["id"]},
                    actor, "ext_expense_reimburse", report_id)
            except Exception:
                # The reimbursement record and the transition are
                # one act: if the transition's audit write fails,
                # the record rolls back with it.
                del self._records[("reimbursement", reimbursement["id"])]
                self._order.remove(("reimbursement", reimbursement["id"]))
                self._counters["rei"] -= 1
                raise
            return reimbursement

    def list_reimbursements(self, program_id, actor, report_id=None):
        """Return a program's reimbursement records, in creation order."""
        self._guard(actor, "read", "ext_reimbursement_read")
        self._program(program_id, actor)
        filters = {}
        if report_id is not None:
            filters["report_id"] = report_id
        with self._lock:
            return self._list("reimbursement", program_id, **filters)

    def expense_summary(self, program_id, period, actor):
        """Derive a program's expense counts and totals for a period.

        Counts and totals derive at read over this surface's own
        recorded expense lines and reimbursement records only;
        nothing is stored, and no core record contributes.
        """
        _validate_period(period)
        self._guard(actor, "read", "ext_expense_summary")
        self._program(program_id, actor)
        with self._lock:
            reports = [
                record for record in self._list("expense_report", program_id)
                if record["period"] == period
            ]
            counts = {status: 0 for status in EXPENSE_STATUSES}
            totals = {status: 0 for status in EXPENSE_STATUSES}
            for record in reports:
                counts[record["status"]] += 1
                totals[record["status"]] += self._report_total(record)
            reimbursed_cents = sum(
                record["amount_cents"]
                for record in self._list("reimbursement", program_id)
                if record["period"] == period
            )
            return {
                "program_id": program_id,
                "period": period,
                "report_count": len(reports),
                "counts_by_status": counts,
                "totals_by_status_cents": totals,
                "reimbursed_cents": reimbursed_cents,
                "basis": "recorded_expense_lines_and_reimbursement_records",
                "paid_here": False,
            }

    # -- expense policies (idx 949) -------------------------------------

    def create_expense_policy(self, program_id, name, rules, actor):
        """Create an expense policy: declared rules, held as data."""
        self._guard(actor, "enter", "ext_policy_create")
        self._program(program_id, actor)
        _validate_non_empty(name, "policy name")
        rules = _validate_policy_rules(rules)
        fields = {
            "program_id": program_id,
            "name": name,
            "rules": rules,
            "definition_only": True,
        }
        return self._create(
            "expense_policy", "pol", fields, actor, "ext_policy_create")

    def get_expense_policy(self, program_id, policy_id, actor):
        """Return one expense policy record."""
        self._guard(actor, "read", "ext_policy_read", target=policy_id)
        self._program(program_id, actor)
        with self._lock:
            return copy.deepcopy(
                self._get("expense_policy", policy_id, program_id))

    def list_expense_policies(self, program_id, actor):
        """Return a program's expense policies, in creation order."""
        self._guard(actor, "read", "ext_policy_read")
        self._program(program_id, actor)
        with self._lock:
            return self._list("expense_policy", program_id)

    def _exceeds(self, observed_cents, limit_cents):
        """The policy comparison seam: strictly greater exceeds.

        A value exactly at the limit complies, mirroring the
        core's earned-cap boundary (exactly-at-cap passes). Every
        comparison in policy evaluation routes through here; this
        is the negative control's target.
        """
        return observed_cents > limit_cents

    def evaluate_expense_report(self, program_id, policy_id, report_id,
                                actor):
        """Derive a report's compliance with a policy, at read.

        The evaluation is computed from the policy's recorded
        rules and the report's recorded lines and is never stored.
        It flags violations; it blocks nothing -- no payment
        exists in this build to block.
        """
        self._guard(actor, "read", "ext_policy_evaluate")
        self._program(program_id, actor)
        with self._lock:
            policy = self._get("expense_policy", policy_id, program_id)
            report = self._get("expense_report", report_id, program_id)
            total = self._report_total(report)
            violations = []
            for index, rule in enumerate(policy["rules"]):
                if rule["kind"] == "category_line_cap":
                    for line in report["lines"]:
                        if line["category"] != rule["category"]:
                            continue
                        if self._exceeds(line["amount_cents"],
                                         rule["limit_cents"]):
                            violations.append({
                                "rule_index": index,
                                "kind": rule["kind"],
                                "category": rule["category"],
                                "limit_cents": rule["limit_cents"],
                                "observed_cents": line["amount_cents"],
                            })
                else:  # report_total_cap
                    if self._exceeds(total, rule["limit_cents"]):
                        violations.append({
                            "rule_index": index,
                            "kind": rule["kind"],
                            "category": None,
                            "limit_cents": rule["limit_cents"],
                            "observed_cents": total,
                        })
            return {
                "program_id": program_id,
                "policy_id": policy_id,
                "report_id": report_id,
                "period": report["period"],
                "compliant": not violations,
                "violations": violations,
                "violation_count": len(violations),
                "method": "deterministic_derivation_over_recorded_rules_and_lines",
                "blocked_here": False,
                "paid_here": False,
            }
