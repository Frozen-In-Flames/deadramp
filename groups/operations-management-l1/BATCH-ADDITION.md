# Final GAPS batch — Remainder Addition — Operations Management L1 (+3 forks)

Second batch unit in this directory (the first unit, shipped
earlier, is in [BATCH.md](BATCH.md)). Worked 2026-11-07 under
[../../gaps-batch/DECISION.md](../../gaps-batch/DECISION.md),
which closed the GAPS batch triage as ratified by Aries
(2026-11-07), and
[../../PLATFORM-LAYER.md](../../PLATFORM-LAYER.md).

**Unit:** the 7 OPEN entries of the GAPS.md section "Remainder
Addition — Operations Management L1 (+3 forks)" (inventory idx
613–619; the section is sourced in [ADDENDUM.md](ADDENDUM.md)
section 5). **Dispositions: 6 built, 1 reference. No
re-judgments** — every entry fit its drafted disposition in
honest records form; the boundaries are stated per entry below
rather than smoothed over.

## What landed

One new module, `src/opsmgmt/extensions_addition.py`
(`OpsExtensionsAddition`, audit prefix `exta_`), wrapping the
core `OpsStore` with the same in-memory record-store,
RBAC-guard, audit, and copied-out-reads architecture as the
first unit's `extensions.py`. All existing modules are
byte-identical (the first unit's `extensions.py` included;
verified by SHA-256 against the pre-build record). 26 new
record kinds across the seven entries. Tests:
`tests/test_gaps_batch_addition.py`, 36 tests; the full suite
runs **211 tests** (175 before this unit), all passing.

**The shape, as in every group in this repo:** records only,
derived-never-stored status. Claimed functions are closed as
records over the substrate's own core records or as reported
events; a record's current reported status derives at read from
its latest reported event through one shared seam
(`_current_reported_status`); anything that would *perform* —
book, admit, run, sense, execute, direct, sign, close, predict
— is a recorded boolean `False` on its record, or has no field
at all. This group sits at L1 (Low / LI-SaaS); no apparatus was
imported from the Moderate-tier L2 sibling.

## Per entry

### Entry 613 — built

> Workspace scheduling & reservation engine (FM:Systems, Tango; the headline function of both workplace forks; the verbatim taxonomy has no scheduling family, so this stands at zero claims while asserted in substance by 2 of 4 forks at this tier)

Reservation records in records form: **reservation records**
(`rsv`, optional core asset/project/person links validated
through the core store; the window is validated for a non-empty
interval — `ends_at` must be after `starts_at` or absent) and
**outcome records** (`rso`) storing the reported lifecycle
(`reported_reserved`, `reported_checked_in`,
`reported_completed`, `reported_cancelled`,
`reported_no_show`) verbatim. `reservation_view` derives
`current_reported_status` at read from the latest outcome (or
`"recorded"`); the stored record's status never changes and
the derived key never appears on it. **Boundary, stated:**
this build books nothing and adjudicates nothing — there is
deliberately **no** double-booking conflict rule: two records
may name overlapping windows for the same asset, because the
closed gap is the scheduling-and-reservation *records
surface*, and inventing a conflict-adjudication rule here
would fake the engine the fork actually runs. Every
reservation carries `booked_here: False`.

### Entry 614 — built

> Visitor & event management (FM:Systems)

Visitor records in records form: **visitor registrations**
(`vis`) holding an opaque `visitor_ref` (the shared reference
validator refuses anything whitespace-, URL-, address-, or
hostname-shaped, so no visitor name or credential can be
recorded) with optional core host-person and project links;
**handling events** (`vie`) storing reported lifecycle states
verbatim, with `visitor_view` deriving the current reported
status at read; and **event definitions as data** (`evt`,
versioned on update, `staged_here: False`) with **check-in
records** (`eck`) bound to an event and optionally to a
registration or a core person. Admission is never decided
here (`admitted_here: False` on registrations and check-ins
alike); check-in counts are the analytics surface's headcount
input.

