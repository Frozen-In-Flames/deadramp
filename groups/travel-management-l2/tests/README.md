# Tests — Travel Management L2 (Group 55)

```bash
cd groups/travel-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 96 tests
```

**96 tests, all passing.** Python standard library only.

## Coverage map

| File | Covers |
|---|---|
| test_access.py | Role/permission matrix (AC-2/AC-3 hooks): admin all actions, member enter/decide/record, viewer read-only, unknown roles and None users denied |
| test_organizations.py | Organization registry, creator membership, membership boundary (outsider reads denied, outsider sees no organizations), member administration restricted to manage_members |
| test_travelers.py | Traveler registry: record shape pinned to exactly 6 keys, no field can hold personal data, role and membership enforcement |
| test_authorizations.py | Authorization lifecycle (draft → submitted → approved/declined), decider-never-requester (AC-5), return-before-depart and non-integer money rejected, trip phase derivation (upcoming / in_progress / completed) and the stored record carrying no derived keys |
| test_expenses.py | Expense reports and line items: approval presupposition, draft-only items, derived totals never stored, report decisions under SoD, and the authorization cap at submission (up to cap submits; one report over the committed cap is rejected and stays draft; drafts do not commit cap) |
| test_vouchers.py | The signature invariant: partial vouchers, vouchers to exactly the report total, one cent over rejected, rejection changes nothing, float/zero rejected, approved-report presupposition |
| test_notifications.py | Notification records: kinds, role enforcement, records-only shape (no delivery fields exist) |
| test_integrations.py | Integration registry: definitions as data, and the registry never executes (no execute/invoke path exists on the store; definitions carry no execution state) |
| test_reporting.py | Search (traveler, destination, report title), per-organization summary counts and money sums, authorization view aggregates, and a recursive scan proving no score/rating/risk key exists on any view |
| test_audit.py | Append-only audit: mutations recorded, entry shape, no mutation API, defensive copies, JSONL persistence round trip |
| test_service.py | Live HTTP: health, 401 on missing/mismatched identity headers, the full flow (org → members → traveler → authorization → submit → creator decide 403 → decider approve → report → items → viewer read with derived total → submit → decide → voucher to total → one cent over = 400 → summary), viewer voucher attempt = 403 with a `:denied` audit entry, audit read restricted to admin, 404s |
| test_negative_control.py | The mutation-verified negative control for the voucher cap (below) |
| test_main_cli.py | CLI parser defaults (port 8799), demo user registry, TLS flag pairing |

## Negative control — mutation-verified

Signature invariant: cumulative vouchers against an expense report
never exceed the report's total, enforced at
`TravelStore._check_voucher_cap`.

- **In-suite:** `test_negative_control.py` subclasses the store with
  `_check_voucher_cap` as a no-op. The canonical store rejects the
  over-cap voucher; the mutant accepts the identical voucher and the
  report's derived remaining balance goes to −1, proving the seam is
  what enforces the cap.
- **External drill (performed on the real tree):** the cap condition
  in `src/travel/store.py` was patched to `if False:` and the full
  suite run: **96 ran, exactly 5 failures**, every one a voucher-cap
  assertion —
  1. test_negative_control canonical rejection
  2. test_service full flow (the one-cent-over HTTP voucher)
  3. test_vouchers rejected-voucher-changes-nothing
  4. test_vouchers single voucher over total
  5. test_vouchers one cent over total

  Raw output in `scratch/mutation-run.txt`. The store was then
  restored from `scratch/store.py.premutation` and verified
  **SHA-256-identical** (`a4098ea6…`, recorded in
  `scratch/store.py.sha256`); the suite is green again.

## Interpretation notes

- The requester of record for separation of duties is the record's
  creator (`created_by`); a decision by any other organization
  member with the `decide` action is accepted.
- Creation calls return the stored record shape; reads return views
  that add derived keys (phase, totals). Tests pin both sides of
  that line.
