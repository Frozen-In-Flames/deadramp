# Final GAPS batch — Group 21, Human Resources L2

Unit: the 16 OPEN entries in GAPS.md under "Group 21 — Human
Resources L2 (4 forks)" (inventory idx 213–228). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 12
build-extension, 4 stub-engine — exactly as triaged in
`../../gaps-batch/inventory.json`. (The separate GAPS.md section
"Remainder Addition — Human Resources L2 (+3 forks)" is a different
unit and is not touched here.)

All extension code is in one new module, `src/hr/extensions.py`
(`HrExtensions`, wrapping the core `HrStore`); every existing core
module is byte-identical to its pre-batch state (SHA-256 verified
against the pre-work baseline; `store.py` still hashes to the
shipped `ec34ab5e…`). Full suite: 89 tests before, **140 tests
after, OK**, including the fresh mutation-verified negative control
recorded in `tests/README.md` (the weighted-mean mutant: 140 ran,
exactly 2 failures under mutation, restored and re-verified).

**One entry's build form needed a stated judgment** (not a
re-judgment — the drafted build-extension disposition stands):

- *Weighted cumulative & consensus scoring computation.* The
  founding design (UNION-SPEC Core 5) stores human ratings verbatim
  and has **no aggregate field by design**; a stored aggregate, an
  average written onto an evaluation, or a score field on any record
  would break that invariant, and had the entry required one it
  would have been re-judged to a labeled reference implementation.
  It does not: the honest build form is a computation performed **at
  read** over the verbatim entries, with the weights recorded as
  data on a crediting-plan record (built under the job-analysis
  entry, idx 216), producing a derived view that is never stored
  and never written back. The view's values are exact Fractions of
  the verbatim ratings. Pins: the stored crediting plan and every
  other stored extension record carry no aggregate key (recursive
  key scan); computing the view changes no extension container and
  leaves the core evaluation record deep-equal; repeated views are
  identical. What remains genuinely unbuilt is a *stored* scoring
  system of record — that is the founding design's deliberate
  exclusion, not a gap this batch reopens.

Two further scope boundaries recorded rather than smoothed over:

- *Retirement benefits calculator* (idx 224) computes the accrual
  side exactly (service months × the plan's recorded accrual rate,
  integer arithmetic, derived at read, paying nothing) and no
  currency amount: converting an accrual fraction into money
  requires the member's pay figure, and no field in this build can
  hold a pay figure (the group's structural privacy rule). The
  estimate view states the boundary (`currency_amount: None`,
  `pays_nothing: True`) instead of importing the figure.
- *General cloud hosting / platform services* (idx 228) was triaged
  stub-engine, not rescope-platform, so it lands as triaged: a
  labeled reference record stating the build's single-tenant
  reference posture. Its substance agrees with PLATFORM-LAYER.md
  decision 6 (hosting is a deployment property that does not
  transfer); the record itself carries that reference. No platform
  service is claimed or provisioned.

| Entry (GAPS.md text, idx) | Disposition | Built (module: `hr/extensions.py`) |
|---|---|---|
| AI talent intelligence & matching engines (the group's AI flagship) (213) | built | `create_match_rule` (`mtr-`, stages + panel-entry threshold + completion requirement recorded as data), `evaluate_match_rule` — deterministic derivation over the vacancy's applications (`method: deterministic_rule_match`): a candidate matches on recorded stage, verbatim panel-entry count, and panel completion, each row carrying that evidence in application-id order (no ranking); employee actors see only their own rows. No learned model anywhere. |
| Applicant-tracking workflow engines (end-to-end hiring workflow automation, job-board posting / sync) (214) | reference (stub-engine) | `create_workflow_definition` (`wfl-`, steps recorded as stage-name data), `record_posting_request` (`pst-`) — every record carries **`reference_stub: True`** and state `recorded_reference_only`; posting receipts also **`reference_transport: True`**. Pinned by test: creating them changes no core record and moves no application stage; nothing is executed, posted, or synced. |
| Position classification intelligence (series & grade recommendation tools) (215) | built | `create_classification_reference` (`clr-`, series/grade + title keywords), `recommend_classification` — deterministic keyword match of the position's recorded title against the library (`method: deterministic_keyword_match`), returning every match with its matched keywords; `classification_comparison` derives recorded-vs-recommended agreement. The position record is never modified (pinned deep-equal). |
| Job analysis & crediting-plan tooling (216) | built | `create_job_analysis` (`jan-`, competencies with recorded level labels, never interpreted numerically), `create_crediting_plan` (`crp-`) — criteria referencing panel evaluations of the vacancy, weights positive integers summing to exactly 100, recorded as data: the inspectable rule the scoring view computes with. |
| Assessment delivery via third-party providers & assessment content (217) | reference (stub-engine) | `create_assessment_content` (`cnt-`, reference metadata only — no assessment content is held), `record_assessment_delivery` (`dlv-`, bound to a core evaluation record, which stays unchanged) — every record carries **`reference_stub: True`**, state `recorded_reference_only`; delivery reads are employee-scoped through the evaluation's application. Nothing is delivered to any provider. |
| Weighted cumulative & consensus scoring computation (ratings are Core records, stored verbatim; no aggregate field exists by design) (218) | built — derived-view form; grounds in the judgment note above | `panel_score_view` — per-criterion exact means of the verbatim ratings combined by the plan's recorded weights via the `_weighted_cumulative` seam (`method: weighted_mean_of_verbatim_ratings`); criteria without entries are named in `pending_criteria` and excluded; `panel_consensus_view` — verbatim ratings, exact mean, and consensus spread (max − min) for one panel. Both views: `derived: True`, `stored: False`, computed at read, stored nowhere. |
| Certificates of eligibles as standalone assembled documents (the referral stage is Core) (219) | built | `assemble_certificate` (`crt-`) — assembles the vacancy's applications at the Core `referred` stage (ids stored as the document's content), `annotate_certificate` (append-only annotations), `get_certificate` / `list_certificates` — entries and `entry_count` are derived at read from the core application records; an employee may read a certificate only when every entry is their own application (multi-person certificates are denied to employees, pinned). |
| Career sites, talent communities, campus recruiting & events platforms (220) | built | `create_career_site` / `set_career_site_state` (`cst-`, configuration records — nothing is served; the state is a recorded publication state), `create_community` + `add_community_member` (`cmu-`/`cmm-`, membership registry, employee-scoped reads), `create_recruiting_event` / `register_for_event` (`evt-`/`evr-`) with `registration_count` derived at read and never stored (pinned). No page is published and no invitation is sent. |
| Talent mobility & workforce-exchange marketplace engines (221) | built | `create_mobility_listing` / `set_mobility_listing_state` (`lst-`), `record_mobility_interest` (`int-`, open listings only, duplicates rejected), `mobility_matches` — deterministic series-overlap derivation (`method: deterministic_series_overlap`): the evidence set is the series of positions behind the person's own applications, returned with the view. No marketplace transaction occurs. |
| Talent management suite depth beyond records (222) | built | `create_development_program` (`prg-`, retention/development/mentoring kinds), `enroll_in_program` / `set_enrollment_state` (`enr-`, duplicate live enrollment rejected), `program_summary` — enrollment counts by state derived at read (`method: deterministic_counts`), gated on `report_read` like the core report. |
| Workforce planning & resource-management analytics / models (223) | built | `workforce_analytics` — deterministic counts over the core records (persons/positions/vacancies/applications/lifecycle-by-derived-status) plus the derived vacancy rate in integer bps; `create_planning_scenario` (`scn-`, assumptions recorded as data: attrition bps + horizon), `scenario_projection` — integer projection derived at read (`headcount * attrition_bps // 10000` per period, floor), assumptions echoed, nothing stored on the scenario (pinned). |
| Retirement benefits calculator (224) | built — accrual form; boundary in the note above | `create_retirement_plan_parameters` (`ppr-`, recorded accrual bps/year + vesting months per plan), `retirement_estimate` — `accrued_bps = service_months * accrual_bps_per_year // 12`, service years and vesting derived (`method: integer_accrual_derivation`), `currency_amount: None`, `pays_nothing: True`; employee-scoped. |
| Employee learning & upskilling delivery (225) | built | `create_course` (`crs-`, catalog records), `assign_course` / `set_learning_state` (`lrn-`, duplicate live assignment rejected, re-assignment after completion allowed), `learning_summary` — per-person counts by state derived at read. No content is delivered to anyone. |
| Integration connector engines (job boards, personnel-record and payroll-center systems, agency HRIS sync) (226) | reference (stub-engine) | `create_connector` (`con-`, opaque system labels — "usajobs", "eopf", "nfc", "ibc", "agency_hris" — naming systems this build does not connect to), `record_sync` (`syn-`, the reported record count held as data) — every record carries **`reference_stub: True`**, state `recorded_reference_only`; sync receipts also **`reference_transport: True`**. Pinned by test against the core report: creating them changes no core record; nothing syncs. |
| Document & template assembly engines (227) | built | `create_template` (`tpl-`) — source kind position or vacancy; `{field}` placeholders validated at creation against that kind's recorded fields (an unknown or cross-kind placeholder is rejected), `assemble_document` (`doc-`) — deterministic substitution over one core record into a document artifact record; the source record is unchanged (pinned). |
| General cloud hosting / platform services (228) | reference (stub-engine) — see the scope note above | `create_hosting_record` (`hst-`) — states the single-tenant reference posture and the PLATFORM-LAYER.md decision-6 reference on the record itself; carries **`reference_stub: True`**, state `recorded_reference_only`. It provisions nothing, hosts nothing, and claims no platform service. |

Cross-cutting, per the group's doctrines: the founding **privacy
discipline** binds the extension exactly as it binds the core —
every stored extension record is walked against the core privacy
test's forbidden-key set (no name/SSN/DOB/salary/compensation/pay/
address/phone/email key can exist), and no stored extension record
carries an aggregate key (score/average/aggregate/mean/
weighted_cumulative/consensus/…), pinning derived-never-stored for
the scoring surface. Person-bound extension records are keyed by
opaque `person_ref` only and are employee-scoped exactly as the
core scopes them. RBAC rides the core's fixed action set (mapping
stated in the module docstring), enforced before any state change
or id allocation; denials consume no id and record nothing (the
store-level convention — denial auditing lives in the service
layer), while successful extension mutations audit on the core log
with `ext_`-prefixed actions. Malformed input is rejected whole:
validation precedes id allocation on every create.
