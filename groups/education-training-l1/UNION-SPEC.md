# Union Spec — Education & Training, CMMC L1 (DeadRamp Phase 2, Group 30)

The merged functional spec for the Education & Training sibling group
at the L1 tier: **2 forks, mixed FedRAMP impact levels** —
**Amplifire** (Amplifire) is **LI-SaaS** and **RQI1Stop** (RQI
Partners LLC) is **Low** — reconciled zero-diff three ways
(`specs/specs.json` ↔ `forks.json` category "Education & Training" +
`cmmc_tier` "L1" ↔ MAP.md "Education & Training — L1 (2)"). Each
fork's actual impact level is recorded in its spec sheet. Both members
are FedRAMP Certified in `forks.json` — verified.

This is the map's lightest tier. Both impact levels map to L1 on the
crosswalk (`../../crosswalk.md`): LI-SaaS is FedRAMP's own tailored
**subset** of the Low baseline for SaaS offerings, so the union of the
group's parent baselines is the Low baseline itself, and the highest
tier any parent carries is the Low family. The group baseline is
therefore the **NIST SP 800-53 Rev. 5 Low baseline** ⇔ **CMMC L1**
(the FAR 52.204-21 practice set), taken in full (Merge Rules 1 and 2).
The baseline section below is written fresh for this tier: Group 13's
Moderate citations (AU-6, AU-9, CA-7, SI-12, the 800-171 framing) were
**not** imported, and no Moderate/High apparatus is inherited
downward.

