# Final GAPS batch — Group 10, Collaboration L1

Unit: the 9 entries in GAPS.md under "Group 10 — Collaboration L1
(10 forks)" (4 `build-extension`, 5 `stub-engine` in
`../../gaps-batch/inventory.json`, idx 104–112). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
required re-judgment**: each fit its drafted disposition on a close
reading of this group's spec, in the forms stated below.

All extension code is in one new module,
`src/collab/extensions.py` (`CollabExtensions`, wrapping the core
`CollabStore`); every existing core module is byte-identical to
its pre-batch state (SHA-256 verified against the pre-work
baseline; `store.py` still `d2b943e2…`, the shipped hash — this
group's core is Group 2's code reused byte-identical, and the
batch adds a module beside it, never a change inside it). Full
suite: 192 tests before, **230 tests after, OK** (38 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines:

- RBAC is enforced through the core `collab.access` matrix — the
  extension maps each operation onto an existing core action (the
  core action set is fixed; the mapping is documented in the
  module docstring and per method) and enforces workspace
  membership through the core store itself, before any state
  change or id allocation. Governance writes (retention policies,
  holds, disposition decisions) map to `manage_members`, the
  matrix's administrative action, so they are platform-admin
  operations at this tier. Denied attempts are recorded on the
  core audit log as `ext_<action>:denied` and every successful
  mutation as `ext_<action>`. If an audit write fails, the record
  insertion and its id roll back before the error propagates
  (pinned by test) — no extension record exists whose audit entry
  does not. The audit claim stays on the FedRAMP Low side of the
  crosswalk only, as the founding spec's precision note requires;
  nothing of the sibling tiers' Moderate/High apparatus
  (hash-chained audit, auditor role, lockout) is imported.
- Derived values are derived at read and never stored: article
  current text and revision count, milestone state counts, hold
  currency, disposition eligibility, workspace analytics. Stored
  records carry no derived key; tests pin that.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries `reference_stub: True`, and no
  workflow runs, nothing is inferred or transcribed, no call
  connects, no media moves, and nothing is signed.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `collab/extensions.py`) |
