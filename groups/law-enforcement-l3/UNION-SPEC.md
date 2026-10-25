# Union Spec — Law Enforcement, CMMC L3-adjacent (DeadRamp Phase 2, Group 35)

The merged functional spec for the **Law Enforcement L3-adjacent**
sibling group: **2 forks**, category **Law Enforcement**, CMMC tier
**L3-adjacent** (every member is FedRAMP **High** in `forks.json` —
verified). The member list was reconciled against `MAP.md`'s
"Law Enforcement — L3-adjacent (2)" section with **zero diffs**:

| Fork | Vendor | Product | Status |
|---|---|---|---|
| FR2421035110 | Cellebrite | Cellebrite Government Cloud (CGC) | FedRAMP Certified |
| FR2616545789 | Magnet Forensics | Magnet One | Agency Authorization In Process |

Both offerings are **SaaS**, both are deployed as **Government
Community Cloud**, and both source records carry
`business_categories: []` — the source does not self-categorize either
offering at all.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
both descriptions were present in the cached dataset.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 34 merged build** (`../law-enforcement-l2/`) — itself
   the union of the 2 Law Enforcement L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room legal research records substrate.
2. This group's **2 High forks**, via the spec sheets in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheets are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4).

**Reuse, stated explicitly:** where functions overlap, this build
reuses Group 34's own open-source code (Apache-2.0, ours). The store's
entity shapes and methods are unchanged from Group 34; `errors.py` is
Group 34's plus one added class (`AuditWriteError`); the remaining
modules are Group 34's, modified for the tier uplift (`audit.py`,
`access.py`, `service.py`, `store.py`, `__main__.py`). The uplift
analysis below names what the High baseline demanded beyond the L2
core and what was done about each item — implemented, or gap-listed
by name. No vendor code, assets, or branding from either sibling
offering is used.

## Group character — read this first

**Unlike the L2 pair, both L3 siblings are genuine digital-forensics
platforms.** Group 34's pair (Lexis+® for Government, Thomson Reuters
Legal Research) are legal research platforms for government
attorneys. This group's pair — Cellebrite Government Cloud (CGC) and
Magnet One — extract, ingest, process, analyze, and review digital
evidence from mobile devices and other sources. Their descriptions
speak an entirely different function vocabulary from the L2 pair's.

That difference is why this spec sheet set is a **zero-claim set**
under the counting method below, and why the core is **carried, not
claimed**, under an explicit core-boundary decision:

- **0 of the 11 core functions are claimed by this group's forks**
  under Group 34's verbatim taxonomy. The core is Group 34's L2 core,
  carried up whole under the Merge Rule and uplifted to the High
  baseline — it is not re-derived from these two descriptions.
- **A wording/taxonomy artifact is not a downgrade.** A taxonomy
  defined from legal-research descriptions does not tag
  digital-forensics descriptions, and that mismatch does not shrink
  the merged build: the Merge Rule takes the union of baselines, and
  the union is carried in full. (Precedents: Groups 6, 22, 23, 24,
  30 — groups where a verbatim taxonomy or a wording artifact left
  core functions unclaimed by a group's own forks, and the core was
  carried on the recorded boundary decision rather than dropped.)
- The functions these two descriptions **do** claim in their own
  words are itemized below as **this group's own verticals** — device
  unlocking; evidence extraction from mobile devices; forensic
  analysis engines; evidence ingest & processing pipelines; evidence
  review; chain-of-custody enforcement over evidence; information
  sharing / collaboration over evidence; forensic reporting. Every
  one is **Extended**: each is a processing engine over evidence
  content, and this records substrate never holds content (see the
  privacy discipline below). The substrate's checksums,
  verify-by-content, and hash chain are records-side **analogues**
  of chain-of-custody enforcement, stated as analogues, not
  equivalents, and not a custody system.

The merged build is therefore the same **records substrate** as
Group 34 — registries and records for matters, sources, documents,
saved searches, annotations, and citation checks — at the High
baseline. It stores no legal content, no document content, no
evidence content, and nothing about any person.

## How functions were counted

Group 34's fixed 9-function taxonomy was applied **verbatim** —
ids, labels, and matching patterns byte-identical to Group 34's
extractor (`scratch/extract.py`) — against each offering's own
public description. A function is claimed for a fork **only** when
the description contains matching text; the matching sentence is
stored as the claim's evidence in the spec sheet. The taxonomy was
**not re-tuned** for this group.

**Result: 0 claims in total. Both spec sheets are zero-claim
sheets**, with the full descriptions preserved in
`specs/specs.json`. Counts are a **floor**, not a ceiling, on what
these products do — here the floor is zero because the taxonomy and
the descriptions speak different vocabularies, not because the
products do nothing.

