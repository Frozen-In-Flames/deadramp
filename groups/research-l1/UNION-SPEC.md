# Union Spec — Research, CMMC L1 (DeadRamp Phase 2 remainder, Research L1 singleton)

The singleton spec for the Research category at the L1 tier:
**1 fork**, FedRAMP **LI-SaaS** — **Laser AI** (Evidence Prime),
FedRAMP Certified, SaaS, Public Cloud. Built under the remainder
census unit `new-singleton:Research|L1`.

**Membership provenance, stated plainly:** `forks.json` files
this fork "Uncategorized (none in source)" at tier L1 — its
source record carries an empty `business_categories` list. The
DeadRamp category is the **remainder census proposal**, taken
from the fork's own description (its first sentence; census
classifier note: "AI/NLP is the technique; the function performed
is systematic-review research synthesis."). Reconciliation:
`remainder.json` unit == `specs/specs.json` == {FR2207359708},
zero diff, and the fork's own recorded fields (LI-SaaS, FedRAMP
Certified, L1) match the source record exactly. MAP.md's
category arithmetic is unaffected: this fork was never in
MAP.md's Research count, because MAP.md counts the Phase 1
category field.

## Lineage: a cross-tier carry, downward (the Merge Rule applied across tiers)

This build does not start from zero. Its parents are:

1. The **Group 53 singleton build** (`../research-l2/`) — the
   Research L2 (FedRAMP Moderate) build: a clean-room
   research-data records service (11 core functions), whose
   taxonomy and substrate this category uses at every tier. (The
   group was later enlarged at L2 by a remainder addition; this
   singleton's lineage is the original Group 53 build — its
   taxonomy, its shipped claim table, and its substrate.)
