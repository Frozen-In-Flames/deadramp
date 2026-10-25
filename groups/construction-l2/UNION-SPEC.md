# Union Spec — Construction, CMMC L2 (DeadRamp Phase 2, Group 19)

The merged functional spec for the Construction sibling group at the L2
tier: **4 forks, all FedRAMP Moderate**, reconciled zero-diff three ways
(`specs/specs.json` ↔ `forks.json` category="Construction" +
cmmc_tier="L2" ↔ MAP.md "Construction — L2 (4)").

The group: Actsoft Workforce Manager for Gov. (Actsoft, Inc) ·
Contract Insight (CobbleStone Software) · Gordian Federal Cloud
powered by RSMeans Data (Gordian) · LCPtracker Pro (LCptracker Inc).

**This group is substantially a source-category artifact, and the
spec says so plainly.** Only one of the four — Gordian — is a
construction platform in the classic sense, and only one —
LCPtracker — carries "Construction" in its source
business_categories; the other three records have empty
business_categories lists and sit in this category per the Phase 1
registry. In substance the four are a mobile field-workforce platform
(Actsoft), a contract lifecycle management platform (CobbleStone), a
construction cost-data and estimating platform (Gordian), and a
prevailing-wage and workforce compliance platform (LCPtracker).
There is no single product they all are. What they share, and what
the claim counts below prove, is a **records substrate**: projects
executed by tiered contractor workforces, under contracts with
lifecycles and key dates, with document, cost, workforce, and
compliance records, and reporting over all of it. The merged build
implements that substrate; each vendor's engine on top of it is an
Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was segment-split
(lines, then sentences) and matched against a 23-family taxonomy
defined from this category's descriptions. A family is claimed only
when the offering's own description contains matching text; the first
matching segment is stored in `specs/specs.json` as evidence, so
every claim is auditable (all evidence verified verbatim against the
descriptions programmatically, 0 violations). **25 claims total, none
removed after the fact**: every wording-artifact correction was
applied by scoping the taxonomy before counting, and all are
documented in `scratch/ARTIFACTS.md`. The load-bearing ones:
CobbleStone's bare "security" never tags identity & access control
(0 claims for that family); Actsoft's driver "score cards" never tag
safety-incident records (fleet telematics, 0 claims); Gordian's
"pricing proposals" was deliberately excluded from financial
tracking, which rests on CobbleStone's explicit "Track financials to
control spend" only. Two kept claims carry recorded thin bases:
Actsoft's compliance claim is addressing-language ("addresses key
market challenges such as … worker compliance"), and Gordian's
project claim rests on "Job Order Contracting". **No fork has zero
claims.** Per-fork claim counts: CobbleStone Contract Insight 9,
Actsoft Workforce Manager for Gov. 7, LCPtracker Pro 6, Gordian
Federal Cloud 3.

## Function ranking — all 4 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 2 | Project & job-order records | **Core** |
| 1 | 2 | Contract lifecycle management | **Core** (records & lifecycle); CLM workflow engine Extended |
| 1 | 2 | Documents, forms, templates & clauses | **Core** (document registry & versions); template/clause libraries Extended |
| 1 | 2 | Workforce records & timekeeping | **Core** |
| 1 | 2 | Prevailing-wage & workforce compliance records | **Core** (payroll records, violations, derived compliance status); determination depth Extended |
| 1 | 2 | Search, reporting & analytics | **Core** (records substrate); analytics engines Extended |
| 1 | 2 | Workflow & process automation | Extended — engines; lifecycle state machines are the in-core seed |
| 1 | 2 | Multi-tenant deployment | Platform property — not a function (see gaps) |
| 9 | 1 | Contractor & subcontractor participation | **Core** (project participants with tiers) |
| 9 | 1 | Job dispatch & assignment | **Core** (dispatch records); routing/optimization Extended |
| 9 | 1 | Financial & spend tracking | **Core** (cost records & project cost summary) |
| 9 | 1 | Key-date alerts & notifications | **Core** (alerts derived from key dates & derived states); delivery transport is deployment-layer |
| 9 | 1 | Cost data & estimating | Extended — estimating engine & proprietary cost data; estimate *records* Core (cost entries of kind `estimate`) |
| 9 | 1 | GPS & location tracking | Extended — live tracking platform |
| 9 | 1 | Fleet & vehicle telematics | Extended — telematics platform |
| 9 | 1 | Electronic signatures | Extended — signature execution |
| 9 | 1 | AI/ML capability | Extended — AI data extraction & negotiation models |

