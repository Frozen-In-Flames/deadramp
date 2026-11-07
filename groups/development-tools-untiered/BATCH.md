# Final GAPS batch — Untiered Set 6, Development Tools (tier null)

Unit: the 7 open entries of the GAPS.md section "Untiered Set 6 —
Development Tools (7 forks, tier null)" (inventory idx 796–802).
Dispositions follow the ratified triage in
`../../gaps-batch/inventory.json` and the batch pattern in
`../../gaps-batch/DECISION.md`, with ONE re-judgment under
DECISION.md qualification 1 (idx 796, below). Built 2026-11-07.

## What landed

One new module, `src/devtools/extensions.py`, class
`DevToolsExtensions`, wrapping the core `DevToolsStore`. The
seven pre-existing core modules (`__init__`, `__main__`,
`access`, `audit`, `errors`, `service`, `store`) are
byte-identical to the shipped build — SHA-256 re-verified
against the group README's accounting table before and after
the batch. No core change was needed and none was made. The
extension only *reads* core records (to bind extension records
to real projects, builds, reviews, environments, deployments)
and appends to the core audit log with `ext_`-prefixed actions;
extension records live in the extension object, and no core
record set is ever written by it.

**Tier discipline on the new surface:** this set is untiered,
so the extension asserts no baseline, assigns no tier, and
draws no CMMC equivalence — and no extension record or derived
view carries a tier, baseline, or impact-level key. That is
pinned by a recursive key scan over every extension record
family and derived view in `tests/test_gaps_batch.py`
(`test_tier_null_scan_over_extension_surface`), the
extension-surface counterpart of `test_specs.py`'s sheet pins.
Documented control claims stay exactly where the union spec
put them: the forks' claims about themselves, recorded in
`UNION-SPEC.md`; this unit adds no control claim of its own.

Doctrines carried from the core, unchanged: opaque `*_ref`
strings only; derived-never-stored (conversion stage status,
promotion state, support case state, workspace latest state
are computed at call time and stored nowhere); validation
fully before mutation, so a failed operation consumes no id
and changes nothing; append-only audit including denied
attempts (`<action>:denied`, exactly as the core store); RBAC
via the core `access` module, enforced before any state
change. Python standard library only (verified with the
group's `scratch/verify_deps.py`: OK; the new module adds
`copy`). The extension surface is store-level only, like the
L1/L2 batch units — no HTTP routes were added; the shipped
service and CLI are untouched.

RBAC action mapping (the core action set is fixed): AI request
and outcome records and governance policies ride the project
family (`project_write` / `project_read`); workspaces and
promotions ride the deployment family; conversion jobs and
gate checks ride the build family; detection scan requests
and findings ride the review family (code-examination
records); support cases and events ride the issue family.

Tests: `tests/test_gaps_batch.py` (34 tests). Suite 74 → 108,
all passing. Fresh negative control: the conversion stage
derivation seam, with the mutation drill on the real file
producing exactly 3 failures; recorded in `tests/README.md`.

## Per-entry dispositions

### idx 796 — "AI code-generation & AI-agent development engines"

**Drafted: build-extension. Landed: reference (RE-JUDGED).**

`record_ai_request` (kind `code_generation` or `agent_task`,
opaque `request_ref`, optional opaque `model_ref`) and
`record_ai_outcome` (outcome label stored verbatim, optional
opaque `result_ref`); `ai_request_view` derives the current
reported outcome at read from the outcome records — the stored
request record carries no outcome field. Every request record
carries `reference_stub: True`, status
`recorded_reference_only`, and `inference_here: False`,
`generated_here: False`, `agent_executed_here: False`.

