# Addendum — Development Tools, CMMC L2: the 4 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 4
previously uncategorized forks of remainder build unit
**`addition:development-tools-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 10-function
core, and its control baseline are **unchanged**. This document
records what joined, what the newcomers claim under the group's
existing taxonomy, the core-delta decision for every claimed
function, and the updated union statement.

**Headline: forks spec'd 4 / 4; 7 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 66 → 78, all
passing; 1 zero-claim fork** (Unqork, pinned in §2, not hidden).
**2 new gap functions** are named in §5, and 5 already-registered
gaps gain claimants.

## 1. Membership and method

The 4 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1607067912` | 18F - 18F Cloud.gov / CG-TTS - Cloud.Gov |
| 2 | `FR2200507410` | Copado / Copado GovCloud |
| 3 | `FR1912051231` | TechTrend, Inc. / Federal GovCloud (FGC) DevSecOps |
| 4 | `FR2125561001` | Unqork, Inc. / Unqork for Government |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the shipped
  `scratch/extract.py` with `ast` (parsed, never executed) and
  tags with those exact (id, label, regex) triples** — the
  taxonomy was applied verbatim, not re-tuned for the newcomers.
  Same sentence splitting, same evidence rule (first matching
  sentence per family, stored verbatim), same sheet schema. The
  4 sheets are **appended** to `specs/specs.json` after the
  original 2, which are byte-for-byte untouched (the appended
  file's byte prefix through the second sheet's closing brace is
  identical to the shipped file, and the original entries
  deep-compare equal to `git show HEAD:`; verified by
  `scratch/append_additions.py`).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 4
  descriptions were present; no live fetching. All 4 are FedRAMP
  **Moderate** and **FedRAMP Certified**, so the group stays
  single-tier and the L2 baseline is inherited in full (Merge
  Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **5
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **5 / 5 verify** as verbatim
  substrings. Verification is not a claim: 3 of the 5 citations
  (Copado's headline sentence, FGC's DevSecOps-practices sentence,
  Unqork's platform sentence) tag **no family** — recorded in §2.
- **No exclusion trap applies to the newcomers.** None of the 4
  records carries a hosted-services block: every record's
  `certified_services` field is empty (asserted in the
  extractor). Only `service_desc` was matched, per house method.
- **Wording-artifact corrections applied to the newcomers:
  none.** Every tightened hit stands; the one thin hit is
  recorded as a wording artifact in §2 rather than corrected.

## 2. What the additions claim

**7 claims** across the 4 forks; 3 of 4 carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 2 + additions = 6 forks) alongside:

| Function | Additions claiming | Group total (6) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| CI build/test pipeline automation | 2 | 3 | **Core slice** — build records (Core 4); execution Extended (gap 1) |
| Hosted platform & managed operations | 2 | 2 | Platform note — provisioning/operations Extended (gap 8) |
| API & integrations | 1 | 2 | Extended — gap 15 |
| Deployment environments, landing zones & tenants | 1 | 1 | **Core slice** — environment & deployment records (Core 7); provisioning Extended (gap 8) |
| Visual modeling & design | 1 | 1 | Extended — gap 6 |

Per-fork claim counts: Copado **3**, FGC DevSecOps **3**,
Cloud.gov **1**, Unqork **0**. The full per-fork table is pinned
literally in `tests/test_additions.py` (`EXPECTED_CLAIMS`).

### The zero-claim fork — pinned, not hidden

**Unqork for Government** (`FR2125561001`) carries **zero
claims**, for the same reason both original products' dominant
functions sit outside the taxonomy: its description phrases its
function in none of the 17 patterns, and the taxonomy was not
re-tuned to catch it. Its whole description is two sentences: a
"no-code, cloud-based development platform" that lets
organizations "rapidly build robust enterprise-grade software
without writing a single line of code", with "all the toolsets
and elements necessary to build and manage applications". The
lone verb "build" is not a CI pipeline claim (Group 17's
tightening principle, carried verbatim), and the platform's
visual builder is never called "visual" in the text, so
`visual_modeling` does not fire either. Its dominant function —
no-code application development — is fork excess and becomes a
new gap in §5.

Twelve families claim **no** addition and are pinned in the
tests rather than left implicit: project/repository
collaboration, issue tracking, code review, deployment &
release, configuration as code, artifact registry, compliance
assessment & KSI, business automation, content authoring, access
control, audit logging, search.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Cloud.gov** — "rapid, incremental, compliant, secure, and
  scalable delivery of government services" is broad
  delivery/security vocabulary: `deployment_release` requires a
  code-release phrase and `access_control` an RBAC/SSO phrase;
  neither fires. The `hosted_platform` evidence sentence itself
  carries "instant provisioning of services and environments"
  and "easy deployment of applications" — provisioning substance
  that is gap 8's remainder, not a deployment claim ("easy
  deployment of applications" is not "deploy process" or
  "delivery platform"). The closing sentence — "tools to quickly
  incorporate 800-53 NIST control documentation into
  easily-prepared and comprehensive System Security Plans (SSPs)
  … Authority To Operate (ATO)" — is compliance substance with
  **no family**: `compliance_ksi` requires a KSI /
  automated-assessment phrase, and "Authority To Operate" is not
  "authorized (users|personnel|agency)". The SSP tooling is fork
  excess → new gap 17.
