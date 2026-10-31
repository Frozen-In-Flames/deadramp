# CRM L3-adjacent — singleton build (Operation DeadRamp, Phase 2, Group 40)

This is the clean-room implementation of the **Customer Relations
Management (CRM) L3-adjacent singleton**: **1 fork** from the
FedRAMP Marketplace at the High tier — **Pega Cloud for Government
(Pegasystems)**, FedRAMP Certified — built under the Merge Rule as
the cross-tier merge of that fork with the shipped Group 25 CRM L2
build: the L2 category substrate carried up whole and uplifted to
the FedRAMP High baseline.

Two honesty notes up front. First, **the singleton tags zero
claims** under Group 25's verbatim taxonomy: Pega's marketplace
description is five sentences of platform prose (a fully managed
cloud, no-code application development with model-based design, a
FedRAMP High authorization statement) containing no taxonomy
vocabulary at all. The near-misses are itemized in
`scratch/ARTIFACTS.md` ("no-code" is not "codeless"; "authorized
FedRAMP High" is not "authorized users") and the taxonomy was not
re-tuned. The 10 core functions below are therefore **carried, not
claimed**, for this tier — they stand because the Merge Rule carries
the L2 union upward whole and a wording artifact is not a downgrade
(the core-boundary decision in `UNION-SPEC.md`). Second, **Pega's
own engines are not in this build**: the no-code development
platform, case/BPM workflow execution, and decisioning that make
Pega Pega are Extended gaps, named in `UNION-SPEC.md` for the final
batch. This build is the records substrate at the High baseline —
not a claim that a low-code platform and a records service are the
same product.

It was written from the union contract only: original code, no
vendor code, assets, or branding. Python 3, **standard library
only**, no external dependencies. Where functions overlap it reuses
Group 25's own Apache-2.0 code: `__init__.py` is byte-identical;
the other six modules are Group 25's, modified only for the High
uplifts marked **[L3]** below.

## The 10 core functions (carried from Group 25, at High)

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
   appends a new version. Records only — nothing is rendered into
   any application.
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
9. **REST API** — every function above over a JSON REST API. Case
   and report endpoints accept a `?now=` ISO parameter for
   deterministic derived values. **[L3]** Unsuccessful logons lock
   the username out (AC-7, below).
10. **RBAC + audit log** — platform roles `admin`, `operator`,
    `viewer`, **[L3]** plus `auditor`, with a permission matrix
    enforced on every operation; every mutation, every search, and
    every denied attempt is recorded with actor, action, target,
    and UTC timestamp. **[L3]** The audit log is **hash-chained and
    tamper-evident** with chain verification, **fail-closed** on
    write failure, and **queryable** (AU-9/AU-5/AU-7). Optional JSONL
    file persistence. There is no mutation or deletion API for
    audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `acct-`, `ct-`,
`case-`, `int-`, `guide-`, `find-`, `mod-`. Permission is checked
before any state change or id allocation. **[L3]** An operation
whose audit write fails is rolled back in full — records and id
counters — and the error propagates (AU-5).

## How to run

From this directory:

```sh
PYTHONPATH=src python -m crm serve --host 127.0.0.1 --port 8799
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`), **[L3]** `--max-failed-logins N` (default 3) and
`--lockout-seconds S` (default 300) for the AC-7 lockout. A startup
line is printed once the server is listening.

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
print(audit.verify_chain())  # (True, None) — the trail is hash-chained [L3]
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401). **[L3]** After
`--max-failed-logins` consecutive failures a username locks for
`--lockout-seconds`; attempts during the lock get 403 and are
audited as `auth:locked`.

