# Finance L3-adjacent — singleton build (Operation DeadRamp, Phase 2, Group 42)

This is the clean-room implementation of the **Finance**
category's **L3-adjacent singleton**: **1 fork** from the FedRAMP
Marketplace at the CMMC L3-adjacent tier (FedRAMP High) — **AWS
GovCloud** (Amazon Web Services, Inc.) — built per the group's
union spec, [`UNION-SPEC.md`](UNION-SPEC.md), as the cross-tier
merge of that fork with the shipped Group 31 (Finance L2) build
under the Merge Rule.

The honest headline of this singleton: **the fork tags zero
function claims.** It is a cloud infrastructure platform filed
under Finance; its marketplace description is region prose (an
AWS Region for sensitive workloads, ITAR, US-citizen/US-soil
operation, account screening, data-center substance) in which no
sentence of Group 31's verbatim taxonomy matches — not even the
hosting family's phrases. The spec does not round cloud vocabulary
up into finance families. What stands in this build is the Finance
category substrate itself, carried up whole from Group 31 under
the Merge Rule (a thinner High fork's prose is not a downgrade)
and uplifted to the High baseline — every core function flagged
**carried, not claimed** for this tier. The fork's own substance,
the cloud platform, is the deployment layer and is named as gaps
in `UNION-SPEC.md`, not built.

It was written from the contract in that spec only: original
code, no vendor code, assets, or branding from the fork. Python 3,
**standard library only**, no external dependencies. Reuse from
Group 31 is stated explicitly in `UNION-SPEC.md` (one module
byte-identical; six modified for the tier uplift).

## The 11 core functions (carried up whole, at the High baseline)

1. **Programs & members** — named programs (one employer or
   agency finance program) with an owner, a member list, and
   provenance. Membership is the boundary every other core
   function enforces.
2. **Participant & traveler registry (opaque references)** —
   participants known only by a caller-supplied opaque `ref` and
   a kind (`employee` or `traveler`), with an active/inactive
   status. The record shape is pinned by tests: no field can hold
   a real name, bank account number, or government identifier.
3. **Earned-wage accrual & access records** — per participant per
   pay period, an accrual records wages already earned. Access
   requests draw against a period's accrual under the
   **earned-cap invariant** (pending + approved + disbursed never
   exceed earned), run the approval machine with separation of
   duties, and an approved amount can gain a disbursement record
   — a record, after the fact, that money moved on external
   rails. This build moves no money.
4. **Travel booking records** — booking records (air or hotel,
   date range, amount in cents) with a `recorded → confirmed /
   cancelled` lifecycle. Records of reservations made elsewhere;
   the build books nothing.
5. **Spend budgets & tracking** — a budget per program per period
   (planned cents per category); **spend-vs-budget** computes
   spent amounts from records (non-cancelled bookings by kind,
   disbursed wage access under `earned_wage`), variance, and
   over-budget flags — computed, never asserted.
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
9. **API access** — every function above is exposed over a REST
   API (JSON), so the service composes with anything that speaks
   HTTP. [L3] Unsuccessful logons lock the username out (AC-7,
   below).
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer`, **plus `auditor`** [L3] (audit
    review only, AC-5), with a permission matrix enforced on
    every operation, layered with program membership
    (non-members cannot read or write a program's content; the
    platform `admin` role can).
11. **Audit log** — an append-only, **hash-chained** [L3] audit
    trail: every program, membership, participant, accrual,
    access-request, disbursement, booking, budget, and wellness
    mutation, and every denied attempt, recorded with actor,
    action, target, and UTC timestamp. [L3] Writes are
    **fail-closed** (a failed audit write rolls the operation
    back), the chain is verifiable (`GET /audit/verify`), and the
    trail is **queryable** (`GET /audit` filter parameters).
    Optional JSONL file persistence.

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

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`), and [L3] `--max-failed-logins N` /
`--lockout-seconds S` for the AC-7 unsuccessful-logon lockout
(defaults 3 and 300). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401). [L3] Consecutive failed logons
count per username: at the configured maximum the username locks
for the configured duration, and attempts during the lock — even
with the correct role — get 403 and are audited as `auth:locked`;
a successful logon resets the counter.

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, create_program, enter, decide, record, manage_members, audit_read, admin |
| `bob`   | member  | read, create_program, enter, decide, record |
| `carol` | viewer  | read |
| `dana`  | auditor | audit_read [L3] |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

