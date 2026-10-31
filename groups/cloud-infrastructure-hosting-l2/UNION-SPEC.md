# Cloud Infrastructure & Hosting L2 — Union Spec

Remainder Group 4 of DeadRamp Phase 2: the founding build of a
**new category**. The remainder census left 23 forks unclassified;
the no-signal live-doc research pass (`remainder/nosignal_report.json`,
`remainder/NOSIGNAL.md`) resolved 13 of them into a category no
shipped group covers — vendors whose public function is the cloud
platform itself: hosting environments, tenancies, and the platform
services around them. This group founds the category at the
Moderate tier with the six Moderate forks. (The six High forks, the
one untiered fork, and the sibling resolutions into other
categories are separate build units.)

The category boundary, as the census recorded it and this build
keeps it: prose emphasizing administration services *performed* on
a platform resolves to System Administration; pure platform and
hosting prose resolves here. No System Administration family,
pattern, or core function was imported.

## Evidence method

Two evidence streams, kept separate by rule and pinned by test:

- **Classification** comes from the vendors' own live public
  pages: each sheet carries `classification_evidence` and
  `classification_source_url` copied from
  `remainder/nosignal_report.json`, which is what places the fork
  in this category at all. For all six forks the classification
  sentence does **not** occur in the cached marketplace
  description.
