# Union Spec — Contact Center, CMMC L2 (DeadRamp Phase 2, Group 15)

The merged functional spec for the Contact Center sibling group at the L2
tier: **5 forks, all FedRAMP Moderate**, reconciled zero-diff three ways
(`specs/specs.json` ↔ `forks.json` category="Contact Center" +
cmmc_tier="L2" ↔ MAP.md "Contact Center — L2 (5)").

The group: BeyondTrust Identity Security For Government (BeyondTrust) ·
LM for Gov (LogicMonitor) · Mindful by Medallia (Medallia Inc.) ·
Security Control Cloud Software Platform (SCCP) (Security Control LLC
(an ISI Company)) · ClaimsXM (Signature Performance, Inc.).

**This group is a source-category artifact, and the spec says so
plainly.** Only one of the five — Mindful by Medallia, a citizen callback
product — is genuinely a contact-center product. The source files the
other four under Contact Center as their first business category:
LM for Gov carries 8 business categories with Contact Center first,
SCCP carries 7, ClaimsXM carries 6, and BeyondTrust's cached record has
an **empty** business_categories list. What those four actually are is
an identity-security platform (BeyondTrust), an infrastructure
observability platform (LogicMonitor), a personnel/facility
security-records platform (SCCP), and a healthcare claims platform
(ClaimsXM). There is no single product they all are. What they share,
and what the claim counts below prove, is a **records substrate** their
claimed functions collectively presuppose: people held in a directory,
work held in queues and cases with a lifecycle, interactions and alerts
recorded against those cases, rules registered against case types,
callbacks scheduled for contacts, and reports, search, access control,
and an audit trail over all of it. The merged build implements that
substrate; each vendor's domain engine on top of it is an Extended
function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split and
matched against an 18-family taxonomy defined from this category's
descriptions. (The assignment brief calls the taxonomy 17 families;
counted as listed it has 18, and all 18 are used.) A family is claimed
only when the offering's own description contains matching text; the
first matching sentence is stored in `specs/specs.json` as evidence, so
every claim is auditable. **24 raw hits → 22 surviving claims.** Two
wording-artifact corrections removed claims, and two scoping decisions
kept false hits out of the count entirely; all are documented in
`scratch/ARTIFACTS.md`: BeyondTrust's session oversight ("under strict
monitoring") falsely tagging monitoring & observability data collection,
and ClaimsXM's self-descriptor "integrated technology solution" falsely
tagging integrations (the removals, 24 → 22); a naive `\bAI\b` falsely
tagging BeyondTrust's "AI identities" (identities belonging to AI
agents, not an AI function) and bare "support" falsely reading
BeyondTrust's IT Remote Support as customer service (excluded by the
scoped regexes as listed). Two kept claims carry recorded bases:
BeyondTrust's dashboards/reporting claim rests on audit reports, not
dashboards, and ClaimsXM's identity/access claim rests on the thin
phrase "by authorized users" — it stands, noted as thin. **No fork has
zero claims.** Per-fork claim counts: BeyondTrust Identity Security For
Government 6, ClaimsXM 5, LM for Gov 5, Mindful by Medallia 4, Security
Control Cloud Software Platform (SCCP) 2.

