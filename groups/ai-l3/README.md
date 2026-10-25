# Artificial Intelligence (AI) L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 22)

This is the merged, clean-room implementation of the **Artificial
Intelligence (AI) L3-adjacent** sibling group: forks from the FedRAMP
Marketplace that share the same category (Artificial Intelligence)
and the same trust tier (CMMC L3-adjacent, equivalent to FedRAMP
**High**), built as one open-source service per the group's union
spec, [`UNION-SPEC.md`](UNION-SPEC.md).

## Lineage and reuse (read this first)

This build is a **cross-tier merge** under Operation DeadRamp's Merge
Rule. One parent is the shipped Group 9 build
([`../ai-l2/`](../ai-l2/)), itself the union of the 11 Artificial
Intelligence L2 (FedRAMP Moderate) forks. The other parent is this
group's High-tier forks. The merge takes the union of the baselines
and inherits the **highest tier in full** — so this tree is Group 9's
service, **uplifted to the FedRAMP High baseline**, extended by this
group's spec sheets.

Reuse is explicit, and was computed, not asserted: Group 9's code is
our own (Apache-2.0). Of the seven `aigateway` modules, **one is
byte-identical to Group 9** (`__init__.py`) and **six carry the High
uplifts** (`audit.py`, `access.py`, `errors.py`, `store.py`,
`service.py`, `__main__.py`) — verified with `cmp`/SHA-256 against
`../ai-l2/src/aigateway/`. No vendor code, assets, or branding from
any sibling offering is used. Python 3, **standard library only**,
no external dependencies.

What the siblings genuinely share is the *platform layer around*
models: a registry of approved models, a gateway that routes
requests to them, metering and budget controls, records, guardrail
hooks, evaluation plumbing, access control, and an audit log. That
layer is what is built here. See the honesty section below for what
is **not** built, starting with the models themselves.

## The 10 core functions (at the High baseline)

1. **Model registry** — models as registered artifacts: name,
   version (auto-incrementing per name), provider label, capability
   tags, a responder behavior (`echo` / `template` / `rules`), and a
   status (`active` / `deprecated`; deprecated models refuse
   requests).
2. **Prompt template registry** — prompt templates as registered,
   versioned artifacts in the same registry pattern; a request may
   name a template, and the gateway renders the prompt through it
   (`{prompt}` substitution) before routing.
3. **Gateway & reference responder** — a request names a registered
   model and a prompt; the gateway routes it through the pinned
   9-step `invoke()` flow to that model's registered responder
   behavior and returns the response with usage figures. The
   responder is a deterministic **reference stub** only, labeled
   `reference_stub: true` with the pinned `REFERENCE_NOTICE` text in
   every response (see Honesty).
4. **Usage metering & quotas** — every completed or blocked
   invocation is metered with the pinned deterministic estimator
   `estimate_tokens(text)` (`0` for empty, else `(len(text)+3)//4`,
   an estimator at ~1 token per 4 characters); per-owner monthly
   usage is queryable, and an administrator may set a per-owner
   monthly token quota. A request whose prompt estimate would exceed
   the owner's quota is refused before it runs.
5. **Conversation & request records** — sessions group invocations
   into conversations with turns; every invocation leaves a request
   record (model, actor, key, token counts, status, timestamps). A
   store-wide **zero-persistence mode** withholds prompt/response
   content from all records and turns (`content_withheld: true`),
   keeping operational metadata only.
6. **Policy guardrails (hooks)** — an ordered, configurable rule
   list (term substrings or regex patterns, scoped to input, output,
   or both) evaluated on every invocation's prompt and output. A
   match blocks the invocation, stores a blocked request record, and
   is audited. This is policy plumbing, not a safety model.
7. **Evaluation harness** — named datasets of cases (prompt,
   expected, match rule: exact or contains, plus optional rubric
   criteria as named substring checks); a run exercises a registered
   model's responder directly over a dataset (no quota, no policy,
   no metering, no request record) and records per-case results and
   an aggregate score.
8. **API access** — every function above is exposed over a REST API
   (JSON). The invocation endpoint is OpenAI-*flavored* (a model
   name and a prompt in, a completion-shaped response out); it is
   this build's own API, not OpenAI's.
