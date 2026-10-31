# Network Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Network
Management — census unit `untiered:Network Management` in
`../../remainder.json`. **This is an untiered set, and that
means something specific:** every member's FedRAMP impact level
is **Unknown** in the source dataset. The source publishes no
baseline for these offerings, so **tier stays null**: no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The union
contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier:
null`, pinned by tests.

The 2 forks were spec'd under the category's existing
12-function taxonomy **verbatim** (AST-parsed out of the
founding group's extractor, never re-tuned). Taxonomy-verbatim
proof: the extractor first reproduced the founding Network
Management L2 group's original shipped claim table exactly —
**1 of 1 forks, 12 of 12 claims, deep-equal** — before tagging
this set. Result here: **2 claims** across the set, one per
fork, both `network_management` — Armada's at full weight (its
own remote management of satellite terminals), IronWiFi's at
**artifact weight** (the verbatim pattern fires on "the
identities you already manage" — identities the *customer*
manages; IronWiFi is an authentication layer). Eleven of the
twelve families stand at zero in this set; the absences,
including the substance several of them have in other words,
are recorded under Named absences in the union spec, not hidden
or repaired.

The build implements the category's **twelve-function
substrate** — the agency-side records machinery a network
management platform acts on — carried **byte-identical** from
the founding Network Management L2 build
(`../network-management-l2/src/netmgmt/`, 7 of 7 modules;
SHA-256 accounting below). The substrate is tier-independent
records code: the founding source contains no tier or baseline
machinery beyond a docstring naming the founding build, so
there was nothing tier-shaped to strip. Where the founding
contract's text speaks of the Moderate/L2 baseline, read it
here as **baseline-neutral**: at tier null the substrate is
claimed against no baseline.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2632755834 | Armada | Armada Platform | 1 |
| FR2631154499 | IronWiFi, LLC | IronWiFi Cloud RADIUS and Wi-Fi Authentication Platform | 1 |

In `forks.json` neither fork is filed under Network Management:
Armada is filed **Fleet Management** and IronWiFi is filed
**Cybersecurity & Risk Management**; both carry Network
Management among their source business categories, and the
census assigned all 2 to this category from their own
descriptions — the spec sheets record the assignment.
Authorization status as recorded is Initial Implementation for
both — a status is record data, not a claim. One honesty note
belongs here: IronWiFi's prose asserts a "FIPS 199 impact
categorization Moderate" while expressly disclaiming a FedRAMP
Moderate Authorization in the same paragraph; its record says
Unknown, and Unknown is what its sheet records, pinned by test
(see `tests/test_specs.py`).

## The 12 core functions

1. **Customer organizations & membership** — organizations
   (`org-`) known only by an opaque `ref` and a label, with an
   owner and member list; membership bounds every other
   function.
2. **Network registry** — networks (`net-`) belonging to an
   organization, with an opaque `ref` (unique per organization),
   a label, and an opaque `site_ref`. The record shape is
   pinned: **no field can hold an address or credential of a
   live network**.
3. **Device inventory** — devices (`dev-`) registered to a
   network, by the description's own classes (`switching`,
   `wireless`, `security_sdwan`, `other`), with an opaque `ref`
   (unique per organization) and an opaque `model_ref`. The
   record shape is pinned: **no field can hold a serial number,
   MAC, or IP address**. Lifecycle state (`registered` /
   `retired`) is event-driven and stored.
4. **Configuration change records** — changes (`chg-`) against a
   network (optionally a device in it), of kinds `create`,
   `update`, `remove`, `policy`, through `requested → approved →
   closed` (plus `rejected`, `cancelled`). The decider is never
   the requester (separation of duties), and closing a change
   modifies no device or network record — pinned by test.
5. **Automation definition registry** — definitions (`aut-`: a
   name and ordered step names) registered as data per
   organization. The registry **never executes** one; that is
   pinned by test.
6. **Telemetry records** — telemetry (`tel-`) recorded against a
   device: a metric name, an integer value (bools, floats, and
   strings rejected at the boundary), a unit label, and a
   caller-supplied ISO-8601 timestamp. Records only — nothing is
   collected, polled, or streamed.
7. **Derived device status** — a device's read view derives
   `derived_status` (`fresh` when its latest telemetry record is
   within 24 hours of the read clock, `stale` when older,
   `unknown` when it has none) and `last_reading_utc` at read
   time. Neither is ever stored — the stored device record
   carries no such key, pinned by test.
8. **Alert records** — alerts (`alr-`) by kind
   (`telemetry_threshold`, `device_stale`, `general`) with a
   message, an optional network and device, and an
   acknowledgement record. Recorded, not delivered.
9. **Registry search & summary** — literal case-insensitive
   substring search over accessible networks, devices, changes,
   and alerts; and a per-organization summary computed on read
   from records only: network count, device counts by class,
   state, and derived status, telemetry record count, change
   counts by status, automation count, alert totals and
   unacknowledged count. Counts — never scores.
10. **REST API** — every function above over a JSON REST API.
11. **RBAC** — roles `admin`, `member`, `viewer` with a
    permission matrix enforced on every operation, layered with
    organization membership.
12. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed).

Claim support in this set, stated honestly (the full accounting
is the union spec's core-boundary decision): the `network
management` family supports Core functions 2, 3, and 4 (Armada
at full weight, IronWiFi at artifact weight); the audit log
(Core 12) is supported at documented-prose weight by both forks'
audit-logging language; every other function is **carried** as
substrate, not claimed here. Functions are carried; no function
is claimed to be *attained* by any fork — the build is the
merged open implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m netmgmt serve            # http://127.0.0.1:8000
PYTHONPATH=src python3 -m netmgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m netmgmt serve --certfile cert.pem --keyfile key.pem   # TLS
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | everything, including reading the audit log |
| `bob`   | member | organizations, records, decisions (never on his own changes) |
| `carol` | viewer | reads only |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client. Organization membership is a second
boundary on top of the role matrix: non-members cannot read or
write an organization's content; the platform `admin` role can.

## API endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | read | `{"networks": [...], "devices": [...], "changes": [...], "alerts": [...]}` |
| `GET /organizations` · `POST /organizations` | read / create_org | create → 201 |
| `GET /organizations/{id}` · `POST /organizations/{id}` | read / enter | POST updates the label |
| `POST /organizations/{id}/members` | manage_members | body `{"username": ...}` |
| `GET /organizations/{id}/summary` | read | counts only, computed on read |
| `GET /organizations/{id}/networks` · `POST` | read / enter | create → 201 |
| `GET /networks/{id}` | read | |
| `GET /organizations/{id}/devices` · `POST` | read / enter | `?as_of=`, `?network_id=`, `?device_class=`, `?state=`; create → 201 |
| `GET /devices/{id}` | read | `?as_of=` read clock for derived status |
| `POST /devices/{id}/retire` | enter | retiring twice → 400 |
| `GET /devices/{id}/telemetry` · `POST` | read / record | integer values only; create → 201 |
| `GET /organizations/{id}/changes` · `POST` | read / enter | `?status=` filter; create → 201 |
| `GET /changes/{id}` | read | |
| `POST /changes/{id}/decide` | decide | body `{"approve": true\|false}`; never the requester |
| `POST /changes/{id}/close` · `/cancel` | record / enter | close touches no device/network; cancel: requester or platform admin only |
| `GET /organizations/{id}/automations` · `POST` · `GET /automations/{id}` | read / enter | definitions only; never executed |
| `GET /organizations/{id}/alerts` · `POST` | read / record | recorded, not delivered |
| `POST /alerts/{id}/acknowledge` | record | acknowledging twice → 400 |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**83 tests, OK** at delivery: the founding group's 72-test core
suite carried with the code, plus 11 spec tests pinning this set
(exactly 2 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; descriptions equal
to the census record under the founding normalization; the
literal claim table — 2 claims, both `network_management`; the
absent family phrases occurring nowhere; IronWiFi's FIPS 199
prose pinned as moving no tier). The category's signature
freshness-derivation mutation drill was re-run in this tree —
exactly 6 failures under the mutant, store restored and SHA-256
verified (see `tests/README.md`).

## Byte-identity accounting

`src/netmgmt/` is carried from the founding group
`../network-management-l2/src/netmgmt/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `f1018c20c5072c6fa40115151c6da67a2e887f12ec96891c138adef2c37a0c98` |
| `__main__.py` | `092c9f0671d3d16d0ad83bfcdf99254df8a1d86de937c81f2ab2f2a4c6613a99` |
| `access.py` | `8272711e42619a77c179e6b247d527ddde14d658a161b920de21f7e9c6557079` |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` |
| `errors.py` | `c8e65b56ab8c2d8d91babb23c2cfdfe9519e265fd261b32899f99eefac0410fb` |
| `service.py` | `413353ef990e0eda8d84e880a908804f3919a5e5dae696c489b95f07252933b5` |
| `store.py` | `5b1e861c23e8ebc5740dd021abb958667bcae44e244ffcfb4e68c284e8dca871` |

One honest note: `__init__.py`'s docstring first line still
names the founding build ("DeadRamp Phase 2, Group 51: Network
Management L2 singleton") — carried verbatim as part of the
byte-identical code, and recorded here rather than silently
edited (the Set 10 precedent). The test suite is likewise
carried (the founding group has no additions module; its full
72-test suite is here), with one labeling fix in
`tests/netmgmt_helpers.py` (its docstring now names this
untiered set instead of the L2 build) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded with its evidence in `UNION-SPEC.md` and
`specs/specs.json`; it is not the build's control attainment,
and nothing here fills a family in from any baseline.

Documented by at least one fork in this set:

- **Identification & authentication (IA)** — IronWiFi:
  certificate-based authentication and policy; users and devices
  authenticate against Entra ID, Google Workspace, Okta, and
  LDAP/Active Directory; device certificates issued and renewed
  by the built-in cloud PKI over SCEP. Authentication is this
  fork's documented core function; this taxonomy carries no
  identity family, so it stands here, not as a taxonomy claim.
- **Access control (AC)** — documented in part: IronWiFi's
  authentication-and-policy language and its captive-portal
  guest/sponsored-access prose; Armada's centralized
  provisioning through a unified management console, at prose
  weight. IronWiFi's `certified_services` record field names
  role-based access — a record field, never matched, and not
  counted.
- **Audit (AU)** — Armada ("audit logging" in its capability
  list) and IronWiFi ("Every authentication is logged per user
  and device"), both at documented-prose weight; this taxonomy
  has no audit family.
- **Cryptographic protection (SC)** — documented in part, at
  prose weight: IronWiFi names EAP-TLS and a cloud PKI. No fork
  here claims FIPS-validated cryptography (IronWiFi's FIPS
  mention is a FIPS 199 categorization).

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, CA, CM, CP, IR, MA, MP,
PE, PL, PM, PS, RA, SA, and SI **as control claims** — is
asserted by no description in the set. Armada's "incident
lifecycle management" is an operational function, not IR
control language; IronWiFi's ITDR flagging is detection prose,
not an SI claim; IronWiFi's SOC 2 Type II sentence is the fork's
compliance assertion, recorded as its statement. If the source
later publishes an impact level for any of these offerings, the
tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented
  control language is recorded as *its* claim, never as the
  build's control attainment.
- **This build is a records substrate.** It manages no live
  network, pushes no configuration, provisions no device, and
  collects no telemetry. Change records never touch devices:
  closing an approved change records intent inside this build
  only, pinned by test. Automation definitions are likewise
  data only, never executed, pinned by test.
- **Extended functions are specified, not implemented.** NOT
  implemented (the founding group's engines, registered under
  it): network optimization engine; network intelligence / AI
  engine; device provisioning & deployment engine; network
  configuration push / control plane; firmware management
  engine; traffic control & SD-WAN policy engine; telemetry
  collection & polling engine; alert evaluation & delivery
  transport; integration connectors; automation execution
  engine; cloud management web application; FIPS-validated
  cryptography (SC-13). NOT implemented (new from this set's
  forks): network access authentication, RADIUS & 802.1X engine;
  cloud PKI & certificate lifecycle engine; Wi-Fi identity
  threat detection (ITDR) engine; captive portal & guest /
  roaming access services; satellite terminal provisioning &
  connectivity management; fleet mapping & geospatial awareness
  platform; incident lifecycle management engine; GPU
  orchestration.
- **Device freshness is derived at read time and never stored**;
  the stored device record carries no derived key — pinned by
  tests twice over. Nothing in the build computes a score, a
  rating, or an optimization value, and no record shape has a
  field for one — pinned by a recursive key scan over every
  view.
- **No live-network identifiers.** No entity shape has a field
  for an IP address, MAC address, serial number, credential, or
  any identifier of a live network: references are opaque and
  caller-chosen, so none can be stored, leaked, or transmitted
  by this build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  and `carol` are documented demo identities supplied by header;
  the service enforces the role permission matrix on those hooks
  and ships no identity provider, no credential store, and no
  authentication of its own. IA-2 stays with the embedding
  organization — which is also, documented above, exactly the
  layer one of this set's forks sells; the build does not
  implement it.
- **Named absences stand.** Eleven of twelve families have 0
  claimants in this set, several with substance in other words
  (provisioning, reporting, alerting, REST APIs, U.S. regions);
  nothing was back-filled to make the set look complete.
