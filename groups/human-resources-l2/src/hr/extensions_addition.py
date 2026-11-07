"""Final GAPS batch, second unit -- remainder-addition extensions
for the Human Resources L2 build.

Clean-room, standard-library-only extensions for the 6 open entries
of the GAPS.md section "Remainder Addition -- Human Resources L2
(+3 forks)" (inventory idx 607-612; see ``BATCH-ADDITION.md`` in the
group directory for the per-entry disposition). This module is a
second wrapper around :class:`HrStore`; the first batch unit's
``extensions.py`` and every core module are untouched.

Honesty of form, per the batch brief and the first unit's forms:

- Time, attendance & leave (idx 607) is records plus derivation:
  time entries and their corrections are records, leave accounts
  record their accrual rate as data, accruals and leave requests
  are records, and the leave balance is derived at read from those
  records -- never stored. No business-rule engine edits an entry:
  a correction is a new record, and the effective minutes are the
  derivation over the entry and its corrections.
- Organizational charts (idx 608) are a derived view over org-unit
  records and position-assignment records: the chart is generated
  at read from the current records, so maintenance is the records
  changing, and a reported-change record states what was reported.
  Nothing renders or publishes a chart anywhere.
- The survey & listening platform (idx 609) is instrument
  definitions plus response records holding reported values
  verbatim: ratings are integers bounded by the instrument's
  recorded scale, signals are labels, and NO method on this surface
  accepts free-text response content -- there is no content,
  comment, or text parameter anywhere (pinned by a signature scan),
  so a narrative answer cannot exist in this substrate. Summaries
  are deterministic counts over the recorded values, never means:
  no engagement score is computed anywhere.
- Benefits administration depth (idx 610) is administration case
  records bound to the core benefits records, worked as task
  checklists whose status is derived at read exactly as the core
  derives lifecycle-case status, plus reported action and
  counseling-session records. It administers nothing against any
  external system and computes no amount (the calculator is the
  first unit's entry and stays there).
- The self-service portal & dashboard (idx 611) is configuration
  and definitions as data plus figures derived at read: a portal
  profile records which section labels a person's portal shows and
  states on its face that identity stays with the embedding
  organization (PLATFORM-LAYER.md decision 1) and that nothing is
  served here; self-service requests are case-shaped records;
  dashboard definitions are pinned to an exact key set that can
  hold no figure, and the dashboard view derives its figures at
  read over exactly the records visible to the actor.
- Uniform allowance processing (idx 612) is workflow records:
  requests in integer cents (an allowance amount is a recorded
  request figure, never a pay figure -- no record here can hold
  one), processing-step records with reported outcome labels, and
  a summary of counts and recorded-cents sums derived at read.

Doctrines carried from the core and the first unit: opaque
``*_ref`` strings only (the same forbidden-key set the core privacy
tests use is pinned over these shapes too, and no stored record
carries an aggregate key); derived-never-stored for every computed
value (effective minutes, leave balances, chart views, survey
counts, admin-case status, dashboard figures, allowance summaries);
append-only audit on the core store's log with ``ext2_``-prefixed
actions for every successful addition mutation (denied operations
record nothing, the store-level convention); RBAC via
:mod:`hr.access` with the core's existing actions, enforced before
any state change or id allocation, so a failed operation consumes
no id and changes nothing; employee scope mirrors the store's.

RBAC action mapping (the core action set is fixed): time, leave,
and allowance records ride the benefits family (leave and allowance
are benefit-shaped; time entries bind the same person's leave
accounting); org units, assignments, and chart views ride the
position family; survey instruments, responses, listening signals,
and multi-rater feedback ride the performance family, with survey
summaries gated on ``report_read`` like the core report; benefits
administration cases, actions, and counseling sessions ride the
benefits family; portal profiles, self-service requests, and
dashboard definitions ride the case family, with dashboard views
gated on ``report_read``.
"""

import copy
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .extensions import AGGREGATE_KEYS, FORBIDDEN_KEYS

__all__ = [
    "AGGREGATE_KEYS",
    "FORBIDDEN_KEYS",
    "HrExtensionsAddition",
]

