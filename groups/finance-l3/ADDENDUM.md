# Addendum — Finance, CMMC L3-adjacent: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:finance-l3`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 11-function
carried core, its core-boundary decision, and its control
baseline are **unchanged**. This document records what joined,
what the newcomer claims under the group's existing taxonomy,
the core-delta decision, and the updated union statement.

**Headline: fork spec'd 1 / 1; 2 new claims — the group's first
claims (total 0 → 2), because the founding fork claims zero and
still does; core delta — zero functions extended, `src/`
byte-identical; tests 249 → 259, all passing.** The newcomer is
a corporate performance management platform whose marketplace
description names its functions in the taxonomy's own vocabulary
for exactly two families: `reporting` (its first-named finance
function) and `hosting_platform` (the taxonomy's platform-note
family, on the verbatim phrase "SaaS offering"). Its headline
function — the CPM engine itself: consolidation, planning,
budgeting, forecasting as computation — has no family in this
taxonomy and is registered as a gap in §5, with the `reporting`
claim covering the reporting slice's records forms only. **3 new
gap functions** are named in §5; no existing gap gains a
claimant; the category's standing named absence (trading &
investment execution) stands at this tier too, token-verified.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1721059275A` | OneStream Software / OneStream Cloud - High |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact (id, label, regex)
  triples** — and, because this group's taxonomy is inherited
  from the parent group, the extractor also parses the taxonomy
  out of `groups/finance-l2/scratch/extract.py` and **asserts
  the two are equal**: the verbatim-inheritance proof, not a
  claim about it. Same sentence splitting, same evidence rule
  (first matching sentence per family), same sheet schema.
- **Corrections:** neither this group's extractor nor Group
  31's carries a programmatic `CORRECTIONS` literal (asserted
  in the extractor). Group 31's five wording-artifact
  corrections are prose-level — a superlative is not a claim;
  outcome prose is not a function; an audience is not a
  function; a phrase naming no implementable function is prose;
  a source category label is not a functional claim — and they
  are applied here as recorded judgment (§2), not as code.
- **Reproduction before tagging:** the extractor first rebuilt
  the original fork's sheet from the raw cache with the
  original construction, and it came out **deep-equal to the
  shipped sheet, claim table included** (empty, as shipped —
  the shipped table is the ground truth and it reproduced
  exactly, "Finance" in the founder's `business_categories`
  remaining a filing label, not a function). Only then was the
  newcomer tagged. The new sheet is **appended** after the
  original, which is byte-for-byte untouched (the re-serialized
  file is byte-preserved through the original sheet's closing
  brace; asserted in the extractor, on top of the parsed
  deep-equality).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. No live
  fetching. The fork is FedRAMP **High / Certified** (SaaS,
  Government Community Cloud) — the group's second High member,
  so the L3-adjacent baseline is inherited in full, unchanged.
- **Category provenance, stated plainly:** forks.json files
  this fork as "Uncategorized (none in source)" and its source
  record carries an **empty** business_categories list. The
  census assigned Finance from the fork's own description, and
  that assignment is what this unit extends; the sheet records
  `deadramp_category: "Finance"` on that basis.
- The census starting point was verified, not trusted: the
  fork's **1 census citation** was re-checked against its own
  cached description and **verifies verbatim (1 / 1)** — with
  the twist recorded in §2: this time the citation *is* a claim
  evidence sentence.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty (asserted in the
  extractor), its description contains no third-party hosted-app
  catalogue and no scope-exclusion segment, and only
  `service_desc` was matched, per house method. Sentences 7–8
  describe the fork's *own* extension marketplace (its own
  described surface, including applications developed by third
  parties for that marketplace); they were matched as the
  fork's own prose and fired nothing, so no exclusion question
  arises. **No raw hit was removed.**

## 2. What the addition claims

**2 claims** under the 8-family taxonomy applied verbatim:

| Family | Evidence (first matching sentence) | Weight |
|---|---|---|
| `reporting` | "OneStream is a Corporate Performance Management (CPM) platform designed to support financial consolidation, reporting, planning, budgeting, and forecasting." | Substantive — the fork's own function enumeration; reporting is a function it performs, named in its defining sentence. The family also fires on sentence 6 ("…enabling streamlined financial reporting and analysis"); the first-match rule books sentence 1. |
| `hosting_platform` | "Delivered as a SaaS offering, the OneStream Government Community Cloud is hosted via Microsoft Azure Government and tailored to meet the needs of federal, state, local, and tribal governments as well as research institutions and government contractors." | Claimed under the verbatim taxonomy on the family's own phrase "SaaS offering" — the same claim shape as DailyPay's at L2 ("delivered as a SaaS offering…"). The taxonomy itself labels this family a **platform note** and the union spec dispositions it at the platform layer; the claim records the delivery form, not a finance function, and it transfers **nothing** of the fork's hosting posture (its cloud runs on another provider's government cloud; no FIPS or authorization posture is inherited — UNION-SPEC's SC-13 gap stands). DailyPay's L2 evidence named both of the family's phrases; this claim rests on "SaaS offering" alone ("multi-tenant" is absent), pinned in the tests. |

The group's claim total goes **0 → 2** (AWS GovCloud 0,
OneStream 2). Six of the eight families stay at 0 of 2.

### Near-misses, itemized per sentence

- **Sentence 1** (the `reporting` evidence) — "budgeting" is
  present in this very sentence, but `spend_management`
  requires the token `\bspend\b`, which occurs **nowhere** in
  the description (count-verified). "Financial consolidation",
  "planning", and "forecasting" name the fork's headline CPM
  functions, for which this taxonomy has no family (§5). The
  bare word "financial" fires nothing: `financial_wellness`
  requires the contiguous phrase "financial wellness".
- **Sentence 2** (the `hosting_platform` evidence) — the
  government list (federal, state, local, tribal, research
  institutions, contractors) is an audience; per Group 31's
  correction 3, an audience is not a function. "Hosted via
  Microsoft Azure Government" is the fork's deployment fact —
  its platform runs on another provider's cloud — recorded
  here, inherited nowhere.
- **Sentence 3** ("fault-tolerant, 64-bit architecture…
  high availability and scalability") — platform properties of
  the fork, not functions; no family, nothing tagged.
- **Sentence 4** (the Windows app "deployed using Microsoft
  ClickOnce Infrastructure or manual installation") — a client
  distribution mechanism; platform layer, no family.
- **Sentence 5** ("integrates with Microsoft Office through an
  Excel add-in, allowing users to interact with data and
  workflows directly within spreadsheets") — integration
  asserted in substance; `api_platform` requires the verbatim
  phrase "open technology platform", which is absent. Booked
  as a gap in §5, not rounded into the family. "Workflows"
  here is the spreadsheet user's, not a workflow family (this
  taxonomy has none; workflow & approvals is a baseline family
  carried at zero claims).
- **Sentence 6** ("data integration from multiple ERP and
  financial systems, enabling streamlined financial reporting
  and analysis") — the second `reporting` hit; the substance
  is booked once (sentence 1 is the evidence). The integration
  substance joins sentence 5's in the §5 gap, booked once.
- **Sentence 7** (the Solution Exchange: "pre-packaged CPM
  solutions") — application extensibility asserted in
  substance; no family covers a marketplace (§5). Not an
  exclusion case: it is the fork's own offering surface.
- **Sentence 8** ("Customers who leverage Solution Exchange to
  install applications developed by OneStream or a third party
  are responsible for determining if the solution meets
  customer requirements…") — customer-responsibility prose, a
  liability allocation, not a function the fork performs.
- **Whole-description absences (count-verified, all zero):**
  no "spend", "booking", or "travel" token; no "earned wages";
  no "financial wellness"; no "multi-tenant"; no "open
  technology platform"; no "real-time" or "streaming" token.

**Named absences — all six stand at this tier.** The functions
UNION-SPEC named as claimed by no fork in this category at
either tier remain unclaimed by the newcomer, token-verified
against its description: banking integration & account
verification (no "bank" token), payroll integration & wage
calculation (no "payroll" token), lending & credit (no "lend"
or "credit" token), **trading & investment execution** (no
"trad", "invest", or "execut" token — "forecasting" is planning
prose, not execution; the L2 addition recorded the same care
for Innovest's wealth management, and the same distinction
applies), tax reporting & remittance (no "tax" token), and GRC
platform functions (no compliance-platform token; the fork's
FedRAMP Certified status is its authorization fact, not a GRC
function).

**The census-citation twist, in the coincidence direction.**
The fork's single census citation verifies as verbatim
description text — and it **is** the `reporting` evidence
sentence, word for word. The census classified the fork by that
sentence, and the claim pass tags the same sentence for the
function it names. Verification is not a claim, in both
directions; here the two coincide, and the coincidence is
recorded rather than assumed (the same shape as Medallia's
second citation in the Customer Service L3-adjacent addition;
the opposite shape from this repo's zero-claim additions, whose
citations verified and tagged nothing).

## 3. Core-delta decision

Both claimed families already carry dispositions in the union
spec's ranking table, and neither disposition moves:
`reporting` is **Core** (Core 7's on-read program summaries and
Core 5's spend-vs-budget are its records forms) and
`hosting_platform` is **platform layer** (a delivery-form note,
not a core function). What changes is the flag, not the build:
at this tier those two families are no longer *carried, not
claimed* for the group — they are **claimed by the addition
fork** (the founding fork's own sheet still claims nothing, and
the core-boundary decision in UNION-SPEC stands verbatim for
it). The other six families keep their union dispositions and
remain carried, not claimed, for both forks. The functions the
newcomer asserts in substance beyond the taxonomy (the CPM
engine, integration, the solution marketplace) are booked as
gaps in §5, not built. **Result: the core is unchanged — delta
zero functions.** The substrate the claimed reporting function
presupposes — period budgets and booking/disbursement records
consolidating into summaries computed on read, in integer
cents — is the substrate the build already is, exercised in
the newcomer's shape by the additions substrate tests.
`src/` is byte-identical to the shipped build (all 7 `finance`
modules SHA-256-verified against the pre-work hashes, both
mutation drills included; `src/finance/store.py` remains
`6ec44f3c1568e5e53c55261e0c9c689b6e2cf2defac65d7e87f41ece658b236f`
and `src/finance/audit.py` remains
`c027a74b04d63f05f6b7dd374ea9450fff445a63d7233a73221d73a29b6c7c55`,
the hashes the shipped tests/README records). The tier baseline
does not change: the group was High 1 and is now High 2.

## 4. Updated union statement

The group now covers **2 forks** (the original singleton + 1
remainder addition), **2 claims** in total (0 → 2), with **1 of
2** forks carrying a claim. The merged build remains the same
11-function finance records substrate — programs & members,
participant registry, earned-wage accrual & access records,
travel booking records, spend budgets, wellness offering
registry, reporting, workflow & approvals, API access, access
control, and the hash-chained fail-closed audit log — carried
at the High baseline under the core-boundary decision, now
spec'd against 2 marketplace offerings instead of 1. The
group's character changes in one stated way: it was the
category tier whose only fork evidenced nothing, and it is now
a tier where the substrate's reporting family and the
platform-note family are evidenced by a member, while six
families remain carried at zero claims and the founding fork's
zero stands exactly as shipped. The claims floor for the
category at L3-adjacent is no longer zero; it is two, and it is
stated rather than padded.

## 5. Gaps — for the registry at ship

**New gap functions** (3), each registered from the fork's
described function:

- **Corporate performance management (CPM) engine** —
  financial consolidation, planning, budgeting, and
  forecasting as computation over financial data (sentence 1,
  the fork's headline function). Registered **with claim
  adjacency**: `reporting` is claimed, and its records forms
  (period summaries on read, spend-vs-budget) are Core; a
  consolidation/planning/forecasting engine — multi-entity
  consolidation, plan and forecast modeling — is not a records
  function and is Extended. Distinct from the Finance L2
  registry's **federal financial management system of record**
  gap (Momentum): that gap is the agency general-ledger system
  carrying the financial lifecycle end to end; the CPM engine
  is the performance-management layer that consolidates and
  plans over financial data. Recorded as distinct, on the L2
  addition's own precedent (its procurement-lifecycle decision),
  so the registry does not conflate the two.
- **Data integration & connector surface** — data integration
  from multiple ERP and financial systems, and the Microsoft
  Office / Excel add-in interaction surface (sentences 5–6),
  asserted in substance in the fork's own words. `api_platform`
  did not fire (its verbatim phrase is absent), so the surface
  is registered from the described function, not from a claim.
  The Core is API-first for its own records; source-system
  connectors and spreadsheet add-ins are not part of it.
- **Solution marketplace & application extensibility** —
  pre-packaged CPM solutions distributed through the fork's
  Solution Exchange, including applications developed by third
  parties for that marketplace (sentences 7–8), asserted in
  substance. No taxonomy family covers a solution marketplace;
  registered from the described surface, not from a claim.

**Existing gaps gaining claimants: none.** The four Extended
functions of the original union (instant disbursement execution
/ payment rails, travel booking execution engines, financial
wellness delivery tools, streaming / real-time reporting
pipelines) gain no claimants from the addition: the claimed
`reporting` is the on-read records form, and the description
carries no real-time or streaming token (contrast Groupize's
L2 evidence, which said "real-time reporting" in so many
words). The singleton's own platform-layer gaps (the cloud
infrastructure platform itself, region operations & sovereignty
properties, root-account eligibility screening, collaborative
continuous monitoring with the provider) are the founding
fork's substance and gain nothing from the newcomer.

**Platform notes for the addition fork** (stated so nothing is
implied): the fork's cloud is hosted via Microsoft Azure
Government — another provider's government cloud is this fork's
deployment fact, and no property of it (authorization posture,
FIPS posture, availability architecture) is inherited by this
build; its fault-tolerant 64-bit architecture and
high-availability properties are platform properties; its
Windows desktop client distribution (ClickOnce / installation
package) is a client-delivery mechanism, not a function of
this build. The baseline gaps at High named in UNION-SPEC
(MFA / authenticator management, FIPS-validated cryptography
SC-13, encryption at rest SC-28, audit retention AU-11,
session lock / termination AC-11/AC-12) are unchanged.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal claim
  tables (the newcomer's 2 claims; the founding fork's empty
  table exactly as shipped), the zero-claim set (the other 6
  families), verbatim evidence with the first-match rule pinned
  (the second `reporting` sentence exists and is *not* the
  evidence), the census citation verifying verbatim and equal
  to the `reporting` evidence, registry fields as published,
  the near-miss pins (budgeting ≠ spend; integration prose ≠
  the `api_platform` phrase; "SaaS offering" alone carries the
  hosting claim), the named-absence token pins, and the group
  totals (2 forks / 2 claims / 1 of 2 claiming) — see
  `tests/test_additions.py`.
- The fork is exercised against the substrate in the same
  file: a period-close flow in the newcomer's shape — two
  employees' accruals (150,000¢ earned), one access disbursed
  (30,000¢) and one pending (10,000¢), a traveler's confirmed
  air booking (45,000¢, over its 40,000¢ budget line) and
  recorded hotel booking (20,000¢), consolidating into
  spend-vs-budget (95,000¢ spent of 100,000¢ budgeted, the air
  line flagged over budget) and the on-read program summary,
  every total asserted to the cent and typed `int`; a
  boundary case rejecting float and boolean amounts whole,
  storing nothing; and an over-cap case rejecting a request
  one cent over the period's earned amount, storing nothing
  and consuming no id. All are carried-substrate cases: the
  newcomer claims `reporting` and the platform note, and the
  addendum claims no other family on its behalf.
- **Tests: 249 → 259, all passing.**
- **Negative controls: BOTH of the group's signature drills
  were re-run in this tree.** Drill 1 (earned cap): the
  comparison in `_check_access_cap` (`src/finance/store.py`)
  was patched out — the body sums the committed and requested
  amounts and returns `True` unconditionally — applied as a
  scoped replacement with the target text asserted to occur
  exactly once, and the full suite ran: **259 tests, exactly
  6 failures** — the shipped drill's 5 plus exactly 1 from the
  new additions module
  (`test_additions.TestOneStreamSubstrate.test_over_cap_request_rejected_whole`),
  tripping exactly as designed. Drill 2 (audit verifier):
  `AuditLog.verify_chain` (`src/finance/audit.py`) was patched
  to return `(True, None)` unconditionally (scoped replacement,
  target asserted to occur exactly once) and the audit test
  files ran: **47 tests, exactly 4 failures** — the identical
  failure set to the shipped drill's record. Both files were
  restored from pre-mutation copies and verified
  SHA-256-identical to the shipped hashes; the full suite
  re-ran green after each restore. Recorded in
  `tests/README.md`, raw lists in
  `scratch/additions_mutation_run.txt` and
  `scratch/additions_mutation_audit_run.txt`.
