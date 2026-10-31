# Union Spec — System Administration, CMMC L2 (DeadRamp Phase 2, Group 54)

The merged functional spec for the **System Administration L2
singleton**: **1 fork**, category **System Administration** (a
brand-new category — no group exists at any other tier), CMMC
tier **L2** (the member is FedRAMP **Moderate** in `forks.json`
— verified). The member list was reconciled two ways with
**zero diffs**: `forks.json` carries exactly one System
Administration entry (and exactly one at L2), and MAP.md's
category arithmetic agrees (System Administration total **1** =
L2 1, all other tiers 0; MAP.md's own reading of this category
calls it pure infrastructure). MAP.md's sibling-group sections
list only groups of size 2 or more, so no prose section exists
for this singleton; the arithmetic is the check, as in the
earlier singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description
and its function claims tagged from that description, every
claim carrying the source sentence as evidence. Source: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product record joined by FedRAMP ID
**FR2415334644**.

**What this fork actually is, stated plainly:** the single
System Administration fork is the U.S. Department of
Agriculture's AgCloud Managed Platform Services (AMPS) — by its
own description, a **General Support System (GSS)** made up of
operating systems and services, designed to run on third-party
cloud hosting platforms, under which the operator (named in the
prose only as DISC) **maintains the full management of the OS
and services** for USDA customers delivering applications on a
FedRAMP CSP hosting environment. The system inherits controls
from the underlying CSP, runs on a Highly Available network,
and is not publicly accessible: it is available only to
organizations who contract with the operator. The fork is a
government agency's own managed-services offering, spec'd by
the same rules as any vendor fork, from its marketplace
description only. What the description never describes is a
records system — the records substrate below is what the
claimed functions *presuppose* (the registry of the customer
organizations, managed systems, applications, service requests,
changes, and control dispositions the managed service acts on),
and the management work itself — administering, patching,
provisioning, and tending those systems — is a service
performed by people and platforms, named as gaps from the
fork's own verbs. The build is that substrate. It administers
no live system and performs no management work.

## How functions were counted (a new category: the Group 1 method)

