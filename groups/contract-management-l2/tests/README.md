# Tests — Contract Management L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test docstring names the core
function / spec claim / control family it traces to, per
`../UNION-SPEC.md`.

## Run

```bash
cd groups/contract-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 106 tests
```

Status at delivery: **106 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | Core 18 Access control — exact eleven-action permission matrix (admin all; member all except `org_write`/`audit_read`; viewer reads only), `can()`/`require()` copies, unknown role/action denied |
| `test_organizations_participants.py` | 14 | Core 1 Organizations — pinned shape, duplicate refs rejected with no id consumed, membership boundary (outsider denied), creator-or-admin member management; Core 2 Participants — platform registry, duplicate refs, reads open to any actor, writes gated |
| `test_contracts.py` | 17 | Core 3 Contracts — stored shape pinned (no derived keys in `store._contracts`), **derived-at-read** obligated_cents / period_elapsed, money discipline (bool/float/string/negative rejected), **bounds seam at creation**, period validation, guarded close, cross-org NotFound; Core 4 Modifications — shape, ceiling-inclusive bound, over-ceiling rejected whole with no id consumed, cumulative summation, below-zero floor, closed contracts rejected |
| `test_cases.py` | 13 | Core 5 Requirements — guarded satisfy/waive lifecycle, status filter; Core 6 Protests — exactly-one-link rule, derived overdue flips with the read clock and clears on close, due_at required; Core 7 Data calls — derived overdue, guarded close; Core 8 Risks — no score field in the pinned shape, contract-link filter |
| `test_portal.py` | 13 | Core 10 Opportunities — kinds from the fork's own vocabulary, derived past_close, directed audience requires registered participants; Core 11 Submissions — **guards**: unregistered participant rejected, directed membership is PermissionDenied, closed and past-close opportunities reject; derived awarded; Core 12 Awards — money discipline, **a submission is awarded at most once**, cross-opportunity NotFound |
| `test_records.py` | 9 | Core 9 Communications — pinned shape, **signature pin**: no content parameter exists on `record_communication` and a smuggled `content` kwarg raises TypeError; Core 13 Payments — kinds, positive-integer-cents discipline, link existence/agreement; Core 14 Workflows — **the registry never executes** (no execute-like operation on the store); Core 15 Integrations |
| `test_reports_search.py` | 6 | Core 16 Reporting — pinned report shape (26 keys), counts and cent sums computed on read incl. derived overdue data calls, recursive no-score scan of the report; Core 17 Registry search — refs/titles/kinds match case-insensitively, membership scoping (outsider sees participants only), empty query rejected |
| `test_privacy.py` | 4 | Privacy discipline — **exact key-set pins for all fifteen entity shapes**, derived views add exactly the derived keys, recursive banned-key scan over every stored record + the report, smuggled kwargs raise TypeError on four store methods |
| `test_audit.py` | 6 | Core 18 Audit (AU) — entry shape exactly `{ts, actor, action, target, details}`, all 24 contract mutation action names in order over the canonical flow, failed operations record nothing, store reads record nothing, JSONL persistence + reload, no mutation API |
| `test_specs.py` | 7 | Spec integrity — membership exactly the census unit's two fork IDs (read from `remainder.json`), descriptions byte-equal to the cached `service_desc`, literal claim tables (11 + 14 = 25), 21-family taxonomy union, **every claim's evidence a verbatim substring**, and the checked-absence token pins (no signature / invoice / clause / draft / template / evaluation / scoring / surveillance / AI / API tokens in either description) |
| `test_service.py` | 6 | Service contract — live HTTP on an ephemeral port: `/health` no auth, **401** (unknown user / role mismatch, audited `:denied`), **403** (member creating an organization; outsider reading), **404**, the full flow, the **bounds rule over HTTP** (over-ceiling and float modifications → 400), audit endpoint admin-only with the read itself audited |
| `test_main_cli.py` | 1 | CLI — `python -m contractmgmt serve` subprocess answers `/health` |
| `test_negative_control.py` | 3 | Negative control (below) |
| `contractmgmt_helpers.py` | — | Canonical fixture: organization created by ADMIN (alice) with MEMBER (bob) and VIEWER (carol) as members; MEMBER2 (erin) and OUTSIDER (dave) are platform members outside the fixture organization |
| `smoke.py` | — | Live smoke driver (not a unittest): real server, organization + participant + contract, in-bounds modification, over-ceiling modification rejected 400, opportunity + submission + award, report totals |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is the **modification bounds rule**: a contract's obligated
amount (base award + recorded modifications) must always satisfy
0 ≤ obligated ≤ ceiling, enforced by the store's
`_check_modification_bounds` seam at creation and at every
modification. The mutant is a `ContractMgmtStore` subclass
(`MutantContractMgmtStore`) whose `_check_modification_bounds`
does nothing. The tests assert the canonical expectations (an
over-ceiling base award is rejected at creation; an over-ceiling
modification is rejected whole; a below-zero modification is
rejected), that the mutant accepts all three and records them,
that the mutant's report therefore shows an obligated total above
its ceiling total where the canonical report's never can, and —
via literal `assertRaises(AssertionError)` — that the canonical
expectations reject the mutant's outcomes.

