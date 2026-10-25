# Union Spec — Law Enforcement, CMMC L2 (DeadRamp Phase 2, Group 34)

The merged functional spec for the **Law Enforcement L2** sibling group:
**2 forks**, category **Law Enforcement**, CMMC tier **L2** (every member
is FedRAMP **Moderate** in `forks.json` — verified, so the group is
single-tier and the merge takes the group baseline in full, per Merge
Rule 2). The member list was reconciled against `MAP.md`'s
"Law Enforcement — L2 (2)" section with **zero diffs**:

| Fork | Vendor | Product | Status |
|---|---|---|---|
| FR2510634052 | LexisNexis Legal and Professional | Lexis+® for Government | FedRAMP Certified |
| FR2502148523 | Thomson Reuters | Thomson Reuters Legal Research (TR LR) | FedRAMP In Process |

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2 entries,
each with the offering's full public marketplace description and its
function claims tagged from that description, every claim carrying the
source sentence as evidence. Sources: GSA FedRAMP Marketplace dataset
(cached at `../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. No live fetching was needed: both descriptions were present
in the cached dataset.

## Group character — read this first

**Neither sibling is a law-enforcement operational platform.** Both are
legal research platforms for government attorneys and legal
professionals, filed under "Law Enforcement" in the source; both source
records carry `business_categories: []` — the source does not
self-categorize either offering at all. This group is therefore a
source-category artifact in the same sense as Groups 15, 26 and 27, and
the spec treats it the way those groups were treated: the taxonomy is
defined from the descriptions as they are, the core is the records
substrate the claimed functions jointly presuppose, and the category's
anticipated operational functions are recorded as **named absences**
(unclaimed — not built, and not registered as gaps, per the Group 21/25
precedent), not invented as claims.

What the two descriptions actually describe is one shared function set
with two dialects: a corpus of primary and secondary law, search over
it, citation validation, document handling, and — on one side each —
collaboration (Lexis) and editorial enhancement + practice guidance
(TR). The merged build is a **legal research records substrate**:
registries and records for matters, sources, documents, saved searches,
annotations, and citation checks. It stores no legal content, no
document content, and nothing about any person.

## How functions were counted

A fixed 9-function taxonomy for this group was matched against each
offering's own public description (extractor: `scratch/extract.py`). A
function is claimed for a fork **only** when the description contains
matching text; the matching sentence is stored as the claim's evidence
in the spec sheet. 13 claims tag in total (Lexis 5, TR 8); there are no
zero-claim sheets, but the claim mass is thin and sits in few families —
counts are a **floor**, not a ceiling, on what these products do.

Wording-artifact corrections applied to the matcher are recorded in
`scratch/extract.py`. The ones that matter for reading this spec:

- **Identity + audience sentences get no tag.** Each description opens
  by naming itself "a legal research solution" for a named audience.
  Those sentences tag nothing; every claim rests on a functional
  sentence (the Group 31 DailyPay precedent).
- **Assurance prose is not an access-control claim.** TR's "enhanced
  security, availability, compliance, and support ... mission-critical
  edge" sentence tags nothing but the platform note. Lexis's
  "maintaining the highest levels of security and compliance required
  for sensitive legal matters" names no mechanism and is recorded as a
  **near-miss** for `access_control`: the family's one claim rests on
  TR's "secure access controls". Access control enters the Core as
  baseline substrate for both forks — claimed for TR, **carried, not
  claimed** for Lexis.
- **No AI tag exists to take.** Neither description mentions AI,
  machine learning, alerting, or citator update feeds, whatever the
  vendors market elsewhere. Nothing is inferred.

## Privacy discipline (hard rule, enforced by tests)

This build stores **records and opaque caller-supplied references
only**, under the strictest form of the project's privacy discipline:

- No entity shape can hold a real name, a case subject, a party, an
  address, or any identifier of a person. Matters, sources, documents,
  searches, annotations and citations are all keyed by opaque
  caller-supplied `*_ref` strings, and every entity's exact key set is
  pinned by tests.
- **Documents are registry metadata + SHA-256 checksums, never
  content.** The store accepts a checksum and a byte count; content
  itself is never stored. Integrity is checked by verify-by-content:
  the caller supplies bytes, the build hashes them and compares.
- **Search queries and annotation notes are stored as SHA-256 digests
  only.** The store has no parameter that can accept query text or
  note text; the service layer hashes before the store ever sees a
  value. A saved-search record proves *that* a search was saved and
  how many results it returned, never what it asked.
- **Citation treatments are recorded verbatim.** A citation check
  stores the caller's treatment string exactly as supplied — never
  normalized, never scored, never aggregated into a computed status.
  (The Group 21 precedent: ratings are records; scoring is an engine.)

## Function ranking — both siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Legal research corpus (primary & secondary law) | 2 | 100% | **Core** as the source registry (records of sources; the corpus content itself is Extended) |
| 2 | Legal search tools | 2 | 100% | **Core slice**: saved-search records + registry-metadata search. Corpus search/relevance engine: Extended |
| 3 | Citation validation | 2 | 100% | **Core slice**: citation-check records with treatment recorded verbatim. The validation engines themselves: Extended |
| 4 | Document management (upload, review, document features) | 2 | 100% | **Core** as the document registry (metadata + checksums, review lifecycle; content never stored) |
| 5 | Save, annotate, share & collaborate on research | 1 | 50% | **Core**: matter membership + saved searches + annotation records (digests only) |
| 6 | Editorial enhancement (taxonomies & editorial features) | 1 | 50% | Extended — the editorial systems are the vendors' proprietary product |
| 7 | Practice guidance & standard documents | 1 | 50% | **Core slice**: guidance/standard-document kinds in the source registry. The guidance content and drafting engine: Extended |
| 8 | Secure access controls | 1 | 50% | **Core** (L2 baseline substrate; claimed for TR, carried for Lexis — see corrections) |
| 9 | SaaS / cloud delivery | 1 | 50% | Platform note (both offerings are SaaS per the source record; the build is a single-tenant reference deployment) |

**Differences are preserved, not averaged away:** the siblings split
cleanly. Lexis's distinctive claim is collaboration over research
artifacts; TR's distinctive claims are the editorial layer (Key Number
taxonomy, KeyCite) and the Practical Law guidance layer. Neither
description contains any operational law-enforcement vocabulary at all.

### Named absences — anticipated by the category, claimed by neither

Recorded so the union is honest about what "Law Enforcement" might
suggest and these two forks do not do (unclaimed → not built, not
gaps, per the Group 21/25 precedent):

- Incident / case management for law-enforcement operations
- Evidence management & chain of custody over physical evidence
- Criminal records / records-management systems (RMS), criminal-history data of any kind
- Investigative case files and case subjects

### The long tail — Extended, specified not implemented

- **The legal corpora themselves** — the primary/secondary law content
  databases and TR's Practical Law guidance content. The content, its
  editorial maintenance, and its licensing are the vendors' product;
  the core registers sources as records and holds no content.
- **Citation-validation engines** — Shepard's® / KeyCite-class
  editorial systems that determine a citation's treatment. The core
  records a treatment a caller supplies; it determines none.
- **Editorial enhancement systems** — headnotes, taxonomy assignment
  (West Key Number System class), and editorial enrichment pipelines.
- **Corpus search & relevance engines** — full-text indexing and
  ranking over the legal corpus. The core searches registry metadata
  only.
- **AI / ML research assistance** — 0 claims in these descriptions;
  named so the union is complete, recorded as unclaimed here.
- **Document content storage, rendering & redaction** — the registry
  holds metadata + checksums only, by the privacy rule.
- **Surveillance, facial recognition, predictive policing, real-time
  intelligence feeds** — named as Extended gaps by category
  discipline: 0 claims, and out of scope for a records substrate;
  none is built, and none would be built from these claims.

## The Core — what the merged build implements (11 functions)

The records substrate every claimed function above presupposes:

1. **Matter registry & members** — matters (the organizing container
   for a body of research) keyed by an opaque `matter_ref`, with a
   guarded lifecycle (`open` → `closed` → reopen) and a member list.
   Membership is the boundary every matter-scoped function enforces;
   writes to a closed matter are rejected.
2. **Source registry** — legal sources as metadata records inside a
   matter: opaque `source_ref`, a kind (`statute`, `case_law`,
   `regulation`, `secondary`, `guidance`, `standard_document`), and
   optional opaque jurisdiction / citation references. No content.
3. **Document registry** — uploaded documents as metadata + SHA-256:
   opaque `doc_ref`, checksum (validated lowercase hex), byte count,
   and a guarded review lifecycle (`registered` → `in_review` →
   `reviewed`). Content is never stored.
4. **Verify-by-content** — given bytes, recompute the SHA-256 and
   compare it to the registered checksum; returns the comparison,
   stores nothing.
5. **Saved-search records** — a saved search is a record: opaque
   `search_ref`, the query's SHA-256 digest (never the query), and a
   result count.
6. **Annotation records** — an annotation on a document, search, or
   source is a record: opaque `annotation_ref`, target, and the
   note's SHA-256 digest (never the note).
7. **Citation-check records** — a citation check is a record: opaque
   `citation_ref`, an optional link to a registered source, and the
   treatment **recorded verbatim** from the caller.
8. **Registry reporting** — counts computed on read: sources by kind,
   documents by status, saved searches, annotations, citation checks
   by recorded treatment (verbatim keys). No analytics engine.
9. **Registry search** — literal substring search over registry
   metadata (references, kinds, statuses, recorded treatments),
   scoped to matters the actor may see. Never over content — there
   is none.
10. **Access control (RBAC)** — platform roles `admin`, `member`,
    `viewer` with a permission matrix enforced on every operation,
    layered with matter membership (non-members cannot read or write
    a matter's records; the platform `admin` role can).
11. **Audit log** — an append-only audit trail: every matter,
    membership, source, document, search, annotation, and
    citation-check mutation, and every denied attempt, recorded with
    actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110 practices
  of NIST SP 800-171 Rev. 2 that define CMMC L2. Both parent forks sit
  at Moderate, so the union baseline is the Moderate baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + matter membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; the build ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review — append-only store, audit-read
    restricted to the `audit_read` permission, held by admin only).
    At L2 the audit mapping holds on **both** sides of the crosswalk,
    because 800-171 carries an audit family (3.3) — the mirror of the
    L1 groups' precision note.
  - Document checksums & verify-by-content → **SI** (SI-7 software,
    firmware and information integrity — a Moderate selection, cited
    as such; hashes are computed with the standard library and are
    an implementation property of the registry).
  - Registries, lifecycle guards, digest discipline → **SI** (SI-10
    information input validation — malformed input, including any
    non-string reference, bad checksum, or negative count, is
    rejected whole, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS when a
    certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `lawenf` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`mat-`, `src-`, `doc-`, `sea-`,
`ann-`, `cit-`); a failed operation consumes no id and changes
nothing. All timestamps are UTC ISO-8601. Validation always precedes
mutation.

- `lawenf/errors.py` — `LawEnfError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `LawEnfError`).
- `lawenf/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `matter_read, matter_write,
  source_write, document_write, search_write, annotation_write,
  citation_write, report_read, audit_read`. `PERMISSIONS`: admin ⊇
  all nine; member = all except `audit_read`; viewer =
  {matter_read, report_read}. `permissions_for(role)`, `can(user,
  action)`, `require(user, action)` raising `PermissionDenied`.
- `lawenf/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL
  file persistence; reloads an existing file on construction.
