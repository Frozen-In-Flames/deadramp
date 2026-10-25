# CRM L2 — merged build (Operation DeadRamp, Phase 2, Group 25)

This is the merged, clean-room implementation of the **Customer
Relations Management (CRM) L2** sibling group: **2 forks / vendor
platforms** from the FedRAMP Marketplace that share the same
category (Customer Relations Management (CRM)) and the same trust
tier (FedRAMP Moderate), built as one open-source service from the
group's union contract.

A note on heterogeneity, honestly: these two products share a
category label more than a function. One is a customer-service
platform (Oracle Service Cloud (OSvC)); the other is a
digital-adoption overlay (WalkMe DAP) filed under this category by
the source. Neither description mentions sales, opportunities,
pipelines, leads, or campaigns — the classic sales-CRM surface is
absent from this group's public record, so none is built. This
build is their **shared records substrate**: the account, contact,
case, interaction, guide, finding, and module records those
products keep, with one access matrix and one audit log — not a
claim that the siblings were ever the same product.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 10 core functions

1. **Account & contact registry** — accounts (`acct-`) and contacts
   (`ct-`, each under an account) keyed by a required, unique,
   **opaque caller-supplied `reference`**, with an optional
   caller-chosen `label` and free-form attributes. No real
   identifiers exist in these shapes (see Honesty).
2. **Service cases** — cases (`case-`) of type inquiry / problem /
   request / feedback / general, with priority, optional
   account/contact links (a contact linked with an account must
   belong to it), an opaque `assignee_ref`, and an
   `open → in_progress → resolved → closed` lifecycle (plus
   cancellation and reopen). A case's SLA **breach flag is derived
   at read time** from `due_at` (never stored; terminal statuses
   never read breached).
3. **Interactions** — immutable interaction records (`int-`) across
   guidance_session / call / chat / email / portal / in_person /
   system channels, with direction, outcome, and an `external_ref`
   passthrough. There is deliberately no update or delete API.
4. **Guides** — guidance content records (`guide-`): title, kind
   (walkthrough / tooltip / checklist / announcement), an opaque
   `target_ref` naming the host surface, and steps. Every update
   appends a new version (unchanged fields carried forward) and
   bumps the version counter. Records only — nothing is rendered
   into any application.
5. **Findings** — gap / problem-area records (`find-`) whose
   `detail` text is stored **verbatim** as supplied, with severity,
   source, and an `open → acknowledged → addressed` lifecycle (plus
   `dismissed`). No score is computed or stored anywhere.
6. **Modules** — configuration records (`mod-`): label, scope, and
   `settings_text` stored verbatim (never executed), versioned on
   update. Module writes are **admin-only**.
7. **Reports** — deterministic aggregate counts (accounts/contacts
   totals; cases by status / type / account plus breached count;
   interactions by channel / outcome; guides by kind / enabled;
   findings by severity / status; module totals), all derived at
   the caller-supplied `now`. Counts of records only.
8. **Search** — literal, case-insensitive substring search (not
   regex) over accounts/contacts (label + reference), case
   subjects, interaction summaries + external refs, finding titles
   + details, and guide titles.
9. **REST API** — every function above is exposed over a JSON REST
   API, so the service composes with anything that speaks HTTP.
   Case and report endpoints accept a `?now=` ISO parameter for
   deterministic derived values.
10. **RBAC + append-only audit log** — platform roles `admin`,
    `operator`, `viewer` with a permission matrix enforced on
    every operation (see below); every account, contact, case,
    interaction, guide, finding, and module mutation, every
    search, and every denied attempt is recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence. There is no mutation or deletion API for audit
    entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `acct-`, `ct-`,
`case-`, `int-`, `guide-`, `find-`, `mod-`. Permission is checked
before any state change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m crm serve --host 127.0.0.1 --port 8799
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from crm.access import User
from crm.audit import AuditLog
from crm.store import CrmStore

audit = AuditLog()
store = CrmStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "operator")
account = store.create_account(admin, "ACCT-100", label="Agency Alpha")
contact = store.create_contact(bob, account["id"], "PERSON-200")
case = store.create_case(bob, "problem", "Renewal portal error",
                         account_id=account["id"], contact_id=contact["id"],
                         due_at="2020-01-01T00:00:00Z")
print(store.get_case(case["id"], bob, now="2025-06-01T00:00:00Z")["breached"])  # True (derived)
finding = store.create_finding(bob, "Gap: renewal step 3",
                               detail="Users abandon at step 3 (vendor-stated)",
                               source="adoption review")
