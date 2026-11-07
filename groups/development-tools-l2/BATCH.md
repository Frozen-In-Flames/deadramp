# Final GAPS batch — Group 29, Development Tools L2

Unit: the 15 open entries of the GAPS.md section "Group 29 —
Development Tools L2 (2 forks)" (inventory idx 303–317).
Dispositions follow the ratified triage in
`../../gaps-batch/inventory.json` and the batch pattern in
`../../gaps-batch/DECISION.md`. Built 2026-11-07.

## What landed

One new module, `src/devtools/extensions.py`, class
`DevToolsExtensions`, wrapping the core `DevToolsStore`. The
seven pre-existing core modules (`__init__`, `__main__`,
`access`, `audit`, `errors`, `service`, `store`) are
byte-identical to the shipped build — SHA-256 re-verified
against the UNION-SPEC contract table before and after the
batch. No core change was needed and none was made. The
extension only *reads* core records (to bind extension records
to real projects, builds, releases, artifacts, environments)
and appends to the core audit log with `ext_`-prefixed actions;
extension records live in the extension object, and no core
record set is ever written by it.

Doctrines carried from the core, unchanged: opaque `*_ref`
strings only; derived-never-stored (flag evaluation results,
experiment summaries, gate verdicts, backend summaries, and the
release plan view are computed at call time and stored
nowhere); validation fully before mutation, so a failed
operation consumes no id and changes nothing; append-only audit
including denied attempts (`<action>:denied`, exactly as the
core store); RBAC via the core `access` module, enforced
before any state change. Python standard library only
(verified with the group's `scratch/verify_deps.py`: OK).

RBAC action mapping (the core action set is fixed): pipelines,
pipeline runs, and toolchains ride the build family
(`build_write` / `build_read`); storage backends and placements
ride the artifact family; feature flags and experiments ride
the deployment family (the feature-release surface); rule sets,
quality profiles, and analysis results ride the review family;
release plans, stage records, and migration records ride the
release family; stub reference records ride `project_write` /
`project_read`.

Tests: `tests/test_gaps_batch.py` (43 tests). Suite 78 → 121,
all passing. Fresh negative control: the kill-switch-blind flag
evaluation, with the mutation drill on the real file producing
exactly 2 failures; recorded in `tests/README.md`.

## Per-entry dispositions

### Build-extension (7) — all closed as built, no re-judgment

**idx 303 — "CI/CD execution engines (pipeline execution:
build / test / deploy runners; claimed 1 of 2 here)"** —
`define_pipeline` (ordered stage records-as-data, stage kinds
build / test / deploy / custom) and `record_pipeline_run`
(status from the core build-status vocabulary, optional binding
to a core build record, opaque `runner_ref`). Every run record
carries `executed_here: False`: runs are records of what an
external runner reported; this build runs nothing.

**idx 305 — "Compilers & build toolchains"** —
`register_toolchain`: registry records declaring the toolchain
(name, language, version label) a real build used, pinned to a
core project. `executed_here: False`; no compiler ships.

**idx 311 — "Artifact binary storage backends (the registry
holds records + checksums only)"** — `register_storage_backend`
plus `place_artifact`, which binds a core artifact to a backend
copying only the artifact record's SHA-256 checksum and size
(`stored_here: False`; no content is accepted or stored), and
`storage_backend_summary`, a read-time derivation over the
placement records (placement count, sum of known sizes,
checksum-only artifacts counted separately as
`unknown_size_count` rather than silently treated as 0). The
entry's own text binds the form and the build honors it
exactly.

**idx 312 — "Feature-flag & feature-management runtime (flag
evaluation, targeting, percentage rollouts, kill-switch)"** —
the one genuinely computable surface, built as a derivation.
Flag records hold the configuration (enabled, killed,
rollout percentage 0–100, targeted subject refs; key unique
per project). `evaluate_flag` is a pure function over the
recorded configuration under a stated rule:
`bucket = int(sha256(flag_id + ":" + subject_ref)[:8], 16) % 100`;
precedence is kill switch → disabled → targeted → rollout
(bucket below the recorded percentage) → miss. The kill switch
is a recorded state evaluation honors, behind a named seam
(`_kill_switch_active`) that the batch's negative control
guards. Evaluation results are computed at call time and
stored nowhere (pinned by test: the flag record is identical
before and after evaluations).

**idx 313 — "Experimentation engine (hypothesis-driven
development)"** — experiment records (at least two unique
variant labels, optional binding to a flag of the same
project) with a draft → running → concluded lifecycle;
`assign_subject` records an assignment whose variant is chosen
by the same stated bucketing rule (`variant index = bucket *
len(variants) // 100`), only while running, at most once per
subject; `record_experiment_outcome` stores outcome labels
verbatim and requires an existing assignment;
`experiment_summary` derives exact integer counts (assignments
per variant, outcomes per label) at read. No rates, no
significance computation — counts only, labeled as such.

