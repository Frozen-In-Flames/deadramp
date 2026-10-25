# Education & Training L1 — merged build (Operation DeadRamp, Phase 2, Group 30)

This is the merged, clean-room implementation of the **Education &
Training L1** sibling group: **2 forks / vendor platforms** from the
FedRAMP Marketplace that share the same function (Education &
Training) and the same trust tier (CMMC L1 — FedRAMP Low and LI-SaaS),
built as one open-source service from the group's union contract
(`UNION-SPEC.md`).

The 2 forks: **Amplifire** (Amplifire) — LI-SaaS · **RQI1Stop** (RQI
Partners LLC) — Low. Both are FedRAMP Certified. Each fork's actual
impact level is recorded in its spec sheet in `specs/specs.json`.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

## The evidence, stated first

Under Group 13's 21-family taxonomy applied verbatim, this group's
two descriptions produce **1 claim in total**: RQI1Stop's
`hosting_platform` tag (its "multi-tenant Public Cloud" sentence — a
platform property, not a learning function). Amplifire's sheet is a
**zero-claim sheet**: its description is training prose ("training
platform", "Patented algorithms", "learner interactions") that meets
none of the taxonomy's verbatim patterns, and every near-miss is
itemized in `scratch/ARTIFACTS.md` rather than rounded up. The
taxonomy was **not** re-tuned for this group. The 10 core functions
below therefore stand under the **core-boundary decision** recorded
in the union spec: the substrate was established by Group 13's union
for this same category (43 evidenced claims at L2), both L1 products
presuppose it in their own words, and two functions (RBAC, audit) are
baseline hooks. In this group, all 10 core functions are **carried,
not claimed** — the counts are a stated floor.

## What the group is: a records substrate

The substrate the category's union proves: courses/programs held in
a registry, learners enrolled or registered, progress/readiness
tracked, assessments administered, certification/credential status
recorded, compliance assignments tracked, sessions scheduled, and
reports produced over those records. Each vendor's engine on top of
it (Amplifire's adaptive knowledge-gap remediation, content and
curriculum delivery) is an Extended function (see Honesty).

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
   deterministic scoring was ruled Extended at 0 claims in either
   tier of this category.
5. **Certificate/credential records** — certification, licensure, and
   credential records (`cred-`) and their tracked status. **Records
   only — no issuance engine** (issuance is claimed by 0 siblings in
   either tier).
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
    API for audit entries. (Baseline hook: AU-2/AU-3 on the FedRAMP
    Low side only — see the baseline section.)

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

65 tests, all passing at delivery in this tree. See `tests/README.md`
for the coverage table, the negative control, and the
mutation-verification drill record (performed fresh here: the
status-derivation mutant produced exactly 8 failures, the same set
as Group 13's drill on the identical code; the file was restored and
SHA-256-verified). A live smoke (`scratch/smoke.py`) drives the store
and the HTTP service end to end: course → enroll → progress →
compliance assignment with a past due date → derived status
`overdue` → completion progress → derived status `completed`; a
learner's admin action is denied at the store, returns 403 over HTTP,
and the denied attempt is audited.

## Reuse, stated explicitly

This build reuses Group 13's implementation (our own Apache-2.0
code) **in full**: all 7 files under `src/learn/` are **byte-identical**
to `groups/education-training-l2/src/learn/` (SHA-256 per file in
`scratch/src-sha256.txt`). The code contains no tier or baseline
logic; what is new here is the group's own spec sheets, this union
spec and its Low/L1 baseline, the README, and the test-suite
docstring adaptations (13 of 15 test files differ from Group 13's by
documentation wording only — group number, this group's claim counts,
Low traceability tags; zero test logic changed). Two comments in
`store.py` carry Group 13's claim counts ("0/8") as the recorded
origin of the records-only decisions; the decisions are restated on
this group's own evidence (0/2) in the union spec, and the comments
stand as lineage so the byte-identity claim stays exact.

## Control baseline (summary) — Low / L1

Group baseline: **NIST SP 800-53 Rev. 5 Low** (the FedRAMP Low
tailoring; LI-SaaS is a tailored subset and adds nothing) ⇔ **CMMC
L1** (the FAR 52.204-21 practice set), per `../../crosswalk.md` and
the union spec's traceability table. No 800-171 practices are claimed
at this tier, and Group 13's Moderate citations were not imported.

| Core function | Control families | How the build answers |
|---|---|---|
| Course/catalog registry | CM-6, AU-2, SI-10 | Registry entries are explicit, configuration-controlled records, recorded when created; inputs validated before any record exists |
| Enrollments & registrations | AC-2, AU-2 | Enrollment is an explicit, recorded action binding a learner to a registry entry |
| Learner progress & readiness records | AU-2 | Progress/readiness state is a recorded, reviewable record per learner |
| Assessment records | AU-2, AU-3, SI-10 | Every administration leaves a record with content; inputs validated before any record exists (records only — no score field) |
| Certificate/credential records | AU-2 | Credential status changes are recorded events on retained records (records only — no issuance claim) |
| Compliance assignments & status derivation | AU-2, CM-6 | Status is derived deterministically at read time from assignment, due date, and progress; derivation runs over recorded facts only |
| Scheduling records | AU-2, CM-6 | Sessions are explicit records bound to registry entries and enrollments |
| Reporting over the records | AU-2 | Reports are computed views over recorded substrate facts only |
| RBAC (admin/instructor/learner/auditor) | AC-2, AC-3, AC-5, AC-6, IA-2/IA-5 (hooks) | Role matrix enforced pre-mutation, with learner scope; identity itself is supplied by the embedding organization |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API |

