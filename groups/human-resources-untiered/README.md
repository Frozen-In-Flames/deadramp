# Human Resources — Untiered set (DeadRamp Phase 2, remainder)

**Untiered Set 16: 2 forks, tier null.** An untiered set is a
remainder-census category whose source records publish **no
FedRAMP impact level**: the marketplace data gives no
authorization baseline for these offerings, so this build
assigns **no tier**, draws **no CMMC equivalence**, and asserts
**no control baseline**. It is built to the forks' **documented
control claims** only — the control language their own public
descriptions actually carry (see below) — and every spec sheet
records `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests. This build claims no
FedRAMP authorization and no CMMC certification for any fork or
for itself. Spec: [`UNION-SPEC.md`](UNION-SPEC.md).

## The forks

| Fork (vendor / product) | FedRAMP ID | Source record | Claims |
|---|---|---|---|
| Dayforce / Dayforce HCM, Public Sector | FR2633957417 | impact **Unknown**, status Initial Implementation; deployment Government Community Cloud; filed **Analytics** in the source registry (business categories [Analytics, Finance, Human Resources]); census-assigned to this category | 5 |
| Deltek - Replicon / Replicon Cloud Platform (Enterprise Time Tracking Platform) | F1606087903 | impact **Unknown**, status FedRAMP In Process; deployment Public Cloud; filed **Uncategorized** in the source registry (business categories []); census-assigned to this category | 1 |

Both are spec'd from their own marketplace descriptions, quoted
in full in `specs/specs.json`. **6 claims** across the set
(25-function taxonomy, verbatim from the founding group;
taxonomy-verbatim proof: the founding group's original shipped
claim tables — 4 forks, 38 claims — reproduced exactly before
this set was tagged); **both forks claim at least one family;
there is no zero-claim fork.** The descriptions are uneven
(Dayforce 1,961 characters, Replicon 224), and counts are a
floor: a claim exists only where a fork's own description
contains the family's text.

## The merged build — Core (12 functions)

The build carries the founding Human Resources L2 group's
twelve-function substrate **whole** — the merged
human-resources records machinery the category presupposes —
and re-anchors it to tier null. The founding source contains
**no tier or baseline machinery at all** (no tier string occurs
anywhere in `src/hr/`), so nothing tier-shaped had to change:
where the founding text says "L2 baseline" for RBAC and the
audit log, read baseline-neutral hooks here.

1. **Person records** — people known by opaque `person_ref`
   only, with a kind (employee, candidate, manager, contractor,
   intern, other) and a lifecycle status. **Carried, not claimed
   in this set** (its anchor family, `talent_acquisition`,
   stands at 0 of 2; the founding spec itself flagged this
   anchor thin).
2. **Position & classification records** — positions with org
   unit, occupational series, grade, and the incumbent person
   reference. **Carried** (0 of 2).
3. **Vacancy announcement records** — announcements bound to
   registered positions, with open/close dates and a controlled
   state machine. **Carried** (0 of 2).
4. **Application records & stage tracking** — candidacies of a
   person for a vacancy, moving through
   applied → under_review → referred → selected / not_selected
   / withdrawn. **Carried** (0 of 2).
5. **Evaluation records** — SME/assessment panel entries with
   verbatim score labels and comments per candidate vacancy.
   Human ratings are stored verbatim; **no aggregate is ever
   computed** (no score, average, or total field exists anywhere
   in the build). **Carried** (0 of 2).
6. **Lifecycle case records** — onboarding and separation
   processes as named task checklists. Case status is **derived
   at read time** from the task states (not_started →
   in_progress → complete) and **never stored**; the stored
   record carries no status field. **Carried** (0 of 2).
7. **Performance review cycle records** — per-person, per-cycle
   review state. **Carried** (0 of 2; Dayforce's "workforce
   management" is not this family's phrase).
8. **Benefits & retirement records** — enrollment and case
   records with state transitions (records only — no
   calculator). **Claim-supported in this set** (Dayforce's
   "benefits administration" capability).
9. **Personnel action & case records** — cases of eight kinds
   (personnel_action, discipline, grievance, labor_dispute,
   award, recognition, investigation, other) with routing
   states. **Carried** (0 of 2).
10. **Reporting over the records** — counts and listings read
    from the substrate only; lifecycle counts use derived
    status. **Claim-supported in this set** (Dayforce's
    "analytics, reporting").
11. **Role-based access control** — four roles
    (admin / hr_specialist / employee / auditor) enforced
    before any mutation; employees act only on records bound
    to their own `person_ref`. **Claim-supported in this set**
    (Dayforce's "role-based access control" — full substance,
    where the founding group's own support was a thin
    "granted access" phrase).
12. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp; no mutation API. **Claim-supported in this set**
    (Dayforce's "centralized audit logging" — audit tooling in
    so many words).

**Claim support, stated honestly:** 4 of the 12 functions are
claim-supported by this set's forks (Cores 8, 10, 11, 12 — all
resting on Dayforce's two functional sentences); the other 8
are **carried, not claimed** — the entire hiring chain and the
case families stand at 0 of 2 here. The remaining two claims
land Extended: `integrations` (Dayforce) and `ai_automation`
(Replicon, **automation weight only** — "automating employee
time tracking"; Replicon contains no AI wording and asserts
none). What the claimed families' engines look like beyond
records is the Extended list in the union spec, not this build.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m hr serve --host 127.0.0.1 --port 8793
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**96 tests, all passing at delivery** (77 carried founding
tests + 19 new spec tests pinning membership, tier discipline,
and this set's claim table; independently re-run by the
coordinator). See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record. A
live smoke (`scratch/smoke.py`) drives the store and the HTTP
service end to end, including a lifecycle case whose derived
status reaches `complete` and the report counts that follow
from it. Result at delivery: **SMOKE OK**.

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

| User | Role | Can |
|---|---|---|
| `alice` | admin | Everything, including audit read and reporting |
| `bob` | hr_specialist | All record writes and reads, audit read, reporting |
| `carol` | employee | Read substrate records; write only records bound to her own `person_ref` (own applications, own reviews, case initiation on her own reference, lifecycle-task state changes on her own cases) |
| `dana` | auditor | Read audit log, reporting, and all records except evaluation entries; no writes |

Demo identities are hooks, not an identity provider (see
Honesty).

## API endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /persons`, `POST /persons` | List / register people (opaque refs) |
| `GET /persons/{id}` | Fetch a person record |
| `POST /persons/{id}/status` | Set person lifecycle status |
| `GET /positions`, `POST /positions` | List / create positions |
| `GET /positions/{id}` | Fetch a position |
| `POST /positions/{id}/fill`, `POST /positions/{id}/vacate`, `POST /positions/{id}/close` | Position lifecycle |
| `GET /vacancies`, `POST /vacancies` | List / create vacancy announcements |
| `GET /vacancies/{id}` | Fetch a vacancy |
| `POST /vacancies/{id}/open`, `POST /vacancies/{id}/close`, `POST /vacancies/{id}/cancel` | Vacancy lifecycle |
| `GET /applications`, `POST /applications` | List / submit applications |
| `GET /applications/{id}` | Fetch an application |
| `POST /applications/{id}/stage` | Advance application stage |
| `GET /evaluations`, `POST /evaluations` | List / record panel evaluations |
| `GET /evaluations/{id}` | Fetch an evaluation (auditor excluded) |
| `GET /lifecycle-cases`, `POST /lifecycle-cases` | List / open onboarding & separation cases |
| `GET /lifecycle-cases/{id}` | Fetch a case (derived status in the view) |
| `POST /lifecycle-cases/{id}/tasks` | Append a task |
| `POST /lifecycle-cases/{id}/tasks/{tid}/state` | Set a task state |
| `GET /reviews`, `POST /reviews` | List / open performance reviews |
| `GET /reviews/{id}` | Fetch a review |
| `POST /reviews/{id}/state` | Advance review state |
| `GET /benefits`, `POST /benefits` | List / create benefits & retirement records |
| `GET /benefits/{id}` | Fetch a benefits record |
| `POST /benefits/{id}/state` | Advance benefits state |
| `GET /cases`, `POST /cases` | List / open personnel cases |
| `GET /cases/{id}` | Fetch a case |
| `POST /cases/{id}/state` | Advance case state |
| `GET /report` | Aggregate reporting over the records |
| `GET /audit` | Read the audit log (admin, hr_specialist, auditor) |

