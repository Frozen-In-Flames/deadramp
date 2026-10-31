# Union Spec — Human Resources, untiered set (DeadRamp Phase 2, remainder)

The union contract for **Untiered Set 16**: **2 forks**, category
**Human Resources**, **tier null**. Every member's FedRAMP
impact level is **Unknown** in the source dataset — the source
publishes no baseline for these offerings — so no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The
Documented control claims section below replaces the baseline
section a tiered group's union spec carries.

Membership is exactly census unit `untiered:Human Resources` in
`../../remainder.json` (2 fork IDs, verified mechanically). As
filed in `forks.json` the set is mixed: Dayforce is filed
**Analytics** (its source business categories are [Analytics,
Finance, Human Resources]) and Deltek - Replicon is filed
**Uncategorized (none in source)** (business categories []); the
census assigned both to this category from their own
descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded are Initial Implementation
(Dayforce) and FedRAMP In Process (Replicon) — a status is
record data, not a claim.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every
sheet recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`. Sources: GSA FedRAMP Marketplace dataset
(cached at `../../raw/data_dump.json`, produced by the General
Services Administration, last change 2026-10-22), product
records joined by FedRAMP ID. Both descriptions were present in
the cached dataset and match `../../remainder/uncovered.json`
exactly (2/2).

## How functions were counted

The category's fixed 25-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../human-resources-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 25 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 4 of 4 forks, 38 of 38 claims, deep-equal** against
the sheets at the original ship commit (`0a14d91`) — using the
founding sentence split and evidence rule (first matching
sentence; over 400 characters, truncated to 397 + '...'),
including the founding normalization (carriage returns become
spaces before sentence-splitting; neither description in this
set contains a carriage return, asserted in the extractor, so
the normalization changes nothing here).

The founding group's recorded wording-artifact discipline was
applied as recorded judgment, itemized for this set in
`scratch/ARTIFACTS.md`: Dayforce's capability-list sentence is
the first evidence for 3 of its 5 claims (house method;
list-level weight, the founding list-sentence precedent);
Replicon's `ai_automation` claim rests on "automating" with no
AI wording anywhere and stands at **automation weight** (the
founding FedHire precedent); Dayforce's "workforce management"
tags neither performance nor planning family (different phrases,
different functions). An exclusion pass scanned every raw hit's
evidence sentence for third-party catalogue segments and
scope-exclusion phrasing: **no hits were removed** — the raw
pass produced exactly the 6 final claims, no evidence sentence
is a catalogue segment, and Dayforce's authorization-boundary
sentences assert its own assessed scope and negate nothing. The
forks' `certified_services` record fields (non-empty for
Dayforce: Core HR, Payroll, Benefits, Hub, Workforce Management)
were **never matched**: the house method matches `service_desc`
only.

A function is claimed for a fork **only** when its own
description contains matching text; counts are a **floor**, not
a ceiling. **6 claims** across the set; **both forks carry at
least one claim; there is no zero-claim fork**. The descriptions
are uneven (Dayforce 1,961 characters, Replicon 224) and no
conclusion about either real product's full depth should be
drawn from its tag count.

Census citations: 3 citations are recorded for these forks in
the census (2 Dayforce, 1 Replicon); **3 of 3 verify** as
verbatim substrings of the forks' own descriptions, and **1 of
3** is itself a claim evidence sentence (Dayforce's
capability-list citation, the evidence for 3 of its claims).
Verification is not a claim, in either direction: Dayforce's
opening citation tags nothing, and Replicon's citation — its
whole one-sentence description — verifies but is not the stored
evidence, because the house sentence-splitter breaks the
sentence at "Replicon Inc." and the claim stands on the second
fragment, the citation sentence's own second half (recorded in
`scratch/ARTIFACTS.md` item 7). The per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 2 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 2) | Disposition in this build |
|---|---|---:|---|
| 1 | Benefits & retirement administration | 1 (Dayforce) | **Core** — Core 8 benefits & retirement records (claim-supported here); administration platform depth and the calculator Extended |
| 1 | Reporting, dashboards & analytics | 1 (Dayforce) | **Core** — Core 10 reporting over the records (claim-supported here); dashboard/visualization engines Extended |
| 1 | Audit & compliance review | 1 (Dayforce) | **Core** — Core 12 audit log (claim-supported here, on "centralized audit logging"); compliance-review modules Extended |
| 1 | Integrations & external system connections | 1 (Dayforce) | Extended — connector engines |
| 1 | Access control & granted access | 1 (Dayforce) | **Core** — Core 11 RBAC (claim-supported here, on "role-based access control") |
| 1 | AI & workflow automation | 1 (Replicon) | Extended — automation & AI engines; the claim stands at **automation weight only** (no AI wording in the fork) |
| 7 | Talent acquisition | 0 | **Core** context — vacancy/application records (Cores 3–4, carried); acquisition engines Extended |
| 7 | Applicant tracking & application management | 0 | **Core** — Core 4 application records (carried) |
| 7 | Vacancy announcements & job postings | 0 | **Core** — Core 3 vacancy records (carried) |
| 7 | Position classification, descriptions & position management | 0 | **Core** — Core 2 position records (carried) |
| 7 | Job analysis & competency documentation | 0 | Extended — job-analysis & crediting-plan tooling |
| 7 | Hiring assessments & assessment strategies | 0 | **Core** — Core 5 evaluation records (carried); delivery via providers Extended |
| 7 | SME panel review & rating records | 0 | **Core** — Core 5 panel records, human ratings verbatim (carried); scoring computation Extended |
| 7 | Candidate referral & certificates of eligibles | 0 | **Core** — the "referred" application stage, Core 4 (carried); assembled certificate documents Extended |
| 7 | New-hire onboarding & entrance-on-duty | 0 | **Core** — Core 6 lifecycle case records (carried) |
| 7 | Performance management | 0 | **Core** — Core 7 review cycle records (carried); calibration/goal engines Extended. Substance-adjacent wording present ("workforce management", Dayforce) — not the family's phrase |
| 7 | Personnel actions, forms & case management | 0 | **Core** — Core 9 case records (carried) |
| 7 | Separation & offboarding | 0 | **Core** — Core 6 lifecycle cases, separation kind (carried) |
| 7 | Employee & labor relations | 0 | **Core** — Core 9 case kind (carried) |
| 7 | Awards & recognition | 0 | **Core** — Core 9 case kind (carried) |
| 7 | Workforce planning & resource management | 0 | Extended — planning analytics/models. Substance-adjacent wording present ("workforce management"; "resource scheduling", Replicon) — neither is the family's phrase |
| 7 | Talent management & talent lifecycle | 0 | Extended — suite depth beyond records |
| 7 | Internal mobility & talent exchange | 0 | Extended — mobility / workforce-exchange marketplace engines |
| 7 | Career sites, campus recruiting & recruiting events | 0 | Extended — outreach sites, communities & events platforms |
| 7 | Employee learning & upskilling | 0 | Extended — learning delivery |

**The set's character, recorded honestly:** the founding group
was a hiring-and-records group whose center of gravity was the
hiring chain (classification → announcement → application →
assessment → panel → referral → onboarding). **None of that
chain is present here** — all ten chain families stand at 0 of
2. What this set actually contains is a full-suite HCM platform
described mostly in platform-and-security prose (Dayforce: its
HR substance is one capability-list sentence naming human
resources, payroll, workforce management, benefits
administration, document management, employee communications,
analytics, and reporting; the rest of its description is
authorization-boundary and security-control text) and a
single-purpose time-tracking product (Replicon, one sentence).
Four of the five claimed families ride Dayforce's two functional
sentences; the fifth is Replicon's automation wording. The
substrate below is the category's records machinery, carried
whole — most of it presupposed by the category, not by these
two forks — and the unmatched substance (payroll, time &
attendance, expense tracking, document management, employee
communications, the security-operations services) is named
under Gaps and Named absences, not forced into families.

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's twelve-function substrate **whole** — person
records (opaque `person_ref` only); position & classification
records; vacancy announcement records; application records &
stage tracking; evaluation records (rater entries verbatim, no
computed aggregate); lifecycle case records with task checklists
(status **derived at read time, never stored**); performance
review cycle records; benefits & retirement records; personnel
action & case records; reporting over the records; RBAC;
append-only audit log. The substrate is records machinery the
category's siblings presuppose, and it is tier-independent code:
the founding source contains **no tier or baseline machinery at
all** (no tier string occurs anywhere in `src/hr/`), so there
was nothing tier-shaped to strip. Where the founding contract's
text says "L2 baseline" for RBAC and the audit log, read it
here as **baseline-neutral hooks**: at tier null they are
substrate, claimed against no baseline.

Claim support in **this** set, stated per function honestly:
**4 of the 12 functions are claim-supported** — Core 8
(benefits & retirement records: Dayforce's "benefits
administration" capability), Core 10 (reporting: Dayforce's
"analytics, reporting"), Core 11 (RBAC: Dayforce's "role-based
access control" — full substance, where the founding group's
own support was a single thin "granted access" phrase), and
Core 12 (audit log: Dayforce's "centralized audit logging" —
full audit-tooling wording, where the founding group's second
claimant rested on a compliance-outcome phrase). **8 functions
are carried, not claimed** (Cores 1–7 and 9: every hiring-chain
and case family stands at 0 of 2 here); Core 1's anchor status
was already flagged thin in the founding spec itself. `integrations`
(1/2) supports no Core function — connector engines are
Extended; the build's REST surface is its own contract, as in
every group. `ai_automation` (1/2, automation weight) likewise
lands Extended. Functions are **carried** as substrate; no
function is claimed to be *attained* by any fork — the build is
the merged open implementation, not any fork's product.

The carried code is **byte-identical** to the founding group's
`src/hr/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `hr` under `src/`, ids sequential per object type
with fixed prefixes (`per-`, `pos-`, `vac-`, `app-`, `evl-`,
`lif-` with `t-` tasks, `rev-`, `ben-`, `cas-`), failed
operations consume no id and change nothing, all timestamps UTC
ISO-8601, roles `admin|hr_specialist|employee|auditor` with the
founding permission matrix and employee scope by `person_ref`,
lifecycle case status derived at read time via
`_derive_case_status` and never stored (the stored record
carries no status field), evaluation records carrying **no
aggregate, average, or score field anywhere**, person records
keyed by opaque caller-supplied references only with **no field
capable of holding a name, SSN, birth date, pay figure, address,
phone, or email in any record shape** (the founding privacy
discipline, test-enforced by a forbidden-key walk over every
entity type), and the audit log append-only with denied
attempts recorded.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded here with its evidence; it is not the build's control
attainment, and nothing in this section fills a family in from
any baseline.

