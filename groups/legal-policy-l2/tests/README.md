# Tests — Legal & Policy L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test docstring names the core
function / spec claim / control family it traces to, per
`../UNION-SPEC.md`.

## Run

```bash
cd groups/legal-policy-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 94 tests
```

Status at delivery: **94 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | Core 13 Access control — exact eleven-action permission matrix (admin all; member all except `agency_write`/`audit_read`; viewer reads only), `can()`/`require()`, unknown role/action denied |
| `test_agencies_workspaces.py` | 15 | Core 1 Agencies — pinned shape, duplicate refs rejected with no id consumed, membership boundary (non-member non-admin denied), creator-or-admin member management; Core 2 Workspaces — per-agency ref uniqueness, cross-agency ids read as NotFound, viewer cannot write |
| `test_sessions_executions.py` | 14 | Core 3 Sessions — stored shape pinned, validation (non-bool sandbox, bad `expires_at`), **derived-at-read**: raw stored record (`store._sessions`) carries no `expired`/`sandbox_consumed`, views derive both (expired flips with the `now` clock, consumed flips after an execution), guarded close; Core 4 Executions — kind/ref validation, **single-use rule** (second sandbox execution → ValidationError, no id consumed, store unchanged), non-sandbox multiple executions, closed sessions rejected |
| `test_library_searches.py` | 11 | Core 5 Library — kinds, library-wide ref uniqueness, reads open to any actor / writes gated; Core 6 Saved searches — digest validation (exactly 64 lowercase hex), result-count discipline, **signature pin**: `save_search` parameters are exactly the contract's and a smuggled `query_text` raises TypeError |
| `test_documents.py` | 10 | Core 7 Documents — lowercase-hex checksum validation, size/kind discipline, per-workspace ref uniqueness, session link must be in the workspace; Core 8 Verify-by-content (SI-7) — exact bytes match, altered bytes do not, str-as-UTF-8, stores nothing |
| `test_usage_exports.py` | 9 | Core 9 Usage — **quantity discipline** (bool/float/string/zero/negative all rejected), kinds, ref uniqueness, link checks; Core 10 Exports — manifest shape, **checksum recomputed independently in the test** from the usage records and matched, empty-set checksum, **window filtering** on `[since, until]` inclusive, export permissions |
| `test_reports_search.py` | 7 | Core 11 Reporting — pinned report shape, counts/sums computed on read, derived sandbox-consumed count; Core 12 Registry search — refs/titles/labels/kinds match case-insensitively, membership scoping (outsider sees library only), digests never matched, empty query rejected |
| `test_privacy.py` | 4 | Privacy discipline — **exact key-set pins for every entity shape** (agency, workspace, session stored + derived view, execution, library source, search, document, usage, export, report, verify), no person/content/score field anywhere, smuggled kwargs raise TypeError on six store methods, query text appears nowhere in the stored search record |
| `test_audit.py` | 7 | Core 13 Audit (AU) — entry shape exactly `{ts, actor, action, target, details}`, all twelve contract mutation action names in order, failed operations record nothing, store reads record nothing, JSONL persistence + reload, no mutation API |
| `test_service.py` | 6 | Service contract — live HTTP on an ephemeral port: `/health` no auth, **401** (unknown user / role mismatch, audited `:denied`), **403** (member creating an agency; viewer writing; outsider reading), **400** (validation; second sandbox execution; bad base64; float quantity), **404**, the full flow, the **query_text hashing path** (response and `store._searches` hold `sha256(text)`; the text appears nowhere in the record), audit endpoint admin-only with the read itself audited |
| `test_main_cli.py` | 1 | CLI — `python -m legalpol serve` subprocess answers `/health` |
| `test_negative_control.py` | 3 | Negative control (below) |
| `legalpol_helpers.py` | — | Canonical fixture: agency created by ADMIN (alice) with MEMBER (bob) and VIEWER (carol) as members; MEMBER2 (erin) and OUTSIDER (dave) are platform members outside the fixture agency |
| `smoke.py` | — | Live smoke driver (not a unittest): real server, agency + workspace + sandbox session, two executions, second rejected 400 |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is the **single-use rule**: a sandbox session accepts exactly one
execution record, enforced by the store's `_check_sandbox_unused`
seam. The mutant is a `LegalPolStore` subclass
(`MutantLegalPolStore`) whose `_check_sandbox_unused` does nothing.
The tests assert the canonical expectation (a second execution is
rejected whole), that the mutant accepts the second execution and
records two, that the mutant's report therefore counts two
executions where the canonical report counts one, and — via literal
`assertRaises(AssertionError)` — that the canonical expectations
reject the mutant's outcomes.

