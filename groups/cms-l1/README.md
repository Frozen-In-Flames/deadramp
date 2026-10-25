# Content Management System (CMS) L1 — merged build (Operation DeadRamp, Phase 2, Group 24)

This is the merged, clean-room implementation of the **Content
Management System (CMS) L1** sibling group: **2 forks / vendor
platforms** from the FedRAMP Marketplace that share the same
function (Content Management System) and the same trust tier
(CMMC L1, the FedRAMP Low / LI-SaaS family), built as one
open-source service from the group's union contract
(`UNION-SPEC.md`).

The 2 forks: **WorldShare Management Services** (OCLC
Incorporated, **LI-SaaS**) — a cloud-based library services
platform built on WorldCat — and **TimeLooper Inc.** (TimeLooper
Xplore, **Low**) — a multi-tenant content management platform for
publishing digital content to mobile applications. Each fork's
actual impact level is recorded in `specs/specs.json`.

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

**Reuse, stated plainly:** the implementation is the shipped
Group 20 (CMS L2) code, reused in full — this project's own
Apache-2.0 code; 23 of 25 copied files are byte-identical to
Group 20's (SHA-256 verified, recorded in
`scratch/reuse-note.md`), and the two differing files are
documentation wording only. The code is functionally tier-neutral
(no tier/baseline strings anywhere in `src/`). **The baseline
claim is new, not reused:** Group 20's Moderate / NIST SP 800-171
framing does not carry over. This group's baseline is the
**Low baseline** — see "Baseline" below.

## The 9 substrate functions

1. **Sites & sections** — sites (`site-`) with globally unique
   slugs, and sections (`sec-`) inside a site; a section's parent
   must belong to the same site, and section slugs are unique
   per site.
2. **Content types** — custom types (`ct-`) plus the built-in
   types `page` / `article` / `document` / `collection`,
   pre-registered at store init with fixed readable ids
   (`ct-page`, `ct-article`, `ct-document`, `ct-collection`,
   `created_by` `"system"`); the built-ins do not consume the
   custom-type counter, so the first custom type is `ct-1`.
3. **Content items & authoring** — items (`ci-`) in a site, of a
   type, optionally in a section, with metadata and tag links,
   starting as `draft` with `author` set to the creator. Creation
   mints revision 1 (`rev-`); every edit mints a new revision
   capturing the title/body/metadata snapshot. Editing rule, kept
   simple: edits are allowed in `draft` (an author only on their
   own items), and in `in_review` only for admin / publisher /
   editor.
4. **Editorial lifecycle** — `submit` (`draft` → `in_review`),
   `approve` (`in_review` → `approved`), `return` (`in_review` →
   `draft`, with a note). Invalid transitions raise a validation
   error. Separation of duties: the approver/returner is never
   the item's author, enforced in the single named method
   `CmsStore._check_approver_not_author` (the negative-control
   seam).
5. **Publishing** — `publish` (`approved` → `published`) mints a
   publish record (`pub-`: item, publisher, timestamps, optional
   `publish_at` / `expire_at`; `expire_at` must be after
   `publish_at` when both are given), and `archive` (`published`
   → `archived`). The window state (`live` / `scheduled` /
   `expired` / `None`) and `is_live` on item reads are **derived**
   from stored facts only, computed against a `now` parameter,
   never stored.
6. **Assets** — asset registration (`asset-`) doubles as the
   ingestion record: filename, kind (`document` / `image` /
   `video` / `audio` / `dataset` / `other`), byte size, MIME type
   and checksum. When bytes are supplied their SHA-256 is
   computed and must match a supplied checksum; only the checksum
   and metadata are stored, never the bytes.
7. **Tags** — tags (`tag-`) with globally unique slugs; items
   link tags at create and update time, and unknown tag ids are
   rejected.
8. **Search** — literal, case-insensitive substring search over
   item title/slug/body/metadata values, asset filename/kind,
   site name/slug and tag name/slug, returning
   `{"items": [...], "assets": [...], "sites": [...], "tags": [...]}`.
   Search is audited.
9. **Reporting** — a registry report computed deterministically
   from registry state: items by status / site / type,
   publish-record count, assets by kind, and total counts.

Plus, across all of the above: **RBAC** — roles `admin`,
`publisher`, `editor`, `author`, `viewer` with the permission
matrix below, enforced before any state change or id allocation
(a failed operation consumes no id) — and an **append-only audit
log**: every mutation, every search, and every denied attempt
(recorded as `"<action>:denied"`), with actor, action, target
and UTC timestamp, and optional JSONL persistence. There is no
mutation or deletion API for audit entries.