Control areas **documented** by at least one fork in this set
— all of them by **Dayforce alone** (FR2633957417); Replicon's
description contains no control language in any form:

- **Identification & authentication (IA)** — "identity and
  access management services" among its boundary services, and:
  "The service supports federated identity using
  customer-managed identity providers and implements Digital
  Identity Level 2 (IAL2/AAL2) requirements, including
  multifactor authentication and identity federation, as
  applicable."
- **Access control (AC)** — via the taxonomy's `access_control`
  claim: "role-based access control, privileged access
  management."
- **Audit & accountability (AU)** — via the taxonomy's
  `audit_compliance` claim: "centralized audit logging."
- **Cryptographic protection (SC)** — "FIPS 140-3 validated
  cryptographic modules to protect federal information in
  transit and at rest."
- **Configuration management / continuous monitoring (CM)** —
  "continuous monitoring" in the same security enumeration.
- **Incident response (IR)** — "incident response" in the same
  enumeration.
- **Risk assessment (RA)** — documented in part: "vulnerability
  management" in the same enumeration (vulnerability
  monitoring/scanning language). No risk-assessment prose
  beyond it occurs.

**Recorded but NOT documented:** Dayforce's authorization
prose — its services "have been independently assessed as part
of the FedRAMP Moderate authorization" and the service is
"designed to process, store, and transmit Federal Moderate
impact information, including Controlled Unclassified
Information (CUI), in accordance with FIPS PUB 199 Moderate
security requirements" — is the fork's assertion about itself,
and its own record contradicts the completion it implies
(impact "Unknown", status Initial Implementation). It is
recorded here as an assertion, at that weight; the assessment
family (CA) is **not** credited from it, and the prose moves no
tier (pinned by test).

