# Union Spec — Grant Management, CMMC L2 (DeadRamp Phase 2, Group 45)

The merged functional spec for the **Grant Management L2 singleton**:
**1 fork**, category **Grant Management** (a brand-new category — no
group exists at any other tier), CMMC tier **L2** (the member is
FedRAMP **Moderate** in `forks.json` — verified). The member list was
reconciled two ways with **zero diffs**: `forks.json` carries exactly
one Grant Management / L2 entry, and MAP.md's category arithmetic
agrees (Grant Management total **1** = L1 0 + L2 1 + L3-adjacent 0 +
untiered 0). MAP.md's sibling-group sections list only groups of
size 2 or more, so no prose section exists for this singleton; the
arithmetic is the check, as in the earlier singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **FR2311952621**.

## How functions were counted (a new category: the Group 1 method)

Grant Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching text;
the matching sentence is stored as the claim's evidence in the spec
sheet. Marketing prose gets no tags. **17 claims in total, one per
family** — the single fork claims every family its own vocabulary
defines. Counts are a **floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/ARTIFACTS.md`):
sentence 1's "designed to streamline the entire grant lifecycle" is
intent prose and tags nothing (the administration function is
claimed from the administrator-workspace sentence); "views" in the
feature list names no implementable function; "security operations
and governance" is hosting-platform support prose; "identity
management" IS tagged, with a platform disposition.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Grant process administration (pre-award through closeout) | 1 | **Core** — the substrate itself (programs, lifecycle, RBAC, audit) |
| 2 | Application submission & management | 1 | **Core** — application records & lifecycle |
| 3 | Applicant portal (external-facing) | 1 | **Core substrate** — the records and API the portal runs on; the web UI itself is Extended |
| 4 | Grant opportunity exploration | 1 | **Core** — the program registry applicants explore |
| 5 | Post-award report access | 1 | **Core** — post-award report records |
| 6 | Reporting | 1 | **Core slice** — registry summaries computed from records; report-generation engines are Extended |
| 7 | Document management | 1 | **Core** — document metadata & checksum records; the storage engine is Extended |
| 8 | Form design | 1 | **Core slice** — form definitions registered as data; the designer and rendering are Extended |
| 9 | Configurable workflows | 1 | **Core slice** — workflow definitions registered as data, **never executed**; the execution engine is Extended |
| 10 | Secure messaging & communication tools | 1 | **Core** — message records |
| 11 | System notifications | 1 | **Core** — notification records; delivery transport is Extended |
| 12 | Internal notes | 1 | **Core** — staff note records, internal by permission |
| 13 | Applicant account & profile management | 1 | **Core** — organization & profile records (opaque references) |
| 14 | E-signature | 1 | **Core slice** — signature events recorded on document records; the signing engine is Extended |
| 15 | Portal customization & branding | 1 | Extended — a property of the portal UI |
| 16 | Identity management (platform) | 1 | Platform note — the build ships RBAC hooks, not an IdP |
| 17 | Cloud hosting platform (platform note) | 1 | Platform note — delivery prose; deployment layer |

**Named absences, stated plainly:** the description contains **no
money vocabulary at all** — no award amounts, no budgets, no payment
function is claimed — and **no eligibility, merit-scoring, or review
criteria vocabulary**. Neither absence is a gap in the registry
sense: nothing was claimed, so nothing is owed. Both are handled by
explicit core-boundary decisions below, not by silence.

**Core-boundary decisions (recorded, per the singleton precedents).**
(1) *Money.* An application, a review, and a decision are records
the claimed functions presuppose, and those records are not
meaningful without the amounts they carry: an application requests
an amount, a program carries the budget its awards draw against, a
decision records an awarded amount. Money therefore enters the
build as record fields — integer cents, floats rejected — under the
house money discipline. No payment or disbursement function is
claimed or built; awards are records, and moving money is Extended.
(2) *Scoring.* None. Reviews record the reviewer's own
recommendation and note verbatim; decisions record the decider's
outcome. Nothing aggregates, ranks, or scores, and no record shape
carries a score field — pinned by test. (3) *The portal.* The
claimed portal is a web application; this build is the records
substrate and API it runs on. The UI, its branding customization,
and its device adaptation are Extended, named below.

## The Core — what the merged build implements (13 functions)

One coherent, standards-based grant records service that the fork's
claimed functions presuppose, built clean-room from this spec:

1. **Grant programs & membership** — named grant programs (`gp-`):
   title, an opaque sponsor reference, an open window
   (`opens_at`/`closes_at`), and a budget in integer cents, with an
   owner and a member list. Membership is the boundary every other
   core function enforces. The program's open status
   (`upcoming`/`open`/`closed`) is **derived at read** from the
   window against the read clock — never stored.
2. **Applicant organization & profile registry (opaque references)**
   — applicant organizations (`org-`) known only by a
   caller-supplied opaque `ref` and a label. The record shape is
   pinned: no field can hold a real identifier.
3. **Application records & lifecycle** — applications (`app-`) by an
   organization against a program, with a requested amount in
   integer cents, a summary, optional form-response data, and an
   event-driven lifecycle: `draft → submitted → under_review →
   awarded / declined`, plus `withdrawn` from any open state.
4. **Review records** — reviews (`rev-`) recorded while an
   application is under review: the reviewer's own recommendation
   (`award`/`decline`/`abstain`) and note, verbatim. Reviews decide
   nothing by themselves and are never aggregated.
5. **Decision & award records** — a decision (`dec-`) on an
   application under review records the decider's outcome; an
   approval also records the award (`awd-`) with its amount in
   integer cents. Two seams are enforced in the store: the decider
   is never the application's submitter (**separation of duties**),
   and the **award-cap invariant** — the awards recorded against a
   program never exceed its budget — checked before anything is
   stored, so a rejected decision consumes no id and changes
   nothing.
6. **Post-award report records** — report obligations (`rep-`) on an
   award, by kind (`progress`/`financial`/`final`) with a due date,
   and their submissions. A report's status
   (`pending`/`overdue`/`submitted`) is **derived at read** from
   the due date and the submission timestamp — never stored.
7. **Document & signature records** — documents (`doc-`) attached to
   a program, application, or award: name, kind, a SHA-256 checksum,
   and a byte size. Content is never stored. A signature is a
   recorded event on the record (who signed, when); the signing
   engine is Extended.
8. **Form & workflow registries** — form definitions (`frm-`: field
   names, kinds, required flags) and workflow definitions (`wfl-`:
   ordered step names), both registered as data per program. The
   workflow registry **never executes** a definition — registering
   one changes no application, ever, pinned by test. Designers,
   rendering, and execution are Extended.
9. **Communications records** — messages (`msg-`) exchanged with an
   applicant organization (recorded inbound/outbound), notifications
   (`ntf-`) recorded per program or per organization (delivery is
   Extended), and internal notes (`note-`) on applications, which
   stay internal: reading them takes the same staff permission as
   writing them, so a read-only member never sees them.
10. **Search & summary reporting** — literal case-insensitive
    substring search over accessible programs, organizations, and
    application summaries; and a per-program summary computed on
    read from records only: application counts by status, award
    count, awarded and remaining cents, report counts by derived
    status. Counts and sums — never scores.
11. **API access** — every function above is exposed over a REST API
    (JSON), so the service composes with anything that speaks HTTP.
12. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced on
    every operation, layered with program membership (non-members
    cannot read or write a program's content; the platform `admin`
    role can).
13. **Audit log** — an append-only audit trail: every program,
    membership, organization, application, review, decision, award,
    report, document, form, workflow, message, note, and
    notification mutation, and every denied attempt, recorded with
    actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of NIST SP 800-171 Rev. 2 that define CMMC L2. The
  single parent fork sits at Moderate, so the baseline is the
  Moderate baseline, un-diluted (Merge Rule 1) and inherited in
  full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + program membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity
    provider).
  - Decisions & reviews → **AC-5** (separation of duties — the
    decider of an application is never its submitter, enforced in
    the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to the
    `audit_read` permission).
  - Programs / applications / awards / reports → **SI** (SI-10
    information input validation — malformed input, including any
    non-integer amount and any award that would breach the program
    budget cap, is rejected whole, never partially applied) and
    **SC** (SC-8 transmission confidentiality — the server runs
    over TLS when a certificate is configured; encryption at rest
    is a deployment-layer control, stated plainly, not claimed
    here).
  - Opaque-reference privacy is a build discipline answering to
    the same input discipline: because no entity shape has a field
    for a real personal or financial identifier, none can be
    stored, leaked, or transmitted by this build. It is stated as
    a discipline, not dressed up as an additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `grants` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`gp-`, `org-`, `app-`, `rev-`,
`dec-`, `awd-`, `rep-`, `doc-`, `frm-`, `wfl-`, `msg-`, `note-`,
`ntf-`); a failed operation consumes no id and changes nothing.
Amounts are integer cents; a bool, float, or string amount raises
`ValidationError`. Statuses that depend on dates (program open
status, report status) are derived at read and never stored.

- `grants/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; `PERMISSIONS`: admin ⊇ {read,
  create_program, enter, decide, record, manage_members,
  audit_read, admin}, member = {read, create_program, enter,
  decide, record}, viewer = {read}; `require(user, action)` raises
  `PermissionDenied`.
