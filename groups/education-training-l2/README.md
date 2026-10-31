# Education & Training L2 — merged build (Operation DeadRamp, Phase 2, Group 13)

This is the merged, clean-room implementation of the **Education &
Training L2** sibling group: **8 forks / vendor platforms** from the
FedRAMP Marketplace that share the same function (Education &
Training) and the same trust tier (CMMC L2, equivalent to FedRAMP
Moderate), built as one open-source service from the group's union
contract (`UNION-SPEC.md`).

The 8 forks: Blackboard LMS (Blackboard) · Acadis Readiness Suite
(Envisage Technologies LLC) · Laerdal -- SimCapture Cloud Government
(Laerdal Labs D.C.) · NEOGOV Cloud (NEOGOV) · Palladium (PDRI by
Pearson) · Pepelwerk Government (Pepelwerk LLC) · Next Generation
Cloud Platform (Peraton Corporation) · Gov Secure Cloud (PSI
Services LLC). All 8 are FedRAMP Moderate; 43 evidenced claims across
the 8 spec sheets in `specs/specs.json`.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

**Remainder addition (2026-10-31):** 1 previously uncategorized
fork from the remainder census — Pearson VUE / Pearson Federal
Cloud System (FedRAMP Moderate) — was spec'd into this group
under the same 21-family taxonomy applied verbatim (see
`ADDENDUM.md`). It claims 4 families (enrollment/candidate
registration, assessments, scheduling, reporting), all already
Core, so the build is unchanged (`src/` byte-identical) and the
group now covers **9 forks, 47 claims**; the suite grew 65 → 79
tests, all passing, with the group's signature compliance-
derivation drill re-run in this tree (exactly 9 failures under
mutation). The addition also asserts online proctoring in its own
words — a substance the taxonomy has no family for; it is
registered as a claimant on the existing proctoring gap in the
addendum, not as a claim.

## What the group is: a records substrate

The claim counts in the union spec prove a **records substrate**, not
a learning-delivery product: courses/programs held in a registry,
learners enrolled or registered, progress/readiness tracked,
assessments administered, certification/credential status recorded,
compliance assignments tracked, sessions scheduled, and reports
produced over those records. Each vendor's delivery, simulation,
matching, and assessment engines on top of that substrate are
Extended functions (see Honesty).

## The 10 core functions

1. **Course/catalog & training program registry** — courses and
   programs as records (`crs-`), configuration-controlled: nothing is
   offered that is not registered.
2. **Enrollments & candidate registrations** — records (`enr-`)
   binding a learner/candidate to a registry entry; duplicate active
   enrollments are rejected.
3. **Learner progress & readiness records** — per-learner progress
   records (`prg-`) with status (`not_started` / `in_progress` /
   `completed`), readiness level, and percent; completion is recorded
   as the terminal progress state. Records only — no content delivery.
4. **Assessment records** — administration records (`asm-`): program/
   course, learner/candidate, optional session, administration state,
   and item responses held verbatim as records. **No scoring** —
   deterministic scoring was ruled Extended at 0/8 claims.
5. **Certificate/credential records** — certification, licensure, and
   credential records (`cred-`) and their tracked status. **Records
   only — no issuance engine** (issuance is claimed by 0/8).
6. **Compliance assignments & derived status** — assignments (`cmp-`)
   with a due date. **Status is never stored**: it is derived at read
   time, deterministically, from the assignment, the due date, the
   learner's progress records, and an explicit `as_of` reference date
   — `completed` when a completed progress record exists for the
   learner+course, `overdue` when `as_of` is after the due date,
   `current` otherwise.
7. **Scheduling records** — training and assessment session records
   (`sch-`) bound to registry entries and enrolled learners.
8. **Reporting over the records** — counts/summaries over registry,
   enrollments (incl. per-course), progress, assessments,
   credentials, compliance status (derived, at `as_of`), and
   sessions. Reporting/dashboard engines are Extended.
9. **RBAC** — `admin` / `instructor` / `learner` / `auditor` roles
   with a permission matrix enforced before any state change, plus
   learner scope: a learner-role actor can only read records whose
   `learner_id` is their own.
10. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or deletion
    API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `crs-`, `enr-`, `prg-`, `asm-`,
`cred-`, `cmp-`, `sch-`. Permission is checked before any state
change or id allocation. Dates are ISO strings (due/issued/expiry
dates `YYYY-MM-DD`; session times ISO-8601 datetimes); compliance
derivation takes an explicit `as_of` date so it never depends on the
wall clock.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m learn serve --host 127.0.0.1 --port 8791
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

As a library:

