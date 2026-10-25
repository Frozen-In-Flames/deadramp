# Construction L2 — merged build (Operation DeadRamp, Phase 2, Group 19)

This is the merged, clean-room implementation of the **Construction
L2** sibling group: **4 forks / vendor platforms** from the FedRAMP
Marketplace that share the same category (Construction) and the same
trust tier (FedRAMP Moderate), built as one open-source service from
the group's union contract (`UNION-SPEC.md`).

A note on heterogeneity, honestly: this category is not four
construction platforms. It contains **one classic construction
platform** (Gordian — cost data and estimating), a prevailing-wage
compliance platform (LCPtracker), a mobile field-workforce platform
(Actsoft), and a contract lifecycle platform (CobbleStone) — and only
LCPtracker carries "Construction" in its source business categories.
This build is their **shared records substrate**: projects executed
by tiered contractor workforces, under contracts with lifecycles and
key dates, with document, cost, workforce, and compliance records —
not a claim that the siblings were ever the same product. Each
vendor's engine (estimating, telematics, CLM workflow, wage
determination) is an Extended function, named in the spec's gaps.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 17 core functions

1. **Organizations & participation** — organizations (`org-`, opaque
   reference + attributes) and project participation records at
   contractor tiers (1 = prime, 2+ = subcontractor tiers; duplicate
   participation is a validation error).
2. **Projects** — projects (`prj-`) with a
   `planned → active → on_hold → completed → closed` lifecycle, plus
   cancellation.
3. **Documents** — a document/drawing registry (`doc-`) with full
   version history; each version carries a caller-supplied content
   checksum. Records and checksums only, never document content.
4. **Contracts** — contracts (`con-`) with counterparty, integer-cent
   value, key dates, and a
   `draft → in_review → executed → active → completed → closed`
   lifecycle (plus termination). **Expiry state is derived at read
   time** (`pre_execution` / `open_ended` / `active` / `expiring` /
   `expired` / `ended`) with a signed `days_to_expiry`; it is never
   stored.
5. **Submittals & RFIs** — submittals (`sub-`) with a
   `draft → submitted → under_review → approved / approved_as_noted /
   revise_resubmit / rejected` lifecycle, RFIs (`rfi-`) with
   `open → answered → closed`; overdue state derived at read.
6. **Schedule & dispatch** — milestones (`ms-`) whose **due state is
   derived at read** (`upcoming` / `due_soon` / `overdue` /
   `completed`), and dispatch records (`dsp-`) with an
   `assigned → in_progress → completed` lifecycle (plus cancellation).
7. **Inspections & punch list** — immutable inspection records
   (`insp-`) and punch items (`pun-`, `open → corrected → verified`,
   reopenable, overdue derived at read).
8. **Safety incidents** — incident records (`inc-`) with severity and
   a `reported → under_review → closed` lifecycle.
9. **Workforce records** — workers (`wrk-`) keyed by an **opaque
   caller-supplied reference only** (never a real identifier — see
   Honesty), and immutable timekeeping entries (`time-`) in integer
   minutes.
10. **Payroll & compliance** — certified-payroll records (`pay-`,
    immutable, integer-cent wage totals) and violation records
    (`vio-`, **admin-only writes**). **Contractor compliance status
    is derived at read time**: open violation ⇒ `noncompliant`, else
    certified payroll on file ⇒ `compliant`, else `no_records`.
11. **Costs** — cost records (`cost-`: budget / estimate /
    change_order / actual) in integer cents, plus a per-project
    summary with derived totals and variance.
12. **Derived alerts** — alerts computed at read from key dates and
    derived states (contract expiring/expired, milestone overdue,
    submittal/RFI/punch overdue, participant noncompliant or without
    compliance records). Nothing is stored.
13. **Reports** — deterministic aggregates at the caller's `now`
    (projects by status, contracts by status and derived expiry,
    milestones by derived due state, overdue counts, compliance
    counts over all participants, cost totals and variance).
14. **Search** — literal, case-insensitive substring search (not
    regex) over projects, organizations (name + reference), document
    titles, and contract titles.
15. **REST API** — every function above over a JSON REST API.
    Contract, record, milestone, report, and alert endpoints accept
    a `?now=` ISO parameter for deterministic derived values.
16. **RBAC** — platform roles `admin`, `operator`, `viewer` with a
    permission matrix enforced on every operation (see below).
17. **Append-only audit log** — every mutation, every search, and
    every denied attempt recorded with actor, action, target, and
    UTC timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Money is integer cents everywhere: floats and bools are rejected at
the boundary. Ids are sequential per object type: `org-`, `prj-`,
`doc-`, `con-`, `sub-`, `rfi-`, `ms-`, `dsp-`, `insp-`, `pun-`,
`inc-`, `wrk-`, `time-`, `pay-`, `vio-`, `cost-`. Permission is
checked before any state change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m construct serve --host 127.0.0.1 --port 8797
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

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

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

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

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case (the communication group's convention).

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

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

## Honesty

- **What this is:** a clean-room records substrate built from the
  four siblings' public marketplace descriptions and the control
  families of the FedRAMP Moderate / CMMC L2 tier. It is not a
  FedRAMP authorization and confers no CMMC certification.
- **Carried, not claimed:** six taxonomy families tag 0 of 4
  descriptions — identity & access control and audit logging
  (baseline substrate) and submittal/RFI, milestone, inspection/
  punch-list, and safety-incident records (the record types the
  category is defined by). They are in the core as carried
  substrate, recorded as such in `UNION-SPEC.md`; the taxonomy was
  not re-tuned to manufacture claims for them.
- **Derived, never stored:** contract expiry state, milestone due
  state, record overdue flags, contractor compliance status, alerts,
  and report figures are computed at read time from stored records
  and the caller's `now`. The stored records contain none of them.
- **Privacy:** worker records hold opaque caller-supplied references
  only — no real identifiers — and payroll records hold aggregate
  wage totals, never per-worker pay.
- **Deployment:** the build is a single-tenant reference deployment
  (2 of 4 siblings claim multi-tenancy in prose; tenant isolation is
  deployment-layer). Encryption at rest is deployment-layer; TLS
  only when a certificate is configured. The demo identities are
  hooks, not an IdP — IA-2 stays with the embedding organization.
- **Gaps:** the engines are not built — estimating and the RSMeans
  cost data, GPS/telematics platforms, CLM workflow and clause
  libraries, e-signature execution, AI extraction, automation
  engines, wage-determination depth, and dispatch optimization are
  Extended functions, registered for the final gap batch (see
  `UNION-SPEC.md`).

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

See `tests/README.md` for the test count, the coverage map, and the
mutation-verified negative-control record.
