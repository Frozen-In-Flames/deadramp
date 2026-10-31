# Union Spec — Cloud Infrastructure & Hosting, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **Cloud Infrastructure & Hosting
untiered set**: **1 fork**, category **Cloud Infrastructure &
Hosting**, **tier null**. The member's FedRAMP impact level is
**Unknown** in the source dataset — the source publishes no
baseline for this offering — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly one fork: **F1403283529 — Project Hosts
Inc. / GSS One - Azure** (PaaS, deployment model Hybrid Cloud,
authorization status **FedRAMP In Process** — a status is record
data, not a claim). In `forks.json` the fork is filed
"Uncategorized (none in source)"; it sat in the remainder
census's `no-signal-set` (no citable function in its cached
description, census citations none, `platform_general: true`),
and its category was resolved by the no-signal live-doc research
pass (`../../remainder/nosignal_report.json`) on the vendor's
own sentence from its FedRAMP page: "Deploy your application
into a secure GSSOne™ environment designed to meet federal
security requirements." (https://projecthosts.com/solutions/fedramp/).
The research pass recorded its boundary adjudication with the
citation: platform/environment prose stating the hosting
function itself, not a sentence emphasizing administration
services performed, so not System Administration. The boundary
strain this creates is recorded under Honesty findings in the
README and not hidden: the fork's cached description is dense
with services Project Hosts performs, and this set claims the
fork in this category on the research pass's adjudication plus
the taxonomy outcome below.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) —
1 entry, with the offering's full public marketplace description
and its function claims tagged from that description, every
claim carrying the source sentence as evidence, the sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier:
null`, and the classification citation recorded as
`classification_evidence` / `classification_source_url` —
a classification citation, kept distinct from claim evidence.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product record joined
by FedRAMP ID; the census carries the same record's
`service_desc` verbatim in `../../remainder/uncovered.json`,
verified byte-equal at extraction.

## How functions were counted

The category's fixed 17-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../cloud-infrastructure-hosting-l2/scratch/extract.py`,
parsed, never executed, never re-typed) and asserts it is the
same 17 families before tagging.

Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 6 of 6 forks, 34 of 34 claims, deep-equal** against
the founding sheets at git HEAD — using the founding method:
the founding unit split (paragraphs → lines → sentences, bullet
markers stripped, "e.g." protected) and the founding evidence
rule (first matching unit stored as evidence), including the
founding SAP catalogue exclusions. The proof is re-run as a pin
inside this set's suite.

Applied verbatim to this set's fork, the mechanical pass
produced **4 raw hits and 0 removals** — **4 claims**:

| Family | Evidence (first matching unit, verbatim) |
|---|---|
| `multi_tenancy` | "GSS One-Azure (GSS1-AZ) is delivered as a hybrid offering using a multi-tenant PaaS cloud computing environment." |
| `monitoring_observability` | "Namely, Project Hosts deploys, secures, manages, and provides continuous monitoring for applications that are compatible with the GSS1-AZ architecture, authentication, operating system, database, and access requirements." |
| `backup_disaster_recovery` | "GSS1-AZ is composed of systems and services that manage access control, authentication, auditing, monitoring, scanning, patching, configuration management, malware prevention, intrusion prevention, incident response, backup, and disaster recovery for each application leveraging the GSS1-AZ." |
| `managed_operations` | "Project Hosts security compliance team also performs monthly vulnerability scanning include ACAS scans, dynamic web app scans and container image scans and documents and tracks these findings in accordance with continuous monitoring requirements." |

Exclusion discipline, as everywhere in this repo:
`certified_services` is never matched (it is empty for this
record — asserted at extraction). The description's final
section is a partial list of third-party applications hosted ON
the platform (52 units after its lead-in sentence, ~50 entries);
those applications' functions belong to other categories, so
the list units were excluded before matching — checked both
ways, **the exclusion removed nothing**, and the equality is
pinned by test. One scope adjudication was recorded (kept, with
reasons) in `ARTIFACTS.md`: the monitoring evidence sentence
sits in a paragraph the fork frames as services "over and above
the PaaS offering described in the GSS1-AZ FedRAMP package";
the sentence itself is a plain first-party functional assertion
with no exclusion phrasing, and claims here measure described
functions. A function is claimed for the fork **only** when its
own description contains matching text; counts are a **floor**,
not a ceiling. The near-misses are itemized in `ARTIFACTS.md`:
the taxonomy phrases several families in the founding forks'
exact words, and this fork asserts the corresponding substance
in other vocabulary (or, for `security_services`, in the wrong
case). The taxonomy was not re-tuned.

Census citations: the census recorded **0 citations** for this
fork, so 0 verify and 0 serve as claim evidence — there were no
cited function sentences to verify; the fork's classification
rests on the live-doc citation alone, recorded on the sheet.

