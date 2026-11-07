# Final GAPS batch — Untiered Set 25, Learning Management

Unit: the 6 OPEN entries in GAPS.md under "Untiered Set 25 —
Learning Management (1 fork, tier null)" (idx 951–956 in
`../../gaps-batch/inventory.json`; the section's seventh entry,
"Platform layer", was already closed as re-scoped under
PLATFORM-LAYER.md and is not touched here). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): 5
build-extension, 1 stub-engine as triaged — with **one
re-judgment** under qualification 1, recorded below.

All extension code is in one new module, `src/lms/extensions.py`
(`LmsExtensions`, wrapping the core `LmsStore`); every existing
core module is byte-identical to its pre-batch state (SHA-256
verified against the shipped accounting in this group's README;
`store.py` still hashes to `820d9712…`). Full suite: 114 tests
before, **146 tests after, OK**, including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline, carried onto the new surface:** this set is
untiered — the fork's impact level is "Unknown" and its CMMC
tier is null. The extension asserts no baseline and draws no
equivalence, and no record or view on the new surface carries a
tier-shaped key at all (recursive key scan, pinned in
`test_gaps_batch.TestCrossCutting`).

**One re-judgment (idx 952).** "Real-time collaboration &
session recording services" was triaged build-extension. On a
close reading of the union spec, its substance is the fork's
first capability bullet — "Real-time collaboration with audio,
video, shared content, and recording capabilities" — that is,
synchronous media transport and media capture. Those have no
records decomposition beyond session metadata: there is no
registry over this substrate's own records that *is* a real-time
collaboration service, the way a media registry *is* a
repository's records form (idx 954) or session scheduling *is*
a classroom's administration form (idx 951). Per DECISION.md
qualification 1 and the batch brief's media/streaming shape,
idx 952 therefore ships as a **labeled reference
implementation**: collaboration and recording records carrying
`reference_stub: True` and `reference_transport: True`, state
`recorded_reference_only`, shared content and recordings named
by opaque reference only, content never held, capture never
performed here (`recorded_here: False`).

Two boundary calls, stated rather than silent:

- **Grading (idx 955)** closes *built* in the form the entry's
  own text bounds: "(the fork's asserted function, registered
  as specified-not-implemented — the build still computes no
  score)". Assignment and submission records plus evaluation
  records whose outcome is caller-supplied text recorded
  verbatim — the substrate's standing treatment of outcomes
  (statement `result_text`, competency levels, citation
  treatment in the sibling builds). Nothing is parsed, made
  numeric, or computed: `computed_here: False` on every
  evaluation record, and the no-score key scan is extended to
  grade-shaped keys over the whole extension surface.
- **User administration (idx 956)** closes *built* as
  administration action records over the core learner registry,
  the form the union spec registers ("the product's own user
  management; distinct from the build's RBAC hooks and from
  the founding group's IdP gap"). The surface holds no
  credential, performs no authentication, and never modifies a
  core learner record (pinned); records carry
  `identity_provider: False` per PLATFORM-LAYER.md decision 1.

| Entry (GAPS.md text) | Disposition | Built (module: `lms/extensions.py`) |
|---|---|---|
| Virtual school / virtual classroom delivery runtime | built | `create_classroom_session` (`vcs-`, bound to a core course and optionally one of its core events — an event of another course is rejected; participant refs must resolve to core learners; `delivered_here: False`), `record_classroom_outcome` (`vco-`, outcome label verbatim with `outcome_basis: caller_reported`), `get_` / `list_classroom_sessions` — views derive `outcome_count` and `latest_outcome_label` at read, never stored; `classroom_summary` (deterministic counts, `method: deterministic_counts`); learner scope is participation |
| Real-time collaboration & session recording services | **reference (re-judged from build-extension; grounds above)** | `create_collaboration_record` (`col-`, optional core course / classroom-session binding, shared content named by opaque refs only; `reference_stub: True`, `reference_transport: True`, state `recorded_reference_only`, `collaborated_here: False`), `record_recording_record` (`rcd-`, opaque media ref + optional validated SHA-256 + caller-reported duration carried as reported data; `content_held: False`, `recorded_here: False`); learner scope is participation |
| Course material authoring workspace | reference (stub-engine) | `create_authoring_draft` (`dft-`, optional core course/content/lesson-plan bindings with the L2 mismatch rules), `revise_authoring_draft` (revisions append-only; views derive current body and `version_count` at read); every view carries `reference_stub: True` and state `recorded_reference_only`; pinned to change no core record |
| Media & shared-materials repository service | built | `create_media_item` (`med-`, metadata registry: opaque `media_ref`, kind enum, optional validated SHA-256, optional reported `size_bytes` with bools rejected; `content_held: False` — no content-shaped parameter exists, `content=` raises TypeError), `record_media_share` (`shr-`, exactly one target — learner ref or course — which must resolve; `distributed_here: False`); item views derive `share_count` and shared-with lists at read, learner-filtered for learner actors |
| Assignment, evaluation & grading engine (the fork's asserted function, registered as specified-not-implemented — the build still computes no score) | built | `create_coursework_assignment` (`asn-`, bound to a core course; the stored record carries no status and no outcome field), `record_submission` (`sub-`, work named by opaque ref + optional checksum, `content_held: False`), `record_evaluation` (`evl-`, `outcome_text` verbatim — a score-looking string stays a string — `outcome_basis: caller_reported`, `computed_here: False`; **separation of duties**: the submission's recorder may not record its evaluation, mirroring the core SF-182 rule; one evaluation per submission), `coursework_summary` (deterministic counts only — no outcome is ever aggregated) |
| User administration service | built | `record_user_admin_action` (`uad-`, labels `provisioned` / `suspended` / `reinstated` / `deprovisioned` over a core learner ref that must resolve; `identity_provider: False`; a `password=` kwarg raises TypeError — no credential-shaped parameter exists), `user_admin_view` — the learner's `current_admin_state` is **derived at read** from the latest recorded action via `_current_admin_state`, never stored, `method: derived_from_recorded_actions`; pinned to never modify the core learner record |

Cross-cutting, per the group's doctrines: the founding
**no-score invariant binds the extension surface exactly as it
binds the core** — a recursive key scan over every extension
record and view finds no `score` / `score_*` / `*_score` key and
no key containing `grade`, pinned in
`test_gaps_batch.TestCrossCutting`; a second recursive scan
finds no tier-shaped key (`tier` / `cmmc` / `baseline` /
`fedramp`) anywhere on the surface, pinning tier null in the
extension as the spec tests pin it on the sheet; all parties are
opaque `*_ref` strings; derived values are derived at read and
never stored (session outcome labels, media share counts,
coursework counts, current admin state); RBAC reuses the core
permission actions (registration for classroom/collaboration,
catalog for authoring/media, progress for coursework, learner
for user administration, report for the summaries) with learner
scope mirroring the store; every successful mutation is recorded
on the core audit log with an `ext_`-prefixed action; denied
writes consume no id (pinned); no public extension method
accepts `**kwargs` (signature pin), so no content-, credential-,
or score-shaped argument can be smuggled past the signatures.

One build note, recorded for honesty: in this tree's shipped
permission matrix `catalog_write` and `learner_write` are
admin-only (the instructor write set excludes them), so the
authoring, media, and user-administration write surfaces are
admin-operated here, while classroom and coursework writes sit
under instructor writes (`registration_write` /
`progress_write`). That is the carried core's own matrix,
applied as shipped — not a narrowing introduced by this unit
(the same note the L1 sibling recorded for its tier).

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