### Entry 615 — built

> Interactive floor plans, wayfinding & digital signage (FM:Systems, Tango)

Definitions-as-data form: **floor-plan definitions** (`flp`)
holding zone definitions as data — each zone is exactly a
`label` and a `kind`; the zone validator **rejects any other
key**, so no coordinate or geometry value can exist anywhere
in this surface, and a plan record therefore cannot be a map.
**Signage definitions** (`sgn`, versioned; `content_text` held
verbatim as data) link a plan and a zone label, with the label
validated against the plan's zone labels. **Digital notices**
(`ntc`) hold the body text verbatim as data. `wayfinding_view`
returns a plan plus signage/notice counts derived at read.
**Boundaries, stated:** nothing is rendered, displayed,
published, or routed here (`rendered_here`,
`displayed_here`, `published_here`, `routed_here`: all
`False`; there is no routing method and signage definitions
accept no coordinate argument at all). Colleague location —
named in the forks' substance — is closed as **not present**:
no record on this surface can hold a person's location, and
the group README's honesty list records the absence rather
than closing the entry over it.

### Entry 616 — reference (stub-engine, as drafted)

> IoT sensor integration & workspace-utilization sensing (FM:Systems, Tango by catalogue substance; likewise no taxonomy family)

Labeled reference implementation, closed under the `reference`
token: **sensor references** (`sen`) holding an opaque
`sensor_ref` — the shared validator rejects anything
address-shaped, so no record can hold a sensor endpoint —
with an optional core asset link; **feed references** (`sfd`)
recording reported feed statuses verbatim and carrying
`reference_transport: True`; and **utilization reports**
(`utl`) storing reported `metric_values` verbatim (floats and
booleans rejected at the boundary — nothing here computes a
rate). All three record kinds carry `reference_stub: True`;
`utilization_view` derives feed/report counts and the latest
reported feed status at read. **Boundary, stated:** the
"engine" this entry names is a running sensor network; this
substrate holds only its references and its reported outputs
(`received_here: False`, `sensed_here: False` on every
record).

### Entry 617 — built

> Workplace analytics & optimization engine (FM:Systems, Tango, by substance)

