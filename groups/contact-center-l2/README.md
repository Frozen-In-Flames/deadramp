# Contact Center L2 — merged build (Operation DeadRamp, Phase 2, Group 15)

This is the merged, clean-room implementation of the **Contact Center
L2** sibling group: **5 forks / vendor platforms** from the FedRAMP
Marketplace that share the same category (Contact Center) and the same
trust tier (FedRAMP Moderate), built as one open-source service from
the group's union contract.

A note on heterogeneity, honestly: this category is not five
contact-center products. It contains **one true callback product**
(Mindful by Medallia — citizen callback scheduling) plus
identity-security, observability, records/claims, and related siblings
filed under this category by the source. This build is their **shared
records substrate**: the directory, queue, case, callback,
interaction, alert, and rule records those products all keep, with
one access matrix and one audit log — not a claim that the siblings
were ever the same product.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 12 core functions

1. **Directory** — agents (`agt-`, with skills and attributes) and
   contacts (`ct-`, with an opaque external `reference` and
   attributes; never a real phone number — see Honesty).
2. **Queues** — queues (`que-`) with agent membership (duplicate
   membership is a validation error).
3. **Cases** — cases (`case-`) of type claim / callback / activity /
   inquiry / general, with priority, optional contact/queue/agent
   links, an `open → in_progress → resolved → closed` lifecycle
   (plus cancellation and reopen), and an SLA **breach flag derived
   at read time** from `due_at` (never stored; terminal statuses
   never read breached).
4. **Callbacks** — callback requests (`cb-`) with a stored status of
   scheduled / completed / cancelled and a **state derived at read
   time**: an overdue scheduled callback reads `state='overdue'`
   while its stored `status` stays `scheduled`. Terminal transitions
   (complete / cancel) are allowed only from `scheduled`.
5. **Interactions** — immutable interaction records (`int-`) across
   voice / chat / email / in_person / remote_session / system
   channels. There is deliberately no update or delete API.
6. **Alerts** — alerts (`alr-`) with severity info / warning /
   critical and a `raised → acknowledged → resolved` lifecycle.
7. **Rules registry** — versioned rules (`rule-`): every update
   appends a new version (unchanged fields carried forward) and bumps
   the version counter. Rule writes are **admin-only**.
8. **Reports** — deterministic aggregate counts (cases by status /
   type / queue plus breached count, interactions by channel /
   outcome, alerts by severity / status, callbacks by derived state),
   all derived at the caller-supplied `now`.
9. **Search** — literal, case-insensitive substring search (not
   regex) over people (agent/contact names, contact references),
   case subjects, interaction summaries + external refs, and alert
   messages.
10. **REST API** — every function above is exposed over a JSON REST
    API, so the service composes with anything that speaks HTTP.
    Case, callback, and report endpoints accept a `?now=` ISO
    parameter for deterministic derived values.
11. **RBAC** — platform roles `admin`, `operator`, `viewer` with a
    permission matrix enforced on every operation (see below).
12. **Append-only audit log** — every agent, contact, queue, case,
    callback, interaction, alert, and rule mutation, every search,
    and every denied attempt is recorded with actor, action, target,
    and UTC timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `agt-`, `ct-`, `que-`, `case-`,
`cb-`, `int-`, `alr-`, `rule-`. Permission is checked before any
state change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m contact serve --host 127.0.0.1 --port 8795
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from contact.access import User
from contact.audit import AuditLog
from contact.store import ContactStore

audit = AuditLog()
store = ContactStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "operator")
agent = store.create_agent("Dana", admin, skills=["billing"])
contact = store.create_contact("Casey", bob, reference="EXT-1001")
case = store.create_case(bob, "claim", "Broken widget",
                         contact_id=contact["id"], agent_id=agent["id"],
                         due_at="2020-01-01T00:00:00Z")
