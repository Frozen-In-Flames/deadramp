# Union Spec — Legal & Policy, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 12**: **3 forks**, category
**Legal & Policy**, **tier null**. Every member's FedRAMP impact
level is **Unknown** in the source dataset — the source publishes
no baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries.

**This category is not the Law Enforcement category.** Legal &
Policy is its own registry category (founded by Singleton 49, the
VulcanGov AI agent workspace); this set's members are a legal
data-discovery platform, a litigation legal-AI platform, and a
FOIA case-management platform that the census assigned to Legal
& Policy from their own descriptions.

Membership is exactly census unit `untiered:Legal & Policy` in
`../../remainder.json` (3 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: Casepoint Government is
filed "Uncategorized (none in source)" with an empty
business-category list, Litmas AI is filed Legal & Policy, and
Alira is filed Analytics (its business categories list Legal &
Policy fifth of six); the census assigned all three to this
category from their own descriptions, and the spec sheets record
the assignment. Authorization statuses as recorded span FedRAMP
In Process (1) and Initial Implementation (2) — a status is
record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 3
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined
by FedRAMP ID. All 3 descriptions were present in the cached
dataset and match `../../remainder/uncovered.json` exactly (3/3,
including Casepoint's "\r\n" line endings, preserved verbatim).

## How functions were counted

The category's fixed 11-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../legal-policy-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 11 families before tagging.
The founding tagging rule is reproduced exactly — patterns
compiled **case-sensitively**, as the founding extractor compiled
them (`re.compile(pattern)`, no flags); the founding sentence
split; the first matching sentence stored verbatim as evidence,
no truncation. Taxonomy-verbatim proof: before tagging this set,
the extractor reproduced the founding group's **original shipped
claim table exactly — 1 of 1 fork, 11 of 11 claims, deep-equal**
against the sheet at the original ship commit (`b66424e`) — using
the founding fork's description from the same raw cache.

The taxonomy is the founding fork's own phrases (the Group 1
method: families named from that fork's description, each with a
verbatim match pattern). The founding group's recorded judgment
is applied as recorded: infrastructure and component naming tags
nothing; assurance prose is not a function claim; a different
phrase for a similar function earns nothing (the founding
additions pass recorded this at length — "user identity
management" is not "agency user management", "advanced
searching" is not "full-text and semantic search",
"Software-as-a-Service (SaaS)" is not "SaaS AI platform"). An
exclusion pass scanned for scope-exclusion evidence sentences:
the raw pass produced **no hits at all**, so there was nothing
to remove and nothing was invented. Matched text is
`service_desc` only — `certified_services` record fields are
never matched (Alira's record names "Audit Logging and
Monitoring" and "Authentication and Access Management" as
certified services; those are component names, not description
text, and they earn nothing — pinned by test).

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not
a ceiling. **0 claims** across the set; **3 of 3 forks carry zero
claims**. The zeros are recorded under Named absences, not
hidden. This is the same outcome the founding group's six tiered
additions recorded under this taxonomy (0 new claims), for the
same reason: the patterns are one product's phrases, and these
forks describe a different functional surface in different
words. The taxonomy was not re-tuned for this set.

On normalization: the founding extractor has no separate
carriage-return normalization; its split absorbs a "\r" only in
whitespace after sentence-ending punctuation. The founding
fork's description contains no carriage return, so the proof
applies the founding rule exactly as shipped. Casepoint's
description contains 10 carriage returns (paragraph breaks and a
bulleted list); the extractor asserted the claim outcome is
identical with and without a "\r" → space pre-normalization
(`scratch/cr_notes.json`), so no normalization step was added.

Census citations: 4 citations are recorded for these forks in
the census; **4 of 4 verify** as verbatim substrings of the
forks' own descriptions, and **0 of 4** are a claim evidence
sentence (there are no claims). Verification is not a claim, in
either direction; the per-citation record is
`scratch/citation_check.json`. Per-fork near-misses are itemized
in `scratch/ARTIFACTS.md`.

## Function ranking — all 3 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 3) | Disposition in this build |
|---|---|---:|---|
| 1 | AI agent workspace | 0 | Core slice in the founding build (workspace & session records); the agent runtime is Extended — **zero claimants in this set; named absence** |
| 2 | Curated legal library (statutes, regulations, guidance, datasets) | 0 | Core in the founding build (library source registry); corpus content Extended — **zero claimants; named absence** |
| 3 | Full-text and semantic search | 0 | Core slice in the founding build (digest-only saved-search records + registry search); the search engines are Extended — **zero claimants; named absence** |
| 4 | Secure single-use agent sandboxes | 0 | Core slice in the founding build (sandbox session records, single-use rule); the sandbox runtime is Extended — **zero claimants; named absence** |
| 5 | Code execution (in agent sandboxes) | 0 | Core slice in the founding build (execution records); the execution engine is Extended — **zero claimants; named absence** |
| 6 | Document generation | 0 | Core slice in the founding build (document records, metadata + checksum); the generation engine is Extended — **zero claimants; named absence** |
| 7 | Agency user management (administration console) | 0 | Core in the founding build (agency registry, membership, RBAC) — **zero claimants; named absence** |
| 8 | Session audit visibility (administration console) | 0 | Core in the founding build (append-only audit log, admin-gated read) — **zero claimants; named absence** |
| 9 | Usage export (administration console) | 0 | Core in the founding build (usage records + export manifests) — **zero claimants; named absence** |
| 10 | Identity federation & MFA (platform) | 0 | Platform note in the founding build (RBAC hooks, not an IdP) — **zero claimants; named absence** |
| 11 | SaaS delivery (platform) | 0 | Platform note in the founding build (single-tenant reference deployment) — **zero claimants; named absence** (all 3 forks are SaaS offerings in the source's service model; the family's pattern is the founding product's own identity clause, "SaaS AI platform", and no fork here uses it) |

## The Core — what this build implements (13 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's thirteen-function substrate **whole** — agency
registry & membership; workspace registry; agent session records;
execution records; library source registry; saved-search records;
document registry; verify-by-content; usage records; usage export
manifests; registry reporting; registry search; access control &
audit. The substrate is records machinery, and it is
tier-independent code: the founding build's source contains no
tier or baseline machinery, so there was nothing tier-shaped to
strip. **In this set, no core function is claim-supported** — all
three forks claim zero families — so every function is **carried,
not claimed**, stated plainly rather than rounded up. Functions
are carried as substrate; no function is claimed to be *attained*
by any fork — the build is the merged open implementation, not
any fork's product. Where the founding contract's text says "L2"
for the group, read it here as the founding build's label:
at tier null the substrate is claimed against no baseline.

The carried code is the founding group's `src/legalpol/` — 6 of
7 modules byte-identical (SHA-256 accounting in this group's
README and `tests/README.md`); `__init__.py` differs by its
docstring's first line only, re-anchored to name this untiered
set instead of the founding group. The implementation contract
is the founding spec's contract, unchanged: Python 3, standard
library only, package `legalpol` under `src/`, ids sequential
per object type with fixed prefixes, failed operations consume
no id and change nothing, all timestamps UTC ISO-8601, roles
`admin|member|viewer` with the founding permission matrix
layered with agency membership, and the audit log append-only
with denied attempts recorded.

Two founding invariants are preserved exactly, because this
category's workspace handles agency legal work:

- **The single-use rule (the signature invariant).** A sandbox
  session accepts **exactly one** execution record, enforced in
  the store by the `_check_sandbox_unused` seam before anything
  is stored; a second attempt raises `ValidationError`, consumes
  no id, and changes nothing.
- **The privacy discipline.** Records hold metadata and digests,
  not content: documents are registry metadata + SHA-256
  checksums, never content (integrity is checked by
  verify-by-content); **search queries are stored as SHA-256
  digests only — the store's `save_search` has no parameter that
  can accept query text**, and the service layer hashes before
  the store ever sees a value (pinned by test); no entity shape
  can hold a real identifier of a person or a matter's substance;
  **nothing is scored** — no record shape carries a score,
  rating, or computed status of a legal question. Date-derived
  status (`expired`, `sandbox_consumed`) is derived at read,
  never stored; the stored session record carries neither key.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 3 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded here;
it is not the build's control attainment, and nothing in this
section fills a family in from any baseline.

Control areas **documented** by at least one fork in the set:
**none.** No description in this set asserts a NIST SP 800-53
control family in control language. The two nearest items are
recorded here precisely so they are not mistaken for control
claims:

- **Alira (FR2633734932)** — "produce defensible, **auditable**
  release packages": auditability of the offering's *outputs*, an
  assurance adjective about release packages. It asserts no
  audit-logging control over the platform, and it is not the
  taxonomy's `session_audit_visibility` family. (The same fork's
  `certified_services` record field names "Audit Logging and
  Monitoring" and "Authentication and Access Management" —
  record fields, never matched, asserting nothing here.)
- **Litmas AI (FR2701247925)** — "Every fact is **traced to its
  source page and line**": the product's provenance function for
  legal facts (citation validation), not a control claim about
  the platform's own operation.
- **Casepoint Government (FR2009476860)** — "organizations that
  require the **highest level of security** and scalability":
  posture prose, no control family named or described.

Control areas **not documented** by any fork in this set: every
NIST SP 800-53 control family — AC, AT, AU, CA, CM, CP, IA, IR,
MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI **as control claims**
— is asserted by no description in the set. If the source later
publishes an impact level for any of these offerings, the tier
is recorded then and not before.

## Named absences

- **All 11 taxonomy families — 0 of 3, each.** The taxonomy is
  the founding fork's own phrases; no sentence in any of the
  three descriptions uses any of them. Every family row in the
  ranking above is a named absence.
- **Zero-claim forks — all 3:** FR2009476860 (Casepoint
  Government), FR2701247925 (Litmas AI), FR2633734932 (Alira).
  The zeros are recorded, not repaired; the taxonomy was not
  re-tuned for them — the same posture the founding additions
  took toward their six zero-claim newcomers.
- **Substance without a family phrase** (recorded, not
  claimed): Litmas's agentic associate and tool-calling runtime;
  Litmas's legal research and drafting of motions, pleadings and
  responses; Casepoint's legal hold, eDiscovery, FOIA, filestore,
  cloud-collection and app-builder modules; Casepoint's bare
  "search" and predictive analytics; Alira's FOIA case
  management, exemption application, and auditable release
  packages. Each is a gap below, in its own name or under a
  registered gap it joins in substance.

## Gaps (registered for the final batch)

Extended functions specified for this category, not implemented.
The founding group's 9 gaps and the additions' 10 gaps stand as
registered in `../../GAPS.md`; they gain **no claimants** from
this set (0 claims) and are not re-registered here. This set's
forks join several registered gaps **in substance** — Casepoint
under the eDiscovery processing & collection engine, the
eDiscovery document review platform, the eDiscovery production
engine, legal hold & preservation management, AI document
analysis for discovery, and the FOIA & disclosure release
engine; Litmas under the AI agent runtime and the document
generation engine — recorded here, not re-registered.

New gaps named by this set's own descriptions:

- [ ] **Legal research, evidence mapping & citation-validation
  engine** — source-traced legal research: evidence mapping,
  citation validation, and drafts tied to the mapped record
  (Litmas AI)
- [ ] **FOIA case management system of record** — the full
  request lifecycle as one system of record: intake, statutory
  deadline tracking, consistent exemption application, and
  requester / analyst / stakeholder portals (Alira)
- [ ] **Discovery platform app builder / extensibility** —
  customer-built applications on the discovery platform
  (Casepoint Government)

## Coverage statement (for this build)

3 forks spec'd of 3 in census unit `untiered:Legal & Policy`;
0 taxonomy claims tagged from the forks' own descriptions (3 of
3 forks zero-claim, recorded not repaired); the thirteen-function
substrate carried from the founding Legal & Policy L2 build and
re-anchored to tier null; tier null recorded on every sheet and
pinned by tests. Nothing in this build claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
any fork or for the build itself.
