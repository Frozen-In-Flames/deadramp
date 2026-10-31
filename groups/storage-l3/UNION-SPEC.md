# Union Spec — Storage, CMMC L3-adjacent (DeadRamp Phase 2 remainder, Storage L3-adjacent singleton)

The singleton fork at this tier is **Commvault Cloud for
Government** (Commvault Systems, Inc., FR2115384377) — FedRAMP
**High**, FedRAMP Certified, SaaS, Government Community Cloud.
The remainder census files it as census unit
`new-singleton:Storage|L3-adjacent` in the **Storage** category
the L2 singleton founded (classifier note: "Primary function is
data backup and recovery / protected storage"); `forks.json`
files it "Uncategorized (none in source)" and its source record
carries an empty business-categories list. The category here is
the census proposal, not a source field — recorded as such in
the spec.

**The headline finding is a zero.** Spec'd under the category's
existing 11-family taxonomy, verbatim, Commvault's description
claims **no family at all**: its prose describes a backup and
recovery service, not the message-archiving records surface the
founding fork's vocabulary defined. Zero is the honest spec
result, recorded plainly below — the taxonomy was not re-tuned,
no family was carved out of near-miss prose, and substance
without phrases became named gaps. This is the in-category
mirror of findings elsewhere in the remainder (Health &
Wellness L3's zero, MDM's mirror finding).

Because the category already has a substrate, the build is not
empty: under the Merge Rule the union at this tier is the
**union** of the L2 substrate and this fork's (empty) claim set,
at the **highest** tier — so the Storage L2 core is carried up
whole and uplifted to the High baseline, and every carried
function is flagged **carried, not claimed** for this fork.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

| | |
|---|---|
| Parent build | `groups/storage-l2/` — Storage at CMMC L2 (Proofpoint Email Archive, 11 claims, 14 core functions) |
| This build | Storage at CMMC **L3-adjacent** ⇔ FedRAMP **High**, 1 fork, **0 claims** |
| Merge Rule 1 (union of baselines) | The union baseline is the High baseline in full; nothing from the Moderate baseline is diluted or dropped |
| Merge Rule 2 (highest tier inherits) | The merged fork sits at L3-adjacent; the L2 core is extended upward, never diluted downward |
| Merge Rule 3 (traceability) | Every carried function traces to the parent's spec; every uplift traces to the High baseline demand that required it (table below) |
| SSDF | Built per NIST SP 800-218 practice: stdlib-only, tests-before-ship, mutation-verified negative controls on both signature seams |

Thinner prose at a higher tier is not a downgrade: the substrate
is carried whole, and the difference between what the parent
fork *claimed* and what this fork claims is stated once, here,
and nowhere blurred.

## How functions were counted — 0 claims, honestly

The taxonomy is the founding group's, **verbatim**: the 11
families defined from Proofpoint Email Archive's own description
by `groups/storage-l2/scratch/extract.py`. This group's
extractor (`scratch/extract.py`) parses the `TAXONOMY` literal
out of that file with `ast` — parse, never execute — and,
before tagging the newcomer, reproduces the parent's shipped
claim table **exactly** (11 claims, deep-equal including every
evidence sentence) from the parent's description. That
taxonomy-verbatim proof passed; only then was Commvault tagged.

Commvault's description splits into 5 fragments. Fragment 2 is
a **workloads catalogue** (marker: "capabilities include the
following workloads" — Microsoft 365, Dynamics 365, Salesforce,
Active Directory, VM & Kubernetes, Endpoint, File & Object,
Database, Air Gap Protection) and is **excluded before
matching**, per the standing exclusion discipline for
third-party hosted-app catalogues (the FedHIVE precedent): a
catalogue of protected workloads is a list of other products,
not a statement of this service's own functions. Raw hits
across all fragments: **exactly 1** — `directory_integration`
on "Active Directory" inside the catalogue, where it names a
protected workload (backed up "For Entra ID and Active
Directory"), not unified-login integration. That hit was
removed by the exclusion and is recorded in
`scratch/raw_hits.json`. Kept hits: **0**. Claims: **0**.

Near-misses (token counts over the full description; the full
record is `scratch/ARTIFACTS.md`):

- **backup ×1, recovery ×2** — the fork's headline function,
  stated in its first sentence. No family in the taxonomy covers
  backup or recovery; the taxonomy was built from an archiving
  fork's vocabulary. Substance without a family → named gap
  (backup & recovery engine), never a re-tuned pattern.
- **"key word search" ×1** (sentence: data is "searchable via
  key word search"), with `searchable` as a standalone token at
  ×0 and none of `search_discovery`'s phrases present — an
  instance of the parent's already-registered full-text content
  search gap. Referenced, not re-registered.
- **Air Gap Protection** is described as "secure and scalable
  cloud storage" for critical data — an instance of the parent's
  archived-payload storage plane gap, with air-gap isolation
  noted there. Bare "storage" occurs as a noun; "storage
  management" ×0 — no `storage_management` claim.
- **audit ×1** ("integrated audit reports") — see the absence
  accounting below.
- **"synchronization" ×1** with `replicat` ×0 — hybrid-cloud
  synchronization substance → named gap.
- **retention ×0.** The founding fork's signature family does
  not occur in this fork's prose at all. Notable, and stated
  plainly: the carried retention substrate below is the
  parent's, not this fork's claim.
- **encrypt ×0, decrypt ×0** — the description's only "key"
  token is "key word search". No encryption claim, no custody
  claim.
- **console ×2** (the "Command Center" management console),
  **monitoring ×1**, **alert ×1 + anomal ×1**, **remediat ×1** —
  substance → named gaps below.
- **IL4 & IL 5 ×2** — the fork states its platform operates at
  IL4/IL5. That is the fork's platform property; it does **not**
  transfer to this build (SC-13 stays a named gap, as at every
  tier).

**Census citation accounting:** the single census citation
verifies as a strict verbatim substring of the description
(1/1), tags no family, and is the evidence for no claim — there
are no claims. Verification is not claiming, in either
direction, and the citation was not load-bearing: the zero
rests on the description itself.

## Function ranking — the singleton

All 11 families at **0 forks claiming**. Every disposition is
**carried substrate**: the records form the parent build
implements, carried up whole under the Merge Rule and flagged
carried-not-claimed for this fork.

| # | Function (taxonomy family) | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Message archiving | 0 | **Carried substrate** — archive collection & message records (parent core 3–4) |
| 2 | Email storage management | 0 | **Carried substrate** — collection and message records (parent core 3–4) |
| 3 | Retention for a specified period | 0 | **Carried substrate** — retention policy records, the retention derivation, and the disposition gate (parent core 2, 5). The fork's prose never says "retention" |
| 4 | Search & discovery | 0 | **Carried substrate** — discovery request records and metadata search (parent core 6, 12); the fork's keyword search is an instance of the parent's Extended full-text gap |
| 5 | Supervision | 0 | **Carried substrate** — supervision review records (parent core 7) |
| 6 | Policy enforcement | 0 | **Carried substrate** — enforcement action records (parent core 8) |
| 7 | Retrieval & export | 0 | **Carried substrate** — retrieval/export request records (parent core 9) |
| 8 | Mail platform integration (native format) | 0 | **Carried substrate** — integration registry entries (parent core 11); the catalogue's Microsoft 365 / Dynamics 365 / Salesforce names are protected workloads (gap: workload protection connectors), not this build's integrations |
| 9 | Directory integration & unified login | 0 | **Carried substrate** — integration registry entries (parent core 11); the description's "Active Directory" is a protected workload inside the excluded catalogue, not unified login |
| 10 | Message encryption & decryption | 0 | **Extended** (as at L2) — the encryption/decryption engine; this fork's prose contains no encryption token at all |
| 11 | Customer-held encryption key custody | 0 | **Carried substrate** — key custody records (parent core 10); the fork's prose contains no custody statement |

**Named absences, rechecked token-by-token against THIS fork
(full record in `scratch/ARTIFACTS.md`):**

- **Standing** (verified absent from this description, token
  counts 0): retention, legal hold (and bare "hold"),
  immutability / WORM, FIPS, "at rest", supervision,
  enforcement, "storage management", searchable (standalone),
  encrypt / decrypt, deduplication, compression, tiering,
  versioning, capacity, journaling, migration, snapshot,
  replication, malware, quota, lifecycle, ingest.
- **Object storage** stands **at claim level**: "object
  storage" occurs exactly once, inside the excluded catalogue,
  as part of the workload name "OCI Object Storage" — a
  protected workload label, not a statement that this service
  provides object storage.
- **Retired in substance — two of the parent's named
  absences:**
  - **Backup** (parent absence) — this fork's description
    states a "data backup and recovery solution" as its headline
    function. The absence retires **in substance**: backup is
    what this fork *is*. It still produces no claim (no family
    covers it) and no build function; it is registered as the
    backup & recovery engine gap. Retirement recorded on this
    fork's own words only.
  - **Audit** (parent absence) — this fork's description states
    "integrated audit reports". The absence retires **in
    substance**: the carried audit substrate (parent core 14,
    uplifted below) is the records form this statement
    presupposes. Still no claim: "audit reports" fires no
    taxonomy family, and none was carved out for it.
- Absence retirements rest only on this fork's own words and
  do not transfer across tiers, in either direction: the
  parent's absences stand in the parent's spec, and this fork's
  standing absences are recorded here, not inherited.

## The Core — what the merged build implements (14 functions, carried)

**Core-boundary decision (stated once):** all 14 core functions
of the Storage L2 build are carried up whole under the Merge
Rule, uplifted to the High baseline where the baseline demands
more (audit, access). **No core function is claim-supported by
this fork** — the fork claims nothing — so every function below
is carried substrate, present because the union inherits the
parent's core in full, and flagged carried-not-claimed wherever
this group's documents enumerate claims. Nothing was dropped
for having no claim here; dropping carried substrate at a
higher tier would dilute the union, which Merge Rule 1
forbids.

The parent's five core-boundary decisions carry with the core,
unchanged:

1. **Metadata, never payloads** — message records hold opaque
   references and recorded values only; no field can hold a
   subject, a body, or any content.
2. **Retention is a derivation** — retention state is computed
   at read by the single seam `_derive_retention_state`; no
   state field is ever stored, so gate, view, and summary can
   never disagree.
3. **Custody holds no keys** — a custody record is a custodian
   reference and a key label; no key material exists in any
   shape, and at most one custody record per collection is
   active.
4. **Registries never execute** — integration and enforcement
   records record; registering connects nothing, enforcing
   executes nothing.
5. **Discovery has no free-text field** — a discovery record
   names a matter, a collection, and a metadata scope; there is
   no content here for a query to name.

The 14 functions (parent numbering; full descriptions in the
parent spec): 1 organization registry; 2 retention policy
records (immutable, integer days); 3 archive collection
registry; 4 message archive records (metadata only); 5
retention derivation & the disposition gate (the signature
invariant); 6 discovery request records; 7 supervision review
records; 8 enforcement action records; 9 retrieval & export
records; 10 key custody records; 11 integration registry
(records only); 12 search & summary reporting (counts and
recorded values, never scores); 13 API access (REST/JSON); 14
access control & audit log — uplifted at this tier, below.

## Control baseline (traceability) — High / L3-adjacent

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High**
  (this fork's impact level, recorded as-is) per
  `../../crosswalk.md`. "Adjacent" remains deliberate wording:
  L3 is not identical to FedRAMP High; it is the same assurance
  weight class.
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline
  (the FedRAMP High tailoring), cross-walked to the CMMC L3
  basis: the 110 practices of NIST SP 800-171 Rev. 2 **plus**
  the selected NIST SP 800-172 enhanced requirements. The
  parent build sat at Moderate; the union baseline is the High
  baseline, un-diluted (Merge Rule 1), inherited in full
  (Rule 2).
- **Feature → control family mapping (this build, at the High
  baseline):** the parent's Moderate table carries up unchanged
  for functions 1–13 (AC-3, CM-6, SI-10, AU-2, AU-3, AC-3 as
  there); the rows that change at High are function 14's:

| Core function | Control families | How the build answers at High |
|---|---|---|
| RBAC | AC-2, AC-3, **AC-5**, AC-6, IA-2 (hooks) | Four-role matrix enforced before any mutation or id allocation, at the store and again at the service layer; `audit_read` is held by admin **and** the separated **auditor** role, which holds nothing else (AC-5, technical slice) |
| Audit log | AU-2, AU-3, **AU-5**, AU-6, **AU-7**, AU-9 | Append-only, **hash-chained** log including denied attempts; no mutation API; audit reads are gated on `audit_read`, are themselves audited, accept reduction filters, and the chain is verifiable via `GET /audit/verify` |
| Service authentication | **AC-7**, IA-2 (hooks) | Per-username consecutive-authentication-failure lockout in the service layer (defaults: 3 failures, 300 s), locked attempts answered 403 and audited `auth:locked`; permission denials do not count |

- **Tier-uplift analysis — what High demanded beyond the L2
  core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over the canonical JSON of {seq, ts, actor, action, target, details, prev_hash} (genesis `prev_hash` = `"0"*64`); `AuditLog.verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify`, whose count is read before its own audit entry is recorded |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; every mutating store method is wrapped so the whole operation (records + id counters, snapshot pattern) rolls back, and the service answers exactly 500 `{"error": "audit write failed"}`. Read methods are not wrapped: they record no audit entry on success, so there is no write to fail closed on — the scoping is stated in the store's docstring, as in the precedents |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` query parameters (inclusive bounds); an unfiltered `GET /audit` keeps the L2 shape |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts — even with the correct role — return 403 and are audited as `auth:locked`; a success resets the counter; an expired lock clears itself; unknown usernames lock too |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role (demo user `dana`) holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named — not taken**: identity-provider properties. This build ships hooks, not an IdP (the parent's posture, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named — not taken**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here. This fork's own IL4/IL5 platform posture is a property of the fork's deployment and does **not** transfer to this build |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged — not taken**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named — not taken**: no retention-period enforcement for the trail in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named — not taken**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Precision notes:**
  - **Cryptography:** SC-12 and SC-13 are **not** claimed, at
    High exactly as at Moderate. This build holds no key
    material and performs no cryptography beyond the audit
    chain's SHA-256 (an integrity mechanism, not a validated
    cryptographic module claim).
  - **Separation of duties:** the AC-5 claim at this tier is a
    technical slice only — a role that can review the trail and
    do nothing else. It arises here because the High baseline
    selects it and the uplift implements it; the parent build
    made no AC-5 claim, and none is back-ported.
  - **Transmission:** SC-8 holds only when a certificate is
    configured (`--certfile`/`--keyfile`); the default serve
    mode is plain HTTP for local/demo use, stated plainly.
- **Caveat (standing, from crosswalk.md):** this traceability
  is a planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the
  High/L3-adjacent control families. FedRAMP authorizes
  products; CMMC certifies organizations — neither regime
  accepts the other as evidence, and any real compliance claim
  still has to be earned inside each regime separately.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `storage` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`, `pol-`,
`col-`, `msg-`, `dsp-`, `dsc-`, `sup-`, `enf-`, `ret-`, `key-`,
`int-`); a failed operation consumes no id and changes nothing
— at this tier "failed" includes an audit-write failure, which
rolls the whole operation back. Sizes and retention periods are
integers; a bool, float, or string where an integer is required
raises `ValidationError`. Any state that depends on a date
(retention state) is derived at read and never stored;
event-driven lifecycle state is stored, as in the parent build.

The parent contract carries up with these deltas [L3]:

- `storage/access.py` — roles `admin|operator|viewer|auditor`;
  `auditor` = {audit_read} exactly; `ROLES` names all four.
- `storage/audit.py` — `AuditLog(path=None)`; entries are
  `{seq, ts, actor, action, target, details, prev_hash, hash}`;
  `.record(..., ts=None)` is fail-closed (AU-5); `.query(...)`
  reduces (AU-7); `.verify_chain()` → `(ok, first_bad_index)`
  (AU-9).
- `storage/store.py` — every mutating method wrapped
  `@_fail_closed` (snapshot/restore of all record dicts and id
  counters on `AuditWriteError`); `audit_read` requires the
  `audit_read` permission (admin or auditor).
- `storage/service.py` — `make_server(host, port, store, audit,
  users, certfile, keyfile, max_failures=3, lockout_seconds=300)`;
  routes add `GET /audit/verify` (audit_read); `GET /audit`
  accepts `actor`/`action`/`target`/`since`/`until`; AC-7
  lockout with `auth:locked` auditing; `AuditWriteError`
  anywhere in dispatch → exactly 500
  `{"error": "audit write failed"}` (handled before the generic
  `StorageError` clause, since `AuditWriteError` subclasses it).
- `storage/__main__.py` — demo users `alice=admin,
  bob=operator, carol=viewer, dana=auditor`; serve flags add
  `--max-failed-logins` / `--lockout-seconds`.
- `storage/errors.py` — adds `AuditWriteError(StorageError)`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. The suite carries **two** mutation-verified
negative controls at this tier: the inherited in-tree retention
mutant (the disposition gate never opens) and the audit-chain
tamper controls; plus **two external mutation drills** performed
live in this tree — the retention-gate drill failed exactly 10
tests, the audit-hash drill exactly 4 — with both files restored
SHA-256-identical. See `tests/README.md` for the counts and the
drill records.

## Gaps — specified, not implemented (for the GAPS.md final batch)

**New registrations from this fork's own prose** (substance
without a taxonomy family; named from its words):

- **Backup & recovery engine** — the fork's headline function
  ("a fully automated cyber resilient SaaS data backup and
  recovery solution"): scheduled and on-demand backup of
  protected workloads and their recovery. No family in the
  category taxonomy covers it; nothing in this build backs up
  or restores anything. NEW.
- **Anomaly detection & alerting engine** — the description's
  anomaly language with alerting ("anomaly" / "alert" tokens):
  detection over protected data and the alert path. NEW.
- **Granular data remediation engine** — the description's
  remediation language: acting on detected threats at data
  granularity. NEW.
- **Workload protection connectors** — the live connectors to
  the catalogue platforms (Microsoft 365, Dynamics 365,
  Salesforce, Active Directory / Entra ID, VM & Kubernetes,
  Endpoint, File & Object stores, databases). The catalogue was
  excluded from claiming; the connectors it names are specified
  here instead. NEW.
- **Management console (Command Center)** — the fork's named
  console surface: the operator interface over protection,
  monitoring, and reports. NEW.
- **SaaS operations automation** — "automated deployment,
  reduced overhead, automated patching and upgrades" and "no
  Agency maintenance": the vendor-side automation that operates
  the service itself. NEW.
- **Hybrid cloud synchronization engine** — the description's
  "synchronization" substance (with `replicat` at ×0):
  keeping protected data synchronized across hybrid estates.
  NEW.

**Referenced, not re-registered** (registered under the parent
union; this fork's prose touches them but adds no new
registration): the archived payload storage plane (Air Gap
Protection's "secure and scalable cloud storage" is an instance
of it, air-gap isolation noted); the full-text content indexing
& search engine ("key word search" is an instance of it); the
archive ingest pipeline; the encryption & decryption engine;
key management hardware & premise equipment; retrieval delivery
transport & export file production; the supervision review
console & workflow engine; policy enforcement execution; mail
platform & directory connectors; disposition execution.

**High baseline gaps** (from the uplift analysis, not taken):
MFA & authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13) — this fork's IL4/IL5
posture is its platform property and does not transfer;
encryption at rest (SC-28); audit retention (AU-11); session
lock / termination (AC-11/AC-12).

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **0 tagged claims** — the
  honest zero, under the parent taxonomy reproduced verbatim
  (taxonomy-verbatim proof: the parent's 11-claim table
  reproduced exactly before tagging). The single census
  citation verifies verbatim and is pinned as tagging no family
  and evidencing no claim. Near-misses and the absence
  accounting are itemized in `scratch/ARTIFACTS.md`.
- Core: **14 / 14** parent core functions carried up whole at
  the High baseline, **0 of them claim-supported by this fork**
  (carried, not claimed); 5 High uplifts implemented
  (hash-chained audit, fail-closed audit writes with store
  rollback, audit query/reduction, auditor role separation,
  logon lockout) and 5 named as gaps, not taken.
- Tests: **127** (see `tests/README.md`), including two
  mutation drills performed live in this tree (retention gate:
  exactly 10 non-passing; audit hash: exactly 4), files restored
  SHA-256-identical, suite green.
- Extended: the 7 new gaps above are specified and named,
  **not** implemented in this build, and registered for the
  final batch; the parent's 10 gaps and the 5 High baseline
  gaps are referenced, not re-registered.
