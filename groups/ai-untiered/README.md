# Artificial Intelligence (AI) — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **9 untiered forks** of Artificial
Intelligence (AI) — census unit `untiered:Artificial Intelligence
(AI)` in `../../remainder.json`, an untiered set built under the
remainder pipeline. **This is an untiered set, and that means
something specific:** every member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no
baseline for these offerings, so **tier stays null**: no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The union
contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests.

The 9 forks were spec'd under the category's existing
16-function taxonomy **verbatim** (AST-parsed out of the founding
group's extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding AI L2 group's current
shipped claim tables exactly — **12 of 12 forks, 47 of 47
claims, deep-equal on ids and evidence** (the original 11 plus
the Gobo remainder addition) — before tagging this set. Result
here: **13 claims** across the set (14 raw hits, 1 removed in the
exclusion pass), **7 of 9 forks claiming at least one**; the two
zero-claim forks (Bland, Lemma) are recorded under Named
absences in the union spec, not hidden or repaired. The set's
headline wording finding: Claude, the flagship LLM offering,
claims **no** `learned_inference` under the verbatim taxonomy —
its prose says "AI assistant" and bare "natural language", which
fire none of the family's phrases — and ElevenLabs claims none
either ("AI-produced" is not an adjective arm). The taxonomy was
not re-tuned for either.

The build implements the category's **ten-function substrate** —
the platform layer around models that the founding siblings
describe — carried **byte-identical** from the founding AI L2
build (`../ai-l2/src/aigateway/`, 7 of 7 modules; SHA-256
accounting below). The substrate is tier-independent platform
code: the founding source contains no tier or baseline machinery,
so there was nothing tier-shaped to strip. Where the founding
contract's text says "L2 baseline hooks" for access control and
audit, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline. The gateway's
responder is a deterministic **reference stub**, labeled
`reference_stub: true` in every response — this build contains
no learned model (see Honesty).

## The 9 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2633053633 | Anthropic | Claude | 2 |
| FR2633153276 | Anyreach, Inc. | Anyreach App Software Application | 3 |
| FR2632558748 | Baseten Labs, Inc. | Baseten Inference Platform | 1 |
| FR2632054530 | Beam Up Ltd | Beam | 1 |
| FR2628647242 | Bland AI | Bland | 0 |
| FR2700137035 | Caldera AI Inc. | Mesa | 1 |
| FR2628647238 | Eleven Labs Inc. | ElevenLabs Platform | 2 |
| FR2634659079 | ThinkTrends LLC | ThinkTrends AI Platform | 3 |
| FR2632054534 | Thread AI, Inc. | Lemma (GovCloud) | 0 |

In `forks.json` the set is as filed: 8 forks carry the Artificial
Intelligence (AI) category and 1 (ThinkTrends) is filed under
Analytics; the census assigned all 9 to this category from their
own descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span FedRAMP Certified (2:
Bland, ElevenLabs) and Initial Implementation (7) — a status is
record data, not a claim.

## The 10 core functions

1. **Model registry** — models as registered artifacts: name,
   version (auto-incrementing per name), provider label,
   capability tags, a responder behavior (`echo` / `template` /
   `rules`), and a status (`active` / `deprecated`; deprecated
   models refuse requests).
2. **Prompt template registry** — prompt templates as registered,
   versioned artifacts in the same registry pattern; a request
   may name a template, and the gateway renders the prompt
   through it (`{prompt}` substitution) before routing.
3. **Gateway & reference responder** — a request names a
   registered model and a prompt; the gateway routes it through
   the pinned 9-step `invoke()` flow to that model's registered
   responder behavior and returns the response with usage
   figures. The responder is a deterministic **reference stub**
   only, labeled `reference_stub: true` with the pinned
   `REFERENCE_NOTICE` text in every response (see Honesty).
4. **Usage metering & quotas** — every completed or blocked
   invocation is metered with the pinned deterministic estimator
   `estimate_tokens(text)` (`0` for empty, else `(len(text)+3)//4`,
   an estimator at ~1 token per 4 characters); per-owner monthly
   usage is queryable, and an administrator may set a per-owner
   monthly token quota. A request whose prompt estimate would
   exceed the owner's quota is refused before it runs.
5. **Conversation & request records** — sessions group
   invocations into conversations with turns; every invocation
   leaves a request record (model, actor, key, token counts,
   status, timestamps). A store-wide **zero-persistence mode**
   withholds prompt/response content from all records and turns
   (`content_withheld: true`), keeping operational metadata only.
6. **Policy guardrails (hooks)** — an ordered, configurable rule
   list (term substrings or regex patterns, scoped to input,
   output, or both) evaluated on every invocation's prompt and
   output. A match blocks the invocation, stores a blocked
   request record, and is audited. This is policy plumbing, not a
   safety model.
7. **Evaluation harness** — named datasets of cases (prompt,
   expected, match rule: exact or contains, plus optional rubric
   criteria as named substring checks); a run exercises a
   registered model's responder directly over a dataset (no
   quota, no policy, no metering, no request record) and records
   per-case results and an aggregate score.
