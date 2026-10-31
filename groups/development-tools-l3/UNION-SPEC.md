# Union Spec — Development Tools, CMMC L3-adjacent (DeadRamp Phase 2, remainder singleton)

The singleton spec for the Development Tools category at the
L3-adjacent tier: **1 fork, FedRAMP High** — Red Hat OpenShift
Service on AWS (ROSA) (Red Hat). Reconciled against the remainder
census (`../../remainder.json`, unit
`new-singleton:Development Tools|L3-adjacent`, fork_ids exactly
[FR2102031769]) and against the source record: the fork sits in
`forks.json` as category "Uncategorized (none in source)" with
cmmc_tier="L3-adjacent"; the census classified it into Development
Tools from its own description ("Turnkey application platform for
building/deploying containerized apps." — classifier note on
record in the census), and this build follows the census. The
record itself: service model PaaS, deployment model Government
Community Cloud, impact level High, status FedRAMP Certified,
`business_categories` and `certified_services` both empty.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Development Tools L2 merged build**
   (`../development-tools-l2/`) — the union of the category's
   Moderate forks, shipped as a working clean-room development
   tools records service (10 core functions), itself the Group 17
   (Development Tools L1) build carried up byte-identical.
2. This singleton's **1 High fork**, via the spec sheet in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run by
the builder, and both negative-control drills were
mutation-verified by patching the implementation (see
tests/README.md).

**Reuse, stated explicitly:** this build reuses the L2 group's own
open-source code (Apache-2.0, ours). One module is byte-identical
to the L2 parent (`__init__.py`); six are modified for the tier
uplift (`errors.py` — AuditWriteError added; `access.py` — auditor
role added; `audit.py` — hash chain, fail-closed writes, and query
added, following the proven `groups/crm-l3` mechanics;
`store.py` — snapshot fail-closed wrapper added, following the
same precedent; `service.py` — lockout, audit verify/query,
auditor user added; `__main__.py` — auditor user and lockout flags
added). No core function changed behavior: every L2 test passes
with only the documented uplift adaptations (tests/README.md).

## How functions were counted — 1 claim, honestly

The category's 17-family taxonomy was applied **verbatim** (same
ids, labels, and matching patterns, AST-parsed out of the L2
group's original `scratch/extract.py` — parsed, never executed,
never re-typed — in this group's `scratch/extract.py`), including
its one recorded correction. Before the newcomer was tagged, the
extractor **reproduced all six shipped L2 claim sheets exactly**
(function ids and evidence sentences, deep-equal): the taxonomy
that produced the parent union is provably the taxonomy applied
here. A family is claimed only when the offering's own description
contains matching text; the first matching sentence is stored in
`specs/specs.json` as evidence.

**Result: 1 claim.**

- **hosted_platform** — "This offering is a FedRAMP High baseline,
  Platform-as-a-Service (PaaS) cloud service for developing and
  running containerized applications offered on the FedRAMP
  authorized AWS GovCloud (US)."

Calibration arithmetic (full log in `scratch/ARTIFACTS.md`):
**8 broad hits → 1 tightened hit → 1 final claim**; 0 corrections
(the taxonomy's single recorded correction names an L2 fork, not
this one); 0 recovered. The seven removed broad hits are the
taxonomy's documented tightening classes doing their work: bare
build/deploy/delivery vocabulary (ci_pipeline,
deployment_release), "Environment" inside the product name
"Integrated Development Environment" (landing_zones), bare
"authorized" as FedRAMP posture in "FedRAMP authorized AWS
GovCloud" (compliance_ksi, access_control), the category noun
"development/developing" plus the `author` substring in
"authorized" (content_authoring), and "fully integrated" as an
adjective (api_integrations).

**Verification ≠ claim, in both directions, pinned:** the census's
one citation for this fork — sentence 2, "It runs natively on
Amazon Web Services (AWS), and allows organizations to increase
operational efficiency, refocus on innovation, and quickly build,
deploy, and scale applications." — **verifies verbatim** against
the cached description and **tags no family**; the single claim
rests on sentence 5, which the census did not cite. Both facts are
pinned by tests (`tests/test_singleton_spec.py`).

