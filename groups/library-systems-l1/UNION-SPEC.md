# Union Spec — Library Systems, CMMC L1 (DeadRamp Phase 2, no-signal new sibling group)

The merged functional spec for the **Library Systems L1 group**:
**2 forks**, category **Library Systems** (a brand-new category),
CMMC tier **L1**. This group exists because of the no-signal
resolution: the remainder census held both forks unclassified
(their marketplace descriptions never state the library function in
a citable sentence, and both were flagged as probable library
systems), and the live-docs research pass then **confirmed both on
the vendors' own words** (`../../remainder/nosignal_report.json`,
`../../remainder/NOSIGNAL.md`). Membership is exactly:

| Fork | Vendor | Product | Impact | Status |
|---|---|---|---|---|
| F1305132147 | Ex Libris | Higher-Ed Platform (Alma, Primo, Leganto, Esploro) | LI-SaaS | FedRAMP Certified |
| FR1818459251 | Sirsi Corporation (SirsiDynix) | EOS.Web | Low | FedRAMP Certified |

Both map to CMMC **L1** per `../../crosswalk.md` (Low and LI-SaaS
both sit in the Low-baseline family). Tier fields are recorded as
the source states them. Both offerings are SaaS. Per-fork spec
sheets: [`specs/specs.json`](specs/specs.json), each carrying the
cached marketplace description, its claims, and the
`classification_evidence` + `classification_source_url` fields from
the research report.

**The category boundary, stated once.** Library Systems is the
library system of record: catalogue, holdings, and circulation
records for a library's collection. It is not Education & Training
(course delivery), not Learning Management (learner records), not
CMS (web content), and not Data Management (general data
platforms). The core below is built to exactly that boundary.

## The evidence split (read before the counts)

Two evidence streams exist for this group and they **never mix**:

- **Classification evidence** — the vendors' live words that founded
  the category. Ex Libris's Knowledge Center: "…the Alma library
  management solution constitute a platform for transforming the
  collection-focused library…" (full sentence on the sheet).
  SirsiDynix: "EOS.Web is an integrated library system designed
  specifically for special libraries…". These sentences classify;
  they are **never claim evidence**.
- **Claim evidence** — sentences from the forks' **cached
  marketplace descriptions only**. A function is claimed only where
  a description sentence fires a taxonomy family, and that sentence
  is stored on the sheet.

## How functions were counted (new category: the fresh-taxonomy method)

The taxonomy was derived fresh from **both** derivation sources —
(a) the cached descriptions and (b) the classification sentences —
with per-family sources recorded in the table below. Families exist
only for functions the forks' own words name; nothing was imported
from another category. Matching is by `scratch/extract.py` against
description sentences. **6 claims in total** (Ex Libris 2,
SirsiDynix 4) across a **10-family** taxonomy. Counts are a floor.

