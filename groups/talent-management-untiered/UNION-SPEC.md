# Union Spec — Talent Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 21**: **2 forks**, category
**Talent Management**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes
no baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's union
spec carries.

Membership is exactly census unit `untiered:Talent Management` in
`../../remainder.json` (2 fork IDs, verified mechanically). Talent
Management here is the category founded by Remainder Group 3
(`../talent-management-l2/`): the candidate-facing pre-hire
acquisition surface. It is a **different category** from Talent
Development (Untiered Set 20, built separately), Learning
Management, and Human Resources; no taxonomy or code was borrowed
from any of them. In `forks.json` the set is mixed as filed:
CodeSignal is filed "Human Resources" (its source business
categories are Human Resources, Talent Management, Talent
Development, Education & Training, Artificial Intelligence (AI)),
and VOS Sapphire is filed "Uncategorized (none in source)" with
**no** source business categories at all; the census assigned both
to Talent Management from their own descriptions (CodeSignal:
"Pre-hire skills assessment and screening is the lead function";
VOS Sapphire: a workforce/employment-services platform for job
seekers and employers), and the spec sheets record the assignment
and the filed values as-is. Authorization status as recorded is
Initial Implementation for both — a status is record data, not a
claim.

| Fork | Vendor | Product | Status | Model |
|---|---|---|---|---|
| FR2635930425 | CodeSignal, Inc. | CodeSignal | Initial Implementation | SaaS |
| FR2631747327 | Geographic Solutions Inc. | VOS Sapphire | Initial Implementation | SaaS |

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`. Sources: GSA FedRAMP Marketplace dataset
(cached at `../../raw/data_dump.json`, produced by the General
Services Administration, last change 2026-10-22), product records
joined by FedRAMP ID. Both descriptions were present in the cached
dataset and match `../../remainder/uncovered.json` exactly (2/2);
neither contains a carriage return.

**The category boundary, carried from the founding spec.** Human
Resources is the *personnel system of record*; this category is
the other side of the hire — candidate-facing acquisition
products whose candidates are opaque references inside an
acquisition pipeline. The moment a hire becomes a personnel
action it belongs to Human Resources' substrate, not this one.
That boundary binds this set as it bound the founding group, with
one recorded strain: VOS Sapphire's description is a **public
workforce-services** platform (labor exchange, case management,
employer services, unemployment insurance) — its "candidates" are
job seekers in a public employment system, not applicants in an
agency's hiring pipeline. The census assigned it here; the build
carries the category substrate whole and registers VOS's actual
functions as gaps (below), rather than pretending the substrate
is its product.

## How functions were counted

The category's fixed 12-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../talent-management-l2/scratch/extract.py`, parsed, never
executed), asserts the same 12 families in the same order, and
applies the founding group's unit splitting (paragraphs → lines →
sentences → numbered clauses) and evidence rule (first matching
unit, stored verbatim; case-sensitive patterns, exactly as the
founding extractor compiles them; no truncation; no
carriage-return normalization — the founding extractor uses
neither, and both descriptions here are carriage-return-free,
asserted by the extractor). Taxonomy-verbatim proof: before
tagging this set, the extractor reproduced the founding group's
**original shipped claim tables exactly — 2 of 2 forks, 14 of 14
claims, deep-equal** against the sheets at the founding ship
commit (`9fc6297`).

