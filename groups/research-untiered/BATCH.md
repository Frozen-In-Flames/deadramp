# Final GAPS batch — Untiered Set 9, Research (tier null)

Date: 2026-11-07. This set's section of `../../GAPS.md` listed 11
open entries (inventory idx 828–838); all 11 are closed by this
unit under the decisions in `../../gaps-batch/DECISION.md`
(ratified 2026-11-07) and `../../PLATFORM-LAYER.md`. The set
stays untiered throughout: tier null, no baseline asserted, no
CMMC equivalence drawn anywhere — the batch tests scan the whole
extension surface for any tier- or baseline-shaped key and find
none.

What landed: one new module, `src/research/extensions.py`
(`ResearchExtensions`, wrapping the core `ResearchStore`; all
seven core modules byte-identical, SHA-256 verified against the
shipped accounting in this group's README), and
`tests/test_gaps_batch.py` (39 tests). Full suite: **93 → 132
tests**, all passing.

The founding privacy discipline binds every shape built here:
records carry metadata and opaque caller-supplied references
only. Subjects, trial participants, and investigated persons are
opaque references; no shape has a field for a captured clinical
value, a consent signature, eCOA response content, an identifier,
or background-check content — pinned by exact key-set assertions
per record type and by `TypeError` on any unexpected keyword
argument. Nothing is scored or ranked anywhere, as in the core.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 828 | Market & policy intelligence platform | built | Intelligence item records (`int-`; kinds directory_entry/legislation/hearing/policy_item) holding a topic reference, a verbatim source label, and an opaque detail reference to content held elsewhere; `gathered_here: False` on every record. `intelligence_summary` derives counts by kind at read (`deterministic_counts`). Nothing is gathered here. |
| 829 | Contract award & subaward analysis | built | Award records (`awd-`; integer cents as data, floats/bools/strings rejected whole; award_ref unique per commons; a subaward must name a prime in the same commons, a prime may not name a parent, subawards may not parent). `award_analysis` is a deterministic sums/counts derivation over the held records (`deterministic_sums`); `funds_moved_here: False` — no award is scored or ranked and no funds move. |
| 830 | Entity / relationship-graph analytics | built | Entity records (`ent-`; opaque refs, ref unique per commons) and directed relationship records (`rel-`; verbatim label; self-loops and exact duplicate edges refused). `entity_view` derives in/out/total degree at read (the stored record carries no degree key); `relationship_counts` and `list_neighbors` are deterministic counts over recorded edges; `inference_here: False` — no inference is drawn from the graph. |
| 831 | Saved-search, alerting & entity-tracking | reference | Labeled reference records (`sst-`, `trk-`): `reference_stub: True`, state `recorded_reference_only`, `executed_here: False`, `alerts_sent_here: False`, `tracking_active_here: False`. A saved search is an opaque search reference + scope label; nothing executes, alerts, or tracks. |
| 832 | Clinical-trial EDC (electronic data capture) | built | Capture-form definition records (`frm-`): fields are opaque field REFERENCES held as data (duplicates refused); `field_count` derived at read in `form_view`, never stored. Submission records (`sub-`): site ref, optional opaque subject ref, counts (`fields_reported`, `queries_reported`; negatives/floats rejected) and a recorded status label only. `captured_values_held_here: False` on both shapes — no parameter of any method can accept a captured value. |
| 833 | eConsent & eCOA | built | Consent instrument records (`cin-`; instrument ref + version label; `signature_possible_here: False`, `consent_effected_here: False`) and append-only consent state records (`cns-`; state label from the reported-* vocabulary, stored verbatim per opaque participant ref; `signature_held_here: False`). Current state is derived at read by the single seam `_current_consent_label` (latest recorded label) and never stored. eCOA: outcome instrument definitions (`oin-`) + response records (`ors-`) carrying a COUNT only (`response_content_held_here: False`). No signature bytes can exist in any shape; no consent is legally effected here — consent is a recorded state, not an act performed by this build. |
| 834 | Clinical-trial reporting & analytics | built | `clinical_summary`: a deterministic counts derivation over the EDC/eConsent/eCOA records held in the commons — submissions by recorded status, fields/queries reported totals, consent current states (derived per participant through the same seam), outcome response totals; `method: deterministic_counts`. No trial result is interpreted and nothing is scored. |
| 835 | Identity resolution & background investigation | built | Per the Data Management units' PPRL precedent: linkage pair records (`lnk-`) between two distinct opaque references with a reported-method label (reported_token_match / reported_key_match / reported_manual_review) and a source label; `match_computed_here: False`, `identity_verified_here: False` — the match was computed elsewhere and is recorded as reported; no identifier is ever accepted as input (references are opaque caller tokens). Investigation case records (`inv-`; opaque subject ref, event-driven opened/closed state) + finding records (`inf-`) holding labels verbatim as reported; `searched_here: False`, `verified_here: False` throughout — nothing is searched or verified here. `linkage_counts` derives pair counts by method. |
| 836 | Ongoing identity monitoring | reference | Labeled reference records (`mon-`): `reference_stub: True`, state `recorded_reference_only`, `monitoring_active_here: False`, `alerts_sent_here: False`. No source is watched and no alert is sent. |
| 837 | Supplier discovery & market research | reference | Labeled reference records (`dis-`): `reference_stub: True`, state `recorded_reference_only`, `discovery_performed_here: False`, `searched_here: False`. An inquiry is recorded; no supplier is searched for, discovered, or contacted. |
| 838 | Supplier intelligence & capabilities data | built | Supplier profile records (`sup-`; opaque supplier ref unique per commons, capability labels recorded verbatim with duplicates collapsed, source label; `evaluated_here: False`). `supplier_capability_counts` derives profile counts per recorded label; `suppliers_with_capability` is a recorded-label lookup (`recorded_label_lookup`) — the suppliers were recorded, never discovered or evaluated here. |

Closure tokens: 8 entries close as `built` (828, 829, 830, 832,
833, 834, 835, 838) and 3 as `reference` (831, 836, 837).

## Re-judgments

None. Every build-extension entry was carried in the records
form described above under the founding no-subject-data
discipline, and every stub-engine entry shipped as its drafted
labeled reference implementation. The two entries nearest the
line are stated plainly rather than re-judged:

- **Identity resolution (835)** is built in the PPRL records
  form, not as a resolution engine: pairs are recorded *as
  reported* by an external process and the build computes no
  match. That is the disposition the Data Management units
  adjudicated for the same family, applied here unchanged.
- **eConsent (833)** is built as consent *state records*, not
  as a consent ceremony: no signature is captured (none can
  exist in the shape) and no consent is legally effected by
  recording a state label. The record is the substrate a consent
  process's outcomes land in.

## Negative control

Fresh, for the new code: the consent current-state derivation
(`ResearchExtensions._current_consent_label` — latest recorded
label wins). In-suite three-leg control in
`tests/test_gaps_batch.py`
(`TestConsentDerivationNegativeControl`, mutant subclass reads
the earliest label), plus a live drill on the real file: the
seam was patched to `return history[0]["state_label"]`, the full
suite ran **132 tests with exactly 4 failures** (the
derivation-dependent set: the EDC/eCOA current-state test, the
clinical summary test, and the control's two canonical arms —
the mutant-agreement tests pass under both by construction),
then the file was restored from
`scratch/extensions.py.premutation` and verified SHA-256
identical (`965e5f3f…`); suite green again. Full record in
`tests/README.md`.

## Core integrity

No core module was modified: `src/research/*.py` SHA-256 sums
match the shipped accounting in this group's README exactly
(store.py `ff43a9ac…`). The extension is store-level only (no
HTTP routes), matching the sibling batch units' pattern — the
core `service.py` is byte-identical and untouched.
