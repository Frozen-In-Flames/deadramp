# Health & Wellness L1 — singleton build (Operation DeadRamp, Phase 2 remainder)

This is the clean-room implementation of the **Health & Wellness
L1 singleton**: **1 fork** from the FedRAMP Marketplace at the
lightest tier — **Itamar Dispatcher Cloud (IDC)** (Itamar
Medical), FedRAMP **LI-SaaS**, FedRAMP Certified — built per the
group's union spec ([`UNION-SPEC.md`](UNION-SPEC.md)) under the
singleton pipeline (same pipeline, group size one). LI-SaaS is
FedRAMP's tailored subset of the Low baseline for SaaS offerings;
the group's union baseline is the Low baseline ⇔ CMMC L1 (FAR
52.204-21).

**Read the honesty section before the function list.** This fork's
public description evidences **zero** function families under the
category taxonomy (applied verbatim from Group 18) — it is a home
sleep-apnea test dispatcher, and the taxonomy's patterns are the
original five forks' glucose/CGM and engagement phrases, none of
which fires on its three sentences. So the build below is the
category's health records substrate **carried** at this tier under
an explicit core-boundary decision, not a set of functions this
fork was found to claim. The decision, its reasoning, and its
price (full disclosure) are in `UNION-SPEC.md`, together with the
near-miss record (integration, device pipeline, and result
collection are all present *in substance* and claimed by no
family). Membership provenance is also recorded there:
`forks.json` files this fork Uncategorized; the Health & Wellness
category is the remainder census proposal, taken from the fork's
own description.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

**Reuse, stated plainly:** the implementation and test suite are
the shipped Group 18 (Health & Wellness L2) build's code, reused —
this project's own Apache-2.0 code. A per-file hash comparison is
recorded in `scratch/reuse-note.md`: all 7 `src/` modules and 13
of 15 carried test files are byte-identical to Group 18's; the two
differing test files differ in documentation wording only, and one
test file is new (the singleton spec pins and substrate cases).
**The baseline claim is not reused.** Everything Group 18 says
about Moderate / NIST SP 800-171 stays in Group 18, and Singleton
46's High uplifts (hash-chained audit, fail-closed audit writes,
audit query, logon lockout, **auditor role tightened to
`audit_read` only**) are not inherited downward — the auditor here
keeps Group 18's read set. This group's claims are the Low
baseline's and FAR 52.204-21's only, as written in
`UNION-SPEC.md`.

## The 10 core functions (carried substrate)

1. **Participant registry** — participants as records (`par-`)
   keyed by an **opaque, caller-supplied reference only**
   (`participant_ref`, unique), kind patient / caregiver /
   professional. No names, contact details, dates of birth, or any
   other identifier fields exist in the shape.
2. **Program registry** — programs, clinics, and care journeys as
   records (`prg-`), configuration-controlled: nothing is offered
   that is not registered.
3. **Enrollments with derived status** — enrollment/registration
   records (`enr-`) binding a participant to a program; duplicate
   active enrollments are rejected. The stored status is always
   `enrolled`; reads add a **derived status** computed
   deterministically from the participant's plan records for that
   program (`overdue` if any is overdue, else `completed` if any
   is completed, else `enrolled`).
4. **Measurement / outcome records** — numeric value + unit +
   metric name + date (`msr-`), per participant, optionally per
   program. **No diagnosis fields, no free-text clinical notes**;
   unknown or extra fields are refused at the boundary (see
   Privacy discipline).
5. **Care / wellness plan records with derived status** — plan
   records (`pln-`) with a due date and an optional completion
   date. Status is **derived** at read time: `completed` when a
   completion date is recorded, `overdue` when `as_of` is after
   the due date, `current` otherwise.
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
   (count, min, max, mean) and per derived status over the
   substrate records, group-wide (`report`) and per program
   (`scorecard`), plus per-participant measurement listing (the
   individual-scorecard view). Pattern/trend detection and
   scorecard presentation engines are Extended.
9. **RBAC** — `admin` / `clinician` / `member` / `auditor` roles
   with a permission matrix enforced before any state change, plus
   member scope: a member-role actor can only read records whose
   participant's `participant_ref` is their own user name.
   **Baseline-carried, not claimed** (0 claims in category text at
   any tier — see Honesty).