```python
import sys; sys.path.insert(0, "src")
from learn.access import User
from learn.audit import AuditLog
from learn.store import LearnStore

audit = AuditLog()
store = LearnStore(audit=audit)
admin = User("alice", "admin"); instructor = User("bob", "instructor")
course = store.create_course("Safety Basics", admin, code="SAFE-101")
store.create_enrollment("carol", course["id"], instructor)
store.create_compliance_assignment("carol", course["id"], "2026-06-01", admin)
print(store.compliance_status("cmp-1", admin, as_of="2026-06-15"))
# {'assignment_id': 'cmp-1', ..., 'status': 'overdue', 'completed': False, 'as_of': '2026-06-15'}
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role       | Permissions |
|---------|------------|-------------|
| `alice` | admin      | all reads + all writes, plus `audit_read` |
| `bob`   | instructor | all record reads + `report_read`; writes: `enrollment_write`, `progress_write`, `assessment_write`, `schedule_write` |
| `carol` | learner    | record reads only, own records only (learner scope); no writes, no `report_read`, no `audit_read` |
| `dana`  | auditor    | all record reads + `report_read` + `audit_read`; no writes |

Read actions: `catalog_read`, `enrollment_read`, `progress_read`,
`assessment_read`, `credential_read`, `compliance_read`,
`schedule_read` (all roles, learner-scoped for learners). Write
actions: `catalog_write`, `credential_write`, `compliance_write`
(admin only); `enrollment_write`, `progress_write`,
`assessment_write`, `schedule_write` (admin + instructor).
`report_read` (admin, instructor, auditor); `audit_read` (admin,
auditor). Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case (the communication group's convention).

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/courses` | catalog_read | `{"courses": [...]}` |
| POST | `/courses` | catalog_write | Body `{"title", "kind"?, "code"?, "description"?}` → 201 course |
| GET | `/courses/{id}` | catalog_read | One registry entry |
| GET | `/enrollments?learner_id=&course_id=` | enrollment_read | `{"enrollments": [...]}` |
| POST | `/enrollments` | enrollment_write | Body `{"learner_id", "course_id", "kind"?}` → 201 enrollment |
| GET | `/enrollments/{id}` | enrollment_read | One enrollment (learner-scoped) |
| GET | `/progress?learner_id=&course_id=` | progress_read | `{"progress": [...]}` |
| POST | `/progress` | progress_write | Body `{"learner_id", "course_id", "status", "readiness"?, "percent_complete"?, "note"?}` → 201 record |
| GET | `/progress/{id}` | progress_read | One progress record (learner-scoped) |
| GET | `/assessments?learner_id=&course_id=` | assessment_read | `{"assessments": [...]}` |
| POST | `/assessments` | assessment_write | Body `{"title", "learner_id", "course_id"?, "session_id"?, "state"?}` → 201 record |
| GET | `/assessments/{id}` | assessment_read | One assessment record (learner-scoped) |
| POST | `/assessments/{id}/responses` | assessment_write | Body `{"item_id", "response"}` → record (stored verbatim, never scored) |
| POST | `/assessments/{id}/state` | assessment_write | Body `{"state"}` → record |
| GET | `/credentials?learner_id=` | credential_read | `{"credentials": [...]}` |
| POST | `/credentials` | credential_write | Body `{"learner_id", "name", "kind"?, "status"?, "issued_date"?, "expiry_date"?}` → 201 record |
| GET | `/credentials/{id}` | credential_read | One credential record (learner-scoped) |
| POST | `/credentials/{id}/status` | credential_write | Body `{"status"}` → record |
| GET | `/compliance?as_of=&learner_id=` | compliance_read | `{"compliance": [...]}` with derived status |
| POST | `/compliance` | compliance_write | Body `{"learner_id", "course_id", "due_date"}` → 201 assignment (no status stored) |
| GET | `/compliance/{id}?as_of=` | compliance_read | One assignment with derived status |
| GET | `/compliance/{id}/status?as_of=` | compliance_read | `{assignment_id, learner_id, course_id, due_date, status, completed, as_of}` |
| GET | `/sessions?course_id=` | schedule_read | `{"sessions": [...]}` |
| POST | `/sessions` | schedule_write | Body `{"title", "course_id", "starts_at", "ends_at"?, "kind"?, "location"?, "learner_ids"?}` → 201 session |
| GET | `/sessions/{id}` | schedule_read | One session record |
| GET | `/report?as_of=` | report_read | Counts/summaries over the records |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

