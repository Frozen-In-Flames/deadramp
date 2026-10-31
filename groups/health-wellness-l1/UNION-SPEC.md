# Union Spec — Health & Wellness, CMMC L1 (DeadRamp Phase 2 remainder, Health & Wellness L1 singleton)

The singleton spec for the Health & Wellness category at the L1
tier: **1 fork, FedRAMP LI-SaaS** — **Itamar Dispatcher Cloud
(IDC)** (Itamar Medical), FedRAMP Certified, SaaS, Public Cloud.
Built under the remainder census unit
`new-singleton:Health & Wellness|L1`.

**Membership provenance, stated plainly:** `forks.json` files this
fork "Uncategorized (none in source)" at tier L1 — its source
record carries an empty `business_categories` list. The DeadRamp
category is the **remainder census proposal**, taken from the
fork's own description (a cloud service supporting providers
conducting home sleep apnea tests; census classifier note: "Home
sleep apnea testing support."). Reconciliation: `remainder.json`
unit == `specs/specs.json` == {FR2212912561}, zero diff, and the
fork's own recorded fields (LI-SaaS, FedRAMP Certified, L1) match
the source record exactly. MAP.md's category arithmetic is
unaffected: this fork was never in MAP.md's Health & Wellness
count, because MAP.md counts the Phase 1 category field.

## Lineage: a cross-tier carry, downward (the Merge Rule applied across tiers)

This build does not start from zero. Its parents are:

