# Union Spec — Legal & Policy, CMMC L2 (DeadRamp Phase 2, Group 49)

The merged functional spec for the **Legal & Policy L2 singleton**:
**1 fork**, category **Legal & Policy** (a brand-new category — no
group exists at any other tier), CMMC tier **L2** (the member is
FedRAMP **Moderate** in `forks.json` — verified). The member list was
reconciled two ways with **zero diffs**: `forks.json` carries exactly
one Legal & Policy / L2 entry, and MAP.md's category arithmetic
agrees (Legal & Policy total **2** = L2 1 + untiered 1 — the other
offering, Litmas AI, carries no baseline in the source and stays
untiered; L1 0, L3-adjacent 0). MAP.md's sibling-group sections list
only groups of size 2 or more, so no prose section exists for this
singleton; the arithmetic is the check, as in the earlier singleton
builds.

| Fork | Vendor | Product | Status |
|---|---|---|---|
| FR2619254906 | Vulcan Technologies, Inc. | VulcanGov (Justinian for Government) | Legacy FedRAMP Ready |

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **FR2619254906**. No live
fetching was needed: the description was present in the cached
dataset.

**This category is not the Law Enforcement category.** Group 34's
Law Enforcement L2 build is a legal *research records* substrate for
two research platforms the source filed under "Law Enforcement."
Legal & Policy is its own registry category, and this fork is a
different kind of product: an **AI agent workspace** grounded in a
curated legal library, with an administration console. House patterns
from the legal-records substrate are reused where they genuinely fit
(digest-only search records, metadata + checksum document records,
opaque references), and the reuse is stated where it happens; the
taxonomy, core, and spec here are this fork's own.

## How functions were counted (a new category: the Group 1 method)

