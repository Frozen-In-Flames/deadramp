# Final GAPS batch — Untiered Set 2, Operations Management (20 forks, tier null)

Unit: the 9 entries in GAPS.md under "Untiered Set 2 —
Operations Management (20 forks, tier null)" (idx 769–777 in
`../../gaps-batch/inventory.json`; all 9 drafted
`build-extension`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **One
entry is re-judged** — AI assistants & agents, from
build-extension to a labeled reference implementation, on the
grounds stated below (DECISION.md qualification 1). Inside one
built entry, one execution-shaped component ships in reference
form in-record (charging-session control requests), following
the Data Management units' adjudicated pattern.

All extension code is in one new module,
`src/opsmgmt/extensions.py` (`OpsExtensions`, wrapping the core
`OpsStore`); every existing core module is byte-identical to
its pre-batch state (SHA-256 verified against the accounting
in this group's README; `store.py` still `8fe67ec2…`). Full
suite: 127 tests before, **161 tests after, OK** (34 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline binds the extension surface exactly as it
binds the core.** Nothing here asserts or records a tier, a
control baseline, or an equivalence: no record shape carries a
tier-shaped key, and a test scans every extension record and
derived view recursively for tier/baseline/equivalence keys
(and for floats and numeric lists). The forks' documented
control claims remain where `UNION-SPEC.md` put them — the
forks' claims about themselves, recorded in the spec; nothing
in this unit asserts a taxonomy claim or a control attainment
for any extension function. The set's standing core-boundary
decision is unchanged: the substrate is carried, not claimed,
and these extension surfaces are records machinery over it.

Cross-cutting, per the group's doctrines: RBAC is enforced
through the core `opsmgmt.access` matrix — the extension maps
each operation onto an existing core action (the core action
set is fixed) and checks it before any state change or id
allocation; denied attempts are recorded on the core audit log
as `ext_<action>:denied` and every successful mutation as
`ext_<action>`; all parties, suppliers, vehicles, and outputs
are opaque `*_ref` strings or core record ids, and no record
shape can hold a payload, content, a prompt, or a computed
score; amounts describing an external platform's work are
stored as reported, never computed here (money-shaped amounts
are integer cents, energy integer watt-hours, floats and bools
rejected at the boundary, mirroring the core's usage
discipline); derived values (program work-order counts,
produced/awarded/payment totals, current state labels,
portfolio counts) are computed at read and never stored.
Current state derives at a single seam, `_latest_label`
(latest recorded label wins), which is the batch's fresh
negative control.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `opsmgmt/extensions.py`) |
|---|---|---|
| CMMS/EAM depth (computerized maintenance management and enterprise asset management engines) | built | `define_maintenance_program` (`pm-`, a definition: name, optional core asset binding, work type, reported interval; `definition_only: True`, `performed_here: False`, `executed_here: False`), `record_custody_event` (`cus-`, append-only reported labels over a core asset; `custody_transferred_here: False`), `maintenance_program_view` — work-order counts (total / open / overdue, overdue through the core's own `_is_overdue` derivation over the core's work-order views) and custody-event count derived at read; the stored program record carries no count key (pinned by test) |
| Manufacturing execution & ERP/MRP | built | `define_bill_of_materials` (`bom-`, components as opaque `part_ref` + positive-integer quantity dicts, exact-shape validated; `definition_only: True`), `create_production_order` (`po-`, positive-integer quantity, project defaulting to the BOM's; `executed_here: False`), `record_production_outcome` (`pout-`, outcome label and produced count stored verbatim as reported), `production_order_view` — `produced_total_reported` is a sum of reported counts derived at read; no production runs and no MRP computation occurs |
| Procurement & sourcing platforms | built | `create_requisition` (`req-`, bound to core organization/project records; `decided_here: False`), `record_sourcing_event` (`sev-`, append-only reported labels with optional opaque `supplier_ref`), `record_award` (`awd-`, award as a reported outcome; amount integer cents as reported), `requisition_view` — `current_state_label` derived at read by the `_latest_label` seam, `awarded_total_cents_reported` a derived sum of reported amounts; the stored requisition carries no state key (pinned) |
| Contract execution management | built | `create_agreement` (`agr-`, `executed_here: False`), `record_agreement_state` (`ags-`, append-only reported state labels), `agreement_view` — `current_state_label` derived at read by the seam; surveillance/obligation tracking is these records; no contract is executed here and the stored agreement carries no state key (pinned) |
| EV charging network management | built (station/session records built; the session-control component ships in reference form in-record — see note 1) | `register_charging_station` (`evs-`, optional core asset binding; `controlled_here: False`), `record_charging_session` (`evse-`, energy integer watt-hours exactly as reported; meters nothing), `record_session_control_request` (`evc-`, `reference_stub: True`, `controlled_here: False`), `charging_station_view` — session count and `energy_wh_total_reported` derived at read as a sum of reports; the stored station carries no total (pinned) |
| Real-estate/facilities portfolio platform | built | `register_property` (`prop-`, bound to a core organization), `create_lease` (`lease-`, opaque `tenant_ref`, optional core project binding), `portfolio_view` — property / lease / leased-property counts derived at read over the surface's own records for the organization; no property is managed and no lease administered beyond its record |
| Kiosk & locker access management | built | `register_access_device` (`dev-`, optional core asset binding; `unlocked_here: False`, `device_controlled_here: False`), `record_access_grant` (`acg-`, opaque `grantee_ref`; `granted_in_record_only: True`, `unlocked_here: False` — the grant exists in this record only and unlocks nothing), `record_access_event` (`ace-`, reported labels stored verbatim), `access_device_view` — grant/event counts derived at read. The records layer is the whole claim: unattended-device administration and physical access control are not built (see note 2) |
| AI assistants & agents | **reference (re-judged from build-extension — see note 3)** | `register_assistant` (`asst-`, a declaration; `reference_stub: True`, `inference_here: False`), `record_assistant_request` (`asrq-`, holds an opaque `request_ref` only — no parameter can accept prompt text and the shape has no field that could hold it, pinned by exact key walk and a TypeError test; `prompt_held: False`), `record_assistant_outcome` (`asoc-`, outcome label verbatim as reported, result held as opaque `result_ref` only). Registration maps to the admin-only core `workflow_write` action, assistants being automation-shaped declarations in this substrate |
| Supply-chain risk & payments orchestration | built | `record_shipment` (`shp-`, `paid_here: False`), `record_risk_report` (`rsk-`, the reporter's `risk_label` verbatim; `score_computed_here: False` and the record's exact key set is pinned — no field can hold a computed score and no numeric value exists in the record), `record_payment_instruction` (`pay-`, positive integer cents; `paid_here` / `settled_here` / `executed_here` False — an instruction record, never a payment), `shipment_view` — `latest_risk_label` derived by the seam, `payment_total_cents_reported` a derived sum; the stored shipment carries neither (pinned) |

## Adjudication notes

**1. Session control, inside the EV charging entry.** The
built part of the entry is the network's records surface —
stations, sessions, reported energy. Starting, stopping, or
throttling a live charging session is an operation against an
external network, the same execution-shaped bound the Data
Management units met inside their archive/production entry
(disposition execution). The component therefore ships in
exactly that adjudicated form: control *request* records,
every one labeled `reference_stub: True` with
`controlled_here: False`, nothing controlled. The entry as a
whole is **not** re-judged: its center of mass is the charging
network's records, which are built above. The parent may close
the entry `built` for the records surface with the control
component labeled reference in-record, as recorded here.

**2. Kiosk & locker boundary.** The forks' substance
(SignifiVISION's centralized monitoring and status for deployed
devices; IVM SmartHub's access-controlled distribution) runs
to device administration and physical access. What is built
here is the records layer those functions presuppose — device
records, grant records, reported access events — with the
boundary carried in the records themselves
(`granted_in_record_only`, `unlocked_here`,
`device_controlled_here`). No device is unlocked, opened,
monitored live, or administered; a grant recorded here
authorizes nothing at any physical device.

**3. AI assistants & agents — re-judgment grounds.** The
drafted disposition was build-extension. On a close reading
of the set's spec, the entry's substance is a running
assistant layer: Fulcrum's Archie and its AI models,
Rohirrim's retrieval-based AI platform, NavigatorCRE's
natural-language querying — inference surfaces all, over data
this substrate does not hold. A records substrate can register
declarations and record requests and reported outcomes, but
calling that "built" would claim the assistant layer in a way
the sibling batch units have consistently refused: the Data
Management untiered unit closed its AI/ML engines entry
`reference` on the identical shape (declarations plus run
records with opaque output references), and the Collaboration
units closed AI assistance as reference stubs. This unit
follows that precedent: the family ships as a labeled
reference implementation (`reference_stub: True` on every
record, results as opaque references only, no prompt or result
content representable), and the parent should close the entry
`reference`.

**4. Scores, stated once.** Two forks' substance involves
scoring-shaped outputs (Partos's supplier vetting; TeamViewer
DEX-style experience scores are another set's fork, not this
one). No score is computed anywhere in this surface: risk
arrives as a reporter's verbatim label on a record whose key
set is pinned to hold nothing numeric, and vetting outcomes
would arrive the same way, as sourcing event labels. This
mirrors the core's inspection doctrine — outcomes stored
verbatim, no score computed.

## Long-tail enumeration

Against the 9 set-specific items of this set's gap list in
`UNION-SPEC.md` (each maps to the entry of the same name in the
table above) and the standing category gaps the spec carries:

**Named as NOT covered by this unit** (so nothing is read as
silently absorbed):

- **Standing category gaps**, registered under the parent
  groups and not re-registered under this set's section, hence
  not this unit's entries: workflow automation execution
  engine (the core registry still never executes; nothing here
  changes that); real-time intelligence & analytics engine; AI
  models (the models themselves — this unit ships the
  assistant *records* reference form, not a model); low-code
  application builder & deployment engine; integration
  connector engines & catalog (Boltline's standing
  `integrations` claim remains Extended and unbuilt — no
  connector record here pretends to one); mobile applications
  & offline sync; network connectivity services & cloud
  platform operations; authorization service / identity
  provider (IA-2 stays with the embedding organization;
  the forks' documented CAC/PIV, MFA, SSO, and SCIM assertions
  remain the forks' claims, built by no one here); common
  security services enforcement plane; policy enforcement
  plane; governance/compliance console engine; scheduling &
  rostering; IoT / telematics data collection (CARTN's and
  SignifiVISION's telemetry substance stays unbuilt — custody
  and access *events* here are reported labels, not collected
  telemetry); multi-tenant hosting (the build remains a
  single-tenant reference implementation); encryption at rest
  and TLS in transit (deployment layer, per
  `../../PLATFORM-LAYER.md` decisions 2–3 — the SC language in
  the spec is the forks' documented language about
  themselves); identity proofing and credential issuance.
- **The section's platform-layer paragraph** in GAPS.md (tier
  stays null; documented control claims at the prose tier) —
  not among the 9 entries; it stands on the spec and on
  `../../PLATFORM-LAYER.md`, and no entry here absorbs it.
- **The founding group's and the L1 singleton's own sections**
  (Operations Management L2, Operations Management L1)
  registered this category's extended families under their own
  sections and closed them in their own batch units. Those
  entries belong to those units; the forms here mirror them
  where this set's spec supports them, and nothing here
  re-closes them.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