| User    | Role     | Permissions |
|---------|----------|-------------|
| `alice` | admin    | all 14 actions |
| `bob`   | operator | all reads except `audit_read`, plus `registry_write`, `case_write`, `interaction_write`, `guide_write`, `finding_write` (NOT `config_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read`: `registry_read`, `case_read`, `interaction_read`, `guide_read`, `finding_read`, `config_read`, `report_read` |
| `dana`  | auditor  | **[L3]** `audit_read` only (AC-5: audit review separated from administration; no operational read or write) |

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

The Group 25 surface, plus the two **[L3]** audit endpoints:

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
| GET | `/audit` | audit_read | `{"entries": [...]}` — **[L3]** accepts `?actor=`, `?action=`, `?target=`, `?since=`, `?until=` filters (AU-7) |
| GET | `/audit/verify` | audit_read | **[L3]** `{"ok", "entries", "first_bad_index"}` — hash-chain verification (AU-9) |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

144 tests. See `tests/README.md` for the coverage table, the two
negative controls, and the mutation-verification drill records.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **High** baseline (the FedRAMP
High baseline for this tier), with the Group 25 mapping carried up
and the **[L3]** uplifts added:

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store and
  again at the API), **AC-5 [L3]** (separation of duties — the
  `auditor` role holds `audit_read` and nothing else), AC-6 (least
  privilege — reads for all operational roles, operational writes
  for operator, module configuration and audit read for admin,
  audit read alone for auditor), **AC-7 [L3]** (unsuccessful logon
  lockout in the service layer); IA-2 (identification &
  authentication — identity is supplied by the embedding
  organization via user/role headers; this service ships hooks,
  not an IdP; MFA-grade authentication at High is the IdP layer's,
  gap-listed in `UNION-SPEC.md`).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records, incl. the **[L3]** chain fields), **AU-5 [L3]** (audit
  failure response — fail-closed writes with full rollback), AU-6
  (audit review — `audit_read` restricted to admin and auditor),
  **AU-7 [L3]** (audit reduction — filtered query), **AU-9 [L3]**
  (protection of audit information — append-only, hash-chained,
  tamper-evident store with `verify_chain()`; no mutation API).
  AU-11 (retention) is gap-listed, not claimed.
- **SI / SA / SC** — SI-10 (information input validation —
  malformed input is rejected, never partially applied, and
  consumes no ids); SA / system acquisition honesty in this README;
  SC-8 (transmission confidentiality — TLS when a certificate is
  configured; encryption at rest is a deployment-layer control,
  stated plainly and not claimed here); SC-13 (FIPS-validated
  cryptography) is gap-listed — Python's standard library is not a
  validated module and this build does not claim it is.

## Honesty: what is NOT in this build

- **Zero claims at this tier.** The singleton's description tags no
  function family under the verbatim taxonomy; the core is the
  Group 25 category substrate carried up under the Merge Rule and
  flagged carried, not claimed, throughout `UNION-SPEC.md`.
- **Pega's engines are NOT implemented.** No no-code / low-code
  application development or model-based design tooling, no case
  automation or BPM/workflow execution, no decisioning engine, no
  GenAI tooling, and no managed-cloud operations platform. Those
  are the singleton's Extended gaps, named in `UNION-SPEC.md`.
- **Extended capabilities from the L2 union are NOT
  implemented.** No customer-service casework depth, no guidance
  delivery runtime (guides are *records* about guidance), no
  gap-identification or adoption-analytics engine (findings are
  recorded, not detected), and no customization/module execution
  engine (module settings are stored verbatim, never run).
- **No sales CRM is built — 0 claims at either tier.** No fork in
  this category supports an opportunity, pipeline, lead, or
  campaign function in its public record, so none is built or
  implied. These are named absences in the spec.
- **No real personal data can be stored — by design.** Accounts
  and contacts are keyed by an opaque caller-supplied `reference`;
  no entity shape has a field for a real name, email, phone
  number, SSN, date of birth, address, or salary.
- **No scores exist — by design.** Vendor-stated figures inside a
  finding's `detail` are stored verbatim and never parsed,
  averaged, or aggregated; the report counts records and nothing
  else.
- **Derived, not stored — and not an SLA engine.** Breach values
  are computed at read time from stored timestamps; there is no
  background timer, escalation, or notification when a case
  breaches.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength (including MFA at this tier), and account
  lifecycle belong to the embedding organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **FIPS-validated cryptography is not claimed**
  (stdlib only). **TLS is available only when a certificate is
  configured**; the default serve mode is plain HTTP for
  local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which baseline
  families the build's features answer to; nothing more. FedRAMP
  authorizes products; CMMC certifies organizations — neither
  regime accepts the other as evidence.
