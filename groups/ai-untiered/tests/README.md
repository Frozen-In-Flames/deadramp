# Tests — Artificial Intelligence (AI), untiered set

Stdlib `unittest` only. Zero third-party imports in `tests/` or
`../src/`. Every core test docstring names the UNION-SPEC core
function / spec claim / control family it traces to.

## Run

```bash
cd groups/ai-untiered
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **159 tests, OK** against the implementation
in `../src/`: the founding group's 146-test core suite carried
with the code (its `test_additions.py`, which pins a different
census unit, was NOT carried), plus 13 spec tests in
`test_specs.py` pinning this untiered set. (Run exactly as above:
helpers are imported as a top-level module from the tests
directory and `tests/__init__.py` is empty by design, so
package-mode discovery with `-t .` is not the supported entry
point for this group.) Test scratch files (audit JSONL) are
created only under the group's `scratch/` directory, never
`/tmp`. The carried suite is byte-identical to the founding
group's except one labeling fix in `aigateway_helpers.py` (its
docstring now names this untiered set instead of L2).

## Coverage map

| File | Core function(s) traced |
|---|---|
| `test_access.py` | 9 Access control & API keys — exact permission matrix for admin/member/viewer (admin = all eight actions; member = {read, registry_write, invoke, eval_run, usage_read}; viewer = {read, usage_read}), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | 10 Audit log — entry keys `ts, actor, action, target, details`, append-only, JSONL file + reload on construction, and the store recording each mutation action (`model_register`, `template_register`, `key_create`, `quota_set`, `session_create`, `invoke`, `policy_add`, `policy_remove`, `eval_dataset_create`, `eval_run`, `model_status`) |
| `test_registry.py` | 1 Model registry + 2 Prompt template registry — shapes/provenance, `mdl-`/`tpl-` id sequences, auto-incrementing versions per name, explicit duplicate (name, version) → `ValidationError`, responder/config validation (template requires `config["template"]`; rules requires `{match, response}` pairs + `default`), `get_*` highest-version selection, sorted lists, `set_model_status`, viewer write denials, failed ops consume no ids |
| `test_keys_quotas.py` | 9 Access control & API keys + 4 Usage metering & quotas — secret shown only at creation, store keeps only the SHA-256 digest (and the secret is never audited), `authenticate_key`, owner-scoped key lists without `secret`/`secret_hash`, owner-or-admin key creation, quota set/get/replace + positive-integer validation + admin-only set, current-month `usage_for` aggregation, quota pre-check (strict "would exceed", exact-limit allowed, charged to the key's owner) |
| `test_gateway.py` | 3 Gateway & reference responder + 4 pinned estimator — `estimate_tokens` formula (`0` for empty, else `(len+3)//4`), exact `REFERENCE_NOTICE` text, echo/template/rules responders, invoke record shape with `reference_stub: true`, version routing, deprecated-model refusal, key/session/template steps (2–4), stub audit details `{model, total_tokens}`, viewer denial |
| `test_policy.py` | 6 Policy guardrails — rule shape/`rule-` ids, scope/kind/regex-compile validation, creation-order evaluation (first match blocks), term (case-insensitive substring) and pattern (regex search) matching, input/output/both scoping, `blocked_input` and `blocked_output` records with pinned usage, `PolicyBlocked.request_id`, `invoke_blocked` audit details `{stage, rule_id}`, blocked records counted in usage, admin-only `policy_write` |
| `test_records.py` | 5 Conversation & request records — session shape/`ses-` ids, owner-or-admin session reads, scoped chronological session/request lists, turns appended on completion only (never on a block), request-record operational metadata, and zero-persistence mode: records and turns carry `prompt`/`output` as `None` plus `content_withheld: true` with metadata stored in full (normal mode carries no `content_withheld` key) |
| `test_eval.py` | 7 Evaluation harness — dataset validation + sequential `case-1…` ids, exact (strip-compared) and contains (case-insensitive) scoring, rubric criteria (all must pass), `score = passed/total` as a float, runs exercise the responder directly (no request record, no metering, no quota/policy effect), `eval_run` audit, creator-or-admin run reads, datasets/runs stored by design even in zero-persistence mode |
| `test_service.py` | 8 API access — live HTTP server: health without auth, 401 unknown user / role mismatch, 403 viewer actions, 404 unknown model/path, 400 invalid input, 422 policy-blocked completion, 429 quota-exceeded completion, full flows (models/templates/keys/quotas/completions/sessions/requests/usage/policy rules + delete/eval datasets + runs/audit), secret-once over HTTP, `audit_read` admin-only, denied attempts (401/403/422/429) audited with the `:denied` suffix, no stack traces |
| `test_main_cli.py` | `python -m aigateway serve` subprocess with demo users alice/bob/carol, including the `--zero-persistence` flag end-to-end over HTTP and the no-command help path |
| `test_negative_control.py` | Negative control (below) |
| `test_specs.py` | Untiered-set spec integrity — exactly 9 sheets in remainder-unit order (membership exact against `remainder.json` unit `untiered:Artificial Intelligence (AI)`), tier discipline on every sheet (`fedramp_impact_level` "Unknown", `cmmc_tier` null), the literal per-fork claim tables (13 claims total), the 16-family counts, the zero-claim set exactly {Bland, Lemma}, evidence verbatim under the founding normalization or its truncated form, the removed Bland `model_gateway` hit absent, and the headline near-misses (Claude / ElevenLabs `learned_inference`, ElevenLabs `multi_tenancy` / `zero_persistence`) pinned unclaimed |
| `aigateway_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OTHER_MEMBER), `make_store()` building an AIGatewayStore + AuditLog + an ADMIN-registered echo model, template/rules model helpers, and scratch-dir helpers confined to the group's `scratch/` |

## Negative control

`test_negative_control.py` implements the contract's required
mutant: a policy check that treats **every** text as clean
(always returns "no match"). The traced claim, named in the
module's docstrings, is that the policy gate is the gateway's
guardrail enforcement point (invoke step 6). For the canonical
case (a prompt containing the blocked term `badword`) the tests
assert three things: the canonical expectation (`PolicyBlocked`
from the real implementation, exactly one stored `blocked_input`
record, nothing completed, an `invoke_blocked` audit entry naming
the rule), that the mutant gate would NOT raise (it waves the
blocked prompt through as "allowed"), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails. The module does **not**
patch the real `src/` policy evaluation itself; that drill is
the coordinator's (see below).

## Mutation verification

VERIFIED in this tree at delivery. The policy evaluation in
`AIGatewayStore._first_policy_match` (`src/aigateway/store.py`) —
the gateway's single policy-evaluation point, invoked for both
the input and output stages — was patched to `return None` as
its first statement: the exact live counterpart of the mutant in
`test_negative_control.py`, treating every text as clean and
waving every blocked invocation through. The full suite was run:
**159 tests ran, exactly 14 failed**. The failures span every
policy-gated surface: 8 in test_policy (input term block, regex
pattern rule, output block with withheld output, first-match
ordering, both-scope blocking, blocked record + exception
request_id, blocked audit entry, blocked usage accounting), 2 in
test_negative_control (the canonical expectation and the
mutant-gate demonstration), 1 in test_gateway (a policy block is
not a completion), 1 in test_service (HTTP 422 for a
policy-blocked completion), and 2 in test_records (blocked record
content withholding under zero-persistence, no session turn
appended for a blocked invoke). No spec test failed — the spec
pins are JSON facts, not policy behavior. `store.py` was then
restored from `scratch/store.py.premutation` (SHA-256
`4a2b74e47fffd731b0bf92dbb1266bf87f0641ee22601bb143a1f3d6807b0e3f`,
verified identical to the pre-mutation hash and to the founding
group's shipped `store.py`) and the suite re-run: **159 tests,
OK**. Raw drill output: `scratch/mutation_run.txt`. The suite
catches this defect class; the negative control is not
decorative.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite follows
the shipped implementation's documented choices (carried from the
founding group):

- `usage_for`'s `month` is the current UTC month as `YYYY-MM`,
  and usage aggregates the records' `total_tokens` for the
  effective owner (the key's owner when a key is used, else the
  actor).
- List endpoints over HTTP wrap their payload (`{"models": [...]}`,
  `{"templates": [...]}`, `{"keys": [...]}`, `{"requests": [...]}`,
  `{"sessions": [...]}`, `{"rules": [...]}`, `{"datasets": [...]}`),
  mirroring the sibling Collaboration build; `/audit` is pinned
  by the contract to `{"entries": [...]}`.
- Statuses the contract does not pin are 200: `POST /quotas`,
  `POST /models/{name}/versions/{v}/status`, and
  `DELETE /policy/rules/{id}`. Creation endpoints the contract
  does pin to 201 are asserted as 201.
- `run_eval` refuses a deprecated model with `ValidationError`,
  by the same "deprecated models refuse requests" rule the
  contract pins for the gateway (Core function 1); the contract
  does not state this case for eval explicitly.
- The service records `audit_read` before reading the entries,
  so a successful `GET /audit` response's trail includes that
  read itself.
- A plain string actor carries identity but no role (the sibling
  build's `_maybe_require` convention): role enforcement applies
  to User-like actors, which is what the service layer always
  passes.

## Final GAPS batch module

The batch extension (`src/aigateway/extensions.py`,
`AIGatewayExtensions`, a wrapper over the untouched core store)
is pinned by `test_gaps_batch.py`. Its 8 entries (2 built, 6
reference), in the same evidence order as the union spec's
Extended functions:

| Batch entry | Pins in `test_gaps_batch.py` |
|---|---|
| Model serving & inference infrastructure | Configuration records over the core registry: exact key set (and no `reference_stub` -- a built record, not a stub), highest-version resolution, refusal for unknown and for deprecated models with no id consumed on refusal, replica-count validation, serving events stored verbatim with `enacted_here: False`, and the serving rollup derived at read (endpoint/event counts, the reported-replica total, sorted model names) with no derived key on any stored record |
| Evaluation & benchmarking engines | Benchmark definitions bound to an existing core dataset and model (NotFound otherwise), runs executed by the core harness itself returning the core run record, link records storing no score, view totals derived at read from the core's run records and proven across two runs, the view inheriting the core's run-ownership discipline (another member refused, admin admitted), a deprecated-model run refused with no link id consumed, and viewer denial audited |
| Learned inference: the models themselves | Request records bound to a registered model with the prompt named only by an optional validated SHA-256 digest, outcome records with the output as an opaque reference only, every record labeled `reference_stub: True` with `inference_here: False`, bad digest refused (including uppercase hex), `prompt=`/`output=` arguments raising TypeError, and a pinned check that registering a request creates no core request record |
| Agentic workflow execution engines | Workflow definitions held as data (step labels verbatim, optional registered model), run requests and reported outcomes, every record labeled with `executed_here: False`, and a pinned check that defining a workflow and requesting a run create no core request and no core session while the core gateway still serves its own reference stub |
| Voice & speech AI engines | Job records for the four recorded voice kinds with an opaque input reference only, outcome records with results as opaque references, `processed_here`/`media_held` False, unknown kinds refused, and `audio=`/`transcript_text=` arguments raising TypeError |
| Document understanding, summarization & report generation | Job records naming the document by opaque reference plus optional validated digest (re-judged to reference; see `BATCH.md`), result records with outputs as opaque references only, `processed_here`/`generated_here`/`content_held` False, and `document_text=`/`content=`/`summary_text=` arguments raising TypeError |
| Knowledge-base / retrieval (RAG) engines | Definition records, ingestion records with counts stored exactly as reported, retrieval queries named only by optional digest, results with answers as opaque references and citations as reference lists (re-judged to reference; see `BATCH.md`), `embeddings_computed_here`/`index_built_here`/`retrieved_here`/`grounded_here` False, and `embeddings=`/`vector=`/`query_text=`/`answer_text=` arguments raising TypeError |
| Vertical workflow applications | Case records for the three recorded verticals keyed by opaque case reference, step labels recorded as reported, outcome records with outputs as opaque references, `casework_performed_here`/`records_generated_here` False, unknown verticals refused, and `subject_name=`/`record_text=` arguments raising TypeError |

Cross-cutting pins: denied writes are audited with the
`:denied` suffix (serving, benchmark, and inference paths),
actorless writes are refused, and the extension summary counts
every record kind at read. **The tier-null pin**: a recursive
walk over every extension record and view (all 20 record kinds
plus the three derived views, populated end to end) asserting no
key contains `tier`, `cmmc`, `baseline`, `equivalence`, or
`impact_level`, no value is a float, no list holds a number, and
every `reference_stub` key found is `True` -- the set asserts no
baseline, so the extension surface cannot grow one.

## Batch negative control — mutation-verified

Fresh control for the batch surface: the serving gate.
`AIGatewayExtensions._serving_allowed` is the single derivation
point deciding whether a model version may be registered as
served; it mirrors the core's rule that deprecated models refuse
requests. The in-suite control
(`TestServingGateNegativeControl`) runs three legs: the real
gate refuses a serving endpoint for a deprecated model; a mutant
subclass with the seam forced open registers it; and treating
the mutant's outcome as canonical raises `AssertionError`.

Live drill, performed 2026-11-07: the seam's return line was
patched in place

```
return model["status"] == "active"  ->  return True
```

and the full suite run: **199 tests, exactly 2 failures**, both
in `test_gaps_batch.py`, both the expected ones:

- `test_endpoint_for_deprecated_model_refused_and_no_id_consumed`
  (canonical refusal: with the gate open, the registration
  succeeds and the `ValidationError` assertion fails);
- `test_three_leg_control` (the control's canonical leg no
  longer refuses, failing its `assertRaises`).

All 159 founding tests still passed under the mutant, confirming
the failure is attributable to the gate seam alone. The module
was then restored from `scratch/extensions.py.premutation`,
verified byte-identical by SHA-256 against
`scratch/extensions.py.sha256`, and the full suite re-run green:
199 tests, OK. The drill log is
`scratch/gaps_batch_mutation_run.txt`.
