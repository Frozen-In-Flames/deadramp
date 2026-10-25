# Union Spec — Governance, Risk, and Compliance (GRC), CMMC L2 (DeadRamp Phase 2, Group 33)

The merged functional spec for the GRC L2 sibling group:
**2 forks**, category **Governance, Risk, and Compliance (GRC)**,
CMMC tier **L2** (every member is FedRAMP **Moderate** in
`forks.json` — verified, so the group is single-tier and the merge
takes the group baseline in full, per Merge Rule 2). The member
list in `forks.json` was reconciled against `MAP.md`'s
"Governance, Risk, and Compliance (GRC) — L2 (2)" section with
**zero diffs**, asserted programmatically in
`scratch/extract.py`.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence. Sources:
GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined
by FedRAMP ID. No live fetching was needed: both descriptions
were present in the cached dataset.

The two siblings:

- **XBU40** (InfusionPoints, FR2525557617) — a FedRAMP **20x**
  enclave platform (SaaS, PaaS; FedRAMP Certified, 20x Class C
  Pilot) whose own functions *are* compliance automation:
  AuditShield automated evidence collection/validation, KSI
  (Key Security Indicator) monitoring/validation, continuous
  monitoring, vulnerability lifecycle management, a Trust Center
  for posture/evidence views, and the Command Center platform
  management console.
- **Constellation GovCloud (CGC)** (Merlin International,
  FR2206159758) — a PaaS hosting enclave (FedRAMP Certified,
  Rev. 5, JAB) whose business is accelerating FedRAMP ATOs for
  hosted SaaS applications: a managed service "designed to
  accelerate FedRAMP authorizations allowing Merlin SaaS
  companies to achieve a FedRAMP Authority to Operate (ATO) more
  quickly and cost-effectively".

**This group is one GRC platform and one enclave that hosts
other people's platforms, and the spec says so plainly.** XBU40
carries 12 of the group's 14 claims. CGC carries 2 — hosting and
authorization support — and **zero of the twelve GRC-function
families**. The union is therefore not an average of two GRC
products: it is the GRC records substrate XBU40's claimed
functions presuppose, which is also exactly the substrate an
authorization-acceleration enclave's hosted systems are tracked
in. The difference is preserved, not averaged away.

## How functions were counted

A fixed 14-function taxonomy for this category — defined from
XBU40's description first, then applied unchanged to both forks —
was matched against each offering's own public description. A
function is claimed for a fork **only** when the description
contains matching text; the matching sentence is stored as the
claim's evidence in the spec sheet. **14 claims total: XBU40 12,
CGC 2.** Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full record in
`scratch/ARTIFACTS.md`). The one that defines this group:

- **CGC's three hosted services are NOT CGC claims.** CGC's
  description lists Torq AI SOC Platform, QIZ, and Veeam under an
  explicit header — "**Services undergoing approval for use —
  not authorized**" — stating they are **not** authorized
  services and **not** included in the certification, recorded
  for transparency only. The extractor truncates CGC's
  description at that header before matching and asserts every
  CGC evidence string lies in its own prose. The excluded block
  is not inert: matched naively it would have added 3 false
  families (`policy_management` from QIZ, `identity_access_hooks`
  and `api_integrations` from Veeam). Those services' domains are
  named below as **out of scope, not gaps CGC owes**. The same
  discipline excludes CGC's `certified_services` record field
  (Hyperproof Gov's GRC-saturated prose is a hosted tenant's
  text, never matched — house method matches `service_desc`
  only).
- **Bare "risk" earns no tag, and neither does the category
  name.** Neither fork's own prose claims risk management;
  "risk" appears only inside the excluded hosted-services prose.
  `risk_management` tags 0 of 2 and is a named absence (below) —
  with the consequence that the Core computes **no risk
  scores** anywhere.
- **"AuditShield" earns no tag.** It is a component name. The
  `audit_support` claim rests on functional phrasing:
  "preserving artifacts and timestamps for assessor review",
  "continuously audit-ready".
- **A source category label is not a claim.** XBU40's source
  record carries `business_categories: []` while `forks.json`
  files it under GRC; CGC's carries the GRC category. Both facts
  are recorded as-is in the spec sheets.

