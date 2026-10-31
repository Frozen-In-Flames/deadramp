# Union Spec — Cybersecurity & Risk Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for the first **untiered set**: **27 forks**,
category **Cybersecurity & Risk Management**, **tier null**. Every
member's FedRAMP impact level is **Unknown** in the source dataset —
the source publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts **no
control baseline**. Per PIPELINE.md, untiered offerings "build to
their documented control claims; tier stays null in the registry
until the source publishes a baseline." The Documented control
claims section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly census unit `untiered:Cybersecurity &
Risk Management` in `../../remainder.json` (27 fork IDs, verified
mechanically). In `forks.json` the set is mixed as filed: 12 forks
carry the Cybersecurity & Risk Management category, 13 are filed
"Uncategorized (none in source)", and 2 are filed under Artificial
Intelligence (AI); the census assigned all 27 to this category from
their own descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span Certified (3), In Process
(9), Initial Implementation (14), and Agency Authorization In
Process (1) — a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 27
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 27 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (27/27).

**Duplicate authorization pair:** FR2232465502 and FR2232465502A
(Broadcom, Symantec Gov Cloud Security (GCS) and its "- High"
record) are spec'd as separate sheets, per the Phase 1 rule that
paired records stay separate. Their descriptions are byte-identical
in the source and their claim tables are identical (4 claims each);
the sheets differ only in fork_id, product name, and source record.
The pair is counted twice in every count below, as the registry
counts it.

## How functions were counted

The category's fixed 25-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../cybersecurity-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 25 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 54 of 54 forks, 204 of 204 claims, deep-equal** against
the sheets at the original ship commit — using the parent's
sentence split and evidence rule (first matching sentence; over 400
characters, truncated to 397 + '...').

