# Union Spec — Travel Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Travel Management:
**1 fork**, **tier null**. The member's FedRAMP impact level is
**Unknown** in the source dataset — the source publishes no
baseline for this offering — so no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries. This is Untiered Set 28, the last untiered
set.

Membership is exactly census unit `untiered:Travel Management`
in `../../remainder.json` (1 fork ID, verified mechanically):
**FR2632558740 — Cornerstone Information Systems / Upstream Gov**,
SaaS, Government Community Cloud, authorization status Initial
Implementation — a status is record data, not a claim. The fork
is filed "Travel Management" in `forks.json` with source
business categories [Travel Management, Accounting, Analytics];
the census proposal agrees with the filed category, so no
reclassification is involved, and the sheet records the filing as
found.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry with the offering's full public marketplace description
and its function claims tagged from that description, recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`. Source:
GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined
by FedRAMP ID. Two cached records carry this ID; their
`service_desc` values are byte-identical (asserted), so one spec
sheet stands — the same duplicate-record shape the founding
fork's own record has. The description matches
`../../remainder/uncovered.json` exactly.

## How functions were counted

The category's fixed 9-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../travel-management-l2/scratch/extract.py`, parsed, never
executed), asserts its 9 (id, label, regex, disposition) tuples,
and asserts the founding extractor carries no CORRECTIONS
literal (its wording-artifact corrections are prose in the
founding `scratch/ARTIFACTS.md`, applied here as recorded
judgment: only `service_desc` is matched; category labels and
product names earn no tags; composition and hosting prose is
platform, never double-counted as a service claim).

Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — both sheets, deep-equal** against git HEAD of the
founding `specs/specs.json`: GO.gov (FR2607452240), **9 of 9
claims**, evidence sentences included; and the founding group's
remainder-addition fork mLINQS (F1610037949), **0 of 0**. The
founding sentence split (whitespace-collapse, then split only on
sentence-final punctuation followed by whitespace and a capital
letter) and evidence rule (first matching sentence, verbatim)
were used throughout.

Exclusion pass: the fork's `certified_services` is **empty** in
both cached records (asserted), so no third-party
hosted-application catalogue is attached to the listing and the
excluded-catalogue precedent does not arise. The description is
a single first-party sentence with no scope-exclusion phrasing.
**Raw hits: 0 across all 9 families; removals: 0** — there was
nothing to remove.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not
a ceiling. Result: **0 claims** — a **zero-claim fork**, recorded
under Named absences, not hidden. The same taxonomy gave the
founding group's addition fork zero on a 1,200-character
description; this fork's entire description is one 76-character
sentence, and its zero is the taxonomy's answer to its words.

Census citations: the census records **1 citation** for this
fork — the description sentence itself. It **verifies verbatim
(1/1)** and serves as claim evidence for **nothing (0/1)**,
there being no claims. Verification is not a claim, in either
direction; and census classification is not a claim either —
the census assigned this fork to Travel Management from this
same sentence, and the taxonomy's answer to it is still zero.
The per-citation record is `scratch/citation_check.json`.

## Function ranking — the set's 1 member

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | Travel services | 0 | Core (trip/authorization records) + Extended (booking engine) — **zero claimants in this set; named absence** |
| 2 | Expense services | 0 | Core (expense/voucher records) + Extended (payment execution, receipt capture) — **zero claimants; named absence** |
| 3 | Integration services | 0 | Core (integration definition registry) + Extended (connector engines) — **zero claimants; named absence** |
| 4 | Notification services | 0 | Core (notification records) + Extended (delivery transport) — **zero claimants; named absence** |
| 5 | Reporting services | 0 | Core (registry summaries) + Extended (report generation engine) — **zero claimants; named absence** (reporting substance present in other words — see Named absences) |
| 6 | Travel and expense operations | 0 | Substrate — **zero claimants; named absence** |
| 7 | Security and privacy compliance | 0 | Platform (assurance purpose) — **zero claimants; named absence** |
| 8 | System of Systems composition | 0 | Platform — **zero claimants; named absence** |
| 9 | Cloud hosting platform | 0 | Platform — **zero claimants; named absence** |

