# Final GAPS batch — Group 27, Customer Service L2

Unit: the 13 entries in GAPS.md under "Group 27 — Customer
Service L2 (2 forks)" (7 `build-extension`, 6 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 276–288). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
required re-judgment**: each fit its drafted disposition on a
close reading of this group's spec, in the forms stated below.

All extension code is in one new module,
`src/custsvc/extensions.py` (`CustsvcExtensions`, wrapping the
core `CustsvcStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified against the pre-work
baseline; `store.py` still `05c749f3…`, the shipped hash — this
group's core is Group 26's code reused byte-identical, and the
batch adds a module beside it, never a change inside it). Full
suite: 69 tests before, **127 tests after, OK** (58 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines:

- RBAC is enforced through the core `custsvc.access` matrix — the
  extension maps each operation onto an existing core action (the
  core action set is fixed; the mapping is documented in the
  module docstring) and checks it before any state change or id
  allocation; denied attempts are recorded on the core audit log
  as `ext_<action>:denied` and every successful mutation as
  `ext_<action>`. If an audit write fails, the record insertion
  and its id roll back before the error propagates (pinned by
  test) — no extension record exists whose audit entry does not.
- The pinned requester discipline extends to every person-shaped
  reference on this surface: survey respondents, relocation
  employees, and signers must be requester refs already registered
  in the core, so the core's exact record shape — which cannot
  hold a phone number, email address, or real identifier —
  governs them too. All other parties and systems are opaque
  `*_ref` strings.
- Derived values are derived at read and never stored: SLA breach
  state under a recorded policy, GRC posture counts, survey
  tallies, notification rollups, analytics reports. Stored records
  carry no derived key; tests pin that.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries `reference_stub: True`
  (notification delivery receipts carry `reference_transport:
  True`), and no site is hosted, no relocation is processed, no
  signature is made, nothing is detected, no channel connects,
  and no assistant infers.
- The founding doctrine is not repealed: the core automation rule
  registry never executes, and the batch's automation surface
  evaluates no condition and performs no action (pinned by
  behavior: an execution request changes no core state).

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `custsvc/extensions.py`) |
|---|---|---|
| Commerce platform hosting & point-of-sale systems (one sibling's entire domain: POS hosting for grocery / gas / loyalty / food-ordering, commerce applications, commerce API platform) | reference (stub-engine) | `register_commerce_site` (`pos-`, opaque `site_ref`, domain enum over the sibling's own named domains; `hosted_here: False`), `record_commerce_report` (`posr-`, platform state stored verbatim as reported) — every record carries `reference_stub: True`; no site is hosted, no transaction is processed, and no record shape can hold a payment instrument or an amount in motion |
| PCS relocation platform (the other sibling's domain: relocation financial workflows from obligation to financial-system interfaces, travel-voucher processing, supplier integration) | reference (stub-engine) | `create_relocation_case` (`pcs-`, employee is a registered core requester by opaque ref; `processed_here: False`), `record_relocation_step` (`pcss-`, the workflow's steps as recorded states; `amount_cents` is integer-cents **data** about the recorded step — booleans/floats rejected at the boundary, no id consumed — and no record shape can hold a payee or account field) — `reference_stub: True` throughout; no obligation is created, no voucher is paid, no financial system is interfaced |
| Automation execution engines (the rule registry is Core; one sibling's automation prose is a recorded near-miss, 0 tagged claims) | built | `request_rule_execution` (`exec-`, a request record against an existing core rule, snapshotting the rule's name and enabled state; `executed_here: False`, `state: recorded_request_only`), `record_execution_report` (`execr-`, an executor's outcome stored verbatim; also `executed_here: False`), `execution_summary` (counts derived at read). The registry-never-executes doctrine is untouched: a test pins that a request plus a report leaves the core rule and case state exactly as it was. The sibling's automation prose remains the recorded near-miss it was at spec time — this surface is the request log an execution engine would front, and the engine is not built |
| E-signature execution & PIV-based signer identity assurance (prose present in one sibling; 0 tagged claims) | reference (stub-engine) | `record_signature_request` (`sig-`, against an existing core case; signer is a registered core requester by opaque ref; `signed_here: False`; the exact record shape is pinned by test — no field can hold signature bytes, a certificate, or a credential), `record_signature_report` (`sigr-`, outcome and the signing system's reported assurance label stored verbatim; `signature_held: False`) — `reference_stub: True` throughout; identity proofing stays with the embedding organization (`PLATFORM-LAYER.md` decision 1) |
| Event detection, diagnosis & orchestration engines (0 claims here; carried from the Group 26 union) | reference (stub-engine) | `register_detection_source` (`det-`, opaque `source_ref`; `detects_here: False`), `record_orchestration_run` (`orc-`, run outcome stored verbatim; may reference an existing core alert, and only an existing one) — `reference_stub: True` throughout; detection happens in source systems elsewhere, and a test pins that an orchestration record creates no alert: the core's alert ingest remains the only path by which an alert record comes to exist |
| GRC platform (0 claims here; carried from the Group 26 union) | built | `register_framework` (`fw-`, framework records as label sets — a framework record asserts no framework support, see the enumeration note on family 10), `register_control` (`ctl-`, the caller's own control label held as data), `map_case_to_control` (`cmap-`, both ends must exist), `framework_posture` — counts over controls, mappings, and mapped core cases (by status, plus the core's own derived breach flag) derived at read; posture is counts only, no score is computed, and no framework is assessed |
| Real-time channels: live chat, voice / telephony (0 claims; named) | reference (stub-engine) | `register_channel` (`chn-`, kind enum live_chat/voice/video; `media_here: False`), `record_channel_session` (`chs-`, a reported session against an existing core case; `connected_here: False`) — `reference_stub: True` throughout; no media exists in this build and nothing connects or streams |
| AI assistance / deflection (0 claims; named) | reference (stub-engine) | `register_assistant` (`ai-`, `inference_here: False`, `method: recorded_declaration_only`), `record_deflection_report` (`air-`, the assistant's reported outcome for a core case stored verbatim; `decided_here: False`) — `reference_stub: True` throughout; a test pins the reported case is untouched — the build deflects nothing, answers nothing, and decides nothing |
| Knowledge base articles (0 of 2; named absence at both tiers) | built | `create_article` (`kb-` + first `kbrev-` revision), `revise_article` (appends a revision; earlier revisions never change and there is no update or delete API), `get_article` / `list_articles` (current title/body and revision count derived at read from the latest revision — the stored article record holds only tags and provenance, pinned by an exact key-set test), `list_article_revisions` (the full append-only history), `search_articles` (substring search over current text, the registry-metadata pattern — not a search engine) |
| Satisfaction / CSAT surveys (0 of 2; named absence; near-miss recorded) | built | `create_survey` (`svy-`, instrument record with its scale as recorded terms, optionally bound to a core case), `record_survey_response` (`svr-`, respondent is a registered core requester by opaque ref; rating validated against the instrument's recorded scale and stored **verbatim**, comment verbatim), `survey_tally` — response count, the full-scale distribution, and the mean as an **exact rational** (numerator/denominator over the recorded ratings, `method: exact_rational_mean_of_recorded_ratings`) derived at read; the stored survey record's exact key set is pinned — no tally, score, or aggregate key exists on any stored record |
| SLA policy engine (due / breach derivation only in Core; no sibling at either tier claims SLA terms) | built | `create_sla_policy` (`sla-`, per-priority resolution targets in minutes held as data; unknown priorities, non-positive, boolean, and float terms rejected), `sla_case_view` and `sla_breach_report` — breach state derived at read from the core case record (created_utc, priority, status) against the recorded terms at the single seam `_is_breached_under_policy` (the batch's fresh negative control); terminal cases are never breached under a policy, uncovered priorities are never breached under it, and a test pins that policy views leave the core case record untouched. This derivation coexists with the core's own `due_at` derivation; neither replaces the other, and no sibling's SLA terms are invented — the terms are the operator's recorded data |
| Notification delivery & status-page hosting (status records / view are Core; delivery is not) | built | `record_notification` (`ntf-`, against an existing core case, recipient a registered core requester by opaque ref, channel a caller label held as data; `reference_transport: True`, `delivered_here: False`), `record_delivery_report` (`ntr-`, a delivery system's reported outcome stored verbatim, same transport labels), `notification_summary` (counts derived at read); `record_status_page` (`stp-`, a configuration record naming the core's derived public status view as its source; `reference_stub: True`, `hosted_here: False`), `status_page_view` — the core `public_status` derivation itself, labeled `served_from: core_public_status_derivation`. Delivery and hosting stay outside the build; what lands is the records layer in front of them |
| Reporting / analytics engines beyond registry reporting (reporting is this group's sole claim, 1 of 2) | built | `analytics_report` — deterministic derivations over core case and alert records at read: cases by channel, by assignee (with per-assignee breach counts), breached by priority, distinct requesters with cases, alerts by severity, and alert-to-case linkage as exact counts (`linked` / `unlinked` / `total` — no float rate). `method: deterministic_counts_over_core_records`, `derived: True`, stored nowhere; a test pins the report moves as records are added, i.e. it is a derivation, not a snapshot. This is the one family this group claims (VEN's "runs real-time reports"), extended at the records level only |

## Long-tail enumeration

Against the 16 families of `UNION-SPEC.md`'s function ranking:

| Spec family | Where it lands |
|---|---|
| Reporting & dashboards | Core (registry reporting, function 9 — this group's one claimed function) + the analytics entry |
| Case / ticket registry, triage & lifecycle | Core (function 1) — no extension needed, none built |
| Automated event detection, diagnosis & response | Core (alert records, function 5); the engines are the detection stub entry |
| Event orchestration, aggregation & alert prioritization | Core (priority + alert records); orchestration is the detection stub entry |
| Automated actions & predefined workflows | Core (rule registry, function 8); execution requests/reports are the automation entry — execution itself is not built |
| On-call scheduling & coverage | Core (function 6) — no extension needed |
| Responder assignment & mobilization | Core (function 3) — no extension needed |
| Status updates & status pages | Core (derived status view, function 7); delivery and page hosting are the notification entry |
| Governance, risk & compliance platform | The GRC entry |
| Compliance framework support (NIST / RMF / ATO) | **Not claimed, and still not claimed.** No framework vocabulary appears in either sibling's description, and the GRC entry's framework records are operator label sets — registering a record named for a framework asserts no support for it. This family gains no claimant from this unit |
| Knowledge base / help articles | The knowledge base entry |
| Satisfaction / CSAT surveys | The surveys entry |
| Real-time chat / voice channels | The channels stub entry |
| AI assistance / deflection / learned models | The AI stub entry |
| Access control | Core (function 10, baseline substrate) — no extension needed |
| Audit logging | Core (function 10, baseline substrate); every extension mutation and denial lands on the same append-only log as `ext_*` / `ext_*:denied` entries |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Execution itself**, in every family that names it: no rule is
  executed, no workflow runs, no orchestration acts. The batch
  closes the records layer in front of those engines; the engines
  remain other systems' work, and the records say so on their
  face (`executed_here: False`).
- **The section's platform-layer items** (encryption at rest
  SC-28 and the Moderate baseline's deployment-layer controls
  named in the spec's control section) — not among the 13
  entries; they stand on `PLATFORM-LAYER.md`, and no entry in
  this unit absorbs them.
- **Either sibling's domain platform as a product**: the commerce
  and relocation entries are reference records of those domains'
  shapes inside this substrate, not builds of NCR's point-of-sale
  platform or of VEN's relocation system. The claims those
  products make remain theirs.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
