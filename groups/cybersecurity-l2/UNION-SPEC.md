# Union Spec — Cybersecurity & Risk Management, CMMC L2 (DeadRamp Phase 2, Group 4)

The merged functional spec for the fourth sibling group: **54 forks**,
category **Cybersecurity & Risk Management**, CMMC tier **L2** (every
member is FedRAMP **Moderate** in `forks.json` — verified, so the group
is single-tier and the merge takes the group baseline in full, per
Merge Rule 2). The member list in `forks.json` was reconciled against
`MAP.md`'s "Cybersecurity & Risk Management — L2 (54)" section:
**zero diffs**.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 54
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced by
the General Services Administration, last change 2026-10-22), product
records joined by FedRAMP ID. No live fetching was needed: all 54
descriptions were present in the cached dataset.

## How functions were counted

A fixed 25-function taxonomy for this category was matched against
each offering's own public description. A function is claimed for a
fork **only** when the description contains matching text; the
matching sentence is stored as the claim's evidence in the spec sheet.
All 54 offerings carry at least one tagged claim (204 claims total),
so nothing needed to be hidden — but counts are still a **floor**,
not a ceiling: Rapid7's suite, for example, plainly includes
vulnerability management (its InsightVM component), yet the word
"vulnerability" never appears adjacent to a scanning/management phrase
in its marketplace description, so no claim was tagged for it.

Four wording-artifact corrections were applied to the matcher and are
recorded here:

- `compliance_grc` does not match bare "continuous monitoring" or
  "maintain compliance": both phrases appear in descriptions as
  vendor-side boilerplate about the *vendor's own* authorization
  posture (a Ransomware Operations Center's monitoring service, an
  SD-WAN vendor's own boundary ConMon, an AppSec vendor's own
  environment) rather than a customer-facing GRC function. The family
  requires a strong marker instead (GRC, compliance
  automation/platform/management/posture/program, continuous
  authorization, continuous compliance, evidence collection, control
  mapping, audit-ready, compliance frameworks). This dropped six
  false claims (Absolute, Cisco SD-WAN, Halcyon, AppOmni, Checkmarx,
  and one more) and kept the eight genuine GRC offerings.
