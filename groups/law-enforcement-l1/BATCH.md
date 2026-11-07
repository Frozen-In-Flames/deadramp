# Final GAPS batch — Singleton 47: Law Enforcement L1 (1 fork)

**Unit.** The 5 open entries of GAPS.md section "Singleton 47 —
Law Enforcement L1 (1 fork)" (inventory idx 448–452; the fork's
own engines, itemized in `UNION-SPEC.md` from the Flock Safety
Platform description's own verbs). The section's other content
is not this unit's: the Group 34 category union's extended
families are registered under Group 34's section and are not
re-registered here; the standing category exclusions
(surveillance, facial recognition, predictive policing,
real-time intelligence feeds) are zero-claim discipline, not
gaps — of these, only surveillance-class function is asserted
by this fork's prose (as the engines below); the other three
appear nowhere in its description and are not attributed to
it; the platform-layer note was closed in writing under
`PLATFORM-LAYER.md` when the batch opened.

**Method.** Per `gaps-batch/DECISION.md`: extension code lands
as a NEW module in the owning group's `src/`; the founding core
modules stay byte-identical; stubs ship as labeled reference
implementations; if an entry does not fit its drafted
disposition on a close reading of the owning group's spec, the
unit records the corrected disposition here and the parent
closes the entry with the matching token.

**Result.** 2 entries built as records in-substrate, 3 entries
shipped as labeled reference implementations — **one
re-judgment** (idx 448, license plate recognition, drafted
build-extension, re-judged to reference; grounds below). Suite
82 → 110 tests, all green; all seven founding core modules
byte-identical to the pre-build hashes (re-verified after the
build; store.py still `7e2bcade…`); extension records
registered: 12 kinds (LPR jobs, LPR outcomes, audio jobs,
audio outcomes, capture jobs, capture outcomes, device
registrations, device statuses, collaboration shares, share
receipts, analysis records, analysis findings). One fresh
mutation-verified negative control (the latest-label seam;
exactly 7 failures under the earliest-record mutation),
recorded in `tests/README.md`.

The group's hard privacy rule — at this singleton its strictest
statement — binds the new surface unchanged. Every extension
record is keyed by an opaque caller-supplied `*_ref` string or
a core record id and holds metadata and SHA-256 digests only —
no extension method has a parameter that can accept plate
text, a vehicle identifier, audio, video, an image, a
transcript, evidence content, or a person's identifier
(passing any such keyword raises `TypeError` before anything
is recorded, pinned by
`tests/test_gaps_batch.py::TestPrivacyShapePins`), every
record's exact key set is pinned, and a recursive scan pins
that no key anywhere on the surface is score-shaped: nothing
here scores, rates, ranks, or predicts. The attribution
discipline stands: capabilities are recorded only as the
fork's own listing states them.

## Per-entry dispositions

| # | Entry (verbatim) | Drafted | Final | Token |
|---|---|---|---|---|
| 1 | License plate recognition engine & camera network (plate reads, vehicle matching) | build-extension | **re-judged: labeled reference implementation** | `reference` |
| 2 | Audio recognition sensors & detection | stub-engine | reference (as drafted) | `reference` |
| 3 | Video management & evidence-capture pipeline (the substrate captures nothing and stores no content) | stub-engine | reference (as drafted) | `reference` |
| 4 | Camera / sensor hardware (the manufactured devices themselves) | build-extension | built | `built` |
| 5 | Public-safety collaboration & crime-analysis platform (the inter-agency layer beyond the devices) | build-extension | built | `built` |

## What was built (per entry)

1. **License plate recognition engine & camera network (plate
   reads, vehicle matching) — re-judged to a labeled reference
   implementation.** Grounds: the entry's substance is
   recognition and matching against the real world — plate
   reads taken by a camera network and matched against
   vehicles. Sensing and recognition against the real world is
   execution, never records: the same ruling this batch
   applied at L3-adjacent, where device unlocking and evidence
   extraction were re-judged `reference` because the capability
   itself is not records, and the standing rule this unit's
   brief states for detection/recognition-shaped entries. A
   records surface that pretended to read plates or match
   vehicles would be an engine in name only. What the
   substrate can honestly hold is the job registry the
   capability's use presupposes: LPR job records (`lpr-`, an
   opaque job reference, an optional verbatim engine label,
   an optional verbatim scope label naming the watch in the
   requester's own words) and reported outcome records
   (`lpo-`, the outcome label verbatim as reported by whatever
   external capability the embedding organization operates,
   the result named by an opaque reference and an optional
   reported count, validated as a non-negative integer with
   booleans and floats rejected). Every record carries
   `reference_stub: True`, `recognized_here: False`,
   `plates_read_here: False`, and `matched_here: False`. No
   plate text and no vehicle identifier exists in any field
   shape — there is no parameter that could accept one
   (signature-pinned). The view derives outcome count and
   latest reported outcome at read.
2. **Audio recognition sensors & detection — labeled
   reference implementation, as drafted.** The entry's
   substance is detection against the real world by the sensor
   layer — execution, not records, exactly as drafted.
   Audio-recognition job records (`aud-`: an opaque job
   reference, the sensor named by an opaque reference only, an
   optional verbatim engine label) and reported outcome
   records (`auo-`: outcome label verbatim, the result named
   by an opaque reference). Every record carries
   `reference_stub: True`, `detected_here: False`, and
   `recognized_here: False`; no audio and no transcript exists
   in any field shape. The view derives outcome count and
   latest outcome at read.
