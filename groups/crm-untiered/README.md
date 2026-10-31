# Customer Relations Management (CRM) — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **untiered fork** of Customer Relations
Management (CRM) — census unit `untiered:Customer Relations
Management (CRM)` in `../../remainder.json` (Untiered Set 23).
**This is an untiered set, and that means something specific:**
the member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for this offering, so
**tier stays null**: no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented
control claims; tier stays null in the registry until the source
publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); the per-fork spec sheet is in
[`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned
by tests.

The fork was spec'd under the category's existing 18-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, asserted equal to the CRM L3 group's copy, never
re-tuned). Taxonomy-verbatim proof: the extractor first
reproduced the founding CRM L2 group's original shipped claim
tables exactly — **2 of 2 forks, 8 of 8 claims, deep-equal** —
before tagging this set. Result here: **2 claims** on the single
fork, and the fork is not a zero-claim fork. One claim is the
category's first registry claim on registry-flavored phrasing
("contact management"); the other is the AI family at bare-token
weight, recorded at exactly that weight (see the union spec).

The build implements the category's **ten-function substrate** —
the CRM records machinery — carried **byte-identical** from the
founding CRM L2 build (`../crm-l2/src/crm/`, 7 of 7 modules;
SHA-256 accounting below). The substrate is tier-independent
records code: the founding source contains no tier or baseline
machinery, so there was nothing tier-shaped to strip, and the CRM
L3 singleton's High uplifts are **not** inherited here — this set
carries the L2 founding substrate as-is. Where the founding
contract's text says baseline substrate for access control and
audit, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline.

## The fork

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2635050861 | VirtualDojo, Inc. | VirtualDojo AI CRM | 2 |

In `forks.json` the fork is filed under Customer Relations
Management (CRM) itself, and the census proposal agrees with the
filed category ("CRM explicitly named") — no reclassification to
record. Its authorization status as recorded is Initial
Implementation — a status is record data, not a claim.

## The 10 core functions

1. **Account & contact registry** — accounts (`acct-`) and
   contacts (`ct-`, each under an account) keyed by a required,
   unique, **opaque caller-supplied `reference`**, with an
   optional caller-chosen `label` and free-form attributes.
   **Claim-supported in this set** (`account_contact_registry`).
2. **Service case records & lifecycle** — cases (`case-`), typed
   (inquiry/problem/request/feedback/general), with
   account/contact links (a contact linked with an account must
   belong to it), an opaque `assignee_ref`, priority, and an
   optional `due_at`. Lifecycle `open → in_progress → resolved →
   closed` (plus `cancelled`; `resolved` may reopen). Breach is
   **derived at read time, never stored**:
   `breached = now > due_at and status not in (resolved, closed,
   cancelled)`. Carried, not claimed in this set.
3. **Interaction & activity records** — immutable records (`int-`)
   across guidance_session/call/chat/email/portal/in_person/system
   channels, with direction, outcome, summary, `external_ref`
   passthrough, and account/contact/case/guide links. No update
   or delete API exists. Carried, not claimed in this set
   (substrate under the founding core-boundary decision).
4. **Guidance content registry** — guides (`guide-`): title, kind
   (walkthrough/tooltip/checklist/announcement), an opaque
   `target_ref` naming the host surface, steps, enabled flag,
   versioned on update with full version history. Records only —
   the build renders nothing into any application. Carried, not
   claimed in this set.
5. **Gap-finding records** — findings (`find-`): title, `detail`
   text stored **verbatim** as supplied, severity, source,
   optional account link, lifecycle `open → acknowledged →
   addressed` (plus `dismissed`). This build stores findings; no
   score is computed or stored anywhere. Carried, not claimed in
   this set.
6. **Module / configuration registry** — modules (`mod-`): label,
   scope, `settings_text` stored verbatim (never executed),
   enabled flag, versioned on update. Writes are **admin-only**.
   Carried, not claimed in this set.
7. **Reports** — deterministic counts over the registry's own
   records: cases by status/type/account plus breached count at
   the report's `now`, interactions by channel/outcome, guides by
   kind/enabled, findings by severity/status, module and registry
   totals. Counts of records only — no scoring aggregate exists.
8. **Search** — literal case-insensitive substring search over
   accounts/contacts (label + reference), cases, interactions,
   findings, and guides.
9. **REST API** — the full surface over HTTP, with the house auth
   convention (X-User/X-Role against a demo registry; 401
   unknown/mismatched, 403 permission, denied attempts audited).
10. **Access control (RBAC) + audit log** — admin/operator/viewer
    matrix over 14 actions; `config_write` and `audit_read` are
    admin-only; enforced in the store before any mutation or id
    allocation, and again at the service layer. The audit log is
    append-only, JSONL-persistable, and records every mutation
    and every denied attempt (`<action>:denied`). Carried, not
    claimed in this set.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type with the prefixes
above.

**Privacy discipline (hard rule of this build).** Accounts and
contacts are keyed by opaque caller-supplied references only. No
entity in this build has a field that can hold a real name,
email, phone number, SSN, date of birth, address, or salary
figure — the shapes are enforced by tests
(`tests/test_privacy.py`), which also assert that no score field
and no scoring aggregate exists anywhere in the build. The fork's
own description asserts its product stores customer PII (as part
of a CUI statement); that is the fork's assertion about its
product — this build stores none of it and no record shape can.

One of the ten functions is claim-supported by the fork in this
set under the category's standing dispositions (see
`UNION-SPEC.md` for the tracing); the other nine are carried as
substrate under the founding core-boundary decision. The
`ai_scoring` claim supports no core function — its disposition is
Extended. Functions are **carried** as substrate; no function is
claimed to be *attained* by the fork — the build is the merged
open implementation, not the fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m crm serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User    | Role     | Permissions                                  |
|---------|----------|----------------------------------------------|
| `alice` | admin    | all 14 actions |
| `bob`   | operator | all reads except `audit_read`, plus `registry_write`, `case_write`, `interaction_write`, `guide_write`, `finding_write` (NOT `config_write`, NOT `audit_read`) |
| `carol` | viewer   | reads only, except `audit_read`: `registry_read`, `case_read`, `interaction_read`, `guide_read`, `finding_read`, `config_read`, `report_read` |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client.

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

Account dicts are `{id, reference, label, attributes, created_by,
created_utc, updated_utc}` with sequential ids `acct-1`,
`acct-2`, …; contact, case, interaction, guide, finding, and
module dicts follow the same pattern with their own prefixes (see
`UNION-SPEC.md` and the founding spec for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**104 tests, OK** at delivery: the founding group's 96-test core
suite carried with the code, plus spec tests pinning this set
(exactly 1 sheet; membership exact against `remainder.json`; the
sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; the description byte-equal to the
raw cache; 2 claims total with no zero-claim fork; the
certified-services catalogue never matched). The category's
signature breach-derivation mutation drill was re-run in this
tree — exactly 7 failures under the mutant, store restored and
SHA-256 verified (see `tests/README.md`).

## Byte-identity accounting

`src/crm/` is carried from the founding group
`../crm-l2/src/crm/` — **7 of 7 modules byte-identical**,
SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `4b3373b1f09735d076660d961012d1751e730ab563639f47d18fbf23b0d9f441` |
| `__main__.py` | `cd5aed9d9bebd6b7ed6a1112b86c3a00c3453ba3aec192b67a3149e77aeb3d98` |
| `access.py` | `81ce16cc83605e14a82fc1d4902bf50bac4974b8fe0a1bfc63c40572c38e9a1e` |
| `audit.py` | `59ee29d87ef84180f6b672e1a4db273e4f52647dd915171fdf5a33804e7178e1` |
| `errors.py` | `58e88aec805d0722bc36ac3adde347ac26c469011bfd4f1a6d005a40a6788d63` |
| `service.py` | `ba4525a4f6581c7217006b8952b8a6aa9149770f74079c1c79ed89666f846c45` |
| `store.py` | `16bcc12fa6b55dec54bf76f150b1619834400ba93ee4687df5dffe2990fe2f1a` |

The tree contains exactly the package — no stray duplicate files
at the `src/` root. The founding source contains no tier or
baseline machinery, and no docstring in it names a tier, so the
carry needed no re-anchoring edits of any kind.

The test suite is likewise carried whole (all 14 founding test
modules), with one labeling fix in `tests/crm_helpers.py` (its
docstring now names this untiered set as the carrier of Group
25's suite) and the new `tests/test_specs.py` added. Full
accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this build
asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts, in its own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

Documented by the fork in this set: **no control family at family
weight.** The description contains no access-control, audit,
encryption, or authentication language; `access_control` and
`audit_logging` both tag 0.

At **prose weight only**: the fork's second sentence asserts the
platform is for "storing Controlled Unclassified Information
(CUI) including government contract data, customer PII, proposal
documents, and financial/pricing data" — a statement about what
data the offering handles, naming no mechanism and no framework,
so it documents no 800-53 family. It is recorded in the union
spec because CUI handling is the fork's own framing of its
purpose, and because it draws this build's privacy boundary: the
build's shapes hold opaque references only and cannot hold the
PII the fork's description names.

**Not documented** by the fork in this set: every NIST SP 800-53
control family — including AC, AU, IA, SC, CA, CM, IR, MA, MP,
PE, PL, PM, PS, RA, SA, and SI **as control claims** — is
asserted by no sentence in the description. If the source later
publishes an impact level for this offering, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for the fork or for
  itself. The fork's recorded authorization status is source
  data, not a claim by this build, and a fork's documented
  control language is recorded as *its* claim, never as the
  build's control attainment.
- **The AI claim is a token, not a capability.** `ai_scoring`
  stands at bare-token weight ("AI", "AI-powered"); the build
  contains no model, no inference, and no scoring of any kind —
  the no-score rule is test-enforced. The AI function the
  description actually names, proposal generation, is an
  Extended gap, not an implementation.
- **Extended functions are specified, not implemented.** The
  union spec ranks 18 functions; the substrate behind 10 is
  implemented here. NOT implemented: the AI proposal-generation
  engine; the pipeline forecasting engine (asserted in substance,
  claimed at no pattern); the document automation engine
  (asserted, with no family in the taxonomy); integration
  connector engines; knowledge base & self-service content;
  marketing-automation engines & email delivery.
- **The catalogue was not mined for claims.** The source record's
  `certified_services` field names a sales-pipeline function the
  description never asserts in matching text; matching it would
  have fabricated a claim, so it stands excluded and the absence
  is pinned by test.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own.
- **Named absences stand.** Customer service cases have 0
  claimants in this set (the description never says "customer
  service"); campaigns & audience lists 0; access control and
  audit logging 0 each, even alongside a CUI-storage assertion.
  Nothing was back-filled to make the set look complete.
