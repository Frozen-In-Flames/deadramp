# Union Spec — Contract Management, CMMC L2 (DeadRamp Phase 2, remainder new sibling group)

The merged functional spec for the **Contract Management L2 sibling
group**: **2 forks**, category **Contract Management** (a brand-new
category proposed by the remainder census and accepted by this
build — no group exists at any other tier), CMMC tier **L2** (both
members are FedRAMP **Moderate** in `forks.json` — verified).
Membership is exactly the census unit's two fork IDs, reconciled
two ways with **zero diffs**: `forks.json` carries exactly these
two Unison offerings at Moderate / Certified / SaaS, and
`remainder.json`'s unit `new-group:Contract Management|L2` lists
exactly `F1506046707` and `F1510017461`. Other contract-named
offerings exist elsewhere in the registry and are **not** members:
the census filed MSM Group's iSite Contract Management Portal
under Operations Management (procurement *operations*), and
Standard Technology's Contract Management Planning and
Surveillance System sits in an untiered set. Neither is imported
here.

| Fork | Vendor | Product | Status |
|---|---|---|---|
| F1506046707 | Unison | Contracting SaaS | FedRAMP Certified |
| F1510017461 | Unison | FedConnect | FedRAMP Certified |

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence. Source: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product records joined by FedRAMP ID. No live
fetching was needed: both descriptions were present in the cached
dataset, and the census's copies in `remainder/uncovered.json`
were verified byte-equal to the cache's `service_desc` fields by
the extractor before tagging.

**The category boundary, stated once.** Two census passes
independently placed procurement *operations* tooling (AI
sourcing, RFP tooling) in Operations Management. This pair is
different in kind: the **contract lifecycle system of record** for
federal acquisition — contract records and their modifications,
compliance requirements, protests, data calls, and the
opportunity-to-award portal records around them. Operations
Management L2 holds procurement operations; Legal & Policy holds
law and policy work; Grant Management L2 holds post-award grants
administration (this group's financial-assistance claims reach
only as far as *opportunities* — see the checked absences). This
group is contract lifecycle records, and its core is built to
exactly that boundary.

## How functions were counted (a new category: the Group 1 method)

Contract Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from the two forks' own
descriptions**: families are named from the descriptions' own
functional vocabulary, each with verbatim match patterns, matched
against the descriptions' sentences and bullet lines by
`scratch/extract.py`. A function is claimed **only** when a unit of
text contains matching text; the first matching unit is stored as
the claim's evidence in the spec sheet. Marketing and outcome
prose gets no tags. **25 claims in total** (Contracting SaaS 11,
FedConnect 14) across a **21-family** taxonomy. Counts are a
**floor**, not a ceiling.

Wording-artifact corrections (full log in `scratch/extract.py`):

