# Manufacturing — untiered (DeadRamp Phase 2, Untiered Set 26)

An **untiered set** of DeadRamp: forks whose FedRAMP impact level
is "Unknown" in the marketplace source. They carry no FedRAMP
baseline, so there is nothing to crosswalk: each fork's tier
stays `null`, no CMMC equivalence is drawn, and the merged build
is built to the fork's **documented control claims** only — the
control language its own description actually uses, traced in
UNION-SPEC.md, never filled in from a baseline. This fork's
description asserts no control language at all, and the spec
says so.

Manufacturing is also a **new category** for this repo: the
census proposed it for this single fork, recording that no
existing category covers manufacturing / engineering-intent
conversion (Operations Management covers running operations, not
transforming engineering intent into manufacturable decisions).
No tiered group exists at any level, so there was no founding
taxonomy to inherit and no substrate to carry. The taxonomy
below was defined fresh from this fork's own description (the
new-category method used for Contract Management, Storage,
Marketing & Sales, and Talent Development), and the core was
built fresh in the house architecture. If tiered Manufacturing
forks ever appear, this set's taxonomy becomes the category's
taxonomy, tested against their prose the way every founding
taxonomy here has been tested against its remainder.

## The fork (1)

| Fork | Vendor | Product | Status | Claims |
|------|--------|---------|--------|-------:|
| FR2632054516 | Neuramill, Inc. | NeuraBridge | Initial Implementation | 4 |

Spec sheet: `specs/specs.json`. Union analysis: `UNION-SPEC.md`.

**NeuraBridge** is intelligence software for high-precision
manufacturing that, in its description's whole account of
itself, "transforms engineering intent into structured,
manufacturable decisions for aerospace and defense teams" —
filed Uncategorized in the source, assigned to the new
Manufacturing category by the census from that description. The
description is two sentences; the taxonomy, the four claims, and
the build all rest on those two sentences and nothing else.

## Taxonomy (4 families, defined from this description)

`manufacturing_intelligence` (sentence 1, at identity-sentence
weight, Extended), `engineering_intent`,
`intent_transformation`, and `manufacturable_decisions`
(sentence 2). Each family's patterns are drawn from the
description's own phrases; the derivation — including why
sentence 1 carries a family here while a comparable positioning
sentence in Set 20 did not, and why the audience phrase "for
aerospace and defense teams" defined no family — is stated in
full in UNION-SPEC.md. Because the taxonomy comes from exactly
one description, every count here is a floor over this set only.

## The merged build — `manufacturing`

A fresh core: Python standard library only, in
`src/manufacturing/` (errors, access, audit, store, service,
CLI). Eight numbered functions in UNION-SPEC.md: organization
registry; engineering intent records with **status derived at
read, never stored** (`open` until a decision cites the intent,
`transformed` after); structured, manufacturable decision
records whose **basis** — the intent records the decision
transforms — is enforced by the **decision-basis guard**, the
build's signature invariant: a basis that is empty, duplicated,
unknown, or another organization's is refused, records nothing,
and consumes no id; search and summary (counts only); a REST
API; and access/audit hooks.

The build performs no transformation and exercises no
intelligence: a decision record *records* a transformation, as
basis links to the intent it rests on, and the engine that
converts intent into decisions is a named gap. It judges no
manufacturability — "manufacturable" is the fork's word for the
kind of decision its software produces. It holds **no money
shape at all**, because the description states no fees, prices,
costs, or budgets, and it computes **no score** of any kind.
People appear only as opaque references that cannot be email
addresses; intent and decision statements are caller-supplied
engineering text stored verbatim.

## Running

Server (demo users alice/bob/carol via `X-User` / `X-Role`
headers):

    PYTHONPATH=src python3 -m manufacturing serve --port 8765

Tests (47):

    PYTHONPATH=src python3 -m unittest discover -s tests

Demo users: alice (admin), bob (operator), carol (viewer). Demo
identities are hooks, not an IdP — authentication stays with the
embedding organization.

## Documented control claims

With no tier, there is no baseline section: UNION-SPEC.md
carries a **Documented control claims** section instead. Its
whole content is: **none documented.** Neither of the
description's two sentences contains any control language —
"security", "access control", "audit", "encrypt", and "single
sign-on" occur nowhere in it (token-verified) — and the raw
record's "Government-Only Cloud" deployment model is record
metadata, not a control claim. Every 800-53 family is listed
not documented for this set. The build's access and audit
machinery is house substrate, claimed against no fork. A fork's
documented control language is its claim, never this build's
attainment — and here there is none to claim.

## Honesty

- **Tier is null.** The fork is "Unknown" in the source; nothing
  here assigns a tier, draws a CMMC equivalence, or asserts a
  baseline, and tests pin `cmmc_tier: null` on the sheet.
- **New category.** The taxonomy is this set's own, derived from
  one two-sentence description. It is not Operations
  Management's taxonomy and not Design & Multimedia's; the
  census's boundary between those categories and this one is
  recorded in UNION-SPEC.md.
- **Every claim traces** to the fork's own description, stored
  as evidence on its sheet. Matching ran over the description
  only: the `certified_services` field was never matched — it is
  empty for this fork in any case.
- **Census citations are not automatically claims** (in either
  direction — and this set runs the other way from Set 20): the
  fork's two census citations verify verbatim AND both serve as
  claim evidence, because the census cited exactly the two
  sentences the taxonomy derives from. Verification alone is
  still not what makes a sentence a claim.
- **One claim is at identity-sentence weight.**
  `manufacturing_intelligence` rests on the sentence that states
  what the software *is*, with no mechanism named; it is
  disposed Extended and the weight is recorded, not hidden.
- **Extended functions, by name:** the engineering-intent
  transformation engine, including the manufacturing-intelligence
  engine entire (the build records transformations as basis
  links; it performs none); and the platform layer (SaaS /
  Government-Only Cloud hosting), which is substrate, not a fork
  function.
- **Named absences** (token-verified in the description): no
  design authoring or CAD, no PLM, no manufacturing execution
  (MES), no quality/inspection/metrology function, no CNC or
  machine control, no supply chain or inventory, no production
  scheduling, no digital twin or simulation, no robotics or
  sensors, no maintenance, no workflow or automation, no
  analytics or reporting surface, no AI, and — despite the
  "aerospace and defense teams" audience — no export-control,
  ITAR, or classification-handling function. Audience is not
  evidence.
