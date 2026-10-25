# Finance L2 — merged build (Operation DeadRamp, Phase 2, Group 31)

This is the merged, clean-room implementation of the **Finance L2**
sibling group: **2 forks** from the FedRAMP Marketplace that share
the same function (Finance) and the same trust tier (CMMC L2,
equivalent to FedRAMP Moderate), built as one open-source service
per the group's union spec, [`UNION-SPEC.md`](UNION-SPEC.md).

It was written from the contract in that spec only: original code,
no vendor code, assets, or branding from either sibling offering.
Python 3, **standard library only**, no external dependencies.

The two siblings share **zero claimed function families** — the
honest headline of this group. One is an earned-wage-access platform
(on-demand pay plus financial wellness); the other is a group-travel
platform for meetings (booking, spend, real-time reporting). What
merges is the substrate both presuppose: programs with members,
participants known only by opaque references, integer-cent financial
records with approval workflow, budgets with spend tracking,
reporting computed from records, role-based access, and an
append-only audit trail. Neither sibling's domain bleeds into the
other's half of the union, and the spec says so plainly.

## The 11 core functions

1. **Programs & members** — named programs (one employer or agency
   finance program) with an owner, a member list, and provenance.
   Membership is the boundary every other core function enforces.
2. **Participant & traveler registry (opaque references)** —
   participants known only by a caller-supplied opaque `ref` and a
   kind (`employee` or `traveler`), with an active/inactive status.
   The record shape is pinned by tests: no field can hold a real
   name, bank account number, or government identifier.
3. **Earned-wage accrual & access records** — per participant per
   pay period, an accrual records wages already earned. Access
   requests draw against a period's accrual under the **earned-cap
   invariant** (pending + approved + disbursed never exceed
   earned), run the approval machine with separation of duties, and
   an approved amount can gain a disbursement record — a record,
   after the fact, that money moved on external rails. This build
   moves no money.
4. **Travel booking records** — booking records (air or hotel, date
   range, amount in cents) with a `recorded → confirmed /
   cancelled` lifecycle. Records of reservations made elsewhere;
   the build books nothing.
5. **Spend budgets & tracking** — a budget per program per period
   (planned cents per category); **spend-vs-budget** computes spent
   amounts from records (non-cancelled bookings by kind, disbursed
   wage access under `earned_wage`), variance, and over-budget
   flags — computed, never asserted.
6. **Financial wellness offering registry** — wellness offerings
   (education, coaching, budgeting, savings, counseling) per
   program, with participant enrollment records. The wellness
   tools themselves are Extended (see `UNION-SPEC.md`).
7. **Reporting** — a per-period program summary computed on read
   from records only: participant count; earned / accessed /
   disbursed / pending wage totals; booking counts and totals by
   kind; wellness enrollment count.
8. **Workflow & approvals** — the access-request state machine
   (`requested → approved / denied`, `approved → disbursed` via a
   disbursement record, `requested / denied → void`), with
   **separation of duties**: the decider of a request is never its
   creator.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with program membership
    (non-members cannot read or write a program's content; the
    platform `admin` role can).
11. **Audit log** — an append-only audit trail: every program,
    membership, participant, accrual, access-request, disbursement,
    booking, budget, and wellness mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence.

