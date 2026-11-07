# Final GAPS batch — Group 4, Cybersecurity & Risk Management L2

Unit: the 17 OPEN entries of this group's section in the repo-root
GAPS.md. The section's 18th entry, "Detection engines and staffed
SOC services (13) — ingestion and triage of their output is core",
was already closed as `re-scoped` before this unit and is not
touched here.

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/cyber/extensions.py` (class `ExtensionStore`), plus
`tests/test_gaps_batch.py`. **No existing core module was changed**
(all eight founding `src/cyber/*.py` files verified byte-identical
by SHA-256 before and after; store.py remains
f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de).

Category discipline, applied to every entry: this build is the
shared defensive substrate only. Nothing in the extension scans,
detects, enforces, blocks, trains, monitors, hosts, or executes.
Engine/agent/plane entries are built in their **records form**:
registries of the thing, ingestion records for its output, and
tracking workflows around it. No new scoring is invented anywhere:
extension posture views are counts only (pinned by tests), and the
only scores in the package remain the founding build's published
severity × criticality and likelihood × impact formulas. Identity
entries are hooks and reported-outcome records only; no IdP is
built (PLATFORM-LAYER.md decision 1). All references are opaque
tokens; IP-shaped, URL, and hostname values are rejected at the
boundary, and no record shape can hold a credential or PII.

Access: the founding permission matrix is reused with no new
actions — registry creates `manage_assets`, ingestion-shaped
records `ingest`, lifecycle transitions `triage`, GRC records
`assess_controls`, campaign creates/assignments `manage_risks`,
reads `read`. Denied attempts are audited with a `:denied` suffix
before the denial propagates.

## Per-entry dispositions

### Build-extension (12) — records form in `cyber.extensions`

1. **Network enforcement planes (11)** — `register_enforcement_point`
   / `retire_enforcement_point` / `list_enforcement_points` /
   `enforcement_coverage`. A registry of enforcement points (kind:
   segmentation, firewall, waf, ztna, sse, browser_isolation) over
   opaque scope and policy references, with a derived, never-stored
   coverage view (counts by kind). Nothing is enforced.
2. **Threat-intelligence feeds (9)** — `register_intel_feed` /
   `list_intel_feeds` / `ingest_intel_item` /
   `transition_intel_item` / `list_intel_items`. Feed registry plus
   ingested intel items with a new → reviewed → retired lifecycle;
   an item's level is stored as *reported by the feed*, never
   computed.
3. **Full GRC automation suites (8) — control mapping is core** —
   `register_framework` / `list_frameworks` /
   `create_evidence_task` / `transition_evidence_task` /
   `list_evidence_tasks`. Beyond the core control map: framework
   records and an evidence-collection workflow whose tasks validate
   control ids against the founding 34-control catalog and enforce
   separation of duties (collector ≠ verifier; see the negative
   control).
4. **Identity products (8) — hooks only, no IdP** —
   `register_identity_hook` / `list_identity_hooks`. Integration
   hook records (sso, mfa, pam, iga, directory) that carry
   `hook_only: true` and `identity_provider: false` in their own
   shape.
5. **EDR/XDR agents (7)** — `register_edr_agent` /
   `record_agent_report` / `list_edr_agents`. Enrollment records
   plus health status records as reported by the external agent.
6. **Phishing simulation / training (7)** — `create_campaign` /
   `transition_campaign` / `list_campaigns` / `assign_training` /
   `complete_training` / `list_assignments` / `campaign_counts`.
   Campaign program records (carrying `messages_sent: false` —
   nothing is sent or simulated) with a planned → approved →
   completed/cancelled lifecycle, training assignments keyed by
   opaque learner references, and derived per-campaign counts.
7. **AppSec testing engines (6)** — `register_appsec_engine` /
   `list_appsec_engines` / `record_appsec_run` /
   `list_appsec_runs`. Engine registry (sast, dast, sca, pentest,
   api) plus run records carrying the finding count the engine
   reported and `executed_here: false`; the findings themselves
   belong in the core register.
8. **CSPM/CNAPP/SSPM posture engines (5)** —
   `register_posture_engine` / `list_posture_engines` /
   `record_posture_snapshot` / `list_snapshots` / `posture_counts`.
   Engine registry plus snapshots validated as counts only
   (non-negative integers; booleans, floats, strings, negatives, and
   empty maps rejected), with a derived per-engine aggregate that
   contains no score, rate, or grade key — pinned recursively by
   test.
9. **Vulnerability scanners (4) — ingestion and tracking is core** —
   `register_scanner` / `list_scanners` / `record_scan` /
   `list_scan_records`. Scanner registry plus scan-event tracking
   records (`executed_here: false`); scanner output itself remains
   core findings, exactly as the founding spec drew the line.
10. **CUI enclaves / VDI (3)** — `register_enclave` /
    `list_enclaves` / `start_enclave_session` /
    `end_enclave_session` / `list_sessions` /
    `active_session_count`. Enclave records (carrying
    `hosted_here: false`) and session tracking records keyed by
    opaque user references, with the active-session count derived
    at read.
11. **Identity proofing / fraud (2)** — `record_proofing_check` /
    `list_proofing_records`. Reported-outcome records only: method
    and outcome are stored exactly as an external service reported
    them, and the record carries `decision_made: false` — this
    build proof-checks no one, scores no one, and decides nothing.
12. **Endpoint management agents (2)** — `register_mgmt_agent` /
    `list_mgmt_agents` / `record_patch_status` /
    `list_patch_records`. Agent registry with a closed capability
    set (patching, configuration, automation) plus patch-status
    records as reported (`applied_here: false`).

### Stub-engine (5) — labeled reference implementations

13. **AI/ML detection models (17 siblings)** —
    `register_model_reference` / `list_model_references` /
    `record_model_output_reference` / `list_model_outputs`. Model
    and model-output records, both carrying `reference_stub: true`.
    No model is loaded, no inference runs, no score is produced;
    an output's label is stored as reported.
14. **SOAR / orchestration engines (14)** —
    `register_playbook_reference` / `list_playbook_references` /
    `record_playbook_run_reference` / `list_playbook_runs`.
    Playbook and reported-run records carrying `reference_stub:
    true`; run records additionally carry `executed: false`.
15. **Backup / recovery products (9)** —
    `register_backup_product_reference` /
    `list_backup_product_references` /
    `record_backup_job_reference` / `list_backup_jobs`. Product
    and reported-job records carrying `reference_stub: true` and
    `executed_here: false`. No backup is taken; nothing is
    restored.
16. **DLP / insider monitoring engines (7)** —
    `register_dlp_engine_reference` / `list_dlp_engine_references`
    / `record_dlp_alert_reference` / `list_dlp_alerts`. Engine and
    alert records carrying `reference_stub: true`; the alert level
    is stored as reported. No content is inspected and no one is
    monitored here.
17. **Log / telemetry pipelines (5)** —
    `register_pipeline_reference` / `list_pipeline_references` /
    `record_pipeline_receipt` / `list_pipeline_receipts`. Pipeline
    records carrying `reference_stub: true`, and transport
    receipts carrying both `reference_stub: true` and
    `reference_transport: true` (house precedent for pipeline
    receipts): a receipt attests a record of movement reported by
    an external pipeline, not movement through this build.

## Re-judgments

None. Every entry fit its drafted disposition on a close reading
of UNION-SPEC.md: the 12 build-extension entries all have an honest
records form consistent with how the founding spec already drew
their Core/Extended lines (its table marks findings ingestion,
control mapping, and scanner-output tracking as Core substrate for
several of these same families), and the 5 stub-engine entries are
exactly the families whose records form would still imply an
engine (inference, orchestration, backup execution, content
monitoring, event transport), so they ship labeled.

## Tests and negative control

- Suite: **204 before → 233 after, OK** (29 new tests in
  `tests/test_gaps_batch.py`, at least one per entry, plus
  cross-cutting RBAC/audit and counts-only pins).
- Fresh mutation-verified negative control: the
  separation-of-duties seam `_check_verifier_not_collector` in
  `src/cyber/extensions.py`. Mutating its equality condition to
  `False` (guard disabled) made the full suite fail with
  **exactly 1 failure** —
  `test_gaps_batch.TestGrcAutomation.test_separation_of_duties_guard`.
  The file was restored byte-identical (SHA-256
  0a2591d1bedc5c342df913c430767d0a8d9e2f07096e872a0b58c37338bac492)
  and the suite re-ran green. Recorded in tests/README.md.

## Unresolved

Nothing unresolved within this unit. The extension surface is a
store-level surface only, matching the batch pattern for sibling
units: no HTTP routes were added (the founding service.py is a core
module and stays byte-identical), so the extension is consumed
in-process, like the other groups' batch extensions.
