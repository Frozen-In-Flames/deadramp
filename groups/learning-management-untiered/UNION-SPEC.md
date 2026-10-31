# Union Spec — Learning Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Learning
Management: **1 fork**, tier **null**. The member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes
no baseline for this offering — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries — and in this set it is empty, stated plainly
below.

Membership is exactly census unit `untiered:Learning Management`
in `../../remainder.json` (1 fork ID, verified mechanically).
**Category assignment, recorded:** `forks.json` files this fork
under **Education & Training**, and its own source record lists
business categories ["Education & Training", "Learning
Management"]. The census assigned it to **Learning Management**
from its own description (classifier note: "Virtual school / LMS
platform") and placed it in this unit. Learning Management and
Education & Training are separate registry categories with
separate taxonomies and separate shipped groups; nothing in this
build is borrowed from the Education & Training groups, and the
filed category is preserved on the sheet
(`business_categories_in_source`) rather than hidden. A category
label is not a functional claim either way (the founding group's
correction 7).

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`. Source:
GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product record joined by
FedRAMP ID **FR2634357692**. The description is present in the
cached dataset and matches `../../remainder/uncovered.json`
exactly. The fork's recorded authorization status (Initial
Implementation) is record data, not a claim.

## How functions were counted

The category's fixed 26-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../learning-management-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 26 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **shipped claim tables exactly —
deep-equal on both sheets**: the PowerTrain founding singleton's
table (26 of 26 claims) and the remainder addition's Percipio
sheet (0 of 0 claims), using the founding sentence split and
evidence rule (whitespace normalized — runs of whitespace
collapse to single spaces — first matching sentence stored
verbatim as evidence). The instrument that yields 26 claims on
the founding fork is the instrument applied here.

An exclusion pass scanned for third-party catalogue segments and
scope-exclusion sentences: **raw hits 0, removed 0** — there was
nothing to remove. The fork's source record carries an empty
`certified_services` list, so no claim could have rested on a
catalogue; the description contains no scope-exclusion phrasing.
The emptiness of both checks is recorded in
`scratch/ARTIFACTS.md`, not assumed.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not a
ceiling. Result: **0 claims**. The single fork is a **zero-claim
fork** — the same outcome the founding group's own remainder
addition produced for Percipio under this taxonomy — recorded
under Named absences, not hidden, and not repaired by re-tuning
the taxonomy.

Census citations: 1 citation is recorded for this fork in the
census (its opening sentence); it **verifies** as a verbatim
substring of the fork's raw description and of the normalized
sheet description, and it is the evidence sentence for **no**
claim, because there are no claims. Verification is not a claim,
in either direction; the record is `scratch/citation_check.json`.

## Function ranking — the set member

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged. Every
family stands at 0 of 1 in this set.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | Registration management for learning events | 0 | **Core** — event & registration records, waitlist as recorded state |
| 2 | Mandatory training compliance | 0 | **Core** — assignments with status **derived at read**, never stored |
| 3 | Learning record store — experience data capture, storage & return (xAPI LRS) | 0 | **Core slice** — experience statement records; the xAPI protocol runtime is Extended |
| 4 | Learner activity tracking | 0 | **Core** — progress & activity records |
| 5 | Training authorization & certification forms (SF-182) | 0 | **Core** — authorization records with recorded decisions |
| 6 | Individual Development Plans (IDP) | 0 | **Core** — development plan records |
| 7 | Competency management | 0 | **Core** — competency definitions & learner competency records (levels verbatim) |
| 8 | Lesson plans | 0 | **Core slice** — lesson plan records in the catalog; authoring is Extended |
| 9 | eLearning content management | 0 | **Core** — content registry records; delivery/runtime Extended |
| 10 | Adjustable workflow | 0 | **Core slice** — workflow definitions registered as data, **never executed**; the execution engine is Extended |
| 11 | Automated notifications | 0 | **Core slice** — notification records; automation & delivery transport are Extended |
| 12 | Wait list management | 0 | **Core** — part of the registration records |
| 13 | Reporting & configurable reports | 0 | **Core slice** — registry summaries & search computed from records; the configurable report builder is Extended |
| 14 | Learning delivery & management | 0 | Extended — the delivery engine itself (the substrate holds its records) |
| 15 | Content standards & distribution (SCORM / AICC / cmi5) | 0 | Extended — packaging/distribution runtime; standards recorded as content-item metadata in Core |
| 16 | EHRI data collection & reporting (HR integration) | 0 | Extended — the EHRI integration & feed engine |
| 17 | Learning analytics & outcomes analysis | 0 | Extended — the analytics engine (Core reporting is counts over records) |
| 18 | Career mapping & recommended training | 0 | Extended — mapping/recommendation engine |
| 19 | Leadership succession planning | 0 | Extended — talent-domain suite |
| 20 | Candidate review (talent acquisition) | 0 | Extended — talent-domain suite |
| 21 | Employee surveys & data collection | 0 | Extended — survey engine |
| 22 | Knowledge base / wiki platform (adjacent product) | 0 | Extended — an adjacent enclave product, not the learning substrate |
| 23 | Web content management platform (adjacent product) | 0 | Extended — an adjacent enclave product, not the learning substrate |
| 24 | Identity & authentication — MFA / SSO (platform) | 0 | Platform note — the build ships RBAC hooks, not an IdP |
| 25 | Multi-tenancy (platform note) | 0 | Platform note — deployment property; single-tenant reference deployment |
| 26 | Cloud hosting platform (platform note) | 0 | Platform note — delivery prose; deployment layer |

**Functions this fork asserts in substance that have no family**
(the taxonomy's absences, not the fork's — each is gapped in its
own name below and itemized in `scratch/ARTIFACTS.md`): a live
virtual classroom (audio/video classroom experiences, real-time
collaboration with shared content and recording); course-material
authoring ("build and edit course materials from a single
workspace"); assignments, evaluations & grading (grading
vocabulary is present; the taxonomy contains no scoring/grading
family at all); user management; a media & shared-materials
repository; and reporting & data analysis (present as generic
prose that fires none of the three reporting-adjacent families'
phrases).

## The Core — what this build implements (14 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's fourteen-function substrate **whole** — learner
registry (opaque references); course, content & lesson-plan
catalog; events & registration management; training authorization
(SF-182) records; individual development plan records; competency
records; learner progress records; learning experience records
(LRS statements); mandatory training compliance & derived status;
workflow & notification registries; search & summary reporting;
API access; access control; audit log. The substrate is the
records machinery the category's claimed functions presuppose,
and it is tier-independent code: the founding build's source
contains no tier machinery in its records operations. Where the
founding contract's text traces features to the Moderate/L2
baseline, read it here as **baseline-neutral**: at tier null the
substrate is claimed against no baseline. **Claim support in
this set: none of the fourteen functions is claim-supported by
the set's fork** — the fork claims nothing, so every function is
**carried, not claimed**, exactly as recorded here. Functions are
carried as substrate; no function is claimed to be *attained* by
the fork — the build is the merged open implementation, not the
fork's product.

The carried code is **byte-identical** to the founding group's
`src/lms/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `lms` under `src/`, ids sequential per object type
with fixed prefixes, failed operations consume no id and change
nothing, all timestamps UTC ISO-8601, roles
`admin|instructor|learner|auditor` with the founding permission
matrix plus learner scope (a learner-role actor reads only
records whose `learner_ref` is their own name), and the audit
log append-only with denied attempts recorded.

The category's doctrines are preserved exactly, as the founding
build implements them:

- **LRS statement records are pinned to exactly eight keys** and
  there is **no score field** — no record shape in the build
  carries a score field and nothing computes one, pinned by a
  recursive key scan in the carried tests. A statement's
  `result_text` is caller-supplied text recorded verbatim, never
  parsed; competency levels are recorded verbatim in the
  caller's own scale.
- **Compliance status is derived at read, never stored**: from
  the assignment, its due date, the learner's progress records,
  and an explicit `as_of` date — `completed` when a completed
  progress record exists, `overdue` when `as_of` is after the due
  date, `current` otherwise. Event seat counts are likewise
  derived at read.
- **The workflow registry never executes**: registering a
  workflow definition changes no other record, ever, pinned by
  test. The registry holds definitions as data.
- **Learners are opaque references only**: a caller-supplied
  `ref` and a label, a shape pinned by test so no field can hold
  a real personal identifier.
- **Authorization decisions are recorded by a named decider who
  is never the record's creator** (separation of duties,
  enforced in the store).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What a documented control claims section would
hold is only what the fork's own marketplace description
asserts, in its own words.

In this set, that section is **empty**: the fork's description
asserts **no control language of any family**. The check is
mechanical — the tokens "security", "authentication", "access
control", "encrypt", "audit", and "compliance" each occur
**zero** times in the description. One adjudication, stated so
the bound is explicit: the bullet "User management" names a
product function (the product's own user administration); it
names no mechanism, no access-control assertion, and no
authentication method, so it is **not** recorded as an AC or IA
control claim — it is gapped below as a function, in its own
name. The fork's deployment model ("Public Cloud") is record
data, not a control claim.

Control areas **not documented** by the fork: **every** NIST SP
800-53 control family — AC, AT, AU, CA, CM, CP, IA, IR, MA, MP,
PE, PL, PM, PS, RA, SA, SC, and SI **as control claims** — is
asserted by no sentence in the description. (The build's own
access-control and audit machinery is substrate carried from the
founding build; it is the build's design, not a fork's claim and
not a baseline.) If the source later publishes an impact level
for this offering, the tier is recorded then and not before.

## Named absences

- **All 26 families — 0 of 1.** The whole taxonomy stands at
  zero in this set; the ranking table above is the itemization.
  Headline absences, because the fork's category would lead a
  reader to expect them:
  - **Learning experience records / LRS — 0.** No "xAPI" token
    occurs anywhere in the description; its "central repository"
    is a media repository, not an LRS.
  - **Content standards & distribution — 0.** No "SCORM", "AICC",
    or "cmi5" token occurs; the substring "scor" occurs zero
    times in the whole description.
  - **Mandatory training compliance — 0**; the word "compliance"
    occurs zero times.
  - **Event registration, competency management, IDPs, SF-182
    forms, lesson plans, workflow, notifications — 0 each**; the
    corresponding vocabularies do not occur.
- **Zero-claim fork:** FR2634357692, Collaborative Learning
  Environment — its description is five capability bullets of
  virtual-school prose in which no functional pattern phrase of
  any of the 26 families appears. The zero is recorded, not
  repaired; the taxonomy was not re-tuned for it (the Percipio
  posture from the founding group's addition).

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented. The founding group's seventeen gaps stand
registered under the founding group; this set adds **no
claimants** to them (its fork claims nothing) — the analytics
gap is noted below as gaining substance, not a claimant. New
gaps from this fork's own description, each named for the
function its prose asserts in substance:

- [ ] open — Virtual school / virtual classroom delivery runtime (live audio/video classroom experiences; the substrate holds learning records, not a classroom)
- [ ] open — Real-time collaboration & session recording services (shared content, recording capabilities)
- [ ] open — Course material authoring workspace (build and edit course materials from a single workspace)
- [ ] open — Media & shared-materials repository service (the central repository the description asserts)
- [ ] open — Assignment, evaluation & grading engine (named in the fork's own words; the build computes no score and this gap does not change that — it is the fork's function, registered as specified-not-implemented)
- [ ] open — User administration service (the product's own user management; distinct from the build's RBAC hooks and from the founding group's IdP gap)
- [ ] open — Platform layer (the fork's Public Cloud hosting is the deployment layer itself, not a function of this build)

Already registered, gaining substance from this set (noted, not
re-registered):

- Learning analytics & outcomes-effectiveness engines / reporting
  beyond registry counts (founding group) — this fork's
  "Reporting and data analysis" bullet is substance toward it.

## Coverage statement (for this build)

1 fork spec'd of 1 in census unit `untiered:Learning Management`;
**0 taxonomy claims** tagged from the fork's own description (the
fork is a zero-claim fork, recorded plainly); the
fourteen-function substrate carried byte-identical from the
founding Learning Management L2 build and re-anchored to tier
null; tier null recorded on the sheet and pinned by tests.
Nothing in this build claims a FedRAMP authorization, a CMMC
certification, or a control baseline for the fork or for the
build itself. This category is Learning Management; it is not
Education & Training.
