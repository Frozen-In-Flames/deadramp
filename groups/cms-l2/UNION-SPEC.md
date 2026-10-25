# Union Spec — Content Management System (CMS), CMMC L2 (DeadRamp Phase 2, Group 20)

The merged functional spec for the Content Management System (CMS)
sibling group at the L2 tier: **4 forks, all FedRAMP Moderate**,
reconciled zero-diff three ways (`specs/specs.json` ↔ `forks.json` ↔
MAP.md "Content Management System (CMS) — L2 (4)").

The group: Acquia Cloud (Acquia Inc.) · Bibliovation/Knowvation
(PTFS/Liblime) · Tyler Federal Cloud Platform (TFCP) (Tyler Federal,
LLC) · Digital Health Research Platform (Vibrent Health).

This is a heterogeneous group. The source's "Content Management
System (CMS)" category collects a Drupal-based cloud platform for
building and delivering government websites, a library system paired
with an enterprise digital content management, discovery and delivery
system, a BPM / case-management platform, and a digital health
research platform whose public face is a CMS website. There is no
single product they all are. What the claim counts below prove they
share is a **content substrate**: content held in a registry and
authored by creators, organized into sites, described by metadata
and tags, supported by media and document assets, found through
search, and delivered or published to its audience — all under
permissioned, protected access with reporting over the registry.
The merged build implements that substrate; each vendor's engine on
top of it (site rendering and hosting, enterprise search indexing,
library systems, BPM casework, participant engagement) is an
Extended function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against a 13-family taxonomy defined from this category's
descriptions. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is
stored in `specs/specs.json` as evidence, so every claim is
auditable. **19 claims survived.** The wording-artifact corrections
applied while calibrating the taxonomy are documented in
`scratch/ARTIFACTS.md`: Tyler TFCP's AWS GovCloud implementation
substrate (and generic "SaaS Platform" delivery-model mentions for
Tyler and Vibrent) tagging no hosting function, Vibrent's
health-research engagement application and Bibliovation's
library-vertical modules tagging no CMS family (while Bibliovation's
MARC21 cataloging editor does tag authoring and its metadata
practices do tag taxonomy), Acquia's Drupal "content management
system" phrase considered and kept, Acquia's Gartner and agency
name-drop marketing prose tagging nothing, and Tyler's generic
"collect, track, manage, process" verbs scoping records management
to "case/record management" and reporting to "report on
information". **No fork has zero claims.** Per-fork claim counts:
Bibliovation/Knowvation 9, Acquia Cloud 4, Tyler Federal Cloud
Platform (TFCP) 3, Digital Health Research Platform 3. All counts
are a floor: several descriptions are boundary or marketing prose,
and the floor is reported, not padded.

## Function ranking — all 4 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 3 | Content management & content registry | **Core** — content registry |
| 2 | 2 | Content authoring & editing | **Core** (3) |
| 2 | 2 | Site & section structure | **Core** (1) |
| 2 | 2 | Reporting & analytics | **Core** — computed views; reporting engines Extended |
| 2 | 2 | Content delivery & publishing | **Core** — publishing/delivery records; rendering, templating & CDN Extended |
| 6 | 1 | Search & discovery | **Core** — metadata search; indexing engines Extended |
| 6 | 1 | Metadata & taxonomy/tagging | **Core** (7) |
| 6 | 1 | Ingestion & repository consolidation | **Core** — registration records; bulk ingestion & index-in-place engines Extended |
| 6 | 1 | Media & document assets | **Core** (6) |
| 6 | 1 | Records & case information management | **Core** — records substrate; Tyler case-management depth Extended |
| 6 | 1 | Workflow / BPM automation | Extended — BPM engine; lifecycle mechanics **Core** under (4) |
| 6 | 1 | Administration, security & protected access | **Core** — RBAC/admin substrate under (11)/(12) |
| 6 | 1 | Cloud platform hosting (PaaS/IaaS) | Extended — hosting itself |

