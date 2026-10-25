# Union Spec — Content Management System (CMS), CMMC L1 (DeadRamp Phase 2, Group 24)

The merged functional spec for the Content Management System (CMS)
sibling group at the L1 tier: **2 forks, mixed FedRAMP impact
levels** — **WorldShare Management Services** (OCLC Incorporated)
is **LI-SaaS** and **TimeLooper Inc.** (TimeLooper Xplore) is
**Low** — reconciled zero-diff three ways (`specs/specs.json` ↔
`forks.json` ↔ MAP.md "Content Management System (CMS) — L1 (2)").
Each fork's actual impact level is recorded in its spec sheet.

This is the map's lightest tier. Both impact levels map to L1 on
the crosswalk (`../../crosswalk.md`): LI-SaaS is FedRAMP's own
tailored **subset** of the Low baseline for SaaS offerings, so the
union of the group's parent baselines is the Low baseline itself,
and the highest tier any parent carries is the Low family. The
group baseline is therefore the **NIST SP 800-53 Rev. 5 Low
baseline** ⇔ **CMMC L1** (the FAR 52.204-21 practice set), taken in
full (Merge Rules 1 and 2). Both members are FedRAMP Certified in
`forks.json` — verified.

The group: a cloud-based **library services platform** (OCLC WMS,
built on WorldCat, the global union catalog of library collections)
and a multi-tenant **content management platform** for publishing
digital content to mobile applications (TimeLooper Xplore). There
is no single product they both are. What they share, underneath
their verticals, is the CMS substrate Group 20's union established
for this category: content held in a registry and authored by
creators, organized into sites, described by metadata and tags,
supported by media and document assets, found through search, and
published to its audience — all under permissioned, protected
access with reporting over the registry. The merged build
implements that substrate; each vendor's engine and vertical on
top of it (library ILS modules, mobile app delivery, discovery and
reporting engines) is an Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP
Marketplace dataset, cached at `../../raw/data_dump.json`;
produced by the General Services Administration, last change
2026-10-22) was sentence-split and matched against **Group 20's
13-family taxonomy, applied verbatim** — same function ids, labels,
and matchers, verified byte-identical in `scratch/extract.py` — so
counts are comparable across the CMS tiers. A family is claimed
only when the offering's own description contains matching text;
the first matching sentence is stored in `specs/specs.json` as
evidence, so every claim is auditable. **1 claim survived.** The
near-misses and wording artifacts are documented in
`scratch/ARTIFACTS.md`: TimeLooper's "content management
**platform**" (the taxonomy keys on "system"), its "administrative
interfaces" and bare "delivery" (the families key on "tools" and
"delivery system"), and its AWS GovCloud hosting substrate (Group
20's Tyler correction: a hosting substrate tags nothing);
OCLC's "discovery service" (the family keys on "search"), its
"custom reports" / "Report Designer" (the family keys on
"reporting"), its "efficient workflows" (the family keys on
"BPM"), and its library-vertical modules tagging no CMS family
(Group 20's Bibliovation precedent). **The taxonomy was not
re-tuned for this group** — that would corrupt cross-tier
comparability. Per-fork claim counts: WorldShare Management
Services 1, TimeLooper Inc. 0. All counts are a floor: both
descriptions are boundary and marketing prose, and the floor is
reported, not padded.

## Function ranking — all 2 siblings (Group 20 taxonomy, verbatim)

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Metadata & taxonomy/tagging | **Core** (7) — OCLC's tagged claim |
| 2 | 0 | Content management & content registry | **Core** — content registry, under the core-boundary decision below |
| 2 | 0 | Content authoring & editing | **Core** (3), core-boundary |
| 2 | 0 | Site & section structure | **Core** (1), core-boundary |
| 2 | 0 | Content delivery & publishing | **Core** — publishing/delivery records, core-boundary; rendering, templating & CDN Extended; mobile delivery Extended |
| 2 | 0 | Search & discovery | **Core** — metadata search, core-boundary; indexing & discovery engines Extended |
| 2 | 0 | Ingestion & repository consolidation | **Core** — registration records, core-boundary; bulk ingestion & index-in-place engines Extended |
| 2 | 0 | Media & document assets | **Core** (6), core-boundary |
| 2 | 0 | Records & case information management | **Core** — records substrate, core-boundary |
| 2 | 0 | Reporting & analytics | **Core** — computed views, core-boundary; reporting/analytics engines Extended |
| 2 | 0 | Administration, security & protected access | **Core** — RBAC/admin substrate under (11)/(12), core-boundary |
| 2 | 0 | Workflow / BPM automation | Extended — BPM engine (carried from the Group 20 union at 0 claims here); lifecycle mechanics **Core** under (4) |
| 2 | 0 | Cloud platform hosting (PaaS/IaaS) | Extended — hosting itself (both forks' hosting is substrate prose; see ARTIFACTS.md) |

**Core-boundary decision (recorded, per the Group 10 precedent):**
eleven of the twelve Core functions tag zero claims in this group.
They stay Core because they define the Content Management System
category itself and both products plainly presuppose them —
TimeLooper in its own words is a platform "that enables
institutions to manage, store, and publish digital content"
(registry, authoring, publishing), and OCLC's WMS is a management
platform whose modules are collection, record, and metadata
management over a shared catalog (registry, assets, metadata). The
one tagged family (metadata & taxonomy) is also the substrate's
center of gravity for OCLC. A wording artifact is not a downgrade,
and the claim floor is stated, not padded.

Named absences, carried from Group 20 and unchanged at this tier:
**no sibling's description claims editorial review/approval
workflow, content versioning/revision history, publish scheduling,
WYSIWYG/visual editing, templating/rendering, or
personalization.** The build's lifecycle states, revisions, and
publish windows are therefore registry mechanics of the claimed
content-registry/publishing substrate (the Group 10 core-boundary
precedent), recorded as such — never presented as claimed
families.

## The Core — what the merged build implements (12 functions)

1. **Site & section structure registry** — sites (`site-`) and
   sections (`sec-`) as structure records.
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
   metadata key/values — this group's one tagged claim family
   (OCLC: "metadata and electronic resource management";
   cataloging/metadata services).
8. **Metadata search & discovery** — literal case-insensitive
   substring search over items, assets, sites, tags; indexing and
   discovery engines Extended.
9. **Registry reporting** — computed views over the registry (items
   by status/site/type, publish activity, asset counts);
   reporting engines Extended.
10. **REST API** — full surface over HTTP, house auth convention
    (X-User/X-Role against demo registry; 401 unknown/mismatched,
    403 permission, denied attempts audited).
11. **RBAC** — admin/publisher/editor/author/viewer matrix,
    enforced in the store before any state change or id allocation
    and again at the service layer.
12. **Audit log** — append-only, JSONL-persistable, records every
    mutation and every denied attempt (`<action>:denied`).

**Reuse, stated explicitly (per the build order for this group):**
the implementation in `src/` and the suite in `tests/` are the
shipped Group 20 (CMS L2) code, reused in full — this project's own
Apache-2.0 code, and a per-file hash comparison (recorded in
`scratch/reuse-note.md`) shows all 7 `src/` files and 16 of 18
`tests/` files byte-identical to Group 20's; the two differing
files are documentation wording only (`tests/cms_helpers.py`
docstring, `tests/README.md`). A grep of the reused `src/` confirms
it contains no tier/baseline strings: the code is functionally
tier-neutral. **What is NOT reused is the baseline claim.** Group
20's Moderate / 800-171 framing does not carry over: this group's
spec, traceability, and README are written against the Low
baseline and FAR 52.204-21 only, and no control is claimed here on
the strength of Group 20's spec.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS**
  (per `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored subset of it),
  cross-walked to the FAR 52.204-21 practices that define CMMC L1.
  Derivation per the Merge Rule: union of parent baselines = Low
  (the LI-SaaS subset adds nothing beyond it), inherited in full.
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Site/section + type registries | CM-6, SI-10 | Sites, sections, and content types are explicit, validated configuration records; nothing is structured that is not registered |
| Content registry & revisions | CM-6, AU-2, SI-10 | Content items and every revision of them are retained registry records, recorded on the FedRAMP Low side (see the AU precision note) |
| Editorial lifecycle | AC-3, AC-5, AC-6 | Role-gated transitions with separation of duties — the approver is never the item's author — and least-privilege enforcement (AC-5 is a Low-baseline selection; Group 20's Moderate framing is not imported) |
| Publishing records & derived windows | AU-2, SI-10 | Publishing is a recorded event with complete record content; window state is derived from stored facts, never stored separately |
| Asset registry & checksums | SI (family), AU-2 | Asset integrity is recorded via SHA-256 checksums — an implementation integrity property of the SI family; the specific Moderate selection SI-7 cited at L2 is **not** a Low-baseline selection and is not claimed here |
| Taxonomy/metadata | CM-6, SI-10 | Tags and metadata are explicit, validated registry configuration — the group's tagged claim family |
| Metadata search | AC-3, AU-2 | Review over registered metadata only, permission-gated, and itself recorded |
| Reporting views | AU-2 | Computed views are review over recorded registry facts |
| REST API | AC-3, SC-8 (partial) | Permission-gated access to the full surface; transmission protection is TLS when configured (see gaps) |
| RBAC | AC-2, AC-3, AC-5, AC-6, IA-2/IA-5 (hooks) | Five-role matrix enforced pre-mutation at two layers; identity and authenticator management stay with the embedding organization (FAR practices: limit access to authorized users and authorized transactions/functions; identify and authenticate users, processes, and devices) |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API |

- **Precision note (audit):** CMMC L1 / FAR 52.204-21 contains **no
  audit practice** for system audit records, so no audit claim is
  made on the CMMC side, and none of Group 20's Moderate-level
  audit citations (AU-6, AU-9) are imported here. The audit log is
  carried because the FedRAMP Low baseline carries the AU family
  (AU-2/AU-3) — not because L1 asks for it.
- **What this tier does not carry, and this build does not
  claim:** the Moderate/High apparatus from the sibling groups is
  out of scope for a Low/L1 merge and is not inherited downward.
  Encryption at rest is a deployment-layer control, stated
  plainly, not claimed here. Neither sibling claims an encryption
  function; TLS support is a property of the reused service,
  recorded as such, not as a claim.
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching equivalence only. FedRAMP authorizes products;
  CMMC certifies organizations. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families.

## Implementation contract (summary)

`src/cms/` (package `cms`, Python stdlib only): `errors`, `access`,
`audit`, `store`, `service`, `__main__`. Identical to Group 20's
contract — the store enforces the RBAC matrix before any state
change or id allocation, so failed operations consume no ids, and
the separation-of-duties guard for the editorial lifecycle lives
in the single method `_check_approver_not_author`. Entry point:
`python -m cms serve`, port 8793. Demo users: alice=admin,
bob=publisher, carol=editor, dave=author, erin=viewer.

## Coverage statement (for this build)

- Forks spec'd: **2 / 2** (LI-SaaS 1, Low 1; each fork's actual
  impact level recorded in its spec sheet), with evidenced claims
  (1 total — the floor is the story of this group, and it is
  reported, not padded).
- Core implemented: **12 / 12** functions above.
- Tests: see tests/README.md (98 tests, including the
  mutation-verified negative control reproduced on this tree).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- **Library ILS vertical (OCLC WMS)** — the dominant vertical of
  this group: circulation, acquisitions, resource sharing / ILL
  (WorldShare ILL, Tipasa), Collection Manager, Knowledgebase,
  EZproxy access proxying, CONTENTdm digital collection
  management, and the WorldCat union-catalog data network beneath
  them.
- **Mobile application delivery (TimeLooper)** — publishing
  digital content to mobile applications and the companion mobile
  application itself (outside the offering's own authorization
  boundary, per its description).
- Rendering & templating engines and visual/WYSIWYG editors
  (carried from the Group 20 union; 0 claims here).
- CDN / delivery network and runtime site serving (carried;
  TimeLooper's "content delivery functionality" is a taxonomy
  near-miss, recorded in ARTIFACTS.md).
- Enterprise search indexing & discovery engines (carried; OCLC's
  discovery service is a near-miss under the verbatim taxonomy).
- Analytics & reporting engines beyond registry reporting
  (carried; OCLC's "analytics, including custom reports and
  visualizations" / Report Designer are near-misses).
- Bulk ingestion & index-in-place engines (carried from the
  Group 20 union).
- BPM / case-management engine; participant engagement vertical;
  personalization / experience optimization (carried from the
  Group 20 union; 0 claims in this group, named so the union at
  this category is complete).
- Platform hosting itself (both forks' hosting is substrate
  prose; Group 20's substrate correction applies).

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when configured; multi-tenancy
(TimeLooper claims multi-tenant in prose; the build is a
single-tenant reference deployment); demo identities are hooks,
not an IdP (IA-2 stays with the embedding organization).
