# Tests — Data Management L3-adjacent merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/data-management-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 239 tests
```

Status at delivery: **239 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

Inherited from Group 12 (197 tests after adaptation — see below):

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix over `PERMISSIONS`/`ACTIONS` for admin/steward/viewer/auditor, the nine pinned write actions, `permissions_for()`, `can()`, `require()`, unknown role/action denied, None user denied |
| `test_audit.py` | Audit log — entry keys (incl. chain fields), User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording each mutation action (dataset_create … export_create, search), failed ops record nothing |
| `test_datasets.py` | Datasets — creation shape/provenance/defaults, `ds-` ids, all classifications, schema validation, `update_dataset`, `update_schema` version bump, denied writes consume no id, get/list sorted, unknown id → `NotFoundError`, plain-string actor identity |
| `test_sources_ingestion.py` | Sources + ingestion + provenance — `src-`/`ing-` creation and validation, unknown dataset/source → `NotFoundError`, bad mode/status/record_count → `ValidationError` with no id consumed, provenance totals over completed ingestions only |
| `test_quality.py` | Quality rules + checks — `qr-` creation and per-kind params validation; one hand-computed check run per kind, `passed` flag, `qc-` ids, viewer run denied |
| `test_access_governance.py` | Access requests + grants — `ar-` flow and duration bounds, duplicate pending rejected, self-decision → `PermissionDenied` (also for an admin requester), approve → `gr-` grant fields + expiry math, deny path consuming no grant id, revoke + double-revoke, `active_grants` filtering with explicit `now` |
| `test_retention.py` | Retention policies — `rp-` set/get/list, duplicate policy rejected with no id consumed, update, dispositions, due computation with explicit `now` (reference = latest completed ingestion, else dataset creation; `legal_hold` excluded) |
| `test_export.py` | Exports — `ex-` manifest with records (checksum equal to the locally computed sha256 of the canonical JSON), csv, empty records; without records (count from completed ingestions, checksum None, current schema_version); bad format / viewer denied with no id consumed; get/list |
| `test_search.py` | Search — datasets/sources/quality rules by their fields; case-insensitive; literal (regex metacharacters inert); blank query → all empty; non-string query → `ValidationError` |
| `test_service.py` | REST API — live HTTP server: health (no auth), 401 unknown user + role mismatch, 403 viewer dataset create (denied attempt audited `<action>:denied`), the full flow (dataset → source → ingestion → quality rule → check → access request → decide → grants → retention → retention-due → export → search → audit), 400/404 error envelopes |
| `test_main_cli.py` | `python -m datamgmt serve --port <free>` subprocess (PYTHONPATH=src), waits for health, answers alice on `/audit`, carol/bob on `/datasets`, dana (auditor) on `/audit` (200) and `/datasets` (403) |
| `test_negative_control.py` | Negative control #1 (below) |
| `datamgmt_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, STEWARD=bob/steward, VIEWER=carol/viewer, AUDITOR=dana/auditor), `USERS` registry, `fresh_store()`, `make_store()` (canonical dataset "Claims Extract" + source "ehr-feed", created by STEWARD) |

New at the High baseline (42 tests):

| File | Covers |
|---|---|
| `test_audit_chain.py` | Hash chain (AU-9/AU-3) — chain fields on every entry, genesis `prev_hash`, independent SHA-256 recomputation, link continuity, `verify_chain()` clean/empty, **negative control #2** (in-place entry mutation detected at exactly index 1), missing-field and broken-link detection, JSONL round-trip + edited-line detection after reload, `GET /audit/verify` (admin + auditor allowed, viewer + steward 403, count read before the endpoint's own audit entry) |
| `test_audit_query.py` | Audit reduction (AU-7) — `AuditLog.query` by actor/action/target, combined filters, since/until windows (inclusive, ISO-string comparison), results are copies; `GET /audit` filter pass-through over HTTP incl. `since`, unfiltered read unchanged, filter still audit_read-gated |
| `test_audit_failure.py` | Fail closed (AU-5) — `record()` raises `AuditWriteError` and rolls the append back on an unwritable JSONL path, chain still verifies with contiguous `seq`; store-level rollback: `create_dataset` with a broken log creates nothing and consumes no id (next create is `ds-1`), `decide_access_request` with a broken log leaves the request `requested` and mints no grant; service-level: `POST /datasets` over HTTP is not a success and creates nothing |
| `test_lockout.py` | Lockout (AC-7) — fresh server per test: threshold failures are 401s, the next correct-role attempt is 403, locked attempts audited `auth:locked`, unknown users lock too, lockout is per-user, success before the threshold resets the counter, lock expiry (2 failures / 1s) lets the user in again |
| `test_auditor.py` | Auditor role (AC-5) — store level: AUDITOR denied every operational read/write while a steward passes the same gates; service level: dana gets 200 on `/audit` and `/audit/verify`, 403 on `/datasets`, `/search`, `/sources`, `/grants`, `/retention-due`, and `POST /datasets` |

