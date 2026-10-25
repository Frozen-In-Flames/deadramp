# Union Spec — Operations Management, CMMC L2 (DeadRamp Phase 2, Group 36)

The merged functional spec for the Operations Management sibling group
at the L2 tier: **2 forks, all FedRAMP Moderate**, reconciled zero-diff
three ways (`specs/specs.json` ↔ `forks.json` category="Operations
Management" + cmmc_tier="L2" ↔ MAP.md "Operations Management — L2
(2)").

The group: Mathematica Cloud Support System (Mathematica Inc.) ·
TrackVia Government (TrackVia, Inc.).

**This group is two half-domains over one shared substrate, and the
spec says so plainly.** The two siblings share exactly **one** of the
taxonomy's 19 families (`program_operations`). MCSS is an internal
cloud management and compliance *console*: a general support system
offering preconfigured authorization, network connectivity, common
security services, usage information, and governance/compliance
functions to its own organization's application teams — and it states
in its own description that it "does not produce, store, or transmit
federal information." TrackVia Government is a configurable
operational-work platform: structured operational data, automated
workflows, real-time intelligence, inspections, asset and equipment
management, workforce readiness, contractor and vendor management.
What they share, and what the claim counts below prove, is a
**records substrate** their claimed functions collectively presuppose:
people and organizations held in a directory, programs/projects,
assets, work records with a lifecycle and due times, inspection
records, usage records, workflow definitions held as a registry, and
reports, search, access control, and an audit trail over all of it.
The merged build implements that substrate; each vendor's engine on
top of it is an Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against a 19-family taxonomy defined from this category's
descriptions. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is
stored in `specs/specs.json` as evidence, so every claim is auditable
(all evidence strings were asserted programmatically to be verbatim
substrings of their descriptions; 0 violations). **20 claims total,
no wording-artifact removals were needed after scoping** — four
scoping decisions kept false hits out of the count entirely and are
documented in `scratch/ARTIFACTS.md`: "AI ready" does not tag AI
(readiness marketing; the AI claim rests on AI named as a platform
component); TrackVia's "stringent federal security and compliance
requirements" does not tag governance/compliance (requirements the
platform *meets*, not a function it *offers*); MCSS's "does not
produce, store, or transmit federal information" tags nothing (a
boundary disclaimer); MCSS's authorization claim rests on the
services-offered sentence, not on "authorization boundary." **No
fork has zero claims.** Per-fork claim counts: Mathematica Cloud
Support System 7, TrackVia Government 13.

## Function ranking — all 2 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 2 | Program & project operations | **Core** — project/program registry |
| 2 | 1 | Operational data & structured records | **Core** — the records substrate itself |
| 2 | 1 | Workflow automation | Core (registry); execution Extended |
| 2 | 1 | Reporting & operational intelligence | Core (records reporting); real-time engine Extended |
| 2 | 1 | Asset & equipment management | **Core** — asset records; management depth Extended |
| 2 | 1 | Inspections & field operations | **Core** — inspection/work records |
| 2 | 1 | Workforce & mission readiness | Core (directory records); readiness analytics Extended |
| 2 | 1 | Safety & compliance management | Core (records substrate); compliance engine Extended |
| 2 | 1 | Governance & compliance functions | Core (records + audit substrate); console engine Extended |
| 2 | 1 | Authorization & access services | **Core** (as RBAC hooks); authorization service / IdP Extended |
| 2 | 1 | Common security services | Core (audit/RBAC hooks); enforcement plane Extended |
| 2 | 1 | Network connectivity & platform services | Extended — platform-layer (the connectivity service itself) |
| 2 | 1 | Usage information & metering | **Core** — usage records |
| 2 | 1 | Policy enforcement | Core (workflow/policy registry); enforcement plane Extended |
| 2 | 1 | Application configuration & deployment | Extended — low-code builder/deployment engine |
| 2 | 1 | Mobile capabilities | Extended — mobile applications & sync |
| 2 | 1 | Integrations & interoperability | Extended — connector engines/catalog |
| 2 | 1 | AI capability | Extended — models |
| 2 | 1 | Contractor & vendor management | **Core** — organization directory records |

Named absences: **scheduling/rostering is claimed by 0 of 2**
siblings (no description asserts a schedule or roster function), and
**IoT/telematics data collection is claimed by 0 of 2** — neither is
built or implied. Multi-tenancy is claimed by neither description;
the build is a single-tenant reference deployment and says so (see
gaps).

## The Core — what the merged build implements (12 functions)

1. **Directory** — person records (`per-`) and organization records
   (`org-`) with opaque reference strings and free-form attributes
   (contractor/vendor organizations ride as org records: TrackVia's
   vendor management; workforce records: TrackVia's readiness use
   case). No real personal identifiers are required by any record
   shape.
2. **Projects** — project/program records (`proj-`) with an optional
   owning organization and member persons (duplicate membership is a
   validation error). Claims basis: `program_operations` (2 of 2).
