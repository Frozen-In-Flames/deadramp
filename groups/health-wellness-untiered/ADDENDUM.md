# Addendum — Health & Wellness, untiered set: the no-signal addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the one
fork that joins the set after the census, resolved by the live-docs
research pass. The original union spec stands as written: its
taxonomy, its ten-function substrate, its privacy discipline, and
its Documented control claims section are **unchanged** — and so is
its tier discipline. Every member of the enlarged set still records
FedRAMP impact level **Unknown** in the source, so **tier stays
null**: no tier is assigned, no CMMC equivalence is drawn, and no
control baseline is asserted for the newcomer or for the set.

**Headline: forks spec'd 1 / 1; 0 claims — the newcomer is a
zero-claim fork under the taxonomy applied verbatim; core delta —
zero functions extended, `src/` byte-identical; documented control
claims — no addition (the fork's description asserts no control
language of any family); tests 80 → 91, all passing.**

## 1. Membership and method

The fork:

| Fork | Vendor / product |
|---|---|
| `FR2700137029` | HealthEdge Software, Inc. / HealthEdge Integrated Solution Suite |

**Why it was not in the census unit.** This fork sat in the
remainder census's **`no-signal-set`**: the census recorded **no
citations and a `no_signal` flag** (reason "prose_only"), with the
classifier note: "Description is a single vague sentence about an
agentic operational/financial platform for payers and agencies; no
specific function named." No citable function could be read out of
its marketplace description, so no build unit proposed a category
for it.

**Classification basis (live-docs research pass).** The category
was resolved afterwards from the vendor's own public pages
(`../../remainder/nosignal_report.json`, entry `FR2700137029`,
status "resolved", existing category — not a new one):

> "HealthEdge combines flexible delivery models with an integrated
> suite of software solutions to transform payer operations,
> connecting data, workflows and performance across the health
> plan enterprise."
> — https://healthedge.com/press-release/healthedge-and-healthproof-merge-creating-disruptive-ai-powered-healthcare-payer-technology-and-services-leader/

**Recorded weight: suite level.** The sentence describes the
Integrated Solution Suite as a whole — the offering this sheet
stands for — and the research record (`../../remainder/NOSIGNAL.md`)
records it at that weight: it is a suite-level statement from the
vendor's own press release, not a component-level or
function-level citation. That sentence is recorded on the fork's
spec sheet as `classification_evidence`, with
`classification_source_url` alongside it. **It is a classification
citation, not claim evidence**: it does not occur in the fork's
cached marketplace description (asserted in the extractor and in
the tests), and no claim below rests on it. Claims are tagged from
the cached description only, exactly as in the union spec.

**Method.** The spec sheet was produced by
`scratch/nosignal_extract.py`, which parses the `TAXONOMY` literal
out of the founding group's extractor
(`../health-wellness-l2/scratch/extract.py`) via `ast` (parsed,
never executed) and asserts its 11 families — and, before tagging
the newcomer, re-applies the taxonomy twice as proof:
(1) to the founding group's original five forks, reproducing
their **original shipped claim tables exactly (5 sheets, 19
claims, deep-equal** against `scratch/original_shipped_specs.json`,
the same proof the set's own extractor ran); and (2) to this
set's 3 shipped sheets' descriptions, reproducing **their stored
claim tables exactly (3 sheets, 1 claim)**. The sheet is
**appended** to `specs/specs.json` after the 3 shipped sheets,
which are verified deep-equal against git HEAD (both in the
extractor and in `tests/test_nosignal_addition.py`); its
description is verified identical in both cached sources
(`raw/data_dump.json` `service_desc` and
`remainder/uncovered.json`). Only `service_desc` was matched: the
record's `certified_services` field is a third-party catalogue
segment and was never read or matched, per house discipline. The
fork is FedRAMP **Initial Implementation**, SaaS, deployment
model Government-Only Cloud as recorded; its sheet records
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, exactly
like the set's shipped sheets.

## 2. What the fork claims

**0 claims.** The entire marketplace description is one sentence:

> "The HealthEdge Integrated Solution Suite provides payers and
> agencies with an agentic platform of operational infrastructure
> designed to guarantee an enduring financial edge."

No family's phrase fires:

| Family | On HealthEdge's words |
|---|---|
| measurement_data | absent — no glucose / CGM / clinical-metrics wording |
| analysis_reporting | absent — no "review, analysis", patterns/trends, or `scorecards` phrase |
| care_guidance | absent — no care wording of any kind |
| patient_engagement | absent — the word **"patient" occurs nowhere** in the description |
| claims_processing | absent — "payers" names the customer population, not "medical claims processing" or "justify reimbursement" |
| emr_integration | absent — "Integrated" in the product's name is not "Integrated with EMR" or "integration with client systems" |
| ai_platform | absent — "agentic" is not the family's exact phrase "Artificial Intelligence (AI) powered" (near-miss, below) |
| automation | absent — neither "automated" nor "automates" appears |
| device_connectivity | absent — no device wording |
| multi_device_access | absent — no multi-device or web-and-mobile phrase |
| hosting_platform | absent — neither of the founding fork's Google phrases; the record's "Government-Only Cloud" deployment model is record metadata, not a description claim |

The set's claim total stays **1**, and **3 of its 4 forks now
carry zero claims** (Elvo, WellHive, HealthEdge). The raw pass
produced no hits at all, so the exclusion pass removed nothing
(`scratch/nosignal_adjudication.json`).

Near-misses, itemized (each pinned in
`tests/test_nosignal_addition.py` — substance token asserted
present, family phrase asserted absent):

- **"Agentic platform"** is AI-adjacent wording, but `ai_platform`
  requires the founding phrase "Artificial Intelligence (AI)
  powered". (The classification press release's own headline
  language about an "AI-powered" company is vendor live-page
  material used for classification; it is not the marketplace
  description and earns no tag either.)
