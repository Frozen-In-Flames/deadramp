# Operations Management L2 — merged build (Operation DeadRamp, Phase 2, Group 36)

This is the merged, clean-room implementation of the **Operations
Management L2** sibling group: **2 forks / vendor platforms** from
the FedRAMP Marketplace that share the same category (Operations
Management) and the same trust tier (FedRAMP Moderate), built as one
open-source service from the group's union contract. It is the last
of the 36 sibling groups.

A note on heterogeneity, honestly: these two siblings share exactly
one of the union taxonomy's 19 claim families. One is an internal
cloud management and compliance console (Mathematica Cloud Support
System — a general support system offering preconfigured
authorization, network, security, usage, and governance services to
its own organization's application teams, which states in its own
description that it does not produce, store, or transmit federal
information). The other is a configurable operational-work platform
(TrackVia Government — structured operational data, automated
workflows, inspections, asset and equipment management, workforce
readiness, contractor and vendor management). This build is their
**shared records substrate**: the directory, project, asset,
work-order, inspection, usage, and workflow-definition records those
products keep, with one access matrix and one audit log — not a claim
that the siblings were ever the same product.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

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
negative control, and the mutation-verification drill record.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline (the FedRAMP
Moderate baseline for this group's tier), cross-walked to the 110
practices of NIST SP 800-171 behind CMMC L2:

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store and
  again at the API), AC-6 (least privilege — reads for all roles,
  operational writes for operator, workflow configuration and audit
  read for admin only); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review — `audit_read` restricted to admin),
  AU-9 (protection of audit information — append-only store, no
  mutation API).
- **CM / CA / SI** — CM-6/CM-8 (configuration and inventory: the
  workflow registry and asset records), CA-2 (inspection records
  support assessment review), SI-10 (information input validation —
  malformed input is rejected, never partially applied, and consumes
  no ids), SI-12 (records retention is partial; disposition engines
  are Extended); SC-8 (transmission confidentiality — the server
  runs over TLS when a certificate is configured; encryption at
  rest is a deployment-layer control, stated plainly and not
  claimed here).

## Additions (remainder unit, 2026-10-31)

Twenty previously uncategorized FedRAMP Moderate offerings have
joined this group under the remainder census
(`addition:operations-management-l2`): Accenture Federal Cloud
ERP, AINS eCase, Bizagi Cloud, Canon Office Cloud, FM:Systems
OpenBlue Workplace, IBM Automation Services for Government,
Ivanti Neurons for ITSM, M.C. Dean InfraLink, Manhattan
Government Cloud, iSite Contract Management Portal, Pitney Bowes
SendPro 360, PTC Cloud Services, GoRPM, Smartsheet Gov, ARIS
Government Cloud, stackArmor Clarity, StackArmor Rally, Tyler
Federal Product Suite, UiPath Automation Cloud Public Sector,
and Xerox Managed Print Services. The group now covers **22
forks**; their spec sheets are appended to `specs/specs.json`
(the two sheets above are byte-preserved), and the union of
record is UNION-SPEC.md plus **ADDENDUM.md**.

What changed: spec coverage (2 → 22 forks, 20 → 27 taxonomy
claims — the newcomers claim only `workflow_automation` ×6 and
`integrations` ×1 under the group's taxonomy applied verbatim;
14 claim zero families, with near-misses itemized in
`scratch/ADDITIONS_ARTIFACTS.md`) and tests (119 → 126, all
passing; the `_is_overdue` mutation drill re-run in this tree,
exactly 9 failures, restored and hash-verified — see
`tests/README.md`).

What did **not** change: the code (`src/` is untouched — the
additions warranted no core extension; every claimed family
already rides the shipped union), the 12 core functions, the
taxonomy, and the Moderate/L2 baseline. The newcomers' own
engines (print fleets, supply chain, PLM, ITSM, case
management, process mining, mailroom operations, and more) are
Extended gaps, named in ADDENDUM.md §5 for the final GAPS batch.

## No-signal addition (2026-10-31)

One more fork has joined: **SMX Elevate Intelligent Automation
Platform (IAP)** (F1603077867, FedRAMP Moderate / PaaS). The
remainder census left it unclassified — its marketplace
description carries no citable function sentence — and the
live-docs research pass resolved it to Operations Management on
SMX's own capability sheet: "Through SMX Elevate, we leverage
our IP and Intelligent Automation Platform (IAP) to design,
build, operate, and secure multi-cloud platforms for mission
critical cloud workloads..." (source:
http://www.smxtech.com/wp-content/uploads/2025/02/SMX_SolutionCap_ELEVATE_Platform_Feb2025.pdf).
The group now covers **23 forks**; the sheet is appended to
`specs/specs.json` (the 22 earlier sheets are byte-preserved)
and carries the classification sentence and URL as
`classification_evidence` / `classification_source_url`,
distinct from claim evidence.

Under the group's taxonomy applied verbatim, the fork claims
**zero families** (raw pass 3 hits: one third-party ISV
catalogue exclusion, two scoping removals — full record in
`scratch/NOSIGNAL_ARTIFACTS.md`), so the group total stays 27
claims, the code is untouched, and nothing about the tier, the
baseline, or the 12 core functions changed. Tests: 126 → 134,
all passing; the `_is_overdue` mutation drill re-run in this
tree, exactly 9 failures, restored and hash-verified — see
`tests/README.md`. Its own engines (multi-cloud platform
operations and lifecycle management; built-in compliance
automation and policy guardrails) are Extended gaps, named in
ADDENDUM.md §8 for the final GAPS batch.

## Honesty: what is NOT in this build

- **Extended capabilities are NOT implemented.** No workflow
  automation *execution* engine (workflow definitions are registry
  records; nothing runs them), no real-time intelligence or
  streaming analytics, no AI models, no low-code application
  builder/deployment engine, no integration connectors, no mobile
  applications or offline sync — those are the siblings' engines,
  named in the union spec's gaps.
- **The platform services are NOT implemented.** No network
  connectivity service, no authorization service / identity
  provider, no security-services enforcement plane, no policy
  enforcement plane, and no governance/compliance console engine.
  The build carries the records and the RBAC/audit hooks those
  services presuppose, and says so.
- **Scheduling/rostering and IoT/telemetry are absent — 0 claims.**
  No sibling in this group supports either in the union contract,
  so neither is built or implied. (After the additions: still 0
  taxonomy claims and unbuilt, though two additions assert
  adjacent substance — see ADDENDUM.md §5.)
- **No federal information content is stored — by design.** One
  sibling states it does not produce, store, or transmit federal
  information, and the build honors that shape: records are
  operational records (work, assets, inspections, usage of
  services) keyed by opaque references, with no field whose
  semantics are a real personal identifier or document content.
- **Derived, not stored.** Overdue values are computed at read time
  from stored timestamps; there is no background timer, escalation,
  or notification when a work order becomes overdue.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not an
  identity provider**. Production identity, authentication strength,
  and account lifecycle belong to the embedding organization.
- **Encryption at rest is a deployment-layer control**, not claimed
  here. **TLS is available only when a certificate is configured**
  (`--certfile`/`--keyfile`); the default serve mode is plain HTTP
  for local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which baseline
  families the build's features answer to; nothing more.
