# Union Spec — Collaboration, CMMC L2 (DeadRamp Phase 2, Group 2)

The merged functional spec for the second-largest sibling group built so
far: **57 forks**, category **Collaboration**, CMMC tier **L2** (every
member is FedRAMP **Moderate** in `forks.json` — verified, so the group
is single-tier and the merge takes the group baseline in full, per
Merge Rule 2). The member list in `forks.json` was reconciled against
`MAP.md`'s "Collaboration — L2 (57)" section: **zero diffs**.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 57
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced by
the General Services Administration, last change 2026-10-22), product
records joined by FedRAMP ID. No live fetching was needed: all 57
descriptions were present in the cached dataset.

## How functions were counted

A fixed 21-function taxonomy for this category was matched against
each offering's own public description. A function is claimed for a
fork **only** when the description contains matching text; the
matching sentence is stored as the claim's evidence in the spec sheet.
51 of 57 offerings carry at least one tagged claim (222 claims total);
6 descriptions carry none: ReadyOp, Dejero Control and Concentrator,
and Visionlink COS2 are one-paragraph delivery-model prose; Figma for
Government's description only enumerates its authorization boundary;
TMS Gov Cloud Suite and Thomson Reuters Risk & Fraud describe
asset/risk tooling in terms outside this taxonomy. Their full text is
still in the spec sheets — nothing is hidden, and no function was
invented for them. Counts below are therefore a **floor**, not a
ceiling, on what these products do.

Three wording-artifact corrections were applied to the matcher and are
recorded here: "diagramming" is required for the whiteboard family
(the bare stem also matched "diagrammatic" in authorization-boundary
boilerplate); "presence" does not match when preceded by "market"
("market presence" is not a presence feature); the calendaring pattern
also accepts "scheduling solution / scheduler" phrasing (a dedicated
scheduling product whose description never says the word "calendar").

## Function ranking — all 57 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | APIs, integrations & interoperability | 31 | 54% | **Core** (the service is API-first) |
| 2 | Workflow & process automation | 25 | 44% | Extended — the siblings' claims are domain process engines (procurement approvals, contract lifecycles, ITSM, records routing) that run *on top of* a collaboration substrate; this build is that substrate (see below) |
| 3 | AI assistance, speech & analytics | 21 | 37% | Extended (search in Core is literal substring matching, not semantic/AI search — stated plainly) |
| 4 | Access control & authentication | 15 | 26% | **Core** (L2 baseline hooks) |
| 5 | Messaging & chat | 11 | 19% | **Core** |
| 6 | Audit logging & trails | 11 | 19% | **Core** (L2 baseline hooks) |
| 7 | Encryption | 11 | 19% | Platform note (TLS supported; see baseline section) |
| 8 | Learning, training & mentoring | 11 | 19% | Extended |
| 9 | Task, project & work management | 10 | 18% | Extended (board cards in Core are the seed — one sibling lists "task cards" as a workspace feature; full task/project management is not claimed) |
| 10 | Shared workspaces & team collaboration | 10 | 18% | **Core** |
| 11 | Voice, telephony & contact center | 9 | 16% | Extended (real-time media transport; see the meetings note below) |
| 12 | File sharing, storage & content management | 9 | 16% | **Core** |
| 13 | Records, governance & compliance management | 9 | 16% | Extended (file versioning and the audit trail in Core are the seed) |
| 14 | Notifications, alerts & emergency communications | 7 | 12% | **Core** (the in-platform notification queue: mentions, invites, shares) |
| 15 | Search & discovery | 7 | 12% | **Core** (literal substring search across workspace objects) |
| 16 | Knowledge management & content experiences | 7 | 12% | Extended |
| 17 | Whiteboarding, visual collaboration & co-authoring | 6 | 11% | **Core** (boards of positioned text cards; no raster canvas — stated plainly) |
| 18 | Meetings, video & web conferencing | 5 | 9% | Extended (media transport — a standard-library text build carries no audio/video; the coordination surface around meetings — calendaring, channels, presence — is Core) |
| 19 | Calendaring & scheduling | 3 | 5% | **Core** (low tag count is a description-wording artifact: siblings say "sessions", "registration", "reservation" where this build says calendar; every meeting and workspace sibling presupposes scheduling) |
| 20 | Electronic & digital signatures | 2 | 4% | Extended |
| 21 | Presence & availability | 2 | 4% | **Core** (low tag count is likewise a wording artifact: presence is a named unified-communications feature in the siblings that do list features, and every messaging sibling presupposes it) |

**Differences are preserved, not averaged away**: the long tail above
(contact-center voice, e-signature, learning management, records
retention, knowledge experiences, domain workflow engines) is the
record of how the siblings differ. Each Extended function names the
claim family and its sibling count; the per-fork spec sheets name
which siblings claim it.

## The Core — what the merged build implements (11 functions)

