# Addendum — Finance, CMMC L2: the 4 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 4
previously uncategorized forks of remainder build unit
**`addition:finance-l2`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 11-function core,
and its control baseline are **unchanged**. This document records
what joined, what the newcomers claim under the group's existing
taxonomy, the core-delta decision for every claimed function, and
the updated union statement.

**Headline: forks spec'd 4 / 4; 1 new claim; core delta — zero
functions extended, `src/` byte-identical; tests 202 → 213, all
passing; 6 new gap functions** are named in §5. Three of the four
newcomers claim **zero families** under the taxonomy applied
verbatim — the taxonomy's 8 families are the two original
siblings' specific functions, and the newcomers are enterprise
financial platforms of other kinds. Their claims, near-misses,
and own surface are recorded in full below, not rounded up.

## 1. Membership and method

The 4 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1603157879` | Apptio an IBM company / Apptio for Technology Business Management and Cloud Financial Management (TBM) |
| 2 | `FR2022243058` | CGI Federal / Momentum Enterprise Suite |
| 3 | `F1308202329` | Coupa Software Inc / Coupa Spend Management for Federal |
| 4 | `FR1821933307` | Innovest Systems, LLC / Trust & Wealth Management Solutions |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the TAXONOMY literal out of the shipped
  `scratch/extract.py` with `ast`** (parsed, never executed), so
  the (function_id, label, regex) triples are the original's by
  construction — the taxonomy was applied verbatim, not re-tuned
  for the newcomers. Same sentence splitting, same evidence rule
  (first matching sentence per family, stored verbatim), same
  sheet schema. The 4 sheets are **appended** to
  `specs/specs.json` after the original 2, which are byte-for-byte
  untouched (pure-insertion diff, +78 lines, 0 deletions; the
  original entries verified deep-equal to git HEAD after the
  append, in `scratch/append_additions.py`).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 4
  descriptions were present; no live fetching. All 4 are FedRAMP
  **Moderate**, so the group stays single-tier and the L2
  baseline is inherited in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **5
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **5 / 5 verify** as verbatim
  substrings. Verification is not a claim: 4 of the 5 citations
  tag no family (both zero-claim forks' citations among them),
  stated plainly in §2.
- **No exclusion trap applies to the newcomers.** None of the 4
  records carries a hosted-services block: every record's
  `certified_services` field is empty (asserted in the build).
  Only `service_desc` was matched, per house method.

## 2. What the additions claim

**1 claim** across the 4 forks; 1 of 4 carries a claim. Claim
counts per family among the additions, with the group's combined
count (original 2 + additions = 6 forks) alongside:

| Function | Additions claiming | Group total (6) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Spend management | 1 | 2 | **Core** — budgets & spend-vs-budget |
| Earned wage access (on-demand pay) | 0 | 1 | **Core** — accrual/access/disbursement records |
| Financial wellness solutions | 0 | 1 | **Core** — offering registry & enrollments |
| Travel booking (air & hotel) | 0 | 1 | **Core** — booking records |
| Group & meeting travel management | 0 | 1 | **Core** — program/traveler/booking substrate |
| Reporting & analytics | 0 | 1 | **Core** — summaries computed on read |
| Open platform & APIs | 0 | 1 | **Core** — the service is API-first |
| SaaS / cloud delivery (platform note) | 0 | 1 | Platform note |

Per-fork claim counts: Coupa **1**, Apptio **0**, CGI Momentum
**0**, Innovest **0**. The full per-fork table is pinned literally
in `tests/test_additions.py` (`EXPECTED_CLAIMS`).

### Zero-claim forks — pinned, not hidden

Three additions carry **zero claims**, for a structural reason:
the group's taxonomy is a fixed 8 families defined from the two
original siblings' descriptions (earned wage access, financial
wellness, travel booking/management, spend, reporting, an "open
technology platform" phrase, a "SaaS offering" phrase). The
newcomers are a technology-cost platform, a federal financial
ERP, and a trust-accounting platform; their functional sentences
match none of the 8 patterns, and the taxonomy was not re-tuned
to catch them. Their substance is itemized below and their own
engines are named as gaps in §5.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Apptio** — The census citation sentence ("market leading
  SaaS provider of Technology Business Management (TBM) and
  cloud financial management solutions…") verifies verbatim and
  tags nothing: "cloud financial management" is not
  `financial_wellness` ("financial wellness" required), and
  "SaaS provider" is not `hosting_platform`'s "SaaS offering"
  (no "multi-tenant" either). "Allocate cloud costs back to the
  agency" and "Price and recover shared services" are cost-
  allocation / chargeback substance with no family to land in;
  "Optimize cloud costs across AWS, Azure and GCP" is cost-
  optimization substance. The description contains no "spend",
  "reporting", or "booking" token at all (0 hits on all 11
  sentences, machine-checked).
- **CGI Momentum** — Its one functional sentence ("built to
  support the full federal financial, budget, asset and
  procurement management lifecycles") is budget/financial
  substance, but `\bspend\b` never fires — the description
  contains no "spend" token ("maximize taxpayer dollars" is the
  closest approach) — and there is no general financial-
  management family for it to land in. "Web-based system" is not
  `hosting_platform` phrasing: the offering is SaaS in the
  registry, but its description never says "SaaS offering" or
  "multi-tenant", and claims follow the description.
- **Coupa** — "spend analytics" is analytics substance but not
  `reporting` (no "reporting" token anywhere in the
  description); it is named as an engine gap in §5. "Full
  auditability for FAR/DFARS processes" is audit substance —
  this taxonomy has no audit family (audit is a baseline hook
  in this group, carried at zero claims) — and its CAS /
  FAR-DFARS compliance prose claims no GRC platform function
  (the UNION-SPEC named-absence for GRC platform functions
  stands). "maximize the value of each dollar spent" is not
  `\bspend\b` ("spent" is a different word). The AI/ML/Image
  Recognition sentence matches no family; the document-
  processing engine is a gap in §5.
- **Innovest** — The sharpest near-miss in the unit: its single
  sentence is "offered in a multi-currency Software as a
  Service (SaaS) environment", and `hosting_platform` requires
  "SaaS offering" or "multi-tenant" — "offered" is not
  "offering", and the sentence says "multi-**currency**", not
  "multi-tenant". The platform note does not fire. "Trust
  accounting and wealth management" matches no family; see §5
  for its gap and for why the UNION-SPEC's trading named-
  absence still stands.

### Wording artifacts in claims that stand

- **Coupa, `spend_management`** — the extractor's first-match
  rule lands on the offering's title sentence ("Coupa Spend
  Management for Federal is a cloud and mobile platform…"),
  where the hit is the product name itself. Per the name-only
  precedent (UiPath in the Operations Management L2 addition),
  the claim is **re-anchored** to the functional sentence —
  "It covers the end-to-end process, including supplier
  identification, sourcing, contracting, procurement against
  contracts, invoicing, payments, and spend analytics to ensure
  compliance and efficiency." — which is the evidence stored in
  the spec sheet. The re-anchor is performed and asserted in
  `scratch/append_additions.py` (the replacement must be a
  verbatim sentence of the description and must itself match
  the family pattern), and pinned by test. The claim itself is
  sound either way: spend management is the product's stated
  function, and its records side is Core 5.

## 3. Core-delta decisions

The one claimed family already has a disposition in UNION-SPEC,
and its records form already exists in the build:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Spend management (1) | Core 5 — spend budgets & tracking: budgets per program per period, spend-vs-budget computed from records | **Carried** — no change. Coupa's claim presupposes exactly the budget/spend records Core 5 holds; its excess (procurement lifecycle execution, spend analytics) is Extended — §5 |

No other family gains a claimant, so no other disposition is
revisited. The zero-claim forks presuppose no records form the
build lacks either: the records their surfaces reduce to
(budgets, allocations-by-category, summaries, opaque-reference
participants with pinned shapes) are Core 1/2/5/7, exercised for
each fork in `tests/test_additions.py`.

**Result: the core is unchanged.** `src/` is byte-identical to
the shipped build (`src/finance/store.py` SHA-256
`f905061dbe5d45ae3ef64333a1a62a1f05af8fadbf0e5d01608cd6ad643f7c9e`
before and after this addendum's work, the mutation drill
included — the same hash as the shipped build's recorded
premutation hash). The tier baseline does not change: same tier
by construction. The money discipline is untouched and is
re-pinned against addition-era records in the additions tests:
integer cents only, floats and booleans rejected whole at the
boundary, and the earned-cap invariant enforced (see §6).

## 4. Updated union statement

The group now covers **6 forks** (2 original siblings + 4
remainder additions), **9 claims** in total (8 + 1), with **3 of
6** forks carrying at least one claim. The merged build remains
the same 11-function finance records substrate — programs &
members, opaque-reference participants, earned-wage accrual &
access records under the earned cap, booking records, spend
budgets & tracking, the wellness offering registry, on-read
reporting, the approval workflow, API, access control, audit —
now spec'd against 6 marketplace offerings instead of 2. The
union's character widens: alongside the original two half-
domains (earned-wage finance, group-travel finance) sit
enterprise and federal financial platforms (TBM/FinOps, a
federal financial ERP, spend/procurement, trust accounting)
whose descriptive surface is almost entirely Extended engines
over the same substrate. Only Coupa's spend claim lands in the
Core; the rest of the newcomers' weight is registered honestly
as gap surface in §5 rather than absorbed into claims the
taxonomy does not support.

## 5. Gaps — for the registry at ship

**New gap functions** (6), each named from the fork's own
described surface:

- **Federal financial management system of record** — the
  general-ledger system carrying the financial, budget, asset,
  and procurement management lifecycles end to end (Momentum).
  Core 5 holds budget records and computes spend-vs-budget; it
  is not an agency's financial system of record.
- **Procurement lifecycle engine** — supplier identification,
  sourcing, contracting, procurement against contracts,
  invoicing, and supplier payment execution (Coupa). Its
  payments are recorded inside this gap rather than enlarging
  the earned-wage *payment rails* gap: a different flow
  (supplier disbursement against invoices, not access to earned
  wages), decided here so the registry does not conflate them.
- **Spend analytics engine** — analytics over spend data
  (Coupa). Core 7 computes summaries on read from records; an
  analytics engine is not a registry function.
- **Technology business management & cloud cost management
  engine** — cost allocation and chargeback ("allocate cloud
  costs back to the agency", "price and recover shared
  services"), cloud cost optimization across providers, FinOps
  enablement (Apptio).
- **Trust accounting & wealth management platform** —
  multi-currency trust accounting system of record and wealth
  management tooling (Innovest).
- **AI/ML document processing** — image recognition and
  automation of manual, paper-based processes (Coupa).

**Existing gaps gaining claimants:** none. The four Extended
functions of the original union (instant disbursement execution
/ payment rails, travel booking execution engines, financial
wellness delivery tools, streaming reporting pipelines) gain no
claimants from the additions — no newcomer claims earned wage
access, travel booking, financial wellness, or real-time
reporting.

**Named-absence status:** the six functions UNION-SPEC named as
claimed by **neither** original sibling (banking integration &
account verification, payroll integration & wage calculation,
lending & credit, trading & investment execution, tax reporting
& remittance, GRC platform functions) remain unclaimed by the
newcomers as well, with one nuance recorded: Innovest asserts
*wealth management*, which is not the *trading & investment
execution* the absence names — no newcomer sentence claims
trading or execution — so the absence stands and wealth
management is registered as its own gap above. Coupa's CAS /
FAR-DFARS compliance prose likewise claims no GRC platform
function.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the literal
  per-fork claim table (including the three zero-claim forks),
  verbatim evidence, descriptions equal to the cached
  marketplace text, the 5 census citations, the Coupa
  re-anchor, and the near-miss pins (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in
  the same tests: Coupa's spend claim riding Core 5 budgets
  (booking spend computed against a budget line); Apptio's
  allocation shape as unbudgeted-spend computation on read;
  Momentum's surface as a Core 7 summary computed exactly from
  wage records; Innovest's as the pinned participant key set
  plus float/boolean rejection at the money boundary.
- **Tests: 202 → 213, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `_check_access_cap`
  in `src/finance/store.py` was patched to compute the
  committed-plus-requested sum into a local and return `True`
  unconditionally — never comparing against the period's earned
  amount, the exact live counterpart of the mutant in
  `test_negative_control.py` — and the full suite ran: **213
  tests, 6 failures**: the shipped drill's 5 (both
  negative-control canonical cases, both earned-wage over-cap
  rejections, the over-cap-request-over-HTTP case) plus 1 from
  the new additions module (`test_additions_earned_cap_still_
  enforced`), which trips on the mutant exactly as designed.
  `store.py` was restored from the pre-mutation copy and
  verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw output in
  `scratch/additions_mutation_run.txt`.
