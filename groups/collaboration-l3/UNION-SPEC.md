# Union Spec — Collaboration, CMMC L3-adjacent (DeadRamp Phase 2, Group 6)

The merged functional spec for the **Collaboration L3-adjacent** sibling
group: **17 forks**, category **Collaboration**, CMMC tier
**L3-adjacent** (every member is FedRAMP **High** in `forks.json` —
verified, so the group is single-tier and the merge takes the group
baseline in full, per Merge Rule 2). The member list in `forks.json`
was reconciled against `MAP.md`'s "Collaboration — L3-adjacent (17)"
section: **zero diffs** in both directions.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 17
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced by
the General Services Administration, last change 2026-10-22), product
records joined by FedRAMP ID. No live fetching was needed: all 17
descriptions were present in the cached dataset.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 2 merged build** (`../collaboration-l2/`) — itself the
   union of the 57 Collaboration L2 (FedRAMP Moderate) forks, shipped
   as a working clean-room collaboration service.
2. This group's **17 High forks**, via the spec sheets in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the merge
takes the **union** of the parents' baselines (Rule 1), the merged
fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheets are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was re-run
independently by the coordinator, and both negative controls were
mutation-verified by patching the implementation (see Verification
below).

**Reuse, stated explicitly:** where functions overlap, this build
reuses Group 2's own open-source code (Apache-2.0, ours). The package
keeps Group 2's seven-module layout (`errors`, `access`, `audit`,
`store`, `service`, `__main__`, `__init__` — the last byte-identical);
six modules were modified for the tier uplift (`errors.py`,
`audit.py`, `access.py`, `store.py`, `service.py`, `__main__.py`). The
uplift analysis below names what the High baseline demanded beyond the
L2 core and what was done about each item — implemented, or gap-listed
by name.

## How functions were counted

The same fixed 21-function taxonomy as Group 2 (verbatim — same ids,
labels, and matching patterns, including its three documented
matcher behaviors) was matched against each offering's own public
description. A function is claimed for a fork **only** when the
description contains matching text; the matching sentence is stored as
the claim's evidence in the spec sheet. 13 of 17 offerings carry at
least one tagged claim (**49 claims** in total); 4 descriptions carry
none: CoLab AI Inc's description is a 259-character summary with no
taxonomy vocabulary, and the Koniag Government Services EHRS,
Salesforce Government Cloud Plus, and ServiceNow Government Community
Cloud listings describe platforms and authorization boundaries rather
than enumerated features. Their full text is still in the spec sheets
— nothing is hidden, and no function was invented for them. Counts
below are therefore a **floor**, not a ceiling, on what these products
do.

The floor effect is stronger at High than it was at Moderate, and the
spec says so plainly: High listings are written as boundary and
enclave descriptions. The clearest evidence is Google Workspace — the
category's flagship collaboration suite — whose High listing tags
exactly **one** function (shared workspaces). Nobody familiar with the
product believes it lacks messaging, calendaring, or presence; its
listing simply does not enumerate features. The ranking below is read
with that lens.

