# Union Spec — Customer Service, CMMC L3-adjacent (DeadRamp Phase 2, Group 41 singleton)

The singleton spec for the Customer Service category at the
L3-adjacent tier: **1 fork, FedRAMP High** — Federal High Impact
Virtualized Environment (FedHIVE) (Human Resources Technologies,
Inc. (HRTec)). Reconciled zero-diff: `specs/specs.json` ↔
`forks.json` category="Customer Service" + cmmc_tier="L3-adjacent"
(exactly one match) ↔ MAP.md's category arithmetic (Customer
Service totals 6 offerings = 2 at L1, shipped as Group 26 + 2 at L2,
shipped as Group 27 + 1 at L3-adjacent, this singleton + 1
untiered, Toonimo Digital Adoption Platform with impact Unknown and
tier null, a remainder fork). MAP.md's sibling sections list only
groups of size 2+, so no sibling-section diff applies to a
singleton; forks.json exactness plus the category arithmetic is the
reconciliation, per the earlier singleton builds.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 26/27 merged build** (`../customer-service-l1/`,
   `../customer-service-l2/`) — the Customer Service records
   substrate, defined at L1 (Group 26) and carried byte-identical
   to L2 (Group 27): 10 core functions.
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

**Reuse, stated explicitly:** this build reuses the Group 26/27
build's own open-source code (Apache-2.0, ours). All seven
`src/custsvc/` modules are modified for the tier uplift — `errors.py`
(AuditWriteError added), `access.py` (auditor role added),
`audit.py` (hash chain, fail-closed writes, and query added,
following the proven `groups/analytics-l3` / `groups/crm-l3`
mechanics), `store.py` (snapshot fail-closed wrapper added),
`service.py` (lockout, audit verify/query, auditor user added),
`__main__.py` (auditor user and lockout flags added), `__init__.py`
(docstring only). No core function changed behavior: every Group
26/27 test passes with only the documented uplift adaptations
(tests/README.md). Per-file SHA-256 in `scratch/reuse-note.md`.

## How functions were counted — zero claims, honestly

Group 26's 16-family taxonomy was applied **verbatim** (same ids,
labels, and matching patterns, in `scratch/extract.py`) to this
fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22). A family is
claimed only when the offering's own description contains matching
text; the first matching sentence would be stored in
`specs/specs.json` as evidence.

**Result: 0 claims.** Two scoping facts produce that zero, and both
are recorded rather than smoothed over:

