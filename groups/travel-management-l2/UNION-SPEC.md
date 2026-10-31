# Union spec — Travel Management L2 (singleton, Group 55)

One fork: **GO.gov** (IBM, FR2607452240), SaaS, Government Community
Cloud, FedRAMP Moderate, FedRAMP Certified. This is a new category
with no prior group at any tier, and the final singleton of the
singleton phase.

## Reconciliation

- forks.json carries exactly one entry with category
  "Travel Management" and CMMC tier "L2": this fork. The spec
  sheet's vendor/product match it exactly.
- MAP.md category arithmetic agrees: Travel Management total 2 =
  L2 1 (this fork) + untiered 1 (Cornerstone Information Systems,
  Upstream Gov, impact Unknown, no tier — it belongs to the
  untiered remainder, not to this group). MAP.md's sibling sections
  list only groups of size 2+, so no sibling section exists for
  this category, per the established singleton method.
- Zero diffs. The description was joined from the cached GSA
  dataset by FedRAMP ID; no live fetching. Two cached records carry
  this ID with byte-identical descriptions; one spec sheet stands.

## Taxonomy — definition method

New-category singleton method (the Group 1 method, as Singletons
45/48/50/51 applied it): the taxonomy is defined FROM this fork's
own marketplace description. Families are named from the
description's own functional vocabulary, matched with verbatim
patterns, and every claim stores its source sentence as evidence.
Marketing prose gets no tags; counts are a floor.

The description is three sentences. S1 is a suite list (five
service families in one comma list, plus the System-of-Systems
framing). S2 is a purpose sentence (operations standardization;
security/privacy compliance). S3 is composition prose (the fork
integrates commercial SaaS/PaaS offerings into AWS hosting) and is
claimed only as platform, never double-counted as a service claim.

## Ranking (9 families, 9 claims, one per family)

| # | Family | Claims | Disposition |
|---|--------|--------|-------------|
| 1 | travel_services | 1 | Core (trip/authorization records) + Extended (booking engine) |
| 2 | expense_services | 1 | Core (expense/voucher records) + Extended (payment execution, receipt capture) |
| 3 | integration_services | 1 | Core (integration definition registry) + Extended (connector engines) |
| 4 | notification_services | 1 | Core (notification records) + Extended (delivery transport) |
| 5 | reporting_services | 1 | Core (registry summaries) + Extended (report generation engine) |
| 6 | travel_expense_operations | 1 | Substrate — the records substrate is the standardization surface |
| 7 | security_privacy_compliance | 1 | Platform — assurance purpose; discharged by the baseline section below, not by a product function |
| 8 | system_of_systems_composition | 1 | Platform — the fork's own composition; the third-party offerings it integrates are outside this build |
| 9 | cloud_hosting_platform | 1 | Platform — the fork's hosting; deployment property of any build |

Checked absences (itemized in scratch/ARTIFACTS.md): no booking or
reservation vocabulary, no per-diem vocabulary, no reimbursement
vocabulary, no approval vocabulary, no receipt vocabulary anywhere
in the description. None of those functions is claimed.

## Core-boundary decisions

1. **Records, not travel.** The claimed services presuppose records
   of trips, expenses, and payments. Core builds that records
   substrate. Travel itself — searching, booking, ticketing,
   travelling — is not performed by anything in the build.
2. **Authorizations and approvals are a records form, stated as a
   decision.** The description contains no approval vocabulary.
   Federal travel under the compliance purpose S2 states runs on
   authorizations, so trip authorization records and decision
   records are in Core as the records form the travel claim
   presupposes. The separation-of-duties seam (the decider is never
   the requester) is the substrate's control, not a claimed product
   feature.
3. **Vouchers are records; no money moves.** Expense services
   presuppose a payment-side record. Voucher records are in Core;
   disbursement execution is Extended. The build holds no funds and
   pays no one.
4. **Money is integer cents.** Fares, authorized amounts, expense
   amounts, and voucher amounts are integer cents; floats, booleans,
   and strings are rejected at the boundary.
