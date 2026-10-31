# Tests — GRC L3-adjacent singleton build (FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core function /
spec claim / control family it traces to.

This suite **extends the shipped Group 33 (GRC L2) suite**: the L2
tests were copied and pass with only the minimal adaptations listed
below, and new files cover the High-baseline uplifts. Per the Merge
Rule, the merged fork inherits the higher tier (High) in full while
reusing the Group 33 code (Apache-2.0, ours) wherever functions
overlap.

## Run

```bash
cd groups/grc-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 166 tests
```

(Run exactly as above: helpers are imported as a top-level module
from the tests directory and `tests/__init__.py` is empty by design,
so package-mode discovery with `-t .` is not the supported entry
point for this group.)

Status at delivery: **166 tests, OK** (118 inherited from Group 33,
7 added inside inherited files for the uplifts, 41 in new files).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 14 | 9 RBAC — exact permission matrix (admin = all 12 actions, member = 7, viewer = read only), `permissions_for()`, `can()`, `require()`, unknown role/action/user denied; **[L3]** role set is exactly four, auditor role = `{audit_read}` only (AC-5, 5 tests) |
| `test_frameworks.py` | 13 | 1 Framework & control catalog registry — seed catalog has exactly 21 controls with pinned shape, seeded store registry (seeding writes no audit), framework/control registration, duplicate + validation + 404 paths, member denied `manage_frameworks` |
| `test_systems.py` | 6 | 2 Governed-system registry — records keyed by opaque caller-supplied refs, free-text name as label only, duplicate/empty rejected, 404, viewer read-only |
| `test_indicators.py` | 12 | 3 Indicator registry — definitions linked to controls, recorded results with status/timestamp verbatim, default UTC timestamp, unknown indicator/system consumes no result id, list filters, viewer may not record |
| `test_evidence.py` | 11 | 4 Evidence registry — metadata record + SHA-256 + byte size + control/system links, **verify-by-content (original True, tampered False)**, link validation consumes no id, review sets the recorded validation status verbatim (admin-only; the filing member may not review), verify never changes the recorded status |
| `test_findings.py` | 19 | 5 Finding / remediation records — creation shape, severity recorded verbatim, **no score/rating/band/derived key on the record**, the exact `FINDING_TRANSITIONS` map, forbidden transitions denied with status unchanged, canonical lifecycle path, `accepted_risk` requires a recorded rationale, and the **derivation**: current before and on the due date, overdue after it, never overdue once remediated/validated/closed or risk-accepted, stored record carries no derived status key |
| `test_assessments.py` | 13 | 6 Assessment & authorization records — assessment shape with result recorded verbatim, unknown system/framework consumes no id, the exact `AUTH_TRANSITIONS` map, legal path + history growth, denied/expired reopen paths, illegal transitions denied with status unchanged, authorization management admin-only |
| `test_posture.py` | 7 | 7 Posture reporting — empty-store shape with every bucket at zero, counts by framework/system/status, open + overdue counts via the read-time derivation, verbatim severity buckets, indicator/evidence summaries, and a **recursive assertion that no key anywhere mentions score/rating/grade/percent**; posture writes no audit entry |
| `test_service.py` | 15 | 8 REST API — live HTTP: `/health`, 401 unknown user / role mismatch / missing headers, 404 and 400 JSON `{error}` shapes, 403s for viewer posting, member framework registration, member evidence review, member authorization management, `audit_read` admin-only among L2 roles, **denied attempts audited with `:denied`**, full flow; **[L3] +1**: auditor allowed `/audit`, denied `/systems` and `/posture` |
| `test_main_cli.py` | 3 | `python -m grc serve` subprocess with demo users alice/bob/carol answering `/health`, `/systems`, `/posture` and `/audit`, role mismatch → 401, no-subcommand → help + exit 2; **[L3] +1 class**: dana=auditor and `--max-failed-logins` / `--lockout-seconds` |
| `test_audit.py` | 7 | 10 Audit log — entry keys (superset incl. [L3] chain fields), actor normalization, append-only surface (no update/delete API, `entries()` returns copies), JSONL persistence + reload, the store recording each mutation action, reads and failed ops writing nothing |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, canonical-hash recomputation, `verify_chain()`, tamper localization, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` (admin + auditor admitted, member + viewer 403) |
| `test_audit_query.py` | 13 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params, auditor can use the reduced search |
| `test_audit_failure.py` | 7 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, store create/evidence-id/transition roll back in full (no record, no id consumed), service create is not a success |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, success resets counter, lock expiry |
| `test_negative_control.py` | 5 | Negative control #1 (below), unchanged from Group 33 |
| `grc_helpers.py` | — | Shared fixtures: demo users (ADMIN=alice/admin, MEMBER=bob/member, VIEWER=carol/viewer, **[L3]** AUDITOR=dana/auditor), `USERS_REGISTRY` (incl. dana), `make_store()` (store + one governed system `SYS-001` + one indicator `KSI-1` → IA-2), `fresh_store()`, `make_system()`, `make_indicator()`, `make_finding()` |
| `store.py.premutation` | — | Pre-mutation copy of `../src/grc/store.py` used by the mutation drill below (SHA-256 recorded there) |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (snapshot over the nine record dicts + counters), service does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (7 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `__main__.py` | `test_access.py` (5 tests), `test_service.py`, `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 L2 core functions keep their Group 33 coverage (see the file
table); the L3 public API contract is the L2 contract plus exactly
the uplifts above. The no-scoring doctrine keeps its Group 33
enforcement at this tier: `test_findings.py` pins the absence of any
score/rating/band key on finding records and `test_posture.py`
recursively asserts no key anywhere in the posture output mentions
score/rating/grade/percent — this fork's `risk_management` claim (an
AI prediction engine, Extended) changes none of that.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 33): the
   contract's required mutant — a status-derivation function whose
   overdue branch **never fires**, returning the stored lifecycle
   status unconditionally. The traced claim: an open finding due
   2026-06-30 derives `"open"` at as_of 2026-06-30 and `"overdue"`
   at as_of 2026-07-01. The test asserts the real
   `derive_finding_status` separates the pair, that the mutant
   collapses both to `"open"`, and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   output as the expected output fails. An end-to-end arm repeats
   the separation through the store.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field, a rewritten `prev_hash`, and an edited
   JSONL line after reload.

