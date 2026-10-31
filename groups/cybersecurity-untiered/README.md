# Cybersecurity & Risk Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **27 untiered forks** of Cybersecurity &
Risk Management — census unit `untiered:Cybersecurity & Risk
Management` in `../../remainder.json`, the first untiered set built
under the remainder pipeline. **This is an untiered set, and that
means something specific:** every member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no baseline
for these offerings, so **tier stays null**: no tier is assigned, no
CMMC equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec sheets are in
[`specs/specs.json`](specs/specs.json), each recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The 27 forks were spec'd under the category's existing 25-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Cybersecurity L2 group's original
shipped claim tables exactly — **54 of 54 forks, 204 of 204 claims,
deep-equal** — before tagging this set. Result here: **107 claims**
across the set, **26 of 27 forks claiming at least one**; the one
zero-claim fork (FR2000863987, Cloudflare for Government) is
recorded under Named absences in the union spec, not hidden or
repaired.

The build implements the category's **eleven-function substrate**
— the defensive records machinery every sibling's output
presupposes — carried **byte-identical** from the founding
Cybersecurity L2 build (`../cybersecurity-l2/src/cyber/`, 8 of 8
modules; SHA-256 accounting below). The substrate is
tier-independent records code: the founding source contains no tier
or baseline machinery, so there was nothing tier-shaped to strip.
Where the founding contract's text says "L2 baseline hooks" for
access control and audit, read it here as **baseline-neutral
hooks**: at tier null they are substrate, claimed against no
baseline.

## The 27 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| F1602167854 | BlackBerry | BlackBerry CylanceProtect & CylanceOptics | 3 |
| FR2232465502 | Broadcom | Symantec Gov Cloud Security (GCS) | 4 |
| FR2232465502A | Broadcom | Symantec Gov Cloud Security (GCS) - High | 4 |
| FR2304757473 | Cisco Systems Inc. | Cisco Security Cloud for Government | 13 |
| FR2000863987 | Cloudflare | Cloudflare for Government | 0 |
| FR2633734912 | ConnectSecure LLC | ConnectSecure Vulnerability and Compliance Manager | 1 |
| FR2134254227 | Devo | Devo.Gov-US | 4 |
| FR2635050845 | DigiCert, Inc. | DigiCert for Government | 4 |
| FR2630354482 | Dispel LLC | Dispel Zero Trust Engine | 3 |
| FR2628647233 | Dispel, LLC | Dispel Zero Trust Engine (DZTE) For Government | 1 |
| FR2632054495 | JupiterOne, Inc. | JupiterOne GovCloud | 7 |
| FR2116544598 | Keeper Security | Keeper Security Government Cloud Password Manager and Privileged Access Manager | 6 |
| FR2527245282 | Mimic Networks, Inc. | Mimic Enterprise Ransomware Defense Platform (ERDP) | 3 |
| FR2630354494 | NextgenID, Inc. | NextgenID User Interface as a Service (UIaaS) | 2 |
| FR2701857797 | Optimal Labs | 9line | 3 |
| FR2631054533 | Portal26, Inc. | AI Security, Governance, & Telemetry Platform | 2 |
| FR2634436150 | Remedio Technologies Inc | Remedio | 6 |
| FR2001938710 | SailPoint Technologies, Inc. (Pre SCR review) | SailPoint Identity Security Cloud | 2 |
| FR2700857464 | Securin, Inc. | Securin Preemptive Exposure Management Platform | 3 |
| FR1919071020 | SentinelOne | SentinelOne Singularity Platform Moderate | 5 |
| FR2635050855 | SuperGov, Inc | SuperFile | 2 |
| FR2634659091 | Tactical Takedown LLC | TNT Business Resilience Platform | 9 |
| FR2632731472 | Transmittr, Inc. | Casco for Government | 4 |
| FR2516140413 | TransUnion LLC | TransUnion TruValidate | 3 |
| FR1935245314 | Trellix | Trellix GovCloud Security Platform | 8 |
| FR2633058240 | Ultra Security, Inc. | Ultra Agentic Security Platform | 2 |
| FR2308034636 | Wiz, Inc. | Wiz Moderate for U.S. Government | 3 |

**Duplicate authorization pair:** FR2232465502 and FR2232465502A
(Broadcom Symantec GCS and its "- High" record) are spec'd as
separate sheets, per the Phase 1 rule that paired records stay
separate. Their descriptions are byte-identical in the source and
their claim tables are identical (4 claims each); the pair is
counted twice in every count, as the registry counts it.

In `forks.json` the set is mixed as filed: 12 forks carry the
Cybersecurity & Risk Management category, 13 are filed
"Uncategorized (none in source)", and 2 are filed under Artificial
Intelligence (AI); the census assigned all 27 to this category from
their own descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span FedRAMP Certified (3),
FedRAMP In Process (9), Initial Implementation (14), and Agency
Authorization In Process (1) — a status is record data, not a
claim.

## The 11 core functions

