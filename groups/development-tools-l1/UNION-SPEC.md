# Union Spec — Development Tools, CMMC L1 (DeadRamp Phase 2, Group 17)

The merged functional spec for the Development Tools **L1** sibling group:
**5 forks**, category **Development Tools**, CMMC tier **L1**. This group
mixes two FedRAMP impact levels: **2 forks are FedRAMP Low** (The
Armory20x, Digital Enterprise Suite FedRAMP Edition) and **3 are LI-SaaS**
(Articulate 360, CircleCI Cloud, GitHub Enterprise Cloud). Both map to L1
on the crosswalk (`../../crosswalk.md`): LI-SaaS is FedRAMP's own tailored
**subset** of the Low baseline for SaaS offerings, so the union of the
group's parent baselines is the Low baseline itself, and the highest tier
any parent carries is the Low family. The group baseline is therefore the
**NIST SP 800-53 Rev. 5 Low baseline** ⇔ **CMMC L1** (the FAR 52.204-21
practice set), taken in full (Merge Rules 1 and 2). Every member is
FedRAMP Certified in `forks.json` — verified. Each fork's **actual**
impact level (Low or LI-SaaS) is recorded per fork in its spec sheet.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 5 entries in
exactly the Group 1 schema, each with the offering's full public
marketplace description and its function claims tagged from that
description, every claim carrying the source sentence as evidence.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. The member list reconciles against `MAP.md`'s "Development
Tools — L1 (5)" section and against `forks.json` (category "Development
Tools", `cmmc_tier` "L1") with **zero diffs** — asserted in
`scratch/extract.py` (specs vendor+product multiset == forks.json group
== MAP.md section; per-fork impact levels checked against both sources).

**The group's character, recorded honestly:** this category is largely a
source-category artifact. Only two members are genuine development tools —
**GitHub Enterprise Cloud** (collaborative code platform: plan, build,
review, ship; bug tracking; discussion) and **CircleCI Cloud** (continuous
integration and delivery: build/test/deploy automation,
configuration-as-code, vendor-managed CI instances). The other three sit
in the category for adjacent reasons: **Articulate 360** is a course
authoring subscription ("the entire course development process");
**The Armory20x** is a FedRAMP 20x deployment landing zone — tenants on
Google Cloud Platform in which CSPs/ISVs deploy workloads, with
stackArmor's automated assessment providing Key Security Indicator (KSI)
status; **Digital Enterprise Suite FedRAMP Edition** (Trisotech) is a
business modeling and business automation suite (visual modeling,
programmatic/business logic, Digital Modeling Suite + Digital Automation
Suite). There is no single product they all are. What the claim counts
below support as a union is a **records substrate for the development
lifecycle**: projects/repositories held in a registry, issues tracked,
code reviews recorded, build and release records kept, artifacts
registered with checksums, environments and deployments recorded, and
search, access control, and audit over those records. The merged build
implements that substrate; each vendor's execution engines on top of it
(CI runners, git internals, authoring tools, modeling engines, landing
zone provisioning, KSI automation) are Extended functions, named in the
long tail under the exact gap names the implementation side uses.

## How functions were counted

