# Union Spec — Finance, untiered set (DeadRamp Phase 2, remainder)

The union contract for this **untiered set**: **1 fork**, category
**Finance**, **tier null**. The member's FedRAMP impact level is
**Unknown** in the source dataset — the source publishes no baseline
for this offering — so no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented control
claims; tier stays null in the registry until the source publishes a
baseline." The Documented control claims section below replaces the
baseline section a tiered group's union spec carries.

Membership is exactly census unit `untiered:Finance` in
`../../remainder.json` (1 fork ID, verified mechanically). The
census proposed category Finance, agreeing with the category the
source itself files the fork under (`forks.json` category Finance;
the fork's source business categories are Finance and Travel
Management). Its authorization status as recorded is Initial
Implementation — a status is record data, not a claim.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence, the sheet recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`. Sources:
GSA FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID. The description
was present in the cached dataset and matches
`../../remainder/uncovered.json` exactly.

## How functions were counted

The category's fixed 8-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../finance-l2/scratch/extract.py`, parsed, never executed)
and asserts it is the same 8 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 2 of 2 forks, 8 of 8 claims, deep-equal** against the
sheets at the original ship commit (`a929b5b`) — using the
parent's sentence split (split on sentence punctuation or newlines)
and evidence rule (first matching sentence, stored verbatim; the
founding Finance extractor applies no truncation and no
carriage-return normalization, and neither founding description
contains a carriage return, asserted in the extractor). The
remainder additions' 4 sheets are not part of the proof: their one
claim's evidence was re-anchored by a recorded human adjudication
in the parent group (Coupa's `spend_management` evidence moved from
the product-name sentence to the functional sentence), so the plain
rule does not reproduce that one evidence string, by the parent's
own record.

The founding group's five recorded wording-artifact corrections
are applied as recorded judgment (a category name inside a
superlative earns no tag; outcome/marketing prose earns no tag; an
audience sentence earns no tag; "traveler experience" earns no
tag; a source category label is not a functional claim). None of
the five situations changes a count here — this description's third
sentence *is* an audience sentence and fires no family in any case.
An exclusion pass scanned the raw hit's evidence sentence for
third-party hosted-app catalogue segments and scope-exclusion
sentences: **no hits were removed** — the description is three
first-party sentences with no catalogue segment and no
scope-exclusion phrasing (asserted programmatically). Adjudications
and wording artifacts are itemized in `scratch/ARTIFACTS.md`.

A function is claimed for the fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**1 claim** on the set's 1 fork — the fork is **not** a zero-claim
fork. The one claim stands at **artifact weight** (see the ranking
note and `scratch/ARTIFACTS.md`).

Census citations: 1 citation is recorded for this fork in the
census; **1 of 1 verifies** as a verbatim substring of the fork's
own description, and **1 of 1** is itself a claim evidence sentence
— the citation *is* the description's first sentence, which carries
the set's one claim. Verification is not a claim, in either
direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — the set's 1 fork

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | Reporting & analytics | 1 | **Core** (program summaries computed on read from records) — **at artifact weight in this set**: the hit fires on "employee expense reporting", the expense-report filing workflow, not on reporting/analytics phrasing; it supports no core function (see below) |
| 2 | Earned wage access (on-demand pay) | 0 | **Core** (accrual, access-request, and disbursement *records* under the earned-cap invariant) — zero claimants in this set |
| 3 | Financial wellness solutions | 0 | **Core** (offering registry + enrollment records) — zero claimants in this set |
| 4 | Travel booking (air & hotel) | 0 | **Core** (booking *records* with lifecycle) — zero claimants in this set |
| 5 | Group & meeting travel management | 0 | **Core** (the program/traveler/booking substrate) — zero claimants in this set; named absence despite the fork's travel-and-expense-policy prose and its Travel Management filing |
| 6 | Spend management | 0 | **Core** (budgets per program per period, spend-vs-budget computed from records) — zero claimants in this set; **the set's loudest named absence** (the fork's whole domain is expenses, yet the word "spend" never occurs) |
| 7 | Open platform & APIs | 0 | **Core** (the service is API-first) — zero claimants in this set |
| 8 | SaaS / cloud delivery (platform note) | 0 | Platform note — zero claimants in this set ("cloud-based SaaS solution" is not the family's "SaaS offering" / "multi-tenant" phrasing; the fork's SaaS delivery is record data, not a claim) |

