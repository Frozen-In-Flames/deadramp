# Union Spec — Construction, untiered set (DeadRamp Phase 2, remainder)

The union contract for the seventh **untiered set**: **6 forks**,
category **Construction**, **tier null**. Every member's FedRAMP
impact level is **Unknown** in the source dataset — the source
publishes no baseline for these offerings — so no tier is assigned,
no CMMC equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's union
spec carries.

Membership is exactly census unit `untiered:Construction` in
`../../remainder.json` (6 fork IDs, verified mechanically).
In `forks.json` the set is mixed as filed: 2 forks carry the
Construction category, 2 are filed under Artificial Intelligence
(AI) (the Specset pair), 1 under Collaboration (InEight Document),
and 1 is filed "Uncategorized (none in source)" (Four BT); the
census assigned all 6 to Construction from their own descriptions,
and the spec sheets record the assignment. Authorization statuses
as recorded span Initial Implementation (5) and FedRAMP Certified
(1, InEight Document — at impact "Unknown"; a status is record
data, not a claim, and it does not move the tier off null).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 6
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 6 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (6/6).

**Duplicate authorization pair:** FR2631258135 and FR2631747321
(Specset Cloud Platform, both records) are spec'd as separate
sheets, per the Phase 1 rule that paired records stay separate.
Their descriptions are byte-identical in the source and their claim
tables are identical (6 claims each); the sheets differ only in
fork_id and source record. FR2631258135's own description states
the second listing is a duplicate created at intake, "pending
retirement, requested 2026-08-31" — recorded; the census counts
both, and so does this build. The pair is counted twice in every
count below, as the registry counts it.

## How functions were counted

The category's fixed 23-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../construction-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 23 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 4 of 4 forks, 25 of 25 claims, deep-equal** against the
sheets at the original ship commit (`bc0751c`) — using the
founding segmentation (lines, then sentences) and evidence rule
(first matching segment; over 400 characters, truncated to
397 + '...').

The founding group's recorded scoping decisions are embodied in
the taxonomy patterns themselves and were applied as recorded
judgment, not re-decided here: schedule/date phrases fire only on
the taxonomy's phrases, not adjacent project prose; cost figures
are never claims and money vocabulary earns nothing by itself
(`financial_tracking` requires "financials"/"spend" text — the
founding group deliberately kept "pricing proposals" out); bare
"security" never tags identity & access control; driver "score
cards" never tag safety incidents; bare "track" is never a
pattern. An exclusion pass scanned every raw hit's evidence
sentence for third-party catalogue segments and scope-exclusion
phrasing: **no hits were removed** — the set's scope-exclusion
prose (Facility Grid's "separate products … not part of this
offering" paragraph) fires no family, and Trimble's modular
packages are a first-party component catalogue, standing at
catalogue weight per the founding additions' posture. Three
standing claims rest on wording artifacts and are recorded **at
artifact weight** in `scratch/ARTIFACTS.md`: Specset's
`compliance_payroll` (both records) fires on UFGS
specification-compliance checking, Trimble's `compliance_payroll`
on the adjective "high-compliance", and Trimble's `audit_logging`
on "audit-ready" — none of the three asserts the family's
substance, and the payroll consequence is stated in the Core
section below.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**27 claims** across the set; **every fork carries at least one
claim** (no zero-claim fork in this set).

Census citations: 7 citations are recorded for these forks in the
census; **7 of 7 verify** as verbatim substrings of the forks' own
descriptions (whitespace-normalized), and **7 of 7** are
themselves a claim evidence sentence. Verification is not a
claim, in either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 6 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 6) | Disposition in this build |
|---|---|---:|---|
| 1 | Project & job-order records | 5 | **Core** |
| 2 | Documents, forms, templates & clauses | 4 | **Core** (document registry & versions); template/clause libraries Extended |
| 3 | Prevailing-wage & workforce compliance records | 3 | **Core** (payroll records, violations, derived compliance status) — **but see the artifact note: in this set the family's claims are in name only** |
| 3 | Workflow & process automation | 3 | Extended — engines; lifecycle state machines are the in-core seed |
| 5 | AI/ML capability | 2 | Extended — AI document-review models (Specset pair) |
| 5 | Submittal & RFI records | 2 | **Core** |
| 5 | Multi-tenant deployment | 2 | Platform property — not a function (see gaps) |
| 8 | Contract lifecycle management | 1 | **Core** (records & lifecycle); CLM workflow engine Extended |
| 8 | Contractor & subcontractor participation | 1 | **Core** (project participants with tiers) |
| 8 | GPS & location tracking | 1 | Extended — spatial/location platform |
| 8 | Cost data & estimating | 1 | Extended — estimating engine & benchmark cost data; estimate *records* Core (cost entries of kind `estimate`) |
| 8 | Audit logging | 1 | **Core** (substrate) — the claim stands at artifact weight ("audit-ready") |
| 8 | Schedule & milestone records | 1 | **Core** |
| 14 | Workforce records & timekeeping | 0 | **Core** — carried, not claimed in this set |
| 14 | Job dispatch & assignment | 0 | **Core** (dispatch records) — carried, not claimed in this set; routing/optimization Extended |
| 14 | Fleet & vehicle telematics | 0 | Extended — telematics platform; no claimant in this set |
| 14 | Financial & spend tracking | 0 | **Core** (cost records & project cost summary) — carried, not claimed in this set |
| 14 | Key-date alerts & notifications | 0 | **Core** (alerts derived from key dates & derived states) — carried, not claimed in this set |
| 14 | Electronic signatures | 0 | Extended — signature execution; no claimant in this set |
| 14 | Search, reporting & analytics | 0 | **Core** (records substrate) — carried, not claimed in this set; analytics engines Extended |
| 14 | Identity & access control | 0 | **Core** (baseline substrate) — carried, not claimed in this set |
| 14 | Inspection & punch-list records | 0 | **Core** — carried, not claimed in this set (named absence: a commissioning platform's checklists and tests are this work in substance) |
| 14 | Safety-incident records | 0 | **Core** — carried, not claimed in this set |

## The Core — what this build implements (17 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's seventeen-function construction records substrate
**whole** — organizations & participation; projects; documents;
contracts; submittals & RFIs; schedule & dispatch; inspections &
punch list; safety incidents; workforce records; payroll &
compliance; costs; derived alerts; reports; search; REST API;
access control; audit log. The substrate is records machinery that
every sibling's work presupposes, and it is tier-independent code:
the founding source contains no tier or baseline machinery, so
there was nothing tier-shaped to strip. Where the founding
contract's text ties functions to the Moderate/L2 baseline (the
access-control and audit substrate), read it here as
**baseline-neutral substrate**: at tier null it is carried, claimed
against no baseline. Functions are **carried** as substrate; the
claims that support them are recorded below, and no function is
claimed to be *attained* by any fork — the build is the merged
open implementation, not any fork's product.