9. **Access control & API keys** — role-based access hooks (platform
   roles `admin`, `member`, `viewer`, plus the High-baseline
   `auditor` role, with a permission matrix enforced on every
   operation and unsuccessful-logon lockout at the service layer)
   plus registered API keys: a key has an owner and an id; only its
   SHA-256 digest is stored, the secret is shown once at creation,
   and invocations may be attributed to a key for metering.
10. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail: every registry, key, quota, policy, session,
    invocation, and evaluation mutation, every policy block, and (at
    the HTTP layer) every denied attempt is recorded with actor,
    action, target, and UTC timestamp. Optional JSONL file
    persistence.

## What the High baseline added (the uplifts)

- **Hash-chained audit (AU-9, AU-3)** — each entry carries `seq`
  (0-based), `prev_hash`, and `hash` (SHA-256 of the canonical JSON
  of `{seq, ts, actor, action, target, details, prev_hash}`; genesis
  `prev_hash` is `"0" * 64`). `AuditLog.verify_chain()` recomputes
  the chain and localizes the first tampered entry at its exact
  index; `GET /audit/verify` exposes it over HTTP. JSONL persistence
  preserves the chain fields across reload.
- **Fail-closed audit writes (AU-5)** — if the audit file write
  fails, the operation fails with it: `AuditLog.record` rolls back
  the in-memory append and raises `AuditWriteError`, and the store
  rolls the whole operation back (no object created, no id
  consumed, no state moved). The service never proceeds unaudited.
- **Audit search & reduction (AU-7)** — `GET /audit` accepts
  `actor`, `action`, `target`, `since`, and `until` filter
  parameters, passed through to `AuditLog.query`.
- **Logon lockout (AC-7)** — consecutive authentication failures are
  tracked per username; at the threshold (default 3) the username
  locks for a window (default 300 s), locked attempts get 403 and
  are audited as `auth:locked`, and a success resets the counter.
- **Separation of duties (AC-5, technical slice)** — the `auditor`
  role holds `audit_read` and nothing else: audit review is a duty
  separable from administration.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed —
a *blocked* invocation is the pinned exception: it stores its blocked
record by design). Ids are sequential per object type: `mdl-`,
`tpl-`, `key-`, `ses-`, `req-`, `evd-`, `evr-`, `rule-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m aigateway serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--zero-persistence` (withhold prompt/response content from all
records; metadata only), `--certfile FILE --keyfile FILE` to serve
over TLS (standard library `ssl`), and `--max-failed-logins N` /
`--lockout-seconds S` for the AC-7 lockout. A startup line is printed
once the server is listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, registry_write, invoke, eval_run, usage_read, policy_write, audit_read, admin (all eight) |
| `bob`   | member  | read, registry_write, invoke, eval_run, usage_read |
| `carol` | viewer  | read, usage_read |
| `dana`  | auditor | audit_read |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404; a policy-blocked
invocation gets 422; a quota-exceeded invocation gets 429; an attempt
against a locked username gets 403. Denied attempts (401, 403, 422,
429) are audited by the HTTP layer with the route's action name
suffixed `:denied`. Errors are always JSON `{"error": "..."}` and no
stack trace is ever returned to a client.

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
| GET | `/audit` | audit_read | `{"entries": [...]}`; optional filters `?actor=&action=&target=&since=&until=` |
| GET | `/audit/verify` | audit_read | `{"ok": bool, "entries": n, "first_bad_index": int\|null}` |

Request dicts are `{id, model, model_version, session_id, actor,
key_id, prompt, output, reference_stub, responder, notice, usage,
status, created_utc}` with sequential ids `req-1`, `req-2`, …; the
other object types follow the same pattern with their own prefixes
(see `UNION-SPEC.md` for every dict shape). In zero-persistence mode
a record additionally carries `content_withheld: true` and its
`prompt`/`output` are `None`.

Audit entries are `{ts, actor, action, target, details, seq,
prev_hash, hash}` — the last three are the High-baseline hash chain.

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**193 tests, all passing** — the Group 9 suite carried up whole (146
tests; four files minimally adapted where the uplift changed
behavior) plus 47 tests added for this tier (7 inside the adapted
files, 40 in the four new uplift files). See
[`tests/README.md`](tests/README.md) for the coverage map, the
adaptation list, the negative controls, and the mutation-verification
record — both drills were performed on this build: the policy
wave-through mutant failed 14 tests and the file was restored
SHA-256-identical, and the audit-tamper control localizes an in-place
mutation at its exact index.

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 **High**
baseline — the CMMC L3 basis of NIST SP 800-171 Rev. 2 plus selected
NIST SP 800-172 enhanced requirements:

