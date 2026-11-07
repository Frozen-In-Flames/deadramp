# Final GAPS batch — Group 22: Artificial Intelligence (AI) L3-adjacent

Unit: the 6 OPEN entries of the GAPS.md section "Group 22 —
Artificial Intelligence (AI) L3-adjacent (3 forks)". Built
2026-11-07 under `gaps-batch/DECISION.md` (the 2026-11-07 ratified
triage) and `PLATFORM-LAYER.md`. All extension code is one new
module, `src/aigateway/extensions.py` (`AIGatewayExtensions`, a
wrapper around the untouched core store); the founding core
modules are byte-identical (store.py SHA-256 `2c71ff55…c515031`
before and after; full baseline in
`scratch/extensions_baseline.sha256`). Tests:
`tests/test_gaps_batch.py` (30 tests; suite 193 → 223, all
passing). Per-entry dispositions below use the exact entry texts
from GAPS.md / `gaps-batch/inventory.json` (idx 229–234). The
disposition column is the closure token the parent records in
GAPS.md.

The group's binding constraint, restated from the founding
build's honesty note (UNION-SPEC.md): learned inference is what
all three siblings sell and is never built — each vendor's models
are their own proprietary artifacts, and a Python-standard-library
build has no learned models. The High uplift hardens the platform
layer around models; it does not change what the responder is.
What the siblings genuinely share, and what this batch extends,
is that platform layer.

The extension surface follows the Group 9 (AI L2) batch unit's
forms (`../ai-l2/BATCH.md`, commit cf42a0c) where the families
overlap — the six entries here are the same six families, carried
from the Group 9 union or claimed by this group's own forks —
adapted to this group's baseline as its own docs state it. The
adaptations: the vertical domains are this group's own three
(idx 234); extension record creation is fail-closed on the
hash-chained audit log (AU-5), rolling back the record and its id
allocation if the audit append raises, exactly like the core
store's own mutations; and the separated `auditor` role (AC-5),
holding `audit_read` only, is denied every extension operation
including reads, with the denial audited — its audit-review duty
runs through the core log, unchanged. Both bindings are pinned by
tests (`TestHighBaselineBindings`).

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 229 | Learned AI/ML inference: real LLMs / ML / NLU / predictive models (3 of 3 claim it; with Group 9's, the final batch's largest single item). The reference responder is a labeled stub, not a substitute. | stub-engine | **reference** | Inference request records bound to a registered core model/version (`ireq-`) and outcome records (`iout-`). The prompt is identified only by an optional validated SHA-256 `prompt_digest` — no parameter accepts prompt text (`prompt=` raises TypeError) — and the output exists only as an opaque `output_ref` (`output=` raises TypeError). Every record carries `reference_stub: True`, `inference_here: False`; a test pins that registering a request creates no core request record and no core session. The entry's own text already states the boundary ("a labeled stub, not a substitute"); the records form is the platform surface around requests made elsewhere, the same form as Group 9's idx 81. |
| 230 | Agentic & automated workflow engines (1) | stub-engine | **reference** | Workflow definition records held as data (`awf-`: step labels verbatim, optional registered model, `definition_only: True`), run-request records (`arun-`), and reported-outcome records (`aout-`), all `reference_stub: True`, `executed_here: False`. A test pins that defining a workflow and requesting a run create no core request and no core session — the registry never executes an agent — while the core gateway still serves its own reference stub. The one claimant (Cognition) rests on the "automated" wording artifact recorded in UNION-SPEC.md; the agents themselves are inference, so the execution half stays with the vendor's runtime. |
| 231 | Document processing & generation workloads (0 tagged under the verbatim taxonomy; one sibling's entire domain in prose, recorded as a near-miss, not invented) | stub-engine | **reference** | Document job records (`dcj-`: extraction/classification/summarization/generation; opaque `document_ref` + optional validated SHA-256 `document_digest`) and result records (`dcr-`) naming the output by opaque `result_ref` only. `reference_stub: True`, `processed_here`/`generated_here`/`content_held: False`; `document_text=`, `content=`, and `summary_text=` arguments raise TypeError. Extraction and generation are inference workloads; Ripcord's digitization domain is exactly this family in prose (the near-miss the entry itself records), and the intake/result records are the honest platform surface. |
| 232 | Analytics, dashboards & reporting (0 in this group; carried from the Group 9 union) | build-extension | **built** | Dashboard definition records (`dash-`) holding panel labels from a fixed panel set (unknown panels refused) — the stored definition's key set is pinned to exactly `{id, name, panels, created_by, created_utc}`, so no figure can be stored — plus `analytics_view` and `dashboard_view` whose figures are derived at read from the core's own records: request counts by status and model and token totals (via the figure-inclusion seam below), model/template registry counts, session counts, evaluation-dataset and case totals, and the core's own current-month usage aggregate for the requesting actor. Figures are computed over exactly the records visible to the actor under the core's read discipline (an admin sees all request records; a member sees their own; pinned by test with a non-owner member seeing zero). A freshness test proves a dashboard defined before any traffic reports the traffic recorded after it. |
| 233 | Contact center & customer experience (0 in this group; carried from the Group 9 union) | stub-engine | **reference** | Contact case records (`ccc-`, opaque `case_ref`, channel label), event records (`cce-`), outcome records (`cco-`); `routed_here`/`orchestrated_here: False`; `customer_name=`, `message_text=`, `transcript=` raise TypeError — no person's name and no conversation content can be held. A vertical application of routing/engagement engines (UNION-SPEC row 16), not platform substrate; the case-records form is what ships, labeled. |
| 234 | Vertical domain applications: AI software-development platform, ML lifecycle development & governance platform, digitization-as-a-service (one sibling each) | build-extension | **built** | Vertical application profile records (`vap-`) whose `domain` is one of the three domains named by the entry's own text — `ai_software_development_platform` (Cognition), `ml_lifecycle_development_governance_platform` (DataRobot), `digitization_as_a_service` (Ripcord) — with an optional binding to a registered core model; activity records (`vaa-`) holding activity labels verbatim with subjects named only by opaque `subject_ref`; and `application_view` rollups (activity total, distinct labels) derived at read — the stored profile carries no totals (pinned by test). Every record states `operated_here: False`: what is built is the platform-side records surface for a vertical application (profile, model binding, activity record, derived view — the same form as Group 9's idx 86), over this substrate's own registry. The verticals' own engines — Cognition's autonomous coding agent, DataRobot's training and governance machinery, Ripcord's robotics and OCR — are the siblings' products and are not operated or simulated here; no parameter accepts a payload, code, a dataset, or any domain content (`payload=`, `code=` raise TypeError). |

