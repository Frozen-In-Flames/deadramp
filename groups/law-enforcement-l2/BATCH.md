# Final GAPS batch — Group 34: Law Enforcement L2 (2 forks)

**Unit.** The 6 open entries of GAPS.md section "Group 34 — Law
Enforcement L2 (2 forks)" (inventory idx 347–352; the group's
legal-research long tail, itemized in `UNION-SPEC.md` as the
Extended functions). The section's other content is not this
unit's: the category-discipline exclusions and the named
absences are unclaimed by design and stay as recorded; the
platform-layer note was closed in writing under
`PLATFORM-LAYER.md` when the batch opened.

**Method.** Per `gaps-batch/DECISION.md`: extension code lands
as a NEW module in the owning group's `src/`; the founding core
modules stay byte-identical; stubs ship as labeled reference
implementations; if an entry does not fit its drafted
disposition on a close reading of the owning group's spec, the
unit records the corrected disposition here and the parent
closes the entry with the matching token.

**Result.** 4 entries built as records in-substrate, 2 entries
shipped as labeled reference implementations — **the drafted
split held exactly; no re-judgments.** Suite 82 → 110 tests,
all green; all seven founding core modules byte-identical to
the pre-build hashes (re-verified after the build; store.py
still `13c8649d…`); extension records registered: 16 kinds
(corpora, corpus-source links, corpus maintenance records,
corpus license records, validation requests, validation
determinations, headnotes, taxonomy assignments, enrichment
reports, corpus search runs, corpus search outcomes,
assistance requests, assistance outcomes, content deposits,
render records, redaction records). One fresh
mutation-verified negative control (the latest-label seam;
exactly 5 failures under the earliest-record mutation),
recorded in `tests/README.md`.

The group's hard privacy rule binds the new surface unchanged.
Every extension record is keyed by an opaque caller-supplied
`*_ref` string or a core record id and holds metadata and
SHA-256 digests only — no extension method has a parameter
that can accept legal or document content, a headnote's or
query's or note's text, a prompt, or a person's identifier
(passing any such keyword raises `TypeError` before anything
is recorded, pinned by
`tests/test_gaps_batch.py::TestPrivacyShapePins`), and every
record's exact key set is pinned. The category-discipline
exclusions (surveillance, facial recognition, predictive
policing, real-time intelligence feeds) are untouched: not
gaps for this unit, not built, not attributed.

## Per-entry dispositions

| # | Entry (verbatim) | Drafted | Final | Token |
|---|---|---|---|---|
| 1 | The legal corpora themselves (primary / secondary law content databases and practical-guidance content: content, editorial maintenance, licensing) | build-extension | built | `built` |
| 2 | Citation-validation engines (editorial systems that determine treatment; the core records a caller-supplied treatment and determines none) | build-extension | built | `built` |
| 3 | Editorial enhancement systems (headnotes, taxonomy assignment, enrichment pipelines) | build-extension | built | `built` |
| 4 | Corpus search & relevance engines (full-text indexing / ranking over the legal corpus; the core searches registry metadata only) | stub-engine | reference (as drafted) | `reference` |
| 5 | AI/ML research assistance (0 claims in these descriptions; named for union completeness) | stub-engine | reference (as drafted) | `reference` |
| 6 | Document content storage, rendering & redaction (the registry holds metadata + checksums only, by the privacy rule) | build-extension | built | `built` |

## What was built (per entry)

1. **The legal corpora themselves — built as the corpus
   registry surface.** Corpus registration records (`cor-`: an
   opaque corpus ref and a coverage label recorded verbatim),
   corpus-source link records (`csl-`: a registered corpus
   bound to a core source record in the same matter — a
   cross-matter source is refused), editorial-maintenance
   event records (`cmn-`: the event label verbatim as
   reported), and license records (`lic-`: the license label
   verbatim). The entry names three aspects — content,
   editorial maintenance, licensing — and the records form
   covers the two that are records: maintenance and licensing,
   plus the collection registry itself. The content databases
   are the vendors' product and are never held here: the
   privacy rule admits no content in any field shape, and
   every record carries `content_held: False`. The corpus view
   derives linked-source / maintenance / license counts and
   the latest maintenance label at read; the stored corpus
   record carries no counts.
2. **Citation-validation engines — built as the validation
   request registry.** Validation request records (`val-`,
   optionally bound to a core source record in the matter) and
   determination records (`vdt-`: the treatment stored
   **verbatim** as reported by whatever external editorial
   system the embedding organization uses, plus an optional
   verbatim engine label). The entry's own text states the
   boundary — the core records a caller-supplied treatment and
   determines none — and the extension keeps it: no treatment
   is determined, normalized, or scored here
   (`determined_here: False` on every record, the core's
   citation discipline extended with a request lifecycle).
   Recording a determination is pinned to create no core
   citation check. The view derives the determination count
   and latest reported treatment at read.