The Group 31 surface, unchanged, plus the two [L3] audit rows:

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}`; optional filters `?actor=&action=&target=&since=&until=` [L3] |
| GET | `/audit/verify` | audit_read | `{"ok": bool, "entries": n, "first_bad_index": i\|null}` — hash-chain verification [L3] |
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
count, including the two mutation-verified negative controls (the
earned-cap invariant and the audit-chain verifier).

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 **High**
baseline ⇔ the CMMC L3 basis (the 110 practices of NIST SP
800-171 Rev. 2 plus selected NIST SP 800-172 enhanced
requirements):

- **AC / IA** — access control (platform roles + program
  membership): AC-2 (account management), AC-3 (access
  enforcement), AC-6 (least privilege); [L3] AC-7 (unsuccessful
  logon lockout); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via
  user/role headers; this service ships hooks, not an IdP).
- **AC-5** — separation of duties: the decider of an access
  request is never its creator, enforced in the store; [L3] the
  auditor role separates audit review from administration.
- **AU** — audit log: AU-2 (event logging), AU-3 (content of
  audit records), [L3] AU-5 (fail closed on audit processing
  failure), AU-6 (audit review), [L3] AU-7 (audit reduction &
  search), AU-9 (protection of audit information — append-only,
  hash-chained store, audit-read restricted to the `audit_read`
  permission).
- **SI / SC** — accruals / access requests / disbursements /
  bookings / budgets: SI-10 (information input validation —
  malformed input, including any non-integer amount and any
  access request that would breach the earned cap, is rejected
  whole, never partially applied); SC-8 (transmission
  confidentiality — TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated
  plainly, not claimed here).

Baseline gaps named, not implied closed: MFA / authenticator
management (IA-2(1)/(2), IA-5), FIPS-validated cryptography
(SC-13 — this build's standard library is not a validated module
and does **not** inherit the fork's FIPS posture), encryption at
rest (SC-28), audit retention enforcement (AU-11), session lock /
termination (AC-11/AC-12).

This mapping states which baseline families the build's features
answer to. It is not a FedRAMP authorization and not a CMMC
certification, and it does not claim either. The crosswalk is a
planning/matching equivalence: FedRAMP authorizes products, CMMC
certifies organizations.

## Honesty section

- **What was claimed vs. what was built.** The singleton was
  spec'd from its own public marketplace description only:
  **0 function claims**, with the full description stored in
  `specs/specs.json` and every near-miss itemized in
  `scratch/ARTIFACTS.md`. All 11 core functions are flagged
  **carried, not claimed** for this tier: they are Group 31's
  union, carried up whole under the Merge Rule and uplifted to
  High — `UNION-SPEC.md` records the core-boundary decision and
  its reasoning.
- **Nothing was invented, and nothing was rounded up.** Cloud
  vocabulary ("move more sensitive workloads into the cloud") was
  not rounded into the hosting family, whose verbatim phrases are
  absent; "collaborative continuous monitoring" matched no family
  (Finance has no monitoring family); the source record's
  "Finance" label — first of ten `business_categories` — is the
  filing reason, not a claim. Functions a Finance label suggests
  but no fork in the category claims at either tier — banking
  integration, payroll calculation, lending, trading, tax — are
  named in the spec as NOT claimed and excluded from the union.
- **The fork's substance is the platform layer.** AWS GovCloud's
  actual product — cloud regions, compute/storage/networking
  infrastructure, US-soil operation, account screening — is
  infrastructure this build runs on, not finance function it
  implements. It is named as gaps in `UNION-SPEC.md` for the final
  batch.
- **Records, not execution.** This build moves no money, links no
  bank account, and books no travel. Disbursement and booking
  records describe events on external rails. Instant disbursement
  execution, travel booking execution, financial wellness
  delivery tools, and streaming reporting are Extended —
  specified in `UNION-SPEC.md`, not implemented here, and
  registered as gaps for the project's final batch.
- **Platform notes, not claims.** Encryption at rest is a
  deployment-layer control. Multi-tenancy is a deployment
  property (the fork operates multi-tenant regions in reality;
  this build is a single-tenant reference deployment). Demo
  identities are hooks, not an IdP (IA-2 stays with the embedding
  organization).