**Carried families — 0 claims in this group, named so the union is
honest.** Six families tag no description in this group. Two are
baseline substrate every DeadRamp build carries (identity & access
control, audit logging). Four are the record types the Construction
category itself is defined by — submittal & RFI records, schedule &
milestone records, inspection & punch-list records, and
safety-incident records — and are **carried into the Core as
substrate, recorded as carried, not claimed**: a contract lifecycle,
a compliant tiered workforce, and tracked spend all execute against
projects whose work moves through submittals, milestones,
inspections, and incident records. The taxonomy was deliberately
not re-tuned to manufacture claims for them.

## The Core — what the merged build implements (17 functions)

1. **Organizations & participation** — organization records (`org-`)
   with opaque references, and project participation records tying an
   organization to a project at a contractor tier (1 = prime, 2+ =
   subcontractor tiers; LCPtracker's "even down to the lower-tier
   subcontractors").
2. **Projects** — project records (`prj-`) with a
   `planned → active → on_hold → completed → closed` lifecycle (plus
   cancellation), agency reference, location, and start/end dates.
3. **Documents** — a document/drawing registry (`doc-`: drawings,
   specifications, contracts, submittals, forms, reports) with full
   version history; each version carries a caller-supplied content
   checksum. The registry holds records and checksums only, never
   document content (the Group 17 pattern).
4. **Contracts** — contract records (`con-`) with counterparty,
   integer-cent value, key dates, and a
   `draft → in_review → executed → active → completed → closed`
   lifecycle (plus termination). **Expiry state is derived at read
   time, never stored**: `pre_execution` / `open_ended` / `active` /
   `expiring` (≤ 30 days) / `expired` / `ended`, with a signed
   `days_to_expiry`.
5. **Submittals & RFIs** — submittal records (`sub-`) with a
   `draft → submitted → under_review → approved / approved_as_noted /
   revise_resubmit / rejected` lifecycle, and RFI records (`rfi-`,
   `open → answered → closed`). Overdue state is **derived at read**
   from `due_at` for any non-terminal record.
6. **Schedule & dispatch** — milestone records (`ms-`) with a
   **due state derived at read** (`upcoming` / `due_soon` ≤ 7 days /
   `overdue` / `completed`), and dispatch records (`dsp-`) with an
   `assigned → in_progress → completed` lifecycle (plus cancellation)
   — Actsoft's Job Dispatching as records.
7. **Inspections & punch list** — immutable inspection records
   (`insp-`, with the inspector's recorded result) and punch items
   (`pun-`, `open → corrected → verified`, reopenable, overdue
   derived at read).
8. **Safety incidents** — incident records (`inc-`) with severity,
   category, and a `reported → under_review → closed` lifecycle.
   Records only; no incident-determination engine is claimed.
9. **Workforce records** — worker records (`wrk-`) keyed by an
   **opaque caller-supplied reference only** (never a real identifier),
   and immutable timekeeping entries (`time-`) in integer minutes —
   Actsoft's Timekeeping and LCPtracker's worker information as
   records.
10. **Payroll & compliance** — certified-payroll records (`pay-`,
    immutable, integer-cent wage totals) and violation records
    (`vio-`, admin-only writes). **Contractor compliance status is
    derived at read time, never stored**, by a single derivation
    point: an open violation ⇒ `noncompliant`; else a certified
    payroll on file ⇒ `compliant`; else `no_records`.
11. **Costs** — cost records (`cost-`) of kind budget / estimate /
    change_order / actual, all amounts integer cents (floats and
    bools rejected at the boundary), plus a per-project summary whose
    totals and variance are derived at read.
12. **Derived alerts** — alert records computed at read time from key
    dates and derived states: contract expiring/expired, milestone
    overdue, submittal/RFI/punch overdue, participant noncompliant,
    participant with no compliance records. Deterministic content and
    ordering; nothing is stored.
13. **Reports** — deterministic aggregates at the caller's `now`:
    projects by status, contracts by status and derived expiry
    state, milestones by derived due state, overdue counts, incident
    counts, compliance counts over all project participants, and
    cost totals with variance.
14. **Search** — literal case-insensitive substring search over
    projects, organizations (name + reference), documents, and
    contracts.
15. **REST API** — the full surface over HTTP, with the house auth
    convention (X-User/X-Role against a demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
16. **Access control (RBAC)** — admin/operator/viewer matrix over 17
    actions; `violation_write` and `audit_read` are admin-only;
    enforced in the store before any mutation or id allocation, and
    again at the service layer.
17. **Audit log** — append-only, JSONL-persistable, recording every
    mutation and every denied attempt (`<action>:denied`).

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes
no tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Organizations, projects, participation | AC-3, AC-6, IA-2 (hooks) | Parties and tiers are explicit records; participation is computed from them, never assumed |
| Documents & versions | CM-6, SI-12 (partial), SC-28 (partial) | Versioned registry with content checksums; retention/disposition engines are Extended |
| Contracts & key dates | AU-2, CM-6 | Every transition is an auditable event under a configured lifecycle; expiry is derived, reviewable, reproducible |
| Submittals, RFIs, milestones, dispatches | AU-2, CA-7, CM-6 | Lifecycle records with overdue/due state derived at read from stored dates against the caller's `now` — never stored |
| Inspections, punch items, incidents | AU-2, AU-3, SI-12 (partial) | Immutable inspection records; punch and incident lifecycles are auditable events |
| Workforce & timekeeping | AU-2, IA-2 (hooks), SI-12 (partial) | Worker records carry opaque references only; time entries are immutable records |
| Payroll, violations, compliance derivation | AU-6, CA-2, CA-7 | Compliance status is derived at read from payroll and violation records by one named derivation point; the derivation is the assessment record |
| Costs | AU-6, SA-4 (partial) | Integer-cent records; summaries and variance derived at read, never stored |
| Derived alerts & reports | AU-6, CA-7 | Alerts and reports are deterministic functions of the records at a stated `now` |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers; `violation_write`/`audit_read` admin-only |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source implementation
whose features trace to the Moderate/L2 control families. FedRAMP
authorizes products; CMMC certifies organizations — neither regime
accepts the other as evidence, and any real compliance claim still
has to be earned inside each regime separately.

## Implementation contract (summary)

`src/construct/` (Python stdlib only): `errors` (`ConstructError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, role matrix), `audit` (append-only AuditLog), `store`
(ConstructStore: the 17 core functions; failed operations consume no
ids; permission checks precede mutation; derived values computed in
exactly three named points — `_contract_expiry_state`,
`_record_overdue` / `_milestone_due_state`, and
`_contractor_compliance`), `service` (HTTP layer, demo registry),
`__main__` (`python -m construct serve`). `tests/`: see
tests/README.md for the test count and the negative-control record
(the count is filled in from the build, not stated here).

Interpretations recorded where the contract was silent: the report's
`punch_items.open` counts status literally `open`; compliance alerts
use the participant's `org_id` as `ref_id`; `key_dates` entries are
validated for a non-empty `label` and ISO `at` and stored as supplied.

## Coverage statement (for this build)

- Forks spec'd: **4 / 4**, each with evidenced claims (25 total).
- Core implemented: **17 / 17** functions above.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Cost estimating engines and the proprietary RSMeans cost data
  (Gordian) — estimate *records* are Core; the data and the engine
  are the vendor's.
- GPS / location tracking platform and mobile field data collection
  (Actsoft) — dispatch and form *records* are Core.
- Fleet & vehicle telematics — vehicle monitoring, idling/stop-time
  analytics, driver behavior score cards (Actsoft).
- Contract lifecycle workflow engines, template & clause libraries,
  and negotiation playbooks with redlining (CobbleStone) — contract
  records and lifecycle are Core.
- E-signature execution (CobbleStone).
- AI/ML models — AI data extraction and negotiation assistance
  (CobbleStone, 1 claim).
- Workflow / process automation engines (2 claims; lifecycle state
  machines are the in-core seed).
- Prevailing-wage determination depth — rate tables, fringe-benefit
  calculation, certified-payroll generation and e-filing
  (LCPtracker) — payroll records and the derived compliance status
  are Core.
- Dispatch routing & optimization (Actsoft) — dispatch records are
  Core.

Platform layer (gap-listed, never implied closed): multi-tenancy
(2 of 4 claim it in prose; the build is a single-tenant reference
deployment); encryption at rest (deployment layer); TLS only when a
certificate is configured; demo identities are hooks, not an IdP —
IA-2 stays with the embedding organization.

**Privacy note:** workforce records hold opaque caller-supplied
references only. The build stores no real worker identifiers, and
payroll records hold aggregate wage totals, never per-worker pay.
