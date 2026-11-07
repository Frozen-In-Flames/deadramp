# Tests — Artificial Intelligence (AI) L2 merged build

Stdlib `unittest` only. Zero third-party imports in `tests/` or
`../src/`. Every test docstring names the UNION-SPEC core function /
spec claim / control family it traces to.

## Run

```bash
cd groups/ai-l2
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **146 tests, OK** against the implementation in
`../src/`. After the remainder addition (unit `addition:ai-l2`,
see `../ADDENDUM.md`): **157 tests, OK** — the original 146 plus
11 in `test_additions.py`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.) Test scratch files (audit JSONL) are
created only under the group's `scratch/` directory, never `/tmp`.

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
| `test_additions.py` | Remainder addition (`addition:ai-l2`, ADDENDUM.md) — spec integrity for the appended Gobo sheet (membership vs `remainder.json`, the literal 2-claim table, the 14-family zero-claim set, verbatim evidence, census citation, near-miss pins incl. "AI-enabled" ≠ `learned_inference` and the agents sentence tagging nothing, group totals 12 forks / 47 claims), plus the fork's substrate cases: a labeled-stub automation invocation, metered and audited, and a human-in-the-loop policy block stored as `blocked_input` and audited (trips the policy mutant) |
| `test_gaps_batch.py` | Final GAPS batch (see `../BATCH.md`) — the extension surface in `src/aigateway/extensions.py` per entry: inference request/outcome records (digest-only prompt identity, `prompt=`/`output=` TypeError pins, no core request created), agent workflow definitions/run requests/outcomes (nothing executes; no core request or session), document job/result records (opaque refs + digests, content kwargs TypeError), analytics/dashboard figures derived at read over the records visible to the actor (definition key set pinned figure-free, freshness), contact case/event/outcome records (no name or conversation-content parameter), vertical application profiles/activity/views for the entry's seven named domains (stored profile carries no totals), the extension summary and `ext_` audit trail incl. a `:denied` entry, and the batch's fresh negative control (below) |
| `test_gaps_batch_addition.py` | Final GAPS batch, second unit (see `../BATCH-ADDITION.md`) — the addition surface in `src/aigateway/extensions_addition.py` per entry: twin profiles + performance observations (figures verbatim strings, numeric figure refused, `telemetry=`/`payload=` TypeError pins, view derives counts/labels/latest while the stored profile carries no derived key), transition plans/steps as data (status for an undeclared step refused consuming no id, per-step current status derived at read, configuration changes `applied_here: False` with `config_body=` TypeError, capacity figures verbatim with `computed_here: False`), the EIS suite as labeled reference records (every record `reference_stub: True`, current lifecycle status derived at read, `amount=`/`document=` TypeError pins), a recursive scan pinning no content/payload/amount/score key and no float value across every addition record and view, the addition summary and `exta_` audit trail incl. `:denied` entries, no core request or session created, and the unit's fresh negative control (below) |
| `aigateway_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OTHER_MEMBER), `make_store()` building an AIGatewayStore + AuditLog + an ADMIN-registered echo model, template/rules model helpers, and scratch-dir helpers confined to the group's `scratch/` |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a policy check that treats **every** text as clean (always returns "no
match"). The traced claim, named in the module's docstrings, is that
the policy gate is the gateway's guardrail enforcement point (invoke
step 6). For the canonical case (a prompt containing the blocked term
`badword`) the tests assert three things: the canonical expectation
(`PolicyBlocked` from the real implementation, exactly one stored
`blocked_input` record, nothing completed, an `invoke_blocked` audit
entry naming the rule), that the mutant gate would NOT raise (it waves
the blocked prompt through as "allowed"), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome as
the expected outcome fails. The module does **not** patch the real
`src/` policy evaluation itself; that drill is the coordinator's (see
below).

## Mutation verification

VERIFIED by the coordinator (2026-10-25). The policy evaluation in
`AIGatewayStore._first_policy_match` (`src/aigateway/store.py`) —
the gateway's single policy-evaluation point, invoked for both the
input and output stages — was patched to `return None` as its first
statement: the exact live counterpart of the mutant in
`test_negative_control.py`, treating every text as clean and waving
every blocked invocation through. The full suite was run: **146
tests ran, 14 failed**. The failures span every policy-gated
surface: 8 in test_policy (input term block, regex pattern rule,
output block with withheld output, first-match ordering, both-scope
blocking, blocked record + exception request_id, blocked audit
entry, blocked usage accounting), 2 in test_negative_control (the
canonical expectation and the mutant-gate demonstration), 1 in
test_gateway (a policy block is not a completion), 1 in
test_service (HTTP 422 for a policy-blocked completion), and 2 in
test_records (blocked record content withholding under
zero-persistence, no session turn appended for a blocked invoke).
`store.py` was then restored from a pre-mutation copy (SHA-256
verified identical to the pre-mutation hash) and the suite re-run:
**146 tests, OK**. The suite catches this defect class; the
negative control is not decorative.