- **"Payers"** names the population served — the founding
  correction class for bare population wording — not a
  claims-processing phrase.
- **"Integrated Solution Suite"** is the product's name, not an
  integration assertion; no integration phrase occurs.
- **"Operational infrastructure" / "financial edge"** is outcome
  prose — the census's own reading ("no specific function named")
  — and matches no family.

## 3. Documented control claims — effect of the addition

**None.** The fork's description asserts no control language of
any family: checked and pinned in the tests — "security", "HIPAA",
"audit", "access control", and "encrypt" each occur **zero**
times in the description, and no identity, SSO, or MFA wording
occurs. The set's Documented control claims accounting therefore
stands exactly as recorded in `UNION-SPEC.md`: the only documented
item in the enlarged set remains WellHive's assertion of
compliance with "HIPAA and NIST 800-53 Appendix J Privacy
Controls", at compliance-assertion weight. (HIPAA appears in the
classification press release's prose about the vendor; that is
classification-side material, not this fork's marketplace
description, and it documents no control claim here.) Nothing is
filled in from any baseline; no CMMC equivalence is drawn; the
tier stays null.

## 4. Named-absence updates on this fork's words

Every family stands absent on this fork's words (§2), so the
union spec's named absences are unchanged in kind and gain one
more zero: measurement & device data, review/analysis &
scorecards, EMR integration, care guidance, claims processing,
hosting claims, AI, automation, device connectivity, and
multi-device access are now 0 of 4 forks on this fork's wording,
as they were 0 of 3 before it (the set's single claim remains
86Borders' `patient_engagement`). **Telehealth**: the fork never
mentions telehealth in any form, so the union spec's record
stands untouched — the wording is absent here, the L2-tier
retirement does not transfer, and this addition neither re-opens
nor extends the question. Access control / audit in text remains
absent — now 0/4 forks; Core 9/10 remain carried substrate, not
claimed, exactly as shipped.

## 5. Core-delta decision

No family is claimed, so no claim buys a new records form. The
described surface was checked against the Core anyway:

| HealthEdge surface | Records form it presupposes | Core delta |
|---|---|---|
| Payer coverage held for members | **Core 7** eligibility/coverage records (opaque `plan_ref` only; no insurer, member-number, or benefit field exists) | **Carried** |
| Operations follow-up tracked over members and programs | **Core 5** plan records with derived status; **Core 3** enrollment derivation | **Carried** |
| The integrated suite's payer operations themselves — the workflows, data connection, and performance machinery named only at suite level by the classification citation | None — engines over plan/claims content, Extended by construction under the set's privacy discipline; no record shape in the substrate can hold them | **Gap** (§6) |

**Result: the core is unchanged.** `src/` is byte-identical to
the shipped build (`src/health/store.py` SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`
before and after this addendum's work, the mutation drill
included; all 7 modules match the founding group's hashes in the
README's byte-identity table). The build remains a records
substrate, **not a medical device, and claims no FDA status** —
for HealthEdge exactly as for the other three.

## 6. Gaps

**New gap function** (1):

- **Payer (health plan) operations platform** — the integrated
  suite's payer-operations functions entire, named at suite level
  by the fork's classification citation ("transform payer
  operations, connecting data, workflows and performance across
  the health plan enterprise") and by its description's "agentic
  platform of operational infrastructure" for payers and agencies.
  No taxonomy family holds payer operations; the function is
  registered in its own name, not approximated into the clinical
  families. The coverage and plan records it presupposes are
  Core 7/5; the operations themselves are Extended.

**Existing gaps gaining substance** (no family claim fired,
recorded as such; noted here, not re-registered):

- **AI/ML models & personalization engines** — HealthEdge's
  "agentic platform" is AI-operations wording in substance; the
  family's exact phrase did not fire.
- **Automation / workflow engines** — the classification
  citation's "workflows" and the description's "operational
  infrastructure" are workflow-automation substance at suite
  level; no automation phrase fired.
- **Hosting platform layer** — the record's Government-Only Cloud
  deployment prose; a platform-layer property, never a health
  function, exactly as recorded for the set's AWS-hosted forks.

**Explicitly no claimant gained:** the set's registered
**insurance verification, benefits discovery & claims adjudication
engines** gap gains **no** claimant from this fork — adjudication
is named in neither the description nor the classification
sentence, and the suite-level phrase "payer operations" is not
inflated into an adjudication claim. The substrate's eligibility
records are the coverage record such an engine would check
against; the engine itself remains unclaimed here.

## 7. Updated union statement

The set now covers **4 forks** (3 census members + 1 no-signal
addition), **1 claim** in total (unchanged), with **1 of 4** forks
carrying a claim and 3 pinned at zero. The merged build is
unchanged: the same ten-function substrate, carried byte-identical
from the founding Health & Wellness L2 build, now spec'd against
4 marketplace offerings. The newcomer widens the set's character:
the shipped three are care-delivery and care-navigation offerings,
while HealthEdge is a **payer-side** platform — health plan
operations, not care delivery — whose marketplace description
names no function at all, which is precisely why the census set
it aside and why its classification rests on the vendor's own
live documentation, cited on the sheet at suite level. The
privacy discipline binds it identically: no field in any record
can hold real PHI, diagnosis content, or clinical free text, and
everything operational in the fork's suite is Extended (§6).
Tier null is recorded on every sheet, the new one included, and
pinned by tests. Nothing in the enlarged set claims a FedRAMP
authorization, a CMMC certification, or a control baseline for
any fork or for the build itself. This build is not a medical
device and claims no FDA status.

## 8. Verification

- Spec integrity is pinned by `tests/test_nosignal_addition.py`:
  sheet count and order (4), the 3 shipped sheets deep-equal to
  git HEAD, membership against the census `no-signal-set`, the
  literal zero-claim table, the unchanged set claim total (1),
  tier discipline on the new sheet, the description verbatim
  against both cached sources, the classification fields pinned
  against `remainder/nosignal_report.json` (with the
  classification sentence asserted absent from the cached
  description and the report entry asserted suite-level in the
  module docstring), the control-language absence pins, and the
  near-miss pins. The fork is exercised against the substrate in
  the same module: a coverage record under an opaque `plan_ref`
  with its exact contract key set deriving upcoming → current →
  ended, and an operations plan deriving overdue with its
  enrollment.
- The whole-file aggregate pins in `tests/test_specs.py` (sheet
  count, census-unit membership, claim total, zero-claim set) are
  scoped to the set's own slice (the first 3 sheets) because a
  4th sheet now follows theirs; every fact they pin about the set
  is unchanged, and the scoping is recorded in that module's
  docstring — the founding group's no-signal precedent.
- **Tests: 80 → 91, all passing.**
- **Negative control:** the set's signature drill was re-run in
  this tree: the overdue branch of
  `HealthStore._derive_plan_status` was patched to return
  `"current"` and the full suite ran — **91 tests, exactly 9
  failures**: the shipped drill's 8 plus the new HealthEdge
  substrate case, tripping exactly as designed; no spec-integrity
  test tripped. `store.py` was restored from the pre-mutation
  copy and verified SHA-256-identical to the shipped hash; the
  suite re-ran green. Recorded in `tests/README.md`; raw output
  in `scratch/nosignal_mutation_run.txt`.