## Function ranking — all 17 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | APIs, integrations & interoperability | 10 | 59% | **Core** (the service is API-first) |
| 2 | AI assistance, speech & analytics | 5 | 29% | Extended (search in Core is literal substring matching, not semantic/AI search — stated plainly) |
| 3 | Access control & authentication | 5 | 29% | **Core** (High baseline hooks, uplifted — see below) |
| 4 | Records, governance & compliance management | 5 | 29% | Extended (file versioning and the audit trail in Core are the seed) |
| 5 | Workflow & process automation | 4 | 24% | Extended — the siblings' claims are domain process engines that run *on top of* a collaboration substrate; this build is that substrate |
| 6 | Encryption | 4 | 24% | Platform note (TLS supported; FIPS caveat in the baseline section) |
| 7 | Audit logging & trails | 3 | 18% | **Core** (High baseline hooks, uplifted — see below) |
| 8 | Voice, telephony & contact center | 2 | 12% | Extended (real-time media transport) |
| 9 | Shared workspaces & team collaboration | 2 | 12% | **Core** |
| 10 | Task, project & work management | 2 | 12% | Extended (board cards in Core are the seed; full task/project management is not claimed) |
| 11 | Notifications, alerts & emergency communications | 2 | 12% | **Core** (the in-platform notification queue: mentions, invites, shares) |
| 12 | Search & discovery | 2 | 12% | **Core** (literal substring search across workspace objects) |
| 13 | Messaging & chat | 1 | 6% | **Core** |
| 14 | File sharing, storage & content management | 1 | 6% | **Core** |
| 15 | Learning, training & mentoring | 1 | 6% | Extended |
| 16 | Meetings, video & web conferencing | 0 | 0% | Extended (media transport — a standard-library text build carries no audio/video; the coordination surface around meetings — calendaring, channels, presence — is Core) |
| 17 | Whiteboarding, visual collaboration & co-authoring | 0 | 0% | **Core** (boards of positioned text cards; no raster canvas — stated plainly; see the core-boundary note below) |
| 18 | Calendaring & scheduling | 0 | 0% | **Core** (see the core-boundary note below) |
| 19 | Presence & availability | 0 | 0% | **Core** (see the core-boundary note below) |
| 20 | Electronic & digital signatures | 0 | 0% | Extended |
| 21 | Knowledge management & content experiences | 0 | 0% | Extended |

**Core-boundary note (the wording-artifact decision, stated once and
plainly):** whiteboarding, calendaring, and presence tag **zero**
claims in this group, and messaging and file sharing tag one each —
yet all five remain Core. The core is not re-derived per tier. Under
the Merge Rule, the L2 union is carried upward whole (Rules 1–2);
dropping a substrate function at the higher tier because High listings
are boundary prose would be a downgrade caused by a description-wording
artifact, and Group 2 already recorded the same artifact at Moderate
(calendaring 3 of 57, presence 2 of 57, both Core, because every
messaging and workspace sibling presupposes them). What changes at
High is the descriptions' vocabulary, not the substrate the siblings
presuppose.

**How this group differs from Group 2 (L2)** — preserved, not averaged
away: at High, "collaboration" predominantly means a *governed enclave
in which collaboration happens*, described by its boundary. Claim mass
shifts to platform-level families — APIs & interoperability 59% (L2:
54%), records & governance 29% (L2: 16%), encryption 24% (L2: 19%),
access control 29% (L2: 26%) — while feature-enumerating families
collapse (messaging 6% vs 19%, file sharing 6% vs 16%, meetings,
calendaring, presence, whiteboarding all 0%). The two richest sheets
are the Project Hosts GSS One hosting enclaves (AWS: 8 claims; Azure:
9), and the group also holds pure infrastructure (CyCloud for VMware
Cloud Foundation, the group's only IaaS) and pure identity (Okta
IDaaS Government High Cloud) under the Collaboration heading — the
marketplace's own categorization, kept as-is. The long tail (contact
center voice, e-signature, learning, knowledge experiences, domain
workflow engines) remains the record of how the siblings differ; the
per-fork spec sheets name which siblings claim each function.

## The Core — what the merged build implements (11 functions, at the High baseline)

The same 11 platform functions as Group 2 (the platform substrate
every sibling presupposes), carried up to the High baseline:

1. **Workspaces** — named shared workspaces with an owner, a member
   list, and provenance (who created it, when). Membership is the
   boundary every other core function enforces.
2. **Messaging & chat** — channels inside a workspace; messages with
   optional threading (a message may reply to another in the same
   channel); `@name` mentions of workspace members generate
   notifications.
3. **File sharing** — files shared into a workspace as versioned
   records: name, content type, size, SHA-256 digest, who shared it,
   when; re-sharing the same name creates the next version.
4. **Calendaring & scheduling** — workspace events with title, start
   and end (ISO-8601), location, and attendees; member attendees are
   notified of the invite.