**Additions re-run (remainder unit `addition:ai-l2`).** The core
was unchanged by the addition, so the same drill was re-run in
this tree against the enlarged suite: `_first_policy_match`
patched to `return None`, full suite run — **157 tests ran,
exactly 15 failed**: the original drill's 14 above plus exactly 1
from `test_additions.py` (the human-in-the-loop block case, which
asserts a `PolicyBlocked` the mutant cannot produce). `store.py`
was restored from `scratch/store.py.premutation_additions` and
verified SHA-256-identical to the shipped hash
(`4a2b74e4…e3f`); the suite re-ran green at **157 tests, OK**. Raw
output: `scratch/additions_mutation_run.txt`.

**Final GAPS batch (2026-11-07).** The batch unit added one new
module, `src/aigateway/extensions.py` (the core is byte-identical,
`store.py` still `4a2b74e4…e3f`), and `test_gaps_batch.py` (28
tests): **157 → 185 tests, OK**. Its fresh negative control is the
figure-inclusion seam, `AIGatewayExtensions._counts_toward_figures`
— the rule, mirroring the core's usage accounting, that every
stored request record counts toward the analytics figures derived
at read, blocked records included. `test_gaps_batch.py`'s
`TestFigureInclusionNegativeControl` carries the in-suite three-leg
form (canonical figures total 2 over one completed + one blocked
invocation; a completed-only mutant subclass totals 1 and
understates the token total; treating the mutant's total as the
canonical expectation raises `AssertionError`). The live drill was
performed on the real module: the seam's return line patched to
`return record["status"] == "completed"`, full suite run — **185
tests ran, exactly 5 failed**, all in `test_gaps_batch.py` (the
control's canonical and mutant-comparison legs, plus the three
analytics tests pinning blocked-inclusive figures: figures
coverage, actor scoping, dashboard freshness), with all 157
founding tests still passing. `extensions.py` was restored from
`scratch/extensions.py.premutation` and verified SHA-256-identical
(`2f7b9432…`); the suite re-ran green at **185 tests, OK**. Raw
output: `scratch/gaps_batch_mutation_run.txt`.

**Final GAPS batch, second unit (2026-11-07).** The unit added
one more new module, `src/aigateway/extensions_addition.py` (all
existing modules byte-identical, `store.py` still `4a2b74e4…e3f`,
the first unit's `extensions.py` still `2f7b9432…`), and
`test_gaps_batch_addition.py` (25 tests): **185 → 210 tests,
OK**. Its fresh negative control is the latest-record seam,
`AIGatewayExtensionsAddition._latest_record` — the rule that
every current-state derivation on the addition surface (a
twin's latest performance report, a plan step's current status,
a service's current lifecycle status) is the *last* record
reported for it. `test_gaps_batch_addition.py`'s
`TestLatestRecordNegativeControl` carries the in-suite
three-leg form (canonical views over two-report histories read
the second report everywhere; an earliest-reading mutant
subclass reads the first everywhere; treating the mutant's
current status as the canonical expectation raises
`AssertionError`). The live drill was performed on the real
module: the seam's return line patched to
`return records[0] if records else None` (occurrence count
asserted = 1 before patching), full suite run — **210 tests
ran, exactly 4 failed**, all in `test_gaps_batch_addition.py`
(the control's canonical leg, plus the twin-view,
transition-plan-view, and EIS-service-view tests that pin
latest derivations), with all 185 founding tests still passing.
`extensions_addition.py` was restored from
`scratch/extensions_addition.py.premutation` and verified
SHA-256-identical (`dcb741db…`); the suite re-ran green at
**210 tests, OK**. Raw output:
`scratch/gaps_batch_addition_mutation_run.txt`.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite follows the
shipped implementation's documented choices:

- `usage_for`'s `month` is the current UTC month as `YYYY-MM`, and
  usage aggregates the records' `total_tokens` for the effective
  owner (the key's owner when a key is used, else the actor).
- List endpoints over HTTP wrap their payload (`{"models": [...]}`,
  `{"templates": [...]}`, `{"keys": [...]}`, `{"requests": [...]}`,
  `{"sessions": [...]}`, `{"rules": [...]}`, `{"datasets": [...]}`),
  mirroring the sibling Collaboration build; `/audit` is pinned by
  the contract to `{"entries": [...]}`.
- Statuses the contract does not pin are 200: `POST /quotas`,
  `POST /models/{name}/versions/{v}/status`, and
  `DELETE /policy/rules/{id}`. Creation endpoints the contract does
  pin to 201 are asserted as 201.
- `run_eval` refuses a deprecated model with `ValidationError`, by
  the same "deprecated models refuse requests" rule the contract
  pins for the gateway (Core function 1); the contract does not
  state this case for eval explicitly.
- The service records `audit_read` before reading the entries, so a
  successful `GET /audit` response's trail includes that read itself.
- A plain string actor carries identity but no role (the sibling
  build's `_maybe_require` convention): role enforcement applies to
  User-like actors, which is what the service layer always passes.
