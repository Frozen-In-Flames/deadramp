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

## Later groups

Each group appends its section here when it ships.
