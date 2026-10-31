# Union Spec — Content Management System (CMS), CMMC L3-adjacent (DeadRamp Phase 2, Singleton / Group 39)

The merged functional spec for the Content Management System (CMS)
group at the L3-adjacent tier: **1 fork, FedRAMP High** — **Iron
Mountain InSight for Government** (Iron Mountain), FedRAMP
Certified, SaaS, Government Community Cloud — reconciled zero-diff
(`specs/specs.json` ↔ `forks.json` exact on all eight registry
fields; category arithmetic in MAP.md's totals: CMS total **8** =
L2 4 + L1 2 + **L3-adjacent 1 (this group)** + untiered 1; MAP.md's
sibling sections list only groups of size ≥ 2, so this singleton
reconciles by forks.json exactness plus that arithmetic, verified by
`scratch/verify.py`). As a group of one, this fork *is* the group:
its claims are the union, and the merge that produces this build is
the cross-tier merge below.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 20 merged build** (`../cms-l2/`) — itself the union of
   the 4 Content Management System (CMS) L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room content-registry service.
2. This group's **1 High fork**, via the spec sheet in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run by
the coordinator, and both negative controls were mutation-verified
(see Verification).

**Reuse, stated explicitly:** this build reuses Group 20's own
open-source code (Apache-2.0, ours). One module is byte-identical to
Group 20 (`__init__.py`); six are modified for the tier uplift
(`errors.py`, `access.py`, `audit.py`, `store.py`, `service.py`,
`__main__.py`). The uplift analysis below names what the High
baseline demanded beyond the L2 core and what was done about each
item — implemented, or gap-listed by name.

## How functions were counted

The fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was matched against
**Group 20's 13-family taxonomy, verbatim** — same ids, labels, and
matching patterns, in `scratch/extract.py` — so counts are
comparable across the CMS tiers. A family is claimed only when the
offering's own description contains matching text; the matching
sentence is stored in `specs/specs.json` as evidence.

