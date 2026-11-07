# Final GAPS batch — Untiered Set 8, Education & Training

Unit: the 16 OPEN entries in GAPS.md under "Untiered Set 8 —
Education & Training (6 forks, tier null)". Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 11
build-extension, 5 stub-engine — as triaged in
`../../gaps-batch/inventory.json`, with ONE re-judgment of form
(the scoring entry, below) that does not change its closure token.

All extension code is in one new module, `src/learn/extensions.py`
(`LearnExtensions`, wrapping the core `LearnStore`); every existing
core module is byte-identical to its shipped state (SHA-256
verified against the set's README accounting — `store.py` still
`f9c8ea10…`). Full suite: 74 tests before, **128 tests after, OK**,
including the fresh mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline:** this set is untiered and the extension keeps
it so — nothing built here asserts a baseline, a tier, or a CMMC
equivalence, and a recursive key scan in the tests pins that no
tier/baseline-shaped key appears anywhere on the extension surface.

## Re-judgment (1, of form — DECISION.md qualification 1)

**"Deterministic scoring & proficiency-rating engines"** was
triaged build-extension. On a close reading of the set's
UNION-SPEC.md, a scoring *engine* — anything that computes a score
or grade — cannot be built in this substrate at all: the founding
category doctrine, stated in the union spec and pinned by the
core's tests, is that deterministic scoring/grading was claimed by
no fork (0/6 here, 0/8 in the founding group), assessments are
administration records only, and no score or grade field exists
anywhere in the build. Building a computed score would break the
founding invariant, so the entry is built in the only honest
in-substrate form (option (a) of the coordinator brief):

- **scoring-RULE records** — a rule's text held as data
  (`method: recorded_rules_only`, `applied_here: False`); rules are
  never applied to any record by this substrate;
- **reported-outcome records** — an outcome, including a
  proficiency rating in Dossier's sense, recorded **verbatim** as
  reported by an external assessor against an existing core
  assessment record. The union spec itself records Dossier's
  "proficiency ratings" as "a fork's recorded data"; this surface
  records such data and computes nothing from it. The core
  assessment record is untouched (pinned by test).

The disposition token is unchanged (`built`): records plus the
substrate's derivations are what build-extension means in this
batch, and the entry's records form is built and tested. What was
re-judged is the *engine* reading of the entry, and the grounds are
recorded here rather than silently shipping a score.

## Scope notes (recorded, not re-judgments)

- **AI assistants & guidance bots** (triaged build-extension) is
  carried as a labeled reference in substance, per the batch brief:
  an assistant profile record plus `guidance_lookup`, a
  deterministic exact-topic-match derivation over the registered
  guidance-flow records, method-labeled
  `deterministic_record_lookup` and carrying `reference_stub: True`
  on its result. No learned model, no generated text — the records
  themselves are returned verbatim.
- **Hosting / multi-tenancy platform layer** follows its drafted
  stub-engine disposition: deployment-posture records plus a
  derived summary stating the build's own posture
  (single-tenant reference), consistent with PLATFORM-LAYER.md
  decision 6 — a fork's hosting substrate does not transfer, and
  the record does not pretend to host anything.