The group: a healthcare **adaptive training platform** (Amplifire —
patented algorithms that detect and correct knowledge gaps in
clinicians, nearly 3.5 billion learner interactions claimed in prose)
and a **CPR training SaaS** (RQI1Stop — RQI Partners, a partnership
of the American Heart Association and Laerdal Medical, delivering
modernized CPR training based on AHA guidelines from a multi-tenant
public cloud). There is no single product they both are. What they
share, underneath their verticals, is the learning-records substrate
Group 13's union established for this category: courses/programs held
in a registry, learners enrolled, progress tracked, assessments
administered, credential status recorded, compliance assignments
tracked, and reports produced over those records. The merged build
implements that substrate; each vendor's engine on top of it
(Amplifire's adaptive remediation engine, course content, CPR
curriculum delivery) is an Extended function, named in the long tail.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `../../raw/data_dump.json`; produced by the
General Services Administration, last change 2026-10-22) was
sentence-split and matched against **Group 13's 21-family taxonomy,
applied verbatim** — same function ids, labels, and matchers,
including all of Group 13's tightened forms after its wording-artifact
corrections, verified byte-identical between the two groups'
extractors — so counts are comparable across the category's tiers. A
family is claimed only when the offering's own description contains
matching text; the first matching sentence is stored in
`specs/specs.json` as evidence, so every claim is auditable. **1
claim survived.** The near-misses are documented in
`scratch/ARTIFACTS.md`: Amplifire's "training platform" (the taxonomy
keys on course / training program / learning environment /
curriculum), its "Patented algorithms" (the ai_automation family
keys on AI / artificial intelligence / automat-), its "learner
interactions" and "on-the-job performance" and bare "workforce"
(each beside, not inside, its family's pattern); RQI1Stop's "deliver
modernized CPR training" (beside course_catalog and
training_development alike) and its certification-free description
(no certification wording exists in it, verified — nothing was
inferred from the vendor's real-world CPR-certification purpose).
**The taxonomy was not re-tuned for this group** — that would corrupt
cross-tier comparability. Per-fork claim counts: RQI1Stop 1,
Amplifire 0 (a zero-claim sheet; its full text is preserved in the
spec sheet and nothing was invented for it). Counts are therefore a
**floor**, not a ceiling, on what these products do.

## Function ranking — all 2 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Hosting & platform services (PaaS, multi-tenant, hosted cloud) | Platform note — not a learning function; single-tenant reference deployment (see gaps) |
| 2 | 0 | Course, catalog & training program management | **Core** — carried, not claimed here (core-boundary decision; 3/8 at L2) |
| 2 | 0 | Enrollments & candidate registration | **Core** — carried (2/8 at L2) |
| 2 | 0 | Learner progress, readiness & experience tracking | **Core** — carried (2/8 at L2) |
| 2 | 0 | Assessments & testing — delivery & administration | **Core** — carried (2/8 at L2); administration records only (decision below) |
| 2 | 0 | Certification, licensure & credential records | **Core** — carried (3/8 at L2); records only, no issuance (decision below) |
| 2 | 0 | Compliance training & compliance management | **Core** — carried (2/8 at L2) |
| 2 | 0 | Scheduling of training & assessment sessions | **Core** — carried (2/8 at L2) |
| 2 | 0 | Reporting, dashboards & analytics | Core — reporting over the records, carried (3/8 at L2); dashboard/analytics engines Extended |
| 2 | 0 | Access control & authorized-user access | **Core** — RBAC baseline hook (1/8 at L2, 0/2 here) |
| 2 | 0 | Talent profiles, skills & best-fit matching | Extended — carried from the Group 13 union (3/8 at L2, 0/2 here) |
| 2 | 0 | Recruiting, hiring, onboarding & workforce management | Extended — carried (3/8 at L2, 0/2 here) |
| 2 | 0 | Training delivery & skills development | Extended — delivery itself, carried (2/8 at L2, 0/2 here) |
| 2 | 0 | Learning content, recording & media | Extended — carried (2/8 at L2, 0/2 here) |
| 2 | 0 | Employee performance management | Extended — carried (2/8 at L2, 0/2 here) |
| 2 | 0 | Data storage, processing & profile data capture | Extended / platform layer — carried (2/8 at L2, 0/2 here) |
| 2 | 0 | Simulations & simulation debriefing | Extended — carried (1/8 at L2, 0/2 here) |
| 2 | 0 | Peer interaction, discussion & social learning | Extended — carried (1/8 at L2, 0/2 here) |
| 2 | 0 | Career exploration, coaching & transition support | Extended — carried (1/8 at L2, 0/2 here) |
| 2 | 0 | AI & automation tools | Extended — carried (1/8 at L2, 0/2 here); see also the prose-described adaptive engine below |
| 2 | 0 | Policy management | Extended — carried (1/8 at L2, 0/2 here) |

**Named absences (0/2, checked with broad patterns — findings, not
oversights; verified programmatically, log in
`scratch/ARTIFACTS.md`):** deterministic **scoring/grading** wording;
**proctoring & identity verification/proofing**; **notifications/
reminders/alerts**; **audit** in descriptive text; **API/
integrations**; **streaming** (the substring `stream` appears in
neither description); course content **authoring**; explicit **due
date/deadline/expiry** wording; explicit **completion/transcript**
wording; **certification/credential/licensure** wording. The Core
below is honest about the two places where it reaches past this
group's descriptive counts (due-date derivation, audit) and says why —
the same flags Group 13 recorded, re-verified against this group's
own text.

## The core-boundary decision (recorded, Group 10 / Group 24 precedent)

Every learning-function family sits at 0/2 in this group, so **no
Core function is claim-supported by this group's own sheets**. The 10
Core functions stand anyway, on three stated grounds: (1) the
category substrate was established by Group 13's union for this same
category, from 43 evidenced claims at L2 — a wording artifact in two
short L1 descriptions is not a downgrade of the category's substrate;
(2) both products presuppose the substrate in their own words —
Amplifire is a "training platform" whose value is counted in "learner
interactions" (a registry of training offerings and records of
learner activity are what such a platform is made of), and RQI1Stop
exists to "deliver modernized CPR training" "as a SaaS offering"
(training delivered to learners, whose participation and currency are
the records the substrate holds); (3) two functions (RBAC, audit) are
baseline hooks the Low baseline itself calls for. The counts stay a
stated floor; nothing in this spec rounds a near-miss up into a claim
to justify the Core after the fact.

## The Core — what the merged build implements (10 functions)

The Group 13 substrate, carried to this tier whole:

1. **Course/catalog registry** — courses and training programs as
   records. *Support in this group: course_catalog 0/2 — carried
   under the core-boundary decision (3/8 at L2).*
2. **Enrollments & registrations** — learner/candidate enrollment
   and registration records against registry entries. *Support:
   enrollment_registration 0/2 — carried (2/8 at L2).*
