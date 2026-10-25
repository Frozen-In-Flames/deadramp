# Union Spec — Accounting, CMMC L3-adjacent (DeadRamp Phase 2, Group 23)

The merged functional spec for the twenty-third sibling group built
so far: **2 forks**, category **Accounting**, CMMC tier
**L3-adjacent** (every member is FedRAMP **High** in `forks.json` —
verified, so the group is single-tier and the merge takes the group
baseline in full, per Merge Rule 2). The member list in `forks.json`
was reconciled against `MAP.md`'s "Accounting — L3-adjacent (2)"
section: **zero diffs**.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
both descriptions were present in the cached dataset.

## This is a cross-tier merge

One parent is the shipped Group 5 build
([`../accounting-l2/`](../accounting-l2/)), itself the union of the
21 Accounting L2 (FedRAMP Moderate) forks: a double-entry accounting
service whose 13-function core is carried up **whole** under the
Merge Rule. The other parent is this group's 2 High forks. The merge
takes the union of the baselines and inherits the **highest tier in
full** — so this tree is Group 5's service, **uplifted to the
FedRAMP High baseline**, extended by this group's spec sheets. The
uplift analysis below names what the High baseline demanded beyond
the L2 core.

## How functions were counted

Group 5's fixed 26-function taxonomy for this category was matched
against each offering's own public description using Group 5's
matcher **verbatim** — patterns and all eleven wording-artifact
corrections unchanged (driver at `scratch/extract_l3.py`). A
function is claimed for a fork **only** when the description
contains matching text; the matching sentence is stored as the
claim's evidence in the spec sheet (verified programmatically: every
evidence string appears verbatim in its fork's description, 0
violations).

**This group's claim mass is 2 claims total**, and the spec records
that plainly rather than repairing it:

- **Trenchant Analytics — AI for Federal Acquisitions (ACQBOT)**
  carries **2 claims** (`workflow_approvals`, `ai_analytics`), both
  from one sentence: "ACQBOT uses the latest Large Language Model
  (LLM) generative capabilities paired with intuitive workflows and
  Robotic Process Automation (RPA) to connect a government
  AI-Powered acquisition system with an industry AI-Powered proposal
  platform." Both families are Extended in this build (below).
- **Citrix Systems, Inc. — Citrix for Government - High** is a
  **zero-claim sheet**: no taxonomy pattern fires on its description,
  which is sovereign-cloud and virtual-workspace prose. The full text
  is preserved in its spec sheet; nothing was invented for it.

Near-misses were observed and deliberately **not** corrected (the
matcher stays verbatim so cross-group counts remain comparable):
Citrix's "secure access", "security controls", and "centralized
administration" do not fire `access_control` / `risk_controls` /
`api_integration`, whose patterns require their own phrasing;
ACQBOT's "solicitation, award, and contracting processes" does not
fire `govcon_grants`, because Group 5's documented correction treats
bare "government contractors" as customer-eligibility phrasing, not
a GovCon-accounting claim.

**Group character, stated plainly:** at High, the Accounting
category in the source is largely a categorization artifact. Neither
member describes an accounting system: one is an AI acquisition
platform, the other a sovereign cloud / DaaS enclave (compare Group
6's enclave character and Group 15's source-category finding). The
descriptions are short, and all counts are a **floor**.

**Core-boundary decision (recorded, overridable):** the 13 Core
functions below tag **zero claims in this group**, and they stay
Core. The Merge Rule carries the L2 union upward whole; the merged
baseline's functions are not re-litigated per group, and a wording
artifact is not a downgrade (the Group 6 / Group 22 precedent).
Group 5's own wording note carries with it: no sibling in either
group says "general ledger" or "double-entry" — the double-entry
journal is Core as the defining mechanism of the `accounting_core`
claim family, and standalone payables/receivables modules were not
invented there and are not invented here.

## Money representation (carried from Group 5, unchanged)