| Entry (GAPS.md text) | Disposition | Built (module: `learn/extensions.py`) |
|---|---|---|
| Phishing simulation & security-awareness engines | built | `create_phishing_campaign` (`psc-`, target learner list, opaque `template_ref`, `executed_here: False` — this substrate sends nothing), `record_phishing_outcome` (`pso-`, outcome label stored verbatim as reported; learner must be a campaign target when targets are recorded), `get_phishing_campaign` / `list_phishing_campaigns` (outcome counts and learners-with-outcomes derived at read), `list_phishing_outcomes` (learner-scoped) |
| Training content delivery & LMS engines | built | `create_delivery_session` (`dls-`, optional core session binding validated against the course), `get_delivery_session` / `list_delivery_sessions` / `delivery_status` — the stored record carries **no status key**; status (`not_started` / `enrolled` / `in_progress` / `completed`) is derived at read from core progress/enrollment records via `_derive_delivery_status`, labeled `derived_from_core_progress_records`. Delivery records only; no content is served |
| Competency management & assessment-cycle engines | reference (stub-engine) | `create_competency_definition` (`cpd-`, per-role definitions with level labels as data), `create_assessment_cycle` (`cyc-`, period label, positive-int reassessment interval), `record_assessor_signoff` (`sgn-`, assessor's reported outcome stored verbatim) — every record carries **`reference_stub: True`** and state `recorded_reference_only` |
| Notification & reminder engine (a founding gap that gains a claimant in this set) | built | `create_notification_rule` (`ntr-`, triggers: derived-overdue assignments, assignments due within a recorded window, upcoming assessment sessions), `evaluate_notifications` — one deterministic pass over the core records at an explicit `as_of`, producing receipts (`nrc-`) deduplicated on (rule, reference, learner) so re-evaluation is idempotent; every receipt carries **`reference_transport: True`** and state `recorded_reference_only` — nothing is sent; `list_notification_receipts` (learner-scoped) |
| Medical education management engines | built | `record_clinical_log` (`clg-`, kinds clinical_hours / procedure / patient_encounter; minutes a non-negative int, booleans/floats rejected), `list_clinical_logs`, `clinical_summary` — entry counts by kind and total minutes derived at read (`method: deterministic_counts`). Logs are records; no clinical system is touched |
| Simulation-center operations engines | built | `create_sim_resource` (`smr-`, opaque `resource_ref` unique; kinds room / equipment / scenario), `record_sim_booking` (`smb-`, datetimes validated; an overlapping booking for the same resource is rejected whole and consumes no id), `sim_resource_schedule` — bookings derived in time order with a derived count. Coordination records only; nothing is captured or replayed |
| Digital adoption & in-app guidance engines | built | `create_guidance_flow` (`gdf-`, steps stored verbatim as data, topic label), `record_guidance_event` (`gde-`, event label verbatim as reported, step index bounds-checked against the flow's steps), `get_guidance_flow` / `list_guidance_flows` (event counts derived at read), `list_guidance_events` (scoped on `user_ref`) |
| AI assistants & guidance bots | built (labeled reference in substance — see scope note) | `create_assistant_profile` (`asp-`, **`reference_stub: True`**), `guidance_lookup` — deterministic exact-topic match over the registered guidance flows, steps returned verbatim, result labeled `method: deterministic_record_lookup` + `reference_stub: True`. A lookup creates no record and generates no text |
| Directory integration & provisioning sync | reference (stub-engine) | `create_directory_sync_record` (`dsy-`, added/changed/archived counts as reported, all non-negative ints), `list_directory_sync_records` — every record carries **`reference_stub: True`**; creating one changes **no** core record (pinned by test against the core report) |
| Career development & clinical ladder engines | built | `create_ladder_program` (`ldr-`, levels as an ordered, duplicate-free label list), `record_evidence_submission` (`evs-`, level must be one of the ladder's; evidence is an opaque ref, never held), `record_progression_review` (`pgr-`, outcome `advanced` / `returned`; **separation of duties** — the reviewer may not be the actor who recorded the submission; one review per submission), `ladder_progress` — per-level submission counts and the current level derived at read by presence match (`method: deterministic_presence_match`), never stored |
| Credentialing & accreditation workflow engines | reference (stub-engine) | `create_accreditation_workflow` (`acw-`, standard label held verbatim as data), `record_workflow_evidence` (`awe-`, opaque evidence refs), `record_credentialing_application` (`cra-`, binds a workflow to an existing Core credential record held by the named learner; changes no core record) — every record carries **`reference_stub: True`**. Credential records stay Core; nothing is accredited or issued |
| Deterministic scoring & proficiency-rating engines | built, records form only (re-judged — see above) | `create_scoring_rule` (`scr-`, rule text held as data, `method: recorded_rules_only`, `applied_here: False` — never applied), `record_reported_outcome` (`rpo-`, outcome recorded **verbatim** as reported by an external assessor against an existing core assessment; the core assessment record is byte-identical before/after, pinned by test), `list_scoring_rules` / `list_reported_outcomes`. **No score or grade is computed or stored anywhere** |
| Recruiting/HCM suite | built | `create_requisition` (`rq-`, opaque `role_ref`), `create_candidate` (`cnd-`, opaque `candidate_ref` — applicants need not be learners), `create_application` (`apl-`, recorded stage starts `applied`; duplicate candidate+requisition rejected), `record_application_stage` (recorded transitions over the stage enum — data, not workflow execution), `create_onboarding_record` (`onb-`, requires recorded stage `hired`; may bind a core enrollment), `recruiting_pipeline` — counts by recorded stage derived at read (`method: deterministic_counts`) |
| Talent & marketplace matching (no claimant in this set) | built | `create_opportunity` (`opp-`, required courses must be Core registry entries), `match_opportunities_for_learner` / `match_learners_for_opportunity` — a deterministic presence match: an opportunity matches when the learner holds a **completed** core progress record for every required course; the view lists `missing_course_ids` as data and a `fully_matched` boolean (`method: deterministic_presence_match`). No ranking and no fit value is computed; the family stands at 0 claimants in this set and the derivation is claimed for no fork |
| Remote proctoring & identity proofing (no claimant in this set) | reference (stub-engine) | `create_proctoring_record` (`prc-`, binds an existing core assessment; learner copied from it), `record_proofing_outcome` (`prf-`, outcome stored verbatim as reported by the provider) — every record carries **`reference_stub: True`**; proofing records also carry `decision_made: False` and `identity_provider: False`, proctoring records `decision_made: False`. Per PLATFORM-LAYER.md decision 1 these records are not identity evidence and decide nothing; nothing is monitored here |
| Hosting / multi-tenancy platform layer | reference (stub-engine) | `create_deployment_record` (`dep-`, tenancy/region labels held verbatim as data, `multi_tenant_here: False`), `deployment_summary` — derived count plus the build's own posture stated plainly (`build_tenancy: single_tenant_reference`). Every record carries **`reference_stub: True`**; recording a posture hosts nothing |

Cross-cutting, per the set's doctrines: tier null throughout (no
baseline asserted, no tier key on any record — pinned by key scan);
the founding **no-score invariant** pinned over the whole extension
surface by a recursive key scan (no `score`-/`grade`-shaped key in
any returned value, core or extension); opaque `*_ref` strings and
the core's `learner_id` convention only, so no record shape can
hold a name, email, phone, or identifier; derived-never-stored for
every computed value (delivery status, campaign outcome counts,
clinical totals, ladder current level, matching, pipeline counts);
RBAC via the existing `learn.access` actions, enforced before any
state change or id allocation (failed operations consume no id);
learner scope mirrors the store's; every successful mutation is
recorded on the core audit log with an `ext_`-prefixed action, and
denied write attempts are recorded with a `:denied` suffix.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
