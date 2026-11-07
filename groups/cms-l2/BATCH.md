# Final GAPS batch — Group 20, Content Management System (CMS) L2

Batch note for the ten open entries of the repo-root `GAPS.md`
section "Group 20 — Content Management System (CMS) L2
(4 forks)", closed under the ratified triage in
`gaps-batch/DECISION.md`. The founding discipline binds
throughout: the substrate is records machinery — content items
with append-only revisions, asset records holding metadata and
checksums only, search as literal substring over registry
metadata — and nothing in this batch renders, serves, indexes,
transmits, hosts, executes, or adjudicates.

## What was added

- `src/cms/extensions.py` (one new module): `CmsExtensions`, a
  records register wrapping the core `CmsStore`. In-memory
  collections with the founding conventions — validation before
  mutation (failed operations consume no id), founding-permission
  RBAC with denials audited in the core audit log under a
  `:denied` suffix, opaque references only, derived-never-stored
  views, counts-only rollups. RBAC reuses the founding action
  vocabulary (no new actions); the action mapping is documented
  in the module docstring.
- `tests/test_gaps_batch.py`: 35 tests pinning the extension
  surface entry by entry, including the stub labels, the exact
  case-record key set, and the batch's fresh negative control
  (below).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the pre-build baseline before and after the build:
`store.py` still `e1d05424…`, all 7 of 7 unchanged). No core
change was needed, and none was made. Suite: **108 tests
before → 143 tests after, OK**.

## Per-entry disposition

**Build-extension (5)** — each closed by its in-substrate records
form: records plus deterministic derivations over this group's
own core content registry.

1. **Rendering & templating engines and visual / WYSIWYG
   editors** (idx 194) — template and fragment *definition
   records* (`create_template` / `update_template` /
   `get_template` / `list_templates`). The body is held as data
   and versioned (prior bodies retained in `history`);
   placeholder names are derived at read time by scanning the
   held text and are absent from the stored record (pinned by
   test). Editor *configuration records* (`create_editor_config`
   / `update_editor_config`) hold a mode label and settings as
   data, versioned the same way. Nothing is rendered and
   nothing is served — every record carries
   `rendered_here: False`. A WYSIWYG editor UI is a client
   surface, not a records function; the records form is the
   definition layer such an editor would edit, and that bound
   is stated rather than smoothed over. (The untiered set's
   batch unit adjudicated this same template form at tier null;
   it is mirrored here.)
2. **Bulk ingestion & index-in-place engines** (idx 197) —
   ingestion-batch records (`create_ingestion_batch`): an
   opaque source reference, a document count stored exactly as
   reported, and checksum references — no content is ingested
   or held (`content_held: False`, exact key set pinned).
   Index-in-place closes as index *declaration* records
   (`create_index_declaration`): target reference and field
   list held as data, `indexing_performed_here: False`.
   `ingestion_summary` derives batch/count/checksum totals at
   read time.
3. **Library ILS vertical (circulation, MARC21 cataloging
   depth, EDI acquisitions, discovery layer)** (idx 198) —
   circulation-style loan records over opaque `patron_ref` /
   `item_ref` (`record_loan` / `record_loan_event`): state
   events recorded verbatim, current state derived at read
   time by `_current_loan_state` and absent from the stored
   record (pinned). MARC21 depth closes as cataloging field
   records (`create_catalog_record`): tag/value pairs held as
   data with an exact field shape, never parsed
   (`discovery_engine_here: False`). EDI acquisitions close as
   order records (`create_acquisition_order`) holding an
   integer-cent amount as data — floats and booleans rejected
   at the boundary, no id consumed — never transmitted
   (`transmitted_here: False`). The discovery layer is the
   core's literal substring search over registry metadata,
   unchanged and pinned by test (regex metacharacters are
   literal text; catalog field values are not searched).
   **Boundary, stated plainly:** a dedicated Library Systems
   category exists elsewhere in this repo
   (`groups/library-systems-l1`); this entry closes as THIS
   group's vertical records form over its own substrate and
   imports nothing from that group.
4. **BPM / case-management engine (EEO, labor relations,
   accommodations, background investigations, IG casework)**
   (idx 199) — case records (`open_case` / `record_case_event`
   / `case_view` / `list_cases`) over opaque `case_ref` /
   `subject_ref`, typed by the five named casework kinds plus
   "other". The stored record's exact key set is pinned by
   test — `{id, case_ref, subject_ref, case_type, opened_by,
   created_utc, events}` — and contains no field that could
   hold case content, narrative, or evidence. State events are
   recorded verbatim; current state is derived at read.
   Decisions (`record_case_decision`) are recorded verbatim
   under the separation-of-duties seam
   `_check_decider_not_opener` (the decider is never the
   case's opener; a denied decision is audited and consumes no
   id) and carry `adjudicated_here: False` — EEO/IG casework
   is records only here; nothing is investigated or
   adjudicated.
