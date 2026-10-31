# Union Spec — Talent Development, untiered (DeadRamp Phase 2, Untiered Set 20)

> **UNION-SPEC v1 — 2 forks spec'd under a taxonomy defined from
> their own descriptions; tier null.**
>
> This set is the remainder census's `untiered:Talent Development`
> unit (REMAINDER.md): the two forks whose FedRAMP impact level is
> "Unknown" in the source and whose function is talent
> development. **Talent Development has no tiered group anywhere
> in this repo** — no L1/L2/L3 sibling exists to inherit a
> taxonomy or a substrate from — so this set gets the
> new-category treatment (the Contract Management / Storage /
> Marketing & Sales method): the taxonomy is derived from these
> forks' own descriptions, and the core is built fresh in the
> house architecture.
>
> Talent Development is a **different category** from Talent
> Management (which has a tiered group), from Learning
> Management, and from Education & Training. The census kept
> them separate and so does this build: no taxonomy, doctrine,
> or code was borrowed from any of them.
>
> Tier discipline: every fork records `fedramp_impact_level`
> exactly as the source has it — "Unknown" — and `cmmc_tier:
> null`. No tier is assigned, no CMMC equivalence is drawn, and
> no FedRAMP baseline is asserted anywhere in this set. The forks
> build to their documented control claims only (the section so
> titled below replaces the baseline section a tiered group's
> union spec would carry).

| Fork | Product | Status | Claims |
|------|---------|--------|-------:|
| FR2318956176 | BetterUp for Government (BetterUp, Inc.) | FedRAMP In Process | 2 |
| FR2635930421 | FORGE (SOFware LLC) | Initial Implementation | 3 |

**Total: 5 claims across 5 families. Zero-claim forks: 0.**

The registry filed BetterUp under "Uncategorized (none in
source)" with no business categories at all, and FORGE under
"Talent Development" with business categories [Talent
Development, Talent Management, Education & Training,
Analytics]. Both assignments in this set are the census's, from
the descriptions, and each sheet records both the filed category
and the census assignment plainly. FORGE's filed categories name
three other categories (Talent Management, Education &
Training, Analytics) — filed categories are the source's
bookkeeping, not functions, and none of them was treated as one.
BetterUp's census classifier note reads "Workforce performance /
behavioral and mindset development platform"; FORGE's reads
"Single-sentence description." Both notes are borne out by the
claim tables: BetterUp's delivered functions are its behavioral
development and its analytics dashboard, and FORGE's entire
function set is in its one sentence.

## Taxonomy derivation

The taxonomy was defined from these two descriptions alone, by
the new-category method: read both descriptions in full, define
one family per distinct function the prose actually names, draw
each family's patterns from the descriptions' own phrases. No
family was imported from another category — in particular not
from Talent Management, Learning Management, or Education &
Training — and no family exists for a function neither fork
describes. Both descriptions are short (BetterUp: three
sentences; FORGE: one), and the two forks describe different
halves of the category that share no family at all:

Families defined from BetterUp's description (2):

- `behavioral_mindset_development` — "behavioral and mindset
  development" (sentence 2).
- `workforce_analytics` — the "Partner Analytics Dashboard
  (PAD)", "near real-time insights into emerging behavioral
  trends across their workforce" (sentence 3).

Families defined from FORGE's description (3):

- `workforce_assessment` — "workforce assessment".
- `talent_development` — "talent development".
- `decision_support` — "organizational decision-making".

Two derivation decisions are recorded rather than smoothed over:

- **The two development families are kept separate.** FORGE
  names development of *talent*; BetterUp names development of
  *behavior and mindset*. Merging them into one family would let
  each fork claim a development function in words it did not
  use, so each stands on its own phrase — and the spec tests pin
  that neither fork claims the other's development family, and
  that each development phrase is absent from the other fork's
  description. The merged core implements both as one
  program-records machinery with the kind recorded as a label;
  the kinds are not merged in the data.
