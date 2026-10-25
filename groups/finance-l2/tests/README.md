# Tests — Finance L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/finance-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 202 tests
```

Status at delivery: **202 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
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