**Grounds for the re-judgment (DECISION.md qualification 1):**
on close reading of the owning group's spec, this entry does
not fit the records-plus-derivation form that closes a
build-extension entry. The entry names the models and agent
runtimes *themselves* (Cursor's AI-assisted development,
Replit's AI agent, Elixium's agent drafting, Linear's agent
workflows), and the founding union spec assigns them to
Extended precisely because "this build contains no inference
of any kind" — a standing design statement of this group, not
a gap in effort. A code-generation or agent "engine" in
records form would be request records plus opaque result
references with the inference half stated absent, which is
exactly the labeled reference form the house precedent ships
for engine entries — the same form the sibling tiered units
used for their stub-engine entries, and the form the batch
brief itself prescribes for AI-shaped entries. The drafted
build-extension token would have claimed a build where the
honest artifact is a reference implementation, so the
disposition is corrected here and the entry closes as
`reference`. Only the token changes: the records surface above
is what either disposition would have shipped.

### idx 797 — "Cloud development environments (hosted IDE workspaces)"

**Disposition: built** (workspace declaration + session
records).

`create_workspace` (bound to a core project; access modes
recorded as labels from the fork's documented access prose —
`browser` / `ssh` — deduplicated, unknown modes rejected) and
`record_workspace_session` (opaque subject ref, reported
status verbatim from `reported_active` / `reported_idle` /
`reported_closed`); `workspace_view` derives session counts
per reported status and the latest reported status at read —
the stored workspace record carries no status field. Every
record carries `hosted_here: False`,
`provisioned_here: False`, `filesystem_held_here: False`: the
workspace is hosted by an external platform, and no workspace
filesystem is ever held here. Near-the-line, stated plainly:
hosting itself is a platform-layer property
(PLATFORM-LAYER.md decision 6) and is *not* built; what is
built is the workspace/session records surface the entry's
subject matter presupposes, in the same form the Talent
Management L2 unit's virtual-event platform declarations
closed at Moderate.

### idx 798 — "Legacy modernization & code-conversion engines"

**Disposition: built** (conversion job records).

`create_conversion_job` holds the five stages Moderniza's own
description names — Blueprint, Contract, Code, Testing,
Deploy — as data on the job record, with source and target as
opaque references plus optional SHA-256 digests (validated as
64-character lowercase hex; code itself is never accepted or
held). `record_conversion_stage` records stage outcomes as
reported labels (`reported_pending` / `reported_in_progress`
/ `reported_completed` / `reported_failed`); a stage outside
the job's recorded five is rejected.
`conversion_job_view` derives each stage's latest reported
status and the overall state (`not_started` / `in_progress` /
`failed` / `completed`) at read via the
`_derive_conversion_stage` seam — the batch's fresh negative
control (below). `converted_here: False` and
`code_held_here: False` on job and stage records alike.

### idx 799 — "CI/CD governance & promotion-gating engines"

