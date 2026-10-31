# Union Spec — Research, CMMC L2 (DeadRamp Phase 2, Group 53)

The merged functional spec for the **Research L2 singleton**:
**1 fork**, category **Research** (a brand-new category — no group
exists at any other tier; it is also the entire category — Research
has exactly one offering in the whole registry), CMMC tier **L2**
(the member is FedRAMP **Moderate** in `forks.json` — verified).
The member list was reconciled two ways with **zero diffs**:
`forks.json` carries exactly one Research / L2 entry (and exactly
one Research entry at any tier), and MAP.md's category arithmetic
agrees (Research total **1**; the service-model table shows
Research = SaaS 1). MAP.md's sibling-group sections list only
groups of size 2 or more, so no prose section exists for this
singleton; the arithmetic is the check, as in the earlier
singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **FR2125059322**.

## How functions were counted (a new category: the Group 1 method)

Research has no parent group, so there is no inherited taxonomy.
The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching
text; the matching sentence is stored as the claim's evidence in
the spec sheet. Marketing and assurance prose gets no tags.

The description is **two sentences**. Sentence 1 is a baseline
determination ("has been determined to have a security
categorization of Moderate (M)") — assurance prose that names no
function; the Moderate fact is carried as the fork's impact level,
not as a claim. Every claim comes from sentence 2, the platform
sentence. **9 claims in total, one per family.** Counts are a
**floor**, not a ceiling — with a two-sentence description, the
floor is low, and that is stated rather than padded.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
"open-source" and "multi-tenant SaaS" are licensing/delivery
properties tagged with platform dispositions; "analyzing" is
claimed with an Extended disposition (no analysis method is
named); "managing" is taken at records strength only (no
ingestion/harmonization reading is imported — none is named).

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Data commons development, configuration & operation | 1 | **Core** — the commons registry (records of commons, their kind, sponsor, membership, lifecycle) is the substrate; the commons runtime engine is Extended |
| 2 | Data ecosystems / data meshes | 1 | **Core** — the same registry: ecosystems and meshes are commons record kinds; cross-commons federation engines are Extended |
| 3 | Workspaces | 1 | **Core** — workspace registry records inside a commons |
| 4 | Data management (managing data) | 1 | **Core** — the dataset registry (metadata + checksum records); ingestion/harmonization engines are Extended |
| 5 | Data analysis (analyzing data) | 1 | Extended — analysis workspaces/engines compute; the description names no method, and the workspace registry (Core) is the records form the activity presupposes |
| 6 | Data sharing | 1 | **Core slice** — sharing is transacted as records: access requests, decisions, and time-boxed grants; the data delivery/transfer engine is Extended |
| 7 | Open access & controlled access data | 1 | **Core** — the access-tier designation is recorded on every dataset record, and controlled access is gated by the request/decision/grant records; enforcement on actual data delivery is Extended |
| 8 | Open-source platform (platform note) | 1 | Platform note — a licensing property of the fork; this build is likewise Apache-2.0 open source |
| 9 | Multi-tenant SaaS delivery (platform note) | 1 | Platform note — delivery prose; the build is a single-tenant reference deployment |

**Named absences, stated plainly:** the description names **no
dataset content of any kind** — no file formats, no record types,
no cohorts, no subject data — and **no** ingestion, harmonization,
indexing, query, or cohort-building function by name. Those
engines are the data-commons machinery the platform sentence
presupposes at one remove; they are registered as Extended gaps
below, not silently imported into the core. There is likewise
**no scoring or ranking vocabulary**: nothing is scored in this
build, and no record shape carries a field for a score.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *Privacy.* A research-data platform's records
substrate holds **metadata and opaque references only** — never
research subject data, never genomic or clinical payloads, never
dataset contents. Dataset records are metadata + a SHA-256
checksum in the legal-records pattern (content is hashed
transiently for verification and never stored), and every entity
shape is pinned by test so no field exists that could hold a
payload. (2) *Sharing as records.* "Sharing" data, for a
controlled-access commons, is transacted through people deciding:
a request, a decision by someone who is not the requester, and a
time-boxed grant. Those records are the substrate; moving the
actual data is the delivery engine, Extended. (3) *Derived grant
status.* A grant's status depends on the clock (and on whether it
has been revoked), so it is **derived at read and never stored** —
the group's signature derivation, with the grant record itself
carrying no status key. A commons' lifecycle status, by contrast,
is event-driven (it changes only through recorded lifecycle
actions), so it is stored, as in the sibling builds.

