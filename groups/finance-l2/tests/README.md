# Tests — Finance L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/finance-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 213 tests
```

Status at delivery: **213 tests, OK** against the implementation in
`../src/` (202 shipped + 11 from the remainder additions,
`test_additions.py`, tracing to `../ADDENDUM.md`). (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers (UNION-SPEC Core) |
|---|---|
| `test_access.py` | 10 Access control — exact permission matrix for admin/member/viewer (admin all eight actions: read, create_program, enter, decide, record, manage_members, audit_read, admin; member {read, create_program, enter, decide, record}; viewer {read}), `permissions_for()`, `can()`, `require()`, unknown role/action/user denied |
| `test_audit.py` | 11 Audit log — entry keys, append-only, JSONL file + reload on construction, and the store recording each mutation action (`program_create`, `member_add`, `participant_create`, `participant_status`, `accrual_record`, `access_request`, `access_approve`, `access_deny`, `access_void`, `disbursement_record`, `booking_create`, `booking_confirm`, `booking_cancel`, `budget_set`, `wellness_create`, `wellness_enroll`); a failed mutation records no success action |
| `test_programs.py` | 1 Programs & members + 2 Participant registry — program creation shape/provenance, `prog-` id sequence, list visibility, owner-or-admin `add_member`, duplicate add → `ValidationError`, non-member get → `PermissionDenied`, failed ops consume no ids; participants: **the exact pinned key set** `{id, program_id, ref, kind, status, created_by, created_utc}` (the privacy pin: no field can hold a real identifier), duplicate ref in same program → `ValidationError` (same ref in a different program OK), bad kind → `ValidationError`, kind filter, status set + invalid status, cross-program get → `NotFoundError`, non-member/viewer create denied |
| `test_earned_wage.py` | 3 Earned-wage accrual & access records + 8 Workflow & approvals — accrual validation (float/bool/string earned amounts, negative, duplicate (participant, period), accrual for a traveler, bad period); request flow (no accrual → `ValidationError`; float/zero/negative amount; bad date); the derived accrual view with every status present (accessed = approved + disbursed only, pending = requested only, denied/void excluded, available = earned − accessed − pending); the cap: exactly-at-cap OK, 1 cent over rejected whole with nothing stored and no id consumed, two requests summing over the cap → second rejected; decide: creator → `PermissionDenied` (SoD), non-requested → `ValidationError`, non-bool approve → `ValidationError`; disbursement copies amount/participant/period from the request, moves it to `disbursed` with `disbursement_id` set, and is rejected from requested/denied/disbursed states; void from requested and denied OK, from approved → `ValidationError`, unrelated member / non-member void → `PermissionDenied` |
| `test_bookings.py` | 4 Travel booking records — creation shape/validation (bad kind, employee participant → `ValidationError`, end before start, same-day OK, float/negative amount, zero amount OK), lifecycle recorded → confirmed → cancelled, confirm/cancel of a cancelled booking → `ValidationError`, list filters including unknown status/kind values → `ValidationError` |
| `test_budgets.py` | 5 Spend budgets & tracking — `set_budget` shape + total, replace semantics (same id, `created_utc` kept, lines replaced, no new id), duplicate category and malformed lines → `ValidationError`, `get_budget` missing period → `NotFoundError`; `spend_vs_budget` math (bookings counted by kind in their start month, recorded/confirmed only — cancelled excluded; disbursements counted under `earned_wage` in their disbursement month; variance = limit − spent; over-budget flag; unbudgeted categories listed sorted; totals consistent) |
| `test_wellness.py` | 6 Financial wellness offering registry — all five kinds accepted, bad kind / empty title → `ValidationError`, enrollment shape (`enr-` id, `enrolled`), duplicate enrollment → `ValidationError` with no id consumed, cross-program offering/participant → `NotFoundError`, enrollment list filtered by offering |
| `test_reports.py` | 7 Reporting — one coherent scenario (2 employees + 1 traveler; earned 150000¢; one approved+disbursed request 20000¢; one pending 10000¢; one denied excluded everywhere; air {count 1, 30000¢} and hotel {count 1, 25000¢} with a cancelled air booking excluded; 2 wellness enrollments) asserting the summary's fields exactly, a second period asserting other-period records land there instead, bad period → `ValidationError`, and an empty period returning zeros with both booking kinds present |
| `test_service.py` | 9 API access + 10 Access control + 11 Audit log — live HTTP server on an ephemeral port: `/health` without auth, 401 unknown user and role mismatch, 404 as JSON with no stack trace, full flow (create program → participants → accrual → request → approve by another user → disbursement → booking → budget → vs-actual → summary), SoD over HTTP (creator approve → 403, request still `requested`), over-cap request over HTTP → 400 with no request created, summary without period → 400, audit endpoint admin-only (member/viewer → 403) and denied attempts recorded with the `:denied` suffix |
| `test_main_cli.py` | `python -m finance serve` subprocess with demo users alice/bob/carol on an ephemeral port |
| `test_negative_control.py` | Negative control (below) |
| `test_additions.py` | Remainder additions (`addition:finance-l2`, `../ADDENDUM.md`) — spec integrity for the 4 added forks (membership/unit order against `../../remainder.json`, literal per-fork claim table incl. the three zero-claim forks, verbatim evidence, census citations, Coupa evidence re-anchor, near-miss pins), one substrate case per addition fork, and the earned-cap invariant re-pinned over addition-era records |
| `finance_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `make_store()` building a FinanceStore + AuditLog + a program owned by MEMBER with VIEWER added as member, and the canonical builders (`make_employee`, `make_traveler`, `make_accrual`, `make_request`, `approved_request`, `disbursed_request`, `make_booking`) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a cap check that sums the period's committed amount and the requested
amount but **never compares the total against the period's earned
amount**, treating every request as within cap. The traced claim,
named in the module's docstrings, is that the earned-cap invariant —
pending plus approved plus disbursed amounts for a (participant,
period) never exceed that period's earned amount — is the SI-10 /
Core 3 integrity boundary of the earned-wage records. For each
canonical case — (a) a single request one cent over the period's
earned amount and (b) two requests each within the earned amount
whose sum exceeds it (the second request is the case) — the test
asserts three things: the canonical expectation (`ValidationError`
from the real store, with nothing stored and no request id consumed),
that the mutant gate would NOT raise (it waves the over-cap request
through as "within cap"), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails. Case (c) is the control sanity check:
a request exactly at the cap passes both the real store and the
mutant.

