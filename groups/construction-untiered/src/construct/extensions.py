"""Final GAPS batch extensions for the Construction untiered
set (Untiered Set 7).

Clean-room, standard-library-only extensions for the 9 open
entries of the "Untiered Set 7 — Construction (6 forks, tier
null)" section of GAPS.md (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a
wrapper around :class:`ConstructStore`; every core module is
untouched and byte-identical to the shipped build.

**Tier discipline binds the extension surface exactly as it
binds the core.** This set's source publishes no FedRAMP impact
level for any member, so tier stays null: no record shape
carries a tier, a baseline, or an equivalence of any kind, and
a test scans every extension record and derived view
recursively for tier-shaped keys, for floats, and for numeric
lists. Nothing here asserts a control baseline or draws a CMMC
equivalence; the forks' documented control claims remain where
``UNION-SPEC.md`` put them — the forks' claims about
themselves, recorded in the spec.

**The founding discipline binds absolutely, here as in the
core:** this build holds records about construction work. It
commissions no system, runs no estimating engine over
proprietary data, reviews no document, checks no specification,
controls no document content, senses no position, issues no
permit, assesses no asset's condition, and runs no model.
Every entity shape in this module carries metadata and opaque
caller-supplied references only, plus figures and outcomes
stored exactly as reported by the external systems and people
who actually did the work. Methods accept only their named
parameters, so a caller cannot smuggle an unlisted field into
a record (pinned by tests: an unexpected keyword raises
``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records over the group's OWN records (core
records and extension records), plus deterministic derivations
at read:

- Commissioning is plan, checklist-item, reported-outcome, and
  turnover-package records over core projects. Systems are
  verified by others (``commissioned_here`` is False); the
  records track the work, and plan-level counts are derived at
  read.
- Cost estimating is estimate records over core projects:
  line items hold a recorded quantity and a recorded unit
  price; line totals and the estimate total are derived
  deterministically at read (integer cents, exact). The
  benchmark cost DATA behind vendor engines is held as a
  source reference only (``data_held_here`` is False); no cost
  database is fabricated.
- AI technical document review is review-request records over
  core documents plus result records holding an opaque result
  reference and reported labels only (``reviewed_here`` /
  ``checked_here`` / ``answered_here`` are False). No
  extracted text exists; a cited question-answering answer is
  held as a reference to an answer recorded elsewhere, never
  as answer text.
- Document control depth is control and approval records over
  core documents: the core registry already holds metadata
  and checksums only, never content, and this surface adds
  control profiles and reported approval decisions, with the
  current approval label and version count derived at read.
- GIS / spatial is layer records (metadata plus an opaque
  geometry reference — no geometry content exists) and
  reported asset-location records holding reported position
  labels verbatim (``tracked_here`` is False).
- Permitting is permit, license, and right-of-way records
  whose reported state labels are appended as records; the
  current state is derived at read by the seam
  :func:`_current_permit_state` (latest recorded label wins).
  The authority issues (``issued_here`` is False); the records
  track.
- Asset management is asset records in the set's own records
  form, reported condition-assessment records (condition
  labels verbatim — nothing is assessed here), and lifecycle
  capital-plan records held as data; counts are derived at
  read in the summary view.
- Prevailing wage follows the founding group's adjudicated
  form exactly: rate tables are held as data; wage lines hold
  recorded inputs only (rate-table reference, worker
  reference, integer minutes); base, fringe, and gross amounts
  are computed deterministically at read by the seam
  :func:`_compute_wage_amounts` using exact rational
  arithmetic (:class:`fractions.Fraction`), never stored.
  Certified-payroll report records reference wage lines; the
  report's totals exist only in its read view. E-filing ships
  as a labeled reference record (``filed_here`` is False).
  In this set the prevailing-wage family is claimed in name
  only (see ``UNION-SPEC.md``); the build is the
  records/arithmetic surface, and it claims no substance for
  any fork.
- Workflow automation ships as a labeled reference
  implementation: definitions held as data plus reported
  outcome records. Every record carries ``reference_stub:
  True``; the registry never executes (``executed_here`` is
  False, pinned).

Doctrines carried from the core: derived-never-stored for
every computed value (estimate totals, approval currency,
permit state, wage amounts, certified-payroll totals, summary
counts); money is integer cents, with booleans and floats
rejected at the boundary; append-only audit on the core
store's log with ``ext_``-prefixed actions for every
successful mutation, and denied write attempts recorded with
a ``:denied`` suffix; RBAC via :mod:`construct.access` with
the core's existing actions, enforced before any state change
or id allocation, so a failed operation consumes no id and
changes nothing.
"""

