# Union Spec — Talent Management, CMMC L2 (DeadRamp Phase 2, remainder new sibling group)

The merged functional spec for the **Talent Management L2 sibling
group**: **2 forks**, category **Talent Management** (a category
the remainder census proposed from these forks' own descriptions;
no group exists at any other tier), CMMC tier **L2** (both
members are FedRAMP **Moderate** in `forks.json` — verified).
Membership is exactly the census unit's two fork IDs, reconciled
two ways with **zero diffs**: `remainder.json`'s unit
`new-group:Talent Management|L2` lists exactly `FR1831429369`
and `FR2113557839`, and both sit at Moderate / Certified / SaaS
in `forks.json` with source category "Uncategorized (none in
source)" — the census classified them from their descriptions
("Recruitment / hiring"; "Talent acquisition/recruiting"), never
from a registry field. The untiered Talent Management set and
the untiered Talent Development set later in the census are
different units and are **not** imported here.

| Fork | Vendor | Product | Status |
|---|---|---|---|
| FR1831429369 | HireVue | Recruitment Assessments and Video Interviewing | FedRAMP Certified |
| FR2113557839 | Yello Dba Recsolu Inc | Yello Government Recruiting Solution | FedRAMP Certified |

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

**The category boundary, stated once.** Human Resources L2
(Group 21) is the *personnel system of record*: positions,
vacancies, applications, personnel actions, and lifecycle cases
for the employed workforce — including its own talent-acquisition
family, which is the federal hiring chain (classification →
announcement → assessment → panel → certificate → onboarding)
inside an HR suite, and a talent-management family that group's
own spec dispositions Extended (retention and workforce
development depth). This pair is the other side of the hire:
**candidate-facing acquisition products** — video interviews and
recruitment assessments (HireVue), recruitment events, talent
pipelines, and applicant analytics (Yello) — whose descriptions
contain no personnel, position, onboarding, or workforce
vocabulary at all. A candidate in this build is an opaque
reference inside an acquisition pipeline; the moment a hire
becomes a personnel action it belongs to Human Resources'
substrate, not this one. No HR fork is imported, and no HR
function (position classification, personnel actions, onboarding)
is built here. Post-hire talent *development* is disposed
Extended below (its records territory is adjacent to Learning
Management's), not built.

## How functions were counted (a new category: the Group 1 method)

Talent Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from the two forks'
own descriptions**: families are named from the descriptions' own
functional vocabulary, each with verbatim match patterns, matched
against the descriptions' sentences and numbered clauses by
`scratch/extract.py`. A function is claimed **only** when a unit
of text contains matching text; the first matching unit is stored
as the claim's evidence in the spec sheet. Marketing and outcome
prose gets no tags. **14 claims in total** (HireVue 6, Yello 8)
across a **12-family** taxonomy. Counts are a **floor**, not a
ceiling.

Wording-artifact corrections (full log in `scratch/extract.py`):

- **Yello's whole functional surface is one sentence with three
  numbered clauses.** Each clause ("1) … events, 2) … pipelines,
  and 3) … analytics …") is matched as its own unit — marker
  stripped, clause text verbatim — the same treatment the
  Contract group's bullet lists received. The sentence's lead-in
  ("Yello's technology allows federal government customers")
  tags nothing.
- **HireVue's I-O sentence is a fragment as published.** "By
  combining video interviews with predictive, validated I-O
  science and artificial intelligence." has no main verb; it is
  matched as published and is the `io_science_ai` evidence.
- **Outcome and scale prose tags nothing.** HireVue's "gain a
  competitive advantage", "more than 700 customers", and
  "powering millions of annual interviews in over 180 countries"
  claim no function. Its platform sentence tags only via its
  functional verb list ("discover, hire, and develop talent"),
  not via "transforming the way".
- **Purpose prose tags nothing.** Yello's "so agencies can speed
  up the hiring process and determine return on investment" is
  the analytics clause's stated purpose. No return-on-investment
  figure is a records function: the core reports counts, and ROI
  determination lives in the analytics gap.
- **"Diverse" is an adjective, not a function.** Yello's
  pipelines are "robust and diverse"; no diversity measurement,
  reporting, or analytics function is described, claimed, or
  built (see checked absences).
- **"Virtual" is an event kind, not a video claim.** Yello's
  events are "in-person and virtual"; Yello never says "video",
  so `video_interviewing` is HireVue's claim alone, and the
  virtual *venue* is the event-platform gap.
- **Neither description says "SaaS".** Both call the product
  "software" ("talent acquisition software", "video interviewing
  software"), so `saas_delivery` is claimed at software weight as
  a platform note — the inverse of the Contract group's
  FedConnect case, where the registry said SaaS, the description
  didn't, and no claim was made. Claims come from descriptions.

## Function ranking — the group (2 forks)

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Recruiting & hiring process | 2 | **Core** context — the requisition → pipeline → placement records below are the process held as records; process engines Extended |
| 2 | Software delivery (platform) | 2 | Platform note — the build is a single-tenant reference deployment |
| 3 | Talent acquisition | 1 | **Core** context — candidate, pipeline, and event records are its records surface; acquisition engines (sourcing, matching) are not claimed by either description (see absences) |
| 4 | Video interviewing | 1 | **Core slice** — interview records of kind `video`. The video media platform (capture, streaming, recording): Extended |
| 5 | Recruitment assessments | 1 | **Core slice** — assessment records with caller-supplied outcome labels. Instrument delivery and any scoring: Extended |
| 6 | Predictive assessment science & AI (I-O science) | 1 | Extended — the predictive models and validation science themselves; the core records instrument labels and outcome labels and computes nothing |
| 7 | Talent development | 1 | Extended — development programs sit past the hire; no development record is presupposed by the acquisition claims |
| 8 | Recruitment events (in-person & virtual) | 1 | **Core** — event records + registration records. The event platform (virtual venue, invitations): Extended |
| 9 | Talent acquisition pipelines | 1 | **Core** — pipeline definitions, placements, and stage-movement records |
| 10 | Pipeline automation | 1 | **Core slice** — workflow definition registry, records only, never executes. The automation engine: Extended |
| 11 | Applicant metrics & analytics | 1 | **Core slice** — registry reporting computed on read (counts, including the current-stage distribution). Analytics engines: Extended |
| 12 | Data analytics visualization | 1 | Extended — dashboard / visualization engines; the core reports counts, it renders nothing |

## Checked absences (verified against both descriptions; never guessed into the build)

- **No applicant tracking.** No "applicant tracking" — indeed
  no "tracking" — token appears in either description. (Human
  Resources' FedHire claims applicant tracking; these two
  descriptions do not, and no ATS function is imported from
  there. Pipelines here are Yello's own claimed shape:
  definitions, placements, movements.)
- **No candidate sourcing, job boards, or postings.** No
  "sourcing", "job board", or "posting" token appears.
  HireVue's "discover" is its verb for what the platform does
  for organizations, not a sourcing engine claim.
- **No scheduling function.** No "schedul" token appears: no
  calendar coordination is claimed or built. (An interview
  record's optional `scheduled_at` and an event's `starts_at`
  are record metadata the claimed records presuppose, not a
  scheduling engine.)
- **No onboarding or post-hire lifecycle.** No "onboard" token
  appears. Onboarding is Human Resources' Core 6, a stated
  boundary, not a gap in this group.
- **No offers or hire decisions.** No "offer" token appears.
  Pipeline stage labels are the caller's own vocabulary; no
  stage in this build is a decision, and nothing records one.
- **No screening or resume parsing.** No "screen" or
  "resume"/"résumé" token appears. Assessments are claimed;
  resume screening is not.
- **No background checks.** No "background check" token
  appears.
- **No candidate communications or CRM.** No "email",
  "message", "campaign", "relationship", or "CRM" token
  appears — so this core deliberately carries **no**
  communication records (a deliberate contrast with the
  Contract core, whose forks claimed a communication channel),
  and messaging is not even a gap: it is not described.
- **No integrations.** No "integrat" token appears — so this
  core carries no integration registry either. The omission is
  a decision driven by the descriptions, stated here so it is
  not mistaken for an oversight.
- **No scoring, ranking, or matching.** No "score", "scoring",
  or "rank" token appears, and no record shape carries any of
  them. Assessment outcomes are caller-supplied labels recorded
  verbatim.
- **No diversity analytics.** "Diverse" appears once, as an
  adjective on Yello's pipelines. No diversity measurement or
  reporting function is described or built.

## Privacy discipline (hard rule, enforced by tests)

Carried from the sibling records substrates, tightened for a
substrate whose records are about job candidates:

- **Candidates are opaque references, not people.** Every
  candidate is a caller-supplied `candidate_ref` plus a label.
  There is no field anywhere that can hold a real person's
  name, contact detail, or identifier, a resume, or a
  demographic attribute.
- **Assessments store labels, never content.** An assessment
  record carries an opaque instrument label and, on completion,
  the caller's outcome label verbatim. No assessment item,
  response, or content exists anywhere in the store, and no
  score field exists: outcomes are recorded, never computed.
- **Interviews store metadata, never media.** An interview
  record carries a kind (`video` / `in_person`), a candidate
  reference, and an optional time. There is no recording,
  transcript, or notes field, and no parameter that could
  accept one.
- **Events store metadata.** Kind, time, title, registrations —
  no attendee lists beyond opaque candidate references.
- **Nothing is scored, ranked, or matched.** No record shape
  carries a score, rating, ranking, or match. Reporting is
  counts of recorded quantities only.

**Derived-never-stored status:** a requisition's `past_close`
(its close time against the read clock) and a placement's
`current_stage_index` / `current_stage` (the stage of its most
recent movement record, or the pipeline's first stage when no
movement exists) are computed by the read views. The stored
records carry none of those keys — pinned by tests. (Lifecycles
themselves — requisition `open` → `closed`, placement `active`
→ `withdrawn`, event `scheduled` → `completed` / `cancelled`,
registration `registered` → `checked_in`, assessment `assigned`
→ `completed`, interview `scheduled` → `completed` /
`cancelled` — are guarded transitions, not date derivations,
so those statuses are stored.)

**The signature invariant — the stage bounds seam, enforced in
the store.** A stage movement's `stage_index` must name a stage
of the placement's pipeline: **0 ≤ stage_index <
len(stages)**. The seam is `_check_stage_bounds` in the store:
it runs before every movement is recorded; a violation raises
`ValidationError`, consumes no id, and changes nothing.
Movements against withdrawn placements are rejected separately.
This is the group's negative control (see the implementation
contract).

## The Core — what the merged build implements (13 functions)

The records substrate the claimed functions jointly presuppose:

1. **Organization registry & membership** — organizations
   (`org-`): an opaque `org_ref`, a label, and a member list.
   Membership is the boundary every organization-scoped
   function enforces; only the organization's creator or a
   platform admin may add members. (Both forks serve agencies;
   the registry is the hiring organization's own boundary.)
2. **Candidate registry** — candidates (`can-`) in an
   organization: an opaque `candidate_ref` and a label. The
   candidate pool the pipelines, events, assessments, and
   interviews all reference. Registration records are not
   identity proofing.
3. **Requisition records** — requisitions (`req-`) in an
   organization: opaque `requisition_ref`, a title, optional
   open/close times, and a guarded lifecycle (`open` →
   `closed`). Read views derive `past_close`; the stored
   record carries no such key.
4. **Pipeline definitions** — pipelines (`pip-`) against one
   requisition: opaque `pipeline_ref`, an ordered list of
   stage labels (non-empty, unique within the pipeline), an
   optional label. A definition is a record; nothing about it
   executes or moves anyone.
5. **Candidate placements & stage movements** — placements
   (`plc-`) of a registered candidate into a pipeline (one
   active placement per candidate per pipeline), with a
   guarded lifecycle (`active` → `withdrawn`), and movements
   (`mov-`): append-only records of a stage index against a
   placement, each checked by the stage bounds seam before it
   is stored. Read views derive the placement's current stage
   from its movement set; the stored placement carries no
   stage field.
6. **Recruitment event records** — events (`evt-`) in an
   organization: opaque `event_ref`, a title, a kind from the
   description's own vocabulary (`in_person` / `virtual`), a
   required `starts_at`, an optional requisition link, and a
   guarded lifecycle (`scheduled` → `completed` /
   `cancelled`).
7. **Event registration records** — registrations (`reg-`)
   of a registered candidate for a scheduled event (one
   registration per candidate per event), with a guarded
   check-in transition (`registered` → `checked_in`).
8. **Assessment records** — assessments (`asm-`) against a
   registered candidate, optionally linked to a requisition:
   an opaque instrument label, a guarded lifecycle
   (`assigned` → `completed`), and on completion the caller's
   outcome label, recorded verbatim. No content, no score.
9. **Interview records** — interviews (`int-`) against a
   registered candidate, optionally linked to a requisition:
   a kind from the descriptions' vocabulary (`video` /
   `in_person`), an optional scheduled time, and a guarded
   lifecycle (`scheduled` → `completed` / `cancelled`).
   Metadata only.
10. **Workflow definition registry** — workflows (`wfl-`) in
    an organization: opaque `workflow_ref` and a label — the
    records surface of Yello's pipeline-automation claim.
    Records only: the registry has no execute operation,
    pinned by test.
11. **Registry reporting** — an organization report computed
    on read: candidate, requisition (by status), pipeline,
    and placement counts; the current-stage distribution of
    active placements (derived from movement records); event
    counts by kind and status; registration and check-in
    counts; assessment counts by status; interview counts by
    kind and status; workflow count. Counts only — no scores,
    no ratios, no ROI figure.
12. **Registry search** — literal case-insensitive substring
    search over registry metadata (references, titles, labels,
    kinds, stage labels), scoped to organizations the actor
    belongs to (or all for a platform admin).
13. **Access control & audit** — platform roles `admin`,
    `member`, `viewer` with a permission matrix enforced on
    every operation, layered with organization membership;
    and an append-only audit log recording every mutation and
    every denied attempt with actor, action, target, and UTC
    timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate**
  baseline (the FedRAMP Moderate tailoring), cross-walked to
  the 110 practices of NIST SP 800-171 Rev. 2 that define CMMC
  L2. Both member forks sit at Moderate, so the union baseline
  is the Moderate baseline, un-diluted (Merge Rule 1) and
  inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + organization membership) →
    **AC** (AC-2 account management, AC-3 access enforcement,
    AC-6 least privilege), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding
    organization via user/role headers; the build ships hooks,
    not an identity provider. Candidate registration records
    are registration, not identity proofing, exactly as IA-2
    sits here — a point that matters doubly in a substrate
    whose records concern people who are not yet employees).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of
    audit records, AU-6 audit review — append-only store,
    audit-read restricted to the `audit_read` permission, held
    by admin only). At L2 the audit mapping holds on **both**
    sides of the crosswalk, because 800-171 carries an audit
    family (3.3). Neither fork's description claims audit
    support by name; the trail is the Moderate baseline's
    answer for a records substrate holding candidate data, not
    a fork claim.
  - Registries, lifecycle guards, the stage bounds seam,
    reference-uniqueness discipline → **SI** (SI-10
    information input validation — malformed input, including
    any duplicate reference, out-of-bounds stage movement,
    movement against a withdrawn placement, or registration
    against a non-scheduled event, is rejected whole, never
    partially applied) and **SC** (SC-8 transmission
    confidentiality — the server runs over TLS when a
    certificate is configured; encryption at rest is a
    deployment-layer control, stated plainly, not claimed
    here. Neither fork's description claims FIPS-validated
    modules for its platform, and this build claims none —
    Python's standard library is not a FIPS-validated
    cryptographic module).
