# Final GAPS batch — Remainder Singleton 56, Customer Relations Management (CRM) L1

Unit: the 8 entries in GAPS.md under "Remainder Singleton 56 —
Customer Relations Management (CRM) L1 (1 fork)" (6
`build-extension`, 2 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 683–690). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **Four
entries required re-judgment** under qualification 1 (idx 684,
686, 689, 690: drafted `build-extension`, closing `reference`),
with grounds stated in their rows below. One further entry (idx
683) closes `built` in the records form its own text bounds, a
near-the-line call stated plainly below.

The forms are the CRM L2 batch unit's adjudicated forms
(`../crm-l2/BATCH.md`), mirrored at this tier. That is not a
shortcut: this singleton's core is byte-identical to Group 25's
(shipped hashes re-verified after the build; `store.py` still
`16bcc12f…`), so the same records form is the same build, and it
carries the same closure token here as at Moderate. What does
**not** carry down is the baseline claimed: everything below is
claimed against this tier's own Low / LI-SaaS baseline (audit
AU-2/AU-3, FedRAMP Low side only), per the precision notes in
`UNION-SPEC.md`.

All extension code is in one new module,
`src/crm/extensions.py` (`CrmExtensions`, wrapping the core
`CrmStore`); every existing core module is byte-identical to its
pre-batch state. Full suite: 108 tests before, **144 tests
after, OK** (36 new in `tests/test_gaps_batch.py`), including
the fresh mutation-verified negative control recorded in
`tests/README.md`.

Cross-cutting, per the group's doctrines:

- RBAC is enforced through the core `crm.access` matrix — the
  extension maps each operation onto an existing core action
  (the mapping is documented in the module docstring) and checks
  it before any state change or id allocation; denied attempts
  are recorded on the core audit log as `ext_<action>:denied`
  and every successful mutation as `ext_<action>`. If an audit
  write fails, the record insertion and its id roll back before
  the error propagates (pinned by test) — no extension record
  exists whose audit entry does not. The mapping inherits the
  core's own asymmetries rather than widening them: channel
  surfaces ride `config_write` / `config_read`, so they are
  admin-only exactly as core module writes are.
- Everything is records over the group's own substrate:
  accounts/contacts by opaque reference, cases, guides,
  interactions. Where an extension record binds a person it
  names a core contact by id or carries an opaque `*_ref`
  string; no record shape can hold a real name, email, phone
  number, social handle, message or post content, or any other
  identifier — the core's privacy discipline governs the
  extension surface unchanged, and it bites hardest exactly
  where this fork's real product lives (handles and message
  content), so content enters only as an opaque `content_ref`.
- Derived values are derived at read and never stored: the
  experience overview's channel/outcome counts, the listening
  summary's reported-mention totals, the extension summary.
  Stored records carry no derived key; tests pin that.
- No score exists anywhere on this surface, by the same design
  as the core: score-shaped parameter names and outcome labels
  are refused at the boundary, evaluation figures are stored
  verbatim as reported, and a recursive scan test pins that no
  stored record or derived view carries a score-shaped key.
- Nothing here executes against an external system. The engine
  families ship as labeled reference implementations: every
  record they create carries `reference_stub: True` (publication
  and advertising outcome receipts additionally carry
  `reference_transport: True`), and no post is published, no
  conversation is listened to, no campaign executes or is
  optimized, no flow executes, no message is sent, and no model
  is run.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `crm/extensions.py`) |
