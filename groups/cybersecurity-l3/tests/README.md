# Tests — Cybersecurity & Risk Management L3-adjacent merged build

236 tests, all passing, standard library only. From the group root:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

Expected: `Ran 236 tests ... OK`.

## Provenance

This suite began as the Cybersecurity L2 parent's 194-test suite and
was carried upward whole, per the cross-tier Merge Rule. Inherited
files are unchanged from `groups/cybersecurity-l2/tests/` **except**:

- `cyber_helpers.py` — adds `AUDITOR = User("dana", "auditor")` and
  `dana` to `USERS_REGISTRY`; header docstring notes the L3 origin.
- `test_access.py` — the role set now has four roles (auditor added);
  adds the auditor's exact-permissions test and the auditor
  audit-read slice; the `audit_read` permission-set assertion names
  admin **and auditor** (in the L2 build only admin held it).
- `test_audit.py` — two exact-key-set assertions now include the
  chain fields `seq` / `prev_hash` / `hash`, with [L3] notes in the
  docstrings. No other inherited assertion changed.

Everything else inherited is byte-identical to the parent suite,
including `test_negative_control.py` and the traceability convention:
every test docstring names the contract it pins — the UNION-SPEC core
function and/or the NIST SP 800-53 control family it traces to — and
HTTP tests drive the real server in-process, exactly as a client
would.

## Layout

| File | Tests | Covers |
|------|------:|--------|
| `cyber_helpers.py` | — | Shared fixtures: users (incl. `AUDITOR`), asset/finding/risk/control payloads, `make_store`, HTTP client |
| `test_access.py` | 20 | Core 10 (AC-2/3/6) + [L3] AC-5 auditor role: closed role/permission table, exact grants per role incl. auditor = `{audit_read}`, default-deny, the admin-only boundary, auditor's audit-read-only reach |
| `test_assets.py` | 21 | Core 1 (CM-8): asset CRUD, validation, labels, decommissioning, id discipline |
| `test_ingest.py` | 25 | Core 2 (RA-5): single/bulk/CSV finding ingestion, atomicity, CVE format, duplicate conflicts |
| `test_lifecycle.py` | 16 | Core 3 (RA-5/IR-4): finding transition maps, terminal states, reopen ban, assignment rules |
| `test_scoring.py` | 14 | Core 4 (RA-3): the severity × criticality table, band edges, `score_finding` purity |
| `test_risks.py` | 21 | Core 5 (RA-3): register CRUD, likelihood × impact scoring, bands, lifecycle |
| `test_controls.py` | 17 | Core 6 (CA-2): the 34-control catalog, family derivation, assessment states |
| `test_search.py` | 16 | Core 7: full-text + faceted search across findings/assets/risks, ranking determinism |
| `test_posture.py` | 7 | Core 8 (CA-7): rollups computed from data, text rendering |
| `test_service.py` | 16 | Core 9 (AC-3/SC-7): HTTP end-to-end — auth failures, error mapping, endpoint matrix |
| `test_main_cli.py` | 1 | CLI subprocess smoke (the `serve` entry point) |
| `test_audit.py` | 17 | Core 11 (AU-2/3/6/12): append-only log, JSONL persistence, per-operation auditing, denied-access entries — key sets updated for the chain fields |
| `test_audit_chain.py` | 15 | [L3] AU-9/AU-3: chain fields, genesis, canonical-hash recomputation, link integrity, verify_chain, JSONL round-trip + edited-line detection, `GET /audit/verify`, auditor HTTP reach (AC-5) |
| `test_audit_failure.py` | 7 | [L3] AU-5: record() fail-closed + rollback, chain intact after failure, store-level rollback (no object, no id consumed, no state move), service-level non-success |
| `test_audit_query.py` | 12 | [L3] AU-7: query() filters (actor/action/target/since/until, inclusive bounds, composition), `GET /audit` parameter pass-through, analyst denied |
| `test_lockout.py` | 6 | [L3] AC-7: lockout at threshold, `auth:locked` auditing, unknown-user lockout, per-user isolation, success resets counter, lock expiry |
| `test_negative_control.py` | 5 | Negative control #1: severity-blind scoring mutant (same failure count as the L2 parent) |
| **Total** | **236** | |

## Negative controls

Two, one inherited and one new at this tier. A suite in which the
negative controls pass proves nothing; both are built to fail loudly
under their mutant/tamper condition.

1. **Severity-blind scoring mutant** (inherited from Group 4) —
   `test_negative_control.py` replaces `score_finding` with a mutant
   that ignores severity, and asserts all-severities-equal scores.
   If someone "simplifies" real scoring the same way, the mutation
   record below shows how much of the suite turns red. Feeds Core 4 /
   RA-3.
2. **Audit-tamper control** [L3] — `test_audit_chain.py` mutates a
   stored audit entry in place (`log._entries[1]["actor"] =
   "mallory"`) and asserts `verify_chain()` reports `(False, 1)`;
   companion cases strip hash fields, break a `prev_hash` link, and
   edit a JSONL line on disk before reload. Feeds Core 11 / AU-9.

## Mutation verification record

Performed on this build (Cybersecurity L3-adjacent), following the
Group 4 procedure:

- Pre-mutation `src/cyber/store.py` SHA-256:
  `1e58d852abd4b06f76c49c1bb2bccd714c23aeacfcbfb597493c8931bd9bcd90`
  (a copy is kept at `scratch/store.py.premutation`).
- Mutation: in `score_finding`, `score = SEVERITY_WEIGHTS[severity] *
  CRITICALITY_WEIGHTS[criticality]` replaced with
  `score = 1 * CRITICALITY_WEIGHTS[criticality]` (severity-blind,
  Group 4's exact mutant).
- Suite under mutation: **236 ran, 30 failed** — the same 30 the
  mutant produces against the parent's core (the uplift tests do not
  depend on scoring values), including both negative-control modules'
  expectations.
- File restored from the pre-mutation copy; SHA-256 verified
  identical to the pre-mutation hash; suite re-run: **236 ran, OK**.

The drill is repeatable: apply the same one-line replacement, rerun,
observe the failures, restore, verify the hash.

## Interpretation notes

- **Atomicity is asserted at store level and over HTTP**, including
  the CSV row-number contract (physical line numbers, header = line
  1) inherited unchanged from Group 4. At this tier atomicity extends
  to the audit write itself (`test_audit_failure.py`): a bulk ingest
  whose audit append fails creates zero findings *and* consumes zero
  ids, so the repaired retry mints `find-1`, `find-2`.
- **Lockout tests use fresh servers per test** (`test_lockout.py`):
  AC-7 state lives on the server instance, so counter leakage between
  tests would be a harness artifact, not behavior. Expiry is tested
  with a real 1-second lock and a 1.2-second wait — the suite's only
  sleep.
- **The audit endpoints count themselves honestly**: `GET /audit` and
  `GET /audit/verify` compute their responses from the trail *before*
  their own `audit_read` entry is appended, and the tests pin that
  ordering rather than working around it.
- **Query tests pin timestamps** (`test_audit_query.py`): `ts` values
  are overwritten after recording to exercise the since/until string
  comparison deterministically. That breaks those entries' hash
  chains *by construction* — chain integrity is asserted in
  `test_audit_chain.py` on unpinned logs, and the two concerns are
  never mixed in one fixture.
- If a test fails, the failing assertion names the behavior — read it
  before reading the implementation; the suite is the contract made
  executable.
