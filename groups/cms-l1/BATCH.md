# Final GAPS batch — Group 24, Content Management System (CMS) L1

Batch note for the eight open entries of the repo-root `GAPS.md`
section "Group 24 — Content Management System (CMS) L1
(2 forks)", closed under the ratified triage in
`gaps-batch/DECISION.md`. This is the project's thinnest-evidence
group: applying Group 20's taxonomy verbatim, the two fork
descriptions tag exactly one claim in the whole group, the core
stands on the explicit core-boundary decision recorded in
`UNION-SPEC.md`, and several entries below are families carried
from the Group 20 (CMS L2) union at 0 claims here. **Stated
plainly: at 0 claims here, the forms for the carried families are
carried from the L2 union's adjudicated batch forms (and, for
personalization, the untiered set's), mirrored at this tier —
they are not claimed from this group's evidence.** The baseline
framing is this group's own throughout: the Low baseline, audit
on the FedRAMP Low side only, and the Moderate selection SI-7 is
not claimed at this tier (asset checksums remain an
implementation integrity property). The founding discipline
binds throughout: the substrate is records machinery — content
items with append-only revisions, asset records holding metadata
and checksums only, search as literal substring over registry
metadata — and nothing in this batch renders, serves, indexes,
transmits, hosts, executes, delivers, fulfills, or adjudicates.

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
- `tests/test_gaps_batch.py`: 44 tests pinning the extension
  surface entry by entry, including the stub labels, the exact
  case-record and report-run key sets, and the batch's fresh
  negative control (below).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the pre-build baseline before and after the build:
`store.py` still `e1d05424…`, all 7 of 7 unchanged). No core
change was needed, and none was made. Suite: **98 tests
before → 142 tests after, OK**.

## Per-entry disposition

**Build-extension (6)** — each closed by its in-substrate records
form: records plus deterministic derivations over this group's
own core content registry.

