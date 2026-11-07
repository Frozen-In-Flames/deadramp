# Final GAPS batch — Remainder Group 5, Library Systems L1

Unit: section "Remainder Group 5 — Library Systems L1 (2 forks)" in
GAPS.md, 8 open entries (the ninth, "Identity provider (IA-2 stays
with the embedding organization)", was already closed `re-scoped`
under PLATFORM-LAYER.md and is untouched). Build: one new module,
`src/librarysys/extensions.py` (`LibraryExtensions` wrapping the
core store); all 7 core modules byte-identical. Tests:
`tests/test_gaps_batch.py`, suite 47 → 66.

Boundary note: the CMS L1 batch unit built an ILS vertical in
records form inside the CMS substrate. This group is the dedicated
library-systems substrate, built from the two library forks' own
descriptions; the surfaces below are this group's own records over
its own catalogue/holdings/circulation core, and nothing here
depends on or duplicates the CMS surface.

## Per-entry dispositions

- **idx 991 — "Discovery & delivery service" → built.**
  Discovery query records holding a validated SHA-256 query digest
  plus opaque result references only; the function signature has no
  query-text parameter, so passing `query_text=` raises TypeError
  and raw query text can never be stored (the Legal & Policy
  sandbox discipline). `result_count` is derived at read from the
  recorded references and is never stored. Delivery closes as
  reported-outcome records bound to a query and a core catalogue
  item (`delivered_here: False`, outcome verbatim), pinned to
  leave the core item byte-identical.

- **idx 992 — "Digital preservation system" → built.**
  Preservation records bound to core catalogue items holding an
  opaque preservation ref and a validated SHA-256 content digest,
  `bytes_held: False` — the bytes themselves are never held here.
  Fixity closes as reported-result records (`verified_here:
  False`): this build computes no checksum over content it does
  not hold, so the reported result is the record.

- **idx 993 — "Course resource list management" → built.**
  Course list records plus entry operations composing core
  catalogue items; an item may appear at most once per list (the
  guard seam below), and `entry_count` is derived at read, never
  stored.

- **idx 994 — "Research activities platform" → reference**
  (as drafted, stub-engine). Research activity records and
  reported-outcome records, `reference_stub: True`,
  `platform_operated_here: False`. The platform itself is not
  operated here.

- **idx 995 — "Knowledge management system" → built.**
  Knowledge records plus link records binding them to core
  catalogue items; `link_count` derived at read. Links are this
  build's own recorded assertions; no retrieval or inference is
  performed and no score is computed anywhere (recursive scan).

- **idx 996 — "Accessible delivery & rendering" → reference**
  (**re-judged** from build-extension, DECISION.md qualification
  1). Grounds: the entry names delivery and rendering themselves,
  and the group's own UNION-SPEC places accessible
  delivery/rendering in the delivery layer, not records; a
  renderer over content this build never holds would be a
  renderer in name only (the Marketing & Sales proposal-generation
  precedent). Lands as accessibility request records against core
  items (patron as opaque `patron_ref` only) plus reported-outcome
  records, `reference_stub: True`, `rendered_here: False`,
  `delivered_here: False`. If the parent prefers `built` for the
  records surface, only the token changes; the code is identical
  either way.

- **idx 997 — "Automation engine" → reference** (as drafted,
  stub-engine). Execution-request records bound to core workflow
  definitions plus reported-outcome records, `reference_stub:
  True`, `executed_here: False`, pinned to leave the core
  workflow record deep-equal — the core registry's never-executes
  discipline is carried unchanged.

- **idx 998 — "Integration transport" → reference** (as drafted,
  stub-engine). Transport receipt records bound to core
  integration records, `reference_transport: True`,
  `transmitted_here: False`, `connected_here: False`, pinned to
  leave the core integration record deep-equal.

## Cross-cutting pins

Exact key sets pinned for the stored records; derived views add
only their derived keys. Failed operations consume no ids (bad
digest → next query is still `dsc-1`). A denied viewer write is
audited as `ext_catalogue_write:denied` on the core audit log.
Recursive scan over every extension surface: no score/rank/rating
key, no money-shaped key (amount/cents/fee/fine/price — the group
has no money shape at all), no float values.

## Fresh negative control (mutation-verified)

The course-list entry guard `_check_course_entry_absent` in
`extensions.py`. In-suite three-leg control in
`test_gaps_batch.NegativeControlTests` (canonical rejects a
duplicate entry / no-guard mutant subclass accepts it /
mutant-as-expectation fails). Live drill on the real file: the
guard condition patched to `if False:` → suite FAILED with
**exactly 1 failure**
(`NegativeControlTests.test_canonical_rejects_duplicate_entry`);
restored from `scratch/extensions.py.premutation`, SHA-256
verified, suite re-ran green (66/66). Recorded in
tests/README.md; full drill output in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered by this unit

The section's identity-provider entry (already `re-scoped` in
writing before this unit). HTTP exposure of the extension surface
(store-level only, matching the sibling batch units' pattern).
