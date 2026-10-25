# Union Spec — Education & Training, CMMC L2 (DeadRamp Phase 2, Group 13)

The merged functional spec for the Education & Training sibling group at
the L2 tier: **8 forks, all FedRAMP Moderate**, reconciled zero-diff
(`specs/specs.json` ↔ `forks.json` category "Education & Training" +
`cmmc_tier` "L2" ↔ MAP.md "Education & Training — L2 (8)").

The group: Blackboard LMS (Blackboard) · Acadis Readiness Suite
(Envisage Technologies LLC) · Laerdal -- SimCapture Cloud Government
(Laerdal Labs D.C.) · NEOGOV Cloud (NEOGOV) · Palladium (PDRI by Pearson)
· Pepelwerk Government (Pepelwerk LLC) · Next Generation Cloud Platform
(Peraton Corporation) · Gov Secure Cloud (PSI Services LLC).

This is a heterogeneous, thinly described group. The source's
"Education & Training" category collects a general LMS (Blackboard), a
training-readiness/compliance suite (Acadis), a healthcare simulation
capture system (SimCapture), a public-sector HCM suite with a training
arm (NEOGOV), a hiring-assessment system (Palladium), a talent-profile /
career marketplace (Pepelwerk), a general PaaS that hosts an employee-
performance module (Peraton NGCP), and a secure computer-based testing
cloud (PSI). There is no single product they all are, and two members
are **platform-layer members whose education surface is thin, recorded
honestly**: Peraton NGCP claims only a performance-management module
name and its PaaS hosting (2 claims, neither a learning function), and
NEOGOV's education surface is one training phrase ("train teams") inside
an HCM/recruiting suite. What the claim counts below prove is a
**records substrate**: courses/programs held in a registry, learners
enrolled or registered, progress/readiness tracked, assessments
administered, certification/credential status recorded, compliance
assignments tracked, and reports produced over those records. The
merged build implements that substrate; each vendor's delivery,
simulation, matching, and assessment engines on top of it are Extended
functions, named in the long tail.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split and
matched against a 21-family taxonomy defined from this category's
descriptions. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is
stored in `specs/specs.json` as evidence, so every claim is auditable.
**43 claims survived.** Six wording-artifact corrections were needed
and are itemized below and in `scratch/ARTIFACTS.md` (48 broad
first-pass hits → 43: 6 false hits removed, 1 true hit recovered).
**No fork has zero claims**, but the floor is low because the
descriptions are short (224–2,258 characters): Per-fork claim counts:
Pepelwerk Government 11, Gov Secure Cloud 8, Acadis Readiness Suite 7,
NEOGOV Cloud 5, SimCapture Cloud Government 4, Blackboard LMS 3,
Palladium 3, Next Generation Cloud Platform 2. Counts are therefore a
**floor**, not a ceiling, on what these products do — Blackboard's
entire description is two sentences, and no conclusion about the real
Blackboard LMS should be drawn from its 3 tags.

### Wording-artifact corrections (itemized; full text in `scratch/ARTIFACTS.md`)

1. **access_control — Acadis (FR1707156421) REMOVED.** Broad pattern's
   bare `authorized` matched "authorized at the FedRAMP Moderate
   baseline" — the offering's own authorization status, not user
   access control. Tightened to authorized-user / access-control
   phrasing; PSI still claims.
2. **access_control — Palladium (FR2326160742) REMOVED.** Bare `role`
   matched job "roles" candidates are matched to, not system roles.
   `role` survives only as `role-based`.
3. **content_media — PSI (FR2607643783) REMOVED.** Bare `delivery`
   matched "delivery … of computer-based assessments" — assessment
   delivery, already claimed under assessments; the Group 11 Trellix
   artifact class. Blackboard ("content") and SimCapture ("recording")
   still claim.
4. **hosting_platform — NEOGOV (FR2119265538) REMOVED, SimCapture
   (FR2422436886) RECOVERED.** Bare `platform` is a product noun, not a
   hosting claim. Tightened to architectural phrases (PaaS,
   multi-tenant, hosted-within, deployed-in, deploys-multiple). Family
   count unchanged (4), composition corrected.
5. **API/integrations family DROPPED (0/8).** The substring `api`
   matched only "Human C**api**tal Management" (NEOGOV). No description
   contains the word API or any integration claim; recorded as a named
   absence below.