- `grants/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry `{ts, actor, action, target,
  details}`; `.entries()` returns copies. Append-only; optional
  JSONL file.
- `grants/store.py` — `GrantsStore(audit=None)` with the operations
  named in the Core above. Program-scoped operations enforce
  membership (or platform admin) and, for User-like actors, the
  role permission for the operation's action. The store audits
  every successful mutation; the service layer audits denied
  attempts (`action:denied`) and audit reads, so nothing is
  recorded twice.
- `grants/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User` /
  `X-Role` headers (role must match the registry). Endpoints per
  the group README. Errors are JSON `{error}` with 400/401/403/404
  as applicable. Denied attempts are audited.
- `grants/__main__.py` — `python -m grants serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's).
- `grants/errors.py` — `GrantsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. **93 tests**, including the **negative
control**: a mutant store with the award-cap check removed accepts
an over-cap award the canonical expectation rejects — and the
external mutation drill (patching `_check_award_cap` to a no-op in
the real `store.py`) makes exactly 4 tests fail; see
`tests/README.md` for the drill record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Applicant portal web application (the responsive browser UI
  itself, including branding customization & rendering and device
  adaptation)
- Workflow execution engine (routing and orchestration of
  configured workflows; the registry holds definitions only)
- Form designer & form rendering engine (the registry holds
  definitions only)
- Document storage & content management engine (the build holds
  metadata and checksums only)
- E-signature signing engine (the signing ceremony and its
  cryptographic binding; the build records signature events)
- Payment / disbursement execution for awards (awards are records;
  no money moves in this build)
- Reporting & analytics engines beyond registry summaries
  (dashboards, ad-hoc report generation, data exports)
- Notification & message delivery transport (email / SMS / push
  delivery; the build records them)
- Applicant matching & opportunity recommendation
- Eligibility determination & merit-scoring engines (nothing is
  scored in this build, by design)
- Closeout automation & financial reconciliation engines
- Identity provider / identity management service (IA-2 stays with
  the embedding organization; the fork claims it of its hosting
  platform)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **17 tagged claims** (one per
  taxonomy family, each with its source sentence as evidence).
- Core: **13 / 13** core functions implemented, at the Moderate/L2
  baseline, each with tracing tests.
- Tests: **93 run, 93 passed**, including the mutation-verified
  award-cap negative control.
- Extended: the 12 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