**Exclusion accounting:** the record's `certified_services` is
empty (asserted in the extractor before tagging), so nothing is
excluded as a third-party catalogue; the description's feature
enumeration (Kubernetes, an Integrated Development Environment,
build pipelines, monitoring, logging, networking) names the
offering's **own** components, in scope by the taxonomy's ordinary
reading. No text was removed before matching: **matched text is
the full text**, and expected raw hits equal claims (1 = 1).

Near-misses, recorded in full in `scratch/ARTIFACTS.md`, not
rounded up: "build pipelines" is not the CI family's operative
phrases (ci_pipeline, 0 here); "quickly build, deploy, and scale
applications" fires no deployment pattern (deployment_release, 0);
"containerized applications" are workloads, not a container
registry (artifact_registry, 0); "monitoring, logging" meets an
audit pattern that is the word "audit" only (audit_logging, 0);
"not managing infrastructure" lacks "infrastructure as code"
(config_as_code, 0); the turnkey / jointly managed prose of
sentences 1 and 4 asserts the hosting substance without any of the
family's phrases — the family is claimed on sentence 5's PaaS
phrasing alone. Kubernetes container orchestration matches **no
family in the 17** and becomes a named gap below, not a re-tuned
pattern.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Hosted platform & managed operations | **Claimed here** — Platform note (the L2 union's own disposition): the claim describes the fork's delivery model; the platform itself is the deployment layer, not a core function of this build |
| 1 | 0 | Project collaboration & shared development | **Core** (records) — carried from the L2 union (claimed at L1 there); carried, not claimed here |
| 1 | 0 | Issue & bug tracking | **Core** (records) — carried from the L2 union; carried, not claimed here |
| 1 | 0 | Code review & discussion | **Core** (records) — carried from the L2 union (its only L2 hit was removed there by the recorded correction); carried, not claimed here |
| 1 | 0 | CI / build pipeline | **Core** (records) — carried from the L2 union (claimed 3 of 6 there); this fork's "build pipelines" is a near-miss (above), and pipeline *execution* is Extended |
| 1 | 0 | Deployment & release | **Core** (records) — carried from the L2 union; carried, not claimed here |
| 1 | 0 | Configuration & infrastructure as code | Extended — execution engines (registered under the L2 union, not re-registered); the fork's infrastructure wording is posture, not config-as-code |
| 1 | 0 | Artifact & package registry | **Core** (records) — carried substrate; this fork's "containerized applications" is a near-miss, not a registry |
| 1 | 0 | Landing zones & tenancy | **Core**-adjacent (environment records) — carried from the L2 union (claimed there by the DevSecOps platform fork); carried, not claimed here |
| 1 | 0 | Compliance automation & KSI | Extended — automation engines (registered under the L2 union); not claimed here |
| 1 | 0 | Visual modeling & low-code design | Extended — modeling engines (claimed at L2 by the low-code fork; engine not built); not claimed here |
| 1 | 0 | Business automation & workflow | Extended — automation engines (registered under the L2 union); not claimed here |
| 1 | 0 | Content authoring | Extended — authoring tools (registered under the L2 union); the fork's IDE is a developer workspace (gap below), not course/content authoring |
| 1 | 0 | API & integrations | Extended — connector/integration engines (claimed at L2 by 2 forks; engines not built); "fully integrated" here is an adjective, not an integration |
| 1 | 0 | Access control & identity | **Core** (baseline substrate, uplifted to High) — carried from the L2 union (claimed there by the feature-flag fork); carried, not claimed here |
| 1 | 0 | Audit logging | **Core** (baseline substrate, uplifted to High) — carried from the L2 union (claimed there by the DevSecOps tooling fork); the fork's "monitoring, logging" is platform observability (gap below), not this family's audit trail |
| 1 | 0 | Search | **Core** (registry mechanics) — carried, not claimed here |

Plus this singleton's own platform surface, named from its prose
(all Extended, detailed in Gaps below): container orchestration
(Kubernetes); an integrated development environment / developer
workspace; build-pipeline execution; platform monitoring & logging
(observability); platform networking; and 24/7 managed platform
operations — the last already registered under the L2 union's
hosted-platform-operations gap and **not re-registered** here, per
the Gap-batch Rule.

**Named absences for this fork** (token-checked against its
description, asserted in no form — not substance-without-phrase,
simply absent): issue/bug tracking vocabulary, code review,
search, source-code hosting. The substrate carries the records
functions anyway (core-boundary decision below); the fork's prose
never reaches them.

**Core-boundary decision (recorded once, per the Merge Rule and
the sibling L3 precedent).** This fork tags exactly one claim, and
that claim (hosted_platform) is a platform note in this category,
not a core function — so **no core function is claim-supported by
this fork**, and all 10 core functions stand in this build as
carried substrate. The reasoning is the Merge Rule itself, not
convenience: a cross-tier merge takes the union of the parents
upward whole, and the L2 union — the category substrate this
fork's category presupposes — is a parent of this build. A short
platform description (five sentences, most of its substance in
phrases the taxonomy deliberately does not fire on) is not a
downgrade, and stripping the substrate at High because the High
fork's prose is thinner than the Moderate forks' would dilute the
union, which Rule 1 prohibits. Every core function is therefore
flagged **carried, not claimed** for this tier. Where the fork
claims less than the substrate — which here is everywhere — that
is this paragraph, stated once and plainly, rather than ten quiet
exceptions.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 functions as the L2 build, carried up whole:

1. **Project & repository records** — projects (`prj-`): name,
   optional description and repository URL, created-by/at
   provenance. Records only — no code is hosted or served.
   Carried, not claimed.
2. **Issue tracking** — issues (`iss-`) under a project: title,
   description, kind, priority, status, and a guarded lifecycle
   `open → in_progress → resolved → closed` (with reopen paths;
   the transition table is enforced, illegal transitions rejected
   with state unchanged — the group's signature guard, drilled).
   Carried, not claimed.
3. **Code-review records** — reviews (`rev-`): title, optional
   source reference, reviewer, and state
   `open → approved / changes_requested → merged / closed`.
   Records only — no merge engine exists. Carried, not claimed.
4. **Build records** — builds (`bld-`): project, ref, status
   (queued/running/succeeded/failed), free-form config stored
   verbatim and never executed. Records only — no build runs.
   Carried, not claimed.
5. **Release records** — releases (`rel-`): project, version
   (unique per project), notes, optional build link. Carried,
   not claimed.
6. **Artifact registry** — artifacts (`art-`): name, version, and
   a SHA-256 checksum computed from supplied content or supplied
   directly (the two must agree); content itself is never stored,
   and `verify_artifact` checks candidate content against the
   stored checksum. Binary storage backends are Extended.
   Carried, not claimed.
7. **Environment & deployment records** — environments (`env-`)
   and deployments (`dep-`) linking environment + project with
   optional release/artifact references and a status
   (deployed/failed/rolled_back). Referenced records must exist.
   Carried, not claimed.
8. **Search** — literal case-insensitive substring search over
   project names, issue titles, review titles, release versions,
   and artifact names. Carried, not claimed.
9. **Access control (RBAC)** — admin/developer/viewer matrix over
   16 actions **plus the auditor role** [L3]; enforced in the
   store before any mutation or id allocation, and again at the
   service layer. Carried substrate, uplifted to High.
10. **Audit log** — append-only, **hash-chained**,
    **fail-closed**, **queryable** [L3], JSONL-persistable;
    records every successful mutation and every denied attempt
    (`<action>:denied`), with actor, action, target, and UTC
    timestamp. Carried substrate, uplifted to High.

**Privacy discipline (hard rule, inherited).** Records hold
project, work-item, and registry metadata only — names of
projects and issues as the caller supplies them, opaque ids, and
free-form text the caller puts in descriptions and notes. No
entity shape carries a personal-identifier field class (no email,
phone, SSN, date-of-birth, or address fields exist in any record),
no artifact content is stored (checksums only), and no score is
computed anywhere: the build has no scoring field, aggregate, or
ranking function.

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices
  of NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. The cross-tier parent (the L2 build) sat
  at Moderate; the union baseline is therefore the High baseline,
  un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3
  is not identical to FedRAMP High; it is the same assurance
  weight class.
- **Feature → control family mapping (carried from the L2 union):**

  | Core function | Control families | How the build answers |
  |---|---|---|
  | Project registry | AC-3, AC-6, IA-2 (hooks) | Provenance-stamped records; writes gated by role before allocation |
  | Issue tracking & lifecycle | AU-2, CM-6, SI-10 | Guarded transition table under a configured lifecycle; every transition audited |
  | Review records | AU-2, CM-6 | State machine records; no merge execution exists to govern |
  | Build records | CM-6, SI-10 | Config stored verbatim, never executed; statuses validated |
  | Release records | CM-6, AU-2 | Per-project version uniqueness enforced in the store |
  | Artifact registry | SI-12, SC-12 (partial) | SHA-256 checksums with verify-by-content; content never stored |
  | Environments & deployments | CM-6, AU-2 | Referential integrity enforced; every deployment audited |
  | Search | AU-6, SI-12 (partial) | Literal search over registry metadata supports review |
  | RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Four-role matrix enforced pre-mutation at two layers; auditor role separates audit review (AC-5) |
  | Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only, hash-chained, fail-closed, queryable log including denied attempts; no mutation API |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service answers 500 `{"error": "audit write failed"}` — an operation whose audit write fails does not proceed. (`search` carries no wrapper: in this package it records no audit entry on success, so there is no write to fail closed on; denied searches are audited by the enforcement path, which propagates the same error.) |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as the L2 build, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here. The fork's own platform properties — its FedRAMP High baseline posture on AWS GovCloud, jointly managed by Red Hat and AWS — are properties of the fork's deployment and **do not transfer** to this build |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only: **FedRAMP authorizes
  products; CMMC certifies organizations** — the build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither regime accepts the other as evidence. Any real compliance
  claim still has to be earned inside each regime separately.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (1 tagged claim; full description
  preserved; near-misses itemized in `scratch/ARTIFACTS.md`;
  census citation verified verbatim and pinned as tagging no
  family; taxonomy-verbatim proof: all 6 shipped L2 sheets
  reproduced exactly by this group's extractor).
- Core implemented: **10 / 10** functions above, at the High
  baseline; 6 tier uplifts implemented (hash-chained audit,
  fail-closed audit writes with store rollback, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor role).
- Tests: **122** (72 in the inherited L2 files — the L2 suite's 66
  plus 6 added inside inherited files for the uplifts — and 50 in
  five new files); three negative controls in the suite
  (lifecycle gate, checksum integrity, audit tamper), and two
  mutation drills performed live in this tree — the lifecycle-gate
  drill failed exactly 8 tests, the audit-hash drill exactly 5 —
  with the files restored SHA-256-identical (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own platform surface (Extended; named from its
prose — the platform's actual product surface, none of it built
here). New registrations only; functions already registered under
the L2 union are referenced, not re-registered:

- **Container orchestration platform (Kubernetes)** — the
  description names Kubernetes as a fully integrated component;
  no family in the category's 17 covers container orchestration.
  NEW.
- **Integrated development environment / developer workspace** —
  the description names an IDE among its integrated features; a
  developer workspace is not the taxonomy's content-authoring
  family. NEW.
- **Platform monitoring & logging (observability)** — the
  description asserts monitoring and logging of the platform
  itself, with 24/7 monitoring and management; platform
  observability is not the audit family's audit trail. NEW.
- **Platform networking** — networking named among the integrated
  platform features; no substrate function answers it. NEW.

Registered under the parent and **not** re-registered here (this
fork's instances of already-registered families): build-pipeline
execution (the L2 union's CI/CD execution engines gap — this
fork's "build pipelines" are an instance); 24/7 managed platform
operations (the L2 union's hosted platform operations gap — this
fork's turnkey jointly managed operations are an instance, and its
`hosted_platform` claim is the platform note recorded above).

Extended families carried from the L2 union, not implemented and
not re-registered (registered once in `../development-tools-l2/
UNION-SPEC.md`): CI/CD execution engines; code hosting internals;
compilers & toolchains; config-as-code execution; compliance/KSI
automation engines; business modeling & automation engines;
course & content authoring tools; landing-zone/tenant provisioning
& hosted platform operations; artifact binary storage backends;
feature-flag runtime; experimentation engine; static code
analysis engine; security posture monitoring & automated
remediation; release automation / environment / data-migration
engine; external-system integration engines.

Baseline gaps at High (platform layer; gap-listed, never implied
closed): MFA / authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13); encryption at rest (SC-28);
audit retention enforcement (AU-11); session lock / termination
(AC-11/AC-12). Platform notes: multi-tenancy (single-tenant
reference deployment); TLS only when a certificate is configured;
demo identities are hooks, not an IdP (IA-2 stays with the
embedding organization).
