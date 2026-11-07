# Final GAPS batch — Group 16, Cybersecurity & Risk Management L1

Unit: the 5 OPEN entries of the GAPS.md section "Group 16 —
Cybersecurity & Risk Management L1 (5 forks)" (inventory idx
169–173). All 5 are accounted for below.

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/cyber/extensions.py` (class `ExtensionStore`), plus
`tests/test_gaps_batch.py`. **No existing core module was changed**
(all eight founding `src/cyber/*.py` files verified byte-identical
by SHA-256 before and after; store.py remains
f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de).

Category discipline, applied to every entry: this build is the
shared defensive substrate only. Nothing in the extension scans,
detects, enforces, blocks, trains, simulates, or executes.
Engine entries are built in their **records form** or shipped as
**labeled reference implementations**. No new scoring is invented
anywhere: extension views are counts only (pinned by tests), and
the only scores in the package remain the founding build's
published severity × criticality and likelihood × impact formulas.
Identity entries are hooks only; no IdP is built
(PLATFORM-LAYER.md decision 1). All references are opaque tokens;
IP-shaped, URL, and hostname values are rejected at the boundary,
and no record shape can hold a credential or PII. Tier discipline
is this group's own: there is no auditor role and no hash-chained
audit at L1 — the extension writes to the founding build's plain
append-only audit log and reuses its permission matrix unchanged
(registry creates `manage_assets`, ingestion-shaped records
`ingest`, lifecycle transitions `triage`, GRC records
`assess_controls`, campaign creates/assignments `manage_risks`,
reads `read`). Denied attempts are audited with a `:denied` suffix
before the denial propagates.

## Per-entry dispositions

### Stub-engine (2) — labeled reference implementations

1. **idx 169 — "AI/ML-powered analytics & anomaly detection models (2 of 5)"** —
   `register_model_reference` / `list_model_references` /
   `record_model_output_reference` / `list_model_outputs`. Model
   and model-output records, both carrying `reference_stub: true`.
   No model is loaded, no inference runs, no score is produced; an
   output's label is stored exactly as the external model reported
   it — a detector's verdict is its own inference, recorded here,
   never reproduced or computed.
2. **idx 171 — "Automation & orchestration engines (SOAR / workflow) (1)"** —
   `register_playbook_reference` / `list_playbook_references` /
   `record_playbook_run_reference` / `list_playbook_runs`.
   Playbook definitions held as data and reported-run records,
   carrying `reference_stub: true`; run records additionally carry
   `executed: false`. The registry never executes a playbook.

### Build-extension (3) — records form in `cyber.extensions`

3. **idx 170 — "Full GRC automation suites beyond the substrate (3 of 5 claim the family; control mapping & assessment records are Core)"** —
   **RE-JUDGED from the drafted stub-engine triage to
   build-extension** (grounds under Re-judgments below).
   `register_framework` / `list_frameworks` /
   `create_evidence_task` / `transition_evidence_task` /
   `list_evidence_tasks`. Beyond the core control map: framework
   records and an evidence-collection workflow whose tasks
   validate control ids against the founding 34-control catalog
   and enforce separation of duties (collector ≠ verifier; see the
   negative control). What remains unbuilt, stated plainly: the
   suite's automation itself — evidence-collection connectors
   that pull from external systems and auditor-portal automation —
   is not built; this is the framework/evidence tracking substrate
   "beyond the substrate" that a records build can honestly hold.
4. **idx 172 — "Identity products / IdP (1; the core ships access-control hooks only)"** —
   `register_identity_hook` / `list_identity_hooks`. Integration
   hook records (sso, mfa, pam, iga, directory) that carry
   `hook_only: true` and `identity_provider: false` in their own
   shape, per PLATFORM-LAYER.md decision 1: identity stays with
   the embedding organization; this build authenticates no one.
5. **idx 173 — "Phishing-defense enforcement & simulation / training content (1; DMARC enforcement)"** —
   two records surfaces. (a) Simulation/training:
   `create_campaign` / `transition_campaign` / `list_campaigns` /
   `assign_training` / `complete_training` / `list_assignments` /
   `campaign_counts`. Campaign program records (carrying
   `messages_sent: false` — nothing is sent or simulated) with a
   planned → approved → completed/cancelled lifecycle, training
   assignments keyed by opaque learner references, and derived
   per-campaign counts. (b) DMARC enforcement:
   `register_dmarc_policy` / `list_dmarc_policies` /
   `record_dmarc_report` / `list_dmarc_reports` / `dmarc_counts`.
   Policy records keyed by an opaque domain reference (a real
   domain name is hostname-shaped and is rejected at the boundary,
   pinned by test) holding DMARC's own published policy vocabulary
   (none / quarantine / reject) as declared data, plus aggregate
   report records whose message counts are stored exactly as the
   external platform reported them; both record kinds carry
   `enforced_here: false`, and the derived counts view sums only
   reported data. No message is inspected, aligned, or rejected
   here — enforcement stays with the platform that runs it (this
   group's one claim is Valimail's DMARC enforcement, recorded in
   UNION-SPEC.md as protocol wording plus the genuine
   impersonation-prevention sentence; the records form covers both
   halves without claiming the enforcement act).

## Re-judgments

**One: idx 170, stub-engine → build-extension.** Grounds, per
DECISION.md qualification 1:

- The draft triage is pattern-based; it matched "automation
  suites" to the engine class generically. On a close reading of
  the owning group's spec, the family has an honest records form:
  UNION-SPEC.md's own disposition for this family is "Core
  substrate (control mapping & assessment, the register every GRC
  suite presupposes; full GRC automation suites are Extended)" —
  the part beyond the substrate that a records substrate can hold
  is the framework register and the evidence-collection workflow,
  and that is exactly what was built.
- The Moderate sibling (Group 4, cybersecurity-l2) shipped the
  identical family as build-extension in this same records form,
  against core code that is **byte-identical** to this group's
  (all 8 `src/cyber/*.py` files share SHA-256 hashes across the
  two groups, recorded in tests/README.md). Closing the same
  family as a stub here and a build there would make the two
  tiers' records disagree about the same substrate — the union
  spec's stated reason for applying one taxonomy unchanged across
  the Cybersecurity groups is that their records stay comparable.
- The re-judgment builds no engine: no connector pulls evidence
  from anywhere, and BATCH.md and the module docstring state what
  remains unbuilt. It therefore follows the batch's standing
  preference — an honest built records form where one exists,
  over a stub label for a surface that is in fact records.

No other entry was re-judged: idx 169 and 171 are engines whose
records form would still imply inference/execution, so they ship
labeled as drafted; idx 172 and 173 fit their drafted
build-extension disposition in the forms above.

## Tests and negative control

- Suite: **205 before → 225 after, OK** (20 new tests in
  `tests/test_gaps_batch.py`, at least one per entry surface, plus
  cross-cutting RBAC/audit and counts-only pins).
- Fresh mutation-verified negative control: the
  separation-of-duties seam `_check_verifier_not_collector` in
  `src/cyber/extensions.py` (new code in this tree). Mutating its
  equality condition to `False` (guard disabled) made the full
  suite fail with **exactly 1 failure** —
  `test_gaps_batch.TestGrcAutomation.test_separation_of_duties_guard`.
  The file was restored byte-identical (SHA-256
  98c0362e592187021d1b76719ec4cb7cb1151a71668439185c7a8f76fada8562)
  and the suite re-ran green. Recorded in tests/README.md.

## Unresolved

Nothing unresolved within this unit. The extension surface is a
store-level surface only, matching the batch pattern for sibling
units: no HTTP routes were added (the founding service.py is a
core module and stays byte-identical), so the extension is
consumed in-process, like the other groups' batch extensions.
Parent ship arithmetic: 5 entries closed — idx 169 `reference`,
idx 170 `built` (token override for the re-judgment), idx 171
`reference`, idx 172 `built`, idx 173 `built` (3 built,
2 reference).