## Mutation verification

VERIFIED in this build session: `_check_sandbox_unused` in the real
`src/legalpol/store.py` was patched to a no-op body
(`return None  # MUTANT (mutation drill)`) and the full suite was
run against the patched implementation.

- Premutation copy: `tests/store.py.premutation`; its SHA-256 is
  `7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`
  (also recorded in `tests/store.py.sha256`). Raw drill output is
  in `tests/mutation-run.txt`.
- Patched run: **94 ran, exactly 4 failed**:
  - `test_negative_control.TestNegativeControlSandboxSingleUse.test_canonical_expectation_rejects_second_execution`
  - `test_negative_control.TestNegativeControlSandboxSingleUse.test_mutant_also_breaks_derived_consumption_semantics`
  - `test_sessions_executions.TestExecutions.test_single_use_rule`
  - `test_service.TestFullFlow.test_flow`
- `store.py` was then restored from `tests/store.py.premutation`
  and verified **SHA-256-identical**
  (`7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`);
  the suite is green again (94/94).

The failing set is exactly the single-use-dependent set: the
derived-consumption tests that only exercise a *first* execution
still pass under the mutant (consumption flips correctly either
way), and `test_mutant_would_not_reject` passes because it exercises
the subclass mutant directly, independent of the real seam — as
expected.

## Live smoke

`PYTHONPATH=src python3 tests/smoke.py` — real server on an
ephemeral port (observed: 39809): `GET /health` → 200
`{"status": "ok"}`; agency `agy-1` created (201); bob added (200);
workspace `wsp-1` (201); sandbox session `ses-1` (201); first
execution 201; **second execution → 400** with the single-use
error message. Smoke OK.

## Interpretation notes

- **Agency creation is admin-only by the contract's own matrix:**
  `agency_write` is held by admin alone (member is "all except
  `agency_write` and `audit_read`"). The canonical fixture
  therefore creates its agency as ADMIN and adds bob/carol as
  members — mirroring how the sibling Grant Management build's
  member management runs through its admin.
- **`add_member` carries no separate role action in the contract**
  (the spec names actions for its neighbours but not for it); the
  store enforces exactly what the spec states — the membership
  boundary, then creator-or-admin. The service route states the
  same.
- **Session derived views:** `expired` uses strict inequality (the
  read clock is *past* `expires_at`); `sandbox_consumed` is true
  only for sandbox sessions with an execution recorded.
  `create_session` returns the stored shape (per the service
  contract), `get_session` / `list_sessions` return derived views.
- **Export checksum canonicalization** (the contract says "SHA-256
  of the canonical JSON (sorted keys, records sorted by id) of
  `{id, kind, quantity, created_utc}`"): records are sorted by
  numeric id, serialized with `json.dumps(..., sort_keys=True,
  separators=(",", ":"))`, UTF-8 encoded. The usage-exports tests
  recompute the checksum independently from the usage records
  using the same stated canonicalization and compare.
- **Session lifecycle `status` is stored** (it is a guarded
  transition, not a date derivation); only `expired` and
  `sandbox_consumed` are derived — the distinction is deliberate
  and stated in the store's module docstring.
