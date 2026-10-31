# Addendum — Learning Management, CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:learning-management-l2`** (see `../../REMAINDER.md`).
The original union spec stands as written: its taxonomy, its
14-function core, its Moderate control baseline, and its five
core-boundary decisions are **unchanged**. This document records
what joined, what the newcomer claims under the group's existing
taxonomy (nothing), the core-delta decision, and the updated
union statement.

**Headline: forks spec'd 1 / 1; 0 new claims — a zero-claim
fork; core delta — zero functions extended, `src/`
byte-identical; tests 104 → 118, all passing.** The singleton's
checked absences were rechecked against the newcomer (§2): the
scoring and credential absences survive in both senses; the
assessment absence survives at claim level (no assessment
family exists in this taxonomy) while its substance picture
changes — the newcomer names assessments as catalogue content;
and the mobile-application *vocabulary* observation no longer
holds for the enlarged group, though it yields no claim and no
gap. **1 new gap function** is named in §5, registered from the
fork's described function rather than from any claim, and 2
already-registered gaps gain a member by substance.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2118043605` | Skillsoft / Percipio |

Census membership was verified against `remainder.json` before
building (unit `addition:learning-management-l2`, `fork_ids ==
["FR2118043605"]`, `extends_group == "learning-management-l2"`).
The fork is filed **Uncategorized** in the source (`forks.json`
category "Uncategorized (none in source)", source business
categories `[]`); Learning Management is the census proposal,
recorded on the sheet as such. Category boundary, stated once:
Learning Management is strictly separate from **Education &
Training** (Groups 13 and 30) — no function from that category's
taxonomy was imported here, and none of this group's families
was re-tuned toward it.

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast`** (parsed, never executed,
  never re-typed) and asserts its 26 (id, label, regex) triples.
  Before tagging the newcomer, the extractor **reproduces the
  original fork's shipped claim table exactly** from the cached
  description — PowerTrain: all 26 claims, evidence sentences
  included, deep-equal — and asserts the shipped sheet
  deep-equal to git HEAD. The new sheet is **appended** to
  `specs/specs.json`; the original sheet is byte-preserved
  through its closing brace (asserted in the extractor).
