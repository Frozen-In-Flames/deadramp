# Addendum — Operations Management, CMMC L1 singleton: the 3 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 3
previously uncategorized forks of remainder build unit
**`addition:operations-management-l1`** (see `../../REMAINDER.md`).
The original union spec stands as written: its taxonomy, its
12-function core, and its Low/L1 control baseline are **unchanged**.
This document records what joined, what the newcomers claim under
the group's existing taxonomy, the core-delta decision for the one
claimed function, and the updated union statement.

**Headline: forks spec'd 3 / 3; 1 new claim; core delta — zero
functions extended, `src/` byte-identical; tests 119 → 129, all
passing.** The single claim (Tango, `integrations`) is the enlarged
group's first: the original fork claimed 0 of 19 families, and two
of the three newcomers claim zero as well. The group's character
finding from the original spec deepens rather than changes — the
category's workplace-scheduling substance arrives at this tier in
the newcomers' own prose, but the verbatim taxonomy has **no
scheduling family**, so it lands almost entirely on the gap side
(§5). **7 new gap functions** are named in §5, and 1
already-registered gap gains a claimant (plus 1 by substance).

## 1. Membership and method

The 3 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2017462201` | Booz Allen Hamilton / Supply Chain Master Catalog (SCMC) Government Cloud Solution |
| 2 | `FR1828574469` | FM:Systems / OpenBlue Employee |
| 3 | `FR2100740435` | Tango / Tango |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed — running
  the original would regenerate the 1-fork specs file) and asserts
  it triple-equal to Group 36's taxonomy parsed the same way**
  before tagging — the taxonomy was applied verbatim, not re-tuned
  for the newcomers. Same sentence splitting, same evidence rule
  (first matching sentence per family, stored verbatim), same
  sheet schema as the shipped OpenWater sheet. The 3 sheets are
  **appended** to `specs/specs.json` after the original, which is
  verified **deep-equal against git HEAD** before and after the
  append.
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 3
  descriptions were present; no live fetching. All 3 are FedRAMP
  **LI-SaaS** (FedRAMP Certified), exactly the original fork's
  impact level, so the group stays single-tier and the Low/L1
  baseline — including its precision notes (AU-2/AU-3 on the Low
  side only; AU-6 deliberately not imported) — is inherited in
  full, unchanged.
- The census starting point was verified, not trusted: all **4
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **4 / 4 verify** as verbatim
  substrings. None of the 4 is the evidence sentence of any claim
  (§2) — verification is not a claim.
- **No exclusion trap applies to the newcomers.** None of the 3
  records carries a hosted-services or certified-services block
  (every record's `certified_services` is empty, asserted in the
  extractor); only `service_desc` was matched, per house method.
  Tango's description does carry an extended catalogue of its own
  other products (§2); the extractor verified programmatically
  that the catalogue sentences add **no family** beyond what the
  certified Reserve surface itself claims, so the claim set is
  identical under either treatment.

## 2. What the additions claim

**1 claim** across the 3 forks. Combined ranking for the enlarged
group (original 1 + additions 3 = 4 forks), under the group's
19-family taxonomy:

| Function family | Additions claiming | Group total (4) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Integrations & interoperability | 1 | 1 | **Extended** — connector engines; Core side is Core 10 (REST API) |
| All other 18 families | 0 | 0 | As in UNION-SPEC (carried substrate / Extended / absent) |

Per-fork claim counts: SCMC **0**, FM:Systems **0**, Tango **1**
(`integrations`, evidence: "Utilize integrations with existing
platforms to rapidly adopt and deploy." — a functionality-list
sentence of the certified Tango Reserve surface). The full per-fork
table is pinned literally in `tests/test_additions.py`
(`EXPECTED_CLAIMS`).

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no
pattern (the full per-sentence map is
`scratch/additions_sentence_map.json`):

- **Booz Allen SCMC** — "purchasing the right items from the
  right vendors at the right price" and "driving contract
  utilization" are not `vendor_management` (the family requires
  the exact phrase "contractor and vendor management");
  procurement / supply-chain operation has no taxonomy family at
  all. "Booz Allen Hamilton's secure cloud infrastructure" is not
  `security_services` ("security services" required). Its census
  citation (the SaaS/procurement sentence) verifies and tags
  nothing.
- **FM:Systems OpenBlue Employee** — "Outlook Integration", "IoT
  Sensor Integration", and "integrating with our room booking"
  are not `\bintegrations\b` (the family requires the plural
  noun). "Contactless workflows" is not "automated workflows" and
  no `automation` token appears. "Mobile scheduling" and "mobile
  technologies" are not "mobile capabilities". "Measure actual
  workspace utilization" is not "usage information". "Reporting &
  Analytics … analyze trends" matches no `reporting_intelligence`
  phrase. "A dynamic management console" is not the
  `governance_compliance` phrase "management and compliance
  console". Its census citation (the desk-and-resource-scheduling
  sentence) verifies and tags nothing — and its headline function,
  **scheduling, has no family**: see the absence note below.
- **Tango** — Both census citations verify and tag nothing: "a
  SaaS workplace solution for managing your use of workspaces"
  matches no family, and "provides operational Analytics for
  workplace optimization efforts" matches no
  `reporting_intelligence` phrase. "Operational data" is not
  `operational_data` ("structured data" required).
  "Assetreservation system" (one word in the source) is not "asset
  and equipment management". "Workplace operations" is not
  "program operations"; "aligns activities across budgets" (in
  the catalogue) is not "across projects". "Secure
  authentication" is not `\bauthorization\b`. In the extended
  catalogue: "IoT integrations" hits the already-claimed family
  and adds nothing; "advanced AI/ML modeling" is not
  `ai_capability` (no "artificial intelligence" / "machine
  learning" phrase); "built to comply with FASB ACS 842" matches
  no governance phrase.

### The two named absences, restated for the enlarged group

UNION-SPEC carried two category named absences, and both survive
this addition **as claim facts** while their substance picture
changes — recorded here so neither is misread:

- **Scheduling / rostering** stood at 0 claims because the
  taxonomy has no scheduling family. Two of the three newcomers
  are scheduling products in their own words (FM:Systems: "desk
  and resource scheduling"; Tango: a "workspace hoteling,
  conference room … reservation system"). The absence now reads:
  asserted in substance by 2 of 4 forks at this tier, claimed by
  0, because no family exists to claim it. The scheduling engine
  is a new gap (§5), not a silent omission.
- **IoT / telematics data collection** stood at 0 claims
  everywhere in the category. Both workplace newcomers assert IoT
  integration in prose (FM:Systems' "IoT Sensor Integration";
  Tango's "IoT integrations", in its catalogue). Still 0 claims —
  again, no family exists — with the substance recorded and the
  sensing engine named as a gap (§5).

### Wording artifacts, recorded not corrected

- **SCMC's described product is not its listing title.** The
  listing names "Supply Chain Master Catalog (SCMC) Government
  Cloud Solution"; the description describes **Prodigo
  Marketplace** throughout (the census classifier noted the
  same). The sheet preserves both as written; nothing is resolved
  or renamed.
- **Tango's prose carries source defects verbatim**: the garbled
  census-citation sentence "Tango provides this the capability to
  manage conference rooms…", the one-word "assetreservation", and
  "FASB ACS 842" (for ASC 842) in the catalogue. Evidence and
  descriptions are stored exactly as published.

## 3. Core-delta decisions

Exactly one family is claimed by the additions, so exactly one
decision is required:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Integrations & interoperability (1: Tango) | Extended — integration connector engines & catalog (category union, registered under Group 36); Core side is Core 10, the REST API surface | **Carried** — no change |

**The decision, stated plainly.** In the original spec this family
stood at 0 claims because its sole raw hit was **removed**: the
hit sat in a scope-exclusion sentence (capabilities the OpenWater
listing itself places outside the FedRAMP Minimum Assessment
Scope), and an out-of-scope catalogue mention asserts no in-scope
function. That ruling was about OpenWater's sentence, not about
the family, and it is unaffected by this addition — OpenWater's
out-of-scope integrations mention remains a separate out-of-scope
gap, exactly as shipped. Tango's hit is different in kind:
functional prose inside the certified Reserve surface ("Utilize
integrations with existing platforms to rapidly adopt and
deploy"), so the claim stands.

What the claim buys: no records form the build lacks. An
integrations claim of this shape presupposes an API surface to
integrate through, and the build's Core 10 is one; the engines
that would execute connections — connectors, sync, third-party
catalogs — were already Extended in the category union and gain a
claimant at this tier (§5). **Result: the core is unchanged.** No
function the 3 forks claim or presuppose a records form for is
missing from the 12-function substrate: SCMC's vendor organization,
supply project, requisition work order, and usage records are
Core 1/2/4/6; Tango's workplace project and facilities work order
are Core 2/4; FM:Systems' reservable-room asset record is Core 3
and its turnover workflow definition is Core 7 (registered, never
executed — the scheduling engine it gestures at is a gap, §5).
`src/` is byte-identical to the shipped build (`src/opsmgmt/
store.py` SHA-256
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`
before and after this addendum's work, the mutation drill
included; the full `src/` diff against HEAD is empty). The tier baseline does not change: same tier by
construction, and the one claim is Extended, adding no control
surface at L1.

