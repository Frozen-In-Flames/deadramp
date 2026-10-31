# Union Spec — Marketing & Sales, untiered (DeadRamp Phase 2, Untiered Set 18)

> **UNION-SPEC v1 — 2 forks spec'd under a taxonomy defined from
> their own descriptions; tier null.**
>
> This set is the remainder census's `untiered:Marketing & Sales`
> unit (REMAINDER.md, census commit `dbcdbf9`): the two forks whose
> FedRAMP impact level is "Unknown" in the source and whose
> function is marketing & sales. **Marketing & Sales has no tiered
> group anywhere in this repo** — no L1/L2/L3 sibling exists to
> inherit a taxonomy or a substrate from — so this set gets the
> new-category treatment (the Contract Management / Storage
> method): the taxonomy is derived from these forks' own
> descriptions, and the core is built fresh in the house
> architecture.
>
> Tier discipline: every fork records `fedramp_impact_level`
> exactly as the source has it — "Unknown" — and `cmmc_tier:
> null`. No tier is assigned, no CMMC equivalence is drawn, and no
> FedRAMP baseline is asserted anywhere in this set. The forks
> build to their documented control claims only (the section so
> titled below replaces the baseline section a tiered group's
> union spec would carry).

| Fork | Product | Status | Claims |
|------|---------|--------|-------:|
| FR2700857472 | CLEATUS (CLEATUS, Inc.) | Initial Implementation | 6 |
| FR2700857469 | Zeta Marketing Platform for Government (Zeta Global Corp.) | Initial Implementation | 7 |

**Total: 13 claims across 13 families. Zero-claim forks: 0.**

The registry filed CLEATUS under "Uncategorized (none in source)"
with no business categories at all, and Zeta under "Analytics"
with business categories [Analytics, Artificial Intelligence (AI),
Communication, Data Management, Marketing & Sales]. Both
assignments in this set are the census's, from the descriptions,
and each sheet records both the filed category and the census
assignment plainly. CLEATUS's census classifier note reads
"Government-contracting business development / capture pipeline";
Zeta's reads "Marketing platform; certified scope is outbound
email campaigns." Both notes are borne out by the claim tables.

## Taxonomy derivation

The taxonomy was defined from these two descriptions alone, by
the new-category method: read both descriptions in full, define
one family per distinct function the prose actually names, draw
each family's patterns from the descriptions' own phrases. No
family was imported from another category, and no family exists
for a function neither fork describes. The two forks describe two
different businesses that meet only at the category label —
government-contracting business development (CLEATUS) and an
outbound email marketing platform (Zeta) — so the taxonomy is
visibly two halves, and that is recorded rather than smoothed
over:

Families defined from CLEATUS's description (6):

- `opportunity_discovery` — "discover relevant government
  contracting opportunities".
- `opportunity_evaluation` — "evaluate" those opportunities.
- `capture_pipeline` — "manage their capture pipeline".
- `proposal_content` — "generate and refine proposal content".
- `workflow_automation` — "automate manual workflows".
- `ai_powered_support` — "an AI-powered platform".

Families defined from Zeta's description (7):

- `audience_segmentation` — "audience segmentation".
- `campaign_authoring` — "campaign creation".
- `campaign_scheduling` — "campaign scheduling".
- `outbound_email_delivery` — "outbound email" delivery, "email
  delivery" in the certified scope.
- `suppression_management` — "suppression management".
- `engagement_reporting` — "reporting" on the campaigns.
- `contact_lists` — "contact lists".

Because the taxonomy is defined from exactly two descriptions,
every count in this spec is a floor over this set only, and the
taxonomy itself is provisional in the honest sense: it is this
set's own, and it becomes the category's taxonomy if tiered
Marketing & Sales forks ever appear — at which point it will be
tested against their prose the way every founding taxonomy here
has been tested against its remainder.

## Function ranking (by forks claiming, of 2)

