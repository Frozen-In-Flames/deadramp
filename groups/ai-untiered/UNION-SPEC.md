# Union Spec — Artificial Intelligence (AI), untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Artificial
Intelligence (AI): **9 forks**, **tier null**. Every member's
FedRAMP impact level is **Unknown** in the source dataset — the
source publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in the
registry until the source publishes a baseline." The Documented
control claims section below replaces the baseline section a
tiered group's union spec carries.

Membership is exactly census unit `untiered:Artificial
Intelligence (AI)` in `../../remainder.json` (9 fork IDs, verified
mechanically, in unit order). In `forks.json` the set is as filed:
8 forks carry the Artificial Intelligence (AI) category and 1
(ThinkTrends, FR2634659079) is filed under Analytics; the census
assigned all 9 to this category from their own descriptions, and
the spec sheets record the assignment. Authorization statuses as
recorded span FedRAMP Certified (2) and Initial Implementation
(7) — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 9
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`. Sources: GSA FedRAMP Marketplace dataset
(cached at `../../raw/data_dump.json`, produced by the General
Services Administration, last change 2026-10-22), product records
joined by FedRAMP ID. All 9 descriptions were present in the
cached dataset and match `../../remainder/uncovered.json` exactly
(9/9).

## How functions were counted

The category's fixed 16-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../ai-l2/scratch/extract.py`, parsed, never executed) and
asserts it is the same 16 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **current shipped claim tables
exactly — 12 of 12 forks, 47 of 47 claims, deep-equal on function
ids and evidence sentences** (the original 11 of Group 9 plus the
Gobo remainder addition) — re-tagging each sheet's stored
description under the founding sentence/evidence rule (sentences
split on `(?<=[.!?])\s+` after replacing carriage returns with
spaces, the founding group's documented normalization; evidence is
the first matching sentence, truncated to 397 + '...' over 400
characters), after asserting each stored description equals the
raw cache's `service_desc`.

The founding group's recorded judgments are applied as recorded
judgment, and the verbatim patterns embody them: "AI-enabled"
does not fire the `learned_inference` pattern and "intelligent
agents" does not fire the ai-agents arm (the Gobo precedent); an
`audit_logging` claim on the single word "auditability" stands at
artifact weight in the founding record (Asato, Gobo). This set's
own adjective-form near-misses are recorded, not repaired, in
`scratch/ARTIFACTS.md` — chiefly Claude's "AI assistant" and bare
"natural language" (no `learned_inference` claim for the set's
flagship LLM), ElevenLabs' "AI-produced" / "multi-tenancy" /
"Zero Retention Mode" / singular "API" (four substance-adjacent
forms, no claims), Bland's "AI phone agents", and Lemma's "AI
workflow orchestration".

