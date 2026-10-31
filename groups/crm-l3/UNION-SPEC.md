# Union Spec — Customer Relations Management (CRM), CMMC L3-adjacent (DeadRamp Phase 2, Group 40 singleton)

The singleton spec for the CRM category at the L3-adjacent tier:
**1 fork, FedRAMP High** — Pega Cloud for Government (Pegasystems).
Reconciled zero-diff: `specs/specs.json` ↔ `forks.json`
category="Customer Relations Management (CRM)" +
cmmc_tier="L3-adjacent" (exactly one match) ↔ MAP.md's category
arithmetic (CRM totals 4 offerings = 2 at L2, shipped as Group 25 +
1 at L3-adjacent, this singleton + 1 untiered, VirtualDojo AI CRM
with impact Unknown and tier null, a remainder fork). MAP.md's
sibling sections list only groups of size 2+, so no sibling-section
diff applies to a singleton; forks.json exactness plus the category
arithmetic is the reconciliation, per the earlier singleton builds.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 25 merged build** (`../crm-l2/`) — the union of the 2
   CRM L2 (FedRAMP Moderate) forks, shipped as a working clean-room
   CRM records service (10 core functions).
2. This singleton's **1 High fork**, via the spec sheet in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run by
the builder, and both negative controls were mutation-verified by
patching the implementation (see tests/README.md).

**Reuse, stated explicitly:** this build reuses Group 25's own
open-source code (Apache-2.0, ours). One module is byte-identical to
Group 25 (`__init__.py`); six are modified for the tier uplift
(`errors.py` — AuditWriteError added; `access.py` — auditor role
added; `audit.py` — hash chain, fail-closed writes, and query added,
following the proven `groups/analytics-l3` mechanics;
`store.py` — snapshot fail-closed wrapper added, following
`groups/accounting-l3`; `service.py` — lockout, audit verify/query,
auditor user added; `__main__.py` — auditor user and lockout flags
added). No core function changed behavior: every Group 25 test
passes with only the documented uplift adaptations
(tests/README.md).

## How functions were counted — zero claims, honestly

Group 25's 18-family taxonomy was applied **verbatim** (same ids,
labels, and matching patterns, in `scratch/extract.py`) to this
fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22). A family is
claimed only when the offering's own description contains matching
text; the first matching sentence would be stored in
`specs/specs.json` as evidence.

**Result: 0 claims.** Pega's description is five sentences of
platform prose: a fully managed cloud for government agencies,
operational support for scaling applications to FedRAMP standards,
Pega Government Platform as a "no-code application development
solution" with "model-based design", an "agile, secure, unified
solution" for transformation, and the FedRAMP High authorization
statement. No sentence contains any taxonomy family's matching text.
The full description is preserved verbatim in the spec sheet, and no
function was invented for it. Counts are a floor, and here the floor
is zero — the same honest outcome as the zero-claim sheets in
Groups 28 and 35 and Singleton 38.

Near-misses, recorded in full in `scratch/ARTIFACTS.md`, not rounded
up: "no-code" is not the taxonomy's "codeless" (configuration
family, 0); "authorized FedRAMP High cloud service provider" is not
"authorized users" (access control, 0); Pega's managed-cloud wording
matches none of the verbatim hosting phrases (hosting, 0); the
source files this offering under Customer Service as its second
filter function, but the description contains no "customer service"
text (case family, 0); the raw record's `all_others` names —
Customer Decision Hub (CDH), GenAI Blueprint, Pega User Management
— are record fields, not description text, and tag nothing.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Modules, customization & codeless configuration | **Core** (records) — carried from the Group 25 union (claimed 2 of 2 there); Pega's own no-code engine is Extended (near-miss above) |
| 1 | 0 | Account & contact records | **Core** (substrate) — carried, not claimed (0 claims in either tier for the family itself; see core-boundary decision) |
| 1 | 0 | Customer service cases & service platform | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there); case-automation depth Extended |
| 1 | 0 | Interaction & activity records | **Core** (substrate) — carried, not claimed |
| 1 | 0 | User guidance & digital adoption | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there) |
| 1 | 0 | Gap & problem-area identification | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there) |
| 1 | 0 | Engagement & productivity tracking | **Core** (records) — carried from the Group 25 union (claimed 1 of 2 there, thin basis recorded there) |
| 1 | 0 | Reporting & dashboards | Core (registry reporting) — carried, not claimed |
| 1 | 0 | Access control & RBAC | **Core** (baseline substrate, uplifted to High) — carried, not claimed |
| 1 | 0 | Audit logging | **Core** (baseline substrate, uplifted to High) — carried, not claimed |
| 1 | 0 | Search | **Core** (registry mechanics) — carried, not claimed |
| 1 | 0 | Hosting / SaaS delivery platform | Platform layer — near-miss recorded; the hosting platform itself is not a function of this build |
| 1 | 0 | Opportunities & sales pipeline | **Named absence** — 0 claims in this category at either tier; not built, not a gap (unclaimed) |
| 1 | 0 | Campaigns & audience lists | **Named absence** — 0 claims at either tier; not built, not a gap (unclaimed) |
| 1 | 0 | Knowledge base & self-service content | Extended — named at 0 claims in this category |
| 1 | 0 | Marketing automation & email delivery | Extended — named at 0 claims in this category |
| 1 | 0 | AI/ML models & scoring | Extended — named at 0 claims here (but see the GenAI gap below, record-named) |
| 1 | 0 | Integrations & interoperability | Extended — connector engines; 0 claims here |

