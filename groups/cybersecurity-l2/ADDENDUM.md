# Addendum — Cybersecurity & Risk Management, CMMC L2: the 18 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 18
previously uncategorized forks of remainder build unit
**`addition:cybersecurity-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 11-function
core, its control baseline, and its Extended dispositions are
**unchanged**. This document records what joined, what the newcomers
claim under the group's existing taxonomy, the core-delta decision
for every claimed function, and the updated union statement.

**Headline: forks spec'd 18 / 18; 67 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 194 → 204, all
passing; no new gap functions** (thirteen already-registered
Extended gaps gain claimants, listed in §5).

## 1. Membership and method

The 18 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2104942200` | Acuant, Inc. / Connect, Ozone, & Facial Recognition System (COFRS) |
| 2 | `FR2031936863` | Armis Federal LLC / Armis FedRAMP Edition (AFE) |
| 3 | `FR1814168113` | Authentic8, Inc. / Silo |
| 4 | `F1605107897` | Cisco Systems Inc. / Cisco Cloudlock for Government |
| 5 | `FR1823149273` | Duo Security (a Cisco Company) / Duo Federal |
| 6 | `FR1829538820` | General Services Administration / Login.gov |
| 7 | `FR1718334757` | ID.me / ID.me Identity Gateway |
| 8 | `F1511167634` | Kiteworks USA, LLC / Kiteworks Federal Cloud |
| 9 | `F1512167750` | Okta / Okta IDaaS Regulated Cloud |
| 10 | `F1301101857` | OpenText / OpenText™ Core Application Security (Fortify On Demand) |
| 11 | `FR2301844932` | Orca Security / Orca Cloud Security Platform |
| 12 | `FR1913470600` | Palo Alto Networks, Inc. / Palo Alto Networks Government Cloud Services |
| 13 | `FR1720461312` | Proofpoint, Inc. / Proofpoint Email and Information Protection Service |
| 14 | `FR1819168894` | Proofpoint, Inc. / Proofpoint Targeted Attack Protection |
| 15 | `F1508207205` | Qualys / Qualys Cloud Platform |
| 16 | `FR1821062403` | Saviynt, Inc. / Saviynt Enterprise Identity Cloud (EIC) |
| 17 | `FR2110342613` | Tanium / Tanium Cloud for US Government (TC-USG) |
| 18 | `FR1731347234` | Zimperium / Zimperium Mobile Endpoint Cyber Security |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`, a
  copy of the group's original `scratch/extract.py` restricted to
  these 18 IDs. The script **asserts its taxonomy triples (id,
  label, regex) equal the original's before tagging** — the
  taxonomy was applied verbatim, not re-tuned for the newcomers.
  Same sentence splitting, same evidence rule (first matching
  sentence, truncated at 400 chars), same sheet schema. The 18
  sheets are **appended** to `specs/specs.json` after the original
  54, which are byte-for-byte untouched (the file re-serializes
  identically for the original entries; verified in the build).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 18
  descriptions were present; no live fetching. All 18 are FedRAMP
  **Moderate**, so the group stays single-tier and the L2 baseline
  is inherited in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **26
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **26 / 26 verify** as verbatim
  substrings (whitespace-normalized — the raw dump wraps lines
  mid-sentence; one Acuant citation verifies only under that
  normalization and is recorded as such in
  `scratch/additions_citation_check.json`).

## 2. What the additions claim

**67 claims** across the 18 forks; 15 of 18 carry at least one
claim. The unit is identity-heavy: 7 of the 18 claim
`identity_access`, and six are primarily identity offerings
(Acuant, Duo, Login.gov, ID.me, Okta, Saviynt). Claim counts per
family among the additions, with the group's combined count
(original 54 + additions = 72 forks) alongside:

| Function | Additions claiming | Group total (72) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Identity, authentication & privileged access | 7 | 15 | Extended |
| APIs & integrations | 6 | 25 | **Core** |
| AI/ML-powered analytics & anomaly detection | 5 | 22 | Extended |
| Network security, segmentation & zero-trust access | 4 | 15 | Extended |
| Insider risk, DLP & data security | 4 | 11 | Extended |
| Dashboards, reporting & analytics | 4 | 20 | **Core** |
| Access control & least privilege (platform feature) | 4 | 12 | **Core** |
| Automation & orchestration | 4 | 18 | Extended |
| Threat detection, SOC & managed response | 3 | 16 | **Core substrate** |
| Cloud & SaaS security posture (CSPM/CNAPP/SSPM) | 3 | 8 | Extended |
| Application security testing & API security | 3 | 9 | Extended |
| Encryption & key management | 3 | 8 | Platform note |
| Threat intelligence | 2 | 11 | Extended |
| Identity proofing & fraud prevention | 2 | 4 | Extended |
| GRC, compliance automation & continuous authorization | 2 | 10 | **Core substrate** |
| Risk assessment, scoring & third-party risk | 2 | 8 | **Core** |
| Asset inventory, visibility & attack surface | 2 | 8 | **Core** |
| Endpoint management, patching & IT automation | 2 | 4 | Extended |
| Vulnerability scanning & management | 1 | 5 | **Core substrate** |
| Endpoint security, EDR & XDR | 1 | 8 | Extended |
| Phishing defense & security awareness training | 1 | 8 | Extended |
| Audit logging & activity trails | 1 | 8 | **Core** |
| Log & telemetry collection, pipelines & data lakes | 1 | 6 | Extended |
| Backup, recovery & data protection | 0 | 9 | Extended |
| Secure enclave / VDI for CUI | 0 | 3 | Extended |

Per-fork claim counts: Palo Alto Networks GCS **16**, Armis AFE
**14**, Kiteworks **9**, Cisco Cloudlock **6**, ID.me **5**, Acuant
**4**, Okta **2**, Orca **2**, Proofpoint Email **2**, Saviynt **2**,
Silo **1**, Duo **1**, Fortify On Demand **1**, Tanium **1**,
Zimperium **1**, and **zero** for Login.gov, Proofpoint TAP, and
Qualys. The full per-fork table is pinned literally in
`tests/test_additions.py` (`EXPECTED_CLAIMS`).

### Zero-claim forks — pinned, not hidden

Three additions carry **zero claims**, for the same reason Rapid7
carries no vulnerability claim among the original 54: their own
marketplace descriptions phrase their function in none of the
taxonomy's 25 patterns, and the taxonomy was not re-tuned to catch
them.

- **Login.gov** (`FR1829538820`) — a production federal
  single-sign-on service whose description says "secure and private
  online access" and "sign in to multiple government agencies" but
  never "single sign-on", "authentication", "identity proofing",
  or any other pattern phrase.
- **Proofpoint Targeted Attack Protection** (`FR1819168894`) —
  "helps detect, mitigate, and block advanced threat" and attacks
  that "trick users to share their passwords": no "threat
  detection" noun phrase, no SIEM/SOAR/MDR marker, and the word
  "phishing" never appears.
- **Qualys Cloud Platform** (`F1508207205`) — "eliminating
  vulnerabilities" without scanning/management adjacency,
  "sensors… collect data automatically" without a telemetry or
  pipeline phrase, "continuously analyzing and correlating"
  without an analytics-family phrase.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full feed is `scratch/additions_near_miss_feed.json`):

- **Acuant COFRS** — Document-authentication, biometric-match, and
  liveness prose has no family to land in (the taxonomy has no
  biometrics family); it rides on the `fraud_identity` claim the
  proofing sentences earn. "An assessment of the degree of match"
  is not `risk_scoring` phrasing.
- **Armis AFE** — "Discovers every managed, unmanaged, and IoT
  device" is not `asset_inventory` phrasing (the claim rests on
  the "attack surface" sentence); "detect threats" (verb) and
  "passively monitors" are not `detection_response` (the claim
  rests on the SIEM-integration sentence); "behavioral anomalies"
  is not `ai_ml`'s "anomaly detection" (the claim rests on the
  "machine learning" sentence).
- **Authentic8 Silo** — `secure_enclave` does not fire: a remote
  browser is never phrased as VDI, virtual desktop, or enclave.
  "Insulates and isolates all web data" is a second isolation
  sentence without the exact "web isolation" phrase; the
  `network_security` claim rests on "the Silo web isolation
  platform."
- **Cisco Cloudlock** — The CASB matches no `cloud_saas_security`
  phrase (no CSPM, posture, or "cloud security platform" wording)
  and "Cloud App Security" is not "application security" for
  `app_security`. "Malicious insiders" in prose does not tag
  `insider_dlp`; the UEBA sentence does.
- **Duo Federal** — "Enforce stricter device and application
  access policies" is not `access_control_feature` (no "access
  control", RBAC, or least-privilege phrase); per-device health
  checking matches no family.
- **ID.me** — Two wording artifacts, recorded rather than
  corrected (the taxonomy is not re-tuned): `risk_scoring` fires
  on "Risk-Based Authentication" via the family's own `risk-based`
  alternative, and `automation` fires on the policy engine's
  "orchestration capability" via the family's orchestration
  alternative. Neither implies a scoring or SOAR engine here —
  see §3. SAML/OAuth/OIDC prose does not tag `api_integration`.
- **Kiteworks** — All 9 claims sit inside one component-list block
  (the sentence splitter's unit), and every matched phrase was
  verified present in it verbatim: "threat detection", "device
  management", "audit logging", "role- and attribute-based access
  control", "REST APIs", "multi-factor authentication", "DLP
  integration", "encryption". The headline sentence ("data
  security, governance, and compliance capabilities") tags
  nothing — `compliance_grc` requires a strong marker, per the
  group's standing correction.
- **Okta** — No near-misses: every keyword-bearing sentence
  matched.
- **Fortify On Demand** — "Static Code Scanning" and "scan
  engine" are not `vuln_management` (no vulnerability adjacency);
  "an audit review by a Fortify Static auditor" is not
  `audit_logging`. The fork rides on its single `app_security`
  claim.
- **Orca Security** — "Discovers all cloud assets / visibility
  into all your assets" is not `asset_inventory` phrasing;
  "regulatory compliance with over 65 out-of-the-box frameworks"
  is not `compliance_grc` ("compliance frameworks" must be
  adjacent); "identifies, prioritizes, and remediates risks" is
  not `risk_scoring` phrasing; the bare noun "vulnerabilities"
  in a detection list is not `vuln_management`.
- **Palo Alto Networks GCS** — A 30+-product catalogue; 16
  families tag. The unmatched keyword sentences are a class, not
  a list: connectivity and management detail (SD-WAN traffic
  engineering, packet mirroring, cloud managers), the Strata
  Logging Service's "collects, normalizes, and integrates data"
  (not `log_telemetry`'s pipeline phrasing), and "threat
  prevention and detection" (not the noun phrase "threat
  detection").
- **Proofpoint Email** — The DLP evidence sentence also contains
  "spam detection" and "threat protection"; neither is
  `detection_response` phrasing, so the sentence tags `insider_dlp`
  only.
- **Saviynt EIC** — "Effectively manage risk" is not
  `risk_scoring` (no score/assessment phrasing, no "cyber risk
  management"); IGA lifecycle/certification and just-in-time
  privileged-access prose rides on the `identity_access` claim;
  "advanced analytics" alone tags neither `ai_ml` nor
  `reporting_dashboards`.
- **Tanium TC-USG** — A brief description: "endpoint management
  and security platform" tags `endpoint_management` only —
  "endpoint security" never appears adjacently — and "automatically
  configured and maintained" tags nothing.
- **Zimperium** — "Mobile Threat Defense (MTD)" is not an MDR or
  SIEM marker; "Mobile Endpoint Cyber Security" breaks
  `endpoint_detection`'s "endpoint security" adjacency;
  "visibility on the threats and vulnerabilities" is not
  "device visibility" for `asset_inventory`; "to assess
  organization risk" reverses `risk_scoring`'s "risk assessment".
  The fork rides on its single `ai_ml` claim.

### Wording artifacts in claims that stand

Recorded for honesty, not corrected — the taxonomy is the group's
law, applied verbatim:

- **Cisco Cloudlock, `network_security`** fires on the "Apps
  Firewall", an OAuth app-discovery control — a "firewall" in
  name, not a network firewall. The claim stands; the family's
  enforcement engine remains Extended either way.
- **Armis AFE, `compliance_grc`** fires on "maintain continuous
  compliance" — the `continuous compliance` strong marker the
  group's corrected family deliberately accepts (bare "continuous
  monitoring" and "maintain compliance" remain excluded).
- **ID.me, `risk_scoring` and `automation`** — see the ID.me
  near-miss entry above.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC, and every Core / Core-substrate family's records form
already exists in the build. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| APIs & integrations (6) | Core 9 — the service is API-first | **Carried** — no change |
| Dashboards, reporting & analytics (4) | Core 8 — posture reporting | **Carried** |
| Access control & least privilege (4) | Core 10 — RBAC hooks | **Carried** |
| Risk assessment, scoring & third-party risk (2) | Core 4/5 — deterministic scoring + register | **Carried** — the additions bring no score of their own; the only scores remain the published formulas |
| Asset inventory, visibility & attack surface (2) | Core 1 — asset register | **Carried** |
| Audit logging & activity trails (1) | Core 11 — append-only audit log | **Carried** |
| Threat detection, SOC & managed response (3) | Core substrate 2/3 — ingestion, triage, tracking of detection output | **Carried** — detection engines stay Extended |
| GRC, compliance automation & continuous authorization (2) | Core substrate 6 — control mapping & assessment | **Carried** — full GRC suites stay Extended |
| Vulnerability scanning & management (1) | Core substrate 2 — ingestion, consolidation, tracking of scanner output | **Carried** — scanners stay Extended |
| Identity, authentication & privileged access (7) | Extended — identity products; the build ships access-control *hooks*, not an IdP | **Gap** — existing gap gains 7 claimants |
| AI/ML-powered analytics & anomaly detection (5) | Extended — detection models and AI scoring engines | **Gap** — gains 5 |
| Network security, segmentation & zero-trust access (4) | Extended — enforcement planes | **Gap** — gains 4 |
| Insider risk, DLP & data security (4) | Extended — monitoring engines; their alerts arrive as findings | **Gap** — gains 4 |
| Automation & orchestration (4) | Extended — SOAR / workflow engines | **Gap** — gains 4 |
| Cloud & SaaS security posture (3) | Extended — posture engines; their findings are ingested | **Gap** — gains 3 |
| Application security testing & API security (3) | Extended — testing engines; their results are ingested | **Gap** — gains 3 |
| Threat intelligence (2) | Extended — feeds, curation, research | **Gap** — gains 2 |
| Identity proofing & fraud prevention (2) | Extended — proofing / fraud-scoring services | **Gap** — gains 2 |
| Endpoint management, patching & IT automation (2) | Extended — management agents | **Gap** — gains 2 |
| Endpoint security, EDR & XDR (1) | Extended — endpoint agents and response platforms | **Gap** — gains 1 |
| Phishing defense & security awareness training (1) | Extended — simulation and training content | **Gap** — gains 1 |
| Log & telemetry pipelines & data lakes (1) | Extended — pipeline routing | **Gap** — gains 1 |
| Encryption & key management (3) | Platform note — TLS when configured; at rest is deployment-layer | **Platform note** — gains 3 claimants; no key-management service added |

**Result: the core is unchanged.** No function the 18 claim
presupposes a records form the build lacks: identity products'
assertions and alerts, posture engines' misconfigurations,
scanners' and testers' results, and email gateways' detections all
land in the same finding/asset/risk/control records the original
54 presupposed. `src/` is byte-identical to the shipped build
(`src/cyber/store.py` SHA-256
`f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de`
before and after this addendum's work, the mutation drill
included). The tier baseline does not change: same tier by
construction.

## 4. Updated union statement

The group now covers **72 forks** (54 original siblings + 18
remainder additions), **271 claims** in total (204 + 67), with
**69 of 72** forks carrying at least one claim. The merged build
remains the same 11-function defensive platform substrate — asset
register, finding ingestion and lifecycle, deterministic risk
scoring, risk register, control mapping & assessment, search,
posture reporting, API, access-control hooks, audit log — now
spec'd against 72 marketplace offerings instead of 54. The
additions shift the union's center of gravity toward identity
(identity_access is now claimed by 15 of 72 forks, the
second-largest Extended family) without changing the substrate
decision the original spec made: this build ships access-control
hooks and ingests identity products' output; it is not an identity
provider.

## 5. Gaps — for the registry at ship

**No new gap functions.** Every Extended family the additions
claim was already specified and registered for this group; the
additions raise claimant counts on existing gaps. For `GAPS.md`,
the existing entries gain these claimants:

- **Identity, authentication & privileged-access products** —
  +7: Acuant COFRS, Duo Federal, ID.me Identity Gateway,
  Kiteworks, Okta IDaaS, Palo Alto Networks GCS, Saviynt EIC
- **AI/ML-powered analytics & anomaly detection** — +5: Acuant
  COFRS, Armis AFE, Cisco Cloudlock, Palo Alto Networks GCS,
  Zimperium
- **Network security enforcement (segmentation, firewall/WAF,
  ZTNA/SSE, browser isolation)** — +4: Armis AFE, Authentic8 Silo,
  Cisco Cloudlock, Palo Alto Networks GCS
- **Insider-risk, DLP & data-security monitoring engines** — +4:
  Cisco Cloudlock, Kiteworks, Palo Alto Networks GCS, Proofpoint
  Email and Information Protection
- **Automation & orchestration engines / SOAR** — +4: Armis AFE,
  Cisco Cloudlock, ID.me Identity Gateway, Palo Alto Networks GCS
- **Cloud & SaaS posture engines (CSPM/CNAPP/SSPM)** — +3: Armis
  AFE, Orca Cloud Security Platform, Palo Alto Networks GCS
- **Application-security testing engines (SAST/DAST/SCA,
  penetration testing)** — +3: Armis AFE, Fortify On Demand, Palo
  Alto Networks GCS
- **Threat-intelligence feeds, curation, and research** — +2:
  Armis AFE, Palo Alto Networks GCS
- **Identity proofing & fraud prevention** — +2: Acuant COFRS,
  ID.me Identity Gateway
- **Endpoint management, patching & IT automation agents** — +2:
  Kiteworks, Tanium TC-USG
- **Endpoint security agents, EDR & XDR platforms** — +1: Palo
  Alto Networks GCS
- **Phishing simulation & security-awareness training** — +1:
  Palo Alto Networks GCS
- **Log & telemetry pipelines and security data lakes** — +1:
  Palo Alto Networks GCS
- **Encryption & key management** (platform note, not a gap
  function) — +3 claimants: Acuant COFRS, Cisco Cloudlock,
  Kiteworks

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim set, and verbatim evidence (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: finding ingestion under the fork's own product as
  source, deterministic scoring, lifecycle transition, and search,
  plus the Core surfaces its claims name (asset rescoring, risk
  register, control assessment, posture, audit) — and a bulk-atomicity
  case mixing addition sources.
- **Tests: 194 → 204, all passing** (the 18 fork cases run as
  subTests inside the additions module).
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `score_finding` in
  `src/cyber/store.py` was patched to the severity-blind mutant
  (`score = 1 * CRITICALITY_WEIGHTS[criticality]`) and the full
  suite ran — **204 tests, 52 failures**, 22 of them from the new
  additions module, whose per-fork score assertions trip on the
  mutant exactly as designed. `store.py` was restored from the
  pre-mutation copy and verified SHA-256-identical to the shipped
  hash; the suite re-ran green. Recorded in `tests/README.md`.
