# Collaboration L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 6)

This is the merged, clean-room implementation of the **Collaboration
L3-adjacent** sibling group: **17 forks** from the FedRAMP Marketplace
that share the same function (Collaboration) and the same trust tier
(CMMC L3-adjacent, equivalent to FedRAMP **High**), built as one
open-source service per the group's union spec,
[`UNION-SPEC.md`](UNION-SPEC.md).

It is a **cross-tier merge** under the project's Merge Rule: the parent
is the shipped **Collaboration L2** merged build
([`../collaboration-l2/`](../collaboration-l2/)), whose 11-function
core this build reuses (our own Apache-2.0 code, stated explicitly in
the union spec) and carries up to the High baseline un-diluted. Where
the High baseline demanded more than the L2 core had, the build was
uplifted; where the demand belongs to a layer this build cannot
honestly supply, the gap is named, not papered over (see the honesty
section). Original code throughout: no vendor code, assets, or
branding from any of the 17 sibling offerings. Python 3, **standard
library only**, no external dependencies.

## The 11 core functions (inherited from the L2 merge, at the High baseline)

1. **Workspaces** — named shared workspaces with an owner, a member
   list, and provenance (who created it, when). Membership is the
   boundary every other core function enforces.
2. **Messaging & chat** — channels inside a workspace; messages with
   optional threading (a message may reply to another in the same
   channel); `@name` mentions of workspace members generate
   notifications.
3. **File sharing** — files shared into a workspace as versioned
   records: name, content type, size, SHA-256 digest of the UTF-8
   content, who shared it, when; re-sharing the same name creates the
   next version, and every other member is notified.
4. **Calendaring & scheduling** — workspace events with title, start
   and end (ISO-8601, end after start), location, and attendees;
   member attendees are notified of the invite.