8. **API access** — every function above is exposed over a REST
   API (JSON). The invocation endpoint is OpenAI-*flavored* (a
   model name and a prompt in, a completion-shaped response out);
   it is this build's own API, not OpenAI's.
9. **Access control & API keys** — role-based access hooks
   (platform roles `admin`, `member`, `viewer` with a permission
   matrix enforced on every operation) plus registered API keys:
   a key has an owner and an id; only its SHA-256 digest is
   stored, the secret is shown once at creation, and invocations
   may be attributed to a key for metering.
10. **Audit log** — an append-only audit trail: every registry,
    key, quota, policy, session, invocation, and evaluation
    mutation, every policy block, and (at the HTTP layer) every
    denied attempt is recorded with actor, action, target, and
    UTC timestamp. Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed — a *blocked* invocation is the pinned exception: it
stores its blocked record by design). Ids are sequential per
object type: `mdl-`, `tpl-`, `key-`, `ses-`, `req-`, `evd-`,
`evr-`, `rule-`.

Three of the ten functions are claim-supported by at least one
fork in this set under the category's standing dispositions (the
audit log by `audit_logging`, 2 forks; access control by
`access_control`, 1 fork; the policy hooks by `guardrails`, 1
fork). The other seven are **carried, not claimed** in this set —
see `UNION-SPEC.md` for the core-boundary decision. No function
is claimed to be *attained* by any fork — the build is the merged
open implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m aigateway serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--zero-persistence` (withhold prompt/response content from all
records; metadata only), and `--certfile FILE --keyfile FILE` to
serve over TLS (standard library `ssl`). A startup line is
printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, registry_write, invoke, eval_run, usage_read, policy_write, audit_read, admin (all eight) |
| `bob`   | member  | read, registry_write, invoke, eval_run, usage_read |
| `carol` | viewer  | read, usage_read |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404; a
policy-blocked invocation gets 422; a quota-exceeded invocation
gets 429. Denied attempts (401, 403, 422, 429) are audited by the
HTTP layer with the route's action name suffixed `:denied`.
Errors are always JSON `{"error": "..."}` and no stack trace is
ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/models` | read | List models → `{"models": [...]}` |
| POST | `/models` | registry_write | Body `{name, responder, version?, provider?, capabilities?, config?}` → 201 model dict |
| GET | `/models/{name}` | read | Latest version of one model |
| GET | `/models/{name}/versions/{v}` | read | One specific model version |
| POST | `/models/{name}/versions/{v}/status` | registry_write | Body `{status}` → updated model dict |
| GET | `/templates` | read | List prompt templates → `{"templates": [...]}` |
| POST | `/templates` | registry_write | Body `{name, text, version?}` → 201 template dict |
| GET | `/keys` | read (store scopes the list) | List API keys (no secret material) → `{"keys": [...]}` |
| POST | `/keys` | registry_write | Body `{owner}` → 201, returns the secret **once** |
| POST | `/quotas` | admin | Body `{owner, token_limit}` → quota dict |
| GET | `/usage/{owner}` | usage_read (owner or admin) | Current-month usage aggregate for the owner |
| POST | `/v1/completions` | invoke | Body `{model, prompt, version?, key_id?, session_id?, template?}` → 201, the request dict (labeled reference stub) |
| GET | `/requests` | read | The caller's request records → `{"requests": [...]}` (optional `?session_id=`) |
| GET | `/requests/{id}` | read | One request record (its actor or an admin) |
| GET | `/sessions` | read | The caller's sessions → `{"sessions": [...]}` |
| POST | `/sessions` | invoke | Body `{title}` → 201 session dict |
| GET | `/sessions/{id}` | read | One session (its owner or an admin) |
| GET | `/policy/rules` | read | List policy rules in creation order → `{"rules": [...]}` |
| POST | `/policy/rules` | policy_write | Body `{scope, kind, value}` → 201 rule dict |
| DELETE | `/policy/rules/{id}` | policy_write | → the removed rule dict |
| GET | `/eval/datasets` | read | List evaluation datasets → `{"datasets": [...]}` |
| POST | `/eval/datasets` | eval_run | Body `{name, cases}` → 201 dataset dict |
| POST | `/eval/datasets/{id}/runs` | eval_run | Body `{model, version?}` → 201, the run dict |
| GET | `/eval/runs/{id}` | read | One evaluation run (its creator or an admin) |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Request dicts are `{id, model, model_version, session_id, actor,
key_id, prompt, output, reference_stub, responder, notice, usage,
status, created_utc}` with sequential ids `req-1`, `req-2`, …;
the other object types follow the same pattern with their own
prefixes (see `UNION-SPEC.md` for every dict shape). In
zero-persistence mode a record additionally carries
`content_withheld: true` and its `prompt`/`output` are `None`.

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**159 tests, OK** at delivery: the founding group's 146-test
core suite carried with the code (its additions module, which
pins a different census unit, not carried), plus 13 spec tests
pinning this set (exactly 9 sheets; membership exact against
`remainder.json`; every sheet's tier null / impact "Unknown";
every claim's evidence verbatim under the founding normalization
or its truncated form; 13 claims total with exactly two
zero-claim forks; the removed Bland hit absent; the headline
near-misses unclaimed). The category's signature policy-match
mutation drill was re-run in this tree — exactly 14 failures
under the mutant, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/aigateway/` is carried from the founding group
`../ai-l2/src/aigateway/` — **7 of 7 modules byte-identical**,
SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `3adc6a53a6d4673ab67626d0ddd5145581b3a33fb2f0c6e6722983e2e5c9cac0` |
| `__main__.py` | `e9c396d154ccbdb0538f144257a93853c144e6993fd91af90a711388006820df` |
| `access.py` | `66d1b81f3671fa29d74a91a188384b1b119bbc90e6898ac28909e0ce9df69c6d` |
| `audit.py` | `2400fc9b3381ef4f669c40983887a1ffd8c20b9980c813d133bf8e0050b484a1` |
| `errors.py` | `204a072c3f38f033f30d5332e7b641ab127ddf14395f2cedb80c7f17655896cc` |
| `service.py` | `9e20dda415c512a21078649d9fec501db5e2135990467b0289a2e28e3d1be2d9` |
| `store.py` | `4a2b74e47fffd731b0bf92dbb1266bf87f0641ee22601bb143a1f3d6807b0e3f` |

The test suite is likewise carried (the founding suite minus its
additions module), with one labeling fix in
`tests/aigateway_helpers.py` (its docstring now names this
untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 9 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under the
taxonomy families that carry control language. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

Documented by at least one fork in the set:

- **Audit & accountability (AU)** — 2 forks, via
  `audit_logging`: Anthropic Claude ("audit controls" across all
  interfaces, at administration-surface weight), ElevenLabs
  Platform ("only system and audit data is persisted" under Zero
  Retention Mode, at ZRM-persistence weight).
- **Access control (AC), with identity & access management
  language (IA)** — 1 fork, via `access_control`: ElevenLabs
  Platform ("a common identity and access management layer").
- **Content policy / guardrail configuration** — 1 fork, via
  `guardrails`: ThinkTrends AI Platform ("Configurable content
  safety guardrails (HIPAA, PII, tone, compliance policies)").
  A configurable policy surface in the fork's own words — not a
  safety-model claim, for the fork or for this build.
- **Platform architecture assertion (not a control family)** —
  1 fork, via `multi_tenancy`: Caldera Mesa ("a multi-tenant
  software-as-a-service application" — multi-tenancy only, no
  isolation language, documented at exactly that weight).

**Not documented** by any fork in this set: model governance (no
`model_governance` claim — ThinkTrends' "Agentic Governance" is
evaluation-jobs substance), usage monitoring (Baseten's
per-token billing lives only in its `certified_services` record
field, never matched), zero-persistence (ElevenLabs' Zero
Retention Mode is retention phrasing, not the family), and every
other NIST SP 800-53 control family — including AT, CA, CM, CP,
IR, MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI beyond the
guardrail policy language above. If the source later publishes
an impact level for any of these offerings, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented control
  language is recorded as *its* claim, never as the build's
  control attainment.
- **The reference responder is a stub, and this build contains
  no learned model.** Its three behaviors are deterministic
  rules over the prompt text: `echo` returns the rendered
  prompt, `template` fills the model's configured template, and
  `rules` returns the first matching configured rule's response
  (else the configured default). Every response it produces is
  labeled `reference_stub: true` and carries a plain-language
  notice saying exactly that. Nothing resembling inference
  executes here; there is no learned "AI" behavior of any kind.
- **Extended functions are specified, not implemented.** The
  union spec ranks 16 functions; the substrate behind 10 is
  implemented here. NOT implemented (claimant counts are this
  set's): learned AI/ML inference — the models themselves (4
  claimants, and the set's two most prominent inference
  products, Claude and ElevenLabs, enlarge the same gap at zero
  claims); agentic & automated workflow execution engines (3);
  voice & speech AI engines (described in substance by Bland,
  ElevenLabs, and Beam); model serving & inference
  infrastructure (Baseten); document understanding,
  summarization & report generation (Beam, Mesa, ThinkTrends
  substance at zero family claims); knowledge-base / retrieval
  engines (ThinkTrends, Mesa); evaluation & benchmarking engines
  (ThinkTrends substance); vertical workflow applications —
  public-records processing (Mesa), human-services case
  workflows (Beam), constituent-service contact-center workflows
  (Anyreach, the set's one `contact_center` claim).
- **Multi-tenancy is a platform note, not a core function here:**
  this build is a single-tenant reference deployment; tenant
  isolation is a deployment-layer property, stated plainly, and
  not claimed here — Mesa's multi-tenancy assertion is its own
  documented claim, not this build's.
- **Encryption is a platform note, not a core function here:**
  the server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated
  plainly, and not claimed here. FIPS-validated crypto (SC-13)
  is not claimed by the build.
- The policy guardrails are **policy plumbing, not a safety
  model**: a configurable rule list evaluated on input and
  output, nothing more, and the build says so.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own. Production identity belongs to the
  embedding organization (IA-2 stays with it).
- **Named absences stand.** Nine of the 16 families have 0
  claimants in this set (`model_gateway`, `model_governance`,
  `usage_metering`, `interaction_records`, `zero_persistence`,
  `evaluation_records`, `api_integration`,
  `document_automation`, `analytics_reporting`); Bland and Lemma
  claim nothing at all. Nothing was back-filled to make the set
  look complete, and no fork was reclassified out of the set for
  describing a non-AI operational surface — classification is the
  census's, claims are the text's.
