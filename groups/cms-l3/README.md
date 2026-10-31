# Content Management System (CMS) L3-adjacent — merged build (Operation DeadRamp, Phase 2, Singleton / Group 39)

This is the merged, clean-room implementation of the **Content
Management System (CMS) L3-adjacent singleton group**: **1 fork**
from the FedRAMP Marketplace at the group's tier (CMMC L3-adjacent,
equivalent to FedRAMP High), built as one open-source service from
the group's union contract (`UNION-SPEC.md`).

The 1 fork: **Iron Mountain InSight for Government** (Iron
Mountain) — FedRAMP Certified, SaaS, Government Community Cloud.

It is a cross-tier merge under the Merge Rule: Group 20's CMS L2
build (the union of the 4 Moderate forks) carried up whole and
uplifted to the High baseline, merged with this group's one High
fork. It was written from that contract only: original code, no
vendor code, assets, or branding from any offering. Python 3,
**standard library only**, no external dependencies.

**Spec honesty up front:** the fork's public description is a single
sentence and tags **0 claims** under Group 20's taxonomy applied
verbatim (see `UNION-SPEC.md` and `scratch/ARTIFACTS.md` for the six
itemized near-misses). The 12-function core stands on an explicit
core-boundary decision recorded in the spec (the Merge Rule carries
the L2 union upward whole; a wording artifact is not a downgrade).
The fork's own engines — ML/AI classification, extraction, and
enrichment over physical and digital content — are Extended gaps,
named in the spec, not built here.

## The substrate (Group 20's 12 functions, at the High baseline)

1. **Sites & sections** — sites (`site-`) with globally unique
   slugs, and sections (`sec-`) inside a site; a section's parent
   must belong to the same site, and section slugs are unique per
   site.
2. **Content types** — custom types (`ct-`) plus the built-in types
   `page` / `article` / `document` / `collection`, pre-registered
   with fixed readable ids (`ct-page`, `ct-article`, `ct-document`,
   `ct-collection`, `created_by` `"system"`).
3. **Content items & authoring** — items (`ci-`) in a site, of a
   type, optionally in a section, with metadata and tag links,
   starting as `draft`. Creation mints revision 1 (`rev-`); every
   edit mints a new revision.
4. **Editorial lifecycle** — `submit` (`draft` → `in_review`),
   `approve` (`in_review` → `approved`), `return` (`in_review` →
   `draft`, with a note). Separation of duties: the
   approver/returner is never the item's author, enforced in
   `CmsStore._check_approver_not_author` (the negative-control seam).
5. **Publishing** — `publish` (`approved` → `published`) mints a
   publish record (`pub-`) with optional `publish_at` / `expire_at`;
   `archive` (`published` → `archived`). The window state
   (`live` / `scheduled` / `expired` / `None`) is **derived** from
   stored facts, computed against a `now` parameter, never stored.
6. **Assets** — asset registration (`asset-`) doubles as the
   ingestion record: filename, kind, byte size, MIME type and
   SHA-256 checksum. Bytes are hashed when supplied and then
   discarded; only metadata + checksum are stored.
7. **Tags** — tags (`tag-`) with globally unique slugs; items link
   tags at create and update time.
8. **Search** — literal, case-insensitive substring search over
   item title/slug/body/metadata values, asset filename/kind, site
   name/slug and tag name/slug. Search is audited.
9. **Reporting** — a registry report computed deterministically
   from registry state: items by status / site / type,
   publish-record count, assets by kind, totals.
10. **REST API** — the full surface over HTTP (table below),
    house auth convention (X-User / X-Role against the demo
    registry; 401 unknown/mismatched, 403 permission, denied
    attempts audited).
11. **RBAC** — roles `admin`, `publisher`, `editor`, `author`,
    `viewer` with the permission matrix below, enforced before any
    state change or id allocation — plus the **[L3] `auditor`**
    role holding `audit_read` only (AC-5).
12. **Audit log** — append-only, JSONL-persistable, records every
    mutation, every search, and every denied attempt
    (`"<action>:denied"`), **[L3] hash-chained and tamper-evident**
    (AU-9), with chain verification, audit query/reduction (AU-7),
    and fail-closed write behavior (AU-5). No mutation or deletion
    API for audit entries.

### High-baseline uplifts [L3]

