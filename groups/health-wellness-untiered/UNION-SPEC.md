# Union Spec — Health & Wellness, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set**: **3 forks**, category
**Health & Wellness**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes no
baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's union
spec carries.

Membership is exactly census unit `untiered:Health & Wellness` in
`../../remainder.json` (3 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: 2 forks carry the Health &
Wellness category and 1 (WellHive) is filed "Uncategorized (none in
source)"; the census assigned all 3 to this category from their own
descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span Initial Implementation (2)
and FedRAMP In Process (1) — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 3
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 3 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (3/3).

## How functions were counted

The category's fixed 11-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../health-wellness-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 11 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 5 of 5 forks, 19 of 19 claims, deep-equal** against the
sheets at the original ship commit (`b8e3171`) — using the parent's
sentence split and evidence rule (first matching sentence; over 400
characters, truncated to 397 + '...').

This taxonomy was defined from the founding five's glucose / CGM
prose. Applied to three forks whose prose is about care
coordination, at-home therapy, and care navigation, it tags
**1 claim across the set; 1 of 3 forks carries a claim**. The two
zero-claim forks are recorded under Named absences, not hidden.
The founding group's recorded wording-artifact corrections are
embodied in the taxonomy patterns themselves (each family requires
its tightened phrase, not the broad first-pass token — no bare
`data`, `patient`, `support`, `device`, `platform`, or substring
`ai`). An exclusion pass scanned every raw hit's evidence sentence
for scope-exclusion phrasing: **no hits were removed** — the one raw
hit's evidence sentence carries none. The source records'
`certified_services` fields are third-party catalogue segments and
were never read or matched (86Borders' field describes a
background-screening service that is not its offering; see
`scratch/ARTIFACTS.md`). Near-misses — substance present in the
text, family phrase absent — are itemized in
`scratch/ARTIFACTS.md` and pinned by tests; the taxonomy was not
re-tuned for any of them.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.

Census citations: 5 citations are recorded for these forks in the
census; **5 of 5 verify** as verbatim substrings of the forks' own
descriptions (whitespace-normalized), and **1 of 5** is itself a
claim evidence sentence. Verification is not a claim, in either
direction; the per-set record is `scratch/citation_check.json`.

