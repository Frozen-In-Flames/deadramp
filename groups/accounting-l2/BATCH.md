# Final GAPS batch — Group 5, Accounting L2

Unit: the 15 entries in GAPS.md under "Group 5 — Accounting L2
(21 forks)" (inventory idx 49–63). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). All extension
code is in one new module, `src/accounting/extensions.py`
(`AccountingExtensions`, wrapping the core `AccountingStore`); every
existing core module is byte-identical to its pre-batch state. Full
suite: 219 tests before, **246 tests after, OK**, including the fresh
mutation-verified negative control recorded in `tests/README.md`.

No entry was re-judged: on a close reading of UNION-SPEC.md each
drafted disposition fits. Two scope notes, recorded rather than
treated as re-judgments: (1) "AI / analytics & BI" is built as
deterministic rules over the core's exact posted statements, labeled
`method: deterministic_rules` in every result — no learned model or
inference is claimed, matching the core's honesty note that its
reporting is exact computed statements, not AI/BI analytics.
(2) "Records retention" builds the retention record and the
derived eligibility check; disposition itself stays with the
embedding organization's records schedule per PLATFORM-LAYER.md.

| Entry (GAPS.md text) | Disposition | Built (module: `accounting/extensions.py`) |
|---|---|---|
| AI / analytics & BI | built | `analytics_summary` (revenue/expense/net + integer-bps margin and expense ratios derived at read from the core income statement and trial balance), `detect_anomalies` (per-account movement change in bps vs a prior period, threshold-flagged, derived at read) |
| Project / program / portfolio management | built | `create_project` (unique code per book), `record_project_cost`, `project_status` (spent / remaining / over-budget derived at read; spend is never stored on the project), `list_projects` |
| Risk register / GRC suites (separation of duties, approvals, and the audit trail are the in-core seed) | built | `create_risk` (likelihood/impact 1–5, opaque `owner_ref`), `risk_exposure` (likelihood × impact and band derived at read, never stored), `mitigate_risk`, `list_risks` |
| Audit management workbenches (the core carries the audit trail, not audit management) | built | `create_audit_plan`, `add_workpaper` (opaque `document_ref`), `create_finding` (severity enum), `close_finding` (separation of duties: the creator may not close their own finding, AC-5), `list_findings` |
| Fixed-asset registers | built | `register_fixed_asset` (integer cents; salvage < cost enforced), `asset_book_value` (straight-line depreciation, accumulated and book value derived at read, never stored), `list_fixed_assets` |
| Records retention | built | `create_retention_record` (opaque `record_ref`, category, period, term in months), `retention_disposition` (age and disposition eligibility derived at read) |
| Forecasting / EPM | built | `create_forecast` (base period, growth in bps), `derive_forecast` (projects the base period's posted net income forward period by period; the projection is derived at read, never stored) |
| Supply chain | built | `create_purchase_order` (line amounts and total computed by the build, vendor as opaque `vendor_ref`; records only, no ordering executes), `record_receipt` (over-receipt rejected), `purchase_order_status` (ordered / partially_received / fulfilled derived at read from receipts) |
| GovCon / grants | built | `create_grant_award` (ceiling in cents, indirect rate in bps), `record_grant_draw` (indirect computed; the signature guard `_check_draw_within_ceiling` rejects any draw that would exceed the ceiling, whole), `grant_status` (drawn / remaining derived at read) |
| Crypto investigation | built | `create_crypto_case` (opaque `wallet_ref`), `record_crypto_transaction` (integer smallest units, in/out), `crypto_case_summary` (in/out/net units derived at read). Records only: no chain access, no pricing or conversion |
| Time tracking | built | `record_time_entry` (opaque `worker_ref`, integer minutes, 1440/day cap), `time_summary` (period totals and per-worker totals derived at read) |
| E-signature | reference (stub-engine) | `create_signature_request`, `list_signature_requests` — labeled reference implementation: every record carries `reference_stub: True` and status `recorded_reference_only`; no signing service is contacted and nothing is signed |
| Payroll | built | `create_payroll_run`, `add_pay_line` (deductions may not exceed gross), `payroll_summary` (gross / deductions / net derived at read; net is never stored on a pay line). Records pay; disbursement is an external rail, not this substrate |
| Tax | built | `create_tax_filing` (opaque `jurisdiction_ref`, taxable base in cents, rate in bps), `tax_due` (base × rate derived at read, never stored). Computes a recorded figure; files nothing |
| Forensic investigation | built | `create_forensic_case`, `add_evidence_item` (hex `content_hash` validated, 8–128 chars), `record_custody_transfer` (append-only custody list, each transfer audited), `forensic_case_summary` (counts derived at read) |

Cross-cutting, per the group's doctrines: money is integer cents
with booleans/floats rejected at every money boundary; all parties
are opaque `*_ref` strings and record shapes are pinned by tests so
no field can hold a name, email, phone, or identifier; book
membership is enforced by delegating to the core store's `get_book`
and role permissions via `accounting.access` (viewer and non-member
denials are pinned by tests); every mutation is recorded on the
core audit log with an `ext_`-prefixed action.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern (extensions
land in `src/` with tests); the service layer is untouched.
