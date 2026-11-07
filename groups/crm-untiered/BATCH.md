# Final GAPS batch unit — Untiered Set 23: CRM (untiered)

Unit: the 4 open entries in GAPS.md under the section header
`## Untiered Set 23 — Customer Relations Management (CRM) (1 fork, tier null)`
(idx 943–946 in `../../gaps-batch/inventory.json`: 2 drafted
`build-extension`, 2 drafted `stub-engine`). The section's fifth
entry, idx 947 "Platform layer", was already closed `re-scoped`
under [`../../PLATFORM-LAYER.md`](../../PLATFORM-LAYER.md) and is
not part of this unit. Dispositions per
[`../../gaps-batch/DECISION.md`](../../gaps-batch/DECISION.md)
(ratified 2026-11-07). **Two entries required re-judgment**
under qualification 1: idx 943 and idx 944 were drafted
`build-extension` and close `reference`, with grounds stated
below. Net for this unit: **4 closed (0 built, 4 reference)**.

All extension code is in one new module,
`src/crm/extensions.py` (`CrmExtensions`, wrapping the core
`CrmStore`); every existing core module is byte-identical to its
pre-batch state (SHA-256 verified against the pre-work baseline;
`store.py` still `16bcc12f…`, the shipped hash). Full suite:
104 tests before, **133 tests after, OK** (29 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Tier discipline on the new surface: this set is untiered — the
sheet records `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, no baseline is asserted and no CMMC
equivalence is drawn — and the extension introduces none of it.
A recursive scan in the batch tests pins that no stored record
or derived view carries a tier-, baseline-, impact-level-,
equivalence-, or score-shaped key, or a personal-data key.

Cross-cutting, per the group's doctrines and the category's
adjudicated batch forms at the sibling tiers:

- RBAC is enforced through the core `crm.access` matrix — the
  extension maps each operation onto an existing core action
  (the mapping is documented in the module docstring) and checks
  it before any state change or id allocation; denied attempts
  are recorded on the core audit log as `ext_<action>:denied`
  and every successful mutation as `ext_<action>`. If an audit
  write fails, the record insertion and its id roll back before
  the error propagates (pinned by test) — no extension record
  exists whose audit entry does not. The mapping inherits the
  core's own asymmetries rather than widening them:
  configuration-bound surfaces (document templates and
  automation, connector definitions and syncs) ride
  `config_write` / `config_read`, so their writes are admin-only
  exactly as core module writes are; the external-engine
  request/report surfaces (proposal generation, forecasting)
  ride `case_write` / `case_read`, the genus both sibling tiers
  gave the category's AI surface.
- Everything is records over the group's own substrate:
  accounts and cases by core id, everything else by opaque
  `*_ref`. No record shape can hold a real name, email, phone
  number, or any other identifier — the core's privacy
  discipline governs the extension surface unchanged — and none
  can hold a document body, a generated text, or a forecast.
- Derived values are derived at read and never stored: the
  connector catalog rollups, the forecast summary counts, the
  extension summary. Stored records carry no derived key; tests
  pin that.
- No score exists anywhere on this surface, by the same design
  as the core: score-shaped parameter names and outcome labels
  are refused at the boundary, evaluation and forecast figures
  are stored verbatim as reported (integers or verbatim label
  strings; booleans and floats rejected), and a recursive scan
  test pins that no stored record or derived view carries a
  score-shaped key.
- Nothing here executes against an external system. All four
  families ship as labeled reference implementations: every
  record they create carries `reference_stub: True` (connector
  records additionally carry `reference_transport: True`), and
  no proposal is generated, no forecast is computed, no
  document is automated, and nothing is connected, transmitted,
  or synced.

## Per-entry dispositions

| Entry (GAPS.md text, verbatim) | Drafted | Disposition |
|---|---|---|
| AI proposal-generation engine (the AI function this fork's description actually names) | build-extension | reference (**re-judged**, grounds below) |
| Pipeline forecasting engine | build-extension | reference (**re-judged**, grounds below) |
| Document automation engine (an asserted function with no family in the taxonomy — recorded as untaxonomied, no family stretched to hold it) | stub-engine | reference (as drafted) |
| Integration connector engines | stub-engine | reference (as drafted) |

Per entry, what was built (module: `crm/extensions.py`):

- **AI proposal-generation engine** — the category's adjudicated
  AI form, proposal-specialized. `register_proposal_request`
  (`prop-`, names the model by opaque `model_ref`, states the
  caller's `purpose`, may bind an existing core account and/or
  case with the core's linkage discipline enforced) — the
  signature deliberately has **no prompt, draft, or content
  parameter** (pinned by `TypeError` tests): generated text
  enters this build never. `record_proposal_report` (`proprep-`,
  outcome label stored verbatim with score-shaped labels
  refused; the generated proposal is named only by an opaque
  `proposal_ref`, `proposal_held_here: False`,
  `generated_here: False`). `record_proposal_evaluation`
  (`propeval-`, a model's evaluation figure stored exactly as
  reported, `computed_here: False`). Pinned: the whole proposal
  surface leaves the core report deep-equal — it creates no core
  records.
- **Pipeline forecasting engine** — `register_forecast_request`
  (`fcreq-`, names the engine by opaque `engine_ref` and the
  pipeline by opaque `pipeline_ref`, may bind an existing core
  account; no horizon, figure, or projection parameter exists).
  `record_forecast_report` (`fcrep-`, outcome label verbatim;
  the forecast itself named only by an opaque `forecast_ref`,
  `forecast_held_here: False`). `record_forecast_figure`
  (`fcfig-`, a forecast figure stored **exactly as the external
  engine reported it** — integer or verbatim label string,
  booleans and floats rejected, `computed_here: False`).
  `forecast_summary` derives counts only (requests / reports /
  figures, by verbatim outcome and figure labels) at read, with
  `method: recorded_forecast_counts` stated on its face — no
  recorded figure is summed, averaged, or projected. Pinned:
  the surface creates **no pipeline or opportunity record of
  any kind** (the class has no such method and the extension
  summary shows only the forecast kinds) — the named absence
  stands untouched.
- **Document automation engine** — `register_document_template`
  (`dtmpl-`, a template definition held as data: required unique
  opaque `template_ref`, optional `definition_text` stored
  verbatim and never rendered, merged, or executed —
  `rendered_here: False`, `executed_here: False` — exactly as
  the core holds module `settings_text` and the High sibling
  holds design definitions). `request_document_automation`
  (`docreq-`, snapshots the template's label and `template_ref`;
  parameters held as validated scalar data with score-shaped
  keys, floats, and nested structures refused; may bind an
  existing core account and/or case under the core's linkage
  discipline; `generated_here: False`, `automated_here: False`,
  `state: recorded_request_only`).
  `record_document_report` (`docrep-`, the engine's outcome from
  the fixed reported vocabulary
  `reported_completed` / `reported_failed` / `reported_noop`;
  the produced document named only by an opaque `document_ref`,
  `document_held_here: False` — the signature refuses document
  content, pinned by `TypeError` test). Pinned: a request plus a
  report leaves the bound core case deep-equal.
- **Integration connector engines** — `register_connector`
  (`conn-`, a connector definition record: required unique
  opaque `connector_ref`, optional caller-chosen label;
  `connected_here: False` — registering the definition connects
  nothing). `record_connector_sync` (`csync-`, a connector's
  sync receipt bound to at most one existing core record —
  account/case/guide/finding/module, existence enforced, target
  never modified, pinned deep-equal; the connector's own
  reported count as data; `reference_stub: True`,
  `reference_transport: True`, `transmitted_here: False`,
  `synced_here: False`) — the founding tier's adjudicated form,
  unchanged. `connector_catalog` rolls the recorded receipts up
  per connector (receipt counts, sums of reported counts, counts
  by direction), derived at read via the single derivation
  point `_sync_rollup` — this unit's mutation-controlled
  derivation (see `tests/README.md`).

## Re-judgment grounds (DECISION.md qualification 1)

**AI proposal-generation engine (idx 943, drafted
build-extension, closing reference).** The entry names a
*generation* engine, and its own parenthetical is precise about
why it is registered: it is "the AI function this fork's
description actually names." What the description asserts is
AI-powered proposal generation — a model producing document
content. That substance is execution by a model over content
bodies, and this substrate holds no content bodies: the build's
privacy discipline is structural (accounts and contacts are
opaque references; no shape can hold the customer PII the
fork's own CUI sentence names, let alone a proposal draft), the
build contains no model (the `ai_scoring` claim stands at
bare-token weight — "AI", "AI-powered" — recorded in the union
spec at exactly that weight, with no scoring, named model, or
machine-learning function asserted), and the build computes no
score anywhere. A generation surface built into this substrate
would have to run a model and hold its output — breaking both
invariants — or be a generation engine in name only. The
category's adjudicated form for this substance, applied at both
sibling tiers (AI/ML models & scoring at Moderate; GenAI
application tooling at High, where the unit records "any model
execution, GenAI drafting, or content generation: requests and
reported outcomes only"), is the labeled reference form used
here: requests whose signatures refuse content, reported
outcomes naming the generated proposal only by opaque
reference, evaluation figures stored verbatim.

**Pipeline forecasting engine (idx 944, drafted
build-extension, closing reference).** The draft read this
entry as records/derivation-shaped, and derivations are this
substrate's honest ceiling — but a forecast cannot be one of
them, for two independent reasons. First, there is nothing
in-substrate to derive it **from**: opportunities & sales
pipeline is a *named absence* in this set (0 of 1 at pattern
weight; the "pipeline forecasting" substance is asserted but
tags nothing, and the catalogue's "Sales pipeline management"
was never matched). The core holds no opportunity or pipeline
records, and the sibling units' discipline is that named
absences stand untouched — the founding-tier unit records
"nothing in this unit creates one." Building a pipeline
registry to feed a derivation would manufacture the very
substrate the spec records as absent. Second, a forecast is a
computed projection — inference about future values — and this
build computes no figure beyond counts of its own records (the
core report's contract: "counts of records only"; the
no-score rule is test-enforced across the category). A forecast
figure computed here would be a computed figure of exactly the
class the category forbids, wearing a different name. What
honestly lands is the records layer in front of the engine:
requests naming the pipeline by opaque reference only, reported
outcomes, and forecast figures stored **verbatim as the
external engine reported them** (`computed_here: False`), with
the summary deriving counts of those records and nothing more.

The two stub-engine drafts (idx 945, 946) close `reference` as
drafted, in the forms the sibling units adjudicated for the
same substances.

## Long tail, enumerated against UNION-SPEC.md

- **Knowledge base & self-service content** and
  **marketing-automation engines & email delivery** appear in
  this set's union-spec gap list but are **not entries of this
  section**: the section's own preamble records that they are
  already registered under the founding group's section and gain
  no claimant here (both tag 0 of 1 in this set). They were
  closed under Group 25's unit; this unit does not re-register
  or re-open them.
- **Hosting / SaaS delivery platform** — platform layer; not an
  entry of this section; stands on `PLATFORM-LAYER.md`.
- The `ai_scoring` claim itself stays Extended at bare-token
  weight, as the union spec records it; nothing in this unit
  raises its weight, and the build still contains no model and
  computes no score.
- The fork's certified-services catalogue remains unmined: its
  "AI-powered proposal drafting using Google Vertex AI" phrase
  is catalogue text, never matched; the proposal entry closes
  on the description's own assertion, in the reference form
  above, and no claim was manufactured from the catalogue.

## Named as not covered

- **Any actual proposal generation, drafting, or model
  execution**: the proposal surface holds requests and reported
  outcomes; no generated content is accepted by any signature
  in this module, and no proposal text is ever held.
- **Any forecasting computation**: no projection, extrapolation,
  or figure is computed here; forecast figures exist only as
  the external engine's reported data, and the summary counts
  records without summing or projecting any figure.
- **Any document assembly, rendering, or automation**: template
  definitions are data, requests are records, outcomes are
  reports; the produced document is named by opaque reference
  and never held.
- **Any real integration**: no connector connects, transmits,
  or syncs; receipts are records of what connectors reported,
  and their targets are never modified.
- **The core's named absences** (opportunities & sales pipeline
  as a records function; campaigns & audience lists; customer
  service cases at claim level) are untouched: nothing in this
  module creates a pipeline, a campaign, or a claim.
- **The fork's product as a product**: the records here are
  this substrate's shapes for the fork's extended families, not
  a build of VirtualDojo AI CRM. The claims that product makes
  — including its assertion that it stores CUI and customer
  PII — remain its own; this build's shapes hold opaque
  references only and can hold none of it.
- **Real authentication / identity proofing** behind the demo
  actor hooks: the extension inherits the group's existing
  posture (hooks, not an IdP) and adds no identity function.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