Control areas **not documented** by any fork in this set:
AT, CA (see above), CP, MA, MP, PE, PL, PM, PS, SA, and SI
**as control claims** — asserted by no description in the set.
If the source later publishes an impact level for any of these
offerings, the tier is recorded then and not before.

## Named absences

- **The hiring chain — 0 of 2 across all ten families.**
  Talent acquisition, applicant tracking, vacancy
  announcements, position classification, job analysis, hiring
  assessments, panel review, referral certificates, onboarding,
  and separation are claimed by neither fork. The category's
  center of gravity in the founding group is simply not what
  these two products describe.
- **Performance management — 0 of 2, substance-adjacent.**
  Dayforce lists "workforce management"; the word "performance"
  occurs nowhere in either description.
- **Workforce planning & resource management — 0 of 2,
  substance-adjacent.** "Workforce management" (Dayforce) is
  not "workforce planning"; "resource scheduling" (Replicon)
  is not "resource management".
- **Personnel actions & case records' family — 0 of 2.** No
  "personnel actions", "case management", or "forms and cases"
  wording occurs; the word "personnel" occurs nowhere.
- **Leave & time-off — 0 of 2 (founding absence; STANDS in
  this set).** Probed with the founding broad pattern: no leave
  wording of any kind in either description. The tiered L2
  retirement of this absence rested on another fork's words
  (GDC's Paycheck 8) and does not transfer here.
- **Policy acknowledgements — 0 of 2 (founding absence;
  STANDS).** No description contains even the substring
  "polic".
- **Background checks — 0 of 2 (founding absence; STANDS).**
- **Salary / compensation administration — 0 of 2 (founding
  absence; STANDS).**
- **Payroll — NOT absent in this set.** Dayforce names payroll
  among its own integrated capabilities (probe fires, 1
  sentence). No taxonomy family exists for payroll, so it is
  named under Gaps — the founding absence does not stand here,
  and nothing was back-filled into the Core for it.
- **Time & attendance — NOT absent in this set.** Replicon's
  description is a time-tracking product statement and the
  founding probe's literal word "timesheet" occurs in it
  (probe fires). No taxonomy family exists for it: Gaps.
- **All remaining families — 0 of 2:** labor relations, awards
  & recognition, talent management, talent mobility,
  recruiting outreach, and learning & upskilling are claimed by
  neither fork, with no vocabulary in the descriptions at all.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not
implemented — restated here where this set's forks claim or
describe them (claimant counts are this set's):

- [ ] Payroll processing engine (Dayforce names payroll among its own capabilities; no taxonomy family exists — **new from this set**; the founding group's payroll absence does not stand here)
- [ ] Time, attendance & leave tracking engine (**already registered** from the tiered additions, where GDC's Paycheck 8 retired both absences; this set adds Replicon's time-and-attendance substance — the probe's literal word and the product's whole function. The leave half gains nothing here: leave remains absent in this set)
- [ ] Expense tracking & management (Replicon substance — "expense management software", "expense tracking" — with no family; **new from this set**)
- [ ] Project time tracking & resource scheduling engines (Replicon substance; the scheduling side of its sentence, distinct from the tracking engine above; **new from this set**)
- [ ] Employee communications & messaging platform (Dayforce substance — "employee communications", "messaging services" — with no family; **new from this set**)
- [ ] Document management services (Dayforce substance — "document management" named twice; distinct from the founding group's document & template *assembly* engines, which generate documents from records; **new from this set**)
- [ ] Identity federation, privileged access management & identity governance services (Dayforce's documented-control side: customer-managed IdP federation, IAL2/AAL2, PAM — the build ships RBAC hooks on demo identities, not an IdP, federation, or PAM service; **new from this set**)
- [ ] Security operations services — continuous monitoring, vulnerability management & incident response engines (Dayforce's documented-control side; the build records an audit log, it operates no monitoring, scanning, or response service; **new from this set**)
- [ ] Federal retirement & benefits administration platform depth (**already registered** from the tiered additions for GRB; Dayforce joins by substance — "benefits administration" as a platform service, beyond Core 8's records)
- [ ] Integration connector engines (1 claimant in this set — Dayforce, on its capability list and boundary services; **already registered** from the founding group)
- [ ] AI & workflow automation engines (1 claimant at automation weight — Replicon; the automation side gains a claimant, no AI is asserted by either fork; **already registered**)
- [ ] Dashboard & visualization engines beyond registry reporting (Dayforce claims reporting at list weight; engines beyond Core 10's counts stand **already registered**)
- [ ] Platform layer (encryption at rest, TLS-when-configured, multi-tenancy — the build performs no cryptography of its own and is a single-tenant reference deployment; demo identities are hooks, not an IdP. Dayforce documents FIPS 140-3 modules for *itself*; the build claims no validated crypto)

## Coverage statement (for this build)

2 forks spec'd of 2 in census unit `untiered:Human Resources`;
6 taxonomy claims tagged from the forks' own descriptions (2 of
2 forks claiming, no zero-claim fork); the twelve-function
substrate carried byte-identical from the founding Human
Resources L2 build and re-anchored to tier null; tier null
recorded on every sheet and pinned by tests. Nothing in this
build claims a FedRAMP authorization, a CMMC certification, or
a control baseline for any fork or for the build itself.
