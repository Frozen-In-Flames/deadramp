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
