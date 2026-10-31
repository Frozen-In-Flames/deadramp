# Union Spec — Enterprise Resource Planning, CMMC L2 (DeadRamp Phase 2 remainder, ERP L2 singleton)

The singleton spec for the **Enterprise Resource Planning**
category at the L2 tier: **1 fork**, a category with no shipped
group at any tier — **Infor Government Solutions (IGS) Software
as a Service** (Infor), FedRAMP **Moderate**, FedRAMP Certified,
SaaS, Government Community Cloud. Built under the remainder
census's **no-signal resolution**: this fork sat in census unit
`no-signal-set`, and its category comes from the live-docs
research pass, not from the marketplace record.

**Membership provenance, stated plainly:** `forks.json` files
this fork "Uncategorized (none in source)" at tier L2 — its
source record carries an empty `business_categories` list, and
the census could cite no function sentence for it from its
marketplace description (census: citations [], `no_signal`
"prose_only", classifier note: "Integrated multi-suite ERP
bundle spanning finance, supply, manufacturing, HCM, asset
management and analytics with no single primary function"). The
DeadRamp category is the **no-signal resolution's proposal**
("Enterprise Resource Planning"; `remainder/nosignal_report.json`,
status resolved, new category), taken from the vendor's own
suite-level sentence on its own brochure page: "Infor Government
Solutions offers a comprehensive suite of 20+ fully integrated
business applications." That sentence and its source URL are
recorded on the spec sheet as `classification_evidence` /
`classification_source_url` — the classification citation, kept
distinct from claim evidence. Reconciliation: census no-signal
set ∋ FR1710033970 == `specs/specs.json` == {FR1710033970}, and
the fork's own recorded fields (Moderate, FedRAMP Certified, L2)
match the source record exactly. This group's number is assigned
in the repo README at ship; this spec deliberately carries none.

**The suite-level framing decision, stated plainly (recorded
once, here):** the description's components span the ground of
the existing Finance, Human Resources, and Operations Management
categories. The category assignment does **not** split the fork
across them. The vendor frames one integrated offering —
"composed of integrated cloud application suites" (description
sentence 1) and "a comprehensive suite of 20+ fully integrated
business applications" (classification sentence) — and the census
classifier independently recorded "no single primary function".
The assignment therefore rests on the vendor's own framing of
the suite as one integrated offering, at exactly that weight. No
taxonomy family below is imported from Finance, Human Resources,
Operations Management, or any other category; every pattern is
this fork's own phrasing.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID **FR1710033970**.
The cached description is byte-identical to
`remainder/uncovered.json`'s description for this fork (asserted
in the extractor).

## How functions were counted (a new category: the Group 1 method)

Enterprise Resource Planning has no parent group, so there is no
inherited taxonomy. The taxonomy below was defined **from this
fork's own words**: families named from the description's own
functional vocabulary, each with a verbatim match pattern,
matched against the description's sentences by
`scratch/extract.py`. Derivation sources, recorded per family in
`scratch/ARTIFACTS.md`: (a) the fork's cached marketplace
description — the source for 23 of 24 families; (b) the
classification sentence — an additional derivation source for
`integrated_application_suite` only. **Claims run on the cached
description alone**: a function is claimed only when a
description sentence contains matching text, and the first
matching sentence is stored as the claim's evidence. The
classification sentence is never claim evidence — it does not
occur in the description at all (asserted in the extractor,
pinned in the spec tests). Marketing prose gets no tags.
**24 claims in total, one per family** — the single fork claims
every family its own vocabulary defines. Counts are a **floor**,
not a ceiling.

