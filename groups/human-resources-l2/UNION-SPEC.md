# Union Spec — Human Resources, CMMC L2 (DeadRamp Phase 2, Group 21)

The merged functional spec for the Human Resources sibling group at
the L2 tier: **4 forks, all FedRAMP Moderate**, reconciled zero-diff
(`specs/specs.json` ↔ `forks.json` category "Human Resources" +
`cmmc_tier` "L2" ↔ MAP.md "Human Resources — L2 (4)").

The group: FedHire (Apply Government Solutions) · Avature Limited
(Avature Federal Platform) · Economic Systems Federal Human Resources
Navigator (Economic Systems) · Eightfold Talent Intelligence Platform
(TIP) (Eightfold AI Inc.).

This group has four distinct shapes and no single product they all
are: a federal hiring platform (FedHire — position classification,
vacancy announcements, applicant tracking, assessments, SME panels,
certificates, and onboarding, component by component), a configurable
HCM suite (Avature — a module list spanning applicant tracking, case
management, performance management, mobility, and learning, offered
no-code and in combination), a federal HR forms/cases and position-
repository platform (FedHR Navigator — forms and cases routed through
agency process, a PD+ position-management repository, a retirement
benefits calculator, and a broad supported-functions list), and an AI
talent-intelligence platform (Eightfold TIP — AI over the talent
lifecycle, sold as acquisition / management / flex / resource /
tracking / exchange modules). The center of gravity is **talent
acquisition**: it is the group's only 3/4 family, and the hiring chain
(classification → announcement → application → assessment → panel →
referral → onboarding) is FedHire's alone in detail. What the claim
counts below prove beyond that chain is a **records substrate**:
persons, positions, vacancies, and applications held as records;
human evaluations, lifecycle cases, performance cycles, benefits and
personnel cases recorded against them; and reports produced over
those records. The merged build implements that substrate; each
vendor's matching, classification-intelligence, scoring, calculator,
marketplace, and workflow engines on top of it are Extended
functions, named in the long tail.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split and
matched against a 25-family taxonomy defined from this category's
descriptions. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is
stored in `specs/specs.json` as evidence, so every claim is auditable.
**38 claims survived, with no pattern adjustments** — the fixed
phrase-based patterns produced exactly the expected counts, and the
borderline items were adjudicated as reviewed-and-kept (or correctly
never tagged), itemized below and in `scratch/ARTIFACTS.md`. **No fork
has zero claims.** Per-fork claim counts: FedHire 14, Economic Systems
Federal Human Resources Navigator 11, Avature Limited 7, Eightfold
Talent Intelligence Platform (TIP) 6. Counts are therefore a **floor**,
not a ceiling, on what these products do — the descriptions are
short and uneven (626–4,429 characters; only FedHire's is long, and
three of the four are essentially a paragraph plus a list), and no
conclusion about a real product's full depth should be drawn from
its tag count.

### Wording-artifact corrections (itemized; full text in `scratch/ARTIFACTS.md`)

1. **Avature generic line NOT tagged (no removal needed).** Avature's
   "identify, attract, hire, develop and retain talented people" line
   contains neither "talent acquisition" nor "applicant tracking," so
   the phrase-based patterns never tag it. Avature claims no
   talent_acquisition; its applicant_tracking claim rests on its
   explicit "Applicant Tracking" module name.
2. **Eightfold "Talent Tracking" NOT tagged applicant_tracking.**
   Talent-pool tracking inside an AI platform is not applicant
   tracking; the phrase pattern requires "applicant tracking" /
   "application management," which Eightfold does not contain.
3. **FedHire ai_automation KEPT with caveat.** No AI wording; the
   claim rests on "automates entrance-on-duty processing" —
   onboarding workflow automation. Eightfold is the group's AI
   claimant.
4. **FedHire access_control KEPT, thin.** Sole basis is inter-agency
   "granted access" for shared certificates of eligibles (1/4).
