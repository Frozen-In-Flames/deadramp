# Union Spec — Manufacturing, untiered (DeadRamp Phase 2, Untiered Set 26)

> **UNION-SPEC v1 — 1 fork spec'd under a taxonomy defined from
> its own description; tier null.**
>
> This set is the remainder census's `untiered:Manufacturing`
> unit (REMAINDER.md): the one fork whose FedRAMP impact level is
> "Unknown" in the source and whose function the census proposed
> as a **new category**, Manufacturing — recording that no
> existing category covers manufacturing / engineering-intent
> conversion (Operations Management covers running operations,
> not transforming engineering intent into manufacturable
> decisions, and Design & Multimedia does not cover
> manufacturing). **Manufacturing has no tiered group anywhere
> in this repo** — no L1/L2/L3 sibling exists to inherit a
> taxonomy or a substrate from — so this set gets the
> new-category treatment (the Contract Management / Storage /
> Marketing & Sales / Talent Development method): the taxonomy
> is derived from the fork's own description, and the core is
> built fresh in the house architecture.
>
> Tier discipline: the fork records `fedramp_impact_level`
> exactly as the source has it — "Unknown" — and `cmmc_tier:
> null`. No tier is assigned, no CMMC equivalence is drawn, and
> no FedRAMP baseline is asserted anywhere in this set. The fork
> builds to its documented control claims only (the section so
> titled below replaces the baseline section a tiered group's
> union spec would carry).

| Fork | Product | Status | Claims |
|------|---------|--------|-------:|
| FR2632054516 | NeuraBridge (Neuramill, Inc.) | Initial Implementation | 4 |

**Total: 4 claims across 4 families. Zero-claim forks: 0.**

The registry filed NeuraBridge under "Uncategorized (none in
source)" with no business categories at all; its assignment to
Manufacturing is the census's, from its description, and the
sheet records both the filed category and the census assignment
plainly. The description is two sentences, and both are
load-bearing: the census cited exactly these two sentences, and
the taxonomy below is derived from exactly these two sentences.

## Taxonomy derivation

The taxonomy was defined from this one description alone, by the
new-category method: read the description in full, define one
family per distinct function the prose actually names, draw each
family's patterns from the description's own phrases. No family
was imported from another category — in particular not from
Operations Management, the census's own boundary case — and no
family exists for a function the description does not name.

The description:

> S1. "NeuraBridge is intelligence software for high-precision
> manufacturing."
> S2. "It transforms engineering intent into structured,
> manufacturable decisions for aerospace and defense teams."

Families defined (4):

- `manufacturing_intelligence` — "intelligence software for
  high-precision manufacturing" (S1).
- `engineering_intent` — "engineering intent" (S2), the input
  the product works on.
- `intent_transformation` — "transforms engineering intent
  into" (S2), the transformation itself.
- `manufacturable_decisions` — "structured, manufacturable
  decisions" (S2), the output.

Two derivation decisions are recorded rather than smoothed over:

- **Sentence 1 carries a family here, unlike Set 20's
  positioning sentence.** BetterUp's sentence 1 named a market
  label ("Workforce Performance and Optimization platform") and
  no delivered function, and defined no family. NeuraBridge's
  sentence 1 states the software's functional kind —
  "intelligence software for high-precision manufacturing" —
  the same assertion the census rested the new category on. It
  is therefore a family, recorded at **identity-sentence
  weight** (it names what the software is; no mechanism,
  technique, or model is stated) and disposed **Extended**, so
  the weight is visible rather than hidden.
- **The audience phrase defined no family.** "for aerospace and
  defense teams" (S2) names who the software serves, not a
  function it performs. No aerospace or defense family exists;
  the phrase instead grounds a named absence below — nothing in
  the description states an export-control, ITAR, or
  classification-handling function, despite the defense
  audience.

Because the taxonomy is defined from exactly one two-sentence
description, every count in this spec is a floor over this set
only, and the taxonomy itself is provisional in the honest
sense: it is this set's own, and it becomes the category's
taxonomy if tiered Manufacturing forks ever appear — at which
point it will be tested against their prose the way every
founding taxonomy here has been tested against its remainder.

## Function ranking (by forks claiming, of 1)

Every family is claimed by the set's single fork, so the ranking
is a flat table of 4 families at 1 of 1. Dispositions: **Core**
means the merged build implements the records machinery for the
function; **Extended** means a named gap in GAPS.md, built later
if ever.