3. **Learner progress & readiness records** — per-learner progress,
   readiness, and tracked-experience records; completion recorded as
   the terminal progress state. *Support: learner_progress 0/2 —
   carried (2/8 at L2). Flag, re-verified here: the word "completion"
   appears in 0/2 of this group's descriptions; completion records
   are the record form the claimed tracking presupposes.*
4. **Assessment records** — records of assessments administered
   (program, candidate/learner, session, administration state), item
   responses held verbatim. *Support: assessments 0/2 — carried (2/8
   at L2).* **Decision carried from Group 13, on this group's own
   evidence too:** deterministic scoring is **not** in the Core —
   scoring/grading wording is 0/2 here (and was 0/8 at L2), so
   assessments are administration records only and **no score field
   exists anywhere in the build**; scoring is Extended below.
5. **Certificate/credential records** — certification, licensure, and
   credential records and their tracked status. *Support:
   certificates_credentials 0/2 — carried (3/8 at L2).* **Decision
   carried from Group 13, on this group's own evidence too:**
   credential **issuance** is claimed by 0/2 here (and was 0/8 at
   L2); the Core holds records only, and no issuance engine is
   specified. (RQI's real-world CPR-certification purpose is nowhere
   in its description's wording and was not converted into a claim —
   see `scratch/ARTIFACTS.md` item 8.)
6. **Compliance assignments & status derivation** — compliance
   training assigned to learners with a due date, with status
   (current/overdue/completed) derived deterministically at read
   time from assignment, due date, and progress records — **status
   is never stored**. *Support: compliance_training 0/2 — carried
   (2/8 at L2). Flag, re-verified here: explicit due-date wording is
   0/2; the assignment + due-date + derived-status triple is the
   minimal record structure compliance tracking presupposes, and the
   derivation is deterministic substrate logic, not a vendor engine —
   included on that basis and flagged here, as at L2.*
7. **Scheduling records** — scheduled training and assessment
   sessions bound to registry entries and enrolled
   learners/candidates. *Support: scheduling 0/2 — carried (2/8 at
   L2).*
8. **Reporting over the records** — reports and queries over course,
   enrollment, progress, assessment, credential, and compliance
   records. *Support: reporting_analytics 0/2 — carried (3/8 at L2).
   Dashboard and predictive-analytics engines are Extended.*
