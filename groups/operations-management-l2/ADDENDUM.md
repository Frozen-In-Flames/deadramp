# Addendum — Operations Management, CMMC L2 (DeadRamp Phase 2 remainder, unit `addition:operations-management-l2`)

The union spec for the enlarged group. The shipped UNION-SPEC.md
stands as written for the original two forks; this addendum records
what joined, what the newcomers claim under the group's taxonomy,
what changed in the union (and what deliberately did not), and the
new gaps. Read together: UNION-SPEC.md + this addendum = the spec
of record for all 22 forks.

## 1. What joined

20 previously uncategorized forks, assigned to Operations
Management by the remainder census (`REMAINDER.md` /
`remainder.json`, build unit `addition:operations-management-l2`)
from their own marketplace descriptions, each with the evidencing
sentences stored as census citations. All 20 are **FedRAMP
Moderate**, so they join at this group's tier by construction and
the baseline does not change: the union baseline remains the
tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, with the standing
caveat from `crosswalk.md` (this mapping is planning/matching
only; the build is not a FedRAMP authorization and confers no CMMC
certification).

| Fork ID | Vendor / Product |
|---|---|
| F1404043549 | Accenture Federal Services / Accenture Federal Cloud ERP |
| AGENCYHUDSAAS | AINS dba OPEXUS / AINS dba OPEXUS - eCase |
| FR1918442180 | Bizagi Corp. / Bizagi Cloud for US Government |
| FR1923039219 | Canon U.S.A., Inc. / Canon Office Cloud – Managed Print Services |
| FR2324454026 | FM:Systems / OpenBlue Workplace |
| FR1728053006 | IBM / IBM Automation Services for Government |
| FR1816364586 | Ivanti / Ivanti Neurons for ITSM (Formerly Service Manager) |
| FR1927682057 | M.C. Dean, Inc. / InfraLink |
| FR2129953050 | Manhattan Associates, Inc. / Manhattan Government Cloud |
| F1506256801 | MSM Group, Inc. / iSite Contract Management Portal |
| FR2102577114 | Pitney Bowes / SendPro 360 |
| F1608097919 | PTC / PTC Cloud Services |
| FR1733061545 | R&K Solutions, Inc / GoRPM |
| FR1730866868 | Smartsheet / Smartsheet Gov |
| FR2000945223 | Software AG Government Solutions / ARIS Government Cloud |
| FR1722532017 | stackArmor / Clarity |
| FR2130949241 | StackArmor / Rally |
| FR2108649352 | Tyler Federal, LLC / Tyler Federal Product Suite |
| FR2132958724 | UiPath / Automation Cloud Public Sector |
| FR1730334049 | Xerox Corporation / Xerox Managed Print Services for US Government |

Their sheets are appended to `specs/specs.json` (entries 3–22).
The two shipped sheets are preserved byte-for-byte: the file's
text up to the second sheet's closing brace is identical to the
shipped file, asserted programmatically at build time
(`scratch/finalize_additions.py`). One schema note: the shipped
sheets took `deadramp_category` from `forks.json`, which lists
these 20 as "Uncategorized (none in source)"; their appended
sheets record the census-assigned category, "Operations
Management", which is the category they join.

## 2. How the additions were spec'd

The group's **existing 19-family taxonomy was applied verbatim**
(ids, labels, and regexes byte-identical to `scratch/extract.py`;
see `scratch/extract_additions.py`). It was not re-tuned for the
newcomers. Census citations and taxonomy claims are different
instruments: a fork joins the group on its census citation (all
**28 citations verified** as verbatim substrings of the cached
descriptions), and it claims only the families the taxonomy
holds, with the first function-asserting sentence stored as
evidence (every stored evidence sentence likewise verified as a
verbatim substring).

