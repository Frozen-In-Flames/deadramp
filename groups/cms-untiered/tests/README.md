# Tests — Content Management System (CMS), untiered set

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to. The core suite is
the founding CMS L2 group's suite, carried with the code; the
founding additions module (`test_additions.py`, which pins the
tiered census unit `addition:cms-l2`) is **not** carried — it pins
a different unit. One labeling fix was made in the carry:
`cms_helpers.py`'s docstring now names this untiered set instead
of L2. `test_negative_control.py` retains its founding provenance
line ("the contract's required negative control for Group 20") —
that is where the contract it pins comes from, and the line is
accurate as provenance.

## Run

```bash
cd groups/cms-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 109 tests
```

Status at delivery: **109 tests, OK** against the implementation
in `../src/`. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

Composition: the founding group's 98 core tests, plus 11 in
`test_specs.py` (below).

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) / access_administration — exact permission matrix for admin/publisher/editor/author/viewer over `PERMISSIONS`/`ACTIONS` (admin = all; publisher = all except `audit_read`; editor, author and viewer sets pinned exactly), `permissions_for()`, `can()`, `require()`, unknown role/None denied, author-own-only edit/submit at store level, plain-string actor identity |
| `test_audit.py` | Append-only audit log / records_management — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording each mutation action (site_create … asset_register), search audited, denied attempts recorded as `<action>:denied` with no id consumed, failed validation records no mutation |
| `test_sites_sections.py` | Sites & sections / site_structure — `site-` ids and shape, slug validation (no id consumed), global site-slug uniqueness, `section-` ids and parent linkage, parent must belong to the same site, section slug unique per site (not global), write-role denials, get/list |
| `test_types.py` | Content types / content_registry — built-ins pre-registered with fixed ids `ct-page`/`ct-article`/`ct-document`/`ct-collection` (`created_by` `"system"`), custom types `ct-{n}` from 1, `type_write` admin/publisher only, name required, unknown type → `NotFoundError` |
| `test_items_revisions.py` | Items & revisions / content_registry, authoring_editing — `ci-` creation shape (draft, author, revision 1 minting `rev-1` snapshot), unknown site/type/section/tag → `NotFoundError` with no id consumed, section-belongs-to-site, item slug unique per site, metadata validation/copy, get/list filters, edits minting revisions with snapshots, approved/published edits rejected, editor-may-edit-in_review vs author-may-not |
| `test_lifecycle.py` | Editorial lifecycle / authoring_editing — submit/approve/return happy paths, return note + resubmission, invalid transitions → `ValidationError`, review roles, author-cannot-approve at store level (name-identical reviewer in a review role), editor-author cannot review own item |
| `test_publishing.py` | Publishing / delivery_publishing — publish record `pub-{n}` fields, publish requires approved (no pub id consumed otherwise), publish roles, archive published-only, window derivation scheduled/live/expired at pinned `now` values (module-level `window_state` and via `get_item`/`list_items`), no-window → live, unpublished → `None`, `expire_at <= publish_at` rejected with the item staying approved |
| `test_assets.py` | Assets / media_assets, ingestion_repository — `asset-` ids and all six kinds, SHA-256 computed from supplied bytes, supplied checksum stored, checksum mismatch → `ValidationError` with no id consumed, bytes never retained (no `data` field on any record), kind/byte_size/checksum/site validation, write roles |
| `test_tags_metadata.py` | Tags & metadata / metadata_taxonomy — `tag-` ids, global slug uniqueness and validation, tag write roles, items linking tags at create and update (reflected in revisions), metadata round trip / default / replacement / copy semantics |
| `test_search.py` | Search / search_discovery — items by title/slug/body/metadata value, assets by filename/kind, sites by name/slug, tags by name/slug, result keys exactly `{items, assets, sites, tags}`, case-insensitive, literal (regex metacharacters neither match nor explode), blank query → all empty, non-string → `ValidationError` |
| `test_report.py` | Reporting / reporting — empty report (all statuses 0, 4 built-in types), counts by status/site/type, publish-record count, assets by kind (zeros included), totals, determinism and read access for any role |
| `test_service.py` | REST API — live HTTP server: health (no auth), 401 unknown user + role mismatch, 403 viewer site create (denied attempt audited `<action>:denied`), full flow (site → section → types → tag → item by dave → PATCH update → revisions → submit → approve-by-author 403 → approve by carol → windowed publish by bob → publishes list → item window at pinned `now` → asset with computed checksum → search → report → archive → audit as alice; audit as non-admin → 403), return flow over HTTP, 400/404 error envelopes |
| `test_main_cli.py` | `python -m cms serve --port <free>` subprocess (PYTHONPATH=src), waits for health, answers alice on `/audit` and erin/bob on `/sites`, terminates |
| `test_specs.py` | This untiered set's spec sheets (Untiered Set 14) — exactly 2 sheets; membership exact against census unit `untiered:Content Management System (CMS)` in `remainder.json`; tier discipline on every sheet (impact "Unknown" as-is, `cmmc_tier` null); registry fields vs `forks.json`; business categories recorded as in source (Liferay's five, Nintex's none); descriptions equal to the census record in `remainder/uncovered.json` (and no carriage returns); the **literal claim table** (1 claim total: Liferay `search_discovery`; Nintex zero-claim — the fallen floor pinned, not repaired); the one claim's evidence as the founding rule's 400-character truncation whose 397-character prefix is an exact substring of the description; near-miss pins (`editorial` earns no authoring claim, Google Cloud Platform earns no hosting claim, role-based permissions earn no access-administration claim, `personalization` stands as a named absence, Nintex's "create, manage and generate document packages" and bare "documents" earn nothing); certified-services record fields earning nothing; census citations 3/3 verifying (Nintex's exact, Liferay's whitespace-normalized) |
| `test_negative_control.py` | Negative control (below) |
| `cms_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, PUBLISHER=bob/publisher, EDITOR=carol/editor, AUTHOR=dave/author, VIEWER=erin/viewer), `USERS` registry, `fresh_store()`, `make_store()` (canonical site "Main Site" by PUBLISHER + section "News" by EDITOR), `make_item()`, `drive_to_approved()` and `drive_to_published()` |
| `store.py.premutation` | Pre-mutation copy of `../src/cms/store.py`, kept for the negative-control drill restore/hash check below (kept here because this group's `scratch/` is owned by the build worker) |

## Negative control

`test_negative_control.py` implements the contract's required
mutant: a `CmsStore` subclass (`MutantCmsStore`) whose
`_check_approver_not_author` is a no-op — the separation-of-duties
check is skipped. The traced claim, named in the module's
docstrings, is that **an item is never approved or returned by
its own author** (sibling claim family authoring_editing;
control family AC-5, separation of duties). For each canonical
case (author-approve, author-return) the test asserts three
things: the canonical expectation (`PermissionDenied` from the
real implementation, the item staying `"in_review"`), that the
mutant would NOT produce that expectation (it approves /
returns), and — via a literal `assertRaises(AssertionError)` —
that treating the mutant's outcome as the expected outcome
fails.

One isolation detail, documented in the test itself: the cases
use an **editor-authored** item reviewed by that same editor
(carol), so the reviewer's role already holds `item_review` and
`_check_approver_not_author` — which compares names — is the
only gate that can deny. A third test confirms a *different*
reviewer (publisher bob) approving carol's item succeeds on the
real store, so the denial is the author check firing rather
than a blanket refusal.

## Mutation verification in this tree (Untiered Set 14 drill)

The founding group's signature drill was re-run in this tree.
The guard body in `CmsStore._check_approver_not_author`
(`src/cms/store.py` — the two-line `if actor_name(actor) ==
item["author"]: raise PermissionDenied(...)`, occurring exactly
once, count asserted before patching) was patched to a no-op
(`return None`), the exact live counterpart of the mutant in
`test_negative_control.py`, and the full suite ran: **109 tests
ran, exactly 4 failed** — the founding drill's identical set:

- `test_lifecycle.TestLifecycle.test_author_cannot_approve_own_item_store_level`
- `test_lifecycle.TestLifecycle.test_editor_who_authored_cannot_review_own`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_approve_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_return_denied_canonical_but_mutant_returns`