9. **Access control (RBAC)** — role-based access in
   admin/instructor/learner/auditor-style roles, enforced before any
   state change, with learner scope (a learner reads only their own
   records). *Support: access_control 0/2 here (1/8 explicit at L2).
   RBAC is Core because the Low baseline requires access limitation
   (AC family; FAR 52.204-21's access-limitation practices) and every
   sibling's records presuppose differentiated access; it is a
   baseline hook, not a claim-count winner.*
10. **Audit log** — append-only audit of every mutation and denied
    attempt. *Support: 0/2 descriptive claims — no description in
    this group mentions audit. Included as a baseline hook on the
    **FedRAMP Low side of the crosswalk only** (AU-2/AU-3; see the
    precision note in the baseline section): CMMC L1 / FAR
    52.204-21 contains no audit practice, and none is claimed from
    it.*

## Long tail — Extended, by name

- **Adaptive learning / knowledge-gap remediation engine** — this
  group's own item. Amplifire's description states it in prose:
  "Patented algorithms detect and correct the knowledge gaps,
  doubts, and misconceptions that Amplifire has discovered in
  clinician's minds in every care setting." It is **not**
  taxonomy-tagged (the verbatim ai_automation pattern does not
  include "algorithms", and the taxonomy was not re-tuned), and it
  is specified here on that prose evidence, clearly labeled. A
  remediation engine is a vendor model over learner records, not
  substrate — the same honesty rule Group 13 applied to matching
  engines and Group 9 to learned inference.
- **Talent, skills & marketplace matching** (talent_skills,
  career_development, ai_automation families) — carried from the
  Group 13 union at 0 claims here, named so the category union is
  complete: best-fit matching, talent marketplaces, AI career
  assistants, career coaching/exploration services.
- **Recruiting, HCM/HRIS & workforce management suite**
  (recruitment_workforce, performance_management, policy_management)
  — carried at 0 claims here. (Amplifire's "workforce aligned" and
  "on-the-job performance" prose are recorded near-misses, not
  claims — `scratch/ARTIFACTS.md` items 4–5.)
- **Course content authoring & delivery, media streaming** —
  content_media carried at 0 claims here; authoring is 0/2 and
  streaming is 0/2 on broad checks in this group (as at L2). The
  delivery/playback engines are Extended; the AHA-guideline CPR
  curriculum and Amplifire's clinical content are vendor content,
  not substrate functions.
- **Simulation engines** (simulations) — carried at 0 claims here;
  simulation capture/debriefing/playback engines. (Neither L1
  sibling is the L2 group's simulation member; the family is named
  so the category union is complete.)
- **Remote proctoring & identity proofing** — 0 claims in either
  tier of this category; specified as a gap so the absence is a
  finding.
- **Deterministic scoring & AI grading** — scoring/grading wording
  0/2 here, 0/8 at L2. Both Extended; the Core holds assessment
  records only (decision at Core function 4).
- **General cloud hosting / PaaS** (hosting_platform, this group's
  only tagged family, 1/2) — RQI1Stop's multi-tenant public-cloud
  delivery. Hosting is a platform-layer property, never a learning
  function; the merged build is a single-tenant reference
  deployment and says so.
- **Collaboration & social learning** (collaboration_social) —
  carried at 0 claims here.
- **Data storage & processing services** (data_services) — carried
  at 0 claims here, beyond the substrate's own records.
- **Notifications & reminders** — 0 claims in either tier, despite
  being the natural companion of Core function 6 (due dates). Named
  as a gap: no sibling's description in either tier supports
  claiming a reminder engine.
- **Integrations & APIs** — 0 claims in either tier. The merged
  build's own API surface is its own design, not a union function.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored subset of it),
  cross-walked to the FAR 52.204-21 practices that define CMMC L1.
  Derivation per the Merge Rule: union of parent baselines = Low
  (the LI-SaaS subset adds nothing), highest parent tier = the Low
  family, so the merged baseline is Low in full. **No 800-171
  practices are claimed at this tier** — L1's basis is FAR
  52.204-21, and Group 13's Moderate ⇔ 800-171 framing is not
  imported.
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Course/catalog registry | CM-6, AU-2, SI-10 | Registry entries are explicit, configuration-controlled records, recorded when created; inputs are validated before any record exists; nothing is offered that is not registered |
| Enrollments & registrations | AC-2, AU-2 | Enrollment is an explicit, recorded account action binding a learner to a registry entry (FAR practice: limit system access to authorized users) |
| Learner progress & readiness records | AU-2 | Progress/readiness state is a recorded, reviewable record per learner, retained with the record set |
| Assessment records | AU-2, AU-3, SI-10 | Every administration leaves a record with content; inputs are validated before any record exists (records only — no score field exists) |
| Certificate/credential records | AU-2 | Credential status changes are recorded events on retained records (records only — no issuance claim) |
| Compliance assignments & status derivation | AU-2, CM-6 | Status is derived deterministically at read time from assignment, due date, and progress; the derivation runs over recorded facts only and is itself reviewable |
| Scheduling records | AU-2, CM-6 | Sessions are explicit records bound to registry entries and enrollments |
| Reporting over the records | AU-2 | Reports are computed views over recorded substrate facts only; no side-channel data |
| RBAC (admin/instructor/learner/auditor) | AC-2, AC-3, AC-5, AC-6, IA-2/IA-5 (hooks) | Role matrix enforced pre-mutation, with learner scope; separation of duties is carried as the AC-5 selection this baseline makes (admin alone holds catalog/credential/compliance writes). Identity and authenticator management stay with the embedding organization (FAR practices: limit access to authorized users and to the transactions/functions each user is permitted to execute; identify and authenticate users, processes, and devices) |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API |

- **Precision note (audit):** CMMC L1 / FAR 52.204-21 contains **no
  audit practice**. The audit log is carried because the FedRAMP Low
  baseline carries the AU family (AU-2/AU-3) — not because L1 asks
  for it. Group 13's additional Moderate citations for this function
  (AU-6, AU-9) are **not** carried at this tier.
- **Precision note (integrity):** no SI-7-style software/firmware
  integrity claim is made at this tier (SI-7 is a Moderate
  selection); input validation is cited as SI-10, which the build
  implements as reject-before-record on every write.
- **Not inherited downward:** Moderate/High apparatus — 800-171
  practice framing, AU-6/AU-9/CA-7/SI-12 traceability citations,
  hash-chained audit, logon lockout, 800-172 anything — is out of
  scope for a Low/L1 merge and is not claimed here. Session
  management is likewise not claimed: the service authenticates per
  request from headers and holds no session state.
- **Transport:** TLS applies when a certificate is configured
  (SC-8); the default serve mode is plain HTTP for local/demo use,
  stated plainly in the README.
- **Caveat, same as the crosswalk's:** FedRAMP authorizes PRODUCTS;
  CMMC certifies ORGANIZATIONS. A FedRAMP impact level is a
  statement about a cloud service offering; a CMMC level is a
  statement about a company and how it handles FCI/CUI. The L1 /
  FedRAMP Low equivalence used here is a **planning/matching
  equivalence only**: it says these forks sit at comparable
  assurance weight so they can be grouped and merged consistently.
  It does **not** claim that a FedRAMP-authorized product confers
  CMMC certification on anyone, that a CMMC-certified organization
  holds a FedRAMP authorization, or that either regime accepts the
  other as evidence. This traceability is a planning mapping; the
  merged build is not a FedRAMP authorization and confers no CMMC
  certification.

Standing platform notes (every group): demo identities are hooks,
not an IdP — IA-2 stays with the embedding organization; encryption
at rest is deployment-layer; TLS applies when a certificate is
configured. Multi-tenancy, this group's only tagged family, is
likewise a deployment property: the merged build is a single-tenant
reference deployment and says so.

## Implementation & reuse (stated explicitly)

- **Code:** Group 13's implementation (the `learn` package, our own
  Apache-2.0 code) is reused **in full and byte-identical** — all 7
  files under `src/learn/` match Group 13's SHA-256 hashes exactly
  (recorded in `scratch/src-sha256.txt`). The code is functionally
  tier-neutral: it contains no baseline or tier logic; only this
  spec, the traceability, and the README are written against the Low
  baseline and FAR 52.204-21. Two comments in `store.py` carry Group
  13's claim counts ("0/8") as the recorded origin of the
  records-only decisions for assessments and credentials; those
  decisions are restated on this group's own evidence (0/2) at Core
  functions 4–5 above, and the comments are left as lineage rather
  than rewritten, so the byte-identity claim stays exact.