## Function ranking — all 3 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 3) | Disposition in this build |
|---|---|---:|---|
| 1 | Patient engagement & surveys | 1 | Extended (engagement/survey engines; engagement is a program/plan surface over substrate records) |
| 2 | Measurement & device data records (glucose / CGM / clinical metrics) | 0 | **Core** (measurement/outcome records) — **zero claimants in this set; carried, not claimed** |
| 2 | Review, analysis, patterns/trends/statistics & scorecards | 0 | **Core** (population scorecard reporting over the records; analysis engines Extended) — **zero claimants in this set; carried, not claimed** |
| 2 | Care-journey guidance, education & navigation | 0 | Extended (guidance/personalization engines; plan & activity records are Core) — **zero claimants in this set** |
| 2 | Medical claims processing & reimbursement | 0 | Extended (adjudication engine; eligibility/coverage records are Core substrate) — **zero claimants in this set** |
| 2 | EMR / client-system integration | 0 | Extended (integration engines; the substrate's own API is its own design) — **zero claimants in this set; substance present in WellHive, phrase absent (see Named absences)** |
| 2 | AI-powered platform claims | 0 | Extended (AI/ML models, not substrate) — **zero claimants in this set** |
| 2 | Automated guidance / task automation | 0 | Extended (automation/workflow engines) — **zero claimants in this set** |
| 2 | Device data connection & upload (incl. secure-code account linking) | 0 | Extended (device sync pipelines; measurement records they would deliver are Core) — **zero claimants in this set** |
| 2 | Multi-device / web / mobile access | 0 | Platform note (access surface, not a records function) — **zero claimants in this set** |
| 2 | Cloud hosting / deployment claims | 0 | Platform note (the family's verbatim phrases are the founding fork's Google Cloud / GKE prose; both AWS-hosted forks here tag nothing) — **zero claimants in this set** |

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — participant
registry; program registry; enrollments with derived status;
measurement / outcome records; care / wellness plan records with
derived status; activity / appointment records; eligibility /
coverage records; population scorecard reporting; access control
(RBAC); append-only audit log. The substrate is records machinery
that every sibling's output presupposes, and it is tier-independent
code: the founding source contains no tier or baseline machinery,
so there was nothing tier-shaped to strip. Claim support in **this
set** is stated plainly: **no Core function is claim-supported
here.** The set's single claim — 86Borders' `patient_engagement` —
is an Extended-disposition family; its record presuppositions
(participants engaged, programs and plans they are engaged through)
are the substrate's shapes, but the engagement engine itself is not
built and no Core function is claimed on its behalf. The other two
functions the founding spec flags, RBAC and the audit log, are
**carried-not-claimed** exactly as in the parent design (0/3
descriptive claims in this set, and 0/5 in the founding group).
Functions are **carried** as substrate; no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/health/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `health` under `src/`, ids sequential per object type with
fixed prefixes (`par-`, `prg-`, `enr-`, `msr-`, `pln-`, `act-`,
`elg-`), failed operations consume no id and change nothing, all
timestamps UTC ISO-8601, roles `admin|clinician|member|auditor`
with the founding permission matrix, derived statuses computed
deterministically at read against an explicit `as_of` date, and the
audit log append-only with denied attempts recorded. Where the
founding contract's text says the RBAC and audit functions are
required by "the L2/Moderate baseline", read it here as
**baseline-neutral substrate**: at tier null they are carried as
the parent design carries them, claimed against no baseline.

The category's **privacy discipline** is preserved exactly, as the
founding build implements it: participants are keyed by an opaque
caller-supplied `participant_ref` and coverage by an opaque
`plan_ref`; no entity shape has a name, contact, date-of-birth,
member-number, diagnosis, or free-text clinical field — those
fields **do not exist**; the HTTP layer refuses any JSON key outside
an endpoint's named field list with a validation error before
calling the store; a member-role caller reads only records whose
participant's reference is their own name. This build is **not a
medical device and claims no FDA status** — it holds wellness and
care-coordination *records* over opaque references, never real
PHI/PII.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 3 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words. A documented control claim
is a **fork's claim about itself**, recorded here with its
evidence; it is not the build's control attainment, and nothing in
this section fills a family in from any baseline.

Control areas **documented** by at least one fork in the set:

- **Privacy controls (NIST SP 800-53 Appendix J)** — **1 fork**:
  WellHive (FR1825232355) asserts it is "also compliant with HIPAA
  and NIST 800-53 Appendix J Privacy Controls." Recorded at
  compliance-assertion weight: the sentence is the fork's own
  compliance claim about itself, in its own words; it is not a
  function claim under the taxonomy and not evidence about any
  other fork.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AC, AT, AU, CA,
CM, CP, IA, IR, MA, MP, PE, PL, PS, RA, SA, SC, and SI **as
control claims** — is asserted by no description in the set. In
particular: the two forks' AWS deployment prose ("deployed on AWS
Commercial infrastructure", "hosted on AWS GovCloud") is
deployment language, not a cryptographic-protection (SC) claim;
Elvo's "records objective session metrics" is measurement
recording, not audit logging (AU); no description carries SSO,
identity-provider, or access-control language (IA/AC). WellHive's
further assertion in the same passage — "In addition to a FedRAMP
Moderate authorization" — is an authorization assertion, not a
control claim, and it is contradicted by the fork's own record
(impact level Unknown, status FedRAMP In Process); it is recorded
in the Honesty section of the README, and it moves no tier. If the
source later publishes an impact level for any of these offerings,
the tier is recorded then and not before.

## Named absences

- **Measurement & device data records — 0 of 3.** The founding
  group's headline family (3/5 there). Elvo "records objective
  session metrics" and offers "quantitative performance data";
  neither is the family's `clinical metrics` phrase, and no glucose
  or CGM wording occurs in this set. Recorded, not repaired.
- **Review, analysis & scorecards — 0 of 3.** 86Borders promises
  "measurable outcomes" and "higher quality scores"; `scorecards`
  never occurs. Scores are not scorecards.
- **EMR / client-system integration — 0 of 3, substance present.**
  WellHive "connects and unifies care and benefits management
  activities … through integrations with Electronic Health Records
  (EHRs) and practice management systems, provider networks, and
  over 700 insurance carriers" — the function in substance, in
  wording that matches neither verbatim pattern (plural
  "integrations", spelled-out "Electronic Health Records"). The
  loudest near-miss in the set; pinned by test.
- **Care-journey guidance — 0 of 3, substance present.** 86Borders
  pairs "local Care Coordinators" with a "healthcare coordination
  platform managing patient engagement and social care" — care
  coordination in substance; no guidance phrase occurs.
- **Medical claims processing & reimbursement — 0 of 3, substance
  present.** WellHive's "Insurance Verification and Discovery" and
  "benefits management activities" are coverage-adjacent; neither
  family phrase occurs.
- **Cloud hosting / deployment claims — 0 of 3, prose present.**
  Two forks carry AWS hosting prose (AWS Commercial, AWS GovCloud);
  the family's verbatim phrases are the founding fork's Google
  Cloud / GKE deployment prose, so both tag nothing. Hosting is a
  platform-layer property in any case.
- **Telehealth — wording present, no family.** Elvo supports data
  collection and exercise programs "during telehealth visits" — a
  use-case context, and telehealth is not a family in this taxonomy
  (a named absence in the founding group, retired at the L2 tier by
  a remainder-addition fork's own words; retirements do not
  transfer across tiers or sets, and this set records the wording
  without re-opening the question).
- **Access control / RBAC and audit logging in descriptive text —
  0 of 3.** Checked with broad patterns, as in the founding group
  (0/5 there). Both are Core as carried substrate only, flagged in
  the Core section.
- **AI-powered platform, automation, device connectivity,
  multi-device access — 0 of 3 each.** No description asserts them
  in matching text (Elvo's "operationalizes" is not `automated`).
- **Zero-claim forks:** FR2633734921, Elvo — and FR1825232355,
  WellHive. Elvo's whole description is exercise-program delivery
  and session metrics in wording the taxonomy's phrases do not
  reach; WellHive's is care navigation and EHR integration in
  wording that matches neither integration pattern. The zeros are
  recorded, not repaired; the taxonomy was not re-tuned for them
  (the Login.gov posture from the founding additions).

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
restated here only where this set's forks claim or substantively
describe them (counts are this set's):

- [ ] Patient engagement channels & content (1 claimant — 86Borders)
- [ ] Survey instruments depth (0 claimants in this set)
- [ ] EMR/EHR integration engines & documentation depth (WellHive substance, 0 claims)
- [ ] Insurance verification, benefits discovery & claims adjudication engines (WellHive substance, 0 claims)
- [ ] Care coordination & navigation platform depth (86Borders and WellHive substance, 0 claims)
- [ ] Integrated scheduling engines (WellHive substance, 0 claims)
- [ ] At-home therapy delivery & session-metrics analytics engines (Elvo substance, 0 claims)
- [ ] Telehealth visit support (Elvo wording as use-case context, 0 claims)
- [ ] Measurement & outcome analytics engines (Elvo and 86Borders substance, 0 claims)
- [ ] Clinical decision support (0 standalone claims — as in the founding group)
- [ ] Device connectivity / sync pipelines (0 claimants in this set)
- [ ] AI/ML models & personalization engines (0 claimants in this set)
- [ ] Automation / workflow engines (0 claimants in this set)
- [ ] Multi-device native apps (platform/access property, 0 claimants in this set)
- [ ] Hosting platform layer (AWS deployment prose in 2 forks; the build is a single-tenant reference deployment and performs no cloud hosting)

## Coverage statement (for this build)

3 forks spec'd of 3 in census unit `untiered:Health & Wellness`;
1 taxonomy claim tagged from the forks' own descriptions (1 of 3
forks claiming at least one); the ten-function substrate carried
byte-identical from the founding Health & Wellness L2 build and
re-anchored to tier null; tier null recorded on every sheet and
pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for any
fork or for the build itself. This build is not a medical device
and claims no FDA status.