- `compliance_grc` does not match the bare acronym "ATO": it fired on
  a vendor describing its *own* authorization. The spelled-out
  "authorization to operate" and "continuous authorization" still
  match (ASSYST's ComplySyncATO keeps its claim on that basis).
- `automation` does not match "automates the …" generically: a data
  pipeline vendor "automating the management of data types" is data
  plumbing, not security automation/orchestration. The family
  requires automation of a workflow, response, remediation, security,
  segmentation, or policy object, or an orchestration claim.
- A `log_telemetry` family was added after the first pass left
  Cribl.Cloud Government — an observability/log pipeline whose output
  feeds SIEMs — with no honest claim at all. The family (log &
  telemetry collection, pipelines, security data lakes) is grounded
  in five siblings' own descriptions, Cribl's included.

## Function ranking — all 54 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | APIs & integrations | 19 | 35% | **Core** (the service is API-first) |
| 2 | AI/ML-powered analytics & anomaly detection | 17 | 31% | Extended (detection models and AI scoring engines; this build's risk scoring is a published deterministic formula, not ML — stated plainly) |
| 3 | Dashboards, reporting & analytics | 16 | 30% | **Core** (posture reporting) |
| 4 | Automation & orchestration | 14 | 26% | Extended (SOAR and workflow engines; the finding lifecycle in Core is a workflow, not an orchestration engine) |
| 5 | Threat detection, SOC & managed response (SIEM/SOAR/MDR) | 13 | 24% | **Core substrate** (ingestion, triage, and tracking of detection output; the detection engines and staffed SOCs themselves are Extended) |
| 6 | Network security, segmentation & zero-trust access | 11 | 20% | Extended (enforcement planes: segmentation, firewall/WAF, ZTNA/SSE, browser isolation) |
| 7 | Threat intelligence | 9 | 17% | Extended (intel feeds, curation, and research services) |
| 8 | Backup, recovery & data protection | 9 | 17% | Extended (backup/vaulting/recovery products) |
| 9 | GRC, compliance automation & continuous authorization | 8 | 15% | **Core substrate** (control mapping & assessment, the register every GRC suite presupposes; full GRC automation suites are Extended) |
| 10 | Identity, authentication & privileged access | 8 | 15% | Extended (identity products; this build ships access-control *hooks*, not an IdP) |
| 11 | Access control & least privilege (platform feature) | 8 | 15% | **Core** (L2 baseline hooks) |
| 12 | Endpoint security, EDR & XDR | 7 | 13% | Extended (endpoint agents and response platforms) |
| 13 | Audit logging & activity trails | 7 | 13% | **Core** (L2 baseline hooks) |
| 14 | Phishing defense & security awareness training | 7 | 13% | Extended (simulation and training content) |
| 15 | Insider risk, DLP & data security | 7 | 13% | Extended (monitoring engines; their alerts arrive in Core as findings) |
| 16 | Risk assessment, scoring & third-party risk | 6 | 11% | **Core** (deterministic finding scoring + the risk register) |
| 17 | Application security testing & API security | 6 | 11% | Extended (SAST/DAST/SCA and pentest engines; their results are ingested by Core) |
| 18 | Asset inventory, visibility & attack surface | 6 | 11% | **Core** (the asset register) |
| 19 | Cloud & SaaS security posture (CSPM/CNAPP/SSPM) | 5 | 9% | Extended (posture engines; their misconfiguration findings are ingested by Core) |
| 20 | Encryption & key management | 5 | 9% | Platform note (TLS supported; see baseline section) |
| 21 | Log & telemetry collection, pipelines & security data lakes | 5 | 9% | Extended (pipeline routing; Core ingests the findings those pipelines feed) |
| 22 | Vulnerability scanning & management | 4 | 7% | **Core substrate** (ingestion, consolidation, and tracking of scanner output — the Nucleus/Tenable pattern; the scanners themselves are Extended) |
| 23 | Secure enclave / VDI for CUI | 3 | 6% | Extended (hosted enclave environments) |
| 24 | Identity proofing & fraud prevention | 2 | 4% | Extended (proofing/fraud-scoring services) |
| 25 | Endpoint management, patching & IT automation | 2 | 4% | Extended (management agents) |

**A deliberate scoping note for a security-tools group:** the merged
build implements the *defensive platform substrate* the siblings
share — the register of assets, the findings those tools produce,
their triage, the risk register, and the control map. It implements
**no offensive tooling and no detection/enforcement engine**: no
scanner, no agent, no firewall, no phishing simulator. Those engines
are the Extended tail, named above with their sibling counts; the
per-fork spec sheets name which siblings claim each.

**Differences are preserved, not averaged away**: the long tail
(identity proofing, hosted CUI enclaves, backup vaulting, browser
isolation, awareness training, pentest services) is the record of how
the siblings differ. Each Extended function names the claim family and
its sibling count; the per-fork spec sheets name which siblings claim
it.

## The Core — what the merged build implements (11 functions)

One coherent, standards-based security-operations register that every
sibling's output presupposes, built clean-room from this spec:

1. **Asset inventory** — a register of assets (name, kind, owner,
   criticality, tags) with provenance (who created it, when).
   Criticality changes recompute the scores of that asset's findings.
2. **Finding ingestion** — findings (the output of scanners, posture
   engines, detection platforms, and tests) enter one at a time, in
   bulk (JSON), or as CSV scan results. A batch is atomic: one bad
   row rejects the whole batch, nothing is partially applied, no ids
   are consumed.
3. **Finding triage & lifecycle** — findings move through a fixed
   lifecycle (`new → triaged → in_progress → mitigated / accepted`,
   with `false_positive` and `closed` per the transition map) with
   assignment. Invalid transitions are rejected, never silently
   applied.
4. **Risk scoring** — a deterministic, published score per finding:
   severity weight × asset criticality weight, with a named band.
   Same inputs, same score, always (no ML, no hidden model).
5. **Risk register** — standing risks with likelihood × impact
   scoring (1–25) and bands, an owner, a lifecycle, and links to the
   findings that evidence them.
6. **Control mapping & assessment** — a built-in catalog of 34
   NIST SP 800-53 Rev. 5 controls; findings link to controls at
   ingest, and each control carries an assessment status and
   evidence note, so coverage is a query, not a spreadsheet.
7. **Search & filtering** — findings filtered by
   severity/status/asset/source and substring; assets and risks by
   substring; one cross-object search.
8. **Posture reporting** — a summary: assets by criticality, findings
   by severity and status, the top open findings by score, risks by
   band and status, control coverage.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `analyst`, `viewer` with a permission matrix enforced on
    every operation.
11. **Audit log** — an append-only audit trail: every asset, finding,
    risk, and control-assessment mutation, every search, and every
    denied attempt is recorded with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110 practices
  of NIST SP 800-171 Rev. 2 that define CMMC L2. All 54 parent forks
  sit at Moderate, so the union baseline is the Moderate baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Asset inventory → **CM** (CM-8 system component inventory),
    **RA** (RA-3 risk assessment — criticality is the input that
    makes scoring possible).
  - Finding ingestion & triage → **RA** (RA-5 vulnerability
    monitoring and scanning — the register is where scan output
    lands), **IR** (IR-4 incident handling, IR-5 incident monitoring
    — the lifecycle is the handling record), **SI** (SI-10
    information input validation — malformed batches are rejected
    whole, never partially applied).
  - Risk scoring & risk register → **RA** (RA-3), **CA** (CA-2
    control assessments, CA-5 plan of action and milestones — the
    register is the POA&M-shaped record).
  - Control mapping & assessment → **CA** (CA-2, CA-5, CA-7
    continuous monitoring — assessment status is the monitoring
    record).
  - Access control → **AC** (AC-2 account management, AC-3 access
    enforcement, AC-6 least privilege), **IA** (IA-2 identification
    & authentication — identity is supplied by the embedding
    organization via user/role headers; the service ships hooks,
    not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit information
    — append-only store, admin-only read).
  - Posture reporting → **CA** (CA-7), **AU** (AU-6 audit review —
    the summary is a review surface).
  - Transmission → **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `cyber` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`asset-`, `find-`, `risk-`); a failed
operation consumes no id and changes nothing. All timestamps are UTC
ISO-8601.

- `cyber/errors.py` — `CyberError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `CyberError`).
- `cyber/access.py` — `User(name, role)`; roles
  `admin|analyst|viewer`; actions `read, ingest, triage,
  manage_assets, manage_risks, assess_controls, audit_read, admin`.
  `PERMISSIONS`: admin ⊇ all eight; analyst = {read, ingest, triage,
  manage_assets, manage_risks, assess_controls}; viewer = {read}.
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`. Unknown role or action is
  denied.
- `cyber/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL
  file persistence; reloads an existing file on construction.
- `cyber/catalog.py` — `CONTROL_CATALOG`: a list of 34 dicts
  `{id, family, title}` covering these NIST SP 800-53 Rev. 5 controls
  (family is the id's alphabetic prefix):
  AC-2 Account Management; AC-3 Access Enforcement; AC-6 Least
  Privilege; AC-17 Remote Access; AT-2 Literacy Training and
  Awareness; AU-2 Event Logging; AU-3 Content of Audit Records;
  AU-6 Audit Record Review, Analysis, and Reporting; AU-9 Protection
  of Audit Information; CA-2 Control Assessments; CA-5 Plan of
  Action and Milestones; CA-7 Continuous Monitoring; CM-6
  Configuration Settings; CM-7 Least Functionality; CM-8 System
  Component Inventory; CP-9 System Backup; IA-2 Identification and
  Authentication; IA-5 Authenticator Management; IR-4 Incident
  Handling; IR-5 Incident Monitoring; MP-6 Media Sanitization; RA-3
  Risk Assessment; RA-5 Vulnerability Monitoring and Scanning; SA-10
  Developer Configuration Management; SC-7 Boundary Protection;
  SC-8 Transmission Confidentiality and Integrity; SC-12
  Cryptographic Key Establishment and Management; SC-13
  Cryptographic Protection; SC-28 Protection of Information at Rest;
  SI-2 Flaw Remediation; SI-3 Malicious Code Protection; SI-4 System
  Monitoring; SI-10 Information Input Validation; SI-16 Memory
  Protection. Plus `CONTROL_IDS` (a set/frozenset of the ids) and
  `control_by_id(control_id)` returning the catalog dict or `None`.
- `cyber/store.py` — constants and the store:
  - `SEVERITIES = ("critical", "high", "medium", "low", "info")`;
    `SEVERITY_WEIGHTS = {"critical": 5, "high": 4, "medium": 3,
    "low": 2, "info": 1}`.
  - `CRITICALITIES = ("critical", "high", "medium", "low")`;
    `CRITICALITY_WEIGHTS = {"critical": 2.0, "high": 1.5,
    "medium": 1.0, "low": 0.5}`.
  - `score_finding(severity, criticality)` → `(score, band)` where
    `score = SEVERITY_WEIGHTS[severity] *
    CRITICALITY_WEIGHTS[criticality]` and band is `"critical"` for
    score ≥ 8, `"high"` for ≥ 5, `"medium"` for ≥ 2.5, else `"low"`.
  - `ASSET_KINDS = ("server", "workstation", "mobile", "network",
    "cloud", "application", "database", "other")`.
  - `FINDING_STATUSES = ("new", "triaged", "in_progress",
    "mitigated", "accepted", "false_positive", "closed")`;
    `FINDING_TRANSITIONS = {"new": {"triaged", "false_positive"},
    "triaged": {"in_progress", "accepted", "false_positive"},
    "in_progress": {"mitigated", "accepted"}, "mitigated":
    {"closed", "in_progress"}, "accepted": {"in_progress",
    "closed"}, "false_positive": {"closed"}, "closed": set()}`.
  - `RISK_STATUSES = ("open", "monitoring", "treated", "closed")`;
    `RISK_TRANSITIONS = {"open": {"monitoring", "treated",
    "closed"}, "monitoring": {"open", "treated", "closed"},
    "treated": {"monitoring", "closed"}, "closed": {"open"}}`.
    `risk_score(likelihood, impact)` → `likelihood * impact`;
    `risk_band(score)` → `"critical"` for ≥ 15, `"high"` for ≥ 10,
    `"medium"` for ≥ 5, else `"low"`.
  - `ASSESSMENT_STATUSES = ("not_assessed", "implemented",
    "partially_implemented", "not_implemented")`.
  - `CyberStore(audit=None)`. The store records every successful
    mutation and every search to its audit log (when one is
    attached) with the action names used below; the HTTP layer
    records denials and `audit_read` only, never duplicating store
    records. Every method validates fully before mutating: a failed
    operation changes nothing, consumes no id, and writes no audit
    entry. Methods:
    - `create_asset(name, kind, owner, criticality, actor,
      tags=None)` (action `manage_assets`) → `{id, name, kind,
      owner, criticality, tags, created_by, created_utc,
      updated_utc}`; `name` and `owner` must be non-empty strings,
      `kind` in `ASSET_KINDS`, `criticality` in `CRITICALITIES`,
      `tags` a list of strings (default `[]`). Audits `asset_create`.
    - `get_asset(asset_id, actor)` (action `read`) → the asset dict
      (`NotFoundError`). `list_assets(actor, q=None)` → asset dicts
      in id order; `q` is a case-insensitive substring over name and
      owner.
    - `update_asset(asset_id, actor, owner=None, criticality=None,
      tags=None)` (action `manage_assets`) → the updated asset dict;
      at least one field must be given, values validated as in
      `create_asset`. Changing `criticality` recomputes `score` and
      `band` of every finding on the asset. Audits `asset_update`.
    - `ingest_finding(item, actor)` (action `ingest`) → the finding
      dict. `item` keys: `title` (non-empty string), `severity` (in
      `SEVERITIES`), `asset_id` (must name an existing asset, else
      `ValidationError`), `source` (non-empty string), `description`
      (default `""`), `cve` (default `None`), `control_ids`
      (default `[]`; each must be in `CONTROL_IDS`, else
      `ValidationError`). The finding dict is `{id, title, severity,
      asset_id, source, description, cve, control_ids, status,
      assignee, score, band, created_by, created_utc, updated_utc}`
      with `status` `"new"`, `assignee` `None`, and score/band from
      `score_finding(severity, asset.criticality)`. Audits
      `finding_ingest` with `details` `{"count": 1, "ids": [id]}`.
    - `ingest_findings(items, actor)` (action `ingest`) → a list of
      finding dicts. **Atomic**: every item is validated before any
      is created; on any error nothing is created, no ids are
      consumed, no audit entry is written. One audit entry
      `finding_ingest` with `details` `{"count": n, "ids": [...]}`.
      An empty list raises `ValidationError`.
    - `ingest_findings_csv(text, actor)` (action `ingest`) → a list
      of finding dicts, same atomicity. The CSV must have a header
      row naming at least `title,severity,asset_id,source`; optional
      columns `description`, `cve`, `control_ids` (a
      semicolon-separated list, empty cell = `[]`). Rows are parsed
      with the stdlib `csv` module and fed through the same
      validation as `ingest_findings`.
    - `get_finding(finding_id, actor)` (action `read`) →
      (`NotFoundError`). `list_findings(actor, severity=None,
      status=None, asset_id=None, source=None, q=None)` → finding
      dicts matching all given filters (`q` is a case-insensitive
      substring over title, description, and source), sorted by
      score descending, then id ascending.
    - `transition_finding(finding_id, new_status, actor)` (action
      `triage`) → the updated finding dict. `new_status` must be in
      `FINDING_STATUSES` and in `FINDING_TRANSITIONS[current]`, else
      `ValidationError`. Audits `finding_transition` with `details`
      `{"from": old, "to": new}`.
    - `assign_finding(finding_id, assignee, actor)` (action
      `triage`) → the updated finding dict; `assignee` is a non-empty
      string or `None` (unassign). Audits `finding_assign`.
    - `create_risk(title, description, likelihood, impact, actor,
      owner="", finding_ids=None)` (action `manage_risks`) → `{id,
      title, description, likelihood, impact, score, band, status,
      owner, finding_ids, created_by, created_utc, updated_utc}`
      with `status` `"open"`; `title` non-empty; `likelihood` and
      `impact` must be integers in 1..5 (booleans are not integers
      here); every id in `finding_ids` must name an existing finding,
      else `ValidationError`. Audits `risk_create`.
    - `get_risk(risk_id, actor)` (action `read`); `list_risks(actor,
      status=None, q=None)` → risk dicts matching the filters (`q`
      over title and description), sorted by score descending, then
      id ascending.
    - `transition_risk(risk_id, new_status, actor)` (action
      `manage_risks`) → the updated risk dict; transitions per
      `RISK_TRANSITIONS`, else `ValidationError`. Audits
      `risk_transition` with `details` `{"from": old, "to": new}`.
    - `list_controls(actor)` (action `read`) → one dict per catalog
      control, in catalog order: `{id, family, title, status,
      evidence, assessed_by, assessed_utc, finding_count}` where
      `status` starts as `"not_assessed"`, `evidence` starts as
      `""`, `assessed_by`/`assessed_utc` start as `None`, and
      `finding_count` is the number of findings whose `control_ids`
      include the control.
    - `assess_control(control_id, status, actor, evidence="")`
      (action `assess_controls`) → the updated control dict (same
      shape as `list_controls` entries). Unknown `control_id` →
      `NotFoundError`; `status` must be in `ASSESSMENT_STATUSES`
      (and not `"not_assessed"` — assessing means assessing), else
      `ValidationError`. Audits `control_assess` with `details`
      `{"status": status}`.
    - `search(actor, q)` (action `read`) → `{findings, assets,
      risks}`: case-insensitive substring matches — findings over
      title/description/source, assets over name/owner, risks over
      title/description. Audits `search` with `details` `{"q": q}`.
    - `posture_summary(actor)` (action `read`) → `{assets:
      {"total": n, "by_criticality": {critical, high, medium,
      low}}, findings: {"total": n, "by_severity": {all five
      severities}, "by_status": {all seven statuses}, "open": n,
      "top_open": [...]}, risks: {"total": n, "by_status": {all
      four statuses}, "by_band": {critical, high, medium, low}},
      controls: {"total": 34, "assessed": n, "implemented": n,
      "coverage_pct": float}}` where `open` counts findings whose
      status is not `closed` or `false_positive`, `top_open` is up
      to 5 open finding dicts sorted by score descending then id
      ascending, `assessed` counts controls with status other than
      `not_assessed`, `implemented` counts controls with status
      `implemented`, and `coverage_pct` is
      `round(100 * implemented / total, 1)`. Does not audit.
- `cyber/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match the
  registry; unknown user or mismatched role → 401). Errors are JSON
  `{error}` with 400/401/403/404 as applicable; denied attempts (401
  and 403) are audited with the action name suffixed `:denied`, and
  no stack trace is ever returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /assets` (read, optional `?q=`) → `{"assets": [...]}`;
    `POST /assets` `{name, kind, owner, criticality, tags?}`
    (manage_assets) → 201
  - `GET /assets/{id}` (read); `POST /assets/{id}/update` `{owner?,
    criticality?, tags?}` (manage_assets)
  - `GET /findings` (read; `?severity=&status=&asset_id=&source=&q=`)
    → `{"findings": [...]}`; `POST /findings` (ingest, one item
    object) → 201; `POST /findings/bulk` `{findings: [...]}` (ingest)
    → 201 `{"findings": [...]}`; `POST /findings/csv` `{csv: "..."}`
    (ingest) → 201 `{"findings": [...]}`
  - `GET /findings/{id}` (read); `POST /findings/{id}/transition`
    `{status}` (triage); `POST /findings/{id}/assign` `{assignee}`
    (triage)
  - `GET /risks` (read; `?status=&q=`) → `{"risks": [...]}`;
    `POST /risks` `{title, description, likelihood, impact, owner?,
    finding_ids?}` (manage_risks) → 201; `GET /risks/{id}` (read);
    `POST /risks/{id}/transition` `{status}` (manage_risks)
  - `GET /controls` (read) → `{"controls": [...]}`;
    `POST /controls/{id}/assess` `{status, evidence?}`
    (assess_controls)
  - `GET /posture` (read) → the summary dict
  - `GET /search?q=` (read) → `{findings, assets, risks}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
