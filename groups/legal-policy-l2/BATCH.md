# Final GAPS batch — Remainder Addition, Legal & Policy L2 (+6 forks)

Date: 2026-11-07. This unit's section of `../../GAPS.md` listed
10 open entries (inventory idx 561–570) — the gap functions the
six remainder forks (CDS Federal Cloud, Deloitte EMS, DocuSign
IAM eSignature, DocuSign CLM, IDGC, RelativityOne Government)
registered in `ADDENDUM.md` §5. All 10 are closed by this unit
under the decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`.

What landed: one new module, `src/legalpol/extensions.py`
(`LegalPolExtensions`, wrapping the core `LegalPolStore`; all
seven core modules byte-identical, SHA-256 verified — store.py
still `7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`,
the shipped hash), and `tests/test_gaps_batch.py` (37 tests).
Full suite: **106 → 143 tests**, all passing.

The founding privacy rule binds every shape built here: documents
exist in this substrate ONLY as metadata + SHA-256 records in the
core document registry. No extension shape has a field for
document content, extracted text, a summary or redaction output,
a signature value, or query text — pinned by exact key-set
assertions per record type, by `TypeError` on any content-shaped
keyword argument, and by a recursive forbidden-key scan over the
whole extension surface. Matters, custodians, reviewers,
requesters, counterparties, and signers are opaque references.
Extension writes map to the core `document_write` RBAC action
(the surface is records over the document/matter substrate);
reads resolve the agency through the core store, so the
membership boundary binds every operation. Nothing is scored.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 561 | eDiscovery processing & collection engine (CDS, Deloitte EMS, IDGC) | built | Matter records (`mat-`; opaque matter ref in a core workspace, `content_collected_here: False`) + collection records (`col-`; source label, document/byte counts stored as reported; `content_collected_here`/`processing_performed_here: False`) + collection–document link records (`clk-`) over core document refs + processing-run records (`prc-`, counts as reported). `collection_view` derives linked-document and run counts at read; the stored record carries neither. Nothing is collected or processed here. |
| 562 | eDiscovery document review platform, incl. hosted review ecosystems (CDS, Deloitte EMS, IDGC, RelativityOne) | built | Review assignment records (`rva-`; core document ref + opaque reviewer ref; `content_reviewed_here: False`) + decision records (`rvd-`; determination label recorded verbatim from a fixed vocabulary). `assignment_view` derives decision count and latest label at read. Pinned behaviorally: recording decisions leaves the core document record byte-identical — the review happens on the reviewer's own system; only its outcome lands here. |
| 563 | eDiscovery production, disposition & archiving engine (Deloitte EMS, IDGC) | built | Production records (`prd-`; counts as reported, `production_executed_here: False`) + production–document links (`plk-`). Disposition as DECISION records (`dsp-`; `executed_here: False`): `disposition_view` derives eligibility at read from recorded states (active holds covering the document, decisions already recorded; `method: derived_from_recorded_states`), and the decision write refuses while an active hold covers the document. The disposition itself is executed by the embedding organization's records schedule, never here (PLATFORM-LAYER.md decision 4). |
| 564 | Legal hold & preservation management (Deloitte EMS, IDGC) | built | Hold records (`hld-`; opaque custodian ref; `preserved_here: False`) + append-only reported state records (`hst-`; reported_issued / reported_acknowledged / reported_released) + coverage records (`hcv-`) over core document refs. Current state is derived at read by the single seam `_current_hold_label` (latest recorded label) and never stored; `hold_view` derives current state, activeness, and coverage. Preservation is performed by the custodian's systems, never here. This seam is the batch's fresh negative control (below). |
| 565 | AI document analysis for discovery: summarization / classification / redaction, assisted review, analytics & visualizations (Deloitte EMS, IDGC, RelativityOne, CDS) | built | Analysis-request records (`anr-`; core document ref + kind from the entry's own five verbs; `inference_here: False`) + result records (`anl-`) holding the reported output as an **opaque result reference** plus an optional verbatim reported label. No summary, classification, or redaction text field exists in any shape — pinned by exact key sets and `TypeError` on `summary=`/`redaction_text=` kwargs. Analytics & visualizations close as `discovery_analytics`: a deterministic counts derivation over the matter's held records (`method: deterministic_counts`), counts and label tallies only. |
| 566 | OCR & document extraction engine (Deloitte EMS) | built | Extraction-job records (`ocr-`; core document ref, page/field counts stored as reported, opaque result reference; `extracted_here: False`). No extracted-text field exists in any shape — pinned by exact key set and `TypeError` on `extracted_text=`. Nothing is extracted here. |
| 567 | FOIA & disclosure release engine (Deloitte EMS) | built | FOIA case records (`foi-`; the request and the requester are opaque references — no request text exists in any shape; `released_here: False`) + append-only reported state records (`fos-`) with current state derived at read + exemption determination records (`fxd-`; exemption label recorded verbatim) + release records (`frl-`; counts as reported, `released_here: False`). `foia_case_view` derives current state and counts. Nothing is released here. |
| 568 | Electronic signature engine: ceremony, binding / validity, envelope & transaction workflow (DocuSign) | reference | Labeled reference records: envelopes (`env-`; optional core agreement/document ref; `reference_stub: True`, state `recorded_reference_only`, `signed_here: False`) + ceremony event records (`sgn-`; opaque signer ref, reported ceremony label verbatim; `reference_stub: True`, `signed_here: False`). No shape has a field that could hold a signature value — the field does not exist (pinned by exact key sets and `TypeError` on `signature=`). Nothing is signed and no binding or validity is effected here. |
| 569 | Contract lifecycle management engine (DocuSign CLM) | built | Agreement records (`agr-`; opaque counterparty ref, optional value held as integer cents — booleans/floats/negatives rejected whole; `executed_here: False`) + append-only reported lifecycle state records (`ags-`). `agreement_view` derives the current state (latest recorded label) at read; the stored record carries no state key. No agreement is executed here. |
| 570 | Agreement workflow automation engine (DocuSign) | reference | Labeled reference records: workflow definitions (`wfd-`) held as DATA (an ordered list of step labels; `reference_stub: True`, state `recorded_reference_only`, `executed_here: False`). Per the house registry-never-executes doctrine, a definition is never run — pinned behaviorally: registering a definition leaves an agreement record byte-identical. |

Closure tokens: 8 entries close as `built` (561, 562, 563, 564,
565, 566, 567, 569) and 2 as `reference` (568, 570).

## Re-judgments

None. Every build-extension entry was carried in the records
form described above under the founding privacy rule, and both
stub-engine entries shipped as their drafted labeled reference
implementations. Two calls nearest the line are stated plainly
rather than re-judged:

- **Legal hold (564)** was decided Extended by the additions pass
  (`ADDENDUM.md` §4) on the ground that its substance is platform
  workflow; the batch brief's disposition for it is
  build-extension, and the records form above is what the
  substrate honestly carries — hold records, reported states,
  and coverage over document references, with preservation
  itself explicitly not performed here (`preserved_here: False`
  on every record). The workflow substance (notice issuance,
  acknowledgment chasing) is not built and not claimed.
- **Disposition (563)** closes as decision records with derived
  eligibility, not as disposition execution: the build destroys,
  archives, and retains nothing, per PLATFORM-LAYER.md decision
  4 (retention enforcement is the embedding organization's
  records schedule at the deployment layer).

## Negative control

Fresh, for the new code: the hold current-state derivation
(`LegalPolExtensions._current_hold_label` — latest recorded
label wins). In-suite three-leg control in
`tests/test_gaps_batch.py` (`TestHoldDerivationNegativeControl`,
mutant subclass reads the earliest label; the mutant flips the
hold view, disposition eligibility, and the analytics
active-hold count), plus a live drill on the real file: the seam
was patched to `return states[0]["state_label"]`, the full suite
ran **143 tests with exactly 5 not passing** (3 failures + 2
errors — the errors are the canonical arms where the
post-release disposition decision unexpectedly raises; the
failing set is exactly the hold-derivation-dependent set), then
the file was restored from `scratch/extensions.py.premutation`
and verified SHA-256 identical (`e3a267ce…`); suite green
again. Full record in `tests/README.md`.

## Core integrity

No core module was modified: `src/legalpol/*.py` SHA-256 sums
match the pre-build baseline exactly (store.py `7030f9fd…`, the
shipped hash). The extension is store-level only (no HTTP
routes), matching the sibling batch units' pattern — the core
`service.py` is byte-identical and untouched. No era rescope was
needed: the additions-era pins (7 spec sheets, the zero-claim
table) are untouched and still pass as written.
