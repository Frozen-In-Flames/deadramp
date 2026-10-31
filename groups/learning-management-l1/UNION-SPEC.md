# Union Spec — Learning Management, CMMC L1 (DeadRamp Phase 2, remainder new sibling group)

The merged functional spec for the **Learning Management L1 sibling
group**: **2 forks**, category **Learning Management**, CMMC tier
**L1** (one member is FedRAMP **Low**, the other **LI-SaaS**, in
`forks.json` — verified; both map to CMMC L1 per `../../crosswalk.md`).
Membership is exactly the remainder census unit
`new-group:Learning Management|L1`'s two fork IDs, reconciled two
ways with **zero diffs**: `remainder.json`'s unit lists exactly
`FR2113157410` and `FR2135043135`, and the `forks.json` rows for
those IDs carry exactly these vendor/product pairs at L1 / Certified
/ SaaS. Both rows sit in the registry's "Uncategorized (none in
source)" bucket — their category comes from the census, from their
own descriptions, cited, never guessed. Two other Learning
Management offerings are **not** members: the L2 singleton
(PowerTrain, `F1405214357`) is a different tier with its own shipped
build, and the census's L2 addition unit (Skillsoft Percipio,
`FR2118043605`) extends that build, not this one; the untiered
Learning Management fork belongs to an untiered set. Neither is
imported here.

| Fork | Vendor | Product | Impact | Status |
|---|---|---|---|---|
| FR2113157410 | Public Health Foundation | TRAIN Learning Network | Low | FedRAMP Certified |
| FR2135043135 | SRR International,Inc. | CloudLCMS | LI-SaaS | FedRAMP Certified |

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 2
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence. Source: GSA
FedRAMP Marketplace dataset (cached at `../../raw/data_dump.json`,
produced by the General Services Administration, last change
2026-10-22), product records joined by FedRAMP ID.

## Relationship to the L2 sibling build (stated once)

Learning Management already has a shipped build at L2:
`groups/learning-management-l2/` (Group 48, the PowerTrain
singleton, FedRAMP Moderate). **This L1 group is its own build at
the Low baseline, in its own directory — not an addition to the L2
directory and not a re-tiering of it.** Same category, different
tier, separate build. What the two builds share is the category
substrate: under the Merge Rule's cross-tier discipline, the
substrate is carried whole across tiers and flagged *carried, not
claimed*, and the baseline is written fresh at each tier (the L2
build's Moderate baseline is not diluted downward; this build's Low
baseline is authored at Low, below).

## The taxonomy decision (stated once, explicitly)

The L2 sibling's taxonomy was defined **from its own fork's
description** (the Group 1 method for a brand-new category): 26
families, each with a verbatim match pattern in the L2 fork's own
phrasing. **This build applies that taxonomy verbatim — identical
families, identical patterns, not re-tuned** (the extractor parses
the L2 extractor's `TAXONOMY` literal with `ast` and asserts
triple-equality before tagging; see `scratch/extract.py`). A
function is claimed **only** when a sentence of an L1 fork's
description contains the pattern's text; the matching sentence is
stored as the claim's evidence. Marketing prose gets no tags.
Counts are a **floor**, not a ceiling.

The measured outcome is the honest one, and it is pinned by test,
not hidden:

- **TRAIN Learning Network claims 0 of the 26 families.** Its
  description asserts an LMS with multi-tenancy, per-organization
  branded portals, course posting, learner-activity tracking and
  reporting, continuing-education management, certificate awarding,
  and direct learner communication — in TRAIN's own verbs, none of
  which is the L2 fork's literal phrasing ("multi-tenant" where the
  pattern is "multiple tenants"; "track and report on learner
  activity" where the pattern is "tracking and analysis of learner
  activities"). Every near-miss is itemized in
  `scratch/ARTIFACTS.md`.
- **CloudLCMS claims 1 of the 26 families** —
  `content_standards_distribution`, on "SCORM 1.2". Its identity
  phrase "learning content management platform" does not match the
  pattern "management of eLearning content", and its headline
  function, rapid content authoring, has no L2 family at all.

## Functions the L1 descriptions assert that the L2 taxonomy does not name

