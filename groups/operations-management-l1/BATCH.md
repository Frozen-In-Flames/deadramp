# Final GAPS batch — Singleton 52, Operations Management L1

Unit: the 9 OPEN entries of this group's section in the repo-root
GAPS.md ("Singleton 52 — Operations Management L1 (1 fork)",
inventory idx 494–502). The category-union Extended families
registered under Group 36 (Operations Management L2) are a
different unit and are not touched or absorbed here; the L2
group's own batch unit (groups/operations-management-l2) shipped
earlier and is cited only for the category's adjudicated forms.

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/opsmgmt/extensions.py` (class `OpsExtensions`, wrapping the
core `OpsStore`), plus `tests/test_gaps_batch.py`. **No existing
core module was changed** — all seven pre-existing
`src/opsmgmt/*.py` files verified byte-identical by SHA-256
before and after (`store.py` remains
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
the group's recorded shipped hash).

Group discipline, applied to every entry: this build is the
operations records substrate only, at the **Low / L1** baseline.
The Moderate framing of Group 36 (whose code this group's `src/`
reuses byte-identical) is deliberately NOT imported: nothing here
claims a Moderate control, an 800-171 mapping, or any apparatus
the founding spec's precision notes exclude at this tier (AU-6,
SI-12, SC-28 stay unclaimed, exactly as UNION-SPEC.md states
them). Nothing in the extension executes, renders, publishes,
hosts, sends, books, pays, connects, or syncs. Engine entries are
built in their **records form**: registries of the thing,
records of its reported state, and deterministic derivations
over the group's own records. The founding discipline on review
is absolute and is kept exactly: **substrate records hold
verbatim outcomes only; nothing in this build computes a
score.** A review's score is stored as the reviewer reported it
— a recorded score is a report, never a computation — and no
aggregate, average, or ranking is derived anywhere. All `*_ref`
parameters are opaque tokens — whitespace, URL, hostname, and
IP-shaped values are rejected at the boundary — and links into
the core substrate use core ids validated through the core
store. RBAC reuses the founding 16-action matrix with no new
actions (mapping table in the module docstring); successful
mutations audit as `ext_*` actions on the core log, denied
attempts as `ext_*:denied`.

## Per-entry dispositions

### Build-extension (8) — records form in `opsmgmt.extensions`

1. **Submission management engine (custom submission forms /
   form builder, submission intake, reviewer assignment)** —
   `create_form_definition` / `update_form_definition` /
   `get_form_definition` / `list_form_definitions` /
   `record_submission` / `get_submission` / `list_submissions` /
   `assign_reviewer` / `withdraw_reviewer_assignment` /
   `list_reviewer_assignments` / `submission_view`. Form
   definitions held as data: field definitions are records
   (objects with a non-empty `name` and `kind`, names unique),
   versioned on update, carrying `rendered_here: False` —
   nothing is rendered. Submission records bind to a form
   definition; submitter-supplied field values ride only for
   fields the form defines and only as short label/reference
   strings (containers and numbers are rejected) — the intake
   record is not a content store, per the substrate's records
   discipline. Reviewer assignments are records over core
   directory persons (validated through the core store); a
   duplicate active assignment is refused, a withdrawn one
   frees the reviewer, and `submission_view` derives
   `current_reviewer_ids` and `review_count` at read — the
   stored submission carries neither key (pinned by test).
2. **Review & evaluation engine (reviewer / judge scoring and
   feedback; substrate inspection records hold verbatim
   outcomes only)** — `record_review` / `get_review` /
   `list_reviews` / `review_summary`. Review records store the
   reviewer's `score` (a scalar) and `feedback` **verbatim as
   reported**, under the founding discipline stated above:
   `score_computed_here: False` on every record, records
   immutable once written (no update/delete API, as the core
   inspections), and `review_summary` is counts only with
   `scores_aggregated: False` — a test pins that no
   aggregate/average/rank key exists in it. The judging engine
   itself — assignment workflows, score computation, feedback
   loops — is not here and is not implied.
3. **Automated communications** — `create_message_template` /
   `update_message_template` / `get_message_template` /
   `list_message_templates` / `record_dispatch_request` /
   `record_dispatch_outcome` / `get_dispatch_request` /
   `list_dispatch_requests` / `list_dispatch_outcomes`.
   Template records hold body text verbatim as data
   (`rendered_here: False`), versioned on update.
   Dispatch-request records name a recipient by opaque
   reference and carry `status: "recorded"` and
   `sent_here: False`; outcome records store the external
   sending system's reported status verbatim. Nothing is sent
   from this build.
4. **Reporting (the product's reporting capability, beyond
   registry summaries)** — `create_report_definition` /
   `update_report_definition` / `get_report_definition` /
   `list_report_definitions` / `record_report_run` /
   `list_report_runs` / `report_run_view`. Definitions are data
   (a name, an optional core-project scope, and metric names
   from a fixed set of eight: submission / review /
   dispatch-request / payment counts, payment total cents,
   session count, session conflict count, gallery item count —
   unknown metric names are refused at the boundary). Run
   records store **no figures** (pinned by test); a run's
   figures derive at read in `report_run_view` as counts of
   this substrate's own records and sums of recorded
   integer-cent amounts only. No new metric is invented — in
   particular no score, rate, or ratio is derivable from the
   metric set.
5. **Program website builder** — `create_site_definition` /
   `update_site_definition` / `get_site_definition` /
   `list_site_definitions`. Site definitions whose pages are
   held verbatim as data (each an object with a non-empty
   `kind` and `label`), versioned on update, carrying
   `published_here: False` and `rendered_here: False`. Nothing
   is published, rendered, or hosted.
6. **Galleries** — `create_gallery` / `add_gallery_item` /
   `get_gallery` / `list_galleries` / `list_gallery_items` /
   `gallery_view`. Gallery definitions plus item records
   holding an **opaque media reference** and an optional
   caption label only — there is no content field on the item
   shape (pinned by test) — carrying `hosted_here: False`.
   The item count in `gallery_view` is derived at read and
   never stored.
7. **Conference session scheduling** — `create_session` /
   `get_session` / `list_sessions` / `session_conflicts`.
   Session records (ISO times, room label, optional
   core-person speaker, optional core project; `ends_at` must
   follow `starts_at`). Conflicts are **derived at read** from
   the recorded times via the seam `_windows_overlap`
   (half-open windows: a session ending exactly when another
   begins does not overlap it): pairs sharing a room label or
   one speaker whose windows overlap are reported with the
   reason. The stored session carries no conflict key (pinned
   by test), the view carries `booked_here: False`, and
   nothing is booked externally.
8. **Payments** — `record_payment` /
   `record_payment_outcome` / `get_payment` / `list_payments` /
   `list_payment_outcomes` / `payment_view` /
   `payments_summary`. Payment records over recorded amounts
   in **integer cents** (floats and booleans rejected at the
   boundary, per the house money doctrine; minimum 1 cent),
   linked optionally to a core project and/or a submission,
   carrying `paid_here: False`. Outcome records store the
   external payment system's reported status verbatim
   (`reported_paid` / `reported_failed` / `reported_refunded`);
   `payment_view` derives `current_reported_status` at read
   from the latest outcome (the stored payment's own status
   never changes — pinned by test). The summary is counts and
   the sum of recorded cents only. Records, never execution
   against real rails.

### Stub-engine (1) — labeled reference implementation

9. **Third-party integrations** —
   `register_integration_reference` /
   `record_integration_event_reference` /
   `get_integration_reference` / `list_integration_references` /
   `list_integration_event_references`. Integration reference
   records (opaque integration reference, kind, optional scope
   reference) plus event reference records carrying reported
   statuses verbatim. Every record carries
   `reference_stub: True` (events additionally
   `reference_transport: True`), `connected_here: False`, and
   `synced_here: False`. Nothing connects to or syncs with any
   external system. This is also the founding spec's own
   placement: the fork names integrations **outside** its
   FedRAMP Minimum Assessment Scope (the one raw taxonomy hit
   in its description was removed as a scope-exclusion wording
   artifact), so the labeled-reference form is the honest
   ceiling here, not a shortcut.

## Re-judgments

None among the 9 entries. Every entry fit its drafted
disposition on a close reading of UNION-SPEC.md: the eight
build-extension entries all have an honest records form
consistent with how the founding spec already drew their lines
(the fork's two certified services as Extended engines over a
records substrate that presupposes exactly these records; the
seven out-of-scope capabilities as records of the thing named),
and the one stub-engine entry is the family the founding spec
itself places outside the assessment scope, shipped labeled.
Two boundaries are stated rather than smoothed over: review
scores are recorded **as reports** and never computed — the
entry closes on the records form of a review, not on a judging
engine; and report figures are counts/sums of recorded values
derived at read — the entry closes on reporting over this
substrate's records, not on the product's reporting surface.

## Tests and negative control

- Suite: **129 before → 175 after, OK** (46 new tests in
  `tests/test_gaps_batch.py`, at least one per entry, plus
  cross-cutting RBAC/audit, no-id-on-failure, and
  copies-are-copies pins).
- Fresh mutation-verified negative control: the session-overlap
  derivation `_windows_overlap` in
  `src/opsmgmt/extensions.py`. The in-test control
  (`TestSessionOverlapNegativeControl`) asserts the canonical
  expectation (an overlapping same-room pair derives exactly
  one room conflict), that a no-overlap mutant of the seam
  would not produce it (the conflict vanishes), and that
  treating the mutant's outcome as expected fails. Live drill
  on the real file: the seam's body was patched to
  `return False`; the full suite ran: **175 tests, exactly
  3 failures** —
  `test_gaps_batch.TestSessions.test_room_conflict_derived_at_read`,
  `test_gaps_batch.TestSessions.test_speaker_conflict_derived`,
  and
  `test_gaps_batch.TestSessionOverlapNegativeControl.test_overlap_derivation_canonical_but_mutant_not`.
  No core test failed. The file was restored from
  `scratch/extensions.py.premutation` and verified SHA-256
  identical
  (`2d77ed776ea5795001eecec64b82648390b28b34b3a0ae0c005400dda9dbbaed`)
  and the suite re-ran green. Recorded in tests/README.md;
  raw drill output in `scratch/gaps_batch_mutation_run.txt`.

## Unresolved

Nothing unresolved within this unit. The extension surface is a
store-level surface only, matching the batch pattern for sibling
units: no HTTP routes were added (the founding `service.py` is a
core module and stays byte-identical), so the extension is
consumed in-process, like the other groups' batch extensions.
