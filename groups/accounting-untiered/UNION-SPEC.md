# Union Spec — Accounting, untiered set (DeadRamp Phase 2, remainder)

The union contract for this **untiered set**: **1 fork**, category
**Accounting**, **tier null**. The member's FedRAMP impact level is
**Unknown** in the source dataset — the source publishes no baseline
for this offering — so no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented control
claims; tier stays null in the registry until the source publishes a
baseline." The Documented control claims section below replaces the
baseline section a tiered group's union spec carries.

Membership is exactly census unit `untiered:Accounting` in
`../../remainder.json` (1 fork ID, verified mechanically). In
`forks.json` the fork is filed under **Accounting** (its source
business categories are Accounting, Finance, and Customer Relations
Management (CRM); the census assigned it to Accounting, its first
business function, and the spec sheet records the assignment). Its
authorization status as recorded is Initial Implementation — a
status is record data, not a claim.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence, the sheet recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`. Sources:
GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product record joined by
FedRAMP ID. The description was present in the cached dataset and
matches `../../remainder/uncovered.json` exactly.

## How functions were counted

The category's fixed 26-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../accounting-l2/scratch/extract.py`, parsed, never executed)
and asserts it is the same 26 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 21 of 21 forks, 123 of 123 claims, deep-equal** against
the sheets at the original ship commit (`789c38c`) — using the
parent's sentence split (carriage returns replaced with spaces
before splitting, the founding group's documented normalization)
and evidence rule (first matching sentence; over 400 characters,
truncated to 397 + '...').

The founding group's eleven recorded wording-artifact corrections
are embodied in the taxonomy patterns themselves (bare "account"
never tags anything; expense requires expense-management phrasing;
bare "Budget" never tags; payroll excludes "labor management";
GovCon/grants is narrowed to GovCon/DCAA/DCMA and federal aid;
"program management" carries the PMO negative lookahead; supply
chain requires warehouse/transportation/inventory *management*
phrasing; "analytics" is matched without a leading word boundary
while bare "analysis" never tags; "asset management", not "asset
manager"; `report\w*` verified safe against the founding 21;
settlement grouped with reconciliation & close). The founding group
records no per-hit removals beyond those pattern-embodied
corrections, and none were invented here. An exclusion pass scanned
every raw hit's evidence sentence for third-party hosted-app
catalogue segments and scope-exclusion sentences: **no hits were
removed** — the description contains no third-party catalogue
segment (its one "third-party providers" mention is a transparency
sentence about documenting them) and no evidence sentence carries
scope-exclusion phrasing (asserted programmatically). Adjudications
and wording artifacts are itemized in `scratch/ARTIFACTS.md`.

A function is claimed for the fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**3 claims** on the set's 1 fork — the fork is **not** a zero-claim
fork. One of the three stands at **artifact weight** (see the
ranking note and `scratch/ARTIFACTS.md`).

Census citations: 2 citations are recorded for this fork in the
census; **2 of 2 verify** as verbatim substrings of the fork's own
description (whitespace-normalized), and **0 of 2** is itself a
claim evidence sentence — both citations are the description's
first two sentences, which fire no family. Verification is not a
claim, in either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — the set's 1 fork

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | Financial reporting & statements | 1 | **Core** — **at artifact weight in this set**: the hit fires on "vulnerability-reporting processes", a security-transparency phrase, not a financial reporting function; it supports no core function (see below) |
| 2 | Audit trail & audit management | 1 | **Core** (the append-only audit trail; audit-*management* workbenches are Extended) — the hit fires on "comprehensive auditability", read at the trail end |
| 3 | Access control & authentication | 1 | **Core** (access-control hooks) — full weight: "strong authentication and access controls" |
| 4 | Core accounting & financial management | 0 | **Core** — **zero claimants in this set; the set's loudest named absence** (the fork's ledger prose fires no family phrase) |
| 5 | APIs, integrations & interoperability | 0 | **Core** (the service is API-first) — zero claimants in this set; named absence |
| 6 | Workflow & approvals | 0 | **Core** (the approval state machine shared by entries, invoices, expenses, with separation of duties) — zero claimants in this set |
| 7 | Reconciliation, settlement & financial close | 0 | **Core** — zero claimants in this set; named absence |
| 8 | Budgeting, planning & cost management | 0 | **Core** (budgets per account per period, budget-vs-actual) — zero claimants in this set |
| 9 | Invoicing & billing | 0 | **Core** — zero claimants in this set |
| 10 | Payment processing, purchase cards & disbursements | 0 | **Core** (recording payments and applying them to invoices; no card networks or payment gateways) — zero claimants in this set; named absence despite the fork's monetization domain |
| 11 | Expense management & travel | 0 | **Core** (expense records with approval; travel *booking* is not included) — zero claimants in this set |
| 12 | AI, analytics & business intelligence | 0 | Extended (the reporting in Core is exact computed statements, not AI/BI analytics) |
| 13 | Risk management & internal controls | 0 | Extended (separation of duties, approval-required posting, and the audit trail in Core are the internal-controls seed; no risk register or GRC module is claimed) — "access controls" alone does not fire this family; named absence |
| 14 | Project, program & portfolio management | 0 | Extended (domain project accounting runs on top of a ledger substrate; this build is that substrate) |
| 15 | Fixed assets, property & fleet management | 0 | Extended (an asset *account* in the chart is not an asset register or depreciation engine) |
| 16 | Records, document management & retention | 0 | Extended (the audit trail in Core is the seed; retention policies are not implemented) — zero claimants despite the fork's immutable-ledger prose; named absence |
| 17 | Forecasting & enterprise performance management (EPM) | 0 | Extended |
| 18 | Supply chain, warehouse & logistics | 0 | Extended (domain operations, outside an accounting core) |
| 19 | Grants, federal aid & GovCon accounting | 0 | Extended (GovCon/DCAA-specific compliance and grants lifecycle are domain layers on the ledger) |
| 20 | Cryptocurrency & blockchain investigation | 0 | Extended (a tail family of the category; not an accounting function) |
| 21 | Time tracking & scheduling | 0 | Extended (labor hours are an input to accounting, not part of this core) |
| 22 | Electronic & digital signatures | 0 | Extended |
| 23 | Payroll & labor | 0 | Extended |
| 24 | Tax reporting & support | 0 | Extended |
| 25 | Encryption | 0 | Platform note (documented control claim in tiered sets where claimed; here the word "encrypt" occurs nowhere — see Documented control claims) |
| 26 | Forensic accounting & financial investigation | 0 | Extended |