## Mutation verification

Both drills were performed live by the coordinator (2026-10-31) on
the real implementation (not just the subclass mutants):

**Drill 1 — status derivation (inherited control).** The derivation
in `src/grc/store.py` (`derive_finding_status`) was patched so the
overdue branch never fires — `if _coerce_as_of(as_of) > due:`
replaced with `if False:` — the exact live counterpart of the
mutant in `test_negative_control.py`. The full suite was run:
**166 tests ran, 8 failed** —

- `test_findings.TestDerivedStatus.test_list_findings_with_as_of_attaches_derivation`
- `test_findings.TestDerivedStatus.test_overdue_after_due_date`
- `test_findings.TestDerivedStatus.test_stored_record_carries_no_derived_status`
- `test_negative_control.TestNegativeControlEndToEnd.test_past_due_open_finding_reads_overdue_in_store`
- `test_negative_control.TestNegativeControlMutantDerivation.test_mutant_also_collapses_in_progress`
- `test_negative_control.TestNegativeControlMutantDerivation.test_real_derivation_separates_the_canonical_pair`
- `test_posture.TestPostureCounts.test_open_and_overdue_counts_use_the_derivation`
- `test_service.TestFullFlow.test_full_flow`

— the **identical failure set to Group 33's drill** at L2. The
failures span every surface that depends on the derivation: the
pure function, the store's as-of reads, the posture overdue count,
and the HTTP full flow. `store.py` was then restored from the
pre-mutation copy (`scratch/store.py.premutation`, also kept at
`tests/store.py.premutation`; SHA-256
`0fe88eb1f8099a30750accc4ebe2afaa36adafbea845b36bd796b42f33507025`,
recorded in `scratch/store.py.sha256` and verified identical after
restore) and the suite re-run: **166 tests, OK**.

**Drill 2 — audit verifier [L3].** `AuditLog.verify_chain`
(`src/grc/audit.py`) was patched to return `(True, None)`
unconditionally — a verifier that never verifies. The audit test
files were run: **42 tests ran, 4 failed** —

- `test_audit_chain.TestVerifyChain.test_negative_control_2_mutated_entry_fails_at_index_1`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_broken_link`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_missing_hash_fields`
- `test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_fails_verification_after_reload`