1. **Asset inventory** — a register of assets (name, kind, owner,
   criticality, tags) with provenance (who created it, when).
   Changing an asset's criticality recomputes the scores of its
   findings.
2. **Finding ingestion** — findings (scanner, posture-engine,
   detection-platform, and test output) enter one at a time, in
   bulk (JSON), or as CSV scan results. A batch is atomic: one bad
   row rejects the whole batch, nothing is partially applied, no
   ids are consumed, and an empty batch is an error.
3. **Finding triage & lifecycle** — findings move through a fixed
   lifecycle (`new → triaged → in_progress → mitigated / accepted`,
   plus `false_positive` and terminal `closed`, per the contract's
   transition map) with assignment. Invalid transitions are
   rejected with a validation error, never silently applied.
4. **Risk scoring** — a deterministic, published score per
   finding: severity weight (critical 5 … info 1) × asset
   criticality weight (critical 2.0 … low 0.5), banded at 8 / 5 /
   2.5. Same inputs, same score, always. No ML, no hidden model.
5. **Risk register** — standing risks with likelihood × impact
   scoring (1–25, banded at 15 / 10 / 5), an owner, a lifecycle
   (including `closed → open` reopen), and links to the findings
   that evidence them.
6. **Control mapping & assessment** — a built-in catalog of 34
   NIST SP 800-53 Rev. 5 controls; findings link to controls at
   ingest, and each control carries an assessment status and an
   evidence note, so coverage is a query (`coverage_pct`), not a
   spreadsheet. The catalog is the substrate's mapping vocabulary
   carried from the founding build — it is the build's design, not
   a fork's claim and not a baseline.
7. **Search & filtering** — findings filtered by
   severity/status/asset/source and substring, sorted by score;
   assets and risks by substring; one cross-object search over all
   three.
8. **Posture reporting** — a summary: assets by criticality,
   findings by severity and status (every bucket present, zeros
   included), the top 5 open findings by score, risks by band and
   status, and control coverage. Posture is counts and buckets; it
   computes no score of its own.
9. **API access** — every function above is exposed over a REST
   API (JSON), so the service composes with anything that speaks
   HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `analyst`, `viewer` with a permission matrix enforced
    on every operation.
11. **Audit log** — an append-only audit trail: every asset,
    finding, risk, and control-assessment mutation, every search,
    and every denied attempt is recorded with actor, action,
    target, and UTC timestamp. Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `asset-`, `find-`,
`risk-`. Severity is derived, never stored; records carry opaque
references only.

Ten of the eleven functions are claim-supported by at least one
fork in this set under the category's standing dispositions (see
`UNION-SPEC.md` for the tracing); search & filtering is a substrate
operation over the registers with no family in the taxonomy,
exactly as in the founding build. Functions are **carried** as
substrate; no function is claimed to be *attained* by any fork —
the build is the merged open implementation, not any fork's
product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m cyber serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, ingest, triage, manage_assets, manage_risks, assess_controls, audit_read, admin |
| `bob`   | analyst | read, ingest, triage, manage_assets, manage_risks, assess_controls |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/assets` | read | List assets (optional `?q=` over name/owner) → `{"assets": [...]}` |
| POST | `/assets` | manage_assets | Body `{"name", "kind", "owner", "criticality", "tags"?}` → 201 asset dict |
| GET | `/assets/{id}` | read | One asset dict |
| POST | `/assets/{id}/update` | manage_assets | Body `{"owner"?, "criticality"?, "tags"?}` → updated asset dict (criticality rescores its findings) |
| GET | `/findings` | read | List findings (`?severity=&status=&asset_id=&source=&q=`), score desc → `{"findings": [...]}` |
| POST | `/findings` | ingest | Body: one finding item → 201 finding dict |
| POST | `/findings/bulk` | ingest | Body `{"findings": [...]}` → 201 `{"findings": [...]}` (atomic) |
| POST | `/findings/csv` | ingest | Body `{"csv": "..."}` → 201 `{"findings": [...]}` (atomic; `control_ids` cell is semicolon-separated) |
| GET | `/findings/{id}` | read | One finding dict |
| POST | `/findings/{id}/transition` | triage | Body `{"status"}` → updated finding dict |
| POST | `/findings/{id}/assign` | triage | Body `{"assignee"}` (or `null` to unassign) → updated finding dict |
| GET | `/risks` | read | List risks (`?status=&q=`), score desc → `{"risks": [...]}` |
| POST | `/risks` | manage_risks | Body `{"title", "description", "likelihood", "impact", "owner"?, "finding_ids"?}` → 201 risk dict |
| GET | `/risks/{id}` | read | One risk dict |
| POST | `/risks/{id}/transition` | manage_risks | Body `{"status"}` → updated risk dict |
| GET | `/controls` | read | The 34-control catalog with assessment state → `{"controls": [...]}` |
| POST | `/controls/{id}/assess` | assess_controls | Body `{"status", "evidence"?}` → updated control dict |
| GET | `/posture` | read | The posture summary dict |
| GET | `/search?q=` | read | `{findings, assets, risks}` substring matches |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Asset dicts are `{id, name, kind, owner, criticality, tags,
created_by, created_utc, updated_utc}` with sequential ids
`asset-1`, `asset-2`, …; finding and risk dicts follow the same
pattern with their own prefixes (see `UNION-SPEC.md` for every
dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**200 tests, OK** at delivery: the founding group's 194-test core
suite carried with the code, plus spec tests pinning this set
(exactly 27 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; 107 claims total with exactly one
zero-claim fork). The category's signature severity-blind mutation
drill was re-run in this tree — exactly 30 failures under the
mutant, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/cyber/` is carried from the founding group
`../cybersecurity-l2/src/cyber/` — **8 of 8 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `8066a9eff6250bd8079dde87585401c9b78e835875db3d9b6a0d38ba109f05c2` |
| `__main__.py` | `660a9196cb404b7e02101d5a0a0438f6f922b015406040a67f93cc2e29459a9b` |
| `access.py` | `c9d4559e85fa8d62fdf33fffbd2f0437bd314a04bfdcab1711f5a1f9228d9e88` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `catalog.py` | `a9afe439050d36ab4e5b26309d63ee8ec0c6cf38bd286acb893eab68084afd3e` |
| `errors.py` | `4540b5f56b7eb2883bf1e28aa8819aaea0369fe8f4a766b7e448c762e3c2cd1f` |
| `service.py` | `1e79939470a51a1a3a3a990b81335c386fdd1b0785fbbcbf4d388c332144bec5` |
| `store.py` | `f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de` |