- **Outcome prose tags nothing.** Contracting SaaS's "Eliminate
  process bottlenecks and compress PALT" and "boost compliance
  and productivity" are outcome claims, not functions; no family
  fires on them (the lifecycle claim in the second case rests on
  the same sentence's "throughout their contracting lifecycles").
  FedConnect's purpose sentence ("bridge the gap … streamline
  the process of doing business with government") and its closing
  "To learn more" sentence likewise tag nothing.
- **One fork's bullets carry its claims.** Contracting SaaS's
  functional surface is its two capability bullet lists; each
  bullet is matched as its own unit, and the bullet text (marker
  stripped, otherwise verbatim) is the evidence. FedConnect's
  claims rest on its prose sentences.
- **A second FAR/DFARS occurrence is not a second claim.**
  Contracting SaaS's risk bullet also names FAR/DFARS; the
  `regulatory_compliance` claim's evidence is the first matching
  unit ("Fully comply with FAR/DFARS and agency supplements"),
  one claim per family per fork.
- **"Payment upon award" is a vendor fee, not a disbursement.**
  FedConnect's sentence makes the *winning vendor company*
  responsible for payment upon award; the `subscription_billing`
  claim therefore covers subscription and award-fee records owed
  *to* the portal operator, never government payments to vendors.
  No invoicing or disbursement function is claimed anywhere (see
  checked absences).
- **FedConnect never says "SaaS."** Its description contains no
  SaaS token, so it makes no `saas_delivery` claim — even though
  `forks.json` records its service model as SaaS. Claims come
  from descriptions, not registry fields.

## Function ranking — the group (2 forks)

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Contract lifecycle management | 2 | **Core** — contract records + modification records; the lifecycle system of record |
| 2 | Regulatory compliance (FAR/DFARS & contracting mandates) | 2 | **Core slice** — compliance requirement records. The regulation corpus and its interpretation: Extended |
| 3 | Audit support & auditability | 2 | **Core** — append-only audit log over every record, with admin-gated audit visibility |
| 4 | Vendor community interaction | 2 | **Core slice** — communication records (metadata only). The community platform / messaging transport: Extended |
| 5 | Opportunity portal (find & review opportunities) | 1 | **Core slice** — opportunity records + registry listing/search. The public web portal front-end: Extended |
| 6 | Opportunity issuance (eRFX) | 1 | **Core** — opportunity records (issuance is creating the record) |
| 7 | Award issuance & receipt | 1 | **Core** — award records against submissions |
| 8 | Bid & proposal submission | 1 | **Core slice** — submission records with open/deadline/directed guards. The electronic intake transport: Extended |
| 9 | Reverse auction events | 1 | **Core slice** — opportunity records of kind `reverse_auction`. The auction engine (live bidding, price discovery): Extended |
| 10 | Financial assistance / grants opportunities | 1 | **Core slice** — opportunity records of kind `financial_assistance`. Post-award grants administration is the Grant Management category's build, not this group's |
| 11 | Subscription & award-fee billing | 1 | **Core slice** — fee & payment records in integer cents. Payment processing rails: Extended |
| 12 | System-to-system integration | 1 | **Core slice** — integration registry records. The interface transports themselves: Extended |
| 13 | Vendor / applicant registration | 1 | **Core slice** — participant registry records. Identity proofing / verification: Extended (IA-2 stays with the embedding organization) |
| 14 | Secure communication channel | 1 | **Core slice** — communication records (metadata only, no content). The secure messaging transport: Extended |
| 15 | Protest response | 1 | **Core slice** — protest records with response deadlines. Adjudication sits with agencies / GAO and is never performed here |
| 16 | Analysis & reporting | 1 | **Core slice** — registry reporting computed on read (counts and sums). An analytics engine: Extended |
| 17 | Standardized workflow | 1 | **Core slice** — workflow definition registry, records only, never executes. The workflow engine: Extended |
| 18 | Data-call response | 1 | **Core** — data-call records with due dates and derived overdue status |
| 19 | Contracting risk visibility | 1 | **Core slice** — risk records + reporting visibility. The claim is visibility; nothing is assessed or scored |
| 20 | Commercial goods & services acquisition | 1 | **Core** via contract records — acquiring commercial goods and services is what the contract records record; no separate entity is presupposed |
| 21 | SaaS delivery (platform) | 1 | Platform note — the build is a single-tenant reference deployment |

## Checked absences (verified against both descriptions; never guessed into the build)

- **No contract authoring.** No "draft", "clause", or "template"
  token appears in either description: no clause library, no
  document drafting, no template management is claimed.
  ("Standardized workflow" is process standardization, not
  document templates.)
- **No electronic signature.** No "signature" / "sign" token
  appears in either description.
- **No source selection, evaluation, or scoring.** No "evaluate",
  "evaluation", "scoring", or "source selection" token appears:
  submissions are recorded, never evaluated, ranked, or scored,
  and no record shape carries a score.
- **No performance surveillance or ratings.** No "surveillance",
  "CPARS", or "performance rating" token appears. (A different
  vendor's product elsewhere in the census is named for contract
  surveillance; it is not one of these forks and its function is
  not imported.)
- **No government disbursement or invoicing.** No "invoice"
  token appears; the only payment either description names is
  the winning vendor's award-fee obligation and agency
  subscription fees (see the wording-artifact note above).
- **No protest adjudication.** Only "respond to protests" is
  claimed — response-support records. Decisions sit with
  agencies and GAO.
- **No AI / ML vocabulary.** Neither description contains
  "artificial intelligence", "machine learning", or a standalone
  "AI" token. The vendor's AI-filed sibling product (Bidscale)
  is a different fork in a different unit and is not imported.
- **No API claim.** Integration is claimed in the description's
  own words as a "system-to-system interface"; no "API" token
  appears, and no API surface is claimed for the forks. (This
  build's own HTTP service is the records substrate's interface,
  not a fork claim.)
- **No post-award grants administration.** FedConnect
  facilitates Financial Assistance *opportunities*; grant
  lifecycle administration is the Grant Management L2 category
  (Singleton 45), a stated boundary, not a gap in this group.
- **No PALT measurement.** "Compress PALT" is outcome prose (see
  above); no lead-time measurement function is claimed.

## Privacy discipline (hard rule, enforced by tests)

Carried from the sibling records substrates, because this group's
records describe live federal acquisitions:

- **Records hold metadata and opaque references, not substance.**
  Contracts, opportunities, submissions, awards, and cases are
  keyed by opaque caller-supplied `*_ref` strings plus caller
  labels. Counterparties, participants, and requesters are opaque
  references; there is no field anywhere that can hold a real
  person's name, contact detail, or identifier, a bid's contents,
  or a contract's text.
- **Communications are metadata only.** A communication record
  carries a counterparty reference, a direction, and a label —
  the store has no parameter that can accept message content.
- **Money is integer cents.** Ceilings, award amounts,
  modification amounts, and payments are Python `int` cents;
  booleans, floats, and strings are rejected at the boundary.
- **Nothing is scored.** No record shape carries a score, rating,
  ranking, or evaluation. Reporting is counts and sums of
  recorded quantities only.

**Derived-never-stored status:** a contract's `obligated_cents`
(the base award amount plus its recorded modifications) and
`period_elapsed` (its period end against the read clock), a
protest's and a data call's `overdue` (open, with the read clock
past its due date), an opportunity's `past_close` (its close time
against the read clock), and a submission's `awarded` (whether an
award record exists for it) are all computed by the read views.
The stored records carry none of those keys — pinned by tests.
(Lifecycles themselves — contract `active` → `closed`,
requirement `open` → `satisfied` / `waived`, case
`open` → `closed`, opportunity `open` → `closed` — are guarded
transitions, not date derivations, so those statuses are stored.)

