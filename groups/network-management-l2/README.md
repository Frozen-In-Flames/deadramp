# Network Management L2 — merged build (Operation DeadRamp, Phase 2, Group 51)

This is the merged, clean-room implementation of the **Network
Management L2** singleton: **1 fork / vendor platform** from the
FedRAMP Marketplace (Cisco Meraki US Government Region, Cisco
Systems Inc.), built as one open-source service from the group's
union contract (`UNION-SPEC.md`). Network Management is a
brand-new category with no parent group at any tier, so the
function taxonomy was defined from the fork's own marketplace
description (the Group 1 method): **12 claims**, each carrying
its source sentence as evidence.

**What the fork actually is:** by its own description, a
**cloud-managed networking platform** — a vendor cloud from
which agencies deploy, manage, and optimize networks of
switching, wireless, and security / SD-WAN devices, with open
APIs, customizable monitoring, and telemetry carried to the
cloud under FIPS protection on a separate U.S.-soil platform.
What the description never describes is a records system: this
build implements the agency-side records substrate the claimed
functions presuppose — the registries of networks, devices,
changes, and telemetry records such a platform acts on. The
platform's engines themselves are Extended (see Honesty).

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

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
10. **REST API** — every function above over a JSON REST API,
    the build's answer to the open-APIs claim.
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

## Run

```bash
cd groups/network-management-l2
PYTHONPATH=src python3 -m netmgmt serve            # http://127.0.0.1:8000
PYTHONPATH=src python3 -m netmgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m netmgmt serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | member | organizations, records, decisions (never on his own changes) |
| `carol` | viewer | reads only |

### Permission matrix

| Action | admin | member | viewer |
|---|:---:|:---:|:---:|
| `read` | ✓ | ✓ | ✓ |
| `create_org` | ✓ | ✓ | — |
| `enter` (creates / registrations / cancels) | ✓ | ✓ | — |
| `decide` (change decisions) | ✓ | ✓ | — |
| `record` (telemetry, change closes, alert acknowledgements) | ✓ | ✓ | — |
| `manage_members` | ✓ | — | — |
| `audit_read` | ✓ | — | — |
| `admin` | ✓ | — | — |

Organization membership is a second boundary on top of this
matrix: non-members cannot read or write an organization's
content; the platform `admin` role can.

### Main flows (curl)

```bash
B=http://127.0.0.1:8000

# 1. Create an organization (bob becomes owner and first member)
curl -s -X POST $B/organizations -H "X-User: bob" -H "X-Role: member" \
  -d '{"ref": "AGENCY-1", "label": "Agency One Networks"}'   # -> org-1

# 2. Add a member (admin only: manage_members)
curl -s -X POST $B/organizations/org-1/members \
  -H "X-User: alice" -H "X-Role: admin" -d '{"username": "erin"}'

# 3. Register a network and a device
curl -s -X POST $B/organizations/org-1/networks \
  -H "X-User: bob" -H "X-Role: member" \
  -d '{"ref": "NET-HQ", "label": "HQ network", "site_ref": "SITE-HQ"}'
curl -s -X POST $B/organizations/org-1/devices \
  -H "X-User: bob" -H "X-Role: member" \
  -d '{"network_id": "net-1", "ref": "DEV-SW-1", "device_class": "switching", "model_ref": "MODEL-SW-1"}'

# 4. Record telemetry (integer value, caller-supplied timestamp)
curl -s -X POST $B/devices/dev-1/telemetry \
  -H "X-User: bob" -H "X-Role: member" \
  -d '{"metric": "throughput", "value": 100, "unit": "mbps", "recorded_utc": "2026-06-01T08:00:00+00:00"}'

# 5. Read the device at a stated clock: derived_status is fresh
#    (12h after the reading; at 2026-06-03T08:00:00+00:00 it is stale)
curl -s "$B/devices/dev-1?as_of=2026-06-01T20%3A00%3A00%2B00%3A00" \
  -H "X-User: bob" -H "X-Role: member"

# 6. Change lifecycle: bob requests, alice decides (the decider
#    is never the requester; any other non-requester member, e.g.
#    erin in the test registry, could too), bob closes -- closing
#    touches no device or network record
curl -s -X POST $B/organizations/org-1/changes \
  -H "X-User: bob" -H "X-Role: member" \
  -d '{"network_id": "net-1", "change_kind": "update", "summary": "Tune HQ policy", "device_id": "dev-1"}'
curl -s -X POST $B/changes/chg-1/decide \
  -H "X-User: alice" -H "X-Role: admin" -d '{"approve": true}'
curl -s -X POST $B/changes/chg-1/close -H "X-User: bob" -H "X-Role: member"

# 7. Summary, search, and the audit log
curl -s $B/organizations/org-1/summary -H "X-User: bob" -H "X-Role: member"
curl -s "$B/search?q=hq" -H "X-User: bob" -H "X-Role: member"
curl -s $B/audit -H "X-User: alice" -H "X-Role: admin"
```

## Endpoints

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

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/network-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 72 tests
```

**72 tests, all passing**, including the mutation-verified
negative control: stubbing the freshness derivation in the real
store to always report `fresh` makes exactly 6 tests fail (see
`tests/README.md` for the drill record).

## Honesty

- This build is a records substrate. It manages no live network,
  pushes no configuration, provisions no device, and collects no
  telemetry. The fork's engines are not in it: no network
  optimization engine, no network intelligence / AI engine, no
  device provisioning or deployment engine, no configuration
  push / control plane, no firmware management, no traffic
  control or SD-WAN policy engine, no telemetry collection or
  polling engine, no alert evaluation or delivery, no
  integration connectors, no automation execution engine, and
  no cloud management web application. Each is named as an
  Extended gap in `UNION-SPEC.md` for the final batch.
- Change records never touch devices: closing an approved change
  records intent inside this build only, and that is pinned by
  test. Automation definitions are likewise data only.
- Nothing in the build computes a score, a rating, or an
  optimization value, and no record shape has a field for one —
  pinned by a recursive key scan over every view.
- Device freshness is derived at read time and never stored;
  the stored device record carries no derived key — pinned by
  tests twice over.
- No entity shape has a field for an IP address, MAC address,
  serial number, credential, or any identifier of a live
  network: references are opaque and caller-chosen, so none can
  be stored, leaked, or transmitted by this build.
- The fork asserts FIPS protection of its own platform; this
  build claims no FIPS-validated cryptography (SC-13 is a named
  gap — the standard library is not a validated module). U.S.
  data residency and platform scalability are deployment-layer
  properties of the fork's platform, not records functions.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization. Encryption is TLS when
  a certificate is configured; encryption at rest is a
  deployment-layer property.
- This build is not a FedRAMP authorization and not a CMMC
  certification, and it does not claim either. FedRAMP
  authorizes products; CMMC certifies organizations; the tier
  is a planning and matching equivalence, never a credential
  claim.
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (12 evidenced claims from the
  single fork, taxonomy defined from its own description) or to
  the Moderate/L2 control families in `UNION-SPEC.md`. Counts
  are a floor, stated as such.