- The original extractor records its wording-artifact
  corrections as prose in its docstring (no CORRECTIONS literal
  exists); they were applied by the same reasoning, and the
  mechanical ones are asserted in the extractor: only
  `service_desc` is matched; the newcomer's
  `certified_services` is empty (asserted); category labels and
  product names earn no tags; "assessments" naming catalogue
  content is not assessment administration (original correction
  3's reasoning); a "score" substring inside another word would
  not be scoring vocabulary (correction 6) — the newcomer in
  fact contains no "score" token at all.
- Exclusion discipline, checked not assumed: the description's
  final sentence — "The external content providers are not
  assessed." — is a scope-exclusion segment (it places
  third-party content providers outside the authorization
  boundary). It contains no taxonomy pattern phrase, so the
  extractor asserts it contributes **zero raw hits**: the
  matched text is the full text and **nothing was removed**.
  The sentence before it ("The learning platform and mobile
  apps were assessed as in-boundary for FedRAMP.") is assurance
  prose about the fork's own authorization posture and tags
  nothing.
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is
  FedRAMP **Moderate** / Certified, SaaS, **Hybrid Cloud**, so
  the group stays single-tier and the Moderate baseline is
  inherited in full (Merge Rules 1–2), unchanged. (Hybrid Cloud
  is the fork's own deployment property; it transfers nothing
  to the build.)
- The census starting point was verified, not trusted: the
  fork's **1 census citation** was re-checked against its own
  cached description and **verifies verbatim** — it is the
  description's first sentence. It tags no family (see §2):
  verification ≠ claim, and census classification ≠ claim
  either, in both directions.

## 2. What the addition claims

**0 claims.** The newcomer's entire marketplace description is
545 characters in five sentences. Under the taxonomy applied
verbatim it produces **0 raw hits across all 26 families** —
every sentence's hit list is empty (`scratch/
additions_sentence_map.json`) — so there is nothing for the
wording-artifact corrections to correct and nothing was
manufactured.

Group claim counts after the addition (2 forks): the total
stays **26** — every family at exactly 1, claimed by PowerTrain;
the newcomer claims none of the 26.

### Near-misses, itemized

The description's phrases, one by one:

- **"authenticates users"** (sentence 1) asserts user
  authentication in substance, but `identity_authentication`
  requires the phrase "multi-factor authentication" (the
  original fork's MFA/SSO platform claim). No MFA or SSO phrase
  appears. Substance without the phrase earns no tag; the
  substance is registered against the identity gap in §5.
- **"tracks learner's progress"** (sentence 1) is progress
  tracking in substance, but `learner_activity_tracking`
  requires "tracking and analysis of learner activities" and
  `learning_experience_records` requires "capture, store, and
  return data about learning experiences". Neither phrase
  appears. The records form the tracking presupposes is Core 7
  (progress records) — already built; no tag, no delta.
- **"connects users to content"** (sentence 1) is content
  access in substance, but `learning_content_delivery` requires
  "learning delivery" / "content delivery" and
  `learning_content_management` requires "management of
  eLearning content". Neither phrase appears. The substance
  rides the delivery-engine gap in §5.
- **"offers 1000s of video-based courses along with ebooks,
  audiobooks, practice labs, boot camps, and assessments"**
  (sentence 2) is a catalogue of content formats the fork
  supplies. No family covers a licensed content library (the
  taxonomy's catalogue-adjacent families are the original
  fork's own phrases: "SCORM 1.2" for
  `content_standards_distribution` — no standards token of any
  kind appears here, not even the substring "SCORM"). The
  library substance is registered as a new gap in §5;
  "assessments" inside this list is treated in the absence
  recheck below.
- **"to help your workforce build skills"** (sentence 2) is
  skills-building in substance; `competency_management`
  requires the phrase "competency management", and no
  competency token of any kind appears.
- **"accessible from both a web browser as well as Apple and
  Andriod mobile apps"** (sentence 3) — the source's own
  misspelling "Andriod" is preserved verbatim in the sheet,
  not corrected. Multi-channel access is the fork's delivery
  surface (platform layer); no family covers it.
- **"a SaaS learning experience platform"** (sentence 1) is
  positioning: `hosting_platform` requires "cloud environment
  that hosts", and no hosting phrase appears. SaaS is the
  fork's delivery model regardless — it transfers nothing.

### Wording artifacts

None. Zero raw hits means no claim stands on an artifact, and
no artifact had to be pinned at reduced weight.

### The singleton's checked absences, rechecked

The union spec's named absences were findings about the
original fork's description. Against the newcomer:

- **Scoring / grading — survives in both senses.** The
  newcomer's text contains no "score" token at all (not even
  the SCORM substring — there is no "SCORM" either) and no
  grading vocabulary. No score field exists anywhere in the
  build; the additions substrate case pins this recursively
  over a statement whose `result_text` is the score-looking
  string "score: 88/100", stored verbatim, never parsed.
- **Assessment — survives at claim level; the substance
  picture changes.** No assessment family exists in this
  taxonomy (the original's single "assessments" occurrence
  named succession-planning resources; correction 3). Percipio
  names "assessments" as one of the content formats it offers
  — assessment *content* in a catalogue list, not assessment
  administration. No claim fires and none is manufactured; the
  substance is booked once, under the new content-library gap
  in §5, not double-booked as an administration function.
- **Credential / certificate — survives in both senses.** No
  "certif" or "credential" token appears anywhere in the
  newcomer's text; nothing is issued, conferred, or tracked as
  a credential.
- **Proctoring, content authoring, discussion / social
  learning, virtual classroom, gamification — survive in both
  senses.** No token of any of them appears.
- **Mobile-application vocabulary — retired as a vocabulary
  observation only.** The union spec recorded the original
  fork's description as containing no mobile-application
  vocabulary; the enlarged group's descriptions now do
  (Percipio's web + mobile-app access surface). No taxonomy
  family exists for mobile apps, so no claim follows, and no
  gap is registered: the apps are the fork's access surface, a
  platform property, and the delivery substance rides the
  already-registered delivery-engine gap.

## 3. Core-delta decisions

The newcomer claims no family, so no family's disposition
changes. The per-family state for the enlarged group, for the
record (dispositions per UNION-SPEC's ranking; every family is
claimed by 1 of 2 forks — PowerTrain — and by 0 for the
newcomer):

| Family | Disposition (UNION-SPEC) | Core delta |
|---|---|---|
| Event registration | Core | **Carried** |
| Mandatory training compliance | Core | **Carried** |
| Learning experience records (LRS) | Core slice; xAPI runtime Extended | **Carried** |
| Learner activity tracking | Core | **Carried** |
| Training authorization forms (SF-182) | Core | **Carried** |
| Individual development plans | Core | **Carried** |
| Competency management | Core | **Carried** |
| Lesson plans | Core slice; authoring Extended | **Carried** |
| Learning content management | Core; delivery/runtime Extended | **Carried** |
| Adjustable workflow | Core slice; execution Extended | **Carried** |
| Automated notifications | Core slice; automation/transport Extended | **Carried** |
| Wait list management | Core | **Carried** |
| Reporting | Core slice; report builder Extended | **Carried** |
| Learning content delivery | Extended — delivery engine | **Carried** (gap gains a substance member, §5) |
| Content standards & distribution | Extended — packaging/distribution runtime | **Carried** |
| EHRI data collection & reporting | Extended — integration engine | **Carried** |
| Learning analytics | Extended — analytics engine | **Carried** |
| Career mapping | Extended — recommendation engine | **Carried** |
| Succession planning | Extended — talent suite | **Carried** |
| Candidate review | Extended — talent suite | **Carried** |
| Employee surveys | Extended — survey engine | **Carried** |
| Knowledge base / wiki | Extended — adjacent product | **Carried** |
| Web CMS platform | Extended — adjacent product | **Carried** |
| Identity & authentication (MFA/SSO) | Platform note | **Carried** (gap gains a substance member, §5) |
| Multi-tenancy | Platform note | **Carried** |
| Hosting platform | Platform note | **Carried** |

**Result: the core is unchanged.** A zero-claim fork
presupposes no records form; the singleton's five
core-boundary decisions stand verbatim — opaque learner
references, progress records as the derivation substrate,
**no scores anywhere** (the newcomer's catalogue contains the
word "assessments" and no scoring vocabulary, and nothing in
this addendum licenses a score field), SF-182 decisions by a
decider who is never the creator, lesson plans as catalog
records. `src/` is byte-identical to the shipped build (all 7
`lms` modules SHA-256-verified against the pre-work baseline,
`scratch/additions_src_hashes_before.txt`; `store.py` remains
`820d97121fd55799b77b417b23d72d26680e22596141ee58e52cfa32bb3bba8a`,
the shipped hash, the mutation drill included; the final
`git diff` on `src/` is empty, pyc churn restored). The
category invariants hold untouched: statement records keep
their exact eight-key shape, compliance status is derived
never stored, and the workflow registry never executes.

## 4. Updated union statement

The group now covers **2 forks**, **26 claims** in total, with
**1 of 2** forks carrying claims. The merged build remains the
same 14-function learning records substrate — learner registry
of opaque references, course/content/lesson-plan catalog,
events & registrations with read-derived seat views, SF-182
authorization records with separation of duties, IDP records,
competency records with verbatim levels, progress records,
eight-key LRS statement records with no score field, compliance
assignments with read-derived status, never-executing workflow
& notification registries, search & counts-only reporting,
REST API, RBAC with learner scope, append-only audit — at the
Moderate baseline, now spec'd against 2 marketplace offerings
instead of 1. The group's character is unchanged and, if
anything, confirmed from the other side: the original fork is
an enclave whose learning ecosystem claims every family its
own vocabulary defines, while the newcomer is a commercial
learning experience platform whose entire Moderate listing is
five sentences of positioning prose. The substrate both would
presuppose is the same; only one of the two listings says so
in the taxonomy's phrases. The category remains strictly
separate from Education & Training at this tier, as at L1.

## 5. Gaps — for the registry at ship

**New gap functions** (1) — registered from the fork's
described function (its catalogue sentence), **not** from a
claim:

- **Licensed content library & practice-lab environments**
  (Skillsoft / Percipio) — the hosted off-the-shelf content
  catalogue itself: 1000s of video-based courses, ebooks,
  audiobooks, and boot camps supplied as licensed content,
  plus hands-on practice-lab environments, and the assessment
  content the catalogue includes (booked here once, as
  content — see §2). The substrate's catalog (Core 2) holds
  records *about* content items and their standards metadata;
  the library is the content supply itself, and no registered
  gap names it: the delivery-engine gap below is the runtime
  that presents content, not the licensed catalogue it
  presents.

**Existing gaps gaining a member by substance (no claimant):**

- **Learning delivery engine** (registered in UNION-SPEC: the
  course playback / delivery runtime; the substrate holds its
  records) — +1 **by substance**: the newcomer "connects users
  to content" and offers its catalogue for consumption across
  web browser and mobile apps. That is a delivery surface
  asserted in its own words; no delivery phrase of the
  taxonomy fires, so no claimant is counted at claim level.
- **Identity provider / MFA / SSO service** (registered in
  UNION-SPEC: IA-2 stays with the embedding organization) —
  +1 **by substance for the authentication half**: the
  newcomer "authenticates users" in its own words. No MFA or
  SSO phrase appears, so the platform-note family does not
  fire and nothing about this build's identity posture
  changes: the build still ships hooks, not an IdP.

**Explicitly no claimant:**

- **Learning analytics & outcomes-effectiveness engines** —
  gains **no** claimant: "tracks learner's progress" is
  tracking substance whose records form is Core 7; no
  analytics phrase appears, and no analytic engine is
  asserted.
- **SCORM / AICC / cmi5 packaging & distribution runtime** —
  gains **no** claimant: the newcomer names no content
  standard at all (no "SCORM" substring, token-verified in
  the additions tests); its catalogue formats (video, ebook,
  audiobook) are content kinds, not packaging standards.
- **xAPI protocol runtime & LRS conformance** — gains **no**
  claimant: no "API" token of any kind appears in the
  newcomer's text (the original fork's only "API" occurrence
  is inside "Experience API (xAPI)"; the newcomer has none).
- **EHRI integration engine, career mapping &
  training-recommendation engine, leadership succession
  planning suite, candidate review system, employee survey
  engine, knowledge base / wiki platform, web CMS platform,
  content authoring tools, SF-182 form workflow, configurable
  report builder, workflow execution engine, notification
  automation & transport** — all gain no claimant: the
  newcomer's text contains no token of any of them
  (token-verified in the additions tests).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the original
  fork's claim table standing exactly (26 claims, evidence
  spot-checked), the literal zero-claim table and the
  whole-taxonomy zero-claim set for the newcomer, tier fields,
  the description verbatim against the cached source
  (whitespace-normalized, "Andriod" preserved), census
  citation accounting, the exclusion-segment pin, the
  named-absence rechecks, and the near-miss pins (see
  `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests: a progress record with a compliance assignment
  whose status derives at read (current before the due date,
  overdue after it on an in-progress record, completed after
  a completed progress record; the stored assignment carries
  no status field), and catalogue content records in the
  fork's formats with an experience statement over one of
  them (exact eight-key shape, a score-looking `result_text`
  stored verbatim, and a recursive no-score-field scan over
  the statement, the progress record, and the report).
- **Tests: 104 → 118, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree. Drill
  (compliance derivation): the overdue branch of
  `LmsStore._derive_status` in `src/lms/store.py` patched to
  `return "current"` (scoped patch on the exact
  `if as_of_date > due:` branch; the target line occurs
  exactly once, count asserted) — **118 tests, exactly 10
  failures**: the shipped drill's 9 plus exactly 1 from the
  additions module
  (`test_additions.TestAdditionSubstrateCases.test_percipio_progress_and_compliance_derivation`),
  tripping as designed. `store.py` was restored from
  `scratch/store.py.premutation-additions` and verified
  SHA-256-identical to the shipped hash (`820d9712…`); the
  suite re-ran green. Recorded in `tests/README.md`; raw
  output in `scratch/additions_mutation_run.txt`.