5. **Eightfold audit_compliance KEPT with caveat.** Rests on "meet
   compliance requirements," a compliance-outcome phrase, not audit
   tooling. FedHire carries the family's audit substance (panel
   records "for audit purposes," audit-enabled vacancies, Auditor /
   Analytics review modules).
6. **benefits_retirement — calculator vs. records separated.** Econ's
   first evidence names its retirement benefits *calculator*, an
   engine (Extended); the Core's benefits/retirement *records* rest
   on Econ's supported-functions list naming benefits and retirement.
7. **List sentences as evidence — house method, noted.** Econ's
   single supported-functions list sentence is the first-matching
   evidence for 6 of its 11 claims; Avature's module-list sentence
   likewise for 6 of its 7, and Eightfold's module-list sentence for
   4 of its 6. List-level claims are recorded at list-level weight.
8. **FedHire mega-sentence truncation — documented, not repaired.**
   FedHire's `<br><br>`-separated components merge into mega-sentences
   under the house splitter, so the 400-char-truncated stored evidence
   for 4 FedHire claims (applicant_tracking, reporting_analytics,
   access_control, ai_automation) ends before the matching token.
   Every claim verifies against the full sentence in
   `scratch/descriptions.txt` / `specs/specs.json`; the extractor was
   not special-cased.

Reviewed and **kept, with caveats**: Avature's talent_management rests
on its "Total Talent Management Framework" name; Eightfold's
workforce_planning on its "Resource Management" module name and its
talent_mobility on "Talent Flex" / "Workforce Exchange" module names —
module/name-level support, recorded at that weight. FedHire's
reporting claim is first matched via Position Classification "status
dashboards"; its broader reporting substance (classification data
tracked for reporting, Analytics/Auditor review) is what the Core's
reporting function rests on.

## Function ranking — all 4 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 3 | Talent acquisition | **Core** context — vacancy/application records (Core 3–4); acquisition engines Extended |
| 2 | 2 | Applicant tracking & application management | **Core** — application records & stage tracking (Core 4); workflow engines Extended |
| 2 | 2 | Position classification, descriptions & position management | **Core** — position & classification records (Core 2); recommendation intelligence Extended |
| 2 | 2 | Performance management | **Core** — performance review cycle records (Core 7); calibration/goal engines Extended |
| 2 | 2 | Personnel actions, forms & case management | **Core** — personnel action & case records (Core 9) |
| 2 | 2 | Talent management & talent lifecycle | Extended — suite depth (retention, workforce development) beyond records |
| 2 | 2 | Internal mobility & talent exchange | Extended — mobility / workforce-exchange marketplace engines |
| 2 | 2 | Workforce planning & resource management | Extended — planning analytics/models; position records carry the org-structure side |
| 2 | 2 | AI & workflow automation | Extended — AI matching and automation engines (see caveats 3) |
| 2 | 2 | Reporting, dashboards & analytics | **Core** — reporting over the records (Core 10); dashboard/visualization engines Extended |
| 2 | 2 | Audit & compliance review | **Core** — audit log (Core 12); compliance-review modules Extended (see caveat 5) |
| 2 | 2 | Integrations & external system connections | Extended — connector engines (USAJOBS, eOPF, NFC, IBC, HRIS sync) |
| 13 | 1 | Vacancy announcements & job postings | **Core** — vacancy announcement records (Core 3) |
| 13 | 1 | Job analysis & competency documentation | Extended — job-analysis & crediting-plan tooling feeding Core records |
| 13 | 1 | Hiring assessments & assessment strategies | **Core** — evaluation records (Core 5); delivery via providers Extended |
| 13 | 1 | SME panel review & rating records | **Core** — panel review records, human ratings verbatim (Core 5); scoring computation Extended |
| 13 | 1 | Candidate referral & certificates of eligibles | **Core** — the "referred" application stage (Core 4); assembled certificate documents Extended |
| 13 | 1 | New-hire onboarding & entrance-on-duty | **Core** — lifecycle case records with checklists (Core 6) |
| 13 | 1 | Benefits & retirement administration | **Core** — benefits & retirement records (Core 8), thin/flagged; calculator Extended |
| 13 | 1 | Separation & offboarding | **Core** — lifecycle case records, separation kind (Core 6) |
| 13 | 1 | Employee & labor relations | **Core** — as a personnel-case kind (Core 9) |
| 13 | 1 | Awards & recognition | **Core** — as a personnel-case kind (Core 9) |
| 13 | 1 | Career sites, campus recruiting & recruiting events | Extended — outreach sites, communities & events platforms |
| 13 | 1 | Employee learning & upskilling | Extended — learning delivery (also the Education group's domain) |
| 13 | 1 | Access control & granted access | **Core** — RBAC (Core 11), descriptive support thin: 1/4, flagged; baseline-carried |

**Named absences (0/4 each, checked with broad patterns — findings,
not oversights):** **leave & time-off** (`leave|time off|paid time
off|vacation`); **policy acknowledgements** (`polic|acknowledg` — no
description contains even the substring "polic"); **payroll**
(`payroll`); **background checks** (`background check|background
investigation`); **salary / compensation administration**
(`salary|compensation`); **time & attendance** (`time and
attendance|timesheet`). A human-resources group with no payroll, no
leave, no compensation, and no time-and-attendance wording in any
description is a hiring-and-records group, and the Core below is
specified accordingly — none of the six is smuggled in.

## The Core — what the merged build implements (12 functions)

The shared substrate the counts support, plus two baseline hooks
flagged where the counts are thin:

1. **Person records** — personnel anchor records keyed by an opaque
   caller-supplied `person_ref` ONLY (kind applicant/employee;
   lifecycle status applicant/active/separated). **Privacy: no name,
   SSN, DOB, salary, or any real-identifier field exists in any
   record shape, by design.** *Support flag: explicit "employee
   record" wording is thin — FedHire's "applicant record" (assessment
   results "returned to the applicant record") is the anchor phrase.
   Included as the anchor record every other claimed record binds
   to, and flagged as such; it is presupposed by every application,
   evaluation, case, and review record below.*