5. **Presence** — a per-user availability status (`available`, `busy`,
   `dnd`, `offline`) with an optional note and an updated timestamp;
   a user sets their own presence (a platform admin may set anyone's).
6. **Whiteboards** — boards inside a workspace holding positioned
   text cards (text plus numeric x/y position) that members can add
   and move. Boards of positioned text cards; no raster canvas.
7. **Search** — literal, case-insensitive substring search across a
   workspace's messages, file names, event titles, and board cards,
   scoped to the one workspace (never across workspaces).
8. **Notifications** — a per-user queue fed by mentions, event
   invites, and file shares; entries can be listed and marked read
   (by their owner, or a platform admin).
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` (as L2) plus **`auditor`**
    (audit review only — the AC-5 separation-of-duties slice), with
    the permission matrix enforced on every operation, layered with
    workspace membership, and **unsuccessful-logon lockout** at the
    service layer (AC-7, uplift).
11. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail (uplift): every entry carries a sequence number and a
    SHA-256 link to its predecessor, the chain can be verified end to
    end, audit writes **fail closed** (an operation whose audit write
    fails does not proceed and changes nothing), and the trail is
    searchable by actor, action, target, and time window.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `ws-`, `ch-`, `msg-`, `file-`,
`evt-`, `bd-`, `card-`, `ntf-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m collab serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`), and the lockout controls `--max-failed-logins N` (default 3)
and `--lockout-seconds S` (default 300). A startup line is printed
once the server is listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, create_workspace, post, share, schedule, board_edit, manage_members, audit_read, admin |
| `bob`   | member  | read, create_workspace, post, share, schedule, board_edit |
| `carol` | viewer  | read                                         |
| `dana`  | auditor | audit_read                                   |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

**Lockout (AC-7):** consecutive authentication failures are counted
per username. At the configured maximum (default 3) the username
locks for the configured window (default 300 seconds): attempts
during the lock — even with the correct role — are answered 403 and
audited as `auth:locked`. A successful authentication resets the
counter; an expired lock clears itself.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/workspaces` | read | List workspaces visible to the caller → `{"workspaces": [...]}` |
| POST | `/workspaces` | create_workspace | Body `{"name"}` → 201 workspace dict |
| GET | `/workspaces/{id}` | read | One workspace dict |
| POST | `/workspaces/{id}/members` | post (store enforces owner-or-admin) | Body `{"username"}` → workspace dict |
| GET | `/workspaces/{id}/channels` | read | List channels → `{"channels": [...]}` |
| POST | `/workspaces/{id}/channels` | post | Body `{"name"}` → 201 channel dict |
| GET | `/workspaces/{id}/channels/{cid}/messages` | read | List messages (optional `?limit=`) → `{"messages": [...]}` |
| POST | `/workspaces/{id}/channels/{cid}/messages` | post | Body `{"text", "parent_id"?}` → 201 message dict |
| GET | `/workspaces/{id}/files` | read | List files → `{"files": [...]}` |
| POST | `/workspaces/{id}/files` | share | Body `{"name", "content", "content_type"?}` → 201 file dict |
| GET | `/workspaces/{id}/files/{fid}` | read | One file dict, including `content` |
| GET | `/workspaces/{id}/events` | read | List events → `{"events": [...]}` |
| POST | `/workspaces/{id}/events` | schedule | Body `{"title", "start", "end", "attendees"?, "location"?}` → 201 event dict |
| GET | `/workspaces/{id}/boards` | read | List boards → `{"boards": [...]}` |
| POST | `/workspaces/{id}/boards` | board_edit | Body `{"name"}` → 201 board dict |
| GET | `/workspaces/{id}/boards/{bid}/cards` | read | List cards → `{"cards": [...]}` |
| POST | `/workspaces/{id}/boards/{bid}/cards` | board_edit | Body `{"text", "x", "y"}` → 201 card dict |
| POST | `/workspaces/{id}/boards/{bid}/cards/{card_id}/move` | board_edit | Body `{"x", "y"}` → updated card dict |
| GET | `/workspaces/{id}/search?q=` | read | `{messages, files, events, cards}` substring matches in that workspace |
| GET | `/presence/{user}` | read | One presence dict |
| PUT | `/presence/{user}` | any authenticated user (store enforces self-or-admin) | Body `{"status", "note"?}` → presence dict |
| GET | `/notifications` | read | `{"notifications": [...]}` for the caller |
| POST | `/notifications/{id}/read` | read (store enforces owner-or-admin) | → updated notification dict |
| GET | `/audit` | audit_read | `{"entries": [...]}`; optional filters `?actor=&action=&target=&since=&until=` |
| GET | `/audit/verify` | audit_read | `{"ok": bool, "entries": n, "first_bad_index": i|null}` — hash-chain verification report |

Workspace dicts are `{id, name, owner, members, created_by,
created_utc}` with sequential ids `ws-1`, `ws-2`, …; the other object
types follow the same pattern with their own prefixes. Audit entries
are `{ts, actor, action, target, details, seq, prev_hash, hash}` (see
`UNION-SPEC.md` for every dict shape and the full contract).

## Remainder addition (1 fork)

The remainder census added 1 previously uncategorized fork to
this group: **Microsoft 365 Government Community Cloud &
Supporting Services** (`MSO365MTA`, FedRAMP High, In Process).
Spec'd under the group's existing 21-family taxonomy applied
verbatim, it carries **1 claim** (messaging & chat — its listing's
first sentence, which is also the census citation) for group
totals of **18 forks, 50 claims, 14 of 18 claiming**. The core is
unchanged (`src/` byte-identical); tests 239 → 251. One new gap
is named (collaborative continuous monitoring service). Full
record: [`ADDENDUM.md`](ADDENDUM.md).

## How to run tests

Tests live in `tests/` (standard library `unittest`), maintained
against the same contract in `UNION-SPEC.md`, including two negative
controls (the membership mutant carried from L2, and an audit-tamper
control), each mutation-verified with the runs recorded in
`tests/README.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 **High**
baseline cross-walked to the CMMC L3 basis (NIST SP 800-171 Rev. 2
plus selected NIST SP 800-172 enhanced requirements):

- **AC / IA** — access control (platform roles + workspace
  membership): AC-2 (account management), AC-3 (access enforcement),
  AC-5 (separation of duties — the `auditor` role holds `audit_read`
  and nothing else), AC-6 (least privilege), AC-7 (unsuccessful logon
  attempts — the service lockout); IA-2 (identification &
  authentication — identity is supplied by the embedding organization
  via user/role headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-5 (response to audit processing failure — fail
  closed), AU-6 (audit review), AU-7 (audit reduction & search),
  AU-9 (protection of audit information — append-only store,
  hash-chained, audit-read restricted to the `audit_read`
  permission).
- **SI / SC** — messaging / files / events / boards / search: SI-10
  (information input validation — malformed input is rejected, never
  partially applied); SC-8 (transmission confidentiality — the server
  runs over TLS when a certificate is configured; encryption at rest
  is a deployment-layer control, stated plainly and not claimed
  here).

## Honesty: what is NOT in this build

The union spec ranks 21 functions across the 17 siblings; 11 are
implemented here (the core inherited from the L2 merge). The
following **Extended functions are specified and ranked in
`UNION-SPEC.md` but are NOT implemented** in this build:

- Workflow & process automation engines (domain process engines that
  run on top of a collaboration substrate — this build is that
  substrate)
- AI assistance, speech & analytics (search in this build is literal
  substring matching, not semantic/AI search)
- Learning, training & mentoring
- Task & project management beyond board cards (board cards are the
  seed, not a full task/project system)
- Voice, telephony & contact center (real-time media transport)
- Records & governance beyond the versioning/audit seed (file
  versioning and the audit trail in this build are that seed)
- Knowledge management & content experiences
- Meetings / video media transport (a standard-library text build
  carries no audio/video; the coordination surface around meetings —
  calendaring, channels, presence — is in the core)
- Electronic & digital signatures

**Baseline gaps at High, named, not implied closed** (the parent
registers these in the repo's `GAPS.md` final-batch registry):

- MFA / authenticator management (IA-2(1)/(2), IA-5) — an
  identity-provider property; this build ships hooks, not an IdP,
  and the embedding organization must supply MFA-grade
  authentication.
- FIPS-validated cryptography (SC-13) — Python's standard library is
  not a FIPS-validated cryptographic module; validated crypto is a
  platform/deployment property and is **not claimed** here.
- Encryption at rest (SC-28) — a deployment-layer control.
- Audit retention enforcement (AU-11) — no retention-period
  enforcement in this build.
- Session lock / termination (AC-11/AC-12) — the service
  authenticates per request from headers and holds no session state
  to lock or terminate; session management belongs to the embedding
  layer.

Further, plainly:

- The demo identities (`alice`, `bob`, `carol`, `dana`) are **hooks,
  not an identity provider**. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which baseline families the build's features answer
  to; nothing more.