## Function ranking — all 5 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 2 | Identity, access control & Zero Trust | **Core** (as substrate) — RBAC substrate; identity products Extended |
| 1 | 2 | Integrations & interoperability | Extended — connector engines/catalog |
| 1 | 2 | Dashboards, reporting & forecasting | Core (records substrate); engines Extended |
| 1 | 2 | Customer service & citizen engagement | **Core** — the case/callback/interaction substrate IS the service surface; no separate engine claimed |
| 5 | 1 | Privileged access management & remote support sessions | Extended — PAM/session engines |
| 5 | 1 | Audit logging, session recording & audit reports | **Core** |
| 5 | 1 | Risk assessment, detection & recommendations | Extended — analytics models |
| 5 | 1 | Monitoring & observability data collection | Extended — collection engines; alert/report records Core |
| 5 | 1 | Alerting | Core (records); engines Extended |
| 5 | 1 | AI/ML capability | Extended — models |
| 5 | 1 | Callback requests & scheduling | **Core** |
| 5 | 1 | Interaction records & external reference passthrough | **Core** |
| 5 | 1 | Voice & telephony channel | Extended — media/PSTN; callback records Core |
| 5 | 1 | Personnel, facility & clearance records management | Core (registry); clearance-management depth Extended |
| 5 | 1 | Activity tracking | **Core** — case/activity records; the tracking surface |
| 5 | 1 | Claims & case processing | Core (case registry); adjudication Extended |
| 5 | 1 | Business rules & process automation | Core (registry); execution Extended |
| 5 | 1 | Fraud, waste & abuse detection | Extended — detection engines |