One coherent, standards-based collaboration service that every
sibling's platform presupposes, built clean-room from this spec:

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
5. **Presence** — a per-user availability status (`available`, `busy`,
   `dnd`, `offline`) with an optional note and an updated timestamp;
   a user sets their own presence (a platform admin may set anyone's).
6. **Whiteboards** — boards inside a workspace holding positioned
   text cards (text plus x/y position) that members can add and move.
7. **Search** — literal, case-insensitive substring search across a
   workspace's messages, file names, event titles, and board cards.
8. **Notifications** — a per-user queue fed by mentions, event
   invites, and file shares; entries can be listed and marked read.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced on
    every operation, layered with workspace membership (non-members
    cannot read or write a workspace's content; the platform `admin`
    role can).
11. **Audit log** — an append-only audit trail: every workspace,
    membership, channel, message, file, event, presence, board, and
    notification mutation, every search, and every denied attempt is
    recorded with actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110 practices
  of NIST SP 800-171 Rev. 2 that define CMMC L2. All 57 parent forks
  sit at Moderate, so the union baseline is the Moderate baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + workspace membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; the service ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit information —
    append-only store, admin-only read).
  - Messaging / files / events / boards / search → **SI** (SI-10
    information input validation — malformed input is rejected, never
    partially applied) and **SC** (SC-8 transmission confidentiality —
    the server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated plainly,
    not claimed here).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `collab` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`ws-`, `ch-`, `msg-`, `file-`,
`evt-`, `bd-`, `card-`, `ntf-`); a failed operation consumes no id and
changes nothing. All timestamps are UTC ISO-8601.

- `collab/errors.py` — `CollabError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `CollabError`).
- `collab/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `read, create_workspace, post,
  share, schedule, board_edit, manage_members, audit_read, admin`.
  `PERMISSIONS`: admin ⊇ all nine; member = {read, create_workspace,
  post, share, schedule, board_edit}; viewer = {read}.
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`.
- `collab/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL
  file persistence; reloads an existing file on construction.
- `collab/store.py` — `CollabStore(audit=None)`. The store records
  every successful mutation and every search to its audit log (when
  one is attached) with the action names used below; the HTTP layer
  records denials and `audit_read` only, never duplicating store
  records. Membership rule: for every workspace-scoped operation the
  actor must be a workspace member or hold the platform `admin` role,
  else `PermissionDenied`; the role permission for the operation is
  also required (`require`). Methods:
  - `create_workspace(name, actor)` → `{id, name, owner, members,
    created_by, created_utc}`; the creator is owner and first member.
    Audits `workspace_create`.
  - `list_workspaces(actor)` → workspace dicts the actor may see
    (member of, or platform admin). `get_workspace(workspace_id,
    actor)` → one dict (`NotFoundError`, or `PermissionDenied` for a
    non-member).
  - `add_member(workspace_id, username, actor)` → updated workspace
    dict. Only the workspace owner or a platform admin may add;
    adding an existing member raises `ValidationError`. Audits
    `member_add`.
  - `create_channel(workspace_id, name, actor)` (action `post`) →
    `{id, workspace_id, name, created_by, created_utc}`;
    `list_channels(workspace_id, actor)`. Audits `channel_create`.
  - `post_message(workspace_id, channel_id, text, actor,
    parent_id=None)` (action `post`) → `{id, workspace_id,
    channel_id, author, text, parent_id, created_utc}`. `parent_id`,
    when given, must name a message in the same channel, else
    `ValidationError`. Each `@name` token naming a workspace member
    other than the author creates a notification for that member
    (kind `mention`, `ref_id` = the message id). Audits
    `message_post`. `list_messages(workspace_id, channel_id, actor,
    limit=None)` → chronological message dicts; `get_message(
    workspace_id, message_id, actor)`.
  - `share_file(workspace_id, name, content, actor,
    content_type="text/plain")` (action `share`) → `{id, workspace_id,
    name, version, size_bytes, sha256, content_type, shared_by,
    created_utc}`; `content` is a `str` stored as UTF-8; `version` is
    1 for the first share of that name in the workspace and increments
    per re-share. Every other workspace member gets a notification
    (kind `file_share`, `ref_id` = the file id). Audits `file_share`.
    `list_files(workspace_id, actor)`; `get_file(workspace_id,
    file_id, actor)` → the file dict plus a `content` key.
  - `create_event(workspace_id, title, start, end, attendees, actor,
    location="")` (action `schedule`) → `{id, workspace_id, title,
    start, end, location, attendees, created_by, created_utc}`;
    `start`/`end` must parse as ISO-8601 datetimes and `end` must be
    after `start`, else `ValidationError`. Attendees who are
    workspace members (other than the creator) get a notification
    (kind `event_invite`, `ref_id` = the event id). Audits
    `event_create`. `list_events(workspace_id, actor)`.
  - `set_presence(username, status, actor, note="")` → `{user,
    status, note, updated_utc}`; `status` must be one of `available`,
    `busy`, `dnd`, `offline`, else `ValidationError`; the actor must
    be `username` themself or a platform admin, else
    `PermissionDenied`. Audits `presence_set`.
    `get_presence(username)` → the presence dict, or `NotFoundError`
    if never set.
  - `create_board(workspace_id, name, actor)` (action `board_edit`)
    → `{id, workspace_id, name, created_by, created_utc}`;
    `list_boards(workspace_id, actor)`. Audits `board_create`.
    `add_card(workspace_id, board_id, text, x, y, actor)` (action
    `board_edit`) → `{id, board_id, workspace_id, text, x, y,
    created_by, created_utc}`; `x`/`y` must be numbers, else
    `ValidationError`. Audits `card_add`.
    `move_card(workspace_id, board_id, card_id, x, y, actor)` →
    updated card dict. Audits `card_move`. `list_cards(workspace_id,
    board_id, actor)`.
  - `search(workspace_id, query_text, actor)` (action `read`) →
    `{messages, files, events, cards}`: case-insensitive substring
    matches over message text, file names, event titles, and card
    text, scoped to the one workspace (never across workspaces).
    Audits `search`.
  - `notifications_for(username)` → that user's notification dicts,
    oldest first: `{id, user, kind, workspace_id, ref_id,
    created_utc, read}`. `mark_read(notification_id, actor)` → the
    updated dict with `read: True`; only the notification's user or a
    platform admin may mark it, else `PermissionDenied`. Audits
    `notification_read`.
