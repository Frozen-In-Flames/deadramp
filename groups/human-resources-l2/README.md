# Human Resources L2 — merged build (Operation DeadRamp, Phase 2, Group 21)

This is the merged, clean-room implementation of the **Human
Resources L2** sibling group: **4 forks / vendor platforms** from the
FedRAMP Marketplace that share the same function (Human Resources)
and the same trust tier (CMMC L2, equivalent to FedRAMP Moderate),
built as one open-source service from the group's union contract
(`UNION-SPEC.md`).

The 4 forks: FedHire (Apply Government Solutions) · Avature Limited
(Avature Federal Platform) · Economic Systems Federal Human
Resources Navigator (Economic Systems) · Eightfold Talent
Intelligence Platform (TIP) (Eightfold AI Inc.). All 4 are FedRAMP
Moderate; 38 evidenced claims across the 4 spec sheets in
`specs/specs.json`.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

## What the group is: a records substrate

The claim counts in the union spec prove a **records substrate**,
not a talent engine: persons held as anchor records, positions and
their classification state registered, vacancy announcements posted
as records, applications tracked through stages, assessments and
panel reviews recorded, onboarding and separation worked as task
checklists, performance cycles, benefits and retirement cases, and
personnel actions held as records, with reports produced over those
records. Each vendor's matching, classification-intelligence,
scoring, recruiting, and calculator engines on top of that
substrate are Extended functions (see Honesty). The group is
talent-acquisition-heavy: its largest family is talent acquisition
(3/4), and its AI flagship (Eightfold) is an engine vendor — the
substrate/engine split is the group's defining honesty call.

## Privacy discipline (hard rule)

Records and opaque caller-supplied references only. A person record
is exactly `{id, person_ref, kind, status, created_by,
created_utc}`: the `person_ref` is an opaque string the caller
supplies, and **no field anywhere in this build holds a real name,
an SSN, a date of birth, a salary or compensation figure, an
address, a phone number, or an email address** — those fields do not
exist in any entity shape, by design, and `tests/test_privacy.py`
asserts the exact person key set and walks one record of every
entity type against a forbidden-key set. Position records carry an
occupational series and grade because those are *classification*
attributes claimed by the position-classification family; they are
not pay data, and no compensation field exists. Salary/compensation
administration is a verified named absence (0/4) in the union spec.

## The 12 core functions

1. **Person records** — anchor records (`per-`) keyed by an opaque
   `person_ref` (unique; duplicates rejected), kind
   (`applicant` / `employee`) and lifecycle status (`applicant` /
   `active` / `separated`). Every other person-bound record requires
   the person to exist.
2. **Position & classification records** — position records (`pos-`)
   with title, occupational series, grade, organization, and status
   (`vacant` / `filled` / `abolished`): the record form of FedHire's
   Position Classification and Econ's PD+ position management
   repository. The series/grade *recommendation* tools are Extended.
3. **Vacancy announcement records** — announcements (`vac-`) bound
   to positions, with open/close dates and states (`draft` /
   `posted` / `closed`).
4. **Application records & stage tracking** — applications (`app-`)
   binding a `person_ref` to a vacancy, with stage (`applied` /
   `screened` / `referred` / `selected` / `not_selected` /
   `withdrawn`); a duplicate active application is rejected. The
   `referred` stage is where candidate referral and certificates of
   eligibles live as records; matching/ranking engines are Extended.
5. **Evaluation records** — hiring-assessment and SME panel review
   records (`evl-`) bound to applications, with rater entries
   (`rater_ref`, numeric rating, comment) recorded verbatim.
   **There is deliberately no aggregate field**: FedHire's weighted
   cumulative / consensus score is a computation, and computation is
   Extended — the substrate records human ratings only.
6. **Lifecycle case records (onboarding & separation)** — cases
   (`lif-`) binding a `person_ref`, kind (`onboarding` /
   `separation`), and task checklists (task states `pending` /
   `done` / `waived`). **Case status is never stored**: it is
   derived at read time from the task states — `not_started` when
   no task has been touched, `in_progress` when some but not all
   tasks are done/waived, `complete` when every task is done or
   waived; `cancelled` is an explicit recorded event flag.
7. **Performance review cycle records** — review records (`rev-`)
   binding a `person_ref` to a cycle/period, with states (`planned`
   / `in_progress` / `completed`) and an optional recorded outcome
   label. Calibration and goal engines are Extended.