Named absences: **knowledge base articles are claimed by 0 of 5**
siblings, **satisfaction/CSAT surveys are claimed by 0 of 5**, and
**SLA terms are claimed by 0 of 5** — no sibling's description asserts an
SLA, so the core derives breach from a per-case due time only (function
3 below) and there is no SLA policy engine in the union. **A real-time
ACD routing engine is claimed by 0 siblings as an engine**: Mindful
claims the callback function (reconnecting a citizen with "an available
agency representative"), not a routing engine; queue assignment in the
core is the substrate that function presupposes, and the routing engine
itself is a gap. Multi-tenancy is claimed in prose by SCCP ("multi-tenant
SaaS cloud computing environment") but is a deployment property, not a
function; the build is a single-tenant reference deployment and says so
(see gaps).

## The Core — what the merged build implements (12 functions)

1. **Directory** — agent records (`agt-`) and external contact records
   (`ct-`) with opaque reference strings and free-form attributes (a
   clearance level rides as an attribute: the SCCP pattern). Claims
   basis: records management, identity & access.
2. **Queues** — named work queues (`que-`) with agent membership; the
   assignment substrate (Mindful reconnects a citizen with "an
   available agency representative").
3. **Case registry & lifecycle** — cases (`case-`), type-tagged
   (claim/callback/activity/inquiry/general), with statuses
   `open → in_progress → resolved → closed` (plus `cancelled`;
   `resolved` may reopen to `in_progress`), assignment to an agent
   and/or a queue, priority, and an optional `due_at`. Breach is
   **derived at read time, never stored**:
   `breached = now > due_at and status not in (resolved, closed, cancelled)`
   — the Education group's derivation pattern.
4. **Callback scheduling** — callback requests (`cb-`) for a contact,
   with a `requested_for` time and optional linked case/agent; stored
   status `scheduled/completed/cancelled`, with state **derived at
   read** (overdue when `now > requested_for` and not terminal). The
   group's one native contact-center function (Mindful).
5. **Interaction records** — channel-tagged
   (voice/chat/email/in_person/remote_session/system), with direction,
   outcome code, summary, links to case/contact/agent, and an
   `external_ref` passthrough (Mindful's contact-center ID returned to
   the agency). Immutable once written.
6. **Alert records** — alerts (`alr-`) with severity, source, message,
   optional case link, and lifecycle `raised → acknowledged → resolved`.
   These are the records of alerting (LogicMonitor); detection engines
   are Extended.
7. **Business-rule registry** — rule records (`rule-`): name, case-type
   scope, condition text, action text, enabled flag, versioned on
   update (full version history retained). Registry only; the rules
   **execution** engine is Extended (ClaimsXM's "business rules and
   logic").
8. **Reports** — deterministic summaries: cases by status/type/queue,
   breached-case count at the report's `now`, interactions by
   channel/outcome, alerts by severity/status, callbacks by derived
   state.
9. **Search** — literal case-insensitive substring search over people,
   cases, interactions, and alerts.
10. **REST API** — the full surface over HTTP, with the house auth
    convention (X-User/X-Role against a demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
11. **Access control (RBAC)** — admin/operator/viewer matrix;
    `rule_write` and `audit_read` are admin-only; enforced in the store
    before any mutation or id allocation, and again at the service
    layer.
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation and every denied attempt (`<action>:denied`).

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is the
tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110 practices
of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`. No parent
carried a higher or lower baseline, so the merge changes no tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Directory, queues | AC-3, AC-6, IA-2 (hooks) | People and queue membership are explicit records; assignment is computed from them, never assumed |
| Cases & lifecycle | AU-2, CM-6, SI-12 (partial) | Every case transition is an auditable event under a configured lifecycle; retention/disposition engines are Extended |
| Breach derivation | AU-6, CA-7, CM-6 | Breach is derived at read from `due_at` and status against the report's `now`, never stored — the derivation is reviewable and reproducible |
| Callbacks | AU-2, SC-8 (partial) | Callback requests are auditable records; transmission protection is reference passthrough of an opaque ID only (see privacy note in gaps) |
| Interactions | AU-2, AU-3, SI-12 (partial) | Immutable interaction records with content; review/search over them is Core, retention engines Extended |
| Alerts | AU-6, SI-4 | Alert records and their lifecycle support monitoring review; monitoring/collection engines are Extended |
| Rules registry | CM-6, SA-4 | Rules are versioned configuration records acquired and managed as configuration, not executed code |
| Reports | AU-6 | Deterministic summaries over the records, including derived breach and callback state at a stated `now` |
| Search | AU-6, SI-12 (partial) | Literal search over records supports review; retention/disposition is partial and Extended |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers; `rule_write`/`audit_read` admin-only |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization and
confers no CMMC certification; it is an open-source implementation whose
features trace to the Moderate/L2 control families. FedRAMP authorizes
products; CMMC certifies organizations — neither regime accepts the
other as evidence, and any real compliance claim still has to be earned
inside each regime separately.

## Implementation contract (summary)

`src/contact/` (Python stdlib only): `errors` (`ContactError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, role matrix), `audit` (append-only AuditLog), `store`
(ContactStore: the 12 core functions; failed operations consume no ids;
permission checks precede mutation), `service` (HTTP layer, demo
registry), `__main__` (`python -m contact serve`). `tests/`: see
tests/README.md for the test count and the negative-control record (the
count is filled in from the build, not stated here).

## Coverage statement (for this build)

- Forks spec'd: **5 / 5**, each with evidenced claims (22 total).
- Core implemented: **12 / 12** functions above.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- PAM & Zero Trust enforcement engines, including just-in-time
  privileged access and session recording with video (BeyondTrust).
- Identity risk analytics & prescriptive recommendations (BeyondTrust
  Identity Security Insights).
- Observability collection engines — collectors, metric collection,
  forecasting (LogicMonitor).
- Voice/telephony media and the callback connection engine, including
  ACD routing (Mindful by Medallia).
- Claims adjudication & fraud/waste/abuse detection engines, including
  rules execution (ClaimsXM).
- Personnel-security / facility-clearance management depth (SCCP).
- Integration connector engines (LogicMonitor's integration catalog;
  BeyondTrust's incident-response workflow integration).
- AI/ML models (LogicMonitor AI observability, 1 claim).
- Knowledge-base articles (0 of 5 — named absence).
- Satisfaction/CSAT surveys (0 of 5 — named absence).
- SLA policy engine — tiers, business-hour calendars, escalation
  (0 of 5 claim SLA terms; the core derives breach from a per-case due
  time only).

Platform layer (gap-listed, never implied closed): multi-tenancy (SCCP
claims multi-tenant prose; the build is a single-tenant reference
deployment); encryption at rest (deployment layer); TLS only when a
certificate is configured; demo identities are hooks, not an IdP —
IA-2 stays with the embedding organization.

**Privacy note:** Mindful's real function needs a phone number. The
build stores only an opaque caller-supplied reference string and never
a real phone number.
