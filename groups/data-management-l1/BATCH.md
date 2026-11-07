# Final GAPS batch — Singleton 38, Data Management L1

Unit: the 5 entries in GAPS.md under "Singleton 38 — Data
Management L1 (1 fork)" (3 `build-extension`, 2 `stub-engine` in
`../../gaps-batch/inventory.json`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07), with **one
re-judgment** (web page rendering for capture, grounds below).
The section's closing prose paragraph (the Group 12 category
union's extended families, already registered under Groups 12 and
28 and not re-registered here; and the platform-layer lines —
encryption at rest, TLS-when-configured, multi-tenancy, demo
identities / IA-2) is not part of the 5 entries: the families
belong to those units, and the platform lines stand closed by
`../../PLATFORM-LAYER.md`. Neither is absorbed by this unit. The
"Remainder Addition — Data Management L1 (+1 fork)" section
(DevResults) is a different unit and is untouched.

All extension code is in one new module,
`src/datamgmt/extensions.py` (`DataMgmtExtensions`, wrapping the
core `DataMgmtStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified against the pre-build
baseline recorded in `scratch/gaps_batch_src_hashes_before.txt`;
`store.py` still `dc35677c…`, the shipped hash). Full suite: 207
tests before, **239 tests after, OK** (32 new in
`tests/test_gaps_batch.py`), including the fresh mutation-verified
negative control recorded in `tests/README.md`.

This group's baseline is the Low baseline / FAR 52.204-21 (the
fork is LI-SaaS). The sibling batch units' forms (Group 12 at
Moderate, Group 28 at High) were followed family-shape by
family-shape where the shapes correspond, but nothing of the
siblings' baseline apparatus is imported: no 800-171 depth, no
hash-chained audit, no lockout, no auditor role exists at this
tier, and none was added. The extension enforces through this
group's own three-role matrix (admin / steward / viewer).

Cross-cutting, per the group's doctrines: RBAC is enforced through
the core `datamgmt.access` matrix — the extension maps each
operation onto an existing core action (the core action set is
fixed) and checks it before any state change or id allocation;
denied attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`; all sites, systems, and requesters are opaque
`*_ref` strings, and no record shape can hold page content, a
record payload, or an identifier value (`content_held: False`
rides on every archive-facing record); derived values (the archive
summary's counts and totals, the content-index summary's latest
reported figure) are computed at read and never stored. Records
hold metadata and checksums, never the data itself — the founding
discipline, applied to the fork's own verticals.

## Re-judgment (DECISION.md qualification 1)

**Web page rendering for capture (dynamic / JS pages)** — drafted
`build-extension`; **re-judged to a labeled reference
implementation** (closure token `reference`).

Grounds, on a close reading of the owning group's spec:

1. Rendering a dynamic/JavaScript page is execution over external
   content: a renderer fetches the page and runs its scripts so
   the snapshot reflects what a visitor sees. This build holds
   registry metadata and records — there is no renderer in it and
   no captured content for one to render. `UNION-SPEC.md`'s
   core-boundary decision names the page renderer explicitly
   among the engines not carried ("the crawler, the page
   renderer, the change detector, the archive store and its
   replay"), and the spec's honesty section repeats it. A method
   that reported a page rendered without rendering it would be a
   false claim, not an extension.
2. Category precedent at both sibling tiers: the analogous
   processing over content — the content processing engines (OCR,
   transcription, categorization) — shipped as labeled reference
   implementations in the Group 12 and Group 28 batch units, on
   the same reasoning (jobs and outputs are records; the
   processing is the engine's, not the build's).
3. What honestly lands in-substrate is the definition and report
   layer: render **profile** definitions held as data (mode,
   wait label) and render **report** records storing the
   renderer's outcome verbatim as reported. Every record carries
   `reference_stub: True` and `rendered_here: False`.

Why the two drafted `build-extension` companions were **not**
re-judged: their records forms bind to, and derive from, the
core's own records — a capture binds a crawl target to a core
ingestion record and takes its counts and checksum from there,
and a seal states the core ingestion's checksum, read at seal
time. That is the same ground on which the sibling units closed
their storage-volume and record-linkage entries `built`: the
records/derivation form genuinely lands, with the engine's
absence stated on the record. Rendering has no such binding —
there is no core record a render could derive from — so it
follows the processing precedent instead. The two drafted
`stub-engine` entries (change detection; full-content search &
indexing) stand as drafted, for the reasons in their rows below.

## Per-entry dispositions

| Entry (GAPS.md text, verbatim) | Disposition | Built (module: `datamgmt/extensions.py`) |
|---|---|---|
| Web crawling & snapshot capture engine (the product's central function; the substrate records ingestions and captures nothing) | built | `define_crawl_target` (`cwt-`, an archive dataset + opaque `site_ref` + optional core source + schedule held as a label; `captured_here: False`), `record_capture` (`cap-`, binds the target to exactly one core ingestion of the same dataset — cross-dataset and duplicate bindings rejected; the capture holds no counts or checksum of its own, those live on the core record), `archive_summary` — target/capture/seal counts derived at read, joined with the core provenance total over completed ingestions. Definitions and records about capture, matching the entry's own bound: the substrate records ingestions and captures nothing |
| Web page rendering for capture (dynamic / JS pages) | **reference (re-judged from build-extension — grounds above)** | `define_render_profile` (`rpf-`, mode enum static / dynamic_javascript / dynamic_javascript_settled, wait label as data), `record_render_report` (`rrp-`, outcome stored verbatim as the renderer's report, optional reported page count) — every record carries `reference_stub: True` and `rendered_here: False` |
| Change detection & dynamic monitoring engine | reference (stub-engine, as drafted) | `define_monitor` (`mon-`, over a crawl target, cadence as a label), `record_change_report` (`chg-`, outcome enum stored verbatim as reported, optional reported page count) — `reference_stub: True`, `monitored_here: False`, `detected_here: False` throughout. Detection is a comparison over snapshot content the substrate does not hold; nothing here fetches or compares |
| Archive storage, integrity sealing & replay / playback of captured pages (the substrate holds registry metadata only) | built | `seal_capture` (`asl-`, carries the checksum of the capture's core ingestion record, read from the core at seal time — `None` when the core recorded none, stated as held; `sealed_here: False`, `content_held: False`; one seal per capture) under the new separation-of-duties seam `_check_sealer_not_recorder` — the sealer may never be the actor who recorded the capture, mirroring the core's signature `_check_decider_not_requester`; the seam is the batch's fresh negative control. `record_replay_request` (`rpl-`, opaque `requester_ref` + purpose) carries `reference_transport: True` and `replayed_here: False` — a request record, never a playback. `archive_summary` counts seals derived at read |
| Full-content search & indexing over the archive (core search is registry-metadata only) | reference (stub-engine, as drafted) | `define_content_index` (`cix-`, name + scope label), `record_index_snapshot` (`isn-`, reported document count and optional checksum stored verbatim as reported), `content_index_summary` — snapshot count and latest reported figure derived at read — `reference_stub: True`, `indexed_here: False`, `searched_here: False`, `content_held: False` throughout. A test pins that the core's metadata search still runs and that the extension exposes no content-search method |

## Named as NOT covered by this unit

- **The section's platform-layer lines** (encryption at rest,
  TLS-when-configured, multi-tenancy, demo identities / IA-2) —
  not among the 5 entries; they stand on `PLATFORM-LAYER.md`.
- **The Group 12 category union's extended families** (distributed
  storage, integration runtime, record linkage, search indexing,
  content processing, workflow, query / visualization, hosting,
  case depth, AI/ML, field-level lineage, retention disposition
  execution) — registered under Groups 12 and 28 per the section's
  own note, closed by those units, not re-registered or closed
  here.
- **The Remainder Addition — Data Management L1 section**
  (DevResults: M&E / results-management platform functions;
  data-capture tooling & collection instruments) — a separate
  unit in the same registry, untouched by this one.
- **Capture, rendering, detection, sealing, replay, indexing, and
  search themselves** — the engines. This unit builds their
  records layer only, and every record carries that bound on its
  face.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
