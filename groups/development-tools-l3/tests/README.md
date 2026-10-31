# Tests — Development Tools L3-adjacent singleton (FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to.

This suite **extends the shipped Development Tools L2 suite**: the
L2 tests were copied (every file except `test_additions.py`, which
pins the L2 group's own sheets and does not belong here — 16 files,
66 tests before that additions file) and pass with only the minimal
adaptations listed below, and new files cover the High-baseline
uplifts and this singleton's spec. The L2 package was carried up
with six High-baseline uplifts: hash-chained audit, fail-closed
audit writes, audit query/reduction, `GET /audit/verify`, auditor
role `dana={audit_read}`, and AC-7 logon lockout
(`max_failures=3` / `lockout_seconds=300`; the service returns
exactly 500 `{"error": "audit write failed"}` on
`AuditWriteError`).

## Run

```bash
cd groups/development-tools-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 122 tests
```

Status at delivery: **122 tests, OK** (72 in the 16 inherited
files — the original 66 plus 6 tests added inside those files by
the adaptations below — and 50 in 5 new files). (Run exactly as
above: helpers are imported as a top-level module from the tests
directory and `tests/__init__.py` is empty by design, so
package-mode discovery with `-t .` is not the supported entry
point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | Access control (RBAC) — exact permission matrix, `permissions_for()`, `can()`, `require()`, unknown role denied, developer lacks `audit_read`; **[L3]** role set is exactly four roles, auditor permission set is exactly `{"audit_read"}` (AC-5, +1 test) |
| `test_projects.py` | 5 | Project registry — creation shape/provenance, `prj-` ids, get/list, empty-name validation with no id consumed, viewer write denied, plain-string actor convention |
| `test_issues.py` | 7 | Issue tracking incl. lifecycle — `iss-` shape, unknown project, list filters, happy-path lifecycle, illegal/same-state/unknown transitions rejected with state unchanged |
| `test_reviews.py` | 5 | Code-review records — `rev-` shape, state transitions, merged/closed terminal, list filter. Records only |
| `test_builds.py` | 3 | Build records — `bld-` shape, default `succeeded`, all four statuses, bad status rejected with no id consumed. Records only |
| `test_releases.py` | 4 | Release records — `rel-` shape, duplicate version in same project rejected, same version in different project allowed |
| `test_artifacts.py` | 6 | Artifact registry incl. checksum verify — sha256/size from str/bytes content, checksum-only registration, neither-given rejected, mismatched checksum+content rejected, `verify_artifact` true/false, no content stored |
| `test_deployments.py` | 4 | Environment & deployment records — `env-`/`dep-` shapes, bad status rejected, unknown refs → `NotFoundError`, list filters |
| `test_search.py` | 4 | Search — case-insensitive hits across all five families, no-hit empty lists, empty query → `ValidationError`, `search` action required |
| `test_store_validation.py` | 4 | Store validation (SI-10) — failed creates consume no ids, permission checked before validation/allocation, no-actor writes denied, wrong-typed inputs rejected |
| `test_audit.py` | 6 | Append-only audit log — entry keys (superset incl. [L3] chain fields), User actor normalised, append-only/copies, JSONL persistence + reload (in group `scratch/`) and reload-then-`verify_chain()` (+1 test), store recording mutations and denied attempts |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq from 0, genesis `prev_hash` `"0"*64`, hash recomputation, links, `verify_chain()` clean/tampered/stripped-field/rewritten-`prev_hash`, JSONL round-trip + edited-line detection, `GET /audit/verify` (admin + auditor 200, viewer + developer 403; entries counted before its own `audit_read` entry) |
| `test_audit_failure.py` | 6 | **[L3] AU-5** fail closed: `AuditLog` with an unwritable JSONL path raises `AuditWriteError` and leaves `entries()` unchanged; store `create_project` by ADMIN (action `project_create`) creates NO project and consumes NO id (next good create is `prj-1`); an issue status transition rolls back too; service `POST /projects` returns 500 with body exactly `{"error": "audit write failed"}` |
| `test_audit_query.py` | 13 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until, inclusive window), `GET /audit` with query params over HTTP, auditor can use the reduced search |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: 2 failures then success OK, 3rd consecutive failure locks, locked account gets 403 with correct role + `auth:locked` audit entry, lock is per-user (bob locked, others unaffected), success resets the counter, short `lockout_seconds` server expires and re-admits |
| `test_service.py` | 9 | REST API — live HTTP server: health, 401s, full flow, viewer write 403 + denied audited, 400/404 envelopes; **[L3]** audit endpoint access — admin 200, dana/auditor 200, developer and viewer 403 (denied audited), auditor denied an operational endpoint (`GET /projects` → 403) (+1 test) |
| `test_main_cli.py` | 3 | `python -m devtools serve` subprocess with demo users alice/bob/carol; **[L3] +2**: startup line ends `dana=auditor)`, `--max-failed-logins` / `--lockout-seconds` accepted (parse-level defaults 3/300) and plumbed through (bob locks after 2 bad-role attempts) |
| `test_negative_control.py` | 5 | Negative controls (below): L2 lifecycle-gate and checksum families unchanged (4 tests), plus **[L3]** audit-tamper control (+1 test) |
| `test_singleton_spec.py` | 10 | Singleton spec integrity + substrate: exactly 1 sheet, fork set vs census unit `new-singleton:Development Tools|L3-adjacent`, literal claim table exactly `[(hosted_platform)]`, verbatim evidence/description, tier fields, census citation accounting, other 16 families absent; substrate: platform-onboarding flow, auditor separation of duties, chain verifies after the flow |
| `devtools_helpers.py` | — | Shared fixtures: demo users (ADMIN/DEVELOPER/VIEWER + **[L3]** AUDITOR), `USERS` registry (incl. dana), `fresh_store()`, `make_store()` |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests), chain fields + reload-then-verify in `test_audit.py`, audit-tamper negative control |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read), entries counted before its own `audit_read` entry | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError` (`devtools.errors`); store rolls the whole operation back (no record, no id consumed); service returns exactly 500 `{"error": "audit write failed"}` | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (6 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py`, `test_service.py`, `test_main_cli.py`, `test_audit_chain.py`, `test_audit_query.py`, `test_singleton_spec.py` |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