Itemized per fork (full wording log in `scratch/ARTIFACTS.md`).
Each item carries its disposition in this build:

**TRAIN Learning Network:**
- **Per-organization branded portals & content access restriction**
  (each organization gets a branded portal; content restricted
  internally or shared across the whole community) — no L2 family.
  The records and enforcement form enters **Core** (function 15:
  organization registry; courses and content carry an owning
  organization and a visibility, enforced for learner-role catalog
  reads). Portal rendering/branding is **Extended**.
- **Course creation & posting; linking to external training** — the
  catalog records they presuppose are carried Core (functions 2);
  content items gain an optional external reference for linked
  external training. The authoring/posting engine is **Extended**.
- **Learner activity tracking & reporting** (in substance) — the
  records forms are carried Core (functions 7, 11). No new engine.
- **Continuing education management** — no L2 family. The records
  form enters **Core** (function 17: continuing-education records,
  credit text verbatim). Credit accounting and renewal-cycle
  management beyond records are **Extended**.
- **Certificate awarding** — no L2 family (at L2, certificates were
  a checked absence: the only certificate vocabulary sat inside
  the SF-182 form's name). The records form enters **Core**
  (function 16: certificate award records). Certificate rendering,
  delivery, and public verification are **Extended**.
- **Direct learner communication** — notification records are
  carried Core (function 10); the messaging transport is
  **Extended** (with the carried notification-transport gap).
- **System integrations** — **Extended** (integration engines).
- **Custom feature development** — a vendor professional service,
  not a product function; recorded here so it is not mistaken for
  a gap. No records form, no gap.
- **Multi-tenancy** (in substance) — platform note, exactly as at
  L2: deployment property; single-tenant reference deployment.

**CloudLCMS:**
- **Rapid content authoring** — no L2 family (at L2, authoring was
  a checked absence and the authoring gap had no claimant). The
  authoring environment is **Extended**, now with an L1 claimant.
- **Collaborative authoring environment** (developers working
  together or individually) — part of the authoring **Extended**
  gap.
- **Section 508 compliance of produced courses** — an accessibility
  property of the authoring output; rides the authoring gap. This
  build's records carry no accessibility claim.
- **Responsive course design (PC & mobile)** — a delivery property;
  rides the carried delivery-engine gap.
- **Custom themes & menus; plugins within courses** — a
  presentation/extension framework; rides the authoring gap.
- **Course export formats (SCORM 1.2, 2004, xAPI, HTML)** — the
  claimed family's substance. The standards survive as content-item
  metadata in Core; **HTML joins the content-standard enum** on
  this fork's evidence (the L2 list had no HTML). The
  packaging/export runtime is **Extended** (carried gap, now with
  an L1 claimant).

## Function ranking — the union (L2 taxonomy, verbatim)

Claim counts are across this group's 2 forks. Dispositions:
**Core** = implemented in this build; **carried** = the records
form is part of the category substrate carried down whole from the
L2 build (flagged carried, not claimed, per the cross-tier
discipline); **Extended** = specified, not implemented, registered
as a gap.

| # | Function (L2 family) | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Content standards & distribution (SCORM / AICC / cmi5) | 1 (CloudLCMS) | **Core slice** — standards recorded as content-item metadata (enum extended with HTML on CloudLCMS's evidence); packaging/export runtime Extended |
| 2 | Registration management for learning events | 0 | Carried Core — event & registration records, waitlist as recorded state |
| 3 | Mandatory training compliance | 0 | Carried Core — assignments with status **derived at read**, never stored (signature invariant) |
| 4 | Learning record store (xAPI LRS) | 0 | Carried Core slice — experience statement records; xAPI protocol runtime Extended |
| 5 | Learner activity tracking | 0 (asserted in substance by TRAIN) | Carried Core — progress & activity records |
| 6 | Training authorization & certification forms (SF-182) | 0 | Carried Core — authorization records with recorded decisions (decider ≠ creator) |
| 7 | Individual Development Plans (IDP) | 0 | Carried Core — development plan records |
| 8 | Competency management | 0 | Carried Core — competency definitions & learner competency records (levels verbatim) |
| 9 | Lesson plans | 0 | Carried Core slice — lesson plan records in the catalog; authoring Extended |
| 10 | eLearning content management | 0 (asserted in substance by both, in different words) | Carried Core — content registry records; delivery/runtime and authoring Extended |
| 11 | Adjustable workflow | 0 | Carried Core slice — workflow definitions registered as data, **never executed**; execution engine Extended |
| 12 | Automated notifications | 0 (direct communication asserted by TRAIN, automation not claimed) | Carried Core slice — notification records; delivery transport Extended |
| 13 | Wait list management | 0 | Carried Core — part of the registration records (capacity-derived seats) |
| 14 | Reporting & configurable reports | 0 (reporting asserted in substance by TRAIN) | Carried Core slice — registry summaries & search computed from records; report builder Extended |
| 15 | Learning delivery & management | 0 | Extended — the delivery engine itself |
| 16 | EHRI data collection & reporting | 0 | Extended — the EHRI integration & feed engine |
| 17 | Learning analytics & outcomes analysis | 0 | Extended — the analytics engine (Core reporting is counts over records) |
| 18 | Career mapping & recommended training | 0 | Extended — mapping/recommendation engine |
| 19 | Leadership succession planning | 0 | Extended — talent-domain suite |
| 20 | Candidate review (talent acquisition) | 0 | Extended — talent-domain suite |
| 21 | Employee surveys & data collection | 0 | Extended — survey engine |
| 22 | Knowledge base / wiki platform (adjacent product) | 0 | Extended — adjacent enclave product at L2 |
| 23 | Web content management platform (adjacent product) | 0 | Extended — adjacent enclave product at L2 |
| 24 | Identity & authentication — MFA / SSO (platform) | 0 | Platform note — the build ships RBAC hooks, not an IdP |
| 25 | Multi-tenancy (platform note) | 0 (asserted in substance by TRAIN) | Platform note — deployment property; single-tenant reference deployment |
| 26 | Cloud hosting platform (platform note) | 0 | Platform note — delivery prose; deployment layer |

Plus the three records forms this tier's own forks assert and the
taxonomy does not name, entering Core by the boundary decisions
below: **organization & portal registry** (TRAIN), **certificate
award records** (TRAIN), **continuing education records** (TRAIN).

**Named absences at this tier, stated plainly (checked, findings
not oversights):** neither L1 description contains scoring or
grading vocabulary about learners, assessment-administration
vocabulary, proctoring, discussion/social-learning, virtual
-classroom, or gamification vocabulary. None of these is a gap:
nothing was claimed, so nothing is owed. Where the build reaches
past the claims, it does so by the explicit core-boundary decisions
below, never by silence.

## Core-boundary decisions (recorded, per the cross-tier precedents)

1. **The carried substrate.** The L2 Core's records forms are
   carried down whole to L1 — all fourteen — flagged *carried, not
   claimed*: only `content_standards_distribution` is claim-anchored
   at this tier. The tier changes the baseline, not the records
   forms. This is the same treatment the shipped cross-tier builds
   applied upward (zero-claim forks at higher tiers carried the
   full substrate), run downward.
2. **Learner records** (carried from L2). Every learner-bound
   record presupposes a learner; learners enter as a registry of
   **opaque references** (a caller-supplied `ref` and a label, a
   shape pinned by test so no field can hold a real personal
   identifier). A learner may carry an optional organization
   reference (decision 6).
3. **Progress records** (carried from L2). Tracking and compliance
   jointly presuppose per-learner progress records; completion is
   the terminal progress state, and compliance derivation reads
   those records.
4. **Scores. None, anywhere.** No claim at either tier defines a
   score, so no record shape carries a score field and nothing
   computes one — pinned by test. A statement's `result_text` and a
   continuing-education record's `credit_text` are caller-supplied
   text recorded **verbatim**, never parsed, summed, or converted.
   Competency levels likewise are recorded verbatim in the caller's
   own scale.
5. **Authorization decisions** (carried from L2). An authorization
   record records its outcome, decided by a named decider who is
   never the record's creator (separation of duties, enforced in
   the store). The SF-182 form itself — rendering, routing,
   signature — is Extended.
