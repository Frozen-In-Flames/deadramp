# Travel Management L2 — merged build (Operation DeadRamp, Phase 2, Group 55)

This is the merged, clean-room implementation of the **Travel
Management L2** singleton: **1 fork / vendor platform** from the
FedRAMP Marketplace (GO.gov, IBM), built as one open-source service
from the group's union contract (`UNION-SPEC.md`). Travel Management
is a brand-new category with no parent group at any tier, so the
function taxonomy was defined from the fork's own marketplace
description (the Group 1 method): **9 claims**, each carrying its
source sentence as evidence. The description is three sentences; its
five service families (travel, expense, integration, notification,
reporting) sit in one suite list.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

## Remainder addition (unit `addition:travel-management-l2`)

The group now specs **2 forks**: the remainder census added
**mLINQS Hosting Service** (mLINQS, FedRAMP Moderate /
Certified) as a second spec sheet. Under the group's 9-family
taxonomy applied verbatim it claims **0 functions** — a
zero-claim fork: its entire marketplace description is eight
sentences about employee relocation ("process thousands of
employee moves annually", "automates FTR, JTR, DSSR, and 6FAM
CONUS/OCONUS relocation policy") in which none of the
taxonomy's verbatim patterns, all defined from GO.gov's own
suite-list vocabulary, appears. The group total stays
**9 claims** (1 of 2 forks claiming). The singleton's five
checked absences were re-searched against the newcomer and all
survive — no booking, per-diem, reimbursement, approval, or
receipt vocabulary in either listing — and the fork's
relocation processing and policy-automation functions are
registered as two new gaps. The core is unchanged (`src/`
byte-identical); the addition brings 14 new spec-integrity and
substrate tests — **110 tests, OK** — and the signature
voucher-cap drill was re-run in this tree (exactly 6 failures
under mutation: the shipped 5 plus the additions case). Full
account in [`ADDENDUM.md`](ADDENDUM.md).

## The 13 core functions

1. **Organization registry & membership** — organizations (`org-`)
   that scope every other record; membership is enforced on every
   organization-scoped operation, on top of the role matrix.
2. **Traveler registry** — travelers (`trv-`) known only by an
   opaque caller-supplied reference and a label; the record shape
   is pinned, so no field can hold real personal data.
3. **Trip authorization records** — authorizations (`auth-`) with a
   destination label, purpose, depart/return dates, and an
   authorized amount in integer cents. Lifecycle
   `draft → submitted → approved / declined` is event-driven and
   stored; the trip **phase** (`upcoming` / `in_progress` /
   `completed`) is derived at read from the dates, never stored.
4. **Authorization decision records** — decisions (`dec-`) recording
   the decider's own outcome and note. The decider is never the
   requester (separation of duties).
5. **Expense report records** — reports (`exp-`) against an approved
   authorization, with the same lifecycle and decision discipline.
6. **Expense line item records** — items (`itm-`) in generic
   substrate categories (lodging, meals, transport, incidentals,
   other), integer cents, addable only while the report is a draft.
   The report total is derived from its items, never stored.
7. **Expense decision records** — the decider is never the report's
   creator.
8. **Voucher records** — vouchers (`vou-`) against an approved
   report, under the **voucher-cap invariant**: cumulative vouchers
   never exceed the report's total. A second cap stands at report
   submission: cumulative submitted/approved report totals never
   exceed the authorization's authorized amount. Vouchers are
   records; no money moves.
9. **Notification records** — notifications (`ntf-`), recorded, not
   delivered.
10. **Integration definition registry** — integration definitions
    (`int-`) registered as data. The registry **never executes** a
    definition; that is pinned by test.
11. **Search & summary reporting** — substring search across
    travelers, authorizations, and reports; per-organization
    summaries computed on read as counts and money sums. Never
    scores.
12. **REST API** — every function above over a JSON REST API.
13. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial record, no id consumed). All
money is integer cents: floats, booleans, and strings are rejected
at the boundary.

## Run

```bash
cd groups/travel-management-l2
PYTHONPATH=src python3 -m travel serve             # http://127.0.0.1:8799
PYTHONPATH=src python3 -m travel serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m travel serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | member | enter, decide (never his own records), record |
| `carol` | viewer | reads only |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?org_id=&q=` | read | `{"travelers": [...], "authorizations": [...], "expense_reports": [...]}` |
| `GET /organizations` · `POST /organizations` | read / enter | create → 201 |
| `GET /organizations/{id}` | read | membership required |
| `GET /organizations/{id}/members` · `POST` | read / manage_members | POST body `{"username": ...}` |
| `GET /organizations/{id}/summary` | read | counts and sums, computed on read |
| `GET /organizations/{id}/travelers` · `POST` | read / enter | create → 201 |
| `GET /travelers/{id}` | read | |
| `GET /organizations/{id}/authorizations` · `POST` | read / enter | create → 201; `?now=` on reads |
| `GET /authorizations/{id}` | read | derived `phase`, `claimed_cents`, `reimbursed_cents` |
| `POST /authorizations/{id}/submit` · `/decide` | enter / decide | decide body `{"approve": bool, "note": ...}`; never the creator |
| `GET /authorizations/{id}/decisions` | read | |
| `GET /authorizations/{id}/expense-reports` · `POST` | read / enter | create → 201; authorization must be approved |
| `GET /expense-reports/{id}` | read | derived `total_cents`, `reimbursed_cents`, `remaining_cents` |
| `GET /expense-reports/{id}/items` · `POST` | read / enter | POST → 201; draft reports only |
| `POST /expense-reports/{id}/submit` · `/decide` | enter / decide | submit checks the authorization cap |
| `GET /expense-reports/{id}/vouchers` · `POST` | read / record | POST → 201; voucher cap enforced |
| `GET /organizations/{id}/notifications` · `POST` | read / record | recorded, not delivered |
| `GET /organizations/{id}/integrations` · `POST` | read / record | definitions only; never executed |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/travel-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 96 tests
```

**96 tests, all passing**, including the mutation-verified
negative control: removing the voucher-cap check from the real
store makes exactly 5 tests fail (see `tests/README.md` for the
drill record).

## Honesty

- The build implements the records substrate the fork's public
  description actually presupposes. The engines are not in it: no
  booking or reservation engine, no carrier/hotel/GDS integrations,
  no payment execution, no receipt capture, no connector engines,
  no delivery transport, no report generation engine. Each is named
  as an Extended gap in `UNION-SPEC.md` for the final batch.
- The description claims **no booking, per-diem, reimbursement, or
  approval function** — those words do not appear in it. Booking and
  per-diem are gaps outright. Authorization/decision records and
  voucher records enter the core only as the records forms the
  claimed travel and expense services presuppose, under explicit
  core-boundary decisions stated in the union spec, not dressed up
  as claims.
- Records of trips and authorizations are Core; travel itself is
  not performed. Vouchers are records; no money moves in this
  build; disbursement belongs to the embedding organization's
  payment rails.
- Statuses that depend on dates or other records (trip phase,
  report totals and balances) are derived at read time and never
  stored; the stored records carry no such keys — pinned by tests.
- Demo identities are hooks, not an identity provider. IA-2 stays
  with the embedding organization. Encryption is TLS when a
  certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment; the fork's System-of-Systems composition
  and its commercial SaaS/PaaS components are its own platform,
  outside this build.
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (9 evidenced claims from the single
  fork, taxonomy defined from its own description) or to the
  Moderate/L2 control families in `UNION-SPEC.md`. Counts are a
  floor, stated as such.
