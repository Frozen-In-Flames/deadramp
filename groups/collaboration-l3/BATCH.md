# Final GAPS batch — Group 6, Collaboration L3-adjacent

This unit closes the 9 open entries of the GAPS.md section
"Group 6 — Collaboration L3-adjacent (17 forks)" (inventory idx
72–80) under the decisions in `../../gaps-batch/DECISION.md`
(ratified 2026-11-07) and `../../PLATFORM-LAYER.md`.

What landed: one new module, `src/collab/extensions.py`
(`CollabExtensions`, wrapping the core `CollabStore`; all seven
core modules byte-identical, SHA-256 verified — store.py still
`bd8941693f91df9705340102a0932f17463583dfaba785ae9222528b79aa880c`,
the shipped hash), and `tests/test_gaps_batch.py` (38 tests).
Full suite: **251 → 289 tests**, all passing.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over the
group's OWN records (core records and extension records). Access
discipline is carried from the core: every operation resolves its
workspace through the core store, so the membership boundary and
the `read` permission bind reads and writes alike; extension
writes map to the core `post` action (held by member and admin),
denied write attempts are audited `ext_*:denied`, and successful
mutations land on the same append-only, hash-chained log with
`ext_`-prefixed actions, recorded before the record commits
(AU-5). The **auditor role holds no extension permission** — it is
not a workspace member and holds no `read`, so it is denied on
every extension operation, matching this tree's High-baseline
AC-5 posture. Nothing in this surface computes a score: a
recursive key scan over the derived views finds no
score/grade/rating/percent/rank key (pinned by test).

## Per-entry disposition

| Idx | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 74 | Records & governance beyond the versioning/audit seed (5) | built | Retention-policy records (`gpol-`; `retention_days` held as data, `retention_enforced_here: False` — enforcement is the deployment layer's records schedule, PLATFORM-LAYER.md decision 4) + legal-hold records (`hold-`) with reported state labels (`hst-`) whose current state is derived at read via `_current_hold_label` (the batch's fresh negative control; the stored hold record carries no state key) + disposition DECISION records (`rdec-`; a `dispose_reported` decision is refused whole while the derived eligibility — retention elapsed AND no active hold — is shut; `executed_here: False`). `governance_view` derives retention elapsed / active hold / eligibility at read. A governance record pinned to change no core file record. |
| 76 | Task & project management beyond board cards (2) | built | Project records (`proj-`) over core boards, milestone records (`mile-`), card links (`lnk-`; duplicate link refused), card-state records (`cst-`; verbatim reported labels, current state derived at read, default `reported_not_started`; a state for an unlinked card is refused), and dependency records (`dep-`; self-dependency refused). `project_view` derives each card's current state and exact counts by state — counts and states only, no progress score anywhere. Core card records pinned byte-identical across extension operations. |
| 77 | Learning / training / mentoring (1) | built | Course records (`crs-`; kind training/mentoring/learning), enrollment records (`enr-`) over opaque learner refs, completion records (`cmp-`; outcomes verbatim, `assessed_here: False`). `course_view` derives enrollment count and completions by outcome label — counts only. Nothing is taught or assessed here. |
| 78 | Knowledge management (0 claims in this group; carried from the L2 union) | built | The Customer Service knowledge-base form: `create_article` (`kb-` + first `kbrev-` revision), `revise_article` (appends; earlier revisions never change; no update or delete), `get_article` / `list_articles` (current title/body and revision count derived at read from the latest revision — the stored article record holds only tags and provenance, pinned by an exact key-set test), `list_article_revisions` (full append-only history), `search_articles` (literal substring over current text — the registry-metadata pattern, not a search engine). |
| 72 | Workflow / process-automation engines (4 siblings) | reference | Labeled reference records: workflow definitions (`wfd-`) held as DATA (an ordered list of step labels; `reference_stub: True`, state `recorded_reference_only`, `executed_here: False`). Per the house registry-never-executes doctrine, a definition is never run — pinned behaviorally: registering a definition leaves core file, card, and workspace records byte-identical. |
| 73 | AI assistance & speech (5) | reference | Labeled reference records: assistant declarations (`ai-`; `inference_here: False`, `method: recorded_declaration_only`), reported outputs (`aio-`) held as opaque references only — no output text exists in any shape (pinned by `TypeError` on a smuggled `output_text=`), transcription jobs (`trj-`; media as opaque ref, `transcribed_here: False`) with reported outcomes (`tro-`; transcript held only as an opaque `result_ref`). |
| 75 | Voice / telephony / contact center (2) | reference | Labeled reference records: voice channel records (`vch-`; `connected_here: False`, `media_here: False`) + call-session records (`call-`; participants are opaque refs). No media exists in this build and nothing connects or streams. |
| 79 | Meetings / video media transport (0 claims in this group) | reference | Labeled reference records: meeting-session records (`mtg-`; optionally linked to a core calendar event, unknown event refused) + reported outcome records (`mtr-`; any recording held only as an opaque `recording_ref`); `media_here: False` throughout. Session records only — the coordination surface around meetings (calendaring, channels, presence) remains Core. |
| 80 | E-signature (0 claims in this group) | reference | Labeled reference records (the Legal & Policy L2 remainder-addition form): envelopes (`env-`; optional core file ref; `reference_stub: True`, state `recorded_reference_only`, `signed_here: False`) + ceremony event records (`sgn-`; opaque signer ref, reported ceremony label verbatim; `signed_here: False`). No shape has a field that could hold a signature value — the field does not exist (pinned by exact key sets and `TypeError` on a smuggled `signature=`). Nothing is signed and no binding or validity is effected here. |

Closure tokens: 4 entries close as `built` (74, 76, 77, 78) and 5
as `reference` (72, 73, 75, 79, 80) — the drafted split held
exactly.

## Re-judgments

None. Every build-extension entry was carried in the records form
described above, and every stub-engine entry shipped as its
drafted labeled reference implementation. Two calls nearest the
line are stated plainly rather than re-judged:

- **Retention decisions (idx 74).** The disposition half of the
  governance entry closes as DECISION records with derived
  eligibility, never execution — the same adjudication the Data
  Management batch units took under PLATFORM-LAYER.md decision 4,
  and the entry's own union-spec text ("retention rides with the
  Extended records & governance function") names retention-period
  enforcement as the gap; what this build supplies is the records
  and derivation layer in front of it, with `executed_here: False`
  on every decision.
- **Knowledge management (idx 78).** The entry carries zero claims
  in this group (carried from the L2 union, per its own text). It
  closes `built` in the registry form because the article substrate
  — records, revisions, literal search — is genuinely implemented
  here over this group's own workspace boundary, not merely
  declared; no content-experience or delivery claim is made for it.

## Not covered by this unit

- The Collaboration L2 section's own batch entries (a different
  unit, in `../collaboration-l2/`), and the remainder addition's
  named gap (collaborative continuous monitoring service), which
  belongs to the "Remainder Addition — Collaboration L3-adjacent"
  section, not this one.
- Execution itself, in every family that names it: no workflow
  runs, no disposition is executed, no call or meeting is carried,
  no signature is effected, and no inference or transcription is
  performed. Store-level surface only (no HTTP routes), matching
  the sibling batch units' pattern; the service layer is untouched.
