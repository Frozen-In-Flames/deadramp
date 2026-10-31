# Tests — Storage L3-adjacent singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**127 tests, all passing** (Python 3 standard library `unittest`
only). Each test module's header names the core function, spec
claim, or control family it traces to. The parent group's suite
is carried up and adapted where the High uplifts extend it; the
uplift modules (`test_audit_chain.py`, `test_audit_failure.py`,
`test_audit_query.py`, `test_lockout.py`) and the singleton spec
module are new at this tier.

| Module | Covers |
|---|---|
| `test_access.py` | Role/permission matrix (AC family) at High, including the separated `auditor` role holding `audit_read` only (AC-5) |
| `test_registries.py` | Organization, retention-policy & collection registries: pinned shapes, ref uniqueness, policy immutability, integer retention days (SI-10) |
| `test_messages.py` | Message archive records: metadata-only pinned shape (recursive no-content scan), per-collection ref uniqueness, custody linkage guards, no-id-on-failure |
| `test_retention.py` | **The signature invariant**: the derivation seam, derived-at-read state (never stored), derived boundary, exact-boundary eligibility, the disposition gate (refuses inside retention, allows at/after, refuses double), per-policy derivation |
| `test_discovery.py` | Discovery records: scope filters, computed result sets, no free-text query field on the shape |
| `test_supervision.py` | Supervision review records: lifecycle transitions, terminal `reviewed`, outcome validation |
| `test_enforcement.py` | Enforcement action records; an `extend_retention` record provably does not change the derivation |
| `test_retrievals.py` | Retrieval & export records: modes/destinations, completion lifecycle |
| `test_custody.py` | Key custody records: shape holds no key material, one-active-per-collection invariant, retire & replace |
| `test_integrations.py` | Integration registry: records only, no execution surface, deactivate lifecycle |
| `test_reporting.py` | Search (literal, metadata-only) & summary: counts only, retention counts follow the clock through the same seam, recursive no-score key scan |
| `test_audit.py` | Append-only audit log; mutations recorded, failures not; `audit_read` gated on the permission (admin **and** auditor); JSONL persistence |
| `test_audit_chain.py` | **[L3] AU-9/AU-3**: chain fields (`seq`/`prev_hash`/`hash`), genesis link, hash recomputed independently as SHA-256 of canonical JSON, tamper localized at the mutated index, JSONL round-trip, edited-line detection after reload, and the `GET /audit/verify` endpoint (auditor allowed; operator/viewer denied; count read before its own audit entry) |
| `test_audit_failure.py` | **[L3] AU-5**: `record()` raises `AuditWriteError` and rolls back the in-memory append; the chain still verifies after a failed record; store operations roll back whole (no record, no id consumed; a custody retirement leaves the record active); the service answers exactly 500 `{"error": "audit write failed"}` and creates nothing |
| `test_audit_query.py` | **[L3] AU-7**: `query()` filters (actor/action/target/since/until, inclusive, conjunctive) over pinned timestamps; `GET /audit` filter parameters; the unfiltered shape unchanged; the auditor may query |
| `test_lockout.py` | **[L3] AC-7**: 3 consecutive authentication failures lock the username (correct role then gets 403 with the lockout body, audited `auth:locked`); per-user isolation; unknown usernames lock too; a success resets the counter; permission 403s never count; the lock expires after `lockout_seconds` |
| `test_service.py` | REST API over real HTTP: full flow through the retention gate, float/bool rejected (400), auth failures (401/403), exactly 3 denied attempts audited |
| `test_main_cli.py` | CLI argument handling and demo-user wiring (now including `dana=auditor`) |
| `test_singleton_spec.py` | Spec integrity for THIS singleton: membership == census unit {FR2115384377} with `extends_group` null, recorded fields match `forks.json`, description verbatim vs the cache record, **functions_claimed pinned empty**, the taxonomy pinned as the parent's verbatim 11 families (ast-parsed from the parent extractor), the census citation verified-but-not-a-claim, the catalogue hit pinned as removed-by-exclusion, checked absences holding at token level, the two substance retirements (backup, audit) pinned as occurring, and three carried-substrate cases (disposition gate under custody linkage, auditor separation at store level, chain verifies after a flow) — substrate cases, explicitly not this fork's claims |
| `test_negative_control.py` | The mutation-verified negative control (below) |

