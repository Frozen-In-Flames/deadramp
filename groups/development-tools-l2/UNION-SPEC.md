# Union Spec — Development Tools, CMMC L2 (DeadRamp Phase 2, Group 29)

The merged functional spec for the Development Tools **L2** sibling
group: **2 forks**, category **Development Tools**, CMMC tier **L2**.
Both members are **FedRAMP Moderate** and **FedRAMP Certified** in
`forks.json` — verified: **AutoRABIT for Public Sector - CodeScan,
Guard, & ARMOR** (AutoRABIT Holding, Inc.) and **LaunchDarkly**
(LaunchDarkly). The group is single-tier, so the union of the parent
baselines is the Moderate baseline itself, and the highest tier any
parent carries is Moderate: the group baseline is the **NIST SP
800-53 Rev. 5 Moderate baseline** ⇔ **CMMC L2** (the 110 requirements
of NIST SP 800-171), taken in full (Merge Rules 1 and 2).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries in exactly the Group 1 schema, each with the offering's full
public marketplace description and its function claims tagged from
that description, every claim carrying the source sentence as
evidence. Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. The member list reconciles against `MAP.md`'s
"Development Tools — L2 (2)" section and against `forks.json`
(category "Development Tools", `cmmc_tier` "L2") with **zero diffs**
— asserted programmatically in `scratch/extract.py` (specs
vendor+product multiset == forks.json group == MAP.md section;
per-fork impact levels and authorization statuses checked against
both sources). No live fetching was needed: both descriptions were
present in the cached dataset.

## Relationship to Group 17 (the L1 sibling build)

This is the second tier of an existing category. Group 17
(`../development-tools-l1/`) defined the taxonomy and built the
development-lifecycle records substrate at the Low/L1 baseline. This
group uses Group 17's **taxonomy verbatim** (same 17 family ids,
labels, and tightened matching patterns) so cross-tier claim counts
are comparable, and — per the core analysis below — **reuses Group
17's implementation in full**: all 7 `src/devtools/` modules are
**byte-identical** to Group 17's (SHA-256 listed in the
implementation contract), and all 16 test files are byte-identical
as copied. What is new in this group is its own spec batch, the
Moderate baseline written fresh below, a fresh mutation drill in
this tree, and the claim analysis of two very different products.
No Moderate/High apparatus from other groups is inherited sideways;
equally, nothing from the L3-adjacent builds (hash-chained audit,
lockout, auditor role, 800-172 requirements) is claimed here.

**The group's character, recorded honestly:** unlike L1 — where
only two of five members were genuine development tools — **both**
forks here are genuine development platforms, but of specialized
kinds whose centers of gravity sit largely **outside** the L1
taxonomy's 17 families. **AutoRABIT** is a Salesforce DevSecOps
suite: CodeScan (static code analysis with 700+ rules, quality
profiles and gates), Guard (continuous Salesforce security
monitoring and automated remediation), and ARMOR (a release-management
platform unifying CI/CD, environment management, and data migration
with immutable audit trails). **LaunchDarkly** is the feature
management platform: feature flags separating code deployment from
feature release, targeting, percentage rollouts, experimentation,
and sub-200-millisecond incident resolution via flag kill switches.
Neither description is a general code-hosting or CI-execution claim,
and the taxonomy — applied verbatim, not re-tuned — tags only four
claims across the two. The merged build is therefore the same
**records substrate** as L1 (projects/repositories in a registry,
issues, review records, build and release records, artifacts by
checksum, environments and deployments, search, RBAC, audit), which
is the record form both products' claimed and near-miss functions
presuppose; each platform's execution engines (flag evaluation,
static analysis, monitoring/remediation, release automation) are
Extended, named in the long tail. The spec records this plainly
rather than forcing the products into families their descriptions do
not phrase.

## How functions were counted

