# Addendum — Health & Wellness, CMMC L2: the 3 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 3
previously uncategorized forks of remainder build unit
**`addition:health-wellness-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 10-function
core, its privacy discipline, and its control baseline are
**unchanged**. This document records what joined, what the newcomers
claim under the group's existing taxonomy, the core-delta decision,
and the updated union statement.

**Headline: forks spec'd 3 / 3; 0 new claims — all 3 additions are
zero-claim forks under the taxonomy applied verbatim; core delta —
zero functions extended, `src/` byte-identical; tests 67 → 80, all
passing.** One of the group's named absences is retired:
**telehealth media**, which stood at 0 claims in the original spec
because no original description claimed video or virtual visits, is
the first newcomer's entire product — it leaves the absence list
and enters §5 as a gap with a claimant. **7 new gap functions** are
named in §5, and 3 already-registered gaps gain claimants by
substance.

## 1. Membership and method

The 3 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2035860874` | Global Telehealth Services, inc. / GTS VirtualHealth Platform (GTS-VP) |
| 2 | `FR2135915901` | Solventum / Solventum RevCycle Health Services Platform |
| 3 | `FR2002367706` | Somnoware Healthcare Systems / Somnoware |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the shipped
  `scratch/extract.py` via `ast` (parsed, never executed) and
  asserts its 11 (id, label, regex) triples before tagging** — the
  taxonomy was applied verbatim, not re-tuned for the newcomers.
  Same sentence splitting, same evidence rule (first matching
  sentence per family, stored verbatim), same sheet schema. The 3
  sheets are **appended** to `specs/specs.json` after the original
  5, which are byte-for-byte untouched (re-serialization prefix
  assertion plus deep-equality against git HEAD, verified in the
  build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 3
  descriptions were present; no live fetching. All 3 are FedRAMP
  **Moderate** and FedRAMP Certified, SaaS, so the group stays
  single-tier and the L2 baseline is inherited in full (Merge
  Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **4
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **4 / 4 verify** as verbatim
  substrings. Verification is not a claim — every cited sentence
  tags no family (see §2).
- **No exclusion trap applies to the newcomers.** None of the 3
  records carries a hosted-services block: every record's
  `certified_services` field is empty (asserted in the extractor).
  Only `service_desc` was matched, per house method.

## 2. What the additions claim

**0 claims** across the 3 forks. This is structural, and it is
pinned in `tests/test_additions.py` (`EXPECTED_CLAIMS`), not
hidden: the taxonomy's 11 patterns are the original siblings'
literal phrases — glucose / CGM vocabulary (`glucose meter data`,
`glucose patterns`, `clinical metrics`), one vendor's brand
pipeline (`connect their Dexcom Clarity data`, `upload CGM User
receiver data`), and one vendor's deployment prose (`Google Cloud`,
`Google Kubernetes Engine`). The newcomers are a telehealth
platform, a revenue-cycle coding platform, and a sleep-medicine
platform; none of them speaks the original five's phrases. The
group's claim total stays **19**, and 3 of its 8 forks now carry
zero claims.

Per-fork claim counts: GTS VirtualHealth **0**, Solventum RevCycle
**0**, Somnoware **0**.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full feed is `scratch/additions_near_miss_feed.json`;
each token below is asserted present in the fork's description by
the additions tests, and each family phrase asserted absent):

- **GTS VirtualHealth** — "labs, images, and **clinical data**" is
  not `measurement_data`'s "clinical metrics". "**integrates with
  RPM medical devices** from most any manufacturer" is device
  integration in substance but matches neither `emr_integration`
  ("integration with client systems" / "Integrated with EMR") nor
  `device_connectivity` (Dexcom's literal pipeline). "patients, and
  patient families" is bare patient wording — the UNION-SPEC
  correction-4 class — not `patient_engagement`. And the fork's
  headline surface, "**Real Time Telehealth visits**" and
  "**video-teleconferencing**", has no family at all: telehealth
  media was a checked named absence in the original spec (see §3).
- **Solventum RevCycle** — "**automatic** suggestion of CPT and
  ICD codes" is not `automation`: neither "automated" nor
  "automates" appears anywhere in the description. "**AI-inclusive
  methodologies**" and "Natural Language Processing (NLP)" are not
  `ai_platform`'s exact phrase "Artificial Intelligence (AI)
  powered" (CuraPatient's). GPCS's "**reimbursement content**" is
  not `claims_processing`'s "justify reimbursement" (Elekta's).
  "**Enterprise Analytics reporting**" matches none of
  `analysis_reporting`'s phrases. "hosts and supports the
  operations of key Solventum software systems" is hosting prose,
  not `hosting_platform`'s Google phrases.
