# Operations Management L1 singleton — build (Operation DeadRamp, Phase 2, Group 52)

This is the clean-room implementation of the **Operations
Management L1 singleton**: a sibling group of **one fork** —
**OpenWater** (OpenWater Software LLC), LI-SaaS, **FedRAMP
Certified** — built as one open-source service from the category's
operations records substrate carried at the L1 (Low) baseline.

**The fork, stated honestly up front.** OpenWater is a
submission-management and review platform: organizations use it to
run awards, abstracts and call-for-papers, grants, scholarships,
fellowships, accreditation, and competition programs, building
custom online submission forms and assigning submissions to
reviewers and judges for scoring and feedback. Its FedRAMP
certification covers exactly two services — **Submission
Management** and **Review & Evaluation**. This build is **not**
that platform and not a substitute for the fork's surface: it is
the category's operations records substrate (the directory,
project, asset, work-order, inspection, usage, and
workflow-definition records the Operations Management category
presupposes), carried in full at L1, and it **claims 0 of the
fork's functions** — the submission-management and
review-and-evaluation engines are Extended gaps, named below and
in the boundary decision recorded in UNION-SPEC.md (carried, not
claimed; precedents Groups 10, 24, 30 and Singletons 37, 38, 47).

It was written from the group's union contract only: original
code, no vendor code, assets, or branding from the offering. The
implementation is the shipped Group 36 (Operations Management L2)
code reused — this project's own Apache-2.0 code, byte-identical
in `src/` (SHA-256 record in `scratch/reuse-note.md`) — with the
baseline claim written fresh for this tier. Python 3, **standard
library only**, no external dependencies.

## The 12 core functions

1. **Directory** — persons (`per-`) and organizations (`org-`), each
   with an opaque external `reference` and free-form attributes.
   Contractor/vendor organizations and workforce records ride here.
2. **Projects** — projects/programs (`proj-`) with an optional owning
   organization and person membership (duplicate membership is a
   validation error).
3. **Assets** — assets (`ast-`) with kind, optional project link, and
   a status lifecycle `in_service ↔ in_maintenance`, either state to
   `retired` (terminal).
4. **Work orders** — work records (`wo-`) of type inspection /
   maintenance / field_operation / task / general, with priority,
   optional project/asset/person links, the lifecycle
   `open → {in_progress, cancelled}`,
   `in_progress → {completed, open, cancelled}`,
   `completed → {closed, in_progress}`, and an **overdue flag derived
   at read time** from `due_at` (never stored; completed, closed, and
   cancelled work orders never read overdue).
5. **Inspections** — immutable inspection records (`insp-`) against
   an asset and/or a work order, with the outcome recorded verbatim
   (`pass` / `fail` / `follow_up` / `not_recorded`). No score is
   computed from outcomes anywhere. There is deliberately no update
   or delete API.
6. **Usage records** — metering records (`use-`): a project, a
   metric name, an integer quantity, and a period. Floats and
   booleans are rejected; the integer's sign is not constrained, so
   corrections ride as new records. Immutable; no update/delete API.
7. **Workflow registry** — versioned workflow definitions (`wf-`):
   every update appends a new version and bumps the counter. The
   registry **never executes**: a test pins that registering a
   workflow changes no work order's state. Workflow writes are
   **admin-only**.
8. **Reports** — deterministic aggregate counts (work orders by
   status / type / project plus overdue count, assets by status,
   inspections by outcome, usage totals summed by metric), all
   derived at the caller-supplied `now`.
9. **Search** — literal, case-insensitive substring search (not
   regex) over people/organizations (names, references), projects,
   work-order subjects, asset names, and inspection summaries.
10. **REST API** — every function above is exposed over a JSON REST
    API. Work-order, list, and report endpoints accept a `?now=` ISO
    parameter for deterministic derived values.
11. **RBAC** — platform roles `admin`, `operator`, `viewer` with a
    permission matrix enforced on every operation (see below).
12. **Append-only audit log** — every person, organization, project,
    asset, work-order, inspection, usage, and workflow mutation,
    every search, and every denied attempt is recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence. There is no mutation or deletion API for audit
    entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `per-`, `org-`, `proj-`, `ast-`,
