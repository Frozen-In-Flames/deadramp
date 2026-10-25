# Union Spec — Customer Service, CMMC L1 (DeadRamp Phase 2, Group 26)

The merged functional spec for the Customer Service sibling group at
the L1 tier: **2 forks, both FedRAMP Low**, reconciled zero-diff three
ways (`specs/specs.json` ↔ `forks.json` category="Customer Service" +
cmmc_tier="L1" ↔ MAP.md "Customer Service — L1 (2)").

The group: PagerDuty Operations Cloud (PagerDuty) · Riskuity
(Longevity Consulting).

**This group is largely a source-category artifact, and the spec says
so plainly.** Only one of the two — PagerDuty Operations Cloud, an
incident-operations platform whose description explicitly includes
triage of "customer support tickets" — claims any customer-service
function at all. The other, Riskuity, is a Governance, Risk, and
Compliance platform; it claims exactly one function family (GRC) and
zero customer-service functions, and its source record carries an
**empty** business_categories list. There is no single product the two
of them are. What the merged build implements is the customer-service
records substrate that PagerDuty's claimed functions presuppose —
cases with a lifecycle, requesters held by opaque reference,
assignment, priority and due records, alert records, on-call
rotations, status communication, and the registry underneath — plus
the baseline substrate (RBAC, audit) both tiers' builds carry.
Riskuity contributes its tier to the union baseline and its one GRC
claim to the gap registry; the GRC platform itself is an Extended
function, not built from one sentence of prose.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against a 16-family taxonomy defined from this category's
descriptions (the category is new; its L2 sibling group has not been
built, so no prior taxonomy exists to inherit). A family is claimed
only when the offering's own description contains matching text; the
first matching sentence is stored in `specs/specs.json` as evidence,
so every claim is auditable. **9 raw hits → 8 surviving claims.** One
wording-artifact correction removed a claim, and four scoping
decisions kept false hits out of the count entirely; all are itemized
in `scratch/ARTIFACTS.md`:

- **Removed:** Riskuity's NIST 800-53 / RMF / ATO sentence tags
  `compliance_frameworks` on raw keywords, but the sentence describes
  the *vendor's* decades of experience, not a function of the offering
  (Group 4's discipline: vendor-posture prose does not tag product
  functions). The family ends at 0 claims.
- **Scoped out by regex design, recorded as near-misses:** PagerDuty's
  "intelligent aggregation" is algorithmic-grouping prose, not an AI
  claim; "Real-time status updates" is status communication, not a
  real-time channel; "external-facing status pages" are communication,
  not reporting; Riskuity's "security and compliance at its core" is
  posture prose, not an access-control or audit function.

Per-fork claim counts: PagerDuty Operations Cloud 7, Riskuity 1.
**No fork has zero claims; one fork (Riskuity) has zero
customer-service claims.**