- **Copado** — The census citation (its headline sentence, "a
  cloud DevOps platform designed to make Salesforce releases
  faster…") tags nothing: "make Salesforce releases faster" is
  not the family's code-release phrasing. The in-scope bullet
  "Deploying Salesforce metadata to production and sandbox
  instances, with Git integration for version control and branch
  management" and the second sentence's "seamlessly deploy from
  a QA environment to production" are deployment substance whose
  phrases do not fire (see the pin in the tests: the CI bullet
  reverses the family's "continuous integration and delivery"
  into "Continuous deployment and continuous integration");
  branch management is exercised through the Git integration the
  `api_integrations` claim covers. "- Change management
  including agile development processes, quality gates, and code
  scanning." is static-analysis substance with no family — the
  same family-less position as AutoRABIT's CodeScan — and gap 12
  gains Copado by substance. "Compliance rules for Salesforce
  metadata, including rule creation, monitoring, and enforcement
  of policies across user stories, Git snapshots, and
  deployments" is compliance/monitoring substance (no KSI
  phrase); its "user stories" are work-item substance without a
  tracking phrase. "Test data seeding across sandboxes" is
  test-data substance riding on the Salesforce release domain
  (gap 14's claimant note).
- **FGC DevSecOps** — "combines an array of tools, integrates
  them together under the FedRAMP umbrella" is not
  `api_integrations` (the pattern is "integrates **with**");
  the same sentence's "hosting, patching and help desk support"
  is managed-operations substance under the `hosted_platform`
  platform note. Its second census citation — "automate
  development, security, and operations (DevSecOps) practices
  through every phase of the software development life cycle" —
  tags nothing (the lone "automate" is not a business-automation
  phrase). The CI evidence sentence writes "continuous
  integration and continuous **deployment**" where
  `deployment_release`'s phrase is "continuous integration and
  **delivery**": no fire. The closing sentence's "integration
  testing" is not an integrations phrase, and its "secure
  operational monitoring" is operational-monitoring substance
  adjacent to gap 13's security-posture monitoring but not the
  same function — recorded here, not counted as a claimant.
- **Unqork** — both sentences; see the zero-claim entry above.

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the group's
law, applied verbatim:

- **Copado, `visual_modeling`** fires via the family's bare
  `visual` alternative, on "visual pipeline configuration" (the
  same sentence that carries its `ci_pipeline` claim). The
  substance is a graphical editor for pipeline configuration —
  thinner than the family's modeling-suite center of gravity,
  and the claim is kept at exactly that weight, per the Group 17
  precedent (Trisotech's bare-"visual" hit: "thin, but 'visual'
  is the suite's own word… Kept"). Its disposition is unaffected:
  the visual tooling is an engine, Extended either way (gap 6).

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| CI build/test pipeline automation (2: Copado, FGC) | Core 4 slice — build records; execution is gap 1 | **Carried** — no change |
| Deployment environments, landing zones & tenants (1: FGC) | Core 7 slice — environment & deployment records; provisioning is gap 8 | **Carried** — no change |
| API & integrations (1: Copado) | Extended — gap 15 (external-system integration engines) | **Gap** — existing gap gains a claimant |
| Visual modeling & design (1: Copado) | Extended — gap 6 (business modeling & automation engines) | **Gap** — existing gap gains its first claimant at this tier |
| Hosted platform & managed operations (2: Cloud.gov, FGC) | Platform note — not a development function; provisioning/operations are gap 8 | **Platform note** — gains 2 claimants; no key-management-style service added, no core change |

**Result: the core is unchanged.** No function the 4 claim
presupposes a records form the build lacks: the newcomers'
pipelines land in build records, their environments and landing
zones in environment/deployment records, and everything beyond
the records — pipeline execution, visual designers, integration
connectors, provisioning, hosting operations — was already
Extended or a platform note in the original union. `src/` is
byte-identical to the shipped build (`src/devtools/store.py`
SHA-256
`36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **6 forks** (2 original siblings + 4
remainder additions), **11 claims** in total (4 + 7), with **5
of 6** forks carrying at least one claim. The merged build
remains the same 10-function development-lifecycle records
substrate — project registry, issue lifecycle, review records,
build records, release records, artifact registry with
checksums, environment & deployment records, search, RBAC,
append-only audit — now spec'd against 6 marketplace offerings
instead of 2. The group's character broadens without changing
the substrate decision: the original pair were disjoint-claim
specialists (a Salesforce DevSecOps suite and a feature-flag
platform); the additions add a second Salesforce DevOps platform
(Copado — the group's claim gravity now sits on Salesforce
release tooling, with AutoRABIT), a government PaaS (Cloud.gov),
a managed DevSecOps suite (FGC), and a no-code platform (Unqork)
whose dominant function, like both originals', sits outside the
taxonomy and is named as a gap rather than forced into a family.

## 5. Gaps — for the registry at ship

**New gap functions** (2), continuing the union's numbering:

16. **No-code / low-code application development platform
    (visual application builder & runtime)** — Unqork. The
    fork's dominant function: building and managing
    enterprise applications without code. No taxonomy family;
    the Core holds the project/issue records an application
    effort presupposes, and no application is built or run
    anywhere in this build.
17. **Compliance documentation & SSP generation tooling** —
    Cloud.gov (incorporating 800-53 control documentation into
    System Security Plans for ATO evaluation). Distinct from
    gap 5 (compliance assessment & KSI status **automation**
    engines): this is documentation generation, not assessment
    or status automation.

**Existing gaps gaining claimants:**

- **CI/CD execution engines** (gap 1) — +2: Copado, FGC
  DevSecOps (the execution remainder of their `ci_pipeline`
  claims; the family's claimants at this tier are now 3 of 6).
- **Business modeling & automation engines** (gap 6) — +1:
  Copado (`visual_modeling`; the family's first claimant at
  this tier — its visual pipeline-configuration tooling).
- **Landing-zone / tenant provisioning & hosted platform
  operations** (gap 8) — +1 claim: FGC (`landing_zones`); +2
  platform claims: Cloud.gov, FGC (`hosted_platform`).
  Provisioning of services/environments and hosted operations
  are this gap's remainder for all three.
- **Static code analysis engine** (gap 12) — +1 **by
  substance**: Copado ("code scanning", "quality gates" in its
  change-management scope). Its family claim did not fire —
  the taxonomy has no analysis family — recorded here rather
  than rounded into a claim.
- **Release automation, environment management & data
  migration engine** (gap 14) — +1 **by substance**: Copado
  (Salesforce metadata deployment execution to production and
  sandbox instances, QA-to-production deployments, test data
  seeding). Its `deployment_release` family claim did not fire
  on phrasing (§2), recorded here rather than rounded up.
- **External-system integration engines** (gap 15) — +1:
  Copado (`api_integrations` claim — Git integrations). FGC's
  tool-integration substance ("integrates them together") is
  recorded as a near-miss in §2 and is **not** counted here.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim fork and zero-claim family sets,
  verbatim evidence, census-citation verification, the near-miss
  pins, and the Copado visual wording-artifact pin (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: environment + deployment records for provisioned
  platform environments (Cloud.gov); build, release, and
  QA-to-production deployment records with artifact
  verify-by-content (Copado); a landing-zone environment record
  with a deployment bound into it (FGC); project and issue
  records through the enforced lifecycle, including the
  lifecycle gate itself (Unqork).
- **Tests: 66 → 78, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the lifecycle gate in
  `DevToolsStore.set_issue_status` (`src/devtools/store.py`) —
  the `if status not in allowed:` check — was patched to accept
  any transition (`if False and status not in allowed:`) and the
  full suite ran — **78 tests, 9 failures**: the original
  drill's 8 (the illegal-transition subtests, the two
  negative-control canonicals, and the service validation case)
  plus 1 from the new additions module (the Unqork
  lifecycle-gate case), which trips on the mutant exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`, raw output in
  `scratch/additions_mutation_run.txt`.