3. **Video management & evidence-capture pipeline (the
   substrate captures nothing and stores no content) —
   labeled reference implementation, as drafted.** The
   pipeline captures, stores, and serves video and audio from
   the camera network: media transport and content storage
   over systems this substrate never holds, and the entry's
   own parenthetical states the bound. Capture job records
   (`cap-`: an opaque job reference, the device named by an
   opaque reference only, an optional verbatim format label)
   and reported outcome records (`cao-`: outcome label
   verbatim; a captured artifact named by its SHA-256 digest
   and byte count under exactly the core document registry's
   discipline — digest and count validation identical, content
   never held). Every record carries `reference_stub: True`
   and `reference_transport: True`, with `captured_here` /
   `stored_here` / `content_held` False. The view derives
   outcome count and latest outcome at read.
4. **Camera / sensor hardware (the manufactured devices
   themselves) — built as the device registry surface.**
   Device registration records (`dev-`: an opaque device
   reference, the caller's kind label recorded verbatim, an
   optional opaque site reference) and reported status records
   (`dst-`: the status label verbatim as reported by whatever
   system operates the device). The entry's own parenthetical
   bounds the claim: the manufactured devices themselves are
   hardware, outside a software build entirely — nothing here
   manufactures, operates, or observes a device
   (`manufactured_here: False` on every registration). What is
   built is the registry the device fleet presupposes, the
   records form of the entry. The current status derives at
   read through the `_latest_label` seam (this unit's fresh
   negative control); the stored registration carries no
   current status and no counts.
5. **Public-safety collaboration & crime-analysis platform
   (the inter-agency layer beyond the devices) — built as
   records, in the tier family's adjudicated forms.** Share
   records (`csh-`) binding an opaque target reference to an
   opaque recipient reference with an optional verbatim scope
   label, and receipt records (`crp-`) holding delivery
   outcomes verbatim as reported — the L3-adjacent unit's
   information-sharing form: every record carries
   `reference_transport: True` and `transmitted_here: False`
   (the share record also `shared_here: False`,
   `content_held: False`); the records describe shares
   effected on systems owned elsewhere. Analysis records
   (`anl-`: an opaque reference, an optional verbatim method
   label, an optional binding to a core document record in the
   same matter) and finding records (`anf-`: an opaque result
   reference plus an optional verbatim reported label). Under
   the tier family's standing rule — findings are records;
   computing is an engine — no pattern is computed here and no
   registry content is read here beyond metadata
   (`analyzed_here: False`, `patterns_computed_here: False`,
   `computed_here: False`); the analysis platform itself is
   the fork's product, and nothing here predicts anything.
   The views derive receipt / finding counts and latest
   reported labels at read, and `extension_report` derives
   deterministic counts over all twelve extension kinds at
   read — the reporting-shaped slice of this entry, computed
   from registry state, never stored, never a score.

## Access mapping (recorded once)

The core's nine-action set is fixed, so the extension maps its
operations onto it (module docstring): LPR jobs / outcomes,
audio jobs / outcomes, capture jobs / outcomes, and analysis
records / findings under `search_write`
(examination/investigation-class records — the Law Enforcement
L3-adjacent unit's precedent); device registrations and status
records under `document_write` (device/evidence-class registry
entries); share records and receipts under `annotation_write`
(records attached to matter objects — the same precedent);
reads under `matter_read`; derived views under `report_read`.
Both founding boundaries are enforced on every operation: the
role via the core action set, and matter membership via the
core store (writes additionally require an open matter).
Denials — role or membership — are audited `ext_<action>:denied`
on the core audit log; successful mutations are audited
`ext_<action>` with the record kind. At this tier the audit
log is the founding plain append-only log: the Moderate/High
apparatus (hash-chained audit, fail-closed audit writes,
logon lockout, the auditor role) is out of scope for a Low/L1
build and is not inherited downward, per the union spec.

## Not covered by this unit (explicit)

- The Group 34 category union's extended families (the legal
  corpora themselves, citation-validation engines, editorial
  enhancement systems, corpus search & relevance engines,
  AI/ML research assistance, document content storage /
  rendering / redaction) stay registered under Group 34's own
  section; they are not this singleton's verticals and are not
  covered here.
- The standing category exclusions — surveillance, facial
  recognition, predictive policing, real-time intelligence
  feeds — are unclaimed-by-design discipline in this category.
  They are not gaps for this unit, nothing in this unit builds
  them, and nothing here attributes them to the fork: of the
  four, only surveillance-class function is asserted by the
  fork's prose, as the engines in entries 1–3, closed as
  labeled reference implementations; facial recognition,
  predictive policing, and intelligence feeds appear nowhere
  in its description.
- The named absences carried from the category union (incident
  / case management, evidence management & chain of custody
  over physical evidence, criminal records / RMS and
  criminal-history data, investigative case files and case
  subjects) stay as recorded in the union spec: unclaimed, not
  built, not gaps. Chain-of-custody in this substrate is
  records-side integrity only, and no entry in this unit
  claims custody over any evidence — the capture surface
  (entry 3) registers reported captures by digest and never
  holds the captured material.
- Real plate recognition, real audio detection, real video
  capture / storage / serving, real device operation, real
  inter-agency transport, and real crime-pattern computation
  are engines, hardware, and operations, not records; this
  unit builds the records and labels the boundary on every
  record.
- The extension surface is in-process only, like the sibling
  units': the founding HTTP service layer is unchanged and
  does not expose extension operations.
