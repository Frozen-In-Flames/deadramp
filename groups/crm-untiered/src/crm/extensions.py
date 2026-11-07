"""Final GAPS batch extensions for the CRM untiered set build
(Untiered Set 23).

Clean-room, standard-library-only records extensions for the 4
open Extended entries this set's GAPS.md section carries: 2
drafted ``build-extension`` and 2 drafted ``stub-engine`` in
``../../gaps-batch/inventory.json`` (idx 943-946; idx 947,
platform layer, was closed ``re-scoped`` under
``../../PLATFORM-LAYER.md``). See ``BATCH.md`` in the group
directory for the per-entry disposition, including two
re-judgments recorded there under DECISION.md qualification 1:
both build-extension drafts close ``reference`` on a close
reading of this set's own spec, so all four entries ship as
labeled reference implementations.

Tier discipline: this set is untiered. The spec sheet records
``fedramp_impact_level: "Unknown"`` and ``cmmc_tier: null``; no
baseline is asserted and no CMMC equivalence is drawn, and this
module introduces none -- no record or derived view it produces
carries a tier, baseline, impact-level, or equivalence key (a
recursive scan in the batch tests pins that, alongside the
no-score scan).

Design, following the core's doctrines and the category's
adjudicated batch forms at the sibling tiers (``../crm-l2`` and
``../crm-l3`` batch units):

- This module is a wrapper around :class:`CrmStore`; the core
  modules are untouched (byte-identical). Core state (accounts,
  contacts, cases, guides, findings, modules) is read through the
  core store's public API, never re-implemented, and no extension
  operation writes core state. Existence checks against the core
  pass ``actor=None`` internally: the extension's own guard has
  already enforced the mapped action before the check runs.
- RBAC goes through :mod:`crm.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like
  actors, and records denied attempts on the core audit log with
  the extension action name suffixed ``:denied``. Plain-string
  actors carry identity but no role, mirroring the core
  convention. The mapping is:

  - proposal-generation requests / reports / evaluations ->
    ``case_write`` / ``case_read`` (the category's AI surface
    genus: case-adjacent operational records, as at both sibling
    tiers);
  - forecast requests / reports / figures -> ``case_write`` /
    ``case_read`` (external-engine request/report records of the
    same genus); the forecast summary -> ``report_read``;
  - document templates, automation requests and reports ->
    ``config_write`` / ``config_read`` (they bind configuration
    records; ``config_write`` is admin-only, as in the core --
    the same genus the sibling tiers gave design definitions and
    module-bound surfaces);
  - connector definitions, sync receipts and the connector
    catalog -> ``config_write`` / ``config_read`` (integration
    configuration genus, as at the founding tier);
  - the extension summary -> ``report_read``.

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If
  the audit write raises, the record insertion and its id roll
  back before the error propagates: no extension record exists
  whose audit entry does not.
- All references to people, systems, and domains are opaque
  ``*_ref`` strings, exactly as in the core. Where a record
  binds a person-bearing core object it names a core account or
  case by id; no record shape in this module can hold a real
  name, email, phone number, or any other identifier, and none
  can hold a document body, a generated text, a forecast, or a
  computed score.
- Derived values are derived at read and never stored: the
  connector catalog rollups, the forecast summary counts, the
  extension summary. Stored records carry no derived key; tests
  pin that.
- Nothing here executes against an external system. All four
  families ship as labeled reference implementations: every
  record they create carries ``reference_stub: True`` (connector
  records additionally carry ``reference_transport: True``), and
  no proposal is generated, no forecast is computed, no document
  is automated, and nothing is transmitted or synced. The
  grounds for closing the two drafted build-extensions in this
  form are in ``BATCH.md``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

AUTOMATION_REPORT_OUTCOMES = (
    "reported_completed",
    "reported_failed",
    "reported_noop",
)
KNOWN_AUTOMATION_REPORT_OUTCOMES = frozenset(AUTOMATION_REPORT_OUTCOMES)
CONNECTOR_DIRECTIONS = ("inbound", "outbound")
KNOWN_CONNECTOR_DIRECTIONS = frozenset(CONNECTOR_DIRECTIONS)
CONNECTOR_TARGET_KINDS = ("account", "case", "guide", "finding", "module")
KNOWN_CONNECTOR_TARGET_KINDS = frozenset(CONNECTOR_TARGET_KINDS)

# Keys that would make a record carry a computed score. The core
# forbids scores by design; the extension refuses them as parameter
# names and result labels alike (tests pin the refusal and scan
# every stored record for these keys).
SCORE_KEYS = frozenset({
    "score", "rating", "rank", "probability", "confidence",
    "likelihood", "propensity",
})


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _nonneg_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _reported_figure(value, what):
    """Validate a figure stored exactly as reported.

    A number stored exactly as supplied (integers only --
    booleans and floats are rejected, mirroring the house rule
    that recorded values are exact), or a verbatim label string.
    Nothing is computed from figures recorded this way.
    """
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValidationError(
            "%s must be an integer or a verbatim label string" % (what,))
    if isinstance(value, str) and not value.strip():
        raise ValidationError("%s must not be empty" % (what,))
    return value


def _validate_parameters(parameters, what="parameters"):
    """Validate a configuration-parameter mapping held as data.

    Keys are parameter names (non-empty strings, never
    score-shaped); values are strings, integers, or booleans --
    the scalar shapes a configuration record can state. Floats
    are rejected (house rule: recorded values are exact), as are
    nested structures: parameters are data, not a program.
    """
    if parameters is None:
        return None
    if not isinstance(parameters, dict):
        raise ValidationError("%s must be a dict" % (what,))
    for key, value in parameters.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "each key in %s must be a non-empty string" % (what,))
        if key.strip().lower() in SCORE_KEYS:
            raise ValidationError(
                "%s may not carry a score-shaped key: %r" % (what, key))
        if isinstance(value, bool) or isinstance(value, (str, int)):
            continue
        raise ValidationError(
            "each value in %s must be a string, integer, or boolean"
            % (what,))
    return copy.deepcopy(parameters)


def _check_outcome_label(outcome_label):
    """Reported outcome labels are stored verbatim -- except a
    score-shaped label, which is refused: reported outcomes are
    labels, and no scoring enters through this surface."""
    _non_empty(outcome_label, "outcome_label")
    if outcome_label.strip().lower() in SCORE_KEYS:
        raise ValidationError(
            "outcome_label may not be a score-shaped label: %r"
            % (outcome_label,))
    return outcome_label


class CrmExtensions:
    """GAPS-batch extension surface over a core CrmStore."""

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
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r"
                    % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
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
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed, mirroring the batch pattern: an
                # operation whose audit write fails does not proceed
                # -- the insertion and the id roll back before the
                # error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    # -- core existence checks (internal; see module docstring) -------

    def _core_account(self, account_id):
        return self.store.get_account(account_id)

    def _core_case(self, case_id):
        return self.store.get_case(case_id)

    def _check_case_account(self, case, account_id):
        """A case linked alongside an account must belong to it --
        the core's linkage discipline, applied to extension
        records that bind both."""
        if account_id is not None and case["account_id"] != account_id:
            raise ValidationError(
                "case %r does not belong to account %r"
                % (case["id"], account_id)
            )

    # ================================================================
    # AI proposal-generation engine (idx 943; reference form --
    # re-judged from the drafted build-extension, grounds in
    # BATCH.md. The category's adjudicated AI form: requests and
    # reported outcomes only; the signature refuses generated
    # content, no model runs, and no proposal text is ever held)
    # ================================================================

    def register_proposal_request(self, actor, model_ref, purpose,
                                  account_id=None, case_id=None):
        """Record a request to an external proposal-generation
        model. Action: case_write.

        Id prefix: prop-. Reference implementation: the request
        names the model by opaque ``model_ref``, states the
        caller's ``purpose``, and may bind an existing core
        account and/or case (a case bound alongside an account it
        does not belong to is refused, mirroring the core's
        linkage discipline). There is deliberately no prompt,
        draft, or content parameter -- generated text enters this
        build never; a generated proposal is reported only by
        opaque reference (``record_proposal_report``), and nothing
        is generated or inferred here (``inference_here: False``,
        ``generated_here: False``).
        """
        self._guard(actor, "case_write", "ext_proposal_request_register")
        _non_empty(model_ref, "model_ref")
        _non_empty(purpose, "purpose")
        with self._lock:
            if account_id is not None:
                self._core_account(account_id)
            if case_id is not None:
                case = self._core_case(case_id)
                self._check_case_account(case, account_id)
            return self._create(
                "proposal_request", "prop",
                {"model_ref": model_ref, "purpose": purpose,
                 "account_id": account_id, "case_id": case_id,
                 "reference_stub": True, "inference_here": False,
                 "generated_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_proposal_request_register")

    def record_proposal_report(self, actor, request_id, outcome_label,
                               proposal_ref=None):
        """Record a model's reported outcome for a proposal
        request. Action: case_write. Id prefix: proprep-.

        The outcome label is stored verbatim as the model's
        operator reported it; the generated proposal itself is
        named only by an opaque ``proposal_ref`` and is never
        held here (``proposal_held_here: False``,
        ``generated_here: False``). A score-shaped outcome label
        is refused.
        """
        self._guard(actor, "case_write", "ext_proposal_report_record",
                    target=request_id)
        _check_outcome_label(outcome_label)
        _string_or_none(proposal_ref, "proposal_ref")
        with self._lock:
            self._get("proposal_request", request_id)
            return self._create(
                "proposal_report", "proprep",
                {"request_id": request_id,
                 "outcome_label": outcome_label,
                 "proposal_ref": proposal_ref,
                 "reference_stub": True,
                 "proposal_held_here": False,
                 "generated_here": False},
                actor, "ext_proposal_report_record")

    def record_proposal_evaluation(self, actor, model_ref, metric_label,
                                   metric_value):
        """Record a proposal model's evaluation figure as
        reported. Action: case_write. Id prefix: propeval-.

        Reference implementation: evaluations of a model happen
        in its own harness, elsewhere; the figure arrives here as
        reported data -- an integer stored exactly as supplied, or
        a verbatim label string -- and nothing is computed from
        it (``computed_here: False``). Booleans and floats are
        rejected, mirroring the house rule that recorded values
        are exact.
        """
        self._guard(actor, "case_write", "ext_proposal_evaluation_record")
        _non_empty(model_ref, "model_ref")
        _non_empty(metric_label, "metric_label")
        _reported_figure(metric_value, "metric_value")
        return self._create(
            "proposal_evaluation", "propeval",
            {"model_ref": model_ref, "metric_label": metric_label,
             "metric_value": metric_value, "reference_stub": True,
             "computed_here": False},
            actor, "ext_proposal_evaluation_record")

    def get_proposal_request(self, request_id, actor=None):
        """One proposal request record. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_proposal_request_read",
                         target=request_id)
        return self._fetch("proposal_request", request_id)

    def list_proposal_requests(self, actor=None, account_id=None,
                               case_id=None):
        """Proposal request records, optionally filtered.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_proposal_request_read")
        filters = {}
        if account_id is not None:
            filters["account_id"] = account_id
        if case_id is not None:
            filters["case_id"] = case_id
        return self._list("proposal_request", **filters)

    def list_proposal_reports(self, request_id, actor=None):
        """Report records for one proposal request.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_proposal_request_read",
                         target=request_id)
        with self._lock:
            self._get("proposal_request", request_id)
            return self._list("proposal_report", request_id=request_id)

    def list_proposal_evaluations(self, actor=None, model_ref=None):
        """Proposal evaluation records. Action: case_read."""
        self._guard_read(actor, "case_read",
                         "ext_proposal_evaluation_read")
        if model_ref is not None:
            return self._list("proposal_evaluation", model_ref=model_ref)
        return self._list("proposal_evaluation")

    # ================================================================
    # Pipeline forecasting engine (idx 944; reference form --
    # re-judged from the drafted build-extension, grounds in
    # BATCH.md. There is no pipeline substrate in this build --
    # opportunities & sales pipeline is a named absence in this
    # set -- and a forecast is a computed projection, which this
    # build never computes: requests name the pipeline by opaque
    # reference only, and forecast figures arrive verbatim as
    # reported by the external engine)
    # ================================================================

    def register_forecast_request(self, actor, engine_ref, pipeline_ref,
                                  account_id=None):
        """Record a request to an external forecasting engine.
        Action: case_write.

        Id prefix: fcreq-. Reference implementation: the request
        names the engine by opaque ``engine_ref`` and the pipeline
        by opaque ``pipeline_ref`` -- the pipeline itself is not a
        record in this build (opportunities & sales pipeline is a
        named absence in this set, and this surface creates no
        pipeline record) -- and may bind an existing core account.
        There is deliberately no horizon, figure, or projection
        parameter: nothing here is computed (``computed_here:
        False``).
        """
        self._guard(actor, "case_write", "ext_forecast_request_register")
        _non_empty(engine_ref, "engine_ref")
        _non_empty(pipeline_ref, "pipeline_ref")
        with self._lock:
            if account_id is not None:
                self._core_account(account_id)
            return self._create(
                "forecast_request", "fcreq",
                {"engine_ref": engine_ref, "pipeline_ref": pipeline_ref,
                 "account_id": account_id, "reference_stub": True,
                 "computed_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_forecast_request_register")

    def record_forecast_report(self, actor, request_id, outcome_label,
                               forecast_ref=None):
        """Record a forecasting engine's reported outcome for a
        request. Action: case_write. Id prefix: fcrep-.

        The outcome label is stored verbatim as the engine's
        operator reported it; the forecast itself is named only
        by an opaque ``forecast_ref`` and is never held here
        (``forecast_held_here: False``). A score-shaped outcome
        label is refused.
        """
        self._guard(actor, "case_write", "ext_forecast_report_record",
                    target=request_id)
        _check_outcome_label(outcome_label)
        _string_or_none(forecast_ref, "forecast_ref")
        with self._lock:
            self._get("forecast_request", request_id)
            return self._create(
                "forecast_report", "fcrep",
                {"request_id": request_id,
                 "outcome_label": outcome_label,
                 "forecast_ref": forecast_ref,
                 "reference_stub": True,
                 "forecast_held_here": False,
                 "computed_here": False},
                actor, "ext_forecast_report_record")

    def record_forecast_figure(self, actor, request_id, figure_label,
                               figure_value):
        """Record a forecast figure exactly as the external engine
        reported it. Action: case_write. Id prefix: fcfig-.

        The figure is reported data: an integer stored exactly as
        supplied, or a verbatim label string. It is never computed
        here, never projected forward, and never combined with
        another figure (``computed_here: False``). Booleans and
        floats are rejected, mirroring the house rule that
        recorded values are exact.
        """
        self._guard(actor, "case_write", "ext_forecast_figure_record",
                    target=request_id)
        _non_empty(figure_label, "figure_label")
        _reported_figure(figure_value, "figure_value")
        with self._lock:
            self._get("forecast_request", request_id)
            return self._create(
                "forecast_figure", "fcfig",
                {"request_id": request_id,
                 "figure_label": figure_label,
                 "figure_value": figure_value,
                 "reference_stub": True, "computed_here": False},
                actor, "ext_forecast_figure_record")

    def get_forecast_request(self, request_id, actor=None):
        """One forecast request record. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_forecast_request_read",
                         target=request_id)
        return self._fetch("forecast_request", request_id)

    def list_forecast_requests(self, actor=None, account_id=None):
        """Forecast request records, optionally for one account.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_forecast_request_read")
        if account_id is not None:
            return self._list("forecast_request", account_id=account_id)
        return self._list("forecast_request")

    def list_forecast_reports(self, request_id, actor=None):
        """Report records for one forecast request.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_forecast_request_read",
                         target=request_id)
        with self._lock:
            self._get("forecast_request", request_id)
            return self._list("forecast_report", request_id=request_id)

    def list_forecast_figures(self, request_id, actor=None):
        """Figure records for one forecast request.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_forecast_request_read",
                         target=request_id)
        with self._lock:
            self._get("forecast_request", request_id)
            return self._list("forecast_figure", request_id=request_id)

    def forecast_summary(self, actor=None):
        """Counts over the recorded forecast records.

        Action: report_read. Derived at read, stored nowhere:
        request / report / figure counts, reports counted by
        their verbatim reported outcome labels, figures counted
        by their verbatim reported labels. Counts of records
        only -- no figure is summed, averaged, or projected, and
        no forecast is computed; the summary states its method on
        its face.
        """
        self._guard_read(actor, "report_read", "ext_forecast_summary")
        with self._lock:
            requests = self._list("forecast_request")
            reports = self._list("forecast_report")
            figures = self._list("forecast_figure")
            by_outcome = {}
            for report in reports:
                label = report["outcome_label"]
                by_outcome[label] = by_outcome.get(label, 0) + 1
            by_figure_label = {}
            for figure in figures:
                label = figure["figure_label"]
                by_figure_label[label] = by_figure_label.get(label, 0) + 1
            return {
                "method": "recorded_forecast_counts",
                "derived": True,
                "requests": len(requests),
                "reports": len(reports),
                "figures": len(figures),
                "by_outcome": by_outcome,
                "by_figure_label": by_figure_label,
            }

    # ================================================================
    # Document automation engine (idx 945; reference form, as
    # drafted stub-engine. Template definitions are held as data,
    # exactly as the core holds a module's settings_text and the
    # High sibling holds design definitions; automation requests
    # and reported outcomes are records; the generated document
    # is named only by opaque reference and never held, rendered,
    # or assembled here)
    # ================================================================

    def register_document_template(self, actor, label, template_ref,
                                   definition_text=None):
        """Register a document template definition as data.
        Action: config_write (admin, as configuration writes
        are). Id prefix: dtmpl-.

        ``template_ref`` is a required, opaque, unique reference
        naming the template in its own system. ``definition_text``,
        when given, is the template's definition text stored
        verbatim as data -- it is never rendered, merged, or
        executed here (``rendered_here: False``,
        ``executed_here: False``), exactly as the core holds
        module ``settings_text``.
        """
        self._guard(actor, "config_write", "ext_document_template_register")
        _non_empty(label, "template label")
        _non_empty(template_ref, "template_ref")
        if definition_text is not None:
            _non_empty(definition_text, "definition_text")
        with self._lock:
            for existing in self._list("document_template"):
                if existing["template_ref"] == template_ref:
                    raise ValidationError(
                        "template_ref %r already exists" % (template_ref,))
            return self._create(
                "document_template", "dtmpl",
                {"label": label, "template_ref": template_ref,
                 "definition_text": definition_text,
                 "reference_stub": True, "rendered_here": False,
                 "executed_here": False},
                actor, "ext_document_template_register")

    def request_document_automation(self, actor, template_id,
                                    parameters=None, account_id=None,
                                    case_id=None):
        """Record a request for the external automation engine to
        produce a document from a registered template.
        Action: config_write (admin). Id prefix: docreq-.

        The request snapshots the template's label and
        ``template_ref`` as data and holds the caller's parameters
        as validated scalar data (score-shaped keys, floats, and
        nested structures refused -- parameters are data, not a
        program). It may bind an existing core account and/or
        case (a case bound alongside an account it does not
        belong to is refused). No document is generated or
        assembled here (``generated_here: False``,
        ``automated_here: False``); the state is
        ``recorded_request_only``.
        """
        self._guard(actor, "config_write",
                    "ext_document_automation_request", target=template_id)
        parameters = _validate_parameters(parameters)
        with self._lock:
            template = self._get("document_template", template_id)
            if account_id is not None:
                self._core_account(account_id)
            if case_id is not None:
                case = self._core_case(case_id)
                self._check_case_account(case, account_id)
            return self._create(
                "document_request", "docreq",
                {"template_id": template_id,
                 "template_ref": template["template_ref"],
                 "parameters": parameters,
                 "account_id": account_id, "case_id": case_id,
                 "reference_stub": True, "generated_here": False,
                 "automated_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_document_automation_request")

    def record_document_report(self, actor, request_id, outcome,
                               document_ref=None):
        """Record the automation engine's reported outcome for a
        request. Action: config_write (admin). Id prefix: docrep-.

        ``outcome`` is from the fixed reported vocabulary
        (``reported_completed`` / ``reported_failed`` /
        ``reported_noop``) -- the engine's own report, stored as
        data. The produced document is named only by an opaque
        ``document_ref`` and is never held here
        (``document_held_here: False``, ``generated_here:
        False``).
        """
        self._guard(actor, "config_write", "ext_document_report_record",
                    target=request_id)
        _one_of(outcome, KNOWN_AUTOMATION_REPORT_OUTCOMES,
                AUTOMATION_REPORT_OUTCOMES, "outcome")
        _string_or_none(document_ref, "document_ref")
        with self._lock:
            self._get("document_request", request_id)
            return self._create(
                "document_report", "docrep",
                {"request_id": request_id, "outcome": outcome,
                 "document_ref": document_ref,
                 "reference_stub": True,
                 "document_held_here": False,
                 "generated_here": False},
                actor, "ext_document_report_record")

    def get_document_template(self, template_id, actor=None):
        """One document template record. Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_document_template_read", target=template_id)
        return self._fetch("document_template", template_id)

    def list_document_templates(self, actor=None):
        """Document template records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_document_template_read")
        return self._list("document_template")

    def get_document_request(self, request_id, actor=None):
        """One document automation request. Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_document_automation_read", target=request_id)
        return self._fetch("document_request", request_id)

    def list_document_requests(self, actor=None, template_id=None):
        """Document automation requests, optionally for one
        template. Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_document_automation_read")
        if template_id is not None:
            return self._list("document_request", template_id=template_id)
        return self._list("document_request")

    def list_document_reports(self, request_id, actor=None):
        """Report records for one document request.

        Action: config_read.
        """
        self._guard_read(actor, "config_read",
                         "ext_document_automation_read", target=request_id)
        with self._lock:
            self._get("document_request", request_id)
            return self._list("document_report", request_id=request_id)

    # ================================================================
    # Integration connector engines (idx 946; reference form, as
    # drafted stub-engine -- connector definitions and sync
    # receipts, labeled reference_transport: True; nothing is
    # connected, transmitted, or synced. This surface is the
    # records layer in front of connectors, not a connector)
    # ================================================================

    def register_connector(self, actor, connector_ref, label=None):
        """Register a connector definition as a record.
        Action: config_write (admin, as configuration writes
        are). Id prefix: conn-.

        ``connector_ref`` is a required, opaque, unique reference
        naming the connector in its own system; ``label`` is a
        caller-chosen display string. Registering the definition
        connects nothing (``connected_here: False``); the record
        exists so sync receipts have a named definition to cite.
        """
        self._guard(actor, "config_write", "ext_connector_register")
        _non_empty(connector_ref, "connector_ref")
        _string_or_none(label, "connector label")
        with self._lock:
            for existing in self._list("connector"):
                if existing["connector_ref"] == connector_ref:
                    raise ValidationError(
                        "connector_ref %r already exists" % (connector_ref,))
            return self._create(
                "connector", "conn",
                {"connector_ref": connector_ref, "label": label,
                 "reference_stub": True, "reference_transport": True,
                 "connected_here": False},
                actor, "ext_connector_register")

    def record_connector_sync(self, actor, connector_ref, direction,
                              records_reported, target_kind=None,
                              target_id=None):
        """Record a connector sync as reported by the connector.
        Action: config_write (admin). Id prefix: csync-.

        Reference implementation: the receipt may bind one
        existing core record (account, case, guide, finding, or
        module) as its target; ``records_reported`` is the
        connector's own count, stored as data. Nothing was
        transmitted or synced here (``transmitted_here: False``,
        ``synced_here: False``), and the target record is never
        modified.
        """
        self._guard(actor, "config_write", "ext_connector_sync_record")
        _non_empty(connector_ref, "connector_ref")
        _one_of(direction, KNOWN_CONNECTOR_DIRECTIONS,
                CONNECTOR_DIRECTIONS, "direction")
        _nonneg_int(records_reported, "records_reported")
        if (target_kind is None) != (target_id is None):
            raise ValidationError(
                "target_kind and target_id must be given together")
        with self._lock:
            if target_kind is not None:
                _one_of(target_kind, KNOWN_CONNECTOR_TARGET_KINDS,
                        CONNECTOR_TARGET_KINDS, "target_kind")
                getter = {
                    "account": self.store.get_account,
                    "case": self.store.get_case,
                    "guide": self.store.get_guide,
                    "finding": self.store.get_finding,
                    "module": self.store.get_module,
                }[target_kind]
                getter(target_id)
            return self._create(
                "connector_sync", "csync",
                {"connector_ref": connector_ref, "direction": direction,
                 "records_reported": records_reported,
                 "target_kind": target_kind, "target_id": target_id,
                 "reference_stub": True, "reference_transport": True,
                 "transmitted_here": False, "synced_here": False},
                actor, "ext_connector_sync_record")

    def get_connector(self, connector_id, actor=None):
        """One connector definition record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_read",
                         target=connector_id)
        return self._fetch("connector", connector_id)

    def list_connectors(self, actor=None):
        """Connector definition records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_read")
        return self._list("connector")

    def get_connector_sync(self, sync_id, actor=None):
        """One connector sync record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_sync_read",
                         target=sync_id)
        return self._fetch("connector_sync", sync_id)

    def list_connector_syncs(self, actor=None, connector_ref=None):
        """Connector sync records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_sync_read")
        if connector_ref is not None:
            return self._list("connector_sync", connector_ref=connector_ref)
        return self._list("connector_sync")

    def _sync_rollup(self, syncs):
        """Accumulate recorded sync receipts per connector.

        The single derivation point for the connector catalog:
        for each connector, the count of its recorded receipts,
        the sum of the connectors' own reported record counts,
        and the receipt counts by direction. Sums of recorded
        values only. MUTATION DRILL NOTE: the batch's negative
        control overrides this method; the live drill patches its
        total-accumulation line (see tests/README.md).
        """
        by_ref = {}
        for sync in syncs:
            entry = by_ref.setdefault(
                sync["connector_ref"],
                {"connector_ref": sync["connector_ref"], "syncs": 0,
                 "records_reported_total": 0, "by_direction": {}})
            entry["syncs"] += 1
            entry["records_reported_total"] += sync["records_reported"]
            direction = sync["direction"]
            entry["by_direction"][direction] = (
                entry["by_direction"].get(direction, 0) + 1)
        return by_ref

    def connector_catalog(self, actor=None):
        """Per-connector rollup of recorded sync receipts.

        Action: config_read. Derived at read, stored nowhere:
        sync counts and sums of the connectors' own reported
        record counts, by connector and direction. Sums of
        recorded values only -- nothing here measures a real
        integration.
        """
        self._guard_read(actor, "config_read", "ext_connector_catalog")
        with self._lock:
            syncs = self._list("connector_sync")
            by_ref = self._sync_rollup(syncs)
            connectors = [by_ref[ref] for ref in sorted(by_ref)]
            return {
                "method": "recorded_sync_counts",
                "derived": True,
                "connectors": connectors,
                "total_syncs": len(syncs),
                "total_records_reported": sum(
                    s["records_reported"] for s in syncs),
            }

    # ================================================================
    # Extension summary (derived)
    # ================================================================

    def extension_summary(self, actor=None):
        """Counts of extension records by kind. Action: report_read.

        Derived at read, stored nowhere. Counts of records only.
        """
        self._guard_read(actor, "report_read", "ext_summary")
        with self._lock:
            counts = {}
            for kind, _record_id in self._order:
                counts[kind] = counts.get(kind, 0) + 1
            return {
                "method": "extension_record_counts",
                "derived": True,
                "by_kind": counts,
                "total": len(self._order),
            }
