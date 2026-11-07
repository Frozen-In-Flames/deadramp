# Final GAPS batch — Untiered Set 3, Governance, Risk, and Compliance (GRC)

Unit: the 12 OPEN entries in GAPS.md under "Untiered Set 3 —
Governance, Risk, and Compliance (GRC) (15 forks, tier null)".
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07): 6 build-extension, 6 stub-engine — as triaged in
`../../gaps-batch/inventory.json`, with TWO re-judgments of form
(the scoring entry and the enclave entry, below) that do not
change their closure tokens.

All extension code is in one new module, `src/grc/extensions.py`
(`GrcExtensions`, wrapping the core `GrcStore`); every existing
core module is byte-identical to its shipped state (SHA-256
verified — `store.py` still `e2eac653…`). Full suite: 130 tests
before, **194 tests after, OK**, including the fresh
mutation-verified negative control recorded in `tests/README.md`
(the reviewer-not-filer guard: exactly 2 failures under mutation,
both in the negative-control class, file restored SHA-256
identical, suite green again).

**Tier discipline:** this set is untiered and the extension keeps
it so — nothing built here asserts a baseline, a tier, or any
equivalence, and a recursive key scan in the tests pins that no
tier-shaped or baseline-shaped key appears anywhere on the
extension surface. The founding **no-score invariant** is pinned
the same way over the whole surface: no score is computed,
stored, or echoed anywhere; the forks' own scores (Northwatch's
PAIN rating, Boundera's score history, TrustGuard's vendor
scoring) remain the forks' claims, recorded as data only.

## Re-judgments (2, of form — DECISION.md qualification 1)