Analytics-definitions form over this unit's own records:
**definitions as data** (`anl`) whose metric names come from
a fixed set (`reservation_count`, `active_reservation_count`,
`visitor_registration_count`, `checkin_count`, `notice_count`,
`requisition_count`, `purchase_total_cents`,
`utilization_report_count`) — metric names outside the set
are refused at the boundary, so no rate, trend, or forecast
metric can be defined; **run records** (`anr`) store **no
figures** (the record's key set is pinned by test); and
`analytics_run_view` derives the figures at read — counts of
recorded values plus the sum of recorded purchase cents,
project-scoped where the record family carries a project
link. "Active" derives through the same
`_current_reported_status` seam. **Boundary, stated:**
optimization closes on what this substrate can honestly do —
counts and sums over its own records, derived at read.
Nothing optimizes anything here (`optimized_here: False` on
definitions and runs alike), and no optimization output is
derivable from the metric set.

### Entry 618 — built

> Procurement marketplace & requisitioning engine (SCMC)

Procurement records in records form: **catalogue listings**
(`lst`, optional core vendor-organization and project links);
**requisitions** (`req`) with optional core project and
work-order links (validated through the core store), an
optional listing link of this surface, and an opaque
`requester_ref`; **purchase records** (`pur`) with money in
**integer cents** (floats and booleans rejected at the
boundary, minimum 1); **outcome records** (`puo`) storing
reported statuses verbatim, with `purchase_view` deriving the
current reported status at read; and `procurement_summary`
deriving counts, the total of recorded cents, outcomes by
reported status, and requisitions per listing at read.
**Boundaries, stated:** a listing record sells nothing and a
requisition record places no order (`ordered_here: False` on
both); purchases are records of payments, never payment
execution (`paid_here: False`); and contract utilization —
named in SCMC's substance — is **counted, never directed**:
the summary carries `directed_here: False`, and no
preferred-source or direction field exists on any record
shape on this surface.

### Entry 619 — built

> Real-estate portfolio suite: space planning, lease administration / accounting, transaction & predictive analytics (Tango catalogue excess)

Portfolio records over the substrate, the catalogue excess
bounded as records: **portfolio spaces** (`spc`, optional core
asset/project links); **space-plan definitions as data**
(`spl`) over spaces of this surface, held under the group's
registry-never-executes discipline (`executed_here: False`);
**move records** (`mov`) whose current reported status
derives at read from **outcome records** (`mvo`); **lease
records** (`lea`) with integer-cent amounts and term in
months, plus **obligation-event records** (`lee`) —
`lease_view` derives the current reported status and the
**total obligation** (recorded amount × recorded term, an
arithmetic product of two recorded integers) at read, never
stored; **transaction records** (`txn`) storing the reported
lifecycle (`reported_proposed`, `reported_under_review`,
`reported_approved`, `reported_closed`, `reported_withdrawn`)
verbatim; and **prediction reports** (`prd`) storing reported
`metric_values` verbatim with an optional opaque `model_ref`.
`portfolio_summary` derives counts (including transactions by
reported status) at read. **Boundaries, stated:** lease
*accounting* closes as recorded obligation data with a derived
sum — no amortization schedule, present value, or lease
classification is computed anywhere, and nothing is signed or
posted to any ledger (`signed_here` / `accounted_here`:
`False`); transactions close nothing here
(`closed_here: False`); space plans move no one
(`moved_here: False`); and predictive analytics ride as
verbatim reported records of an external engine's outputs —
this substrate predicts nothing (`predicted_here: False` on
every report and on the summary).

## Tests and negative control

Full suite: **211 tests, all passing** (175 before this unit;
36 new in `tests/test_gaps_batch_addition.py`, one class per
entry plus cross-cutting RBAC/audit/no-id-on-failure/copies
pins). Every view's derived key is pinned absent from the
stored record; every `*_here: False` boundary on the new
surface is pinned true-to-value by test; the analytics run
record's exact key set is pinned so no figure slot can appear;
the zone validator's no-geometry rejection is pinned; the
integer-cents and verbatim-values boundaries are pinned for
purchases, leases, utilization reports, and prediction
reports.

**Fresh negative control (this unit):** the
latest-reported-status seam (`_current_reported_status`). The
in-test control
(`tests/test_gaps_batch_addition.py::TestCurrentStatusNegativeControl`)
pins the canonical latest-event reading against an in-test
first-event mutant across two record families (reservations,
leases) and fails if the mutant's outcome is treated as
expected. **Mutation verification (live drill, 2026-11-07):**
the seam's real body (`return events[-1]["reported_status"]`,
line 340) was replaced with `return
events[0]["reported_status"]` — exactly **6 tests fail**
(`TestReservations.test_current_status_derived_never_stored`,
`TestVisitorsAndEvents.test_current_state_derived_from_latest_event`,
`TestSensorReferences.test_utilization_view_counts_and_latest_feed_status`,
`TestWorkplaceAnalytics.test_figures_derived_at_read_from_own_records`,
and both negative-control tests). Restored from the
pre-mutation copy (SHA-256 `41f5efe9…` before and after); the
suite is green again at 211. Raw drill output:
`scratch/gaps_batch_addition_mutation_run.txt`.

## Not covered (unchanged, named for honesty)

Unchanged from the first unit's note, and still true: this is
a store-level surface — there are no HTTP routes for the core
or either extension module (the CLI remains the shipped
interface), and the founding spec's gaps (identity issuance
and proofing, autonomous agent simulation, autonomous reading
or correction of logs and records, embodied presence
observation, and revenue recognition) remain named absences,
not silently closed. This unit adds one absence of its own:
**colleague location** (entry 615's substance) — no record on
this surface holds a person's location.
