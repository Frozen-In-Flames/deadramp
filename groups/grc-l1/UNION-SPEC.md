# Union Spec — Governance, Risk, and Compliance (GRC), CMMC L1 singleton (DeadRamp Phase 2, Group 43)

The functional spec for the **GRC L1 singleton**: a sibling group of
**one fork** — **Vanta - Trust Management Platform** (Vanta Inc.),
SaaS, Public Cloud deployment, FedRAMP **Low**, FedRAMP Certified
(FedRAMP ID FR2525556241). Per PIPELINE.md, singletons build after
the sibling groups with the same pipeline at group size one: this
spec is the one fork's claims under the category taxonomy, and the
build is the category substrate those claims presuppose, at this
fork's own tier.

The fork's marketplace record adds program context the spec sheet
preserves without converting into claims: the certification is a
**FedRAMP 20x Class B Pilot** certification (the record's
`fedramp_msg`; its `filter_classes` carries
`filter-impact-level-20x-Low`), with Schellman as assessor of
record in the listing filters. Program membership is not a function
claim; see `scratch/ARTIFACTS.md`.

**Reconciliation (zero diffs).** `forks.json` carries exactly one
GRC / L1 entry (the fork above; its registry fields match the raw
marketplace record field for field — impact Low in both, status
FedRAMP Certified in both, asserted programmatically in
`scratch/extract.py`). MAP.md omits groups of one from its
sibling-group sections by design; the reconciliation therefore runs
through the category total: MAP.md's category table gives GRC
**11** offerings, and the `forks.json` tier split accounts for all
of them — L2 (2) + L3-adjacent (1) + L1 (1) + untiered (7) = 11 —
with this singleton the L1 entry.

## How functions were counted

The fixed **14-family taxonomy from Group 33** (GRC L2) was applied
**unchanged** — ids, labels, and matchers verified byte-identical
against Group 33's extractor — so counts are comparable across the
category's tiers. A family is claimed only when the fork's own
public description contains matching text; the first matching
sentence is stored in `specs/specs.json` as evidence. Group 33's
pattern-intrinsic corrections are inherited with the taxonomy and
were not re-opened (a component name earns no tag; bare "risk"
earns no tag; only `service_desc` is matched). **4 claims** survive
(4 raw hits, 0 removed — no new corrections were needed). Counts
are a **floor**, not a ceiling. Near-misses are itemized in
`scratch/ARTIFACTS.md`; the taxonomy was **not** re-tuned to
capture them.

