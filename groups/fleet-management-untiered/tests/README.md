# Tests — Fleet Management untiered set merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/fleet-management-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 83 tests
```

Status at delivery: **83 tests, OK** against the implementation in
`../src/` — the founding group's 67-test core suite carried with
the code, plus 16 spec tests in `test_specs.py` pinning this set's
sheets. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty
by design, so package-mode discovery with `-t .` is not the
supported entry point for this group.)

## Carried-suite accounting

The core suite is the founding group's (`../fleet-management-l1/
tests/`), carried whole: all 14 core test modules plus
`fleet_helpers.py`, byte-identical except **one labeling fix** in
`fleet_helpers.py` (its docstring now names this untiered set
instead of Group 32 / Fleet Management L1). This category has no
additions module, so nothing was omitted. `test_specs.py` is new
in this group. Several carried docstrings still say "Group 32" or
"Low baseline" where they trace the founding contract; they ride
verbatim as part of the carried suite, and the re-anchor rule
applies: at tier null, read founding baseline language as
baseline-neutral substrate language (see `../UNION-SPEC.md`).

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 10 RBAC — exact permission matrix for admin/manager/viewer (baseline read+search; manager adds write; admin adds write+audit_read+admin), `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording mutations and denied attempts |
| `test_vehicles.py` | Core 1 vehicle & asset registry — creation shape/provenance, `veh-` ids, get/list, bad status / empty label validation with no id consumed, viewer write denied, plain-string actor convention |
| `test_operators.py` | Core 2 operator records (privacy discipline) — the EXACT key set is pinned (`{id, operator_ref, credential_kind, credential_status, created_by, created_utc}`), forbidden PII-shaped keys asserted absent, credential-status enum, empty ref rejected |
| `test_reservations.py` | Core 3 reservation & assignment records — `res-` shape, unknown vehicle, end-after-start validation, happy-path and cancel lifecycles, illegal/same-state/terminal transitions rejected with state unchanged, the overlap rule (no second active reservation for the same vehicle; checked_out still active; other vehicles unaffected; no id consumed) |
| `test_checkins.py` | Core 4 check-in / check-out records — activity drives the reservation lifecycle (check_out → checked_out, check_in → returned), check-in-before-out and double check-out rejected with nothing recorded, bad kind / odometer rejected |
| `test_usage.py` | Core 5 usage & odometer records — `use-` shape, the monotonic rule (lower rejected, equal/higher accepted, no id consumed), per-vehicle scoping of the rule, unknown vehicle / bad readings |
| `test_maintenance.py` | Core 6 maintenance & inspection records — derivation current/overdue/completed at explicit `as_of` dates, completion, double-complete rejected, bad kind/due-date rejected, and the traced claim that the STORED record has no `status` (and no `derived_status`) key |
| `test_charging_sessions.py` | Core 7 charging session records — `chg-` shape, open session (`ended_utc` None, integer `watt_hours` default 0), close records end + final energy, double-close rejected, float/negative/string watt-hours rejected |
| `test_search.py` | Core 9 search + Core 8 reporting — case-insensitive hits across all five search families, no-hit empty lists, empty query → ValidationError; summary counts per record set, aggregate watt-hours, per-vehicle latest odometer + record counts, empty-store report |
| `test_store_validation.py` | SI-10 store validation — failed creates across all types consume no ids, permission checked before validation/allocation, no-actor writes denied, wrong-typed inputs rejected |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (vehicle → operator → reservation → check-out/check-in → usage + monotonic 400 → maintenance derived overdue → complete → charging + close → search → report), viewer write 403 + denied audited, audit admin-only, 400/404 envelopes |
| `test_main_cli.py` | `python -m fleet serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `test_specs.py` | This set's spec pins (below) |
| `fleet_helpers.py` | Shared fixtures: demo users (ADMIN/MANAGER/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a FleetStore + AuditLog + one vehicle + one operator (created by ADMIN) |

## Coverage table

| Core function | Test files |
|---|---|
| 1. Vehicle & asset registry | `test_vehicles.py`, `test_service.py`, `test_main_cli.py` |
| 2. Operator records (opaque ref, no PII) | `test_operators.py`, `test_service.py` |
| 3. Reservation & assignment records (lifecycle + overlap rule) | `test_reservations.py`, `test_service.py` |
| 4. Check-in / check-out activity records | `test_checkins.py`, `test_service.py` |
| 5. Usage & odometer records (monotonic rule) | `test_usage.py`, `test_service.py` |
| 6. Maintenance & inspection records (derived due status) | `test_maintenance.py`, `test_negative_control.py`, `test_service.py` |
| 7. Charging session records (integer watt-hours) | `test_charging_sessions.py`, `test_service.py`, `test_search.py` |
| 8. Reporting | `test_search.py`, `test_service.py` |
| 9. Search | `test_search.py`, `test_service.py` |
| 10. RBAC + append-only audit | `test_access.py`, `test_audit.py`, `test_vehicles.py`, `test_store_validation.py`, `test_service.py` |
| Spec sheets (this set) | `test_specs.py` |

## Spec tests (`test_specs.py`, 16 tests)

Pin the specs, not the code: exactly 2 sheets; membership exact
against census unit `untiered:Fleet Management` in
`../../remainder.json`; every sheet's `fedramp_impact_level`
"Unknown" with `cmmc_tier` null; vendor/product/status/source_url
equal to `forks.json`; recorded fields as in source (status
Initial Implementation, deployment Public Cloud, SaaS, business
categories [Fleet Management, Operations Management]); descriptions
equal to the census's recorded descriptions; the literal claim
table (each fork: `telematics_gps`, `api_integrations`; 4 claims
total; no zero-claim fork); every claim's evidence verbatim in its
description (checked against the founding normalization, carriage
returns to spaces); the duplicate pair's sheets carrying identical
descriptions and identical claim tables under different fork IDs;
and absence pins holding the recorded adjudications — ELD absent
despite "driver workflows" and "regulatory compliance" being
present; reporting absent despite "reporting" and "visibility"
being present (the phrase "reporting and analytics" and the word
"analytics" occur nowhere); registry and search absent (no FMIS
phrase, no search vocabulary); maintenance absent despite
"equipment monitoring"; telematics standing on the word
"telematics" alone (no `gps` / "live tracking" / "vehicle location
tracking" token anywhere); and no control language of any kind in
either description (no authorized-users, audit, encryption,
access-control, authentication, or role-based wording).

## Negative control

`test_negative_control.py` implements the contract's negative
control for the derived due status (Core 6), carried verbatim from
the founding group:

(a) **Derivation tests** — a `FleetStore` subclass
(`MutantFleetStore`) whose `_derive_due_status` returns `"current"`
for the overdue branch. The traced claim is that **due status is
derived, and a past-due uncompleted record is `overdue`**: for the
canonical case the test asserts the canonical expectation (from the
real implementation), that the mutant would NOT produce that
expectation, and — via a literal `assertRaises(AssertionError)` —
that treating the mutant's outcome as the expected outcome fails.

(b) **Branch isolation** — the same mutant still agrees with the
canonical implementation on `current` (before due) and `completed`
(after completion), isolating the defect to the mutated overdue
branch alone.

## Mutation verification

VERIFIED in this tree at delivery (2026-10-31). The derivation in
`FleetStore._derive_due_status` (`src/fleet/store.py`) — the
`if as_of_date > due: return "overdue"` branch — was patched so the
overdue branch returns `"current"` (`return "overdue"` →
`return "current"`), the exact live counterpart of the mutant in
`test_negative_control.py`. The full suite was run: **83 tests ran,
3 failed** (recorded in `scratch/mutation-run.txt`) —

- `test_maintenance.TestMaintenance.test_derived_overdue`
- `test_negative_control.TestNegativeControlDerivation.test_overdue_canonical_but_mutant_reports_current`
- `test_service.TestFullFlow.test_full_flow`

— the identical failure set to the founding group's drill.
**No spec test failed** under the mutant (the mutation touches the
store, not the specs). `store.py` was then restored from the
pre-mutation copy (`scratch/store.py.premutation`; SHA-256
`c1fd0b1c9f11dc80768759665723fa5bb8de00137607ad6632e6ee8f2674881b`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`, byte-identical via `cmp` to both the
pre-mutation file and the founding group's shipped `store.py`) and
the suite re-run: **83 tests, OK**. The suite catches this defect
class; the negative control is not decorative.

## Smoke

A live smoke (`scratch/smoke.py`, carried from the founding group)
drives the store and the HTTP service end to end: vehicle →
operator → reservation → check-out / check-in (reservation ends
`returned`) → usage record, with a lower odometer reading rejected
by the monotonic rule → maintenance derived `overdue` at a past-due
`as_of`, then completed → charging session closed with 22500 Wh →
search hit → summary report (latest odometer 12150, total 22500
Wh); a viewer write attempt returns 403 over HTTP and the denial is
present in the audit log. Result at delivery: **SMOKE OK**.

## Dependency check

`scratch/verify_deps.py` parses every `.py` file under `src/` with
`ast` and asserts every imported top-level module is in
`sys.stdlib_module_names`. Result at delivery: imports found
`argparse, dataclasses, datetime, http, json, os, ssl, sys,
threading, urllib`; third-party imports: none. **OK: stdlib only.**