Near-misses and corrections are recorded in full in
`scratch/ARTIFACTS.md`. The summary that matters for reading this
spec:

- **`collaboration` ×2 — near-miss, no tag.** Cellebrite's
  "information sharing" and Magnet's "advanced evidence review and
  collaboration features" do not contain the verbatim pattern
  ("save, annotate, share and collaborate"). Both phrases are
  recorded instead as evidence for the group's own
  information-sharing / collaboration vertical (Extended).
- **`hosting_platform` — near-miss, no tag.** Cellebrite's
  "operational within Amazon Web Services (AWS) GovCloud" and
  Magnet's "within a FedRAMP High authorized cloud environment" do
  not match the verbatim pattern ("secure cloud environment").
  Both offerings are SaaS per the source record; hosting remains a
  platform note in prose.
- **`access_control` — near-miss, no tag.** Magnet's "documented
  security controls, and continuous monitoring aligned to FedRAMP
  standards" is assurance prose about the offering's own
  authorization posture (Group 34 wording-artifact correction 2);
  the verbatim pattern is "secure access controls". Access control
  enters the Core as High-baseline substrate, **carried, not
  claimed** — for both forks.
- **`legal_search` — near-miss, no tag.** Magnet's "ingest, process,
  analyze, and manage digital evidence" names no search tool and
  no "searches".
- **`document_management` — near-miss, no tag.** Magnet's "manage
  digital evidence" is not "document upload" or "document
  management features".
- **Cellebrite's chain-of-custody sentence tags nothing.** "…
  without compromising the integrity or chain of custody of the
  mobile device" is recorded as motivation for the substrate's
  integrity mechanisms and as the evidence sentence for the
  chain-of-custody vertical (Extended) — not as a claim for any
  taxonomy family, and not as a claim for the substrate's analogues.
- **Magnet's security-controls sentence is assurance prose.** It
  tags nothing (see `access_control` above).
- **No claim is inferred** from the category label "Law
  Enforcement" itself, from either vendor's reputation, or from any
  source beyond the two marketplace descriptions.

## Function ranking — both siblings

### Group 34's taxonomy, applied verbatim

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Legal research corpus (primary & secondary law) | 0 | 0% | **Core carried** as the source registry (records of sources; the corpus content itself is Extended) |
| 2 | Legal search tools | 0 | 0% | **Core slice carried**: saved-search records + registry-metadata search. Corpus search/relevance engine: Extended |
| 3 | Citation validation | 0 | 0% | **Core slice carried**: citation-check records with treatment recorded verbatim. The validation engines themselves: Extended |
| 4 | Document management (upload, review, document features) | 0 | 0% | **Core carried** as the document registry (metadata + checksums, review lifecycle; content never stored) |
| 5 | Save, annotate, share & collaborate on research | 0 | 0% | **Core carried**: matter membership + saved searches + annotation records (digests only) |
| 6 | Editorial enhancement (taxonomies & editorial features) | 0 | 0% | Extended — the editorial systems are the L2 vendors' proprietary product |
| 7 | Practice guidance & standard documents | 0 | 0% | **Core slice carried**: guidance/standard-document kinds in the source registry. The guidance content and drafting engine: Extended |
| 8 | Secure access controls | 0 | 0% | **Core carried** (High-baseline substrate; claimed for neither fork here — see corrections) |
| 9 | SaaS / cloud delivery | 0 | 0% | Platform note (both offerings are SaaS per the source record; the build is a single-tenant reference deployment) |

### This group's own verticals — claimed in the descriptions' own words

Every vertical below rests on a verbatim evidence sentence in
`scratch/ARTIFACTS.md` (sourced from `specs/specs.json`). Every one
is **Extended — specified, not implemented**: each is a processing
engine over evidence content, which this records substrate never
holds.

| # | Vertical | Claiming sibling(s) | Disposition in this build |
|---|---|---|---|
| 1 | Device unlocking | Cellebrite | Extended |
| 2 | Evidence extraction from mobile devices | Cellebrite | Extended |
| 3 | Forensic analysis engines | Both | Extended |
| 4 | Evidence ingest & processing pipelines | Magnet Forensics | Extended |
| 5 | Evidence review | Magnet Forensics | Extended |
| 6 | Chain-of-custody enforcement over evidence | Cellebrite | Extended — the substrate's checksums / verify-by-content / hash chain are records-side analogues, not equivalents |
| 7 | Information sharing / collaboration over evidence | Both | Extended |
| 8 | Forensic reporting | Cellebrite | Extended — beyond the substrate's registry reporting (counts over records) |

