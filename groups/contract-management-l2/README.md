# Contract Management L2 — merged build (Operation DeadRamp, Phase 2, remainder new sibling group)

This is the merged, clean-room implementation of the **Contract
Management L2** sibling group: **2 forks** from the FedRAMP
Marketplace — **F1506046707** (Unison Contracting SaaS) and
**F1510017461** (Unison FedConnect), both **FedRAMP Moderate /
CMMC L2**, FedRAMP Certified — built as one open-source service
from the group's union contract (`UNION-SPEC.md`). Contract
Management is a brand-new category proposed by the remainder
census (no group exists at any other tier), so the function
taxonomy was defined from the two forks' own marketplace
descriptions (the Group 1 method): a **21-family** taxonomy,
**25 claims** (Contracting SaaS 11, FedConnect 14), each carrying
its source sentence as evidence.

**The category boundary, stated once.** Procurement *operations*
tooling (AI sourcing, RFP tooling) lives in Operations Management
L2; law and policy work lives in Legal & Policy; post-award
grants administration lives in Grant Management L2. This pair is
different in kind: the **contract lifecycle system of record** for
federal acquisition — contract records and their modifications,
compliance requirements, protests, data calls, and the
opportunity-to-award portal records around them. This build is
contract lifecycle records, built to exactly that boundary.

It was written from that contract only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**, no
external dependencies.

## The 18 core functions

1. **Organization registry & membership** — organizations
   (`org-`) keyed by an opaque `org_ref` with a label and a
   member list. Membership is the boundary every
   organization-scoped function enforces; only the
   organization's creator or a platform admin may add members.
2. **Participant registry** — participants (`par-`) at platform
   level: the vendor / applicant registration records directed
   opportunities and submissions presuppose. Registration
   records are not identity proofing.
3. **Contract records** — contracts (`con-`): the lifecycle
   system of record, with `ceiling_cents` and base `award_cents`
   (integer cents), optional period start/end, and a guarded
   lifecycle (`active` → `closed`). Read views derive
   `obligated_cents` and `period_elapsed`; the stored record
   carries neither key.
4. **Contract modification records** — modifications (`mod-`)
   with signed integer-cent amounts. **The modification bounds
   rule is the signature invariant:** the obligated amount (base
   award + recorded modifications) must always satisfy
   0 ≤ obligated ≤ ceiling, enforced before a contract is
   created and before every modification is stored.
   Modifications against closed contracts are rejected.
5. **Compliance requirement records** — requirements (`req-`)
   with a guarded lifecycle (`open` → `satisfied` / `waived`).
6. **Protest records** — protests (`pro-`) against exactly one
   of a contract or an opportunity, with a required response due
   date and a derived `overdue` flag on read views.
7. **Data-call records** — data calls (`dcl-`) with opaque
   requester references, required due dates, and derived
   `overdue`.
8. **Risk records** — risks (`rsk-`), optionally against a
   contract. Visibility records only; nothing is assessed or
   scored.
9. **Communication records** — communications (`com-`):
   counterparty reference, direction, label. **Metadata only —
   the store has no parameter that can accept message content.**
10. **Opportunity records** — opportunities (`opp-`) with kinds
    from the fork's own vocabulary (`erfx`, `reverse_auction`,
    `financial_assistance`), public or directed audiences, an
    optional close time, and a derived `past_close` flag.
11. **Submission records** — submissions (`sub-`) guarded four
    ways: the opportunity must be open, not past its close time,
    the participant must be registered, and on a directed
    opportunity the participant must be a directed recipient.
    Read views derive `awarded`.
12. **Award records** — awards (`awd-`) against an opportunity
    and one of its submissions, in integer cents. A submission
    is awarded at most once.
13. **Fee & payment records** — payments (`pay-`) of kind
    `subscription` / `award_fee` (the description's own two fee
    mechanisms), positive integer cents, with optional
    opportunity / award links.
14. **Workflow definition registry** — workflows (`wfl-`):
    records only. The registry has no execute operation, pinned
    by test.
15. **Integration registry** — integrations (`int-`): records of
    system-to-system interfaces, never transports.
16. **Registry reporting** — an organization report computed on
    read: counts by status and kind, obligated / ceiling /
    award / payment cent sums, derived overdue data-call count.
    Counts and sums only — no scores.