65 tests, all passing at delivery. See `tests/README.md` for the
coverage table, the negative control, and the mutation-verification
drill record. A live smoke (`scratch/smoke.py`) drives the store and
the HTTP service end to end: course → enroll → progress → compliance
assignment with a past due date → derived status `overdue` →
completion progress → derived status `completed`; a learner's admin
action is denied at the store, returns 403 over HTTP, and the denied
attempt is audited.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline cross-walked to
the NIST SP 800-171 practices behind CMMC L2, per the union spec's
traceability table:

| Core function | Control families | How the build answers |
|---|---|---|
| Course/catalog registry | CM-6, SI-12 | Registry entries are explicit, configuration-controlled records; nothing is offered that is not registered |
| Enrollments & registrations | AC-2, AU-2 | Enrollment is an explicit, auditable record binding a learner to a registry entry |
| Learner progress & readiness records | AU-6, SI-12 | Progress/readiness state is a reviewable record per learner, retained with the record set |
| Assessment records | AU-2, AU-3, SI-10 | Every administration leaves a record with content; inputs are validated before any record exists |
| Certificate/credential records | AU-2, SI-12 | Credential status changes are auditable events on retained records (records only — no issuance claim) |
| Compliance assignments & status derivation | AU-6, CA-7, CM-6 | Status is derived deterministically from assignment, due date, and progress; derivation is queryable and reviewable |
| Scheduling records | AU-2, CM-6 | Sessions are explicit records bound to registry entries and enrollments |
| Reporting over the records | AU-6, CA-7 | Reports read the substrate records only; no side-channel data |
| RBAC (admin/instructor/learner/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; identity itself is supplied by the embedding organization (see Honesty) |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

## Honesty: what is Core, what is Extended, what is NOT in this build

**Core vs Extended.** The Core is exactly the 10 functions above:
8 claim-supported by the spec sheets, RBAC baseline-supported with
thin descriptive claims (1/8 explicit), and the audit log
baseline-only (see below). Everything else in the union spec's long
tail is **Extended and NOT implemented** here; it is reserved for
the final gap batch. The gap list, by name, exactly as registered:

1. Talent, skills & marketplace matching (incl. career exploration/coaching and the AI Career Assistant)
2. Recruiting, HCM/HRIS & workforce management suite (incl. employee performance management and policy management)
3. Course content authoring & delivery, media streaming
4. Simulation engines (simulation capture, debriefing & playback)
5. Remote proctoring & identity proofing
6. Deterministic scoring & AI grading
7. Skills-marketplace matching
8. General cloud hosting / PaaS (multi-tenancy as a deployment property)
9. Collaboration & social learning (peer interaction & discussions)
10. Data storage & processing services (beyond the substrate's own records)
11. Notifications & reminders
12. Integrations & APIs (as a union function; this build's own REST surface is its own design)

**Certificates are records only.** This build holds and tracks
certificate/credential records and their status changes. It does not
issue, sign, or revoke-by-authority any credential: credential
**issuance is claimed by 0/8 siblings** and is not specified in the
Core. Two of the three supporting claims are themselves record-form
only (credential data captured in a profile; assessment programs used
for licensure/certification), which is why the Core is records.

**No scoring.** Assessment support is administration records
(sessions, states, item responses held verbatim). Deterministic
scoring/grading wording appears in **0/8** descriptions; no score or
grade field exists anywhere in this build.

**Audit is a baseline hook with 0/8 descriptive claims.** No sibling
description in this group mentions audit logging. The append-only
audit log is included solely because the L2/Moderate baseline
requires it (AU family), exactly as in sibling groups — not because
any vendor function claims it.

**Due dates are a flagged reach, stated plainly.** Explicit due-date
wording is also 0/8. The assignment + due-date + derived-status
triple in Core function 6 is the minimal record structure compliance
*tracking* presupposes, and the derivation is deterministic substrate
logic rather than a vendor engine; it is included on that basis and
flagged in the union spec.

**Demo identities are hooks, not an IdP.** The demo identities
(`alice`, `bob`, `carol`, `dana`) are hooks, not an identity
provider: IA-2 (identification & authentication) stays with the
embedding organization, which supplies production identity,
authentication strength, and account lifecycle.

**Platform layer.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies when a certificate is
configured (`--certfile`/`--keyfile`); the default serve mode is
plain HTTP for local/demo use. The merged build is a
**single-tenant reference deployment**; multi-tenancy and general
cloud hosting/PaaS are deployment properties, not learning
functions.

**Tier caveat.** FedRAMP authorizes products; CMMC certifies
organizations. The L2 / FedRAMP Moderate equivalence used here is a
planning/matching equivalence only. This build is **not a FedRAMP
authorization and confers no CMMC certification**, and it claims
neither.
