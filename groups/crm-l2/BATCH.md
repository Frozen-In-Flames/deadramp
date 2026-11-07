# Final GAPS batch — Group 25, Customer Relations Management (CRM) L2

Unit: the 8 entries in GAPS.md under "Group 25 — Customer
Relations Management (CRM) L2 (2 forks)" (3 `build-extension`,
5 `stub-engine` in `../../gaps-batch/inventory.json`, idx
268–275). Dispositions per `../../gaps-batch/DECISION.md`
(ratified 2026-11-07). **One entry required re-judgment** under
qualification 1: idx 275's sibling entry (idx 271, customization &
module engines) was drafted `build-extension` and closes
`reference`, with grounds stated in its row below.

All extension code is in one new module,
`src/crm/extensions.py` (`CrmExtensions`, wrapping the core
`CrmStore`); every existing core module is byte-identical to its
pre-batch state (SHA-256 verified against the pre-work baseline;
`store.py` still `16bcc12f…`, the shipped hash). Full suite:
96 tests before, **134 tests after, OK** (38 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines:

- RBAC is enforced through the core `crm.access` matrix — the
  extension maps each operation onto an existing core action (the
  core action set is fixed; the mapping is documented in the
  module docstring) and checks it before any state change or id
  allocation; denied attempts are recorded on the core audit log
  as `ext_<action>:denied` and every successful mutation as
  `ext_<action>`. If an audit write fails, the record insertion
  and its id roll back before the error propagates (pinned by
  test) — no extension record exists whose audit entry does not.
  The mapping inherits the core's own asymmetries rather than
  widening them: module-bound surfaces ride `config_write` /
  `config_read`, so execution requests and connector syncs are
  admin-only exactly as core module writes are.
- Everything is records over the group's own substrate:
  accounts/contacts by opaque reference, cases, guides, findings,
  modules. Where an extension record binds a person it names a
  core contact by id or carries an opaque `*_ref` string; no
  record shape can hold a real name, email, phone number, or any
  other identifier — the core's privacy discipline governs the
  extension surface unchanged.
- Derived values are derived at read and never stored: knowledge
  base current text and revision counts, engagement metrics,
  connector catalog rollups, the extension summary. Stored
  records carry no derived key; tests pin that.
- No score exists anywhere on this surface, by the same design
  as the core: score-shaped parameter names and outcome labels
  are refused at the boundary, evaluation figures are stored
  verbatim as reported, and a recursive scan test pins that no
  stored record or derived view carries a score-shaped key.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries `reference_stub: True`
  (connector sync receipts additionally carry
  `reference_transport: True`), and no guidance is rendered, no
  telemetry is collected, no gap is detected, no module or flow
  executes, no message is sent, no model is run, and nothing is
  synced.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `crm/extensions.py`) |
