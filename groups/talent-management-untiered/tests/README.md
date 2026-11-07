# Tests — Talent Management untiered set (tier null)

Stdlib `unittest` only. Every test module's header names the core
function / spec claim it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/talent-management-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 102 tests
PYTHONPATH=src python3 tests/smoke.py                       # prints SMOKE OK
```

Status at delivery: **102 tests, OK** — the founding Talent
Management L2 group's 92-test core suite carried with the code
(its `test_specs.py` is NOT carried: it pins the founding census
unit), plus 10 new spec tests in `test_specs.py` pinning this
set. Carried test modules are byte-identical to the founding
suite except `talentmgmt_helpers.py` (one labeling fix: its
docstring names this untiered set instead of L2).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | RBAC matrix (Core 13): the three roles' action sets exactly; unknown role fail-closed; no write for viewer |
| `test_organizations_candidates.py` | 13 | Cores 1–2: organization/member records, opaque candidate registration, ref uniqueness, membership scoping |
| `test_requisitions_pipelines.py` | 12 | Cores 3–4: requisition lifecycle with derived `past_close`, pipeline records with ordered stage lists, membership scoping |
| `test_placements.py` | 11 | Core 5: placements, the stage bounds rule (out-of-bounds / negative / bool / float / string rejected whole), derived current stage, one active placement per candidate per pipeline, withdrawal |
| `test_events.py` | 9 | Cores 6–7: event records (in-person / virtual kinds), registrations, check-in transitions, event lifecycle |
| `test_assessments_interviews.py` | 9 | Cores 8–9: assessment records with verbatim outcome labels (no score field exists), interview scheduling/completion/cancellation |
| `test_records.py` | 3 | Core 10: workflow definition registry — shape, ref uniqueness, and a pin that the store exposes no execute-like operation |
| `test_reports_search.py` | 7 | Cores 11–12: report key set (exactly 18 keys), counts, active-only stage distribution, no-score key scan; case-insensitive membership-scoped search |
| `test_privacy.py` | 5 | Privacy discipline: exact key sets for all eleven stored shapes, derived-view key deltas, recursive banned-key scan, smuggled kwargs raise `TypeError` |
| `test_audit.py` | 6 | Core 13 (audit substrate): entry shape, all twenty mutation action names in canonical order, failed operations and store reads record nothing, JSONL persistence/reload, no mutation API |
| `test_service.py` | 6 | HTTP contract: `/health`, 401s audited as `:denied`, 403s, 404, full flow with stage bounds over HTTP, admin-only `/audit` whose read is itself audited |
| `test_main_cli.py` | 1 | `python -m talentmgmt serve` answers `/health` |
| `test_negative_control.py` | 3 | The stage bounds rule is load-bearing (below) |
| `test_specs.py` | 10 | This set's spec pins — exactly 2 sheets in census order; membership exact against census unit `untiered:Talent Management` in `remainder.json`; the unit's tier is null and every sheet's tier null / impact "Unknown"; descriptions byte-equal to the cache `service_desc` and to `remainder/uncovered.json`, no carriage returns; registry fields vs `forks.json` and source business categories recorded as-is; the literal claim table (0 claims total, both forks zero-claim); census citations 4/4 verbatim; substance tokens present but untagged (verb discipline); `certified_services` never matched (14 entries, incl. SSO/SCIM and scores, while "score" occurs in neither description) |
| `smoke.py` | — | Live driver (not a unittest): real server, real requests; prints `SMOKE OK` |
| `talentmgmt_helpers.py` | — | Shared fixtures carried from the founding suite (docstring labeling fix only): demo users, fresh stores, canonical builders |

## Negative control

`test_negative_control.py` proves the group's signature invariant
— the stage bounds rule (Core 5): a movement's `stage_index` must
satisfy `0 <= stage_index < len(stages)`, enforced by
`TalentMgmtStore._check_stage_bounds` before anything is stored —
is load-bearing, not decorative. The canonical store rejects an
out-of-bounds movement whole (nothing recorded, derived stage
unchanged), and rejects negative and boolean indices. The
`MutantTalentMgmtStore` subclass, whose seam is a no-op, accepts
the out-of-bounds movement; its placement's derived view then
raises `IndexError`, because the stored index names no stage. A
negative index is worse: the mutant's derived view silently
resolves it to the pipeline's **last** stage (Python negative
indexing), so the placement appears to sit at "Decision" without
passing a single stage gate. Each test asserts the canonical
expectation, the mutant's divergence, and a literal
`assertRaises(AssertionError)` showing that treating the mutant's
outcome as the expectation fails.

## Mutation verification — re-run in this tree

VERIFIED for this untiered build: the body of
`_check_stage_bounds` in the real `src/talentmgmt/store.py` was
replaced with `return None`, the full suite was run against the
patched implementation, and the file was restored from
`scratch/store.py.premutation` and verified byte-identical by
SHA-256.

Result under mutation: **102 tests run, exactly 5 failures** —
the founding group's original drill set, unchanged:

- `test_negative_control.TestNegativeControlStageBounds.test_canonical_expectation_rejects_out_of_bounds_movement`
- `test_negative_control.TestNegativeControlStageBounds.test_mutant_also_breaks_negative_and_boolean_indices`
- `test_placements.TestPlacements.test_non_integer_indices_rejected`
- `test_placements.TestPlacements.test_out_of_bounds_indices_rejected_whole`
- `test_service.TestService.test_full_flow_and_bounds_over_http` (the mutant returned 201 for `stage_index` 99)

No spec test failed under the mutant: `test_specs.py` pins the
spec sheets, not the bounds seam. Raw drill output is in
`scratch/mutation_run.txt`.

After restore: `store.py` SHA-256
`ff0cab40ba3b90c226a9cf993780dc26bc3dec8556d072c3bc664f5c832b08af`
(matches `scratch/store.py.sha256`; the module differs from the
founding group's shipped store by its docstring only, re-anchored
to tier null), and the suite is green again (102 tests, OK).

## Live smoke

`tests/smoke.py` starts the real server on an ephemeral port and
drives it over HTTP: health; organization + members; candidate;
requisition; pipeline; placement; an in-bounds movement (201,
derived stage "Interview"); an out-of-bounds movement (400);
event + registration + check-in; an assessment completed with a
verbatim outcome label; a video interview; and a report asserting
`placements_by_stage == {"Interview": 1}` and
`checked_in_count == 1`. It prints `SMOKE OK`. Verified in this
tree at delivery.

## Interpretation notes

- Assessments store a caller-supplied **outcome label verbatim**
  and nothing else: there is no score field anywhere in the
  package, pinned by the privacy scan and the report scan.
  Scoring, ranking, and matching are engines (gaps in
  UNION-SPEC.md), not records. This is the founding category's
  doctrine, preserved exactly at tier null.
- The report's `placements_by_stage` counts **active** placements
  only; a withdrawn placement's movements remain in the substrate
  but contribute nothing to the distribution.
- The audit flow test pins 23 entries covering all twenty
  distinct mutation action names in order; denials at the HTTP
  layer are recorded by the service with a `:denied` suffix, and
  store-level failures record nothing, so nothing is double-counted.
- Tier discipline is pinned in `test_specs.py`, not in the core
  suite: the carried core contains no tier or baseline machinery
  beyond the re-anchored docstrings, so there is nothing
  tier-shaped for the core tests to pin.
- Byte identity: `src/talentmgmt/` is 5 of 7 modules
  byte-identical to `../talent-management-l2/src/talentmgmt/`;
  `__init__.py` and `store.py` differ by docstring only (full
  SHA-256 table in `../README.md`).

## Final GAPS batch module

| File | Covers |
|---|---|
| `test_gaps_batch.py` | The batch extension surface (`src/talentmgmt/extensions.py`, 39 tests): one class per closed entry — proctoring session reference records bound to core assessments with verbatim reported outcomes (`reference_stub: True`, nothing adjudicated, no identity document or session media held), learning program definitions + enrollments + module-completion check-offs with progress derived at read and never stored, tutor session metadata records, integration endpoint definitions + exchange receipts (`reference_stub` / `reference_transport: True`, no credentials held, no data moved), exchange postings + reported match records (`matched_here` False, no score anywhere) with a counts-only derived summary, workforce cases + label-only activity records with activity counts derived at read, employer registrations + service requests with guarded lifecycles and a derived summary, UI claim reference records whose current reported status derives at read from the newest append-only report (`determined_here` / `benefits_paid_here` False) + UI exchange receipts, and LMI observations stored as reported with a deterministic grouped summary derived at read (counts and sums of reported values; no average, rate, or index) + publication definitions and distribution receipts. Cross-cutting: exact key sets for all nineteen extension record kinds; a recursive scan over every extension record and derived view (no tier/baseline/equivalence-shaped key, no float value; no numeric list in any stored record); no banned identity- or score-shaped key anywhere; PII- and content-shaped keyword arguments raise `TypeError`; extension signatures carry no substance-shaped parameter; denied attempts audited `ext_<action>:denied`; the core membership boundary binds extension reads and writes; failed operations consume no id |

## Batch negative control — mutation-verified

`test_gaps_batch.py`'s `TestNegativeControlModuleBounds`
implements the batch's fresh mutant: a `TalentMgmtExtensions`
subclass (`MutantTalentMgmtExtensions`) whose
`_check_module_bounds` seam is a no-op — any module index is
accepted. The traced claim is the extension's analogue of the
core's signature stage bounds rule: **a module-completion
check-off's `module_index` must name a module of the enrollment's
program (`0 <= module_index < len(modules)`), enforced before
anything is stored, so the derived progress view always names
real modules**. The canonical surface rejects an out-of-bounds
check-off whole (nothing recorded, no id consumed); the mutant
stores it, and its derived progress view then raises
`IndexError`, because the stored index names no module. Each
test asserts the canonical expectation, the mutant's divergence,
and a literal `assertRaises(AssertionError)` showing that
treating the mutant's outcome as the expectation fails.

Mutation verification in THIS tree (2026-11-07): the body of
`_check_module_bounds` in the real
`src/talentmgmt/extensions.py` was replaced with `return None`,
the full suite was run: **141 tests ran, exactly 3 failed** —

- `test_gaps_batch.TestNegativeControlModuleBounds.test_canonical_expectation_rejects_out_of_bounds_completion`
- `test_gaps_batch.TestLearning.test_module_completion_out_of_bounds_rejected`
- `test_gaps_batch.TestLearning.test_module_completion_negative_and_bool_rejected`

— exactly the tests that pin the bounds seam on the real
implementation (the mutant-subclass legs pass under the file
mutation, as designed: they override the seam themselves). No
core test failed under the mutant. `extensions.py` was then
restored from `scratch/extensions.py.premutation` and verified
SHA-256-identical to the pre-mutation hash
(`245af1c65be35053fca0d8180bbd38d489865a8372a30b4d20b14fca0f0e662e`,
recorded in `scratch/extensions.py.sha256`); the suite re-ran:
**141 tests, OK**. Raw record: `scratch/batch_mutation_run.txt`.
