# Final GAPS batch — second unit: Remainder Addition — Development Tools L2

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Development Tools L2 (+4 forks)`**
(the +4 forks are Cloud.gov, Copado GovCloud, Federal GovCloud
(FGC) DevSecOps, and Unqork for Government, added to this group
by the remainder census; their spec sheets' ADDENDUM §5
registered these gaps). Dispositions follow
`../../gaps-batch/DECISION.md`; platform-layer closures follow
`../../PLATFORM-LAYER.md`.

**Entry-count note:** the brief's count verifies exactly. GAPS.md's
section lists exactly 2 `- [ ] open` entries, and
`gaps-batch/inventory.json` assigns exactly idx 578 and 579 to
this section (578 build-extension, 579 stub-engine — 1 build /
1 stub). The first unit's BATCH.md independently names these
same two entries as this unit's scope. No discrepancy.

Everything landed as ONE new module,
`src/devtools/extensions_addition.py`
(`DevToolsExtensionsAddition`, wrapping the core
`DevToolsStore`), with audit actions prefixed `exta_`. All 8
pre-existing modules — the 7 inherited core modules and the
founding `extensions.py` from this group's first batch unit —
are byte-identical (SHA-256 verified against the pre-build
record in `scratch/prebatch-addition-src.sha256`; `store.py`
still `36b04bd5…`, `extensions.py` still `a3b7598b…`). No core
extension was needed and none was made. Tests:
`tests/test_gaps_batch_addition.py` (23 tests). Suite:
**121 → 144, all passing.** Python standard library only
(`scratch/verify_deps.py` re-run: OK).

Doctrines carried from the core and the first unit, unchanged:
opaque `*_ref` strings only; derived-never-stored (the
application view, the document-generation view, and the
addition summary are computed at call time and stored nowhere);
validation fully before mutation, so a failed operation
consumes no id and changes nothing; append-only audit including
denied attempts; RBAC via the core `access` module. RBAC
mapping for this unit: application definitions, revisions,
publications, and the application view ride the build family
(`build_write` / `build_read`); document-generation reference
and outcome records ride `project_write` / `project_read`, the
founding mapping for stub reference records; the addition
summary rides `project_read`.

## Per-entry disposition

### idx 578 — built (build-extension, as drafted)

> No-code / low-code application development platform: visual application builder & runtime (Unqork)

Built in the definitions-as-data form this category's grammar
uses for builder surfaces. `define_application` (`app-`, bound
to a core project) holds an application definition whose
components are inert data — each an opaque `component_ref`
under a recorded kind label (`page` / `form` / `workflow` /
`data_model` / `integration` / `custom`), refs unique within
the definition, the list deep-copied at the boundary so caller
mutation cannot reach the record. `revise_application`
replaces the components and increments the definition's
`revision`. `record_application_publication` (`apu-`) records
a publication outcome as reported by the external platform:
status from the recorded vocabulary (`reported_published` /
`reported_failed` / `reported_unpublished`), a snapshot of the
definition revision it reports against, the built application
named only by an optional opaque `application_ref`, and an
optional binding to a core environment record.
`application_view` derives the current reported state at read
(revision, component count, publication count, latest
reported status via the `_latest_label` seam); the stored
definition record carries no count and no status field
(pinned by test).

The boundary is stated on every record: `definition_only:
True`, `built_here: False`, `run_here: False`,
`executed_here: False`, `rendered_here: False` on definitions;
`built_here` / `run_here` / `executed_here: False` on
publications. The visual builder surface that produces
definitions and the runtime that would execute them are not
built — exactly the bound the group's own ADDENDUM (gap 16)
records for this entry: "no application is built or run
anywhere in this build." Grounds for closing built rather
than re-judging to reference: the definition layer is a
genuine records object in this substrate (versioned data over
the group's own project records), and definitions-as-data
plus reported outcomes is this group's founding built form
(pipeline definitions + reported runs, idx 303; release plans
+ reported stages, idx 316) and the form three sibling units
built for this same substance — Operations Management L2
(application definition records, `built_here: False` /
`deployed_here: False`, deployment outcomes as records),
CMS untiered idx 889 (application and form definition
records, `executed_here: False` / `rendered_here: False`),
and GRC L3 idx 425 (no-code configuration definitions as
versioned data, same two labels). The CRM L3 unit closed its
no-code entry reference on its own substrate's invariant
(configuration text stored verbatim, never executed); this
substrate's definitions are likewise never executed — the
difference is the token each group's grammar assigns to the
definition layer, and this group's grammar, stated above,
assigns built. The generation/runtime half is not built
under either token and is labeled absent here on every
record's face.

### idx 579 — reference (stub-engine, as drafted)

> Compliance documentation & SSP generation tooling (Cloud.gov; distinct from assessment automation: this is documentation generation)

Ships as a labeled reference implementation.
`record_document_generation_reference` (`dgr-`, bound to a
core project) names the target document, the framework /
control-documentation source, and the system by opaque
reference only (`document_ref`, `framework_ref`, `system_ref`);
`record_document_generation_outcome` (`dgo-`) stores a status
label verbatim as reported by the external tooling, with the
generated document named only by an optional opaque
`output_ref`. `document_generation_view` derives the outcome
count and the latest reported outcome label at read (via the
`_latest_label` seam); the stored reference record carries
neither. Every record carries `reference_stub: True` and
status `recorded_reference_only`, with `generated_here:
False` and `document_held_here: False`: no document content
is accepted or held anywhere on this surface, and nothing is
generated.

Why the reference form and not the GRC built form: the GRC
groups built package generation as deterministic manifest
assembly (GRC untiered) / a manifest view derived at read
(GRC L2 idx 359) because the GRC substrate itself holds the
records a package is assembled from — controls, evidence
with checksums, findings, assessments for a governed system.
This substrate holds no control documentation and no
compliance records of any kind, so there is nothing
in-substrate from which an SSP could honestly be assembled
or a manifest derived; a view here would be a derivation over
nothing. The reference form is the honest closure, as
drafted. The entry's own distinction is preserved on the
record: this is documentation generation, kept separate from
the assessment-automation reference the first unit recorded
at idx 307 (a different record kind, a different entry).

## Re-judgments

None. Both entries closed at their drafted dispositions: idx
578 built in the definitions-as-data form (grounds above),
idx 579 reference as drafted (grounds above).

## Fresh negative control

**The earliest-reading latest-label seam.**
`DevToolsExtensionsAddition._latest_label` is the single seam
through which both views derive current reported state: the
current state of an application or a document generation is
the *last* record reported for it. The in-suite control
(`LatestLabelNegativeControlTests`) shares the record tables
with a subclass whose seam reads the earliest record: the
canonical implementation reports the latest publication
status (`reported_failed` after `reported_published` then
`reported_failed`); the mutant reports the superseded
`reported_published`; and treating the mutant's outcome as
the canonical expectation raises `AssertionError` literally.

**Mutation drill (performed at build time).** The real
`extensions_addition.py` was mutated so `_latest_label`
returns `records[0][key]` instead of `records[-1][key]`
(occurrence count asserted = 1 before replacing), and the
full suite was run: **144 ran, exactly 3 failures** —

- `test_gaps_batch_addition.ApplicationPublicationTests.test_application_view_derives_and_stores_nothing`
- `test_gaps_batch_addition.DocumentGenerationReferenceTests.test_view_derives_latest_outcome_and_stores_nothing`
- `test_gaps_batch_addition.LatestLabelNegativeControlTests.test_canonical_latest_publication_status`

All three failures sit on the latest-label surface and
nothing else trips, which is the specificity the drill exists
to prove. The file was restored from
`scratch/extensions_addition.py.premutation` and verified
SHA-256-identical to its pre-drill hash (`416819c1…`); the
suite re-ran green at 144. Raw drill output:
`scratch/gaps_addition_mutation_run.txt`. Recorded in
`tests/README.md`.

## Verification (builder-side)

- Full suite: 121 tests before, **144 tests after, OK**
  (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Mutation drill: earliest-reading `_latest_label` mutant →
  exactly 3 failures (above); restored SHA-256-verified;
  suite re-run green.
- Core byte-identity: all 8 pre-existing `src/devtools/`
  modules re-hashed after the build; identical to the
  pre-build record (`sha256sum -c
  scratch/prebatch-addition-src.sha256`: all OK).
- Dependency check: `scratch/verify_deps.py` re-run — stdlib
  only, no third-party imports (the new module adds no import
  beyond `copy`, `threading`, `datetime`).
- Live smoke (in-process): application defined → revised
  (revision 2, view component count 3) → two publications
  recorded against a core environment → view derives latest
  status `reported_failed`; document-generation reference →
  two outcomes → view derives latest label `final_generated`;
  viewer write denied (`PermissionDenied`) and audited; all
  five `exta_` audit actions present. SMOKE OK.
- Tree state: exactly the 5 intended paths (new module, new
  test module, this note, and append-only notes in the group
  `README.md` and `tests/README.md`); drill backups in the
  group's gitignored `scratch/`; new-module `__pycache__`
  cleaned; no tracked `.pyc` churn. Nothing committed;
  repo-root GAPS.md and README.md untouched.