## Function ranking — both siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Assessment & authorization support | 2 | 100% | **Core** — assessment & authorization-readiness records (#6 below); package generation Extended |
| 1 | Platform hosting / enclave operations | 2 | 100% | Platform layer — the enclave/PaaS operations themselves are Extended; the Core's governed-system registry (#2) is the records substrate both platforms presuppose |
| 3 | Evidence management & validation | 1 | 50% | **Core** — evidence registry (#4); the automated validation *engine* is Extended |
| 3 | Continuous monitoring | 1 | 50% | **Core** — monitoring/validation results recorded on indicators and evidence (#3, #4); monitoring feeds Extended |
| 3 | Security indicators (KSI) tracking & validation | 1 | 50% | **Core** — indicator registry with recorded validation results (#3); automated KSI validation Extended |
| 3 | Vulnerability & remediation management | 1 | 50% | **Core** — finding/remediation (POA&M-style) records (#5); the scanning engine Extended |
| 3 | Control & framework compliance management | 1 | 50% | **Core** — framework & control catalog registry (#1) |
| 3 | Compliance posture reporting & dashboards | 1 | 50% | **Core** — posture reporting computed on read (#7), counts/summaries only, **no computed risk scores**; scoring engines Extended |
| 3 | Audit support & assessor review | 1 | 50% | **Core** — append-only audit (#10) plus assessor-facing evidence/validation records (#4, #6) |
| 3 | Identity & access controls (hooks) | 1 | 50% | **Core** — RBAC (#9); hooks only, no identity provider |
| 3 | Workflow & automation | 1 | 50% | **Core** — enforced record lifecycles (findings #5, readiness #6) are the in-core seed; automation engines Extended |
| 3 | APIs & integrations | 1 | 50% | **Core** — REST API (#8); API/telemetry evidence *collection* Extended |
| 13 | Risk management | 0 | 0% | **Named absence** — claimed by neither fork's own prose (see corrections); not built, not a gap |
| 13 | Policy management | 0 | 0% | **Named absence** — policy vocabulary exists only in the excluded QIZ prose; not built, not a gap |

Baseline families carried at **zero claims as GRC claims** but
present in the Core as L2 baseline substrate (same posture as the
sibling groups): the REST API surface, RBAC enforcement, and the
append-only audit trail are Core items #8–#10 in their own right;
here they also have partial claim support (`api_integrations`,
`identity_access_hooks`, `audit_support` each tag 1 of 2, all
from XBU40) — recorded as claimed-by-one, never inflated to two.

### The long tail — Extended, and functions named as NOT claimed

Extended functions are specified here, ranked, and **not**
implemented in this build; they are registered in the repo's gap
registry for the final batch:

- **Automated evidence-validation engine (API/telemetry
  collection)** — AuditShield's engine remainder: collecting
  evidence through APIs, serverless validation functions, and
  infrastructure telemetry, and *verifying* it automatically.
  The Core registers evidence (metadata + SHA-256) and records
  validation *results*; it runs no collection and no validation
  itself.
- **Continuous-monitoring feeds & scanner integrations** — the
  live telemetry/configuration feeds and scanner connectors
  whose outputs the Core records as validation results and
  findings. The Core ingests records; it operates no feed.
- **Vulnerability scanning engine** — the scanning remainder of
  `vulnerability_remediation`. The Core holds finding/remediation
  records with an enforced lifecycle; it scans nothing.
- **Automated KSI validation** — the engine remainder of
  `ksi_tracking`: evaluating indicators automatically against
  live posture. The Core registers indicators and records
  validation results with timestamps; the evaluation is an
  engine.
- **Posture / risk scoring engines** — any engine that computes
  a posture or risk *score*. Named Extended and also bounded by
  the named absence above: neither sibling claims risk
  management, and Core posture reporting is counts and summaries
  computed on read, with no score field anywhere by design.
- **Hosted enclave & PaaS operations themselves** — running the
  GovCloud hosting environments, platform operations and
  security operations teams, network protection and encryption
  planes both descriptions assert as platform properties. The
  Core is a single-tenant reference deployment; the enclave is
  the deployment layer, stated plainly, not claimed here.
- **FedRAMP package generation** — assembling authorization
  packages (SSP/POA&M exports and submission artifacts) from the
  Core's records. The Core holds the records a package is built
  from; it generates no package.

Named here so the category record is complete — **out of scope,
not gaps**: the domains of the three services CGC's description
lists as **not authorized and not included in its
certification**. They are other products' functions, excluded
from CGC's claim surface by CGC's own wording (see
`scratch/ARTIFACTS.md`), and this build owes none of them:

- **Torq AI SOC Platform's domain** — SOC alert triage,
  investigation, and response automation (agentic SOC).
- **QIZ's domain** — cryptography posture management:
  cryptographic discovery/inventory, CBOM production, policy
  definition and violation reporting, post-quantum transition
  planning.
- **Veeam's domain** — SaaS backup & recovery for Microsoft 365
  (immutable backups, restore operations).

Named absences (0 of 2 claims in either fork's own prose;
excluded from the union, not silently dropped, and **not**
gaps because unclaimed):

- **Risk management** — no risk register, risk tracking, or risk
  assessment sentence exists in either fork's own prose.
- **Policy management** — no policy authoring/definition/
  enforcement sentence exists in either fork's own prose.

## The Core — what the merged build implements (10 functions)

One coherent, standards-based GRC records service: **the
records substrate the claims presuppose.** Every XBU40 claim is a
statement about records being kept — evidence collected and
validated, indicators tracked, findings moved through a
lifecycle, posture shown to assessors — and every CGC claim is a
statement about systems being hosted and moved toward
authorization. The Core is the registry layer both statements
stand on. Engines that *produce* those records automatically are
Extended (above); the Core records their outputs faithfully.

1. **Framework & control catalog registry** — frameworks and
   their controls registered as catalog records (the substrate
   of `control_framework_compliance`: XBU40's validations "map
   directly to a FedRAMP 20x KSI" and to the control baseline;
   traceability from evidence and indicators runs through this
   catalog).
2. **Governed-system registry (opaque references)** — the
   systems/environments under governance, known only by
   caller-supplied opaque references. This is the object both
   platforms operate on: XBU40's hosted enclave environments and
   CGC's hosted Merlin SaaS systems alike. No field can hold a
   real system credential or network identifier.
3. **Indicator (KSI) registry with recorded validation
   results** — security indicators registered per framework/
   system, each carrying an append-only history of validation
   results (status, timestamp, evidence links). Recording the
   result is Core; *performing* the validation automatically is
   Extended.
4. **Evidence registry (metadata + SHA-256, validation-status
   records)** — evidence artifacts registered by metadata and
   SHA-256 content hash (the registry holds records and hashes,
   not artifact binaries), each with validation-status records
   over time. The substrate of `evidence_management` and of the
   Trust Center's "access evidence artifacts" view.
5. **Finding / remediation (POA&M-style) records** — findings
   (from vulnerability work, assessments, or monitoring) with an
   **enforced lifecycle** and due dates. Due-date status
   (e.g. overdue) is **DERIVED at read time, never stored** —
   computed from the due date and current state, so it can never
   drift from the record. The substrate of
   `vulnerability_remediation`'s "remediation tracking" and
   "integrated workflows that support remediation and
   validation".
6. **Assessment & authorization-readiness records** — assessment
   events and per-system authorization-readiness records (which
   framework, which controls/indicators stand where, what an
   assessor reviewed and when). The group's only 2-of-2 GRC
   family, claimed by XBU40 as 20x readiness and by CGC as ATO
   acceleration; the Core keeps the readiness *record* both
   services work against.
7. **Posture reporting computed on read** — per-system and
   per-framework summaries computed on read from records only:
   indicator validation counts, evidence counts by validation
   status, open/overdue finding counts, readiness summaries.
   **Counts and summaries only — NO computed risk scores** (no
   score field exists anywhere, by design; see the risk
   named absence).
8. **REST API** — every function above exposed over a REST API
   (JSON), so the service composes with anything that speaks
   HTTP (`api_integrations`, claimed by XBU40: evidence
   collected "through APIs").
9. **RBAC** — role-based access hooks: platform roles with a
   permission matrix enforced on every operation
   (`identity_access_hooks`, claimed by XBU40 as "identity and
   access controls"). Identity itself is supplied by the
   embedding organization; the service ships hooks, not an
   identity provider.
10. **Append-only audit with denied attempts** — every registry
    mutation and every denied attempt recorded with actor,
    action, target, and UTC timestamp, in an append-only trail
    (`audit_support`: the substrate of "preserving artifacts and
    timestamps for assessor review" and "continuously
    audit-ready").

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring) ⇔ the 110 practices
  of NIST SP 800-171 that define CMMC L2. Both forks sit at
  Moderate, so the union baseline is the Moderate baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge
  Rule 2). XBU40's 20x program mechanics (KSI validation in
  place of the traditional 800-53 assessment cadence) are its
  own authorization path at the same Moderate tier, recorded in
  `scratch/ARTIFACTS.md`; the baseline stated here is the
  crosswalk baseline for the merged build.
- **Feature → control family mapping (this build):**
  - Framework & control catalog registry → **CA** (CA-2 control
    assessments — the catalog is what assessments assess
    against), **PM** (program management — framework/program
    registry).
  - Governed-system registry → **CA** (CA-6 authorization to
    operate — readiness is tracked per governed system), **CM**
    (CM-8 system component inventory — the registry is the
    inventory of record, by opaque reference).
  - Indicator registry & validation results → **CA** (CA-5 plan
    of action and milestones — adjacent record discipline),
    **CA-7** (continuous monitoring — validation results are
    the monitoring record), **RA** (RA-5 — see findings below).
  - Evidence registry → **AU** (AU-6 audit review — evidence and
    timestamps preserved for assessor review), **SI** (SI-7
    software & information integrity — SHA-256 content hashes
    on every evidence record), **SA** (SA-11/SA-12 family
    posture: developer/supply records are the embedding
    organization's, stated plainly, not claimed here).
  - Finding / remediation records → **RA** (RA-3 risk
    assessment inputs — findings are recorded, never scored;
    RA-5 vulnerability monitoring & scanning — the *records* of
    scanning output; the scanner is Extended), **SI** (SI-2 flaw
    remediation — the enforced lifecycle and derived due-date
    status), **CA** (CA-5 — POA&M-style records are this item's
    shape).
  - Assessment & authorization-readiness records → **CA**
    (CA-2, CA-6 — assessment events and ATO-readiness state).
  - Posture reporting (computed on read) → **CA** (CA-7
    continuous monitoring reporting), **AU** (AU-6 — summaries
    derive from records and audit, never from stored derived
    state).
  - RBAC → **AC** (AC-2 account management, AC-3 access
    enforcement, AC-6 least privilege), **IA** (IA-2
    identification & authentication — identity is supplied by
    the embedding organization via user/role headers; the
    service ships hooks, not an identity provider).
  - Append-only audit → **AU** (AU-2 event logging, AU-3 content
    of audit records, AU-6 audit review, AU-9 protection of
    audit information — append-only store, denied attempts
    recorded).
  - Input discipline across all registries → **SI** (SI-10
    information input validation — malformed input is rejected
    whole, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS
    when a certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed
    here).
- **Standing caveat (from `crosswalk.md`, binding on this
  spec):** **FedRAMP authorizes products; CMMC certifies
  organizations.** This mapping states which baseline families
  the build's features answer to, as a **planning equivalence
  only**. It is not a FedRAMP authorization and not a CMMC
  certification, and it does not claim either; a FedRAMP-
  authorized product confers no CMMC certification on anyone,
  and compliance inside each regime must still be earned
  separately.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (14 claims total; XBU40 12, CGC 2;
  the siblings share 2 families — assessment & authorization
  support, and platform hosting at the platform layer).
- Taxonomy: 14 families; 12 claimed by at least one fork, 2 at
  zero claims in both forks' own prose (risk management, policy
  management), recorded as named absences.
- Core: 10 core functions implemented by the build side, each
  the records substrate of the claims above.
- Extended: 7 functions specified and ranked, **not**
  implemented in this build (automated evidence-validation
  engine incl. API/telemetry collection, continuous-monitoring
  feeds & scanner integrations, vulnerability scanning engine,
  automated KSI validation, posture/risk scoring engines,
  hosted enclave & PaaS operations themselves, FedRAMP package
  generation). Three further domains (Torq, QIZ, Veeam) are
  named **out of scope, not gaps**: services CGC's own
  description excludes from its certification. Platform note:
  the build is a single-tenant reference deployment; encryption
  at rest is deployment-layer (TLS when configured); demo
  identities are hooks, not an IdP (IA-2 stays with the
  embedding organization).