No spec test failed under the mutant (the spec pins read
`specs.json`, not the store). `store.py` was then restored from
the pre-mutation copy kept in this directory
(`tests/store.py.premutation`) and verified SHA-256
`e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1`,
identical to the founding shipped hash; the suite re-ran:
**109 tests, OK**. The raw mutated run is in
`scratch/mutation_run.txt`. (The founding group's later
addition re-run failed exactly 5 — the same 4 plus one from its
additions module, which is not carried here; 4 is the correct
count for this tree.) The suite catches this defect class; the
negative control is not decorative.

## Live smoke (this tree)

A live HTTP smoke was run against the carried server
(`scratch/smoke.py`, output in `scratch/smoke_output.txt`):
health 200 with no auth; site created by bob/publisher (201);
section by carol/editor (201); item created by dave/author
(201), submitted by dave (200); dave's approve of his own item →
403; a second item authored by carol/editor, submitted, and
carol's approve of her own item → **403 (the
separation-of-duties guard over HTTP)**; bob approves dave's
item (200) and publishes it (200); the published item reads back
with derived `window_state: live`; search for "Smoke" returns
the item; a viewer (erin) site create → 403; the audit log as
alice/admin shows 13 entries including `:denied` records for the
denied attempts, and `/audit` as bob/publisher → 403. **SMOKE
OK.**

