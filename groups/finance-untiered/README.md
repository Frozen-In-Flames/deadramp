# Finance — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **1 untiered fork** of Finance — census
unit `untiered:Finance` in `../../remainder.json`, Untiered Set 24
under the remainder pipeline. **This is an untiered set, and that
means something specific:** the member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no baseline
for this offering, so **tier stays null**: no tier is assigned, no
CMMC equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); the per-fork spec sheet is in
[`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The fork was spec'd under the category's existing 8-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Finance L2 group's original shipped
claim tables exactly — **2 of 2 forks, 8 of 8 claims, deep-equal**
against the sheets at the founding ship commit (`a929b5b`) —
before tagging this set. Result here: **1 claim** on the set's 1
fork — `reporting` at **artifact weight** (it fires on "employee
expense reporting", the expense-report filing workflow, not on
reporting/analytics phrasing of the kind the family's founding
claim rests on; recorded in `scratch/ARTIFACTS.md`, not hidden or
repaired). The fork is not a zero-claim fork, and the category's
spend family is its loudest named absence: the fork's whole domain
is expenses, yet the word "spend" occurs nowhere in its description
("expense" does not contain it).

The build implements the category's **eleven-function substrate**
— the finance records machinery both founding siblings' platforms
presuppose — carried **byte-identical** from the founding Finance
L2 build (`../finance-l2/src/finance/`, 7 of 7 modules; SHA-256
accounting below). The **Finance L3 singleton's High uplifts are
not inherited**: no hash-chained audit, no fail-closed writes, no
restricted auditor, no logon lockout — nothing is uplifted into a
set whose tier is null. Where the founding contract's text ties
its hooks to the L2 baseline, read it here as **baseline-neutral
hooks**: at tier null they are substrate, claimed against no
baseline.

## The 1 fork

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2633058235 | Emburse | Emburse Enterprise | 1 (at artifact weight) |

The census proposed category Finance, agreeing with the category
the source itself files the fork under; its source business
categories are Finance and Travel Management, recorded on the
sheet. Its authorization status as recorded is Initial
Implementation, and its service model is SaaS — record data, not
claims.

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

**No core function is claim-supported at full weight by this set's
fork** (see `UNION-SPEC.md` for the full accounting): its only
family hit is the artifact-weight `reporting` hit, which documents
no reporting capability and supports nothing, and its described
function — expense reporting, approval, and reimbursement
workflows — is named by no family in the category taxonomy. The
functions are implemented because they are the category substrate
every finance platform in this category presupposes — the founding
group's design — not because this fork's prose claims them. No
function is claimed to be *attained* by the fork — the build is
the merged open implementation, not the fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m finance serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, create_program, enter, decide, record, manage_members, audit_read, admin |
| `bob`   | member  | read, create_program, enter, decide, record |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

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
| POST | `/programs/{id}/accruals` | enter | Body `{"participant_id", "period", "earned_cents"}` → 201 accrual record |
| GET | `/programs/{id}/accruals/{aid}` | read | Accrual record + derived accessed/pending/available |
| GET | `/programs/{id}/access-requests?status=` | read | List access requests → `{"access_requests": [...]}` |
| POST | `/programs/{id}/access-requests` | enter | Body `{"participant_id", "period", "amount_cents", "date"}` → 201 request dict |
| GET | `/programs/{id}/access-requests/{rid}` | read | One access request dict |
| POST | `/programs/{id}/access-requests/{rid}/approve` | decide | → updated request dict (decider ≠ creator) |
| POST | `/programs/{id}/access-requests/{rid}/deny` | decide | → updated request dict |
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
| GET | `/programs/{id}/budgets/{period}/vs-actual` | read | Budget lines with spent amounts, variances, over-budget flags + unbudgeted categories |
| GET | `/programs/{id}/wellness-offerings` | read | List offerings → `{"offerings": [...]}` |
| POST | `/programs/{id}/wellness-offerings` | enter | Body `{"title", "kind"}` → 201 offering dict |
| GET | `/programs/{id}/wellness-offerings/{oid}` | read | One offering dict |
| GET | `/programs/{id}/wellness-enrollments?offering_id=` | read | List enrollments → `{"enrollments": [...]}` |
| POST | `/programs/{id}/wellness-offerings/{oid}/enrollments` | enter | Body `{"participant_id"}` → 201 enrollment dict |
| GET | `/programs/{id}/reports/summary?period=` | read | Per-period program summary (missing `period` → 400) |

Program dicts are `{id, name, owner, members, created_by,
created_utc}` with sequential ids `prog-1`, `prog-2`, …; the other
object types follow the same pattern with their own prefixes (see
`UNION-SPEC.md` and the founding group's spec for every dict
shape). Participant dicts have exactly the keys `{id, program_id,
ref, kind, status, created_by, created_utc}` — the privacy pin: no
field can hold a real identifier.

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

(Run exactly as above: helpers are imported as a top-level module
from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

**209 tests, OK** at delivery: the founding group's 202-test core
suite carried with the code (its `test_additions.py` is *not*
carried — it pins the parent group's remainder additions against
the parent group's own specs, which are not this set's), plus spec
tests pinning this set (exactly 1 sheet; membership exact against
`remainder.json`; the sheet's tier null / impact "Unknown"; every
claim's evidence verbatim in its description; exactly 1 claim on
exactly the family {reporting}, with the zero-claim set empty; the
named-absence tokens occurring nowhere in the description). The
category's signature earned-cap mutation drill was re-run in this
tree — exactly 5 failures under the mutant, the founding drill's
identical failure set, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/finance/` is carried from the founding group
`../finance-l2/src/finance/` — **7 of 7 modules byte-identical**,
SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `bfbdf5a40d665f74aca1511a7573cd52202b3954ed83040c696162a839e10b54` |
| `__main__.py` | `71c3de5588adc92231a7f8f6cdfd620c99877359875c1339d2ac89b8568c641a` |
| `access.py` | `f7cb5e28e5818bb88f12d9d186625269695b42558dadc49e3a15c3308a85de8e` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `2e7c57db7f0b0f4b621b623549d0ed3f9f198e37b165671030117f551e6d0e45` |
| `service.py` | `1610945ac96d9367dd5470bfea40d15b27e4cd9fa1872bd236fbce4738bbfac9` |
| `store.py` | `f905061dbe5d45ae3ef64333a1a62a1f05af8fadbf0e5d01608cd6ad643f7c9e` |

The shipped tree contains exactly the package under `src/finance/`
— nothing flat at the `src/` root. The test suite is likewise
carried (all eleven founding core test modules plus the helpers),
with one labeling fix in `tests/finance_helpers.py` (its docstring
now names this untiered set instead of L2), the parent's
`test_additions.py` not carried (it pins the parent group's
additions, not this set), and the new `tests/test_specs.py` added.
Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering (impact "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. A documented control claim is a **fork's claim about
itself**, recorded with its evidence in `UNION-SPEC.md` and
`specs/specs.json`; it is not the build's control attainment, and
nothing here fills a family in from any baseline.

Documented by the set's fork: **none.** No sentence in the fork's
description asserts a NIST SP 800-53 control family at claim
weight, and none at the taxonomy tier (the category taxonomy is
functional by founding design).

Recorded at prose weight, converted to no family:

- **"Authorized users"** — the solution "is designed to enable
  authorized users to submit, review, approve, and administer
  business expenses": a user population named, no mechanism stated
  (no access-control, authentication, SSO, MFA, federation, or role
  language occurs anywhere in the description). **AC and IA are not
  documented by it.**
- **Customer-policy framing** — "in accordance with applicable
  organizational travel and expense policies": the customer's own
  business policies framing the workflow, not a control claim about
  the offering.

**Not documented** by the fork: every NIST SP 800-53 control family
— AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PM, PS, RA, SA,
SC, and SI **as control claims** — is asserted by no sentence in
the description. One bound stated explicitly: **SC is not
documented** (the word "encrypt" occurs nowhere, despite
"cloud-based SaaS solution"; pinned by test). If the source later
publishes an impact level for this offering, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for the fork or for itself.
  The fork's recorded authorization status is source data, not a
  claim by this build, and the fork's documented control language
  (here: none at claim weight) is recorded as *its* claim, never as
  the build's control attainment.
- **The L3 uplifts are not here.** The Finance L3 singleton's High
  machinery (hash-chained audit, fail-closed writes, audit
  reduction, restricted auditor, logon lockout) is a different
  tier's build. This set carries the L2 founding substrate as-is;
  nothing was uplifted into a tier-null set.
- **The substrate is carried, not claimed.** All eleven core
  functions lack full-weight claim support from this set's fork:
  its one `reporting` hit is the artifact-weight "expense
  reporting" hit, which documents no reporting capability, and its
  described function (expense reporting, approval, and
  reimbursement workflows) is named by no taxonomy family. The
  functions are implemented because they are the category substrate
  — the founding group's design — not because this fork's prose
  claims them.
- **Extended functions are specified, not implemented.** The union
  spec ranks 8 functions; the substrate behind the Core is
  implemented here. The Extended functions that arise from this
  set's fork are the expense reporting/approval/reimbursement
  workflow engine and the travel & expense policy enforcement
  engine (both registered in `UNION-SPEC.md`'s gap list); the
  founding group's remaining extended tail (instant disbursement
  execution / payment rails, travel booking execution engines,
  financial wellness delivery tools, streaming reporting pipelines)
  stands registered under the founding group and is not
  re-registered here.
- **Records, not execution:** disbursement records state that money
  moved on an external rail; this build moves no money, holds no
  balances on any rail, and books no travel. Booking records record
  reservations made elsewhere.
- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated plainly,
  and not claimed here — and the fork documents no encryption claim
  of its own (see above).
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- **Named absences stand.** Spend management has 0 claimants in
  this set despite the fork's expense domain (the word "spend"
  never occurs); travel management, travel booking, SaaS delivery,
  earned wage access, financial wellness, and open platform & APIs
  likewise stand at 0 of 1, several with substance present in other
  words. Nothing was back-filled to make the set look complete.
