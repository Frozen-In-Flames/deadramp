# Union Spec — Customer Service, CMMC L2 (DeadRamp Phase 2, Group 27)

The merged functional spec for the Customer Service sibling group at
the L2 tier: **2 forks, both FedRAMP Moderate**, reconciled zero-diff
three ways (`specs/specs.json` ↔ `forks.json` category="Customer
Service" + cmmc_tier="L2" ↔ MAP.md "Customer Service — L2 (2)").

The group: NCR VOYIX GOVERNMENT CLOUD (NCR Government, LLC) ·
Virtual Employee Network (VEN) (Relocation Management Worldwide
(RMW)).

**This group is a source-category artifact even more completely than
its L1 sibling, and the spec says so plainly.** Neither fork claims
any core customer-service function — no case/ticket, no channels, no
knowledge base, no surveys, anywhere in the tier. NCR VOYIX
Government Cloud is a commerce point-of-sale hosting environment
(AMS, Freshop, BSL Open APIs; Emerald/Aloha/RPOS point-of-sale for
grocery, gas, loyalty, and food-ordering transactions); it tags
**zero claims in any of the 16 taxonomy families**, and its source
record carries an **empty** business_categories list — the source
does not self-categorize it at all. VEN is a Permanent Change of
Station (PCS) employee-relocation system; of the 16 families it
claims exactly one, reporting, on a single sentence. What the merged
build implements is the customer-service records substrate defined
by this category's union at L1 (Group 26) — cases with a lifecycle,
requesters held by opaque reference, assignment, priority and due
records, alert records, on-call rotations, status communication,
and the registry underneath — carried at this group's Moderate
baseline under an explicit core-boundary decision (below). Both
forks' own domains (point-of-sale commerce hosting; PCS relocation
finance) are domain platforms, not customer-service substrate; they
are registered as gaps, not built, and nothing was invented to make
either product look like a helpdesk.

## Relationship to the L1 build (Group 26)

Group 26 defined this category's 16-family taxonomy and built the
substrate at the Low/L1 baseline. This group uses that taxonomy
**verbatim** (function_id, label, and regex unchanged — cross-tier
comparability is the point, and no regex was re-tuned for these
descriptions) and reuses Group 26's implementation **byte-identical**:
all 21 copied files (7 `src/custsvc/` modules, 14 test files) are
SHA-256-identical to the L1 originals (store.py:
`05c749f34c37a977e76cb1372c035909ad09875a7180ff441ac876a489cffe06`
in both trees). The reuse is justified on the claims, not on
convenience: the single family this group claims (reporting) sits
inside the L1 core's registry-reporting function, and neither fork
claims anything the substrate does not already hold. What is new
here is the baseline: this spec's control section is written fresh
for Moderate/L2. No Moderate or High apparatus from *other*
categories' groups is inherited sideways, and Group 26's Low-tier
framing is not imported either.

**Core-boundary decision (recorded, per the Group 10/24
precedent).** At L1 the substrate rested on one sibling's claimed
functions. Here it rests on thinner ice and the spec does not
pretend otherwise: VEN's own prose presupposes records of exactly
the substrate's shape — employee submissions initiated in the
system, agency review/reject/approve/certify actions against them,
expense and policy records, and the reports it claims outright —
while NCR presupposes nothing customer-service at all and
contributes its Moderate tier to the union baseline and nothing
else. The 10 core functions therefore stand as the category's
records substrate carried at this tier: 1 is claimed here
(reporting, inside function 9), 9 are carried, not claimed. Dropping
the substrate because the source miscategorized two products would
leave the category's L2 tier with no build at all and would break
the union the category's other tier already established; building
either fork's actual domain instead would be inventing a different
category's product. Both forks' domains are named in the gap list.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against Group 26's 16-family taxonomy, verbatim. A
family is claimed only when the offering's own description contains
matching text; the first matching sentence is stored in
`specs/specs.json` as evidence, so every claim is auditable (and
was programmatically verified verbatim: 0 violations). **1 raw hit
→ 1 surviving claim. Zero corrections were needed** — no raw hit
described vendor posture in a way that required removal — and six
near-misses are itemized in `scratch/ARTIFACTS.md`, none promoted:

- **automation_workflows / VEN:** the description is saturated with
  automation prose ("an automated work flow controlled by the
  Agency", "Fully automates expenses, policy, and suppliers",
  "Fully automates all Federal regulations and laws"), but none of
  the verbatim alternatives (automated actions / predefined
  workflows / trigger predefined) appears. The family stays at 0;
  the prose is recorded, not promoted.
- **oncall_scheduling / VEN:** "Users have 24/7 access to the
  system" is availability, not on-call coverage; the regex requires
  "24/7 coverage" and "coverage" never appears.