**Precision note (audit):** CMMC L1 / FAR 52.204-21 contains **no
audit practice**. The audit log is carried because the FedRAMP Low
baseline carries the AU family (AU-2/AU-3) — not because L1 asks for
it. Group 13's Moderate citations for this function (AU-6, AU-9) are
not carried at this tier.

## Honesty: what is Core, what is Extended, what is NOT in this build

**The claim floor, again, plainly.** 1 claim tags in this entire
group; Amplifire's sheet tags zero. Every learning-function family
sits at 0/2. The Core stands on the recorded core-boundary decision
(union spec), not on this group's counts, and no near-miss was
rounded up to change that. RQI1Stop's description contains no
certification wording at all: no credential claim was inferred from
the vendor's real-world CPR-certification purpose.

**Core vs Extended.** The Core is exactly the 10 functions above —
in this group all 10 are **carried, not claimed** (RBAC and audit are
additionally Low-baseline hooks). Everything else in the union spec's
long tail is **Extended and NOT implemented** here; it is reserved
for the final gap batch. The gap list, by name, exactly as registered
for GAPS.md:

1. Adaptive learning / knowledge-gap remediation engine (Amplifire's patented algorithms, described in prose; 0 tagged claims — the verbatim taxonomy was not re-tuned to capture it)
2. Talent, skills & marketplace matching (incl. career exploration/coaching and AI career assistants) (carried from the Group 13 union; 0 claims here)
3. Recruiting, HCM/HRIS & workforce management suites (incl. performance and policy management) (carried; 0 claims here)
4. Course content authoring & delivery, media streaming (carried; 0 claims here)
5. Simulation engines (capture, debriefing & playback) (carried; 0 claims here)
6. Remote proctoring & identity proofing (0 claims in either tier of this category)
7. Deterministic scoring & AI grading (0 claims in either tier; assessments are administration records only, no score field exists by design)
8. Collaboration & social learning (carried; 0 claims here)
9. Data storage & processing services beyond the substrate's own records (carried; 0 claims here)
10. Notifications & reminders (0 claims in either tier)
11. Integrations & APIs as a union function (0 claims in either tier; this build's own REST surface is its own design)

Platform-layer: general cloud hosting / PaaS incl. multi-tenancy
(this group's sole tagged family, 1 of 2 — a deployment property;
single-tenant reference deployment); encryption at rest is
deployment-layer (TLS when configured); demo identities are hooks,
not an IdP (IA-2 stays with the embedding organization).

**Certificates are records only.** This build holds and tracks
certificate/credential records and their status changes. It does not
issue, sign, or revoke-by-authority any credential: credential
**issuance is claimed by 0 siblings in either tier** of this category
and is not specified in the Core.

**No scoring.** Assessment support is administration records
(sessions, states, item responses held verbatim). Deterministic
scoring/grading wording appears in **0 descriptions in either tier**;
no score or grade field exists anywhere in this build.

**Audit is a baseline hook with 0/2 descriptive claims.** No sibling
description in this group mentions audit logging. The append-only
audit log is carried on the FedRAMP Low side of the crosswalk only
(AU-2/AU-3); FAR 52.204-21 contains no audit practice and none is
claimed from it.

**Due dates are a flagged reach, stated plainly.** Explicit due-date
wording is also 0/2 here (0/8 at L2). The assignment + due-date +
derived-status triple in Core function 6 is the minimal record
structure compliance *tracking* presupposes, and the derivation is
deterministic substrate logic rather than a vendor engine; it is
included on that basis and flagged in the union spec.

**Demo identities are hooks, not an IdP.** The demo identities
(`alice`, `bob`, `carol`, `dana`) are hooks, not an identity
provider: IA-2 (identification & authentication) stays with the
embedding organization, which supplies production identity,
authentication strength, and account lifecycle.

**Platform layer.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies when a certificate is
configured (`--certfile`/`--keyfile`); the default serve mode is
plain HTTP for local/demo use. The merged build is a
**single-tenant reference deployment**; multi-tenancy (this group's
one tagged family) and general cloud hosting/PaaS are deployment
properties, not learning functions.

**Tier caveat.** FedRAMP authorizes products; CMMC certifies
organizations. The L1 / FedRAMP Low–LI-SaaS equivalence used here is
a planning/matching equivalence only. This build is **not a FedRAMP
authorization and confers no CMMC certification**, and it claims
neither.