5. **Personalization / experience optimization** (idx 202) —
   audience segment definitions with match conditions held as
   data (`create_segment`), subject attribute records keyed by
   opaque `subject_ref` (`record_subject_attributes` — this
   build records no visitor identity of its own), and rule
   records binding a segment to an opaque content reference
   (`create_rule`). Matching is derived at read time by the
   seam `_condition_holds`: deterministic presence/equality
   checks over recorded attributes, reported as
   matched-condition counts and aggregate matching counts
   (`segment_match`, `segment_match_counts`, `rule_view`).
   This is the form the untiered set's batch unit adjudicated
   for the same family. **The honest form is narrower than the
   entry's name, stated plainly:** no optimization is computed
   (no ranking, no variant selection, no outcome measurement)
   and no content is served (`served_here: False`,
   `optimized_here: False` on the views). What is built is the
   records-and-derivation layer — segment definitions,
   recorded attributes, and deterministic match derivations —
   which is the part of the family this substrate can honestly
   hold. The disposition stays build-extension on that stated
   scope; it is not re-judged, because the brief for this unit
   defines the build-extension form for this entry as exactly
   these records and derivations.

**Stub-engine (5)** — each closed as a labeled reference
implementation: registry records only, never execution, each
carrying `reference_stub: True` and its family's not-here flag.

6. **CDN / delivery network and runtime site serving**
   (idx 195) — CDN reference records
   (`register_cdn_reference`; `served_here: False`) with
   transport receipts (`record_cdn_receipt`) carrying
   `reference_transport: True`. Per PLATFORM-LAYER.md decision
   6, runtime serving is a deployment property; this build
   serves no site.
7. **Enterprise search indexing engines (Boolean / concept /
   fuzzy / multilingual / hierarchical / geospatial; the core
   searches registry metadata)** (idx 196) — search index
   reference records (`register_search_index_reference`;
   `indexing_performed_here: False`) plus run references
   storing engine-reported document counts exactly as reported
   (`record_index_run_reference`). The build's search remains
   the core's literal substring search over registry metadata
   (pinned by test); no indexing is performed here.
8. **Participant engagement & research platform vertical**
   (idx 200) — engagement platform reference records
   (`register_engagement_reference`; `engaged_here: False`,
   `reference_transport: True`) with receipts
   (`record_engagement_receipt`) storing channel references
   and participant counts exactly as reported by the external
   platform. Recruitment, the participant portal, and
   longitudinal study tooling stay with that platform; no
   participant is engaged here.
9. **Platform hosting itself (PaaS runtime)** (idx 201) —
   hosting reference records (`register_hosting_reference`;
   `hosted_here: False`) with the fork's substrate label
   recorded verbatim as the fork's own. Per PLATFORM-LAYER.md
   decision 6, a fork's hosting substrate does not transfer to
   the build.
10. **Editorial workflow engines beyond lifecycle mechanics
    (parallel review, routing, notifications; claimed by no
    sibling)** (idx 203) — workflow engine reference records
    (`register_workflow_engine_reference`) holding the engine's
    workflow definition as data (`executed_here: False`).
    Registering a reference changes no core item — pinned by a
    test that creates an item, registers a parallel-review
    engine reference, and reads the item back still `draft`.
    The editorial lifecycle mechanics stay the core's.

## Re-judgments

**None.** All ten entries landed at their drafted triage
dispositions. The personalization entry's scope bound (records
and deterministic match derivations; no optimization computed,
no content served) is stated in its disposition above — it is
the build-extension form the unit's brief specifies for this
entry, not a corrected disposition.

## Negative control (fresh, for the new code)

The case-decision separation-of-duties seam
`CmsExtensions._check_decider_not_opener` is the load-bearing
guard for the BPM entry: a case's decision may be recorded only
by someone other than the user who opened the case (control
family AC-5, mirroring the group's own founding drill on the
editorial approver guard). `tests/test_gaps_batch.py` carries
the in-suite control in three-legged form (canonical /
mutant-waves-through / mutant-as-expectation fails), and the
live drill was performed on the real module: the seam's guard
body patched to `return None` (occurrence count asserted = 1
before patching) made **exactly 2 of 143 tests fail** (the two
canonical-expectation tests in the control class); the module
was restored from `scratch/extensions.py.premutation` and
verified SHA-256 identical (`ebb3e8d9…`), suite re-ran green.
Full record in `tests/README.md`; raw mutated run in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / unchanged

- `specs/specs.json`, the core service layer, and the REST API
  are untouched — the extension surface is store-level only,
  following the sibling batch units' pattern.
- The section's platform-layer paragraph in the union spec
  (encryption at rest, TLS when configured, multi-tenancy,
  demo identities as hooks) stands on PLATFORM-LAYER.md and
  was not absorbed by any entry here.
- The remainder addition's registered gap (Iron Mountain
  InSight's ML/AI content classification, extraction &
  enrichment engine, in `ADDENDUM.md`) is a different section's
  entry and is untouched by this unit.