The founding group's recorded judgments are applied as recorded:
numbered clauses matched as their own units; the fragment
sentence matched as published; outcome, scale, and purpose prose
tags nothing; "diverse" is an adjective, not a function;
"virtual" is an event kind, not a video claim. The founding group
recorded no per-hit removals beyond those judgments, and none
were invented here. An exclusion pass ran before matching:
matched text is `service_desc` **only** — `certified_services`
record fields are **never matched** (CodeSignal carries a
14-entry list naming assessment scores, session recordings, and
an "SSO (SAML) and SCIM Provisioning" service; matching it would
have fabricated claims — pinned by test), and scope-exclusion /
third-party sentences (CodeSignal's "does not process protected
health information or cardholder data"; its third-party
foundation-model subprocessor sentence) assert no function of the
offering. The raw pass in any case produced **no hits at all**,
so nothing was removed. Adjudications and near-misses are
itemized in `scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**Result: 0 claims across the set; both forks are zero-claim.**
The zeros are this set's recorded result, not a defect to be
repaired by re-tuning — a case-insensitive re-check of every
pattern against both descriptions also produces no hits, so the
outcome does not turn on the founding patterns' case sensitivity.
Substance the descriptions assert in other words is itemized
under Named absences and registered as gaps.

Census citations: 4 citations are recorded for these forks in the
census (2 per fork); **4 of 4 verify** as verbatim substrings of
the forks' own descriptions (whitespace-normalized), and **0 of
4** are a claim evidence sentence (there are no claims for them
to evidence). Verification is not a claim, in either direction;
the per-citation record is `scratch/citation_check.json`.

## Function ranking — all 2 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged. Every
family stands at zero claimants in this set; each row is a named
absence, recorded rather than back-filled.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Talent acquisition | 0 | **Core** context (candidate, pipeline, and event records) — **zero claimants in this set; named absence** |
| 2 | Recruiting & hiring process | 0 | **Core** context (requisition → pipeline → placement records) — **zero claimants; named absence** |
| 3 | Video interviewing | 0 | **Core slice** (interview records of kind `video`; the media platform is Extended) — **zero claimants; named absence** |
| 4 | Recruitment assessments | 0 | **Core slice** (assessment records with caller-supplied outcome labels; delivery/scoring Extended) — **zero claimants; named absence** |
| 5 | Predictive assessment science & AI (I-O science) | 0 | Extended (predictive models and validation science) — **zero claimants; named absence** |
| 6 | Talent development | 0 | Extended (development programs past the hire) — **zero claimants; named absence** |
| 7 | Recruitment events (in-person & virtual) | 0 | **Core** (event + registration records; the event platform is Extended) — **zero claimants; named absence** |
| 8 | Talent acquisition pipelines | 0 | **Core** (pipeline definitions, placements, stage movements) — **zero claimants; named absence** |
| 9 | Pipeline automation | 0 | **Core slice** (workflow definition registry, records only; the engine is Extended) — **zero claimants; named absence** |
| 10 | Applicant metrics & analytics | 0 | **Core slice** (registry reporting, counts only; analytics engines Extended) — **zero claimants; named absence** |
| 11 | Data analytics visualization | 0 | Extended (dashboard/visualization engines) — **zero claimants; named absence** |
| 12 | Software delivery (platform) | 0 | Platform note (the build is a single-tenant reference deployment) — **zero claimants; named absence** |

## The Core — what this build implements (13 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's thirteen-function substrate **whole** —
organization registry & membership; candidate registry;
requisition records; pipeline definitions; candidate placements &
stage movements; recruitment event records; event registration
records; assessment records; interview records; workflow
definition registry (records only, never executes); registry
reporting (counts only); registry search; access control &
audit. **No core function is claim-supported in this set** — all
twelve taxonomy families stand at zero — so every function is
**carried, not claimed**: the substrate is the category's records
machinery, carried from the founding build, and it is what any
Talent Management offering's records presuppose. No function is
claimed to be *attained* by any fork — the build is the merged
open implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/talentmgmt/` in 5 of 7 modules; the remaining two
(`__init__.py`, `store.py`) differ by their docstrings only,
which in the founding build named the L2 group and here name
tier null (SHA-256 accounting in this group's README and
`tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `talentmgmt` under `src/`, ids sequential per object type
with fixed prefixes (`org-`, `can-`, `req-`, `pip-`, `plc-`,
`mov-`, `evt-`, `reg-`, `asm-`, `int-`, `wfl-`), failed
operations consume no id and change nothing, all timestamps UTC
ISO-8601, roles `admin|member|viewer` with the founding
permission matrix layered with organization membership, and the
audit log append-only with denied attempts recorded at the HTTP
layer. Where the founding contract's text maps access control and
audit to a Moderate baseline, read it here as **baseline-neutral
hooks**: at tier null they are substrate, claimed against no
baseline.

Two founding invariants are preserved exactly, as the founding
build implements them:

- **The stage bounds rule (the category's signature).** A stage
  movement's `stage_index` must satisfy `0 <= stage_index <
  len(stages)`, enforced by the store's `_check_stage_bounds`
  seam before anything is stored, so a placement's derived
  current stage always names a real stage. A placement's
  `current_stage_index` / `current_stage` and a requisition's
  `past_close` are **derived at read, never stored** — pinned by
  tests.
- **No score field anywhere (the category's doctrine).**
  Assessments store a caller-supplied outcome label verbatim and
  nothing else; no record shape carries a score, rating, ranking,
  or match; reporting is counts of recorded quantities only.
  Neither untiered description tests this doctrine — "score"
  occurs in neither `service_desc` (it occurs only inside
  CodeSignal's `certified_services`, never matched) — so the
  doctrine stands here as founding design, preserved, not as a
  claim about these forks.

**Privacy discipline, preserved exactly:** candidates are opaque
references (`candidate_ref` + label); there is no field anywhere
that can hold a real person's name, contact detail, or
identifier, a resume, assessment content, or an interview
recording or transcript. This is stated against a real divergence
in this set: **CodeSignal's description states that its offering
handles candidate PII (name, email address, IP address) and, for
proctoring, government-issued identity documents and session
video.** That is the fork's data practice, recorded on its sheet
as description; this build does not adopt it — the substrate
stores none of those things, and no record shape here can.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Two tiers of documentation, kept separate:

**Taxonomy tier — none.** No taxonomy family fires anywhere in
this set; the category's taxonomy is in any case functional by
founding design and carries no control families, so no documented
control claim stands at the taxonomy tier.

**Prose tier** — control language in description sentences that
fired no family, traced and quoted, never converted to claims:

- **Identification & authentication (IA) — in part, 1 fork:**
  CodeSignal (FR2635930425). Its description states the offering
  provides "the integration, administration, reporting,
  **identity**, and API services that support them", and that its
  proctoring and integrity services handle "government-issued
  identity documents and session video". The fork asserts an
  identity service surface and identity-document handling for
  proctoring, in its own words; **no mechanism is named** — no
  SSO, MFA, federation, or provisioning is asserted anywhere in
  its `service_desc`, and none is documented here. (An "SSO
  (SAML) and SCIM Provisioning" entry exists in the record's
  `certified_services` field; that field is never matched and
  documents nothing in this spec.) Identity provision itself
  stays with the services the fork describes, exactly as its
  sentences state them.

**Explicitly not documented control claims:** CodeSignal's
"Tenant data is logically segregated" is multi-tenancy platform
prose (the Set 18 posture), not an access-control claim; its
"Customer data handled includes candidate, learner, and user PII
…" paragraph is a data-inventory disclosure, not a control claim;
VOS Sapphire's "into one secure system" is a posture adjective
and its "improves collaboration and compliance" is outcome prose
naming no control, mechanism, or practice — neither documents
anything.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AC, AT, AU (no
audit language occurs; "reporting" in both descriptions is a
function noun, not an audit trail), CA, CM, CP, IR, MA, MP, PE,
PL, PM, PS, RA, SA, SC (no encryption language occurs anywhere in
the set), and SI **as control claims** — is asserted by no
description in the set. If the source later publishes an impact
level for either of these offerings, the tier is recorded then
and not before.

## Named absences

- **All twelve families — 0 of 2.** Every family in the category
  taxonomy stands at zero claimants in this set, and both forks
  are zero-claim. The set's result is stated, not softened.
- **Recruitment assessments, in substance — CodeSignal.**
  "pre-hire assessments delivered in a browser-based IDE",
  "behavioral and cognitive assessments": the family's only
  pattern is the exact phrase "recruitment assessments", which
  never occurs.
- **Video interviewing, in substance — CodeSignal.** "live
  collaborative technical interviews", "AI-conducted screening
  interviews", proctoring "session video": neither "video
  interviewing" nor "video interviews" occurs. (Screening itself
  is present here — the founding L2 checked absence of screening
  was a fact about the L2 forks' descriptions, not a category
  rule.)
- **Predictive science & AI, in substance — CodeSignal.**
  "AI-conducted" is the abbreviation only; neither "I-O science"
  nor "artificial intelligence" is spelled out.
- **Talent development, in substance — CodeSignal.**
  "skills evaluation and development", "experiential technical
  learning": "develop talent" never occurs.
- **Software delivery, in substance — both forks.** CodeSignal
  is a "multi-tenant SaaS platform"; VOS Sapphire is a
  "cloud-based workforce development platform". Neither uses
  either of the family's two phrases ("talent acquisition
  software", "video interviewing software") — the founding group
  claimed this family at software weight on those phrases alone.
- **Pipeline automation, in substance — VOS Sapphire.**
  "streamlines operations through automation": the noun occurs;
  the family's pattern is the verb `automate`, which does not.
- **Talent acquisition, pipelines, events, analytics — VOS
  Sapphire, without the vocabulary in any form.** VOS describes
  a public workforce-services platform; no talent-acquisition,
  pipeline, recruitment-event, or applicant-analytics phrasing
  occurs, exactly or approximately. Its functions are registered
  as gaps in their own names, not approximated into this
  category's families.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented.
The first group is the founding group's standing engine tail,
restated with this set's claimants (zero throughout — several
gain substance from these forks' descriptions, noted per item);
the second group is this set's forks' own described substance,
registered in its own names:

- [ ] Video interview platform — live and on-demand video: capture, streaming, recording storage and playback (founding gap; 0 claimants in this set — CodeSignal's live collaborative interviews and proctoring session video are this engine's substance in other words)
- [ ] Assessment delivery & scoring engines — administering instruments, capturing responses, any scoring computation (founding gap; 0 claimants — CodeSignal's browser-IDE pre-hire, behavioral, and cognitive assessments are its substance; the core records assignments and verbatim outcome labels only)
- [ ] Predictive I-O models & AI — model development, validation, and inference (founding gap; 0 claimants — CodeSignal's AI-conducted screening interviews are inference in substance)
- [ ] Virtual event platform — the virtual venue and event communications (founding gap; 0 claimants in this set)
- [ ] Pipeline automation engine — executing registered workflow definitions (founding gap; 0 claimants — VOS's "automation" is this engine's substance as a noun)
- [ ] Analytics & visualization engines — dashboards, real-time visualization, ROI determination (founding gap; 0 claimants in this set)
- [ ] Talent development programs — development planning, programs, progress past the hire (founding gap; 0 claimants — CodeSignal's experiential technical learning borders this surface; see its own gap below)
- [ ] Identity provider / candidate identity verification — IA-2 stays with the embedding organization (founding gap; 0 claimants — CodeSignal documents an identity service surface and identity-document handling for proctoring at prose weight, above)
- [ ] Assessment proctoring & integrity services — identity-document checks, session monitoring and review, integrity adjudication (CodeSignal)
- [ ] Experiential technical learning platform — hands-on technical learning delivery and its tutor surface (CodeSignal)
- [ ] Integration & API services layer — ATS/HRIS-style integrations and public/developer APIs as a running service surface (both forks in substance: CodeSignal's "integration, administration, reporting, identity, and API services"; VOS Sapphire's unemployment insurance integration is its own gap below)
- [ ] Labor exchange platform — job-seeker/employer matching exchanges as a public employment service (VOS Sapphire)
- [ ] Workforce case management system — case records and workflows for workforce program participants (VOS Sapphire)
- [ ] Employer services platform — services to employers in a public workforce system (VOS Sapphire)
- [ ] Unemployment insurance integration & administration — UI program integration and its administration surface (VOS Sapphire)
- [ ] Labor market information service — labor market data collection, analysis, and delivery (VOS Sapphire)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP. Boundary note: personnel
records, position classification, and onboarding belong to the
Human Resources build — this group holds candidate acquisition
records only, by design and by the founding descriptions' own
wording.

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Talent Management`;
**0 taxonomy claims** tagged from the forks' own descriptions (0
of 2 forks claiming at least one — both forks zero-claim,
recorded); the thirteen-function substrate carried from the
founding Talent Management L2 build (5 of 7 source modules
byte-identical, the other two re-anchored by docstring only) and
re-anchored to tier null; tier null recorded on every sheet and
pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
any fork or for the build itself.