**The signature invariant — the modification bounds seam,
enforced in the store.** A contract's obligated amount — base
award plus the sum of its recorded modifications — must always
satisfy **0 ≤ obligated ≤ ceiling**. The seam is
`_check_modification_bounds` in the store: it runs before a
contract is created (with its base award as the amount under
test) and before every modification is recorded; a violation
raises `ValidationError`, consumes no id, and changes nothing.
Modifications against closed contracts are rejected separately.
This is the group's negative control (see the implementation
contract).

## The Core — what the merged build implements (18 functions)

The records substrate the claimed functions jointly presuppose:

1. **Organization registry & membership** — organizations
   (`org-`): an opaque `org_ref`, a label, and a member list.
   Membership is the boundary every organization-scoped function
   enforces; only the organization's creator or a platform admin
   may add members. (Both forks serve agencies and contractor
   companies alike; the registry is neutral between them.)
2. **Participant registry** — participants (`par-`) at platform
   level: an opaque `participant_ref` and a label — the
   registration records FedConnect's directed opportunities and
   submissions presuppose. Registration records are not identity
   proofing.
3. **Contract records** — contracts (`con-`) in an organization:
   opaque `contract_ref` (unique within the organization), a
   title, an opaque `counterparty_ref`, `ceiling_cents` and base
   `award_cents` (integer cents), optional period start/end, and
   a guarded lifecycle (`active` → `closed`). Read views derive
   `obligated_cents` and `period_elapsed`; the stored record
   carries neither.
4. **Contract modification records** — modifications (`mod-`)
   against a contract: opaque `mod_ref` (unique within the
   contract), a signed `amount_cents`, an optional label. The
   bounds seam runs before each is stored; modifications against
   closed contracts are rejected.
5. **Compliance requirement records** — requirements (`req-`) in
   an organization: opaque `requirement_ref`, a label, and a
   guarded lifecycle (`open` → `satisfied`, `open` → `waived`).
6. **Protest records** — protests (`pro-`) against exactly one of
   a contract or an opportunity in the same organization: opaque
   `protest_ref`, a label, a required `due_at`, a guarded
   lifecycle (`open` → `closed`), and a derived `overdue` flag
   on read views.
7. **Data-call records** — data calls (`dcl-`) in an
   organization: opaque `datacall_ref`, an opaque `requester_ref`
   (the federal customers, auditors, and executives of the fork's
   prose are references, never identities), a label, a required
   `due_at`, a guarded lifecycle, and a derived `overdue` flag.
8. **Risk records** — risks (`rsk-`) in an organization,
   optionally against a contract: opaque `risk_ref`, a label, a
   guarded lifecycle (`open` → `closed`). Visibility records
   only; no assessment, no score.
9. **Communication records** — communications (`com-`) in an
   organization: opaque `comm_ref`, an opaque `counterparty_ref`,
   a direction (`inbound` / `outbound`), and a label. No content
   field exists.
10. **Opportunity records** — opportunities (`opp-`) issued by an
    organization: opaque `opportunity_ref`, a title, a kind from
    the fork's own vocabulary (`erfx`, `reverse_auction`,
    `financial_assistance`), an audience (`public` / `directed`;
    directed requires a non-empty list of registered participant
    references), an optional `closes_at`, and a guarded lifecycle
    (`open` → `closed`). Read views derive `past_close`.
11. **Submission records** — submissions (`sub-`) against an
    opportunity: opaque `submission_ref` and the submitting
    participant's opaque reference. Guards: the opportunity must
    be open and not past its close time; the participant must be
    registered; for a directed opportunity the participant must
    be among its directed-to references. Read views derive
    `awarded`.
12. **Award records** — awards (`awd-`) against an opportunity
    and one of its submissions: opaque `award_ref`,
    `amount_cents` (integer cents ≥ 0). A submission is awarded
    at most once — recording an award consumes it.
13. **Fee & payment records** — payments (`pay-`) in an
    organization: opaque `payment_ref`, a kind (`subscription` /
    `award_fee`), `amount_cents` (a positive integer), and
    optional opportunity / award links that must exist in the
    organization.
14. **Workflow definition registry** — workflows (`wfl-`) in an
    organization: opaque `workflow_ref` and a label. Records
    only: the registry has no execute operation, pinned by test.
