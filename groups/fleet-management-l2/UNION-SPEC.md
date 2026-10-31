# Union Spec — Fleet Management, CMMC L2 (DeadRamp Phase 2 remainder, Fleet Management L2 singleton)

The singleton spec for the Fleet Management category at the L2 tier:
**1 fork, FedRAMP Moderate** — **Geotab Telematics Platform
Government (GTP Gov)** (Geotab), FedRAMP Certified, SaaS,
Government Community Cloud. Built under the remainder census unit
`new-singleton:Fleet Management|L2`.

**Membership provenance, stated plainly:** `forks.json` files this
fork "Uncategorized (none in source)" at tier L2 — its source record
carries an empty `business_categories` list and an empty
business-function segment in `filter_classes`. The DeadRamp
category is the **remainder census proposal**, taken from the fork's
own description ("providing fleet management tools to Government
fleets"; census classification in `remainder/class_all.json`,
proposed category Fleet Management, citation = the fork's whole
description). Reconciliation: `remainder.json` unit ==
`specs/specs.json` == {FR1918150046}, zero diff, and the fork's own
recorded fields (Moderate, FedRAMP Certified, SaaS, Government
Community Cloud, L2) match the source record exactly. MAP.md's
category arithmetic is unaffected: this fork was never in MAP.md's
Fleet Management count, because MAP.md counts the Phase 1 category
field.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1 entry
in exactly the Group 1 schema, with the offering's full public
marketplace description and its function claims tagged from that
description, every claim carrying the source sentence as evidence.
Source: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product record joined by
FedRAMP ID.

## Lineage: a cross-tier carry, upward (the Merge Rule applied across tiers)

This build does not start from zero. Its parents are:

1. The **Group 32 merged build** (`../fleet-management-l1/`) — the
   union of the 2 Fleet Management L1 forks (one FedRAMP Low, one
   LI-SaaS), a working clean-room fleet records substrate (10 core
   functions), whose taxonomy and substrate this category uses at
   every tier. The category has no L3 group; L1 and this singleton
   are its two tiers.
