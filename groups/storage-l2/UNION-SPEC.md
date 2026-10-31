# Union Spec — Storage, CMMC L2 (DeadRamp Phase 2 remainder, Storage L2 singleton)

The singleton spec for the **Storage** category at the L2 tier:
**1 fork**, a category with no shipped group at any tier —
**Proofpoint Email Archive** (Proofpoint, Inc.), FedRAMP
**Moderate**, FedRAMP Certified, SaaS, Government Community
Cloud. Built under the remainder census unit
`new-singleton:Storage|L2`.

**Membership provenance, stated plainly:** `forks.json` files
this fork "Uncategorized (none in source)" at tier L2 — its
source record carries an empty `business_categories` list. The
DeadRamp category is the **remainder census proposal**
("Storage"; classifier note: "Email archiving, retention, search
and retrieval"), taken from the fork's own description: its
primary function is message archiving storage, a function none
of the shipped categories covers. Reconciliation:
`remainder.json` unit == `specs/specs.json` == {F1304222071},
zero diff, and the fork's own recorded fields (Moderate,
FedRAMP Certified, L2) match the source record exactly. MAP.md's
category arithmetic is unaffected: this fork was never in
MAP.md's category counts, because MAP.md counts the Phase 1
category field. This group's number is assigned in the repo
README at ship; this spec deliberately carries none. A sibling
unit (`new-singleton:Storage|L3-adjacent`) will be built later
carrying this group's substrate up a tier; this spec is written
to serve as its parent.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, every
claim carrying the source sentence as evidence. Source: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID **F1304222071**.

## How functions were counted (a new category: the Group 1 method)

Storage has no parent group, so there is no inherited taxonomy.
The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern,
matched against the description's sentences by
`scratch/extract.py`. A function is claimed **only** when a
sentence contains matching text; the first matching sentence is
stored as the claim's evidence in the spec sheet. Marketing
prose gets no tags. **11 claims in total, one per family** — the
single fork claims every family its own vocabulary defines.
Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
sentence 1's "protect an organization from legal liabilities and
regulatory risks" is benefit prose and tags nothing (no
legal-hold family is carved out of it; legal hold is a checked
absence); sentence 1's "end-user productivity" is outcome prose,
while "email storage management" in the same sentence is claimed
as its own family at that weight; sentence 9's guarantee prose
("guarantees the security of data...") carries no encryption
pattern, deliberately — the encryption claim rests on the
mechanism sentences (8, 10, 11); sentence 5's "tight integration"
positioning tags nothing (the integration families rest on
sentences 6 and 7); sentence 12 restates the key-custody
property as an access consequence and tags nothing; the web
interface is an access surface, not a family. The source
record's `certified_services` is empty — no third-party
catalogue exists — and no sentence is a scope-exclusion
sentence, so **nothing was removed before matching: raw hits ==
claims, 11 == 11**.

**Census citation accounting:** both census citations verify as
strict verbatim substrings of the description (2/2), and both
are also claim-bearing sentences — citation 1 (sentence 1) is
the stored evidence for `message_archiving` and
`storage_management`; citation 2 (sentence 3) is the stored
evidence for `retention` and `retrieval_export`. Verification
and claiming coincide here, recorded as the coincidence
direction; no citation was load-bearing, because every claim
rests on the description itself.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Message archiving | 1 | **Core** — archive collection & message records (metadata form; the payload plane is Extended) |
| 2 | Email storage management | 1 | **Core** (records) — collections and message records are its records form; capacity machinery is not described and not built |
| 3 | Retention for a specified period | 1 | **Core** — retention policy records, the retention derivation, and the disposition gate |
| 4 | Search & discovery | 1 | **Core** (records) — discovery request records and metadata search; the full-text content search engine is Extended |
| 5 | Supervision | 1 | **Core** (records) — supervision review records; the review console is Extended |
| 6 | Policy enforcement | 1 | **Core** (records) — enforcement action records; enforcement execution in connected systems is Extended |
| 7 | Retrieval & export | 1 | **Core** (records) — retrieval/export request records; delivery transport and file production are Extended |
| 8 | Mail platform integration (native format) | 1 | **Core** (records) — an integration registry entry; the live connector and ingest pipeline are Extended |
| 9 | Directory integration & unified login | 1 | **Core** (records) — an integration registry entry; identity itself stays with the embedding organization (IA-2 hooks) |
| 10 | Message encryption & decryption | 1 | **Extended** — the encryption/decryption engine itself; the build holds no payloads and performs no cryptography |
| 11 | Customer-held encryption key custody | 1 | **Core** (records) — key custody records (custodian reference + key label, never key material); key generation and custody hardware are Extended |