15. **Integration registry** — integrations (`int-`) in an
    organization: opaque `integration_ref`, an opaque
    `system_ref` naming the other system, and a label. Records
    of interfaces, never transports.
16. **Registry reporting** — an organization report computed on
    read: contract counts by status, obligated and ceiling sums,
    modification count, requirement counts by status, open and
    overdue case counts, opportunity counts by kind and status,
    submission and award counts, award and payment sums by kind,
    and registry counts. Counts and sums only — no scores.
17. **Registry search** — literal case-insensitive substring
    search over registry metadata (references, titles, labels,
    kinds), scoped to organizations the actor belongs to (or all
    for a platform admin), plus the platform participant
    registry.
18. **Access control & audit** — platform roles `admin`,
    `member`, `viewer` with a permission matrix enforced on
    every operation, layered with organization membership; and
    an append-only audit log recording every mutation and every
    denied attempt with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to the
  110 practices of NIST SP 800-171 Rev. 2 that define CMMC L2.
  Both member forks sit at Moderate, so the union baseline is
  the Moderate baseline, un-diluted (Merge Rule 1) and inherited
  in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + organization membership) →
    **AC** (AC-2 account management, AC-3 access enforcement,
    AC-6 least privilege), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the build ships hooks,
    not an identity provider. Participant registration records
    are registration, not identity proofing, exactly as IA-2
    sits here).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of
    audit records, AU-6 audit review — append-only store,
    audit-read restricted to the `audit_read` permission, held
    by admin only). At L2 the audit mapping holds on **both**
    sides of the crosswalk, because 800-171 carries an audit
    family (3.3). This is also the substrate of the forks'
    `audit_support` claim: the auditable approach both
    descriptions name is answered by an append-only trail over
    every record in the build.
  - Registries, lifecycle guards, the modification bounds seam,
    integer-cent discipline → **SI** (SI-10 information input
    validation — malformed input, including any non-integer
    money value, duplicate reference, out-of-bounds
    modification, or late/directed-guard submission, is rejected
    whole, never partially applied) and **SC** (SC-8 transmission
    confidentiality — the server runs over TLS when a
    certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed here.
    Neither fork's description claims FIPS-validated modules for
    its platform, and this build claims none — Python's standard
    library is not a FIPS-validated cryptographic module).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `contractmgmt` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`, `par-`,
`con-`, `mod-`, `req-`, `pro-`, `dcl-`, `rsk-`, `com-`, `opp-`,
`sub-`, `awd-`, `pay-`, `wfl-`, `int-`); a failed operation
consumes no id and changes nothing. All timestamps are UTC
ISO-8601. Validation always precedes mutation.

- `contractmgmt/errors.py` — `ContractMgmtError`,
  `ValidationError`, `NotFoundError`, `PermissionDenied` (all
  deriving from `ContractMgmtError`).
- `contractmgmt/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `org_read, org_write,
  contract_write, compliance_write, case_write, comm_write,
  portal_write, payment_write, registry_write, report_read,
  audit_read`. `PERMISSIONS`: admin ⊇ all eleven; member = all
  except `org_write` and `audit_read`; viewer = {org_read,
  report_read}. `permissions_for(role)`, `can(user, action)`,
  `require(user, action)` raising `PermissionDenied`.
- `contractmgmt/audit.py` — `AuditLog(path=None)`;
  `.record(actor, action, target, details=None)`; `.entries()`
  returns entry dicts with keys `ts, actor, action, target,
  details`. Append-only; optional JSONL file persistence;
  reloads an existing file on construction.