3. **Assets** — asset/equipment records (`ast-`) with kind, optional
   project link, attributes, and a status lifecycle
   `in_service → in_maintenance → in_service`, `in_service →
   retired`, `in_maintenance → retired`; `retired` is terminal.
4. **Work orders** — work records (`wo-`), type-tagged
   (inspection/maintenance/field_operation/task/general), with the
   lifecycle `open → {in_progress, cancelled}`,
   `in_progress → {completed, open, cancelled}`,
   `completed → {closed, in_progress}` (reopen), `closed` and
   `cancelled` terminal — the house transition map, transposed from
   the shipped case lifecycle — assignment
   to a person and/or a project, an optional asset link, priority,
   and an optional `due_at`. Overdue is **derived at read time,
   never stored**:
   `overdue = now > due_at and status not in (completed, closed, cancelled)`.
5. **Inspections** — inspection records (`insp-`) against an asset
   and/or a work order, with an inspector person link, a summary, and
   an outcome recorded verbatim (`pass` / `fail` / `follow_up` /
   `not_recorded` default). Immutable once written; no score is
   computed from outcomes anywhere.
6. **Usage records** — usage/metering records (`use-`): a project or
   service reference, a metric name, an integer quantity (floats and
   booleans rejected at the boundary; the integer's sign is not
   constrained — corrections and adjustments ride as new records,
   since usage records are immutable), and a period string.
   Immutable once written. Claims basis: MCSS's usage information.
7. **Workflow registry** — workflow definition records (`wf-`):
   name, work-type scope, trigger text, action text, enabled flag,
   versioned on update (full version history retained). Registry
   only; the workflow **execution** engine is Extended, and a test
   pins that registering a workflow changes no work order's state.
8. **Reports** — deterministic summaries: work orders by
   status/type/project plus overdue count at the report's `now`,
   assets by status, inspections by outcome, usage totals by metric.
9. **Search** — literal case-insensitive substring search over
   people/organizations (names, references), projects, work orders
   (subjects), assets (names), and inspections (summaries).