The test suite is likewise carried (the founding suite minus its
additions module, which pins a different census unit), with one
labeling fix in `tests/cyber_helpers.py` (its docstring now names
this untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 27 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under the
taxonomy families that carry control language. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family in
from any baseline.

Documented by at least one fork in the set:

- **Identification & authentication (IA)** — 8 forks, via
  `identity_access`: Cisco Security Cloud for Government, Dispel
  Zero Trust Engine, JupiterOne GovCloud, Keeper Security
  Government Cloud, Mimic ERDP, NextgenID UIaaS, SailPoint
  Identity Security Cloud, TransUnion TruValidate.
- **Cryptographic protection, encryption & key management (SC)**
  — 6 forks, via `encryption_feature`: Broadcom Symantec GCS
  (both records of the duplicate pair), DigiCert for Government,
  Portal26, SuperFile, and Mimic ERDP at **artifact weight** —
  Mimic's hit fires on the *attacker's* verb (ransomware that can
  "encrypt") and documents no encryption capability of the
  offering itself; it is recorded at artifact weight in
  `scratch/ARTIFACTS.md`. The other five carry encryption or
  key-management language about the offering itself.
- **Access control & least privilege (AC)** — 5 forks, via
  `access_control_feature`: Cisco Security Cloud for Government,
  DigiCert for Government, Dispel Zero Trust Engine, Remedio,
  SuperFile.
- **Control assessment & compliance language (CA)** — 4 forks, via
  `compliance_grc`: ConnectSecure, JupiterOne GovCloud, Remedio,
  TNT Business Resilience Platform.
- **Risk assessment language (RA)** — 2 forks, via `risk_scoring`:
  Securin Preemptive Exposure Management, TNT Business Resilience
  Platform.
- **Audit logging (AU)** — 1 fork, via `audit_logging`: DigiCert
  for Government.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, CM, CP, IR, MA, MP, PE, PL,
PM, PS, SA, and SI **as control claims** — is asserted by no
description in the set. If the source later publishes an impact
level for any of these offerings, the tier is recorded then and
not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **Extended functions are specified, not implemented.** The union
  spec ranks 25 functions; the substrate behind 11 is implemented
  here. NOT implemented (claimant counts are this set's): AI/ML
  analytics & anomaly-detection engines (13 — risk scoring here is
  a published deterministic formula, not a model); detection
  engines and staffed SOC / managed-response services (9 —
  ingestion and triage of their output is Core, detecting is not);
  identity, authentication & privileged-access products (8); 
  automation & orchestration engines / SOAR (7); endpoint
  management, patching & IT automation agents (5); endpoint
  security agents, EDR & XDR platforms (4); threat-intelligence
  feeds, curation & research (3); network security enforcement
  planes (3); insider-risk, DLP & data-security monitoring engines
  (3); log & telemetry pipelines and security data lakes (3);
  identity proofing & fraud-prevention services (2); cloud & SaaS
  posture engines (2); application-security testing engines (2);
  phishing simulation & security-awareness training (2).
- **The build performs no cryptography of its own.** Six forks
  document encryption claims about themselves; the substrate does
  no encryption — TLS is a deployment-layer option when a
  certificate is configured, and FIPS-validated crypto (SC-13) is
  not claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own.
- **Named absences stand.** Backup, recovery & data protection
  has 0 claimants in this set; secure enclave / VDI for CUI has 0;
  audit logging has 1 of 27. Nothing was back-filled to make the
  set look complete.
