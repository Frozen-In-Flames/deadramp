# Tests — Travel Management, untiered set (Untiered Set 28)

```bash
cd groups/travel-management-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 107 tests
```

**107 tests, all passing** (96 carried founding core tests + 11
new spec tests for this set, see below). Python standard library
only.

The carried suite is the founding Travel Management L2 group's
suite, carried with the code (`src/travel/` is byte-identical to
the founding build, 7 of 7 modules — SHA-256 accounting in the
group README). The founding suite's `test_additions.py` was NOT
carried: it pins a different census unit
(`addition:travel-management-l2`). No carried test file needed a
labeling change — none names the founding tier. Helpers are
imported as a top-level module from the tests directory and
`tests/__init__.py` is empty by design, so package-mode discovery
with `-t .` is not the supported entry point for this group.

## Coverage map

| File | Covers |
|---|---|
| test_access.py | Role/permission matrix hooks: admin all actions, member enter/decide/record, viewer read-only, unknown roles and None users denied |
| test_organizations.py | Organization registry, creator membership, membership boundary (outsider reads denied, outsider sees no organizations), member administration restricted to manage_members |
| test_travelers.py | Traveler registry: record shape pinned to exactly 6 keys, no field can hold personal data, role and membership enforcement |
| test_authorizations.py | Authorization lifecycle (draft → submitted → approved/declined), decider-never-requester, return-before-depart and non-integer money rejected, trip phase derivation (upcoming / in_progress / completed) and the stored record carrying no derived keys |
| test_expenses.py | Expense reports and line items: approval presupposition, draft-only items, derived totals never stored, report decisions under SoD, and the authorization cap at submission (up to cap submits; one report over the committed cap is rejected and stays draft; drafts do not commit cap) |
| test_vouchers.py | The signature invariant: partial vouchers, vouchers to exactly the report total, one cent over rejected, rejection changes nothing, float/zero rejected, approved-report presupposition |
| test_notifications.py | Notification records: kinds, role enforcement, records-only shape (no delivery fields exist) |
| test_integrations.py | Integration registry: definitions as data, and the registry never executes (no execute/invoke path exists on the store; definitions carry no execution state) |
| test_reporting.py | Search (traveler, destination, report title), per-organization summary counts and money sums, authorization view aggregates, and a recursive scan proving no score/rating/risk key exists on any view |
| test_audit.py | Append-only audit: mutations recorded, entry shape, no mutation API, defensive copies, JSONL persistence round trip |
| test_service.py | Live HTTP: health, 401 on missing/mismatched identity headers, the full flow (org → members → traveler → authorization → submit → creator decide 403 → decider approve → report → items → viewer read with derived total → submit → decide → voucher to total → one cent over = 400 → summary), viewer voucher attempt = 403 with a `:denied` audit entry, audit read restricted to admin, 404s |
| test_negative_control.py | The mutation-verified negative control for the voucher cap (below) |
| test_main_cli.py | CLI parser defaults (port 8799), demo user registry, TLS flag pairing |
| test_specs.py | This untiered set's spec integrity (below) |
| travel_helpers.py | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), DECIDER=dana/member (an organization member who decides records bob created) |

## Spec tests (this set)

`test_specs.py` (11 tests) pins the untiered fork (Cornerstone
Information Systems / Upstream Gov, `FR2632558740`): sheet count
and unit order, membership against `remainder.json` with the
unit's tier null, TIER DISCIPLINE (the sheet's `cmmc_tier` is
None and its `fedramp_impact_level` is `"Unknown"` — no tier is
invented, and the founding group's Moderate baseline is not
inherited), the literal 0-claim table with the zero-claim set
exactly {FR2632558740} and the whole-taxonomy zero set (all 9
families), the description verbatim against the cached source
(both duplicate records), the sheet's category, census citation
accounting (1 citation: verifies verbatim, serves as evidence
for nothing — verification is not a claim), the
no-exclusion-trap pin (the cached record's `certified_services`
is empty), the founding build's five checked absences re-searched
at the token level on THIS fork's words (booking, per-diem,
reimbursement, approval, receipt — all survive), the near-miss
pins ("reporting"/"analysis"/"aggregation" present; "reporting
services" and the other suite-list phrases absent), and the
no-control-language pin (the ground for the union spec's
Documented control claims section listing every family as not
documented).

## Negative control — mutation-verified

Signature invariant: cumulative vouchers against an expense
report never exceed the report's total, enforced at
`TravelStore._check_voucher_cap`.

- **In-suite:** `test_negative_control.py` subclasses the store
  with `_check_voucher_cap` as a no-op. The canonical store
  rejects the over-cap voucher; the mutant accepts the identical
  voucher and the report's derived remaining balance goes to −1,
  proving the seam is what enforces the cap.
- **External drill (re-run in THIS tree, 2026-10-31):** the core
  is unchanged, so the founding group's signature drill was
  re-run here. The cap condition in `src/travel/store.py`
  (`if already + amount_cents > total:`, occurring exactly once,
  count asserted) was patched to `if False:` and the full suite
  run: **107 ran, exactly 5 failures** — the founding shipped
  drill's identical set, every one a voucher-cap assertion, and
  no spec test tripped:
  1. `test_negative_control.TestVoucherCapNegativeControl.test_canonical_store_rejects_over_cap_voucher`
  2. `test_service.TestService.test_full_flow`
  3. `test_vouchers.TestVouchers.test_rejected_voucher_changes_nothing`
  4. `test_vouchers.TestVouchers.test_single_voucher_over_total_rejected`
  5. `test_vouchers.TestVouchers.test_voucher_one_cent_over_total_rejected`

  Raw output in `scratch/mutation_run.txt`. `store.py` was then
  restored from `scratch/store.py.premutation` and verified
  **SHA-256-identical** to the founding shipped hash
  (`a4098ea612bbffa7fed89323e39752c79f28e08ce1e343f3ece92d5517da61ce`,
  recorded in `scratch/store.py.sha256`); the suite re-ran green
  at 107.

## Interpretation notes

- The requester of record for separation of duties is the
  record's creator (`created_by`); a decision by any other
  organization member with the `decide` action is accepted.
- Creation calls return the stored record shape; reads return
  views that add derived keys (phase, totals). Tests pin both
  sides of that line.
- Tier note: the carried tests exercise the substrate's hooks
  (role matrix, membership, audit) as **baseline-neutral**
  substrate. Nothing in this tree asserts the founding group's
  Moderate baseline or any CMMC tier; the set's tier is null and
  the sheets pin it.
