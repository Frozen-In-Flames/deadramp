# Final GAPS batch — Singleton 50, Mobile Device Management (MDM) L2

Unit: the 15 OPEN entries in GAPS.md under "Singleton 50 —
Mobile Device Management (MDM) L2 (1 fork, new category)"
(inventory idx 470–484). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 11
build-extension, 4 stub-engine — the stub set is idx 471, 472,
477, 480 per `../../gaps-batch/inventory.json` (the unit brief's
stub list repeated idx 480's text with a caveat; the inventory
is authoritative and was followed per entry). The separate
GAPS.md section "Remainder Addition — Mobile Device
Management (MDM) L2 (+1 fork)" (idx 679–680) is a different
unit and is not touched here.

All extension code is in one new module,
`src/mdm/extensions.py` (`MdmExtensions`, wrapping the core
`MdmStore`); every existing core module is byte-identical to
its pre-batch state (SHA-256 verified against the pre-work
baseline; `store.py` still hashes to the shipped `8c0c787a…`).
Full suite: 89 tests before, **132 tests after, OK**, including
the fresh mutation-verified negative control recorded in
`tests/README.md` (the command-confirmation guard mutant: 132
ran, exactly 2 failures under mutation, restored and
re-verified).

**The founding constraint, carried into every entry.** The
founding fork is a Telecommunication Expense Management system
filed under MDM; its taxonomy contains no device-management
family, and the addition fork (Ivanti, a genuine MDM platform)
claimed zero families for that reason. The core-delta decision
in `ADDENDUM.md` §3 stands and binds this batch: extensions are
claim-driven records work, **not** a backdoor device registry.
Every device in this surface is an opaque caller-supplied
`device_ref`; no record shape has a field that could hold an
IMEI, serial, phone number, MAC address, or any location data.
That invariant is pinned by a recursive key scan over every
stored extension record in `tests/test_gaps_batch.py`, using
the `FORBIDDEN_KEYS` set stated in the module.

**Two entries' build forms needed stated judgments** (not
re-judgments — the drafted build-extension dispositions stand;
the forms are the honest in-substrate forms, stated rather than
smoothed over):

