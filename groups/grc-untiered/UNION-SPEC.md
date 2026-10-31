# Union Spec — Governance, Risk, and Compliance (GRC), untiered set

**Set:** remainder build unit `untiered:Governance, Risk, and
Compliance (GRC)` — **15 forks** whose FedRAMP impact level in the
source is **Unknown**. **Tier: null.** There is no FedRAMP baseline
for this set and no CMMC tier; nothing here is built to a baseline.
The set builds to its **documented control claims** only: what the
forks' own descriptions assert, tagged under the category's existing
taxonomy, verbatim.

**Category substrate:** the founding group's build (groups/grc-l2)
is carried whole — its Core is the category's records substrate and
is byte-identical here (accounting in README.md). The founding
group's two famous named absences, **risk_management** and
**policy_management**, were retired at L2 by claiming forks; at tier
null they are simply families to tag honestly per fork text, and
this set's forks claim both (below).

## Membership (15 forks, remainder-unit order)

| Fork | Vendor / Product | Claims |
|---|---|---|
| FR2701557058 | 38North Security, LLC / Northwatch | 3 |
| FR2628647239 | Advent Business Company Inc. / Enablement® | 4 |
| FR2635930439 | Advent Business Company Inc. / Enablement® | 4 |
| FR2628943633 | Boundera / Boundera SaaS | 2 |
| FR2631258122 | Cahill Swift, LLC / Cahill Swift Compliance Management Platform | 1 |
| FR2631258125 | Certivo, Inc. / Certivo Compliance Platform | 0 |
| FR2630354485 | ComplianceAid INC. / ComplianceAide Government Cloud | 1 |
| FR2633957422 | MediaLab Solutions LLC / Vastian (MediaLab by Vastian) | 0 |
| FR2631054539 | Mycroft Technologies Inc / Mycroft GRC Platform | 5 |
| FR2632558735 | Ocasio Convergence Holdings LLC / Axiom Convergence Engine (ACE) | 0 |
| FR2700754082 | PlatformOne Group Inc / ComplianceONE | 2 |
| FR2700137045 | RegScale, Inc. / RegScale Trust Center 20x (Class C) | 0 |
| FR2629068830 | SunStone Secure, LLC / SunStone Artemis Platform | 0 |
| FR2633053629 | TGuardAI Inc. / TrustGuard AI Compliance Platform | 3 |
| FR2630354484 | VisualVault LLC / VisualVault Cloud | 0 |

**25 claims total; 6 forks claim zero** and are reported plainly.
The two Enablement sheets are separate forks whose raw descriptions
are byte-identical; their claim tables are identical (4 each), as
expected, and both are spec'd (the Phase 1 rule).

## Counting method

The founding group's **14-family taxonomy, verbatim**: AST-parsed
out of `groups/grc-l2/scratch/extract.py` (parsed, never executed),
applied with the founding sentence rule (split on `(?<=[.!?])\s+`)
and the founding evidence rule (first matching sentence per family,
stored verbatim, no truncation). Before tagging this set, the
extractor **reproduced the founding group's original shipped claim
tables exactly** — both forks, 14 claims, deep-equal against git
commit `1dcba25`, with founding correction 1 (the CGC
hosted-services exclusion) applied on the proof path — and stops
without writing specs if the proof fails. It did not fail.

Exclusion discipline, applied before finalizing: third-party
catalogues and scope-exclusion sentences are excluded before
matching, and removed raw hits are recorded. This set has **one**
removal out of 26 raw hits: ComplianceAide's
`assessment_authorization` hit, whose only `assessor` evidence sits
inside the sentence where the offering states it "does not replace
an independent assessor or Authorizing Official, make authorization
decisions" — a capability placed out of scope by the fork's own
wording. No description in this set contains a third-party
hosted-app catalogue or a "not authorized" hosted-services block
(asserted in the extractor); Northwatch's module list is a
first-party catalogue and stands. `certified_services` record
fields (non-empty for 12 of the 15 forks) are never matched —
founding correction 2.