- **Caveat, same as the crosswalk's:** this mapping states
  which baseline families the build's features answer to. It is
  not a FedRAMP authorization and not a CMMC certification, and
  it does not claim either. FedRAMP authorizes products; CMMC
  certifies organizations; the tier is a planning/matching
  equivalence, never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `talentmgmt` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`org-`, `can-`,
`req-`, `pip-`, `plc-`, `mov-`, `evt-`, `reg-`, `asm-`, `int-`,
`wfl-`); a failed operation consumes no id and changes nothing.
All timestamps are UTC ISO-8601. Validation always precedes
mutation.

- `talentmgmt/errors.py` — `TalentMgmtError`,
  `ValidationError`, `NotFoundError`, `PermissionDenied` (all
  deriving from `TalentMgmtError`).
- `talentmgmt/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `org_read, org_write,
  candidate_write, requisition_write, pipeline_write,
  event_write, assessment_write, interview_write,
  registry_write, report_read, audit_read`. `PERMISSIONS`:
  admin ⊇ all eleven; member = all except `org_write` and
  `audit_read`; viewer = {org_read, report_read}.
  `permissions_for(role)`, `can(user, action)`,
  `require(user, action)` raising `PermissionDenied`.
- `talentmgmt/audit.py` — `AuditLog(path=None)`;
  `.record(actor, action, target, details=None)`; `.entries()`
  returns entry dicts with keys `ts, actor, action, target,
  details`. Append-only; optional JSONL file persistence;
  reloads an existing file on construction.
- `talentmgmt/store.py` — `TalentMgmtStore(audit=None)`. The
  store records every successful mutation to its audit log
  (when one is attached); the HTTP layer records denials and
  `audit_read` only. Two boundaries on every
  organization-scoped operation: the actor must be an
  organization member or hold the platform `admin` role, else
  `PermissionDenied`; and the operation's role permission is
  required (enforced when the actor is a `User`; a plain-string
  actor carries identity but no role, so role enforcement for
  those happens in the service layer — the house convention).
  Constants: `REQUISITION_STATUSES = ("open", "closed")`,
  `PLACEMENT_STATUSES = ("active", "withdrawn")`,
  `EVENT_KINDS = ("in_person", "virtual")`, `EVENT_STATUSES =
  ("scheduled", "completed", "cancelled")`,
  `REGISTRATION_STATUSES = ("registered", "checked_in")`,
  `ASSESSMENT_STATUSES = ("assigned", "completed")`,
  `INTERVIEW_KINDS = ("video", "in_person")`,
  `INTERVIEW_STATUSES = ("scheduled", "completed",
  "cancelled")`. Methods:
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
  - `register_candidate(org_id, candidate_ref, label, actor)`
    (action `candidate_write`) → `{id, org_id, candidate_ref,
    label, created_by, created_utc}`; `candidate_ref` non-empty
    and unique within the organization. Audits
    `candidate_register`. `get_candidate(org_id, candidate_id,
    actor)`; `list_candidates(org_id, actor)`.
  - `create_requisition(org_id, requisition_ref, title, actor,
    opens_at=None, closes_at=None)` (action
    `requisition_write`) → stored `{id, org_id,
    requisition_ref, title, opens_at, closes_at, status,
    created_by, created_utc}`; status starts `open`; times when
    given must parse as ISO dates/datetimes and `closes_at`
    must not precede `opens_at`; `requisition_ref` non-empty
    and unique within the organization. Audits
    `requisition_create`. `get_requisition(org_id,
    requisition_id, actor, now=None)` → the stored fields
    **plus derived** `past_close` (bool: `closes_at` is set and
    the read clock is past it). **The stored record never
    carries it** — `list_requisitions(org_id, actor, now=None)`
    returns the same derived views. `close_requisition(org_id,
    requisition_id, actor)` (action `requisition_write`):
    `open` → `closed`; wrong state → `ValidationError`. Audits
    `requisition_close`.
  - `create_pipeline(org_id, pipeline_ref, requisition_id,
    stages, actor, label=None)` (action `pipeline_write`) →
    `{id, org_id, pipeline_ref, requisition_id, stages, label,
    created_by, created_utc}`; the requisition must exist in
    this organization; `stages` a non-empty list of non-empty
    strings, unique within the pipeline; `pipeline_ref`
    non-empty and unique within the organization. Audits
    `pipeline_create`. `get_pipeline(org_id, pipeline_id,
    actor)`; `list_pipelines(org_id, actor, requisition_id=None)`.
  - `_check_stage_bounds(pipeline, stage_index)` — the seam.
    Raises `ValidationError` when `stage_index` is not an
    integer (booleans included) or when it falls outside
    `0 <= stage_index < len(pipeline["stages"])`.
  - `place_candidate(org_id, pipeline_id, placement_ref,
    candidate_ref, actor)` (action `pipeline_write`) → stored
    `{id, org_id, pipeline_id, placement_ref, candidate_ref,
    status, created_by, created_utc}`; status starts `active`;
    the pipeline must exist in this organization; the candidate
    must be registered in this organization (else
    `ValidationError`); `placement_ref` non-empty and unique
    within the pipeline; a candidate with an active placement
    in the same pipeline cannot be placed again
    (`ValidationError`). Audits `placement_create`.
    `get_placement(org_id, placement_id, actor)` → stored
    fields **plus derived** `current_stage_index` (the most
    recent movement's stage index, or 0) and `current_stage`
    (that stage's label); **the stored record never carries
    either key** — `list_placements(org_id, actor,
    pipeline_id=None)` returns the same views.
    `withdraw_placement(org_id, placement_id, actor)` (action
    `pipeline_write`): `active` → `withdrawn`. Audits
    `placement_withdraw`.
  - `record_movement(org_id, placement_id, movement_ref,
    stage_index, actor, label=None)` (action `pipeline_write`)
    → `{id, org_id, placement_id, movement_ref, stage_index,
    label, created_by, created_utc}`; the placement must exist
    in this organization and be `active` (withdrawn →
    `ValidationError`); `movement_ref` non-empty and unique
    within the placement. **Bounds seam:**
    `_check_stage_bounds(pipeline, stage_index)` runs before
    anything is stored. Audits `movement_record`.
    `list_movements(org_id, placement_id, actor)`.
  - `create_event(org_id, event_ref, title, kind, starts_at,
    actor, requisition_id=None, label=None)` (action
    `event_write`) → `{id, org_id, event_ref, title, kind,
    starts_at, requisition_id, label, status, created_by,
    created_utc}`; status starts `scheduled`; `kind` one of
    `EVENT_KINDS`; `starts_at` required and must parse; a
    requisition link when given must exist in this
    organization; `event_ref` non-empty and unique within the
    organization. Audits `event_create`. `get_event(org_id,
    event_id, actor)`; `list_events(org_id, actor, kind=None,
    requisition_id=None)`. `complete_event(org_id, event_id,
    actor)` / `cancel_event(org_id, event_id, actor)` (action
    `event_write`): `scheduled` → `completed` / `cancelled`;
    wrong state → `ValidationError`. Audits `event_complete` /
    `event_cancel`.
  - `register_for_event(org_id, event_id, registration_ref,
    candidate_ref, actor)` (action `event_write`) → `{id,
    org_id, event_id, registration_ref, candidate_ref, status,
    created_by, created_utc}`; status starts `registered`;
    guards: the event must exist in this organization and be
    `scheduled` (else `ValidationError`); the candidate must
    be registered in this organization (else
    `ValidationError`); `registration_ref` non-empty and
    unique within the event; a candidate registers for an
    event at most once (`ValidationError`). Audits
    `registration_create`. `check_in_registration(org_id,
    registration_id, actor)` (action `event_write`):
    `registered` → `checked_in`. Audits
    `registration_check_in`. `list_registrations(org_id,
    event_id, actor)`.
  - `record_assessment(org_id, assessment_ref, candidate_ref,
    instrument_label, actor, requisition_id=None)` (action
    `assessment_write`) → `{id, org_id, assessment_ref,
    candidate_ref, instrument_label, requisition_id, status,
    outcome_label, created_by, created_utc}`; status starts
    `assigned`; `outcome_label` starts None; the candidate
    must be registered in this organization; a requisition
    link when given must exist in this organization;
    `assessment_ref` non-empty and unique within the
    organization. Audits `assessment_record`.
    `complete_assessment(org_id, assessment_id, outcome_label,
    actor)` (action `assessment_write`): `assigned` →
    `completed`, setting the caller's outcome label (required,
    non-empty, recorded verbatim). Audits
    `assessment_complete`. `get_assessment(org_id,
    assessment_id, actor)`; `list_assessments(org_id, actor,
    candidate_ref=None, status=None)`.
  - `schedule_interview(org_id, interview_ref, candidate_ref,
    kind, actor, requisition_id=None, scheduled_at=None)`
    (action `interview_write`) → `{id, org_id, interview_ref,
    candidate_ref, kind, requisition_id, scheduled_at, status,
    created_by, created_utc}`; status starts `scheduled`;
    `kind` one of `INTERVIEW_KINDS`; the candidate must be
    registered in this organization; a requisition link and a
    scheduled time when given must exist / parse;
    `interview_ref` non-empty and unique within the
    organization. Audits `interview_schedule`.
    `complete_interview(org_id, interview_id, actor)` /
    `cancel_interview(org_id, interview_id, actor)` (action
    `interview_write`): `scheduled` → `completed` /
    `cancelled`. Audits `interview_complete` /
    `interview_cancel`. `get_interview(org_id, interview_id,
    actor)`; `list_interviews(org_id, actor, candidate_ref=None,
    kind=None)`.
  - `register_workflow(org_id, workflow_ref, label, actor)`
    (action `registry_write`) → `{id, org_id, workflow_ref,
    label, created_by, created_utc}`; `workflow_ref` non-empty
    and unique within the organization. **The registry records
    workflow definitions only; there is no execute
    operation.** Audits `workflow_register`.
    `list_workflows(org_id, actor)`.
  - `org_report(org_id, actor, now=None)` (action
    `report_read`) → `{org_id, candidate_count,
    requisition_count, requisitions_by_status, pipeline_count,
    placement_count, placements_by_stage, event_count,
    events_by_kind, events_by_status, registration_count,
    checked_in_count, assessment_count,
    assessments_by_status, interview_count, interviews_by_kind,
    interviews_by_status, workflow_count}` — counts computed
    on read from the records; `placements_by_stage` is the
    derived current-stage distribution over **active**
    placements only, keyed by stage label.
  - `search_registry(actor, query)` (action `org_read`) →
    `{organizations, candidates, requisitions, pipelines,
    events, workflows}`: literal case-insensitive substring
    match over `*_ref` fields, titles, labels, kinds, and
    pipeline stage labels, restricted to organizations the
    actor is a member of (or all for a platform admin);
    requisitions and pipelines are returned as derived views /
    stage-list copies. Empty query → `ValidationError`.
- `talentmgmt/service.py` — `make_server(host, port, store,
  audit, users)` → `http.server.ThreadingHTTPServer`; `users`
  maps name → role. Auth via `X-User` / `X-Role` headers (the
  role must match the registry; unknown user or mismatched
  role → 401). Errors are JSON `{error}` with 400/401/403/404
  as applicable; denied attempts (401 and 403) are audited
  with the action name suffixed `:denied`, and no stack trace
  is ever returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /organizations` (org_read) → `{"organizations":
    [...]}`; `POST /organizations` `{org_ref, label}`
    (org_write) → 201 organization dict
  - `GET /organizations/{id}` (org_read)
  - `POST /organizations/{id}/members` `{username}` →
    organization dict (the store enforces creator-or-admin)
  - `GET /organizations/{id}/candidates` (org_read) →
    `{"candidates": [...]}`; `POST` `{candidate_ref, label}`
    (candidate_write) → 201
  - `GET /organizations/{id}/requisitions` (org_read) →
    `{"requisitions": [...]}` (derived views); `POST`
    `{requisition_ref, title, opens_at?, closes_at?}`
    (requisition_write) → 201 stored shape
  - `POST /organizations/{id}/requisitions/{rid}/close`
    (requisition_write) → requisition dict
  - `GET /organizations/{id}/pipelines?requisition_id=`
    (org_read) → `{"pipelines": [...]}`; `POST`
    `{pipeline_ref, requisition_id, stages, label?}`
    (pipeline_write) → 201
  - `POST /organizations/{id}/pipelines/{pid}/placements`
    `{placement_ref, candidate_ref}` (pipeline_write) → 201
    stored shape
  - `GET /organizations/{id}/placements?pipeline_id=`
    (org_read) → `{"placements": [...]}` (derived views)
  - `GET /organizations/{id}/placements/{plid}/movements`
    (org_read) → `{"movements": [...]}`; `POST`
    `{movement_ref, stage_index, label?}` (pipeline_write) →
    201; an out-of-bounds stage index → 400
  - `POST /organizations/{id}/placements/{plid}/withdraw`
    (pipeline_write) → placement dict
  - `GET /organizations/{id}/events?kind=&requisition_id=`
    (org_read) → `{"events": [...]}`; `POST` `{event_ref,
    title, kind, starts_at, requisition_id?, label?}`
    (event_write) → 201
  - `POST /organizations/{id}/events/{eid}/complete` ·
    `/cancel` (event_write) → event dict
  - `GET /organizations/{id}/events/{eid}/registrations`
    (org_read) → `{"registrations": [...]}`; `POST`
    `{registration_ref, candidate_ref}` (event_write) → 201
  - `POST /organizations/{id}/registrations/{rid}/check-in`
    (event_write) → registration dict
  - `GET /organizations/{id}/assessments?candidate_ref=&status=`
    (org_read) → `{"assessments": [...]}`; `POST`
    `{assessment_ref, candidate_ref, instrument_label,
    requisition_id?}` (assessment_write) → 201
  - `POST /organizations/{id}/assessments/{aid}/complete`
    `{outcome_label}` (assessment_write) → assessment dict
  - `GET /organizations/{id}/interviews?candidate_ref=&kind=`
    (org_read) → `{"interviews": [...]}`; `POST`
    `{interview_ref, candidate_ref, kind, requisition_id?,
    scheduled_at?}` (interview_write) → 201
  - `POST /organizations/{id}/interviews/{iid}/complete` ·
    `/cancel` (interview_write) → interview dict
  - `GET /organizations/{id}/workflows` (org_read) →
    `{"workflows": [...]}`; `POST` `{workflow_ref, label}`
    (registry_write) → 201
  - `GET /organizations/{id}/report` (report_read) → report
    dict
  - `GET /search?q=` (org_read) → registry search dict
