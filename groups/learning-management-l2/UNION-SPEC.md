# Union Spec — Learning Management, CMMC L2 (DeadRamp Phase 2, Group 48)

The merged functional spec for the **Learning Management L2
singleton**: **1 fork**, category **Learning Management** (a
brand-new category — no group exists at any other tier; "Education
& Training" is a different registry category with its own shipped
groups, Groups 13 and 30, and the two are **not** merged), CMMC
tier **L2** (the member is FedRAMP **Moderate** in `forks.json` —
verified). The member list was reconciled two ways with **zero
diffs**: `forks.json` carries exactly one Learning Management / L2
entry, and MAP.md's category arithmetic agrees (Learning Management
total **1** = L1 0 + L2 1 + L3-adjacent 0 + untiered 0). MAP.md's
sibling-group sections list only groups of size 2 or more, so no
prose section exists for this singleton; the arithmetic is the
check, as in the earlier singleton builds.

Per-fork spec sheet: [`specs/specs.json`](specs/specs.json) — 1
entry, with the offering's full public marketplace description and
its function claims tagged from that description, every claim
carrying the source sentence as evidence. Source: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product record joined by FedRAMP ID **F1405214357**.

## How functions were counted (a new category: the Group 1 method)

Learning Management has no parent group, so there is no inherited
taxonomy. The taxonomy below was defined **from this fork's own
description**: families are named from the description's own
functional vocabulary, each with a verbatim match pattern, matched
against the description's sentences by `scratch/extract.py`. A
function is claimed **only** when a sentence contains matching
text; the matching sentence is stored as the claim's evidence in
the spec sheet. Marketing prose gets no tags. **26 claims in total
— the single fork claims every family its own vocabulary defines.**
Counts are a **floor**, not a ceiling.

Two structural facts about the source text shape the evidence (full
log in `scratch/ARTIFACTS.md`): the Callisto baseline sentence is a
single semicolon-joined sentence in the source and evidences twelve
families; the Career Voyager paragraph is likewise one sentence
evidencing four. Wording-artifact corrections: the enclave framing
and product-list sentences tag (almost) nothing; "assessments" in
the succession-planning sentence is not learning assessment
administration (no assessment family exists in this taxonomy);
"Certification" occurs only inside the SF-182 form's proper name
(no credential family exists); "API" occurs only inside
"Experience API (xAPI)"; the broad scoring pattern's only hits are
the substring inside "SCORM" (no scoring family exists); and the
"currently In Process" application named at the end is not part of
the authorized offering and tags nothing.

## Function ranking — the singleton

| # | Function | Forks claiming | Disposition in this build |
|---|---|---:|---|
| 1 | Registration management for learning events | 1 | **Core** — event & registration records, waitlist as recorded state |
| 2 | Mandatory training compliance | 1 | **Core** — assignments with status **derived at read**, never stored |
| 3 | Learning record store — experience data capture, storage & return (xAPI LRS) | 1 | **Core slice** — experience statement records; the xAPI protocol runtime is Extended |
| 4 | Learner activity tracking | 1 | **Core** — progress & activity records the tracking claim presupposes |
| 5 | Training authorization & certification forms (SF-182) | 1 | **Core** — authorization records with recorded decisions |
| 6 | Individual Development Plans (IDP) | 1 | **Core** — development plan records |
| 7 | Competency management | 1 | **Core** — competency definitions & learner competency records (levels verbatim) |
| 8 | Lesson plans | 1 | **Core slice** — lesson plan records in the catalog; authoring is Extended |
| 9 | eLearning content management | 1 | **Core** — content registry records; delivery/runtime Extended |
| 10 | Adjustable workflow | 1 | **Core slice** — workflow definitions registered as data, **never executed**; the execution engine is Extended |
| 11 | Automated notifications | 1 | **Core slice** — notification records; automation & delivery transport are Extended |
| 12 | Wait list management | 1 | **Core** — part of the registration records (recorded state, capacity-derived seats) |
| 13 | Reporting & configurable reports | 1 | **Core slice** — registry summaries & search computed from records; the configurable report builder is Extended |
| 14 | Learning delivery & management | 1 | Extended — the delivery engine itself (the substrate holds its records) |
| 15 | Content standards & distribution (SCORM / AICC / cmi5) | 1 | Extended — packaging/distribution runtime; the standards are recorded as content-item metadata in Core |
| 16 | EHRI data collection & reporting (HR integration) | 1 | Extended — the EHRI integration & feed engine |
| 17 | Learning analytics & outcomes analysis | 1 | Extended — the analytics engine (Core reporting is counts over records) |
| 18 | Career mapping & recommended training | 1 | Extended — mapping/recommendation engine; its competency & catalog records are Core |
| 19 | Leadership succession planning | 1 | Extended — talent-domain suite |
| 20 | Candidate review (talent acquisition) | 1 | Extended — talent-domain suite |
| 21 | Employee surveys & data collection | 1 | Extended — survey engine |
| 22 | Knowledge base / wiki platform (adjacent product) | 1 | Extended — an adjacent enclave product, not the learning substrate |
| 23 | Web content management platform (adjacent product) | 1 | Extended — an adjacent enclave product, not the learning substrate |
| 24 | Identity & authentication — MFA / SSO (platform) | 1 | Platform note — the build ships RBAC hooks, not an IdP |
| 25 | Multi-tenancy (platform note) | 1 | Platform note — deployment property; single-tenant reference deployment |
| 26 | Cloud hosting platform (platform note) | 1 | Platform note — delivery prose; deployment layer |

