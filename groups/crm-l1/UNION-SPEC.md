# Union Spec — Customer Relations Management (CRM), CMMC L1 (DeadRamp Phase 2 remainder, CRM L1 singleton)

The singleton spec for the CRM category at the L1 tier: **1 fork,
FedRAMP LI-SaaS** — **Sprinklr CXM for Government (CXM)**
(Sprinklr, Inc.), FedRAMP Certified, SaaS, Public Cloud. Built under
the remainder census unit `new-singleton:Customer Relations
Management (CRM)|L1`.

**Membership provenance, stated plainly:** `forks.json` files this
fork "Uncategorized (none in source)" at tier L1 — its source
record carries an empty `business_categories` list and an empty
business-function segment in `filter_classes`. The DeadRamp
category is the **remainder census proposal**, taken from the
fork's own description ("helps organizations create, manage, and
optimize customer experiences…"; census classifier note: "Customer
experience management."). Reconciliation: `remainder.json` unit ==
`specs/specs.json` == {FR2035740126}, zero diff, and the fork's own
recorded fields (LI-SaaS, FedRAMP Certified, L1) match the source
record exactly. MAP.md's category arithmetic is unaffected: this
fork was never in MAP.md's CRM count, because MAP.md counts the
Phase 1 category field.

## Lineage: a cross-tier carry, downward (the Merge Rule applied across tiers)

This build does not start from zero. Its parents are:

1. The **Group 25 merged build** (`../crm-l2/`) — the union of the
   2 CRM L2 (FedRAMP Moderate) forks, a working clean-room CRM
   records service (10 core functions), whose taxonomy and
   substrate this category uses at every tier (Group 40, the
   L3-adjacent singleton, carried the same substrate **up** to
   High).