print(store.get_case(case["id"], bob, now="2025-06-01T00:00:00Z")["breached"])  # True (derived)
cb = store.schedule_callback(bob, contact["id"], "2020-01-01T00:00:00Z")
print(store.get_callback(cb["id"], bob, now="2025-06-01T00:00:00Z")["state"])  # 'overdue' (derived)
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all 16 actions |
| `bob`   | operator | all reads except `audit_read`, plus `directory_write`, `queue_write`, `case_write`, `callback_write`, `interaction_write`, `alert_write` (NOT `rule_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read`: `directory_read`, `queue_read`, `case_read`, `callback_read`, `interaction_read`, `alert_read`, `rule_read`, `report_read` |

Read actions: `directory_read`, `queue_read`, `case_read`,
`callback_read`, `interaction_read`, `alert_read`, `rule_read`,
`report_read`, `audit_read`. Write actions: `directory_write`,
`queue_write`, `case_write`, `callback_write`, `interaction_write`,
`alert_write`, `rule_write`. Unknown roles hold no permissions.

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
| GET | `/agents` | directory_read | `{"agents": [...]}` |
| POST | `/agents` | directory_write | Body `{"name", "skills"?, "attributes"?}` → 201 agent |
| GET | `/contacts` | directory_read | `{"contacts": [...]}` |
| POST | `/contacts` | directory_write | Body `{"name", "reference"?, "attributes"?}` → 201 contact |
| GET | `/queues` | queue_read | `{"queues": [...]}` |
| POST | `/queues` | queue_write | Body `{"name"}` → 201 queue |
| GET | `/queues/{id}/members` | queue_read | `{"members": [agent, ...]}` |
| POST | `/queues/{id}/members` | queue_write | Body `{"agent_id"}` → 201 queue |
| GET | `/cases` | case_read | `{"cases": [...]}` — accepts `?now=`, `?status=`, `?queue_id=`, `?case_type=` |
| POST | `/cases` | case_write | Body `{"case_type", "subject", "contact_id"?, "queue_id"?, "agent_id"?, "priority"?, "due_at"?}` → 201 case |
| GET | `/cases/{id}` | case_read | One case (with derived `breached`) — accepts `?now=` |
| POST | `/cases/{id}/assign` | case_write | Body `{"agent_id"?, "queue_id"?}` (at least one) → case |
| POST | `/cases/{id}/transition` | case_write | Body `{"to_status"}` → case |
| GET | `/callbacks` | callback_read | `{"callbacks": [...]}` (with derived `state`) — accepts `?now=` |
| POST | `/callbacks` | callback_write | Body `{"contact_id", "requested_for", "case_id"?, "agent_id"?, "note"?}` → 201 callback |
| POST | `/callbacks/{id}/complete` | callback_write | Body `{"outcome"?}` → callback |
| POST | `/callbacks/{id}/cancel` | callback_write | → callback |
| GET | `/interactions` | interaction_read | `{"interactions": [...]}` — accepts `?case_id=` |
| POST | `/interactions` | interaction_write | Body `{"channel", "direction", "summary", "case_id"?, "contact_id"?, "agent_id"?, "outcome"?, "external_ref"?}` → 201 interaction |
| GET | `/alerts` | alert_read | `{"alerts": [...]}` |
| POST | `/alerts` | alert_write | Body `{"severity", "message", "source"?, "case_id"?}` → 201 alert |
| POST | `/alerts/{id}/ack` | alert_write | Acknowledge → alert |
| POST | `/alerts/{id}/resolve` | alert_write | Resolve → alert |
| GET | `/rules` | rule_read | `{"rules": [...]}` |
| POST | `/rules` | rule_write (admin) | Body `{"name", "case_type", "condition", "action_text"}` → 201 rule |
| PATCH | `/rules/{id}` | rule_write (admin) | Body `{"condition"?, "action_text"?, "enabled"?}` → rule at new version |
| GET | `/report` | report_read | Aggregate report — accepts `?now=` |
| GET | `/search?q=...` | case_read | `{people, cases, interactions, alerts}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Single-object GETs for agents, contacts, queues, callbacks,
interactions, alerts, and rules (`GET /agents/{id}`, etc.) are also
served with the matching read permission.

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

107 tests. See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline (the FedRAMP
Moderate baseline for this group's tier):

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store and
  again at the API), AC-6 (least privilege — reads for all roles,
  operational writes for operator, rule configuration and audit read
  for admin only); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review — `audit_read` restricted to admin),
  AU-9 (protection of audit information — append-only store, no
  mutation API).
- **SI / SA** — SI-10 (information input validation — malformed
  input is rejected, never partially applied, and consumes no ids);
  SA / system acquisition honesty in this README: what the build is
  and is not is stated plainly, including the records-only scope
  (below); SC-8 (transmission confidentiality — the server runs
  over TLS when a certificate is configured; encryption at rest is a
  deployment-layer control, stated plainly and not claimed here).

## Honesty: what is NOT in this build

- **Extended capabilities are NOT implemented.** No telephony or
  callback dialing engine, no ACD/IVR routing engine, no workforce
  management, no real-time media — callbacks here are *records*
  about a requested contact, in the shape of the one true callback
  sibling's data (a requested time, a contact reference, an optional
  case/agent link), not a dialer.
- **Knowledge-base and CSAT/survey capabilities are absent — 0
  claims.** No sibling in this group supports a knowledge base or a
  satisfaction-survey function in the union contract, so none is
  built or implied.
- **No real phone numbers are stored — by design.** A contact's
  `reference` is an opaque external reference string for the
  embedding organization's own systems. This build has no field
  whose semantics are "the citizen's phone number", and scheduling a
  callback dials nothing.
- **Derived, not stored — and not an SLA engine.** Breach and
  overdue values are computed at read time from stored timestamps;
  there is no background timer, escalation, or notification when a
  case breaches or a callback becomes overdue.
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
