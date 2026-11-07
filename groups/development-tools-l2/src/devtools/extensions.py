"""Final GAPS batch extensions for the Development Tools L2 build.

Clean-room, standard-library-only extensions for the 15 open
Extended entries of Group 29 (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module wraps a
:class:`~devtools.store.DevToolsStore`; every core module is
untouched and byte-identical to the shipped build.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records. Nothing in this module executes a build,
compiles code, analyzes code, provisions anything, remediates
anything, or calls an external system.

- **CI/CD execution engines** land as pipeline *definition*
  records plus pipeline *run* records reported by external
  runners. Every run record carries ``executed_here: False``;
  this build runs nothing.
- **Compilers & build toolchains** land as toolchain registry
  records -- the declaration of the toolchain a real build used.
  No compiler ships.
- **Artifact binary storage backends** land as backend
  registration records plus placement records that bind a core
  artifact to a backend, copying only the artifact's recorded
  SHA-256 checksum and size. No binary is accepted or stored
  (``stored_here: False``); the core registry's records +
  checksums discipline is unchanged.
- **Feature-flag & feature-management runtime** is the one
  genuinely computable surface: flag evaluation is a pure
  deterministic function over recorded flag / targeting / rollout
  records, so it is implemented as a derivation. The bucketing
  rule is stated, not hidden: ``bucket = int(sha256(flag_id +
  ":" + subject_ref)[:8], 16) % 100`` over the opaque subject
  reference. The kill switch is a recorded state that evaluation
  honors before targeting and rollout. Evaluation results are
  computed at call time and stored nowhere.
- **Experimentation engine** lands as experiment records,
  assignment records whose variant is chosen by the same stated
  bucketing rule (``variant index = bucket * len(variants) //
  100``), outcome records stored verbatim as reported, and a
  summary that is exact integer counts over those records --
  no rates, no significance computation.
- **Static code analysis engine** lands as rule-set and
  quality-profile records (rules and gate thresholds held as
  data) plus analysis-result records whose finding counts are
  reported by an external analyzer (``analyzed_here: False``).
  Quality-gate evaluation is a derivation: the recorded gate
  thresholds compared against the recorded reported counts.
- **Release automation, environment management & data
  migration engine** lands as release-plan records with
  recorded stage states, data-migration records with outcomes
  as reported (``executed_here: False``), and a plan view whose
  overall state is derived at read from the recorded stage
  records, never stored.
- The eight **stub-engine** entries (code hosting internals,
  configuration-as-code execution, compliance assessment & KSI
  automation, business modeling & automation, course & content
  authoring, landing-zone / tenant provisioning, security
  posture monitoring & automated remediation, external-system
  integration engines) ship as labeled reference
  implementations: records carry ``reference_stub: True`` and
  status ``recorded_reference_only`` (integration records also
  ``reference_transport: True``). Creating one changes no core
  record; that is pinned by test.

Doctrines carried from the core: opaque ``*_ref`` strings only;
derived-never-stored for every computed value (evaluation
results, summaries, gate verdicts, plan views); validation fully
before mutation, so a failed operation consumes no id and
changes nothing; append-only audit on the core store's log with
``ext_``-prefixed actions for extension mutations and denied
attempts audited as ``<action>:denied``, exactly as the core
store does; RBAC via :mod:`devtools.access`, enforced before
any state change or id allocation. Plain-string actors carry
identity but no role, so -- as in the core store -- there is
nothing to enforce against at this layer for them.

RBAC action mapping (the core action set is fixed): pipeline
definitions, pipeline runs, and toolchains ride the build
family (``build_write`` / ``build_read``); storage backends and
placements ride the artifact family; feature flags and
experiments ride the deployment family (the feature-release
surface); rule sets, quality profiles, and analysis results
ride the review family (code-examination records); release
plans, stage records, and migration records ride the release
family; stub reference records are registry-level records about
a project and ride ``project_write`` / ``project_read``.
"""

import copy
import hashlib
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

FLAG_EVALUATION_METHOD = "sha256_bucket_over_flag_and_subject"
EXPERIMENT_ASSIGNMENT_METHOD = "sha256_bucket_over_experiment_and_subject"
EXPERIMENT_SUMMARY_METHOD = "exact_counts_over_recorded_assignments_and_outcomes"
GATE_EVALUATION_METHOD = "recorded_gate_thresholds_over_reported_counts"
RELEASE_PLAN_VIEW_METHOD = "derived_from_recorded_stage_records"
BACKEND_SUMMARY_METHOD = "derived_from_placement_records"

PIPELINE_STAGE_KINDS = ("build", "test", "deploy", "custom")
RELEASE_STAGE_KINDS = ("deployment", "data_migration", "verification", "custom")
RELEASE_STAGE_STATUSES = ("in_progress", "succeeded", "failed", "skipped")
MIGRATION_STATUSES = (
    "planned", "reported_running", "reported_succeeded", "reported_failed",
)
ANALYSIS_SEVERITIES = ("info", "low", "medium", "high", "critical")
STORAGE_BACKEND_KINDS = ("object_store", "filesystem", "archive", "custom")
MODEL_REFERENCE_KINDS = ("business_model", "workflow_automation")
REMEDIATION_STATUSES = ("reported_open", "reported_remediated", "reported_accepted")
INTEGRATION_DIRECTIONS = ("inbound", "outbound")
EXPERIMENT_TRANSITIONS = {
    "draft": {"running"},
    "running": {"concluded"},
    "concluded": set(),
}

