# Tests — Operations Management L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/operations-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 119 tests
```

Status at delivery: **119 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---|---|
| `test_access.py` | 11 | Access control (RBAC) — exact 16-action permission matrix for admin/operator/viewer (admin all 16; operator all reads except `audit_read` + all writes except `workflow_write`; viewer reads except `audit_read` only), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | 10 | Append-only audit log — entry keys `{ts, actor, action, target, details}`, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording every contract mutation action name, failed ops record nothing |
| `test_directory.py` | 12 | Directory — persons (`per-`) and organizations (`org-`) creation shape/provenance/defaults, get/list, copies-are-copies, validation (empty name, bad reference/attributes), viewer write denied, failed ops consume no ids |
| `test_projects.py` | 9 | Projects — `proj-` creation with org link, add member, duplicate membership → `ValidationError`, unknown ids → `NotFoundError`, `list_project_members` returns person dicts, copies-are-copies |
| `test_assets.py` | 9 | Assets — `ast-` creation (status `in_service`), lifecycle `in_service→in_maintenance→in_service`, `→retired`, retired terminal, invalid transition → `ValidationError`, list filters by status/project |
| `test_work_orders.py` | 17 | Work orders — `wo-` creation/validation (types, priorities, `due_at` parsing, referenced ids must exist), assignment (at least one of person/project), full lifecycle + reopen + cancel paths, invalid transitions, overdue derivation (overdue open/in_progress past due → `overdue=True`; future/no/exact due → `False`; completed/closed/cancelled never overdue; `now` as string/datetime/None; derived-not-stored — stored record has no `"overdue"` key), list filters, no-id-on-failure |
| `test_inspections.py` | 9 | Inspections — `insp-` recording, all four outcomes verbatim (`pass`/`fail`/`follow_up`/`not_recorded`), at-least-one-of asset/work_order required, linked-id checks, immutability (no update/delete API on the store; returned records are copies), filters |
| `test_usage.py` | 13 | Usage records — `use-`: integer quantity accepted; float quantity → `ValidationError`; bool quantity → `ValidationError`; zero/negative integers accepted as implemented (the implementation imposes no sign/range check — pinned as implemented); unknown project → `NotFoundError`; immutability (no update/delete API); list filters; report sums quantities by metric |
| `test_workflows.py` | 8 | Workflow registry — `wf-` creation at version 1 with versions list, `work_type` = known type or `"all"`, versioned updates carrying unchanged fields forward, admin-only write (operator denied), copies-are-copies, and the registry-never-executes pin (a workflow matching a work order changes none of its states) |
| `test_reports_search.py` | 10 | Reports + search — report shape/counts exactly per UNION-SPEC (work orders by_status/by_type/by_project incl. `"unassigned"`, overdue at `now`; assets by_status; inspections by_outcome; usage by_metric SUMMED quantities), now-dependence of overdue counts, empty store; search shape `{people, organizations, projects, work_orders, assets, inspections}`, name+reference/subject/name/summary matching, literal-not-regex, empty query → `ValidationError`, search uses `project_read` permission per the builder's documented convention |
| `test_service.py` | 8 | REST API — live HTTP server (ephemeral port): health with no auth, 401 unknown user / role mismatch, 403 viewer write + `workflow_write` for operator (denied attempts audited with `:denied`), full flow (person → org → project+member → asset → work order → assign/transition → inspection → usage → workflow create/PATCH → report/search → audit), `audit_read` admin-only, 400/404 envelopes, `?now=` derivation on work-order and report endpoints |
| `test_main_cli.py` | 1 | `python -m opsmgmt serve` subprocess on an ephemeral port with demo users alice/bob/carol |
| `test_negative_control.py` | 2 | Negative control (below) |
| `test_additions.py` | 7 | Remainder additions (below) — spec integrity (22 sheets, shipped two first with 7/13 claims, 27 total), exact census-unit membership (20 fork IDs, Moderate/L2), house schema conformity, taxonomy + verbatim-evidence audit, the exact adjudicated claim map (7 claims / 6 forks / 14 zero-claim), workflow-registry Core pin exercised per workflow claimant (registry never executes; admin-only writes), integrations Extended honesty pin (no connector/execution entry point on the store). Scoped to the era's 22 sheets since the no-signal append (see the note in that module) |
| `test_nosignal.py` | 8 | No-signal addition (below) — spec integrity for the 23rd sheet (first 22 sheets deep-equal to git HEAD; membership F1603077867 Moderate/L2; house schema + exactly the two classification fields; description == `remainder/uncovered.json` record verbatim; literal zero-claim table with the group total unchanged at 27; classification fields pinned against `remainder/nosignal_report.json`, and pinned as never claim evidence) + the SMX substrate case (directory/project/work records + workflow registry hold its operations shape; registry never executes; admin-only writes; no execution entry point on the store) |
| `opsmgmt_helpers.py` | — | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building an OpsStore + AuditLog + a person + an organization + a project with the person as a member (created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
an `OpsStore` subclass (`MutantOpsStore`) overriding the single
derivation point — `_is_overdue` always returns `False`. The traced
claim, named in the module's docstrings, is that **overdue derivation
happens at read time**: an overdue open work order must read
`overdue=True` (and a report at that `now` must count it overdue).
For each canonical case (overdue work order via `get_work_order`,
and via `list_work_orders`) the test asserts three things: the
canonical expectation (derived value from the real implementation,
including, for the get case, the report count), that the mutant
would NOT produce that expectation (it reads `overdue=False`, and
its report counts zero overdue), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails.

## Mutation verification

VERIFIED by the builder (2026-10-25), live drill performed on the
real implementation (not just the subclass mutant). The body of
`OpsStore._is_overdue` (`src/opsmgmt/store.py`) — the single
derivation point for work-order overdue — was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`, so an overdue open work order never read
overdue. The full suite was run: **119 tests ran, 9 failed** —

- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_list_view_canonical_but_mutant_not`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_work_order_overdue_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_overdue_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestFullFlow.test_full_flow`
- `test_work_orders.TestOverdueDerivation.test_in_progress_past_due_overdue`
- `test_work_orders.TestOverdueDerivation.test_now_forms`
- `test_work_orders.TestOverdueDerivation.test_overdue_is_derived_not_stored`
- `test_work_orders.TestOverdueDerivation.test_overdue_open_work_order_overdue`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
recorded in `scratch/store.py.sha256` and verified identical after
restore) and the suite re-run: **119 tests, OK**. The suite catches
this defect class; the negative control is not decorative.

## Implementation notes (as implemented, pinned by tests)

- Usage quantities: UNION-SPEC requires an integer quantity (floats
  and booleans rejected). The implementation imposes no sign/range
  check, so zero and negative integers are accepted and recorded;
  `test_usage.py` pins that behaviour as implemented.
- Search permission: store `search` uses the `project_read` action
  per the builder's documented convention in `store.py`; all three
  roles hold it, and a `None` actor is denied. Pinned in
  `test_reports_search.py`.

## Additions (remainder unit `addition:operations-management-l2`, 2026-10-31)

The 20 remainder forks appended to `specs/specs.json` (see
`../ADDENDUM.md`) warranted **no core extension** — every claimed
family rides the shipped union — so `src/` is unchanged and the
suite grows only by `test_additions.py` (7 tests, in the layout
table above). Suite status for the enlarged group: **126 tests,
OK** (run exactly as above).

Negative control for the additions: with no new core function to
drill, the group's signature drill was **re-run in this tree**.
`OpsStore._is_overdue` in the real `src/opsmgmt/store.py` was
patched to `return False`; the full suite ran: **126 tests,
exactly 9 failed**, the identical failure set to the shipped
drill above (the 7 additions tests do not exercise `_is_overdue`
and pass under the mutant, as expected):

- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_list_view_canonical_but_mutant_not`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_work_order_overdue_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_overdue_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestFullFlow.test_full_flow`
- `test_work_orders.TestOverdueDerivation.test_in_progress_past_due_overdue`
- `test_work_orders.TestOverdueDerivation.test_now_forms`
- `test_work_orders.TestOverdueDerivation.test_overdue_is_derived_not_stored`
- `test_work_orders.TestOverdueDerivation.test_overdue_open_work_order_overdue`

`store.py` was restored from `scratch/store.py.premutation.additions`
and verified **SHA-256 identical to the shipped build's recorded
hash** (`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
`scratch/store.py.sha256`) — i.e. byte-identical to the code that
shipped with the original group — and the suite re-run: **126
tests, OK**. Raw drill output: `scratch/additions_mutation_run.txt`.

## No-signal addition (F1603077867, SMX Elevate IAP, 2026-10-31)

One further sheet was appended to `specs/specs.json` (see
`../ADDENDUM.md` §8): a fork the remainder census left unclassified,
resolved to this group by the live-docs research pass
(`../../remainder/nosignal_report.json`). It claims **zero
families** under the verbatim taxonomy (raw pass 3 hits: one
third-party catalogue exclusion, two scoping removals — full record
in `../scratch/NOSIGNAL_ARTIFACTS.md`), so `src/` is unchanged and
the suite grows only by `test_nosignal.py` (8 tests, in the layout
table above). One transparency note: `test_additions.py`'s
whole-file assertions are now scoped to the 22 sheets of its own
era (`specs[:22]` / `specs[2:22]`, noted in that module) — every
assertion about the additions unit keeps its exact strength, and
the new sheet is pinned by `test_nosignal.py`, including a
deep-equality check of the first 22 sheets against git HEAD.
Suite status for the group: **134 tests, OK** (run exactly as
above).

Negative control for the no-signal addition: with no new core
function to drill, the group's signature drill was **re-run in
this tree** (2026-10-31). `OpsStore._is_overdue` in the real
`src/opsmgmt/store.py` was patched to `return False`; the full
suite ran: **134 tests, exactly 9 failed**, the identical failure
set to the shipped drill and the additions re-run (the 8
no-signal tests do not exercise `_is_overdue` and pass under the
mutant, as expected):

- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_list_view_canonical_but_mutant_not`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_work_order_overdue_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_overdue_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestFullFlow.test_full_flow`
- `test_work_orders.TestOverdueDerivation.test_in_progress_past_due_overdue`
- `test_work_orders.TestOverdueDerivation.test_now_forms`
- `test_work_orders.TestOverdueDerivation.test_overdue_is_derived_not_stored`
- `test_work_orders.TestOverdueDerivation.test_overdue_open_work_order_overdue`

`store.py` was restored from `scratch/store.py.premutation.nosignal`
and verified **SHA-256 identical to the shipped build's recorded
hash** (`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
`scratch/store.py.sha256`) — i.e. byte-identical to the code that
shipped with the original group — and the suite re-run: **134
tests, OK**. Raw drill output: `scratch/nosignal_mutation_run.txt`.

## Final GAPS batch — Group 36 unit

The final GAPS batch closes this group's 13 open entries in one
new module, `src/opsmgmt/extensions.py` (class `OpsExtensions`,
wrapping the core store), tested by `test_gaps_batch.py`. The
pattern follows gaps-batch/DECISION.md: six build-extension
entries in records form (low-code application definitions and
deployment intents, mobile sync sessions and conflicts, the
security-services and policy enforcement-point records, rosters /
shifts / assignments with coverage derived at read, and IoT
device/readings records) and seven labeled reference
implementations (`reference_stub: True`) for the engine families
(workflow run references, stream and snapshot references, model
and output references, connector references, platform service
references, identity hooks with `identity_provider: False`, and
governance framework/compliance-snapshot references). No existing
core module changed — all seven pre-existing `src/opsmgmt/*.py`
files verified byte-identical by SHA-256. Per-entry record:
`../BATCH.md`.

