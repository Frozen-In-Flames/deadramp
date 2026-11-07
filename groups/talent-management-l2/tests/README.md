# Talent Management L2 — tests

Run the full suite:

```
cd groups/talent-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests
```

99 tests, all passing. Run the live smoke driver separately:

```
PYTHONPATH=src python3 tests/smoke.py
```

## Layout

| File | Tests | What it pins |
| --- | --- | --- |
| `test_access.py` | 7 | RBAC matrix (Core 1): the three roles' action sets exactly; unknown role fail-closed; no write for viewer |
| `test_organizations_candidates.py` | 13 | Cores 1–2: organization/member records, opaque candidate registration, ref uniqueness, membership scoping |
| `test_requisitions_pipelines.py` | 12 | Cores 3–4: requisition lifecycle with derived `past_close`, pipeline records with ordered stage lists, membership scoping |
| `test_placements.py` | 11 | Core 5: placements, the stage bounds rule (out-of-bounds / negative / bool / float / string rejected whole), derived current stage, one active placement per candidate per pipeline, withdrawal |
| `test_events.py` | 9 | Core 6: event records (in-person / virtual kinds), registrations, check-in transitions, event lifecycle |
| `test_assessments_interviews.py` | 9 | Cores 7–8: assessment records with verbatim outcome labels (no score field exists), interview scheduling/completion/cancellation |
| `test_records.py` | 3 | Core 10: workflow definition registry — shape, ref uniqueness, and a pin that the store exposes no execute-like operation |
| `test_reports_search.py` | 7 | Cores 11–12: report key set (exactly 18 keys), counts, active-only stage distribution, no-score key scan; case-insensitive membership-scoped search |
| `test_privacy.py` | 5 | Privacy discipline: exact key sets for all eleven stored shapes, derived-view key deltas, recursive banned-key scan, smuggled kwargs raise `TypeError` |
| `test_audit.py` | 6 | Core 13 (AU): entry shape, all twenty mutation action names in canonical order, failed operations and store reads record nothing, JSONL persistence/reload, no mutation API |
| `test_specs.py` | 7 | Spec integrity: membership equals the census unit, descriptions byte-equal to the cache, literal claim tables (6 + 8 = 14), 12-family taxonomy, verbatim evidence, checked absences hold |
| `test_service.py` | 6 | HTTP contract: `/health`, 401s audited as `:denied`, 403s, 404, full flow with stage bounds over HTTP, admin-only `/audit` whose read is itself audited |
| `test_main_cli.py` | 1 | `python -m talentmgmt serve` answers `/health` |
| `test_negative_control.py` | 3 | The stage bounds rule is load-bearing (below) |
| `smoke.py` | — | Live driver (not a unittest): real server, real requests; prints `SMOKE OK` |
| `talentmgmt_helpers.py` | — | Shared fixtures: demo users, fresh stores, canonical builders |

## Negative control

`test_negative_control.py` proves the group's signature invariant —
the stage bounds rule (Core 5): a movement's `stage_index` must
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

## Mutation verification

The drill was performed on the real store, not only the subclass:
the body of `_check_stage_bounds` in `src/talentmgmt/store.py` was
replaced with `return None`, the full suite was run, and the file
was restored from `tests/store.py.premutation` and verified
byte-identical by SHA-256 (`tests/store.py.sha256`).

Result under mutation: **99 tests run, exactly 5 failures** — the
three bounds tests in `test_placements.py` and
`test_negative_control.py` that exercise the real store, plus the
HTTP bounds test in `test_service.py` (the mutant returned 201 for
`stage_index` 99). The full record is in `tests/mutation-run.txt`.
After restore, the suite is green again (99 tests, OK).

## Live smoke

`tests/smoke.py` starts the real server on an ephemeral port and
drives it over HTTP: health; organization + members; candidate;
requisition; pipeline; placement; an in-bounds movement (201,
derived stage "Interview"); an out-of-bounds movement (400);
event + registration + check-in; an assessment completed with a
verbatim outcome label; a video interview; and a report asserting
`placements_by_stage == {"Interview": 1}` and
`checked_in_count == 1`. It prints `SMOKE OK`.

## Interpretation notes

- Assessments store a caller-supplied **outcome label verbatim** and
  nothing else: there is no score field anywhere in the package,
  pinned by the privacy scan and the report scan. Scoring,
  ranking, and matching are engines (gaps in UNION-SPEC.md), not
  records.
- The report's `placements_by_stage` counts **active** placements
  only; a withdrawn placement's movements remain in the substrate
  but contribute nothing to the distribution.
- The audit flow test pins 23 entries covering all twenty distinct
  mutation action names in order; denials at the HTTP layer are
  recorded by the service with a `:denied` suffix, and store-level
  failures record nothing, so nothing is double-counted.

## Final GAPS batch (Remainder Group 3 section)

`test_gaps_batch.py` (36 tests) pins the batch extension surface
(`src/talentmgmt/extensions.py`, `TalentMgmtExtensions`) that
closes the 7 open entries of this group's GAPS.md section — see
`BATCH.md` in the group directory for the per-entry disposition.
The full suite is now **135 tests, all passing** (99 founding +
36 batch). The batch tests pin: the two labeled reference
implementations (video session and delivery session records with
`reference_stub: True`; automation run records likewise), the
reported-label forms for predictions and ROI figures (a numeric
ROI figure is refused whole), the venue / attendance-report /
invitation records for virtual events (an attendance report
changes nothing in the core registry; an invitation is a
`reference_transport` record, never a send), the no-move pin for
automation reports (a reported run changes no core placement and
creates no core movement), the derived analytics snapshot
(deterministic counts; the core report's 18 keys carried whole),
development progress derived from milestone check-offs and never
stored, exact key sets for all fourteen extension record kinds,
a recursive no-banned-key / no-score-key / no-float scan over
every extension record and derived view, TypeError on smuggled
substance kwargs, signature scans, and RBAC/audit parity with the
core (viewer denial audited as `:denied`; non-member blocked by
the core membership boundary).

### Fresh negative control — development module bounds

`TestNegativeControlModuleBounds` in `test_gaps_batch.py` proves
the batch's signature seam load-bearing:
`_check_development_module_bounds` in `extensions.py` — a
module-milestone's `module_index` must name a module of the
enrollment's program, `0 <= module_index < len(modules)`,
checked before anything is stored (the extension's analogue of
the founding stage bounds rule). A subclass mutant makes the
seam a no-op and accepts an out-of-bounds check-off (index 99),
after which the derived progress view raises `IndexError`
because the stored index names no module; the canonical surface
rejects the same call whole and consumes no id.

The drill was also run live against the real module on
2026-11-07: `_check_development_module_bounds`'s body was
replaced with `return None` in the real `extensions.py`, the
full suite was run, and **exactly 1 of the 135 tests failed**
(`test_canonical_expectation_rejects_out_of_bounds_milestone` —
the two subclass-mutant tests do not depend on the real seam and
kept passing). The module was then restored from
`scratch/extensions.py.premutation` and verified byte-identical
(SHA-256 `bc0a0724786c76c84b2e115f77602f857a7f9895340a7b92dfabb2defcba24cd`,
recorded in `scratch/extensions.py.sha256`); the suite is green
again (135 tests, OK), and every core module is byte-identical
to its pre-batch hash.
