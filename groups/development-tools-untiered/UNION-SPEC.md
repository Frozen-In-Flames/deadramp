# Union Spec — Development Tools, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Development Tools:
**7 forks**, category **Development Tools**, **tier null**. Every
member's FedRAMP impact level is **Unknown** in the source dataset —
the source publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts **no
control baseline**. Per PIPELINE.md, untiered offerings "build to
their documented control claims; tier stays null in the registry
until the source publishes a baseline." The Documented control
claims section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly census unit `untiered:Development Tools` in
`../../remainder.json` (7 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: 2 forks carry the
Development Tools category (KineticCode, Moderniza), 2 are filed
under Artificial Intelligence (AI) (Cursor, Replit for Government),
2 are filed "Uncategorized (none in source)" (Harness for
Government, Elixium), and 1 is filed under Operations Management
(Linear); the census assigned all 7 to this category from their own
descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span Initial Implementation (5),
FedRAMP In Process (1), and FedRAMP Certified (1 — Harness, whose
record pairs a Certified status with an Unknown impact level; both
strings are recorded as-is) — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 7
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 7 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (7/7).

## How functions were counted

The category's fixed 17-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../development-tools-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 17 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 2 of 2 forks, 4 of 4 claims, deep-equal** against the
sheets at the original ship commit (`a72b99a`, before the remainder
additions were appended), using the parent's sentence split and
evidence rule (first matching sentence; over 400 characters,
truncated to 397 + '...') and applying the parent's one recorded
CORRECTIONS entry on the proof path (AutoRABIT's `code_review`
removal — without it the recomputation carries one extra claim, so
the correction is load-bearing for the proof, exactly as shipped).

The category's recorded judgment was applied as recorded: there is
**no records-configuration family** in the shipped taxonomy, so
governance/configuration prose that matches no family is a named
gap, never a claim (KineticCode's gating and promotion
configuration, §Gaps); lifecycle claims fire only on a family's
matching text, not on adjacent platform prose (Replit's and
KineticCode's deploy/promotion prose tags nothing — see
`scratch/ARTIFACTS.md`). An exclusion pass scanned every raw hit's
evidence sentence for third-party hosted-app catalogue segments and
scope-exclusion sentences: **no hits were removed** — no description
in this set contains a third-party catalogue segment (only
`service_desc` was ever matched; the records' `certified_services`
fields, non-empty for 6 of the 7 forks, were never consulted), and
the set's one scope-exclusion passage — Cursor's Origin prose,
placing its Git hosting product outside the offering — carries no
raw hit, a fact the extractor asserts programmatically and
`tests/test_specs.py` pins. Wording artifacts in claims that stand
are itemized in `scratch/ARTIFACTS.md` (two `landing_zones` hits at
artifact weight on the word "multi-tenant"; one
`deployment_release` hit at product-noun weight; one first-hit
`audit_logging` evidence resting on "auditable" with the substantive
audit-trail sentence recorded).

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**14 claims** across the set; **6 of 7 forks carry at least one
claim**. The one zero-claim fork is recorded under Named absences,
not hidden.

Census citations: 8 citations are recorded for these forks in the
census; **8 of 8 verify** as verbatim substrings of the forks' own
descriptions (whitespace-normalized), and **4 of 8** are themselves
a claim evidence sentence. Verification is not a claim, in either
direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 7 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 7) | Disposition in this build |
|---|---|---:|---|
| 1 | Code review & discussion | 2 | **Core** — Core 3, review records (records only — no merge engine, no AI review) |
| 1 | Deployment environments, landing zones & tenants | 2 | **Core slice** — Core 7, environment & deployment records; both hits are the word "multi-tenant" at **artifact weight** (see below); provisioning is Extended |
| 1 | Hosted platform & managed operations | 2 | Platform note — not a development function; the merged build is a single-tenant reference deployment (provisioning/operations: Extended) |
| 1 | Audit logging | 2 | **Core** — Core 10, append-only audit log |
| 5 | Project/repository registry & code collaboration | 1 | **Core** — Core 1, project registry |
| 5 | Issue & work-item tracking | 1 | **Core** — Core 2, issue records with the lifecycle gate |
| 5 | CI build/test pipeline automation | 1 | **Core slice**: build records (Core 4). Execution: Extended — "CI/CD execution engines" |
| 5 | Deployment & release | 1 | **Core records** — release records (Core 5) and deployment records (Core 7); the one hit is at **product-noun weight** ("delivery platform"); execution is Extended |
| 5 | API & integrations | 1 | Extended — "External-system integration engines" (the build's own REST surface is its implementation contract, not a sibling claim) |
| 5 | Access control | 1 | **Core** — Core 9, RBAC |
| 11 | Configuration as code | 0 | Extended — "Configuration-as-code execution & orchestration" — **zero claimants in this set; named absence** |
| 11 | Artifact/package registry | 0 | **Core** — Core 6 (records + checksums; 0 descriptive claims in this set — carried, flagged in the Core note; binary storage Extended) — **zero claimants; named absence** |
| 11 | Compliance assessment & KSI status reporting | 0 | Extended — "Compliance assessment & KSI status automation engines" — **zero claimants; named absence** (Cursor's independent-assessment prose requires "automated assessment" and tags nothing) |
| 11 | Visual modeling & design | 0 | Extended — "Business modeling & automation engines (modeling + execution)" — **zero claimants; named absence** |
| 11 | Workflow & business automation | 0 | Extended — "Business modeling & automation engines (modeling + execution)" — **zero claimants; named absence** (agent-workflow prose in Linear, Elixium, and Replit matches no family phrase) |
| 11 | Content & course authoring | 0 | Extended — "Course & content authoring tools" — **zero claimants; named absence** |
| 11 | Search | 0 | **Core** — Core 8 (0 descriptive claims at every tier so far; substrate operation over the build's own registry metadata, flagged) — **zero claimants; named absence** |

**Differences are preserved, not averaged away**: no two forks in
this set claim the same *substantive* profile. KineticCode is a
CI/CD governance wrapper whose five claims ride on its governance
sentences while its CI/CD substance tags nothing; Harness is the
category's canonical CI/CD platform and tags the pipeline family
directly; Linear is an issue-tracking product that tags its own
family outright; Cursor and Replit are AI development platforms
whose AI engines match no family in a taxonomy written before them;
Moderniza is a conversion pipeline whose only tag is its audit
ledger; Elixium tags nothing at all. The union is held together by
the records substrate, not by overlapping claims, and the per-fork
spec sheets name which fork claims what.

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — project &
repository registry; issue & work-item tracking; code-review
records; build records; release records; artifact registry with
checksums; environment & deployment records; search; RBAC; and the
append-only audit log — including its self-contained **lifecycle
gate** (the issue lifecycle `open → {in_progress, closed}`,
`in_progress → {resolved, open}`, `resolved → {closed, open}`,
`closed → {open}`, with every other transition rejected and state
unchanged, and the review state machine beside it). The substrate
is records machinery that every sibling's output presupposes, and
it is tier-independent code: the founding source contains no tier
or baseline machinery, so there was nothing tier-shaped to strip.
Functions are **carried** as substrate; claim support in this set
is stated per function below, and no function is claimed to be
*attained* by any fork — the build is the merged open
implementation, not any fork's product. No function was added to
or removed from the Core for this set: nothing the descriptions
claim beyond the substrate is a records function — the AI engines,
the hosted IDE workspaces, the conversion pipeline, and the
governance gating are execution engines, which this project's
discipline assigns to Extended at every tier.

Claim support in this set, per function:

1. **Project & repository registry (records)** — *supported:*
   `project_collaboration` 1/7 (Replit's "real-time
   collaboration"). The registry is the record form the lifecycle
   functions all presuppose.
2. **Issue & work-item tracking with lifecycle** — *supported:*
   `issue_tracking` 1/7 (Linear's "provides issue tracking"). The
   lifecycle gate is the build's signature invariant,
   mutation-verified in this tree (see `tests/README.md`).
3. **Code-review records (records only — no merge engine)** —
   *supported:* `code_review` 2/7 (Cursor, at list weight — one
   verb in its opening sentence; KineticCode, its automated
   pull-request review step). No review is performed by this
   build; outcomes are recorded.
4. **Build records (records of build runs with status — no
   execution)** — *supported (slice):* `ci_pipeline` 1/7
   (Harness's spelled-out "continuous integration"). Execution is
   Extended; compilers and toolchains are Extended.
5. **Release records (versioned, per-project unique version)** —
   *supported at product-noun weight:* `deployment_release` 1/7
   (Harness, on the phrase "delivery platform"). KineticCode's
   controlled-promotion prose and Replit's deploy prose are
   recorded near-misses, not rounded up.
6. **Artifact registry with checksums (SHA-256 records;
   verify-by-content; binary storage is NOT in the build)** —
   *carried:* `artifact_registry` 0/7 in this set. KineticCode's
   "build checksums generated and re-verified at each environment
   promotion" is the closest prose in the set and matches no family
   phrase; it is recorded as a near-miss.
7. **Environment & deployment records** — *carried:* the family's
   2 hits in this set (`landing_zones`, KineticCode and Linear)
   are both the word "multi-tenant" at artifact weight — tenancy
   prose, not environment prose — so this function stands on the
   substrate decision alone here. Provisioning the environments
   themselves is Extended.
8. **Search over registry metadata** — *carried:*
   `search` 0/7, as at both founding tiers. Search here is a
   substrate operation over the build's own records, not a
   sibling's search engine; no sibling claims one.
9. **RBAC (roles admin/developer/viewer; alice/bob/carol demo
   identities as hooks)** — *supported:* `access_control` 1/7
   (KineticCode's "business-unit and role-based views," with
   access-policy violation flagging). The demo identities are
   hooks, not an IdP.
10. **Append-only audit log** — *supported:* `audit_logging` 2/7
    (KineticCode — "auditable controls" at first hit, with a
    "persistent audit trail of scans, approvals, merges and
    promotions" stated outright later in the description;
    Moderniza — "Every step leaves a ledger the customer can
    audit"). Every mutation and denied attempt is recorded with
    actor, action, target, and UTC timestamp.

The carried code is **byte-identical** to the founding group's
`src/devtools/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`) — and, through the founding group, to
Group 17's original implementation: the substrate has now been
carried unchanged across three builds (L1, L2, untiered). The
implementation contract is the founding spec's contract, unchanged:
Python 3, standard library only, package `devtools` under `src/`,
ids sequential per object type (`prj-`, `iss-`, `rev-`, `bld-`,
`rel-`, `art-`, `env-`, `dep-`), failed operations consume no id and
change nothing, permission checked before any state change or id
allocation, all timestamps UTC ISO-8601, roles
`admin|developer|viewer` with the founding permission matrix, and
the audit log append-only with denied attempts recorded. Where the
founding contract's text ties RBAC and audit to a tier baseline,
read it here as **baseline-neutral hooks**: at tier null they are
substrate, claimed against no baseline.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 7 offerings (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words — first under the taxonomy
families that carry control language, then at prose weight where a
description asserts control substance no family phrase captures. A
documented control claim is a **fork's claim about itself**,
recorded here with its evidence; it is not the build's control
attainment, and nothing in this section fills a family in from any
baseline.

Control areas **documented** by at least one fork in the set, via a
taxonomy family:

- **Access control (AC)** — via `access_control`, **1 fork**:
  KineticCode (FR2701557054 — "business-unit and role-based views,
  with detection and flagging of access-policy violations for human
  remediation"). Role-based access governance over its own
  platform, in the fork's own words.
- **Audit & accountability (AU)** — via `audit_logging`, **2
  forks**: KineticCode (FR2701557054 — "auditable controls" at
  first hit; "persistent audit trail of scans, approvals, merges
  and promotions" stated outright) and Moderniza (FR2701557044 —
  "Every step leaves a ledger the customer can audit").

Control areas **documented at prose weight** — asserted in a fork's
own sentences, captured by no family phrase, recorded as prose and
not as claims:

- **Configuration management / change control (CM)** — KineticCode
  (FR2701557054): "build checksums generated and re-verified at
  each environment promotion" and "strict sequential Dev, Test,
  Stage, Prod promotion with notifications on mismatch or stalled
  promotions" — promotion control over its own delivery pipeline.
- **System & information integrity (SI)** — KineticCode
  (FR2701557054): "detection of secrets, tokens and credentials in
  checked-in code, plus detection of risky code patterns" and
  "CUI/FCI marking assistance"; and Harness (FR2631258132):
  "security testing" in its stated capability list.
- **Assessment & authorization (CA)** — Cursor (FR2631054484):
  "Anysphere, Inc. is pursuing FedRAMP 20x Class C certification
  for the Cursor platform, and A-LIGN is performing the independent
  assessment. Certification has not yet been granted. Anysphere's
  FedRAMP 20x Class A application is under FedRAMP review." This
  documents an assessment *underway* for the fork itself — process
  prose about its own authorization pursuit, recorded with the
  fork's own "not yet been granted" — not an authorization, and
  not a control the fork operates for customers.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, CP, IR, MA, MP,
PE, PL, PM, PS, RA, SA, and SC — is asserted by no description in
the set. In particular: **identification & authentication (IA)** is
not documented — no description carries an SSO / identity-provider
/ authentication phrase (KineticCode's role-based language rides
with AC above; Replit's "in-browser and SSH access" is access
prose, not an authentication claim); and **cryptographic
protection (SC)** is not documented — no description asserts
encryption of its own data (KineticCode's checksums are integrity
records, not cryptography). If the source later publishes an impact
level for any of these offerings, the tier is recorded then and not
before.

## Named absences

- **Configuration as code — 0 of 7.** No description asserts
  configuration-as-code or infrastructure-as-code in matching text.
- **Artifact/package registry — 0 of 7.** The `artifact_registry`
  family has no claimant in this set (it had none at L2 either);
  the closest prose is KineticCode's build checksums, recorded as
  a near-miss in `scratch/ARTIFACTS.md`.
- **Compliance assessment & KSI status reporting — 0 of 7.**
  Cursor's independent-assessment prose requires the family's
  "automated assessment" phrase and tags nothing; it is recorded
  at prose weight in Documented control claims instead.
- **Visual modeling & design — 0 of 7; Workflow & business
  automation — 0 of 7; Content & course authoring — 0 of 7;
  Search — 0 of 7.** Agent-workflow prose (Linear's "agent
  workflows," Elixium's AI-agent proposals, Replit's AI agent)
  matches no automation family phrase; no description asserts a
  search function.
- **Zero-claim fork:** FR2701457600, Elixium — its work-tracking
  substance ("boards, stories, epics, decisions and test plans")
  matches no family phrase, and its second sentence is a customer
  support platform, which is fork excess for this category. The
  zero is recorded, not repaired; the taxonomy was not re-tuned
  for it.
- **Deployment & release substance without the phrase:**
  KineticCode's controlled promotion and Replit's "build, run and
  deploy software" / "deploy applications" are deployment prose
  that tags nothing (see `scratch/ARTIFACTS.md`); the family's only
  hit in the set is Harness's, at product-noun weight.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
the founding group's engine gaps restated where this set's forks
claim or approach them (counts are this set's), then the gaps new
in this set:

- [ ] CI/CD execution engines (pipeline execution — build/test/deploy runners) (1 claimant's engine: Harness; KineticCode's gating wraps such pipelines without being one)
- [ ] Code hosting internals (git storage, branching & merging engines) (0 claimants in this set; Cursor's excluded Origin product is the nearest subject, expressly out of its offering's scope)
- [ ] Compilers & build toolchains (0 claimants; build records presuppose one existed wherever a real build ran)
- [ ] Configuration-as-code execution & orchestration (0 claimants)
- [ ] Compliance assessment & KSI status automation engines (0 claimants)
- [ ] Business modeling & automation engines (modeling + execution) (0 claimants)
- [ ] Course & content authoring tools (0 claimants)
- [ ] Landing-zone / tenant provisioning & hosted platform operations (2 forks document multi-tenant hosted platforms; provisioning and operations are platform-layer, not implemented)
- [ ] Artifact binary storage backends (the registry holds records + checksums only) (0 claimants)
- [ ] Feature-flag & feature-management runtime (0 claimants in this set; carried so the category union is complete)
- [ ] Experimentation engine (0 claimants in this set; carried)
- [ ] Static code analysis engine (0 claimants in this set; KineticCode's risky-code-pattern detection is the nearest prose, recorded under the new detection gap below)
- [ ] Security posture monitoring & automated remediation engine (0 claimants in this set; carried)
- [ ] Release automation, environment management & data migration engine (approached by KineticCode's controlled promotion and Replit's deployments prose; no family claim at substance weight)
- [ ] External-system integration engines (1 claimant: Linear's public GraphQL API is its own surface; no connector executes anywhere in this build)
- [ ] **AI code-generation & AI-agent development engines** (new in this set — Cursor's AI-assisted development, Replit's AI agent and AI coding assistance, Elixium's agent drafting, Linear's agent workflows: the models and agent runtimes themselves; this build contains no inference of any kind)
- [ ] **Cloud development environments — hosted IDE workspaces** (new — Replit's Cloud Development Environment: isolated per-user workspaces, persistent filesystems, in-browser/SSH access)
- [ ] **Legacy modernization & code-conversion engines** (new — Moderniza's five-step conversion pipeline: Blueprint, Contract, Code, Testing, Deploy)
- [ ] **CI/CD governance & promotion-gating engines** (new — KineticCode's pull-request gating, coverage validation, controlled sequential promotion, and mismatch notification executed against live pipelines)
- [ ] **Secrets & sensitive-data detection engines** (new — KineticCode's detection of secrets, tokens, credentials, and CUI/FCI marking in checked-in code)
- [ ] **Pipeline governance configuration records** (new — the category's standing records-configuration gap: gating rules, approval requirements, coverage thresholds, and promotion policies held as configuration records; the shipped taxonomy has no family for this text, so it is a named gap and never a claim — KineticCode's prose is this set's instance)
- [ ] **Fork excess — customer support platform** (new — Elixium's in-app chat, support tickets, support email, and support phone line: a customer-service function inside a development-tools filing, named here so it is not silently dropped; it belongs to another category's union, not this one's)

**Platform-layer gaps (named, not implied closed):** encryption at
rest (deployment layer, not claimed here); TLS only when configured
(the server runs over TLS when a certificate is supplied; the
default serve mode is plain HTTP for local/demo use);
multi-tenancy (a deployment property — the merged build is a
single-tenant reference deployment; two forks document multi-tenant
platforms about themselves, which is their claim, not this build's
architecture); demo identities are hooks, not an IdP
(identification & authentication stays with the embedding
organization, which supplies production identity, authentication
strength, and account lifecycle).

## Coverage statement (for this build)

7 forks spec'd of 7 in census unit `untiered:Development Tools`;
14 taxonomy claims tagged from the forks' own descriptions (6 of 7
forks claiming at least one); the ten-function substrate carried
byte-identical from the founding Development Tools build (through
it, from Group 17's original) and re-anchored to tier null; tier
null recorded on every sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or a
control baseline for any fork or for the build itself.