- `contractmgmt/store.py` — `ContractMgmtStore(audit=None)`. The
  store records every successful mutation to its audit log (when
  one is attached); the HTTP layer records denials and
  `audit_read` only. Two boundaries on every organization-scoped
  operation: the actor must be an organization member or hold
  the platform `admin` role, else `PermissionDenied`; and the
  operation's role permission is required (enforced when the
  actor is a `User`; a plain-string actor carries identity but
  no role, so role enforcement for those happens in the service
  layer — the house convention). The participant registry is not
  organization-scoped: writes require `registry_write`; reads
  are open to any actor. Constants: `OPPORTUNITY_KINDS =
  ("erfx", "reverse_auction", "financial_assistance")`,
  `AUDIENCES = ("public", "directed")`, `PAYMENT_KINDS =
  ("subscription", "award_fee")`, `DIRECTIONS = ("inbound",
  "outbound")`, `CONTRACT_STATUSES = ("active", "closed")`,
  `REQUIREMENT_STATUSES = ("open", "satisfied", "waived")`,
  `CASE_STATUSES = ("open", "closed")`, `OPPORTUNITY_STATUSES =
  ("open", "closed")`. Methods:
  - `create_organization(org_ref, label, actor)` (action
    `org_write`) → `{id, org_ref, label, members, created_by,
    created_utc}`; `org_ref` a non-empty string, unique across
    organizations (duplicate → `ValidationError`); the creator
    is the first member. Audits `organization_create`.
    `list_organizations(actor)` → organizations the actor is a
    member of, or all for a platform admin, in creation order.
    `get_organization(org_id, actor)` (`NotFoundError`;
    `PermissionDenied` for a non-member non-admin).
  - `add_member(org_id, username, actor)` → updated
    organization dict. Only the organization's creator or a
    platform admin may add; adding an existing member raises
    `ValidationError`. Audits `member_add`.
  - `register_participant(participant_ref, label, actor)`
    (action `registry_write`) → `{id, participant_ref, label,
    created_by, created_utc}`; `participant_ref` non-empty and
    unique across the registry. Audits `participant_register`.
    `list_participants(actor)`; `get_participant(participant_id,
    actor)` — reads open to any actor.
  - `create_contract(org_id, contract_ref, title,
    counterparty_ref, ceiling_cents, award_cents, actor,
    period_start=None, period_end=None)` (action
    `contract_write`) → stored `{id, org_id, contract_ref,
    title, counterparty_ref, ceiling_cents, award_cents,
    period_start, period_end, status, created_by, created_utc}`;
    status starts `active`; money values are ints ≥ 0 (booleans,
    floats, strings rejected); period values when given must
    parse as ISO dates/datetimes and `period_end` must not
    precede `period_start`; `contract_ref` non-empty and unique
    within the organization. **Bounds seam:** before the record
    is stored, `_check_modification_bounds(contract,
    [], award_cents)` runs against the would-be contract, so a
    base award above the ceiling is rejected at creation.
    Audits `contract_create`. `get_contract(org_id, contract_id,
    actor, now=None)` → the stored fields **plus derived**
    `obligated_cents` (base award + the sum of its modifications)
    and `period_elapsed` (bool: `period_end` is set and the read
    clock is past it). **The stored record never carries either
    key** — `list_contracts(org_id, actor, now=None)` returns the
    same derived views. `close_contract(org_id, contract_id,
    actor)` (action `contract_write`): `active` → `closed`;
    wrong state → `ValidationError`. Audits `contract_close`.
  - `_check_modification_bounds(contract, existing_amounts,
    additional_cents)` — the seam. Computes `obligated =
    sum(existing_amounts) + additional_cents` and raises
    `ValidationError` when `obligated < 0` or `obligated >
    contract["ceiling_cents"]`. Callers pass the amounts already
    obligated as `existing_amounts`: at contract creation that is
    `[]` with the base award as `additional_cents`; at
    modification time it is `[contract["award_cents"]] + [the
    amounts of the contract's existing modifications]` with the
    new modification's amount as `additional_cents`.
  - `record_modification(org_id, contract_id, mod_ref,
    amount_cents, actor, label=None)` (action `contract_write`)
    → `{id, org_id, contract_id, mod_ref, amount_cents, label,
    created_by, created_utc}`; the contract must exist in this
    organization and be `active` (closed → `ValidationError`);
    `amount_cents` an int of any sign (booleans, floats, strings
    rejected); `mod_ref` non-empty and unique within the
    contract. **Bounds seam:** `_check_modification_bounds(
    contract, [contract["award_cents"]] + [amounts of existing
    modifications], amount_cents)` runs before anything is
    stored. Audits `modification_record`. `list_modifications(
    org_id, contract_id, actor)`.
  - `create_requirement(org_id, requirement_ref, label, actor)`
    (action `compliance_write`) → `{id, org_id, requirement_ref,
    label, status, created_by, created_utc}`; status starts
    `open`; `requirement_ref` non-empty and unique within the
    organization. Audits `requirement_create`.
    `satisfy_requirement(org_id, requirement_id, actor)` /
    `waive_requirement(org_id, requirement_id, actor)` (action
    `compliance_write`): `open` → `satisfied` / `waived`; wrong
    state → `ValidationError`. Audits `requirement_satisfy` /
    `requirement_waive`. `list_requirements(org_id, actor,
    status=None)`; `get_requirement(org_id, requirement_id,
    actor)`.
  - `create_protest(org_id, protest_ref, label, due_at, actor,
    contract_id=None, opportunity_id=None)` (action
    `case_write`) → `{id, org_id, protest_ref, contract_id,
    opportunity_id, label, due_at, status, created_by,
    created_utc}`; status starts `open`; **exactly one** of
    `contract_id` / `opportunity_id` must be given (both or
    neither → `ValidationError`) and the linked record must
    exist in this organization; `due_at` is required and must
    parse as an ISO date/datetime; `protest_ref` non-empty and
    unique within the organization. Audits `protest_create`.
    `get_protest(org_id, protest_id, actor, now=None)` → stored
    fields **plus derived** `overdue` (bool: status is `open`
    and the read clock is past `due_at`); the stored record
    never carries it. `list_protests(org_id, actor, now=None)`
    returns the same views. `close_protest(org_id, protest_id,
    actor)` (action `case_write`): `open` → `closed`. Audits
    `protest_close`.
  - `create_datacall(org_id, datacall_ref, requester_ref, label,
    due_at, actor)` (action `case_write`) → `{id, org_id,
    datacall_ref, requester_ref, label, due_at, status,
    created_by, created_utc}`; same due-date, lifecycle, and
    derived-`overdue` discipline as protests; `datacall_ref`
    unique within the organization. Audits `datacall_create`.
    `close_datacall(...)`, `get_datacall(...)`,
    `list_datacalls(...)` mirror the protest methods.
  - `create_risk(org_id, risk_ref, label, actor,
    contract_id=None)` (action `case_write`) → `{id, org_id,
    risk_ref, contract_id, label, status, created_by,
    created_utc}`; status starts `open`; `contract_id` when
    given must name a contract in this organization; `risk_ref`
    unique within the organization. Audits `risk_create`.
    `close_risk(org_id, risk_id, actor)`: `open` → `closed`.
    Audits `risk_close`. `list_risks(org_id, actor,
    contract_id=None)`; `get_risk(org_id, risk_id, actor)`.
  - `record_communication(org_id, comm_ref, counterparty_ref,
    direction, label, actor)` (action `comm_write`) → `{id,
    org_id, comm_ref, counterparty_ref, direction, label,
    created_by, created_utc}`. **There is no parameter for
    message content.** `direction` one of `DIRECTIONS`;
    `comm_ref` non-empty and unique within the organization.
    Audits `communication_record`. `list_communications(org_id,
    actor, direction=None)`.
  - `create_opportunity(org_id, opportunity_ref, title, kind,
    actor, audience="public", directed_to=None, closes_at=None)`
    (action `portal_write`) → stored `{id, org_id,
    opportunity_ref, title, kind, audience, directed_to,
    closes_at, status, created_by, created_utc}`; status starts
    `open`; `kind` one of `OPPORTUNITY_KINDS`; `audience` one of
    `AUDIENCES`; for `directed`, `directed_to` must be a
    non-empty list of participant references that all exist in
    the participant registry (unknown → `ValidationError`); for
    `public`, `directed_to` must be None or empty and is stored
    as `[]`; `closes_at` when given must parse; `opportunity_ref`
    non-empty and unique within the organization. Audits
    `opportunity_create`. `get_opportunity(org_id,
    opportunity_id, actor, now=None)` → stored fields **plus
    derived** `past_close` (bool: `closes_at` is set and the
    read clock is past it); the stored record never carries it.
    `list_opportunities(org_id, actor, kind=None, now=None)`
    returns the same views. `close_opportunity(org_id,
    opportunity_id, actor)` (action `portal_write`): `open` →
    `closed`. Audits `opportunity_close`.
  - `record_submission(org_id, opportunity_id, submission_ref,
    participant_ref, actor)` (action `portal_write`) → `{id,
    org_id, opportunity_id, submission_ref, participant_ref,
    created_by, created_utc}`. Guards, in order: the opportunity
    must exist in this organization; its status must be `open`
    (else `ValidationError`); when `closes_at` is set, the
    current time must not be past it (else `ValidationError`);
    `participant_ref` must name a registered participant (else
    `ValidationError`); for a `directed` opportunity the
    participant must be in its `directed_to` list (else
    `PermissionDenied`); `submission_ref` non-empty and unique
    within the opportunity. Audits `submission_record`.
    `get_submission(org_id, submission_id, actor)` → stored
    fields **plus derived** `awarded` (bool: an award exists for
    this submission); the stored record never carries it.
    `list_submissions(org_id, opportunity_id, actor)` returns
    the same views.
  - `record_award(org_id, opportunity_id, submission_id,
    award_ref, amount_cents, actor)` (action `portal_write`) →
    `{id, org_id, opportunity_id, submission_id, award_ref,
    amount_cents, created_by, created_utc}`; the opportunity and
    the submission must exist, the submission within this
    opportunity; `amount_cents` an int ≥ 0 (booleans, floats,
    strings rejected); `award_ref` non-empty and unique within
    the opportunity; **a submission is awarded at most once** —
    a second award against the same submission raises
    `ValidationError`. Audits `award_record`.
    `list_awards(org_id, opportunity_id, actor)`.
  - `record_payment(org_id, payment_ref, kind, amount_cents,
    actor, opportunity_id=None, award_id=None)` (action
    `payment_write`) → `{id, org_id, payment_ref, kind,
    amount_cents, opportunity_id, award_id, created_by,
    created_utc}`; `kind` one of `PAYMENT_KINDS`; `amount_cents`
    an int > 0 (booleans, floats, strings rejected);
    `payment_ref` non-empty and unique within the organization;
    linked ids when given must exist in this organization, and
    an award link must belong to the given opportunity when both
    are given. Audits `payment_record`. `list_payments(org_id,
    actor, kind=None)`.
  - `register_workflow(org_id, workflow_ref, label, actor)`
    (action `registry_write`) → `{id, org_id, workflow_ref,
    label, created_by, created_utc}`; `workflow_ref` non-empty
    and unique within the organization. **The registry records
    workflow definitions only; there is no execute operation.**
    Audits `workflow_register`. `list_workflows(org_id, actor)`.
  - `register_integration(org_id, integration_ref, system_ref,
    label, actor)` (action `registry_write`) → `{id, org_id,
    integration_ref, system_ref, label, created_by,
    created_utc}`; `integration_ref` non-empty and unique within
    the organization. Audits `integration_register`.
    `list_integrations(org_id, actor)`.
  - `org_report(org_id, actor, now=None)` (action
    `report_read`) → `{org_id, contract_count,
    contracts_by_status, obligated_cents_total,
    ceiling_cents_total, modification_count, requirement_count,
    requirements_by_status, protest_count, open_protests,
    datacall_count, open_datacalls, overdue_datacalls,
    risk_count, open_risks, communication_count,
    opportunity_count, opportunities_by_kind,
    opportunities_by_status, submission_count, award_count,
    award_cents_total, payment_count, payment_cents_total,
    payments_by_kind, workflow_count, integration_count}` —
    counts and cent sums computed on read from the records;
    `overdue_datacalls` is the derived count (open data calls
    past their due date at the read clock).
  - `search_registry(actor, query)` (action `org_read`) →
    `{organizations, participants, contracts, opportunities,
    workflows, integrations}`: literal case-insensitive
    substring match over `*_ref` fields, titles, labels, and
    kinds, restricted to organizations the actor is a member of
    (or all for a platform admin); participants are
    platform-wide; contracts and opportunities are returned as
    derived views. Empty query → `ValidationError`.