1. The **Group 18 merged build** (`../health-wellness-l2/`) — the
   union of the 5 Health & Wellness L2 (FedRAMP Moderate) forks, a
   working clean-room health records substrate (10 core
   functions), whose taxonomy and substrate this category uses at
   every tier. Group 18 was later enlarged by 3 remainder
   additions (8 sheets spec'd, claim total unchanged at 19); its
   core did not change. Singleton 46 (`../health-wellness-l3/`)
   carried the same substrate **up** to High.
2. This singleton's **1 LI-SaaS fork**, via the spec sheet in
   `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents (Rule 1) — the category
substrate is carried whole, not stripped because one fork's
marketing prose is thin (a wording floor is not a downgrade, the
same reasoning Singleton 46 recorded in the upward direction and
the CRM L1 singleton recorded downward). The tier, however, is
this fork's own: **LI-SaaS / L1**, the lightest tier, and the
baseline below is written **fresh for Low** (Rule 2 satisfied at
the merged tier, which here is L1). Rule 3 traceability is this
document plus the spec sheet; Rule 4's SSDF-shaped process is the
provenance here, the review recorded in `scratch/ARTIFACTS.md`,
and the verification record in `tests/README.md` (full suite run
by the builder; the signature negative control mutation-verified
live in this tree).

**What does NOT carry down, stated once:** Group 18's Moderate /
NIST SP 800-171 baseline citations stay in Group 18, and
Singleton 46's High uplifts are **not** inherited downward —
hash-chained audit, fail-closed audit writes, audit query and the
`/audit/verify` endpoint, logon lockout, and the **auditor-role
tightening** (at High the auditor holds `audit_read` only) answer
High-baseline demands that do not exist at Low/L1. The auditor
here keeps Group 18's matrix (the 7 record reads + `report_read`
+ `audit_read`, no writes). The implementation needs no downward
modification at all: all 7 `src/` modules are byte-identical to
Group 18's (hash record in `scratch/reuse-note.md`), because the
L2 build carries no Moderate-specific machinery in code — its
baseline lives in its spec documents, not in the implementation.

## How functions were counted — zero claims, honestly

Group 18's 11-family taxonomy was applied **verbatim** — parsed
via `ast` out of Group 18's shipped `scratch/extract.py` (never
executed, never re-typed). **How the taxonomy is confirmed to be
the original:** `scratch/` is gitignored, so the extractor file
itself was never committed; what was committed is what it
produced — the 5 spec sheets at the original ship commit
(`b8e3171`). Before the newcomer was tagged, this group's
extractor re-tagged those 5 forks from the raw cache with the
parsed taxonomy and reproduced their shipped claim tables
**exactly** (19 claims, evidence strings included), cross-checked
against the on-disk parent sheets (deep-equal to that commit; the
later additions build parsed and asserted the same literal). If
the on-disk taxonomy had been altered since the original pass,
the reproduction would fail; it does not. A family is claimed
only when the fork's own description contains matching text; the
first matching sentence is stored in `specs/specs.json` as
evidence. Source: GSA FedRAMP Marketplace dataset, cached at
`raw/data_dump.json` (produced by the General Services
Administration, last change 2026-10-22).

**Result: 0 claims.** Itamar's description is three sentences
about a dispatcher cloud for home sleep apnea testing: it supports
providers conducting home sleep tests with the WatchPAT device;
providers integrate the IDC APIs into patient management systems
to initialize devices and collect test results; patients take the
study with the device and a proprietary mobile application that
transfers sleep study data to IDC. Group 18's taxonomy was defined
from glucose/CGM and patient-engagement descriptions, and its
patterns are literal phrases from those descriptions ("glucose
meter data", "clinical metrics", the spelled-out "Artificial
Intelligence (AI) powered", Dexcom's own pipeline sentences). None
of them fires on a sleep-diagnostics dispatcher's vocabulary.
**Raw hits equal claims (0 = 0):** nothing was removed before
matching — the source record's `certified_services` is empty
(asserted in the extractor), there is no hosted-app catalogue and
no scope-exclusion sentence, and the named components (WatchPAT,
the mobile app) are the fork's own. The full description is
preserved verbatim in the spec sheet, and no function was invented
for it. Counts are a floor, and here the floor is zero — the same
honest outcome as the zero-claim sheets in Groups 28 and 35,
Singleton 46 in this very category, and Group 18's own three
remainder additions.

Near-misses, recorded in full in `scratch/ARTIFACTS.md`, not
rounded up: "integrates the IDC APIs into supported patient
management systems" is EMR/client-system integration **in
substance** but matches neither of the family's literal phrases
(the Somnoware precedent at L2: substance recorded, no claim);
"initialize WatchPAT devices" and "communicates and transfers
sleep study data to IDC" are a device data pipeline **in
substance** but match neither of the device family's Dexcom
literals; "collect test results" and "sleep study data" are
clinical content, not the measurement family's glucose literals —
and under this category's privacy discipline clinical content is
Extended by construction, never a substrate measurement record
(Singleton 46's EEG ruling is the direct precedent); "a proprietary
Mobile application" is a single companion app, not the access
family's plural-surface phrases; "supports" is the bare-support
wording of Group 18's correction 3; "in a secure manner" is a
posture adverb, the correction 9 class — no access-control or
audit claim.

**Census citation accounting:** the census recorded one citation
for this fork — sentence 1 — which verifies as a strict verbatim
substring and tags **no** family. There are no claims, so no claim
rests on an uncited sentence either. Verification is not a claim,
in either direction; both facts are pinned in
`tests/test_singleton_spec.py` and `scratch/citation_check.json`.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Measurement & device data records (glucose / CGM / clinical metrics) | **Core** — measurement/outcome records, carried from the Group 18 union (claimed 3 of 5 there). This fork's sleep study data and test results are NOT this family: they are clinical content, Extended by construction (below), and no study payload is ever a substrate measurement record |
| 1 | 0 | Review, analysis, patterns/trends/statistics & scorecards | **Core** — population scorecard reporting over substrate records, carried from the Group 18 union (3 of 5 there); analysis engines Extended |
| 1 | 0 | Care-journey guidance, education & navigation | Extended — carried from the Group 18 union (1 of 5 there); plan & activity records are Core |
| 1 | 0 | Patient engagement & surveys | Extended — carried from the Group 18 union (2 of 5 there). This fork's "patients" are actors in a diagnostic procedure (Group 18 correction 4), not an engagement claim |
| 1 | 0 | Medical claims processing & reimbursement | Extended — adjudication engine, carried from the Group 18 union (2 of 5 there); eligibility/coverage records are Core |
| 1 | 0 | EMR / client-system integration | Extended — integration engines, carried from the Group 18 union (2 of 5 there). This fork integrates with patient management systems **in substance** (sentence 2); the gap gains a claimant by substance, the family claim does not fire |
| 1 | 0 | AI-powered platform claims | Extended — AI/ML models, carried from the Group 18 union (1 of 5 there). No AI wording of any kind in this fork's text |
| 1 | 0 | Automated guidance / task automation | Extended — automation/workflow engines, carried from the Group 18 union (1 of 5 there). No "automated/automates" wording here |
| 1 | 0 | Device data connection & upload (incl. secure-code account linking) | Extended — device sync pipelines, carried from the Group 18 union (1 of 5 there). This fork's device initialization and study-data transfer are that pipeline **in substance**; the gap gains a claimant by substance, the family claim does not fire |
| 1 | 0 | Multi-device / web / mobile access | Platform note — carried from the Group 18 union (2 of 5 there); an access surface, not a records function. This fork's single proprietary mobile application is a claimant by substance for the native-apps gap, not this family's phrase |
| 1 | 0 | Cloud hosting / deployment claims | Platform note — carried from the Group 18 union (1 of 5 there); the Public Cloud record field is record data, not description text, and tags nothing |
| 1 | — | Access control / RBAC (0 claims in category text at any tier) | **Core** (baseline substrate) — carried, not claimed |
| 1 | — | Audit logging (0 claims in category text at any tier) | **Core** (baseline substrate) — carried, not claimed |
| 1 | — | Telehealth media | **Named absence — survives at this tier.** Retired at L2 by the GTS addition's own words; this fork's text has no video/virtual/visit wording (token-checked), and a dispatched home diagnostic is not a media visit. Not built, not a gap beyond its Group 18 registration |

Plus this singleton's own engines, named from its description's
own words (all Extended, detailed in Gaps below): home sleep-test
dispatch & WatchPAT device initialization; sleep study results
collection & provider review. These are **clinical/diagnostic
surfaces**: per this category's hard privacy rule they are never
built here, and nothing in this build claims any diagnostic
function.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35/38/40 precedent).** This fork tags zero claims, yet
all 10 core functions stand in this build. The reasoning is the
Merge Rule itself: the category substrate is the union this fork's
category presupposes, carried whole at the fork's own tier. The
presupposition is read at the level of the product's operation and
stated here as *interpretation, not evidence*: a dispatcher cloud
through which providers run home sleep tests for patients
presupposes people held as records (→ participant registry — held
under opaque references, never as patient identities), a testing
offering those tests are run under (→ program registry), patients
bound to that offering (→ enrollments), the study itself as a
scheduled, completable event (→ activity records), caller-recorded
administration values about the study (→ measurement records —
metric name, number, unit, date only; the study's clinical payload
is not this), follow-up work with due dates (→ plan records),
coverage for the test (→ eligibility records under opaque plan
references), and review over all of it (→ scorecard reporting,
RBAC, audit). Each step is a substrate function from Group 18's
core; none of them is this product's engine — its engines are the
device dispatch, the API integration, and the clinical data
pipeline, all Extended. The alternative — building nothing at L1,
or building only a stub around a claim this fork does not make —
was considered and rejected: the category's L1 tier would carry no
substrate while every other tier carries it, and a stub would
invert the core/extended boundary. The price of carrying the
substrate is this disclosure and the coverage statement's wording:
**core carried, not claimed, for this fork.** That price is paid
in full, in both places.

**Named absences.** Telehealth media survives at this tier (see
the ranking note): the L2 retirement rested on the GTS addition's
own words at L2, and a retirement must rest on the fork's own
words — this fork's words describe a device-dispatched home
diagnostic, token-checked for video/virtual/telehealth/visit
wording (all zero). Standalone **clinical decision support**
stands absent (no recommendation/alert/order-set wording;
"collect test results" is collection, not decision support — the
category-wide ruling that also covered Dexcom's flavour at L2 and
Somnoware's "clinical intelligence"). **Access control / RBAC**
and **audit logging** in descriptive text stand at 0 for this
fork ("access" and "audit" tokens: zero; "in a secure manner" is
posture) — both Core as baseline only, flagged. They are recorded
so the union is complete and the absences are provable from the
record; they are not built as vendor functions and the absence
items are not gaps, because nothing was claimed (the Group 21
precedent).

## The Core — what the build implements (10 functions, carried at the L1 baseline)

The same 10 functions as Group 18, carried whole:

1. **Participant registry** — participants (`par-`) keyed by an
   **opaque, caller-supplied reference only** (`participant_ref`,
   unique), kind patient/caregiver/professional. No names, contact
   details, dates of birth, or any other identifier fields exist
   in the shape. Carried, not claimed.
2. **Program registry** — programs, clinics, and care journeys as
   records (`prg-`), configuration-controlled. Carried, not
   claimed.
3. **Enrollments with derived status** — enrollment/registration
   records (`enr-`) binding a participant to a program; duplicate
   active enrollments rejected. Stored status is always
   `enrolled`; reads add a **derived status** computed
   deterministically from the participant's plan records for that
   program (overdue > completed > enrolled). Carried, not claimed.
4. **Measurement / outcome records** — numeric value + unit +
   metric name + date (`msr-`), per participant, optionally per
   program. **No diagnosis fields, no free-text clinical notes**;
   unknown or extra fields are refused at the boundary. Carried
   from the Group 18 union.
5. **Care / wellness plan records with derived status** — plan
   records (`pln-`) with a due date and an optional completion
   date; status **derived** at read (`completed` when a completion
   date is recorded, `overdue` when `as_of` is after the due date,
   `current` otherwise) — the derivation lives in the single
   method `_derive_plan_status`. Carried from the Group 18 union.
6. **Activity / appointment records** — scheduled activities and
   appointments (`act-`) bound to a participant and optionally a
   program, with lifecycle state (scheduled / completed /
   cancelled). Records only — no scheduling or visit engine.
   Carried, not claimed.
7. **Eligibility / coverage records** — per-participant coverage
   records (`elg-`) holding an **opaque plan reference only**
   (`plan_ref`), with coverage dates and a **derived** status
   (upcoming / current / ended). No insurer names, member numbers,
   or benefit details exist in the shape. Carried, not claimed.
8. **Population scorecard reporting** — aggregates per metric
   (count, min, max, mean) and per derived status over the
   substrate records, group-wide (`report`) and per program
   (`scorecard`), plus per-participant measurement listing.
   Aggregation over records only; pattern/trend engines are
   Extended. Carried from the Group 18 union.
9. **Access control (RBAC)** — admin/clinician/member/auditor
   roles over 16 actions, enforced before any state change, plus
   member scope (a member-role actor reads only records whose
   participant's `participant_ref` is their own user name).
   Baseline substrate, carried not claimed.
10. **Audit log** — append-only audit of every mutation, every
    report/scorecard read, and every denied attempt; optional
    JSONL persistence; no mutation API. Baseline substrate,
    carried not claimed.

**Privacy discipline (hard rule, inherited).** Records and opaque
references only: no entity shape in this build can hold a real
name, address, phone, email, date of birth, SSN, member/insurance
number, diagnosis, or clinical free text — the shapes are
enforced by tests, and the HTTP layer refuses any JSON key outside
an endpoint's named field list. For this fork the rule bites in a
specific place: **sleep study data and test results are clinical
content.** The substrate holds none of it — no device payloads, no
waveforms, no results, no findings. A measurement record here is a
caller-recorded administration value (a metric name, a number, a
unit, a date) and nothing else; the pipeline that moves the real
study data from the WatchPAT device and the mobile application
into IDC is the fork's Extended engine, and anything that would
hold real PHI would need its own authorization basis.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this
  fork's impact level) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline.
  LI-SaaS is FedRAMP's tailored **subset** of that baseline for
  SaaS offerings, so the union baseline is the Low baseline itself,
  cross-walked to the FAR 52.204-21 basic-safeguarding practices
  that define CMMC L1. One fork at one tier plus the carried
  substrate, so no merge changes the tier (Merge Rules 1 and 2
  recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Participant registry (opaque refs) | AC-2, AC-3, SI-10; IA-2 (hooks) | Participants exist only as explicit records under caller-supplied opaque references; no identifier fields exist to leak; identity itself is supplied by the embedding organization |
| Program registry | CM-6, SI-10 | Programs are explicit, configuration-controlled records; nothing is offered that is not registered |
| Enrollments with derived status | AC-3, AU-2/AU-3 (Low side), CM-6 | Enrollment is an explicit, auditable record; its status is derived deterministically from plan records and is reproducible from the records and the trail |
| Measurement / outcome records | AU-2, AU-3 (Low side), SI-10 | Every measurement leaves a validated record (named fields only; extra fields refused); inputs are validated before any record exists |
| Care/wellness plan records | AU-2, AU-3 (Low side), CM-6 | Plan status is derived deterministically from due/completion dates; derivation is queryable and reviewable |
| Activity / appointment records | AU-2, AU-3 (Low side), CM-6 | Activities are explicit records bound to participants and programs, with auditable state changes |
| Eligibility / coverage records | AC-3, AU-2/AU-3 (Low side) | Coverage exists only as a record under an opaque plan reference, with derived status reviewable as of any date |
| Population scorecard reporting | AU-2, AU-3 (Low side) | Reports aggregate the substrate records only (per metric, per program); no side-channel data |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Four-role matrix enforced pre-mutation at two layers; role differentiation traced to AC-3 — see precision notes |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing is
  silently imported from the sibling tiers' tables):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and its
    LI-SaaS tailoring) carries the AU family — Group 18's AU-6
    (audit review) and AU-9 (protection of audit information)
    citations are Moderate selections and are **not** claimed here;
    AU-2/AU-3 only. Singleton 46's hash chain, fail-closed writes,
    and audit query (AU-5/AU-7/AU-9 uplifts) are High answers and
    are not inherited downward.
  - **Separation of duties / least privilege:** the four-role
    differentiation (and member scope) is a design property of the
    carried substrate. Its Moderate-table family homes in Group
    18's spec were AC-5/AC-6, which are **not** Low-baseline
    selections, so at this tier the differentiation is traced to
    AC-3 access enforcement, with AC-5/AC-6 named as lineage only.
    Singleton 46's auditor tightening was an AC-5 answer at High
    and is likewise not inherited: the auditor here holds Group
    18's read set.
  - **What else does not carry down:** Group 18's CA-7 citations
    (enrollment/plan derivation and reporting rows) are Moderate
    selections in its table and are not claimed here; the
    derivations are traced to AU-2/AU-3 (Low side) and CM-6.
    Singleton 46's AC-7 lockout is a High answer, absent here by
    design (the demo registry has the same four users as at L2).
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence, and
  any real compliance claim still has to be earned inside each
  regime separately.

## Implementation contract (summary)

Identical to Group 18's — `src/health/` (Python stdlib only):
`errors` (`HealthError`, `ValidationError`, `NotFoundError`,
`PermissionDenied`), `access` (User, admin/clinician/member/
auditor matrix over 16 actions), `audit` (append-only AuditLog),
`store` (HealthStore: the 10 core functions; failed operations
consume no ids; permission checks precede mutation; the plan
derivation lives in the single method `_derive_plan_status`),
`service` (HTTP layer, demo registry alice=admin / bob=clinician /
carol=member / dana=auditor), `__main__` (`python -m health
serve`, port 8792). All 7 modules byte-identical to Group 18's
(hash record in `scratch/reuse-note.md`). `tests/`: see
tests/README.md for the test count and the negative-control record
(the count is filled in from the build, not stated here).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Itamar Dispatcher Cloud (IDC), LI-SaaS,
  its actual impact level recorded in the spec sheet; category by
  remainder-census proposal, provenance recorded).
- Claims evidenced for the fork: **0** of 11 families — the
  zero-claim outcome is the finding, recorded with its near-misses,
  not a gap in the paperwork.
- Core implemented: **10 / 10** functions above — **carried as the
  category substrate under the core-boundary decision, not claimed
  as this fork's evidenced functions.** The distinction is the
  coverage statement, not a footnote to it.
- Tests: **79 run, 79 passed**, including the mutation-verified
  negative control performed against this group's tree
  (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its
description's own words — the product's actual surface, none of it
built here):

- Home sleep-test dispatch & WatchPAT device initialization:
  dispatching studies to patients, initializing devices for a
  study, and the device-side lifecycle around a home sleep test.
- Sleep study results collection & provider review: collecting
  the study's results from the device pipeline and presenting
  them for provider review. The payload is clinical content —
  Extended by construction under the privacy discipline; the
  substrate stores no result, waveform, or finding.

Registered gaps gaining a claimant **by substance** from this fork
(no family claim fired; recorded as substance, per the L2
additions precedent):

- EMR/EHR integration engines & documentation depth — +1 by
  substance: this fork (IDC APIs integrated into supported patient
  management systems).
- Device connectivity / sync pipelines — +1 by substance: this
  fork (device initialization; device + mobile application
  transferring sleep study data to the platform).
- Multi-device native apps — +1 by substance: this fork (the
  proprietary patient-facing mobile application; a data-collection
  companion, named here so the substance is on record).

Extended families carried from the Group 18 union (as enlarged),
not implemented — the category's registered gap list:

- Clinical decision support (0 standalone claims category-wide).
- Medical claims adjudication engine (eligibility/coverage
  *records* are Core; adjudication is not).
- AI/ML models & personalization engines.
- Automation / workflow engines.
- Survey instruments depth.
- Patient engagement channels & content.
- Telehealth media engine (gap with a claimant at L2 — GTS
  VirtualHealth; at this tier the absence survives and this fork
  is not a claimant).
- Hosting platform (a platform-layer property — Dexcom's Google
  Cloud / GKE prose at L2; never a health function).
- Store-and-forward clinical data service (registered by the L2
  additions — GTS's labs/images/clinical-data exchange).
- Medical coding engine (computer-assisted coding) (L2 additions
  — Solventum).
- Grouper / classification & reimbursement content services (L2
  additions — Solventum).
- Clinical documentation integrity (CDI) tooling (L2 additions —
  Solventum).
- Diagnostic report generation engine (L2 additions — Somnoware;
  distinct from this fork's results *collection*: generation of a
  diagnostic report is not asserted in this fork's words).
- Therapy progress & risk-profile console (L2 additions —
  Somnoware).

Platform layer (gap-listed, never implied closed): multi-tenancy
(the build is a single-tenant reference deployment); encryption at
rest (deployment layer); TLS only when a certificate is
configured; demo identities are hooks, not an IdP — IA-2 stays
with the embedding organization. The hosting/delivery platform is
the deployment layer itself, not a function of this build.

**Privacy note:** this build stores records and opaque
caller-supplied references only — no real names, patient
identifiers, diagnoses, sleep study data, or test results exist in
any entity shape, and measurement records are caller-recorded
administration values, never device payloads.