2. **Position & classification records** — position records (title,
   occupational series, grade, organization, status) and their
   classification state. *Support: position_classification 2/4
   (FedHire Position Classification; Econ's PD+ position management
   repository).*
3. **Vacancy announcement records** — announcement records bound to
   positions, with open/close dates and draft/posted/closed states.
   *Support: vacancy_announcements 1/4 (FedHire job opportunity
   announcements / JOAs).*
4. **Application records & stage tracking** — applications binding a
   `person_ref` to a vacancy, with stage (applied / screened /
   referred / selected / not_selected / withdrawn); the "referred"
   stage is where FedHire's candidate referral and certificates of
   eligibles live as records. *Support: applicant_tracking 2/4
   (FedHire, Avature), talent_acquisition 3/4 context (FedHire,
   Econ, Eightfold), referral_certificates 1/4 (FedHire). Matching /
   ranking engines are Extended.*
5. **Evaluation records** — hiring-assessment records and SME panel
   review records bound to applications; rater entries (`rater_ref`,
   numeric rating, comment) recorded verbatim. **No computed
   aggregate: there is deliberately no aggregate field.** FedHire's
   weighted cumulative / consensus scoring is an engine and is
   Extended; the substrate records human ratings only (the Education
   group's no-score-field precedent, adapted: human ratings are
   records, computation is not). *Support: hiring_assessments 1/4
   and panel_review 1/4 (both FedHire).*
6. **Lifecycle case records (onboarding & separation) with task
   checklists** — cases binding a `person_ref`, kind onboarding /
   separation, and tasks with states (pending / done / waived). Case
   status is **derived at read time** from task states (not_started /
   in_progress / complete; cancelled is an explicit recorded event
   flag) — **never stored**. *Support: onboarding 1/4 (FedHire
   entrance-on-duty), separation 1/4 (Econ).*