| Function | Disposition |
|----------|-------------|
| `manufacturing_intelligence` | Extended — the intelligence engine; claimed at identity-sentence weight |
| `engineering_intent` | Core — engineering intent records |
| `intent_transformation` | Core in records form — decision records carry the intent records they transform, validated by the basis guard; the transformation engine itself is Extended |
| `manufacturable_decisions` | Core — structured decision records; the build records decisions as stated and judges manufacturability not at all |

## The merged build — `manufacturing`

A fresh core in the house architecture (`src/manufacturing/`:
errors, access, audit, store, service, CLI), Python standard
library only. Demo identities are hooks, not an IdP: alice
(admin), bob (operator), carol (viewer).

1. **Organization registry** — tenant records keyed by an
   external reference. Substrate: every other record hangs off
   an organization. (The fork serves "aerospace and defense
   teams"; organizations are the teams' records form.)
2. **Engineering intent records** — label, the intent statement
   stored verbatim, and the author's opaque reference, per
   organization. **Status is derived at read, never stored**
   (`open` / `transformed`, computed by the single seam
   `_derive_intent_status` from whether any decision record
   cites the intent in its basis). (Core: `engineering_intent`.)
3. **Manufacturable decision records** — label, the decision
   statement stored verbatim, the decider's opaque reference, a
   decision moment, and the **basis**: the intent records the
   decision transforms. The basis is enforced by the
   decision-basis guard, the build's signature invariant,
   through the single seam `_check_decision_basis`: the basis
   must be non-empty, distinct, existing, and of the same
   organization, or the decision is refused, records nothing,
   and consumes no id. (Core: `manufacturable_decisions`,
   `intent_transformation` in records form.)
4. **Search** — literal substring search over organizations,
   intent records, and decision records. Substrate.
5. **Summary** — counts computed on read: organizations,
   intents by derived status, decisions. Counts only. Substrate
   surface over the core records.
6. **REST API** — the store over HTTP (X-User / X-Role
   headers); denied attempts audited with a `:denied` suffix;
   audit reads themselves audited. Substrate.
7. **Access control** — three-role permission matrix (admin /
   operator / viewer) enforced on every operation. Substrate.
8. **Audit log** — append-only (JSONL optional), recording
   every mutation. Substrate.

### Core-boundary decision (stated once)

The merged build implements **records machinery for the claimed
functions, and nothing else**. It performs no transformation (a
decision record *records* a transformation, as its basis links
to the intent records it rests on; the engine that converts
intent into decisions is Extended), it exercises no intelligence
(the `manufacturing_intelligence` family is Extended entire), and
it judges no manufacturability ("manufacturable" is the fork's
word for the kind of decision its software produces, carried in
the family name; a decision record states the decision as the
organization recorded it). It computes **no score, rating,
ranking, or rate** anywhere — the description's "high-precision"
is an adjective about manufacturing, not a computed quantity,
and no scoring vocabulary appears in it. It holds **no money
shape at all**: the description states no fees, prices, costs,
or budgets, so — as with the Event Management, Marketing &
Sales, and Talent Development builds — no money record was
forced into the design. And it holds **no personally identifying
information**: people appear only as opaque references validated
to be incapable of being an email address. Intent and decision
statements are caller-supplied engineering text stored verbatim
— the record of what the organization stated, the same treatment
the sibling builds give finding detail and settings text. The
decision-basis guard itself is this build's records-form rule
for the claimed transformation, stated here — it is not a claim
that the fork implements this exact check.

## Documented control claims

*This section replaces the baseline section of a tiered union
spec. With no tier, there is no baseline to inherit; what follows
is only what the fork's own description asserts, traced to its
sentences. A fork's documented control language is its claim,
never this build's attainment.*

**Documented: none.** Neither sentence contains any control
language at all — token-verified: "security", "access control",
"audit", "encrypt", and "single sign-on" occur nowhere in the
description, and no 800-53 family is asserted in any form. The
raw record's `deployment_model` ("Government-Only Cloud") is
record metadata outside the description; matching runs over the
description only, and a deployment model is platform metadata,
not a control claim — it is recorded as such and documents
nothing. Accordingly: AC, AU, IA, SC, CA, CM, IR, MA, MP, PE,
PL, PM, PS, RA, SA, SI are all **not documented** for this set,
and the build's own access/audit machinery is house substrate,
claimed against no fork.

## Named absences (token-verified in the description)

Functions a reader would expect in a category called
Manufacturing that the description does **not** state — each
verified absent at token level (the check is pinned by
`test_specs.py`):

- **Design authoring / CAD** — "design" occurs nowhere and no
  CAD token occurs. The software consumes engineering intent; it
  does not state a design tool.
- **Product lifecycle management (PLM)** — "lifecycle" occurs
  nowhere and no PLM token occurs.
- **Manufacturing execution (MES)** — "execution system" occurs
  nowhere and no MES token occurs. Nothing here runs a factory
  floor.
- **Quality management, inspection, metrology, tolerances** —
  "quality", "inspection", "metrology", and "tolerance" all
  occur nowhere. "High-precision" is the fork's adjective, not a
  stated quality or inspection function.
- **Machine control / CNC / machining operations** — "machining",
  "machine tool", and any CNC token occur nowhere.
- **Supply chain and inventory** — "supply" and "inventory"
  occur nowhere.
- **Production scheduling and planning** — "scheduling" and
  "production planning" occur nowhere.
- **Digital twin and simulation** — "twin" and "simulation"
  occur nowhere.
- **Robotics and sensor integration** — "robot" and "sensor"
  occur nowhere.
- **Maintenance and repair** — "maintenance" and "repair" occur
  nowhere.
- **Workflow and automation** — "workflow" and "automation"
  occur nowhere.
- **Analytics, dashboards, reporting** — "analytics",
  "dashboard", and "reporting" occur nowhere. The fork calls
  itself intelligence software; it states no analytics surface.
- **Export control / ITAR / classification handling** — "export"
  occurs nowhere and no ITAR token occurs. The audience is
  "aerospace and defense teams", and reputation or audience is
  not evidence: no defense-specific control function is stated,
  claimed, or built.
- **AI** — no standalone "AI" token occurs (regex-verified) and
  "artificial intelligence" occurs nowhere. The fork says
  "intelligence software"; it does not say AI, and no AI family
  was defined.
- **Scoring of any kind** — "score" and "scoring" occur nowhere;
  the build's no-score discipline is the description's own.
- **Money functions** — "price", "fee", "cost", and "budget"
  occur nowhere; the build holds no money shape.

## Exclusions, wording artifacts, and evidence notes

- **`certified_services` is never matched** (house method:
  matching runs over `service_desc` only). This fork's field is
  empty (`[]`), recorded in
  `scratch/certified_services_notes.json`.
- **Census citations are not automatically claims, in either
  direction — and this set runs the other way from Set 20.**
  The fork carries two census citations (its two sentences);
  both verify verbatim, and **both serve as claim evidence** —
  S1 is the evidence for `manufacturing_intelligence`, S2 for
  the other three families — because the census cited exactly
  the sentences the taxonomy derives from. In Set 20 both
  citations verified and neither served as evidence. Both
  directions are recorded as found; verification alone is still
  not what makes a sentence a claim — the taxonomy matches are.
- **No removals.** The raw pass produced 4 hits; no evidence
  sentence carries scope-exclusion phrasing, and all 4 stand.
- **No wording artifacts were found** — no family fired on a
  word used in another sense. In particular the patterns keep
  "manufacturing" and "manufacturable" distinct: sentence 1's
  "manufacturing" does not fire the decisions family, and
  sentence 2's "manufacturable" does not fire the intelligence
  family. Each family's hits are its defining phrases.
- **The description agrees across all three sources exactly** —
  the raw cache's `service_desc`, the census record in
  remainder/uncovered.json, and the sheet are byte-identical;
  vendor and product agree across the raw record, forks.json,
  and the census. No discrepancies were found.
- **One build-process correction, recorded:** an early spec-test
  pin was written against the census working copy's field
  spelling (`"NEW: Manufacturing"`, `new_category`) and failed
  against the shipped census record in remainder.json, which
  stores `proposed_category` as `"Manufacturing"` with
  `proposed_category_is_new`. The pin was corrected to the
  shipped record; the claim tables were unaffected.

## Gaps (registered in GAPS.md at ship)

The engineering-intent transformation engine — including the
manufacturing-intelligence engine entire (the build records a
transformation as a decision's basis links; the conversion of
intent into decisions, by whatever analysis the fork performs,
is the fork's and is not implemented here); and the platform
layer (the SaaS / Government-Only Cloud hosting the record
names) — platform metadata, as everywhere in this repo, is the
embedding organization's substrate, not a fork function.