**Named absences, stated plainly (checked with broad patterns —
findings, not oversights):** the description contains **no scoring
or grading vocabulary** (the substring "score" occurs zero times);
**no assessment-administration vocabulary** (the single word
"assessments" names succession-planning resources); **no
credential/certificate vocabulary** beyond the SF-182 form's name —
nothing is issued, conferred, or tracked as a credential; **no
proctoring, content-authoring, discussion/social-learning, virtual
-classroom, gamification, or mobile-application vocabulary**. None
of these is a gap in the registry sense: nothing was claimed, so
nothing is owed. Where the build reaches past the claims, it does
so by the explicit core-boundary decisions below, never by silence.

**Core-boundary decisions (recorded, per the singleton precedents).**
(1) *Learner records.* Every learner-bound claim (registrations,
IDPs, compliance, the LRS's "central repository for learning
records") presupposes a learner the records bind to. Learners
therefore enter the build as a registry of **opaque references**:
a caller-supplied `ref` and a label, a shape pinned by test so no
field can hold a real personal identifier. (2) *Progress records.*
The tracking claim and the compliance claim jointly presuppose
per-learner progress records; completion is recorded as the
terminal progress state, and compliance derivation reads those
records — the Group 13 discipline, carried here because the claims
presuppose it, not because the categories were merged. (3) *Scores.*
None, anywhere. No claim defines a score, so no record shape
carries a score field and nothing computes one — pinned by test. A
statement's `result_text` is caller-supplied text recorded
verbatim, never parsed. Competency levels likewise are recorded
verbatim in the caller's own scale. (4) *The SF-182 decisions.* An
authorization record is not meaningful without its outcome, so
decisions are recorded on the record by a named decider — and the
decider is never the record's creator (separation of duties,
enforced in the store). The form itself — rendering, routing,
signature — is Extended. (5) *Lesson plans.* The claim names
lesson plans as baseline content; the build holds them as catalog
records (title, course, ordered references to catalog entries).
The authoring tool that composes them is Extended.

## The Core — what the merged build implements (14 functions)

One coherent, standards-based learning records service that the
fork's claimed functions presuppose, built clean-room from this
spec:

1. **Learner registry (opaque references)** — learners (`lrn-`)
   known only by a caller-supplied opaque `ref` (unique) and a
   label. The record shape is pinned: no field can hold a real
   identifier.
2. **Course, content & lesson-plan catalog** — courses and
   programs (`crs-`); content items (`cnt-`) whose `standard`
   field takes exactly the fork's own list (SCORM 1.2, SCORM 2004,
   AICC, xAPI, cmi5, MP3, MP4, PDF, other); lesson plans (`les-`)
   as catalog records referencing courses and content items.
