# Final GAPS batch — Remainder Singleton 58, Development Tools L3-adjacent

Unit: the 4 open entries of the GAPS.md section "Remainder
Singleton 58 — Development Tools L3-adjacent (1 fork)"
(inventory idx 701–704). Dispositions follow the ratified
triage in `../../gaps-batch/inventory.json` and the batch
pattern in `../../gaps-batch/DECISION.md`. **No
re-judgments**: every entry fit its drafted disposition on a
close reading of the group's spec, in the forms below.
Built 2026-11-07.

## What landed

One new module, `src/devtools/extensions.py`, class
`DevToolsExtensions`, wrapping the core `DevToolsStore`. The
seven pre-existing core modules (`__init__`, `__main__`,
`access`, `audit`, `errors`, `service`, `store`) are
byte-identical to the shipped build — SHA-256 re-verified
against the pre-build baseline in `scratch/prebuild-src.sha256`
before and after the batch (`store.py` still `8ca50cf1…`, the
hash recorded in `tests/README.md`). No core change was needed
and none was made. The extension only *reads* core records
(to bind extension records to real projects and environments)
and appends to the core audit log with `ext_`-prefixed
actions; extension records live in the extension object, and
no core record set is ever written by it (pinned by test over
all eight core record sets).

High apparatus binds the extension, as the batch brief
requires at this tier: extension mutations land on the core
hash-chained audit log (the chain verifies `(True, None)`
after extension activity, pinned); creation is fail-closed
in the core's AU-5 posture — an audit append failure rolls
back the new record and its id allocation before the error
propagates (pinned against a broken JSONL path); the
separated `auditor` role is denied every extension read and
write, since those ride operational actions, while its core
audit duty (query, chain verification) works unchanged
(pinned). AC-7 lockout lives in the untouched core service
layer, which the extension does not modify.

