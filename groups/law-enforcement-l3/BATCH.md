# Final GAPS batch — Group 35: Law Enforcement L3-adjacent (2 forks)

**Unit.** The 8 open entries of GAPS.md section "Group 35 — Law
Enforcement L3-adjacent (2 forks)" (inventory idx 360–367; this
group's own forensic verticals, itemized in `UNION-SPEC.md`
from verbatim evidence sentences in the two forks' own
descriptions). The section's other content is not this unit's:
the carried Group 34 legal-research long tail is registered
under Group 34's section; the five High platform gaps in this
section (IA-2(1)/(2)/IA-5, SC-13, SC-28, AU-11, AC-11/AC-12)
were closed `re-scoped` in writing under `PLATFORM-LAYER.md`
when the batch opened.

**Method.** Per `gaps-batch/DECISION.md`: extension code lands
as a NEW module in the owning group's `src/`; the founding core
modules stay byte-identical; stubs ship as labeled reference
implementations; if an entry does not fit its drafted
disposition on a close reading of the owning group's spec, the
unit records the corrected disposition here and the parent
closes the entry with the matching token.

**Result.** 6 entries built as records in-substrate, 2 entries
re-judged to labeled reference implementations. Suite 110 → 156
tests, all green; all seven founding core modules byte-identical
to the pre-build hashes (re-verified after the build; store.py
still `18070d55…`); extension records registered: 15 kinds
(unlock requests, unlock outcomes, extraction requests,
extraction outcomes, analysis records, analysis findings,
ingest batches, ingest artifacts, processing reports, evidence
reviews, artifact registrations, custody transfers, share
records, share receipts, forensic reports). One fresh
mutation-verified negative control (the current-holder seam;
exactly 2 failures under the first-transfer mutation),
recorded in `tests/README.md`.

The group's hard privacy rule and category discipline bind the
new surface unchanged. Every extension record is keyed by an
opaque caller-supplied `*_ref` string or a core record id and
holds metadata and SHA-256 digests only — no extension method
has a parameter that can accept evidence content, a finding's
or report's text, a credential or bypass value, or a person's
identifier (passing any such keyword raises `TypeError` before
anything is recorded, pinned by
`tests/test_gaps_batch.py::TestPrivacyShapePins`), and every
record's exact key set is pinned. The category-discipline
exclusions (surveillance, facial recognition, predictive
policing, real-time intelligence feeds) are untouched: not
gaps for this unit, not built, not attributed.

High apparatus binds the new surface: extension mutations are
audited on the core hash-chained audit log **audit-before-commit**
— the audit entry is written before the record commits, so a
failed audit write (`AuditWriteError`) commits nothing and
consumes no id (pinned by `TestFailClosedExtension`) — and the
auditor role, holding only `audit_read`, maps to no core action
any extension operation uses and is denied every extension
operation, read and write (pinned by
`TestAccessAndBoundaries`).

## Per-entry dispositions

