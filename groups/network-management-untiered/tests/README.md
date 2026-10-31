# Tests — Network Management untiered set (Untiered Set 19, tier null)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

The core suite is the founding Network Management L2 group's
suite, carried with the byte-identical code (the founding group
has no additions module, so the carry is its full 72 tests),
plus `test_specs.py`, new for this set. One labeling fix:
`netmgmt_helpers.py`'s docstring now names this untiered set
instead of the L2 build; no test logic changed. Traces in the
carried modules that name the founding group's Moderate/L2
baseline read at tier null as baseline-neutral substrate — the
code they test contains no tier machinery.

## Run

```bash
cd groups/network-management-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 83 tests
```

Status at delivery: **83 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 11 Access control — exact permission matrix, `require()`; audit_read admin-only |
| `test_organizations.py` | 7 | 1 Organizations — pinned record shape (exactly six keys), duplicate refs, membership boundary, member management, read-only viewer |
| `test_networks.py` | 5 | 2 Network registry — pinned record shape (exactly seven keys, no live-network identifier field), per-org ref uniqueness, membership boundary |
| `test_devices.py` | 8 | 3 Device inventory, 7 Derived status — pinned stored shape (exactly nine keys, no derived key stored), fresh / stale / unknown derivation against `as_of`, retire lifecycle, cross-org network rejected |
| `test_telemetry.py` | 6 | 6 Telemetry records — pinned shape, integer-only value boundary (bool / float / string rejected), trailing-`Z` timestamps accepted, unparseable timestamps rejected, cross-org device rejected |
| `test_changes.py` | 10 | 4 Change records — pinned creation shape, AC-5 requester/decider separation, decision fields added at decision, close adds `closed_utc` and modifies no device or network record, cancel restricted to requester or platform admin |
| `test_automations.py` | 3 | 5 Automation registry — definition validation; the registry never executes (behavior pin + no execution entry point) |
| `test_alerts.py` | 4 | 8 Alert records — pinned shape with acknowledgement fields starting `None`, kind validation, network/device linkage validation, acknowledge sets both fields and twice is an error |
| `test_reporting.py` | 4 | 9 Search & summary — literal substring search over accessible records only, counts-only summary including devices by class, state, and derived status |
| `test_service.py` | 7 | 10 REST API — live HTTP: 401/403/404/400 semantics, the full network/device/telemetry/change flow over HTTP (including `?as_of=` derived status), automations and alerts over HTTP, denied attempts audited with `:denied`, audit endpoint admin-only |
| `test_audit.py` | 4 | 12 Audit log — mutation recording, entry shape, JSONL persistence round-trip, no mutation API |
| `test_main_cli.py` | 1 | CLI — `python -m netmgmt serve` subprocess answers `/health` |
| `test_store_validation.py` | 3 | Cross-cutting input discipline — failed operations consume no id and change nothing; no score/rating/health/optimization key on any view (recursive scan) |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_specs.py` | 11 | This set's spec sheets — exactly 2 sheets, membership exact against census unit `untiered:Network Management`, tier null / impact "Unknown" on every sheet, registry fields vs `forks.json`, business categories as in source, descriptions equal to the census record under the founding normalization (IronWiFi's paragraph-break difference pinned as whitespace-only), the literal claim table (2 claims, both `network_management`, no zero-claim fork), evidence verbatim in descriptions, the 11 absent family phrases occurring nowhere, IronWiFi's FIPS 199 prose pinned as moving no tier, census citations 2/2 verified with exactly 1 serving as claim evidence |
| `netmgmt_helpers.py` | — | Canonical fixture: organization `AGENCY-1` by bob, erin added as staff member (the canonical decider), network `NET-HQ`, device `DEV-SW-1` (switching), telemetry reading recorded 2026-06-01T08:00:00+00:00 so `as_of` 2026-06-01T20:00:00+00:00 → fresh and 2026-06-03T08:00:00+00:00 → stale; outsider dave in no organization |

## Negative control

**`test_negative_control.py`** — the category's signature
invariant is **derived device status**: a device's freshness is
derived at read from its latest telemetry record against a
stated 24-hour window (fresh within it, stale beyond it,
unknown with no records), never stored. The mutant is a
`NetmgmtStore` subclass (`MutantNetmgmtStore`) whose
`_derive_device_status` always returns `fresh`. The tests assert
the canonical expectations (fresh at the +12h read clock, stale
at the +48h read clock), that the implementation matches them in
both the device view and the organization summary, and — via a
literal `assertRaises(AssertionError)` — that the canonical
expectation rejects the mutant's outcome (the mutant reports
`fresh` at the stale read clock).

## Mutation verification (this tree)

VERIFIED for this group: `_derive_device_status` in the real
`src/netmgmt/store.py` was patched (body replaced, syntax-checked
first) to always return `"fresh"` and the suite was run against
the patched implementation.

- Patched run: **83 ran, exactly 6 failed** — the founding
  drill's identical failure set:
  - `test_devices.TestDevices.test_derived_status_stale_after_24h`
  - `test_devices.TestDevices.test_read_view_adds_derived_keys_never_stored`
  - `test_negative_control.TestNegativeControlDerivedStatus.test_canonical_expectation`
  - `test_negative_control.TestNegativeControlDerivedStatus.test_implementation_matches_canonical_in_summary`
  - `test_reporting.TestSummary.test_summary_counts`
  - `test_service.TestService.test_full_flow_over_http`
- No spec test failed under the mutant.
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`5b1e861c…`, recorded in
  `scratch/store.py.sha256`, the founding shipped hash); the
  suite is green again (83/83). Raw drill output is in
  `scratch/mutation_run.txt`.

The failing set is exactly the derivation-dependent set: the
fresh case still passes under the mutant (the mutant agrees with
the correct answer there, by construction), the stored-record key
pin is untouched by this mutation, and the mutant's own subclass
test passes by construction, as expected.

## Interpretation notes

- Derived status is pinned twice over: once through the public
  device views and the summary, and once by asserting the raw
  stored device record (`store._devices`) carries exactly its
  nine stored keys and no derived key at all.
- A device's lifecycle `state` is event-driven, not date- or
  threshold-driven, so it *is* stored — and the retire test pins
  that retiring is its only transition (retiring twice is a
  validation error). The distinction from derived freshness is
  deliberate and stated in the store's module docstring.
- Closing a change is pinned as a records-only event:
  `test_close_approved_change_modifies_no_device_or_network`
  compares the raw stored device and network records before and
  after the close and requires them identical. The push that
  would apply a change is Extended.
- An empty search query returns no records in any category: the
  search is a literal substring search and the empty-needle case
  is defined as no search (the contract names the searched
  fields, not an empty-query behavior; this is the adjudicated
  reading, recorded here).
- Telemetry timestamps are caller-supplied and stored verbatim
  (including a trailing `Z`); freshness math parses them, it
  never rewrites them.
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.
- The spec tests pin the result, not just the process: a
  re-extraction that re-tunes the taxonomy, a sheet edit that
  manufactures a claim, or a "correction" that moves IronWiFi's
  tier off null on the strength of its FIPS 199 prose fails
  here instead of drifting.
