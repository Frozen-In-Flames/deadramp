# Addendum — Travel Management, CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:travel-management-l2`** (see `../../REMAINDER.md`).
The original union spec stands as written: its taxonomy, its
13-function core, its Moderate control baseline, and its seven
core-boundary decisions are **unchanged**. This document records
what joined, what the newcomer claims under the group's existing
taxonomy (nothing), the core-delta decision, and the updated
union statement.

**Headline: fork spec'd 1 / 1; 0 new claims — a zero-claim fork;
core delta — zero functions extended, `src/` byte-identical;
tests 96 → 110, all passing.** The newcomer is an employee
relocation platform: its entire listing is eight sentences
about processing employee moves and automating federal
relocation policy. The group's taxonomy was defined from
GO.gov's own suite-list vocabulary, and none of its nine
verbatim patterns appears in the newcomer's text — the raw hit
count is 0 across all 9 families. The singleton's five checked
absences were re-searched against the newcomer and **all five
survive** (§2): the relocation fork carries no booking,
per-diem, reimbursement, approval, or receipt vocabulary
either. **2 new gap functions** are named in §5, registered
from the fork's described function rather than from any claim;
no existing gap gains a claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `F1610037949` | mLINQS / mLINQS Hosting Service |

Census membership was verified against `remainder.json` before
building (unit `addition:travel-management-l2`, `fork_ids ==
["F1610037949"]`, `extends_group == "travel-management-l2"`).
The fork is filed **Uncategorized** in the source (`forks.json`
category "Uncategorized (none in source)", source business
categories `[]`); Travel Management is the census proposal,
recorded on the sheet as such.

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast`** (parsed, never executed,
  never re-typed) and asserts its 9 (id, label, regex,
  disposition) tuples. Before tagging the newcomer, the
  extractor **reproduces the original fork's shipped claim
  table exactly** from the cached description — GO.gov: all 9
  claims, evidence sentences included, deep-equal — and
  asserts the shipped sheet deep-equal to git HEAD. The new
  sheet is **appended** to `specs/specs.json`; the original
  sheet is byte-preserved through its closing brace (asserted
  in the extractor; the resulting diff is a pure insertion).
- The original extractor carries no CORRECTIONS literal
  (asserted in the extractor); its wording-artifact
  corrections are prose in `scratch/ARTIFACTS.md` and were
  applied by the same reasoning: only `service_desc` is
  matched; category labels and product names earn no tags;
  composition and hosting prose is platform, never
  double-counted as a service claim.
- Exclusion discipline, checked not assumed: the newcomer's
  `certified_services` is empty in both cached records
  (asserted), so no third-party hosted-application catalogue
  is attached to the listing and the excluded-catalogue
  precedent does not arise. The text names only the fork's own
  product (moveLINQ) and its own components. The matched text
  is the full text and **nothing was removed** — the raw hit
  count is zero, so there was nothing to remove.
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. Two
  cached records carry this ID; their `service_desc` values
  are byte-identical (asserted), so one spec sheet stands —
  the same duplicate-record shape the original fork's own
  record has. No live fetching. The fork is FedRAMP
  **Moderate** / Certified, SaaS, **Government Community
  Cloud**, so the group stays single-tier and the Moderate
  baseline is inherited in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: the
  fork's **2 census citations** were re-checked against its
  own cached description and **both verify verbatim** — they
  are the description's second and fourth sentences. Neither
  tags a family (see §2): verification ≠ claim, and census
  classification ≠ claim either, in both directions.

## 2. What the addition claims

**0 claims.** The newcomer's entire marketplace description is
eight sentences (roughly 1,200 characters) about employee
relocation. Under the taxonomy applied verbatim it produces
**0 raw hits across all 9 families** — every sentence's hit
list is empty (`scratch/additions_sentence_map.json`) — so
there is nothing for the wording-artifact corrections to
correct and nothing was manufactured.

Group claim counts after the addition (2 forks): the total
stays **9** — every family at exactly 1, claimed by GO.gov;
the newcomer claims none of the 9.

### Near-misses, itemized

The description's phrases, one by one:

- **"process thousands of employee moves annually"**
  (sentence 1) and **"manage employee relocation"**
  (sentence 2) assert relocation processing and management in
  substance. No family covers relocation: the taxonomy's
  service families are GO.gov's suite-list items
  (`travel_services` requires "suite of travel"), and no
  relocation phrase appears in any pattern. Substance without
  the phrase earns no tag; the substance is registered as a
  new gap in §5.
- **"will be in full compliance"** (sentence 3) is compliance
  assurance in substance, but `security_privacy_compliance`
  requires the phrase "compliance with federal security and
  privacy regulations". The newcomer names no regulation set
  in that sentence. No tag; the compliance purpose is in any
  case discharged by the baseline, per the original family's
  platform disposition.
- **"automates FTR, JTR, DSSR, and 6FAM CONUS/OCONUS
  relocation policy"** (sentence 4) asserts a policy rules
  engine in substance. No family covers policy automation;
  `travel_expense_operations` requires "streamline and
  standardize federal travel and expense operations", which
  does not appear. The substance is registered as a new gap
  in §5.
- **"adheres to E-Gov Travel, GSA/OMB reporting, and Section
  508 standards"** (sentence 4) is standards-adherence prose.
  `reporting_services` requires the phrase "reporting
  services" (the suite-list item); adherence to reporting
  *standards* is conformance asserted about the fork's own
  posture, not a reporting function. No tag, and the report
  generation gap gains no claimant (§5).
- **"on a hosted platform"** (sentence 5), **"this Software
  as a Service (SaaS) model"** (sentence 6), and **"hosting
  multiple federal agencies"** (sentence 8) are hosting
  substance, but `cloud_hosting_platform` requires the phrase
  "secure hosting environments". No tag. Hosting is the
  fork's own deployment property regardless — it transfers
  nothing to the build.
- **"focus their budgets on business objectives"**
  (sentence 7) is outcome prose about agency managers; no
  budget or expense token of any family appears ("budgets"
  here is a noun in a rhetorical sentence, not an expense
  function). No tag.

### Wording artifacts

None. Zero raw hits means no claim stands on an artifact, and
no artifact had to be pinned at reduced weight.

### The singleton's checked absences, rechecked

The union spec's checked absences were findings about the
original fork's description, with token lists recorded in
`scratch/ARTIFACTS.md`. Re-searched against the newcomer's
text (token-verified in the additions tests):

- **Booking / reservation — survives.** No "book", "reserv",
  "itinerary", "flight", "airline", "hotel", "lodging", or
  "rental" token appears. A retirement would have to rest on
  the fork's own words; the words are absent. The booking
  engine and carrier/hotel integration gaps stand as
  registered, and Core holds trip records only — now for both
  forks.
- **Per-diem — survives.** No "per diem", "allowance", or
  "rate table" token. The newcomer automates relocation
  *policy* (FTR/JTR/DSSR/6FAM) without naming any per-diem
  computation; no per-diem function is claimed or built for
  the enlarged group.
- **Reimbursement — survives.** No "reimburs", "voucher", or
  "disburs" token. Voucher records remain in Core only under
  the original core-boundary decision 3 (the payment-side
  records form expense services presuppose); the newcomer
  changes nothing about that decision, and no money moves.
- **Approval — survives.** No "approv" or "authoriz" token.
  Authorization and decision records remain in Core only
  under core-boundary decision 2; the newcomer's listing adds
  no approval vocabulary of its own.
- **Receipt — survives.** No "receipt", "scan", or "OCR"
  token. Receipt capture remains a gap for the enlarged
  group.

## 3. Core-delta decisions

The newcomer claims no family, so no family's disposition
changes. The per-family state for the enlarged group, for the
record (dispositions per UNION-SPEC's ranking; every family is
claimed by 1 of 2 forks — GO.gov — and by 0 for the newcomer):

| Family | Disposition (UNION-SPEC) | Core delta |
|---|---|---|
| Travel services | Core (trip/authorization records) + Extended (booking engine) | **Carried** |
| Expense services | Core (expense/voucher records) + Extended (payment execution, receipt capture) | **Carried** |
| Integration services | Core (integration definition registry) + Extended (connector engines) | **Carried** |
| Notification services | Core (notification records) + Extended (delivery transport) | **Carried** |
| Reporting services | Core (registry summaries) + Extended (report generation engine) | **Carried** |
| Travel and expense operations | Substrate | **Carried** |
| Security and privacy compliance | Platform | **Carried** |
| System of Systems composition | Platform | **Carried** |
| Cloud hosting platform | Platform | **Carried** |

**Result: the core is unchanged.** A zero-claim fork
presupposes no records form the substrate lacks: an employee
move, as a records matter, is the same shape as a trip — an
opaque traveler reference, an authorization with an integer-
cents cap decided under separation of duties, expense items,
and vouchers capped at the report total — and the additions
substrate cases run exactly that flow. What the fork adds in
substance (relocation processing, a relocation policy rules
engine) is engine work, registered as gaps in §5, not records.
The singleton's seven core-boundary decisions stand verbatim —
records not travel, authorizations as a records form, vouchers
as records with no money moving, **integer cents** throughout,
derived-never-stored phase and totals, traveler privacy by
pinned shape, no scores. `src/` is byte-identical to the
shipped build (all 7 `travel` modules SHA-256-verified against
the pre-work baseline, `scratch/additions_src_hashes_before.txt`;
`store.py` remains
`a4098ea612bbffa7fed89323e39752c79f28e08ce1e343f3ece92d5517da61ce`,
the shipped hash, the mutation drill included; the final
`git diff` on `src/` is empty, pyc churn restored).

## 4. Updated union statement

The group now covers **2 forks**, **9 claims** in total, with
**1 of 2** forks carrying claims. The merged build remains the
same 13-function travel records substrate — organization
registry & membership, traveler registry of pinned six-key
opaque records, trip authorization records with derived phase,
decision records under separation of duties, expense report
and line-item records with derived totals, voucher records
under the signature cap, notification records that are never
delivered, a never-executing integration definition registry,
search & counts-and-sums reporting with no scores, REST API,
RBAC with organization membership, append-only audit — at the
Moderate baseline, now spec'd against 2 marketplace offerings
instead of 1. The group's character is confirmed from a second
direction: the original fork is a System-of-Systems travel and
expense suite whose listing enumerates the taxonomy's phrases
itself, while the newcomer is a single-purpose relocation
platform whose listing speaks an adjacent vocabulary the
taxonomy does not reach. The records substrate both presuppose
is the same; only one of the two listings says so in the
taxonomy's phrases. Travel Management's other registry member
(Upstream Gov, untiered) belongs to the untiered remainder and
is not part of this group.

## 5. Gaps — for the registry at ship

**New gap functions** (2) — registered from the fork's
described function, **not** from a claim:

- **Employee relocation management & processing engine**
  (mLINQS / mLINQS Hosting Service) — processing employee
  relocations end to end: "process thousands of employee
  moves annually" (sentence 1), "manage employee relocation"
  (sentence 2), "every relocation processed using moveLINQ"
  (sentence 3). A relocation is a lifecycle distinct from a
  trip — household-goods movement, entitlement counseling,
  relocation allowances under FTR/JTR — and no registered gap
  names it: the booking gap is reservation mechanics, and the
  substrate's authorization/expense/voucher records are the
  records form a move presupposes, not the processing engine
  that runs one.
- **Relocation policy & entitlement rules automation**
  (mLINQS / mLINQS Hosting Service) — the rules engine the
  fork names in its own words: "The software automates FTR,
  JTR, DSSR, and 6FAM CONUS/OCONUS relocation policy"
  (sentence 4). Automated application of the federal
  relocation regulation corpus to individual moves. Distinct
  from per-diem computation (which survives as an absence —
  no per-diem token appears, and no rate calculation is
  described); this gap is the policy-application engine the
  description does assert.

**Existing gaps gaining a claimant: none.**

- **Travel booking & reservation engine; carrier, hotel & GDS
  reservation integrations** — gain **no** claimant: the
  booking absence survives token-verified (§2).
- **Payment & disbursement execution** — gains **no**
  claimant: the newcomer "processes" moves, an operational
  verb, and names no payment, disbursement, or reimbursement
  function; no money token appears.
- **Receipt capture & imaging / OCR** — gains **no**
  claimant: the receipt absence survives token-verified.
- **Report generation engine & dashboards** — gains **no**
  claimant: "adheres to … GSA/OMB reporting … standards"
  (sentence 4) asserts conformance to reporting standards,
  not report generation; adherence prose is not a reporting
  function (see §2).
- **Integration connector engines; notification delivery
  transport; identity provider / identity management
  service** — all gain no claimant: the newcomer's text
  contains no token of any of them.

**Platform notes for the addition fork** (stated so nothing is
implied): the fork's hosted SaaS composition, its Government
Community Cloud deployment, its multi-agency hosting
efficiencies, and its Section 508 / E-Gov Travel standards
adherence are its own platform and posture properties — none
is inherited by this build, and none changes the build's IA-2
or SC-13 posture.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit
  order, membership against `remainder.json`, the original
  fork's claim table standing exactly (9 claims in taxonomy
  order), the literal zero-claim table and the whole-taxonomy
  zero-claim set for the newcomer, tier fields, the description
  verbatim against the cached source (both duplicate records),
  census citation accounting, the no-exclusion-trap pin, the
  checked-absence rechecks at the token level, and the
  near-miss pins (see `tests/test_additions.py`).
- The addition fork is exercised against the substrate in the
  same tests: a relocation-shaped flow (traveler record,
  relocation authorization decided by a non-requester, expense
  report with a draft-state derived total, vouchers to exactly
  the report total and one cent over rejected whole), and the
  traveler record's pinned six-key shape with a relocation
  authorization's phase derived at read (upcoming /
  in_progress / completed).
- **Tests: 96 → 110, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree. Drill (voucher
  cap): the cap condition in `TravelStore._check_voucher_cap`
  in `src/travel/store.py` (`if already + amount_cents >
  total:`) patched to `if False:` (scoped patch; the target
  line occurs exactly once, count asserted) — **110 tests,
  exactly 6 failures**: the shipped drill's 5 plus exactly 1
  from the additions module
  (`test_additions.TestAdditionSubstrateCases.test_mlinqs_relocation_expense_flow_and_voucher_cap`),
  tripping as designed. `store.py` was restored from
  `scratch/store.py.premutation-additions` and verified
  SHA-256-identical to the shipped hash (`a4098ea6…`); the
  suite re-ran green. Recorded in `tests/README.md`; raw
  output in `scratch/additions_mutation_run.txt`.