## The Core — what this build implements (13 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's thirteen-function substrate **whole** —
organization registry & membership; traveler registry;
trip authorization records; authorization decision records;
expense report records; expense line item records; expense
decision records; voucher records; notification records;
integration definition registry; search & summary reporting;
REST API; RBAC + append-only audit. The substrate is records
machinery that the category's claimed surfaces presuppose, and
it is tier-independent code: the founding build's source
contains no tier or baseline machinery of its own (its baseline
lives in its union spec's traceability section, which this set
does not inherit), so there was nothing tier-shaped to strip.
The founding build's seven core-boundary decisions are carried
as the substrate's design, unchanged: records, not travel;
authorizations and approvals as a records form under
separation of duties (the decider is never the requester);
vouchers as records with no money moving; **money as integer
cents**, floats, booleans, and strings rejected at the boundary;
derived-never-stored phase and totals (lifecycle status is
event-driven and stored; the distinction stands as the founding
store states it); traveler privacy by pinned shape (opaque
caller-supplied references only); and **no scores** — summaries
are counts and money sums, and no record shape has a field for
a score (pinned by a recursive key scan in the carried tests).

**Claim support, stated honestly:** in this set, **none of the
thirteen functions is claim-supported** — the set's only fork
claims no family. The functions are **carried**, not claimed,
exactly as the founding group's substrate functions stood for
its own zero-claim addition fork. One proximity is recorded so
it is not mistaken for support: the fork's described function —
aggregation of travel data to support comprehensive reporting
and analysis — is in substance closest to Core function 11
(search & summary reporting), whose records the aggregation
would feed and whose summaries are the reporting surface. But
`reporting_services` does not fire on this fork's words, so
function 11 stands here as carried substrate, **not** as a
claim-supported function, and the aggregation engine itself is
an Extended gap (below). No function is claimed to be
*attained* by the fork — the build is the merged open
implementation, not the fork's product.