17. **Registry search** — literal case-insensitive substring
    search over registry metadata, membership-scoped, plus the
    platform participant registry.
18. **Access control & audit** — platform roles `admin`,
    `member`, `viewer` with a permission matrix enforced on
    every operation, layered with organization membership; and
    an append-only audit log recording every mutation and every
    denied attempt.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Validation always precedes mutation.

## Run

```bash
cd groups/contract-management-l2
PYTHONPATH=src python3 -m contractmgmt serve            # http://127.0.0.1:8813
PYTHONPATH=src python3 -m contractmgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m contractmgmt serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization).
Callers authenticate with `X-User` / `X-Role` headers matching
these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including creating organizations and reading the audit log |
| `bob` | member | contracts, cases, portal records, payments, registries, reports (in organizations he belongs to) |
| `carol` | viewer | reads and reports only, in organizations she belongs to |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | org_read | registry search dict (membership-scoped + participants) |
| `GET /organizations` · `POST /organizations` | org_read / org_write | create → 201; body `{org_ref, label}` |
| `GET /organizations/{id}` | org_read | |
| `POST /organizations/{id}/members` | creator-or-admin (store) | body `{"username": ...}` → organization dict |
| `GET /participants` · `POST /participants` | open read / registry_write | platform registry; create → 201; body `{participant_ref, label}` |
| `GET /organizations/{id}/contracts` · `POST` | org_read / contract_write | GET returns derived views; create → 201 stored shape; body `{contract_ref, title, counterparty_ref, ceiling_cents, award_cents, period_start?, period_end?}` |
| `POST /organizations/{id}/contracts/{cid}/close` | contract_write | `active` → `closed` |
| `GET /organizations/{id}/contracts/{cid}/modifications` · `POST` | org_read / contract_write | create → 201; body `{mod_ref, amount_cents, label?}`; out-of-bounds → 400 |
| `GET /organizations/{id}/requirements?status=` · `POST` | org_read / compliance_write | create → 201; body `{requirement_ref, label}` |
| `POST /organizations/{id}/requirements/{rid}/satisfy` · `/waive` | compliance_write | guarded transitions from `open` |
| `GET /organizations/{id}/protests` · `POST` | org_read / case_write | GET returns derived views; body `{protest_ref, label, due_at, contract_id? \| opportunity_id?}` (exactly one link) |
| `POST /organizations/{id}/protests/{pid}/close` | case_write | |
| `GET /organizations/{id}/datacalls` · `POST` | org_read / case_write | GET returns derived views; body `{datacall_ref, requester_ref, label, due_at}` |
| `POST /organizations/{id}/datacalls/{did}/close` | case_write | |
| `GET /organizations/{id}/risks?contract_id=` · `POST` | org_read / case_write | body `{risk_ref, label, contract_id?}` |
| `POST /organizations/{id}/risks/{rid}/close` | case_write | |
| `GET /organizations/{id}/communications?direction=` · `POST` | org_read / comm_write | body `{comm_ref, counterparty_ref, direction, label}` — no content field exists |
| `GET /organizations/{id}/opportunities?kind=` · `POST` | org_read / portal_write | GET returns derived views; body `{opportunity_ref, title, kind, audience?, directed_to?, closes_at?}` |
| `POST /organizations/{id}/opportunities/{oid}/close` | portal_write | |
| `GET /organizations/{id}/opportunities/{oid}/submissions` · `POST` | org_read / portal_write | GET returns derived views; body `{submission_ref, participant_ref}` |
| `GET /organizations/{id}/opportunities/{oid}/awards` · `POST` | org_read / portal_write | body `{submission_id, award_ref, amount_cents}` |
| `GET /organizations/{id}/payments?kind=` · `POST` | org_read / payment_write | body `{payment_ref, kind, amount_cents, opportunity_id?, award_id?}` |
| `GET /organizations/{id}/workflows` · `POST` | org_read / registry_write | records only; nothing executes |
| `GET /organizations/{id}/integrations` · `POST` | org_read / registry_write | body `{integration_ref, system_ref, label}` |
| `GET /organizations/{id}/report` | report_read | counts and cent sums, computed on read |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown
user or role mismatch, 403 permission, 404 not found. Denied
attempts are audited with the action suffixed `:denied`.

## Permission matrix

Eleven actions: `org_read`, `org_write`, `contract_write`,
`compliance_write`, `case_write`, `comm_write`, `portal_write`,
`payment_write`, `registry_write`, `report_read`, `audit_read`.

| Role | Permissions |
|---|---|
| `admin` | all eleven |
| `member` | all except `org_write` and `audit_read` (9) |
| `viewer` | `org_read`, `report_read` |

Organization membership is layered on top: every
organization-scoped operation additionally requires the actor to
be a member of that organization (a platform admin is the
exception). The participant registry is not organization-scoped:
writes require `registry_write`; reads are open to any actor.

## Control mapping summary

Group tier CMMC **L2** ⇔ FedRAMP **Moderate** (per the project
crosswalk); baseline NIST SP 800-53 Rev. 5 Moderate, cross-walked
to the 110 practices of NIST SP 800-171 Rev. 2.

- Access control (platform roles + organization membership) →
  **AC** (AC-2, AC-3, AC-6), **IA** (IA-2 — identity is supplied
  by the embedding organization via user/role headers; the build
  ships hooks, not an identity provider. Participant
  registration records are registration, not identity proofing).
- Audit log → **AU** (AU-2, AU-3, AU-6 — append-only store;
  audit-read restricted to `audit_read`, held by admin only).
  This is also the substrate of the forks' auditability claim:
  the auditable approach both descriptions name is answered by
  an append-only trail over every record in the build.
- Registries, lifecycle guards, the modification bounds seam,
  integer-cent discipline → **SI** (SI-10 — malformed input,
  including any non-integer money value, duplicate reference,
  out-of-bounds modification, or late/directed-guard submission,
  is rejected whole) and **SC** (SC-8 — TLS when a certificate
  is configured; encryption at rest is a deployment-layer
  control, stated plainly, not claimed here. Neither fork's
  description claims FIPS-validated modules for its platform,
  and this build claims none — Python's standard library is not
  a FIPS-validated cryptographic module).

## Tests

```bash
cd groups/contract-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 106 tests
```

**106 tests, all passing**, including the mutation-verified
negative control: removing the modification bounds check from
the real store makes exactly 8 tests fail (see `tests/README.md`
for the drill record).

## Honesty

- This build is the **records substrate only**. The regulatory
  corpus and its interpretation, the workflow execution engine,
  the analytics engine, the opportunity portal front-end, the
  reverse auction engine, the submission intake transport, the
  payment processing rails, the integration transport, the
  communication transport, and identity/registration
  verification are **Extended** — named as gaps in
  `UNION-SPEC.md`, not implemented here. The core records
  contracts, cases, opportunities, submissions, and awards; it
  runs no auction, executes no workflow, transports nothing,
  and moves no money.
- **Substance is never stored.** Contracts are metadata +
  amounts; bids are submission records without contents;
  communications are metadata with no content field anywhere in
  the store's signatures — pinned by tests.
- **Nothing is scored.** No record shape carries a score,
  rating, ranking, or evaluation, and the descriptions claim
  none: submissions are recorded, never evaluated. Reporting is
  counts and sums of recorded quantities.
- Derived status is derived at read, never stored: a contract's
  `obligated_cents` and `period_elapsed`, a case's `overdue`,
  an opportunity's `past_close`, and a submission's `awarded`
  are computed by the read views, and the stored records carry
  none of those keys — pinned by tests that read the store's
  internal records.
- Checked absences are stated in `UNION-SPEC.md` and pinned by
  the spec tests: neither description claims contract authoring,
  e-signature, source selection or scoring, performance
  surveillance, invoicing/disbursement, protest adjudication, or
  any AI/ML or API function — so the build contains none of
  them, and no function was guessed into existence.
- Demo identities are hooks, not an IdP (IA-2). Encryption is
  TLS when a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a
  **single-tenant reference deployment**.
- The baseline mapping (800-53 Moderate ⇔ 800-171) is a planning
  equivalence per the project crosswalk — **not a FedRAMP
  authorization and not a CMMC certification**, and this build
  claims neither. FedRAMP authorizes products; CMMC certifies
  organizations.
- Claims discipline: every function above traces to the forks'
  claims in `specs/specs.json` (25 evidenced claims across a
  21-family taxonomy defined from the forks' own descriptions)
  or to the Moderate/L2 control families in `UNION-SPEC.md`.
  Counts are a floor, stated as such.