6. **Media streaming family DROPPED (0/8).** The substring `stream`
   matched only "**stream**line" (Pepelwerk). No description claims
   video/media streaming; recorded as a named absence below.
7. **learner_progress — Acadis evidence RE-BASED (kept, count
   unchanged).** Bare `tracking` first hit "certification tracking"
   (the credential family's evidence); the claim now rests on Acadis's
   "training and readiness management platform" sentence.

Reviewed and **kept, with caveats**: PSI's certificates claim rests on
"assessment programs used for licensure, certification … and
credentialing" (programs supported, not credentials issued); Pepelwerk's
rests on Talent Profiles capturing "education/certifications" (credential
data in a profile, not issuance) — both are therefore specified as
credential *records*, never issuance. Pepelwerk's performance claim
("CTMS performance process") is thinner than Peraton's named module;
NEOGOV's training claim is the single phrase "train teams." PSI's
"secure assessment delivery" / "test session administration" were
**not** tagged as proctoring or identity verification — no description
in this group claims either.

## Function ranking — all 8 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 4 | Hosting & platform services (PaaS, multi-tenant, hosted cloud) | Platform note — not a learning function; single-tenant reference deployment (see gaps) |
| 2 | 3 | Course, catalog & training program management | **Core** — course/catalog registry |
| 2 | 3 | Certification, licensure & credential records | **Core** — credential records (not issuance; see caveats) |
| 2 | 3 | Reporting, dashboards & analytics | Core — reporting over the records; dashboard/analytics engines Extended |
| 2 | 3 | Talent profiles, skills & best-fit matching | Extended — matching/marketplace engines; profile records are substrate-adjacent |
| 2 | 3 | Recruiting, hiring, onboarding & workforce management | Extended — HCM/HRIS domain suite |
| 7 | 2 | Enrollments & candidate registration | **Core** — enrollment/registration records |
| 7 | 2 | Learner progress, readiness & experience tracking | **Core** — progress/readiness records |
| 7 | 2 | Assessments & testing — delivery & administration | **Core** — assessment records; delivery engines and scoring Extended |
| 7 | 2 | Compliance training & compliance management | **Core** — compliance assignments & status |
| 7 | 2 | Scheduling of training & assessment sessions | **Core** — scheduling records |
| 7 | 2 | Training delivery & skills development | Extended — delivery itself; assignment/progress records are Core |
| 7 | 2 | Learning content, recording & media | Extended — content delivery, recording & playback engines |
| 7 | 2 | Employee performance management | Extended — HR domain module |
| 7 | 2 | Data storage, processing & profile data capture | Extended / platform layer — storage & processing services |
| 16 | 1 | Access control & authorized-user access | **Core** — RBAC (claim support thin: 1/8 explicit; see Core note) |
| 16 | 1 | Simulations & simulation debriefing | Extended — simulation capture/debrief engine |
| 16 | 1 | Peer interaction, discussion & social learning | Extended — collaboration surface |
| 16 | 1 | Career exploration, coaching & transition support | Extended — career services |
| 16 | 1 | AI & automation tools | Extended — AI Career Assistant / automation (models, not substrate) |
| 16 | 1 | Policy management | Extended — policy administration domain |

**Named absences (0/8, checked with broad patterns — findings, not
oversights):** deterministic **scoring/grading** of assessments (no
description uses score/grade wording); **proctoring & identity
verification/proofing**; **notifications/reminders/alerts**; **audit
logging** in descriptive text; **API/integrations** (only hit was the
substring inside "Capital"); **video/media streaming** (only hit was
"streamline"); **course content authoring**; explicit **due
dates/deadlines/expiry** wording and explicit **completion/transcript**
wording. The Core below is honest about the two places where it reaches
past the descriptive counts (due-date derivation, audit) and says why.

## The Core — what the merged build implements (10 functions)

The shared substrate the counts support, plus two baseline hooks
flagged where the counts do not:

1. **Course/catalog registry** — courses and training programs as
   records (course/program registry). *Support: course_catalog 3/8
   (Blackboard's learning environment, Acadis's training program
   management, Pepelwerk's course matching).*
2. **Enrollments & registrations** — learner/candidate enrollment and
   registration records against registry entries. *Support:
   enrollment_registration 2/8 (Pepelwerk student enrollment, PSI
   candidate registration).*
3. **Learner progress & readiness records** — per-learner progress,
   readiness, and tracked-experience records; completion is recorded
   as the terminal progress state. *Support: learner_progress 2/8
   (Acadis readiness management, SimCapture tracking of simulation
   experiences). Flag: the word "completion" appears in 0/8
   descriptions; completion records are the record form the claimed
   tracking presupposes, not a separately claimed feature.*
4. **Assessment records** — records of assessments administered
   (program, candidate/learner, session, administration state).
   *Support: assessments 2/8 (Palladium administering assessments,
   PSI computer-based assessment delivery/administration).
   Deterministic scoring of objective items is **not** in the Core:
   scoring/grading wording is 0/8, so scoring is Extended below.*
5. **Certificate/credential records** — certification, licensure, and
   credential records and their tracking (Acadis's "certification
   tracking" is the group's own phrase). *Support:
   certificates_credentials 3/8. The Core holds records; credential
   **issuance** is claimed by 0/8 and is not specified.*
6. **Compliance assignments & status derivation** — compliance
   training assigned to learners with a due date, with status
   (current/overdue) derived deterministically from assignment,
   due date, and progress records. *Support: compliance_training 2/8
   (Acadis compliance-driven training, NEOGOV compliance needs) and
   scheduling 2/8. Flag: explicit due-date wording is 0/8; the
   assignment + due-date + derived-status triple is the minimal
   record structure compliance **tracking** presupposes, and the
   derivation itself is deterministic substrate logic, not a vendor
   engine — included on that basis and flagged here.*
7. **Scheduling records** — scheduled training and assessment
   sessions bound to registry entries and enrolled learners/candidates.
   *Support: scheduling 2/8 (Acadis scheduling, PSI candidate
   scheduling / test sessions).*
8. **Reporting over the records** — reports and queries over course,
   enrollment, progress, assessment, credential, and compliance
   records. *Support: reporting_analytics 3/8 (Acadis operational
   reporting, Pepelwerk analytics/dashboard, PSI reporting). The Core
   is reporting over substrate records; dashboard and predictive-
   analytics engines are Extended.*
9. **Access control (RBAC)** — role-based access in
   admin/instructor/learner/auditor-style roles, enforced before any
   state change. *Support: access_control 1/8 explicit (PSI's
   "authorized agency users") — thin descriptive support, stated
   plainly. RBAC is Core because the L2/Moderate baseline requires it
   (AC/IA families, traceability below) and because every sibling's
   records presuppose differentiated admin/learner access; it is a
   baseline hook, not a claim-count winner.*
10. **Audit log** — append-only audit of every mutation and denied
    attempt. *Support: 0/8 descriptive claims — no description in this
    group mentions audit. Included solely as an L2/Moderate baseline
    hook (AU family), exactly as in sibling groups, and flagged here
    so no reader mistakes it for a claimed vendor function.*

## Long tail — Extended, by name

- **Talent, skills & marketplace matching** (talent_skills 3/8;
  career_development 1/8; ai_automation 1/8) — Palladium's best-fit
  pinpointing, Pepelwerk's talent-development marketplace, course
  matching engine, AI Career Assistant, and career coaching/exploration
  services. Matching and recommendation are vendor engines over
  profile records; the engines are Extended even though the family
  ties for the group's highest learning-function count — the same
  honesty rule sibling Group 9 applied to learned inference.
- **Recruiting, HCM/HRIS & workforce management suite**
  (recruitment_workforce 3/8; performance_management 2/8;
  policy_management 1/8) — NEOGOV's source/recruit/hire/onboard/retain
  suite, public-safety workforce platform, policy management, and
  Peraton's ePerformance module: an HR domain system adjacent to, not
  part of, the learning substrate.
- **Course content authoring & delivery, media streaming** —
  content_media claims 2/8 (Blackboard content, SimCapture recording),
  but authoring is 0/8 and streaming is 0/8 (see named absences); the
  delivery/playback engines are Extended.
- **Simulation engines** (simulations 1/8) — SimCapture's healthcare
  simulation recording, debriefing, and playback; the tracked-
  experience *records* are Core (function 3), the capture engine is not.
- **Remote proctoring & identity proofing** — 0/8 claims; PSI's secure
  delivery and test-session administration do not claim them.
  Specified as a gap so the absence is a finding.
- **Deterministic scoring & AI grading** — scoring of objective items
  0/8 explicit; grading/tutoring of free text 0/8. Both Extended; the
  Core holds assessment records only.
- **Skills-marketplace matching** — see talent/marketplace above
  (Pepelwerk's marketplace creation, Palladium's best-fit matching).
- **General cloud hosting / PaaS** (hosting_platform 4/8, the group's
  largest family) — Peraton NGCP is a general platform that deploys
  other SaaS products; Acadis/SimCapture/PSI name their hosting
  environments. Hosting is a platform-layer property, never a learning
  function; the merged build is a single-tenant reference deployment
  and says so.
- **Collaboration & social learning** (collaboration_social 1/8) —
  Blackboard's peer-to-peer interaction and discussions.
- **Data storage & processing services** (data_services 2/8) — PSI's
  boundary storage/processing services and Pepelwerk's profile data
  capture pipelines, beyond the substrate's own records.
- **Notifications & reminders** — 0/8 claims, despite being the natural
  companion of Core function 6 (due dates). Named here as a gap: a
  reminder engine may be built later, but no sibling's description
  supports claiming one now.
- **Integrations & APIs** — 0/8 claims (see correction 5). The merged
  build's own API surface, if any, is its own design, not a union
  function.

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes no
tier (Merge Rules 1–2: union of baselines, highest tier wins — here
all parents already sit at the same tier).

| Core function | Control families | How the build answers |
|---|---|---|
| Course/catalog registry | CM-6, SI-12 | Registry entries are explicit, configuration-controlled records; nothing is offered that is not registered |
| Enrollments & registrations | AC-2, AU-2 | Enrollment is an explicit, auditable record binding a learner to a registry entry |
| Learner progress & readiness records | AU-6, SI-12 | Progress/readiness state is a reviewable record per learner, retained with the record set |
| Assessment records | AU-2, AU-3, SI-10 | Every administration leaves a record with content; inputs are validated before any record exists |
| Certificate/credential records | AU-2, SI-12 | Credential status changes are auditable events on retained records (records only — no issuance claim) |
| Compliance assignments & status derivation | AU-6, CA-7, CM-6 | Status is derived deterministically from assignment, due date, and progress; derivation is queryable and reviewable |
| Scheduling records | AU-2, CM-6 | Sessions are explicit records bound to registry entries and enrollments |
| Reporting over the records | AU-6, CA-7 | Reports read the substrate records only; no side-channel data |
| RBAC (admin/instructor/learner/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; identity itself is supplied by the embedding organization (see caveat) |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** FedRAMP authorizes
PRODUCTS, CMMC certifies ORGANIZATIONS. A FedRAMP impact level is a
statement about a cloud service offering; a CMMC level is a statement
about a company and how it handles FCI/CUI. The L2 / FedRAMP Moderate
equivalence used here is a **planning/matching equivalence only**: it
says these forks sit at comparable assurance weight so they can be
grouped and merged consistently. It does **not** claim that a
FedRAMP-authorized product confers CMMC certification on anyone, that
a CMMC-certified organization holds a FedRAMP authorization, or that
either regime accepts the other as evidence. This traceability is a
planning mapping; the merged build is not a FedRAMP authorization and
confers no CMMC certification.

Standing platform notes (every group): demo identities are hooks, not
an IdP — IA-2 stays with the embedding organization; encryption at
rest is deployment-layer; TLS applies when a certificate is
configured. Multi-tenancy, named in prose by SimCapture, is likewise a
deployment property: the merged build is a single-tenant reference
deployment and says so.

## Coverage statement (for this spec batch)

- Forks spec'd: **8 / 8**, each with evidenced claims (43 total).
- Taxonomy: **21 function families**, defined from this category's
  descriptions; 7 further families checked and found at **0/8**
  (scoring, proctoring/identity, notifications, audit-in-text,
  API/integrations, streaming, authoring) and recorded as named
  absences rather than dropped silently.
- Core specified: **10 functions** (8 claim-supported, 1
  baseline-supported with thin claims — RBAC, 1 baseline-only —
  audit), each flagged as such.
- Extended / gap list: 12 named items above. No implementation code
  in this batch — specs and union spec only.
