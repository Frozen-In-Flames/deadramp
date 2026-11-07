# Final GAPS batch unit — Singleton 40: CRM L3-adjacent

This group (Customer Relations Management at FedRAMP High,
1 fork) carries 5 open Extended entries in
[GAPS.md](../../GAPS.md) under the section header
`## Singleton 40 — CRM L3-adjacent (1 fork)` (idx 399-403 in
`../../gaps-batch/inventory.json`: 3 drafted `build-extension`,
2 drafted `stub-engine`). Per
[`../../gaps-batch/DECISION.md`](../../gaps-batch/DECISION.md)
this unit closes those entries in one new module
(`src/crm/extensions.py`) with its own test file
(`tests/test_gaps_batch.py`), all existing modules
byte-identical. The WP/Pega baseline's description tags nothing
at High: every entry in this section names an Extended
function, and per the Merge Rule the Moderate substrate the fork
inherits arrives whole and is carried-not-claimed.

## Dispositions

All five entries close `reference`. Three are re-judgments
under DECISION.md qualification 1 (the drafted split is a draft,
not a mandate; grounds below). The pattern is this category's
own adjudicated standard, applied at both sibling tiers:
engines whose substance is execution, generation, inference, or
platform operation close as labeled reference implementations
carrying the records layer in front of the engine, never as
engines in name only. This build's core is Group 25's substrate
carried up whole through Moderate to High, so a form that was
reference at Moderate cannot honestly carry `built` at High for
the same substance.

