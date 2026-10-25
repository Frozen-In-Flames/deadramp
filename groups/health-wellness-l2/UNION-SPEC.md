# Union Spec — Health & Wellness, CMMC L2 (DeadRamp Phase 2, Group 18)

The merged functional spec for the Health & Wellness sibling group at
the L2 tier: **5 forks, all FedRAMP Moderate**, reconciled zero-diff
(`specs/specs.json` ↔ `forks.json` category "Health & Wellness" +
`cmmc_tier` "L2" ↔ MAP.md "Health & Wellness — L2 (5)").

| Fork | Vendor — Product | Status | Deployment |
|---|---|---|---|
| FR2000174962 | Abbott, Inc. — LibreView for US Government | FedRAMP Certified | Government Community Cloud |
| FR2135180018 | CuraPatient — Composite Apps/ CuraPatient | Agency Authorization In Process | Government Community Cloud |
| FR2508262726 | Dexcom Inc. — Dexcom Clarity for Government | FedRAMP Certified | Public Cloud |
| FR2309381948 | Elekta Solutions — Elekta ProKnow Federal | FedRAMP Certified | Public Cloud |
| FR2210851632 | GetWellNetwork — GetWellNetwork  - Get Well Anywhere - Federal | FedRAMP Certified | Government Community Cloud |

All five are SaaS. This is a heterogeneous, thinly described group.
The source's "Health & Wellness" category collects a glucose-data
review tool for diabetes care (Abbott LibreView), a second glucose /
CGM data tool with clinic-account linking and receiver upload (Dexcom
Clarity), a clinical-metrics scorecard tool (Elekta ProKnow), an
AI-powered operations platform whose health surface is claims
processing and patient engagement (CuraPatient), and a digital
patient-engagement platform that guides patients through a care
journey (GetWellNetwork). There is no single product they all are.
What the claim counts below prove is a **records substrate**:
participants held in a registry under opaque references, programs
(clinics / care journeys) held in a registry, participants enrolled,
measurement and outcome values recorded against metrics, care/wellness
plans recorded with derived completion status, activities and
appointments recorded, eligibility/coverage recorded under opaque
plan references, and population scorecards aggregated over those
records. The merged build implements that substrate; each vendor's
clinical, device, AI, and workflow engines on top of it are Extended
functions, named in the long tail. The privacy discipline (section
after the Core) is constitutive, not decorative: the substrate holds
records and opaque references only, and anything that would hold real
clinical content is Extended by construction.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against an 11-family taxonomy defined from this category's
descriptions (the coordinator's 12th candidate family,
`account_linking`, was merged into `device_connectivity` — see
correction 11 in `scratch/ARTIFACTS.md`). A family is claimed only
when the offering's own description contains matching text; the first
matching sentence is stored in `specs/specs.json` as evidence, so
every claim is auditable, and the extractor verifies programmatically
that every evidence string is a verbatim sentence of its fork's
description (**0 violations**). **19 claims survived.** Wording-
artifact corrections are itemized below and in `scratch/ARTIFACTS.md`
(36 broad first-pass hits → 19: 16 false hits removed, 1 family
merged, 2 kept claims evidence-re-based). **No fork has zero claims**,
but the floor is low because the descriptions are short (Elekta's is
two sentences): per-fork claim counts: CuraPatient 5, GetWellNetwork
5, Dexcom Clarity for Government 4, Elekta ProKnow Federal 3,
LibreView for US Government 2. Counts are therefore a **floor**, not
a ceiling, on what these products do — no conclusion about the real
LibreView should be drawn from its 2 tags.

### Wording-artifact corrections (itemized; full text in `scratch/ARTIFACTS.md`)

1. **analysis_reporting — CuraPatient REMOVED.** Bare `review` matched
   "completed the FedRAMP review process" — accreditation prose, the
   regulator reviewing the vendor. CuraPatient's whole first
   paragraph (FedRAMP review, "highest security standards",
   "protecting sensitive data") earns **no** function tags.
2. **measurement_data — CuraPatient REMOVED.** Bare `data` matched
   "protecting sensitive data" — security posture, not measurements.
3. **care_guidance — CuraPatient and Abbott REMOVED.** Bare `support`
   matched "ready to support agency requests" (CuraPatient) and "to
   support effective diabetes management" / "supported by Abbott"
   (Abbott) — neither is care-journey guidance.
