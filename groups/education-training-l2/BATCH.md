# Final GAPS batch — Group 13, Education & Training L2

Unit: the 11 OPEN entries in GAPS.md under "Group 13 — Education &
Training L2 (8 forks)". Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 6
build-extension, 5 stub-engine — as triaged in
`../../gaps-batch/inventory.json`, with NO re-judgments: every
build entry is honestly carried in records form under this group's
founding no-score invariant, and every stub entry ships as a labeled
reference implementation, so no disposition needed correcting on
close reading of the group's UNION-SPEC.md.

All extension code is in one new module, `src/learn/extensions.py`
(`LearnExtensions`, wrapping the core `LearnStore`); every existing
core module is byte-identical to its shipped state (verified: `git
diff HEAD -- groups/education-training-l2/src` is empty apart from
the new untracked module). Full suite: 79 tests before, **116 tests
after, OK**, including the fresh mutation-verified negative control
recorded in `tests/README.md`.

**Founding-tier discipline:** this group is the category's founding
tier — its union spec established the records substrate the sibling
tiers reuse — and the forms here follow this group's spec where the
tiers differ. Compliance status stays DERIVED at read in the core
and is never stored by the extension either; assessments stay
administration records only — **no score or grade field exists
anywhere on the extension surface**, pinned by a recursive key scan
in the tests; learner records are opaque refs under the core's
learner-scope access rules. The forms mirror the adjudicated
records forms of the untiered set's and the L1 group's batch units
(`groups/education-training-untiered/BATCH.md`,
`groups/education-training-l1/BATCH.md`) for the same families.

