# Tests — Learning Management L2 singleton build

Stdlib `unittest` only. Every test docstring names the core
function / claim family / control family it traces to.

## Run

```bash
cd groups/learning-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 118 tests
```

Status at delivery: **104 tests, OK** against the implementation
in `../src/`. After the remainder addition (unit
`addition:learning-management-l2`): **118 tests, OK** (see the
additions row in the layout table and the drill re-run record at
the end of this file). After the no-signal addition
(F1207261443, Skillsoft / Private Cloud): **133 tests, OK** (see
the no-signal row in the layout table and the second drill
re-run record at the end of this file). (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 8 | Core 13 RBAC — exact permission matrix for admin/instructor/learner/auditor, `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | 5 | Core 14 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording mutation actions, failed ops record nothing |
| `test_learners.py` | 6 | Core 1 learner registry — `lrn-` shape/provenance, duplicate ref rejected with no id consumed, validation, learner_write admin-only |
| `test_catalog.py` | 11 | Core 2 catalog — course/program kinds, all nine content standards accepted + bad standard rejected, lesson-plan reference resolution (unknown ref → NotFoundError), catalog_write admin-only |
| `test_registrations.py` | 13 | Core 3 events & registrations — capacity → waitlist derivation, derived seat view vs. stored record, promotion into a full event rejected, duplicate active registration rejected with no id consumed, re-register after cancellation, learner scope |
| `test_authorizations.py` | 7 | Core 4 SF-182 authorization records — requested → approved/declined flow, **decider ≠ creator** (PermissionDenied), double-decide rejected, validation, learner scope |
| `test_plans.py` | 5 | Core 5 IDP records — shape, activities deep-copied (caller mutation does not reach the store), activity/target-date validation, learner scope |
| `test_competencies.py` | 5 | Core 6 competency records — definitions, learner levels recorded **verbatim**, unknown learner/competency, learner scope |
| `test_progress.py` | 4 | Core 7 progress records — shape, status/readiness/percent validation (bool percent rejected), unknown learner/course, learner scope |
| `test_statements.py` | 5 | Core 8 LRS statement records — **exact eight-key shape**, `result_text` stored verbatim (a "score: 88/100" string stays a string), recursive **no-score-field pin** across statement/progress/learner-competency/report shapes |
| `test_compliance.py` | 8 | Core 9 compliance — stored record carries **no status field**, current/overdue/completed derivation against explicit `as_of`, on-due-date is current, completion overrides overdue, in_progress does not complete, derivation deterministic in `as_of`, compliance_write admin-only, learner scope |
| `test_workflows_notifications.py` | 6 | Core 10 registries — workflow definitions validated, **never-executes pin** (registering a workflow changes no registration/authorization/notification state), notification records + recipient filter |
| `test_reporting.py` | 7 | Core 11 search & reporting — empty-store shape, populated counts, compliance counts use derived status at `as_of`, substring search, learner denied `report_read` (search and report) |
| `test_service.py` | 10 | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (learner → course → content → lesson plan → event → register → authorization decided by a different actor → IDP → competency → progress → statement → compliance derived overdue → completed → report → search), learner write 403 + denied audited, learner scope over HTTP, audit admin+auditor only, 400/404 envelopes |
| `test_main_cli.py` | 1 | `python -m lms serve` subprocess with demo users alice/bob/carol/dana |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_additions.py` | 14 | Remainder addition (unit `addition:learning-management-l2`) — spec integrity for the appended Percipio sheet (count/order/membership, the original claim table standing at 26, the literal **zero-claim** table and whole-taxonomy zero-claim set, tier fields, verbatim description, census citation accounting, exclusion-segment pin, named-absence rechecks, near-miss pins) + 2 substrate cases (progress record with compliance status derived at read; catalogue content records with an exact-eight-key statement and recursive no-score scan). Three whole-file pins (count/order, membership, zero-claim list) are scoped to this unit's own slice (the first 2 sheets) since the no-signal sheet now follows — disclosed in their docstrings |
| `test_nosignal_addition.py` | 15 | No-signal addition (F1207261443, Skillsoft / Private Cloud) — spec integrity for the appended sheet (count/order, both shipped sheets deep-equal to git HEAD, membership against the census `no-signal-set` with its `no_signal` flag / empty citations / classifier note pinned, the literal **zero-claim** table and whole-taxonomy zero-claim set, unchanged group total of 26 with 2 of 3 forks at zero, tier fields, description verbatim against both cached sources, classification fields pinned against `../../remainder/nosignal_report.json` with the classification sentence asserted absent from the cached description, the **platform-documentation caveat** pinned on the report's notes and on ADDENDUM §7's text, named-absence rechecks, near-miss pins) + 2 substrate cases (hosted catalogue content with progress record and compliance status derived at read; an exact-eight-key statement over a hosted content item with recursive no-score scan) |
| `test_gaps_batch.py` | 33 | Final GAPS batch (Singleton 48) — extension surface in `../src/lms/extensions.py`: one class per open GAPS entry (delivery sessions with derived status, package/distribution records + record conformance, xAPI record conformance + labeled forwards, analytics/outcomes count derivations, career-path gap derivation, succession coverage, candidate review with separation of duties, survey records with verbatim tallies, KB articles, CMS pages, report definitions + derived runs, notification rules + labeled receipts, EHRI / authoring / SF-182-form / workflow-execution reference stubs) + cross-cutting no-score recursive key scan, learner scope, `ext_` audit actions |
| `lms_helpers.py` | — | Shared fixtures: demo users (ADMIN/INSTRUCTOR/LEARNER/AUDITOR), `USERS` registry, `fresh_store()`, and `make_store()` building an LmsStore + AuditLog + one learner (ref `carol`) + one course |

## Negative control

`test_negative_control.py` implements the contract's negative
control: an `LmsStore` subclass (`MutantLmsStore`) whose
`_derive_status` always returns `"current"` — the compliance
status derivation is skipped. The traced claim, named in the
module's docstrings, is that **compliance status is derived
deterministically from assignment, due date, and progress
records**: a past-due incomplete assignment must read `overdue`,
and an assignment with a completed progress record must read
`completed`. For each canonical case (past-due incomplete,
completed) the test asserts three things: the canonical
expectation (from the real implementation), that the mutant would
NOT produce that expectation (it says `current` anyway), and —
via a literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails. A third test
asserts the companion RBAC gate: a learner creating a compliance
assignment is denied and nothing is stored.

## Mutation verification

VERIFIED by the coordinator for this group (2026-10-31). The
overdue branch in `LmsStore._derive_status` (`src/lms/store.py`) —
the line `return "overdue"` under `if as_of_date > due:` — was
patched to `return "current"`, the exact live counterpart of the
mutant in `test_negative_control.py`, so a past-due incomplete
assignment read `current` instead of `overdue`. The full suite
was run: **104 tests ran, 9 failed** (raw output in
`scratch/mutation-run.txt`) —

- `test_compliance.TestCompliance.test_completed_progress_overrides_overdue`
- `test_compliance.TestCompliance.test_derivation_deterministic_in_as_of`
- `test_compliance.TestCompliance.test_in_progress_does_not_complete`
- `test_compliance.TestCompliance.test_list_compliance_derives_each`
- `test_compliance.TestCompliance.test_overdue_when_past_due_and_incomplete`
- `test_compliance.TestCompliance.test_validation_and_permissions`
- `test_negative_control.TestNegativeControlMutantCompliance.test_past_due_incomplete_is_overdue_canonical_but_mutant_current`
- `test_reporting.TestReporting.test_report_compliance_uses_derived_status`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from the pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`820d97121fd55799b77b417b23d72d26680e22596141ee58e52cfa32bb3bba8a`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`) and the suite re-run: **104 tests,
OK**. The suite catches this defect class; the negative control
is not decorative.

## Remainder addition — drill re-run (unit `addition:learning-management-l2`)

The addition changes no core code (`src/` byte-identical, all 7
`lms` module hashes verified against the pre-work baseline in
`../scratch/additions_src_hashes_before.txt`), so the group's
signature drill was re-run in this tree against the enlarged
suite (118 tests). Raw output in
`../scratch/additions_mutation_run.txt`.

**Drill re-run — compliance derivation.** The overdue branch of
`LmsStore._derive_status` in `src/lms/store.py` (`return
"overdue"` under `if as_of_date > due:`) was patched to `return
"current"` — the same scoped patch as the original drill (the
branch text occurs exactly once in the file, count asserted
before patching). The full suite ran: **118 tests, exactly 10
failures** — the shipped drill's identical 9 plus exactly 1 from
the additions module,
`test_additions.TestAdditionSubstrateCases.test_percipio_progress_and_compliance_derivation`,
tripping on the mutant exactly as designed. `store.py` was
restored from `../scratch/store.py.premutation-additions` and
verified SHA-256-identical to the shipped hash (`820d9712…`);
the suite re-ran green: **118 tests, OK**.

## No-signal addition — drill re-run (F1207261443, Skillsoft / Private Cloud)

The addition changes no core code (`src/` byte-identical, all 7
`lms` module hashes verified against the pre-work baseline in
`../scratch/nosignal_src_hashes_before.txt`), so the group's
signature drill was re-run in this tree against the enlarged
suite (133 tests). Raw output in
`../scratch/nosignal_mutation_run.txt`.

**Drill re-run — compliance derivation.** The overdue branch of
`LmsStore._derive_status` in `src/lms/store.py` (`return
"overdue"` under `if as_of_date > due:`) was patched to `return
"current"` — the same scoped patch as the original drill (the
branch text occurs exactly once in the file, count asserted
before patching). The full suite ran: **133 tests, exactly 11
failures** — the shipped drill's identical 9, the additions
re-run's +1
(`test_additions.TestAdditionSubstrateCases.test_percipio_progress_and_compliance_derivation`),
and exactly 1 from the no-signal module,
`test_nosignal_addition.TestNoSignalSubstrateCases.test_private_cloud_progress_and_compliance_derivation`,
tripping on the mutant exactly as designed. `store.py` was
restored from `../scratch/store.py.premutation-nosignal` and
verified SHA-256-identical to the shipped hash (`820d9712…`);
the suite re-ran green: **133 tests, OK**.

## Final GAPS batch (2026-11-07)

`test_gaps_batch.py` (33 tests) pins the extension surface in
`../src/lms/extensions.py` (`LmsExtensions`): one class per open
GAPS.md entry for this group (see `../BATCH.md` for the per-entry
disposition — 12 built, 4 reference), plus cross-cutting pins: a
recursive **no-score key scan** over 20 extension surfaces (the
founding invariant binding the extension exactly as it binds the
core), derived-never-stored delivery status, stub labels
(`reference_stub: True` on EHRI feed records, authoring drafts,
SF-182 form workflow records, and workflow execution records) and
the transport label (`reference_transport: True` on statement
forward records and notification receipts), the
workflow-execution stub's changes-nothing pin, learner scope, and
`ext_`-prefixed audit actions.

### Batch mutation verification

VERIFIED by the coordinator for this batch unit (2026-11-07). The
completed branch of the delivery-status derivation
(`_derive_delivery_status` in `src/lms/extensions.py`) — the line
`return "completed"` under the completed-progress check — was
patched to `return "in_progress"`, so a learner with a completed
core progress record read `in_progress` instead of `completed`.
The full suite was run: **166 tests ran, exactly 1 failure**
(`test_gaps_batch.TestDeliveryEngine.test_status_derived_from_core_progress`).
`extensions.py` was then restored from the pre-mutation copy and
verified SHA-256-identical to the pre-mutation hash
(`833ca1c9f294c963eaabadf69fff8770beb346b887b9662409e0444051281cc6`),
and the suite re-run: **166 tests, OK**.

Full suite status after the batch: **166 tests, OK** (133 at
delivery + 33 batch tests). Core modules byte-identical to their
pre-batch hashes (`store.py` still `820d9712…`).

One disclosure: the shipped suite arrived at this unit with 1
pre-existing failure — `test_nosignal_addition`'s git-HEAD sheet
pin asserted HEAD held 2 spec sheets, true only before that
unit's own ship landed (HEAD now holds 3). The pin was rescoped
to its own era slice (the first 2 HEAD sheets) with the rescope
disclosed in the test's docstring; the pin's strength is
unchanged. Before the batch: 133 tests, 1 failure (that pin).
After: 166 tests, OK.

## Final GAPS batch — second unit (2026-11-08)

`test_gaps_batch_addition.py` (19 tests) pins the second
extension surface in `../src/lms/extensions_addition.py`
(`LmsExtensionsAddition`): the one open entry of the GAPS.md
section "Remainder Addition — Learning Management L2 (+1 fork)"
(idx 678; see `../BATCH-ADDITION.md` — closed as drafted,
stub-engine, as a labeled reference implementation). Pins:
library item shape with the stub/transport labels and the
not-here flags, the fork's own format vocabulary, assessment
content as catalogue content (never administration), core
bindings by id only with the mismatch rule, core records
byte-identical across a full addition flow, access reports held
verbatim with reported counts validated (bool/float/negative
rejected, no id consumed), lab environments bound to
practice-lab items only, derived `latest_outcome_label` and
counts in the item view and the summary, a recursive
no-score/no-content key scan over the whole surface, a
no-`**kwargs` signature scan with TypeError pins on smuggled
`content=` / `password=` calls, no float values anywhere, RBAC
denials consuming no id, and `exta_`-prefixed audit actions.

### Addition mutation verification

VERIFIED by the coordinator for this batch unit (2026-11-08).
The latest-outcome seam (`_latest_outcome_label` in
`src/lms/extensions_addition.py`) — the line
`return reports[-1]["outcome_label"] if reports else None`
(occurrence count asserted = 1 before patching) — was patched
to read the FIRST recorded report (`reports[0]`), so views and
the summary read the earliest reported outcome instead of the
latest. The full suite was run: **185 tests ran, exactly 4
failures** (raw output in
`../scratch/gaps_batch_addition_mutation_run.txt`) —

- `test_gaps_batch_addition.TestAccessReports.test_view_derives_count_and_latest_outcome`
- `test_gaps_batch_addition.TestLibrarySummary.test_summary_counts_and_latest`
- `test_gaps_batch_addition.TestNegativeControlLatestOutcome.test_canonical_view_uses_latest_outcome`
- `test_gaps_batch_addition.TestNegativeControlLatestOutcome.test_seam_directly`

`extensions_addition.py` was then restored from the
pre-mutation copy (`../scratch/extensions_addition.py.premutation`;
SHA-256 `daaa1554e0bfb00a32ccf70198114e3c8498311b39ff0463c64c8f164bb44e2a`,
verified identical) and the suite re-run: **185 tests, OK**.

Full suite status after the second batch unit: **185 tests,
OK** (166 before + 19 addition tests). All pre-existing modules
byte-identical to their pre-build hashes (`store.py` still
`820d9712…`, first unit's `extensions.py` still `833ca1c9…`).

## Final GAPS batch — third unit (2026-11-08)

`test_gaps_batch_nosignal.py` (16 tests) pins the third
extension surface in `../src/lms/extensions_nosignal.py`
(`LmsExtensionsNoSignal`): the one open entry of the GAPS.md
section "No-Signal Addition — Learning Management L2
(Skillsoft Private Cloud, F1207261443)" (idx 971; see
`../BATCH-NOSIGNAL.md` — closed as drafted, stub-engine, as a
labeled reference implementation). Pins: deployment shape with
the stub/transport labels and the not-here flags, the
offering's deployment-kind vocabulary, core binding by id only,
core records byte-identical across a full no-signal flow,
delivery reports held verbatim with reported counts validated
(bool/float/negative rejected, no id consumed), derived
`latest_outcome_label` and counts in the deployment view and
the summary, a recursive no-score/no-content key scan over the
whole surface, a no-`**kwargs` signature scan with TypeError
pins on smuggled `content=` / `password=` calls, no float
values anywhere, no provision/execute-shaped method, RBAC
denials consuming no id, and `extn_`-prefixed audit actions.

### No-signal mutation verification

VERIFIED by the coordinator for this batch unit (2026-11-08).
The latest-outcome seam (`_latest_outcome_label` in
`src/lms/extensions_nosignal.py`) — the line
`return reports[-1]["outcome_label"] if reports else None`
(occurrence count asserted = 1 before patching) — was patched
to read the FIRST recorded report (`reports[0]`), so views and
the summary read the earliest reported outcome instead of the
latest. The full suite was run: **201 tests ran, exactly 4
failures** (raw output in
`../scratch/gaps_batch_nosignal_mutation_run.txt`) —

- `test_gaps_batch_nosignal.TestDeliveryReports.test_view_derives_count_and_latest_outcome`
- `test_gaps_batch_nosignal.TestHostingSummary.test_summary_counts_and_latest`
- `test_gaps_batch_nosignal.TestNegativeControlLatestOutcome.test_canonical_view_uses_latest_outcome`
- `test_gaps_batch_nosignal.TestNegativeControlLatestOutcome.test_seam_directly`

`extensions_nosignal.py` was then restored from the
pre-mutation copy (`../scratch/extensions_nosignal.py.premutation`;
SHA-256 `8c2ac492e18df5f953fa3d78e180047deb8c439c833b07004994755ae4c59adf`,
verified identical) and the suite re-run: **201 tests, OK**.

Full suite status after the third batch unit: **201 tests,
OK** (185 before + 16 no-signal tests). All pre-existing modules
byte-identical to their pre-build hashes (`store.py` still
`820d9712…`, first unit's `extensions.py` still `833ca1c9…`,
second unit's `extensions_addition.py` still `daaa1554…`).
