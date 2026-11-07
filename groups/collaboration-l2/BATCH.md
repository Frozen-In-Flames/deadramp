# Final GAPS batch — Group 2, Collaboration L2

Built under `gaps-batch/DECISION.md` (ratified 2026-11-07) for the
8 open entries of the GAPS.md section "Group 2 — Collaboration L2
(57 forks)" (inventory idx 14-20 and 22). The ninth entry of the
section, idx 21 "Meetings / video media transport (coordination
surface is core; a stdlib build carries no A/V)", was already
closed re-scoped in writing before this unit and is not part of
it; the extension surface therefore carries no meetings section,
unlike the sibling tiers' batch units.

The drafted triage split held on close reading for all 8 entries:
4 closed `built`, 4 closed `reference`. Nothing was re-judged.

## What landed

One new module, `src/collab/extensions.py` (`CollabExtensions`, a
wrapper around `CollabStore`): 8 entry surfaces, 34 new tests in
`tests/test_gaps_batch.py`. Every core module is byte-identical
to the shipped build (SHA-256 checked after the build; store.py
still reads `d2b943e2…`). The forms mirror the sibling tiers'
batch units (`../collaboration-l3/BATCH.md`,
`../collaboration-l1/BATCH.md`), held at this group's Moderate
apparatus: the core's plain append-only audit log (AU-2/AU-3/
AU-6/AU-9, which at Moderate holds on both sides of the
crosswalk), no hash-chained audit and no auditor role (those are
the High tier's uplifts), and no FAR-side-only audit note (that
is the Low tier's precision).

Form choices carried from the more recent sibling unit (L3),
recorded here so the record shows the choice rather than hiding
it: signatures are actor-first (the core store's own convention),
extension writes map uniformly to the core `post` action (the
content-contribution action held by member and admin; the viewer
is read-only), and learning enrollment holds learners as opaque
`learner_ref` references (this group's own minimal-people design:
the spec's only people noun is the workspace member, and
rosters belong to the embedding organization). L1 took the
actor-last / `manage_members` / member-bound forms at its tier;
the derivations and labels are otherwise identical across tiers.

Access discipline, carried from the core: every operation
resolves its workspace through the core store, so the membership
boundary binds throughout; denied write attempts by role-holding
actors are audited with a `:denied` suffix; successful extension
mutations are audited with `ext_`-prefixed actions on the same
append-only log; the audit entry is recorded before the extension
record commits, so an audit failure changes nothing and consumes
no id. Validation precedes mutation: a failed operation consumes
no id and changes nothing.

Suite: 208 tests before, 242 after, all green. Fresh negative
control: the legal-hold current-state derivation
(`_current_hold_label`) — live drill produced exactly 3
not-passing tests (2 failures + 1 error), all in
`test_gaps_batch.py`; see `tests/README.md` for the record and
`TestNegativeControlHoldDerivation` for the standing three-legged
control.

## Per-entry disposition

### idx 19 — "Records & governance beyond the versioning/audit seed" — build-extension → **built**

Retention-policy records (`gpol-`, retention period as data,
`retention_enforced_here: False`), legal-hold records (`hold-`)
with append-only reported state labels (`hst-`), and disposition
decision records (`rdec-`) over core workspace/file records. The
hold's current state, the active-hold lookup, retention elapsed,
and disposition eligibility are all derived at read and stored
nowhere (views carry `derived: True`). A `dispose_reported`
decision is refused whole with `ValidationError` while the
derived eligibility is shut (retention not elapsed under the
policy, or an active hold covers the file); eligible decisions
are recorded with `eligible_at_record` and `executed_here:
False`. Recording a governance record changes no core file
record (pinned by test). Retention enforcement and disposition
execution are the embedding organization's records schedule at
the deployment layer (PLATFORM-LAYER.md decision 4) — the build
records and derives; it never deletes.

### idx 17 — "Task & project management beyond board cards" — build-extension → **built**

Project records (`proj-`) over core boards, milestone records
(`mile-`), card links (`lnk-`) binding core cards to milestones
(the card must sit on the project's board, duplicate links
refused), dependency records (`dep-`, self-dependency refused),
and card state records (`cst-`, refused for unlinked cards).
`project_view` derives each linked card's current state from the
latest recorded label (default `reported_not_started`), plus
exact counts (`cards_by_state`, `milestone_count`,
`dependency_count`). Counts and states only: no score-shaped key
exists anywhere in any extension view (pinned by a recursive key
scan). The core card record is never touched.

### idx 16 — "Learning, training, mentoring" — build-extension → **built**

Course records (`crs-`, kind one of training/mentoring/
learning), enrollment records (`enr-`) over opaque learner
references, and completion records (`cmp-`) holding verbatim
reported outcome labels (`reported_completed` /
`reported_in_progress` / `reported_withdrawn`) with
`assessed_here: False` — nothing is taught or assessed here.
`course_view` derives enrollment and per-outcome completion
counts at read; no pass rate, grade, or score is computed
(recursive key scan pinned).

### idx 20 — "Knowledge management" — build-extension → **built**

Article records in the Customer Service knowledge-base form: the
stored article shape is pinned by test to exactly {id,
workspace_id, tags, created_by, created_utc}; the text lives in
append-only revision records (`kbrev-`) and the current title/
body are derived at read from the latest revision. Search is the
core's literal case-insensitive substring doctrine over current
text — no ranking, no relevance score.

### idx 14 — "Workflow / process-automation engines (the group's #2 claim family)" — stub-engine → **reference**

Labeled reference implementation (`reference_stub: True`,
`executed_here: False`, state `recorded_reference_only`):
workflow definitions held as data (`wfd-`, steps as a non-empty
list of step names) and never run, triggered, or scheduled — the
house registry-never-executes doctrine, pinned behaviorally
(registering a definition leaves core file, card, and workspace
records deep-equal).

### idx 15 — "AI assistance, speech, and analytics" — stub-engine → **reference**

Labeled reference implementation: assistant registrations
(`ai-`, kind assistance/speech/analytics, method
`recorded_declaration_only`, `inference_here: False`), reported
outputs (`aio-`) held as opaque `output_ref`s with an optional
opaque `target_ref` — the method signature carries no output-text
parameter, so smuggling text in raises `TypeError` (pinned).
Transcription jobs (`trj-`, media as an opaque reference) and
reported outcomes (`tro-`, result as an opaque reference) carry
`transcribed_here: False`. No inference runs and no speech is
transcribed in this build.

### idx 18 — "Voice / telephony / contact center" — stub-engine → **reference**

Labeled reference implementation: voice-channel registrations
(`vch-`, kind voice/telephony/contact_center, `connected_here:
False`, `media_here: False`) and call-session records (`call-`)
with opaque participant references. No call is placed, connected,
or streamed; no media exists in this build.

### idx 22 — "E-signature" — stub-engine → **reference**

Labeled reference implementation in the Legal & Policy form:
envelope records (`env-`, optionally over a core file record)
and ceremony-event records (`sgn-`) with reported labels against
opaque signer references. Stored key sets are pinned by test
(envelope exactly {id, workspace_id, envelope_ref, file_id,
reference_stub, signed_here, created_by, created_utc}; ceremony
exactly {id, workspace_id, envelope_id, signer_ref, event_label,
reference_stub, signed_here, created_by, created_utc}); no field
anywhere can hold a signature value — the signatures carry no
such parameter, so smuggling one in raises `TypeError` (pinned);
`signed_here: False` throughout.

## Tier discipline record

- Baseline held: the Moderate baseline (800-53 Rev. 5 Moderate /
  CMMC L2) is neither raised nor lowered by this unit; no L3
  apparatus (hash-chained audit, auditor role) and no L1 audit
  caveat were imported.
- The platform-layer items stay where PLATFORM-LAYER.md puts
  them: identity proofing and MFA stay with the embedding
  organization (decision 1; demo identities are hooks, not an
  IdP), no FIPS-validated cryptography is claimed (decision 2),
  and retention enforcement stays at the deployment layer
  (decision 4) — the governance surface records and derives only.
- What is still not here, by design: no content beyond opaque
  references on the AI/voice/signature surfaces, no execution of
  any registered definition, no deletion anywhere.

## Verification (builder side)

- Full suite before: 208 tests, OK. After: 242 tests, OK.
- Core byte-identity: SHA-256 of all 7 `src/collab/` core modules
  verified unchanged after the build (`sha256sum -c` against the
  pre-build record); `extensions.py` is the only new source file.
- Mutation drill on the fresh negative control: backup to
  `scratch/extensions.py.batch-backup`, patched
  `_current_hold_label`'s return at its own line (the identical
  line text also occurs in `_current_card_label`; the mutation
  was scoped by line number to the hold derivation) from
  `states[-1]` to `states[0]`, suite ran 242 with exactly 3 not
  passing (2 failures + 1 error), all in `tests/test_gaps_batch.py`;
  restored from backup, SHA-256 verified identical, suite re-run
  green.
