# Tests — Event Management L1 singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**79 tests, all passing** (Python 3 standard library `unittest`
only). Each test module's header names the core function, spec
claim, or control family it traces to.

| Module | Covers |
|---|---|
| `test_access.py` | Role/permission matrix (AC family) |
| `test_registries.py` | Organizer & vendor registries: pinned shapes, no identifier field possible, ref uniqueness |
| `test_events.py` | Event records: claimed formats, status derived at read and never stored (pinned stored key set); preparation task records and their completion lifecycle |
| `test_sessions.py` | Session records for the three claimed gathering kinds; window-within-event containment; derived status; speaker as opaque ref only |
| `test_outreach.py` | Outreach records: organizer/event ownership guard, recorded never sent |
| `test_matchmaking.py` | Round & participation records: tag normalization, one participation per vendor per round, open-round-only recording, immutability |
| `test_matches.py` | **The signature invariant**: coverage rule (tag set covers required set), matches derived never stored, empty-criteria semantics, derivation survives round close, recursive no-score key scan |
| `test_reporting.py` | Search & summary: counts only, matches total as a derived count, recursive no-score key scan over summaries, match views, and stored records |
| `test_audit.py` | Append-only audit log; mutations recorded, failures not; `audit_read` admin-only; JSONL persistence |
| `test_service.py` | REST API over real HTTP: full flow through rounds/participations/matches, bad format rejected (400), auth failures (401/403), exactly 3 denied attempts audited |
| `test_main_cli.py` | CLI argument handling and demo-user wiring |
| `test_specs.py` | Spec integrity: membership == census unit {FR2304546222}, recorded fields match `forks.json`, taxonomy == the 8 own-description families, evidence verbatim, matchmaking evidence pinned to the provision sentence, census citations verify |
| `test_negative_control.py` | The mutation-verified negative control (below) |

## Negative control — mutation-verified

The signature invariant is the match derivation: a round's
matches are the participations whose recorded capability tags
**cover** the round's recorded required tags (set inclusion),
derived at read by the single seam `_derive_matches` in
`src/events/store.py`. An oracle that passes under both inclusion
directions is testing that code ran, not that coverage is the
rule — so the invariant is verified two ways:

1. **In-tree mutant** (`test_negative_control.py`): the canonical
   match expectation is asserted against a run where the
   `_derive_matches` seam is swapped for a mutant reversing the
   inclusion (a participation qualifies when its tags are a
   *subset* of the required tags). The test asserts the canonical
   check raises `AssertionError` against the mutant. A third test
   pins the honest limit of the discrimination: an exactly-matching
   participation satisfies both directions, so the discrimination
   lives in the canonical fixture's superset/subset pair.
2. **External drill** (performed on this tree, recorded in
   `scratch/mutation-run.txt`): `_derive_matches` in the real
   `src/events/store.py` was patched to reverse the inclusion,
   the full suite re-run, and the file then restored.

**Drill result: exactly 6 failures out of 79 tests:**

- `test_matches.MatchTests.test_coverage_rule`
- `test_matches.MatchTests.test_empty_required_tags_admits_every_participation`
- `test_matches.MatchTests.test_match_is_derived_not_stored`
- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`
- `test_reporting.SummaryTests.test_matches_total_is_a_derived_count`
- `test_service.ServiceTests.test_full_flow`

Every other test still passed against the mutant (the mutant
changes only who qualifies, nothing else — which is the point:
the six failures are exactly the tests that pin the invariant and
its downstream derivations). The store was then restored from
`scratch/store.py.premutation` and verified **byte-identical by
SHA-256** (`scratch/store.py.sha256`), and the full suite re-ran
green: **79 tests, OK**.