## Negative controls

1. **`test_negative_control.py::TestNegativeControlLifecycle` and
   `::TestNegativeControlChecksum`** (kept unchanged from L2): a
   `DevToolsStore` subclass (`MutantDevToolsStore`) whose
   `set_issue_status` accepts any transition, and an always-True
   artifact verify. Each canonical case asserts three things: the
   canonical expectation from the real implementation, that the
   mutant would NOT produce that expectation, and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails.
2. **`test_negative_control.py::TestNegativeControlAuditTamper`**
   (new in L3, AU-9): a stored audit entry mutated in place (its
   actor changed to `"mallory"`) must leave
   `verify_chain() == (False, that entry's index)` — the canonical
   verifier **rejects** the tampered log — while a naive mutant
   verifier (`mutant_verify_chain`) that always returns
   `(True, None)` accepts it, shown via the same three-part
   canonical/mutant/`assertRaises(AssertionError)` shape, adapted
   to devtools names (`project_create`/`prj-1`, `issue_create`/`iss-1`).

## Mutation verification

Both drills were performed live in THIS tree, after the suite was
green, on the real implementation (not just the subclass mutants).
Raw outputs are in `../scratch/`.

**Drill 1 — lifecycle gate (signature).** In
`src/devtools/store.py`, within `set_issue_status` ONLY, the
transition check `if status not in allowed:` was patched to
`if False and status not in allowed:` (exactly one replacement,
scoped to that method). The full suite was run: **122 tests ran,
8 failed** (raw output: `../scratch/mutation-run.txt`) — 8 failure
entries across 4 distinct test methods:

- `test_issues.TestIssues.test_lifecycle_illegal_transitions_rejected_state_unchanged` (subtests `bad='open'`, `bad='resolved'`, `bad='bogus'`, `bad='merged'`, plus the follow-on check in the same test — 5 of the 8 failure entries)
- `test_negative_control.TestNegativeControlLifecycle.test_closed_to_resolved_rejected_canonical`
- `test_negative_control.TestNegativeControlLifecycle.test_open_to_resolved_rejected_canonical_but_mutant_allows`
- `test_service.TestServiceAccessAndErrors.test_validation_400_and_not_found_404`

`store.py` was then restored with
`cp scratch/store.py.pristine src/devtools/store.py`; the restored
file's SHA-256 is
`8ca50cf1082d99ed351f527ad7cc46549bafd022f83f1f8a20c3535d5ae8e099`,
identical to the hash recorded in `scratch/store.py.sha256`
(that file records the hash against the name `store.py.pristine`,
so `sha256sum -c` was run inside `scratch/` — `store.py.pristine: OK`
— and the restored `src/devtools/store.py` hash was compared
directly to the recorded hash). The suite was re-run green.

**Drill 2 — audit hash (L3 control).** In
`src/devtools/audit.py`, `_entry_hash` was patched to return
`"0" * 64` unconditionally. The full suite was run: **122 tests
ran, 5 failed** (raw output: `../scratch/audit_mutation_run.txt`) —

