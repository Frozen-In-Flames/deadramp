# Final GAPS batch — Content Management System (CMS), Untiered Set 14

Batch note for the twelve open entries of the repo-root `GAPS.md`
section "Untiered Set 14 — Content Management System (CMS)
(2 forks, tier null)", closed under the ratified triage in
`gaps-batch/DECISION.md`. This set is untiered: tier stays null
everywhere — no baseline is asserted, no CMMC equivalence is
drawn, and nothing in this batch adds a tier, baseline,
impact-level, or equivalence key or language to any record,
view, or document. The founding discipline binds throughout:
the substrate is records machinery; nothing renders, serves,
generates, indexes, executes, hosts, or provides identity.

## What was added

- `src/cms/extensions.py` (one new module): `CmsExtensions`,
  a records register wrapping the core `CmsStore`. In-memory
  collections with the founding conventions — validation before
  mutation (failed operations consume no id), founding-permission
  RBAC with denials audited in the core audit log under a
  `:denied` suffix, opaque references only, derived-never-stored
  views, counts-only rollups. RBAC reuses the founding action
  vocabulary (no new actions); the action mapping is documented
  in the module docstring.
- `tests/test_gaps_batch.py`: 26 tests pinning the extension
  surface entry by entry, including the stub labels, a recursive
  tier/baseline/score key scan over the whole surface, and the
  batch's fresh negative control (below).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the accounting in the group README before and after the
build: `store.py` still `e1d05424…`, all 7 of 7 unchanged). No
core change was needed, and none was made. Suite: **109 tests
before → 135 tests after, OK**.

## Per-entry disposition

**Build-extension (5)** — each closed by its in-substrate records
form: records plus deterministic derivations over this set's own
core content registry.

1. **Rendering & templating engines and visual/WYSIWYG editors**
   (idx 884) — template and fragment *definition records*
   (`create_template` / `update_template` / `get_template` /
   `list_templates`). The body is held as data and versioned
   (prior bodies retained in `history`); placeholder names are
   derived at read time by scanning the held text. Nothing is
   rendered and nothing is served — every record carries
   `rendered_here: False`, pinned by test. A WYSIWYG editor UI
   is a client surface, not a records function; the records form
   is the definition layer such an editor would edit, and that
   bound is stated rather than smoothed over.
2. **Personalization / experience optimization** (idx 885) —
   audience segment definitions with match conditions held as
   data (`create_segment`), subject attribute records keyed by
   opaque `subject_ref` (`record_subject_attributes` — this
   build records no visitor identity of its own), and rule
   records binding a segment to an opaque content reference
   (`create_rule`). Matching is derived at read time by the
   single seam `_condition_holds`: deterministic
   presence/equality checks over recorded attributes, reported
   as matched-condition counts and aggregate matching counts
   (`segment_match`, `segment_match_counts`, `rule_view`).
   **The honest form is narrower than the entry's name, stated
   plainly:** no optimization is computed (no ranking, no
   variant selection, no outcome measurement) and no content is
   served (`served_here: False`, `optimized_here: False` on the
   views). What is built is the records-and-derivation layer —
   segment definitions, recorded attributes, and deterministic
   match derivations — which is the part of the family this
   substrate can honestly hold. The disposition stays
   build-extension on that stated scope; it is not re-judged,
   because the brief for this unit defines the build-extension
   form for this entry as exactly these records and derivations.
3. **Document & media versioning depth** (idx 887) —
   `item_version_chain` derives an item's full revision chain
   at read time from the core revision registry;
   `record_comparison` records comparisons between two existing
   revisions with the outcome label recorded verbatim and
   `diff_computed_here: False` (no diff engine runs over
   revision content — comparison metadata is a recorded label,
   per the founding discipline that the registry holds records,
   not content machinery); asset version groups
   (`create_asset_version_group` / `add_asset_version`) link
   core asset records under recorded version labels, with
   member counts and label lists derived at read. One version
   entry per asset per group; unknown assets and unknown
   revision numbers are rejected with no id consumed.
4. **Low-code application builders & form engines** (idx 889) —
   application and form *definition records*
   (`create_definition` / `update_definition`), held as data
   (deep-copied at the boundary) and versioned on update, with
   `executed_here: False` and `rendered_here: False` on every
   record. Nothing executes and nothing renders; the records
   are the definition layer a builder UI would manipulate.
