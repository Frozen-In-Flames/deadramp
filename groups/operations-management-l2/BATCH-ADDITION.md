# Final GAPS batch — Remainder Addition, Operations Management L2

Unit: the 13 OPEN entries of the "Remainder Addition —
Operations Management L2 (+20 forks)" section in the repo-root
GAPS.md (inventory idx 539–551). This is a SECOND batch unit in
this group directory: the first unit (the original Group 36
section) shipped just before it, and its module
`src/opsmgmt/extensions.py` and tests `tests/test_gaps_batch.py`
are part of the shipped tree and stay **byte-identical** here,
as do all seven pre-existing core modules (`store.py` remains
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`;
`extensions.py` remains
`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`,
both SHA-256 verified before and after). The "Remainder
Addition — Operations Management L1 (+3 forks)" and "No-Signal
Addition — Operations Management L2" sections are different
units; nothing in them is touched or absorbed here.

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/opsmgmt/verticals.py` (class `OpsVerticals`, wrapping the
core `OpsStore`), plus `tests/test_gaps_batch_addition.py`.

Group discipline, applied to every entry: each vertical is a
records surface over the group's own substrate concepts
(directory, projects, assets, work orders, inspections, usage)
— domain records with lifecycles held as recorded states and
counts/totals derived at read. Nothing executes in any domain:
no print job prints, no shipment moves, no ticket
auto-resolves, no package is tracked live, no ERP transaction
posts. Financial-shaped records (leases, journal entries,
payroll records, contract finance views) are integer-cents
data records with recorded states; floats and booleans are
rejected at the boundary. All `*_ref` parameters are opaque
tokens (whitespace, URL, hostname, and IP-shaped values
rejected), and links into the core substrate use core ids
validated through the core store. RBAC reuses the founding
16-action matrix with no new actions (mapping table in the
module docstring); successful mutations audit as `vert_*`
actions on the core log, denied attempts as `vert_*:denied`.

## Per-entry dispositions

### Build-extension (12) — records form in `opsmgmt.verticals`

1. **Managed print services engine (Canon, Xerox)** —
   `register_print_device` / `record_meter_reading` /
   `record_print_job` / `get_print_device` /
   `list_print_devices` / `list_meter_readings` /
   `list_print_jobs` / `print_summary`. Print-device records
   over opaque references (optionally linked to a core asset),
   integer meter readings stored as reported
   (`collected_here: False`), and print-job records whose
   status is stored exactly as reported (`printed_here:
   False` on devices, jobs, and the summary). The summary
   derives device counts by kind, job counts by reported
   status, and job/meter page totals at read.
2. **Supply chain & logistics execution suite (Manhattan)** —
   `record_shipment` / `update_shipment_status` /
   `record_supply_order` / `record_inventory` /
   `list_shipments` / `list_supply_orders` / `list_inventory`
   / `supply_chain_summary`. Shipment records with
   recorded/reported states over opaque origin/destination
   references (`moved_here: False`), distributed-order records
   (`fulfilled_here: False`), and integer inventory-quantity
   records; the summary derives counts by status and sums
   inventory quantities by SKU at read. No shipment moves and
   no order is fulfilled here.
3. **Product lifecycle management (PLM) platform (PTC)** —
   `create_product` / `advance_product_stage` /
   `record_product_revision` / `record_product_change` /
   `get_product` / `list_products` / `list_product_revisions`
   / `plm_summary`. Product records whose lifecycle stage
   (concept/design/validation/production/retired) is held as
   data and recorded as reported, revision records with
   labels verbatim, and change records (`applied_here:
   False`). The summary derives product counts by stage at
   read; the stored product carries no count.
4. **IT service management (ITSM) suite (Ivanti)** —
   `create_ticket` / `transition_ticket` / `approve_change` /
   `get_ticket` / `list_tickets` / `itsm_summary`. Ticket
   records (incident/problem/change/request) with priority
   and recorded/reported lifecycle states; recorded_closed
   and cancelled are terminal. No ticket auto-resolves
   (`resolved_here: False`). Change approvals are recorded
   under an inline separation-of-duties check: the approver
   may never be the ticket's creator.
5. **Infrastructure maintenance management system
   (InfraLink)** — `create_maintenance_plan` /
   `record_maintenance_issue` / `record_material` /
   `list_maintenance_plans` / `list_maintenance_issues` /
   `list_materials` / `infra_summary`. Maintenance-plan
   records over core assets (interval held as integer data;
   `scheduled_here: False` — preventive-maintenance
   scheduling substance is recorded, nothing is scheduled or
   dispatched), issue records optionally linking a core work
   order validated through the core store, configuration
   baselines ride as plan/issue record data, and integer
   material-inventory quantity records summed by reference
   in the derived summary.
6. **Facilities & real property management suite / IWMS
   (FM:Systems, GoRPM, IBM TRIRIGA overlap)** —
   `create_facility` / `create_space` / `record_lease` /
   `record_move_request` / `get_facility` / `list_facilities`
   / `list_spaces` / `list_leases` / `facilities_summary`.
   Facility and space records (capacity an integer held as
   data), lease records in integer cents with recorded
   states (`paid_here: False` — space, move, lease, portfolio,
   and capital-project substance rides as these records and
   the derived summary), and move-request records with
   reported states (`moved_here: False`). The summary derives
   space counts by kind, lease counts by status, and the
   lease-cents data total at read.
7. **Case management platforms incl. EEO + FOIA (Tyler
   Federal, AINS eCase)** — `open_case` /
   `record_case_evidence_ref` / `transition_case` /
   `record_case_decision` / `record_foia_production` /
   `get_case` / `list_cases` / `list_case_evidence` /
   `list_case_decisions` / `list_foia_productions` /
   `case_summary`. Follows the data-management precedent:
   case records (eeo/foia/general/investigation/
   correspondence) whose shape is pinned by test to exactly
   ten keys with no field that can hold content; evidence
   held as opaque references only (`content_held_here:
   False`); decision records under the named seam
   `_check_decider_not_opener` (the decider may never be the
   case's opener — this unit's fresh negative control);
   FOIA production records (FOIA cases only) whose
   release/production state is a recorded reported state
   with `released_here: False` throughout — nothing is
   released or produced here. Correspondence and
   investigations ride as case types on the same surface.
8. **Business process modeling, process mining & enterprise
   architecture platform (Software AG ARIS / ALFABET)** —
   `create_process_model` / `update_process_model` /
   `record_reported_analysis` / `get_process_model` /
   `list_process_models` / `list_reported_analyses` /
   `process_summary`. Model records (process/architecture/
   value_chain) with element labels held as data, versioned
   on update, configuration-shaped so writes ride
   `workflow_write` exactly as the core workflow registry.
   Process mining is **reported-analysis records only**:
   counts exactly as reported by an external tool, with
   `computed_here: False` and `mined_here: False` — no event
   log is ingested and no mining happens here.
9. **Mail & package operations (Pitney Bowes)** —
   `record_mail_item` / `update_mail_item_status` /
   `register_locker` / `list_mail_items` / `list_lockers` /
   `mail_summary`. Mail/package item records (multi-carrier
   substance rides as an opaque `carrier_ref`) with
   recorded/reported states and smart-locker records
   (`operated_here: False`). No package is tracked live
   (`tracked_live_here: False`) and nothing is shipped
   (`shipped_here: False`); a status update stores the newly
   reported state and delivers nothing.
10. **Strategic portfolio & agile planning platforms
    (Clarity, Rally)** — `create_portfolio` /
    `create_initiative` / `record_roadmap_item` /
    `get_portfolio` / `list_portfolios` / `list_initiatives`
    / `list_roadmap_items` / `portfolio_summary`. Portfolio,
    initiative, and roadmap-item records over core projects;
    cross-team planning substance rides as iteration labels
    held as data. Priority is stored verbatim as a label
    (`priority_label`); no score, ranking, or prioritization
    is computed (`ranked_here: False`, pinned by test).
11. **Back-office ERP suite (Accenture)** —
    `record_journal_entry` / `record_payroll_record` /
    `list_journal_entries` / `list_payroll_records` /
    `erp_summary`. Journal-entry records (debit/credit) and
    payroll records over core persons, both in integer cents
    with recorded states. **No transaction posts:**
    `posted_here: False` and `paid_here: False` on every
    record and on the summary; a `reported_posted` journal
    status is a state reported by an external ERP, stored as
    reported. Financial-management and property/asset
    accounting substance rides as account references and the
    derived debit/credit/payroll cent totals, summed at read
    — the stored entries carry no total (pinned by test).
12. **Contract progress management application (iSite)** —
    `create_contract` / `record_milestone` /
    `record_progress_report` / `record_contract_finance` /
    `get_contract` / `list_contracts` / `list_milestones` /
    `list_progress_reports` / `contract_summary`. Contract
    records over core projects/organizations, milestone
    records with reported states, task/program views riding
    as milestone and progress records, progress-report
    records whose percent (integer 0–100) is stored exactly
    as reported with `computed_here: False` (no progress is
    calculated from milestones, and the summary never
    averages percents — pinned by test), and finance-view
    records in integer cents as data (`paid_here: False`),
    summed at read.

### Stub-engine (1) — labeled reference implementation

13. **Enterprise asset management depth: predictive
    maintenance / asset health / IoT telemetry analytics
    (IBM Maximo)** — `register_health_reference` /
    `record_telemetry_analytics_reference` /
    `list_health_references` /
    `list_telemetry_analytics_references` / `maximo_summary`.
    House stub form: health/predictive references carry a
    label stored exactly as an external engine reported it,
    with `reference_stub: True`, `predicted_here: False`, and
    `computed_here: False`; telemetry-analytics references
    carry counts exactly as reported, with
    `reference_stub: True`, `reference_transport: True`,
    `computed_here: False`, and `collected_here: False`. No
    prediction, health score, or analytics value is computed
    here, and no record shape carries a score field (pinned
    by test). The summary is counts only.

## Re-judgments

None among the 13 entries. Every build-extension entry fit
its drafted disposition on a close reading of UNION-SPEC.md
and ADDENDUM.md §5: each vertical's substance presupposes
records over this group's substrate (assets for print fleets
and maintenance plans, work records for tickets and issues,
projects for portfolios and contracts, usage-shaped integer
quantities for meters and inventories), and each engine
behavior above the records (printing, moving, resolving,
tracking, posting, releasing, mining) is carried as a
recorded/reported state with its `*_here: False` label rather
than performed. The Maximo entry fit its drafted stub
disposition exactly: its claims are predictions and analytics
over external telemetry, which have no honest records form
that computes them, so they ship labeled.

