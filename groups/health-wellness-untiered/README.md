# Health & Wellness — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **3 untiered forks** of Health & Wellness
— census unit `untiered:Health & Wellness` in `../../remainder.json`.
**This is an untiered set, and that means something specific:**
every member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for these offerings, so
**tier stays null**: no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented control
claims; tier stays null in the registry until the source publishes
a baseline." The union contract is [`UNION-SPEC.md`](UNION-SPEC.md);
per-fork spec sheets are in [`specs/specs.json`](specs/specs.json),
each recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests.

The 3 forks were spec'd under the category's existing 11-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). That taxonomy was defined from the
founding five's glucose / CGM prose. Taxonomy-verbatim proof: the
extractor first reproduced the founding Health & Wellness L2
group's original shipped claim tables exactly — **5 of 5 forks, 19
of 19 claims, deep-equal** — before tagging this set. Result here:
**1 claim** across the set, **1 of 3 forks claiming at least
one**; the two zero-claim forks (Elvo, WellHive) are recorded under
Named absences in the union spec, not hidden or repaired.

The build implements the category's **ten-function substrate** —
the wellness records machinery every sibling's output presupposes —
carried **byte-identical** from the founding Health & Wellness L2
build (`../health-wellness-l2/src/health/`, 7 of 7 modules;
SHA-256 accounting below). The substrate is tier-independent
records code: the founding source contains no tier or baseline
machinery, so there was nothing tier-shaped to strip. Where the
founding contract's text says RBAC and the audit log are Core
because "the L2/Moderate baseline requires" them, read it here as
**baseline-neutral substrate**: at tier null they are carried as
the parent design carries them, claimed against no baseline.

## The 3 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2634047811 | 86Borders LLC | 86Borders ConnectAllCare | 1 |
| FR2633734921 | Elvo | Elvo | 0 |
| FR1825232355 | WellHive Holdings, LLC | WellHive | 0 |

In `forks.json` the set is mixed as filed: 86Borders and Elvo carry
the Health & Wellness category, and WellHive is filed
"Uncategorized (none in source)"; the census assigned all 3 to this
category from their own descriptions, and the spec sheets record
the assignment. Authorization statuses as recorded span Initial
Implementation (2) and FedRAMP In Process (1) — a status is record
data, not a claim.

## The 10 core functions

1. **Participant registry** — participants as records (`par-`)
   keyed by an **opaque, caller-supplied reference only**
   (`participant_ref`, unique). No names, contact details, dates of
   birth, or any other identifier fields exist in the shape.
2. **Program registry** — programs, clinics, and care journeys as
   records (`prg-`), configuration-controlled: nothing is offered
   that is not registered.
3. **Enrollments with derived status** — enrollment/registration
   records (`enr-`) binding a participant to a program; duplicate
   active enrollments are rejected. The stored status is always
   `enrolled`; reads add a **derived status** computed
   deterministically from the participant's plan records for that
   program (`overdue` if any is overdue, else `completed` if any is
   completed, else `enrolled`).
4. **Measurement / outcome records** — numeric value + unit +
   metric name + date (`msr-`), per participant, optionally per
   program. **No diagnosis fields, no free-text clinical notes**;
   unknown or extra fields are refused at the boundary (see Privacy
   discipline).
5. **Care / wellness plan records with derived status** — plan
   records (`pln-`) with a due date and an optional completion
   date. Status is **derived** at read time: `completed` when a
   completion date is recorded, `overdue` when `as_of` is after the
   due date, `current` otherwise.
6. **Activity / appointment records** — scheduled activities and
   appointments (`act-`) bound to a participant and optionally a
   program, with a lifecycle state (`scheduled` / `completed` /
   `cancelled`). Records only — no scheduling/visit engine.
7. **Eligibility / coverage records** — per-participant coverage
   records (`elg-`) holding an **opaque plan reference only**
   (`plan_ref`), with coverage dates and a **derived** current
   status (`upcoming` / `current` / `ended`). No insurer names,
   member numbers, or benefit details exist in the shape. Records
   only — no claims adjudication.
8. **Population scorecard reporting** — aggregates per metric
   (count, min, max, mean) and per derived status over the substrate
   records, group-wide (`report`) and per program (`scorecard`),
   plus per-participant measurement listing (the
   individual-scorecard view). Pattern/trend detection and
   scorecard presentation engines are Extended.
