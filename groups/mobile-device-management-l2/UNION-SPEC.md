# Union Spec — Mobile Device Management (MDM), CMMC L2 (DeadRamp Phase 2, Group 50)

The merged functional spec for the **Mobile Device Management
(MDM) L2 singleton**: **1 fork**, category **Mobile Device
Management (MDM)** (a brand-new category — no group exists at any
other tier), CMMC tier **L2** (the member is FedRAMP **Moderate**
in `forks.json` — verified). The member list was reconciled two
ways with **zero diffs**: `forks.json` carries exactly one MDM /
L2 entry, and MAP.md's category arithmetic agrees (MDM total
**1** = L1 0 + L2 1 + L3-adjacent 0 + untiered 0; its service-model
table likewise shows MDM as SaaS 1 and nothing else). MAP.md's
sibling-group sections list only groups of size 2 or more, so no
prose section exists for this singleton; the arithmetic is the
check, as in the earlier singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID **FR2505553757**.

**What this fork actually is, stated plainly:** the single MDM
fork is Turning Point Global Solutions' Network Inventory and
Optimization Solution (NiOS®) — by its own description, a
**Telecommunication Expense Management (TEM) and Managed Mobility
(MM) system**: telecom ordering, service inventory, bill
validation, budgets, and reporting for government telecom
estates. It is filed under Mobile Device Management (MDM) in the
marketplace; its description contains **no mobile-device
management vocabulary at all** — no enrollment, no remote wipe or
lock, no application management, no device policy, no handset or
identifier registry. "Mobility" in its prose names telecom
mobility *services* (lines and plans held in inventory), not
managed handsets. This spec follows the description, not the
filing: the taxonomy below is the TEM/MM surface the fork claims,
and the MDM category's signature device functions are recorded
as named absences, never rounded up from the category label or
from the word "mobility".

## How functions were counted (a new category: the Group 1 method)

MDM has no parent group, so there is no inherited taxonomy. The
taxonomy below was defined **from this fork's own description**:
families are named from the description's own functional
vocabulary, each with a verbatim match pattern, matched against
the description's sentences by `scratch/extract.py`. A function
is claimed **only** when a sentence contains matching text; the
matching sentence is stored as the claim's evidence in the spec
sheet. Marketing prose gets no tags. **16 claims in total, one
per family**. Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
"Optimization" appears only in the product's *name* — no sentence
claims an optimization function, so no family is defined for it;
sentence 1's five-domain summary list IS tagged (it names
functions the offering performs, and the bullets detail each),
while its "automation" word tags nothing beyond the workflow
bullet's own family; "single-pane window" tags the substrate the
view runs on, not a rendered UI; "enhancing governance, and
ensuring cost control" is outcome prose riding on reporting;
"projections" tags budget visibility as a *recorded value* — the
forecasting engine is Extended and nothing in the build computes
one; the source record's `business_categories` is empty (`[]`)
while `forks.json` files the fork under MDM — both facts recorded
as-is, neither treated as a functional claim.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Telecom ordering & service orders | 1 | **Core** — service order records & lifecycle (MACD, port, suspend, restore) |
| 2 | Built-in customizable workflow | 1 | **Core slice** — workflow definitions registered as data, **never executed**; the execution/routing engine is Extended |
| 3 | Telecom service inventory management | 1 | **Core** — the inventory registry (unified view = registry + search + API) |
| 4 | Bill validation, reconciliation & verification | 1 | **Core** — bill records and deterministic validation runs against contracts/orders/quotes/inventory records |
| 5 | Bill dispute initiation & tracking | 1 | **Core** — dispute records tracked through resolution |
| 6 | Financial management | 1 | **Core** — the budget/obligation/chargeback substrate the description's money functions presuppose |
| 7 | Budget visibility (obligated, spent, available) | 1 | **Core** — obligated/spent summed and available **derived at read**; projections recorded verbatim, never computed |
| 8 | Budget alerts | 1 | **Core** — alert records; delivery transport is Extended |
| 9 | Internal customer chargebacks | 1 | **Core** — chargeback records against budgets |
| 10 | Reporting & spending insights | 1 | **Core slice** — registry summaries computed from records; report-generation/analytics engines are Extended |
| 11 | Telecom lifecycle management, single-pane view | 1 | **Core substrate** — the records, search, and API the single view runs on; the web UI itself is Extended |
| 12 | Secure web-based portal | 1 | **Core substrate** — as #11; the portal UI is Extended |
| 13 | Data integration | 1 | Extended — carrier/contract data-integration engine and connectors |
| 14 | Analytics | 1 | Extended — analytics engine beyond registry summaries |
| 15 | APIs (Application Processing Interfaces) | 1 | **Core** — the build is API-first; every core function is exposed over REST |
| 16 | Cloud hosting platform (platform note) | 1 | Platform note — delivery prose (AWS GovCloud hosting, multi-tenant architecture); deployment layer |

