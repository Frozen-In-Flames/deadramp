# Final GAPS batch, second unit — Remainder Addition, Human Resources L2

Unit: the 6 OPEN entries in GAPS.md under "Remainder Addition —
Human Resources L2 (+3 forks)" (inventory idx 607–612).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07): **6 build-extension, 0 stub-engine — closed exactly
as triaged in `../../gaps-batch/inventory.json`: 6 built, 0
reference, 0 re-scoped, and no re-judgments.** (The first batch
unit for this group, the 16 entries under "Group 21 — Human
Resources L2 (4 forks)", is shipped and recorded in `BATCH.md`;
it is not touched here.)

All addition code is in one new module,
`src/hr/extensions_addition.py` (`HrExtensionsAddition`, wrapping
the core `HrStore`); every existing module — core and the first
unit's `extensions.py` alike — is byte-identical to its pre-unit
state (SHA-256 verified against the pre-work baseline; `store.py`
still hashes to the shipped `ec34ab5e…`, the first unit's
`extensions.py` to `f3063102…`). Full suite: 140 tests before,
**176 tests after, OK**, including the fresh mutation-verified
negative control recorded in `tests/README.md` (the leave-balance
mutant: 176 ran, exactly 3 failures under mutation, restored and
re-verified).

Scope boundaries recorded rather than smoothed over, one per
entry where the entry's prose reaches past the substrate:

- *Time, attendance & leave* (idx 607): GDC's Paycheck 8 prose
  names time-entry pre-edits under agency business rules. No rule
  engine edits an entry here: a correction is a new record, the
  original entry is never modified, and the effective minutes are
  derived at read (latest correction wins). Leave balances are
  likewise derived at read from recorded accrual rates, accrual
  events, and request states — no balance is stored.
- *Survey & listening* (idx 609): Perceptyx's platform includes
  dialogue and narrative feedback in the real product. This
  substrate holds reported values verbatim only: ratings bounded
  by the instrument's recorded scale and label-only signals. No
  method accepts free-text response content — there is no
  content, comment, or text parameter anywhere on the surface
  (pinned by a signature scan and by TypeError pins) — and
  summaries are deterministic counts per rating value, never a
  mean: no engagement score is computed anywhere, per the group's
  no-computed-scores doctrine.
- *Self-service portal & dashboard* (idx 611): the portal record
  states its own boundary on its face — `identity_provider:
  False` (SSO and role management stay with the embedding
  organization, PLATFORM-LAYER.md decision 1) and `served_here:
  False` (this build serves no portal; the profile is the
  configuration record an embedding portal would read). What is
  built is the records surface: profiles, self-service requests,
  and dashboard definitions whose figures derive at read.