- **BetterUp's sentence 1 defined no family.** "Workforce
  Performance and Optimization platform" is platform positioning
  prose: it names no delivered function verb, and its delivered
  functions are sentences 2 and 3. Performance management in the
  appraisal sense is therefore a named absence below, not a
  family.

Because the taxonomy is defined from exactly two descriptions,
every count in this spec is a floor over this set only, and the
taxonomy itself is provisional in the honest sense: it is this
set's own, and it becomes the category's taxonomy if tiered
Talent Development forks ever appear — at which point it will be
tested against their prose the way every founding taxonomy here
has been tested against its remainder.

## Function ranking (by forks claiming, of 2)

Every family is claimed by exactly one fork — there is no
overlap between the two descriptions at all — so the ranking is
a flat table of 5 families at 1 of 2, grouped by the fork that
carries them. Dispositions: **Core** means the merged build
implements the records machinery for the function; **Extended**
means a named gap in GAPS.md, built later if ever. Every family
here has a records form, so every family is Core; the engines
behind the records are gaps, named below.

BetterUp side:

| Function | Disposition |
|----------|-------------|
| `behavioral_mindset_development` | Core (program + participation records, kind `behavioral_mindset_development`) |
| `workforce_analytics` | Core (aggregate insight-snapshot records behind the small-cohort guard; the trend-computation engine is Extended) |

FORGE side:

| Function | Disposition |
|----------|-------------|
| `workforce_assessment` | Core (assessment + result records; instruments and their administration are Extended) |
| `talent_development` | Core (program + participation records, kind `talent_development`) |
| `decision_support` | Core (decision records with a stated basis; the build decides nothing) |

## The merged build — `talentdev`

A fresh core in the house architecture (`src/talentdev/`:
errors, access, audit, store, service, CLI), Python standard
library only. Demo identities are hooks, not an IdP: alice
(admin), bob (operator), carol (viewer).

1. **Organization registry** — tenant records keyed by an
   external reference. Substrate: every other record hangs off
   an organization.
2. **Development program records** — label, kind from a fixed
   vocabulary of exactly the two claimed development families
   (`talent_development`, `behavioral_mindset_development`), and
   an optional goal label recording the agency goal the program
   is aligned to (BetterUp: development "aligned to each
   agency's unique goals" — the label records the alignment, it
   measures nothing). (Core: `talent_development`,
   `behavioral_mindset_development`.)
3. **Participation records** — program, participant by opaque
   reference, enrollment and completion moments; a participant
   may not be enrolled twice in one program. **Status is
   derived at read, never stored** (`enrolled` / `completed`,
   computed by the single seam `_derive_participation_status`).
   (Core: both development families.)
4. **Assessment records** — label and instrument label, per
   organization. (Core: `workforce_assessment`.)
5. **Assessment result records** — assessment, subject by
   opaque reference, administered moment, and an outcome from a
   fixed vocabulary of administration states only (`completed` /
   `partial` / `not_completed`). The shape carries **no numeric
   field at all**: nothing in either description grounds a score,
   and none was invented. (Core: `workforce_assessment`.)
6. **Insight snapshot records — behind the small-cohort
   guard.** Metric label, period label, cohort size, and the
   count of cohort members exhibiting the metric; aggregate
   counts only, no participant reference on the shape. A
   snapshot over a cohort smaller than 5 is refused, records
   nothing, and consumes no id; the refusal is the build's
   signature invariant, enforced through the single seam
   `_check_cohort_allowed`. (Core: `workforce_analytics`.)
7. **Decision records** — label, decision from a fixed
   vocabulary (`approved` / `deferred` / `declined`), the
   decider's opaque reference, and the basis: assessment and
   snapshot ids, each validated to exist and to belong to the
   same organization. The build records decisions; it makes and
   recommends none. (Core: `decision_support`.)
8. **Search** — literal substring search over organizations,
   programs, assessments, and decisions. Substrate.
