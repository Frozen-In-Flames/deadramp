# Communication L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 14)

This is the merged, clean-room implementation of the
**Communication L3-adjacent** sibling group: **6 forks / vendor
platforms** from the FedRAMP Marketplace that share the same
function (Communication) and the same trust tier (CMMC
L3-adjacent, equivalent to FedRAMP High), built as one open-source
service from the group's union contract (see
[`UNION-SPEC.md`](UNION-SPEC.md)).

The group: Akamai Cloud (Akamai) · Artera Harmony Federal Edition
(Artera) · Enterprise Cloud Fax Government (ECFax) (Consensus Cloud
Solutions) · ETHERFAX GovCloud (ETHERFAX) · Hypori Government Cloud
(Hypori, Inc.) · Motorola Solutions Federal Cloud (MSFC) (Motorola
Solutions).

It is a **cross-tier merge**: the Group 11 Communication L2 merged
build, carried up whole under the Merge Rule (union of baselines,
never dilution) and uplifted to the High baseline. It was written
from the union contract only: original code, no vendor code,
assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 12 core functions

1. **Directory** — contacts (`ct-`) with per-kind addresses
   ({email, sms, voice, push}) and groups (`grp-`) of contacts.
2. **Channels** — channel configurations (`ch-`) per kind, with an
   enabled/disabled flag; channel writes are admin-only.
3. **Templates** — named templates (`tpl-`) whose subject/body may
   contain `{placeholder}`s, rendered with caller-supplied
   variables (missing variable is a validation error; extras are
   ignored).
4. **Message composition** — messages (`msg-`) from a template or a
   literal subject/body, addressed to the order-stable
   deduplicated union of individual contacts and group members.
5. **Per-recipient delivery records** — one delivery (`dlv-`) per
   recipient × reachable channel kind, with a status lifecycle
   (`queued` → `delivered`/`failed` → `acknowledged`), attempts,
   receipt, failure reason, and ack timestamp. Recipients reachable
   on no selected kind are listed in the message's
   `skipped_recipients`; a message with zero deliveries is rejected
   and consumes no ids.
6. **Dispatch with receipts** — due deliveries are dispatched
   through the reference transport (see Honesty): delivered with a
   labelled receipt when an enabled channel of the kind exists,
   otherwise failed with `failure_reason='no_enabled_channel'`.
7. **Scheduling** — a message may carry an ISO-8601 `send_at`;
   `dispatch_due` skips not-yet-due messages (an explicit `now` may
   be supplied as an ISO string or a datetime), and
   `dispatch_message` on a future message is a validation error.
8. **Acknowledgement tracking** — `acknowledge` a delivered
   delivery on a `require_ack` message; `ack_status` reports
   total, acknowledged count, and pending contact ids per message.
9. **Immutable records + search** — message/delivery records are
   the record of what was composed and what happened to it; search
   is a literal, case-insensitive substring search over contacts
   (name + address values), messages (subject + body), and
   deliveries (address).
10. **REST API** — every function above is exposed over a JSON REST
    API, so the service composes with anything that speaks HTTP.
11. **RBAC** — platform roles `admin`, `operator`, `viewer`, plus
    `auditor` (High uplift), with a permission matrix enforced on
    every operation (see below).
12. **Append-only, hash-chained audit log** — every contact, group,
    channel, template, message, dispatch, and acknowledgement
    mutation, every search, and every denied attempt is recorded
    with actor, action, target, and UTC timestamp. Each entry is
    hash-chained to its predecessor (tamper-evident), audit writes
    fail closed, and the trail supports filtered query and chain
    verification. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `ct-`, `grp-`,
`ch-`, `tpl-`, `msg-`, `dlv-`. Permission is checked before any
state change or id allocation.

## High-baseline uplifts (what changed from the L2 build)

- **Hash-chained, tamper-evident audit (AU-9, AU-3).** Every audit
  entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its
  canonical JSON; `GET /audit/verify` reports whether the chain is
  intact and localizes the first bad entry.
- **Fail-closed audit writes (AU-5).** If an audit write fails, the
  operation being audited does not proceed at all — no object, no
  id consumed — and the service answers HTTP 500
  `{"error": "audit write failed"}`.
- **Audit query / reduction (AU-7).** `GET /audit` accepts
  `actor`, `action`, `target`, `since`, and `until` filter
  parameters.
- **Unsuccessful-logon lockout (AC-7).** Consecutive authentication
  failures are tracked per username; at the threshold (default 3)
  the username locks (default 300s) and further attempts — even
  with the correct role — are answered 403 and audited as
  `auth:locked`.