## Final GAPS batch coverage (Untiered Set 14, 2026-11-07)

The batch unit for this set added `../src/cms/extensions.py`
(`CmsExtensions`, a records register wrapping the core store)
and `test_gaps_batch.py` (26 tests) pinning the extension
surface for the twelve open entries of this set's GAPS.md
section. Existing content above is unchanged; the core suite is
untouched and the core modules are byte-identical.

| File | Covers |
|---|---|
| `test_gaps_batch.py` | Final GAPS batch, Untiered Set 14 — templates & fragments (record shape, `rendered_here` False pinned, placeholder names derived at read and absent from the stored record, update versioning with history, viewer write denied with no id consumed, audit action recorded); personalization (segment/subject/rule records, match derived at read — matched-condition counts for full/partial/non matches, aggregate match counts derived, rule view derives and serves nothing, subject re-record replaces attributes keeping the id, unknown subject → `NotFoundError`, bad conditions rejected with no id consumed); versioning depth (item version chain derived from core revisions, comparison records with verbatim labels and `diff_computed_here` False, unknown revision rejected with no id consumed, asset version groups with derived member counts, duplicate membership and unknown asset rejected); low-code definitions (held as data, deep-copied at the boundary, `executed_here`/`rendered_here` False, update versioning, non-object definition rejected); multi-site locales (locale records with per-site code uniqueness, item linkage with same-site enforcement and duplicate rejection, per-site and multi-site summaries derived); the seven reference stubs (labels pinned per family — `reference_stub` True throughout; search index `indexing_performed_here` False with engine-reported run counts stored as reported and core search unchanged; workflow engine definitions as data with a core item pinned unchanged/`draft`; document generation `generated_here` False with opaque package references; identity hook `hook_only` True / `identity_provider` False with the protocol label verbatim; headless delivery receipts `reference_transport` True / `delivered_here` False; CDN `served_here` False; hosting `hosted_here` False with the substrate label recorded); tier discipline (recursive scan over every extension record type and view asserting no tier/baseline/impact/score-shaped key exists anywhere on the surface); the batch's fresh negative control (below) |

Suite status for the batch unit: **135 tests, OK** (109 before,
26 added).

## Negative control (batch — personalization matching seam)

`test_gaps_batch.py`'s `TestConditionNegativeControl`
implements the batch's fresh mutant for the new code: the
traced claim is that **a subject matches a segment only when
every recorded condition holds against the subject's recorded
attributes**, and `cms.extensions._condition_holds` is the
single derivation seam for that claim. The mutant replaces the
seam with a wave-through (`lambda cond, attrs: True`). For each
canonical case (an `equals` condition the subject fails, in
both `segment_match` and `segment_match_counts`) the test
asserts three things: the canonical expectation (no match /
zero matching, from the real seam), that the mutant would NOT
produce that expectation (it matches / counts one), and — via a
literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails.

## Mutation verification (batch drill)

VERIFIED by the builder (2026-11-07), live drill performed on
the real implementation. The equality branch of
`_condition_holds` in `src/cms/extensions.py` (the line
`return attributes.get(key) == condition["value"]`, occurring
exactly once, count asserted before patching) was patched to
`return True`, so an `equals` condition holds even when the
subject's recorded value differs. The full suite ran: **135
tests ran, exactly 5 failed** —

- `test_gaps_batch.TestPersonalization.test_match_derived_at_read`
- `test_gaps_batch.TestPersonalization.test_match_counts_derived`
- `test_gaps_batch.TestPersonalization.test_rule_view_derives_and_serves_nothing`
- `test_gaps_batch.TestConditionNegativeControl.test_equals_condition_canonical_but_mutant_not`
- `test_gaps_batch.TestConditionNegativeControl.test_counts_canonical_but_mutant_not`

No core-suite test failed under the mutant (the core does not
call the extension seam). `extensions.py` was then restored
from the pre-mutation copy (`../scratch/extensions.py.premutation`)
and verified **SHA-256 identical**
(`78797954a15a533ff6e228c08bd47ad9ab7c589ea0572b6dba5e0226119d89bc`,
recorded in `../scratch/extensions.py.sha256`) and the suite
re-run: **135 tests, OK**. Raw drill output:
`../scratch/gaps_batch_mutation_run.txt`. The suite catches
this defect class; the negative control is not decorative.