- `contractmgmt/service.py` — `make_server(host, port, store,
  audit, users)` → `http.server.ThreadingHTTPServer`; `users`
  maps name → role. Auth via `X-User` / `X-Role` headers (the
  role must match the registry; unknown user or mismatched role
  → 401). Errors are JSON `{error}` with 400/401/403/404 as
  applicable; denied attempts (401 and 403) are audited with the
  action name suffixed `:denied`, and no stack trace is ever
  returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /organizations` (org_read) → `{"organizations":
    [...]}`; `POST /organizations` `{org_ref, label}`
    (org_write) → 201 organization dict
  - `GET /organizations/{id}` (org_read)
  - `POST /organizations/{id}/members` `{username}` →
    organization dict (the store enforces creator-or-admin)
  - `GET /participants` → `{"participants": [...]}`; `POST
    /participants` `{participant_ref, label}` (registry_write)
    → 201
  - `GET /organizations/{id}/contracts` (org_read) →
    `{"contracts": [...]}` (derived views); `POST
    /organizations/{id}/contracts` `{contract_ref, title,
    counterparty_ref, ceiling_cents, award_cents, period_start?,
    period_end?}` (contract_write) → 201 stored-shape contract
  - `POST /organizations/{id}/contracts/{cid}/close`
    (contract_write) → contract dict
  - `GET /organizations/{id}/contracts/{cid}/modifications`
    (org_read) → `{"modifications": [...]}`; `POST` `{mod_ref,
    amount_cents, label?}` (contract_write) → 201; an
    out-of-bounds modification → 400
  - `GET /organizations/{id}/requirements?status=` (org_read)
    → `{"requirements": [...]}`; `POST` `{requirement_ref,
    label}` (compliance_write) → 201
  - `POST /organizations/{id}/requirements/{rid}/satisfy` ·
    `/waive` (compliance_write) → requirement dict
  - `GET /organizations/{id}/protests` (org_read) →
    `{"protests": [...]}` (derived views); `POST`
    `{protest_ref, label, due_at, contract_id? | opportunity_id?}`
    (case_write) → 201 stored shape
  - `POST /organizations/{id}/protests/{pid}/close`
    (case_write) → protest dict
  - `GET /organizations/{id}/datacalls` (org_read) →
    `{"datacalls": [...]}` (derived views); `POST`
    `{datacall_ref, requester_ref, label, due_at}` (case_write)
    → 201 stored shape
  - `POST /organizations/{id}/datacalls/{did}/close`
    (case_write) → data-call dict
  - `GET /organizations/{id}/risks?contract_id=` (org_read) →
    `{"risks": [...]}`; `POST` `{risk_ref, label, contract_id?}`
    (case_write) → 201
  - `POST /organizations/{id}/risks/{rid}/close` (case_write)
    → risk dict
  - `GET /organizations/{id}/communications?direction=`
    (org_read) → `{"communications": [...]}`; `POST`
    `{comm_ref, counterparty_ref, direction, label}`
    (comm_write) → 201
  - `GET /organizations/{id}/opportunities?kind=` (org_read)
    → `{"opportunities": [...]}` (derived views); `POST`
    `{opportunity_ref, title, kind, audience?, directed_to?,
    closes_at?}` (portal_write) → 201 stored shape
  - `POST /organizations/{id}/opportunities/{oid}/close`
    (portal_write) → opportunity dict
  - `GET /organizations/{id}/opportunities/{oid}/submissions`
    (org_read) → `{"submissions": [...]}` (derived views);
    `POST` `{submission_ref, participant_ref}` (portal_write)
    → 201 stored shape
  - `GET /organizations/{id}/opportunities/{oid}/awards`
    (org_read) → `{"awards": [...]}`; `POST` `{submission_id,
    award_ref, amount_cents}` (portal_write) → 201
  - `GET /organizations/{id}/payments?kind=` (org_read) →
    `{"payments": [...]}`; `POST` `{payment_ref, kind,
    amount_cents, opportunity_id?, award_id?}` (payment_write)
    → 201
  - `GET /organizations/{id}/workflows` (org_read) →
    `{"workflows": [...]}`; `POST` `{workflow_ref, label}`
    (registry_write) → 201
  - `GET /organizations/{id}/integrations` (org_read) →
    `{"integrations": [...]}`; `POST` `{integration_ref,
    system_ref, label}` (registry_write) → 201
  - `GET /organizations/{id}/report` (report_read) → report
    dict
  - `GET /search?q=` (org_read) → registry search dict
- `contractmgmt/__main__.py` — `python -m contractmgmt serve
  --host --port [--audit-log PATH] [--certfile --keyfile]` with
  demo users `alice=admin, bob=member, carol=viewer`
  (documented as demo identities; production identity is the
  embedding organization's, per IA-2 above). Default port 8813.

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to, and include the **negative control**: a mutant store whose
`_check_modification_bounds` performs no check at all, so an
over-ceiling contract award and an over-ceiling (or
below-zero) modification are accepted. The canonical expectation
is shown to reject them — the real store must raise
`ValidationError` while the mutant accepts — proving the suite
catches the modification-bounds defect class rather than merely
passing. The negative control must additionally be
**mutation-verified**: patching the real seam in `src/` with the
mutant body must make the suite fail; the run and its result are
recorded in `tests/README.md`. A spec-integrity test module pins
the spec sheets themselves: membership exactly the census unit's
two fork IDs (read from `../../../remainder.json`), each sheet's
description byte-equal to the cached `service_desc`, every
claim's evidence a verbatim substring of its sheet's description,
and the literal per-fork claim tables (11 and 14).

## Gaps — specified, not implemented (for the GAPS.md final batch)

- **Regulatory content & interpretation** — the FAR/DFARS corpus,
  agency supplements, and their continuous updates and
  interpretation. The core records compliance requirements and
  their disposition; it holds no regulation text.
- **Workflow execution engine** — running the standardized
  workflows the registry defines. The core registers workflow
  definitions; it executes nothing.
- **Analytics engine** — analysis beyond the registry reporting
  counts and sums (PALT measurement, bottleneck analysis,
  spend analysis). The core reports recorded quantities only.
- **Opportunity portal front-end** — the public and directed web
  portal itself (publication, browsing, the browser experience
  FedConnect's description describes). The core holds
  opportunity records and registry search.
- **Reverse auction engine** — live auction events: bidding,
  price discovery, event execution. The core records
  reverse-auction opportunities and their awards; it runs no
  auction.
- **Submission intake transport** — the electronic channel that
  receives bids and proposals (document upload, receipt,
  virus/format handling). The core records submissions and
  enforces their guards; it transports nothing.
- **Payment processing rails** — collecting subscription and
  award fees (payment instruments, settlement, refunds). The
  core records payments in integer cents; it moves no money.
- **Integration transport** — the system-to-system interfaces
  themselves (the Contracting/Grants application interface
  FedConnect's description names, and any other). The core
  registers interface records; it connects to nothing.
- **Communication transport** — the secure messaging channel
  itself between agencies and their vendor communities. The
  core records communication metadata; it sends nothing.
- **Identity provider / registration verification service** —
  participant registration records are not identity proofing;
  IA-2 stays with the embedding organization and this build
  ships hooks, not an IdP.

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (single-tenant reference deployment);
demo identities are hooks, not an IdP. Boundary note: post-award
grants administration belongs to the Grant Management L2 build —
this group records financial-assistance opportunities only, by
design and by the descriptions' own wording.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (25 claims total across a 21-family
  taxonomy defined from the forks' own descriptions, each claim
  with its source sentence as evidence).
- Core: 18 core functions implemented, each with tracing tests.
- Extended: 10 gaps specified above, **not** implemented in this
  build (the regulatory corpus, the workflow engine, the
  analytics engine, the portal front-end, the reverse auction
  engine, the intake transport, the payment rails, the
  integration transport, the communication transport, and the
  identity/registration verification service).
- Platform notes (claimed as a platform family, not built):
  SaaS delivery.