2. This singleton's **1 Moderate fork**, via the spec sheet in
   `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents (Rule 1) — the category
substrate is carried whole, not stripped because one fork's
marketing prose is thin (a wording floor is not a downgrade, the
same reasoning the CRM L1 singleton recorded in the downward
direction). The merged tier is the **highest** parent tier
(Rule 2): the fork's own **Moderate**, satisfied in full by the
baseline written fresh below — the L1 group's Low baseline does not
carry up as the group's baseline, and nothing is diluted to meet
it. Rule 3 traceability is this document plus the spec sheet;
Rule 4's SSDF-shaped process is the provenance here, the review
recorded in `scratch/ARTIFACTS.md`, and the verification record in
`tests/README.md` (full suite run by the builder; the signature
negative control mutation-verified live in this tree).

**What changes at Moderate, stated once:** Group 32's baseline was
written for Low/L1 and carried a precision note that its audit log
traces to the AU family **on the FedRAMP Low side only**, because
CMMC L1 / FAR 52.204-21 contains no audit practice. That note does
**not** carry up: at Moderate the AU family is in the baseline on
both sides (the FedRAMP Moderate baseline carries AU; CMMC L2's
substrate, NIST SP 800-171, carries the 3.3 audit practices), and
the baseline section below is written accordingly. The High
apparatus used by High-tier builds elsewhere in this repo
(hash-chained audit, fail-closed audit writes, logon lockout,
auditor role) answers High-baseline demands that do not exist at
Moderate; it is neither inherited nor claimed here.

## The core-boundary decision (stated once)

**No core function is claim-supported by this fork.** The fork's
single claim (`telematics_gps`) is an **Extended** function — a
live data plane, not a records form — so it buys no Core function.
The Core below is the category's fleet records substrate, carried
whole from the Group 32 union under the Merge Rule and flagged
**carried, not claimed** for this fork. The price of the decision,
stated plainly: this build's function list describes what the
*category's* substrate is, evidenced by the category's L1 forks —
not what Geotab's one-sentence description was found to claim. What
this fork claims is exactly one function, and it is Extended. Any
reader who wants only claim-supported functions should read the
function ranking table, where the distinction is kept per family.

## How functions were counted

Group 32's **17-family taxonomy was applied verbatim** — parsed via
`ast` out of Group 32's shipped `scratch/extract.py` (never
executed, never re-typed) — so counts are comparable across the
category's tiers and nothing was re-tuned to fit this one fork.
Before the newcomer was tagged, the extractor reproduced Group 32's
two shipped claim tables **exactly** from the raw cache (FleetCommander
7, CP Fed Cloud 5, 12 total; function_id + evidence deep-equal).
A family is claimed only when the fork's own description contains
matching text; the first matching sentence is stored in
`specs/specs.json` as evidence.

**Result: 1 claim.** `telematics_gps`, on the fork's only sentence:
"The Geotab Telematics Platform (Government) (GTP Gov) is an
end-to-end vehicle Telematics product, providing fleet management
tools to Government fleets." The word "Telematics" is asserted
twice — in the product's name and in its functional
self-description. Broad first-pass patterns produced 3 hits on this
sentence; **2 false hits were removed** (`vehicle_registry` on bare
fleet/vehicle words with no FMIS phrase; `api_integrations` on the
bare noun "Platform"), 0 true hits recovered, 0 evidence re-bases —
itemized in `scratch/ARTIFACTS.md`, which also records the claim's
exact weight: **the tokens `gps`, `live`, and `location` appear
nowhere in the description**, so no GPS, live-streaming, or
location-tracking capability is attributed beyond what the word
"telematics" itself asserts. The description is 153 characters —
the shortest in this category — and counts are a floor, not a
ceiling: no conclusion about the real Geotab product should be
drawn from its tag count.

**Census citation accounting:** the census recorded one citation
for this fork — the entire description sentence — which verifies as
a strict verbatim substring **and is the claim evidence** for
`telematics_gps`. That is the coincidence direction: verification
is not a claim (the claim stands because the taxonomy pattern
fires, and would stand on the same sentence had the census cited
anything else), recorded in both directions in
`scratch/ARTIFACTS.md`, `scratch/citation_check.json`, and pinned in
`tests/test_singleton_spec.py`.

**Exclusion discipline:** the source record's `certified_services`
is empty (asserted in the extractor), so no third-party catalogue
text exists to exclude; the single-sentence description contains no
catalogue and no scope-exclusion sentence. The record's
`leveraged_systems` field names a **different vendor's** EV
charging product (ATOM EVSE, Atom Power, Inc.) that this
authorization leverages; a record field is not description text, it
was never matched, and it manufactured no `ev_charging` claim —
recorded in `scratch/ARTIFACTS.md`.

## Function ranking — the singleton (17 families)

L1 counts (of 2) are shown for cross-tier comparability; dispositions
are this singleton's.

| # | This fork | L1 | Function family | Disposition in this build |
|---|---:|---:|---|---|
| 1 | 1 | 0 | Live telematics & GPS tracking | **Extended** — claimed here (telematics worded; GPS/live/location not worded, exact weight in ARTIFACTS item 3): "Live telematics & GPS streaming", now with a claimant |
| 2 | 0 | 2 | Usage & odometer records | **Core** — Core 5, carried, not claimed |
| 2 | 0 | 2 | Operator / driver credential & account records | **Core** — Core 2, carried, not claimed |
| 2 | 0 | 1 | Vehicle & asset registry | **Core** — Core 1, carried, not claimed |
| 2 | 0 | 1 | Vehicle reservation & assignment | **Core** — Core 3, carried, not claimed |
| 2 | 0 | 1 | Check-in / check-out activity records | **Core** — Core 4, carried, not claimed |
| 2 | 0 | 1 | EV charging stations & sessions | **Core slice** — Core 7 session records, carried, not claimed; live station communication & session control Extended |
| 2 | 0 | 1 | Payment processing | Extended — "Payment processing", unclaimed here |
| 2 | 0 | 1 | Demand & capacity forecasting | Extended — "Demand & capacity forecasting engine", unclaimed here |
| 2 | 0 | 1 | Reporting & analytics | **Core slice** — Core 8 registry reporting, carried, not claimed; engines beyond that Extended |
| 2 | 0 | 1 | Access control & user validation | **Core** substrate — Core 10 RBAC is baseline-carried at Moderate; this fork words no validation text |
| 2 | 0 | 0 | Maintenance & inspection records | **Core** — Core 6, carried (flagged at L1 as a carried record type); **named absence survives** at claim level (no maintenance/inspection token in this fork) |
| 2 | 0 | 0 | Dispatch routing & optimization | Extended — **named absence survives** (no dispatch/routing token) |
| 2 | 0 | 0 | ELD / hours-of-service integration | Extended — **named absence survives** (no ELD/hours-of-service token; the vendor's ELD business elsewhere is reputation, not evidence) |
| 2 | 0 | 0 | API & integrations | **Named absence survives** — absent from this fork's union (the build's own REST surface is its implementation contract, not a claim) |
| 2 | 0 | 0 | Audit logging | **Core** — Core 10, baseline-carried at Moderate (AU in-baseline on both sides at this tier); **descriptive absence survives** (no audit token) |
| 2 | 0 | 0 | Search | **Core** — Core 9, substrate operation; **descriptive absence survives** (no search token) |

**Named-absence verdicts, summarized:** of Group 32's seven 0/2
families, exactly one absence retires here — **live telematics &
GPS tracking**, at claim level and in its telematics half only (the
fork's own word; the GPS and live qualifiers stay unworded). The
other six survive against this fork token-by-token (full recheck
table in `scratch/ARTIFACTS.md`): maintenance & inspection records,
dispatch routing & optimization, ELD / hours-of-service integration,
API & integrations, audit logging (descriptive), and search
(descriptive). A retirement rests on the fork's own words, and only
one family's words are present.

## The Core — what the merged build implements (10 functions, all carried)

The Group 32 substrate, carried whole; support counts below are the
**category's L1 evidence**, restated so the carry is auditable —
this fork claims none of them (core-boundary decision above).

1. **Vehicle & asset registry (records)** — vehicles and fleet
   assets held as registry records. *Category support:
   vehicle_registry 1/2 at L1 (FleetCommander's FMIS claim).*
2. **Operator records (opaque caller-supplied references only —
   no real PII fields)** — operator records holding caller-supplied
   references and credential records, never real personal
   identifiers; the record's key set is pinned by test. *Category
   support: operator_records 2/2 at L1.*
3. **Reservation & assignment records with lifecycle (reserved →
   checked_out → returned; reserved → cancelled)** — plus the
   implemented overlap rule: a vehicle with an active reservation
   cannot be reserved again. *Category support:
   vehicle_reservation 1/2 at L1.*
4. **Check-in / check-out activity records** — the activity record
   drives the reservation lifecycle (check_out only from reserved,
   check_in only from checked_out; a mismatch records nothing).
   *Category support: checkin_checkout 1/2 at L1.*
5. **Usage & odometer records** — with the monotonic sanity rule: a
   reading lower than the vehicle's latest recorded reading is
   rejected and records nothing. *Category support: usage_metering
   2/2 at L1, both dialects.*
6. **Maintenance & inspection records with due status DERIVED at
   read time (never stored)** — `completed` if a completion is
   recorded, else `overdue` if read after the due date, else
   `current`; the stored record carries no status field. *Category
   support: 0/2 at L1 — flagged carried record type, as at L1.*
7. **Charging session records (EV charging sessions as records —
   station communication is Extended)** — energy in integer
   watt-hours, never a float. *Category support: ev_charging 1/2
   at L1 (ChargePoint). This fork claims no charging function; its
   record's leveraged EVSE system is another vendor's product and
   is not evidence (see exclusion note).*
8. **Reporting over registry records (counts and record listings
   only)** — counts per record set, aggregate charging energy, and
   a per-vehicle usage summary. *Category support:
   reporting_analytics 1/2 at L1; the Core slice is counts and
   listings only, engines Extended.*
9. **Search over registry metadata (substrate)** — substring search
   across the build's own registry metadata. *Category support:
   0/2 — flagged substrate operation, as at L1.*
10. **RBAC (roles admin/manager/viewer; alice/bob/carol demo
    hooks) + append-only audit log** — role-based access enforced
    before any state change or id allocation; every mutation and
    denied attempt recorded with actor, action, target, and UTC
    timestamp; audit read is permission-gated. *Category support:
    0/2 descriptive claims — baseline-carried. At Moderate the AU
    family is in the baseline on both the FedRAMP and the CMMC
    (800-171) side (see "What changes at Moderate" above). The demo
    identities are hooks, not an IdP.*

## Long tail — Extended, by name (gaps)

Exactly the gap names the implementation side uses. Items already
registered under Group 32 are referenced, not re-registered; this
singleton changes their claimant status only where noted.

- **Live telematics & GPS streaming** (telematics_gps) — **gains a
  claimant at this tier**: this fork, on the word "telematics"
  (GPS / live-streaming specifics unworded — exact weight in
  `scratch/ARTIFACTS.md` item 3). The live vehicle telemetry /
  location data plane itself. The Core holds no telemetry stream,
  no GPS feed, and no location record type.
- **Dispatch routing & optimization** (dispatch_optimization) —
  named absence survives; no claimant at any tier of this category.
- **ELD / hours-of-service integrations** (eld_integration) — named
  absence survives; no claimant at any tier of this category.
- **Demand & capacity forecasting engine** (demand_forecasting) —
  claimed at L1 (FleetCommander); unclaimed here.
- **EV charging station communication & session control**
  (ev_charging) — live communication with charging stations,
  session initiation, OCPP-class protocols; claimed at L1
  (ChargePoint); unclaimed here. The Core holds charging-session
  *records* only (Core 7).
- **Payment processing** (payment_processing) — claimed at L1
  (ChargePoint); unclaimed here. The Core processes no payments.
- **Analytics & utilization-optimization engines beyond registry
  reporting** (reporting_analytics) — claimed at L1
  (FleetCommander); unclaimed here. Core 8 is counts and listings
  only.
- **Hosted platform operations** — a platform-layer note, not a
  tagged family: the fork is vendor-hosted SaaS on Government
  Community Cloud, asserted only in the bare noun "Platform" in
  its product name, which this spec deliberately does not tag as a
  claim. Hosting is a platform-layer property, never a fleet
  function; the merged build is a single-tenant reference
  deployment and says so.

**Named absence:** **API & integrations** — checked with broad
patterns; the only hit was the bare "Platform" noun in the
product's name. This fork claims no API and no external
integration, and the family remains absent from the category's
union at this tier. The merged build's own HTTP API
(implementation contract below) is its design, not a union
function.

## Control baseline (traceability) — Moderate / L2

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`). The singleton is uniformly Moderate — no
  tier mix.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of **NIST SP 800-171** that are CMMC L2's substrate.
  Derivation per the Merge Rule: the merged tier is the highest
  parent tier (Moderate, this fork's own), satisfied in full; the
  carried substrate's L1 documentation does not dilute it. This
  baseline is written fresh for Moderate.
- **Feature → control family mapping (this build, at the Moderate
  baseline):**
  - Access control hooks (Core 10) → **AC** (AC-2 account
    management, AC-3 access enforcement, AC-6 least privilege;
    800-171 practices 3.1.1 / 3.1.2: limit system access to
    authorized users and to the transactions and functions they are
    authorized to execute), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the service ships hooks,
    not an identity provider; 800-171 practice 3.5.1 / 3.5.2 at the
    hook level). Demo identities alice/bob/carol are hooks, not an
    IdP — IA-2 stays with the embedding organization.
  - Audit log (Core 10) → **AU** (AU-2 event logging, AU-3 content
    of audit records, AU-6 audit review at the hook level — the
    permission-gated audit read, AU-9 protection of audit
    information — the append-only store with no mutation or
    deletion API). **At this tier the AU family is claimed on both
    sides of the crosswalk:** the FedRAMP Moderate baseline carries
    it, and 800-171 carries the 3.3 audit practices (3.3.1 create
    and retain audit logs, 3.3.2 traceability to individual users).
    Group 32's Low-side-only precision note does not apply here
    and is not repeated.
  - Registry records, lifecycle transitions, and search
    (Cores 1–9) → **SI** (SI-10 information input validation —
    malformed input is rejected, never partially applied, and
    consumes no id; maintenance due status derived at read time,
    never stored, is a record-integrity property of the store) and
    **CM** (CM-6 configuration settings — the lifecycle, overlap,
    and monotonic rules are the build's enforced configuration of
    its record types), **SC** (SC-8 transmission confidentiality —
    the server runs over TLS when a certificate is configured).
    Encryption at rest is a deployment-layer control, stated
    plainly, not claimed here. This fork claims no encryption
    function.