## Function ranking — the singleton fork under the category taxonomy

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Control & framework compliance management | **Core** — framework & control catalog registry (#1) |
| 1 | 1 | Continuous monitoring | **Core** — monitoring results recorded on indicators and evidence (#3, #4); the monitoring engine and its feeds are Extended |
| 1 | 1 | Risk management | **Core (records slice)** — risk-bearing records held verbatim in the governed-system and finding registries (#2, #5); the risk assessment / scoring engine is Extended, and no score is computed anywhere |
| 1 | 1 | Workflow & automation | **Core (seed)** — enforced record lifecycles (#5, #6) are the in-core seed; automation engines Extended |
| 5 | 0 | Evidence management & validation | 0 claims — no "evidence" token appears in the description (recorded near-miss); the registry (#4) is carried substrate (boundary decision); collection/validation engines Extended |
| 5 | 0 | Security indicators (KSI) tracking & validation | 0 claims — the fork's 20x program context is not an indicator claim (recorded near-miss); the indicator registry (#3) is carried as the monitoring-results record shape; automated validation Extended |
| 5 | 0 | Compliance posture reporting & dashboards | 0 claims — the Trust Center display sentence is a recorded near-miss (no dashboard/view pattern fires); posture counts (#7) are carried as the read side of the claimed families; Trust Center publication Extended |
| 5 | 0 | Assessment & authorization support | 0 claims — the "selected audit partners" sentence is a recorded near-miss (no assessor/authorization phrasing); readiness records (#6) carried substrate; package generation Extended |
| 5 | 0 | Audit support & assessor review | 0 claims — same near-miss; the append-only audit (#10) is carried on the FedRAMP Low side of the crosswalk only (see baseline) |
| 5 | 0 | APIs & integrations | 0 claims — the REST API (#8) is carried as baseline substrate; evidence-collection integrations Extended |
| 5 | 0 | Identity & access controls (hooks) | 0 claims — RBAC (#9) is carried as Low-baseline hooks |
| 5 | 0 | Vulnerability & remediation management | 0 claims — finding/remediation records (#5) are carried as the substrate of the claimed risk and monitoring families; the scanning engine Extended |
| 5 | 0 | Platform hosting / enclave operations | 0 claims — absent (SaaS / Public Cloud are record fields, not hosting phrasing; the opposite shape from Group 33's enclave sibling) |
| 5 | 0 | Policy management | **Named absence** — no policy vocabulary exists in the fork's prose (0 claims at L2 as well); not built, not a gap |

**The tier difference from Group 33, stated plainly.**
`risk_management` was a **named absence at L2**: neither L2 fork's
own prose contains the phrase, and Group 33's spec records that no
risk engine was rounded up from the category name. This fork's
prose *does* contain it — "vendor risk management" is one of its
four named activities — so at this tier the family is **claimed**.
What the claim buys is records: vendors and systems under risk
management are governed-system records (opaque references), and
risk findings are finding records, both held verbatim. It does not
buy an engine: risk *assessment* and *scoring* are Extended, and
the Core computes **no risk score anywhere** — posture reporting
is counts only, enforced recursively by `test_posture.py`. The
consequence Group 33 drew from the absence (no scores in the Core)
holds at this tier for the stronger reason that a claim was never
a license to compute one.

**The fork's excess over the substrate** (functions its description
asserts beyond the claimed families' record shapes):
**questionnaire automation** (a named activity no taxonomy family
names), **Trust Center publication** of the up-to-date security
program description, and the **continuous, automated evidence
collection** the "compliance automation suite" and "continuous
monitoring solution" phrases presuppose as an engine (the Core
records the results; it collects nothing). These are specified as
Extended gaps below — named, not forced into families.

## The Core — what the build implements (10 functions)

The same GRC records substrate the category's L2 merged build
implements — the records substrate this fork's claims presuppose:

1. **Framework & control catalog registry** — frameworks and their
   controls registered as catalog records. **Anchored in this
   fork's own claim**: `control_framework_compliance` (the
   platform streamlines compliance against named frameworks —
   SOC 2, ISO 27001, ISO 42001, NIST AI RMF, CIS CSC, NIST CSF,
   FedRAMP; the names are catalog content this registry holds).
2. **Governed-system registry (opaque references)** — the
   systems, environments, and vendors under governance, known
   only by caller-supplied opaque references. **Anchored in
   part**: it is the object registry of the claimed
   `continuous_monitoring` and `risk_management` (vendor risk)
   functions; no field can hold a real credential or network
   identifier.
3. **Indicator registry with recorded validation results** —
   indicators registered per framework/system, each carrying an
   append-only history of validation results (status verbatim,
   timestamp, evidence links). **Carried**: the indicator family
   itself tags 0 here (the fork's 20x program context names no
   indicator vocabulary), and this registry is the record shape
   the claimed continuous monitoring produces. Recording a result
   is Core; *performing* the validation is Extended.
4. **Evidence registry (metadata + SHA-256, validation-status
   records)** — artifacts registered by metadata and content
   hash (the registry holds records and hashes, not binaries),
   with verify-by-content and validation statuses recorded
   verbatim, never computed. **Carried**: the evidence family
   tags 0 here (no "evidence" token in the prose); the registry
   is the artifact substrate the claimed compliance-automation
   work presupposes.
5. **Finding / remediation (POA&M-style) records** — findings
   with an enforced lifecycle and due dates; due-date status
   (overdue) is **DERIVED at read time, never stored**.
   **Anchored in part**: the records the claimed
   `risk_management` function and the claimed monitoring outputs
   land in; severities and statuses recorded verbatim.
6. **Assessment & authorization-readiness records** — assessment
   events and per-system readiness records. **Carried**: the
   assessment family tags 0 here (the audit-partner sentence is a
   recorded near-miss); assessment-shaped records are what the
   claimed framework-compliance work is worked against, stated
   as interpretation, not evidence.
7. **Posture reporting computed on read** — per-system and
   per-framework counts and summaries from records only:
   indicator validation counts, evidence counts by recorded
   validation status, open/overdue finding counts, readiness
   summaries. **Counts and summaries only — NO computed risk
   scores** (no score field exists anywhere; the claimed risk
   family changes nothing about this). **Carried** as the read
   side of the claimed monitoring and compliance families; the
   family's dashboard phrasing tags 0 (Trust Center near-miss).
8. **REST API** — every function above over HTTP/JSON.
   **Carried** as baseline substrate (the integrations family
   tags 0; no connector claim is asserted).
9. **RBAC** — role-based access hooks (admin / member / viewer)
   with a permission matrix enforced on every operation.
   **Carried** as baseline substrate; identity is supplied by
   the embedding organization — hooks, not an identity provider.
10. **Append-only audit with denied attempts** — every mutation
    and every denied attempt recorded (actor, action, target,
    UTC timestamp). **Carried** as baseline substrate; at this
    tier it traces to the AU family on the FedRAMP Low side of
    the crosswalk only (see baseline precision notes).

**Core-boundary decision (explicit).** Of the 10 core functions,
one is anchored in this fork's own claims (the catalog registry),
three are anchored in part (governed systems, findings, and the
lifecycle seed inside the assessment records), and the rest tag
zero claims in this group and are **carried, not claimed**: they
stand because (a) the fork's own claims presuppose them — there
is no continuous monitoring without a results record, no vendor
risk management without a governed-party registry and a findings
record, no compliance automation without artifacts and an audit
trail — and (b) the category union at L2 established this
substrate as the GRC core, and a singleton inherits its category's
substrate at its own tier rather than re-deriving a lesser one. A
wording artifact is not a downgrade, and a singleton is not a
lesser build. This mirrors the recorded boundary decisions in
Groups 37, 38, and 33 itself.

**Reuse, stated explicitly.** The implementation in `src/` and
the suite in `tests/` are the shipped Group 33 (GRC L2) code,
reused — this project's own Apache-2.0 code. All 8 `src/` modules
are byte-identical to Group 33's (SHA-256 per file in
`scratch/reuse-note.md`); 13 of 14 test files are byte-identical
and the one differing file differs by a single docstring line
(zero test-logic changes, diff-verified). The source carries no
tier or baseline strings: the code is tier-neutral. **What is NOT
reused is the baseline claim** — Group 33's Moderate / 800-171
framing does not carry over; this group's spec, traceability, and
README are written against the Low baseline and FAR 52.204-21
only.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** (this fork) on
  the crosswalk (`../../crosswalk.md`). The L1 tier also holds
  LI-SaaS forks, whose baseline is a tailored subset of Low;
  derivation per the Merge Rule: the union of the Low and
  LI-SaaS parent baselines is the Low baseline itself (the subset
  adds nothing beyond it), inherited in full.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline
  (the FedRAMP Low tailoring), cross-walked to the 17 practices
  of **FAR 52.204-21** that define CMMC L1.

| Core function | Control families | How the build answers |
|---|---|---|
| Framework & control catalog registry | CA-2, PM (program registry posture) | The catalog is what assessments are recorded against; framework/program records are the registry. FAR side: no direct practice — cataloging is program bookkeeping, stated as such |
| Governed-system registry | CA-6 (readiness tracked per system), CM-8 | The registry is the inventory of record, by opaque reference. FAR side: the practices on identifying and inventorying systems the organization operates |
| Indicator registry & validation results | CA-7, CA-5 (adjacent record discipline) | Recorded validation results are the continuous-monitoring record of the claimed monitoring function |
| Evidence registry | AU-2, AU-3 (Low side only — see notes), SA (records posture) | Metadata + SHA-256 with verify-by-content; validation statuses recorded verbatim. **No SI-7 claim is made at this tier** (SI-7 is a Moderate selection); the checksum discipline is an implementation property |
| Finding / remediation records | RA-5 (records of scanning/monitoring output), SI-2 (flaw remediation lifecycle), CA-5 (POA&M shape) | Findings are recorded, never scored; the lifecycle is enforced and due-date status is derived at read |
| Assessment & readiness records | CA-2, CA-6 | Assessment events and readiness state per governed system |
| Posture reporting (computed on read) | CA-7 | Summaries derive from records on read, never from stored derived state; counts only |
| RBAC | AC-3, AC-6, IA-2 (hooks) | Three-role matrix enforced pre-mutation at two layers. FAR side: limit system access to authorized users, personnel, and transactions. IA-2: identity is supplied by the embedding organization via user/role headers; the service ships hooks, not an identity provider |
| Append-only audit | AU-2, AU-3 (Low side only — see notes) | Append-only log including denied attempts; no mutation API |
| Input discipline, all registries | SI-10, SC-8 (partial) | Malformed input rejected whole, never partially applied; transmission protection is TLS when a certificate is configured (see gaps) |

**Precision notes (this tier).** (1) Audit traces to the AU
family **on the FedRAMP Low side of the crosswalk only**: FAR
52.204-21 contains no audit practice, so no audit claim is made
on the CMMC side — the position differs from Group 33 at L2,
where the 800-171 substrate (family 3.3) lets the audit trace
hold on both sides; that Moderate-side support does **not**
exist at L1 and is not claimed. (2) Group 33's Moderate-level
audit citations are deliberately **not** imported here: **AU-6
and AU-9 are not claimed at this tier**; the append-only store
and the admin-gated audit read are implementation properties,
stated as such. (3) The Moderate/High apparatus from the sibling
tiers (the L3 groups' hash-chained audit, lockout machinery,
auditor role, 800-172-derived enhancements) is out of scope for
a Low/L1 build and is **not inherited downward**. (4) No SI-7
claim (Moderate selection); evidence checksums are an
implementation property.

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP
authorization and confers no CMMC certification; it is an
open-source implementation whose features trace to the Low/L1
control families. **FedRAMP authorizes products; CMMC certifies
organizations**, and compliance inside each regime must still be
earned separately.

## Implementation contract (summary)

Identical to Group 33's contract — Python 3, **standard library
only**, package `grc` under `src/`, runnable and testable with
`PYTHONPATH=src`: `errors` (GrcError family), `access` (User,
admin/member/viewer matrix of 12 actions), `audit` (append-only
AuditLog with optional JSONL persistence), `catalog` (the seeded
generic 800-53-style catalog: one framework, 21 controls — seed
data, not a baseline), `store` (GrcStore: the 10 core functions;
failed operations consume no ids; permission checks precede
mutation; finding status derived at read, never stored), `service`
(HTTP layer, demo registry alice=admin / bob=member /
carol=viewer), `__main__` (`python -m grc serve`). `tests/`: 118
unittest tests across 13 modules, every test docstring tracing to
a core function, a claim family, or a control family; the
negative control and its live mutation verification **in this
tree** are recorded in `tests/README.md` (derivation mutant →
8 failures; restored SHA-256-identical, suite green).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Vanta - Trust Management Platform,
  FedRAMP Low; 4 evidenced claims over the 14-family category
  taxonomy).
- Core implemented: **10 / 10** functions above, at the Low/L1
  baseline — 1 claim-anchored, 3 anchored in part, 6 carried
  under the recorded boundary decision.
- Tests: **118 run, 118 passed**, including the mutation-verified
  negative control (drill performed fresh in this tree).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions (this fork's excess and the claimed families'
engine remainders):

- **Continuous-monitoring engine & evidence-collection
  integrations** — the automated control checks and the
  collection of evidence from connected systems that the claimed
  monitoring and automation functions presuppose as an engine.
  The Core records results and artifacts; it checks nothing and
  collects nothing. *(Overlaps Group 33's registered "automated
  evidence-validation engine" and "continuous-monitoring feeds"
  entries; the engine remainder is named here from this fork's
  own claims.)*
- **Automated evidence validation** — verifying collected
  evidence automatically (already registered under Group 33;
  restated because it is this fork's engine remainder too).
- **Vendor risk assessment engine** — evaluating and scoring
  vendors (the `risk_management` claim's engine remainder;
  risk-bearing *records* are Core, held verbatim, and no score
  is computed anywhere in the Core).
- **Questionnaire automation engine** — security/audit
  questionnaire intake, reuse of prior answers, and response
  workflows (a named activity in the fork's prose that no
  taxonomy family names).
- **Trust Center publication** — customer-facing publication of
  the up-to-date security program description and posture (the
  Core's posture reporting is internal counts over records; it
  publishes nothing).
- **Posture / risk scoring engines** — any engine that computes
  a posture or risk *score* (already registered under Group 33;
  deliberately absent here — Core posture is counts only).
- **Workflow automation engines** — reminders, escalations,
  notifications, ticket sync, and auditor-collaboration
  workflows (the `workflow_automation` claim's engine remainder;
  the enforced record lifecycles are the Core seed).
- **Vulnerability scanning engine** — already registered under
  Group 33 (0 claims at this tier; the finding-records substrate
  is Core).
- **Automated KSI validation** — already registered under Group
  33 (0 claims at this tier; the indicator registry is Core).
- **FedRAMP authorization package generation** — already
  registered under Group 33 (readiness records are Core; no
  package is generated).
- **Hosted enclave & PaaS operations** — already registered
  under Group 33 (0 claims at this tier; this fork is SaaS).

Named absence (0 claims in the fork's prose; excluded from the
union, not silently dropped, and **not** a gap because unclaimed):

- **Policy management** — no policy authoring/definition/
  enforcement sentence exists in the description (the same
  absence Group 33 recorded at L2).

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when a certificate is
configured; multi-tenancy (the build is a single-tenant reference
deployment); demo identities are hooks, not an IdP — IA-2 stays
with the embedding organization.
