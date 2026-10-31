# Union Spec — Content Management System (CMS), untiered set (DeadRamp Phase 2, remainder)

The union contract for an **untiered set**: **2 forks**, category
**Content Management System (CMS)**, **tier null**. Every member's
FedRAMP impact level is **Unknown** in the source dataset — the
source publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in the
registry until the source publishes a baseline." The Documented
control claims section below replaces the baseline section a
tiered group's union spec carries.

Membership is exactly census unit `untiered:Content Management
System (CMS)` in `../../remainder.json` (2 fork IDs, verified
mechanically): **Liferay SaaS** (Liferay, Inc., FR2701857792) and
**Nintex Drawloop DocGen** (Nintex, FR2001462460). In `forks.json`
the set is mixed as filed: Liferay is filed under Collaboration
(its source business categories list Collaboration first, with
Content Management System (CMS) among five), and Nintex is filed
"Uncategorized (none in source)" with no business categories at
all; the census assigned both to this category from their own
descriptions (classifier notes: "Core capabilities listed first
are content and site management" for Liferay; "Document generation
and document package management" for Nintex), and the spec sheets
record the assignment. Authorization statuses as recorded are
Initial Implementation (Liferay) and FedRAMP In Process (Nintex)
— a status is record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. Both descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (2/2).

## How functions were counted

The category's fixed 13-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../cms-l2/scratch/extract.py`, parsed, never executed) and
asserts it is the same 13 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 4 of 4 forks, 19 of 19 claims, deep-equal** against the
sheets at the original ship commit (`de9db16`) — using the
parent's sentence split (with the founding normalization,
carriage returns to spaces before sentence-splitting) and
evidence rule (first matching sentence; over 400 characters,
truncated to 397 + '...'). Neither description in this set
contains a carriage return; Liferay's carries "\n" line breaks,
which the founding split absorbs where they follow
sentence-ending punctuation and otherwise leaves inside one
sentence — the founding rule applied exactly as shipped.

