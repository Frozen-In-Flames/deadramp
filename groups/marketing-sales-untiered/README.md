# Marketing & Sales — untiered (DeadRamp Phase 2, Untiered Set 18)

An **untiered set** of DeadRamp: forks whose FedRAMP impact level
is "Unknown" in the marketplace source. They carry no FedRAMP
baseline, so there is nothing to crosswalk: each fork's tier
stays `null`, no CMMC equivalence is drawn, and the merged build
is built to the forks' **documented control claims** only — the
control language their own descriptions actually use, traced in
UNION-SPEC.md, never filled in from a baseline.

Marketing & Sales is also a **new category** for this repo: no
tiered group exists at any level, so there was no founding
taxonomy to inherit and no substrate to carry. The taxonomy
below was defined fresh from these two descriptions (the
new-category method used for Contract Management and Storage),
and the core was built fresh in the house architecture. If
tiered Marketing & Sales forks ever appear, this set's taxonomy
becomes the category's taxonomy, tested against their prose the
way every founding taxonomy here has been.

## The forks (2)

| Fork | Vendor | Product | Status | Claims |
|------|--------|---------|--------|-------:|
| FR2700857472 | CLEATUS, Inc. | CLEATUS | Initial Implementation | 6 |
| FR2700857469 | Zeta Global Corp. | Zeta Marketing Platform for Government | Initial Implementation | 7 |

Spec sheets: `specs/specs.json`. Union analysis: `UNION-SPEC.md`.

The two forks describe two different businesses that meet only
at the category label. **CLEATUS** is a government-contracting
business-development platform: discovering and evaluating federal
contracting opportunities, managing a capture pipeline, and
generating proposal content, with workflow automation — filed
Uncategorized in the source, assigned here by the census from
its description. **Zeta** is an outbound email marketing
platform whose certified scope its own description bounds to
email: audience segmentation, campaign creation and scheduling,
suppression management, reporting, and contact lists — filed
under Analytics in the source. Their claim tables do not overlap
at all: 13 claims, each family carried by exactly one fork, and
zero zero-claim forks.

## Taxonomy (13 families, defined from these descriptions)

CLEATUS-derived: `opportunity_discovery`,
`opportunity_evaluation`, `capture_pipeline`, `proposal_content`,
`workflow_automation`, `ai_powered_support`. Zeta-derived:
`audience_segmentation`, `campaign_authoring`,
`campaign_scheduling`, `outbound_email_delivery`,
`suppression_management`, `engagement_reporting`, `contact_lists`.
Each family's patterns are drawn from its fork's own phrases;
the derivation is stated in full in UNION-SPEC.md. Because the
taxonomy comes from exactly two descriptions, every count here
is a floor over this set only.

## The merged build — `marketsales`

A fresh core: Python standard library only, in `src/marketsales/`
(errors, access, audit, store, service, CLI). Fifteen numbered
functions in UNION-SPEC.md: organization registry; opportunity,
evaluation, pipeline, and proposal-content version records;
workflow registry (**records only — it never executes**);
contact-list and segment records (counts only); campaign records
with **status derived at read, never stored**; suppression
records; delivery-outcome records behind the **suppression
gate** — a `delivered` outcome is refused for a contact under an
active suppression on the campaign's list, the build's signature
invariant; engagement records and a derived count-only report;
search and summary; a REST API; and access/audit hooks.

The build discovers nothing, computes no segment membership,
drafts no proposal text, executes no workflow, and sends no
email: it is the records machinery for the claimed functions,
and the engines behind them are named gaps. It computes no
score, grade, fit, ranking, or rate anywhere — neither
description uses scoring vocabulary — and it holds **no money
shape at all**, because neither description states fees, prices,
budgets, or spend. Contacts are opaque references that cannot be
email addresses; no record can hold a name, an address, proposal
text, or message content.

## Running

Server (demo users alice/bob/carol via `X-User` / `X-Role`
headers):

    PYTHONPATH=src python3 -m marketsales serve --port 8765

Tests (70):

    PYTHONPATH=src python3 -m unittest discover -s tests

Demo users: alice (admin), bob (operator), carol (viewer). Demo
identities are hooks, not an IdP — authentication stays with the
embedding organization.

## Documented control claims

With no tier, there is no baseline section: UNION-SPEC.md
carries a **Documented control claims** section instead. Its
whole content is one prose-weight item — CLEATUS asserts that it
"processes, stores, and transmits Controlled Unclassified
Information (CUI)", with no mechanism stated, so no 800-53
family is documented by it — and an explicit not-documented
list covering every 800-53 family: neither description contains
access-control, identity/authentication, audit, or encryption
language (token-verified). The build's own access and audit
machinery is house substrate, claimed against no fork. A fork's
documented control language is its claim, never this build's
attainment.

## Honesty

- **Tier is null.** Both forks are "Unknown" in the source;
  nothing here assigns a tier, draws a CMMC equivalence, or
  asserts a baseline, and tests pin `cmmc_tier: null` on every
  sheet.
- **New category.** The taxonomy is this set's own, derived
  from two descriptions; the two halves (capture management,
  email marketing) do not overlap, and that is stated rather
  than smoothed over.
- **Every claim traces** to a fork's own description sentence,
  stored as evidence on its sheet. Matching ran over the
  descriptions only: the `certified_services` fields were never
  matched — CLEATUS's would have fabricated up to ten claims,
  including a market-intelligence family this taxonomy
  deliberately does not have — and the difference is recorded
  in UNION-SPEC.md and `scratch/`.
- **Census citations are not automatically claims** (in either
  direction): Zeta's positioning citation verifies but tags
  nothing; its scope citation is the evidence for six families.
- **Extended functions, by name:** AI models and agents; live
  opportunity-discovery feeds and contract-search engines;
  market intelligence and competitor/forecast analytics; the
  proposal generation engine; the workflow execution engine;
  the segmentation engine; the email sending transport and
  deliverability infrastructure; bounce/complaint handling
  automation, campaign template management, and preference
  management (each named in Zeta's `certified_services` but
  absent from its description — gaps resting on the
  description rule); and the platform layer (hosting,
  multi-tenancy), which is substrate, not a fork function.
- **Named absences** (token-verified in both descriptions): no
  CRM, no leads, no advertising, no social, no SMS, no search
  marketing, no landing pages, no A/B testing, no
  personalization, no analytics function, no brand management,
  no events/webinars, no print/direct mail, no scoring. The
  category's most expected centre — CRM — is absent from both
  forks' prose.