System Administration has no parent group, so there is no
inherited taxonomy. The taxonomy below was defined **from this
fork's own description**: families are named from the
description's own functional vocabulary, each with a verbatim
match pattern, matched against the description's sentences by
`scratch/extract.py`. A function is claimed **only** when a
sentence contains matching text; the matching sentence is
stored as the claim's evidence in the spec sheet. Marketing
prose gets no tags. **8 claims in total, one per family**.
Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in
`scratch/ARTIFACTS.md`): sentence 3 (0-indexed; the "major part
of DISC's cloud service offering" sentence) tags nothing — it
restates the application-delivery purpose as offering
positioning; the description's prose says the operator's
controls are maintained "at the High baseline level", but the
offering's own impact level in the same source record is
Moderate and the registry tiers it L2 — the phrase is recorded
inside its evidence sentence and is **not** read as re-tiering
the offering, and this build builds to Moderate/L2; DISC is
never expanded in the description and is recorded unexpanded;
the source record's `business_categories` is empty (`[]`) while
`forks.json` files the fork under System Administration — both
facts recorded as-is, neither treated as a functional claim;
the registry service model is PaaS for what the prose describes
as a managed-services GSS — recorded as-is; the description
contains **no monitoring, incident-response, ticketing, or
service-level vocabulary** — those are named absences, not
attributed functions (see below).

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | General Support System (GSS) of operating systems & services | 1 | **Core substrate** — the registries below are the GSS's records surface; the GSS's runtime platforms themselves are the platform layer |
| 2 | Full management of operating systems & services | 1 | **Core slice** — management work as service request and change records; the administration operations themselves are Extended |
| 3 | Application delivery on the managed platform | 1 | **Core slice** — application registration records on managed systems; the delivery / hosting runtime is the CSP's environment, Extended |
| 4 | Operation on third-party CSP hosting platforms | 1 | Platform note — the hosting platforms are outside the fork's own security boundary by its own statement; systems record only an opaque `platform_ref` |
| 5 | Control inheritance from the underlying CSP | 1 | **Core** — control records carrying each control's recorded source (`inherited` / `local` / `shared`) per managed system |
| 6 | CSP virtualization of computing environments | 1 | Extended — the virtualization engine is the CSP's |
| 7 | Highly Available (HA) network, up-time & redundancy | 1 | Extended — HA network operation, redundancy, and failover are platform operations |
| 8 | Access restricted to contracting organizations | 1 | **Core** — customer organizations with membership as the access boundary; the platform is not publicly accessible, and neither is any record in this build |

**Named absences, stated plainly:** the description contains
**no monitoring or alerting vocabulary**, no incident-response
function, no ticketing or help-desk vocabulary (service request
*records* are Core as the records form of the management claim —
see boundary decision 3 — but no ticket system is claimed), no
service-level or SLA vocabulary (request due dates are the
substrate's records discipline, not an SLA claim), no backup or
disaster-recovery function, no identity or SSO administration
beyond the access-restriction claim, and no reporting family
(the Core's registry summaries are substrate for the management
claims, not a reporting claim).

**Core-boundary decisions (recorded, per the singleton
precedents).** (1) *The scoping container.* Every claimed
function is exercised for customer organizations who contract
with the operator ("only available to organizations who
contract with DISC"), so the substrate is scoped by customer
organizations with membership, the house scoping pattern: the
organization record is known only by an opaque `ref` and a
label, and membership is the records form of the fork's
contract-gated access claim. (2) *Management is work; the
substrate holds its records.* "Full management of the OS and
services" is performed by the operator's people and platforms.
In a records substrate, that work exists as service request
records (what was asked, against which system, due when, and
its lifecycle) and change records (what was proposed, who
decided, whether it closed). Recording a request performs no
work, and closing a change alters no system or application
record — both pinned by test. (3) *Requests are records, not a
ticketing claim.* The description names no ticket system; the
request registry is the minimal records presupposition of a
managed service (work cannot be managed, audited, or traced
without a record of what was requested), recorded here as a
boundary decision rather than dressed up as a claim. (4)
*Overdue is derived, never stored.* Whether an open request is
past its due date depends on the read clock, so `overdue` is
derived at read from the stored due date and lifecycle status
and is never stored: a stored flag would itself go stale inside
the store, which is exactly the failure derivation exists to
prevent. Lifecycle status, by contrast, is event-driven, so it
is stored. (5) *Control records carry dispositions, not
posture.* The inheritance claim presupposes knowing, per
system, which controls are inherited from the hosting platform
and which are implemented locally — so control records carry
the recorded source verbatim. The store derives no compliance
posture, score, or health value from them, pinned by a
recursive key scan over every view. (6) *No live-system
identifiers.* Managed systems and applications are known only
by opaque caller-chosen references and labels, and no entity
shape has a field for a hostname, an IP address, a credential,
or any identifier of a live system — so none can be stored,
leaked, or transmitted by this build. The hosting platform
itself is likewise only an opaque `platform_ref`.

## The Core — what the merged build implements (12 functions)

One coherent, standards-based system-administration records
service that the fork's claimed functions presuppose, built
clean-room from this spec:

1. **Customer organizations & membership** — customer
   organizations (`org-`): an opaque caller-supplied `ref` and
   a label, an owner, and a member list. Membership is the
   boundary every other core function enforces — the records
   form of the fork's contract-gated access.
2. **Managed system registry** — managed systems (`sys-`)
   belonging to an organization: an opaque `ref` (unique per
   organization), a label, a `kind` from the description's own
   vocabulary (`operating_system` / `platform_service`), and an
   opaque `platform_ref` for the third-party hosting platform
   it runs on. The record shape is **pinned** — exactly nine
   keys, none of which can hold a hostname, address, or
   credential of a live system. A system's lifecycle `state`
   (`registered` / `retired`) is event-driven and stored.
3. **Application registry** — applications (`app-`) hosted on a
   managed system: an opaque `ref` (unique per organization), a
   label, and the hosting system. The record shape is
   **pinned** — exactly eight keys. Lifecycle `state` is
   event-driven and stored.
4. **Service request records** — requests (`req-`) against a
   managed system (optionally an application hosted on it), of
   kinds `support`, `maintenance`, `access`, `other`, with a
   verbatim summary, a due date, and the lifecycle
   `open → in_progress → resolved`, plus `cancelled`.
   Cancellation is restricted to the requester or a platform
   admin. Recording a request performs no work.
5. **Derived request status** — a request's read view derives
   `overdue` (still open or in progress, and its due date is
   before the read date; resolved and cancelled requests are
   never overdue) at read time. It is never stored — the stored
   request record carries no such key, pinned by test.
6. **Change records** — changes (`chg-`) against a managed
   system (optionally an application on it), of kinds `patch`,
   `configure`, `provision`, `decommission`, with a verbatim
   summary and the lifecycle `requested → approved → closed`,
   plus `rejected` and `cancelled`. Two seams are enforced in
   the store: the decider is never the requester (**separation
   of duties**), and closing a change alters no system or
   application record — the records are the management surface;
   the work that would carry a change out is Extended.
7. **Control inheritance records** — control records (`ctl-`)
   per managed system: a control reference and its recorded
   `source` — `inherited` (satisfied by the underlying hosting
   platform), `local` (implemented on the managed platform), or
   `shared` — with an optional note, one record per control per
   system. Dispositions are carried verbatim; no posture is
   derived from them.
8. **Registry search** — literal case-insensitive substring
   search over accessible systems, applications, requests, and
   changes.
9. **Registry summary** — a per-organization summary computed
   on read from records only: system counts by kind and state,
   application count, request counts by status plus the
   derived overdue count, change counts by status, and control
   counts by source. Counts — never scores.
10. **API access** — every function above is exposed over a
    REST API (JSON), so the service composes with anything
    that speaks HTTP.
11. **Access control** — role-based access hooks: platform
    roles `admin`, `member`, `viewer` with a permission matrix
    enforced on every operation, layered with organization
    membership (non-members cannot read or write an
    organization's content; the platform `admin` role can).
12. **Audit log** — an append-only audit trail: every
    organization, membership, system, application, request,
    change, and control mutation, and every denied attempt,
    recorded with actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to
  the 110 practices of NIST SP 800-171 Rev. 2 that define CMMC
  L2. The single parent fork sits at Moderate, so the baseline
  is the Moderate baseline, un-diluted (Merge Rule 1) and
  inherited in full (Merge Rule 2). The fork's prose mentions
  its operator's controls being maintained at a High baseline
  level; per the wording-artifact log, that phrase does not
  re-tier the offering, and no High-baseline claim is made here.
- **Feature → control family mapping (this build):**
  - Access control (platform roles + organization membership)
    → **AC** (AC-2 account management, AC-3 access enforcement,
    AC-6 least privilege), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the service ships
    hooks, not an identity provider).
  - Change decisions → **AC-5** (separation of duties — the
    decider of a change is never its requester, enforced in
    the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of
    audit records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to
    the `audit_read` permission).
  - Control inheritance records → **CA** (CA-2 control
    assessments' records surface: which controls rest on which
    source, recorded per system) — stated as records
    traceability, not as an assessment claim; the assessments
    themselves are the operator's and assessors' work.
  - Systems / applications / requests / changes / controls →
    **SI** (SI-10 information input validation — malformed
    input, including an unparseable or impossible due date, a
    system kind outside the description's vocabulary, or an
    application registered to another organization's system, is
    rejected whole, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS
    when a certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed
    here).
  - Opaque-reference privacy is a build discipline answering
    to the same input discipline: because no entity shape has
    a field for a real hostname, address, or credential, none
    can be stored, leaked, or transmitted by this build. It is
    stated as a discipline, not dressed up as an additional
    control claim.
- **Caveat, same as the crosswalk's:** this mapping states
  which baseline families the build's features answer to. It
  is not a FedRAMP authorization and not a CMMC certification,
  and it does not claim either. FedRAMP authorizes products;
  CMMC certifies organizations; the tier is a planning and
  matching equivalence, never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `sysadmin` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`,
`sys-`, `app-`, `req-`, `chg-`, `ctl-`); a failed operation
consumes no id and changes nothing. Due dates are `YYYY-MM-DD`
calendar dates; anything else raises `ValidationError`. A
request's `overdue` flag exists only on read views, never on
the stored record.

- `sysadmin/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read,
  create_org, enter, decide, record, manage_members,
  audit_read, admin}, member = {read, create_org, enter,
  decide, record}, viewer = {read}; `require(user, action)`
  raises `PermissionDenied`.
- `sysadmin/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)` → entry `{ts, actor, action,
  target, details}`; `.entries()` returns copies. Append-only;
  optional JSONL file.
- `sysadmin/store.py` — `SysadminStore(audit=None)` with the
  operations named in the Core above. Organization-scoped
  operations enforce membership (or platform admin) and, for
  User-like actors, the role permission for the operation's
  action (`enter` for creates/registrations/retires and request
  starts/cancels, `decide` for change decisions, `record` for
  request resolutions and change closes, `read` for reads,
  `manage_members` for membership changes). The store audits
  every successful mutation; the service layer audits denied
  attempts (`action:denied`) and audit reads, so nothing is
  recorded twice. Named seams: `_is_overdue` (the overdue
  derivation) and `_check_decider_not_requester` (the AC-5 seam
  on change decisions).
- `sysadmin/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via
  `X-User` / `X-Role` headers (role must match the registry).
  Endpoints per the group README. Errors are JSON `{error}`
  with 400/401/403/404 as applicable. Denied attempts are
  audited.
- `sysadmin/__main__.py` — `python -m sysadmin serve --host
  --port [--audit-log PATH] [--certfile --keyfile]` with demo
  users `alice=admin, bob=member, carol=viewer` (documented as
  demo identities; production identity is the embedding
  organization's).
- `sysadmin/errors.py` — `SysadminError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring
or module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative
control**: a mutant store whose overdue derivation always
reports not overdue is shown to violate the canonical
expectation — and the external mutation drill (patching
`_is_overdue` in the real `store.py`) makes a named set of
tests fail; see `tests/README.md` for the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

From this fork's own claims (the work and engines behind the
records), named from the fork's own verbs:

- Managed OS & services administration operations (the full
  management itself: administering, configuring, patching,
  hardening, and tending operating systems and services —
  performed by the operator's people and platforms, never by
  this substrate)
- System provisioning & deployment operations (standing up OS
  instances and services on the CSP platform; the substrate
  registers systems, it does not provision them)
- Application delivery & hosting runtime (the CSP hosting
  environment applications are delivered on and run in)
- Virtualization engine (the CSP's virtualization of computing
  environments)
- High-availability network operation (the HA network,
  redundancy, and failover the fork runs on)
- Third-party CSP hosting platforms (outside the fork's own
  security boundary by its own statement; the substrate records
  only an opaque platform reference)

Platform-layer: control inheritance means part of the fork's
own baseline is satisfied by the underlying CSP platform — a
platform-layer fact about the fork, recorded in Core as control
dispositions; encryption at rest is deployment-layer (TLS when
configured); the fork's customers' own environments and the
operator's staffing are outside any software build; demo
identities are hooks, not an IdP (IA-2 stays with the embedding
organization).

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **8 tagged claims** (one
  per taxonomy family, each with its source sentence as
  evidence; the taxonomy was defined from the fork's own
  description).
- Core: **12 / 12** core functions implemented, at the
  Moderate/L2 baseline, each with tracing tests.
- Tests: see `tests/README.md` for the delivered count,
  including the mutation-verified derived-overdue negative
  control.
- Extended: the 6 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
