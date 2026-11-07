# Final GAPS batch — Untiered Set 21, Talent Management (2 forks, tier null)

Unit: the 8 open entries in GAPS.md under "Untiered Set 21 —
Talent Management (2 forks, tier null)" (idx 935–942 in
`../../gaps-batch/inventory.json`; 5 `build-extension`,
3 `stub-engine`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
is re-judged.** Three components inside built or reference
entries follow the batch's adjudicated forms, with the grounds
stated where they land (matching, inside the labor exchange
entry; delivery, inside the labor market information entry; the
identity-document component, inside the proctoring entry).

All extension code is in one new module,
`src/talentmgmt/extensions.py` (`TalentMgmtExtensions`, wrapping
the core `TalentMgmtStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified against
the accounting in this group's README; `store.py` still
`ff0cab40…`). Full suite: 102 tests before, **141 tests after,
OK** (39 new in `tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline binds the extension surface exactly as it
binds the core.** Nothing here asserts or records a tier, a
control baseline, or an equivalence: no record shape carries a
tier-shaped key, and a test scans every extension record and
derived view recursively for tier/baseline/equivalence keys (and
for float values, and for numeric lists in stored records — a
stored list of numbers could be a vector value). The forks'
documented control claims remain where `UNION-SPEC.md` put
them — the forks' claims about themselves, recorded in the
spec.

Cross-cutting, per the group's doctrines: RBAC is enforced
through the core `talentmgmt.access` matrix — the extension maps
each operation onto an existing core action (the core action set
is fixed) and checks it before any state change or id
allocation; organization access itself is resolved through the
core store's public API, so the core's membership boundary binds
every extension read and write exactly as it binds the core's;
denied attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`; candidates are opaque references validated
against the core candidate registry, and employers and external
systems are opaque `*_ref` strings; no record shape can hold a
real person's name, contact detail, or identifier, an identity
document, session media, assessment content, or a case note's
text (pinned by exact key sets and TypeError tests); **no score
is computed anywhere** — matches, proctoring outcomes, and UI
statuses are reported labels recorded verbatim; derived values
(learning progress, case activity counts, the exchange /
employer / LMI summaries, a UI claim's current reported status)
are computed at read and never stored.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `talentmgmt/extensions.py`) |
|---|---|---|
| Assessment proctoring & integrity services | reference (stub-engine) | `register_proctoring_session` (`pro-`, bound to a core assessment record; check kinds as labels from a fixed set; the candidate reference is read from the core assessment, never supplied) + `record_proctoring_report` (guarded `requested` → `reported` transition storing the service's outcome label and reported flag count verbatim) — `reference_stub: True`, `adjudicated_here: False`, `identity_document_held_here: False`, `session_media_held_here: False` throughout; no document is checked, no session is monitored, no integrity outcome is adjudicated here |
| Experiential technical learning platform | built (build-extension) | `create_learning_program` (`lrn-`, a definition: an ordered module list held as data, `content_held_here: False`), `enroll_candidate` (`enr-`, opaque candidate bound to a program, once per candidate per program), `record_module_completion` (`mod-`, a check-off record; the module bounds seam `_check_module_bounds` runs before anything is stored — the batch's fresh negative control), `learning_progress` (completed indices/labels, counts, and completion derived at read from the check-off records; the stored enrollment carries no progress key, pinned by test), `record_tutor_session` (`tut-`, metadata + verbatim outcome label, `session_content_held_here: False`) |
| Integration & API services layer | reference (stub-engine) | `register_integration_endpoint` (`iep-`, a definition record: opaque `system_ref`, kind and direction labels, `reference_stub: True`, `credentials_held_here: False`, `connected_here: False` — credentials and identity stay with the embedding organization per PLATFORM-LAYER.md decision 1), `record_integration_exchange` (`iex-`, a receipt: in/out record counts and an outcome label stored exactly as the connected system reports them, `reference_transport: True`, `data_moved_here: False`) |
| Labor exchange platform | built (build-extension) | `create_exchange_posting` / `close_exchange_posting` (`job-`, postings listed by opaque employer references, guarded open → closed lifecycle), `record_exchange_match` (`mat-`, a caller-reported pairing of a posting and an opaque candidate reference with the reporter's outcome label verbatim; one record per posting/candidate pair; `matched_here: False` — see note 1), `exchange_summary` (postings by status, matches by reported outcome label, distinct matched candidates — deterministic counts derived at read; no rate, ranking, or score) |
| Workforce case management system | built (build-extension) | `create_workforce_case` / `close_workforce_case` (`cas-`, an opaque participant reference — a core candidate — bound to a program label, guarded open → closed lifecycle), `record_case_activity` (`act-`, append-only records carrying a kind label from a fixed set and a short label; activities record against open cases only; no narrative note text exists — there is no parameter that could accept it), `get_workforce_case` (`activity_count` and `activities_by_kind` derived at read; the stored case record carries neither, pinned by test) |
| Employer services platform | built (build-extension) | `register_employer` (`emp-`, opaque employer references registered inside the organization — a workforce system's employer registry, distinct from the core's tenancy organizations), `create_service_request` / `complete_service_request` / `cancel_service_request` (`esr-`, a kind label held as data and a guarded open → completed / cancelled lifecycle; completion stores the caller's outcome label verbatim; nothing is dispatched or delivered here), `employer_services_summary` (employers, requests by kind and by status — deterministic counts derived at read) |
| Unemployment insurance integration & administration | reference (stub-engine) | `register_ui_claim` (`uic-`, a reference record: opaque claim reference + participant candidate reference + the UI program's own status label as reported; `reference_stub: True`, `determined_here: False`, `benefits_paid_here: False`), `record_ui_claim_report` (`uir-`, append-only status report records; `get_ui_claim` derives `current_reported_status` and `report_count` at read from the newest report — the registration label when none exists — and the stored claim carries neither, pinned by test), `record_ui_exchange` (`uie-`, a receipt: claims/determinations counts as reported, `reference_stub: True`, `reference_transport: True`, `administered_here: False`) |
| Labor market information service | built (build-extension) | `record_lmi_observation` (`lmi-`, a recorded data point: region / occupation / period labels, a metric kind label, and an integer value stored exactly as its opaque `source_ref` reported it; floats, booleans, and negatives rejected at the boundary; `collected_here: False` — nothing is collected from any external source here), `lmi_summary` (observations grouped by their recorded label tuple, each group carrying its observation count and the sum of its reported values, derived at read and deterministically ordered; no average, rate, or index is computed), `create_lmi_publication` (`pub-`, a definition held as data, `definition_only: True`, `delivered_here: False`), `record_lmi_distribution` (`dst-`, a receipt: recipient count as reported, `reference_transport: True`, `delivered_here: False` — see note 2) |

## Adjudication notes

**1. Matching, inside the labor exchange entry.** The entry's
own text names "job-seeker/employer matching exchanges," and
matching is inference: a stdlib records build has no matcher,
and computing one would contradict the category's founding
no-score doctrine. The component therefore ships in the batch's
adjudicated form for inference-shaped functions — the exchange
records a pairing only as a caller-reported record with the
reporter's outcome label verbatim and `matched_here: False` on
every match record (a recursive scan pins that no score-shaped
key exists anywhere in the surface). The entry as a whole is
**not** re-judged: its drafted disposition is build-extension,
its center of mass is the exchange's records platform (postings,
reported pairings, derived counts), and that platform is built.
What is not built is the match computation, and no record claims
otherwise.

**2. Delivery, inside the labor market information entry.**
Collection and analysis land as built records and a derived
summary (above). Delivery is transport: publications ship as
definitions held as data (`definition_only: True`,
`delivered_here: False`) and distributions as receipts carrying
`reference_transport: True`, exactly the batch's adjudicated
form for transport-shaped components. The entry as a whole is
not re-judged.

**3. The identity-document component, inside the proctoring
entry.** CodeSignal's description states its proctoring handles
government-issued identity documents and session video. This
build holds neither, by structural privacy: the session record
carries check-kind labels and the service's reported outcome,
and carries `identity_document_held_here: False` and
`session_media_held_here: False` on its face. Identity provision
itself stays with the embedding organization (PLATFORM-LAYER.md
decision 1); the fork's data practice remains recorded on its
spec sheet as its own, exactly as the founding build recorded
it.

## What this unit does not change

- The founding group's eight engine gaps registered under
  Remainder Group 3 (video interview platform, assessment
  delivery & scoring engines, predictive I-O models & AI,
  virtual event platform, pipeline automation engine, analytics
  & visualization engines, talent development programs, identity
  provider / candidate identity verification) are **not** in
  this unit's section and are not touched; they close under
  their own section.
- The section's platform-layer paragraph (encryption at rest,
  multi-tenancy, demo identities) was already closed in writing
  under PLATFORM-LAYER.md and is not re-opened.
- No core module changes; no HTTP surface is added (the batch
  pattern is a store-level extension surface, as in the sibling
  units).