10. **Append-only audit log** — every mutation, every report /
    scorecard read, and every denied attempt recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence. There is no mutation or deletion API for audit
    entries. **Baseline-carried, not claimed**.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `par-`, `prg-`,
`enr-`, `msr-`, `pln-`, `act-`, `elg-`. Permission is checked
before any state change or id allocation. Dates are ISO strings
(dates `YYYY-MM-DD`; activity times ISO-8601 datetimes); derived
statuses take an explicit `as_of` date so they never depend on the
wall clock.

## Privacy discipline

This group handles health-adjacent records, so the substrate's
field discipline is part of the contract, not an implementation
nicety:

- **Records + opaque references only.** Participants are keyed by
  a caller-supplied opaque `participant_ref`; coverage by an
  opaque `plan_ref`. The substrate never stores a real name,
  address, phone, email, date of birth, SSN, member/insurance
  number, or any other direct identifier — those fields **do not
  exist** in any entity shape.
- **No diagnosis, no clinical free text.** Measurement records
  hold a metric name, a numeric value, a unit, and a date —
  nothing else. No entity has a diagnosis field, a notes field, or
  any free-text clinical field.
- **For this fork specifically: no sleep study data, no test
  results.** The WatchPAT device's payloads, the study data the
  mobile application transfers, and the results IDC collects are
  clinical content. The substrate holds none of it; a measurement
  record here is a caller-recorded administration value only, and
  the pipeline that moves real study data is the fork's Extended
  engine.
- **Refusal at the boundary.** Store methods accept only the
  contract's named parameters; the HTTP layer rejects any JSON key
  outside an endpoint's named field list with `ValidationError`
  (HTTP 400) before calling the store, so a caller cannot smuggle
  a diagnosis, a note, or an identifier into a record by adding a
  field. The test suite asserts this explicitly (a `diagnosis` key
  on `POST /measurements` is refused and nothing is stored).
- **Member scope.** A member-role caller can read only records
  whose participant's `participant_ref` equals the caller's user
  name.
- **Anything clinical is Extended.** Diagnosis content, clinical
  notes or documentation, decision support, and any real PHI
  belong to the Extended engines in the union spec's gap list;
  this build neither stores nor transmits them.

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
program = store.create_program("Home Sleep Testing", admin, code="HST-101")
participant = store.create_participant("carol", admin)
store.create_enrollment(participant["id"], program["id"], clinician)
plan = store.create_plan(participant["id"], program["id"], "Return device", "2026-06-01", clinician)
print(store.get_plan(plan["id"], admin, as_of="2026-06-15")["derived_status"])
# 'overdue'
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role      | Permissions |
|---------|-----------|-------------|
| `alice` | admin     | all 16 actions |
| `bob`   | clinician | all 7 record reads + `enrollment_write`, `measurement_write`, `plan_write`, `activity_write` + `report_read` |
| `carol` | member    | the 7 record reads only, own-participant records only (member scope); no writes, no `report_read`, no `audit_read` |
| `dana`  | auditor   | all 7 record reads + `report_read` + `audit_read`; no writes — **not** tightened to `audit_read` only; that tightening is Singleton 46's High-tier decision and is not inherited downward |

Read actions: `participant_read`, `program_read`, `enrollment_read`,
`measurement_read`, `plan_read`, `activity_read`, `eligibility_read`
(the 7 record reads, member-scoped for members). Write actions:
`participant_write`, `program_write`, `eligibility_write` (admin
only); `enrollment_write`, `measurement_write`, `plan_write`,
`activity_write` (admin + clinician). `report_read` (admin,
clinician, auditor); `audit_read` (admin, auditor). Unknown roles
hold no permissions.

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is
responsible for enforcement in that case (the shipped groups'
convention).

A permitted role performing a forbidden action gets 403;
validation failures (including unknown/extra JSON keys) get 400;
unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

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

79 tests. See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **Low** baseline (the FedRAMP
Low baseline; LI-SaaS is its tailored subset for SaaS offerings),
cross-walked to the FAR 52.204-21 practices behind CMMC L1.
Written fresh for this tier — Group 18's Moderate mapping is not
reused (see the precision notes in `UNION-SPEC.md`):

