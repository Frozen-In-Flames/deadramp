# Tests — Content Management System (CMS) L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/cms-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 108 tests
```

Status at delivery: **98 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

Status after the remainder addition (unit `addition:cms-l2`):
**108 tests, OK** — the 98 above plus 10 in `test_additions.py`
(see the addition section at the end of this file). The core is
unchanged; the signature drill was re-run in this tree and failed
exactly 5 tests under mutation (record below).

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
| `test_additions.py` | Remainder addition (unit `addition:cms-l2`) — spec integrity for the appended Iron Mountain InSight sheet (count/order, membership vs `remainder.json`, the literal **zero-claim** table pinned, group totals 19 claims / exactly 1 zero-claim fork, tier fields, verbatim description, census citation = the whole description verifying and tagging nothing, near-miss token pins) plus 2 substrate cases (content record with classification/extraction metadata + tag and a physical-content asset registration found by metadata search; editorial lifecycle with the editor-author approval denial) |
| `test_negative_control.py` | Negative control (below) |
| `cms_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, PUBLISHER=bob/publisher, EDITOR=carol/editor, AUTHOR=dave/author, VIEWER=erin/viewer), `USERS` registry, `fresh_store()`, `make_store()` (canonical site "Main Site" by PUBLISHER + section "News" by EDITOR), `make_item()`, `drive_to_approved()` and `drive_to_published()` |
| `store.py.premutation` | Pre-mutation copy of `../src/cms/store.py`, kept for the negative-control drill restore/hash check below (kept here because this group's `scratch/` is owned by a sibling worker) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `CmsStore` subclass (`MutantCmsStore`) whose
`_check_approver_not_author` is a no-op — the separation-of-duties
check is skipped. The traced claim, named in the module's docstrings,
is that **an item is never approved or returned by its own author**
(sibling claim family authoring_editing; control family AC-5,
separation of duties). For each canonical case (author-approve,
author-return) the test asserts three things: the canonical
expectation (`PermissionDenied` from the real implementation, the
item staying `"in_review"`), that the mutant would NOT produce that
expectation (it approves / returns), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails.

One isolation detail, documented in the test itself: the cases use an
**editor-authored** item reviewed by that same editor (carol), so the
reviewer's role already holds `item_review` and
`_check_approver_not_author` — which compares names — is the only gate
that can deny. A third test confirms a *different* reviewer
(publisher bob) approving carol's item succeeds on the real store, so
the denial is the author check firing rather than a blanket refusal.

Mutation verification: VERIFIED by the build worker (2026-10-25). The
author-approval guard in `CmsStore._check_approver_not_author`
(`src/cms/store.py`) was patched to a no-op (`return None`), the exact
live counterpart of the mutant in `test_negative_control.py`, so an
item's author could approve and return their own item. The full suite
was run: **98 tests ran, 4 failed** —

- `test_lifecycle.TestLifecycle.test_author_cannot_approve_own_item_store_level`
- `test_lifecycle.TestLifecycle.test_editor_who_authored_cannot_review_own`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_approve_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_return_denied_canonical_but_mutant_returns`

`store.py` was then restored from the pre-mutation copy kept in this
directory (`tests/store.py.premutation`, SHA-256
`e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1`,
verified identical to the pre-mutation hash) and the suite re-run:
**98 tests, OK**. The suite catches this defect class; the negative
control is not decorative.

## Remainder addition — drill re-run (unit addition:cms-l2)

The addition (Iron Mountain InSight, `FR2031155471`) claims zero
families and changes no core code, so the group's signature drill
was re-run in this tree at addition time. The guard body in
`CmsStore._check_approver_not_author` (`src/cms/store.py`) was
patched to a no-op (`return None`) — the guard line
`if actor_name(actor) == item["author"]:` occurs exactly once in
the file (count asserted before patching), so the mutant was
never unscoped — and the full suite ran: **108 tests ran, exactly
5 failed** —

- `test_additions.TestAdditionSubstrateCases.test_insight_item_lifecycle_author_guard`
- `test_lifecycle.TestLifecycle.test_author_cannot_approve_own_item_store_level`
- `test_lifecycle.TestLifecycle.test_editor_who_authored_cannot_review_own`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_approve_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_return_denied_canonical_but_mutant_returns`

— the shipped drill's 4 plus exactly 1 from the new additions
module (the InSight lifecycle author-guard case), tripping as
designed. `store.py` was restored from the pre-mutation copy
(`scratch/store.py.premutation-additions`) and verified SHA-256
`e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1`,
identical to the shipped hash; the suite re-ran: **108 tests,
OK**. The raw failure list is in
`scratch/additions_mutation_run.txt`.
