# Education & Training — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **6 untiered forks** of Education &
Training — census unit `untiered:Education & Training` in
`../../remainder.json`, the eighth untiered set built under the
remainder pipeline. **This is an untiered set, and that means
something specific:** every member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no baseline
for these offerings, so **tier stays null**: no tier is assigned, no
CMMC equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec sheets are in
[`specs/specs.json`](specs/specs.json), each recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

This category is Education & Training — a different category from
Learning Management, which has its own groups, taxonomy, and
substrate; nothing here is borrowed from them.

The 6 forks were spec'd under the category's existing 21-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Education & Training L2 group's
original shipped claim tables exactly — **8 of 8 forks, 43 of 43
claims, deep-equal** — before tagging this set. Result here: **29
claims** across the set (30 raw hits, 1 removed in the exclusion
pass: Toonimo's certification hit rested on its own FedRAMP
target-certification sentence), **5 of 6 forks claiming at least
one**; the one zero-claim fork (FR1916744879, Proofpoint Security
Awareness Training) is recorded under Named absences in the union
spec, not hidden or repaired.

The build implements the category's **ten-function substrate** —
the records machinery every sibling's output presupposes — carried
**byte-identical** from the founding Education & Training L2 build
(`../education-training-l2/src/learn/`, 7 of 7 modules; SHA-256
accounting below). The substrate is tier-independent records code:
the founding source contains no tier machinery, so there was
nothing tier-shaped to strip. Where the founding contract's text
justifies RBAC and the audit log partly as Moderate-baseline hooks,
read it here as **baseline-neutral hooks**: at tier null they are
substrate, claimed against no baseline.

## The 6 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2700137041 | Dossier | Dossier for Government | 9 |
| FR1912662229 | KnowBe4, Inc. | KnowBe4 Security Awareness Training | 7 |
| FR2635447609 | MyEvaluations.com Inc. | MyEvaluations | 6 |
| FR2633734917 | Simuhealth Technologies Inc. | Simuhealth | 5 |
| FR2635050850 | Toonimo Inc. | Toonimo Digital Adoption Platform | 2 |
| FR1916744879 | Proofpoint, Inc. | Proofpoint Security Awareness Training | 0 |

In `forks.json` the set is mixed as filed: 1 fork carries the
Education & Training category (Dossier), 2 are filed
"Uncategorized (none in source)" (KnowBe4, Proofpoint), 2 are filed
under Analytics (MyEvaluations, Simuhealth), and 1 under Customer
Service (Toonimo); the census assigned all 6 to this category from
their own descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span Initial Implementation (4)
and FedRAMP In Process (2) — a status is record data, not a claim.

## The 10 core functions

1. **Course/catalog & training program registry** — courses and
   programs as records (`crs-`), configuration-controlled: nothing
   is offered that is not registered. *Support in this set:
   `course_catalog` 4/6.*
2. **Enrollments & candidate registrations** — records (`enr-`)
   binding a learner/candidate to a registry entry; duplicate
   active enrollments are rejected. *Support: 1/6 (KnowBe4's
   self-service enrollment) — thin, stated plainly.*
3. **Learner progress & readiness records** — per-learner progress
   records (`prg-`) with status (`not_started` / `in_progress` /
   `completed`), readiness level, and percent; completion is
   recorded as the terminal progress state. Records only — no
   content delivery. *Support: 2/6.*
4. **Assessment records** — administration records (`asm-`):
   program/course, learner/candidate, optional session,
   administration state, and item responses held verbatim as
   records. **No scoring** — deterministic scoring was ruled
   Extended by the founding group at 0 claims, and this set's
   descriptions use no score/grade wording either. *Support: 2/6.*
5. **Certificate/credential records** — certification, licensure,
   and credential records (`cred-`) and their tracked status.
   **Records only — no issuance engine.** *Support: 2/6
   (MyEvaluations' credentialing; Dossier's at records weight —
   certification documents held as supporting attachments).*