TIME_ENTRY_KINDS = ("regular", "overtime", "leave", "holiday")
LEAVE_KINDS = ("annual", "sick", "vltp", "fmla", "other")
LEAVE_REQUEST_STATES = ("requested", "approved", "denied", "taken", "cancelled")
ADMIN_CASE_KINDS = (
    "enrollment_review", "retirement_counseling", "eligibility_review",
    "provider_coordination", "general_administration",
)
ADMIN_TASK_STATES = ("pending", "done", "waived")
LISTENING_CHANNELS = ("pulse", "always_on", "lifecycle", "dialogue")
SERVICE_REQUEST_KINDS = (
    "profile_update", "document_request", "benefits_question", "general",
)
SERVICE_REQUEST_STATES = ("opened", "in_review", "closed")
ALLOWANCE_REQUEST_STATES = (
    "requested", "approved", "denied", "fulfilled", "cancelled",
)
DASHBOARD_PANEL_KINDS = (
    "persons", "positions", "vacancies", "applications",
    "benefits", "cases", "lifecycle_cases", "performance_reviews",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_int(value, what, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    if maximum is not None and value > maximum:
        raise ValidationError("%s must be at most %d" % (what, maximum))
    return value


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


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


class HrExtensionsAddition:
    """Second extension surface over an :class:`HrStore`."""

    def __init__(self, store):
        self.store = store
        self._time_entries = {}
        self._time_corrections = {}
        self._leave_accounts = {}
        self._leave_accruals = {}
        self._leave_requests = {}
        self._org_units = {}
        self._org_assignments = {}
        self._org_changes = {}
        self._survey_instruments = {}
        self._survey_responses = {}
        self._listening_signals = {}
        self._feedback_records = {}
        self._admin_cases = {}
        self._admin_actions = {}
        self._counseling_sessions = {}
        self._portal_profiles = {}
        self._service_requests = {}
        self._dashboards = {}
        self._allowance_requests = {}
        self._allowance_steps = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), "ext2_" + action, target, details=details)

    @staticmethod
    def _is_employee(actor):
        return actor is not None and getattr(actor, "role", None) == "employee"

    def _scope_check(self, actor, person_ref):
        if self._is_employee(actor) and getattr(actor, "name", None) != person_ref:
            raise PermissionDenied(
                "permission denied: employee %r may not access records of person %r"
                % (getattr(actor, "name", None), person_ref)
            )

    def _scoped(self, actor, records):
        if self._is_employee(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get("person_ref") == name]
        return list(records)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _require_person_ref(self, person_ref):
        _validate_non_empty(person_ref, "person_ref")
        persons = self.store.list_persons(actor=None)
        if not any(p["person_ref"] == person_ref for p in persons):
            raise NotFoundError("person not found: %r" % (person_ref,))

    # -- Time, attendance & leave tracking (idx 607) -------------------
    # Records plus derivation: entries and corrections are records;
    # the effective minutes of an entry are derived at read (the
    # latest correction wins). Leave accounts record an accrual rate
    # as data; accrual events and requests are records; the balance
    # is derived at read and never stored.

    def record_time_entry(self, person_ref, work_date, minutes, kind_label, actor):
        """Record one time entry. Action: benefits_write.

        ``minutes`` is a non-negative integer; ``kind_label`` is one
        of TIME_ENTRY_KINDS. The person must exist in the core.
        """
        _require_actor(actor, "benefits_write")
        _validate_date(work_date, "work_date")
        _validate_int(minutes, "minutes", minimum=0)
        if kind_label not in TIME_ENTRY_KINDS:
            raise ValidationError(
                "kind_label must be one of %s" % (", ".join(TIME_ENTRY_KINDS),)
            )
        with self._lock:
            self._require_person_ref(person_ref)
            entry_id = self._next_id("tim")
            record = {
                "id": entry_id,
                "person_ref": person_ref,
                "work_date": work_date,
                "minutes": minutes,
                "kind_label": kind_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._time_entries[entry_id] = record
            self._audit(actor, "time_entry_create", entry_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def record_time_correction(self, entry_id, corrected_minutes, reason_label, actor):
        """Record a correction to a time entry. Action: benefits_write.

        The original entry is never edited; the correction is its
        own record and the effective minutes are derived at read.
        """
        _require_actor(actor, "benefits_write")
        _validate_int(corrected_minutes, "corrected_minutes", minimum=0)
        _validate_non_empty(reason_label, "reason_label")
        with self._lock:
            entry = self._time_entries.get(entry_id)
            if entry is None:
                raise NotFoundError("time entry not found: %r" % (entry_id,))
            correction_id = self._next_id("tcr")
            record = {
                "id": correction_id,
                "entry_id": entry_id,
                "person_ref": entry["person_ref"],
                "corrected_minutes": corrected_minutes,
                "reason_label": reason_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._time_corrections[correction_id] = record
            self._audit(actor, "time_correction_create", correction_id,
                        details={"entry_id": entry_id})
            return copy.deepcopy(record)

    def _effective_minutes(self, entry):
        corrections = [
            c for c in self._time_corrections.values()
            if c["entry_id"] == entry["id"]
        ]
        if not corrections:
            return entry["minutes"]
        return self._sorted(corrections)[-1]["corrected_minutes"]

    def list_time_entries(self, actor=None, person_ref=None):
        """Return time-entry views with derived effective minutes.

        Action: benefits_read. Employee-scoped. The stored record
        carries no effective-minutes key; the view adds it.
        """
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._time_entries.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            views = []
            for record in self._sorted(records):
                view = copy.deepcopy(record)
                view["effective_minutes"] = self._effective_minutes(record)
                views.append(view)
            return views

    def time_summary(self, person_ref, actor=None):
        """Derive a per-person time summary at read. Never stored.

        Action: benefits_read; employee-scoped to the actor's own
        person_ref. Counts and effective-minute totals over the
        recorded entries only. Method: ``deterministic_counts``.
        """
        _maybe_require(actor, "benefits_read")
        self._scope_check(actor, person_ref)
        with self._lock:
            self._require_person_ref(person_ref)
            entries = [
                e for e in self._time_entries.values()
                if e["person_ref"] == person_ref
            ]
            by_kind = {}
            total = 0
            for entry in self._sorted(entries):
                effective = self._effective_minutes(entry)
                total += effective
                by_kind[entry["kind_label"]] = by_kind.get(entry["kind_label"], 0) + 1
            return {
                "person_ref": person_ref,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "entry_count": len(entries),
                "effective_minutes_total": total,
                "entries_by_kind": by_kind,
            }

    def create_leave_account(self, person_ref, leave_kind, accrual_minutes_per_period, actor):
        """Create a leave account record. Action: benefits_write.

        The accrual rate is recorded as data (integer minutes per
        period); one account per person and leave kind.
        """
        _require_actor(actor, "benefits_write")
        if leave_kind not in LEAVE_KINDS:
            raise ValidationError(
                "leave_kind must be one of %s" % (", ".join(LEAVE_KINDS),)
            )
        _validate_int(
            accrual_minutes_per_period, "accrual_minutes_per_period", minimum=0
        )
        with self._lock:
            self._require_person_ref(person_ref)
            for account in self._leave_accounts.values():
                if (account["person_ref"] == person_ref
                        and account["leave_kind"] == leave_kind):
                    raise ValidationError(
                        "leave account already exists for person %r kind %r"
                        % (person_ref, leave_kind)
                    )
            account_id = self._next_id("lva")
            record = {
                "id": account_id,
                "person_ref": person_ref,
                "leave_kind": leave_kind,
                "accrual_minutes_per_period": accrual_minutes_per_period,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._leave_accounts[account_id] = record
            self._audit(actor, "leave_account_create", account_id,
                        details={"person_ref": person_ref, "leave_kind": leave_kind})
            return copy.deepcopy(record)

    def record_leave_accrual(self, account_id, periods, actor):
        """Record an accrual event on a leave account.

        Action: benefits_write. ``periods`` is a positive integer;
        the accrued minutes are derived from the account's recorded
        rate at read, never stored on the event.
        """
        _require_actor(actor, "benefits_write")
        _validate_int(periods, "periods", minimum=1)
        with self._lock:
            account = self._leave_accounts.get(account_id)
            if account is None:
                raise NotFoundError("leave account not found: %r" % (account_id,))
            accrual_id = self._next_id("lac")
            record = {
                "id": accrual_id,
                "account_id": account_id,
                "person_ref": account["person_ref"],
                "leave_kind": account["leave_kind"],
                "periods": periods,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._leave_accruals[accrual_id] = record
            self._audit(actor, "leave_accrual_create", accrual_id,
                        details={"account_id": account_id})
            return copy.deepcopy(record)

    def create_leave_request(self, person_ref, leave_kind, minutes_requested,
                             start_date, actor):
        """Create a leave request record. Action: benefits_write.

        State starts ``requested`` and changes only through
        :meth:`set_leave_request_state`.
        """
        _require_actor(actor, "benefits_write")
        if leave_kind not in LEAVE_KINDS:
            raise ValidationError(
                "leave_kind must be one of %s" % (", ".join(LEAVE_KINDS),)
            )
        _validate_int(minutes_requested, "minutes_requested", minimum=1)
        _validate_date(start_date, "start_date")
        with self._lock:
            self._require_person_ref(person_ref)
            request_id = self._next_id("lvr")
            record = {
                "id": request_id,
                "person_ref": person_ref,
                "leave_kind": leave_kind,
                "minutes_requested": minutes_requested,
                "start_date": start_date,
                "state": "requested",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._leave_requests[request_id] = record
            self._audit(actor, "leave_request_create", request_id,
                        details={"person_ref": person_ref, "leave_kind": leave_kind})
            return copy.deepcopy(record)

    def set_leave_request_state(self, request_id, state, actor):
        """Set a leave request's recorded state. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        if state not in LEAVE_REQUEST_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(LEAVE_REQUEST_STATES),)
            )
        with self._lock:
            record = self._leave_requests.get(request_id)
            if record is None:
                raise NotFoundError("leave request not found: %r" % (request_id,))
            record["state"] = state
            self._audit(actor, "leave_request_state", request_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def list_leave_requests(self, actor=None, person_ref=None):
        """Return leave request records. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._leave_requests.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def _leave_used_minutes(self, requests):
        """Minutes counting against a balance: approved or taken."""
        return sum(
            r["minutes_requested"] for r in requests
            if r["state"] in ("approved", "taken")
        )

    def leave_balance_view(self, person_ref, leave_kind, actor=None):
        """Derive a leave balance at read. Never stored.

        Action: benefits_read; employee-scoped. Accrued minutes are
        the account's recorded rate times the recorded accrual
        periods; used minutes are the recorded minutes of requests
        in state approved or taken (the ``_leave_used_minutes``
        seam); pending minutes are requests still in state
        requested. Method: ``integer_leave_accounting``.
        """
        _maybe_require(actor, "benefits_read")
        self._scope_check(actor, person_ref)
        if leave_kind not in LEAVE_KINDS:
            raise ValidationError(
                "leave_kind must be one of %s" % (", ".join(LEAVE_KINDS),)
            )
        with self._lock:
            self._require_person_ref(person_ref)
            account = None
            for candidate in self._leave_accounts.values():
                if (candidate["person_ref"] == person_ref
                        and candidate["leave_kind"] == leave_kind):
                    account = candidate
                    break
            if account is None:
                raise NotFoundError(
                    "leave account not found for person %r kind %r"
                    % (person_ref, leave_kind)
                )
            accrued = sum(
                event["periods"] * account["accrual_minutes_per_period"]
                for event in self._leave_accruals.values()
                if event["account_id"] == account["id"]
            )
            requests = [
                r for r in self._leave_requests.values()
                if r["person_ref"] == person_ref and r["leave_kind"] == leave_kind
            ]
            used = self._leave_used_minutes(requests)
            pending = sum(
                r["minutes_requested"] for r in requests if r["state"] == "requested"
            )
            return {
                "person_ref": person_ref,
                "leave_kind": leave_kind,
                "account_id": account["id"],
                "method": "integer_leave_accounting",
                "derived": True,
                "stored": False,
                "accrued_minutes": accrued,
                "used_minutes": used,
                "pending_minutes": pending,
                "balance_minutes": accrued - used,
            }

    # -- Organizational chart generation & maintenance (idx 608) -------
    # Org units and position assignments are records; the chart is a
    # view derived at read from the current records, so it is always
    # as current as the records (maintenance = records changing).
    # Reported changes are records of what was reported.

    def create_org_unit(self, unit_ref, title, actor, parent_unit_ref=None):
        """Create an org-unit record. Action: position_write.

        ``unit_ref`` is a unique opaque label; ``parent_unit_ref``,
        when given, must name an existing unit.
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(unit_ref, "unit_ref")
        _validate_non_empty(title, "title")
        with self._lock:
            for unit in self._org_units.values():
                if unit["unit_ref"] == unit_ref:
                    raise ValidationError("duplicate unit_ref: %r" % (unit_ref,))
            if parent_unit_ref is not None:
                if not any(
                    u["unit_ref"] == parent_unit_ref for u in self._org_units.values()
                ):
                    raise NotFoundError(
                        "parent org unit not found: %r" % (parent_unit_ref,)
                    )
            unit_id = self._next_id("ogu")
            record = {
                "id": unit_id,
                "unit_ref": unit_ref,
                "title": title,
                "parent_unit_ref": parent_unit_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._org_units[unit_id] = record
            self._audit(actor, "org_unit_create", unit_id,
                        details={"unit_ref": unit_ref})
            return copy.deepcopy(record)

    def assign_position_to_unit(self, position_id, unit_ref, actor):
        """Assign a core position to an org unit. Action: position_write.

        The position must exist in the core; it is never modified.
        A position has at most one assignment record on this
        surface: a second assignment for the same position is
        rejected (there is no delete or unassign API; a reported
        reorganization is a change record, and the chart view
        derives from the assignment records as they stand).
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(unit_ref, "unit_ref")
        with self._lock:
            self.store.get_position(position_id, actor=None)
            if not any(
                u["unit_ref"] == unit_ref for u in self._org_units.values()
            ):
                raise NotFoundError("org unit not found: %r" % (unit_ref,))
            for assignment in self._org_assignments.values():
                if assignment["position_id"] == position_id:
                    raise ValidationError(
                        "position %r already assigned to unit %r"
                        % (position_id, assignment["unit_ref"])
                    )
            assignment_id = self._next_id("oga")
            record = {
                "id": assignment_id,
                "position_id": position_id,
                "unit_ref": unit_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._org_assignments[assignment_id] = record
            self._audit(actor, "org_assignment_create", assignment_id,
                        details={"position_id": position_id, "unit_ref": unit_ref})
            return copy.deepcopy(record)

    def record_org_change(self, unit_ref, change_label, outcome_label, actor):
        """Record a reported organizational change. Action: position_write.

        A record of what was reported; applying changes to units is
        done by creating units and assignments, never by this record.
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(change_label, "change_label")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            if not any(
                u["unit_ref"] == unit_ref for u in self._org_units.values()
            ):
                raise NotFoundError("org unit not found: %r" % (unit_ref,))
            change_id = self._next_id("ogc")
            record = {
                "id": change_id,
                "unit_ref": unit_ref,
                "change_label": change_label,
                "outcome_label": outcome_label,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._org_changes[change_id] = record
            self._audit(actor, "org_change_create", change_id,
                        details={"unit_ref": unit_ref})
            return copy.deepcopy(record)

    def list_org_units(self, actor=None):
        """Return org-unit records. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            return [
                copy.deepcopy(r) for r in self._sorted(self._org_units.values())
            ]

    def org_chart_view(self, actor=None):
        """Derive the organizational chart at read. Never stored.

        Action: position_read. Units in unit-id order, each with the
        position ids assigned to it and their count, both derived
        from the assignment records at read; positions with no
        assignment are listed separately. Method:
        ``deterministic_org_chart_derivation``.
        """
        _maybe_require(actor, "position_read")
        with self._lock:
            units = []
            assigned_position_ids = set()
            for unit in self._sorted(self._org_units.values()):
                position_ids = [
                    a["position_id"]
                    for a in self._sorted(self._org_assignments.values())
                    if a["unit_ref"] == unit["unit_ref"]
                ]
                assigned_position_ids.update(position_ids)
                units.append({
                    "unit_ref": unit["unit_ref"],
                    "title": unit["title"],
                    "parent_unit_ref": unit["parent_unit_ref"],
                    "position_ids": position_ids,
                    "position_count": len(position_ids),
                })
            all_position_ids = [
                p["id"] for p in self.store.list_positions(actor=None)
            ]
            unassigned = [
                pid for pid in all_position_ids if pid not in assigned_position_ids
            ]
            return {
                "method": "deterministic_org_chart_derivation",
                "derived": True,
                "stored": False,
                "units": units,
                "unit_count": len(units),
                "unassigned_position_ids": unassigned,
            }

    # -- Employee engagement survey & listening platform (idx 609) -----
    # Instrument definitions plus response records holding reported
    # values verbatim. No method accepts free-text response content:
    # answers are integer ratings bounded by the instrument's
    # recorded scale, signals and feedback carry labels and verbatim
    # ratings only. Summaries are deterministic counts, never means.

    def create_survey_instrument(self, instrument_ref, title, questions, actor):
        """Create a survey instrument definition. Action: performance_write.

        ``questions`` is a non-empty list of
        ``{question_ref, topic_label, max_rating}`` objects with
        exactly those keys; ``max_rating`` is a positive integer
        bounding every recorded answer to that question.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(instrument_ref, "instrument_ref")
        _validate_non_empty(title, "title")
        if not isinstance(questions, (list, tuple)) or not questions:
            raise ValidationError("questions must be a non-empty list")
        cleaned = []
        seen = set()
        for entry in questions:
            if not isinstance(entry, dict):
                raise ValidationError("each question must be an object")
            if set(entry) != {"question_ref", "topic_label", "max_rating"}:
                raise ValidationError(
                    "each question must have exactly question_ref, "
                    "topic_label, max_rating"
                )
            question_ref = _validate_non_empty(
                entry.get("question_ref"), "question_ref"
            )
            topic_label = _validate_non_empty(entry.get("topic_label"), "topic_label")
            max_rating = _validate_int(entry.get("max_rating"), "max_rating", minimum=1)
            if question_ref in seen:
                raise ValidationError("duplicate question_ref: %r" % (question_ref,))
            seen.add(question_ref)
            cleaned.append({
                "question_ref": question_ref,
                "topic_label": topic_label,
                "max_rating": max_rating,
            })
        with self._lock:
            for instrument in self._survey_instruments.values():
                if instrument["instrument_ref"] == instrument_ref:
                    raise ValidationError(
                        "duplicate instrument_ref: %r" % (instrument_ref,)
                    )
            instrument_id = self._next_id("svi")
            record = {
                "id": instrument_id,
                "instrument_ref": instrument_ref,
                "title": title,
                "questions": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._survey_instruments[instrument_id] = record
            self._audit(actor, "survey_instrument_create", instrument_id,
                        details={"instrument_ref": instrument_ref})
            return copy.deepcopy(record)

    def get_survey_instrument(self, instrument_id, actor=None):
        """Return one survey instrument. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            record = self._survey_instruments.get(instrument_id)
            if record is None:
                raise NotFoundError(
                    "survey instrument not found: %r" % (instrument_id,)
                )
            return copy.deepcopy(record)

    def record_survey_response(self, instrument_id, person_ref, answers, actor):
        """Record one survey response. Action: performance_write.

        ``answers`` is a non-empty list of ``{question_ref, rating}``
        objects with exactly those keys; every rating is an integer
        between 1 and the question's recorded ``max_rating`` and is
        stored verbatim. There is deliberately no parameter that
        could hold a narrative answer.
        """
        _require_actor(actor, "performance_write")
        if not isinstance(answers, (list, tuple)) or not answers:
            raise ValidationError("answers must be a non-empty list")
        with self._lock:
            instrument = self._survey_instruments.get(instrument_id)
            if instrument is None:
                raise NotFoundError(
                    "survey instrument not found: %r" % (instrument_id,)
                )
            self._require_person_ref(person_ref)
            scales = {q["question_ref"]: q["max_rating"] for q in instrument["questions"]}
            cleaned = []
            seen = set()
            for entry in answers:
                if not isinstance(entry, dict):
                    raise ValidationError("each answer must be an object")
                if set(entry) != {"question_ref", "rating"}:
                    raise ValidationError(
                        "each answer must have exactly question_ref, rating"
                    )
                question_ref = entry.get("question_ref")
                if question_ref not in scales:
                    raise ValidationError(
                        "unknown question_ref for this instrument: %r" % (question_ref,)
                    )
                if question_ref in seen:
                    raise ValidationError(
                        "duplicate answer for question_ref: %r" % (question_ref,)
                    )
                seen.add(question_ref)
                rating = _validate_int(
                    entry.get("rating"), "rating",
                    minimum=1, maximum=scales[question_ref],
                )
                cleaned.append({"question_ref": question_ref, "rating": rating})
            response_id = self._next_id("svr")
            record = {
                "id": response_id,
                "instrument_id": instrument_id,
                "person_ref": person_ref,
                "answers": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._survey_responses[response_id] = record
            self._audit(actor, "survey_response_create", response_id,
                        details={"instrument_id": instrument_id,
                                 "person_ref": person_ref})
            return copy.deepcopy(record)

    def list_survey_responses(self, actor=None, instrument_id=None, person_ref=None):
        """Return survey response records. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            records = list(self._survey_responses.values())
            if instrument_id is not None:
                records = [r for r in records if r["instrument_id"] == instrument_id]
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def survey_summary(self, instrument_id, actor=None):
        """Derive survey counts at read. Never stored.

        Action: report_read. Per question, the count of responses
        recorded at each rating value -- counts only; no mean or
        score is computed anywhere on this surface. Method:
        ``deterministic_counts``.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            instrument = self._survey_instruments.get(instrument_id)
            if instrument is None:
                raise NotFoundError(
                    "survey instrument not found: %r" % (instrument_id,)
                )
            responses = [
                r for r in self._survey_responses.values()
                if r["instrument_id"] == instrument_id
            ]
            questions = []
            for question in instrument["questions"]:
                counts = {}
                for response in responses:
                    for answer in response["answers"]:
                        if answer["question_ref"] == question["question_ref"]:
                            key = answer["rating"]
                            counts[key] = counts.get(key, 0) + 1
                questions.append({
                    "question_ref": question["question_ref"],
                    "topic_label": question["topic_label"],
                    "rating_counts": [
                        {"rating": rating, "count": counts[rating]}
                        for rating in sorted(counts)
                    ],
                    "answer_count": sum(counts.values()),
                })
            return {
                "instrument_id": instrument_id,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "response_count": len(responses),
                "questions": questions,
            }

    def record_listening_signal(self, person_ref, channel_label, signal_label, actor):
        """Record one reported listening signal. Action: performance_write.

        Channels are the recorded LISTENING_CHANNELS labels; the
        signal itself is a label only -- no narrative content can be
        recorded.
        """
        _require_actor(actor, "performance_write")
        if channel_label not in LISTENING_CHANNELS:
            raise ValidationError(
                "channel_label must be one of %s" % (", ".join(LISTENING_CHANNELS),)
            )
        _validate_non_empty(signal_label, "signal_label")
        with self._lock:
            self._require_person_ref(person_ref)
            signal_id = self._next_id("lis")
            record = {
                "id": signal_id,
                "person_ref": person_ref,
                "channel_label": channel_label,
                "signal_label": signal_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._listening_signals[signal_id] = record
            self._audit(actor, "listening_signal_create", signal_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def list_listening_signals(self, actor=None, person_ref=None):
        """Return listening signal records. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            records = list(self._listening_signals.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def record_feedback(self, person_ref, rater_ref, topic_label, rating, actor):
        """Record one multi-rater feedback entry, verbatim.

        Action: performance_write. The rating is an integer 1..5
        stored exactly as reported; no aggregate over feedback is
        computed or stored anywhere.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(rater_ref, "rater_ref")
        _validate_non_empty(topic_label, "topic_label")
        _validate_int(rating, "rating", minimum=1, maximum=5)
        with self._lock:
            self._require_person_ref(person_ref)
            feedback_id = self._next_id("fbk")
            record = {
                "id": feedback_id,
                "person_ref": person_ref,
                "rater_ref": rater_ref,
                "topic_label": topic_label,
                "rating": rating,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._feedback_records[feedback_id] = record
            self._audit(actor, "feedback_create", feedback_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def list_feedback(self, actor=None, person_ref=None):
        """Return feedback records. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            records = list(self._feedback_records.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- Benefits administration platform depth (idx 610) --------------
    # Administration cases bound to core benefits records, worked as
    # task checklists with status derived at read (the core lifecycle
    # derivation, applied to this surface's own records), plus
    # reported action records and counseling-session records.

    @staticmethod
    def _derive_admin_case_status(case):
        if case["cancelled"]:
            return "cancelled"
        tasks = case["tasks"]
        if not tasks or all(t["state"] == "pending" for t in tasks):
            return "not_started"
        if all(t["state"] in ("done", "waived") for t in tasks):
            return "complete"
        return "in_progress"

    def _admin_case_view(self, record):
        view = copy.deepcopy(record)
        view["status"] = self._derive_admin_case_status(record)
        return view

    def _admin_case_person_ref(self, record):
        benefits = self.store.get_benefits_record(record["benefits_record_id"], actor=None)
        return benefits["person_ref"]

    def create_admin_case(self, benefits_record_id, kind_label, actor, task_titles=None):
        """Create a benefits administration case. Action: benefits_write.

        Bound to a core benefits record, which is never modified.
        ``task_titles`` is an optional list of checklist titles; the
        case's status is derived at read from the task states and
        is never stored on the record.
        """
        _require_actor(actor, "benefits_write")
        if kind_label not in ADMIN_CASE_KINDS:
            raise ValidationError(
                "kind_label must be one of %s" % (", ".join(ADMIN_CASE_KINDS),)
            )
        titles = []
        if task_titles is not None:
            if not isinstance(task_titles, (list, tuple)):
                raise ValidationError("task_titles must be a list")
            for title in task_titles:
                _validate_non_empty(title, "task title")
                titles.append(title)
        with self._lock:
            self.store.get_benefits_record(benefits_record_id, actor=None)
            case_id = self._next_id("adc")
            tasks = [
                {"id": "t-%d" % (i + 1), "title": title, "state": "pending"}
                for i, title in enumerate(titles)
            ]
            record = {
                "id": case_id,
                "benefits_record_id": benefits_record_id,
                "kind_label": kind_label,
                "tasks": tasks,
                "cancelled": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._admin_cases[case_id] = record
            self._audit(actor, "admin_case_create", case_id,
                        details={"benefits_record_id": benefits_record_id})
            return self._admin_case_view(record)

    def add_admin_task(self, case_id, title, actor):
        """Append a task to an admin case. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        _validate_non_empty(title, "title")
        with self._lock:
            record = self._admin_cases.get(case_id)
            if record is None:
                raise NotFoundError("admin case not found: %r" % (case_id,))
            task_id = "t-%d" % (len(record["tasks"]) + 1)
            record["tasks"].append({"id": task_id, "title": title, "state": "pending"})
            self._audit(actor, "admin_task_add", case_id, details={"task_id": task_id})
            return self._admin_case_view(record)

    def set_admin_task_state(self, case_id, task_id, state, actor):
        """Set one admin-case task's state. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        if state not in ADMIN_TASK_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(ADMIN_TASK_STATES),)
            )
        with self._lock:
            record = self._admin_cases.get(case_id)
            if record is None:
                raise NotFoundError("admin case not found: %r" % (case_id,))
            for task in record["tasks"]:
                if task["id"] == task_id:
                    task["state"] = state
                    self._audit(actor, "admin_task_state", case_id,
                                details={"task_id": task_id, "state": state})
                    return self._admin_case_view(record)
            raise NotFoundError(
                "task not found: %r in admin case %r" % (task_id, case_id)
            )

    def cancel_admin_case(self, case_id, actor):
        """Record the cancellation event on an admin case.

        Action: benefits_write. Cancellation is a recorded flag;
        the derived status reads ``cancelled`` from it.
        """
        _require_actor(actor, "benefits_write")
        with self._lock:
            record = self._admin_cases.get(case_id)
            if record is None:
                raise NotFoundError("admin case not found: %r" % (case_id,))
            record["cancelled"] = True
            self._audit(actor, "admin_case_cancel", case_id)
            return self._admin_case_view(record)

    def get_admin_case(self, case_id, actor=None):
        """Return one admin case view. Action: benefits_read.

        Employee-scoped through the bound benefits record.
        """
        _maybe_require(actor, "benefits_read")
        with self._lock:
            record = self._admin_cases.get(case_id)
            if record is None:
                raise NotFoundError("admin case not found: %r" % (case_id,))
            self._scope_check(actor, self._admin_case_person_ref(record))
            return self._admin_case_view(record)

    def list_admin_cases(self, actor=None, benefits_record_id=None):
        """Return admin case views. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._admin_cases.values())
            if benefits_record_id is not None:
                records = [
                    r for r in records if r["benefits_record_id"] == benefits_record_id
                ]
            views = []
            for record in self._sorted(records):
                if self._is_employee(actor):
                    if self._admin_case_person_ref(record) != getattr(actor, "name", None):
                        continue
                views.append(self._admin_case_view(record))
            return views

    def record_admin_action(self, case_id, action_label, outcome_label, actor):
        """Record a reported administration action on a case.

        Action: benefits_write. A record of what was reported done
        under the case; it changes no core benefits record.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(action_label, "action_label")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            if case_id not in self._admin_cases:
                raise NotFoundError("admin case not found: %r" % (case_id,))
            action_id = self._next_id("ada")
            record = {
                "id": action_id,
                "case_id": case_id,
                "action_label": action_label,
                "outcome_label": outcome_label,
                "administered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._admin_actions[action_id] = record
            self._audit(actor, "admin_action_create", action_id,
                        details={"case_id": case_id})
            return copy.deepcopy(record)

    def record_counseling_session(self, person_ref, session_kind_label,
                                  outcome_label, actor):
        """Record a reported counseling session. Action: benefits_write.

        A record of a session as reported (kind and outcome labels);
        no session is conducted by this build.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(session_kind_label, "session_kind_label")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._require_person_ref(person_ref)
            session_id = self._next_id("cns")
            record = {
                "id": session_id,
                "person_ref": person_ref,
                "session_kind_label": session_kind_label,
                "outcome_label": outcome_label,
                "conducted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._counseling_sessions[session_id] = record
            self._audit(actor, "counseling_session_create", session_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def list_counseling_sessions(self, actor=None, person_ref=None):
        """Return counseling session records. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._counseling_sessions.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- Self-service portal & HR dashboard (idx 611) ------------------
    # Portal profiles and dashboard definitions are records (data);
    # self-service requests are case-shaped records; dashboard
    # figures are derived at read over the records visible to the
    # actor. Nothing is served and no identity is provided here.

    def create_portal_profile(self, person_ref, section_labels, actor):
        """Create a self-service portal profile. Action: case_write.

        One profile per person. The record states on its face that
        identity stays with the embedding organization
        (``identity_provider: False``, PLATFORM-LAYER.md decision 1)
        and that this build serves no portal (``served_here:
        False``); the profile is the configuration record the
        embedding organization's portal would read.
        """
        _require_actor(actor, "case_write")
        if not isinstance(section_labels, (list, tuple)) or not section_labels:
            raise ValidationError("section_labels must be a non-empty list")
        labels = []
        for label in section_labels:
            _validate_non_empty(label, "section label")
            labels.append(label)
        with self._lock:
            self._require_person_ref(person_ref)
            for profile in self._portal_profiles.values():
                if profile["person_ref"] == person_ref:
                    raise ValidationError(
                        "portal profile already exists for person %r" % (person_ref,)
                    )
            profile_id = self._next_id("prt")
            record = {
                "id": profile_id,
                "person_ref": person_ref,
                "section_labels": labels,
                "identity_provider": False,
                "served_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portal_profiles[profile_id] = record
            self._audit(actor, "portal_profile_create", profile_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def get_portal_profile(self, profile_id, actor=None):
        """Return one portal profile. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            record = self._portal_profiles.get(profile_id)
            if record is None:
                raise NotFoundError("portal profile not found: %r" % (profile_id,))
            self._scope_check(actor, record["person_ref"])
            return copy.deepcopy(record)

    def create_service_request(self, person_ref, kind_label, actor):
        """Create a self-service request record. Action: case_write."""
        _require_actor(actor, "case_write")
        if kind_label not in SERVICE_REQUEST_KINDS:
            raise ValidationError(
                "kind_label must be one of %s" % (", ".join(SERVICE_REQUEST_KINDS),)
            )
        with self._lock:
            self._require_person_ref(person_ref)
            request_id = self._next_id("ssr")
            record = {
                "id": request_id,
                "person_ref": person_ref,
                "kind_label": kind_label,
                "state": "opened",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._service_requests[request_id] = record
            self._audit(actor, "service_request_create", request_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def set_service_request_state(self, request_id, state, actor):
        """Set a service request's recorded state. Action: case_write."""
        _require_actor(actor, "case_write")
        if state not in SERVICE_REQUEST_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(SERVICE_REQUEST_STATES),)
            )
        with self._lock:
            record = self._service_requests.get(request_id)
            if record is None:
                raise NotFoundError("service request not found: %r" % (request_id,))
            record["state"] = state
            self._audit(actor, "service_request_state", request_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def list_service_requests(self, actor=None, person_ref=None):
        """Return service request records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            records = list(self._service_requests.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def create_dashboard(self, title, panels, actor):
        """Create a dashboard definition record. Action: case_write.

        The stored record is pinned to exactly ``{id, title, panels,
        created_by, created_utc}`` -- no figure can be stored on it.
        ``panels`` is a non-empty list of DASHBOARD_PANEL_KINDS
        labels, recorded as data.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(title, "title")
        if not isinstance(panels, (list, tuple)) or not panels:
            raise ValidationError("panels must be a non-empty list")
        cleaned = []
        for panel in panels:
            if panel not in DASHBOARD_PANEL_KINDS:
                raise ValidationError(
                    "panel must be one of %s" % (", ".join(DASHBOARD_PANEL_KINDS),)
                )
            cleaned.append(panel)
        with self._lock:
            dashboard_id = self._next_id("dsh")
            record = {
                "id": dashboard_id,
                "title": title,
                "panels": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[dashboard_id] = record
            self._audit(actor, "dashboard_create", dashboard_id,
                        details={"title": title})
            return copy.deepcopy(record)

    def get_dashboard(self, dashboard_id, actor=None):
        """Return one dashboard definition. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            record = self._dashboards.get(dashboard_id)
            if record is None:
                raise NotFoundError("dashboard not found: %r" % (dashboard_id,))
            return copy.deepcopy(record)

    def _panel_count(self, panel, actor):
        store = self.store
        if panel == "persons":
            return len(store.list_persons(actor=actor))
        if panel == "positions":
            return len(store.list_positions(actor=actor))
        if panel == "vacancies":
            return len(store.list_vacancies(actor=actor))
        if panel == "applications":
            return len(store.list_applications(actor=actor))
        if panel == "benefits":
            return len(store.list_benefits_records(actor=actor))
        if panel == "cases":
            return len(store.list_cases(actor=actor))
        if panel == "lifecycle_cases":
            return len(store.list_lifecycle_cases(actor=actor))
        if panel == "performance_reviews":
            return len(store.list_performance_reviews(actor=actor))
        raise ValidationError("unknown panel kind: %r" % (panel,))

    def dashboard_view(self, dashboard_id, actor=None):
        """Derive a dashboard's figures at read. Never stored.

        Action: report_read. Each panel's figure is the count of
        the core records of that kind visible to the actor (the
        core's own list methods apply employee scope), derived at
        read, so a dashboard recorded earlier reports records
        recorded after it. Method: ``deterministic_counts``.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            record = self._dashboards.get(dashboard_id)
            if record is None:
                raise NotFoundError("dashboard not found: %r" % (dashboard_id,))
            figures = [
                {"panel": panel, "count": self._panel_count(panel, actor)}
                for panel in record["panels"]
            ]
            return {
                "dashboard_id": dashboard_id,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "figures": figures,
            }

    # -- Uniform allowance request processing (idx 612) ----------------
    # Workflow records: requests in integer cents with recorded
    # states, processing-step records with reported outcomes, and a
    # summary derived at read (counts + recorded-cents sums).

    def create_allowance_request(self, person_ref, item_label, amount_cents, actor):
        """Create a uniform allowance request. Action: benefits_write.

        ``amount_cents`` is a positive integer number of cents --
        the requested allowance amount as recorded data. It is not
        a pay figure and no pay figure can be recorded here.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(item_label, "item_label")
        _validate_int(amount_cents, "amount_cents", minimum=1)
        with self._lock:
            self._require_person_ref(person_ref)
            request_id = self._next_id("uar")
            record = {
                "id": request_id,
                "person_ref": person_ref,
                "item_label": item_label,
                "amount_cents": amount_cents,
                "state": "requested",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._allowance_requests[request_id] = record
            self._audit(actor, "allowance_request_create", request_id,
                        details={"person_ref": person_ref})
            return copy.deepcopy(record)

    def set_allowance_request_state(self, request_id, state, actor):
        """Set an allowance request's recorded state.

        Action: benefits_write.
        """
        _require_actor(actor, "benefits_write")
        if state not in ALLOWANCE_REQUEST_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(ALLOWANCE_REQUEST_STATES),)
            )
        with self._lock:
            record = self._allowance_requests.get(request_id)
            if record is None:
                raise NotFoundError("allowance request not found: %r" % (request_id,))
            record["state"] = state
            self._audit(actor, "allowance_request_state", request_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def record_allowance_step(self, request_id, step_label, outcome_label, actor):
        """Record one processing step on an allowance request.

        Action: benefits_write. Steps are records with reported
        outcome labels; recording one changes no request state.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(step_label, "step_label")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            if request_id not in self._allowance_requests:
                raise NotFoundError("allowance request not found: %r" % (request_id,))
            step_id = self._next_id("uas")
            record = {
                "id": step_id,
                "request_id": request_id,
                "step_label": step_label,
                "outcome_label": outcome_label,
                "processed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._allowance_steps[step_id] = record
            self._audit(actor, "allowance_step_create", step_id,
                        details={"request_id": request_id})
            return copy.deepcopy(record)

    def list_allowance_requests(self, actor=None, person_ref=None):
        """Return allowance request records. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._allowance_requests.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            records = self._scoped(actor, records)
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def list_allowance_steps(self, actor=None, request_id=None):
        """Return allowance processing-step records.

        Action: benefits_read; employee-scoped through the request.
        """
        _maybe_require(actor, "benefits_read")
        with self._lock:
            records = list(self._allowance_steps.values())
            if request_id is not None:
                records = [r for r in records if r["request_id"] == request_id]
            if self._is_employee(actor):
                own = {
                    r["id"] for r in self._allowance_requests.values()
                    if r["person_ref"] == getattr(actor, "name", None)
                }
                records = [r for r in records if r["request_id"] in own]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def allowance_summary(self, actor=None):
        """Derive the allowance summary at read. Never stored.

        Action: report_read. Request counts by recorded state and
        recorded-cents sums by state, over the request records
        only. Method: ``deterministic_counts``.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            by_state = {}
            cents_by_state = {}
            for record in self._allowance_requests.values():
                state = record["state"]
                by_state[state] = by_state.get(state, 0) + 1
                cents_by_state[state] = (
                    cents_by_state.get(state, 0) + record["amount_cents"]
                )
            return {
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "request_count": len(self._allowance_requests),
                "requests_by_state": by_state,
                "amount_cents_by_state": cents_by_state,
            }
