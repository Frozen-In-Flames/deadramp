# Union Spec — Governance, Risk, and Compliance (GRC), CMMC L3-adjacent (DeadRamp Phase 2, Group 44 singleton)

The singleton spec for the GRC category at the L3-adjacent tier:
**1 fork, FedRAMP High** — US AI (United Solutions, FR2009746321).
Reconciled zero-diff: `specs/specs.json` ↔ `forks.json`
category="Governance, Risk, and Compliance (GRC)" +
cmmc_tier="L3-adjacent" (exactly one match) ↔ MAP.md's category
arithmetic (GRC totals 11 offerings = 1 at L1, a separate singleton
+ 2 at L2, shipped as Group 33 + 1 at L3-adjacent, this singleton +
7 untiered with impact Unknown and tier null, remainder forks).
MAP.md's sibling sections list only groups of size 2+, so no
sibling-section diff applies to a singleton; forks.json exactness
plus the category arithmetic is the reconciliation, per the earlier
singleton builds.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 33 merged build** (`../grc-l2/`) — the union of the
   2 GRC L2 (FedRAMP Moderate) forks, shipped as a working clean-room
   GRC records substrate (10 core functions).
2. This singleton's **1 High fork**, via the spec sheet in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run by
the coordinator, and both negative controls were mutation-verified
by patching the implementation (see Verification below and
tests/README.md).

**Reuse, stated explicitly:** this build reuses Group 33's own
open-source code (Apache-2.0, ours). Two modules are byte-identical
to Group 33 (`__init__.py`, `catalog.py`); six are modified for the
tier uplift (`errors.py` — AuditWriteError added; `access.py` —
auditor role added; `audit.py` — hash chain, fail-closed writes,
and query added, following the proven `groups/analytics-l3`
mechanics as applied in `groups/crm-l3`; `store.py` — snapshot
fail-closed wrapper added; `service.py` — lockout, audit
verify/query, auditor user added; `__main__.py` — auditor user and
lockout flags added). Per-file record in `scratch/reuse-note.md`.
No core function changed behavior: every Group 33 test passes with
only the documented uplift adaptations (tests/README.md).

## What this fork actually is (from its own description)

US AI's marketplace description does not describe a GRC product.
It describes a **managed, multi-tenant AI platform suite**: a suite
of microapps and microservices built on an AI-powered data lake, a
zero-trust framework, and hyperscale microservices infrastructure,
comprising nine named suites — a software factory / app store with
CI/CD and Kubernetes hosting across high-impact clouds (Extreme
Innovation Software Factory), a cybersecurity-lifecycle suite
(Archangel), a traceability/provenance platform (Certior), a
low-/no-code process designer for tracking people entering and
leaving secured locations and requesting services (Evolution), a
general-purpose ML data-lake platform (Forsight), grants-lifecycle
automation (Gini), a supply-chain ecosystem (Illuminate), a
healthcare ecosystem (Siqi), and an emergency-response ecosystem
(Velicus). The GRC slice of that platform is **Archangel** alone,
and Archangel's own substance is AI prediction: it "automates" the
cybersecurity lifecycle "from Governance, Risk, and Compliance
(GRC) to Continuous Diagnostics and Mitigation (CDM)", applies AI
to "automate security accreditation by predicting compliance with
security controls", applies "Blockchain, AI, and RPA to
continuously monitor device logs and predict vulnerabilities and
breaches", and applies AI "to predict global security and supply
chain risks".

That is stated here plainly because it decides the build: the
fork's GRC functions are prediction and monitoring engines
(Extended, below), and the records substrate those engines' outputs
land in is the Group 33 union this build carries up. The other
eight suites are this fork's non-GRC substance in other categories'
domains; they are named in the long tail, recorded, and not built
here — this group owes the GRC category, not the whole platform.

## How functions were counted

Group 33's fixed 14-function taxonomy for this category was applied
**verbatim** (same ids, labels, and matching patterns — verified
byte-identical to Group 33's extractor taxonomy block) to this
fork's own public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `../../raw/data_dump.json`, produced by the
General Services Administration, last change 2026-10-22; product
record joined by FedRAMP ID; only the record's `service_desc` was
matched). A function is claimed **only** when the description
contains matching text; the matching sentence is stored as the
claim's evidence in `specs/specs.json`.

**Result: 2 claims** (floor, not ceiling):

| Function | Evidence (verbatim, from the Archangel passage) |
|---|---|
| Continuous monitoring | "Additionally, CSPs and security professionals apply Blockchain, AI, and RPA to continuously monitor device logs and predict vulnerabilities and breaches." |
| Risk management | "Lastly, security, supply chain, and risk management professionals apply AI to predict global security and supply chain risks." |