**Disposition: built** (gate-check and promotion records over
the substrate's own records).

`record_gate_check` binds a check to at most one recorded
subject — a core build, review, or deployment of the *same*
project (cross-project subjects and multi-subject checks are
rejected) — and optionally to a governance policy of the same
project (idx 801); its outcome is a label reported by the
external gating engine (`reported_passed` / `reported_failed`
/ `reported_waived`), stored verbatim. A check changes no core
record — pinned by test (the subject build record is identical
before and after). `record_promotion` records a promotion
between two distinct core environments, optionally citing a
core release and a governance policy of the project;
`record_promotion_outcome` records outcome labels verbatim,
including `reported_mismatch` and `reported_stalled` — the
notification cases KineticCode's own prose names.
`promotion_view` derives the current reported state at read;
the stored promotion record carries no status field.
`gated_here: False`, `enforced_here: False`,
`promoted_here: False` throughout: gating executed against
live pipelines is the engine half, and it is stated absent —
what is built governs this substrate's own records.

### idx 800 — "Secrets & sensitive-data detection engines"

**Disposition: reference** (as drafted; stub-engine).

`record_detection_scan` (opaque `scan_ref`, optional opaque
`target_ref`) and `record_detection_finding` (finding kind
from the categories the fork's prose names — `secret`,
`token`, `credential`, `cui_marking`, `fci_marking`,
`risky_pattern` — an opaque `location_ref`, and a severity
label stored verbatim as the scanner reported it). Records
carry `reference_stub: True` (scans also status
`recorded_reference_only`) and `scanned_here: False`,
`detected_here: False`. Detection is an engine run over code
content, and this substrate never holds code content — the
core artifact registry's checksums-only discipline is
unchanged — so findings arrive as reports, never as
detections made here. A finding against an unknown scan is a
`NotFoundError`; a bad kind is rejected with no id consumed.

### idx 801 — "Pipeline governance configuration records (the category's standing records-configuration gap, claimed in substance here)"

**Disposition: built** (configuration records held as data).

`create_governance_policy` records gating rules, approval
requirements, coverage thresholds, and promotion policies as
configuration data: rules are `{rule_ref, kind, requirement}`
objects with kind in `gate` / `approval` / `coverage` /
`promotion` and unique `rule_ref`s; the promotion sequence is
an ordered list of environment names (KineticCode's strict
sequential Dev, Test, Stage, Prod promotion is the recorded
shape; duplicates rejected); the coverage threshold is an
integer percentage 0–100. The records carry
`enforced_here: False` and `executed_here: False`: a policy
is a definition held as data — it is never evaluated or
enforced against a live pipeline, and gate checks (idx 799)
may cite it as a reference without inheriting enforcement.

### idx 802 — "Fork excess: customer support platform"

**Disposition: built** (support case records).

`create_support_case` (channel from the four Elixium's
description names — `in_app_chat`, `support_ticket`,
`support_email`, `support_phone` — optional opaque subject
ref) and `record_support_event` (event labels `opened` /
`responded` / `escalated` / `resolved` / `closed`, stored
verbatim); `support_case_view` derives the case's current
state at read from its event records — the stored case record
carries no status field. The boundary is stated on the
records: channels are labels over a transport this build does
not operate (`reference_transport: True`,
`delivered_here: False`), and no message content can exist on
any record (`messages_held_here: False`; there is no message
field). The founding union spec assigns this function to
another category's union and names it here so it is not
silently dropped; the gap was registered in *this* section,
so it closes here in the records form this substrate supports,
with the cross-category note preserved rather than erased.

## Re-judgments

One: idx 796, drafted build-extension, landed reference, with
grounds stated at the entry above (the entry names the models
and agent runtimes themselves; the founding spec's
no-inference design statement governs; the honest records form
for such an entry is the labeled reference form). The other
six entries landed at their drafted dispositions (five
build-extension built, one stub-engine reference).

## Fresh negative control

The conversion stage derivation seam
`_derive_conversion_stage` (the latest recorded outcome
decides a stage's current reported status; earliest-outcome
derivation is the mutant). In-suite three-part form in
`TestNegativeControlConversionDerivation`, plus a live file
mutation drill recorded in `tests/README.md`: replacing the
seam's line with `outcomes[0]` makes exactly 3 tests fail
(`test_job_view_derives_latest_stage_status`,
`test_control_passes`, and the canonical leg of
`test_earliest_outcome_mutant_is_rejected`, which asserts the
literal canonical value against the real implementation);
restored, the suite is green.

## Verification (builder-side)

- Full suite: 74 tests before, **108 tests after, OK**
  (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Mutation drill: `_derive_conversion_stage` in the real
  `extensions.py` patched (`outcomes[-1]` → `outcomes[0]`);
  full suite → exactly 3 failures (named above); file restored
  from the pre-mutation copy and SHA-256-verified
  (`483d234232f04dfc14c989f0045c4d5bdb7c93a22b1876dff65aeecc521d2bfe`);
  suite re-run green. Raw output:
  `scratch/gaps_mutation_run.txt`.
- Core byte-identity: all seven core modules re-hashed after
  the batch; identical to the pre-batch hashes and to the
  group README's accounting table.
- Dependency check: `scratch/verify_deps.py` re-run — stdlib
  only, no third-party imports (the new module adds `copy`).
- Live smokes: the founding `scratch/smoke.py` still passes
  against the untouched core (SMOKE OK); an in-process smoke
  of the extension surface drove governance policy →
  conversion job + stage → workspace + session → support case,
  with all extension mutations present in the audit log under
  `ext_` actions.
