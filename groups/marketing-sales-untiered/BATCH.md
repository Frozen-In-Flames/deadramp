# Final GAPS batch — Untiered Set 18, Marketing & Sales

Unit: the 8 OPEN entries in GAPS.md under "Untiered Set 18 —
Marketing & Sales (2 forks, tier null; NEW CATEGORY)" (5
`build-extension`, 3 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 912–919; the section's
ninth entry, idx 920 "Platform layer", was already closed
`re-scoped` under `../../PLATFORM-LAYER.md` and is not part of
this unit). Dispositions per `../../gaps-batch/DECISION.md`
(ratified 2026-11-07). **Three entries required re-judgment**
under qualification 1 — idx 915, 917, and 918 were drafted
`build-extension` and close `reference`, with grounds stated in
their rows below.

All extension code is in one new module,
`src/marketsales/extensions.py` (`MarketSalesExtensions`,
wrapping the core `MarketSalesStore`); every existing core
module is byte-identical to its pre-batch state (SHA-256
verified against the pre-work baseline; `store.py` still
`869c1f36…`, the shipped hash). Full suite: 70 tests before,
**111 tests after, OK** (41 new in `tests/test_gaps_batch.py`),
including the fresh mutation-verified negative control recorded
in `tests/README.md`.

Cross-cutting, per the set's doctrines:

- **Tier null binds the whole surface.** No extension record or
  derived view carries a tier, baseline, impact-level, or
  equivalence key; a recursive scan over every extension record
  kind and view pins it (the Data Management untiered model),
  alongside the core's forbidden key parts (no score, grade,
  rank, rate, email, body, password, or secret key anywhere).
- **RBAC rides the core matrix.** The core action set is fixed,
  so each extension operation maps onto an existing core action
  (the mapping is documented in the module docstring) and is
  checked before any state change or id allocation. Successful
  mutations land on the core audit log as `ext_<operation>`; if
  an audit write fails, the record insertion and its id roll
  back before the error propagates (pinned by test) — no
  extension record exists whose audit entry does not. Denied
  attempts are not recorded at this layer, per this group's
  convention (they are the HTTP layer's responsibility, exactly
  as the core store records them); the service layer is
  untouched and the extension surface is not exposed over HTTP,
  which is out of scope for the batch pattern.
- **Derived values are derived at read and never stored**: the
  market view's counts, the handling queue, and a contact's
  current preferences. Stored records carry no derived key.
- **No score exists anywhere on this surface**, by the set's
  own design: score-shaped parameter names and data keys are
  refused at the boundary, reported figures are stored verbatim,
  and the recursive scan pins the absence.
- **Nothing here executes against an external system.** The
  reference families ship as labeled reference implementations:
  every record they create carries `reference_stub: True`
  (feeds and transport additionally `reference_transport:
  True`), and no model is run, no feed is fetched, no text is
  drafted, no membership is computed, no workflow executes, and
  no email is sent.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `marketsales/extensions.py`) |
