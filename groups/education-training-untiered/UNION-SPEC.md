# Union Spec — Education & Training, untiered set (DeadRamp Phase 2, remainder)

The union contract for the eighth **untiered set**: **6 forks**,
category **Education & Training**, **tier null**. Every member's
FedRAMP impact level is **Unknown** in the source dataset — the
source publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts **no
control baseline**. Per PIPELINE.md, untiered offerings "build to
their documented control claims; tier stays null in the registry
until the source publishes a baseline." The Documented control
claims section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly census unit `untiered:Education & Training`
in `../../remainder.json` (6 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: 1 fork carries the Education
& Training category (Dossier), 2 are filed "Uncategorized (none in
source)" (KnowBe4, Proofpoint), 2 are filed under Analytics
(MyEvaluations, Simuhealth), and 1 under Customer Service (Toonimo);
the census assigned all 6 to this category from their own
descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span Initial Implementation (4)
and FedRAMP In Process (2) — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 6
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 6 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (6/6).

This category is Education & Training. It is **not** Learning
Management: the Learning Management groups have their own taxonomy
and substrate, and nothing here is borrowed from them.

## How functions were counted

The category's fixed 21-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../education-training-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 21 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 8 of 8 forks, 43 of 43 claims, deep-equal** against the
sheets at the original ship (the founding group's later
remainder-addition sheet, Pearson VUE, is an addendum sheet and is
not part of the proof target) — using the founding sentence split
and evidence rule (first matching sentence; over 400 characters,
truncated to 397 + '...'; `\r` replaced with a space before
splitting, the founding group's documented normalization).

An exclusion pass then scanned every raw hit's evidence sentence
for third-party catalogue segments and scope-exclusion /
authorization-status sentences (the founding group's correction
class: a claim stands only when the matched text asserts a
customer-facing function of the offering itself). **One hit was
removed** — Toonimo's `certificates_credentials`, whose only
evidence sentence is the offering's own FedRAMP target-certification
statement — and the scan flagged no other hit. The removal and all
wording-artifact adjudications are itemized in
`scratch/ARTIFACTS.md`. `certified_services` fields in the raw
records (non-empty for four of the six forks) were never matched;
only `service_desc` text is tagged.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**29 claims** across the set; **5 of 6 forks carry at least one
claim**. The one zero-claim fork is recorded under Named absences,
not hidden.

Census citations: 9 citations are recorded for these forks in the
census; **9 of 9 verify** as verbatim substrings of the forks' own
descriptions (whitespace-normalized), and **5 of 9** are themselves
a claim evidence sentence. Verification is not a claim, in either
direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 6 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 6) | Disposition in this build |
|---|---|---:|---|
| 1 | Reporting, dashboards & analytics | 5 | **Core** (reporting over the records; dashboard/analytics engines Extended) |
| 2 | Course, catalog & training program management | 4 | **Core** (course/catalog registry) |
| 3 | Scheduling of training & assessment sessions | 4 | **Core** (scheduling records) |
| 4 | AI & automation tools | 3 | Extended (AI assistants and automation engines; two of the three hits are automation wording at recorded weight — see ARTIFACTS.md) |
| 5 | Learner progress, readiness & experience tracking | 2 | **Core** (progress/readiness records) |
| 6 | Assessments & testing — delivery & administration | 2 | **Core** (assessment records; delivery engines and scoring Extended) |
| 7 | Certification, licensure & credential records | 2 | **Core** (credential records, not issuance; Dossier's hit is at records weight — see ARTIFACTS.md) |
| 8 | Hosting & platform services (PaaS, multi-tenant, hosted cloud) | 2 | Platform note — not a learning function; single-tenant reference deployment (see gaps) |
| 9 | Enrollments & candidate registration | 1 | **Core** (enrollment/registration records) |
| 10 | Learning content, recording & media | 1 | Extended (content delivery, recording & playback engines) |
| 11 | Access control & authorized-user access | 1 | **Core** (RBAC) |
| 12 | Recruiting, hiring, onboarding & workforce management | 1 | Extended (HCM/HRIS domain suite) |
| 13 | Simulations & simulation debriefing | 1 | Extended (simulation capture/debrief engine; tracked-experience records are Core) |

**Zero-claim families in this set (8 of 21):** compliance training &
compliance management (0/6 — the set's headline absence, see Named
absences); talent profiles, skills & best-fit matching (0/6);
training delivery & skills development (0/6 — the family's delivery
phrases occur nowhere, despite two security-awareness-training
products and an LMS in the set); career exploration, coaching &
transition support (0/6 — Dossier's career-development substance
stands without a family phrase); employee performance management
(0/6); policy management (0/6); peer interaction, discussion &
social learning (0/6); data storage, processing & profile data
capture (0/6).

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — course/catalog
registry; enrollments & registrations; learner progress & readiness
records; assessment records; certificate/credential records;
compliance assignments & derived status; scheduling records;
reporting over the records; access control (RBAC); append-only
audit log. The substrate is records machinery that every sibling's
output presupposes, and it is tier-independent code: the founding
source contains no tier machinery, so there was nothing tier-shaped
to strip. Where the founding contract's text justifies RBAC and the
audit log partly as Moderate-baseline hooks, read that here as
**baseline-neutral hooks**: at tier null they are substrate,
claimed against no baseline. Functions are **carried** as
substrate; the claims that support them are recorded below, and no
function is claimed to be *attained* by any fork — the build is the
merged open implementation, not any fork's product.

Claim support in **this set**, per function, stated plainly:

- **Claim-supported at family weight (8):** course/catalog registry
  (`course_catalog` 4/6); progress & readiness records
  (`learner_progress` 2/6); assessment records (`assessments` 2/6);
  credential records (`certificates_credentials` 2/6, Dossier's at
  records weight — certification documents held as attachments);
  scheduling records (`scheduling` 4/6); reporting
  (`reporting_analytics` 5/6); enrollments & registrations
  (`enrollment_registration` 1/6 — KnowBe4's self-service
  enrollment; thin, stated plainly); RBAC (`access_control` 1/6 —
  Dossier's "role-based access control"; the same thin 1-of-N
  support the founding group recorded for its own set).
- **Claim-supported at documented-prose weight (1):** the audit
  log. This category's taxonomy has no audit family (the founding
  group recorded audit-in-text as a named absence at 0/8 and
  carried the log as a baseline hook). Here Dossier asserts "audit
  logging" in its own service sentence — prose support, recorded
  under Documented control claims (AU), not converted into a
  taxonomy claim.