An exclusion pass scanned every raw hit's evidence sentence for
negation / scope-exclusion phrasing: **one hit was removed** of
14 raw hits. Bland's `model_gateway` hit fired on "model
providers" inside the sentence stating customer calls are **not**
sent to third-party frontier model providers — the
gateway-to-providers capability placed out of scope by the fork's
own wording (the scope-exclusion precedent). One flagged hit was
adjudicated **keep**: ElevenLabs' `audit_logging`, whose Zero
Retention Mode sentence negates retention of customer
inputs/outputs but positively asserts that system and audit data
is persisted. `certified_services` record fields (non-empty for
8 of the 9 forks) were never matched — that discipline alone
prevented a fabricated `usage_metering` claim from Baseten's
certified-services billing text. Full record:
`scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not a
ceiling. **13 claims** across the set; **7 of 9 forks carry at
least one claim**. The two zero-claim forks are recorded under
Named absences, not hidden.

Census citations: 10 citations are recorded for these forks in
the census; **10 of 10 verify** as verbatim substrings of the
forks' own descriptions (one, ThinkTrends' second citation, only
after whitespace normalization — the source sentence is
line-broken); **5 of 10** are themselves a claim evidence
sentence. Verification is not a claim, in either direction; the
per-citation record is `scratch/citation_check.json`.

## Function ranking — all 9 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 9) | Disposition in this build |
|---|---|---:|---|
| 1 | Learned AI/ML inference (LLMs, ML, NLU, predictive models) | 4 | Extended — the models themselves; see the honesty note below |
| 2 | Agentic & automated workflow automation | 3 | Extended (domain automation engines; the agents themselves are inference) |
| 3 | Audit logging & trails | 2 | **Core** (audit log) |
| 4 | Identity & access control | 1 | **Core** (access-control hooks) |
| 5 | Multi-tenant architecture & tenant isolation | 1 | Platform note (single-tenant reference deployment; tenant isolation is a deployment-layer property) |
| 6 | Configurable security guardrails / content policy | 1 | **Core** (policy plumbing — rules evaluated on input and output, not a safety model) |
| 7 | Contact center & customer experience | 1 | Extended (a vertical application, not platform substrate) |
| 8 | Model gateway & request routing | 0 | **Core** substrate (the gateway) — **zero claimants in this set; named absence** (the set's only raw hit was removed in the exclusion pass) |
| 9 | Model governance & approved-model registry | 0 | **Core** substrate (the registry) — **zero claimants in this set; named absence** |
| 10 | Usage monitoring, metering & cost/budget controls | 0 | **Core** substrate (metering & quotas) — **zero claimants in this set; named absence** |
| 11 | Request/response & interaction records, operational metadata | 0 | **Core** substrate (request records) — **zero claimants in this set; named absence** |
| 12 | Zero-persistence / ephemeral processing option | 0 | **Core** substrate (zero-persistence mode) — **zero claimants in this set; named absence** |
| 13 | Evaluation records, scoring & quality review | 0 | **Core** substrate (evaluation harness) — **zero claimants in this set; named absence** |
| 14 | Open APIs & integrations | 0 | **Core** surface (the service is API-first) — **zero claimants in this set; named absence** |
| 15 | Document processing & generation workflows | 0 | Extended — **zero claimants in this set; named absence** |
| 16 | Analytics, dashboards & reporting | 0 | Extended — **zero claimants in this set; named absence** |

**The honesty note on row 1** (carried from the founding spec,
unchanged in substance): learned inference is what most of these
products *sell*, and it is the one thing this build does not and
cannot contain: each vendor's models are their own proprietary
artifacts, and a Python-standard-library build has no learned
models. What the founding siblings genuinely share is the
*platform layer around* the models — a registry of approved
models, a gateway that routes requests to them, metering and
budget controls, records, guardrail hooks, evaluation plumbing,
access control, and an audit log. That layer is the core below,
carried whole. The gateway's responder is a deterministic
**reference stub** (echo, template, or rule-based behaviors),
labeled `reference_stub: true` in every response it produces.
Actual learned inference is an Extended gap for the final batch.

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — model
registry; prompt template registry; gateway & reference
responder; usage metering & quotas; conversation & request
records (with zero-persistence mode); policy guardrails (hooks);
evaluation harness; API access; access control & API keys; audit
log. The substrate is the platform layer every sibling's offering
presupposes, and it is tier-independent code: the founding
build's source contains no tier or baseline machinery, so there
was nothing tier-shaped to strip. In this set, three of the ten
functions are claim-supported by at least one fork under the
standing dispositions (the audit log by `audit_logging`, 2 forks;
access control by `access_control`, 1 fork; the policy hooks by
`guardrails`, 1 fork). The other seven are **carried, not
claimed** in this set: no fork here claims the gateway, the
registry, metering, interaction records, zero-persistence,
evaluation records, or the API surface at the taxonomy's phrases,
and the substrate is not re-scoped to pretend otherwise.
Functions are **carried** as substrate; no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/aigateway/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `aigateway` under `src/`, ids sequential
per object type with fixed prefixes (`mdl-`, `tpl-`, `key-`,
`ses-`, `req-`, `evd-`, `evr-`, `rule-`), failed operations
consume no id and change nothing (a *blocked* invocation stores
its blocked record by design), all timestamps UTC ISO-8601,
roles `admin|member|viewer` with the founding permission matrix,
the token estimator pinned at `estimate_tokens(text)` = 0 for
empty, else `(len(text)+3)//4`, and the audit log append-only
with denied attempts recorded at the HTTP layer. Where the
founding contract's text says "L2 baseline hooks" for access
control and audit, read it here as **baseline-neutral hooks**:
at tier null they are substrate, claimed against no baseline.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 9 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under the
taxonomy families that carry control language. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Control areas **documented** by at least one fork in the set:

- **Audit & accountability (AU)** — via `audit_logging`,
  **2 forks**: Anthropic Claude (FR2633053633 — "Organization
  administrators manage identity, access, data retention, and
  audit controls across all interfaces"; recorded at
  administration-surface weight, above the founding record's
  "auditability" artifact weight, below an explicit audit-logging
  claim), ElevenLabs Platform (FR2628647238 — under Zero
  Retention Mode "only system and audit data is persisted";
  recorded at ZRM-persistence weight).