3. **Events & registration management** — live/virtual learning
   events (`evt-`) with an optional capacity, and registrations
   (`reg-`) binding a learner to an event. A registration's state
   (`registered`/`waitlisted`/`cancelled`/`attended`) is a
   recorded fact; an event's `seats_taken`, `waitlist_count`, and
   `seats_open` are **derived at read** from the registrations —
   never stored. Registering into a full event records
   `waitlisted`; promotion is an explicit recorded state change,
   never an automation.
4. **Training authorization (SF-182) records** — authorizations
   (`aut-`) by a learner against a course or event, recorded from
   `requested` to a recorded decision (`approved`/`declined`) with
   decider and note. The decider is never the record's creator,
   enforced in the store.
5. **Individual development plan records** — IDPs (`idp-`): a
   learner, a goal, an optional target date, and planned
   activities as data (activity text, optional course reference).
6. **Competency records** — competency definitions (`cpt-`) and
   learner competency records (`lcr-`) whose level is recorded
   **verbatim** in the caller's own scale. Nothing ranks,
   aggregates, or converts levels.
7. **Learner progress records** — per-learner, per-course progress
   records (`prg-`) with status (`not_started`/`in_progress`/
   `completed`), readiness, and percent. Completion is recorded
   as the terminal progress state. Records only — no content
   delivery.
8. **Learning experience records (LRS statements)** — statements
   (`stm-`): learner reference, verb, object reference, context,
   and an optional caller-supplied result text recorded verbatim.
   The record shape is pinned to exactly eight keys; there is no
   score field. The xAPI protocol runtime is Extended; this is
   the records form the LRS claim presupposes.
9. **Mandatory training compliance & derived status** — compliance
   assignments (`asg-`) with a due date. **Status is never
   stored**: it is derived at read time, deterministically, from
   the assignment, the due date, the learner's progress records,
   and an explicit `as_of` reference date — `completed` when a
   completed progress record exists for the learner+course,
   `overdue` when `as_of` is after the due date, `current`
   otherwise. This derivation is the group's signature invariant
   and its negative control.
10. **Workflow & notification registries** — workflow definitions
    (`wfl-`: ordered step names, registered as data per scope)
    that **never execute** — registering one changes no other
    record, ever, pinned by test — and notification records
    (`ntf-`) per recipient. Delivery transport is Extended.
11. **Search & summary reporting** — literal case-insensitive
    substring search over courses, content items, learners, and
    events; and a summary report computed on read from records
    only: counts by family and by state, with compliance counts
    by derived status at `as_of`. Counts — never scores.
12. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
13. **Access control** — role-based access hooks: platform roles
    `admin`, `instructor`, `learner`, `auditor` with a permission
    matrix enforced on every operation, layered with learner
    scope: a learner-role actor reads only records whose
    `learner_ref` is their own name.
14. **Audit log** — an append-only audit trail: every learner,
    catalog, registration, authorization, plan, competency,
    progress, statement, compliance, workflow, and notification
    mutation, every report read, and every denied attempt,
    recorded with actor, action, target, and UTC timestamp.

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
  - Access control (platform roles + learner scope) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity
    provider; the fork's MFA/SSO claim belongs to its platform
    and is an IA-2 property of the embedding deployment).
  - Authorization decisions → **AC-5** (separation of duties —
    the decider of an authorization is never its creator,
    enforced in the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, audit-read restricted to
    the `audit_read` permission).
  - Records & registries → **SI** (SI-10 information input
    validation — malformed input, including a bool percent or a
    capacity, a duplicate active registration, and a promotion
    into a full event, is rejected whole, never partially
    applied) and **SC** (SC-8 transmission confidentiality — the
    server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated
    plainly, not claimed here).
  - Derived-never-stored status → **AU-6 / CA-7** posture: the
    compliance position is computed deterministically from
    retained records at an explicit reference date, so it is
    reviewable and reproducible from the record set alone.
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
`asg-`, `wfl-`, `ntf-`); a failed operation consumes no id and
changes nothing. Statuses that depend on dates or counts
(compliance status, event seat counts) are derived at read and
never stored.

