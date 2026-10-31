# Fleet Management L2 — singleton build (Operation DeadRamp, Phase 2 remainder)

This is the clean-room implementation of the **Fleet Management L2
singleton**: **1 fork** from the FedRAMP Marketplace at the Moderate
tier — **Geotab Telematics Platform Government (GTP Gov)**
(Geotab), FedRAMP **Moderate**, FedRAMP Certified, SaaS,
Government Community Cloud — built per the group's union spec
([`UNION-SPEC.md`](UNION-SPEC.md)) under the singleton pipeline
(same pipeline, group size one). The group's union baseline is the
NIST SP 800-53 Rev. 5 **Moderate** baseline ⇔ **CMMC L2** (NIST SP
800-171), written fresh for Moderate in the union spec.

**Read the honesty section before the function list.** This fork's
public description — a single 153-character sentence — evidences
exactly **one** function family under the category taxonomy
(applied verbatim from Group 32): `telematics_gps`, claimed on the
word "Telematics" and Extended, not built. The GPS and live
qualifiers in that family's label are **not** worded in the
description and are not attributed. So the build below is the
category's fleet records substrate **carried** at this tier under
an explicit core-boundary decision (stated once in
`UNION-SPEC.md`, with its price), not a set of functions this fork
was found to claim. Membership provenance is also recorded there:
`forks.json` files this fork Uncategorized; the Fleet Management
category is the remainder census proposal, taken from the fork's
own description.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

**Reuse, stated plainly:** the implementation is the Group 32
(Fleet Management L1) substrate carried up whole under the Merge
Rule — **all 7 `src/` modules are byte-identical** to Group 32's
(SHA-256 record in `scratch/reuse-note.md`), because the L1 build
carries no tier-specific machinery in code; what changes at
Moderate is the baseline documentation, written fresh in
`UNION-SPEC.md` and below. The test suite is likewise carried:
15 of 16 carried test files byte-identical (`fleet_helpers.py`
differs only in its docstring), plus this singleton's own
`test_singleton_spec.py`.

## What the group is: a records substrate

This build is a **records substrate**, not a fleet operations
platform: vehicles held in a registry, operators recorded by opaque
reference only, reservations tracked through a lifecycle, check-in /
check-out activity recorded, odometer readings recorded with a
monotonic sanity rule, maintenance and inspection records whose due
status is derived at read, charging sessions recorded in integer
watt-hours, registry reporting, and search over those records. Each
vendor's live operations on top of that substrate (telematics
streaming — this fork's own claimed function — dispatch, station
communication, payments) are NOT in this build (see Honesty).

## The 10 core functions (all carried from the Group 32 union)

1. **Vehicle & asset registry** — vehicle records (`veh-`) with
   label, vehicle type, and status (`active` / `retired`).
2. **Operator records** — operator records (`opr-`) keyed by an
   **opaque caller-supplied reference**, with a credential kind and
   credential status. Privacy discipline: the record's key set is
   exactly `{id, operator_ref, credential_kind, credential_status,
   created_by, created_utc}` — there are **no fields that can hold a
   real name, a license number, or any other PII** (the exact key
   set is pinned by a test).
3. **Reservation & assignment records** — reservation records
   (`res-`) with a lifecycle: `reserved → {checked_out, cancelled}`,
   `checked_out → {returned}`; `returned` / `cancelled` are
   terminal. Any other transition (including same-state and unknown
   status) is rejected and leaves the state unchanged. **Overlap
   rule implemented:** a vehicle with an active reservation (status
   `reserved` or `checked_out`) cannot be reserved again at all — a
   second active reservation for the same vehicle is a validation
   error, regardless of the requested window. Returning or
   cancelling frees the vehicle.
4. **Check-in / check-out activity records** — activity records
   (`chk-`) with kind (`check_out` / `check_in`) and an odometer
   reading. **Design implemented:** the activity record drives the
   reservation lifecycle — `check_out` is valid only from
   `reserved` and moves the reservation to `checked_out`;
   `check_in` is valid only from `checked_out` and moves it to
   `returned`. A mismatched activity is rejected and records
   nothing.
5. **Usage & odometer records** — usage records (`use-`) per
   vehicle. **Monotonic sanity rule implemented:** a reading lower
   than the vehicle's latest recorded usage reading is rejected
   with a validation error and records nothing; an equal or higher
   reading is accepted. The rule is per vehicle.
6. **Maintenance & inspection records with DERIVED due status** —
   maintenance/inspection records (`mnt-`) with a due date and a
   completion date (`None` until done). **The stored record carries
   NO status field.** Due status is derived at read, in the single
   method `FleetStore._derive_due_status(record, as_of_date)`:
   `completed` if a completion date is set, else `overdue` if
   `as_of` is after the due date, else `current`. Read views carry
   the status as `derived_status`. `POST /maintenance/{id}/complete`
   records completion.
7. **Charging session records** — charging session records (`chg-`)
   keyed by opaque station and operator references, open
   (`ended_utc` is `None`) until closed. **Energy is recorded as
   integer watt-hours (`watt_hours`)** — never a float — to avoid
   float ambiguity. Sessions are closed with
   `POST /charging-sessions/{id}/close` (an endpoint added beyond
   the contract minimum in the parent build), which records the end
   timestamp and the final watt-hours.