All JSON. Mutations require an `X-User` header naming a demo
user; unknown users are denied and the denial is audited.

## Byte-identity accounting

The carried core is verbatim. SHA-256 of every module in
`src/hr/`, identical to the founding group's `src/hr/` at ship
commit `0a14d91` (the founding `store.py` hash is the hash its
own tests README records; the drill below re-verified it):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `569578d5c728a0e37956c86deae5f652603722ec2ae21af2ef4967f2e2dd46a8` |
| `__main__.py` | `d37279e695288d523c8d0ce0a7db95042f8e09d2b47ad3716f4b51b1704d827a` |
| `access.py` | `a2076b19dfcbd3f86ea8492f1544b37640d2f64eb0c4131f5103c7f33ad406df` |
| `audit.py` | `e8a1e7d293458547e89014e9a0de92f9e57ecfc980a43aa13c35e3be854a51e7` |
| `errors.py` | `69a8fe60e3f06b79ae4e7425b0bd897c916988ff238c0f98fed53068cb78e617` |
| `service.py` | `2652bfe38b6e8368b29e525014f1e7ce098d2547c6f9e615503a58060a6985b2` |
| `store.py` | `ec34ab5e55f81b88a027aca6a29d024e18786f4791646dca7213b56f0a1061f0` |

**7 of 7 modules byte-identical** — the founding substrate
contains no tier or baseline machinery (no tier string occurs
anywhere in it), so re-anchoring to tier null changed no code.
The test helpers (`tests/hr_helpers.py`) are carried with one
edit: the docstring now names this untiered set.

