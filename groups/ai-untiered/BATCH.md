# Final GAPS batch — Untiered Set 4: Artificial Intelligence (AI)

Unit: the 8 OPEN entries of the GAPS.md section "Untiered Set 4 —
Artificial Intelligence (AI) (9 forks, tier null)". Built
2026-11-07 under `gaps-batch/DECISION.md` (the 2026-11-07
ratified triage) and `PLATFORM-LAYER.md`. All extension code is
one new module, `src/aigateway/extensions.py`
(`AIGatewayExtensions`, a wrapper around the untouched core
store); the founding core modules are byte-identical. Tests:
`tests/test_gaps_batch.py` (40 tests; suite 159 → 199, all
passing). Per-entry dispositions below use the exact entry texts
from GAPS.md / `gaps-batch/inventory.json` (idx 778–785). The
section held exactly these 8 open entries and no ninth entry;
the disposition column is the closure token the parent records
in GAPS.md.

The set's binding constraints, restated from the founding build:
learned inference is the category's #1 family and is never built
— vendor models are their own and a stdlib build has none. Tier
is null: the set's forks publish no FedRAMP impact level, so the
union spec asserts no baseline and no CMMC equivalence, and the
extension surface carries no tier-shaped key anywhere (pinned by
a recursive scan in the batch tests).

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 778 | Learned inference: the models themselves (four claimants in this set; the build's inference surface remains a labeled reference stub, never a model) | stub-engine | **reference** | Inference request records bound to a registered core model/version (`ireq-`) and outcome records (`iout-`). The prompt is identified only by an optional validated SHA-256 `prompt_digest` — no parameter accepts prompt text (`prompt=` raises TypeError) — and the output exists only as an opaque `output_ref` (`output=` raises TypeError). Every record carries `reference_stub: True`, `inference_here: False`; a test pins that registering a request creates no core request record. |
| 779 | Agentic workflow execution engines | stub-engine | **reference** | Workflow definition records held as data (`awf-`: step labels verbatim, optional registered model, `definition_only: True`), run-request records (`arun-`), and reported-outcome records (`aout-`), all `reference_stub: True`, `executed_here: False`. A test pins that defining a workflow and requesting a run create no core request and no core session — the registry never executes an agent — while the core gateway still serves its own reference stub. |
| 780 | Voice & speech AI engines | stub-engine | **reference** | Voice job records (`voj-`) for the four recorded kinds (speech_to_text, text_to_speech, voice_agent, real_time_interpretation) with an opaque `input_ref` only, and outcome records (`vou-`) whose results are opaque references. `reference_stub: True`, `processed_here: False`, `media_held: False`; `audio=` and `transcript_text=` arguments raise TypeError — no media or text content exists anywhere on the surface. |
| 781 | Model serving & inference infrastructure | build-extension | **built** | Serving-endpoint configuration records (`sep-`) bound to a registered core model/version, plus serving-event records (`sev-`) holding platform-reported event labels verbatim, and a `serving_summary` derived at read (endpoint/event counts, the reported-replica total, sorted model names; stored records carry no derived key). Endpoints register only for **active** model versions — the serving gate mirroring the core's deprecated-refusal rule; that gate is the batch's fresh negative control. The records state their own boundary: `provisioned_here: False`, `autoscaled_here: False`, `state: "recorded_configuration"`. No infrastructure is provisioned by these records and nothing is served by them; the gateway's reference responder remains the only serving surface in the build, and it is a stub. |
| 782 | Document understanding, summarization & report generation | build-extension | **reference** (re-judged) | Document job records (`dcj-`) naming the document by opaque `document_ref` plus an optional validated SHA-256 `document_digest`, and result records (`dcr-`) naming the output by opaque `result_ref` only. `reference_stub: True`, `processed_here: False`, `generated_here: False`, `content_held: False`; `document_text=`, `content=`, and `summary_text=` arguments raise TypeError. Grounds for the re-judgment below. |
| 783 | Knowledge-base / retrieval (RAG) engines | build-extension | **reference** (re-judged) | Knowledge-base definition records (`kb-`: name plus opaque `source_refs`), ingestion records (`kbi-`) whose document/chunk counts are stored exactly as reported, retrieval-query records (`rtq-`) naming the query only by an optional validated SHA-256 digest, and retrieval-result records (`rtr-`) with the answer as an opaque `answer_ref` and citations as reference strings. `reference_stub: True` throughout, `embeddings_computed_here` / `index_built_here` / `retrieved_here` / `answer_held` / `grounded_here` all False; `embeddings=`, `vector=`, `query_text=`, and `answer_text=` arguments raise TypeError. Grounds for the re-judgment below. |
| 784 | Evaluation & benchmarking engines | build-extension | **built** | Benchmark definition records (`bmk-`) binding one core evaluation dataset to one registered model/version, run records (`bmr-`) that are links to core evaluation runs, and a `benchmark_view` whose run/case/pass totals are derived at read from the core's own run records. A benchmark run **is** a core `run_eval`: the harness's deterministic exact/contains/rubric scoring over the registered reference responder, executed and recorded by the core. Nothing new is scored — the extension stores no score anywhere (the link record's key set is pinned score-free), no external model is evaluated (`external_models_evaluated: False`), and reading a view inherits the core's run-ownership discipline (creator-or-admin; pinned by test). |
| 785 | Vertical workflow applications (public-records generation, human-services case work, constituent contact center) | stub-engine | **reference** | Vertical case records (`vtc-`) for the three recorded verticals, keyed by an opaque `case_ref` with an optional registered model; step records (`vts-`) holding step labels as reported; outcome records (`vto-`) with outputs as opaque references. `reference_stub: True`, `casework_performed_here: False`, `records_generated_here: False`, `executed_here: False` on steps; `subject_name=` and `record_text=` arguments raise TypeError — no person's name and no generated record content can be held. |

## Re-judgments (DECISION.md qualification 1)

Two entries drafted build-extension are re-judged to reference
on close reading, because their substance is a running model and
the category's founding doctrine — ratified in the AI L2 build
and restated in this unit's brief — is that learned inference is
never built. This is the batch's standing treatment of
inference-shaped entries (cf. Operations Management's AI
assistants and Law Enforcement's AI investigation models, both
closed reference).

- **idx 782 (document understanding, summarization & report
  generation).** Understanding a document, summarizing it, and
  generating a report from it are the model's own work; there is
  no records-only form of "understanding" that is not a label
  for inference. What can honestly be built is the surrounding
  platform surface — job intake, model binding, result
  references — and that surface is exactly what ships, labeled.
  Closing it `built` would claim a capability the build does
  not have.
- **idx 783 (knowledge-base / retrieval (RAG) engines).** The
  knowledge-base half has a genuine records form (definitions,
  source references, reported ingestion counts — cf. Data
  Management's built vector-collection definitions), and that
  half ships in records form. But the entry's own text names
  the *retrieval engine* as the deliverable, and retrieval of
  the RAG kind — embeddings, similarity search, grounded
  citation-based answers — is a running model: computing
  embeddings or grounding an answer here would require an
  inference engine this build does not have. The entry
  therefore closes reference as a whole, with the definition
  half carried inside the labeled records rather than split
  into a `built` claim the entry text does not support.

No other re-judgment was needed. The two `built` closures are
bounded the other way: idx 781 builds the *configuration
records* of serving infrastructure over the core registry (the
same form in which Data Management untiered closed its
petabyte-scale warehouse entry built), with the records
themselves stating that nothing is provisioned or served; idx
784 builds only records *over* the core's existing harness —
dataset/model binding, run links, derived totals — and scores
nothing new, which is precisely the bound the unit brief set
("nothing new is scored").

## Negative control

Fresh, for this surface: the serving gate
(`AIGatewayExtensions._serving_allowed`). In-suite three-leg
control in `test_gaps_batch.py`
(`TestServingGateNegativeControl`): canonical refusal of a
deprecated-model endpoint; a mutant subclass with the seam
forced open registers it; treating the mutant outcome as
canonical raises `AssertionError`. Live drill performed
2026-11-07 (recorded in `tests/README.md`, log in
`scratch/gaps_batch_mutation_run.txt`): patching the seam's
return line to `return True` produced exactly **2 failures** out
of 199 — the canonical refusal test and the control itself —
with all 159 founding tests still passing; the module was
restored from `scratch/extensions.py.premutation`, SHA-256
verified, and the suite re-run green (199 tests, OK).

## What is NOT covered (named, not closed silently)

- **Real serving.** Endpoint records are configuration records.
  Deploying, scaling, load-balancing, or routing traffic to an
  actual model runtime is outside this build; nothing here
  provisions infrastructure.
- **Real inference of any kind.** No prompt is executed by the
  extension surface; the only responder in the build remains the
  core gateway's deterministic reference stub, unchanged.
- **Real retrieval.** No embedding is computed, no index exists,
  no document is fetched, and no answer is grounded or verified
  here; citation references are the external system's report,
  stored as references.
- **The forks' platform assertions stay assertions.** Bedrock's
  "FedRAMP-authorized infrastructure" sentence and the set's
  multi-tenancy language remain the forks' claims about their
  own platforms (UNION-SPEC §Documented control claims); the
  extension surface records nothing about hosting and asserts
  nothing about it. PLATFORM-LAYER.md decisions 1–6 are
  untouched by this unit: no identity provider, no validated
  cryptography, no retention enforcement, and no session layer
  was built or claimed.
- **The two zero-claim forks (Bland, Lemma)** contribute no
  claims to this unit, as in the founding build; nothing was
  back-filled for them.
