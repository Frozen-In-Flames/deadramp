# Cloud Infrastructure & Hosting L3-adjacent — Union Spec

The High-tier sibling group of the category founded at Moderate
by Remainder Group 4 (`groups/cloud-infrastructure-hosting-l2/`,
shipped at commit 7875481). The remainder census's no-signal
live-doc research pass (`remainder/nosignal_report.json`,
`remainder/NOSIGNAL.md`) resolved 13 forks into **Cloud
Infrastructure & Hosting**; six are FedRAMP High, and they are
this group. The taxonomy is the founding group's, verbatim; the
core is the founding `cloudinfra` substrate carried up whole and
uplifted to the High baseline, never diluted (the Merge Rule:
cross-tier builds extend upward, baselines union, never
intersect).

The category boundary, as the census recorded it and both builds
keep it: prose emphasizing administration services *performed* on
a platform resolves to System Administration; pure platform and
hosting prose resolves here. No System Administration family,
pattern, or core function was imported at either tier.

## Evidence method

Two evidence streams, kept separate by rule and pinned by test,
exactly as at founding:

- **Classification** comes from the vendors' own live public
  pages: each sheet carries `classification_evidence` and
  `classification_source_url` copied from
  `remainder/nosignal_report.json`, which is what places the fork
  in this category at all. For all six forks the classification
  sentence does **not** occur in the cached marketplace
  description.
