# Final GAPS batch — Singleton 49, Legal & Policy L2 (1 fork, new category)

Date: 2026-11-07. This unit's section of `../../GAPS.md` listed
9 entries (inventory idx 485–493) — the Extended functions the
founding fork (VulcanGov / Justinian for Government) registered
in `UNION-SPEC.md`. Two were already closed `re-scoped` in
writing under `../../PLATFORM-LAYER.md` before this unit (idx
491 identity provider / federation service; idx 493
FIPS-validated cryptography) and are untouched here. The 7 OPEN
entries (idx 485–490, 492) are closed by this unit under the
decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`.

This is the second GAPS-batch unit in this directory. The first
(the remainder additions' section, idx 561–570) took
`BATCH.md`, `src/legalpol/extensions.py`, and
`tests/test_gaps_batch.py`; this unit therefore lands as
`BATCH-SINGLETON49.md` (this file),
`src/legalpol/singleton_extensions.py`, and
`tests/test_gaps_batch_singleton.py`, and modifies neither of
the first unit's files.

What landed: one new module, `src/legalpol/singleton_extensions.py`
(`LegalPolSingletonExtensions`, wrapping the core
`LegalPolStore`; all seven core modules byte-identical,
SHA-256 verified — store.py still
`7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`,
the shipped hash; the additions unit's `extensions.py` is also
byte-identical, still `e3a267ce…`), and
`tests/test_gaps_batch_singleton.py` (33 tests). Full suite:
**143 → 176 tests**, all passing.

The founding privacy rule binds every shape built here: the
legal corpus and documents exist in this substrate ONLY as
metadata + SHA-256 records in the core library and document
registries. No shape in this module has a field for corpus
content, document content, generated text, a prompt, a model
completion, or query text — pinned by exact key-set assertions
per record type, by `TypeError` on any content-shaped keyword
argument, and by a recursive forbidden-key scan over the whole
new surface. Sessions, executions, searches, documents, library
sources, licensors, and endpoints are opaque references or
verbatim labels. Extension writes map to the core
`document_write` RBAC action, except corpus writes, which map
to `library_write` because the corpus hangs off the platform
library; agency-scoped reads resolve the agency through the
core store, so the membership boundary binds every operation,
and corpus reads are open to any actor exactly as core library
reads are. Nothing is scored.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 485 | AI agent runtime (LLM inference, agent orchestration, grounding / retrieval, model transport bridge) | reference | Labeled reference records: agent-run requests (`arr-`; core workspace + session refs, optional task label; `reference_stub: True`, state `recorded_reference_only`, `inference_here`/`orchestrated_here`/`retrieved_here: False`) + reported outcome records (`aro-`; the reported output held as an **opaque result reference** plus an optional verbatim reported label — no completion text field exists; `prompt=`/`completion=` kwargs raise `TypeError`) + model transport bridge definitions (`mbr-`; `reference_stub: True`, `reference_transport: True`, `transported_here: False`). `agent_run_view` derives outcome count and latest reported label at read. No inference runs, nothing is orchestrated, retrieved, or transported here. |
| 486 | Legal corpus content (the statutes / regulations / guidance / datasets themselves, curation and update pipeline, licensing) | built | Content REGISTRY records over core library sources (`cor-`; reported item count stored as reported + optional corpus SHA-256 digest — a record *about* the content, never the content; `content_held_here`/`curated_here`/`licensed_here: False`) + append-only reported curation event records (`cev-`; labels from the entry's own pipeline verbs: reported_added / reported_updated / reported_withdrawn / reported_recatalogued) + license records (`lic-`; opaque licensor ref, license label verbatim; `licensed_here: False`). `corpus_content_view` derives the current curation state at read by the single seam `_current_curation_label` (latest recorded label) plus `is_withdrawn`; the stored record carries neither. `corpus_summary` is a deterministic counts derivation over the platform library (`method: deterministic_counts`). Curation and licensing themselves are performed by the corpus's own pipeline and licensors, never here. This seam is the batch's fresh negative control (below). |
| 487 | Full-text & semantic search engines (indexing, vector / semantic ranking over the corpus; saved searches are digest records in Core) | reference | Labeled reference records: engine definitions (`sen-`; kind full_text / semantic / hybrid; `reference_stub: True`, state `recorded_reference_only`, `indexed_here`/`ranked_here`/`searched_here: False`) + reported run records (`srn-`; bound to the definition and optionally to a core saved search, result count stored as reported; `searched_here`/`ranked_here: False`). The core's digest-only discipline carries unchanged: no method has a parameter that could accept query text, and a smuggled `query_text=` kwarg raises `TypeError` (pinned). Nothing is indexed, ranked, or searched here. |
| 488 | Sandbox runtime (the isolated single-use execution environment itself; executions are recorded, never performed) | built | Provisioning-request records (`sbp-`) over core sandbox sessions — a non-sandbox session is refused whole — + append-only reported outcome records (`sbo-`; reported_provisioned / reported_failed / reported_torn_down). `sandbox_runtime_view` derives the outcome count and latest label at read and reads the core session's own derived flags (`sandbox_consumed`, lifecycle status) through the core at read — the core's single-use rule is untouched and carries unchanged (pinned: the view's `sandbox_consumed` flips only when the core records the session's one execution). The environment itself — isolation, resource limits, teardown — is never provisioned here: `provisioned_here`/`runtime_here: False` on every record. |
| 489 | Code execution engine | built | Execution-job records (`ejb-`) bound to CORE execution records (the job names the core execution it reports on and carries its kind) + append-only reported outcome records (`ejo-`; outcome label verbatim from a fixed vocabulary; exit code stored as reported — an integer, booleans/floats rejected, negatives accepted because an exit code is a reported value, not a count). `execution_job_view` derives outcome count, latest label, and latest reported exit code at read. Execution itself is performed by the external engine, never here: `executed_here: False` on every record. |
| 490 | Document generation engine (drafting / generation from corpus and session context) | reference | Labeled reference records: generation requests (`gnr-`; core workspace ref + optional core session ref + optional purpose label; `reference_stub: True`, state `recorded_reference_only`, `generated_here`/`drafted_here: False`) + reported output records (`gno-`) holding the output as a **core document reference** in the request's workspace (the core registry's metadata + checksum record; an output document from another workspace is refused as not found; duplicate output links rejected). No generated-text field exists in any shape — pinned by exact key sets and `TypeError` on `document_text=`. Nothing is drafted or generated here; per the brief, generation is a model's work and document text cannot be held in this substrate. |
| 492 | Security monitoring & platform security services (deployment-platform layer) | reference | Labeled reference records: monitoring feed definitions (`mfd-`; `reference_stub: True`, `reference_transport: True`, state `recorded_reference_only`, `monitored_here`/`scanned_here: False`) + reported observation records (`mfo-`; observation and severity labels recorded verbatim; `monitored_here: False`). `monitoring_feed_view` derives the observation count and counts by reported severity label at read. An observation changes no core record. Monitoring, scanning, and the platform security services themselves are the deployment platform's layer (the entry's own bound, and PLATFORM-LAYER.md's posture), never performed here. |

Closure tokens: 3 entries close as `built` (486, 488, 489) and
4 as `reference` (485, 487, 490, 492).

## Re-judgments

None. Every entry lands at its drafted disposition: the three
build-extension entries (486, 488, 489) were carried in the
records form above under the founding privacy rule, and the
four stub-engine entries (485, 487, 490, 492) shipped as their
drafted labeled reference implementations. Three calls nearest
the line are stated plainly rather than re-judged:

- **Legal corpus content (486)** closes `built` as a content
  registry — records of the corpus's reported extent, digests,
  curation events, and licenses over the core library's source
  records. The content itself is not, and under the founding
  privacy rule cannot be, held here (`content_held_here: False`
  on every record); what is built is the registry the entry's
  curation and licensing pipeline runs over, in the same sense
  the additions unit built legal holds as records while
  preservation stayed with the custodian's systems.
- **Sandbox runtime (488)** closes `built` as provisioning
  records over the core's sandbox sessions. The entry's own
  text bounds it ("executions are recorded, never performed");
  the isolation environment itself is not built and not
  claimed (`runtime_here: False`).
- **Code execution engine (489)** closes `built` as job and
  reported-outcome records bound to the core's execution
  records — the in-substrate half of the engine's surface. No
  code is executed here (`executed_here: False`).

## Negative control

Fresh, for the new code: the corpus curation-state derivation
(`LegalPolSingletonExtensions._current_curation_label` — the
latest recorded curation event label wins). In-suite three-leg
control in `tests/test_gaps_batch_singleton.py`
(`TestCurationDerivationNegativeControl`, mutant subclass reads
the earliest label; the mutant flips the derived current state
and the derived `is_withdrawn` flag), plus a live drill on the
real file: the seam was patched to
`return events[0]["event_label"]`, the full suite ran **176
tests with exactly 3 failures** — exactly the
curation-derivation-dependent set — then the file was restored
from `scratch/singleton_extensions.py.premutation` and verified
SHA-256 identical (`73f3259f…`); suite green again. Full record
in `tests/README.md`.

## Core integrity

No core module was modified, and neither was the additions
unit's `extensions.py`: all `src/legalpol/*.py` SHA-256 sums
for pre-existing modules match the pre-build baseline exactly
(store.py `7030f9fd…`, the shipped hash; extensions.py
`e3a267ce…`, the additions unit's shipped hash). The extension
is store-level only (no HTTP routes), matching the sibling
batch units' pattern — the core `service.py` is byte-identical
and untouched. No era rescope was needed: the founding pins
(1 spec sheet, the 11-claim table) and the additions-era pins
(7 spec sheets, the zero-claim table) are untouched and still
pass as written.
