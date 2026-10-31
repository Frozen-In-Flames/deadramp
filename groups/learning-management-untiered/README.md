# Learning Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **1 untiered fork** of Learning
Management — census unit `untiered:Learning Management` in
`../../remainder.json`. **This is an untiered set, and that means
something specific:** the member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no
baseline for this offering, so **tier stays null**: no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The union
contract is [`UNION-SPEC.md`](UNION-SPEC.md); the per-fork spec
sheet is in [`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned
by tests.

**This category is Learning Management — not Education &
Training.** They are separate registry categories with separate
taxonomies and separate builds. `forks.json` files this fork
under Education & Training; the census assigned it to Learning
Management from its own description, and the sheet records both
facts (see the union spec).

The fork was spec'd under the category's existing 26-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding group's shipped claim
tables exactly — **deep-equal on both sheets** (the PowerTrain
founding singleton's 26 claims; the remainder addition's
zero-claim Percipio sheet) — before tagging this set. Result
here: **0 claims**. The fork is a **zero-claim fork**, recorded
plainly: its description is five capability bullets of
virtual-school prose in which no functional pattern phrase of
any of the 26 families appears. The taxonomy was not re-tuned to
manufacture a claim, and the zero is pinned mechanically by the
spec tests, which re-apply the taxonomy and reproduce the empty
table.

The build implements the category's **fourteen-function
substrate** — the learning records machinery the category's
claimed functions presuppose — carried **byte-identical** from
the founding Learning Management L2 build
(`../learning-management-l2/src/lms/`, 7 of 7 modules; SHA-256
accounting below) and re-anchored to tier null. **Claim support
in this set: none** — the set's fork claims nothing, so all
fourteen functions are **carried, not claimed**, stated once in
the union spec's core-boundary decision and repeated in Honesty
below. Where the founding contract's text traces features to the
Moderate/L2 baseline, read it here as **baseline-neutral hooks**:
at tier null they are substrate, claimed against no baseline.

## The fork

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2634357692 | Progressive Expert Consulting | Collaborative Learning Environment | 0 |

The fork's recorded authorization status is Initial
Implementation and its deployment model Public Cloud — record
data, not claims. Its own source record lists business
categories ["Education & Training", "Learning Management"].

## The 14 core functions

1. **Learner registry (opaque references)** — learners (`lrn-`)
   known only by a caller-supplied opaque `ref` and a label; the
   record shape is pinned so no field can hold a real identifier.
2. **Course, content & lesson-plan catalog** — courses/programs
   (`crs-`); content items (`cnt-`) whose `standard` is one of
   the category's own list (`scorm_1_2`, `scorm_2004`, `aicc`,
   `xapi`, `cmi5`, `mp3`, `mp4`, `pdf`, `other`); lesson plans
   (`les-`) referencing catalog entries.
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
   field** anywhere in the build (pinned by a recursive key scan
   in the tests).
9. **Mandatory training compliance & derived status** —
   assignments (`asg-`) with a due date. **Status is never
   stored**: it is derived at read time, deterministically, from
   the assignment, the due date, the learner's progress records,
   and an explicit `as_of` reference date — `completed` when a
   completed progress record exists, `overdue` when `as_of` is
   after the due date, `current` otherwise. This derivation is
   the category's signature invariant and its negative control.
10. **Workflow & notification registries** — workflow definitions
    (`wfl-`) registered as data and **never executed** (pinned by
    test: registering one changes no other record, ever);
    notification records (`ntf-`). Delivery is Extended.
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

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

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
individual development plans. A permitted role performing a
forbidden action gets 403; validation failures get 400; unknown
objects get 404. Errors are always JSON `{"error": "..."}` and no
stack trace is ever returned to a client. Denied attempts are
audited with the action suffixed `:denied`.

## API endpoints

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

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**114 tests, OK** at delivery: the founding group's 104-test
core suite carried with the code (its additions module, which
pins a different census unit, was not carried), plus 10 spec
tests pinning this set (exactly 1 sheet; membership exact
against `remainder.json`; the sheet's tier null / impact
"Unknown"; the description byte-equal to the raw cache under the
founding normalization; the literal 0-claim table, reproduced
mechanically by re-applying the founding taxonomy; the census
citation verifying while serving as no claim's evidence; the
empty certified-services catalogue). The category's signature
compliance-derivation mutation drill was re-run in this tree —
exactly 9 failures under the mutant, the founding drill's
identical set, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/lms/` is carried from the founding group
`../learning-management-l2/src/lms/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `8610cca0b3fa9b98e5f0420d280284affefec7fca93cd6009b923b6419457830` |
| `__main__.py` | `80966d478d796d7d331556212226d581bd63f1dde1f4e2e278da95426baf431b` |
| `access.py` | `940da90748c749ba1f9b8133c91e9a2f2c071e73df7ac345187346636b26813e` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `d9e4a997fb23d209b248172d8356a5452c22cc98167a6859e231412732e443f7` |
| `service.py` | `97405aaa7f8a85dbe1e3b280faffecf0ee3fc08716425dc9d72c56cd3bd27691` |
| `store.py` | `820d97121fd55799b77b417b23d72d26680e22596141ee58e52cfa32bb3bba8a` |

The tree contains exactly the package — no files sit flat at the
`src/` root. The test suite is likewise carried (the founding
suite minus its additions module), with one labeling fix in
`tests/lms_helpers.py` (its docstring now names this untiered set
as the suite's home while keeping its trace to the founding
contract) and the new `tests/test_specs.py` added. Full
accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts, in its own words.

Documented by the fork in this set: **none.** The description
asserts no control language of any family — the tokens
"security", "authentication", "access control", "encrypt",
"audit", and "compliance" each occur zero times in it. Its
"User management" bullet names a product function with no
mechanism stated, so it documents no AC or IA claim; it is
gapped as a function in the union spec.

**Not documented** by the fork: every NIST SP 800-53 control
family — AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PM, PS,
RA, SA, SC, and SI **as control claims** — is asserted by no
sentence in the description. The build's own RBAC and audit
machinery is carried substrate, the build's design — not a
fork's claim and not a baseline. If the source later publishes
an impact level for this offering, the tier is recorded then and
not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for the fork or for
  itself. The fork's recorded authorization status is source
  data, not a claim by this build.
- **Zero claims, plainly.** The set's only fork claims none of
  the category's 26 functions under the verbatim taxonomy. No
  core function is claim-supported in this set; all fourteen are
  carried substrate, not claimed attainments. Nothing was
  back-filled or re-tuned to make the set look claimed.
- **This is Learning Management, not Education & Training.** The
  fork is filed under Education & Training in `forks.json`; the
  census assigned it here from its description. No taxonomy,
  code, or claim was borrowed from the Education & Training
  groups in either direction.
- **Extended functions are specified, not implemented.** NOT
  implemented (all from this fork's own prose, named in
  `UNION-SPEC.md`): the virtual school / virtual classroom
  delivery runtime; real-time collaboration & session recording;
  the course material authoring workspace; the media &
  shared-materials repository service; the assignment,
  evaluation & grading engine; the user administration service;
  and the platform layer. The founding group's seventeen Extended
  gaps stand registered under it; this set adds no claimants to
  them.
- **No score exists anywhere.** No record shape carries a score
  field and nothing computes one — pinned by test. The fork's
  own "grading" word does not change this: grading is the fork's
  function, registered above as an unimplemented gap, and the
  category's taxonomy has no grading family to claim it under.
- **Compliance status and event seat counts are derived, never
  stored** — computed from the record set at an explicit
  reference point, reviewable and reproducible.
- **Workflow definitions never execute.** The registry holds
  definitions as data; registering one changes no other record.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  `carol`, and `dana` are documented demo identities supplied by
  header; the service enforces the role permission matrix on
  those hooks and ships no identity provider, no credential
  store, and no authentication of its own. IA-2 stays with the
  embedding organization. Encryption is TLS when a certificate
  is configured; encryption at rest is a deployment-layer
  property. The deployment is a single-tenant reference
  deployment.
