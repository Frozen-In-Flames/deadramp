# Final GAPS batch — second unit: Remainder Addition — CMS L2

Unit: the 1 OPEN entry of the GAPS.md section
**`## Remainder Addition — CMS L2 (+1 fork)`** (the +1 fork is
Iron Mountain / Iron Mountain InSight, FR2031155471, added to
this group by the remainder census; its spec sheet's ADDENDUM
§5 registered this gap). Built 2026-11-08 under
`gaps-batch/DECISION.md` (the 2026-11-07 ratified triage) and
`PLATFORM-LAYER.md`. Entry count verified against both sources
before building: GAPS.md's section lists exactly 1 `- [] open`
entry and `gaps-batch/inventory.json` assigns exactly idx 660
to this section — **no discrepancy**.

All extension code is one new module,
`src/cms/extensions_addition.py` (`CmsExtensionsAddition`, a
second wrapper around the untouched core store, audit actions
prefixed `exta_`); every existing module — including the first
batch unit's `extensions.py` — is byte-identical (SHA-256
verified against the pre-build record in
`scratch/prebatch-addition-src.sha256`; `store.py` still
`e1d05424…`, `extensions.py` still `ebb3e8d9…`, all 8 of 8
unchanged). No core extension was needed, and none was made.
Tests: `tests/test_gaps_batch_addition.py` (25 tests; suite
143 → 168, all passing).

The group's binding doctrines bind this unit throughout:
**content is never held** (documents are metadata + SHA-256
digests only; no field shape can hold a document body, and the
surface's signatures refuse content — pinned by `TypeError`
tests); status derives at read, never stored; the build
contains no model. The sibling CMS L3-adjacent build
(`groups/cms-l3/BATCH.md`) adjudicated this same fork family's
three engine entries (its idx 394–396) into exactly the form
used here; this unit carries that form at the L2 tier (plain
append-only audit; no High-tier apparatus imported downward).

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 660 | ML/AI content classification, extraction & enrichment engine: automatically classifying, extracting, and enriching physical and digital content (registered from the fork's described headline function, not from a claim; the records its outputs would write — item metadata, tags, asset registrations — are Core, the engine is Extended) | build-extension | **reference** (re-judged, see below) | Labeled reference records for all three engine functions, every record carrying `reference_stub: True` and its family's not-here flag. **Classification:** job records (`clsjob-`, target named by reference only — a core item or asset reference, which must resolve, or an opaque external reference; content optionally named by a validated SHA-256 digest) and outcome records (`clsout-`) holding the external engine's labels verbatim (`outcome_basis: "engine_reported"`; confidence held only as a verbatim reported *label* — a numeric confidence is rejected, and a recursive scan pins no score-shaped key and no float value anywhere on the surface); `classified_here: False`. **Extraction:** job records (`extjob-`, source by reference as above, requested field labels held as data) and outcome records (`extout-`) holding {field_label, value} pairs verbatim under exact pair-shape validation, deep-copied at the boundary; `extracted_here: False`. **Enrichment:** job records (`enrjob-`) bound to a core item and outcome records (`enrout-`) holding the engine's reported metadata verbatim **on the outcome record only** — never applied to the core item (`applied_here` / `derived_here` / `enriched_here: False`), pinned by a test that the bound item and its revision list are byte-identical after an outcome is recorded. Job views derive outcome counts and the latest reported outcome at read via the `_latest_outcome` seam (stored records carry no latest key, pinned); `engine_summary` derives counts only. Recording any job or outcome creates no core item, asset, tag, or revision. |

## Re-judgments (DECISION.md qualification 1)

**One** (idx 660), build-extension → reference. Grounds: the
entry names a *learned* ML/AI engine, and a learned engine's
substance is inference over content. This substrate holds
registry metadata and checksums only — never content bodies —
so there is nothing here for a classifier, extractor, or
enrichment engine to run over, and no deterministic derivation
over the group's own records constitutes classifying,
extracting from, or enriching content. The entry's own text
bounds it the same way: the records its outputs would write
(item metadata, tags, asset registrations) are Core — and
already stand in the core — while the engine is Extended. The
honest form is the batch's established learned-inference form
(the AI groups at every tier; the sibling CMS L3-adjacent
build's idx 394–396 for this same fork family): job records
naming the subject by reference or digest, plus outcome
records holding the external engine's reports verbatim,
labeled `reference_stub: True` — records *about* the engine's
work, never the engine. Building the same records without the
label and calling the entry built would claim an inference
capability this build does not have. Expected closure
arithmetic for the parent: **1 entry closed — 0 built,
1 reference, token override: idx 660 closes `reference`
against its drafted build-extension triage.**

## Negative control

Fresh, for this surface: the latest-outcome seam
(`CmsExtensionsAddition._latest_outcome`). The canonical rule:
every "latest reported" derivation on this surface — a
classification job's latest labels, an extraction job's latest
fields, an enrichment job's latest metadata — is the *last*
outcome recorded for the job. The in-suite three-leg control
in `test_gaps_batch_addition.py`
(`TestLatestOutcomeNegativeControl`): canonical views over
two-outcome histories read the second outcome everywhere
(labels `["new"]`, field value `"new"`, metadata `{"s":
"new"}`); an earliest-reading mutant subclass reads the first
everywhere; treating the mutant's reading as the canonical
expectation raises `AssertionError`. Live drill performed
2026-11-08 (recorded in `tests/README.md`, log in
`scratch/gaps_batch_addition_mutation_run.txt`): patching the
seam's return line from `return outcomes[-1] if outcomes else
None` to `return outcomes[0] if outcomes else None`
(occurrence count asserted = 1 before patching) produced
exactly **4 failures** out of 168 — the control's canonical
leg plus the three job-view tests that pin latest derivations
(classification, extraction, enrichment) — with all 143
pre-existing tests still passing; the module was restored from
`scratch/extensions_addition.py.premutation`, SHA-256 verified
(`c5b23220…`), and the suite re-run green (168 tests, OK).

## What is NOT covered (named, not closed silently)

- **No classification, extraction, or enrichment is
  performed.** No model exists in this build; no content is
  read, inferred over, or transformed. The records are the
  labeled reference form of an external engine's requests and
  reported outcomes.
- **No reported outcome is applied.** Enrichment metadata is
  never written to a core item, classification labels never
  become item tags, and extraction fields never become item
  metadata on this surface; caller-supplied metadata reaches
  items only through the core's own authoring functions.
- **PLATFORM-LAYER.md decisions 1–6 are untouched** by this
  unit: no identity provider, no validated cryptography, no
  retention enforcement, no session layer, and no hosting or
  multi-tenancy claim was built or implied. The fork's own
  SaaS hosting posture stays the fork's (ADDENDUM §2 recorded
  it tags no hosting family and gains no claimant here).
