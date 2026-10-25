# Union Spec — Finance, CMMC L2 (DeadRamp Phase 2, Group 31)

The merged functional spec for the Finance L2 sibling group:
**2 forks**, category **Finance**, CMMC tier **L2** (every member is
FedRAMP **Moderate** in `forks.json` — verified, so the group is
single-tier and the merge takes the group baseline in full, per Merge
Rule 2). The member list in `forks.json` was reconciled against
`MAP.md`'s "Finance — L2 (2)" section with **zero diffs**, asserted
programmatically in `scratch/extract.py`.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
both descriptions were present in the cached dataset.

The two siblings:

- **DailyPay for Government** (DailyPay, FR2623848170) — on-demand
  pay: instant access to earned wages plus financial wellness
  solutions, delivered as SaaS to governments and their contractors.
- **Groupize** (Groupize, Inc., FR2626247309) — group travel for
  meetings: booking, spend, and traveler experience in one place,
  with real-time reporting.

## How functions were counted

A fixed 8-function taxonomy for this category (defined from the two
descriptions) was matched against each offering's own public
description. A function is claimed for a fork **only** when the
description contains matching text; the matching sentence is stored
as the claim's evidence in the spec sheet. 8 claims total, 4 per
fork. Counts are a **floor**, not a ceiling: both descriptions are
short (DailyPay's is four sentences; Groupize's is one sentence).

Wording-artifact corrections applied to the matcher are recorded in
`scratch/extract.py` (five of them). The ones that matter for reading
this spec:

- **DailyPay's "the leader in On-Demand Pay" earns no tag.** It is a
  superlative market-position phrase. The `earned_wage_access` claim
  rests on the functional sentence: the platform "can deliver
  instant access to earned wages". A category name inside a
  superlative is not a function claim.
- **"Traveler experience" earns no tag.** Groupize's single sentence
  names booking, spend, travel management, and real-time reporting;
  "traveler experience" names no implementable function and is
  recorded as prose, not a claim.
- **A source category label is not a claim.** Groupize's source
  record carries `business_categories` including 'Governance, Risk,
  and Compliance (GRC)', but its description contains no sentence
  claiming a GRC function, so no GRC claim is tagged. Conversely
  DailyPay's source record carries `business_categories: []` while
  `forks.json` files it under Finance; both facts are recorded
  as-is in the spec sheets.

**The two siblings share zero claimed families.** The union is two
half-domains — earned-wage finance and group-travel finance — over
one shared substrate (programs, opaque-reference participants,
integer-cent records, budgets, reporting, approvals, audit). Neither
description claims any part of the other's domain, and this spec
does not pretend otherwise: the differences are preserved, not
averaged away.

## Money representation, records-not-execution, and privacy

Three stated disciplines govern every money-bearing function below,
inherited from the Accounting group's doctrine:

- **Integer cents only.** Every amount field is named `*_cents` and
  must be a Python `int` — booleans are rejected, and floats are
  rejected even when integral, so no binary floating-point value can
  ever enter a total. All arithmetic is integer arithmetic and
  therefore exact by construction.
- **Records, not execution.** Payments, transfers, and disbursements
  are *recorded*, never executed against real rails. A disbursement
  record states that money moved on an external rail (the employer's
  payroll/banking infrastructure); this build moves no money, holds
  no balances on any rail, and books no travel. Booking records
  likewise record reservations made elsewhere.
- **Opaque references only.** People and accounts are known to the
  build exclusively by caller-supplied opaque references
  (`participant` records carry a `ref` string and a kind, nothing
  else). No entity shape has a field that could hold a real name,
  bank account number, card number, or government identifier; the
  record shapes are pinned by tests so no such field can appear.