- **Access control (AC), with identification & authentication
  language (IA)** — via `access_control`, **1 fork**: ElevenLabs
  Platform (FR2628647238 — "All services share a common identity
  and access management layer"). Claude's administration
  sentence names "identity, access" in comma form and forms no
  `access_control` claim; it is recorded as a near-miss, not
  documented here as a second AC claim.
- **Content policy / guardrail configuration (policy language)**
  — via `guardrails`, **1 fork**: ThinkTrends AI Platform
  (FR2634659079 — "Configurable content safety guardrails
  (HIPAA, PII, tone, compliance policies) applied at the agent
  and platform level"). This documents a configurable policy
  surface in the fork's own words; it is not a safety-model
  claim, for the fork or for this build.
- **Platform architecture assertion (not a control family)** —
  via `multi_tenancy`, **1 fork**: Caldera Mesa (FR2700137035 —
  "a multi-tenant software-as-a-service application"). The
  family's label includes tenant isolation; Mesa's sentence
  asserts multi-tenancy only, no isolation language, and it is
  documented at exactly that weight.

Control areas **not documented** by any fork in this set: model
governance (no fork fires `model_governance` — ThinkTrends'
"Agentic Governance" bullet is evaluation-jobs substance and
fires no governance family); usage monitoring (no
`usage_metering` claim — Baseten's per-token billing language
exists only in its `certified_services` record field, which is
never matched); zero-persistence (ElevenLabs' Zero Retention
Mode is retention phrasing, not the family's
"zero-persistence / ephemeral" phrases); and every other NIST
SP 800-53 control family — including AT, CA, CM, CP, IR, MA, MP,
PE, PL, PM, PS, RA, SA, SC, and SI beyond the guardrail policy
language above — is asserted by no description in the set. If
the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **Nine families at 0 of 9:** `model_gateway`,
  `model_governance`, `usage_metering`, `interaction_records`,
  `zero_persistence`, `evaluation_records`, `api_integration`,
  `document_automation`, `analytics_reporting`. Seven of the nine
  are Core substrate families — the substrate is carried whole
  regardless; the absences are about what this set's prose
  claims, and they stand unfilled.
- **`learned_inference` near-absence at the top of the market:**
  the family leads the ranking (4 of 9), but the set's two most
  prominent inference products claim none of it — Claude (its
  prose says "AI assistant" and bare "natural language") and
  ElevenLabs ("AI-produced speech"). Both zeros are wording
  facts under the verbatim taxonomy, recorded not repaired.
- **Zero-claim forks (2):** FR2628647242, Bland AI / Bland — a
  FedRAMP Certified voice-AI platform whose "AI phone agents" is
  not the family's contiguous "AI agents" phrase, and whose only
  raw hit sat inside an explicit negation and was removed; and
  FR2632054534, Thread AI / Lemma (GovCloud) — a one-sentence
  description naming "AI workflow orchestration", which fires no
  family (no agentic token, no automat\w+ token).

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented
— claimant counts are this set's:

- [ ] Learned AI/ML inference — the models themselves (4 claimants: Anyreach, Baseten at platform weight, Beam, ThinkTrends; Claude's and ElevenLabs' models are substance at zero claims and enlarge the same gap)
- [ ] Agentic & automated workflow execution engines (3 claimants: Claude, Anyreach, ThinkTrends; Lemma's orchestration platform is the same substance at zero claims)
- [ ] Voice & speech AI engines — speech-to-text, text-to-speech, voice agents, real-time interpretation (Bland, ElevenLabs, Beam, described in substance across all three; claim-light by phrasing)
- [ ] Model serving & inference infrastructure — managed deployment, autoscaling, serving (Baseten; Bland's own-models boundary and ElevenLabs' unified data plane are adjacent substance)
- [ ] Document understanding, summarization & report generation (Beam Notes/Reports; Mesa Research drafting; ThinkTrends knowledge-base ingestion — no `document_automation` claim at the family's phrases)
- [ ] Knowledge-base / retrieval engines — vector embeddings, grounded citation-based answers (ThinkTrends, Mesa Research)
- [ ] Evaluation & benchmarking engines (ThinkTrends' automated evaluation jobs against accuracy/relevance/safety benchmarks — substance, no `evaluation_records` claim)
- [ ] Vertical workflow applications — public-records processing (Mesa: intake through review, redaction, release), human-services case workflows (Beam), constituent-service contact-center workflows (Anyreach — the set's one `contact_center` claim)

## Coverage statement (for this build)

9 forks spec'd of 9 in census unit `untiered:Artificial
Intelligence (AI)`; 13 taxonomy claims tagged from the forks' own
descriptions (7 of 9 forks claiming at least one); the
ten-function substrate carried byte-identical from the founding
AI L2 build and re-anchored to tier null; tier null recorded on
every sheet and pinned by tests. Nothing in this build claims a
FedRAMP authorization, a CMMC certification, or a control
baseline for any fork or for the build itself, and the gateway's
inference surface is a labeled reference stub, not a model.
