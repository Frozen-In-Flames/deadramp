# Final GAPS batch — Group 17, Development Tools L1

Unit: section "Group 17 — Development Tools L1 (5 forks)" of the
repo-root `GAPS.md` — the 9 open Extended entries (inventory
idx 174–182). Built per `gaps-batch/DECISION.md` and
`PLATFORM-LAYER.md`; this file is the per-entry disposition
record. The extension code is `src/devtools/extensions.py`
(`DevToolsExtensions`, wrapping the core store); all core modules
are byte-identical to the shipped build (SHA-256 of `store.py`
recorded before and after the build: identical). Tests:
`tests/test_gaps_batch.py` — 43 new tests, suite 66 → 109, all
passing. The Development Tools L2 batch unit
(`groups/development-tools-l2/BATCH.md`) shipped this category's
families at Moderate;
its adjudicated forms are mirrored here wherever this tier's spec
and core support them (execution-shaped families as
request/outcome records, reported values verbatim and never
interpreted). No Moderate apparatus is imported: the L1 core has
no pipeline-definition objects and no feature-flag registry, so
the L2 unit's pipeline records and computable flag evaluation
have no L1 counterpart and are not simulated.

## Build-extension entries (3)

### idx 174 — CI/CD execution engines (pipeline execution: build / test / deploy runners)

**Disposition: built** (in the adjudicated records form).

The core build record — with its `config` held as a record — is
the pipeline definition this tier's substrate carries (Core 4 of
UNION-SPEC: "pipeline definitions are records (config carried on
the build record) and nothing executes them"). The execution
engine therefore closes as:

- `request_pipeline_run(project_id, actor, build_id=None,
  runner_ref=None, stage_label=None)` → a pipeline run *request*
  record (`run-N`) bound to a core build record of the same
  project (a build of another project is rejected; an unknown
  build raises `NotFoundError` and consumes no id). The record
  carries `executed_here: False` and **no status field** — a
  request pinned by test to change no core build record
  (`test_request_and_outcome_leave_core_build_unchanged`).
- `record_run_outcome(run_id, actor, status, runner_ref=None)` →
  a run *outcome* record (`out-N`); the status is the external
  runner's report, restricted to the core build-status
  vocabulary and stored verbatim.
- `pipeline_run_view(run_id)` derives the run's current reported
  status at read from its outcome records (`requested` before
  any outcome) via the `_derive_run_status` seam; stored
  nowhere. This seam is the batch's fresh negative control (see
  below).

Nothing in this build runs a pipeline; the runner is external
and its results arrive as records.

### idx 176 — Compilers & build toolchains

**Disposition: built.**

`register_toolchain(project_id, name, actor, language=None,
version_label=None)` → a toolchain declaration record (`tch-N`:
name, language, version label as data), `executed_here: False`;
plus `get_toolchain` / `list_toolchains`. The record declares
the toolchain a real build used; no compiler ships in this
substrate, and none is simulated.

### idx 182 — Artifact binary storage backends (the registry holds records + checksums only; verification is by content hash)

**Disposition: built** (custody-accounting form; the entry's own
bounding text is the design).

- `register_storage_backend(name, actor, kind=…)` → a
  storage-backend record (`stb-N`; kinds: object store,
  filesystem, archive, custom), `content_held_here: False`.
- `record_artifact_custody(artifact_id, backend_id, actor,
  custodian_ref=None)` → a custody record (`plm-N`) binding a
  core artifact to a backend, copying **only** the artifact
  record's SHA-256 checksum and recorded size, plus an opaque
  custodian reference. No content is accepted or held anywhere
  (`content_held_here: False`; no `content` field exists —
  pinned by test).
- `storage_backend_summary(backend_id)` derives placements,
  total size, and an explicit unknown-size count (checksum-only
  artifacts carry no size and are counted separately, never
  silently zeroed) at read from the custody records.

The core registry's verify-by-content function is untouched and
remains the only verification path — pinned by
`test_verify_by_content_unchanged_after_custody` (original bytes
verify `True`, tampered bytes `False`, after custody records
exist). The byte plane itself is not here: the founding boundary
is structural (the registry holds records + checksums only), and
this unit closes the *backend bookkeeping* the entry names, not
a binary store.

## Stub-engine entries (6) — labeled reference implementations

All six ship as records carrying `reference_stub: True` and
status `recorded_reference_only` (assessment jobs and course
records carry the same labels on their own record types), and
creating any of them changes no core record — pinned by
`test_stubs_change_no_core_record` over all eight core record
sets.

### idx 175 — Code hosting internals (git storage, branching & merging engines)

**Disposition: reference.**