5. **Multi-site & multilingual site operations depth**
   (idx 891) — locale records over core sites
   (`create_locale`, codes unique per site) with item linkages
   (`link_item_to_locale`; the item must belong to the locale's
   site, duplicates rejected), and read-time derivations:
   `site_locale_summary` (locale count, locale codes, distinct
   linked items, site item count) and `multi_site_summary`
   (per-site section/item/locale/linked counts over the core
   registry plus this module's records). All counts derived,
   none stored. Linkage is a record — no localized content is
   produced here.

**Stub-engine (7)** — each closed as a labeled reference
implementation: registry records only, never execution, each
carrying `reference_stub: True` and its family's not-here flag.

6. **Enterprise search indexing engines** (idx 883) — search
   index reference records (`indexing_performed_here: False`)
   plus run references storing engine-reported document counts
   exactly as reported. The build's search remains the core's
   literal substring search over registry metadata (pinned by
   test); no indexing is performed here.
7. **Editorial workflow engines beyond lifecycle mechanics**
   (idx 886) — workflow engine reference records holding the
   engine's workflow definition as data
   (`executed_here: False`). Registering a reference changes no
   core item — pinned by a test that creates an item, registers
   a parallel-review engine reference, and reads the item back
   still `draft`. The editorial lifecycle mechanics stay the
   core's.
8. **Document generation engines** (idx 888) — document
   generation reference records (`generated_here: False`) plus
   generated-package references recorded as opaque refs
   reported by the external engine. This family is the
   zero-claim fork's (Nintex Drawloop DocGen) whole function
   and has no family in the set's taxonomy; it is closed as a
   reference, not repaired into the taxonomy.
9. **Identity federation / SSO services (IdP)** (idx 890) —
   identity hook records per PLATFORM-LAYER.md decision 1:
   `hook_only: True`, `identity_provider: False`, the protocol
   label (e.g. "SAML 2.0", as Liferay documents it) recorded
   verbatim. This build is not an IdP and ships no credential
   store; the documented SSO assertion remains the fork's.
10. **Headless delivery & integration engines** (idx 892) —
    headless delivery reference records
    (`delivered_here: False`) with transport receipts carrying
    `reference_transport: True`. The build's own REST API over
    the registry is Core and unchanged; delivery to external
    channels is an external system.
11. **CDN / delivery network and runtime site serving**
    (idx 893) — CDN reference records
    (`reference_transport: True`, `served_here: False`). Per
    PLATFORM-LAYER.md decision 6, runtime serving is a
    deployment property; this build serves no site.
12. **Platform hosting itself** (idx 894) — hosting reference
    records (`hosted_here: False`) with the fork's substrate
    label recorded as the fork's own. Per PLATFORM-LAYER.md
    decision 6, a fork's hosting substrate does not transfer to
    the build.

## Re-judgments

**None.** All twelve entries landed at their drafted triage
dispositions. The personalization entry's scope bound (records
and deterministic match derivations; no optimization computed,
no content served) is stated in its disposition above — it is
the build-extension form the unit's brief specifies for this
entry, not a corrected disposition.

## Negative control (fresh, for the new code)

The personalization matching seam `cms.extensions._condition_holds`
is the load-bearing derivation: a subject matches a segment only
when every recorded condition holds. `tests/test_gaps_batch.py`
carries the in-suite control in three-legged form (canonical /
mutant-waves-through / mutant-as-expectation fails), and the
live drill was performed on the real module: the seam's equality
branch patched to `return True` (occurrence count asserted = 1
before patching) made **exactly 5 of 135 tests fail**; the
module was restored from `scratch/extensions.py.premutation`
and verified SHA-256 identical (`78797954…`), suite re-ran
green. Full record in `tests/README.md`; raw mutated run in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / unchanged

- The already-closed platform-layer entry (idx 895) is
  untouched, as are `specs/specs.json`, the core service layer,
  and the REST API — the extension surface is store-level only,
  following the sibling batch units' pattern.
- Standing founding gaps with no claimant in this set (library
  ILS vertical; BPM / case-management engine depth; participant
  engagement & research platform vertical; bulk ingestion &
  index-in-place engines) remain registered under the founding
  group; they are not this unit's entries and were not touched.
