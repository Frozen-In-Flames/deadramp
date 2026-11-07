# Final GAPS batch — Untiered Set 16, Human Resources (2 forks, tier null)

Unit: the 7 OPEN entries in GAPS.md under "Untiered Set 16 —
Human Resources (2 forks, tier null)" (inventory idx 905–911).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07): 5 build-extension, 2 stub-engine — **exactly as
triaged** in `../../gaps-batch/inventory.json`. **No
re-judgments**: on close reading against this set's union spec,
every drafted build-extension entry has an honest records form in
this substrate, and both stub-engine entries are engine-over-
external-system entries whose labeled reference form is the
drafted one. No entry needed a corrected disposition under
DECISION.md qualification 1.

All extension code is in one new module, `src/hr/extensions.py`
(`HrExtensions`, wrapping the core `HrStore`); every existing
core module is byte-identical to its pre-batch state (SHA-256
verified against the pre-work baseline recorded in
`scratch/extensions_baseline.sha256`; `store.py` still hashes to
the shipped `ec34ab5e…`). Full suite: 96 tests before, **132
tests after, OK**, including the fresh mutation-verified
negative control recorded in `tests/README.md` (the payroll net
sign-flip: 132 ran, exactly 3 failures under mutation, restored
and re-verified).

**Tier discipline carries onto the new surface.** This set is
tier null: no record or derived view in the extension carries a
tier, CMMC, baseline, FedRAMP, or impact-level key — pinned by a
recursive scan over every stored extension record and every
derived view in `tests/test_gaps_batch.py`. Dayforce's documented
control claims (federation, IAL2/AAL2, FIPS 140-3) remain the
fork's claims about itself; the federation entry below closes
them as reference records, not as build attainment, and nothing
here converts the fork's Moderate prose into a tier.

**The privacy discipline binds the extension exactly as it binds
the core.** Person-bound records are keyed by opaque `person_ref`
only and employee-scoped as the core scopes them. The core
privacy test's forbidden-key set is walked over every stored
extension record and every derived view; no public method on the
surface accepts a name-, identifier-, or content-shaped
parameter (signature scan, including a no-`**kwargs` pin), and
smuggled `email=` / `phone=` / `ssn=` / `content=` keyword
arguments raise `TypeError`. Eligibility and access outcomes are
recorded labels, never computed predicates over people.

| Entry (GAPS.md text, idx) | Disposition | Built (module: `hr/extensions.py`) |
|---|---|---|
| Payroll processing engine (905) | built | `create_payroll_run` (`prn-`, period dates validated, end not before start), `add_pay_statement` (per-person statement bound to a core person record; gross and deduction amounts are integer cents as reported — floats/bools rejected; duplicate statement per person per run rejected; closed runs refuse statements), `set_payroll_run_state`, `get_payroll_run` / `list_payroll_runs` — views derive each statement's net and the run totals at read via the `_derive_net_cents` seam; the stored statement carries gross and deductions only, no net or total key anywhere (pinned). The run record states `paid_here: False` and `executed_here: False`: this is a record of payroll, never a payment. Employee readers see only their own statements and totals over them. |
| Expense tracking & management (906) | built | `create_expense_report` (`exp-`, bound to a core person), `add_expense_line` (category from a fixed label set; integer cents, strictly positive; optional ISO incurred date and opaque receipt `note_ref` — receipt content is never accepted or held; closed reports refuse lines), `set_expense_report_state` (draft/submitted/approved/rejected/closed as recorded labels — an approval decides nothing about payment), `get_expense_report` / `list_expense_reports` — the report total and line count are derived at read; the stored record carries no total key (pinned); the record states `reimbursed_here: False`. Employee-scoped reads. |
| Project time tracking & resource scheduling engines (907) | built | `record_time_entry` (`tme-`, caller-recorded integer minutes — floats/bools/zero/negative rejected; `source: "recorded"`), `create_schedule_assignment` (`sch-`, the assignment held as data with `assigned_automatically: False` — no assignment is computed and no optimization is implied), `project_time_summary` / `person_time_summary` — deterministic counts and sums (entries, recorded minutes, assignments, scheduled minutes, distinct persons) derived at read, `derived: True`, `stored: False`; the project summary requires `report_read`, as in the core report. |
| Employee communications & messaging platform (908) | built | `create_communication` (`com-`, channel label + opaque `audience_ref` + opaque `message_ref`; the record states `messages_held_here: False` — no parameter on the surface can accept message content, pinned by TypeError tests), `record_delivery_receipt` (`rcp-`, the transport's reported outcome label and optional reported count, held verbatim), `get_communication` / `list_communications` — receipt count and latest outcome derived at read. Transport receipts carry the communications adjudicated form: `reference_transport: True`, `delivered_here: False`. Nothing is sent. |
| Document management services (909) | built | `register_document` (`doc-`, opaque `document_ref`, unique; kind label; retention label held as data; optional SHA-256 digest validated as a 64-character hex string and normalized to lowercase), `add_document_version` (appends to the version chain), `get_document` / `list_documents` — current version, version count, and current digest are derived at read from the recorded chain; the stored record carries no current-version key (pinned). The record states `content_held_here: False` and `stored_here: False`: this is a registry of references and digests — distinct from the founding group's document & template *assembly* engines, which generate documents from records; nothing here generates, stores, or renders a document. |
| Identity federation / privileged access management services (the documented side of an IdP; the build ships hooks, not an IdP) (910) | reference (stub-engine) | `create_federation_record` (`fed-`, provider and protocol labels naming systems this build does not federate with), `record_access_review` (`pam-`, bound to a core person; the review outcome is a label reported by the privileged-access system outside this build, held verbatim) — every record carries **`reference_stub: True`** and state `recorded_reference_only`; the federation record states `identity_provider: False` and `federated_here: False`, the review record `determined_here: False` and `managed_here: False`. Pinned by test: creating them changes no core record. Grounding: PLATFORM-LAYER.md decision 1 — identity, federation, and PAM stay with the embedding organization; Dayforce documents them for itself, and that documentation does not transfer. |
| Security operations engines: continuous monitoring, vulnerability management, incident response (documented by one fork; the build performs none of them) (911) | reference (stub-engine) | `record_monitoring_report` (`mon-`), `record_vulnerability_report` (`vul-`, severity is the reporting system's label, held verbatim — no severity is computed here), `record_security_incident` (`inc-`, optionally bound to an existing core personnel case, which stays byte-identical, pinned), `security_operations_summary` (counts by family derived at read) — every record carries **`reference_stub: True`** and state `recorded_reference_only`, with `monitored_here` / `detected_here` / `scanned_here` / `responded_here` False on the respective records. The build records an audit log; it operates no monitoring, scanning, or response service. |

Cross-cutting, per the group's doctrines: amounts are integer
cents and minutes are integer minutes, validated at the boundary
(floats and booleans rejected); every computed figure (payroll
nets and totals, expense totals, time summaries, document
current version, communication receipt views, both summaries) is
derived at read and stored nowhere; RBAC rides the core's fixed
action set (mapping stated in the module docstring), enforced
before any state change or id allocation, so failed operations
consume no id and change nothing; successful extension mutations
audit on the core log with `ext_`-prefixed actions. The surface
is store-level only, like the founding tier's batch surface: the
HTTP service and CLI are unchanged, and no core module was
modified for this unit.