- `lms/access.py` — `User(name, role)`; roles
  `admin|instructor|learner|auditor`; record reads = {catalog,
  learner, registration, authorization, plan, competency,
  progress, experience, compliance, workflow}`_read`; instructor
  writes = {registration, authorization, plan, competency,
  progress, experience, workflow}`_write`;
  `PERMISSIONS`: admin = reads + all writes (plus catalog_write,
  learner_write, compliance_write) + {report_read, audit_read},
  instructor = reads + instructor writes + {report_read},
  learner = reads only, auditor = reads + {report_read,
  audit_read}; `require(user, action)` raises `PermissionDenied`.
  Lesson plans sit in the catalog family (catalog_write);
  `plan_write` covers development plans (IDPs) — a recorded
  contract decision.
- `lms/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry `{ts, actor, action, target,
  details}`; `.entries()` returns copies. Append-only; optional
  JSONL file.
- `lms/store.py` — `LmsStore(audit=None)` with the operations
  named in the Core above. Learner-owned operations enforce
  learner scope for learner-role actors. The store audits every
  successful mutation; the service layer audits denied attempts
  (`action:denied`) and audit reads, so nothing is recorded twice.
- `lms/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`. Auth via `X-User` /
  `X-Role` headers (role must match the registry). Endpoints per
  the group README. Errors are JSON `{error}` with 400/401/403/404
  as applicable. Denied attempts are audited.
- `lms/__main__.py` — `python -m lms serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=instructor, carol=learner, dana=auditor`
  (documented as demo identities; production identity is the
  embedding organization's).
- `lms/errors.py` — `LmsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring or
module header naming the core function / spec claim / control
family it traces to. **104 tests**, including the **negative
control**: a mutant store whose `_derive_status` always returns
`"current"` fails the canonical derivation expectations — and the
external mutation drill (patching the overdue branch of
`_derive_status` to `return "current"` in the real `store.py`)
makes exactly 9 tests fail; see `tests/README.md` for the drill
record.

## Gaps — specified, not implemented (for the GAPS.md final batch)

- Learning delivery engine (course playback, the Moodle-based
  delivery runtime itself; the substrate holds its records)
- SCORM / AICC / cmi5 packaging & distribution runtime (uniform
  content access & deployment; standards survive as content-item
  metadata)
- xAPI protocol runtime & LRS conformance (statement ingestion
  endpoints, statement forwarding, xAPI query protocol; the
  substrate holds statement records in its own shape)
- EHRI integration engine (OPM EHRI data feeds, collection
  pipelines & EHRI reporting)
- Learning analytics & outcomes-effectiveness engines (beyond
  registry counts)
- Career mapping & training-recommendation engine (career
  ladders, skills-gap views, recommended training)
- Leadership succession planning suite
- Candidate review / talent acquisition system (fellowship &
  internship application processes)
- Employee survey engine (instrument design, collection
  campaigns; PowerSurvey)
- Knowledge base / wiki platform (the hardened MediaWiki product)
- Web CMS platform (the hardened Drupal baseline product)
- Content authoring tools & lesson-plan editor (the registry
  holds plan records)
- SF-182 form rendering, routing & signature workflow (the build
  records authorizations and their decisions)
- Configurable report builder & dashboard engine (the registry
  computes fixed summaries & search)
- Workflow execution engine (routing and orchestration of
  registered definitions; the registry holds definitions only)
- Notification automation & delivery transport (email / SMS /
  push; the build records notifications)
- Identity provider / MFA / SSO service (IA-2 stays with the
  embedding organization; the fork claims it of its platform)

Platform-layer: encryption at rest is deployment-layer (TLS when
configured); multi-tenancy (claimed by the fork; single-tenant
reference deployment); demo identities are hooks, not an IdP.

## Coverage statement (for this build)

- Specs: **1 / 1** forks spec'd, with **26 tagged claims** (one per
  taxonomy family, each with its source sentence as evidence).
- Core: **14 / 14** core functions implemented, at the Moderate/L2
  baseline, each with tracing tests.
- Tests: **104 run, 104 passed**, including the mutation-verified
  compliance-derivation negative control (drill: 9 failures under
  the mutant, store restored SHA-256-identical).
- Extended: the 17 gaps above are specified and named, **not**
  implemented in this build, and registered for the final batch.