- **AC / IA** — access control (platform roles + API-key registry):
  AC-2 (account management), AC-3 (access enforcement), AC-5
  (separation of duties — the `auditor` role), AC-6 (least
  privilege), AC-7 (unsuccessful logon attempts — lockout); IA-2
  (identification & authentication — identity is supplied by the
  embedding organization via user/role headers; API-key secrets are
  stored only as SHA-256 digests, IA-5-flavored authenticator
  hygiene; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-5 (response to audit processing failure — fail
  closed), AU-6 (audit review), AU-7 (audit reduction & search),
  AU-9 (protection of audit information — append-only, hash-chained,
  audit-read restricted to the `audit_read` permission).
- **SI / SC** — gateway, records, metering, policy, evaluation:
  SI-10 (information input validation — malformed input is
  rejected, never partially applied) and SI-4-flavored usage
  monitoring via the metering records; SC-8 (transmission
  confidentiality — the server runs over TLS when a certificate is
  configured; encryption at rest is a deployment-layer control,
  stated plainly and not claimed here). Zero-persistence mode adds
  an SC/SI data-minimization flavor: content is never written to any
  record; only operational metadata persists.

Baseline gaps at High, named plainly (full analysis in
`UNION-SPEC.md`):

- **MFA and authenticator management (IA-2(1)/(2), IA-5)** are
  identity-provider properties. The demo identities are **hooks, not
  an identity provider**; the embedding organization must supply
  MFA-grade authentication, account lifecycle, and authenticator
  management.
- **FIPS-validated cryptography (SC-13)** is **not claimed**:
  Python's standard library is not a FIPS-validated module;
  validated crypto is a platform/deployment property.
- **Encryption at rest (SC-28)** remains a deployment-layer control.
- **Audit retention enforcement (AU-11)** is not implemented.
- **Session lock / termination (AC-11, AC-12)** are not implemented:
  the service authenticates per request and holds no session state
  for logon purposes; session management belongs to the embedding
  layer.
- Separation of duties is implemented only as its technical slice
  (the `auditor` role); who may hold which role is the embedding
  organization's policy.

## Honesty: what is NOT in this build

Plainly, first and most important:

- **The reference responder is a stub, and this build contains no
  learned model.** Its three behaviors are deterministic rules over
  the prompt text: `echo` returns the rendered prompt, `template`
  fills the model's configured template, and `rules` returns the
  first matching configured rule's response (else the configured
  default). Every response it produces is labeled
  `reference_stub: true` and carries a plain-language notice saying
  exactly that. There is no learned "AI" behavior here of any kind.
- **Learned AI/ML inference is NOT implemented and NOT contained in
  this build.** It stays **Extended** — in the Group 9 spec it was
  the group's #1 claim family (8 of 11 L2 siblings, 73%), and it is
  not faked here at any tier: each vendor's models are their own
  proprietary artifacts, and a Python-standard-library build has no
  learned models; claiming otherwise would be fabrication. The High
  uplift hardens the platform layer around models; it does not
  change what the responder is. What is built here is the platform
  layer around models this build does not contain.

The other Extended functions ranked in `UNION-SPEC.md` are also
specified there and **NOT implemented** in this build:

- Agentic & automated workflow engines (domain automation engines
  that run on top of the platform; the agents themselves are
  inference)
- Document processing & generation workflows (extraction and
  generation are inference workloads)
- Analytics, dashboards & reporting
- Contact center & customer experience (a vertical application, not
  platform substrate)
- The siblings' vertical domain applications (acquisition support,
  manufacturing quality, compliance/ERP enclaves, IT asset
  management, requirements management, cloud infrastructure, and
  the rest of the long tail named in the spec)

Further, plainly:

- **Multi-tenancy is a platform note, not a core function here:**
  this build is a single-tenant reference deployment; tenant
  isolation is a deployment-layer property, stated plainly, and not
  claimed here.
- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly, and not
  claimed here.
- The policy guardrails are **policy plumbing, not a safety
  model**: a configurable rule list evaluated on input and output,
  nothing more, and the build says so.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength, and account lifecycle belong to the
  embedding organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which baseline families the build's features answer
  to; nothing more. It also confers no AI capability claim: the
  registry, gateway, and harness are platform plumbing around models
  this build does not contain.
