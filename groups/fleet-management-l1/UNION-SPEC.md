# Union Spec — Fleet Management, CMMC L1 (DeadRamp Phase 2, Group 32)

The merged functional spec for the Fleet Management **L1** sibling group:
**2 forks**, category **Fleet Management**, CMMC tier **L1**. This group
mixes two FedRAMP impact levels: **1 fork is FedRAMP Low**
(FleetCommander) and **1 is LI-SaaS** (CP Fed Cloud). Both map to L1 on
the crosswalk (`../../crosswalk.md`): LI-SaaS is FedRAMP's own tailored
**subset** of the Low baseline for SaaS offerings, so the union of the
group's parent baselines is the Low baseline itself, and the highest tier
any parent carries is the Low family. The group baseline is therefore the
**NIST SP 800-53 Rev. 5 Low baseline** ⇔ **CMMC L1** (the FAR 52.204-21
practice set), taken in full (Merge Rules 1 and 2). Every member is
FedRAMP Certified in `forks.json` — verified. Each fork's **actual**
impact level (Low or LI-SaaS) is recorded per fork in its spec sheet.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2 entries in
exactly the Group 1 schema, each with the offering's full public
marketplace description and its function claims tagged from that
description, every claim carrying the source sentence as evidence.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. The member list reconciles against `MAP.md`'s "Fleet
Management — L1 (2)" section and against `forks.json` (category "Fleet
Management", `cmmc_tier` "L1") with **zero diffs** — asserted in
`scratch/extract.py` (specs vendor+product multiset == forks.json group
== MAP.md section; per-fork impact levels checked against both sources;
both forks' `business_categories_in_source` verified as `[]` in the raw
records).

**The group's character, recorded honestly:** the two members share a
source category and almost nothing else. **FleetCommander** (Agile Fleet)
is a fleet management information system (FMIS): vehicle reservations,
demand and capacity forecasting, data collection for odometer readings,
driver credentials, and check-in/check-out activity, with reporting and
analytics over the fleet. **CP Fed Cloud** (ChargePoint, Inc.) is an
electric-vehicle charging transaction system: it communicates with
charging stations at client sites, initiates charging sessions, accepts
payments, stores customer/organizational information, validates
authorized users of the charging infrastructure, and updates accounts
with usage statistics. One is a fleet MIS; the other is an EV-charging
transaction system — FleetCommander claims no charging, payment, or
user-validation function, and CP Fed Cloud claims no reservation,
check-in/check-out, forecasting, or reporting function. There is no
single product they both are. What the claim counts below support as a
union is a **records substrate for fleet operations**: vehicles held in
a registry, operator records, reservation/assignment records with a
lifecycle, check-in/check-out records, usage/odometer records,
maintenance/inspection records, charging-session records, and reporting,
search, access control, and audit over those records. The merged build
implements that substrate; each vendor's engines on top of it (the
forecasting engine, live station communication and session control,
payment processing, utilization-optimization analytics) are Extended
functions, named in the long tail under the exact gap names the
implementation side uses.

## How functions were counted

Each fork's public marketplace description was sentence-split and matched
against a **17-family taxonomy defined from this category's
descriptions**. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is stored
in `specs/specs.json` as evidence, so every claim is auditable. Bare
"platform"/"system" nouns are not hosting claims, and marketing prose
gets no tags (e.g. FleetCommander's "robust, customizable" claims
nothing; "visibility and control" is a reporting benefit, not access
control — see `scratch/ARTIFACTS.md` item 1). **12 claims survived.**
Wording-artifact corrections were needed and are itemized in
`scratch/ARTIFACTS.md` (21 broad first-pass hits → 12: **9 false hits
removed, 0 true hits recovered, 2 evidence re-bases** with count
unchanged — the classic classes: bare "control" tagged as access
control; "electric vehicle" tagged as a vehicle registry; generic
"services" tagged as maintenance; station siting ("located") and station
communication tagged as telematics/GPS; utilization optimization tagged
as dispatch routing; driver-credential records tagged as ELD
integration; bare "platform"/"system"/"communicates" tagged as API
integrations; reporting "visibility" tagged as search). **No fork has
zero claims.** Per-fork claim counts: FleetCommander 7, CP Fed Cloud 5.
Counts are a **floor**, not a ceiling: the descriptions are short
(537–728 characters) — each is four sentences — and no conclusion about
the real FleetCommander or ChargePoint products should be drawn from
their tag counts.

