# Gap registry — the final batch

Rule (Aries, Oct 25, 2026): every gap named by any group build — functions specified in a group's union spec but not implemented, and baseline requirements a build gap-lists instead of claiming — is collected HERE, in one registry. The gaps are worked as a single final batch at the very end of the repo, after the last sibling group (and the singleton/remainder forks) has shipped. Groups do not stop to close their own gaps mid-pipeline; they name them, register them here on ship, and the line keeps moving.

Status key: `open` = registered, not yet built. The final batch closes entries or re-scopes them in writing; an entry never disappears silently.

## Group 1 — Analytics L2 (128 forks)

Extended functions, specified in groups/analytics-l2/UNION-SPEC.md, not implemented:
- [ ] open — Predictive ML (the remainder of the statistical/ML claim family; core covers descriptive statistics only)
- [ ] open — Alerts, monitoring & detection
- [ ] open — Real-time / streaming analytics
- [ ] open — Collaboration (shared workspaces around analytics)
- [ ] open — Proprietary-source connectors (core covers open-format file ingest only)
- [ ] open — Data transformation / ETL
- [ ] open — Governance beyond the dataset registry
- [ ] open — Geospatial analytics
- [ ] open — Text / NLP analytics
- [ ] open — Archiving
- [ ] open — Self-service BI
- [ ] open — KPI management
- [ ] open — Scheduling
- [ ] open — Media analytics

## Group 2 — Collaboration L2 (57 forks)