## 4. Updated union statement

The group now covers **4 forks** (the original singleton + 3
remainder additions), **1 claim** in total (0 + 1), with **1 of 4**
forks carrying at least one claim. The merged build remains the
same 12-function operations records substrate at the Low/L1
baseline — directory, projects, assets, work orders (overdue
derived at read, never stored), inspections (verbatim outcomes
only), usage records, the never-executing workflow registry,
reports, search, REST API, RBAC, append-only audit — now spec'd
against 4 marketplace offerings instead of 1.

The group's character, stated as plainly as the original spec
stated it: **none of the 4 forks is an operations-work platform of
the kind the category taxonomy was defined from.** The original is
a submission-and-review platform; the newcomers are two
workplace-operations platforms whose headline function
(scheduling and reservation) the taxonomy cannot name, and a
healthcare supply-chain procurement gateway whose described
product is a different product than its listing title. The
substrate is still **not a substitute** for any fork's actual
surface, and nothing in the build schedules, reserves, procures,
or scores. That is now true against 4 forks, with the newcomers'
engines named as gaps in §5 rather than left implicit.

## 5. Gaps — for the registry at ship

**New gap functions** (7):

- **Workspace scheduling & reservation engine** — desk / room /
  resource scheduling, hoteling & desk sharing, the reservation
  lifecycle (FM:Systems OpenBlue Employee; Tango Reserve). The
  headline function of both workplace forks; no taxonomy family
  names it (the category's scheduling absence, §2).
- **Visitor & event management** — visitor registration and
  handling, event setup and management (FM:Systems).
- **Interactive floor plans, wayfinding & digital signage** —
  floor-plan interfaces, colleague location, room / lobby / desk
  signage (FM:Systems; Tango).
- **IoT sensor integration & workspace-utilization sensing** —
  sensor feeds and utilization measurement (FM:Systems; Tango by
  catalogue substance). The category's IoT claim-absence stands
  (no family exists); the forks assert the substance in prose.
- **Workplace analytics & optimization engine** — utilization and
  operational analytics beyond the substrate's registry reports
  (FM:Systems, Tango, by substance: "Reporting & Analytics",
  "operational Analytics"; the `reporting_intelligence` claim did
  not fire on their wording, recorded in §2).
- **Procurement marketplace & requisitioning engine** —
  e-commerce ordering gateway, contract utilization at the point
  of requisition, preferred-source direction (Booz Allen SCMC /
  Prodigo Marketplace).
- **Real-estate portfolio suite** (Tango catalogue excess) —
  space planning & move management, lease administration & lease
  accounting, transaction / pipeline analytics, predictive
  location analytics. The fork's extended catalogue beyond the
  certified Reserve surface, recorded as excess per the census
  treatment — not as certified claims.

**Existing gaps gaining claimants:**

- **Integration connector engines & catalog** (category-union
  Extended family, registered under Group 36) — +1 claimant at
  this tier: Tango, whose claim fired on certified-surface prose.
  OpenWater's out-of-scope third-party-integrations gap is
  separate and gains nothing.
- **Mobile applications & offline sync** — +1 by substance:
  FM:Systems ("mobile scheduling", "mobile technologies" as its
  access mode); the `mobile_capabilities` family claim itself did
  not fire on its wording, recorded in §2.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and unit order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim fork set, verbatim evidence, the census
  citations, and the near-miss pins (see
  `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: SCMC's vendor organization + supply project +
  requisition work order + order-volume usage record, with the
  report's overdue count derived at `now`; FM:Systems' reservable
  room as an asset record beside a registered (never executed)
  turnover workflow, with the absence of any reservation /
  scheduling entry point on the store pinned; Tango's workplace
  project + facilities work order, with the absence of any
  connector / integration entry point pinned (the integrations
  claim is Extended only).
- **Tests: 119 → 129, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `OpsStore._is_overdue`
  in `src/opsmgmt/store.py` was patched so its final return is
  `False` (an overdue open work order never reads overdue) and
  the full suite ran — **129 tests, exactly 11 failures**: the
  shipped drill's 9 (work-order derivation ×4, negative control
  ×2, report overdue ×2, service full flow) plus 2 from the new
  additions module (the SCMC substrate case and the Tango
  integrations case), which trip on the mutant exactly as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; full output in
  `scratch/additions_mutation_run.txt`.
