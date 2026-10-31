# Addendum — Artificial Intelligence (AI), CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:ai-l2`** (see `../../REMAINDER.md`). The original union
spec stands as written: its taxonomy, its 10-function core, and its
control baseline are **unchanged**. This document records what
joined, what the newcomer claims under the group's existing
taxonomy, the core-delta decision for every claimed function, and
the updated union statement.

**Headline: fork spec'd 1 / 1; 2 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 146 → 157, all
passing.** The newcomer is an AI-branded cognitive-automation
platform whose description is dense with AI adjectives — and under
the group's verbatim taxonomy it claims exactly two families,
neither of them learned inference. That outcome is structural, it
is pinned in tests with the near-misses itemized, and §2 records
it rather than tuning it away. **3 new gap functions** are named
in §5; 1 already-registered gap gains a claimant and 1 gains a
by-substance member.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2214346691` | Secunetics, Inc. / Gobo Framework (Gobo) |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the taxonomy out of the original
  `scratch/extract.py` via `ast` (parsed, never executed) and
  asserts the 16 (id, label, regex) triples before tagging** —
  the taxonomy was applied verbatim, not re-tuned for the
  newcomer. Verbatim is proven, not asserted: the extractor first
  **reproduces the original 11 forks' shipped claim tables
  exactly** (function ids and evidence sentences) from their
  stored descriptions; only then does it tag anyone new. Same
  sentence splitting, same evidence rule (first matching sentence
  per family, stored verbatim), same sheet schema. The sheet is
  **appended** to `specs/specs.json` after the original 11, which
  are verified deep-equal against git HEAD.
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **Moderate** / Certified (SaaS, Government Community Cloud), so
  the group stays single-tier and the L2 baseline is inherited in
  full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: the
  census's **1 citation** for this fork was re-checked against
  the fork's own cached description and **verifies** as a
  verbatim substring. It is exactly the sentence that becomes the
  `agentic_workflows` evidence — verification and claim coincide
  here, which §2 notes rather than generalizes.
- **No exclusion trap applies to the newcomer.** Its record
  carries no `certified_services` block (the field is empty in
  the cached record), so there is no hosted-services segment to
  exclude; only `service_desc` was matched, per house method.

## 2. What the addition claims

**2 claims** for the 1 fork; the fork carries at least one claim,
so the group stays at every fork claiming. Claim counts for the
families the addition touches, with the group's combined count
(original 11 + addition = 12 forks) alongside:

| Function | Addition claiming | Group total (12) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Agentic & automated workflow automation | 1 | 5 | **Extended** — domain automation engines; the agents themselves are inference |
| Audit logging & trails | 1 | 5 | **Core** (Core 10 — append-only audit log) |
| Learned AI/ML inference | 0 | 8 | **Extended** — gains a by-substance member only (§5) |
| All other 13 families | 0 | unchanged | as in UNION-SPEC |

The full claim table is pinned literally in
`tests/test_additions.py` (`EXPECTED_CLAIMS`).

### The finding that matters

Gobo is sold as an AI platform — "AI-enabled cognitive automation",
"semantic intelligence", "intelligent agents" — and it claims
**no** `learned_inference`. The family's patterns are the original
pass's literal phrases (`ai-powered`, `ai agents`, `machine
learning`, `generative ai`, …), and none of Gobo's adjectives is
among them: "AI-enabled" is not "ai-powered", "intelligent agents"
is not "ai agents", and "semantic intelligence" matches nothing.
The taxonomy was not re-tuned to catch them. The inference
substance is real and is recorded as such in §5 — as a
by-substance enlargement of the inference gap, not as a claim.

Sharper still: the fork's most agentic sentence — "Gobo features
intelligent agents to orchestrate complex administrative and
technical processes" — tags **no family at all** (no "ai agents",
no `automat*` token), pinned by test. The `agentic_workflows`
claim rests on the description's automation wording elsewhere,
starting with its first sentence ("AI-enabled cognitive
automation platform", via `automat\w+`).

### Near-misses, itemized

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`; every item below is pinned
in tests):