## Function ranking — the set's 1 fork

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | `hosting_platform` — hosting / managed cloud platform | 0 | **Core** (functions 2, 3, 5) — **no claimant in this set; named absence** |
| 2 | `infrastructure_providers` — underlying cloud infrastructure & providers | 0 | **Core** (function 4) — **no claimant in this set; named absence** |
| 3 | `monitoring_observability` — monitoring & observability | 1 | **Core** (function 7) — claimed |
| 4 | `identity_access` — identity, access & directory services | 0 | **Core** (function 10) — **no claimant in this set; named absence** |
| 5 | `dedicated_environments` — dedicated / enclave environments & hosting models | 0 | **Core** (functions 2, 3) — **no claimant in this set; named absence** |
| 6 | `multi_tenancy` — multi-tenancy / shared service | 1 | **Core** records slice (function 2) — claimed; the tenancy isolation itself is platform layer |
| 7 | `deployment_configuration` — deployment templates & preconfigured resources | 0 | **Core** (function 6) — **no claimant in this set** |
| 8 | `security_services` — platform security services (IPS/IDS, WAF, endpoint) | 0 | **Core** (function 8) — **no claimant in this set; named absence (case artifact)** |
| 9 | `backup_disaster_recovery` — backup, restore & disaster recovery | 1 | **Core** (function 9) — claimed |
| 10 | `managed_operations` — managed operations (patching, scanning, configuration) | 1 | **Core** (function 11) — claimed |
| 11 | `us_operations_residency` — U.S.-only operations & data residency | 0 | **Core** records slice (function 3) — **no claimant in this set; named absence** |
| 12 | `encryption` — encryption at rest | 0 | **Core** records slice (function 5) — **no claimant in this set** (the token "encrypt" occurs 0 times) |
| 13 | `resource_optimization` — application resource management & optimization | 0 | **Core** records slice (function 13) — **no claimant in this set** |
| 14 | `ai_recommendations` — AI-driven operational recommendations | 0 | **Core** records slice (function 13) — **no claimant in this set** |
| 15 | `account_provisioning` — cloud account provisioning, invoicing & utilization transparency | 0 | **Core** (function 12) — **no claimant in this set; named absence** |
| 16 | `compliance_authorization_support` — Assessment & Authorization support | 0 | Extended (a support service, not a records function) — **no claimant in this set; named absence (exact phrases absent)** |
| 17 | `content_delivery` — content delivery network | 0 | Extended (the network itself) — **no claimant in this set** |

## The Core — what this build implements (16 functions)

**Core-boundary decision (stated once):** the build carries
the founding group's sixteen-function substrate **whole** —
organization registry & membership; cloud tenancy records;
hosting environment records; infrastructure provider registry;
hosted deployment records under the deployment slot rule;
deployment template registry (settings stored verbatim, never
executed); monitoring records; platform security service
records; backup & recovery records; identity configuration
records (no field can hold a credential); operations task
records; cloud account & utilization records; recommendation
records; registry reporting (counts and unit sums only);
registry search; and access control (RBAC) & append-only
audit. The substrate is the records machinery the category's
merged build implements — records *about* infrastructure: it
provisions nothing, orchestrates nothing, carries no traffic,
collects no telemetry, and executes nothing. **In this set,
4 of the 16 functions are claim-supported** — function 2 at
its records slice (via `multi_tenancy`), function 7
(`monitoring_observability`), function 9
(`backup_disaster_recovery`), and function 11
(`managed_operations`) — and the remaining 12 are **carried,
not claimed**: the substrate's warrant for them in this set is
the category's merged build, not this fork's wording. That is
stated plainly rather than softened.