Posture exclusions (applied before matching, recorded here): both
descriptions carry posture prose — "security", "reliability",
"ease of integration" is a claim (see the family), but "security",
"reliability", "ease of use", "flexibility", "robust capabilities",
and SirsiDynix's FedRAMP Authorization / compliance-needs sentence
tag **nothing**: no family fires on posture adjectives, and no
control claim is drawn from marketplace prose at this tier (the L1
baseline below is the group's baseline, not a fork claim). Neither
short description contains a third-party catalogue or a
scope-exclusion sentence; `certified_services` was never read.
Raw hits equal final claims (6 raw, 0 removed, 0 added).

## The taxonomy (10 families, with derivation sources)

| # | Family | Derivation source |
|---|---|---|
| 1 | library_management — Library management / integrated library system | Classification (Alma sentence) + description (SirsiDynix "Integrated Library System (ILS) offerings") |
| 2 | discovery_delivery — Discovery and delivery | Classification only (Primo: "discovery and delivery system") |
| 3 | digital_preservation — Long-term preservation of digital assets | Classification only (Rosetta sentence) |
| 4 | course_resource_lists — Course resource lists | Classification only (Leganto: "managing course resource lists") |
| 5 | research_activities — Research activities support | Classification only (Esploro sentence) |
| 6 | knowledge_management — Knowledge management | Classification only (EOS.Web sentence) |
| 7 | platform_services — Open platform / common cross-product services | Description (Ex Libris) + classification ("constitute a platform") |
| 8 | integration — Integration with third-party products and services | Descriptions (both forks) |
| 9 | library_automation — Library automation | Description (SirsiDynix) |
| 10 | accessibility — Accessibility | Description (SirsiDynix) |

## Function ranking — the group (2 forks)

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Library management / integrated library system | 1 | **Core** — library registry, catalogue item records, holdings records, circulation (loan and hold) records |
| 2 | Integration | 2 | **Core slice** — integration registry records. The interface transports themselves: Extended |
| 3 | Open platform / common cross-product services | 1 | **Core slice** — the library registry substrate the records share. The vendor platform itself: Platform note |
| 4 | Library automation | 1 | **Core slice** — workflow definition registry, records only, never executes. The automation engine: Extended |
| 5 | Accessibility | 1 | Extended — accessible delivery/rendering is a delivery layer, not records (see Gaps) |
| 6 | Discovery and delivery | 0 | Extended — classification-derived, unclaimed in either description (see Gaps) |
| 7 | Long-term preservation of digital assets | 0 | Extended — classification-derived, unclaimed |
| 8 | Course resource lists | 0 | Extended — classification-derived, unclaimed |
| 9 | Research activities support | 0 | Extended — classification-derived, unclaimed |
| 10 | Knowledge management | 0 | Extended — classification-derived, unclaimed |

## Checked absences (verified against both descriptions; never guessed into the build)

- **No catalogue, holdings, circulation, loan, hold, patron, or
  borrowing vocabulary in either description.** The words never
  occur. The Core's catalogue/holdings/circulation records are the
  records machinery the single `library_management` claim (an
  integrated library system) presupposes — recorded here as the
  core-boundary decision, not smuggled in as claims.
- **No discovery, preservation, course-list, research, or
  knowledge-management vocabulary in either description.** Those
  five functions are named only by the classification sentences;
  they carry zero claims and stand as gaps, not functions.
- **No money vocabulary.** No fee, fine, payment, or charge token
  appears in either description; the build has **no money shape at
  all** — no field can hold an amount.
- **No scoring or ranking.** No score/rank token; reporting is
  counts only, test-enforced.
- **No patron identity.** Neither description names patron data;
  the build's patrons are opaque `patron_ref` strings and no field
  can hold a real name or contact detail (pinned by test).

**The core-boundary decision, stated once.** Claimed families 1–4
are built as records (with accessibility and the five
classification-only families Extended). Catalogue, holdings, and
circulation records are inside the boundary because an integrated
library system without them is a label, not a system; they are
grounded in the `library_management` claim and stated here, once.
Everything else the classification sentences name stays outside
until a description or a later batch grounds it.

**Derived-never-stored status:** a holding's `available_copies`
(quantity minus active loans), a loan's `overdue` (active, with the
read clock past its due date), and a hold's `queue_position` (its
place among the item's active holds) are computed by the read
views. Stored records carry none of those keys — pinned by tests.
Loan and hold lifecycles (`active` → `returned` /
`fulfilled` / `cancelled`) are guarded transitions, so those
statuses are stored.

**The signature invariant — the holding availability seam.** A
holding's active loans must never exceed its quantity:
`_check_holding_availability` in the store runs before every loan
is recorded; a violation raises `ValidationError`, consumes no id,
and changes nothing. This is the group's negative control (see
`tests/README.md`: mutation-verified, exactly 2 failures).

## The Core — what the merged build implements (10 functions)

Package `librarysys` under `src/`, Python standard library only,
ids sequential per type (`lib-`, `cat-`, `hld-`, `lon-`, `hol-`,
`int-`, `wfl-`); a failed operation consumes no id and changes
nothing; all timestamps UTC ISO-8601; validation precedes mutation.

1. **Library registry & membership** — libraries (`lib-`): opaque
   `library_ref`, a label, a member list. Membership is the
   boundary every library-scoped function enforces; only the
   creator or a platform admin may add members. (Substrate;
   grounds the platform_services claim.)
2. **Catalogue item records** — items (`cat-`) in a library:
   opaque `item_ref` (unique within the library), a title, an
   optional `format_label`. (library_management.)
3. **Holdings records** — holdings (`hld-`) against an item:
   opaque `holding_ref`, an opaque `branch_ref`, `quantity` (an
   int ≥ 1; booleans, floats, strings rejected). Read views derive
   `available_copies`. (library_management.)
4. **Loan records** — loans (`lon-`) against a holding: opaque
   `loan_ref`, an opaque `patron_ref`, a required `due_at`, a
   guarded lifecycle (`active` → `returned`). The availability
   seam runs before each is stored. Read views derive `overdue`.
   (library_management.)
5. **Hold records** — holds (`hol-`) against an item: opaque
   `hold_ref`, an opaque `patron_ref`, a guarded lifecycle
   (`active` → `fulfilled` / `cancelled`). Read views derive
   `queue_position`. (library_management.)
6. **Integration registry** — integrations (`int-`) in a library:
   opaque `integration_ref`, an opaque `system_ref`, a label.
   Records of interfaces, never transports. (integration.)
7. **Workflow registry** — workflows (`wfl-`) in a library: opaque
   `workflow_ref`, a label. Records only: the registry has no
   execute operation, pinned by test. (library_automation.)
8. **Registry reporting** — a library report computed on read:
   item, holding, copy, loan (active/overdue), hold, integration,
   and workflow counts. Counts only — no scores.