- **Somnoware** — "**engagement metrics**" is not
  `measurement_data`'s "clinical metrics", and the same sentence
  ("patient CPAP therapy progress, risk profiles, and engagement
  metrics") holds the words "patient" and "engagement" **never
  adjacent**, so `patient_engagement` does not fire.
  "**integrations with** all major diagnostic devices, **EMR
  applications**, and therapy manufacturers" is EMR integration in
  substance but is neither "Integrated with EMR" nor "integration
  with client systems". "**clinical intelligence**" is not the
  `ai_platform` phrase. "**Care Management** Console" is not
  `care_guidance`'s "care journey". "diagnostic reports" matches
  no `analysis_reporting` phrase; "cloud-based platform" matches
  no `hosting_platform` phrase.

### Named-absence updates

- **Telehealth media — absence retired.** UNION-SPEC recorded it
  at 0/5 because "no description claims video/virtual visits".
  That sentence is no longer true of the enlarged group: GTS
  claims "Real Time Telehealth visits" and communication "through
  video-teleconferencing" in its first two sentences (verified
  programmatically: across all 8 descriptions, GTS is the only
  fork with video/telehealth wording). The absence rationale is
  gone, so the function gets the standard treatment in §3/§5.
- **Clinical decision support — absence stands.** Somnoware's
  "clinical intelligence" and "accelerated diagnosis" are flavour
  around its diagnostic-report surface, the same treatment
  UNION-SPEC gave Dexcom's "help providers make diabetes
  management decisions": no standalone CDS product claim
  (recommendations, alerts, order sets) is recorded for any of
  the 8 forks. The report-generation engine is gapped in §5.
- **Access control / audit in text — still 0/8.** None of the 3
  newcomers claims RBAC or audit logging in functional terms
  (broad-pattern check across the enlarged group: no hits), so
  Core 9/10 remain baseline-carried, not claimed, exactly as
  shipped.

## 3. Core-delta decisions

No family is claimed by any addition, so no claim buys a new
records form. The per-fork substance was checked against the Core
anyway, and the decisions are stated plainly:

| Addition surface | Records form it presupposes | Core delta |
|---|---|---|
| GTS telehealth visits | **Core 6** activity/appointment records (a visit is an activity record; the media channel is an engine, §5) | **Carried** |
| GTS remote patient monitoring values | **Core 4** measurement/outcome records (metric + value + unit + date; no clinical content) | **Carried** |
| GTS store-and-forward (labs, images, clinical data) | None — the payload is clinical content, Extended by construction under the group's privacy discipline | **Gap** (§5) |
| Solventum coding / grouper / CDI surfaces | None — engines over clinical content; no records form is claimed | **Gap** (§5) |
| Solventum reimbursement content | **Core 7** eligibility/coverage records are the record a reimbursement workflow checks against (opaque `plan_ref` only) | **Carried** |
| Somnoware therapy progress | **Core 5** plan records with derived status; **Core 4** measurement records for its metrics | **Carried** |
| Somnoware diagnostic reports / risk profiles | None — generation and profiling are engines; the substrate computes no risk profile and stores no diagnosis | **Gap** (§5) |