5. **Derived, never stored.** A trip's phase
   (upcoming / in_progress / completed) is derived at read from its
   dates; an expense report's total, reimbursed sum, and remaining
   balance are derived at read from its items and vouchers. Stored
   records carry none of those keys. Lifecycle status
   (draft / submitted / approved / declined) is event-driven — it
   changes only through recorded actions — so it is stored. The
   distinction is stated in the store docstring.
6. **Traveler privacy.** Traveler records carry an opaque
   caller-supplied reference and a label only; the shape is pinned
   by test so no field can hold a name-bearing identifier beyond the
   label, a document number, or any real personal data. Itineraries
   in Core are destination labels and dates, nothing more.
7. **No scores.** Summaries are counts and money sums computed on
   read. Nothing in the build computes a score, rating, or risk
   value, and no record shape has a field for one (pinned by a
   recursive key scan in the tests).

## The core (13 functions)

1. Organization registry & membership (agencies; boundary for all
   org-scoped records)
2. Traveler registry (opaque references, pinned shape)
3. Trip authorization records (destination label, dates, purpose,
   authorized amount in cents; event-driven lifecycle)
4. Authorization decision records (approve/decline; decider never
   the requester)
5. Expense report records (against an approved authorization;
   event-driven lifecycle)
6. Expense line item records (category, amount in cents, date,
   note; addable only while the report is a draft)
7. Expense decision records (decider never the report's creator)
8. Voucher records (against an approved report; signature
   invariant below)
9. Notification records (recorded, never delivered)
10. Integration definition registry (definitions as data; the
    registry never executes — no execute path exists)
11. Search & summary reporting (substring search; per-organization
    counts and money sums; no scores)
12. REST API (every function above over JSON HTTP)
13. RBAC + append-only audit (role matrix plus organization
    membership; every mutation and every denied attempt recorded)

**Signature invariant — the voucher cap.** The cumulative vouchers
recorded against an expense report never exceed the report's total
(the sum of its line items). Enforced at the store seam
`_check_voucher_cap` before anything is stored; a rejected voucher
consumes no id and changes nothing. A second cap stands at report
submission: the cumulative totals of submitted and approved reports
against an authorization never exceed its authorized amount
(`_check_authorization_cap`). The negative control is
mutation-verified against the voucher cap (see tests/README.md).

## Long tail (Extended — named for GAPS.md, not built)

- Travel booking & reservation engine
- Carrier, hotel & GDS reservation integrations
- Payment & disbursement execution (vouchers are records)
- Receipt capture & imaging / OCR
- Integration connector engines (the registry holds definitions)
- Notification delivery transport
- Report generation engine & dashboards (beyond registry summaries)
- Identity provider / identity management service

Platform-layer: the commercial SaaS/PaaS offerings the fork
integrates are its own components, outside this build; hosting
(AWS GovCloud (US) and commercial regions for the fork) is a
deployment property; encryption at rest (deployment layer; TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP (IA-2 stays with the
embedding organization).

## Baseline — FedRAMP Moderate ⇔ CMMC L2

Tier: FedRAMP Moderate ⇔ NIST SP 800-53 Rev. 5 Moderate /
SP 800-171, CMMC L2. Standing caveat: **FedRAMP authorizes
products; CMMC certifies organizations.** The tier is a planning
and matching equivalence for this map, never a credential claim.

Feature → control-family traceability:

| Core feature | Families |
|---|---|
| RBAC role matrix + org membership | AC-2, AC-3, AC-6 |
| Decider-never-requester on authorizations and reports | AC-5 |
| Append-only audit, denied attempts recorded | AU-2, AU-3, AU-6, AU-9 |
| Traveler records: opaque refs, pinned shapes, no PII fields | AC-3, SI-12 (minimization by shape) |
| Integer-cents money boundary, validate-before-store | SI-10 |
| Integration registry records definitions, never executes | CM-7, AC-3 |
| Notification records without delivery | AU-2 (event records) |
| TLS when configured | SC-8, SC-13 (no validated module claimed) |
| Demo identities as hooks, IdP external | IA-2 (stays with the embedding organization) |

## Coverage statement

Forks spec'd: 1/1. Claims: 9 (five service families, one operations
family, three platform families). Core implemented: 13/13. The
build is Python standard library only.