**Money is integer cents, everywhere; records are not execution.**
Every amount field is `*_cents` and must be an integer — booleans
and floats are rejected at the boundary, even integral floats — so
all arithmetic is exact by construction. Payments, transfers, and
disbursements are recorded, never executed against real rails.
Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `prog-`, `part-`,
`acc-`, `req-`, `dis-`, `bkg-`, `bud-`, `wel-`, `enr-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m finance serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, create_program, enter, decide, record, manage_members, audit_read, admin |
| `bob`   | member  | read, create_program, enter, decide, record |
| `carol` | viewer  | read |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |
| GET | `/programs` | read | List programs visible to the caller → `{"programs": [...]}` |
| POST | `/programs` | create_program | Body `{"name"}` → 201 program dict |
| GET | `/programs/{id}` | read | One program dict |
| POST | `/programs/{id}/members` | any authenticated (store enforces owner-or-admin) | Body `{"username"}` → program dict |
| GET | `/programs/{id}/participants?kind=` | read | List participants → `{"participants": [...]}` |
| POST | `/programs/{id}/participants` | enter | Body `{"ref", "kind"}` → 201 participant dict |
| GET | `/programs/{id}/participants/{pid}` | read | One participant dict |
| POST | `/programs/{id}/participants/{pid}/status` | enter | Body `{"status"}` → updated participant dict |
| GET | `/programs/{id}/accruals?participant_id=` | read | List accrual views → `{"accruals": [...]}` |
| POST | `/programs/{id}/accruals` | enter | Body `{"participant_id", "period", "earned_cents"}` → 201 accrual dict |
| GET | `/programs/{id}/accruals/{aid}` | read | Accrual view (with derived accessed/pending/available) |
| GET | `/programs/{id}/access-requests?status=` | read | List access requests → `{"access_requests": [...]}` |
| POST | `/programs/{id}/access-requests` | enter | Body `{"participant_id", "period", "amount_cents", "date"}` → 201 request dict |
| GET | `/programs/{id}/access-requests/{rid}` | read | One request dict |
| POST | `/programs/{id}/access-requests/{rid}/approve` | decide | → approved request dict (decider ≠ creator) |
| POST | `/programs/{id}/access-requests/{rid}/deny` | decide | → denied request dict |
| POST | `/programs/{id}/access-requests/{rid}/void` | enter | → voided request dict |
| POST | `/programs/{id}/access-requests/{rid}/disbursements` | record | Body `{"date", "method"?}` → 201 disbursement dict |
| GET | `/programs/{id}/disbursements?request_id=` | read | List disbursements → `{"disbursements": [...]}` |
| GET | `/programs/{id}/bookings?status=&kind=` | read | List bookings → `{"bookings": [...]}` |
| POST | `/programs/{id}/bookings` | enter | Body `{"participant_id", "kind", "start_date", "end_date", "amount_cents"}` → 201 booking dict |
| GET | `/programs/{id}/bookings/{bid}` | read | One booking dict |
| POST | `/programs/{id}/bookings/{bid}/confirm` | record | → confirmed booking dict |
| POST | `/programs/{id}/bookings/{bid}/cancel` | enter | → cancelled booking dict |
| PUT | `/programs/{id}/budgets/{period}` | enter | Body `{"lines"}` → budget dict (create-or-replace) |
| GET | `/programs/{id}/budgets/{period}` | read | One budget dict |
| GET | `/programs/{id}/budgets/{period}/vs-actual` | read | Budget lines with spent amounts, variances, over-budget flags, unbudgeted spending |
| GET | `/programs/{id}/wellness-offerings` | read | List offerings → `{"offerings": [...]}` |
| POST | `/programs/{id}/wellness-offerings` | enter | Body `{"title", "kind"}` → 201 offering dict |
| GET | `/programs/{id}/wellness-offerings/{oid}` | read | One offering dict |
| GET | `/programs/{id}/wellness-enrollments?offering_id=` | read | List enrollments → `{"enrollments": [...]}` |
| POST | `/programs/{id}/wellness-offerings/{oid}/enrollments` | enter | Body `{"participant_id"}` → 201 enrollment dict |
| GET | `/programs/{id}/reports/summary?period=` | read | Program summary dict (`period` required) |

Program dicts are `{id, name, owner, members, created_by,
created_utc}` with sequential ids `prog-1`, `prog-2`, …; the other
object types follow the same pattern with their own prefixes (see
`UNION-SPEC.md` for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

Status at delivery: **see `tests/README.md`** for the verified
count, including the mutation-verified negative control on the
earned-cap invariant.

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 Moderate
baseline cross-walked to the NIST SP 800-171 Rev. 2 practices that
define CMMC L2:

- **AC / IA** — access control (platform roles + program
  membership): AC-2 (account management), AC-3 (access enforcement),
  AC-6 (least privilege); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AC-5** — separation of duties: the decider of an access request
  is never its creator, enforced in the store.
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit
  information — append-only store, audit-read restricted to the
  `audit_read` permission).
- **SI / SC** — accruals / access requests / disbursements /
  bookings / budgets: SI-10 (information input validation —
  malformed input, including any non-integer amount and any access
  request that would breach the earned cap, is rejected whole,
  never partially applied); SC-8 (transmission confidentiality —
  TLS when a certificate is configured; encryption at rest is a
  deployment-layer control, stated plainly, not claimed here).

This mapping states which baseline families the build's features
answer to. It is not a FedRAMP authorization and not a CMMC
certification, and it does not claim either. The crosswalk is a
planning/matching equivalence: FedRAMP authorizes products, CMMC
certifies organizations.

## Honesty section

- **What was claimed vs. what was built.** Both siblings were
  spec'd from their own public marketplace descriptions only: 8
  function claims total (4 per fork), each with its source sentence
  stored as evidence in `specs/specs.json`. The siblings share zero
  claimed families. Every core function above traces to a claim, to
  a defining mechanism of a claim (the accrual/access/disbursement
  records are what "access to earned wages" means as a records
  system), or to the L2 baseline (access control, workflow,
  audit) — and `UNION-SPEC.md` says which is which.
- **Nothing was invented.** Marketing prose earned no tags
  ("the leader in On-Demand Pay", "traveler experience",
  talent-attraction outcomes). A source category label (GRC on
  Groupize's record) earned no claim without a descriptive
  sentence. Functions a Finance label suggests but neither sibling
  claims — banking integration, payroll calculation, lending,
  trading, tax — are named in the spec as NOT claimed and excluded
  from the union.
- **Records, not execution.** This build moves no money, links no
  bank account, and books no travel. Disbursement and booking
  records describe events on external rails. Instant disbursement
  execution, travel booking execution, financial wellness delivery
  tools, and streaming reporting are Extended — specified in
  `UNION-SPEC.md`, not implemented here, and registered as gaps for
  the project's final batch.
- **Platform notes, not claims.** Encryption at rest is a
  deployment-layer control. Multi-tenancy is a deployment property
  (one sibling describes its own multi-tenant delivery; this build
  is a single-tenant reference deployment). Demo identities are
  hooks, not an IdP (IA-2 stays with the embedding organization).
