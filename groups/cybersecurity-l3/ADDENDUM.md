# Addendum — Cybersecurity & Risk Management, L3-adjacent: the 2 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 2
previously uncategorized forks of remainder build unit
**`addition:cybersecurity-l3`** (see `../../REMAINDER.md`). The
original union spec stands as written: its 25-function taxonomy,
its 11-function core, its High-baseline uplift, and its baseline
gaps are **unchanged**. This document records what joined, what the
newcomers claim under the group's existing taxonomy, the
core-delta decision for every claimed function, and the updated
union statement.

**Headline: forks spec'd 2 / 2; 14 new claims (15 raw matches, 1
dropped as a wording artifact); core delta — zero functions
extended, `src/` byte-identical; tests 236 → 247, all passing.**
No named absence is affected: the group's three zero-claim
families (`fraud_identity`, `app_security`, `log_telemetry`) and
its zero-claim fork (NetCloud Federal) remain exactly as shipped,
and the High platform baseline gaps (IA-2/IA-5, SC-13, SC-28,
AU-11, AC-11/AC-12) are unchanged. **3 new gap functions** are
named in §5, and 7 already-registered gaps gain claimants.

## 1. Membership and method

The 2 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2304757473A` | Cisco Systems Inc. / Cisco Security Cloud for Government |
| 2 | `FR1714261912` | XTec, Incorporated / AuthentX Cloud |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the taxonomy out of the original
  `scratch/extract.py` via `ast` (never executed, never re-typed)
  and applies it verbatim** — same sentence splitting, same
  evidence rule (first matching sentence per family, stored
  verbatim, truncated at 400 characters), same sheet schema.
  Before tagging anyone new, the extractor **re-runs the original
  method over the original 16 forks and asserts their
  `functions_claimed` arrays deep-equal the shipped sheets** —
  taxonomy, method, and the original corrections table reproduced
  exactly (the self-proof runs on every invocation and passed).
  The 2 sheets are **appended** to `specs/specs.json` after the
  original 16, which are byte-for-byte untouched (pure append:
  +108 lines, 0 deletions; deep-equality verified in the build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. Both
  descriptions were present; no live fetching. Both forks are
  FedRAMP **High** (Certified), so the group stays single-tier
  and the High baseline is inherited in full (Merge Rules 1–2),
  unchanged.
- The census starting point was verified, not trusted: both
  **census citations** for these forks (1 each, from
  `../../remainder/class_all.json`) were re-checked against the
  forks' own cached descriptions and **2 / 2 verify** as verbatim
  substrings (pinned by test).
- **No exclusion trap applies to the newcomers.** Neither
  record carries a hosted-services block: both records'
  `certified_services` fields are empty and no "not authorized"
  segment exists in either description (asserted in the
  extractor). Only `service_desc` was matched, per house method.
- Registry note: Cisco Security Cloud for Government exists in
  the source under two FedRAMP IDs (the census's duplicate-pair
  list); the untiered sibling record is a different build unit
  and is not part of this addition. This addendum covers the
  High record `FR2304757473A` only.

## 2. What the additions claim

**14 claims** across the 2 forks; both carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 16 + additions = 18 forks) alongside:

| Function | Additions claiming | Group total (18) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Identity, authentication & privileged access | 2 | 9 | Extended — identity products proper; access-control *hooks* are Core |
| Network security, segmentation & zero-trust access | 1 | 4 | Extended — network enforcement planes |
| Insider risk, DLP & data security | 1 | 4 | Extended — DLP engines |
| AI/ML-powered analytics & anomaly detection | 1 | 4 | Extended — detection models and AI engines |
| APIs & integrations | 1 | 4 | **Core** — API-first platform surface |
| Dashboards, reporting & analytics | 1 | 7 | **Core** — posture reporting |
| Access control & least privilege (platform feature) | 1 | 5 | **Core** — access control (uplifted at High) |
| Threat detection, SOC & managed response | 1 | 3 | **Core substrate** — ingestion/triage; engines and SOCs Extended |
| Threat intelligence | 1 | 3 | Extended — intel feeds and curation |
| Asset inventory, visibility & attack surface | 1 | 3 | **Core** — asset inventory |
| Automation & orchestration | 1 | 3 | Extended — SOAR and workflow engines |
| Encryption & key management | 1 | 3 | Platform note — TLS when configured; FIPS-validated cryptography is a baseline gap at High (SC-13) |
| Phishing defense & security awareness training | 1 | 2 | Extended — phishing defense is inline enforcement at this tier (the Zscaler precedent in UNION-SPEC) |

Per-fork claim counts: Cisco Security Cloud for Government
**12**, AuthentX Cloud **2**. The full per-fork table is pinned
literally in `tests/test_additions.py` (`EXPECTED_CLAIMS`).

### The one correction (wording artifact, dropped)

Group 4's discipline, applied as in the original pass: a claim
stands only when the matched text asserts a customer-facing
function **of the offering itself** — and the function the family
names.

- **Cisco Security Cloud for Government — dropped
  `endpoint_management`.** The family's only match is "delivers
  cloud-native firewall policy and device management through a
  unified management plane" (Security Cloud Control — Firewall
  Management). The "device management" asserted there manages
  **firewall appliances** (the NGFW fleet the same component
  orchestrates) — a network-security function the offering
  already claims under `network_security`, not endpoint
  management, patching, or IT automation of endpoints. The
  matched term names the wrong function (the class of the
  original pass's Idira bare-"firewall" drop). The sentence
  remains in the sheet's description; the claim does not, and
  the absence is pinned by test. The firewall *management plane*
  itself is a real surface the taxonomy has no family for; it
  is registered as a new gap in §5.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Cisco** — `compliance_grc` never fires despite pervasive
  compliance prose: "ensuring protection and compliance for
  government agencies", "beyond the governance and compliance
  benefits", and Duo's "satisfy NIST 800-63-3 and 53/63/171
  authentication requirements" contain none of the family's
  phrases (no compliance automation / platform / management /
  posture / program, no "governance, risk, and compliance").
  `cloud_saas_security` never fires although **CASB is named
  twice** (the Umbrella suite sentence and the Secure Access
  capability list): the family requires posture / CSPM / CNAPP /
  SSPM / misconfiguration phrasing, and a bare CASB names none
  of it — the substance is recorded under §5 as a by-substance
  enlargement. `vuln_management`: Duo's "prevents modern
  attackers that often target … the exploitation of known
  software vulnerabilities affecting outdated software versions"
  casts vulnerabilities as the attacker's vector, not a
  scanning or management function. `endpoint_detection`:
  "Advanced Malware Protection" in the Secure Access list is
  malware protection with no EDR / endpoint-detection phrase.
  `audit_logging`: no audit token appears anywhere; the "SAL
  Eventing License Utilization Dashboard" is licensing telemetry,
  not an audit trail. Access-control substance beyond the
  evidence sentence: Security Cloud Control's "Roles are
  assigned to these users and groups to define their privileges
  for administering Security Cloud Control and the integrated
  products" is RBAC in substance but matches no pattern token
  ("role-based access" never appears); the
  `access_control_feature` claim rests on Secure Access's
  "streamlines policy enforcement", as tagged.
- **AuthentX** — `compliance_grc` never fires: the description
  is HSPD-12 / FICAM / OMB mandate prose ("aligned with federal
  mandates and high assurance requirements") with none of the
  family's phrases. `access_control_feature` never fires: the
  offering is "identity, credential and access management" and
  endpoints are "securely accessible", but "access control"
  never appears — the substance is claimed under
  `identity_access`, the family's parent discipline.
  `fraud_identity` never fires: enrollment and issuance (the
  AuthentX Enrollment Manager, enrollment and issuance
  peripherals, the Luna Credential System) is PIV credentialing
  in substance, but no proofing / verification phrase ("verify
  identities", "identity proofing") appears.
  `endpoint_management` never fires: "provisioning, configuring,
  monitoring, and patching are all performed by U.S.-based Luna
  as a Service engineers" is vendor-side administration of the
  HSM appliance, not a customer endpoint-management function.
  `data_protection` never fires: "generate, store, protect and
  manage cryptographic keys used to secure sensitive data" never
  forms the contiguous phrase, and its substance is claimed
  under `encryption_feature`.

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the
group's law, applied verbatim:

- **Cisco, `api_integration`** fires on "integration with CISA
  Protective DNS" — an integration with a named external
  service, which is what the family's pattern literally tags.
  Stronger API substance exists later in the same description
  ("integrated as an API-based supplemental control", Secure
  Email Threat Defense), but evidence is the first matching
  sentence by the group's method, and the claim's Core
  disposition (§3) does not depend on the distinction.
- **Cisco, `reporting_dashboards`** evidence is "real-time
  visibility into traffic and threats" — the pattern's
  real-time-visibility alternative. A literal dashboard ("a
  summary dashboard for customers") appears later in the same
  component's prose; the Core 8 disposition is the same either
  way.
- **Cisco, `ai_ml`** evidence is "powered by Cisco Talos and
  AI, enable real-time threat detection, behavioral analysis" —
  prose asserting AI-powered detection by the offering. This is
  not the original pass's Armory case (bare "AI" inside a
  dependent product's *name*, dropped): here AI is asserted as
  the mechanism of a described capability, and the claim stands
  at the family's Extended weight.
- **AuthentX, `encryption_feature`** is a platform-note family,
  and the note cuts both ways: the fork's Luna HSM is "FIPS
  140-2, Level 3 certified" — that certification is the *fork's*
  platform property. It does not transfer to this build, whose
  SC-13 gap (Python's hashlib is not a FIPS-validated module)
  stands exactly as UNION-SPEC records it.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Asset inventory (1) | Core 1 — asset registry; discovery output lands as asset records | **Carried** — no change |
| Threat detection / response (1) | Core substrate 2/3 — ingestion & triage of detection output | **Carried** — engines stay Extended |
| Dashboards / reporting (1) | Core 8 — posture computed on read, counts only | **Carried** |
| Access control feature (1) | Core 10 — RBAC, uplifted at High (auditor role, AC-7) | **Carried** — the claim buys the hooks, not an IdP |
| APIs & integrations (1) | Core 9 — the service is a REST API | **Carried** — connector engines stay Extended |
| Identity & access (2) | Extended — IdP / PAM / IGA / MFA engines | **Carried** — hooks only, per the original scoping |
| Network security (1) | Extended — network enforcement planes | **Carried** — output lands as findings |
| Insider / DLP (1) | Extended — DLP engines | **Carried** — alerts land as findings |
| AI/ML (1) | Extended — detection models | **Carried** — no model enters; scoring stays the declared deterministic formula |
| Threat intelligence (1) | Extended — intel feeds & curation | **Carried** |
| Automation (1) | Extended — SOAR / workflow engines | **Carried** |
| Phishing defense (1) | Extended — inline enforcement at this tier (UNION-SPEC precedent) | **Carried** |
| Encryption & key management (1) | Platform note — TLS when configured; SC-13 gap | **Carried** — the fork's FIPS-certified HSM is not inherited |

**Result: the core is unchanged.** No function either fork
claims presupposes a records form the build lacks, and neither
fork claims `risk_scoring`: no computed score enters with the
additions — the only scores in the enlarged group remain Core
4's declared severity × criticality formula and Core 5's
likelihood × impact register, and posture stays counts-only
(the additions tests pin the deterministic score and the
counts-only posture over the new forks' records). `src/` is
byte-identical to the shipped build (`src/cyber/store.py`
SHA-256
`1e58d852abd4b06f76c49c1bb2bccd714c23aeacfcbfb597493c8931bd9bcd90`
before and after this addendum's work, the mutation drill
included; the full `src/` diff against HEAD is empty). The
tier baseline does not change: same tier by construction, and
the High uplifts (hash-chained fail-closed audit, audit query,
AC-7 lockout, auditor role) are exercised over the additions'
records by the new tests.

## 4. Updated union statement

The group now covers **18 forks** (16 original siblings + 2
remainder additions), **74 claims** in total (60 + 14), with
**17 of 18** forks carrying at least one claim — NetCloud
Federal remains the group's only zero-claim fork. The merged
build remains the same 11-function defensive substrate at the
High baseline, now spec'd against 18 marketplace offerings
instead of 16. The group's character deepens in its stated
direction: this was an **identity-and-boundary group**, and the
additions extend both halves — `identity_access` reaches 9 of
18 forks (half the group: AuthentX is a pure ICAM platform and
Duo rides inside Cisco's suite), and Cisco's suite is the
broadest single claim set in the group (12 claims against an
original maximum of 7), spanning the boundary families
(network security, DLP, threat intelligence, detection,
automation) that sit Extended around the substrate. Per-claimant
engines still do not become shared substrate at this tier; the
no-score discipline and the High baseline gaps are unchanged.

## 5. Gaps — for the registry at ship

**New gap functions** (3):

- **Firewall management & orchestration plane** — Cisco
  Security Cloud Control, Firewall Management for Government:
  cloud-native firewall policy & device management console,
  NGFW (ASA / FTD) orchestration across hybrid environments,
  zero-touch provisioning, AIOps Policy Analyzer & Optimizer.
  (The surface whose "device management" wording produced the
  §2 correction: an engine, with no taxonomy family.)
- **HSM as a Service (cloud HSM & key-management service)** —
  AuthentX Luna as a Service: dedicated and managed HSM models,
  hosted Luna Credential System. A customer-facing cryptographic
  service — distinct from the substrate's SC-13 platform gap,
  which stands.
- **Inline email security platform** — Cisco Secure Email
  Threat Defense: AI-powered email threat detection, BEC /
  phishing / QR-code (quishing) detection, deployed as an
  API-based supplemental control or inline gateway. The
  `phishing_awareness` family's previously registered extended
  function is simulation / training *content*; inline
  enforcement engines are named separately here (Zscaler's
  original claim was recorded at the same enforcement weight).

**Existing gaps gaining claimants:**

- **Network enforcement planes** — +1: Cisco (DNS-layer
  security, secure web gateway, cloud-delivered firewall / IPS,
  FWaaS, SSE / SASE / ZTNA, Multicloud Defense) — the largest
  network-security surface in the enlarged group.
- **Identity products (IdP / PAM / IGA / MFA engines)** — +2:
  Cisco (Duo Federal MFA, device-trust checks at access time)
  and AuthentX (the ICAM platform itself: PIV enrollment,
  issuance, and credential lifecycle under HSPD-12 / FICAM).
- **DLP engines** — +1: Cisco (Umbrella and Secure Access DLP).
- **AI/ML detection models** — +1: Cisco (Talos- and AI-powered
  detection, AIOps anomaly detection, AI-powered email
  detections).
- **Threat-intel feeds & curation** — +1: Cisco (Talos Threat
  Intelligence, CISA Protective DNS integration).
- **SOAR / workflow automation engines** — +1: Cisco (firewall
  orchestration, automated policy and object updates).
- **Cloud / SaaS posture engines** — +1 *by substance*: Cisco's
  CASB, named in two component descriptions; the
  `cloud_saas_security` family claim itself did not fire on the
  wording (recorded in §2).
- **Posture / risk scoring engines** — explicitly gain **no**
  claimants: neither addition claims `risk_scoring`, and
  nothing in either description presupposes a computed score
  beyond the substrate's declared deterministic formula.

**Platform baseline gaps at High — unchanged:** MFA /
authenticator management (IA-2(1)/(2), IA-5 — AuthentX and Duo
*are* that layer as products; the substrate's own missing
authentication remains the gap), FIPS-validated cryptography
(SC-13), encryption at rest (SC-28), audit retention (AU-11),
session lock / termination (AC-11 / AC-12).

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the literal
  per-fork claim table, the group totals (18 forks, 74 claims,
  one zero-claim fork), the pinned correction (Cisco
  `endpoint_management` absent while its sentence remains), the
  named near-miss absence set, verbatim evidence, and the
  census citations (see `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: asset registration with criticality-driven
  rescoring and counts-only posture rollups over its findings
  (Cisco); finding ingestion, lifecycle, and search under its
  own product attribution with the hash-chained audit verifying
  after its operations (both forks); and the AC-5 boundary —
  the trail AuthentX-attributed operations produced is
  queryable, and the auditor (audit_read and nothing else) is
  denied the ingest itself (AuthentX: its identity claims buy
  hooks, not an IdP; dana's audit-read reach itself is pinned
  by the shipped suite).
- **Tests: 236 → 247, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `score_finding` in
  `src/cyber/store.py` was patched to the severity-blind mutant
  (`score = 1 * CRITICALITY_WEIGHTS[criticality]`, Group 4's
  exact mutant) and the full suite ran — **247 tests, 33
  failures**: the shipped drill's 30 plus exactly 3 from the
  new additions module (both forks' substrate cases and the
  AuthentX auditor case, tripping on the deterministic-score
  assertions exactly as designed). `store.py` was restored
  from the pre-mutation copy and verified SHA-256-identical to
  the shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
