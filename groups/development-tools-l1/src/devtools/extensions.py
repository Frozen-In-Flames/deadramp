"""Final GAPS batch extensions for the Development Tools L1 build.

Clean-room, standard-library-only extensions for the 9 open
Extended entries of Group 17 (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module wraps a
:class:`~devtools.store.DevToolsStore`; every core module is
untouched and byte-identical to the shipped build.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records. Nothing in this module executes a
pipeline, compiles code, stores a git object or an artifact
binary, applies a configuration, assesses compliance, executes a
model, authors content, or provisions anything.

- **CI/CD execution engines** land as pipeline run *request*
  records bound to core build records (the core build record,
  with its config held as a record, is the pipeline definition
  this tier's substrate carries) plus run *outcome* records
  whose status is the external runner's report, stored verbatim.
  Every record carries ``executed_here: False``; this build runs
  nothing. A run's current reported status is derived at read
  from its outcome records and stored nowhere.
- **Compilers & build toolchains** land as toolchain registry
  records -- the declaration of the toolchain a real build used.
  No compiler ships.
- **Artifact binary storage backends** land as backend
  registration records plus artifact *custody* records that bind
  a core artifact to a backend, copying only the artifact
  record's SHA-256 checksum and recorded size. No content is
  accepted or held (``content_held_here: False``); the core
  registry's verify-by-content function is unchanged and remains
  the only verification path.
- The six **stub-engine** entries (code hosting internals,
  configuration-as-code execution & orchestration, compliance
  assessment & KSI status automation, business modeling &
  automation, course & content authoring tools, landing-zone /
  tenant provisioning & hosted platform operations) ship as
  labeled reference implementations: records carry
  ``reference_stub: True`` and status
  ``recorded_reference_only``. Creating one changes no core
  record; that is pinned by test.

Doctrines carried from the core: opaque ``*_ref`` strings only;
derived-never-stored for every computed value (run views,
assessment views, backend summaries are computed at call time
and stored nowhere); validation fully before mutation, so a
failed operation consumes no id and changes nothing; append-only
audit on the core store's log with ``ext_``-prefixed actions for
extension mutations and denied attempts audited as
``<action>:denied``, exactly as the core store does; RBAC via
:mod:`devtools.access`, enforced before any state change or id
allocation. Plain-string actors carry identity but no role, so
-- as in the core store -- there is nothing to enforce against
at this layer for them.

RBAC action mapping (the core action set is fixed): pipeline
run requests, run outcomes, and toolchains ride the build family
(``build_write`` / ``build_read``); storage backends and custody
records ride the artifact family; compliance assessment jobs
and status reports ride the review family (examination
records); stub reference records, branch records, apply
outcomes, model execution requests, and course records are
registry-level records about a project and ride
``project_write`` / ``project_read``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import (
    BUILD_STATUSES,
    _validate_non_empty,
    _validate_optional_str,
)

RUN_VIEW_METHOD = "latest_reported_outcome_over_run_outcome_records"
ASSESSMENT_VIEW_METHOD = "latest_reported_status_over_assessment_reports"
BACKEND_SUMMARY_METHOD = "derived_from_custody_records"

MODEL_REFERENCE_KINDS = ("business_model", "workflow_automation")
STORAGE_BACKEND_KINDS = ("object_store", "filesystem", "archive", "custom")

REFERENCE_KINDS = (
    "repository", "configuration", "model", "provisioning",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_negative_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be non-negative" % (what,))
    return value


class DevToolsExtensions:
    """Extension surface for the Group 17 final GAPS batch unit.

    Wraps a :class:`DevToolsStore`. All extension records live in
    this object; the core store's record sets are never written
    by this class (core records are only read, to bind extension
    records to real projects / builds / artifacts /
    environments, and to append to the core audit log).
    """

    def __init__(self, store):
        self.store = store
        self._pipeline_runs = {}
        self._run_outcomes = {}
        self._toolchains = {}
        self._storage_backends = {}
        self._custody = {}
        self._references = {}
        self._branches = {}
        self._apply_outcomes = {}
        self._assessment_jobs = {}
        self._assessment_reports = {}
        self._model_executions = {}
        self._courses = {}
        self._course_assets = {}
        self._course_outcomes = {}
        self._counters = {
            "run": 0, "out": 0, "tch": 0, "stb": 0, "plm": 0,
            "ref": 0, "brn": 0, "apl": 0, "asj": 0, "asr": 0,
            "exq": 0, "crs": 0, "ast": 0, "cou": 0,
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

    # -- CI/CD execution engines (request / outcome records) -----------

    def request_pipeline_run(self, project_id, actor, build_id=None,
                             runner_ref=None, stage_label=None):
        """Request a pipeline run. Action: build_write.

        A run *request* record: the request names the pipeline
        definition it runs against -- here the core build record
        whose config is held as a record -- and an opaque runner
        reference. Nothing executes (``executed_here: False``);
        the runner's result arrives later as an outcome record
        (see :meth:`record_run_outcome`). Recording a request
        changes no core record.
        """
        self._require_actor(actor, "build_write", project_id)
        _validate_optional_str(runner_ref, "runner_ref")
        _validate_optional_str(stage_label, "stage_label")
        with self._lock:
            self._core_project(project_id)
            if build_id is not None:
                build = self.store.get_build(build_id)
                if build["project_id"] != project_id:
                    raise ValidationError(
                        "build %r does not belong to project %r"
                        % (build_id, project_id)
                    )
            run_id = self._next_id("run")
            record = {
                "id": run_id,
                "project_id": project_id,
                "build_id": build_id,
                "runner_ref": runner_ref,
                "stage_label": stage_label,
                "executed_here": False,
                "requested_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pipeline_runs[run_id] = record
            self._audit(actor, "ext_pipeline_run_request", run_id,
                        details={"project_id": project_id,
                                 "build_id": build_id})
            return self._copy(record)

    def get_pipeline_run(self, run_id, actor=None):
        """Return one pipeline run request. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy(
                self._get(self._pipeline_runs, run_id, "pipeline run")
            )

    def list_pipeline_runs(self, project_id=None, actor=None):
        """Return pipeline run requests. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._pipeline_runs, project_id)

    def record_run_outcome(self, run_id, actor, status, runner_ref=None):
        """Record a run outcome reported by an external runner.

        Action: build_write. The status is the runner's report,
        recorded verbatim from the core build-status vocabulary;
        this build ran nothing (``executed_here: False`` on the
        record).
        """
        self._require_actor(actor, "build_write", run_id)
        if status not in BUILD_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(BUILD_STATUSES),)
            )
        _validate_optional_str(runner_ref, "runner_ref")
        with self._lock:
            run = self._get(self._pipeline_runs, run_id, "pipeline run")
            outcome_id = self._next_id("out")
            record = {
                "id": outcome_id,
                "run_id": run_id,
                "project_id": run["project_id"],
                "status": status,
                "runner_ref": runner_ref,
                "executed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._run_outcomes[outcome_id] = record
            self._audit(actor, "ext_pipeline_run_outcome", outcome_id,
                        details={"run_id": run_id, "status": status})
            return self._copy(record)

    def list_run_outcomes(self, run_id=None, actor=None):
        """Return run outcome records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            records = sorted(
                self._run_outcomes.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if run_id is not None:
                records = [r for r in records if r["run_id"] == run_id]
            return [self._copy(r) for r in records]

    def _derive_run_status(self, outcomes):
        """The run-status seam: a run's current reported status.

        ``outcomes`` are the run's outcome records in record
        order. The current status is the *latest* reported
        outcome's status, or ``requested`` when no outcome has
        been reported yet.

        MUTATION DRILL NOTE: this seam is the load-bearing
        invariant of the batch's fresh negative control -- a
        derivation that read the *earliest* outcome instead
        would keep reporting a superseded runner result (a run
        the runner later reported succeeded would still read
        failed). The mutant the drill rejects reads
        ``outcomes[0]``.
        """
        if not outcomes:
            return "requested"
        return outcomes[-1]["status"]

    def pipeline_run_view(self, run_id, actor=None):
        """Derive a pipeline run's current state at read.

        Action: build_read. The reported status is computed from
        the run's outcome records at call time (see
        :meth:`_derive_run_status`) and stored nowhere; the
        stored run request carries no status field.
        """
        self._maybe_require(actor, "build_read")
        with self._lock:
            run = self._get(self._pipeline_runs, run_id, "pipeline run")
            outcomes = [
                r for r in sorted(
                    self._run_outcomes.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                )
                if r["run_id"] == run_id
            ]
            return {
                "run_id": run_id,
                "project_id": run["project_id"],
                "build_id": run["build_id"],
                "reported_status": self._derive_run_status(outcomes),
                "outcome_count": len(outcomes),
                "executed_here": False,
                "method": RUN_VIEW_METHOD,
            }

    # -- Compilers & build toolchains (registry records) ---------------

    def register_toolchain(self, project_id, name, actor,
                           language=None, version_label=None):
        """Register a toolchain declaration. Action: build_write.

        The record declares the toolchain (name, language,
        version label) a real build used; no compiler exists in
        this build (``executed_here: False``).
        """
        self._require_actor(actor, "build_write", project_id)
        _validate_non_empty(name, "toolchain name")
        _validate_optional_str(language, "language")
        _validate_optional_str(version_label, "version_label")
        with self._lock:
            self._core_project(project_id)
            toolchain_id = self._next_id("tch")
            record = {
                "id": toolchain_id,
                "project_id": project_id,
                "name": name,
                "language": language,
                "version_label": version_label,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._toolchains[toolchain_id] = record
            self._audit(actor, "ext_toolchain_register", toolchain_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_toolchain(self, toolchain_id, actor=None):
        """Return one toolchain record. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy(
                self._get(self._toolchains, toolchain_id, "toolchain")
            )

    def list_toolchains(self, project_id=None, actor=None):
        """Return toolchain records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._toolchains, project_id)

    # -- Artifact binary storage backends (custody records) -------------

    def register_storage_backend(self, name, actor, kind="filesystem"):
        """Register a storage-backend record. Action: artifact_write.

        A backend here is a bookkeeping record: custody records
        bind core artifacts to it by checksum. This build holds
        no binary anywhere.
        """
        self._require_actor(
            actor, "artifact_write",
            name if isinstance(name, str) else "storage_backend",
        )
        _validate_non_empty(name, "storage backend name")
        if kind not in STORAGE_BACKEND_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(STORAGE_BACKEND_KINDS),)
            )
        with self._lock:
            backend_id = self._next_id("stb")
            record = {
                "id": backend_id,
                "name": name,
                "kind": kind,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._storage_backends[backend_id] = record
            self._audit(actor, "ext_storage_backend_register", backend_id,
                        details={"name": name, "kind": kind})
            return self._copy(record)

    def get_storage_backend(self, backend_id, actor=None):
        """Return one storage-backend record. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            return self._copy(
                self._get(self._storage_backends, backend_id, "storage backend")
            )

    def list_storage_backends(self, actor=None):
        """Return storage-backend records. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            return self._list(self._storage_backends)

    def record_artifact_custody(self, artifact_id, backend_id, actor,
                                custodian_ref=None):
        """Record the custody of a core artifact on a backend.

        Action: artifact_write. The custody record copies the
        core artifact record's SHA-256 checksum and recorded
        size -- and nothing else; no content is accepted or held
        (``content_held_here: False``). Verification stays the
        core registry's verify-by-content function, unchanged.
        """
        self._require_actor(actor, "artifact_write", artifact_id)
        _validate_optional_str(custodian_ref, "custodian_ref")
        with self._lock:
            artifact = self.store.get_artifact(artifact_id)
            self._get(self._storage_backends, backend_id, "storage backend")
            custody_id = self._next_id("plm")
            record = {
                "id": custody_id,
                "artifact_id": artifact_id,
                "backend_id": backend_id,
                "project_id": artifact["project_id"],
                "custodian_ref": custodian_ref,
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._custody[custody_id] = record
            self._audit(actor, "ext_artifact_custody", custody_id,
                        details={"artifact_id": artifact_id,
                                 "backend_id": backend_id})
            return self._copy(record)

    def list_artifact_custody(self, backend_id=None, artifact_id=None,
                              actor=None):
        """Return custody records. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            records = sorted(
                self._custody.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if backend_id is not None:
                records = [r for r in records if r["backend_id"] == backend_id]
            if artifact_id is not None:
                records = [r for r in records
                           if r["artifact_id"] == artifact_id]
            return [self._copy(r) for r in records]

    def storage_backend_summary(self, backend_id, actor=None):
        """Derive a backend's custody summary at read.

        Action: artifact_read. Counts and size totals are
        computed from the custody records at call time and
        stored nowhere. Artifacts registered checksum-only have
        no recorded size; they are counted separately as
        ``unknown_size_count`` rather than silently treated
        as 0.
        """
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            self._get(self._storage_backends, backend_id, "storage backend")
            custody = [r for r in self._custody.values()
                       if r["backend_id"] == backend_id]
            known_sizes = [r["size_bytes"] for r in custody
                           if r["size_bytes"] is not None]
            return {
                "backend_id": backend_id,
                "placements": len(custody),
                "total_size_bytes": sum(known_sizes),
                "unknown_size_count": len(custody) - len(known_sizes),
                "method": BACKEND_SUMMARY_METHOD,
            }

    # -- Stub engines: labeled reference implementations -----------------
    #
    # Each record carries reference_stub: True and status
    # "recorded_reference_only". Creating one changes no core
    # record (pinned by test); the audit entries are the core
    # log's own append-only record of the extension mutation.

    def _record_reference(self, kind, project_id, actor, fields,
                          audit_details):
        self._require_actor(actor, "project_write", project_id)
        with self._lock:
            self._core_project(project_id)
            reference_id = self._next_id("ref")
            record = {
                "id": reference_id,
                "kind": kind,
                "project_id": project_id,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            record.update(fields)
            self._references[reference_id] = record
            details = {"project_id": project_id, "kind": kind}
            details.update(audit_details)
            self._audit(actor, "ext_reference_record", reference_id,
                        details=details)
            return self._copy(record)

    def get_reference_record(self, reference_id, actor=None):
        """Return one reference record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(
                self._get(self._references, reference_id, "reference record")
            )

    def list_reference_records(self, kind=None, project_id=None, actor=None):
        """Return reference records, optionally filtered.

        Action: project_read.
        """
        self._maybe_require(actor, "project_read")
        if kind is not None and kind not in REFERENCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(REFERENCE_KINDS),)
            )
        with self._lock:
            records = sorted(
                self._references.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            if project_id is not None:
                records = [r for r in records
                           if r["project_id"] == project_id]
            return [self._copy(r) for r in records]

    # -- Code hosting internals (idx 175) --------------------------------

    def record_repository_reference(self, project_id, host_ref, actor,
                                    default_branch_label=None):
        """Reference record for code hosting internals.

        Action: project_write. Points at an external host by
        opaque reference; the repository is metadata only -- no
        git object storage, branching, or merging exists in this
        build (``stored_here: False``, ``merged_here: False``),
        and no record field can hold object content.
        """
        _validate_non_empty(host_ref, "host_ref")
        _validate_optional_str(default_branch_label, "default_branch_label")
        return self._record_reference(
            "repository", project_id, actor,
            {"host_ref": host_ref,
             "default_branch_label": default_branch_label,
             "stored_here": False,
             "merged_here": False},
            {"host_ref": host_ref},
        )

    def record_branch_record(self, reference_id, branch_ref, actor,
                             base_branch_label=None):
        """Record a branch of a referenced repository, as metadata.

        Action: project_write. The branch is a metadata record
        about the external host's branch; nothing is stored or
        merged here (``stored_here: False``,
        ``merged_here: False``).
        """
        self._require_actor(actor, "project_write", reference_id)
        _validate_non_empty(branch_ref, "branch_ref")
        _validate_optional_str(base_branch_label, "base_branch_label")
        with self._lock:
            reference = self._get(
                self._references, reference_id, "reference record"
            )
            if reference["kind"] != "repository":
                raise ValidationError(
                    "reference %r is not a repository reference"
                    % (reference_id,)
                )
            branch_id = self._next_id("brn")
            record = {
                "id": branch_id,
                "reference_id": reference_id,
                "project_id": reference["project_id"],
                "branch_ref": branch_ref,
                "base_branch_label": base_branch_label,
                "reference_stub": True,
                "stored_here": False,
                "merged_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._branches[branch_id] = record
            self._audit(actor, "ext_branch_record", branch_id,
                        details={"reference_id": reference_id,
                                 "branch_ref": branch_ref})
            return self._copy(record)

    def list_branch_records(self, reference_id=None, actor=None):
        """Return branch records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._branches.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if reference_id is not None:
                records = [r for r in records
                           if r["reference_id"] == reference_id]
            return [self._copy(r) for r in records]

    # -- Configuration-as-code execution & orchestration (idx 177) -------

    def record_configuration_reference(self, project_id, config_ref, actor,
                                       format_label=None):
        """Reference record for configuration-as-code execution.

        Action: project_write. The configuration is held as a
        definition (an opaque reference plus a format label) and
        is never applied or executed by this build
        (``applied_here: False``, ``executed_here: False``) --
        the registry never executes.
        """
        _validate_non_empty(config_ref, "config_ref")
        _validate_optional_str(format_label, "format_label")
        return self._record_reference(
            "configuration", project_id, actor,
            {"config_ref": config_ref,
             "format_label": format_label,
             "applied_here": False,
             "executed_here": False},
            {"config_ref": config_ref},
        )

    def record_apply_outcome(self, reference_id, outcome_label, actor):
        """Record an apply outcome reported for a configuration.

        Action: project_write. The outcome label is stored
        verbatim, as reported by the external configuration
        tooling; nothing was applied here
        (``applied_here: False``).
        """
        self._require_actor(actor, "project_write", reference_id)
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            reference = self._get(
                self._references, reference_id, "reference record"
            )
            if reference["kind"] != "configuration":
                raise ValidationError(
                    "reference %r is not a configuration reference"
                    % (reference_id,)
                )
            outcome_id = self._next_id("apl")
            record = {
                "id": outcome_id,
                "reference_id": reference_id,
                "project_id": reference["project_id"],
                "outcome_label": outcome_label,
                "reference_stub": True,
                "applied_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._apply_outcomes[outcome_id] = record
            self._audit(actor, "ext_apply_outcome_record", outcome_id,
                        details={"reference_id": reference_id,
                                 "outcome_label": outcome_label})
            return self._copy(record)

    def list_apply_outcomes(self, reference_id=None, actor=None):
        """Return apply outcome records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._apply_outcomes.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if reference_id is not None:
                records = [r for r in records
                           if r["reference_id"] == reference_id]
            return [self._copy(r) for r in records]

    # -- Compliance assessment & KSI status automation (idx 178) ---------

    def create_assessment_job(self, project_id, framework_ref, actor,
                              ksi_ref=None):
        """Create a compliance assessment job record.

        Action: review_write. The job records that an external
        assessor is assessing the project against an opaque
        framework reference (and, for 20x, an opaque KSI
        reference); nothing is assessed in this build
        (``assessed_here: False``). Reported statuses arrive as
        records (see :meth:`record_assessment_status`).
        """
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(framework_ref, "framework_ref")
        _validate_optional_str(ksi_ref, "ksi_ref")
        with self._lock:
            self._core_project(project_id)
            job_id = self._next_id("asj")
            record = {
                "id": job_id,
                "project_id": project_id,
                "framework_ref": framework_ref,
                "ksi_ref": ksi_ref,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "assessed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessment_jobs[job_id] = record
            self._audit(actor, "ext_assessment_job_create", job_id,
                        details={"project_id": project_id,
                                 "framework_ref": framework_ref})
            return self._copy(record)

    def get_assessment_job(self, job_id, actor=None):
        """Return one assessment job record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._copy(
                self._get(self._assessment_jobs, job_id, "assessment job")
            )

    def list_assessment_jobs(self, project_id=None, actor=None):
        """Return assessment job records. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._list(self._assessment_jobs, project_id)

    def record_assessment_status(self, job_id, status_label, actor):
        """Record an assessment status reported by an assessor.

        Action: review_write. The status label is stored
        verbatim, exactly as reported; it is never interpreted
        and no compliance score is computed from it anywhere in
        this build (``assessed_here: False``).
        """
        self._require_actor(actor, "review_write", job_id)
        _validate_non_empty(status_label, "status_label")
        with self._lock:
            job = self._get(self._assessment_jobs, job_id, "assessment job")
            report_id = self._next_id("asr")
            record = {
                "id": report_id,
                "job_id": job_id,
                "project_id": job["project_id"],
                "status_label": status_label,
                "reference_stub": True,
                "assessed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessment_reports[report_id] = record
            self._audit(actor, "ext_assessment_status_record", report_id,
                        details={"job_id": job_id,
                                 "status_label": status_label})
            return self._copy(record)

    def list_assessment_reports(self, job_id=None, actor=None):
        """Return assessment status reports. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            records = sorted(
                self._assessment_reports.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [self._copy(r) for r in records]

    def assessment_job_view(self, job_id, actor=None):
        """Derive an assessment job's latest reported status.

        Action: review_read. The latest status label is the
        most recent status report's label, verbatim, computed
        at call time and stored nowhere; the stored job record
        carries no reported-status field. No score is derived.
        """
        self._maybe_require(actor, "review_read")
        with self._lock:
            job = self._get(self._assessment_jobs, job_id, "assessment job")
            reports = [
                r for r in sorted(
                    self._assessment_reports.values(),
                    key=lambda r: int(r["id"].rsplit("-", 1)[1]),
                )
                if r["job_id"] == job_id
            ]
            return {
                "job_id": job_id,
                "project_id": job["project_id"],
                "framework_ref": job["framework_ref"],
                "latest_reported_status": (
                    reports[-1]["status_label"] if reports else None
                ),
                "status_report_count": len(reports),
                "assessed_here": False,
                "method": ASSESSMENT_VIEW_METHOD,
            }

    # -- Business modeling & automation engines (idx 179) -----------------

    def record_model_reference(self, project_id, model_ref, actor,
                               kind="business_model"):
        """Reference record for business modeling & automation.

        Action: project_write. The model is held as a definition
        (an opaque reference plus a kind label) and is never
        executed in this build (``executed_here: False``);
        executions arrive as requests against the definition
        (see :meth:`request_model_execution`).
        """
        _validate_non_empty(model_ref, "model_ref")
        if kind not in MODEL_REFERENCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(MODEL_REFERENCE_KINDS),)
            )
        return self._record_reference(
            "model", project_id, actor,
            {"model_ref": model_ref,
             "model_kind": kind,
             "executed_here": False},
            {"model_ref": model_ref},
        )

    def request_model_execution(self, reference_id, actor,
                                requester_ref=None):
        """Request the execution of a referenced model.

        Action: project_write. The request is a record only:
        the external modeling/automation engine is what would
        run the model; nothing executes here
        (``executed_here: False``).
        """
        self._require_actor(actor, "project_write", reference_id)
        _validate_optional_str(requester_ref, "requester_ref")
        with self._lock:
            reference = self._get(
                self._references, reference_id, "reference record"
            )
            if reference["kind"] != "model":
                raise ValidationError(
                    "reference %r is not a model reference" % (reference_id,)
                )
            execution_id = self._next_id("exq")
            record = {
                "id": execution_id,
                "reference_id": reference_id,
                "project_id": reference["project_id"],
                "requester_ref": requester_ref,
                "reference_stub": True,
                "status": "requested",
                "executed_here": False,
                "requested_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_executions[execution_id] = record
            self._audit(actor, "ext_model_execution_request", execution_id,
                        details={"reference_id": reference_id})
            return self._copy(record)

    def list_model_executions(self, reference_id=None, actor=None):
        """Return model execution requests. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._model_executions.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if reference_id is not None:
                records = [r for r in records
                           if r["reference_id"] == reference_id]
            return [self._copy(r) for r in records]

    # -- Course & content authoring tools (idx 180) -----------------------

    def create_course_record(self, project_id, title, actor,
                             format_label=None):
        """Create a course record, as metadata.

        Action: project_write. The course the external
        authoring tool maintains is recorded as metadata (a
        title and a format label); authored content is never
        held here -- no record field can hold content
        (``authored_here: False``).
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(title, "course title")
        _validate_optional_str(format_label, "format_label")
        with self._lock:
            self._core_project(project_id)
            course_id = self._next_id("crs")
            record = {
                "id": course_id,
                "project_id": project_id,
                "title": title,
                "format_label": format_label,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "authored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._courses[course_id] = record
            self._audit(actor, "ext_course_record_create", course_id,
                        details={"project_id": project_id, "title": title})
            return self._copy(record)

    def get_course_record(self, course_id, actor=None):
        """Return one course record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(self._get(self._courses, course_id, "course"))

    def list_course_records(self, project_id=None, actor=None):
        """Return course records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._list(self._courses, project_id)

    def record_course_asset(self, course_id, asset_ref, actor,
                            format_label=None):
        """Record a course asset, as metadata.

        Action: project_write. The asset is an opaque reference
        plus a format label; the asset's content is never held
        here (``authored_here: False``).
        """
        self._require_actor(actor, "project_write", course_id)
        _validate_non_empty(asset_ref, "asset_ref")
        _validate_optional_str(format_label, "format_label")
        with self._lock:
            course = self._get(self._courses, course_id, "course")
            asset_id = self._next_id("ast")
            record = {
                "id": asset_id,
                "course_id": course_id,
                "project_id": course["project_id"],
                "asset_ref": asset_ref,
                "format_label": format_label,
                "reference_stub": True,
                "authored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._course_assets[asset_id] = record
            self._audit(actor, "ext_course_asset_record", asset_id,
                        details={"course_id": course_id,
                                 "asset_ref": asset_ref})
            return self._copy(record)

    def list_course_assets(self, course_id=None, actor=None):
        """Return course asset records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._course_assets.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._copy(r) for r in records]

    def record_course_outcome(self, course_id, outcome_label, actor):
        """Record a course authoring outcome, as reported.

        Action: project_write. The outcome label is stored
        verbatim, as reported by the external authoring tool;
        nothing was authored here (``authored_here: False``).
        """
        self._require_actor(actor, "project_write", course_id)
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            course = self._get(self._courses, course_id, "course")
            outcome_id = self._next_id("cou")
            record = {
                "id": outcome_id,
                "course_id": course_id,
                "project_id": course["project_id"],
                "outcome_label": outcome_label,
                "reference_stub": True,
                "authored_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._course_outcomes[outcome_id] = record
            self._audit(actor, "ext_course_outcome_record", outcome_id,
                        details={"course_id": course_id,
                                 "outcome_label": outcome_label})
            return self._copy(record)

    def list_course_outcomes(self, course_id=None, actor=None):
        """Return course outcome records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(
                self._course_outcomes.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if course_id is not None:
                records = [r for r in records
                           if r["course_id"] == course_id]
            return [self._copy(r) for r in records]

    # -- Landing-zone / tenant provisioning & hosting (idx 181) -----------

    def record_provisioning_reference(self, project_id, zone_ref, actor,
                                      environment_id=None):
        """Reference record for landing-zone / tenant provisioning.

        Action: project_write. Optionally binds a core
        environment record; nothing is provisioned or hosted in
        this build (``provisioned_here: False``,
        ``hosted_here: False``) -- provisioning and hosting are
        platform-layer properties (PLATFORM-LAYER.md decision 6).
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(zone_ref, "zone_ref")
        if environment_id is not None:
            self.store.get_environment(environment_id)
        return self._record_reference(
            "provisioning", project_id, actor,
            {"zone_ref": zone_ref,
             "environment_id": environment_id,
             "provisioned_here": False,
             "hosted_here": False},
            {"zone_ref": zone_ref},
        )
