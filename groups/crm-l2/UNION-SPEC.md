# Union Spec — Customer Relations Management (CRM), CMMC L2 (DeadRamp Phase 2, Group 25)

The merged functional spec for the CRM sibling group at the L2 tier:
**2 forks, all FedRAMP Moderate**, reconciled zero-diff three ways
(`specs/specs.json` ↔ `forks.json` category="Customer Relations
Management (CRM)" + cmmc_tier="L2" ↔ MAP.md "Customer Relations
Management (CRM) — L2 (2)").

The group: Oracle Service Cloud (OSvC) (Oracle) · WalkMe DAP
(WalkMe, Inc).

**This group is two products that share a category label more than a
function, and the spec says so plainly.** One is a customer-service
platform (Oracle Service Cloud, FedRAMP Certified since 2014); the
other is a digital-adoption overlay (WalkMe DAP, Agency Authorization
In Process) whose cached marketplace record carries an **empty**
business_categories list and reaches this category through its
filter_classes string, where CRM is the first of ~11 business
functions. Neither description mentions sales, opportunities,
pipelines, leads, or campaigns — the classic sales-CRM surface is
simply absent from this group's public record. What the two claimed
surfaces share, and what the build implements, is a **CRM records
substrate**: accounts and contacts keyed by opaque references,
service cases with a stage lifecycle, interaction records, guidance
content records, gap-finding records, a module/configuration
registry, and reports, search, access control, and an audit trail
over all of it. Each vendor's engine on top of that substrate is an
Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against an 18-family taxonomy defined from this
category's descriptions. A family is claimed only when the offering's
own description contains matching text; the first matching sentence
is stored in `specs/specs.json` as evidence, so every claim is
auditable. **8 claims total, no fork at zero.** Per-fork claim
counts: Oracle Service Cloud (OSvC) 3, WalkMe DAP 5.

Wording-artifact discipline (full record in `scratch/ARTIFACTS.md`):
no raw hit was removed after tagging; the corrections are scoping
decisions that kept false hits out of the count. Bare "customers" in
both descriptions names the population served, not an
account/contact registry, so that family tags 0 of 2 and enters the
Core as substrate (below). WalkMe's overlay prose ("adapts software
and websites... without changes to your underlying platforms") is
integration-adjacent but asserts no integration function, so
integrations tags 0 of 2 — a recorded near-miss. Two kept claims
carry recorded thin bases: WalkMe's engagement_tracking rests on
outcome prose ("streamlining productivity and engagement"), not an
analytics-engine assertion; Oracle's case_service_records rests on
"customer service platform" plus "customer service agent-facing
functions" in the same description.

## Function ranking — both siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 2 | Modules, customization & codeless configuration | **Core** — module/configuration registry (records); customization engines Extended |
| 1 | 2 | Hosting / SaaS delivery platform | Platform layer — asserted in prose by both; the hosting platform itself is not a function of this build |
| 3 | 1 | Customer service cases & service platform | **Core** — case records & lifecycle substrate; casework depth Extended |
| 3 | 1 | User guidance & digital adoption | **Core** — guidance content registry (records); the in-app delivery runtime is Extended |
| 3 | 1 | Gap & problem-area identification | **Core** — finding records, text verbatim; the identification engine is Extended |
| 3 | 1 | Engagement & productivity tracking | Core (records) — engagement exists in the build only as interaction records; analytics engines Extended. Thin basis recorded |
| 7 | 0 | Account & contact records | **Core** (substrate) — 0 tagged claims; core-boundary decision below |
| 7 | 0 | Interaction & activity records | **Core** (substrate) — 0 tagged claims; the record type both claimed surfaces produce |
| 7 | 0 | Reporting & dashboards | Core (registry reporting); dashboard/analytics engines Extended |
| 7 | 0 | Access control & RBAC | **Core** (baseline substrate) — carried, not claimed |
| 7 | 0 | Audit logging | **Core** (baseline substrate) — carried, not claimed |
| 7 | 0 | Search | **Core** (registry mechanics) — carried, not claimed |
| 7 | 0 | Opportunities & sales pipeline | **Named absence** — 0 of 2; not built, not a gap (unclaimed) |
| 7 | 0 | Campaigns & audience lists | **Named absence** — 0 of 2; not built, not a gap (unclaimed) |
| 7 | 0 | Knowledge base & self-service content | Extended — named at 0 claims here |
| 7 | 0 | Marketing automation & email delivery | Extended — named at 0 claims here |
| 7 | 0 | AI/ML models & scoring | Extended — named at 0 claims here |
| 7 | 0 | Integrations & interoperability | Extended — connector engines; near-miss recorded, 0 claims |

**Core-boundary decision (recorded, per the Group 10/15/24
precedent).** Two families tag zero claims yet stand in the Core as
substrate: the account/contact registry and interaction records. The
reasoning is the category's own: a "customer service platform" with
"customer-facing and customer service agent-facing functions"
(Oracle) and a platform serving "employees, customers & citizens"
(WalkMe) both presuppose account/contact records as their object
model, and both claimed surfaces (agent-facing service work,
guidance sessions) produce interaction records. The taxonomy was
deliberately NOT re-tuned to manufacture claims for them; the counts
above stay a stated floor, and these two functions are flagged
carried, not claimed, everywhere they appear.

**Named absences.** Opportunity/pipeline and campaign/list families
are claimed by **0 of 2** siblings — no sales vocabulary exists in
either description. They are recorded here so the union is complete
and the absence is provable from the record; they are not built and
they are not gaps, because nothing was claimed (the Group 21
precedent). If a future sibling in this category claims them, they
enter through its spec.

## The Core — what the merged build implements (10 functions)

1. **Account & contact registry** — accounts (`acct-`) and contacts
   (`ct-`, each under an account) keyed by a required, unique,
   **opaque caller-supplied `reference`**, with an optional
   caller-chosen `label` and free-form attributes. Substrate (see
   the core-boundary decision).
2. **Service case records & lifecycle** — cases (`case-`), typed
   (inquiry/problem/request/feedback/general), with account/contact
   links (a contact linked with an account must belong to it),
   an opaque `assignee_ref`, priority, and an optional `due_at`.
   Lifecycle `open → in_progress → resolved → closed` (plus
   `cancelled`; `resolved` may reopen). Breach is **derived at
   read time, never stored**:
   `breached = now > due_at and status not in (resolved, closed, cancelled)`.
   Claims basis: case_service_records (Oracle).
3. **Interaction & activity records** — immutable records (`int-`)
   across guidance_session/call/chat/email/portal/in_person/system
   channels, with direction, outcome, summary, `external_ref`
   passthrough, and account/contact/case/guide links. No update or
   delete API exists.
4. **Guidance content registry** — guides (`guide-`): title, kind
   (walkthrough/tooltip/checklist/announcement), an opaque
   `target_ref` naming the host surface, steps, enabled flag,
   versioned on update with full version history. Records only —
   the build renders nothing into any application. Claims basis:
   guidance_adoption (WalkMe).
5. **Gap-finding records** — findings (`find-`): title, `detail`
   text stored **verbatim** as supplied, severity, source, optional
   account link, lifecycle `open → acknowledged → addressed` (plus
   `dismissed`). This build stores findings; no score is computed
   or stored anywhere, and no aggregate the claims do not define is
   produced. Claims basis: gap_identification (WalkMe).
6. **Module / configuration registry** — modules (`mod-`): label,
   scope, `settings_text` stored verbatim (never executed),
   enabled flag, versioned on update. Writes are **admin-only**.
   Claims basis: configuration_extensibility (both siblings).
7. **Reports** — deterministic counts over the registry's own
   records: cases by status/type/account plus breached count at the
   report's `now`, interactions by channel/outcome, guides by
   kind/enabled, findings by severity/status, module and registry
   totals. Counts of records only — no scoring aggregate exists.
8. **Search** — literal case-insensitive substring search over
   accounts/contacts (label + reference), cases, interactions,
   findings, and guides.
9. **REST API** — the full surface over HTTP, with the house auth
   convention (X-User/X-Role against a demo registry; 401
   unknown/mismatched, 403 permission, denied attempts audited).
10. **Access control (RBAC) + audit log** — admin/operator/viewer
    matrix over 14 actions; `config_write` and `audit_read` are
    admin-only; enforced in the store before any mutation or id
    allocation, and again at the service layer. The audit log is
    append-only, JSONL-persistable, and records every mutation and
    every denied attempt (`<action>:denied`). Baseline substrate,
    carried not claimed.

**Privacy discipline (hard rule of this build).** Accounts and
contacts are keyed by opaque caller-supplied references only. No
entity in this build has a field that can hold a real name, email,
phone number, SSN, date of birth, address, or salary figure — the
shapes are enforced by tests (`tests/test_privacy.py`), which also
assert that no score field and no scoring aggregate exists anywhere
in the build.

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline
is the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the
110 practices of **NIST SP 800-171** behind CMMC L2, per
`crosswalk.md`. No parent carried a higher or lower baseline, so
the merge changes no tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Account/contact registry | AC-3, AC-6, IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness and account linkage are enforced in the store |
| Cases & lifecycle | AU-2, CM-6, SI-12 (partial) | Every case transition is an auditable event under a configured lifecycle; retention/disposition engines are Extended |
| Breach derivation | AU-6, CA-7, CM-6 | Breach is derived at read from `due_at` and status against the report's `now`, never stored — reviewable and reproducible |
| Interactions | AU-2, AU-3, SI-12 (partial) | Immutable interaction records with content; review/search over them is Core, retention engines Extended |
| Guides registry | CM-6, SA-4 | Guides are versioned configuration records, acquired and managed as configuration, never executed or rendered by this build |
| Findings | AU-2, AU-6, SI-12 (partial) | Finding records are stored verbatim with lifecycle; identification engines are Extended |
| Modules registry | CM-6, SA-4 | Modules are versioned configuration records; settings text is stored, never executed |
| Reports | AU-6 | Deterministic counts over the records, including derived breach at a stated `now`; no scoring aggregate |
| Search | AU-6, SI-12 (partial) | Literal search over records supports review; retention/disposition is partial and Extended |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers; `config_write`/`audit_read` admin-only |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source
implementation whose features trace to the Moderate/L2 control
families. FedRAMP authorizes products; CMMC certifies
organizations — neither regime accepts the other as evidence, and
any real compliance claim still has to be earned inside each regime
separately.

## Implementation contract (summary)

`src/crm/` (Python stdlib only): `errors` (`CrmError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, role matrix), `audit` (append-only AuditLog), `store`
(CrmStore: the 10 core functions; failed operations consume no ids;
permission checks precede mutation), `service` (HTTP layer, demo
registry), `__main__` (`python -m crm serve`). `tests/`: see
tests/README.md for the test count and the negative-control record
(the count is filled in from the build, not stated here).

## Coverage statement (for this build)

- Forks spec'd: **2 / 2**, each with evidenced claims (8 total).
- Core implemented: **10 / 10** functions above.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Customer-service casework depth: knowledge-driven agent desktops,
  self-service portals, chat/chatbot channels, customer-facing
  engagement surfaces (Oracle Service Cloud).
- Guidance delivery runtime: the in-application overlay engine that
  renders guidance inside third-party software and websites,
  including codeless authoring tooling (WalkMe DAP).
- Gap-identification & adoption-analytics engines: live usage
  telemetry collection, gap/problem-area detection, engagement
  analytics and reporting beyond record counts (WalkMe DAP).
- Customization & module engines: add-on module execution,
  codeless configuration runtimes (both siblings' prose).
- Knowledge base & self-service content (0 claims in this group).
- Marketing-automation engines & email delivery (0 claims here).
- AI/ML models & scoring (0 claims here; no score is computed
  anywhere in the core, by design).
- Integration connector engines (0 claims here; near-miss recorded
  in scratch/ARTIFACTS.md).

Platform layer (gap-listed, never implied closed): multi-tenancy
(the build is a single-tenant reference deployment); encryption at
rest (deployment layer); TLS only when a certificate is
configured; demo identities are hooks, not an IdP — IA-2 stays
with the embedding organization. The hosting/delivery platform both
siblings assert in prose is the deployment layer itself, not a
function of this build.

**Privacy note:** this build stores records and opaque
caller-supplied references only — no real names, emails, phone
numbers, or other identifiers exist in any entity shape, and
finding details are stored verbatim, never scored.