## Negative controls — mutation-verified (two seams at this tier)

**Seam 1 — the retention derivation (inherited).** A message's
retention state is computed at read by the single seam
`_derive_retention_state` in `src/storage/store.py`, and a
disposition may be recorded only when the derived state is
`disposition_eligible`. An oracle that passes whether or not
retention has expired is testing that code ran, not that
retention is enforced — so the invariant is verified two ways:
the in-tree control (`test_negative_control.py`) asserts the
canonical gate expectation passes on the real store and FAILS
against a mutant seam under which retention never expires, and
the external drill below applied the equivalent patch to the
real file.

**Seam 2 — the audit hash chain (new at this tier).**
`test_audit_chain.py` carries the in-tree tamper controls: a
stored entry mutated in place (`log._entries[1]["actor"] =
"mallory"`) must make `verify_chain()` fail at index 1, a broken
`prev_hash` link and a stripped hash field must each fail at
their own index, and an edited JSONL line must fail verification
after reload. The external drill below applied the constant-hash
mutant to the real `_entry_hash`.

## External mutation drills — performed live in this tree

Both drills: premutation copy saved with its SHA-256, one seam
patched, the full 127-test suite run, the file restored from the
premutation copy and verified byte-identical by SHA-256, the
suite green again. Full record: `scratch/mutation-run.txt`.

**Drill 1 — retention gate.** Patch: in `_derive_retention_state`
(`src/storage/store.py`), the single occurrence of
`if now >= boundary:` → `if False:`.
Premutation SHA-256:
`903dd5d27dabb6d684f55749243fbd8be3ea9693e9b68c7653ec66bd37a12aba`.
Result: **exactly 10 tests did not pass (7 failures, 3 errors)** —
`test_retention.SeamTests.test_seam_states`,
`test_retention.RetentionViewTests.test_state_is_derived_at_read_and_never_stored`,
`test_retention.RetentionViewTests.test_exact_boundary_is_eligible`,
`test_retention.RetentionViewTests.test_list_filter_by_derived_state`,
`test_retention.DispositionGateTests.test_disposition_at_and_after_boundary` (error),
`test_retention.DispositionGateTests.test_double_disposition_is_refused` (error),
`test_reporting.ReportingTests.test_summary_retention_counts_follow_the_clock`,
`test_service.ServiceTests.test_full_flow_with_retention_gate`,
`test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`,
`test_singleton_spec.CarriedSubstrateCaseTests.test_custody_linked_archival_reaches_the_disposition_gate` (error).
The 2 gate-test errors are the tests whose fixture records a
disposition on an eligible message; under the mutant the gate
never opens, so the fixture itself raises. The parent group's
drill found 9 non-passing; the tenth here is this tier's
singleton substrate case, which pins the same invariant.

**Drill 2 — audit hash.** Patch: `_entry_hash`
(`src/storage/audit.py`) returns the constant `"0" * 64`.
Premutation SHA-256:
`bb2722652ca92c4466fe53ca716ff6ad560736fc0ee8a2ab45500001419177be`.
Result: **exactly 4 tests failed** —
`test_audit_chain.TestHashChainFields.test_hash_is_sha256_of_canonical_json`,
`test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_fails_verification_after_reload`,
`test_audit_chain.TestVerifyChain.test_negative_control_2_mutated_entry_fails_at_index_1`,
`test_audit_chain.TestVerifyChain.test_verify_chain_detects_broken_link`.
Under a constant hash the chain still self-links and a clean log
still verifies, so these 4 are exactly the tests that
discriminate a real hash from a constant. (The Development Tools
L3 precedent found 5; its fifth was a separate
canonical-verifier negative-control test that this lineage's
negative-control file does not carry — that file is the
retention seam's.)
