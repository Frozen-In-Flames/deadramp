# Union Spec — Health & Wellness, CMMC L3-adjacent (DeadRamp Phase 2, Group 46 singleton)

The singleton spec for the Health & Wellness category at the
L3-adjacent tier: **1 fork, FedRAMP High** — Ceribell EEG
(Ceribell), FedRAMP Certified, SaaS, Government Community Cloud,
agency authorization held by the Department of Veterans Affairs.
Reconciled zero-diff: `specs/specs.json` ↔ `forks.json`
category="Health & Wellness" + cmmc_tier="L3-adjacent" (exactly
one match) ↔ MAP.md's category arithmetic (Health & Wellness
totals 10 offerings = 5 at L2, shipped as Group 18 + 1 at
L3-adjacent, this singleton + 4 untiered — 86Borders ConnectAllCare,
Elvo, HealthEdge Integrated Solution Suite, OpenClinica4 — remainder
forks). MAP.md's sibling sections list only groups of size 2+, and
Ceribell appears in no sibling section; forks.json exactness plus
the category arithmetic is the reconciliation, per the earlier
singleton builds.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 18 merged build** (`../health-wellness-l2/`) — the
   union of the 5 Health & Wellness L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room wellness records service
   (10 core functions) under this category's hard privacy rule.
2. This singleton's **1 High fork**, via the spec sheet in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheet are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was re-run
independently by the coordinator, and both negative controls were
mutation-verified by patching the implementation on the final tree
(see Verification below).

**Reuse, stated explicitly:** this build reuses Group 18's own
open-source code (Apache-2.0, ours). One module is byte-identical
to Group 18 (`__init__.py`); six are modified for the tier uplift
(`errors.py` — AuditWriteError added; `access.py` — auditor role
tightened to audit_read only; `audit.py` — hash chain, fail-closed
writes, and query added, following the proven `groups/analytics-l3`
mechanics; `store.py` — snapshot fail-closed wrapper on every
mutating method, following `groups/accounting-l3`;
`service.py` — lockout, audit verify/query endpoints;
`__main__.py` — lockout flags added). No core function changed
behavior except the auditor tightening, which is itself one of the
uplifts and is documented as such everywhere it lands.

## How functions were counted — zero claims, honestly

Group 18's 11-family taxonomy was applied **verbatim** (same ids,
labels, and matching patterns, in `scratch/extract.py`; verified
programmatically identical to Group 18's taxonomy) to this fork's
public marketplace description (GSA FedRAMP Marketplace dataset,
cached at `raw/data_dump.json`; produced by the General Services
Administration, last change 2026-10-22). A family is claimed only
when the offering's own description contains matching text; the
first matching sentence would be stored in `specs/specs.json` as
evidence.

**Result: 0 claims.** Ceribell's description is three sentences
about an FDA-cleared, AI-powered neurodiagnostic platform: bedside
diagnosis and real-time monitoring of suspected seizure patients,
a SaaS portal streaming EEG data for physician review, and
continuous AI monitoring producing a Seizure Burden trendline and
alerts for suspected status epilepticus. Group 18's taxonomy was
defined from glucose/CGM and patient-engagement descriptions, and
its patterns are literal phrases from those descriptions
("glucose meter data", "review, analysis", the spelled-out
"Artificial Intelligence (AI) powered"). None of them fires on an
EEG platform's vocabulary. The full description is preserved
verbatim in the spec sheet, and no function was invented for it.
Counts are a floor, and here the floor is zero — the same honest
outcome as the zero-claim sheets in Groups 28 and 35 and
Singletons 38 and 40.

Near-misses, recorded in full in `scratch/ARTIFACTS.md`, not
rounded up: "EEG data" / "real-time monitoring" do not match
measurement_data's glucose/clinical-metrics literals (the data
here is a clinical signal, and in substance it belongs to the
clinical engines below, not to the substrate's measurement
records); "securely review" is not "review, analysis"
(analysis_reporting) and "review from anywhere" is not
multi_device_access's phrasing; "AI-powered" / "AI monitoring"
do not match ai_platform's spelled-out phrase (Group 18's
correction 7 precedent: only the full phrase claims — Ceribell's
"AI" is a real word, not a substring artifact, but the
abbreviated form still does not match); "cloud-hosted portal"
is not hosting_platform's Google Cloud / GKE patterns; and the
clinical surface — bedside diagnosis, EEG streaming, Seizure
Burden quantification, seizure alerting — matches no taxonomy
family at all, because the taxonomy has no clinical-engine
family. It is named as Extended below, never tagged.