|---|---|---|
| AI assistance / speech / analytics (4 of 10 — this group's top tagged family) | reference (stub-engine) | `register_assistant` (`ai-`, `reference_stub: True`, `inference_here: False`, `method: recorded_declaration_only`), `record_assistant_report` (`air-`, a reported outcome stored verbatim against an existing core message; `decided_here: False`; a test pins the referenced message byte-identical after the report), `register_transcription_job` (`trn-`, opaque `source_ref`; `transcribed_here: False`), `record_transcription_report` (`trnr-`, outcome verbatim, result held as an opaque `result_ref` only — the exact record shape is pinned by test and no field can hold transcript text), `workspace_analytics` (deterministic counts over core records — members, channels, messages, files, events, boards, cards — derived at read, `method: deterministic_counts_over_core_records`, stored nowhere; a test pins the counts move as records are added). The claims are the siblings' own product AI (Adobe's assistants, A-SCEND's AI audit tooling); this build ships no AI, and search stays the core's literal substring matching |
| Workflow / process automation (1) | reference (stub-engine) | `register_workflow_definition` (`wfd-`, an ordered list of step labels held as data; `reference_stub: True`, `state: recorded_reference_only`, `executed_here: False`). Per the house registry-never-executes doctrine, a definition is never run — pinned behaviorally: registering one leaves the core workspace record and message list byte-identical |
| Learning / training / mentoring (1) | built | `create_course` (`crs-`), `enroll_learner` (`enr-`, the learner must already be a workspace member — the core membership boundary governs person references here; duplicate enrollment refused), `record_completion` (`cmp-`, the outcome label stored **verbatim** as reported by whoever ran the course; `assessed_here: False` — this build assesses nothing), `course_view` (enrollment and completion counts derived at read; the stored course record carries no count key) |
| Knowledge management (1) | built | `create_article` (`kb-` + first `kbrev-` revision), `revise_article` (appends a revision; earlier revisions never change and there is no update or delete API), `get_article` / `list_articles` (current title/body and revision count derived at read from the latest revision — the stored article record holds only tags and provenance, pinned by an exact key-set test), `list_article_revisions` (the full append-only history), `search_articles` (literal substring search over current text — the registry pattern, not a search engine) |
| Voice / telephony / contact center | reference (stub-engine) | `register_voice_channel` (`vch-`, `reference_stub: True`, `connected_here: False`, `media_here: False`), `record_voice_session` (`vcs-`, a reported session outcome stored verbatim; same labels) — no media exists in this build, nothing connects, and no record shape can hold a phone number or call content |
| Task & project management beyond board cards | built | `create_milestone` (`ms-`, over an existing core board), `link_card_to_milestone` (`msl-`, the card must be on the milestone's board; duplicate links refused), `record_card_state` (`cst-`, the caller's state label stored verbatim; recording one changes no core card, pinned by test), `milestone_view` — linked-card count, cards with/without any recorded state, and counts per latest recorded state label, derived at read. **Counts and states only: no progress score, percentage, or completion rate is computed or stored** (the view's key set is pinned against score-shaped keys) |
| Records & governance beyond the versioning/audit seed | built | `create_retention_policy` (`pol-`, the operator's recorded schedule held as data; `retention_days` an int ≥ 0, booleans/floats/strings rejected whole), `place_hold` (`hld-`, over an existing core file; `executed_here: False`; placing one changes no core file record, pinned by test), `release_hold` (`hlr-`; hold currency is derived at read from the presence of a release record — the stored hold record carries no state key; double release refused), `disposition_eligibility` (retention met, active holds, and eligibility derived at read through the single seam `_disposition_eligible`, with an `at` override for deterministic evaluation), `record_disposition_decision` (`dsp-`, **gated**: recorded only when the seam derives eligible at the decision moment, otherwise refused whole with nothing stored; `executed_here: False` — per PLATFORM-LAYER.md decision 4, retention enforcement and disposition execution are the embedding organization's records schedule at the deployment layer; this build records the policy and the decision and disposes of nothing) |
| Meetings / video media transport | reference (stub-engine) | `record_meeting_session` (`mtg-`, a coordination record optionally bound to an existing core calendar event — the coordination surface around meetings is Core; `reference_stub: True`, `media_here: False`). Session records only: a standard-library text build carries no audio/video, and no session transports any |
| E-signature | reference (stub-engine) | `create_envelope` (`env-`, over an existing core file; `reference_stub: True`, `state: recorded_reference_only`, `signed_here: False`; the exact record shape is pinned by test — no field can hold a signature value, a certificate, or a credential), `record_ceremony_event` (`sgn-`, signer a workspace member by opaque username, the reported ceremony label stored verbatim; `signed_here: False`) — the Legal & Policy house form; nothing is signed and no binding or validity is effected here; signer identity assurance stays with the embedding organization (PLATFORM-LAYER.md decision 1). The spec records this family's zero claims as a wording artifact (Adobe bundles Acrobat Sign without using the taxonomy's phrasing); the artifact stands as recorded, and the surface is a reference record set, not a claim |

## Long-tail enumeration

Against the 21 functions of `UNION-SPEC.md`'s function ranking:

| Spec function | Where it lands |
|---|---|
| AI assistance, speech & analytics (1) | The AI reference entry |
| APIs, integrations & interoperability (2) | Core (the service is API-first) — no extension needed |
| Access control & authentication (3) | Core (L1 baseline hooks) — no extension needed; the extension surface enforces through it |
| Calendaring & scheduling (4) | Core — meeting sessions bind to it in the meetings entry |
| Workflow & process automation (5) | The workflow reference entry |
| Search & discovery (6) | Core (literal substring search); article search is in the knowledge entry, same pattern |
| Audit logging & trails (7) | Core (Low-side AU tracing only); every extension mutation and denial lands on the same append-only log as `ext_*` / `ext_*:denied` entries |
| Learning, training & mentoring (8) | The learning entry |
| Knowledge management & content experiences (9) | The knowledge entry |
| Messaging & chat (10) | Core — no extension needed |
| Meetings, video & web conferencing (11) | The meetings reference entry (media transport itself is not built, in any form) |
| Voice, telephony & contact center (12) | The voice reference entry |
| File sharing, storage & content management (13) | Core — governance records and envelopes bind to its file records |
| Shared workspaces & team collaboration (14) | Core — the boundary every extension record sits inside |
| Whiteboarding, visual collaboration & co-authoring (15) | Core — milestones and card states build over its boards/cards |
| Presence & availability (16) | Core — no extension needed |
| Task, project & work management (17) | The task/project entry (board cards remain the Core seed) |
| Electronic & digital signatures (18) | The e-signature reference entry |
| Notifications, alerts & emergency communications (19) | Core (the in-platform queue) — no extension needed |
| Encryption (20) | Platform note in the founding spec — stands on PLATFORM-LAYER.md decisions 2–3; not an entry in this unit and nothing here absorbs it |
| Records, governance & compliance management (21) | The records & governance entry (file versioning and the audit trail remain the Core seed it extends) |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Execution itself**, in every family that names it: no workflow
  runs, no disposition is executed, no hold is enforced against a
  connected system, no signature binds. The batch closes the
  records layer in front of those engines; the engines remain
  other systems' work, and the records say so on their face
  (`executed_here: False`, `signed_here: False`).
- **Media itself**: no audio, video, or call content exists in
  this build in any form — the voice and meetings entries are
  coordination and outcome records over transports that live
  elsewhere.
- **Assessment**: completion outcomes are recorded verbatim from
  whoever ran the course; nothing here grades, scores, or
  assesses a learner, and no milestone progress score is computed
  anywhere on the surface.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