**Named absences, stated plainly (the category's signature
surface):** the description contains **no device-management
vocabulary** — no enrollment or provisioning of handsets, no
remote wipe/lock, no application catalog or app management, no
device policy or compliance enforcement, no location tracking,
and no device identifier (IMEI/serial/phone-number) registry.
None of it was claimed, so in the registry sense none of it is
owed by the fork; it is registered as Extended below because it
is the surface the *category name* promises, and a reader of
this repo is entitled to see it named rather than silently
missing. **"Optimization"** likewise appears only in the product
name; the optimization engine is registered as a gap named from
the name, not from any claim.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *The scoping container.* Every claimed
function is exercised by a customer organization over its own
telecom estate ("enables customers to manage…" throughout), so
the substrate is scoped by customer organizations with
membership, the house scoping pattern: the organization record
is known only by an opaque `ref` and a label. (2) *Validation
arithmetic.* A validation run compares a bill's stated total
against the sum of the inventory's registered recurring charges
under a stated rule (items not in `disconnected` state bill).
That is deterministic arithmetic over records the functions
presuppose — the data-management sibling groups' quality-run
pattern — not reconciliation AI: matching a bill line-by-line
against carrier feeds is the integration engine, Extended.
(3) *Projections.* Recorded verbatim when a caller supplies one;
never computed. A forecast produced by the build would be an
engine wearing a record's clothes. (4) *Fulfillment side
effects.* An inventory item's provisioning state changes only
when a service order is fulfilled, per a fixed mapping stated in
the spec (suspend → suspended, restore/new/macd/port → active,
disconnect → disconnected). Those are registry mechanics of the
substrate, recorded as such — no carrier is contacted, ever;
the carrier-facing execution of an order is Extended.
(5) *Money.* Amounts are integer cents throughout, floats
rejected at the boundary, under the house money discipline.
Bills, budgets, and chargebacks are records; no payment moves.

## The Core — what the merged build implements (14 functions)

One coherent, standards-based telecom expense / managed mobility
records service that the fork's claimed functions presuppose,
built clean-room from this spec:

1. **Customer organizations & membership** — customer
   organizations (`org-`): an opaque caller-supplied `ref` and a
   label, an owner, and a member list. Membership is the
   boundary every other core function enforces.
2. **Telecom service inventory** — inventory items (`inv-`) for
   wireline, mobility, and other telecom services: an opaque
   service `ref` (unique per organization), a `plan_ref`, and a
   monthly recurring charge in integer cents. The record shape
   is **pinned** — exactly ten keys, none of which can hold a
   phone number, IMEI, serial, or any real device identifier.
   An item's provisioning state (`active`/`suspended`/
   `disconnected`) changes only through fulfilled orders.
3. **Service order records & lifecycle** — orders (`ord-`) of
   the description's own types (`new`, `macd`, `port`,
   `suspend`, `restore`, `disconnect`) with the lifecycle
   `requested → approved → fulfilled`, plus `rejected` and
   `cancelled`. Two seams are enforced in the store: the decider
   is never the requester (**separation of duties**), and
   fulfillment is the only event that moves a linked item's
   provisioning state, per the mapping in boundary decision (4).