Plus this singleton's own engines, named from its prose and record
(all Extended, detailed in Gaps below): no-code / low-code
application development & model-based design; case management &
BPM / workflow execution (the platform's signature domain — the
description's "build applications" prose and the category it is
filed under, not a taxonomy claim); decisioning (Customer Decision
Hub, record-named in `all_others`); GenAI application tooling
(GenAI Blueprint, record-named); managed cloud operations &
application scaling platform.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35 precedent).** This fork tags zero claims, yet all 10
core functions stand in this build. The reasoning is the Merge Rule
itself, not convenience: a cross-tier merge takes the union of the
parents upward whole, and Group 25's union — the category substrate
this fork's category presupposes — is a parent of this build. A
wording artifact (a five-sentence platform description with no
taxonomy vocabulary) is not a downgrade, and stripping the substrate
at High because the High fork's marketing prose is thinner than the
Moderate forks' would dilute the union, which Rule 1 prohibits.
Every core function is therefore flagged **carried, not claimed**
for this tier, exactly as Groups 22, 23, and 35 flagged theirs.
Where the fork claims less than the substrate — which here is
everywhere — that is this paragraph, stated once and plainly,
rather than ten quiet exceptions.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 functions as Group 25, carried up whole:

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
   `target_ref`, steps, enabled flag, versioned on update with full
   version history. Records only — nothing is rendered into any
   application. Carried from the Group 25 union.
5. **Gap-finding records** — findings (`find-`): title, `detail`
   text stored **verbatim**, severity, source, optional account
   link, lifecycle `open → acknowledged → addressed` (plus
   `dismissed`). No score is computed or stored anywhere.
   Vendor-stated figures inside a finding's `detail` are records,
   stored verbatim, never aggregated. Carried from the Group 25
   union.
6. **Module / configuration registry** — modules (`mod-`): label,
   scope, `settings_text` stored verbatim (never executed), enabled
   flag, versioned on update. Writes are **admin-only**. Carried
   from the Group 25 union.
7. **Reports** — deterministic counts over the registry's own
   records (cases by status/type/account plus breached count at the
   report's `now`, interactions by channel/outcome, guides by
   kind/enabled, findings by severity/status, module and registry
   totals). Counts of records only — no scoring aggregate exists.
8. **Search** — literal case-insensitive substring search over
   accounts/contacts (label + reference), cases, interactions,
   findings, and guides.
9. **REST API** — the full surface over HTTP, with the house auth
   convention (X-User/X-Role against a demo registry; 401
   unknown/mismatched, 403 permission, denied attempts audited),
   uplifted with lockout (below).
10. **Access control (RBAC) + audit log** — admin/operator/viewer
    matrix over 14 actions **plus the auditor role** [L3];
    `config_write` and `audit_read` are admin-gated (operator holds
    neither; the auditor holds `audit_read` and nothing else);
    enforced in the store before any mutation or id allocation,
    and again at the service layer. The audit log is append-only,
    **hash-chained**, JSONL-persistable, **fail-closed**, and
    **queryable** [L3], and records every mutation and every
    denied attempt (`<action>:denied`).

