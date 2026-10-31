# Union Spec — Customer Relations Management (CRM), untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Customer Relations
Management (CRM): **1 fork**, **tier null**. The member's FedRAMP
impact level is **Unknown** in the source dataset — the source
publishes no baseline for this offering — so no tier is assigned,
no CMMC equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The Documented control claims
section below replaces the baseline section a tiered group's
union spec carries.

Membership is exactly census unit `untiered:Customer Relations
Management (CRM)` in `../../remainder.json` (1 fork ID, verified
mechanically). Unlike most untiered sets, there is no
reclassification to record: `forks.json` files this fork under
Customer Relations Management (CRM) itself, and the census
proposal agrees with the filed category ("CRM explicitly named",
per the census classifier note). Its authorization status as
recorded is **Initial Implementation** — a status is record data,
not a claim.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence, the sheet recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`. Source:
GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product record joined by
FedRAMP ID. The description was present in the cached dataset and
matches `../../remainder/uncovered.json` exactly (1/1).

## How functions were counted

The category's fixed 18-function taxonomy was applied
**verbatim**: the extractor in `scratch/extract.py` AST-parses
the TAXONOMY literal out of the founding group's extractor
(`../../crm-l2/scratch/extract.py`, parsed, never executed) and
asserts it equals the taxonomy parsed the same way out of the
CRM L3 group's extractor — one taxonomy at all tiers of the
category, and at tier null. Taxonomy-verbatim proof: before
tagging this set, the extractor reproduced the founding group's
**original shipped claim tables exactly — 2 of 2 forks, 8 of 8
claims, deep-equal** against the sheets as shipped — using the
parent's sentence split and evidence rule (first matching
sentence, stored verbatim).

Exclusion discipline: the source record carries a **non-empty**
`certified_services` catalogue whose text asserts functions
("Sales pipeline management, revenue forecasting, analytics";
"AI-powered proposal drafting using Google Vertex AI") that the
marketplace description does not assert in matching text. Per the
house method (the FedHIVE exclusion; the CLEATUS and CodeSignal
lessons), that field was **never matched** — tagging ran on the
description only. Matching it would have fabricated an
`opportunity_pipeline` claim on the catalogue's "Sales pipeline"
phrase alone; the would-have-fired record is in
`scratch/certified_services_record.json` and the absence is
pinned by a spec test. A scope-exclusion scan of the
description's two sentences removed **no hits** — neither
sentence is an exclusion sentence. Wording artifacts and
near-misses are itemized in `scratch/ARTIFACTS.md`.

A function is claimed for the fork **only** when its own
description contains matching text; counts are a **floor**, not a
ceiling. **2 claims** on the set's single fork; the fork is **not**
a zero-claim fork.

Census citations: 1 citation is recorded for this fork in the
census; it **verifies under whitespace normalization only** (the
census stores the sentence with spaces where the source
description carries literal newlines — the raw-substring check
fails and is recorded as failing, in
`scratch/citation_check.json`), and it **is** the claim evidence
sentence for both claims. Verification is not a claim, in either
direction; here the two happen to coincide.

## Function ranking — the set's 1 fork

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 1) | Disposition in this build |
|---|---|---:|---|
| 1 | Account & contact records | 1 | **Core** — the account & contact registry; claim-supported in this set (see the core-boundary decision) |
| 1 | AI/ML models & scoring | 1 | Extended — claimed at **bare-token weight** only (see below); the build contains no model and computes no score |
| 3 | Customer service cases & service platform | 0 | Core substrate carried, not claimed in this set — **named absence** (no "customer service" text) |
| 3 | Interaction & activity records | 0 | Core substrate carried, not claimed in this set (founding core-boundary decision) |
| 3 | User guidance & digital adoption | 0 | Core records carried, not claimed in this set; the delivery runtime is Extended |
| 3 | Gap & problem-area identification | 0 | Core records carried, not claimed in this set; the identification engine is Extended |
| 3 | Engagement & productivity tracking | 0 | Core records carried, not claimed in this set; analytics engines Extended |
| 3 | Modules, customization & codeless configuration | 0 | Core registry carried, not claimed in this set; customization engines Extended |
| 3 | Reporting & dashboards | 0 | Core (registry reporting) carried, not claimed in this set; dashboard/analytics engines Extended |
| 3 | Access control & RBAC | 0 | Core substrate carried, not claimed in this set (baseline-neutral hooks at tier null) |
| 3 | Audit logging | 0 | Core substrate carried, not claimed in this set (baseline-neutral hooks at tier null) |
| 3 | Search | 0 | Core (registry mechanics) carried, not claimed in this set |
| 3 | Opportunities & sales pipeline | 0 | Extended — **named absence at pattern weight**: "pipeline forecasting" is asserted in substance and tags nothing; the forecasting engine is a gap in its own name (see ARTIFACTS.md). The catalogue's "Sales pipeline management" was never matched |
| 3 | Campaigns & audience lists | 0 | **Named absence** — 0 of 1; no campaign vocabulary exists in the description |
| 3 | Knowledge base & self-service content | 0 | Extended — named at 0 claims here |
| 3 | Marketing automation & email delivery | 0 | Extended — named at 0 claims here ("document automation" is a different function with no family; a gap in its own name) |
| 3 | Integrations & interoperability | 0 | Extended — connector engines; 0 claims here, no "integrat…" text |
| 3 | Hosting / SaaS delivery platform | 0 | Platform layer — "cloud-based" prose recorded as a near-miss; the family's recorded phrases do not occur |

**The ai_scoring claim, at its exact weight.** The fork's first
sentence fires the family's `\bAI\b` pattern ("VirtualDojo AI
CRM", "AI-powered proposal generation") — the same bare-token
shape as the CRM L1 singleton's claim ("AI-backed core
platform"). What the sentence asserts is an AI-powered platform
and one named AI function, proposal generation; it asserts no
scoring, no named model, and no machine-learning function, and
none of the family's other patterns (machine learning, predictive,
lead scoring, sentiment) fires anywhere. The claim stands at
exactly that weight, the family stays Extended, and the build
computes no score anywhere — the category's no-score rule is
test-enforced. Proposal generation itself has no family in the
taxonomy; it is registered below as a gap in its own name.

## The Core — what this build implements (10 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's ten-function substrate **whole** — account &
contact registry; service case records & lifecycle (breach
**derived at read time, never stored**); interaction & activity
records; guidance content registry; gap-finding records; module /
configuration registry; reports; search; REST API; access control
(RBAC) + audit log. The substrate is records machinery, and it is
tier-independent code: the founding build's source contains no
tier or baseline machinery, so there was nothing tier-shaped to
strip — and in particular the CRM L3 singleton's High uplifts
(hash-chained audit, fail-closed writes, logon lockout, and the
rest of its uplift set) are **not** inherited here; this set
carries the L2 founding substrate as-is. Where the founding
contract's text says baseline substrate for access control and
audit, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline.

Claim support in this set, stated per function: **one** of the
ten functions is claim-supported — the account & contact registry,
by `account_contact_registry` (the fork names "contact
management" in its own words; this is the first tier or set of
the category where the registry family is claimed rather than
carried, the L2 founding group having recorded it at 0 of 2 as
substrate). The other nine are **carried, not claimed**: case
records (the founding group's claim was Oracle's "customer
service" prose; this fork's description contains none),
interaction records (substrate under the founding core-boundary
decision, and untagged here too), guidance, findings, modules,
reports, search, the API surface, and the access/audit hooks —
none has a claiming family in this set. The `ai_scoring` claim
supports **no** core function: its disposition is Extended.
Functions are **carried** as substrate; the one claim that
supports a function is recorded above, and no function is claimed
to be *attained* by the fork — the build is the merged open
implementation, not the fork's product.

The carried code is **byte-identical** to the founding group's
`src/crm/` (7 modules; SHA-256 accounting in this group's README
and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `crm` under `src/`, ids sequential per object type
with fixed prefixes (`acct-`, `ct-`, `case-`, `int-`, `guide-`,
`find-`, `mod-`), failed operations consume no id and change
nothing, permission checks precede mutation, roles
`admin|operator|viewer` with the founding 14-action permission
matrix, and the audit log append-only with denied attempts
recorded.

**Privacy discipline (hard rule of this build, carried from the
founding spec).** Accounts and contacts are keyed by opaque
caller-supplied references only. No entity in this build has a
field that can hold a real name, email, phone number, SSN, date
of birth, address, or salary figure — the shapes are enforced by
tests (`tests/test_privacy.py`), which also assert that no score
field and no scoring aggregate exists anywhere in the build.
This matters here in a specific way, recorded plainly: the fork's
own description asserts that the product stores **customer PII**
(as part of its CUI statement). That is the fork's assertion
about its product; the build stores none of it and no record
shape can.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering ("Unknown"), so this build
asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own
marketplace description asserts, in its own words. A documented
control claim is a **fork's claim about itself**, recorded here
with its evidence; it is not the build's control attainment, and
nothing in this section fills a family in from any baseline.

Control areas **documented** by the fork in this set: **none at
family weight.** No taxonomy family carrying control language
fires — `access_control` tags 0 and `audit_logging` tags 0 — and
the description contains no access-control, audit, encryption, or
authentication language of any kind.

At **prose weight only**, one data statement is recorded: the
fork's second sentence asserts the platform is for "storing
Controlled Unclassified Information (CUI) including government
contract data, customer PII, proposal documents, and
financial/pricing data." That is a statement about what data the
offering handles, naming **no mechanism and no framework**, so it
documents no 800-53 family (the BetterUp precedent in Untiered
Set 20: an assertion without a mechanism documents nothing). It
is recorded because CUI handling is the fork's own framing of its
purpose — and because it draws the build's privacy boundary
(see above): the build's shapes hold opaque references only.

Control areas **not documented** by the fork in this set: every
NIST SP 800-53 control family — including AC, AU, IA, SC, CA, CM,
IR, MA, MP, PE, PL, PM, PS, RA, SA, and SI **as control claims** —
is asserted by no sentence in the description. If the source
later publishes an impact level for this offering, the tier is
recorded then and not before.

## Named absences

- **Customer service cases — 0 of 1.** The `case_service_records`
  family claimed the founding group's Oracle fork on "customer
  service" prose; this fork's description says "customer
  relationship management" throughout and never "customer
  service". A CRM description without the service phrase is
  recorded, not repaired.
- **Opportunities & sales pipeline — 0 of 1 at pattern weight,
  present in substance.** "Pipeline forecasting" is asserted and
  tags nothing (the family's patterns are the sales-side
  vocabulary); the catalogue's "Sales pipeline management" was
  never matched. Both facts stand together: the function is
  gapped in its own name, and no claim was manufactured for it.
- **Campaigns & audience lists — 0 of 1.** The founding group's
  other named absence stands here too: no campaign vocabulary
  exists in the description.
- **Access control and audit logging — 0 of 1 each.** The
  description is silent on both, even while asserting CUI
  storage; the substrate's hooks are carried, not claimed.
- **Hosting / SaaS delivery — 0 of 1.** "Cloud-based" prose only;
  the family's recorded phrases do not occur.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented
— restated here only where this set's fork claims or describes
them:

- [ ] AI proposal-generation engine (the AI function the description actually names; the `ai_scoring` claim stands at bare-token weight and no model of any kind is implemented)
- [ ] Pipeline forecasting engine (asserted in substance as "pipeline forecasting"; no taxonomy claim)
- [ ] Document automation engine (asserted in the description; no family in the taxonomy)
- [ ] Integration connector engines (0 claims here)
- [ ] Knowledge base & self-service content (0 claims here)
- [ ] Marketing-automation engines & email delivery (0 claims here)
- [ ] Platform layer (multi-tenancy — the build is a single-tenant reference deployment; encryption at rest is deployment layer; TLS only when a certificate is configured; demo identities are hooks, not an IdP — IA-2 stays with the embedding organization; the hosting/delivery platform is the deployment layer itself, not a function of this build)

## Coverage statement (for this build)

1 fork spec'd of 1 in census unit `untiered:Customer Relations
Management (CRM)`; 2 taxonomy claims tagged from the fork's own
description (the fork claiming at least one; not a zero-claim
fork); the ten-function substrate carried byte-identical from the
founding CRM L2 build and re-anchored to tier null; tier null
recorded on the sheet and pinned by tests. Nothing in this build
claims a FedRAMP authorization, a CMMC certification, or a control
baseline for the fork or for the build itself.
