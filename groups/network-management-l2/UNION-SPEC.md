# Union Spec — Network Management, CMMC L2 (DeadRamp Phase 2, Group 51)

The merged functional spec for the **Network Management L2
singleton**: **1 fork**, category **Network Management** (a
brand-new category — no group exists at any other tier), CMMC
tier **L2** (the member is FedRAMP **Moderate** in `forks.json`
— verified). The member list was reconciled two ways with
**zero diffs**: `forks.json` carries exactly one Network
Management / L2 entry, and MAP.md's category arithmetic agrees
(Network Management total **1** = L2 1, all other tiers 0;
MAP.md's own reading of this category calls it pure
infrastructure). MAP.md's sibling-group sections list only
groups of size 2 or more, so no prose section exists for this
singleton; the arithmetic is the check, as in the earlier
singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, every
claim carrying the source sentence as evidence. Source: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID
**FR2315535023**.

**What this fork actually is, stated plainly:** the single
Network Management fork is Cisco's Meraki US Government Region
— by its own description, a **cloud-managed networking
platform**: a vendor cloud from which agencies deploy, manage,
and optimize networks of switching, wireless, and security /
SD-WAN devices, with open APIs, customizable monitoring, and
telemetry carried to the cloud under FIPS protection on a
separate U.S.-soil platform. The description is platform prose:
three of its nine sentences are marketing or audience
positioning and tag nothing. What it never describes is a
records system — the records substrate below is what the
claimed functions *presuppose* (an agency-side registry of the
networks, devices, changes, and telemetry records the platform
acts on), and the platform's engines themselves — provisioning,
configuration push, optimization, intelligence, collection —
are Extended, named from the fork's own verbs. The build is
that substrate. It manages no live network, pushes no
configuration, and collects no telemetry.

## How functions were counted (a new category: the Group 1 method)

Network Management has no parent group, so there is no
inherited taxonomy. The taxonomy below was defined **from this
fork's own description**: families are named from the
description's own functional vocabulary, each with a verbatim
match pattern, matched against the description's sentences by
`scratch/extract.py`. A function is claimed **only** when a
sentence contains matching text; the matching sentence is
stored as the claim's evidence in the spec sheet. Marketing
prose gets no tags. **12 claims in total, one per family**.
Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in
`scratch/ARTIFACTS.md`): sentences 1, 3, and 6 tag nothing
(outcome prose and audience positioning); "optimize" IS a
functional verb here ("deploy, manage, and optimize
networks"), so optimization is claimed with the engine
Extended — deliberately unlike Group 50, where "Optimization"
appeared only in a product name and earned no claim; "(AI)" is
the fork's parenthetical gloss on "network intelligence", one
family, not a second AI claim; "FIPS" is recorded inside its
evidence sentence but the build claims no FIPS-validated
cryptography (the standard library is not a validated module;
SC-13 is a gap); the device designations MS/MR/MX appear only
inside the stored evidence — the build's device classes use
the description's generic glosses (switching, wireless,
security & SD-WAN); the source record's `business_categories`
is empty (`[]`) while `forks.json` files the fork under
Network Management — both facts recorded as-is, neither
treated as a functional claim.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Cloud-managed networking platform | 1 | **Core substrate** — the registries and API cloud management runs on; the vendor cloud itself is the platform layer |
| 2 | Network deployment | 1 | **Core slice** — deployment as registration records (networks and devices enter the registry); the provisioning / bring-online engine is Extended |
| 3 | Network management | 1 | **Core** — network registry, device inventory, and configuration change records |
| 4 | Network optimization | 1 | Extended — optimization engine |
| 5 | Network intelligence (AI) | 1 | Extended — intelligence / inference engine |
| 6 | Open APIs | 1 | **Core** — the build is API-first; every core function is exposed over REST |
| 7 | Process integration & automation | 1 | **Core slice** — automation definitions registered as data, **never executed**; the execution engine and integration connectors are Extended |
| 8 | Customizable monitoring & management | 1 | **Core** — telemetry records and alert records (configurable by metric and kind); collection, polling, and alerting engines are Extended |
| 9 | Platform scalability | 1 | Platform note — scale prose (worldwide, cloud architecture); deployment layer |
| 10 | Telemetry data protection | 1 | **Core** — telemetry records held in the registry; FIPS-validated cryptography is a named gap (SC-13), not claimed |
| 11 | U.S. data residency | 1 | Platform note — the fork's separate U.S.-soil platform is a deployment property, not a records function |
| 12 | Network device offering (switching, wireless, security & SD-WAN) | 1 | **Core** — device inventory records by class; the hardware devices themselves are not software, and their control plane is Extended |