|---|---|---|
| Customer-service casework depth (knowledge-driven agent desktops, self-service portals, chat / chatbot channels) | built (build-extension, as drafted) | Knowledge-driven desktop half: the knowledge base surface below (articles + append-only revisions) is what a knowledge-driven desktop composes. Desktop compositions as records: `create_agent_desktop` (`desk-`, an opaque case-queue ref plus the kb-article/topic ids the desktop composes — referenced records must exist; `composed_here: False`, the live agent workspace is not built). Self-service portals as content records: `create_self_service_topic` (`topic-`, title/body data, optionally bound to a kb article; enable/disable via `set_self_service_topic_enabled`; `hosted_here: False` — no portal is hosted). Chat / chatbot channels in the records form: `register_chat_session` (`chats-`, bound to an existing core case; `reference_stub: True`, `connected_here: False`) and `record_chat_outcome` (`chatr-`, the channel system's outcome stored verbatim; no transcript shape exists) — no channel connects |
| Guidance delivery runtime (in-app overlay engine + codeless authoring tooling) | reference (stub-engine, as drafted) | `register_guidance_session` (`gses-`, bound to an existing core guide with its current version snapshotted as data; contact named by opaque ref or core contact id with the core's contact↔account linkage enforced when an account is named; `rendered_here: False`, `delivered_here: False`), `record_guidance_outcome` (`gsout-`, the host application's outcome label stored verbatim; `observed_here: False`; score-shaped labels refused) — sessions are reported records, the overlay runtime is not built. Codeless authoring tooling: `register_authoring_definition` (`authd-`, definition text held verbatim as data, exactly as the core holds module `settings_text`; `authored_here: False`) — `reference_stub: True` throughout |
| Gap-identification & adoption-analytics engines (telemetry collection, gap detection, engagement analytics beyond record counts) | reference (stub-engine, as drafted) | Telemetry collection: `record_telemetry_report` (`telr-`, a source system's own event count for a named period stored as data; `collected_here: False`; negative and float counts rejected). Gap detection: `record_detection_report` (`detr-`, finding-shaped reported data — title, verbatim detail, core severity vocabulary, optional existing account; `detected_here: False`) — a test pins that recording one creates **no core finding**: the core finding registry remains the only path by which a finding comes to exist, and it is a human's record. Adoption analytics "beyond record counts" is not claimed: `engagement_metrics` is deterministic counts over recorded records only (core interactions by channel/outcome, recorded guidance sessions/outcomes by verbatim label, core findings by severity/status), derived at read and stored nowhere — the honest ceiling of this substrate, stated on the report as `method: deterministic_counts_over_recorded_records` |
| Customization & module engines (add-on module execution, codeless configuration runtimes) | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `request_module_execution` (`mexec-`, bound to an existing core module, snapshotting its label and version, parameters held as validated scalar data; `executed_here: False`, `state: recorded_request_only`), `record_module_execution_report` (`mexecr-`, the external runtime's outcome from a fixed reported vocabulary; `executed_here: False`) — a test pins that a request plus a report leaves the core module record deep-equal. Codeless configuration runtimes: `register_runtime_parameter_set` (`rtps-`, a module's would-be runtime parameters held as data; `applied_here: False`; floats, nested structures, and score-shaped keys rejected). `reference_stub: True` throughout; both surfaces ride `config_write`/`config_read`, admin-only as in the core |
| Knowledge base & self-service content (0 claims here) | built (build-extension, as drafted) | `create_kb_article` (`kb-` + first `kbrev-` revision), `revise_kb_article` (appends a revision; earlier revisions never change and there is no update or delete API), `get_kb_article` / `list_kb_articles` (current title/body and revision count derived at read from the latest revision — the stored article record holds only tags and provenance, pinned by an exact key-set test), `list_kb_revisions` (the full append-only history), `search_kb_articles` (literal substring search over current text — registry mechanics, not a search engine). Self-service content is the topic surface in the casework row above |
| Marketing-automation engines & email delivery (0 claims here) | reference (stub-engine, as drafted) | `create_segment` (`seg-`, an audience recorded as opaque account references; `targeted_here: False`), `define_marketing_flow` (`mflow-`, `kind` is the constant `marketing_flow`; steps are `{step, channel}` records held as data; `executed_here: False`, `state: recorded_definition_only`), `record_flow_outcome` (`mout-`, outcome label verbatim plus the delivery system's own reported count as data; `sent_here: False`) — `reference_stub: True` throughout; a test pins that defining a flow and recording its outcome changes no core record and creates no segment, and that segments and flows are separate record kinds whose ids never cross-resolve. No message is sent and no flow executes |
| AI/ML models & scoring (0 claims here; no score is computed anywhere in the core, by design) | reference (stub-engine, as drafted) | `register_ai_request` (`aireq-`, names the model by opaque `model_ref`, may bind an existing core case; `inference_here: False`) — the signature itself refuses result content: there is no parameter that could carry it (pinned by a `TypeError` test). `record_ai_report` (`air-`, outcome label stored verbatim, result named only by opaque `result_ref`, `result_held_here: False`; score-shaped labels refused). `record_ai_evaluation` (`aieval-`, a model's evaluation figure stored exactly as reported — integer or verbatim label; booleans and floats rejected; `computed_here: False`). The entry's own bound stands: no score is computed anywhere in this build, core or extension |
| Integration connector engines (0 claims here; near-miss recorded) | reference (stub-engine, as drafted) | `record_connector_sync` (`csync-`, a connector's sync receipt bound to at most one existing core record — account/case/guide/finding/module, existence enforced, target never modified; the connector's own reported count as data; `reference_stub: True`, `reference_transport: True`, `transmitted_here: False`, `synced_here: False`), `connector_catalog` (per-connector rollups of recorded receipts — sync counts and sums of reported counts by direction — derived at read). The spec's recorded near-miss stands: WalkMe's overlay prose asserts no integration function, and this surface asserts none either — it is the records layer in front of connectors, not a connector |

## Re-judgment grounds (idx 271, DECISION.md qualification 1)

"Customization & module engines" was drafted `build-extension`
on pattern: module records exist in the core, so an extension
over them looked records-shaped. On a close reading of the
group's own spec it is not. The core's contract for modules is
explicit and load-bearing: "`settings_text` stored verbatim
(never executed)", restated in the README's honesty section ("no
customization/module execution engine (module settings are
stored verbatim, never run)") and in the union ranking, where
the family's Core disposition is the *registry* and the engines
are Extended. An add-on module **execution** engine or a
codeless configuration **runtime** built into this substrate
would have to execute that stored text — breaking the founding
invariant the group's tests and docs pin — or else be a runtime
in name only. Per qualification 1 the disposition is corrected
to the honest one: the entry closes as a labeled reference
implementation (execution-request records, reported outcomes,
parameter sets held as data), the same form the batch gives
every engine-over-external-systems family, with the invariant
stated on every record (`executed_here: False`,
`applied_here: False`, `reference_stub: True`).

## Long-tail enumeration

Against the function ranking of `UNION-SPEC.md`:

| Spec family | Where it lands |
|---|---|
| Modules, customization & codeless configuration | Core (module/configuration registry, function 6); the engines are the re-judged module-engines entry |
| Hosting / SaaS delivery platform | Platform layer — not among the 8 entries; stands on `PLATFORM-LAYER.md` |
| Customer service cases & service platform | Core (function 2); casework depth is the casework entry |
| User guidance & digital adoption | Core (guidance content registry, function 4); the delivery runtime is the guidance entry |
| Gap & problem-area identification | Core (finding records, function 5); the engines are the gap-identification entry |
| Engagement & productivity tracking | Core (interaction records, function 3); analytics beyond counts is the gap-identification entry, which closes at counts and says so |
| Account & contact records | Core (function 1, substrate) — no extension needed |
| Interaction & activity records | Core (function 3) — no extension needed |
| Reporting & dashboards | Core (function 7, registry reporting); dashboard/analytics engines are the gap-identification entry |
| Access control & RBAC | Core (function 10, baseline substrate); the extension rides the same matrix |
| Audit logging | Core (function 10, baseline substrate); every extension mutation and denial lands on the same append-only log as `ext_*` / `ext_*:denied` entries |
| Search | Core (function 8); kb search is registry mechanics inside the knowledge entry |
| Opportunities & sales pipeline | **Named absence — untouched.** 0 of 2 claims; not built, not a gap, and nothing in this unit creates one |
| Campaigns & audience lists | **Named absence at claim level — untouched.** The marketing entry closes the registered *engines* gap (automation/email delivery) in reference form; its segment records are opaque reference lists inside this substrate and retire no part of the claim-level absence, which stands as the spec records it |
| Knowledge base & self-service content | The knowledge base entry |
| Marketing automation & email delivery | The marketing entry |
| AI/ML models & scoring | The AI entry |
| Integrations & interoperability | The connector entry; the recorded near-miss stands |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Execution itself**, in every family that names it: no module
  runs, no configuration runtime applies parameters, no flow
  executes, no overlay renders. The batch closes the records
  layer in front of those engines; the engines remain other
  systems' work, and the records say so on their face.
- **The section's platform-layer paragraph** (multi-tenancy,
  encryption at rest, TLS when configured, demo identities as
  hooks / IA-2 with the embedding organization, the hosting /
  delivery platform) — not among the 8 entries; it stands on
  `PLATFORM-LAYER.md`, and no entry in this unit absorbs it.
- **Either sibling's product as a product**: the records here are
  this substrate's shapes for the two platforms' extended
  families, not builds of Oracle Service Cloud or of WalkMe DAP.
  The claims those products make remain theirs.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