The founding addendum's two wording precedents were checked against
this set and **neither arises**: no fork's risk_management hit fires
on a framework name (the Kovr "DoD Risk Management Framework (RMF)"
posture — Mycroft's standing hit fires on "vendor and risk
management" offered as a capability template), and no fork writes
"Authorization to Operate" where the taxonomy requires "Authority
to Operate" (the Kovr near-miss). Wording artifacts that do stand
are recorded at artifact weight in `scratch/ARTIFACTS.md` — chiefly
Enablement's `api_integrations`, which fires on the token
"integration" in "No coding, no integration team, no consultants":
a team the customer does not need, not an integration surface.

Census citations (remainder.json) are **not claims**: all 20 verify
as substrings of the forks' own descriptions, but only 6 of the 20
are themselves a claim evidence sentence. The other direction
holds too: claims stand on description sentences whether or not
the census cited them.

## Claim ranking (all 14 families)

Dispositions use the founding group's vocabulary, as updated by its
L2 addendum: **Core** = built in the carried substrate as records;
**Extended** = named, not built.

| # | Family | Forks claiming | Disposition |
|---|---|---|---|
| 1 | policy_management | 6 — Northwatch, Enablement ×2, Cahill Swift, ComplianceAide, ComplianceONE | **Core** as records (control catalog, Core 1; evidence records, Core 4). Policy lifecycle engine: Extended gap. |
| 2 | ksi_tracking | 4 — Northwatch, Enablement ×2, Boundera | **Core** (indicator registry + recorded results, Core 3). Automated KSI validation: Extended gap. |
| 3 | api_integrations | 4 — Enablement ×2 (artifact, see above), Mycroft, ComplianceONE | **Core** surface is the build's own REST API (Core 8). Connector/integration engine: Extended gap. |
| 4 | continuous_monitoring | 3 — Enablement ×2, Mycroft | **Core** as recorded indicator results (Core 3). Live feeds & scanner integrations: Extended gap. |
| 5 | control_framework_compliance | 2 — Mycroft, TrustGuard AI | **Core** (framework & control catalog registry, Core 1). |
| 6 | assessment_authorization | 2 — Northwatch, Boundera | **Core** (assessment & authorization-readiness records, Core 6). |
| 7 | workflow_automation | 2 — Mycroft, TrustGuard AI | **Core** only as the records substrate's enforced lifecycles (Core 5). Automation/agentic execution engines: Extended gap. |
| 8 | risk_management | 1 — Mycroft | **Core** as records (assessment records, Core 6; finding records, Core 5) — the founding addendum's disposition: **no risk-register object, no score**. Scoring engines: Extended gap. |
| 9 | audit_support | 1 — TrustGuard AI | **Core** (evidence records, Core 4; append-only audit log, Core 10). |
| 10 | evidence_management | **0** | Named absence for this set. The Core substrate (Core 4) exists from the founding build; no fork here claims the family at the taxonomy's phrases. |
| 11 | vulnerability_remediation | **0** | Named absence for this set. Finding records (Core 5) exist as substrate; no fork claims the family. |
| 12 | posture_reporting | **0** | Named absence for this set. Posture counts (Core 7) exist as substrate; no fork claims the family — posture prose is everywhere in these descriptions and the family's phrases are nowhere. |
| 13 | platform_hosting | **0** | Extended (hosted enclave & PaaS operations), unclaimed in this set. |
| 14 | identity_access_hooks | **0** | Named absence for this set. RBAC (Core 9) exists as substrate hooks; no fork claims the family (Enablement's "role-based and attribute-based access control" never forms the contiguous phrase — recorded near-miss). |

## Core-boundary decision (stated once)

The Core is the founding group's records substrate, carried whole
and byte-identical, because every family this set's forks claim
maps onto a records function the founding build already ships, and
the families this set does not claim are not built here as features
either — where the carried substrate already contains them as
records (evidence, findings, posture counts, RBAC), they remain
substrate, not claims of this set. Tier null changes nothing about
the boundary: nothing is built down from a baseline, because there
is no baseline; the build is the records substrate, and everything
beyond records is Extended and named below. **Posture reporting is
counts only, and no score is computed anywhere in this build** —
test-enforced by recursive key scan — even though forks in this
set document scores of their own (Northwatch's PAIN rating,
Boundera's score history, TrustGuard's vendor scoring). Those
scores are the forks' claims, recorded as such; they are not
computed, stored, or echoed by this build.

## Documented control claims

Control families below are documented **only** where this set's
forks' own descriptions assert them, each traced to the claiming
fork and its evidence sentence. A fork's documented control
language is **its claim, never this build's attainment**.

- **CA — Security Assessment and Authorization: DOCUMENTED.**
  - *continuous_monitoring* — Enablement (both sheets): "backed by
    native, always-on continuous monitoring"; Mycroft: "Continuous
    Monitoring: automated evidence collection and control
    monitoring."
  - *assessment_authorization* — Northwatch: "The notifications are
    published to the customer's assessor and agency customers
    through the Certification Data Sharing module…"; Boundera:
    "grant assessors controlled access to KSIs, rules, evidence,
    vulnerabilities, SDR and other packages."
  - *control_framework_compliance* — Mycroft ("Compliance
    Automation: task management dashboards and templates…");
    TrustGuard AI ("unifies internal compliance automation and
    external threat monitoring in a single system of record").
  - *ksi_tracking* — Northwatch ("Key Security Indicators (KSI)");
    Enablement (both sheets, KSI mapping sentence); Boundera
    ("failed KSI assertions become tracked vulnerability records…").
  - *posture_reporting* is **not documented** (0 claims).
- **RA — Risk Assessment: DOCUMENTED in part.**
  - *risk_management* — Mycroft only: "templates for policy
    documentation, vendor and risk management, and IT asset
    management."
  - *vulnerability_remediation* is **not documented** (0 claims) —
    Boundera tracks "vulnerability records with due dates,
    dispositions, and remediation clocks" under its ksi_tracking
    evidence, but no sentence fires the remediation family.
- **AU — Audit and Accountability: DOCUMENTED.**
  - *audit_support* — TrustGuard AI: "generate audit-ready,
    machine-readable findings and reports."
  - *evidence_management* is **not documented** as a family
    (0 claims): evidence collection prose is ubiquitous in these
    descriptions, and the family's phrases ("collects and verifies
    evidence", "evidence validation") appear in none of them.
- **PM — Program Management: DOCUMENTED.**
  - *policy_management* — 6 forks: Northwatch ("register of the
    governance documents FedRAMP 20x requires: policies, procedures,
    plans, inventories and records"), Enablement ×2 ("Policies and
    controls are written once…"), Cahill Swift ("drug and alcohol
    testing policies under 49 CFR Part 219"), ComplianceAide
    ("produces … policies, control narratives, System Security Plan
    (SSP) support…"), ComplianceONE ("It holds control
    implementation records, policies, procedures, evidence files,
    POA&Ms, risks, incidents and assessment results…").
- **AC / IA — Access Control / Identification and Authentication:
  NOT DOCUMENTED.** *identity_access_hooks* has 0 claims; the
  closest text (Enablement's role-based and attribute-based access
  control) is a recorded near-miss, not a claim. The build's RBAC
  is demo substrate, not a documented claim of this set.
- **Not documented** (no fork in this set asserts them, and nothing
  is filled in from any baseline): AT, CM, CP, IR, MA, MP, PE, PL,
  PS, SA, SC, SI — and, within the families above, the zero-claim
  members named individually.

## Named absences (this set)

- **evidence_management — 0 of 15.** The set's most striking
  absence: nearly every description talks about evidence, and none
  uses the family's phrases.
- **posture_reporting — 0 of 15.** Posture prose everywhere ("live
  security posture", "reads security posture", "one
  continuously-updated view of their posture"); the family's
  phrases ("compliance posture", "posture dashboard",
  "posture report") in none.
- **vulnerability_remediation — 0 of 15.**
- **identity_access_hooks — 0 of 15.**
- **platform_hosting — 0 of 15.**
- The category's two historic named absences are **not** absent
  here: risk_management is claimed once (Mycroft) and
  policy_management leads the ranking at six forks. Both stand at
  the founding addendum's dispositions — records, no risk-register
  object, no score, no policy lifecycle engine.

## Gaps (for the final GAPS batch — named, not built)

Extended functions, restated from the founding group where this
set's forks give them substance:

1. **Automated evidence collection & validation engine** (API /
   telemetry connectors, machine validation of evidence) —
   substance in Boundera, Northwatch, Cahill Swift; the family
   itself unclaimed at verbatim weight.
2. **Continuous-monitoring feeds & scanner integrations** —
   claimed as monitoring by Enablement and Mycroft; feeds unbuilt.
3. **Vulnerability scanning engine** — Mycroft claims monitoring
   via third-party integrations; no scanner is built.
4. **Automated KSI validation** (machine-checkable KSI rules) —
   tracking claimed by 4 forks; validation unbuilt.
5. **Posture & risk scoring engines** — documented as the forks'
   own claims only (Northwatch PAIN N1–N5; Boundera score history;
   TrustGuard vendor scoring). The build computes no score
   anywhere, by design.
6. **Hosted enclave & PaaS operations** — unbuilt and unclaimed in
   this set.
7. **FedRAMP package generation** (SSP / POA&M document generation,
   OSCAL emission) — substance in Northwatch, Boundera, RegScale,
   SunStone; unbuilt.
8. **Policy lifecycle engine** (drafting, versioning, attestation
   workflows beyond records) — the founding addendum's gap;
   policy claimed by 6 forks here as records.
9. **Agentic workflow execution** — automation claimed as records
   by Mycroft and TrustGuard AI; execution unbuilt.
10. **AI control-narrative & assessment-response generation** —
    ComplianceAide and TrustGuard AI document generation claims;
    unbuilt.
11. **Data-integration connector engine** (beyond the build's own
    REST surface) — Mycroft, ComplianceONE, Enablement claims.

Fork excess (documented product surface outside the category's
records substrate):

12. **Healthcare quality management suite** — Vastian (MediaLab):
    inspections, competency, continuing education, incident
    management for healthcare organizations.
13. **AI/ML governance evaluation engine** — ACE: source-validity
    and claim-scope evaluation gating AI-assisted output.
14. **Digital-twin OSCAL analysis engine** — SunStone Artemis /
    Apollo: OSCAL 1.1.3 ingestion and digital-twin compliance
    analysis.
15. **No-code process / BPM platform** — Enablement (visual BPMN
    process platform) and VisualVault (configurable constituent
    process automation): general process platforms wearing GRC
    clothes, claimed here only where their sentences fire GRC
    families.
