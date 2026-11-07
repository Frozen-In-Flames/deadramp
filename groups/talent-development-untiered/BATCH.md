# Final GAPS batch — Untiered Set 20, Talent Development (2 forks, tier null; NEW CATEGORY)

Unit: the 4 OPEN entries in GAPS.md under "Untiered Set 20 —
Talent Development (2 forks, tier null; NEW CATEGORY)"
(inventory idx 930–933 in `../../gaps-batch/inventory.json`;
idx 934, "Platform layer (the AWS GovCloud substrate one fork
names)", was already closed `re-scoped` at batch foundation
under PLATFORM-LAYER.md and is not touched). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 2
build-extension, 2 stub-engine — **exactly as triaged**. **No
re-judgments**: on close reading against this set's union spec,
both build-extension entries have an honest records form in
this substrate (stated at their entries below, with the bound
named rather than smoothed over), and both stub-engine entries
are engine-over-external-system entries whose labeled reference
form is the drafted one.

All extension code is in one new module,
`src/talentdev/extensions.py` (`TalentDevExtensions`, wrapping
the core `TalentDevStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified:
`store.py` still `8d30cd13…`, all 7 of 7 unchanged). Full
suite: 58 tests before, **86 tests after, OK** (28 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in
`tests/README.md` (the `_latest_label` earliest-reading drill:
86 ran, exactly 4 failures under mutation, restored
byte-identical and re-verified).

**Tier discipline binds the extension surface exactly as it
binds the core.** Nothing here asserts or records a tier, a
control baseline, or an equivalence: no record shape carries a
tier-shaped key, and a test scans every extension record and
derived view recursively for tier/baseline/equivalence keys —
alongside the founding shapes scan (score, grade, rank, rating,
rate, money keys, personal-data keys) and a stored-record float
scan. BetterUp's one documented control claim (privacy
safeguarding, prose weight, no mechanism named) remains the
fork's claim about itself in UNION-SPEC.md; nothing here
converts it into a build attainment.

**Talent-area discipline, per the founding build:** people
appear only as opaque references validated to be incapable of
being an email address (attendance records read the participant
reference from the core participation, never from the caller;
administration reports validate the subject reference with the
core's own rule); **no score is computed anywhere** — attendance
labels are a fixed administration vocabulary, every other
outcome is a reported label recorded verbatim, and every
derived figure is a count or a sum of recorded counts, derived
at read and stored nowhere; no record shape can hold session
content, assessment content, or model content (pinned by exact
key sets and TypeError tests: no public method accepts a
`**kwargs`, and smuggled `content=` / `email=` / `weights=`
keyword arguments raise `TypeError`).

Cross-cutting: RBAC rides the core's fixed action set (delivery
sessions and attendance under `programs`; instrument references
and administration reports under `assess`; trend definitions and
model references/reports under `insights`; all reads under
`read`), enforced before any state change or id allocation, so
failed operations consume no id and change nothing; denials are
recorded on the core audit log as `ext_<action>:denied` and
successful mutations as `ext_<action>`. The surface is
store-level only: the HTTP service and CLI are unchanged. The
single derivation seam is `_latest_label` (the most recently
recorded record's label), shared by every latest-label view.

## Per-entry dispositions

| Entry (GAPS.md text, idx) | Disposition | Built (module: `talentdev/extensions.py`) |
|---|---|---|
| Live development delivery (the sessions behind a program; their form is unnamed by either description) (930) | built (build-extension) | `schedule_delivery_session` (`ses-`, bound to a core program; label + caller-stated `mode_label` held as data — the form is unnamed by either description, so no delivery taxonomy was invented; record states `delivered_here: False`, `content_held_here: False`, state `recorded_session_only`), `record_attendance` (`att-`, bound to a core participation of the session's own program — a participation in another program is refused with no id consumed; one attendance record per participation per session; the label is the fixed administration vocabulary `attended` / `missed` / `partial`; the participant reference is read from the core participation, never supplied), `program_delivery_view` (session count, attendance count, counts by recorded label, distinct-participant count, and latest recorded attendance label, all derived at read via the `_latest_label` seam; the stored session record carries no count key, pinned). What is built is the records layer a delivery's operation would be recorded through; no session is delivered here and no record claims otherwise. |
| Assessment instruments and their administration / scoring engines (931) | reference (stub-engine) | `register_instrument_reference` (`itr-`, one per core assessment, refused twice with no id consumed; holds the assessment's instrument label exactly as the core recorded it, as data) + `record_administration_report` (`adr-`, the administering system's outcome label held verbatim; subject an opaque reference under the core's validation; the record carries no numeric field of any kind, pinned) — every record carries **`reference_stub: True`** with `instrument_held_here: False`, `administered_here: False`, `judged_here: False` throughout (the spelling follows the batch's adjudicated form: the founding no-score key scan forbids a key containing "score", so the not-judged flag is `judged_here`); `instrument_view` derives report count, counts by reported label, and latest reported label at read. Pinned by test: registering a reference and recording reports leave the bound core assessment byte-identical, the core summary unchanged, and create no core result record — the core's own result records remain the administration-outcome records of this substrate. |
| Analytics / trend-computation engine behind the dashboard (932) | built (build-extension) | `create_trend_definition` (`trd-`, a definition held as data: organization + definition label + the core snapshot metric label it is stated over; `definition_only: True`, `computed_here: False` for the trend engine itself; the stored record carries no totals, pinned) + `trend_view` (derived at read over the core's OWN recorded insight snapshots for the definition's organization and metric: snapshot count, sum of recorded cohort sizes, sum of recorded exhibiting counts, latest recorded period label via the `_latest_label` seam; snapshots of other metrics and other organizations never join). **The honest form is narrower than the entry's name, stated plainly:** no trend is computed over raw workforce data, no dashboard is rendered, and no proportion, change, or trend figure of any kind is produced — the view is deterministic sums and counts over aggregates this substrate already records, under the core's small-cohort guard. The disposition stays build-extension on that stated scope, on the Media set's optimization precedent (records plus deterministic derivations, the engine itself not built, the bound stated rather than smoothed over). |
| AI models (no fork describes one — registered for completeness only, not as a claimed-function gap) (933) | reference (stub-engine) | `register_model_reference` (`mod-`, model and purpose labels held as data, exactly as a caller states them) + `record_model_report` (`mdr-`, the external operator's outcome label held verbatim) + `model_view` (report count, counts by reported label, latest reported label, derived at read) — every record carries **`reference_stub: True`** with `inference_here: False` and `model_held_here: False`. The entry's own text bounds it: no fork describes an AI model, and the founding spec's named absences record AI as token-verified absent from both descriptions — so the reference form records that the surface exists and claims nothing behind it. Pinned by test: the class has no inference-shaped method at all (no `infer` / `predict` / `recommend` / `generate` / `train` / `run_model` / `complete`), and registering a reference changes no core record. |

## What this unit does not change

- The section's platform-layer entry (idx 934, the AWS GovCloud
  substrate one fork names) was already closed in writing under
  PLATFORM-LAYER.md decision 6 and is not re-opened.
- No core module changes; no HTTP surface is added (the batch
  pattern is a store-level extension surface, as in the sibling
  units).
- The category boundary stands: nothing here imports a taxonomy,
  doctrine, or code form from Talent Management, Learning
  Management, or Education & Training — the adjudicated forms
  cited (caller-reported labels, reference stubs, the
  no-"score"-key spelling) are batch-wide forms, applied inside
  this set's own substrate and vocabulary.
