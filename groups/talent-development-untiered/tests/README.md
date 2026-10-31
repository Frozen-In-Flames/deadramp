# Tests — Talent Development, untiered (DeadRamp Phase 2, Untiered Set 20)

Run everything from this directory:

    cd groups/talent-development-untiered
    PYTHONPATH=src python3 -m unittest discover -s tests

`talentdev_helpers.py` builds a fresh store wired to an in-memory
audit log, with one actor per role — alice (admin), bob (operator),
carol (viewer) — and the shared fixtures (one organization, one
program).

58 tests, fully green.

## Layout

- `test_access.py` — the roles/permissions matrix (core function
  11): admin, operator, viewer; unknown roles/users denied.
- `test_audit.py` — the audit log (core function 12): append-only
  entries with actor/action/target; entries returned as copies;
  JSONL persistence round-trips.
- `test_programs.py` — organizations, programs, and participations
  (core functions 1, 2, 3): organization references unique; both
  development kinds recorded separately and an unknown kind
  (including `coaching` and `learning_management`) refused;
  participation status is derived at read through the
  `_derive_participation_status` seam and the stored record
  provably has no `status` key; duplicate enrollment refused;
  completion before enrollment refused; person references cannot
  be email addresses or carry whitespace; viewer writes denied.
- `test_assessments.py` — assessment and result records (core
  functions 4 and 5): results record administration outcomes only;
  judgment outcomes (`passed`, `failed`, `excellent`, a numeric
  string) are all refused; results require a known assessment and
  a clean subject reference.
- `test_insights.py` — insight snapshots (core function 6): the
  snapshot shape carries no person reference; THE small-cohort
  guard — cohorts of 0, 1, and 4 are refused, record nothing, and
  consume no id, and a cohort of exactly 5 records; value counts
  may not exceed the cohort; counts are strict integers (bools,
  floats, strings, negatives refused).
- `test_decisions.py` — decision records (core function 7): the
  decision vocabulary is closed; every basis id must exist and
  belong to the deciding organization; the decider is an opaque
  reference.
- `test_shapes.py` — pinned record shapes: exact key sets for all
  seven record types (the participation set proves no stored
  `status`; the snapshot set proves no person reference); the
  result record carries no numeric field of any kind; a recursive
  scan over a fully populated store proves no forbidden key part
  exists anywhere (score, grade, rank, rating, rate, email, ssn,
  password, secret, salary, wage, price, fee, amount, cost,
  diagnosis, health).
- `test_negative_control.py` — the mutation-verified negative
  control (below).
- `test_service.py` — the REST API over real HTTP (core function
  10): health is public; missing headers, unknown users, and
  mismatched roles are 401; the full flow exercises the
  small-cohort guard end to end (a snapshot over a cohort of 3 is
  a 400) and the closed outcome vocabulary (a `passed` result is
  a 400); viewer writes are 403 and audited with a `:denied`
  suffix; the audit endpoint requires `audit_read`; 404/405
  mapping.
- `test_main_cli.py` — the CLI entry point: demo-user wiring; no
  command returns 2.
- `test_specs.py` — spec integrity: membership exactly the census
  unit `untiered:Talent Development` ({FR2318956176,
  FR2635930421}); tier null on every sheet (`cmmc_tier` None,
  `fedramp_impact_level` "Unknown"); recorded vendor/product/
  status match forks.json; the claim tables equal the expected
  tables (BetterUp 2, FORGE 3, total 5) under the set's own
  5-family taxonomy; every claim's evidence sentence appears in
  the fork's description (whitespace-normalized); the two
  development families are pinned un-merged (neither fork claims
  the other's, and each phrase is absent from the other
  description); each fork's single census citation verifies and
  neither serves as claim evidence; FORGE's `certified_services`
  self-entry is recorded and was never matched; the
  checked-absence tokens are absent from both descriptions at
  token level; no CMMC equivalence language appears in any sheet.

## Negative control — the small-cohort-guard drill

The signature invariant is the small-cohort guard: an insight
snapshot may not be recorded for a cohort smaller than
`MIN_COHORT_SIZE` (5), because an aggregate count over a handful
of people can single out an individual — the outcome BetterUp's
privacy sentence says its dashboard avoids. An oracle that passes
whether or not the guard enforces would be testing that code
ran, not that the guard holds. The drill mutates the guard seam
in the real `src/talentdev/store.py`:

    def _check_cohort_allowed(cohort_size):   # becomes
        return None  # MUTANT (drill): cohort guard disabled

(the body that raises `ValidationError` below the floor is
replaced with a no-op), then the full suite is re-run. Result:
exactly 3 failures, all guard-dependent —

- `test_insights.TestSnapshots.test_small_cohort_guard`
- `test_negative_control.TestNegativeControl.test_canonical_check_passes_on_the_real_derivation`
- `test_service.TestService.test_full_flow`

No other test moved: the guard's other arms (value-exceeds-cohort
refusal, strict-integer counts, the at-the-floor cohort recording)
do not depend on the seam's refusal and correctly kept passing.
Raw drill output: `scratch/mutation-failures.txt`.

After the drill, `store.py` is restored byte-identical
(SHA-256 `8d30cd1360f25e7f25e9313590c99c6baaa49050a884f67e58c2cd968bde4213`,
verified with `sha256sum -c`) and the suite is fully green again.
`test_negative_control.py` also carries the drill's in-tree form:
the same mutant applied by monkeypatch, with the canonical check
asserted to fail against it — plus the discriminating other arm
(a cohort of exactly `MIN_COHORT_SIZE` IS recorded on the real
store, so the invariant is a floor, not a ban).
