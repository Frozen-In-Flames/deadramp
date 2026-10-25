# Health & Wellness L2 — merged build (Operation DeadRamp, Phase 2, Group 18)

This is the merged, clean-room implementation of the **Health &
Wellness L2** sibling group: **5 forks / vendor platforms** from the
FedRAMP Marketplace that share the same function family (Health &
Wellness) and the same trust tier (CMMC L2, equivalent to FedRAMP
Moderate), built as one open-source service from the group's union
contract (`UNION-SPEC.md`).

The 5 forks: LibreView for US Government (Abbott, Inc.) · Composite
Apps/ CuraPatient (CuraPatient) · Dexcom Clarity for Government
(Dexcom Inc.) · Elekta ProKnow Federal (Elekta Solutions) ·
GetWellNetwork - Get Well Anywhere - Federal (GetWellNetwork). All 5
are FedRAMP Moderate (4 FedRAMP Certified, CuraPatient Agency
Authorization In Process); 19 evidenced claims across the 5 spec
sheets in `specs/specs.json`.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

## What the group is: a records substrate

The claim counts in the union spec prove a **records substrate**,
not a clinical product: participants held in a registry under opaque
references, programs (clinics / care journeys) held in a registry,
participants enrolled, measurement and outcome values recorded
against metrics, care/wellness plans recorded with derived
completion status, activities and appointments recorded,
eligibility/coverage recorded under opaque plan references, and
population scorecards aggregated over those records. Each vendor's
clinical, device, AI, and workflow engines on top of that substrate
are Extended functions (see Honesty).

## The 10 core functions

1. **Participant registry** — participants as records (`par-`) keyed
   by an **opaque, caller-supplied reference only**
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
4. **Measurement / outcome records** — numeric value + unit + metric
   name + date (`msr-`), per participant, optionally per program.
   **No diagnosis fields, no free-text clinical notes**; unknown or
   extra fields are refused at the boundary (see Privacy discipline).
5. **Care / wellness plan records with derived status** — plan
   records (`pln-`) with a due date and an optional completion date.
   Status is **derived** at read time: `completed` when a completion
   date is recorded, `overdue` when `as_of` is after the due date,
   `current` otherwise.
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
   individual-scorecard view). Pattern/trend detection and scorecard
   presentation engines are Extended.
9. **RBAC** — `admin` / `clinician` / `member` / `auditor` roles
   with a permission matrix enforced before any state change, plus
   member scope: a member-role actor can only read records whose
   participant's `participant_ref` is their own user name.
   **Baseline-carried, not claimed** (0/5 — see Honesty).
10. **Append-only audit log** — every mutation, every report /
    scorecard read, and every denied attempt recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence. There is no mutation or deletion API for audit
    entries. **Baseline-carried, not claimed** (0/5 — see Honesty).

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `par-`, `prg-`, `enr-`, `msr-`,
`pln-`, `act-`, `elg-`. Permission is checked before any state change
or id allocation. Dates are ISO strings (dates `YYYY-MM-DD`;
activity times ISO-8601 datetimes); derived statuses take an
explicit `as_of` date so they never depend on the wall clock.

## Privacy discipline

This group handles health-adjacent records, so the substrate's field
discipline is part of the contract, not an implementation nicety:

- **Records + opaque references only.** Participants are keyed by a
  caller-supplied opaque `participant_ref`; coverage by an opaque
  `plan_ref`. The substrate never stores a real name, address,
  phone, email, date of birth, SSN, member/insurance number, or any
  other direct identifier — those fields **do not exist** in any
  entity shape.
- **No diagnosis, no clinical free text.** Measurement records hold
  a metric name, a numeric value, a unit, and a date — nothing else.
  No entity has a diagnosis field, a notes field, or any free-text
  clinical field. (Deliberate contrast with Group 13, whose progress
  records carried a `note`: this package has **no** note field
  anywhere.)
- **Refusal at the boundary.** Store methods accept only the
  contract's named parameters; the HTTP layer rejects any JSON key
  outside an endpoint's named field list with `ValidationError`
  (HTTP 400) before calling the store, so a caller cannot smuggle a
  diagnosis, a note, or an identifier into a record by adding a
  field. The test suite asserts this explicitly (a `diagnosis` key
  on `POST /measurements` is refused and nothing is stored).
