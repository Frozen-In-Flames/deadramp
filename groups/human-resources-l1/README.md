# Human Resources L1 — singleton build (Operation DeadRamp, Phase 2 remainder)

This is the clean-room implementation of the **Human Resources
L1 singleton**: **1 fork** from the FedRAMP Marketplace at the
lightest tier — **QGenda** (Qgenda, LLC), FedRAMP **LI-SaaS**,
FedRAMP Certified — built per the group's union spec
([`UNION-SPEC.md`](UNION-SPEC.md)) under the singleton pipeline
(same pipeline, group size one). LI-SaaS is FedRAMP's tailored
subset of the Low baseline for SaaS offerings; the group's union
baseline is the Low baseline ⇔ CMMC L1 (FAR 52.204-21).

**Read the honesty section before the function list.** This
fork's public description evidences exactly **one** function
family under the category taxonomy (applied verbatim from Group
21) — `ai_automation`, claimed on the recorded basis "scheduling
automation" (no AI wording appears anywhere in the description)
and Extended, not built — and its headline function, workforce
call/scheduling for healthcare organizations, has **no taxonomy
family at all** and is recorded as a gap. The build below is
therefore the category's HR records substrate **carried** at
this tier under an explicit core-boundary decision, not a set of
functions this fork was found to claim. The decision, its
reasoning, and its price (full disclosure) are in
`UNION-SPEC.md`. Membership provenance is also recorded there:
`forks.json` files this fork Uncategorized; the Human Resources
category is the remainder census proposal, taken from the fork's
own description.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

**Reuse, stated plainly:** the implementation and test suite are
the shipped Group 21 (Human Resources L2) build's code, reused —
this project's own Apache-2.0 code. A per-file hash comparison
is recorded in `scratch/reuse-note.md`: all 7 `src/` modules and
12 of the 17 carried test files are byte-identical to Group
21's; the 5 differing test files differ in documentation wording
only; Group 21's `test_additions.py` is not carried (it pins
that group's remainder additions); and one test file is new
(the singleton spec pins). **The baseline claim is not reused.**
Everything Group 21 says about Moderate / NIST SP 800-171 stays
in Group 21. This group's claims are the Low baseline's and FAR
52.204-21's only, as written in `UNION-SPEC.md`.

## Privacy discipline (hard rule)

Records and opaque caller-supplied references only. A person
record is exactly `{id, person_ref, kind, status, created_by,
created_utc}`: the `person_ref` is an opaque string the caller
supplies, and **no field anywhere in this build holds a real
name, an SSN, a date of birth, a salary or compensation figure,
an address, a phone number, or an email address** — those fields
do not exist in any entity shape, by design, and
`tests/test_privacy.py` asserts the exact person key set and
walks one record of every entity type against a forbidden-key
set. For this fork the rule bites in a specific place: a
scheduling platform's real records are rosters of named
clinicians — this substrate holds neither names nor schedules.
Position records carry an occupational series and grade because
those are *classification* attributes of the position family;
they are not pay data, and no compensation field exists. Salary
/ compensation administration is a verified named absence at
this tier (see Honesty).

## The 12 core functions (carried substrate)

1. **Person records** — anchor records (`per-`) keyed by an
   opaque `person_ref` (unique; duplicates rejected), kind
   (`applicant` / `employee`) and lifecycle status (`applicant`
   / `active` / `separated`). Every other person-bound record
   requires the person to exist.
2. **Position & classification records** — position records
   (`pos-`) with title, occupational series, grade,
   organization, and status (`vacant` / `filled` / `abolished`).
   Series/grade *recommendation* tools are Extended.
3. **Vacancy announcement records** — announcements (`vac-`)
   bound to positions, with open/close dates and states
   (`draft` / `posted` / `closed`).
4. **Application records & stage tracking** — applications
   (`app-`) binding a `person_ref` to a vacancy, with stage
   (`applied` / `screened` / `referred` / `selected` /
   `not_selected` / `withdrawn`); a duplicate active
   application is rejected. The `referred` stage is where
   candidate referral and certificates of eligibles live as
   records; matching/ranking engines are Extended.