## Function ranking — both siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Earned wage access (on-demand pay) | 1 | 50% | **Core** (accrual, access-request, and disbursement *records* with the earned-cap invariant; instant money movement itself is Extended — see the long tail) |
| 2 | Financial wellness solutions | 1 | 50% | **Core** (offering registry + enrollment records; the wellness tools themselves are Extended) |
| 3 | Travel booking (air & hotel) | 1 | 50% | **Core** (booking *records* with lifecycle; live inventory/ticketing is Extended) |
| 4 | Group & meeting travel management | 1 | 50% | **Core** (the program/traveler/booking substrate the claim presupposes) |
| 5 | Spend management | 1 | 50% | **Core** (budgets per program per period, spend-vs-budget computed from records) |
| 6 | Reporting & analytics | 1 | 50% | **Core** (program summaries computed on read from records; "real-time" streaming is a property of the sibling's platform, stated plainly) |
| 7 | Open platform & APIs | 1 | 50% | **Core** (the service is API-first) |
| 8 | SaaS / cloud delivery (platform note) | 1 | 50% | Platform note (single-tenant reference deployment; see baseline section) |

Baseline families carried at **zero claims in this group** (they are
in the Core as L2 baseline hooks, not because either description
claims them — the same posture as the sibling groups): access
control & authentication, workflow & approvals (the shared state
machine with separation of duties), and the audit trail.

### The long tail — Extended, and functions named as NOT claimed

Extended functions are specified here, ranked, and **not**
implemented in this build; they are registered in the repo's gap
registry for the final batch:

- **Instant disbursement execution / payment rails** (ACH, wire,
  card networks) — the execution remainder of `earned_wage_access`.
  The claim is *access to earned wages*; the Core records accruals,
  access decisions, and disbursements. Moving money in real time is
  an engine on external rails, and records-not-execution is this
  build's stated discipline.
- **Travel booking execution engines** (live air/hotel inventory,
  ticketing, reservation systems) — the execution remainder of
  `travel_booking`. The Core holds booking records with a lifecycle;
  it queries no inventory and issues no ticket.
- **Financial wellness delivery tools** (the budgeting, coaching,
  and savings products behind the offering registry) — the execution
  remainder of `financial_wellness`. The Core registers offerings
  and enrollments as records.
- **Streaming / real-time reporting pipelines** — the Core computes
  summaries on read from records; a streaming analytics pipeline is
  an engine, not a registry function.

Named here so the category record is complete — functions a
"Finance" label suggests that **neither description claims at all**
(zero claims; excluded from the union, not silently dropped):

- **Banking integration & account verification** — no sentence
  claims linking or verifying real bank accounts; the entity shapes
  forbid real account identifiers by design.
- **Payroll system integration & wage calculation** — DailyPay
  presupposes an employer's payroll as the *source* of earned
  wages, but claims no payroll function. Accruals in the Core are
  records of amounts computed elsewhere.
- **Lending & credit** — earned wage access as claimed is access to
  *already-earned* wages only. Nothing here lends, underwrites, or
  advances unearned money.
- **Trading & investment execution** — claimed by neither sibling.
- **Tax reporting & remittance** — claimed by neither sibling.
- **GRC platform functions** — present only as a source category
  label on Groupize's record; no descriptive sentence claims them
  (see the corrections above).

## The Core — what the merged build implements (11 functions)

One coherent, standards-based finance records service that both
siblings' platforms presuppose, built clean-room from this spec:

1. **Programs & members** — named programs (the container: one
   employer or agency finance program) with an owner, a member
   list, and provenance. Membership is the boundary every other
   core function enforces.
2. **Participant & traveler registry (opaque references)** —
   participants known only by a caller-supplied opaque `ref` and a
   kind (`employee` or `traveler`), with an active/inactive status.
   The record shape is pinned: no field can hold a real identifier.
3. **Earned-wage accrual & access records** — per participant per
   pay period (`YYYY-MM`), an accrual records wages already earned
   (integer cents, computed by the employer's payroll elsewhere).
   An access request draws against one period's accrual and runs
   the approval machine (below); the **earned-cap invariant** —
   pending plus approved plus disbursed amounts for a period never
   exceed that period's earned amount — is enforced at request
   time. Approving is separated from requesting (separation of
   duties). A disbursement record then records, after the fact,
   that an approved amount was disbursed on external rails.
   Accrual views derive accessed / pending / available amounts on
   read; nothing derived is stored.
4. **Travel booking records** — booking records (air or hotel,
   date range, amount in cents) for a traveler participant, with a
   `recorded → confirmed / cancelled` lifecycle. Records of
   reservations made on external systems; the build books nothing.
5. **Spend budgets & tracking** — a budget per program per period:
   planned cents per category. **Spend-vs-budget** computes spent
   amounts from records (non-cancelled bookings by kind; disbursed
   wage access under the `earned_wage` category), variance, and
   over-budget flags — computed, never asserted.
6. **Financial wellness offering registry** — wellness offerings
   (title + kind: education, coaching, budgeting, savings,
   counseling) registered per program, with participant enrollment
   records. The registry is the claim's substrate; the wellness
   tools themselves are Extended.
7. **Reporting** — a per-period program summary computed on read
   from records only: participant count, earned / accessed /
   disbursed / pending wage totals, booking counts and totals by
   kind, wellness enrollment count.
8. **Workflow & approvals** — the state machine for access
   requests: `requested → approved / denied`, `approved →
   disbursed` (via a disbursement record), `requested / denied →
   void`. Decision (approve/deny) requires an actor other than the
   request's creator (separation of duties, AC-5); void is limited
   to the creator, the program owner, or a platform admin.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with program membership
    (non-members cannot read or write a program's content; the
    platform `admin` role can).
11. **Audit log** — an append-only audit trail: every program,
    membership, participant, accrual, access-request, disbursement,
    booking, budget, and wellness mutation, and every denied
    attempt, recorded with actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110
  practices of NIST SP 800-171 Rev. 2 that define CMMC L2. Both
  parent forks sit at Moderate, so the union baseline is the
  Moderate baseline, un-diluted (Merge Rule 1) and inherited in
  full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + program membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity
    provider).
  - Workflow & approvals → **AC-5** (separation of duties — the
    decider of an access request is never its creator, enforced in
    the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to the
    `audit_read` permission).
  - Accruals / access requests / disbursements / bookings / budgets
    → **SI** (SI-10 information input validation — malformed input,
    including any non-integer amount and any access request that
    would breach the earned cap, is rejected whole, never partially
    applied) and **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
  - Opaque-reference privacy is a build discipline answering to the
    same input discipline: because no entity shape has a field for
    a real financial identifier, none can be stored, leaked, or
    transmitted by this build. It is stated as a discipline, not
    dressed up as an additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `finance` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`prog-`, `part-`, `acc-`, `req-`,
`dis-`, `bkg-`, `bud-`, `wel-`, `enr-`); a failed operation consumes
no id and changes nothing. All timestamps are UTC ISO-8601. All
money is integer cents (see the money section above). Dates are ISO
calendar dates (`YYYY-MM-DD`); a pay/fiscal period is the string
`YYYY-MM`, validated (month 01–12).