## Re-judgments (DECISION.md qualification 1)

None. All six entries close with their drafted dispositions.
The two `built` closures are bounded as their rows state: idx
232 builds derivations over the core's own records and nothing
else (no external analytics is imported and no figure is
stored); idx 234 builds the records surface of the vertical
applications with the operating half stated absent on every
record, rather than claiming any vertical's engine. The four
`reference` closures follow the category's standing treatment
of inference-shaped entries: their substance is a running model
(or, for idx 230, runtimes whose agents are inference), and the
honest records form ships labeled.

One check, recorded here as in the Group 9 unit: this group's
core **does** have an evaluation function — Core function 7,
`run_eval`, the evaluation harness exercised over the registered
reference responder. No entry in this section is
evaluation-shaped (evaluation records are Core in this group,
UNION-SPEC row 12, not Extended), so the Untiered Set 4
adjudication for evaluation entries (built where runs execute
via the core's own harness) has nothing to attach to in this
unit; the analytics surface reads evaluation *datasets* as
registry counts only and scores nothing new.

## Negative control

Fresh, for this surface: the figure-inclusion seam
(`AIGatewayExtensions._counts_toward_figures`). The canonical
rule mirrors the core's usage accounting (UNION-SPEC core
function 4: usage aggregates include blocked records): every
stored request record counts toward the derived figures. The
in-suite three-leg control in `test_gaps_batch.py`
(`TestFigureInclusionNegativeControl`): canonical figures over
one completed + one blocked invocation total 2 with the blocked
record counted; a mutant subclass counting only completed
records totals 1 and understates the token total; treating the
mutant's total as the canonical expectation raises
`AssertionError`. Live drill performed 2026-11-07 (recorded in
`tests/README.md`, log in `scratch/gaps_batch_mutation_run.txt`):
patching the seam's return line to
`return record["status"] == "completed"` produced exactly
**5 failures** out of 223 — the canonical leg and the
mutant-comparison leg of the control, plus the three analytics
tests that pin blocked-inclusive figures (figures coverage,
actor scoping, dashboard freshness) — with all 193 founding
tests still passing; the module was restored from
`scratch/extensions.py.premutation`, SHA-256 verified
(`16ec3aa0…`), and the suite re-run green (223 tests, OK).

## What is NOT covered (named, not closed silently)

- **Real inference of any kind.** No prompt is executed by the
  extension surface; the only responder in the build remains
  the core gateway's deterministic reference stub, unchanged
  and labeled. The inference request records are records of
  requests made elsewhere.
- **Real agent or workflow execution.** Definitions are data
  and run requests are records; no step of any workflow runs
  here, and no core request or session is created by asking.
- **Real document processing or generation.** No document is
  read, extracted from, or produced; documents and outputs
  exist on this surface only as opaque references and digests.
- **Real contact-center operation.** No interaction is routed,
  queued, orchestrated, or conducted; no customer is contacted
  and no conversation content exists in any record shape.
- **The verticals' own engines.** Application profiles do not
  write or deploy code, train or govern a model, or digitize a
  document; the records state `operated_here: False` and mean
  it.
- **PLATFORM-LAYER.md decisions 1–6 are untouched** by this
  unit: no identity provider, no validated cryptography, no
  retention enforcement, no session layer, and no hosting or
  multi-tenancy claim was built or implied. The group's
  multi-tenancy platform note (1 tagged claim — Ripcord;
  DataRobot's "single tenancy isolation" near-miss) stays a
  platform note under decision 6, exactly as UNION-SPEC.md and
  the GAPS.md section record it; it is not among this unit's 6
  entries and nothing here closes it.
- **The five High baseline gaps** named in the GAPS.md section
  (MFA/authenticator management, FIPS-validated cryptography,
  encryption at rest, audit retention enforcement, session
  lock/termination) are platform-layer entries closed in
  writing under PLATFORM-LAYER.md, not by this build; the
  extension inherits the core's posture on each and adds
  nothing to it.