Each fork's public marketplace description was sentence-split and
matched against Group 17's **17-family taxonomy, verbatim**. A family
is claimed only when the offering's own description contains matching
text; the first matching sentence is stored in `specs/specs.json` as
evidence, so every claim is auditable. Marketing prose gets no tags.
**4 claims survived.** Wording-artifact corrections are itemized in
`scratch/ARTIFACTS.md`: **22 broad first-pass hits → 5 tightened hits
→ 4 final claims** (17 false hits removed by the verbatim tightened
patterns — bare assurance/domain vocabulary, "continuous integration"
mistaken for an integration claim, audience/category nouns,
product-noun "platform" and runtime "environment", non-business
automation, and release vocabulary that is not the family's
code-release phrasing; **1 further tightened hit removed** as a
correction: AutoRABIT's "manual reviews" names the human process
Guard replaces, not a code-review function; **0 true hits
recovered**). **No fork has zero claims.** Per-fork claim counts:
AutoRABIT 2 (api_integrations, audit_logging), LaunchDarkly 2
(ci_pipeline, access_control). Counts are a **floor**, not a
ceiling: both descriptions are ~1,800 characters, and no conclusion
about the real AutoRABIT or LaunchDarkly products should be drawn
from their tag counts — in particular, both products' dominant
functions (static analysis and Salesforce release/security
automation; feature management) match **no family** in the verbatim
taxonomy and are recorded as near-misses and Extended gaps instead
(see `scratch/ARTIFACTS.md`).