7. **Performance review cycle records** — review records binding a
   `person_ref` to a cycle/period with states (planned /
   in_progress / completed) and a recorded outcome label. *Support:
   performance_management 2/4 (Avature, Econ). The management
   suites' calibration/goal engines are Extended.*
8. **Benefits & retirement records** — benefits-enrollment records
   (plan_ref, state pending / active / closed) and retirement case
   records. *Support: benefits_retirement 1/4 (Econ), flagged thin:
   single claimant, list-level support for the records; the
   retirement benefits **calculator** is an engine, Extended.*
9. **Personnel action & case records** — case records (kinds:
   personnel_action, award, labor_relations, general) with routing
   states (opened / in_review / closed). *Support:
   personnel_actions_cases 2/4 (Econ forms-and-cases routing +
   personnel actions; Avature Case Management); awards_recognition
   1/4 and labor_relations 1/4 (both Econ) live here as case kinds.*
10. **Reporting over the records** — counts/summaries over the
    substrate records only. *Support: reporting_analytics 2/4
    (FedHire reporting/dashboards; Econ reporting & data
    visualization, incl. its DEIA reporting). Visualization /
    specialized-reporting engines are Extended.*
11. **RBAC** — admin / hr_specialist / employee / auditor roles,
    enforced before any state change; employee-role actors read only
    their own records (`person_ref` scope). *Support: access_control
    1/4 descriptive (FedHire "granted access") — thin, flagged —
    plus the L2 baseline requirement (AC/IA families, traceability
    below).*
12. **Append-only audit log** — every mutation and denied attempt.
    *Support: audit_compliance 2/4 — unusually claim-supported for a
    baseline hook: FedHire documents panel records "for audit
    purposes," runs audit-enabled vacancies, and ships Auditor /
    Analytics review modules (Eightfold's second claim is the
    compliance-outcome phrase, caveated above) — plus the AU
    baseline family.*

## Long tail — Extended, by name