- `test_audit_chain.TestHashChainFields.test_hash_is_sha256_of_canonical_json`
- `test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_fails_verification_after_reload`
- `test_audit_chain.TestVerifyChain.test_negative_control_2_mutated_entry_fails_at_index_1`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_broken_link`
- `test_negative_control.TestNegativeControlAuditTamper.test_tampered_entry_is_rejected_by_canonical_verifier`

Honest note (mirroring communication-l3's drill record): the basic
seq/`prev_hash`-linkage assertions still hold under a constant
hash — every `prev_hash` is `"0"*64` and every `hash` is `"0"*64`,
so the links line up trivially; clean-log verification and
stripped-field detection also still pass, since they do not depend
on the hash value. The defect is caught by the canonical-hash
recomputation, the in-place mutation localisation, the
edited-JSONL detection, the broken-link check (the rewritten
`prev_hash` now equals the constant chain value), and the
audit-tamper negative control — which is exactly those tests' job.

`audit.py` was then restored from `scratch/audit.py.pristine`;
the restored file's SHA-256 is
`0625d3fb6bc1c70531ce2ced1812e83479771350e9d3c7a97218b5073dfc6103`,
identical to the hash recorded in `scratch/audit.py.sha256`
(verified the same way: `sha256sum -c` inside `scratch/` —
`audit.py.pristine: OK` — plus a direct hash comparison for the
restored src file).

After both restores the tree is byte-identical to the pre-drill
state (both src hashes match their recorded pristine hashes) and
the full suite was re-run: **122 tests, OK**. The suite catches
both defect classes; neither negative control is decorative.

## L2 test adaptations (complete list)

Every copied L2 test passes as-is except these deliberate,
uplift-driven changes (verified by diff: the other inherited
files — `__init__.py`, `test_artifacts.py`, `test_builds.py`,
`test_deployments.py`, `test_issues.py`, `test_projects.py`,
`test_releases.py`, `test_reviews.py`, `test_search.py`,
`test_store_validation.py` — are byte-identical to L2):

1. **`devtools_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and `USERS["dana"] = "auditor"`;
   the docstring now notes the [L3] auditor. No existing helper,
   user, or fixture changed.
2. **`test_access.py` — role set extended, auditor pin added.**
   `test_matrix_roles_exact` now expects exactly four roles
   `{admin, developer, viewer, auditor}`; one new test,
   `test_auditor_permission_set_exact`, pins the auditor
   permission set as exactly `{"audit_read"}` (AC-5). The existing
   pins are kept (developer lacks `audit_read`, unknown role
   denied).
3. **`test_audit.py` — superset key assertion, plus one test.**
   `test_entry_keys_and_actor_normalisation` now asserts the
   original five keys AND the [L3] chain fields
   `seq`/`prev_hash`/`hash` as subsets (superset assertion, was:
   exact equality). One new test,
   `test_jsonl_reload_then_verify_chain`, reloads a JSONL log and
   asserts `verify_chain() == (True, None)`. No other audit
   assertion changed.
4. **`test_service.py` — audit access is now admin+auditor.**
   A `DANA` header constant was added;
   `test_audit_access_admin_only` now also asserts dana/auditor
   gets 200 on `GET /audit` (admin 200, developer and viewer still
   403); one new test, `test_auditor_denied_operational_endpoint`,
   asserts dana gets 403 on `GET /projects`. Module docstring
   updated to the 4-user registry. No lockout adaptation was
   needed: no carried test makes 3+ failed auth attempts for a
   real username against one server instance (the auth-failure
   test makes at most 1 counted failure per real username), so
   AC-7 never trips in the inherited service tests, and no
   threshold was weakened or raised.
5. **`test_main_cli.py` — additive uplift class.** The module
   docstring now includes `dana=auditor`; a new
   `TestCommandLineUplifts` class (2 tests) checks that
   `--max-failed-logins` / `--lockout-seconds` are accepted at
   parse level (defaults 3/300) and that the startup line ends
   `dana=auditor)` (also asserting dana answers 200 on `/audit`
   and that `--max-failed-logins 2` locks bob after two bad-role
   attempts). The original CLI test is unchanged apart from its
   class docstring wording ("the demo users").
6. **`test_negative_control.py` — audit-tamper control added.**
   The L2 lifecycle-gate and checksum families are unchanged; a
   new `TestNegativeControlAuditTamper` class, its
   `mutant_verify_chain` naive verifier, and a docstring paragraph
   naming it were added (Negative controls #2, above).

No other adaptation was made. `test_additions.py` was NOT copied:
it pins the L2 group's own sheets and does not belong here; its
singleton analogue here is the new `test_singleton_spec.py`.

## Interpretation notes

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
  platform (construction follows crm-l3's `test_audit_failure.py`,
  using a temporary directory).
- Lockout state is scoped to one server instance:
  `test_lockout.py` builds a fresh server per test so failure
  counters never leak between tests.

## Dependency note

Stdlib `unittest` only — no third-party test dependencies. The
new audit-chain/failure/query/lockout/singleton files use only
the standard library (`hashlib`, `http.client`, `json`, `os`,
`tempfile`, `threading`, `time`, `unittest`, `urllib.parse`)
plus the group's own `devtools` package and `devtools_helpers`.