All monetary values are **integer cents**. Every amount field is
named `*_cents` and must be a Python `int` — booleans are rejected,
and floats are rejected even when integral, so no binary
floating-point value can ever enter a total. All arithmetic is
integer arithmetic and therefore exact by construction.

## Function ranking — this group's 2 siblings

Dispositions are the function's disposition in **this** build:
Core functions are Group 5's, carried up whole and uplifted;
Extended functions are specified, not implemented.

| # | Function | Siblings claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | AI, analytics & business intelligence | 1 (ACQBOT) | Extended (the reporting in Core is exact computed statements, not AI/BI analytics) |
| 2 | Workflow & approvals | 1 (ACQBOT) | **Core** (carried: the approval state machine shared by entries, invoices, expenses, with separation of duties) |
| 3 | APIs, integrations & interoperability | 0 | **Core** (carried: the service is API-first) |
| 4 | Financial reporting & statements | 0 | **Core** (carried) |
| 5 | Reconciliation, settlement & financial close | 0 | **Core** (carried) |
| 6 | Core accounting & financial management | 0 | **Core** (carried: chart of accounts + double-entry journal) |
| 7 | Budgeting, planning & cost management | 0 | **Core** (carried) |
| 8 | Audit trail & audit management | 0 | **Core** (carried, uplifted: the hash-chained audit trail; audit-*management* workbenches are Extended) |
| 9 | Invoicing & billing | 0 | **Core** (carried) |
| 10 | Access control & authentication | 0 | **Core** (carried, uplifted: High baseline hooks, auditor role, lockout — see below) |
| 11 | Payment processing, purchase cards & disbursements | 0 | **Core** (carried: payments as records applied to invoices; no card networks or payment gateways) |
| 12 | Expense management & travel | 0 | **Core** (carried: expense records with approval; travel *booking* not included) |
| 13 | Project, program & portfolio management | 0 | Extended (carried) |
| 14 | Risk management & internal controls | 0 | Extended (carried: SoD, approval-required posting, and the audit trail in Core are the seed) |
| 15 | Fixed assets, property & fleet management | 0 | Extended (carried) |
| 16 | Records, document management & retention | 0 | Extended (carried) |
| 17 | Forecasting & enterprise performance management (EPM) | 0 | Extended (carried) |
| 18 | Supply chain, warehouse & logistics | 0 | Extended (carried) |
| 19 | Grants, federal aid & GovCon accounting | 0 | Extended (carried; ACQBOT's acquisition prose is a recorded near-miss, not a claim) |
| 20 | Cryptocurrency & blockchain investigation | 0 | Extended (carried) |
| 21 | Time tracking & scheduling | 0 | Extended (carried) |
| 22 | Electronic & digital signatures | 0 | Extended (carried) |
| 23 | Payroll & labor | 0 | Extended (carried) |
| 24 | Tax reporting & support | 0 | Extended (carried) |
| 25 | Forensic accounting & financial investigation | 0 | Extended (carried) |
| 26 | Encryption | 0 | Platform note (TLS when configured; see baseline section) |

**Differences are preserved, not averaged away**: the two members'
actual domains — AI-powered federal acquisition (ACQBOT) and
sovereign cloud / virtual workspaces (Citrix) — are recorded in
their spec sheets and in the Extended/vertical notes, not forced
into accounting buckets.

## The Core — what the merged build implements (13 functions, at High)

Carried whole from Group 5 (see `../accounting-l2/UNION-SPEC.md`
for the full per-function text); in brief:

1. **Books & members** — named books (the fiscal container) with an
   owner, a member list, and provenance; membership is the boundary
   every other core function enforces.
2. **Chart of accounts** — accounts with a code unique per book, a
   name, and a type (`asset`, `liability`, `equity`, `revenue`,
   `expense`) fixing the normal-balance direction.
3. **Double-entry journal & ledger posting** — entries of
   debit/credit lines; every entry must balance in exact integer
   cents or it is rejected whole; drafted, submitted, and **approved
   by someone other than their creator** (separation of duties)
   before posting; only posted entries touch balances and reports;
   a posted entry is never edited or voided — the correction is a
   reversing entry.
4. **Invoicing & billing** — line items with totals computed by the
   build, never trusted from the caller; the same approval machine;
   `issued` on approval.
5. **Payments** — recorded against an issued invoice and applied to
   its balance; partial allowed, overpayment rejected, fully paid
   becomes `paid`. Payments are records, not payment rails.
6. **Expenses** — expense records running the same approval machine;
   an approved expense can be marked reimbursed.
7. **Budgets** — per book per fiscal period (`YYYY-MM`), with
   budget-vs-actual against posted ledger movement.
8. **Reconciliation & period close** — reconcile an account against
   a stated expected balance; closing a period locks the ledger for
   that period.
9. **Financial reporting** — from posted entries only: trial balance
   (the `balanced` flag computed from the rows), income statement,
   balance sheet (balanced flag computed, not asserted), per-account
   balance and activity.
10. **Workflow & approvals** — the shared state machine
    (`draft → pending → posted` / `issued` / `approved`, plus
    `rejected` and `void`) with separation of duties throughout.
11. **API access** — every function above over a REST API (JSON).
12. **Access control** — platform roles `admin`, `member`, `viewer`
    plus **`auditor`** [L3], permission matrix enforced on every
    operation, layered with book membership; unsuccessful-logon
    lockout at the service layer (uplift, below).
13. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail with audit query/reduction, chain verification, and
    fail-closed write behavior (uplifts, below); every mutation and
    every denied attempt recorded.

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. Both parent forks sit at High, and the
  cross-tier parent (Group 5's build) sat at Moderate; the union
  baseline is therefore the High baseline, un-diluted (Merge
  Rule 1), inherited in full (Merge Rule 2). "Adjacent" remains
  deliberate wording, as in the crosswalk: L3 is not identical to
  FedRAMP High; it is the same assurance weight class.
- **Feature → control family mapping (carried from Group 5):**
  - Access control (platform roles + book membership) → **AC**
    (AC-2, AC-3, AC-6), **IA** (IA-2 — identity is supplied by the
    embedding organization via user/role headers; hooks, not an
    identity provider).
  - Workflow & approvals → **AC-5** (separation of duties — the
    approver of an entry, invoice, or expense is never its creator,
    enforced in the store).
  - Audit log → **AU** (AU-2, AU-3, AU-6, AU-9). Reconciliation
    records and period closes are audit records in the same trail.
  - Journal / invoices / expenses / payments / budgets → **SI**
    (SI-10 — malformed input, including any non-integer or
    unbalanced amount, is rejected whole, never partially applied)
    and **SC** (SC-8 — TLS when a certificate is configured;
    encryption at rest is deployment-layer, stated, not claimed).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole mutation (no object created, no id consumed, state exactly as before) and the service never reports success for an unaudited operation |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service (named-username authentication failures only); lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Group 5, restated because High demands more of the IdP layer) |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module; not claimed |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `accounting` under
`src/`, runnable and testable with `PYTHONPATH=src`. The contract
is Group 5's (see `../accounting-l2/UNION-SPEC.md`), unchanged
except for the uplift deltas marked **[L3]**:

- `accounting/errors.py` — Group 5's four errors, plus **[L3]**
  `AuditWriteError` (deriving from `AccountingError`).
- `accounting/access.py` — roles `admin|member|viewer|auditor`
  **[L3]**; `PERMISSIONS` as Group 5, plus **[L3]** `auditor =
  {audit_read}` and nothing else.
- `accounting/audit.py` — `AuditLog(path=None)`; `.record(...)` →
  entry dict with Group 5's keys plus **[L3]** `seq, prev_hash,
  hash` (SHA-256 of the canonical JSON of `{seq, ts, actor, action,
  target, details, prev_hash}`); raises **[L3]** `AuditWriteError`
  and rolls back if the JSONL write fails. `.entries()` returns all
  entries. **[L3]** `.query(actor=None, action=None, target=None,
  since=None, until=None)` returns filtered entries (`since`/`until`
  are lexicographic ISO-string comparisons, inclusive on both ends);
  `.verify_chain()` returns `(ok, first_bad_index_or_None)`.
  Append-only; optional JSONL file; loaded entries participate in
  chain verification.
- `accounting/store.py` — as Group 5; **[L3]** every mutating
  method is fail-closed: if the audit write raises
  `AuditWriteError`, the whole mutation rolls back (no object
  created, no id consumed, state exactly as before the call) and
  the error propagates.
- `accounting/service.py` — `make_server(host, port, store, audit,
  users, max_failures=3, lockout_seconds=300)` **[L3 kwargs]**.
  Endpoints as Group 5, plus **[L3]** `GET /audit` filter params
  `actor, action, target, since, until`, and **[L3]**
  `GET /audit/verify` → `{ok, entries, first_bad_index}`
  (audit_read). **[L3]** consecutive named-username authentication
  failures are tracked per username; at `max_failures` the username
  locks for `lockout_seconds` (403, audited `auth:locked`); success
  resets. The `/audit` handlers preserve Group 5's convention: the
  entries are read before the handler's own `audit_read` is
  recorded, so a read does not appear in its own response.
- `accounting/__main__.py` — `python -m accounting serve --host
  --port [--audit-log PATH] [--certfile --keyfile]
  [--max-failed-logins N] [--lockout-seconds S]` **[L3 flags]** with
  demo users `alice=admin, bob=member, carol=viewer, dana=auditor`
  **[L3]** (documented as demo identities; production identity is
  the embedding organization's).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to. **273 tests**: the 219 Group 5 tests (inherited; four files
adapted for the uplift — adaptations listed in `tests/README.md`)
plus 54 new tests covering the chain, audit query, fail-closed
rollback, lockout, and the auditor role. Two **negative controls**,
both mutation-verified with the drills recorded in
`tests/README.md`:

1. The balance-check mutant (carried from Group 5): patching the
   real balance check in `store.py` so it never compares the debit
   and credit sums made the suite fail (**4 failures** — the same
   defect surface as Group 5); the file was restored and SHA-256
   verified identical, and the suite returned to green. The
   canonical expectation is also demonstrated in-suite: an
   unbalanced entry must raise `ValidationError` from the real
   store and store nothing.
2. **[L3]** Audit tamper: mutating a stored audit entry in place
   makes `verify_chain()` report failure at exactly that entry's
   index — demonstrated for a rewritten actor, a stripped `hash`,
   a rewritten `prev_hash`, an edited JSONL line after reload, and
   over HTTP via `GET /audit/verify`.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (2 claims total; 1 zero-claim sheet,
  recorded above).
- Core: 13 core functions implemented, at the High baseline, each
  with tracing tests; 6 tier uplifts implemented (hash-chained
  audit, fail-closed audit writes with store rollback, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor role).
- Extended: the functions specified and ranked, **not** implemented
  in this build — the same families as Group 5 (AI/analytics & BI
  — this group's only claimed Extended family, 1 of 2 forks;
  project/program/portfolio management, risk register & GRC beyond
  the SoD/audit seed, audit-management workbenches, fixed-asset
  registers, records retention beyond the audit seed, forecasting
  & EPM, supply chain, GovCon/grants specifics, crypto
  investigation, time tracking, e-signature, payroll, tax support,
  forensic investigation); encryption is a platform note (TLS when
  a certificate is configured; at rest is deployment-layer). The
  two members' own domains (an LLM/RPA acquisition platform; a
  sovereign cloud / DaaS enclave) are likewise not built here —
  they belong to their own categories' groups, and this group's
  union is the accounting substrate at High.
- Baseline gaps named, not implied closed: MFA/authenticator
  management (IA-2(1)/(2), IA-5 — IdP layer), FIPS-validated crypto
  (SC-13), encryption at rest (SC-28), audit retention enforcement
  (AU-11), session lock/termination (AC-11/AC-12).