6. **Compliance assignments & derived status** — assignments
   (`cmp-`) with a due date. **Status is never stored**: it is
   derived at read time, deterministically, from the assignment,
   the due date, the learner's progress records, and an explicit
   `as_of` reference date — `completed` when a completed progress
   record exists for the learner+course, `overdue` when `as_of` is
   after the due date, `current` otherwise. *Support in this set:
   the `compliance_training` family stands at 0/6 — the word
   "compliance" occurs in none of the six descriptions — so this
   function is **carried, not claimed** at family level; its inputs
   (assessment schedules, overdue flags) are claimed by Dossier
   under `assessments` / `scheduling`. Flagged here and in the
   union spec, exactly as the founding spec flagged its own
   reaches past the counts.*
7. **Scheduling records** — training and assessment session
   records (`sch-`) bound to registry entries and enrolled
   learners. *Support: 4/6.*
8. **Reporting over the records** — counts/summaries over registry,
   enrollments (incl. per-course), progress, assessments,
   credentials, compliance status (derived, at `as_of`), and
   sessions. Reporting/dashboard engines are Extended. *Support:
   5/6.*
9. **RBAC** — `admin` / `instructor` / `learner` / `auditor` roles
   with a permission matrix enforced before any state change, plus
   learner scope: a learner-role actor can only read records whose
   `learner_id` is their own. *Support: 1/6 explicit (Dossier's
   "role-based access control") — the same thin support the
   founding group recorded for its own set.*
10. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries. *Support in this
    set: no taxonomy family exists for audit in this category, but
    Dossier asserts "audit logging" in its own service sentence —
    documented-prose support (see Documented control claims),
    stronger than the founding group's 0/8 descriptive support.*

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `crs-`, `enr-`,
`prg-`, `asm-`, `cred-`, `cmp-`, `sch-`. Permission is checked
before any state change or id allocation. Dates are ISO strings
(due/issued/expiry dates `YYYY-MM-DD`; session times ISO-8601
datetimes); compliance derivation takes an explicit `as_of` date
so it never depends on the wall clock.

Functions are **carried** as substrate; no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m learn serve --host 127.0.0.1 --port 8791
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

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
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

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
for enforcement in that case (the founding group's convention,
carried unchanged).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

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

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**74 tests, OK** at delivery: the founding group's 65-test core
suite carried with the code (minus its additions module, which
pins a different census unit), plus 9 spec tests pinning this set
(exactly 6 sheets; membership exact against `remainder.json`; every
sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; 29 claims total with exactly one
zero-claim fork; the exclusion-pass pins). The category's signature
compliance-derivation mutation drill was re-run in this tree —
exactly 8 failures under the mutant, the founding drill's identical
set, store restored and SHA-256 verified (see `tests/README.md`).
A live smoke (`scratch/smoke.py`) also passed: course → enroll →
progress → compliance assignment past due → derived status
`overdue` (the stored record carries no status field) → completion
progress → derived status `completed`; a learner's admin action
denied at the store, 403 over HTTP, and the denied attempt audited.

## Byte-identity accounting