Doctrines carried from the core, unchanged: opaque `*_ref`
strings only; derived-never-stored (outcome counts, session
counts, sums of recorded report counts, and latest reported
labels are computed at call time and stored nowhere);
validation fully before mutation, so a failed operation
consumes no id and changes nothing; append-only audit
including denied attempts (`<action>:denied`, exactly as the
core store); RBAC via the core `access` module, enforced
before any state change. Python standard library only
(verified with the group's `scratch/verify_deps.py`: OK).

RBAC action mapping (the core action set is fixed): cluster
references, cluster outcomes, telemetry sources, and
telemetry reports ride the project family, as the L2 unit's
reference records did; workspaces, workspace sessions,
network routes, route outcomes, and network policies ride
the deployment family (the environment surface), as core
environments and deployments do.

Tests: `tests/test_gaps_batch.py` (26 tests). Suite 122 →
148, all passing. Fresh negative control: the latest-label
derivation seam, with the mutation drill on the real file
producing exactly 5 failures; recorded in `tests/README.md`.

## Per-entry dispositions

### idx 701 — "Container orchestration platform: the managed container platform the fork is (the Core holds development-work records; it runs no containers)"

**Drafted: stub-engine. Landed: reference (as drafted).**

`record_cluster_reference` (opaque `platform_ref`) plus
`record_cluster_outcome` records whose status labels are the
platform's own reports, stored verbatim; `cluster_reference_view`
derives the outcome count and the latest reported status at
read via the `_latest_label` seam — the stored reference
record carries no status field beyond its
`recorded_reference_only` marker. Every record carries
`reference_stub: True` and `orchestrated_here: False` /
`containers_run_here: False` / `managed_here: False`: the
entry's own parenthetical is the design — the Core holds
development-work records and runs no containers, so the
platform itself ships as the labeled reference form the
house precedent prescribes for stub-engine entries.

### idx 702 — "Integrated development environment / developer workspace"

**Drafted: build-extension. Landed: built (as drafted).**

`create_workspace` (bound to a core project; access modes
recorded as labels from the recorded vocabulary — `browser`
/ `ssh` / `desktop_client` — deduplicated, unknown modes
rejected) and `record_workspace_session` (opaque subject
ref, reported status verbatim from `reported_active` /
`reported_idle` / `reported_closed`); `workspace_view`
derives session counts per reported status and the latest
reported status at read — the stored workspace record
carries no status field. This is the form the untiered
sibling unit adjudicated for the same substance (cloud
development environments / hosted IDE workspaces, idx 797
there, closed built). The boundary is stated on every
record and stands: hosting itself is a platform-layer
property (PLATFORM-LAYER.md decision 6) and is *not* built —
`hosted_here: False`, `provisioned_here: False`,
`filesystem_held_here: False`, `executed_here: False`; no
workspace filesystem is ever held here. What is built is
the workspace/session records surface the entry's subject
matter presupposes.

### idx 703 — "Platform monitoring & logging (observability): the platform's own telemetry surface (\"monitoring, logging\" in the fork's prose fired no family — the audit patterns key on the word audit — and is recorded as near-miss, not claim)"

**Drafted: stub-engine. Landed: reference (as drafted).**

`record_telemetry_source` (kind from the telemetry
vocabulary — `metrics` / `logs` / `traces` — plus an opaque
`source_ref`) plus `record_telemetry_report` records
holding the reported summary label and the reported event
count verbatim (count validated as a non-negative integer;
bools and floats rejected). `telemetry_source_view` derives
the report count, the latest summary label, and
`total_reported_events` at read — and that total is the sum
of the *recorded* report counts, stated as such in the
module and here: a sum of reports, not a measurement.
Reports recorded without a count are tallied separately as
`reports_without_count`, never silently treated as zero.
Every record carries `reference_stub: True` and
`collected_here: False` / `monitored_here: False`: this is
the platform's own telemetry surface, not this build's
audit trail — the near-miss recorded in the entry's own
text stays a near-miss.

### idx 704 — "Platform networking: the container platform's network fabric"

**Drafted: build-extension. Landed: built (as drafted).**

Network configuration records held as data:
`define_network_route` (bound to a core environment; name,
opaque `target_ref`, optional host/path labels held as
data) and `define_network_policy` (rules held as data —
`{rule_ref, effect}` over the `allow` / `deny` vocabulary,
rule refs unique within the policy), plus
`record_route_outcome` records whose status labels are the
platform's reports, stored verbatim; `network_route_view`
derives the outcome count and latest reported status at
read — the stored definition carries no status field, and
recording an outcome leaves the definition byte-identical
(pinned). The boundary is stated on every record: the
definitions are never applied or enforced
(`applied_here: False`, `provisioned_here: False`,
`enforced_here: False`). The fabric itself — the actual
network data plane — is the platform's infrastructure and
a deployment property (PLATFORM-LAYER.md decision 6); it is
not built and not claimed. What is built is the
configuration-records surface, in the form this category
adjudicated for configuration held as data (pipeline
definitions at L2; governance-policy records at the
untiered tier).

## Re-judgments

None. The drafted split held on close reading of the
group's spec: the two stub-engine entries are the platform
itself and its telemetry surface, which ship as labeled
reference implementations; the two build-extension entries
admit the category's adjudicated records forms (workspace
declarations + sessions, per the untiered sibling;
configuration definitions held as data, per the L2 and
untiered siblings), with the platform-layer boundary stated
on the records rather than papered over.

## Fresh negative control

The latest-label derivation seam
`DevToolsExtensions._latest_label` (the latest recorded
label decides a view's current reported label;
earliest-label derivation is the mutant). In-suite
three-part form in `TestLatestLabelNegativeControl`, plus a
live file mutation drill recorded in `tests/README.md`:
patching the seam's return to read `records[0]` makes
exactly 5 tests fail — one per derivation surface (cluster,
workspace, telemetry, route views) plus the control's
canonical leg; restored, the suite is green.

## Verification (builder-side)

- Full suite: 122 tests before, **148 tests after, OK**
  (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Mutation drill: `_latest_label` in the real
  `extensions.py` patched (`records[-1]` → `records[0]`,
  occurrence count asserted = 1); full suite → exactly 5
  failures (named in `tests/README.md`); file restored from
  `scratch/extensions.py.premutation` and SHA-256-verified
  identical (`472db5c1…`); suite re-run green. Raw output:
  `scratch/gaps_mutation_run.txt`.
- Core byte-identity: all seven core modules re-hashed
  after the batch; identical to the pre-build baseline.
- Dependency check: `scratch/verify_deps.py` re-run —
  stdlib only, no third-party imports (the new module adds
  `copy` and `threading`).
- Live smokes: the founding `scratch/smoke.py` still passes
  against the untouched core (SMOKE OK); an in-process smoke
  of the extension surface drove cluster reference + outcome
  → workspace + session → telemetry source + report → route
  + outcome, with the chain verifying `(True, None)` after
  the flow and the auditor denied an extension read.