Every family is claimed by exactly one fork — there is no overlap
between the two descriptions at all — so the ranking is a flat
table of 13 families at 1 of 2, grouped by the fork that carries
them. Dispositions: **Core** means the merged build implements
the records machinery for the function; **Extended** means a
named gap in GAPS.md, built later if ever.

CLEATUS side:

| Function | Disposition |
|----------|-------------|
| `opportunity_discovery` | Core (opportunity records) |
| `opportunity_evaluation` | Core (evaluation records) |
| `capture_pipeline` | Core (pipeline records) |
| `proposal_content` | Core (content version records, metadata only) |
| `workflow_automation` | Core (workflow registry — records only, never executes) |
| `ai_powered_support` | Extended |

Zeta side:

| Function | Disposition |
|----------|-------------|
| `audience_segmentation` | Core (segment records) |
| `campaign_authoring` | Core (campaign records) |
| `campaign_scheduling` | Core (campaign records carry the schedule) |
| `outbound_email_delivery` | Core (delivery-outcome records; the sending transport itself is Extended) |
| `suppression_management` | Core (suppression records + the delivery gate) |
| `engagement_reporting` | Core (engagement records + derived count report) |
| `contact_lists` | Core (list records, counts only) |

## The merged build — `marketsales`

A fresh core in the house architecture
(`src/marketsales/`: errors, access, audit, store, service, CLI),
Python standard library only. Demo identities are hooks, not an
IdP: alice (admin), bob (operator), carol (viewer).

1. **Organization registry** — tenant records keyed by an
   external reference. Substrate: every other record hangs off
   an organization.
2. **Opportunity records** — external reference, agency and title
   labels, posted/due moments; references unique per
   organization. (Core: `opportunity_discovery`.)
3. **Evaluation records** — a decision from a fixed vocabulary
   (pursue / watch / no_pursue), an evaluator reference, an
   optional note. No score field exists. (Core:
   `opportunity_evaluation`.)
4. **Capture-pipeline records** — one entry per opportunity;
   stage moves only along a recorded transition map
   (identified → qualified → capture → proposal → submitted →
   awarded / not_awarded / no_bid). (Core: `capture_pipeline`.)
5. **Proposal-content version records** — item label, kind,
   version, size in bytes; versions unique per (opportunity,
   item); metadata only — no field can hold content text.
   (Core: `proposal_content`.)
6. **Workflow registry** — trigger and cadence labels, an active
   flag. Records only: registering or toggling a workflow runs
   nothing, and the package has no execution entry point.
   (Core: `workflow_automation`.)
7. **Contact-list records** — a label and a contact count.
   Counts only: no field can hold a contact. (Core:
   `contact_lists`.)
8. **Audience-segment records** — a label, a basis label, a
   member count. The segmentation engine that would compute
   membership is a gap. (Core: `audience_segmentation`.)
9. **Campaign records** — label, segment, list, optional
   scheduled moment. **Status is derived at read, never
   stored** (reported > delivered > scheduled > draft).
   (Core: `campaign_authoring`, `campaign_scheduling`.)
10. **Suppression records** — list, opaque contact reference,
    reason from a fixed vocabulary (unsubscribe / complaint /
    bounce / manual); at most one active suppression per
    (list, contact); release is a recorded state change.
    (Core: `suppression_management`.)
11. **Delivery-outcome records — behind the suppression gate.**
    Outcomes delivered / bounced / deferred. A `delivered`
    outcome is refused for a contact under an active
    suppression on the campaign's list; the refusal is the
    build's signature invariant, enforced through the single
    seam `_check_delivery_allowed`. (Core:
    `outbound_email_delivery`.)
12. **Engagement records** — kind from a fixed vocabulary
    (open / click / reply / unsubscribe), per campaign and
    contact reference. (Core: `engagement_reporting`.)
13. **Engagement report, search, summary** — derived count
    maps only; no rates, percentages, or scores anywhere.
    (Core: `engagement_reporting`.)
