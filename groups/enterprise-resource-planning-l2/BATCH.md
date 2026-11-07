# Final GAPS batch — Singleton 66, Enterprise Resource Planning L2

Unit: the 16 OPEN entries in GAPS.md under "Singleton 66 —
Enterprise Resource Planning L2 (Infor Government Solutions,
FR1710033970)". (The section's 17th entry, the GovCloud / ITAR /
CJIS / HIPAA platform-layer entry, was already closed as
re-scoped under PLATFORM-LAYER.md before this unit started and
is not touched here.) Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). All
extension code is in one new module, `src/erp/extensions.py`
(`ErpExtensions`, wrapping the core `ErpStore`); every existing
core module is byte-identical to its pre-batch state (SHA-256
verified against the pre-batch hashes). Full suite: 81 tests
before, **118 tests after, OK**, including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

How "built" reads in this substrate, per the unit brief:
build-extension is the in-substrate form — records plus
deterministic derivations over the group's OWN records. This
group's core already does real money math (balanced entries,
integer cents, totals derived at read), so a payroll or close
calculation over records the build itself holds is a
derivation, not an external execution. Anything that would
execute against an external system, present a live portal, run
a network, or operate a gateway is records/reference form only,
labeled where the triage says stub.

No entry was re-judged: on a close reading of UNION-SPEC.md
each drafted disposition fits, with the scope notes recorded
per entry below rather than treated as re-judgments — chiefly
that the scheduling "optimizer" is built as a deterministic
coverage derivation that performs no optimization search and
claims none (its method is labeled on every view), and that
the supplier exchange's notices are records of publications
that never leave the substrate (each carries
`reference_transport: True`, `delivery_state: recorded_only`).