## Tests and negative control

- Suite: **184 before → 228 after, OK** (44 new tests in
  `tests/test_gaps_batch_addition.py`, at least one per
  entry, plus cross-cutting RBAC/audit, no-id-on-failure,
  copies-are-copies, and independence pins). All pre-existing
  modules — core and the first batch unit's
  `extensions.py`/`test_gaps_batch.py` — are byte-identical
  (SHA-256 verified) and their tests pass unchanged.
- Fresh mutation-verified negative control: the
  decider-not-opener guard `_check_decider_not_opener` in
  `src/opsmgmt/verticals.py`. The in-test control
  (`TestDeciderNotOpenerNegativeControl`) asserts the
  canonical expectation, that a no-op mutant of the seam
  would not produce it, and that treating the mutant's
  outcome as expected fails. Live drill on the real file:
  the guard's condition was patched to `False` (guard
  disabled); the full suite ran: **228 tests, exactly 2
  failures** —
  `test_gaps_batch_addition.TestCaseManagement.test_opener_may_not_decide_canonical`
  and
  `test_gaps_batch_addition.TestDeciderNotOpenerNegativeControl.test_decider_guard_canonical_but_mutant_not`.
  The file was restored from
  `scratch/verticals.py.premutation` and verified SHA-256
  identical
  (`8fb9943f0680f74abfad35d9e9ca9483cdaee14f598dfd5e550fe1be1be8131b`)
  and the suite re-ran green. Recorded in tests/README.md;
  raw drill output in `scratch/gaps_addition_mutation_run.txt`.

## Unresolved

Nothing unresolved within this unit. The verticals surface
is a store-level surface only, matching the batch pattern:
no HTTP routes were added (the founding `service.py` is a
core module and stays byte-identical), so the extension is
consumed in-process, like the other groups' batch extensions.