The patterns are anchored, where a suite component exists, to
that component's own section sentence, which produces the
corrections that matter (full log in `scratch/ARTIFACTS.md`):
the capabilities-list sentence (sentence 2, naming Financial &
Supply Management, Manufacturing ERP, Human Capital Management,
Asset & Maintenance Management, Business Intelligence &
Analytics in one breath) tags **nothing** — it corroborates the
suite's span but is stored as evidence for no claim; the
hosting/compliance paragraph (sentences 3–7: GovCloud hosting,
ITAR/FedRAMP/CJIS/SRG posture, NIST categorization, HIPAA)
tags nothing, and no hosting family exists in this taxonomy
(the Energy Management singleton's discipline) — deployment and
compliance facts are record fields, not claims; feature-list
phrases inside component sentences (materials and inventory,
project management, product lifecycle management, quality
management, contract management, advanced planning and
scheduling, track and trace) are not carved into families —
contract management in particular names another DeadRamp
category's centre (Remainder Group 1) and occurs only inside a
feature list; the Asset & Maintenance section's opening sentence
names a partner product (Hexagon's EAM) under the offering's own
section header, and the asset claim rests on that sentence as
the fork's own description text; outcome prose (sentence 19),
quality-attribute prose (sentence 8), and the BI paragraph's
"auditing features and granular user access controls" (sentence
55) tag nothing. The source record's `certified_services` is
empty and no sentence is a scope-exclusion sentence, so **raw
hits == claims, 24 == 24**. The classification sentence's "20+"
is the vendor's brochure figure, not verified against the
description (which names fewer distinct components) — recorded
at brochure weight.

**Census citation accounting:** the census recorded **zero
citations** for this fork, so there was nothing to re-verify and
the classification rests on the live-docs citation alone. That
is the honest position for a no-signal fork: the marketplace
text classifies nothing; the vendor's own brochure sentence
classifies the suite; the claims rest on the marketplace text
itself.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---|---|
| 1 | Integrated application suite | 1 | **Core** (records) — the application registry; the suite platform itself is Extended |
| 2 | Federated security & single sign-on | 1 | **Core** (records) — access configuration records; the federation service itself is Extended (IA-2) |
| 3 | Role-based access authorization | 1 | **Core** — the build's own RBAC matrix, plus the access configuration records |
| 4 | Enterprise portal & collaboration | 1 | **Extended** — the portal presentation surface |
| 5 | Configurable homepages & widgets | 1 | **Extended** — the homepage/widget presentation layer |
| 6 | Integration & process orchestration (iPaaS) | 1 | **Core** (records) — the integration registry; the orchestration runtime is Extended |
| 7 | API gateway & policy management | 1 | **Core** (records) — `api_gateway` registry records; the gateway runtime is Extended |
| 8 | Document management | 1 | **Core** (records) — document metadata records; capture/conversion machinery is Extended |
| 9 | Data lake & metadata management | 1 | **Extended** — the schema-on-read data lake engine |
| 10 | Financial management (general ledger) | 1 | **Core** — general-ledger records under the balanced-entry rule; the close/consolidation engine is Extended |
| 11 | Supply management (source-to-settle) | 1 | **Core** (records) — purchase order records; matching/payment execution is Extended |
| 12 | Expense management | 1 | **Core** — expense report records; policy enforcement & fraud detection engines are Extended |
| 13 | Manufacturing ERP | 1 | **Core** (records) — inventory records; the production engine is Extended |
| 14 | Supplier collaboration exchange | 1 | **Extended** — the live supplier exchange (demand/ASN publishing) |
| 15 | Human capital management | 1 | **Core** — the person/time/payroll records below are its records form |
| 16 | Core HR & person system of record | 1 | **Core** — person records (opaque references, pinned shape) |
| 17 | Talent management | 1 | **Extended** — the talent workflow engine (identify/hire/develop/reward/retain) |
| 18 | Workforce management | 1 | **Core** (records) — time & absence records; the demand-driven scheduling optimizer is Extended |
| 19 | Payroll | 1 | **Core** (records) — payroll run records; the pay calculation engine is Extended |
| 20 | Asset management | 1 | **Core** — asset records (caller-stated labels; no computed condition) |
| 21 | Maintenance management & work orders | 1 | **Core** — work order records with a recorded lifecycle |
| 22 | Business intelligence & analytics | 1 | **Extended** — the BI platform (dashboards, semantic layer, warehouse automation) |
| 23 | Enterprise performance management (planning & forecasting) | 1 | **Extended** — the planning/forecasting/consolidation engine |
| 24 | Governance, risk & compliance | 1 | **Extended** — the GRC engine (risk workflows, permission verification) |

**Named absences, stated plainly (token-verified; full list in
`scratch/ARTIFACTS.md`):** the description never says
**"enterprise resource planning"** — the category's own full name
occurs zero times (the words are "Manufacturing ERP", "Infor ERP
solutions", "manufacturing ERPs", "an end-to-end ERP solution");
the category rests on the suite framing, not on the phrase.
There is **no CRM or customer-relationship vocabulary, no sales
order or order management vocabulary, no tax vocabulary, no
budgeting vocabulary** (d/EPM plans and forecasts; the word
"budget" never occurs), **no grants vocabulary, no training
vocabulary, no e-commerce, help-desk, point-of-sale, treasury, or
reconciliation vocabulary, and no scoring vocabulary**. **No
amount, rate, or fee figure is stated anywhere** ("fee" occurs
once, inside "feedback"): the core's money records carry
caller-recorded integer cents and rest on the ledger /
receivables / payables / cash / expense / payment / payroll
function words, not on any stated figure. None of the absences
is a gap in the registry sense: nothing was claimed, so nothing
is owed.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *Records, not engines.* Every Core disposition
above is the records form of the claimed function: registries,
ledger entries, orders, reports, person/time/payroll records,
asset and work-order records, inventory and document records.
The engines the fork names — orchestration, gateways, close
processes, production, scheduling optimization, pay calculation,
BI, planning, GRC — are Extended, each named as a gap. (2)
*Balance is a rule, not a review.* A ledger entry's balance is
decided by a single seam over recorded values, not by a person's
judgment, which is why no separation-of-duties claim arises from
it (see precision notes). (3) *Totals are derived, never
stored.* Purchase-order and expense-report totals are computed
at read from their lines; the stored shapes carry no total key,
pinned by test. (4) *People and documents are references and
metadata.* A person record holds an opaque reference and two
labels — no field can hold a name or any real identifier; a
document record holds metadata — no field can hold content.
Both shapes are pinned and recursively scanned in the tests.
(5) *Registries never execute.* Integration, workflow, and
access-configuration records describe connections, processes,
and identity configuration; recording one performs none of them.
The no-execution property is pinned structurally: the store
exposes no run/fire/execute/connect operation at all. (6) *No
hosting claim.* The fork's GovCloud/ITAR/JAB posture is its own
platform property (see the traceability precision notes); this
build claims no hosting or compliance property of the fork's.

## The Core — what the merged build implements (17 functions)

One coherent, standards-based enterprise-suite records service
that the fork's claimed functions presuppose, built clean-room
from this spec:

1. **Organization registry (opaque references)** — organizations
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier.
2. **Application registry** — applications (`app-`) registered
   per organization with a suite label and an active/inactive
   lifecycle. Records only: registering an application installs
   nothing and runs nothing.
3. **Access configuration records** — records (`acc-`) naming,
   per organization, the identity provider and multi-factor
   arrangement the suite federates with, each by caller-stated
   label. Records only: this authenticates no one; identity
   itself stays with the embedding organization (IA-2).
4. **General ledger records (the signature invariant)** —
   entries (`led-`) of debit/credit lines against opaque
   account references, in integer cents (booleans, floats, and
   strings rejected at the boundary). An entry is recorded only
   when the single seam `_check_entry_balanced` accepts it:
   every line one-sided, total debits equal total credits, total
   positive. An unbalanced entry is refused whole — nothing is
   recorded and no id is consumed. Entry views carry the derived
   debit/credit totals; the stored record carries no total keys.
5. **Procurement records** — purchase orders (`po-`) against
   suppliers named by opaque reference, with quantity /
   unit-price lines in integer cents, an `open → received →
   closed` recorded lifecycle, and the order total derived at
   read, never stored.
6. **Expense records** — expense reports (`exp-`) for a person
   record, with categorized amount lines in integer cents, the
   total derived at read, and a recorded-outcome lifecycle
   (`submitted → approved` / `submitted → rejected`, terminal).
7. **Person records (the system of record)** — records (`per-`)
   holding an opaque `person_ref` (unique per organization), a
   department label, and a role label. The shape is pinned: no
   field can hold a name, email, phone number, or any real
   identifier.
8. **Time & absence records** — time entries (`tim-`: a date and
   whole minutes, integers only) and absence records (`abs-`: a
   kind label and an inclusive date range) for a person record.
9. **Payroll run records** — runs (`pay-`) recording a period
   label and a caller-recorded gross amount in integer cents.
   No pay calculation, job costing, or disbursement is
   performed; the calculation engine is Extended.
10. **Asset records** — assets (`ast-`) with an opaque reference,
    a label, and a caller-stated criticality label (a label,
    never a computed assessment).
11. **Work order records** — work orders (`wo-`) against an
    asset, in the fork's own kind vocabulary (`preventive`,
    `corrective`), with a recorded lifecycle (`open → assigned
    → completed`; `completed` terminal; assignees by opaque
    reference).
12. **Inventory records** — items (`inv-`) with integer
    quantities on hand that change only through recorded
    adjustments and may never go negative.
13. **Document records** — records (`doc-`) of business
    documents: an opaque reference, a label, a business-purpose
    label. Metadata only — the pinned shape has no field that
    could hold content.
14. **Integration & workflow registries (records only)** —
    integration records (`int-`) of kinds `integration_platform`
    and `api_gateway`, and workflow records (`wfl-`) naming a
    process and its trigger by label. Neither registry executes
    anything (decision 5).
15. **Search & summary reporting** — literal case-insensitive
    substring search over organizations, applications, persons,
    assets, and documents; and a summary computed on read from
    records only: registry counts and by-status / by-kind
    breakdowns. Counts and recorded values — never scores.
16. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that
    speaks HTTP.
17. **Access control & audit log** — role-based access hooks:
    platform roles `admin`, `operator`, `viewer` with a
    permission matrix enforced on every operation; and an
    append-only audit trail recording every mutation and every
    denied attempt, with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability) — Moderate / L2

- **Singleton tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (this
  fork's impact level, recorded as-is) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to
  the 110 practices of NIST SP 800-171 Rev. 2 that define CMMC
  L2. One fork at one tier, so no merge changes the tier (Merge
  Rules 1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the
  Moderate baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Organization, application & access-configuration registries | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness and integer validation are enforced in the store; identity itself is supplied by the embedding organization |
| General ledger records | AU-2, AU-3, CM-6, SI-10 | Entries validate at the boundary (integer cents) and record only through the single balance seam, so the gate and the derived totals can never disagree; every recording is audited |
| Procurement & expense records | AU-2, AU-3, SI-10 | Lines validate at the boundary; totals are derived at read from the recorded lines; outcomes and transitions are recorded actions with actor and timestamp |
| Person, time, absence & payroll records | AU-2, AU-3, SI-10 | Person shapes are pinned to references and labels (no identifier can be stored); minutes and cents are integers, validated on write; person-linked records require the person record to exist in the same organization |
| Asset, work-order & inventory records | AU-2, AU-3, CM-6 | Lifecycles change only through recorded actions; quantities are integers and cannot go negative; criticality is a caller-stated label, never computed |
| Document records | AU-2, AU-3, SI-10 | Metadata records validated on write; the pinned shape admits no content |
| Integration & workflow registries | CM-6, AC-3 | Configuration-controlled records; the registries perform no connection and no execution — pinned structurally by test |
| Summary reporting & search | AU-2, AU-3; AC-3 | Deterministic counts over the records; literal search over registered metadata only, permission-gated |
| RBAC | AC-2, AC-3, AC-6, IA-2 (hooks) | Three-role matrix enforced before any mutation or id allocation, at the store and again at the service layer; `audit_read` is admin-only |
| Audit log | AU-2, AU-3, AU-6, AU-9 | Append-only log including denied attempts; no mutation API; audit reads are restricted to the `audit_read` permission and are themselves audited at the service layer |

- **Precision notes (what Moderate does and does not carry,
  stated so nothing is silently imported from other tiers'
  tables):**
  - **Audit:** AU-2/AU-3/AU-6/AU-9 are Moderate selections and
    are claimed as above: append-only storage (AU-9) and a
    restricted, itself-audited read path (AU-6). Hash-chained
    audit, fail-closed audit writes, audit query/reduction
    (AU-7), logon lockout (AC-7), and a separate auditor role
    are High answers from sibling groups and are **not** claimed
    here.
  - **Separation of duties:** no AC-5 claim arises. Ledger
    balance is decided by a derivation over recorded values,
    not by a person; expense outcomes and order transitions are
    recorded actions by named actors, visible in the trail.
  - **Identity:** the fork's federated security (SSO/MFA) is
    its platform property. This build records federation
    *configuration* (labels) and enforces its own role matrix;
    it operates no identity provider and claims no IA-2
    satisfaction — identity stays with the embedding
    organization, as in every DeadRamp build.
  - **Platform posture:** the fork's GovCloud hosting, ITAR,
    CJIS, DoD SRG, HIPAA, and NIST SP 800-171 statements are
    the fork's own properties, recorded on its spec sheet as
    record data. They do **not** transfer to this build, and no
    SC-13 (cryptographic protection) claim is made: this build
    performs no cryptography. Transmission holds only when a
    certificate is configured (`--certfile`/`--keyfile`); the
    default serve mode is plain HTTP for local/demo use, and
    encryption at rest is a deployment-layer control, stated
    plainly and not claimed here.
- **Caveat (standing, from crosswalk.md):** this traceability
  is a planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the
  Moderate/L2 control families. FedRAMP authorizes products;
  CMMC certifies organizations — neither regime accepts the
  other as evidence, and any real compliance claim still has to
  be earned inside each regime separately.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `erp` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential
per object type with fixed prefixes (`org-`, `app-`, `acc-`,
`led-`, `po-`, `exp-`, `per-`, `tim-`, `abs-`, `pay-`, `ast-`,
`wo-`, `inv-`, `doc-`, `int-`, `wfl-`); a failed operation
consumes no id and changes nothing. Amounts, minutes, and
quantities are integers; a bool, float, or string where an
integer is required raises `ValidationError`. Totals over lines
are derived at read and never stored; event-driven lifecycle
state (an expense outcome, an order's receipt state, a work
order's assignment state, a registry record's active/inactive)
is stored, as in the sibling builds' record lifecycles.

- `erp/access.py` — `User(name, role)`; roles
  `admin|operator|viewer`; `PERMISSIONS`: admin ⊇ {read,
  register, record, approve, audit_read, admin}, operator =
  {read, register, record, approve}, viewer = {read};
  `require(user, action)` raises `PermissionDenied`.
- `erp/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `erp/store.py` — `ErpStore(audit=None)` with the operations
  named in the Core above. Role permission is enforced for
  User-like actors before any state change or id allocation; a
  plain-string actor carries identity only, and enforcement for
  those happens in the service layer (the sibling builds'
  convention). The store audits every successful mutation; the
  service layer audits denied attempts (`action:denied`) and
  audit reads, so nothing is recorded twice. The balance rule
  lives in the single seam `_check_entry_balanced(lines)`.
- `erp/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  Endpoints per the group README. Errors are JSON `{error}` with
  400/401/403/404 as applicable. Denied attempts are audited.
- `erp/__main__.py` — `python -m erp serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=operator, carol=viewer` (documented as demo
  identities; production identity is the embedding
  organization's).
- `erp/errors.py` — `ErpError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**:
an in-tree mutant seam under which every ledger entry
"balances", so unbalanced entries record — if the suite passed
against it, the ledger tests would be testing that code ran, not
that balance is enforced — plus the external mutation drill (the
same patch applied to the real `store.py`); see `tests/README.md`
for the counts and the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Suite platform & portal presentation layer (the enterprise
  portal surface and the homepages/widgets rendering; this build
  keeps the application registry records)
- Identity federation service (the SSO/MFA provider itself;
  this build keeps configuration records, and identity stays
  with the embedding organization)
- Integration execution & orchestration runtime (the ION
  runtime: event processing and end-to-end process execution;
  this build keeps the registry records)
- API gateway runtime (live API routing, discovery, policy
  enforcement, and throttling; this build keeps the registry
  records)
- Data lake & schema-on-read engine (the data consumption
  framework and metadata management service; this build holds
  record metadata, not a data lake)
- Financial close & consolidation engine (the single close
  process, matching, and consolidation; this build keeps the
  ledger records)
- Source-to-settle execution engine (procurement matching and
  payment execution; this build keeps the order records)
- Expense policy enforcement & fraud detection engine (policy
  compliance checks and error/fraud detection over reports;
  this build keeps the report records and their outcomes)
- Manufacturing production engine (production execution,
  advanced planning & scheduling, product configuration, product
  lifecycle management, shop-floor automation and warehouse
  mobility; this build keeps the inventory records)
- Supplier exchange network (live demand and Advance Ship
  Notice publishing and supplier collaboration; this build
  names suppliers by opaque reference only)
- Talent management engine (identify / hire / develop / reward
  / retain workflows; this build keeps the person records)
- Workforce scheduling optimizer (demand-driven and
  workforce scheduling; this build keeps the time and absence
  records)
- Payroll calculation engine (pay computation, job costing, and
  disbursement; this build keeps the run records)
- Business intelligence platform (reporting, dashboards,
  semantic data layer, data warehouse automation; this build's
  reporting is counts over its own records)
- Enterprise performance management engine (planning,
  forecasting, and in-memory consolidation)
- Governance, risk & compliance engine (risk mitigation
  workflows and user-permission verification; this build's
  audit trail is its own substrate property, not the fork's
  GRC product)

Platform-layer: the fork's GovCloud hosting and its ITAR /
CJIS / DoD SRG / HIPAA posture are the fork's platform
properties and do not transfer; FIPS-validated cryptography
(SC-13) is not claimed by this build; encryption at rest is
deployment-layer (TLS when configured); multi-tenancy
(single-tenant reference deployment); demo identities are
hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **24 tagged claims** (one
  per taxonomy family, each with its source sentence as
  evidence), plus the classification citation recorded on the
  sheet at brochure weight.
- Core: **17 / 17** core functions implemented, at the
  Moderate/L2 baseline, each with tracing tests.
- Tests: see `tests/README.md` for the count (filled in from
  the build, not stated here), including the mutation-verified
  balanced-entry negative control.
- Extended: the 16 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
