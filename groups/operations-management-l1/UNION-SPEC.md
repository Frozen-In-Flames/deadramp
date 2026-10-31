# Union Spec — Operations Management, CMMC L1 singleton (DeadRamp Phase 2, Group 52)

The functional spec for the **Operations Management L1 singleton**: a
sibling group of **one fork** — **OpenWater** (OpenWater Software
LLC), SaaS, Public Cloud deployment, FedRAMP **LI-SaaS**, FedRAMP
Certified (FedRAMP ID FR2113346550). Per PIPELINE.md, singletons
build after the sibling groups with the same pipeline at group size
one: this spec is the one fork's claims under the category taxonomy,
and the build is the category substrate those claims presuppose, at
this fork's own tier.

**Reconciliation (zero diffs).** `forks.json` carries exactly one
Operations Management / L1 entry (the fork above; its registry fields
match the raw marketplace record field for field). MAP.md's sibling
sections list only groups of 2+, so the reconciliation runs through
`forks.json` exactness plus MAP.md's category arithmetic: the
category total is **15** = L2 **2** + L1 **1** + untiered **12**
(tiered = 3 = L2 2 + L1 1). Zero diffs.

The fork's source record carries
`business_categories: ['Operations Management']`, preserved in the
spec sheet (in the string form used by Group 36's sheets), as is its
source service model `['SaaS']`.

## Singleton character — read this first

**This fork is not an operations-work platform of the kind the
category taxonomy was defined from.** It is a submission and review
platform: organizations use it to run awards, abstracts and
call-for-papers, grants, scholarships, fellowships, accreditation,
and competition programs, and its FedRAMP certification covers its
**Submission Management** and **Review & Evaluation** services only.
The category taxonomy (Group 36's, below) was defined from the L2
group's two descriptions — an internal cloud management/compliance
console and a configurable operational-work platform — and this
fork's vocabulary intersects it almost nowhere: the verbatim
taxonomy yields exactly **one raw hit**, and that hit is removed
under the recorded ruling below. **Final claims: 0 of 19 families.**
The taxonomy was not re-tuned.

The spec therefore treats the fork the way the recorded precedents
treat it:

- The fork's own engines — submission management and review &
  evaluation — are **Extended gaps**, named from the listing's own
  certified-service names. Nothing in the build performs them.
- The **operations records substrate** the category established at
  L2 is carried in full at L1 under an explicit core-boundary
  decision (below). A singleton inherits its category's substrate at
  its own tier rather than re-deriving a lesser one, and a wording
  artifact is not a downgrade.

## How functions were counted

The fixed **19-family taxonomy from Group 36** (Operations
Management L2) was applied **unchanged** — ids, labels, and matchers
verified identical against Group 36's extractor programmatically
(`scratch/extract.py` execs Group 36's source up to its `COMPILED`
line and asserts the two TAXONOMY lists are equal). A family is
claimed only when the fork's own public description contains
matching text; the first matching sentence would be stored in
`specs/specs.json` as evidence. Group 36's scoping decisions are
inherited with the taxonomy and were not re-opened.

**1 raw hit, 1 removal, 0 claims survive.** The sole raw hit is
`integrations` (`\bintegrations\b`) in sentence 4. **Ruling
(applied, recorded, not re-litigated):** sentence 4 is a
scope-exclusion sentence — it names third-party integrations among
capabilities the listing itself places **outside** the FedRAMP
Minimum Assessment Scope. Per the category discipline (Group 36's
MCSS boundary-disclaimer precedent; Group 41's excluded-catalogue
precedent), that hit is **removed** as a wording artifact with the
reason stated — in the extractor's artifact log data, in
`scratch/ARTIFACTS.md` item (g), and here — and third-party
integrations is named as an out-of-scope Extended gap instead.
Counts are a **floor**, not a ceiling. Near-misses are itemized in
`scratch/ARTIFACTS.md`; the taxonomy was **not** re-tuned to capture
them. Every stored evidence string was asserted programmatically to
be a verbatim substring of its description (vacuous at 0 claims; the
assertion code is kept, and the removed hit's evidence was asserted
verbatim before it was discarded).

## Function ranking — the singleton fork under the category taxonomy

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Program & project operations | 0 claims — near-miss noted (S1 program vocabulary; ARTIFACTS.md (a)); project/program records carried as substrate |
| 1 | 0 | Operational data & structured records | 0 claims — absent; the records substrate itself is carried |
| 1 | 0 | Workflow automation | 0 claims — near-miss noted (S4 "automated communications" is not "automation", and is out-of-scope anyway; ARTIFACTS.md (e)); workflow registry carried as substrate, execution Extended at L2 |
| 1 | 0 | Reporting & operational intelligence | 0 claims — near-miss noted (S4 "reporting" matches no intelligence phrase, and is out-of-scope anyway; ARTIFACTS.md (f)); registry reports carried as substrate |
| 1 | 0 | Asset & equipment management | 0 claims — absent; asset records carried as substrate |
| 1 | 0 | Inspections & field operations | 0 claims — near-miss noted (S2's review surface is not "inspections", and no scoring family exists; ARTIFACTS.md (c)); inspection records (verbatim outcomes only) carried as substrate |
| 1 | 0 | Workforce & mission readiness | 0 claims — absent; directory records carried as substrate |
| 1 | 0 | Safety & compliance management | 0 claims — absent |
| 1 | 0 | Governance & compliance functions | 0 claims — absent |
| 1 | 0 | Authorization & access services | 0 claims — absent; RBAC carried as Low-baseline hooks; an authorization service / IdP is Extended at L2 |
| 1 | 0 | Common security services | 0 claims — absent; audit/RBAC hooks carried as substrate; the enforcement plane is Extended at L2 |
| 1 | 0 | Network connectivity & platform services | 0 claims — absent; Extended (platform layer) at L2 |
| 1 | 0 | Usage information & metering | 0 claims — absent; usage records carried as substrate |
| 1 | 0 | Policy enforcement | 0 claims — absent; workflow/policy registry carried as substrate; the enforcement plane is Extended at L2 |
| 1 | 0 | Application configuration & deployment | 0 claims — absent (S2's form builder matches no family; ARTIFACTS.md (d)); the low-code builder/deployment engine is Extended at L2, and this fork's form builder is part of its Submission management gap |
| 1 | 0 | Mobile capabilities | 0 claims — absent; Extended at L2 |
| 1 | 0 | Integrations & interoperability | 0 claims — **1 raw hit REMOVED** (S4 scope-exclusion sentence; see counting note above and ARTIFACTS.md (g)); named as an out-of-scope Extended gap instead |
| 1 | 0 | AI capability | 0 claims — absent; Extended at L2 |
| 1 | 0 | Contractor & vendor management | 0 claims — absent; organization directory records carried as substrate |

**The fork's excess over the substrate** (functions its description
asserts that no taxonomy family names, because the category taxonomy
was defined from the L2 group's descriptions): the two certified
services — **Submission Management** and **Review & Evaluation** —
and the seven capabilities the listing names only to place them
outside the FedRAMP Minimum Assessment Scope: **automated
communications**, **reporting**, **program website builder**,
**galleries**, **conference session scheduling**, **payments**, and
**third-party integrations**. All are specified as Extended gaps
below — named, not forced into families.

**Named absences carried from the category record:**
**scheduling/rostering is claimed by 0 forks** at L2 — this fork
names conference session scheduling only as an out-of-scope
capability, so the absence stands at this tier too; and
**IoT/telematics data collection is claimed by 0 forks everywhere**
in the category. Neither is built or implied.

## The Core — what the build implements (12 functions)

The same operations records substrate the category's L2 merged build
implements (full contract in Group 36's UNION-SPEC.md, which this
build's `src/` implements unchanged):

1. **Directory** — person records (`per-`) and organization records
   (`org-`) with opaque reference strings and free-form attributes.
   No real personal identifiers are required by any record shape.
2. **Projects** — project/program records (`proj-`) with an optional
   owning organization and member persons (duplicate membership is a
   validation error).
3. **Assets** — asset/equipment records (`ast-`) with kind, optional
   project link, attributes, and a status lifecycle
   `in_service → in_maintenance → in_service`,
   `in_service → retired`, `in_maintenance → retired`; `retired` is
   terminal.
4. **Work orders** — work records (`wo-`), type-tagged
   (inspection/maintenance/field_operation/task/general), with the
   house lifecycle, assignment to a person and/or a project, an
   optional asset link, priority, and an optional `due_at`. Overdue
   is **derived at read time, never stored**:
   `overdue = now > due_at and status not in (completed, closed, cancelled)`.
5. **Inspections** — inspection records (`insp-`) against an asset
   and/or a work order, with an inspector person link, a summary, and
   an outcome recorded verbatim (`pass` / `fail` / `follow_up` /
   `not_recorded` default). Immutable once written; no score is
   computed from outcomes anywhere.
6. **Usage records** — usage/metering records (`use-`): a project or
   service reference, a metric name, an integer quantity, and a
   period string. Immutable once written.
7. **Workflow registry** — workflow definition records (`wf-`):
   name, work-type scope, trigger text, action text, enabled flag,
   versioned on update (full version history retained). Registry
   only; the workflow **execution** engine is Extended.
8. **Reports** — deterministic summaries: work orders by
   status/type/project plus overdue count at the report's `now`,
   assets by status, inspections by outcome, usage totals by metric.
9. **Search** — literal case-insensitive substring search over
   people/organizations, projects, work orders, assets, and
   inspections.
10. **REST API** — the full surface over HTTP, with the house auth
    convention (X-User/X-Role against a demo registry; 401
    unknown/mismatched, 403 permission, denied attempts audited).
11. **Access control (RBAC)** — admin/operator/viewer matrix enforced
    in the store before any mutation or id allocation, and again at
    the service layer.
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation and every denied attempt (`<action>:denied`).

**Core-boundary decision (explicit).** **0 functions are
claim-anchored** in this group; all 12 are **carried, not claimed**:
they stand because (a) the category union at L2 established this
substrate as the Operations Management core and a singleton inherits
its category's substrate at its own tier, and (b) the fork's prose
presupposes records-keeping of exactly this kind (programs,
administrators/reviewers/judges as directory persons, dated work).

**The sharper boundary, stated plainly.** The fork's actual surface
is submission management and review & evaluation; this substrate is
**NOT a substitute for it**, and nothing in the build performs or
claims judging/scoring — substrate inspection records hold verbatim
outcomes only.

**Reuse, stated explicitly.** The implementation in `src/` and the
suite in `tests/` are the shipped Group 36 (Operations Management
L2) code, reused — this project's own Apache-2.0 code. All 7 `src/`
modules are byte-identical to Group 36's; 13 of 15 test files are
byte-identical and the 2 differing files differ by documentation
wording only (docstring group references; zero test-logic changes) —
20 of 22 files byte-identical in total (per-file SHA-256 in
`scratch/reuse-note.md`). The source carries no tier or baseline
strings: the code is tier-neutral. **What is NOT reused is the
baseline claim** — Group 36's Moderate / 800-171 framing does not
carry over; this group's spec, traceability, and README are written
against the Low baseline and FAR 52.204-21 only.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this fork) on
  the crosswalk (`../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring; LI-SaaS is a tailored **subset** of it for
  SaaS offerings), cross-walked to the 17 practices of **FAR
  52.204-21** that define CMMC L1. Derivation per the Merge Rule: the
  union of the Low and LI-SaaS parent baselines is the Low baseline
  itself (the subset adds nothing beyond it), inherited in full.

| Core function | Control families | How the build answers |
|---|---|---|
| Directory, projects | AC-3, AC-6, IA-2 (hooks) | People, organizations, and project membership are explicit records; assignment is computed from them, never assumed. FAR side: limit system access to authorized users and transactions. IA-2: identity is supplied by the embedding organization via user/role headers; the service ships hooks, not an identity provider |
| Work orders & lifecycle | CM-6, SI-10 | Work records follow a configured lifecycle; references, types, and due times are validated before any record or id exists |
| Overdue derivation | AU-2, AU-3 (Low side only), CM-6 | Overdue is derived at read from `due_at` and status against the report's `now`, never stored — reviewable and reproducible under the configured lifecycle |
| Assets | CM-8, AU-2 (Low side only) | Asset records with lifecycle are the inventory substrate; every transition is an auditable event |
| Inspections | AU-2, AU-3 (Low side only) | Inspection records with verbatim outcomes are auditable content, reviewable as written |
| Usage records | AU-2, AU-3 (Low side only) | Metering records are auditable content; they record usage of services |
| Workflow registry | CM-6 | Workflows are versioned configuration records, managed as configuration, not executed code |
| Reports | AU-2, AU-3 (Low side only) | Deterministic summaries over the records, including derived overdue at a stated `now` |
| Search | AU-2, AU-3 (Low side only) | Literal search over records supports review of auditable content |
| RBAC | AC-3, AC-6, IA-2 (hooks) | Three-role matrix enforced pre-mutation at two layers. IA-2: identity is supplied by the embedding organization via user/role headers; the service ships hooks, not an identity provider |
| Audit log | AU-2, AU-3 (Low side only) | Append-only log including denied attempts; no mutation API |
| Transport | SC-8 (partial) | TLS when a certificate is configured (see platform layer) |

**Precision notes (this tier).** (1) Audit traces to the AU family
**on the FedRAMP Low side of the crosswalk only**: FAR 52.204-21
contains no audit practice, so no audit claim is made on the CMMC
side. (2) Group 36's **AU-6** citation is deliberately **not**
imported here: AU-6 is not a Low selection and is not claimed; the
append-only store and the admin-gated audit read are implementation
properties, stated as such. Group 36's **SI-12** and **SC-28**
mentions are likewise not carried as control claims at this tier —
records-retention partiality and encryption-at-rest are stated as
implementation/deployment properties, not controls. (3) No
Moderate/High apparatus is inherited downward — and in this category
the parent build carries no tier-specific apparatus anyway: the code
is tier-neutral, and what does not carry is the baseline claim
itself.

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source
implementation whose features trace to the Low/L1 control families.

## Implementation contract (summary)

Identical to Group 36's contract — Python 3, **standard library
only**, package `opsmgmt` under `src/`, runnable and testable with
`PYTHONPATH=src`: `errors` (`OpsError`, `ValidationError`,
`NotFoundError`, `PermissionDenied`), `access` (User, role matrix),
`audit` (append-only AuditLog), `store` (OpsStore: the 12 core
functions; failed operations consume no ids; permission checks
precede mutation), `service` (HTTP layer, demo registry alice=admin
/ bob=operator / carol=viewer), `__main__` (`python -m opsmgmt
serve`, default port 8797). Tests: see tests/README.md.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (OpenWater, LI-SaaS; **0 claims** — 1 raw
  hit removed, recorded; the sheet is preserved in full regardless).
- Core implemented: **12 / 12** functions above, carried not claimed,
  at the Low/L1 baseline.
- Tests: see tests/README.md.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions (this fork's own engines, named from the
listing's own certified-service names):

- **Submission management engine** — custom submission forms / form
  builder, submission intake, reviewer assignment (the fork's
  certified Submission Management service; S2's form building and
  assignment prose).
- **Review & evaluation engine** — judge/reviewer scoring and
  feedback: the judging engine (the fork's certified Review &
  Evaluation service; S2's scoring and feedback prose). **Nothing in
  the build scores** — substrate inspection records hold verbatim
  outcomes only.

Out-of-scope product capabilities (each named in the listing, S4,
but **explicitly outside the FedRAMP Minimum Assessment Scope** —
gap-listed under that flag, not as in-scope claims):

- **Automated communications** — the product's automated
  communications capability (out-of-scope per S4).
- **Reporting** — the product's reporting capability, beyond the
  substrate's registry summaries (out-of-scope per S4).
- **Program website builder** (out-of-scope per S4).
- **Galleries** (out-of-scope per S4).
- **Conference session scheduling** (out-of-scope per S4; the
  category's scheduling/rostering absence otherwise stands — see the
  ranking note above).
- **Payments** (out-of-scope per S4).
- **Third-party integrations** (out-of-scope per S4; the removed raw
  hit — see the counting note and ARTIFACTS.md (g)).

Category-union Extended families already registered under Group 36
(restated for completeness, **NOT** re-registered): workflow
execution engine; real-time intelligence & analytics engine; AI
models; low-code application builder & deployment engine;
integration connector engines & catalog; mobile applications &
offline sync; network connectivity services & cloud platform
operations; authorization service / identity provider; common
security services enforcement plane; policy enforcement plane;
governance/compliance console engine.

Platform layer (gap-listed, never implied closed): multi-tenancy
(asserted by the fork of its own platform, S1; the build is a
single-tenant reference deployment); encryption at rest (deployment
layer); TLS only when a certificate is configured; demo identities
are hooks, not an IdP — IA-2 stays with the embedding organization.