Named absences: **no sibling's description claims editorial
review/approval workflow, content versioning/revision history,
publish scheduling, WYSIWYG/visual editing, templating/rendering, or
personalization.** The build's lifecycle states, revisions, and
publish windows are therefore registry mechanics of the claimed
content-registry/publishing functions (the Group 10 core-boundary
precedent: category-defining mechanics the products presuppose),
recorded as such — never presented as claimed families.

## The Core — what the merged build implements (12 functions)

1. **Site & section structure registry** — sites (`site-`) and
   sections (`sec-`) as structure records (Acquia build websites;
   Vibrent sites per customer).
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
   registration is the ingestion record (Bibliovation's 225 document
   types; ingestion into a single repository). Registry holds
   metadata + checksum, not file bytes.
7. **Taxonomy & metadata registry** — tags (`tag-`) and per-item
   metadata key/values (Bibliovation metadata read/write/tag).
8. **Metadata search & discovery** — literal case-insensitive
   substring search over items, assets, sites, tags (Bibliovation
   search claim); indexing engines Extended.
9. **Registry reporting** — computed views over the registry (items
   by status/site/type, publish activity, asset counts)
   (Bibliovation + Tyler reporting claims); reporting engines
   Extended.
10. **REST API** — full surface over HTTP, house auth convention
    (X-User/X-Role against demo registry; 401 unknown/mismatched,
    403 permission, denied attempts audited).
11. **RBAC** — admin/publisher/editor/author/viewer matrix, enforced
    in the store before any state change or id allocation and again
    at the service layer.
12. **Audit log** — append-only, JSONL-persistable, records every
    mutation and every denied attempt (`<action>:denied`).

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes
no tier.

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
| REST API | AC-3, SC-8 (partial) | Permission-gated access to the full surface; transmission protection is TLS when configured (see gaps) |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Five-role matrix enforced pre-mutation at two layers; authenticator management stays with the embedding organization |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching equivalence only. FedRAMP authorizes products;
CMMC certifies organizations. The build is not a FedRAMP
authorization and confers no CMMC certification; it is an
open-source implementation whose features trace to the Moderate/L2
control families.

## Implementation contract (summary)

`src/cms/` (package `cms`, Python stdlib only): `errors`, `access`,
`audit`, `store`, `service`, `__main__`. The store enforces the RBAC
matrix before any state change or id allocation, so failed
operations consume no ids, and the separation-of-duties guard for
the editorial lifecycle lives in the single method
`_check_approver_not_author`. Entry point: `python -m cms serve`,
port 8793. Demo users: alice=admin, bob=publisher, carol=editor,
dave=author, erin=viewer.

## Coverage statement (for this build)

- Forks spec'd: **4 / 4**, each with evidenced claims (19 total).
- Core implemented: **12 / 12** functions above.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Rendering & templating engines and visual/WYSIWYG editors.
- CDN / delivery network and runtime site serving (Acquia).
- Enterprise search indexing engines: Boolean/concept/fuzzy/
  multilingual/hierarchical/geospatial indexing (Bibliovation).
- Bulk ingestion & index-in-place engines.
- Library ILS vertical (Bibliovation): circulation, MARC21
  cataloging depth, EDI acquisitions, discovery layer.
- BPM / case-management engine (Tyler TFCP): EEO, labor relations,
  reasonable accommodations, background investigations,
  inspector-general casework.
- Participant engagement & research platform vertical (Vibrent
  DHRP): recruitment, participant portal, longitudinal study
  tooling.
- Platform hosting itself (Acquia PaaS runtime).
- Personalization / experience optimization.
- Editorial workflow engines beyond lifecycle mechanics (parallel
  review, routing, notifications — claimed by no sibling).

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when configured; multi-tenancy
(single-tenant reference deployment); demo identities are hooks,
not an IdP (IA-2 stays with the embedding organization).
