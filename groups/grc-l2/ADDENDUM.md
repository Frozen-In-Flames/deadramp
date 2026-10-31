# Addendum — Governance, Risk, and Compliance (GRC), CMMC L2: the 5 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 5
previously uncategorized forks of remainder build unit
**`addition:grc-l2`** (see `../../REMAINDER.md`). The original union
spec stands as written: its taxonomy, its 10-function core, and its
control baseline are **unchanged**. This document records what
joined, what the newcomers claim under the group's existing
taxonomy, the core-delta decision for every claimed function, and
the updated union statement.

**Headline: forks spec'd 5 / 5; 13 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 118 → 132, all
passing; both of the group's named absences are retired** —
`risk_management` and `policy_management`, which stood at 0 of 2
in the original spec *because unclaimed*, are claimed by the
newcomers, with the consequences worked out in §3. **7 new gap
functions** are named in §5, and 4 already-registered gaps gain
claimants.

## 1. Membership and method

The 5 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2620235600` | Anecdotes / Anecdotes |
| 2 | `FR2621445678` | Halo / Halo |
| 3 | `FR2607537684` | Kovr.ai / Kovr Nova |
| 4 | `FR2004146362` | MediaLab, Inc. / MediaLab Federal |
| 5 | `FR1726564822` | Workiva / Workiva Platform |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **imports the original `scratch/extract.py`'s taxonomy and
  asserts its literal copy of the (id, label, regex) triples equal
  to the original's before tagging** — the taxonomy was applied
  verbatim, not re-tuned for the newcomers. Same sentence
  splitting, same evidence rule (first matching sentence per
  family, stored verbatim), same sheet schema. The 5 sheets are
  **appended** to `specs/specs.json` after the original 2, which
  are byte-for-byte untouched (the file re-serializes identically
  for the original entries and is byte-preserved through the
  second sheet's closing brace; verified in the build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 5
  descriptions were present; no live fetching. All 5 are FedRAMP
  **Moderate** (Kovr Nova's authorization status is Legacy
  FedRAMP Ready; its impact level is Moderate), so the group
  stays single-tier and the L2 baseline is inherited in full
  (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **8
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **8 / 8 verify** as verbatim
  substrings.
- **No exclusion trap applies to the newcomers.** Unlike the
  original CGC sheet, none of the 5 records carries a
  hosted-services block: every record's `certified_services`
  field is empty and no "not authorized" segment exists in any of
  the 5 descriptions (asserted in the extractor). Only
  `service_desc` was matched, per house method.

## 2. What the additions claim

**13 claims** across the 5 forks; all 5 carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 2 + additions = 7 forks) alongside:

| Function | Additions claiming | Group total (7) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Continuous monitoring | 3 | 4 | **Core** — results/findings recorded; feeds Extended |
| Risk management | 3 | 3 | **Named absence retired** — records Core; scoring engines Extended |
| Control & framework compliance management | 2 | 3 | **Core** — catalog registry |
| Policy management | 2 | 2 | **Named absence retired** — records Core; lifecycle engine Extended (new gap) |
| Compliance posture reporting & dashboards | 1 | 2 | **Core** — counts only, no scores |
| Workflow & automation | 1 | 2 | **Core** seed — enforced lifecycles; engines Extended |
| APIs & integrations | 1 | 2 | **Core** — REST API |
| Evidence management & validation | 0 | 1 | **Core** — evidence registry |
| Security indicators (KSI) tracking & validation | 0 | 1 | **Core** — indicator registry |
| Vulnerability & remediation management | 0 | 1 | **Core** — finding records |
| Assessment & authorization support | 0 | 2 | **Core** — assessment & authorization records |
| Audit support & assessor review | 0 | 1 | **Core** — append-only audit |
| Platform hosting / enclave operations | 0 | 2 | Platform layer |
| Identity & access controls (hooks) | 0 | 1 | **Core** — RBAC |

Per-fork claim counts: Anecdotes **4**, Kovr Nova **4**, Halo
**2**, Workiva **2**, MediaLab **1**. The full per-fork table is
pinned literally in `tests/test_additions.py` (`EXPECTED_CLAIMS`).

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Anecdotes** — "automates evidence collection" is not
  `evidence_management` (the family requires validation /
  artifacts phrasing); "Continuous Control Monitoring" is not
  `continuous monitoring` (adjacency), and the "FedRAMP 20x
  Class C (Moderate) Certification" sentence is not
  `assessment_authorization`'s "FedRAMP 20x authorization";
  "automate workflows" (its agents) is not `workflow_automation`
  phrasing. Its `continuous_monitoring` claim rests on "replacing
  point-in-time assessments with continuous monitoring".
- **Halo** — "Key Security Indicator validation" (singular) is
  not `ksi_tracking`'s plural "Key Security Indicators", and no
  "KSI" token appears; "Ongoing Authorization deliverables" is
  not an `assessment_authorization` phrase; in the GRC-module
  sentence, "Plan of Action and Milestones (POA&M) tracking",
  "asset inventory", "deviation management", "OSCAL-based system
  documentation", and "cross-framework control mapping" match no
  family (the `risk_management` claim rests on "vulnerability
  and risk management" in the same sentence — and POA&M records
  are Core 5 regardless: the `vulnerability_remediation` pattern
  requires "remediation tracking" or "vulnerability
  lifecycle/scanning/posture"). "workflow automation" and
  "security workflows" are not `workflow_automation` phrasing;
  "user access management" is not `identity_access_hooks`;
  "executive dashboards" is not `posture_reporting` ("monitoring
  dashboards" required).
- **Kovr Nova** — The group's most authorization-focused product
  claims **no** `assessment_authorization`: it writes
  "Authorization to Operate (ATO)", never the taxonomy's
  "Authority to Operate", and neither "authorization readiness"
  nor "assessor" appears ("assessment responses", "Security
  Assessment Reports" are not `assessor`). "evidence
  processing", "accelerate evidence collection", and "automated
  evidence ingestion" are not `evidence_management`;
  "integrated POA&M lifecycle tracking … real-time visibility
  into remediation status" is not `vulnerability_remediation`
  ("remediation tracking" required); "Pre-built connectors" is
  not `api_integrations` (no API / integration token).
- **MediaLab Federal** — "Role-based permissions" is not
  "role-based access control" (`identity_access_hooks`);
  "inspection readiness" is not "authorization readiness";
  "competency assessment" contains no `assessor`. Everything
  else in its description is healthcare-quality surface (see §5).
- **Workiva** — "a full audit trail" is not `audit_support`
  (the family requires audit-ready / assessor-review / audit-
  support phrasing); "granular permissions" is not
  `identity_access_hooks`; "real-time reports and dashboards"
  is not `posture_reporting`; "evidence requests" is not
  `evidence_management`; "Compliance made simple — streamline
  documentation" is not adjacent "compliance documentation";
  "helps mitigate risk" matches no risk pattern (the
  `risk_management` claim rests on "Manage risk assessments,
  evidence requests, issues, and findings").

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the group's
law, applied verbatim:

- **Kovr Nova, `risk_management`** fires on the framework **name**
  "DoD Risk Management Framework (RMF)" inside its
  supported-frameworks list. The claim stands; its functional
  risk substance is thinner than Halo's ("vulnerability and risk
  management" as offered functionality) or Workiva's ("Manage
  risk assessments"), and the family's records disposition in §3
  does not depend on the distinction.
- **Anecdotes, `policy_management`** fires via the family's bare
  `\bpolicies\b` alternative, on "maps controls across 60+
  industry frameworks and custom policies". The sentence's
  substance is control↔framework/policy *mapping* — which is
  exactly the records form §3 assigns it — but the family label
  is broader than the sentence, and that is recorded here rather
  than tuned away.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC **except the two former named absences**, which are
decided here. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Continuous monitoring (3) | Core 3/4 — indicator results and findings are the monitoring record | **Carried** — no change |
| Control & framework compliance management (2) | Core 1 — framework & control catalog registry | **Carried** |
| Compliance posture reporting & dashboards (1) | Core 7 — posture computed on read, counts only | **Carried** |
| Workflow & automation (1) | Core seed — enforced record lifecycles (findings, authorizations) | **Carried** — execution engines stay Extended |
| APIs & integrations (1) | Core 8 — the service is a REST API | **Carried** — connector engines are a new gap (§5) |
| Risk management (3) | **Named absence in UNION-SPEC — retired by this addendum** | **Carried as records** — see below |
| Policy management (2) | **Named absence in UNION-SPEC — retired by this addendum** | **Carried as records; lifecycle engine is a new gap** — see below |

**The two retired absences, decided plainly.** UNION-SPEC named
risk management and policy management as absences *because
unclaimed* — "not built, not a gap". The newcomers claim both, so
the absence rationale no longer holds and each family gets the
standard treatment: a claim buys its records form, engines are
Extended.

- **Risk management** (Halo, Kovr Nova, Workiva). The records
  forms already exist: risk assessments are **assessment
  records** (Core 6), issues and findings are **finding records**
  (Core 5), and Halo's POA&M tracking is the finding lifecycle
  itself (Core 5). No risk-register object is added, and —
  per the standing category discipline — **no risk score is
  computed anywhere**: the additions' risk prose defines no
  score, the posture surface stays counts-only (pinned
  recursively by the additions tests), and the scoring remainder
  stays the already-Extended *posture / risk scoring engines*
  gap. Carried.
- **Policy management** (Anecdotes, MediaLab). The records forms
  already exist: Anecdotes' control↔policy mapping runs through
  the **catalog registry** (Core 1 — a custom policy set is a
  catalog framework with its controls), and MediaLab's policy
  documents are **evidence records** (Core 4 — metadata +
  SHA-256, reviewer-set validation status). What the Core does
  not hold is a policy *lifecycle* — authoring, approval
  workflow, enforcement — which is not a records form but an
  engine: it becomes a new Extended gap in §5. Carried as
  records; gap for the engine.

**Result: the core is unchanged.** No function the 5 claim
presupposes a records form the build lacks. `src/` is
byte-identical to the shipped build (`src/grc/store.py` SHA-256
`e2eac653fb99f97b2a8348f0814eb2b65caa3fc6da0e4103897da67ff3369eeb`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **7 forks** (2 original siblings + 5
remainder additions), **27 claims** in total (14 + 13), with
**7 of 7** forks carrying at least one claim. The merged build
remains the same 10-function GRC records substrate — framework &
control catalog, governed-system registry, indicator registry,
evidence registry, finding/POA&M records, assessment &
authorization records, counts-only posture, REST API, RBAC,
append-only audit — now spec'd against 7 marketplace offerings
instead of 2. The group's character changes: the original union
was one genuine GRC platform (XBU40) plus a hosting enclave
(CGC); the additions are mostly GRC products in their own right
(Anecdotes, Kovr Nova, Workiva, and Halo's GRC module), plus one
healthcare-quality platform (MediaLab) whose only GRC-family
surface is the policy-document claim. Both named absences are
retired; the union's no-score discipline is unchanged and is now
pinned against the risk claims as well.

## 5. Gaps — for the registry at ship

**New gap functions** (7):

- **Policy lifecycle management engine** (authoring, approval
  workflow, enforcement of policies) — Anecdotes, MediaLab
  Federal, from the retired-absence `policy_management` claims
- **Agentic workflow execution engine** (agents executing GRC
  workflows end to end) — Anecdotes
- **AI control-narrative & assessment-response generation
  (secure AI enclave)** — Kovr Nova (Artemis)
- **Data-integration connector engine** (system-to-system
  connectors and sync) — Workiva (agency information-system
  connections); Kovr's pre-built connectors are counted under
  the evidence-collection gap below
- **IT service management suite (ITSM / ESM)** — Halo fork
  excess beyond the GRC taxonomy: CMDB, change & incident
  management, SLA tracking, self-service portals
- **Healthcare quality management suite** — MediaLab fork
  excess: continuing education & training, competency
  assessment, personnel files & certifications, non-conforming
  event management, instrument maintenance
- **Connected financial & regulatory reporting / publishing
  platform** — Workiva fork excess (connected reporting and
  report publishing)

**Existing gaps gaining claimants:**

- **Automated evidence-validation engine (API/telemetry
  collection)** — +2 by substance: Kovr Nova (automated evidence
  ingestion, evidence processing), Anecdotes (automated evidence
  collection). The collection remainder of the evidence function,
  already Extended; neither fork's `evidence_management` family
  claim fired, recorded in §2.
- **Continuous-monitoring feeds & scanner integrations** — +3:
  Anecdotes, Halo, Kovr Nova (the additions' continuous-
  monitoring claimants; their outputs land in Core 3/4 records).
- **Automated KSI validation** — +1 by substance: Halo (KSI
  validation; the `ksi_tracking` family claim itself did not
  fire on the singular wording, recorded in §2).
- **FedRAMP package generation** — +1: Kovr Nova (SSP / SAR /
  POA&M / SRTM artifact generation from system documentation).
- **Posture / risk scoring engines** — explicitly gains **no**
  claimants from the additions' risk claims: the claims buy
  records verbatim, and nothing in the 5 descriptions
  presupposes a computed score.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim family set, verbatim evidence, the
  near-miss pins, and the retired-absence claimant sets (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: catalog registration of a custom framework/policy
  set with a recorded indicator result (Anecdotes); the POA&M
  finding lifecycle with read-time overdue derivation (Halo);
  assessment + authorization records and an artifact evidence
  record with verify-by-content (Kovr); a policy document as an
  evidence record with reviewer-set status and the filer's
  review denied (MediaLab); risk-assessment, issue, and
  evidence-request records under a recursively score-free
  posture (Workiva).
- **Tests: 118 → 132, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `derive_finding_status`
  in `src/grc/store.py` was patched so the overdue branch never
  fires (`if _coerce_as_of(as_of) > due:` → `if False:`) and the
  full suite ran — **132 tests, 10 failures**: the original
  drill's 8 (findings derivation ×3, negative control ×3,
  posture counts, service full flow) plus 2 from the new
  additions module (the Halo POA&M derivation case and the
  Workiva posture-overdue case), which trip on the mutant
  exactly as designed. `store.py` was restored from the
  pre-mutation copy and verified SHA-256-identical to the
  shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`.