4. **Workflow definition registry** — workflow definitions
   (`wfl-`: ordered step names) registered as data per
   organization. The registry **never executes** a definition —
   registering one changes no order and no item, ever, pinned
   by test. The routing/execution engine is Extended.
5. **Contract & quote registries** — contracts (`con-`) by
   opaque `ref` with a term window, and quotes (`quo-`) recorded
   against a contract (optionally an item) with an amount in
   integer cents — the records bill validation verifies against.
6. **Bill records & validation runs** — bills (`bil-`) by period
   (`YYYY-MM`) with a stated total in integer cents, and
   validation runs (`val-`) recording the stated total, the
   expected total computed from the inventory registry under the
   stated rule, the variance, and the result (`match`/
   `variance`). A run never modifies the bill.
7. **Dispute records & lifecycle** — disputes (`dis-`) on a
   bill: the disputed amount, the reason verbatim, and the
   lifecycle `open → in_progress → resolved` with the
   resolution recorded verbatim. A dispute can never exceed the
   bill it disputes — checked before anything is stored, so a
   rejected dispute consumes no id and changes nothing.
8. **Budget records, obligations & derived availability** —
   budgets (`bud-`), one per organization and period, with a
   budget in integer cents and an optional caller-supplied
   projection recorded verbatim; obligations (`obl-`) record
   `obligated` and `spent` amounts. Obligated, spent, and
   available (= budget − obligated − spent) are **derived at
   read** and never stored — the stored budget record carries
   no such key, pinned by test.
9. **Chargeback records** — internal customer chargebacks
   (`chg-`) against a budget: an opaque unit reference and an
   amount in integer cents.
10. **Budget alert records** — alerts (`alr-`) by kind
    (`budget_threshold`/`budget_projection`/`general`) with a
    message and an acknowledgement record. Alerts are recorded;
    delivery is Extended.
11. **Search & summary reporting** — literal case-insensitive
    substring search over accessible organizations, inventory,
    orders, bills, and contracts; and a per-organization summary
    computed on read from records only: inventory counts by
    kind and state, order counts by status, bill totals,
    dispute counts and open disputed cents, per-budget derived
    figures, chargeback totals, unacknowledged alert counts.
    Counts and sums — never scores.
12. **API access** — every function above is exposed over a
    REST API (JSON), so the service composes with anything that
    speaks HTTP.