9. **Summary** — counts computed on read: programs by kind,
   participations by derived status, results by outcome,
   decisions by decision. Counts only. Substrate surface over
   the core records.
10. **REST API** — the store over HTTP (X-User / X-Role
    headers); denied attempts audited with a `:denied` suffix;
    audit reads themselves audited. Substrate.
11. **Access control** — three-role permission matrix (admin /
    operator / viewer) enforced on every operation. Substrate.
12. **Audit log** — append-only (JSONL optional), recording
    every mutation. Substrate.

### Core-boundary decision (stated once)

The merged build implements **records machinery for the claimed
functions, and nothing else**. It delivers no development (the
sessions, coaching or otherwise, behind a program are Extended —
and neither description even names coaching), it administers no
assessment (instruments and their administration/scoring engines
are Extended; result records carry the administration outcome
only), it computes no trends (snapshots are recorded aggregates;
the analytics engine behind a live dashboard is Extended), and
it makes no decisions (decision records state a decision and its
basis; the judgment is the organization's). It computes **no
score, rating, ranking, or rate** anywhere — neither description
uses scoring vocabulary, and none was invented; the result
record shape has no numeric field, pinned by test. It holds
**no money shape at all**: neither description states fees,
prices, budgets, or spend, so — as with the Event Management and
Marketing & Sales builds — no money record was forced into the
design. And it holds **no personally identifying information**:
people appear only as opaque references validated to be
incapable of being an email address, and insight snapshots hold
no person reference at all, because they are aggregates — which
is what the small-cohort guard protects. The guard itself
(cohort floor of 5) is this build's own rule, grounded in
BetterUp's privacy sentence as a design note; it is not a claim
that any fork implements a cohort floor.

## Documented control claims

*This section replaces the baseline section of a tiered union
spec. With no tier, there is no baseline to inherit; what follows
is only what the forks' own descriptions assert, each traced to
its fork and sentence. A fork's documented control language is
its claim, never this build's attainment.*

**Documented at prose weight (1 item):**

- **Privacy safeguarding of individual participants** — BetterUp
  (FR2318956176): "Through the Partner Analytics Dashboard
  (PAD), BUFG equips government leaders with near real-time
  insights into emerging behavioral trends across their
  workforce, while fully safeguarding the privacy of individual
  program participants." The fork asserts privacy safeguarding
  for its analytics. No mechanism is stated — no framework,
  standard, or technique is named — so nothing further is
  traced: no 800-53 family is documented by this sentence. (The
  contrast is Set 11's: a fork that *names* HIPAA and NIST
  800-53 is documented at compliance-assertion weight; BetterUp
  names neither, so prose weight is the whole of it.) The build
  takes the sentence as a design note — aggregate-only snapshots
  behind a small-cohort guard — without claiming the build
  attains the fork's safeguarding.

**Not documented (every 800-53 family):** neither description
contains access-control language, identity or authentication
language (token-verified: "access control", "single sign-on",
and "sso" occur nowhere), audit language (token-verified:
"audit" occurs nowhere), encryption language (token-verified:
"encrypt" occurs nowhere), or even the word "security"
(token-verified: absent from both descriptions). FORGE's
"deployed in AWS GovCloud (US)" is a platform assertion, not a
control claim, and is recorded as such. Accordingly: AC, AU, IA,
SC, CA, CM, IR, MA, MP, PE, PL, PM, PS, RA, SA, SI are all **not
documented** for this set, and the build's own access/audit
machinery is house substrate, claimed against no fork.

## Named absences (token-verified across both descriptions)

Functions a reader would expect in a category called Talent
Development that **neither** description states — each verified
absent at token level in both descriptions (the check is pinned
by `test_specs.py`):

- **Coaching** — "coach" occurs nowhere. BetterUp is known in
  its market as a coaching platform; its government description
  here never says so, and reputation is not evidence. The build
  has no coaching function.
- **Mentoring** — "mentor" occurs nowhere.
- **Training** — "training" and "course" and "curriculum" occur
  nowhere. (FORGE is *filed* with Education & Training among its
  business categories; filed category is not function.)
- **Learning / LMS** — "learning" occurs nowhere. There is no
  learning-management family in this taxonomy, and this category
  is not Learning Management.
- **Skills inventories** — "skill" occurs nowhere.
- **Competency models** — "competen" occurs nowhere.
- **Succession planning** — "succession" occurs nowhere.
- **Career pathing** — "career" occurs nowhere.
- **Performance management (appraisal sense)** — "appraisal"
  occurs nowhere and "review" as a word occurs nowhere.
  "Performance" appears only inside BetterUp's positioning
  phrase ("Workforce Performance and Optimization") and its
  adjective "performance-driven" — neither states an appraisal
  function.
- **Employee engagement measurement** — "engagement" occurs
  nowhere.
- **Certification tracking** — "certif" occurs nowhere in either
  description.
- **Feedback** — "feedback" occurs nowhere.
- **AI** — "artificial intelligence" occurs nowhere, and no
  standalone "AI" token occurs (regex-verified). Unlike several
  sibling sets, no fork here claims an AI function, so there is
  no AI family and no AI gap resting on a claim.
- **Scoring of any kind** — "score" and "scoring" occur nowhere;
  the build's no-score discipline is the descriptions' own.

## Exclusions, wording artifacts, and evidence notes

- **`certified_services` is never matched** (house method:
  matching runs over `service_desc` only). BetterUp's field is
  empty. FORGE's field carries one entry naming the product
  itself — {"serviceName": "FORGE", "serviceDescription":
  "Cloud-hosted workforce assessment, talent development, and
  organizational decision-support capabilities."} — whose text
  restates the same three functions its description states.
  Matching it would have changed no claim (unlike CLEATUS in
  Set 18, where the field would have fabricated an entire
  family); it was still not matched, and the field is recorded
  in `scratch/certified_services_notes.json`.
- **The founding sentence split cuts FORGE's sentence.**
  FORGE's description is one sentence containing "U.S.", and the
  founding split (on sentence-ending punctuation) cuts it after
  "U.S.", leaving the fragment "government customers." All three
  of FORGE's claim phrases sit in the first fragment, which is
  the evidence of record on its sheet; no claim turns on the
  fragment. (The CMS untiered set recorded the same artifact
  class.)
- **Census citations are not automatically claims, in either
  direction — both directions occur in this set.** Each fork
  carries exactly one census citation, and both verify verbatim
  against the descriptions; neither serves as claim evidence.
  BetterUp's citation is its sentence 1 — the positioning
  sentence — which tags nothing. FORGE's citation is its
  complete sentence, while the claim evidence of record is that
  sentence's first fragment under the founding split (above), so
  the citation verifies but is not itself the stored evidence.
  All of this is pinned by test.
- **BetterUp's sentence 1** ("…is a Workforce Performance and
  Optimization platform designed specifically to help government
  organizations achieve their mission-critical objectives") is
  the uncited-by-claims positioning sentence: it fired no family
  and grounds the performance-management named absence.
- **No removals.** The raw pass produced 5 hits; no evidence
  sentence carries scope-exclusion phrasing, and all 5 stand.
- **No wording artifacts were found** — no family fired on a
  word used in another sense in either description. Each
  family's single hit is its defining phrase.

## Gaps (registered in GAPS.md at ship)

Live development delivery (the sessions behind a program —
coaching, facilitation, or any other delivery form; neither
description names the form); assessment instruments and their
administration and scoring engines (the build records
administrations and their outcomes; the instruments and their
judgments are the forks'); the analytics and trend-computation
engine behind the dashboard (the build records aggregate
snapshots; it computes no trends and renders no dashboard); AI
models (no fork describes one — listed for completeness with
the absence above, not as a claimed-function gap); and the
platform layer FORGE describes (AWS GovCloud hosting) —
platform prose, as everywhere in this repo, is the embedding
organization's substrate, not a fork function.
