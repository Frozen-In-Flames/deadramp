# Content Management System (CMS) — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Content
Management System (CMS) — census unit `untiered:Content
Management System (CMS)` in `../../remainder.json`. **This is an
untiered set, and that means something specific:** every member's
FedRAMP impact level is **Unknown** in the source dataset. The
source publishes no baseline for these offerings, so **tier stays
null**: no tier is assigned, no CMMC equivalence is drawn, and
this build asserts **no control baseline**. Per PIPELINE.md,
untiered offerings "build to their documented control claims;
tier stays null in the registry until the source publishes a
baseline." The union contract is [`UNION-SPEC.md`](UNION-SPEC.md);
per-fork spec sheets are in [`specs/specs.json`](specs/specs.json),
each recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests.

The 2 forks were spec'd under the category's existing 13-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding CMS L2 group's original
shipped claim tables exactly — **4 of 4 forks, 19 of 19 claims,
deep-equal** — before tagging this set. Result here: **1 claim**
across the set, **1 of 2 forks claiming at least one**; the
zero-claim fork (FR2001462460, Nintex Drawloop DocGen) is recorded
under Named absences in the union spec, not hidden or repaired.
The category's "no fork has zero claims" floor — already broken
at the tiered L2 addition — falls here too, and that is recorded
rather than fixed by re-tuning.

The build implements the category's **twelve-function substrate**
— the content-registry machinery every sibling's output
presupposes — carried **byte-identical** from the founding CMS L2
build (`../cms-l2/src/cms/`, 7 of 7 modules; SHA-256 accounting
below). The substrate is tier-independent records code: the
founding source contains no tier or baseline machinery at all
(verified by scan), so there was nothing tier-shaped to strip and
no tier text to re-anchor. Exactly **one** of the twelve functions
is claim-supported in this set (metadata search & discovery, via
Liferay's `search_discovery` claim at catalogue weight); the other
eleven are **carried, not claimed**, stated plainly in the union
spec's core-boundary decision.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2701857792 | Liferay, Inc. | Liferay SaaS | 1 |
| FR2001462460 | Nintex | Nintex Drawloop DocGen | 0 |

In `forks.json` the set is mixed as filed: Liferay is filed under
Collaboration (its source business categories list Collaboration,
Content Management System (CMS), Customer Service, Development
Tools, Marketing & Sales), and Nintex is filed "Uncategorized
(none in source)" with no business categories at all; the census
assigned both to this category from their own descriptions, and
the spec sheets record the assignment. Authorization statuses as
recorded are Initial Implementation (Liferay) and FedRAMP In
Process (Nintex) — a status is record data, not a claim.

## The 12 core functions

1. **Site & section structure registry** — sites (`site-`) and
   sections (`sec-`) as structure records; site slugs globally
   unique, section slugs unique per site, a section's parent must
   belong to the same site.
2. **Content type registry** — built-in types `page` / `article` /
   `document` / `collection` pre-registered with fixed ids
   (`ct-page` …), custom types definable (`ct-`).
3. **Content registry & authoring** — items (`ci-`) created and
   updated by authors with title, slug, body, metadata, tags;
   every content edit mints a revision record (`rev-`) (registry
   mechanics).
4. **Editorial lifecycle** — status draft → in_review → approved
   → published → archived (return: in_review → draft, with a
   note), transitions role-gated; the approver/returner is never
   the item's author (separation of duties, enforced in
   `CmsStore._check_approver_not_author`).
5. **Publishing records & windows** — publishing mints a publish
   record (`pub-`) with optional publish_at/expire_at window;
   the window state (`live` / `scheduled` / `expired` / `None`)
   and `is_live` are **derived** at read time from stored facts,
   never stored.
6. **Media & document asset registry** — assets (`asset-`) with
   kind, filename, byte size, MIME type, SHA-256 checksum;
   registration is the ingestion record. The registry holds
   metadata + checksum, **never file bytes** (bytes are hashed
   when supplied and discarded).
7. **Taxonomy & metadata registry** — tags (`tag-`) and per-item
   metadata key/values.
