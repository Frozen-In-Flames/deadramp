# Tests — Operations Management L1 singleton build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to. The suite is the shipped
Group 36 (Operations Management L2) suite inherited for this
singleton: 13 of 15 files byte-identical, 2 differing by docstring
wording only (group references; zero logic changes — see
`../scratch/reuse-note.md`).

## Run

```bash
cd groups/operations-management-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 175 tests
```

Status at delivery: **119 tests, OK** against the implementation in
`../src/`; **129 tests, OK** after the remainder additions below;
**175 tests, OK** after the final GAPS batch unit below. (Run exactly as above: helpers are imported as a top-level
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
| `test_additions.py` | 10 | Remainder additions (unit `addition:operations-management-l1`) — spec integrity (4 sheets, original first and unchanged, exact census membership, house schema, taxonomy labels, verbatim evidence, literal claim map: 1 claim / Tango `integrations`; SCMC and FM:Systems zero-claim), census citations 4/4 verbatim but tagging nothing, near-miss pins, and one substrate case per addition fork (SCMC procurement records + report overdue derivation; FM:Systems reservable-room asset + never-executing workflow, no reservation/scheduling API on the store; Tango workplace records, integrations Extended-only — no connector entry point) |
| `test_gaps_batch.py` | 46 | Final GAPS batch (unit `Singleton 52 — Operations Management L1`) — the extension surface in `src/opsmgmt/extensions.py`: form definitions as data (`rendered_here: False`, versioned, field validation), submission records (values only for defined fields, labels not content, opaque submitter refs), reviewer assignments (duplicate-active refused, withdraw frees, current reviewers derived at read and never stored), reviews (score/feedback stored verbatim, `score_computed_here: False`, immutable — no update/delete API, summary counts only with no aggregate key), message templates + dispatch requests/outcomes (`sent_here: False`, reported statuses verbatim), report definitions + runs (run records store no figures; figures derived at read; project scope honored; unknown metrics refused), site definitions (`published_here`/`rendered_here: False`), galleries (opaque media refs only, no content field, `hosted_here: False`, item count derived), sessions (window validation, room/speaker conflicts derived at read, half-open adjacency, no conflict key stored), payments (integer cents only — float/bool/zero refused, `paid_here: False`, current reported status derived from latest outcome), integration references (`reference_stub: True`, event references also `reference_transport: True`, `connected_here`/`synced_here: False`), cross-cutting RBAC/audit pins (viewer and operator denials audited as `ext_*:denied`, no-id-on-failure, copies-are-copies), and the batch's fresh negative control (below) |
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

VERIFIED in this tree (2026-10-31), live drill performed on the
real implementation (not just the subclass mutant). The body of
`OpsStore._is_overdue` (`src/opsmgmt/store.py`) — the single
derivation point for work-order overdue — was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`, so an overdue open work order never read
overdue. The full suite was run: **119 tests ran, 9 failed** (full
output in `scratch/mutation-run.txt`) —

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

## Additions drill re-run (remainder unit, 2026-10-31)

The core did not change for the remainder additions (ADDENDUM.md
§3), so the same live drill was re-run in this tree after
`test_additions.py` landed: the final return of
`OpsStore._is_overdue` was patched to `return False` and the full
suite ran — **129 tests, exactly 11 failures**: the original
drill's 9 above, plus 2 from the additions module, tripping
exactly as designed —

- `test_additions.TestAdditionSubstrateCases.test_scmc_procurement_records_ride_the_substrate`
- `test_additions.TestAdditionSubstrateCases.test_tango_integrations_claim_is_extended_only`

`store.py` was restored from the additions pre-mutation copy
(`scratch/additions_store.py.premutation`) and verified
SHA-256-identical to the shipped hash above; the suite re-ran:
**129 tests, OK**. Full record in
`scratch/additions_mutation_run.txt`.

## Implementation notes (as implemented, pinned by tests)

- Usage quantities: UNION-SPEC requires an integer quantity (floats
  and booleans rejected). The implementation imposes no sign/range
  check, so zero and negative integers are accepted and recorded;
  `test_usage.py` pins that behaviour as implemented.
- Search permission: store `search` uses the `project_read` action
  per the builder's documented convention in `store.py`; all three
  roles hold it, and a `None` actor is denied. Pinned in
  `test_reports_search.py`.

## Final GAPS batch negative control (2026-11-07)

`test_gaps_batch.py` adds the batch's fresh negative control for
the NEW extension code: `TestSessionOverlapNegativeControl`
implements the three-leg house form against the single
derivation point for session conflicts — `_windows_overlap` in
`src/opsmgmt/extensions.py` (half-open window overlap). The
traced claim is that **session conflicts derive at read time**
from the recorded session windows: two sessions sharing a room
label whose windows overlap must read as exactly one room
conflict in `session_conflicts`. The test asserts the canonical
expectation from the real implementation, that a mutant seam
(patched in-process to always report no overlap) would NOT
produce it (the conflict vanishes), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails.

## GAPS batch mutation verification

VERIFIED in this tree (2026-11-07), live drill performed on the
real extension file (not just the in-process mutant). The body
of `_windows_overlap` (`src/opsmgmt/extensions.py`) was patched
to `return False`, so no two recorded sessions could ever derive
a conflict. The full suite was run: **175 tests ran, exactly
3 failed** (full output in `scratch/gaps_batch_mutation_run.txt`) —

- `test_gaps_batch.TestSessions.test_room_conflict_derived_at_read`
- `test_gaps_batch.TestSessions.test_speaker_conflict_derived`
- `test_gaps_batch.TestSessionOverlapNegativeControl.test_overlap_derivation_canonical_but_mutant_not`

No core test failed. `extensions.py` was then restored from the
pre-mutation copy (`scratch/extensions.py.premutation`; SHA-256
`2d77ed776ea5795001eecec64b82648390b28b34b3a0ae0c005400dda9dbbaed`,
recorded in `scratch/extensions.py.sha256` and verified
identical after restore) and the suite re-run: **175 tests,
OK**. All seven pre-existing core modules were verified
byte-identical to their pre-unit hashes after the unit landed
(`store.py` still
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`).