**23 of 26 families stand at 0 of 1.** That is the honest shape of
this set: a one-fork untiered set whose single description is
positioning and trust prose around a ledger, not a feature list.
The differences are preserved, not averaged away, and nothing was
back-filled.

## The Core — what this build implements (13 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's thirteen-function substrate **whole** — books &
members; chart of accounts; double-entry journal & ledger posting;
invoicing & billing; payments; expenses; budgets; reconciliation &
period close; financial reporting; workflow & approvals; API
access; access control; audit log. The substrate is the money
machinery every accounting sibling's platform presupposes, and it
is tier-independent code: the founding build's source contains no
tier or baseline machinery, so there was nothing tier-shaped to
strip. **Claim support in this set, stated honestly:** of the
thirteen functions, two are claim-supported by the set's fork under
the standing dispositions — **access control** (by
`access_control`, full weight) and the **audit log** (by `audit`,
read at the trail end of that family). The remaining eleven are
**carried, not claimed**: financial reporting's only family hit is
the artifact-weight `financial_reporting` hit, which documents no
reporting capability and supports nothing; `accounting_core`
itself — the family the journal, chart, and books answer to — has
**no claimant** in this set, because the fork's ledger prose ("a
single immutable financial ledger", "one financial event",
"financial correctness") contains none of the family's phrases
("general ledger", "accounting", "financial management",
"financials", "bookkeeping"); API access likewise has no
`api_integration` claimant ("one programmable platform" carries no
API or integration phrase). Functions are **carried** as substrate;
the claims that support two of them are recorded above, and no
function is claimed to be *attained* by the fork — the build is the
merged open implementation, not the fork's product.