The founding group's four recorded wording-artifact corrections are
embodied in the taxonomy patterns themselves (the `compliance_grc`
family requires a strong marker, not bare "continuous monitoring" or
the bare acronym "ATO"; `automation` requires automation of a
workflow/response/remediation/security/segmentation/policy object,
not a bare "automates the …"; the `log_telemetry` family added for
pipeline offerings). The founding ADDENDUM records no per-hit
removals beyond those pattern-embodied corrections, and none were
invented here. An exclusion pass scanned every raw hit's evidence
sentence for third-party hosted-app catalogue segments and
scope-exclusion sentences: **no hits were removed** — no description
in this set contains a third-party catalogue segment, and no
evidence sentence carries scope-exclusion phrasing. First-party
component catalogues (Broadcom, Cisco, SentinelOne, Trellix,
DigiCert, Remedio) stand at catalogue weight, per the founding
additions' posture; adjudications and wording artifacts are itemized
in `scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**107 claims** across the set; **26 of 27 forks carry at least one
claim**. The one zero-claim fork is recorded under Named absences,
not hidden.

Census citations: 39 citations are recorded for these forks in the
census; **39 of 39 verify** as verbatim substrings of the forks' own
descriptions (whitespace-normalized), and **25 of 39** are
themselves a claim evidence sentence. Verification is not a claim,
in either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 27 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 27) | Disposition in this build |
|---|---|---:|---|
| 1 | AI/ML-powered analytics & anomaly detection | 13 | Extended (detection models and AI scoring engines; this build's risk scoring is a published deterministic formula, not ML — stated plainly) |
| 2 | Threat detection, SOC & managed response (SIEM/SOAR/MDR) | 9 | **Core substrate** (ingestion, triage, and tracking of detection output; the detection engines and staffed SOCs themselves are Extended) |
| 3 | Identity, authentication & privileged access | 8 | Extended (identity products; this build ships access-control *hooks*, not an IdP) |
| 4 | Dashboards, reporting & analytics | 7 | **Core** (posture reporting) |
| 5 | APIs & integrations | 7 | **Core** (the service is API-first) |
| 6 | Automation & orchestration | 7 | Extended (SOAR and workflow engines; the finding lifecycle in Core is a workflow, not an orchestration engine) |
| 7 | Encryption & key management | 6 | Platform note (documented control claim — see below; the build performs no cryptography of its own) |
| 8 | Vulnerability scanning & management | 5 | **Core substrate** (ingestion, consolidation, and tracking of scanner output; the scanners themselves are Extended) |
| 9 | Endpoint management, patching & IT automation | 5 | Extended (management agents) |
| 10 | Access control & least privilege (platform feature) | 5 | **Core** (access-control hooks) |
| 11 | GRC, compliance automation & continuous authorization | 4 | **Core substrate** (control mapping & assessment, the register every GRC suite presupposes; full GRC automation suites are Extended) |
| 12 | Asset inventory, visibility & attack surface | 4 | **Core** (the asset register) |
| 13 | Endpoint security, EDR & XDR | 4 | Extended (endpoint agents and response platforms) |
| 14 | Threat intelligence | 3 | Extended (intel feeds, curation, and research services) |
| 15 | Network security, segmentation & zero-trust access | 3 | Extended (enforcement planes: segmentation, firewall/WAF, ZTNA/SSE, browser isolation) |
| 16 | Insider risk, DLP & data security | 3 | Extended (monitoring engines; their alerts arrive in Core as findings) |
| 17 | Log & telemetry collection, pipelines & security data lakes | 3 | Extended (pipeline routing; Core ingests the findings those pipelines feed) |
| 18 | Identity proofing & fraud prevention | 2 | Extended (proofing/fraud-scoring services) |
| 19 | Risk assessment, scoring & third-party risk | 2 | **Core** (deterministic finding scoring + the risk register) |
| 20 | Cloud & SaaS security posture (CSPM/CNAPP/SSPM) | 2 | Extended (posture engines; their misconfiguration findings are ingested by Core) |
| 21 | Application security testing & API security | 2 | Extended (SAST/DAST/SCA and pentest engines; their results are ingested by Core) |
| 22 | Phishing defense & security awareness training | 2 | Extended (simulation and training content) |
| 23 | Audit logging & activity trails | 1 | **Core** (audit-log hooks) |
| 24 | Backup, recovery & data protection | 0 | Extended (backup/vaulting/recovery products) — **zero claimants in this set; named absence** |
| 25 | Secure enclave / VDI for CUI | 0 | Extended (hosted enclave environments) — **zero claimants in this set; named absence** |

**A deliberate scoping note for a security-tools group** (carried
from the founding spec): the merged build implements the *defensive
platform substrate* the siblings share — the register of assets, the
findings those tools produce, their triage, the risk register, and
the control map. It implements **no offensive tooling and no
detection/enforcement engine**: no scanner, no agent, no firewall,
no phishing simulator. Those engines are the Extended tail, named
above with their set counts; the per-fork spec sheets name which
forks claim each.

## The Core — what this build implements (11 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's eleven-function substrate **whole** — asset
inventory; finding ingestion; finding triage & lifecycle; risk
scoring (the published deterministic severity × criticality
formula); risk register; control mapping & assessment; search &
filtering; posture reporting; API access; access control; audit
log. The substrate is records machinery that every sibling's output
presupposes, and it is tier-independent code: the founding build's
source contains no tier or baseline machinery, so there was nothing
tier-shaped to strip. In this set, ten of the eleven functions are claim-supported by at
least one fork under the standing dispositions (asset inventory by
`asset_inventory`; ingestion and triage as the substrate of
`vuln_management` and `detection_response`; risk scoring and the
risk register by `risk_scoring`; control mapping & assessment by
`compliance_grc`; posture reporting by `reporting_dashboards`; API
access by `api_integration`; access control by
`access_control_feature`; the audit log by `audit_logging`). The
eleventh, search & filtering, is a substrate operation over the
registers with no family in the taxonomy, exactly as in the
founding build. Functions are **carried** as substrate; the claims
that support them are recorded above, and no function is claimed to
be *attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/cyber/` (8 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `cyber` under `src/`, ids sequential per object type with
fixed prefixes, failed operations consume no id and change nothing,
all timestamps UTC ISO-8601, roles `admin|analyst|viewer` with the
founding permission matrix, the 34-control 800-53 Rev. 5 catalog as
the control map's vocabulary, and the audit log append-only with
denied attempts recorded. Where the founding contract's text says
"L2 baseline hooks" for access control and audit, read it here as
**baseline-neutral hooks**: at tier null they are substrate, claimed
against no baseline.

Two category invariants are preserved exactly, as the founding
build implements them: finding and risk scores are the published
deterministic formulas (severity weight × criticality weight;
likelihood × impact), computed at ingest/creation — they are
derivations from recorded inputs, not models; and posture reporting
is a counts-and-buckets summary (assets by criticality, findings by
severity and status, risks by band and status, control coverage as
assessed/implemented counts) — posture computes no score of its
own.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 27 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words, under the taxonomy
families that carry control language. A documented control claim is
a **fork's claim about itself**, recorded here with its evidence;
it is not the build's control attainment, and nothing in this
section fills a family in from any baseline.

Control areas **documented** by at least one fork in the set:

- **Identification & authentication (IA)** — via
  `identity_access`, **8 forks**: Cisco Security Cloud for
  Government (FR2304757473, two-factor identity verification),
  Dispel Zero Trust Engine (FR2630354482, privileged access
  management), JupiterOne GovCloud (FR2632054495, identity and
  access management tooling), Keeper Security Government Cloud
  (FR2116544598, password and privileged access management),
  Mimic ERDP (FR2527245282), NextgenID UIaaS (FR2630354494,
  identity & credential management), SailPoint Identity Security
  Cloud (FR2001938710), TransUnion TruValidate (FR2516140413,
  identity platform).
- **Cryptographic protection — encryption & key management (SC)**
  — via `encryption_feature`, **6 forks**: Broadcom Symantec GCS
  (FR2232465502 and FR2232465502A, the duplicate pair), DigiCert
  for Government (FR2635050845, key/certificate lifecycle
  language), Portal26 (FR2631054533 — "Federal customer data is
  encrypted in transit and at rest"), SuperFile (FR2635050855 —
  "dynamic key generation, layered encryption"). **Artifact
  weight:** Mimic ERDP's claim (FR2527245282) fires on the
  *attacker's* verb — ransomware that can "encrypt" — and is
  recorded at artifact weight in `scratch/ARTIFACTS.md`; it
  documents no encryption capability of the offering itself.
- **Access control & least privilege (AC)** — via
  `access_control_feature`, **5 forks**: Cisco Security Cloud for
  Government (FR2304757473, policy enforcement), DigiCert for
  Government (FR2635050845), Dispel Zero Trust Engine
  (FR2630354482 — "least-privilege access"), Remedio
  (FR2634436150), SuperFile (FR2635050855 — "embedded access
  controls").
- **Control assessment, compliance mapping & continuous
  authorization language (CA)** — via `compliance_grc`, **4
  forks**: ConnectSecure (FR2633734912, compliance management),
  JupiterOne GovCloud (FR2632054495 — "compliance dashboards map
  assets and controls to supported compliance frameworks"),
  Remedio (FR2634436150 — "continuous compliance"), TNT Business
  Resilience Platform (FR2634659091, compliance management).
- **Risk assessment language (RA)** — via `risk_scoring`, **2
  forks**: Securin Preemptive Exposure Management (FR2700857464 —
  "risk-based prioritization"), TNT Business Resilience Platform
  (FR2634659091).
- **Audit logging (AU)** — via `audit_logging`, **1 fork**:
  DigiCert for Government (FR2635050845, audit-readiness /
  activity-trail language in its certificate-platform prose).

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, CM, CP, IR,
MA, MP, PE, PL, PM, PS, SA, and SI **as control claims** — is
asserted by no description in the set. (Several of those letters
appear in the build's own control *catalog*, which is the
substrate's mapping vocabulary carried from the founding build;
the catalog is the build's design, not a fork's claim and not a
baseline.) If the source later publishes an impact level for any of
these offerings, the tier is recorded then and not before.

## Named absences

- **Backup, recovery & data protection — 0 of 27.** The
  `data_protection` family, claimed by 9 siblings in the founding
  group, has no claimant in this set; no description here asserts
  backup, disaster recovery, or a cyber vault in matching text.
- **Secure enclave / VDI for CUI — 0 of 27.** No description
  asserts a virtual desktop, secure enclave, or secure-spaces
  function.
- **Audit logging — 1 of 27.** Near-absent: only DigiCert's prose
  carries audit language; the other 26 descriptions are silent on
  audit trails even where they claim adjacent control language.
- **Zero-claim fork:** FR2000863987, Cloudflare for Government —
  its description's "journey to Zero Trust" phrasing matches no
  family (it is not ZTNA phrasing in the taxonomy's terms), and no
  other family fires. The zero is recorded, not repaired; the
  taxonomy was not re-tuned for it (the Login.gov posture from the
  founding additions).

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
the same engine gaps as the founding group, restated here only
where this set's forks claim them (claimant counts are this set's):

- [ ] AI/ML analytics & anomaly-detection engines (13 claimants)
- [ ] Detection engines and staffed SOC / managed-response services (9 claimants' engines; their output's ingestion and triage is Core)
- [ ] Identity, authentication & privileged-access products / IdP (8)
- [ ] Automation & orchestration engines / SOAR (7)
- [ ] Endpoint management, patching & IT automation agents (5)
- [ ] Endpoint security agents, EDR & XDR platforms (4)
- [ ] Threat-intelligence feeds, curation & research (3)
- [ ] Network security enforcement planes (segmentation, firewall/WAF, ZTNA/SSE, browser isolation) (3)
- [ ] Insider-risk, DLP & data-security monitoring engines (3)
- [ ] Log & telemetry pipelines and security data lakes (3)
- [ ] Identity proofing & fraud-prevention services (2)
- [ ] Cloud & SaaS posture engines (CSPM/CNAPP/SSPM) (2)
- [ ] Application-security testing engines (SAST/DAST/SCA, penetration testing) (2)
- [ ] Phishing simulation & security-awareness training (2)
- [ ] Encryption & key-management platform layer (the forks document encryption claims; the build performs no cryptography — TLS is deployment-layer, FIPS-validated crypto (SC-13) is not claimed by the build)

## Coverage statement (for this build)

27 forks spec'd of 27 in census unit `untiered:Cybersecurity &
Risk Management`; 107 taxonomy claims tagged from the forks' own
descriptions (26 of 27 forks claiming at least one); the
eleven-function substrate carried byte-identical from the founding
Cybersecurity L2 build and re-anchored to tier null; tier null
recorded on every sheet and pinned by tests. Nothing in this build
claims a FedRAMP authorization, a CMMC certification, or a control
baseline for any fork or for the build itself.