Both claims' substance is an AI engine: monitoring performed by
blockchain/AI/RPA machinery over device logs, and risk *prediction*
by AI. What the Core implements for them is the records substrate
their outputs presuppose — monitoring results recorded as indicator
validation results and findings (Core #3/#5), and risk work
recorded as finding records with a counts-only posture summary
(Core #5/#7). The engines themselves are Extended (Gaps below).
**No score follows from the risk claim**: posture reporting in this
build computes counts and summaries only, and no score, rating, or
grade field exists anywhere in the build or its output — enforced
by the inherited posture tests, which scan recursively for such
keys. A claim that a vendor's AI predicts risks licenses recording
findings; it does not license this build to compute risk.

Wording-artifact notes (full record in `scratch/ARTIFACTS.md`):

- **The risk_management tag is new at this tier, and the record
  says why.** At L2 the family was a named absence (0 of 2) because
  neither fork's own prose contained the pattern phrase; Group 33's
  discipline was that bare "risk" and the category name earn no
  tag. This fork's prose literally contains "risk management" in a
  functional sentence, so the verbatim pattern tags it. The tag is
  recorded with its basis and its limit (prediction engine =
  Extended; no scoring), not silently absorbed and not suppressed
  to match the L2 outcome.
- **"Automate security accreditation by predicting compliance with
  security controls" tags nothing.** It is a near-miss to both
  `assessment_authorization` (no authorization-readiness / ATO /
  assessor phrasing) and `control_framework_compliance`
  ("predicting compliance" is not the pattern's "automated
  compliance"). The accreditation-prediction engine is Extended.
- **Category and program names earn no tags.** "from Governance,
  Risk, and Compliance (GRC) to Continuous Diagnostics and
  Mitigation (CDM)" names the category and a federal program; the
  continuous_monitoring tag rests on the device-logs sentence only.
- **Certior's "traceability, provenance, and auditability" tags
  nothing** — not `audit_support` (no audit-ready / assessor-review
  phrasing) and not `evidence_management`. The traceability
  platform is named in the long tail.
- **"Predict vulnerabilities and breaches" tags nothing** — the
  `vulnerability_remediation` pattern requires vulnerability
  lifecycle/scanning/posture phrasing. Prediction is an engine.
- Bare words earn no tags: Forsight's "compliance, risk, fraud"
  list; "zero-trust framework", "security controls", and
  "self-sovereign identity" (not `identity_access_hooks`);
  "infrastructure automation and devsecops", "intelligently
  automate", "automate the grants life cycle" (not
  `workflow_automation` — the pattern requires integrated
  workflows / automation engine / compliance automation); Gini's
  "standardized pre-award risk framework" ("risk framework" is not
  in the risk pattern, and the substance is grants-domain).
- The source record carries `business_categories: []` while
  forks.json files the fork under GRC; recorded as-is in the spec
  sheet. A source category label is not a functional claim.

## Function ranking — the singleton

| # | Family | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Continuous monitoring | 1 | **Claimed** — Core records substrate (indicator validation results #3, finding records #5); the monitoring engine and its feeds are Extended |
| 1 | Risk management | 1 | **Claimed** — Core records substrate (finding records #5, counts-only posture #7); the AI risk-prediction engine is Extended; **no scoring anywhere** |
| 3 | Evidence management & validation | 0 | **Core** — evidence registry (#4), carried from the Group 33 union (claimed 1 of 2 there); the automated validation engine is Extended |
| 3 | Security indicators (KSI) tracking & validation | 0 | **Core** — indicator registry with recorded validation results (#3), carried (claimed 1 of 2 at L2); automated KSI validation Extended |
| 3 | Vulnerability & remediation management | 0 | **Core** — finding/remediation records (#5), carried (claimed 1 of 2 at L2); the scanning engine Extended |
| 3 | Control & framework compliance management | 0 | **Core** — framework & control catalog registry (#1), carried (claimed 1 of 2 at L2) |
| 3 | Compliance posture reporting & dashboards | 0 | **Core** — posture reporting computed on read (#7), counts/summaries only, carried (claimed 1 of 2 at L2); dashboard/scoring engines Extended |
| 3 | Assessment & authorization support | 0 | **Core** — assessment & authorization-readiness records (#6), carried (the L2 group's only 2-of-2 family); package generation Extended |
| 3 | Audit support & assessor review | 0 | **Core** — append-only audit (#10, uplifted) plus assessor-facing evidence/validation records (#4, #6), carried (claimed 1 of 2 at L2) |
| 3 | Platform hosting / enclave operations | 0 | Platform layer — the fork's hyperscale hosting operations are Extended / deployment layer (see Gaps); the Core's governed-system registry (#2) is the records substrate |
| 3 | Identity & access controls (hooks) | 0 | **Core** — RBAC (#9, uplifted), carried (claimed 1 of 2 at L2); hooks only, no identity provider |
| 3 | Workflow & automation | 0 | **Core** — enforced record lifecycles (findings #5, authorizations #6) are the in-core seed, carried (claimed 1 of 2 at L2); automation engines Extended |
| 3 | APIs & integrations | 0 | **Core** — REST API (#8), carried (claimed 1 of 2 at L2); API/telemetry evidence *collection* Extended |
| 14 | Policy management | 0 | **Named absence** — 0 claims in this fork's prose and 0 of 2 at L2; claimed by no fork in this category at any tier so far; not built, not a gap |

Baseline families carried as baseline substrate (same posture as
Group 33): the REST API surface, RBAC enforcement, and the
append-only audit trail are Core items #8–#10 in their own right,
uplifted to the High baseline below.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 40 precedent).** This fork tags 2 of 14 families — not zero,
but both tags are engine claims, and neither names a records
function. All 10 core functions nevertheless stand in this build,
for two recorded reasons, not convenience: (1) the two claimed
families presuppose exactly this substrate — continuous
monitoring's outputs and risk work land as indicator results,
evidence, and findings, and a build that shipped the category at
High with no registry for them would implement neither claim's
record-keeping half; and (2) the Merge Rule: a cross-tier merge
takes the union of the parents upward whole, Group 33's union is a
parent of this build, and thinner (or differently-aimed) marketing
prose at High is not a downgrade — stripping the substrate would
dilute the union, which Rule 1 prohibits. Core functions the fork
does not claim are flagged **carried, not claimed** for this tier;
functions it does claim are flagged **claimed (records substrate);
engine Extended**. That is this paragraph, stated once and plainly,
rather than ten quiet exceptions.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 functions as Group 33, carried up whole. Package
`grc` under `src/`, Python 3, **standard library only**, runnable
and testable with `PYTHONPATH=src`. The contract is Group 33's,
unchanged except for the uplift deltas marked **[L3]** (below and
in tests/README.md).

1. **Framework & control catalog registry** — frameworks and their
   controls registered as catalog records; a fresh store is seeded
   with a generic 800-53-style catalog (one framework, 21
   controls). Carried, not claimed at this tier.
2. **Governed-system registry (opaque references)** — the
   systems/environments under governance, known only by
   caller-supplied opaque references; no field can hold a real
   system credential or network identifier. Carried (platform
   substrate).
3. **Indicator (KSI) registry with recorded validation results** —
   indicators registered per framework/system, each carrying an
   append-only history of validation results (status recorded
   verbatim, timestamp, evidence links). Recording the result is
   Core; performing the validation automatically is Extended.
   **Claimed in part**: this is where continuous monitoring's
   recorded outputs land.
4. **Evidence registry (metadata + SHA-256, validation-status
   records)** — evidence artifacts registered by metadata and
   SHA-256 content hash (records and hashes, not binaries), with
   verify-by-content and validation-status records over time; the
   filing user may not review their own evidence (separation
   enforced in the store). Carried, not claimed at this tier.
5. **Finding / remediation (POA&M-style) records** — findings with
   an **enforced lifecycle** and due dates; due-date status
   (overdue) is **DERIVED at read time, never stored**. Severity is
   recorded verbatim; **no score is computed or stored anywhere**.
   **Claimed in part**: the records half of both claimed families
   (monitoring findings; risk findings).
6. **Assessment & authorization-readiness records** — assessment
   events and per-system authorization records with a guarded
   lifecycle and full transition history. The Core keeps the
   readiness *record*; it grants no authorization. Carried, not
   claimed at this tier (the fork's accreditation *prediction* is
   Extended).
7. **Posture reporting computed on read** — per-system and
   per-framework summaries computed on read from records only:
   indicator validation counts, evidence counts by validation
   status, open/overdue finding counts, readiness summaries.
   **Counts and summaries only — NO computed risk scores** (no
   score/rating/grade field exists anywhere, by design; enforced
   by test). **Claimed in part** as the reporting half of the risk
   family — counts of recorded findings, never a rating of them.
8. **REST API** — every function above over a REST API (JSON), so
   the service composes with anything that speaks HTTP. **[L3]**
   adds `GET /audit/verify` and the `GET /audit` filter parameters.
9. **RBAC** — role-based access hooks: roles `admin`, `member`,
   `viewer` (as Group 33) **plus `auditor`** (`audit_read` only)
   **[L3]**, with the permission matrix enforced on every operation
   in the store and again at the service layer. Identity is
   supplied by the embedding organization; hooks, not an IdP.
10. **Append-only audit with denied attempts** — every registry
    mutation and every denied attempt recorded with actor, action,
    target, and UTC timestamp, in an append-only trail that is
    **[L3]** hash-chained and tamper-evident, fail-closed on write
    failure, and queryable (audit reduction).

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. The cross-tier parent (Group 33's build)
  sat at Moderate; the union baseline is therefore the High
  baseline, un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3 is
  not identical to FedRAMP High; it is the same assurance weight
  class.
- **Feature → control family mapping (carried from Group 33,
  updated for the uplift):**
  - Framework & control catalog registry → **CA** (CA-2 control
    assessments — the catalog is what assessments assess against),
    **PM** (program management — framework/program registry).
  - Governed-system registry → **CA** (CA-6 authorization to
    operate — readiness is tracked per governed system), **CM**
    (CM-8 system component inventory — the registry is the
    inventory of record, by opaque reference).
  - Indicator registry & validation results → **CA** (CA-5 plan of
    action and milestones — adjacent record discipline), **CA-7**
    (continuous monitoring — validation results are the monitoring
    record; at this tier they are also where the fork's claimed
    continuous monitoring lands its records), **RA** (RA-5 — see
    findings).
  - Evidence registry → **AU** (AU-6 audit review — evidence and
    timestamps preserved for assessor review), **SI** (SI-7
    software & information integrity — SHA-256 content hashes on
    every evidence record).
  - Finding / remediation records → **RA** (RA-3 risk assessment
    inputs — findings are recorded, never scored; at this tier the
    fork's risk claim lands here as records), **SI** (SI-2 flaw
    remediation — the enforced lifecycle and derived due-date
    status), **CA** (CA-5 — POA&M-style records are this item's
    shape).
  - Assessment & authorization-readiness records → **CA** (CA-2,
    CA-6 — assessment events and ATO-readiness state).
  - Posture reporting (computed on read) → **CA** (CA-7 continuous
    monitoring reporting), **AU** (AU-6 — summaries derive from
    records and audit, never from stored derived state).
  - RBAC → **AC** (AC-2, AC-3, AC-6), **[L3] AC-5** (auditor role —
    audit review as a separable duty), **[L3] AC-7** (service-layer
    logon lockout), **IA** (IA-2 — identity supplied by the
    embedding organization via user/role headers; hooks, not an
    IdP).
  - Append-only audit → **AU** (AU-2, AU-3, **[L3] AU-5**
    fail-closed writes, AU-6, **[L3] AU-7** query/reduction,
    **[L3] AU-9** hash-chained tamper evidence; denied attempts
    recorded).
  - Input discipline across all registries → **SI** (SI-10
    information input validation — malformed input is rejected
    whole, never partially applied) and **SC** (SC-8 transmission
    confidentiality — TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Group 33, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only: **FedRAMP authorizes
  products; CMMC certifies organizations** — the build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither regime accepts the other as evidence. Any real compliance
  claim still has to be earned inside each regime separately.

## Verification

- Specs: 1 / 1 forks spec'd (2 tagged claims; full description
  preserved; near-misses itemized in `scratch/ARTIFACTS.md`).
- Core: 10 / 10 core functions implemented at the High baseline;
  6 tier uplifts implemented (hash-chained audit, fail-closed
  audit writes with store rollback, audit query/reduction, chain
  verification endpoint, logon lockout, auditor role).
- Tests: **166** (118 inherited from Group 33, 7 added inside
  inherited files for the uplifts, 41 in new uplift files), all
  passing on the coordinator's run.
- **Negative control 1 (inherited, mutation-verified live in this
  tree):** the finding status derivation patched so the overdue
  branch never fires (`if False:`) made **exactly 8 tests fail**
  — the identical failure set to Group 33's drill (derivation
  canonicals, both negative-control arms and the end-to-end arm,
  posture overdue count, service full flow). store.py restored
  from the pre-mutation copy and SHA-256-verified identical
  (`0fe88eb1…`); suite green again.
- **Negative control 2 ([L3], mutation-verified live):**
  `verify_chain` patched to return `(True, None)` unconditionally
  made **exactly 4 tests fail** in the audit files (mutated-entry
  control, broken link, missing hash fields, edited-JSONL reload).
  audit.py restored and SHA-256-verified identical (`df7b1ef9…`);
  suite green again. Full drill records in tests/README.md.

## Coverage statement (for this build)

- Specs: 1 / 1 forks spec'd (2 claims total: continuous
  monitoring 1, risk management 1; both from the fork's Archangel
  passage; the other 12 taxonomy families tag 0 here).
- Taxonomy: 14 families; 2 claimed by this fork, 11 carried as
  Core substrate from the Group 33 union at 0 claims here, 1
  (policy management) a named absence at every tier so far.
- Core: 10 core functions implemented by the build side, each the
  records substrate of the category union, at the High baseline.
- Extended: this fork's own engines (below) plus the 7 functions
  carried from the Group 33 union, specified and ranked, **not**
  implemented in this build. Platform note: the build is a
  single-tenant reference deployment; encryption at rest is
  deployment-layer (TLS when configured); demo identities are
  hooks, not an IdP (IA-2 stays with the embedding organization).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its description
— the platform's actual product surface, none of it built here):

- **AI accreditation & compliance prediction engine** (Archangel:
  "automate security accreditation by predicting compliance with
  security controls") — the prediction half of the fork's
  assessment surface; the Core keeps assessment/readiness
  *records* only.
- **Continuous device-log monitoring & breach/vulnerability
  prediction** (Archangel: Blockchain/AI/RPA monitoring of device
  logs, predicting vulnerabilities and breaches; CDM operations) —
  the engine half of this fork's claimed continuous monitoring;
  the Core records monitoring *results*.
- **AI risk prediction engine** (Archangel: predicting global
  security and supply-chain risks) — the engine half of this
  fork's claimed risk management; the Core records risk *findings*
  and counts them. Any scoring engine belongs here too, and the
  Core's counts-only posture is not a down-payment on one.
- **AI-powered data lake & ML platform** (Forsight: supervised and
  unsupervised ML collection, curation, indexing, insight and
  prediction over acquisition/finance/grants/health/supply-chain
  data; the hyperscale community database of curated records) —
  AI/ML model machinery generally; no model or inference of any
  kind is built anywhere in this group.
- **Software factory & application hosting platform** (Extreme
  Innovation Software Factory: app store, tenant application
  hosting, CI/CD pipelines, software/data libraries and pipelines,
  Kubernetes clusters across AWS/Google/Azure high-impact clouds) —
  platform layer; also the fork's multi-tenancy operations (the
  build is a single-tenant reference deployment).
- **Traceability, provenance & auditability platform** (Certior:
  point-and-click tracking configuration over products and supply
  lines) — a records platform of a different shape than this
  substrate; named, not built.
- **Low-/no-code process configuration designer & movement/service
  tracking** (Evolution: secured-location entry/exit, service
  requesting and receiving — passports, visas, asylum, healthcare,
  transportation).
- **Grants lifecycle automation** (Gini: grants automation,
  pre-award risk framework, ledger reconciliation, digital
  dossier, single-audit finding extraction over 100TB of data).
- **Supply-chain ecosystem engines** (Illuminate: contract
  formation/administration/closeout automation, provenance
  tracking of goods and services).
- **Healthcare ecosystem platform** (Siqi: health-data collection,
  blockchain health records, self-sovereign identity, disease
  prediction, contact-tracing provenance).
- **Emergency-response coordination platform** (Velicus: responder
  tracking, geolocation/health/safety, AI responder matching).
- **Blockchain / RPA machinery** asserted across the suite
  (Archangel, Gini, Illuminate, Siqi) — distributed-ledger and
  robotic-process-automation engines; none is built here.

Extended functions carried from the Group 33 union, specified in
`../grc-l2/UNION-SPEC.md`, not implemented:

- Automated evidence-validation engine (API/telemetry collection).
- Continuous-monitoring feeds & scanner integrations.
- Vulnerability scanning engine.
- Automated KSI validation.
- Posture / risk scoring engines — named Extended here as at L2,
  and bounded by the same doctrine: the Core computes no score,
  and this fork's risk claim (an AI prediction engine, above) is
  where any predictive machinery belongs, not in posture.
- Hosted enclave & PaaS operations themselves.
- FedRAMP package generation (SSP/POA&M exports and submission
  artifacts from the Core's records).

Baseline gaps at High (platform layer; gap-listed, never implied
closed): MFA / authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13); encryption at rest (SC-28);
audit retention enforcement (AU-11); session lock / termination
(AC-11/AC-12). Platform notes: multi-tenancy (claimed by the fork
as its operating model; the build is a single-tenant reference
deployment); TLS only when a certificate is configured; demo
identities are hooks, not an IdP (IA-2 stays with the embedding
organization).
