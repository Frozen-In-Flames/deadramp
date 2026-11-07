# Final GAPS batch — Singleton 45, Grant Management L2

Unit: the 11 OPEN entries in GAPS.md under "Singleton 45 — Grant
Management L2 (1 fork, new category)". Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 9
build-extension, 2 stub-engine — as triaged in
`../../gaps-batch/inventory.json` (idx 431–441), with ONE
re-judgment of form (the merit-scoring half of the eligibility
entry, below) that does not change its closure token. The 12th
entry in the section (identity provider / identity management
service) was already closed `re-scoped` under PLATFORM-LAYER.md
and is not touched.

All extension code is in one new module, `src/grants/extensions.py`
(`GrantsExtensions`, wrapping the core `GrantsStore`); every
existing core module is byte-identical to its shipped state
(SHA-256 verified against the pre-work baseline — `store.py` still
`1e340e6a…`). Full suite: 93 tests before, **135 tests after, OK**,
including the fresh mutation-verified negative control recorded in
`tests/README.md`.

**Founding doctrines carried into the extension:** the award-cap
discipline generalizes to a disbursement cap (recorded
disbursements against an award never exceed the award's recorded
amount, checked before anything is stored); money is integer
cents everywhere (floats, booleans, and strings rejected at the
boundary); and the two named absences stay honored — the extension
introduces no money *movement* (disbursement records move nothing)
and no scoring of any kind (see the re-judgment below).

## Re-judgment (1, of form — DECISION.md qualification 1)

**"Eligibility determination & merit-scoring engines (nothing is
scored, by design)"** was triaged build-extension. The entry has
two halves, and they do not stand alike under this group's spec:

- *Eligibility determination* is buildable as built: criteria held
  as data (a maximum requested amount in integer cents, required
  form-response fields, a response-field equality, an
  application-status set) and a determination derived at read by
  deterministic checks over the application's recorded fields —
  per-criterion outcomes returned as evidence, the determination
  itself never stored. A criteria check over recorded data is a
  derivation, not a score: it computes no aggregate, ranks nothing,
  and its inputs and rule are both records the substrate already
  holds.
- *Merit scoring* cannot be built as an engine without breaking
  the founding invariant. The union spec's core-boundary decision
  (2) is explicit: the fork's description contains no
  merit-scoring vocabulary, reviews record the reviewer's own
  words verbatim, and "nothing aggregates, ranks, or scores, and
  no record shape carries a score field — pinned by test." Any
  computed merit value would violate that decision. Following the
  Education & Training untiered unit's adjudicated precedent for
  exactly this entry shape, the merit half is therefore built in
  the only honest in-substrate form: **scoring-RULE records** held
  as data (`method: recorded_rules_only`, `applied_here: False`,
  never applied) plus **reported-outcome records** whose outcome
  text is stored verbatim as reported by an external reviewer
  against an existing core application (the core application
  record is byte-identical before/after, pinned by test).