One disclosed test-only change: `test_nosignal.py` arrived red
at this unit's baseline — its git-HEAD pin asserted HEAD held
exactly 22 spec sheets, true only before that unit's own ship
committed the 23rd. Following the era-rescope accommodation used
by earlier batch units, the pin is scoped to its own era's slice
(HEAD's first 22 sheets deep-equal the working file's first 22);
`specs/specs.json` is untouched. Suite status for the group:
**184 tests, OK**.

Negative control for the batch (fresh, on the new code): the
shift-overlap guard `_check_shift_overlap` in
`src/opsmgmt/extensions.py` — a person may not hold two ACTIVE
assignments whose windows overlap (half-open windows; adjacent
shifts allowed; withdrawn assignments free the window). The
in-test control (`TestShiftOverlapNegativeControl`) asserts the
canonical expectation, that a no-op mutant of the seam would
not produce it, and that treating the mutant's outcome as
expected fails. A live mutation drill was then run on the real
file: a copy was saved to `scratch/extensions.py.premutation`
(pre-mutation SHA-256
`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`,
`scratch/extensions.py.sha256`), the guard's overlap condition
was patched to `False` (guard disabled), and the full suite was
re-run: **184 tests ran, exactly 2 failed** — the canonical
overlap assertion and the negative-control pin — which is the
expected failure set for a disabled overlap guard (every other
test still passes against the mutant, as expected):

- `test_gaps_batch.TestScheduling.test_overlap_rejected_canonical`
- `test_gaps_batch.TestShiftOverlapNegativeControl.test_overlap_guard_canonical_but_mutant_not`

`extensions.py` was restored from `scratch/extensions.py.premutation`
and verified **SHA-256 identical** to the pre-mutation file, and
the suite re-run: **184 tests, OK**. Raw drill output:
`scratch/gaps_mutation_run.txt`.

## Final GAPS batch — Remainder Addition unit (second batch unit)