6. **Organizations & visibility** (new at this tier, TRAIN's
   evidence). TRAIN's portal sentence presupposes organizations
   and a visibility rule for content. Organizations therefore enter
   as records (`org-`: opaque `ref`, label, portal label); courses
   and content items may carry an owning organization and a
   `visibility` of `organization` (restricted internally) or
   `community` (available across the whole community, TRAIN's own
   words). For learner-role catalog reads the rule is enforced: a
   learner sees community items plus their own organization's
   items. Branding and portal rendering are Extended; the record
   and the rule are Core.
7. **Certificates** (new at this tier, TRAIN's evidence). An award
   is an append-only fact: learner, course (optional), title,
   award date, note, and the recording actor. Nothing in TRAIN's
   text supports a revocation or reissue workflow, so none is
   built; rendering, delivery, and public verification are
   Extended.
8. **Lesson plans** (carried from L2). Catalog records (title,
   course, ordered references to catalog entries); the authoring
   tool is Extended.

## The Core — what the merged build implements (17 functions)

One coherent, standards-based learning records service, built
clean-room from this spec: functions 1–14 carried from the L2
substrate, 15–17 new at this tier on this tier's own evidence.

1. **Learner registry (opaque references)** — learners (`lrn-`)
   known only by a caller-supplied opaque `ref` (unique) and a
   label, with an optional organization reference. The record
   shape is pinned: no field can hold a real identifier.
2. **Course, content & lesson-plan catalog** — courses and
   programs (`crs-`); content items (`cnt-`) whose `standard`
   field takes exactly the union of the two tiers' own lists
   (SCORM 1.2, SCORM 2004, AICC, xAPI, cmi5, MP3, MP4, PDF, HTML,
   other — HTML added on CloudLCMS's evidence); lesson plans
   (`les-`) as catalog records referencing courses and content
   items. Content items may carry an external reference (linked
   external training, TRAIN). Courses and content may carry an
   owning organization and a visibility (decision 6).
3. **Events & registration management** — live/virtual learning
   events (`evt-`) with an optional capacity, and registrations
   (`reg-`) binding a learner to an event. A registration's state
   (`registered`/`waitlisted`/`cancelled`/`attended`) is a
   recorded fact; an event's `seats_taken`, `waitlist_count`, and
   `seats_open` are **derived at read** — never stored.
   Registering into a full event records `waitlisted`; promotion
   is an explicit recorded state change, never an automation.
4. **Training authorization (SF-182) records** — authorizations
   (`aut-`) by a learner against a course or event, recorded from
   `requested` to a recorded decision (`approved`/`declined`) with
   decider and note. The decider is never the record's creator,
   enforced in the store.
5. **Individual development plan records** — IDPs (`idp-`): a
   learner, a goal, an optional target date, and planned
   activities as data.
6. **Competency records** — competency definitions (`cpt-`) and
   learner competency records (`lcr-`) whose level is recorded
   **verbatim** in the caller's own scale. Nothing ranks,
   aggregates, or converts levels.
7. **Learner progress records** — per-learner, per-course progress
   records (`prg-`) with status (`not_started`/`in_progress`/
   `completed`), readiness, and percent. Records only — no content
   delivery.
8. **Learning experience records (LRS statements)** — statements
   (`stm-`): learner reference, verb, object reference, context,
   and an optional caller-supplied result text recorded verbatim.
   The record shape is pinned to exactly eight keys; there is no
   score field. The xAPI protocol runtime is Extended.
9. **Mandatory training compliance & derived status** — compliance
   assignments (`asg-`) with a due date. **Status is never
   stored**: derived at read, deterministically, from the
   assignment, the due date, the learner's progress records, and
   an explicit `as_of` reference date — `completed` when a
   completed progress record exists for the learner+course,
   `overdue` when `as_of` is after the due date, `current`
   otherwise. This derivation is the group's signature invariant
   and its negative control.
10. **Workflow & notification registries** — workflow definitions
    (`wfl-`: ordered step names, registered as data) that **never
    execute** — registering one changes no other record, ever,
    pinned by test — and notification records (`ntf-`) per
    recipient. Delivery transport is Extended.
11. **Search & summary reporting** — literal case-insensitive
    substring search over courses, content items, learners,
    events, and organizations; and a summary report computed on
    read from records only: counts by family and by state, with
    compliance counts by derived status at `as_of`. Counts — never
    scores.
12. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
13. **Access control** — role-based access hooks: platform roles
    `admin`, `instructor`, `learner`, `auditor` with a permission
    matrix enforced on every operation, layered with learner
    scope: a learner-role actor reads only records whose
    `learner_ref` is their own name, and catalog items visible to
    them under decision 6.
14. **Audit log** — an append-only audit trail: every mutation,
    every report read, and every denied attempt, recorded with
    actor, action, target, and UTC timestamp.
15. **Organization & portal registry** — organizations (`org-`):
    an opaque `ref` (unique), a label, and a portal label (the
    branded portal's name as data). The registry is the anchor
    for learner membership and catalog visibility (decision 6).
    Portal rendering is Extended.
16. **Certificate award records** — certificates (`crt-`): a
    learner reference, an optional course, a title, an optional
    award date, a note, and the recording actor. Append-only
    facts; learner scope applies. Rendering, delivery, and
    verification are Extended.
17. **Continuing education records** — CE records (`ceu-`): a
    learner reference, an opaque activity reference, a
    caller-supplied credit text recorded **verbatim** (never
    parsed, summed, or converted), and an optional recorded-on
    date. Learner scope applies. Credit accounting beyond records
    is Extended.

## Control baseline (traceability)

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low / LI-SaaS** (per
  `../../crosswalk.md`). One member sits at Low, the other at
  LI-SaaS; both are L1, so the baseline is the Low baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring), cross-walked to the 17 practices of NIST
  SP 800-171 Rev. 2 / FAR 52.204-21 that define CMMC L1. The
  baseline is authored fresh at Low for this build: the L2 build's
  Moderate mappings are **not** carried down. In particular the
  audit mapping stays on the Low side — **AU-2 / AU-3 only; AU-6
  and AU-9 are deliberately NOT imported.**
- **Feature → control family mapping (this build):**
  - Access control (platform roles + learner scope + catalog
    visibility) → **AC** (AC-2 account management, AC-3 access
    enforcement, AC-6 least privilege), **IA** (IA-2
    identification & authentication — identity is supplied by the
    embedding organization via user/role headers; the service
    ships hooks, not an identity provider).
  - Authorization decisions → **AC-5** (separation of duties —
    the decider of an authorization is never its creator,
    enforced in the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records — append-only store, audit-read restricted to the
    `audit_read` permission). Nothing beyond AU-2/AU-3 is claimed
    at this tier.
  - Records & registries → **SI** (SI-10 information input
    validation — malformed input, including a bool percent or
    capacity, a duplicate active registration, a promotion into a
    full event, an unknown visibility, or an unresolvable
    organization reference, is rejected whole, never partially
    applied) and **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
  - Derived-never-stored status → a build discipline answering to
    the AU-2/AU-3 record set: the compliance position is computed
    deterministically from retained records at an explicit
    reference date, so it is reviewable and reproducible from the
    record set alone. No AU-6 claim is made at this tier.
  - Opaque-reference privacy is a build discipline answering to
    the same input discipline: because no entity shape has a
    field for a real personal identifier, none can be stored,
    leaked, or transmitted by this build. It is stated as a
    discipline, not dressed up as an additional control claim.
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either. FedRAMP authorizes products; CMMC certifies
  organizations; the tier is a planning/matching equivalence,
  never a credential claim.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `lms` under `src/`,
runnable and testable with `PYTHONPATH=src`. Ids are sequential per
object type with fixed prefixes (`lrn-`, `crs-`, `cnt-`, `les-`,
`evt-`, `reg-`, `aut-`, `idp-`, `cpt-`, `lcr-`, `prg-`, `stm-`,
`asg-`, `wfl-`, `ntf-`, `org-`, `crt-`, `ceu-`); a failed operation
consumes no id and changes nothing. Statuses that depend on dates
or counts (compliance status, event seat counts) are derived at
read and never stored. The carried functions keep the L2 build's
signatures and semantics exactly; the deltas below are the whole of
the difference.

- `lms/access.py` — `User(name, role)`; roles
  `admin|instructor|learner|auditor`. The L2 action list plus six
  new actions: `organization_read`, `organization_write`,
  `certificate_read`, `certificate_write`, `continuing_ed_read`,
  `continuing_ed_write`. Record reads = the L2 read set plus
  {organization, certificate, continuing_ed}`_read`; instructor
  writes = the L2 instructor set plus {certificate_write,
  continuing_ed_write}; `organization_write` is admin-only.
  `PERMISSIONS`: admin = reads + all writes + {report_read,
  audit_read}, instructor = reads + instructor writes +
  {report_read}, learner = reads only, auditor = reads +
  {report_read, audit_read}; `require(user, action)` raises
  `PermissionDenied`.
- `lms/audit.py` — as L2: `AuditLog(path=None)`;
  `.record(actor, action, target, details=None)` → entry `{ts,
  actor, action, target, details}`; `.entries()` returns copies.
  Append-only; optional JSONL file.
- `lms/errors.py` — as L2: `LmsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.
- `lms/store.py` — `LmsStore(audit=None)`. All L2 operations with
  L2 signatures and semantics, plus these deltas:
  - `create_organization(ref, label, actor, portal_label="")` →
    `org-` record `{id, ref, label, portal_label, created_by,
    created_utc}`; `ref` unique, duplicates rejected whole.
    `get_organization(organization_id, actor=None)`,
    `list_organizations(actor=None)`. Action: organization_write /
    organization_read.
  - `create_learner(ref, label, actor, org_ref=None)` — as L2 plus
    the optional organization reference: when given, it must
    resolve to an existing organization's `ref`, else
    `ValidationError`; the stored record carries `org_ref` (the
    value or `None`).
  - `create_course(title, actor, kind="course", code=None,
    description="", org_ref=None, visibility="community")` and
    `create_content_item(title, standard, actor, course_id=None,
    org_ref=None, visibility="community", external_ref=None)` —
    `visibility` must be exactly `"organization"` or `"community"`;
    `visibility="organization"` requires an `org_ref` that
    resolves; any given `org_ref` must resolve. Stored records
    carry `org_ref` and `visibility` (content items also
    `external_ref`). The content `standard` enum is the L2 list
    plus `"html"` (the enum's values are the substrate's lowercase
    tokens — `scorm_1_2`, `xapi`, `pdf` — so HTML's token is
    lowercase too).
  - Catalog visibility enforcement: for a learner-role actor,
    `get_course` / `list_courses` / `get_content_item` /
    `list_content_items` expose an item only when its visibility
    is `"community"` or its `org_ref` equals the org_ref of the
    learner record whose `ref` is the actor's name; a learner with
    no record or no organization sees community items only. A
    single get on an invisible item raises `PermissionDenied`
    (the store's scope discipline, as L2). Other roles are
    unrestricted.
  - `record_certificate(learner_ref, title, actor, course_id=None,
    awarded_on=None, note="")` → `crt-` record `{id, learner_ref,
    course_id, title, awarded_on, note, created_by, created_utc}`;
    `awarded_on`, when given, must be an ISO calendar date.
    `get_certificate(certificate_id, actor=None)`,
    `list_certificates(actor=None, learner_ref=None)`. Learner
    scope applies (a learner reads only their own certificates).
    Action: certificate_write / certificate_read.
  - `record_continuing_education(learner_ref, activity_ref,
    credit_text, actor, recorded_on=None)` → `ceu-` record `{id,
    learner_ref, activity_ref, credit_text, recorded_on,
    created_by, created_utc}`; `credit_text` is stored verbatim
    and never parsed; `recorded_on`, when given, must be an ISO
    calendar date. `get_continuing_education(record_id,
    actor=None)`, `list_continuing_education(actor=None,
    learner_ref=None)`. Learner scope applies. Action:
    continuing_ed_write / continuing_ed_read.
  - `search` additionally covers organizations (match on `ref`,
    `label`, `portal_label`) and returns them under
    `"organizations"`.
  - `report` additionally returns `"organizations"`,
    `"certificates"`, and `"continuing_education_records"` counts.
    Counts only — the recursive no-score discipline is unchanged
    and test-enforced.
  - Learner-owned operations enforce learner scope for learner-role
    actors (as L2). The store audits every successful mutation;
    the service layer audits denied attempts (`action:denied`) and
    audit reads, so nothing is recorded twice.
- `lms/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User` /
  `X-Role` headers (role must match the registry). L2's endpoints,
  plus: `/organizations` (GET list = organization_read, POST =
  organization_write; GET one = organization_read),
  `/certificates` (GET = certificate_read, POST =
  certificate_write), `/continuing-education` (GET =
  continuing_ed_read, POST = continuing_ed_write). Create bodies
  accept the new optional fields (`org_ref`, `visibility`,
  `external_ref`, `portal_label`, `awarded_on`, `recorded_on`,
  `credit_text`, `activity_ref`). Errors are JSON `{error}` with
  400/401/403/404 as applicable; unknown body keys are refused
  (400). Denied attempts are audited.
- `lms/__main__.py` — `python -m lms serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=instructor, carol=learner, dana=auditor`
  (documented as demo identities; production identity is the
  embedding organization's).

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. The suite includes the **negative control**: a
mutant store whose `_derive_status` always returns `"current"`
fails the canonical derivation expectations — and the external
mutation drill (patching the overdue branch of `_derive_status` to
`return "current"` in the real `store.py`) makes exactly the
recorded number of tests fail; see `tests/README.md` for the drill
record and the coverage statement below for the measured counts.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Carried from the L2 union's Extended set (specified there, still
Extended at this tier):

- Learning delivery engine (course playback and delivery runtime;
  the substrate holds its records)
- SCORM / AICC / cmi5 packaging & distribution runtime — at this
  tier including the HTML export CloudLCMS names (standards
  survive as content-item metadata; this gap now has an L1
  claimant)
- xAPI protocol runtime & LRS conformance (statement ingestion
  endpoints, statement forwarding, xAPI query protocol)
- EHRI integration engine (OPM EHRI data feeds & reporting)
- Learning analytics & outcomes-effectiveness engines (beyond
  registry counts)
- Career mapping & training-recommendation engine
- Leadership succession planning suite
- Candidate review / talent acquisition system
- Employee survey engine
- Knowledge base / wiki platform
- Web CMS platform
- Lesson-plan editor & content authoring tools for plan records
  (the registry holds plan records)
- SF-182 form rendering, routing & signature workflow (the build
  records authorizations and their decisions)
- Configurable report builder & dashboard engine (the registry
  computes fixed summaries & search)
- Workflow execution engine (routing and orchestration of
  registered definitions; the registry holds definitions only)
- Notification automation & delivery transport (email / SMS /
  push; the build records notifications)
- Identity provider / MFA / SSO service (IA-2 stays with the
  embedding organization)

New at this tier, from this tier's own forks:

- **Learning content authoring environment** (CloudLCMS) — rapid
  authoring, collaborative authoring workspaces, custom themes &
  menus, plugin framework, Section 508-conformant course output
- **Course posting & publication workflow** (TRAIN) — the
  create-and-post workflow and external-training linking beyond
  registry records
- **Branded portal rendering & presentation engine** (TRAIN) —
  the per-organization branded portal itself (the registry holds
  portal labels and the visibility rule)
- **Continuing education management engine** (TRAIN) — credit
  accounting, renewal cycles, and CE reporting beyond verbatim
  records
- **Certificate issuance & verification service** (TRAIN) —
  certificate rendering, delivery, and public verification (the
  build records award facts)
- **System integration engines** (TRAIN) — the system integrations
  the fork asserts as an offering (connector runtimes; EHRI's
  engine above is the HR-specific case)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (asserted in substance by TRAIN;
single-tenant reference deployment); demo identities are hooks,
not an IdP.

## Coverage statement (for this build)

- Specs: **2 / 2** forks spec'd, with **1 tagged claim** under the
  verbatim L2 taxonomy (CloudLCMS: content standards &
  distribution), TRAIN pinned at zero claims, and every
  asserted-but-unnamed function itemized above with a disposition.
- Core: **17 / 17** core functions implemented, at the Low/L1
  baseline, each with tracing tests.
- Tests: **137 run, 137 passed**, including the
  mutation-verified compliance-derivation negative control
  (drill: 9 failures under the mutant, store restored
  SHA-256-identical).
- Extended: the 23 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