The founding group's recorded wording-artifact corrections are
embodied in the taxonomy patterns and its recorded judgment
(corrections 1–7 in `../../cms-l2/scratch/ARTIFACTS.md`) is
applied as recorded: vendor implementation substrate tags no
hosting function; generic SaaS-Platform delivery-model mentions
tag nothing; marketing prose tags nothing; generic verb strings
assert no family; claims come from description text only, never
from business categories, product names, `certified_services`
record fields, or compliance posture. An exclusion pass scanned
the set's one raw hit's evidence sentence for third-party
catalogue segments and scope-exclusion phrasing: **no hit was
removed** — the sentence is the fork's own first-party "Core
capabilities" list, which stands at **catalogue weight** per the
founding additions' posture, and it negates nothing. Nintex
produced no raw hits. Adjudications and near-misses are itemized
in `scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not
a ceiling. **1 claim** across the set; **1 of 2 forks carries a
claim**. The zero-claim fork is recorded under Named absences,
not hidden.

Census citations: 3 citations are recorded for these forks in
the census; **3 of 3 verify** as substrings of the forks' own
descriptions (Nintex's two exactly; Liferay's one after
whitespace normalization — the source's line breaks are "\n",
the citation renders them as spaces), and **0 of 3** is itself a
claim evidence sentence: Liferay's citation is its first
sentence (platform prose), not the capabilities sentence that
evidences its one claim, and Nintex has no claims for its
citations to evidence. Verification is not a claim, in either
direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 2 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Search & discovery | 1 | **Core** (metadata search; indexing engines Extended) |
| 2 | Content management & content registry | 0 | **Core** (the content registry) — zero claimants in this set; named absence |
| 2 | Content authoring & editing | 0 | **Core** — zero claimants in this set; named absence |
| 2 | Site & section structure | 0 | **Core** — zero claimants in this set; named absence |
| 2 | Metadata & taxonomy/tagging | 0 | **Core** — zero claimants in this set; named absence |
| 2 | Ingestion & repository consolidation | 0 | **Core** (registration records; bulk ingestion & index-in-place engines Extended) — zero claimants in this set; named absence |
| 2 | Media & document assets | 0 | **Core** — zero claimants in this set; named absence |
| 2 | Records & case information management | 0 | **Core** (records substrate; case-management depth Extended) — zero claimants in this set; named absence |
| 2 | Reporting & analytics | 0 | **Core** (computed views; reporting engines Extended) — zero claimants in this set; named absence |
| 2 | Administration, security & protected access | 0 | **Core** (RBAC/admin substrate) — zero claimants in this set; named absence (the family's phrases do not occur; role-based-permissions language is traced under Documented control claims instead) |
| 2 | Content delivery & publishing | 0 | **Core** (publishing/delivery records; rendering, templating & CDN Extended) — zero claimants in this set; named absence |
| 2 | Workflow / BPM automation | 0 | Extended (BPM engine; lifecycle mechanics **Core**) — zero claimants in this set; named absence |
| 2 | Cloud platform hosting (PaaS/IaaS) | 0 | Extended (hosting itself) — zero claimants in this set; named absence |

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's twelve-function substrate **whole** — site &
section structure registry; content type registry; content
registry & authoring (items, with a revision record minted on
every edit); editorial lifecycle (draft → in_review → approved →
published → archived, role-gated, the approver never the item's
author); publishing records & windows (window state derived at
read time from stored facts, never stored); media & document
asset registry (metadata + SHA-256 checksum, never file bytes);
taxonomy & metadata registry; metadata search & discovery;
registry reporting; REST API; RBAC (five-role matrix enforced
before any state change or id allocation); append-only audit log
recording every mutation and every denied attempt. The substrate
is records machinery that every sibling's output presupposes,
and it is tier-independent code: the founding source contains
**no tier or baseline machinery at all** (verified by scan —
there was nothing tier-shaped to strip, and no "L2" text to
re-anchor). In this set, **one of the twelve functions is
claim-supported**: metadata search & discovery, by
`search_discovery` (Liferay, 1 fork, at catalogue weight). The
other eleven are **carried, not claimed**: no fork's description
fires their families here, and that is stated rather than
smoothed over. The lifecycle states, revisions, and publish
windows are the founding build's registry mechanics, carried
with the code; per the founding group's named-absence
discipline they are **never presented as claimed families** —
here they are not even indirectly claim-supported, because the
content-registry and delivery families they mechanize are
themselves unclaimed in this set. Functions are **carried** as
substrate; no function is claimed to be *attained* by any fork —
the build is the merged open implementation, not any fork's
product.

The carried code is **byte-identical** to the founding group's
`src/cms/` (7 of 7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `cms` under `src/`, ids sequential per
object type with fixed prefixes (`site-`, `sec-`, `ct-`, `ci-`,
`rev-`, `pub-`, `asset-`, `tag-`), failed operations consume no
id and change nothing, slug uniqueness enforced per its scope,
all timestamps UTC ISO-8601, roles
`admin|publisher|editor|author|viewer` with the founding
permission matrix, the separation-of-duties guard for the
editorial lifecycle in the single method
`_check_approver_not_author`, publishing window state derived
never stored, asset bytes hashed when supplied and never
retained, and the audit log append-only with denied attempts
recorded as `<action>:denied`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded here with its evidence; it is not the build's control
attainment, and nothing in this section fills a family in from
any baseline.

Control areas **documented** by at least one fork in the set —
both at **prose weight**: the sentences below carry control
language, but the taxonomy's `access_administration` family did
not fire on them, because that family's patterns are the
founding forks' own phrases ("administrative tools" /
"protected access" / "proper permissions"). Documenting the
language here converts nothing into a taxonomy claim.

- **Access control (AC)** — **Liferay SaaS** (FR2701857792):
  "granular role-based permissions", and "permission-controlled
  access to documents and digital assets" (both in its
  capabilities list).
- **Identification & authentication (IA)** — **Liferay SaaS**
  (FR2701857792): "single sign-on via SAML 2.0 and OpenID
  Connect" (in its capabilities list). This documents the
  fork's SSO assertion; the build ships access-control *hooks*,
  not an IdP.

Recorded, **not** a documented control claim:

- **Liferay SaaS**: "operated under Liferay's SOC 2 Type
  II–audited security program" — a compliance assertion about
  the operator's own security program, recorded at
  compliance-assertion weight. It asserts no 800-53 family for
  the offering and documents no audit-logging function.
- **Nintex Drawloop DocGen**: "know their document data is
  secure and compliant throughout the process" — posture prose.
  It names no control, mechanism, or standard, and documents
  nothing.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, AU, CA, CM,
CP, IR, MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control
claims** — is asserted by no description in the set. (No
description here contains encryption, audit-logging, or
assessment language in control terms at all.) If the source
later publishes an impact level for either of these offerings,
the tier is recorded then and not before.

## Named absences

- **Twelve of thirteen families — 0 of 2.** Content registry,
  authoring & editing, site structure, metadata & taxonomy,
  ingestion & repository, media & document assets, records
  management, reporting, workflow/BPM, access administration,
  delivery & publishing, and platform hosting each have no
  claimant in this set. The per-family near-misses (prose that
  describes the function in words the verbatim patterns do not
  take) are itemized in `scratch/ARTIFACTS.md`.
- **Zero-claim fork:** FR2001462460, Nintex Drawloop DocGen —
  a document-generation product whose description's verbs
  ("create, manage and generate document packages") match no
  family phrase, whose "documents" are never "digital
  documents", and whose whole function (document generation)
  has no family in this taxonomy. The zero is recorded, not
  repaired; the taxonomy was not re-tuned for it.
- **The founding named absences stand in substance.** The
  founding group recorded six functions no sibling claimed and
  no family keys on: editorial review/approval workflow,
  content versioning/revision history, publish scheduling,
  WYSIWYG/visual editing, templating/rendering, and
  personalization. Liferay's prose asserts **five of the six in
  substance** — editorial approval workflows; documents and
  media versioning; a visual page builder; reusable fragments
  and templates; audience-targeted content and user
  segmentation (publish scheduling is the one absence with no
  substance here either). They remain absences **as claims**
  and are registered as gaps below; the taxonomy's silence
  about them is founding design, not an oversight this set
  corrects.
- **The floor.** The founding union spec recorded "no fork has
  zero claims" for its four forks. That floor fell at the
  tiered remainder addition (Iron Mountain InSight) and falls
  here (1 of 2 zero-claim; set total 1 claim). Floors are
  recorded, never preserved by re-tuning.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented. The founding group's gaps stand as registered;
below are restated only where this set's forks claim or
substantiate them, plus this set's new gaps:

- [ ] Enterprise search indexing engines (Boolean/concept/fuzzy/multilingual indexing; this build's search is literal substring over registry metadata — Liferay's enterprise search is the 1 claimant family, at catalogue weight)
- [ ] Rendering & templating engines and visual/WYSIWYG editors (Liferay substance: visual page builder, reusable fragments and templates)
- [ ] Personalization / experience optimization (Liferay substance: audience-targeted content, user segmentation; deliberately no family — founding judgment)
- [ ] Editorial workflow engines beyond lifecycle mechanics (parallel review, routing, notifications; Liferay substance: editorial approval workflows, configurable workflows for requests, applications, and approvals)
- [ ] Document & media versioning depth beyond registry revision mechanics (Liferay substance: centralized storage with versioning for documents and media)
- [ ] Document generation engines (Nintex Drawloop DocGen's whole function — generating documents and document packages from Salesforce data; fork excess in this category, no family exists)
- [ ] Low-code application builders & form engines (Liferay substance: Liferay Objects custom data models, forms)
- [ ] Identity federation / SSO services (IdP) (Liferay documents SSO via SAML 2.0 / OpenID Connect; the build ships hooks, not an IdP)
- [ ] Multi-site & multilingual site operations depth (Liferay substance: multi-site and multilingual management, portals and intranets on one platform)
- [ ] Headless delivery & integration engines (Liferay substance: headless REST and GraphQL APIs, client extensions as a delivery platform; the build's own REST API over the registry is Core)
- [ ] CDN / delivery network and runtime site serving (Liferay substance: building and operating public websites and portals)
- [ ] Platform hosting itself (both forks are hosted SaaS offerings; Liferay is fully managed on Google Cloud Platform — hosting is Extended per the founding disposition, and the substrate a fork runs on tags nothing)
- [ ] Platform layer (encryption at rest is deployment-layer; TLS only when configured; the build is a single-tenant reference deployment; demo identities are hooks, not an IdP — IA-2 stays with the embedding organization)

Standing founding gaps with **no claimant and no substance in
this set** (library ILS vertical; BPM / case-management engine
depth; participant engagement & research platform vertical;
bulk ingestion & index-in-place engines) remain registered
under the founding group and in `../../GAPS.md`; they are not
re-registered here.

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Content
Management System (CMS)`; 1 taxonomy claim tagged from the
forks' own descriptions (1 of 2 forks claiming at least one);
the twelve-function substrate carried byte-identical from the
founding CMS L2 build and re-anchored to tier null; tier null
recorded on every sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or
a control baseline for any fork or for the build itself.