## Function ranking — the singleton

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Measurement & device data records | **Core** — measurement/outcome records, carried from the Group 18 union (claimed 3 of 5 there). Ceribell's EEG signal data is NOT this family: it is a clinical engine (below), and no EEG value is ever a substrate measurement record |
| 1 | 0 | Review, analysis, patterns/trends/statistics & scorecards | **Core** — population scorecard reporting over substrate records, carried from the Group 18 union (3 of 5 there); analysis engines Extended. The Seizure Burden trendline is a clinical computation, not this reporting |
| 1 | 0 | Care-journey guidance, education & navigation | Extended — carried from the Group 18 union (1 of 5 there); plan & activity records are Core |
| 1 | 0 | Patient engagement & surveys | Extended — carried from the Group 18 union (2 of 5 there) |
| 1 | 0 | Medical claims processing & reimbursement | Extended — adjudication engine, carried from the Group 18 union (2 of 5 there); eligibility/coverage records are Core |
| 1 | 0 | EMR / client-system integration | Extended — integration engines, carried from the Group 18 union (2 of 5 there) |
| 1 | 0 | AI-powered platform claims | Extended — AI/ML models, carried from the Group 18 union (1 of 5 there). Ceribell's AI monitoring is a clinical engine (below), not this platform family |
| 1 | 0 | Automated guidance / task automation | Extended — automation/workflow engines, carried from the Group 18 union (1 of 5 there) |
| 1 | 0 | Device data connection & upload | Extended — device sync pipelines, carried from the Group 18 union (1 of 5 there). Ceribell's EEG streaming is a clinical acquisition pipeline (below), not a sync pipeline |
| 1 | 0 | Multi-device / web / mobile access | Platform note — carried from the Group 18 union (2 of 5 there); an access surface, not a records function |
| 1 | 0 | Cloud hosting / deployment claims | Platform note — carried from the Group 18 union (1 of 5 there); deployment prose |
| 1 | — | Access control / RBAC (0 claims in group text at L2) | **Core** (baseline substrate, uplifted to High) — carried, not claimed |
| 1 | — | Audit logging (0 claims in group text at L2) | **Core** (baseline substrate, uplifted to High) — carried, not claimed |
| 1 | — | Telehealth media | **Named absence** at L2 (0 claims); Ceribell's portal is a review surface for recorded/streamed EEG, not a telehealth visit claim — not built, not a gap beyond its Group 18 registration |

Plus this singleton's own engines, named from its description
(all Extended, detailed in Gaps below): EEG signal acquisition &
real-time streaming; EEG waveform review rendering; continuous AI
seizure monitoring & Seizure Burden quantification; seizure
detection & alerting (suspected status epilepticus); bedside
diagnostic support. These are **clinical engines**: per this
category's hard privacy rule they are never built here, and
nothing in this build claims any diagnostic function.

**Core-boundary decision (recorded, per the Merge Rule and the
Group 22/23/35/40 precedent).** This fork tags zero claims, yet
all 10 core functions stand in this build. The reasoning is the
Merge Rule itself, not convenience: a cross-tier merge takes the
union of the parents upward whole, and Group 18's union — the
category substrate this fork's category presupposes — is a parent
of this build. A wording artifact (a three-sentence clinical
description with no taxonomy vocabulary) is not a downgrade, and
stripping the substrate at High because the High fork's prose is
clinical rather than administrative would dilute the union,
which Rule 1 prohibits. Every core function is therefore flagged
**carried, not claimed** for this tier. Where the fork claims
less than the substrate — which here is everywhere — that is this
paragraph, stated once and plainly, rather than ten quiet
exceptions. One boundary is sharper here than in any prior
singleton: the fork's actual product surface is clinical, and the
substrate is not a substitute for it. The substrate is what a
wellness program's records look like; Ceribell's product is a
neurodiagnostic device platform. Both facts are stated, neither
is blurred.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 functions as Group 18, carried up whole:

1. **Participant registry** — participants as records keyed by an
   **opaque, caller-supplied reference only** (`participant_ref`,
   unique). No name, contact, date-of-birth, or identifier fields
   exist in the shape. Carried, not claimed.
2. **Program registry** — programs (clinics, care journeys,
   scorecard populations) as records. Carried, not claimed.
3. **Enrollments with derived status** — enrollment/registration
   records binding a participant to a program; status
   (enrolled / completed / overdue) **derived deterministically**
   from the participant's plan records for that program, never
   stored as the derived value. Carried, not claimed.
4. **Measurement / outcome records** — numeric value + unit +
   metric name + date per participant, optionally per program.
   No diagnosis fields, no free-text clinical notes; unknown or
   extra fields are refused at the boundary. These are program
   metrics (the L2 siblings' glucose values, clinical-metric
   objectives) — **not** EEG data and not any clinical signal.
   Carried from the Group 18 union.
5. **Care / wellness plan records with derived status** — plan
   records with a due date and optional completion date; status
   (current / overdue / completed) derived deterministically.
   Carried, not claimed.