- `lawenf/store.py` — `LawEnfStore(audit=None)`. The store records
  every successful mutation to its audit log (when one is attached);
  the HTTP layer records denials and `audit_read` only. Two
  boundaries on every matter-scoped operation: the actor must be a
  matter member or hold the platform `admin` role, else
  `PermissionDenied`; and the operation's role permission is
  required (enforced when the actor is a `User`; a plain-string
  actor carries identity but no role, so role enforcement for those
  happens in the service layer — the house convention). Methods:
  - `create_matter(matter_ref, actor)` (action `matter_write`) →
    `{id, matter_ref, status, members, created_by, created_utc}`;
    `matter_ref` a non-empty string, unique across matters
    (duplicate → `ValidationError`); status starts `open`; the
    creator is the first member. Audits `matter_create`.
    `list_matters(actor)` → matters the actor is a member of, or all
    for a platform admin, in creation order. `get_matter(matter_id,
    actor)` (`NotFoundError`; `PermissionDenied` for a non-member
    non-admin).
  - `add_member(matter_id, username, actor)` → updated matter dict.
    Only the matter's creator or a platform admin may add; adding an
    existing member raises `ValidationError`. Audits `member_add`.
  - `close_matter(matter_id, actor)` / `reopen_matter(matter_id,
    actor)` (action `matter_write`): `open` → `closed` / `closed` →
    `open`; wrong state → `ValidationError`. Audits `matter_close` /
    `matter_reopen`. Every create operation below raises
    `ValidationError` on a closed matter.
  - `create_source(matter_id, source_ref, kind, actor,
    jurisdiction_ref=None, citation_ref=None)` (action
    `source_write`) → `{id, matter_id, source_ref, kind,
    jurisdiction_ref, citation_ref, created_by, created_utc}`;
    `kind` must be one of `statute`, `case_law`, `regulation`,
    `secondary`, `guidance`, `standard_document`; `source_ref`
    non-empty and unique within the matter. Audits `source_create`.
    `list_sources(matter_id, actor, kind=None)`; `get_source(...)`
    (an id from another matter → `NotFoundError`).
  - `register_document(matter_id, doc_ref, sha256, size_bytes,
    actor)` (action `document_write`) → `{id, matter_id, doc_ref,
    sha256, size_bytes, status, created_by, created_utc}`; status
    starts `registered`; `sha256` must be exactly 64 lowercase hex
    characters; `size_bytes` an int ≥ 0 (booleans and floats
    rejected); `doc_ref` non-empty and unique within the matter.
    Audits `document_register`. `get_document(...)`;
    `list_documents(matter_id, actor, status=None)` (unknown status
    filter → `ValidationError`).
  - `begin_review(matter_id, doc_id, actor)` /
    `complete_review(matter_id, doc_id, actor)` (action
    `document_write`): `registered` → `in_review` → `reviewed`; any
    other transition → `ValidationError`. Audits
    `document_begin_review` / `document_complete_review`.
  - `verify_document(matter_id, doc_id, content, actor)` (action
    `matter_read`) → `{document_id, sha256, computed_sha256,
    matches}`; `content` is bytes (a str is encoded as UTF-8);
    non-mutating, records nothing.
  - `save_search(matter_id, search_ref, query_sha256, result_count,
    actor)` (action `search_write`) → `{id, matter_id, search_ref,
    query_sha256, result_count, created_by, created_utc}`.
    **There is no parameter for query text.** `query_sha256` must be
    64 lowercase hex; `result_count` an int ≥ 0; `search_ref`
    non-empty and unique within the matter. Audits `search_save`.
    `list_searches(...)`; `get_search(...)`.
  - `add_annotation(matter_id, target_kind, target_id,
    annotation_ref, note_sha256, actor)` (action
    `annotation_write`) → `{id, matter_id, target_kind, target_id,
    annotation_ref, note_sha256, created_by, created_utc}`.
    **There is no parameter for note text.** `target_kind` one of
    `document`, `search`, `source`; the target must exist in this
    matter (else `NotFoundError`); `note_sha256` 64 lowercase hex;
    `annotation_ref` non-empty and unique within the matter. Audits
    `annotation_add`. `list_annotations(matter_id, actor,
    target_id=None)`.
  - `record_citation_check(matter_id, citation_ref, treatment,
    actor, source_id=None)` (action `citation_write`) → `{id,
    matter_id, citation_ref, source_id, treatment, created_by,
    created_utc}`; `treatment` a non-empty string stored **verbatim**
    (no normalization, no allowed-set, no derived status);
    `source_id` when given must name a source in this matter.
    Audits `citation_check_record`. `list_citation_checks(...)`.
  - `matter_report(matter_id, actor)` (action `report_read`) →
    `{matter_id, status, member_count, sources_by_kind,
    documents_by_status, search_count, annotation_count,
    citation_checks_by_treatment}` — counts computed on read from
    the records; treatment keys are the verbatim recorded strings.
  - `search_registry(actor, query)` (action `matter_read`) →
    `{matters, sources, documents, searches, citation_checks}`:
    literal case-insensitive substring match over `*_ref` fields,
    kinds, statuses, and recorded treatments, restricted to matters
    the actor is a member of (or all for a platform admin). Empty
    query → `ValidationError`. Digests are never matched or
    returned as searchable text.