14. **REST API** — the store over HTTP (X-User / X-Role
    headers), including suppression-check and campaign-report
    endpoints; denied attempts audited with a `:denied`
    suffix; audit reads themselves audited.
15. **Access control and audit hooks** — three-role permission
    matrix enforced on every operation; append-only audit log
    (JSONL optional) recording every mutation.

### Core-boundary decision (stated once)

The merged build implements **records machinery for the claimed
functions, and nothing else**. It discovers nothing (opportunity
records are registered, never fetched — the live feeds and
search engines behind CLEATUS's discovery claim are a gap), it
computes no membership (segments record a stated basis and
count; the segmentation engine is a gap), it drafts no proposal
text (content records are version metadata; the generation
engine is a gap — and `ai_powered_support`, the one family whose
substance is a model, is Extended entire), it executes no
workflow (the registry records definitions only), and it sends
no email (delivery records state outcomes; the transport is a
gap). It computes **no score, grade, fit, ranking, or rate**
anywhere — neither description uses scoring vocabulary, and none
was invented; evaluation is a recorded decision, reporting is
counts. It holds **no money shape at all**: neither description
states fees, prices, budgets, or spend, so — as with the Event
Management singleton — no money record was forced into the
design. And it holds **no personally identifying information**:
contacts are opaque references validated to be incapable of
being an email address, lists and segments hold counts, and no
record anywhere can hold a name, an address, or message content.

## Documented control claims

*This section replaces the baseline section of a tiered union
spec. With no tier, there is no baseline to inherit; what follows
is only what the forks' own descriptions assert, each traced to
its fork and sentence. A fork's documented control language is
its claim, never this build's attainment.*

**Documented at prose weight (1 item):**

- **Data handling for Controlled Unclassified Information** —
  CLEATUS (FR2700857472): "Built for government contractors,
  CLEATUS processes, stores, and transmits Controlled
  Unclassified Information (CUI) and supports common business
  development workflows teaming and subcontractor coordination."
  The fork asserts CUI processing/storage/transmission. No
  mechanism is stated — no encryption, key management, or
  handling standard is named — so nothing further is traced:
  no 800-53 family is documented by this sentence, and the
  build neither holds CUI nor claims to.

**Not documented (every 800-53 family):** neither description
contains access-control language, identity or authentication
language (no SSO, no MFA — token-verified: "single sign-on" and
"sso" occur nowhere), audit language (token-verified: "audit"
occurs nowhere), or encryption language (token-verified:
"encrypt" occurs nowhere). Zeta's "multi-tenant SaaS solution"
sentence is a platform assertion, not a control claim, and is
recorded as such. CLEATUS's hosting sentence ("hosted on AWS
GovCloud with portions of the contractor's stack in AWS US East
and US West regions") is platform prose, not a control claim.
Accordingly: AC, AU, IA, SC, CA, CM, IR, MA, MP, PE, PL, PM, PS,
RA, SA, SI are all **not documented** for this set, and the
build's own access/audit machinery is house substrate, claimed
against no fork.

## Named absences (token-verified across both descriptions)

Functions a reader would expect in a category called Marketing &
Sales that **neither** description states — each verified absent
at token level in both descriptions (the check is pinned by
`test_specs.py`):

- **CRM / customer-relationship records** — "crm" and "customer
  relationship" occur nowhere. The category's most expected
  centre is absent from both forks.
- **Lead management** — "lead" occurs nowhere.
- **Advertising** — "advertis" occurs nowhere.
- **Social media** — "social" occurs nowhere.
- **SMS / text messaging** — "sms" and "text messag" occur
  nowhere; Zeta's certified scope is outbound email only, stated
  in its own sentence.
- **Search marketing / SEO** — "search engine" occurs nowhere.
- **Landing pages / web forms** — "landing page" occurs nowhere.
- **A/B testing** — "a/b test" occurs nowhere.
- **Personalization** — "personali" occurs nowhere.
- **Marketing analytics as a function** — "analytics" occurs
  nowhere in either description (Zeta is *filed* under Analytics
  in the registry; its description claims campaign reporting,
  not analytics). Filed category is not function.
- **Brand management** — "brand" occurs nowhere.
- **Events / webinars** — "webinar" and "event" occur nowhere.
- **Print / direct mail** — "print" and "direct mail" occur
  nowhere; the one physical-sounding channel is email.
- **Template management** — "template" occurs nowhere in either
  *description*. It is named in Zeta's `certified_services`
  field, which the house method never matches (below) — so it
  stands as an absence in the descriptions and a gap resting on
  the description rule, recorded with that caveat wherever it
  appears.
- **Scoring of any kind** — "score" and "scoring" occur nowhere;
  the build's no-score discipline is the descriptions' own.

## Exclusions, wording artifacts, and evidence notes

- **`certified_services` is never matched** (house method:
  matching runs over `service_desc` only). The exclusion matters
  concretely here. CLEATUS's field names Opportunity Discovery,
  Opportunity Finder (SAM.gov and other data source searching),
  Market Intelligence, Contract Breakdown, Proposal Writer,
  Pursuit Management, Contractor Teaming, GovCon Copilot (AI
  agents), AI Workflows, and API — matching it would have
  fabricated up to ten claims, including an entire market-
  intelligence family this taxonomy deliberately does not have.
  Zeta's field names campaign template management and bounce /
  complaint handling that its description never states. All of
  it is recorded in `scratch/certified_services_notes.json` and
  the affected functions appear as gaps, not claims.
- **Scope sentences:** CLEATUS's sentence 4 ("The system does
  not process classified information.") is a scope-exclusion
  sentence; it fired nothing and is recorded. Zeta's sentence 2
  ("The certified offering covers outbound email:") is the
  opposite shape — an affirmative scope statement that *is* the
  function list — and is the evidence sentence for six of Zeta's
  seven claims. The scope bound it states (email only) is what
  grounds the channel absences above.
- **Census citations are not automatically claims, in either
  direction:** CLEATUS's two census citations are verbatim-exact
  and both are claim evidence. Zeta's two citations verify only
  after whitespace normalization (its cached description carries
  literal newlines where the citations render spaces); of those,
  the first (the FedRAMP-positioning sentence) tags nothing and
  is not evidence for any claim, while the second is the
  evidence sentence for six families. All four verifications are
  pinned by test.
- **CLEATUS's first sentence** ("…helps small and mid-sized
  government contractors discover, evaluate, and manage their
  capture pipeline, proposal support, and business development
  workflows") tags discovery, evaluation, and pipeline; its
  "proposal support" phrase does not fire `proposal_content` —
  that claim rests on the second sentence's "generate and
  refine proposal content", at full weight.
- **Zeta's "reporting"** appears twice (sentences 2 and 4); the
  first-match rule keeps sentence 2 as the evidence of record.
- **No wording artifacts were found** — no family fired on a
  word used in another sense in either description. The raw pass
  produced 13 hits and all 13 stand.
- **`ai_powered_support` is claimed at exact weight:** CLEATUS
  calls itself "an AI-powered platform" and, in its unmatched
  services field, an agentic one — but its description names no
  model, agent, or inference function. The claim stands as the
  fork states it, and the family is Extended: the build contains
  no inference of any kind.

## Gaps (registered in GAPS.md at ship)

AI models and agents (the `ai_powered_support` substance);
live opportunity-discovery feeds and contract-search engines;
market intelligence and competitor/forecast analytics; the
proposal generation engine (the drafting itself); the workflow
execution engine; the segmentation engine (membership
computation); the email sending transport and deliverability
infrastructure; bounce and complaint handling automation (named
in Zeta's `certified_services`, absent from its description —
the gap rests on the description rule); campaign template
management (same caveat); preference management (same caveat);
and the platform layer both forks describe (hosting, multi-
tenancy) — platform prose, as everywhere in this repo, is the
embedding organization's substrate, not a fork function.