Legal & Policy has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching text;
the matching sentence is stored as the claim's evidence in the spec
sheet. Marketing prose gets no tags. **11 claims in total, one per
family.** Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/extract.py`):

- **One sentence carries the product.** The description's first
  sentence names every product function (agent workspace, library,
  search, sandboxes, code execution, document generation, and the
  administration console's three functions). Every product claim
  rests on it. Its opening identity clause ("is a SaaS AI platform
  for government") tags only the `saas_delivery` platform family.
- **Infrastructure prose tags nothing.** The delivery sentence
  (GovCloud region, ECS Fargate, Aurora, S3, OpenSearch,
  ElastiCache) and the data-flow sentence (Bedrock inference over a
  documented transport bridge, cross-boundary disclosure practice)
  name components and practices, not functions of a records
  substrate. LLM inference is the agent runtime — registered
  Extended under `ai_agent_workspace`, not tagged as its own claim.
- **Assurance prose is not a function claim.** The encryption /
  FIPS-validated-modules / security-monitoring clauses tag nothing;
  they are answered in this spec's platform notes. The same
  sentence's identity clause ("identity and access are federated
  through Okta for Government with enforced multi-factor
  authentication") tags `identity_federation` with a **platform**
  disposition (the Group 45 precedent): the build ships RBAC hooks,
  not an IdP.
- **Audience and publication prose tag nothing.** The availability
  sentence (federal, state and local governments) and the Trust
  Center / gated-portal sentence name no implementable function;
  "live availability status" is the vendor's status page, not a
  function of this build.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | AI agent workspace | 1 | **Core slice** — workspace & agent-session records. The agent runtime (LLM inference, agent orchestration) is Extended |
| 2 | Curated legal library (statutes, regulations, guidance, datasets) | 1 | **Core** as the library registry (records of sources; the corpus content itself is Extended) |
| 3 | Full-text and semantic search | 1 | **Core slice** — saved-search records (digest only) + registry-metadata search. Full-text and semantic engines: Extended |
| 4 | Secure single-use agent sandboxes | 1 | **Core slice** — sandbox session records with the single-use rule enforced (one execution per sandbox session). The sandbox runtime (isolation, execution environment) is Extended |
| 5 | Code execution (in agent sandboxes) | 1 | **Core slice** — execution records. The execution engine itself: Extended |
| 6 | Document generation | 1 | **Core slice** — generated-document records (metadata + checksum; content never stored). The generation engine: Extended |
| 7 | Agency user management (administration console) | 1 | **Core** — agency registry, membership, RBAC |
| 8 | Session audit visibility (administration console) | 1 | **Core** — append-only audit log with admin-gated read |
| 9 | Usage export (administration console) | 1 | **Core** — usage records + export manifests with checksums over the exported set |
| 10 | Identity federation & MFA (platform) | 1 | Platform note — the build ships RBAC hooks, not an IdP; federation and MFA stay with the embedding organization |
| 11 | SaaS delivery (platform) | 1 | Platform note — the build is a single-tenant reference deployment |

## Privacy discipline (hard rule, enforced by tests)

Carried from the legal-records groups, because this fork's workspace
handles agency legal work:

- **Records hold metadata and digests, not content.** Documents are
  registry metadata + SHA-256 checksums, never content; integrity is
  checked by verify-by-content (the caller supplies bytes, the build
  hashes and compares, stores nothing).
- **Search queries are stored as SHA-256 digests only.** The store
  has no parameter that can accept query text; the service layer
  hashes before the store ever sees a value. A saved-search record
  proves *that* a search was saved and how many results it returned,
  never what it asked.
- **No entity shape can hold a real identifier of a person or a
  matter's substance.** Agencies, workspaces, sessions, executions,
  library sources, searches, documents, usage and exports are all
  keyed by opaque caller-supplied `*_ref` strings plus caller labels;
  every entity's exact key set is pinned by tests, and the store's
  signatures reject smuggled fields.
- **Nothing is scored.** No record shape carries a score, rating, or
  computed status of a legal question. Usage totals are sums of
  recorded quantities — counts, not judgments.

**Date-derived status is derived at read, never stored:** a
session's `expired` flag is computed from its `expires_at` against
the read clock, and a sandbox session's `sandbox_consumed` flag is
computed from whether an execution record exists for it. The stored
session record carries neither key — pinned by test. (The session
lifecycle itself — `active` → `closed` — is a guarded transition,
not a date derivation.)

**The signature invariant — single use, enforced in the store.** A
sandbox session accepts **exactly one** execution record. The seam
is `_check_sandbox_unused` in the store: before an execution is
recorded against a sandbox session, the store checks that no
execution exists for it yet; a second attempt raises
`ValidationError`, consumes no id, and changes nothing. This is the
group's negative control (see the implementation contract).

## The Core — what the merged build implements (13 functions)

The records substrate the claimed functions jointly presuppose:

1. **Agency registry & membership** — agencies (`agy-`): an opaque
   `agency_ref`, a label, and a member list. Membership is the
   boundary every agency-scoped function enforces; only the
   agency's creator or a platform admin may add members.
2. **Workspace registry** — workspaces (`wsp-`) inside an agency:
   opaque `workspace_ref` (unique within the agency) and a title.
3. **Agent session records** — sessions (`ses-`) in a workspace:
   opaque `session_ref`, an optional purpose label, a `sandbox`
   flag, an optional `expires_at`, and a guarded lifecycle
   (`active` → `closed`). Read views derive `expired` and
   `sandbox_consumed`; the stored record carries neither.
4. **Execution records** — executions (`exe-`) recorded against a
   session: opaque `execution_ref`, a kind, an optional language
   label. The single-use rule for sandbox sessions is enforced
   here; executions against closed sessions are rejected.
5. **Library source registry** — the curated library as metadata
   records (`lib-`): opaque `source_ref`, a kind (`statute`,
   `regulation`, `guidance`, `dataset`), an optional title and
   opaque jurisdiction reference. No content — the corpus itself
   is Extended.
6. **Saved-search records** — a saved search (`sea-`) in an agency
   (optionally tied to a workspace): opaque `search_ref`, the
   query's SHA-256 digest (never the query), and a result count.
7. **Document registry** — documents (`doc-`) in a workspace:
   opaque `doc_ref`, a kind (`generated` / `uploaded`), SHA-256
   checksum (validated lowercase hex), and a byte count. Content
   is never stored.
8. **Verify-by-content** — given bytes, recompute the SHA-256 and
   compare it to the registered checksum; returns the comparison,
   stores nothing.
9. **Usage records** — usage (`use-`) recorded per agency
   (optionally per workspace/session): opaque `usage_ref`, a kind
   (`search`, `session`, `execution`, `document`, `inference`,
   `export`), and a quantity that must be a positive integer —
   booleans, floats, and strings are rejected at the boundary.
10. **Usage export manifests** — an export (`exp-`) over an agency's
    usage records in an optional time window: the record count,
    the total quantity, and a SHA-256 checksum of the canonical
    exported set, computed at export time from the records.
11. **Registry reporting** — an agency report computed on read:
    workspace, session, execution, search, document and export
    counts, sessions by lifecycle status, sandbox sessions
    consumed (derived), and usage sums by kind. No analytics
    engine, no scores.
12. **Registry search** — literal case-insensitive substring search
    over registry metadata (references, titles, kinds), scoped to
    agencies the actor belongs to (or all for a platform admin),
    plus the platform library. Digests are never matched or
    returned as searchable text.
13. **Access control & audit** — platform roles `admin`, `member`,
    `viewer` with a permission matrix enforced on every operation,
    layered with agency membership; and an append-only audit log
    recording every mutation and every denied attempt with actor,
    action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of NIST SP 800-171 Rev. 2 that define CMMC L2. The
  single parent fork sits at Moderate, so the union baseline is
  the Moderate baseline, un-diluted (Merge Rule 1) and inherited
  in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + agency membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; the build ships hooks, not an identity
    provider. The fork's own description federates identity to an
    external IdP with enforced MFA; that is the embedding
    organization's layer, exactly as IA-2 sits here).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review — append-only store, audit-read
    restricted to the `audit_read` permission, held by admin
    only). At L2 the audit mapping holds on **both** sides of the
    crosswalk, because 800-171 carries an audit family (3.3).
  - Document checksums & verify-by-content → **SI** (SI-7
    software, firmware and information integrity — a Moderate
    selection, cited as such; hashes are computed with the
    standard library).
  - Registries, lifecycle guards, the single-use seam, digest
    discipline → **SI** (SI-10 information input validation —
    malformed input, including any non-integer quantity, bad
    checksum, duplicate reference, or second sandbox execution,
    is rejected whole, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS when
    a certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here.
    The fork's description claims FIPS-validated modules of its
    own platform; this build claims none — Python's standard
    library is not a FIPS-validated cryptographic module).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `legalpol` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`agy-`, `wsp-`,
`ses-`, `exe-`, `lib-`, `sea-`, `doc-`, `use-`, `exp-`); a failed
operation consumes no id and changes nothing. All timestamps are
UTC ISO-8601. Validation always precedes mutation.

- `legalpol/errors.py` — `LegalPolError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `LegalPolError`).
- `legalpol/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `agency_read, agency_write,
  workspace_write, session_write, library_write, search_write,
  document_write, usage_write, export, report_read, audit_read`.
  `PERMISSIONS`: admin ⊇ all eleven; member = all except
  `agency_write` and `audit_read`; viewer = {agency_read,
  report_read}. `permissions_for(role)`, `can(user, action)`,
  `require(user, action)` raising `PermissionDenied`.
- `legalpol/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)`; `.entries()` returns entry
  dicts with keys `ts, actor, action, target, details`.
  Append-only; optional JSONL file persistence; reloads an
  existing file on construction.
- `legalpol/store.py` — `LegalPolStore(audit=None)`. The store
  records every successful mutation to its audit log (when one is
  attached); the HTTP layer records denials and `audit_read`
  only. Two boundaries on every agency-scoped operation: the
  actor must be an agency member or hold the platform `admin`
  role, else `PermissionDenied`; and the operation's role
  permission is required (enforced when the actor is a `User`; a
  plain-string actor carries identity but no role, so role
  enforcement for those happens in the service layer — the house
  convention). The platform library (sources) is not
  agency-scoped: writes require `library_write`; reads are open
  to any actor. Methods:
  - `create_agency(agency_ref, label, actor)` (action
    `agency_write`) → `{id, agency_ref, label, members,
    created_by, created_utc}`; `agency_ref` a non-empty string,
    unique across agencies (duplicate → `ValidationError`); the
    creator is the first member. Audits `agency_create`.
    `list_agencies(actor)` → agencies the actor is a member of,
    or all for a platform admin, in creation order.
    `get_agency(agency_id, actor)` (`NotFoundError`;
    `PermissionDenied` for a non-member non-admin).
  - `add_member(agency_id, username, actor)` → updated agency
    dict. Only the agency's creator or a platform admin may add;
    adding an existing member raises `ValidationError`. Audits
    `member_add`.
  - `create_workspace(agency_id, workspace_ref, title, actor)`
    (action `workspace_write`) → `{id, agency_id, workspace_ref,
    title, created_by, created_utc}`; `workspace_ref` non-empty
    and unique within the agency. Audits `workspace_create`.
    `list_workspaces(agency_id, actor)`; `get_workspace(...)`
    (an id from another agency → `NotFoundError`).
  - `create_session(agency_id, workspace_id, session_ref,
    actor, purpose=None, sandbox=False, expires_at=None)`
    (action `session_write`) → stored `{id, agency_id,
    workspace_id, session_ref, purpose, sandbox, status,
    expires_at, created_by, created_utc}`; status starts
    `active`; `sandbox` must be a bool; `expires_at` when given
    must parse as an ISO-8601 timestamp (else
    `ValidationError`); `session_ref` non-empty and unique
    within the workspace. Audits `session_create`.
    `get_session(agency_id, session_id, actor, now=None)` →
    the stored fields **plus derived** `expired` (bool:
    `expires_at` is set and the read clock is past it) and
    `sandbox_consumed` (bool: the session is a sandbox session
    and an execution exists for it). **The stored record never
    carries either key** — `list_sessions(agency_id, actor,
    workspace_id=None, now=None)` returns the same derived
    views. `close_session(agency_id, session_id, actor)`
    (action `session_write`): `active` → `closed`; wrong state
    → `ValidationError`. Audits `session_close`.
  - `record_execution(agency_id, session_id, execution_ref,
    actor, kind="code", language=None)` (action
    `session_write`) → `{id, agency_id, session_id,
    execution_ref, kind, language, created_by, created_utc}`;
    `kind` one of `code`, `document`; the session must exist in
    this agency and be `active` (closed → `ValidationError`);
    `execution_ref` non-empty and unique within the session.
    **Single-use seam:** when the session is a sandbox session,
    `_check_sandbox_unused(session_id)` runs before anything is
    stored and raises `ValidationError` if an execution already
    exists for the session. Audits `execution_record`.
    `list_executions(agency_id, session_id, actor)`.
  - `register_library_source(source_ref, kind, actor,
    title=None, jurisdiction_ref=None)` (action
    `library_write`) → `{id, source_ref, kind, title,
    jurisdiction_ref, created_by, created_utc}`; `kind` one of
    `statute`, `regulation`, `guidance`, `dataset`;
    `source_ref` non-empty and unique across the library.
    Audits `library_register`. `list_library_sources(actor,
    kind=None)`; `get_library_source(source_id, actor)`.
  - `save_search(agency_id, search_ref, query_sha256,
    result_count, actor, workspace_id=None)` (action
    `search_write`) → `{id, agency_id, workspace_id, search_ref,
    query_sha256, result_count, created_by, created_utc}`.
    **There is no parameter for query text.** `query_sha256`
    must be exactly 64 lowercase hex characters; `result_count`
    an int ≥ 0 (booleans and floats rejected); `search_ref`
    non-empty and unique within the agency; `workspace_id` when
    given must name a workspace in this agency. Audits
    `search_save`. `list_searches(agency_id, actor,
    workspace_id=None)`; `get_search(...)`.
  - `register_document(agency_id, workspace_id, doc_ref,
    sha256, size_bytes, actor, kind="generated",
    session_id=None)` (action `document_write`) → `{id,
    agency_id, workspace_id, session_id, doc_ref, kind,
    sha256, size_bytes, created_by, created_utc}`; `kind` one
    of `generated`, `uploaded`; `sha256` exactly 64 lowercase
    hex; `size_bytes` an int ≥ 0 (booleans and floats
    rejected); `doc_ref` non-empty and unique within the
    workspace; `session_id` when given must name a session in
    this workspace. Audits `document_register`.
    `get_document(...)`; `list_documents(agency_id, actor,
    workspace_id=None)`.
  - `verify_document(agency_id, doc_id, content, actor)`
    (action `agency_read`) → `{document_id, sha256,
    computed_sha256, matches}`; `content` is bytes (a str is
    encoded as UTF-8); non-mutating, records nothing.
  - `record_usage(agency_id, usage_ref, kind, quantity, actor,
    session_id=None, workspace_id=None)` (action
    `usage_write`) → `{id, agency_id, workspace_id, session_id,
    usage_ref, kind, quantity, created_by, created_utc}`;
    `kind` one of `search`, `session`, `execution`, `document`,
    `inference`, `export`; `quantity` an int > 0 (booleans,
    floats, and strings rejected); `usage_ref` non-empty and
    unique within the agency; linked ids when given must exist
    in this agency. Audits `usage_record`.
    `list_usage(agency_id, actor, kind=None)`.
  - `export_usage(agency_id, export_ref, actor, since=None,
    until=None)` (action `export`) → `{id, agency_id,
    export_ref, since, until, record_count, total_quantity,
    checksum, created_by, created_utc}`; the exported set is the
    agency's usage records whose `created_utc` falls in
    [`since`, `until`] (open-ended when a bound is None);
    `checksum` is the SHA-256 of the canonical JSON (sorted
    keys, records sorted by id) of `{id, kind, quantity,
    created_utc}` for each record in the set; `export_ref`
    non-empty and unique within the agency. Audits
    `usage_export`. `list_exports(agency_id, actor)`.
  - `agency_report(agency_id, actor, now=None)` (action
    `report_read`) → `{agency_id, workspace_count,
    session_count, sessions_by_status, sandbox_sessions,
    sandbox_sessions_consumed, execution_count, search_count,
    document_count, export_count, usage_by_kind}` — counts and
    quantity sums computed on read from the records;
    `sandbox_sessions_consumed` is the derived count (sandbox
    sessions with an execution recorded).
  - `search_registry(actor, query)` (action `agency_read`) →
    `{agencies, workspaces, sessions, library_sources,
    documents}`: literal case-insensitive substring match over
    `*_ref` fields, titles, labels, and kinds, restricted to
    agencies the actor is a member of (or all for a platform
    admin); library sources are platform-wide. Empty query →
    `ValidationError`. Digests and checksums are never matched
    or returned as searchable text.
- `legalpol/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name
  → role. Auth via `X-User` / `X-Role` headers (the role must
  match the registry; unknown user or mismatched role → 401).
  Errors are JSON `{error}` with 400/401/403/404 as applicable;
  denied attempts (401 and 403) are audited with the action name
  suffixed `:denied`, and no stack trace is ever returned. The
  service layer is the only place query text may appear: it
  SHA-256-hashes the `query_text` request field before calling
  the store, and never logs or stores the text. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /agencies` (agency_read) → `{"agencies": [...]}`;
    `POST /agencies` `{agency_ref, label}` (agency_write) →
    201 agency dict
  - `GET /agencies/{id}` (agency_read)
  - `POST /agencies/{id}/members` `{username}` → agency dict
    (the store enforces creator-or-admin)
  - `GET /agencies/{id}/workspaces` (agency_read) →
    `{"workspaces": [...]}`; `POST /agencies/{id}/workspaces`
    `{workspace_ref, title}` (workspace_write) → 201
  - `GET /agencies/{id}/sessions?workspace_id=` (agency_read)
    → `{"sessions": [...]}` (derived views); `POST
    /agencies/{id}/sessions` `{workspace_id, session_ref,
    purpose?, sandbox?, expires_at?}` (session_write) → 201
    stored-shape session dict
  - `POST /agencies/{id}/sessions/{sid}/close`
    (session_write) → session dict
  - `GET /agencies/{id}/sessions/{sid}/executions`
    (agency_read) → `{"executions": [...]}`; `POST
    /agencies/{id}/sessions/{sid}/executions`
    `{execution_ref, kind?, language?}` (session_write) → 201
  - `GET /library?kind=` → `{"sources": [...]}`; `POST
    /library` `{source_ref, kind, title?, jurisdiction_ref?}`
    (library_write) → 201
  - `GET /agencies/{id}/searches?workspace_id=` (agency_read)
    → `{"searches": [...]}`; `POST /agencies/{id}/searches`
    `{search_ref, query_text | query_sha256, result_count,
    workspace_id?}` (search_write) → 201 (digest computed here
    when `query_text` is given)
  - `GET /agencies/{id}/documents?workspace_id=`
    (agency_read) → `{"documents": [...]}`; `POST
    /agencies/{id}/documents` `{workspace_id, doc_ref,
    sha256, size_bytes, kind?, session_id?}` (document_write)
    → 201
  - `POST /agencies/{id}/documents/{did}/verify`
    `{content_b64}` (agency_read) → verify dict; malformed
    base64 → 400
  - `GET /agencies/{id}/usage?kind=` (agency_read) →
    `{"usage": [...]}`; `POST /agencies/{id}/usage`
    `{usage_ref, kind, quantity, session_id?, workspace_id?}`
    (usage_write) → 201
  - `GET /agencies/{id}/exports` (agency_read) →
    `{"exports": [...]}`; `POST /agencies/{id}/exports`
    `{export_ref, since?, until?}` (export) → 201
  - `GET /agencies/{id}/report` (report_read) → report dict
  - `GET /search?q=` (agency_read) → registry search dict
- `legalpol/__main__.py` — `python -m legalpol serve --host
  --port [--audit-log PATH] [--certfile --keyfile]` with demo
  users `alice=admin, bob=member, carol=viewer` (documented as
  demo identities; production identity is the embedding
  organization's, per IA-2 above). Default port 8799.

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to, and include the **negative control**: a mutant store whose
`_check_sandbox_unused` performs no check at all, so a second
execution against a single-use sandbox session is accepted. The
canonical expectation is shown to reject it — the real store must
raise `ValidationError` on the second execution while the mutant
accepts — proving the suite catches the single-use defect class
rather than merely passing. The negative control must
additionally be **mutation-verified**: patching the real seam in
`src/` with the mutant body must make the suite fail; the run
and its result are recorded in `tests/README.md`.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- **AI agent runtime** — LLM inference, agent orchestration,
  grounding/retrieval over the library, and the model transport
  bridge the description names. The core records workspaces,
  sessions and executions; it runs no agent and calls no model.
- **Legal corpus content** — the statutes, regulations, guidance
  and datasets themselves, their curation and continuous update
  pipeline, and their licensing. The core registers sources as
  records and holds no content.
- **Full-text & semantic search engines** — full-text indexing
  and vector/semantic ranking over the corpus. The core searches
  registry metadata only and records searches as digests.
- **Sandbox runtime** — the isolated, single-use execution
  environment itself (container isolation, resource limits,
  teardown). The core records sandbox sessions and enforces the
  single-use rule over execution records; it executes nothing.
- **Code execution engine** — running code, in sandboxes or
  anywhere else. Execution is recorded, never performed.
- **Document generation engine** — drafting/generation of
  documents from corpus and session context. The core registers
  generated documents as metadata + checksums; it generates
  none.
- **Identity provider / federation service** — the fork's
  description federates identity (Okta for Government, enforced
  MFA); IA-2 stays with the embedding organization and this
  build ships hooks, not an IdP.
- **Security monitoring & platform security services** —
  monitoring, scanning and the native cloud security services
  the description names are the deployment platform's layer.
- **FIPS-validated cryptography** — claimed by the fork's own
  platform; Python's standard library is not a FIPS-validated
  module, and this build claims no validated cryptography.

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: 1 / 1 forks spec'd (11 claims total, one per taxonomy
  family, each with its source sentence as evidence).
- Core: 13 core functions implemented, each with tracing tests.
- Extended: 9 gaps specified above, **not** implemented in this
  build (the agent runtime, the corpus content, the search
  engines, the sandbox runtime, the code execution engine, the
  document generation engine, the IdP/federation service,
  platform security monitoring, FIPS-validated cryptography).
- Platform notes (claimed as platform families, not built):
  identity federation & MFA, SaaS delivery.
