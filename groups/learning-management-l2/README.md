# Learning Management L2 — singleton build (Operation DeadRamp, Phase 2, Group 48)

This is the clean-room implementation of the **Learning Management
L2 singleton**: **1 fork / vendor platform** from the FedRAMP
Marketplace, in a category with no group at any other tier, built
as one open-source service from the group's union contract
(`UNION-SPEC.md`).

The fork: **PowerTrain Government Learning Enclave - SaaS**
(PowerTrain Inc.), FedRAMP Moderate, FedRAMP Certified. 26
evidenced claims in the spec sheet in `specs/specs.json`, under a
26-family taxonomy defined from the fork's own marketplace
description (the category had no parent group, so there was no
taxonomy to inherit).

It was written from that contract only: original code, no vendor
code, assets, or branding from the offering. Python 3, **standard
library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

## What the fork is: a learning records substrate

The claims prove a **records substrate**, not a learning-delivery
product: learners held as opaque references, a course/content/
lesson-plan catalog, events with registrations and wait lists,
SF-182 training authorizations with recorded decisions, individual
development plans, competency records, progress records, learning
experience (LRS) statement records, mandatory-training compliance
assignments, and reports produced over those records. The fork's
engines on top of that substrate — the Moodle-based delivery
runtime, the SCORM distribution controller, the xAPI protocol
runtime, the EHRI feed, the career-mapping and survey engines, and
the two adjacent platform products (a hardened wiki and a hardened
CMS) — are Extended functions (see Honesty).

## The 14 core functions

1. **Learner registry (opaque references)** — learners (`lrn-`)
   known only by a caller-supplied opaque `ref` and a label; the
   record shape is pinned so no field can hold a real identifier.
2. **Course, content & lesson-plan catalog** — courses/programs
   (`crs-`); content items (`cnt-`) whose `standard` is one of the
   fork's own list (`scorm_1_2`, `scorm_2004`, `aicc`, `xapi`,
   `cmi5`, `mp3`, `mp4`, `pdf`, `other`); lesson plans (`les-`)
   referencing catalog entries.
3. **Events & registration management** — live/virtual events
   (`evt-`) with optional capacity; registrations (`reg-`) with
   recorded state (`registered` / `waitlisted` / `cancelled` /
   `attended`). An event's `seats_taken`, `waitlist_count`, and
   `seats_open` are **derived at read** from the registrations,
   never stored. A full event wait-lists new registrations;
   promotion is an explicit recorded state change, and promoting
   into a full event is rejected.
4. **Training authorization (SF-182) records** — authorizations
   (`aut-`) recorded from `requested` to a recorded decision
   (`approved` / `declined`). **The decider is never the record's
   creator** (separation of duties, enforced in the store).
5. **Individual development plan records** — IDPs (`idp-`): goal,
   optional target date, planned activities as data.
6. **Competency records** — competency definitions (`cpt-`) and
   learner competency records (`lcr-`) with the level recorded
   **verbatim** in the caller's own scale. Nothing ranks or
   converts levels.
7. **Learner progress records** — progress records (`prg-`) with
   status (`not_started` / `in_progress` / `completed`),
   readiness, and percent; completion is the terminal progress
   state. Records only — no content delivery, no scoring.
8. **Learning experience records (LRS statements)** — statements
   (`stm-`): learner reference, verb, object reference, context,
   optional result text recorded **verbatim, never parsed**. The
   shape is pinned to exactly eight keys; **there is no score
   field** (the description contains no scoring vocabulary at
   all — the only "scor" substring in it is inside "SCORM").
9. **Mandatory training compliance & derived status** —
   assignments (`asg-`) with a due date. **Status is never
   stored**: it is derived at read time, deterministically, from
   the assignment, the due date, the learner's progress records,
   and an explicit `as_of` reference date — `completed` when a
   completed progress record exists, `overdue` when `as_of` is
   after the due date, `current` otherwise.