- `talentmgmt/__main__.py` — `python -m talentmgmt serve
  --host --port [--audit-log PATH] [--certfile --keyfile]`
  with demo users `alice=admin, bob=member, carol=viewer`
  (documented as demo identities; production identity is the
  embedding organization's, per IA-2 above). Default port
  8817.

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces
to, and include the **negative control**: a mutant store whose
`_check_stage_bounds` performs no check at all, so a movement to
a stage index beyond the pipeline's stage list (or below zero)
is accepted and the placement's derived current stage breaks.
The canonical expectation is shown to reject those movements —
the real store must raise `ValidationError` while the mutant
accepts — proving the suite catches the stage-bounds defect
class rather than merely passing. The negative control must
additionally be **mutation-verified**: patching the real seam
in `src/` with the mutant body must make the suite fail; the
run and its result are recorded in `tests/README.md`. A
spec-integrity test module pins the spec sheets themselves:
membership exactly the census unit's two fork IDs (read from
`../../../remainder.json`), each sheet's description byte-equal
to the cached `service_desc`, every claim's evidence a verbatim
substring of its sheet's description, and the literal per-fork
claim tables (6 and 8).

## Gaps — specified, not implemented (for the GAPS.md final batch)

- **Video interview platform** — live and on-demand video:
  capture, streaming, recording storage and playback, the
  interview room itself. The core records video-kind interview
  metadata; it carries no media.
