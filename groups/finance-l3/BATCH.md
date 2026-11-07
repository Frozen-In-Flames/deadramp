# Final GAPS batch — Singleton 42, Finance L3-adjacent

Unit: the 4 OPEN entries in GAPS.md under "Singleton 42 —
Finance L3-adjacent (1 fork)" (3 `build-extension`, 1
`stub-engine` in `../../gaps-batch/inventory.json`, idx 404–407).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07). **No entry required re-judgment**: each fit its
drafted disposition on a close reading of this group's spec, in
the forms stated below.

All extension code is in one new module,
`src/finance/extensions.py` (`FinanceExtensions`, wrapping the
core `FinanceStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified against
the pre-work baseline in `scratch/prebatch-src.sha256`;
`store.py` still
`6ec44f3c1568e5e53c55261e0c9c689b6e2cf2defac65d7e87f41ece658b236f`
and `audit.py` still
`c027a74b04d63f05f6b7dd374ea9450fff445a63d7233a73221d73a29b6c7c55`,
the shipped hashes). Full suite: 259 tests before, **293 tests
after, OK** (34 new in `tests/test_gaps_batch.py`), including
the fresh mutation-verified negative control recorded in
`tests/README.md`.

The unit's character, stated plainly: the founding fork is a
cloud infrastructure platform filed under Finance whose
marketplace description tags **zero** finance claims
(`UNION-SPEC.md`). Its four gap entries are not finance
functions at all — they are the fork's own substance, the
platform layer this build runs *on*. The honest build is
therefore the records layer in front of that platform, inside
this group's program-scoped substrate, following the Finance L2
batch module's conventions exactly.

Cross-cutting, per the group's doctrines:

- **The platform layer is recorded, never operated**
  (PLATFORM-LAYER.md decision 6). Nothing here provisions,
  starts, runs, verifies, enforces, screens, determines, or
  monitors anything. Every record carries its honesty label on
  its face (`operated_here` / `verified_here` / `enforced_here`
  / `screened_here` / `determined_here` / `monitored_here` —
  all `False`).
- **No money exists on this surface.** None of the four entries
  is a money function, so no record shape carries a `*_cents`
  field (or any amount field) at all — pinned by a recursive
  key scan. Where the Finance L2 surface extended the earned
  cap, this surface has no cap to extend: there is nothing to
  draw against.
- **The category's standing named absences stand.** Trading &
  investment execution above all: the extension class has no
  order, execution, or payment operation of any kind, pinned
  by test (`create_trade_order`, `execute_trade`,
  `place_trade`, `buy`, `sell`, `execute_payment`,
  `make_payment`, `transfer_funds`, `provision_region`,
  `start_region` do not exist on the class). Banking
  integration, payroll calculation, lending & credit, and tax
  remittance likewise gain no surface here.
- **Identity discipline.** A screening case names a root
  account holder by an opaque caller `account_ref` only. No
  record shape has a field that could hold a real name, a
  government identifier, or any bank or account identifier —
  pinned by exact key-set tests and the recursive key scan.
- Derived values are derived at read and never stored: the
  platform posture counts, the screening summary, and the
  monitoring summary are computed over this surface's own
  records by the module-level seam `_count_by_label`. Counts
  only: no posture value, rate, trend, forecast, average, or
  grand total is computed anywhere (the one sum on the surface,
  `total_events_reported`, is a total of *reported counts* in
  the reference family, stated as such).
- RBAC is enforced through the core `finance.access` matrix —
  the extension maps each operation onto an existing core
  action (registrations/records → `enter`, outcome and
  attestation reports → `record`, reads and derived views →
  `read`), checked before any state change or id allocation,
  with denied attempts recorded on the core audit log as
  `ext_<action>:denied`; every successful mutation lands as
  `ext_<action>`. Program membership (the second boundary) is
  enforced through the core store's own access-checked program
  read. The High apparatus binds the surface through the core:
  extension actions land on the hash-chained, fail-closed
  audit log (chain verified `(True, None)` in tests after
  extension operations); the separated `auditor` role is
  denied every extension read and write (denials audited),
  while its core audit duty — reading the trail and
  `AuditLog.query` / `verify_chain()` — works unchanged,
  pinned by test. If an audit write fails, the record
  insertion and its id roll back before the error propagates
  (pinned by test).
- The stub-engine family ships as a labeled reference
  implementation: every record it creates carries
  `reference_stub: True` and `reference_transport: True`. The
  three built families carry **no** `reference_stub` key —
  the distinction is pinned by test.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `finance/extensions.py`) |
|---|---|---|
| The cloud infrastructure platform itself (the provider's regions: compute, storage, networking, database, and the rest of the service catalog operated as infrastructure) | built | `register_region` (`regn-`, caller `region_ref` unique within the program, `operated_here: False`, `state: recorded_reference_only`), `record_region_service` (`rsvc-`, one catalog service per record: opaque `service_ref`, category over the fixed catalog vocabulary compute / storage / networking / database / other, optional label held as data), `get_region`, `list_regions`, `list_region_services`, and `platform_posture` (region / service counts and per-category counts derived at read via `_count_by_label`). The catalog layer in front of the platform: a region's services are records about the catalog, and recording one provisions nothing |
| Region operations & sovereignty properties (US-citizen / US-soil operation, ITAR environment, the regions' FedRAMP High boundary) | built | `record_region_attestation` (`ratt-`, per registered region: `attestation_kind` over the fixed property vocabulary personnel_eligibility / physical_operation / handling_environment / authorization_boundary, and the provider's `statement_label` stored **verbatim**), `list_region_attestations`, and the attestation half of `platform_posture` (counts by kind). Every record carries `attested_by_provider: True`, `verified_here: False`, `enforced_here: False`: the properties are the provider's properties of its platform, recorded as stated — this build neither verifies nor enforces one, and recording an attestation leaves the region record byte-identical (pinned by test) |
| Eligibility screening of root account holders | built | `record_screening_case` (`scrn-`, the account holder named by an opaque `account_ref` unique within the program, optional `basis_label` held as data; `screened_here: False`, `determined_here: False`, `state: recorded_case_only`), `record_screening_report` (`srpt-`, the screening operator's outcome stored verbatim from the fixed vocabulary reported_eligible / reported_ineligible / reported_pending, optional detail), `get_screening_case`, `list_screening_cases`, `list_screening_reports`, `screening_summary` (case/report counts and per-outcome counts derived at read). No check is run and no determination is computed here; a report leaves the case record byte-identical (pinned by test) |
| Collaborative continuous monitoring with the provider | reference (stub-engine) | `register_monitoring_arrangement` (`marr-`, opaque `arrangement_ref` unique within the program, optional `scope_label`; `state: recorded_arrangement_only`), `record_monitoring_report` (`mrpt-`, the arrangement's reported status from the fixed vocabulary reported_healthy / reported_degraded / reported_incident / reported_outage, plus an event count stored **as reported** — validated as a non-negative integer count, booleans and floats rejected), `get_monitoring_arrangement`, `list_monitoring_arrangements`, `list_monitoring_reports`, `monitoring_summary` (counts and the total of reported event counts derived at read) — `reference_stub: True` and `reference_transport: True` on every record; nothing is monitored here |

## Named as NOT covered by this unit

- **Operating anything**: no region is provisioned, no service
  is run, no sovereignty property is verified or enforced, no
  account holder is screened, no determination is made, and no
  system is monitored. The batch closes the records layer in
  front of those operations; the operations remain the
  provider's, and the records say so on their face.
- **The section's baseline gaps at High** (MFA / authenticator
  management IA-2(1)/(2) / IA-5, FIPS-validated cryptography
  SC-13, encryption at rest SC-28, audit retention enforcement
  AU-11, session lock / termination AC-11/AC-12) and its
  platform-layer notes (multi-tenancy, TLS only when
  configured, demo identities as hooks rather than an IdP) —
  not among the 4 entries; they stand on `PLATFORM-LAYER.md`,
  and no entry in this unit absorbs them. The build explicitly
  does **not** inherit the fork's FIPS posture or its FedRAMP
  High authorization boundary: the attestation records record
  the provider's statements about *its* regions, and transfer
  nothing.
- **The remainder-addition section for this group**
  ("Remainder Addition — Finance L3-adjacent (+1 fork)": the
  OneStream CPM engine, data integration & connector surface,
  and solution marketplace & application extensibility entries,
  idx 667–669) — a separate unit in this batch, still open,
  not absorbed here.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
