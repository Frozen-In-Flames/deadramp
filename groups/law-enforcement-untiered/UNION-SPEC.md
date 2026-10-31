# Union Spec — Law Enforcement, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 17**: **2 forks**, category
**Law Enforcement**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes no
baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until the
source publishes a baseline." The Documented control claims section
below replaces the baseline section a tiered group's union spec
carries.

Membership is exactly census unit `untiered:Law Enforcement` in
`../../remainder.json` (2 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: Pryme Infil is filed under
Law Enforcement; TRM Labs on GovCloud is filed under Cybersecurity
& Risk Management, and the census assigned it to this category from
its own description (its source business categories include Law
Enforcement). The spec sheets record the census assignment.
Authorization statuses as recorded are Legacy FedRAMP Ready (Pryme
Infil) and Initial Implementation (TRM Labs) — a status is record
data, not a claim.

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

The category's fixed 9-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../law-enforcement-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 9 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 2 of 2 forks, 13 of 13 claims, deep-equal** against the
founding sheets (the founding L2 group received no remainder
additions, so its shipped tables are the originals), using the
founding sentence split and evidence rule (first matching sentence
per family, in taxonomy order, stored verbatim, no truncation).

The founding group's recorded wording-artifact corrections are
applied as recorded judgment (identity + audience sentences tag
nothing; assurance prose is not an access-control claim;
`access_control` rests only on the exact phrase "secure access
controls"). An exclusion pass scanned for third-party catalogue
segments and scope-exclusion sentences: **the raw pass produced 0
hits**, so there was nothing to remove — no family pattern occurs
in any sentence of either description. `certified_services` record
fields (non-empty for both forks) were never matched, per the house
method. Adjudications and near-misses are itemized in
`scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**0 claims** across the set; **both forks are zero-claim**. The
founding taxonomy is a legal-research taxonomy — it was defined
from the founding group's two legal-research descriptions — and
these two operational descriptions (a public-safety
command-and-control platform; a blockchain-intelligence
investigation platform) fire none of its phrases. The zeros are
recorded under Named absences, not hidden, and the taxonomy was
not re-tuned: the same outcome this category recorded at its L1
singleton (0 claims) and its L3-adjacent addition (0 claims).

Census citations: 2 citations are recorded for these forks in the
census; **2 of 2 verify** as verbatim substrings of the forks' own
descriptions, and **0 of 2** are a claim evidence sentence (there
are no claims). Verification is not a claim, in either direction;
the per-citation record is `scratch/citation_check.json`.

## Function ranking — both set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged. Every family
stands at 0 of 2 in this set; each row is therefore also a named
absence.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Legal research corpus (primary & secondary law) | 0 | **Core** as the source registry (records of sources; the corpus content itself is Extended) — carried, not claimed here |
| 2 | Legal search tools | 0 | **Core slice**: saved-search records + registry-metadata search — carried, not claimed here. Corpus search/relevance engine: Extended |
| 3 | Citation validation | 0 | **Core slice**: citation-check records with treatment recorded verbatim — carried, not claimed here. The validation engines themselves: Extended |
| 4 | Document management (upload, review, document features) | 0 | **Core** as the document registry (metadata + checksums, review lifecycle; content never stored) — carried, not claimed here |
| 5 | Save, annotate, share & collaborate on research | 0 | **Core**: matter membership + saved searches + annotation records (digests only) — carried, not claimed here |
| 6 | Editorial enhancement (taxonomies & editorial features) | 0 | Extended (the editorial systems are the vendors' proprietary product) |
| 7 | Practice guidance & standard documents | 0 | **Core slice**: guidance/standard-document kinds in the source registry — carried, not claimed here. The guidance content and drafting engine: Extended |
| 8 | Secure access controls | 0 | **Core** (access-control substrate; in this set documented at the prose tier only — see Documented control claims — and carried, not claimed) |
| 9 | SaaS / cloud delivery (platform note) | 0 | Platform note — carried, not claimed here (both offerings are SaaS per their source records; the build is a single-tenant reference deployment) |

## The Core — what this build implements (11 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's eleven-function substrate **whole** — matter
registry & members; source registry; document registry;
verify-by-content; saved-search records; annotation records;
citation-check records; registry reporting; registry search;
access control (RBAC); audit log. The substrate is records
machinery, and it is tier-independent code: the founding build's
source contains no tier or baseline machinery (the one tier-shaped
text is the founding label line in the `__init__.py` docstring,
carried verbatim and accounted in the README's byte-identity
table), so there was nothing tier-shaped to strip. In this set,
**no core function is claim-supported** — the set carries 0 claims
— so every function is **carried, not claimed**, stated plainly.
Functions are carried as substrate; no function is claimed to be
*attained* by any fork — the build is the merged open
implementation, not either fork's product.

The carried code is **byte-identical** to the founding group's
`src/lawenf/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the founding
spec's contract, unchanged: Python 3, standard library only,
package `lawenf` under `src/`, ids sequential per object type with
fixed prefixes (`mat-`, `src-`, `doc-`, `sea-`, `ann-`, `cit-`),
failed operations consume no id and change nothing, all timestamps
UTC ISO-8601, roles `admin|member|viewer` with the founding
permission matrix layered with matter membership, and the audit
log append-only with denied attempts recorded.

The founding privacy discipline is preserved exactly, as the
founding build implements it — it is the strictest form of the
project's privacy discipline:

- No entity shape can hold a real name, a case subject, a party, an
  address, or any identifier of a person. Every entity's exact key
  set is pinned by tests; records are keyed by opaque
  caller-supplied `*_ref` strings only.
- Documents are registry metadata + SHA-256 checksums, never
  content; integrity is checked by verify-by-content.
- Search queries and annotation notes are stored as SHA-256 digests
  only — the store has no parameter that can accept query text or
  note text; the service layer hashes before the store ever sees a
  value.
- Citation treatments are recorded **verbatim** — never normalized,
  never scored, never aggregated into a computed status (ratings
  are records; scoring is an engine, and no engine is built here).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words. A documented control claim
is a **fork's claim about itself**, recorded here with its
evidence; it is not the build's control attainment, and nothing in
this section fills a family in from any baseline. Because the
founding taxonomy carries no control families of its own beyond
`access_control`, this section stands at the prose tier: control
language in the descriptions, traced and quoted, never converted
into taxonomy claims.

Control areas **documented** by at least one fork in the set:

- **Identification & authentication (IA)** — via TRM Labs on
  GovCloud (FR2631258113): "All capabilities share a common
  identity and access management layer, workspace-based
  multi-tenancy, and a unified data plane within the GovCloud
  authorization boundary." An identity layer is asserted; no
  authentication mechanism (no MFA, SSO, or credential phrase)
  is named.
- **Access control (AC)** — documented **in part**, via the same
  TRM Labs sentence: an access *management* layer is asserted.
  The founding family's exact phrase ("secure access controls")
  does not occur, so this stands at prose weight only and is not
  a taxonomy claim (the founding group's Lexis near-miss is the
  same class, recorded there).
- **Cryptographic protection (SC)** — documented at **prose
  weight**, via Pryme Infil (FR2628943632): "encrypted messaging"
  asserts encryption of the offering's messaging function. No
  algorithm, standard, or FIPS claim is made by the fork or
  recorded here, and the build performs no cryptography of its
  own.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, AU, CA, CM,
CP, IR, MA, MP, PE, PL, PM, PS, RA, SA, and SI **as control
claims** — is asserted by no description in the set. Two bounds are
stated explicitly because the words occur: Pryme Infil's "risk
assessments" names an operational function the platform offers to
agencies, not risk-assessment (RA) or assessment (CA) language
about the offering itself; and Pryme Infil's "after-action
documentation" is operational documentation, not audit logging
(AU). Neither is documented here. If the source later publishes an
impact level for either of these offerings, the tier is recorded
then and not before.

## Named absences

- **All nine taxonomy families — 0 of 2.** The founding taxonomy is
  a legal-research taxonomy; neither operational description fires
  any of its phrases. Both forks are zero-claim, recorded, not
  repaired; the taxonomy was not re-tuned for them.
- **Incident / case management for law-enforcement operations —
  unclaimed.** Pryme Infil's substance is operational command and
  planning, but no family in the founding taxonomy names it and no
  records function for it is claimed; the platform itself is an
  Extended gap (below).
- **Evidence management & chain of custody — unclaimed.** No
  description asserts custody over evidence in any words.
- **Criminal records / records-management systems (RMS),
  criminal-history data — unclaimed.** Neither description asserts
  a records system over persons; TRM's "resolve a lead — a name,
  an account, an address — across connected sources" is an
  investigation-resolution function (Extended), not a criminal
  record, and this build's records hold no person data at all.
- **Investigative case files and case subjects — unclaimed.**
  TRM's substance is investigative *tooling*; investigative case
  files as a records function are not claimed, and case subjects
  are exactly what the substrate's privacy discipline cannot hold.
- **Category-discipline exclusions — attributed to neither fork.**
  Surveillance, facial recognition, predictive policing, real-time
  intelligence feeds, and camera/sensor monitoring: the tokens
  `facial`, `predictive`, `surveillance`, `camera`, `sensor` and
  the phrase `real-time intelligence` occur **0 times** in each
  description (counted on the descriptions themselves and pinned
  by test). Pryme Infil's own words are "GPS mapping" and
  "real-time team coordination" — mapping and coordination
  substance, recorded as Extended gaps — and TRM's is "glass-box
  attribution" for cryptocurrency flows. None of the excluded
  functions is claimed, attributed, or built.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
the founding group's engine gaps (the legal corpora themselves,
citation-validation engines, editorial enhancement systems, corpus
search & relevance engines, document content storage/rendering)
are already registered under the founding group and are not
re-registered here. New gaps from this set's forks, with their
claimants in substance (counts are this set's):

- [ ] Command-and-control & operational planning platform (Pryme Infil)
- [ ] Real-time team coordination & encrypted messaging engines, and real channel transports (Pryme Infil — the build transports nothing)
- [ ] GPS mapping & location services (Pryme Infil)
- [ ] Operational risk-assessment tooling (Pryme Infil)
- [ ] After-action documentation & reporting engine (Pryme Infil)
- [ ] Blockchain intelligence & multi-chain investigation graph engine (TRM Labs)
- [ ] All-source intelligence fusion & lead/identity resolution across connected sources (TRM Labs)
- [ ] AI investigation models (TRM Labs — "all-source AI investigation software"; the models are the vendor's product)
- [ ] Workspace multi-tenancy & platform layer (TRM Labs' workspace-based multi-tenancy; the build is a single-tenant reference deployment, encryption at rest is deployment-layer, TLS only when configured)

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Law Enforcement`; 0
taxonomy claims tagged from the forks' own descriptions (both
forks zero-claim, recorded not repaired); the eleven-function
substrate carried byte-identical from the founding Law Enforcement
L2 build and re-anchored to tier null; tier null recorded on every
sheet and pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
either fork or for the build itself.