**idx 314 — "Static code analysis engine (rule sets, quality
profiles & gates)"** — rule-set records (rules held as data:
{rule_ref, severity} over the recorded severity vocabulary)
and quality-profile records (a recorded gate: severity →
maximum tolerated count). `record_analysis_result` stores
finding counts as reported by an external analyzer
(`analyzed_here: False`; when a rule set is named, finding
rule_refs must be among its recorded rules).
`evaluate_quality_gate` derives the verdict at read: recorded
gate thresholds against the recorded reported counts summed
per severity, breaches enumerated, ungated severities reported
separately. No code is analyzed anywhere in this build.

**idx 316 — "Release automation, environment management &
data migration engine"** — release-plan records (stage kinds
deployment / data_migration / verification / custom; optional
binding to a core release and a core environment),
`record_release_stage` (stage outcomes as recorded labels,
stage must be one of the plan's recorded stages), and
`record_data_migration` (status and row count as reported,
`executed_here: False`). `release_plan_view` derives the
per-stage latest status and the overall state
(not_started / in_progress / failed / completed) at read; the
stored plan record carries no status field.

### Stub-engine (8) — all closed as reference, no re-judgment

Each is a single labeled reference-record family on
`DevToolsExtensions`, bound to a core project, carrying
`reference_stub: True` and status `recorded_reference_only`.
Pinned by test: creating all eight changes no core record set
(counts of all eight core record sets identical before and
after).

**idx 304 — "Code hosting internals (git storage, branching &
merging engines; 0 claims here)"** — `record_repository_reference`:
opaque `host_ref` + optional default-branch label;
`stored_here: False`. No git storage exists in this build.

**idx 306 — "Configuration-as-code execution & orchestration
(0 claims here; \"strict configuration control\" is a recorded
near-miss)"** — `record_configuration_reference`: opaque
`config_ref` + optional format label; `executed_here: False`.
The near-miss stays a near-miss: the reference records the
configuration, it does not claim configuration control.

**idx 307 — "Compliance assessment & KSI status automation
engines (0 claims here)"** — `record_assessment_reference`:
`framework_ref` + `status_label` recorded verbatim as reported
by an external assessor; `assessed_here: False`.

**idx 308 — "Business modeling & automation engines (modeling
plus execution)"** — `record_model_reference`: opaque
`model_ref`, kind business_model or workflow_automation;
`executed_here: False`.

**idx 309 — "Course & content authoring tools"** —
`record_authoring_reference`: opaque `content_ref` + optional
format label; `authored_here: False`.

**idx 310 — "Landing-zone / tenant provisioning & hosted
platform operations (0 claims here; \"environment management\"
near-miss)"** — `record_provisioning_reference`: opaque
`zone_ref`, optionally bound to a core environment record;
`provisioned_here: False`.

**idx 315 — "Security posture monitoring & automated
remediation engine"** — `record_posture_reference`: opaque
`monitor_ref`, optional `finding_ref`, remediation status
recorded as reported (reported_open / reported_remediated /
reported_accepted); `monitored_here: False`,
`remediated_here: False`.

**idx 317 — "External-system integration engines (claimed 1
of 2 here)"** — `record_integration_reference`: opaque
`system_ref`, direction inbound or outbound;
`executed_here: False` and `reference_transport: True` (the
house transport label). The one claim behind this entry is the
core's existing api_integrations claim surface; the reference
record adds no execution.

## Re-judgments

None. Every entry fit its drafted disposition on close reading
of the group's spec: the seven build-extension entries all
admit the records-plus-derivations form (the flag runtime is
genuinely computable as a pure derivation, exactly as the
batch brief anticipated), and the eight stub-engine entries
are recorded as labeled reference implementations per their
drafted triage.

## Out of scope, not touched

The inventory section "Remainder Addition — Development Tools
L2 (+4 forks)" is a separate unit with its own two entries
(the no-code / low-code platform entry and the compliance
documentation & SSP generation tooling entry). They are not
part of this unit and were not absorbed or modified here.

## Verification (builder-side)

- Full suite: 78 tests before, **121 tests after, OK**
  (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Mutation drill: `_kill_switch_active` in the real
  `extensions.py` patched to `return False`; full suite →
  exactly 2 failures (`test_kill_switch_and_restore`,
  `test_kill_switch_ignoring_mutant_is_rejected`); file
  restored from the pre-mutation copy and SHA-256-verified
  (`a3b7598b6166a42cdd0dcf321f17e5d9a991ca3f46f3841a00c662bf6a0e734d`);
  suite re-run green. Raw output:
  `scratch/gaps_mutation_run.txt`.
- Core byte-identity: all seven core modules re-hashed after
  the batch; identical to the pre-batch hashes and to the
  UNION-SPEC contract table.
- Dependency check: `scratch/verify_deps.py` re-run — stdlib
  only, no third-party imports (the new module adds `copy`).
- Live smoke (in-process): flag created → rollout 100 →
  evaluation serves via rollout → kill → evaluation returns
  `served: False`, reason `kill_switch`; pipeline defined and a
  run recorded with `executed_here: False`; all extension
  mutations present in the audit log with `ext_` actions.
