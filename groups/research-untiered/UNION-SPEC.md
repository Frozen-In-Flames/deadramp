# Union Spec — Research, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 9**: **4 forks**, category
**Research**, **tier null**. Every member's FedRAMP impact level
is **Unknown** in the source dataset — the source publishes no
baseline for these offerings — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly census unit `untiered:Research` in
`../../remainder.json` (4 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: 1 fork carries Analytics
(Leadership Connect), 1 Health & Wellness (OpenClinica), 1
Artificial Intelligence (AI) (Sixtyfour), and 1 Operations
Management (Sustainment); the census assigned all four to
Research from their own descriptions, and the spec sheets record
the assignment. Three of the four carry "Research" among their
source business categories; **Sustainment does not** — its
assignment rests on its description's market-research function
alone (the census's classifier note: "Supplier discovery /
market research"). Authorization status as recorded is Initial
Implementation for all four — a status is record data, not a
claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 4
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined
by FedRAMP ID. All 4 descriptions were present in the cached
dataset and match `../../remainder/uncovered.json` exactly (4/4).

## How functions were counted

The category's fixed 9-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../research-l2/scratch/extract.py`, parsed, never executed)
and asserts it is the same 9 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim table
exactly — 1 of 1 forks, 9 of 9 claims, deep-equal** against the
sheet at the original ship commit (`4c868c3`) — using the
founding sentence split and evidence rule (first matching
sentence, stored verbatim, no truncation). The founding group's
current `specs.json` carries five later remainder-addition
sheets; the proof is taken against the ship-commit copy, not the
enlarged file.

The taxonomy is Gen3-shaped by construction: the founding group
defined it from its single fork's two-sentence description, and
its patterns are that description's literal phrases. The founding
group's recorded judgment is applied as recorded: licensing and
delivery properties ("open-source", "multi-tenant Software as a
Service") carry platform dispositions *when they fire* — neither
phrase fires here; the verb discipline is the founding one —
`data_analysis` takes the verb "analyzing", not the nouns
"analysis" / "analytics"; `data_management` takes "managing", not
"maintains" / "maintained"; `data_sharing` takes "sharing", not
"shared". An exclusion pass scanned for scope-exclusion phrasing
and third-party catalogue segments: matched text is `service_desc`
only, `certified_services` record fields are never matched (three
of the four forks carry non-empty lists — OpenClinica's contains
an "API Access (REST/SOAP)" entry its description never asserts),
and the raw pass in any case produced **no hits at all**, so
nothing was removed. Adjudications and near-misses are itemized
in `scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**Result: 0 claims across the set; all 4 forks are zero-claim.**
The zeros are this set's recorded result, not a defect to be
repaired by re-tuning — the category's own precedents stand the
same way (the Research L1 singleton at zero claims; three of the
founding group's five remainder additions at zero).

Census citations: 6 citations are recorded for these forks in the
census; **6 of 6 verify** as verbatim substrings of the forks' own
descriptions, and **0 of 6** are a claim evidence sentence (there
are no claims for them to evidence). Verification is not a claim,
in either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 4 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged. Every
family stands at zero claimants in this set; each row is a named
absence, recorded rather than back-filled.

| # | Function | Forks claiming (of 4) | Disposition in this build |
|---|---|---:|---|
| 1 | Data commons development, configuration & operation | 0 | **Core substrate** (the commons registry is the records form; the commons runtime engine is Extended) — **zero claimants in this set; named absence** |
| 2 | Data ecosystems / data meshes | 0 | **Core substrate** (ecosystems and meshes are commons record kinds; federation engines are Extended) — **zero claimants; named absence** |
| 3 | Workspaces | 0 | **Core substrate** (the workspace registry) — **zero claimants; named absence** |
| 4 | Data management (managing data) | 0 | **Core substrate** (the dataset registry, metadata + checksums; ingestion/harmonization engines are Extended) — **zero claimants; named absence** |
| 5 | Data analysis (analyzing data) | 0 | Extended (analysis engines compute; the workspace registry is the records form) — **zero claimants; named absence** |
| 6 | Data sharing | 0 | **Core slice** (sharing transacted as request / decision / time-boxed grant records; the delivery engine is Extended) — **zero claimants; named absence** |
| 7 | Open access & controlled access data | 0 | **Core substrate** (the access-tier designation on every dataset record, gated by the request/decision/grant records; enforcement on actual delivery is Extended) — **zero claimants; named absence** |
| 8 | Open-source platform (platform note) | 0 | Platform note (a licensing property; this build is likewise Apache-2.0) — **zero claimants; named absence** |
| 9 | Multi-tenant SaaS delivery (platform note) | 0 | Platform note (delivery prose; the build is a single-tenant reference deployment) — **zero claimants; named absence** |

Substance asserted without the families' phrases is itemized
under Named absences below and in `scratch/ARTIFACTS.md`; it is
registered as gaps, not tagged.

## The Core — what this build implements (11 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's eleven-function substrate **whole** — data
commons registry & membership; organization registry (opaque
references); workspace registry; dataset registry (metadata +
checksums only); access request records; decision records;
access grant records; search & summary reporting; API access;
access control; audit log. **No core function is claim-supported
in this set** — all nine taxonomy families stand at zero — so
every function is **carried, not claimed**: the substrate is the
category's records machinery, it is tier-independent code (the
founding source contains no tier or baseline machinery beyond a
docstring, re-anchored here), and it is what any Research-category
offering's records presuppose. No function is claimed to be
*attained* by any fork — the build is the merged open
implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/research/` in 6 of 7 modules; the seventh (`__init__.py`)
differs by its docstring only, which in the founding build named
the Moderate/L2 baseline and here names tier null (SHA-256
accounting in this group's README and `tests/README.md`). The
implementation contract is the founding spec's contract,
unchanged: Python 3, standard library only, package `research`
under `src/`, ids sequential per object type with fixed prefixes
(`com-`, `org-`, `ws-`, `ds-`, `ar-`, `dec-`, `gr-`), failed
operations consume no id and change nothing, durations whole days
(positive `int`; bools, floats, and strings rejected), all
timestamps UTC ISO-8601, roles `admin|member|viewer` with the
founding permission matrix, commons membership as the boundary
every commons-scoped function enforces, and the audit log
append-only with denied attempts recorded. Where the founding
contract's text says access control and audit are L2 baseline
hooks, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline.

Three founding disciplines are preserved exactly, as the founding
build implements them:

- **Privacy is structural.** Records carry metadata and opaque
  references only — never research subject data, never dataset
  contents. Every entity shape is pinned by test to exactly its
  key set (the dataset record: exactly 9 keys — `id`,
  `commons_id`, `name`, `description`, `access_tier`, `sha256`,
  `size_bytes`, `created_by`, `created_utc` — no field exists
  that could hold a payload), and caller-supplied verification
  content is hashed transiently, compared, and discarded. **No
  record shape carries a field for a score, and nothing in this
  build is scored or ranked** — summaries are counts, computed on
  read.
- **Grant status is derived, never stored.** A grant's status
  (`scheduled` / `active` / `expired` / `revoked`) is derived at
  read from its start, expiry, and revocation timestamp against
  the read clock: before start it is `scheduled`, inside the
  window `active`, strictly after expiry `expired`, and a
  recorded revocation beats expiry. The stored grant record
  carries no `status` key. Grants are **time-boxed and confer
  nothing by themselves** — they are records; actual data
  delivery is Extended. A commons' lifecycle status, by contrast,
  is event-driven and *is* stored, as in the founding build.
- **Sharing is gated by people deciding.** Access requests exist
  only against `controlled` datasets — **a request against an
  open dataset is rejected by design** (open data needs no gate,
  and a request record for one would be a false one) — and the
  decider of a request is never its requester (separation of
  duties, enforced in the store).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 4 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Two tiers of documentation, kept separate:

**Taxonomy tier — none.** No taxonomy family fires anywhere in
this set, so no documented control claim stands at the taxonomy
tier. (The category's taxonomy is functional by founding design —
it carries no control families; in the tiered groups the control
mapping was carried by the baseline section, and at tier null
there is no baseline to carry it.)

**Prose tier** — control language in description sentences that
fired no family, traced and quoted, never converted to claims:

- **Identification & authentication (IA)** — documented,
  **1 fork**: Leadership Connect (FR2632054521) — "agency user
  account and profile records, authentication and session data,
  single sign-on identity assertions where an agency has
  configured federated access". The fork documents account
  records and federated authentication assertions about its own
  platform; identity provision itself stays with the agency's
  configured federation, exactly as the sentence states it.
- **Audit (AU)** — documented, **1 fork**: Leadership Connect
  (FR2632054521) — "usage and audit records associated with
  individual agency users". The founding taxonomy has no audit
  family, so this language stands at prose weight only.

**Explicitly not a documented control claim:** Sustainment's
"purpose-built for federal security and compliance requirements"
(FR2631747315) names no control, mechanism, or practice; it is
posture prose and documents nothing. OpenClinica's and
Sixtyfour's descriptions carry no control language at all.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AC (no sentence
asserts access control, permissions, or enforcement; Leadership
Connect's "shared among users within an agency account" is
distribution prose, recorded as such), SC (no encryption language
occurs anywhere in the set), AT, CA, CM, CP, IR, MA, MP, PE, PL,
PM, PS, RA, and SA — is asserted by no description in the set. If
the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **All nine families — 0 of 4.** Every family in the category
  taxonomy stands at zero claimants in this set, and all four
  forks are zero-claim. The set's result is stated, not softened.
- **Data analysis, in substance — Leadership Connect,
  OpenClinica.** "contract award and subaward analysis",
  "relationship-graph analytics", "reporting and analytics":
  the nouns occur; the family's verb ("analyzing") does not.
- **Data management, in substance — Leadership Connect.** The
  description's records verbs are "creates, collects, processes,
  stores, and maintains"; "managing" never occurs.
- **Data sharing, in substance — Leadership Connect.** "records
  of lists and views **shared** among users within an agency
  account": the past participle occurs; "sharing" does not.
- **Workspaces — 0 of 4, without substance nearby.** No fork's
  prose names workspaces in any form; the registry is carried as
  category substrate only.
- **Platform notes — 0 of 4.** All four forks describe SaaS
  delivery, none writes "multi-tenant Software as a Service";
  none writes "open-source" (Sixtyfour's "online sources" is a
  different phrase).

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented.
The first group is this set's forks' own described substance
(claimant counts are zero throughout — these are gap
registrations from substance, not from claims); the second is the
category's standing engine tail, restated with zero claimants in
this set:

- [ ] Market & policy intelligence platform — decision-maker directory, legislative tracking, congressional hearing coverage (Leadership Connect)
- [ ] Contract award & subaward analysis engine (Leadership Connect)
- [ ] Entity / relationship-graph analytics engine (Leadership Connect)
- [ ] Saved-search, alerting & entity-tracking engine (Leadership Connect)
- [ ] Electronic data capture (EDC) engine for clinical trials (OpenClinica)
- [ ] eConsent & electronic clinical outcome assessment (eCOA) engines (OpenClinica)
- [ ] Clinical-trial reporting & analytics engine (OpenClinica)
- [ ] Identity resolution & background investigation engine (Sixtyfour)
- [ ] Ongoing identity monitoring engine (Sixtyfour)
- [ ] Supplier discovery & market research engine (Sustainment)
- [ ] Supplier intelligence & capabilities-data engine (Sustainment)
- [ ] Data commons runtime engine (actually developing, configuring, and operating a running commons; the build is its records substrate)
- [ ] Data ingestion / ETL engine (nothing is ingested; dataset records are metadata + checksums)
- [ ] Data harmonization engine (common-data-model mapping and transformation of real datasets)
- [ ] Indexing & metadata catalog engines beyond the registry (search indexes over dataset contents)
- [ ] Query & analysis workspace engines (the analysis computation the workspaces host)
- [ ] Cohort builder / cohort discovery engine
- [ ] Cross-commons federation / data mesh networking (commons here are records; no inter-commons protocol runs)
- [ ] Data delivery / transfer engine for sharing (grants are records; no data moves)
- [ ] Access enforcement on data delivery (the gate on actual reads of dataset content; this build gates records)
- [ ] Identity provider / identity management service (identity stays with the embedding organization; Leadership Connect's documented SSO assertions are its own federation surface, not implemented here)
- [ ] Encryption & key-management platform layer (no fork in this set documents an encryption claim; the build performs no cryptography of its own — TLS is deployment-layer when a certificate is configured, encryption at rest is deployment-layer, and FIPS-validated crypto (SC-13) is not claimed by the build)

## Coverage statement (for this build)

4 forks spec'd of 4 in census unit `untiered:Research`; **0
taxonomy claims** tagged from the forks' own descriptions (0 of 4
forks claiming at least one — every fork zero-claim, recorded);
the eleven-function substrate carried from the founding Research
L2 build (6 of 7 source modules byte-identical, the seventh
re-anchored by docstring only) and re-anchored to tier null; tier
null recorded on every sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or a
control baseline for any fork or for the build itself.