9. **RBAC** — `admin` / `clinician` / `member` / `auditor` roles
   with a permission matrix enforced before any state change, plus
   member scope: a member-role actor can only read records whose
   participant's `participant_ref` is their own user name.
   **Carried-not-claimed** in this set (0/3).
10. **Append-only audit log** — every mutation, every report /
    scorecard read, and every denied attempt recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence. There is no mutation or deletion API for audit
    entries. **Carried-not-claimed** in this set (0/3).

Claim support in this set, stated plainly (see `UNION-SPEC.md` for
the core-boundary decision): **no Core function is claim-supported
here** — the set's single claim is an Extended-disposition family
(patient engagement), and the substrate is carried whole because it
is the category's merged implementation, not because these three
forks' wording claims it. Malformed input is rejected with a
validation error and leaves the store completely unchanged (no
partial application, no id consumed). Ids are sequential per object
type: `par-`, `prg-`, `enr-`, `msr-`, `pln-`, `act-`, `elg-`.
Permission is checked before any state change or id allocation.
Dates are ISO strings (dates `YYYY-MM-DD`; activity times ISO-8601
datetimes); derived statuses take an explicit `as_of` date so they
never depend on the wall clock.

## Privacy discipline

This group handles health-adjacent records, so the substrate's
field discipline is part of the contract, not an implementation
nicety:

- **Records + opaque references only.** Participants are keyed by a
  caller-supplied opaque `participant_ref`; coverage by an opaque
  `plan_ref`. The substrate never stores a real name, address,
  phone, email, date of birth, SSN, member/insurance number, or any
  other direct identifier — those fields **do not exist** in any
  entity shape.
- **No diagnosis, no clinical free text.** Measurement records hold
  a metric name, a numeric value, a unit, and a date — nothing else.
  No entity has a diagnosis field, a notes field, or any free-text
  clinical field anywhere in this package.
- **Refusal at the boundary.** Store methods accept only the
  contract's named parameters; the HTTP layer rejects any JSON key
  outside an endpoint's named field list with `ValidationError`
  (HTTP 400) before calling the store, so a caller cannot smuggle a
  diagnosis, a note, or an identifier into a record by adding a
  field. The test suite asserts this explicitly (a `diagnosis` key
  on `POST /measurements` is refused and nothing is stored).
- **Member scope.** A member-role caller can read only records
  whose participant's `participant_ref` equals the caller's user
  name.
- **Anything clinical is Extended.** Diagnosis content, clinical
  notes or documentation, decision support, and any real PHI belong
  to the Extended engines in the long tail; the merged build neither
  stores nor transmits them. This build is **not a medical device
  and claims no FDA status**.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m health serve --host 127.0.0.1 --port 8792
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). On startup the service prints exactly:
`health service listening on <scheme>://<host>:<port> (demo users: alice=admin, bob=clinician, carol=member, dana=auditor)`.

As a library:

```python
import sys; sys.path.insert(0, "src")
from health.access import User
from health.audit import AuditLog
from health.store import HealthStore

audit = AuditLog()
store = HealthStore(audit=audit)
admin = User("alice", "admin"); clinician = User("bob", "clinician")
program = store.create_program("Diabetes Care", admin, code="DIA-101")
participant = store.create_participant("carol", admin)
store.create_enrollment(participant["id"], program["id"], clinician)
plan = store.create_plan(participant["id"], program["id"], "Daily checks", "2026-06-01", clinician)
print(store.get_plan(plan["id"], admin, as_of="2026-06-15")["derived_status"])
# 'overdue'
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role      | Permissions |
|---------|-----------|-------------|
| `alice` | admin     | all 16 actions |
| `bob`   | clinician | all 7 record reads + `enrollment_write`, `measurement_write`, `plan_write`, `activity_write` + `report_read` |
| `carol` | member    | the 7 record reads only, own-participant records only (member scope); no writes, no `report_read`, no `audit_read` |
| `dana`  | auditor   | all 7 record reads + `report_read` + `audit_read`; no writes |

Read actions: `participant_read`, `program_read`, `enrollment_read`,
`measurement_read`, `plan_read`, `activity_read`, `eligibility_read`
(the 7 record reads, member-scoped for members). Write actions:
`participant_write`, `program_write`, `eligibility_write` (admin
only); `enrollment_write`, `measurement_write`, `plan_write`,
`activity_write` (admin + clinician). `report_read` (admin,
clinician, auditor); `audit_read` (admin, auditor). Unknown roles
hold no permissions.

A permitted role performing a forbidden action gets 403; validation
failures (including unknown/extra JSON keys) get 400; unknown
objects get 404. Errors are always JSON `{"error": "..."}` and no
stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |
| GET | `/report?as_of=` | report_read | Population report over the records |
| GET | `/scorecard/{program_id}?as_of=` | report_read | Per-program scorecard |
| POST | `/participants` | participant_write | Body `{"participant_ref", "kind"?}` → 201 participant |
| GET | `/participants` | participant_read | `{"participants": [...]}` |
| GET | `/participants/{id}` | participant_read | One participant (member-scoped) |
| POST | `/programs` | program_write | Body `{"title", "kind"?, "code"?, "description"?}` → 201 program |
| GET | `/programs` | program_read | `{"programs": [...]}` |
| GET | `/programs/{id}` | program_read | One registry entry |
| POST | `/enrollments` | enrollment_write | Body `{"participant_id", "program_id", "kind"?}` → 201 enrollment view (with `derived_status`) |
| GET | `/enrollments?participant_id=&program_id=&as_of=` | enrollment_read | `{"enrollments": [...]}` |
| GET | `/enrollments/{id}?as_of=` | enrollment_read | One enrollment view |
| POST | `/measurements` | measurement_write | Body `{"participant_id", "metric_name", "value", "unit", "recorded_on", "program_id"?}` → 201 measurement |
| GET | `/measurements?participant_id=&program_id=&metric_name=` | measurement_read | `{"measurements": [...]}` |
| GET | `/measurements/{id}` | measurement_read | One measurement record |
| POST | `/plans` | plan_write | Body `{"participant_id", "program_id", "title", "due_date", "kind"?}` → 201 plan view |
| GET | `/plans?participant_id=&program_id=&as_of=` | plan_read | `{"plans": [...]}` |
| GET | `/plans/{id}?as_of=` | plan_read | One plan view |
| POST | `/plans/{id}/complete` | plan_write | Body `{"completed_on"}` → plan view |
| POST | `/activities` | activity_write | Body `{"participant_id", "title", "starts_at", "program_id"?, "ends_at"?, "kind"?}` → 201 activity |
| GET | `/activities?participant_id=&program_id=` | activity_read | `{"activities": [...]}` |
| GET | `/activities/{id}` | activity_read | One activity record |
| POST | `/activities/{id}/state` | activity_write | Body `{"state"}` → activity |
| POST | `/eligibility` | eligibility_write | Body `{"participant_id", "plan_ref", "coverage_start", "program_id"?, "coverage_end"?}` → 201 eligibility view |
| GET | `/eligibility?participant_id=&as_of=` | eligibility_read | `{"eligibility": [...]}` |
| GET | `/eligibility/{id}?as_of=` | eligibility_read | One eligibility view |
| GET | `/eligibility/{id}/status?as_of=` | eligibility_read | `{"id": ..., "derived_status": ...}` |

There is no DELETE or PATCH route and no audit-mutation route.

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**80 tests, OK** at delivery: the founding group's 67-test core
suite carried with the code (minus its additions module, which pins
a different census unit), plus 13 spec tests pinning this set
(exactly 3 sheets; membership exact against `remainder.json`; every
sheet's tier null / impact "Unknown"; registry fields and
descriptions verbatim; the literal claim table — 1 claim total,
Elvo and WellHive zero-claim; every claim's evidence verbatim;
near-miss pins; WellHive's Moderate prose pinned as moving no
tier). The founding group's signature derived-status mutation drill
was re-run in this tree — exactly 8 failures under the mutant, the
founding drill's identical set, store restored and SHA-256 verified
(see `tests/README.md`). A live smoke (`scratch/smoke.py`) drives
the store and the HTTP service end to end: program → participant →
enroll → measurement → plan with a past due date → derived status
`overdue` (plan and enrollment) → completion → derived status
`completed`; a member's admin action is denied at the store,
returns 403 over HTTP, and the denied attempt is audited.

## Byte-identity accounting

`src/health/` is carried from the founding group
`../health-wellness-l2/src/health/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `21016b6995fe9ec07f712896ef07e8a1481b38898d1f8a396e19a52cd9370efd` |
| `__main__.py` | `78778c6489fb3fcf582c362dbcb6f5f1bdda2efcba726cbde66b1799cc11e246` |
| `access.py` | `538865448f17a881d33bf4b26fc2ce3d983675ae51ea915085e2e7423369770c` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `41f500b71506c31e65498ec6dd9c8765dbf3c6e36e051ac5d8b12e486d2927c2` |
| `service.py` | `969052d3e044e0cb965416b02b6ea07b7cff4222a81c3dfb1e53af2048c9842f` |
| `store.py` | `c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711` |