## Mutation verification

VERIFIED by the coordinator (2026-10-25). The cap check in
`_check_access_cap` (`src/finance/store.py`) was patched from
`if committed_cents + amount_cents > earned_cents: raise
ValidationError(...)` to a body that computes the sum into a local
and returns `True` unconditionally — the exact live counterpart of
the mutant in `test_negative_control.py` — and the full suite was
run: **202 tests ran, 5 failed**. The failures are exactly the defect
class's surface: `test_earned_wage`'s one-cent-over-cap rejection and
two-requests-summing-over-cap rejection, both negative-control
canonical cases, and `test_service`'s over-cap-request-over-HTTP
case (the mutant returned 201 where the contract requires 400).
`store.py` was then restored from a pre-mutation copy (SHA-256
verified identical to the pre-mutation hash,
`f905061dbe5d45ae3ef64333a1a62a1f05af8fadbf0e5d01608cd6ad643f7c9e`,
kept at `../scratch/store.py.premutation` with its hash at
`../scratch/store.py.sha256`) and the suite re-run: **202 tests,
OK**. The suite catches this defect class; the negative control is
not decorative.

**Additions re-run (2026-10-31, `addition:finance-l2`):** the core
is unchanged, so the same drill was re-run in this tree with the
identical mutant. The full suite ran: **213 tests, 6 failures** —
the shipped drill's 5, plus
`test_additions.TestAdditionSubstrateCases.test_additions_earned_cap_still_enforced`,
the additions module's cap case, tripping exactly as designed.
`store.py` was restored from the pre-mutation copy and verified
SHA-256-identical to the same shipped hash; the suite re-ran green
at 213. Raw failure list in `../scratch/additions_mutation_run.txt`.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite stays
tolerant of the remaining freedom:

- `list_accruals` is specified to return accrual views; the suite
  pins ids, order, and the participant filter on the list, and pins
  exact derived fields on `get_accrual` (checked as the record keys
  plus the three derived keys), so a record-only list shape would
  still pass.
- `permissions_for()` for an unknown role is accepted as either an
  empty permission set or a denying raise; `can()` for an unknown
  role likewise. `require()` for an unknown role must deny.