The carried code is **byte-identical** to the founding group's
`src/cloudinfra/` (7 of 7 modules; SHA-256 accounting in this
group's README and `tests/README.md`). There is no tier to
uplift to and none was applied; no tier's build is inherited
downward either — the untiered sets carry the founding core at
its founding build, unchanged. The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `cloudinfra` under `src/`, ids sequential
per object type with fixed prefixes, failed operations consume
no id and change nothing, roles `admin|member|viewer` with the
founding permission matrix layered under organization
membership, and the audit log append-only with denied attempts
recorded at the HTTP layer. The founding doctrines are
preserved exactly: the **deployment slot rule** (at most one
active deployment per workload reference per tenancy, enforced
by the store's `_check_deployment_slot` seam on activation —
this set's negative control, re-run in this tree); utilization
in **integer service units only**, and **no money shape
anywhere** (no fork in this category states an amount, rate, or
fee, so there is nothing to denominate); template settings
stored verbatim and never executed (pinned by test: no
execute/apply/launch/provision operation exists); identity
configuration shapes that provably cannot hold a credential
(shape-pinned by test); statuses that are guarded lifecycles
stored, everything that is a computation over records (tenancy
deployment counts, task `overdue`) derived at read and never
stored; reporting as counts and unit sums only, with no score
and no money anywhere in any view (key-scanned by test). Where
the carried code's docstrings say "L2" (the label line in
`__init__.py` and `store.py`), read it as the founding group's
label on byte-identical carried code: at tier null the hooks
are baseline-neutral substrate, claimed against no baseline.

**This build operates no platform.** It holds the records a
hosting platform's arrangements presuppose; it deploys no
application, monitors no workload, and performs no operations.
The engines themselves are gaps, named below.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts, in its own words. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment,
and nothing in this section fills a family in from any
baseline. (The taxonomy families above are function families;
this section reads the description's control language
separately, exactly as the founding spec separated its baseline
traceability from its claims.)

Control areas **documented** by the set's fork:

- **Contingency planning (CP)** — documented at the **taxonomy
  tier**: the fork's `backup_disaster_recovery` claim evidence
  sentence asserts it is "composed of systems and services that
  manage … backup, and disaster recovery for each application
  leveraging the GSS1-AZ". (The build's function 9 records
  backup/recovery arrangements; nothing is backed up or
  restored by this build.)