Extended functions, specified in groups/collaboration-l2/UNION-SPEC.md, not implemented:
- [ ] open — Workflow / process-automation engines (the group's #2 claim family)
- [ ] open — AI assistance, speech, and analytics
- [ ] open — Learning, training, mentoring
- [ ] open — Task & project management beyond board cards
- [ ] open — Voice / telephony / contact center
- [ ] open — Records & governance beyond the versioning/audit seed
- [ ] open — Knowledge management
- [ ] open — Meetings / video media transport (coordination surface is core; a stdlib build carries no A/V)
- [ ] open — E-signature

## Group 3 — Analytics L3-adjacent (54 forks)

Extended functions, specified in groups/analytics-l3/UNION-SPEC.md, not implemented. Same 14 families as Group 1, with this group's claim weights; first candidate for the batch:
- [ ] open — Alerts, monitoring & detection (27 of 54 forks claim it; kept Extended because each claimant binds alerting to its own domain telemetry — reasoning in the group spec)
- [ ] open — Predictive ML remainder (family #1 at 34 of 54)
- [ ] open — Real-time / streaming (18), collaboration (17), proprietary connectors (17), governance (11), transformation (10), text/NLP (6), archiving (4), scheduling (3), geospatial (3), media analytics (2), self-service BI (2), KPI (0 claims in this group)

Baseline gaps at High (platform layer; gap-listed, never implied closed):
- [ ] open — MFA / authenticator management (IA-2(1)/(2), IA-5) — IdP layer, hooks only
- [ ] open — FIPS-validated cryptography (SC-13) — Python stdlib is not a validated module; not claimed
- [ ] open — Encryption at rest (SC-28) — deployment layer
- [ ] open — Audit retention enforcement (AU-11)
- [ ] open — Session lock / termination (AC-11/AC-12) — stateless per-request auth in the current build

## Group 4 — Cybersecurity & Risk Management L2 (54 forks)

Extended functions, specified in groups/cybersecurity-l2/UNION-SPEC.md, not implemented. By design the build is the shared defensive substrate only: no offensive tooling and no engine of any kind. The engines are the gaps:
- [ ] open — AI/ML detection models (17 siblings)
- [ ] open — SOAR / orchestration engines (14)
- [ ] open — Detection engines and staffed SOC services (13) — ingestion and triage of their output is core
- [ ] open — Network enforcement planes (11)
- [ ] open — Threat-intelligence feeds (9)
- [ ] open — Backup / recovery products (9)
- [ ] open — Full GRC automation suites (8) — control mapping is core
- [ ] open — Identity products (8) — hooks only, no IdP
- [ ] open — EDR/XDR agents (7)
- [ ] open — Phishing simulation / training (7)
- [ ] open — DLP / insider monitoring engines (7)
- [ ] open — AppSec testing engines (6)
- [ ] open — CSPM/CNAPP/SSPM posture engines (5)
- [ ] open — Log / telemetry pipelines (5)
- [ ] open — Vulnerability scanners (4) — ingestion and tracking is core
- [ ] open — CUI enclaves / VDI (3)
- [ ] open — Identity proofing / fraud (2)
- [ ] open — Endpoint management agents (2)

Platform note: encryption is TLS when configured; at rest is deployment-layer.

## Group 5 — Accounting L2 (21 forks)

Extended families, specified in groups/accounting-l2/UNION-SPEC.md, not implemented:
- [ ] open — AI / analytics & BI
- [ ] open — Project / program / portfolio management
- [ ] open — Risk register / GRC suites (separation of duties, approvals, and the audit trail are the in-core seed)
- [ ] open — Audit management workbenches (the core carries the audit trail, not audit management)
- [ ] open — Fixed-asset registers
- [ ] open — Records retention
- [ ] open — Forecasting / EPM
- [ ] open — Supply chain
- [ ] open — GovCon / grants
- [ ] open — Crypto investigation
- [ ] open — Time tracking
- [ ] open — E-signature
- [ ] open — Payroll
- [ ] open — Tax
- [ ] open — Forensic investigation

Platform note: encryption is TLS when configured; at rest is deployment-layer. Documented wording gap (not papered over): no sibling description says "general ledger," "double-entry," "payable," or "receivable"; the double-entry journal is in the core as the defining mechanism of the accounting_core family (8 siblings), and standalone AP/AR modules were not invented.

## Group 7 — Analytics L1 (16 forks)

Extended functions, specified in groups/analytics-l1/UNION-SPEC.md, not implemented (8):
- [ ] open — Real-time / streaming (8 of 16 — joint-largest family in this group, its biggest gap)
- [ ] open — Proprietary-source connectors (5) — core covers open CSV/JSON only
- [ ] open — Predictive ML, remainder of the statistics/ML family (5)
- [ ] open — Alerts / monitoring (3)
- [ ] open — Collaboration (3)
- [ ] open — Archiving (2)
- [ ] open — Transformation (1)
- [ ] open — Text / NLP (1)

Platform-layer, gap-listed not claimed: encryption at rest (deployment layer); production identity/authenticator strength (demo identities are hooks; IA-2 stays with the embedding organization); TLS only when configured. Tier precision recorded in the spec: the union of Low and LI-SaaS baselines is NIST SP 800-53 Low (LI-SaaS is a tailored subset, adds nothing); audit traces to the AU family on the FedRAMP Low side only, because FAR 52.204-21 carries no audit practice; Moderate/High apparatus was deliberately not inherited downward. Seven taxonomy functions (geospatial, governance, encryption, KPI, self-service BI, scheduling, media) are claimed by zero siblings in this group and are absent from its union entirely.

## Group 6 — Collaboration L3-adjacent (17 forks)

Extended functions, specified in groups/collaboration-l3/UNION-SPEC.md, not implemented (9):
- [ ] open — Workflow / process-automation engines (4 siblings)
- [ ] open — AI assistance & speech (5)
- [ ] open — Records & governance beyond the versioning/audit seed (5)
- [ ] open — Voice / telephony / contact center (2)
- [ ] open — Task & project management beyond board cards (2)
- [ ] open — Learning / training / mentoring (1)
- [ ] open — Knowledge management (0 claims in this group; carried from the L2 union)
- [ ] open — Meetings / video media transport (0 claims in this group)
- [ ] open — E-signature (0 claims in this group)

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Group character recorded in the spec: at High this is an enclave group — listings are boundary prose, claim mass sits in platform families (APIs 10 of 17), and the L2 core was carried upward whole because a wording artifact is not a downgrade.

## Group 9 — Artificial Intelligence (AI) L2 (11 forks)

The final batch's largest single item lives here:
- [ ] open — Learned AI/ML inference: real LLMs, ML, NLU, and predictive models (8 of 11 forks claim it; the group's #1 family). Each vendor's models are their own; the shipped core's responder is a deterministic reference stub (echo/template/rules) labeled `reference_stub: true` on every response, and is not a substitute for inference.

Other extended families, specified in groups/ai-l2/UNION-SPEC.md, not implemented:
- [ ] open — Agentic & automated workflow engines (4)
- [ ] open — Document processing & generation workloads (4)
- [ ] open — Analytics, dashboards & reporting (2)
- [ ] open — Contact center & customer experience (1)
- [ ] open — Vertical domain applications: compliance/ERP enclave, IT asset management, electronics data exchange, manufacturing QC, requirements management, acquisition support, cloud infrastructure (one sibling each)

Platform notes: multi-tenancy (6 claim it) — the build is a single-tenant reference deployment, tenant isolation is deployment-layer; encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP.

## Group 8 — Cybersecurity & Risk Management L3-adjacent (16 forks)

Extended functions, specified in groups/cybersecurity-l3/UNION-SPEC.md, not implemented (18). Same engine families as Group 4, carried to the High tier; the shipped build is the defensive substrate only:
- [ ] open — Identity products (IdP / PAM / IGA / MFA engines)
- [ ] open — Endpoint management agents
- [ ] open — DLP engines
- [ ] open — AI/ML detection models
- [ ] open — Network enforcement planes
- [ ] open — Backup & recovery products
- [ ] open — SOAR / workflow automation
- [ ] open — Threat-intelligence feeds
- [ ] open — EDR agents
- [ ] open — Cloud / SaaS posture engines
- [ ] open — Phishing simulation / training content
- [ ] open — Fraud / identity-proofing products
- [ ] open — AppSec engines
- [ ] open — Log pipelines
- [ ] open — CUI enclaves / VDI
- [ ] open — Vulnerability scanners (ingestion and tracking is core)
- [ ] open — Plus the substrate-adjacent families named in the spec's long tail (2)

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12).

## Group 10 — Collaboration L1 (10 forks)

Extended functions, specified in groups/collaboration-l1/UNION-SPEC.md, not implemented (9):
- [ ] open — AI assistance / speech / analytics (4 of 10 — this group's top tagged family)
- [ ] open — Workflow / process automation (1)
- [ ] open — Learning / training / mentoring (1)
- [ ] open — Knowledge management (1)
- [ ] open — Voice / telephony / contact center
- [ ] open — Task & project management beyond board cards
- [ ] open — Records & governance beyond the versioning/audit seed
- [ ] open — Meetings / video media transport
- [ ] open — E-signature

Platform-layer: encryption at rest (deployment layer); production identity / authenticator strength (demo identities are hooks; IA-2 stays with the embedding organization); TLS only when configured. Spec honesty note: this group's descriptions are marketing prose, only 15 claims tag across 6 of 10 sheets (four tag nothing), and six Core functions tag zero claims — they stay Core under the recorded core-boundary decision (they define the category and the products presuppose them; the taxonomy was deliberately not re-tuned, preserving cross-group comparability), so all counts are a stated floor. Tier precision: audit traces to AU-2/AU-3 on the FedRAMP Low side only; Group 2's Moderate citations were not imported.

## Group 11 — Communication L2 (10 forks)

Extended functions, specified in groups/communication-l2/UNION-SPEC.md, not implemented:
- [ ] open — Email security & threat-detection engines (behavioral baselining, detonation, quarantine)
- [ ] open — AI/ML models and virtual-assistant intelligence (incl. conversational IVR)
- [ ] open — Voice / telephony media, IVR conversation engines, carrier integration
- [ ] open — Video / media transport (claimed by 0 of 10 descriptions; named for completeness)
- [ ] open — Archiving & eDiscovery engines (multi-channel capture, retention/disposition, legal holds, FOIA production)
- [ ] open — Correspondence / casework depth (incl. inter-organization exchange)
- [ ] open — Key & certificate lifecycle automation (CA connectors, issuance, deployment)
- [ ] open — End-to-end encrypted message transport and identity proofing
- [ ] open — Personnel / asset tracking platform (devices, live location, geofencing)
- [ ] open — Permits / passes / surveys and payment processing
- [ ] open — E-signature execution
- [ ] open — Workflow / BPM engines and reporting / analytics engines beyond the records substrate

Platform-layer: encryption at rest (deployment layer); TLS only when a certificate is configured; multi-tenancy (the build is a single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). The shipped core's dispatch runs through a deterministic reference transport labeled `reference_transport: true` on every receipt; it moves no real messages.

## Group 13 — Education & Training L2 (8 forks)

Extended functions, specified in groups/education-training-l2/UNION-SPEC.md, not implemented:
- [ ] open — Talent, skills & marketplace matching (incl. career exploration / coaching and AI career assistants) (3 of 8)
- [ ] open — Recruiting, HCM / HRIS & workforce management suites (incl. performance and policy management)
- [ ] open — Course content authoring & delivery, media streaming
- [ ] open — Simulation engines (capture, debriefing & playback); the simulation records are Core, the engine is not
- [ ] open — Remote proctoring & identity proofing (0 of 8 claims; explicitly not inferred from "secure assessment delivery")
- [ ] open — Deterministic scoring & AI grading (0 of 8; assessments are administration records only, no score field exists by design)
- [ ] open — General cloud hosting / PaaS (4 of 8; multi-tenancy is a deployment property)
- [ ] open — Collaboration & social learning (1 of 8)
- [ ] open — Data storage & processing services beyond the substrate's own records
- [ ] open — Notifications & reminders (0 of 8)
- [ ] open — Integrations & APIs as a union function (0 of 8)

Platform-layer: single-tenant reference deployment; encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Certificates are records only (issuance claimed by 0 of 8).

## Group 12 — Data Management L2 (8 forks)

Extended functions, specified in groups/data-management-l2/UNION-SPEC.md, not implemented (16):
- [ ] open — Distributed storage engines (data lake / warehouse internals, database engines, replication)
- [ ] open — Integration runtime & connector engine (iPaaS execution)
- [ ] open — PPRL record-linkage engine & de-identification engines
- [ ] open — Enterprise search indexing engine (the core searches registry metadata)
- [ ] open — Content processing engines (OCR, transcription, categorization)
- [ ] open — Workflow / BPM execution & guided-interview engines
- [ ] open — Query & visualization engines
- [ ] open — IaaS / PaaS hosting (compute, private cloud, DaaS, AaaS)
- [ ] open — Kubernetes provisioning & cluster lifecycle engine
- [ ] open — Asset inspection & capital-planning applications
- [ ] open — Managed file transfer transport
- [ ] open — Case management depth (vetting / adjudication)
- [ ] open — AI/ML analytics & orchestration in bundled applications
- [ ] open — Field-level / transformation lineage beyond ingestion records (the build's provenance is bounded to ingestion granularity, stated in the spec)
- [ ] open — Retention disposition execution (deletion / archival engines, NARA / FOIA production; the core schedules and reports due state only)
- [ ] open — Plus the families named in the spec's long tail

Platform-layer: encryption at rest (deployment layer; TLS when configured); multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Recorded findings: no sibling claims a storage engine as a customer-facing function, and none claims field-level lineage.

## Group 15 — Contact Center L2 (5 forks)

Extended functions, specified in groups/contact-center-l2/UNION-SPEC.md, not implemented:
- [ ] open — PAM & Zero Trust enforcement engines (incl. just-in-time privileged access, session recording)
- [ ] open — Identity risk analytics & prescriptive recommendations
- [ ] open — Observability collection engines (collectors, metric collection, forecasting)
- [ ] open — Voice / telephony media & the callback connection engine (incl. ACD routing)
- [ ] open — Claims adjudication & fraud / waste / abuse detection engines (incl. rules execution; the core keeps a rule registry only)
- [ ] open — Personnel-security / facility-clearance management depth
- [ ] open — Integration connector engines
- [ ] open — AI/ML models (1 claim)
- [ ] open — Knowledge-base articles (0 of 5 claims; named absence)
- [ ] open — Satisfaction / CSAT surveys (0 of 5 claims; named absence)
- [ ] open — SLA policy engine (tiers, business-hour calendars, escalation; 0 of 5 claim SLA terms; the core derives breach from a per-case due time only)

Platform-layer: multi-tenancy (single-tenant reference deployment); encryption at rest (deployment layer); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec finding: this sibling group is largely a source-category artifact — only one of the five is genuinely a contact-center product; the build is the records substrate their claimed functions collectively presuppose. Privacy note: caller references are stored as opaque caller-supplied references only, never real phone numbers.

## Group 14 — Communication L3-adjacent (6 forks)

Extended functions, specified in groups/communication-l3/UNION-SPEC.md, not implemented:
- [ ] open — Workflow / BPM engines beyond the approval-less dispatch substrate
- [ ] open — End-to-end encrypted message transport and secure data-exchange networks; fax transport networks and carrier integration
- [ ] open — Key & certificate lifecycle automation (CA connectors, issuance, deployment)
- [ ] open — Voice / telephony media, IVR and virtual-agent conversation engines; mission-critical voice ecosystems
- [ ] open — Virtual-workspace streaming and remote-experience delivery; edge delivery / CDN platform functions
- [ ] open — Carried from the Group 11 union at this tier (0 claims in this group's descriptions; named so the union is complete): email security engines, AI/ML models, archiving & eDiscovery engines, correspondence / casework depth, personnel / asset tracking, permits / passes / surveys, e-signature execution, payment processing, reporting / analytics engines beyond the records substrate

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP. Spec honesty note: 11 claims across 5 of 6 sheets; one sheet (a cloud delivery platform) is accreditation prose with no taxonomy vocabulary — full text preserved, nothing invented.

## Group 16 — Cybersecurity & Risk Management L1 (5 forks)

Extended functions, specified in groups/cybersecurity-l1/UNION-SPEC.md, not implemented. Claimed in this group:
- [ ] open — AI/ML-powered analytics & anomaly detection models (2 of 5)
- [ ] open — Full GRC automation suites beyond the substrate (3 of 5 claim the family; control mapping & assessment records are Core)
- [ ] open — Automation & orchestration engines (SOAR / workflow) (1)
- [ ] open — Identity products / IdP (1; the core ships access-control hooks only)
- [ ] open — Phishing-defense enforcement & simulation / training content (1; DMARC enforcement)

Remainders of Core-substrate families: detection engines & staffed SOC services; vulnerability scanners (ingest / consolidation / tracking is Core).

Carried at 0 claims in this group, named for the final batch and cross-group comparability: network security / segmentation / zero-trust enforcement planes; threat intelligence; backup, recovery & data protection; EDR / XDR agents; insider risk / DLP engines; AppSec testing engines; CSPM / CNAPP / SSPM posture engines; log & telemetry pipelines; secure enclave / VDI for CUI; identity proofing & fraud prevention; endpoint management / patching agents.

Platform-layer: encryption & key management (TLS when a certificate is configured; encryption at rest is deployment-layer, not claimed); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Tier precision: five Core taxonomy families tag 0 claims in this group and are carried as Core by design, recorded in the spec as carried, not claimed; Group 8's High apparatus is explicitly not inherited downward and not claimed.

## Group 17 — Development Tools L1 (5 forks)

Extended functions, specified in groups/development-tools-l1/UNION-SPEC.md, not implemented (9):
- [ ] open — CI/CD execution engines (pipeline execution: build / test / deploy runners)
- [ ] open — Code hosting internals (git storage, branching & merging engines)
- [ ] open — Compilers & build toolchains
- [ ] open — Configuration-as-code execution & orchestration
- [ ] open — Compliance assessment & KSI status automation engines
- [ ] open — Business modeling & automation engines (modeling + execution)
- [ ] open — Course & content authoring tools
- [ ] open — Landing-zone / tenant provisioning & hosted platform operations
- [ ] open — Artifact binary storage backends (the registry holds records + checksums only; verification is by content hash)

Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Group character, recorded in the spec: only two of the five are genuine development tools; the union is a development-lifecycle records substrate. Five taxonomy families sit at 0 of 5 claims (artifact registry, API / integrations, access control, audit logging, search); four enter the Core only as flagged substrate / baseline items, and API / integrations is absent from the union entirely.

## Group 18 — Health & Wellness L2 (5 forks)

Extended functions, specified in groups/health-wellness-l2/UNION-SPEC.md, not implemented:
- [ ] open — Clinical decision support (0 standalone claims)
- [ ] open — EMR / EHR integration engines & documentation depth (2 of 5 claim the family)
- [ ] open — Medical claims adjudication engine (2 of 5; the core keeps eligibility / coverage records only)
- [ ] open — Device connectivity / sync pipelines (1 of 5)
- [ ] open — AI/ML models & personalization engines (1 of 5)
- [ ] open — Automation / workflow engines (1 of 5)
- [ ] open — Survey instruments depth (within patient engagement, 2 of 5)
- [ ] open — Patient engagement channels & content (2 of 5; care guidance 1 of 5)
- [ ] open — Telehealth media (0 claims; named absence)
- [ ] open — Multi-device native apps (platform property, 2 of 5)
- [ ] open — Hosting platform (1 of 5)

Platform-layer: single-tenant reference deployment; encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Privacy discipline (hard rule, enforced by tests): the build stores records and opaque caller-supplied references only — no diagnosis fields, no free-text clinical notes, no real identifiers in any entity shape; RBAC and audit are carried in the Core as baseline substrate at 0 of 5 claims, recorded as carried, not claimed.

## Group 20 — Content Management System (CMS) L2 (4 forks)

Extended functions, specified in groups/cms-l2/UNION-SPEC.md, not implemented:
- [ ] open — Rendering & templating engines and visual / WYSIWYG editors
- [ ] open — CDN / delivery network and runtime site serving
- [ ] open — Enterprise search indexing engines (Boolean / concept / fuzzy / multilingual / hierarchical / geospatial; the core searches registry metadata)
- [ ] open — Bulk ingestion & index-in-place engines
- [ ] open — Library ILS vertical (circulation, MARC21 cataloging depth, EDI acquisitions, discovery layer)
- [ ] open — BPM / case-management engine (EEO, labor relations, accommodations, background investigations, IG casework)
- [ ] open — Participant engagement & research platform vertical
- [ ] open — Platform hosting itself (PaaS runtime)
- [ ] open — Personalization / experience optimization
- [ ] open — Editorial workflow engines beyond lifecycle mechanics (parallel review, routing, notifications; claimed by no sibling)

Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Named absences recorded in the spec: no sibling claims editorial review workflow, versioning, publish scheduling, WYSIWYG editing, templating / rendering, or personalization; the build's lifecycle states, revisions, and publish windows are documented as registry mechanics of the claimed content-registry / publishing families (the Group 10 core-boundary precedent), never as claimed families.

## Group 19 — Construction L2 (4 forks)

Extended functions, specified in groups/construction-l2/UNION-SPEC.md, not implemented:
- [ ] open — Cost estimating engines & the proprietary cost data behind them (estimate records are Core)
- [ ] open — GPS / location tracking platform & mobile field data collection
- [ ] open — Fleet & vehicle telematics (vehicle monitoring, driver-behavior score cards)
- [ ] open — Contract-lifecycle workflow engines, template & clause libraries, negotiation playbooks with redlining
- [ ] open — E-signature execution
- [ ] open — AI/ML models (AI data extraction & negotiation assistance) (1)
- [ ] open — Workflow / process automation engines (2; lifecycle state machines are the in-core seed)
- [ ] open — Prevailing-wage determination depth (rate tables, fringe calculation, certified-payroll generation / e-filing)
- [ ] open — Dispatch routing & optimization

Platform-layer: multi-tenancy (2 of 4 claim it in prose; single-tenant reference deployment); encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Privacy discipline: worker records hold opaque caller-supplied references only; payroll records hold aggregate wage totals, never per-worker pay. Spec note: six taxonomy families tag 0 of 4 descriptions; four (submittal / RFI, schedule / milestones, inspection / punch-list, safety incidents) are carried into the Core explicitly flagged carried, not claimed, as the record types the category is defined by.

## Group 21 — Human Resources L2 (4 forks)

Extended functions, specified in groups/human-resources-l2/UNION-SPEC.md, not implemented (16):
- [ ] open — AI talent intelligence & matching engines (the group's AI flagship)
- [ ] open — Applicant-tracking workflow engines (end-to-end hiring workflow automation, job-board posting / sync)
- [ ] open — Position classification intelligence (series & grade recommendation tools)
- [ ] open — Job analysis & crediting-plan tooling
- [ ] open — Assessment delivery via third-party providers & assessment content
- [ ] open — Weighted cumulative & consensus scoring computation (ratings are Core records, stored verbatim; no aggregate field exists by design)
- [ ] open — Certificates of eligibles as standalone assembled documents (the referral stage is Core)
- [ ] open — Career sites, talent communities, campus recruiting & events platforms
- [ ] open — Talent mobility & workforce-exchange marketplace engines
- [ ] open — Talent management suite depth beyond records
- [ ] open — Workforce planning & resource-management analytics / models
- [ ] open — Retirement benefits calculator
- [ ] open — Employee learning & upskilling delivery
- [ ] open — Integration connector engines (job boards, personnel-record and payroll-center systems, agency HRIS sync)
- [ ] open — Document & template assembly engines
- [ ] open — General cloud hosting / platform services

Platform-layer: single-tenant reference deployment; encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Privacy discipline (structural, tested on the record shapes): persons are keyed by opaque caller-supplied references only; no field in any entity can hold a real name, SSN, DOB, salary figure, address, phone, or email. Named absences (0 of 4 claims, verified; not gaps because unclaimed): leave & time-off, policy acknowledgements, payroll execution, background checks, salary / compensation administration, time & attendance.

## Group 22 — Artificial Intelligence (AI) L3-adjacent (3 forks)

- [ ] open — Learned AI/ML inference: real LLMs / ML / NLU / predictive models (3 of 3 claim it; with Group 9's, the final batch's largest single item). The reference responder is a labeled stub, not a substitute.
- [ ] open — Agentic & automated workflow engines (1)
- [ ] open — Document processing & generation workloads (0 tagged under the verbatim taxonomy; one sibling's entire domain in prose, recorded as a near-miss, not invented)
- [ ] open — Analytics, dashboards & reporting (0 in this group; carried from the Group 9 union)
- [ ] open — Contact center & customer experience (0 in this group; carried from the Group 9 union)
- [ ] open — Vertical domain applications: AI software-development platform, ML lifecycle development & governance platform, digitization-as-a-service (one sibling each)

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform note: multi-tenancy (1 tagged claim) — single-tenant reference deployment, tenant isolation is deployment-layer; demo identities are hooks, not an IdP. Spec note: 13 of 16 taxonomy functions tag zero claims in this group (short marketing descriptions); the platform functions stay Core under the recorded core-boundary decision, because the Merge Rule carries the L2 union upward whole.

## Group 24 — Content Management System (CMS) L1 (2 forks)

Extended functions, specified in groups/cms-l1/UNION-SPEC.md, not implemented:
- [ ] open — Library ILS vertical (this group's dominant vertical): circulation, acquisitions, resource sharing / interlibrary loan, collection management, knowledgebase, access proxying, digital collection management, and the union-catalog data network beneath them
- [ ] open — Mobile application delivery and the companion mobile app itself
- [ ] open — Rendering & templating engines and visual / WYSIWYG editors (carried from the Group 20 union; 0 claims here)
- [ ] open — CDN / delivery network and runtime site serving (carried; one sibling's "content delivery functionality" is a recorded near-miss)
- [ ] open — Enterprise search indexing & discovery engines (carried; one sibling's discovery service is a recorded near-miss)
- [ ] open — Analytics & reporting engines beyond registry reporting (carried; "custom reports / Report Designer" are recorded near-misses)
- [ ] open — Bulk ingestion & index-in-place engines (carried)
- [ ] open — BPM / case-management engine; participant engagement vertical; personalization (carried from the Group 20 union at 0 claims here)

Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (one sibling claims it in prose; single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec honesty note: exactly one claim tags in this entire group under the verbatim Group 20 taxonomy; every near-miss is itemized in the spec's artifact log, the taxonomy was not re-tuned, and the 12-function core stands on an explicit core-boundary decision (both products presuppose the substrate in their own words). Tier precision: SI-7 is a Moderate selection and is explicitly not claimed at this tier; the asset checksums are an SI-family implementation property.

## Group 23 — Accounting L3-adjacent (2 forks)

Extended families carried from the Group 5 union, specified in groups/accounting-l3/UNION-SPEC.md, not implemented:
- [ ] open — AI / analytics & BI (this group's only claimed Extended family, 1 of 2)
- [ ] open — Project / program / portfolio management
- [ ] open — Risk register & GRC suites beyond the separation-of-duties / audit seed
- [ ] open — Audit-management workbenches
- [ ] open — Fixed-asset registers
- [ ] open — Records retention beyond the audit seed
- [ ] open — Forecasting / EPM
- [ ] open — Supply chain
- [ ] open — GovCon / grants specifics
- [ ] open — Crypto investigation
- [ ] open — Time tracking
- [ ] open — E-signature
- [ ] open — Payroll
- [ ] open — Tax support
- [ ] open — Forensic investigation

Members' own domains, not built here (they belong to their own categories' groups): one sibling's LLM / RPA acquisition platform; the other's sovereign cloud / DaaS enclave (a zero-claim sheet in this group: sovereign-cloud prose, full text preserved, nothing invented).

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Spec note: the 13 Core functions tag zero claims in this group and stay Core under the recorded core-boundary decision (the Merge Rule carries the L2 union upward whole; a wording artifact is not a downgrade).

## Group 26 — Customer Service L1 (2 forks)

Extended functions, specified in groups/customer-service-l1/UNION-SPEC.md, not implemented:
- [ ] open — Event detection, diagnosis & orchestration engines (alert records / triage are Core)
- [ ] open — Automation execution engines (the rule registry is Core; nothing executes, pinned by test)
- [ ] open — GRC platform (one sibling's sole claim family, incl. compliance-framework support depth)
- [ ] open — Real-time channels: live chat, voice / telephony (0 claims; named)
- [ ] open — AI assistance / deflection (0 tagged claims; near-miss recorded)
- [ ] open — Knowledge base articles (0 of 2; named absence)
- [ ] open — Satisfaction / CSAT surveys (0 of 2; named absence)
- [ ] open — SLA policy engine (due / breach derivation only in Core; no sibling claims SLA terms)
- [ ] open — Notification delivery & status-page hosting (status records / view are Core; delivery is not)
- [ ] open — Reporting / analytics engines beyond registry reporting (0 claims)

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec finding: this group is largely a source-category artifact — one sibling is a GRC platform claiming zero customer-service functions; the build is the records substrate the other sibling's claims presuppose, and nothing was invented to make the two look alike.

## Group 25 — Customer Relations Management (CRM) L2 (2 forks)

Extended functions, specified in groups/crm-l2/UNION-SPEC.md, not implemented:
- [ ] open — Customer-service casework depth (knowledge-driven agent desktops, self-service portals, chat / chatbot channels)
- [ ] open — Guidance delivery runtime (in-app overlay engine + codeless authoring tooling)
- [ ] open — Gap-identification & adoption-analytics engines (telemetry collection, gap detection, engagement analytics beyond record counts)
- [ ] open — Customization & module engines (add-on module execution, codeless configuration runtimes)
- [ ] open — Knowledge base & self-service content (0 claims here)
- [ ] open — Marketing-automation engines & email delivery (0 claims here)
- [ ] open — AI/ML models & scoring (0 claims here; no score is computed anywhere in the core, by design)
- [ ] open — Integration connector engines (0 claims here; near-miss recorded)

Platform-layer: multi-tenancy (single-tenant reference deployment); encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization); the hosting / delivery platform both siblings assert in prose is the deployment layer itself. Named absences (not gaps, unclaimed): opportunity / pipeline and campaign / lists — neither description contains sales vocabulary at all. Privacy discipline is test-enforced on the record shapes (opaque references only), and gap-finding records carry detail verbatim with no score field anywhere.

## Group 27 — Customer Service L2 (2 forks)

Extended functions, specified in groups/customer-service-l2/UNION-SPEC.md, not implemented:
- [ ] open — Commerce platform hosting & point-of-sale systems (one sibling's entire domain: POS hosting for grocery / gas / loyalty / food-ordering, commerce applications, commerce API platform)
- [ ] open — PCS relocation platform (the other sibling's domain: relocation financial workflows from obligation to financial-system interfaces, travel-voucher processing, supplier integration)
- [ ] open — Automation execution engines (the rule registry is Core; one sibling's automation prose is a recorded near-miss, 0 tagged claims)
- [ ] open — E-signature execution & PIV-based signer identity assurance (prose present in one sibling; 0 tagged claims)
- [ ] open — Event detection, diagnosis & orchestration engines (0 claims here; carried from the Group 26 union)
- [ ] open — GRC platform (0 claims here; carried from the Group 26 union)
- [ ] open — Real-time channels: live chat, voice / telephony (0 claims; named)
- [ ] open — AI assistance / deflection (0 claims; named)
- [ ] open — Knowledge base articles (0 of 2; named absence at both tiers)
- [ ] open — Satisfaction / CSAT surveys (0 of 2; named absence; near-miss recorded)
- [ ] open — SLA policy engine (due / breach derivation only in Core; no sibling at either tier claims SLA terms)
- [ ] open — Notification delivery & status-page hosting (status records / view are Core; delivery is not)
- [ ] open — Reporting / analytics engines beyond registry reporting (reporting is this group's sole claim, 1 of 2)

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec finding: this group is a source-category artifact at both forks — one claims zero functions of any family (and is not self-categorized in the source), the other's sole claim is generic platform reporting; neither claims any core customer-service function, and the substrate stands on a recorded core-boundary decision rather than on claims.

## Group 28 — Data Management L3-adjacent (2 forks)

Extended families carried from the Group 12 union, specified in groups/data-management-l3/UNION-SPEC.md, not implemented:
- [ ] open — Distributed storage engines
- [ ] open — Integration runtime & connector engine
- [ ] open — PPRL record-linkage & de-identification engines
- [ ] open — Enterprise search indexing engine
- [ ] open — Content processing engines (OCR / transcription / categorization)
- [ ] open — Workflow / BPM & guided-interview engines
- [ ] open — Query & visualization engines
- [ ] open — IaaS / PaaS hosting; Kubernetes provisioning engine
- [ ] open — Asset inspection & capital-planning apps
- [ ] open — Managed file transfer transport (claimed outright by one sibling at this tier; transfers in the core are ingestion-shaped records)
- [ ] open — Case management depth
- [ ] open — AI/ML analytics in bundled apps
- [ ] open — Field-level / transformation lineage (provenance stays bounded to ingestion granularity)
- [ ] open — Retention disposition execution

This group's own verticals: digital-evidence management depth (playback, redaction, disclosure), device fleet control (body-worn / in-car cameras, conducted-energy devices, interview rooms), real-time operations platform, records / report-writing automation; secure transfer & sharing platform depth (working web / email / SFTP / MFT / API transports), secure data forms, possessionless editing, DLP / CDR / antivirus engines, customer-managed keys, SIEM forwarding.

Baseline gaps at High (platform layer; gap-listed, never implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5; one sibling advertises MFA and PIV/CAC/TOTP as product features of the identity layer this build deliberately does not ship); FIPS-validated cryptography (SC-13; one sibling claims FIPS 140-3 validated modules, and this build does not inherit that claim); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform notes: TLS only when configured; single-tenant reference deployment; demo identities are hooks, not an IdP.

## Group 29 — Development Tools L2 (2 forks)

Extended functions carried from the Group 17 union, specified in groups/development-tools-l2/UNION-SPEC.md, not implemented:
- [ ] open — CI/CD execution engines (pipeline execution: build / test / deploy runners; claimed 1 of 2 here)
- [ ] open — Code hosting internals (git storage, branching & merging engines; 0 claims here)
- [ ] open — Compilers & build toolchains
- [ ] open — Configuration-as-code execution & orchestration (0 claims here; "strict configuration control" is a recorded near-miss)
- [ ] open — Compliance assessment & KSI status automation engines (0 claims here)
- [ ] open — Business modeling & automation engines (modeling plus execution)
- [ ] open — Course & content authoring tools
- [ ] open — Landing-zone / tenant provisioning & hosted platform operations (0 claims here; "environment management" near-miss)
- [ ] open — Artifact binary storage backends (the registry holds records + checksums only)

New in this group:
- [ ] open — Feature-flag & feature-management runtime (flag evaluation, targeting, percentage rollouts, kill-switch)
- [ ] open — Experimentation engine (hypothesis-driven development)
- [ ] open — Static code analysis engine (rule sets, quality profiles & gates)
- [ ] open — Security posture monitoring & automated remediation engine
- [ ] open — Release automation, environment management & data migration engine
- [ ] open — External-system integration engines (claimed 1 of 2 here)

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: the two forks share no claimed family, and the release family drops to 0 of 2 on phrasing alone despite both descriptions being saturated with release vocabulary — recorded as near-misses, not rounded up.

## Group 30 — Education & Training L1 (2 forks)

Extended functions, specified in groups/education-training-l1/UNION-SPEC.md, not implemented:
- [ ] open — Adaptive learning / knowledge-gap remediation engine (one sibling's patented algorithms, described in prose; 0 tagged claims — the verbatim taxonomy was not re-tuned to capture it)
- [ ] open — Talent, skills & marketplace matching incl. career exploration / coaching and AI career assistants (carried from the Group 13 union; 0 claims here)
- [ ] open — Recruiting, HCM / HRIS & workforce management suites incl. performance and policy management (carried; 0 claims here)
- [ ] open — Course content authoring & delivery, media streaming (carried; 0 claims here)
- [ ] open — Simulation engines: capture, debriefing & playback (carried; 0 claims here)
- [ ] open — Remote proctoring & identity proofing (0 claims in either tier of this category)
- [ ] open — Deterministic scoring & AI grading (0 claims in either tier; assessments are administration records only, no score field by design)
- [ ] open — Collaboration & social learning (carried; 0 claims here)
- [ ] open — Data storage & processing services beyond the substrate's own records (carried; 0 claims here)
- [ ] open — Notifications & reminders (0 claims in either tier)
- [ ] open — Integrations & APIs as a union function (0 claims in either tier)

Platform-layer: general cloud hosting / PaaS incl. multi-tenancy (this group's sole tagged family, 1 of 2; single-tenant reference deployment); encryption at rest (deployment layer); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: exactly one claim tags in this group (a platform property, not a learning function); all ten core functions are carried, not claimed, under an explicit core-boundary decision, and Group 13's two records-only decisions (no computed scores, no credential issuance) carry on this group's own 0-of-2 evidence.

## Group 32 — Fleet Management L1 (2 forks)

Extended functions, specified in groups/fleet-management-l1/UNION-SPEC.md, not implemented:
- [ ] open — Live telematics & GPS streaming (0 claims in this group; named)
- [ ] open — Dispatch routing & optimization (0 claims; named)
- [ ] open — ELD / hours-of-service integrations (0 claims; named)
- [ ] open — Demand & capacity forecasting engine (claimed 1 of 2)
- [ ] open — EV charging station communication & session control (claimed 1 of 2; the core holds charging session records only, no live station communication)
- [ ] open — Payment processing (claimed 1 of 2)
- [ ] open — Analytics & utilization-optimization engines beyond registry reporting (claimed 1 of 2)
- [ ] open — Hosted platform operations (platform-layer)

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: API & integrations is a named absence (0 of 2), absent from the union entirely. Three core functions are carried, not claimed, and flagged in the spec: maintenance & inspection records (0 of 2; the due status is derived at read time, never stored), search (0 of 2, substrate), and RBAC + audit (0 of 2, baseline-carried; audit traces to AU-2/AU-3 on the FedRAMP Low side only, because FAR 52.204-21 carries no audit practice). Privacy discipline: operator records are keyed by opaque caller-supplied references with the exact key set pinned by tests; no field can hold a real name or license number.

## Group 31 — Finance L2 (2 forks)

Extended functions, specified in groups/finance-l2/UNION-SPEC.md, not implemented:
- [ ] open — Instant disbursement execution / payment rails (ACH, wire, card networks): the execution remainder of the earned-wage-access claim; the core records disbursements and moves no money
- [ ] open — Travel booking execution engines (live air / hotel inventory, ticketing, reservation systems): the execution remainder of the travel-booking claim; the core holds booking records only
- [ ] open — Financial wellness delivery tools (the budgeting / coaching / savings products behind the offering registry): the execution remainder of the financial-wellness claim
- [ ] open — Streaming / real-time reporting pipelines (core reporting is computed on read from records)
- [ ] open — Banking integration & account verification (0 claims; entity shapes forbid real account identifiers by design)
- [ ] open — Payroll system integration & wage calculation (0 claims; accruals record amounts computed elsewhere)
- [ ] open — Lending & credit engines (0 claims; access is to already-earned wages only)
- [ ] open — Trading & investment execution (0 claims)
- [ ] open — Tax reporting & remittance (0 claims)
- [ ] open — GRC platform functions (0 claims in text; source category label only)

Platform-layer: encryption at rest is deployment-layer (TLS when configured); multi-tenancy (one sibling describes its own multi-tenant delivery; single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: the two siblings share zero claimed families — the union is two half-domains (earned-wage finance; group-travel finance) over one shared records substrate, money in integer cents only, disbursements recorded and never executed.

## Group 34 — Law Enforcement L2 (2 forks)

Extended functions, specified in groups/law-enforcement-l2/UNION-SPEC.md, not implemented:
- [ ] open — The legal corpora themselves (primary / secondary law content databases and practical-guidance content: content, editorial maintenance, licensing)
- [ ] open — Citation-validation engines (editorial systems that determine treatment; the core records a caller-supplied treatment and determines none)
- [ ] open — Editorial enhancement systems (headnotes, taxonomy assignment, enrichment pipelines)
- [ ] open — Corpus search & relevance engines (full-text indexing / ranking over the legal corpus; the core searches registry metadata only)
- [ ] open — AI/ML research assistance (0 claims in these descriptions; named for union completeness)
- [ ] open — Document content storage, rendering & redaction (the registry holds metadata + checksums only, by the privacy rule)

Category-discipline exclusions (0 claims, not built): surveillance, facial recognition, predictive policing, real-time intelligence feeds. Named absences (unclaimed, not built, not gaps): incident / case management, evidence management & chain of custody, criminal records / RMS, investigative case files — neither sibling is an operational law-enforcement platform; both are legal research platforms for government attorneys, and the core follows the claims.

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Privacy rule is structural: entity key sets are pinned by tests, smuggled fields are rejected by the store signatures, and search queries and annotation notes are stored as digests only.

## Group 33 — Governance, Risk, and Compliance (GRC) L2 (2 forks)

Extended functions, specified in groups/grc-l2/UNION-SPEC.md, not implemented:
- [ ] open — Automated evidence-validation engine, incl. API / telemetry evidence collection
- [ ] open — Continuous-monitoring feeds & scanner integrations
- [ ] open — Vulnerability scanning engine (prioritization / scoring of findings; the core records findings and remediation verbatim)
- [ ] open — Automated KSI validation
- [ ] open — Posture / risk scoring engines (deliberately absent from the core; no aggregate is computed anywhere)
- [ ] open — Hosted enclave & PaaS operations themselves (one sibling's own domain; also the other sibling's hosting claim)
- [ ] open — FedRAMP authorization package generation

Named absences (not gaps): risk register / risk management functions and policy management — 0 claims in either fork's own prose; no risk engine was rounded up from the category name. Extraction note: one sibling's description carries a "services undergoing approval for use — not authorized" block naming third-party services; that block was excluded before matching (it alone would have added three false families), and those services' domains are out of scope, not gaps this group owes.

Platform-layer: encryption at rest is deployment-layer (TLS when configured); single-tenant reference deployment; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization).

## Group 35 — Law Enforcement L3-adjacent (2 forks)

Cross-tier merge of Group 34 (cross-tier parent), uplifted to the High baseline. Both spec sheets are zero-claim sheets under Group 34's 9-family taxonomy applied verbatim (0 claims total, full descriptions preserved): both siblings (Cellebrite Government Cloud (CGC), Magnet One) are genuine digital-forensics platforms whose vocabulary the legal-research taxonomy does not reach. The L2 core (11 functions) is carried whole under the Merge Rule — 0 of 11 claimed by this group's forks — with the six High uplifts (hash-chained audit + verify_chain, GET /audit/verify, fail-closed audit writes with store rollback, audit query, AC-7 logon lockout, auditor role with audit_read only).

Extended functions, specified in groups/law-enforcement-l3/UNION-SPEC.md, not implemented — this group's own verticals, each a processing engine over evidence content the records substrate never holds:
- [ ] open — Device unlocking (Cellebrite)
- [ ] open — Evidence extraction from mobile devices (Cellebrite)
- [ ] open — Forensic analysis engines (both siblings)
- [ ] open — Evidence ingest & processing pipelines (Magnet One)
- [ ] open — Evidence review (Magnet One)
- [ ] open — Chain-of-custody enforcement over evidence (Cellebrite; the substrate's checksums / verify-by-content / hash chain are records-side analogues, stated as analogues, not equivalents)
- [ ] open — Information sharing / collaboration over evidence (both siblings)
- [ ] open — Forensic reporting (Cellebrite; beyond the substrate's counts-only registry reporting)

Extended carried from Group 34's section (still open at this tier): the legal corpora themselves; citation-validation engines; editorial enhancement systems; corpus search & relevance engines; AI/ML research assistance (0 claims at either tier); document content storage, rendering & redaction.

High platform gaps (named, not implied closed): MFA / authenticator management (IA-2(1)/(2), IA-5 — demo identities are hooks, not an IdP); FIPS-validated cryptography (SC-13 — Python stdlib is not a FIPS-validated module, not claimed); encryption at rest (SC-28 — deployment layer); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12 — per-request header auth, no session state).

Category-discipline exclusions (0 claims, not built): surveillance, facial recognition, predictive policing, real-time intelligence feeds. Named absences carried from Group 34 remain accurate for the legal-research side only (incident / case management, criminal records / RMS, investigative case files); the forensic evidence functions are this group's Extended verticals above, not named absences. Privacy rule unchanged and structural: opaque references only, digests only for queries and notes, smuggled fields rejected by the store signatures.

## Group 36 — Operations Management L2 (2 forks)

Extended functions, specified in groups/operations-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Workflow automation execution engine (the registry is Core; execution is the engine)
- [ ] open — Real-time intelligence & analytics engine (streaming intelligence, outcome analytics beyond registry reporting)
- [ ] open — AI models (1 claim)
- [ ] open — Low-code application builder & deployment engine
- [ ] open — Integration connector engines & catalog
- [ ] open — Mobile applications & offline sync
- [ ] open — Network connectivity services & cloud platform operations (platform-layer; one sibling's own service)
- [ ] open — Authorization service / identity provider (the build ships RBAC hooks, not an IdP)
- [ ] open — Common security services enforcement plane
- [ ] open — Policy enforcement plane (runtime enforcement across projects)
- [ ] open — Governance / compliance console engine (continuous compliance monitoring depth)
- [ ] open — Scheduling & rostering (0 of 2; named absence)
- [ ] open — IoT / telematics data collection (0 of 2; named absence)

Platform-layer: multi-tenancy (claimed by neither sibling; single-tenant reference deployment); encryption at rest is deployment-layer (TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: the two siblings share exactly 1 of 19 taxonomy families — two half-domains over one shared records substrate — and one sibling's boundary disclaimer (it does not produce, store, or transmit federal information) is recorded as tagging nothing.

## Singleton 37 — Communication L1 (1 fork)

Extended functions, specified in groups/communication-l1/UNION-SPEC.md, not implemented:
- [ ] open — Campaign orchestration engine (visual campaign orchestration, cross-channel campaign execution, campaign / journey lifecycle; the fork's signature function)
- [ ] open — Audience segmentation engine (targeted segmentation over audience data)
- [ ] open — Customer profile store & identity resolution (beyond the directory's contact records)
- [ ] open — Real-time interaction management (real-time decisioning / interaction handling)
- [ ] open — Workflow / BPM engine (campaign-creation workflow as an engine incl. approval chains; claim remainder — the approval-less dispatch substrate is Core)
- [ ] open — Reporting / analytics engines beyond the records substrate (campaign-effectiveness analytics and dashboards)
- [ ] open — Real channel execution (email / SMS / push delivery networks and direct-mail fulfillment; core dispatch is the labelled reference transport and transmits nothing)
- [ ] open — Managed-service operations (hosting / operating the platform itself)

Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: the fork's signature functions match no family in the category taxonomy (defined from the L2 group, where no sibling is a campaign platform); they are specified as gaps, not forced into families, and the taxonomy was not re-tuned.

## Singleton 38 — Data Management L1 (1 fork)

Extended functions new with this fork, specified in groups/data-management-l1/UNION-SPEC.md, not implemented:
- [ ] open — Web crawling & snapshot capture engine (the product's central function; the substrate records ingestions and captures nothing)
- [ ] open — Web page rendering for capture (dynamic / JS pages)
- [ ] open — Change detection & dynamic monitoring engine
- [ ] open — Archive storage, integrity sealing & replay / playback of captured pages (the substrate holds registry metadata only)
- [ ] open — Full-content search & indexing over the archive (core search is registry-metadata only)

The Group 12 category union's extended families (distributed storage, integration runtime, record linkage, search indexing, content processing, workflow, query / visualization, hosting, case depth, AI/ML, field-level lineage, retention disposition execution) are already registered under Groups 12 and 28 and are not re-registered here. Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork (three sentences of boundary prose); all twelve core functions are carried, not claimed, under an explicit core-boundary decision, and at this tier the never-self-approve guard traces to AC-3, AC-5 being lineage only (not a Low selection).

## Singleton 39 — CMS L3-adjacent (1 fork)

Extended functions new with this fork, specified in groups/cms-l3/UNION-SPEC.md, not implemented:
- [ ] open — Learned ML / AI classification engine (automatically classify physical and digital content)
- [ ] open — Learned ML / AI extraction engine (extract content / data from physical and digital content)
- [ ] open — Learned ML / AI enrichment engine (enrich content with derived metadata; the substrate stores caller-supplied metadata only and derives none)
- [ ] open — Physical-content intake & digitization pipeline (scanning / conversion of physical records into the platform)
- [ ] open — The content services platform runtime itself (hosting / delivery of the SaaS platform)

The Group 20 category union's extended families (rendering & templating engines, visual editors, CDN / delivery, enterprise search indexing, bulk ingestion, library ILS vertical, BPM / case engine, engagement vertical, personalization, editorial workflow engines beyond lifecycle mechanics) are already registered under Groups 20 and 24 and are not re-registered here. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork (a single-sentence description); all twelve core functions are carried, not claimed, under the Merge Rule, and no retention / disposition language is imported from the vendor's broader reputation.

## Singleton 40 — CRM L3-adjacent (1 fork)

Extended functions new with this fork, specified in groups/crm-l3/UNION-SPEC.md, not implemented:
- [ ] open — No-code / low-code application development engine & model-based design tooling (the description's central assertion; a near-miss to the configuration family, not a tagged claim)
- [ ] open — Case management & BPM / workflow execution engines (case automation, process orchestration, workflow execution; the substrate's case records are Core, the automation acting on cases is not)
- [ ] open — Decisioning engine (named in the source record, not in the description; record-named, not description-claimed)
- [ ] open — GenAI application tooling and AI / ML models generally (record-named as above)
- [ ] open — Managed cloud operations & application scaling platform (the deployment layer itself, operated)

The Group 25 category union's extended families (casework depth, guidance delivery runtime, gap-identification & adoption analytics, customization & module engines, knowledge base & self-service content, marketing automation, integration connectors) are already registered under Group 25 and are not re-registered here. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork (a five-sentence platform description with no taxonomy vocabulary); all ten core functions are carried, not claimed, under the Merge Rule.

## Singleton 42 — Finance L3-adjacent (1 fork)

The fork's own substance is a cloud infrastructure platform, platform layer rather than finance function, specified in groups/finance-l3/UNION-SPEC.md, not implemented:
- [ ] open — The cloud infrastructure platform itself (the provider's regions: compute, storage, networking, database, and the rest of the service catalog operated as infrastructure)
- [ ] open — Region operations & sovereignty properties (US-citizen / US-soil operation, ITAR environment, the regions' FedRAMP High boundary)
- [ ] open — Eligibility screening of root account holders
- [ ] open — Collaborative continuous monitoring with the provider

The Group 31 category union's extended families (instant disbursement execution / payment rails, travel booking execution engines, financial wellness delivery tools, streaming / real-time reporting pipelines) are already registered under Group 31 and are not re-registered here. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13 — the build explicitly does NOT inherit the fork's FIPS posture; stdlib is not a validated module); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (the fork operates multi-tenant regions in reality; single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork (region prose — ITAR, sovereignty, data-center inventory; not even the hosting family tags, and the category name in its business_categories list is a filing label, not a claim); all eleven core functions are carried, not claimed, under the Merge Rule. Named absences for the category at both tiers (not built, not gaps): banking integration & account verification, payroll integration & wage calculation, lending & credit, trading & investment execution, tax reporting & remittance, GRC platform functions.

## Singleton 41 — Customer Service L3-adjacent (1 fork)

The fork's own substance is a virtualized-environment hosting platform, specified in groups/customer-service-l3/UNION-SPEC.md, not implemented:
- [ ] open — Virtualization & cloud hosting platform (IaaS / PaaS / SaaS in one High boundary; the product itself)
- [ ] open — Authorization acceleration & control inheritance (assessment reuse across hosted customers)
- [ ] open — Continuous monitoring & SOC operations (24/7 SOC)
- [ ] open — Vulnerability management & patching operations
- [ ] open — Incident response operations (hosting boundary)
- [ ] open — Migration & lift-and-shift services (legacy / COTS, hybrid cloud)
- [ ] open — Hosted third-party application ecosystem (each catalogue application is its own vendor's product)

The Group 26/27 category union's extended families (event detection & orchestration engines, automation execution engines, GRC platform, real-time channels, AI assistance, SLA policy engine, notification delivery, reporting / analytics engines) are already registered under Groups 26 and 27 and are not re-registered here. Named absences at every tier (not gaps): knowledge base articles; satisfaction / CSAT surveys. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13 — the fork's "FIPS PUB 199 High" wording is an impact categorization, not a validated-module claim, and the build inherits neither reading); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (the fork is inherently multi-agency; the build is a single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork — its description's trailing catalogue of roughly twenty third-party hosted applications was excluded before matching (matching it would have manufactured six family hits, every one from another vendor's blurb), and its own prose is hosting-boundary prose; the source record does not even self-categorize the fork. All ten core functions are carried, not claimed, under the Merge Rule.

## Singleton 43 — GRC L1 (1 fork)

Extended functions new with this fork, specified in groups/grc-l1/UNION-SPEC.md, not implemented:
- [ ] open — Questionnaire automation engine (a named activity in the fork's prose that no taxonomy family names)
- [ ] open — Trust Center publication (customer-facing publication of the security program description / posture; core posture is internal counts)
- [ ] open — Vendor risk assessment engine (evaluating / scoring vendors — the risk claim's engine remainder; the records are Core and no score is computed)
- [ ] open — Continuous-monitoring engine & evidence-collection integrations (automated control checks and evidence collection from connected systems; overlaps Group 33's registered validation-engine and feed entries, named here from this fork's own claims)

The Group 33 category union's extended families (automated evidence validation, posture / risk scoring engines, workflow automation engines, vulnerability scanning engine, automated KSI validation, FedRAMP authorization package generation, hosted enclave & PaaS operations) are already registered under Group 33 and are not re-registered here. Named absence (not a gap): policy management — no policy vocabulary in the fork's prose, the same absence as at L2. Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the fork is FedRAMP Low (not LI-SaaS) and a FedRAMP 20x Class B Pilot participant, recorded as program context, not converted into claims; at L1 the audit trace holds on the FedRAMP Low side only (FAR 52.204-21 carries no audit practice), and no SI-7 claim is made.

## Singleton 44 — GRC L3-adjacent (1 fork)

The fork is a managed multi-tenant AI platform suite, not a GRC product; its GRC slice is one suite whose substance is AI prediction. Its own engines, specified in groups/grc-l3/UNION-SPEC.md, not implemented:
- [ ] open — AI accreditation & compliance prediction engine
- [ ] open — Continuous device-log monitoring & breach / vulnerability prediction (the engine half of the claimed continuous monitoring)
- [ ] open — AI risk prediction engine (the engine half of the claimed risk management; any scoring engine belongs here too)
- [ ] open — AI-powered data lake & ML platform (AI / ML model machinery generally; no model or inference is built anywhere in this group)
- [ ] open — Software factory & application hosting platform (app store, tenant hosting, CI / CD, Kubernetes across clouds; platform layer)
- [ ] open — Traceability, provenance & auditability platform
- [ ] open — Low- / no-code process configuration designer & movement / service tracking
- [ ] open — Grants lifecycle automation
- [ ] open — Supply-chain ecosystem engines
- [ ] open — Healthcare ecosystem platform
- [ ] open — Emergency-response coordination platform
- [ ] open — Blockchain / RPA machinery asserted across the suite

The Group 33 category union's extended families (automated evidence validation, monitoring feeds & scanner integrations, vulnerability scanning engine, automated KSI validation, posture / risk scoring engines, hosted enclave & PaaS operations, FedRAMP package generation) are already registered under Group 33 and are not re-registered here. Named absence (not a gap): policy management — zero claims at every GRC tier so far. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (the fork operates multi-tenant; single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: both tagged claims are engine claims — the Core implements the records substrate their outputs land in (monitoring results, finding records, counts-only posture); no scoring follows from the risk tag.

## Singleton 45 — Grant Management L2 (1 fork, new category)

Extended functions, specified in groups/grant-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Applicant portal web application (the responsive browser UI itself, incl. branding customization & rendering and device adaptation)
- [ ] open — Workflow execution engine (the registry holds definitions only)
- [ ] open — Form designer & form rendering engine (the registry holds definitions only)
- [ ] open — Document storage & content management engine (core holds metadata / checksums only)
- [ ] open — E-signature signing engine (ceremony & cryptographic binding; signature events are recorded)
- [ ] open — Payment / disbursement execution for awards (awards are records; no money moves)
- [ ] open — Reporting & analytics engines beyond registry summaries (dashboards, ad-hoc generation, exports)
- [ ] open — Notification & message delivery transport (email / SMS / push; records only)
- [ ] open — Applicant matching & opportunity recommendation
- [ ] open — Eligibility determination & merit-scoring engines (nothing is scored, by design)
- [ ] open — Closeout automation & financial reconciliation engines
- [ ] open — Identity provider / identity management service (the build ships RBAC hooks; IA-2 stays with the embedding organization)

Platform-layer: encryption at rest (deployment layer; TLS when configured); multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP. Spec notes: the category is new, so the taxonomy was defined from this fork's own description (17 families, 17 claims); the description contains no money vocabulary and no scoring vocabulary — money enters only as fields on records the claimed functions presuppose, under an explicit core-boundary decision, and no score field exists anywhere in the build.

## Singleton 46 — Health & Wellness L3-adjacent (1 fork)

The fork's clinical engines, specified in groups/health-wellness-l3/UNION-SPEC.md, not implemented (per the category privacy rule they may not be built on this substrate, and nothing in the build performs or claims any diagnostic function):
- [ ] open — EEG signal acquisition & real-time streaming pipeline
- [ ] open — EEG waveform review rendering (physician review surface)
- [ ] open — Continuous AI seizure monitoring & Seizure Burden quantification
- [ ] open — Seizure detection & alerting (suspected status epilepticus)
- [ ] open — Bedside diagnostic support

The Group 18 category union's extended families (clinical decision support, EMR / EHR integration, claims adjudication, device connectivity, AI / ML models, automation engines, survey depth, engagement channels, telehealth media, native apps, hosting platform) are already registered under Group 18 and are not re-registered here. Baseline gaps at High: MFA / authenticator management (IA-2(1)/(2), IA-5); FIPS-validated cryptography (SC-13); encryption at rest (SC-28); audit retention enforcement (AU-11); session lock / termination (AC-11/AC-12). Platform-layer: multi-tenancy (single-tenant reference deployment); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork (the category taxonomy was defined from glucose / CGM descriptions and contains no phrase that fires on an EEG platform's vocabulary; six broad first-pass hits were removed by the inherited tightened patterns). The build is not a medical device and claims no FDA status; the fork's clearance belongs to the fork's product.

## Singleton 47 — Law Enforcement L1 (1 fork)

The fork's own engines, named from its description's own verbs in groups/law-enforcement-l1/UNION-SPEC.md, not implemented (the carried substrate contains no surveillance function and, under the category privacy rule, can hold nothing about any person):
- [ ] open — License plate recognition engine & camera network (plate reads, vehicle matching)
- [ ] open — Audio recognition sensors & detection
- [ ] open — Video management & evidence-capture pipeline (the substrate captures nothing and stores no content)
- [ ] open — Camera / sensor hardware (the manufactured devices themselves)
- [ ] open — Public-safety collaboration & crime-analysis platform (the inter-agency layer beyond the devices)

The Group 34 category union's extended families (the legal corpora themselves, citation-validation engines, editorial enhancement systems, corpus search & relevance engines, AI / ML research assistance, document content storage / rendering / redaction) are already registered under Group 34 and are not re-registered here. Standing category exclusions (zero claims, not built): surveillance, facial recognition, predictive policing, real-time intelligence feeds — of these, only surveillance-class function is asserted by this fork's prose (as the engines above); the other three appear nowhere in its description and are not attributed to it. Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the fork is FedRAMP Low; at L1 the audit trace holds on the FedRAMP Low side only, and Group 34's SI-7 and AU-6 citations are deliberately not imported (not Low selections; checksums are an implementation property at this tier).

## Singleton 48 — Learning Management L2 (1 fork, new category)

Extended functions, specified in groups/learning-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Learning delivery engine (the LMS runtime itself)
- [ ] open — SCORM / AICC / cmi5 packaging & distribution runtime
- [ ] open — xAPI protocol runtime & LRS conformance (statement records are Core; the protocol engine is not)
- [ ] open — EHRI integration engine
- [ ] open — Learning analytics & outcomes engines
- [ ] open — Career mapping & recommendation engine
- [ ] open — Leadership succession planning suite
- [ ] open — Candidate review / talent acquisition system
- [ ] open — Employee survey engine
- [ ] open — Knowledge base / wiki platform (adjacent product)
- [ ] open — Web CMS platform (adjacent product)
- [ ] open — Content authoring tools & lesson-plan editor
- [ ] open — SF-182 form rendering / routing / signature workflow (authorization records are Core)
- [ ] open — Configurable report builder & dashboards
- [ ] open — Workflow execution engine (the registry holds definitions only)
- [ ] open — Notification automation & delivery transport
- [ ] open — Identity provider / MFA / SSO service

Platform-layer: multi-tenancy (claimed by the fork; single-tenant reference deployment); encryption at rest (deployment layer; TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the category is new and strictly separate from Education & Training; no assessment or credential family exists in its taxonomy, because the description's only "assessments" names succession-planning resources and "Certification" occurs only inside the SF-182 form's proper name (the only "scor" hits are inside "SCORM") — checked absences, itemized in the spec. LRS statement records carry an exact eight-key shape with result text verbatim and no score field anywhere.

## Singleton 50 — Mobile Device Management (MDM) L2 (1 fork, new category)

Extended functions, specified in groups/mobile-device-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Optimization engine (named from the product name only; no optimization claim exists in the description)
- [ ] open — Workflow execution / routing engine (the registry holds definitions only)
- [ ] open — Carrier & network integration engines (carrier order execution, bill feeds, data integration)
- [ ] open — Bill reconciliation engine beyond registry validation runs
- [ ] open — Budget projection / forecasting engine (projections are recorded verbatim, never computed)
- [ ] open — Analytics engine beyond registry summaries
- [ ] open — Report generation engine
- [ ] open — Alert delivery transport (alerts are records)
- [ ] open — Web portal / single-pane web application
- [ ] open — Managed Mobility services operations

Category named absences (not claimed by this fork; recorded so the category's expected device surface is accounted for, not silently missing):
- [ ] open — Mobile device enrollment & provisioning plane
- [ ] open — Remote wipe / lock / device command plane
- [ ] open — Device policy management & compliance enforcement
- [ ] open — Mobile application management
- [ ] open — Device location & tracking services

Platform-layer: encryption at rest (deployment layer); multi-tenancy (the fork asserts it of its hosting platform; the build is a single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: the fork is a Telecommunication Expense Management and Managed Mobility system filed under MDM; its description contains zero device-management vocabulary, the taxonomy reflects the TEM surface actually claimed, and the inventory record shape is pinned to ten keys so no field can hold a phone number, IMEI, serial, or any real device identifier.

## Singleton 49 — Legal & Policy L2 (1 fork, new category)

Extended functions, specified in groups/legal-policy-l2/UNION-SPEC.md, not implemented:
- [ ] open — AI agent runtime (LLM inference, agent orchestration, grounding / retrieval, model transport bridge)
- [ ] open — Legal corpus content (the statutes / regulations / guidance / datasets themselves, curation and update pipeline, licensing)
- [ ] open — Full-text & semantic search engines (indexing, vector / semantic ranking over the corpus; saved searches are digest records in Core)
- [ ] open — Sandbox runtime (the isolated single-use execution environment itself; executions are recorded, never performed)
- [ ] open — Code execution engine
- [ ] open — Document generation engine (drafting / generation from corpus and session context)
- [ ] open — Identity provider / federation service (the fork federates identity with enforced MFA; IA-2 stays with the embedding organization)
- [ ] open — Security monitoring & platform security services (deployment-platform layer)
- [ ] open — FIPS-validated cryptography (claimed by the fork's own platform; the standard library is not a validated module and none is claimed)

Platform-layer: encryption at rest (deployment layer); TLS only when configured; multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP. Spec notes: the category is new and strictly separate from Law Enforcement (legal research platforms); this fork is an AI agent workspace grounded in a curated legal library with an administration console, and every product function sits in its description's first sentence. Privacy discipline: documents are metadata + SHA-256 only with verify-by-content, and the store layer has no parameter that can accept query text — the service layer hashes queries before the store sees them.

## Singleton 52 — Operations Management L1 (1 fork)

The fork's own certified services, specified in groups/operations-management-l1/UNION-SPEC.md, not implemented (nothing in the build performs or claims judging or scoring):
- [ ] open — Submission management engine (custom submission forms / form builder, submission intake, reviewer assignment)
- [ ] open — Review & evaluation engine (reviewer / judge scoring and feedback; substrate inspection records hold verbatim outcomes only)

Product capabilities named in the listing but explicitly outside its FedRAMP Minimum Assessment Scope, per the listing's own scope sentence:
- [ ] open — Automated communications
- [ ] open — Reporting (the product's reporting capability, beyond registry summaries)
- [ ] open — Program website builder
- [ ] open — Galleries
- [ ] open — Conference session scheduling
- [ ] open — Payments
- [ ] open — Third-party integrations

The Group 36 category union's extended families (workflow execution, real-time intelligence & analytics, AI models, low-code builder, integration connectors, mobile apps, network connectivity & cloud operations, identity provider, security enforcement plane, policy enforcement plane, governance console) are already registered under Group 36 and are not re-registered here. Named absences from the category record: scheduling / rostering (zero claims at L2; this fork names conference session scheduling only as an out-of-scope capability) and IoT / telematics (zero claims everywhere). Platform-layer: multi-tenancy (asserted by the fork of its own platform; single-tenant reference deployment); encryption at rest (deployment layer); TLS only when configured; demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec note: zero claims tag for this fork; the one raw hit (integrations) fired only inside the listing's scope-exclusion sentence and was removed under the boundary-disclaimer and excluded-catalogue precedents. At L1 the audit trace holds on the FedRAMP Low side only, and Group 36's AU-6 citation is deliberately not imported.

## Singleton 51 — Network Management L2 (1 fork, new category)

Extended functions, specified in groups/network-management-l2/UNION-SPEC.md, not implemented (the build manages no live network, pushes no configuration, and collects no telemetry):
- [ ] open — Network optimization engine ("optimize" is a real verb in this fork's description, unlike the name-only case at Singleton 50; claimed, engine Extended)
- [ ] open — Network intelligence / AI engine
- [ ] open — Device provisioning & deployment engine
- [ ] open — Network configuration push / control plane (configuration changes are records; closing one alters no device or network record)
- [ ] open — Firmware management engine
- [ ] open — Traffic control & SD-WAN policy engine (named from the device gloss, not a claim)
- [ ] open — Telemetry collection & polling engine (telemetry in Core is caller-supplied records only)
- [ ] open — Alert evaluation & delivery transport (alerts are records)
- [ ] open — Integration connectors
- [ ] open — Automation execution engine (the registry holds definitions only)
- [ ] open — Cloud management web application
- [ ] open — FIPS-validated cryptography (SC-13; the fork's platform property — the build claims no validated cryptography)

Platform-layer: U.S. data residency (deployment property); platform scalability / multi-region operation; encryption at rest (deployment layer; TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the category is new; the description is platform prose (three of nine sentences tag nothing), and no reporting family exists in its taxonomy because the description carries no report or dashboard vocabulary — registry summaries are substrate, not a reporting claim. Device records carry a nine-key pinned shape with classes from the description's generic glosses; vendor model designations appear only inside stored evidence.

## Singleton 54 — System Administration L2 (1 fork, new category)

The fork's operations, performed by people and platforms and named from its own verbs in groups/system-administration-l2/UNION-SPEC.md, not implemented (Core holds their records — service requests, changes, control inheritance — and the substrate performs none of the management work):
- [ ] open — Managed OS & services administration operations (the full management itself)
- [ ] open — System provisioning & deployment operations
- [ ] open — Application delivery & hosting runtime
- [ ] open — Virtualization engine (the underlying cloud provider's)
- [ ] open — High-availability network operation
- [ ] open — Third-party CSP hosting platforms (outside the fork's own boundary)

Platform-layer: part of the fork's baseline is satisfied by the underlying CSP (control inheritance, recorded in Core as dispositions verbatim); encryption at rest (deployment layer; TLS when configured); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the fork is a General Support System whose operator maintains full management of the OS and services; its prose says controls are maintained "at the High baseline level," but the offering's own impact level is Moderate — recorded as a wording artifact, not read as re-tiering, and the build builds to Moderate / L2. Named absences: the description carries zero monitoring, incident-response, ticketing, SLA, backup / DR, or reporting vocabulary, recorded as absences rather than attributed. System and application record shapes have no field that can hold a hostname, IP address, or credential.

## Singleton 53 — Research L2 (1 fork, new category)

Extended functions, specified in groups/research-l2/UNION-SPEC.md, not implemented:
- [ ] open — Data commons runtime engine
- [ ] open — Data ingestion / ETL engine
- [ ] open — Data harmonization engine
- [ ] open — Indexing & metadata catalog engines beyond the registry
- [ ] open — Query & analysis workspace engines
- [ ] open — Cohort builder / cohort discovery engine
- [ ] open — Cross-commons federation / data mesh networking
- [ ] open — Data delivery / transfer engine for sharing
- [ ] open — Access enforcement on data delivery (grants are records that confer nothing; no data moves in this build)
- [ ] open — Identity provider / identity management service

Platform-layer: encryption at rest (deployment layer; TLS when configured); multi-tenancy (the fork claims it of its own platform; single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the category is new; the description is two sentences, the first a baseline determination that tags nothing, so all nine claims come from the single platform sentence. Privacy discipline: the dataset record shape is pinned to exactly nine keys (metadata, checksum, access tier) so no field can hold research subject data, genomic or clinical payloads, or dataset contents; verify-by-content hashes caller bytes transiently and discards them; access requests are rejected for open datasets rather than gated falsely.

## Singleton 55 — Travel Management L2 (1 fork, new category)

Extended functions, specified in groups/travel-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Travel booking & reservation engine
- [ ] open — Carrier, hotel & GDS reservation integrations
- [ ] open — Payment & disbursement execution (vouchers are records; no money moves)
- [ ] open — Receipt capture & imaging / OCR
- [ ] open — Integration connector engines (the registry holds definitions only)
- [ ] open — Notification delivery transport (notifications are records)
- [ ] open — Report generation engine & dashboards (beyond registry summaries)
- [ ] open — Identity provider / identity management service

Platform-layer: the commercial SaaS / PaaS offerings the fork integrates are its own components, outside this build; hosting regions are a deployment property; encryption at rest (deployment layer; TLS when configured); multi-tenancy (single-tenant reference deployment); demo identities are hooks, not an IdP (IA-2 stays with the embedding organization). Spec notes: the category is new and this singleton completes the singleton phase. The description (three sentences) contains no booking / reservation, per-diem, reimbursement, approval, or receipt vocabulary — checked absences, itemized in the spec; authorization, decision, and voucher records enter Core only as the records forms the claimed travel and expense services presuppose, under explicit core-boundary decisions. Traveler records carry opaque references in a shape pinned to exactly six keys.

## Remainder Addition — Operations Management L2 (+20 forks)

New extended functions from the addition forks, specified in groups/operations-management-l2/ADDENDUM.md, not implemented:
- [ ] open — Managed print services engine (Canon, Xerox)
- [ ] open — Supply chain & logistics execution suite (Manhattan)
- [ ] open — Product lifecycle management (PLM) platform (PTC)
- [ ] open — IT service management (ITSM) suite (Ivanti)
- [ ] open — Infrastructure maintenance management system (InfraLink)
- [ ] open — Facilities & real property management suite / IWMS (FM:Systems, GoRPM, IBM TRIRIGA overlap)
- [ ] open — Case management platforms incl. EEO + FOIA (Tyler Federal, AINS eCase)
- [ ] open — Business process modeling, process mining & enterprise architecture platform (Software AG ARIS / ALFABET)
- [ ] open — Mail & package operations (Pitney Bowes)
- [ ] open — Strategic portfolio & agile planning platforms (Clarity, Rally)
- [ ] open — Back-office ERP suite (Accenture)
- [ ] open — Contract progress management application (iSite)
- [ ] open — Enterprise asset management depth: predictive maintenance / asset health / IoT telemetry analytics (IBM Maximo)

Enlargements of families already registered under Group 36: the workflow automation execution engine is now asserted by 7 of 22 forks (adds the RPA / process-automation platforms UiPath and Bizagi); integration connector engines & catalog now 2 of 22 (adds IBM webMethods). Absence update: scheduling & rostering and IoT / telematics remain at zero taxonomy claims and unbuilt, but are no longer universal absences in this category (InfraLink asserts scheduling substance; IBM asserts IoT integration substance).

## Remainder Addition — Cybersecurity L2 (+18 forks)

No new extended functions; the addition enlarges families already registered under Group 4 (claimant counts in groups/cybersecurity-l2/ADDENDUM.md): identity, authentication & privileged-access products (+7 forks, now the union's largest Extended family at 15 of 72); AI / ML-powered analytics & anomaly detection (+5); network security enforcement (+4); insider-risk, DLP & data-security monitoring engines (+4); automation & orchestration engines / SOAR (+4); cloud & SaaS posture engines (+3); application-security testing engines (+3); threat-intelligence feeds (+2); identity proofing & fraud prevention (+2); endpoint management & patching agents (+2); endpoint security agents / EDR & XDR (+1); phishing simulation & security-awareness training (+1); log & telemetry pipelines (+1). Platform note: encryption & key management gains 3 claimants (no key-management service added; the substrate's hooks-not-IdP decision is reaffirmed). Three addition forks claim zero families under the taxonomy applied verbatim (Login.gov, Proofpoint TAP, Qualys) — their near-misses are itemized in the addendum rather than tuned for.

## Remainder Addition — System Administration L2 (+8 forks)

New extended functions from the addition forks, specified in groups/system-administration-l2/ADDENDUM.md, not implemented:
- [ ] open — Virtual workspace & desktop delivery platform (Citrix DaaS)
- [ ] open — Observability & AIOps platform (Dynatrace)
- [ ] open — IT service & asset management suite, ITSM / ITAM (OpenText; Oracle service desk rides it)
- [ ] open — Universal discovery & CMDB engine (OpenText)
- [ ] open — Project & portfolio management platform (OpenText)
- [ ] open — DEX analytics & endpoint automation platform (TeamViewer)
- [ ] open — Geospatial (GIS) application platform (Esri's ArcGIS payload)
- [ ] open — Managed backup & disaster-recovery services (Contegix, DLH, Oracle, Esri)
- [ ] open — Security operations services: SOC / SIEM / vulnerability scanning (Esri, Contegix, DLH)

Enlargements of families already registered under Singleton 54: managed OS & services administration operations (now the substance of 5 of 9 forks); virtualization engine (2 of 9; Citrix's headline function); application delivery & hosting runtime; high-availability network operation (substance only). Named-absence update: monitoring, incident response, ticketing, and backup / DR are no longer universal absences of the enlarged group (asserted as engines by addition forks; still zero claims, unbuilt, gap-named above); SLA vocabulary remains universally absent.

## Remainder Addition — Legal & Policy L2 (+6 forks)

New extended functions from the addition forks, specified in groups/legal-policy-l2/ADDENDUM.md, not implemented (the group's original nine Extended gaps gain no claimants; the newcomers claim zero families under the taxonomy, which is the original fork's literal phrases):
- [ ] open — eDiscovery processing & collection engine (CDS, Deloitte EMS, IDGC)
- [ ] open — eDiscovery document review platform, incl. hosted review ecosystems (CDS, Deloitte EMS, IDGC, RelativityOne)
- [ ] open — eDiscovery production, disposition & archiving engine (Deloitte EMS, IDGC)
- [ ] open — Legal hold & preservation management (Deloitte EMS, IDGC)
- [ ] open — AI document analysis for discovery: summarization / classification / redaction, assisted review, analytics & visualizations (Deloitte EMS, IDGC, RelativityOne, CDS)
- [ ] open — OCR & document extraction engine (Deloitte EMS)
- [ ] open — FOIA & disclosure release engine (Deloitte EMS)
- [ ] open — Electronic signature engine: ceremony, binding / validity, envelope & transaction workflow (DocuSign)
- [ ] open — Contract lifecycle management engine (DocuSign CLM)
- [ ] open — Agreement workflow automation engine (DocuSign)

## Remainder Addition — Data Management L2 (+5 forks)

No new extended functions; the addition enlarges families already registered under Group 12 (claimant counts in groups/data-management-l2/ADDENDUM.md): integration runtime & connector engine (+2: DNAnexus, Informatica IICS); workflow / BPM execution engine (+1: Collibra); search indexing engine (+1: OpenFLIS); query & visualization engines (+1: IICS). The file-transfer transport gap gains Vaultara Flare as a described-function member with zero taxonomy claims (its "electronic transfer / digital delivery" phrasing matches neither "managed file transfer" nor "MFT") — recorded with exactly that caveat. Unclaimed domain engines in the newcomers' prose (DNAnexus's molecular analysis, Collibra's intelligence platform) are recorded as near-miss substance in the addendum, not as gaps.

## Remainder Addition — GRC L2 (+5 forks)

New extended functions from the addition forks, specified in groups/grc-l2/ADDENDUM.md, not implemented:
- [ ] open — Policy lifecycle management engine: authoring / approval / enforcement (policy records are Core; the lifecycle is an engine) (Anecdotes, MediaLab)
- [ ] open — Agentic workflow execution engine (Anecdotes)
- [ ] open — AI control-narrative & assessment-response generation / secure AI enclave (Kovr)
- [ ] open — Data-integration connector engine (Workiva)
- [ ] open — IT service management suite ITSM / ESM incl. CMDB / SLA (Halo fork excess)
- [ ] open — Healthcare quality management suite (MediaLab fork excess)
- [ ] open — Connected financial & regulatory reporting / publishing platform (Workiva fork excess)

Enlargements of families already registered under Group 33: automated evidence-validation engine incl. collection (+Kovr, Anecdotes by substance); continuous-monitoring feeds (+3 claimants); automated KSI validation (+Halo by substance); FedRAMP package generation (+Kovr). Posture / risk scoring engines gain no claimants, and no score is computed anywhere in the enlarged build. Absence retirement: the group's two standing named absences, risk_management and policy_management, are retired by this addition — newcomers claim both, and each claim buys its records form under the standard treatment (assessments and findings as records; policy documents as evidence records), with the policy lifecycle registered above as the genuinely new engine gap.

## Remainder Addition — Development Tools L2 (+4 forks)

New extended functions from the addition forks, specified in groups/development-tools-l2/ADDENDUM.md, not implemented:
- [ ] open — No-code / low-code application development platform: visual application builder & runtime (Unqork)
- [ ] open — Compliance documentation & SSP generation tooling (Cloud.gov; distinct from assessment automation: this is documentation generation)

Enlargements of families already registered under Group 29: CI / CD execution engines (+Copado, +FGC); business modeling & automation engines (+Copado, first claimant at this tier); landing-zone provisioning & hosted platform operations (+FGC, +Cloud.gov); static code analysis engine (+Copado by substance: "code scanning" / "quality gates" — the family claim did not fire); release automation & data migration engine (+Copado by substance: Salesforce metadata deployment — the family's phrasing did not fire on the reversed wording); external-system integration engines (+Copado). One addition fork claims zero families (Unqork; its lone verb "build" is not a CI claim and its visual builder is never called "visual"), pinned in tests.

## Remainder Addition — Research L2 (+5 forks)

New extended functions from the addition forks, specified in groups/research-l2/ADDENDUM.md, not implemented:
- [ ] open — Interactive analysis environment & workflow execution engine (Terra)
- [ ] open — Bioinformatics analysis pipeline engines (ROSALIND, Seven Bridges)
- [ ] open — Diagnostic monitoring & variant surveillance platform incl. BioBank sample tracking (ROSALIND)
- [ ] open — Knowledge-graph storage & searchable library engine (ROSALIND)
- [ ] open — Elastic storage & compute allocation engine (Seven Bridges)
- [ ] open — Multi-modal survey research platform (Ipsos)
- [ ] open — AI analytics engine over LLMs (Ipsos)
- [ ] open — Technology transfer & IP management suite (Wellspring)
- [ ] open — Document generation & e-signature workflow engines + external integration components (Wellspring fork excess)

Enlargements of families already registered under Singleton 53: data delivery / transfer engine for sharing (+2 claimants: Terra, ROSALIND); query & analysis workspace engines (+3 by substance: Terra, ROSALIND, Seven Bridges — analysis is their headline activity but the data_analysis claim itself did not fire on their wording, recorded as such). Platform notes: multi-tenancy asserted by ROSALIND and Wellspring of their own platforms; Wellspring's product runs inside a third-party government cloud (the fork's dependency, outside this build). Three addition forks claim zero families (Ipsos, Seven Bridges, Wellspring) under the taxonomy, whose patterns are the original fork's literal phrases.

## Remainder Addition — Finance L2 (+4 forks)

New extended functions from the addition forks, specified in groups/finance-l2/ADDENDUM.md, not implemented:
- [ ] open — Federal financial management system of record (Momentum)
- [ ] open — Procurement lifecycle engine: supplier identification, sourcing, contracting, invoicing, supplier payment execution (Coupa; its payments recorded here, deliberately NOT enlarging the earned-wage payment-rails gap)
- [ ] open — Spend analytics engine (Coupa)
- [ ] open — Technology business management & cloud cost allocation / optimization (FinOps) engine (Apptio)
- [ ] open — Trust accounting & wealth management platform, multi-currency (Innovest; the union's "trading & investment execution" named absence still stands: Innovest asserts wealth management, not trading)
- [ ] open — AI / ML document processing & image recognition (Coupa)

No existing Extended gap gains a claimant in this addition. Three addition forks claim zero families (Apptio, Momentum, Innovest) under the taxonomy, pinned in tests with near-misses itemized ("multi-currency" is not "multi-tenant"; "SaaS provider" is not "SaaS offering"). Coupa's one claim was re-anchored from its product-name sentence to its functional sentence under the name-only precedent.

## Remainder Addition — Collaboration L2 (+3 forks)

New extended functions from the addition forks, specified in groups/collaboration-l2/ADDENDUM.md, not implemented:
- [ ] open — Innovation management & crowdsourcing platform (IdeaScale)
- [ ] open — Centralized administration console for collaboration services (Webex)
- [ ] open — Virtual visitation scheduling portal: business-rules / workflow configuration, zero-touch device connectivity (Webex)
- [ ] open — Collaboration hardware endpoints & purpose-built devices (Webex, platform layer)
- [ ] open — Product-specific connector engines (Huddle, office-suite integrations)

Enlargements of families already registered under Group 2: meetings / video media transport +1 (Webex); voice / telephony / contact center +1 (Webex); workflow / process-automation engines +1 (Webex, at wording-artifact weight); AI assistance / speech / analytics +1 (Webex, at wording-artifact weight); records & governance beyond the seed +1 (Huddle); task & project management beyond board cards +1 by substance (Huddle, claim did not fire). The encryption platform note gains no claimant. One addition fork claims zero families (IdeaScale: "collaboratively transform" is not a workspaces phrase; "project plans" is not project management), pinned in tests.

## Remainder Addition — Health & Wellness L2 (+3 forks)

New extended functions from the addition forks, specified in groups/health-wellness-l2/ADDENDUM.md, not implemented:
- [ ] open — Telehealth media engine (GTS; this retires the group's standing telehealth named absence: GTS claims telehealth visits in its own words; the visit is a Core activity record, the media channel is the gap)
- [ ] open — Store-and-forward clinical data service: labs / images / clinical data (GTS)
- [ ] open — Medical coding engine / computer-assisted coding (Solventum; named separately from the coding step inside the adjudication gap, reasoning in the addendum)
- [ ] open — Grouper / classification & reimbursement content services (Solventum)
- [ ] open — Clinical documentation integrity tooling (Solventum)
- [ ] open — Diagnostic report generation engine (Somnoware)
- [ ] open — Therapy progress & risk-profile console (Somnoware; values are Core records; no risk profile is computed in this build)

Enlargements by substance, no family claim fired, recorded as such: device connectivity / sync pipelines +GTS (RPM device integration); EMR / EHR integration engines +Somnoware; AI / ML models +Solventum and +Somnoware. Claims adjudication gains no claimant (Solventum's "reimbursement content" is a content service, gapped separately above). All three addition forks claim zero families under the taxonomy (built from the original five's glucose / CGM vocabulary), pinned in tests with near-misses itemized; the clinical-decision-support absence stands.

## Remainder Addition — Human Resources L2 (+3 forks)

New extended functions from the addition forks, specified in groups/human-resources-l2/ADDENDUM.md, not implemented:
- [ ] open — Time, attendance & leave tracking engine (GDC; retires the group's two standing absences, leave & time-off and time & attendance, asserted in substance in its own prose; the tracking surface is an engine, not a records form)
- [ ] open — Organizational chart generation & maintenance automation (GDC)
- [ ] open — Employee engagement survey & listening platform (Perceptyx; its whole function, which has no taxonomy family)
- [ ] open — Federal retirement & benefits administration platform depth (GRB fork excess, distinct from the existing calculator gap)
- [ ] open — Employee self-service portal & HR dashboard (GDC)
- [ ] open — Uniform allowance request processing (GDC)

Enlargements of families already registered under Group 21: workforce planning & resource-management analytics / models (+GDC); integration connector engines (+GRB by substance); document & template assembly engines (+GDC by substance). AI talent intelligence & matching engines explicitly gain no claimant (one addition's automation claim carries zero AI wording anywhere, recorded as a wording artifact).

## Remainder Addition — Operations Management L1 (+3 forks)

New extended functions from the addition forks, specified in groups/operations-management-l1/ADDENDUM.md, not implemented:
- [ ] open — Workspace scheduling & reservation engine (FM:Systems, Tango; the headline function of both workplace forks; the verbatim taxonomy has no scheduling family, so this stands at zero claims while asserted in substance by 2 of 4 forks at this tier)
- [ ] open — Visitor & event management (FM:Systems)
- [ ] open — Interactive floor plans, wayfinding & digital signage (FM:Systems, Tango)
- [ ] open — IoT sensor integration & workspace-utilization sensing (FM:Systems, Tango by catalogue substance; likewise no taxonomy family)
- [ ] open — Workplace analytics & optimization engine (FM:Systems, Tango, by substance)
- [ ] open — Procurement marketplace & requisitioning engine (SCMC)
- [ ] open — Real-estate portfolio suite: space planning, lease administration / accounting, transaction & predictive analytics (Tango catalogue excess)

Enlargements: integration connector engines & catalog +1 claimant at this tier (Tango; the original fork's separate out-of-scope integrations gap gains nothing); mobile applications & offline sync +1 by substance (FM:Systems). The addition gives the group its first taxonomy claim (group total 0 to 1).

## Remainder Addition — Cybersecurity L3-adjacent (+2 forks)

New extended functions from the addition forks, specified in groups/cybersecurity-l3/ADDENDUM.md, not implemented:
- [ ] open — Firewall management & orchestration plane: NGFW policy / device management, zero-touch provisioning, AIOps policy analysis (Cisco)
- [ ] open — HSM as a Service: cloud HSM & key-management service (AuthentX; distinct from the SC-13 platform gap; the fork's own FIPS 140-2 Level 3 HSM certification is its platform property and does not transfer to this build)
- [ ] open — Inline email security platform (Cisco; named separately from the phishing family's simulation / training content)

Enlargements of families already registered under Group 8: network enforcement planes +1 (Cisco, the group's largest network surface); identity products +2; DLP engines +1; AI / ML detection models +1; threat-intel feeds +1; SOAR / workflow automation +1; cloud / SaaS posture engines +1 by substance (CASB named twice, no posture phrasing). Posture / risk scoring engines explicitly gain no claimants, and neither addition fork claims risk scoring, so no computed score enters the enlarged build. One correction applied in the addition spec: a raw endpoint-management match was dropped because the sentence manages firewall appliances, a network function, not endpoints.

## Remainder Group 1 — Contract Management L2 (2 forks, new category)

Extended functions from the group's forks, specified in groups/contract-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Regulatory content & interpretation: FAR / DFARS corpus, agency supplements, updates
- [ ] open — Workflow execution engine
- [ ] open — Analytics engine: PALT measurement, bottleneck / spend analysis beyond registry counts and sums
- [ ] open — Opportunity portal front-end (the public / directed web portal itself)
- [ ] open — Reverse auction engine: live bidding, price discovery
- [ ] open — Submission intake transport (electronic bid / proposal receipt channel)
- [ ] open — Payment processing rails: fee collection / settlement (the core records payments, moves no money)
- [ ] open — Integration transport (the system-to-system interfaces themselves)
- [ ] open — Communication transport (the secure messaging channel itself)
- [ ] open — Identity provider / registration verification service (registration records are not identity proofing; IA-2 stays with the embedding organization)

Boundary, stated in the spec: procurement operations tooling lives in Operations Management; post-award grants administration lives in Grant Management; this group's financial-assistance claims reach only as far as opportunities. Checked absences in both descriptions: no contract authoring / clause library, no e-signature, no source selection / evaluation / scoring, no invoicing or government disbursement.

## Remainder Group 2 — Learning Management L1 (2 forks, new tier group)

New extended functions at this tier, specified in groups/learning-management-l1/UNION-SPEC.md, not implemented (the carried Extended set from the L2 sibling build — delivery engine, packaging runtimes, xAPI runtime, analytics, succession, survey, form workflows, report builder, notification transport, IdP — is already registered under Singleton 48 and is not re-registered here):
- [ ] open — Learning content authoring environment: rapid / collaborative authoring, themes & menus, plugins, 508-conformant output (CloudLCMS)
- [ ] open — Course posting & publication workflow (TRAIN)
- [ ] open — Branded portal rendering & presentation engine (TRAIN)
- [ ] open — Continuing education management engine (TRAIN)
- [ ] open — Certificate issuance & verification service (TRAIN)
- [ ] open — System integration engines (TRAIN)

The L2 sibling's 26-family taxonomy was applied verbatim at this tier: one claim in two forks (SCORM 1.2 content standards distribution), and TRAIN is a zero-claim fork whose own verbs (multi-tenancy, branded portals, tracking, continuing education, certificates) match none of the L2 fork's literal phrases; its asserted functions are the new gaps above, itemized in the spec rather than claimed.

## Remainder Group 3 — Talent Management L2 (2 forks, new category)

Extended functions from the group's forks, specified in groups/talent-management-l2/UNION-SPEC.md, not implemented:
- [ ] open — Video interview platform
- [ ] open — Assessment delivery & scoring engines
- [ ] open — Predictive I-O models & AI
- [ ] open — Virtual event platform
- [ ] open — Pipeline automation engine
- [ ] open — Analytics & visualization engines (incl. ROI determination)
- [ ] open — Talent development programs
- [ ] open — Identity provider / candidate identity verification (IA-2 stays with the embedding organization)

Boundary, stated in the spec: this group is the candidate-facing pre-hire acquisition surface; Human Resources L2 remains the personnel system of record, and no HR forks were imported. Deliberate absences: no communications surface and no integration registry, because neither description claims them; no score field exists anywhere in the build.

## Remainder Addition — Analytics L1 (+1 fork)

New extended functions from the addition fork, specified in groups/analytics-l1/ADDENDUM.md, not implemented:
- [ ] open — Collaboration & unified-communications telemetry engine: multi-vendor UC telemetry collection, experience visibility / insights (the fork's whole product; named separately from the generic alerts gap, which covers engines over data already in the platform)
- [ ] open — End-user experience & productivity analytics engine (by substance; no family claims it, no score defined or computed)

Enlargements of families already registered under Group 7: alerts / monitoring engines +1 claimant (substantive); proprietary-source connectors +1 by substance; real-time / streaming analytics +1 by substance. Two of the fork's three claims are wording artifacts, recorded at artifact weight and not counted as enlargements: sharing & collaboration fired on the product name, and data transformation fired on "workplace transformation" (organizational change, its evidence sentence containing no data wording at all), both pinned by test.

## Remainder Addition — AI L2 (+1 fork)

New extended functions from the addition fork, specified in groups/ai-l2/ADDENDUM.md, not implemented:
- [ ] open — Infrastructure Digital Twin & infrastructure performance management engine
- [ ] open — Service transition management: migration planning / tracking incl. IPv6, with automated configuration management & capacity planning
- [ ] open — EIS service management suite: SLA / service-level monitoring, CLIN & invoice management with reconciliation & dispute support, service inventory lifecycle, provider credit recovery (fork excess)

Enlargements: agentic & automated workflow engines +1 claimant (now 5 of 12 in the group); learned AI / ML inference +1 by substance, explicitly not a claimant (the fork's semantic intelligence and public-comment analysis are recorded so the final batch sizes the inference gap honestly). Document processing & generation explicitly gains no claimant. The fork claims no learned inference under the taxonomy despite its AI branding ("AI-enabled" is not "ai-powered"; "intelligent agents" is not "ai agents"), pinned in tests; its audit claim rests on the single word "auditability", a wording artifact with a recorded precedent in the group.

## Remainder Addition — Analytics L2 (+1 fork)

New extended functions from the addition fork, specified in groups/analytics-l2/ADDENDUM.md, not implemented (all fork excess from its own service catalogue):
- [ ] open — Automated back-office service tools (HR, finance & property management)
- [ ] open — Digital signature engine
- [ ] open — E-workflow tooling (explicitly distinguished from the group's Extended scheduling & workflow automation family)
- [ ] open — Mobile client capabilities

No existing gap gains a counted claimant: the fork's collaboration claim fired inside its own service catalogue and is recorded at catalogue weight (the catalogue lists the fork's own offered services, so the third-party-catalogue exclusion does not apply, but the artifact-weight precedent does); its visualization claim is Core (dashboard composition), not a gap.

## Remainder Addition — Collaboration L3-adjacent (+1 fork)

New extended function from the addition fork, specified in groups/collaboration-l3/ADDENDUM.md, not implemented:
- [ ] open — Collaborative continuous monitoring service (the fork's closing sentence names an agency-vendor continuous-monitoring arrangement with no family in this taxonomy)

No existing gap gains a claimant: the fork's single claim (messaging) is a Core function, and all Extended families and the High baseline gaps stand at their original counts. Platform note, not a gap: the fork's inherited-services dependency on its underlying government cloud is its platform posture, recorded in the addendum. Registry honesty: the source publishes no service model for this fork, so none was invented from the product's reputation; the spec records the empty list as published.

## Remainder Addition — Communication L2 (+1 fork)

New extended function from the addition fork, specified in groups/communication-l2/ADDENDUM.md, not implemented:
- [ ] open — Marketing automation & citizen-engagement campaign engine: audience targeting / segmentation and automated campaign execution (registered from the fork's described function; its headline "marketing automation platform" phrasing fires no taxonomy family)

No existing gap gains a claimant: secure transmission explicitly gains none (adjective prose without the family's operative phrasing). Both census citations for this fork verify as verbatim text and neither tags a family; the fork's single claim rests on a third sentence the census did not cite — verification is not a claim, in both directions.

## Later groups

Each group appends its section here when it ships.
