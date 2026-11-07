"""Final GAPS batch extensions for the Development Tools untiered set.

Clean-room, standard-library-only extensions for the 7 open
entries of the GAPS.md section "Untiered Set 6 — Development
Tools (7 forks, tier null)" (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module wraps a
:class:`~devtools.store.DevToolsStore`; every core module is
untouched and byte-identical to the shipped build.

**Tier discipline, carried onto the new surface:** this set is
untiered — the source publishes no FedRAMP impact level for its
forks — so nothing in this module asserts a baseline, assigns a
tier, or draws a CMMC equivalence. No extension record or derived
view carries a tier, baseline, or impact-level key; that is
pinned by a recursive scan in the batch tests, exactly as the
founding set's sheets pin ``cmmc_tier: null``.

Honesty of form, per the batch pattern: an "engine" here is its
in-substrate form — records plus deterministic derivations over
the group's OWN records. Nothing in this module generates code,
runs an agent, hosts a workspace, converts code, gates a live
pipeline, or scans content.

- **AI code-generation & AI-agent development engines** are
  RE-JUDGED from their drafted build-extension disposition to a
  labeled reference implementation (grounds in ``BATCH.md``):
  the entry names the models and agent runtimes themselves, and
  the founding spec states this build contains no inference of
  any kind. What lands is request records plus reported outcome
  records holding opaque result references — ``reference_stub:
  True``, ``inference_here: False``, ``generated_here: False``,
  ``agent_executed_here: False``.
- **Cloud development environments (hosted IDE workspaces)**
  land as workspace records over core projects: a declaration of
  the workspace an external platform hosts, with the documented
  access modes (browser / SSH — Replit's own access prose)
  recorded as labels, plus session records whose statuses are
  reported verbatim. ``hosted_here: False``,
  ``provisioned_here: False``, ``filesystem_held_here: False`` —
  no workspace is hosted, provisioned, or stored here.
- **Legacy modernization & code-conversion engines** land as
  conversion job records whose stages are the five steps
  Moderniza's own description names (Blueprint, Contract, Code,
  Testing, Deploy), held as data. Stage outcomes are recorded as
  reported labels; the job view derives each stage's latest
  reported status at read. Source and target code are opaque
  references with optional SHA-256 digests — code itself is
  never accepted or held (``converted_here: False``,
  ``code_held_here: False``).
- **CI/CD governance & promotion-gating engines** land as
  gate-check records and promotion records over the substrate's
  own build / review / deployment records: a check outcome is a
  label reported about a recorded subject, and a promotion's
  current reported state derives at read from its recorded
  outcome records (including the mismatch and stalled outcomes
  KineticCode's prose names as notification cases). Nothing is
  gated or enforced against a live pipeline (``gated_here:
  False``, ``enforced_here: False``, ``promoted_here: False``).
- **Secrets & sensitive-data detection engines** ship as the
  labeled reference implementation their triage drafted:
  scan-request records plus reported finding records
  (``reference_stub: True``, ``scanned_here: False``,
  ``detected_here: False``). Detection is an engine run over
  content, and this substrate never holds code content — the
  artifact registry's checksums-only discipline is unchanged —
  so findings arrive as reports, never as detections made here.
- **Pipeline governance configuration records** land as
  governance policy records: gating rules, approval
  requirements, coverage thresholds, and promotion sequences
  held as configuration data (KineticCode's strict sequential
  Dev, Test, Stage, Prod promotion is the recorded shape).
  Definitions as data — a policy is never evaluated or enforced
  against a live pipeline (``enforced_here: False``,
  ``executed_here: False``).
- **Fork excess: customer support platform** lands as support
  case records over core projects. The founding union spec
  assigns this function to another category's union; the gap
  was registered in this section, so it closes here in records
  form: cases on the four channels Elixium's description names
  (in-app chat, support tickets, support email, support phone),
  channels recorded as labels with ``reference_transport:
  True``, event labels stored verbatim, and the case's current
  state derived at read. No message content can exist on any
  record (``messages_held_here: False``,
  ``delivered_here: False``).

Doctrines carried from the core: opaque ``*_ref`` strings only;
derived-never-stored for every computed value (conversion stage
status, promotion state, support case state, workspace session
state are computed at call time and stored nowhere); validation
fully before mutation, so a failed operation consumes no id and
changes nothing; append-only audit on the core store's log with
``ext_``-prefixed actions for extension mutations and denied
attempts audited as ``<action>:denied``, exactly as the core
store does; RBAC via :mod:`devtools.access`, enforced before
any state change or id allocation. Plain-string actors carry
identity but no role, so — as in the core store — there is
nothing to enforce against at this layer for them.

RBAC action mapping (the core action set is fixed): AI request
and outcome records ride ``project_write`` / ``project_read``
(registry-level records about a project); workspaces and
promotions ride the deployment family (the environment
surface); conversion jobs and gate checks ride the build
family; detection scan requests and findings ride the review
family (code-examination records); governance policies ride the
project family; support cases and events ride the issue family.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import _validate_non_empty, _validate_optional_str

CONVERSION_STAGES = ("blueprint", "contract", "code", "testing", "deploy")
CONVERSION_STAGE_STATUSES = (
    "reported_pending", "reported_in_progress",
    "reported_completed", "reported_failed",
)
CONVERSION_VIEW_METHOD = "derived_from_recorded_stage_outcomes"
AI_REQUEST_KINDS = ("code_generation", "agent_task")
WORKSPACE_ACCESS_MODES = ("browser", "ssh")
WORKSPACE_SESSION_STATUSES = (
    "reported_active", "reported_idle", "reported_closed",
)
GATE_KINDS = ("pull_request", "coverage", "approval", "promotion")
GATE_OUTCOMES = ("reported_passed", "reported_failed", "reported_waived")
PROMOTION_OUTCOMES = (
    "reported_promoted", "reported_blocked",
    "reported_mismatch", "reported_stalled",
)
GOVERNANCE_RULE_KINDS = ("gate", "approval", "coverage", "promotion")
DETECTION_FINDING_KINDS = (
    "secret", "token", "credential",
    "cui_marking", "fci_marking", "risky_pattern",
)
SUPPORT_CHANNELS = (
    "in_app_chat", "support_ticket", "support_email", "support_phone",
)
SUPPORT_EVENT_LABELS = (
    "opened", "responded", "escalated", "resolved", "closed",
)

_HEX = set("0123456789abcdef")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_digest(value, what):
    """An optional SHA-256 digest: 64 lowercase hex characters."""
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in _HEX for ch in value)
    ):
        raise ValidationError("%s must be a SHA-256 hex digest" % (what,))
    return value


def _validate_label_list(values, allowed, what):
    if not isinstance(values, list) or not values:
        raise ValidationError("%s must be a non-empty list" % (what,))
    result = []
    for value in values:
        if value not in allowed:
            raise ValidationError(
                "%s entries must be one of %s" % (what, ", ".join(allowed))
            )
        if value not in result:
            result.append(value)
    return result


class DevToolsExtensions:
    """Extension surface for the Untiered Set 6 final GAPS batch unit.

    Wraps a :class:`DevToolsStore`. All extension records live in
    this object; the core store's record sets are never written
    by this class (core records are only read, to bind extension
    records to real projects / builds / reviews / environments /
    deployments, and to append to the core audit log).
    """

    def __init__(self, store):
        self.store = store
        self._ai_requests = {}
        self._ai_outcomes = {}
        self._workspaces = {}
        self._workspace_sessions = {}
        self._conversion_jobs = {}
        self._conversion_stages = {}
        self._gate_checks = {}
        self._promotions = {}
        self._promotion_outcomes = {}
        self._references = {}
        self._detection_findings = {}
        self._governance_policies = {}
        self._support_cases = {}
        self._support_events = {}
        self._counters = {
            "air": 0, "aio": 0, "wsp": 0, "wss": 0, "cnv": 0,
            "cns": 0, "gtc": 0, "prm": 0, "pro": 0, "ref": 0,
            "dtf": 0, "gov": 0, "sup": 0, "sev": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(
                actor_name(actor), action, target, details=details
            )

    def _enforce(self, actor, action, target):
        """Enforce for a User actor; audit the denied attempt, then raise."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % (action,), target)
                raise

    def _require_actor(self, actor, action, target):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,)
            )
        self._enforce(actor, action, target)

    def _maybe_require(self, actor, action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    @staticmethod
    def _copy(record):
        return copy.deepcopy(record)

    def _get(self, table, record_id, what):
        rec = table.get(record_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return rec

    def _list(self, table, project_id=None):
        records = sorted(
            table.values(), key=lambda r: int(r["id"].rsplit("-", 1)[1])
        )
        if project_id is not None:
            records = [r for r in records if r.get("project_id") == project_id]
        return [self._copy(r) for r in records]

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    # -- AI code-generation & AI-agent engines (reference) -------------

    def record_ai_request(self, project_id, kind, request_ref, actor,
                          model_ref=None):
        """Record an AI generation / agent request. Action: project_write.

        REFERENCE implementation: the request is a record about
        an external model or agent runtime. Nothing is inferred,
        generated, or executed here; the model's output, if any,
        arrives later as a reported outcome holding an opaque
        result reference.
        """
        self._require_actor(actor, "project_write", project_id)
        if kind not in AI_REQUEST_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(AI_REQUEST_KINDS),)
            )
        _validate_non_empty(request_ref, "request_ref")
        _validate_optional_str(model_ref, "model_ref")
        with self._lock:
            self._core_project(project_id)
            request_id = self._next_id("air")
            record = {
                "id": request_id,
                "project_id": project_id,
                "kind": kind,
                "request_ref": request_ref,
                "model_ref": model_ref,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "inference_here": False,
                "generated_here": False,
                "agent_executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ai_requests[request_id] = record
            self._audit(actor, "ext_ai_request", request_id,
                        details={"project_id": project_id, "kind": kind})
            return self._copy(record)

    def record_ai_outcome(self, request_id, outcome_label, actor,
                          result_ref=None):
        """Record a reported outcome of an AI request. Action: project_write.

        The outcome label is the external runtime's report,
        stored verbatim and never interpreted; the output itself
        is an opaque reference — generated content is never held.
        """
        self._require_actor(actor, "project_write", request_id)
        _validate_non_empty(outcome_label, "outcome_label")
        _validate_optional_str(result_ref, "result_ref")
        with self._lock:
            self._get(self._ai_requests, request_id, "ai request")
            outcome_id = self._next_id("aio")
            record = {
                "id": outcome_id,
                "request_id": request_id,
                "outcome_label": outcome_label,
                "result_ref": result_ref,
                "reference_stub": True,
                "generated_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ai_outcomes[outcome_id] = record
            self._audit(actor, "ext_ai_outcome", outcome_id,
                        details={"request_id": request_id})
            return self._copy(record)

    def get_ai_request(self, request_id, actor=None):
        """Return one AI request record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(
                self._get(self._ai_requests, request_id, "ai request")
            )

    def list_ai_requests(self, project_id=None, actor=None):
        """Return AI request records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._list(self._ai_requests, project_id)

    def list_ai_outcomes(self, request_id=None, actor=None):
        """Return AI outcome records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._ai_outcomes.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if request_id is not None:
                records = [
                    r for r in records if r["request_id"] == request_id
                ]
            return [self._copy(r) for r in records]

    def ai_request_view(self, request_id, actor=None):
        """Derived view: request + its reported outcomes.

        The current reported outcome is the latest outcome
        record's label, derived at read; the stored request
        record carries no outcome field.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            request = self._copy(
                self._get(self._ai_requests, request_id, "ai request")
            )
            outcomes = [
                self._copy(r) for r in sorted(
                    self._ai_outcomes.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                ) if r["request_id"] == request_id
            ]
            return {
                "request": request,
                "outcomes": outcomes,
                "outcome_count": len(outcomes),
                "current_outcome_label": (
                    outcomes[-1]["outcome_label"] if outcomes else None
                ),
            }

    # -- Cloud development environments (workspace records) ------------

    def create_workspace(self, project_id, name, actor, access_modes=None):
        """Declare a hosted development workspace. Action: deployment_write.

        A workspace is a *declaration* record: the workspace
        itself is hosted by an external platform. The access
        modes are the fork's documented access prose (browser /
        SSH), recorded as labels. Nothing is hosted, provisioned,
        or stored here — a workspace's filesystem is never held.
        """
        self._require_actor(actor, "deployment_write", project_id)
        _validate_non_empty(name, "workspace name")
        modes = ["browser"]
        if access_modes is not None:
            modes = _validate_label_list(
                access_modes, WORKSPACE_ACCESS_MODES, "access_modes"
            )
        with self._lock:
            self._core_project(project_id)
            workspace_id = self._next_id("wsp")
            record = {
                "id": workspace_id,
                "project_id": project_id,
                "name": name,
                "access_modes": modes,
                "hosted_here": False,
                "provisioned_here": False,
                "filesystem_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workspaces[workspace_id] = record
            self._audit(actor, "ext_workspace_create", workspace_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def record_workspace_session(self, workspace_id, subject_ref,
                                 reported_status, actor):
        """Record a workspace session as reported. Action: deployment_write.

        The status is the hosting platform's report, stored
        verbatim; the session itself happened elsewhere.
        """
        self._require_actor(actor, "deployment_write", workspace_id)
        _validate_non_empty(subject_ref, "subject_ref")
        if reported_status not in WORKSPACE_SESSION_STATUSES:
            raise ValidationError(
                "reported_status must be one of %s"
                % (", ".join(WORKSPACE_SESSION_STATUSES),)
            )
        with self._lock:
            self._get(self._workspaces, workspace_id, "workspace")
            session_id = self._next_id("wss")
            record = {
                "id": session_id,
                "workspace_id": workspace_id,
                "subject_ref": subject_ref,
                "reported_status": reported_status,
                "hosted_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workspace_sessions[session_id] = record
            self._audit(actor, "ext_workspace_session", session_id,
                        details={"workspace_id": workspace_id})
            return self._copy(record)

    def get_workspace(self, workspace_id, actor=None):
        """Return one workspace record. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(
                self._get(self._workspaces, workspace_id, "workspace")
            )

    def list_workspaces(self, project_id=None, actor=None):
        """Return workspace records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._workspaces, project_id)

    def workspace_view(self, workspace_id, actor=None):
        """Derived view: workspace + session counts and latest state.

        The latest reported session status is derived at read
        from the session records; the stored workspace record
        carries no status field.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            workspace = self._copy(
                self._get(self._workspaces, workspace_id, "workspace")
            )
            sessions = [
                self._copy(r) for r in sorted(
                    self._workspace_sessions.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                ) if r["workspace_id"] == workspace_id
            ]
            counts = {}
            for session in sessions:
                label = session["reported_status"]
                counts[label] = counts.get(label, 0) + 1
            return {
                "workspace": workspace,
                "session_count": len(sessions),
                "sessions_by_reported_status": counts,
                "latest_reported_status": (
                    sessions[-1]["reported_status"] if sessions else None
                ),
            }

    # -- Legacy modernization & code conversion (job records) ----------

    def create_conversion_job(self, project_id, name, source_ref, actor,
                              target_ref=None, source_digest=None,
                              target_digest=None):
        """Create a code-conversion job record. Action: build_write.

        The job's stages are the five steps the fork's own
        description names — Blueprint, Contract, Code, Testing,
        Deploy — held as data. Source and target code are opaque
        references with optional SHA-256 digests; code itself is
        never accepted or held, and nothing is converted here.
        """
        self._require_actor(actor, "build_write", project_id)
        _validate_non_empty(name, "conversion job name")
        _validate_non_empty(source_ref, "source_ref")
        _validate_optional_str(target_ref, "target_ref")
        _validate_digest(source_digest, "source_digest")
        _validate_digest(target_digest, "target_digest")
        with self._lock:
            self._core_project(project_id)
            job_id = self._next_id("cnv")
            record = {
                "id": job_id,
                "project_id": project_id,
                "name": name,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "source_digest": source_digest,
                "target_digest": target_digest,
                "stages": list(CONVERSION_STAGES),
                "converted_here": False,
                "code_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._conversion_jobs[job_id] = record
            self._audit(actor, "ext_conversion_create", job_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def record_conversion_stage(self, job_id, stage, status_label, actor,
                                artifact_ref=None):
        """Record a conversion stage outcome as reported. Action: build_write.

        The stage must be one of the job's recorded stages; the
        status is the external conversion pipeline's report,
        stored verbatim.
        """
        self._require_actor(actor, "build_write", job_id)
        if status_label not in CONVERSION_STAGE_STATUSES:
            raise ValidationError(
                "status_label must be one of %s"
                % (", ".join(CONVERSION_STAGE_STATUSES),)
            )
        _validate_optional_str(artifact_ref, "artifact_ref")
        with self._lock:
            job = self._get(self._conversion_jobs, job_id, "conversion job")
            if stage not in job["stages"]:
                raise ValidationError(
                    "stage %r is not one of the job's recorded stages"
                    % (stage,)
                )
            record_id = self._next_id("cns")
            record = {
                "id": record_id,
                "job_id": job_id,
                "stage": stage,
                "status_label": status_label,
                "artifact_ref": artifact_ref,
                "converted_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._conversion_stages[record_id] = record
            self._audit(actor, "ext_conversion_stage", record_id,
                        details={"job_id": job_id, "stage": stage})
            return self._copy(record)

    @staticmethod
    def _derive_conversion_stage(outcomes):
        """The current reported status of one conversion stage.

        ``outcomes`` are the stage's outcome records in recorded
        order; the LATEST recorded outcome decides. Returns None
        when the stage has no outcome records yet.

        MUTATION DRILL NOTE: this derivation is the batch's
        signature seam — deriving from the earliest outcome
        instead is the mutant the negative control guards
        against (see tests/README.md).
        """
        if not outcomes:
            return None
        return outcomes[-1]["status_label"]

    def get_conversion_job(self, job_id, actor=None):
        """Return one conversion job record. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy(
                self._get(self._conversion_jobs, job_id, "conversion job")
            )

    def list_conversion_jobs(self, project_id=None, actor=None):
        """Return conversion job records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._conversion_jobs, project_id)

    def conversion_job_view(self, job_id, actor=None):
        """Derived view: per-stage latest reported status + overall.

        Derived at read from the recorded stage outcomes; the
        stored job record carries no status field. Overall:
        ``not_started`` (no outcomes), ``failed`` (any stage's
        latest is reported_failed), ``completed`` (every stage's
        latest is reported_completed), else ``in_progress``.
        """
        self._maybe_require(actor, "build_read")
        with self._lock:
            job = self._copy(
                self._get(self._conversion_jobs, job_id, "conversion job")
            )
            ordered = sorted(
                self._conversion_stages.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            stages = {}
            for stage in job["stages"]:
                outcomes = [
                    r for r in ordered
                    if r["job_id"] == job_id and r["stage"] == stage
                ]
                stages[stage] = self._derive_conversion_stage(outcomes)
            latest = [s for s in stages.values() if s is not None]
            if not latest:
                overall = "not_started"
            elif "reported_failed" in latest:
                overall = "failed"
            elif len(latest) == len(job["stages"]) and all(
                s == "reported_completed" for s in latest
            ):
                overall = "completed"
            else:
                overall = "in_progress"
            return {
                "job": job,
                "stages": stages,
                "overall": overall,
                "derivation_method": CONVERSION_VIEW_METHOD,
            }

    # -- CI/CD governance & promotion gating (records over core) -------

    def record_gate_check(self, project_id, gate_kind, actor,
                          outcome_label=None, check_ref=None,
                          policy_id=None, subject_build_id=None,
                          subject_review_id=None, subject_deployment_id=None):
        """Record a governance gate check over a core record.

        Action: build_write. The check is a record about a
        recorded subject (a core build, review, or deployment of
        the same project); its outcome is a label reported by the
        external gating engine, stored verbatim. Nothing is gated
        or enforced here — the check does not change its subject
        (pinned by test).
        """
        self._require_actor(actor, "build_write", project_id)
        if gate_kind not in GATE_KINDS:
            raise ValidationError(
                "gate_kind must be one of %s" % (", ".join(GATE_KINDS),)
            )
        if outcome_label is not None and outcome_label not in GATE_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(GATE_OUTCOMES),)
            )
        _validate_optional_str(check_ref, "check_ref")
        subjects = [
            s for s in (subject_build_id, subject_review_id,
                        subject_deployment_id) if s is not None
        ]
        if len(subjects) > 1:
            raise ValidationError(
                "a gate check names at most one subject record"
            )
        with self._lock:
            self._core_project(project_id)
            if policy_id is not None:
                policy = self._get(
                    self._governance_policies, policy_id, "governance policy"
                )
                if policy["project_id"] != project_id:
                    raise ValidationError(
                        "governance policy %r belongs to another project"
                        % (policy_id,)
                    )
            if subject_build_id is not None:
                subject = self.store.get_build(subject_build_id)
                if subject["project_id"] != project_id:
                    raise ValidationError(
                        "build %r belongs to another project"
                        % (subject_build_id,)
                    )
            if subject_review_id is not None:
                subject = self.store.get_review(subject_review_id)
                if subject["project_id"] != project_id:
                    raise ValidationError(
                        "review %r belongs to another project"
                        % (subject_review_id,)
                    )
            if subject_deployment_id is not None:
                found = None
                for dep in self.store.list_deployments():
                    if dep["id"] == subject_deployment_id:
                        found = dep
                        break
                if found is None:
                    raise NotFoundError(
                        "deployment not found: %r" % (subject_deployment_id,)
                    )
                if found["project_id"] != project_id:
                    raise ValidationError(
                        "deployment %r belongs to another project"
                        % (subject_deployment_id,)
                    )
            check_id = self._next_id("gtc")
            record = {
                "id": check_id,
                "project_id": project_id,
                "gate_kind": gate_kind,
                "outcome_label": outcome_label,
                "check_ref": check_ref,
                "policy_id": policy_id,
                "subject_build_id": subject_build_id,
                "subject_review_id": subject_review_id,
                "subject_deployment_id": subject_deployment_id,
                "gated_here": False,
                "enforced_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gate_checks[check_id] = record
            self._audit(actor, "ext_gate_check", check_id,
                        details={"project_id": project_id,
                                 "gate_kind": gate_kind})
            return self._copy(record)

    def list_gate_checks(self, project_id=None, actor=None):
        """Return gate check records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._gate_checks, project_id)

    def record_promotion(self, project_id, from_environment_id,
                         to_environment_id, actor, release_id=None,
                         policy_id=None):
        """Record a promotion between two core environments.

        Action: deployment_write. A promotion is a record about
        recorded environments; nothing is promoted here. The
        promotion sequence a governance policy records is data
        the record may cite — it is not enforced.
        """
        self._require_actor(actor, "deployment_write", project_id)
        if from_environment_id == to_environment_id:
            raise ValidationError(
                "a promotion names two different environments"
            )
        with self._lock:
            self._core_project(project_id)
            self.store.get_environment(from_environment_id)
            self.store.get_environment(to_environment_id)
            if release_id is not None:
                release = self.store.get_release(release_id)
                if release["project_id"] != project_id:
                    raise ValidationError(
                        "release %r belongs to another project"
                        % (release_id,)
                    )
            if policy_id is not None:
                policy = self._get(
                    self._governance_policies, policy_id, "governance policy"
                )
                if policy["project_id"] != project_id:
                    raise ValidationError(
                        "governance policy %r belongs to another project"
                        % (policy_id,)
                    )
            promotion_id = self._next_id("prm")
            record = {
                "id": promotion_id,
                "project_id": project_id,
                "from_environment_id": from_environment_id,
                "to_environment_id": to_environment_id,
                "release_id": release_id,
                "policy_id": policy_id,
                "promoted_here": False,
                "enforced_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._promotions[promotion_id] = record
            self._audit(actor, "ext_promotion_record", promotion_id,
                        details={"project_id": project_id})
            return self._copy(record)

    def record_promotion_outcome(self, promotion_id, outcome_label, actor):
        """Record a promotion outcome as reported. Action: deployment_write.

        The label is the external pipeline's report — including
        the mismatch and stalled outcomes the fork's prose names
        as notification cases — stored verbatim.
        """
        self._require_actor(actor, "deployment_write", promotion_id)
        if outcome_label not in PROMOTION_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(PROMOTION_OUTCOMES),)
            )
        with self._lock:
            self._get(self._promotions, promotion_id, "promotion")
            outcome_id = self._next_id("pro")
            record = {
                "id": outcome_id,
                "promotion_id": promotion_id,
                "outcome_label": outcome_label,
                "promoted_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._promotion_outcomes[outcome_id] = record
            self._audit(actor, "ext_promotion_outcome", outcome_id,
                        details={"promotion_id": promotion_id})
            return self._copy(record)

    def promotion_view(self, promotion_id, actor=None):
        """Derived view: promotion + outcomes + current reported state.

        The current state is the latest recorded outcome's
        label, derived at read (``recorded`` before any
        outcome); the stored promotion record carries no status
        field.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            promotion = self._copy(
                self._get(self._promotions, promotion_id, "promotion")
            )
            outcomes = [
                self._copy(r) for r in sorted(
                    self._promotion_outcomes.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                ) if r["promotion_id"] == promotion_id
            ]
            return {
                "promotion": promotion,
                "outcomes": outcomes,
                "outcome_count": len(outcomes),
                "current_outcome_label": (
                    outcomes[-1]["outcome_label"] if outcomes else None
                ),
                "current_state": (
                    outcomes[-1]["outcome_label"] if outcomes else "recorded"
                ),
            }

    def list_promotions(self, project_id=None, actor=None):
        """Return promotion records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._promotions, project_id)

    # -- Pipeline governance configuration records ---------------------

    def create_governance_policy(self, project_id, name, rules, actor,
                                 promotion_sequence=None,
                                 coverage_threshold=None):
        """Create a pipeline governance policy record.

        Action: project_write. The policy holds governance
        configuration AS DATA: gating rules, approval
        requirements, coverage thresholds, and promotion
        policies. A rule is ``{rule_ref, kind, requirement}``
        with kind in gate / approval / coverage / promotion.
        The promotion sequence is a list of environment names
        (the fork's strict sequential Dev, Test, Stage, Prod
        shape). Nothing here is evaluated or enforced against a
        live pipeline.
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(name, "policy name")
        if not isinstance(rules, list) or not rules:
            raise ValidationError("rules must be a non-empty list")
        normalized_rules = []
        seen_refs = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValidationError("each rule must be an object")
            rule_ref = _validate_non_empty(rule.get("rule_ref"), "rule_ref")
            kind = rule.get("kind")
            if kind not in GOVERNANCE_RULE_KINDS:
                raise ValidationError(
                    "rule kind must be one of %s"
                    % (", ".join(GOVERNANCE_RULE_KINDS),)
                )
            requirement = _validate_non_empty(
                rule.get("requirement"), "requirement"
            )
            if rule_ref in seen_refs:
                raise ValidationError("duplicate rule_ref %r" % (rule_ref,))
            seen_refs.add(rule_ref)
            normalized_rules.append({
                "rule_ref": rule_ref,
                "kind": kind,
                "requirement": requirement,
            })
        sequence = None
        if promotion_sequence is not None:
            if not isinstance(promotion_sequence, list) \
                    or not promotion_sequence:
                raise ValidationError(
                    "promotion_sequence must be a non-empty list"
                )
            sequence = []
            for step in promotion_sequence:
                _validate_non_empty(step, "promotion step")
                if step in sequence:
                    raise ValidationError(
                        "duplicate promotion step %r" % (step,)
                    )
                sequence.append(step)
        if coverage_threshold is not None:
            if isinstance(coverage_threshold, bool) \
                    or not isinstance(coverage_threshold, int):
                raise ValidationError(
                    "coverage_threshold must be an integer percentage"
                )
            if coverage_threshold < 0 or coverage_threshold > 100:
                raise ValidationError(
                    "coverage_threshold must be between 0 and 100"
                )
        with self._lock:
            self._core_project(project_id)
            policy_id = self._next_id("gov")
            record = {
                "id": policy_id,
                "project_id": project_id,
                "name": name,
                "rules": normalized_rules,
                "promotion_sequence": sequence,
                "coverage_threshold": coverage_threshold,
                "enforced_here": False,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._governance_policies[policy_id] = record
            self._audit(actor, "ext_governance_policy_create", policy_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_governance_policy(self, policy_id, actor=None):
        """Return one governance policy record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(self._get(
                self._governance_policies, policy_id, "governance policy"
            ))

    def list_governance_policies(self, project_id=None, actor=None):
        """Return governance policy records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._list(self._governance_policies, project_id)

    # -- Secrets & sensitive-data detection engines (reference) --------

    def record_detection_scan(self, project_id, scan_ref, actor,
                              target_ref=None):
        """Record a detection scan request. Action: review_write.

        REFERENCE implementation: a scan is an engine run over
        code content, and this substrate never holds code
        content — so a scan exists here only as a request record
        about an external scanner. Findings arrive as reports
        (``record_detection_finding``), never as detections made
        here.
        """
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(scan_ref, "scan_ref")
        _validate_optional_str(target_ref, "target_ref")
        with self._lock:
            self._core_project(project_id)
            scan_id = self._next_id("ref")
            record = {
                "id": scan_id,
                "kind": "detection_scan",
                "project_id": project_id,
                "scan_ref": scan_ref,
                "target_ref": target_ref,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "scanned_here": False,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._references[scan_id] = record
            self._audit(actor, "ext_detection_scan", scan_id,
                        details={"project_id": project_id})
            return self._copy(record)

    def record_detection_finding(self, scan_id, finding_kind, location_ref,
                                 actor, severity_label=None):
        """Record a detection finding as reported. Action: review_write.

        The finding kind is one of the categories the fork's
        prose names (secrets, tokens, credentials, CUI/FCI
        markings, risky patterns); the location is an opaque
        reference — the flagged content itself is never held.
        The severity label is the scanner's report, verbatim.
        """
        self._require_actor(actor, "review_write", scan_id)
        if finding_kind not in DETECTION_FINDING_KINDS:
            raise ValidationError(
                "finding_kind must be one of %s"
                % (", ".join(DETECTION_FINDING_KINDS),)
            )
        _validate_non_empty(location_ref, "location_ref")
        _validate_optional_str(severity_label, "severity_label")
        with self._lock:
            scan = self._get(self._references, scan_id, "reference record")
            if scan.get("kind") != "detection_scan":
                raise ValidationError(
                    "record %r is not a detection scan" % (scan_id,)
                )
            finding_id = self._next_id("dtf")
            record = {
                "id": finding_id,
                "scan_id": scan_id,
                "project_id": scan["project_id"],
                "finding_kind": finding_kind,
                "location_ref": location_ref,
                "severity_label": severity_label,
                "reference_stub": True,
                "detected_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._detection_findings[finding_id] = record
            self._audit(actor, "ext_detection_finding", finding_id,
                        details={"scan_id": scan_id,
                                 "finding_kind": finding_kind})
            return self._copy(record)

    def get_detection_scan(self, scan_id, actor=None):
        """Return one detection scan reference record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._copy(
                self._get(self._references, scan_id, "reference record")
            )

    def list_detection_findings(self, scan_id=None, actor=None):
        """Return detection finding records. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            records = sorted(
                self._detection_findings.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if scan_id is not None:
                records = [r for r in records if r["scan_id"] == scan_id]
            return [self._copy(r) for r in records]

    # -- Fork excess: customer support platform (case records) ---------

    def create_support_case(self, project_id, channel, actor,
                            subject_ref=None):
        """Open a support case record. Action: issue_write.

        The channel is one of the four the fork's description
        names, recorded as a label; the channel itself is a
        transport this build does not operate
        (``reference_transport: True``). No message content can
        exist on a case record. The stored case carries no
        status — its state derives from its event records.
        """
        self._require_actor(actor, "issue_write", project_id)
        if channel not in SUPPORT_CHANNELS:
            raise ValidationError(
                "channel must be one of %s" % (", ".join(SUPPORT_CHANNELS),)
            )
        _validate_optional_str(subject_ref, "subject_ref")
        with self._lock:
            self._core_project(project_id)
            case_id = self._next_id("sup")
            record = {
                "id": case_id,
                "project_id": project_id,
                "channel": channel,
                "subject_ref": subject_ref,
                "reference_transport": True,
                "messages_held_here": False,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._support_cases[case_id] = record
            self._audit(actor, "ext_support_case_create", case_id,
                        details={"project_id": project_id,
                                 "channel": channel})
            return self._copy(record)

    def record_support_event(self, case_id, event_label, actor):
        """Record a support case event label verbatim. Action: issue_write."""
        self._require_actor(actor, "issue_write", case_id)
        if event_label not in SUPPORT_EVENT_LABELS:
            raise ValidationError(
                "event_label must be one of %s"
                % (", ".join(SUPPORT_EVENT_LABELS),)
            )
        with self._lock:
            self._get(self._support_cases, case_id, "support case")
            event_id = self._next_id("sev")
            record = {
                "id": event_id,
                "case_id": case_id,
                "event_label": event_label,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._support_events[event_id] = record
            self._audit(actor, "ext_support_event", event_id,
                        details={"case_id": case_id})
            return self._copy(record)

    @staticmethod
    def _derive_support_state(events):
        """A support case's current state: its latest event label.

        ``events`` are the case's event records in recorded
        order; a case with no events is ``opened``.
        """
        if not events:
            return "opened"
        return events[-1]["event_label"]

    def support_case_view(self, case_id, actor=None):
        """Derived view: case + events + current state, derived at read.

        The stored case record carries no status field; the
        state comes from the recorded event labels only.
        """
        self._maybe_require(actor, "issue_read")
        with self._lock:
            case = self._copy(
                self._get(self._support_cases, case_id, "support case")
            )
            events = [
                self._copy(r) for r in sorted(
                    self._support_events.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                ) if r["case_id"] == case_id
            ]
            return {
                "case": case,
                "events": events,
                "event_count": len(events),
                "current_state": self._derive_support_state(events),
            }

    def list_support_cases(self, project_id=None, actor=None):
        """Return support case records. Action: issue_read."""
        self._maybe_require(actor, "issue_read")
        with self._lock:
            return self._list(self._support_cases, project_id)