print(finding["detail"])  # stored verbatim; never scored
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all 14 actions |
| `bob`   | operator | all reads except `audit_read`, plus `registry_write`, `case_write`, `interaction_write`, `guide_write`, `finding_write` (NOT `config_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read`: `registry_read`, `case_read`, `interaction_read`, `guide_read`, `finding_read`, `config_read`, `report_read` |

Read actions: `registry_read`, `case_read`, `interaction_read`,
`guide_read`, `finding_read`, `config_read`, `report_read`,
`audit_read`. Write actions: `registry_write`, `case_write`,
`interaction_write`, `guide_write`, `finding_write`,
`config_write`. Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a
plain string carries identity but no role, so the service layer —
which knows the registry and always passes `User` objects — is
responsible for enforcement in that case (the shipped groups'
convention).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/accounts` | registry_read | `{"accounts": [...]}` |
| POST | `/accounts` | registry_write | Body `{"reference", "label"?, "attributes"?}` → 201 account |
| GET | `/accounts/{id}` | registry_read | One account |
| GET | `/contacts` | registry_read | `{"contacts": [...]}` — accepts `?account_id=` |
| POST | `/contacts` | registry_write | Body `{"account_id", "reference", "label"?, "attributes"?}` → 201 contact |
| GET | `/contacts/{id}` | registry_read | One contact |
| GET | `/cases` | case_read | `{"cases": [...]}` — accepts `?now=`, `?status=`, `?case_type=`, `?account_id=` |
| POST | `/cases` | case_write | Body `{"case_type", "subject", "account_id"?, "contact_id"?, "assignee_ref"?, "priority"?, "due_at"?}` → 201 case |
| GET | `/cases/{id}` | case_read | One case (with derived `breached`) — accepts `?now=` |
| POST | `/cases/{id}/assign` | case_write | Body `{"assignee_ref"}` → case |
| POST | `/cases/{id}/transition` | case_write | Body `{"to_status"}` → case |
| GET | `/interactions` | interaction_read | `{"interactions": [...]}` — accepts `?case_id=`, `?account_id=` |
| POST | `/interactions` | interaction_write | Body `{"channel", "direction", "summary", "account_id"?, "contact_id"?, "case_id"?, "guide_id"?, "outcome"?, "external_ref"?}` → 201 interaction |
| GET | `/interactions/{id}` | interaction_read | One interaction |
| GET | `/guides` | guide_read | `{"guides": [...]}` |
| POST | `/guides` | guide_write | Body `{"title", "kind", "target_ref", "steps"?, "enabled"?}` → 201 guide |
| GET | `/guides/{id}` | guide_read | One guide |
| PATCH | `/guides/{id}` | guide_write | Body `{"steps"?, "enabled"?, "target_ref"?}` → guide at new version |
| GET | `/findings` | finding_read | `{"findings": [...]}` — accepts `?status=`, `?account_id=` |
| POST | `/findings` | finding_write | Body `{"title", "detail"?, "severity"?, "account_id"?, "source"?}` → 201 finding |
| GET | `/findings/{id}` | finding_read | One finding |
| POST | `/findings/{id}/transition` | finding_write | Body `{"to_status"}` → finding |
| GET | `/modules` | config_read | `{"modules": [...]}` |
| POST | `/modules` | config_write (admin) | Body `{"label", "scope", "settings_text", "enabled"?}` → 201 module |
| GET | `/modules/{id}` | config_read | One module |
| PATCH | `/modules/{id}` | config_write (admin) | Body `{"settings_text"?, "enabled"?}` → module at new version |
| GET | `/report` | report_read | Aggregate report — accepts `?now=` |
| GET | `/search?q=...` | case_read | `{accounts, contacts, cases, interactions, findings, guides}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

96 tests. See `tests/README.md` for the coverage table, the
negative control, and the mutation-verification drill record.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 Moderate baseline (the FedRAMP
Moderate baseline for this group's tier):

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store and
  again at the API), AC-6 (least privilege — reads for all roles,
  operational writes for operator, module configuration and audit
  read for admin only); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review — `audit_read` restricted to
  admin), AU-9 (protection of audit information — append-only
  store, no mutation API).
- **SI / SA** — SI-10 (information input validation — malformed
  input is rejected, never partially applied, and consumes no
  ids); SA / system acquisition honesty in this README: what the
  build is and is not is stated plainly, including the records-only
  scope (below); SC-8 (transmission confidentiality — the server
  runs over TLS when a certificate is configured; encryption at
  rest is a deployment-layer control, stated plainly and not
  claimed here).

## Honesty: what is NOT in this build

- **Extended capabilities are NOT implemented.** No customer-service
  casework depth (knowledge-driven agent desktop, self-service
  portal, chatbots), no guidance delivery runtime (nothing here
  renders a walkthrough inside any application — guides are
  *records* about guidance), no gap-identification or
  adoption-analytics engine (findings are recorded, not detected),
  and no customization/module execution engine (module settings
  are stored verbatim, never run).
- **No sales CRM is built — 0 claims.** No sibling in this group
  supports an opportunity, pipeline, lead, or campaign function in
  the union contract, so none is built or implied. These are named
  absences in the spec, recorded from the descriptions.
- **No real personal data can be stored — by design.** Accounts
  and contacts are keyed by an opaque caller-supplied `reference`;
  no entity shape has a field for a real name, email, phone
  number, SSN, date of birth, address, or salary. The `label` is a
  caller-chosen display string this build never interprets.
- **No scores exist — by design.** Vendor-stated figures inside a
  finding's `detail` are stored verbatim and never parsed,
  averaged, or aggregated; the report counts records and nothing
  else, because no claim defines a scoring aggregate.
- **Derived, not stored — and not an SLA engine.** Breach values
  are computed at read time from stored timestamps; there is no
  background timer, escalation, or notification when a case
  breaches.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not
  an identity provider**. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **TLS is available only when a certificate is
  configured** (`--certfile`/`--keyfile`); the default serve mode
  is plain HTTP for local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which baseline
  families the build's features answer to; nothing more.