5. **Evaluation records** — hiring-assessment and SME panel
   review records (`evl-`) bound to applications, with rater
   entries (`rater_ref`, numeric rating, comment) recorded
   verbatim. **There is deliberately no aggregate field**:
   weighted cumulative / consensus scoring is a computation,
   and computation is Extended — the substrate records human
   ratings only.
6. **Lifecycle case records (onboarding & separation)** — cases
   (`lif-`) binding a `person_ref`, kind (`onboarding` /
   `separation`), and task checklists (task states `pending` /
   `done` / `waived`). **Case status is never stored**: it is
   derived at read time from the task states — `not_started`
   when no task has been touched, `in_progress` when some but
   not all tasks are done/waived, `complete` when every task is
   done or waived; `cancelled` is an explicit recorded event
   flag.
7. **Performance review cycle records** — review records
   (`rev-`) binding a `person_ref` to a cycle/period, with
   states (`planned` / `in_progress` / `completed`) and an
   optional recorded outcome label. Calibration and goal
   engines are Extended.
8. **Benefits & retirement records** — benefits-enrollment
   records and retirement case records (`ben-`) with an opaque
   plan reference and state (`pending` / `active` / `closed`).
   The retirement benefits **calculator** is an engine and is
   Extended.
9. **Personnel action & case records** — case records (`cas-`)
   with kinds (`personnel_action` / `award` / `labor_relations`
   / `general`) and routing states (`opened` / `in_review` /
   `closed`).
10. **Reporting over the records** — counts/summaries over
    persons, positions, vacancies, applications (by stage),
    evaluations, lifecycle cases (by **derived** status),
    performance reviews, benefits records, and cases.
    Reporting/visualization engines are Extended.
11. **RBAC** — `admin` / `hr_specialist` / `employee` /
    `auditor` roles with a permission matrix enforced before
    any state change, plus employee scope: an employee-role
    actor can only read records whose `person_ref` is their
    own.
12. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `per-`, `pos-`,
`vac-`, `app-`, `evl-`, `lif-`, `rev-`, `ben-`, `cas-`.
Permission is checked before any state change or id allocation.
Dates are ISO strings (`YYYY-MM-DD`); lifecycle derivation is a
pure function of the task states and never depends on the wall
clock.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m hr serve --host 127.0.0.1 --port 8793
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from hr.access import User
from hr.audit import AuditLog
from hr.store import HrStore

audit = AuditLog()
store = HrStore(audit=audit)
admin = User("alice", "admin"); specialist = User("bob", "hr_specialist")
store.create_person("STAFF-2042", admin, kind="employee")
case = store.create_lifecycle_case(
    "STAFF-2042", "onboarding", specialist,
    task_titles=["Credentialing file opened", "Schedule profile created"])
store.set_task_state(case["id"], "t-1", "done", specialist)
print(store.get_lifecycle_case(case["id"], specialist)["status"])
# 'in_progress' — derived from the task states, never stored
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User    | Role          | Permissions |
|---------|---------------|-------------|
| `alice` | admin         | all reads + all writes, plus `audit_read` |
| `bob`   | hr_specialist | all record reads + all record writes + `report_read`; no `audit_read` |
| `carol` | employee      | record reads only, own records only (employee scope); no writes, no `report_read`, no `audit_read` |
| `dana`  | auditor       | all record reads + `report_read` + `audit_read`; no writes |

