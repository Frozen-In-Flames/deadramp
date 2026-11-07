# Final GAPS batch — Group 23, Accounting L3-adjacent

Unit: the 15 GAPS.md entries for this section. Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 14
build-extension, 1 stub-engine. All 15 are accounted for below; no
entry was dropped, and no disposition was re-judged — a close
reading of `UNION-SPEC.md` confirmed each drafted disposition: every
build-extension entry is records/derivation-shaped in the group's
own taxonomy language, and e-signature is the one entry whose honest
form is a labeled reference record (execution against an external
signing service is not a records-substrate function).

## What landed

- **New module:** `src/accounting/extensions.py` —
  `ExtensionStore`, an in-memory records substrate for the Extended
  families. All pre-existing core modules (`store.py`, `audit.py`,
  `access.py`, `errors.py`, `service.py`, `__main__.py`,
  `__init__.py`) stay **byte-identical**; the High-baseline uplifts
  (hash-chained audit, fail-closed writes, auditor role, logon
  lockout) are untouched and keep their shipped tests. The extension
  store writes to the same hash-chained `AuditLog`, with the same
  fail-closed rollback on `AuditWriteError`, the same integer-cents
  validators (imported from the core store, not re-implemented), the
  same RBAC actions (`enter` / `approve` / `pay` / `read`; the
  auditor role therefore holds no operational permission on this
  surface, pinned by test), separation of duties on every approval
  step, and derived-never-stored values wherever a value is a
  derivation (derived keys are absent from stored records, pinned
  by test).
- **Tests:** `tests/test_gaps_batch.py`, 54 tests. Full suite:
  **273 before → 327 after, OK.**
- **Fresh mutation-verified negative control:** the budget-cap
  check in `record_project_spend` was mutated to compute the
  prior-spend sum but never compare it to the budget
  (`if spent + amount_cents > project["budget_cents"]:` →
  `if spent < 0:`). Full suite: **327 ran, 2 failed**
  (`test_spend_cap_and_derived_view`,
  `test_negative_control_budget_cap_mutant`). Restored with SHA-256
  verification and re-run green. Full record in `tests/README.md`.

## Per-entry dispositions

| # | GAPS.md entry | Disposition | Built (module `accounting.extensions`, class `ExtensionStore`) |
|---|---|---|---|
| 1 | AI / analytics & BI (this group's only claimed Extended family, 1 of 2) | build-extension | `create_dataset`, `record_insight`, `analytics_summary` (counts and metric total derived at read; records of analytic results — no inference is performed or claimed) |
| 2 | Project / program / portfolio management | build-extension | `create_project`, `activate_project` (SoD), `record_project_spend` (capped at budget), `project_view` (spent / remaining / utilization_bps derived) |
| 3 | Risk register & GRC suites beyond the separation-of-duties / audit seed | build-extension | `create_risk`, `add_risk_control`, `accept_risk` (SoD), `risk_view` (score = likelihood x impact_cents and control count derived) |
| 4 | Audit-management workbenches | build-extension | `create_engagement`, `add_finding`, `resolve_finding` (SoD), `close_engagement` (refused while findings are open), `engagement_view` (counts derived) |
| 5 | Fixed-asset registers | build-extension | `register_fixed_asset` (salvage ≤ cost), `dispose_fixed_asset` (SoD), `asset_view` (straight-line depreciation derived, book value floored at salvage) |
| 6 | Records retention beyond the audit seed | build-extension | `create_retention_policy`, `assign_retention`, `record_disposition` (SoD; a decision record — assignments are never deleted, per the platform-layer AU-11 decision), `retention_view` (due date and due-ness derived) |
| 7 | Forecasting / EPM | build-extension | `create_forecast` (duplicate labels and floats rejected), `approve_forecast` (SoD), `forecast_variance` (per-label and total variance derived; actuals are inputs only, never stored) |
| 8 | Supply chain | build-extension | `register_supplier`, `create_purchase_order`, `approve_purchase_order` (SoD), `record_receipt` (capped at ordered quantity), `purchase_order_view` (total / received / remaining / fulfillment derived; no stored total key) |
| 9 | GovCon / grants specifics | build-extension | `create_award`, `activate_award` (SoD), `record_award_cost` (direct/indirect, capped at ceiling), `award_view` (split, total, remaining derived) |
| 10 | Crypto investigation | build-extension | `create_crypto_case`, `add_wallet_observation`, `close_crypto_case` (SoD), `crypto_case_view` (observation count, distinct wallets, total observed derived). Records only: no tracing, clustering, or external lookup; wallet identifiers are opaque refs and the observation record shape is pinned to exactly six keys |
| 11 | Time tracking | build-extension | `record_time_entry` (whole minutes, 1..1440), `approve_time_entry` (SoD), `time_summary` (total and approved minutes derived per opaque worker ref) |
| 12 | E-signature | **stub-engine** | `create_signature_request`, `record_signature_event`, `signature_request_view`. Labeled reference implementation: every request and event record carries `reference_stub: True` (pinned), the only request status is `recorded`, and the event vocabulary (`prepared`, `viewed`, `signed_declared`) contains no state claiming a document was sent or signed through a signing service. Nothing executes against any external system |
| 13 | Payroll | build-extension | `create_payroll_run`, `add_pay_item` (deductions ≤ gross), `approve_payroll_run` (SoD, non-empty), `record_payroll_disbursement` (records disbursement of an approved run; `pay` permission; not a payment rail), `payroll_view` (gross / deductions / net derived; no `net_cents` key on stored items) |
| 14 | Tax support | build-extension | `create_tax_filing`, `add_tax_line`, `finalize_tax_filing` (SoD), `tax_filing_view` (line count and total derived). Preparation records only: nothing is transmitted to any tax authority, and `finalized` names the preparation record's state, not a submission |
| 15 | Forensic investigation | build-extension | `create_forensic_case`, `add_evidence_item`, `transfer_custody` (append-only custody events), `close_forensic_case` (SoD), `evidence_view` (current custodian and chain length derived from the last custody event, never stored as a field) |

## Re-judgments

None. All 15 drafted dispositions were confirmed on a close reading
of the union spec (DECISION.md qualification 1 was considered per
entry and no correction was needed). Two scope boundaries were
recorded rather than re-judged, because they follow from the house
records-not-execution doctrine rather than from a wrong disposition:
tax support is preparation records (no transmission), and payroll
disbursement is a recorded state (no money movement) — the same
posture the core takes for payments ("records, not rails").

## Unresolved

Nothing in this unit. The platform-layer entries for this group
(MFA/IA, FIPS/SC-13, SC-28, AU-11, AC-11/AC-12) were already closed
in writing by `../../PLATFORM-LAYER.md` in the re-scope step and are
not part of this unit.