The test suite is likewise carried (the founding suite minus its
additions module), with one labeling fix in
`tests/health_helpers.py` (its docstring now names this untiered
set instead of the founding group) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 3 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family in
from any baseline.

Documented by at least one fork in the set:

- **Privacy controls (NIST SP 800-53 Appendix J)** — 1 fork:
  WellHive asserts it is "also compliant with HIPAA and NIST
  800-53 Appendix J Privacy Controls." Recorded at
  compliance-assertion weight: the fork's own compliance claim
  about itself, not a function claim under the taxonomy and not
  evidence about any other fork.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AC, AT, AU, CA, CM, CP, IA, IR,
MA, MP, PE, PL, RA, SA, SC, and SI **as control claims** — is
asserted by no description in the set. The two forks' AWS
deployment prose is deployment language, not an SC claim; Elvo's
session-metrics recording is not an AU claim; no description
carries SSO, identity-provider, or access-control language. If the
source later publishes an impact level for any of these offerings,
the tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment. One fork's prose goes further than its record:
  WellHive writes "In addition to a FedRAMP Moderate
  authorization" while its own marketplace record carries impact
  level **Unknown** and status **FedRAMP In Process**. The
  sentence is recorded as the fork's assertion; it converts to no
  tier here, and the discrepancy is the fork's, not smoothed over.
- **Not a medical device; no FDA status.** The build is a records
  substrate over opaque references. It stores no real PHI/PII,
  holds no diagnosis or clinical free text (those fields do not
  exist), and makes no clinical claim of any kind.
- **Extended functions are specified, not implemented.** The
  union spec ranks 11 functions; the substrate behind the records
  is implemented here, and no Core function is claim-supported in
  this set. NOT implemented (counts are this set's): patient
  engagement channels & content and survey instruments (1 fork
  claims the family; the engines are Extended); EMR/EHR
  integration engines (WellHive describes the function in
  substance, in wording that claims nothing); insurance
  verification, benefits discovery & claims adjudication engines
  (WellHive substance); care coordination & navigation platform
  depth (86Borders and WellHive substance); integrated scheduling
  engines (WellHive substance); at-home therapy delivery &
  session-metrics analytics (Elvo substance); telehealth visit
  support (Elvo names telehealth as a use-case context only);
  measurement & outcome analytics engines; clinical decision
  support; device connectivity / sync pipelines; AI/ML models &
  personalization engines; automation / workflow engines;
  multi-device native apps (a platform/access property).
- **The build performs no cloud hosting of its own.** Two forks
  document AWS deployment prose about themselves; the substrate is
  a single-tenant reference deployment — TLS is a deployment-layer
  option when a certificate is configured, and encryption at rest
  is deployment-layer, not claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  `carol`, and `dana` are documented demo identities supplied by
  header; the service enforces the role permission matrix on those
  hooks and ships no identity provider, no credential store, and
  no authentication of its own. IA-2 stays with the embedding
  organization.
- **Named absences stand.** Measurement & device data records,
  review/analysis & scorecards, EMR integration, care guidance,
  claims processing, hosting claims, AI, automation, device
  connectivity, and multi-device access all have 0 claimants in
  this set — several against prose that describes the function in
  other words, itemized in the union spec. Nothing was back-filled
  to make the set look complete.