3. **Editorial enhancement systems — built as enhancement
   records over registered sources.** Headnote records
   (`hed-`: the headnote named by its SHA-256 digest only —
   the core's annotation discipline; the text is never held),
   taxonomy assignment records (`txa-`: the class label
   verbatim as reported; `assigned_here: False`), and
   enrichment stage report records (`enr-`: stage and outcome
   labels verbatim; `enriched_here: False`). The enhancement
   view derives per-kind counts and the latest reported class
   label at read.
4. **Corpus search & relevance engines — labeled reference
   implementation, as drafted.** Full-text indexing and
   ranking run over the legal corpus, which this substrate
   never holds; there is nothing in-substrate to index. Search
   run records (`csr-`: the query named by its SHA-256 digest
   only — there is no parameter that could accept query text,
   exactly as the core's saved-search records name theirs —
   plus an optional verbatim engine label) and reported
   outcome records (`cso-`: outcome label verbatim, optional
   reported result count, validated as a non-negative integer
   with booleans and floats rejected). Every record carries
   `reference_stub: True`, `searched_here: False`, and
   `ranked_here: False`. The view derives the outcome count
   and latest outcome at read.
5. **AI/ML research assistance — labeled reference
   implementation, as drafted.** Assistance is a running
   model's work, and the entry carries 0 claims in these
   descriptions — it is named for union completeness, and its
   substance is the models, not a registry (the ground on
   which the batch's other stub-triaged AI entries closed
   `reference`). Request records (`asr-`: an optional verbatim
   model label; the prompt named by an optional SHA-256 digest
   only — `prompt=` raises `TypeError`) and reported outcome
   records (`aso-`: the result named by an opaque reference;
   `output_held: False`). Every record carries
   `reference_stub: True` and `inference_here: False`.
6. **Document content storage, rendering & redaction —
   built as content operation records over core documents,**
   under the privacy bound the entry itself states. Content
   deposit records (`dep-`: a core document bound to an opaque
   external storage reference; `stored_here: False` — the
   deposit happened in a store owned elsewhere), render
   records (`ren-`: a verbatim format label; the output named
   by an optional SHA-256 digest; `rendered_here: False`),
   and redaction records (`red-`: the outcome label verbatim;
   the output named by an opaque reference plus an optional
   digest; `redacted_here: False`). No parameter can accept
   document content, and recording an operation is pinned to
   leave the targeted core document record byte-identical —
   the L3 unit's evidence-review form at this tier. The view
   derives per-kind counts and the latest redaction outcome
   at read.

## Access mapping (recorded once)

The core's nine-action set is fixed, so the extension maps its
operations onto it (module docstring): corpus registrations,
corpus-source links, maintenance records, and license records
under `source_write` (source-registry-class records);
validation requests and determinations under `citation_write`
(citation-class records, the verbatim-treatment discipline);
headnotes, taxonomy assignments, and enrichment reports under
`annotation_write` (records attached to registered sources);
corpus search runs / outcomes and assistance requests /
outcomes under `search_write` (research-class records);
content deposits, render records, and redaction records under
`document_write` (document-class registry entries); reads
under `matter_read`; derived views under `report_read`. Both
founding boundaries are enforced on every operation: the role
via the core action set, and matter membership via the core
store (writes additionally require an open matter). Denials —
role or membership — are audited `ext_<action>:denied` on the
core audit log; successful mutations are audited
`ext_<action>` with the record kind.

## Not covered by this unit (explicit)

- The legal corpora's content, the citation-validation
  engines' determinations, the editorial systems' headnote
  text and taxonomy assignment work, corpus indexing /
  ranking, model inference, document content storage,
  rendering, and redaction are the vendors' engines and
  content operations, not records; this unit builds the
  records and labels the boundary on every record.
- The category-discipline exclusions — surveillance, facial
  recognition, predictive policing, real-time intelligence
  feeds — are unclaimed-by-design in this category. They are
  not gaps, nothing in this unit builds them, and nothing
  here attributes them to either fork.
- The named absences (incident / case management, evidence
  management & chain of custody, criminal records / RMS,
  investigative case files) stay as recorded in the union
  spec: unclaimed, not built, not gaps — neither sibling is
  an operational law-enforcement platform.
- The extension surface is in-process only, like the sibling
  units': the founding HTTP service layer is unchanged and
  does not expose extension operations.
