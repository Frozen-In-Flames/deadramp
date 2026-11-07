# Final GAPS batch — Singleton 39, Content Management System (CMS) L3-adjacent

Batch note for the five open entries of the repo-root `GAPS.md`
section "Singleton 39 — CMS L3-adjacent (1 fork)", closed under
the ratified triage in `gaps-batch/DECISION.md`. This is the
project's thinnest-evidence group: the sole fork's description is
a single sentence and tags 0 claims under Group 20's taxonomy
applied verbatim; the 12-function core stands on the explicit
core-boundary decision recorded in `UNION-SPEC.md` (the Merge
Rule carries the L2 union upward whole). The five entries are
the fork's own engines, named from its description's own verbs.
The founding discipline binds throughout: the substrate is
records machinery — a content registry holding metadata and
checksums only, never content bodies — and nothing in this batch
renders, serves, indexes, hosts, executes, or learns.

## What was added

- `src/cms/extensions.py` (one new module): `CmsExtensions`, a
  records register wrapping the core `CmsStore`. In-memory
  collections with the founding conventions — validation before
  mutation (failed operations consume no id), founding-permission
  RBAC with denials audited in the core audit log under a
  `:denied` suffix, opaque references only, derived-never-stored
  views, counts-only rollups. RBAC reuses the founding action
  vocabulary (no new actions); the action mapping is documented
  in the module docstring. High-baseline posture binds the
  surface: extension mutations write to the core's hash-chained
  audit log **audit-first** — the audit entry is recorded before
  the extension record commits, so an audit write failure raises
  `AuditWriteError`, leaves no record, and consumes no id
  (AU-5/AU-9); the `auditor` role is denied every extension read
  and write while its core audit duty (log read, chain verify)
  works unchanged (AC-5).
- `tests/test_gaps_batch.py`: 30 tests pinning the extension
  surface entry by entry, including the stub labels, the exact
  intake-record key set, the recursive no-score key scan, the
  fail-closed audit test, and the batch's fresh negative control
  (below).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the pre-build baseline before and after the build:
`store.py` still `19b4f504…`, all 7 of 7 unchanged). No core
change was needed, and none was made. Suite: **146 tests
before → 176 tests after, OK**.

## Per-entry disposition

**Build-extension (1)** — closed by its in-substrate records
form: records plus deterministic derivations over this group's
own core registry.

1. **Physical-content intake & digitization pipeline
   (scanning / conversion of physical records into the
   platform)** (idx 397) — physical-intake records
   (`register_physical_intake`): an opaque source reference, a
   form label, a page count stored exactly as reported
   (floats/booleans rejected at the boundary, no id consumed),
   an optional condition label — metadata *about* physical
   records; the records themselves are never held
   (`content_held: False`; the stored record's exact key set is
   pinned by test and contains no stage field). Pipeline stage
   events (`record_digitization_step`) are recorded verbatim;
   the current stage is derived at read time by the seam
   `_current_intake_stage` and stored nowhere. Digitization
   outcomes (`record_digitization_outcome`) bind an intake to
   the core asset registration that is its digitized surrogate
   — registration stays the core's own function and the asset
   record holds metadata + checksum, as everywhere in this
   substrate; an unknown asset is rejected and a second outcome
   is refused. `digitization_summary` derives counts (intakes,
   digitized, by derived current stage) at read time. **The
   bound, stated plainly:** scanning, conversion, and OCR are
   physical/engine acts and are not performed here
   (`scanned_here: False`, `converted_here: False` on the
   intake and on the outcome). What is built is the
   intake-and-pipeline records layer — the same records form
   the CMS L2 unit adjudicated for bulk ingestion — not the
   digitization machinery. The disposition stays
   build-extension on that stated scope.

**Stub-engine (4)** — each closed as a labeled reference
implementation: records only, never execution, each carrying
`reference_stub: True` and its family's not-here flag.

2. **Learned ML / AI classification engine (automatically
   classify physical and digital content)** (idx 394) —
   **re-judged** (see Re-judgments). Classification job records
   (`register_classification_job`): the target named by
   reference only — a core item or asset reference, which must
   resolve (an unknown target is rejected with no id
   consumed), or an opaque external reference — with the
   content optionally named by a validated SHA-256 digest; no
   content parameter exists on the surface (pinned by a
   `TypeError` test). Outcome records
   (`record_classification_outcome`) hold the external
   engine's reported labels verbatim, with any confidence held
   as a verbatim reported *label* — a numeric confidence is
   rejected, and a recursive key scan pins that no score-shaped
   key exists anywhere on the surface. Job views derive
   outcome counts and latest reported labels at read.
   Registering jobs and outcomes is pinned to leave the bound
   core item byte-identical.
