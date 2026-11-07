# Final GAPS batch — Group 8, Cybersecurity & Risk Management L3-adjacent

Unit: the 16 OPEN entries of the GAPS.md section "Group 8 —
Cybersecurity & Risk Management L3-adjacent (16 forks)". The 17th
entry in the section, "Identity products (IdP / PAM / IGA / MFA
engines)", was already closed as `re-scoped` under
`../../PLATFORM-LAYER.md` in the re-scope step and is not part of
this unit. Dispositions per `../../gaps-batch/DECISION.md`
(ratified 2026-11-07): 13 build-extension, 3 stub-engine. All 16 are
accounted for below; no entry was dropped and no disposition was
re-judged — the re-judgment qualification was considered per entry,
and §3 records why every entry's honest form is the one that landed.

## Category discipline (founding, preserved)

This build is the shared **defensive substrate only**. Nothing in
the extension module scans, detects, enforces, blocks, quarantines,
or executes. Every build-extension entry below lands in its
**records form**: registries of the engines/agents/feeds the
embedding organization runs elsewhere, ingestion records for the
output they produce, and tracking workflows over those records. A
policy record's declared effect is data about an external system's
configuration; recording it changes nothing outside the register.
The three stub entries ship as labeled reference implementations
(records carry `reference_stub: True`, status vocabulary is only
`recorded`, nothing executes). No extension record, view, or summary
computes a score: severities, verdicts, confidences, and counts from
external engines are recorded as the source's own data, and every
rollup is **counts and buckets only** — the founding build's
deterministic finding/risk scoring (its published severity x
criticality and likelihood x impact tables in `cyber.store`) remains
the only scoring in the package and is not re-implemented or
extended here.

## What landed

- **New module:** `src/cyber/extensions.py` — `ExtensionStore`, an
  in-memory records substrate for the Extended families, plus the
  `count_by` counting seam every extension rollup uses. All
  pre-existing core modules stay **byte-identical** (SHA-256 verified
  against the pre-build hashes; `store.py` still
  `1e58d852…`); the High uplifts (hash-chained audit, fail-closed
  writes, audit query/reduction, auditor role, logon lockout) are
  untouched and keep their shipped tests. The extension store writes
  to the same hash-chained `AuditLog` with the same fail-closed
  rollback on `AuditWriteError` (no object created, no id consumed),
  enforces RBAC through the core `access` module (registrations and
  definitions: `manage_assets`; engine-output ingestion: `ingest`;
  workflow decisions: `triage`; views/summaries: `read`; the auditor
  role therefore holds no permission on this surface, pinned by
  test), audit-records denied attempts on this surface
  (`extension_denied`), and derives every count/total/latest value
  at read time — derived keys are absent from stored records, pinned
  by tests. References are opaque tokens only: IPv4 literals, dotted
  hostnames, and URLs are rejected at the boundary, so no field can
  hold a real system's address, a credential, or PII.
- **Tests:** `tests/test_gaps_batch.py`, 39 tests. Full suite:
  **247 before → 286 after, OK.**