- `lawenf/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match
  the registry; unknown user or mismatched role → 401). Errors are
  JSON `{error}` with 400/401/403/404 as applicable; denied attempts
  (401 and 403) are audited with the action name suffixed `:denied`,
  and no stack trace is ever returned. The service layer is the only
  place query text or note text may appear: it SHA-256-hashes
  `query_text` / `note_text` request fields before calling the
  store, and never logs or stores the text. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /matters` (matter_read) → `{"matters": [...]}`;
    `POST /matters` `{matter_ref}` (matter_write) → 201 matter dict
  - `GET /matters/{id}` (matter_read)
  - `POST /matters/{id}/members` `{username}` → matter dict (the
    store enforces creator-or-admin)
  - `POST /matters/{id}/close` / `POST /matters/{id}/reopen`
    (matter_write) → matter dict
  - `GET /matters/{id}/sources?kind=` (matter_read) →
    `{"sources": [...]}`; `POST /matters/{id}/sources`
    `{source_ref, kind, jurisdiction_ref?, citation_ref?}`
    (source_write) → 201
  - `GET /matters/{id}/documents?status=` (matter_read) →
    `{"documents": [...]}`; `POST /matters/{id}/documents`
    `{doc_ref, sha256, size_bytes}` (document_write) → 201
  - `POST /matters/{id}/documents/{did}/begin-review` /
    `/complete-review` (document_write) → document dict
  - `POST /matters/{id}/documents/{did}/verify`
    `{content_b64}` (matter_read) → verify dict; malformed base64
    → 400
  - `GET /matters/{id}/searches` (matter_read) →
    `{"searches": [...]}`; `POST /matters/{id}/searches`
    `{search_ref, query_text | query_sha256, result_count}`
    (search_write) → 201 (digest computed here when `query_text` is
    given)
  - `GET /matters/{id}/annotations?target_id=` (matter_read) →
    `{"annotations": [...]}`; `POST /matters/{id}/annotations`
    `{target_kind, target_id, annotation_ref, note_text |
    note_sha256}` (annotation_write) → 201
  - `GET /matters/{id}/citation-checks` (matter_read) →
    `{"citation_checks": [...]}`; `POST
    /matters/{id}/citation-checks` `{citation_ref, treatment,
    source_id?}` (citation_write) → 201
  - `GET /matters/{id}/report` (report_read) → report dict
  - `GET /search?q=` (matter_read) → registry search dict
