# Union Spec — Human Resources, CMMC L1 (DeadRamp Phase 2 remainder, Human Resources L1 singleton)

The singleton spec for the Human Resources category at the L1
tier: **1 fork, FedRAMP LI-SaaS** — **QGenda** (Qgenda, LLC),
FedRAMP Certified, SaaS, Public Cloud. Built under the remainder
census unit `new-singleton:Human Resources|L1`.

**Membership provenance, stated plainly:** `forks.json` files
this fork "Uncategorized (none in source)" at tier L1 — its
source record carries an empty `business_categories` list and an
empty business-function segment in `filter_classes`. The
DeadRamp category is the **remainder census proposal**, taken
from the fork's own description (census classifier note:
"Workforce call/scheduling automation for healthcare
organizations."). Reconciliation: `remainder.json` unit ==
`specs/specs.json` == {FR1924942935}, zero diff, and the fork's
own recorded fields (LI-SaaS, FedRAMP Certified, L1) match the
source record exactly. MAP.md's category arithmetic is
unaffected: this fork was never in MAP.md's Human Resources
count, because MAP.md counts the Phase 1 category field.

## Lineage: a cross-tier carry, downward (the Merge Rule applied across tiers)

This build does not start from zero. Its parent is the **Group
21 merged build** (`../human-resources-l2/`) — the union of the
4 Human Resources L2 (FedRAMP Moderate) forks, a working
clean-room HR records service (12 core functions), whose taxonomy
and substrate this category uses at every tier built so far.
(Group 21 was later enlarged to 7 forks by a remainder addition;
this singleton's lineage is the original Group 21 union — its
taxonomy, claim tables, and core are the originals, reproduced
and verified as recorded below. The addition's three forks are
L2 facts and play no part here.)

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents (Rule 1) — the category
substrate is carried whole, not stripped because one fork's
marketing prose is thin (a wording floor is not a downgrade).
The tier, however, is this fork's own: **LI-SaaS / L1**, the
lightest tier, and the baseline below is written **fresh for
Low** (Rule 2 satisfied at the merged tier, which here is L1).
Rule 3 traceability is this document plus the spec sheet; Rule
4's SSDF-shaped process is the provenance here, the review
recorded in `scratch/ARTIFACTS.md`, and the verification record
in `tests/README.md` (full suite run by the builder; the
signature negative control mutation-verified live in this tree).

**What does NOT carry down, stated once:** Group 21's Moderate /
NIST SP 800-171 baseline citations stay in Group 21. This
category has no tier above L2, so there are no High uplifts in
its lineage to inherit or refuse. The implementation needs no
downward modification at all: all 7 `src/` modules are
byte-identical to Group 21's (hash record in
`scratch/reuse-note.md`), because the L2 build carries no
Moderate-specific machinery in code — its baseline lives in its
spec documents, not in the implementation. The four-role matrix
(admin / hr_specialist / employee / auditor) is part of that
carried code as shipped at L2; it is substrate, not an uplift,
and the carry rule does not edit the substrate.

## How functions were counted