**Privacy discipline (hard rule, inherited).** Accounts and
contacts are keyed by opaque caller-supplied references only. No
entity has a field that can hold a real name, email, phone number,
SSN, date of birth, address, or salary figure — enforced by tests
(`tests/test_privacy.py`), which also assert that no score field
and no scoring aggregate exists anywhere in the build.

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. The cross-tier parent (Group 25's build)
  sat at Moderate; the union baseline is therefore the High
  baseline, un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3 is
  not identical to FedRAMP High; it is the same assurance weight
  class.
- **Feature → control family mapping (carried from Group 25):**

  | Core function | Control families | How the build answers |
  |---|---|---|
  | Account/contact registry | AC-3, AC-6, IA-2 (hooks) | Records keyed by opaque references; uniqueness and account linkage enforced in the store |
  | Cases & lifecycle | AU-2, CM-6, SI-12 (partial) | Every transition is an auditable event under a configured lifecycle; retention/disposition engines are Extended |
  | Breach derivation | AU-6, CA-7, CM-6 | Derived at read from `due_at` and status against the report's `now`, never stored |
  | Interactions | AU-2, AU-3, SI-12 (partial) | Immutable records with content; review/search is Core, retention engines Extended |
  | Guides registry | CM-6, SA-4 | Versioned configuration records, never executed or rendered |
  | Findings | AU-2, AU-6, SI-12 (partial) | Records stored verbatim with lifecycle; identification engines are Extended |
  | Modules registry | CM-6, SA-4 | Versioned configuration records; settings text stored, never executed |
  | Reports | AU-6 | Deterministic counts, including derived breach at a stated `now`; no scoring aggregate |
  | Search | AU-6, SI-12 (partial) | Literal search over records supports review |
  | RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Four-role matrix enforced pre-mutation at two layers; auditor role separates audit review (AC-5) |
  | Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only, hash-chained, fail-closed, queryable log including denied attempts; no mutation API |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Group 25, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only: **FedRAMP authorizes
  products; CMMC certifies organizations** — the build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither regime accepts the other as evidence. Any real compliance
  claim still has to be earned inside each regime separately.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (0 tagged claims; full description
  preserved; near-misses itemized in `scratch/ARTIFACTS.md`).
- Core implemented: **10 / 10** functions above, at the High
  baseline; 6 tier uplifts implemented (hash-chained audit,
  fail-closed audit writes with store rollback, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor role).
- Tests: **144** (96 inherited from Group 25, 8 added inside
  inherited files, 40 in new uplift files); two negative controls,
  both mutation-verified live (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its prose and
record — the platform's actual product surface, none of it built
here):

- No-code / low-code application development engine & model-based
  design tooling (the description's central assertion; near-miss to
  the configuration family, not a tagged claim).
- Case management & BPM / workflow execution engines — case
  automation, process orchestration, workflow execution (the
  platform's signature domain; the substrate's case *records* are
  Core, the automation that acts on cases is not built).
- Decisioning engine (Customer Decision Hub — named in the source
  record's `all_others`, not in the description; record-named, not
  description-claimed).
- GenAI application tooling (GenAI Blueprint — record-named as
  above) and AI/ML models generally.
- Managed cloud operations & application scaling platform (the
  fully managed cloud, environments, and operational support the
  description asserts — the deployment layer itself, operated).

Extended families carried from the Group 25 union, not implemented:

- Customer-service casework depth: knowledge-driven agent desktops,
  self-service portals, chat/chatbot channels.
- Guidance delivery runtime: the in-application overlay engine and
  codeless authoring tooling.
- Gap-identification & adoption-analytics engines: live telemetry
  collection, gap detection, engagement analytics beyond counts.
- Customization & module engines: add-on module execution,
  codeless configuration runtimes.
- Knowledge base & self-service content (0 claims in this category).
- Marketing-automation engines & email delivery (0 claims here).
- Integration connector engines (0 claims here).

Baseline gaps at High (platform layer; gap-listed, never implied
closed): MFA / authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13); encryption at rest (SC-28);
audit retention enforcement (AU-11); session lock / termination
(AC-11/AC-12). Platform notes: multi-tenancy (single-tenant
reference deployment); TLS only when a certificate is configured;
demo identities are hooks, not an IdP (IA-2 stays with the embedding
organization). The managed hosting platform the fork asserts in
prose is the deployment layer itself.