- `lawenf/__main__.py` — `python -m lawenf serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above). Default port 8797.

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces to,
and include a **negative control**: a mutant membership guard (one
that performs no membership check at all, so any authenticated actor
can read any matter) and a mutant verify (one that reports `matches`
True for any content). The canonical expectations are shown to reject
both — an outsider read must raise `PermissionDenied` from the real
store, and altered content must read `matches: False` — proving the
suite catches those defect classes rather than merely passing. The
negative control must additionally be **mutation-verified**: patching
the real membership guard in `src/` with the mutant must make the
suite fail; the run and its result are recorded in `tests/README.md`.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (13 claims total; no zero-claim sheets).
- Core: 11 core functions implemented, each with tracing tests.
- Extended: 7 functions specified and ranked, **not** implemented in
  this build (the legal corpora themselves, citation-validation
  engines, editorial enhancement systems, corpus search & relevance
  engines, AI/ML research assistance (0 claims here), document
  content storage/rendering/redaction, and the category-discipline
  exclusions: surveillance, facial recognition, predictive policing,
  real-time intelligence feeds).
- Named absences (unclaimed, not gaps): incident/case management,
  evidence management & chain of custody, criminal records/RMS,
  investigative case files.
- Platform-layer: encryption at rest (deployment layer); TLS only
  when configured; multi-tenancy (single-tenant reference
  deployment); demo identities are hooks, not an IdP (IA-2 stays
  with the embedding organization).