1. **The third-party catalogue was excluded before matching.**
   FedHIVE's description ends with ~20 blurbs for third-party
   applications deployable inside its environment (1Kosmos,
   FormAssembly, RegScale, VMware, and others). Those are other
   vendors' products. Matching the full text would have produced
   raw hits in 6 families — every one from the catalogue (HPE
   Mist's "fewer trouble tickets", FormAssembly's "role-based
   access controls" and "audit trails", RegScale's "governance,
   risk, and compliance processes"). All excluded, per the GRC L2
   precedent; the full accounting is in `scratch/ARTIFACTS.md` and
   `scratch/function_counts.json`.
2. **FedHIVE's own prose is hosting-boundary prose.** It describes
   a virtualized environment: IaaS/PaaS/SaaS delivery inside one
   High authorization boundary, 400+ controls implemented and
   continuously managed, a 24/7 SOC, lift-and-shift migration,
   control inheritance for hosted providers. No sentence contains
   any taxonomy family's matching text. The closest approach,
   compliance frameworks, misses on wording alone ("NIST SP
   800-53" vs. the pattern's "NIST 800-53"; "(P-ATO)" vs. "(ATO)")
   and is recorded as a near-miss, not promoted — the taxonomy was
   not re-tuned. Nine near-misses are itemized in
   `scratch/ARTIFACTS.md`.

The full description is preserved verbatim in the spec sheet, and
no function was invented for the fork. Counts are a floor, and here
the floor is zero — the same honest outcome as the zero-claim
sheets in Groups 28 and 35 and Singletons 38 and 40. The fork's
source record also carries an **empty** `business_categories` list:
the source does not self-categorize it at all; its Customer Service
category comes from the Phase 1 registry.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Case / ticket registry, triage & lifecycle | **Core** — the case registry; carried, not claimed |
| 1 | 0 | Automated event detection, diagnosis & response | Core (records); detection/diagnosis engines Extended — near-miss recorded (SOC / monitoring prose) |
| 1 | 0 | Event orchestration, aggregation & alert prioritization | Core (priority + alert records); orchestration/aggregation engines Extended |
| 1 | 0 | Automated actions & predefined workflows | Core (rule registry, never executes); execution Extended — near-miss recorded |
| 1 | 0 | On-call scheduling & coverage | **Core** — rotation records + derivation; carried, not claimed — near-miss recorded (24/7 SOC) |
| 1 | 0 | Responder assignment & mobilization | **Core** — case assignment; carried, not claimed |
| 1 | 0 | Status updates & status pages | **Core** — derived status view + public updates; carried, not claimed |
| 1 | 0 | Governance, risk & compliance platform | Extended — carried from the Group 26 union (claimed 1 of 2 there) |
| 1 | 0 | Compliance framework support (NIST / RMF / ATO) | Extended — the fork's own domain in prose (control implementation & inheritance), a recorded near-miss under the verbatim taxonomy, not a tagged claim |
| 1 | 0 | Knowledge base / help articles | Named absence — claimed by no fork at any tier of this category; not built |
| 1 | 0 | Satisfaction / CSAT surveys | Named absence — claimed by no fork at any tier; not built |
| 1 | 0 | Real-time chat / voice channels | Extended — media/telephony |
| 1 | 0 | AI assistance / deflection / learned models | Extended — models (all AI vocabulary in this description belongs to the excluded catalogue) |
| 1 | 0 | Reporting & dashboards | Core (registry reporting) — carried, not claimed; engines Extended |
| 1 | 0 | Access control | **Core** as baseline substrate, uplifted to High — carried, not claimed |
| 1 | 0 | Audit logging | **Core** as baseline substrate, uplifted to High — carried, not claimed |

Plus this singleton's own platform substance, named from its prose
(all Extended / platform-layer, detailed in Gaps below):
virtualization & cloud hosting (the product itself), authorization
acceleration & control inheritance, continuous monitoring & SOC
operations, vulnerability management & patching, incident response
operations, migration services, and the hosted third-party
application ecosystem.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35 and Singleton 38/40 precedent).** This fork tags
zero claims, yet all 10 core functions stand in this build. The
reasoning is the Merge Rule itself, not convenience: a cross-tier
merge takes the union of the parents upward whole, and the Group
26/27 union — the category substrate this fork's category
presupposes — is a parent of this build. A wording artifact (a
hosting platform filed under Customer Service whose own prose
contains no customer-service vocabulary) is not a downgrade, and
stripping the substrate at High because the High fork's prose is
about a different layer entirely would dilute the union, which
Rule 1 prohibits. Every core function is therefore flagged
**carried, not claimed** for this tier. Where the fork claims less
than the substrate — which here is everywhere — that is this
paragraph, stated once and plainly, rather than ten quiet
exceptions. Building the fork's actual domain instead (a
virtualization platform) would be inventing a different category's
product; it is named in the gap list, not built.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 functions as Groups 26/27, carried up whole:

1. **Case registry + lifecycle** — cases (`case-`) with title, body,
   requester reference, channel label, and a guarded lifecycle
   (new → open → in_progress → resolved → closed, with reopen from
   resolved/closed). Invalid transitions are rejected whole.
   Carried, not claimed.
2. **Requester records, opaque references only** — requesters
   (`req-`) keyed by a caller-supplied opaque `ref` plus a display
   label. The record shape is exactly
   `{id, ref, label, created_utc, created_by}`: no field could hold
   a phone number, email address, or real identifier. Carried, not
   claimed.
3. **Assignment** — a responder directory (`rsp-`, labels only) and
   case assignment/reassignment, audited with from/to. Carried, not
   claimed.
4. **Priority & due records, breach derived at read** — priority
   (low/normal/high/critical) and an optional per-case `due_at`; a
   case reads `breached` iff it is past due and not in a terminal
   status. No fork at any tier of this category claims SLA terms,
   so there is no SLA policy engine in the union: the substrate
   holds the due time, the derivation is read-time only. Carried,
   not claimed.
5. **Alert/event records** — alert records (`alert-`) with opaque
   source references, severity, and a new → acknowledged → resolved
   state, single and bulk ingest (bulk is atomic: a bad entry
   records nothing), linkable to cases. Carried, not claimed.
6. **On-call schedules** — rotation records (`sched-`): an ordered
   responder list, a period in days, an anchor date. Who is on call
   at any date is *derived* by pure date arithmetic. The fork's
   "24/7 SOC" is its own operations center, recorded as a
   near-miss; it is not this function and does not claim it.
   Carried, not claimed.
7. **Status communication** — updates posted against cases, flagged
   public or internal; the external status view is derived at read
   (overall = outage if any open case is critical, degraded if any
   open case is high priority or breached, else operational) and
   exposes public updates only. Carried, not claimed.
8. **Automation rule registry** — rules (`rule-`) as records: name,
   trigger, condition text, action text, enabled flag. The registry
   **never evaluates a condition and never executes an action** — a
   test pins that a matching rule changes no state. Carried, not
   claimed.
9. **Registry reporting & search** — counts by status/priority, the
   derived breach count, alert counts by state, current on-call per
   schedule; substring search over case titles, bodies and
   requester labels. Carried, not claimed.
