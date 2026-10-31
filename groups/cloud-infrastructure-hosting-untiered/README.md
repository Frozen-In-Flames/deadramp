# Cloud Infrastructure & Hosting — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **1 untiered fork** of Cloud
Infrastructure & Hosting — the category founded at the Moderate
tier by Remainder Group 4 (`../cloud-infrastructure-hosting-l2/`).
**This is an untiered set, and that means something specific:**
the member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for this offering, so
**tier stays null**: no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented
control claims; tier stays null in the registry until the source
publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); the spec sheet is in
[`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned
by tests.

## The fork

| Fork | Vendor / Product | Model | Claims |
|---|---|---|---:|
| F1403283529 | Project Hosts Inc. / GSS One - Azure | PaaS (Hybrid Cloud) | 4 |

In `forks.json` the fork is filed "Uncategorized (none in
source)". It sat in the remainder census's **no-signal-set**:
its cached marketplace description carried no citable function
(census citations: none; `no_signal`, reason "prose_only";
`platform_general: true`), so no census build unit proposed a
category for it. Its classification as Cloud Infrastructure &
Hosting was resolved afterwards by the live-docs research pass,
on the vendor's own sentence from its FedRAMP page — "Deploy
your application into a secure GSSOne™ environment designed to
meet federal security requirements."
(https://projecthosts.com/solutions/fedramp/) — recorded on its
spec sheet as `classification_evidence` with its source URL: a
classification citation, **not claim evidence** (it does not
occur in the cached description, pinned by test). The research
pass recorded its boundary adjudication with the citation:
platform/environment prose stating the hosting function itself,
not a sentence emphasizing administration services performed, so
not System Administration. The fork's recorded authorization
status is **FedRAMP In Process** — record data, not a claim.

The fork was spec'd under the category's existing 17-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding group's original
shipped claim tables exactly — **6 of 6 forks, 34 of 34 claims,
deep-equal against git HEAD** — before tagging this fork.
Result here: **4 claims** (`multi_tenancy`,
`monitoring_observability`, `backup_disaster_recovery`,
`managed_operations`), 4 raw hits, 0 removed; the description's
trailing third-party application list (52 units, ~50 hosted
applications) was excluded before matching and the exclusion
removed nothing, checked both ways and pinned by test. The
near-misses are itemized in [`ARTIFACTS.md`](ARTIFACTS.md), not
rounded up — including the set's loudest: the category's centre
family, `hosting_platform`, fires nothing on this fork's words.

The build implements the category's **sixteen-function
substrate** — the records machinery a hosting platform's
arrangements presuppose — carried **byte-identical** from the
founding Cloud Infrastructure & Hosting L2 build
(`../cloud-infrastructure-hosting-l2/src/cloudinfra/`, 7 of 7
modules; SHA-256 accounting below). **In this set, 4 of the 16
functions are claim-supported** (function 2 at its records
slice, and functions 7, 9, and 11) and the remaining 12 are
**carried, not claimed** — stated plainly in the union spec's
core-boundary decision. No tier uplift was applied (there is no
tier to uplift to) and nothing is inherited downward: the
untiered sets carry the founding core at its founding build.
Where the carried code's docstrings say "L2" (the label line in
`__init__.py` and `store.py`), read it as the founding group's
label on byte-identical code: at tier null the hooks are
baseline-neutral substrate, claimed against no baseline.

## The 16 core functions

1. **Organization registry & membership** — carried substrate
   (house standard; the membership boundary every operation
   enforces). *Carried, not claimed in this set.*
2. **Cloud tenancy records** — hosting models in the forks' own
   words (`boundary_protected`, `managed`, `enclave`, `shared`),
   optional provider link; deployment counts derived at read,
   never stored. *Claim-supported at the records slice*
   (`multi_tenancy`).
3. **Hosting environment records** — optional tenancy link,
   caller-stated residency label, guarded lifecycle
   provisioned → active → retired. *Carried, not claimed.*
4. **Infrastructure provider registry** — providers named as
   records; a registration integrates with nothing. *Carried,
   not claimed* (Azure Government is named in the fork's prose
   but no provider family phrase fires).
5. **Hosted deployment records** — workload as an opaque
   reference inside a tenancy, optional environment/template
   links, caller-stated encryption label, guarded lifecycle
   recorded → active → stopped, under the **deployment slot
   rule**: at most one active deployment per workload per
   tenancy, enforced by the `_check_deployment_slot` seam on
   activation (this set's negative control, re-run in this
   tree). *Carried, not claimed.*
6. **Deployment template registry** — settings stored verbatim,
   never executed (pinned by test: no execute/apply/launch/
   provision operation exists). *Carried, not claimed.*
7. **Monitoring records** — kinds from the forks' words
   (continuous, network, log ingestion, observability) over
   opaque targets; no telemetry is collected. *Claim-supported*
   (`monitoring_observability`).
8. **Platform security service records** — the seven named
   service kinds over opaque targets; no engine is operated.
   *Carried, not claimed* (the fork's "intrusion prevention" is
   lowercase where the family's patterns are title-case — a
   case artifact, recorded, not repaired).
9. **Backup & recovery records** — backup / restore / disaster
   recovery records; nothing is backed up or restored.
   *Claim-supported* (`backup_disaster_recovery`).
10. **Identity configuration records** — SSO / IAM policy /
    directory / authentication configurations by kind and
    label; **no field can hold a credential** (shape-pinned by
    test); the IdP itself stays with the embedding organization
    (IA-2). *Carried, not claimed.*
11. **Operations task records** — patching / vulnerability
    scanning / configuration management / support tasks with
    required due dates; `overdue` derived at read, never
    stored. *Claim-supported* (`managed_operations`).
12. **Cloud account & utilization records** — account lifecycle
    open → closed; one utilization record per account per
    period, **integer service units only** (floats, booleans,
    strings rejected at the boundary). There is **no money
    shape anywhere** in this build — no fork in the category
    states an amount, rate, or fee. *Carried, not claimed.*
13. **Recommendation records** — resource-optimization and
    AI-recommendation records with caller-supplied detail
    stored verbatim; the substrate generates no recommendations.
    *Carried, not claimed.*
14. **Registry reporting** — counts and unit sums on read; no
    scores and no money exist to report (key-scanned by test).
    *Carried substrate.*
15. **Registry search** — literal substring over refs, labels,
    kinds; membership-scoped. *Carried substrate.*
16. **Access control (RBAC) & append-only audit** — role ladder
    (admin/member/viewer) plus the membership boundary on every
    org-scoped operation; append-only audit records every
    successful mutation, and the HTTP layer records denied
    attempts. *Carried substrate.*

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type. Records carry
opaque references only.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m cloudinfra serve                  # http://127.0.0.1:8819
PYTHONPATH=src python3 -m cloudinfra serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cloudinfra serve --certfile cert.pem --keyfile key.pem   # TLS
```

Example flow:

```bash
curl -s -X POST localhost:8819/organizations \
  -H 'X-User: alice' -H 'X-Role: admin' \
  -d '{"org_ref":"AGENCY-1","label":"Agency One"}'
curl -s -X POST localhost:8819/organizations/org-1/members \
  -H 'X-User: alice' -H 'X-Role: admin' \
  -d '{"username":"bob"}'
curl -s -X POST localhost:8819/organizations/org-1/tenancies \
  -H 'X-User: bob' -H 'X-Role: member' \
  -d '{"tenancy_ref":"TEN-1","label":"Shared tenancy","hosting_model":"shared"}'
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**,
supplied per request with the `X-User` and `X-Role` headers.
The role header must match the registry exactly, or the request
is rejected with 401 (an unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | every action, including `org_write` and `audit_read` |
| `bob`   | member | every working action (no `org_write`, no `audit_read`) |
| `carol` | viewer | read-only (`org_read`, `report_read`) |

Org-scoped operations additionally require membership in the
organization (or admin). A permitted role performing a forbidden
action gets 403; validation failures get 400; unknown objects
get 404. Errors are always JSON `{"error": "..."}`.

## How to run tests

Tests live in `tests/` (standard library `unittest`):

```sh
PYTHONPATH=src python3 -m unittest discover -s tests        # 119 tests
PYTHONPATH=src python3 tests/smoke.py                       # live smoke
```

**119 tests, OK** at delivery: the founding group's core suite
carried with the code (its `test_specs.py` and
`test_negative_control.py` replaced with this set's own; every
other module byte-identical to the founding group's), plus this
set's spec tests pinning membership (exactly 1 sheet; census
`no-signal-set` membership; tier null / impact "Unknown"; the
literal 4-claim table; the taxonomy-verbatim reproduction proof
against the founding tables at git HEAD; the catalogue
exclusion removing nothing; the classification citation pinned
against `../../remainder/nosignal_report.json`). The category's
signature deployment-slot mutation drill was re-run in this
tree — **exactly 4 failures under the mutant, the founding
drill's identical set**, store restored and SHA-256 verified
(see `tests/README.md` and `tests/mutation-run.txt`).

## Byte-identity accounting

`src/cloudinfra/` is carried from the founding group
`../cloud-infrastructure-hosting-l2/src/cloudinfra/` — **7 of 7
modules byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `7459deccf259d7ad3911f7972d8ab34c80e07b704b869b6d372acdfbe5d61a9e` |
| `__main__.py` | `48e7e14ea4ed4c7713868fea0f8e9868d7d510657c69990bb00ed770c14f87dc` |
| `access.py` | `1f1c5a1ade84075a27bb630fd8aaad1c8015f220299ed45b784cb91cee22f492` |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` |
| `errors.py` | `d6cb58deaf2375b1112c418c36f79bb7c6b0cb4d11f77677cb8a2b479c40d6e5` |
| `service.py` | `c5965dde73a270f9d6a90b55b7f78219f6790341ad0c31bcec75cb0f481a472d` |
| `store.py` | `95d39967282ea5d215687e7f96244d364c7114378d46fe84c5e19c82cad9c405` |

The only carried text that still names the founding tier is
the label line in two docstrings (`__init__.py` line 3 and
`store.py` line 3, each naming the "Cloud Infrastructure &
Hosting L2 union spec") — the founding group's own label inside
byte-identical code, retained so the accounting above is exact;
this group's docs carry the tier-null anchoring. The test suite
is likewise carried (13 modules byte-identical to the founding
group's), with `tests/test_specs.py` and
`tests/test_negative_control.py` written for this set. Full
accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts, in its own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is
not the build's control attainment, and nothing here fills a
family in from any baseline.

Documented by the set's fork (full tracing in `UNION-SPEC.md`):

- **Contingency planning (CP)** — at the **taxonomy tier**: the
  fork's `backup_disaster_recovery` claim sentence asserts it
  composes services that manage "backup, and disaster recovery"
  for each hosted application.
- **Access control (AC), identification & authentication (IA),
  audit (AU), configuration management (CM), system &
  information integrity (SI), incident response (IR)** — at the
  **prose tier**, all traced to the fork's composed-of sentence
  ("…systems and services that manage access control,
  authentication, auditing, monitoring, scanning, patching,
  configuration management, malware prevention, intrusion
  prevention, incident response, backup, and disaster recovery
  for each application leveraging the GSS1-AZ"), with AU and IR
  reinforced by later sentences (SOC review of audit logs;
  incident response reporting, analysis, eradication, and
  recovery). Traced and quoted, never converted — the
  taxonomy's `identity_access` family fires nothing here.
- **Risk assessment (RA) — in part**, prose tier: monthly
  vulnerability scanning (ACAS, dynamic web app, and container
  image scans) with findings tracked under continuous
  monitoring requirements.
- **Assessment & authorization (CA) — in part**, prose tier:
  the fork creates customers' SaaS-level FedRAMP packages,
  helps them through the agency authorization process, manages
  their 3PAO annual assessments, performs compliance reviews,
  and provides monthly POA&Ms. Bound: this documents
  assessment-support activity performed *for customers*; the
  fork asserts no authorization of its own (its status is
  FedRAMP In Process) and none is documented for it.

Recorded but **not** traced to a family: the Ticketing System's
"secure channel" names no mechanism (the token "encrypt"
occurs 0 times; no TLS/FIPS language occurs), so SC is not
documented; the Console's "manage training" is a
customer-facing product function, so AT is not documented.

**Not documented** by the fork: AT, MP, PE, PL, PM, PS, SA,
and SC — asserted by no sentence in the description as control
claims. If the source later publishes an impact level for this
offering, the tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP
  baseline, no CMMC tier, and no authorization — for the fork
  or for itself. The fork's recorded authorization status is
  source data, not a claim by this build, and the fork's
  documented control language is recorded as *its* claim, never
  as the build's control attainment.
- **The classification rests on live vendor prose; the claims
  rest only on the cached description.** The two evidence
  streams never mix, and the spec tests pin that mechanically.
  The census could cite no function sentence for this fork at
  all (0 citations) — the classification needed the vendor's
  live FedRAMP page; the claims did not need it and do not use
  it.
- **Boundary strain, recorded.** The census's managed-platform
  boundary sends prose emphasizing administration services
  *performed* to System Administration. This fork's description
  is dense with performed services (patching, scanning,
  incident response, monitoring — performed by Project Hosts
  engineers), and its platform is styled a "General Support
  System" — the System Administration founding fork's own
  centre vocabulary. The research pass nonetheless classified
  the fork here, on the vendor page's hosting-function sentence
  and its recorded adjudication, and this set keeps that
  classification. In substance the tension is smaller than it
  looks — the category's `managed_operations` family covers
  exactly the performed-operations prose, and the fork claims
  it here on its own words — but the strain is recorded, not
  smoothed over, and no System Administration family, pattern,
  or core function was imported.
- **The category's centre is a named absence here.**
  `hosting_platform` fires nothing on this fork's words
  ("cloud computing environment" is not "cloud environment"),
  and `security_services` fires nothing because "intrusion
  prevention" is lowercase where the family's patterns are
  title-case. Neither was repaired; the taxonomy was not
  re-tuned. Counts are a floor.
- **The build operates no platform.** Extended functions are
  specified, not implemented (see `UNION-SPEC.md`): the hosting
  platform and its provisioning & orchestration engines
  themselves; template execution; monitoring & observability
  engines; platform security service engines; backup execution
  & DR orchestration; the identity provider; encryption
  implementation & key management; operations execution
  engines; invoicing, billing & FinOps; the AI recommendation
  and resource-management engines; CDN operation; A&A support
  services; residency & personnel verification. Of these, the
  monitoring, backup/DR, and operations engines and the
  platform-layer multi-tenancy gain this fork as a claimant
  (A&A support and the identity provider in substance only) —
  recorded in the union spec's gap section, not re-registered.
- **No money, no scores.** Nothing in the build holds a money
  shape (no fork in the category states an amount, rate, or
  fee — the fork's one "money" word is outcome prose about
  wasted resources) and nothing computes a score, rating,
  health, or posture value; reporting is counts and unit sums
  only.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  and `carol` are documented demo identities supplied by
  header; the service enforces the role permission matrix on
  those hooks and ships no identity provider, no credential
  store, and no authentication of its own. IA-2 stays with the
  embedding organization.