REFERENCE_KINDS = (
    "repository", "configuration", "assessment", "model",
    "authoring", "provisioning", "posture", "integration",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _bucket(scope_id, subject_ref):
    """The stated deterministic bucketing rule (0..99).

    ``bucket = int(sha256(scope_id + ":" + subject_ref)[:8], 16) % 100``
    over the opaque subject reference. Pure function of its inputs;
    the same inputs always produce the same bucket.
    """
    digest = hashlib.sha256(
        ("%s:%s" % (scope_id, subject_ref)).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) % 100


def _validate_percentage(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer percentage" % (what,))
    if value < 0 or value > 100:
        raise ValidationError("%s must be between 0 and 100" % (what,))
    return value


def _validate_non_negative_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be non-negative" % (what,))
    return value


def _validate_stages(stages, kinds, what):
    """Normalize a stage list to a list of {name, kind} dicts.

    A stage is a non-empty string (kind defaults to "custom") or a
    dict with a non-empty ``name`` and a ``kind`` in ``kinds``.
    Stage names must be unique within the list.
    """
    if not isinstance(stages, list) or not stages:
        raise ValidationError("%s must be a non-empty list" % (what,))
    normalized = []
    seen = set()
    for stage in stages:
        if isinstance(stage, str):
            stage = {"name": stage, "kind": "custom"}
        if not isinstance(stage, dict):
            raise ValidationError("%s entries must be strings or objects" % (what,))
        name = _validate_non_empty(stage.get("name"), "stage name")
        kind = stage.get("kind", "custom")
        if kind not in kinds:
            raise ValidationError(
                "stage kind must be one of %s" % (", ".join(kinds),)
            )
        if name in seen:
            raise ValidationError("duplicate stage name %r" % (name,))
        seen.add(name)
        normalized.append({"name": name, "kind": kind})
    return normalized


def _validate_ref_list(values, what):
    if not isinstance(values, list):
        raise ValidationError("%s must be a list" % (what,))
    result = []
    for value in values:
        _validate_non_empty(value, what)
        if value not in result:
            result.append(value)
    return result


class DevToolsExtensions:
    """Extension surface for the Group 29 final GAPS batch unit.

    Wraps a :class:`DevToolsStore`. All extension records live in
    this object; the core store's record sets are never written
    by this class (core records are only read, to bind extension
    records to real projects / builds / releases / artifacts /
    environments, and to append to the core audit log).
    """

    def __init__(self, store):
        self.store = store
        self._pipelines = {}
        self._pipeline_runs = {}
        self._toolchains = {}
        self._storage_backends = {}
        self._placements = {}
        self._flags = {}
        self._experiments = {}
        self._assignments = {}
        self._outcomes = {}
        self._rule_sets = {}
        self._quality_profiles = {}
        self._analysis_results = {}
        self._release_plans = {}
        self._release_stages = {}
        self._data_migrations = {}
        self._references = {}
        self._counters = {
            "pip": 0, "run": 0, "tch": 0, "stb": 0, "plm": 0,
            "flg": 0, "exp": 0, "asn": 0, "out": 0, "rul": 0,
            "qpr": 0, "anr": 0, "rlp": 0, "rls": 0, "mig": 0,
            "ref": 0,
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
        records = sorted(table.values(), key=lambda r: int(r["id"].rsplit("-", 1)[1]))
        if project_id is not None:
            records = [r for r in records if r.get("project_id") == project_id]
        return [self._copy(r) for r in records]

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    # -- CI/CD execution engines (records form) ------------------------

    def define_pipeline(self, project_id, name, actor, stages):
        """Define a pipeline. Action: build_write.

        A pipeline is a *definition* record: an ordered list of
        stage records-as-data. Nothing executes; runs arrive as
        records reported by external runners (see
        :meth:`record_pipeline_run`).
        """
        self._require_actor(actor, "build_write", project_id)
        _validate_non_empty(name, "pipeline name")
        stages = _validate_stages(stages, PIPELINE_STAGE_KINDS, "pipeline stages")
        with self._lock:
            self._core_project(project_id)
            pipeline_id = self._next_id("pip")
            record = {
                "id": pipeline_id,
                "project_id": project_id,
                "name": name,
                "stages": stages,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pipelines[pipeline_id] = record
            self._audit(actor, "ext_pipeline_create", pipeline_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_pipeline(self, pipeline_id, actor=None):
        """Return one pipeline definition. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy(self._get(self._pipelines, pipeline_id, "pipeline"))

    def list_pipelines(self, project_id=None, actor=None):
        """Return pipeline definitions. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._pipelines, project_id)

    def record_pipeline_run(self, pipeline_id, actor, status="succeeded",
                            runner_ref=None, build_id=None):
        """Record a pipeline run reported by an external runner.

        Action: build_write. The status is the runner's report,
        recorded verbatim; this build ran nothing
        (``executed_here: False`` on the record). ``build_id``, if
        given, must name a core build record.
        """
        self._require_actor(actor, "build_write", pipeline_id)
        if status not in BUILD_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(BUILD_STATUSES),)
            )
        _validate_optional_str(runner_ref, "runner_ref")
        with self._lock:
            pipeline = self._get(self._pipelines, pipeline_id, "pipeline")
            if build_id is not None:
                self.store.get_build(build_id)
            run_id = self._next_id("run")
            record = {
                "id": run_id,
                "pipeline_id": pipeline_id,
                "project_id": pipeline["project_id"],
                "status": status,
                "runner_ref": runner_ref,
                "build_id": build_id,
                "executed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pipeline_runs[run_id] = record
            self._audit(actor, "ext_pipeline_run_record", run_id,
                        details={"pipeline_id": pipeline_id, "status": status})
            return self._copy(record)

    def list_pipeline_runs(self, pipeline_id=None, actor=None):
        """Return pipeline run records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            records = sorted(
                self._pipeline_runs.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if pipeline_id is not None:
                records = [r for r in records if r["pipeline_id"] == pipeline_id]
            return [self._copy(r) for r in records]

    # -- Compilers & build toolchains (registry records) ---------------

    def register_toolchain(self, project_id, name, actor,
                           language=None, version_label=None):
        """Register a toolchain declaration. Action: build_write.

        The record declares the toolchain a real build used; no
        compiler exists in this build (``executed_here: False``).
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
            return self._copy(self._get(self._toolchains, toolchain_id, "toolchain"))

    def list_toolchains(self, project_id=None, actor=None):
        """Return toolchain records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._list(self._toolchains, project_id)

    # -- Artifact binary storage backends (records + checksums) ---------

    def register_storage_backend(self, name, actor, kind="filesystem"):
        """Register a storage-backend record. Action: artifact_write.

        A backend here is a bookkeeping record: placements bind
        core artifacts to it by checksum. This build stores no
        binary anywhere.
        """
        self._require_actor(actor, "artifact_write",
                            name if isinstance(name, str) else "storage_backend")
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
                "stored_here": False,
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

    def place_artifact(self, artifact_id, backend_id, actor):
        """Record the placement of a core artifact on a backend.

        Action: artifact_write. The placement copies the core
        artifact record's SHA-256 checksum and size -- and nothing
        else; no content is accepted or stored
        (``stored_here: False``).
        """
        self._require_actor(actor, "artifact_write", artifact_id)
        with self._lock:
            artifact = self.store.get_artifact(artifact_id)
            self._get(self._storage_backends, backend_id, "storage backend")
            placement_id = self._next_id("plm")
            record = {
                "id": placement_id,
                "artifact_id": artifact_id,
                "backend_id": backend_id,
                "project_id": artifact["project_id"],
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "stored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._placements[placement_id] = record
            self._audit(actor, "ext_artifact_place", placement_id,
                        details={"artifact_id": artifact_id,
                                 "backend_id": backend_id})
            return self._copy(record)

    def list_placements(self, backend_id=None, artifact_id=None, actor=None):
        """Return placement records. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            records = sorted(
                self._placements.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if backend_id is not None:
                records = [r for r in records if r["backend_id"] == backend_id]
            if artifact_id is not None:
                records = [r for r in records if r["artifact_id"] == artifact_id]
            return [self._copy(r) for r in records]

    def storage_backend_summary(self, backend_id, actor=None):
        """Derive a backend's placement summary at read.

        Action: artifact_read. Counts and size totals are computed
        from the placement records at call time and stored
        nowhere. Artifacts registered checksum-only have no
        recorded size; they are counted separately as
        ``unknown_size_count`` rather than silently treated as 0.
        """
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            self._get(self._storage_backends, backend_id, "storage backend")
            placements = [r for r in self._placements.values()
                          if r["backend_id"] == backend_id]
            known_sizes = [r["size_bytes"] for r in placements
                           if r["size_bytes"] is not None]
            return {
                "backend_id": backend_id,
                "placements": len(placements),
                "total_size_bytes": sum(known_sizes),
                "unknown_size_count": len(placements) - len(known_sizes),
                "method": BACKEND_SUMMARY_METHOD,
            }

    # -- Feature-flag & feature-management runtime -----------------------

    def create_flag(self, project_id, key, actor, description=None):
        """Create a feature-flag record. Action: deployment_write.

        The flag starts enabled, not killed, with a 0% rollout
        and no targeted subjects: it serves nothing until its
        recorded configuration says otherwise.
        """
        self._require_actor(actor, "deployment_write", project_id)
        _validate_non_empty(key, "flag key")
        _validate_optional_str(description, "description")
        with self._lock:
            self._core_project(project_id)
            for existing in self._flags.values():
                if (existing["project_id"] == project_id
                        and existing["key"] == key):
                    raise ValidationError(
                        "flag key %r already exists for project %r"
                        % (key, project_id)
                    )
            flag_id = self._next_id("flg")
            record = {
                "id": flag_id,
                "project_id": project_id,
                "key": key,
                "description": description,
                "enabled": True,
                "killed": False,
                "rollout_percentage": 0,
                "targeted_subject_refs": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._flags[flag_id] = record
            self._audit(actor, "ext_flag_create", flag_id,
                        details={"project_id": project_id, "key": key})
            return self._copy(record)

    def get_flag(self, flag_id, actor=None):
        """Return one flag record. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(self._get(self._flags, flag_id, "flag"))

    def list_flags(self, project_id=None, actor=None):
        """Return flag records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._flags, project_id)

    def set_flag_enabled(self, flag_id, enabled, actor):
        """Record a flag's enabled state. Action: deployment_write."""
        self._require_actor(actor, "deployment_write", flag_id)
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a boolean")
        with self._lock:
            record = self._get(self._flags, flag_id, "flag")
            record["enabled"] = enabled
            self._audit(actor, "ext_flag_set_enabled", flag_id,
                        details={"enabled": enabled})
            return self._copy(record)

    def set_flag_rollout(self, flag_id, percentage, actor):
        """Record a flag's rollout percentage (0..100).

        Action: deployment_write.
        """
        self._require_actor(actor, "deployment_write", flag_id)
        _validate_percentage(percentage, "rollout percentage")
        with self._lock:
            record = self._get(self._flags, flag_id, "flag")
            record["rollout_percentage"] = percentage
            self._audit(actor, "ext_flag_set_rollout", flag_id,
                        details={"rollout_percentage": percentage})
            return self._copy(record)

    def set_flag_targeting(self, flag_id, subject_refs, actor):
        """Record a flag's targeted subject references.

        Action: deployment_write. Subjects are opaque references;
        the list replaces any previous targeting.
        """
        self._require_actor(actor, "deployment_write", flag_id)
        subject_refs = _validate_ref_list(subject_refs, "targeted subject ref")
        with self._lock:
            record = self._get(self._flags, flag_id, "flag")
            record["targeted_subject_refs"] = subject_refs
            self._audit(actor, "ext_flag_set_targeting", flag_id,
                        details={"subjects": len(subject_refs)})
            return self._copy(record)

    def kill_flag(self, flag_id, actor):
        """Record the flag's kill switch as thrown.

        Action: deployment_write. Evaluation honors the recorded
        kill state before targeting and rollout (see
        :meth:`evaluate_flag`).
        """
        self._require_actor(actor, "deployment_write", flag_id)
        with self._lock:
            record = self._get(self._flags, flag_id, "flag")
            record["killed"] = True
            self._audit(actor, "ext_flag_kill", flag_id, details={})
            return self._copy(record)

    def restore_flag(self, flag_id, actor):
        """Record the flag's kill switch as restored.

        Action: deployment_write.
        """
        self._require_actor(actor, "deployment_write", flag_id)
        with self._lock:
            record = self._get(self._flags, flag_id, "flag")
            record["killed"] = False
            self._audit(actor, "ext_flag_restore", flag_id, details={})
            return self._copy(record)

    def _kill_switch_active(self, flag):
        """The kill-switch seam: is this flag's kill switch thrown?

        MUTATION DRILL NOTE: this seam is the load-bearing
        invariant of the batch's fresh negative control -- a
        killed flag must serve no subject, whatever its targeting
        or rollout says. An implementation that ignores the
        recorded kill state is the mutant the drill rejects.
        """
        return bool(flag["killed"])

    def evaluate_flag(self, flag_id, subject_ref, actor=None):
        """Evaluate a flag for one opaque subject reference.

        Action: deployment_read. A pure derivation over the
        recorded flag configuration, computed at call time and
        stored nowhere:

        1. kill switch thrown -> not served, ``kill_switch``;
        2. flag disabled -> not served, ``flag_disabled``;
        3. subject in the recorded targeting list -> served,
           ``targeted``;
        4. the subject's bucket (the stated sha256 rule) below
           the recorded rollout percentage -> served, ``rollout``;
        5. otherwise -> not served, ``rollout_miss``.
        """
        self._maybe_require(actor, "deployment_read")
        _validate_non_empty(subject_ref, "subject_ref")
        with self._lock:
            flag = self._get(self._flags, flag_id, "flag")
            bucket = _bucket(flag_id, subject_ref)
            if self._kill_switch_active(flag):
                served, reason = False, "kill_switch"
            elif not flag["enabled"]:
                served, reason = False, "flag_disabled"
            elif subject_ref in flag["targeted_subject_refs"]:
                served, reason = True, "targeted"
            elif bucket < flag["rollout_percentage"]:
                served, reason = True, "rollout"
            else:
                served, reason = False, "rollout_miss"
            return {
                "flag_id": flag_id,
                "subject_ref": subject_ref,
                "bucket": bucket,
                "served": served,
                "reason": reason,
                "method": FLAG_EVALUATION_METHOD,
            }

    # -- Experimentation engine (records form) ---------------------------

    def create_experiment(self, project_id, name, actor, variants, flag_id=None):
        """Create an experiment record. Action: deployment_write.

        Variants are recorded labels (at least two, unique). The
        experiment starts in ``draft``; subjects can only be
        assigned while it is ``running``.
        """
        self._require_actor(actor, "deployment_write", project_id)
        _validate_non_empty(name, "experiment name")
        variants = _validate_ref_list(variants, "variant")
        if len(variants) < 2:
            raise ValidationError("an experiment needs at least two variants")
        with self._lock:
            self._core_project(project_id)
            if flag_id is not None:
                flag = self._get(self._flags, flag_id, "flag")
                if flag["project_id"] != project_id:
                    raise ValidationError(
                        "flag %r does not belong to project %r"
                        % (flag_id, project_id)
                    )
            experiment_id = self._next_id("exp")
            record = {
                "id": experiment_id,
                "project_id": project_id,
                "name": name,
                "flag_id": flag_id,
                "variants": variants,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._experiments[experiment_id] = record
            self._audit(actor, "ext_experiment_create", experiment_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_experiment(self, experiment_id, actor=None):
        """Return one experiment record. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(
                self._get(self._experiments, experiment_id, "experiment")
            )

    def list_experiments(self, project_id=None, actor=None):
        """Return experiment records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._experiments, project_id)

    def set_experiment_status(self, experiment_id, status, actor):
        """Transition an experiment's status. Action: deployment_write.

        Transitions ONLY: draft -> running, running -> concluded.
        """
        self._require_actor(actor, "deployment_write", experiment_id)
        with self._lock:
            record = self._get(self._experiments, experiment_id, "experiment")
            allowed = EXPERIMENT_TRANSITIONS.get(record["status"], set())
            if status not in allowed:
                raise ValidationError(
                    "experiment status transition %r -> %r is not allowed"
                    % (record["status"], status)
                )
            record["status"] = status
            self._audit(actor, "ext_experiment_set_status", experiment_id,
                        details={"status": status})
            return self._copy(record)

    def assign_subject(self, experiment_id, subject_ref, actor):
        """Record a subject's variant assignment. Action: deployment_write.

        The variant is chosen by the stated bucketing rule --
        ``bucket = int(sha256(experiment_id + ":" + subject_ref)
        [:8], 16) % 100``; ``variant index = bucket *
        len(variants) // 100`` -- and recorded as the exposure
        record. Assignment requires a ``running`` experiment, and
        a subject is assigned at most once per experiment.
        """
        self._require_actor(actor, "deployment_write", experiment_id)
        _validate_non_empty(subject_ref, "subject_ref")
        with self._lock:
            experiment = self._get(self._experiments, experiment_id, "experiment")
            if experiment["status"] != "running":
                raise ValidationError(
                    "subjects can only be assigned to a running experiment "
                    "(status is %r)" % (experiment["status"],)
                )
            for existing in self._assignments.values():
                if (existing["experiment_id"] == experiment_id
                        and existing["subject_ref"] == subject_ref):
                    raise ValidationError(
                        "subject %r is already assigned to experiment %r"
                        % (subject_ref, experiment_id)
                    )
            bucket = _bucket(experiment_id, subject_ref)
            variants = experiment["variants"]
            variant = variants[(bucket * len(variants)) // 100]
            assignment_id = self._next_id("asn")
            record = {
                "id": assignment_id,
                "experiment_id": experiment_id,
                "project_id": experiment["project_id"],
                "subject_ref": subject_ref,
                "variant": variant,
                "bucket": bucket,
                "method": EXPERIMENT_ASSIGNMENT_METHOD,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assignments[assignment_id] = record
            self._audit(actor, "ext_experiment_assign", assignment_id,
                        details={"experiment_id": experiment_id,
                                 "variant": variant})
            return self._copy(record)

    def list_assignments(self, experiment_id=None, actor=None):
        """Return assignment records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            records = sorted(
                self._assignments.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if experiment_id is not None:
                records = [r for r in records
                           if r["experiment_id"] == experiment_id]
            return [self._copy(r) for r in records]

    def record_experiment_outcome(self, experiment_id, subject_ref, outcome, actor):
        """Record an outcome for an assigned subject, verbatim.

        Action: deployment_write. The outcome label is stored
        exactly as reported and never interpreted; an outcome
        requires an existing assignment for the subject.
        """
        self._require_actor(actor, "deployment_write", experiment_id)
        _validate_non_empty(subject_ref, "subject_ref")
        _validate_non_empty(outcome, "outcome")
        with self._lock:
            experiment = self._get(self._experiments, experiment_id, "experiment")
            assigned = any(
                a["experiment_id"] == experiment_id
                and a["subject_ref"] == subject_ref
                for a in self._assignments.values()
            )
            if not assigned:
                raise ValidationError(
                    "subject %r has no assignment in experiment %r"
                    % (subject_ref, experiment_id)
                )
            outcome_id = self._next_id("out")
            record = {
                "id": outcome_id,
                "experiment_id": experiment_id,
                "project_id": experiment["project_id"],
                "subject_ref": subject_ref,
                "outcome": outcome,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._outcomes[outcome_id] = record
            self._audit(actor, "ext_experiment_outcome_record", outcome_id,
                        details={"experiment_id": experiment_id})
            return self._copy(record)

    def list_outcomes(self, experiment_id=None, actor=None):
        """Return outcome records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            records = sorted(
                self._outcomes.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if experiment_id is not None:
                records = [r for r in records
                           if r["experiment_id"] == experiment_id]
            return [self._copy(r) for r in records]

    def experiment_summary(self, experiment_id, actor=None):
        """Derive an experiment's exact counts at read.

        Action: deployment_read. Counts of assignments per
        variant and of outcomes per recorded label, computed from
        the records at call time and stored nowhere. No rates and
        no significance computation: counts only, exactly as
        recorded.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            experiment = self._get(self._experiments, experiment_id, "experiment")
            by_variant = {variant: 0 for variant in experiment["variants"]}
            total_assignments = 0
            for assignment in self._assignments.values():
                if assignment["experiment_id"] == experiment_id:
                    by_variant[assignment["variant"]] += 1
                    total_assignments += 1
            by_outcome = {}
            total_outcomes = 0
            for outcome in self._outcomes.values():
                if outcome["experiment_id"] == experiment_id:
                    by_outcome[outcome["outcome"]] = (
                        by_outcome.get(outcome["outcome"], 0) + 1
                    )
                    total_outcomes += 1
            return {
                "experiment_id": experiment_id,
                "status": experiment["status"],
                "assignments_by_variant": by_variant,
                "outcomes_by_label": by_outcome,
                "total_assignments": total_assignments,
                "total_outcomes": total_outcomes,
                "method": EXPERIMENT_SUMMARY_METHOD,
            }

    # -- Static code analysis engine (records form) ----------------------

    def create_rule_set(self, project_id, name, actor, rules):
        """Create an analysis rule-set record. Action: review_write.

        Rules are held as data: a list of {rule_ref, severity}
        with severity in the recorded severity vocabulary. No
        rule is ever run against code in this build.
        """
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(name, "rule set name")
        if not isinstance(rules, list) or not rules:
            raise ValidationError("rules must be a non-empty list")
        normalized = []
        seen = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValidationError("each rule must be an object")
            rule_ref = _validate_non_empty(rule.get("rule_ref"), "rule_ref")
            severity = rule.get("severity")
            if severity not in ANALYSIS_SEVERITIES:
                raise ValidationError(
                    "severity must be one of %s"
                    % (", ".join(ANALYSIS_SEVERITIES),)
                )
            if rule_ref in seen:
                raise ValidationError("duplicate rule_ref %r" % (rule_ref,))
            seen.add(rule_ref)
            normalized.append({"rule_ref": rule_ref, "severity": severity})
        with self._lock:
            self._core_project(project_id)
            rule_set_id = self._next_id("rul")
            record = {
                "id": rule_set_id,
                "project_id": project_id,
                "name": name,
                "rules": normalized,
                "analyzed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rule_sets[rule_set_id] = record
            self._audit(actor, "ext_rule_set_create", rule_set_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_rule_set(self, rule_set_id, actor=None):
        """Return one rule-set record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._copy(self._get(self._rule_sets, rule_set_id, "rule set"))

    def list_rule_sets(self, project_id=None, actor=None):
        """Return rule-set records. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._list(self._rule_sets, project_id)

    def create_quality_profile(self, project_id, name, actor, rule_set_id,
                               gate=None):
        """Create a quality-profile record. Action: review_write.

        The gate, if given, is recorded data: a mapping of
        severity -> maximum tolerated reported count. It is
        enforced nowhere except the read-time derivation in
        :meth:`evaluate_quality_gate`.
        """
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(name, "quality profile name")
        if gate is not None:
            if not isinstance(gate, dict):
                raise ValidationError("gate must be an object")
            for severity, limit in gate.items():
                if severity not in ANALYSIS_SEVERITIES:
                    raise ValidationError(
                        "gate severity must be one of %s"
                        % (", ".join(ANALYSIS_SEVERITIES),)
                    )
                _validate_non_negative_int(limit, "gate limit")
        with self._lock:
            self._core_project(project_id)
            rule_set = self._get(self._rule_sets, rule_set_id, "rule set")
            if rule_set["project_id"] != project_id:
                raise ValidationError(
                    "rule set %r does not belong to project %r"
                    % (rule_set_id, project_id)
                )
            profile_id = self._next_id("qpr")
            record = {
                "id": profile_id,
                "project_id": project_id,
                "name": name,
                "rule_set_id": rule_set_id,
                "gate": dict(gate) if gate is not None else None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._quality_profiles[profile_id] = record
            self._audit(actor, "ext_quality_profile_create", profile_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def get_quality_profile(self, profile_id, actor=None):
        """Return one quality-profile record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._copy(
                self._get(self._quality_profiles, profile_id, "quality profile")
            )

    def list_quality_profiles(self, project_id=None, actor=None):
        """Return quality-profile records. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._list(self._quality_profiles, project_id)

    def record_analysis_result(self, project_id, actor, analyzer_ref,
                               rule_set_id=None, profile_id=None, findings=None):
        """Record an analysis result reported by an external analyzer.

        Action: review_write. Findings are counts per rule as
        reported; no code is analyzed in this build
        (``analyzed_here: False``). When a rule set is named
        (directly or via the profile), every finding's rule_ref
        must be one of its recorded rules.
        """
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(analyzer_ref, "analyzer_ref")
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            raise ValidationError("findings must be a list")
        normalized = []
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValidationError("each finding must be an object")
            rule_ref = _validate_non_empty(finding.get("rule_ref"), "rule_ref")
            severity = finding.get("severity")
            if severity not in ANALYSIS_SEVERITIES:
                raise ValidationError(
                    "severity must be one of %s"
                    % (", ".join(ANALYSIS_SEVERITIES),)
                )
            count = _validate_non_negative_int(finding.get("count"), "finding count")
            normalized.append(
                {"rule_ref": rule_ref, "severity": severity, "count": count}
            )
        with self._lock:
            self._core_project(project_id)
            profile = None
            if profile_id is not None:
                profile = self._get(
                    self._quality_profiles, profile_id, "quality profile"
                )
                if profile["project_id"] != project_id:
                    raise ValidationError(
                        "quality profile %r does not belong to project %r"
                        % (profile_id, project_id)
                    )
                if rule_set_id is not None and rule_set_id != profile["rule_set_id"]:
                    raise ValidationError(
                        "rule set %r does not match the profile's rule set %r"
                        % (rule_set_id, profile["rule_set_id"])
                    )
                rule_set_id = profile["rule_set_id"]
            if rule_set_id is not None:
                rule_set = self._get(self._rule_sets, rule_set_id, "rule set")
                if rule_set["project_id"] != project_id:
                    raise ValidationError(
                        "rule set %r does not belong to project %r"
                        % (rule_set_id, project_id)
                    )
                known = {r["rule_ref"] for r in rule_set["rules"]}
                for finding in normalized:
                    if finding["rule_ref"] not in known:
                        raise ValidationError(
                            "finding rule_ref %r is not in rule set %r"
                            % (finding["rule_ref"], rule_set_id)
                        )
            result_id = self._next_id("anr")
            record = {
                "id": result_id,
                "project_id": project_id,
                "rule_set_id": rule_set_id,
                "profile_id": profile_id,
                "analyzer_ref": analyzer_ref,
                "findings": normalized,
                "analyzed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._analysis_results[result_id] = record
            self._audit(actor, "ext_analysis_result_record", result_id,
                        details={"project_id": project_id,
                                 "analyzer_ref": analyzer_ref})
            return self._copy(record)

    def get_analysis_result(self, result_id, actor=None):
        """Return one analysis-result record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._copy(
                self._get(self._analysis_results, result_id, "analysis result")
            )

    def list_analysis_results(self, project_id=None, actor=None):
        """Return analysis-result records. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return self._list(self._analysis_results, project_id)

    def evaluate_quality_gate(self, result_id, actor=None):
        """Derive a quality-gate verdict at read.

        Action: review_read. The result's profile must carry a
        recorded gate; the verdict compares the gate's recorded
        per-severity limits against the result's recorded
        reported counts, summed per severity. Computed at call
        time and stored nowhere. Severities with findings but no
        gate limit are reported as ``ungated_severities`` and do
        not affect the verdict.
        """
        self._maybe_require(actor, "review_read")
        with self._lock:
            result = self._get(self._analysis_results, result_id, "analysis result")
            if result["profile_id"] is None:
                raise ValidationError(
                    "analysis result %r names no quality profile; "
                    "there is no gate to evaluate against" % (result_id,)
                )
            profile = self._get(
                self._quality_profiles, result["profile_id"], "quality profile"
            )
            gate = profile["gate"]
            if gate is None:
                raise ValidationError(
                    "quality profile %r records no gate thresholds"
                    % (profile["id"],)
                )
            totals = {}
            for finding in result["findings"]:
                totals[finding["severity"]] = (
                    totals.get(finding["severity"], 0) + finding["count"]
                )
            breaches = []
            for severity in sorted(gate):
                count = totals.get(severity, 0)
                if count > gate[severity]:
                    breaches.append({
                        "severity": severity,
                        "count": count,
                        "limit": gate[severity],
                    })
            ungated = sorted(s for s in totals if s not in gate)
            return {
                "result_id": result_id,
                "profile_id": profile["id"],
                "passed": not breaches,
                "breaches": breaches,
                "ungated_severities": ungated,
                "method": GATE_EVALUATION_METHOD,
            }

    # -- Release automation / environment mgmt / data migration -----------

    def create_release_plan(self, project_id, actor, stages,
                            release_id=None, environment_id=None):
        """Create a release-plan record. Action: release_write.

        Stages are recorded data ({name, kind}); stage kinds
        include ``deployment`` and ``data_migration``. The plan
        executes nothing (``executed_here: False``); stage
        outcomes arrive as records (see
        :meth:`record_release_stage`).
        """
        self._require_actor(actor, "release_write", project_id)
        stages = _validate_stages(stages, RELEASE_STAGE_KINDS, "release plan stages")
        with self._lock:
            self._core_project(project_id)
            if release_id is not None:
                release = self.store.get_release(release_id)
                if release["project_id"] != project_id:
                    raise ValidationError(
                        "release %r does not belong to project %r"
                        % (release_id, project_id)
                    )
            if environment_id is not None:
                self.store.get_environment(environment_id)
            plan_id = self._next_id("rlp")
            record = {
                "id": plan_id,
                "project_id": project_id,
                "release_id": release_id,
                "environment_id": environment_id,
                "stages": stages,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._release_plans[plan_id] = record
            self._audit(actor, "ext_release_plan_create", plan_id,
                        details={"project_id": project_id})
            return self._copy(record)

    def get_release_plan(self, plan_id, actor=None):
        """Return one release-plan record. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            return self._copy(
                self._get(self._release_plans, plan_id, "release plan")
            )

    def list_release_plans(self, project_id=None, actor=None):
        """Return release-plan records. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            return self._list(self._release_plans, project_id)

    def record_release_stage(self, plan_id, stage_name, status, actor, note=None):
        """Record one stage outcome for a release plan, as reported.

        Action: release_write. The stage must be one of the
        plan's recorded stages; the status is a recorded label,
        not an execution claim (``executed_here: False``).
        """
        self._require_actor(actor, "release_write", plan_id)
        _validate_non_empty(stage_name, "stage_name")
        if status not in RELEASE_STAGE_STATUSES:
            raise ValidationError(
                "status must be one of %s"
                % (", ".join(RELEASE_STAGE_STATUSES),)
            )
        _validate_optional_str(note, "note")
        with self._lock:
            plan = self._get(self._release_plans, plan_id, "release plan")
            if stage_name not in {s["name"] for s in plan["stages"]}:
                raise ValidationError(
                    "stage %r is not a stage of release plan %r"
                    % (stage_name, plan_id)
                )
            stage_id = self._next_id("rls")
            record = {
                "id": stage_id,
                "plan_id": plan_id,
                "project_id": plan["project_id"],
                "stage_name": stage_name,
                "status": status,
                "note": note,
                "executed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._release_stages[stage_id] = record
            self._audit(actor, "ext_release_stage_record", stage_id,
                        details={"plan_id": plan_id, "stage_name": stage_name,
                                 "status": status})
            return self._copy(record)

    def list_release_stages(self, plan_id=None, actor=None):
        """Return release-stage records. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            records = sorted(
                self._release_stages.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if plan_id is not None:
                records = [r for r in records if r["plan_id"] == plan_id]
            return [self._copy(r) for r in records]

    def record_data_migration(self, plan_id, migration_ref, status, actor,
                              rows_reported=None):
        """Record a data migration attached to a release plan.

        Action: release_write. The status and row count are as
        reported by the external migration tooling; nothing is
        migrated in this build (``executed_here: False``).
        """
        self._require_actor(actor, "release_write", plan_id)
        _validate_non_empty(migration_ref, "migration_ref")
        if status not in MIGRATION_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(MIGRATION_STATUSES),)
            )
        if rows_reported is not None:
            _validate_non_negative_int(rows_reported, "rows_reported")
        with self._lock:
            plan = self._get(self._release_plans, plan_id, "release plan")
            migration_id = self._next_id("mig")
            record = {
                "id": migration_id,
                "plan_id": plan_id,
                "project_id": plan["project_id"],
                "migration_ref": migration_ref,
                "status": status,
                "rows_reported": rows_reported,
                "executed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._data_migrations[migration_id] = record
            self._audit(actor, "ext_data_migration_record", migration_id,
                        details={"plan_id": plan_id,
                                 "migration_ref": migration_ref,
                                 "status": status})
            return self._copy(record)

    def list_data_migrations(self, plan_id=None, actor=None):
        """Return data-migration records. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            records = sorted(
                self._data_migrations.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            )
            if plan_id is not None:
                records = [r for r in records if r["plan_id"] == plan_id]
            return [self._copy(r) for r in records]

    def release_plan_view(self, plan_id, actor=None):
        """Derive a release plan's state at read.

        Action: release_read. Per-stage latest recorded status,
        and an overall state derived from them: no stage records
        -> ``not_started``; any stage's latest status ``failed``
        -> ``failed``; every stage's latest status in
        {``succeeded``, ``skipped``} -> ``completed``; otherwise
        ``in_progress``. Computed at call time; the stored plan
        record carries no status field.
        """
        self._maybe_require(actor, "release_read")
        with self._lock:
            plan = self._get(self._release_plans, plan_id, "release plan")
            latest = {}
            for stage_record in sorted(
                self._release_stages.values(),
                key=lambda r: int(r["id"].rsplit("-", 1)[1]),
            ):
                if stage_record["plan_id"] == plan_id:
                    latest[stage_record["stage_name"]] = stage_record["status"]
            stages = [
                {
                    "name": stage["name"],
                    "kind": stage["kind"],
                    "latest_status": latest.get(stage["name"]),
                }
                for stage in plan["stages"]
            ]
            if not latest:
                overall = "not_started"
            elif any(status == "failed" for status in latest.values()):
                overall = "failed"
            elif all(
                latest.get(stage["name"]) in ("succeeded", "skipped")
                for stage in plan["stages"]
            ):
                overall = "completed"
            else:
                overall = "in_progress"
            return {
                "plan_id": plan_id,
                "stages": stages,
                "overall_status": overall,
                "method": RELEASE_PLAN_VIEW_METHOD,
            }

    # -- Stub engines: labeled reference implementations -------------------
    #
    # Each record carries reference_stub: True and status
    # "recorded_reference_only". Creating one changes no core
    # record (pinned by test); the audit entries are the core
    # log's own append-only record of the extension mutation.

    def _record_reference(self, kind, project_id, actor, fields, audit_details):
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

    def record_repository_reference(self, project_id, host_ref, actor,
                                    default_branch_label=None):
        """Reference record for code hosting internals (idx 304).

        Action: project_write. Points at an external host by
        opaque reference; no git storage, branching, or merging
        exists in this build (``stored_here: False``).
        """
        _validate_non_empty(host_ref, "host_ref")
        _validate_optional_str(default_branch_label, "default_branch_label")
        return self._record_reference(
            "repository", project_id, actor,
            {"host_ref": host_ref,
             "default_branch_label": default_branch_label,
             "stored_here": False},
            {"host_ref": host_ref},
        )

    def record_configuration_reference(self, project_id, config_ref, actor,
                                       format_label=None):
        """Reference record for configuration-as-code execution (idx 306).

        Action: project_write. The configuration is referenced,
        never executed (``executed_here: False``).
        """
        _validate_non_empty(config_ref, "config_ref")
        _validate_optional_str(format_label, "format_label")
        return self._record_reference(
            "configuration", project_id, actor,
            {"config_ref": config_ref,
             "format_label": format_label,
             "executed_here": False},
            {"config_ref": config_ref},
        )

    def record_assessment_reference(self, project_id, framework_ref,
                                    status_label, actor):
        """Reference record for compliance assessment & KSI automation (idx 307).

        Action: project_write. The status label is recorded
        verbatim, as reported by an external assessor; nothing is
        assessed in this build (``assessed_here: False``).
        """
        _validate_non_empty(framework_ref, "framework_ref")
        _validate_non_empty(status_label, "status_label")
        return self._record_reference(
            "assessment", project_id, actor,
            {"framework_ref": framework_ref,
             "status_label": status_label,
             "assessed_here": False},
            {"framework_ref": framework_ref},
        )

    def record_model_reference(self, project_id, model_ref, actor,
                               kind="business_model"):
        """Reference record for business modeling & automation (idx 308).

        Action: project_write. The model is referenced, never
        executed (``executed_here: False``).
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

    def record_authoring_reference(self, project_id, content_ref, actor,
                                   format_label=None):
        """Reference record for course & content authoring tools (idx 309).

        Action: project_write. The content is referenced, never
        authored or stored in this build (``authored_here: False``).
        """
        _validate_non_empty(content_ref, "content_ref")
        _validate_optional_str(format_label, "format_label")
        return self._record_reference(
            "authoring", project_id, actor,
            {"content_ref": content_ref,
             "format_label": format_label,
             "authored_here": False},
            {"content_ref": content_ref},
        )

    def record_provisioning_reference(self, project_id, zone_ref, actor,
                                      environment_id=None):
        """Reference record for landing-zone / tenant provisioning (idx 310).

        Action: project_write. Optionally binds a core environment
        record; nothing is provisioned in this build
        (``provisioned_here: False``).
        """
        _validate_non_empty(zone_ref, "zone_ref")
        if environment_id is not None:
            self.store.get_environment(environment_id)
        return self._record_reference(
            "provisioning", project_id, actor,
            {"zone_ref": zone_ref,
             "environment_id": environment_id,
             "provisioned_here": False},
            {"zone_ref": zone_ref},
        )

    def record_posture_reference(self, project_id, monitor_ref, actor,
                                 finding_ref=None,
                                 remediation_status="reported_open"):
        """Reference record for posture monitoring & remediation (idx 315).

        Action: project_write. The remediation status is recorded
        as reported; nothing is monitored or remediated in this
        build (``monitored_here: False``, ``remediated_here:
        False``).
        """
        _validate_non_empty(monitor_ref, "monitor_ref")
        _validate_optional_str(finding_ref, "finding_ref")
        if remediation_status not in REMEDIATION_STATUSES:
            raise ValidationError(
                "remediation_status must be one of %s"
                % (", ".join(REMEDIATION_STATUSES),)
            )
        return self._record_reference(
            "posture", project_id, actor,
            {"monitor_ref": monitor_ref,
             "finding_ref": finding_ref,
             "remediation_status": remediation_status,
             "monitored_here": False,
             "remediated_here": False},
            {"monitor_ref": monitor_ref},
        )

    def record_integration_reference(self, project_id, system_ref, actor,
                                     direction="outbound"):
        """Reference record for external-system integration engines (idx 317).

        Action: project_write. The external system is referenced;
        no connector executes in this build
        (``executed_here: False``, ``reference_transport: True``).
        """
        _validate_non_empty(system_ref, "system_ref")
        if direction not in INTEGRATION_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s"
                % (", ".join(INTEGRATION_DIRECTIONS),)
            )
        return self._record_reference(
            "integration", project_id, actor,
            {"system_ref": system_ref,
             "direction": direction,
             "executed_here": False,
             "reference_transport": True},
            {"system_ref": system_ref},
        )

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
                records = [r for r in records if r["project_id"] == project_id]
            return [self._copy(r) for r in records]