**Named absences, stated plainly (token-verified; full list in
`scratch/ARTIFACTS.md`):** the description contains **no object,
block, or file storage vocabulary at all** (no buckets, volumes,
or shares), **no backup, restore, snapshot, replication, or
disaster-recovery vocabulary**, **no deduplication, compression,
tiering, lifecycle, versioning, capacity, or quota vocabulary**,
**no WORM or immutability vocabulary** (retention is claimed;
immutability is not), **no legal-hold vocabulary** (the one
"legal" phrase is benefit prose), **no audit vocabulary**, **no
journaling, migration, or content-scanning vocabulary**, and
**no "at rest" or FIPS vocabulary**. The category name promises
generic storage; the fork's own words define it as message
archiving storage, and nothing else was claimed, so nothing else
is owed. None of the absences is a gap in the registry sense:
nothing was claimed, so nothing is owed.

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *Metadata, never payloads.* The substrate
holds records about archived messages — references, moments,
sizes, format labels. It stores no message content of any kind:
no subject, no body, no attachment. The record shape is pinned
so no field could hold one, and the pinned shape is enforced by
a recursive scan in the tests. The byte storage of the messages
themselves is the Extended payload plane. (2) *Retention is a
derivation, not a state.* A message's retention state is
computed at read from recorded values (archived-at moment, the
collection's policy period, the presence of a disposition
record) by a single seam; it is never stored, so it cannot drift
from the records. Disposition is gated on that derivation — a
recorded decision procedure, not a person's decision — which is
why no separation-of-duties claim arises from it (see precision
notes). (3) *Custody records hold no keys.* A custody record
names a custodian by opaque reference and a key by opaque label.
No key material is accepted, stored, or derivable from anything
in this build; key generation, storage hardware, and all
cryptography are Extended. (4) *Registries never execute.* The
integration registry records that an integration exists; it
connects to nothing, authenticates no one, and moves no message.
Enforcement records likewise record actions taken; an
`extend_retention` record does not alter any derivation, which
answers only to the collection's policy record — pinned by
test. (5) *Discovery has no free-text field.* A discovery record
names a matter, a collection, and metadata scope (sender
reference, date window); the result set is computed from the
archive records at recording time. The substrate holds no
content, so there is no content here for a query to name.

## The Core — what the merged build implements (14 functions)

One coherent, standards-based message-archiving records service
that the fork's claimed functions presuppose, built clean-room
from this spec:

1. **Organization registry (opaque references)** — organizations
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier.
2. **Retention policy records** — policies (`pol-`): a label and
   a retention period in whole days (integers only; booleans and
   floats rejected at the boundary). Policies are immutable once
   recorded — there is deliberately no update operation — so a
   retention derivation is always reproducible against the
   policy the collection named.
3. **Archive collection registry** — collections (`col-`) opened
   for an organization under a retention policy, with a
   caller-stated format label (a label, not a conversion).
4. **Message archive records** — records (`msg-`) of archived
   messages: an opaque `message_ref` (unique within the
   collection), opaque sender/recipient references, the
   archived-at moment, a recorded size in bytes, a format label,
   an optional key-custody link, and a store-assigned sequence.
   Metadata only — see core-boundary decision 1. A message may
   be archived under a custody record only if that record
   belongs to the same collection and is active.
5. **Retention derivation & the disposition gate (the signature
   invariant)** — a message's retention state
   (`retained` / `disposition_eligible` / `disposed`) is derived
   at read by the single seam `_derive_retention_state` from the
   archived-at moment, the policy period, and the presence of a
   disposition record; `retention_until` is the derived
   boundary. The stored record carries no state key. Disposition
   records (`dsp-`) may be recorded **only** when the derived
   state at the disposition moment is `disposition_eligible`:
   inside retention the gate refuses, and a disposed message
   cannot be disposed of again. The record states that
   disposition occurred; destroying payload bytes is the
   Extended storage plane's — this store holds none.
6. **Discovery request records** — records (`dsc-`) of search &
   discovery requests: an opaque matter reference, the
   collection, optional sender/date scope, and the result count
   and message ids computed from the archive records at
   recording time. No free-text query field exists (decision 5).
7. **Supervision review records** — reviews (`sup-`) of archived
   messages for a reviewer (opaque reference), with an
   event-driven lifecycle (`pending → reviewed`,
   `pending → escalated → reviewed`; `reviewed` is terminal)
   changed only by recorded outcomes with verbatim notes.
8. **Enforcement action records** — records (`enf-`) of
   enforcement actions from a fixed action vocabulary
   (`block_access`, `block_export`, `extend_retention`,
   `block_disposition`, `flag_for_review`) against an opaque
   target under a stated policy reference. Records only
   (decision 4).