- `cyber/__main__.py` — `python -m cyber serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=analyst, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring naming
the core function / spec claim it traces to, and include a **negative
control**: a mutant scoring function that ignores severity (every
severity weighted 1, so a finding's score depends only on asset
criticality). The traced claim is that severity must move the score:
a critical finding and an informational finding on the same asset
cannot score alike. For the canonical cases the test asserts the real
`score_finding` separates them (`("critical","critical")` →
`(10.0, "critical")`; `("info","critical")` → `(2.0, "low")`), that
the mutant collapses them to the same value, and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's output as
the expected output fails. The negative control must additionally be
**mutation-verified**: patching the real `score_finding` in `src/`
with the severity-blind mutant must make the suite fail; the run and
its result are recorded in `tests/README.md`.

## Coverage statement (for this build)

- Specs: 54 / 54 forks spec'd.
- Core: 11 core functions implemented, each with tracing tests.
- Extended: the product-side engines are specified and ranked, **not**
  implemented in this build (AI/ML detection models, SOAR/workflow
  orchestration engines, detection engines and staffed SOC services,
  network enforcement planes, threat-intelligence feeds, backup and
  recovery products, full GRC automation suites, identity products,
  endpoint agents, awareness-training content, DLP/insider monitoring
  engines, posture engines, log/telemetry pipelines, vulnerability
  scanners, hosted CUI enclaves, identity-proofing services, endpoint
  management agents); encryption is a platform note (TLS when a
  certificate is configured; at rest is a deployment-layer control).