Baseline families carried at **zero claims in the founding group**
stand at zero claims here too, in the Core as substrate, not
because the description claims them: access control &
authentication, workflow & approvals (the shared state machine with
separation of duties), and the audit trail.

**7 of 8 families stand at 0 of 1, and the eighth stands at artifact
weight.** That is the honest shape of this set: a one-fork untiered
set whose single description names an expense-workflow product in a
taxonomy built from earned-wage and group-travel descriptions. The
differences are preserved, not averaged away, and nothing was
back-filled.

## The Core — what this build implements (11 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's eleven-function substrate **whole** — programs &
members; participant & traveler registry; earned-wage accrual &
access records; travel booking records; spend budgets & tracking;
financial wellness offering registry; reporting; workflow &
approvals; API access; access control; audit log. The substrate is
the finance records machinery both founding siblings' platforms
presuppose, and it is carried from the **L2 founding build** as-is:
the Finance L3 singleton's High uplifts (hash-chained audit,
fail-closed writes, restricted auditor, logon lockout) are **not**
inherited here — nothing is uplifted into a set whose tier is null.
**Claim support in this set, stated honestly:** of the eleven
functions, **none is claim-supported at full weight**. The set's
only family hit is `reporting` at artifact weight — it fires on the
expense-report filing phrase, documents no reporting or analytics
capability, and supports nothing. The remaining ten functions have
no claimant at all in this set: the fork's described function —
expense reporting, approval, and reimbursement workflows — is named
by **no family** in the category taxonomy (whose two half-domains
are earned-wage finance and group-travel finance), so the substrate
that would hold its records is carried, not claimed. Functions are
**carried** as substrate; no function is claimed to be *attained*
by the fork — the build is the merged open implementation, not the
fork's product.