| Uplift | Control | What changed vs Group 20 |
|---|---|---|
| Hash-chained audit (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` localizes the first bad entry; `GET /audit/verify` | AU-9, AU-3 | `audit.py` replaced |
| Fail-closed audit writes: `record()` rolls back + raises `AuditWriteError`; every mutating store method runs inside the `_atomic` snapshot guard (whole operation rolls back, no id consumed); service answers 500 | AU-5 | `errors.py`, `audit.py`, `store.py`, `service.py` |
| Audit reduction: `AuditLog.query(actor, action, target, since, until)` + `GET /audit` filter parameters | AU-7 | `audit.py`, `service.py` |
| Logon lockout: per-username consecutive-failure tracking, lock at 3 failures for 300 s (configurable), locked attempts 403 + audited `auth:locked`, success resets | AC-7 | `service.py`, `__main__.py` flags |
| Auditor role `dana` = {`audit_read`} only | AC-5 | `access.py`, demo registry |

### Permission matrix (operational roles, as Group 20; auditor added)

| Action | admin | publisher | editor | author | viewer | auditor |
|---|---|---|---|---|---|---|
| Reads (`site_read`, `section_read`, `type_read`, `item_read`, `asset_read`, `tag_read`, `search`, `report_read`) | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `audit_read` | ✓ | — | — | — | — | ✓ |
| `site_write`, `type_write`, `item_publish`, `item_archive` | ✓ | ✓ | — | — | — | — |
| `section_write`, `tag_write`, `item_review` | ✓ | ✓ | ✓ | — | — | — |
| `item_create`, `item_edit`, `item_submit`, `asset_write` | ✓ | ✓ | ✓ | ✓ | — | — |

Author ownership is additional: an author may edit or submit only
their own items, and the approver/returner of an item is never its
author (any role). Plain-string actors carry identity but no role;
the service layer enforces in that case (and always passes User
objects).

## Run

```bash
cd groups/cms-l3
PYTHONPATH=src python3 -m cms serve            # http://127.0.0.1:8793
PYTHONPATH=src python3 -m cms serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cms serve --max-failed-logins 3 --lockout-seconds 300   # AC-7 [L3]
PYTHONPATH=src python3 -m cms serve --certfile cert.pem --keyfile key.pem         # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization):

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | publisher | all reads except the audit log; all writes incl. publish/archive |
| `carol` | editor | reads, sections, item create/edit/submit/review, assets, tags |
| `dave` | author | reads, item create/edit/submit (own items only), assets |
| `erin` | viewer | reads only (except the audit log) |
| `dana` | auditor **[L3]** | `audit_read` only: `GET /audit`, `GET /audit/verify`; nothing else |

## Endpoints

Group 20's 29 endpoint patterns (30 method+path combinations),
plus **[L3]** `GET /audit/verify`:

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` (`?actor=&action=&target=&since=&until=`) **[L3 filters]** | audit_read | admin/auditor; `{"entries": [...]}` |
| `GET /audit/verify` **[L3]** | audit_read | `{ok, entries, first_bad_index}` (AU-9) |
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
| `GET /assets` (`?site_id=`) · `POST /assets` | asset_read / asset_write | create → 201 |
| `GET /assets/{id}` | asset_read | |
| `GET /tags` · `POST /tags` | tag_read / tag_write | create → 201 |
| `GET /tags/{id}` | tag_read | |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission (and locked accounts, AC-7), 404
not found, **[L3]** 500 audit write failure (AU-5, fail closed).
Denied attempts are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/cms-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 146 tests
```

**146 tests, all passing**: 98 inherited from Group 20 (with the
adaptations listed in `tests/README.md`), 4 auditor tests added to
the inherited access suite, and 44 new High-uplift tests. Two
mutation-verified negative controls: disabling the author-approval
guard in the real store makes exactly 4 tests fail, and a mutated
audit entry makes `verify_chain()` report `(False, 1)` (details in
`tests/README.md`).

## Honesty

- The build implements the content-management substrate on an
  explicit core-boundary decision (see `UNION-SPEC.md`): the sole
  fork's description tags 0 claims under the verbatim taxonomy, and
  the substrate is carried up whole under the Merge Rule rather
  than rounded up from the fork's prose. The fork's actual product
  depth — ML/AI classification, extraction, and enrichment engines,
  physical-content digitization, the hosted platform runtime — is
  **not** in this build; each is a named Extended gap.
- No rendering or theming engine, no rich-text / WYSIWYG editor,
  no workflow or notification engine, no media storage or
  transcoding, no search index, no hosting or delivery network.
- Publishing is registry state plus a derived window: the build
  records that an item was published, by whom, and for what window,
  and computes `live` / `scheduled` / `expired` from those facts.
  It does not render or serve the published content anywhere.
- Assets are registration records (checksum + metadata), not
  stored files: bytes are hashed when supplied, then discarded.
- Demo identities are hooks, not an identity provider. IA-2 (and
  MFA, IA-2(1)/(2)/IA-5) stays with the embedding organization.
  Encryption is TLS when a certificate is configured; encryption
  at rest (SC-28) and FIPS-validated cryptography (SC-13) are
  deployment-layer / platform properties, gap-listed and **not
  claimed**. Audit retention (AU-11) and session lock/termination
  (AC-11/AC-12) are likewise gap-listed in `UNION-SPEC.md`.
- Claims discipline: every function above traces to Group 20's
  union (carried under the recorded boundary decision) or to the
  High/L3-adjacent control families in `UNION-SPEC.md`. This build
  is not a FedRAMP authorization and confers no CMMC certification.