## Documented control claims (summary)

**No baseline is asserted.** What the set's forks' own
descriptions document — every item **Dayforce's**; Replicon's
description contains no control language in any form:

- **IA documented** — identity and access management services;
  federated identity via customer-managed IdPs; IAL2/AAL2 with
  multifactor authentication and identity federation.
- **AC documented** — role-based access control, privileged
  access management (the taxonomy's `access_control` claim).
- **AU documented** — centralized audit logging (the taxonomy's
  `audit_compliance` claim).
- **SC documented** — FIPS 140-3 validated cryptographic
  modules, in transit and at rest.
- **CM documented** — continuous monitoring.
- **IR documented** — incident response.
- **RA documented in part** — vulnerability management.
- **CA recorded but NOT documented** — the only assessment
  sentence is part of the fork's authorization assertion (see
  Honesty); it is not credited as an assessment claim.

**Not documented:** AT, CA, CP, MA, MP, PE, PL, PM, PS, SA,
and SI as control claims — asserted by no description in this
set, and never filled from a baseline. The full traceability
(claiming fork + evidence sentence per family) is in
`UNION-SPEC.md`.

## Honesty: what is Core, what is Extended, what is NOT in this build

**Tier null, plainly.** These forks' source records publish no
FedRAMP impact level. Nothing here assigns them Moderate, Low,
or any other level; nothing crosswalks them to a CMMC tier; the
Documented control claims above are the ceiling of what this
build repeats about their controls, and they are the forks'
claims about themselves, not the build's attainment.

**Dayforce's Moderate prose does not move its tier.** Its
description asserts its services "have been independently
assessed as part of the FedRAMP Moderate authorization" and
that it handles "Federal Moderate impact information … in
accordance with FIPS PUB 199 Moderate security requirements."
Its own record says impact **Unknown**, status **Initial
Implementation**. The assertion is recorded (in the union spec
and pinned by test) at exactly that weight: the fork's words,
contradicted by the fork's record, converting to nothing.