## Adaptations to inherited files (uplift only; nothing else changed)

- `datamgmt_helpers.py` — suite header now names Group 28; added
  `AUDITOR = User("dana", "auditor")` and `dana` in the `USERS`
  registry.
- `test_access.py` — matrix updated for the fourth role:
  `test_roles_exact` includes `auditor`; `test_audit_read_is_admin_only`
  became `test_audit_read_holders` (admin **and** auditor hold
  `audit_read`; steward/viewer do not); one new test,
  `test_auditor_permissions_exact` (auditor = {`audit_read`} exactly);
  `test_permissions_for_matches_matrix`, `test_can_matrix`, and
  `test_require_denies_off_matrix` extended over the auditor row.
- `test_audit.py` — `test_record_roundtrip` key-set assertion now
  includes the chain fields `seq`, `prev_hash`, `hash`.
- `test_main_cli.py` — docstring names the fourth demo user; the
  smoke adds dana on `/audit` (200) and `/datasets` (403).
- All other inherited test files are **byte-identical** to Group
  12's.

## Negative controls

### #1 — Self-approval guard (inherited from Group 12, AC-3/AC-5)

`test_negative_control.py` implements the mutant: a `DataMgmtStore`
subclass (`MutantDataMgmtStore`) whose `_check_decider_not_requester`
is a no-op — the separation-of-duties check is skipped. The traced
claim is that **access decisions are never self-approved** (Datavant
governance claim from the L2 union: data can only be processed by
the right entity, for the right purpose, under the right conditions;
control family AC-3/AC-5). For each canonical case (viewer
requester, steward requester) the test asserts the canonical
expectation (`PermissionDenied` from the real implementation, the
request staying `"requested"`, no grant existing), that the mutant
would NOT produce it (it approves and grants), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as expected fails. The isolation detail from Group 12 stands: the
viewer case presents the requester's own name ("carol") in a role
holding `access_decide`, so the name-based self-decision check is
the only gate that can deny.

Mutation verification: VERIFIED by the coordinator (2026-10-25).
The self-approval guard in `DataMgmtStore._check_decider_not_requester`
(`src/datamgmt/store.py`) was patched to a no-op (`return None`),
the exact live counterpart of the in-suite mutant. The full suite
was run: **239 tests ran, 4 failed** —

- `test_access_governance.TestDecideAccess.test_admin_self_decision_also_denied`
- `test_access_governance.TestDecideAccess.test_self_decision_denied_request_stays_requested_no_grant`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_steward_self_decision_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_viewer_self_decision_denied_canonical_but_mutant_approves`

`store.py` was then restored from the pre-mutation copy in
`scratch/` (SHA-256 `7e4544a450335093a3cde0a04fbd61a1e9380aed8c51b9c744e62d22a476d639`,
verified identical to the pre-mutation hash in `scratch/store.py.sha256`)
and the suite re-run: **239 tests, OK**. The same four tests failed
under the identical drill in Group 12; the guard's coverage survived
the tier uplift unchanged.

### #2 — Audit tamper (new at High, AU-9)

`test_audit_chain.py::TestVerifyChain::test_negative_control_mutated_entry_fails_at_index_1`
mutates a stored audit entry in place on the live implementation
(`log._entries[1]["actor"] = "mallory"`) and asserts
`verify_chain()` reports `(False, 1)` — failure at exactly the
tampered entry's index — after first asserting the untouched chain
verifies `(True, None)`.
`TestHashChainPersistence::test_edited_jsonl_line_fails_verification_after_reload`
performs the same mutation at the file layer (one JSONL line's actor
rewritten on disk) and asserts detection after reload, again at
index 1. The control runs in the suite on every run; no separate
patch drill is needed because the mutation is applied to the real
log state, not to a copy of the logic.
