# Cybersecurity & Risk Management L2 — merged build (Operation DeadRamp, Phase 2, Group 4)

This is the merged, clean-room implementation of the **Cybersecurity
& Risk Management L2** sibling group: **54 forks** from the FedRAMP
Marketplace that share the same function (Cybersecurity & Risk
Management) and the same trust tier (CMMC L2, equivalent to FedRAMP
Moderate), built as one open-source service per the group's union
spec, [`UNION-SPEC.md`](UNION-SPEC.md).

It was written from the contract in that spec only: original code, no
vendor code, assets, or branding from any of the 54 sibling offerings.
Python 3, **standard library only**, no external dependencies.

A deliberate scoping note for a security-tools group: this build is
the **defensive platform substrate** the siblings share — the asset
register, the findings those tools produce, their triage, the risk
register, and the control map. It contains **no offensive tooling
and no detection or enforcement engine**: no scanner, no endpoint
agent, no firewall, no phishing simulator. Those engines are the
Extended tail, listed plainly in the honesty section below.

## Additions: the 18 remainder forks (unit `addition:cybersecurity-l2`)

Eighteen previously uncategorized FedRAMP Moderate offerings have
since been spec'd into this group under the same taxonomy, applied
verbatim: Acuant COFRS, Armis FedRAMP Edition, Authentic8 Silo,
Cisco Cloudlock, Duo Federal, Login.gov, ID.me Identity Gateway,
Kiteworks, Okta IDaaS, Fortify On Demand, Orca Security, Palo Alto
Networks Government Cloud Services, Proofpoint Email and
Information Protection, Proofpoint Targeted Attack Protection,
Qualys Cloud Platform, Saviynt EIC, Tanium TC-USG, and Zimperium —
**72 forks** in total, **271 claims**, with the full record in
[`ADDENDUM.md`](ADDENDUM.md). What changed and what did not:

- **Spec sheets:** the 18 new sheets are appended to
  `specs/specs.json`; the original 54 are byte-for-byte untouched.
  Three additions carry zero claims — Login.gov, Proofpoint TAP,
  and Qualys — because their own descriptions phrase their
  function in none of the taxonomy's patterns; that is pinned in
  tests, not hidden (ADDENDUM §2, with per-fork near-misses).
- **Core: unchanged.** Every function the additions claim maps to
  a disposition the union spec already had, and no claim
  presupposes a records form the build lacks, so `src/` is
  byte-identical to the build described below. The unit is
  identity-heavy (7 of 18 claim identity products) and the answer
  is the one the original spec gave: access-control hooks and
  ingested output, not an identity provider.
- **Gaps:** no new gap functions; thirteen already-registered
  Extended gaps gain claimants (identity products +7, AI/ML
  analytics +5, network enforcement +4, DLP engines +4, SOAR +4,
  posture engines +3, appsec testing +3, threat intel +2, identity
  proofing +2, endpoint management +2, EDR/XDR +1, phishing
  defense +1, log pipelines +1) — itemized in ADDENDUM §5.
- **Tests:** 194 → **204, OK**, including the additions module
  (`tests/test_additions.py`) and a re-run of the mutation drill
  in this tree (52 failures under the severity-blind mutant, 22
  of them from the additions module; store restored and
  hash-verified).

## The 11 core functions

1. **Asset inventory** — a register of assets (name, kind, owner,
   criticality, tags) with provenance (who created it, when). Changing
   an asset's criticality recomputes the scores of its findings.
2. **Finding ingestion** — findings (scanner, posture-engine,
   detection-platform, and test output) enter one at a time, in bulk
   (JSON), or as CSV scan results. A batch is atomic: one bad row
   rejects the whole batch, nothing is partially applied, no ids are
   consumed, and an empty batch is an error.
3. **Finding triage & lifecycle** — findings move through a fixed
   lifecycle (`new → triaged → in_progress → mitigated / accepted`,
   plus `false_positive` and terminal `closed`, per the contract's
   transition map) with assignment. Invalid transitions are rejected
   with a validation error, never silently applied.
4. **Risk scoring** — a deterministic, published score per finding:
   severity weight (critical 5 … info 1) × asset criticality weight
   (critical 2.0 … low 0.5), banded at 8 / 5 / 2.5. Same inputs, same
   score, always. No ML, no hidden model.
5. **Risk register** — standing risks with likelihood × impact
   scoring (1–25, banded at 15 / 10 / 5), an owner, a lifecycle
   (including `closed → open` reopen), and links to the findings
   that evidence them.
6. **Control mapping & assessment** — a built-in catalog of 34
   NIST SP 800-53 Rev. 5 controls; findings link to controls at
   ingest, and each control carries an assessment status and an
   evidence note, so coverage is a query (`coverage_pct`), not a
   spreadsheet.