- **Assessment delivery & scoring engines** — administering
  instruments to candidates, capturing responses, and any
  scoring computation over them. The core records assignments
  and caller-supplied outcome labels; it delivers nothing and
  computes nothing.
- **Predictive I-O models & AI** — the predictive, validated
  I-O science and artificial intelligence HireVue's description
  names: model development, validation, and inference over
  interviews and assessments.
- **Virtual event platform** — the virtual venue for virtual
  recruitment events, plus invitation and event-communications
  tooling around events. The core records events and
  registrations; it hosts nothing and sends nothing.
- **Pipeline automation engine** — executing the automations
  Yello's description names (the workflow registry's
  definitions, run). The core registers workflow definitions;
  it executes nothing.
- **Analytics & visualization engines** — dashboards, real-time
  visualization, and return-on-investment determination over
  the registry's counts. The core reports recorded quantities
  only.
- **Talent development programs** — the "develop talent"
  surface past the hire (development planning, programs,
  progress). The core ends at the acquisition pipeline, by the
  boundary stated above.
- **Identity provider / candidate identity verification** —
  candidate registration records are not identity proofing;
  IA-2 stays with the embedding organization and this build
  ships hooks, not an IdP.

Platform-layer: encryption at rest is deployment-layer (TLS
when configured); multi-tenancy (single-tenant reference
deployment); demo identities are hooks, not an IdP. Boundary
note: personnel records, position classification, and
onboarding belong to the Human Resources L2 build — this group
holds candidate acquisition records only, by design and by the
descriptions' own wording.

## Coverage statement (for this build)

- Specs: 2 / 2 forks spec'd (14 claims total across a 12-family
  taxonomy defined from the forks' own descriptions, each claim
  with its source sentence as evidence).
- Core: 13 core functions implemented, each with tracing tests.
- Extended: 8 gaps specified above, **not** implemented in this
  build (the video interview platform, assessment delivery &
  scoring engines, predictive I-O models & AI, the virtual
  event platform, the pipeline automation engine, analytics &
  visualization engines, talent development programs, and the
  identity/verification service).
- Platform notes (claimed as a platform family, not built):
  software delivery.