`wo-`, `insp-`, `use-`, `wf-`. Permission is checked before any state
change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m opsmgmt serve --host 127.0.0.1 --port 8797
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from opsmgmt.access import User
from opsmgmt.audit import AuditLog
from opsmgmt.store import OpsStore

audit = AuditLog()
store = OpsStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "operator")
person = store.create_person("Dana Operator", admin, reference="EXT-2001")
project = store.create_project("Pump Station Program", admin)
wo = store.create_work_order(bob, "inspection", "Inspect pump station",
                             project_id=project["id"], person_id=person["id"],
                             due_at="2020-01-01T00:00:00Z")
print(store.get_work_order(wo["id"], bob, now="2025-06-01T00:00:00Z")["overdue"])  # True (derived)
store.record_usage(bob, project["id"], "hours", 7, "2026-10")
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all 16 actions |
| `bob`   | operator | all reads except `audit_read`, plus `directory_write`, `project_write`, `asset_write`, `work_write`, `inspection_write`, `usage_write` (NOT `workflow_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read`: `directory_read`, `project_read`, `asset_read`, `work_read`, `inspection_read`, `usage_read`, `workflow_read`, `report_read` |

Read actions: `directory_read`, `project_read`, `asset_read`,
`work_read`, `inspection_read`, `usage_read`, `workflow_read`,
`report_read`, `audit_read`. Write actions: `directory_write`,
`project_write`, `asset_write`, `work_write`, `inspection_write`,
`usage_write`, `workflow_write`. Unknown roles hold no permissions.
Search is authorized under `project_read` (the house convention);
all three roles hold it.

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
| GET | `/persons` | directory_read | `{"persons": [...]}` |
| POST | `/persons` | directory_write | Body `{"name", "reference"?, "attributes"?}` → 201 person |
| GET | `/organizations` | directory_read | `{"organizations": [...]}` |
| POST | `/organizations` | directory_write | Body `{"name", "reference"?, "attributes"?}` → 201 organization |
| GET | `/projects` | project_read | `{"projects": [...]}` |
| POST | `/projects` | project_write | Body `{"name", "org_id"?, "attributes"?}` → 201 project |
| GET | `/projects/{id}/members` | project_read | `{"members": [person, ...]}` |
| POST | `/projects/{id}/members` | project_write | Body `{"person_id"}` → 201 project |
| GET | `/assets` | asset_read | `{"assets": [...]}` — accepts `?status=`, `?project_id=` |
| POST | `/assets` | asset_write | Body `{"name", "kind"?, "project_id"?, "attributes"?}` → 201 asset |
| POST | `/assets/{id}/transition` | asset_write | Body `{"to_status"}` → asset |
| GET | `/work-orders` | work_read | `{"work_orders": [...]}` — accepts `?now=`, `?status=`, `?project_id=`, `?work_type=` |
| POST | `/work-orders` | work_write | Body `{"work_type", "subject", "project_id"?, "asset_id"?, "person_id"?, "priority"?, "due_at"?}` → 201 work order |
| GET | `/work-orders/{id}` | work_read | One work order (with derived `overdue`) — accepts `?now=` |
| POST | `/work-orders/{id}/assign` | work_write | Body `{"person_id"?, "project_id"?}` (at least one) → work order |
| POST | `/work-orders/{id}/transition` | work_write | Body `{"to_status"}` → work order |
| GET | `/inspections` | inspection_read | `{"inspections": [...]}` — accepts `?asset_id=`, `?work_order_id=` |
| POST | `/inspections` | inspection_write | Body `{"summary", "asset_id"? and/or "work_order_id", "inspector_id"?, "outcome"?}` → 201 inspection |
| GET | `/usage` | usage_read | `{"usage": [...]}` — accepts `?project_id=`, `?metric=` |
| POST | `/usage` | usage_write | Body `{"project_id", "metric", "quantity", "period"}` → 201 usage record |
| GET | `/workflows` | workflow_read | `{"workflows": [...]}` |
| POST | `/workflows` | workflow_write (admin) | Body `{"name", "work_type", "trigger_text", "action_text"}` → 201 workflow |
| PATCH | `/workflows/{id}` | workflow_write (admin) | Body `{"trigger_text"?, "action_text"?, "enabled"?}` → workflow at new version |
| GET | `/report` | report_read | Aggregate report — accepts `?now=` |
| GET | `/search?q=...` | project_read | `{people, organizations, projects, work_orders, assets, inspections}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Single-object GETs for persons, organizations, projects, assets,
inspections, and workflows (`GET /persons/{id}`, etc.) are also
served with the matching read permission.

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

119 tests. See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record for
this tree.

## Control-family mapping (Low baseline)

This group sits at the map's lightest tier: **CMMC L1** ⇔ FedRAMP
**Low / LI-SaaS** (the fork is LI-SaaS, FedRAMP's tailored subset
of the Low baseline for SaaS). The baseline is the NIST SP 800-53
Rev. 5 **Low** baseline cross-walked to the FAR 52.204-21
practices behind CMMC L1. Group 36's Moderate citations are
deliberately **not** imported.

- **AC / IA** — AC-3 (access enforcement — the RBAC matrix,
  enforced in the store and again at the API), AC-6 (least
  privilege — reads for all roles, operational writes for
  operator, workflow configuration and audit read for admin
  only); IA-2 (identification & authentication — identity is
  supplied by the embedding organization via user/role headers;
  this service ships hooks, not an IdP). FAR side: limit system
  access to authorized users and to the transactions and
  functions they are authorized to execute; identify and
  authenticate users before allowing access.
- **AU** — AU-2 (event logging), AU-3 (content of audit records),
  **on the FedRAMP Low side of the crosswalk only**: FAR
  52.204-21 contains no audit practice, so no audit claim is made
  on the CMMC side. **AU-6 is NOT claimed at this tier** (it is
  not a Low selection, and Group 36's Moderate citation of it
  does not carry down); the append-only store and the
  admin-gated audit read are stated as implementation properties.
- **CM** — CM-6 (configuration settings — the workflow registry
  is versioned configuration, managed as configuration, not
  executed code), CM-8 (system component inventory — the asset
  records with lifecycle are the inventory substrate; discovery
  and scanning engines are Extended).
- **SI** — SI-10 (information input validation — malformed input
  is rejected, never partially applied, and consumes no ids).
- **SC** — SC-8, **partial** (transmission confidentiality — the
  server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated
  plainly and not claimed here).

This mapping states which baseline families the build's features
answer to. It is not a FedRAMP authorization and confers no CMMC
certification.

## Honesty: what is NOT in this build

- **The fork's certified services are NOT implemented.** No
  submission management engine (no submission forms, no intake,
  no program administration surface) and no review & evaluation /
  judging engine (no reviewer assignment of submissions, no
  scoring, no feedback workflow) — **nothing in this build
  scores anything**. Those are the fork's own engines, specified
  as Extended gaps; this build claims 0 of the fork's functions.
- **The fork's out-of-scope capabilities are NOT implemented**,
  and are named here exactly as the fork's own listing names
  them, each **explicitly outside the FedRAMP Minimum Assessment
  Scope** per that listing: automated communications, the
  reporting product, the program website builder, galleries,
  conference session scheduling, payments, and third-party
  integrations.
- **The category's Extended engines are NOT implemented.** No
  workflow automation *execution* engine (workflow definitions
  are registry records; nothing runs them), no real-time
  intelligence or streaming analytics, no AI models, no low-code
  application builder/deployment engine, no integration
  connectors, no mobile applications or offline sync.
- **The platform services are NOT implemented.** No network
  connectivity service, no authorization service / identity
  provider, no security-services enforcement plane, no policy
  enforcement plane, and no governance/compliance console engine.
  The build carries the records and the RBAC/audit hooks those
  services presuppose, and says so.
- **Derived, not stored.** Overdue values are computed at read
  time from stored timestamps; there is no background timer,
  escalation, or notification when a work order becomes overdue.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation. The fork asserts multi-tenancy of its own
  platform; that is the fork's platform property, not this
  build's — this build is a single-tenant reference deployment
  and says so.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not
  an identity provider**. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **TLS is available only when a certificate is
  configured** (`--certfile`/`--keyfile`); the default serve mode
  is plain HTTP for local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which Low-baseline
  families the build's features answer to; nothing more.