Read actions: `person_read`, `position_read`, `vacancy_read`,
`application_read`, `evaluation_read`, `lifecycle_read`,
`performance_read`, `benefits_read`, `case_read` (all roles,
employee-scoped by `person_ref`; positions and vacancies are
org-level and unscoped). Write actions: the matching `*_write`
actions (admin + hr_specialist). `report_read` (admin,
hr_specialist, auditor); `audit_read` (admin, auditor). Unknown
roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a
plain string carries identity but no role, so the service layer
— which knows the registry and always passes `User` objects —
is responsible for enforcement in that case (the house
convention).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors
are always JSON `{"error": "..."}` and no stack trace is ever
returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/persons` | person_read | `{"persons": [...]}` |
| POST | `/persons` | person_write | Body `{"person_ref", "kind"?}` → 201 person |
| GET | `/persons/{id}` | person_read | One person record (employee-scoped) |
| POST | `/persons/{id}/status` | person_write | Body `{"status"}` → record |
| GET | `/positions` | position_read | `{"positions": [...]}` |
| POST | `/positions` | position_write | Body `{"title", "series"?, "grade"?, "organization"?}` → 201 position |
| GET | `/positions/{id}` | position_read | One position record |
| POST | `/positions/{id}/status` | position_write | Body `{"status"}` → record |
| GET | `/vacancies?position_id=` | vacancy_read | `{"vacancies": [...]}` |
| POST | `/vacancies` | vacancy_write | Body `{"position_id", "title", "opens_on"?, "closes_on"?}` → 201 vacancy |
| GET | `/vacancies/{id}` | vacancy_read | One vacancy record |
| POST | `/vacancies/{id}/status` | vacancy_write | Body `{"status"}` → record |
| GET | `/applications?person_ref=&vacancy_id=` | application_read | `{"applications": [...]}` |
| POST | `/applications` | application_write | Body `{"person_ref", "vacancy_id"}` → 201 application |
| GET | `/applications/{id}` | application_read | One application (employee-scoped) |
| POST | `/applications/{id}/stage` | application_write | Body `{"stage"}` → record |
| GET | `/evaluations?application_id=` | evaluation_read | `{"evaluations": [...]}` |
| POST | `/evaluations` | evaluation_write | Body `{"application_id", "kind", "title"}` → 201 record |
| GET | `/evaluations/{id}` | evaluation_read | One evaluation record (employee-scoped via its application) |
| POST | `/evaluations/{id}/entries` | evaluation_write | Body `{"rater_ref", "rating", "comment"}` → record (stored verbatim, never aggregated) |
| POST | `/evaluations/{id}/state` | evaluation_write | Body `{"state"}` → record |
| GET | `/lifecycle-cases?person_ref=` | lifecycle_read | `{"lifecycle_cases": [...]}` with derived status |
| POST | `/lifecycle-cases` | lifecycle_write | Body `{"person_ref", "kind", "task_titles"?}` → 201 case (view with derived status) |
| GET | `/lifecycle-cases/{id}` | lifecycle_read | One case with derived status (employee-scoped) |
| POST | `/lifecycle-cases/{id}/tasks` | lifecycle_write | Body `{"title"}` → case view |
| POST | `/lifecycle-cases/{id}/tasks/{task_id}/state` | lifecycle_write | Body `{"state"}` → case view |
| POST | `/lifecycle-cases/{id}/cancel` | lifecycle_write | → case view (derived status `cancelled`) |
| GET | `/performance-reviews?person_ref=` | performance_read | `{"performance_reviews": [...]}` |
| POST | `/performance-reviews` | performance_write | Body `{"person_ref", "cycle", "period_start"?, "period_end"?}` → 201 record |
| GET | `/performance-reviews/{id}` | performance_read | One review record (employee-scoped) |
| POST | `/performance-reviews/{id}/state` | performance_write | Body `{"state", "outcome"?}` → record |
| GET | `/benefits?person_ref=` | benefits_read | `{"benefits": [...]}` |
| POST | `/benefits` | benefits_write | Body `{"person_ref", "kind", "plan_ref"}` → 201 record |
| GET | `/benefits/{id}` | benefits_read | One benefits record (employee-scoped) |
| POST | `/benefits/{id}/state` | benefits_write | Body `{"state"}` → record |
| GET | `/cases?person_ref=` | case_read | `{"cases": [...]}` |
| POST | `/cases` | case_write | Body `{"person_ref", "kind", "title"}` → 201 case |
| GET | `/cases/{id}` | case_read | One case record (employee-scoped) |
| POST | `/cases/{id}/state` | case_write | Body `{"state"}` → record |
| GET | `/report` | report_read | Counts/summaries over the records |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

91 tests. See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **Low** baseline (the FedRAMP
Low baseline; LI-SaaS is its tailored subset for SaaS
offerings), cross-walked to the FAR 52.204-21 practices behind
CMMC L1. Written fresh for this tier — Group 21's Moderate
mapping is not reused (see the precision notes in
`UNION-SPEC.md`):

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store
  and again at the API, with employee scope by `person_ref`;
  the admin/auditor gating of `audit_read` is traced here,
  AC-5/AC-6 not being Low-baseline selections); IA-2
  (identification & authentication — identity is supplied by
  the embedding organization via user/role headers; this
  service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of
  audit records) — claimed on the **FedRAMP Low side only**:
  FAR 52.204-21 / CMMC L1 contains no audit practice, and
  AU-6/AU-9 are Moderate selections not claimed at this tier.
- **CM / SI** — CM-6 (configuration settings — the lifecycle
  derivation, position records, and case kinds are configured
  records; lifecycle status derives from recorded task states);
  SI-10 (information input validation — malformed input is
  rejected, never partially applied, and consumes no ids);
  SC-8 (transmission confidentiality — the server runs over TLS
  when a certificate is configured; encryption at rest is a
  deployment-layer control, stated plainly and not claimed
  here). Group 21's CA-7 and SI-12 citations are not
  Low-baseline selections and are not claimed here.

## Honesty: what is NOT in this build

- **One claim at this tier, and it is Extended.** The
  singleton's description tags exactly one function family
  (`ai_automation`, on "scheduling automation" — automation
  wording with no AI asserted anywhere in the text); no AI
  function and no automation engine is implemented. The 12
  core functions are the Group 21 category substrate carried
  at this tier and flagged carried, not claimed, throughout
  `UNION-SPEC.md`.
- **QGenda's engine is NOT implemented.** No workforce
  scheduling, no call rosters, no schedule optimization, no
  shift or coverage management of any kind. Scheduling is the
  fork's whole described function; the category taxonomy has
  no scheduling family, so it is a named gap for the final
  batch (see `UNION-SPEC.md`), not a feature of this build.
- **Extended capabilities from the L2 union are NOT
  implemented.** No AI talent intelligence or matching, no
  applicant-tracking workflow engine, no classification
  intelligence, no job-analysis tooling, no assessment
  delivery, no scoring computation (evaluation records hold
  human ratings verbatim; no aggregate exists), no certificate
  document assembly, no career sites or recruiting platforms,
  no mobility marketplace, no workforce-planning analytics,
  no retirement benefits calculator, no learning delivery, no
  integration connectors, and no document assembly. Those are
  the union's Extended gaps, named in `UNION-SPEC.md`.
- **Named absences stand at this tier — checked, not
  assumed.** Six functions the category might be expected to
  contain were re-probed against this fork's description and
  all six are absent from it (0 hits each): **leave & time-off
  records, policy acknowledgement records, payroll execution,
  background checks/investigations, salary/compensation
  administration, and time & attendance**. Two of the six were
  retired at L2 by another fork's own words (GDC's Paycheck 8
  asserts leave and time & attendance tracking); QGenda's
  words contain neither, so neither retirement carries to this
  tier. They are not in the Core and not in the Extended list,
  because this fork does not claim them.
- **No real personal data can be stored — by design.**
  Persons are keyed by an opaque caller-supplied `person_ref`;
  no entity shape has a field for a real name, SSN, date of
  birth, salary, address, phone number, or email — or,
  pointedly for this fork, a clinician's name or a shift
  schedule.
- **No scores exist — by design.** Evaluation entries are
  stored verbatim and never parsed, averaged, or aggregated;
  the report counts records and nothing else.
- **Derived, not stored.** Lifecycle case status is computed
  at read time from recorded task states; there is no
  background process advancing cases.
- This build is **single-tenant**: one store, one audit log,
  no tenant isolation.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength, and account lifecycle belong to the
  embedding organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **TLS is available only when a certificate is
  configured**; the default serve mode is plain HTTP for
  local/demo use.
- This build is **not a FedRAMP authorization**, and it does
  not claim one. The control mapping above states which
  baseline families the build's features answer to; nothing
  more. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence.