9. **Retrieval & export records** — requests (`ret-`) to
   retrieve an archived message in real time or in batch, to an
   inbox, a data file, or the interface, with completion by
   recorded action. Delivery transport and file production are
   Extended.
10. **Key custody records** — records (`key-`) naming, per
    collection, the custodian (opaque reference) and the key
    (opaque label), with an active/retired lifecycle. **At most
    one active custody record per collection** — the fork's own
    statement is that a single holder holds the keys, kept here
    as a record invariant. No key material exists in any shape
    (decision 3).
11. **Integration registry (records only)** — records (`int-`)
    of the two claimed integrations (`mail_platform`,
    `directory`) per organization, with an active/inactive
    lifecycle. Registering one connects nothing (decision 4).
12. **Search & summary reporting** — literal case-insensitive
    substring search over organizations, policies, collections,
    and message metadata; and a summary computed on read from
    records only: registry counts, messages by derived retention
    state at a stated `now`, disposition and discovery counts,
    supervision by status, enforcement count, retrieval counts,
    active custody count, integrations by kind. Counts and
    recorded values — never scores.
13. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that
    speaks HTTP.
14. **Access control & audit log** — role-based access hooks:
    platform roles `admin`, `operator`, `viewer` with a
    permission matrix enforced on every operation; and an
    append-only audit trail recording every mutation and every
    denied attempt, with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability) — Moderate / L2

