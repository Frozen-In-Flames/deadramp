# Union Spec — Cybersecurity & Risk Management, L3-adjacent (16 forks)

**Group:** The 16 FedRAMP High offerings in the Cybersecurity & Risk
Management category (`forks.json`: category "Cybersecurity & Risk
Management", `cmmc_tier` "L3-adjacent"). The member list was
reconciled against MAP.md's "Cybersecurity & Risk Management —
L3-adjacent (16)" section with **zero diffs**: every MAP.md row matches
a forks.json entry and vice versa. All 16 are FedRAMP High; all 16 are
SaaS. Authorization statuses in the source: Certified (11), Agency
Authorization In Process (2 — xDome for Government, Wraithwatch
Government), Legacy FedRAMP Ready (3 — NetCloud Federal, NinjaOne for
Government, Optum Serve Federal Platform).

Members: Caveonix (Caveonix, Inc.); xDome for Government (Claroty);
Cyera for Government (Cyera); NetCloud Federal (Ericsson); Keeper ICAM
& Identity Security Platform for Government (Keeper Security); NinjaOne
for Government – FedRAMP High (NinjaOne); Optum Serve Federal Platform
(Optum Serve); Idira Endpoint Privilege Manager for Government and
Idira Identity Security Government Services Platform (Palo Alto
Networks); Qualys Government Platform (Qualys, Inc.); Saviynt High
Security Identity Platform (Saviynt); The Armory (stackArmor); Xacta
SaaS (Telos Corporation); Wraithwatch Government (Wraithwatch
Corporation); Zscaler Internet Access - Government (Secure Web Gateway
- vTIC) - High and Zscaler Private Access - Government (Zscaler).

**This group is a cross-tier merge.** Per the Merge Rule in
`crosswalk.md` (union of baselines, highest tier wins, control
traceability), this build **extends the shipped Cybersecurity L2
merged build** (`groups/cybersecurity-l2/src`, DeadRamp's own
Apache-2.0 code, reused with the reuse stated here and in the group
README) merged with these 16 High-tier forks, and must satisfy the
**higher** tier in full: the NIST SP 800-53 Rev. 5 **High** baseline,
which `crosswalk.md` maps to CMMC L3-adjacent (800-171 plus the
800-172 subset). The L2 group's 11 core functions are carried upward
whole — the Merge Rule takes the union of the parents, never the
intersection, and a smaller claim count at High is not a downgrade
(the same principle Group 6 recorded for Collaboration L3-adjacent).
What changes at High is the platform layer: Section 4 lists the uplift
analysis; the group README lists the code-level reuse.

The result is one clean-room merged build. Nothing here copies any
vendor's code, text, interface, or branding; the taxonomy below is
DeadRamp's own, and every count is derived from the GSA marketplace
dataset by the method described next.

## How functions were counted (same method as Groups 1–7)

Each fork's public marketplace description was matched
deterministically (keyword/regex rules, committed in
`scratch/extract.py`) against **the same fixed 25-function taxonomy
Group 4 defined for this category** — reused verbatim, not re-derived,
so claim counts are comparable across tiers:

`vuln_management`, `endpoint_detection`, `detection_response`,
`threat_intel`, `identity_access`, `fraud_identity`,
`compliance_grc`, `risk_scoring`, `data_protection`,
`cloud_saas_security`, `network_security`, `app_security`,
`phishing_awareness`, `insider_dlp`, `asset_inventory`,
`endpoint_management`, `ai_ml`, `reporting_dashboards`,
`audit_logging`, `access_control_feature`, `encryption_feature`,
`api_integration`, `automation`, `log_telemetry`, `secure_enclave`.

A fork "claims" a function when matched text asserts the offering
itself provides it (the source sentence is stored as evidence in
`specs/specs.json`). Counts are a **floor**: functions a product
offers but its marketplace blurb never mentions are invisible to this
method and are not invented.

**Claims: 15 of the 16 forks claim at least one function; 60 claims
in total** (71 raw matches, 11 dropped by the corrections below).
The one zero-claim fork is **NetCloud Federal** (Ericsson): its
description is SD-WAN / network-connectivity prose that asserts no
function in the taxonomy — the full text is preserved in its spec
sheet and nothing was invented for it.

### Wording-artifact corrections (Group 4's discipline, applied here)

Group 4's rule: a claim stands only when the matched text asserts a
customer-facing function **of the offering itself**. Four forks needed
corrections in this group (11 claims dropped):

1. **Wraithwatch Government (FR2612836790)** — dropped
   `vuln_management`, `endpoint_detection`, `detection_response`,
   `log_telemetry`, `reporting_dashboards`. All five rested on its
   data-source enumeration sentence ("endpoint detection and
   response, SIEM, identity providers, vulnerability scanners…") —
   systems whose output Wraithwatch *explores* in customers' existing
   SIEM indexes, not functions it provides — or on "reporting" as a
   noun for published disclosures ("supply chain compromise
   reporting"). Kept: `threat_intel`, `compliance_grc`,
   `api_integration` (its own stated mechanism).
2. **The Armory (FR2513256853)** — dropped `insider_dlp` (the matched
   text was a "Discover more" link label naming ISV partner Qanapi's
   product tagline) and `ai_ml` (bare "AI" inside a dependent product
   name, "Patlytics AI Platform"). Kept: `encryption_feature`,
   `data_protection`, `api_integration`, `reporting_dashboards` —
   Qanapi is a listed constituent ISV service of the Armory offering,
   so prose asserting its capabilities is an assertion about the
   offering; the drops above are the link-label and bare-name cases.
3. **Idira Identity Security Government Services Platform
   (FR2001619337)** — dropped `phishing_awareness` ("Phishing-Resistant
   MFA" is an authentication property, already claimed by
   `identity_access`'s pattern), `network_security` (bare "firewall"
   in "without the need for VPNs or invasive firewall modifications"
   — what the connector avoids, not a network-security function it
   provides), `secure_enclave` ("virtual desktops" inside a coverage
   enumeration of protected targets).
4. **Zscaler Private Access - Government (FR1719759604)** — dropped
   `secure_enclave` ("VDI alternative" is positioning *against* VDI;
   the offering replaces VDI, it does not provide one).

Borderline calls kept, for the record: Keeper's `endpoint_management`
(via "remote access", a named component of its delivered platform);
Idira ISGP's `insider_dlp` (privileged-session monitoring "to
mitigate insider threats" is an asserted PAM function of the
offering); Qualys's `cloud_saas_security` ("misconfigurations" inside
its VMDR-for-cloud sentence).

The group's character at High, in one line: this is an
**identity-and-boundary group** — identity platforms (Idira ×2,
Keeper, Saviynt) and zero-trust network services (Zscaler ×2,
Claroty, Ericsson) dominate, listings are enclave and boundary prose,
and claim mass sits in identity, platform, and reporting families.
Per-claimant engines (EDR agents, scanners, DLP enforcement) do not
become shared substrate at either tier; they are the extended
functions below, exactly as Group 4 scoped them.

## Function ranking — claims across the 16 forks

| # | Function | Claims | Disposition |
|---|----------|-------:|-------------|
| 1 | identity_access | 7 | Extended — identity products proper (IdP, PAM, IGA, MFA engines). Only the access-control *hooks* are core (function 10). |
| 2 | reporting_dashboards | 6 | **Core** — posture reporting |
| 3 | compliance_grc | 4 | **Core substrate** — control mapping & assessment |
| 4 | audit_logging | 4 | **Core** — audit log (uplifted at High, Section 4) |
| 5 | endpoint_management | 4 | Extended — endpoint management agents |
| 6 | access_control_feature | 4 | **Core** — access control (uplifted at High, Section 4) |
| 7 | vuln_management | 3 | **Core substrate** — ingestion, tracking, lifecycle; scanners are Extended |
| 8 | insider_dlp | 3 | Extended — DLP engines; alerts arrive as findings |
| 9 | ai_ml | 3 | Extended — detection models and AI engines; scoring here is a deterministic formula |
| 10 | network_security | 3 | Extended — network enforcement planes; their output arrives as findings |
| 11 | api_integration | 3 | **Core** — API-first platform surface |
| 12 | detection_response | 2 | **Core substrate** — ingestion/triage of detection output; engines and SOCs are Extended |
| 13 | encryption_feature | 2 | Platform note — TLS when configured; FIPS-validated cryptography is a baseline gap at High (SC-13, Section 4) |
| 14 | asset_inventory | 2 | **Core** — asset inventory |
| 15 | data_protection | 2 | Extended — backup/recovery products proper |
| 16 | automation | 2 | Extended — SOAR and workflow engines |
| 17 | threat_intel | 2 | Extended — intel feeds and curation |
| 18 | endpoint_detection | 1 | Extended — EDR agents proper |
| 19 | cloud_saas_security | 1 | Extended — posture engines proper; their findings are ingested |
| 20 | risk_scoring | 1 | **Core** — deterministic finding scoring and the risk register (carried up whole from the L2 parent; the Merge Rule's union, and the substrate presupposes it) |
| 21 | phishing_awareness | 1 | Extended — phishing defense is Zscaler's inline enforcement here; simulation/training *content* as in Group 4 |
| 22 | fraud_identity | 0 | Extended — identity-proofing/fraud products; zero claims in this group, retained for cross-group comparability |
| 23 | app_security | 0 | Extended — AppSec engines; zero claims in this group |
| 24 | log_telemetry | 0 | Extended — log pipelines/streaming; zero claims after correction (Wraithwatch's matched text was an ingestion-source artifact) |
| 25 | secure_enclave | 0 | Extended — CUI enclaves/VDI; zero claims after corrections (both matched instances were artifacts) |

The core is Group 4's 11 functions, unchanged as a set, at High.
Functions 1, 5, 8–10, 15–19, 21–25 are the long tail: real products
exist behind them, and they are named here rather than blended into a
core they would distort. Identity being the #1 family at High (7 of
16) does not move it into the core: IdP/PAM/IGA engines are
per-vendor products with no shared substrate surface, the same
scoping Group 4 applied at Moderate (8 of 54).

## The core — 11 functions, inherited and uplifted

The core is a **defensive substrate**: the shared data model and
workflow every sibling presupposes, with no offensive capability and
no engines. Its definition is Group 4's, verbatim in substance;
functions 10 and 11 carry the High uplifts, marked **[L3]**.

1. **Asset inventory** — register the systems under management:
   name, kind (server, workstation, network device, cloud service,
   application, database, other), owner, free-form labels, lifecycle
   status (active, decommissioned), and a criticality rating (low,
   medium, high, critical) that feeds scoring.
2. **Finding ingestion** — findings arrive from scanners, sensors,
   audits, and humans (never produced by scanning here): title,
   description, source, CVE id, affected asset, severity, status.
   Single, bulk, and CSV paths; bulk and CSV are **atomic** (validate
   everything, then commit; a bad row creates nothing and consumes
   no ids, and the error names the row).
3. **Finding triage & lifecycle** — findings move through a fixed
   lifecycle (`new` → `triaged` → `confirmed` → `in_remediation` →
   `resolved`, with `accepted_risk` and `false_positive` exits);
   illegal jumps are rejected, terminal states are final, assignment
   only to known users.
4. **Deterministic risk scoring** — every finding carries a score
   computed from two declared inputs only: severity weight × asset
   criticality weight, with severity bands (critical ≥ 8, high ≥ 5,
   medium ≥ 2.5, else low). Same inputs, same score, on every machine
   — the anti-ML: explainable, testable, reproducible.
5. **Risk register** — risks beyond single findings: title,
   description, linked asset (optional), likelihood × impact (1–5
   each) for an inherent score 1–25, bands (critical ≥ 15, high ≥ 10,
   medium ≥ 5), lifecycle (`identified` → `assessed` → `mitigating`
   → `accepted` / `closed`).
6. **Control mapping & assessment** — a built-in catalog of 34 NIST
   SP 800-53 Rev. 5 controls (id, family, title) spanning the
   families the siblings' marketing names; per-control assessment
   state (not assessed, implemented, partially implemented, planned,
   not applicable), assessor, free-text evidence notes. Assessment
   machinery is data; it confers no authorization on anyone.
7. **Search & filtering** — full-text and faceted search across
   findings (title, description, source, CVE, asset), assets, and
   risks: structured filters plus deterministic ranking (relevance,
   then score, then recency).
8. **Posture reporting** — counts and rollups computed from the data,
   never stored opinions: findings by status / severity band /
   source, asset criticality distribution, risk band distribution,
   control posture by family, and a plain-text summary. Rendered as
   JSON from the API and as text from the CLI.
9. **API access** — the full substrate over a REST JSON API; every
   operation the CLI does is an API operation. **[L3]** The service
   layer adds unsuccessful-logon lockout (AC-7) and the
   `GET /audit/verify` endpoint.
10. **Access control** — role-based permissions enforced on every
    operation: **admin** (everything), **analyst** (read plus the
    working set), **viewer** (read-only). **[L3]** A fourth role is
    added at High: **auditor**, holding `audit_read` and nothing
    else (AC-5 least privilege).
11. **Audit log** — append-only record of every state-changing
    operation, every read of posture/report data, every denied
    access, and every authentication failure: timestamp, actor,
    action, target, details. **[L3]** At High the log is a
    **hash-chained, tamper-evident** trail with chain verification,
    **fail-closed** writes, and **query/reduction** (Section 4).

**Non-goals, explicit:** no vulnerability scanning, no packet
capture, no exploitation tooling, no endpoint agents, no network
enforcement, no ML models. Engines that produce findings are
extended functions; this build consumes their output.

## Baseline and traceability (FedRAMP High ⇔ CMMC L3-adjacent)

Baseline source: NIST SP 800-53 Rev. 5, **FedRAMP High** baseline.
Per `crosswalk.md`, FedRAMP High maps to CMMC **L3-adjacent**:
NIST SP 800-171 in full plus the NIST SP 800-172 enhanced-requirement
subset that FedRAMP High's additional controls represent. **Standing
caveat:** FedRAMP authorizes *products*; CMMC certifies
*organizations*. The tier labels in this repo are planning and
matching equivalences, never credential claims — implementing
controls from a baseline does not make this software authorized or
certified under either program, and nothing in this group claims
otherwise.

### Tier-uplift analysis — what High demands beyond the L2 build

The Merge Rule requires the merged fork to satisfy the **highest**
tier of its parents **in full**. The table below is the uplift from
the Cybersecurity L2 (Moderate) parent: what High adds, and the
disposition of each addition in this build. It mirrors the pattern
Groups 3 and 6 applied.

| Area | High requirement (800-53 Rev. 5) | Disposition |
|------|-----------------------------------|-------------|
| Audit integrity | AU-9 protection of audit information; AU-3 content of audit records | **Implemented** — every entry gains `seq`, `prev_hash`, `hash` (SHA-256 over the canonical JSON of {seq, ts, actor, action, target, details, prev_hash}); genesis `prev_hash` `"0"*64`; `AuditLog.verify_chain()` → `(ok, first_bad_index)`; `GET /audit/verify` endpoint. |
| Audit failure response | AU-5 | **Implemented, fail-closed** — a failed JSONL append rolls back the in-memory entry and raises `AuditWriteError`. The store rolls the whole operation back with it: audited methods snapshot state first and restore on audit failure, so no object is created, no id is consumed, no lifecycle state moves. |
| Audit reduction | AU-7 audit reduction and report generation | **Implemented** — `AuditLog.query(actor, action, target, since, until)`; `GET /audit` passes the same five filters through. |
| Unsuccessful logon | AC-7 | **Implemented** — per-username consecutive-failure counting in the service layer; at the threshold (`max_failures`, default 3) the username locks for `lockout_seconds` (default 300); locked attempts get 403 and are audited as `auth:locked`; a success resets the counter; expiry clears the lock. CLI flags `--max-failed-logins` / `--lockout-seconds`. |
| Least privilege | AC-5 / AC-6 separation of duties, least privilege | **Implemented** — fourth role **auditor** = `{audit_read}` only; demo user `dana`. |
| Personnel / media / physical families | PS, MP, PE families enter the High baseline for the *deployment* | Deployment-layer: no software surface in a stdlib substrate. Named here so the baseline delta is visible, not silently dropped. |
| Identification & authentication | IA-2(1)/(2) MFA for network/privileged access; IA-5 authenticator management | **Gap** — this substrate has no credential store at all: identity arrives as caller-asserted headers (Group 4's documented trust model). Real MFA and authenticator management belong to the identity layer. Registered as a platform baseline gap. |
| Cryptography | SC-13 FIPS-validated cryptographic modules | **Gap** — Python's hashlib is not a FIPS-validated module and is not represented as one. Registered as a platform baseline gap. |
| Data at rest | SC-28 protection of information at rest | **Gap** — the substrate keeps data in memory / operator-chosen JSONL; at-rest encryption is a deployment-layer control. Registered as a platform baseline gap. |
| Audit retention | AU-11 audit record retention | **Gap** — the JSONL trail has no retention/archival policy engine. Registered as a platform baseline gap. |
| Session controls | AC-11 session lock; AC-12 session termination | **Gap** — sessions are per-request header assertions; there is no session to lock or terminate. Registered as a platform baseline gap. |

Nothing in the L2 core weakened at High: the uplift is additive
(union, per the Merge Rule). Operating-system and deployment
controls (TLS termination, host hardening, backup) remain the
deployment's, as in every DeadRamp group.

### Feature → control-family traceability

Group 4's mapping, unchanged, with the High additions marked **[L3]**:

| Core function | NIST SP 800-53 families it exercises |
|---------------|---------------------------------------|
| Asset inventory | CM-8 (system component inventory), PM-5 |
| Finding ingestion | RA-5 (vulnerability monitoring), SI-4 (system monitoring), CA-8 |
| Finding triage & lifecycle | RA-5, IR-4 (incident handling), SI-2 (flaw remediation) |
| Deterministic risk scoring | RA-3 (risk assessment) |
| Risk register | RA-3, PM-9 (risk management strategy) |
| Control mapping & assessment | CA-2 (control assessments), CA-5 (POA&M — posture data), PM-10 |
| Search & filtering | RA-5, SI-4 (query surfaces over monitoring data) |
| Posture reporting | CA-7 (continuous monitoring), PM-14 |
| API access | SC-7 (boundary protection — API is the boundary), AC-3 |
| Access control | AC-2, AC-3, AC-6; **[L3]** AC-5 (auditor role), AC-7 (logon lockout) |
| Audit log | AU-2, AU-3, AU-6, AU-12; **[L3]** AU-9 (hash chain), AU-5 (fail-closed writes), AU-7 (query/reduction) |

The tests cite the same families per test class, so a test name can
be traced back to a control family and forward to the function whose
claims ranked above.

## Implementation contract

One Python package, `cyber`, standard library only, no third-party
dependencies. Group 4's contract, with this group's deltas marked
**[L3]**:

- **Reuse:** `groups/cybersecurity-l2/src/cyber/__init__.py` and
  `catalog.py` are byte-identical to the L2 parent. `errors.py`,
  `audit.py`, `access.py`, `store.py`, `service.py`, and
  `__main__.py` carry the uplifts below. (The parent spec's contract
  mentions a `csvutil.py` module; no such file exists in the parent
  build — CSV parsing lives inline in `store.py` — and none was
  invented here.)
- `errors.py` — the `CyberError` hierarchy (ValidationError,
  NotFoundError, PermissionDenied, InvalidTransitionError,
  ConflictError). **[L3]** Adds `AuditWriteError(CyberError)`.
- `audit.py` — append-only audit log, optional JSONL persistence.
  **[L3]** Fully rewritten: hash-chained entries (`seq`,
  `prev_hash`, `hash`), `verify_chain()`, `query(...)` filters,
  fail-closed `record()` with rollback and `AuditWriteError`.
- `access.py` — users are (name, role); role → permission set is a
  closed table. **[L3]** Adds the `auditor` role = `{audit_read}`
  only. Permissions: `read`, `ingest`, `triage`, `manage_assets`,
  `manage_risks`, `assess_controls`, `audit_read`, `admin`.
- `catalog.py` — the built-in 34-control SP 800-53 Rev. 5 catalog
  (id, family, title) and family derivation. Byte-identical.
- `store.py` — in-memory store; ids `asset-N` / `find-N` / `risk-N`
  from per-kind counters, never reused after success; failed
  operations (validation *or* audit failure) consume no ids.
  **[L3]** Audited methods run fail-closed: state is snapshotted
  before the mutation and restored if the audit write fails.
  `score_finding(severity, criticality)` is the single scoring
  function.
- CSV parsing (CRLF/LF, quoting, blank-line skipping, physical line
  numbers) lives inline in `store.py`, as in the parent build.
- `service.py` — `http.server`-based REST API; the CLI is `serve`
  (the parent spec's mention of a `demo` subcommand does not exist in
  the parent code and was not invented here); TLS via
  `--certfile`/`--keyfile` when provided (deployment layer). **[L3]** `make_server(..., max_failures=3,
  lockout_seconds=300)` adds AC-7 lockout; `GET /audit/verify` route;
  `GET /audit` filter parameters (`actor`, `action`, `target`,
  `since`, `until`); `AuditWriteError` from the audit step propagates
  instead of being swallowed.
- `__main__.py` — **[L3]** demo users gain `dana` (auditor);
  `--max-failed-logins` / `--lockout-seconds` flags on `serve` and
  `demo`.
- Every store operation checks its permission first, mutates second,
  audits last-but-atomically **[L3:** an audit failure unwinds the
  mutation**]**; denied operations are audited and consume no ids.

## Coverage statement

- Spec sheets: **16 of 16** forks (`specs/specs.json`), each with the
  source sentence stored as evidence per claim.
- Core functions implemented: **11 of 11**, carried up from the L2
  parent and uplifted to the High baseline where High demands more
  (Section 4).
- Tests: **236 passing** (`tests/README.md` has the layout, the
  traceability convention, the negative controls — including the
  audit-tamper control new at this tier — and the mutation
  verification record).
- Extended functions not implemented (the long tail, for the final
  gap batch): identity products, endpoint management agents, DLP
  engines, AI/ML detection models, network enforcement planes, backup
  & recovery products, SOAR/workflow automation, threat-intel feeds,
  EDR agents, cloud/SaaS posture engines, phishing simulation/training
  content, fraud/identity-proofing products, AppSec engines, log
  pipelines, CUI enclaves/VDI, vulnerability scanners.
- Platform baseline gaps at High (for the final gap batch): MFA /
  authenticator management (IA-2(1)/(2), IA-5), FIPS-validated
  cryptography (SC-13), encryption at rest (SC-28), audit retention
  (AU-11), session lock/termination (AC-11/AC-12).