`audit.py` was then restored from `scratch/audit.py.premutation`
(SHA-256
`df7b1ef9cb00458f1a56673900bf05b30a855fd4dede1f6e24e9ac4647abcb34`,
recorded in `scratch/audit.py.sha256` and verified identical after
restore) and the full suite re-run: **166 tests, OK**. The suite
catches both defect classes; neither negative control is decorative.

## Group 33 test adaptations (complete list)

Every copied Group 33 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_access.py` — role-set test extended, additive auditor
   class.** `test_roles_are_admin_member_viewer` became
   `test_roles_are_admin_member_viewer_auditor`: uplift 5 adds the
   `auditor` role to `PERMISSIONS` / `ROLES`. All existing per-role
   permission assertions are unchanged (existing roles' permissions
   did not move). Five auditor tests were added in a new
   `TestAuditorRole` class (AC-5).
2. **`test_audit.py` — one exact key-set assertion relaxed to a
   superset.** `test_entry_keys_and_actor_normalization` asserted
   audit entries carry *exactly* `{ts, actor, action, target,
   details}`. Uplift 1 adds `seq` / `prev_hash` / `hash` to every
   entry, so the assertion now requires the original five keys plus
   the three chain keys as subsets. The test's docstring was updated
   to say so. No other audit assertion changed — the original keys
   and values are unchanged, per the uplift spec. (The append-only
   surface test still holds: `verify_chain` / `query` are read
   surfaces, not mutation APIs.)
3. **`grc_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user; the
   module docstring header now reads "GRC L3 test suite". No
   existing helper, user, or fixture changed; `test_service.py`
   (which consumes the registry) needed one additive test only —
   its per-username auth failures against the class server stay
   below the new default lockout threshold (alice 1, mallory 1),
   so no lockout trips.
4. **`test_service.py` — additive only.** One new test
   (`test_audit_read_auditor_allowed_records_denied`) plus the
   `DANA` header constant; the original
   `test_audit_read_is_admin_only` docstring now reads "among the
   L2 roles" (its assertions are unchanged).
5. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags and
   the dana demo user; the original CLI tests are unchanged apart
   from the module docstring's identity list.

No other Group 33 test file was modified (`test_assessments.py`,
`test_evidence.py`, `test_findings.py`, `test_frameworks.py`,
`test_indicators.py`, `test_negative_control.py`, `test_posture.py`,
`test_systems.py` are byte-identical to Group 33).

## Interpretation notes

Inherited from Group 33 and still in force:

- "Open findings" in posture counts the lifecycle states `open`,
  `in_progress`, and `accepted_risk` (a risk-accepted POA&M item is
  still an open item until it is closed or returns to work); the
  derivation's overdue states are exactly `open` / `in_progress`, so
  a risk-accepted finding is never overdue.
- Overdue is strict: an open finding is overdue only when the as-of
  date is *after* the due date; on the due date itself it is still
  current.
- `get_finding` / `list_findings` without `as_of` return exactly the
  stored fields — that is how the suite shows the stored record
  carries no derived status key — and with `as_of` the returned
  copies gain `derived_status`.
- Statuses the contract says are "recorded verbatim" (indicator
  result status, finding severity, assessment result, evidence
  validation status) are asserted verbatim with deliberately
  non-canonical strings (vendor wording, mixed case) so any
  normalization would fail the suite.
- Over HTTP, creation endpoints are asserted as exactly 201, auth
  failures as exactly 401, permission failures as exactly 403, and
  the list endpoints with their wrappers (`{"frameworks": [...]}`,
  `{"controls": [...]}`, `{"systems": [...]}`, `{"indicators":
  [...]}`, `{"results": [...]}`, `{"evidence": [...]}`, `{"findings":
  [...]}`, `{"assessments": [...]}`, `{"authorizations": [...]}`,
  `{"entries": [...]}`); `/posture` is the bare summary dict.

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic.
- `GET /audit/verify` reads the entry count *before* appending its
  own `audit_read` entry; the endpoint test asserts against the
  pre-request length.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform.
- GRC's service layer keeps its user registry in `__main__.py`'s
  `DEMO_USERS` (there is no service-level `USERS` dict in this
  package, unlike CRM's); the HTTP tests pass `USERS_REGISTRY` from
  `grc_helpers` explicitly, as the Group 33 suite did.