- **Carried, not claimed at family level (1):** compliance
  assignments & derived status. The `compliance_training` family
  stands at **0/6 in this set** — the word "compliance" occurs in
  none of the six descriptions. The derivation's inputs are claimed
  by Dossier under other families (assessment schedules and overdue
  flags, under `assessments` / `scheduling`), and the derivation
  itself is deterministic substrate logic carried from the founding
  build on exactly the basis the founding spec stated for its own
  reaches past the counts. It is flagged here so no reader mistakes
  it for a claimed vendor function in this set.

The founding category's doctrines are preserved exactly, as the
founding build implements them: **compliance status is derived,
never stored** — the stored assignment record carries no status
field, and status (`current` / `overdue` / `completed`) is computed
deterministically at read from assignment, due date, progress
records, and an explicit `as_of` date; and **assessment records
carry no score or grade field** — item responses are stored
verbatim and scoring is an Extended engine (Dossier's "proficiency
ratings" are a fork's recorded data in its own prose; no scoring
family exists in the taxonomy and none is claimed). Progress
percent and readiness are recorded fields on progress records, as
in the founding build — records, not computed scores.

The carried code is **byte-identical** to the founding group's
`src/learn/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `learn` under `src/`, ids sequential per object type with
fixed prefixes (`crs-`, `enr-`, `prg-`, `asm-`, `cred-`, `cmp-`,
`sch-`), failed operations consume no id and change nothing, all
timestamps UTC ISO-8601, roles `admin|instructor|learner|auditor`
with the founding permission matrix plus learner scope (a learner
reads only records whose `learner_id` is their own), and the audit
log append-only with denied attempts recorded.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 6 offerings (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words. A documented control claim
is a **fork's claim about itself**, recorded here with its
evidence; it is not the build's control attainment, and nothing in
this section fills a family in from any baseline. One further
record: Dossier states its included services are "categorized Low
under FIPS 199" — the fork's own categorization statement, recorded
in `scratch/ARTIFACTS.md`; the marketplace record's impact level
stays "Unknown" and no tier is recorded from prose.

Control areas **documented** by at least one fork in the set:

- **Access control (AC)** — 1 fork, family-traced: Dossier for
  Government (FR2700137041), via `access_control` ("role-based
  access control" in its Dossier Profile service sentence). At
  records weight, the same fork's data inventory also lists
  "account role assignment" among the records it holds.
- **Audit logging (AU)** — 1 fork, at documented-prose weight:
  Dossier for Government (FR2700137041) asserts "audit logging"
  in the same Profile service sentence. This category's taxonomy
  has no audit family, so the assertion is recorded here in the
  fork's own words; it is not a taxonomy claim and not the build's
  attainment.
- **Cryptographic protection (SC)** — 1 fork, at documented-prose
  weight: KnowBe4 (FR1912662229) — "All email addresses are
  encrypted and kept private." An assertion about the offering's
  handling of one data type, recorded at exactly that weight.
- **Identification & authentication (IA)** — documented **in part**,
  at prose weight: KnowBe4's Active Directory Integration syncs
  user data so users "will be added, changed and archived in sync
  with changes made within AD automatically" — directory-based
  provisioning, recorded as such. No fork in this set asserts
  authentication, SSO, or MFA in its own words.

**Platform-layer prose, recorded but NOT documented as the fork's
own control claim:** KnowBe4's "We use FedRAMP compliant Amazon Web
Services East (AWS US East), which is maintained in an ISO
certified facility" is an inherited-platform posture statement (and
its "FedRAMP compliant" / "PCI compliant" adjectives are status
prose, the founding group's artifact class); Toonimo's
authorization-boundary sentence names leveraged AWS components
(containers on Kubernetes/EKS, managed database, object storage,
CDN, WAF, KMS) — a boundary description of a leveraged platform,
not a control the offering itself asserts. MyEvaluations'
"accreditation workflows" and Simuhealth's "accreditation evidence
management" are likewise **not** documented under CA: accreditation
there is the forks' *product function for their customers*
(medical-education and simulation-center accreditation), not a
control claim about themselves, and the distinction is recorded
rather than blurred.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, CA, CM, CP,
IR, MA, MP, PE, PL, PM, PS, RA, SA, and SI **as control claims** —
is asserted by no description in the set, beyond the prose-weight
notes above. If the source later publishes an impact level for any
of these offerings, the tier is recorded then and not before.

## Named absences

- **Compliance training & compliance management — 0 of 6.** The
  headline absence, and a wording fact: the word "compliance"
  occurs in none of the six descriptions. KnowBe4 offers only the
  adjective "compliant" (FedRAMP / SCORM / PCI status prose), and
  Dossier — whose whole product is recurring competency-obligation
  tracking with assessment schedules, notifications, and overdue
  flags — never uses the word. The family is not back-filled; the
  substrate's derivation is carried and flagged (see the Core).
- **Training delivery & skills development — 0 of 6.** The family's
  delivery phrases occur nowhere, even though the set contains two
  security-awareness-training products and Dossier's integrated
  LMS. Delivery is Extended regardless; the absence is of the
  *phrasing*, recorded as found.
- **Simulated phishing — substance without the family noun.** The
  `simulations` family has 1 claimant (Simuhealth), but KnowBe4's
  simulated-phishing platform does not fire it: the pattern is the
  noun `simulation`, and "Simulated Phishing" is the adjective.
  The taxonomy was not re-tuned; the engine is a gap below with
  KnowBe4 and Proofpoint as substance claimants.
- **Assessments — KnowBe4 at 0.** Its "Phishing Security Tests" are
  assessments in substance; "tests" is not the family's
  `assessment` / `test session` phrase.
- **Learner progress — Simuhealth at 0 on the founding precedent.**
  "Competency tracking" is the substance; founding correction 7
  requires "tracking of", and bare "tracking" was tightened out
  there. Governed by the Acadis precedent, not re-tuned here.
- **Career development — Dossier at 0 on phrasing.** Its
  "structured career development supporting clinical ladder
  programs" matches none of the family's phrases; the substance is
  a gap below.
- **Zero-claim fork:** FR1916744879, Proofpoint Security Awareness
  Training — its description is outcome prose ("drives behavior
  change and real security outcomes"; "tracks all the metrics that
  your CISO needs" — "tracks" is not "tracking of") and fires no
  family. The zero is recorded, not repaired.
- **Scoring / grading — 0 of 6, as in the founding group.** No
  description uses score/grade wording for assessments; Dossier's
  "proficiency ratings" are recorded data in its prose, with no
  scoring family in the taxonomy. Scoring stays Extended.
- **Proctoring & identity proofing — 0 of 6.** No description in
  this set claims either; both stay gaps, as in the founding group.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
restated here only where this set's forks claim or substantively
assert them (claimant counts are this set's):

- [ ] Phishing simulation & security-awareness training engines (KnowBe4, Proofpoint in substance — simulated phishing campaigns, phishing security tests, remedial learning assignment)
- [ ] Training content delivery & LMS engines (KnowBe4's content library and SCORM delivery, Dossier Learn's course delivery — delivery itself; the records are Core)
- [ ] Competency management & assessment-cycle engines (Dossier — competency definitions per role, assessor sign-off workflows, proficiency ratings, configurable reassessment cycles)
- [ ] Notification & reminder engine (Dossier, in substance — automated notification of upcoming and overdue assessments; the founding group's named gap gains a claimant here)
- [ ] Medical education management engines (MyEvaluations — accreditation workflows, clinical-hours / procedure / patient logs, continuous educational improvement)
- [ ] Simulation-center operations engines (Simuhealth — resource coordination, equipment & inventory lifecycle, scenario libraries, accreditation evidence management; the simulation capture/debrief engine of the founding tail included)
- [ ] Digital adoption & in-application guidance engines (Toonimo — walkthroughs, AI chatbot & voicebot guidance, process intelligence)
- [ ] AI assistants & guidance bots (Toonimo; the set's other two `ai_automation` hits are automation wording — notification automation and directory sync, engines included here and under integrations)
- [ ] Directory integration & user provisioning sync (KnowBe4 Active Directory Integration — the category's integrations substance; the founding taxonomy's API/integrations family was dropped at 0/8 there and stays dropped)
- [ ] Career development & clinical ladder engines (Dossier Development Program — advancement levels, evidence submission, progression review)
- [ ] Credentialing & accreditation workflow engines (MyEvaluations credentialing and accreditation workflows; credential *records* are Core)
- [ ] Deterministic scoring & proficiency-rating engines (Dossier's proficiency ratings in substance; scoring was 0/6 explicit here as in the founding set)
- [ ] Recruiting, HCM/HRIS & workforce management suite (MyEvaluations onboarding claimant; the founding tail's domain suite)
- [ ] Talent, skills & marketplace matching engines (0 claimants in this set; founding tail restated for completeness of the category ledger)
- [ ] Remote proctoring & identity proofing (0 claimants in this set, as in the founding group — specified so the absence is a finding)
- [ ] General cloud hosting / PaaS & multi-tenancy (2 claimants at platform-note weight — the merged build is a single-tenant reference deployment and says so)

## Coverage statement (for this build)

6 forks spec'd of 6 in census unit `untiered:Education & Training`;
29 taxonomy claims tagged from the forks' own descriptions (5 of 6
forks claiming at least one; 1 raw hit removed in the exclusion
pass and recorded); the ten-function substrate carried
byte-identical from the founding Education & Training L2 build and
re-anchored to tier null; tier null recorded on every sheet and
pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for any
fork or for the build itself.