- **access_control / VEN:** PIV-card authentication of a digital
  signature, e-signature identity assurance, and the bare verb
  "access" — authentication/protection prose, no access-control,
  role-based, RBAC, or permissions vocabulary.
- **realtime_channels + status_communication / VEN:** "Real-time
  information directly from suppliers" and "runs real-time reports"
  are real-time data/reporting, not a channel or status pages (the
  Group 26 discipline: real-time status prose is not a channel).
- **compliance_frameworks + governance_risk_compliance / VEN:**
  FEAFA compliance framing and relocation-regulation prose; no
  NIST 800-53 / RMF / ATO term and no exact GRC phrase appears at
  all. (Contrast Group 26, where Riskuity's framework terms appeared
  but described the vendor's experience and were removed; here there
  was nothing to remove.)
- **satisfaction_surveys / VEN:** "based on anticipated client
  needs and customer input" is product-development feedback, not a
  survey instrument.
- **NCR wording note:** "customers" appears twice ("common
  interfaces for customers and 3rd parties", "the customer's
  ecosystem") in the API-consumer sense, not a service-recipient
  sense; no regex fires and there is nothing to correct.

Per-fork claim counts: VEN 1, NCR VOYIX Government Cloud 0.
**Fifteen of the sixteen families tag zero claims in this group.**

## Function ranking — all 2 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Reporting & dashboards | **Core** — registry reporting (function 9); engines Extended |
| 2 | 0 | Case / ticket registry, triage & lifecycle | **Core** — the case registry; carried, not claimed in this group |
| 2 | 0 | Automated event detection, diagnosis & response | Core (records); detection/diagnosis engines Extended |
| 2 | 0 | Event orchestration, aggregation & alert prioritization | Core (priority + alert records); orchestration/aggregation engines Extended |
| 2 | 0 | Automated actions & predefined workflows | Core (rule registry); execution Extended — VEN's automation prose is a recorded near-miss, not a claim |
| 2 | 0 | On-call scheduling & coverage | **Core** — rotation records + derivation; carried, not claimed |
| 2 | 0 | Responder assignment & mobilization | **Core** — case assignment; carried, not claimed |
| 2 | 0 | Status updates & status pages | **Core** — derived status view + public updates; carried, not claimed |
| 2 | 0 | Governance, risk & compliance platform | Extended — carried from the Group 26 union (0 claims here) |
| 2 | 0 | Compliance framework support (NIST / RMF / ATO) | Not claimed — no framework vocabulary appears in either description |
| 2 | 0 | Knowledge base / help articles | Named absence — not built |
| 2 | 0 | Satisfaction / CSAT surveys | Named absence — not built (near-miss recorded) |
| 2 | 0 | Real-time chat / voice channels | Extended — media/telephony |
| 2 | 0 | AI assistance / deflection / learned models | Extended — models |
| 2 | 0 | Access control | **Core** as baseline substrate — carried, not claimed |
| 2 | 0 | Audit logging | **Core** as baseline substrate — carried, not claimed |

## The Core — what the merged build implements (10 functions)

Identical in scope to Group 26's core; implemented by the reused
code. Stated here in full because this group's spec must stand on
its own:

1. **Case registry + lifecycle** — cases (`case-`) with title, body,
   requester reference, channel label, and a guarded lifecycle
   (new → open → in_progress → resolved → closed, with reopen from
   resolved/closed). Invalid transitions are rejected whole. VEN's
   submission → agency review/approve/certify shape is this
   function's record shape, recorded as presupposition, not claim.
2. **Requester records, opaque references only** — requesters
   (`req-`) keyed by a caller-supplied opaque `ref` plus a display
   label. The record shape is exactly `{id, ref, label, created_utc,
   created_by}`: no field could hold a phone number, email address,
   or real identifier. In a tier whose one claiming fork holds
   *employee relocation* records, this discipline matters more, not
   less — and it is unchanged.
3. **Assignment** — a responder directory (`rsp-`, labels only) and
   case assignment/reassignment, audited with from/to.
4. **Priority & due records, breach derived at read** — priority
   (low/normal/high/critical) and an optional per-case `due_at`; a
   case reads `breached` iff it is past due and not in a terminal
   status. No sibling at either tier claims SLA terms, so there is
   no SLA policy engine in the union: the substrate holds the due
   time, the derivation is read-time only.
5. **Alert/event records** — alert records (`alert-`) with opaque
   source references, severity, and a new → acknowledged → resolved
   state, single and bulk ingest (bulk is atomic: a bad entry
   records nothing), linkable to cases.
6. **On-call schedules** — rotation records (`sched-`): an ordered
   responder list, a period in days, an anchor date. Who is on call
   at any date is *derived* by pure date arithmetic (whole periods
   since the anchor, modulo rotation size; dates before the anchor
   wrap backwards). No scheduling engine exists or is needed.
7. **Status communication** — updates posted against cases, flagged
   public or internal; the external status view is derived at read
   (overall = outage if any open case is critical, degraded if any
   open case is high priority or breached, else operational) and
   exposes public updates only.
8. **Automation rule registry** — rules (`rule-`) as records: name,
   trigger, condition text, action text, enabled flag. The registry
   **never evaluates a condition and never executes an action** — a
   test pins that a matching rule changes no state. VEN's "automated
   work flow controlled by the Agency" is, at most, this registry's
   shape with an execution engine behind it; the engine is Extended.
9. **Registry reporting & search** — counts by status/priority, the
   derived breach count, alert counts by state, current on-call per
   schedule; substring search over case titles, bodies and requester
   labels. **This is the one core function claimed in this group:**
   VEN's agency "runs real-time reports" in the system. Reporting
   beyond registry counts is Extended.
10. **RBAC + append-only audit** — roles admin / agent / viewer
    (agent cannot write rules or read the audit; viewer is read-only
    without audit), and an append-only audit log recording every
    mutation and, at the service layer, every denied attempt
    (`<action>:denied`). Baseline substrate: carried at 0 claims,
    recorded as carried, not claimed.

Design provenance, stated on the record: the implementation is
Group 26's shipped code reused in full and verified byte-identical
by SHA-256 (21 of 21 files) — our own Apache-2.0 code, the
cross-tier reuse pattern this repo's other categories established
(Analytics L1/L3, Collaboration L1/L3, Cybersecurity L3). The
architecture originates in the Contact Center L2 group's patterns.
No code is copied from any vendor, and no vendor branding appears
anywhere in the build.

## Control baseline (traceability) — Moderate / L2

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Group composition:** both forks are FedRAMP **Moderate**
  (Moderate 2, Low 0, LI-SaaS 0) — recorded per fork in
  `specs/specs.json`. Derivation per the Merge Rule: union of the
  parent baselines = NIST SP 800-53 Rev. 5 **Moderate**, inherited
  in full; the Moderate baseline covers the full NIST SP 800-171
  substrate (110 requirements) that CMMC L2 certifies. This
  baseline section is written fresh for this tier and this group's
  claims; Group 26's Low/L1 section is not reused, and no High-tier
  apparatus is claimed.
- **Feature → control family mapping (this build, at the Moderate
  baseline):**
  - Access control hooks → **AC** (AC-2 account management, AC-3
    access enforcement, AC-6 least privilege), **IA** (IA-2
    identification & authentication — identity is supplied by the
    embedding organization via user/role headers; the service ships
    hooks, not an identity provider). On the CMMC side these answer
    to 800-171's access-control and identification/authentication
    families (3.1, 3.5).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, analysis & reporting — the
    admin-gated audit read and the registry reporting answer here).
    **Precision note, the mirror of Group 26's:** at L1 the audit
    claim held on the FedRAMP Low side only, because FAR
    52.204-21 carries no audit practice. At L2 that limitation does
    **not** apply — 800-171 carries an audit-and-accountability
    family (3.3), which maps onto AU — so the audit claim holds on
    both sides of the crosswalk at this tier.
  - Case / alert / schedule records, derivations and search →
    **SI** (SI-10 information input validation — malformed input is
    rejected, never partially applied; the atomic bulk ingest is an
    SI-10 property) and **SC** (SC-8 transmission confidentiality —
    the server runs over TLS when a certificate is configured).
    Encryption at rest (SC-28) is a deployment-layer control,
    gap-listed below, not claimed here. No sibling in this group
    claims an encryption function (0 of 2; VEN's "protection of
    sensitive employee data" is protection prose, recorded as a
    near-miss under access_control, not an encryption claim).
- **What this tier does not carry, and this build does not claim:**
  the High-tier apparatus from other categories' groups
  (hash-chained tamper-evident audit, logon lockout, a dedicated
  auditor role, 800-172-derived enhancements) is out of scope for a
  Moderate merge; it is not inherited sideways, and the plain
  append-only audit this build carries is the Moderate-appropriate
  form.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations.

## Implementation contract (summary)

Python 3, **standard library only**, package `custsvc` under `src/`,
runnable and testable with `PYTHONPATH=src`:

- `custsvc/access.py` — `User(name, role)`; roles
  `admin|agent|viewer`; admin = all actions, agent = all reads
  except `audit_read` + case/requester/responder/alert/schedule
  writes, viewer = reads except `audit_read`; `require(user,
  action)` raises `PermissionDenied`.
- `custsvc/au
...[truncated 4962 chars]