- **Member scope.** A member-role caller can read only records whose
  participant's `participant_ref` equals the caller's user name —
  the same own-records scoping Group 13 enforced for learners.
- **Anything clinical is Extended.** Diagnosis content, clinical
  notes or documentation, decision support, and any real PHI belong
  to the Extended engines in the long tail; the merged build neither
  stores nor transmits them.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m health serve --host 127.0.0.1 --port 8792
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). On startup the service prints exactly:
`health service listening on <scheme>://<host>:<port> (demo users: alice=admin, bob=clinician, carol=member, dana=auditor)`.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

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

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case (the education group's convention).

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

67 tests, all passing at delivery. See `tests/README.md` for the
coverage table, the negative control, and the mutation-verification
drill record. A live smoke (`scratch/smoke.py`) drives the store and
the HTTP service end to end: program → participant → enroll →
measurement → plan with a past due date → derived status `overdue`
(plan and enrollment) → completion → derived status `completed`; a
member's admin action is denied at the store, returns 403 over HTTP,
and the denied attempt is audited.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline cross-walked to
the NIST SP 800-171 practices behind CMMC L2, per the union spec's
traceability table:

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
| RBAC (admin/clinician/member/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; identity itself is supplied by the embedding organization (see Honesty) |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

## Honesty: what is Core, what is Extended, what is NOT in this build

**Core vs Extended.** The Core is exactly the 10 functions above:
8 claim-supported or substrate-presupposed (and flagged as such in
the union spec — enrollments, plans, and eligibility records are the
minimal record structures the claimed functions presuppose), and 2
baseline-only (RBAC and audit — see below). Everything else in the
union spec's long tail is **Extended and NOT implemented** here; it
is reserved for the final gap batch. The gap list, by name, exactly
as registered:

1. Clinical decision support (0 standalone claims — Dexcom's decision wording is analysis flavour)
2. EMR/EHR integration engines & documentation depth
3. Medical claims adjudication engine (eligibility/coverage *records* are Core; adjudication, coding, pricing, reimbursement workflows are not)
4. Device connectivity / sync pipelines (incl. secure-code account linking; the measurement records they would deliver are Core)
5. AI/ML models & personalization engines
6. Automation / workflow engines
7. Survey instruments depth
8. Patient engagement channels & content
9. Telehealth media (**0 claims — named absence**: no description claims video/virtual visits)
10. Multi-device native apps (a platform/access property, not a records function)
11. Hosting platform (a platform-layer property — Dexcom's Google Cloud / GKE prose; never a health function)

**Privacy discipline is constitutive.** See the dedicated section
above: opaque references only, no diagnosis or clinical free text
anywhere, extra fields refused at the boundary, member scope on
reads. Anything that would hold real clinical content is Extended
by construction and would need its own authorization basis; this
build neither stores nor transmits it.

**RBAC and audit are carried-not-claimed.** No sibling description
in this group claims access control / RBAC or audit logging in
functional terms (both checked with broad patterns at **0/5**). Both
enter the Core solely because the L2/Moderate baseline requires them
(AC/IA and AU families), exactly as in sibling groups — not because
any vendor function claims them. No reader should mistake them for
claimed vendor functions.

**Demo identities are hooks, not an IdP.** The demo identities
(`alice`, `bob`, `carol`, `dana`) are hooks, not an identity
provider: IA-2 (identification & authentication) stays with the
embedding organization, which supplies production identity,
authentication strength, and account lifecycle.

**Platform layer.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies when a certificate is
configured (`--certfile`/`--keyfile`); the default serve mode is
plain HTTP for local/demo use. The merged build is a
**single-tenant reference deployment**; multi-tenancy and cloud
hosting are deployment properties, not health functions.

**Tier caveat.** FedRAMP authorizes products; CMMC certifies
organizations. The L2 / FedRAMP Moderate equivalence used here is a
planning/matching equivalence only. This build is **not a FedRAMP
authorization and confers no CMMC certification**, and it claims
neither.