7. **Search & filtering** — findings filtered by
   severity/status/asset/source and substring, sorted by score;
   assets and risks by substring; one cross-object search over all
   three.
8. **Posture reporting** — a summary: assets by criticality,
   findings by severity and status (every bucket present, zeros
   included), the top 5 open findings by score, risks by band and
   status, and control coverage.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `analyst`, `viewer` with a permission matrix enforced
    on every operation.
11. **Audit log** — an append-only audit trail: every asset,
    finding, risk, and control-assessment mutation, every search,
    and every denied attempt is recorded with actor, action, target,
    and UTC timestamp. Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `asset-`, `find-`, `risk-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m cyber serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, ingest, triage, manage_assets, manage_risks, assess_controls, audit_read, admin |
| `bob`   | analyst | read, ingest, triage, manage_assets, manage_risks, assess_controls |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

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
created_by, created_utc, updated_utc}` with sequential ids `asset-1`,
`asset-2`, …; finding and risk dicts follow the same pattern with
their own prefixes (see `UNION-SPEC.md` for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**194 tests, OK** at delivery, including a mutation-verified
negative control on the risk-scoring function (see
`tests/README.md`). With the additions module: **204 tests, OK**.

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 Moderate
baseline cross-walked to the NIST SP 800-171 Rev. 2 practices that
define CMMC L2:

- **CM / RA** — asset inventory: CM-8 (system component inventory);
  RA-3 (risk assessment — criticality is the scoring input).
- **RA / IR / SI** — finding ingestion & triage: RA-5 (vulnerability
  monitoring and scanning — the register is where scan output lands);
  IR-4 / IR-5 (incident handling / monitoring — the lifecycle is the
  handling record); SI-10 (information input validation — malformed
  batches are rejected whole).
- **RA / CA** — risk scoring & register: RA-3; CA-2 (control
  assessments), CA-5 (plan of action and milestones — the register is
  the POA&M-shaped record).
- **CA** — control mapping & assessment: CA-2, CA-5, CA-7
  (continuous monitoring — assessment status is the monitoring
  record).
- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement), AC-6 (least privilege); IA-2
  (identification & authentication — identity is supplied by the
  embedding organization via user/role headers; this service ships
  hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit
  information — append-only store, audit-read restricted to the
  `audit_read` permission).
- **SC** — transmission: SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here).

## Honesty: what is NOT in this build

The union spec ranks 25 functions across the 54 siblings; the
substrate behind 11 of them is implemented here. The following
**Extended functions are specified and ranked in `UNION-SPEC.md` but
are NOT implemented** in this build — in every case the product-side
engine is what is missing; where an engine's *output* is a finding,
that output is ingestible by the core above:

- AI/ML-powered analytics & anomaly detection (17 siblings) — risk
  scoring here is a published deterministic formula, not a model
- Automation & orchestration engines / SOAR (14)
- Detection engines and staffed SOC / managed-response services
  (13) — ingestion, triage, and tracking of their output is Core;
  detecting is not
- Network security enforcement: segmentation, firewall/WAF, ZTNA/SSE,
  browser isolation (11)
- Threat-intelligence feeds, curation, and research (9)
- Backup, recovery & data-protection products (9)
- Full GRC automation suites (8) — control mapping & assessment is
  Core; framework automation, evidence-collection connectors, and
  auditor workflows are not
- Identity, authentication & privileged-access products (8) — the
  build ships access-control hooks, not an IdP
- Endpoint security agents, EDR & XDR platforms (7)
- Phishing simulation & security-awareness training (7)
- Insider-risk, DLP & data-security monitoring engines (7) — their
  alerts arrive in Core as findings
- Application-security testing engines: SAST/DAST/SCA, penetration
  testing (6) — their results are ingested by Core
- Cloud & SaaS posture engines: CSPM/CNAPP/SSPM (5) — their
  misconfiguration findings are ingested by Core
- Log & telemetry pipelines and security data lakes (5)
- Vulnerability scanners (4) — ingestion, consolidation, and
  tracking of scanner output is Core; scanning is not
- Secure enclaves / VDI for CUI (3)
- Identity proofing & fraud prevention (2)
- Endpoint management, patching & IT automation agents (2)

Further, plainly:

- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly, and not
  claimed here. (5 siblings claim encryption/key management as a
  product function; no key-management service is implemented.)
- **Function counts are a floor.** Spec claims are tagged only where
  a sibling's own marketplace description phrases the function
  recognizably; Rapid7's suite, for example, earns no
  vulnerability-management claim because its description never says
  so in matching words, even though its InsightVM component is one.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not an
  identity provider**. Production identity, authentication strength,
  and account lifecycle belong to the embedding organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which baseline families the build's features answer
  to; nothing more.