**0 claims survived.** The description is a single sentence (full
text preserved in the spec sheet and in `scratch/ARTIFACTS.md`): a
"content services platform" that "leverages Machine Learning (ML)
and Artificial Intelligence (AI) to automatically classify, extract,
and enrich physical and digital content." Six near-misses are
itemized in `scratch/ARTIFACTS.md` — "content services platform" vs
the content_registry pattern, the SaaS delivery-model prose vs
platform_hosting (Group 20's substrate corrections), classify /
extract / enrich and the ML/AI layer (no CMS family keys on them),
and "digital content" vs the media_assets pattern. The taxonomy was
not re-tuned for this group. The zero is reported, not padded.

## Function ranking — the 1 fork (Group 20 taxonomy, verbatim)

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| — | 0 | Content management & content registry | **Core** — content registry, under the core-boundary decision below |
| — | 0 | Content authoring & editing | **Core** (3), core-boundary |
| — | 0 | Site & section structure | **Core** (1), core-boundary |
| — | 0 | Search & discovery | **Core** — metadata search, core-boundary; indexing engines Extended |
| — | 0 | Metadata & taxonomy/tagging | **Core** (7), core-boundary |
| — | 0 | Ingestion & repository consolidation | **Core** — registration records, core-boundary; bulk ingestion engines Extended |
| — | 0 | Media & document assets | **Core** (6), core-boundary |
| — | 0 | Records & case information management | **Core** — records substrate, core-boundary |
| — | 0 | Reporting & analytics | **Core** — computed views, core-boundary; reporting engines Extended |
| — | 0 | Workflow / BPM automation | Extended — BPM engine (carried from the Group 20 union at 0 claims here); lifecycle mechanics **Core** under (4) |
| — | 0 | Administration, security & protected access | **Core** — RBAC/admin substrate under (11)/(12), core-boundary |
| — | 0 | Content delivery & publishing | **Core** — publishing/delivery records, core-boundary; rendering, templating & CDN Extended |
| — | 0 | Cloud platform hosting (PaaS/IaaS) | Extended — hosting itself (this fork's hosting is delivery-model prose; see ARTIFACTS.md) |

**Core-boundary decision (recorded, per the Groups 6/22/23/35
precedent):** all twelve Core functions tag zero claims in this
group. They stay Core because the Merge Rule carries the L2 union
upward whole — the merged fork inherits the highest tier and the
full union of functions; a wording artifact is not a downgrade.
Dropping the content substrate at High because the one High listing
describes itself in a single sentence of platform prose would
violate Rule 1 (union, never intersection). The decision is
reinforced on this fork's own words: a "content services platform"
presupposes content held in a registry, organized, described, and
delivered — the substrate is an interpretation of the fork's own
self-description, stated as interpretation, not as tagged evidence.

**Group character, preserved rather than averaged away:** the sole
member is not a website CMS. It is an information-governance
platform: ML/AI classification, extraction, and enrichment over
physical and digital content, delivered as a FedRAMP High SaaS in a
Government Community Cloud (authorizing agency of record in the
source dataset: Internal Revenue Service). What it presupposes at
the High baseline is the content substrate the L2 union defines —
registered content, governed access, derived publishing state,
audited everything — uplifted below. Its engines on top of that
substrate are Extended, named in the gaps from its own verbs.

Named absences, carried from Group 20 and unchanged at this tier:
**no description at any CMS tier claims editorial review/approval
workflow, content versioning/revision history, publish scheduling,
WYSIWYG/visual editing, templating/rendering, or personalization.**
For this fork specifically: no retention/disposition language
appears in its description, and none is imported from the vendor's
broader reputation. The build's lifecycle states, revisions, and
publish windows are registry mechanics of the substrate, recorded
as such — never presented as claimed families.

## The Core — what the merged build implements (12 functions, at the High baseline)

Group 20's twelve functions, carried up whole:

1. **Site & section structure registry** — sites (`site-`) and
   sections (`sec-`) as structure records; section slugs unique per
   site, a section's parent in the same site.
2. **Content type registry** — typed items: page/article/document/
   collection built in, custom types definable (`ct-`).
3. **Content registry & authoring** — items (`ci-`) created/updated
   by authors with title, slug, body, metadata, tags; every content
   edit mints a revision record (`rev-`) (registry mechanics).
4. **Editorial lifecycle** — status draft → in_review → approved →
   published → archived (return: in_review → draft), transitions
   role-gated; the approver is never the item's author
   (separation-of-duties seam `_check_approver_not_author`).
5. **Publishing records & windows** — publishing an item mints a
   publish record (`pub-`) with optional publish_at/expire_at
   window; live/scheduled/expired window state is DERIVED at read
   time from stored facts, never stored.
6. **Media & document asset registry** — assets (`asset-`) with
   kind, filename, byte size, MIME type, SHA-256 checksum;
   registration is the ingestion record. Registry holds metadata +
   checksum, not file bytes.
7. **Taxonomy & metadata registry** — tags (`tag-`) and per-item
   metadata key/values.
8. **Metadata search & discovery** — literal case-insensitive
   substring search over items, assets, sites, tags; indexing
   engines Extended.
9. **Registry reporting** — computed views over the registry (items
   by status/site/type, publish activity, asset counts); reporting
   engines Extended.
10. **REST API** — full surface over HTTP, house auth convention
    (X-User/X-Role against demo registry; 401 unknown/mismatched,
    403 permission, denied attempts audited), uplifted with logon
    lockout (AC-7, below).
11. **RBAC** — admin/publisher/editor/author/viewer matrix, enforced
    in the store before any state change or id allocation and again
    at the service layer, plus the **`auditor`** role holding
    `audit_read` only (AC-5 uplift, below).
12. **Audit log** — append-only, JSONL-persistable, records every
    mutation and every denied attempt (`<action>:denied`), uplifted
    with a **hash-chained tamper-evident** chain, chain
    verification, audit query/reduction, and **fail-closed** write
    behavior (AU-9/AU-7/AU-5, below).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 **plus** the selected NIST SP 800-172 enhanced
  requirements. The group's only fork sits at High, and the
  cross-tier parent (Group 20's build) sat at Moderate; the union
  baseline is therefore the High baseline, un-diluted (Merge
  Rule 1), inherited in full (Rule 2). "Adjacent" remains
  deliberate wording, as in the crosswalk: L3 is not identical to
  FedRAMP High; it is the same assurance weight class.

| Core function | Control families | How the build answers |
|---|---|---|
| Site/section + type registries | CM-6, SI-10, AC-3 | Sites, sections, and content types are explicit, validated configuration records; nothing is structured that is not registered |
| Content registry & revisions | CM-6, AU-2, SI-12 | Content items and every revision of them are auditable, retained registry records |
| Editorial lifecycle | AC-3, AC-5, AC-6 | Role-gated transitions with separation of duties — the approver is never the item's author — and least-privilege enforcement |
| Publishing records & derived windows | AU-2, AU-3, SI-12 | Publishing is an auditable event with complete record content; window state is derived from stored facts, never stored separately |
| Asset registry & checksums | SI-7, AU-2 | Asset integrity is recorded via SHA-256 checksums; every asset registration is an auditable event |
| Taxonomy/metadata | CM-6, SI-10 | Tags and metadata are explicit, validated registry configuration |
| Metadata search | AU-6, AC-3 | Review over registered metadata only, permission-gated |
| Reporting views | AU-6, CA-2 | Computed views over the registry are review and assessment over recorded facts |
| REST API | AC-3, AC-7, SC-8 (partial) | Permission-gated access to the full surface; per-username logon lockout (AC-7 uplift); transmission protection is TLS when configured (see gaps) |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Five operational roles plus the auditor role (AC-5 uplift), enforced pre-mutation at two layers; authenticator management stays with the embedding organization |
| Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only log including denied attempts; hash-chained and tamper-evident (AU-9); fail-closed writes with store-level rollback (AU-5); query/reduction (AU-7); no mutation API |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3; 800-172 audit requirements) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store wraps every mutating method in a snapshot rollback (`_atomic`) so the whole operation rolls back (no object, no change, no id consumed) and the service answers 500 — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role (demo identity `dana`) holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 20, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement on the audit trail in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only. FedRAMP authorizes products;
  CMMC certifies organizations. The build is not a FedRAMP
  authorization and confers no CMMC certification.

## Implementation contract (summary)

`src/cms/` (package `cms`, Python stdlib only), Group 20's contract
unchanged except for the uplift deltas marked **[L3]**:

- `cms/errors.py` — `CmsError`, `ValidationError`, `NotFoundError`,
  `PermissionDenied`, plus **[L3]** `AuditWriteError`.
- `cms/access.py` — roles `admin|publisher|editor|author|viewer`
  plus **[L3]** `auditor` = {`audit_read`}; `PERMISSIONS`/`ACTIONS`
  as Group 20 otherwise; `require(user, action)` raises
  `PermissionDenied`.
- `cms/audit.py` — `AuditLog(path=None)`; `.record(...)` → entry
  dict with keys `ts, actor, action, target, details` plus **[L3]**
  `seq, prev_hash, hash` (SHA-256 of the canonical JSON of
  `{seq, ts, actor, action, target, details, prev_hash}`); raises
  **[L3]** `AuditWriteError` and rolls the append back if the JSONL
  write fails. `.entries()` returns all entries. **[L3]**
  `.query(actor=None, action=None, target=None, since=None,
  until=None)` returns filtered entries; `.verify_chain()` returns
  `(ok, first_bad_index_or_None)`. Append-only; optional JSONL file;
  loaded entries participate in chain verification.
- `cms/store.py` — as Group 20 (the substrate functions; failed
  operations consume no ids; permission checks precede mutation;
  the approver guard lives in the single method
  `_check_approver_not_author`); **[L3]** every mutating method
  (and `search`, which audits) runs its state-changing block inside
  the `_atomic` snapshot guard, so an audit write failure rolls the
  whole operation back and `AuditWriteError` propagates.
- `cms/service.py` — `make_server(host, port, store, audit, users,
  max_failures=3, lockout_seconds=300)` **[L3 kwargs]**. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  **[L3]** consecutive auth failures are tracked per username; at
  `max_failures` the username locks for `lockout_seconds` (403,
  audited `auth:locked`); success resets. Endpoints as Group 20 plus
  **[L3]** `GET /audit/verify` → `{ok, entries, first_bad_index}`
  (audit_read; the count is read before the request's own
  `audit_read` entry is appended) and `GET /audit` filter
  parameters (`actor`, `action`, `target`, `since`, `until`).
  **[L3]** an `AuditWriteError` surfacing in dispatch is answered
  500, never swallowed.
- `cms/__main__.py` — `python -m cms serve [--host] [--port 8793]
  [--audit-log PATH] [--certfile --keyfile]` plus **[L3]**
  `--max-failed-logins` / `--lockout-seconds`; demo users
  alice=admin, bob=publisher, carol=editor, dave=author,
  erin=viewer, **[L3]** dana=auditor.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (one zero-claim sheet, preserved in full;
  0 tagged claims — see How functions were counted).
- Core implemented: **12 / 12** functions above, at the High
  baseline, each with tracing tests; 6 tier uplifts implemented
  (hash-chained audit, fail-closed audit writes, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor role).
- Tests: **146** (98 inherited from Group 20, 4 auditor tests added
  to the inherited access suite, 44 new uplift tests) — see
  `tests/README.md`, including both mutation-verified negative
  controls.

## Gaps — specified, not implemented (for the GAPS.md final batch)

This fork's own engines (from its description's own verbs;
near-misses #3–#5 in `scratch/ARTIFACTS.md`, not tagged claims):

- Learned ML/AI classification engine (automatically classify
  physical and digital content).
- Learned ML/AI extraction engine (extract content/data from
  physical and digital content).
- Learned ML/AI enrichment engine (enrich content with derived
  metadata — the fork's substance; the substrate stores caller-
  supplied metadata only and derives none).
- Physical-content intake & digitization pipeline (the physical
  side of "physical and digital content": scanning/conversion of
  physical records into the platform).
- The content services platform runtime itself (hosting/delivery
  of the SaaS platform; delivery-model prose in the description).

Extended functions carried from the Group 20 union, specified in
`../cms-l2/UNION-SPEC.md`, not implemented:

- Rendering & templating engines and visual/WYSIWYG editors.
- CDN / delivery network and runtime site serving.
- Enterprise search indexing engines (the core searches registry
  metadata only).
- Bulk ingestion & index-in-place engines.
- Library ILS vertical.
- BPM / case-management engine.
- Participant engagement & research platform vertical.
- Personalization / experience optimization.
- Editorial workflow engines beyond lifecycle mechanics (parallel
  review, routing, notifications — claimed by no sibling at any
  CMS tier).

Baseline gaps at High (platform layer; gap-listed, never implied
closed):

- MFA / authenticator management (IA-2(1)/(2), IA-5) — IdP layer,
  hooks only.
- FIPS-validated cryptography (SC-13) — Python stdlib is not a
  validated module; not claimed.
- Encryption at rest (SC-28) — deployment layer.
- Audit retention enforcement (AU-11).
- Session lock / termination (AC-11/AC-12) — stateless per-request
  auth in the current build.

Platform notes: TLS only when a certificate is configured;
multi-tenancy (single-tenant reference deployment); demo identities
are hooks, not an IdP (IA-2 stays with the embedding organization).

## Verification

- Suite: `PYTHONPATH=src python3 -m unittest discover -s tests` —
  **146 tests, OK** (coordinator's run at delivery).
- Negative control 1 (inherited, AC-5): disabling the approver
  guard `_check_approver_not_author` in the real store made
  exactly **4** tests fail; store restored from
  `tests/store.py.premutation` (SHA-256 verified identical) and the
  suite returned to green. Recorded in `tests/README.md`.
- Negative control 2 ([L3], AU-9): an in-place mutated audit entry
  makes `verify_chain()` report `(False, 1)` — proven in-suite
  (`test_audit_chain.py`) and in an external drill at delivery
  (clean log `(True, None)`; entry 1 mutated → `(False, 1)`).
- Reconciliation: `python3 scratch/verify.py` — specs ↔ forks.json
  exact, CMS category arithmetic 8 = 4 + 2 + 1 + 1, zero diffs.
- Live smoke at delivery (coordinator): HTTP flow site → item →
  submit → approve (non-author) → publish; author self-approval
  denied at the store level (`PermissionDenied`); auditor `dana`
  denied `/sites` (403) and admitted to `/audit/verify`
  (`{ok: true, entries: 10, first_bad_index: null}`); chain
  verified clean, then localized a tamper at index 1.