The carried code is **byte-identical** to the founding group's
`src/travel/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is
the founding spec's contract, unchanged: Python 3, standard
library only, package `travel` under `src/`, ids sequential per
object type with fixed prefixes, failed operations consume no
id and change nothing, all timestamps UTC ISO-8601, roles
`admin|member|viewer` with the founding permission matrix plus
organization membership, and the audit log append-only with
denied attempts recorded. Where the founding contract's text
rests a core function on the Moderate baseline's control
families, read it here as **baseline-neutral substrate**: at
tier null the hooks are carried, claimed against no baseline.
The substrate's signature invariant stands exactly as founded:
**the voucher cap** — cumulative vouchers recorded against an
expense report never exceed the report's total, enforced at the
store seam `_check_voucher_cap` before anything is stored (a
second cap stands at report submission against the
authorization's authorized amount).

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts — and here the answer is:
**nothing**. A documented control claim is a fork's claim about
itself; this fork's one-sentence description contains **no
control language of any family** (token-verified: "security",
"privacy", "compliance", "access control", "audit", "encrypt",
"authentication", "single sign-on", "sso", "multi-factor",
"mfa", "role-based" — none occurs; recorded in
`scratch/absence_check.json` and pinned in the spec tests).

Control areas **documented** by this set: **none**.

Control areas **not documented**: every NIST SP 800-53 control
family — AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PM,
PS, RA, SA, SC, SI — is asserted by no sentence in the fork's
description, and nothing is filled in from any baseline. The
record's deployment model, "Government Community Cloud", is
record metadata outside the description — platform metadata,
not a control claim. If the source later publishes an impact
level for this offering, the tier is recorded then and not
before.

## Named absences

- **All 9 taxonomy families — 0 of 1.** The taxonomy was defined
  from the founding fork's suite-list vocabulary; this fork's
  sentence speaks none of it. The zero is recorded, not
  repaired; the taxonomy was not re-tuned for it.
- **The founding build's five checked absences, re-probed on
  this fork's own words — all five SURVIVE** (token lists from
  the founding `scratch/ARTIFACTS.md`; full record in
  `scratch/absence_check.json`, pinned by tests). An absence
  retires only on a fork's own words, never by transfer:
  - **Booking / reservation — survives.** No "book", "reserv",
    "itinerary", "flight", "airline", "hotel", "lodging", or
    "rental" token.
  - **Per-diem — survives.** No "per diem", "allowance", or
    "rate table" token.
  - **Reimbursement — survives.** No "reimburs", "voucher", or
    "disburs" token.
  - **Approval — survives.** No "approv" or "authoriz" token
    (the wider of the founding and addition stems probed).
  - **Receipt — survives.** No "receipt", "scan", or "ocr"
    token.
- **Reporting substance without the phrase.** "Comprehensive
  reporting and analysis" is present; the family's phrase
  "reporting services" is not. Recorded as a near-miss in
  `scratch/ARTIFACTS.md`, not repaired into a claim.
- **Zero-claim fork:** FR2632558740, Cornerstone Information
  Systems / Upstream Gov — its entire description is the single
  sentence "Aggregation of travel data to support comprehensive
  reporting and analysis.", and no family fires. Travel
  Management is now zero-claim at every remainder step in this
  repo: the founding group's addition fork and this untiered
  fork both stand at zero, with all claims in the category
  carried by the founding fork alone.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented:

**New gap, from this set:**

- [ ] **Travel data aggregation & analytics engine** (Upstream
  Gov) — the fork's described function entire, registered in
  its own name from its description, not from a claim:
  collecting travel data from source systems, aggregating it,
  and the comprehensive reporting and analysis the aggregation
  supports ("Aggregation of travel data to support
  comprehensive reporting and analysis."). No taxonomy family
  names aggregation, and no registered gap names it: the
  substrate's search & summary reporting is counts and sums
  over its own records, not multi-source aggregation, and the
  report-generation gap below is generation of reports, not
  the aggregation pipeline that feeds them.

**Already registered, gaining substance in this set (noted, not
re-registered):**

- **Report generation engine & dashboards** (founding group) —
  this fork's reporting substance ("comprehensive reporting
  and analysis") is the closest any remainder fork comes to
  it, but claimant accounting is by claims and there are
  none, so it gains **no claimant** here; the substance is
  recorded in `scratch/ARTIFACTS.md`.

**Founding tail, standing as registered under the founding
group (zero claimants in this set):** travel booking &
reservation engine; carrier, hotel & GDS reservation
integrations; payment & disbursement execution; receipt
capture & imaging / OCR; integration connector engines;
notification delivery transport; identity provider / identity
management service; the founding group's two addition gaps
(employee relocation management & processing engine; relocation
policy & entitlement rules automation) — none gains a claimant
from this fork, whose words contain no token of any of them.

**Platform layer:** the fork's Government Community Cloud
hosting is its own deployment property; the build is a
single-tenant reference deployment; encryption at rest is a
deployment-layer property (TLS only when a certificate is
configured); demo identities are hooks, not an IdP — IA-2
stays with the embedding organization.

## Coverage statement (for this build)

1 fork spec'd of 1 in census unit `untiered:Travel Management`;
0 taxonomy claims tagged from the fork's own description (the
fork is zero-claim, recorded plainly); the thirteen-function
substrate carried byte-identical from the founding Travel
Management L2 build and re-anchored to tier null; tier null
recorded on the sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or
a control baseline for the fork or for the build itself. With
this set, every Travel Management fork in the registry is
spec'd: the founding fork at L2 (9 claims), its addition fork
(0), and this untiered fork (0).