Slugs are non-empty, lowercase alphanumerics and hyphens. Slug
uniqueness is per site for items, global for sites and tags.
Timestamps are UTC ISO-8601. Malformed input is rejected with a
validation error and leaves the store completely unchanged.

### Permission matrix

| Action | admin | publisher | editor | author | viewer |
|---|---|---|---|---|---|
| Reads (`site_read`, `section_read`, `type_read`, `item_read`, `asset_read`, `tag_read`, `search`, `report_read`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `audit_read` | ✓ | — | — | — | — |
| `site_write`, `type_write`, `item_publish`, `item_archive` | ✓ | ✓ | — | — | — |
| `section_write`, `tag_write`, `item_review` | ✓ | ✓ | ✓ | — | — |
| `item_create`, `item_edit`, `item_submit`, `asset_write` | ✓ | ✓ | ✓ | ✓ | — |

Author ownership is additional to the matrix: an author may edit
or submit only items where `item.author` is their own name, and
the approver/returner of an item is never its author (any role).

Plain-string actors carry identity but no role: the store enforces
only for User-like actors, and the service layer — which knows
the role registry — is responsible for enforcement in that case
(and always passes User objects).

## Baseline (Low / L1)

The union of this group's parent baselines is the **NIST SP
800-53 Rev. 5 Low** baseline: TimeLooper carries FedRAMP Low, and
OCLC's LI-SaaS is FedRAMP's tailored subset of Low, which adds
nothing beyond it. Low ⇔ **CMMC L1** (the FAR 52.204-21 practice
set), per `../../crosswalk.md`. Feature→control-family
traceability is in `UNION-SPEC.md`, written for this tier.
Precision notes, stated there and repeated here because they are
the point of the L1 build: audit traces to AU-2/AU-3 **on the
FedRAMP Low side only** (FAR 52.204-21 carries no audit practice
for system audit records, so no audit claim is made on the CMMC
side, and Group 20's Moderate citations AU-6/AU-9 were not
imported); the SHA-256 asset checksums are an implementation
integrity property (the Moderate selection SI-7 is not a Low
selection and is not claimed); the Moderate/High apparatus is not
inherited downward. This mapping is a planning/matching
equivalence only — FedRAMP authorizes products, CMMC certifies
organizations; the build is neither an authorization nor a
certification.

## Run

```bash
cd groups/cms-l1
PYTHONPATH=src python3 -m cms serve            # http://127.0.0.1:8793
PYTHONPATH=src python3 -m cms serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cms serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | publisher | all reads except the audit log; all writes incl. publish/archive |
| `carol` | editor | reads, sections, item create/edit/submit/review, assets, tags |
| `dave` | author | reads, item create/edit/submit (own items only), assets |
| `erin` | viewer | reads only (except the audit log) |

## Endpoints

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

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/cms-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 98 tests
```

**98 tests, all passing**, including the mutation-verified
negative control: disabling the author-approval guard in the real
store makes exactly 4 tests fail (see `tests/README.md` for the
drill record, reproduced on this tree).

## Honesty

- The build implements the content-management substrate the
  category shares. The engines and verticals are not in it: no
  rendering or theming engine, no rich-text / WYSIWYG editor, no
  workflow or notification engine, no media storage or
  transcoding, no search index, no hosting or delivery network —
  and neither of this group's verticals: no library ILS modules
  (OCLC) and no mobile application delivery (TimeLooper). Each is
  a named gap in `UNION-SPEC.md` for the final batch, not a
  claimed function.
- Claims discipline, stated at full strength for this group:
  applying Group 20's taxonomy verbatim, the two descriptions
  tag **exactly one claim** (OCLC's metadata & taxonomy family);
  TimeLooper's sheet tags zero, because its prose says "content
  management **platform**", "administrative interfaces", and
  "delivery" where the taxonomy keys on "system", "tools", and
  "delivery system". Those near-misses are recorded in
  `scratch/ARTIFACTS.md`, the taxonomy was **not** re-tuned, and
  the twelve core functions stand under the core-boundary
  decision recorded in `UNION-SPEC.md`: they define the CMS
  category and both products presuppose them. Counts are a
  floor, reported, not padded.
- Publishing is registry state plus a derived window: the build
  records that an item was published, by whom, and for what
  window, and computes `live` / `scheduled` / `expired` from
  those facts. It does not render or serve the published content
  anywhere.
- Assets are registration records (checksum + metadata), not
  stored files: the bytes are hashed when supplied and then
  discarded.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization. Encryption is TLS when
  a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment (TimeLooper claims multi-tenant in prose;
  tenancy isolation is deployment-layer).
