# Construction — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **6 untiered forks** of Construction —
census unit `untiered:Construction` in `../../remainder.json`,
Untiered Set 7. **This is an untiered set, and that means something
specific:** every member's FedRAMP impact level is **Unknown** in
the source dataset. The source publishes no baseline for these
offerings, so **tier stays null**: no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec sheets are in
[`specs/specs.json`](specs/specs.json), each recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The 6 forks were spec'd under the category's existing 23-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Construction L2 group's original
shipped claim tables exactly — **4 of 4 forks, 25 of 25 claims,
deep-equal** — before tagging this set. Result here: **27 claims**
across the set, **every fork claiming at least one**; **3 claims
stand at artifact weight** (Specset's UFGS specification-compliance
checking and Trimble's "high-compliance" adjective under the
compliance family; Trimble's "audit-ready" under audit logging),
recorded as such in `scratch/ARTIFACTS.md`, not hidden or promoted.

The build implements the category's **seventeen-function
substrate** — the construction records machinery every sibling's
work presupposes — carried **byte-identical** from the founding
Construction L2 build (`../construction-l2/src/construct/`, 7 of 7
modules; SHA-256 accounting below). The substrate is
tier-independent records code: the founding source contains no
tier or baseline machinery, so there was nothing tier-shaped to
strip. Where the founding contract's text ties substrate functions
to the Moderate/L2 baseline (access control, audit), read it here
as **baseline-neutral substrate**: at tier null it is carried,
claimed against no baseline.

## The 6 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2701557038 | Facility Grid, LLC | Facility Grid | 6 |
| FR2633734906 | Four BT, LLC | Four BT Benchmark Construction Estimator | 2 |
| FR2520254824 | InEight, Inc. | InEight Document US Government | 2 |
| FR2631258135 | Specset | Specset Cloud Platform | 6 |
| FR2631747321 | Specset | Specset Cloud Platform | 6 |
| FR2701247929 | Trimble Inc. | Trimble for Government | 5 |

**Duplicate authorization pair:** FR2631258135 and FR2631747321
(Specset Cloud Platform) are spec'd as separate sheets, per the
Phase 1 rule that paired records stay separate. Their descriptions
are byte-identical in the source and their claim tables are
identical (6 claims each); the pair is counted twice in every
count, as the registry counts it. FR2631258135's own description
states the second listing is a duplicate created at intake,
"pending retirement, requested 2026-08-31" — recorded, and counted
as the census counts it.

In `forks.json` the set is mixed as filed: 2 forks carry the
Construction category, 2 are filed under Artificial Intelligence
(AI) (the Specset pair), 1 under Collaboration (InEight), and 1 is
filed "Uncategorized (none in source)" (Four BT); the census
assigned all 6 to Construction from their own descriptions, and
the spec sheets record the assignment. Authorization statuses as
recorded span Initial Implementation (5) and FedRAMP Certified (1,
InEight Document, at impact "Unknown") — a status is record data,
not a claim.

What the six are, in substance: a construction commissioning
platform (Facility Grid), a construction cost-estimating service
(Four BT), a construction document control platform (InEight), an
AI construction document review platform (Specset, twice), and a
modular government platform spanning field collaboration, project
management, asset management, and permitting (Trimble). What they
share with the founding group is the records substrate below.

## The 17 core functions

1. **Organizations & participation** — organization records
   (`org-`, opaque reference + attributes) and project
   participation records tying an organization to a project at a
   contractor tier (1 = prime, 2+ = subcontractor tiers; duplicate
   participation is a validation error).
2. **Projects** — project records (`prj-`) with a
   `planned → active → on_hold → completed → closed` lifecycle
   (plus cancellation), agency reference, location, start/end
   dates.
3. **Documents** — a document/drawing registry (`doc-`: drawings,
   specifications, contracts, submittals, forms, reports) with full
   version history; each version carries a caller-supplied content
   checksum. The registry holds records and checksums only, never
   document content.
4. **Contracts** — contract records (`con-`) with counterparty,
   integer-cent value, key dates, and a
   `draft → in_review → executed → active → completed → closed`
   lifecycle (plus termination). **Expiry state is derived at read
   time, never stored**: `pre_execution` / `open_ended` / `active`
   / `expiring` (≤ 30 days) / `expired` / `ended`, with a signed
   `days_to_expiry`.
5. **Submittals & RFIs** — submittal records (`sub-`) with a
   `draft → submitted → under_review → approved /
   approved_as_noted / revise_resubmit / rejected` lifecycle, and
   RFI records (`rfi-`, `open → answered → closed`). Overdue state
   is **derived at read** from `due_at` for any non-terminal
   record.
6. **Schedule & dispatch** — milestone records (`ms-`) with a
   **due state derived at read** (`upcoming` / `due_soon` ≤ 7 days
   / `overdue` / `completed`), and dispatch records (`dsp-`) with
   an `assigned → in_progress → completed` lifecycle (plus
   cancellation).
7. **Inspections & punch list** — immutable inspection records
   (`insp-`, with the inspector's recorded result) and punch items
   (`pun-`, `open → corrected → verified`, reopenable, overdue
   derived at read).
8. **Safety incidents** — incident records (`inc-`) with severity,
   category, and a `reported → under_review → closed` lifecycle.
   Records only; no incident-determination engine is claimed.
9. **Workforce records** — worker records (`wrk-`) keyed by an
   **opaque caller-supplied reference only** (never a real
   identifier), and immutable timekeeping entries (`time-`) in
   integer minutes.
10. **Payroll & compliance** — certified-payroll records (`pay-`,
    immutable, integer-cent wage totals) and violation records
    (`vio-`, **admin-only writes**). **Contractor compliance
    status is derived at read time, never stored**, by a single
    derivation point: an open violation ⇒ `noncompliant`; else a
    certified payroll on file ⇒ `compliant`; else `no_records`.
11. **Costs** — cost records (`cost-`) of kind budget / estimate /
    change_order / actual, all amounts integer cents (floats and
    bools rejected at the boundary), plus a per-project summary
    whose totals and variance are derived at read.
12. **Derived alerts** — alert records computed at read time from
    key dates and derived states: contract expiring/expired,
    milestone overdue, submittal/RFI/punch overdue, participant
    noncompliant, participant with no compliance records.
    Deterministic content and ordering; nothing is stored.
13. **Reports** — deterministic aggregates at the caller's `now`:
    projects by status, contracts by status and derived expiry
    state, milestones by derived due state, overdue counts,
    incident counts, compliance counts over all project
    participants, and cost totals with variance.
14. **Search** — literal case-insensitive substring search over
    projects, organizations (name + reference), documents, and
    contracts.
15. **REST API** — the full surface over HTTP, with the house auth
    convention (X-User/X-Role against a demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
16. **Access control (RBAC)** — admin/operator/viewer matrix over
    17 actions; `violation_write` and `audit_read` are admin-only;
    enforced in the store before any mutation or id allocation,
    and again at the service layer.
17. **Audit log** — append-only, JSONL-persistable, recording
    every mutation and every denied attempt (`<action>:denied`).

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). **Money is integer cents everywhere: floats and bools
are rejected at the boundary** — the founding build's discipline,
preserved exactly. Ids are sequential per object type: `org-`,
`prj-`, `doc-`, `con-`, `sub-`, `rfi-`, `ms-`, `dsp-`, `insp-`,
`pun-`, `inc-`, `wrk-`, `time-`, `pay-`, `vio-`, `cost-`.

Claim support in this set (full tracing in `UNION-SPEC.md`):
projects, documents, submittals & RFIs, organizations &
participation, contracts (thin basis), the milestones half of
schedule, the estimate-records half of costs, and the audit log
(artifact weight only) are claim-supported by at least one fork.
**Payroll & compliance is claimed in name, not in substance**: its
3 family claims rest on wording artifacts (UFGS
specification-compliance checking; a "high-compliance" adjective),
none asserting prevailing-wage or payroll records — payroll
records and the compliance derivation are carried substrate here.
Inspections & punch list, safety incidents, workforce records,
dispatch records, financial tracking, derived alerts, reports,
search, and access control are carried, not claimed. Functions are
**carried** as substrate; no function is claimed to be *attained*
by any fork — the build is the merged open implementation, not
any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m construct serve --host 127.0.0.1 --port 8797
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from construct.access import User
from construct.audit import AuditLog
from construct.store import ConstructStore

audit = AuditLog()
store = ConstructStore(audit=audit)
admin = User("alice", "admin")
prime = store.create_org("Prime Builders LLC", admin)
sub = store.create_org("Sub Electric Inc", admin)
project = store.create_project("Courthouse Annex", admin)
store.add_participant(project["id"], prime["id"], admin, tier=1)
store.add_participant(project["id"], sub["id"], admin, tier=2)
store.transition_project(project["id"], admin, "active")
print(store.contractor_compliance(project["id"], sub["id"], admin)["status"])  # 'no_records' (derived)
store.create_payroll(admin, project["id"], sub["id"],
                     "2026-10-01T00:00:00Z", "2026-10-15T00:00:00Z",
                     certified=True, total_wages_cents=4825000)
print(store.contractor_compliance(project["id"], sub["id"], admin)["status"])  # 'compliant' (derived)
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all 17 actions |
| `bob`   | operator | all reads except `audit_read`, plus all writes except `violation_write` (NOT `violation_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read` |

Read actions: `project_read`, `org_read`, `document_read`,
`contract_read`, `record_read`, `workforce_read`, `cost_read`,
`report_read`, `audit_read`. Write actions: `project_write`,
`org_write`, `document_write`, `contract_write`, `record_write`,
`workforce_write`, `cost_write`, `violation_write`. Unknown roles
hold no permissions.

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | `audit_read` | audit entries (admin only) |
| GET | `/search?q=` | `project_read` | search projects/orgs/documents/contracts |
| GET | `/report?now=` | `report_read` | aggregate report at `now` |
| GET | `/alerts?now=` | `report_read` | derived alerts at `now` |
| GET/POST | `/orgs` | `org_read` / `org_write` | list / create organizations |
| GET | `/orgs/{id}` | `org_read` | one organization |
| GET/POST | `/projects` | `project_read` / `project_write` | list (`?status=`) / create projects |
| GET | `/projects/{id}` | `project_read` | one project |
| POST | `/projects/{id}/transition` | `project_write` | lifecycle transition |
| GET/POST | `/projects/{id}/participants` | `project_read` / `project_write` | list / add participants |
| GET | `/projects/{id}/compliance?org_id=` | `workforce_read` | derived compliance status for one participant |
| GET | `/projects/{id}/cost-summary` | `cost_read` | derived cost totals & variance |
| GET/POST | `/documents` | `document_read` / `document_write` | list (`?project_id=`) / create documents |
| GET/PATCH | `/documents/{id}` | `document_read` / `document_write` | one document / append a version |
| GET/POST | `/contracts` | `contract_read` / `contract_write` | list (`?project_id=&status=&now=`) / create contracts |
| GET | `/contracts/{id}?now=` | `contract_read` | one contract with derived expiry |
| POST | `/contracts/{id}/transition` | `contract_write` | lifecycle transition |
| GET/POST | `/submittals`, `/rfis` | `record_read` / `record_write` | list (`?project_id=&status=&now=`) / create |
| GET | `/submittals/{id}`, `/rfis/{id}` (`?now=`) | `record_read` | one record with derived overdue |
| POST | `/submittals/{id}/transition`, `/rfis/{id}/transition` | `record_write` | lifecycle transition |
| GET/POST | `/milestones` | `record_read` / `record_write` | list (`?project_id=&now=`) / create |
| GET | `/milestones/{id}?now=` | `record_read` | one milestone with derived due state |
| POST | `/milestones/{id}/complete` | `record_write` | mark completed |
| GET/POST | `/dispatches` | `record_read` / `record_write` | list (`?project_id=`) / create |
| POST | `/dispatches/{id}/transition` | `record_write` | lifecycle transition |
| GET/POST | `/inspections` | `record_read` / `record_write` | list (`?project_id=`) / create (immutable) |
| GET/POST | `/punch-items` | `record_read` / `record_write` | list (`?project_id=&now=`) / create |
| POST | `/punch-items/{id}/transition` | `record_write` | lifecycle transition |
| GET/POST | `/incidents` | `record_read` / `record_write` | list (`?project_id=&status=`) / create |
| POST | `/incidents/{id}/transition` | `record_write` | lifecycle transition |
| GET/POST | `/workers` | `workforce_read` / `workforce_write` | list (`?project_id=&org_id=`) / create |
| GET/POST | `/time-entries` | `workforce_read` / `workforce_write` | list (`?worker_id=&project_id=`) / create (immutable) |
| GET/POST | `/payrolls` | `workforce_read` / `workforce_write` | list (`?project_id=&org_id=`) / create (immutable) |
| GET/POST | `/violations` | `workforce_read` / `violation_write` | list (`?project_id=&org_id=&status=`) / create (admin only) |
| POST | `/violations/{id}/resolve` | `violation_write` | resolve (admin only) |
| GET/POST | `/costs` | `cost_read` / `cost_write` | list (`?project_id=&kind=`) / create (immutable) |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**153 tests, OK** at delivery: the founding group's 146-test core
suite carried with the code, plus spec tests pinning this set
(exactly 6 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; 27 claims total with no zero-claim
fork; the Specset duplicate pair's claim tables identical). The
category's signature compliance-derivation mutation drill was
re-run in this tree — exactly 11 failures under the mutant, the
identical failure set the founding group's drill produced, store
restored and SHA-256 verified (see `tests/README.md`).

## Byte-identity accounting

`src/construct/` is carried from the founding group
`../construction-l2/src/construct/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `50128f582c6ad03d80cfa0744332cac31fa0e5811f72ba8bba3958931a22647d` |
| `__main__.py` | `9e1f2fa8b8e06649a78fe23bf57b420d87bd2cc6551da61126ca653ca3657b61` |
| `access.py` | `23251b1872bbe5c921a1e30b184289254649654c293dd3dac7d32af70877cfb6` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `139b3410eb2a30e5f4b7d93d10b1372ad8bca1b47326a715c07eaa2aad0ecda5` |
| `service.py` | `51a666ab112948920bac4e9de628b576b159be345996fe6c2adcd9497a00321c` |
| `store.py` | `49b5b203bd6dfece596aafed6987b06d7f7c9574efd047669026afa6a5cd7d65` |

The test suite is likewise carried (the founding suite entire —
that group had no additions module), with one labeling fix in
`tests/construct_helpers.py` (its docstring now names this
untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 6 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under the
taxonomy families that carry control language. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

Documented by at least one fork in the set:

- **Audit & accountability (AU)** — at **artifact weight only**,
  1 fork: Trimble for Government, via `audit_logging` —
  "audit-ready" readiness marketing in its Permit Management
  module. It documents no audit capability beyond the word, and
  is recorded at artifact weight in `scratch/ARTIFACTS.md`.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AC, AT, CA, CM, CP, IA, IR, MA,
MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control claims** — is
asserted by no description in the set. The set's three
`compliance_payroll` claims are **not** control claims (Specset's
is a function performed on a customer's documents; Trimble's is a
posture adjective), and Facility Grid's SOC 2 Type II examination
is a certification pursuit, not a control claim. If the source
later publishes an impact level for any of these offerings, the
tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build (InEight Document is FedRAMP Certified at
  recorded impact "Unknown"; the status does not move the tier),
  and a fork's documented control language is recorded as *its*
  claim, never as the build's control attainment.
- **Extended functions are specified, not implemented.** The
  union spec ranks 23 functions; the substrate behind 17 is
  implemented here. NOT implemented (claimant counts are this
  set's): the construction commissioning engine — checklists,
  functional performance tests, issues & observations, turnover
  packages (Facility Grid); cost estimating engines and benchmark
  cost data (1 — estimate *records* are Core); AI technical
  document review, UFGS compliance checking, and cited question
  answering (2, the Specset pair); document control platform
  depth (InEight); GIS/spatial platform and asset location
  tracking (1); permitting, licensing & right-of-way management
  (Trimble); asset management platform (Trimble, with
  asset-management logic also asserted by Specset); workflow /
  process automation engines (3 — lifecycle state machines are
  the in-core seed); prevailing-wage determination depth (the
  standing category gap — this set claims the family in name
  only).
- **Carried, not claimed:** six of the substrate's record types
  have no claimant in this set's substance — inspections & punch
  list, safety incidents, workforce & timekeeping, dispatch,
  financial tracking, alerts — plus reports, search, and access
  control. They are in the core as carried substrate, recorded as
  such in `UNION-SPEC.md`; the taxonomy was not re-tuned to
  manufacture claims for them.
- **Derived, never stored:** contract expiry state, milestone due
  state, record overdue flags, contractor compliance status,
  alerts, and report figures are computed at read time from stored
  records and the caller's `now`. The stored records contain none
  of them.
- **Privacy:** worker records hold opaque caller-supplied
  references only — no real identifiers — and payroll records hold
  aggregate wage totals, never per-worker pay. The document
  registry holds records and checksums only, never document
  content.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own. IA-2 stays with the embedding
  organization.
- **Deployment:** the build is a single-tenant reference
  deployment (2 of 6 siblings claim multi-tenancy in prose;
  tenant isolation is deployment-layer). Encryption at rest is
  deployment-layer; TLS only when a certificate is configured.
- **Named absences stand.** Inspection & punch-list records have
  0 claimants in this set despite a commissioning platform in it;
  search, reporting & analytics has 0 despite a "search and
  question answering" headline. Nothing was back-filled to make
  the set look complete.