- **"AI-enabled"** (twice, incl. the "AI-Enabled Cognitive
  Automation" heading) — not `learned_inference`'s "ai-powered"
  or any other alternative.
- **"intelligent agents"** — not "ai agents"; and the sentence
  contains no automation token (see above).
- **"semantic intelligence"** — no family; the sentence it sits
  in claims `agentic_workflows` only via "automate complex,
  data-intensive tasks".
- **"public comment analysis" / "analyze complex datasets"** —
  "analysis" and "analyze" are not `analytics_reporting`'s
  "analytics"; no "dashboard" or "reporting" token appears
  anywhere in the description.
- **"integrates seamlessly with existing systems and data
  environments"** — not `api_integration`: no API token, no
  "integration methods", no pre-built integrations phrase.
- **"auditability, and governance"** — "governance" alone is not
  `model_governance` ("model governance" required); see the
  artifact note below for what the same sentence does claim.
- **"quality of outcomes"** — not `evaluation_records`' "quality
  management".
- **"CLIN and Invoice Management … automate invoice
  reconciliation"** — not `document_automation`'s "invoice
  processing", and not `usage_metering` (no "billing", no token
  counts, no cost-and-budget phrasing). The invoice surface is
  recorded under the EIS gap in §5, not double-counted here.
- **"human-in-the-loop control"** — not `guardrails` (no
  guardrail token) and not `access_control` (no access-control,
  role-based, or identity phrasing anywhere in the description).
- **"vendor-agnostic platform"** — not `multi_tenancy` (no
  multi-tenant or tenant-isolation wording).
- **"real-time performance tracking" / "continuous SLA and
  Service Inventory Management"** — monitoring substance with no
  family: this taxonomy has no infrastructure-monitoring family;
  the surface is gapped in §5, not claimed.

### Wording artifact in a claim that stands

Recorded for honesty, not corrected — the taxonomy is the
group's law, applied verbatim:

- **Gobo, `audit_logging`** fires via the family's bare `(audit)`
  pattern on the single word **"auditability"** ("maintaining
  strict human-in-the-loop control, auditability, and
  governance"). This is the **Asato precedent** from the original
  pass, which UNION-SPEC already records in the same terms. The
  claim stands at that weight; the audit core does not rest on
  it (four original siblings claim audit logging explicitly, and
  Core 10 is baseline plumbing regardless).

## 3. Core-delta decisions

Both claimed families already have dispositions in UNION-SPEC:

| Claimed family | Disposition | Core delta |
|---|---|---|
| Agentic & automated workflow automation | Extended — domain automation engines that run on top of the platform; the agents themselves are inference | **Carried** — no change; the family's platform side (gateway + labeled reference stub) is already Core 3 |
| Audit logging & trails | Core 10 — append-only audit log | **Carried** — no change |

**Result: the core is unchanged.** No function the newcomer
claims presupposes a records form or platform function the build
lacks: its automation surface arrives through the gateway as
prompt traffic answered by the deterministic reference responder
— labeled `reference_stub: true` with the pinned notice, never a
learned model — and its audit surface is the audit log the build
already keeps. `src/` is byte-identical to the shipped build
(`src/aigateway/store.py` SHA-256
`4a2b74e47fffd731b0bf92dbb1266bf87f0641ee22601bb143a1f3d6807b0e3f`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction. The group's central honesty position is likewise
unchanged by the newcomer: what Gobo sells (cognitive automation,
agents, semantic analysis) is inference, and this build contains
no learned model — §5 sizes that gap with Gobo included.

## 4. Updated union statement

The group now covers **12 forks** (11 original siblings + 1
remainder addition), **47 claims** in total (45 + 2), with **12
of 12** forks carrying at least one claim. The merged build
remains the same 10-function AI-platform substrate — model and
template registries, gateway with a labeled reference responder,
metering and quotas, conversation and request records with a
zero-persistence mode, policy guardrail hooks, evaluation
harness, REST API, access control with API keys, append-only
audit — now spec'd against 12 marketplace offerings instead of
11. The ranking shifts only in shares: learned inference stays
the largest family at 8 of 12 (67%, was 73%), multi-tenancy is 6
of 12, and audit logging and agentic workflows each rise to 5 of
12. The newcomer's character is worth stating plainly: it is an
IT-infrastructure automation product filed by the census into the
AI category on its own AI wording — the same filing shape as the
original pass's AWS and Stell sheets, except that where those two
tagged only multi-tenancy, Gobo's automation wording is dense
enough to claim the agentic family outright.

## 5. Gaps — for the registry at ship

**New gap functions** (3), all fork excess beyond the taxonomy —
functions Gobo's description asserts in its own words that no
family names:

- **Infrastructure Digital Twin & infrastructure performance
  management engine** — deep, continuous visibility into IT
  ecosystems; real-time performance tracking to optimize network
  operations and ensure system availability (Gobo IDT)
- **Service transition management** — structured migration
  planning and tracking for critical mandates (the description's
  example is the IPv6 transition), with automated configuration
  management and capacity planning as the description groups
  them (Gobo)
- **EIS service management suite** — GSA Enterprise
  Infrastructure Solutions oversight: monitoring how well
  telecommunications providers meet promised service levels,
  CLIN and invoice management (line-item tracking, invoice
  reconciliation, dispute-resolution support), continuous SLA
  and service inventory lifecycle management, and recovery of
  service-provider credits (Gobo fork excess — a
  telecom-contract administration vertical)

**Existing gaps gaining members:**

- **Agentic & automated workflow engines** (already Extended
  under Group 9) — **+1 claimant**: Gobo, the family's fifth
  claimant of 12; its I2Apps automation surface is exactly this
  engine class, and the build's side of it remains the gateway
  plus the labeled reference stub.
- **Learned AI/ML inference** (already Extended under Group 9 —
  the group's #1 family and the final batch's largest single
  item) — **+1 by substance, explicitly not a claimant**: Gobo's
  semantic intelligence and its public comment analysis /
  regulatory review workload are inference, recorded here so the
  final batch sizes the inference gap with Gobo's substance
  included even though the family claim did not fire on its
  adjectives (§2).
- **Document processing & generation** — explicitly gains **no**
  claimant: "Invoice Management" is not the family's "invoice
  processing" pattern, and Gobo's invoice handling is recorded
  once, under the EIS suite gap above.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and appended
  position, membership against `remainder.json`, the literal
  claim table, the zero-claim family set (the other 14 families),
  verbatim evidence, the census citation, the near-miss pins, and
  the group totals (see `tests/test_additions.py`).
- The fork is exercised against the substrate in the same tests:
  an EIS-flavored automation invocation through the gateway
  (rules responder; output is the configured response, labeled
  `reference_stub: true` with the pinned `REFERENCE_NOTICE`,
  metered, and audited) and a human-in-the-loop case (an input
  policy rule blocks an "unreviewed" automation prompt; exactly
  one `blocked_input` record is stored, nothing completes, and
  the audit trail carries the `invoke_blocked` entry — the audit
  claim's Core side).
- **Tests: 146 → 157, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `AIGatewayStore.
  _first_policy_match` in `src/aigateway/store.py` was patched
  to `return None` as its first statement (the exact mutant of
  `tests/test_negative_control.py` — every text treated as
  clean) and the full suite ran — **157 tests, exactly 15
  failures**: the shipped drill's 14 (8 in test_policy, 2 in
  test_negative_control, 1 in test_gateway, 1 in test_service, 2
  in test_records) plus exactly 1 from the new additions module
  (the human-in-the-loop block case), tripping exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