**"Posture & risk scoring engines"** was triaged build-extension.
On a close reading of the set's UNION-SPEC.md, a scoring *engine*
— anything that computes a score — cannot be built in this
substrate at all: the category doctrine, stated in the union
spec's core-boundary decision and pinned by the core's tests, is
that posture reporting is counts only and no score is computed
anywhere in this build, even though forks in this set document
scores of their own. Building a computed score would break the
founding invariant, so the entry is built in the only honest
in-substrate form (following the Education & Training untiered
unit's adjudicated precedent for exactly this entry shape):

- **scoring-RULE records** — a rule's text held as data
  (`method: recorded_rules_only`, `applied_here: False`); rules
  are never applied to any record by this substrate;
- **reported-score records** — a score label, in the fork's own
  words (e.g. a PAIN-style band), recorded **verbatim** as
  reported by the fork's engine against an existing governed
  system. The union spec itself records those scores as "the
  forks' claims, recorded as such"; this surface records such
  data and computes nothing from it — the only aggregate is a
  count of records per verbatim label.

The disposition token is unchanged (`built`). What was re-judged
is the *engine* reading of the entry, and the grounds are recorded
here rather than silently shipping a score.

**"Hosted enclave & PaaS operations"** was triaged
build-extension. It is built in records form: enclave records
plus hosting-state records stored exactly as reported, with the
current reported state derived at read. Per PLATFORM-LAYER.md
decision 6, a fork's hosting substrate does not transfer and
hosting is a deployment property — so the records carry
`hosted_here: False` and state `recorded_reference_only`, and
nothing here operates a platform. (The GRC L2 sibling section
drafted the same entry as a stub for the same reason; this set's
drafted disposition is build-extension, and the records form
above is what "built" honestly means for it — the substance
shipped is a labeled records form either way, stated plainly
rather than papered over.) The disposition token is unchanged
(`built`).

## Scope notes (recorded, not re-judgments)

- **Automated evidence collection & validation** is built at the
  strength the substrate honestly supports. Collection is a *run
  record* (`reference_transport: True`, `collected_here: False`):
  no connector fetches anything, and evidence artifacts continue
  to be filed through the core registry. Validation is a *batch
  review record*: the outcome is recorded verbatim by an
  authorized reviewer under a filer ≠ reviewer separation-of-duties
  guard (the core's own separation, carried to this surface), it
  is never an automated verdict computed here, and it never
  modifies the core evidence record (`applied_to_core: False`) —
  the core's recorded validation status remains the core
  reviewer's field, so the batch layer cannot quietly rewrite
  core state.
- **Vulnerability scanning** lands its reported findings as
  ordinary core finding records (severity verbatim, core lifecycle
  and read-time derivation), which is the substrate's own finding
  surface; the report record itself is `executed_here: False` and
  no prioritization is computed from the reported severities.

| Entry (GAPS.md text) | Disposition | Built (module: `grc/extensions.py`) |
|---|---|---|
| Automated evidence collection & validation engine | built | `create_collection_run` (`col-`, binds an existing governed system + known controls; `reference_transport: True`, `collected_here: False`, changes no core record), `get/list_collection_runs`, `record_evidence_review` (`evr-`, outcome stored verbatim; **separation of duties**: the artifact's core filer may not record its batch review — seam `_check_reviewer_not_filer`, this unit's fresh negative control; `applied_to_core: False` — the core evidence record is byte-identical before/after, pinned by test), `list_evidence_reviews`, `evidence_review_summary` (counts by recorded status, `method: deterministic_counts`) |
| Continuous-monitoring feeds & scanner integrations | reference (stub-engine) | `create_feed` (`monitoring_feed` / `scanner_integration` kinds), `record_feed_receipt` (`frc-`, item count as reported, booleans/floats/negatives rejected), `get/list_feeds`, `list_feed_receipts` — every record carries **`reference_stub: True`**; feeds and receipts also **`reference_transport: True`**, `connected_here` / `ingested_here: False`; receipt counts and item totals derived at read; creating them changes **no** core record (pinned by deep-equal posture test) |
| Vulnerability scanning engine | built | `create_scanner` (caller-supplied opaque ref, duplicate rejected), `record_scan_report` (`scr-`, every reported finding validated fully before anything is recorded — a bad item records nothing and consumes no id — then landed as a **core finding record** via the core store: severity verbatim, core lifecycle, overdue derived at read by the core; `executed_here: False`, no prioritization computed), `get/list_scan_reports`, `scan_report_summary` (counts only) |
| Automated KSI validation | reference (stub-engine) | `create_ksi_rule` (binds an existing core indicator; rule text held verbatim as data), `record_ksi_evaluation` (`kev-`, outcome stored verbatim as reported by an external validator), `get/list_ksi_rules`, `list_ksi_evaluations`, `ksi_evaluation_summary` — every record carries **`reference_stub: True`** and `evaluated_here: False`; no rule is ever evaluated here; evaluations create no core indicator result (pinned by test) |
| Posture & risk scoring engines (the claiming forks' own engines — this category computes no scores anywhere, and the set's posture remains counts only) | built, records form only (re-judged — see above) | `create_scoring_rule` (`srl-`, rule text held as data, `method: recorded_rules_only`, `applied_here: False` — never applied; rules unaffected by recorded scores, pinned by test), `record_reported_score` (`rps-`, label stored **verbatim** in the fork's own words, `computed_here: False`), `list_scoring_rules` / `list_reported_scores`, `reported_score_summary` — counts per verbatim label only (`method: deterministic_counts`). **No score is computed or stored anywhere** |
| Hosted enclave & PaaS operations | built, records form (re-judged — see above) | `create_enclave` (caller-supplied opaque ref; member systems validated against the core registry; `hosted_here: False`), `record_hosting_state` (`hst-`, state stored verbatim as reported), `get/list_enclaves` — the view derives `current_reported_state` at read from the state records (the create return carries no such key), `enclave_summary` (counts by reported state). Nothing is hosted or operated here |
| FedRAMP package generation | built | `create_package` (`pkg-`, deterministic manifest assembly over records the substrate already holds for one system under one framework: control list, evidence with checksums + recorded validation statuses, findings with read-time `derived_status` at the package's `as_of`, assessments, authorizations, and this extension's policy records with derived current states; counts derived from the assembly; `method: deterministic_manifest_assembly`, `narrative_generated: False`, `documents_emitted: False`), `get/list_packages` — the manifest is a snapshot: records created afterwards do not rewrite it (pinned by test); no narrative text is generated and no document (SSP / POA&M / OSCAL) is emitted |
| Policy lifecycle engine | built | `create_policy` (`pol-`, stores its **initial** state only), `transition_policy` (guarded by `POLICY_TRANSITIONS`: draft → in_review → approved → published / attested → superseded / retired, with reopen and retire paths; illegal moves denied with history unchanged), `record_attestation` (`att-`, attestor's outcome stored verbatim, `decision_made: False` — an attestation record moves nothing), `get/list_policies`, `policy_summary` — **current state is derived at read** from the recorded transition history and **never stored** (the stored record carries no `current_state` key, pinned by test against the internal record); **attestation status is derived at read**: `attested` in the attested state, `expired` for an approved/published policy past its recorded expiry date at `as_of`, otherwise `unattested` |
| Agentic workflow execution | reference (stub-engine) | `create_workflow_run` (caller-supplied ref, optional governed system), `record_workflow_step` (`wfs-`, step status stored verbatim as reported), `get/list_workflow_runs` (step count derived at read), `list_workflow_steps` — every record carries **`reference_stub: True`**, runs `executed: False`, steps `executed_here: False`; creating them changes **no** core record (pinned by deep-equal posture test) |
| AI control-narrative & assessment-response generation | reference (stub-engine) | `create_narrative_request` (`nar-`, kinds `control_narrative` / `assessment_response`, binds an existing system + known controls), `record_narrative_outcome` (`nao-`, outcome label stored verbatim as reported), `get/list_narrative_requests` — every request carries **`reference_stub: True`**, `generated_here: False`, and **`narrative_text: None`**: no text is generated anywhere on this surface (pinned by test) |
| Data-integration connector engine | reference (stub-engine) | `create_connector` (caller-supplied ref, target held as a label), `record_connector_run` (`cnr-`, record count as reported; booleans/floats/negatives rejected), `get/list_connectors`, `list_connector_runs` — every record carries **`reference_stub: True`**; connectors and receipts also **`reference_transport: True`**, `connected_here` / `moved_here: False`; run counts and reported totals derived at read; the build's own REST API stays Core 8 and is not a connector |
| Fork excess: healthcare quality suite; AI/ML governance evaluation engine; digital-twin OSCAL analysis engine; no-code BPM platform | reference (stub-engine) | `create_excess_profile` (`exc-`, one profile per kind — `healthcare_quality`, `ai_ml_governance_evaluation`, `digital_twin_oscal_analysis`, `no_code_bpm`; unknown kinds rejected), `record_excess_outcome` (`exo-`, label stored verbatim, `computed_here: False`), `get/list_excess_profiles`, `excess_summary` — every record carries **`reference_stub: True`** and `executed_here: False`. These are product surfaces outside the category's records substrate, recorded as existing in the forks' products; nothing of them runs or is computed here (no OSCAL is ingested, no twin is analyzed, no process is modeled, no healthcare workflow executes) |

Cross-cutting, per the set's doctrines: tier null throughout (no
baseline asserted, no tier key on any record — pinned by key
scan); the founding **no-score invariant** pinned over the whole
extension surface by a recursive key scan (no score-shaped key in
any returned value, extension or core posture); opaque refs and
the core's governed-system references only, so no record shape
can hold a name-as-key, email, phone, or identifier; statuses and
outcomes produced by the forks' engines are **recorded verbatim**;
derived-never-stored for every computed value (current reported
hosting state, policy current state, policy attestation status,
feed/connector totals, all summaries — counts via
`method: deterministic_counts`); RBAC via the existing
`grc.access` actions, enforced before any state change or id
allocation (failed operations consume no id); every successful
mutation is recorded on the core audit log with an `ext_`-prefixed
action, and denied write attempts are recorded with a `:denied`
suffix.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