`src/learn/` is carried from the founding group
`../education-training-l2/src/learn/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `fc039601d86f7d877235a8dfc50e23c8d6e474303c5d24a03a08250f40286b3e` |
| `__main__.py` | `6c264b4a3c2caf997f21b06d2362c9f790ade963976200553f42247820394e34` |
| `access.py` | `d769e6203349b942f5d2d42046dbbb05a26b0e135d4689ac83141fedcac9286c` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `3917f305d4b758ddd8a9f7f7d5166ec9711407f630af1ef36e1a78c27954fab4` |
| `service.py` | `1b454836de68a56d8e011f86ea3d32cba60c2407d033eb1993ce0b93dff79075` |
| `store.py` | `f9c8ea1018db3d3ba10fc21bd00a7c592f4adf682d3a23e0fdc6a7417cbd3ffc` |

The test suite is likewise carried (the founding suite minus its
additions module), with one labeling fix in
`tests/learn_helpers.py` (its docstring now names this untiered set
instead of L2) and the new `tests/test_specs.py` added. Full
accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 6 offerings (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with its
evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not the
build's control attainment, and nothing here fills a family in
from any baseline. Dossier's prose statement that its services are
"categorized Low under FIPS 199" is recorded as the fork's own
statement; it does not convert into a registry tier, and the
marketplace record's impact level stays "Unknown".

Documented by at least one fork in the set:

- **Access control (AC)** — 1 fork, family-traced: Dossier for
  Government, via `access_control` ("role-based access control").
- **Audit logging (AU)** — 1 fork, at documented-prose weight:
  Dossier asserts "audit logging" in its own service sentence;
  this category's taxonomy has no audit family, so the assertion
  stands here in the fork's words, not as a taxonomy claim.
- **Cryptographic protection (SC)** — 1 fork, at documented-prose
  weight: KnowBe4 — "All email addresses are encrypted and kept
  private," an assertion about one data type, at exactly that
  weight.
- **Identification & authentication (IA)** — documented **in part**,
  at prose weight: KnowBe4's Active Directory Integration syncs
  user data (directory-based provisioning — not authentication;
  no fork in this set asserts authentication, SSO, or MFA).

**Recorded but NOT documented as a fork's own control claim:**
KnowBe4's use of "FedRAMP compliant Amazon Web Services East …
maintained in an ISO certified facility" (inherited-platform
posture; its "compliant" adjectives are status prose); Toonimo's
authorization-boundary sentence naming leveraged AWS components
including WAF and KMS (a boundary description, not a control the
offering asserts); MyEvaluations' "accreditation workflows" and
Simuhealth's "accreditation evidence management" (their *product
function for customers*, not control claims about themselves — not
documented under CA, and the distinction is stated rather than
blurred).

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, CA, CM, CP, IR, MA, MP, PE,
PL, PM, PS, RA, SA, and SI **as control claims** — is asserted by
no description in the set, beyond the prose-weight notes above. If
the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **Extended functions are specified, not implemented.** The union
  spec ranks 21 functions; the substrate behind 10 is implemented
  here. NOT implemented (claimant counts are this set's):
  phishing simulation & security-awareness training engines
  (KnowBe4 and Proofpoint in substance — KnowBe4's simulated
  phishing does not even fire the `simulations` family, whose
  pattern is the noun "simulation"); training content delivery &
  LMS engines (delivery itself; the records are Core); competency
  management & assessment-cycle engines (Dossier — sign-off
  workflows, proficiency ratings, reassessment cycles); the
  notification & reminder engine (Dossier in substance — the
  founding group's named gap gains a claimant here); medical
  education management engines (MyEvaluations); simulation-center
  operations engines (Simuhealth); digital adoption &
  in-application guidance engines (Toonimo); AI assistants &
  guidance bots (Toonimo — the set's only genuine AI wording; the
  other two `ai_automation` hits are automation wording);
  directory integration & user provisioning sync (KnowBe4);
  career development & clinical ladder engines (Dossier, in
  substance without a family phrase); credentialing & accreditation
  workflow engines (MyEvaluations — credential *records* are
  Core); deterministic scoring & proficiency-rating engines (0
  explicit claims, as in the founding group); recruiting/HCM
  domain suites (1); talent & marketplace matching engines (0 in
  this set); remote proctoring & identity proofing (0 in this set,
  as in the founding group); hosting & multi-tenancy as a platform
  layer (2 at platform-note weight — the build is a single-tenant
  reference deployment and says so).
- **One core function is carried, not claimed, in this set.**
  Compliance assignments & derived status: the
  `compliance_training` family stands at 0 of 6 because the word
  "compliance" occurs in none of the six descriptions — even
  though Dossier's product is competency-obligation tracking and
  claims the derivation's inputs under other families. The flag is
  stated in the union spec's core-boundary decision, not buried.
- **Named absences stand.** Compliance 0/6 (above); training
  delivery phrases 0/6 despite two training products and an LMS;
  talent/skills, performance management, policy management, peer
  collaboration, and data services all 0/6; scoring/grading 0/6;
  proctoring 0/6. Nothing was back-filled to make the set look
  complete, and the taxonomy was not re-tuned for the zero-claim
  fork or any near-miss (see `scratch/ARTIFACTS.md`).
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  `carol`, and `dana` are documented demo identities supplied by
  header; the service enforces the role permission matrix and
  learner scope on those hooks and ships no identity provider, no
  credential store, and no authentication of its own.