5. **Presence** — a per-user availability status (`available`,
   `busy`, `dnd`, `offline`) with an optional note and an updated
   timestamp; a user sets their own presence (a platform admin may
   set anyone's).
6. **Whiteboards** — boards inside a workspace holding positioned
   text cards (text plus x/y position) that members can add and move.
7. **Search** — literal, case-insensitive substring search across a
   workspace's messages, file names, event titles, and board cards.
8. **Notifications** — a per-user queue fed by mentions, event
   invites, and file shares; entries can be listed and marked read.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` (as Group 2) plus **`auditor`**
    (audit review only), with the permission matrix enforced on
    every operation, layered with workspace membership, and
    unsuccessful-logon lockout at the service layer (uplifts, below).
11. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail with audit search/reduction, chain verification, and
    fail-closed write behavior (uplifts, below).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. All 17 parent forks sit at High, and the
  cross-tier parent (Group 2's build) sat at Moderate; the union
  baseline is therefore the High baseline, un-diluted (Merge Rule 1),
  inherited in full (Merge Rule 2). "Adjacent" remains deliberate
  wording, as in the crosswalk: L3 is not identical to FedRAMP High;
  it is the same assurance weight class.
- **Feature → control family mapping (carried from Group 2):**
  - Access control (platform roles + workspace membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; the service ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit information —
    append-only store, admin/auditor-only read).
  - Messaging / files / events / boards / search → **SI** (SI-10
    information input validation — malformed input is rejected, never
    partially applied) and **SC** (SC-8 transmission confidentiality —
    the server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated plainly,
    not claimed here).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3; 800-172 audit requirements) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently; the service layer swallowed all audit errors | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store records the audit entry *before* committing a mutation, so an operation whose audit write fails proceeds not at all — no object, no notification, no id consumed; the service propagates the error as HTTP 500 and never returns a stack trace |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter; an expired lock clears itself |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 2, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build; retention rides with the Extended records & governance function (5 siblings claim records/governance) |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `collab` under `src/`,
runnable and testable with `PYTHONPATH=src`. The contract is Group 2's,
unchanged except for the uplift deltas marked **[L3]**. Ids are
sequential per object type with fixed prefixes (`ws-`, `ch-`, `msg-`,
`file-`, `evt-`, `bd-`, `card-`, `ntf-`); a failed operation consumes
no id and changes nothing. All timestamps are UTC ISO-8601.

- `collab/errors.py` — `CollabError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (as Group 2), plus **[L3]**
  `AuditWriteError`: raised when an audit write fails; the operation
  being audited fails closed.
- `collab/access.py` — `User(name, role)`; roles
  `admin|member|viewer|auditor` **[L3]**; actions `read,
  create_workspace, post, share, schedule, board_edit,
  manage_members, audit_read, admin`. `PERMISSIONS`: admin ⊇ all
  nine; member = {read, create_workspace, post, share, schedule,
  board_edit}; viewer = {read}; **auditor = {audit_read}** **[L3]**;
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`.
- `collab/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry dict with keys `ts, actor, action,
  target, details` plus **[L3]** `seq, prev_hash, hash` (SHA-256 of
  the canonical JSON of `{seq, ts, actor, action, target, details,
  prev_hash}`); raises **[L3]** `AuditWriteError` and rolls back the
  in-memory append if the JSONL write fails. `.entries()` returns all
  entries. **[L3]** `.query(actor=None, action=None, target=None,
  since=None, until=None)` returns filtered entries (since/until are
  ISO strings compared against `ts`, inclusive); `.verify_chain()`
  returns `(ok, first_bad_index_or_None)`. Append-only; optional JSONL
  file; loaded entries participate in chain verification.
- `collab/store.py` — `CollabStore(audit=None)`, Group 2's methods,
  shapes, audit action names, and membership rule unchanged, with one
  **[L3]** structural delta: the store records the audit entry
  **before** committing each mutation (audit-before-commit, AU-5). If
  the audit write raises `AuditWriteError`, it propagates and the
  store is completely unchanged — no object stored, no notification
  created, no counter consumed, no field flipped. (Group 2 recorded
  after mutating; the visible success-path behavior — entries,
  ordering, return values — is identical.)
- `collab/service.py` — `make_server(host, port, store, audit, users,
  max_failures=3, lockout_seconds=300)` **[L3 kwargs]** →
  `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth
  via `X-User` / `X-Role` headers (the role must match the registry;
  unknown user or mismatched role → 401). **[L3]** consecutive auth
  failures are tracked per username; at `max_failures` the username
  locks for `lockout_seconds` (403, audited `auth:locked`); success
  resets; an expired lock clears itself. Endpoints as Group 2
  (`GET /health`, workspaces / members / channels / messages / files /
  events / boards / cards / search / presence / notifications),
  plus **[L3]** `GET /audit/verify` → `{ok, entries,
  first_bad_index}` (audit_read; `entries` counts the trail before
  this read's own `audit_read` entry is recorded) and `GET /audit`
  filter parameters `actor, action, target, since, until`. Denied
  attempts (401 and 403) are audited with the action name suffixed
  `:denied`; **[L3]** an `AuditWriteError` anywhere in the request
  path surfaces as HTTP 500 `{"error": "audit write failed"}`; no
  stack trace is ever returned.
- `collab/__main__.py` — `python -m collab serve --host --port
  [--audit-log PATH] [--certfile --keyfile] [--max-failed-logins N]
  [--lockout-seconds S]` **[L3 flags]** with demo users `alice=admin,
  bob=member, carol=viewer, dana=auditor` **[L3]** (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring naming
the core function / spec claim / control family it traces to. 239
tests: the 192 Group 2 tests (inherited; files minimally adapted for
the uplift — adaptations listed in `tests/README.md`) plus 47 new
tests covering the hash chain, fail-closed audit behavior, audit
query, logon lockout, and the auditor role. Two **negative controls**:

1. The membership mutant (carried from Group 2): a membership check
   that treats every actor as a workspace member; the canonical
   expectation is shown to reject it — a non-member's post must raise
   `PermissionDenied`, and the mutant is demonstrated to wave it
   through — proving the suite catches that defect class rather than
   merely passing.
2. **[L3]** Audit tamper: mutating a stored audit entry in place
   makes `verify_chain()` report failure at exactly that entry's
   index, and a naive always-`(True, None)` verifier is shown to
   accept the tampered log — proving the chain catches the tampering
   defect class rather than merely existing.

**Verification (mutation drills, recorded in `tests/README.md`):**
patching the real membership condition in `src/collab/store.py` to
wave non-members through made the suite fail (**239 ran, 14
failed**, spanning 8 test files); the file was restored SHA-256-
identical and the suite returned to green. Separately, patching
`_entry_hash` in `src/collab/audit.py` to a constant made the
audit-focused files fail (**28 ran, 4 failed** — the chain and
tamper-control tests; `test_audit.py`'s basic linkage assertions hold
even under a constant hash, recorded honestly there); restored
SHA-256-identical, full suite green. The coordinator additionally
re-ran the full suite independently and re-verified the spec
reconciliation from the raw inputs.

## Coverage statement (for this build)

- Specs: 17 / 17 forks spec'd (13 with at least one tagged claim; 49
  claims total).
- Core: 11 core functions implemented, at the High baseline, each
  with tracing tests; 6 tier uplifts implemented (hash-chained audit,
  chain-verification endpoint, fail-closed audit writes, audit
  query/reduction, logon lockout, auditor role).
- Extended: 9 functions specified and ranked, **not** implemented in
  this build: workflow/process automation engines (4 siblings), AI
  assistance and speech (5), records & governance beyond the
  versioning/audit seed (5), voice/telephony/contact center (2),
  task & project management beyond board cards (2), learning/
  training/mentoring (1), knowledge management (0), meetings media
  transport (0), e-signature (0).
- Baseline gaps named, not implied closed: MFA/authenticator
  management (IA-2(1)/(2), IA-5 — IdP layer), FIPS-validated crypto
  (SC-13), encryption at rest (SC-28), audit retention enforcement
  (AU-11), session lock/termination (AC-11/AC-12). Encryption is a
  platform note (TLS when a certificate is configured; at rest is a
  deployment-layer control).