Each fork's public marketplace description was sentence-split and matched
against a **17-family taxonomy defined from this category's
descriptions**. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is stored
in `specs/specs.json` as evidence, so every claim is auditable. Marketing
prose gets no tags (e.g. CircleCI's "Scale is where https://circleci.com
really shines" claims nothing). **14 claims survived.** Wording-artifact
corrections were needed and are itemized in `scratch/ARTIFACTS.md` (29
broad first-pass hits → 14: **15 false hits removed, 0 true hits
recovered, 2 evidence re-bases** with count unchanged — the classic
classes: bare "security"/"securely"/"authorized" describing the offering's
own FedRAMP posture tagged as access control ×3; the substring "author"
inside "authorized/authorizable" tagged as content authoring; bare
"platform" tagged as hosting; "find bugs" tagged as issue tracking;
"continuous integration" tagged as an external integration claim).
**No fork has zero claims.** Per-fork claim counts: CircleCI Cloud 4,
GitHub Enterprise Cloud 4, The Armory20x 3, Digital Enterprise Suite
FedRAMP Edition 2, Articulate 360 1. Counts are a **floor**, not a
ceiling: the descriptions are short (277–1,259 characters) — Articulate
360's entire description is three sentences, and no conclusion about the
real Articulate 360, GitHub, or CircleCI products should be drawn from
their tag counts.

## Function ranking — all 5 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Deployment & release | 2 | 40% | **Core** — release records (Core 5) and deployment records (Core 7); execution is Extended (see gaps) |
| 1 | Hosted platform & managed operations | 2 | 40% | Platform note — not a development function; single-tenant reference deployment (provisioning/operations: Extended, gap "Landing-zone / tenant provisioning & hosted platform operations") |
| 3 | Project/repository registry & code collaboration | 1 | 20% | **Core** — Core 1 (records substrate; claim support thin: 1/5, GitHub only — see Core note) |
| 3 | Issue & work-item tracking | 1 | 20% | **Core** — Core 2 |
| 3 | Code review & discussion | 1 | 20% | **Core** — Core 3 (records only — no merge engine) |
| 3 | CI build/test pipeline automation | 1 | 20% | **Core slice**: build records (Core 4). Execution: Extended — "CI/CD execution engines (pipeline execution — build/test/deploy runners)" |
| 3 | Configuration as code | 1 | 20% | Extended — "Configuration-as-code execution & orchestration" |
| 3 | Deployment environments, landing zones & tenants | 1 | 20% | **Core slice**: environment & deployment records (Core 7). Provisioning: Extended — "Landing-zone / tenant provisioning & hosted platform operations" |
| 3 | Compliance assessment & KSI status reporting | 1 | 20% | Extended — "Compliance assessment & KSI status automation engines" |
| 3 | Visual modeling & design | 1 | 20% | Extended — "Business modeling & automation engines (modeling + execution)" |
| 3 | Workflow & business automation | 1 | 20% | Extended — "Business modeling & automation engines (modeling + execution)" |
| 3 | Content & course authoring | 1 | 20% | Extended — "Course & content authoring tools" |
| 13 | Artifact/package registry | 0 | 0% | **Core** — Core 6 (0 descriptive claims; substrate/baseline item, flagged in the Core note; binary storage Extended — "Artifact binary storage backends (the registry holds records + checksums only)") |
| 13 | API & integrations | 0 | 0% | **Not claimed by any sibling in this group** — named absence (the build's own REST surface is its implementation contract, not a sibling claim) |
| 13 | Access control | 0 | 0% | **Core** — Core 9, RBAC (0 descriptive claims; baseline-carried, flagged in the Core note) |
| 13 | Audit logging | 0 | 0% | **Core** — Core 10 (0 descriptive claims; baseline-carried, AU on the Low side only, flagged in the Core note) |
| 13 | Search | 0 | 0% | **Core** — Core 8 (0 descriptive claims; substrate operation over the build's own registry metadata, flagged in the Core note) |

**Differences are preserved, not averaged away**: the Extended rows and
the zero-claim rows are the record of how this group actually divides —
GitHub's collaboration/tracking/review claims, CircleCI's CI/release/
configuration claims, Armory20x's landing-zone/KSI claims, Trisotech's
modeling/automation claims, and Articulate's single authoring claim share
almost no family between them (no family exceeds 2 of 5 siblings, and the
two 2-of-5 families pair different forks: release = CircleCI + GitHub,
hosted = CircleCI + Armory20x). The per-fork spec sheets name which
siblings claim what.

## The Core — what the merged build implements (10 functions)

The shared records substrate the counts support, plus the baseline hooks
flagged where the counts do not:

1. **Project & repository registry (records)** — projects/repositories
   held as registry records. *Support: project_collaboration 1/5
   (GitHub's collaborative development platform). Flag: no description
   words a "registry" or "repository" as a noun; the registry is the
   record form the claimed collaboration, tracking, review, and release
   functions all presuppose — the same substrate reasoning the Analytics
   groups applied to their dataset registry.*
2. **Issue & work-item tracking with lifecycle (open → in_progress → resolved → closed, reopen paths)**
   — issue/work-item records bound to
   registry projects, moving through the stated lifecycle. *Support:
   issue_tracking 1/5 (GitHub's "tracking bugs"). Flag: the lifecycle
   states are the record form tracking presupposes; no description words
   the states themselves.*
3. **Code-review records (records only — no merge engine)** — records of
   reviews and discussion on registry projects. *Support: code_review
   1/5 (GitHub's "review, and ship software … discussing ideas"). The
   Core holds records; merging and branching engines are Extended
   ("Code hosting internals (git storage, branching & merging
   engines)").*
4. **Build records (records of build runs with status — no execution)**
   — records of build runs (project, status, timing) with no runner
   behind them. *Support: ci_pipeline 1/5 (CircleCI's continuous
   integration automating "the build, test, and deploy process").
   Execution is Extended ("CI/CD execution engines (pipeline execution —
   build/test/deploy runners)"); compilers and toolchains are Extended
   ("Compilers & build toolchains").*
5. **Release records (versioned, per-project unique version)** —
   versioned release records bound to a project; a version is unique
   within its project. *Support: deployment_release 2/5 (CircleCI's
   "release code", GitHub's "ship software") — the group's joint-largest
   development family.*
6. **Artifact registry with checksums (SHA-256 records; verify-by-content; binary storage is NOT in the build)**
   — artifact records (name,
   project/release binding, SHA-256) with verification by supplied
   content against the recorded checksum. *Support: 0/5 descriptive
   claims — flagged. The registry is the substrate release and
   deployment records presuppose (an unnamed artifact is what a release
   record points at); binary storage is Extended ("Artifact binary
   storage backends (the registry holds records + checksums only)").*
7. **Environment & deployment records (environments, and deployment records binding project + release/artifact to an environment)**
   —
   environment records (including landing-zone/tenant environments)
   and deployment records binding a project and a release or artifact
   to an environment. *Support: landing_zones 1/5 (Armory20x's
   deployment landing zone and tenants) and deployment_release 2/5.
   Provisioning the environments themselves is Extended
   ("Landing-zone / tenant provisioning & hosted platform operations").*
8. **Search over registry metadata** — search across the registry's own
   metadata (projects, issues, reviews, builds, releases, artifacts,
   environments, deployments). *Support: 0/5 descriptive claims —
   flagged. Search here is a substrate operation over the build's own
   records, not a sibling's search engine; no sibling claims one.*
9. **RBAC (roles admin/developer/viewer; alice/bob/carol demo identities as hooks)**
   — role-based access enforced before any state change.
   *Support: 0/5 descriptive claims — flagged (every "security"/
   "securely"/"authorized" hit in this group was a posture artifact;
   see `scratch/ARTIFACTS.md` item 1). RBAC is Core because the Low/L1
   baseline requires it (AC/IA families, traceability below) and
   because every sibling's records presuppose differentiated
   developer/viewer access; it is a baseline hook, not a claim-count
   winner. The demo identities are hooks, not an IdP.*
10. **Append-only audit log (baseline-carried; AU on the Low side only)**
    — an append-only audit trail: every mutation and denied
    attempt recorded with actor, action, target, and UTC timestamp.
    *Support: 0/5 descriptive claims — no description in this group
    mentions audit. Included solely as a Low-baseline hook (AU family
    on the FedRAMP Low side of the crosswalk only), flagged here so no
    reader mistakes it for a claimed vendor function; see the precision
    note in the baseline section.*

## Long tail — Extended, by name

Exactly the gap names the implementation side uses:

- **CI/CD execution engines (pipeline execution — build/test/deploy
  runners)** (ci_pipeline 1/5) — CircleCI's actual build/test/deploy
  execution. The Core holds build *records* only.
- **Code hosting internals (git storage, branching & merging engines)**
  — the engine side of GitHub's collaboration/review claims (1/5 each).
  The Core holds registry and review *records* only.
- **Compilers & build toolchains** — no description claims a toolchain;
  named because build records (Core 4) presuppose one existed wherever
  a real build ran. The build ships none.
- **Configuration-as-code execution & orchestration** (config_as_code
  1/5) — CircleCI's configuration-as-code, executed. The Core stores no
  configuration engine; the claim is specified here, not implemented.
- **Compliance assessment & KSI status automation engines**
  (compliance_ksi 1/5) — Armory20x's automated assessment solution and
  KSI status reporting for 20x tenants.
- **Business modeling & automation engines (modeling + execution)**
  (visual_modeling 1/5, business_automation 1/5) — Trisotech's Digital
  Modeling Suite and Digital Automation Suite: modeling, and execution
  of the modeled business logic.
- **Course & content authoring tools** (content_authoring 1/5) —
  Articulate 360's desktop and web authoring apps for course
  development.
- **Landing-zone / tenant provisioning & hosted platform operations**
  (landing_zones 1/5, hosted_platform 2/5) — provisioning Armory20x
  tenants/landing zones, CircleCI's vendor-run CI instances, and hosted
  platform operations generally. Hosting is a platform-layer property,
  never a development function; the merged build is a single-tenant
  reference deployment and says so.
- **Artifact binary storage backends (the registry holds records +
  checksums only)** — storage of the artifact binaries themselves;
  Core 6 deliberately holds records and SHA-256 checksums, with
  verify-by-content, and no binary store.

**Named absence:** **API & integrations** (0/5) — checked with broad
patterns; the only hits were the letters/word "integration" inside
CircleCI's "continuous integration" and a plugins sentence asserting the
*absence* of plugin management. No sibling claims an API or an external
integration. The merged build's own HTTP API (implementation contract
below) is its design, not a union function.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`). Tier mix: **Low 2 / LI-SaaS 3**, each fork's
  actual level recorded in its spec sheet.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored subset of it), cross-walked
  to the FAR 52.204-21 practices that define CMMC L1. Derivation per the
  Merge Rule: union of parent baselines = Low (the LI-SaaS subset adds
  nothing beyond it), inherited in full. This baseline is written fresh
  for the lightest tier.
- **Feature → control family mapping (this build, at the Low baseline):**
  - Access control hooks (Core 9) → **AC** (AC-2 account management,
    AC-3 access enforcement; FAR 52.204-21's access-limitation practices:
    limit system access to authorized users and to the transactions and
    functions they are authorized to execute), **IA** (IA-2
    identification & authentication — identity is supplied by the
    embedding organization via user/role headers; the service ships
    hooks, not an identity provider; FAR's practices: identify system
    users, processes, and devices, and authenticate them before allowing
    access). Demo identities alice/bob/carol are hooks, not an IdP —
    IA-2 stays with the embedding organization.
  - Audit log (Core 10) → **AU**, **on the FedRAMP Low side of the
    crosswalk only** (AU-2 event logging, AU-3 content of audit
    records; the append-only store and permission-gated read are
    implementation properties). **Precision note:** CMMC L1 / FAR
    52.204-21 contains **no audit practice**, so no audit claim is made
    on the CMMC side. The audit log is carried because the FedRAMP Low
    baseline carries the AU family — not because L1 asks for it.
  - Registry records, lifecycle transitions, checksum verification, and
    search (Cores 1–8) → **SI** (SI-10 information input validation —
    malformed input is rejected, never partially applied; per-project
    unique release versions and SHA-256 verify-by-content are record
    integrity properties of the store) and **SC** (SC-8 transmission
    confidentiality — the server runs over TLS when a certificate is
    configured; FAR's system-and-communications-protection practices
    cover boundary protection and protecting transmitted information at
    the family level). Encryption at rest is a deployment-layer
    control, stated plainly, not claimed here. No sibling in this group
    claims an encryption function.
- **What this tier does not carry, and this build does not claim:** the
  Moderate/High apparatus from the sibling groups (e.g. Moderate-level
  audit enhancements, lockout machinery, and 800-172-derived
  requirements) is out of scope for a Low/L1 merge and is **not
  inherited downward**.
- **Standing platform notes:** encryption at rest is deployment-layer;
  TLS applies only when configured; multi-tenancy (named in prose by
  Armory20x's tenants) is a deployment property — the merged build is a
  single-tenant reference deployment; demo identities are hooks, not an
  IdP (IA-2 stays with the embedding organization).
- **Caveat (standing, from crosswalk.md):** FedRAMP authorizes
  **products**; CMMC certifies **organizations**. A FedRAMP impact level
  is a statement about a cloud service offering; a CMMC level is a
  statement about a company and how it handles FCI/CUI. The L1 / FedRAMP
  Low equivalence used here is a **planning/matching equivalence
  only**: it says these forks sit at comparable assurance weight so they
  can be grouped and merged consistently. It does **not** claim that a
  FedRAMP-authorized product confers CMMC certification on anyone, that
  a CMMC-certified organization holds a FedRAMP authorization, or that
  either regime accepts the other as evidence. This traceability is a
  planning mapping; the merged build is not a FedRAMP authorization and
  confers no CMMC certification, and neither credential is claimed.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**, package `devtools` under `src/`,
runnable and testable with `PYTHONPATH=src`:

- `devtools/errors.py` — `DevToolsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.
- `devtools/access.py` — `User(name, role)`; roles
  `admin|developer|viewer`; `PERMISSIONS`: admin ⊇ {write, verify,
  audit_read, admin}, developer = {write, verify}, viewer = {} (read and
  search only); `require(user, action)` raises `PermissionDenied`.
- `devtools/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL file.
- `devtools/store.py` — `DevToolsStore(audit=None)` holding the eight
  record sets; sequential prefixed ids `"prj-1"`, `"iss-1"`, `"rev-1"`,
  `"bld-1"`, `"rel-1"`, `"art-1"`, `"env-1"`, `"dep-1"`, … per set.
  Projects `{id, name, …}`; issues carry the lifecycle states
  `open → in_progress → resolved → closed` with reopen paths back to
  `open`; releases enforce per-project unique `version`; artifacts carry
  a SHA-256 checksum with verify-by-content; deployments bind
  `project + release/artifact → environment`. Malformed input raises
  `ValidationError` and changes nothing.
- `devtools/service.py` — `make_server(host, port, store, audit, users)`
  → `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth
  via `X-User` / `X-Role` headers (role must match the registry).
  Endpoints: `GET /health`, `GET|POST /projects`,
  `GET /projects/{id}`, `GET|POST /issues`, `POST /issues/{id}/status`,
  `GET|POST /reviews`, `POST /reviews/{id}/state`,
  `GET|POST /builds`, `GET|POST /releases`, `GET|POST /artifacts`,
  `POST /artifacts/{id}/verify`, `GET|POST /environments`,
  `GET|POST /deployments`, `GET /search`, `GET /audit`. Errors are JSON
  `{error}` with 400/401/403/404 as applicable. Denied attempts are
  audited.
- `devtools/__main__.py` — `python -m devtools serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=developer, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's, per
  IA-2 above).

## Coverage statement (for this spec batch)

- Specs: **5 / 5** forks spec'd (Low 2, LI-SaaS 3; each fork's actual
  impact level recorded in its spec sheet), reconciled zero-diff against
  `forks.json` and `MAP.md`.
- Claims: **14 total**, every claim carrying its source sentence as
  evidence; per-fork counts CircleCI Cloud 4, GitHub Enterprise Cloud 4,
  The Armory20x 3, Digital Enterprise Suite FedRAMP Edition 2,
  Articulate 360 1; **zero-claim forks: none**.
- Taxonomy: **17 function families** defined from this category's
  descriptions; 12 claimed by at least one sibling, 5 at **0/5** and
  recorded as named absences rather than dropped silently (artifact/
  package registry, API & integrations, access control, audit logging,
  search — of these, artifact registry, access control, audit, and
  search enter the Core only as flagged substrate/baseline items, and
  API & integrations is absent from the union entirely).
- Artifact corrections: **15 false hits removed, 0 true hits recovered,
  2 evidence re-bases**, itemized in `scratch/ARTIFACTS.md` (29 broad
  first-pass hits → 14 final claims).
- Core specified: **10 / 10 functions**, exactly the list above (6 fully
  or partly claim-supported — registry, issues, reviews, builds,
  releases, environments/deployments; 4 flagged substrate/baseline
  items — artifact registry, search, RBAC, audit), each flagged as such.
- Extended: **9 named gaps**, specified and ranked, **not** implemented
  in the Core build — "CI/CD execution engines (pipeline execution —
  build/test/deploy runners)", "Code hosting internals (git storage,
  branching & merging engines)", "Compilers & build toolchains",
  "Configuration-as-code execution & orchestration", "Compliance
  assessment & KSI status automation engines", "Business modeling &
  automation engines (modeling + execution)", "Course & content
  authoring tools", "Landing-zone / tenant provisioning & hosted
  platform operations", "Artifact binary storage backends (the registry
  holds records + checksums only)" — named here rather than implied
  done. No implementation code in this batch — specs and union spec
  only; the implementation is built in parallel against the Core list
  above.