|---|---|---|
| Unified customer experience management (CXM) platform: the unified platform itself, over the records substrate | built (build-extension, as drafted — in the records form its own text bounds; near-the-line, stated below) | Channel-surface definition records: `register_channel_surface` (`surface-`, a channel label from the core channel vocabulary plus this fork's own channel words — social / web / messaging / advertising — and an opaque `surface_ref`; `operated_here: False`, `hosted_here: False`), and the unified view: `experience_overview` — deterministic counts derived at read over the substrate's own records (core interactions by channel via the seam `_channel_counts` and by verbatim outcome, core case/account totals, surface and extension totals), stored nowhere, with `platform_operated_here: False` stated on the view. The records surface is genuinely built; the operating platform itself is not (see the near-the-line note) |
| Social media management & publishing engine | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `register_content_item` (`post-`, a post named only by opaque `content_ref` — the signature has no parameter that could carry post content, pinned by a `TypeError` test; `content_held_here: False`, `published_here: False`), `define_publication_schedule` (`sched-`, existing item ids plus a verbatim cadence label held as data; `executed_here: False`), `record_publication_outcome` (`pubr-`, the channel's outcome label and its own reported reach figure stored as data; `reference_transport: True`, `published_here: False`) — `reference_stub: True` throughout; a test pins that defining a schedule changes no core record |
| Social listening & research analytics engine | reference (stub-engine, as drafted) | `define_listening_topic` (`ltopic-`, definition text held verbatim as data, exactly as the core holds configuration text; `listened_here: False`), `record_listening_report` (`lrep-`, the source system's insight stored verbatim with its own reported mention count as data; `collected_here: False`) — a test pins that recording one creates **no core finding**: the core finding registry remains the only path by which a finding comes to exist, and it is a human's record (the L2 detection-report adjudication). Research analytics "beyond counts" is not claimed: `listening_summary` is counts of recorded reports and the sum of the sources' own reported mention figures, derived at read — the honest ceiling of this substrate, stated on the view as `method: recorded_report_counts` |
| Advertising campaign management engine | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `define_ad_campaign` (`adcamp-`, channel labels plus a recorded planned `budget_cents` figure held as data — integer cents, floats and booleans rejected, no money moves: `spent_here: False`; may name a recorded segment; `executed_here: False`, `optimized_here: False`), `record_ad_outcome` (`adout-`, outcome label verbatim plus the advertising network's own reported impression/click counts as data; `reference_transport: True`) — `reference_stub: True` throughout |
| Care engagement depth: the engagement machinery of the fork's care product beyond the substrate's case and interaction records | built (build-extension, as drafted; the L2 casework form) | Agent-desktop compositions as records: `create_agent_desktop` (`desk-`, an opaque case-queue ref plus the core guide ids and self-service topic ids the desktop composes — referenced records must exist; `composed_here: False`, the live agent workspace is not built). Self-service topics as content records: `create_self_service_topic` (`topic-`, title/body data, optionally bound to a core guide; enable/disable via `set_self_service_topic_enabled`; `hosted_here: False` — no portal is hosted). Chat channels in the records form: `register_chat_session` (`chats-`, bound to an existing core case; `reference_stub: True`, `connected_here: False`) and `record_chat_outcome` (`chatr-`, the channel system's outcome stored verbatim; no transcript shape exists) — no channel connects |
| Engagement & messaging orchestration engine | reference (stub-engine, as drafted) | `define_orchestration_flow` (`oflow-`, `kind` is the constant `orchestration_flow`; steps are `{step, channel}` records held as data; `executed_here: False`, `state: recorded_definition_only`), `record_orchestration_outcome` (`oout-`, outcome label verbatim plus the messaging system's own reported count as data; `sent_here: False`) — `reference_stub: True` throughout; a test pins that defining a flow and recording its outcome changes no core record. Orchestration flows and marketing flows are separate record kinds whose ids never cross-resolve (pinned) |
| Marketing platform functions (the fork's marketing product as an engine; the claim-level campaigns absence below stands) | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `create_segment` (`seg-`, an audience recorded as opaque account references; `targeted_here: False`), `define_marketing_flow` (`mflow-`, `kind` is the constant `marketing_flow`; steps are `{step, channel}` records held as data; `executed_here: False`, `state: recorded_definition_only`), `record_flow_outcome` (`mout-`, outcome label verbatim plus the delivery system's own reported count as data; `sent_here: False`) — `reference_stub: True` throughout; a test pins that defining a flow and recording its outcome changes no core record and creates no segment, and that segments and flows are separate record kinds whose ids never cross-resolve. The entry's own parenthetical stands: these segment records retire no part of the claim-level campaigns/audience absence |
| AI-backed core platform: the fork's AI-backed core itself (its one claim, ai_scoring, is recorded at exact weight — an AI-backed platform is asserted, no scoring, model, or ML function is described; the family is Extended in this category and stays Extended, and the build implements no AI and computes no score anywhere) | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | The L2 unit's AI form: `register_ai_request` (`aireq-`, names the model by opaque `model_ref`, may bind an existing core case; `inference_here: False`) — the signature itself refuses result content: there is no parameter that could carry it (pinned by a `TypeError` test). `record_ai_report` (`air-`, outcome label stored verbatim, result named only by opaque `result_ref`, `result_held_here: False`; score-shaped labels refused). `record_ai_evaluation` (`aieval-`, a model's evaluation figure stored exactly as reported — integer or verbatim label; booleans and floats rejected; `computed_here: False`). The entry's own bound stands: no score is computed anywhere in this build, core or extension, and no model runs |

## Near-the-line call (idx 683, CXM platform)

The entry closes `built`, and the call is stated rather than
hidden. Its own text bounds the deliverable: "the unified
platform itself, **over the records substrate**". What is built
is exactly that records surface — channel-surface definitions
plus the derived cross-channel overview over the substrate's own
records — and it is genuinely built, derived, and tested. The
operating platform itself (hosting, running, presenting one live
surface) is not built and is not claimed: every surface record
carries `operated_here: False` / `hosted_here: False`, the
overview carries `platform_operated_here: False`, and
`PLATFORM-LAYER.md` decision 6 (hosting substrate and platform
umbrella) stands beside this closure, not absorbed by it. If the
parent prefers the `reference` token for the platform entry,
only the token changes; the code and its labels already state
the boundary.

## Re-judgment grounds (DECISION.md qualification 1)

**Idx 684, social media management & publishing
(build-extension → reference).** The entry names an *engine*
whose substance is authoring, scheduling, and publishing **to
external social networks**. Execution against those networks is
not a records function: nothing in this substrate can publish,
and a build that claimed to would be an engine in name only.
The category's privacy discipline closes the other door — a
management surface over post *content* would need to hold that
content, and no shape here can hold a post, a handle, or a
message. What honestly lands is the batch's standard form for
engines over external systems, the same form the L2 unit gave
its marketing entry: definitions held as data, items named by
opaque reference, outcomes as reported.

**Idx 686, advertising campaign management (build-extension →
reference).** Paid campaign planning, execution, and
optimization run against external advertising networks, over
live auction and delivery data this substrate does not hold.
Execution there is not a records function, and *optimization*
is a computation the build must not simulate — the honest
surface records the campaign definition (including its planned
budget as an exact recorded figure; no money moves) and the
network's reported outcomes, and says `optimized_here: False`
on the record.

**Idx 689, marketing platform functions (build-extension →
reference).** The entry names the fork's marketing product *as
an engine*. Within this category the identical records form —
segments as opaque reference lists, flow definitions held as
data, outcomes as reported — closed `reference` in the L2
unit's marketing-automation entry, on the ground that the
registry never executes a flow and no message is sent. This
singleton's substrate is byte-identical to L2's; the same form
cannot honestly carry `built` at L1 for the same substance. The
entry's own parenthetical points the same way: it keeps the
claim-level campaigns absence standing, marking the engine
reading — not a records reading — as the registered gap.

**Idx 690, AI-backed core platform (build-extension →
reference).** The strongest of the four, because the entry's own
text draws the bound: the family "is Extended in this category
and stays Extended", no scoring, model, or ML function is
described, and "the build implements no AI and computes no
score anywhere". The fork's one claim asserts an AI-backed
platform; an AI core cannot be built in a records substrate
without fabricating inference. The entry therefore closes in
the L2 unit's AI form — request records whose signature refuses
result content, reported outcomes holding opaque references,
evaluation figures stored verbatim as reported — every record
labeled `reference_stub: True`, `inference_here: False`.

## Long-tail enumeration

Against the gaps list of `UNION-SPEC.md`:

| Spec gap | Where it lands |
|---|---|
| Unified customer-experience management platform | The CXM entry above (records form; near-the-line note) |
| Social media management & publishing | The publishing entry (reference, re-judged) |
| Social listening / research analytics (Modern Research) | The listening entry (reference, as drafted) |
| Advertising campaign management (Modern Advertising) | The advertising entry (reference, re-judged) |
| Care engagement depth (Modern Care) | The care entry (built, L2 casework form) |
| Engagement & messaging orchestration (Modern Engagement) | The orchestration entry (reference, as drafted) |
| Marketing platform functions (Modern Marketing) | The marketing entry (reference, re-judged) |
| The AI-backed core (the claimed family, Extended) | The AI entry (reference, re-judged); no AI function is implemented and no score is computed anywhere, exactly as the entry's own text bounds |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **The carried CRM Extended set from the parent group** —
  customer-service casework depth, guidance delivery runtime,
  gap-identification & adoption-analytics engines, customization
  & module engines, knowledge base & self-service content,
  marketing-automation engines & email delivery, integration
  connector engines. As the GAPS.md section itself records, that
  set "remains registered once under Group 25 and is not
  re-registered here": those entries are Group 25's unit (closed
  there — see `../crm-l2/BATCH.md`), and nothing in this unit
  touches them. The knowledge base in particular is **not**
  built here; the L2 forms this unit mirrors are the ones this
  section's own entries name (casework shapes inside the care
  entry, flow shapes inside the orchestration and marketing
  entries, AI shapes inside the AI entry).
- **Execution itself**, in every family that names it: no post
  is published, no campaign runs or is optimized, no flow
  executes, no message is sent, no model runs. The batch closes
  the records layer in front of those engines; the engines
  remain other systems' work, and the records say so on their
  face.
- **The section's platform-layer lines** (multi-tenancy,
  encryption at rest, TLS when configured, demo identities as
  hooks / IA-2 with the embedding organization, the hosting /
  delivery platform) — they stand on `PLATFORM-LAYER.md` and no
  entry in this unit absorbs them.
- **The named absences** — opportunity / pipeline at 0 claims at
  every tier of this category, and campaigns / audience lists at
  0 claims at claim level. Untouched: not built, not gaps
  retired. The marketing entry's segment records are opaque
  reference lists inside this substrate and retire no part of
  the claim-level absence, which stands as the spec records it.
- **The fork's products as products**: the records here are this
  substrate's shapes for the fork's extended families, not
  builds of Sprinklr's Modern Marketing / Advertising /
  Research / Care / Engagement products. The claims those
  products make remain theirs.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