## The Core — what the merged build implements (11 functions)

One coherent, standards-based research-data records service that
the fork's claimed functions presuppose, built clean-room from
this spec:

1. **Data commons registry & membership** — commons records
   (`com-`): name, title, kind (`commons` / `ecosystem` / `mesh`
   — the description's own nouns), an opaque sponsor reference,
   an owner and a member list. Membership is the boundary every
   other commons-scoped function enforces. The lifecycle is
   event-driven: `draft → active → retired`, changed only through
   recorded lifecycle actions.
2. **Organization registry (opaque references)** — organizations
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier.
3. **Workspace registry** — workspaces (`ws-`) inside a commons:
   name and a stated purpose. Workspaces are where the claimed
   managing/analyzing/sharing activities are hosted; the registry
   is their records form.
4. **Dataset registry (metadata + checksums only)** — datasets
   (`ds-`) inside a commons: name, description, an access tier
   (`open` / `controlled` — the description's own designations),
   a SHA-256 checksum, and a byte size. Content is never stored.
   A dataset can be verified against caller-supplied content
   (hashed transiently, compared, discarded) in the
   legal-records pattern.
5. **Access request records** — requests (`ar-`) for controlled
   datasets: the requester, a stated purpose, and a requested
   duration in days. Requests against open datasets are rejected
   — open data needs no request, and a request record for one
   would be a false gate. The lifecycle is event-driven:
   `pending → approved / denied`, plus `withdrawn` while pending.
6. **Decision records** — a decision (`dec-`) on a pending
   request records the decider's outcome and note. One seam is
   enforced in the store: the decider is never the requester
   (**separation of duties**, AC-5).
7. **Access grant records** — an approval mints a grant (`gr-`):
   the dataset, the grantee, a start, and an expiry computed from
   the requested duration. A grant's status (`scheduled` /
   `active` / `expired` / `revoked`) is **derived at read** from
   the start, expiry, and revocation timestamp against the read
   clock — **never stored**. Revocation is a recorded event.
   Grants are records: they confer nothing by themselves; actual
   data delivery is Extended.
8. **Search & summary reporting** — literal case-insensitive
   substring search over accessible commons, organizations, and
   datasets in accessible commons; and a per-commons summary
   computed on read from records only: workspace count, dataset
   counts by tier, request counts by status, grant counts by
   derived status. Counts — never scores.
9. **API access** — every function above is exposed over a REST
   API (JSON), so the service composes with anything that speaks
   HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with commons membership
    (non-members cannot read or write a commons' content; the
    platform `admin` role can).
11. **Audit log** — an append-only audit trail: every commons,
    membership, organization, workspace, dataset, request,
    decision, grant, and revocation mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of NIST SP 800-171 Rev. 2 that define CMMC L2. The
  single parent fork sits at Moderate, so the baseline is the
  Moderate baseline, un-diluted (Merge Rule 1) and inherited in
  full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + commons membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity
    provider).
  - Access decisions → **AC-5** (separation of duties — the
    decider of an access request is never its requester, enforced
    in the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to the
    `audit_read` permission).
  - Commons / workspaces / datasets / requests / grants → **SI**
    (SI-10 information input validation — malformed input,
    including a request against an open dataset and any decision
    on a non-pending request, is rejected whole, never partially
    applied) and **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
  - Opaque-reference / metadata-only privacy is a build
    discipline answering to the same input discipline: because no
    entity shape has a field for research subject data or dataset
    content, none can be stored, leaked, or transmitted by this
    build. It is stated as a discipline, not dressed up as an
    additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `research` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`com-`, `org-`,
`ws-`, `ds-`, `ar-`, `dec-`, `gr-`); a failed operation consumes
no id and changes nothing. Durations are whole days (positive
`int`; bools, floats, and strings raise `ValidationError`).
Grant status is derived at read and never stored; the stored
grant record carries no `status` key.