- Store-level role enforcement is tested with `User` actors only.
  Per the contract, a plain-string actor carries identity but no
  role, so role enforcement for string actors belongs to the service
  layer and is not asserted against the store.
- `spend_vs_budget` attributes disbursement spending to the month
  of the disbursement's own `date` (the contract's literal wording:
  "whose `date` falls in the period"), which the suite pins with a
  dedicated cross-month case; `program_summary` attributes wage
  totals by the access request's period and disbursements by their
  date, per the contract.

## Final GAPS batch — extension coverage (added 2026-11-07)

| File | Covers |
|---|---|
| `test_gaps_batch.py` | The extension surface in `src/finance/extensions.py` (`FinanceExtensions` over the core store) — one class per open GAPS.md entry for this group (see `../BATCH.md` for dispositions): disbursement execution **request** records capped by the earned cap (the cap reads the core accrual view's derived `available_cents`, so core pending/accessed totals bind this surface; a `reported_failed` report releases the cap, a `reported_paid` report does not) plus verbatim rail outcome reports (`paid_here: False` throughout; a request plus a report leaves core disbursements, access requests, and the accrual view untouched); booking execution requests against existing core bookings plus verbatim reports (the core booking stays byte-identical, still `recorded`); wellness session records over core enrollments plus verbatim reports; loan application records plus verbatim reported decisions (the application record is byte-identical after a decision report; the registry is not capped by earned wages because it disburses nothing; a recursive key scan pins that no record carries a credit score field); trade order records plus verbatim reports; tax preparation records (zero amount OK) plus verbatim filing reports; GRC framework/control records and mappings to existing core records with posture counts derived at read (no derived key on any stored record); the three stubs as labeled reference records — reporting streams + receipts (`reference_stub` / `reference_transport`, counts as reported, core summary untouched), banking verification requests/reports pinned to their **exact key sets** with a recursive scan proving no field can hold an account identifier (the core participant's pinned 7-key shape re-asserted after the flow), and payroll sync receipts pinned to an exact key set holding **no `*_cents` field at all** (counts as reported; a sync creates no accrual and changes no recorded amount). Cross-cutting: `ext_` actions and `:denied` denials on the core audit log, viewer write denied, non-member denied by the core membership boundary, platform-admin reach, cross-program records invisible, an audit-write failure rolls the record and its id back, and a recursive forbidden-key scan (`score`, `account`, `routing`, `iban`, `sort_code`, `card_number`) across one record of every extension kind. Plus negative control #2 (below). |

Suite status with the batch: **267 tests** (213 at delivery + 54 in
`test_gaps_batch.py`), all passing.

## Negative control #2 — disbursement execution cap (batch, 2026-11-07)

`test_gaps_batch.py::TestDisbursementCapNegativeControl` implements
the mutant for the extension surface's own cap seam: a check that
sums the outstanding committed amount and the requested amount but
**never compares the total against the accrual's available amount**,
treating every request as within cap. The traced claim is that the
earned-cap invariant — the SI-10 / Core 3 integrity boundary of
earned-wage access — binds this surface's disbursement execution
requests exactly as it binds core access requests: outstanding
requested amounts for a (participant, period) never exceed the
accrual view's derived `available_cents`. For each canonical case —
(a) a single request one cent over the available amount and (b) two
requests each within the available amount whose sum exceeds it (the
second request is the case) — the test asserts the canonical
expectation (`ValidationError` from the real surface, with nothing
stored and no id consumed), that the mutant gate would NOT raise,
and — via a literal `assertRaises(AssertionError)` — that treating
the mutant's outcome as the expected outcome fails. Case (c) is the
control sanity check: a request exactly at the cap passes both the
real surface and the mutant.

Mutation verification: VERIFIED by the coordinator (2026-11-07).
The cap check in `_check_disbursement_cap`
(`src/finance/extensions.py`) was patched to compute the
committed-plus-requested sum into a local and return `True`
unconditionally — the exact live counterpart of the mutant in the
test module — and the full suite was run: **267 tests ran, exactly
4 failed**:

- `test_gaps_batch.TestDisbursementCapNegativeControl.test_single_request_one_cent_over_available`
- `test_gaps_batch.TestDisbursementCapNegativeControl.test_two_requests_each_within_available_whose_sum_exceeds_it`
- `test_gaps_batch.TestDisbursementExecution.test_core_pending_consumes_available`
- `test_gaps_batch.TestDisbursementExecution.test_failed_report_releases_cap_paid_report_does_not`

