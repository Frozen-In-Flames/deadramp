# Tests — Research untiered set (tier null)

Stdlib `unittest` only. Every test module's header names the core
function / spec claim it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/research-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 93 tests
```

Status at delivery: **93 tests, OK** — the founding Research L2
group's 85-test core suite carried with the code (its
`test_additions.py` module is NOT carried: it pins the parent
group's own remainder-addition census unit), plus 8 new spec
tests in `test_specs.py` pinning this set.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 10 Access control — exact permission matrix for the research actions, `require()` denials; audit_read admin-only |
| `test_commons.py` | 17 | 1 Commons registry — creation validation (bad kind, duplicate name, failed creation consumes no id), event-driven lifecycle and its illegal transitions, membership boundary (outsider denied, admin reaches without membership), pinned stored shape |
| `test_organizations.py` | 6 | 2 Organizations — pinned record shape, duplicate refs, profile updates |
| `test_workspaces.py` | 5 | 3 Workspaces — pinned shape, create/get/list inside a commons, outsider denied |
| `test_datasets.py` | 9 | 4 Datasets — pinned exact key set (no field can hold content), checksum validation and normalization, size validation, tier validation, verify-by-content true/false |
| `test_access_requests.py` | 9 | 5 Access requests — controlled-only rule (open dataset rejected), duration validation (floats/bools/strings rejected whole), withdraw lifecycle |
| `test_decisions_grants.py` | 10 | 6 Decisions (separation of duties: decider is never the requester, with no state change on denial; non-pending decision rejected; decline mints nothing), 7 Grants — expiry = start + duration, derivation scheduled/active/expired, revocation beats expiry, stored record carries no `status` key, derived-status list filter |
| `test_reporting.py` | 6 | 8 Search & summary — substring search scoping (outsider sees no commons content); summary counts computed from records, grants recounted by derived status at two clocks |
| `test_service.py` | 7 | 9 REST API — live HTTP: 401/403/404/400 semantics, the full sharing flow over HTTP including grant reads at two `?now=` values, denied attempts audited with `:denied` |
| `test_audit.py` | 5 | 11 Audit log — mutation recording, entry shape, JSONL persistence round-trip, no mutation API |
| `test_main_cli.py` | 1 | CLI — `python -m research serve` subprocess answers `/health` |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_specs.py` | 8 | This set's spec pins — exactly 4 sheets; membership exact against census unit `untiered:Research` in `remainder.json` (ids and order); every sheet's tier null / impact "Unknown"; registry fields vs `forks.json`; source business categories recorded as-is (including Sustainment's list, which carries no "Research"); descriptions exact-equal to the census record in `remainder/uncovered.json` with no carriage returns; the literal claim table (0 claims total, all four forks zero-claim); census citations 6/6 verbatim in the descriptions |
| `research_helpers.py` | — | Canonical fixture carried from the founding suite (one labeling fix: its docstring now names this untiered set instead of L2): commons `gen3-commons` by bob, erin added as staff member (the canonical decider — requests are bob's, and the decider is never the requester), ORG-100 organization; outsider dave in no commons; fixed clock anchors (T0, window, expiry) |

## Negative control

**`test_negative_control.py`** — the category's signature
invariant is **grant status derivation**: a grant reads `active`
only while unrevoked, unexpired, and started, and that status is
derived at read, never stored. The mutant is a `ResearchStore`
subclass (`MutantResearchStore`) whose `_derive_grant_status`
always returns `"active"`. The tests assert the canonical
expectations (an expired grant reads `expired`; a revoked grant
reads `revoked`), and — via literal `assertRaises(AssertionError)`
— that the canonical expectations reject the mutant's outcomes
(the mutant reports both grants as `active`).

## Mutation verification — re-run in this tree

VERIFIED for this untiered build: `_derive_grant_status` in the
real `src/research/store.py` was patched to return `"active"`
unconditionally and the full suite was run against the patched
implementation.

- Patched run: **93 ran, exactly 7 failed** — the founding
  group's original drill set, unchanged:
  - `test_decisions_grants.TestGrantDerivation.test_status_is_derived_from_the_read_clock`
  - `test_decisions_grants.TestGrantDerivation.test_revocation_beats_expiry`
  - `test_decisions_grants.TestGrantDerivation.test_list_grants_status_filter_uses_derived_status`
  - `test_negative_control.TestNegativeControlGrantDerivation.test_canonical_expired_grant_reads_expired`
  - `test_negative_control.TestNegativeControlGrantDerivation.test_canonical_revoked_grant_reads_revoked`
  - `test_reporting.TestCommonsSummary.test_summary_counts_computed_from_records`
  - `test_service.TestServiceFlow.test_full_sharing_flow_over_http`
- No spec test failed under the mutant: `test_specs.py` pins the
  spec sheets, not the derivation seam.
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`ff43a9ac…`, recorded in
  `scratch/store.py.sha256` — the same hash as the founding
  group's shipped store, since the module is byte-identical);
  the suite is green again (93/93). Raw drill output is in
  `scratch/mutation_run.txt`.

The failing set is exactly the derivation-dependent set: the
separation-of-duties, open-dataset-gate, and shape-pinning tests
are untouched by this mutation (they guard different seams), and
the boundary test (a read at exactly `expires_at` still derives
`active`, because expiry is `moment > expires_at` per the
contract) is a canonical-expectation test that passes under both
implementations — the mutant agrees with the contract at that one
instant by construction.

## Interpretation notes

- Grant status is derived at read: the tests pin this twice over,
  once through the public views at different `now` values and once
  by asserting the raw stored records (`store._grants`) carry no
  `status` key at all and match the pinned key set exactly.
- Commons lifecycle status and request lifecycle status are
  event-driven, not date-driven, so they *are* stored — the
  distinction is deliberate and stated in the store's module
  docstring.
- `decide_access_request` returns `{"decision": ..., "request":
  ...}` plus `"grant"` (the grant view, with derived status) on
  approvals only; a decline carries no grant key and mints no
  grant record.
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.
- Derivation boundary, per the contract text: a grant is `expired`
  only when the read moment is strictly after `expires_at`, so a
  read at exactly `expires_at` derives `active`. The tests assert
  the contract as written rather than a rounded version of it.
- Tier discipline is pinned in `test_specs.py`, not in the core
  suite: the carried core contains no tier or baseline machinery,
  so there is nothing tier-shaped for the core tests to pin.