8. **Reporting** — registry reporting only, via
   `GET /reports/summary` (an endpoint added beyond the contract
   minimum in the parent build): counts per record set, aggregate
   charging energy in integer watt-hours, and a per-vehicle usage
   summary (latest recorded odometer, counts of usage / reservation
   / check-in / maintenance records per vehicle). Charging sessions
   key to station/operator references, not vehicles, so their
   energy is reported in aggregate only. No analytics engine.
9. **Search** — case-insensitive substring search over registry
   metadata (vehicle labels/types, operator references,
   reservations, maintenance, charging sessions) via
   `GET /search?q=`.
10. **RBAC + append-only audit** — `admin` / `manager` / `viewer`
    roles with a permission matrix enforced before any state
    change; every mutation and every denied attempt is recorded
    with actor, action, target, and UTC timestamp in an append-only
    audit log (optional JSONL file persistence; no mutation or
    deletion API for audit entries). Reading the audit requires the
    `audit_read` permission (admin only); a viewer cannot write
    (403, audited).

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `veh-`, `opr-`, `res-`, `chk-`,
`use-`, `mnt-`, `chg-`. Permission is checked before any state
change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m fleet serve --host 127.0.0.1 --port 8799
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

As a library:

```python
import sys; sys.path.insert(0, "src")
from fleet.access import User
from fleet.audit import AuditLog
from fleet.store import FleetStore

audit = AuditLog()
store = FleetStore(audit=audit)
admin = User("alice", "admin"); manager = User("bob", "manager")
vehicle = store.create_vehicle("Pool Sedan 1", "sedan", admin)
store.record_usage(vehicle["id"], 12000, manager)
res = store.create_reservation(vehicle["id"], "OP-REF-001", "2026-11-01", "2026-11-03", manager)
store.record_checkin(res["id"], "check_out", 12000, manager)
print(store.get_reservation(res["id"])["status"])  # checked_out
print(store.summary_report(admin)["counts"])
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

Every role holds the baseline actions `read` and `search`; the
matrix adds on top of that baseline:

| User    | Role    | Permissions (baseline `read` + `search`, plus) |
|---------|---------|------------------------------------------------|
| `alice` | admin   | `write`, `audit_read`, `admin` (all actions)   |
| `bob`   | manager | `write`                                        |
| `carol` | viewer  | — (read + search only; no writes, no `audit_read`) |

Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case.

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

Contract endpoints are the minimum; the two endpoints marked
**(added)** are documented additions inherited from the parent
build (`/reports/summary` for Core 8 reporting and
`/charging-sessions/{id}/close` for Core 7 session closure), as are
single-record GETs for operators, reservations, and charging
sessions.

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/vehicles` | read | `{"vehicles": [...]}` |
| POST | `/vehicles` | write | Body `{"label", "vehicle_type", "status"?}` → 201 vehicle |
| GET | `/vehicles/{id}` | read | One vehicle |
| GET | `/operators` | read | `{"operators": [...]}` (opaque references only) |
| POST | `/operators` | write | Body `{"operator_ref", "credential_kind", "credential_status"?}` → 201 operator record |
| GET | `/operators/{id}` | read | One operator record **(added)** |
| GET | `/reservations?vehicle_id=&status=` | read | `{"reservations": [...]}` |
| POST | `/reservations` | write | Body `{"vehicle_id", "operator_ref", "start", "end"}` → 201 reservation (`reserved`) |
| GET | `/reservations/{id}` | read | One reservation **(added)** |
| POST | `/reservations/{id}/status` | write | Body `{"status"}` → reservation (lifecycle-gated) |
| GET | `/checkins?reservation_id=` | read | `{"checkins": [...]}` |
| POST | `/checkins` | write | Body `{"reservation_id", "kind", "odometer"}` → 201 activity record (drives the reservation lifecycle) |
| GET | `/usage?vehicle_id=` | read | `{"usage": [...]}` |
| POST | `/usage` | write | Body `{"vehicle_id", "odometer_reading"}` → 201 usage record (monotonic rule) |
| GET | `/maintenance?vehicle_id=&as_of=` | read | `{"maintenance": [...]}` (views with `derived_status`) |
| POST | `/maintenance` | write | Body `{"vehicle_id", "kind", "due_date"}` → 201 maintenance view |
| GET | `/maintenance/{id}?as_of=` | read | One maintenance view with `derived_status` |
| POST | `/maintenance/{id}/complete` | write | Body `{"completed_date"?}` → maintenance view (`completed`) |
| GET | `/charging-sessions` | read | `{"charging_sessions": [...]}` |
| POST | `/charging-sessions` | write | Body `{"station_ref", "operator_ref", "started_utc"?, "watt_hours"?}` → 201 open session |
| GET | `/charging-sessions/{id}` | read | One charging session **(added)** |
| POST | `/charging-sessions/{id}/close` | write | Body `{"ended_utc"?, "watt_hours"?}` → closed session **(added)** |
| GET | `/reports/summary` | read | Counts + aggregate watt-hours + per-vehicle usage summary **(added)** |
| GET | `/search?q=` | search | `{"vehicles": [...], "operators": [...], "reservations": [...], "maintenance": [...], "charging_sessions": [...]}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

79 tests, all passing at delivery. See `tests/README.md` for the
coverage table, the negative control, and the mutation-verification
drill record (performed live in this tree). A live smoke
(`scratch/smoke.py`) drives the store and the HTTP service end to
end: vehicle → operator → reservation → check-out / check-in →
usage with the monotonic rule → maintenance derived overdue, then
completed → charging session + close → search hit → summary report;
a viewer write attempt returns 403 over HTTP and the denied attempt
is present in the audit log.

## Control-family mapping (summary)

Against the **NIST SP 800-53 Rev. 5 Moderate baseline** (the
FedRAMP Moderate tailoring), cross-walked to the **NIST SP 800-171**
practices behind CMMC L2, **at the Moderate baseline**:

| Core function | Control families | How the build answers |
|---|---|---|
| Vehicle/operator/reservation/check-in/usage/maintenance/charging records, reporting, search | AC / IA hooks, AU, SI-10, CM-6 | Records are explicit and configuration-controlled; identity is supplied by the embedding organization via user/role headers (AC-2, AC-3, AC-6; IA-2 hooks — this service ships hooks, not an IdP; 800-171 3.1.1/3.1.2, 3.5.1/3.5.2 at the hook level) |
| RBAC (admin/manager/viewer) | AC-3, AC-6, IA-2 (hooks) | Role matrix enforced pre-mutation, before any id allocation; role header must match the registry exactly or 401 |
| Audit log | AU-2, AU-3, AU-6, AU-9 | Append-only log including denied attempts; no mutation API; audit-read restricted to `audit_read` (admin only). **At Moderate the AU family is in the baseline on both sides** (FedRAMP Moderate carries AU; 800-171 carries the 3.3 audit practices, incl. 3.3.1 log creation/retention and 3.3.2 individual traceability) — Group 32's Low-side-only precision note does not apply at this tier |
| All inputs | SI-10 | Malformed input is rejected with a validation error, never partially applied, and consumes no id; lifecycle gates, the no-second-active-reservation rule, the monotonic odometer rule, and integer watt-hours are validated before any record changes |
| Record-type configuration | CM-6 | The lifecycle, overlap, and monotonic rules are the build's enforced configuration of its record types |
| Transport | SC-8 | The server runs over TLS when a certificate is configured (`--certfile`/`--keyfile`); the default serve mode is plain HTTP for local/demo use |

## Honesty: what is Core, what is Extended, what is NOT in this build

**One claim, and it is not built.** This fork claims exactly one
function family — live telematics & GPS tracking, on the word
"Telematics" in its one-sentence description — and that function is
Extended: **there is no telematics/GPS streaming in this build**,
no GPS feed, no live location tracking, and no record type that
holds a location. The description words no `gps`, `live`, or
`location` token, and none is attributed beyond the word
"telematics" itself. The fork's wider-market reputation (GPS
hardware, ELD products, fuel and maintenance products) is not
evidence and is attributed nowhere: its own description states
none of it, and the ELD, maintenance, dispatch, and API named
absences all survive against it (see `UNION-SPEC.md`).

**Carried, not claimed.** All 10 core functions are the category
substrate carried from the Group 32 (L1) union under the Merge
Rule; **none of them is claim-supported by this fork**. The
function list describes the category's substrate, evidenced by the
category's L1 forks. This is stated once in `UNION-SPEC.md` as the
core-boundary decision, with its price.

**Records only.** This build is a records substrate: **no
telematics/GPS streaming, no dispatch optimization, no ELD
integration, no forecasting engine, no live station communication,
no payment processing**. A reservation record does not dispatch a
vehicle, a check-in record does not read a vehicle, an odometer
record is a caller-reported reading (sanity-checked for monotonic
order, not measured), and a charging session record does not talk
to a charging station or bill anyone. (The fork's source record
leverages another vendor's EV charging product; that is a record
field about a different offering, manufactured no claim here, and
this fork claims no charging function.)

**Operator privacy by construction.** Operator records hold opaque
references and credential metadata only; there is no field in the
record that can hold a driver's name, license number, or other PII.
Identity resolution stays with the embedding organization.

**Platform-layer notes.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies only when configured
(`--certfile`/`--keyfile`); the default serve mode is plain HTTP
for local/demo use. The merged build is a **single-tenant
reference deployment**; multi-tenancy is a deployment property, not
a fleet-management function. The demo identities (`alice`, `bob`,
`carol`) are **hooks, not an IdP**: IA-2 (identification &
authentication) stays with the embedding organization, which
supplies production identity, authentication strength, and account
lifecycle.

**Tier caveat.** This build is **not a FedRAMP authorization and
confers no CMMC certification**, and it claims neither. The tier
here is this fork's own — FedRAMP Moderate — matched to CMMC L2.
The L2 / FedRAMP Moderate equivalence used here is a
planning/matching equivalence only; FedRAMP authorizes products
and CMMC certifies organizations.