- `collab/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match the
  registry; unknown user or mismatched role → 401). Errors are JSON
  `{error}` with 400/401/403/404 as applicable; denied attempts (401
  and 403) are audited with the action name suffixed `:denied`, and
  no stack trace is ever returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /workspaces` (read); `POST /workspaces` `{name}`
    (create_workspace) → 201
  - `GET /workspaces/{id}` (read)
  - `POST /workspaces/{id}/members` `{username}` (post at the HTTP
    layer; the store enforces owner-or-admin) → workspace dict
  - `GET /workspaces/{id}/channels` (read);
    `POST /workspaces/{id}/channels` `{name}` (post) → 201
  - `GET /workspaces/{id}/channels/{cid}/messages` (read);
    `POST /workspaces/{id}/channels/{cid}/messages` `{text,
    parent_id?}` (post) → 201
  - `GET /workspaces/{id}/files` (read);
    `POST /workspaces/{id}/files` `{name, content, content_type?}`
    (share) → 201; `GET /workspaces/{id}/files/{fid}` (read)
  - `GET /workspaces/{id}/events` (read);
    `POST /workspaces/{id}/events` `{title, start, end, attendees?,
    location?}` (schedule) → 201
  - `GET /workspaces/{id}/boards` (read);
    `POST /workspaces/{id}/boards` `{name}` (board_edit) → 201;
    `GET /workspaces/{id}/boards/{bid}/cards` (read);
    `POST /workspaces/{id}/boards/{bid}/cards` `{text, x, y}`
    (board_edit) → 201;
    `POST /workspaces/{id}/boards/{bid}/cards/{card_id}/move`
    `{x, y}` (board_edit)
  - `GET /workspaces/{id}/search?q=` (read)
  - `GET /presence/{user}` (read); `PUT /presence/{user}` `{status,
    note?}` (any authenticated user; the store enforces self-or-admin)
  - `GET /notifications` (read) → `{"notifications": [...]}` for the
    caller; `POST /notifications/{id}/read` (read; the store enforces
    owner-or-admin)
  - `GET /audit` (audit_read) → `{"entries": [...]}`
- `collab/__main__.py` — `python -m collab serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring naming
the core function / spec claim it traces to, and include a **negative
control**: a mutant membership check (one that treats every actor as a
workspace member) whose behavior the canonical expectation is shown to
reject — a non-member's post must raise `PermissionDenied`, and the
mutant is demonstrated to wave it through — proving the suite catches
that defect class rather than merely passing. The negative control
must additionally be **mutation-verified**: patching the real
membership check in `src/` with the mutant must make the suite fail;
the run and its result are recorded in `tests/README.md`.

## Coverage statement (for this build)

- Specs: 57 / 57 forks spec'd.
- Core: 11 core functions implemented, each with tracing tests.
- Extended: 9 functions specified and ranked, **not** implemented in
  this build (workflow/process automation engines, AI assistance and
  speech, learning/training/mentoring, task & project management
  beyond board cards, voice/telephony/contact center, records &
  governance beyond the versioning/audit seed, knowledge management,
  meetings media transport, e-signature); encryption is a platform
  note (TLS when a certificate is configured; at rest is a
  deployment-layer control).