- `finance/errors.py` — `FinanceError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `FinanceError`).
- `finance/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `read, create_program, enter,
  decide, record, manage_members, audit_read, admin`. `PERMISSIONS`:
  admin ⊇ all eight; member = {read, create_program, enter, decide,
  record}; viewer = {read}. `permissions_for(role)`, `can(user,
  action)`, `require(user, action)` raising `PermissionDenied`.
- `finance/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)`; `.entries()` returns entry dicts
  with keys `ts, actor, action, target, details`. Append-only;
  optional JSONL file persistence; reloads an existing file on
  construction.
- `finance/store.py` — `FinanceStore(audit=None)`. The store
  records every successful mutation to its audit log (when one is
  attached) with the action names used below; the HTTP layer records
  denials and `audit_read` only, never duplicating store records.
  Two boundaries on every program-scoped operation: the actor must
  be a program member or hold the platform `admin` role, else
  `PermissionDenied`; and the operation's role permission is
  required when the actor is a User-like object (a plain string
  actor carries identity but no role, so role enforcement for those
  happens in the service layer). Validation always precedes
  mutation: a failed operation changes nothing, consumes no id.
  Amounts: any amount that is not an `int` (booleans included)
  raises `ValidationError`. A missing object (including an id that
  belongs to another program) raises `NotFoundError`; a malformed
  reference or value inside a payload raises `ValidationError`.
  Methods:
  - `create_program(name, actor)` → `{id, name, owner, members,
    created_by, created_utc}`; the creator is owner and first
    member. Audits `program_create`.
  - `list_programs(actor)` → program dicts the actor may see
    (member of, or platform admin). `get_program(program_id,
    actor)` → one dict (`NotFoundError`, or `PermissionDenied` for
    a non-member).
  - `add_member(program_id, username, actor)` → updated program
    dict. Only the program owner or a platform admin may add;
    adding an existing member raises `ValidationError`. Audits
    `member_add`.
  - `create_participant(program_id, ref, kind, actor)` (action
    `enter`) → `{id, program_id, ref, kind, status, created_by,
    created_utc}` with `status` `"active"`. `ref` must be a
    non-empty string, unique within the program (duplicate →
    `ValidationError`); `kind` must be one of `employee`,
    `traveler`. **The returned dict has exactly these keys** — the
    privacy pin. Audits `participant_create`.
    `get_participant(program_id, participant_id, actor)`;
    `list_participants(program_id, actor, kind=None)` in creation
    order (an unknown `kind` filter → `ValidationError`).
  - `set_participant_status(program_id, participant_id, status,
    actor)` (action `enter`): status `active` or `inactive` (else
    `ValidationError`) → updated participant dict. Audits
    `participant_status`.
  - `record_accrual(program_id, participant_id, period,
    earned_cents, actor)` (action `enter`) → `{id, program_id,
    participant_id, period, earned_cents, created_by, created_utc}`.
    The participant must exist in this program (`NotFoundError`)
    and be of kind `employee` (else `ValidationError`); `period`
    must be a valid `YYYY-MM`; `earned_cents` an int ≥ 0; a second
    accrual for the same (participant, period) → `ValidationError`.
    Audits `accrual_record`. `list_accruals(program_id, actor,
    participant_id=None)` → accrual **views** in creation order.
  - `get_accrual(program_id, accrual_id, actor)` → the accrual
    record plus derived fields `{accessed_cents, pending_cents,
    available_cents}`: `accessed_cents` is the sum of amounts of
    access requests for the same (participant, period) in status
    `approved` or `disbursed`; `pending_cents` the sum in status
    `requested`; denied and void requests count toward neither;
    `available_cents = earned_cents - accessed_cents -
    pending_cents`. Derived on read, never stored.
  - `request_access(program_id, participant_id, period,
    amount_cents, date, actor)` (action `enter`) → `{id,
    program_id, participant_id, period, amount_cents, date, status,
    created_by, created_utc, decided_by, decided_utc,
    disbursement_id}`. The participant must exist (`NotFoundError`)
    and be an `employee` (`ValidationError`); an accrual must exist
    for (participant, period) (else `ValidationError`); `date` must
    be a valid ISO date; `amount_cents` a positive int. **The
    earned cap:** `amount_cents` plus the period's committed total
    (pending + accessed, as defined for `get_accrual`) must not
    exceed the accrual's `earned_cents` — else `ValidationError`
    and nothing is stored. The cap comparison lives in a
    module-level helper `_check_access_cap(earned_cents,
    committed_cents, amount_cents)` that raises `ValidationError`
    when `committed_cents + amount_cents > earned_cents` (this is
    the negative control's target). Initial status `requested`;
    `decided_by`/`decided_utc`/`disbursement_id` start as None.
    Audits `access_request`. `get_access_request(program_id,
    request_id, actor)`; `list_access_requests(program_id, actor,
    status=None)` in creation order (an unknown `status` filter →
    `ValidationError`; valid statuses are `requested`, `approved`,
    `denied`, `disbursed`, `void`).
  - `decide_access(program_id, request_id, approve, actor)` (action
    `decide`): status must be `requested` (else `ValidationError`);
    `approve` must be a bool (else `ValidationError`); the actor's
    name must differ from `created_by` (else `PermissionDenied` —
    separation of duties). Sets status `approved` or `denied`,
    `decided_by`, `decided_utc`. Audits `access_approve` or
    `access_deny`.
  - `void_access(program_id, request_id, actor)` (action `enter`):
    status `requested` or `denied` → `void`; only the creator, the
    program owner, or a platform admin (else `PermissionDenied`).
    Audits `access_void`.
  - `record_disbursement(program_id, request_id, date, actor,
    method="")` (action `record`) → `{id, program_id, request_id,
    participant_id, period, amount_cents, date, method, recorded_by,
    recorded_utc}`. The request must exist (`NotFoundError`) and be
    in status `approved` (else `ValidationError`); `date` valid;
    `method` a string (an opaque label of the external rail the
    disbursement used, recorded after the fact — this build
    executes nothing). `amount_cents`, `participant_id`, and
    `period` are copied from the request. The request's status
    becomes `disbursed` and its `disbursement_id` is set. Audits
    `disbursement_record`. `list_disbursements(program_id, actor,
    request_id=None)` in creation order.
  - `create_booking(program_id, participant_id, kind, start_date,
    end_date, amount_cents, actor)` (action `enter`) → `{id,
    program_id, participant_id, kind, start_date, end_date,
    amount_cents, status, created_by, created_utc}`. `kind` must be
    `air` or `hotel`; the participant must exist (`NotFoundError`)
    and be a `traveler` (`ValidationError`); both dates valid ISO
    dates with `end_date` not before `start_date`; `amount_cents`
    an int ≥ 0. Initial status `recorded`. Audits `booking_create`.
    `get_booking(program_id, booking_id, actor)`;
    `list_bookings(program_id, actor, status=None, kind=None)` in
    creation order (unknown filter values → `ValidationError`;
    valid statuses are `recorded`, `confirmed`, `cancelled`).
  - `confirm_booking(program_id, booking_id, actor)` (action
    `record`): status `recorded` → `confirmed` (else
    `ValidationError`). Audits `booking_confirm`.
    `cancel_booking(program_id, booking_id, actor)` (action
    `enter`): status `recorded` or `confirmed` → `cancelled` (else
    `ValidationError`). Audits `booking_cancel`.
  - `set_budget(program_id, period, lines, actor)` (action
    `enter`) → `{id, program_id, period, lines, total_cents,
    created_by, created_utc, updated_utc}`. `period` valid
    `YYYY-MM`. `lines` is a list of at least one dict `{category,
    limit_cents}`: category a non-empty string, `limit_cents` an
    int ≥ 0, a repeated category in one call → `ValidationError`.
    One budget per (program, period): if one exists, its lines and
    total are replaced, its `id`, `created_by`, and `created_utc`
    are kept, and `updated_utc` is refreshed. Audits `budget_set`.
    `get_budget(program_id, period, actor)` → the budget dict
    (`NotFoundError` if none was set for that period).
  - `spend_vs_budget(program_id, period, actor)` (action `read`) →
    `{program_id, period, lines, total_budgeted_cents,
    total_spent_cents, total_variance_cents, unbudgeted}`; requires
    a budget for the period (else `NotFoundError`). Each line:
    `{category, limit_cents, spent_cents, variance_cents,
    over_budget}` with `variance_cents = limit_cents -
    spent_cents` and `over_budget = spent_cents > limit_cents`.
    `spent_cents` for a category is the sum of amounts of bookings
    whose `kind` equals the category, whose status is `recorded`
    or `confirmed`, and whose `start_date` falls in the period;
    for the category `earned_wage` it is instead the sum of
    disbursement amounts whose `date` falls in the period.
    `unbudgeted` lists `{category, spent_cents}` for categories
    with spending in the period but no budget line (booking kinds
    present in the period, plus `earned_wage` when disbursements
    exist in the period), sorted by category. Totals:
    `total_budgeted_cents` is the sum of line limits;
    `total_spent_cents` is the sum of line spent amounts plus
    unbudgeted spent amounts; `total_variance_cents =
    total_budgeted_cents - total_spent_cents`.
  - `create_wellness_offering(program_id, title, kind, actor)`
    (action `enter`) → `{id, program_id, title, kind, created_by,
    created_utc}`. `title` a non-empty string; `kind` one of
    `education`, `coaching`, `budgeting`, `savings`, `counseling`.
    Audits `wellness_create`. `get_wellness_offering(program_id,
    offering_id, actor)`; `list_wellness_offerings(program_id,
    actor)` in creation order.
  - `enroll_participant(program_id, offering_id, participant_id,
    actor)` (action `enter`) → `{id, program_id, offering_id,
    participant_id, status, created_by, created_utc}` with status
    `enrolled`. The offering and the participant must exist in this
    program (`NotFoundError`); a duplicate enrollment for the same
    (offering, participant) → `ValidationError`. Audits
    `wellness_enroll`. `list_wellness_enrollments(program_id,
    actor, offering_id=None)` in creation order.
  - `program_summary(program_id, period, actor)` (action `read`) →
    `{program_id, period, participants, earned_cents,
    accessed_cents, disbursed_cents, pending_cents, bookings,
    wellness_enrollments}`. `period` must be valid. `participants`
    is the count of participants in the program. `earned_cents` is
    the sum of accrual `earned_cents` for the period;
    `accessed_cents` the sum of access-request amounts in the
    period with status `approved` or `disbursed`;
    `disbursed_cents` the sum of disbursement amounts dated in the
    period; `pending_cents` the sum of access-request amounts in
    the period with status `requested`. `bookings` is
    `{"air": {"count": n, "total_cents": t}, "hotel": {...}}` over
    non-cancelled bookings whose `start_date` falls in the period
    (both kinds always present). `wellness_enrollments` is the
    total enrollment count in the program.
- `finance/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match
  the registry; unknown user or mismatched role → 401). Errors are
  JSON `{error}` with 400/401/403/404 as applicable; denied attempts
  (401 and 403) are audited with the action name suffixed `:denied`,
  and no stack trace is ever returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /programs` (read) → `{"programs": [...]}`;
    `POST /programs` `{name}` (create_program) → 201 program dict
  - `GET /programs/{id}` (read)
  - `POST /programs/{id}/members` `{username}` (any authenticated
    user; the store enforces owner-or-admin) → program dict
  - `GET /programs/{id}/participants?kind=` (read) →
    `{"participants": [...]}`; `POST /programs/{id}/participants`
    `{ref, kind}` (enter) → 201
  - `GET /programs/{id}/participants/{pid}` (read);
    `POST /programs/{id}/participants/{pid}/status` `{status}`
    (enter) → updated participant
  - `GET /programs/{id}/accruals?participant_id=` (read) →
    `{"accruals": [...]}`; `POST /programs/{id}/accruals`
    `{participant_id, period, earned_cents}` (enter) → 201 accrual
    record
  - `GET /programs/{id}/accruals/{aid}` (read) → accrual view
  - `GET /programs/{id}/access-requests?status=` (read) →
    `{"access_requests": [...]}`; `POST
    /programs/{id}/access-requests` `{participant_id, period,
    amount_cents, date}` (enter) → 201
  - `GET /programs/{id}/access-requests/{rid}` (read)
  - `POST /programs/{id}/access-requests/{rid}/approve` (decide);
    `POST /programs/{id}/access-requests/{rid}/deny` (decide);
    `POST /programs/{id}/access-requests/{rid}/void` (enter) →
    updated request
  - `POST /programs/{id}/access-requests/{rid}/disbursements`
    `{date, method?}` (record) → 201 disbursement dict
  - `GET /programs/{id}/disbursements?request_id=` (read) →
    `{"disbursements": [...]}`
  - `GET /programs/{id}/bookings?status=&kind=` (read) →
    `{"bookings": [...]}`; `POST /programs/{id}/bookings`
    `{participant_id, kind, start_date, end_date, amount_cents}`
    (enter) → 201
  - `GET /programs/{id}/bookings/{bid}` (read);
    `POST /programs/{id}/bookings/{bid}/confirm` (record);
    `POST /programs/{id}/bookings/{bid}/cancel` (enter) → updated
    booking
  - `PUT /programs/{id}/budgets/{period}` `{lines}` (enter) →
    budget dict; `GET /programs/{id}/budgets/{period}` (read);
    `GET /programs/{id}/budgets/{period}/vs-actual` (read)
  - `GET /programs/{id}/wellness-offerings` (read) →
    `{"offerings": [...]}`; `POST /programs/{id}/wellness-offerings`
    `{title, kind}` (enter) → 201
  - `GET /programs/{id}/wellness-offerings/{oid}` (read)
  - `GET /programs/{id}/wellness-enrollments?offering_id=` (read)
    → `{"enrollments": [...]}`; `POST
    /programs/{id}/wellness-offerings/{oid}/enrollments`
    `{participant_id}` (enter) → 201
  - `GET /programs/{id}/reports/summary?period=` (read; a missing
    `period` → 400)
- `finance/__main__.py` — `python -m finance serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim it traces to, and include a
**negative control**: a mutant cap check (one that sums the
committed and requested amounts but never compares the total against
the period's earned amount, treating every request as within cap)
whose behavior the canonical expectation is shown to reject — a
request that would push a period's committed total even one cent
over its earned amount must raise `ValidationError` from the real
store and store nothing, and the mutant is demonstrated to wave it
through — proving the suite catches that defect class rather than
merely passing. The negative control must additionally be
**mutation-verified**: patching the real cap check
(`_check_access_cap` in `src/finance/store.py`) with the mutant must
make the suite fail; the run and its result are recorded in
`tests/README.md`.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (8 claims total; the siblings share zero
  claimed families).
- Core: 11 core functions implemented, each with tracing tests.
- Extended: 4 functions specified and ranked, **not** implemented in
  this build (instant disbursement execution / payment rails,
  travel booking execution engines, financial wellness delivery
  tools, streaming reporting pipelines); SaaS delivery is a platform
  note (the build is a single-tenant reference deployment runnable
  over TLS when a certificate is configured; multi-tenancy and
  encryption at rest are deployment-layer properties, stated
  plainly, not claimed here). Six further functions are named in
  this spec as claimed by **neither** sibling and excluded from the
  union (banking integration & account verification, payroll
  integration & wage calculation, lending & credit, trading &
  investment execution, tax reporting & remittance, GRC platform
  functions).