|---|---|---|
| AI models / agents (the build contains no inference) | reference (stub-engine, as drafted) | `register_ai_request` (`aireq-`, names the model by opaque `model_ref`, may bind an existing organization / opportunity / campaign; `inference_here: False`) — the signature refuses result content: there is no parameter that could carry it (pinned by `TypeError` tests). `record_ai_report` (`air-`, outcome label stored verbatim, result named only by opaque `result_ref`, `result_held_here: False`). `record_ai_evaluation` (`aieval-`, the model's evaluation figure stored exactly as reported — integer or verbatim label; booleans and floats rejected; `computed_here: False`). Agents: `register_agent_definition` (`agent-`, steps held as an ordered list of action labels, data only; `executed_here: False`, and the class exposes no execution entry point, pinned by test). `reference_stub: True` throughout |
| Live opportunity-discovery feeds & contract-search engines | reference (stub-engine, as drafted) | `register_discovery_feed` (`feed-`, source and query labels held as data; `fetched_here: False`, `searched_here: False`, `reference_stub: True`, `reference_transport: True`) and `set_discovery_feed_active` (a recorded flag, exactly as the core workflow registry's). `record_discovery_report` (`dscr-`, the feed's own reported counts for a period, stored as data) — a test pins that recording a report registers **no core opportunity**: discovery enters the core only through a human's own registration, as the core has always held |
| Market intelligence & competitor / forecast analytics | built (build-extension, as drafted — near-the-line call, stated below) | Intelligence reports: `record_intelligence_report` (`intel-`, an analyst's recorded observation about a market subject, optionally a competitor label, with the source named by `source_ref` — the analyst's work product recorded as data, the same records shape as the core's evaluation records). Forecasts: `record_forecast` (`fcst-`, a source's own expected count stored verbatim with its horizon and basis labels; `computed_here: False` — a forecast record is a citation, not a computation). The derived side: `market_view` — deterministic counts over the substrate's own records (opportunities by agency label, evaluations by decision, pipeline entries by stage, recorded intelligence/forecast counts), derived at read, org-filterable, carrying `method: deterministic_counts_over_recorded_records` and `counts_only: True` on its face. No win rate, share, or projection is computed anywhere — the core's counts-only reporting discipline is this family's honest ceiling, stated rather than smoothed over |
| Proposal generation engine | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `request_proposal_generation` (`genreq-`, bound to an existing opportunity, item and kind labels; `drafted_here: False`) — the signature has no parameter that could carry drafted text (pinned by `TypeError` tests). `record_generation_report` (`genrep-`, outcome label verbatim; a reported result is named by the id of an existing core content-version record for the same opportunity — existence enforced, the core record pinned unchanged — and is not held here, `result_held_here: False`). `reference_stub: True` throughout |
| Workflow execution engine (the build's workflow registry records only and never executes) | reference (stub-engine, as drafted) | `request_workflow_execution` (`wexec-`, bound to an existing core workflow, parameters held as validated scalar data — floats and score-shaped keys rejected; `executed_here: False`, `state: recorded_request_only`) and `record_workflow_execution_report` (`wexecr-`, the external executor's outcome label verbatim) — a test pins that a request plus a report leaves the core workflow record deep-equal: the registry's founding discipline (records only, never executes) is untouched |
| Segmentation engine | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `request_segmentation` (`segreq-`, bound to an existing core segment, criteria held as validated definition data; `computed_here: False`, `state: recorded_request_only`) and `record_segmentation_report` (`segrep-`, the engine's reported member count stored as data) — a test pins that a request plus a report leaves the core segment record deep-equal, its own recorded member count standing as the core recorded it. `reference_stub: True` throughout |
| Email sending transport & deliverability | **reference — RE-JUDGED from the drafted build-extension** (grounds below) | `request_send` (`send-`, bound to an existing core campaign; `sent_here: False`, `transmitted_here: False`, `reference_stub: True`, `reference_transport: True`, `state: recorded_request_only`) and `record_transport_receipt` (`rcpt-`, the transport's own reported delivered / bounced / deferred counts for a period, stored as data) — tests pin that a send request plus a receipt creates **no core delivery or engagement record** and moves the campaign's derived status not at all: delivery outcomes enter the core only as facts recorded after the fact, exactly as the founding build holds |
| Bounce/complaint handling automation, campaign template management, preference management (each named in a fork's certified-services record but absent from its description — gaps resting on the description rule, caveat recorded in the union spec) | built (build-extension, as drafted) | Handling automation in records form: `register_handling_rule` (`hrule-`, trigger and action from fixed vocabularies, held as data; `applied_here: False` — definitions never execute here) and `set_handling_rule_active`. The queue: `pending_handling` — every bounced delivery outcome and every active complaint suppression that no handling record covers, **derived at read** from core records through the `_derive_pending_handling` / `_handling_covered` seams (the unit's mutation-verified drill target). Handling decisions: `record_handling` (`hndl-`, trigger and action from fixed vocabularies, optionally bound to a campaign on the same list) — a decision record only: a test pins it creates, releases, and modifies **no core suppression**; the operator performs that through the core, and this record is its handling trail. Template management: `register_template` (`tmpl-`, metadata only — label, kind, version, recorded size in bytes — in exactly the core proposal-content records' form; versions unique per (organization, label); the signature refuses any body). Preference management: `record_preference` (`pref-`, kind from a fixed vocabulary — channel / frequency / topic — and the value as a verbatim label, keyed by the core's opaque contact reference, whose shape cannot be an email address) and `current_preferences` — the latest recorded value per kind, derived at read through `_latest_preference`; kinds never recorded are absent, never defaulted. The entry's own caveat stands as the union spec records it: all three functions rest on the description rule, named in a fork's certified-services record and absent from its description |

## Re-judgment grounds (DECISION.md qualification 1)

**Idx 915, proposal generation engine (drafted build-extension
→ reference).** Generation is drafting: the engine's substance
is producing proposal text. This substrate cannot hold text at
all — the core's proposal-content records are metadata only (an
item label, a kind, a version, a size), an invariant the
founding spec states as a core-boundary decision and the
founding tests pin by exact key set. A generation engine built
into this substrate would have to emit text it cannot hold —
fabricating the one artifact the build is designed never to
carry — or be a generator in name only. That is the CRM L2
module-engines pattern exactly (an execution surface over
records the founding contract holds as never-executed data).
The honest disposition is the reference form: generation
requests and reported outcomes, with a reported result named by
the core content-version record a human registered for it.

**Idx 917, segmentation engine (drafted build-extension →
reference).** The engine's substance is computing segment
membership. Membership computation needs a contact universe to
compute over, and this substrate deliberately has none: contact
lists and segments hold counts only, and individual contacts
exist solely as opaque references on suppression, delivery, and
engagement records — the founding privacy design, stated in the
union spec's core-boundary decision ("it computes no
membership... the segmentation engine is a gap"). Where a
sibling substrate held a directory to derive membership over,
segmentation closed built by derivation; here there is nothing
to derive over, and inventing members to derive from would
fabricate the contacts the build refuses to hold. The entry
closes in the reference form: computation requests with
criteria held as data, and the engine's reported counts.

**Idx 918, email sending transport & deliverability (drafted
build-extension → reference).** The entry names the transport
itself. Sending is execution against external networks —
mailbox providers, feedback loops, deliverability
infrastructure — none of which exists in any form in this
substrate, and the batch's standing rule closes
send/publish/dial/optimize shapes as labeled reference records.
The records side of delivery already exists in the core
(delivery-outcome records behind the suppression gate); what
this entry adds is the layer in front of it, in the same form
the CRM builds gave their connector and email-delivery
surfaces: send-request records and the transport's reported
receipts, `reference_transport: True`, pinned to create no core
delivery record. The Communication untiered unit closed its
channel entries built under those entries' own bounding text;
this entry's text carries no such bound — it names the
transport — so the reference token is the honest one.

## Near-the-line call, stated (idx 914)

Market intelligence was drafted `build-extension` and closes
`built`, and the boundary deserves stating plainly. What is
built is the records layer: intelligence observations and
forecast figures recorded as data (each naming its source), and
deterministic counts over the substrate's own records. What is
not built is any gathering, analysis, or projection over
external market data — no feed is read, no competitor is
researched, no forecast is computed; a forecast record cites
its source's figure and says `computed_here: False` on its
face. If a reader holds that market intelligence is the
gathering itself, the token would be `reference` and only the
token changes — the code is identical either way. The parent
unit's call, recorded here rather than hidden: the records and
derivations are real functions of this substrate (the derived
counts are the same form as the core's own summary), the
entry's drafted disposition was build-extension, and the gap
text does not bound the entry to the external engine the way
the transport entry does — so it closes built, with this note
as its boundary.

## Long-tail enumeration

Against the function ranking of `UNION-SPEC.md`:

| Spec family | Where it lands |
|---|---|
| `opportunity_discovery` | Core (opportunity records, function 2); the live feeds and search engines behind the claim are the idx 913 entry |
| `opportunity_evaluation` | Core (evaluation records, function 3) — no extension needed |
| `capture_pipeline` | Core (pipeline records, function 4) — no extension needed |
| `proposal_content` | Core (content version records, function 5); the generation engine is the idx 915 entry |
| `workflow_automation` | Core (workflow registry, function 6); the execution engine is the idx 916 entry |
| `ai_powered_support` | Extended entire at founding; the idx 912 entry |
| `audience_segmentation` | Core (segment records, function 8); the membership engine is the idx 917 entry |
| `campaign_authoring` | Core (campaign records, function 9) — no extension needed |
| `campaign_scheduling` | Core (campaign records carry the schedule, function 9) — no extension needed |
| `outbound_email_delivery` | Core (delivery-outcome records behind the suppression gate, function 11); the sending transport is the idx 918 entry |
| `suppression_management` | Core (suppression records + the gate, function 10); bounce/complaint handling automation is part of the idx 919 entry |
| `engagement_reporting` | Core (engagement records + derived count report, functions 12–13) — no extension needed |
| `contact_lists` | Core (list records, counts only, function 7); preference management over those lists is part of the idx 919 entry |
| Campaign template management | Named in Zeta's `certified_services` only; part of the idx 919 entry, in the core content records' metadata form |

**Named as NOT covered by this unit** (so the enumeration
closes only what it lists):

- **The section's platform-layer entry (idx 920)** — already
  closed `re-scoped` under `PLATFORM-LAYER.md` (hosting,
  multi-tenancy, and CLEATUS's GovCloud substrate are the
  embedding organization's platform, not a fork function); no
  entry in this unit absorbs it, and the set's one documented
  control item (CLEATUS's CUI sentence, no mechanism stated)
  remains the fork's claim, not this build's attainment —
  nothing here holds CUI.
- **The named absences stand untouched**: no CRM or
  customer-relationship records, no lead management, no
  advertising, no social media, no SMS, no search marketing, no
  landing pages, no A/B testing, no personalization, no
  analytics function beyond the counts the idx 914 entry states,
  no brand management, no events. Nothing in this unit creates
  one, and the market view is not a marketing-analytics engine —
  it is counts over this substrate's own records, labeled as
  such.
- **Execution itself, in every family that names it**: no model
  runs, no feed fetches, no draft is generated, no membership is
  computed, no workflow executes, no email is sent. The batch
  closes the records layer in front of those engines; the
  engines remain other systems' work, and the records say so on
  their face.
- **Either fork's product as a product**: the records here are
  this substrate's shapes for the two platforms' extended
  families, not builds of CLEATUS or of the Zeta Marketing
  Platform. The claims those products make remain theirs.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
