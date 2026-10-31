# Union Spec — Energy Management, CMMC L1 (DeadRamp Phase 2 remainder, Energy Management L1 singleton)

The singleton spec for the **Energy Management** category at the
L1 tier: **1 fork**, brand-new category (the remainder census
proposed it for this fork; no group exists at any other tier) —
**Exchange Platform** (Enel X North America), FedRAMP **LI-SaaS**,
FedRAMP Certified, SaaS, Public Cloud. Built under the remainder
census unit `new-singleton:Energy Management|L1`.

**Membership provenance, stated plainly:** `forks.json` files this
fork "Uncategorized (none in source)" at tier L1 — its source
record carries an empty `business_categories` list. The DeadRamp
category is the **remainder census proposal**, taken from the
fork's own description: its primary function is energy procurement
via reverse auction for energy supply, a function none of the 36
Phase 1 categories covers. Reconciliation: `remainder.json` unit
== `specs/specs.json` == {FR2014363920}, zero diff, and the fork's
own recorded fields (LI-SaaS, FedRAMP Certified, L1) match the
source record exactly. MAP.md's category arithmetic is unaffected:
this fork was never in MAP.md's category counts, because MAP.md
counts the Phase 1 category field. This group's number is assigned
in the repo README at ship; this spec deliberately carries none.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **FR2014363920**.

## How functions were counted (a new category: the Group 1 method)

Energy Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching
text; the first matching sentence is stored as the claim's
evidence in the spec sheet. Marketing prose gets no tags. **9
claims in total, one per family** — the single fork claims every
family its own vocabulary defines. Counts are a **floor**, not a
ceiling.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
sentence 1's "focuses on enabling... best price" is positioning
prose and tags nothing (the auction function is claimed from the
mechanism named in the same sentence); sentence 3's "increasing
liquidity and driving down price" is market-effect prose and tags
nothing; sentence 4's consulting framing tags nothing while each
named service is its own family; sentence 5's "automated" is
recorded at artifact weight (alert records claimed, the trigger
engine Extended); sentence 6's "market intelligence updates" is
booked once, under market-update notifications, not double-booked
as intelligence. The description carries **no hosting or cloud
language at all**, so this taxonomy — a deliberate contrast with
sibling groups — has no hosting-platform family; "SaaS" and
"Public Cloud" are source-record fields, not claims.

**Census citation accounting:** both census citations verify as
strict verbatim substrings of the description (2/2), and both are
also claim-bearing sentences for `reverse_auction` — citation 1 is
the stored evidence sentence and citation 2 carries the family's
second pattern hit. Verification and claiming coincide here,
recorded as the coincidence direction; no citation was
load-bearing, because every claim rests on the description itself.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Reverse auction conduct | 1 | **Core** — the substrate itself (auction & bid records, outcome derivation) |
| 2 | Energy provider choice (de-regulated markets) | 1 | **Core** (records) — the provider registry and auction participation records are its records form; choice itself is a market property, not a build function |
| 3 | Budgeting consulting | 1 | **Core** (records) — advisory engagement records; the advice itself is Extended |
| 4 | Market intelligence | 1 | **Core** (records) — engagement records; the intelligence engine is Extended |
| 5 | Risk management consulting | 1 | **Core** (records) — engagement records; the advice itself is Extended |
| 6 | Price-change trigger alerts | 1 | **Core** (records) — subscription & alert records; the trigger-evaluation engine and delivery are Extended |
| 7 | Contract change notifications | 1 | **Core** (records) — alert records; delivery transport is Extended |
| 8 | Market update notifications | 1 | **Core** (records) — alert records; delivery transport is Extended |
| 9 | Customer price charts | 1 | **Core slice** — price-observation records and on-read series summaries; chart rendering is Extended |