8. **Benefits & retirement records** — benefits-enrollment records
   and retirement case records (`ben-`) with a plan reference and
   state (`pending` / `active` / `closed`). The retirement benefits
   **calculator** is an engine and is Extended.
9. **Personnel action & case records** — case records (`cas-`) with
   kinds (`personnel_action` / `award` / `labor_relations` /
   `general`) and routing states (`opened` / `in_review` /
   `closed`): the record form of Econ's forms-and-cases routing and
   Avature's Case Management; the awards and labor-relations
   families live here as case kinds.
10. **Reporting over the records** — counts/summaries over persons,
    positions, vacancies, applications (by stage), evaluations,
    lifecycle cases (by **derived** status), performance reviews,
    benefits records, and cases. Reporting/visualization engines
    are Extended.
11. **RBAC** — `admin` / `hr_specialist` / `employee` / `auditor`
    roles with a permission matrix enforced before any state change,
    plus employee scope: an employee-role actor can only read
    records whose `person_ref` is their own.
12. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries. Unusually for a baseline hook,
    audit has descriptive claim support in this group (FedHire
    documents panel records "for audit purposes" and ships audit
    review modules).

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `per-`, `pos-`,
`vac-`, `app-`, `evl-`, `lif-`, `rev-`, `ben-`, `cas-`. Permission
is checked before any state change or id allocation. Dates are ISO
strings (`YYYY-MM-DD`); lifecycle derivation is a pure function of
the task states and never depends on the wall clock.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m hr serve --host 127.0.0.1 --port 8793
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
from hr.access import User
from hr.audit import AuditLog
from hr.store import HrStore

audit = AuditLog()
store = HrStore(audit=audit)
admin = User("alice", "admin"); specialist = User("bob", "hr_specialist")
store.create_person("carol", admin, kind="employee")
case = store.create_lifecycle_case(
    "carol", "onboarding", specialist,
    task_titles=["Entrance-on-duty forms", "Provisioning"])
store.set_task_state(case["id"], "t-1", "done", specialist)
print(store.get_lifecycle_case(case["id"], specialist)["status"])
# 'in_progress' — derived from the task states, never stored
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

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

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case (the house convention).

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

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

77 tests, all passing at delivery (independently re-run by the
coordinator). See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record. A live
smoke (`scratch/smoke.py`) drives the store and the HTTP service end
to end, including a lifecycle case whose derived status reaches
`complete` and the report counts that follow from it.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline cross-walked to
the NIST SP 800-171 practices behind CMMC L2, per the union spec's
traceability table:

| Core function | Control families | How the build answers |
|---|---|---|
| Person records | AC-2, AU-2, SI-12 | Anchor records are explicit and auditable; opaque references only, no identifier fields exist |
| Position & classification records | CM-6, SI-12 | Positions are configuration-controlled registry records; nothing is announced that is not registered |
| Vacancy announcement records | AU-2, CM-6 | Announcements are explicit records bound to registered positions, with controlled states |
| Application records & stage tracking | AC-2, AU-2 | Every candidacy is an explicit, auditable record; stage changes are events on the record |
| Evaluation records | AU-2, AU-3, SI-10 | Ratings and comments are recorded verbatim with content; inputs validated before any record exists; no computed aggregate |
| Lifecycle cases & derived status | AU-6, CA-7, CM-6 | Status is derived deterministically from task states; derivation is queryable and reviewable, never stored |
| Performance review cycle records | AU-6, SI-12 | Review state is a reviewable record per person and cycle, retained with the record set |
| Benefits & retirement records | AU-2, SI-12 | Enrollment/case state changes are auditable events on retained records (records only — no calculator) |
| Personnel action & case records | AU-2, AU-3, SI-10 | Cases are explicit records with routing states; every transition is audited |
| Reporting over the records | AU-6, CA-7 | Reports read the substrate records only; no side-channel data |
| RBAC (admin/hr_specialist/employee/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; identity itself is supplied by the embedding organization (see Honesty) |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

## Honesty: what is Core, what is Extended, what is NOT in this build

**Core vs Extended.** The Core is exactly the 12 functions above:
10 claim-supported by the spec sheets, RBAC baseline-supported with
thin descriptive claims (1/4 explicit), and the audit log
claim-supported (2/4) as well as baseline-required. Everything else
in the union spec's long tail is **Extended and NOT implemented**
here; it is reserved for the final gap batch. The gap list, by name,
exactly as registered:

1. AI talent intelligence & matching engines (Eightfold's AI matching over the talent lifecycle)
2. Applicant-tracking workflow engines (end-to-end hiring workflow automation, JOA posting/sync with external job boards)
3. Position classification intelligence (occupational-series & grade recommendation tools, classification-library comparison/suggestions)
4. Job analysis & crediting-plan tooling (competency frameworks, assessment-strategy builders)
5. Assessment delivery via third-party providers & assessment content/methodologies
6. Weighted cumulative & consensus scoring computation (panel ratings are Core records; computing aggregates is an engine)
7. Certificates of eligibles as standalone assembled documents/artifacts (the referral stage is Core)
8. Career sites, talent communities, campus recruiting & events platforms
9. Talent mobility & workforce-exchange marketplace engines
10. Talent management suite depth (retention & workforce-development programs beyond records)
11. Workforce planning & resource-management analytics/models
12. Retirement benefits calculator
13. Employee learning & upskilling delivery
14. Integration connector engines (USAJOBS, eOPF, NFC, IBC, agency HRIS sync)
15. Document & template assembly engines (classification documents, onboarding form population, agency-branded templates)
16. General cloud hosting / platform services (multi-tenancy as a deployment property)

**Named absences — checked, not assumed.** Six functions the
category might be expected to contain appear in **0 of 4**
descriptions (broad patterns over the full texts, recorded in the
union spec): **leave & time-off records, policy acknowledgement
records, payroll execution, background checks/investigations,
salary/compensation administration, and time & attendance**. They
are not in the Core and not in the Extended list, because no sibling
claims them; payroll's only trace is the NFC named as an integration
target. (Leave balances and policy acknowledgements were the
obvious substrate candidates going in — the claims do not support
them, so they are findings, not features.)

**No computed scores.** Evaluation support is records: human
ratings and narrative comments stored verbatim. FedHire's weighted
cumulative and consensus scoring is a computation over those
records and is Extended; no aggregate, average, or total field
exists anywhere in this build.

**Privacy is structural, not procedural.** The build does not
"handle PII carefully" — it has no fields capable of holding it.
Person records are opaque references; nothing in any entity shape
accepts a name, SSN, birth date, pay figure, address, phone, or
email, and the privacy tests assert this on the shapes themselves.

**Thin claims, flagged where they sit.** Person records rest on
thin explicit wording (FedHire's "applicant record" is the anchor
phrase) and are included as the anchor record every other claimed
record binds to. RBAC's descriptive support is one inter-agency
"granted access" phrase (1/4); it is Core because the L2/Moderate
baseline requires it. Benefits records rest on one sibling's
supported-functions list (1/4). All three flags are stated in the
union spec where the functions are defined.

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
cloud hosting are deployment properties, not HR functions.

**Tier caveat.** FedRAMP authorizes products; CMMC certifies
organizations. The L2 / FedRAMP Moderate equivalence used here is a
planning/matching equivalence only. This build is **not a FedRAMP
authorization and confers no CMMC certification**, and it claims
neither.

## Remainder additions (2026-10-31)

The remainder census unit `addition:human-resources-l2` appended
3 previously uncategorized forks to this group — GDC Integration
General Support System (GSS), Government Retirement & Benefits
GRB Platform, and Perceptyx Insights Platform — spec'd under the
group's existing 25-family taxonomy applied verbatim (proven by
exact reproduction of the original claim tables). See
`ADDENDUM.md` for the full record. In brief: **11 new claims**
(group total 49 across 7 forks, 7 of 7 claiming); **the core is
unchanged** (`src/` byte-identical; the additions' claims all ride
the shipped records forms); **tests 77 → 89, all passing**, with
the group's signature lifecycle-derivation drill re-run in this
tree (exactly 7 failures under mutation: the original 5 plus 2
from the additions module). The group's character broadens from
hiring-centric to post-hire operations: reporting & analytics
becomes the largest family (4 of 7), and benefits & retirement
gains a substantive specialist (GRB). Two of the six named
absences above are **retired** by GDC's own prose — leave &
time-off and time & attendance are asserted in substance by its
Paycheck 8 module — and enter the gap registry as a time,
attendance & leave tracking engine for the final batch, alongside
5 further new gaps named in `ADDENDUM.md` §5 (org-chart
automation, the employee survey & listening platform, GRB's
administration depth, the self-service portal, uniform allowance
processing). The payroll absence stands: the word's single
appearance in the enlarged group is GRB naming an external
payroll/HRIS system it interfaces with.
