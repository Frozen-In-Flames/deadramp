# Union Spec — Artificial Intelligence (AI), CMMC L3-adjacent (DeadRamp Phase 2, Group 22)

The merged functional spec for the twenty-second sibling group:
**3 forks**, category **Artificial Intelligence (AI)**, CMMC tier
**L3-adjacent** (every member is FedRAMP **High** in `forks.json` —
verified, so the group is single-tier and the merge takes the group
baseline in full, per Merge Rule 2). The member list in
`forks.json` was reconciled against `MAP.md`'s "Artificial
Intelligence (AI) — L3-adjacent (3)" section: **zero diffs** in
both directions.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 3
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence. Sources: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product records joined by FedRAMP ID. No live
fetching was needed: all 3 descriptions were present in the cached
dataset.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two
parents:

1. The **Group 9 merged build** (`../ai-l2/`) — itself the union of
   the 11 Artificial Intelligence (AI) L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room AI-platform substrate.
2. This group's **3 High forks**, via the spec sheets in `specs/`:
   Cognition Platform (Cognition USG, Inc.), DataRobot for
   Government (DataRobot), Canopy (Ripcord).

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** /
CMMC **L3-adjacent** — and must satisfy it **in full** (Rule 2),
this document plus the spec sheets are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was re-run
independently by the coordinator, and both negative controls were
mutation-verified by patching the implementation (see
Verification below).

**Reuse, stated explicitly:** where functions overlap, this build
reuses Group 9's own open-source code (Apache-2.0, ours). One
module is byte-identical to Group 9 (`__init__.py`); six are
modified for the tier uplift (`audit.py`, `access.py`,
`errors.py`, `store.py`, `service.py`, `__main__.py`) — verified
with `cmp`/SHA-256, not asserted. The uplift analysis below names
what the High baseline demanded beyond the L2 core and what was
done about each item — implemented, or gap-listed by name.

## How functions were counted

The same fixed 16-function taxonomy as Group 9 (verbatim — same
ids, labels, and matching patterns) was matched against each
offering's own public description. A function is claimed for a
fork **only** when the description contains matching text; the
matching sentence is stored as the claim's evidence in the spec
sheet. All 3 offerings carry at least one tagged claim (**5 claims
in total**), so — unlike the enclave groups at this tier — there
are no zero-claim sheets here and no function was invented for any
fork. The three descriptions are short marketing prose
(628–871 characters each, against Group 9's longer platform
descriptions), so the counts are a **floor**, not a ceiling, and
an unusually low one; the wording artifacts below are where the
floor shows.

Wording-artifact judgments recorded by the extractor, kept
visible rather than silently cleaned up:

