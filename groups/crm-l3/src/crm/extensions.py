"""Final GAPS batch extensions for the CRM L3-adjacent merged
build (Singleton 40).

Clean-room, standard-library-only records extensions for the 5
open Extended entries this singleton's GAPS.md section carries:
3 drafted ``build-extension`` and 2 drafted ``stub-engine`` in
``../../gaps-batch/inventory.json`` (idx 399-403). See ``BATCH.md``
in the group directory for the per-entry disposition, including
three re-judgments recorded there under DECISION.md
qualification 1 (idx 399, 401, 403: drafted ``build-extension``,
closing ``reference``, with grounds).

All five entries close as labeled reference implementations.
That is this tier's honest outcome, not a shortcut: the five
entries name the singleton fork's own product surface -- a
no-code application development engine, a BPM / workflow
execution engine, a decisioning engine, GenAI tooling, and the
operated managed-cloud platform itself -- and every one of them
is an engine whose substance is execution, generation,
inference, or platform operation against external systems. The
category's adjudicated forms at Moderate (``../crm-l2/BATCH.md``)
and at Low / LI-SaaS (``../crm-l1/BATCH.md``) closed the same
substances the same way, and this build's core is Group 25's
substrate carried up whole: the same form cannot honestly carry
``built`` at High for the same substance.

Design, following the core's doctrines:

- This module is a wrapper around :class:`CrmStore`; the core
  modules are untouched (byte-identical). Core state (accounts,
  contacts, cases, guides, findings, modules) is read through
  the core store's public API, never re-implemented, and no
  extension operation writes core state. Existence checks
  against the core pass ``actor=None`` internally: the
  extension's own guard has already enforced the mapped action
  before the check runs.
- RBAC goes through :mod:`crm.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like
  actors, and records denied attempts on the core audit log with
  the extension action name suffixed ``:denied``. Plain-string
  actors carry identity but no role, mirroring the core
  convention. The mapping is:

  - design definitions, revisions, and generation requests /
    reports -> ``config_write`` / ``config_read`` (they bind
    module configuration records; ``config_write`` is
    admin-only, as in the core);
  - workflow definitions, run requests, and run reports ->
    ``case_write`` / ``case_read`` (they bind case records);
  - decision requests, reports, and evaluations ->
    ``case_write`` / ``case_read`` (case-adjacent operational
    records, as the L2 unit mapped its AI surface);
  - AI / GenAI requests, reports, and evaluations ->
    ``case_write`` / ``case_read`` (the L2 mapping);
  - environment records, scaling reports, operations reports,
    and the operations summary -> ``config_write`` /
    ``config_read`` (platform configuration genus);
  - the extension summary -> ``report_read``.

  The separated ``auditor`` role [L3] holds ``audit_read`` and
  nothing else, so it is denied every extension read and write;
  its denials land on the same hash-chained log it exists to
  review (pinned by test).
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. The
  log at this tier is hash-chained and fail-closed [L3]: if the
  audit write raises, the record insertion and its id roll back
  before the error propagates -- no extension record exists
  whose audit entry does not, and the chain still verifies after
  extension operations (pinned by test).
- All references to people, systems, environments, and models
  are opaque ``*_ref`` strings, exactly as in the core. Where a
  record binds a person or an organization it names a core
  account/contact by id or carries an opaque ``*_ref`` string;
  no record shape in this module can hold a real name, email,
  phone number, or any other identifier, and none can hold a
  computed score or a generated artifact.
- Derived values are derived at read and never stored: design
  current text and revision counts, the operations rollup, the
  extension summary. Stored records carry no derived key; tests
  pin that.
- Nothing here executes against an external system. Every
  record this module creates carries ``reference_stub: True``:
  no application is generated, no design is executed, no
  workflow runs, no case is acted on by automation, no decision
  is computed, no model is run, no content is generated, and no
  environment is hosted, operated, or scaled. The records say
  so on their face (``generated_here: False``,
  ``executed_here: False``, ``decided_here: False``,
  ``inference_here: False``, ``hosted_here: False``,
  ``operated_here: False``, ``scaled_here: False``).
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

EXECUTION_REPORT_OUTCOMES = (
    "reported_completed",
    "reported_failed",
    "reported_noop",
)
KNOWN_EXECUTION_REPORT_OUTCOMES = frozenset(EXECUTION_REPORT_OUTCOMES)

# Keys that would make a record carry a computed score. The core
# forbids scores by design; the extension refuses them as
# parameter names and result labels alike (tests pin the refusal
# and scan every stored record for these keys). Decisioning is
# the family where this bites hardest: a decision computed from
# a propensity is a score by another name, and none is computed
# or stored here.
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


def _check_label_not_score_shaped(label, what):
    if label.strip().lower() in SCORE_KEYS:
        raise ValidationError(
            "%s may not be a score-shaped label: %r" % (what, label))
    return label


def _validate_parameters(parameters, what="parameters", required=False):
    """Validate a configuration-parameter mapping held as data.

    Keys are parameter names (non-empty strings, never
    score-shaped); values are strings, integers, or booleans --
    the scalar shapes a configuration record can state. Floats
    are rejected (house rule: recorded values are exact), as are
    nested structures: parameters are data, not a program.
    """
    if parameters is None:
        if required:
            raise ValidationError("%s are required" % (what,))
        return None
    if not isinstance(parameters, dict):
        raise ValidationError("%s must be a dict" % (what,))
    if required and not parameters:
        raise ValidationError("%s must not be empty" % (what,))
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


def _validate_workflow_steps(steps):
    """Validate workflow step records: {step, action} data.

    Steps are the definition's own data -- a named step and the
    action label the external engine would perform. Only those
    two keys are kept; a step record is data about a process,
    never a program this build runs.
    """
    if steps is None:
        return []
    if not isinstance(steps, list):
        raise ValidationError("steps must be a list of step records")
    if len(steps) > 50:
        raise ValidationError("steps may hold at most 50 entries")
    result = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValidationError("each step must be a record")
        name = step.get("step")
        action = step.get("action")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("each step needs a non-empty 'step'")
        if not isinstance(action, str) or not action.strip():
            raise ValidationError("each step needs a non-empty 'action'")
        result.append({"step": name, "action": action})
    return result


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

        Mirrors the core store: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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
                # Fail closed, mirroring the core's AU-5 posture at
                # this tier: an operation whose audit write fails
                # does not proceed -- the insertion and the id roll
                # back before the error propagates.
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

    def _core_module(self, module_id):
        return self.store.get_module(module_id)

    # ================================================================
    # No-code / low-code application development engine &
    # model-based design tooling (build-extension entry, RE-JUDGED
    # to reference form -- grounds in BATCH.md: a development
    # engine generates and runs applications from design models;
    # generation is execution, and the core's founding invariant
    # holds configuration text verbatim, never executed. What
    # lands is the records layer in front of the engine: design
    # definitions held as data, generation requests, and reported
    # outcomes, every record labeled reference_stub: True)
    # ================================================================

    def register_design_definition(self, actor, name, model_text,
                                   module_id=None):
        """Record an application design definition as data.

        Action: config_write (admin, as module writes are). Id
        prefixes: design- plus a first drev- revision.
        Reference implementation: ``model_text`` is the design
        model held verbatim as data, exactly as the core holds a
        module's ``settings_text`` -- it is never interpreted,
        generated from, or executed (``designed_here: False``,
        ``generated_here: False``). The definition may bind an
        existing core module; the module record is never touched.
        """
        self._guard(actor, "config_write",
                    "ext_design_definition_register")
        _non_empty(name, "design name")
        _non_empty(model_text, "model_text")
        with self._lock:
            if module_id is not None:
                self._core_module(module_id)
            design = self._create(
                "design_definition", "design",
                {"name": name, "module_id": module_id,
                 "reference_stub": True, "designed_here": False,
                 "generated_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_design_definition_register")
            self._create(
                "design_revision", "drev",
                {"design_id": design["id"], "revision": 1,
                 "model_text": model_text},
                actor, "ext_design_definition_register")
            return self._design_view(design["id"])

    def revise_design_definition(self, actor, design_id, model_text):
        """Append a revision to a design definition.

        Action: config_write. Id prefix: drev-. Revisions are
        append-only; earlier revisions never change and there is
        no update or delete API. The current text is the latest
        revision's, derived at read.
        """
        self._guard(actor, "config_write",
                    "ext_design_definition_revise", target=design_id)
        _non_empty(model_text, "model_text")
        with self._lock:
            self._get("design_definition", design_id)
            revisions = self._list("design_revision",
                                   design_id=design_id)
            return self._create(
                "design_revision", "drev",
                {"design_id": design_id,
                 "revision": len(revisions) + 1,
                 "model_text": model_text},
                actor, "ext_design_definition_revise")

    def _revisions_of(self, design_id):
        return self._list("design_revision", design_id=design_id)

    def _design_view(self, design_id):
        design = self._fetch("design_definition", design_id)
        revisions = self._revisions_of(design_id)
        current = revisions[-1] if revisions else None
        design["model_text"] = (
            current["model_text"] if current is not None else None)
        design["revision_count"] = len(revisions)
        return design

    def get_design_definition(self, design_id, actor=None):
        """One design definition, current text derived at read.

        Action: config_read.
        """
        self._guard_read(actor, "config_read",
                         "ext_design_definition_read", target=design_id)
        with self._lock:
            return self._design_view(design_id)

    def list_design_definitions(self, actor=None):
        """All design definitions (current views). Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_design_definition_read")
        with self._lock:
            return [self._design_view(d["id"])
                    for d in self._list("design_definition")]

    def list_design_revisions(self, design_id, actor=None):
        """The append-only revision history of one design.

        Action: config_read.
        """
        self._guard_read(actor, "config_read",
                         "ext_design_definition_read", target=design_id)
        with self._lock:
            self._get("design_definition", design_id)
            return self._revisions_of(design_id)

    def request_application_generation(self, actor, design_id,
                                       parameters=None):
        """Record a request to generate an application elsewhere.

        Action: config_write. Id prefix: genreq-. Reference
        implementation: the request snapshots the design's
        current revision number and holds its parameters as
        validated scalar data (score-shaped keys refused,
        exactly as the core refuses scores); nothing is
        generated (``generated_here: False``,
        ``executed_here: False``) and the design record itself
        is never touched.
        """
        self._guard(actor, "config_write", "ext_generation_request",
                    target=design_id)
        parameters = _validate_parameters(parameters)
        with self._lock:
            self._get("design_definition", design_id)
            revisions = self._revisions_of(design_id)
            return self._create(
                "generation_request", "genreq",
                {"design_id": design_id,
                 "design_revision": len(revisions),
                 "parameters": parameters, "reference_stub": True,
                 "generated_here": False, "executed_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_generation_request")

    def record_generation_report(self, actor, generation_id, outcome,
                                 artifact_ref=None):
        """Record a generation outcome, verbatim as reported.

        Action: config_write. Id prefix: genrep-. The outcome is
        the external development platform's report from the
        fixed vocabulary; the generated application itself is
        named only by an opaque ``artifact_ref`` and is never
        held here (``artifact_held_here: False``,
        ``generated_here: False``).
        """
        self._guard(actor, "config_write", "ext_generation_report",
                    target=generation_id)
        _one_of(outcome, KNOWN_EXECUTION_REPORT_OUTCOMES,
                EXECUTION_REPORT_OUTCOMES, "outcome")
        _string_or_none(artifact_ref, "artifact_ref")
        with self._lock:
            self._get("generation_request", generation_id)
            return self._create(
                "generation_report", "genrep",
                {"generation_id": generation_id, "outcome": outcome,
                 "artifact_ref": artifact_ref,
                 "reference_stub": True, "generated_here": False,
                 "artifact_held_here": False},
                actor, "ext_generation_report")

    def get_generation_request(self, generation_id, actor=None):
        """One generation request record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_generation_read",
                         target=generation_id)
        return self._fetch("generation_request", generation_id)

    def list_generation_requests(self, actor=None, design_id=None):
        """Generation request records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_generation_read")
        if design_id is not None:
            return self._list("generation_request", design_id=design_id)
        return self._list("generation_request")

    def list_generation_reports(self, generation_id, actor=None):
        """Generation report records for one request.

        Action: config_read.
        """
        self._guard_read(actor, "config_read", "ext_generation_read",
                         target=generation_id)
        with self._lock:
            self._get("generation_request", generation_id)
            return self._list("generation_report",
                              generation_id=generation_id)

    # ================================================================
    # Case management & BPM / workflow execution engines
    # (stub-engine entry; reference form as drafted -- workflow
    # definitions held as data, run requests and reported run
    # outcomes; the registry never executes a workflow and no
    # automation acts on a case)
    # ================================================================

    def define_workflow(self, actor, name, steps=None, case_id=None):
        """Record a workflow definition as data.

        Action: case_write. Id prefix: wflow-. Reference
        implementation: ``kind`` is the constant ``bpm_workflow``
        and the steps are ``{step, action}`` records held as
        data; the definition may bind an existing core case.
        The registry never executes a workflow
        (``executed_here: False``), pinned by test: defining a
        workflow and recording a run changes no core record.
        """
        self._guard(actor, "case_write", "ext_workflow_define")
        _non_empty(name, "workflow name")
        steps = _validate_workflow_steps(steps)
        with self._lock:
            if case_id is not None:
                self._core_case(case_id)
            return self._create(
                "workflow", "wflow",
                {"kind": "bpm_workflow", "name": name,
                 "case_id": case_id, "steps": steps,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_workflow_define")

    def request_workflow_run(self, actor, workflow_id, case_id=None):
        """Record a request to run a workflow elsewhere.

        Action: case_write. Id prefix: wfrun-. The run binds
        the workflow and at most one core case: the workflow's
        own bound case, or an explicitly named existing case;
        a conflicting pair is refused. Nothing runs
        (``executed_here: False``) and the bound case record is
        never touched -- case automation acting on cases is
        the engine's, not this build's.
        """
        self._guard(actor, "case_write", "ext_workflow_run_request",
                    target=workflow_id)
        with self._lock:
            workflow = self._get("workflow", workflow_id)
            bound_case = workflow["case_id"]
            if (bound_case is not None and case_id is not None
                    and case_id != bound_case):
                raise ValidationError(
                    "run case %r conflicts with the workflow's "
                    "bound case %r" % (case_id, bound_case))
            run_case = case_id if case_id is not None else bound_case
            if run_case is not None:
                self._core_case(run_case)
            return self._create(
                "workflow_run", "wfrun",
                {"workflow_id": workflow_id, "case_id": run_case,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_workflow_run_request")

    def record_workflow_run_report(self, actor, run_id, outcome,
                                   steps_reported=None):
        """Record a workflow run outcome, verbatim as reported.

        Action: case_write. Id prefix: wfout-. The outcome is
        the external engine's report from the fixed vocabulary;
        ``steps_reported`` is the engine's own count of steps
        it reports having run, stored as data. The run happened
        there, not here (``executed_here: False``).
        """
        self._guard(actor, "case_write", "ext_workflow_run_report",
                    target=run_id)
        _one_of(outcome, KNOWN_EXECUTION_REPORT_OUTCOMES,
                EXECUTION_REPORT_OUTCOMES, "outcome")
        if steps_reported is not None:
            _nonneg_int(steps_reported, "steps_reported")
        with self._lock:
            self._get("workflow_run", run_id)
            return self._create(
                "workflow_run_report", "wfout",
                {"run_id": run_id, "outcome": outcome,
                 "steps_reported": steps_reported,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_workflow_run_report")

    def get_workflow(self, workflow_id, actor=None):
        """One workflow definition record. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_workflow_read",
                         target=workflow_id)
        return self._fetch("workflow", workflow_id)

    def list_workflows(self, actor=None, case_id=None):
        """Workflow definition records. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_workflow_read")
        if case_id is not None:
            return self._list("workflow", case_id=case_id)
        return self._list("workflow")

    def list_workflow_runs(self, workflow_id, actor=None):
        """Run request records for one workflow.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_workflow_read",
                         target=workflow_id)
        with self._lock:
            self._get("workflow", workflow_id)
            return self._list("workflow_run", workflow_id=workflow_id)

    def list_workflow_run_reports(self, run_id, actor=None):
        """Run report records for one run request.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_workflow_read",
                         target=run_id)
        with self._lock:
            self._get("workflow_run", run_id)
            return self._list("workflow_run_report", run_id=run_id)

    # ================================================================
    # Decisioning engine (build-extension entry, RE-JUDGED to
    # reference form -- grounds in BATCH.md: a decisioning
    # engine's substance is inference, choosing an action from
    # context by a computed propensity; this build computes no
    # score anywhere, by design, and a decisioning surface that
    # decided nothing would be an engine in name only. What
    # lands is the category's adjudicated AI form: request
    # records whose signature refuses decision content, reported
    # outcomes naming the decision only by opaque reference,
    # and evaluation figures stored verbatim as reported)
    # ================================================================

    def register_decision_request(self, actor, engine_ref, purpose,
                                  case_id=None, account_id=None):
        """Record a request to an external decisioning engine.

        Action: case_write. Id prefix: dreq-. Reference
        implementation: the request names the engine by opaque
        ``engine_ref`` and may bind an existing core case and /
        or account (a case linked alongside an account it does
        not belong to is refused, mirroring the core's linkage
        discipline). There is deliberately no decision, result,
        or score parameter -- a decision enters this build only
        as a reported record (``record_decision_report``), never
        as a value this build produces (``decided_here: False``,
        ``inference_here: False``).
        """
        self._guard(actor, "case_write", "ext_decision_request_register")
        _non_empty(engine_ref, "engine_ref")
        _non_empty(purpose, "purpose")
        with self._lock:
            if account_id is not None:
                self._core_account(account_id)
            if case_id is not None:
                case = self._core_case(case_id)
                if (account_id is not None
                        and case["account_id"] is not None
                        and case["account_id"] != account_id):
                    raise ValidationError(
                        "case %r does not belong to account %r"
                        % (case_id, account_id))
            return self._create(
                "decision_request", "dreq",
                {"engine_ref": engine_ref, "purpose": purpose,
                 "case_id": case_id, "account_id": account_id,
                 "reference_stub": True, "decided_here": False,
                 "inference_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_decision_request_register")

    def record_decision_report(self, actor, request_id, outcome_label,
                               decision_ref=None):
        """Record a decisioning engine's reported outcome.

        Action: case_write. Id prefix: drep-. The outcome label
        is stored verbatim as the engine's operator reported
        it; the decision itself is named only by an opaque
        ``decision_ref`` and is never held or reproduced here
        (``decision_held_here: False``). A score-shaped outcome
        label is refused: reported outcomes are labels, and no
        scoring enters through this surface.
        """
        self._guard(actor, "case_write", "ext_decision_report_record",
                    target=request_id)
        _non_empty(outcome_label, "outcome_label")
        _check_label_not_score_shaped(outcome_label, "outcome_label")
        _string_or_none(decision_ref, "decision_ref")
        with self._lock:
            self._get("decision_request", request_id)
            return self._create(
                "decision_report", "drep",
                {"request_id": request_id,
                 "outcome_label": outcome_label,
                 "decision_ref": decision_ref,
                 "reference_stub": True, "decided_here": False,
                 "decision_held_here": False},
                actor, "ext_decision_report_record")

    def record_decision_evaluation(self, actor, engine_ref,
                                   metric_label, metric_value):
        """Record a decisioning evaluation figure as reported.

        Action: case_write. Id prefix: deval-. Reference
        implementation: evaluations of the engine happen in its
        own harness, elsewhere; the figure arrives here as
        reported data -- an integer stored exactly as supplied,
        or a verbatim label string -- and nothing is computed
        from it (``computed_here: False``). Booleans and floats
        are rejected for numeric values, mirroring the house
        rule that recorded values are exact.
        """
        self._guard(actor, "case_write",
                    "ext_decision_evaluation_record")
        _non_empty(engine_ref, "engine_ref")
        _non_empty(metric_label, "metric_label")
        if isinstance(metric_value, bool) or not isinstance(
                metric_value, (int, str)):
            raise ValidationError(
                "metric_value must be an integer or a verbatim "
                "label string")
        if isinstance(metric_value, str) and not metric_value.strip():
            raise ValidationError("metric_value must not be empty")
        return self._create(
            "decision_evaluation", "deval",
            {"engine_ref": engine_ref, "metric_label": metric_label,
             "metric_value": metric_value, "reference_stub": True,
             "computed_here": False},
            actor, "ext_decision_evaluation_record")

    def get_decision_request(self, request_id, actor=None):
        """One decision request record. Action: case_read."""
        self._guard_read(actor, "case_read",
                         "ext_decision_request_read", target=request_id)
        return self._fetch("decision_request", request_id)

    def list_decision_requests(self, actor=None, case_id=None):
        """Decision request records. Action: case_read."""
        self._guard_read(actor, "case_read",
                         "ext_decision_request_read")
        if case_id is not None:
            return self._list("decision_request", case_id=case_id)
        return self._list("decision_request")

    def list_decision_reports(self, request_id, actor=None):
        """Report records for one decision request.

        Action: case_read.
        """
        self._guard_read(actor, "case_read",
                         "ext_decision_request_read", target=request_id)
        with self._lock:
            self._get("decision_request", request_id)
            return self._list("decision_report", request_id=request_id)

    def list_decision_evaluations(self, actor=None, engine_ref=None):
        """Decision evaluation records. Action: case_read."""
        self._guard_read(actor, "case_read",
                         "ext_decision_evaluation_read")
        if engine_ref is not None:
            return self._list("decision_evaluation",
                              engine_ref=engine_ref)
        return self._list("decision_evaluation")

    # ================================================================
    # GenAI application tooling and AI / ML models generally
    # (stub-engine entry; reference form as drafted -- requests
    # and reported results only; no model runs, no content is
    # generated, and no score is computed, mirroring the core's
    # by-design absence of scores. GenAI tooling requests use
    # this same form: ``model_ref`` may name a generative tool,
    # and the signature refuses generated content exactly as it
    # refuses result content)
    # ================================================================

    def register_ai_request(self, actor, model_ref, purpose,
                            case_id=None):
        """Record a request to an external model or GenAI tool.

        Action: case_write. Id prefix: aireq-. Reference
        implementation: the request names the model by opaque
        ``model_ref`` and may bind an existing core case; there
        is deliberately no result, output, or generated-content
        parameter -- a result enters this build only as a
        reported record (``record_ai_report``), never as a value
        this build produces (``inference_here: False``).
        """
        self._guard(actor, "case_write", "ext_ai_request_register")
        _non_empty(model_ref, "model_ref")
        _non_empty(purpose, "purpose")
        with self._lock:
            if case_id is not None:
                self._core_case(case_id)
            return self._create(
                "ai_request", "aireq",
                {"model_ref": model_ref, "purpose": purpose,
                 "case_id": case_id, "reference_stub": True,
                 "inference_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_ai_request_register")

    def record_ai_report(self, actor, request_id, outcome_label,
                         result_ref=None):
        """Record a model's reported outcome for a request.

        Action: case_write. Id prefix: air-. The outcome label
        is stored verbatim as the model's operator reported it;
        the result itself is named only by an opaque
        ``result_ref`` and is never held here
        (``result_held_here: False``). A score-shaped outcome
        label is refused: reported outcomes are labels, and no
        scoring enters through this surface.
        """
        self._guard(actor, "case_write", "ext_ai_report_record",
                    target=request_id)
        _non_empty(outcome_label, "outcome_label")
        _check_label_not_score_shaped(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._get("ai_request", request_id)
            return self._create(
                "ai_report", "air",
                {"request_id": request_id,
                 "outcome_label": outcome_label,
                 "result_ref": result_ref,
                 "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_ai_report_record")

    def record_ai_evaluation(self, actor, model_ref, metric_label,
                             metric_value):
        """Record a model evaluation figure as reported.

        Action: case_write. Id prefix: aieval-. Reference
        implementation: evaluations of a model happen in its
        own harness, elsewhere; the figure arrives here as
        reported data -- an integer stored exactly as supplied,
        or a verbatim label string -- and nothing is computed
        from it (``computed_here: False``). Booleans and floats
        are rejected for numeric values, mirroring the house
        rule that recorded values are exact.
        """
        self._guard(actor, "case_write", "ext_ai_evaluation_record")
        _non_empty(model_ref, "model_ref")
        _non_empty(metric_label, "metric_label")
        if isinstance(metric_value, bool) or not isinstance(
                metric_value, (int, str)):
            raise ValidationError(
                "metric_value must be an integer or a verbatim "
                "label string")
        if isinstance(metric_value, str) and not metric_value.strip():
            raise ValidationError("metric_value must not be empty")
        return self._create(
            "ai_evaluation", "aieval",
            {"model_ref": model_ref, "metric_label": metric_label,
             "metric_value": metric_value, "reference_stub": True,
             "computed_here": False},
            actor, "ext_ai_evaluation_record")

    def get_ai_request(self, request_id, actor=None):
        """One AI request record. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_request_read",
                         target=request_id)
        return self._fetch("ai_request", request_id)

    def list_ai_requests(self, actor=None, case_id=None):
        """AI request records, optionally for one case.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_ai_request_read")
        if case_id is not None:
            return self._list("ai_request", case_id=case_id)
        return self._list("ai_request")

    def list_ai_reports(self, request_id, actor=None):
        """Report records for one AI request. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_request_read",
                         target=request_id)
        with self._lock:
            self._get("ai_request", request_id)
            return self._list("ai_report", request_id=request_id)

    def list_ai_evaluations(self, actor=None, model_ref=None):
        """AI evaluation records. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_evaluation_read")
        if model_ref is not None:
            return self._list("ai_evaluation", model_ref=model_ref)
        return self._list("ai_evaluation")

    # ================================================================
    # Managed cloud operations & application scaling platform
    # (build-extension entry, RE-JUDGED to reference form --
    # grounds in BATCH.md: the entry's own text names the
    # deployment layer itself, operated, which PLATFORM-LAYER.md
    # decision 6 assigns to the deployment layer; operating a
    # cloud is execution against infrastructure, not records.
    # What lands is the records layer in front of the platform:
    # environment records named by opaque reference, and the
    # operator's scaling and operations reports stored as
    # reported data, rolled up by deterministic counts)
    # ================================================================

    def register_environment(self, actor, environment_ref,
                             platform_label=None):
        """Record an operated environment by opaque reference.

        Action: config_write (admin, as configuration writes
        are). Id prefix: env-. Reference implementation: the
        environment is the platform operator's deployment,
        named here by a required, unique, opaque
        ``environment_ref``; nothing is hosted, operated, or
        provisioned by this record (``hosted_here: False``,
        ``operated_here: False``).
        """
        self._guard(actor, "config_write", "ext_environment_register")
        _non_empty(environment_ref, "environment_ref")
        _string_or_none(platform_label, "platform_label")
        with self._lock:
            for existing in self._list("environment"):
                if existing["environment_ref"] == environment_ref:
                    raise ValidationError(
                        "environment_ref %r already exists"
                        % (environment_ref,))
            return self._create(
                "environment", "env",
                {"environment_ref": environment_ref,
                 "platform_label": platform_label,
                 "reference_stub": True, "hosted_here": False,
                 "operated_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_environment_register")

    def record_scaling_report(self, actor, environment_id,
                              outcome_label, instances_reported=None):
        """Record a scaling outcome, verbatim as reported.

        Action: config_write. Id prefix: scale-. The report is
        the platform operator's own account of a scaling action
        it took elsewhere: the outcome label verbatim and its
        own reported instance count stored as data. Nothing was
        scaled here (``scaled_here: False``). A score-shaped
        outcome label is refused, as on every reported-outcome
        surface in this module.
        """
        self._guard(actor, "config_write", "ext_scaling_report_record",
                    target=environment_id)
        _non_empty(outcome_label, "outcome_label")
        _check_label_not_score_shaped(outcome_label, "outcome_label")
        if instances_reported is not None:
            _nonneg_int(instances_reported, "instances_reported")
        with self._lock:
            self._get("environment", environment_id)
            return self._create(
                "scaling_report", "scale",
                {"environment_id": environment_id,
                 "outcome_label": outcome_label,
                 "instances_reported": instances_reported,
                 "reference_stub": True, "scaled_here": False},
                actor, "ext_scaling_report_record")

    def record_operations_report(self, actor, environment_id,
                                 report_label, detail=None,
                                 events_reported=None):
        """Record an operations report, verbatim as reported.

        Action: config_write. Id prefix: opsrep-. The report is
        the platform operator's own account of operations it
        performed elsewhere: a label, optional verbatim
        ``detail`` text, and its own reported event count,
        stored as data. Nothing was operated here
        (``operated_here: False``).
        """
        self._guard(actor, "config_write",
                    "ext_operations_report_record", target=environment_id)
        _non_empty(report_label, "report_label")
        _string_or_none(detail, "detail")
        if events_reported is not None:
            _nonneg_int(events_reported, "events_reported")
        with self._lock:
            self._get("environment", environment_id)
            return self._create(
                "operations_report", "opsrep",
                {"environment_id": environment_id,
                 "report_label": report_label, "detail": detail,
                 "events_reported": events_reported,
                 "reference_stub": True, "operated_here": False},
                actor, "ext_operations_report_record")

    def get_environment(self, environment_id, actor=None):
        """One environment record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_environment_read",
                         target=environment_id)
        return self._fetch("environment", environment_id)

    def list_environments(self, actor=None):
        """All environment records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_environment_read")
        return self._list("environment")

    def list_scaling_reports(self, environment_id, actor=None):
        """Scaling report records for one environment.

        Action: config_read.
        """
        self._guard_read(actor, "config_read", "ext_environment_read",
                         target=environment_id)
        with self._lock:
            self._get("environment", environment_id)
            return self._list("scaling_report",
                              environment_id=environment_id)

    def list_operations_reports(self, environment_id, actor=None):
        """Operations report records for one environment.

        Action: config_read.
        """
        self._guard_read(actor, "config_read", "ext_environment_read",
                         target=environment_id)
        with self._lock:
            self._get("environment", environment_id)
            return self._list("operations_report",
                              environment_id=environment_id)

    def _environment_rollup(self, scaling_reports, operations_reports):
        """Per-environment rollup of the recorded platform reports.

        Derived at read, stored nowhere: for each environment
        id, the counts of its recorded scaling and operations
        reports and the sum of the operator's own reported
        instance counts. Sums of recorded values only -- nothing
        here measures a real platform.

        MUTATION DRILL NOTE: the scaling-count line of this
        method is the batch negative control's load-bearing
        derivation point -- recorded scaling reports must count
        in the rollup (see tests/README.md).
        """
        rollup = {}
        for report in scaling_reports:
            entry = rollup.setdefault(
                report["environment_id"],
                {"scaling_reports": 0, "operations_reports": 0,
                 "instances_reported_total": 0})
            entry["scaling_reports"] = (
                entry.get("scaling_reports", 0) + 1)
            entry["instances_reported_total"] += (
                report["instances_reported"] or 0)
        for report in operations_reports:
            entry = rollup.setdefault(
                report["environment_id"],
                {"scaling_reports": 0, "operations_reports": 0,
                 "instances_reported_total": 0})
            entry["operations_reports"] = (
                entry.get("operations_reports", 0) + 1)
        return rollup

    def operations_summary(self, actor=None):
        """Per-environment rollup of recorded platform reports.

        Action: config_read. Derived at read, stored nowhere:
        every registered environment with its recorded scaling
        and operations report counts and the sum of the
        operator's own reported instance counts, plus totals
        over the raw report lists. Counts and sums of recorded
        reports only; the platform itself is operated elsewhere
        (``operated_here: False`` stated on the view).
        """
        self._guard_read(actor, "config_read", "ext_operations_summary")
        with self._lock:
            environments = self._list("environment")
            scaling = self._list("scaling_report")
            operations = self._list("operations_report")
            rollup = self._environment_rollup(scaling, operations)
            rows = []
            for environment in environments:
                entry = rollup.get(
                    environment["id"],
                    {"scaling_reports": 0, "operations_reports": 0,
                     "instances_reported_total": 0})
                rows.append({
                    "environment_id": environment["id"],
                    "environment_ref": environment["environment_ref"],
                    "scaling_reports": entry["scaling_reports"],
                    "operations_reports": entry["operations_reports"],
                    "instances_reported_total": (
                        entry["instances_reported_total"]),
                })
            return {
                "method": "recorded_operations_counts",
                "derived": True,
                "operated_here": False,
                "environments": rows,
                "total_scaling_reports": len(scaling),
                "total_operations_reports": len(operations),
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
