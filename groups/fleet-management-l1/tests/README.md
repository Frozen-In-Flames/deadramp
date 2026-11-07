# Tests — Fleet Management L1 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/fleet-management-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 67 tests
```

Status at delivery: **67 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

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

## Negative control

`test_negative_control.py` implements the contract's negative
control for the derived due status (Core 6):

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

VERIFIED by the build worker (2026-10-25). The derivation in
`FleetStore._derive_due_status` (`src/fleet/store.py`) — the
`if as_of_date > due: return "overdue"` branch — was patched so the
overdue branch returns `"current"` (`return "overdue"` →
`return "current"`), the exact live counterpart of the mutant in
`test_negative_control.py`. The full suite was run: **67 tests ran,
3 failed** (recorded in `scratch/mutation-run.txt`) —

- `test_maintenance.TestMaintenance.test_derived_overdue`
- `test_negative_control.TestNegativeControlDerivation.test_overdue_canonical_but_mutant_reports_current`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.pristine`; SHA-256
`c1fd0b1c9f11dc80768759665723fa5bb8de00137607ad6632e6ee8f2674881b`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`, and byte-identical via `cmp`) and the
suite re-run: **67 tests, OK**. The suite catches this defect class;
the negative control is not decorative.

## Smoke

A live smoke (`scratch/smoke.py`) drives the store and the HTTP
service end to end: vehicle → operator → reservation → check-out /
check-in (reservation ends `returned`) → usage record, with a lower
odometer reading rejected by the monotonic rule → maintenance
derived `overdue` at a past-due `as_of`, then completed → charging
session closed with 22500 Wh → search hit → summary report (latest
odometer 12150, total 22500 Wh); a viewer write attempt returns 403
over HTTP and the denial is present in the audit log. Result at
delivery: **SMOKE OK**.

## Dependency check

`scratch/verify_deps.py` parses every `.py` file under `src/` with
`ast` and asserts every imported top-level module is in
`sys.stdlib_module_names`. Result at delivery: imports found
`argparse, dataclasses, datetime, http, json, os, ssl, sys,
threading, urllib`; third-party imports: none. **OK: stdlib only.**

## Final GAPS batch coverage (2026-11-07)

`test_gaps_batch.py` (30 tests) pins the extension surface in
`src/fleet/extensions.py` (`FleetExtensions`, wrapping the core
`FleetStore`; all core modules byte-identical) for the 8 entries
of the GAPS.md section "Group 32 — Fleet Management L1 (2
forks)" — see `../BATCH.md` for the per-entry disposition:

| Entry | Tests |
|---|---|
| Live telematics & GPS streaming (reference) | `TestTelematicsReference` — exact key sets, `reference_stub: True`, `tracked_here`/`sensed_here` False, report count derived at read, coordinate-kwarg smuggling raises `TypeError` |
| Dispatch routing & optimization (built, records form) | `TestDispatchRecords` — plan steps verbatim, `optimized_here` False, assignment `dispatched_here`/`controlled_here` False and pinned to leave the core reservation untouched, outcomes verbatim |
| ELD / hours-of-service integrations (reference) | `TestEldReference` — binding `connected_here` False; reported figures/labels verbatim with `evaluated_here` False (over-limit figures still record the reported label — nothing evaluates) |
| Demand & capacity forecasting engine (built) | `TestForecastDerivation` + `TestDemandTotalsNegativeControl` — inputs verbatim; totals/balance/ratio derived at read, exact (`"3/4"`, whole renders int, empty capacity `None`); floats/bools rejected |
| EV charging station communication & session control (reference components) | `TestSessionControlReference` — `reference_stub: True`, `communicated_here`/`controlled_here` False, core session record pinned byte-equal before/after |
| Payment processing (built) | `TestPayments` — exact key set (no credential field), integer cents, float amount and `card_number` kwarg rejected, totals derived at read by outcome |
| Analytics & utilization-optimization engines beyond registry reporting (built) | `TestAnalytics` — run record pinned to exactly `{id, label, created_by, created_utc}` (no figures stored); view derives counts/sums/exact-fraction shares at read and tracks registry state after recording; recursive scan pins no score/rating/rank/grade/index/coordinate-shaped key anywhere on the surface; optimization requests are reference-only |
| Hosted platform operations (reference) | `TestPlatformOperationsReference` — `operated_here`/`hosted_here` False, counts by kind/status derived at read |
| Cross-cutting | `TestCrossCutting` — viewer write denied + audited with `:denied` suffix and no id consumed; no-actor writes denied; extension mutations land on the core audit log with `ext_`-prefixed actions |

### Negative control (fresh, for the new code)

`TestDemandTotalsNegativeControl` implements the batch unit's
negative control for the demand/capacity derivation seam
(`_recorded_demand_totals` in `src/fleet/extensions.py`): the
canonical expectation is demand inputs totalling (15) into the
demand total and capacity inputs (20) into the capacity total;
a local kind-swapped mutant yields (20, 15), differs from the
canonical result, and treating the mutant's output as the
expectation fails via a literal `assertRaises(AssertionError)`.

**Mutation verification (live drill, 2026-11-07):** the seam
in the real `extensions.py` was patched to swap the two kind
filters (`"demand"` ↔ `"capacity"`), and the full suite ran:
**97 tests ran, exactly 3 failed**, all in `test_gaps_batch.py`
—

- `test_gaps_batch.TestDemandTotalsNegativeControl.test_canonical_but_mutant_swaps`
- `test_gaps_batch.TestForecastDerivation.test_view_derives_recorded_totals_exactly`
- `test_gaps_batch.TestForecastDerivation.test_ratio_whole_renders_int_and_empty_capacity_none`

No core test failed. `extensions.py` was restored from
`scratch/extensions.py.premutation`, verified byte-identical by
SHA-256 (`scratch/extensions.py.sha256`,
`e4d9561eb71504b83c4669d2142016b6e801c66180e647f9b34805dcf7f05470`),
and the suite re-ran green: **97 tests, OK**. Raw drill output
is in `scratch/gaps_batch_mutation_run.txt`. The suite catches
this defect class; the negative control is not decorative.

Full suite after the batch unit: **97 tests, OK** (67 core +
30 batch).
