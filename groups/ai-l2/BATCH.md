# Final GAPS batch — Group 9: Artificial Intelligence (AI) L2

Unit: the 6 OPEN entries of the GAPS.md section "Group 9 —
Artificial Intelligence (AI) L2 (11 forks)". Built 2026-11-07
under `gaps-batch/DECISION.md` (the 2026-11-07 ratified triage)
and `PLATFORM-LAYER.md`. All extension code is one new module,
`src/aigateway/extensions.py` (`AIGatewayExtensions`, a wrapper
around the untouched core store); the founding core modules —
including the remainder addition's shipped state — are
byte-identical (store.py SHA-256 `4a2b74e4…e3f` before and
after). Tests: `tests/test_gaps_batch.py` (28 tests; suite
157 → 185, all passing). Per-entry dispositions below use the
exact entry texts from GAPS.md / `gaps-batch/inventory.json`
(idx 81–86). The disposition column is the closure token the
parent records in GAPS.md.

The group's binding constraint, restated from the founding
build's honesty note (UNION-SPEC.md): learned inference is the
group's #1 family and is never built — each vendor's models are
their own proprietary artifacts, and a Python-standard-library
build has no learned models. What the siblings share, and what
this batch extends, is the platform layer around the models.

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 81 | Learned AI/ML inference: real LLMs, ML, NLU, and predictive models (8 of 11 forks claim it; the group's #1 family). Each vendor's models are their own; the shipped core's responder is a deterministic reference stub (echo/template/rules) labeled `reference_stub: true` on every response, and is not a substitute for inference. | stub-engine | **reference** | Inference request records bound to a registered core model/version (`ireq-`) and outcome records (`iout-`). The prompt is identified only by an optional validated SHA-256 `prompt_digest` — no parameter accepts prompt text (`prompt=` raises TypeError) — and the output exists only as an opaque `output_ref` (`output=` raises TypeError). Every record carries `reference_stub: True`, `inference_here: False`; a test pins that registering a request creates no core request record and no core session. The entry's own text already states the boundary (the core responder "is not a substitute for inference"); the records form is the platform surface around requests made elsewhere, which is all this category ever builds for this family (cf. Untiered Set 4, idx 778, same form). |
| 82 | Agentic & automated workflow engines (4) | stub-engine | **reference** | Workflow definition records held as data (`awf-`: step labels verbatim, optional registered model, `definition_only: True`), run-request records (`arun-`), and reported-outcome records (`aout-`), all `reference_stub: True`, `executed_here: False`. A test pins that defining a workflow and requesting a run create no core request and no core session — the registry never executes an agent — while the core gateway still serves its own reference stub. The agents themselves are inference (UNION-SPEC row 4), so the execution half stays with the vendors' runtimes. |
| 83 | Document processing & generation workloads (4) | stub-engine | **reference** | Document job records (`dcj-`) for the four recorded kinds (extraction, classification, summarization, generation) naming the document by opaque `document_ref` plus an optional validated SHA-256 `document_digest`, and result records (`dcr-`) naming the output by opaque `result_ref` only. `reference_stub: True`, `processed_here`/`generated_here`/`content_held: False`; `document_text=`, `content=`, and `summary_text=` arguments raise TypeError. Extraction and generation are inference workloads (UNION-SPEC row 5); the intake/result records are the honest platform surface. |
| 84 | Analytics, dashboards & reporting (2) | build-extension | **built** | Dashboard definition records (`dash-`) holding panel labels from a fixed panel set (unknown panels refused) — the stored definition's key set is pinned to exactly `{id, name, panels, created_by, created_utc}`, so no figure can be stored — plus `analytics_view` and `dashboard_view` whose figures are derived at read from the core's own records: request counts by status and model and token totals (via the figure-inclusion seam below), model/template registry counts, session counts, evaluation-dataset and case totals, and the core's own current-month usage aggregate for the requesting actor. Figures are computed over exactly the records visible to the actor under the core's read discipline (an admin sees all request records; a member sees their own; pinned by test with a non-owner member seeing zero). A freshness test proves a dashboard defined before any traffic reports the traffic recorded after it. |
| 85 | Contact center & customer experience (1) | stub-engine | **reference** | Contact case records (`ccc-`) keyed by an opaque `case_ref` with an optional channel label from the recorded channel set and an optional registered model, event records (`cce-`) holding event labels verbatim, and outcome records (`cco-`) with outputs as opaque references. `reference_stub: True`, `routed_here`/`orchestrated_here: False`; `customer_name=`, `message_text=`, and `transcript=` arguments raise TypeError — no person's name and no conversation content can be held. Genesys's domain is a vertical application of routing/engagement engines (UNION-SPEC row 16), not platform substrate; the case-records form is what ships, labeled. |
| 86 | Vertical domain applications: compliance/ERP enclave, IT asset management, electronics data exchange, manufacturing QC, requirements management, acquisition support, cloud infrastructure (one sibling each) | build-extension | **built** | Vertical application profile records (`vap-`) whose `domain` is one of the seven domains named by the entry's own text, with an optional binding to a registered core model; activity records (`vaa-`) holding activity labels verbatim with subjects named only by opaque `subject_ref`; and `application_view` rollups (activity total, distinct labels) derived at read — the stored profile carries no totals (pinned by test). Every record states `operated_here: False`: what is built is the platform-side records surface for a vertical application (profile, model binding, activity record, derived view — the same form in which the batch built Talent Management L2's development programs and Marketing & Sales untiered's market-intelligence reports), over this substrate's own registry. The verticals' own engines — the enclave's transaction processing, the QC inspection engine, the exchange's message translation — are the siblings' products and are not operated or simulated here; no parameter accepts a payload or any domain content (`payload=` raises TypeError). |

## Re-judgments (DECISION.md qualification 1)

None. All six entries close with their drafted dispositions.
The two `built` closures are bounded as their rows state: idx
84 builds derivations over the core's own records and nothing
else (no external analytics is imported and no figure is
stored); idx 86 builds the records surface of the vertical
applications with the operating half stated absent on every
record, rather than claiming any vertical's engine. The four
`reference` closures follow the category's standing treatment
of inference-shaped entries: their substance is a running
model (or, for idx 82, runtimes whose agents are inference),
and the honest records form ships labeled.

One check the brief called for is recorded here: this group's
core **does** have an evaluation function — Core function 7,
`run_eval`, the evaluation harness exercised over the
registered reference responder. No entry in this section is
evaluation-shaped (evaluation records are Core in this group,
UNION-SPEC row 11, not Extended), so the Untiered Set 4
adjudication for evaluation entries (built where runs execute
via the core's own harness, idx 784 there) has nothing to
attach to in this unit; the analytics surface reads evaluation
*datasets* as registry counts only and scores nothing new.

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
**5 failures** out of 185 — the canonical leg and the
mutant-comparison leg of the control, plus the three analytics
tests that pin blocked-inclusive figures (figures coverage,
actor scoping, dashboard freshness) — with all 157 founding
tests still passing; the module was restored from
`scratch/extensions.py.premutation`, SHA-256 verified
(`2f7b9432…`), and the suite re-run green (185 tests, OK).

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
  operate an ERP enclave, inspect a manufactured part, or
  translate an exchange message; the records state
  `operated_here: False` and mean it.
- **PLATFORM-LAYER.md decisions 1–6 are untouched** by this
  unit: no identity provider, no validated cryptography, no
  retention enforcement, no session layer, and no hosting or
  multi-tenancy claim was built or implied. The group's
  multi-tenancy platform note (6 claimants) stays a platform
  note, exactly as UNION-SPEC.md records it.