**Core vs Extended.** The Core is exactly the 12 functions
above: 4 claim-supported in this set (benefits records,
reporting, RBAC, audit log — the last two on full-substance
control sentences, stronger evidence than the founding group's
own), 8 carried (the hiring chain and case substrates, claimed
by 0 of 2 forks here). The two remaining claims ride two
functions named for the final gap batch, together with every
other Extended function this set's forks describe:

1. Payroll processing engine (Dayforce names payroll among its own capabilities; the founding absence does not stand in this set)
2. Expense tracking & management (Replicon)
3. Project time tracking & resource scheduling engines (Replicon)
4. Employee communications & messaging platform (Dayforce)
5. Document management services (Dayforce; distinct from document & template assembly, which generates documents)
6. Identity federation, privileged access management & identity governance services (Dayforce's documented-control side)
7. Security operations services — continuous monitoring, vulnerability management & incident response engines (Dayforce's documented-control side)
8. Time, attendance & leave tracking engine (already registered from the tiered additions; Replicon's time-and-attendance substance joins it here — leave itself remains absent in this set)
9. Federal retirement & benefits administration platform depth (already registered; Dayforce joins GRB by substance)
10. Integration connector engines (already registered; Dayforce claims integrations here)
11. AI & workflow automation engines (already registered; Replicon's claim is automation wording, no AI asserted)
12. Dashboard & visualization engines beyond registry reporting (already registered)
13. Platform layer — encryption at rest, TLS-when-configured, multi-tenancy (the build performs no cryptography of its own; Dayforce's FIPS 140-3 sentence documents its own modules, not this build's)

**Named absences — checked, not assumed.** The founding group's
six probed absences were re-probed on THIS set's words (full
record in `scratch/ARTIFACTS.md` item 6): **leave & time-off,
policy acknowledgements, background checks, and
salary/compensation administration stand at 0 of 2 here** (the
tiered L2 retirements of the first two rested on a different
fork's words and do not transfer). **Payroll and time &
attendance do not stand** — Dayforce names payroll among its
own capabilities, and Replicon's timesheet/time-tracking
substance is its whole description — but neither has a taxonomy
family, so both are gaps above, not claims and not substrate.
The entire hiring chain (acquisition through separation) is
absent at 0 of 2, including its substance-adjacent neighbours:
"workforce management" is not performance management and not
workforce planning; "resource scheduling" is not resource
management.

**No computed scores.** Evaluation support is records: human
ratings and narrative comments stored verbatim. No aggregate,
average, or total field exists anywhere in this build.

**Privacy is structural, not procedural.** The build does not
"handle PII carefully" — it has no fields capable of holding
it. Person records are opaque references; nothing in any entity
shape accepts a name, SSN, birth date, pay figure, address,
phone, or email, and the privacy tests assert this on the
shapes themselves. The substrate holds records about cases and
people by opaque reference only — never real PII — exactly as
the founding group designed it.

**Census citations verifying are not claims.** 3 of 3 census
citations verify verbatim; only 1 of 3 is a claim evidence
sentence. Dayforce's opening citation tags nothing, and
Replicon's verifies while its stored evidence is the citation
sentence's second fragment (the house splitter breaks at
"Replicon Inc." — recorded in `scratch/ARTIFACTS.md`, not
repaired by special-casing one fork).

**Demo identities are hooks, not an IdP.** The demo identities
(`alice`, `bob`, `carol`, `dana`) are hooks, not an identity
provider: identification & authentication (IA-2) stays with the
embedding organization, which supplies production identity,
authentication strength, and account lifecycle. (Dayforce
documents federation and IAL2/AAL2 for *itself*; the build ships
none of that — it is gap 6 above.)

**Platform layer.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies when a certificate is
configured (`--certfile`/`--keyfile`); the default serve mode
is plain HTTP for local/demo use. The merged build is a
**single-tenant reference deployment**; multi-tenancy and
general cloud hosting are deployment properties, not HR
functions.