- **AI talent intelligence & matching engines** (ai_automation
  engine side, 2/4) — Eightfold's AI matching over the talent
  lifecycle (the group's AI flagship), and FedHire's onboarding
  automation as a workflow engine. Models and automation are vendor
  engines over Core records; no AI function is in the Core.
- **Applicant-tracking workflow engines** — end-to-end hiring
  workflow automation and JOA posting/sync with external job boards.
  The application and announcement *records* are Core (functions
  3–4); the workflow and posting engines are not.
- **Position classification intelligence** — occupational-series &
  grade recommendation tools and classification-library comparison /
  suggestions (FedHire's guided builders and intelligent tools).
  Position and classification *records* are Core (function 2).
- **Job analysis & crediting-plan tooling** (job_analysis 1/4) —
  competency frameworks and assessment-strategy builders feeding the
  hiring workflow (FedHire Job Analysis, crediting plans).
- **Assessment delivery via third-party providers & assessment
  content/methodologies** (hiring_assessments 1/4) — FedHire's
  framework for delivering external, integrated applicant
  assessments and its methodology library. Evaluation *records* are
  Core (function 5); delivery and content are not.
- **Weighted cumulative & consensus scoring computation** —
  averaging, consensus-scoring, and weighted cumulative scores over
  panel ratings (FedHire Collaborate). Panel ratings are Core
  records; computing aggregates over them is an engine.
- **Certificates of eligibles as standalone assembled
  documents/artifacts** — assembled, annotated, and shared
  certificate documents (FedHire Selecting Official). The referral
  *stage* is Core (function 4); the document artifact is not.
- **Career sites, talent communities, campus recruiting & events
  platforms** (recruiting_outreach 1/4) — Avature's Career Sites &
  Talent Communities, Campus Recruiting, and Events Management.
- **Talent mobility & workforce-exchange marketplace engines**
  (talent_mobility 2/4) — Avature Internal Talent Mobility and
  Eightfold Talent Flex / Workforce Exchange as marketplaces.
- **Talent management suite depth** (talent_management 2/4 beyond
  records) — retention and workforce-development programs (Eightfold
  lifecycle optimization, Avature's Total Talent framework depth).
- **Workforce planning & resource-management analytics/models**
  (workforce_planning 2/4) — planning models and resource analytics
  (Econ, Eightfold Resource Management). Position records carry the
  org-structure side in the Core.
- **Retirement benefits calculator** (benefits_retirement engine
  side) — Econ's calculator. Benefits/retirement *records* are Core
  (function 8); computing benefit amounts is not.
- **Employee learning & upskilling delivery** (learning_upskilling
  1/4) — Avature Employee Social Learning/UpSkilling delivery; also
  the Education group's domain, not this substrate's.
- **Integration connector engines** (integrations 2/4) — USAJOBS,
  eOPF, NFC, IBC, and agency HRIS sync connectors (FedHire names the
  first four explicitly; Econ claims federal-system integrations
  generally). This build's own REST surface is its own design, not a
  union function.
- **Document & template assembly engines** — classification
  documents, onboarding form population, and agency-branded
  templates/documents (FedHire document workflows). The Core holds
  the records those documents are assembled from, not the assembly.
- **General cloud hosting / platform services** — platform-layer
  property of every sibling (all SaaS, Government Community Cloud);
  never an HR function. The merged build is a single-tenant
  reference deployment and says so.

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes no
tier (Merge Rules 1–2: union of baselines, highest tier wins — here
all parents already sit at the same tier).

| Core function | Control families | How the build answers |
|---|---|---|
| Person records | AC-2, AU-2, SI-12 | Anchor records keyed only by opaque `person_ref`; no real-identifier field exists in any record shape; lifecycle changes are auditable events |
| Position & classification records | CM-6, SI-12 | Positions and their classification state are explicit, configuration-controlled records, retained with the record set |
| Vacancy announcement records | AU-2, CM-6 | Announcements are explicit records bound to positions, with recorded open/close dates and state changes |
| Application records & stage tracking | AC-2, AU-2, SI-10 | Every application and stage transition is an explicit, auditable record binding a `person_ref` to a vacancy; inputs validated before any record exists |
| Evaluation records | AU-2, AU-3, SI-10 | Rater entries are recorded verbatim with content; no aggregate is computed, so no derived value needs validation or explanation |
| Lifecycle case records (onboarding & separation) | AU-2, AU-6, CM-6 | Case status is derived deterministically at read time from recorded task states; derivation is queryable and reviewable, never stored |
| Performance review cycle records | AU-6, SI-12 | Cycle state and outcome labels are reviewable records per person and period, retained with the record set |
| Benefits & retirement records | AU-2, SI-12 | Enrollment state and retirement cases are auditable records; no benefit amount is computed by the substrate |
| Personnel action & case records | AC-3, AU-2 | Cases are explicit records with recorded kind and routing state; routing-state changes are auditable events |
| Reporting over the records | AU-6, CA-7 | Reports read the substrate records only; no side-channel data |
| RBAC (admin/hr_specialist/employee/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation, with employee actors scoped to their own `person_ref`; identity itself is supplied by the embedding organization (see caveat) |
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
configured. The merged build is a single-tenant reference deployment
and says so.

## Coverage statement (for this spec batch)

- Forks spec'd: **4 / 4**, each with evidenced claims (38 total).
- Taxonomy: **25 function families**, defined from this category's
  descriptions; 6 further families checked and found at **0/4**
  (leave & time-off, policy acknowledgements, payroll, background
  checks, salary/compensation administration, time & attendance)
  and recorded as named absences rather than dropped silently.
- Core specified: **12 functions** (10 claim-supported, 1
  claim-supported with thin descriptive support plus baseline —
  RBAC, 1 claim-supported and baseline — audit log; the person-
  record anchor is flagged for thin explicit wording), each flagged
  as such.
- Extended / gap list: 16 named items above. No implementation code
  in this batch — specs and union spec only.