Mutant output is saved at `scratch/batch-mutation-output.txt`.
`extensions.py` was then restored from
`scratch/extensions.py.premutation` and verified byte-identical
(SHA-256
`e9bf7bbc2d552d3f242f5274d415bb01631e2450c3c1c6d24d96e2c1e7370d7e`,
recorded in `scratch/extensions.py.sha256`) and the suite re-run:
**267 tests, OK**. An oracle that passes with the cap comparison
removed would be testing that code ran, not that the earned cap
binds disbursement execution requests — this control is the filter
against that. (Negative control #1, the core `_check_access_cap`
drill, is unchanged above; its seam is in the byte-identical core
and was not touched.)

## Final GAPS batch — remainder addition coverage (added 2026-11-07)

`tests/test_gaps_batch_addition.py` (41 tests) pins the second
batch unit's surface, `src/finance/extensions_addition.py`
(`FinanceExtensionsAddition`, audited under the `exta_` prefix):
ledger account and journal entry records with balances and the
trial balance derived at read and never stored; the procurement
lifecycle as one record kind per stage, with the contract's
recorded ceiling bounding its orders and supplier payment
outcomes recorded verbatim in this family; the spend-analytics
view pinned to counts and recorded-cent sums (no rate, trend,
forecast, average, or grand-total key can exist in its shape);
FinOps allocation/tagging records with savings figures stored as
reported; trust accounts, transactions, and custodian-reported
positions with balances derived by recorded arithmetic, no
cross-currency sums, and no execution surface of any kind; and
the document-processing reference stub's labels. Cross-cutting
pins cover exact key sets for every new record kind (an
exact-key recursive scan: no account-number, routing, IBAN,
sort-code, card-number, bank-account, or score key anywhere),
the integer-cents boundary (a rejected amount consumes no id),
denied writes audited as `exta_*:denied`, outsider denial,
platform-admin reach, cross-program invisibility, and
audit-failure rollback of record and id.

Suite status with the addition: **308 tests** (267 at the first
batch unit + 41 here), all passing.

## Negative control #3 — ledger derivation (batch addition, 2026-11-07)

Records for this unit: `AccountTotalsNegativeControl` in
`tests/test_gaps_batch_addition.py`, targeting the derivation
seam of the Momentum records surface — `_account_totals` in
`src/finance/extensions_addition.py`, through which every ledger
balance and the trial balance are derived at read. Canonical
scenario: three journal entries (debit glac-1/credit glac-2
10000; debit glac-1/credit glac-3 5000; debit glac-2/credit
glac-1 2000) give glac-1 totals (15000 debits, 2000 credits) and
balance 13000. The mutant under control adds the credit side to
the debit total instead of netting it, silently corrupting every
derived balance while leaving every stored record's shape
intact. The test class carries the canonical expectation on the
real seam, the canonical/mutant divergence, a literal
`assertRaises(AssertionError)` leg treating the mutant balance
as canonical, and an only-debits sanity case where canonical and
mutant agree.

Mutation verification: VERIFIED by the coordinator (2026-11-07).
The real seam was patched by the exact one-line change
(`credit_total += entry["amount_cents"]` →
`debit_total += entry["amount_cents"]`, the live counterpart of
the test mutant) and the full suite was run: **308 tests ran,
exactly 4 failed**:

- `test_gaps_batch_addition.AccountTotalsNegativeControl.test_canonical_expectation_holds`
- `test_gaps_batch_addition.AccountTotalsNegativeControl.test_mutant_totals_differ_from_canonical`
- `test_gaps_batch_addition.MomentumSystemOfRecord.test_account_balances_derived_at_read_never_stored`
- `test_gaps_batch_addition.MomentumSystemOfRecord.test_trial_balance_derives_balanced_totals`

`extensions_addition.py` was then restored from
`scratch/extensions_addition.py.premutation` and verified
byte-identical (SHA-256
`cccf59bb1c3484aa2c815debffd9c9d94297a0df09c9da83627a76cbcf8e76de`,
recorded in `scratch/extensions_addition.py.sha256`) and the
suite re-run: **308 tests, OK**. An oracle that passes with the
credit side netted the wrong way would be testing that code ran,
not that a ledger balance is debits minus credits — this control
is the filter against that. (Negative controls #1 and #2 are
unchanged above; their seams are in the byte-identical core and
the first unit's byte-identical `extensions.py`.)