The carried code is **byte-identical** to the founding group's
`src/accounting/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `accounting` under `src/`, ids sequential per object
type with fixed prefixes, failed operations consume no id and
change nothing, all timestamps UTC ISO-8601, roles
`admin|member|viewer` with the founding permission matrix layered
with book membership, separation of duties on approvals, and the
audit log append-only with denied attempts recorded. Where the
founding contract's text says "L2 baseline hooks" for access
control, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline.

**Money representation (a stated choice, carried from the founding
spec):** all monetary values in this build are **integer cents**.
Every amount field is named `*_cents` and must be a Python `int` —
booleans are rejected, and floats are rejected even when integral,
so no binary floating-point value can ever enter a total. All
arithmetic (line amounts, invoice totals, balances, statements) is
integer arithmetic and therefore exact by construction.

One category invariant is preserved exactly, as the founding build
implements it: the debits-equal-credits balance check in
`create_entry` is the ledger's integrity boundary — an unbalanced
entry is rejected whole, stores nothing, and consumes no id — and
it is the subject of this build's mutation-verified negative
control (see `tests/README.md`).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this build
asserts **no FedRAMP baseline, no CMMC tier, and no equivalence**.
What follows is only what the fork's own marketplace description
asserts, in its own words, under the taxonomy families that carry
control language. A documented control claim is a **fork's claim
about itself**, recorded here with its evidence; it is not the
build's control attainment, and nothing in this section fills a
family in from any baseline.

Control areas **documented** by the set's fork:

- **Identification & authentication (IA)** and **Access control
  (AC)** — via `access_control`, **1 fork**: Meterbox
  (FR2633734927) — "strong authentication and access controls", in
  the sentence "Meterbox emphasizes customer data isolation,
  privacy by default, comprehensive auditability, strong
  authentication and access controls, flexible deployment for
  regulated or sovereign environments, and support for privacy and
  data-rights requirements." Both the `authentication` and the
  `access control` alternatives of the family fire on this
  sentence; the claim is recorded at full weight.
- **Audit logging (AU)** — via `audit`, **1 fork**: Meterbox
  (FR2633734927) — "comprehensive auditability", in the same
  sentence. "Auditability" is a property the offering asserts of
  itself; the claim is recorded at the audit-*trail* end of the
  family, and no audit-management capability is documented by it.

Recorded at **prose weight, converted to no family**:

- **Privacy language** — the same sentence's "customer data
  isolation, privacy by default" and "support for privacy and
  data-rights requirements". Privacy is asserted about the offering
  itself, but no Accounting taxonomy family traces privacy
  language, so it converts to no claim and is documented here only
  as the fork's prose assertion.

Control areas **not documented** by the fork: every other NIST SP
800-53 control family — including AT, CA, CM, CP, IR, MA, MP, PE,
PL, PM, PS, RA, SA, SC, and SI **as control claims** — is asserted
by no sentence in the description. Three bounds are worth stating
explicitly:

- **SC is not documented.** The word "encrypt" occurs nowhere in
  the description, despite "data isolation", "privacy by default",
  and "regulated or sovereign environments". No encryption claim is
  recorded.
- **CA is not documented.** The closing sentence's "being built
  toward major enterprise security and compliance standards" is
  future-directed aspiration — the fork says it is building
  *toward* standards while "transparently documenting its current
  certifications" — not a claim of current assessment or
  certification. It is recorded as posture prose, not a control
  claim.
- **The build's own machinery is not a fork claim.** The carried
  substrate's separation of duties, input validation, and
  append-only audit log are the founding build's design (traced to
  baseline families in the *founding* group's spec, at its tier);
  at tier null they are substrate, and nothing about them is
  attributed to this fork.

If the source later publishes an impact level for this offering,
the tier is recorded then and not before.

## Named absences

- **Core accounting & financial management — 0 of 1, the set's
  loudest absence.** The description is built around a ledger —
  "a single immutable financial ledger", "Every customer
  interaction becomes one financial event", "while increasing
  financial correctness" — yet fires nothing: "financial ledger"
  is not "general ledger", and none of "accounting", "financial
  management", "federal financials", "financials", or
  "bookkeeping" occurs. The category's centre is present in
  substance and absent in phrase; the zero is recorded, not
  repaired, and the taxonomy was not re-tuned for it.
- **Payment processing — 0 of 1.** "Fragmented monetization
  infrastructure" is the fork's whole domain, yet no payment
  phrase occurs: no "payment(s)", no "bill pay", no purchase-card
  or disbursement wording.
- **Reconciliation, settlement & financial close — 0 of 1.**
  "Instead of synchronizing systems, we derive different business
  views from one authoritative source" is single-source derivation
  prose; no reconcile / settlement / close phrase occurs.
- **APIs & integrations — 0 of 1.** "One programmable platform"
  asserts programmability, but no `api` token and no
  `integrat\w+` or `interoperab` phrase occurs ("infrastructure"
  does not contain "integrat").
- **Invoicing & billing — 0 of 1.** No invoice or billing wording
  occurs anywhere in the description.
- **Records, document management & retention — 0 of 1.** An
  "immutable" ledger with "customer data isolation" is records
  substance, but no records/document management or retention
  phrase occurs.
- **Risk management & internal controls — 0 of 1.** Sentence 4's
  "access controls" is not "internal controls", and no
  risk-management phrase occurs.
- **Workflow & approvals — 0 of 1.** The description's only
  "processes" is "vulnerability-reporting processes", which is not
  "business process(es)"; no workflow or approval wording occurs.
- **Encryption — 0 of 1** (see Documented control claims): the
  word "encrypt" occurs nowhere.
- **Zero-claim fork: none.** The set's one fork carries 3 claims —
  two at full/trail weight (`access_control`, `audit`) and one at
  artifact weight (`financial_reporting`) — recorded as such, not
  rounded up.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
restated here only where this set's fork claims them:

- [ ] Audit *management* workbenches (audit plans, workpapers,
  findings — the `audit` family's Extended half; 1 claimant, whose
  claim is recorded at the trail end)

No other gap gains a claimant from this set: the fork's remaining
claimed family is Core (`access_control`), and its third hit is the
artifact-weight `financial_reporting` hit, which documents no
reporting capability and registers no reporting gap. The founding
group's extended tail (AI/analytics & BI, project/program/portfolio
management, risk register & GRC beyond the SoD/audit seed,
fixed-asset registers, records retention beyond the audit seed,
forecasting & EPM, supply chain, GovCon/grants specifics, crypto
investigation, time tracking, e-signature, payroll, tax support,
forensic investigation) stands registered under the founding group
and is not re-registered here.

## Coverage statement (for this build)

1 fork spec'd of 1 in census unit `untiered:Accounting`; 3 taxonomy
claims tagged from the fork's own description (2 at full/trail
weight, 1 at artifact weight; the fork is not zero-claim); the
thirteen-function substrate carried byte-identical from the
founding Accounting L2 build and re-anchored to tier null; tier
null recorded on the sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or a
control baseline for the fork or for the build itself.