13. **Access control** — role-based access hooks: platform
    roles `admin`, `member`, `viewer` with a permission matrix
    enforced on every operation, layered with organization
    membership (non-members cannot read or write an
    organization's content; the platform `admin` role can).
14. **Audit log** — an append-only audit trail: every
    organization, membership, inventory, order, workflow,
    contract, quote, bill, validation, dispute, budget,
    obligation, chargeback, and alert mutation, and every
    denied attempt, recorded with actor, action, target, and
    UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to
  the 110 practices of NIST SP 800-171 Rev. 2 that define CMMC
  L2. The single parent fork sits at Moderate, so the baseline
  is the Moderate baseline, un-diluted (Merge Rule 1) and
  inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + organization membership)
    → **AC** (AC-2 account management, AC-3 access enforcement,
    AC-6 least privilege), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the service ships
    hooks, not an identity provider).
  - Order decisions → **AC-5** (separation of duties — the
    decider of an order is never its requester, enforced in
    the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of
    audit records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to
    the `audit_read` permission).
  - Inventory / orders / bills / budgets → **SI** (SI-10
    information input validation — malformed input, including
    any non-integer amount, a malformed period, or a dispute
    exceeding its bill, is rejected whole, never partially
    applied) and **SC** (SC-8 transmission confidentiality —
    the server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
  - Opaque-reference privacy is a build discipline answering
    to the same input discipline: because no entity shape has
    a field for a real personal, device, or financial
    identifier, none can be stored, leaked, or transmitted by
    this build. It is stated as a discipline, not dressed up
    as an additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states
  which baseline families the build's features answer to. It
  is not a FedRAMP authorization and not a CMMC certification,
  and it does not claim either. FedRAMP authorizes products;
  CMMC certifies organizations; the tier is a planning and
  matching equivalence, never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `mdm` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential
per object type with fixed prefixes (`org-`, `inv-`, `ord-`,
`wfl-`, `con-`, `quo-`, `bil-`, `val-`, `dis-`, `bud-`, `obl-`,
`chg-`, `alr-`); a failed operation consumes no id and changes
nothing. Amounts are integer cents; a bool, float, or string
amount raises `ValidationError`. A budget's obligated, spent,
and available values are derived at read and never stored.

- `mdm/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read,
  create_org, enter, decide, record, manage_members,
  audit_read, admin}, member = {read, create_org, enter,
  decide, record}, viewer = {read}; `require(user, action)`
  raises `PermissionDenied`.
- `mdm/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `mdm/store.py` — `MdmStore(audit=None)` with the operations
  named in the Core above. Organization-scoped operations
  enforce membership (or platform admin) and, for User-like
  actors, the role permission for the operation's action. The
  store audits every successful mutation; the service layer
  audits denied attempts (`action:denied`) and audit reads, so
  nothing is recorded twice. Named seams: `_available_cents`
  (the availability derivation) and `_check_dispute_within_bill`
  (the dispute cap).
- `mdm/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  Endpoints per the group README. Errors are JSON `{error}`
  with 400/401/403/404 as applicable. Denied attempts are
  audited.
- `mdm/__main__.py` — `python -m mdm serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding
  organization's).
- `mdm/errors.py` — `MdmError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. **75 tests**, including the **negative
control**: a mutant store whose availability derivation returns
the bare budget is shown to violate the canonical expectation —
and the external mutation drill (patching `_available_cents`
in the real `store.py` to return the bare budget) makes exactly
4 tests fail; see `tests/README.md` for the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

From this fork's own claims (the engines behind the records):

- Optimization engine (named from the product's name; no
  description sentence claims an optimization function)
- Workflow execution / routing engine (the registry holds
  definitions only)
- Carrier & network integration engines (carrier ordering
  execution for MACD/port/suspend/restore, carrier bill feeds,
  contract/quote data integration — the data-integration claim)
- Bill reconciliation engine beyond registry validation runs
  (line-level matching against carrier data)
- Budget projection / forecasting engine (projections are
  recorded verbatim, never computed)
- Analytics engine beyond registry summaries (spending
  insights, anomaly detection)
- Report generation engine (ad-hoc reports, dashboards,
  exports)
- Alert delivery transport (email / SMS / push; alerts are
  recorded, not delivered)
- Web portal / single-pane web application (the browser UI
  itself)
- Managed Mobility services operations (the human/service
  operations the fork's MM offering wraps around the system)

From the category's named absences (not claimed by this fork;
registered so the category surface is named, not missing):

- Mobile device enrollment & provisioning plane
- Remote wipe / lock / device command plane
- Device policy management & compliance enforcement
- Mobile application management (catalog, distribution,
  wrapping)
- Device location & tracking services

Platform-layer: encryption at rest is deployment-layer (TLS
when configured); multi-tenancy (the fork asserts a multi-tenant
architecture of its hosting platform; this build is a
single-tenant reference deployment); demo identities are hooks,
not an IdP (IA-2 stays with the embedding organization).

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **16 tagged claims** (one
  per taxonomy family, each with its source sentence as
  evidence; the taxonomy was defined from the fork's own
  description).
- Core: **14 / 14** core functions implemented, at the
  Moderate/L2 baseline, each with tracing tests.
- Tests: **75 run, 75 passed**, including the mutation-verified
  derived-availability negative control.
- Extended: the 15 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