**Named absences, stated plainly:** the description contains
**no reporting vocabulary** — no reports, dashboards, or
analytics family exists in this taxonomy (the Core's registry
summaries are substrate for the management and monitoring
claims, not a reporting claim). It names no configuration
schema or template system, no firmware function, no VPN or
tunnel function (SD-WAN appears only inside a device-class
gloss — the traffic-control & SD-WAN policy engine is
registered as a gap named from that gloss, not from a claim),
no identity or SSO administration beyond the open-APIs claim,
and no alerting thresholds or notification channels (alert
*records* are Core under monitoring; evaluation and delivery
are Extended).

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *The scoping container.* Every claimed
function is exercised by a government agency over its own
networks ("gives government agencies the ability to…"), so the
substrate is scoped by customer organizations with membership,
the house scoping pattern: the organization record is known
only by an opaque `ref` and a label. (2) *Deployment as
records.* In a records substrate, "deploy" is the registration
of networks and devices — the events by which an estate enters
the registry. The engine that actually brings a device online
(zero-touch provisioning, configuration push) is the network
control plane: Extended, never built into a records substrate.
(3) *Change records never touch devices.* Managing and
customizing a network in Core means configuration change
records with an approval lifecycle (decider never the
requester, AC-5). Closing an approved change records the
intent; it changes no device and no network, pinned by test.
The push that would apply it is Extended. (4) *Telemetry are
records; freshness is derived.* Telemetry records carry
caller-supplied values and caller-supplied timestamps — the
build collects nothing and polls nothing. A device's status
(`fresh` / `stale` / `unknown`) is **derived at read** from its
latest telemetry record against a stated 24-hour window, and
is never stored: a stored status would itself go stale inside
the store, which is exactly the failure derivation exists to
prevent. (5) *No live-network identifiers.* Device classes use
the description's generic glosses, and no entity shape has a
field for an IP address, MAC address, serial number,
credential, or any identifier of a live network — references
are opaque and caller-chosen, so none can be stored, leaked,
or transmitted by this build. (6) *Automation definitions are
data.* Registered per organization, the registry never
executes one — registering a definition changes no network,
device, change, or telemetry record, ever, pinned by test.

## The Core — what the merged build implements (12 functions)

One coherent, standards-based network-management records
service that the fork's claimed functions presuppose, built
clean-room from this spec:

1. **Customer organizations & membership** — customer
   organizations (`org-`): an opaque caller-supplied `ref` and
   a label, an owner, and a member list. Membership is the
   boundary every other core function enforces.
2. **Network registry** — networks (`net-`) belonging to an
   organization: an opaque `ref` (unique per organization), a
   label, and an opaque `site_ref`. The record shape is
   **pinned** — exactly seven keys, none of which can hold an
   address or credential of a live network.