2. This singleton's **1 LI-SaaS fork**, via the spec sheet in
   `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents (Rule 1) — the category
substrate is carried whole, not stripped because one fork's
marketing prose is thin (a wording floor is not a downgrade, the
same reasoning Group 40 recorded in the upward direction). The
tier, however, is this fork's own: **LI-SaaS / L1**, the lightest
tier, and the baseline below is written **fresh for Low** (Rule 2
satisfied at the merged tier, which here is L1). Rule 3
traceability is this document plus the spec sheet; Rule 4's
SSDF-shaped process is the provenance here, the review recorded in
`scratch/ARTIFACTS.md`, and the verification record in
`tests/README.md` (full suite run by the builder; the signature
negative control mutation-verified live in this tree).

**What does NOT carry down, stated once:** Group 25's Moderate /
NIST SP 800-171 baseline citations stay in Group 25, and Group 40's
High uplifts (hash-chained audit, fail-closed audit writes, audit
query, logon lockout, auditor role) are **not** inherited downward —
they answer High-baseline demands that do not exist at Low/L1.
The implementation needs no downward modification at all: all 7
`src/` modules are byte-identical to Group 25's (hash record in
`scratch/reuse-note.md`), because the L2 build carries no
Moderate-specific machinery in code — its baseline lives in its
spec documents, not in the implementation.

## How functions were counted

Group 25's 18-family taxonomy was applied **verbatim** — parsed via
`ast` out of Group 25's shipped `scratch/extract.py` (never
executed, never re-typed) and asserted equal to Group 40's, so
counts are comparable across the category's tiers and nothing was
re-tuned to fit this one fork. Before the newcomer was tagged, the
extractor reproduced Group 25's two shipped claim tables exactly
from the raw cache (Oracle 3, WalkMe 5, 8 total). A family is
claimed only when the fork's own description contains matching
text; the first matching sentence is stored in `specs/specs.json`
as evidence. Source: GSA FedRAMP Marketplace dataset, cached at
`raw/data_dump.json` (produced by the General Services
Administration, last change 2026-10-22).

**Result: 1 claim.** `ai_scoring`, on sentence 2: "Sprinklr's
AI-backed core platform consists of five products: Modern
Marketing, Modern Advertising, Modern Research, Modern Care, and
Modern Engagement." The basis is recorded at its exact weight (full
record in `scratch/ARTIFACTS.md`): the sentence asserts an
**AI-backed core platform**; it asserts no scoring, no named model,
and no machine-learning function. The family's disposition in this
category is Extended, and it stays Extended — this build implements
no AI function and computes no score anywhere. Sentence 1 tags
nothing, and the fork's five own product names tag nothing
("Modern Marketing" is not "marketing automation"; "Modern
Research" does not fire the bare-word search pattern; "Modern Care"
is not "customer service"; "Modern Engagement" is neither
engagement pattern). Raw hits equal claims (1 = 1); nothing was
removed before matching — the source record's `certified_services`
is empty (asserted), and the product list is the fork's own
components, an in-scope enumeration, not a third-party catalogue.

**Census citation accounting:** the census recorded one citation
for this fork — sentence 1 — which verifies as a strict verbatim
substring and tags **no** family. The single claim rests on
sentence 2, which the census did not cite. Verification is not a
claim, in either direction; both facts are pinned in
`tests/test_singleton_spec.py` and `scratch/citation_check.json`.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | AI/ML models & scoring | **Extended** — claimed on the recorded thin basis ("AI-backed core platform"); no AI function built, no score computed anywhere |
| 2 | 0 | Account & contact records | **Core** (substrate) — carried, not claimed (0 claims in this category at any tier for the family itself; see core-boundary decision) |
| 2 | 0 | Customer service cases & service platform | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there); casework depth Extended |
| 2 | 0 | Interaction & activity records | **Core** (substrate) — carried, not claimed |
| 2 | 0 | User guidance & digital adoption | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there) |
| 2 | 0 | Gap & problem-area identification | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there) |
| 2 | 0 | Engagement & productivity tracking | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there, thin basis recorded there); analytics engines Extended |
| 2 | 0 | Modules, customization & codeless configuration | **Core** (records) — carried from the Group 25 union (claimed 2 of 2 there); customization engines Extended |
| 2 | 0 | Reporting & dashboards | Core (registry reporting) — carried, not claimed |
| 2 | 0 | Access control & RBAC | **Core** (baseline substrate) — carried, not claimed |
| 2 | 0 | Audit logging | **Core** (baseline substrate) — carried, not claimed |
| 2 | 0 | Search | **Core** (registry mechanics) — carried, not claimed |
| 2 | 0 | Hosting / SaaS delivery platform | Platform layer — 0 claims here (no verbatim hosting phrase in the description; the Public Cloud record field is record data, not text); the hosting platform itself is not a function of this build |
| 2 | 0 | Opportunities & sales pipeline | **Named absence** — 0 claims in this category at any tier; not built, not a gap (unclaimed) |
| 2 | 0 | Campaigns & audience lists | **Named absence** (claim level) — 0 claims at any tier; the fork's advertising/marketing product names are named as engines in the gaps, which does not retire the claim-level absence |
| 2 | 0 | Knowledge base & self-service content | Extended — named at 0 claims in this category |
| 2 | 0 | Marketing automation & email delivery | Extended — named at 0 claims here (the fork's "Modern Marketing" product name is not the family's phrase; the marketing platform itself is gap-named below from the description's own words) |
| 2 | 0 | Integrations & interoperability | Extended — connector engines; 0 claims here (no "integrat*" text in the description) |

Plus this singleton's own engines, named from its description's own
words (all Extended, detailed in Gaps below): the unified
customer-experience management platform itself; social media
management & publishing across the named channels; social
listening / research analytics (Modern Research); advertising
campaign management (Modern Advertising); care engagement depth
(Modern Care); engagement & messaging orchestration (Modern
Engagement); marketing platform functions (Modern Marketing); and
the AI-backed core (the claimed family, Extended).

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35/38/40 precedent).** This fork's single claim is an
Extended family, so **no core function below is claim-supported
for this fork**, yet all 10 core functions stand in this build. The
reasoning is the Merge Rule itself: the category substrate is the
union this fork's category presupposes, carried whole at the fork's
own tier. The presupposition is read at the level of the product's
operation and stated here as *interpretation, not evidence*: a
customer-experience platform operating across social, messaging,
email, and web channels for named organizations presupposes
account/contact records as its object model (→ registry),
interactions across those channels as its working record (→
interaction records), a care surface whose work is tracked (→ case
records), guidance and findings as its recorded by-products (→
guides, findings), configuration for its modules (→ module
registry), and review over all of it (→ reports, search, RBAC,
audit). Each step is a substrate function from Group 25's core;
none of them is this product's engine. The alternative — building
nothing at L1, or building only an "AI" stub around the one claim —
was considered and rejected: the category's L1 tier would carry no
substrate while every other tier carries it, and a stub around an
Extended family would invert the core/extended boundary. The price
of carrying the substrate is this disclosure and the coverage
statement's wording: **core carried, not claimed, for this fork.**
That price is paid in full, in both places.

**Named absences.** Opportunity/pipeline is claimed by **0 forks in
this category at any tier** — no sales vocabulary exists in any CRM
description built so far. Campaigns/audience lists likewise stand
at 0 claims at every tier (claim level; see the ranking note). They
are recorded so the union is complete and the absence is provable
from the record; they are not built and they are not gaps, because
nothing was claimed (the Group 21 precedent). If a future sibling
in this category claims them, they enter through its spec.

## The Core — what the build implements (10 functions, carried at the L1 baseline)

The same 10 functions as Group 25, carried whole:

1. **Account & contact registry** — accounts (`acct-`) and contacts
   (`ct-`, each under an account) keyed by a required, unique,
   **opaque caller-supplied `reference`**, with an optional
   caller-chosen `label` and free-form attributes. Carried, not
   claimed.
2. **Service case records & lifecycle** — cases (`case-`), typed
   (inquiry/problem/request/feedback/general), with account/contact
   links (a contact linked with an account must belong to it), an
   opaque `assignee_ref`, priority, and an optional `due_at`.
   Lifecycle `open → in_progress → resolved → closed` (plus
   `cancelled`; `resolved` may reopen). Breach is **derived at read
   time, never stored**:
   `breached = now > due_at and status not in (resolved, closed, cancelled)`.
   Carried from the Group 25 union.
3. **Interaction & activity records** — immutable records (`int-`)
   across guidance_session/call/chat/email/portal/in_person/system
   channels, with direction, outcome, summary, `external_ref`
   passthrough, and account/contact/case/guide links. No update or
   delete API exists. Carried, not claimed.
4. **Guidance content registry** — guides (`guide-`): title, kind
   (walkthrough/tooltip/checklist/announcement), an opaque
   `target_ref` naming the host surface, steps, enabled flag,
   versioned on update with full version history. Records only —
   the build renders nothing into any application. Carried from
   the Group 25 union.
5. **Gap-finding records** — findings (`find-`): title, `detail`
   text stored **verbatim** as supplied, severity, source, optional
   account link, lifecycle `open → acknowledged → addressed` (plus
   `dismissed`). No score is computed or stored anywhere;
   vendor-stated figures inside a finding's `detail` are records,
   stored verbatim, never aggregated. Carried from the Group 25
   union.
6. **Module / configuration registry** — modules (`mod-`): label,
   scope, `settings_text` stored verbatim (never executed), enabled
   flag, versioned on update. Writes are **admin-only**. Carried
   from the Group 25 union.
7. **Reports** — deterministic counts over the registry's own
   records: cases by status/type/account plus breached count at the
   report's `now`, interactions by channel/outcome, guides by
   kind/enabled, findings by severity/status, module and registry
   totals. Counts of records only — no scoring aggregate exists.
8. **Search** — literal case-insensitive substring search over
   accounts/contacts (label + reference), cases, interactions,
   findings, and guides.
9. **REST API** — the full surface over HTTP, with the house auth
   convention (X-User/X-Role against a demo registry; 401
   unknown/mismatched, 403 permission, denied attempts audited).
10. **Access control (RBAC) + audit log** — admin/operator/viewer
    matrix over 14 actions; `config_write` and `audit_read` are
    admin-only; enforced in the store before any mutation or id
    allocation, and again at the service layer. The audit log is
    append-only, JSONL-persistable, and records every mutation and
    every denied attempt (`<action>:denied`). Baseline substrate,
    carried not claimed.

**Privacy discipline (hard rule, inherited).** Accounts and
contacts are keyed by opaque caller-supplied references only. No
entity in this build has a field that can hold a real name, email,
phone number, SSN, date of birth, address, or salary figure — the
shapes are enforced by tests (`tests/test_privacy.py`), which also
assert that no score field and no scoring aggregate exists anywhere
in the build. For this fork the rule bites in a specific place: a
social/CX platform's real records are full of handles and message
content; this substrate holds **neither** — interaction records
carry a channel, a direction, an outcome, and a caller-written
summary, never a harvested post, handle, or profile.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this
  fork's impact level) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline.
  LI-SaaS is FedRAMP's tailored **subset** of that baseline for
  SaaS offerings, so the union baseline is the Low baseline itself,
  cross-walked to the FAR 52.204-21 basic-safeguarding practices
  that define CMMC L1. One fork at one tier plus the carried
  substrate, so no merge changes the tier (Merge Rules 1 and 2
  recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Account/contact registry | AC-3, CM-6, SI-10; IA-2 (hooks) | Records are explicit and keyed by opaque references; uniqueness and account linkage are enforced in the store; identity itself is supplied by the embedding organization |
| Cases & lifecycle | AU-2, AU-3 (Low side), CM-6 | Every case transition is an auditable event under a configured lifecycle; retention/disposition engines are Extended |
| Breach derivation | CM-6, AU-2/AU-3 (Low side) | Breach is derived at read from `due_at` and status against the report's `now`, never stored — reproducible from the records and the trail |
| Interactions | AU-2, AU-3 (Low side) | Immutable interaction records with content; review/search over them is Core |
| Guides registry | CM-6, SI-10 | Guides are versioned configuration records, validated on write, never executed or rendered by this build |
| Findings | AU-2, AU-3 (Low side), SI-10 | Finding records are stored verbatim with lifecycle; identification engines are Extended |
| Modules registry | CM-6, SI-10 | Modules are versioned configuration records; settings text is stored, never executed |
| Reports | AU-2, AU-3 (Low side) | Deterministic counts over the records, including derived breach at a stated `now`; no scoring aggregate |
| Search | AC-3 | Literal search over registered records only, permission-gated |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Three-role matrix enforced pre-mutation at two layers; `config_write`/`audit_read` admin-gated (traced to AC-3 — see precision notes) |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing is
  silently imported from the sibling tiers' tables):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and its
    LI-SaaS tailoring) carries the AU family — Group 25's AU-6
    (audit review) and AU-9 (protection of audit information)
    citations are Moderate selections and are **not** claimed here;
    AU-2/AU-3 only. Group 40's hash chain, fail-closed writes, and
    audit query (AU-5/AU-7/AU-9 uplifts) are High answers and are
    not inherited downward.
  - **Separation of duties / least privilege:** `config_write` and
    `audit_read` being admin-only is a design property of the
    carried substrate. Its Moderate-table family homes in Group
    25's spec were AC-5/AC-6, which are **not** Low-baseline
    selections, so at this tier the gating is traced to AC-3
    access enforcement, with AC-5/AC-6 named as lineage only.
  - **What else does not carry down:** Group 25's CA-7 (breach
    derivation row) and SA-4 (guides/modules rows) citations are
    Moderate selections and are not claimed here; Group 40's AC-7
    lockout and AC-5 auditor role are High answers, absent here by
    design (the demo registry has three roles, as at L2).
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence, and
  any real compliance claim still has to be earned inside each
  regime separately.

## Implementation contract (summary)

Identical to Group 25's — `src/crm/` (Python stdlib only):
`errors` (`CrmError`, `ValidationError`, `NotFoundError`,
`PermissionDenied`), `access` (User, admin/operator/viewer matrix),
`audit` (append-only AuditLog), `store` (CrmStore: the 10 core
functions; failed operations consume no ids; permission checks
precede mutation; the breach derivation lives in the single method
`_is_breached`), `service` (HTTP layer, demo registry alice=admin /
bob=operator / carol=viewer), `__main__` (`python -m crm serve`).
All 7 modules byte-identical to Group 25's (hash record in
`scratch/reuse-note.md`). `tests/`: see tests/README.md for the
test count and the negative-control record (the count is filled in
from the build, not stated here).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Sprinklr CXM for Government (CXM),
  LI-SaaS, its actual impact level recorded in the spec sheet;
  category by remainder-census proposal, provenance recorded).
- Claims evidenced for the fork: **1** of 18 families —
  `ai_scoring`, Extended, on the recorded basis ("AI-backed core
  platform"); no core function is claim-supported for this fork.
- Core implemented: **10 / 10** functions above — **carried as the
  category substrate under the core-boundary decision, not claimed
  as this fork's evidenced functions.** The distinction is the
  coverage statement, not a footnote to it.
- Tests: **108 run, 108 passed**, including the mutation-verified
  negative control performed against this group's tree
  (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its
description's own words — the platform's actual product surface,
none of it built here):

- Unified customer-experience management platform: creating,
  managing, and optimizing customer experiences across digital
  channels as one operating surface (the description's headline
  assertion and the census's classifier note; no taxonomy family
  covers CXM as such).
- Social media management & publishing: authoring, scheduling,
  and publishing to social channels, and operating brand presence
  on them.
- Social listening & research analytics (Modern Research):
  monitoring public conversation, research/insight analytics over
  it, and the reporting depth beyond record counts.
- Advertising campaign management (Modern Advertising): paid
  campaign planning, execution, and optimization across channels.
  (Named from the fork's own product list; the taxonomy's
  campaigns family remains unclaimed at claim level — see named
  absences.)
- Care engagement depth (Modern Care): agent workspaces, case
  automation, and customer-facing care channels beyond the case
  records substrate.
- Engagement & messaging orchestration (Modern Engagement):
  messaging-channel orchestration and engagement automation
  across social/messaging/email/web.
- Marketing platform functions (Modern Marketing): marketing
  operations beyond the records substrate (the taxonomy's
  marketing-automation family remains unclaimed at claim level).
- The AI-backed core (the claimed family, Extended): AI/ML models
  generally — including any sentiment analysis, scoring, or
  prediction models. This build computes no score and runs no
  model; the claim records the vendor's assertion, not a build
  feature.

Extended families carried from the Group 25 union, not implemented:

- Customer-service casework depth: knowledge-driven agent desktops,
  self-service portals, chat/chatbot channels, customer-facing
  engagement surfaces.
- Guidance delivery runtime: the in-application overlay engine
  that renders guidance inside third-party software and websites,
  including codeless authoring tooling.
- Gap-identification & adoption-analytics engines: live usage
  telemetry collection, gap/problem-area detection, engagement
  analytics and reporting beyond record counts.
- Customization & module engines: add-on module execution,
  codeless configuration runtimes.
- Knowledge base & self-service content (0 claims in this category).
- Marketing-automation engines & email delivery (0 claims at claim
  level in this category).
- Integration connector engines (0 claims here; no "integrat*"
  text in this fork's description either).

Platform layer (gap-listed, never implied closed): multi-tenancy
(the build is a single-tenant reference deployment); encryption at
rest (deployment layer); TLS only when a certificate is
configured; demo identities are hooks, not an IdP — IA-2 stays
with the embedding organization. The hosting/delivery platform is
the deployment layer itself, not a function of this build.

**Privacy note:** this build stores records and opaque
caller-supplied references only — no real names, emails, phone
numbers, social handles, or message content exist in any entity
shape, and finding details are stored verbatim, never scored.
