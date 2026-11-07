"""Final GAPS batch extensions for the Human Resources untiered set.

Clean-room, standard-library-only extensions for the 7 open entries
of Untiered Set 16 (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`HrStore`; every core module is untouched and byte-identical.

Tier discipline: this set is **tier null** -- the source publishes
no FedRAMP impact level for either fork, so this surface asserts no
baseline, draws no CMMC equivalence, and no record or view here
carries a tier, baseline, impact-level, or CMMC key (pinned by a
recursive scan in the batch tests).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records.

- Payroll and expenses are administrative records: amounts are
  integer cents, recorded as reported (floats and booleans are
  rejected at the boundary), and every total / net figure is a
  derivation at read time, never stored. A payroll run pays
  nothing and executes nothing (``paid_here`` / ``executed_here``
  are False on the record); an expense approval is a recorded
  decision label, and reimbursement never happens here
  (``reimbursed_here`` False).
- Time tracking and scheduling are records: caller-recorded time
  entries in integer minutes, and schedule assignments held as
  data. No assignment is computed (``assigned_automatically``
  False); project / person summaries are deterministic counts and
  sums derived at read.
- Employee communications are metadata records only: a channel
  label, an opaque audience reference, and an opaque message
  reference. Message content is never held -- no parameter on this
  surface can accept it -- and delivery is a reported receipt in
  the communications adjudicated form (``reference_transport``
  True, ``delivered_here`` False).
- Document management is a registry: opaque document references
  plus optional validated SHA-256 digests and a version chain.
  Document content is never held or stored (``content_held_here``
  / ``stored_here`` False); the current version is derived at
  read from the recorded chain, never stored.
- Identity federation / privileged access and the security
  operations engines are stub-engine entries and ship as labeled
  reference implementations: records carry ``reference_stub``
  True and state ``recorded_reference_only``. Federation stays
  with the embedding organization's identity provider
  (PLATFORM-LAYER.md decision 1; this build ships hooks, not an
  IdP -- ``identity_provider`` False on the record). Security
  operations outcomes and severities are reported labels held
  verbatim; nothing here monitors, scans, or responds
  (``monitored_here`` / ``scanned_here`` / ``responded_here``
  False).

Doctrines carried from the core: opaque ``*_ref`` strings only --
the founding privacy discipline binds this surface exactly as it
binds the core, so no record shape here can hold a real name, SSN,
DOB, salary, address, phone, or email (the core privacy test's
forbidden-key set is pinned over these shapes too, and no public
method on this surface accepts a name-, email-, phone-,
identifier-, or content-shaped argument); person-bound records
are keyed by opaque ``person_ref`` only and are employee-scoped
exactly as the core scopes them; eligibility / qualification
determinations are never computed predicates over people --
outcomes are recorded labels; derived-never-stored for every
computed value (payroll nets and totals, expense totals, time
summaries, document current version, communication receipt
views); append-only audit on the core store's log with
``ext_``-prefixed actions for every successful extension mutation
(denied operations record nothing, the store-level convention --
denial auditing lives in the service layer); RBAC via
:mod:`hr.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing.

RBAC action mapping (the core action set is fixed): payroll runs
and expense reports ride the benefits family (money
administration records); time entries, schedule assignments, and
person time summaries ride the performance family (per-person
work records); communications, documents, federation / privileged
-access reference records, and security-operations reference
records ride the case family (administrative records, per the
founding tier's template / reference-record precedent); aggregate
summary views require ``report_read``, as in the core report.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PAYROLL_RUN_STATES = ("recorded", "closed")
EXPENSE_CATEGORIES = ("travel", "meals", "lodging", "supplies", "other")
EXPENSE_STATES = ("draft", "submitted", "approved", "rejected", "closed")
COMMUNICATION_CHANNELS = ("announcement", "email_notice", "notice_board", "other")
DOCUMENT_KINDS = ("policy", "form", "notice", "record", "other")

# The core privacy test's forbidden-key set (tests/test_privacy.py):
# no extension record shape may carry any of these keys either.
FORBIDDEN_KEYS = {
    "name", "ssn", "social_security_number", "salary", "compensation",
    "pay", "dob", "date_of_birth", "address", "phone", "email",
}
# Tier-shaped keys are forbidden on every extension record and
# derived view: this set is tier null and asserts no baseline.
TIER_KEYS = {"tier", "cmmc_tier", "cmmc", "baseline", "fedramp_impact_level",
             "impact_level"}
# Argument names no public method on this surface may accept: the
# no-PII / no-content invariant at the signature level.
FORBIDDEN_PARAMS = {
    "name", "ssn", "social_security_number", "dob", "date_of_birth",
    "address", "phone", "email", "salary", "compensation",
    "content", "message_text", "document_text", "body",
}


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


def _validate_int(value, what, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_date(value, what):
    """Validate an ISO date string (YYYY-MM-DD); return a date object."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _validate_digest(value, what="digest"):
    """Validate an optional SHA-256 hex digest; return it lowercased."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("%s must be a hex string" % (what,))
    candidate = value.strip().lower()
    if len(candidate) != 64 or any(c not in "0123456789abcdef" for c in candidate):
        raise ValidationError("%s must be a 64-character SHA-256 hex digest" % (what,))
    return candidate


def _maybe_require(actor, action):
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _derive_net_cents(gross_amount_cents, deduction_amounts):
    """Payroll net seam: the single point where a statement's net is
    derived -- the recorded gross minus the recorded deduction
    amounts, in integer cents. The result is a read-time view
    value; it is never stored on the statement record.

    MUTATION DRILL NOTE: this seam is the batch unit's fresh
    negative-control target -- adding the deductions instead of
    subtracting them would silently corrupt every payroll view
    while leaving the stored record shapes intact (see
    tests/README.md).
    """
    return gross_amount_cents - sum(deduction_amounts)


class HrExtensions:
    """Extension surface over an :class:`HrStore` (final GAPS batch)."""

    def __init__(self, store):
        self.store = store
        self._payroll_runs = {}
        self._expense_reports = {}
        self._time_entries = {}
        self._schedule_assignments = {}
        self._communications = {}
        self._delivery_receipts = {}
        self._documents = {}
        self._federation_records = {}
        self._access_reviews = {}
        self._monitoring_reports = {}
        self._vulnerability_reports = {}
        self._security_incidents = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), "ext_" + action, target, details=details)

    @staticmethod
    def _is_employee(actor):
        return actor is not None and getattr(actor, "role", None) == "employee"

    def _scope_check(self, actor, person_ref):
        if self._is_employee(actor) and getattr(actor, "name", None) != person_ref:
            raise PermissionDenied(
                "permission denied: employee %r may not access records of person %r"
                % (getattr(actor, "name", None), person_ref)
            )

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _person_exists(self, person_ref):
        return any(
            p["person_ref"] == person_ref
            for p in self.store.list_persons(actor=None)
        )

    def _require_person_ref(self, person_ref):
        if not self._person_exists(person_ref):
            raise NotFoundError("person not found: %r" % (person_ref,))

    def _get_payroll_run(self, run_id):
        record = self._payroll_runs.get(run_id)
        if record is None:
            raise NotFoundError("payroll run not found: %r" % (run_id,))
        return record

    def _get_expense_report(self, report_id):
        record = self._expense_reports.get(report_id)
        if record is None:
            raise NotFoundError("expense report not found: %r" % (report_id,))
        return record

    def _get_communication(self, communication_id):
        record = self._communications.get(communication_id)
        if record is None:
            raise NotFoundError("communication not found: %r" % (communication_id,))
        return record

    def _get_document(self, document_id):
        record = self._documents.get(document_id)
        if record is None:
            raise NotFoundError("document not found: %r" % (document_id,))
        return record

    # -- payroll processing (records form) -----------------------------
    # A payroll "run" is an administrative record of a pay period
    # with per-person statements whose figures are recorded as
    # reported, in integer cents. Nets and totals are derived at
    # read; nothing is paid and nothing is executed.

    def create_payroll_run(self, period_start, period_end, actor, label=""):
        """Create a payroll run record. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        start = _validate_date(period_start, "period_start")
        end = _validate_date(period_end, "period_end")
        if end < start:
            raise ValidationError("period_end must not be before period_start")
        _validate_string(label, "label")
        with self._lock:
            run_id = self._next_id("prn")
            record = {
                "id": run_id,
                "period_start": period_start,
                "period_end": period_end,
                "label": label,
                "state": "recorded",
                "statements": [],
                "paid_here": False,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payroll_runs[run_id] = record
            self._audit(actor, "payroll_run_create", run_id,
                        details={"period_start": period_start,
                                 "period_end": period_end})
            return self._payroll_run_view(record, actor)

    def add_pay_statement(self, run_id, person_ref, gross_amount_cents, actor,
                          deductions=None):
        """Record one person's statement on a payroll run.

        Action: benefits_write. The person (by opaque person_ref)
        must exist in the core; figures are integer cents as
        reported; a duplicate statement for the same person on the
        same run is a validation error. The statement stores gross
        and deductions only -- the net is derived at read.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_int(gross_amount_cents, "gross_amount_cents", minimum=0)
        if deductions is None:
            deductions = []
        if not isinstance(deductions, (list, tuple)):
            raise ValidationError("deductions must be a list")
        cleaned = []
        for item in deductions:
            if not isinstance(item, dict):
                raise ValidationError("each deduction must be a mapping")
            _validate_non_empty(item.get("label"), "deduction label")
            _validate_int(item.get("amount_cents"), "deduction amount_cents",
                          minimum=0)
            cleaned.append({"label": item["label"],
                            "amount_cents": item["amount_cents"]})
        with self._lock:
            record = self._get_payroll_run(run_id)
            if record["state"] != "recorded":
                raise ValidationError(
                    "payroll run %r is %s; statements cannot be added"
                    % (run_id, record["state"]))
            self._require_person_ref(person_ref)
            if any(s["person_ref"] == person_ref for s in record["statements"]):
                raise ValidationError(
                    "person %r already has a statement on run %r"
                    % (person_ref, run_id))
            statement = {
                "statement_id": "s-%d" % (len(record["statements"]) + 1),
                "person_ref": person_ref,
                "gross_amount_cents": gross_amount_cents,
                "deductions": cleaned,
            }
            record["statements"].append(statement)
            self._audit(actor, "pay_statement_add", run_id,
                        details={"person_ref": person_ref})
            return self._payroll_run_view(record, actor)

    def set_payroll_run_state(self, run_id, state, actor):
        """Set a payroll run's recorded state. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        if state not in PAYROLL_RUN_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(PAYROLL_RUN_STATES),))
        with self._lock:
            record = self._get_payroll_run(run_id)
            record["state"] = state
            self._audit(actor, "payroll_run_set_state", run_id,
                        details={"state": state})
            return self._payroll_run_view(record, actor)

    def _payroll_run_view(self, record, actor):
        view = {
            "id": record["id"],
            "period_start": record["period_start"],
            "period_end": record["period_end"],
            "label": record["label"],
            "state": record["state"],
            "paid_here": record["paid_here"],
            "executed_here": record["executed_here"],
            "created_by": record["created_by"],
            "created_utc": record["created_utc"],
            "derived": True,
        }
        statements = record["statements"]
        if self._is_employee(actor):
            own = getattr(actor, "name", None)
            statements = [s for s in statements if s["person_ref"] == own]
        view_statements = []
        total_gross = 0
        total_deductions = 0
        for statement in statements:
            amounts = [d["amount_cents"] for d in statement["deductions"]]
            net = _derive_net_cents(statement["gross_amount_cents"], amounts)
            view_statements.append({
                "statement_id": statement["statement_id"],
                "person_ref": statement["person_ref"],
                "gross_amount_cents": statement["gross_amount_cents"],
                "deductions": [dict(d) for d in statement["deductions"]],
                "net_amount_cents": net,
            })
            total_gross += statement["gross_amount_cents"]
            total_deductions += sum(amounts)
        view["statements"] = view_statements
        view["statement_count"] = len(view_statements)
        view["total_gross_cents"] = total_gross
        view["total_deduction_cents"] = total_deductions
        view["total_net_cents"] = _derive_net_cents(total_gross,
                                                    [total_deductions])
        return view

    def get_payroll_run(self, run_id, actor=None):
        """Return one payroll run view. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            return self._payroll_run_view(self._get_payroll_run(run_id), actor)

    def list_payroll_runs(self, actor=None):
        """Return payroll run views sorted by id. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            return [self._payroll_run_view(r, actor)
                    for r in self._sorted(self._payroll_runs.values())]

    # -- expense tracking & management ---------------------------------
    # Expense reports are per-person administrative records with
    # integer-cent line items. The report total is derived at read;
    # the approval state is a recorded decision label; nothing is
    # reimbursed here.

    def create_expense_report(self, person_ref, title, actor):
        """Create an expense report. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(title, "expense report title")
        with self._lock:
            self._require_person_ref(person_ref)
            report_id = self._next_id("exp")
            record = {
                "id": report_id,
                "person_ref": person_ref,
                "title": title,
                "state": "draft",
                "lines": [],
                "reimbursed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._expense_reports[report_id] = record
            self._audit(actor, "expense_report_create", report_id,
                        details={"person_ref": person_ref})
            return self._expense_report_view(record)

    def add_expense_line(self, report_id, category, amount_cents, actor,
                         incurred_on=None, note_ref=None):
        """Append one line item to an expense report.

        Action: benefits_write. Amounts are integer cents, strictly
        positive; ``note_ref`` is an opaque reference to a receipt
        held elsewhere -- no receipt content is accepted or held.
        """
        _require_actor(actor, "benefits_write")
        if category not in EXPENSE_CATEGORIES:
            raise ValidationError(
                "category must be one of %s" % (", ".join(EXPENSE_CATEGORIES),))
        _validate_int(amount_cents, "amount_cents", minimum=1)
        if incurred_on is not None:
            _validate_date(incurred_on, "incurred_on")
        if note_ref is not None:
            _validate_non_empty(note_ref, "note_ref")
        with self._lock:
            record = self._get_expense_report(report_id)
            if record["state"] == "closed":
                raise ValidationError(
                    "expense report %r is closed; lines cannot be added"
                    % (report_id,))
            line = {
                "line_id": "l-%d" % (len(record["lines"]) + 1),
                "category": category,
                "amount_cents": amount_cents,
                "incurred_on": incurred_on,
                "note_ref": note_ref,
            }
            record["lines"].append(line)
            self._audit(actor, "expense_line_add", report_id,
                        details={"category": category})
            return self._expense_report_view(record)

    def set_expense_report_state(self, report_id, state, actor):
        """Set an expense report's recorded state. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        if state not in EXPENSE_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(EXPENSE_STATES),))
        with self._lock:
            record = self._get_expense_report(report_id)
            record["state"] = state
            self._audit(actor, "expense_report_set_state", report_id,
                        details={"state": state})
            return self._expense_report_view(record)

    def _expense_report_view(self, record):
        view = dict(record)
        view["lines"] = [dict(line) for line in record["lines"]]
        view["total_cents"] = sum(line["amount_cents"] for line in record["lines"])
        view["line_count"] = len(record["lines"])
        view["derived"] = True
        return view

    def get_expense_report(self, report_id, actor=None):
        """Return one expense report view. Action: benefits_read (+ scope)."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            record = self._get_expense_report(report_id)
            self._scope_check(actor, record["person_ref"])
            return self._expense_report_view(record)

    def list_expense_reports(self, actor=None, person_ref=None):
        """Return expense report views. Action: benefits_read (+ scope)."""
        _maybe_require(actor, "benefits_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._expense_reports.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if self._is_employee(actor):
                own = getattr(actor, "name", None)
                records = [r for r in records if r["person_ref"] == own]
            return [self._expense_report_view(r) for r in self._sorted(records)]

    # -- project time tracking & resource scheduling -------------------
    # Time entries are caller-recorded, in integer minutes.
    # Schedule assignments are definitions held as data; no
    # assignment is computed. Summaries are counts and sums derived
    # at read.

    def record_time_entry(self, person_ref, project_ref, entry_on, minutes,
                          actor, activity_label=""):
        """Record one time entry. Action: performance_write."""
        _require_actor(actor, "performance_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(project_ref, "project_ref")
        _validate_date(entry_on, "entry_on")
        _validate_int(minutes, "minutes", minimum=1)
        _validate_string(activity_label, "activity_label")
        with self._lock:
            self._require_person_ref(person_ref)
            entry_id = self._next_id("tme")
            record = {
                "id": entry_id,
                "person_ref": person_ref,
                "project_ref": project_ref,
                "entry_on": entry_on,
                "minutes": minutes,
                "activity_label": activity_label,
                "source": "recorded",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._time_entries[entry_id] = record
            self._audit(actor, "time_entry_record", entry_id,
                        details={"person_ref": person_ref,
                                 "project_ref": project_ref})
            return dict(record)

    def create_schedule_assignment(self, person_ref, project_ref, starts_on,
                                   ends_on, planned_minutes, actor):
        """Record one schedule assignment as data.

        Action: performance_write. The assignment is a recorded
        plan; this build assigns nobody automatically.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(project_ref, "project_ref")
        start = _validate_date(starts_on, "starts_on")
        end = _validate_date(ends_on, "ends_on")
        if end < start:
            raise ValidationError("ends_on must not be before starts_on")
        _validate_int(planned_minutes, "planned_minutes", minimum=0)
        with self._lock:
            self._require_person_ref(person_ref)
            assignment_id = self._next_id("sch")
            record = {
                "id": assignment_id,
                "person_ref": person_ref,
                "project_ref": project_ref,
                "starts_on": starts_on,
                "ends_on": ends_on,
                "planned_minutes": planned_minutes,
                "assigned_automatically": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._schedule_assignments[assignment_id] = record
            self._audit(actor, "schedule_assignment_create", assignment_id,
                        details={"person_ref": person_ref,
                                 "project_ref": project_ref})
            return dict(record)

    def list_time_entries(self, actor=None, person_ref=None, project_ref=None):
        """Return time entries. Action: performance_read (+ scope)."""
        _maybe_require(actor, "performance_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._time_entries.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if project_ref is not None:
                records = [r for r in records if r["project_ref"] == project_ref]
            if self._is_employee(actor):
                own = getattr(actor, "name", None)
                records = [r for r in records if r["person_ref"] == own]
            return [dict(r) for r in self._sorted(records)]

    def list_schedule_assignments(self, actor=None, person_ref=None,
                                  project_ref=None):
        """Return schedule assignments. Action: performance_read (+ scope)."""
        _maybe_require(actor, "performance_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._schedule_assignments.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if project_ref is not None:
                records = [r for r in records if r["project_ref"] == project_ref]
            if self._is_employee(actor):
                own = getattr(actor, "name", None)
                records = [r for r in records if r["person_ref"] == own]
            return [dict(r) for r in self._sorted(records)]

    def project_time_summary(self, project_ref, actor):
        """Derived counts/sums over one project's records.

        Action: report_read. Computed at read, stored nowhere.
        """
        _require_actor(actor, "report_read")
        _validate_non_empty(project_ref, "project_ref")
        with self._lock:
            entries = [r for r in self._time_entries.values()
                       if r["project_ref"] == project_ref]
            assignments = [r for r in self._schedule_assignments.values()
                           if r["project_ref"] == project_ref]
            return {
                "project_ref": project_ref,
                "entry_count": len(entries),
                "recorded_minutes": sum(r["minutes"] for r in entries),
                "assignment_count": len(assignments),
                "scheduled_minutes": sum(r["planned_minutes"]
                                         for r in assignments),
                "person_count": len({r["person_ref"] for r in entries}
                                    | {r["person_ref"] for r in assignments}),
                "method": "deterministic_counts_and_sums",
                "derived": True,
                "stored": False,
            }

    def person_time_summary(self, person_ref, actor=None):
        """Derived per-person time totals. Action: performance_read (+ scope)."""
        _maybe_require(actor, "performance_read")
        _validate_non_empty(person_ref, "person_ref")
        self._scope_check(actor, person_ref)
        with self._lock:
            self._require_person_ref(person_ref)
            entries = [r for r in self._time_entries.values()
                       if r["person_ref"] == person_ref]
            assignments = [r for r in self._schedule_assignments.values()
                           if r["person_ref"] == person_ref]
            return {
                "person_ref": person_ref,
                "entry_count": len(entries),
                "recorded_minutes": sum(r["minutes"] for r in entries),
                "assignment_count": len(assignments),
                "scheduled_minutes": sum(r["planned_minutes"]
                                         for r in assignments),
                "method": "deterministic_counts_and_sums",
                "derived": True,
                "stored": False,
            }

    # -- employee communications & messaging (metadata records) --------
    # A communication record holds a channel label, an opaque
    # audience reference, and an opaque message reference. Content
    # is never held; delivery is a reported receipt.

    def create_communication(self, channel, audience_ref, message_ref, actor,
                             subject_label=""):
        """Create a communication metadata record. Action: case_write."""
        _require_actor(actor, "case_write")
        if channel not in COMMUNICATION_CHANNELS:
            raise ValidationError(
                "channel must be one of %s"
                % (", ".join(COMMUNICATION_CHANNELS),))
        _validate_non_empty(audience_ref, "audience_ref")
        _validate_non_empty(message_ref, "message_ref")
        _validate_string(subject_label, "subject_label")
        with self._lock:
            communication_id = self._next_id("com")
            record = {
                "id": communication_id,
                "channel": channel,
                "audience_ref": audience_ref,
                "message_ref": message_ref,
                "subject_label": subject_label,
                "state": "recorded",
                "reference_transport": True,
                "delivered_here": False,
                "messages_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._communications[communication_id] = record
            self._audit(actor, "communication_create", communication_id,
                        details={"channel": channel})
            return self._communication_view(record)

    def record_delivery_receipt(self, communication_id, outcome_label, actor,
                                reported_count=None):
        """Record a reported delivery outcome. Action: case_write.

        The outcome is a label reported by the transport outside
        this build, held verbatim; nothing is delivered here.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(outcome_label, "outcome_label")
        if reported_count is not None:
            _validate_int(reported_count, "reported_count", minimum=0)
        with self._lock:
            self._get_communication(communication_id)
            receipt_id = self._next_id("rcp")
            record = {
                "id": receipt_id,
                "communication_id": communication_id,
                "outcome_label": outcome_label,
                "reported_count": reported_count,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_receipts[receipt_id] = record
            self._audit(actor, "delivery_receipt_record", receipt_id,
                        details={"communication_id": communication_id})
            return dict(record)

    def _communication_view(self, record):
        view = dict(record)
        receipts = [r for r in self._delivery_receipts.values()
                    if r["communication_id"] == record["id"]]
        receipts = self._sorted(receipts)
        view["receipt_count"] = len(receipts)
        view["latest_outcome_label"] = (
            receipts[-1]["outcome_label"] if receipts else None)
        view["derived"] = True
        return view

    def get_communication(self, communication_id, actor=None):
        """Return one communication view. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return self._communication_view(
                self._get_communication(communication_id))

    def list_communications(self, actor=None):
        """Return communication views sorted by id. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [self._communication_view(r)
                    for r in self._sorted(self._communications.values())]

    # -- document management services (registry form) ------------------
    # A document record is an opaque reference plus an optional
    # validated digest and a version chain. Content is never held;
    # the current version is derived at read from the chain.

    def register_document(self, document_ref, kind, actor, digest=None,
                          retention_label=""):
        """Register one document reference. Action: case_write."""
        _require_actor(actor, "case_write")
        _validate_non_empty(document_ref, "document_ref")
        if kind not in DOCUMENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(DOCUMENT_KINDS),))
        digest = _validate_digest(digest)
        _validate_string(retention_label, "retention_label")
        with self._lock:
            if any(d["document_ref"] == document_ref
                   for d in self._documents.values()):
                raise ValidationError(
                    "document_ref already registered: %r" % (document_ref,))
            document_id = self._next_id("doc")
            record = {
                "id": document_id,
                "document_ref": document_ref,
                "kind": kind,
                "retention_label": retention_label,
                "versions": [{
                    "version": 1,
                    "digest": digest,
                    "recorded_utc": _utc_now(),
                }],
                "content_held_here": False,
                "stored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._documents[document_id] = record
            self._audit(actor, "document_register", document_id,
                        details={"document_ref": document_ref, "kind": kind})
            return self._document_view(record)

    def add_document_version(self, document_id, actor, digest=None):
        """Append a version to a document's chain. Action: case_write."""
        _require_actor(actor, "case_write")
        digest = _validate_digest(digest)
        with self._lock:
            record = self._get_document(document_id)
            version = {
                "version": len(record["versions"]) + 1,
                "digest": digest,
                "recorded_utc": _utc_now(),
            }
            record["versions"].append(version)
            self._audit(actor, "document_version_add", document_id,
                        details={"version": version["version"]})
            return self._document_view(record)

    def _document_view(self, record):
        view = dict(record)
        view["versions"] = [dict(v) for v in record["versions"]]
        latest = record["versions"][-1]
        view["version_count"] = len(record["versions"])
        view["current_version"] = latest["version"]
        view["current_digest"] = latest["digest"]
        view["derived"] = True
        return view

    def get_document(self, document_id, actor=None):
        """Return one document view. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return self._document_view(self._get_document(document_id))

    def list_documents(self, actor=None):
        """Return document views sorted by id. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [self._document_view(r)
                    for r in self._sorted(self._documents.values())]

    # -- identity federation & privileged access (reference) -----------
    # Stub-engine entry: labeled reference records only. Identity
    # stays with the embedding organization (PLATFORM-LAYER.md
    # decision 1); the build ships hooks, not an IdP.

    def create_federation_record(self, provider_label, actor, protocol_label=""):
        """Record a federation configuration reference.

        Action: case_write. ``provider_label`` names an identity
        provider this build does not federate with; the record
        states that on its face.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(provider_label, "provider_label")
        _validate_string(protocol_label, "protocol_label")
        with self._lock:
            record_id = self._next_id("fed")
            record = {
                "id": record_id,
                "provider_label": provider_label,
                "protocol_label": protocol_label,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "identity_provider": False,
                "federated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._federation_records[record_id] = record
            self._audit(actor, "federation_record_create", record_id,
                        details={"provider_label": provider_label})
            return dict(record)

    def record_access_review(self, person_ref, outcome_label, actor):
        """Record a reported privileged-access review outcome.

        Action: case_write. The outcome is a label reported by the
        privileged-access system outside this build, held verbatim;
        no eligibility or access determination is computed here.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._require_person_ref(person_ref)
            record_id = self._next_id("pam")
            record = {
                "id": record_id,
                "person_ref": person_ref,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "determined_here": False,
                "managed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._access_reviews[record_id] = record
            self._audit(actor, "access_review_record", record_id,
                        details={"person_ref": person_ref})
            return dict(record)

    def list_federation_records(self, actor=None):
        """Return federation reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._federation_records.values())]

    def list_access_reviews(self, actor=None, person_ref=None):
        """Return access review records. Action: case_read (+ scope)."""
        _maybe_require(actor, "case_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._access_reviews.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if self._is_employee(actor):
                own = getattr(actor, "name", None)
                records = [r for r in records if r["person_ref"] == own]
            return [dict(r) for r in self._sorted(records)]

    # -- security operations engines (reference) -----------------------
    # Stub-engine entry: labeled reference records only. Outcomes,
    # severities, and counts are reported by systems outside this
    # build and held verbatim; nothing here monitors, scans, or
    # responds.

    def record_monitoring_report(self, source_label, outcome_label, actor,
                                 reported_count=None):
        """Record a reported monitoring outcome. Action: case_write."""
        _require_actor(actor, "case_write")
        _validate_non_empty(source_label, "source_label")
        _validate_non_empty(outcome_label, "outcome_label")
        if reported_count is not None:
            _validate_int(reported_count, "reported_count", minimum=0)
        with self._lock:
            record_id = self._next_id("mon")
            record = {
                "id": record_id,
                "source_label": source_label,
                "outcome_label": outcome_label,
                "reported_count": reported_count,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "monitored_here": False,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._monitoring_reports[record_id] = record
            self._audit(actor, "monitoring_report_record", record_id,
                        details={"source_label": source_label})
            return dict(record)

    def record_vulnerability_report(self, source_label, severity_label, actor,
                                    reported_count=None):
        """Record a reported vulnerability outcome. Action: case_write.

        ``severity_label`` is the reporting system's label, held
        verbatim; no severity is computed here.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(source_label, "source_label")
        _validate_non_empty(severity_label, "severity_label")
        if reported_count is not None:
            _validate_int(reported_count, "reported_count", minimum=0)
        with self._lock:
            record_id = self._next_id("vul")
            record = {
                "id": record_id,
                "source_label": source_label,
                "severity_label": severity_label,
                "reported_count": reported_count,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "scanned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vulnerability_reports[record_id] = record
            self._audit(actor, "vulnerability_report_record", record_id,
                        details={"source_label": source_label})
            return dict(record)

    def record_security_incident(self, title, actor, case_id=None):
        """Record a reported security incident. Action: case_write.

        Optionally bound to a core personnel case record, which
        must exist and is never modified by this record.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(title, "incident title")
        with self._lock:
            if case_id is not None:
                self.store.get_case(case_id, actor=None)
            record_id = self._next_id("inc")
            record = {
                "id": record_id,
                "title": title,
                "case_id": case_id,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "responded_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._security_incidents[record_id] = record
            self._audit(actor, "security_incident_record", record_id,
                        details={"case_id": case_id})
            return dict(record)

    def list_monitoring_reports(self, actor=None):
        """Return monitoring reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._monitoring_reports.values())]

    def list_vulnerability_reports(self, actor=None):
        """Return vulnerability reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._vulnerability_reports.values())]

    def list_security_incidents(self, actor=None):
        """Return security incident reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._security_incidents.values())]

    def security_operations_summary(self, actor):
        """Derived counts over the security-operations records.

        Action: report_read. Computed at read, stored nowhere.
        """
        _require_actor(actor, "report_read")
        with self._lock:
            return {
                "monitoring_reports": len(self._monitoring_reports),
                "vulnerability_reports": len(self._vulnerability_reports),
                "security_incidents": len(self._security_incidents),
                "reference_stub": True,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
            }

    # -- extension summary ----------------------------------------------

    def extension_summary(self, actor):
        """Derived counts over the whole extension surface.

        Action: report_read. Computed at read, stored nowhere.
        """
        _require_actor(actor, "report_read")
        with self._lock:
            return {
                "payroll_runs": len(self._payroll_runs),
                "expense_reports": len(self._expense_reports),
                "time_entries": len(self._time_entries),
                "schedule_assignments": len(self._schedule_assignments),
                "communications": len(self._communications),
                "delivery_receipts": len(self._delivery_receipts),
                "documents": len(self._documents),
                "federation_records": len(self._federation_records),
                "access_reviews": len(self._access_reviews),
                "monitoring_reports": len(self._monitoring_reports),
                "vulnerability_reports": len(self._vulnerability_reports),
                "security_incidents": len(self._security_incidents),
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
            }