- **Access control (AC)** — prose tier: the same composed-of
  sentence names "access control" among the services the GSS
  composes; the GSS One Portal sentence adds user administration
  substance ("create and manage non privileged users for their
  organization including revoking access"). Traced and quoted,
  never converted: the taxonomy's `identity_access` family
  fires nothing on this description.
- **Identification & authentication (IA)** — prose tier: the
  composed-of sentence names "authentication". No mechanism is
  named (no MFA, SSO, or directory phrase occurs), so IA is
  documented at prose weight only.
- **Audit (AU)** — prose tier: the composed-of sentence names
  "auditing"; a later sentence adds "all SOC review and
  analysis of audit logs and responding/investigating alerts
  for suspicious activity".
- **Configuration management (CM)** — prose tier: the
  composed-of sentence names "configuration management"; a
  later sentence repeats it ("monthly baseline compliance
  scanning, configuration management, patch and vulnerability
  management").
- **System & information integrity (SI)** — prose tier: the
  composed-of sentence names "monitoring, scanning, …
  malware prevention, intrusion prevention" among the composed
  services. (The monitoring/scanning *functions* are claimed
  under the taxonomy separately; this entry documents the
  control language only.)
- **Incident response (IR)** — prose tier: the composed-of
  sentence names "incident response"; a later passage details
  "incident response reporting, analysis, eradication, and
  recovery".
- **Risk assessment (RA)** — documented **in part**, prose
  tier: the fork performs "monthly vulnerability scanning
  include ACAS scans, dynamic web app scans and container image
  scans" and tracks the findings "in accordance with continuous
  monitoring requirements" — vulnerability scanning (RA-5
  substance) in its own words. The same sentence carries the
  set's `managed_operations` taxonomy claim; the control
  reading is recorded here separately and converts nothing.
- **Assessment & authorization (CA)** — documented **in part**,
  prose tier: the fork "creates their SaaS-level FedRAMP
  package, helps them throughout the agency authorization
  process, and manages their 3PAO annual assessments"; it
  "performs compliance reviews", "provides a monthly
  application-level POA&M", and its Console lets customers
  "link controls to artifacts and evidence to speed up ATO
  times". Bound, stated plainly: this documents
  assessment-support *activity the fork performs for its
  customers*; the fork asserts no authorization of its own (its
  recorded status is FedRAMP In Process) and none is documented
  for it. The taxonomy's `compliance_authorization_support`
  family fires nothing — its exact phrases occur 0 times — so
  this entry stands at prose weight only.

Recorded but **not** traced to a family: the GSS One Ticketing
System's "communicate with PH staff through a secure channel"
names no mechanism — the token "encrypt" occurs 0 times in the
description and no TLS or FIPS-validated-cryptography language
occurs — so it is recorded here as posture prose, not as an SC
claim. The GSS One Console's "allows them to manage training"
is a customer-facing product function the fork sells, not a
control claim about the fork itself, so AT is not documented.

Control areas **not documented** by the fork: AT, MP, PE, PL,
PM, PS, SA, and SC — asserted by no sentence in the description
as control claims (SC per the bound above). If the source later
publishes an impact level for this offering, the tier is
recorded then and not before.

## Named absences

- **hosting_platform — 0 of 1, the set's loudest absence.** The
  category's centre family fires nothing on this fork's words:
  "multi-tenant PaaS cloud computing environment" is not the
  family's "cloud environment" phrase, and no other hosting
  pattern occurs. The fork is in the category on its
  classification citation and claims four neighbouring
  families; the centre is recorded claimless, not repaired.
- **infrastructure_providers — 0 of 1, with the host named.**
  Azure Government is named as the deployment platform
  ("deployed on Azure Government", "FedRAMP-authorized Azure
  PaaS services") but none of the family's provider phrases
  occurs, so function 4 is carried, not claimed.
- **identity_access — 0 of 1, with substance throughout.**
  Access control, authentication, user administration, and JIT
  access are asserted across the Portal and composed-of prose;
  no family phrase occurs (see Documented control claims, where
  the same language is traced at prose tier instead).
- **security_services — 0 of 1, a case artifact.** "intrusion
  prevention" occurs twice in lowercase; the family's patterns
  are title-case. "malware prevention" and "Network Security
  Group firewall access controls" carry the substance in other
  words. Recorded, not repaired; the taxonomy was not re-tuned.
- **dedicated_environments — 0 of 1, with substance.**
  "customer-dedicated virtual servers", "customer-dedicated
  subnets", and "dedicated applications just for their agency"
  assert the function; the family's phrases do not occur.
- **us_operations_residency — 0 of 1, with substance.** A
  "Government Only" General Support System on Azure Government
  is residency posture in substance; the family's phrases are
  the founding forks' own words and none occurs.
- **account_provisioning — 0 of 1.** "account creation" is
  Portal prose; "account provisioning and invoicing" and the
  FinOps token are absent, and no amount, rate, or fee is
  stated anywhere — the build's no-money shape stands.
- **compliance_authorization_support — 0 of 1 at family
  weight**, with the category's densest A&A substance outside
  the founding group (see CA, documented in part, above).
- **deployment_configuration, encryption,
  resource_optimization, ai_recommendations, content_delivery
  — 0 of 1 each**, no substance asserted. Container
  orchestration / Kubernetes, serverless, and database hosting
  tokens occur 0 times in the description (pinned by test), as
  in the founding group.
- **Zero-claim forks: none** — the set's only fork claims 4.

## Gaps (registered for the final batch)

The founding group's gaps stand as registered there; this
section records only which of them **gain a claimant in this
set** (taxonomy claimant unless marked substance-only). No
founding gap is re-registered here, and no founding gap loses
a claimant (this set adds a fork; it removes none).

- **Monitoring & observability engines** (founding gap 4) —
  **gains a claimant**: this fork (`monitoring_observability`).
  The build records monitoring arrangements; telemetry
  collection, tracing, and alerting remain unimplemented.
- **Backup execution & disaster-recovery orchestration**
  (founding gap 6) — **gains a claimant**: this fork
  (`backup_disaster_recovery`). The build records arrangements;
  nothing is backed up, restored, or orchestrated.
- **Operations execution engines** (founding gap 9) —
  **gains a claimant**: this fork (`managed_operations`).
  Patch deployment, scanning execution, and configuration
  enforcement remain unimplemented; the build records the
  tasks.
- **Platform layer — multi-tenancy itself** (founding
  platform layer, unnumbered) — **gains a claimant**: this fork
  (`multi_tenancy`). The build records tenancies; isolation is
  a deployment property, not something this substrate performs.
- **Assessment & Authorization support services** (founding
  gap 13) — gains a claimant **in substance only**: the fork's
  A&A practice is documented in part at prose tier (above), but
  the taxonomy family fires nothing on its exact phrases, so
  no taxonomy claimant is counted.
- **Identity provider, single sign-on & directory services**
  (founding gap 7) — gains substance only: access-control and
  authentication language is traced at prose tier; the family
  fires nothing, and IA-2 stays with the embedding organization.

Every other founding gap — the hosting platform and its
provisioning & orchestration engines (gap 1), the Elastic
Stack hosting engine (2), template execution (3), platform
security service engines (5), encryption implementation & key
management (8), invoicing/billing & FinOps (10), the AI
recommendation and resource-management engines (11), CDN
operation (12), and residency & personnel verification (14) —
has **no claimant in this set** and stands exactly as
registered by the founding group.

## Coverage statement (for this build)

1 fork spec'd of 1 in the set (the category's only untiered
fork; census unit `no-signal-set`, category resolved by the
live-doc research pass); 4 taxonomy claims tagged from the
fork's own cached description under the founding taxonomy
applied verbatim, the taxonomy-verbatim proof reproduced
against the founding group's shipped tables first (6 of 6
forks, 34 of 34 claims, deep-equal vs git HEAD); the
sixteen-function substrate carried byte-identical from the
founding Cloud Infrastructure & Hosting L2 build and
re-anchored to tier null; tier null recorded on the sheet and
pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
the fork or for the build itself.