- **Claims** come only from the fork's cached marketplace
  description (`remainder/uncovered.json`'s `description`, verified
  byte-equal to the cache's `service_desc`), under the taxonomy
  below. A function is claimed only where matching text actually
  occurs in the description; the first matching unit is stored as
  the claim's evidence. The classification sentence is never claim
  evidence (pinned by test).

Further discipline, as everywhere in this repo: `certified_services`
is never matched (it is empty for all six records — asserted at
extraction); scope-exclusion and disclaimer prose earns nothing
(the SAP descriptions open with the FedRAMP disclaimer boilerplate,
which fires no family); marketing and outcome prose gets no tags.
Counts are a floor.

**Hosted-application catalogue exclusion (SAP NS2 forks).** Both
SAP descriptions enumerate the business applications hosted *on*
the environment (S/4HANA, SuccessFactors, BTP, HANA Cloud,
Analytics Cloud, IBP, Fieldglass, and the SuccessFactors
"Includes:" continuation). Those applications' functions — ERP,
payroll, human capital, supply chain — belong to other categories,
so catalogue units are excluded before matching; the environment
paragraphs and the suite-intro sentences, which state the hosting
function itself, stay matchable. Checked result: each catalogue
contains exactly one would-be hit (the S/4HANA unit's "managed
cloud service" → `hosting_platform`), and in both forks the
family's first-match evidence is an environment sentence that
precedes the catalogue, so the exclusion changed no final claim
table. It stands as method and is pinned by test (no SAP claim
evidence starts with a catalogue lead-in; "payroll" and "human
capital" occur in both SAP descriptions and in no claim).

## Members (6 forks, all FedRAMP Moderate / CMMC L2, all FedRAMP Certified)

| Fork | Vendor / Product | Model | Deployment | Classification source |
|---|---|---|---|---|
| FR2004446306 | Elastic / Elastic Cloud | SaaS | Government Community Cloud | elastic.co |
| F1208031461 | IBM / IBM Platform Services for Government | SaaS, PaaS | Public Cloud | ibm.com |
| F1510137547 | Rackspace Government Solutions / Rackspace Government Cloud | PaaS | Government Community Cloud | rackspace.com |
| F1602257856 | SAP National Security Services Inc. (SAP NS2) / DoD Cloud Intelligent Enterprise – DD-CIE | SaaS | Government Community Cloud | sapns2.com |
| FR1719841002 | SAP NS2 / SAP NS2 Cloud Intelligent Enterprise | PaaS, SaaS | Government Community Cloud | sapns2.com |
| AGENCYWC2 | United States Department of the Treasury / Treasury Cloud Moderate | PaaS, SaaS | Government Community Cloud | home.treasury.gov |

Claims by fork: Treasury Cloud Moderate 12, Rackspace Government
Cloud 9, Elastic Cloud 5, IBM Platform Services 5, SAP NS2 CIE 2,
SAP NS2 DD-CIE 1. **Total 34 claims across 17 families. Zero-claim
forks: none.**

Recorded caveats at their exact weight: DD-CIE's classification
evidence names SAP IBP as the hosted example — the sheet stands for
the DD-CIE environment, and the claim table rests on the
environment's own sentences, not on IBP. CIE's evidence names the
Government Cloud portfolio. For Treasury Cloud Moderate, no agency
page states a distinct "Moderate" variant — neither confirmed nor
refuted; the tier comes from the marketplace record itself. Both
SAP descriptions assert IL4/IL5 (DD-CIE) and a DISA Provisional
Authorization at IL2 dated 17 March 2026 (CIE) in prose while their
marketplace records say Moderate; the tier comes from the record,
and the IL prose moves nothing. DD-CIE's vendor name on the
evidence page is styled "SAP NS2" while the marketplace record
names the legal entity — the same vendor, recorded as filed.

## Taxonomy (17 families, derived fresh for this category)

Derivation sources: (a) the six cached descriptions and (b) the six
classification sentences — the forks' own words in both cases.
Where a classification sentence names a function the cached
description also names in substance, the family stands on the
description's phrases (claims still fire only on the description).
Per-family sources are noted in the table.

| # | Family | Claims | Derivation (the forks' own words) | Disposition |
|---|---|---|---|---|
| 1 | `hosting_platform` — hosting / managed cloud platform | 5 | "hosts and manages" + "default encryption at rest" stack prose (Elastic); "fully-managed cloud solution" (Rackspace); "hosts the following suite" / "has the following suite" + "secure cloud environment" (SAP ×2); "multi-tenant IaaS/PaaS hosting environment" (Treasury) | **Core** (functions 2, 3, 5) |
| 2 | `infrastructure_providers` — underlying cloud infrastructure & providers | 3 | "multiple public cloud providers, including Amazon Web Services (AWS)" (Elastic); "wraps VMware and AWS" (Rackspace); "The IaaS/PaaS provider used for this solution is Amazon Web Services (AWS) US East/West" + "native cloud services" (Treasury) | **Core** (function 4) |
| 3 | `monitoring_observability` — monitoring & observability | 3 | "observability" in the service list + Instana "monitor their entire stack" (IBM); "continuous monitoring" (Rackspace); "Monitoring of network ingress and egress traffic" + "log ingestion and monitoring" (Treasury) | **Core** (function 7) |
| 4 | `identity_access` — identity, access & directory services | 3 | "SAML and native authentication for hosted deployments" (Elastic); "identity & access management" + "Single-sign-on (SSO)" (IBM); "Single Sign-On with connection to TCloud Active Directory" + "IAM policies, groups and roles" + "Directory services" (Treasury) | **Core** (function 10) |
| 5 | `dedicated_environments` — dedicated / enclave environments & hosting models | 2 | "secured enclaves" + "dedicated application stacks" (Rackspace); "two cloud hosting models: Boundary Protected and Managed" (Treasury) | **Core** (functions 2, 3) |
| 6 | `multi_tenancy` — multi-tenancy / shared service | 2 | "secure multi-tenant architecture" (IBM MaaS360 component); "multi-tenant IaaS/PaaS hosting environment" + "offered as a shared service" (Treasury) | **Core** records slice (function 2); the tenancy isolation itself is platform layer |
| 7 | `deployment_configuration` — deployment templates & preconfigured resources | 2 | "use-case-configured templates ... based on best practices for your specific use case" (Elastic); "Preconfigured networking resources" (Treasury) | **Core** (function 6) |
| 8 | `security_services` — platform security services (IPS/IDS, WAF, endpoint) | 2 | "log aggregation, vulnerability scanning, endpoint protection, file integrity monitoring and host IPS/IDS" (Rackspace); "Intrusion Prevention Services (IPS)" + "Web Application Firewall (WAF)" + "Endpoint Detection and Response (EDR)" + "Anti-Virus" (Treasury) | **Core** (function 8) |
| 9 | `backup_disaster_recovery` — backup, restore & disaster recovery | 2 | "backup, restore, and disaster recovery built-in" (Rackspace); "Disaster recovery and Contingency Planning - Backup and restore" (Treasury) | **Core** (function 9) |
| 10 | `managed_operations` — managed operations (patching, scanning, configuration) | 2 | "24/7/365 operations and system support" (Rackspace); "Operating System (OS) level patching" + "Vulnerability scanning" + "Configuration management for OS and Databases" (Treasury) | **Core** (function 11) |
| 11 | `us_operations_residency` — U.S.-only operations & data residency | 2 | "US Rackspace datacenters" + "U.S. only support model" (Rackspace); "operated exclusively by U.S. citizens with operations and data restricted to U.S. soil" + "U.S.-based cloud environment" (SAP CIE) | **Core** records slice (function 3, caller-stated residency label); verification is Extended |
| 12 | `encryption` — encryption at rest | 1 | "default encryption at rest ... for hosted deployments" (Elastic) | **Core** records slice (function 5, caller-stated label); the cryptography is Extended |
| 13 | `resource_optimization` — application resource management & optimization | 1 | "dynamic resource allocation" + Turbonomic "dynamically allocates resources" (IBM) | **Core** records slice (function 13); the engine is Extended |
| 14 | `ai_recommendations` — AI-driven operational recommendations | 1 | "AI-driven recommendations and tips that are prioritized and customized" (IBM Concert) | **Core** records slice (function 13); the engine is Extended |
| 15 | `account_provisioning` — cloud account provisioning, invoicing & utilization transparency | 1 | "TCloud provides account provisioning and invoicing for designated tenant agencies" + "FinOps dashboards for resource utilization and costs" (Treasury) | **Core** (function 12); invoicing itself is Extended — see the money note |
| 16 | `compliance_authorization_support` — Assessment & Authorization support | 1 | "achieve Assessment & Authorization faster and more cost-effectively" (Rackspace) | Extended (a support service, not a records function); documents CA in part — see baseline |
| 17 | `content_delivery` — content delivery network | 1 | "delivered to end-users through the Akamai Content Delivery Network (CDN)" (Treasury) | Extended (the network itself) |

**The money note.** No fork's description states an amount, a
rate, or a fee schedule — Treasury names invoicing and FinOps cost
dashboards, Rackspace names "cost savings of up to 70%" as outcome
prose. So this build deliberately holds **no money shape anywhere**:
utilization is recorded in integer service units (function 12), and
invoicing/billing is an Extended gap. This is the one founding
category build with no cents discipline, because there is nothing
in the forks' words to denominate.

## Core boundary (stated once)

The build is a records substrate **about** infrastructure. It
records tenancies, environments, deployments, templates, service
arrangements, tasks, accounts, utilization, and recommendations as
the embedding organization records them. It provisions nothing,
orchestrates nothing, carries no traffic, collects no telemetry,
and executes nothing: template settings are stored verbatim and
never run; registries record, they do not operate. Statuses that
are guarded lifecycles are stored; everything that is a
computation over records (tenancy deployment counts, task overdue)
is derived at read time and never stored.

Numbered core functions:

1. Organization registry & membership — carried substrate (house
   standard; the membership boundary every category build shares).
2. Cloud tenancy records — hosting models (`boundary_protected`,
   `managed`, `enclave`, `shared`, the forks' own model words),
   optional provider link; deployment counts derived at read.
3. Hosting environment records — optional tenancy link,
   caller-stated residency label, guarded lifecycle
   provisioned → active → retired.
4. Infrastructure provider registry — providers named as records;
   a registration integrates with nothing.
5. Hosted deployment records — workload as an opaque reference
   inside a tenancy, optional environment/template links,
   caller-stated encryption label, guarded lifecycle
   recorded → active → stopped, under the **deployment slot rule**
   (below).
6. Deployment template registry — settings stored verbatim, never
   executed (pinned by test: no execute/apply/launch/provision
   operation exists).
7. Monitoring records — kinds from the forks' words (continuous,
   network, log ingestion, observability) over opaque targets; no
   telemetry is collected.
8. Platform security service records — the seven named service
   kinds over opaque targets; no engine is operated.
9. Backup & recovery records — backup / restore / disaster
   recovery records; nothing is backed up or restored.
10. Identity configuration records — SSO / IAM policy / directory /
    authentication configurations by kind and label; **no field
    can hold a credential** (shape-pinned by test); the IdP itself
    stays with the embedding organization.
11. Operations task records — patching / vulnerability scanning /
    configuration management / support tasks with required due
    dates; `overdue` derived at read.
12. Cloud account & utilization records — account lifecycle
    open → closed; one utilization record per account per period,
    integer service units only.
13. Recommendation records — resource-optimization and
    AI-recommendation records with caller-supplied detail stored
    verbatim; the substrate generates no recommendations.
14. Registry reporting — counts and unit sums on read; no scores
    and no money exist to report (key-scanned by test).
15. Registry search — literal substring over refs, labels, kinds;
    membership-scoped.
16. Access control (RBAC) & append-only audit — carried substrate.

**Signature invariant — the deployment slot rule.** Within one
tenancy, at most one deployment of a given workload reference may
be active at a time, enforced by the store's
`_check_deployment_slot` seam on activation: a second activation is
refused whole and changes nothing. The seam is this group's
negative control (mutation-verified; see tests/README.md).

## Control baseline — FedRAMP Moderate (NIST SP 800-53) / CMMC L2

Every fork in this group is FedRAMP Moderate, which the DeadRamp
crosswalk maps to CMMC Level 2 for planning purposes. Standing
caveat, as everywhere in this repo: **FedRAMP authorizes products;
CMMC certifies organizations.** The tier is a planning/matching
equivalence, never a credential claim — nothing here asserts that
this build, or any organization running it, holds a FedRAMP
authorization or a CMMC certification.

| Core function | 800-53 families | How the build answers |
|---|---|---|
| 1, 16 Organization registry, RBAC, audit | AC, IA, AU | Role ladder (admin/member/viewer) plus the membership boundary on every org-scoped operation; append-only audit records every successful mutation, and the HTTP layer records denied attempts |
| 2, 3 Tenancy & environment records | AC, CM | Tenancies and environments are access-scoped configuration records; hosting model and lifecycle state are explicit fields, not prose |
| 4 Provider registry | SA, CA | Providers are named records the tenancy links to; the registry asserts no supply-chain verification (that stays with the authorizing process) |
| 5 Deployment records + slot rule | CM, SI-10 | Guarded lifecycle; the slot rule is input validation at the state boundary — one active deployment per workload per tenancy, refused whole on violation |
| 6 Template registry | CM-6 | Configuration settings held as records, verbatim, never executed — configuration is data here, not behavior |
| 7 Monitoring records | AU, SI-4 (records slice) | Monitoring arrangements are recorded by kind and target; the telemetry itself is an engine outside this substrate |
| 8 Security service records | SI-3, SI-4 (records slice) | Named protective services recorded by kind and target; no protective engine is operated |
| 9 Protection records | CP-9, CP-10 (records slice) | Backup/restore/DR arrangements and events recorded; execution is a deployment-layer engine |
| 10 Identity configuration records | IA, AC | Configurations recorded by kind; no credential material exists in any shape; authentication itself is the embedding organization's IdP (IA-2) |
| 11 Operations task records | SI-2, RA-5 (records slice) | Patching and scanning *tasks* with due dates and a derived overdue flag; the scanning/patching engines are Extended |
| 12 Account & utilization records | AC, AU | Account lifecycle plus per-period unit records — utilization accounting without a billing engine |
| 13 Recommendation records | SI, CA (records slice) | Recommendations issued elsewhere are recorded verbatim; the build issues none |
| 14 Reporting | CA, AU | Counts and unit sums derived on read; posture is reported, never scored |
| Documented from fork prose | CA (in part) | Rackspace's Assessment & Authorization support claim documents the CA family at service weight; it is an Extended function, and no baseline section is built on it |

Precision notes, stated once: (a) SC-8/SC-13 — when the embedding
organization serves this substrate over TLS (the CLI supports
`--certfile`/`--keyfile`), transport protection is configured, not
implemented here; the `encryption` family's build surface is a
caller-stated label on a deployment record — **the build performs
no cryptography**, and Python's standard library is not
FIPS-validated, so no FIPS claim is made anywhere. (b) The
residency label on an environment is caller-stated; verifying
U.S.-only operations is an organizational control, recorded as an
Extended gap, not something software in this repo can assert.
(c) Audit records are append-only in this substrate; AU retention
and review policy belong to the embedding organization.

## Named absences (checked against the descriptions, not assumed)

- **Container orchestration / Kubernetes.** The tokens `kubernetes`,
  `docker`, `terraform`, `ansible` occur in none of the six
  descriptions (pinned by test). Treasury's "container security" is
  a workload class inside its unified-platform bullet — protection
  substance, not an orchestration function; no family was invented
  for it.
- **Serverless.** The token occurs in none of the six cached
  descriptions; it appears only in Elastic's live classification
  material (serverless projects on the hosted deployments) — a
  hosting delivery form of the Extended platform, not a family.
- **Database hosting as a function.** SAP HANA Cloud is a catalogue
  entry (excluded with the catalogue); Treasury's "OS and
  Databases" phrase is configuration-management substance and is
  claimed there. No database family exists in this taxonomy.
- **Device / endpoint management.** IBM's bundle includes MaaS360
  endpoint management paragraphs ("endpoint management" occurs only
  in IBM's description, pinned) — that is the Mobile Device
  Management category's ground, which exists elsewhere in the
  registry; no family was created for it here.
- **Hosted business applications.** ERP, HCM/payroll, supply-chain,
  and field-service functions occur only inside the excluded SAP
  catalogue (and Fieldglass is itself a shipped fork elsewhere);
  they are other categories' functions riding on this platform.
- **Learned inference / AI platform functions.** No fork describes
  model inference as a platform function. Elastic's "machine
  learning" occurs once, as a hosted-stack feature name in its
  feature list — it fires no family (pinned as confined to
  Elastic). IBM's AI surface claims recommendations, not inference.
- **Money amounts, rates, fee schedules.** None stated anywhere
  (see the money note in the taxonomy section).

## Near-misses and artifacts (recorded, not repaired)

- **DD-CIE residency artifact.** DD-CIE's description carries the
  sentence "SAP NS2 DDCIE is operated exclusively by U.S. citizens
  with operations and data restricted to U.S. soil" verbatim, but
  the house sentence split cuts the unit after "U.S.", so neither
  residency pattern survives whole and the fork claims
  `hosting_platform` only. CIE claims residency on its surviving
  "U.S.-based cloud environment" phrase. The artifact is pinned by
  test; the count is a floor, as everywhere.
- **Elastic monitoring near-miss.** The ESS sentence names
  "monitoring" among hosted-stack capabilities; the family's
  patterns are the forks' specific phrases (continuous monitoring,
  network monitoring, log ingestion, observability), and a bare
  feature-list noun fires none of them. Elastic claims no
  monitoring family.
- **IBM bundle shape.** IBM's description is a bundle: an overview
  paragraph plus component paragraphs (MaaS360, Verify, Instana,
  Turbonomic, Concert) that are the offering's own composition.
  Claims fire on the bundle's own sentences at that weight; the
  MaaS360 device-management substance is the one part that belongs
  to another category (named absence above), and Verify's
  identity substance supports the `identity_access` claim at the
  same weight as the overview sentence that is its evidence.
- **Treasury's unified-platform bullet** ("data protection,
  vulnerability management, workload protection, and container
  security") is a platform-name enumeration; its workload
  protection substance is named here, and the concrete services in
  Treasury's two model lists are what the claims rest on.

## Gaps registered from this group (for the repo GAPS.md batch)

Extended functions, by name — each is a real engine or service the
forks describe and this records substrate deliberately does not
implement:

1. The hosting platform itself — provisioning & orchestration
   engines (all six forks; the category's centre, held as Extended
   by the core-boundary decision).
2. Elastic Stack hosting engine (Elastic Cloud's hosted-deployment
   machinery, including its serverless delivery form).
3. Deployment template execution / workload launch engine.
4. Monitoring & observability engines (telemetry collection,
   distributed tracing, alerting).
5. Platform security service engines (IPS/IDS, WAF, endpoint
   protection and EDR, anti-virus, file integrity monitoring).
6. Backup execution & disaster-recovery orchestration.
7. Identity provider, single sign-on & directory services (IA-2 —
   stays with the embedding organization).
8. Encryption implementation & key management (FIPS-validated
   modules; SC-13 at deployment weight).
9. Operations execution engines (patch deployment, vulnerability
   scanning, configuration enforcement).
10. Invoicing, billing & FinOps cost engine (Treasury names
    invoicing and cost dashboards; no amounts are recorded here).
11. AI recommendation engine (IBM Concert class) and application
    resource management engine (IBM Turbonomic class).
12. Content delivery network operation (the Akamai CDN Treasury
    delivers through).
13. Assessment & Authorization support services (Rackspace's A&A
    acceleration practice).
14. Residency & personnel verification services (U.S.-citizen
    operations verification behind the residency labels).

Platform layer (unnumbered, as everywhere): multi-tenancy itself
(this build is a single-tenant reference deployment), TLS when
configured, and encryption at rest as deployed.