- `research/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read,
  create_commons, enter, decide, record, manage_members,
  audit_read, admin}, member = {read, create_commons, enter,
  decide, record}, viewer = {read}; `require(user, action)` raises
  `PermissionDenied`. Actions tuple: ("read", "create_commons",
  "enter", "decide", "record", "manage_members", "audit_read",
  "admin").
- `research/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file. (Same shape as the sibling builds.)
- `research/errors.py` — `ResearchError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.
- `research/store.py` — `ResearchStore(audit=None)`. Commons-
  scoped operations enforce membership (or platform admin) and,
  for User-like actors, the role permission for the operation's
  action (a plain string actor carries identity but no role; role
  enforcement for those happens in the service layer — the sibling
  convention). The store audits every successful mutation; the
  service layer audits denied attempts (`action:denied`) and audit
  reads, so nothing is recorded twice. Operations:
  - Commons: `create_commons(actor, name, title, kind,
    sponsor_ref)` (creator is owner + first member; duplicate
    name rejected; kind ∈ COMMONS_KINDS) → view; `get_commons(
    actor, commons_id)`; `list_commons(actor)` (only commons the
    actor belongs to, or all for admin); `add_member(actor,
    commons_id, username)` (action `manage_members`);
    `activate_commons(actor, commons_id)` (from `draft` only);
    `retire_commons(actor, commons_id)` (from `draft` or
    `active`); `commons_summary(actor, commons_id, now=None)`.
    Commons record shape (pinned): `{id, name, title, kind,
    sponsor_ref, status, owner, members, created_by,
    created_utc}`; the view is the record with `members` copied.
  - Organizations: `create_organization(actor, ref, label)`
    (action `enter`; duplicate ref rejected) → record `{id, ref,
    label, created_by, created_utc}` (pinned); `update_
    organization(actor, org_id, label)`; `get_organization(actor,
    org_id)`; `list_organizations(actor)`.
  - Workspaces: `create_workspace(actor, commons_id, name,
    purpose)` (action `record`) → record `{id, commons_id, name,
    purpose, created_by, created_utc}` (pinned); `get_workspace(
    actor, workspace_id)`; `list_workspaces(actor, commons_id)`.
  - Datasets: `register_dataset(actor, commons_id, name,
    description, access_tier, sha256, size_bytes)` (action
    `record`; tier ∈ ("open", "controlled"); sha256 must be 64
    hex chars, stored lowercased; size_bytes a non-negative int)
    → record `{id, commons_id, name, description, access_tier,
    sha256, size_bytes, created_by, created_utc}` (pinned — no
    content field exists); `get_dataset(actor, dataset_id)`;
    `list_datasets(actor, commons_id, access_tier=None)`;
    `verify_dataset(actor, dataset_id, content)` where content
    is `bytes` → `{"dataset_id", "sha256", "computed_sha256",
    "matches"}`; content is hashed and discarded, never stored.
  - Access requests: `create_access_request(actor, dataset_id,
    purpose, duration_days)` (action `enter`; requester is the
    actor; the dataset must be `controlled` — an open dataset
    raises `ValidationError`; duration_days a positive int) →
    record `{id, dataset_id, commons_id, requester, purpose,
    duration_days, status: "pending", created_by, created_utc}`
    (pinned); `get_access_request(actor, request_id)`;
    `list_access_requests(actor, dataset_id)`;
    `withdraw_access_request(actor, request_id)` (requester or
    commons member with `enter`; only from `pending` → status
    `withdrawn`).
  - Decisions: `decide_access_request(actor, request_id, approve,
    note="", starts_at=None)` (action `decide`; the decider is
    never the requester — seam `_check_decider_not_requester`;
    only a `pending` request can be decided; on approval, mint a
    grant with `starts_at` (default: now) and `expires_at` =
    starts_at + duration_days) → `{"decision": {...}, "request":
    {...}}` plus `"grant": {...}` (the grant **view**, with
    derived status) on approvals only. Decision record: `{id,
    request_id, dataset_id, commons_id, decider, approve, note,
    created_utc}`.
  - Grants: stored record `{id, dataset_id, commons_id,
    request_id, grantee, starts_at, expires_at, revoked_at,
    created_by, created_utc}` (pinned — **no `status` key**).
    Derivation seam: `_derive_grant_status(grant, moment)` →
    `"revoked"` if `revoked_at` is not None, else `"expired"` if
    moment > expires_at, else `"scheduled"` if moment <
    starts_at, else `"active"`. `_grant_view(grant, now=None)`
    adds `status`. `get_grant(actor, grant_id, now=None)`;
    `list_grants(actor, commons_id, status=None, now=None)`
    (status filters on the derived status); `revoke_grant(actor,
    grant_id)` (action `decide`; sets `revoked_at`; revoking an
    already-revoked grant raises `ValidationError`).
  - Search: `search(actor, query)` → `{"commons": [...],
    "organizations": [...], "datasets": [...]}` — literal
    case-insensitive substring search over commons the actor can
    access (name/title), all organizations (ref/label), and
    datasets in accessible commons (name/description).
  - `commons_summary` returns `{"commons_id", "kind", "status",
    "workspaces", "datasets_by_tier": {"open", "controlled"},
    "requests_by_status": {"pending", "approved", "denied",
    "withdrawn"}, "grants_by_status": {"scheduled", "active",
    "expired", "revoked"}}` — counts computed on read.
- `research/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User`
  / `X-Role` headers (role must match the registry). Endpoints per
  the group README. Errors are JSON `{error}` with 400/401/403/404
  as applicable. Denied attempts are audited. Routes:
  `GET /health`; `GET /audit`; `GET /search?q=`; `POST /commons`,
  `GET /commons`, `GET /commons/{id}`, `POST
  /commons/{id}/members`, `POST /commons/{id}/activate`, `POST
  /commons/{id}/retire`, `GET /commons/{id}/summary`;
  `POST /organizations`, `GET /organizations`, `GET
  /organizations/{id}`, `POST /organizations/{id}`;
  `POST /commons/{id}/workspaces`, `GET /commons/{id}/workspaces`,
  `GET /workspaces/{id}`; `POST /commons/{id}/datasets`, `GET
  /commons/{id}/datasets`, `GET /datasets/{id}`, `POST
  /datasets/{id}/verify` (JSON body `{"content": "..."}` — the
  string is UTF-8-encoded, hashed, and discarded);
  `POST /datasets/{id}/access-requests`, `GET
  /datasets/{id}/access-requests`, `GET /access-requests/{id}`,
  `POST /access-requests/{id}/decide`, `POST
  /access-requests/{id}/withdraw`; `GET /grants/{id}`, `GET
  /commons/{id}/grants`, `POST /grants/{id}/revoke`. Reads that
  derive grant status accept `?now=`.
- `research/__main__.py` — `python -m research serve --host
  --port [--audit-log PATH] [--certfile --keyfile]`, default port
  **8798**, with demo users `alice=admin, bob=member,
  carol=viewer` (documented as demo identities; production
  identity is the embedding organization's).

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**:
a mutant store whose `_derive_grant_status` always returns
`"active"` reports an expired and a revoked grant as active — the
canonical expectation rejects both — and the external mutation
drill (patching `_derive_grant_status` in the real `store.py`)
makes the derivation-dependent tests fail; see `tests/README.md`
for the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Data commons runtime engine (actually developing, configuring,
  and operating a running commons; the build is its records
  substrate)
- Data ingestion / ETL engine (nothing is ingested; dataset
  records are metadata + checksums)
- Data harmonization engine (common-data-model mapping and
  transformation of real datasets)
- Indexing & metadata catalog engines beyond the registry
  (search indexes over dataset contents)
- Query & analysis workspace engines (the analysis computation
  the workspaces host; no method is named in the description)
- Cohort builder / cohort discovery engine
- Cross-commons federation / data mesh networking (commons here
  are records; no inter-commons protocol runs)
- Data delivery / transfer engine for sharing (grants are
  records; no data moves)
- Access enforcement on data delivery (the gate on actual reads
  of dataset content; this build gates records)
- Identity provider / identity management service (IA-2 stays
  with the embedding organization)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (claimed by the fork of its own
platform; single-tenant reference deployment); demo identities
are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **9 tagged claims** (one per
  taxonomy family, each with its source sentence as evidence —
  all nine from the description's single platform sentence).
- Core: **11 / 11** core functions implemented, at the Moderate/L2
  baseline, each with tracing tests.
- Tests: **85 run, 85 passed**, including the mutation-verified
  grant-derivation negative control (the always-`active` mutant
  makes exactly 7 tests fail; see `tests/README.md`).
- Extended: the 10 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
