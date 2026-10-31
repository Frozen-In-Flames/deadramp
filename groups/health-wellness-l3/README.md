# Health & Wellness L3-adjacent — singleton build (Operation DeadRamp, Phase 2, Group 46)

This is the clean-room implementation of the **Health & Wellness
L3-adjacent singleton**: **1 fork** from the FedRAMP Marketplace
at the High tier — **Ceribell EEG (Ceribell)**, FedRAMP
Certified — built under the Merge Rule as the cross-tier merge
of that fork with the shipped Group 18 Health & Wellness L2
build: the L2 category substrate carried up whole and uplifted
to the FedRAMP High baseline.

Three honesty notes up front. First, **the singleton tags zero
claims** under Group 18's verbatim taxonomy: Ceribell's
marketplace description is three sentences about an FDA-cleared,
AI-powered neurodiagnostic platform (bedside seizure diagnosis,
EEG streaming to a review portal, AI Seizure Burden monitoring),
and Group 18's taxonomy — defined from glucose/CGM and
patient-engagement descriptions — contains no phrase that fires
on it. The near-misses are itemized in `scratch/ARTIFACTS.md`
("AI-powered" is not the spelled-out "Artificial Intelligence
(AI) powered"; "EEG data" is not "glucose meter data") and the
taxonomy was not re-tuned. The 10 core functions below are
therefore **carried, not claimed**, for this tier — they stand
because the Merge Rule carries the L2 union upward whole and a
wording artifact is not a downgrade (the core-boundary decision
in `UNION-SPEC.md`). Second, **Ceribell's own engines are not
in this build and may not be built on it**: EEG acquisition and
streaming, waveform review, AI seizure monitoring, seizure
alerting, and diagnostic support are clinical engines, named as
Extended gaps in `UNION-SPEC.md` for the final batch. Nothing
in this build performs or claims any diagnostic function.
Third, this category's **hard privacy rule** binds the whole
build: records carry opaque references only — no real PHI/PII
content exists in any record shape, ever (see Honesty).

It was written from the union contract only: original code, no
vendor code, assets, or branding. Python 3, **standard library
only**, no external dependencies. Where functions overlap it
reuses Group 18's own Apache-2.0 code: `__init__.py` is
byte-identical; the other six modules are Group 18's, modified
only for the High uplifts marked **[L3]** below.

## The 10 core functions (carried from Group 18, at High)

1. **Participant registry** — participants (`par-`) keyed by a
   required, unique, **opaque caller-supplied
   `participant_ref`**. No name, contact, or date-of-birth
   fields exist in the shape.
2. **Program registry** — programs (`prg-`): clinics, care
   journeys, scorecard populations, as configuration records.
3. **Enrollments with derived status** — enrollment records
   (`enr-`) binding a participant to a program; status
   (enrolled / completed / overdue) is **derived at read time**
   from the participant's plan records for that program, never
   stored as the derived value.
4. **Measurement / outcome records** — measurements (`msr-`):
   metric name, numeric value, unit, date, per participant and
   optionally per program. Program metrics only — **no
   diagnosis fields, no clinical notes, no EEG or any other
   clinical signal**; extra fields are refused at the boundary.
5. **Care / wellness plan records** — plans (`pln-`) with a due
   date and optional completion date; status (current /
   overdue / completed) derived deterministically at read.
6. **Activity / appointment records** — activities (`act-`)
   bound to a participant and optionally a program, with a
   scheduled / completed / cancelled lifecycle.
7. **Eligibility / coverage records** — coverage records
   (`elg-`) holding an **opaque `plan_ref` only**, with
   coverage dates and a derived status (upcoming / current /
   ended). No insurer names, member numbers, or benefit
   details exist in the shape.
8. **Population scorecard reporting** — per-metric aggregates
   (count, min, max, mean) and per-derived-status breakdowns
   over the substrate records, group-wide and per program.
   Aggregation over records only; no clinical quantity is
   computed.
9. **Access control (RBAC)** — roles admin / clinician /
   member / auditor over 16 actions, enforced before any
   mutation; member callers read only their own participant's
   records. **[L3]** the auditor role is tightened to
   `audit_read` only (AC-5 separation of duties).
10. **Audit log** — append-only log of every mutation and
    every denied attempt. **[L3]** hash-chained and
    tamper-evident (`verify_chain()`), fail-closed on write
    failure (the operation rolls back), and queryable by
    actor/action/target/since/until; **[L3]** per-username
    logon lockout in the service layer (AC-7).

## Run

```bash
cd groups/health-wellness-l3
PYTHONPATH=src python3 -m health serve            # http://127.0.0.1:8792
PYTHONPATH=src python3 -m health serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m health serve --max-failed-logins 3 --lockout-seconds 300
PYTHONPATH=src python3 -m health serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity
provider — production identity belongs to the embedding
organization). Callers authenticate with `X-User` / `X-Role`
headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | clinician | all record reads; enrollment/measurement/plan/activity writes; reports |
| `carol` | member | record reads, own participant's records only |
| `dana` | auditor | **[L3]** the audit log only (incl. `/audit/verify`) |

Endpoints follow Group 18's table exactly (`GET /health`,
`/participants`, `/programs`, `/enrollments`, `/measurements`,
`/plans`, `/activities`, `/eligibility`, `/report`,
`/scorecard/{id}`, `GET /audit`), plus the **[L3]** additions:
`GET /audit` accepts `actor`, `action`, `target`, `since`,
`until` filter parameters, and `GET /audit/verify` returns
`{ok, entries, first_bad_index}` (audit_read). Errors are JSON
`{"error": msg}`: 400 validation (including any unknown JSON
key in a request body), 401 unknown user or role mismatch,
403 permission, 404 not found. Denied attempts are audited
with the action suffixed `:denied`.

## Tests

```bash
cd groups/health-wellness-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 121 tests
```

**121 tests, all passing** (67 inherited from Group 18, 7
added inside inherited files, 47 in new uplift/privacy
files), including two negative controls, both
mutation-verified by patching the real implementation on the
final tree: removing the plan-status overdue branch produces
exactly 8 failures, and neutering `verify_chain()` produces
exactly 4 (see `tests/README.md` for the drill record and the
complete list of Group 18 test adaptations).

## Honesty

- The build implements the wellness **records substrate**
  the category's L2 union established, at the High baseline.
  It is not Ceribell's product: the EEG device platform —
  signal acquisition, streaming, waveform review, AI seizure
  monitoring and alerting, diagnostic support — is a set of
  clinical engines, specified as Extended gaps in
  `UNION-SPEC.md` and absent here by design.
- **Privacy is constitutive, not decorative.** Every entity
  shape is pinned by tests to an exact key set containing no
  name, email, phone, date of birth, diagnosis, note, insurer,
  member-number, or any other identifier or clinical field.
  The HTTP layer refuses unknown JSON keys (400), so clinical
  content cannot be smuggled into a record. Participants and
  coverage exist only under opaque caller-supplied references.
- Statuses (plan, enrollment, eligibility) are **derived at
  read time** from stored dates, deterministically; the stored
  records carry no derived-status field.
- This build is not a medical device, performs no diagnosis,
  monitoring, or alerting, and claims no FDA or clinical
  status of any kind. The fork's FDA clearance belongs to the
  fork's own product.
- Claims discipline: the singleton tags **0 claims**; every
  core function is flagged carried-not-claimed for this tier
  in `UNION-SPEC.md`, with the Merge Rule reasoning stated
  once, plainly. Counts are a floor, stated as such.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization; MFA-grade
  authentication (IA-2(1)/(2), IA-5), FIPS-validated crypto
  (SC-13), encryption at rest (SC-28), audit retention
  (AU-11), and session management (AC-11/AC-12) are named
  gaps at this tier, not implied closures. The deployment is
  a single-tenant reference deployment; TLS applies when a
  certificate is configured.