- **What this tier does not carry, and this build does not claim:**
  the High apparatus (hash-chained / fail-closed audit, logon
  lockout machinery, auditor role, 800-172-derived enhancements)
  is out of scope for a Moderate merge and is **not** inherited
  upward from any High build or downward-claimed here.
- **Standing platform notes:** encryption at rest is
  deployment-layer; TLS applies only when configured;
  multi-tenancy is a deployment property — the merged build is a
  single-tenant reference deployment; demo identities are hooks,
  not an IdP (IA-2 stays with the embedding organization).
- **Caveat (standing, from crosswalk.md):** FedRAMP authorizes
  **products**; CMMC certifies **organizations**. A FedRAMP impact
  level is a statement about a cloud service offering; a CMMC level
  is a statement about a company and how it handles FCI/CUI. The
  L2 / FedRAMP Moderate equivalence used here is a
  **planning/matching equivalence only**: it says these forks sit
  at comparable assurance weight so they can be grouped and merged
  consistently. It does **not** claim that a FedRAMP-authorized
  product confers CMMC certification on anyone, that a
  CMMC-certified organization holds a FedRAMP authorization, or
  that either regime accepts the other as evidence. This
  traceability is a planning mapping; the merged build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither credential is claimed.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**, package `fleet` under `src/`,
