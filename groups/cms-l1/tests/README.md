# Tests — Content Management System (CMS) L1 merged build (Group 24)

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

**Reuse:** this suite is the shipped Group 20 (CMS L2) suite, reused
in full — this project's own Apache-2.0 code. 16 of 18 files in this
directory are byte-identical to Group 20's (SHA-256 verified; record
in `../scratch/reuse-note.md`); the exceptions are
`cms_helpers.py` (docstring wording only) and this README. No
assertion was changed. What the suite verifies is the reused
implementation; the **baseline claims** it is read against at this
tier are this group's own (Low / FAR 52.204-21, in
`../UNION-SPEC.md`) — Group 20's Moderate framing is not inherited.

## Run

```bash
cd groups/cms-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 98 tests
```

Status at delivery: **98 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

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
| `test_tags_metadata.py` | Tags & metadata / metadata_taxonomy — `tag-` ids, global slug uniqueness and validation, tag write roles, items linking tags at create and update (reflected in revisions), metadata round trip / default / replacement / copy semantics. This is this group's one tagged claim family (OCLC) |
| `test_search.py` | Search / search_discovery — items by title/slug/body/metadata value, assets by filename/kind, sites by name/slug, tags by name/slug, result keys exactly `{items, assets, sites, tags}`, case-insensitive, literal (regex metacharacters neither match nor explode), blank query → all empty, non-string → `ValidationError` |
| `test_report.py` | Reporting / reporting — empty report (all statuses 0, 4 built-in types), counts by status/site/type, publish-record count, assets by kind (zeros included), totals, determinism and read access for any role |
| `test_service.py` | REST API — live HTTP server: health (no auth), 401 unknown user + role mismatch, 403 viewer site create (denied attempt audited `<action>:denied`), full flow (site → section → types → tag → item by dave → PATCH update → revisions → submit → approve-by-author 403 → approve by carol → windowed publish by bob → publishes list → item window at pinned `now` → asset with computed checksum → search → report → archive → audit as alice; audit as non-admin → 403), return flow over HTTP, 400/404 error envelopes |
| `test_main_cli.py` | `python -m cms serve --port <free>` subprocess (PYTHONPATH=src), waits for health, answers alice on `/audit` and erin/bob on `/sites`, terminates |
| `test_negative_control.py` | Negative control (below) |
| `cms_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, PUBLISHER=bob/publisher, EDITOR=carol/editor, AUTHOR=dave/author, VIEWER=erin/viewer), `USERS` registry, `fresh_store()`, `make_store()` (canonical site "Main Site" by PUBLISHER + section "News" by EDITOR), `make_item()`, `drive_to_approved()` and `drive_to_published()` |
| `store.py.premutation` | Pre-mutation copy of `../src/cms/store.py`, inherited from Group 20 with the reuse (the store is byte-identical, so the copy is this tree's valid restore point as well; this group's own drill used `../scratch/store.py.pristine`) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `CmsStore` subclass (`MutantCmsStore`) whose
`_check_approver_not_author` is a no-op — the separation-of-duties
check is skipped. The traced claim, named in the module's docstrings,
is that **an item is never approved or returned by its own author**
(sibling claim family authoring_editing; control family AC-5,
separation of duties — a Low-baseline selection at this tier). For
each canonical case (author-approve, author-return) the test asserts
three things: the canonical expectation (`PermissionDenied` from the
real implementation, the item staying `"in_review"`), that the mutant
would NOT produce that expectation (it approves / returns), and — via
a literal `assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails.

One isolation detail, documented in the test itself: the cases use an
**editor-authored** item reviewed by that same editor (carol), so the
reviewer's role already holds `item_review` and
`_check_approver_not_author` — which compares names — is the only gate
that can deny. A third test confirms a *different* reviewer
(publisher bob) approving carol's item succeeds on the real store, so
the denial is the author check firing rather than a blanket refusal.

Mutation verification: VERIFIED on this tree (2026-10-25). The
author-approval guard in `CmsStore._check_approver_not_author`
(`src/cms/store.py`) was patched to a no-op (`return None`), the exact
live counterpart of the mutant in `test_negative_control.py`, so an
item's author could approve and return their own item. The full suite
was run: **98 tests ran, 4 failed** —

- `test_lifecycle.TestLifecycle.test_author_cannot_approve_own_item_store_level`
- `test_lifecycle.TestLifecycle.test_editor_who_authored_cannot_review_own`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_approve_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_return_denied_canonical_but_mutant_returns`

— the same four failures as Group 20's drill on its own tree (full
output in `../scratch/mutation-run.txt`). `store.py` was then
restored from the pre-mutation copy (`../scratch/store.py.pristine`,
SHA-256
`e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1`,
verified identical to the pre-mutation hash, to
`tests/store.py.premutation`, and to Group 20's original file) and
the suite re-run: **98 tests, OK**. The suite catches this defect
class; the negative control is not decorative.
