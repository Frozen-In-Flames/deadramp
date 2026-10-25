# Union Spec — Artificial Intelligence (AI), CMMC L2 (DeadRamp Phase 2, Group 9)

The merged functional spec for the ninth sibling group: **11 forks**,
category **Artificial Intelligence (AI)**, CMMC tier **L2** (every
member is FedRAMP **Moderate** in `forks.json` — verified, so the
group is single-tier and the merge takes the group baseline in full,
per Merge Rule 2). The member list in `forks.json` was reconciled
against `MAP.md`'s "Artificial Intelligence (AI) — L2 (11)" section:
**zero diffs** in both directions.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 11
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
all 11 descriptions were present in the cached dataset.

## How functions were counted

A fixed 16-function taxonomy for this category was matched against
each offering's own public description. A function is claimed for a
fork **only** when the description contains matching text; the
matching sentence is stored as the claim's evidence in the spec
sheet. All 11 offerings carry at least one tagged claim (45 claims
total), so no fork needed an invented function — but three forks
(AWS US East/West, CabletequeGov, Stell Requirements Management
System) carry exactly one claim each, and AWS's and Stell's
descriptions contain no AI-function text at all: they are a cloud
infrastructure listing and a requirements-management listing that
the marketplace files under this category, tagged here only on
multi-tenancy. Counts below are therefore a **floor**, not a
ceiling, on what these products do.

Wording-artifact judgments recorded by the extractor, kept visible
rather than silently cleaned up:

- **Asato — audit logging** rests on the single word "auditability"
  ("strong governance, auditability, and tenant isolation"). The
  audit core below does not rest on it: Aeroplicity ("audit
  logging", "Logs — audit logs"), Praxon Arc ("audit logging"),
  and Bidscale ("a clear audit trail") claim it explicitly.
- **Genesys — interaction records**: the matched sentence is
  "maintaining context, intent, and desired outcome" — conversational
  context-keeping inside a routing engine, not request/response
  records. The records core rests on Consus Gateway's operational-
  metadata sentence (below); Genesys's claim is a related but
  distinct one and is counted with that caveat.
- **Cableteque — agentic workflows** is plain "procurement
  automation" wording with no agentic or AI-agent language anywhere
  in the description; it matches only the broad automation arm of
  the pattern.
- **Genesys — evaluation records**: the first matched sentence is
  routing "evaluation and scoring methods"; the quality-review arm
  of the label is substantiated later in the same description
  ("quality management" in its workforce-engagement suite).
- **Consus — APIs & integrations**: the matched sentence is the
  gateway's own "single API endpoint" — its OpenAI-compatible API
  *is* its integration surface, counted as such.

## Function ranking — all 11 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Learned AI/ML inference (LLMs, ML, NLU, predictive models) | 8 | 73% | **Extended** — see the honesty note below; this is the group's largest family and it is deliberately *not* in the core |
| 2 | Multi-tenant architecture & tenant isolation | 6 | 55% | Platform note (the build is a single-tenant reference deployment; tenant isolation is a deployment-layer property, stated plainly) |
| 3 | Audit logging & trails | 4 | 36% | **Core** (L2 baseline hooks) |
| 4 | Agentic & automated workflow automation | 4 | 36% | Extended (domain automation engines that run on top of the platform; the agents themselves are inference) |
| 5 | Document processing & generation workflows | 4 | 36% | Extended (extraction and generation are inference workloads) |
| 6 | Open APIs & integrations | 3 | 27% | **Core** (the service is API-first) |
| 7 | Model gateway & request routing | 2 | 18% | **Core** (Consus Gateway, Praxon Arc) |
| 8 | Usage monitoring, metering & cost/budget controls | 2 | 18% | **Core** (Consus: token counts for billing; Praxon: usage monitoring, cost and budget controls) |
| 9 | Identity & access control | 2 | 18% | **Core** (L2 baseline hooks) |
| 10 | Request/response & interaction records, operational metadata | 2 | 18% | **Core** (Consus's operational-metadata sentence is the substrate's own spec; Genesys counted with the caveat above) |
| 11 | Evaluation records, scoring & quality review | 2 | 18% | **Core** (Bidscale: evaluation records and reports; Genesys: scoring and quality management) |
| 12 | Analytics, dashboards & reporting | 2 | 18% | Extended |
| 13 | Model governance & approved-model registry | 1 | 9% | **Core** (Praxon names "model governance" and "approved generative AI models" directly; the registry is also the substrate both gateway siblings presuppose — a request names a model, so the gateway must hold the model→responder mapping) |
| 14 | Configurable security guardrails / content policy | 1 | 9% | **Core** (Praxon: "configurable security guardrails" — the only configurable safety surface any sibling names; what is built is policy *plumbing*, rules evaluated on input and output, not a safety model) |
| 15 | Zero-persistence / ephemeral processing option | 1 | 9% | **Core** (Consus's stated architecture: content processed in ephemeral memory, "never written to disk, logged, or stored"; the only persistent records are operational metadata. Built as the records layer's zero-persistence mode) |
| 16 | Contact center & customer experience | 1 | 9% | Extended (Genesys's domain; a vertical application, not platform substrate) |

**The honesty note on row 1.** Learned inference is what most of
these products *sell*, and it is the one thing this build does not
and cannot contain: each vendor's models are their own proprietary
artifacts, and a Python-standard-library build has no learned
models. Claiming otherwise would be fabrication. What the siblings
genuinely share — and what two of them (Consus Gateway, Praxon Arc)
describe almost feature for feature — is the *platform layer around*
the models: a registry of approved models, a gateway that routes
requests to them, metering and budget controls, records, guardrail
hooks, evaluation plumbing, access control, and an audit log. That
layer is the core below. The gateway's responder is a deterministic
**reference stub** (echo, template, or rule-based behaviors),
labeled as a stub in every response it produces. Actual learned
inference is an Extended gap for the final batch, named as such.

**Differences are preserved, not averaged away**: the long tail
above (contact-center orchestration, document generation,
acquisition-support modules, manufacturing quality workflows,
compliance/ERP enclaves, IT asset management, requirements
management, cloud infrastructure) is the record of how the
siblings differ. Each Extended function names its claim family and
sibling count; the per-fork spec sheets name which siblings
claim it.

## The Core — what the merged build implements (10 functions)

One coherent AI-platform substrate that the gateway siblings
describe and every sibling's platform presupposes, built clean-room
from this spec:

1. **Model registry** — models as registered artifacts: name,
   version (auto-incrementing per name), provider label, capability
   tags, a responder behavior, and a status (`active` /
   `deprecated`; deprecated models refuse requests). This is the
   record Praxon's "approved generative AI models" and "model
   governance" name, and the mapping Consus's routing presupposes.
2. **Prompt template registry** — prompt templates as registered,
   versioned artifacts in the same registry pattern; a request may
   name a template, and the gateway renders the prompt through it
   (`{prompt}` substitution) before routing. Prompts are the
   first-class traffic of both gateway siblings' descriptions
   ("customer applications submit requests"; "prompt and response
   content are processed…"), so the registry covers them alongside
   models.
3. **Gateway & reference responder** — a request names a registered
   model and a prompt; the gateway routes it to that model's
   registered responder behavior and returns the response with
   usage figures. Responders are deterministic reference behaviors
   only — `echo` (returns the rendered prompt), `template` (fills
   the model's configured template), `rules` (first matching
   configured rule wins, else the configured default) — and every
   response carries `reference_stub: true` and a plain-language
   notice that the output is a stub, not a learned model.
4. **Usage metering & quotas** — every completed or blocked
   invocation is metered with a deterministic token estimator
   (stated as an estimator, ~1 token per 4 characters); per-owner
   monthly usage is queryable, and an administrator may set a
   per-owner monthly token quota (Consus's "token counts… used for
   billing, accountability"; Praxon's "cost and budget controls").
   A request whose prompt estimate would exceed the owner's quota
   is refused before it runs.
5. **Conversation & request records** — sessions group invocations
   into conversations with turns; every invocation leaves a request
   record (model, actor, key, token counts, status, timestamps —
   Consus's operational metadata, almost verbatim). A store-wide
   **zero-persistence mode** (Consus's architecture) withholds
   prompt/response content from all records, keeping metadata only.
6. **Policy guardrails (hooks)** — an ordered, configurable rule
   list (term substrings or regex patterns, scoped to input,
   output, or both) evaluated on every invocation's prompt and
   output. A match blocks the invocation, stores a blocked request
   record, and is audited. This is policy plumbing — the
   *configurable* surface Praxon names — not a safety model, and
   the build says so.
7. **Evaluation harness** — named datasets of cases (prompt,
   expected, match rule: exact or contains, plus optional rubric
   criteria as named substring checks); a run exercises a
   registered model's responder over a dataset and records per-case
   results and an aggregate score. The plumbing Bidscale's
   "evaluation records… generate evaluation reports with a clear
   audit trail" presupposes. Eval runs exercise the responder
   directly — they are recorded as eval runs, are not metered as
   gateway traffic, and (being operator-supplied test data) are
   stored by design even in zero-persistence mode.
8. **API access** — every function above is exposed over a REST API
   (JSON). The invocation endpoint is OpenAI-*flavored* (a model
   name and a prompt in, a completion-shaped response out) because
   both gateway siblings advertise OpenAI-compatible surfaces; it
   is this build's own API, not OpenAI's.
9. **Access control & API keys** — role-based access hooks
   (platform roles `admin`, `member`, `viewer` with a permission
   matrix enforced on every operation) plus registered API keys:
   a key has an owner and an id (Consus's "API key identifier");
   only its SHA-256 digest is stored, the secret is shown once at
   creation, and invocations may be attributed to a key for
   metering.
10. **Audit log** — an append-only audit trail: every registry,
    key, quota, policy, session, invocation, and evaluation
    mutation, every policy block, and (at the HTTP layer) every
    denied attempt is recorded with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of NIST SP 800-171 Rev. 2 that define CMMC L2. All 11
  parent forks sit at Moderate, so the union baseline is the
  Moderate baseline, un-diluted (Merge Rule 1) and inherited in
  full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + API-key registry) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; API-key secrets are stored only as SHA-256 digests,
    IA-5-flavored authenticator hygiene; the service ships hooks,
    not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, admin-only read).
  - Gateway, records, metering, policy, evaluation → **SI** (SI-10
    information input validation — malformed input is rejected,
    never partially applied; SI-4-flavored usage monitoring via
    the metering records) and **SC** (SC-8 transmission
    confidentiality — the server runs over TLS when a certificate
    is configured; encryption at rest is a deployment-layer
    control, stated plainly, not claimed here).
  - Zero-persistence mode → **SC**/**SI** data-minimization flavor:
    content is never written to any record; only operational
    metadata persists, per Consus's own stated architecture.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. It also confers no AI capability claim: the
  registry, gateway, and harness are platform plumbing around
  models this build does not contain.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `aigateway` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`mdl-`, `tpl-`,
`key-`, `ses-`, `req-`, `evd-`, `evr-`, `rule-`); a failed operation
consumes no id and changes nothing. All timestamps are UTC
ISO-8601. The token estimator is pinned: `estimate_tokens(text)`
is `0` for an empty string, else `(len(text) + 3) // 4`.

- `aigateway/errors.py` — `AIGatewayError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`, `QuotaExceeded`,
  `PolicyBlocked` (all deriving from `AIGatewayError`).
- `aigateway/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `read, registry_write, invoke,
  eval_run, usage_read, policy_write, audit_read, admin`.
  `PERMISSIONS`: admin ⊇ all eight; member = {read, registry_write,
  invoke, eval_run, usage_read}; viewer = {read, usage_read}.
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`.
- `aigateway/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)`; `.entries()` returns entry dicts
  with keys `ts, actor, action, target, details`. Append-only;
  optional JSONL file persistence; reloads an existing file on
  construction.
- `aigateway/store.py` — `AIGatewayStore(audit=None,
  zero_persistence=False)`, and the module constant
  `REFERENCE_NOTICE` = "Reference responder: deterministic stub
  output. This build contains no learned model; output is produced
  by the registered responder behavior (echo, template, or
  rules)." The store records every successful mutation, every
  completed invocation, and every policy block to its audit log
  (when one is attached) with the action names below; the HTTP
  layer records denials and `audit_read` only, never duplicating
  store records. Methods:
  - `register_model(name, responder, actor, version=None,
    provider="", capabilities=None, config=None)` (action
    `registry_write`) → `{id, name, version, provider, responder,
    capabilities, config, status, created_by, created_utc}` with
    `status` starting `"active"`. `responder` must be one of
    `echo|template|rules`, else `ValidationError`. `version`: when
    omitted, the next integer for that name (1 for the first);
    an explicit duplicate (name, version) raises
    `ValidationError`. Config validation: `template` requires
    `config["template"]` to be a string; `rules` requires
    `config["rules"]` to be a list of `{match, response}` string
    pairs and `config["default"]` to be a string. Audits
    `model_register`.
  - `get_model(name, actor, version=None)` (action `read`) → the
    model dict; `version=None` selects the highest version;
    `NotFoundError` if absent. `list_models(actor)` → all model
    dicts sorted by (name, version).
  - `set_model_status(name, version, status, actor)` (action
    `registry_write`) → updated model dict; `status` must be
    `active|deprecated`, else `ValidationError`. Audits
    `model_status`.
  - `register_template(name, text, actor, version=None)` (action
    `registry_write`) → `{id, name, version, text, created_by,
    created_utc}`; version rules as for models. Rendering: if the
    text contains `{prompt}`, the prompt replaces it; otherwise
    the template text is used as-is. Audits `template_register`.
    `get_template(name, actor, version=None)`, `list_templates(
    actor)` as for models.
  - `create_api_key(owner, actor)` (action `registry_write`; the
    actor must be the owner themself or a platform admin, else
    `PermissionDenied`) → `{id, owner, secret, created_by,
    created_utc}`. The `secret` is returned **only** here; the
    store keeps `secret_hash` (SHA-256 hex of the secret) and no
    other copy. Audits `key_create` (the secret is never audited).
  - `authenticate_key(secret)` → the owner's name, or `None`.
    Not audited.
  - `list_api_keys(actor)` (action `read`) → key dicts **without**
    `secret` or `secret_hash`: `{id, owner, created_by,
    created_utc}`. A non-admin actor sees only their own keys.
  - `set_quota(owner, token_limit, actor)` (action `admin`) →
    `{owner, token_limit, updated_utc}`; `token_limit` must be a
    positive integer, else `ValidationError`. One quota per owner;
    setting replaces. Audits `quota_set`.
  - `get_quota(owner, actor)` (action `usage_read`; actor must be
    the owner or a platform admin, else `PermissionDenied`) → the
    quota dict, or `None`.
  - `usage_for(owner, actor)` (action `usage_read`; owner-or-admin
    as above) → `{owner, month, prompt_tokens, completion_tokens,
    total_tokens, requests}` aggregated over the current UTC
    month's request records, including blocked ones (blocked
    records carry the usage stated under `invoke`).
  - `create_session(title, actor)` (action `invoke`) → `{id,
    owner, title, turns, created_utc}` with `turns` starting
    empty. Audits `session_create`. `get_session(session_id,
    actor)` (action `read`; owner or platform admin, else
    `PermissionDenied`); `list_sessions(actor)` → the actor's own
    sessions (admin: all), chronological.
  - `invoke(model_name, prompt, actor, version=None, key_id=None,
    session_id=None, template_name=None, template_version=None)`
    (action `invoke`) → the request dict `{id, model,
    model_version, session_id, actor, key_id, prompt, output,
    reference_stub, responder, notice, usage, status,
    created_utc}`, where `reference_stub` is `True`, `notice` is
    `REFERENCE_NOTICE`, `usage` is `{prompt_tokens,
    completion_tokens, total_tokens}`, and `status` is
    `"completed"` for a stored completion. Steps, in order:
    1. Resolve the model (`NotFoundError`); a `deprecated` model
       raises `ValidationError`.
    2. If `key_id` is given: the key must exist (`NotFoundError`)
       and belong to the actor, unless the actor is a platform
       admin (`PermissionDenied`).
    3. If `session_id` is given: the session must exist
       (`NotFoundError`) and belong to the actor or an admin
       (`PermissionDenied`).
    4. If `template_name` is given: render the prompt through the
       template (the rendered text is the effective prompt
       everywhere below, including metering and records).
    5. Quota pre-check: the quota owner is the key's owner when
       `key_id` is given, else the actor. If that owner has a
       quota and current-month usage plus `estimate_tokens(
       effective prompt)` would exceed it, raise `QuotaExceeded`
       — nothing is stored and no responder runs.
    6. Input policy check: if any applicable rule matches the
       effective prompt, store a request record with `status`
       `"blocked_input"`, `output` `None`, usage
       `{prompt_tokens: estimate, completion_tokens: 0,
       total_tokens: estimate}`, audit `invoke_blocked` with
       details `{stage: "input", rule_id}`, and raise
       `PolicyBlocked`.
    7. Run the responder: `echo` → the effective prompt;
       `template` → the model's `config["template"]` with
       `{prompt}` replaced by the effective prompt (used as-is if
       no placeholder); `rules` → the first rule whose `match` is
       a case-insensitive substring of the effective prompt wins,
       else `config["default"]`.
    8. Output policy check: if any applicable rule matches the
       output, store the record with `status` `"blocked_output"`,
       `output` `None`, usage estimated over both prompt and the
       (withheld) output, audit `invoke_blocked` with details
       `{stage: "output", rule_id}`, and raise `PolicyBlocked`.
    9. Otherwise store the record with `status` `"completed"`,
       append a turn `{request_id, prompt, output, created_utc}`
       to the session if one was given, audit `invoke` with
       details `{model, total_tokens}`, and return the record.
    In **zero-persistence mode**, stored records and session turns
    carry `prompt`/`output` as `None` and an extra key
    `content_withheld: True`; metadata (ids, model, actor, key,
    usage, status, timestamps) is stored in full. Blocked records
    never append session turns. A `PolicyBlocked` exception
    carries the stored record's id as its `request_id` attribute.
  - `get_request(request_id, actor)` (action `read`; the
    invocation's actor or a platform admin, else
    `PermissionDenied`). `list_requests(actor, session_id=None)`
    → the actor's own request records (admin: all),
    chronological, optionally filtered to one session.
  - `add_rule(scope, kind, value, actor)` (action `policy_write`)
    → `{id, scope, kind, value, created_by, created_utc}`;
    `scope` must be `input|output|both`, `kind` must be
    `term|pattern`, else `ValidationError`; a `pattern` value
    must compile as a regex, else `ValidationError`. A `term`
    rule matches as a case-insensitive substring; a `pattern`
    rule matches via regex search. Rules evaluate in creation
    order; the first match blocks. Audits `policy_add`.
    `remove_rule(rule_id, actor)` (action `policy_write`) →
    the removed dict; audits `policy_remove`. `list_rules(actor)`
    (action `read`) → rules in creation order.
  - `create_eval_dataset(name, cases, actor)` (action `eval_run`)
    → `{id, name, cases, created_by, created_utc}`; `cases` must
    be a non-empty list of dicts with string `prompt` and
    `expected`, optional `match` (`exact|contains`, default
    `exact`; anything else → `ValidationError`), and optional
    `rubric`, a dict of criterion name → expected substring.
    Stored cases gain sequential `case_id`s (`case-1`, …).
    Audits `eval_dataset_create`. `get_eval_dataset(dataset_id,
    actor)`, `list_eval_datasets(actor)` (action `read`).
  - `run_eval(dataset_id, model_name, actor, version=None)`
    (action `eval_run`) → `{id, dataset_id, model, model_version,
    results, passed, total, score, created_by, created_utc}`;
    each result is `{case_id, prompt, expected, output, passed,
    rubric_results}`. The responder runs directly (no quota, no
    policy, no metering, no request record). Scoring: `exact` →
    `output.strip() == expected.strip()`; `contains` →
    `expected.lower() in output.lower()`; each rubric criterion
    passes iff its substring appears in the output
    (case-insensitive); a case passes iff its match passes **and**
    every rubric criterion passes. `score` is `passed / total`
    as a float. Audits `eval_run`. `get_eval_run(run_id, actor)`
    (action `read`; the run's creator or a platform admin).
- `aigateway/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match
  the registry; unknown user or mismatched role → 401). Errors are
  JSON `{error}` with statuses: `ValidationError` 400, unknown
  user / role mismatch 401, `PermissionDenied` 403, `NotFoundError`
  404, `PolicyBlocked` 422, `QuotaExceeded` 429. Denied attempts
  (401, 403, 422, 429) are audited with the route's action name
  suffixed `:denied`, and no stack trace is ever returned.
  Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /models` (read); `POST /models` `{name, responder,
    version?, provider?, capabilities?, config?}`
    (registry_write) → 201; `GET /models/{name}` (read) → latest
    version; `GET /models/{name}/versions/{v}` (read);
    `POST /models/{name}/versions/{v}/status` `{status}`
    (registry_write)
  - `GET /templates` (read); `POST /templates` `{name, text,
    version?}` (registry_write) → 201
  - `GET /keys` (read; store scopes the list); `POST /keys`
    `{owner}` (registry_write) → 201, returns the secret once
  - `POST /quotas` `{owner, token_limit}` (admin); `GET
    /usage/{owner}` (usage_read)
  - `POST /v1/completions` `{model, prompt, version?, key_id?,
    session_id?, template?}` (invoke) → 201, the request dict
  - `GET /requests` (read); `GET /requests/{id}` (read)
  - `GET /sessions` (read); `POST /sessions` `{title}` (invoke)
    → 201; `GET /sessions/{id}` (read)
  - `GET /policy/rules` (read); `POST /policy/rules` `{scope,
    kind, value}` (policy_write) → 201; `DELETE
    /policy/rules/{id}` (policy_write)
  - `GET /eval/datasets` (read); `POST /eval/datasets` `{name,
    cases}` (eval_run) → 201; `POST /eval/datasets/{id}/runs`
    `{model, version?}` (eval_run) → 201, the run dict; `GET
    /eval/runs/{id}` (read)
  - `GET /audit` (audit_read) → `{"entries": [...]}`
- `aigateway/__main__.py` — `python -m aigateway serve --host
  --port [--audit-log PATH] [--zero-persistence] [--certfile
  --keyfile]` with demo users `alice=admin, bob=member,
  carol=viewer` (documented as demo identities; production
  identity is the embedding organization's, per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim it traces to, and include a
**negative control**: a mutant policy check (one that treats every
text as clean) whose behavior the canonical expectation is shown
to reject — a prompt containing a blocked term must raise
`PolicyBlocked` and store a `blocked_input` record, and the mutant
is demonstrated to wave it through — proving the suite catches
that defect class rather than merely passing. The negative
control must additionally be **mutation-verified**: patching the
real policy evaluation in `src/` with the mutant must make the
suite fail; the run and its result are recorded in
`tests/README.md`.

## Coverage statement (for this build)

- Specs: 11 / 11 forks spec'd.
- Core: 10 core functions implemented, each with tracing tests.
- Extended: 6 functions specified and ranked, **not** implemented
  in this build (learned AI/ML inference — the group's #1 family
  and the final batch's largest single item; agentic & automated
  workflow engines; document processing & generation; analytics,
  dashboards & reporting; contact center & customer experience;
  and the siblings' vertical domain applications, named in the
  ranking notes); multi-tenancy is a platform note (single-tenant
  reference deployment; tenant isolation is a deployment-layer
  property) and encryption is a platform note (TLS when a
  certificate is configured; at rest is a deployment-layer
  control).