- **Singleton tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (this
  fork's impact level, recorded as-is) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to
  the 110 practices of NIST SP 800-171 Rev. 2 that define CMMC
  L2. One fork at one tier, so no merge changes the tier (Merge
  Rules 1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the
  Moderate baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Organization, policy & collection registries | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness and integer validation are enforced in the store; identity itself is supplied by the embedding organization |
| Message archive records | AU-2, AU-3, SI-10 | Metadata records are validated on write (integer sizes, parseable moments, per-collection reference uniqueness); the pinned shape admits no content |
| Retention derivation & disposition gate | CM-6, AU-2, AU-3 | State is derived at read from the records by a single seam (`_derive_retention_state`), so it is reproducible from the records and the trail; the gate is the same seam, so gate, view, and summary can never disagree |
| Discovery records | AU-2, AU-3, AC-3 | Requests are explicit, scoped records with computed result sets; creating one requires the `discover` permission |
| Supervision review records | AU-2, AU-3, AC-3 | Reviews have an auditable, recorded-action lifecycle; outcomes carry the actor's name in the trail |
| Enforcement action records | AU-2, AU-3 | Actions are recorded from a fixed vocabulary with actor and timestamp; execution is Extended |
| Retrieval & export records | AU-2, AU-3; SC-8 (transport is Extended) | Requests and completions are recorded; the delivery transport itself is outside this build |
| Key custody records | AC-3, CM-6 | Custody is an explicit, access-gated record set with a one-active-per-collection invariant; no key material exists here, so no SC-12/SC-13 claim arises (see precision notes) |
| Integration registry | CM-6, AC-3 | Integrations are configuration-controlled records; the registry performs no connection |
| Summary reporting & search | AU-2, AU-3; AC-3 | Deterministic counts over the records at a stated `now`; literal search over registered metadata only, permission-gated |
| RBAC | AC-2, AC-3, AC-6, IA-2 (hooks) | Three-role matrix enforced before any mutation or id allocation, at the store and again at the service layer; `audit_read` is admin-only |
| Audit log | AU-2, AU-3, AU-6, AU-9 | Append-only log including denied attempts; no mutation API; audit reads are restricted to the `audit_read` permission and are themselves audited at the service layer |

- **Precision notes (what Moderate does and does not carry,
  stated so nothing is silently imported from other tiers'
  tables):**
  - **Audit:** AU-2/AU-3/AU-6/AU-9 are Moderate selections and
    are claimed as above: append-only storage (AU-9) and a
    restricted, itself-audited read path (AU-6). Hash-chained
    audit, fail-closed audit writes, audit query/reduction
    (AU-7), logon lockout (AC-7), and a separate auditor role
    are High answers from sibling groups and are **not** claimed
    here.
  - **Separation of duties:** no AC-5 claim arises.
    Dispositions are gated by a derivation over recorded
    values, not decided by a person, so there is no
    decider/submitter seam to separate; supervision outcomes are
    recorded actions by named actors, visible in the trail.
  - **Cryptography:** SC-12 (key establishment & management)
    and SC-13 (cryptographic protection) are **not** claimed.
    This build holds no key material and performs no
    cryptography; the fork's encryption technology and key
    custody are its platform properties, recorded as claims
    about the fork and as Extended gaps for any build that
    would perform them — they do not transfer.
  - **Transmission:** SC-8 holds only when a certificate is
    configured (`--certfile`/`--keyfile`); the default serve
    mode is plain HTTP for local/demo use, and encryption at
    rest is a deployment-layer control, stated plainly and not
    claimed here.
- **Caveat (standing, from crosswalk.md):** this traceability
  is a planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the
  Moderate/L2 control families. FedRAMP authorizes products;
  CMMC certifies organizations — neither regime accepts the
  other as evidence, and any real compliance claim still has to
  be earned inside each regime separately.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `storage` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`, `pol-`,
`col-`, `msg-`, `dsp-`, `dsc-`, `sup-`, `enf-`, `ret-`, `key-`,
`int-`); a failed operation consumes no id and changes nothing.
Sizes and retention periods are integers; a bool, float, or
string where an integer is required raises `ValidationError`.
Any state that depends on a date (retention state) is derived at
read and never stored; event-driven lifecycle state (a review's
status, a retrieval's completion, a custody record's
active/retired, an integration's active/inactive) is stored, as
in the sibling builds' record lifecycles.

- `storage/access.py` — `User(name, role)`; roles
  `admin|operator|viewer`; `PERMISSIONS`: admin ⊇ {read,
  register, archive, discover, supervise, enforce, retrieve,
  custody, audit_read, admin}, operator = {read, register,
  archive, discover, supervise, enforce, retrieve, custody},
  viewer = {read}; `require(user, action)` raises
  `PermissionDenied`.
- `storage/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `storage/store.py` — `StorageStore(audit=None)` with the
  operations named in the Core above. Role permission is
  enforced for User-like actors before any state change or id
  allocation; a plain-string actor carries identity only, and
  enforcement for those happens in the service layer (the
  sibling builds' convention). The store audits every successful
  mutation; the service layer audits denied attempts
  (`action:denied`) and audit reads, so nothing is recorded
  twice. The retention derivation lives in the single seam
  `_derive_retention_state(archived_at, retention_days,
  disposed, now)`.
- `storage/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  Endpoints per the group README. Errors are JSON `{error}` with
  400/401/403/404 as applicable. Denied attempts are audited.
- `storage/__main__.py` — `python -m storage serve --host
  --port [--audit-log PATH] [--certfile --keyfile]` with demo
  users `alice=admin, bob=operator, carol=viewer` (documented as
  demo identities; production identity is the embedding
  organization's).
- `storage/errors.py` — `StorageError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**:
an in-tree mutant seam under which retention never expires, so
the disposition gate never opens — if the suite passed against
it, the retention tests would be testing that code ran, not that
retention is enforced — plus the external mutation drill (the
same patch applied to the real `store.py`); see `tests/README.md`
for the counts and the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Archived payload storage plane (the actual byte storage of
  archived messages — object/file/block storage, however
  realized; this build holds metadata records about messages,
  never the messages)
- Archive ingest pipeline (capture from the mail platform —
  journaling or connector-based — and native-format conversion
  and normalization)
- Full-text content indexing & search engine (searching message
  bodies and attachments; this build searches record metadata
  only and holds no content to index)
- Encryption & decryption engine (the fork's named
  encryption technology or any other; including cryptographic
  key generation)
- Key management hardware & premise equipment (the custodian
  appliance, software-based or hardware-based, that would hold
  keys inside the customer environment)
- Retrieval delivery transport & export file production
  (delivering a retrieved message to an inbox, producing the
  export data file; this build records the requests and their
  completion)
- Supervision review console & workflow engine (sampling,
  reviewer queues, and the review interface; this build keeps
  the review records)
- Policy enforcement execution (acting on enforcement decisions
  in connected systems; this build records the actions)
- Mail platform & directory connectors (the live integrations;
  this build keeps the registry records, and identity stays
  with the embedding organization)
- Disposition execution (destruction of archived payload bytes
  when retention expires; this build records that disposition
  occurred and holds no payloads to destroy)

Platform-layer: FIPS-validated cryptography (SC-13) is not
stated by the fork and not claimed by this build — any
validated-module requirement is a platform property to be
satisfied at the platform layer; encryption at rest is
deployment-layer (TLS when configured); multi-tenancy
(single-tenant reference deployment); demo identities are
hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **11 tagged claims** (one
  per taxonomy family, each with its source sentence as
  evidence).
- Core: **14 / 14** core functions implemented, at the
  Moderate/L2 baseline, each with tracing tests.
- Tests: see `tests/README.md` for the count (filled in from
  the build, not stated here), including the mutation-verified
  retention-derivation negative control.
- Extended: the 10 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