| Entry (GAPS.md text) | Disposition | Built (module: `erp/extensions.py`) |
|---|---|---|
| Suite platform & portal presentation layer | built | `create_portal_page`, `add_portal_widget` (position unique per page), `portal_layout` (widgets ordered by recorded position, derived at read; the stored list keeps recording order), `list_portal_pages`. Configuration records and a derived layout only — no page is rendered and no portal is served |
| Data lake & schema-on-read engine | built | `register_lake_dataset` (one of the 8 core record kinds + a declared field list), `lake_query` (the schema applied at read over the core's CURRENT records — nothing is materialized, so later records appear in later queries; the stored dataset holds no rows), `list_lake_datasets` |
| Financial close & consolidation engine | built | `create_close_period` (references ledger entries of one org, cross-org entries refused), `close_status` (totals and aggregate balance derived at read), `consolidation_view` (per-account debit/credit/net summed across organizations, derived at read), `list_close_periods`. No close process executes and nothing posts anywhere |
| Source-to-settle execution engine | built | `create_settle_cycle` (over a recorded purchase order), `record_payment_instruction` (the signature guard `_check_instruction_within_total` caps cumulative instructions at the order's derived total, refused whole, no id consumed; every instruction carries `payment_executed: False` — recording one disburses nothing), `settle_status` (match state derived from the order's recorded lifecycle), `list_settle_cycles`, `list_payment_instructions` |
| Manufacturing production engine | built | `create_production_order` (over a core inventory item), `record_production_output` (over-plan output refused whole; output applied to stock through the core store's own recorded adjustment), `production_status` (produced / remaining / complete derived at read), `list_production_orders`. No planning, scheduling, configuration, or shop-floor machinery |
| Supplier exchange network | built | `publish_supplier_notice` (kinds: demand / advance_ship_notice / collaboration; every record carries `reference_transport: True` and `delivery_state: recorded_only` — no notice leaves the substrate), `supplier_exchange_feed` (notices plus the supplier's purchase-order summaries, derived at read), `list_supplier_notices` |
| Talent management engine | built | `create_talent_cycle` (over a person record), `record_talent_stage` (the fork's own stage vocabulary — identified / hired / developed / rewarded / retained — forward only, by recorded action), `talent_pipeline` (counts by current stage, derived at read), `list_talent_cycles`. Stages are recorded states, never scores |
| Workforce scheduling optimizer | built | `create_schedule` (caller-recorded demand: required minutes per date), `add_shift`, `schedule_view` (per-date coverage, gap, deterministic double-booking flags, and per-person totals, all derived at read; method labeled `deterministic_coverage`). No optimization search is performed and none is claimed — the derivation computes what the records say, it does not propose assignments |
| Payroll calculation engine | built | `create_payroll_calculation` (inputs only: person, inclusive date range, hourly rate in integer cents, deduction lines in bps of gross summing to ≤ 10000), `payroll_calculation_view` (minutes summed from the person's CURRENT core time entries in range; gross = minutes × rate // 60; deductions and net derived at read — the stored record has no minutes/gross/net key), `list_payroll_calculations`. No disbursement is performed |
| Business intelligence platform | built | `create_dashboard` (definition records naming metric kinds from the build's own vocabulary), `dashboard_view` (organization counts, ledger / purchase-order / expense / payroll totals, inventory levels — all derived at read from the core's records for that organization; the definition stores no values), `list_dashboards`. No semantic layer, warehouse, or external data |
| Enterprise performance management engine | built | `create_plan` (planned debit/credit per account, integer cents), `plan_view` (actuals from the org's current ledger, variance per account, derived at read), `plan_forecast` (growth in bps applied period by period with integer floor arithmetic, derived at read), `list_plans` |
| Governance, risk & compliance engine | built | `create_risk_record` (caller-stated likelihood/impact 1–5), `risk_exposure` (product and band derived at read, never stored), `create_control_check`, `record_check_result` (pass/fail recorded exactly once), `grc_summary` (risk counts by derived band, check counts by outcome, and a permission verification read from the build's own `erp.access` matrix — verifying changes nothing), `list_risk_records`, `list_control_checks` |
| Identity federation service | reference (stub-engine) | `create_federation_record`, `list_federation_records` — labeled reference implementation: every record carries `reference_stub: True`, `hook_only: True`, and status `recorded_reference_only`. Per PLATFORM-LAYER.md decision 1 this substrate is never an IdP: the records are federation configuration hooks, and no authentication is performed |
| Integration execution & orchestration runtime (the build's registries store records and never execute) | reference (stub-engine) | `create_orchestration_record` (must reference a core workflow record of the org), `list_orchestration_records` — every record carries `reference_stub: True` and status `recorded_reference_only`. The runtime it names is not present; a test pins that the extension class exposes no execution verb (execute / run / fire / trigger / dispatch / connect) at all |
| API gateway runtime | reference (stub-engine) | `create_gateway_route_record` (must reference a core integration record of kind `api_gateway`; a route against any other kind is refused), `list_gateway_route_records` — every record carries `reference_stub: True` and status `recorded_reference_only`. No call is routed, no policy enforced, nothing throttled |
| Expense policy enforcement & fraud detection engine | reference (stub-engine) | `create_expense_policy` (category + per-line limit in integer cents), `expense_policy_evaluation` (derived at read: the report's lines in the policy's category above the recorded limit, each with its excess; carries `reference_stub: True` and method `deterministic_limit_check`), `list_expense_policies`. A finding states a recorded limit breach only — fraud is a determination this build does not make, and a recursive key scan pins that no fraud field exists on any evaluation |

Cross-cutting, per the group's doctrines: money is integer
cents with booleans/floats/strings rejected at every money
boundary; quantities and minutes are integers under the same
rule; all parties are opaque `*_ref` strings and a recursive
scan pins that no record shape can hold a score, rating,
ranking, or identifier field; role permissions are enforced
via `erp.access` exactly as the core enforces them (viewer
denials pinned by test); every extension mutation is recorded
on the core audit log with an `ext_`-prefixed action; derived
values are derived at read and never stored — the stored
records' exact key sets are pinned by tests for the portal,
lake, close, settle-cycle, production-order, schedule,
payroll-calculation, dashboard, and risk surfaces.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