The carried code is **byte-identical** to the founding group's
`src/finance/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `finance` under `src/`, ids sequential per object
type with fixed prefixes, failed operations consume no id and
change nothing, all timestamps UTC ISO-8601, roles
`admin|member|viewer` with the founding permission matrix layered
with program membership, separation of duties on access decisions,
and the audit log append-only with denied attempts recorded. Where
the founding contract's text ties its hooks to the L2 baseline,
read it here as **baseline-neutral hooks**: at tier null they are
substrate, claimed against no baseline.

**Money representation (a stated choice, carried from the founding
spec):** all monetary values in this build are **integer cents**.
Every amount field is named `*_cents` and must be a Python `int` —
booleans are rejected, and floats are rejected even when integral,
so no binary floating-point value can ever enter a total. All
arithmetic is integer arithmetic and therefore exact by
construction. Payments, transfers, and disbursements are
*recorded*, never executed against real rails; booking records
likewise record reservations made elsewhere. People are known to
the build exclusively by caller-supplied opaque references; no
entity shape has a field that could hold a real name, bank account
number, card number, or government identifier, and the record
shapes are pinned by tests.

One category invariant is preserved exactly, as the founding build
implements it: the **earned-cap invariant** — pending plus approved
plus disbursed access amounts for a (participant, period) never
exceed that period's earned amount, enforced in
`_check_access_cap` at request time — is the earned-wage records'
integrity boundary, and it is the subject of this build's
mutation-verified negative control (see `tests/README.md`).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this build
asserts **no FedRAMP baseline, no CMMC tier, and no equivalence**.
What follows is only what the fork's own marketplace description
asserts, in its own words. A documented control claim is a **fork's
claim about itself**, recorded here with its evidence; it is not
the build's control attainment, and nothing in this section fills a
family in from any baseline.

Control areas **documented** by the set's fork: **none.** No
sentence in the description asserts a NIST SP 800-53 control family
at claim weight, and none at the taxonomy tier (the taxonomy is
functional by founding design).

Recorded at **prose weight, converted to no family**:

- **"Authorized users"** — sentence 2: the solution "is designed to
  enable authorized users to submit, review, approve, and
  administer business expenses". This names a user population, not
  a mechanism: no access-control, authentication, SSO, MFA,
  federation, or role language occurs anywhere in the description.
  Recorded as the fork's prose framing; **AC and IA are not
  documented by it** (the posture of the Talent Development
  untiered set's mechanism-free privacy sentence).
- **Customer-policy framing** — sentence 2's "in accordance with
  applicable organizational travel and expense policies" states
  that the customer's own business policies frame the workflow. It
  is the product's functional context, not a control claim about
  the offering.

Control areas **not documented** by the fork: every NIST SP 800-53
control family — AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL,
PM, PS, RA, SA, SC, and SI **as control claims** — is asserted by no
sentence in the description. Two bounds are worth stating
explicitly:

- **SC is not documented.** The word "encrypt" occurs nowhere in
  the description (pinned by test), despite "cloud-based SaaS
  solution". No encryption claim is recorded.
- **The build's own machinery is not a fork claim.** The carried
  substrate's separation of duties, input validation, earned-cap
  enforcement, and append-only audit log are the founding build's
  design (traced to baseline families in the *founding* group's
  spec, at its tier); at tier null they are substrate, and nothing
  about them is attributed to this fork.

If the source later publishes an impact level for this offering,
the tier is recorded then and not before.

## Named absences

- **Spend management — 0 of 1, the set's loudest absence.** The
  fork's whole domain is spend in substance — "employee expense
  reporting, approval, and reimbursement workflows", "business
  expenses" — yet the word "spend" occurs nowhere in the
  description. "Expense" does not contain it (e-x-p-e-n-s-e), and
  the family's `\bspend\b` pattern correctly never fires. Pinned by
  test; the zero is recorded, not repaired, and the taxonomy was
  not re-tuned for it.
- **Group & meeting travel management — 0 of 1.** Sentence 2 names
  "organizational travel and expense policies", and the source
  files the fork under Travel Management among its business
  categories — but neither "travel management" nor "travel for
  meetings" occurs. A policy the workflows run under is not travel
  management, and a source category label is not a claim (founding
  correction 5).
- **SaaS / cloud delivery — 0 of 1.** Sentence 1's "cloud-based
  SaaS solution" and the record's SaaS service model are delivery
  facts; the family's phrases ("SaaS offering", "multi-tenant")
  occur nowhere.
- **Travel booking — 0 of 1.** No "booking" token occurs anywhere
  in the description.
- **Earned wage access, financial wellness, open platform & APIs —
  0 of 1 each.** Neither half-domain of the founding taxonomy is
  this fork's business, and no API or platform phrase occurs.
- **Expense management itself has no family.** The fork's entire
  described function — expense reporting, approval, and
  reimbursement workflows under travel and expense policies — is
  named by no family in the category's 8-family taxonomy. It is
  registered below as a gap in its own name, not approximated into
  `spend_management` or `reporting`.
- **Zero-claim fork: none.** The set's one fork carries 1 claim —
  at artifact weight (`reporting`) — recorded as such, not rounded
  up.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
the two that arise from this set's fork:

- [ ] Expense reporting, approval & reimbursement workflow engine
  (the fork's described function entire: expense records running a
  submit → review → approve → administer workflow with
  reimbursement recording; named in no taxonomy family, registered
  in its own name)
- [ ] Travel & expense policy enforcement engine (the policy rules
  the workflows run "in accordance with" — sentence 2's framing;
  the build's records presuppose policy outcomes, no policy rules
  are represented)

No other gap gains a claimant from this set: the fork's only
claimed family is `reporting`, at artifact weight, which documents
no reporting capability and registers no reporting gap. The
founding group's extended tail (instant disbursement execution /
payment rails, travel booking execution engines, financial wellness
delivery tools, streaming / real-time reporting pipelines) stands
registered under the founding group and is not re-registered here.

## Coverage statement (for this build)

1 fork spec'd of 1 in census unit `untiered:Finance`; 1 taxonomy
claim tagged from the fork's own description (at artifact weight;
the fork is not zero-claim); the eleven-function substrate carried
byte-identical from the founding Finance L2 build (the L3
singleton's High uplifts not inherited) and re-anchored to tier
null; tier null recorded on the sheet and pinned by tests. Nothing
in this build claims a FedRAMP authorization, a CMMC certification,
or a control baseline for the fork or for the build itself.
