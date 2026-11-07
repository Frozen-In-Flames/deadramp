# Final GAPS batch — Singleton 48, Learning Management L2

Unit: the 16 OPEN entries in GAPS.md under "Singleton 48 —
Learning Management L2 (1 fork, new category)" (the 17th entry,
"Identity provider / MFA / SSO service", was already closed as
re-scoped under PLATFORM-LAYER.md and is not touched here).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07): 12 build-extension, 4 stub-engine — exactly as triaged
in `../../gaps-batch/inventory.json`.

All extension code is in one new module, `src/lms/extensions.py`
(`LmsExtensions`, wrapping the core `LmsStore`); every existing core
module is byte-identical to its pre-batch state (SHA-256 verified
against the pre-work baseline; `store.py` still hashes to the
shipped `820d9712…`). Full suite: 133 tests before, **166 tests
after, OK**, including the fresh mutation-verified negative control
recorded in `tests/README.md`.

**No entry was re-judged.** On a close reading of UNION-SPEC.md
each drafted disposition fits, with the in-substrate forms stated
in the batch brief: delivery = session records with status derived
from core progress records (never a content runtime); packaging /
xAPI = manifest and statement records with conformance-shaped
validation OF THE RECORDS (never a SCORM player or xAPI endpoint,
and no conformance certification is claimed — the derived result
carries `method: record_validation_only`); analytics /
recommendation = deterministic derivations over held records,
method-labeled, never a learned model; notification transport =
labeled `reference_transport` receipts (nothing is sent).

One test-era rescope, disclosed rather than silent: the shipped
suite arrived with 1 pre-existing failure —
`test_nosignal_addition`'s git-HEAD pin asserted HEAD held 2 spec
sheets, true only before that unit's own ship landed (HEAD now
holds 3). The pin was rescoped to its own era slice (the first 2
HEAD sheets, exactly the sheets that existed before its append),
with the rescope disclosed in the test's docstring; the pin's
strength (neither pre-existing sheet may change) is unchanged.
No core code and no spec sheet was touched by the rescope.