- **Fresh mutation-verified negative control:** the `count_by`
  counting seam in `extensions.py` was mutated to a
  classification-blind form (every value counted under the first
  choice, mirroring the core's severity-blind scoring mutant).
  Full suite: **286 ran, exactly 6 failed**, all in
  `test_gaps_batch.py`. Restored with SHA-256 verification
  (`66a7e6e6…`, identical to the pre-mutation hash) and re-run
  green. Full record in `tests/README.md`.

## Per-entry dispositions

| # | GAPS.md entry | Disposition | Built (module `cyber.extensions`, class `ExtensionStore`) |
|---|---|---|---|
| 1 | Endpoint management agents | build-extension (records form) | `register_endpoint_agent`, `record_agent_checkin`, `endpoint_agent_view` (check-in count and latest posture derived at read, never stored). Registry of agents the organization runs; nothing enrolls, patches, or manages an endpoint |
| 2 | DLP engines | build-extension (records form) | `create_dlp_policy` (declared action vocabulary is `monitor` / `alert` only — no effect an engine would take is representable, pinned by test), `record_dlp_event`, `dlp_summary` (counts by classification) |
| 3 | AI/ML detection models | **stub-engine** | `register_detection_model`, `record_model_output`. Labeled reference implementation: every record carries `reference_stub: True`, status is only `recorded`, output labels are the model's own recorded data with no confidence and no computed score (pinned) |
| 4 | Network enforcement planes | build-extension (records form) | `register_enforcement_point`, `create_enforcement_rule` (a record of declared configuration with `status: recorded`; nothing is applied — no traffic is allowed, denied, or inspected), `enforcement_point_view` (rule count derived) |
| 5 | Backup & recovery products | **stub-engine** | `register_backup_job`, `record_backup_run`, `record_restore_test`. Labeled reference implementation: every record carries `reference_stub: True`; runs and restore tests are records of outcomes reported from elsewhere — no data is copied, snapshotted, or restored |
| 6 | SOAR / workflow automation | **stub-engine** | `create_playbook`, `record_playbook_run`. Labeled reference implementation: every record carries `reference_stub: True`; the registry never executes a playbook — steps are stored as the definition's own text and no step is run or dispatched |
| 7 | Threat-intelligence feeds | build-extension (records form) | `register_intel_feed`, `add_indicator` (the feed's own opaque token and confidence label, recorded as source data, never resolved, fetched, or scored), `intel_summary` (counts by kind) |
| 8 | EDR agents | build-extension (records form) | `register_edr_agent`, `record_edr_detection` (the agent's own verdict/severity recorded; a detection record is never scored — no `score`/`band` key, pinned — scoring begins only if a human promotes it through core finding ingestion) |
| 9 | Cloud / SaaS posture engines | build-extension (records form) | `register_posture_scope`, `record_posture_check` (`control_id` must name a core-catalog control, so results trace to the core's control families), `posture_engine_summary` (counts by result only) |
| 10 | Phishing simulation / training content | build-extension (records form) | `create_campaign` (status only `recorded`; no message is composed or sent), `record_campaign_outcome`, `campaign_view` (outcome counts derived) |
| 11 | Fraud / identity-proofing products | build-extension (records form) | `create_proofing_case`, `record_proofing_outcome` (separation of duties: the decider is never the case creator), `proofing_case_view` (current outcome derived from the last outcome record, never stored). Records of proofing handled elsewhere — per PLATFORM-LAYER.md this substrate is not an identity provider and performs no proofing |
| 12 | AppSec engines | build-extension (records form) | `register_app`, `record_appsec_scan` (the engine's own reported count recorded as data; no code is scanned and no finding detail enters here — findings belong to core ingestion), `appsec_summary` (counts by kind, reported total) |
| 13 | Log pipelines | build-extension (records form) | `register_log_pipeline`, `record_log_batch`, `log_pipeline_view` (batch count and records total derived). Batch records hold counts and a window label only: no function on this surface can accept log content (pinned by a signature test over every `ExtensionStore` method) |
| 14 | CUI enclaves / VDI | build-extension (records form) | `register_enclave`, `record_enclave_session` (opaque user ref, minutes only), `enclave_view` (session count and total minutes derived). No desktop, session, or enclave is provisioned |
| 15 | Vulnerability scanners (ingestion and tracking is core) | build-extension (records form) | `register_scanner`, `record_scan_run`, `scanner_view` (run count and reported total derived). The extension is the scanner/run registry; finding ingestion and tracking themselves remain core (`CyberStore.ingest_finding`) and are not duplicated |
| 16 | Plus the substrate-adjacent families named in the spec's long tail (2) | build-extension (enumeration) | See the long-tail enumeration below: every Extended family in this group's UNION-SPEC is accounted for there, family by family, including the ones that are core, platform, or re-scoped rather than extension |

## Long-tail enumeration (entry 16)

The UNION-SPEC coverage statement names 16 Extended functions; the
function ranking adds the surrounding taxonomy families. Each is
accounted for exactly once:

**Covered by this unit (extension surface, rows above):**
`endpoint_management` (entry 1), `insider_dlp` (2), `ai_ml` (3,
stub), `network_security` (4), `data_protection` — backup/recovery
(5, stub), `automation` — SOAR/workflow (6, stub), `threat_intel`
(7), `endpoint_detection` — EDR (8), `cloud_saas_security` (9),
`phishing_awareness` — simulation/training content (10),
`fraud_identity` (11), `app_security` (12), `log_telemetry` (13),
`secure_enclave` — CUI enclaves/VDI (14), `vuln_management`'s
scanner remainder (15; ingestion/tracking was already core).

**Not extension, by the spec's own dispositions (not absorbed,
not re-opened):**
- `identity_access` — the "Identity products" entry, already
  `re-scoped` under PLATFORM-LAYER.md; not part of this unit.
- Core families (already implemented in the shipped build, not
  gaps): `reporting_dashboards`, `compliance_grc` (substrate),
  `audit_logging`, `access_control_feature`, `api_integration`,
  `asset_inventory`, `detection_response` (ingestion/triage
  substrate), `risk_scoring` (the deterministic tables — untouched,
  and the addition forks' posture/scoring engines gained no
  claimants per ADDENDUM.md, so no new computed score enters).
- `encryption_feature` — platform note (TLS when configured;
  SC-13 is a platform gap closed in writing by PLATFORM-LAYER.md).

**Explicitly NOT covered by this unit:** the two Extended functions
registered under the separate GAPS.md section "Remainder Addition —
Cybersecurity L3-adjacent (+2 forks)" — the **firewall management &
orchestration plane** (Cisco) and the **inline email security
platform** (Cisco). They belong to that section's own batch unit,
not this one; they are named here so the catch-all entry is not
read as silently absorbing them. Within this group's own spec long
tail, nothing else remains uncovered: every family named in the
UNION-SPEC ranking and coverage statement appears in one of the
three lists above.

## Re-judgments

None. All 16 drafted dispositions were confirmed on a close reading
of the union spec (DECISION.md qualification 1 was considered per
entry). The records-form scoping of the engine/agent entries is not
a re-judgment: it is the founding build's own scoping, stated in the
UNION-SPEC ("per-claimant engines do not become shared substrate at
either tier"), in the group README's honesty section, and in this
unit's brief. Two scope boundaries were recorded rather than
re-judged, because they follow from that discipline: DLP declared
actions are limited to `monitor` / `alert` (an enforceable effect is
not representable as a record here), and EDR detection records are
never scored by the extension (scoring is a core act, on core
findings, under the published table only).

## Unresolved

Nothing in this unit. The platform-layer baseline gaps at High
(IA-2(1)/(2)/IA-5, SC-13, SC-28, AU-11, AC-11/AC-12) were already
closed in writing by `../../PLATFORM-LAYER.md` and are not part of
this unit; the two Remainder Addition section entries named in the
long-tail enumeration belong to that section's own unit.