10. **RBAC + append-only audit** — roles admin / agent / viewer
    (agent cannot write rules or read the audit; viewer is
    read-only without audit) **plus the auditor role** [L3], and an
    append-only audit log recording every mutation and, at the
    service layer, every denied attempt (`<action>:denied`),
    uplifted to the High baseline (below). Carried, not claimed.

**Privacy discipline (hard rule, inherited).** Requester records
hold an opaque caller-supplied reference and a label, nothing
else — enforced by tests (`tests/test_requesters.py`), which pin
the exact record shape. Alert sources are opaque references too.
This matters at this tier in particular: the fork's stated purpose
is protecting CUI and PII inside its boundary, and the substrate
still holds no real identifier for anyone.

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. The cross-tier parents (Groups 26/27) sat
  at Low and Moderate; the union baseline is therefore the High
  baseline, un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3 is
  not identical to FedRAMP High; it is the same assurance weight
  class.
- **Feature → control family mapping (carried from Groups 26/27):**

  | Core function | Control families | How the build answers |
  |---|---|---|
  | Access control hooks | AC-2, AC-3, AC-6; IA-2 (hooks) | Fixed role matrix enforced in the store before any mutation or id allocation, and again at the service layer; identity supplied by the embedding organization |
  | Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only, hash-chained, fail-closed, queryable log including denied attempts; no mutation API |
  | Case / alert / schedule records | SI-10, SC-8 | Malformed input rejected whole, never partially applied (atomic bulk ingest is an SI-10 property); TLS when a certificate is configured |
  | Derivations (breach, on-call, status) | AU-6, CA-7, CM-6 | Computed at read from records against a stated `now`; never stored |
  | Rule registry | CM-6, SA-4 | Configuration records stored verbatim, never executed |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held rule writes and audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Groups 26/27, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here. (The fork's "FIPS PUB 199 High level" wording is an impact categorization, not a validated-module claim, and this build inherits neither reading.) |
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
  preserved; the third-party catalogue exclusion and nine
  near-misses itemized in `scratch/ARTIFACTS.md`).
- Core implemented: **10 / 10** functions above, at the High
  baseline; 6 tier uplifts implemented (hash-chained audit,
  fail-closed audit writes with store rollback, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor role). All 10 are **carried, not claimed** at this tier,
  under the recorded core-boundary decision.
- Tests: **112** (69 inherited from Groups 26/27, 7 added inside
  inherited files, 36 in new uplift files); two negative controls,
  both mutation-verified live (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own platform substance (Extended; named from its
prose — the fork's actual product surface, none of it built here):

- Virtualization & cloud hosting platform — IaaS/PaaS/SaaS delivery
  within a single High authorization boundary, hypervisor and
  private-cloud operations, hybrid architectures spanning GovCloud
  and hyperscaler environments (the fork's entire product; it is
  the platform layer itself).
- Authorization acceleration & control inheritance — JAB P-ATO
  sponsorship, full High baseline control inheritance, assessment
  reuse (the fork's named differentiator; its framework prose is
  the compliance_frameworks near-miss recorded above).
- Continuous monitoring & Security Operations Center operations
  (24/7 SOC, automated continuous monitoring of the boundary).
- Vulnerability management & patching operations.
- Incident response operations (for the hosting boundary).
- Migration & lift-and-shift services (legacy systems, COTS
  applications, enterprise stacks, minimal re-engineering).
- Hosted third-party application ecosystem — the ~20 applications
  in the excluded catalogue (identity, forms, GRC, storage,
  Kubernetes, collaboration, and others), each its own vendor's
  product belonging to its own category's build.

Extended families carried from the Group 26/27 category union, not
implemented:

- Event detection, diagnosis & orchestration engines (alert
  records and triage are Core; the engines are not).
- Automation execution engines (the rule registry is Core; nothing
  executes, pinned by test).
- GRC platform (claimed by one L1 sibling; 0 claims here).
- Real-time channels: live chat, voice / telephony.
- AI assistance / deflection / learned models.
- SLA policy engine (due / breach derivation only in Core; no fork
  at any tier claims SLA terms).
- Notification delivery & status-page hosting (status records and
  the derived view are Core; delivery is not).
- Reporting / analytics engines beyond registry reporting.

Named absences (not gaps, unclaimed at every tier of this
category): knowledge base / help articles; satisfaction / CSAT
surveys.

Baseline gaps at High (platform layer; gap-listed, never implied
closed): MFA / authenticator management (IA-2(1)/(2), IA-5);
FIPS-validated cryptography (SC-13); encryption at rest (SC-28);
audit retention enforcement (AU-11); session lock / termination
(AC-11/AC-12). Platform notes: multi-tenancy (the fork is
inherently a multi-agency environment; this build is a
single-tenant reference deployment, and tenant isolation is a
deployment property); TLS only when a certificate is configured;
demo identities are hooks, not an IdP (IA-2 stays with the
embedding organization).