| Entry (GAPS.md text) | Disposition | Built (module: `lms/extensions.py`) |
|---|---|---|
| Learning delivery engine (the LMS runtime itself) | built | `create_delivery_session` (`dls-`, mode enum, content item must belong to the course), `get_delivery_session` / `list_delivery_sessions` (views), `delivery_status` — the stored record carries **no status key**; status (`enrolled` / `in_progress` / `completed` / `not_started`) is derived at read from the core progress records via `_derive_delivery_status`, labeled `derived_from_core_progress_records` |
| SCORM / AICC / cmi5 packaging & distribution runtime | built | `create_package` (`pkg-`, standard in the packaging subset of the core's own list, item refs must resolve to core content items), `package_conformance` (derived record validation: has entries / entries resolve / entry standards match the manifest; `conformant` derived, never stored), `record_distribution` / `list_distributions` (`dst-`, state `recorded` — a record of distribution, nothing deployed) |
| xAPI protocol runtime & LRS conformance (statement records are Core; the protocol engine is not) | built | `statement_conformance` (derived over the core statements: exact eight-key shape re-read from the store, verbs non-empty, result text verbatim-string-only; counts by verb), `record_statement_forward` / `list_statement_forwards` (`fwd-`, **`reference_transport: True`**, state `recorded_reference_only` — nothing transmitted) |
| EHRI integration engine | reference (stub-engine) | `create_ehri_feed_record` (`ehr-`, period `YYYY-MM` validated, learner refs must exist, count snapshot), `list_ehri_feed_records` — every record carries **`reference_stub: True`** and state `recorded_reference_only`; no feed is collected, transmitted, or reported |
| Learning analytics & outcomes engines | built | `analytics_summary` (aggregate progress counts by status, completed share of progress RECORDS in integer bps, compliance counts by derived status at an explicit `as_of`, statement/session/response counts; `method: deterministic_counts`), `outcomes_by_course` (per-course progress-by-status, event and registration counts) — counts and record shares only, no per-learner value |
| Career mapping & recommendation engine | built | `create_career_path` (`crp-`, competency/course refs must resolve, order preserved), `recommend_training` — deterministic gap derivation (`method: deterministic_gap_match`): a competency is covered when any core learner-competency record exists (levels never interpreted); a path course is recommended when the learner has no completed progress for it; path order, never a ranking |
| Leadership succession planning suite | built | `create_succession_plan` (`suc-`, opaque `role_ref`, candidates must be registered learners, required competencies must resolve), `succession_coverage` — derived per-candidate covered/missing lists and a `covers_all` boolean by presence match (`method: deterministic_presence_match`); no readiness score |
| Candidate review / talent acquisition system | built | `create_application` (`app-`, opaque `candidate_ref` / `program_ref` — applicants need not be learners), `review_application` — recorded decision (`accepted` / `declined`) with **separation of duties**: the creator may not review their own application (mirrors the core SF-182 rule), double review rejected |
| Employee survey engine | built | `create_survey` (`svy-`, questions as verbatim text), `record_survey_response` (`rsp-`, opaque `respondent_ref`, answers must be strings, one per question, stored verbatim — a numeric answer is rejected, so no answer can become a score), `survey_summary` — derived counts of identical verbatim answers per question (`method: verbatim_answer_counts`), never parsed or averaged |
| Knowledge base / wiki platform (adjacent product) | built | `create_kb_article` (`kba-`), `revise_kb_article` (revisions append-only), `get_kb_article` / `search_kb` — views derive `version_count` and current body from the revision list at read; the stored record holds the revisions, no version counter |
| Web CMS platform (adjacent product) | built | `create_cms_page` (`pg-`, unique slug enforced), `publish_cms_page` (recorded draft → published state; double publish rejected), `get_cms_page` / `list_cms_pages` — page records only; nothing is rendered or served |
| Content authoring tools & lesson-plan editor | reference (stub-engine) | `create_authoring_draft` (`dft-`, optional link to a core lesson plan), `revise_authoring_draft` (revisions append-only), `get_authoring_draft` / `list_authoring_drafts` — every draft view carries **`reference_stub: True`**, state `recorded_reference_only`; the core lesson plan is untouched by the draft surface (pinned by test) |
| SF-182 form rendering / routing / signature workflow (authorization records are Core) | reference (stub-engine) | `create_form_workflow_record` (`frm-`, authorization must resolve to a core record, its state snapshot recorded, steps default to render → route → sign as data), `list_form_workflow_records` — every record carries **`reference_stub: True`**, state `recorded_reference_only`; nothing is rendered, routed, or signed, and the core authorization decision stands unchanged (pinned by test) |
| Configurable report builder & dashboards | built | `create_report_definition` (`rpd-`, sections validated against the six allowed section names, no repeats, no results stored on the definition), `run_report_definition` — derives each section's counts from the core records at run time (`method: deterministic_counts`); the dashboard form is a definition plus its derived run |
| Workflow execution engine (the registry holds definitions only) | reference (stub-engine) | `create_execution_record` (`exe-`, the core workflow definition's steps copied as data), `list_execution_records` — every record carries **`reference_stub: True`**, state `recorded_reference_only`; creating one changes **no** core record and no other extension record (pinned by test against notification/registration counts and the definition itself) — the registry still never executes |
| Notification automation & delivery transport | built | `create_notification_rule` (`ntr-`, trigger enum), `evaluate_notification_rules` — deterministic pass: for `compliance_overdue` rules, one receipt per assignment derived overdue at an explicit `as_of` (recipient match or the `*` broadcast marker), each receipt also recording a core notification record; **`reference_transport: True`**, state `recorded_reference_only` on every receipt (`rcpt-`); no email/SMS/push is sent, ever |

Cross-cutting, per the group's doctrines: the founding **no-score
invariant binds the extension surface exactly as it binds the
core** — a recursive key scan over 20 extension surfaces (records,
views, derivations, stub records) finds no `score` / `score_*` /
`*_score` key, pinned in `test_gaps_batch.TestCrossCutting`;
all parties are opaque `*_ref` strings; derived values are derived
at read and never stored (delivery status, package conformance,
analytics, recommendation gaps, succession coverage, report
results, survey tallies, KB version counts); RBAC reuses the core
permission actions (catalog for packages/KB/CMS/authoring,
progress for delivery, experience for the xAPI surface, plan for
career/succession, authorization for applications and form
records, workflow for surveys/report definitions/notification
rules, compliance for EHRI records, report for analytics and
report runs) with learner scope mirroring the store; every
successful mutation is recorded on the core audit log with an
`ext_`-prefixed action.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