runnable and testable with `PYTHONPATH=src`. The implementation is
Group 32's, carried byte-identical (7 of 7 modules; hash record in
`scratch/reuse-note.md`):

- `fleet/errors.py` — `FleetError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.
- `fleet/access.py` — `User(name, role)`; roles
  `admin|manager|viewer`; `PERMISSIONS`: admin ⊇ {write, audit_read,
  admin}, manager = {write}, viewer = {} (read and search only);
  `require(user, action)` raises `PermissionDenied`.
- `fleet/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL
  file.
- `fleet/store.py` — `FleetStore(audit=None)` holding the seven
  record sets; sequential prefixed ids `"veh-1"`, `"opr-1"`,
  `"res-1"`, `"chk-1"`, `"use-1"`, `"mnt-1"`, `"chg-1"`, … per set.
  Reservations carry the lifecycle `reserved → checked_out →
  returned` and `reserved → cancelled`, plus the no-second-active-
  reservation rule. Maintenance due status is derived at read time
  via `_derive_due_status(record, as_of)` — completed if a
  completion is recorded, overdue if `as_of` is past due and not
  completed, else current; the stored record carries **no** derived
  status. Operator records hold opaque caller-supplied references
  only. Malformed input raises `ValidationError` and changes
  nothing.
- `fleet/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps
  name → role. Auth via `X-User` / `X-Role` headers (role must
  match the registry). Endpoints: `GET /health`,
  `GET|POST /vehicles`, `GET /vehicles/{id}`, `GET|POST /operators`,
  `GET|POST /reservations`, `POST /reservations/{id}/status`,
  `GET|POST /checkins`, `GET|POST /usage`, `GET|POST /maintenance`,
  `GET /maintenance/{id}`, `POST /maintenance/{id}/complete`,
  `GET|POST /charging-sessions`, `GET /search`, `GET /audit` —
  plus the documented additions `GET /reports/summary`,
  `POST /charging-sessions/{id}/close`, and single-record GETs.
  Errors are JSON `{error}` with 400/401/403/404 as applicable.
  Denied attempts are audited.
- `fleet/__main__.py` — `python -m fleet serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=manager, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