10. **REST API** — the full surface over HTTP, with the house auth
    convention (X-User/X-Role against a demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
11. **Access control (RBAC)** — admin/operator/viewer matrix;
    `workflow_write` and `audit_read` are admin-only; enforced in
    the store before any mutation or id allocation, and again at the
    service layer.
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation and every denied attempt (`<action>:denied`).

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes no
tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Directory, projects | AC-3, AC-6, IA-2 (hooks) | People, organizations, and project membership are explicit records; assignment is computed from them, never assumed |
| Work orders & lifecycle | AU-2, CM-6, SI-12 (partial) | Every work-order transition is an auditable event under a configured lifecycle; retention/disposition engines are Extended |
| Overdue derivation | AU-6, CA-7, CM-6 | Overdue is derived at read from `due_at` and status against the report's `now`, never stored — reviewable and reproducible |
| Assets | CM-8, AU-2 | Asset records with lifecycle are the inventory substrate; discovery/scanning engines are Extended |
| Inspections | CA-2, AU-2, SI-12 (partial) | Inspection records with verbatim outcomes support assessment review; scoring engines are not built |
| Usage records | AU-2, AU-3, SC-28 (not claimed) | Metering records are auditable content; they record usage of services, never federal information content |
| Workflow registry | CM-6, SA-4 | Workflows are versioned configuration records, managed as configuration, not executed code |
| Reports | AU-6 | Deterministic summaries over the records, including derived overdue at a stated `now` |
| Search | AU-6, SI-12 (partial) | Literal search over records supports review; retention/disposition is partial and Extended |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers; `workflow_write`/`audit_read` admin-only |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source implementation
whose features trace to the Moderate/L2 control families. FedRAMP
authorizes products; CMMC certifies organizations — neither regime
accepts the other as evidence, and any real compliance claim still
has to be earned inside each regime separately.

## Implementation contract (summary)

`src/opsmgmt/` (Python stdlib only): `errors` (`OpsError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, role matrix: 16 actions — reads `directory_read`,
`project_read`, `asset_read`, `work_read`, `inspection_read`,
`usage_read`, `workflow_read`, `report_read`, `audit_read`; writes
`directory_write`, `project_write`, `asset_write`, `work_write`,
`inspection_write`, `usage_write`, `workflow_write`; admin = all 16,
operator = all reads except `audit_read` + all writes except
`workflow_write`, viewer = all reads except `audit_read`), `audit`
(append-only AuditLog), `store` (OpsStore: the 12 core functions;
failed operations consume no ids; permission checks precede
mutation; derivation lives in the single method
`OpsStore._is_overdue`), `service` (HTTP layer, demo registry
alice=admin, bob=operator, carol=viewer), `__main__` (`python -m
opsmgmt serve`, default port 8797). `tests/`: see tests/README.md for
the test count and the negative-control record (the count is filled
in from the build, not stated here).

Store API (signatures follow the house pattern of the shipped
groups; actor is a User-like object or a plain string):

- Directory: `create_person(name, actor, reference=None, attributes=None)` → `per-`;
  `get_person`, `list_persons`; `create_organization(name, actor, reference=None, attributes=None)` → `org-`;
  `get_organization`, `list_organizations`.
- Projects: `create_project(name, actor, org_id=None, attributes=None)` → `proj-`;
  `add_person_to_project(project_id, person_id, actor)` (duplicate → ValidationError);
  `get_project`, `list_projects`, `list_project_members(project_id, actor=None)`.
- Assets: `create_asset(name, actor, kind="equipment", project_id=None, attributes=None)` → `ast-`, status starts `in_service`;
  `transition_asset(asset_id, actor, to_status)` per the lifecycle above;
  `get_asset`, `list_assets(actor=None, status=None, project_id=None)`.
- Work orders: `create_work_order(actor, work_type, subject, project_id=None, asset_id=None, person_id=None, priority="normal", due_at=None)` → `wo-`, status `open`;
  `assign_work_order(work_order_id, actor, person_id=None, project_id=None)` (at least one required);
  `transition_work_order(work_order_id, actor, to_status)` per the lifecycle above;
  `get_work_order(work_order_id, actor=None, now=None)` (view carries derived `overdue`);
  `list_work_orders(actor=None, now=None, status=None, project_id=None, work_type=None)`.
- Inspections: `record_inspection(actor, summary, asset_id=None, work_order_id=None, inspector_id=None, outcome="not_recorded")` → `insp-` (at least one of asset_id/work_order_id required); `get_inspection`, `list_inspections(actor=None, asset_id=None, work_order_id=None)`. No update/delete API.
- Usage: `record_usage(actor, project_id, metric, quantity, period)` → `use-` (project must exist; quantity must be an int, not bool/float); `list_usage(actor=None, project_id=None, metric=None)`. No update/delete API.
- Workflows: `create_workflow(actor, name, work_type, trigger_text, action_text)` → `wf-` at version 1 (work_type = a known work type or `all`);
  `update_workflow(workflow_id, actor, trigger_text=None, action_text=None, enabled=None)` appends a version;
  `get_workflow`, `list_workflows`.
- Reports: `report(actor=None, now=None)` → `{work_orders: {total, by_status, by_type, by_project, overdue}, assets: {total, by_status}, inspections: {total, by_outcome}, usage: {total, by_metric}}` where by_metric sums quantities.
- Search: `search(query, actor)` → `{people, organizations, projects, work_orders, assets, inspections}`; empty query → ValidationError; audits a `search` entry.

Service endpoints mirror the store (list/create/get per resource,
plus `POST /work-orders/{id}/assign`, `POST /work-orders/{id}/transition`,
`POST /assets/{id}/transition`, `POST /projects/{id}/members`,
`PATCH /workflows/{id}`, `GET /report`, `GET /search?q=`,
`GET /audit`, `GET /health`). Work-order and report endpoints accept
`?now=`. Errors are JSON `{error}` with 400/401/403/404; no stack
trace is ever returned.

## Coverage statement (for this build)

- Forks spec'd: **2 / 2**, each with evidenced claims (20 total).
- Core implemented: **12 / 12** functions above.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Workflow automation execution engine — running automated workflows
  against work records (TrackVia; the registry is Core, execution is
  the engine).
- Real-time intelligence & analytics engine — streaming/real-time
  operational intelligence and outcome analytics beyond registry
  reporting (TrackVia).
- AI models (TrackVia; AI named as a platform component, 1 claim).
- Low-code application builder & deployment engine — configuring and
  deploying operational applications (TrackVia).
- Integration connector engines & catalog (TrackVia).
- Mobile applications & offline sync (TrackVia mobile capabilities).
- Network connectivity services & cloud platform operations — the
  connectivity service and the GSS hosting itself (MCSS;
  platform-layer).
- Authorization service / identity provider — the centralized
  authorization service MCSS offers its application teams (the build
  ships RBAC hooks, not an IdP).
- Common security services enforcement plane (MCSS).
- Policy enforcement plane — enforcing policy across projects at
  runtime (MCSS; the registry records policies/workflows, the plane
  that enforces them is the engine).
- Governance/compliance console engine — continuous compliance
  monitoring and console automation depth (MCSS).
- Scheduling & rostering (0 of 2 — named absence).
- IoT / telematics data collection (0 of 2 — named absence).

Platform layer (gap-listed, never implied closed): multi-tenancy
(claimed by neither sibling; the build is a single-tenant reference
deployment); encryption at rest (deployment layer); TLS only when a
certificate is configured; demo identities are hooks, not an IdP —
IA-2 stays with the embedding organization.

**Boundary note:** MCSS states it does not produce, store, or
transmit federal information, and this build honors that shape:
records here are operational records (work, assets, inspections,
usage of services), keyed by opaque references. No record shape
holds federal information content, real personal identifiers, or
evidence content.