4. **patient_engagement — Abbott and Elekta REMOVED.** Bare `patient`
   matched patients-as-users (Abbott) and patients-as-scorecard-
   subjects (Elekta). The family requires engagement/survey wording.
5. **device_connectivity — Abbott and CuraPatient REMOVED.** Bare
   `device` matched Abbott's manufacturer context ("a major
   manufacturer of glucose monitoring devices" — Abbott makes
   devices; the sentence claims no connection or upload) and
   CuraPatient's multi-device *access* sentence (a different family).
6. **automation — Dexcom REMOVED.** Broad `auto\w+` matched GKE
   "Autopilot" — a cloud deployment feature, not task automation.
7. **ai_platform — Dexcom and GetWellNetwork REMOVED.** The substring
   `ai` matched "av**ai**lable" and "entert**ai**n" (the Group 13
   "C**api**tal" artifact class). Only CuraPatient's full "Artificial
   Intelligence (AI) powered" phrase claims.
8. **hosting_platform — CuraPatient and GetWellNetwork REMOVED.**
   Bare `platform` is a product noun ("digital platform", "patient
   engagement platform"), not a hosting claim. Dexcom's Google
   Cloud / GKE deployment prose still claims.
9. **access_control / audit guard families — DROPPED (0 true claims).**
   Broad `secure|security|authorized|access` hit only posture
   adjectives (CuraPatient) and a "secure code" for account linking
   (Dexcom); `audit` hit 0/5. No fork claims RBAC or audit in
   functional terms, so no tag is issued; both enter the Core as
   baseline substrate, carried-not-claimed (see Core notes 9–10).
10. **account_linking — MERGED into device_connectivity.** Dexcom's
    secure-code clinic-account link and its receiver-data upload are
    one link-then-upload pipeline; one family reads cleaner than two
    one-sentence families.
11. **Evidence re-based (kept):** Dexcom's measurement claim rests on
    "highlighting glucose patterns…", not on sentence 1 naming the
    parent CGM system; CuraPatient's engagement claim rests on its
    core-functionalities sentence, not on the substring "Patient"
    inside the vendor's own name in the FedRAMP paragraph.
12. **Abbott's trademark sentence** ("Trademarks are the property of
    their respective owners") carries no tags.

Reviewed and **kept, with caveats**: Elekta's claims claim rests on
scorecards that "justify reimbursement" — reimbursement justification,
not adjudication (the Core holds coverage *records*; adjudication is
Extended). CuraPatient's integration claim rests on "integration with
client systems" — it does not name EMR/EHR, so the family label is
"EMR / client-system integration" (GetWell names EMR explicitly).
Dexcom's "help providers make diabetes management decisions" is
decision-support flavour around its analysis claim, not a clinical
decision-support claim. GetWell's "EMR documentation" is work being
automated, not integration. GetWell's "entertain" is not tagged.

## Function ranking — all 5 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 3 | Measurement & device data records (glucose / CGM / clinical metrics) | **Core** — measurement/outcome records |
| 1 | 3 | Review, analysis, patterns/trends/statistics & scorecards | **Core** — population scorecard reporting over the records; analysis engines Extended |
| 3 | 2 | Patient engagement & surveys | Extended — engagement/survey engines; engagement is a program/plan surface over substrate records |
| 3 | 2 | Medical claims processing & reimbursement | Extended — adjudication engine; eligibility/coverage records are Core substrate |
| 3 | 2 | EMR / client-system integration | Extended — integration engines; the substrate's own API is its own design |
| 3 | 2 | Multi-device / web / mobile access | Platform note — access surface, not a records function |
| 7 | 1 | Care-journey guidance, education & navigation | Extended — guidance/personalization engines; plan & activity records are Core |
| 7 | 1 | AI-powered platform claims | Extended — AI/ML models, not substrate |
| 7 | 1 | Automated guidance / task automation | Extended — automation/workflow engines |
| 7 | 1 | Device data connection & upload (incl. secure-code account linking) | Extended — device sync pipelines; measurement records they would deliver are Core |
| 7 | 1 | Cloud hosting / deployment claims | Platform note — deployment prose (Google Cloud / GKE); single-tenant reference deployment |

**Named absences (0/5, checked with broad patterns — findings, not
oversights):** explicit **access control / RBAC** wording and **audit
logging** in descriptive text (both Core as baseline only, flagged);
**telehealth media** (no description claims video/virtual visits);
standalone **clinical decision support** product claims (Dexcom's
decision wording is flavour around analysis — see caveats).

## The Core — what the merged build implements (10 functions)

The shared substrate the counts support, plus two baseline hooks
flagged where the counts do not:

1. **Participant registry** — participants (patients, caregivers,
   professionals, CGM users in the siblings' vocabularies) as records
   keyed by an **opaque, caller-supplied reference only**
   (`participant_ref`). No names, contact details, dates of birth, or
   any other identifier fields exist in the shape. *Support: every
   claimed function in the group is predicated on a participant —
   Abbott's "patients, caregivers and healthcare professionals",
   Dexcom's "CGM Users" and "providers", Elekta's "individual
   patients", GetWell's "each patient". The registry is the record
   form those subjects presuppose.*
2. **Program registry** — programs (clinics, care journeys, scorecard
   populations) as records. *Support: Dexcom's "clinic account",
   GetWell's care journey "from pre-procedure preparation … to
   post-discharge recovery", Elekta's populations, CuraPatient's
   client operations.*
3. **Enrollments with derived status** — enrollment/registration
   records binding a participant to a program, with a derived status
   (enrolled / completed / overdue) computed deterministically from
   the participant's plan records for that program (contract §6).
   *Support: the substrate form presupposed by Dexcom's clinic-account
   connection, GetWell's journey enrolment, and Elekta's individual-
   patient scorecards. Flag: no description uses the word
   "enrollment"; the record is the minimal structure those claimed
   functions presuppose, included on that basis and flagged here.*
4. **Measurement / outcome records** — numeric value + unit + metric
   name + date, per participant, optionally per program. **No
   diagnosis fields, no free-text clinical notes; unknown or extra
   fields are refused at the boundary** (contract §5). *Support:
   measurement_data 3/5 (Abbott historical glucose meter data,
   Dexcom glucose patterns / receiver data, Elekta clinical
   metrics).*
5. **Care / wellness plan records with derived status** — plan
   records with a due date and an optional completion date; status
   (current / overdue / completed) derived deterministically.
   *Support: care_guidance 1/5 (GetWell's guidance through the care
   journey) and measurement_data 3/5 (objectives in Elekta's
   scorecards — "clinical metrics and their objectives" — are plan-
   shaped records). The due-date + derivation triple is the minimal
   record structure a guided journey with objectives presupposes;
   flagged as substrate logic, as in Group 13's compliance function.*
6. **Activity / appointment records** — scheduled activities and
   appointments bound to a participant and optionally a program, with
   a lifecycle state. *Support: GetWell's journey stages (pre-
   procedure preparation, ED waiting room, inpatient, post-discharge)
   and Dexcom's "during visits, providers can upload…" — visits and
   journey stages are activity-shaped records; the records are Core,
   any scheduling/visit engine is not claimed and not specified.*
7. **Eligibility / coverage records** — per-participant coverage
   records holding an **opaque plan reference only** (`plan_ref`),
   with coverage dates and a derived current status (upcoming /
   current / ended). No insurer names, member numbers, or benefit
   details exist in the shape. *Support: claims_processing 2/5
   (CuraPatient medical claims processing, Elekta reimbursement
   justification) — claims and reimbursement presuppose a coverage
   record to be checked against; the Core holds the record, the
   claims engine is Extended.*
8. **Population scorecard reporting** — aggregates per metric (count,
   min, max, mean) and per derived-status over the substrate records,
   group-wide and per program, plus per-participant measurement
   listing (the individual-scorecard view). *Support:
   analysis_reporting 3/5 (Abbott review/analysis, Dexcom patterns/
   trends/statistics, Elekta scorecards "for individual patients and
   across populations" — the group's own phrasing for exactly this
   split). The Core is aggregation over substrate records; pattern/
   trend detection and scorecard presentation engines are Extended.*
9. **Access control (RBAC)** — role-based access in
   admin/clinician/member/auditor roles, enforced before any state
   change. *Support: 0/5 explicit descriptive claims — stated
   plainly. RBAC is Core because the L2/Moderate baseline requires it
   (AC/IA families, traceability below) and because health records
   presuppose differentiated clinician/member access; it is
   **baseline-carried, not claimed** (precedent: cybersecurity-l1
   UNION-SPEC).*
10. **Audit log** — append-only audit of every mutation and denied
    attempt. *Support: 0/5 descriptive claims. Included solely as an
    L2/Moderate baseline hook (AU family), **carried-not-claimed**,
    exactly as in sibling groups, and flagged here so no reader
    mistakes it for a claimed vendor function.*

## Privacy discipline

This group handles health-adjacent records, so the substrate's field
discipline is part of the spec, not an implementation nicety:

- **Records + opaque references only.** Participants are keyed by a
  caller-supplied opaque `participant_ref`; coverage by an opaque
  `plan_ref`. The substrate never stores a real name, address, phone,
  email, date of birth, SSN, member/insurance number, or any other
  direct identifier — those fields **do not exist** in any entity
  shape in the contract.
- **No diagnosis, no clinical free text.** Measurement records hold
  a metric name, a numeric value, a unit, and a date — nothing else.
  No entity has a diagnosis field, a notes field, or any free-text
  clinical field. (Deliberate contrast with Group 13, whose progress
  records carried a `note`: this package has **no** note field
  anywhere.)
- **Refusal at the boundary.** Store methods accept only the named
  fields in the contract; the HTTP layer rejects any JSON key outside
  an endpoint's named field list with `ValidationError` (HTTP 400),
  so a caller cannot smuggle a diagnosis, a note, or an identifier
  into a record by adding a field.
- **Member scope.** A member-role caller can read only records whose
  participant's `participant_ref` equals the caller's user name —
  the same own-records scoping Group 13 enforced for learners.
- **Anything clinical is Extended.** Diagnosis content, clinical
  notes or documentation, decision support, and any real PHI belong
  to the Extended engines in the long tail, which would each need
  their own authorization basis; the merged build neither stores nor
  transmits them.

## Long tail — Extended, by name

- **Clinical decision support** — 0 standalone claims. Dexcom's "help
  providers make diabetes management decisions" is analysis flavour;
  a CDS engine (recommendations, alerts, order sets) is a vendor
  clinical system, not substrate.
- **EMR/EHR integration engines & documentation depth** —
  emr_integration 2/5 (GetWell EMR systems, CuraPatient client
  systems). HL7/FHIR pipelines, EMR documentation generation
  (GetWell's automated "EMR documentation" is documentation depth,
  not a records function), and sync semantics are Extended; the
  substrate exposes only its own API.
- **Medical claims adjudication engine** — claims_processing 2/5
  (CuraPatient claims processing, Elekta reimbursement
  justification). Adjudication, coding, pricing, and reimbursement
  workflows are Extended; eligibility/coverage *records* are Core.
- **Device connectivity / sync pipelines** — device_connectivity 1/5
  (Dexcom, merged account_linking included). Receiver protocols,
  secure-code linking flows, and sync/retry pipelines are Extended;
  the measurement records they deliver are Core.
- **AI/ML models & personalization engines** — ai_platform 1/5
  (CuraPatient). Model training/inference and GetWell's
  "personalized, individualized" tailoring engines are Extended.
- **Automation / workflow engines** — automation 1/5 (GetWell
  automated guidance, automated clinician tasks). Rule engines and
  task-routing are Extended; plan/activity records are Core.
- **Survey instruments depth** — patient_engagement 2/5 includes
  GetWell's "survey patients" wording. Questionnaires, branching
  instruments, and response analytics beyond a plan/activity record
  are Extended.
- **Patient engagement channels & content** — patient_engagement 2/5,
  care_guidance 1/5: engagement campaigns, education/entertainment
  content delivery, and navigation services are vendor surfaces over
  the substrate's plan and activity records.
- **Telehealth media** — **0 claims (named absence).** No description
  claims video visits, virtual visits, or any media channel.
- **Multi-device native apps** — multi_device_access 2/5 (CuraPatient
  native iOS/Android + responsive web; GetWell web and mobile). A
  platform/access property, not a records function; the merged build
  is a single HTTP service and says so.
- **Hosting platform** — hosting_platform 1/5 (Dexcom's Google Cloud
  organization, multi-zone redundancy, private GKE Autopilot
  clusters). A platform-layer property, never a health function; the
  merged build is a single-tenant reference deployment and says so.

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes no
tier (Merge Rules 1–2: union of baselines, highest tier wins — here
all parents already sit at the same tier).

| Core function | Control families | How the build answers |
|---|---|---|
| Participant registry (opaque refs) | AC-2, AU-2, SI-12 | Participants exist only as explicit records under caller-supplied opaque references; no identifier fields exist to leak |
| Program registry | CM-6, SI-12 | Programs are explicit, configuration-controlled records; nothing is offered that is not registered |
| Enrollments with derived status | AC-2, AU-2, CA-7 | Enrollment is an explicit, auditable record; its status is derived deterministically and is reviewable |
| Measurement / outcome records | AU-2, AU-3, SI-10 | Every measurement leaves a validated record (named fields only; extra fields refused); inputs are validated before any record exists |
| Care/wellness plan records | AU-6, CA-7, CM-6 | Plan status is derived deterministically from due/completion dates; derivation is queryable and reviewable |
| Activity / appointment records | AU-2, CM-6 | Activities are explicit records bound to participants and programs, with auditable state changes |
| Eligibility / coverage records | AU-2, SI-12 | Coverage exists only as a record under an opaque plan reference, with derived status reviewable as of any date |
| Population scorecard reporting | AU-6, CA-7 | Reports aggregate the substrate records only (per metric, per program); no side-channel data |
| RBAC (admin/clinician/member/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; identity itself is supplied by the embedding organization (see caveat) |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** FedRAMP authorizes
PRODUCTS, CMMC certifies ORGANIZATIONS. A FedRAMP impact level is a
statement about a cloud service offering; a CMMC level is a statement
about a company and how it handles FCI/CUI. The L2 / FedRAMP Moderate
equivalence used here is a **planning/matching equivalence only**: it
says these forks sit at comparable assurance weight so they can be
grouped and merged consistently. It does **not** claim that a
FedRAMP-authorized product confers CMMC certification on anyone, that
a CMMC-certified organization holds a FedRAMP authorization, or that
either regime accepts the other as evidence. This traceability is a
planning mapping; the merged build is not a FedRAMP authorization and
confers no CMMC certification.

Standing platform notes (every group): demo identities are hooks, not
an IdP — IA-2 stays with the embedding organization; encryption at
rest is deployment-layer; TLS applies when a certificate is
configured. Multi-tenancy and cloud hosting, named in prose by
Dexcom, are likewise deployment properties: the merged build is a
single-tenant reference deployment and says so.

## Implementation contract (for the build worker)

Mirror `groups/education-training-l2/src/learn/` in structure and
conventions; change only what this contract says. Standard library
only. Package name: **`health`**, at
`groups/health-wellness-l2/src/health/`.

### 1. Module layout

```
src/health/
  __init__.py    # docstring + __version__ = "0.1.0" + __all__ = ["__version__"]
  errors.py      # HealthError base; ValidationError, NotFoundError, PermissionDenied
  access.py      # ROLES, ACTIONS, PERMISSIONS, User dataclass, permissions_for/can/require
  audit.py       # AuditLog (append-only, optional JSONL path) — same semantics as learn's
  store.py       # HealthStore — all state, validation, derivation, reporting
  service.py     # USERS registry, HTTP handler, routing, make_server
  __main__.py    # CLI: python -m health serve
```

Error semantics (as in `learn`): every deliberately raised error
derives from `HealthError`; `ValidationError` = input failed
validation, nothing changed; `NotFoundError` = requested object does
not exist; `PermissionDenied` = actor may not perform the action.

### 2. Demo users and roles

Demo registry in `service.py` (`USERS`, also exported as
`DEMO_USERS`), mirroring Group 13's four demo identities with this
group's role names substituted (instructor→clinician,
learner→member):

- `alice` — `admin`
- `bob` — `clinician`
- `carol` — `member`
- `dana` — `auditor`

Callers authenticate with `X-User` / `X-Role` headers checked against
the registry; an unknown user or a role mismatch is rejected with
401. These are documented demo identities, not an identity provider —
production identity belongs to the embedding organization.

### 3. Permission matrix (`access.py`)

Actions (16):
`participant_read`, `participant_write`, `program_read`,
`program_write`, `enrollment_read`, `enrollment_write`,
`measurement_read`, `measurement_write`, `plan_read`, `plan_write`,
`activity_read`, `activity_write`, `eligibility_read`,
`eligibility_write`, `report_read`, `audit_read`.

Record reads = the 7 `*_read` actions excluding `report_read` /
`audit_read` (i.e. participant, program, enrollment, measurement,
plan, activity, eligibility reads).

| Role | Permissions |
|---|---|
| `admin` | all 16 actions |
| `clinician` | all 7 record reads + `enrollment_write`, `measurement_write`, `plan_write`, `activity_write` + `report_read` |
| `member` | the 7 record reads only (own-participant scope enforced in the store, §5) |
| `auditor` | the 7 record reads + `report_read` + `audit_read`; no writes |

`require(user, action)` raises `PermissionDenied` for a `None` user,
an unknown role, or an action outside the role's set — same semantics
as `learn/access.py`, including the plain-string-actor convention:
store methods accept `User` objects; a plain string carries identity
for provenance/audit but no role, so store-level enforcement is
skipped for it (`_maybe_require` / `_require_actor` helpers as in
`learn/store.py`) and the service layer enforces.

### 4. Audit (`audit.py`)

Identical semantics to `learn/audit.py`: entries are dicts
`{ts, actor, action, target, details}` (`ts` = UTC ISO-8601), only
ever appended (no update/delete API), optionally mirrored as JSONL to
a path (existing file is loaded on construction; malformed lines are
skipped). The store audits every mutation and every report/scorecard
read; the service layer audits only denied attempts (401/403, action
suffixed `":denied"`) and `audit_read`.

### 5. Entity shapes (`store.py`) — field lists are EXACT

Store methods take **only the named parameters below**. The HTTP
layer rejects any JSON body key outside the endpoint's named field
list with `ValidationError` (HTTP 400) before calling the store —
this is the boundary at which extra fields (a `diagnosis`, a `note`,
a `name`, a `dob`, anything) are refused. No entity has a free-text
clinical field or a note field. All records also carry
`created_by` (actor name) and `created_utc` (UTC ISO-8601), assigned
by the store, never caller-supplied. IDs are store-assigned with the
prefixes shown, sequential per prefix.

Common validation: string fields named below as non-empty must be
`str` and non-empty after no transformation (mirror
`_validate_non_empty`); dates are ISO `YYYY-MM-DD` validated as real
calendar dates; datetimes are ISO-8601 parsed with
`datetime.fromisoformat` (a trailing `Z` is accepted); referencing a
non-existent program/participant/enrollment id raises
`NotFoundError`.

1. **Participant** — prefix `par`.
   `create_participant(participant_ref, actor, kind="patient")`.
   Fields: `id`, `participant_ref` (non-empty str, **unique** — a
   second create with the same ref raises `ValidationError`),
   `kind` ∈ `("patient", "caregiver", "professional")`,
   `created_by`, `created_utc`. No other fields exist.
2. **Program** — prefix `prg`.
   `create_program(title, actor, kind="program", code=None, description="")`.
   Fields: `id`, `title` (non-empty str), `kind` ∈ `("program",
   "clinic", "care_journey")`, `code` (str or `None`), `description`
   (str; a program description, never participant data),
   `created_by`, `created_utc`.
3. **Enrollment** — prefix `enr`.
   `create_enrollment(participant_id, program_id, actor, kind="enrollment")`.
   Fields: `id`, `participant_id`, `program_id`, `kind` ∈
   `("enrollment", "registration")`, `status` = `"enrolled"` (stored;
   never set directly), `created_by`, `created_utc`. A duplicate
   active enrollment (same participant + program + kind with stored
   status `"enrolled"`) raises `ValidationError`. Reads return the
   stored fields **plus** `derived_status` (§6).
4. **Measurement** — prefix `msr`.
   `record_measurement(participant_id, metric_name, value, unit, recorded_on, actor, program_id=None)`.
   Fields: `id`, `participant_id`, `program_id` (id or `None`),
   `metric_name` (non-empty str), `value` (int or float; `bool` is
   rejected; must be finite — NaN/inf raise `ValidationError`),
   `unit` (non-empty str), `recorded_on` (ISO date str),
   `created_by`, `created_utc`. **No other fields — in particular no
   diagnosis, no note.**
5. **Plan record** — prefix `pln`.
   `create_plan(participant_id, program_id, title, due_date, actor, kind="care_plan")`;
   `complete_plan(plan_id, completed_on, actor)`.
   Fields: `id`, `participant_id`, `program_id`, `title` (non-empty
   str), `kind` ∈ `("care_plan", "wellness_plan", "education")`,
   `due_date` (ISO date), `completed_on` (ISO date or `None`;
   initially `None`; `complete_plan` sets it — completing an already
   completed plan raises `ValidationError`; `completed_on` may be
   any valid date, including before `due_date`), `created_by`,
   `created_utc`. Reads return the stored fields **plus**
   `derived_status` (§6).
6. **Activity / appointment** — prefix `act`.
   `create_activity(participant_id, title, starts_at, actor, program_id=None, ends_at=None, kind="appointment")`;
   `set_activity_state(activity_id, state, actor)`.
   Fields: `id`, `participant_id`, `program_id` (id or `None`),
   `title` (non-empty str), `kind` ∈ `("appointment", "activity",
   "session")`, `starts_at` (ISO datetime str), `ends_at` (ISO
   datetime str or `None`; if present must be ≥ `starts_at`, else
   `ValidationError`), `state` ∈ `("scheduled", "completed",
   "cancelled")` (initially `"scheduled"`), `created_by`,
   `created_utc`.
7. **Eligibility / coverage** — prefix `elg`.
   `create_eligibility(participant_id, plan_ref, coverage_start, actor, program_id=None, coverage_end=None)`.
   Fields: `id`, `participant_id`, `program_id` (id or `None`),
   `plan_ref` (non-empty opaque str), `coverage_start` (ISO date),
   `coverage_end` (ISO date or `None`; if present must be ≥
   `coverage_start`), `created_by`, `created_utc`. Reads return the
   stored fields **plus** `derived_status` (§6). No insurer, member
   number, or benefit fields exist.

Getters/listers mirror `learn`: `get_<entity>(id, actor=None)`,
`list_<entity>s(actor=None, **filters)` with filters —
enrollments: `participant_id`, `program_id`; measurements:
`participant_id`, `program_id`, `metric_name`; plans:
`participant_id`, `program_id`; activities: `participant_id`,
`program_id`; eligibility: `participant_id`. Lists are sorted by
numeric id. Getters raise `NotFoundError` for unknown ids.

**Member scope** (store-level, mirroring `learn`'s learner scope):
if the actor is a `User` with role `member`, the actor may read only
records whose participant's `participant_ref` equals the actor's user
name. For participant records themselves, the record's own
`participant_ref` is compared. A scoped `get_*` on another
participant's record raises `PermissionDenied`; scoped `list_*`
silently excludes other participants' records, and passing a
`participant_id` filter for another participant raises
`PermissionDenied`. Programs are registry records and are readable
by all roles without scoping.

### 6. Derived-status rules (deterministic; `as_of` is an ISO date, default = today UTC)

- **Plan:** `completed` if `completed_on` is not `None`; else
  `overdue` if `as_of > due_date`; else `current`.
- **Eligibility:** `ended` if `coverage_end` is not `None` and
  `as_of > coverage_end`; else `upcoming` if `as_of <
  coverage_start`; else `current`.
- **Enrollment:** computed from the participant's plan records for
  that enrollment's program, each derived as above with the same
  `as_of`: `overdue` if any such plan is `overdue`; else `completed`
  if any such plan is `completed`; else `enrolled`. (Precedence:
  overdue > completed > enrolled.)
- Views that carry a derived status accept `as_of=None`:
  `get_enrollment(id, actor=None, as_of=None)`,
  `list_enrollments(..., as_of=None)`, `get_plan` / `list_plans`
  likewise, `get_eligibility` / `list_eligibilities` likewise, plus
  `eligibility_status(eligibility_id, actor=None, as_of=None)`
  returning `{"id": ..., "derived_status": ...}`.

### 7. Reporting (`store.report`, `store.scorecard`)

`report(actor, as_of=None)` — action `report_read`. Returns exactly:
`as_of` (ISO date), `participants`, `programs`, `enrollments`
(counts), `measurements` (count), `measurements_by_metric` =
`{metric_name: {"count": n, "min": v, "max": v, "mean": sum/n}}`
over all measurements, `plans` (count), `plans_by_status` =
`{"current": n, "overdue": n, "completed": n}` (derived at `as_of`),
`activities` (count), `activities_by_state` = `{"scheduled": n,
"completed": n, "cancelled": n}`, `eligibility` (count),
`eligibility_by_status` = `{"upcoming": n, "current": n, "ended":
n}` (derived at `as_of`), `enrollments_by_program` =
`{program_id: n}`.

`scorecard(program_id, actor, as_of=None)` — action `report_read`;
unknown program raises `NotFoundError`. Returns exactly:
`program_id`, `as_of`, `participants` (distinct participants with at
least one measurement or plan in this program), `measurements`
(count in program), `measurements_by_metric` (same aggregate shape,
program-scoped), `plans` (count in program), `plans_by_status`
(same shape, program-scoped).

Both audit the read (`report` / `scorecard` actions).

### 8. HTTP endpoints (`service.py`)

Same handler conventions as `learn/service.py`: JSON bodies, errors
as `{"error": msg}` with 400 (validation) / 401 (auth) / 403
(permission) / 404 (not found), no stack traces, `GET /health` →
200 `{"status": "ok"}` without auth. Creates return 201, all other
successes 200. Unknown JSON keys in any POST body → 400 (see §5).
List responses wrap results: `{"participants": [...]}` etc.

| Method & path | Action | Body / params → result |
|---|---|---|
| `GET /health` | — | `{"status": "ok"}` |
| `GET /audit` | `audit_read` | `{"entries": [...]}` |
| `GET /report?as_of=` | `report_read` | `store.report(...)` |
| `GET /scorecard/{program_id}?as_of=` | `report_read` | `store.scorecard(...)` |
| `POST /participants` | `participant_write` | body `{participant_ref, kind?}` → 201 participant |
| `GET /participants` | `participant_read` | `{"participants": [...]}` |
| `GET /participants/{id}` | `participant_read` | participant |
| `POST /programs` | `program_write` | body `{title, kind?, code?, description?}` → 201 program |
| `GET /programs` | `program_read` | `{"programs": [...]}` |
| `GET /programs/{id}` | `program_read` | program |
| `POST /enrollments` | `enrollment_write` | body `{participant_id, program_id, kind?}` → 201 enrollment view |
| `GET /enrollments?participant_id=&program_id=&as_of=` | `enrollment_read` | `{"enrollments": [...]}` |
| `GET /enrollments/{id}?as_of=` | `enrollment_read` | enrollment view |
| `POST /measurements` | `measurement_write` | body `{participant_id, metric_name, value, unit, recorded_on, program_id?}` → 201 measurement |
| `GET /measurements?participant_id=&program_id=&metric_name=` | `measurement_read` | `{"measurements": [...]}` |
| `GET /measurements/{id}` | `measurement_read` | measurement |
| `POST /plans` | `plan_write` | body `{participant_id, program_id, title, due_date, kind?}` → 201 plan view |
| `GET /plans?participant_id=&program_id=&as_of=` | `plan_read` | `{"plans": [...]}` |
| `GET /plans/{id}?as_of=` | `plan_read` | plan view |
| `POST /plans/{id}/complete` | `plan_write` | body `{completed_on}` → 200 plan view |
| `POST /activities` | `activity_write` | body `{participant_id, title, starts_at, program_id?, ends_at?, kind?}` → 201 activity |
| `GET /activities?participant_id=&program_id=` | `activity_read` | `{"activities": [...]}` |
| `GET /activities/{id}` | `activity_read` | activity |
| `POST /activities/{id}/state` | `activity_write` | body `{state}` → 200 activity |
| `POST /eligibility` | `eligibility_write` | body `{participant_id, plan_ref, coverage_start, program_id?, coverage_end?}` → 201 eligibility view |
| `GET /eligibility?participant_id=&as_of=` | `eligibility_read` | `{"eligibility": [...]}` |
| `GET /eligibility/{id}?as_of=` | `eligibility_read` | eligibility view |
| `GET /eligibility/{id}/status?as_of=` | `eligibility_read` | `{"id": ..., "derived_status": ...}` |

There is no DELETE or PATCH route and no audit-mutation route, as in
`learn` (its `do_DELETE`/`do_PATCH` fall through to the same 404
routing).

### 9. CLI (`__main__.py`)

`python -m health serve [--host 127.0.0.1] [--port 8792]
[--audit-log PATH] [--certfile PEM --keyfile PEM]` — mirroring
`learn/__main__.py`: no subcommand → print help, return 2;
`--certfile`/`--keyfile` must be given together (parser error
otherwise); when both are given, serve over TLS via the standard
library `ssl` module. On startup print exactly:
`health service listening on <scheme>://<host>:<port> (demo users: alice=admin, bob=clinician, carol=member, dana=auditor)`.

## Coverage statement (for this spec batch)

- Forks spec'd: **5 / 5**, each with evidenced claims (19 total).
- Taxonomy: **11 function families** (12th candidate,
  `account_linking`, merged into `device_connectivity`); 3 further
  families checked and found at **0/5** (access control in text,
  audit in text, telehealth media) and recorded as named absences /
  baseline-carried rather than dropped silently.
- Core specified: **10 functions** (8 claim-supported or
  substrate-presupposed and flagged as such, 2 baseline-only —
  RBAC and audit — flagged carried-not-claimed), each with its
  justification stated inline.
- Extended / gap list: 11 named items above. No implementation code
  in this batch — specs and union spec only.