1. **Library ILS vertical (this group's dominant vertical):
   circulation, acquisitions, resource sharing / interlibrary
   loan, collection management, knowledgebase, access proxying,
   digital collection management, and the union-catalog data
   network beneath them** (idx 235) — the CMS L2 unit's records
   form, expanded to this group's full vertical. Circulation:
   loan records over opaque `patron_ref` / `item_ref`
   (`record_loan` / `record_loan_event`); state events recorded
   verbatim, current state derived at read time by
   `_current_loan_state` and absent from the stored record
   (pinned). Acquisitions: order records
   (`create_acquisition_order`) holding an integer-cent amount
   as data — floats and booleans rejected at the boundary, no
   id consumed — never transmitted (`transmitted_here: False`);
   MARC21-shaped cataloging field records
   (`create_catalog_record`) held as data with an exact field
   shape, never parsed (`discovery_engine_here: False`).
   Resource sharing / ILL: request records over opaque patron,
   item, and partner references (`record_ill_request` /
   `record_ill_event`) with partner-reported outcome labels
   recorded verbatim and current state derived at read;
   fulfillment is the partner library's system
   (`fulfilled_here: False` on the view). Collection management:
   collection records binding opaque item references to recorded
   collection labels, with counts by label derived at read
   (`collection_summary`). Knowledgebase: article records in the
   article-revisions form (`create_kb_article` /
   `update_kb_article`) — bodies held as data and versioned,
   prior bodies retained in `history`, nothing published or
   rendered (`published_here: False`). Access proxying:
   configuration records (`create_proxy_config`) holding a
   target reference and settings as data; no traffic is proxied
   (`proxied_here: False`). Digital collection management:
   collection records bound to core sites
   (`create_digital_collection`) whose members are
   metadata-plus-digest records (`add_digital_item` — opaque
   asset reference plus SHA-256 only, exactly the core asset
   registry's discipline; bytes never held, `bytes_held:
   False`; member counts derived at read). Union catalog:
   contribution / holding records (`record_union_holding` /
   `record_union_event`) with state derived at read; the
   union-catalog data network itself is other libraries'
   systems (`network_here: False` on every record).
   **Boundary, stated plainly:** a dedicated Library Systems
   category exists elsewhere in this repo
   (`groups/library-systems-l1`); this entry closes as THIS
   group's vertical records form over its own substrate and
   imports nothing from that group.
2. **Mobile application delivery and the companion mobile app
   itself** (idx 236) — application definition records
   (`create_app_definition`, optionally bound to an existing
   core site) and release definition records
   (`create_app_release`), plus reported distribution outcome
   records (`record_distribution_outcome`) storing channel
   install counts exactly as reported, with totals derived at
   read (`distribution_summary`). No application binary is held
   (`binary_held: False`) and nothing is delivered here
   (`delivered_here: False` on definitions, releases, and
   outcomes).
3. **Rendering & templating engines and visual / WYSIWYG
   editors (carried from the Group 20 union; 0 claims here)**
   (idx 237) — template and fragment *definition records*
   (`create_template` / `update_template` / `get_template` /
   `list_templates`). The body is held as data and versioned
   (prior bodies retained in `history`); placeholder names are
   derived at read time by scanning the held text and are absent
   from the stored record (pinned by test). Editor
   *configuration records* (`create_editor_config` /
   `update_editor_config`) hold a mode label and settings as
   data, versioned the same way. Nothing is rendered and
   nothing is served — every record carries
   `rendered_here: False`. A WYSIWYG editor UI is a client
   surface, not a records function; the records form is the
   definition layer such an editor would edit, and that bound
   is stated rather than smoothed over. (The form the CMS L2 and
   untiered batch units adjudicated, mirrored here.)
4. **Analytics & reporting engines beyond registry reporting
   (carried; "custom reports / Report Designer" are recorded
   near-misses)** (idx 240) — report *definition records*
   (`create_report_definition`) selecting one of four core
   registry breakdowns (status / site / type / asset kind) as
   data, and run records (`record_report_run`) whose stored
   shape is pinned by test to exactly `{id, definition_id,
   recorded_by, recorded_utc}` — a run record stores **no
   figures**. Figures exist only in the derived view
   (`report_run_view`): deterministic counts over this
   substrate's own core registry, computed at read time from
   the core's registry report (`figures_stored: False`; a test
   pins that a run's figures change when the registry changes
   after the run was recorded). **The near-miss status is
   restated plainly:** the union spec records OCLC's "analytics,
   including custom reports and visualizations" / Report
   Designer as taxonomy near-misses; this build is
   registry-derived reporting, not the vendor's Report Designer,
   and no report-designer surface is claimed.
5. **Bulk ingestion & index-in-place engines (carried)**
   (idx 241) — ingestion-batch records
   (`create_ingestion_batch`): an opaque source reference, a
   document count stored exactly as reported, and checksum
   references — no content is ingested or held
   (`content_held: False`, exact key set pinned) — and
   ingestion-*job* records (`create_ingestion_job`) bound to
   existing core content records (an unknown item is rejected
   with no id consumed) with verbatim reported counts;
   ingested content is handled exactly as the core's discipline
   allows (records, metadata, and checksums — never file bytes)
   and no ingestion engine runs here (`executed_here: False`).
   Index-in-place closes as index *declaration* records
   (`create_index_declaration`): target reference and field
   list held as data, `indexing_performed_here: False`.
   `ingestion_summary` derives batch/job/count/checksum totals
   at read time.
6. **BPM / case-management engine; participant engagement
   vertical; personalization (carried from the Group 20 union
   at 0 claims here)** (idx 242) — one carried entry closing in
   three records forms. BPM: case records (`open_case` /
   `record_case_event` / `case_view` / `list_cases`) over opaque
   `case_ref` / `subject_ref`. The stored record's exact key set
   is pinned by test — `{id, case_ref, subject_ref, case_type,
   opened_by, created_utc, events}` — and contains no field that
   could hold case content, narrative, or evidence. State events
   are recorded verbatim; current state is derived at read.
   Decisions (`record_case_decision`) are recorded verbatim
   under the separation-of-duties seam
   `_check_decider_not_opener` (the decider is never the case's
   opener; a denied decision is audited and consumes no id) and
   carry `adjudicated_here: False` — nothing is investigated or
   adjudicated here. The mechanism is the CMS L2 unit's
   adjudicated form; the case-type vocabulary is generic at
   this tier (`general`, `service_request`, `access_request`,
   `program_case`, `other`) because the family is carried at
   0 claims here and no fork's casework kinds are imported.
   Participant engagement: participation records
   (`record_participation`) over opaque program and participant
   references with outcome labels recorded verbatim as reported
   by the engagement program, and counts by outcome derived at
   read (`participation_summary`); this build records no
   participant identity of its own and engages no participant.
   Personalization: audience segment definitions with match
   conditions held as data (`create_segment`), subject
   attribute records keyed by opaque `subject_ref`
   (`record_subject_attributes` — this build records no visitor
   identity of its own), and rule records binding a segment to
   an opaque content reference (`create_rule`) — the untiered
   set's adjudicated form. Matching is derived at read time by
   the seam `_condition_holds`: deterministic presence/equality
   checks over recorded attributes, reported as
   matched-condition counts and aggregate matching counts
   (`segment_match`, `segment_match_counts`, `rule_view`).
   **The honest form is narrower than the family's name, stated
   plainly:** no optimization is computed (no ranking, no
   variant selection, no outcome measurement) and no content is
   served (`served_here: False`, `optimized_here: False` on the
   views). What is built is the records-and-derivation layer,
   which is the part of the family this substrate can honestly
   hold.

**Stub-engine (2)** — each closed as a labeled reference
implementation: registry records only, never execution, each
carrying `reference_stub: True` and its family's not-here flag.

7. **CDN / delivery network and runtime site serving (carried;
   one sibling's "content delivery functionality" is a recorded
   near-miss)** (idx 238) — CDN reference records
   (`register_cdn_reference`; `served_here: False`) with
   transport receipts (`record_cdn_receipt`) carrying
   `reference_transport: True`. Per PLATFORM-LAYER.md decision
   6, runtime serving is a deployment property; this build
   serves no site. The near-miss status of the sibling's
   "content delivery functionality" is recorded in the union
   spec's ARTIFACTS note and stands; the reference form does not
   depend on it.
8. **Enterprise search indexing & discovery engines (carried;
   one sibling's discovery service is a recorded near-miss)**
   (idx 239) — search index reference records
   (`register_search_index_reference`; `indexed_here: False`)
   plus run references storing engine-reported document counts
   exactly as reported (`record_index_run_reference`), and
   discovery query records (`record_discovery_query`) holding a
   SHA-256 digest of the query plus opaque result references
   only — the raw query text is never stored (pinned by test:
   the record's exact key set carries `query_sha256` and no
   query-text field), per this substrate's metadata-plus-digest
   discipline. The build's search remains the core's literal
   substring search over registry metadata (pinned by test); no
   indexing is performed and no index is consulted here. The
   near-miss status of OCLC's discovery service under the
   verbatim taxonomy stands as recorded.

## Re-judgments

**None.** All eight entries landed at their drafted triage
dispositions. The personalization scope bound (records and
deterministic match derivations; no optimization computed, no
content served) is stated in its disposition above — it is the
build-extension form the unit's brief specifies for this entry,
not a corrected disposition.

## Negative control (fresh, for the new code)

The case-decision separation-of-duties seam
`CmsExtensions._check_decider_not_opener` is the load-bearing
guard for the BPM entry: a case's decision may be recorded only
by someone other than the user who opened the case (control
family AC-5 — a Low-baseline selection at this tier — mirroring
the group's own founding drill on the editorial approver guard).
`tests/test_gaps_batch.py` carries the in-suite control in
three-legged form (canonical / mutant-waves-through /
mutant-as-expectation fails), and the live drill was performed
on the real module: the seam's guard condition patched to
`if False:` (occurrence count asserted = 1 before patching) made
**exactly 2 of 142 tests fail** (the two canonical-expectation
tests in the control class); the module was restored from
`scratch/extensions.py.premutation` and verified SHA-256
identical (`9881cb12…`), suite re-ran green. Full record in
`tests/README.md`; raw mutated run in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / unchanged

- `specs/specs.json`, the core service layer, and the REST API
  are untouched — the extension surface is store-level only,
  following the sibling batch units' pattern.
- The section's platform-layer entries in the union spec
  (encryption at rest, TLS when configured, multi-tenancy, demo
  identities as hooks — not an IdP) stand on PLATFORM-LAYER.md
  and were not absorbed by any entry here; the hosting family
  itself is not among this unit's eight entries.
- Entries belonging to other GAPS.md sections (including the
  CMS L2 section and its remainder addition) are untouched by
  this unit.
