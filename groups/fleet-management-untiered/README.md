# Fleet Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Fleet
Management — census unit `untiered:Fleet Management` in
`../../remainder.json` (Untiered Set 15). **This is an untiered
set, and that means something specific:** every member's FedRAMP
impact level is **Unknown** in the source dataset. The source
publishes no baseline for these offerings, so **tier stays null**:
no tier is assigned, no CMMC equivalence is drawn, and this build
asserts **no control baseline**. Per PIPELINE.md, untiered
offerings "build to their documented control claims; tier stays
null in the registry until the source publishes a baseline." The
union contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`,
pinned by tests.

The 2 forks were spec'd under the category's existing 17-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Fleet Management L1 group's original
shipped claim tables exactly — **2 of 2 forks, 12 of 12 claims,
deep-equal** — before tagging this set. Result here: **4 claims**
across the set, **both forks claiming 2**; there is no zero-claim
fork. Both descriptions are three sentences long, and almost
everything they describe — video-based safety, equipment
monitoring, alerting, driver workflows — has no family in a
taxonomy that was defined from the founding group's two thin
descriptions; the mismatch is recorded in the union spec, not
repaired.

The build implements the category's **ten-function substrate** —
the fleet-operations records machinery — carried **byte-identical**
from the founding Fleet Management L1 build
(`../fleet-management-l1/src/fleet/`, 7 of 7 modules; SHA-256
accounting below). The substrate is tier-independent records code:
the founding source contains no tier or baseline machinery, so
there was nothing tier-shaped to strip. Where the founding
contract's text says "Low baseline hooks" for RBAC and the audit
log, read it here as **baseline-neutral hooks**: at tier null they
are substrate, claimed against no baseline.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2633153272 | Samsara Inc. | Samsara Connected Operations Cloud | 2 |
| FR2700857493 | Samsara Inc. | Samsara Connected Operations Cloud | 2 |

**Duplicate pair:** the two records are the same vendor and
product under two FedRAMP IDs, with byte-identical descriptions
(550 characters) and identical recorded fields. They are spec'd as
separate sheets, per the Phase 1 rule that paired records stay
separate; their claim tables are identical (2 claims each) and the
pair is counted twice in every count, as the registry counts it.

Both forks are filed Fleet Management in `forks.json`, and both
carry the source business categories [Fleet Management, Operations
Management]; the census assigned both to this category from their
own descriptions, and the spec sheets record the assignment.
Authorization status as recorded is Initial Implementation for
both — a status is record data, not a claim.

## The 10 core functions

1. **Vehicle & asset registry** — vehicles and fleet assets held
   as registry records (`veh-` ids), with creation shape and
   provenance validated at write.
2. **Operator records** — operator/driver credential and account
   records holding **opaque caller-supplied references only**; the
   record shape is pinned to an exact key set and no field can hold
   a real name or identifier.
3. **Reservation & assignment records** — reservations binding a
   vehicle to an operator reference, with the lifecycle
   `reserved → checked_out → returned` / `reserved → cancelled`
   and the overlap rule (no second active reservation for the same
   vehicle).
4. **Check-in / check-out activity records** — activity records
   that drive the reservation lifecycle; check-in-before-out and
   double check-out are rejected with nothing recorded.
5. **Usage & odometer records** — usage records under the
   monotonic rule (a lower reading is rejected, no id consumed),
   scoped per vehicle.
6. **Maintenance & inspection records** — records whose due status
   (`current` / `overdue` / `completed`) is **derived at read time
   and never stored**; the stored record carries no status field.
7. **Charging session records** — EV charging sessions as records
   (station reference, operator reference, integer watt-hours);
   the Core holds records only — live station communication is
   Extended.
8. **Reporting** — counts, aggregate watt-hours, and per-vehicle
   usage summaries computed over the build's own registry records.
9. **Search** — case-insensitive search across the registry's own
   metadata (vehicles, operators, reservations, maintenance,
   charging sessions); a substrate operation, not a sibling's
   search engine.
10. **RBAC + append-only audit log** — role-based access
    (admin/manager/viewer) enforced before any state change or id
    allocation, and an append-only audit trail recording every
    mutation and every denied attempt with actor, action, target,
    and UTC timestamp; optional JSONL persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `veh-`, `opr-`,
`res-`, `chk-`, `use-`, `mnt-`, `chg-`. Permission is checked
before any state change or id allocation.

Claim support in this set, stated honestly (see `UNION-SPEC.md`):
**none of the ten functions is claim-supported by a family in this
set** — every Core family's count here is 0 of 2, and the functions
are carried as substrate, exactly as the founding group flagged
its own carried items. The set's claims land elsewhere:
`telematics_gps` (2/2) is an Extended engine, and
`api_integrations` (2/2) supports the substrate's API surface
below. No function is claimed to be *attained* by any fork — the
build is the merged open implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m fleet serve --host 127.0.0.1 --port 8799
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

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

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

Every role holds the baseline actions `read` and `search`; the
matrix adds on top of that baseline:

| User    | Role    | Permissions (baseline `read` + `search`, plus) |
|---------|---------|------------------------------------------------|
| `alice` | admin   | `write`, `audit_read`, `admin` (all actions)   |
| `bob`   | manager | `write`                                        |
| `carol` | viewer  | — (read + search only; no writes, no `audit_read`) |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/vehicles` | read | `{"vehicles": [...]}` |
| POST | `/vehicles` | write | Body `{"label", "vehicle_type", "status"?}` → 201 vehicle |
| GET | `/vehicles/{id}` | read | One vehicle |
| GET | `/operators` | read | `{"operators": [...]}` (opaque references only) |
| POST | `/operators` | write | Body `{"operator_ref", "credential_kind", "credential_status"?}` → 201 operator record |
| GET | `/operators/{id}` | read | One operator record |
| GET | `/reservations?vehicle_id=&status=` | read | `{"reservations": [...]}` |
| POST | `/reservations` | write | Body `{"vehicle_id", "operator_ref", "start", "end"}` → 201 reservation (`reserved`) |
| GET | `/reservations/{id}` | read | One reservation |
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
| GET | `/charging-sessions/{id}` | read | One charging session |
| POST | `/charging-sessions/{id}/close` | write | Body `{"ended_utc"?, "watt_hours"?}` → closed session |
| GET | `/reports/summary` | read | Counts + aggregate watt-hours + per-vehicle usage summary |
| GET | `/search?q=` | search | `{"vehicles": [...], "operators": [...], "reservations": [...], "maintenance": [...], "charging_sessions": [...]}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**83 tests, OK** at delivery: the founding group's 67-test core
suite carried with the code, plus 16 spec tests pinning this set
(exactly 2 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; 4 claims total with no zero-claim
fork; the recorded removals and near-misses held as absence pins).
The category's signature derivation mutation drill was re-run in
this tree — exactly 3 failures under the mutant, store restored
and SHA-256 verified (see `tests/README.md`). A live smoke
(`scratch/smoke.py`) drives the store and the HTTP service end to
end: **SMOKE OK** at delivery.

## Byte-identity accounting

`src/fleet/` is carried from the founding group
`../fleet-management-l1/src/fleet/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `be69d383fba999427bf00c3d624cbc993ede780e27aac4430efb6ac6a21cddfb` |
| `__main__.py` | `ee2a480adaaf1e522877b5c0ab31b0de76b70ffca0221ca704d6c8b39d47ea9d` |
| `access.py` | `4f624329357121f459e06574ad07318a888a6e6ffeac06b8b37b83af357ad400` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `3bea41a3f3d00e2c9e702ac6b4a02ca9c86374543041793485cdade30de2dd44` |
| `service.py` | `e48da6ce6f9a310aa34ad940f81709c8e5a53d685f960a0644644669141c37e4` |
| `store.py` | `c1fd0b1c9f11dc80768759665723fa5bb8de00137607ad6632e6ee8f2674881b` |