| # | Entry (verbatim) | Drafted | Final | Token |
|---|---|---|---|---|
| 1 | Device unlocking (Cellebrite) | build-extension | **re-judged: labeled reference implementation** | `reference` |
| 2 | Evidence extraction from mobile devices (Cellebrite) | build-extension | **re-judged: labeled reference implementation** | `reference` |
| 3 | Forensic analysis engines (both siblings) | build-extension | built | `built` |
| 4 | Evidence ingest & processing pipelines (Magnet One) | build-extension | built | `built` |
| 5 | Evidence review (Magnet One) | build-extension | built | `built` |
| 6 | Chain-of-custody enforcement over evidence (Cellebrite; the substrate's checksums / verify-by-content / hash chain are records-side analogues, stated as analogues, not equivalents) | build-extension | built (custody transfer records; enforcement not claimed) | `built` |
| 7 | Information sharing / collaboration over evidence (both siblings) | build-extension | built | `built` |
| 8 | Forensic reporting (Cellebrite; beyond the substrate's counts-only registry reporting) | build-extension | built | `built` |

## What was built (per entry)

1. **Device unlocking (Cellebrite) — re-judged to a labeled
   reference implementation.** Grounds: the entry's substance
   is a capability that defeats a device's access controls.
   Per this unit's brief, such a capability is not built in
   any form — there is nothing records-shaped about the
   unlocking itself, and a records surface that pretended to
   the function would be a runtime in name only. What the
   substrate can honestly hold is the request registry the
   capability's use presupposes: unlock request records
   (`unl-`, an opaque request ref and an opaque device ref)
   and unlock outcome records (`uno-`, the outcome label
   recorded verbatim as reported by whatever external
   capability the embedding organization operates). Every
   record carries `reference_stub: True`,
   `unlocked_here: False`, and `capability_held_here: False`;
   no parameter can accept a credential, a bypass code, or
   device data (signature-pinned). The view derives outcome
   count and latest outcome at read.
2. **Evidence extraction from mobile devices (Cellebrite) —
   re-judged to a labeled reference implementation.** Grounds:
   the same as entry 1 — extraction is the capability that
   pulls data off a device past its access controls; the
   capability itself is not records, and it is not built.
   Extraction request records (`exr-`) and outcome records
   (`exo-`) mirror entry 1's surface with
   `extracted_here: False` and `capability_held_here: False`.
   The artifacts an extraction produces are registered where
   artifacts belong: the ingest surface (entry 4) and the core
   document registry, as metadata + SHA-256.
3. **Forensic analysis engines (both siblings) — built.**
   Analysis records (`ana-`: an opaque ref, an optional method
   label recorded verbatim, an optional binding to a core
   document record) and finding records (`anf-`: an opaque
   result reference plus an optional verbatim reported label).
   No finding is computed and nothing is analyzed here
   (`analyzed_here: False`, `findings_computed_here: False`,
   `computed_here: False`, `content_held: False`); there is no
   parameter that could accept a finding's text. The view
   derives the finding count at read; the stored record
   carries no count.
4. **Evidence ingest & processing pipelines (Magnet One) —
   built.** Ingest batch records (`ing-`), artifact records
   (`ina-`) holding an artifact's SHA-256 digest and byte
   count under exactly the core document registry's discipline
   (content never held; digest and count validation identical;
   `artifact_ref` unique within its batch), and
   processing-stage report records (`inp-`: stage and outcome
   labels recorded verbatim as reported). Nothing is ingested
   or processed here (`ingested_here: False`,
   `processed_here: False`). The batch view derives artifact
   count, total recorded bytes (a sum over recorded values),
   and report count at read.
5. **Evidence review (Magnet One) — built.** Review records
   (`evr-`) targeting a core document record or an ingest
   artifact record in the same matter, with the outcome label
   recorded verbatim as reported. Nothing is rendered and no
   content is held (`rendered_here: False`,
   `content_held: False`): the review workspace is the fork's
   product; this surface is its record.
6. **Chain-of-custody enforcement over evidence (Cellebrite;
   the substrate's checksums / verify-by-content / hash chain
   are records-side analogues, stated as analogues, not
   equivalents) — built, as custody records.** Artifact
   registrations (`art-`: opaque ref, SHA-256, byte count, and
   the holder at registration as reported) and custody
   transfer records (`cus-`: from/to holder references,
   both opaque, recorded as reported). This is a custody
   **ledger**, not custody enforcement:
   `custody_enforced_here: False` on every record, and the
   entry's own analogue caveat is carried verbatim — the
   substrate's checksums, verify-by-content, and hash chain
   are records-side analogues of enforcement, not equivalents.
   `verify_artifact` mirrors the core's verify-by-content over
   artifact registrations (hashes caller-supplied bytes,
   compares, stores nothing, enforces nothing). The current
   holder derives at read through the `_current_holder` seam
   (the batch's fresh negative control); the stored
   registration carries no current holder.
7. **Information sharing / collaboration over evidence (both
   siblings) — built, in the Communication adjudicated form.**
   Share records (`shr-`) binding a target — a core document
   record, an artifact registration, or a custody transfer
   record in the same matter — to an opaque recipient
   reference, and receipt records (`shp-`) holding delivery
   outcomes verbatim as reported. Every record carries
   `reference_transport: True` and `transmitted_here: False`
   (the share record also `shared_here: False`,
   `content_held: False`): the records describe shares
   effected on systems owned elsewhere. Recording a share is
   pinned to leave the targeted core document byte-identical.
   The view derives receipt count and latest outcome at read.
8. **Forensic reporting (Cellebrite; beyond the substrate's
   counts-only registry reporting) — built.** Forensic report
   registrations (`frp-`: metadata plus an optional report
   SHA-256; reports are generated on the forks' platforms
   elsewhere — `generated_here: False`, `content_held:
   False`). The report view derives the matter's
   forensic-registry counts at read over the extension
   surface's own records (artifact registrations, custody
   transfers, ingest batches and artifacts, analysis records,
   evidence reviews, share records) — the "beyond registry
   reporting" slice the entry names, and the figures provably
   track registry state because they are computed from it at
   read; the stored report record carries no figures.

## Access mapping (recorded once)

The core's nine-action set is fixed, so the extension maps its
operations onto it (module docstring): artifact registrations,
custody transfers, ingest batches / artifacts / processing
reports, and forensic reports under `document_write`
(evidence/document-class registry entries); unlock and
extraction requests and outcomes, and analysis records and
findings, under `search_write` (examination/investigation-class
records — the Law Enforcement untiered unit's precedent);
evidence reviews and share records / receipts under
`annotation_write` (records attached to matter objects — the
same precedent); reads under `matter_read`; derived views under
`report_read`. No extension operation maps to `audit_read`, so
the auditor role is denied all of them. Both founding
boundaries are enforced on every operation: the role via the
core action set, and matter membership via the core store
(writes additionally require an open matter). Denials — role or
membership — are audited `ext_<action>:denied` on the core
audit log; successful mutations are audited `ext_<action>` with
the record kind, written before the record commits.

## Not covered by this unit (explicit)

- The carried Group 34 legal-research long tail (the legal
  corpora themselves, citation-validation engines, editorial
  enhancement systems, corpus search & relevance engines,
  AI/ML research assistance, document content storage /
  rendering / redaction) stays registered under Group 34's own
  section; it is not this group's verticals and is not covered
  here.
- The TRAPWIRE remainder addition's own verticals stay
  registered under the "Remainder Addition — Law Enforcement
  L3-adjacent" section (a separate batch unit).
- The category-discipline exclusions — surveillance, facial
  recognition, predictive policing, real-time intelligence
  feeds — are unclaimed-by-design in this category. They are
  not gaps, nothing in this unit builds them, and nothing here
  attributes them to any fork.
- Real device unlocking, real extraction, real forensic
  analysis, real evidence processing, real review rendering,
  custody enforcement over physical or digital evidence, real
  information transport, and real report generation are
  engines and operations, not records; this unit builds the
  records and labels the boundary on every record.
- The extension surface is in-process only, like the Law
  Enforcement untiered unit's: the founding HTTP service layer
  is unchanged and does not expose extension operations.