## Function ranking — all 2 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Usage & odometer records | 2 | 100% | **Core** — Core 5 (both dialects claimed: "odometer readings" and "usage statistics") |
| 1 | Operator / driver credential & account records | 2 | 100% | **Core** — Core 2 (driver credentials; customer/organizational information and accounts) |
| 3 | Vehicle & asset registry | 1 | 50% | **Core** — Core 1 (FleetCommander's FMIS claim; CP Fed Cloud claims no vehicle registry) |
| 3 | Vehicle reservation & assignment | 1 | 50% | **Core** — Core 3 |
| 3 | Check-in / check-out activity records | 1 | 50% | **Core** — Core 4 |
| 3 | EV charging stations & sessions | 1 | 50% | **Core slice**: charging-session records (Core 7). Live station communication & session control: Extended — "EV charging station communication & session control" |
| 3 | Payment processing | 1 | 50% | Extended — "Payment processing" (the Core holds charging-session records; it processes no payments) |
| 3 | Demand & capacity forecasting | 1 | 50% | Extended — "Demand & capacity forecasting engine" (claimed 1/2, FleetCommander; no forecasting is computed in the Core) |
| 3 | Reporting & analytics | 1 | 50% | **Core slice**: reporting over registry records (Core 8). Engines beyond that: Extended — "Analytics & utilization-optimization engines beyond registry reporting" |
| 3 | Access control & user validation | 1 | 50% | Claimed function is CP Fed Cloud's user validation; the Core's RBAC roles and audit log are baseline-carried and flagged at 0 role/audit claims in the Core note (Core 10) |
| 11 | Maintenance & inspection records | 0 | 0% | **Core** — Core 6 (0 descriptive claims; carried record type, flagged in the Core note) |
| 11 | Live telematics & GPS tracking | 0 | 0% | Extended — "Live telematics & GPS streaming" (named absence; no sibling claims it) |
| 11 | Dispatch routing & optimization | 0 | 0% | Extended — "Dispatch routing & optimization" (named absence) |
| 11 | ELD / hours-of-service integration | 0 | 0% | Extended — "ELD / hours-of-service integrations" (named absence) |
| 11 | API & integrations | 0 | 0% | **Not claimed by any sibling in this group** — named absence (the build's own REST surface is its implementation contract, not a sibling claim) |
| 11 | Audit logging | 0 | 0% | **Core** — Core 10 (0 descriptive claims; baseline-carried, AU on the Low side only, flagged in the Core note) |
| 11 | Search | 0 | 0% | **Core** — Core 9 (0 descriptive claims; substrate operation over the build's own registry metadata, flagged in the Core note) |

**Differences are preserved, not averaged away**: the only families both
siblings claim are usage records and operator/account records — and even
there in different dialects (odometer readings vs usage statistics;
driver credentials vs customer/organizational accounts). Every other
claimed family belongs to exactly one fork: FleetCommander's registry,
reservation, check-in/check-out, forecasting, and reporting claims, and
CP Fed Cloud's charging, payment, and user-validation claims, share no
family between them. The per-fork spec sheets name which sibling claims
what.

## The Core — what the merged build implements (10 functions)

The shared records substrate the counts support, plus the baseline hooks
flagged where the counts do not:

1. **Vehicle & asset registry (records)** — vehicles and fleet assets
   held as registry records. *Support: vehicle_registry 1/2
   (FleetCommander's Fleet Management Information System (FMIS) claim —
   an FMIS is the system of record for a fleet; CP Fed Cloud manages
   charging stations, not vehicles, and claims no registry).*
2. **Operator records (opaque caller-supplied references only — driver
   credential records; no real PII fields)** — operator records holding
   caller-supplied references and credential records, never real
   personal identifiers. *Support: operator_records 2/2
   (FleetCommander's "driver credentials"; CP Fed Cloud's stored
   customer/organizational information and user/organizational
   accounts) — the group's joint-largest family.*
3. **Reservation & assignment records with lifecycle (reserved →
   checked_out → returned; reserved → cancelled)** — reservation
   records binding a vehicle to an operator reference, moving through
   the stated lifecycle. *Support: vehicle_reservation 1/2
   (FleetCommander's "vehicle reservation capabilities"). Flag: the
   lifecycle states are the record form a reservation presupposes; no
   description words the states themselves.*
4. **Check-in / check-out activity records** — activity records of
   vehicle check-in and check-out, bound to vehicles and operator
   references. *Support: checkin_checkout 1/2 (FleetCommander's
   "check-in and check-out activity" data collection).*
5. **Usage & odometer records** — usage records (odometer readings and
   usage figures) bound to vehicles, operators, or charging accounts.
   *Support: usage_metering 2/2 — claimed by both siblings, in both
   dialects ("odometer readings"; "usage statistics").*
6. **Maintenance & inspection records with due status DERIVED at read
   time (never stored)** — maintenance/inspection records whose due
   status (completed / overdue / current) is computed when read, from
   the record's due and completion data and the read time; the stored
   record carries no status field. *Support: 0/2 descriptive claims —
   flagged, carried. No description in this group contains maintenance
   or inspection vocabulary (see `scratch/ARTIFACTS.md` item 3); the
   record type is carried because a fleet registry is defined by the
   record types it keeps, and because both siblings' records presuppose
   tracked upkeep state — recorded here as carried, not claimed.*
7. **Charging session records (EV charging sessions as records —
   station communication is Extended)** — records of charging sessions
   (station reference, account/operator reference, usage). *Support:
   ev_charging 1/2 (CP Fed Cloud's electric-vehicle charging sessions).
   The Core holds records; communicating with stations and initiating
   sessions live is Extended ("EV charging station communication &
   session control").*
8. **Reporting over registry records (counts and record listings
   only)** — counts and listings computed over the build's own registry
   records (vehicles, reservations, usage, charging sessions, and the
   rest). *Support: reporting_analytics 1/2 (FleetCommander's
   "reporting and analytics features"). Flag: the Core slice is counts
   and listings only; analytics and utilization-optimization engines
   beyond registry reporting are Extended (see long tail).*
9. **Search over registry metadata (flagged: 0 claims, substrate)** —
   search across the registry's own metadata (vehicles, operators,
   reservations, check-ins, usage, maintenance, charging sessions).
   *Support: 0/2 descriptive claims — flagged. Search here is a
   substrate operation over the build's own records, not a sibling's
   search engine; no sibling claims one (the only broad hit was
   reporting "visibility"; see `scratch/ARTIFACTS.md` item 8).*
10. **RBAC (roles admin/manager/viewer; alice/bob/carol demo hooks) +
    append-only audit log (flagged: 0 claims, baseline-carried, AU Low
    side only)** — role-based access enforced before any state change,
    and an append-only audit trail: every mutation and denied attempt
    recorded with actor, action, target, and UTC timestamp.
    *Support: 0/2 descriptive claims for the roles and the audit log as
    such — flagged. CP Fed Cloud's access_control claim (1/2) is
    validation of authorized charging users; no description in this
    group words roles, permissions, or audit, and FleetCommander has
    no access text at all. RBAC is Core because the Low/L1 baseline
    requires it (AC/IA families, traceability below); the audit log is
    carried solely as a Low-baseline hook (AU family on the FedRAMP Low
    side of the crosswalk only), flagged here so no reader mistakes
    either for a claimed vendor function; see the precision note in the
    baseline section. The demo identities are hooks, not an IdP.*

## Long tail — Extended, by name

Exactly the gap names the implementation side uses:

- **Live telematics & GPS streaming** (telematics_gps 0/2) — named
  absence: no sibling claims live vehicle telemetry or GPS tracking.
  CP Fed Cloud's stations "located at client sites" is station siting,
  not tracking (see `scratch/ARTIFACTS.md` item 4).
- **Dispatch routing & optimization** (dispatch_optimization 0/2) —
  named absence: no sibling claims dispatching or routing.
  FleetCommander's "optimize fleet utilization" is a reporting/
  forecasting outcome, not routing (item 5).
- **ELD / hours-of-service integrations** (eld_integration 0/2) — named
  absence: no sibling claims an electronic logging device or
  hours-of-service function. Driver-credential records (Core 2) are
  records, not an ELD integration (item 6).
- **Demand & capacity forecasting engine** (demand_forecasting 1/2 —
  FleetCommander) — the engine that analyzes and forecasts fleet demand
  and capacity. The Core stores no forecasting computation; the claim
  is specified here, not implemented.
- **EV charging station communication & session control** (ev_charging
  1/2 — ChargePoint) — live communication with charging stations at
  client sites, establishing/initiating charging sessions, and
  OCPP-class station protocols. The Core holds charging-session
  *records* only (Core 7).
- **Payment processing** (payment_processing 1/2 — ChargePoint) —
  accepting payments and account authorization for station use, as
  CP Fed Cloud does. The Core holds charging-session records and
  processes no payments.
- **Analytics & utilization-optimization engines beyond registry
  reporting** (reporting_analytics 1/2 — FleetCommander) — the
  analytics, visibility, and utilization-optimization engines behind
  FleetCommander's reporting claim. Core 8 is counts and record
  listings only.
- **Hosted platform operations** — a platform-layer note, not a tagged
  family: both siblings are vendor-hosted SaaS on Government Community
  Cloud, asserted only in bare "platform"/"system" prose that this
  spec deliberately does not tag as a claim (item 7). Hosting is a
  platform-layer property, never a fleet function; the merged build is
  a single-tenant reference deployment and says so.

**Named absence:** **API & integrations** (0/2) — checked with broad
patterns; the only hits were bare "platform"/"system" nouns and CP Fed
Cloud's station communication, which is the `ev_charging` function. No
sibling claims an API or an external integration. The merged build's own
HTTP API (implementation contract below) is its design, not a union
function.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`). Tier mix: **Low 1 / LI-SaaS 1**, each fork's
  actual level recorded in its spec sheet.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored subset of it), cross-walked
  to the FAR 52.204-21 practices that define CMMC L1. Derivation per the
  Merge Rule: union of parent baselines = Low (the LI-SaaS subset adds
  nothing beyond it), inherited in full. This baseline is written fresh
  for the lightest tier.
- **Feature → control family mapping (this build, at the Low baseline):**
  - Access control hooks (Core 10) and user validation → **AC** (AC-2
    account management, AC-3 access enforcement; FAR 52.204-21's
    access-limitation practices: limit system access to authorized users
    and to the transactions and functions they are authorized to
    execute), **IA** (IA-2 identification & authentication — identity is
    supplied by the embedding organization via user/role headers; the
    service ships hooks, not an identity provider; FAR's practices:
    identify system users, processes, and devices, and authenticate
    them before allowing access). Demo identities alice/bob/carol are
    hooks, not an IdP — IA-2 stays with the embedding organization.
    CP Fed Cloud's claimed validation of authorized charging users sits
    in this same family at the product layer; the build's roles are the
    substrate hook for it, not the claimed product.
  - Audit log (Core 10) → **AU**, **on the FedRAMP Low side of the
    crosswalk only** (AU-2 event logging, AU-3 content of audit
    records; the append-only store and permission-gated read are
    implementation properties). **Precision note:** CMMC L1 / FAR
    52.204-21 contains **no audit practice**, so no audit claim is made
    on the CMMC side. The audit log is carried because the FedRAMP Low
    baseline carries the AU family — not because L1 asks for it.
  - Registry records, lifecycle transitions, and search (Cores 1–9) →
    **SI** (SI-10 information input validation — malformed input is
    rejected, never partially applied; maintenance due status derived
    at read time, never stored, is a record-integrity property of the
    store) and **SC** (SC-8 transmission confidentiality — the server
    runs over TLS when a certificate is configured; FAR's
    system-and-communications-protection practices cover boundary
    protection and protecting transmitted information at the family
    level). Encryption at rest is a deployment-layer control, stated
    plainly, not claimed here. No sibling in this group claims an
    encryption function.
- **What this tier does not carry, and this build does not claim:** the
  Moderate/High apparatus from the sibling groups (e.g. Moderate-level
  audit enhancements, lockout machinery, and 800-172-derived
  requirements) is out of scope for a Low/L1 merge and is **not
  inherited downward**.
- **Standing platform notes:** encryption at rest is deployment-layer;
  TLS applies only when configured; multi-tenancy is a deployment
  property — the merged build is a single-tenant reference deployment;
  demo identities are hooks, not an IdP (IA-2 stays with the embedding
  organization).
- **Caveat (standing, from crosswalk.md):** FedRAMP authorizes
  **products**; CMMC certifies **organizations**. A FedRAMP impact level
  is a statement about a cloud service offering; a CMMC level is a
  statement about a company and how it handles FCI/CUI. The L1 / FedRAMP
  Low equivalence used here is a **planning/matching equivalence
  only**: it says these forks sit at comparable assurance weight so they
  can be grouped and merged consistently. It does **not** claim that a
  FedRAMP-authorized product confers CMMC certification on anyone, that
  a CMMC-certified organization holds a FedRAMP authorization, or that
  either regime accepts the other as evidence. This traceability is a
  planning mapping; the merged build is not a FedRAMP authorization and
  confers no CMMC certification, and neither credential is claimed.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**, package `fleet` under `src/`,
runnable and testable with `PYTHONPATH=src`:

- `fleet/errors.py` — `FleetError`, `ValidationError`, `NotFoundError`,
  `PermissionDenied`.
- `fleet/access.py` — `User(name, role)`; roles `admin|manager|viewer`;
  `PERMISSIONS`: admin ⊇ {write, audit_read, admin}, manager = {write},
  viewer = {} (read and search only); `require(user, action)` raises
  `PermissionDenied`.
- `fleet/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL file.
- `fleet/store.py` — `FleetStore(audit=None)` holding the seven record
  sets; sequential prefixed ids `"veh-1"`, `"opr-1"`, `"res-1"`,
  `"chk-1"`, `"use-1"`, `"mnt-1"`, `"chg-1"`, … per set. Reservations
  carry the lifecycle `reserved → checked_out → returned` and
  `reserved → cancelled`. Maintenance due status is derived at read
  time via `_derive_due_status(record, as_of)` — completed if a
  completion is recorded, overdue if `as_of` is past due and not
  completed, else current; the stored record carries **no** derived
  status. Operator records hold opaque caller-supplied references only.
  Malformed input raises `ValidationError` and changes nothing.
- `fleet/service.py` — `make_server(host, port, store, audit, users)`
  → `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth
  via `X-User` / `X-Role` headers (role must match the registry).
  Endpoints: `GET /health`, `GET|POST /vehicles`, `GET /vehicles/{id}`,
  `GET|POST /operators`, `GET|POST /reservations`,
  `POST /reservations/{id}/status`, `GET|POST /checkins`,
  `GET|POST /usage`, `GET|POST /maintenance`, `GET /maintenance/{id}`,
  `POST /maintenance/{id}/complete`, `GET|POST /charging-sessions`,
  `GET /search`, `GET /audit`. Errors are JSON `{error}` with
  400/401/403/404 as applicable. Denied attempts are audited.
- `fleet/__main__.py` — `python -m fleet serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=manager, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's, per
  IA-2 above).

## Coverage statement (for this spec batch)

- Specs: **2 / 2** forks spec'd (Low 1, LI-SaaS 1; each fork's actual
  impact level recorded in its spec sheet), reconciled zero-diff against
  `forks.json` and `MAP.md`.
- Claims: **12 total**, every claim carrying its source sentence as
  evidence; per-fork counts FleetCommander 7, CP Fed Cloud 5;
  **zero-claim forks: none**.
- Taxonomy: **17 function families** defined from this category's
  descriptions; 10 claimed by at least one sibling, 7 at **0/2** and
  recorded as named absences rather than dropped silently
  (maintenance & inspection records, live telematics & GPS tracking,
  dispatch routing & optimization, ELD / hours-of-service integration,
  API & integrations, audit logging, search — of these, maintenance
  records, audit, and search enter the Core only as flagged carried /
  substrate / baseline items, telematics, dispatch, and ELD are
  Extended gaps, and API & integrations is absent from the union
  entirely).
- Artifact corrections: **9 false hits removed, 0 true hits recovered,
  2 evidence re-bases**, itemized in `scratch/ARTIFACTS.md` (21 broad
  first-pass hits → 12 final claims).
- Core specified: **10 / 10 functions**, exactly the list above (7 fully
  or partly claim-supported — registry, operators, reservations,
  check-ins, usage, charging sessions, reporting; 3 flagged carried /
  substrate / baseline items — maintenance records, search, RBAC +
  audit), each flagged as such.
- Extended: **8 named gaps**, specified and ranked, **not** implemented
  in the Core build — "Live telematics & GPS streaming", "Dispatch
  routing & optimization", "ELD / hours-of-service integrations",
  "Demand & capacity forecasting engine", "EV charging station
  communication & session control", "Payment processing", "Analytics &
  utilization-optimization engines beyond registry reporting", "Hosted
  platform operations" — named here rather than implied done. No
  implementation code in this batch — specs and union spec only; the
  implementation is built in parallel against the Core list above.