6. **Activity / appointment records** — scheduled activities and
   appointments bound to a participant and optionally a program,
   with a lifecycle state. Carried, not claimed.
7. **Eligibility / coverage records** — per-participant coverage
   records holding an **opaque plan reference only** (`plan_ref`),
   with coverage dates and a derived current status (upcoming /
   current / ended). No insurer names, member numbers, or benefit
   details exist in the shape. Carried, not claimed.
8. **Population scorecard reporting** — aggregates per metric
   (count, min, max, mean) and per derived status over the
   substrate records, group-wide and per program, plus
   per-participant measurement listing. Aggregation over records
   only; no pattern/trend detection, and **no clinical quantity
   of any kind is computed**. Carried from the Group 18 union.
9. **Access control (RBAC)** — admin/clinician/member/auditor
   roles over 16 actions, enforced before any state change;
   member-role callers read only their own participant's records.
   At High the **auditor role is tightened to `audit_read` only**
   [L3]. Baseline-carried, not claimed.
10. **Audit log** — append-only audit of every mutation and
    denied attempt; at High: **hash-chained and tamper-evident,
    fail-closed on write failure, and queryable** [L3].
    Baseline-carried, not claimed.

## Privacy discipline (hard rule, constitutive for this category)

- **Records + opaque references only.** Participants are keyed
  by a caller-supplied opaque `participant_ref`; coverage by an
  opaque `plan_ref`. The substrate never stores a real name,
  address, phone, email, date of birth, SSN, member/insurance
  number, or any other direct identifier — those fields **do not
  exist** in any entity shape, and the shapes are pinned by tests
  (`tests/test_privacy.py`: exact key sets for all 7 entities).
- **No diagnosis, no clinical free text, no clinical signal.**
  No entity has a diagnosis field, a notes field, or any field
  that could hold EEG data, waveforms, seizure events, or any
  other clinical content. Measurement records hold a metric name,
  a numeric value, a unit, and a date — program metrics only.
- **Refusal at the boundary.** The HTTP layer rejects any JSON
  key outside an endpoint's named field list with
  `ValidationError` (HTTP 400), so a caller cannot smuggle a
  diagnosis, a note, or an identifier into a record by adding a
  field. Pinned by tests.
- **Member scope.** A member-role caller can read only records
  whose participant's `participant_ref` equals the caller's user
  name.
- **Nothing diagnostic is claimed.** The fork's product is an
  FDA-cleared diagnostic platform; this build is a records
  substrate. It performs no diagnosis, no detection, no
  monitoring of any patient, and no alerting — and its documents
  say so wherever the fork's clinical surface is named.

## Control baseline and tier-uplift analysis (traceability)