**Named absences, stated plainly (token-verified; full list in
`scratch/ARTIFACTS.md`):** the description contains **no demand
response, curtailment, EV-charging, storage, renewables, carbon,
efficiency, metering, consumption, billing, or grid-services
vocabulary at all**. The vendor is widely known for several of
those businesses; none of them is in this offering's marketplace
description, and reputation is not evidence. None of the absences
is a gap in the registry sense: nothing was claimed, so nothing is
owed. The category as this fork's own words define it is **energy
supply procurement** — a reverse auction, the provider choice it
operationalizes, advisory services around it, and the alerts and
price information surrounding it.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *Prices.* Bids and price observations carry a
price as record fields — an auction record without its bids'
prices, and a price series without prices, are not meaningful —
under a strict form of the house money discipline: prices are
**integers** (cents per the auction's stated unit), and any
non-integer price (floats and booleans included, even integral
floats) is rejected at the boundary. No payment, settlement, or
billing function is claimed or built; the winning bid is a record
selection, and paying on it is Extended. (2) *The outcome is a
derivation, not a score.* The auction outcome selects the lowest
recorded bid — a minimum over recorded values, exactly the class
of on-read computation the sibling builds perform with sums and
counts. It is **derived at read and never stored**, and it is not
a score, rating, or ranking of any provider: the build returns the
single winning selection the auction itself defines, plus counts,
and deliberately produces no provider leaderboard. No record shape
carries a score field — pinned by test. (3) *Alerts are records.*
The claimed alert functions presuppose subscriptions and issued
alerts as records; both are Core. The engine that watches prices
and fires alerts on a trigger, and every delivery transport, are
Extended — the build records alerts, it does not send them, and
it does not evaluate triggers. (4) *Nothing physical.* The build
holds records about energy procurement. It operates no grid,
charging, building, or metering system, and no record in it can
actuate anything; that boundary is stated here and in the README,
not left implicit.

## The Core — what the merged build implements (12 functions)

One coherent, standards-based energy-procurement records service
that the fork's claimed functions presuppose, built clean-room
from this spec:

1. **Customer registry (opaque references)** — customers (`cust-`)
   known only by a caller-supplied opaque `ref` and a label. The
   record shape is pinned: no field can hold a real identifier.
2. **Provider registry (opaque references)** — energy providers
   (`prov-`) under the same pinned shape and discipline.
3. **Auction records** — auctions (`auc-`) opened for a customer:
   commodity and region as caller-stated text, a unit label, a
   contract quantity in whole units, and an `opens_at`/`closes_at`
   window. An auction's status (`upcoming`/`open`/`closed`) is
   **derived at read** from the window (and any recorded early
   close) against the read clock — never stored. An operator may
   record an early close; after that the derived status is
   `closed` at any clock.
4. **Bid records** — bids (`bid-`) by a provider on an auction,
   each carrying an integer price in cents per the auction's unit
   and a store-assigned sequence. Bids are recorded **only while
   the auction is open** (derived at the bid's moment) and are
   immutable once recorded: there is no update or delete.
5. **Outcome derivation (the signature invariant)** — the auction
   outcome is computed on read from the bid records alone: bid and
   provider counts, the lowest price, and the winning bid —
   lowest price, ties broken by earliest sequence. **No outcome
   field is ever stored** on the auction record. Before the
   auction closes the derived winner is provisional; the outcome
   view states the derived status alongside, and `is_final` marks
   a closed auction's outcome as final.
6. **Price-observation records** — observations (`obs-`) of a
   price for a caller-stated region and commodity at a moment:
   integer cents per unit. These are the records price charts are
   drawn from; the latest observation per series is derived at
   read. Rendering is Extended.
7. **Alert subscriptions** — subscriptions (`sub-`) by a customer
   to a notification kind (`price_change`, `contract_change`,
   `market_update`), with an optional integer price threshold and
   optional region/commodity filters. A subscription is created
   active and may be deactivated by a recorded action.
8. **Alert records** — alerts (`alrt-`) issued to a customer, by
   kind, with a caller-stated subject, optionally linked to the
   subscription they arose under. Recorded, never delivered;
   delivery transport and trigger evaluation are Extended.
9. **Advisory engagement records** — engagements (`eng-`) of the
   three claimed consulting kinds (`budgeting`,
   `market_intelligence`, `risk_management`) for a customer, with
   the engagement note stored verbatim and an event-driven
   lifecycle (`open → closed`). The advice itself is Extended;
   what is Core is the engagement record.
10. **Search & summary reporting** — literal case-insensitive
    substring search over customers, providers, auctions, and
    engagement notes; and a summary computed on read from records
    only: registry counts, auctions by derived status, bid and
    observation counts, latest price per series, active
    subscriptions, alerts by kind, engagements by kind and
    status. Counts, sums of counts, and recorded prices — never
    scores.
11. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
12. **Access control & audit log** — role-based access hooks:
    platform roles `admin`, `member`, `viewer` with a permission
    matrix enforced on every operation; and an append-only audit
    trail recording every customer, provider, auction, bid,
    observation, subscription, alert, and engagement mutation, and
    every denied attempt, with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this
  fork's impact level, recorded as-is, not rounded to Low) per
  `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline.
  LI-SaaS is FedRAMP's tailored **subset** of that baseline for
  SaaS offerings, so the baseline is the Low baseline itself,
  cross-walked to the FAR 52.204-21 basic-safeguarding practices
  that define CMMC L1. One fork at one tier, so no merge changes
  the tier (Merge Rules 1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Customer & provider registries | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness is enforced in the store; identity itself is supplied by the embedding organization |
| Auction records & derived status | CM-6, AU-2/AU-3 (Low side) | Auctions are configuration-controlled records; status is derived at read from the recorded window, reproducible from the records and the trail |
| Bid records | AU-2, AU-3 (Low side), SI-10 | Bids are immutable, validated records accepted only inside the auction's derived-open window; non-integer prices are rejected whole |
| Outcome derivation | CM-6, AU-2/AU-3 (Low side) | The outcome is derived at read from the bid records by a single seam (`_derive_winner`); nothing about it is stored, so it cannot drift from the records |
| Price observations | AU-2, AU-3 (Low side), SI-10 | Observation records are validated and retained with the record set; series latest is derived at read |
| Alert subscriptions & alert records | CM-6, SI-10 | Subscriptions and alerts are explicit records validated on write; no delivery occurs in this build |
| Advisory engagements | AU-2, AU-3 (Low side) | Engagement records with an auditable lifecycle; notes stored verbatim |
| Summary reporting & search | AU-2, AU-3 (Low side); AC-3 | Deterministic counts over the records at a stated `now`; literal search over registered records only, permission-gated |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Three-role matrix enforced before any mutation or id allocation, at the store and again at the service layer; `audit_read` is admin-only, traced to AC-3 (see precision notes) |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing
  is silently imported from other tiers' tables):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and
    its LI-SaaS tailoring) carries the AU family — AU-2/AU-3
    only. AU-6 (audit review) and AU-9 (protection of audit
    information) are Moderate selections and are **not** claimed
    here; hash-chained audit, fail-closed audit writes, audit
    query, logon lockout, and an auditor role are High answers
    from sibling groups and are absent here by design.
  - **Least privilege / separation of duties:** `audit_read`
    being admin-only is a design property of this substrate,
    traced at this tier to AC-3 access enforcement; AC-5/AC-6 are
    not Low-baseline selections and are named as lineage only.
    This build has no decider/submitter seam (it records no
    decisions), so no AC-5-shaped claim arises at all.
  - **Transmission:** SC-8 holds only when a certificate is
    configured (`--certfile`/`--keyfile`); the default serve mode
    is plain HTTP for local/demo use, and encryption at rest is a
    deployment-layer control, stated plainly and not claimed
    here.
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence,
  and any real compliance claim still has to be earned inside each
  regime separately.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `energy` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`cust-`, `prov-`,
`auc-`, `bid-`, `obs-`, `sub-`, `alrt-`, `eng-`); a failed
operation consumes no id and changes nothing. Prices are integer
cents per the auction's (or series') stated unit; a bool, float,
or string price raises `ValidationError`. Any status that depends
on a date (auction status) is derived at read and never stored;
event-driven lifecycle state (an engagement's open/closed, a
subscription's active flag, an auction's recorded early close) is
stored, as in the sibling builds' record lifecycles.

- `energy/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read, register,
  conduct, observe, alert, advise, audit_read, admin}, member =
  {read, register, conduct, observe, alert, advise}, viewer =
  {read}; `require(user, action)` raises `PermissionDenied`.
- `energy/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `energy/store.py` — `EnergyStore(audit=None)` with the
  operations named in the Core above. Role permission is enforced
  for User-like actors before any state change or id allocation;
  a plain-string actor carries identity only, and enforcement for
  those happens in the service layer (the sibling builds'
  convention). The store audits every successful mutation; the
  service layer audits denied attempts (`action:denied`) and
  audit reads, so nothing is recorded twice. The outcome
  derivation lives in the single seam `_derive_winner(bids)`.
- `energy/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User` /
  `X-Role` headers (role must match the registry). Endpoints per
  the group README. Errors are JSON `{error}` with 400/401/403/404
  as applicable. Denied attempts are audited.
- `energy/__main__.py` — `python -m energy serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's).
- `energy/errors.py` — `EnergyError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**:
a mutant store whose `_derive_winner` selects the *highest* bid —
if the suite passed against it, the outcome tests would be testing
that code ran, not that a reverse auction's lowest bid wins — plus
the external mutation drill (the same patch applied to the real
`store.py`); see `tests/README.md` for the counts and the drill
record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Reverse auction execution engine (live bidding sessions,
  real-time bid streaming, automated auction scheduling and
  clearing; the build holds auction and bid records and derives
  the outcome from them)
- Price-trigger evaluation engine (watching price observations
  and firing alerts when a subscription's trigger condition is
  met; the build records subscriptions and alerts, it evaluates
  nothing)
- Alert & notification delivery transport (email / SMS / push /
  portal delivery of the recorded alerts)
- Market intelligence engine (market data collection, analysis,
  and the generation of intelligence content, price forecasts,
  and regional news / insights)
- Advisory practice itself (the budgeting, market-intelligence,
  and risk-management advice; the build records engagements)
- Price chart rendering & dashboards (visualization of the
  observation records; exports)
- Supply contract lifecycle & execution (contract formation,
  e-signature, amendment, and settlement on a winning bid; the
  build records a contract *change* only as an alert subject)
- Payment / settlement execution (no money moves in this build)
- Identity provider / identity management service (IA-2 stays
  with the embedding organization)
- Energy data integrations (market price feeds, meter / usage
  data ingestion — no such data is described by the fork or held
  by the build)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP. **Physical-layer:** this
build controls nothing physical — it holds records about energy
procurement and does not operate grid, charging, building, or
metering systems.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **9 tagged claims** (one per
  taxonomy family, each with its source sentence as evidence).
- Core: **12 / 12** core functions implemented, at the LI-SaaS/L1
  baseline, each with tracing tests.
- Tests: see `tests/README.md` for the count (filled in from the
  build, not stated here), including the mutation-verified
  outcome-derivation negative control.
- Extended: the 10 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