- **Claims** come only from the fork's cached marketplace
  description (`remainder/uncovered.json`'s `description`, verified
  byte-equal to the cache's `service_desc`), under the founding
  taxonomy. A function is claimed only where matching text
  actually occurs in the description; the first matching unit is
  stored as the claim's evidence. The classification sentence is
  never claim evidence (pinned by test).

Further discipline, as everywhere in this repo: `certified_services`
is never matched (it is empty for all six records — asserted at
extraction); scope-exclusion and disclaimer prose earns nothing;
marketing and outcome prose gets no tags. Counts are a floor. No
hosted-application catalogue exclusion applies to this set (the
founding catalogue lead-ins belong to the SAP NS2 forks, which are
not members here); the raw pass is the final pass, and the
extractor reports it as such.

## Taxonomy — verbatim from the founding group (proof, not prose)

The 17 families, patterns, and labels are the founding group's,
taken from its extractor by `ast` parsing (`ast.literal_eval` of
the `TAXONOMY` assignment; the founding extractor is never
imported or executed) and never re-typed or re-tuned in this
group's extractor.

**Taxonomy-verbatim proof** (run at extraction and pinned by
`test_specs.TestTaxonomyVerbatim`): re-applying the ast-parsed
taxonomy to the founding group's six cached descriptions
reproduces its shipped claim tables exactly — deep-equal against
`groups/cloud-infrastructure-hosting-l2/specs/specs.json` at git
HEAD, 6 sheets, 34 claims. This group's own tables are likewise
recomputed from the census descriptions by the same matcher in
the spec tests.

| # | Family | Claims here | Founding claims | Disposition (as at founding) |
|---|---|---|---|---|
| 1 | `hosting_platform` | 1 | 5 | **Core** (functions 2, 3, 5) |
| 2 | `infrastructure_providers` | 1 | 3 | **Core** (function 4) |
| 3 | `monitoring_observability` | 3 | 3 | **Core** (function 7) |
| 4 | `identity_access` | 2 | 3 | **Core** (function 10) |
| 5 | `dedicated_environments` | 1 | 2 | **Core** (functions 2, 3) |
| 6 | `multi_tenancy` | 3 | 2 | **Core** records slice (function 2); tenancy isolation itself is platform layer |
| 7 | `deployment_configuration` | 1 | 2 | **Core** (function 6) |
| 8 | `security_services` | 1 | 2 | **Core** (function 8) |
| 9 | `backup_disaster_recovery` | 2 | 2 | **Core** (function 9) |
| 10 | `managed_operations` | 1 | 2 | **Core** (function 11) |
| 11 | `us_operations_residency` | 0 | 2 | **Core** records slice (function 3, caller-stated residency label); verification is Extended — no claimant at this tier |
| 12 | `encryption` | 0 | 1 | **Core** records slice (function 5, caller-stated label); the cryptography is Extended — no claimant at this tier |
| 13 | `resource_optimization` | 1 | 1 | **Core** records slice (function 13); the engine is Extended |
| 14 | `ai_recommendations` | 1 | 1 | **Core** records slice (function 13); the engine is Extended |
| 15 | `account_provisioning` | 1 | 1 | **Core** (function 12); invoicing itself is Extended — see the money note |
| 16 | `compliance_authorization_support` | 0 | 1 | Extended (a support service, not a records function) — no claimant at this tier |
| 17 | `content_delivery` | 0 | 1 | Extended (the network itself) — no claimant at this tier |

**The money note, unchanged from founding.** No fork's description
at this tier states an amount, a rate, or a fee schedule either —
IT-CNP names "flexible fixed monthly subscription or
consumption-based billing models" (models, not amounts), Oracle
names "price-performance" as outcome prose. So this build, like
the founding build, deliberately holds **no money shape
anywhere**: utilization is recorded in integer service units
(function 12), and invoicing/billing is an Extended gap.

## Members (6 forks, all FedRAMP High / CMMC L3-adjacent)

| Fork | Vendor / Product | Model | Deployment | Status | Claims | Classification source |
|---|---|---|---|---|---|---|
| F1211011660 | IBM / IBM Cloud for Government | IaaS, PaaS | Hybrid Cloud | FedRAMP Certified | 0 | ibm.com (Service Description, updated Dec 12, 2018) |
| F1208031461A | IBM / IBM Platform Services for Government | SaaS, PaaS | Public Cloud | Agency Authorization In Process | 5 | ibm.com (Federal Government Solutions page) |
| F1206081363 | IBM / SmartCloud for Government | IaaS | Government Community Cloud | FedRAMP Certified | 1 | ibm.com (GSA IT Schedule terms, Ch. 9, rev. Jan 25, 2017 — legacy) |
| F1303221956 | IT-CNP / GovDataHosting Cloud Platform | PaaS, IaaS | Hybrid Cloud | FedRAMP Certified | 3 | it-cnp.com |
| FR1900048743 | Oracle / Oracle Cloud Infrastructure-Government Cloud | IaaS, PaaS | Government Community Cloud | FedRAMP Certified | 0 | oracle.com (Government Cloud page) |
| FR1801046750 | United States Department of the Treasury / Treasury Cloud (TCloud) | IaaS, PaaS | Government Community Cloud | FedRAMP Certified | 10 | home.treasury.gov (FY 2025 Capital Investment Plan) |

**Total 19 claims across 13 families. Zero-claim forks: 2**
(IBM Cloud for Government, Oracle OCI-Gov) — both flagship
infrastructure offerings whose cached descriptions are
posture/overview prose carrying none of the taxonomy's phrases;
their substance is recorded as near-misses below, not repaired
into claims.

Duplicate-authorization pairs, stated plainly:

- **F1208031461A** is the High duplicate-authorization sibling of
  the founding group's F1208031461 (IBM Platform Services). The
  two marketplace records carry the *same description*, so the
  claim tables are identical (5 claims); the records differ where
  records differ — impact level (High vs Moderate) and status
  (Agency Authorization In Process vs FedRAMP Certified). It is a
  separate offering and is spec'd separately, per the Phase 1
  rule; both sheets stand.
- **FR1801046750** (TCloud-H) and the founding group's AGENCYWC2
  (Treasury Cloud Moderate) are separate offerings of the same
  service family with *different* descriptions: the High record's
  service list is wider, yet its table is smaller (10 vs 12) —
  it drops `multi_tenancy` (its tenancy word is the unhyphenated
  "multitenant", which the family's pattern does not fire on) and
  `content_delivery` (the High description names no CDN). Both
  sheets stand; neither is adjusted toward the other.

Recorded caveats at their exact weight: SmartCloud's
classification evidence is a **legacy** source — no current IBM
product page exists; the sentence is IBM's own words in an
IBM-hosted GSA schedule document revised January 25, 2017. IBM
Cloud for Government's evidence is from IBM's own Service
Description updated December 12, 2018. IT-CNP's prose asserts a
"FedRAMP Class D (High)" certification and support for "low,
moderate, and high impact information systems" — recorded as the
fork's assertions; the tier on the sheet is the marketplace
record's High. IT-CNP also asserts that customers "inherit the
heavy lifting of FedRAMP High compliance" over "the underlying
NIST SP 800-53 control set" — posture prose about the fork's own
offering, recorded here; it documents no baseline section of this
build. TCloud-H's prose ("designed to process High Impact level
information") agrees with its record and moves nothing either
way.

## Core boundary (stated once)

The build is the founding records substrate **about**
infrastructure, carried up whole: all 16 numbered core functions
of the founding build are present with their doctrines unchanged
— tenancy deployment counts and task `overdue` derived at read
and never stored; guarded lifecycles stored; template settings
stored verbatim and never executed (no execute/apply/launch/
provision operation exists); identity configuration records whose
shapes cannot hold a credential; utilization in integer service
units with floats, booleans, and strings rejected at the boundary;
**no money shape anywhere**; counts-only reporting, key-scanned;
registries record, they do not operate. The signature invariant
is the founding one: the **deployment slot rule** — within one
tenancy, at most one deployment of a given workload reference may
be active at a time, enforced by the store's
`_check_deployment_slot` seam on activation (mutation-verified at
this tier; see tests/README.md).

**Uplifts taken at this tier** (the repo's established High set,
as applied in `groups/analytics-l3`, `groups/development-tools-l3`,
and `groups/storage-l3`):

1. **Hash-chained audit (AU-9, AU-3)** — every audit entry carries
   `seq`, `prev_hash`, and a SHA-256 `hash` over the canonical
   JSON of its hashed fields (genesis `prev_hash` = `"0"*64`);
   `AuditLog.verify_chain()` localizes the first bad entry;
   exposed as `GET /audit/verify`, whose count is read before its
   own audit entry is recorded.
2. **Fail-closed audit writes (AU-5)** — `AuditLog.record()` rolls
   back the in-memory append and raises `AuditWriteError` on a
   failed JSONL append; every mutating store method is wrapped in
   the snapshot/rollback decorator, so the whole operation rolls
   back; the service answers exactly 500
   `{"error": "audit write failed"}`. Read methods are not
   wrapped: they record no audit entry on success, so there is no
   write to fail closed on.
3. **Audit query & reduction (AU-6, AU-7)** — `AuditLog.query(
   actor, action, target, since, until)` with inclusive bounds,
   plus matching `GET /audit` query parameters; an unfiltered
   `GET /audit` keeps the founding shape.
4. **Auditor role (AC-5, technical slice)** — a fourth role,
   `auditor` (demo user `dana`), holds `audit_read` and nothing
   else; audit review exists as a duty separable from
   administration. Organizational separation-of-duties policy
   remains the embedding organization's.
5. **Logon lockout (AC-7)** — per-username consecutive
   authentication-failure tracking in the service layer; lockout
   at `max_failures` (default 3) for `lockout_seconds` (default
   300); locked attempts — even with the correct role — return
   403 and are audited `auth:locked`; a success resets the
   counter; an expired lock clears itself; unknown usernames lock
   too; permission denials do not count.

**Explicitly NOT inherited or NOT claimed at this tier:**
nothing of the founding core is dropped or diluted — the uplift
is union, per the Merge Rule. Not back-ported in the other
direction either: the founding build makes no AC-5/AC-7/AU-7/
AU-9 claim, and none is asserted for it here. The five demands
considered and **not taken** are named as baseline gaps below
(stronger authentication, FIPS-validated cryptography, encryption
at rest, audit retention, session lock/termination). The
`encryption` and `us_operations_residency` families keep their
founding records-slice disposition at this tier (caller-stated
labels on records) but have **no claimant fork here**, so no core
function gains claim support from them at this tier; the core
carries them as substrate, not as claims.

**Byte-identity accounting** (per module, against the founding
group's `src/cloudinfra/`): **0 of 7 modules byte-identical** —
every module differs, each for a stated reason: `audit.py`
(hash chain, fail-closed record, query — uplift 1–3);
`store.py` (the `_fail_closed` snapshot wrapper on all 20
mutating methods — uplift 2); `service.py` (lockout, `/audit`
query parameters, `/audit/verify`, fail-closed 500, `dana` in the
demo registry — uplifts 1–5 at the HTTP layer); `access.py` (the
`auditor` role — uplift 4); `errors.py` (`AuditWriteError` added);
`__main__.py` (`dana` demo user, `--max-failed-logins` /
`--lockout-seconds` flags); `__init__.py` (tier docstring,
`AuditWriteError` export). The founding logic inside each module
is otherwise carried line-for-line; no founding behavior is
removed.

## Control baseline — FedRAMP High (NIST SP 800-53) / CMMC L3-adjacent

Every fork in this group is FedRAMP High, which the DeadRamp
crosswalk maps to CMMC L3-adjacent for planning purposes.
Standing caveat, as everywhere in this repo: **FedRAMP authorizes
products; CMMC certifies organizations.** The tier is a
planning/matching equivalence, never a credential claim —
nothing here asserts that this build, or any organization running
it, holds a FedRAMP authorization or a CMMC certification.

The founding group's Moderate traceability table carries up
whole (functions 1–16 as there: AC/IA/AU for registry, RBAC and
audit; AC/CM for tenancy and environment records; SA/CA for the
provider registry; CM/SI-10 for deployment records and the slot
rule; CM-6 for the template registry; AU/SI-4, SI-3/SI-4,
CP-9/CP-10, IA/AC, SI-2/RA-5, AC/AU, SI/CA, CA/AU at the records
weights stated there). The rows that **change** at High are the
substrate rows, and they change by union — the High baseline is
the Moderate baseline plus the uplift demands:

| Core function | 800-53 families | How the build answers at High |
|---|---|---|
| 1, 16 Organization registry, RBAC, audit | AC, IA, AU + **AC-5**, **AU-5**, **AU-7**, **AU-9** | Four-role matrix (admin/member/viewer/auditor) enforced before any mutation or id allocation; `audit_read` held by admin **and** the separated **auditor** role, which holds nothing else (AC-5, technical slice); append-only **hash-chained** audit (AU-9/AU-3) including denied attempts at the HTTP layer, **fail-closed** on write error with whole-operation rollback (AU-5), reducible by query (AU-7) and verifiable via `GET /audit/verify` |
| Service authentication | **AC-7**, IA-2 (hooks) | Per-username consecutive-authentication-failure lockout in the service layer (defaults: 3 failures, 300 s), locked attempts answered 403 and audited `auth:locked`; permission denials do not count |

- **Tier-uplift analysis — what High demanded beyond the
  founding core:**

  | Demand (High / 800-172 direction) | Founding core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented** (uplift 1) |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed** (uplift 2): record rolls back and raises; every mutating store method rolls back whole on snapshot; the service answers exactly 500 `{"error": "audit write failed"}` |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented** (uplift 3) |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented** (uplift 5) |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)** (uplift 4) |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named — not taken**: identity-provider properties. This build ships hooks, not an IdP (the founding posture, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named — not taken**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here. No fork's IL or FIPS posture transfers to this build |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged — not taken**: remains a deployment-layer control; this tier additionally has no `encryption` claimant fork |
  | Audit retention (AU-11) | Not addressed | **Gap, named — not taken**: no retention-period enforcement for the trail in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named — not taken**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

Precision notes, stated once: (a) SC-8/SC-13 — when the embedding
organization serves this substrate over TLS (the CLI supports
`--certfile`/`--keyfile`), transport protection is configured,
not implemented here; the build performs no cryptography beyond
the audit chain's SHA-256 (an integrity mechanism, not a
validated cryptographic module claim), and **no FIPS claim is
made anywhere**. (b) The residency label on an environment is
caller-stated; verifying U.S.-only operations is an
organizational control, recorded as an Extended gap, not
something software in this repo can assert — at this tier no fork
even claims the residency family (see near-misses). (c) Audit
records are append-only in this substrate; AU retention and
review policy belong to the embedding organization (AU-11 is a
named gap above). (d) At founding, Rackspace's A&A-support claim
documented the CA family in part at service weight; **no fork at
this tier claims `compliance_authorization_support`**, so CA is
carried by the baseline section only, and nothing here is built
on fork prose for it.

## Named absences (checked against the descriptions, not assumed)

- **Container orchestration / Kubernetes.** The tokens
  `kubernetes`, `docker`, `terraform`, `ansible` occur in none of
  the six descriptions (pinned by test). TCloud-H's "container
  security" is a workload class inside its unified-platform
  bullet — protection substance, not an orchestration function;
  no family was invented for it (the founding group's identical
  finding for its Treasury fork).
- **Serverless.** The token occurs in none of the six cached
  descriptions.
- **Learned inference / AI platform functions.** No fork describes
  model inference, and the token string "machine learning" occurs
  in none of the six descriptions (pinned). Platform Services'
  AI surface claims recommendations, not inference.
- **Database hosting as a function.** No database family exists in
  this taxonomy. SmartCloud's service list names "Storage
  Management and Backup" and "Storage management" as managed
  service items; IT-CNP's "databases" phrase sits inside its
  managed-layers sentence (claimed there under monitoring and
  backup). Neither is a database-hosting claim.
- **Device / endpoint management.** Platform Services' bundle
  includes MaaS360 endpoint management paragraphs ("endpoint
  management" occurs only in that fork's description, pinned) —
  that is the Mobile Device Management category's ground, which
  exists elsewhere in the registry; no family was created for it
  here, at this tier exactly as at founding.
- **Hosted business applications.** None of these six
  descriptions enumerates hosted business applications (the
  founding tier's SAP catalogue situation does not recur here).
- **Money amounts, rates, fee schedules.** None stated anywhere
  (see the money note in the taxonomy section).

## Near-misses and artifacts (recorded, not repaired)

- **IBM Cloud for Government (zero claims).** Its description
  carries provisioning and orchestration substance in its own
  words ("automated provisioning of services in public, private,
  and hybrid cloud offerings"; "orchestration of bare metal and
  virtual servers") — but the taxonomy's `hosting_platform`
  patterns are the founding forks' specific phrases, and none
  fires. The fork is the category's centre described in other
  words; it claims zero, and the gap register below records its
  substance under the platform gap. Pinned by test.
- **Oracle OCI-Gov (zero claims).** Platform prose throughout
  ("government-community cloud", "infrastructure and platform
  cloud services", "scale elastically") with no family phrase;
  zero claims, pinned.
- **IT-CNP identity near-miss.** The description spells "identity
  and access management" in its managed-layers sentence; the
  family's pattern is the founding phrase "identity & access
  management" (ampersand). No `identity_access` claim. The same
  sentence does claim monitoring and backup, whose phrases it
  carries verbatim.
- **IT-CNP residency near-miss.** "100% of our datacenters and
  24/7/365 mission-critical support are provided from the
  continental United States by U.S. persons" is residency
  substance in the fork's own words; none of the family's phrases
  ("restricted to U.S. soil", "operated exclusively by U.S.
  citizens", "U.S.-based cloud environment") occurs, so
  `us_operations_residency` claims nothing here.
- **SmartCloud operations near-miss.** Its service list carries
  "System Vulnerability Scanning" (capital S); the family's
  pattern is "Vulnerability scanning" — no `managed_operations`
  claim. Its "fully managed, cloud hosting services" likewise
  fires no `hosting_platform` pattern (the family's phrases are
  "fully-managed cloud", "hosting environment", and kin). Its one
  claim is `multi_tenancy`, on its first sentence.
- **TCloud-H tenancy near-miss.** "multitenant,
  government-exclusive cloud platforms" — the unhyphenated word
  does not fire the family's "multi-tenant" pattern, so the High
  record claims no `multi_tenancy` although its Moderate sibling
  does (see the pair note above).
- **Platform Services bundle shape (as at founding).** The
  description is a bundle: an overview paragraph plus component
  paragraphs (MaaS360, Verify, Instana, Turbonomic, Concert) that
  are the offering's own composition. Claims fire on the bundle's
  own sentences at that weight; the MaaS360 device-management
  substance is another category's ground (named absence above).

## Gaps at this tier (for the repo GAPS.md batch)

The founding group's 14 registered gaps are **already
registered**; they are not re-registered here. Their claimant
state at this tier, by name:

- **Gain or hold claimants:** the hosting platform /
  provisioning & orchestration engines (TCloud-H claims the
  hosting family; IBM Cloud for Government's provisioning and
  orchestration substance stands behind the same gap at
  zero-claim weight — the gap's centre at this tier); deployment
  template execution engine (TCloud-H); monitoring &
  observability engines (Platform Services, IT-CNP, TCloud-H —
  3 claimants, as at founding); platform security service
  engines (TCloud-H); backup execution & DR orchestration
  (IT-CNP, TCloud-H — 2, as at founding); application resource
  management engine and AI recommendation engine (Platform
  Services claims both families, the same fork as at founding);
  invoicing, billing & FinOps engine (TCloud-H, as at founding);
  identity provider / SSO / directory services (Platform
  Services, TCloud-H — 2 claimants; the IA-2 boundary is
  unchanged).
- **Lose all taxonomy claimants at this tier:** the Elastic
  Stack hosting engine (Elastic is a founding-tier fork only);
  encryption implementation & key management (`encryption` 0/6 —
  the records slice is carried, claim-supported by nothing here);
  content delivery network operation (`content_delivery` 0/6 —
  the High Treasury record names no CDN); Assessment &
  Authorization support services
  (`compliance_authorization_support` 0/6); residency & personnel
  verification services (`us_operations_residency` 0/6 at
  taxonomy weight — IT-CNP's U.S.-persons sentence stands behind
  the gap in substance, recorded in the near-misses).
- **Operations execution engines** hold one claimant
  (`managed_operations`, TCloud-H) against two at founding.

**New at this tier — High baseline gaps (from the uplift
analysis, not taken):** stronger authentication at the identity
layer (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator
management — an IdP property the embedding organization must
supply); FIPS-validated cryptography (SC-13); encryption at rest
as a deployment control (SC-28); audit retention enforcement
(AU-11); session lock / termination (AC-11, AC-12).

Platform layer (unnumbered, as everywhere): multi-tenancy itself
(this build is a single-tenant reference deployment), TLS when
configured, and encryption at rest as deployed.
