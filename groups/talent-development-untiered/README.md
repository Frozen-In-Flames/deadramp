# Talent Development — untiered (DeadRamp Phase 2, Untiered Set 20)

An **untiered set** of DeadRamp: forks whose FedRAMP impact level
is "Unknown" in the marketplace source. They carry no FedRAMP
baseline, so there is nothing to crosswalk: each fork's tier
stays `null`, no CMMC equivalence is drawn, and the merged build
is built to the forks' **documented control claims** only — the
control language their own descriptions actually use, traced in
UNION-SPEC.md, never filled in from a baseline.

Talent Development is also a **new category** for this repo: no
tiered group exists at any level, so there was no founding
taxonomy to inherit and no substrate to carry. The taxonomy
below was defined fresh from these two descriptions (the
new-category method used for Contract Management, Storage, and
Marketing & Sales), and the core was built fresh in the house
architecture. If tiered Talent Development forks ever appear,
this set's taxonomy becomes the category's taxonomy, tested
against their prose the way every founding taxonomy here has
been. This category is **not** Talent Management (a separate
category with its own tiered group), not Learning Management,
and not Education & Training — the census kept them separate
and so does this build.

## The forks (2)

| Fork | Vendor | Product | Status | Claims |
|------|--------|---------|--------|-------:|
| FR2318956176 | BetterUp, Inc. | BetterUp for Government | FedRAMP In Process | 2 |
| FR2635930421 | SOFware LLC | FORGE | Initial Implementation | 3 |

Spec sheets: `specs/specs.json`. Union analysis: `UNION-SPEC.md`.

The two forks describe different halves of the category that
meet only at the label, and their claim tables do not overlap at
all. **BetterUp for Government** is a workforce performance
platform whose description delivers two functions: performance-
driven behavioral and mindset development aligned to each
agency's goals, and a Partner Analytics Dashboard giving leaders
near real-time insights into behavioral trends "while fully
safeguarding the privacy of individual program participants" —
filed Uncategorized in the source, assigned here by the census
from its description. **FORGE** is a SaaS platform in AWS
GovCloud whose single sentence carries its whole function set:
workforce assessment, talent development, and organizational
decision-making — filed under Talent Development in the source
(with Talent Management, Education & Training, and Analytics
also listed as business categories; filed categories are
bookkeeping, not functions). 5 claims, each family carried by
exactly one fork, and zero zero-claim forks.

## Taxonomy (5 families, defined from these descriptions)

BetterUp-derived: `behavioral_mindset_development`,
`workforce_analytics`. FORGE-derived: `workforce_assessment`,
`talent_development`, `decision_support`. Each family's patterns
are drawn from its fork's own phrases; the derivation is stated
in full in UNION-SPEC.md. One derivation decision is recorded
there rather than smoothed over: the two development families
stay **separate** — talent development (FORGE's words) and
behavioral/mindset development (BetterUp's words) are different
functions as described, and neither fork claims the other's.
Because the taxonomy comes from exactly two descriptions, every
count here is a floor over this set only.

## The merged build — `talentdev`

A fresh core: Python standard library only, in `src/talentdev/`
(errors, access, audit, store, service, CLI). Twelve numbered
functions in UNION-SPEC.md: organization registry; development
program records whose kind is exactly one of the two claimed
development families; participation records with **status
derived at read, never stored**; assessment records and
assessment result records whose outcome is an administration
state only — the result shape carries **no numeric field at
all**, because neither description grounds a score; aggregate
insight snapshot records behind the **small-cohort guard** — a
snapshot over a cohort smaller than 5 is refused, the build's
signature invariant; decision records with a validated basis;
search and summary (counts only); a REST API; and access/audit
hooks.

The build delivers no development sessions, administers no
assessment, computes no trends, and makes no decisions: it is
the records machinery for the claimed functions, and the
engines behind them are named gaps. It holds **no money shape
at all**, because neither description states fees, prices,
budgets, or spend. People appear only as opaque references that
cannot be email addresses, and snapshots hold no person
reference at all — they are aggregates, which is what the
cohort guard protects.

## Running

Server (demo users alice/bob/carol via `X-User` / `X-Role`
headers):

    PYTHONPATH=src python3 -m talentdev serve --port 8765

Tests (58):

    PYTHONPATH=src python3 -m unittest discover -s tests

Demo users: alice (admin), bob (operator), carol (viewer). Demo
identities are hooks, not an IdP — authentication stays with the
embedding organization.

## Documented control claims

With no tier, there is no baseline section: UNION-SPEC.md
carries a **Documented control claims** section instead. Its
whole content is one prose-weight item — BetterUp asserts its
dashboard works "while fully safeguarding the privacy of
individual program participants", with no mechanism or framework
named, so no 800-53 family is documented by it — and an explicit
not-documented list covering every 800-53 family: neither
description contains access-control, identity/authentication,
audit, encryption, or even "security" language (token-
verified). FORGE's AWS GovCloud sentence is platform prose, not
a control claim. The build's small-cohort guard is its own rule,
taken from that privacy sentence as a design note; the build's
access and audit machinery is house substrate, claimed against
no fork. A fork's documented control language is its claim,
never this build's attainment.

## Honesty

- **Tier is null.** Both forks are "Unknown" in the source;
  nothing here assigns a tier, draws a CMMC equivalence, or
  asserts a baseline, and tests pin `cmmc_tier: null` on every
  sheet.
- **New category.** The taxonomy is this set's own, derived
  from two descriptions; the two halves (behavioral development
  + analytics, assessment + talent development + decision
  support) do not overlap, and that is stated rather than
  smoothed over. This category is not Talent Management,
  Learning Management, or Education & Training.
- **Every claim traces** to a fork's own description sentence,
  stored as evidence on its sheet. Matching ran over the
  descriptions only: the `certified_services` fields were never
  matched — FORGE's names the product itself and restates its
  three functions, so matching it would have changed nothing,
  and it was still not matched; the difference from sets where
  the field would have fabricated claims is recorded in
  UNION-SPEC.md and `scratch/`.
- **Census citations are not automatically claims** (in either
  direction, and both directions occur here): BetterUp's single
  citation verifies but cites its positioning sentence, which
  tags nothing; FORGE's single citation verifies but cites its
  complete sentence, while the claim evidence of record is that
  sentence's first fragment under the founding sentence split
  (the split cuts after "U.S."; recorded in
  `scratch/ARTIFACTS.md`).
- **Extended functions, by name:** live development delivery
  (the sessions behind a program, in whatever form — neither
  description names the form); assessment instruments and their
  administration and scoring engines; the analytics and
  trend-computation engine behind the dashboard; AI models (no
  fork describes one); and the platform layer (AWS GovCloud
  hosting), which is substrate, not a fork function.
- **Named absences** (token-verified in both descriptions): no
  coaching, no mentoring, no training, no courses or curricula,
  no learning/LMS function, no skills inventories, no competency
  models, no succession planning, no career pathing, no
  performance appraisal, no engagement measurement, no
  certification tracking, no feedback, no AI, no scoring. The
  category's most expected centre — coaching, the function
  BetterUp is known for in its market — is absent from its
  government description's prose, and reputation is not
  evidence.