- **Singleton tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 Rev. 2 **plus** the selected NIST SP 800-172
  enhanced requirements. The cross-tier parent (Group 18's build)
  sat at Moderate; the union baseline is therefore the High
  baseline, un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3
  is not identical to FedRAMP High; it is the same assurance
  weight class.
- **Feature → control family mapping (carried from Group 18):**

  | Core function | Control families | How the build answers |
  |---|---|---|
  | Participant registry (opaque refs) | AC-2, AU-2, SI-12 | Participants exist only as explicit records under caller-supplied opaque references; no identifier fields exist to leak |
  | Program registry | CM-6, SI-12 | Programs are explicit, configuration-controlled records |
  | Enrollments with derived status | AC-2, AU-2, CA-7 | Enrollment is an explicit, auditable record; its status is derived deterministically and is reviewable |
  | Measurement / outcome records | AU-2, AU-3, SI-10 | Every measurement leaves a validated record (named fields only; extra fields refused); inputs are validated before any record exists |
  | Care/wellness plan records | AU-6, CA-7, CM-6 | Plan status is derived deterministically from due/completion dates; derivation is queryable and reviewable |
  | Activity / appointment records | AU-2, CM-6 | Activities are explicit records bound to participants and programs, with auditable state changes |
  | Eligibility / coverage records | AU-2, SI-12 | Coverage exists only as a record under an opaque plan reference, with derived status reviewable as of any date |
  | Population scorecard reporting | AU-6, CA-7 | Reports aggregate the substrate records only; no side-channel data, no clinical computation |
  | RBAC (admin/clinician/member/auditor) | AC-3, AC-5, AC-6, IA-2 (hooks), IA-5 (hooks) | Role matrix enforced pre-mutation; auditor separated at High [L3]; identity itself is supplied by the embedding organization |
  | Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only, hash-chained, fail-closed, queryable log including denied attempts; no mutation API |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole operation (records + id counters, snapshot pattern) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | The L2 auditor held record reads + report_read + audit_read | **Implemented (tightening)**: the `auditor` role now holds `audit_read` **only** — audit review exists as a duty separable from administration and from record access. This is the one deliberate behavior change to an inherited function, recorded here and in tests/README.md. Organizational SoD policy remains the embedding organization's |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: identity-provider properties. This build ships hooks, not an IdP (same posture as Group 18, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is a
  planning/matching equivalence only: **FedRAMP authorizes
  products; CMMC certifies organizations** — the build is not a
  FedRAMP authorization and confers no CMMC certification, and
  neither regime accepts the other as evidence. Any real
  compliance claim still has to be earned inside each regime
  separately. A further caveat specific to this category: nothing
  in this traceability speaks to FDA clearance or any clinical
  regulatory status — the fork holds its own FDA clearance for
  its own product; this records substrate is not a medical
  device and claims no clinical function.

## Verification

- **Suite:** 121 tests, all passing, re-run independently by the
  coordinator on the final tree (67 inherited from Group 18, 7
  added inside inherited files for the uplifts, 47 in new files:
  audit chain 15, audit query 13, audit failure 6, lockout 6,
  privacy 7). Details and the complete Group 18 adaptation list:
  `tests/README.md`.
- **Negative controls (in-suite):** (1) the derivation mutant
  subclass (unchanged from Group 18) — a store whose plan-status
  derivation always returns `current` provably fails the
  canonical expectations; (2) the audit-tamper control — a
  mutated stored entry makes `verify_chain()` report failure at
  exactly that entry's index.
- **Mutation verification (coordinator, external, on the final
  tree):** Drill 1 — the overdue branch of
  `HealthStore._derive_plan_status` patched out of the real
  implementation: 121 ran, **exactly 8 failures**; store.py
  restored and SHA-256-verified byte-identical
  (`a0430e37…`, `scratch/store.py.sha256`); suite green again.
  Drill 2 — `AuditLog.verify_chain()` patched to return
  `(True, None)` unconditionally: 121 ran, **exactly 4
  failures**; audit.py restored and SHA-256-verified
  byte-identical (`be169ca5…`, `scratch/audit.py.sha256`);
  suite green again.
- **Coordinator smoke (live, on the final tree):** a plan due
  2026-01-10 reads `current` as of 2026-01-05 and `overdue` as
  of 2026-02-01, while the stored record carries no
  `derived_status` key; a participant record's keys are exactly
  `{id, participant_ref, kind, created_by, created_utc}`; a
  clean audit chain verifies `(True, None)` and an in-place
  mutation of entry 1's actor makes it report `(False, 1)`.

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (0 tagged claims; full description
  preserved; near-misses itemized in `scratch/ARTIFACTS.md`).
- Core implemented: **10 / 10** functions above, at the High
  baseline; 6 tier uplifts implemented (hash-chained audit,
  fail-closed audit writes with store rollback, audit
  query/reduction, chain verification endpoint, logon lockout,
  auditor tightening).
- Tests: **121**, all passing, independently re-run by the
  coordinator; both negative controls mutation-verified by
  patching the implementation (8 and 4 failures respectively).

## Gaps — specified, not implemented (for the GAPS.md final batch)

This singleton's own engines (Extended; named from its
description — the fork's actual product surface, none of it
built here, and per this category's hard privacy rule none of
it may be built on this substrate):

- **EEG signal acquisition & real-time streaming pipeline** —
  bedside device capture and live streaming of EEG data to the
  portal (clinical engine).
- **EEG waveform review rendering** — the physician review
  surface for streamed/recorded EEG (clinical engine; the
  substrate renders nothing).
- **Continuous AI seizure monitoring & Seizure Burden
  quantification** — the AI monitoring and trendline computation
  the description claims (clinical AI engine; no model of any
  kind exists in this build).
- **Seizure detection & alerting** — detection of and alerts
  for suspected status epilepticus (clinical engine; the
  substrate alerts no one about anything clinical).
- **Bedside diagnostic support** — the diagnostic function
  itself (clinical engine; this build performs no diagnosis
  and claims none).

Extended families carried from the Group 18 union, not
implemented (already registered under Group 18 in GAPS.md):
clinical decision support; EMR/EHR integration engines &
documentation depth; medical claims adjudication engine;
device connectivity / sync pipelines; AI/ML models &
personalization engines; automation / workflow engines;
survey instruments depth; patient engagement channels &
content; telehealth media (named absence); multi-device native
apps; hosting platform.

Baseline gaps at High (platform layer; gap-listed, never
implied closed): MFA / authenticator management (IA-2(1)/(2),
IA-5); FIPS-validated cryptography (SC-13); encryption at
rest (SC-28); audit retention enforcement (AU-11); session
lock / termination (AC-11/AC-12). Platform notes:
multi-tenancy (single-tenant reference deployment); TLS only
when a certificate is configured; demo identities are hooks,
not an IdP (IA-2 stays with the embedding organization).