10. **Workflow & notification registries** — workflow definitions
    (`wfl-`) registered as data and **never executed** (pinned by
    test); notification records (`ntf-`). Delivery is Extended.
11. **Search & summary reporting** — substring search over
    courses, content items, learners, and events; a summary
    report of counts by family and state, with compliance counts
    by derived status at `as_of`. Counts — never scores.
12. **REST API** — every function above over JSON HTTP.
13. **RBAC** — `admin` / `instructor` / `learner` / `auditor`
    roles with a permission matrix enforced before any state
    change, plus learner scope: a learner-role actor can only
    read records whose `learner_ref` is their own.
14. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `lrn-`, `crs-`,
`cnt-`, `les-`, `evt-`, `reg-`, `aut-`, `idp-`, `cpt-`, `lcr-`,
`prg-`, `stm-`, `asg-`, `wfl-`, `ntf-`. Permission is checked
before any state change or id allocation. Dates are ISO strings
(due/target dates `YYYY-MM-DD`; event times ISO-8601 datetimes);
compliance derivation takes an explicit `as_of` date so it never
depends on the wall clock.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m lms serve --host 127.0.0.1 --port 8794
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

As a library:

```python
import sys; sys.path.insert(0, "src")
from lms.access import User
from lms.audit import AuditLog
from lms.store import LmsStore

audit = AuditLog()
store = LmsStore(audit=audit)
admin = User("alice", "admin"); instructor = User("bob", "instructor")
learner = store.create_learner("carol", "Carol Learner", admin)
course = store.create_course("Safety Basics", admin, code="SAFE-101")
store.create_compliance_assignment("carol", course["id"], "2026-06-01", admin)
print(store.compliance_status("asg-1", admin, as_of="2026-06-15"))
# {'assignment_id': 'asg-1', ..., 'status': 'overdue', 'completed': False, 'as_of': '2026-06-15'}
```

## Demo users, roles, and permissions

Demo identities (documented demo users, not an identity
provider — production identity belongs to the embedding
organization). Callers authenticate with `X-User` / `X-Role`
headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including catalog/learner/compliance writes and reading the audit log |
| `bob` | instructor | all record reads except the audit log; registration, authorization, plan, competency, progress, experience, and workflow writes; reports and search |
| `carol` | learner | record reads only, scoped to records whose `learner_ref` is `carol` |
| `dana` | auditor | all record reads plus reports/search and the audit log; no writes |