**Result: the core is unchanged.** No function the 3 claim — and
no records form their described surfaces presuppose — is missing
from the build. `src/` is byte-identical to the shipped build
(`src/health/store.py` SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction. The build remains a records substrate, **not a
medical device, and claims no FDA status** — for the newcomers
exactly as for the original five.

## 4. Updated union statement

The group now covers **8 forks** (5 original siblings + 3 remainder
additions), **19 claims** in total (19 + 0), with **5 of 8** forks
carrying at least one claim and 3 pinned at zero. The merged build
remains the same 10-function health records substrate —
participants under opaque references, programs, enrollments with
derived status, measurement/outcome records, care/wellness plans
with derived status, activity/appointment records,
eligibility/coverage records under opaque plan references,
population scorecard reporting, RBAC, append-only audit — now
spec'd against 8 marketplace offerings instead of 5. The group's
character widens: the original union was glucose/CGM-centred with
engagement and claims edges; the additions bring the group's first
telehealth platform, a revenue-cycle coding platform, and a
sleep/pulmonary platform, none of which speaks the taxonomy's
phrases. The privacy discipline is unchanged and binds the
newcomers identically: no field in any record can hold real PHI,
diagnosis content, or clinical free text, and everything clinical
in the newcomers' surfaces is Extended (§5).

## 5. Gaps — for the registry at ship

**New gap functions** (7):

- **Telehealth media engine** — real-time video visits /
  video-teleconferencing (GTS VirtualHealth). Retires the group's
  named absence: UNION-SPEC's long tail stood this item at 0
  claims because no original description claimed it; it now has
  a claimant. The visit record itself is Core 6.
- **Store-and-forward clinical data service** — asynchronous
  exchange of labs, images, and clinical data (GTS
  VirtualHealth). Clinical payload content; Extended by
  construction under the privacy discipline.
- **Medical coding engine (computer-assisted coding)** — NLP
  suggestion/derivation of CPT/ICD codes, coding edits,
  terminology assistance (Solventum). Distinct from the coding
  step inside the claims adjudication gap: this is a standalone
  coding platform, not an adjudication workflow.
- **Grouper / classification & reimbursement content services** —
  GPCS grouping, classification, edits and reimbursement content
  (Solventum).
- **Clinical documentation integrity (CDI) tooling** —
  documentation-integrity workflows and clinician document input
  (Solventum).
- **Diagnostic report generation engine** — instant generation of
  diagnostic reports for sleep and pulmonary tests (Somnoware).
- **Therapy progress & risk-profile console** — CPAP therapy
  progress tracking, risk profiles, and engagement-metrics
  presentation (Somnoware). The underlying values are Core 4
  records; the console and any risk-profile computation are the
  vendor's engine — this build computes no risk profile.

**Existing gaps gaining claimants (by substance — no family claim
fired, recorded as such):**

- **Device connectivity / sync pipelines** — +1 by substance:
  GTS (RPM medical-device integration across manufacturers; the
  family's Dexcom-literal patterns did not fire).
- **EMR/EHR integration engines & documentation depth** — +1 by
  substance: Somnoware (integrations with diagnostic devices,
  EMR applications, and therapy manufacturers).
- **AI/ML models & personalization engines** — +2 by substance:
  Solventum (NLP code suggestion, "AI-inclusive methodologies"),
  Somnoware ("clinical intelligence"). Neither fork's
  `ai_platform` family claim fired.
- **Medical claims adjudication engine** — explicitly gains **no**
  claimant: Solventum's reimbursement *content* is a content
  service (gapped separately above), not adjudication, and its
  "justify reimbursement" pattern did not fire.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and order,
  membership against `remainder.json`, the literal zero-claim
  table, the unchanged group claim total (19), verbatim
  descriptions against the cached dataset, the 4 census citations
  as substrings, and the per-fork near-miss pins (substance token
  present, family phrase absent) — see `tests/test_additions.py`.
- Every addition fork is exercised against the substrate in the
  same tests: a telehealth visit as an activity record with its
  exact contract key set (no media field exists), a monitoring
  measurement, and a follow-up plan deriving overdue with its
  enrollment (GTS); a coverage record under an opaque plan
  reference deriving upcoming → current → ended with its exact
  key set (Solventum); a CPAP plan deriving current → overdue →
  completed over a measurement record whose shape has no
  diagnosis field (Somnoware).
- **Tests: 67 → 80, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the overdue branch of
  `HealthStore._derive_plan_status` in `src/health/store.py` was
  patched to return `"current"` and the full suite ran — **80
  tests, exactly 10 failures**: the shipped drill's 8 plus 2 from
  the new additions module (the GTS visit/plan case and the
  Somnoware CPAP-plan case), tripping exactly as designed; the
  Solventum case does not depend on plan derivation and did not
  trip. `store.py` was restored from the pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`.

## 7. No-signal addition: CirrusMD (post-census)

One further fork joins the group after the additions above:

| Fork | Vendor / product |
|---|---|
| `FR2220549818` | CirrusMD / CirrusMD Virtual Health Chat for Government |

**Why it was not in the census units.** This fork sat in the
remainder census's **`no-signal-set`**: its cached marketplace
description is generic SaaS / security / hosting boilerplate, and
the census recorded **no citations and a `no_signal` flag**
(reason "prose_only") — no citable function could be read out of
the description, so no build unit proposed a category for it.

**Classification basis (live-docs research pass).** The category
was resolved afterwards from the vendor's own public pages
(`../../remainder/nosignal_report.json`, entry `FR2220549818`,
status "resolved", existing category — not a new one):

> "CirrusMD’s multidisciplinary care team of doctors and health
> coaches delivers 24/7/365 physician-first care and guidance at
> scale for health plans and large self-insured employers."
> — https://www.cirrusmd.com/about-cirrusmd

That sentence is recorded on the fork's spec sheet as
`classification_evidence`, with `classification_source_url`
alongside it. **It is a classification citation, not claim
evidence**: it does not occur in the fork's cached marketplace
description (asserted in the tests), and no claim below rests on
it. Claims are tagged from the cached description only, exactly as
in §1.

**Method.** Identical to §1, with one strengthening: the spec
sheet was produced by `scratch/nosignal_extract.py`, which parses
the `TAXONOMY` literal out of the shipped `scratch/extract.py` via
`ast` (parsed, never executed) and asserts its 11 triples — and,
before tagging the newcomer, **re-applies the taxonomy to all 8
shipped sheets' descriptions and reproduces their stored claim
tables exactly** (5 founding + 3 additions; taxonomy-verbatim
proof). The sheet is **appended** to `specs/specs.json` after the
8 shipped sheets, which are verified deep-equal against git HEAD
(both in the extractor and in
`tests/test_nosignal_addition.py`); its description is verified
identical in both cached sources (`raw/data_dump.json` and
`remainder/uncovered.json`). The fork is FedRAMP **Moderate** and
FedRAMP Certified, SaaS, Government Community Cloud, so the group
stays single-tier and the L2 baseline is inherited in full.
**No exclusion trap applies:** the record's `certified_services`
field is empty (asserted in the extractor); only `service_desc`
was matched.

**What the fork claims: 0.** The description is delivery and
posture prose — a multi-tenant Government Community Cloud SaaS
offering, "best-of-breed security solutions", "fully secure and
complies with HIPAA and GDPR", and a provider-managed-environment
paragraph. No family's phrase fires:

| Family | On CirrusMD's words |
|---|---|
| measurement_data | absent — no glucose / clinical-metrics wording |
| analysis_reporting | absent — no review/analysis, patterns, or scorecard phrase |
| care_guidance | absent — "increases access to Agency Care" is not "care journey" or a guidance phrase |
| patient_engagement | absent — the word **"patient" occurs nowhere** in the description |
| claims_processing | absent — no claims or reimbursement wording |
| emr_integration | absent — no integration wording at all |
| ai_platform | absent — no AI wording |
| automation | absent — neither "automated" nor "automates" appears |
| device_connectivity | absent — no device wording |
| multi_device_access | absent — "multi-tenant" is tenancy, not "multi-device accessibility" |
| hosting_platform | absent — community-cloud delivery prose, but neither of Dexcom's Google phrases; hosting is platform-layer regardless |

The group's claim total stays **19**, and **4 of its 9 forks now
carry zero claims** (the 3 additions + CirrusMD). Near-misses are
itemized in `scratch/nosignal_near_miss_feed.json` and pinned in
the tests: "Virtual Health Chat" (the product name, in sentences
1 and 5) names a channel no family covers; "Agency Care" is not
`care_guidance`; "multi-tenant" is not `multi_device_access`;
"cloud-based service offering" is not Dexcom's hosting phrases;
"fully secure" / HIPAA / GDPR prose is posture, the UNION-SPEC
correction classes 1/2/9 — it earns no tag.

**Named-absence updates on this fork's words.** Telehealth was
retired as an absence in §2 on GTS's words; CirrusMD's cached
description adds no telehealth *function* sentence of its own (the
channel appears only in the product name), so the retirement
stands as recorded in §2 and CirrusMD enters the telehealth gap
family by substance in the gap list below, through its
classification citation — not through a claim. Access control /
audit in text is **still absent — now 0/9 forks**: CirrusMD's
security prose is posture, not functional RBAC/audit wording, and
the word "audit" never appears; Core 9/10 remain
baseline-carried, not claimed. Clinical decision support stands
absent (no wording of any kind).

**Core-delta decision.** No family is claimed, so no claim buys a
new records form; the described surface was checked against the
Core anyway:

| CirrusMD surface | Records form it presupposes | Core delta |
|---|---|---|
| Virtual health chat visit with a physician | **Core 6** activity/appointment records (a visit is an activity record; the chat channel is an engine — see gaps) | **Carried** |
| Care-team guidance and follow-up | **Core 5** plan records with derived status; **Core 3** enrollment derivation | **Carried** |
| Chat transcripts / clinical conversation content | None — the payload is clinical content, Extended by construction under the group's privacy discipline; no activity field can hold it | **Gap** (channel gap below) |

**Result: the core is unchanged.** `src/` is byte-identical to
the shipped build, including tracked files (`src/health/store.py`
SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`
before and after this section's work, the mutation drill
included). The tier baseline does not change. The build remains a
records substrate, **not a medical device, and claims no FDA
status** — for CirrusMD exactly as for the other eight.

**Gaps.**

- **New gap function** (1):
  - **Chat-based virtual care channel** — secure text-chat
    encounters between patients and the care team, including chat
    delivery and routing (CirrusMD). Distinct from the telehealth
    media engine (real-time video, GTS): this fork's channel is
    chat, identified from its product name and its classification
    citation; the visit record itself is Core 6, and no
    conversation content is stored anywhere in the substrate.
    With this, telehealth delivery has two claimants-by-substance
    across two channels (GTS video, CirrusMD chat).
- **Existing gap gaining substance** (no family claim fired,
  recorded as such):
  - **Hosting platform** — CirrusMD's description is multi-tenant
    Government Community Cloud delivery prose throughout. A
    platform-layer property, never a health function, exactly as
    recorded for Dexcom in the union spec.

**Updated union statement.** The group now covers **9 forks**
(5 original siblings + 3 remainder additions + 1 no-signal
addition), **19 claims** in total (19 + 0 + 0), with **5 of 9**
forks carrying at least one claim and 4 pinned at zero. The
merged build is unchanged: the same 10-function health records
substrate, now spec'd against 9 marketplace offerings. The
no-signal fork widens the group's character once more — a
chat-first virtual-care platform whose marketplace description
says almost nothing about its function, which is precisely why
the census set it aside and why its classification rests on the
vendor's own live documentation, cited on the sheet. The privacy
discipline binds it identically: no field in any record can hold
real PHI, diagnosis content, or clinical free text, and the
fork's chat content is Extended by construction.

**Verification.**

- Spec integrity is pinned by `tests/test_nosignal_addition.py`:
  sheet count and order (9), the 8 shipped sheets deep-equal to
  git HEAD, membership against the census `no-signal-set`, the
  literal zero-claim table, the unchanged group claim total (19),
  the description verbatim against both cached sources, the
  classification fields pinned against
  `remainder/nosignal_report.json` (with the classification
  sentence asserted absent from the cached description), and the
  near-miss pins. The fork is exercised against the substrate in
  the same module: a virtual health chat visit as a Core 6
  activity record with its exact contract key set (no channel,
  message, or transcript field exists), completed, with a
  follow-up plan deriving overdue and carrying its enrollment.
- Three whole-file pins in `tests/test_additions.py` were scoped
  to that unit's own slice (the first 8 sheets / the unit's
  zero-claim count) because a 9th sheet now follows theirs; every
  fact they pin about the additions unit is unchanged, and the
  scoping is recorded in their docstrings.
- **Tests: 80 → 91, all passing.**
- **Negative control:** the group's signature drill was re-run in
  this tree: the overdue branch of
  `HealthStore._derive_plan_status` was patched to return
  `"current"` and the full suite ran — **91 tests, exactly 11
  failures**: the additions re-run's 10 plus the new CirrusMD
  substrate case, tripping exactly as designed. `store.py` was
  restored from the pre-mutation copy and verified
  SHA-256-identical to the shipped hash; the suite re-ran green.
  Recorded in `tests/README.md`.