2. This singleton's **1 LI-SaaS fork**, via the spec sheet in
   `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents (Rule 1) — the category
substrate is carried whole, not stripped because one fork's
marketing prose is thin (a wording floor is not a downgrade, the
same reasoning the CRM tiers recorded). The tier, however, is
this fork's own: **LI-SaaS / L1**, the lightest tier, and the
baseline below is written **fresh for Low** (Rule 2 satisfied at
the merged tier, which here is L1). Rule 3 traceability is this
document plus the spec sheet; Rule 4's SSDF-shaped process is
the provenance here, the review recorded in
`scratch/ARTIFACTS.md`, and the verification record in
`tests/README.md` (full suite run by the builder; the signature
negative control mutation-verified live in this tree).

**What does NOT carry down, stated once:** Group 53's Moderate /
NIST SP 800-171 baseline citations stay in Group 53. The
implementation needs almost no downward modification: 6 of 7
`src/` modules are byte-identical to Group 53's, and the seventh
(`__init__.py`) differs only in its package docstring, which
named the Moderate/L2 baseline and was re-anchored to this
group's tier (hash record in `scratch/reuse-note.md`). The L2
build carries no Moderate-specific machinery in code — its
baseline lives in its spec documents, not in the implementation.

## How functions were counted

The Research category's 9-family taxonomy was applied
**verbatim** — parsed via `ast` out of Group 53's original
shipped `scratch/extract.py` (never executed, never re-typed),
so counts are comparable across the category's tiers and nothing
was re-tuned to fit this one fork. Before the newcomer was
tagged, the extractor reproduced Group 53's original shipped
claim table exactly from the raw cache (Gen3, 9 claims, evidence
included; the sheet verified deep-equal to the original ship
commit `4c868c3`). A family is claimed only when the fork's own
description contains matching text; the first matching sentence
is stored in `specs/specs.json` as evidence. Source: GSA FedRAMP
Marketplace dataset, cached at `raw/data_dump.json` (produced by
the General Services Administration, last change 2026-10-22).

**Result: 0 claims.** Zero raw hits across all 9 families and
all 6 sentences of the description (per-sentence hit map in
`scratch/sentence_map.json`, all-empty). Nothing was removed
before matching — the source record's `certified_services` is
empty (asserted), and no sentence is a scope-exclusion sentence,
so matched text is the full text and raw hits equal claims
(0 = 0).

The taxonomy is data-commons-shaped because Group 53 defined it
from the Gen3 description's own functional vocabulary. Laser
AI's description is systematic-review automation prose: it
asserts review automation, screening, extraction, and quality
assessment in its own words and fires none of the nine families.
The near-misses are itemized in `scratch/ARTIFACTS.md` (the noun
"management" is not the verb "managing"; "shared" is not
"sharing"; "meta-analysis" is not "analyzing"); the patterns
were not loosened. The zero is the finding, stated plainly — the
category has seen the same shape before: 3 of the 5 forks in
Group 53's own remainder addition claimed zero under the
verbatim taxonomy.

**Census citation accounting:** the census recorded one citation
for this fork — sentence 1 — which verifies as a strict verbatim
substring of the description and tags **no** family. Verification
is not a claim, in either direction; both facts are pinned in
`tests/test_singleton_spec.py` and `scratch/citation_check.json`.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Data commons development, configuration & operation | **Core** (substrate) — carried from the Group 53 union (claimed 1 of 1 there); the commons runtime engine is Extended |
| 1 | 0 | Data ecosystems / data meshes | **Core** (substrate) — carried (claimed there); federation engines Extended |
| 1 | 0 | Workspaces | **Core** (substrate) — carried (claimed there) |
| 1 | 0 | Data management (managing data) | **Core** (substrate) — carried (claimed there at records strength); ingestion/harmonization engines Extended |
| 1 | 0 | Data analysis (analyzing data) | Extended — carried as the Group 53 union's Extended family (claimed there, no method named); the workspace registry (Core) is its records form |
| 1 | 0 | Data sharing | **Core slice** (substrate) — carried (claimed there): requests, decisions, time-boxed grants as records; the delivery engine is Extended |
| 1 | 0 | Open access & controlled access data | **Core** (substrate) — carried (claimed there): the tier designation on every dataset record, gating by request/decision/grant records |
| 1 | 0 | Open-source platform (platform note) | Platform note — 0 claims here (no "open-source" text in this fork's description); this build is likewise Apache-2.0 open source |
| 1 | 0 | Multi-tenant SaaS delivery (platform note) | Platform note — 0 claims here (the multi-tenant SaaS phrase is absent; SaaS/Public Cloud are record fields, not text); the build is a single-tenant reference deployment |

Plus this singleton's own engines, named from its description's
own words (all Extended, detailed in Gaps below): the living
systematic review automation engine itself (NLP/AI synthesis);
literature search-strategy construction & execution; screening
(title/abstract and full-text); data extraction from full texts;
review quality assessment & verification; review protocol
creation; meta-analysis export; shared dictionaries; review
project/team/role administration; customizable workflow
processes; and the human-in-the-loop AI suggestion interface.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35/38/40 and CRM L1 precedent).** This fork claims
**no** family, so **no core function below is claim-supported
for this fork**, yet all 11 core functions stand in this build.
The reasoning is the Merge Rule itself: the category substrate
is the union this fork's category presupposes, carried whole at
the fork's own tier. The presupposition is read at the level of
the research operation and stated here as *interpretation, not
evidence*: a system that synthesizes research knowledge for
larger organizations, manages projects/teams/roles, and gates
regulator and sponsor verification of review quality presupposes
governed records of what evidence exists (→ dataset registry,
metadata + checksum only), who may see controlled material and
for how long (→ access requests, decisions, time-boxed grants),
the working surfaces where the synthesis is organized (→ commons
and workspace registries), and review over all of it (→ search,
summary, RBAC, audit). Each step is a substrate function from
Group 53's core; none of them is this product's engine — LASER's
engine is the NLP/AI synthesis pipeline, which is Extended and
not built here. The alternative — building nothing at L1, or
building only an "AI" stub — was considered and rejected: the
category's L1 tier would carry no substrate while its L2 tier
carries it, and a stub around no claim at all would invert the
core/extended boundary entirely. The price of carrying the
substrate is this disclosure and the coverage statement's
wording: **core carried, not claimed, for this fork.** That
price is paid in full, in both places.

**Named absences (rechecked against this fork token-by-token).**
All 9 taxonomy families stand at 0 claims for this fork (above).
The category's standing absences also survive recheck: the
description names **no dataset content of any kind** — no file
formats, no record types, no cohorts, no subject data (LASER
names review *steps*, never dataset contents) — and **no**
ingestion, harmonization, indexing, query, or cohort-building
function by name. There is likewise **no scoring or ranking
vocabulary**: "quality assessment" is assessment *of reviews*,
nothing is scored in this build, and no record shape carries a
field for a score. Two further token-verified absences for a
systematic-review tool: no named literature database (0 tokens
for PubMed/Embase/Cochrane) and no methodology-standard token
(0 for PRISMA) — the description speaks of systematic reviews
generically. These are recorded so the absence is provable from
the record; unclaimed families are not gaps by themselves (the
Group 21 precedent) — but the functions this fork *does* assert
in substance are named as gaps below.

## The Core — what the build implements (11 functions, carried at the L1 baseline)

The same 11 functions as Group 53, carried whole:

1. **Data commons registry & membership** — commons records
   (`com-`): name, title, kind (`commons` / `ecosystem` /
   `mesh`), an opaque sponsor reference, an owner and a member
   list. Membership is the boundary every other commons-scoped
   function enforces. The lifecycle is event-driven:
   `draft → active → retired`, changed only through recorded
   lifecycle actions. Carried, not claimed.
2. **Organization registry (opaque references)** — organizations
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier. Carried, not claimed.
3. **Workspace registry** — workspaces (`ws-`) inside a commons:
   name and a stated purpose. Carried, not claimed.
4. **Dataset registry (metadata + checksums only)** — datasets
   (`ds-`) inside a commons: name, description, an access tier
   (`open` / `controlled`), a SHA-256 checksum, and a byte size.
   Content is never stored. A dataset can be verified against
   caller-supplied content (hashed transiently, compared,
   discarded) in the legal-records pattern. Carried, not
   claimed.
5. **Access request records** — requests (`ar-`) for controlled
   datasets: the requester, a stated purpose, and a requested
   duration in days. Requests against open datasets are
   rejected — open data needs no request, and a request record
   for one would be a false gate. The lifecycle is event-driven:
   `pending → approved / denied`, plus `withdrawn` while
   pending. Carried, not claimed.
6. **Decision records** — a decision (`dec-`) on a pending
   request records the decider's outcome and note. One seam is
   enforced in the store: the decider is never the requester
   (separation of duties — see the baseline precision notes for
   how this is traced at Low). Carried, not claimed.
7. **Access grant records** — an approval mints a grant (`gr-`):
   the dataset, the grantee, a start, and an expiry computed
   from the requested duration. A grant's status (`scheduled` /
   `active` / `expired` / `revoked`) is **derived at read** from
   the start, expiry, and revocation timestamp against the read
   clock — **never stored**; the stored record carries no
   `status` key. Revocation is a recorded event. Grants are
   records: they confer nothing by themselves; actual data
   delivery is Extended. Carried, not claimed.
8. **Search & summary reporting** — literal case-insensitive
   substring search over accessible commons, organizations, and
   datasets in accessible commons; and a per-commons summary
   computed on read from records only: workspace count, dataset
   counts by tier, request counts by status, grant counts by
   derived status. Counts — never scores. Carried, not claimed.
9. **API access** — every function above is exposed over a REST
   API (JSON). Carried substrate mechanics.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix
    enforced on every operation, layered with commons membership
    (non-members cannot read or write a commons' content; the
    platform `admin` role can). Carried, not claimed.
11. **Audit log** — an append-only audit trail: every commons,
    membership, organization, workspace, dataset, request,
    decision, grant, and revocation mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp. Carried, not claimed.

**Privacy discipline (hard rule, inherited).** A research-data
platform's records substrate holds **metadata and opaque
references only** — never research subject data, never genomic
or clinical payloads, never dataset contents, and — pointedly
for this fork — never review contents, protocol text, screening
results, or extracted study data either: those are the fork's
engine outputs, and no entity shape here has a field for them.
Dataset records are metadata + a SHA-256 checksum (content is
hashed transiently for verification and never stored), and every
entity shape is pinned by test so no field exists that could
hold a payload.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this
  fork's impact level) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline.
  LI-SaaS is FedRAMP's tailored **subset** of that baseline for
  SaaS offerings, so the union baseline is the Low baseline
  itself, cross-walked to the FAR 52.204-21 basic-safeguarding
  practices that define CMMC L1. One fork at one tier plus the
  carried substrate, so no merge changes the tier (Merge Rules
  1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Commons & membership registry | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit; membership is enforced in the store on every commons-scoped operation; uniqueness and kind validation on write; identity itself is supplied by the embedding organization |
| Organization registry | AC-3, SI-10 | Opaque references only, pinned shape, duplicate refs rejected |
| Workspaces | CM-6, SI-10 | Workspace records validated on write inside a membership boundary |
| Datasets (metadata + checksum) | AU-2, AU-3 (Low side), SI-10 | Every registration is an auditable event; content is verified transiently and never stored |
| Access requests | AC-3, SI-10 | The controlled-only gate and duration validation are enforced in the store; malformed input is rejected whole |
| Decisions | AC-3 (AC-5 lineage — see precision notes) | The decider is never the requester, enforced in the store as the single seam `_check_decider_not_requester` |
| Grants (derived status) | CM-6, AU-2/AU-3 (Low side) | Grant status is derived at read from stored timestamps against the read clock, never stored — reproducible from the records and the trail |
| Search & summary | AC-3 | Literal search and counts over accessible records only, permission-gated |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Three-role matrix enforced pre-mutation in the store and again at the service layer |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing
  is silently imported from the sibling tier's table):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and
    its LI-SaaS tailoring) carries the AU family — Group 53's
    AU-6 (audit review) and AU-9 (protection of audit
    information) citations are Moderate selections and are
    **not** claimed here; AU-2/AU-3 only.
  - **Separation of duties:** the decider-never-requester seam
    is a design property of the carried substrate. Its
    Moderate-table family home in Group 53's spec was AC-5,
    which is **not** a Low-baseline selection, so at this tier
    the seam is traced to AC-3 access enforcement, with AC-5
    named as lineage only.
  - **Transmission:** SC-8 (TLS when a certificate is
    configured) is stated as a deployment property in Group
    53's spec and is restated the same way here — encryption at
    rest is a deployment-layer control, stated plainly, not
    claimed.
- **Caveat (standing, from crosswalk.md):** this traceability
  is a planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence,
  and any real compliance claim still has to be earned inside
  each regime separately.

## Implementation contract (summary)

Identical to Group 53's — `src/research/` (Python stdlib only):
`errors` (`ResearchError`, `ValidationError`, `NotFoundError`,
`PermissionDenied`), `access` (User, admin/member/viewer
matrix), `audit` (append-only AuditLog), `store` (ResearchStore:
the 11 core functions; failed operations consume no ids;
permission checks precede mutation; the grant derivation lives
in the single method `_derive_grant_status`; the separation seam
is `_check_decider_not_requester`), `service` (HTTP layer, demo
registry alice=admin / bob=member / carol=viewer, port **8798**),
`__main__` (`python -m research serve`). 6 of 7 modules
byte-identical to Group 53's; `__init__.py` differs in its
docstring only (hash record in `scratch/reuse-note.md`).
`tests/`: see tests/README.md for the test count and the
negative-control record (the count is filled in from the build,
not stated here).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Laser AI, LI-SaaS, its actual impact
  level recorded in the spec sheet; category by remainder-census
  proposal, provenance recorded).
- Claims evidenced for the fork: **0** of 9 families — the
  zero-claim finding, with 0 raw hits; no core function is
  claim-supported for this fork.
- Core implemented: **11 / 11** functions above — **carried as
  the category substrate under the core-boundary decision, not
  claimed as this fork's evidenced functions.** The distinction
  is the coverage statement, not a footnote to it.
- Tests: **96 run, 96 passed**, including the mutation-verified
  negative control performed against this group's tree
  (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its
description's own words — the product's actual surface, none of
it built here):

- Living systematic review automation engine: the NLP/AI
  pipeline that synthesizes available knowledge about a health
  problem continuously, keeps reviews "living", and offloads
  repetitive review tasks to the AI-enabled system (the
  description's headline assertion and the census's classifier
  note; no taxonomy family covers review synthesis as such).
- Literature search-strategy construction & execution engine:
  building and running the search strategy a review protocol
  specifies, across literature sources (the build's registry
  search is substrate mechanics over its own records, not this).
- Screening engine: title/abstract (T&A) screening and full-text
  screening of candidate studies against a protocol.
- Data extraction engine: extracting study data from full texts
  into review datasets.
- Review quality assessment & verification engine: quality
  assessment of reviews, and the quick verification surface for
  regulators and sponsors.
- Review protocol creation tooling: authoring the protocol a
  review follows.
- Meta-analysis export engine: export of extracted data to
  external meta-analysis tools.
- Shared dictionaries & terminology management: the shared
  dictionaries the description names (asserted in substance —
  "shared" is not the data-sharing family's phrase; see
  ARTIFACTS.md).
- Review project, team & role administration: enterprise-grade
  management of the projects, teams, and roles a review program
  runs under (asserted in substance; the noun "management" is
  not the data-management family's verb).
- Customizable workflow engine for review processes: the
  customizable workflow processes the description names —
  an execution engine, not a records form.
- Human-in-the-loop AI suggestion interface: the human-centric
  interface for interacting with AI suggestions (a surface over
  the automation engine, named separately because the
  description names it separately).

Extended families carried from the Group 53 union, not
implemented (registered once under Group 53; not re-registered
here): data commons runtime engine; data ingestion / ETL engine;
data harmonization engine; indexing & metadata catalog engines
beyond the registry; query & analysis workspace engines; cohort
builder / cohort discovery engine; cross-commons federation /
data mesh networking; data delivery / transfer engine for
sharing; access enforcement on data delivery; identity provider
/ identity management service (IA-2 stays with the embedding
organization).

Platform layer (gap-listed, never implied closed): multi-tenancy
(the build is a single-tenant reference deployment); encryption
at rest (deployment layer); TLS only when a certificate is
configured; demo identities are hooks, not an IdP. The
hosting/delivery platform is the deployment layer itself, not a
function of this build.

**Privacy note:** this build stores records and opaque
caller-supplied references only — no research subject data, no
dataset contents, and no review contents, protocol text,
screening results, or extracted study data exist in any entity
shape; dataset content is hashed transiently for verification
and discarded, and nothing is scored anywhere.