## Function ranking — all 2 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | CI build/test pipeline automation | 1 | 50% | **Core slice**: build records (Core 4). Execution: Extended — "CI/CD execution engines (pipeline execution — build/test/deploy runners)" |
| 1 | API & integrations | 1 | 50% | Extended — "External-system integration engines" (new in this group). The build's own REST surface is its implementation contract, not a sibling claim |
| 1 | Access control | 1 | 50% | **Core** — Core 9, RBAC (claim-supported here: LaunchDarkly's feature-level RBAC; at L1 this family was 0/5 and RBAC was baseline-carried only) |
| 1 | Audit logging | 1 | 50% | **Core** — Core 10 (claim-supported here: AutoRABIT's "immutable audit trails"; at L1 this family was 0/5) |
| 5 | Project/repository registry & code collaboration | 0 | 0% | **Core** — Core 1 (records substrate; 0 claims in this group — carried, flagged in the Core note) |
| 5 | Issue & work-item tracking | 0 | 0% | **Core** — Core 2 (carried substrate, flagged) |
| 5 | Code review & discussion | 0 | 0% | **Core** — Core 3 (records only — no merge engine; carried substrate, flagged; the group's one raw hit was the item-7 correction) |
| 5 | Deployment & release | 0 | 0% | **Core records** — release records (Core 5) and deployment records (Core 7) stand as substrate (flagged); the family's verbatim phrases fire on neither description — ARMOR's "Release Management platform" is a recorded near-miss. Execution is Extended (gap 1 and new gap 14) |
| 5 | Configuration as code | 0 | 0% | Extended — "Configuration-as-code execution & orchestration" (carried; ARMOR's "strict configuration control" is a recorded near-miss) |
| 5 | Artifact/package registry | 0 | 0% | **Core** — Core 6 (0 descriptive claims; substrate/baseline item, flagged; binary storage Extended — carried gap 9) |
| 5 | Deployment environments, landing zones & tenants | 0 | 0% | **Core slice**: environment & deployment records (Core 7). Provisioning: Extended — "Landing-zone / tenant provisioning & hosted platform operations" (carried; ARMOR's "environment management" is a recorded near-miss) |
| 5 | Compliance assessment & KSI status reporting | 0 | 0% | Extended — "Compliance assessment & KSI status automation engines" (carried; Guard's governance prose claims no KSI/automated-assessment phrase) |
| 5 | Visual modeling & design | 0 | 0% | Extended — "Business modeling & automation engines (modeling + execution)" (carried) |
| 5 | Workflow & business automation | 0 | 0% | Extended — "Business modeling & automation engines (modeling + execution)" (carried; LaunchDarkly's "approval workflows" is a recorded near-miss) |
| 5 | Content & course authoring | 0 | 0% | Extended — "Course & content authoring tools" (carried) |
| 5 | Hosted platform & managed operations | 0 | 0% | Platform note — not a development function; single-tenant reference deployment (provisioning/operations: Extended, carried gap 8; LaunchDarkly's "hosting options" is a recorded near-miss) |
| 5 | Search | 0 | 0% | **Core** — Core 8 (0 descriptive claims; substrate operation over the build's own registry metadata, flagged) |

**Differences are preserved, not averaged away**: the two forks
share **no claimed family at all** — AutoRABIT's pair
(integrations, audit) and LaunchDarkly's pair (CI pipeline, access
control) are disjoint, and the families each product's prose comes
closest to (deployment/release for both) tag on neither. The union
is held together by the records substrate and the tier, not by
overlapping claims, and the per-fork spec sheets name which sibling
claims what.

**How this group differs from Group 17 (L1)** — preserved, not
averaged away: three families that sat at 0/5 at L1 gain genuine
claims here (access control 1/2, audit logging 1/2, API &
integrations 1/2 — API/integrations was absent from the L1 union
entirely and enters this group's union as an Extended gap), while
deployment & release drops from 2/5 to 0/2 on phrasing alone (both
L2 descriptions are saturated with release vocabulary; none of it is
the family's verbatim code-release phrasing — items 6–7 of
`scratch/ARTIFACTS.md`). Search remains 0 at both tiers.

## The Core — what the merged build implements (10 functions)

The same records substrate as Group 17, with this group's support
flags stated exactly: **3 of the 10 Core functions carry claim
support in this group** (Core 4's slice, Core 9, Core 10); **7 are
carried** as the substrate the claimed and near-miss functions
presuppose, under the recorded core-boundary decision below — they
are not presented as claimed here.

1. **Project & repository registry (records)** — projects/repositories
   held as registry records. *Support in this group: 0/2 — carried.
   The registry is the record form the lifecycle functions all
   presuppose (Group 17's reasoning, unchanged).*
2. **Issue & work-item tracking with lifecycle (open → in_progress →
   resolved → closed, reopen paths)** — issue/work-item records bound
   to registry projects, moving through the stated lifecycle.
   *Support: 0/2 — carried. (AutoRABIT's remediated "issues" and
   LaunchDarkly's resolved "incidents" are recorded near-misses, not
   tracking claims.)*
3. **Code-review records (records only — no merge engine)** — records
   of reviews and discussion on registry projects. *Support: 0/2 —
   carried. The group's single raw review hit was removed as the
   item-7 wording-artifact correction.*
4. **Build records (records of build runs with status — no
   execution)** — records of build runs (project, status, timing)
   with no runner behind them. *Support: ci_pipeline 1/2
   (LaunchDarkly's spelled-out Continuous Integration/Continuous
   Delivery facilitation). Execution is Extended (gap 1); compilers
   and toolchains are Extended (gap 3).*
5. **Release records (versioned, per-project unique version)** —
   versioned release records bound to a project; a version is unique
   within its project. *Support: deployment_release 0/2 in this
   group — carried substrate. Release records are the record form
   of ARMOR's release-management domain and of LaunchDarkly's
   feature releases, even though the family's verb phrases fire on
   neither description; the near-miss is recorded, not rounded up.*
6. **Artifact registry with checksums (SHA-256 records;
   verify-by-content; binary storage is NOT in the build)** —
   artifact records (name, project/release binding, SHA-256) with
   verification by supplied content against the recorded checksum.
   *Support: 0/2 descriptive claims — carried, as at L1. Binary
   storage is Extended (gap 9).*
7. **Environment & deployment records (environments, and deployment
   records binding project + release/artifact to an environment)**
   — environment records and deployment records binding a project
   and a release or artifact to an environment. *Support: 0/2 —
   carried. ARMOR's "environment management" is a recorded
   near-miss for the landing-zone family; provisioning the
   environments themselves is Extended (gap 8).*
8. **Search over registry metadata** — search across the registry's
   own metadata (projects, issues, reviews, builds, releases,
   artifacts, environments, deployments). *Support: 0/2 descriptive
   claims — carried. Search here is a substrate operation over the
   build's own records, not a sibling's search engine; no sibling
   claims one at either tier.*
9. **RBAC (roles admin/developer/viewer; alice/bob/carol demo
   identities as hooks)** — role-based access enforced before any
   state change. *Support: access_control 1/2 (LaunchDarkly's
   "custom role-based access control down to the feature level") —
   claim-supported in this group, and independently required by the
   Moderate baseline (AC/IA families, traceability below). The demo
   identities are hooks, not an IdP.*
10. **Append-only audit log** — an append-only audit trail: every
    mutation and denied attempt recorded with actor, action, target,
    and UTC timestamp. *Support: audit_logging 1/2 (AutoRABIT
    ARMOR's "immutable audit trails") — claim-supported in this
    group, and carried by the Moderate baseline's AU family on both
    sides of the crosswalk (see the precision note below).*

**Core-boundary decision (recorded):** the substrate stands in this
group on three claimed functions, two products whose presupposed
record forms are exactly the substrate's (releases, environments,
builds, deployments are the objects both descriptions manipulate in
prose), and the Moderate baseline's own requirements for access
control and audit. No function was added to the Core for this tier:
neither description claims a records function beyond the substrate,
and everything beyond it that the descriptions *do* claim or
approach — flag evaluation, static analysis, monitoring and
remediation, release automation, integrations — is an execution
engine, which this project's discipline assigns to Extended at
every tier. Extending the Core with an engine on the strength of
one sibling's prose would claim a commonality the evidence does not
establish.

## Long tail — Extended, by name

Carried from the Group 17 union (gaps 1–9, exact names unchanged),
then new in this group (gaps 10–15):

1. **CI/CD execution engines (pipeline execution — build/test/deploy
   runners)** (ci_pipeline 1/2 here; 1/5 at L1) — the actual
   build/test/deploy execution behind the facilitation claim. The
   Core holds build *records* only.
2. **Code hosting internals (git storage, branching & merging
   engines)** — 0 claims at this tier; carried so the category
   union is complete. The Core holds registry and review *records*
   only.
3. **Compilers & build toolchains** — no description at either tier
   claims a toolchain; named because build records (Core 4)
   presuppose one existed wherever a real build ran. The build
   ships none.
4. **Configuration-as-code execution & orchestration**
   (config_as_code 0/2 here; 1/5 at L1) — configuration executed as
   an engine. ARMOR's "strict configuration control" is governance
   prose, recorded as a near-miss.
5. **Compliance assessment & KSI status automation engines**
   (compliance_ksi 0/2 here; 1/5 at L1) — no sibling at this tier
   claims a KSI or automated-assessment phrase.
6. **Business modeling & automation engines (modeling +
   execution)** (0/2 here; 2/5 at L1 across its two families).
7. **Course & content authoring tools** (0/2 here; 1/5 at L1).
8. **Landing-zone / tenant provisioning & hosted platform
   operations** (landing_zones 0/2, hosted_platform 0/2 here) —
   provisioning environments/tenants and hosted platform operations
   generally. Hosting is a platform-layer property, never a
   development function; the merged build is a single-tenant
   reference deployment and says so.
9. **Artifact binary storage backends (the registry holds records +
   checksums only)** — storage of the artifact binaries themselves;
   Core 6 deliberately holds records and SHA-256 checksums, with
   verify-by-content, and no binary store.
10. **Feature-flag & feature-management runtime** (LaunchDarkly) —
    flag evaluation and serving, audience targeting, percentage
    rollouts, and the kill-switch actuation behind the
    sub-200-millisecond incident-resolution claim. The taxonomy has
    no family for feature management; the Core's records (projects,
    releases, deployments) are the record form around it, and no
    flag is evaluated anywhere in this build.
11. **Experimentation engine** (LaunchDarkly) — hypothesis-driven
    development: experiment assignment, exposure and outcome
    records-as-engine, and rollout decisions from results. No
    taxonomy family; not implemented.
12. **Static code analysis engine** (AutoRABIT CodeScan) — the
    analyzer itself: 700+ built-in security/quality rules, custom
    rule definition, quality profiles, and quality gates enforced
    in the development/deployment process. No taxonomy family; the
    Core holds no analyzer.
13. **Security posture monitoring & automated remediation engine**
    (AutoRABIT Guard) — continuous monitoring of a Salesforce
    environment for security gaps, policy enforcement at scale, and
    automatic remediation. An engine over a live environment; not
    implemented.
14. **Release automation, environment management & data migration
    engine** (AutoRABIT ARMOR) — executing the unified CI/CD,
    environment-management, and data-migration pipeline for
    Salesforce metadata and data, with policy-driven automation and
    pre-deployment security analysis. The Core holds the *records*
    of builds, releases, environments, and deployments; the
    execution is this gap.
15. **External-system integration engines** (api_integrations 1/2 —
    AutoRABIT) — integrations that actually execute against external
    systems (CodeScan's integration into Salesforce development and
    deployment processes and external systems). The Core's REST API
    is the build's own surface; no connector executes anywhere in
    this build. (At L1 this family was 0/5 and absent from the
    union; it enters the union here on a genuine claim.)

**Platform-layer gaps (named, not implied closed):** encryption at
rest (deployment layer; SC-28 is a deployment property, not claimed
here); TLS only when configured (SC-8 — the server runs over TLS
when a certificate is supplied; the default serve mode is plain
HTTP for local/demo use); multi-tenancy (a deployment property —
the merged build is a single-tenant reference deployment; neither
description claims multi-tenancy under the family's phrasing);
demo identities are hooks, not an IdP (IA-2 stays with the
embedding organization, which supplies production identity,
authentication strength, and account lifecycle).

## Control baseline (traceability) — Moderate / L2

Written fresh for this tier; not copied from Group 17's Low
baseline.

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`). Tier mix: **Moderate 2 / 2**, each fork's
  impact level recorded in its spec sheet.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the **110
  requirements of NIST SP 800-171** that define CMMC L2. Derivation
  per the Merge Rule: both parents sit at Moderate, so the union of
  parent baselines is the Moderate baseline, inherited in full.
- **Feature → control family mapping (this build, at the Moderate
  baseline):**
  - Access control hooks (Core 9) → **AC** (AC-2 account management,
    AC-3 access enforcement, AC-6 least privilege), **IA** (IA-2
    identification & authentication — identity is supplied by the
    embedding organization via user/role headers; the service ships
    hooks, not an identity provider). On the 800-171 side: 3.1
    (access control) and 3.5 (identification and authentication) at
    the family level. Claim-supported in this group by
    LaunchDarkly's feature-level RBAC claim.
  - Audit log (Core 10) → **AU** (AU-2 event logging, AU-3 content
    of audit records, AU-6 audit review/analysis at the family
    level — the log is readable only under `audit_read`, admin
    only). On the 800-171 side: 3.3 (audit and accountability).
    **Precision note (the mirror of Group 17's):** CMMC L1 / FAR
    52.204-21 contains **no audit practice**, so at L1 the audit
    mapping held on the FedRAMP side only; **at L2 it holds on both
    sides**, because 800-171 carries an audit family (3.3).
    Claim-supported in this group by AutoRABIT's "immutable audit
    trails" claim.
  - Registry records, lifecycle transitions, configuration held as
    record, and checksum verification (Cores 1–8) → **SI** (SI-10
    information input validation — malformed input is rejected,
    never partially applied; SI-7 software and information
    integrity — SHA-256 verify-by-content is an integrity check,
    and SI-7 is a Moderate-baseline selection, citable at this
    tier), **CM** (CM-2 baseline configuration / CM-3 configuration
    change control at the family level — release records with
    per-project unique versions and build configuration held as
    record are configuration-controlled records; 800-171 3.4),
    and **SC** (SC-8 transmission confidentiality — the server runs
    over TLS when a certificate is configured; 800-171 3.13).
    Encryption at rest is a deployment-layer control, stated
    plainly, not claimed here. No sibling in this group claims an
    encryption function.
- **What this tier does not carry, and this build does not claim:**
  the High/L3-adjacent apparatus from the cross-tier builds
  (hash-chained tamper-evident audit, fail-closed audit writes,
  logon lockout, auditor role, 800-172 enhanced requirements) is
  out of scope for a Moderate merge and is **not inherited
  sideways**; the Low/L1 framing (FAR 52.204-21) is superseded by
  the 800-171 basis above, not carried upward.
- **Caveat (standing, from crosswalk.md):** FedRAMP authorizes
  **products**; CMMC certifies **organizations**. A FedRAMP impact
  level is a statement about a cloud service offering; a CMMC level
  is a statement about a company and how it handles FCI/CUI. The
  L2 / FedRAMP Moderate equivalence used here is a
  **planning/matching equivalence only**: it says these forks sit
  at comparable assurance weight so they can be grouped and merged
  consistently. It does **not** claim that a FedRAMP-authorized
  product confers CMMC certification on anyone, that a
  CMMC-certified organization holds a FedRAMP authorization, or
  that either regime accepts the other as evidence. This
  traceability is a planning mapping; the merged build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither credential is claimed.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**, package `devtools` under
`src/`, runnable and testable with `PYTHONPATH=src`. The contract is
Group 17's, unchanged — the implementation is **reused in full from
Group 17** (our own Apache-2.0 code), every module byte-identical:

| Module | SHA-256 (identical in both trees) |
|---|---|
| `devtools/__init__.py` | `b55a40a77630d2e1019fc51586e3ade5fc7a79b0d0ed740e58190c2403e3ff3c` |
| `devtools/__main__.py` | `9cf786b62f0ab5dda96b967b3e733167b8805ac7e12859a4e0970d1fffc2a092` |
| `devtools/access.py` | `9880ba510e8e07b52d10851ea320a71b19f4cb9efbd28e5d55bab2a1cb185aaf` |
| `devtools/audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `devtools/errors.py` | `b33b6959002a76cc15258f7c3760d4510e14addd05601ce8b949f7c1912f2947` |
| `devtools/service.py` | `7404a8edf1ed22ffea5fe363a7f2678cd0410436e6b7f113b0d5584a062b8021` |
| `devtools/store.py` | `36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0` |

- `devtools/errors.py` — `DevToolsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.
- `devtools/access.py` — `User(name, role)`; roles
  `admin|developer|viewer`; `PERMISSIONS`: admin ⊇ {write, verify,
  audit_read, admin}, developer = {write, verify}, viewer = {} (read
  and search only); `require(user, action)` raises
  `PermissionDenied`.
- `devtools/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)`; `.entries()` returns entry dicts
  with keys `ts, actor, action, target, details`. Append-only;
  optional JSONL file.
- `devtools/store.py` — `DevToolsStore(audit=None)` holding the
  eight record sets; sequential prefixed ids `"prj-1"`, `"iss-1"`,
  `"rev-1"`, `"bld-1"`, `"rel-1"`, `"art-1"`, `"env-1"`, `"dep-1"`,
  … per set. Issues carry the lifecycle `open → in_progress →
  resolved → closed` with reopen paths back to `open`; reviews
  carry `open → {approved, changes_requested, closed}`,
  `changes_requested → {open, closed}`, `approved → {merged,
  closed}`, `merged`/`closed` terminal; releases enforce
  per-project unique `version`; artifacts carry a SHA-256 checksum
  with verify-by-content; deployments bind `project +
  release/artifact → environment`. Malformed input raises
  `ValidationError` and changes nothing.
- `devtools/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (role must match the
  registry). Endpoints: `GET /health`, `GET|POST /projects`,
  `GET /projects/{id}`, `GET|POST /issues`,
  `POST /issues/{id}/status`, `GET|POST /reviews`,
  `POST /reviews/{id}/state`, `GET|POST /builds`,
  `GET|POST /releases`, `GET|POST /artifacts`,
  `POST /artifacts/{id}/verify`, `GET|POST /environments`,
  `GET|POST /deployments`, `GET /search`, `GET /audit`. Errors are
  JSON `{error}` with 400/401/403/404 as applicable. Denied
  attempts are audited.
- `devtools/__main__.py` — `python -m devtools serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=developer, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to. **66 tests** — Group 17's suite copied byte-identical and run
against this tree (66, OK). The negative control is Group 17's
two-family control (lifecycle gate + checksum integrity), and the
lifecycle-gate mutant was **mutation-verified fresh in this tree**:
patching `set_issue_status` to accept any transition made the
suite fail (66 ran, **8 failed** — the same failing set as Group
17's drill); `store.py` was restored and SHA-256-verified against
`scratch/store.py.pristine` and `scratch/store.py.sha256`, and the
suite returned to green. Drill record: `tests/README.md` and
`scratch/mutation-run.txt`.

## Coverage statement (for this build)

- Specs: **2 / 2** forks spec'd (Moderate 2; both FedRAMP
  Certified; each fork's impact level recorded in its spec sheet),
  reconciled zero-diff against `forks.json` and `MAP.md`.
- Claims: **4 total**, every claim carrying its source sentence as
  evidence; per-fork counts AutoRABIT 2, LaunchDarkly 2;
  **zero-claim forks: none**.
- Taxonomy: **17 function families**, Group 17's verbatim; 4 claimed
  by at least one sibling, 13 at **0/2** and recorded as named
  absences, carried substrate, or carried Extended gaps rather than
  dropped silently (project/repository collaboration, issue
  tracking, code review, deployment & release, configuration as
  code, artifact registry, landing zones, compliance/KSI, visual
  modeling, business automation, content authoring, hosted
  platform, search).
- Artifact corrections: **17 false hits removed by tightening, 1
  tightened hit removed as a correction, 0 true hits recovered**
  (22 broad first-pass hits → 4 final claims), itemized in
  `scratch/ARTIFACTS.md`, plus 10 recorded near-misses where the
  prose approaches a family the verbatim phrasing does not tag —
  including both products' dominant functions, which sit outside
  the taxonomy entirely.
- Core implemented: **10 / 10 functions**, exactly the list above
  (3 claim-supported in this group — build-record slice of
  ci_pipeline, RBAC, audit; 7 carried substrate/baseline items,
  flagged as such), via full byte-identical reuse of Group 17's
  implementation (SHA-256 table above).
- Extended: **15 named gaps**, specified and ranked, **not**
  implemented in this build — the 9 carried from the Group 17
  union and 6 new in this group (feature-flag & feature-management
  runtime, experimentation engine, static code analysis engine,
  security posture monitoring & automated remediation engine,
  release automation / environment management & data migration
  engine, external-system integration engines) — named here rather
  than implied done, for registration in GAPS.md and the final
  batch.