| Entry (GAPS.md text, idx) | Disposition | Built (module: `hr/extensions_addition.py`) |
|---|---|---|
| Time, attendance & leave tracking engine (GDC; retires the group's two standing absences, leave & time-off and time & attendance, asserted in substance in its own prose; the tracking surface is an engine, not a records form) (607) | built | `record_time_entry` (`tim-`, minutes as a non-negative integer, kind label from a fixed vocabulary), `record_time_correction` (`tcr-`, a new record; the original entry is never edited), `list_time_entries` (views add `effective_minutes`, derived at read as the latest correction's minutes), `time_summary` (counts + effective totals derived at read, `method: deterministic_counts`); `create_leave_account` (`lva-`, accrual rate recorded as data, one account per person and kind), `record_leave_accrual` (`lac-`, period events), `create_leave_request` / `set_leave_request_state` / `list_leave_requests` (`lvr-`, recorded states requested/approved/denied/taken/cancelled), `leave_balance_view` — accrued = recorded rate × recorded periods, used via the `_leave_used_minutes` seam (approved or taken only), pending = still requested, balance derived at read (`method: integer_leave_accounting`), never stored. |
| Organizational chart generation & maintenance automation (GDC) (608) | built | `create_org_unit` (`ogu-`, unique opaque `unit_ref`, optional parent unit), `assign_position_to_unit` (`oga-`, binds a core position, which is never modified; a second assignment for one position is rejected), `record_org_change` (`ogc-`, a reported change with `applied_here: False`), `org_chart_view` — the chart generated at read from the current unit and assignment records (`method: deterministic_org_chart_derivation`), each unit carrying its derived position ids and count, unassigned core positions listed separately; freshness is pinned (a chart read before an assignment differs from one read after it, exactly by that assignment). |
| Employee engagement survey & listening platform (Perceptyx; its whole function, which has no taxonomy family) (609) | built | `create_survey_instrument` / `get_survey_instrument` (`svi-`, question definitions pinned to exactly `{question_ref, topic_label, max_rating}`), `record_survey_response` / `list_survey_responses` (`svr-`, answers pinned to exactly `{question_ref, rating}`, each rating an integer stored verbatim and bounded by the question's recorded scale), `survey_summary` — response count and per-question counts per rating value derived at read (`method: deterministic_counts`; no mean, no score), `record_listening_signal` / `list_listening_signals` (`lis-`, channel label from a fixed vocabulary plus a signal label — no narrative can be recorded), `record_feedback` / `list_feedback` (`fbk-`, multi-rater entries with verbatim 1..5 ratings; no aggregate computed or stored). Content-shaped input is refused structurally: unexpected keyword arguments raise TypeError, extra answer keys raise ValidationError. |
| Federal retirement & benefits administration platform depth (GRB fork excess, distinct from the existing calculator gap) (610) | built | `create_admin_case` (`adc-`, bound to a core benefits record, which is never modified; kind label from the administration vocabulary), `add_admin_task` / `set_admin_task_state` / `cancel_admin_case` — a task checklist whose status is derived at read by `_derive_admin_case_status` (the core lifecycle derivation applied to this surface's own records: not_started / in_progress / complete, cancelled as a recorded flag; the stored record carries no status key, pinned), `get_admin_case` / `list_admin_cases` (employee-scoped through the bound benefits record), `record_admin_action` (`ada-`, reported actions with `administered_here: False`), `record_counseling_session` / `list_counseling_sessions` (`cns-`, reported sessions with `conducted_here: False`). No amount is computed; the calculator remains the first unit's separate entry. |
| Employee self-service portal & HR dashboard (GDC) (611) | built | `create_portal_profile` / `get_portal_profile` (`prt-`, one per person; section labels recorded as data; the record carries `identity_provider: False` and `served_here: False` on its face), `create_service_request` / `set_service_request_state` / `list_service_requests` (`ssr-`, case-shaped self-service records with recorded states), `create_dashboard` / `get_dashboard` (`dsh-`, the stored definition pinned to exactly `{id, title, panels, created_by, created_utc}` — no figure can be stored on it), `dashboard_view` — each panel's figure is the count of the core records of that kind visible to the actor, derived at read through the core's own scoped list methods (`method: deterministic_counts`), gated on `report_read`; freshness pinned (a dashboard recorded earlier reports records recorded after it). |
| Uniform allowance request processing (GDC) (612) | built | `create_allowance_request` (`uar-`, the requested amount as a positive integer number of cents — recorded request data, never a pay figure; float and bool amounts rejected), `set_allowance_request_state` (recorded states requested/approved/denied/fulfilled/cancelled), `record_allowance_step` / `list_allowance_steps` (`uas-`, processing steps with reported outcome labels and `processed_here: False`; recording a step changes no request state, pinned), `list_allowance_requests` (employee-scoped), `allowance_summary` — request counts and recorded-cents sums by state derived at read (`method: deterministic_counts`), gated on `report_read`. |

Cross-cutting, per the group's doctrines: the founding **privacy
discipline** binds the addition exactly as it binds the core and
the first unit — every stored addition record is walked against
the core privacy test's forbidden-key set (no name/SSN/DOB/
salary/compensation/pay/address/phone/email key can exist), no
stored addition record carries an aggregate key, and a signature
scan over every public method of `HrExtensionsAddition` asserts
no parameter can accept a real name, an identifier, a pay figure,
or free-text response content, and that no method takes
`**kwargs`. Person-bound addition records are keyed by opaque
`person_ref` only and are employee-scoped exactly as the core
scopes them (admin cases scope through their bound benefits
record; allowance steps through their request). RBAC rides the
core's fixed action set (mapping stated in the module docstring),
enforced before any state change or id allocation; denials
consume no id and record nothing, while successful addition
mutations audit on the core log with `ext2_`-prefixed actions.
Malformed input is rejected whole: validation precedes id
allocation on every create.