`record_repository_reference` → a repository reference record
(opaque host reference, default-branch label) with
`stored_here: False` and `merged_here: False`;
`record_branch_record` → branch metadata records against a
repository reference (rejected for any other reference kind).
No git object storage, branching, or merging exists here, and
no record field can hold object content (pinned:
`test_reference_shape_and_labels` asserts no `content` key).

### idx 177 — Configuration-as-code execution & orchestration

**Disposition: reference.**

`record_configuration_reference` → a configuration definition
held as data (opaque reference + format label) with
`applied_here: False` and `executed_here: False` — the registry
never executes. `record_apply_outcome` records apply outcomes
reported by the external configuration tooling, verbatim.

### idx 178 — Compliance assessment & KSI status automation engines

**Disposition: reference.**

`create_assessment_job` → an assessment job record (opaque
framework reference, optional opaque KSI reference) with
`assessed_here: False`; `record_assessment_status` stores
reported status labels **verbatim, never interpreted**;
`assessment_job_view` derives the latest reported status at read
(the stored job record carries no reported-status field). No
compliance score is computed anywhere on the extension surface —
pinned by a recursive key scan
(`test_no_score_field_anywhere`) over every extension record
type and view. Supported assessment/content *records* are
already core (the group's UNION-SPEC places the automation
engines, not the records, in Extended); this unit closes the
engine entry in reference form.

### idx 179 — Business modeling & automation engines (modeling + execution)

**Disposition: reference.**

`record_model_reference` → a model definition held as data
(opaque reference + kind label: business model or workflow
automation), `executed_here: False`;
`request_model_execution` → execution *request* records against
a model definition (rejected for other reference kinds). The
external modeling/automation engine is what would run a model;
nothing executes here.

### idx 180 — Course & content authoring tools

**Disposition: reference.**

`create_course_record` → a course record as metadata (title,
format label) with `authored_here: False`;
`record_course_asset` → asset records as metadata (opaque
reference + format label); `record_course_outcome` → outcome
labels reported by the external authoring tool, verbatim.
Authored content is never held — no record field can hold
content (pinned by test).

### idx 181 — Landing-zone / tenant provisioning & hosted platform operations

**Disposition: reference.**

`record_provisioning_reference` → a provisioning reference
record (opaque zone reference, optional binding to a core
environment record) with `provisioned_here: False` and
`hosted_here: False`, per PLATFORM-LAYER.md decision 6:
provisioning and hosting are platform-layer properties of the
deployment, not functions this build performs or claims.
Supported environment/deployment *records* are already core.

## Cross-cutting invariants pinned by the batch tests

- **Nothing executes.** Every build-family record carries
  `executed_here: False`; every reference record carries its
  `*_here: False` label(s) (`stored_here`, `merged_here`,
  `applied_here`, `assessed_here`, `provisioned_here`,
  `hosted_here`, `authored_here`, `content_held_here`).
- **Reported values are verbatim.** Run outcome statuses (core
  vocabulary), apply outcome labels, assessment status labels,
  and course outcome labels are stored exactly as reported and
  never interpreted; derivations read them, they do not rewrite
  them.
- **Derived, never stored.** Run views, assessment views, and
  backend summaries are computed at call time; the stored run
  request has no status field and the stored assessment job has
  no reported-status field (both pinned).
- **Validation before mutation.** Failed operations consume no
  id and change nothing (pinned for run requests and run
  outcomes); RBAC is enforced before any state change, and
  denied attempts are audited as `<action>:denied` on the core
  append-only log (pinned for a viewer run request). Extension
  mutations audit with `ext_`-prefixed actions.
- **RBAC mapping** (the core action set is fixed): run requests,
  run outcomes, and toolchains ride the build family; backends
  and custody ride the artifact family; assessment jobs and
  status reports ride the review family; reference, branch, apply
  outcome, model execution, and course records ride the project
  family.

## Fresh negative control

The pipeline-run status derivation seam `_derive_run_status`
(latest reported outcome decides; earliest-outcome derivation is
the mutant). In-suite three-part form in
`TestNegativeControlRunStatusDerivation`, plus a live file
mutation drill recorded in `tests/README.md`: replacing the
seam's line with `outcomes[0]` makes exactly 2 tests fail
(`test_control_passes`,
`test_outcomes_verbatim_and_view_derives_latest`); restored,
the suite is green.

## Re-judgments

None. All 9 entries landed at their drafted dispositions (3
build-extension, 6 stub-engine); no entry needed re-judgment
under DECISION.md qualification 1. The two tier adaptations
relative to the L2 unit are recorded above as design facts, not
re-judgments: the L1 core carries pipeline definitions on build
records rather than as pipeline objects (idx 174 binds there),
and the L2 unit's computable feature-flag evaluation has no L1
analogue because this tier's spec claims no flag family.