Claim support in this set, per function:

- **Claim-supported:** projects (5 forks); documents (4);
  organizations & participation (1, Facility Grid's "prime
  contractors"); contracts (1, Facility Grid — on deliverables
  language, a thin basis recorded in `scratch/ARTIFACTS.md`);
  submittals & RFIs (2, the Specset pair — a family the founding
  group carried at zero and this set claims); schedule —
  milestones half (1, Facility Grid's "schedules"); costs —
  estimate-records half (1, Four BT's estimating, via the
  `cost_data_estimating` family's Core records disposition);
  audit log (1, Trimble — **at artifact weight only**:
  "audit-ready" is readiness marketing, not an audit-log
  assertion).
- **Claimed in name, not in substance:** payroll & compliance.
  The family's 3 claims all rest on wording artifacts (Specset's
  UFGS specification-compliance checking; Trimble's
  "high-compliance" adjective); none asserts prevailing-wage,
  payroll, or workforce-compliance records. Payroll records,
  violation records, and the derived compliance status are
  therefore **carried, not claimed in substance** in this set.
- **Carried, not claimed:** inspections & punch list; safety
  incidents; workforce records & timekeeping; dispatch records
  (the `job_dispatch` family stands at 0); financial & spend
  tracking (the cost *summary* side of costs); derived alerts;
  reports; search; access control. The REST API is substrate with
  no family in this category's taxonomy (Facility Grid names a
  REST API in prose; that earns no claim and needs none).

