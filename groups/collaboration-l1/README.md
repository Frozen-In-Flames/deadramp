# Collaboration L1 — merged build (Operation DeadRamp, Phase 2, Group 10)

This is the merged, clean-room implementation of the **Collaboration
L1** sibling group: **10 forks** from the FedRAMP Marketplace that
share the same function (Collaboration) and the same trust tier
(CMMC L1), built as one open-source service per the group's union
spec, [`UNION-SPEC.md`](UNION-SPEC.md).

This is one of the map's lightest-tier groups, and one of the few
that mixes two FedRAMP impact levels: **2 forks are FedRAMP Low**
(A-SCEND; Vyond for Government) and **8 are LI-SaaS** — FedRAMP's
tailored subset of the Low baseline for SaaS. Each fork's actual
impact level is recorded in its spec sheet
([`specs/specs.json`](specs/specs.json)). The group's union baseline
is the Low baseline, taken in full.

It was written from the contract in the union spec: original code,
no vendor code, assets, or branding from any of the 10 sibling
offerings. Python 3, **standard library only**, no external
dependencies.

**Reuse, stated plainly:** the implementation and test suite are the
shipped Group 2 (Collaboration L2) build's code, reused in full —
this project's own Apache-2.0 code. A per-file hash comparison is
recorded in `scratch/reuse-note.md`: all 7 `src/` modules and 14 of
16 test files are byte-identical to Group 2's; the two differing
files are documentation wording only, and the copied code was
verified to contain no tier or baseline language. **The baseline
claim is not reused.** Everything Group 2 says about Moderate /
NIST SP 800-171 stays in Group 2. This group's claims are the Low
baseline's and FAR 52.204-21's only, as written in `UNION-SPEC.md`.

## The 11 core functions

1. **Workspaces** — named shared workspaces with an owner, a member
   list, and provenance (who created it, when). Membership is the
   boundary every other core function enforces.
2. **Messaging & chat** — channels inside a workspace; messages with
   optional threading (a message may reply to another in the same
   channel); `@name` mentions of workspace members generate
   notifications.
3. **File sharing** — files shared into a workspace as versioned
   records: name, content type, size, SHA-256 digest of the UTF-8
   content, who shared it, when; re-sharing the same name creates
   the next version, and every other member is notified.
4. **Calendaring & scheduling** — workspace events with title, start
   and end (ISO-8601, end after start), location, and attendees;
   member attendees are notified of the invite.
5. **Presence** — a per-user availability status (`available`,
   `busy`, `dnd`, `offline`) with an optional note and an updated
   timestamp; a user sets their own presence (a platform admin may
   set anyone's).
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
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with workspace membership
    (non-members cannot read or write a workspace's content; the
    platform `admin` role can).
11. **Audit log** — an append-only audit trail: every workspace,
    membership, channel, message, file, event, presence, board, and
    notification mutation, every search, and every denied attempt is
    recorded with actor, action, target, and UTC timestamp. Optional
    JSONL file persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `ws-`, `ch-`, `msg-`, `file-`,
`evt-`, `bd-`, `card-`, `ntf-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m collab serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, create_workspace, post, share, schedule, board_edit, manage_members, audit_read, admin |
| `bob`   | member  | read, create_workspace, post, share, schedule, board_edit |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

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
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Workspace dicts are `{id, name, owner, members, created_by,
created_utc}` with sequential ids `ws-1`, `ws-2`, …; the other object
types follow the same pattern with their own prefixes (see
`UNION-SPEC.md` for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

192 tests. `tests/README.md` carries the coverage map, the negative
control, and the mutation-verification record for this tree.

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 **Low**
baseline (the union of this group's Low and LI-SaaS parents)
cross-walked to the FAR 52.204-21 practices that define CMMC L1:

- **AC / IA** — access control (platform roles + workspace
  membership): AC-2 (account management), AC-3 (access enforcement);
  FAR 52.204-21's practices on limiting system access to authorized
  users and authorized transactions. IA-2 (identification &
  authentication — identity is supplied by the embedding
  organization via user/role headers; this service ships hooks, not
  an IdP); FAR's identify-and-authenticate practices.
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records) — **on the FedRAMP Low side of the crosswalk only.** FAR
  52.204-21 contains no audit practice, so no audit claim is made on
  the CMMC side, and Group 2's Moderate-level audit citations (AU-6,
  AU-9) are not imported here.
- **SI / SC** — messaging / files / events / boards / search: SI-10
  (information input validation — malformed input is rejected, never
  partially applied); SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here).

Nothing from the Moderate/High apparatus of the sibling groups
(hash-chained audit, lockout, auditor role, 800-172 enhancements) is
claimed at this tier.

## Honesty: what is NOT in this build

The union spec ranks 21 functions across the 10 siblings; 11 are
implemented here. The following **Extended functions are specified
and ranked in `UNION-SPEC.md` but are NOT implemented** in this
build:

- AI assistance, speech & analytics (the top tagged family in this
  group — 4 of 10 siblings — and entirely the siblings' own product
  AI; search in this build is literal substring matching, not
  semantic/AI search)
- Workflow & process automation engines (domain process engines
  that run on top of a collaboration substrate — this build is that
  substrate)
- Learning, training & mentoring
- Knowledge management & content experiences
- Voice, telephony & contact center (real-time media transport)
- Task & project management beyond board cards (board cards are
  the seed, not a full task/project system)
- Records & governance beyond the versioning/audit seed (file
  versioning and the audit trail in this build are that seed)
- Meetings / video media transport (a standard-library text build
  carries no audio/video; the coordination surface around meetings
  — calendaring, channels, presence — is in the core)
- Electronic & digital signatures

Also plainly:

- **This group's spec counts are a low floor.** Only 6 of the 10
  descriptions tag any function claim (15 claims total), and 4 tag
  none (Overleaf, Vbrick, both Vyond records) — their descriptions
  are product-level prose in vocabulary the category taxonomy does
  not cover. The full descriptions are in `specs/specs.json`;
  nothing was invented to fill the gap, and the taxonomy was not
  re-tuned for this group (see the core-boundary note in
  `UNION-SPEC.md`).
- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly, and not
  claimed here. No sibling in this group claims an encryption
  function.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not
  an identity provider**. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control
  mapping above states which baseline families the build's features
  answer to; nothing more.