| Core function | Control families | How the build answers |
|---|---|---|
| Participant registry (opaque refs) | AC-2, AC-3, SI-10; IA-2 (hooks) | Participants exist only as explicit records under caller-supplied opaque references; no identifier fields exist to leak |
| Program registry | CM-6, SI-10 | Programs are explicit, configuration-controlled records; nothing is offered that is not registered |
| Enrollments with derived status | AC-3, AU-2/AU-3 (Low side), CM-6 | Enrollment is an explicit, auditable record; its status is derived deterministically and is reproducible |
| Measurement / outcome records | AU-2, AU-3 (Low side), SI-10 | Every measurement leaves a validated record (named fields only; extra fields refused); inputs are validated before any record exists |
| Care/wellness plan records | AU-2, AU-3 (Low side), CM-6 | Plan status is derived deterministically from due/completion dates; derivation is queryable and reviewable |
| Activity / appointment records | AU-2, AU-3 (Low side), CM-6 | Activities are explicit records bound to participants and programs, with auditable state changes |
| Eligibility / coverage records | AC-3, AU-2/AU-3 (Low side) | Coverage exists only as a record under an opaque plan reference, with derived status reviewable as of any date |
| Population scorecard reporting | AU-2, AU-3 (Low side) | Reports aggregate the substrate records only (per metric, per program); no side-channel data |
| RBAC (admin/clinician/member/auditor) | AC-2, AC-3, IA-2 (hooks) | Role matrix enforced pre-mutation; role differentiation traced to AC-3 at this tier (AC-5/AC-6 are lineage only); identity itself is supplied by the embedding organization |
| Audit log | AU-2, AU-3 — FedRAMP Low side only | Append-only log including denied attempts; no mutation API. FAR 52.204-21 has no audit practice, so no CMMC-side audit claim is made; AU-6/AU-9 are Moderate selections, not claimed here |

## Honesty: what is NOT in this build

- **Zero claims at this tier.** The singleton's description tags
  no function family under the category taxonomy; the 10 core
  functions are the Group 18 category substrate carried at this
  tier and flagged carried, not claimed, throughout
  `UNION-SPEC.md`. The zero is the finding, with its near-misses
  itemized in `scratch/ARTIFACTS.md` — not a gap in the paperwork.
- **Itamar's engines are NOT implemented.** No home sleep-test
  dispatch, no WatchPAT device initialization, no API integration
  engine into patient management systems, no device or mobile-app
  data-transfer pipeline, and no sleep study results collection or
  provider review surface. Those are the singleton's Extended
  gaps, named in `UNION-SPEC.md` for the final batch. Three
  registered category gaps gain this fork as a claimant **by
  substance only** (EMR/EHR integration engines, device
  connectivity / sync pipelines, multi-device native apps); no
  family claim fired for any of them.
- **Extended capabilities from the L2 union are NOT
  implemented.** No clinical decision support, no claims
  adjudication, no AI/ML models, no automation/workflow engines,
  no survey instruments, no engagement channels, no telehealth
  media, and none of the L2 additions' engines (store-and-forward
  clinical data, coding, grouper/content services, CDI, diagnostic
  report generation, therapy/risk console).
- **Telehealth is a named absence at this tier — still.** It was
  retired at L2 by another fork's own words; this fork describes
  a device-dispatched home diagnostic, not a visit over a media
  channel, and the absence survives here on token-level evidence.
- **No real health data can be stored — by design.** No patient
  identifiers, no diagnoses, no sleep study data, no test results,
  no clinical notes exist in any entity shape; measurement records
  are caller-recorded administration values (metric, number, unit,
  date) and nothing else.
- **This build is not a medical device and claims no FDA
  status.** It diagnoses nothing, monitors nothing, and processes
  no clinical signal. The vendor's device is the vendor's; nothing
  about it transfers to this build.
- **RBAC and audit are carried-not-claimed.** No description in
  this category claims access control or audit logging in
  functional terms at any tier; both are Core solely as baseline
  substrate.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength, and account lifecycle belong to the
  embedding organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **TLS is available only when a certificate is
  configured**; the default serve mode is plain HTTP for
  local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which baseline
  families the build's features answer to; nothing more. FedRAMP
  authorizes products; CMMC certifies organizations — neither
  regime accepts the other as evidence.