The carried code is **byte-identical** to the founding group's
`src/construct/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `construct` under `src/`, ids sequential per object
type with fixed prefixes, failed operations consume no id and
change nothing, permission checks precede mutation and id
allocation, all timestamps UTC ISO-8601, roles
`admin|operator|viewer` with the founding permission matrix, and
the audit log append-only with denied attempts recorded. The
money discipline is the founding build's, preserved exactly:
**integer cents everywhere — floats and bools are rejected at the
boundary** on contract values, payroll wage totals, and cost
amounts. Derived values are computed at read time in exactly the
founding build's named derivation points — `_contract_expiry_state`,
`_record_overdue` / `_milestone_due_state`, and
`_contractor_compliance` — and are never stored: contract expiry
state, milestone due state, record overdue flags, contractor
compliance status, alerts, and report figures.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 6 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words, under the
taxonomy families that carry control language. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Control areas **documented** by at least one fork in the set:

- **Audit & accountability (AU)** — at **artifact weight only**,
  1 fork: Trimble for Government (FR2701247929), via
  `audit_logging` — "in a compliant, audit-ready cloud
  environment" (Permit Management module). "Audit-ready" is a
  readiness assertion about the environment the offering runs in,
  not an audit-log function of the offering; it is recorded at
  artifact weight in `scratch/ARTIFACTS.md` and documents no
  audit capability beyond the word.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AC, AT, CA, CM,
CP, IA, IR, MA, MP, PE, PL, PM, PS, RA, SA, SC, and SI **as
control claims** — is asserted by no description in the set. Two
points of discipline behind that result, stated explicitly:

- **The set's three `compliance_payroll` claims are not control
  claims.** Specset's UFGS compliance checking is a function the
  offering performs on a *customer's documents*; Trimble's
  "high-compliance … builds" (and its "comply with federal
  security mandates (including CMMC alignment…)" prose — "comply"
  matches no pattern, and no control assertion is made in control
  terms) describe the regulatory setting of the work, not the
  offering's own control posture. Neither is recorded as a CA or
  PM claim.
- **Facility Grid's SOC 2 Type II examination** (cited as the
  basis of a *pursued* FedRAMP 20x certification path) is a
  certification pursuit recorded in the description, not a
  documented control claim; nothing is documented from it.

If the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **Inspection & punch-list records — 0 of 6.** The family the
  category is arguably defined by in this set: Facility Grid is a
  commissioning platform whose recorded work is "installation
  checklists, functional performance tests, issues and
  observations" — inspection and punch-list work in substance.
  Neither "inspection" nor "punch list" occurs in any description
  here, so no claim stands. Carried substrate.
- **Search, reporting & analytics — 0 of 6.** Specset's headline
  "search and question answering across a project's documents"
  earns no claim: the family requires "searching" (or reporting /
  reports / analytics text), and the taxonomy was not re-tuned to
  catch the bare word "search".
- **Workforce records & timekeeping — 0 of 6; job dispatch &
  assignment — 0 of 6; fleet & vehicle telematics — 0 of 6;
  financial & spend tracking — 0 of 6; key-date alerts &
  notifications — 0 of 6; electronic signatures — 0 of 6;
  identity & access control — 0 of 6; safety-incident records —
  0 of 6.** Ten of the taxonomy's 23 families have no claimant in
  this set; nothing was back-filled to make the set look
  complete.
- **Asset management has no family in this taxonomy.** Trimble
  ships an "Asset Management" module and Specset asserts "asset
  management logic"; the category's taxonomy defines no asset
  family, so the function is named as a gap below, not a claim.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
engines named here with this set's claimant counts; the founding
group's standing gaps are restated only where this set's forks
claim them:

- [ ] Construction commissioning engine — equipment/system
  inventories, installation checklists, functional performance
  tests, issues & observations, turnover package assembly
  (Facility Grid; the records the platform keeps are Core, the
  commissioning workflow is the engine)
- [ ] Cost estimating engines and benchmark cost data (Four BT,
  1 claimant; estimate *records* are Core)
- [ ] AI technical document review — submittal review against
  project specifications, UFGS compliance checking, design review
  automation, cited question answering over project documents
  (Specset, 2 claimants)
- [ ] Document control & collaboration platform depth —
  configurability and tracking engines behind the document
  registry (InEight Document)
- [ ] GIS / spatial data platform, field layout & asset location
  tracking (Trimble, 1 claimant)
- [ ] Permitting, licensing, land-use & right-of-way management
  (Trimble)
- [ ] Asset management platform — facility/spatial asset
  registers, condition assessment, lifecycle capital planning
  (Trimble; asset-management logic also asserted by Specset)
- [ ] Workflow / process automation engines (3 claimants;
  lifecycle state machines are the in-core seed)
- [ ] Prevailing-wage determination depth — rate tables,
  fringe-benefit calculation, certified-payroll generation and
  e-filing (standing category gap; in this set the family is
  claimed in name only, by wording artifacts — the gap stands
  regardless)
- [ ] Platform layer: multi-tenancy (2 of 6 claim it in prose;
  the build is a single-tenant reference deployment); encryption
  at rest (deployment layer); TLS only when a certificate is
  configured; demo identities are hooks, not an IdP — IA-2 stays
  with the embedding organization

## Coverage statement (for this build)

6 forks spec'd of 6 in census unit `untiered:Construction`; 27
taxonomy claims tagged from the forks' own descriptions (every
fork claiming at least one; 3 claims at artifact weight, recorded
as such); the seventeen-function substrate carried byte-identical
from the founding Construction L2 build and re-anchored to tier
null; tier null recorded on every sheet and pinned by tests.
Nothing in this build claims a FedRAMP authorization, a CMMC
certification, or a control baseline for any fork or for the
build itself.