3. **Learned ML / AI extraction engine (extract content / data
   from physical and digital content)** (idx 395) —
   **re-judged** (see Re-judgments). Extraction job records
   (`register_extraction_job`) name the source by reference
   (core asset/item, resolving, or opaque external) with the
   requested field labels held as data. Outcome records
   (`record_extraction_outcome`) hold {field_label, value}
   pairs verbatim as reported, under an exact pair-shape
   validation; outcome fields are deep-copied at the boundary
   (pinned: mutating the caller's list changes nothing stored).
4. **Learned ML / AI enrichment engine (enrich content with
   derived metadata; the substrate stores caller-supplied
   metadata only and derives none)** (idx 396) —
   **re-judged** (see Re-judgments). Enrichment job records
   (`register_enrichment_job`) bind a core item. Outcome
   records (`record_enrichment_outcome`) hold the external
   engine's reported key/value metadata verbatim **on the
   outcome record only**: it is never applied to the core item
   (`applied_here: False`, `derived_here: False`) — pinned by
   a test that the core item's metadata and revision count are
   unchanged after an outcome is recorded. Caller-supplied
   metadata reaches items only through the core's own
   authoring functions, exactly as the entry's registered text
   states.
5. **The content services platform runtime itself (hosting /
   delivery of the SaaS platform)** (idx 398) — platform
   runtime reference records
   (`register_platform_runtime_reference`;
   `hosted_here: False`, `delivered_here: False`,
   `reference_transport: True`) with the fork's substrate
   label recorded verbatim as the fork's own. Per
   PLATFORM-LAYER.md decision 6, hosting/delivery of the SaaS
   platform is a deployment property and does not transfer to
   the build — the form every CMS sibling's hosting entry
   took.

## Re-judgments

**Three** (idx 394, 395, 396), each build-extension →
reference, under DECISION.md qualification 1. Grounds, recorded
per the qualification: the three entries name *learned* ML/AI
engines, and a learned engine's substance is inference over
content. This substrate holds registry metadata and checksums
only — never content bodies — so there is nothing here for a
classifier, extractor, or enrichment engine to run over, and no
deterministic derivation over the group's own records
constitutes classifying, extracting from, or enriching content.
The enrichment entry's own registered text states the bound:
"the substrate stores caller-supplied metadata only and derives
none." The honest form is therefore the batch's established
learned-inference form (the AI groups at every tier, DevTools
untiered's AI code-generation, Finance L2's AI/ML document
processing): job records naming the subject by reference or
digest, plus outcome records holding the external engine's
reports verbatim, labeled `reference_stub: True` — records
*about* the engines' work, never the engines. Building the same
records without the label and calling the entries built would
claim an inference capability this build does not have.

Idx 397 and idx 398 landed at their drafted dispositions (the
digitization bound — pipeline records built, scanning/conversion
not performed — is stated in its disposition above; it is the
build-extension form the unit's brief specifies for this entry,
not a corrected disposition).

## Negative control (fresh, for the new code)

The intake current-stage seam
`CmsExtensions._current_intake_stage` is the load-bearing
derivation for the digitization entry: an intake's current
stage is the label of its *latest* recorded stage event,
derived at read and stored nowhere. `tests/test_gaps_batch.py`
carries the in-suite control in three-legged form (canonical /
earliest-reading mutant subclass / mutant-as-expectation
fails), and the live drill was performed on the real module:
the seam's return patched from `steps[-1]["label"]` to
`steps[0]["label"]` (occurrence count asserted = 1 before
patching) made **exactly 2 of 176 tests fail**
(`TestDigitizationPipeline.test_stage_derived_at_read_never_stored`
and
`TestIntakeStageNegativeControl.test_canonical_current_stage_is_latest`);
the module was restored from `scratch/extensions.py.premutation`
and verified SHA-256 identical (`404d2dd3…`), suite re-ran
green. Full record in `tests/README.md`; raw mutated run in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / unchanged

- `specs/specs.json`, the core service layer, and the REST API
  are untouched — the extension surface is store-level only,
  following the sibling batch units' pattern.
- The section's baseline-gap paragraph in GAPS.md (MFA /
  authenticator management, FIPS-validated cryptography,
  encryption at rest, audit retention enforcement, session
  lock / termination) and its platform-layer note stand on
  PLATFORM-LAYER.md and were not absorbed by any entry here;
  none of the five entries in this unit is a platform-layer
  entry.
- The Group 20 category union's extended families remain
  registered under Groups 20 and 24 and were not re-registered
  or touched by this unit; the CMS L2 remainder addition's
  registered gap (a different section) is likewise untouched.