import copy
import threading
from datetime import datetime, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CHECKLIST_ITEM_KINDS = (
    "installation_checklist",
    "functional_performance_test",
    "issue_observation",
)
CHECKLIST_OUTCOME_LABELS = (
    "reported_passed",
    "reported_failed",
    "reported_open",
    "reported_resolved",
)
REVIEW_KINDS = (
    "submittal_review",
    "ufgs_check",
    "design_review",
    "cited_question_answering",
)
REVIEW_OUTCOME_LABELS = (
    "reported_compliant",
    "reported_noncompliant",
    "reported_comments",
    "reported_answered",
)
APPROVAL_DECISION_LABELS = (
    "reported_approved",
    "reported_approved_as_noted",
    "reported_revise_resubmit",
    "reported_rejected",
)
PERMIT_KINDS = (
    "permit",
    "license",
    "right_of_way",
)
PERMIT_STATE_LABELS = (
    "reported_submitted",
    "reported_under_review",
    "reported_issued",
    "reported_denied",
    "reported_expired",
    "reported_revoked",
)
CONDITION_LABELS = (
    "reported_good",
    "reported_fair",
    "reported_poor",
    "reported_critical",
)
WORKFLOW_OUTCOME_LABELS = (
    "reported_completed",
    "reported_failed",
    "reported_cancelled",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _optional_text(value, what):
    if value is None:
        return None
    return _non_empty(value, what)


def _money(value, what):
    """The house money rule: integer cents (not bool) >= 0."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if value < 0:
        raise ValidationError("%s must be >= 0" % (what,))
    return value


def _positive_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _rate_cents(value, what, allow_zero):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if allow_zero:
        if value < 0:
            raise ValidationError("%s must be >= 0" % (what,))
    elif value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _compute_wage_amounts(base_rate_cents_per_hour, fringe_rate_cents_per_hour,
                          minutes):
    """Prevailing-wage derivation seam: the single point where
    wage amounts are computed.

    Given a recorded base rate and fringe rate (integer cents
    per hour) and recorded integer minutes, return
    ``(base_cents, fringe_cents, gross_cents)`` as exact
    :class:`~fractions.Fraction` values: ``rate * minutes /
    60``, with the gross the exact sum. Nothing is rounded and
    nothing is stored — views render an exact Fraction as an
    ``int`` when it is whole, else as a ``"num/den"`` string.
    """
    base = Fraction(base_rate_cents_per_hour * minutes, 60)
    fringe = Fraction(fringe_rate_cents_per_hour * minutes, 60)
    return base, fringe, base + fringe


def _cents_out(amount):
    """Render an exact Fraction of cents for a view: an int when
    whole, else the exact ``"numerator/denominator"`` string."""
    if amount.denominator == 1:
        return amount.numerator
    return "%d/%d" % (amount.numerator, amount.denominator)


def _current_permit_state(states):
    """Permit-state derivation seam: a permit's current state
    is its latest recorded reported-state label, or
    ``"recorded"`` when no state has been recorded yet.

    State records are append-only and kept in recording order;
    the current state is derived at read from them and is never
    stored on the permit record. This is the batch's fresh
    negative control target: reading the earliest label instead
    would resurrect superseded states (see tests/README.md).
    """
    if not states:
        return "recorded"
    return states[-1]["state_label"]


class ConstructExtensions:
    """Extension surface wrapping one :class:`ConstructStore`."""

    def __init__(self, store):
        self.store = store
        self._cx_plans = {}
        self._cx_items = {}
        self._cx_outcomes = {}
        self._cx_turnovers = {}
        self._estimates = {}
        self._estimate_lines = {}
        self._reviews = {}
        self._review_results = {}
        self._doc_controls = {}
        self._doc_approvals = {}
        self._gis_layers = {}
        self._locations = {}
        self._permits = {}
        self._permit_states = {}
        self._assets = {}
        self._assessments = {}
        self._capital_plans = {}
        self._rate_tables = {}
        self._wage_lines = {}
        self._payroll_reports = {}
        self._efilings = {}
        self._workflow_definitions = {}
        self._workflow_outcomes = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`construct.access.require`; a plain string
        carries identity but no role). A denied attempt is
        recorded on the audit log with a ``:denied`` suffix
        before the error propagates; a missing actor is denied
        outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- commissioning (entry: Construction commissioning engine) -------

    def create_commissioning_plan(self, actor, project_id, title,
                                  system_label=None):
        """Record a commissioning plan against a core project.
        Action: record_write. The plan holds checklist items and
        reported outcomes; systems are verified by others —
        nothing here commissions anything."""
        self._guard(actor, "record_write", "ext_cx_plan_create")
        _non_empty(title, "plan title")
        _optional_text(system_label, "system_label")
        self.store.get_project(project_id, actor)
        with self._lock:
            plan = {
                "id": self._next_id("cxp-"),
                "project_id": project_id,
                "title": title,
                "system_label": system_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cx_plans[plan["id"]] = plan
        self._audit(actor, "ext_cx_plan_create", plan["id"],
                    {"project_id": project_id})
        return copy.deepcopy(plan)

    def add_checklist_item(self, actor, plan_id, kind, label):
        """Add a checklist item to a commissioning plan. Action:
        record_write. ``kind`` is one of the recorded item kinds
        (installation checklist, functional performance test,
        issue & observation); the item is a record — no test is
        performed and no issue is determined here."""
        self._guard(actor, "record_write", "ext_cx_item_create")
        if kind not in CHECKLIST_ITEM_KINDS:
            raise ValidationError("unknown checklist item kind: %r" % (kind,))
        _non_empty(label, "item label")
        with self._lock:
            self._get(self._cx_plans, plan_id, "commissioning plan")
            item = {
                "id": self._next_id("cxi-"),
                "plan_id": plan_id,
                "kind": kind,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cx_items[item["id"]] = item
        self._audit(actor, "ext_cx_item_create", item["id"],
                    {"plan_id": plan_id})
        return copy.deepcopy(item)

    def record_checklist_outcome(self, actor, item_id, outcome_label,
                                 reported_by_ref=None):
        """Record a checklist outcome exactly as reported.
        Action: record_write. The label is stored verbatim;
        ``commissioned_here`` is False — the verification was
        performed by whoever reported it, not by this build."""
        self._guard(actor, "record_write", "ext_cx_outcome_create")
        if outcome_label not in CHECKLIST_OUTCOME_LABELS:
            raise ValidationError(
                "unknown checklist outcome label: %r" % (outcome_label,))
        _optional_text(reported_by_ref, "reported_by_ref")
        with self._lock:
            self._get(self._cx_items, item_id, "checklist item")
            outcome = {
                "id": self._next_id("cxo-"),
                "item_id": item_id,
                "outcome_label": outcome_label,
                "reported_by_ref": reported_by_ref,
                "commissioned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cx_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_cx_outcome_create", outcome["id"],
                    {"item_id": item_id})
        return copy.deepcopy(outcome)

    def record_turnover_package(self, actor, plan_id, package_ref,
                                document_ids=()):
        """Record a turnover package for a commissioning plan.
        Action: record_write. The package is held as an opaque
        reference plus the core document ids it assembles —
        assembly happens in the commissioning platform
        (``assembled_here`` is False); each named document must
        exist in the core registry."""
        self._guard(actor, "record_write", "ext_cx_turnover_create")
        _non_empty(package_ref, "package_ref")
        if not isinstance(document_ids, (list, tuple)):
            raise ValidationError("document_ids must be a list")
        document_ids = list(document_ids)
        with self._lock:
            self._get(self._cx_plans, plan_id, "commissioning plan")
            for document_id in document_ids:
                self.store.get_document(document_id, actor)
            package = {
                "id": self._next_id("cxt-"),
                "plan_id": plan_id,
                "package_ref": package_ref,
                "document_ids": document_ids,
                "assembled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cx_turnovers[package["id"]] = package
        self._audit(actor, "ext_cx_turnover_create", package["id"],
                    {"plan_id": plan_id})
        return copy.deepcopy(package)

    def get_commissioning_plan(self, actor, plan_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._cx_plans, plan_id,
                                       "commissioning plan"))

    def list_commissioning_plans(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(p) for p in self._cx_plans.values()
            if project_id is None or p["project_id"] == project_id
        ]

    def list_checklist_items(self, actor, plan_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(i) for i in self._cx_items.values()
            if plan_id is None or i["plan_id"] == plan_id
        ]

    def list_checklist_outcomes(self, actor, item_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(o) for o in self._cx_outcomes.values()
            if item_id is None or o["item_id"] == item_id
        ]

    def list_turnover_packages(self, actor, plan_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(p) for p in self._cx_turnovers.values()
            if plan_id is None or p["plan_id"] == plan_id
        ]

    def commissioning_plan_view(self, actor, plan_id):
        """The plan plus derived counts at read: checklist items
        by kind, outcomes by label, and the turnover package
        count. Nothing here is stored."""
        self._maybe_require(actor, "record_read")
        plan = self._get(self._cx_plans, plan_id, "commissioning plan")
        items = self.list_checklist_items(actor, plan_id)
        item_ids = {i["id"] for i in items}
        outcomes = [o for o in self._cx_outcomes.values()
                    if o["item_id"] in item_ids]
        by_kind = {}
        for item in items:
            by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
        by_label = {}
        for outcome in outcomes:
            by_label[outcome["outcome_label"]] = \
                by_label.get(outcome["outcome_label"], 0) + 1
        view = copy.deepcopy(plan)
        view["items"] = items
        view["item_count"] = len(items)
        view["items_by_kind"] = by_kind
        view["outcome_count"] = len(outcomes)
        view["outcomes_by_label"] = by_label
        view["turnover_count"] = len(
            self.list_turnover_packages(actor, plan_id))
        return view

    # -- cost estimating (entry: Cost estimating engines & benchmark
    #    cost data) -------------------------------------------------------

    def create_estimate(self, actor, project_id, title,
                        cost_data_source_ref=None):
        """Record an estimate against a core project. Action:
        cost_write. The estimate holds line items (recorded
        quantities and unit prices); its totals are derived at
        read in :meth:`estimate_view`. The benchmark cost DATA
        behind vendor engines is held as a source reference
        only — ``data_held_here`` is False and no cost database
        exists here."""
        self._guard(actor, "cost_write", "ext_estimate_create")
        _non_empty(title, "estimate title")
        _optional_text(cost_data_source_ref, "cost_data_source_ref")
        self.store.get_project(project_id, actor)
        with self._lock:
            estimate = {
                "id": self._next_id("est-"),
                "project_id": project_id,
                "title": title,
                "cost_data_source_ref": cost_data_source_ref,
                "data_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._estimates[estimate["id"]] = estimate
        self._audit(actor, "ext_estimate_create", estimate["id"],
                    {"project_id": project_id})
        return copy.deepcopy(estimate)

    def add_estimate_line(self, actor, estimate_id, description,
                          quantity, unit_price_cents):
        """Add a line item to an estimate. Action: cost_write.
        The line holds a recorded quantity and a recorded unit
        price (integer cents, house money rule); its line total
        is derived at read and never stored — the stored line
        carries no total key."""
        self._guard(actor, "cost_write", "ext_estimate_line_create")
        _non_empty(description, "line description")
        _positive_int(quantity, "quantity")
        _money(unit_price_cents, "unit_price_cents")
        with self._lock:
            self._get(self._estimates, estimate_id, "estimate")
            line = {
                "id": self._next_id("estl-"),
                "estimate_id": estimate_id,
                "description": description,
                "quantity": quantity,
                "unit_price_cents": unit_price_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._estimate_lines[line["id"]] = line
        self._audit(actor, "ext_estimate_line_create", line["id"],
                    {"estimate_id": estimate_id})
        return copy.deepcopy(line)

    def get_estimate(self, actor, estimate_id):
        """The stored estimate record — it carries no total key;
        totals exist only in :meth:`estimate_view`."""
        self._maybe_require(actor, "cost_read")
        return copy.deepcopy(self._get(self._estimates, estimate_id,
                                       "estimate"))

    def list_estimates(self, actor, project_id=None):
        self._maybe_require(actor, "cost_read")
        return [
            copy.deepcopy(e) for e in self._estimates.values()
            if project_id is None or e["project_id"] == project_id
        ]

    def list_estimate_lines(self, actor, estimate_id=None):
        self._maybe_require(actor, "cost_read")
        return [
            copy.deepcopy(line) for line in self._estimate_lines.values()
            if estimate_id is None or line["estimate_id"] == estimate_id
        ]

    def estimate_view(self, actor, estimate_id):
        """The estimate record plus its lines, each with its line
        total derived at read (quantity x unit price, integer
        cents, exact), and the estimate total derived as their
        sum. Nothing here is stored."""
        self._maybe_require(actor, "cost_read")
        estimate = self._get(self._estimates, estimate_id, "estimate")
        lines = []
        total = 0
        for line in self.list_estimate_lines(actor, estimate_id):
            line_total = line["quantity"] * line["unit_price_cents"]
            total += line_total
            rendered = dict(line)
            rendered["line_total_cents"] = line_total
            lines.append(rendered)
        view = copy.deepcopy(estimate)
        view["lines"] = lines
        view["line_count"] = len(lines)
        view["total_cents"] = total
        return view

    # -- AI technical document review (entry: AI technical document
    #    review, UFGS checking & cited question-answering) -----------------

    def create_review_request(self, actor, document_id, kind,
                              model_label=None, question_ref=None):
        """Record an AI document-review request against a core
        document. Action: document_write. ``kind`` is one of
        the recorded review kinds (submittal review, UFGS check,
        design review, cited question-answering). The request is
        a record — no review runs here (``reviewed_here`` is
        False). For cited question-answering the question is
        held as an opaque ``question_ref``; no question text and
        no answer text field exists on any record in this
        surface."""
        self._guard(actor, "document_write", "ext_review_create")
        if kind not in REVIEW_KINDS:
            raise ValidationError("unknown review kind: %r" % (kind,))
        _optional_text(model_label, "model_label")
        _optional_text(question_ref, "question_ref")
        self.store.get_document(document_id, actor)
        with self._lock:
            request = {
                "id": self._next_id("air-"),
                "document_id": document_id,
                "kind": kind,
                "model_label": model_label,
                "question_ref": question_ref,
                "reviewed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reviews[request["id"]] = request
        self._audit(actor, "ext_review_create", request["id"],
                    {"document_id": document_id, "kind": kind})
        return copy.deepcopy(request)

    def record_review_result(self, actor, request_id, outcome_label,
                             result_ref, answer_ref=None):
        """Record a review result exactly as the reviewing
        system reported it. Action: document_write. The outcome
        label is stored verbatim and the result is held as an
        opaque reference only — ``reviewed_here`` /
        ``checked_here`` / ``answered_here`` are False, no
        extracted-text field exists, and a cited answer is held
        as ``answer_ref``, a reference to an answer recorded
        elsewhere, never as answer text."""
        self._guard(actor, "document_write", "ext_review_result_create")
        if outcome_label not in REVIEW_OUTCOME_LABELS:
            raise ValidationError(
                "unknown review outcome label: %r" % (outcome_label,))
        _non_empty(result_ref, "result_ref")
        _optional_text(answer_ref, "answer_ref")
        with self._lock:
            self._get(self._reviews, request_id, "review request")
            result = {
                "id": self._next_id("aio-"),
                "request_id": request_id,
                "outcome_label": outcome_label,
                "result_ref": result_ref,
                "answer_ref": answer_ref,
                "reviewed_here": False,
                "checked_here": False,
                "answered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._review_results[result["id"]] = result
        self._audit(actor, "ext_review_result_create", result["id"],
                    {"request_id": request_id})
        return copy.deepcopy(result)

    def get_review_request(self, actor, request_id):
        self._maybe_require(actor, "document_read")
        return copy.deepcopy(self._get(self._reviews, request_id,
                                       "review request"))

    def list_review_requests(self, actor, document_id=None):
        self._maybe_require(actor, "document_read")
        return [
            copy.deepcopy(r) for r in self._reviews.values()
            if document_id is None or r["document_id"] == document_id
        ]

    def list_review_results(self, actor, request_id=None):
        self._maybe_require(actor, "document_read")
        return [
            copy.deepcopy(r) for r in self._review_results.values()
            if request_id is None or r["request_id"] == request_id
        ]

    # -- document control depth (entry: Document control platform
    #    depth) -------------------------------------------------------------

    def register_document_control(self, actor, document_id,
                                  control_label, register_ref=None):
        """Register a core document under document control.
        Action: document_write. The core registry holds the
        document's metadata and version checksums only, never
        content; this record adds the control profile (a label
        and an optional register reference) the tracking engine
        behind the registry would carry. ``content_held_here``
        is False."""
        self._guard(actor, "document_write", "ext_doc_control_create")
        _non_empty(control_label, "control_label")
        _optional_text(register_ref, "register_ref")
        self.store.get_document(document_id, actor)
        with self._lock:
            if any(c["document_id"] == document_id
                   for c in self._doc_controls.values()):
                raise ValidationError(
                    "document %s is already under document control"
                    % (document_id,))
            control = {
                "id": self._next_id("dct-"),
                "document_id": document_id,
                "control_label": control_label,
                "register_ref": register_ref,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._doc_controls[control["id"]] = control
        self._audit(actor, "ext_doc_control_create", control["id"],
                    {"document_id": document_id})
        return copy.deepcopy(control)

    def record_document_approval(self, actor, control_id, decision_label,
                                 version_number=None,
                                 reported_by_ref=None):
        """Record an approval decision against a controlled
        document exactly as reported. Action: document_write.
        The decision label is stored verbatim; the current
        approval state is derived at read in
        :meth:`document_control_view` (the latest recorded
        decision) and never stored. ``approved_here`` is False —
        the decision was made by whoever reported it."""
        self._guard(actor, "document_write", "ext_doc_approval_create")
        if decision_label not in APPROVAL_DECISION_LABELS:
            raise ValidationError(
                "unknown approval decision label: %r" % (decision_label,))
        if version_number is not None:
            _positive_int(version_number, "version_number")
        _optional_text(reported_by_ref, "reported_by_ref")
        with self._lock:
            self._get(self._doc_controls, control_id, "document control")
            approval = {
                "id": self._next_id("dap-"),
                "control_id": control_id,
                "decision_label": decision_label,
                "version_number": version_number,
                "reported_by_ref": reported_by_ref,
                "approved_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._doc_approvals[approval["id"]] = approval
        self._audit(actor, "ext_doc_approval_create", approval["id"],
                    {"control_id": control_id})
        return copy.deepcopy(approval)

    def get_document_control(self, actor, control_id):
        """The stored control record — it carries no approval
        state; currency exists only in
        :meth:`document_control_view`."""
        self._maybe_require(actor, "document_read")
        return copy.deepcopy(self._get(self._doc_controls, control_id,
                                       "document control"))

    def list_document_controls(self, actor, document_id=None):
        self._maybe_require(actor, "document_read")
        return [
            copy.deepcopy(c) for c in self._doc_controls.values()
            if document_id is None or c["document_id"] == document_id
        ]

    def list_document_approvals(self, actor, control_id=None):
        self._maybe_require(actor, "document_read")
        return [
            copy.deepcopy(a) for a in self._doc_approvals.values()
            if control_id is None or a["control_id"] == control_id
        ]

    def document_control_view(self, actor, control_id):
        """The control record, the core document read from the
        core at read time (with its version history), the
        recorded approval decisions in order, and the current
        approval label derived at read as the latest recorded
        decision (``"recorded"`` when none). Nothing here is
        stored."""
        self._maybe_require(actor, "document_read")
        control = self._get(self._doc_controls, control_id,
                            "document control")
        approvals = self.list_document_approvals(actor, control_id)
        view = copy.deepcopy(control)
        view["document"] = self.store.get_document(
            control["document_id"], actor)
        view["approvals"] = approvals
        view["approval_count"] = len(approvals)
        view["current_approval_label"] = (
            approvals[-1]["decision_label"] if approvals else "recorded")
        return view

    # -- GIS / spatial (entry: GIS/spatial platform & asset location
    #    tracking) ----------------------------------------------------------

    def create_gis_layer(self, actor, project_id, label,
                         geometry_ref=None, source_ref=None):
        """Record a GIS layer for a core project, as metadata.
        Action: record_write. The layer's geometry is held as an
        opaque ``geometry_ref`` only — no geometry content field
        exists on this surface — and its source as an opaque
        ``source_ref``."""
        self._guard(actor, "record_write", "ext_gis_layer_create")
        _non_empty(label, "layer label")
        _optional_text(geometry_ref, "geometry_ref")
        _optional_text(source_ref, "source_ref")
        self.store.get_project(project_id, actor)
        with self._lock:
            layer = {
                "id": self._next_id("gis-"),
                "project_id": project_id,
                "label": label,
                "geometry_ref": geometry_ref,
                "source_ref": source_ref,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gis_layers[layer["id"]] = layer
        self._audit(actor, "ext_gis_layer_create", layer["id"],
                    {"project_id": project_id})
        return copy.deepcopy(layer)

    def record_asset_location(self, actor, asset_ref,
                              reported_position_label, layer_id=None,
                              project_id=None, reported_at=None):
        """Record an asset's reported location. Action:
        record_write. The reported position label is stored
        verbatim as the field system reported it — positions are
        caller-reported data, never sensed (``tracked_here`` is
        False), and each record is standalone: no continuous
        tracking state exists. ``asset_ref`` is an opaque
        reference (it may name an extension asset record)."""
        self._guard(actor, "record_write", "ext_location_create")
        _non_empty(asset_ref, "asset_ref")
        _non_empty(reported_position_label, "reported_position_label")
        _optional_text(reported_at, "reported_at")
        if project_id is not None:
            self.store.get_project(project_id, actor)
        with self._lock:
            if layer_id is not None:
                layer = self._get(self._gis_layers, layer_id, "GIS layer")
                if project_id is not None \
                        and layer["project_id"] != project_id:
                    raise ValidationError(
                        "layer %s does not belong to project %s"
                        % (layer_id, project_id))
            record = {
                "id": self._next_id("loc-"),
                "asset_ref": asset_ref,
                "layer_id": layer_id,
                "project_id": project_id,
                "reported_position_label": reported_position_label,
                "reported_at": reported_at,
                "tracked_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._locations[record["id"]] = record
        self._audit(actor, "ext_location_create", record["id"],
                    {"asset_ref": asset_ref})
        return copy.deepcopy(record)

    def get_gis_layer(self, actor, layer_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._gis_layers, layer_id,
                                       "GIS layer"))

    def list_gis_layers(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(layer) for layer in self._gis_layers.values()
            if project_id is None or layer["project_id"] == project_id
        ]

    def list_asset_locations(self, actor, asset_ref=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(r) for r in self._locations.values()
            if asset_ref is None or r["asset_ref"] == asset_ref
        ]

    # -- permitting (entry: Permitting, licensing & right-of-way
    #    management) ---------------------------------------------------------

    def create_permit(self, actor, project_id, kind, title,
                      authority_label=None, application_ref=None):
        """Record a permit, license, or right-of-way against a
        core project. Action: record_write. The stored record
        carries no state key — its current state is derived at
        read in :meth:`permit_view` from the append-only
        reported state records by :func:`_current_permit_state`.
        The authority issues (``issued_here`` is False); this
        build tracks."""
        self._guard(actor, "record_write", "ext_permit_create")
        if kind not in PERMIT_KINDS:
            raise ValidationError("unknown permit kind: %r" % (kind,))
        _non_empty(title, "permit title")
        _optional_text(authority_label, "authority_label")
        _optional_text(application_ref, "application_ref")
        self.store.get_project(project_id, actor)
        with self._lock:
            permit = {
                "id": self._next_id("prm-"),
                "project_id": project_id,
                "kind": kind,
                "title": title,
                "authority_label": authority_label,
                "application_ref": application_ref,
                "issued_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._permits[permit["id"]] = permit
        self._audit(actor, "ext_permit_create", permit["id"],
                    {"project_id": project_id, "kind": kind})
        return copy.deepcopy(permit)

    def record_permit_state(self, actor, permit_id, state_label,
                            reported_at=None):
        """Append a reported state for a permit. Action:
        record_write. The label is stored verbatim in recording
        order; the permit's current state is derived from these
        records at read, never stored on the permit."""
        self._guard(actor, "record_write", "ext_permit_state_create")
        if state_label not in PERMIT_STATE_LABELS:
            raise ValidationError(
                "unknown permit state label: %r" % (state_label,))
        _optional_text(reported_at, "reported_at")
        with self._lock:
            self._get(self._permits, permit_id, "permit")
            state = {
                "id": self._next_id("prs-"),
                "permit_id": permit_id,
                "state_label": state_label,
                "reported_at": reported_at,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._permit_states[state["id"]] = state
        self._audit(actor, "ext_permit_state_create", state["id"],
                    {"permit_id": permit_id})
        return copy.deepcopy(state)

    def get_permit(self, actor, permit_id):
        """The stored permit record — it carries no state key;
        the current state exists only in :meth:`permit_view`."""
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._permits, permit_id,
                                       "permit"))

    def list_permits(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(p) for p in self._permits.values()
            if project_id is None or p["project_id"] == project_id
        ]

    def list_permit_states(self, actor, permit_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(s) for s in self._permit_states.values()
            if permit_id is None or s["permit_id"] == permit_id
        ]

    def permit_view(self, actor, permit_id):
        """The permit record plus its reported states in
        recording order, and ``current_state`` derived at read
        by :func:`_current_permit_state` — the latest recorded
        label, or ``"recorded"`` when no state has been
        recorded. Nothing here is stored."""
        self._maybe_require(actor, "record_read")
        permit = self._get(self._permits, permit_id, "permit")
        states = self.list_permit_states(actor, permit_id)
        view = copy.deepcopy(permit)
        view["states"] = states
        view["state_count"] = len(states)
        view["current_state"] = _current_permit_state(states)
        return view

    # -- asset management (entry: Asset management platform) ------------------

    def register_asset(self, actor, asset_ref, kind_label,
                       project_id=None, org_id=None, location_label=None):
        """Register an asset record in the set's own records
        form. Action: record_write. ``asset_ref`` is an opaque
        caller-supplied reference, unique in this registry (the
        platform's registers key on it); the record holds
        labels and references only."""
        self._guard(actor, "record_write", "ext_asset_create")
        _non_empty(asset_ref, "asset_ref")
        _non_empty(kind_label, "kind_label")
        _optional_text(location_label, "location_label")
        if project_id is not None:
            self.store.get_project(project_id, actor)
        if org_id is not None:
            self.store.get_org(org_id, actor)
        with self._lock:
            if any(a["asset_ref"] == asset_ref
                   for a in self._assets.values()):
                raise ValidationError(
                    "asset_ref already registered: %r" % (asset_ref,))
            asset = {
                "id": self._next_id("ast-"),
                "asset_ref": asset_ref,
                "kind_label": kind_label,
                "project_id": project_id,
                "org_id": org_id,
                "location_label": location_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assets[asset["id"]] = asset
        self._audit(actor, "ext_asset_create", asset["id"],
                    {"asset_ref": asset_ref})
        return copy.deepcopy(asset)

    def record_condition_assessment(self, actor, asset_id, condition_label,
                                    assessed_by_ref=None, reported_at=None):
        """Record a condition assessment against a registered
        asset exactly as reported. Action: record_write. The
        condition label is a REPORTED label stored verbatim —
        nothing is assessed here (``assessed_here`` is False)."""
        self._guard(actor, "record_write", "ext_assessment_create")
        if condition_label not in CONDITION_LABELS:
            raise ValidationError(
                "unknown condition label: %r" % (condition_label,))
        _optional_text(assessed_by_ref, "assessed_by_ref")
        _optional_text(reported_at, "reported_at")
        with self._lock:
            self._get(self._assets, asset_id, "asset")
            assessment = {
                "id": self._next_id("asc-"),
                "asset_id": asset_id,
                "condition_label": condition_label,
                "assessed_by_ref": assessed_by_ref,
                "reported_at": reported_at,
                "assessed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessments[assessment["id"]] = assessment
        self._audit(actor, "ext_assessment_create", assessment["id"],
                    {"asset_id": asset_id})
        return copy.deepcopy(assessment)

    def create_capital_plan(self, actor, asset_id, action_label,
                            planned_period_label, estimate_ref=None):
        """Record a lifecycle capital-plan entry for an asset,
        held as data. Action: record_write. The plan names a
        planned action and period as labels and may reference
        an estimate; nothing is funded, scheduled, or executed
        here (``executed_here`` is False)."""
        self._guard(actor, "record_write", "ext_capital_plan_create")
        _non_empty(action_label, "action_label")
        _non_empty(planned_period_label, "planned_period_label")
        _optional_text(estimate_ref, "estimate_ref")
        with self._lock:
            self._get(self._assets, asset_id, "asset")
            plan = {
                "id": self._next_id("cap-"),
                "asset_id": asset_id,
                "action_label": action_label,
                "planned_period_label": planned_period_label,
                "estimate_ref": estimate_ref,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._capital_plans[plan["id"]] = plan
        self._audit(actor, "ext_capital_plan_create", plan["id"],
                    {"asset_id": asset_id})
        return copy.deepcopy(plan)

    def get_asset(self, actor, asset_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._assets, asset_id, "asset"))

    def list_assets(self, actor, project_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(a) for a in self._assets.values()
            if project_id is None or a["project_id"] == project_id
        ]

    def list_condition_assessments(self, actor, asset_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(a) for a in self._assessments.values()
            if asset_id is None or a["asset_id"] == asset_id
        ]

    def list_capital_plans(self, actor, asset_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(p) for p in self._capital_plans.values()
            if asset_id is None or p["asset_id"] == asset_id
        ]

    def asset_summary(self, actor, project_id=None):
        """Derived counts at read over the asset registry:
        assets by kind label, assessments by reported condition
        label, and the capital-plan count. Counts only — no
        condition is computed and no score exists. Nothing here
        is stored."""
        self._maybe_require(actor, "record_read")
        assets = self.list_assets(actor, project_id)
        asset_ids = {a["id"] for a in assets}
        by_kind = {}
        for asset in assets:
            by_kind[asset["kind_label"]] = \
                by_kind.get(asset["kind_label"], 0) + 1
        by_condition = {}
        assessment_count = 0
        for assessment in self._assessments.values():
            if assessment["asset_id"] in asset_ids:
                assessment_count += 1
                by_condition[assessment["condition_label"]] = \
                    by_condition.get(assessment["condition_label"], 0) + 1
        plan_count = sum(
            1 for p in self._capital_plans.values()
            if p["asset_id"] in asset_ids)
        return {
            "project_id": project_id,
            "asset_count": len(assets),
            "assets_by_kind": by_kind,
            "assessment_count": assessment_count,
            "assessments_by_condition": by_condition,
            "capital_plan_count": plan_count,
        }

    # -- prevailing wage (entry: Prevailing-wage determination depth) ---------

    def create_rate_table(self, actor, jurisdiction_label, trade_label,
                          base_rate_cents_per_hour,
                          fringe_rate_cents_per_hour,
                          effective_label=None):
        """Record a prevailing-wage rate table as data. Action:
        workforce_write. Rates are integer cents per hour (base
        positive, fringe may be zero); the table determines
        nothing by itself — amounts are computed at read from a
        wage line's recorded minutes by
        :func:`_compute_wage_amounts`."""
        self._guard(actor, "workforce_write", "ext_rate_table_create")
        _non_empty(jurisdiction_label, "jurisdiction_label")
        _non_empty(trade_label, "trade_label")
        _rate_cents(base_rate_cents_per_hour, "base_rate_cents_per_hour",
                    allow_zero=False)
        _rate_cents(fringe_rate_cents_per_hour, "fringe_rate_cents_per_hour",
                    allow_zero=True)
        _optional_text(effective_label, "effective_label")
        with self._lock:
            table = {
                "id": self._next_id("rate-"),
                "jurisdiction_label": jurisdiction_label,
                "trade_label": trade_label,
                "base_rate_cents_per_hour": base_rate_cents_per_hour,
                "fringe_rate_cents_per_hour": fringe_rate_cents_per_hour,
                "effective_label": effective_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rate_tables[table["id"]] = table
        self._audit(actor, "ext_rate_table_create", table["id"],
                    {"trade_label": trade_label})
        return copy.deepcopy(table)

    def record_wage_line(self, actor, project_id, org_id, worker_ref,
                         rate_table_id, minutes, period_label):
        """Record one wage line: recorded inputs only. Action:
        workforce_write. The line holds a rate-table reference,
        an opaque worker reference, and integer minutes — no
        amount is stored; base, fringe, and gross are derived
        at read in :meth:`wage_line_view`. The project and org
        must exist in the core."""
        self._guard(actor, "workforce_write", "ext_wage_line_create")
        _non_empty(worker_ref, "worker_ref")
        _non_empty(period_label, "period_label")
        _positive_int(minutes, "minutes")
        self.store.get_project(project_id, actor)
        self.store.get_org(org_id, actor)
        with self._lock:
            self._get(self._rate_tables, rate_table_id, "rate table")
            line = {
                "id": self._next_id("wage-"),
                "project_id": project_id,
                "org_id": org_id,
                "worker_ref": worker_ref,
                "rate_table_id": rate_table_id,
                "minutes": minutes,
                "period_label": period_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._wage_lines[line["id"]] = line
        self._audit(actor, "ext_wage_line_create", line["id"],
                    {"project_id": project_id, "org_id": org_id})
        return copy.deepcopy(line)

    def get_rate_table(self, actor, table_id):
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._rate_tables, table_id,
                                       "rate table"))

    def list_rate_tables(self, actor):
        self._maybe_require(actor, "workforce_read")
        return [copy.deepcopy(t) for t in self._rate_tables.values()]

    def get_wage_line(self, actor, line_id):
        """The stored wage line — it carries no amount key;
        amounts exist only in :meth:`wage_line_view`."""
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._wage_lines, line_id,
                                       "wage line"))

    def list_wage_lines(self, actor, project_id=None, org_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(line) for line in self._wage_lines.values()
            if (project_id is None or line["project_id"] == project_id)
            and (org_id is None or line["org_id"] == org_id)
        ]

    def wage_line_view(self, actor, line_id):
        """The wage line plus the amounts derived at read from
        its rate table and recorded minutes by
        :func:`_compute_wage_amounts`: ``base_cents``,
        ``fringe_cents``, and ``gross_cents``, each rendered
        exactly (an int when whole, else a ``"num/den"``
        string). Nothing here is stored."""
        self._maybe_require(actor, "workforce_read")
        line = self._get(self._wage_lines, line_id, "wage line")
        table = self._get(self._rate_tables, line["rate_table_id"],
                          "rate table")
        base, fringe, gross = _compute_wage_amounts(
            table["base_rate_cents_per_hour"],
            table["fringe_rate_cents_per_hour"],
            line["minutes"])
        view = copy.deepcopy(line)
        view["base_cents"] = _cents_out(base)
        view["fringe_cents"] = _cents_out(fringe)
        view["gross_cents"] = _cents_out(gross)
        return view

    def generate_certified_payroll_report(self, actor, project_id, org_id,
                                          period_label, line_ids):
        """Generate a certified-payroll report record over wage
        lines. Action: workforce_write. What is derived here is
        exactly this: the report record references the given
        wage lines (each must belong to the project and org),
        and its totals are derived at read in
        :meth:`certified_payroll_view` from the same wage seam
        — the stored report carries no totals. No core payroll
        record is created or changed."""
        self._guard(actor, "workforce_write", "ext_payroll_report_create")
        _non_empty(period_label, "period_label")
        if not isinstance(line_ids, (list, tuple)) or not line_ids:
            raise ValidationError("line_ids must be a non-empty list")
        line_ids = list(line_ids)
        if len(set(line_ids)) != len(line_ids):
            raise ValidationError("line_ids must not contain duplicates")
        self.store.get_project(project_id, actor)
        self.store.get_org(org_id, actor)
        with self._lock:
            for line_id in line_ids:
                line = self._get(self._wage_lines, line_id, "wage line")
                if line["project_id"] != project_id \
                        or line["org_id"] != org_id:
                    raise ValidationError(
                        "wage line %s does not belong to project %s / org %s"
                        % (line_id, project_id, org_id))
            report = {
                "id": self._next_id("cpr-"),
                "project_id": project_id,
                "org_id": org_id,
                "period_label": period_label,
                "line_ids": line_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payroll_reports[report["id"]] = report
        self._audit(actor, "ext_payroll_report_create", report["id"],
                    {"project_id": project_id, "org_id": org_id})
        return copy.deepcopy(report)

    def get_certified_payroll_report(self, actor, report_id):
        """The stored report record — it carries no totals;
        totals exist only in :meth:`certified_payroll_view`."""
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._payroll_reports, report_id,
                                       "certified payroll report"))

    def list_certified_payroll_reports(self, actor, project_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(r) for r in self._payroll_reports.values()
            if project_id is None or r["project_id"] == project_id
        ]

    def certified_payroll_view(self, actor, report_id):
        """The report record plus its totals derived at read:
        the exact sum over its wage lines of the seam's base,
        fringe, and gross amounts (each rendered exactly), the
        line count, and the distinct recorded worker references
        count. Nothing here is stored."""
        self._maybe_require(actor, "workforce_read")
        report = self._get(self._payroll_reports, report_id,
                           "certified payroll report")
        total_base = Fraction(0)
        total_fringe = Fraction(0)
        total_gross = Fraction(0)
        workers = set()
        for line_id in report["line_ids"]:
            line = self._wage_lines[line_id]
            table = self._rate_tables[line["rate_table_id"]]
            base, fringe, gross = _compute_wage_amounts(
                table["base_rate_cents_per_hour"],
                table["fringe_rate_cents_per_hour"],
                line["minutes"])
            total_base += base
            total_fringe += fringe
            total_gross += gross
            workers.add(line["worker_ref"])
        view = copy.deepcopy(report)
        view["line_count"] = len(report["line_ids"])
        view["worker_count"] = len(workers)
        view["total_base_cents"] = _cents_out(total_base)
        view["total_fringe_cents"] = _cents_out(total_fringe)
        view["total_gross_cents"] = _cents_out(total_gross)
        return view

    def record_efiling(self, actor, report_id, filing_ref):
        """Record an e-filing of a certified-payroll report, as
        a labeled reference implementation. Action:
        workforce_write. ``filed_here`` is False: filing happens
        on the receiving agency's system; what is recorded here
        is the filing reference exactly as reported."""
        self._guard(actor, "workforce_write", "ext_efiling_create")
        _non_empty(filing_ref, "filing_ref")
        with self._lock:
            self._get(self._payroll_reports, report_id,
                      "certified payroll report")
            filing = {
                "id": self._next_id("efl-"),
                "report_id": report_id,
                "filing_ref": filing_ref,
                "reference_stub": True,
                "filed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._efilings[filing["id"]] = filing
        self._audit(actor, "ext_efiling_create", filing["id"],
                    {"report_id": report_id})
        return copy.deepcopy(filing)

    def get_efiling(self, actor, filing_id):
        self._maybe_require(actor, "workforce_read")
        return copy.deepcopy(self._get(self._efilings, filing_id,
                                       "e-filing"))

    def list_efilings(self, actor, report_id=None):
        self._maybe_require(actor, "workforce_read")
        return [
            copy.deepcopy(f) for f in self._efilings.values()
            if report_id is None or f["report_id"] == report_id
        ]

    # -- workflow automation (entry: Workflow automation engines; stub) -------

    def create_workflow_definition(self, actor, label, steps):
        """Record a workflow definition as data, as a labeled
        reference implementation. Action: record_write.
        ``steps`` is an ordered list of step labels stored
        verbatim; the core's lifecycle state machines are the
        in-core seed this definition describes. The registry
        never executes a definition — ``executed_here`` is
        False and there is no run API."""
        self._guard(actor, "record_write", "ext_workflow_definition_create")
        _non_empty(label, "workflow label")
        if not isinstance(steps, (list, tuple)) or not steps:
            raise ValidationError("steps must be a non-empty list")
        steps = list(steps)
        for step in steps:
            _non_empty(step, "workflow step")
        with self._lock:
            definition = {
                "id": self._next_id("wfd-"),
                "label": label,
                "steps": steps,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_definitions[definition["id"]] = definition
        self._audit(actor, "ext_workflow_definition_create", definition["id"],
                    {"label": label})
        return copy.deepcopy(definition)

    def record_workflow_outcome(self, actor, definition_id, outcome_label):
        """Record a workflow outcome exactly as the executing
        system reported it. Action: record_write. The label is
        stored verbatim; ``executed_here`` is False — recording
        an outcome executes nothing and changes no definition
        and no core record."""
        self._guard(actor, "record_write", "ext_workflow_outcome_create")
        if outcome_label not in WORKFLOW_OUTCOME_LABELS:
            raise ValidationError(
                "unknown workflow outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._workflow_definitions, definition_id,
                      "workflow definition")
            outcome = {
                "id": self._next_id("wfo-"),
                "definition_id": definition_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_workflow_outcome_create", outcome["id"],
                    {"definition_id": definition_id})
        return copy.deepcopy(outcome)

    def get_workflow_definition(self, actor, definition_id):
        self._maybe_require(actor, "record_read")
        return copy.deepcopy(self._get(self._workflow_definitions,
                                       definition_id,
                                       "workflow definition"))

    def list_workflow_definitions(self, actor):
        self._maybe_require(actor, "record_read")
        return [copy.deepcopy(d)
                for d in self._workflow_definitions.values()]

    def list_workflow_outcomes(self, actor, definition_id=None):
        self._maybe_require(actor, "record_read")
        return [
            copy.deepcopy(o) for o in self._workflow_outcomes.values()
            if definition_id is None or o["definition_id"] == definition_id
        ]