9. **Registry search** — literal case-insensitive substring search
   over registry metadata, scoped to libraries the actor belongs
   to (or all for a platform admin).
10. **Access control & audit** — platform roles `admin`, `member`,
    `viewer` with a permission matrix enforced on every operation,
    layered with library membership; and an append-only audit log
    recording every mutation and every denied attempt.

Access contract: actions `lib_read, lib_write, catalogue_write,
circulation_write, registry_write, report_read, audit_read`;
admin holds all seven; member holds all except `lib_write` and
`audit_read`; viewer holds {lib_read, report_read}. The store
records successful mutations to its audit log; the HTTP layer
records denials and `audit_read` only. Service:
`librarysys/service.py` — `make_server(host, port, store, audit,
users)`; auth via `X-User` / `X-Role` headers (the role must match
the registry; unknown user or mismatched role → 403, audited);
errors are JSON `{error}` with 400/403/404 as applicable; no stack
trace is ever returned. Endpoints: `GET /health` (no auth);
`GET /audit` (audit_read); `GET|POST /libraries`;
`GET /libraries/{id}`; `POST /libraries/{id}/members`;
`GET|POST /libraries/{id}/items`; `GET|POST
/libraries/{id}/holdings`; `GET|POST /libraries/{id}/loans`;
`POST /libraries/{id}/loans/{lid}/return`; `GET|POST
/libraries/{id}/holds`; `POST /libraries/{id}/holds/{hid}/fulfill`
· `/cancel`; `GET|POST /libraries/{id}/integrations`; `GET|POST
/libraries/{id}/workflows`; `GET /libraries/{id}/report`;
`GET /search?q=`. CLI: `python -m librarysys serve --host --port
[--audit-log PATH] [--certfile --keyfile]`, demo users
`alice=admin, bob=member, carol=viewer`, default port 8821.

## Control baseline (traceability)

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low / LI-SaaS** (per
  `../../crosswalk.md`). Both forks sit in the Low-baseline
  family, so the union baseline is the Low baseline, un-diluted
  (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low / LI-SaaS tailoring), cross-walked to the 17
  practices of FAR 52.204-21 that define CMMC L1.
- **Documented control claims:** none are drawn from the forks'
  descriptions at this tier — both descriptions' security and
  compliance sentences are posture prose (see the exclusions
  above), and no baseline family is asserted on a fork's behalf.
  The mapping below is the **build's** baseline traceability, not
  a fork claim.
- **Feature → control family mapping (this build):**
  - Access control (platform roles + library membership) → **AC**
    (AC-2, AC-3, AC-6), **IA** (IA-2 — identity is supplied by the
    embedding organization via user/role headers; the build ships
    hooks, not an identity provider).
  - Audit log → **AU** (AU-2, AU-3, AU-6 — append-only store,
    audit-read restricted to the `audit_read` permission, held by
    admin only).
  - Registries, lifecycle guards, the availability seam, integer
    quantity discipline → **SI** (SI-10 information input
    validation — malformed input is rejected whole, never
    partially applied) and **SC** (SC-8 — the server runs over TLS
    when a certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here.
    Neither fork's description claims FIPS-validated modules, and
    this build claims none).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- **Discovery & delivery service** — the discovery layer the
  classification sentence names for Primo (search, discovery, and
  delivery of library resources). Classification-derived, zero
  claims in either description; the core holds catalogue records
  and registry search only.
- **Digital preservation system** — long-term preservation of
  digital assets (the Rosetta function named in the classification
  sentence). Classification-derived, zero claims.
- **Course resource list management** — managing course resource
  lists (the Leganto function named in the classification
  sentence). Classification-derived, zero claims.
- **Research activities platform** — maximizing visibility,
  efficiency, and compliance of research activities (the Esploro
  function named in the classification sentence).
  Classification-derived, zero claims.
- **Knowledge management system** — the knowledge-management
  function the EOS.Web classification sentence names for special
  libraries. Classification-derived, zero claims.
- **Accessible delivery & rendering** — the accessible formats and
  delivery experience behind the accessibility claim. The core
  records a catalogue item's format label; it renders and delivers
  nothing.
- **Automation engine** — executing the library automation the
  workflow registry defines. The core registers workflow
  definitions; it executes nothing.
- **Integration transport** — the third-party interfaces
  themselves (the products and tools both descriptions name
  integration with). The core registers interface records; it
  connects to nothing.
- **Identity provider** — patron and staff identity proofing;
  IA-2 stays with the embedding organization and this build ships
  hooks, not an IdP.

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (6 claims total across a 10-family
  taxonomy derived from the forks' own words in both derivation
  sources, each claim with its description sentence as evidence;
  classification fields pinned separately against the no-signal
  report).
- Core: 10 core functions implemented, each with tracing tests.
- Extended: 9 gaps specified above, **not** implemented in this
  build.
- Platform notes: SaaS delivery (both forks' recorded service
  model) is a platform note, not a built function.