## Mutation verification

VERIFIED in this build session: `_check_modification_bounds` in
the real `src/contractmgmt/store.py` was patched to a no-op body
(`return None  # MUTANT (mutation drill)`) and the full suite was
run against the patched implementation. The mutant source was
syntax-checked (`compile()`) before the recorded run.

- Premutation copy: `tests/store.py.premutation`; its SHA-256 is
  `83c2046df03c3f0affeca39e02d613ee2d65ee1a25bf4ffe0d44c8b69f293811`
  (also recorded in `tests/store.py.sha256`). Raw drill output is
  in `tests/mutation-run.txt`.
- Patched run: **106 ran, exactly 8 failed**:
  - `test_audit.TestAuditLog.test_failed_operations_record_nothing`
  - `test_contracts.TestContracts.test_base_award_above_ceiling_rejected_at_creation`
  - `test_contracts.TestModifications.test_below_zero_modification_rejected`
  - `test_contracts.TestModifications.test_cumulative_mods_checked_together`
  - `test_contracts.TestModifications.test_over_ceiling_modification_rejected_whole`
  - `test_negative_control.TestNegativeControlModificationBounds.test_canonical_expectation_rejects_over_ceiling_modification`
  - `test_negative_control.TestNegativeControlModificationBounds.test_mutant_also_breaks_creation_and_floor`
  - `test_service.TestService.test_full_flow_and_bounds_over_http`
- `store.py` was then restored from `tests/store.py.premutation`
  and verified **SHA-256-identical**
  (`83c2046df03c3f0affeca39e02d613ee2d65ee1a25bf4ffe0d44c8b69f293811`);
  the suite is green again (106/106).

The failing set is exactly the bounds-dependent set: tests that
never violate the bound (e.g. the ceiling-inclusive modification
test) still pass under the mutant, and
`test_mutant_would_not_reject` passes because it exercises the
subclass mutant directly, independent of the real seam — as
expected.

## Live smoke

`PYTHONPATH=src python3 tests/smoke.py` — real server on an
ephemeral port: `GET /health` → 200 `{"status": "ok"}`;
organization `org-1` created (201); participant registered;
contract created (201); modification MOD-1 recorded (201,
obligated 900 of ceiling 1000); **over-ceiling modification →
400** with the ceiling error message; opportunity + submission +
award recorded; report shows `obligated_cents_total=900` and
`award_cents_total=900`. Smoke OK.

## Interpretation notes

- **Organization creation is admin-only by the contract's own
  matrix:** `org_write` is held by admin alone (member is "all
  except `org_write` and `audit_read`"). The canonical fixture
  therefore creates its organization as ADMIN and adds bob/carol
  as members — mirroring how the sibling Legal & Policy build's
  member management runs through its admin.
- **`add_member` carries no separate role action in the
  contract** (the spec names actions for its neighbours but not
  for it); the store enforces exactly what the spec states — the
  membership boundary, then creator-or-admin. The service route
  states the same.
- **The bounds seam's argument convention:** callers pass the
  amounts already obligated as `existing_amounts` — `[]` at
  creation with the base award as the amount under test, and
  `[award_cents] + [existing modification amounts]` at
  modification time. The seam itself is a pure sum-and-compare,
  which is what makes the mutant a one-line body.
- **Submission deadline checks use the store's real clock** (the
  contract gives `record_submission` no `now` parameter, unlike
  the read views); the tests therefore use a far-past
  `closes_at` (2020) for the rejection case and no `closes_at`
  elsewhere, keeping the suite deterministic.
- **Contract lifecycle `status` is stored** (it is a guarded
  transition, not a date derivation); only `obligated_cents` and
  `period_elapsed` are derived — the distinction is deliberate
  and stated in the store's module docstring.