- **Auditor role (AC-5).** A fourth role, `auditor`, holds
  `audit_read` and nothing else: audit review is a duty separable
  from administration.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m comm serve --host 127.0.0.1 --port 8790
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`), and `--max-failed-logins N` / `--lockout-seconds S`
for the AC-7 lockout. A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from comm.access import User
from comm.audit import AuditLog
from comm.store import CommStore

audit = AuditLog()
store = CommStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "operator")
contact = store.create_contact("Dana", {"email": "dana@example.com"}, bob)
store.create_channel("email", "primary", admin)
msg = store.compose_message(bob, subject="Hi", body="Hello",
                            contact_ids=[contact["id"]],
                            channel_kinds=["email"])
print(store.dispatch_due(bob))  # {'dispatched': 1, 'delivered': 1, 'failed': 0}
print(audit.verify_chain())     # (True, None)
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all reads + all writes, plus `channel_write`, `audit_read` |
| `bob`   | operator | all reads + `contact_write`, `group_write`, `template_write`, `message_compose`, `dispatch`, `ack_record` |
| `carol` | viewer   | reads only: `contact_read`, `channel_read`, `template_read`, `records_read` |
| `dana`  | auditor  | `audit_read` only (AC-5 separation of duties) |

Read actions: `contact_read`, `channel_read`, `template_read`,
`records_read`. Write actions: `contact_write`, `group_write`,
`template_write`, `message_compose`, `dispatch`, `ack_record`
(operator + admin); `channel_write` (admin only); `audit_read`
(admin + auditor). Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a
plain string carries identity but no role, so the service layer —
which knows the registry and always passes `User` objects — is
responsible for enforcement in that case (the house convention).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/contacts` | contact_read | `{"contacts": [...]}` |
| POST | `/contacts` | contact_write | Body `{"name", "addresses"}` → 201 contact |
| GET | `/contacts/{id}` | contact_read | One contact |
| GET | `/groups` | contact_read | `{"groups": [...]}` |
| POST | `/groups` | group_write | Body `{"name"}` → 201 group |
| GET | `/groups/{id}/members` | contact_read | `{"members": [contact, ...]}` |
| POST | `/groups/{id}/members` | group_write | Body `{"contact_id"}` → 201 group |
| GET | `/channels` | channel_read | `{"channels": [...]}` |
| POST | `/channels` | channel_write | Body `{"kind", "name", "enabled"?}` → 201 channel |
| POST | `/channels/{id}/enabled` | channel_write | Body `{"enabled": bool}` → channel |
| GET | `/templates` | template_read | `{"templates": [...]}` |
| POST | `/templates` | template_write | Body `{"name", "subject", "body"}` → 201 template |
| GET | `/templates/{id}` | template_read | One template |
| GET | `/messages` | records_read | `{"messages": [...]}` |
| POST | `/messages` | message_compose | Body `{"subject"?, "body"?, "template_id"?, "variables"?, "contact_ids"?, "group_ids"?, "channel_kinds"?, "send_at"?, "require_ack"?}` → 201 message |
| GET | `/messages/{id}` | records_read | One message |
| GET | `/messages/{id}/deliveries` | records_read | `{"deliveries": [...]}` |
| GET | `/messages/{id}/ack-status` | records_read | `{message_id, require_ack, total, acknowledged, pending_contact_ids}` |
| POST | `/messages/{id}/dispatch` | dispatch | Dispatch that message → summary `{dispatched, delivered, failed}` |
| POST | `/dispatch-due` | dispatch | Dispatch all due queued deliveries → summary |
| POST | `/deliveries/{id}/ack` | ack_record | Acknowledge → delivery |
| GET | `/search?q=...` | records_read | `{contacts, messages, deliveries}` |
| GET | `/audit` | audit_read | `{"entries": [...]}`; optional filters `?actor=&action=&target=&since=&until=` |
| GET | `/audit/verify` | audit_read | `{ok, entries, first_bad_index}` — hash-chain verification |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

See `tests/README.md` for the coverage table, the negative
controls, and the mutation-verification drill records.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **High** baseline cross-walked
to the CMMC L3 basis (the NIST SP 800-171 Rev. 2 practices plus
selected NIST SP 800-172 enhanced requirements):

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store and
  again at the API), AC-5 (separation of duties — the `auditor`
  role holds audit review and nothing else), AC-6 (least privilege
  — reads for all roles, operational writes for operator, channel
  configuration for admin only), AC-7 (unsuccessful logon attempts
  — per-username lockout); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-5 (response to audit processing failures — writes
  fail closed), AU-6 / AU-7 (audit review, analysis & reduction —
  filtered query; `audit_read` restricted to admin + auditor),
  AU-9 (protection of audit information — append-only, hash-chained
  store, no mutation API, chain verification).
- **SI / SA / SC** — SI-10 (information input validation —
  malformed input is rejected, never partially applied, and
  consumes no ids); SC-8 (transmission confidentiality — the server
  runs over TLS when a certificate is configured; encryption at
  rest is a deployment-layer control, stated plainly and not
  claimed here).

## Honesty: what is NOT in this build

- **The reference transport is a deterministic stub.** Dispatch
  records delivery locally — status, attempts, and a receipt
  explicitly labelled `{"transport": "reference",
  "reference_transport": true}` — when an enabled channel of the
  delivery's kind exists. **It does not transmit anything over any
  real network**: no email is sent, no SMS is sent, no fax is sent,
  no call is placed, no push notification is pushed.
- The following Extended capabilities are **NOT implemented**
  (they are reserved for the final gap batch): real-time
  voice/video media transport, fax transport networks, email
  threat-detection engines, archiving/eDiscovery engines,
  certificate lifecycle automation, IVR / virtual-agent
  conversation engines, virtual-workspace streaming, workflow/BPM
  engines, and E2E encrypted transport.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength (including the MFA that
  IA-2(1)/(2) demands at this tier), and account lifecycle belong
  to the embedding organization.
- **FIPS-validated cryptography is not claimed** (SC-13): Python's
  standard library is not a FIPS-validated cryptographic module,
  even though a sibling describes its own hosting in FIPS-140-3
  terms.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **TLS is available only when a certificate is
  configured** (`--certfile`/`--keyfile`); the default serve mode
  is plain HTTP for local/demo use.
- **Audit retention (AU-11) is not enforced**, and there are no
  sessions to lock or terminate (AC-11/AC-12): authentication is
  per-request from headers.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control
  mapping above states which baseline families the build's
  features answer to; nothing more.
