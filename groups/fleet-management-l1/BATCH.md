# Final GAPS batch — Group 32, Fleet Management L1 (2 forks)

Date: 2026-11-07. This section of `../../GAPS.md` listed 8 open
entries; all 8 are closed by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/fleet/extensions.py`
(`FleetExtensions`, wrapping the core `FleetStore`; all seven
core modules byte-identical, SHA-256 verified against the
pre-build hashes — store.py still `c1fd0b1c…`, the shipped
hash), and `tests/test_gaps_batch.py` (30 tests). Full suite:
**67 → 97 tests**, all passing.

**The founding discipline binds every shape built here:** this
build holds records about fleet operations. It streams no
telemetry, senses no position, dispatches no vehicle,
optimizes no route, connects to no logging device, forecasts
nothing, talks to no charging station, moves no money, and
runs no analytics engine. Records carry metadata and opaque
caller-supplied references only, plus figures and outcomes
stored exactly as reported by the external systems and people
who actually did the work. That is pinned by exact key-set
assertions per record type, by `TypeError` on any unexpected
keyword argument, and by a recursive scan pinning that no
score/rating/rank/grade/index-shaped key exists anywhere on
the extension surface. Every "engine" below is its
in-substrate form: records over the group's OWN records (core
records and extension records), plus deterministic derivations
at read. The baseline stays as written for the core — Low /
L1, audit on the FedRAMP Low side only (AU-2/AU-3; FAR
52.204-21 carries no audit practice) — and no Moderate/High
apparatus is imported.

## Per-entry disposition

| Entry (GAPS.md text) | Inventory idx / drafted triage | Disposition | Built as |
|---|---|---|---|
| Live telematics & GPS streaming (0 claims in this group; named) | 329 / stub-engine | reference | Labeled reference records: telematics stream-subscription records (`tlm-`) against a core vehicle, holding an opaque `source_ref` (`reference_stub: True`, `streamed_here: False` — no stream is opened), plus caller-REPORTED position/status records (`tlr-`) holding the reported position label verbatim (`tracked_here` / `sensed_here: False`). Each report is standalone — no track/trail/history structure exists (pinned by exact key set), and no coordinate field exists: a `latitude=` kwarg raises `TypeError`. `telematics_stream_view` derives the report count at read; the stored stream carries no count. |
| Dispatch routing & optimization (0 claims; named) | 330 / build-extension | built | Records form: route-plan records (`rtp-`) holding an ordered list of step labels verbatim as data (`optimized_here: False` — nothing computes, compares, ranks, or scores routes), dispatch-assignment records (`dsp-`) over core reservations binding an operator reference and an optional route plan (`dispatched_here` / `controlled_here: False` — the assignment is the record form of a dispatch decision made elsewhere; a test pins that recording one leaves the core reservation untouched), and reported outcome records (`dso-`) with labels verbatim. `route_plan_view` derives the assignment count at read. |
| ELD / hours-of-service integrations (0 claims; named) | 331 / stub-engine | reference | Labeled reference records: device-binding records (`eld-`) binding a core operator record to an opaque `device_ref` (`reference_stub: True`, `connected_here: False` — nothing connects to a device), plus hours-of-service records (`hos-`) holding reported driving/on-duty minute figures and the reported compliance label verbatim (`evaluated_here: False`). No hours-of-service limit is evaluated and no compliance status is computed — a test records figures beyond any real limit alongside a `reported_compliant` label to pin that the label is a report, never a determination. |
| Demand & capacity forecasting engine (claimed 1 of 2) | 332 / build-extension | built | Forecast-input records (`fci-`): demand/capacity figures for a named subject and period, stored verbatim as reported (integer units; floats and bools rejected at the boundary). `forecast_view` derives the recorded demand and capacity totals via the seam `_recorded_demand_totals`, their exact difference, and their exact ratio rendered as an int when whole, else as an exact `"num/den"` string (`None` when no capacity is recorded). Nothing is projected, estimated, or fitted (`projected_here` / `modeled_here: False`): the derivation is over recorded figures only — the records-form forecasting surface, not a forecasting engine. |
| EV charging station communication & session control (claimed 1 of 2; the core holds charging session records only, no live station communication) | 333 / build-extension | **reference (re-judged — see below)** | Session-control request records (`sctl-`) bound to core charging sessions, in the recorded kinds (start session, stop session, set limit with an integer watt-hour limit), riding in-record as labeled reference components: `reference_stub: True`, state `recorded_reference_only`, `communicated_here` / `controlled_here: False`. Plus reported outcome records (`sout-`) with labels verbatim, and a view deriving the outcome count at read. Pinned: recording a control request leaves the core charging-session record byte-equal — this surface never reads a session for update and never modifies one. |
| Payment processing (claimed 1 of 2) | 334 / build-extension | built | Payment records (`pay-`) bound to core charging sessions: kind (authorization / capture / refund), integer cents (floats rejected at the boundary), an opaque `payment_ref`, and the reported outcome label verbatim (`moved_here` / `settled_here: False` — the outcome was produced by the processor that actually acted). The exact key set is pinned: no field can hold a card or account number, and a `card_number=` kwarg raises `TypeError`. `session_payments_view` derives the payment count, the total, and totals by reported outcome at read; stored payments carry no totals. |
| Analytics & utilization-optimization engines beyond registry reporting (claimed 1 of 2) | 335 / build-extension | built | Report-run records (`rpt-`) pinned to exactly `{id, label, created_by, created_utc}` — a run stores NO figures. `analytics_view` derives everything at read from the substrate's own records: counts per record set (core and extension), aggregate recorded charging energy (integer watt-hours), the fleet's latest recorded odometer (maximum recorded reading, or `None`), and the maintenance completed share and charging closed share as exact int/`"num/den"` fractions (`None` on an empty denominator set) — a test proves the figures track registry state recorded after the run. No score, rating, ranking, or index exists anywhere on the surface (recursive scan). Utilization optimization ships inside the entry as a labeled reference component: optimization-request records (`opt-`, `reference_stub: True`, `optimized_here: False`) held as data for an optimizer that lives elsewhere. |
| Hosted platform operations (platform-layer) | 336 / stub-engine | reference | Labeled reference records: platform-operation records (`plt-`) in the recorded kinds (deployment, maintenance window, incident, status report) holding the reported status label verbatim and an optional opaque `detail_ref` (`reference_stub: True`, `operated_here` / `hosted_here: False` — this build operates and hosts nothing). `platform_operations_view` derives counts by kind and by reported status at read — counts only. PLATFORM-LAYER.md decision 6 stands beside this closure and is not re-argued by it: hosting remains a deployment property; these records close only the records surface of the entry (see re-judgments). |

Closure tokens: the drafted split was 5 build-extension /
3 stub-engine. After the one re-judgment below (EV charging
session control), the final count is **4 built** (dispatch
routing & optimization, demand & capacity forecasting,
payment processing, analytics beyond registry reporting) and
**4 reference** (live telematics & GPS streaming, ELD /
hours-of-service integrations, EV charging station
communication & session control, hosted platform operations).
The parent closes the tokens in GAPS.md; this unit's count
line is stated so the two agree.

## Re-judgments

One, under DECISION.md qualification 1:

- **EV charging station communication & session control**
  (idx 333), drafted build-extension, closed `reference`.
  Grounds: on close reading of the group's own UNION-SPEC,
  the entry's substance is the act the spec names — live
  communication with charging stations at client sites,
  establishing/initiating sessions, and OCPP-class station
  protocols — and the entry text itself records that "the
  core holds charging session records only, no live station
  communication." What this build can honestly add over the
  core session records is a records surface of control
  *requests* and reported outcomes, which is exactly the
  labeled in-record reference form the Operations Management
  (untiered) unit adjudicated for the identical shape ("EV
  charging session-control requests ride in-record as
  reference components, `reference_stub: True`,
  `controlled_here: False`"). Shipping the records surface
  under a `built` token would overstate it: nothing here
  communicates with or controls a station, and the records say
  so on their face. The build is unchanged by the token — the
  request/outcome surface, its pins, and its tests are the
  same either way; only the closure token is corrected.

Two calls nearest the line were held at their drafted
dispositions rather than re-judged, and are stated plainly:

- **Demand & capacity forecasting** closes `built` in the
  records form the brief prescribes: reported inputs plus
  deterministic read-time derivations over the recorded
  figures. Nothing is projected — no future period's demand
  is estimated and no model is fit — and the view carries
  `projected_here` / `modeled_here: False` on its face. The
  drafted build-extension disposition is honored for the
  substrate surface (the records and the exact derivation);
  the entry's engine substance (forecasting proper) is not
  claimed by any record here.
- **Hosted platform operations** was drafted stub-engine,
  not rescope-platform, and closes `reference` as drafted:
  the section's own platform paragraph in GAPS.md and
  PLATFORM-LAYER.md decision 6 already carry the written
  platform decision for hosting as a deployment property, and
  this unit adds the records surface (reported operation and
  status records) on top of it rather than re-opening the
  written decision. The records claim no hosting: every one
  carries `hosted_here: False`.

## Negative control

Fresh, for the new code: the demand/capacity derivation seam
(`_recorded_demand_totals` in `src/fleet/extensions.py` — a
subject's recorded demand and capacity are the sums of its
demand-kind and capacity-kind recorded inputs respectively).
In-suite control in `tests/test_gaps_batch.py`
(`TestDemandTotalsNegativeControl`: the canonical inputs yield
(15, 20) from the seam; a local kind-swapped mutant yields
(20, 15), and treating the mutant's outcome as the expectation
fails via `assertRaises(AssertionError)`), plus a live drill
on the real file: the seam's two kind filters were swapped,
and the full suite ran **97 tests with exactly 3 failures**,
all in the batch's own new tests
(`TestDemandTotalsNegativeControl.test_canonical_but_mutant_swaps`,
`TestForecastDerivation.test_view_derives_recorded_totals_exactly`,
`TestForecastDerivation.test_ratio_whole_renders_int_and_empty_capacity_none`)
— no core test failed. The file was restored from
`scratch/extensions.py.premutation`, verified byte-identical
by SHA-256 (`scratch/extensions.py.sha256`), and the suite
re-ran green. Recorded in tests/README.md; drill output in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / honesty notes

- Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the core service layer is
  untouched and all seven core modules are byte-identical.
- No record in this unit streams telemetry, senses a
  position, dispatches or controls a vehicle, optimizes a
  route, connects to a logging device, evaluates a
  compliance limit, projects a forecast, communicates with a
  charging station, moves money, computes a score, operates
  a platform, or hosts anything; the `*_here: False` labels
  are on the records themselves, not only in this document.
- Position data exists here only as caller-reported labels
  held verbatim; there is no coordinate field in any shape,
  and the recursive scan pins latitude/longitude/coordinate
  keys absent alongside the score-shaped keys.
- Operator privacy carries from the core unchanged: extension
  records bind operators by core record id or opaque
  caller-supplied reference only; no shape here can hold a
  real name, a license number, or a payment credential.
- The named absence stands: **API & integrations** (0 of 2)
  is absent from the union entirely and was not part of this
  section's entries; nothing in this unit builds or claims an
  external integration — the ELD and telematics surfaces are
  labeled reference records about external systems, not
  integrations with them.