| Entry (GAPS.md text) | Disposition | Built (module: `learn/extensions.py`) |
|---|---|---|
| Talent, skills & marketplace matching (incl. career exploration / coaching and AI career assistants) (3 of 8) | built | `create_opportunity` (`opp-`, required courses must be Core registry entries), `match_opportunities_for_learner` / `match_learners_for_opportunity` — a deterministic presence match: an opportunity matches when the learner holds a **completed** core progress record for every required course; the view lists `completed_course_ids` and `missing_course_ids` as the per-match evidence plus a `fully_matched` boolean (`method: deterministic_presence_match`), via the seam `_learner_completed_all`. No ranking and no fit value is computed. Career side: `create_career_profile` (`crp-`, interests as data), `create_guidance_flow` (`gdf-`, steps verbatim), `create_assistant_profile` (`asp-`, labeled reference record, `reference_stub: True`), `guidance_lookup` — deterministic exact-topic match over the registered guidance flows, steps returned verbatim, `method: deterministic_record_lookup` + `reference_stub: True`; a lookup creates no record and generates no text |
| Recruiting, HCM / HRIS & workforce management suites (incl. performance and policy management) | built | `create_requisition` (`rq-`, opaque `role_ref`), `create_candidate` (`cnd-`, opaque `candidate_ref` — applicants need not be learners), `create_application` (`apl-`, recorded stage starts `applied`; duplicate candidate+requisition rejected), `record_application_stage` (recorded transitions over the stage enum — data, not workflow execution), `create_onboarding_record` (`onb-`, requires recorded stage `hired`; may bind a core enrollment), `recruiting_pipeline` — counts by recorded stage derived at read (`method: deterministic_counts`), `record_performance_record` (`pfr-`, outcome stored verbatim as reported, `evaluated_here: False`), `create_policy_record` (`pol-`, policy text held verbatim as data, `enforced_here: False` — never enforced here) |
| Course content authoring & delivery, media streaming | reference (stub-engine) | `create_content_package` (`cnt-`, authoring/delivery declaration as data, `authored_here: False`, `streamed_here: False`), `record_delivery_receipt` (`dlr-`, reported delivery state stored verbatim, `delivered_here: False`, `reference_transport: True`) — every record carries **`reference_stub: True`** and state `recorded_reference_only`; nothing is authored, delivered, or streamed here. Authoring and streaming are both named absences in this group's union spec (0/8; the only first-pass hits were substrings inside "Capital" and "streamline") |
| Simulation engines (capture, debriefing & playback); the simulation records are Core, the engine is not | built | `create_simulation_session` (`sim-`, binds a Core course and recorded member learners; the stored record carries **no state key**), `record_simulation_event` (`sme-`, recorded state label over the enum scheduled / captured / debriefed / played_back, stored as the operator's record, `captured_here: False`, `played_back_here: False`), `get_simulation_session` / `list_simulation_sessions` — `current_state` derived at read from the latest recorded event (`state_method: latest_recorded_event`) with a derived `event_count`. Coordination records only; nothing is captured, rendered, or played back |
| Remote proctoring & identity proofing (0 of 8 claims; explicitly not inferred from "secure assessment delivery") | reference (stub-engine) | `create_proctoring_record` (`prc-`, binds an existing core assessment; learner copied from it; `monitored_here: False`), `record_proofing_outcome` (`prf-`, outcome stored verbatim as reported by the provider) — every record carries **`reference_stub: True`**; proofing records also carry `decision_made: False` and `identity_provider: False`, proctoring records `decision_made: False`. Per PLATFORM-LAYER.md decision 1 these records are not identity evidence and decide nothing; nothing is monitored here. (Pearson VUE's remainder-addition sheet asserts online proctoring in its own words as a claimant on this gap — see ADDENDUM.md — not as a claim.) |
| Deterministic scoring & AI grading (0 of 8; assessments are administration records only, no score field exists by design) | reference (stub-engine) | `create_rule_record` (`scr-`, rule text held as data, `method: recorded_rules_only`, `applied_here: False` — never applied), `record_reported_outcome` (`rpo-`, outcome recorded **verbatim** as reported by an external assessor against an existing core assessment; `computed_here: False`; the core assessment record is byte-identical before/after, pinned by test) — every record carries **`reference_stub: True`** and state `recorded_reference_only`, consistent with the founding design: assessments stay administration records and nothing is computed |
| General cloud hosting / PaaS (4 of 8; multi-tenancy is a deployment property) | reference (stub-engine) | `create_deployment_record` (`dep-`, tenancy/region labels held verbatim as data, `hosted_here: False`, `multi_tenant_here: False`), `deployment_summary` — derived count plus the build's own posture stated plainly (`build_tenancy: single_tenant_reference`) — every record carries **`reference_stub: True`**. Per PLATFORM-LAYER.md decision 6, a fork's hosting substrate does not transfer; recording a posture hosts nothing |
| Collaboration & social learning (1 of 8) | built | `create_study_group` (`grp-`, binds a Core course and recorded member learners), `record_group_activity` (`act-`, activity label stored verbatim as reported; the learner must be a recorded member when members are recorded), `get_study_group` / `list_study_groups` (activity counts and total derived at read), `list_group_activities` (learner-scoped). Group/activity records over core enrollments only |
| Data storage & processing services beyond the substrate's own records | built | `create_dataset_declaration` (`dsv-`, source label and reported row count held as reported data, `rows_stored_here: False`; row counts are non-negative ints, booleans/floats rejected), `dataset_projection` — a deterministic derivation over the CORE records at an explicit `as_of` (counts only, via the core report; the declared reported count is echoed as reported data, never reconciled), `list_dataset_declarations`. No rows are stored or returned anywhere |
| Notifications & reminders (0 of 8) | built | `create_notification_rule` (`ntr-`, triggers: derived-overdue assignments, assignments due within a recorded window, upcoming assessment sessions), `evaluate_notifications` — one deterministic pass over the core records at an explicit `as_of`, producing receipts (`nrc-`) deduplicated on (rule, reference, learner) so re-evaluation is idempotent; every receipt carries **`reference_transport: True`** and state `recorded_reference_only` — nothing is sent; `list_notification_receipts` (learner-scoped) |
| Integrations & APIs as a union function (0 of 8) | reference (stub-engine) | `create_integration_record` (`int-`, endpoint label held verbatim as data, `executed_here: False`, `connected_here: False`), `list_integration_records` — every record carries **`reference_stub: True`** and state `recorded_reference_only`; creating one changes **no** core record (pinned by test against the core report) and calls nothing. The family's only first-pass hit in this group was the substring "api" inside "Human C**api**tal Management". This build's own REST surface remains its own design, as the union spec states |

Cross-cutting, per the group's doctrines: the founding **no-score
invariant** pinned over the whole extension surface by a recursive
key scan (no `score`-/`grade`-shaped key in any returned value, core
or extension); opaque `*_ref` strings and the core's `learner_id`
convention only, so no record shape can hold a name, email, phone,
or identifier; derived-never-stored for every computed value
(presence matches, pipeline counts, simulation current state, group
activity counts, dataset projections, notification evaluation);
RBAC via the existing `learn.access` actions, enforced before any
state change or id allocation (failed operations consume no id);
learner scope mirrors the store's; every successful mutation is
recorded on the core audit log with an `ext_`-prefixed action, and
denied write attempts are recorded with a `:denied` suffix.

**Re-judgments: none.** Every build entry was honestly carriable in
records form under the no-score invariant, and every stub entry
ships as a labeled reference implementation at its drafted
disposition.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
