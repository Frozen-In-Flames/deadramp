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

## Later groups

Each group appends its section here when it ships.