| GAPS entry (verbatim) | Drafted | Disposition |
|---|---|---|
| No-code / low-code application development engine & model-based design tooling (the description's central assertion; a near-miss to the configuration family, not a tagged claim) | build-extension | reference (re-judged) |
| Case management & BPM / workflow execution engines (case automation, process orchestration, workflow execution; the substrate's case records are Core, the automation acting on cases is not) | stub-engine | reference (as drafted) |
| Decisioning engine (named in the source record, not in the description; record-named, not description-claimed) | build-extension | reference (re-judged) |
| GenAI application tooling and AI / ML models generally (record-named as above) | stub-engine | reference (as drafted) |
| Managed cloud operations & application scaling platform (the deployment layer itself, operated) | build-extension | reference (re-judged) |

Net for this unit: **5 closed (0 built, 5 reference)**. No entry
is re-scoped by this unit, and no GAPS.md line is edited by the
build; the parent closes the tokens.

## What was built

One new module, `src/crm/extensions.py` (class
`CrmExtensions`, a wrapper over the core `CrmStore`), following
the category's records doctrines and this tier's apparatus:

- **RBAC through the core matrix.** Every extension operation
  maps onto an existing core action and is checked via
  `crm.access.require` before any state change or id
  allocation; denied attempts are audited on the core log with
  the extension action name suffixed `:denied`. Module-bound
  surfaces (design definitions, generation, environments,
  platform reports) ride `config_write` / `config_read`, so
  their writes are admin-only exactly as core module writes
  are; case-bound surfaces (workflows, decisioning, AI) ride
  `case_write` / `case_read`; the extension summary rides
  `report_read`. The separated `auditor` role holds
  `audit_read` and nothing else, so the High apparatus binds
  the extension: the auditor is denied every extension read and
  write, and its denials land on the hash-chained log it exists
  to review (pinned by test).
- **The hash-chained audit binds the extension.** Every
  extension mutation is recorded on the core store's
  hash-chained log with an `ext_`-prefixed action name; the
  chain verifies after extension operations (pinned), and if
  the audit write raises, the record insertion and its id roll
  back before the error propagates, mirroring the core's
  fail-closed AU-5 posture (pinned by test with a swapped-in
  failing audit backend).
- **Opaque refs only.** Records bind core accounts/cases/
  modules by id or name external systems by opaque `*_ref`
  strings; no record shape can hold a real name, email, phone
  number, or any other identifier (recursive key scan pinned).
- **No computed scores, anywhere.** Score-shaped keys are
  refused as generation parameters and score-shaped labels are
  refused on every reported-outcome surface; figures are
  stored verbatim as reported (integers or verbatim label
  strings; booleans and floats rejected). This bites hardest on
  the decisioning entry: a decision computed from a propensity
  is a score by another name, and none is computed or stored.
- **Derived at read, never stored.** Design current text and
  revision counts, the operations rollup, and the extension
  summary are computed at read; stored records carry no derived
  key (exact key sets pinned).
- **Labeled on their face.** Every record the module creates
  carries `reference_stub: True` and the corresponding
  `*_here: False` flags: nothing is generated, executed,
  decided, inferred, hosted, operated, or scaled by this build.

Per entry:

- **No-code / low-code application development engine &
  model-based design tooling** — `register_design_definition`
  (`design-`) holds the design model text verbatim as data,
  exactly as the core holds a module's `settings_text`, with
  append-only revisions (`drev-`; current text derived at
  read); the definition may bind an existing core module, which
  is never touched (deep-equal pin).
  `request_application_generation` (`genreq-`) snapshots the
  design's current revision number and holds validated scalar
  parameters as data (score-shaped keys refused).
  `record_generation_report` (`genrep-`) records the external
  platform's outcome from a fixed vocabulary; the generated
  application is named only by an opaque `artifact_ref`, never
  held (`generated_here: False`, `artifact_held_here: False`).
- **Case management & BPM / workflow execution engines** —
  `define_workflow` (`wflow-`) holds a `bpm_workflow`
  definition as data: `{step, action}` step records, optional
  binding to an existing core case. `request_workflow_run`
  (`wfrun-`) binds the workflow and at most one case (the
  workflow's own, or an explicitly named existing case; a
  conflicting pair is refused). `record_workflow_run_report`
  (`wfout-`) records the external engine's reported outcome and
  its own reported step count as data. Pinned: defining a
  workflow, requesting a run, and recording a report leave the
  bound core case deep-equal — the automation acting on cases
  is the engine's, not this build's (`executed_here: False`).
- **Decisioning engine** — `register_decision_request`
  (`dreq-`) names the engine by opaque `engine_ref` and may
  bind an existing core case and/or account (a case linked
  alongside an account it does not belong to is refused,
  mirroring the core's linkage discipline). The signature
  deliberately has no decision, result, or score parameter
  (pinned by TypeError tests).
  `record_decision_report` (`drep-`) stores the engine's
  outcome label verbatim; the decision itself is named only by
  an opaque `decision_ref`, never held
  (`decision_held_here: False`).
  `record_decision_evaluation` (`deval-`) stores evaluation
  figures exactly as reported (`computed_here: False`).
- **GenAI application tooling and AI / ML models generally** —
  the category's adjudicated AI form: `register_ai_request`
  (`aireq-`; `model_ref` may name a GenAI tool, and the
  signature refuses generated content exactly as it refuses
  result content), `record_ai_report` (`air-`; result named
  only by opaque `result_ref`, `result_held_here: False`), and
  `record_ai_evaluation` (`aieval-`; figures verbatim,
  `computed_here: False`). Pinned: the whole AI surface creates
  no core records.
- **Managed cloud operations & application scaling platform** —
  `register_environment` (`env-`) records an operated
  environment by required, unique, opaque `environment_ref`
  (`hosted_here: False`, `operated_here: False`).
  `record_scaling_report` (`scale-`) stores the platform
  operator's scaling outcome label verbatim and its own
  reported instance count as data (`scaled_here: False`).
  `record_operations_report` (`opsrep-`) stores an operations
  report as reported: label, optional verbatim detail text, and
  the operator's reported event count.
  `operations_summary` rolls the recorded reports up per
  environment — counts and sums of recorded values only,
  derived at read, `method: recorded_operations_counts` — and
  is this unit's mutation-controlled derivation point (see
  tests/README.md).

`extension_summary` (report_read) counts extension records by
kind, derived at read.

## Re-judgment grounds

**No-code / low-code application development engine &
model-based design tooling (idx 399, drafted build-extension,
closing reference).** The entry names a development *engine*:
its substance is turning a design model into a running
application — generation, which is execution. The core's
founding invariant, restated in this group's UNION-SPEC core
function 6 and pinned by the core suite, is that configuration
text is stored verbatim and never executed; a development
engine built into this substrate would have to interpret and
run stored model text, breaking the invariant, or be an engine
in name only. The Moderate unit re-judged the identical
substance (customization & module engines: codeless
configuration runtimes, module execution) to exactly the form
used here, and the Low / LI-SaaS unit re-judged its
configuration-execution half the same way. What honestly lands
is the records layer in front of the engine: design definitions
held as data, generation requests, and reported outcomes.

**Decisioning engine (idx 401, drafted build-extension,
closing reference).** A decisioning engine's substance is
inference: choosing the next-best action from customer context
by a computed evaluation of that context. This build computes
no score anywhere, by design — scores are refused as keys,
labels, and values across the whole extension — and decisioning
without a computed decision is a decisioning engine in name
only. The category's adjudicated form for inference-shaped
entries, applied at both sibling tiers (AI/ML models & scoring
at Moderate; the AI-backed core function at Low / LI-SaaS), is
the labeled reference form used here: requests whose signature
refuses decision content, reported outcomes naming the
decision only by opaque reference, evaluation figures stored
verbatim. The entry is also, by its own parenthetical,
record-named rather than description-claimed.

**Managed cloud operations & application scaling platform
(idx 403, drafted build-extension, closing reference).** The
entry's own text names "the deployment layer itself,
operated." PLATFORM-LAYER.md decision 6 assigns the hosting
substrate and platform umbrella to the deployment layer, and
this group's UNION-SPEC claims no records function for hosting
(the ranking lists it as Platform layer). Operating a cloud —
provisioning environments, scaling running applications — is
execution against infrastructure, not records. A sibling
High-tier singleton unit closed the hosting platform itself as
`reference` on the same grounds. What honestly lands is the
records layer in front of the platform: environments named by
opaque reference and the operator's scaling and operations
reports stored as reported data.

The two stub-engine drafts (idx 400, 402) close `reference` as
drafted, in the forms the sibling units adjudicated for the
same substances.

## Long tail, enumerated against UNION-SPEC.md

- The fork's extended families carried from Group 25's Extended
  list (casework depth and article retrieval, guidance delivery
  runtime, gap identification & adoption analytics,
  customization & module engines, knowledge base & self-service
  content, marketing automation, integration connectors) were
  already registered and closed under Group 25's own section;
  carried-not-claimed families are not re-registered by this
  unit, and nothing in this unit re-opens them.
- The Extended families beyond this fork that UNION-SPEC.md
  names rank for other CRM tiers (social listening & engagement
  at Low, referral & voice support at Moderate) are not entries
  in this section and are untouched by this unit.
- The platform-layer rows of the High ranking (identity and
  access management including MFA/IA-5, FIPS-validated
  cryptography SC-13, encryption at rest SC-28, audit retention
  AU-11, session controls AC-11/AC-12) stand on
  [`../../PLATFORM-LAYER.md`](../../PLATFORM-LAYER.md) and were
  closed there; they are not among this section's 5 entries.

## Named as not covered

- Any actual application generation, design execution, or
  model interpretation: the no-code surface holds design text
  as data and records generation requests and reports; it
  generates nothing.
- Any workflow execution or case automation: definitions, run
  requests, and reported outcomes only; no automation reads or
  writes a case on the engine's behalf.
- Any decisioning inference, next-best-action computation, or
  propensity scoring: requests and reported outcomes only.
- Any model execution, GenAI drafting, or content generation:
  requests and reported outcomes only; no generated content is
  accepted by any signature in this module.
- Any hosting, provisioning, operations, or scaling of a real
  platform: environments are records named by opaque reference
  and platform activity arrives only as operator reports.
- The core's named absences (opportunities & sales pipeline;
  campaigns & audience lists) are untouched: nothing in this
  module sells, markets, or pipelines.
- Real authentication / identity proofing behind the demo actor
  hooks: the extension inherits the group's existing posture
  (hooks, not an IdP) and adds no identity function.