8. **Metadata search & discovery** — literal, case-insensitive
   substring search over items, assets, sites, and tags,
   returning `{"items": [...], "assets": [...], "sites": [...],
   "tags": [...]}`. Search is audited. *(The one claim-supported
   function in this set.)*
9. **Registry reporting** — computed views over the registry:
   items by status/site/type, publish-record count, assets by
   kind, totals; deterministic, computed from recorded facts.
10. **REST API** — the full surface over HTTP, house auth
    convention (X-User / X-Role against the demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
11. **RBAC** — roles `admin`, `publisher`, `editor`, `author`,
    `viewer` with the permission matrix below, enforced in the
    store before any state change or id allocation and again at
    the service layer.
12. **Audit log** — append-only, JSONL-persistable; records every
    mutation, every search, and every denied attempt
    (`<action>:denied`) with actor, action, target, and UTC
    timestamp. There is no mutation or deletion API for entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Slugs are non-empty, lowercase alphanumerics and
hyphens. All timestamps are UTC ISO-8601.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m cms serve            # http://127.0.0.1:8793
PYTHONPATH=src python3 -m cms serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cms serve --certfile cert.pem --keyfile key.pem   # TLS
```

## Demo users, roles, and permissions

The server ships five documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | publisher | all reads except the audit log; all writes incl. publish/archive |
| `carol` | editor | reads, sections, item create/edit/submit/review, assets, tags |
| `dave` | author | reads, item create/edit/submit (own items only), assets |
| `erin` | viewer | reads only (except the audit log) |

Author ownership is additional to the matrix: an author may edit
or submit only items where `item.author` is their own name, and
the approver/returner of an item is never its author (any role).
A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client.

## API endpoints

29 endpoint patterns (30 method+path combinations, counting both
the `PATCH` and `POST` forms of the item update):

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | search | `{"items": [...], "assets": [...], "sites": [...], "tags": [...]}` |
| `GET /report` | report_read | registry report |
| `GET /publishes` (`?item_id=`) | item_read | `{"publishes": [...]}` |
| `GET /sites` · `POST /sites` | site_read / site_write | create → 201 |
| `GET /sites/{id}` | site_read | |
| `GET /sites/{id}/sections` · `POST` | section_read / section_write | create → 201 |
| `GET /types` · `POST /types` | type_read / type_write | create → 201 |
| `GET /types/{id}` | type_read | |
| `GET /items` (`?site_id=`, `?status=`, `?now=`) · `POST /items` | item_read / item_create | create → 201 |
| `GET /items/{id}` (`?now=`) | item_read | includes derived `window_state` / `is_live` |
| `PATCH /items/{id}` · `POST /items/{id}` | item_edit | update; mints a revision |
| `GET /items/{id}/revisions` | item_read | `{"revisions": [...]}` |
| `POST /items/{id}/submit` | item_submit | draft → in_review |
| `POST /items/{id}/approve` | item_review | in_review → approved; never the author |
| `POST /items/{id}/return` | item_review | in_review → draft; body `{"note": ...}` |
| `POST /items/{id}/publish` | item_publish | approved → published; body may carry `publish_at` / `expire_at` |
| `POST /items/{id}/archive` | item_archive | published → archived |
| `GET /assets` (`?site_id=`) · `POST /assets` | asset_read / asset_write | create → 201; body may carry `data` / `data_base64` for checksum computation |
| `GET /assets/{id}` | asset_read | |
| `GET /tags` · `POST /tags` | tag_read / tag_write | create → 201 |
| `GET /tags/{id}` | tag_read | |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**109 tests, OK** at delivery: the founding group's 98-test core
suite carried with the code, plus 11 spec tests pinning this set
(exactly 2 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; registry fields and
business categories as in source; descriptions equal to the
census record; the literal claim table — 1 claim total, Liferay
`search_discovery` with founding-rule truncated evidence, Nintex
zero-claim; the near-miss tokens earning nothing; 3 of 3 census
citations verifying). The founding group's signature drill was
re-run in this tree: patching the author-approval guard
`CmsStore._check_approver_not_author` to a no-op makes **exactly
4 tests fail** — the founding drill's identical set — and the
store was restored and SHA-256 verified (see `tests/README.md`).
A live HTTP smoke also passed (full flow; both author-approval
denials returned 403; the published item read back with derived
`window_state: live`; the viewer write was denied and the denial
appears in the audit log; record in `tests/README.md`).

## Byte-identity accounting

`src/cms/` is carried from the founding group
`../cms-l2/src/cms/` — **7 of 7 modules byte-identical**,
SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `fccc5d81560df8737e494a1d30bfab22ebccef87bacd916c733b78ee6873e4da` |
| `__main__.py` | `e70fdb32d7f88a428067c481e0eba9942d004811d0928ff37bc9536225457e19` |
| `access.py` | `245350b01216ab883bfe502ddec038063e7027696fd79fb4efaf920a86563088` |
| `audit.py` | `9bd4ecc63d7997a83c3ded5d86ab75e6e5dec5cce514f784399dc61508a0f762` |
| `errors.py` | `9c0858c58ddebad2041efdca7451e94038061a99a9681f4d49564380798d4fe3` |
| `service.py` | `e5f998f13a52fe01874a5cd58823c8fdd49447fa536a549d5bffff0f84436f6c` |
| `store.py` | `e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1` |

The test suite is likewise carried (the founding suite minus its
additions module, which pins a different census unit), with one
labeling fix in `tests/cms_helpers.py` (its docstring now names
this untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

Documented by at least one fork in the set — both at **prose
weight** (the sentences carry control language, but the
taxonomy's `access_administration` family did not fire on them;
documenting the language converts nothing into a taxonomy
claim):

- **Access control (AC)** — Liferay SaaS: "granular role-based
  permissions", and "permission-controlled access to documents
  and digital assets".
- **Identification & authentication (IA)** — Liferay SaaS:
  "single sign-on via SAML 2.0 and OpenID Connect" (the fork's
  SSO assertion; the build ships hooks, not an IdP).

Recorded, not documented: Liferay's "operated under Liferay's
SOC 2 Type II–audited security program" is a compliance
assertion about the operator's program (compliance-assertion
weight — it asserts no 800-53 family and no audit-logging
function), and Nintex's "document data is secure and compliant"
is posture prose naming no control or standard.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, AU, CA, CM, CP, IR, MA,
MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control claims** —
is asserted by no description in the set. If the source later
publishes an impact level for either of these offerings, the
tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented
  control language is recorded as *its* claim, never as the
  build's control attainment.
- **One claim supports one function; the rest is carried.** Of
  the twelve substrate functions, only metadata search &
  discovery is claim-supported in this set (Liferay,
  `search_discovery`, catalogue weight). The other eleven are
  the category substrate carried whole — present in the build,
  absent from these forks' claim tables, and stated that way in
  the union spec rather than smoothed over.
- **Extended functions are specified, not implemented.** The
  union spec's gaps name them: enterprise search indexing
  engines (this build's search is literal substring over
  registry metadata); rendering & templating engines and
  visual/WYSIWYG editors; personalization / experience
  optimization; editorial workflow engines beyond lifecycle
  mechanics; document & media versioning depth; document
  generation engines (the zero-claim fork's whole function);
  low-code application builders; identity federation / SSO
  services; multi-site & multilingual operations depth; headless
  delivery & integration engines; CDN and runtime site serving;
  platform hosting itself.
- **Publishing is records plus a derived window.** The build
  records that an item was published, by whom, and for what
  window, and computes `live` / `scheduled` / `expired` from
  those facts. It does not render or serve the published
  content anywhere.
- **Assets are registration records, not stored files.** Bytes
  are hashed when supplied and then discarded; the registry
  holds checksums and metadata only.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  `carol`, `dave`, and `erin` are documented demo identities
  supplied by header; the service enforces the role permission
  matrix on those hooks and ships no identity provider, no
  credential store, and no authentication of its own (IA-2
  stays with the embedding organization, even though a fork
  here documents SSO).
- **Named absences stand.** Twelve of thirteen taxonomy
  families have 0 claimants in this set, and five of the
  founding group's six named absences (editorial workflow,
  versioning, WYSIWYG editing, templating, personalization)
  stand in Liferay's prose as substance without standing as
  claims. Nothing was back-filled to make the set look
  complete.