- **Cognition Platform — agentic workflows** rests solely on the
  generic word "automated" ("automated code generation, testing,
  review, and deployment"); the description contains no "agentic",
  "AI agents", or programmable-rules language. Kept as tagged
  under the verbatim taxonomy, flagged here.
- **DataRobot — multi-tenancy, NOT claimed**: the description says
  "single tenancy isolation" — semantically tenant isolation, but
  the taxonomy requires "multi-tenant" or the exact phrase "tenant
  isolation" ("tenancy" ≠ "tenant"). Recorded as a near-miss, not
  a claim.
- **DataRobot — model governance, NOT claimed**: "develop,
  deliver, and govern AI at scale" does not contain "model
  governance" or "approved models". Near-miss, recorded.
- **Ripcord Canopy — document processing, NOT claimed**: Canopy
  is self-describedly "a document intelligence platform" that
  digitizes, classifies, and extracts documents, but none of the
  taxonomy's narrow document patterns literally appear.
  **Agentic workflows, NOT claimed** ("agent-in-the-loop" is not
  agentic / AI agents / automat\*), and **evaluation records, NOT
  claimed** ("quality assurance" is not "quality management").

## Function ranking — all 3 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Learned AI/ML inference (LLMs, ML, NLU, predictive models) | 3 | 100% | **Extended** — see the honesty note below; claimed by every sibling and deliberately *not* in the core |
| 2 | Agentic & automated workflow automation | 1 | 33% | Extended (Cognition; rests on the "automated" wording artifact above) |
| 3 | Multi-tenant architecture & tenant isolation | 1 | 33% | Platform note (Ripcord; the build is a single-tenant reference deployment; tenant isolation is a deployment-layer property, stated plainly) |
| 4 | Model gateway & request routing | 0 | 0% | **Core** — carried from the Group 9 union (see the core-boundary note) |
| 5 | Model governance & approved-model registry | 0 | 0% | **Core** — carried from the Group 9 union |
| 6 | Usage monitoring, metering & cost/budget controls | 0 | 0% | **Core** — carried from the Group 9 union |
| 7 | Audit logging & trails | 0 | 0% | **Core** (High baseline hooks, uplifted — see below) |
| 8 | Identity & access control | 0 | 0% | **Core** (High baseline hooks, uplifted — see below) |
| 9 | Configurable security guardrails / content policy | 0 | 0% | **Core** — carried from the Group 9 union (policy *plumbing*, not a safety model) |
| 10 | Request/response & interaction records, operational metadata | 0 | 0% | **Core** — carried from the Group 9 union |
| 11 | Zero-persistence / ephemeral processing option | 0 | 0% | **Core** — carried from the Group 9 union |
| 12 | Evaluation records, scoring & quality review | 0 | 0% | **Core** — carried from the Group 9 union |
| 13 | Open APIs & integrations | 0 | 0% | **Core** (the service is API-first) — carried from the Group 9 union |
| 14 | Document processing & generation workflows | 0 | 0% | Extended (Ripcord's domain in prose; untagged under the verbatim taxonomy — near-miss recorded above) |
| 15 | Analytics, dashboards & reporting | 0 | 0% | Extended |
| 16 | Contact center & customer experience | 0 | 0% | Extended (carried from the Group 9 union at 0 claims in this group) |

**The core-boundary note (Group 6's precedent, applied again).**
Thirteen of sixteen functions tag zero claims in this group,
including the entire platform surface (gateway, registries,
metering, records, policy, evaluation) that Group 9's core is
built from. Those functions stay Core because the Merge Rule
carries the L2 union upward whole: the merged fork inherits the
union of its parents, and this group's parent is the Group 9
build. A wording artifact — three short marketing descriptions
that never say "gateway", "registry", or "audit" — is not a
downgrade, and re-tuning the taxonomy to make these descriptions
tag more would corrupt cross-group comparability. The taxonomy
was therefore not re-tuned, and the thin claim mass is recorded
as what it is.

**The honesty note on row 1.** Learned inference is what all
three of these products *sell* — an autonomous software-engineering
agent (Cognition), an ML model development and governance
platform (DataRobot), a document-intelligence service (Ripcord) —
and it is the one thing this build does not and cannot contain:
each vendor's models are their own proprietary artifacts, and a
Python-standard-library build has no learned models. Claiming
otherwise would be fabrication. What the siblings genuinely share
with the Group 9 union — and what the merged build is — is the
*platform layer around* the models: a registry of approved
models, a gateway that routes requests to them, metering and
budget controls, records, guardrail hooks, evaluation plumbing,
access control, and an audit log, now uplifted to the High
baseline. The gateway's responder is a deterministic **reference
stub** (echo, template, or rule-based behaviors), labeled
`reference_stub: true` in every response it produces. Actual
learned inference is an Extended gap for the final batch, named
as such.

**Differences are preserved, not averaged away**: the three
siblings are three different verticals wearing one category —
AI-driven software development (Cognition/Devin: codebase
analysis, automated code generation, testing, review, deployment,
legacy-language modernization), ML lifecycle development and
governance (DataRobot: explore, build, train, manage ML and
generative models, on Kubernetes/EKS), and digitization as a
service (Ripcord Canopy: robotics, OCR/ICR, LLM-based document
classification and extraction, agent-in-the-loop QA). None of
those domain applications is platform substrate; each is named in
the ranking's Extended rows and in its fork's spec sheet.

## The Core — what the merged build implements (10 functions)

Group 9's core, carried up whole under the Merge Rule and
uplifted to High (uplift deltas in the next section):

1. **Model registry** — models as registered, versioned
   artifacts (name, auto-incrementing version, provider label,
   capability tags, responder behavior, status
   `active`/`deprecated`; deprecated models refuse requests).
2. **Prompt template registry** — prompt templates as registered,
   versioned artifacts; a request may name a template and the
   gateway renders the prompt through it (`{prompt}`
   substitution) before routing.
3. **Gateway & reference responder** — a request names a
   registered model and a prompt; the gateway routes it to that
   model's registered responder behavior (`echo`, `template`,
   `rules` — deterministic reference behaviors only) and returns
   the response with usage figures, `reference_stub: true`, and
   the pinned plain-language notice that the output is a stub,
   not a learned model.
4. **Usage metering & quotas** — every completed or blocked
   invocation is metered with a pinned deterministic token
   estimator (~1 token per 4 characters, stated as an estimator);
   per-owner monthly usage is queryable and an administrator may
   set a per-owner monthly token quota, enforced before a request
   runs.
5. **Conversation & request records** — sessions group
   invocations into conversations; every invocation leaves a
   request record of operational metadata; a store-wide
   **zero-persistence mode** withholds prompt/response content
   from all records, keeping metadata only.
6. **Policy guardrails (hooks)** — an ordered, configurable rule
   list (term substrings or regex patterns, scoped to input,
   output, or both) evaluated on every invocation's prompt and
   output; a match blocks the invocation, stores a blocked
   request record, and is audited. Policy plumbing, not a safety
   model, and the build says so.
7. **Evaluation harness** — named datasets of cases (prompt,
   expected, exact/contains match, optional rubric criteria); a
   run exercises a registered model's responder over a dataset
   and records per-case results and an aggregate score. Eval runs
   exercise the responder directly — recorded as eval runs, not
   metered as gateway traffic.
8. **API access** — every function above exposed over a REST API
   (JSON); the invocation endpoint is OpenAI-*flavored* because
   Group 9's gateway siblings advertise OpenAI-compatible
   surfaces; it is this build's own API, not OpenAI's.
9. **Access control & API keys** — role-based access hooks
   (platform roles with a permission matrix enforced on every
   operation, uplifted with the `auditor` role below) plus
   registered API keys: only the SHA-256 digest is stored, the
   secret is shown once at creation, and invocations may be
   attributed to a key for metering.
10. **Audit log** — an append-only, hash-chained audit trail
    (uplifted, below): every registry, key, quota, policy,
    session, invocation, and evaluation mutation, every policy
    block, and (at the HTTP layer) every denied attempt, recorded
    with actor, action, target, and UTC timestamp.

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline
  (the FedRAMP High tailoring), cross-walked to the 110 practices
  of NIST SP 800-171 Rev. 2 plus the subset of NIST SP 800-172
  enhanced requirements that define CMMC L3. The parents sit at
  two tiers — the Group 9 union at Moderate, this group's forks
  at High — so per Merge Rules 1–2 the merged baseline is the
  **union**, taken at **High**, un-diluted and inherited in full.
- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand at High | Control anchor | Disposition |
  |---|---|---|
  | Tamper-evident audit records | AU-9, AU-3 | **Implemented** — every audit entry carries `seq`, `prev_hash`, `hash` (SHA-256 over the canonical JSON of the entry's content plus `prev_hash`; genesis `prev_hash` is `"0"*64`); `AuditLog.verify_chain()` returns `(True, None)` or `(False, first-bad-index)`; `GET /audit/verify` exposes it; the chain survives JSONL persistence and reload |
  | Response to audit-processing failure | AU-5 | **Implemented** — `AuditLog.record` rolls back the in-memory append and raises `AuditWriteError` when the file append fails; every audited store mutation is wrapped fail-closed (pre-operation state snapshot restored, error propagates): an operation whose audit write fails creates no object and consumes no id |
  | Audit review, analysis & reduction | AU-7 | **Implemented** — `GET /audit` passes `actor`, `action`, `target`, `since`, `until` filters through to the log's query |
  | Unsuccessful logon attempts | AC-7 | **Implemented** — service-layer per-username lockout (`max_failures` default 3, `lockout_seconds` default 300); attempts while locked are answered 403 and audited `auth:locked`; a successful authentication resets the counter; CLI flags `--max-failed-logins` / `--lockout-seconds` |
  | Separation of duties for audit review | AC-5 | **Implemented** — new `auditor` role holding `{audit_read}` and no other permission; demo identity `dana=auditor` alongside `alice=admin`, `bob=member`, `carol=viewer` |
  | MFA / authenticator management | IA-2(1)/(2), IA-5 | **Gap-listed** — identity is the embedding organization's (demo identities are hooks, not an IdP); no authenticator management is built or claimed |
  | FIPS-validated cryptography | SC-13 | **Gap-listed** — Python stdlib is not a FIPS-validated module; the audit chain's SHA-256 is a stdlib hash, not claimed as validated cryptography |
  | Encryption at rest | SC-28 | **Gap-listed** — deployment layer; transmission confidentiality is TLS when a certificate is configured (SC-8) |
  | Audit retention enforcement | AU-11 | **Gap-listed** — the log is append-only and persistent, but no retention period is enforced |
  | Session lock / termination | AC-11/AC-12 | **Gap-listed** — stateless per-request header auth in the current build; no session objects to lock or terminate |

- **Feature → control family mapping (this build):** as Group 9,
  with the uplift deltas marked **[L3]**:
  - Access control (platform roles + API-key registry) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege; **[L3]** AC-5 auditor separation of duties, AC-7
    logon lockout), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; API-key secrets are stored only as SHA-256
    digests, IA-5-flavored authenticator hygiene; the service
    ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review; **[L3]** AU-5 fail-closed audit
    writes with rollback, AU-7 audit query/reduction, AU-9
    hash-chain protection of audit information — admin/auditor-only
    read).
  - Gateway, records, metering, policy, evaluation → **SI**
    (SI-10 information input validation — malformed input is
    rejected, never partially applied; SI-4-flavored usage
    monitoring via the metering records) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS when
    a certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here).
  - Zero-persistence mode → **SC**/**SI** data-minimization
    flavor: content is never written to any record; only
    operational metadata persists, per the Group 9 substrate's
    own stated architecture.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. It also confers no AI capability claim: the
  registry, gateway, and harness are platform plumbing around
  models this build does not contain.

## Implementation contract (what `src/` and `tests/` are built against)

Group 9's implementation contract (in `../ai-l2/UNION-SPEC.md`)
stands **unchanged** except for the uplift deltas below, marked
**[L3]**. Python 3, **standard library only** — verified by an
import audit of every module. Package `aigateway` under `src/`,
runnable and testable with `PYTHONPATH=src`.

- **[L3] `aigateway/errors.py`** — gains `AuditWriteError`,
  deriving from `AIGatewayError`; at the HTTP layer it maps to
  **500** `{"error": "audit write failed"}` (see interpretations).
- **[L3] `aigateway/audit.py`** — entries gain `seq` (0-based),
  `prev_hash`, `hash` (eight keys total: the Group 9 five plus
  these three). `verify_chain()` → `(True, None)` on a clean
  chain, `(False, index)` localizing the first entry whose `seq`,
  `prev_hash`, or recomputed `hash` disagrees. `record()` is
  fail-closed: on `OSError` from the JSONL append it removes the
  in-memory entry and raises `AuditWriteError`. Gains
  `query(actor=None, action=None, target=None, since=None,
  until=None)` for audit reduction. JSONL reload preserves chain
  fields, so a reloaded log still verifies.
- **[L3] `aigateway/access.py`** — roles gain `auditor` =
  `{audit_read}` only (no other action). All Group 9 roles and
  the eight actions are unchanged.
- **[L3] `aigateway/store.py`** — every audited mutation (11
  methods, including `invoke`'s blocked and completed paths) is
  wrapped fail-closed: a pre-operation deep-copy snapshot of the
  store's mutable state is restored if the operation raises
  `AuditWriteError`, and the error propagates — no object
  created, no id consumed. All method signatures, ids, and the
  pinned token estimator are unchanged from Group 9.
- **[L3] `aigateway/service.py`** — `make_server(host, port,
  store, audit, users, max_failures=3, lockout_seconds=300)`.
  Authentication failures are counted per username; at
  `max_failures` consecutive failures the username locks for
  `lockout_seconds`; attempts while locked are answered 403 and
  audited `auth:locked`; a successful authentication resets the
  counter. `GET /audit` (audit_read) passes `actor`, `action`,
  `target`, `since`, `until` query filters through. New
  `GET /audit/verify` (audit_read) → `{"ok": bool, "entries":
  count, "first_bad_index": index-or-null}`. All Group 9
  endpoints, statuses, and denial auditing are unchanged.
- **[L3] `aigateway/__main__.py`** — demo users gain
  `dana=auditor`; `serve` gains `--max-failed-logins` /
  `--lockout-seconds` flags feeding the lockout parameters.

**Contract interpretations resolved during the build** (named, so
the record shows where the Group 9 contract was silent and this
build chose): (1) **`/audit` read ordering** — the L3 reference
builds compute the trail before appending their `audit_read`
entry, but Group 9 records the read first and its inherited
service test pins that; the L2 ordering was kept and filters
added on top. `GET /audit/verify` has no L2 precedent and follows
the L3 ordering (verification computed before its own
`audit_read` entry is appended). (2) **Filter set** — the full
five (`actor`, `action`, `target`, `since`, `until`) at both the
log and HTTP layers (the L3 references split this set across
layers; the union was taken, per Merge Rule 1). (3)
**`AuditWriteError` HTTP status** — 500, following the
collaboration L3 precedent rather than the cybersecurity 400,
because aigateway's generic `AIGatewayError` mapping would
otherwise report an audit-infrastructure failure as a client
error.

## Verification

- **Specs:** 3 / 3 forks spec'd; member set reconciled three ways
  (forks.json ↔ MAP.md ↔ specs.json) with zero diffs; every
  claim's evidence string verified to appear in its fork's own
  description.
- **Tests:** **193 run, 193 passed** (coordinator's independent
  re-run: `PYTHONPATH=src python3 -m unittest discover -s
  tests`). Composition: Group 9's 146 inherited (nine test files
  byte-identical to Group 9's; four minimally adapted — the audit
  key-set assertion extended to the eight chained keys, additive
  auditor-role and CLI-uplift test classes, one additive helpers
  fixture) plus 47 new uplift tests (`test_audit_chain.py`,
  `test_audit_failure.py`, `test_audit_query.py`,
  `test_lockout.py`, and the additive classes).
- **Negative controls, both mutation-verified by drill:**
  (a) **Policy wave-through** — patching the real
  `_first_policy_match` in `src/aigateway/store.py` to wave every
  text through produced **14 failures** across the suite (the
  same distribution as Group 9's drill; no uplift test depends on
  policy). The file was restored from its pre-mutation copy and
  SHA-256-verified identical; the suite returned to green.
  (b) **Audit tamper** — a clean log verifies `(True, None)`;
  mutating entry 1's actor in place makes `verify_chain()` return
  `(False, 1)` — the tampered index, exactly. Recorded in
  `tests/README.md`.
- **Live smoke (coordinator-driven):** registered echo model
  invoked through the store — response carries
  `reference_stub: true` with the pinned notice; chain verifies
  clean, then localizes a hand-made tamper at index 1; the
  `auditor` role reads audit and is denied `invoke` and
  `registry_write`.

## Coverage statement (for this build)

- Specs: 3 / 3 forks spec'd.
- Core: 10 core functions implemented (Group 9's union carried up
  whole), each with tracing tests, uplifted to the High baseline
  as analyzed above.
- Extended: specified and ranked, **not** implemented in this
  build — learned AI/ML inference (the group's #1 family at 3 of
  3 and, with Group 9's, the final batch's largest single item);
  agentic & automated workflow engines; document processing &
  generation workloads; analytics, dashboards & reporting;
  contact center & customer experience; and the siblings' vertical
  domain applications (AI software-development platform, ML
  lifecycle platform, digitization-as-a-service), named in the
  ranking notes. Multi-tenancy is a platform note (single-tenant
  reference deployment; tenant isolation is a deployment-layer
  property), and the five High platform gaps (MFA/authenticator
  management, FIPS-validated cryptography, encryption at rest,
  audit retention, session lock/termination) are gap-listed in
  the uplift table, never implied closed.