3. **Device inventory** — devices (`dev-`) registered to a
   network, by the description's own classes (`switching`,
   `wireless`, `security_sdwan`, `other`): an opaque `ref`
   (unique per organization) and an opaque `model_ref`. The
   record shape is **pinned** — exactly nine keys, none of
   which can hold a serial number, MAC, or IP address. A
   device's lifecycle state (`registered` / `retired`) is
   event-driven and stored; its freshness status is not (see
   #7).
4. **Configuration change records** — changes (`chg-`) against
   a network (optionally a device in it), of kinds `create`,
   `update`, `remove`, `policy`, with a verbatim summary and
   the lifecycle `requested → approved → closed`, plus
   `rejected` and `cancelled`. Two seams are enforced in the
   store: the decider is never the requester (**separation of
   duties**), and closing a change alters no device or network
   record — the records are the management surface; the push
   engine is Extended.
5. **Automation definition registry** — automation definitions
   (`aut-`: a name and ordered step names) registered as data
   per organization. The registry **never executes** a
   definition, pinned by test. The execution engine and the
   integration connectors are Extended.
6. **Telemetry records** — telemetry (`tel-`) recorded against
   a device: a metric name, an integer value (bools, floats,
   and strings rejected at the boundary), a unit label, and a
   caller-supplied ISO-8601 timestamp. Records only — nothing
   is collected, polled, or streamed by this build.
7. **Derived device status** — a device's read view derives
   `derived_status` (`fresh` when its latest telemetry record
   is within 24 hours of the read clock, `stale` when older,
   `unknown` when it has none) and `last_reading_utc` from its
   telemetry records at read time. Neither is ever stored —
   the stored device record carries no such key, pinned by
   test.
8. **Alert records** — alerts (`alr-`) by kind
   (`telemetry_threshold` / `device_stale` / `general`) with a
   message, an optional network and device, and an
   acknowledgement record. Alerts are recorded; threshold
   evaluation and delivery are Extended.
9. **Registry search & summary** — literal case-insensitive
   substring search over accessible networks, devices,
   changes, and alerts; and a per-organization summary
   computed on read from records only: network count, device
   counts by class, state, and derived status, telemetry
   record count, change counts by status, automation count,
   alert totals and unacknowledged count. Counts — never
   scores.
10. **API access** — every function above is exposed over a
    REST API (JSON), so the service composes with anything
    that speaks HTTP — the build's answer to the open-APIs
    claim.
11. **Access control** — role-based access hooks: platform
    roles `admin`, `member`, `viewer` with a permission matrix
    enforced on every operation, layered with organization
    membership (non-members cannot read or write an
    organization's content; the platform `admin` role can).
12. **Audit log** — an append-only audit trail: every
    organization, membership, network, device, telemetry,
    change, automation, and alert mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp.

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
  - Change decisions → **AC-5** (separation of duties — the
    decider of a change is never its requester, enforced in
    the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of
    audit records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to
    the `audit_read` permission).
  - Networks / devices / telemetry / changes → **SI** (SI-10
    information input validation — malformed input, including
    any non-integer telemetry value, an unparseable timestamp,
    or a device registered to another organization's network,
    is rejected whole, never partially applied) and **SC**
    (SC-8 transmission confidentiality — the server runs over
    TLS when a certificate is configured; encryption at rest
    and U.S.-soil residency are deployment-layer controls,
    stated plainly, not claimed here; SC-13 FIPS-validated
    cryptography is a named gap — the fork asserts FIPS
    protection of its own platform and the standard library
    is not a validated module).
  - Opaque-reference privacy is a build discipline answering
    to the same input discipline: because no entity shape has
    a field for a real network address, device identifier, or
    credential, none can be stored, leaked, or transmitted by
    this build. It is stated as a discipline, not dressed up
    as an additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states
  which baseline families the build's features answer to. It
  is not a FedRAMP authorization and not a CMMC certification,
  and it does not claim either. FedRAMP authorizes products;
  CMMC certifies organizations; the tier is a planning and
  matching equivalence, never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `netmgmt` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`,
`net-`, `dev-`, `tel-`, `chg-`, `aut-`, `alr-`); a failed
operation consumes no id and changes nothing. Telemetry values
are integers; a bool, float, or string value raises
`ValidationError`. A device's `derived_status` and
`last_reading_utc` exist only on read views, never on the
stored record.

- `netmgmt/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read,
  create_org, enter, decide, record, manage_members,
  audit_read, admin}, member = {read, create_org, enter,
  decide, record}, viewer = {read}; `require(user, action)`
  raises `PermissionDenied`.
- `netmgmt/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `netmgmt/store.py` — `NetmgmtStore(audit=None)` with the
  operations named in the Core above. Organization-scoped
  operations enforce membership (or platform admin) and, for
  User-like actors, the role permission for the operation's
  action (`enter` for creates/registrations/cancels, `decide`
  for change decisions, `record` for telemetry, change closes,
  and alert acknowledgements, `read` for reads, `manage_members`
  for membership changes). The store audits every successful
  mutation; the service layer audits denied attempts
  (`action:denied`) and audit reads, so nothing is recorded
  twice. Named seams: `_derive_device_status` (the freshness
  derivation) and `_check_decider_not_requester` (the AC-5
  seam on change decisions).
- `netmgmt/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  Endpoints per the group README. Errors are JSON `{error}`
  with 400/401/403/404 as applicable. Denied attempts are
  audited.
- `netmgmt/__main__.py` — `python -m netmgmt serve --host
  --port [--audit-log PATH] [--certfile --keyfile]` with demo
  users `alice=admin, bob=member, carol=viewer` (documented as
  demo identities; production identity is the embedding
  organization's).
- `netmgmt/errors.py` — `NetmgmtError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative
control**: a mutant store whose freshness derivation always
reports `fresh` is shown to violate the canonical expectation —
and the external mutation drill (patching
`_derive_device_status` in the real `store.py`) makes a named
set of tests fail; see `tests/README.md` for the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

From this fork's own claims (the engines behind the records):

- Network optimization engine
- Network intelligence / AI engine (inference, insights, and
  anomaly detection beyond registry records)
- Device provisioning & deployment engine (zero-touch
  provisioning, onboarding, actual bring-online of devices)
- Network configuration push / control plane (applying
  configuration to live devices; change records never push)
- Firmware management engine
- Traffic control & SD-WAN policy engine (named from the
  device-class gloss; no traffic claim exists in the
  description)
- Telemetry collection & polling engine (polling or streaming
  ingestion from live devices; telemetry in Core is recorded,
  never collected)
- Alert evaluation & delivery transport (threshold evaluation,
  email / SMS / push; alerts in Core are records)
- Integration connectors (third-party integrations over the
  open APIs)
- Automation execution engine (definitions are registered,
  never executed)
- Cloud management web application (the dashboard UI itself)
- FIPS-validated cryptography (SC-13 — the fork asserts FIPS
  protection of its own platform; the standard library is not
  a validated module and none is claimed)

Platform-layer: U.S. data residency is deployment-layer (the
fork's separate U.S.-soil platform is a deployment property,
not a records function); platform scalability / multi-region
operation (platform prose; this build is a single-deployment
reference); encryption at rest is deployment-layer (TLS when
configured); demo identities are hooks, not an IdP (IA-2 stays
with the embedding organization).

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **12 tagged claims** (one
  per taxonomy family, each with its source sentence as
  evidence; the taxonomy was defined from the fork's own
  description).
- Core: **12 / 12** core functions implemented, at the
  Moderate/L2 baseline, each with tracing tests.
- Tests: see `tests/README.md` for the delivered count,
  including the mutation-verified derived-status negative
  control.
- Extended: the 12 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