- *Remote wipe / lock / device command plane* (idx 481) is
  built as command **records**: a request, a confirmation gated
  by a separation-of-duties seam (the confirmer is never the
  requester — the batch's fresh negative control), and an
  outcome recorded as reported by the external plane. Every
  record carries `executed_here: False`; this build issues no
  command to any device. This parallels the core's own service
  orders, which are likewise records whose carrier-side
  execution is Extended. A build that claimed to wipe a device
  would be a fake device plane; a records plane is what a
  records substrate honestly ships.
- *Device location & tracking services* (idx 484) is built as
  tracking-service configuration/status records **only**: an
  opaque device reference, a service label, and reported
  service-state labels (active / inactive / suspended), with
  current state derived at read. **No location data exists in
  this build** — no coordinate, address, or place field exists
  on any record, and `location_data_held` is False on every
  tracking record, report, and view. What the substrate holds
  is the tracking service's enrollment and status paperwork,
  never a position. Had the entry required holding positions,
  it would have been re-judged.

One further basis stated plainly:

- *Optimization engine* (idx 470) rests on the founding fork's
  product **name** only — no description sentence claims an
  optimization function (UNION-SPEC wording-artifact log). It
  is built as recorded optimization **recommendation** records
  (subject ref, action label, rationale, and an optional
  estimated saving, all recorded verbatim as the recommender's
  data, `computed_here: False`). No optimizer runs; nothing in
  the build computes or applies an optimization.

| Entry (GAPS.md text, idx) | Disposition | Built (module: `mdm/extensions.py`) |
|---|---|---|
| Optimization engine (named from the product name only; no optimization claim exists in the description) (470) | built — recorded-recommendation form; basis in the note above | `create_optimization_recommendation` (`opt-`, subject/action/rationale/estimated saving recorded verbatim, `method: recorded_recommendation`, `computed_here: False`), get/list. Money boundary enforced (float saving rejected, no id consumed). |
| Workflow execution / routing engine (the registry holds definitions only) (471) | reference (stub-engine) | `record_workflow_execution` (`wex-`) — carries **`reference_stub: True`**, state `recorded_reference_only`, `executed: False`. Pinned by test: creating one leaves the core workflow record deep-equal and moves no order; the registry still never executes. |
| Carrier & network integration engines (carrier order execution, bill feeds, data integration) (472) | reference (stub-engine) | `create_carrier_connector` (`int-`, `connected_here: False`), `record_carrier_event` (`cev-`, order-execution requests and feed receipts as reported) — every record carries **`reference_stub: True`** and state `recorded_reference_only`; event receipts also **`reference_transport: True`**, `executed_here: False`. No carrier is contacted. |
| Bill reconciliation engine beyond registry validation runs (473) | built | `create_reconciliation` (`rec-`) — lines recorded verbatim (label, billed/expected integer cents, the reconciler's reported line status); the stored case carries **no totals** (pinned key set); `reconciliation_view` derives summed billed/expected/variance and per-status counts at read (`method: recorded_lines_derived_totals`). Line-level matching against carrier data stays outside; a case never modifies its bill (pinned). |
| Budget projection / forecasting engine (projections are recorded verbatim, never computed) (474) | built — verbatim form, per the entry's own text | `create_forecast` (`for-`) — projected obligated/spent recorded verbatim with the caller's basis (`method: recorded_verbatim`, `computed_here: False`); `forecast_view` places the recorded projection beside the core budget view's derived obligated/spent/available, each figure source-labeled; projected available is arithmetic over the *recorded* projection, labeled as such. |
| Analytics engine beyond registry summaries (475) | built | `create_analytic` (`ana-`, kinds: spending_by_period / recurring_by_kind / open_dispute_exposure), `analytic_view` — deterministic derivations over current core records at read (`method: deterministic_derivation`): bill stated sums by period; recurring-charge sums by service kind excluding disconnected items; dispute counts by status plus open disputed cents. Counts and sums only, never a score; stored nowhere. |
| Report generation engine (476) | built | `create_report_definition` (`rep-`, sections from the fixed vocabulary), `generate_report` (`rpr-`) — a run record holding the figures derived at generation time from the core organization summary for the definition's sections (the core validation-run event-record shape); pinned as a snapshot: later record changes do not rewrite an earlier run. |
| Alert delivery transport (alerts are records) (477) | reference (stub-engine) | `record_alert_delivery` (`dlv-`) — carries **`reference_stub: True`** and **`reference_transport: True`**, state `recorded_reference_only`, `delivered: False`. Pinned by test: the core alert record is deep-equal before and after; nothing is delivered. |
| Web portal / single-pane web application (478) | built | `create_portal_page` (`por-`, page ref/title/section names as configuration data, per-org ref uniqueness), `portal_view` — the recorded configurations plus the core summary counts the view would present, `served_here: False`, `rendered_here: False` on every page. No page is rendered or served. |
| Managed Mobility services operations (479) | built | `create_service_operation` (`ops-`, kinds: line_audit / rate_review / estate_cleanup / vendor_coordination / other) with a recorded lifecycle (open → in_progress → completed/cancelled; invalid jumps rejected whole), `operations_summary` — counts by kind and status derived at read. The human operations the fork's MM offering wraps around the system, in records form. |
| Mobile device enrollment & provisioning plane (480) | reference (stub-engine) | `record_enrollment` (`enr-`) — opaque `device_ref` + program label only (exact key set pinned; no identifier field), carries **`reference_stub: True`**, state `recorded_reference_only`, `provisioned_here: False`. Pinned by test: the core organization summary is deep-equal before and after; nothing is provisioned. |
| Remote wipe / lock / device command plane (481) | built — records form; judgment in the note above | `request_device_command` (`cmd-`, kinds wipe/lock/unlock), `confirm_device_command` — gated by the `_check_command_confirmer_not_requester` separation-of-duties seam (the fresh negative control), `record_command_outcome` — outcome labels as reported (`reported_completed` / `reported_failed`), only from confirmed. `executed_here: False` on every record, pinned through the full lifecycle. |
| Device policy management & compliance enforcement (482) | built | `create_device_policy` (`pol-`, requirement labels recorded as data, per-org ref uniqueness, `enforced_here: False`), `record_compliance_check` (`chk-`, results as reported, labels validated against the policy's recorded requirements), `compliance_view` — state derived at read from the latest recorded check (unknown / compliant / non_compliant), `method: derived_from_recorded_checks`. Nothing is enforced on any device. |
| Mobile application management (483) | built | `create_app_record` (`app-`, catalog records by opaque ref with a recorded version label, per-org ref uniqueness), `record_app_distribution` (`dst-`, assignment records naming an opaque device ref and a channel label, `delivered_here: False`), `app_summary` — app/distribution/distinct-device counts derived at read. Nothing is distributed, installed, or wrapped. |
| Device location & tracking services (484) | built — configuration/status form; judgment in the note above | `create_tracking_record` (`trk-`, exact key set pinned, `location_data_held: False`, per-org device-ref uniqueness), `record_tracking_status` (`tsr-`, service-state labels active/inactive/suspended as reported), `tracking_view` — current state derived at read from the latest report (or `unreported`); the stored record carries no state key (pinned). **No location data exists in this build.** |

Cross-cutting, per the group's doctrines: the founding
**privacy invariant** binds the extension exactly as it binds
the core — every stored extension record is walked against the
module's forbidden-key set (no IMEI/serial/phone/MAC/coordinate/
address/location key can exist), and devices are opaque
`device_ref` strings only. Money rides the core store's own
validators (integer cents; floats and booleans rejected at the
boundary, before id allocation). Every computed value is
derived at read and stored nowhere (reconciliation totals,
forecast-view figures, analytic views, compliance state,
operations/app summaries, tracking current state — each view
carries `derived: True`, `stored: False`). RBAC rides the
core's fixed action set through the store's scoping seam (role
permission + organization membership; mapping stated in the
module docstring), enforced before any state change or id
allocation; denials consume no id and record nothing (the
store-level convention — denial auditing lives in the service
layer), while successful extension mutations audit on the core
log with `ext_`-prefixed actions. Malformed input is rejected
whole: validation precedes id allocation on every create.