The test suite is likewise carried (the founding group's full
67-test core suite; this category has no additions module), with
one labeling fix in `tests/fleet_helpers.py` (its docstring now
names this untiered set instead of Group 32 / L1) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

Documented by at least one fork in this set: **none.**

The one control-adjacent phrase in either description —
"regulatory compliance" — names an application area the platform
offers, alongside fleet telematics, video-based safety, equipment
monitoring, and driver workflows; it asserts no control family
about the offering itself and is recorded as prose, not as a
documented control claim. No description in this set contains
access-control, authentication, authorization, audit, encryption,
or assessment language in any form (pinned by test).

**Not documented** by any fork in this set: every NIST SP 800-53
control family — including AC, AT, AU, CA, CM, CP, IA, IR, MA, MP,
PE, PL, PM, PS, RA, SA, SC, and SI **as control claims** — is
asserted by no description in the set. If the source later
publishes an impact level for any of these offerings, the tier is
recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build.
- **Extended functions are specified, not implemented.** The union
  spec ranks 17 functions; the substrate behind 10 is implemented
  here. NOT implemented (claimant counts are this set's): live
  telematics & GPS streaming (2 — the build ingests no telemetry
  and tracks no vehicle); integration engines & external
  connectors (2 — the build's REST API is its contract, not a
  connector); video-based safety & dash-camera analytics (0
  claimants under any family — substance only); IoT device
  telemetry ingestion & equipment/environmental monitoring (0 —
  substance only); alerting & notification engines (0 — substance
  only); driver workflow & compliance applications (0 — substance
  only); payment processing (0); demand & capacity forecasting
  engine (0); dispatch routing & optimization (0); ELD /
  hours-of-service integrations (0); EV charging station
  communication & session control (0 — Core 7 holds records only).
- **The build performs no cryptography of its own.** No fork here
  documents an encryption claim; the substrate does no encryption
  — TLS is a deployment-layer option when a certificate is
  configured, and FIPS-validated crypto (SC-13) is not claimed by
  the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own.
- **Named absences stand.** ELD / hours-of-service has 0
  claimants in this set despite the vendor's ELD business
  elsewhere; reporting & analytics has 0 despite dashboards and
  reporting being listed in both descriptions; maintenance &
  inspection has 0 despite equipment monitoring being described.
  Nothing was back-filled to make the set look complete.