## Function ranking — all 2 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Case / ticket registry, triage & lifecycle | **Core** — the case registry |
| 1 | 1 | Automated event detection, diagnosis & response | Core (records); detection/diagnosis engines Extended |
| 1 | 1 | Event orchestration, aggregation & alert prioritization | Core (priority + alert records); orchestration/aggregation engines Extended |
| 1 | 1 | Automated actions & predefined workflows | Core (rule registry); execution Extended |
| 1 | 1 | On-call scheduling & coverage | **Core** — rotation records + derivation |
| 1 | 1 | Responder assignment & mobilization | **Core** — case assignment |
| 1 | 1 | Status updates & status pages | **Core** — derived status view + public updates |
| 1 | 1 | Governance, risk & compliance platform | Extended — GRC platform (Riskuity's sole claim) |
| 9 | 0 | Compliance framework support (NIST / RMF / ATO) | Not claimed — raw hit removed as a wording artifact (see above) |
| 9 | 0 | Knowledge base / help articles | Named absence — not built |
| 9 | 0 | Satisfaction / CSAT surveys | Named absence — not built |
| 9 | 0 | Real-time chat / voice channels | Extended — media/telephony |
| 9 | 0 | AI assistance / deflection / learned models | Extended — models (near-miss recorded, not tagged) |
| 9 | 0 | Reporting & dashboards | Core (registry reporting only); engines Extended |
| 9 | 0 | Access control | **Core** as baseline substrate — carried, not claimed |
| 9 | 0 | Audit logging | **Core** as baseline substrate — carried, not claimed |

## The Core — what the merged build implements (10 functions)

1. **Case registry + lifecycle** — cases (`case-`) with title, body,
   requester reference, channel label, and a guarded lifecycle
   (new → open → in_progress → resolved → closed, with reopen from
   resolved/closed). Invalid transitions are rejected whole.
2. **Requester records, opaque references only** — requesters
   (`req-`) keyed by a caller-supplied opaque `ref` plus a display
   label. The record shape is exactly `{id, ref, label, created_utc,
   created_by}`: there is no field that could hold a phone number,
   email address, or real identifier (the Contact Center group's
   privacy discipline, reused by design).
3. **Assignment** — a responder directory (`rsp-`, labels only) and
   case assignment/reassignment, audited with from/to.
4. **Priority & due records, breach derived at read** — priority
   (low/normal/high/critical) and an optional per-case `due_at`; a
   case reads `breached` iff it is past due and not in a terminal
   status. No sibling claims SLA terms, so there is no SLA policy
   engine in the union (the Contact Center group's precedent): the
   substrate holds the due time, the derivation is read-time only.
5. **Alert/event records** — alert records (`alert-`) with opaque
   source references, severity, and a new → acknowledged → resolved
   state, single and bulk ingest (bulk is atomic: a bad entry records
   nothing), linkable to cases. These are the records PagerDuty's
   claimed detection/response functions produce; the engines are
   Extended.
6. **On-call schedules** — rotation records (`sched-`): an ordered
   responder list, a period in days, an anchor date. Who is on call at
   any date is *derived* by pure date arithmetic (whole periods since
   the anchor, modulo rotation size; dates before the anchor wrap
   backwards). No scheduling engine exists or is needed.
7. **Status communication** — updates posted against cases, flagged
   public or internal; the external status view is derived at read
   (overall = outage if any open case is critical, degraded if any
   open case is high priority or breached, else operational) and
   exposes public updates only.
8. **Automation rule registry** — rules (`rule-`) as records: name,
   trigger, condition text, action text, enabled flag. The registry
   **never evaluates a condition and never executes an action** — a
   test pins that a matching rule changes no state. Execution engines
   are Extended.
9. **Registry reporting & search** — counts by status/priority, the
   derived breach count, alert counts by state, current on-call per
   schedule; substring search over case titles, bodies and requester
   labels. Reporting beyond registry counts is Extended.
10. **RBAC + append-only audit** — roles admin / agent / viewer
    (agent cannot write rules or read the audit; viewer is read-only
    without audit), and an append-only audit log recording every
    mutation and, at the service layer, every denied attempt
    (`<action>:denied`). Baseline substrate: carried at 0 claims,
    recorded as carried, not claimed.

Design reuse, stated on the record: the architecture (errors /
access / audit / store / service / CLI, plain-string-vs-User actor
convention, denied-attempt auditing at the service layer, derived
breach) follows the shipped Contact Center L2 build's patterns — our
own Apache-2.0 code patterns, re-implemented for this group's claims
and tier, not copied; the Contact Center spec does not govern here.
No code is shared between the two group directories.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`).
- **Group composition:** both forks are FedRAMP **Low** (Low 2,
  LI-SaaS 0) — recorded per fork in `specs/specs.json`. The tier rule
  is stated in full anyway: the union of the Low and LI-SaaS parent
  baselines is NIST SP 800-53 Rev. 5 **Low** (LI-SaaS is a tailored
  subset, adds nothing), cross-walked to the FAR 52.204-21 practices
  that define CMMC L1. Derivation per the Merge Rule: union of parent
  baselines = Low, inherited in full. This baseline is written fresh
  for this tier; no Moderate or High framing is imported.
- **Feature → control family mapping (this build, at the Low
  baseline):**
  - Access control hooks → **AC** (AC-2 account management, AC-3
    access enforcement; FAR 52.204-21's access-limitation practices:
    limit system access to authorized users and to the transactions
    and functions they are authorized to execute), **IA** (IA-2
    identification & authentication — identity is supplied by the
    embedding organization via user/role headers; the service ships
    hooks, not an identity provider; FAR's practices: identify system
    users, processes, and devices, and authenticate them before
    allowing access).
  - Audit log → **AU**, **on the FedRAMP Low side of the crosswalk
    only** (AU-2 event logging, AU-3 content of audit records; the
    append-only store and permission-gated read are implementation
    properties). **Precision note:** CMMC L1 / FAR 52.204-21 contains
    **no audit practice**, so no audit claim is made on the CMMC side.
    The audit log is carried because the FedRAMP Low baseline carries
    the AU family — not because L1 asks for it.
  - Case / alert / schedule records, derivation and search → **SI**
    (SI-10 information input validation — malformed input is rejected,
    never partially applied; the atomic bulk ingest is an SI-10
    property) and **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured; FAR's
    system-and-communications-protection practices cover boundary
    protection at the family level). Encryption at rest is a
    deployment-layer control, stated plainly, not claimed here. No
    sibling in this group claims an encryption function (0 of 2).
- **What this tier does not carry, and this build does not claim:**
  the Moderate/High apparatus from the sibling groups (audit hash
  chaining, logon lockout, auditor role, 800-172-derived
  enhancements) is out of scope for a Low/L1 merge and is not
  inherited downward.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either. FedRAMP authorizes products; CMMC certifies
  organizations.

## Implementation contract (summary)

Python 3, **standard library only**, package `custsvc` under `src/`,
runnable and testable with `PYTHONPATH=src`:

- `custsvc/access.py` — `User(name, role)`; roles
  `admin|agent|viewer`; admin = all actions, agent = all reads except
  `audit_read` + case/requester/responder/alert/schedule writes,
  viewer = reads except `audit_read`; `require(user, action)` raises
  `PermissionDenied`.
- `custsvc/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` → dicts with keys `ts, actor,
  action, target, details`. Append-only; optional JSONL file.
- `custsvc/store.py` — `CustsvcStore(audit=None)`; requesters,
  responders, cases (lifecycle + derived `breached`), alerts (single
  + atomic bulk), schedules (`on_call` derivation), rules (registry
  only), `public_status`, `report_summary`, `search_cases`. Id
  prefixes: `req- rsp- case- upd- alert- sched- rule-`.
- `custsvc/service.py` — `make_server(host, port, store, audit,
  users)`; demo users alice=admin, bob=agent, carol=viewer via
  `X-User` / `X-Role` headers; errors map ValidationError→400,
  NotFoundError→404, PermissionDenied→403, unauthenticated→401; denied
  attempts audited as `<action>:denied`.
- `custsvc/__main__.py` — `python -m custsvc serve` (default port
  8799, `--audit-log`, `--certfile`/`--keyfile` for TLS).

## Coverage statement (for this build)

Forks spec'd: **2 of 2**. Core functions implemented: **10 of 10**.
Tests: **69 run, 69 passed**, including one mutation-verified
negative control (breach derivation; 7 failures under the mutant —
see `tests/README.md`). Claims: 8 surviving of 9 raw hits, 1 removed
by a documented wording-artifact correction.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:

- **Event detection, diagnosis & orchestration engines** — automated
  detection/diagnosis of source events, event orchestration and
  intelligent aggregation (PagerDuty's engine claims; alert *records*
  and their triage are Core).
- **Automation execution engines** — evaluating rule conditions and
  executing automated actions / predefined workflows before human
  intervention (the rule *registry* is Core; nothing executes).
- **GRC platform** — Riskuity's sole claim family: governance, risk
  and compliance management depth (risk registers, RMF/ATO workflows,
  compliance automation), and with it any compliance-framework
  support depth.
- **Real-time channels** — live chat, voice/telephony channels and
  their media (0 claims in this group; named so the union is
  complete).
- **AI assistance / deflection** — virtual agents, deflection bots,
  learned models (0 tagged claims; "intelligent aggregation" is a
  recorded near-miss, not a claim).
- **Knowledge base articles** — 0 of 2 claims; named absence.
- **Satisfaction / CSAT surveys** — 0 of 2 claims; named absence.
- **SLA policy engine** — tiers, business-hour calendars, escalation
  policies (0 claims; the Core derives breach from a per-case due
  time only).
- **Notification delivery & status-page hosting** — real-time push
  and transport of status updates (email/SMS/push delivery, hosted
  status pages); the status *records* and derived view are Core,
  delivery is not.
- **Reporting / analytics engines** beyond registry reporting
  (0 claims in this group).

Platform-layer gaps (gap-listed, never implied closed): encryption
at rest (deployment layer); TLS only when a certificate is
configured; multi-tenancy (the build is a single-tenant reference
deployment); demo identities are hooks, not an IdP (IA-2 stays with
the embedding organization).