The second batch unit in this directory closes the 13 open
entries of the "Remainder Addition — Operations Management L2
(+20 forks)" GAPS.md section in one new module,
`src/opsmgmt/verticals.py` (class `OpsVerticals`, wrapping the
core store), tested by `test_gaps_batch_addition.py` (44
tests). The first unit's `src/opsmgmt/extensions.py` and
`test_gaps_batch.py` are part of the shipped tree and stay
byte-identical (SHA-256 verified: `extensions.py`
`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`,
`store.py`
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`),
as do all seven pre-existing core modules. Twelve entries
land as records surfaces for the named vendor verticals
(managed print, supply chain, PLM, ITSM, infrastructure
maintenance, facilities/IWMS, case management incl. EEO +
FOIA, process modeling/mining records, mail & package,
portfolio/agile planning, back-office ERP records, contract
progress), each with lifecycles held as recorded/reported
states and counts/totals derived at read; nothing prints,
moves, auto-resolves, tracks live, posts, releases, or mines.
One entry (enterprise asset management depth / Maximo) ships
as a labeled reference implementation (`reference_stub:
True`; reported labels and counts only, nothing predicted or
computed). Per-entry record: `../BATCH-ADDITION.md`. Suite
status for the group: **228 tests, OK**.

Negative control for this unit (fresh, on the new code): the
case decider-not-opener guard `_check_decider_not_opener` in
`src/opsmgmt/verticals.py` — the actor who records a decision
on a case may never be the actor who opened it. The in-test
control (`TestDeciderNotOpenerNegativeControl`) asserts the
canonical expectation, that a no-op mutant of the seam would
not produce it, and that treating the mutant's outcome as
expected fails. A live mutation drill was then run on the
real file: a copy was saved to
`scratch/verticals.py.premutation` (pre-mutation SHA-256
`8fb9943f0680f74abfad35d9e9ca9483cdaee14f598dfd5e550fe1be1be8131b`,
`scratch/verticals.py.sha256`), the guard's condition was
patched to `False` (guard disabled), and the full suite was
re-run: **228 tests ran, exactly 2 failed** — the canonical
opener-may-not-decide assertion and the negative-control
pin — which is the expected failure set for a disabled
decider guard (every other test still passes against the
mutant, as expected):

- `test_gaps_batch_addition.TestCaseManagement.test_opener_may_not_decide_canonical`
- `test_gaps_batch_addition.TestDeciderNotOpenerNegativeControl.test_decider_guard_canonical_but_mutant_not`

`verticals.py` was restored from
`scratch/verticals.py.premutation` and verified **SHA-256
identical** to the pre-mutation file, and the suite re-run:
**228 tests, OK**. Raw drill output:
`scratch/gaps_addition_mutation_run.txt`.

## Final GAPS batch — No-Signal Addition unit (third batch unit)

The third batch unit in this directory closes the 2 open
entries of the "No-Signal Addition — Operations Management L2
(SMX Elevate IAP, F1603077867)" GAPS.md section in one new
module, `src/opsmgmt/extensions_nosignal.py` (class
`OpsNoSignal`, wrapping the core store, audit prefix `extn_`),
tested by `test_gaps_batch_nosignal.py` (21 tests). All
pre-existing modules stay byte-identical (SHA-256 verified
against `scratch/prebatch-nosignal-src.sha256`), including the
first batch unit's `extensions.py`
(`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`)
and the second batch unit's `verticals.py`
(`8fb9943f0680f74abfad35d9e9ca9483cdaee14f598dfd5e550fe1be1be8131b`),
and `store.py`
(`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`).
The cloud platform operations entry ships as a labeled
reference implementation (`reference_stub: True`; platform
references plus lifecycle operation references with outcomes
and counts exactly as reported; automation modes held as
data, never executed; nothing provisioned, operated,
monitored, secured, or lifecycle-managed here). The
compliance automation & policy guardrails entry lands as
records: baseline packs keyed to the baselines the fork names
in its own words (CMMC, HIPAA, HITECH, CJIS, PCI, SOC 1/2,
FedRAMP, DoD IL) with control references as data, guardrail
definitions with rule text verbatim and never evaluated,
scoped to multi-tenant / cross-domain operations, and
guardrail check records with outcomes exactly as reported —
`automated_here` / `evaluated_here` / `enforced_here: False`
throughout; the guardrail view's check count, counts by
outcome, and latest outcome are derived at read and never
stored. Per-entry record: `../BATCH-NOSIGNAL.md`. Suite
status for the group: **249 tests, OK**.

Negative control for this unit (fresh, on the new code): the
checker-not-definer guard `_check_checker_not_definer` in
`src/opsmgmt/extensions_nosignal.py` — the actor who records
a guardrail check may never be the actor who defined the
guardrail. The in-test control
(`TestCheckerNotDefinerNegativeControl`) asserts the
canonical expectation, that a no-op mutant of the seam would
not produce it, and that treating the mutant's outcome as
expected fails. A live mutation drill was then run on the
real file: a copy was saved to
`scratch/extensions_nosignal.py.premutation` (pre-mutation
SHA-256
`709f2c1d768ea185b6537e03d893601257bb29eb9742f844688392c80d6ac155`,
`scratch/extensions_nosignal.py.sha256`), the guard's
condition was patched to `False` (guard disabled), and the
full suite was re-run: **249 tests ran, exactly 2 failed** —
the canonical definer-may-not-check assertion and the
negative-control pin — which is the expected failure set for
a disabled checker guard (every other test still passes
against the mutant, as expected):

- `test_gaps_batch_nosignal.TestGuardrails.test_definer_may_not_check_canonical`
- `test_gaps_batch_nosignal.TestCheckerNotDefinerNegativeControl.test_checker_guard_canonical_but_mutant_not`

`extensions_nosignal.py` was restored from
`scratch/extensions_nosignal.py.premutation` and verified
**SHA-256 identical** to the pre-mutation file, and the suite
re-run: **249 tests, OK**. Raw drill output:
`scratch/gaps_nosignal_mutation_run.txt`.