## Coverage statement (for this spec batch)

- Specs: **1 / 1** fork spec'd (Moderate; the fork's actual impact
  level recorded in its spec sheet), reconciled zero-diff against
  the `remainder.json` census unit.
- Claims: **1 total**, carrying its source sentence as evidence;
  per-fork count Geotab GTP Gov 1; **zero-claim forks: none**.
- Taxonomy: **17 function families**, the category's existing
  taxonomy applied verbatim (parent claim tables reproduced exactly
  before tagging); 1 family claimed by this fork, 16 at **0/1** and
  recorded in the ranking table rather than dropped silently (of
  these, Group 32's six surviving named absences are named as such;
  the ten families claimed at L1 are unclaimed here and flagged).
- Artifact corrections for this fork: **2 false hits removed, 0
  true hits recovered, 0 evidence re-bases**, itemized in
  `scratch/ARTIFACTS.md` (3 broad first-pass hits → 1 final claim).
- Core specified: **10 / 10 functions carried** from the Group 32
  union, each flagged carried-not-claimed for this fork under the
  core-boundary decision above; **0 core functions are
  claim-supported by this fork**, stated plainly rather than
  implied otherwise.
- Extended: the category's named gaps are specified above, **not**
  implemented in the Core build; the one change this singleton
  makes to their status is that "Live telematics & GPS streaming"
  gains a claimant (telematics half, at the recorded weight).