Permission actions: `catalog_read/write`, `learner_read/write`,
`registration_read/write`, `authorization_read/write`,
`plan_read/write`, `competency_read/write`, `progress_read/write`,
`experience_read/write`, `compliance_read/write`,
`workflow_read/write`, `report_read`, `audit_read`. Lesson plans
are catalog records (`catalog_write`); `plan_write` covers
individual development plans.

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin + auditor; `{"entries": [...]}` |
| `GET /report` (`?as_of=`) | report_read | counts over the records |
| `GET /search?q=` | report_read | substring search; missing/empty `q` → 400 |
| `GET /learners` · `POST /learners` | learner_read / learner_write | create → 201 |
| `GET /learners/{id}` | learner_read | |
| `GET /courses` · `POST /courses` | catalog_read / catalog_write | create → 201 |
| `GET /courses/{id}` | catalog_read | |
| `GET /content-items` (`?course_id=`) · `POST /content-items` | catalog_read / catalog_write | create → 201 |
| `GET /content-items/{id}` | catalog_read | |
| `GET /lesson-plans` (`?course_id=`) · `POST /lesson-plans` | catalog_read / catalog_write | create → 201 |
| `GET /lesson-plans/{id}` | catalog_read | |
| `GET /events` (`?course_id=`) · `POST /events` | registration_read / registration_write | create → 201; list/get return derived seat counts |
| `GET /events/{id}` | registration_read | view includes `seats_taken`, `waitlist_count`, `seats_open` |
| `GET /registrations` (`?event_id=`, `?learner_ref=`) · `POST /registrations` | registration_read / registration_write | create → 201 |
| `GET /registrations/{id}` · `POST /registrations/{id}/state` | registration_read / registration_write | |
| `GET /authorizations` (`?learner_ref=`) · `POST /authorizations` | authorization_read / authorization_write | create → 201 |
| `GET /authorizations/{id}` · `POST /authorizations/{id}/decide` | authorization_read / authorization_write | decider ≠ creator |
| `GET /development-plans` (`?learner_ref=`) · `POST /development-plans` | plan_read / plan_write | create → 201 |
| `GET /development-plans/{id}` | plan_read | |
| `GET /competencies` · `POST /competencies` | competency_read / competency_write | create → 201 |
| `GET /competencies/{id}` | competency_read | |
| `GET /learner-competencies` (`?learner_ref=`, `?competency_id=`) · `POST /learner-competencies` | competency_read / competency_write | create → 201 |
| `GET /learner-competencies/{id}` | competency_read | |
| `GET /progress` (`?learner_ref=`, `?course_id=`) · `POST /progress` | progress_read / progress_write | create → 201 |
| `GET /progress/{id}` | progress_read | |
| `GET /statements` (`?learner_ref=`, `?object_ref=`) · `POST /statements` | experience_read / experience_write | create → 201 |
| `GET /statements/{id}` | experience_read | |
| `GET /compliance` (`?as_of=`, `?learner_ref=`) · `POST /compliance` | compliance_read / compliance_write | create → 201 |
| `GET /compliance/{id}` (`?as_of=`) · `GET /compliance/{id}/status` (`?as_of=`) | compliance_read | derived status |
| `GET /workflows` · `POST /workflows` | workflow_read / workflow_write | create → 201; definitions only, never executed |
| `GET /workflows/{id}` | workflow_read | |
| `GET /notifications` (`?recipient_ref=`) · `POST /notifications` | workflow_read / workflow_write | create → 201 |
| `GET /notifications/{id}` | workflow_read | |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown
user or role mismatch, 403 permission, 404 not found. Denied
attempts are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/learning-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 104 tests
```

**104 tests, all passing**, including the mutation-verified
negative control: patching the overdue branch of the compliance
derivation to always read `current` makes exactly 9 tests fail
(see `tests/README.md` for the drill record).

## Honesty

- The build implements the learning **records substrate** the
  fork's public description actually presupposes. The engines
  are not in it: no Moodle delivery runtime, no SCORM/cmi5
  packaging or distribution, no xAPI protocol endpoints, no EHRI
  feed, no analytics engine, no career-mapping or survey engine,
  no wiki or CMS product, no authoring tool, no form rendering
  or signature workflow, no workflow execution, no notification
  delivery. Each is named as an Extended gap in `UNION-SPEC.md`
  for the final batch.
- Compliance status and event seat counts are **derived, never
  stored** — the stored assignment record has no status field
  and the stored event record has no seat fields; both are
  computed from the record set at an explicit reference point.
- Nothing in this build confers anything: authorizations record
  decisions made by people, competency records hold levels
  people recorded, progress records hold states people recorded.
  No credential is issued (the category claims none), no score
  is computed (no record shape carries a score field, pinned by
  test), and no workflow executes.
- The adjacent products inside the enclave (a hardened wiki, a
  hardened CMS, a talent platform) are claimed by the fork and
  specified as Extended; they are not learning functions and the
  substrate does not pretend to be them.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization (the fork's MFA/SSO
  claim is a property of its platform). Encryption is TLS when
  a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment; the fork claims multi-tenancy, which is
  a deployment property, stated here plainly.
- Claims discipline: every function above traces to a claim in
  `specs/specs.json` (26 evidenced claims across the 1 fork) or
  to the Moderate/L2 control families in `UNION-SPEC.md`. Counts
  are a floor, stated as such.