The mechanical pass produced 10 raw claims; the shipped group's
own scoping discipline (a claim stands only when the matched text
asserts a customer-facing function of the offering) removed 3 and
re-anchored 2 evidence sentences — every call, plus a per-fork
near-miss itemization, is recorded in
`scratch/ADDITIONS_ARTIFACTS.md`. Final result: **7 claims over 6
forks; 14 forks claim zero families.** The zero-claim forks are
not defective sheets: the taxonomy was defined from two
descriptions and phrases its families narrowly ("asset and
equipment management", "usage information", "program
operations"), and most newcomers assert their substance one word
away from those phrases — asset management without "and
equipment" (5 forks), metering without "usage information"
(Canon, Xerox, Pitney Bowes), workflows without "automated"
(InfraLink, eCase, Tyler). Those near-misses are itemized, not
rounded up.

Per-fork claims:

| Fork | Claims |
|---|---|
| Bizagi Cloud for US Government | workflow_automation |
| FM:Systems OpenBlue Workplace | workflow_automation |
| IBM Automation Services for Government | workflow_automation, integrations |
| Ivanti Neurons for ITSM | workflow_automation |
| UiPath Automation Cloud Public Sector | workflow_automation |
| Xerox Managed Print Services | workflow_automation |
| The other 14 additions | — (zero families) |

## 3. Claim ranking — enlarged group (22 forks)

| # | Forks (was) | Function family | Disposition (unchanged) |
|---|---:|---|---|
| 1 | 7 (1) | Workflow automation | Core (registry); execution Extended |
| 2 | 2 | Program & project operations | **Core** — project/program registry |
| 2 | 2 (1) | Integrations & interoperability | Extended — connector engines/catalog |
| 4 | 1 | Operational data & structured records | **Core** — the records substrate itself |
| 4 | 1 | Reporting & operational intelligence | Core (records reporting); real-time engine Extended |
| 4 | 1 | Asset & equipment management | **Core** — asset records; management depth Extended |
| 4 | 1 | Inspections & field operations | **Core** — inspection/work records |
| 4 | 1 | Workforce & mission readiness | Core (directory records); readiness analytics Extended |
| 4 | 1 | Safety & compliance management | Core (records substrate); compliance engine Extended |
| 4 | 1 | Governance & compliance functions | Core (records + audit substrate); console engine Extended |
| 4 | 1 | Authorization & access services | **Core** (as RBAC hooks); authorization service / IdP Extended |
| 4 | 1 | Common security services | Core (audit/RBAC hooks); enforcement plane Extended |
| 4 | 1 | Network connectivity & platform services | Extended — platform-layer |
| 4 | 1 | Usage information & metering | **Core** — usage records |
| 4 | 1 | Policy enforcement | Core (workflow/policy registry); enforcement plane Extended |
| 4 | 1 | Application configuration & deployment | Extended — low-code builder/deployment engine |
| 4 | 1 | Mobile capabilities | Extended — mobile applications & sync |
| 4 | 1 | AI capability | Extended — models |
| 4 | 1 | Contractor & vendor management | **Core** — organization directory records |

Group totals: **27 claims** (was 20). Only two families moved:
`workflow_automation` (1 → 7 forks, now the group's most-claimed
family) and `integrations` (1 → 2).

## 4. Core-delta decisions

**Core delta: zero functions. `src/` is unchanged** — no core
extension was warranted, and none was made. Per claimed function:

- `workflow_automation` (6 new forks) → **carried.** The family's
  Core side is the workflow registry (Core 7), which already
  implements what the union presupposes: versioned workflow
  definitions held as records, never executed. The newcomers'
  claims are process-automation *platforms* (Bizagi, UiPath,
  IBM, Ivanti, FM:Systems, Xerox); the part of their function
  that exceeds the registry is execution, already an Extended
  gap (§5, enlarged). No new records function is presupposed by
  any of the six claims that the substrate does not already
  hold, so the registry is not extended.
- `integrations` (1 new fork, IBM) → **Extended, as before.**
  The family had no Core side in the shipped union (connector
  engines & catalog); IBM's claim joins TrackVia's in that gap.
  The build gains no connector surface, and a test pins that
  the store exposes no execution/connector entry point.
- All other families: no new claims → no delta, by construction.

Evidence that the code is untouched: `src/opsmgmt/store.py`
SHA-256 `8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`
is identical to the shipped build's recorded hash
(`scratch/store.py.sha256`), and the additions mutation drill
(§6) was run against that exact file and restored to it.

## 5. Gaps — new and enlarged (for the GAPS.md final batch)

**New** — engines the additions bring that the shipped union's
gap list does not name:

- **Managed print services engine** — output/scan management,
  print-device fleet auditing, automated meter collection,
  secure print (Canon Office Cloud; Xerox MPS).
- **Supply chain & logistics execution suite** — warehouse
  management, transportation planning / execution /
  procurement, supplier enablement, distributed order
  management (Manhattan Government Cloud).
- **Product lifecycle management (PLM) platform** — product
  data creation / collaboration across the lifecycle and
  service lifecycle management (PTC Windchill / Windchill+).
- **IT service management (ITSM) suite** — incident, problem,
  change and release management; service desk (Ivanti Neurons
  for ITSM).
- **Infrastructure maintenance management system** —
  preventive-maintenance scheduling and tracking, issue
  ticketing, configuration baselines, materials inventory
  (InfraLink).
- **Facilities & real property management suite (IWMS)** —
  space, move, and lease management; real-property portfolio
  and capital projects (FM:Systems OpenBlue Workplace; GoRPM;
  IBM TRIRIGA component overlaps).
- **Case management platforms** — EEO case management, dynamic
  case management / BPM, FOIA case processing, correspondence
  and investigations (Tyler Federal icomplaints / entellitrak;
  AINS eCase incl. FOIAXpress).
- **Business process modeling, process mining & enterprise
  architecture platform** (Software AG ARIS; ALFABET).
- **Mail & package operations** — multi-carrier shipping,
  package receiving / tracking / delivery, smart locker
  management (Pitney Bowes SendPro 360).
- **Strategic portfolio & agile planning platforms** —
  portfolio management, roadmaps, cross-team planning and
  execution at scale (stackArmor Clarity; StackArmor Rally).
- **Back-office ERP suite** — financial management, HR and
  payroll, property/asset accounting over Oracle/COTS
  applications (Accenture Federal Cloud ERP).
- **Contract progress management application** — task /
  program / finance views over day-to-day federal contract
  progress (iSite Contract Management Portal).
- **Enterprise asset management depth** — predictive
  maintenance, asset health monitoring, IoT telemetry
  analytics beyond asset records (IBM Maximo within IAS4G;
  extends the shipped ranking's "management depth Extended"
  disposition for asset management).

**Enlarged** — already registered under Group 36; the additions
change their weight, not their nature:

- **Workflow automation execution engine** — was TrackVia
  (1 of 2); now asserted by **7 of 22** forks, including two
  dedicated automation platforms (UiPath RPA, Bizagi digital
  process automation). Robotic process automation execution
  rides this gap.
- **Integration connector engines & catalog** — was TrackVia
  (1 of 2); now **2 of 22** (adds IBM webMethods Hybrid
  Integration).
- **Scheduling & rostering** (named absence) — still 0 taxonomy
  claims and unbuilt, but no longer a universal absence:
  InfraLink asserts scheduling substance (1 of 22) that no
  taxonomy family holds.
- **IoT / telematics data collection** (named absence) —
  still 0 taxonomy claims and unbuilt; IBM asserts IoT
  integration substance inside its `integrations` claim.
  Collection itself remains unbuilt.

Supporting substance without claim changes (recorded so the
final batch sees it): `ai_capability` stays at 1 claim, but
UiPath ("AI-powered automation"), Tyler ("Natural Language
Analytics"), and IBM ("intelligent" EAM) assert AI-adjacent
substance the scoped patterns do not hold; the low-code
builder gap gains UiPath ("Low-code Application Development")
and eCase ("rapid application development") substance; the
mobile gap gains Ivanti ("mobile ... support") and Tyler
("Mobile Modules") substance.

Platform layer (unchanged, gap-listed as before): multi-tenancy
(IAS4G and ARIS assert multi-tenant delivery of their own
platforms; the build remains a single-tenant reference
deployment); encryption at rest (deployment layer); TLS only
when configured; demo identities are hooks, not an IdP — IA-2
stays with the embedding organization.

## 6. Verification (additions)

- Forks spec'd: **20 / 20**, each with verified evidence (or a
  recorded zero-claim outcome); shipped sheets byte-preserved.
- Core implemented: **12 / 12** (the shipped union core;
  extended by 0 functions — §4).
- Tests: **119 → 126** (new file `tests/test_additions.py`, 7
  tests: spec integrity, exact membership, house schema,
  taxonomy/verbatim-evidence audit, the exact claim map, the
  registry-never-executes pin exercised per workflow claimant,
  and the integrations Extended honesty pin). Full suite green.
- Negative control: the core is unchanged, so the group's
  signature drill was **re-run in this tree** (2026-10-31):
  `OpsStore._is_overdue` patched to `return False` in the real
  `src/opsmgmt/store.py` → **126 ran, exactly 9 failed**, the
  identical failure set to the shipped drill (2 negative-control
  canonicals, 2 reports/search, 1 service full-flow, 4
  work-order derivation); store restored and SHA-256-verified
  identical to the shipped hash; suite re-run **126, OK**.
  Record in `tests/README.md`; raw output
  `scratch/additions_mutation_run.txt`; pre-mutation copy
  `scratch/store.py.premutation.additions`.

## 7. Updated union statement

The enlarged group is **22 forks over one records substrate**,
and the additions make the shipped group's heterogeneity
finding stronger, not weaker. The original pair shared one
taxonomy family; the enlarged group shares a *substrate*: the
22 offerings' claimed and census-evidenced functions
collectively presuppose directory, project, asset, work,
inspection, usage, and workflow-definition records under
access control and audit, and that substrate is what this build
implements once, at Moderate/L2. Above it, the engines diverge
completely — print fleets, supply chains, product lifecycles,
case files, process models, mailrooms — and 14 of the 20
newcomers claim nothing the taxonomy holds at all: they are in
this group because their own descriptions describe operational
work management (the census's classification), not because
their vocabulary matches two other products'. Every engine is
named in §5. Nothing about the tier, the baseline, or the
12-function core changed to admit them.

## 8. No-signal addition (2026-10-31)

One further fork joins, by a different route than §1's twenty.
The remainder census left 23 forks unclassified — their cached
marketplace descriptions carry no citable function sentence
(`REMAINDER.md`, unit `no-signal-set`). The live-docs research
pass (`remainder/nosignal_report.json`, `remainder/NOSIGNAL.md`)
resolved this one to Operations Management from the vendor's own
public documentation:

| Fork ID | Vendor / Product |
|---|---|
| F1603077867 | SMX (Formerly Smartronix) / Elevate Intelligent Automation Platform (IAP) |

**Classification basis.** SMX's own capability sheet
(smxtech.com) states: "Through SMX Elevate, we leverage our IP
and Intelligent Automation Platform (IAP) to design, build,
operate, and secure multi-cloud platforms for mission critical
cloud workloads, specializing in highly regulated and
security-first clients including Federal Government, DoD,
healthcare industries, and financial services."
Source: http://www.smxtech.com/wp-content/uploads/2025/02/SMX_SolutionCap_ELEVATE_Platform_Feb2025.pdf
The sentence and URL are stored on the sheet as
`classification_evidence` / `classification_source_url` — the
classification citation, kept distinct from claim evidence:
citations are not claims. The sentence is not a substring of the
cached description (asserted at build time, pinned by test), and
no claim rests on it. (The research report's notes add that the
IAP's cornerstones are automation via Infrastructure-as-Code,
Operations-as-Code, and Policy and Compliance-as-Code.) The fork is **FedRAMP Moderate**, so it
joins at this group's tier by construction and the baseline
does not change (§1's baseline statement stands).

**How it was spec'd.** The group's 19-family taxonomy was
applied verbatim — parsed out of `scratch/extract.py` via `ast`
(never executed), asserted identical to the additions literal —
after first reproducing the group's current shipped claim tables
exactly: a mechanical pass over the 22 shipped descriptions plus
the §2 adjudications (3 removals, 2 evidence re-anchors)
reproduces all 22 tables, 27 claims, ids/labels/evidence equal
(`scratch/extract_nosignal.py`). Claims were then tagged only
from the fork's own cached description
(`remainder/uncovered.json`, asserted byte-identical to the raw
cache's `service_desc`), with the description's five third-party
ISV catalogue paragraphs (Beyond Identity, C3 AI, ColorTokens,
eShare, Versa — partner products deployable through the
platform) excluded before matching, as in the shipped group's
discipline. Raw pass: **3 hits**. Dispositions, each recorded in
full in `scratch/NOSIGNAL_ARTIFACTS.md`:

- `security_services` — **excluded**: the only hit sits in the
  Versa catalogue paragraph, and the matched text is Versa's own
  feature name ("Security Services Edge (SSE)") — a name-only
  token inside another product's expansion (the SCAP class).
- `workflow_automation` — **removed**: the sole hit is the
  offering's own product name ("Intelligent Automation
  Platform") inside the certification sentence — a name-only
  token (UiPath precedent); no other sentence matches the
  pattern while asserting the function ("automations" plural
  does not fire), so there is nothing to re-anchor to.
- `authorization_services` — **removed**: the sole hit asserts
  the platform's own platform-level authorization posture,
  inherited by tenants — the class removed for IBM IAS4G
  ("integrated within the single FedRAMP authorization
  boundary"); the MCSS services-offered standard is not met.

**Final: 0 claims.** SMX joins the group's zero-claim majority
(now 15 of 23). The claim ranking in §3 is unchanged — no family
moved; group totals stay **27 claims over 23 forks**. Named
absences on its own words (itemized in
`scratch/NOSIGNAL_ARTIFACTS.md`): all 19 families, with
substance recorded, not rounded up — provisioning, monitoring,
security, and lifecycle management of multi-cloud platforms are
asserted in its own words and held by no family; "integrates"
is the verb form; governance and policy-guardrail substance
stands without the scoped phrases; "Elevate AI" is AI branding
without a scoped phrase.

**Core-delta decision: zero functions. `src/` is unchanged** —
by the §4 construction, a fork with no claims presupposes no
core extension. The substrate the fork's substance rides is the
shipped one (directory, project, work, workflow-definition
records under access control and audit); a substrate case for
this fork is pinned in `tests/test_nosignal.py`.
`src/opsmgmt/store.py` remains SHA-256
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
the shipped build's recorded hash.

**Gaps gained.**

New — engines this fork asserts in substance that neither the
shipped union's gap list nor §5 names:

- **Cloud platform operations & lifecycle management engine** —
  provisioning, monitoring, security, and lifecycle management
  of multi-cloud platforms, run as code (Infrastructure-as-Code
  / Operations-as-Code) (SMX Elevate IAP; adjacent to, but not
  the same as, the shipped union's platform-layer connectivity
  gap).
- **Built-in compliance automation & policy guardrails
  engine** — native controls and automations supporting CMMC,
  HIPAA, HITECH, CJIS, PCI, SOC 1/2, FedRAMP, and DoD IL
  baselines, with policy-driven guardrails over multi-tenant
  and cross-domain operations (SMX Elevate IAP; related to the
  shipped governance/compliance console and policy enforcement
  plane gaps, which are MCSS's console/enforcement depth, not
  this baseline-content automation).

Already registered — gaining substance, noted here, not
re-registered:

- **Authorization service / identity provider** (UNION-SPEC
  gap) — SMX's "Elevate ATO Fast Track" accelerator asserts
  authorization-acceleration substance for customers' own
  FedRAMP/CMMC/DoD authorization processes.
- **AI models** (UNION-SPEC gap) — SMX's own "Elevate AI"
  accelerator (secure generative AI) asserts AI substance at
  branding level; `ai_capability` remains TrackVia's claim
  alone.
- **Platform layer — multi-tenancy** — SMX asserts multi-tenant
  and cross-domain operation of its own platform (cf. the
  IAS4G/ARIS assertions in §5); the build remains a
  single-tenant reference deployment.

**Verification (no-signal addition).**

- Forks spec'd: **1 / 1**, with a recorded zero-claim outcome;
  the 22 shipped sheets are preserved byte-for-byte (asserted at
  build time) and pinned deep-equal to git HEAD by test.
- Core implemented: **12 / 12** (the shipped union core;
  extended by 0 functions).
- Tests: **126 → 134** (new file `tests/test_nosignal.py`, 8
  tests: HEAD deep-equality, membership, schema, verbatim
  description-of-record, the literal zero-claim table,
  classification-field pins, and the substrate case). Full
  suite green. One transparency note: `test_additions.py`'s
  whole-file assertions are scoped to its era's 22 sheets
  (`specs[:22]` / `specs[2:22]`, noted in that module); every
  assertion about the additions unit keeps its exact strength.
- Negative control: the core is unchanged, so the group's
  signature drill was **re-run in this tree** (2026-10-31):
  `OpsStore._is_overdue` patched to `return False` in the real
  `src/opsmgmt/store.py` → **134 ran, exactly 9 failed**, the
  identical failure set to the shipped drill; store restored
  and SHA-256-verified identical to the shipped hash; suite
  re-run **134, OK**. Record in `tests/README.md`; raw output
  `scratch/nosignal_mutation_run.txt`; pre-mutation copy
  `scratch/store.py.premutation.nosignal`.

**Updated union statement.** The group is now **23 forks over
one records substrate**. The 23rd arrived by live documentation
rather than marketplace prose, and the taxonomy — applied
verbatim, untested by its vocabulary — holds it at zero claims:
its own capability sheet classifies it by operating multi-cloud
platforms, a function this group's families, defined from two
other products' descriptions, do not name. It is in this group
because SMX's own words describe operations work, and its
engines are named above. Nothing about the tier, the baseline,
or the 12-function core changed to admit it.
