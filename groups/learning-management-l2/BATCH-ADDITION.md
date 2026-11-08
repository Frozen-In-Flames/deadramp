# Final GAPS batch — second unit: Remainder Addition — Learning Management L2

Unit: the 1 OPEN entry in GAPS.md under the exact section header
**`## Remainder Addition — Learning Management L2 (+1 fork)`**
(idx 678 in `../../gaps-batch/inventory.json`). Entry count
verified against both sources: GAPS.md lists exactly 1
`- [ ] open` entry in this section and the inventory assigns
exactly idx 678 to it — **no discrepancy**. The section holds no
pre-closed entries. Disposition per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): the entry
was drafted **stub-engine** and closes **reference** exactly as
drafted — **no re-judgment**.

All extension code is in one new module,
`src/lms/extensions_addition.py` (`LmsExtensionsAddition`,
wrapping the core `LmsStore`, audit prefix `exta_`). Every
existing module — the 7 core modules and the first batch unit's
`extensions.py` (`833ca1c9…`) — is byte-identical to its
pre-build state (SHA-256 verified against the pre-work baseline
in `scratch/prebatch-addition-src.sha256`; `store.py` still
hashes to the shipped `820d9712…`). No core extension was
needed. Full suite: 166 tests before, **185 tests after, OK**,
including the fresh mutation-verified negative control recorded
in `tests/README.md`.

## Per-entry disposition

### idx 678 — reference (stub-engine, as drafted)

> Licensed content library & practice-lab environments: the hosted off-the-shelf catalogue itself — thousands of video courses, ebooks, audiobooks, boot camps, hands-on practice labs, and the assessment content it includes, booked once as content (the substrate's catalog holds records ABOUT content, and the already-registered delivery-engine gap is the runtime, not the catalogue; no registered gap named the content supply itself)

The entry names the content supply itself: a hosted catalogue
operated by the addition fork's platform (Percipio). This
substrate holds no content — its catalog is records ABOUT
content (core content items are metadata with a standards
label) — and it hosts and delivers nothing: the first unit
already closed the delivery runtime as session records, and the
entry's own parenthetical draws the same line from the other
side (the delivery-engine gap is the runtime, not the
catalogue). What ships is the labeled reference form, in the
house pattern for a hosted supply:

- `create_library_item` (`lib-`, Action: catalog_write) — a
  record ABOUT one catalogue item: title, `format_kind` from the
  fork's own format list in its description (`video_course`,
  `ebook`, `audiobook`, `boot_camp`, `practice_lab`,
  `assessment_content`), and the supplying platform named by an
  opaque `provider_ref`. Optional bindings to a core course
  and/or a core content item are **by id only** and must
  resolve; a bound content item belonging to a different course
  is rejected, mirroring the first unit's delivery-session
  mismatch rule. Every record carries `reference_stub: True`,
  `reference_transport: True`, state `recorded_reference_only`,
  and `hosted_here` / `content_held` / `delivered_here` /
  `administered_here: False` on its face; the stored record's
  exact key set is pinned by test. A full addition flow is
  pinned to leave the bound core course and content records
  **byte-identical**.
- Assessment content is catalogue content, exactly as the
  addendum books it: the `assessment_content` format label names
  items IN the catalogue, never assessment administration —
  `administered_here: False` on every record, no administration-
  or score-shaped method exists on the surface (pinned), and
  the founding no-score invariant binds the surface by a
  recursive key scan.
- `record_access_report` (`acc-`, Action: catalog_write) — a
  platform access report held **verbatim**: the fork's own
  channels (`web_browser`, `mobile_app`), the outcome label
  stored exactly as reported (`outcome_basis:
  platform_reported`), and an optional `reported_item_count`
  held exactly as reported (non-negative integers only; bools,
  floats, negatives, and numeric strings are rejected with no
  id consumed). `transmitted_here: False` — nothing is fetched
  or checked here.
- `record_lab_environment` (`lab-`, Action: catalog_write) — a
  practice-lab environment named by **opaque reference only**,
  bound to a library item whose format is `practice_lab` (any
  other format is rejected). `provisioned_here: False`,
  `executed_here: False`, `content_held: False` — no
  environment is provisioned and no lab runs here.
- Derived views: `library_item_view` adds `access_report_count`
  and `latest_outcome_label` derived at read from the recorded
  reports via the `_latest_outcome_label` seam (the stored
  record carries neither key, pinned); `library_summary`
  (Action: report_read) is deterministic counts over the
  recorded reference records only (`counts_basis:
  recorded_reference_records_only`) — no catalogue size, usage,
  or learner figure is computed or claimed.

Cross-cutting, per the group's doctrines: the founding
**no-score invariant binds the addition surface exactly as it
binds the core** — a recursive key scan over every addition
record, view, list, and the summary finds no `score` /
`score_*` / `*_score` / grade-shaped key, and no content-,
body-, payload-, URL-, password-, or credential-shaped key
(pinned in `test_gaps_batch_addition.TestCrossCutting`); no
public method accepts `**kwargs` (signature scan, pinned), so
no content or credential argument can be smuggled in (a
`content=` or `password=` call raises TypeError, pinned); no
float value appears anywhere on the surface (pinned); all
parties are opaque `*_ref` strings; RBAC reuses the core
permission actions (catalog for items/reports/labs, report for
the summary) with the core's matrix applied as shipped — at
this tier `catalog_write` is admin-only, so the write surface
is admin-operated, the same note the L1 sibling recorded for
its tier; denied writes consume no id (pinned); every
successful mutation is recorded on the core audit log with an
`exta_`-prefixed action.

**Fresh mutation-verified negative control:** the
`_latest_outcome_label` seam in `extensions_addition.py` —
patching its return to read the FIRST recorded report
(`reports[0]` instead of `reports[-1]`, occurrence count
asserted = 1 before patching) made exactly **4** of 185 tests
fail, all in the new module (the view-derivation test, the
summary test, and the control's canonical and seam-direct
legs), with all 166 pre-existing tests still passing. The
module was restored from `scratch/extensions_addition.py.premutation`
and verified SHA-256-identical (`daaa1554…`); the suite re-ran
green. Full record in `tests/README.md`; raw output in
`scratch/gaps_batch_addition_mutation_run.txt`.

Left unresolved: nothing in this unit. HTTP exposure of the
addition surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
