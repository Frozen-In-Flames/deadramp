# Final GAPS batch — Group 31, Finance L2

Unit: the 10 OPEN entries in GAPS.md under "Group 31 — Finance
L2 (2 forks)" (7 `build-extension`, 3 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 337–346). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
required re-judgment**: each fit its drafted disposition on a
close reading of this group's spec, in the forms stated below.

All extension code is in one new module,
`src/finance/extensions.py` (`FinanceExtensions`, wrapping the
core `FinanceStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified against the pre-work
baseline; `store.py` still
`f905061dbe5d45ae3ef64333a1a62a1f05af8fadbf0e5d01608cd6ad643f7c9e`,
the shipped hash). Full suite: 213 tests before, **267 tests
after, OK** (54 new in `tests/test_gaps_batch.py`), including the
fresh mutation-verified negative control recorded in
`tests/README.md`.

Cross-cutting, per the group's doctrines:

- **Records, not execution** is not repealed: nothing here moves
  money, books travel, lends, trades, remits, verifies an account,
  calculates wages, or streams anything. Every execution remainder
  lands as a request record (`state: recorded_*_only`) plus
  outcome reports stored verbatim as reported by the external
  system that actually acted, with the honesty label on the face
  of every record (`paid_here` / `booked_here` / `ticketed_here` /
  `delivered_here` / `disbursed_here` / `executed_here` /
  `filed_here` / `remitted_here` / `verified_here` /
  `streamed_here` / `computed_here` — all `False`).
- **Money is integer cents, everywhere**: every `*_cents` field
  is validated exactly as the core validates (Python `int` only;
  booleans and floats rejected at the boundary), and a rejected
  operation consumes no id and stores nothing — pinned per family.
- **The earned cap extends to disbursement execution requests.**
  A request draws against the same (participant, period) accrual
  as a core access request: its amount plus this surface's
  outstanding requests for that accrual may not exceed the
  accrual view's derived `available_cents` (earned minus the
  core's accessed and pending totals), enforced at the seam
  `_check_disbursement_cap` — the batch's fresh negative control.
  A request whose latest report is `reported_failed` stops
  counting as outstanding (the rail reported nothing moved); a
  `reported_paid` request keeps counting. The core's own cap and
  state are never written by this surface: a request plus a
  report leaves core disbursements, access requests, and the
  accrual view byte-identical (pinned by test).
- RBAC is enforced through the core `finance.access` matrix — the
  extension maps each operation onto an existing core action
  (creates/requests/registrations → `enter`, outcome reports and
  receipts → `record`, reads and derived views → `read`), checks
  it before any state change or id allocation, and records denied
  attempts on the core audit log as `ext_<action>:denied`; every
  successful mutation lands as `ext_<action>`. Program membership
  (the second boundary) is enforced through the core store's own
  access-checked program read, so non-members are denied and the
  platform `admin` role reaches programs it does not belong to,
  exactly as in the core. If an audit write fails, the record
  insertion and its id roll back before the error propagates
  (pinned by test).
- People are known only by the core's opaque-reference
  participants: every person-shaped field on this surface is a
  core `participant_id` that must exist in the same program, so
  the core's pinned participant shape governs this surface too.
  **No record shape in the module has a field that could hold a
  real account identifier, and no record shape carries a credit
  score field** — both absences are pinned by exact key-set tests
  and recursive key scans.
- Derived values are derived at read and never stored: GRC
  posture counts, streaming totals, payroll sync totals,
  disbursement and wellness rollups. Stored records carry no
  derived key; tests pin that.
- The stub-engine families ship as labeled reference
  implementations: every record they create carries
  `reference_stub: True` (streaming receipts additionally carry
  `reference_transport: True`).

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `finance/extensions.py`) |
|---|---|---|
| Instant disbursement execution / payment rails (ACH, wire, card networks): the execution remainder of the earned-wage-access claim; the core records disbursements and moves no money | built | `request_disbursement_execution` (`dexc-`, against a core employee participant + accrual; rail held as a label over the enum ach/wire/card; amount is integer cents capped by the earned cap at the seam `_check_disbursement_cap` against the accrual view's derived `available_cents`; `paid_here: False`, `state: recorded_request_only`), `record_disbursement_execution_report` (`drep-`, the rail's outcome stored verbatim; also `paid_here: False`), `disbursement_execution_summary` (counts/totals derived at read). A request plus a report changes no core state |
| Travel booking execution engines (live air / hotel inventory, ticketing, reservation systems): the execution remainder of the travel-booking claim; the core holds booking records only | built | `request_booking_execution` (`bexc-`, against an existing core booking, copying its participant id; action label over inventory_hold / ticket_issue / reservation_confirm; `booked_here: False`, `ticketed_here: False`), `record_booking_execution_report` (`brep-`, outcome stored verbatim, same labels). A test pins the core booking byte-identical and still `recorded` after a request plus a `reported_ticketed` report |
| Financial wellness delivery tools (the budgeting / coaching / savings products behind the offering registry): the execution remainder of the financial-wellness claim | built | `schedule_wellness_session` (`wses-`, over an existing core enrollment, copying its offering and participant ids; `delivered_here: False`, `state: scheduled_record_only`), `record_wellness_session_report` (`wsrp-`, the delivering party's outcome stored verbatim; `delivered_here: False`), `wellness_delivery_summary` (counts derived at read). Session content is delivered by others; the core enrollment is untouched |
| Lending & credit engines (0 claims; access is to already-earned wages only) | built | `create_loan_application` (`loan-`, for an existing core participant; amount is integer-cents data; `disbursed_here: False`, `underwriting_computed_here: False`, `state: recorded_application_only`), `record_loan_decision_report` (`ldec-`, the external lender's decision label stored **verbatim** — any non-empty string; `decided_here: False`; the application record is byte-identical after a report, pinned by test). No underwriting is computed and **no credit score field exists on any record shape** (recursive key scan, pinned). The founding line stands: the registry creates no credit product and disburses nothing; an application larger than any accrual is still only a record (pinned), while wage access itself stays capped by the core |
| Trading & investment execution (0 claims) | built | `create_trade_order` (`tord-`, instrument named by an opaque `instrument_ref` held as data; side buy/sell; amount integer cents; `executed_here: False`), `record_trade_execution_report` (`trpt-`, the broker's outcome stored verbatim; `executed_here: False`; the order record is byte-identical after a report). Nothing is routed, priced, or settled here |
| Tax reporting & remittance (0 claims) | built | `create_tax_preparation` (`tax-`, form label held as data; amount integer cents, zero allowed; `filed_here: False`, `remitted_here: False`), `record_tax_filing_report` (`tfil-`, the filing system's outcome stored verbatim; same labels). Nothing is filed and nothing is remitted here |
| GRC platform functions (0 claims in text; source category label only) | built | `register_framework` (`gfw-`), `register_control` (`gctl-`, the caller's own control label held as data), `map_record_to_control` (`gmap-`, the core record end must exist — participant, booking, accrual, access request, or wellness offering), `framework_posture` — counts over frameworks, controls, and mappings (by record kind) derived at read. Every record carries `compliance_asserted: False`: registering a label asserts no compliance, no control is evaluated, and no posture value is computed beyond counts |
| Streaming / real-time reporting pipelines (core reporting is computed on read from records) | reference (stub-engine) | `register_reporting_stream` (`strm-`, opaque `stream_ref`; `streamed_here: False`), `record_stream_receipt` (`strc-`, event count stored as reported; `reference_transport: True`), `streaming_summary` (totals derived at read) — `reference_stub: True` throughout; nothing is streamed, and a test pins the core program summary byte-identical across the flow |
| Banking integration & account verification (0 claims; entity shapes forbid real account identifiers by design) | reference (stub-engine) | `record_verification_request` (`bver-`, names a core participant and a method label held as data; `verified_here: False`), `record_verification_report` (`bvrp-`, the verification system's reported outcome label stored verbatim) — `reference_stub: True` throughout. **The exact key sets of both records are pinned by test, and a recursive key scan proves no field can hold an account identifier** (no `account`, `routing`, `iban`, `sort_code`, or `card_number` key anywhere); the core participant's pinned 7-key shape is re-asserted after the flow. Nothing is verified here |
| Payroll system integration & wage calculation (0 claims; accruals record amounts computed elsewhere) | reference (stub-engine) | `record_payroll_sync` (`psyn-`, sync receipt: source ref + period + participant/accrual **counts as reported**; `computed_here: False`), `payroll_sync_summary` (totals derived at read) — `reference_stub: True` throughout. The sync record's exact key set is pinned and holds **no `*_cents` field at all**: wage amounts stay computed elsewhere, and a test pins that a sync creates no accrual and changes no recorded amount |

## Named as NOT covered by this unit

- **Execution itself**, in every family that names it: no money
  moves, no ticket is issued, no loan is funded, no trade is
  executed, no return is filed, no account is verified, no wage
  is calculated, and nothing is streamed. The batch closes the
  records layer in front of those engines; the engines remain
  other systems' work, and the records say so on their face.
- **The section's platform-layer items** (encryption at rest,
  multi-tenancy, demo identities as hooks rather than an IdP) —
  not among the 10 entries; they stand on `PLATFORM-LAYER.md`,
  and no entry in this unit absorbs them.
- **The remainder-addition section for this group** ("Remainder
  Addition — Finance L2 (+4 forks)": the Momentum system of
  record, the Coupa procurement/spend-analytics engines, the
  Apptio TBM/FinOps engine, the Innovest trust platform, and
  AI/ML document processing) — a separate unit in this batch,
  still open, not absorbed here.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