**Differences are preserved, not averaged away:** Cellebrite's
distinctive claims are the device-side verticals (unlocking,
extraction, chain of custody, forensic reporting); Magnet's
distinctive claims are the platform-side verticals (evidence ingest
& processing pipelines, evidence review). Forensic analysis and
information sharing / collaboration are claimed by both.

### Named absences — carried from Group 34, with the L3 nuance

Group 34 recorded, for the legal-research side, the category's
anticipated operational functions claimed by neither L2 fork
(unclaimed → not built, not gaps, per the Group 21/25 precedent):

- Incident / case management for law-enforcement operations
- Evidence management & chain of custody as an operational system
- Criminal records / records-management systems (RMS), criminal-history data of any kind
- Investigative case files and case subjects

The nuance for this group: at L3 the forks **do** claim forensic
evidence functions in their own words — itemized above as this
group's own verticals. That is different from the L2 named
absences. The verticals are this group's Extended list; the
named-absence framing is kept for the legal-research side only
where it remains accurate, and no vertical is silently folded into
a named absence or vice versa.

### The long tail — Extended, specified not implemented

Carried from Group 34's union (see `GAPS.md`, Group 34 section),
plus this group's own verticals above:

- **The legal corpora themselves** — the primary/secondary law
  content databases and TR's Practical Law guidance content. The
  content, its editorial maintenance, and its licensing are the
  vendors' product; the core registers sources as records and holds
  no content.
- **Citation-validation engines** — Shepard's® / KeyCite-class
  editorial systems that determine a citation's treatment. The core
  records a treatment a caller supplies; it determines none.
- **Editorial enhancement systems** — headnotes, taxonomy
  assignment (West Key Number System class), and editorial
  enrichment pipelines.
- **Corpus search & relevance engines** — full-text indexing and
  ranking over the legal corpus. The core searches registry
  metadata only.
- **AI / ML research assistance** — 0 claims at either tier; named
  so the union is complete, recorded as unclaimed here.
- **Document content storage, rendering & redaction** — the
  registry holds metadata + checksums only, by the privacy rule.
- **This group's own verticals (8)** — device unlocking; evidence
  extraction from mobile devices; forensic analysis engines;
  evidence ingest & processing pipelines; evidence review;
  chain-of-custody enforcement over evidence; information sharing /
  collaboration over evidence; forensic reporting. Each operates
  over evidence content the substrate never holds.

### Category-discipline exclusions (0 claims, not built)

- **Surveillance, facial recognition, predictive policing,
  real-time intelligence feeds** — named as Extended gaps by
  category discipline: 0 claims, and out of scope for a records
  substrate; none is built, and none would be built from these
  claims.

## Privacy discipline (hard rule, enforced by tests)

This build stores **records and opaque caller-supplied references
only**, under the strictest form of the project's privacy
discipline. The rule carries **unchanged** from Group 34:

- No entity shape can hold a real name, a case subject, a party, an
  address, an evidence content, or any content, or any identifier
  of a person. Matters, sources, documents, searches, annotations
  and citations are all keyed by opaque caller-supplied `*_ref`
  strings, and every entity's exact key set is pinned by tests.
  Smuggled fields are rejected by the store signatures themselves.
- **Documents are registry metadata + SHA-256 checksums, never
  content.** The store accepts a checksum and a byte count; content
  itself is never stored. Integrity is checked by verify-by-content:
  the caller supplies bytes, the build hashes them and compares.
- **Search queries and annotation notes are stored as SHA-256
  digests only.** The store has no parameter that can accept query
  text or note text; the service layer hashes before the store ever
  sees a value. A saved-search record proves *that* a search was
  saved and how many results it returned, never what it asked.
- **Citation treatments are recorded verbatim.** A citation check
  stores the caller's treatment string exactly as supplied — never
  normalized, never scored, never aggregated into a computed
  status. (The Group 21 precedent: ratings are records; scoring is
  an engine.)

## The Core — what the merged build implements (11 functions, at the High baseline)

Group 34's 11 functions, carried up whole under the Merge Rule and
uplifted to the High baseline. The uplift deltas on access control
and the audit log are named in items 10–11 and analyzed in full in
the next section:

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
    `viewer`, plus the High-baseline **`auditor`** role, with a
    permission matrix enforced on every operation, layered with
    matter membership (non-members cannot read or write a matter's
    records; the platform `admin` role can), and unsuccessful-logon
    lockout at the service layer (uplifts, below).
11. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail: every matter, membership, source, document, search,
    annotation, and citation-check mutation, and every denied
    attempt, recorded with actor, action, target, and UTC timestamp,
    with fail-closed writes, audit query/reduction, and chain
    verification (uplifts, below).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 **plus** the selected NIST SP 800-172 enhanced
  requirements. Both of this group's forks sit at High, and the
  cross-tier parent (Group 34's build) sat at Moderate; the union
  baseline is therefore the High baseline, un-diluted (Merge Rule 1),
  inherited in full (Merge Rule 2). "Adjacent" remains deliberate
  wording, as in the crosswalk: L3 is not identical to FedRAMP High;
  it is the same assurance weight class.
- **Feature → control family mapping (this build, carried from
  Group 34 and uplifted):**
  - Access control (platform roles + matter membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; the build ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-7 audit reduction, AU-9
    protection of audit information — append-only store, audit-read
    restricted to the `audit_read` permission).
  - Document checksums & verify-by-content → **SI** (SI-7 software,
    firmware and information integrity — a High selection, cited as
    such; hashes are computed with the standard library and are an
    implementation property of the registry).
  - Registries, lifecycle guards, digest discipline → **SI** (SI-10
    information input validation — malformed input, including any
    non-string reference, bad checksum, or negative count, is
    rejected whole, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS when a
    certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON; `verify_chain()` recomputes the chain and localizes the first bad entry |
  | Chain verification, exposed (AU-9, AU-3) | No verification surface | **Implemented**: `GET /audit/verify` exposes `verify_chain()` (audit_read) |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: an audit write failure raises `AuditWriteError`; the store snapshots state before every mutating method and rolls back in full on failure — no object, no change, no id consumed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query` plus matching `GET /audit` filter parameters (`actor`, `action`, `target`, `since`, `until`) |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role (`dana`) holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Admin retains all actions including `audit_read`; `member` = all except `audit_read`; `viewer` = `matter_read` + `report_read`. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 34, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

  Platform notes, stated plainly: TLS only when configured;
  single-tenant reference deployment.

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the crosswalk is a planning/matching equivalence.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `lawenf` under `src/`,
runnable and testable with `PYTHONPATH=src`. The contract is Group
34's, unchanged except for the uplift deltas marked **[L3]**:
ids are sequential per object type with fixed prefixes (`mat-`,
`src-`, `doc-`, `sea-`, `ann-`, `cit-`); a failed operation consumes
no id and changes nothing. All timestamps are UTC ISO-8601.
Validation always precedes mutation.

- `lawenf/errors.py` — `LawEnfError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`, plus **[L3]**
  `AuditWriteError` (all deriving from `LawEnfError`).
- `lawenf/access.py` — `User(name, role)`; roles
  `admin|member|viewer|auditor` **[L3]**; actions `matter_read,
  matter_write, source_write, document_write, search_write,
  annotation_write, citation_write, report_read, audit_read`.
  `PERMISSIONS`: admin ⊇ all nine; member = all except
  `audit_read`; viewer = {matter_read, report_read}; **[L3]**
  auditor = {audit_read} only. `permissions_for(role)`, `can(user,
  action)`, `require(user, action)` raising `PermissionDenied`.
- `lawenf/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry dict with keys `ts, actor, action,
  target, details` plus **[L3]** `seq, prev_hash, hash` (SHA-256 of
  the canonical JSON of the entry; genesis `prev_hash` = `"0"*64`);
  raises **[L3]** `AuditWriteError` and rolls back the in-memory
  append if the JSONL write fails. `.entries()` returns all
  entries. **[L3]** `.query(actor=None, action=None, target=None,
  since=None, until=None)` returns filtered entries;
  `.verify_chain()` returns `(ok, first_bad_index_or_None)`.
  Append-only; optional JSONL file persistence; reloads an existing
  file on construction, and loaded entries participate in chain
  verification.
- `lawenf/store.py` — `LawEnfStore(audit=None)`. Entity shapes and
  methods **unchanged from Group 34**; **[L3]** every mutating
  method is wrapped in a fail-closed snapshot guard (`_atomic`):
  the store snapshots state before the method runs and, if the
  audit write (or any part of the operation) fails, rolls back in
  full — no object, no change, no id consumed — and the
  `AuditWriteError` propagates. The store records every successful
  mutation to its audit log (when one is attached); the HTTP layer
  records denials and `audit_read` only. Two boundaries on every
  matter-scoped operation: the actor must be a matter member or
  hold the platform `admin` role, else `PermissionDenied`; and the
  operation's role permission is required (enforced when the actor
  is a `User`; a plain-string actor carries identity but no role,
  so role enforcement for those happens in the service layer — the
  house convention). Methods:
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
  users, max_failures=3, lockout_seconds=300)` **[L3 kwargs]** →
  `http.server.ThreadingHTTPServer`; `users` maps name → role.
  Auth via `X-User` / `X-Role` headers (the role must match the
  registry; unknown user or mismatched role → 401). **[L3]**
  consecutive auth failures are tracked per username; at
  `max_failures` the username locks for `lockout_seconds` (403,
  audited `auth:locked`); success resets the counter. Errors are
  JSON `{error}` with 400/401/403/404 as applicable; denied attempts
  (401 and 403) are audited with the action name suffixed `:denied`,
  and no stack trace is ever returned. The service layer is the only
  place query text or note text may appear: it SHA-256-hashes
  `query_text` / `note_text` request fields before calling the
  store, and never logs or stores the text. Endpoints: Group 34's
  endpoint set, plus the **[L3]** items marked below:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`; **[L3]**
    optional filter params `actor, action, target, since, until`
  - **[L3]** `GET /audit/verify` (audit_read) →
    `{"ok": bool, "entries": n, "first_bad_index": int|null}`
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
  [--audit-log PATH] [--certfile --keyfile] [--max-failed-logins N]
  [--lockout-seconds S]` **[L3 flags]** with demo users
  `alice=admin, bob=member, carol=viewer, dana=auditor` **[L3]**
  (documented as demo identities; production identity is the
  embedding organization's, per IA-2 above). Default port 8797.

Tests live in `tests/` (stdlib `unittest`): the inherited Group 34
suite, adapted for the uplift, plus new uplift tests, each test
docstring naming the core function / spec claim / control family it
traces to. **Negative controls:**

- The inherited membership-guard mutant (one that performs no
  membership check at all, so any authenticated actor can read any
  matter) and the inherited verify mutant (one that reports
  `matches` True for any content) — in-suite, as in Group 34. The
  canonical expectations are shown to reject both — an outsider
  read must raise `PermissionDenied` from the real store, and
  altered content must read `matches: False`.
- **[L3]** The audit-tamper negative control, new at High: mutating
  a stored audit entry in place makes `verify_chain()` report
  failure at exactly that entry's index, and a JSONL line edited on
  disk is detected after reload — proving the chain catches the
  tampering defect class rather than merely existing.

The membership-guard mutant must additionally be
**mutation-verified**: patching the real membership guard in `src/`
with the mutant must make the suite fail. The membership-guard
mutation drill was performed against the real source in this tree;
its run and result are recorded in `tests/README.md`.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (**0 claims total; both spec sheets are
  zero-claim sheets** under Group 34's verbatim taxonomy, full
  descriptions preserved).
- Core: 11 core functions carried whole from Group 34 at the High
  baseline, each with tracing tests; **0 of 11 claimed by this
  group's forks** — carried, not claimed, under the recorded
  core-boundary decision.
- Uplifts: 6 tier uplifts implemented (hash-chained audit,
  fail-closed audit writes, audit query/reduction, chain
  verification endpoint, logon lockout, auditor role).
- Extended: the legal-research long tail carried from Group 34's
  union (the legal corpora themselves, citation-validation engines,
  editorial enhancement systems, corpus search & relevance engines,
  AI/ML research assistance (0 claims at either tier), document
  content storage/rendering/redaction) **and** this group's own
  verticals (8: device unlocking, evidence extraction from mobile
  devices, forensic analysis engines, evidence ingest & processing
  pipelines, evidence review, chain-of-custody enforcement over
  evidence, information sharing / collaboration over evidence,
  forensic reporting) — all specified and ranked, **not**
  implemented in this build. Category-discipline exclusions
  (surveillance, facial recognition, predictive policing, real-time
  intelligence feeds): 0 claims, not built.
- Named absences (unclaimed at L2, for the legal-research side):
  incident/case management, evidence management & chain of custody
  as an operational system, criminal records/RMS, investigative
  case files — with the L3 nuance recorded above: this group's
  forks do claim forensic evidence functions in their own words,
  itemized as this group's Extended verticals.
- Baseline gaps named, not implied closed: MFA / authenticator
  management (IA-2(1)/(2), IA-5 — demo identities are hooks, not an
  IdP); FIPS-validated cryptography (SC-13 — Python stdlib is not a
  FIPS-validated module, not claimed); encryption at rest (SC-28 —
  deployment layer); audit retention enforcement (AU-11); session
  lock/termination (AC-11/AC-12 — per-request header auth, no
  session state).
- Platform-layer: TLS only when configured; single-tenant
  reference deployment.