The disposition token is unchanged (`built`): records plus the
substrate's derivations are what build-extension means in this
batch, and the entry's buildable half is built as a derivation
while its unbuildable half is built in records form. What was
re-judged is the *engine* reading of the merit half, and the
grounds are recorded here rather than silently shipping a score.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `grants/extensions.py`) |
|---|---|---|
| Applicant portal web application (the responsive browser UI itself, incl. branding customization & rendering and device adaptation) | built | `create_portal_configuration` (`ptl-`, one per program: brand label, theme entries as string data, page inventory as data, device modes from the recorded `desktop`/`tablet`/`mobile` vocabulary; `rendered_here: False`, `served_here: False` — no page is rendered and nothing is served), `get_portal_configuration` |
| Workflow execution engine (the registry holds definitions only) | reference (stub-engine) | `create_workflow_run_reference` (`wfr-`, copies the core workflow definition's steps as data; `reference_stub: True`, state `recorded_reference_only`, `executed_here: False`; pinned by test to change no application and no workflow record — the registry-never-executes doctrine is not repealed), `list_workflow_run_references` |
| Form designer & form rendering engine (the registry holds definitions only) | built | `create_form_layout` (`fly-`, section/field placement as data against an existing core form definition; every placed field validated against the definition's own field names, duplicate placement rejected whole; `rendered_here: False`), `get_form_layout` / `list_form_layouts` |
| Document storage & content management engine (core holds metadata / checksums only) | built | `create_vault_record` (`vlt-`, opaque `storage_ref` + optional retention label bound to a core document record; `content_held: False`), `get_vault_record` / `list_vault_records`, `verify_vault_content` — a derivation comparing the SHA-256 of caller-supplied bytes with the core document's recorded checksum; content is never stored |
| E-signature signing engine (ceremony & cryptographic binding; signature events are recorded) | reference (stub-engine) | `create_signing_reference` (`sgr-`, an intended signing recorded against a core document; `reference_stub: True`, state `recorded_reference_only`, `ceremony_here: False`, `cryptographic_binding: False`; pinned by test to leave the core document unsigned — signature *events* remain the core's own record), `list_signing_references` |
| Payment / disbursement execution for awards (awards are records; no money moves) | built | `record_disbursement` (`dis-`, integer cents, positive only, under the `_check_disbursement_cap` seam — recorded disbursements never exceed the award's recorded amount, checked before storing so a rejection consumes no id; `disbursed_here: False`, `paid_here: False` — recording one moves no money), `get_disbursement` / `list_disbursements`, `disbursement_summary` (recorded total and remaining derived at read, never stored) |
| Reporting & analytics engines beyond registry summaries (dashboards, ad-hoc generation, exports) | built | `create_dashboard` (`dsh-`, panel definitions as data over a fixed metric vocabulary of derivations), `run_dashboard` — derives every panel value from core records at run time (`method: deterministic_counts`), stores nothing, repeat runs over unchanged records identical; `create_export_record` (`exp-`, manifest of record counts derived from core records at creation, `delivered_here: False`), `get_export_record` / `list_export_records` |
| Notification & message delivery transport (email / SMS / push; records only) | built | `record_delivery` (`dlv-`, a receipt binding a channel — `email`/`sms`/`push` — to an existing core notification record; `reference_transport: True`, state `recorded_reference_only`, `delivered_here: False`; the core notification surface is unchanged), `list_deliveries` |
| Applicant matching & opportunity recommendation | built | `create_match_criteria` (`mtc-`, required form-response field names held as data), `evaluate_matches` — a deterministic presence match over each program application's recorded responses, in application creation order, listing `missing_fields` as evidence (`method: deterministic_presence_match`); no ranking and no fit value is computed, and the evaluation stores nothing |
| Eligibility determination & merit-scoring engines (nothing is scored, by design) | built, with the merit half in records form (re-judged — see above) | Eligibility: `create_eligibility_criteria` (`elc-`, criteria as validated data: `max_requested_cents`, `required_response_field`, `response_field_equals`, `application_status_in`), `evaluate_eligibility` — deterministic per-criterion checks over the application's recorded fields, determination derived at read, `stored: False`, nothing persisted. Merit: `create_scoring_rule` (`scr-`, rule text as data, `method: recorded_rules_only`, `applied_here: False`), `record_review_outcome` (`rvo-`, outcome text verbatim as reported by an external reviewer, `computed_here: False`; core application untouched, pinned) |
| Closeout automation & financial reconciliation engines | built | `create_reconciliation` (`rec-`, holds the externally reported disbursed figure as data; the view derives `recorded_disbursed_cents`, `remaining_vs_award_cents`, and `variance_vs_reported_cents` at read in exact integer cents — the stored record carries no variance key, pinned), `get_reconciliation` / `list_reconciliations`, `closeout_readiness` — a derivation over core records (outstanding post-award report obligations, reconciliation presence, named blockers), `record_closeout` (`clo-`, gated on derived readiness, one per award, `executed_here: False`, `automation_here: False` — no automation executes), `list_closeouts` |

Cross-cutting, per the group's doctrines: integer-cents money
discipline at every new boundary; failed operations consume no id
and change nothing (validation and cap checks run before minting);
program membership and the role matrix enforced through the core
store's own access-checked reads, layered with `grants.access`
role checks (`record` for extension writes, `read` for reads and
derivations) enforced before any state change; every successful
extension mutation recorded on the core audit log with an
`ext_`-prefixed action, denied write attempts with a `:denied`
suffix; the founding **no-score invariant** pinned over the whole
extension surface by a recursive key scan (no score-, rating-,
grade-, or rank-shaped key in any returned value, core or
extension) in `tests/test_gaps_batch.py`.

Not covered, named plainly: the portal's actual rendering, form
rendering, and any served UI (the entry's own text is the browser
application itself; this substrate holds its configuration data —
the same core-boundary decision the union spec recorded for the
portal at build time); content storage itself (vault records point
at storage held elsewhere; content is never in this substrate);
payment rails (disbursement is a records surface — execution stays
with the embedding organization's payment systems, as the union
spec's money boundary decision states); and message *composition*
transport beyond notification receipts (message records themselves
are Core). HTTP exposure of the extension surface was out of scope
for the batch pattern (extensions land in `src/` with tests); the
service layer is untouched and byte-identical.