- **Tests:** Group 13's suite inherited (65 tests). 13 of 15 test
  files differ from Group 13's by **documentation wording only**
  (group number, this group's claim counts in the trace headers, Low
  traceability tags); zero test logic changed — verified by diff.
  `tests/__init__.py` and `tests/test_main_cli.py` are byte-identical.
- **Verification in this tree:** 65/65 tests pass; the compliance
  status-derivation negative control was **mutation-verified fresh
  here** (the `_derive_status` overdue branch patched to return
  "current" → exactly 8 failures, the same failure set as Group 13's
  drill; store.py restored and SHA-256-verified identical to the
  pre-mutation copy); a live store + HTTP smoke passes (derived
  status current → overdue → completed; a learner's admin action
  denied at the store, 403 over HTTP, and the denial audited);
  dependency verification confirms Python stdlib only.

## Coverage statement (for this build)

- Forks spec'd: **2 / 2** (LI-SaaS 1, Low 1; each fork's actual
  impact level recorded in its sheet), each sheet carrying the full
  public description; 1 evidenced claim total, 1 zero-claim sheet.
- Taxonomy: Group 13's **21 function families**, applied verbatim;
  10 further candidate families checked with broad patterns and
  found at **0/2** (scoring, proctoring/identity, notifications,
  audit-in-text, API/integrations, streaming, authoring, due-date
  wording, completion/transcript wording, certification wording)
  and recorded as named absences rather than dropped silently.
- Core implemented: **10 / 10** functions (the Group 13 substrate,
  byte-identical code), each flagged claim-carried vs
  baseline-supported in the Core section above: in this group all 10
  are **carried, not claimed**, under the recorded core-boundary
  decision; RBAC and audit are additionally baseline hooks.
- Extended / gap list: 12 named items above, registered for the
  final gap batch (see README for the list by name).