Group 21's 25-family taxonomy was applied **verbatim** — parsed
via `ast` out of Group 21's shipped `scratch/extract.py` (never
executed, never re-typed — that file is the original extractor,
unchanged since the original ship; the group's additions
extractor parses the same literal out of the same file). Before
the newcomer was tagged, the extractor reproduced Group 21's
**original** four shipped claim tables exactly from the raw
cache (FedHire 14, Economic Systems 11, Avature 7, Eightfold 6 —
38 claims, function ids and evidence strings), and asserted the
reproduction equal to both the git-HEAD snapshot of the original
ship (`scratch/original_specs.json`, commit 0a14d91) and the
corresponding sheets of the group's current enlarged specs. A
family is claimed only when the fork's own description contains
matching text; the first matching sentence is stored in
`specs/specs.json` as evidence. Source: GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json` (produced by the General
Services Administration, last change 2026-10-22).

**Result: 1 claim.** `ai_automation`, on sentence 1: "QGenda is
the leader in cloud-based call and scheduling automation
(https://www.qgenda.com/customers/federal/)." The basis is
recorded at its exact weight (full record in
`scratch/ARTIFACTS.md`): the sentence asserts **scheduling
automation**; the description contains no AI wording at all (no
standalone "AI", no "artificial intelligence"). The claim stands
on the `automat\w+` branch at automation weight — the same basis
as two kept claims at L2 (FedHire's "automates
entrance-on-duty processing", GDC's "automates the creation …
of organizational charts") — and the family's disposition in
this category is Extended, and it stays Extended: this build
implements no AI function and no automation engine. Raw hits
equal claims (1 = 1); nothing was removed before matching — the
source record's `certified_services` is empty (asserted) and
the description contains no scope-exclusion segment.

**The fork's headline function has no family.** Workforce
call/scheduling — the whole of what the description says the
product does, for physician groups, hospitals, academic medical
centers, and enterprise health systems — matches none of the 25
families, which were defined from the L2 descriptions and
contain no scheduling family. It is named in the gaps below,
not forced into a neighbouring family (the Perceptyx precedent
at L2: a whole function with no family is a gap, recorded, not
a claim).

**Census citation accounting:** the census recorded two
citations for this fork — the description's two sentences. Both
verify as strict verbatim substrings. Citation 1 **is** the
claim's evidence sentence and tags `ai_automation`; citation 2
verifies and tags **no** family. Verification is not a claim,
in either direction; both facts are pinned in
`tests/test_singleton_spec.py` and `scratch/citation_check.json`.

## Function ranking — the singleton

Dispositions are Group 21's union dispositions, carried with the
taxonomy; the claim count column is this fork only (of 1).

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | AI & workflow automation | **Extended** — claimed on the recorded basis ("scheduling automation"); no AI asserted, no automation engine built |
| 2 | 0 | Talent acquisition | **Core** context — carried, not claimed |
| 2 | 0 | Applicant tracking & application management | **Core** (records) — carried, not claimed |
| 2 | 0 | Vacancy announcements & job postings | **Core** (records) — carried, not claimed |
| 2 | 0 | Position classification, descriptions & position management | **Core** (records) — carried, not claimed |
| 2 | 0 | Job analysis & competency documentation | Extended — carried as a named gap, not claimed |
| 2 | 0 | Hiring assessments & assessment strategies | **Core** (records) — carried, not claimed |
| 2 | 0 | SME panel review & rating records | **Core** (records) — carried, not claimed |
| 2 | 0 | Candidate referral & certificates of eligibles | **Core** (stage) — carried, not claimed |
| 2 | 0 | New-hire onboarding & entrance-on-duty | **Core** (records) — carried, not claimed |
| 2 | 0 | Performance management | **Core** (records) — carried, not claimed |
| 2 | 0 | Benefits & retirement administration | **Core** (records) — carried, not claimed |
| 2 | 0 | Personnel actions, forms & case management | **Core** (records) — carried, not claimed |
| 2 | 0 | Separation & offboarding | **Core** (records) — carried, not claimed |
| 2 | 0 | Employee & labor relations | **Core** (case kind) — carried, not claimed |
| 2 | 0 | Awards & recognition | **Core** (case kind) — carried, not claimed |
| 2 | 0 | Workforce planning & resource management | Extended — 0 claims here; the fork's "optimize their workforce" is a recorded near-miss (ARTIFACTS.md), not this family's phrase |
| 2 | 0 | Talent management & talent lifecycle | Extended — carried as a named gap, not claimed |
| 2 | 0 | Internal mobility & talent exchange | Extended — carried as a named gap, not claimed |
| 2 | 0 | Career sites, campus recruiting & recruiting events | Extended — carried as a named gap, not claimed |
| 2 | 0 | Employee learning & upskilling | Extended — carried as a named gap, not claimed |
| 2 | 0 | Reporting, dashboards & analytics | **Core** (over the records) — carried, not claimed |
| 2 | 0 | Audit & compliance review | **Core** (audit log) — carried, not claimed |
| 2 | 0 | Integrations & external system connections | Extended — carried as a named gap, not claimed |
| 2 | 0 | Access control & granted access | **Core** (baseline substrate) — carried, not claimed |

Plus this singleton's own engine, named from its description's
own words (Extended, detailed in Gaps below): the **workforce
scheduling & call-scheduling engine** itself — the fork's
headline function, for which the category taxonomy has no
family.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35/38/40/56 precedent).** This fork's single claim is
an Extended family, so **no core function below is
claim-supported for this fork**, yet all 12 core functions stand
in this build. The reasoning is the Merge Rule itself: the
category substrate is the union this fork's category
presupposes, carried whole at the fork's own tier. The
presupposition is read at the level of the product's operation
and stated here as *interpretation, not evidence*: a
workforce-scheduling platform operating over a healthcare
organization's staff presupposes the staff as its object model
(→ person records), the roles and posts being staffed (→
position records), entrance-on-duty work before a member's
first scheduled shift (→ lifecycle cases), standing personnel
administration around the roster (→ performance cycles,
benefits records, personnel cases), and review over all of it
(→ reporting, RBAC, audit); the hiring-chain records
(vacancies, applications, evaluations) are the category
substrate this tier would otherwise lack entirely. Each step is
a substrate function from Group 21's core; none of them is this
product's engine — its engine is scheduling, and scheduling is
Extended. The alternative — building nothing at L1, or building
only an "automation" stub around the one claim — was considered
and rejected: the category's L1 tier would carry no substrate
while its L2 tier carries it, and a stub around an Extended
family would invert the core/extended boundary. The price of
carrying the substrate is this disclosure and the coverage
statement's wording: **core carried, not claimed, for this
fork.** That price is paid in full, in both places.

**Named absences — all six stand at this tier.** Group 21 named
six absences at 0/4 (leave & time-off, policy acknowledgements,
payroll, background checks, salary/compensation administration,
time & attendance); its L2 remainder addition retired two of
them (leave & time-off, time & attendance) on GDC's own words.
Each absence was re-probed against THIS fork's description
(probe output in `scratch/absence_probes.json`, pins in tests):

- **Leave & time-off — stands.** Probe
  (`leave|time off|paid time off|vacation`): 0 hits. The L2
  retirement rested on Paycheck 8's own leave wording; this
  fork's text contains none, so the retirement does not carry
  to this tier.
- **Time & attendance — stands.** Literal probe
  (`time and attendance|timesheet`): 0 hits, and the substance
  probe finds no attendance wording at all (no "attendance",
  no "timesheet", no "time tracking"). GDC retired this absence
  at L2 because its prose asserted time and attendance
  tracking; this fork's substance is *scheduling* — deciding
  who works when, in advance — a different function, recorded
  under its own gap name rather than used to retire this
  absence.
- **Policy acknowledgements — stands** (`polic|acknowledg`: 0).
- **Payroll — stands** (`payroll`: 0; the word does not appear
  even as an external-system reference here).
- **Background checks — stands** (0).
- **Salary / compensation administration — stands**
  (`salary|compensation`: 0).

They are recorded so the union is complete and the absence is
provable from the record; they are not built and they are not
gaps, because nothing was claimed (the Group 21 precedent). If
a future sibling in this category claims them at this tier,
they enter through its spec.

## The Core — what the build implements (12 functions, carried at the L1 baseline)

The same 12 functions as Group 21, carried whole:

1. **Person records** — personnel anchor records (`per-`) keyed
   by an opaque caller-supplied `person_ref` ONLY (kind
   applicant/employee; lifecycle status applicant/active/
   separated). **Privacy: no name, SSN, DOB, salary, or any
   real-identifier field exists in any record shape, by
   design.** Carried, not claimed.
2. **Position & classification records** — position records
   (`pos-`) with title, occupational series, grade,
   organization, and status (vacant/filled/abolished).
   Carried, not claimed.
3. **Vacancy announcement records** — announcements (`vac-`)
   bound to positions, with open/close dates and states
   (draft/posted/closed). Carried, not claimed.
4. **Application records & stage tracking** — applications
   (`app-`) binding a `person_ref` to a vacancy, with stage
   (applied/screened/referred/selected/not_selected/withdrawn);
   a duplicate active application is rejected. Carried, not
   claimed.
5. **Evaluation records** — hiring-assessment and SME panel
   review records (`evl-`) bound to applications; rater entries
   (`rater_ref`, numeric rating, comment) recorded verbatim.
   **No computed aggregate exists.** Carried, not claimed.
6. **Lifecycle case records (onboarding & separation) with
   task checklists** — cases (`lif-`) binding a `person_ref`,
   kind onboarding/separation, tasks with states
   (pending/done/waived). Case status is **derived at read
   time** from task states (not_started/in_progress/complete;
   cancelled is an explicit recorded event flag) — **never
   stored**. Carried, not claimed.
7. **Performance review cycle records** — review records
   (`rev-`) binding a `person_ref` to a cycle/period with
   states (planned/in_progress/completed) and a recorded
   outcome label. Carried, not claimed.
8. **Benefits & retirement records** — benefits-enrollment
   records and retirement case records (`ben-`) with an opaque
   `plan_ref` and state (pending/active/closed). Carried, not
   claimed.
9. **Personnel action & case records** — case records (`cas-`)
   with kinds (personnel_action/award/labor_relations/general)
   and routing states (opened/in_review/closed). Carried, not
   claimed.
10. **Reporting over the records** — counts/summaries over the
    substrate records only. Carried, not claimed.
11. **RBAC** — admin/hr_specialist/employee/auditor roles,
    enforced before any state change; employee-role actors read
    only their own records (`person_ref` scope). Baseline
    substrate, carried not claimed.
12. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp; optional JSONL persistence; no mutation API.
    Baseline substrate, carried not claimed.

**Privacy discipline (hard rule, inherited).** Person records
are keyed by opaque caller-supplied references only. No entity
in this build has a field that can hold a real name, SSN, date
of birth, salary or compensation figure, address, phone number,
or email address — the shapes are enforced by tests
(`tests/test_privacy.py`). For this fork the rule bites in a
specific place: a scheduling platform's real records are
rosters of named clinicians with their shifts; this substrate
holds **neither names nor schedules** — it holds person and
position records keyed by opaque references, and the schedule
itself is the fork's Extended engine, not built here.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Singleton tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this
  fork's impact level) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline.
  LI-SaaS is FedRAMP's tailored **subset** of that baseline for
  SaaS offerings, so the union baseline is the Low baseline
  itself, cross-walked to the FAR 52.204-21 basic-safeguarding
  practices that define CMMC L1. One fork at one tier plus the
  carried substrate, so no merge changes the tier (Merge Rules
  1 and 2 recorded as taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Person records | AC-3, CM-6, SI-10; IA-2 (hooks) | Anchor records keyed only by opaque `person_ref`; no real-identifier field exists in any record shape; identity itself is supplied by the embedding organization |
| Position & classification records | CM-6, SI-10 | Positions and their classification state are explicit, validated registry records |
| Vacancy announcement records | AU-2, AU-3 (Low side), CM-6 | Announcements are explicit records bound to positions, with recorded dates and state changes |
| Application records & stage tracking | AC-3, AU-2, AU-3 (Low side), SI-10 | Every application and stage transition is an explicit, auditable record; inputs validated before any record exists |
| Evaluation records | AU-2, AU-3 (Low side), SI-10 | Rater entries recorded verbatim with content; no aggregate is computed, so no derived value needs validation or explanation |
| Lifecycle case records | CM-6, AU-2, AU-3 (Low side) | Case status is derived deterministically at read time from recorded task states — reproducible from the records and the trail, never stored |
| Performance review cycle records | AU-2, AU-3 (Low side), CM-6 | Cycle state and outcome labels are reviewable records per person and period |
| Benefits & retirement records | AU-2, AU-3 (Low side) | Enrollment state and retirement cases are auditable records; no benefit amount is computed by the substrate |
| Personnel action & case records | AC-3, AU-2, AU-3 (Low side) | Cases are explicit records with recorded kind and routing state; routing changes are auditable events |
| Reporting over the records | AU-2, AU-3 (Low side) | Reports read the substrate records only; counts only, no side-channel data |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Four-role matrix enforced pre-mutation at two layers, with employee scope by `person_ref`; `audit_read` gating traced to AC-3 — see precision notes |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing
  is silently imported from the sibling tier's table):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and
    its LI-SaaS tailoring) carries the AU family — Group 21's
    AU-9 (protection of audit information) citation is a
    Moderate selection and is **not** claimed here; AU-2/AU-3
    only. Group 21's AU-6 citations (lifecycle, performance,
    reporting rows) are likewise Moderate selections and are
    not claimed here.
  - **Separation of duties / least privilege:** the four-role
    matrix and its admin/auditor gating are design properties
    of the carried substrate. Their Moderate-table family homes
    in Group 21's spec were AC-5/AC-6, which are **not**
    Low-baseline selections, so at this tier the gating is
    traced to AC-3 access enforcement, with AC-5/AC-6 named as
    lineage only.
  - **What else does not carry down:** Group 21's CA-7
    citations (lifecycle derivation and reporting rows) and
    SI-12 citations (person, position, performance, benefits
    rows) are not Low-baseline selections and are not claimed
    here; retention is a property of the record set as held,
    not a control claimed at this tier.
- **Caveat (standing, from crosswalk.md):** this traceability
  is a planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence,
  and any real compliance claim still has to be earned inside
  each regime separately.

## Implementation contract (summary)

Identical to Group 21's — `src/hr/` (Python stdlib only):
`errors` (`HrError`, `ValidationError`, `NotFoundError`,
`PermissionDenied`), `access` (User, admin/hr_specialist/
employee/auditor matrix), `audit` (append-only AuditLog),
`store` (HrStore: the 12 core functions; failed operations
consume no ids; permission checks precede mutation; the
lifecycle derivation lives in the single method
`_derive_case_status`), `service` (HTTP layer, demo registry
alice=admin / bob=hr_specialist / carol=employee /
dana=auditor), `__main__` (`python -m hr serve`). All 7 modules
byte-identical to Group 21's (hash record in
`scratch/reuse-note.md`). `tests/`: see tests/README.md for the
test count and the negative-control record (the count is filled
in from the build, not stated here).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (QGenda, LI-SaaS, its actual impact
  level recorded in the spec sheet; category by
  remainder-census proposal, provenance recorded).
- Claims evidenced for the fork: **1** of 25 families —
  `ai_automation`, Extended, on the recorded basis ("scheduling
  automation"; no AI asserted); no core function is
  claim-supported for this fork. The fork's headline function
  (workforce scheduling) has no taxonomy family and is recorded
  as a gap.
- Core implemented: **12 / 12** functions above — **carried as
  the category substrate under the core-boundary decision, not
  claimed as this fork's evidenced functions.** The distinction
  is the coverage statement, not a footnote to it.
- Tests: **91 run, 91 passed**, including the mutation-verified
  negative control performed against this group's tree
  (tests/README.md).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engine (Extended; named from its
description's own words — the product's actual surface, none of
it built here):

- **Workforce scheduling & call-scheduling engine**: building,
  optimizing, and maintaining staff schedules and call rosters
  for healthcare organizations (physician groups, hospitals,
  academic medical centers, enterprise health systems) —
  schedule construction, coverage optimization, call rotation,
  and the automation the fork's one claim names. The category
  taxonomy has no scheduling family; this is the fork's whole
  function, recorded here so the registry names it. The
  automation engines behind the claimed `ai_automation` family
  (Extended at every tier of this category) are this engine's
  machinery, not a separate build item.

Extended families carried from the Group 21 union, not
implemented (the union's long tail, by name):

- AI talent intelligence & matching engines.
- Applicant-tracking workflow engines.
- Position classification intelligence.
- Job analysis & crediting-plan tooling.
- Assessment delivery via third-party providers & assessment
  content/methodologies.
- Weighted cumulative & consensus scoring computation.
- Certificates of eligibles as standalone assembled
  documents/artifacts.
- Career sites, talent communities, campus recruiting & events
  platforms.
- Talent mobility & workforce-exchange marketplace engines.
- Talent management suite depth.
- Workforce planning & resource-management analytics/models.
- Retirement benefits calculator.
- Employee learning & upskilling delivery.
- Integration connector engines (USAJOBS, eOPF, NFC, IBC,
  agency HRIS sync).
- Document & template assembly engines.
- General cloud hosting / platform services.

Platform layer (gap-listed, never implied closed): multi-tenancy
(the build is a single-tenant reference deployment); encryption
at rest (deployment layer); TLS only when a certificate is
configured; demo identities are hooks, not an IdP — IA-2 stays
with the embedding organization. The hosting/delivery platform
is the deployment layer itself, not a function of this build.

**Privacy note:** this build stores records and opaque
caller-supplied references only — no real names, SSNs, dates of
birth, salary figures, addresses, phone numbers, or email
addresses exist in any entity shape, and evaluation entries are
stored verbatim, never aggregated.
