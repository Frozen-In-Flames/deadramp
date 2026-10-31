# GRC L3-adjacent — singleton build (Operation DeadRamp, Phase 2, Group 44)

The **Governance, Risk, and Compliance (GRC)** category's singleton
at the L3-adjacent tier: **1 fork — US AI (United Solutions)**,
FedRAMP **High**. A clean-room **GRC records substrate** carried up
whole from the Group 33 L2 build and uplifted to the High baseline:
the registers a governance, risk, and compliance program keeps —
frameworks and their controls, the systems under governance,
indicators and their recorded results, evidence artifacts, findings
and their remediation lifecycle, assessments, and authorization
status records — exposed over a REST API with role-based access
control and a hash-chained, tamper-evident audit log.

Written from the group's contract only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**,
zero third-party dependencies.

What the fork itself is, plainly (from its own marketplace
description): a managed, multi-tenant **AI platform suite** of nine
named microapp suites on an AI-powered data lake. Its GRC slice is
one suite (Archangel) whose substance is AI prediction —
accreditation prediction, device-log monitoring with vulnerability
and breach prediction, risk prediction. Under the category taxonomy
applied verbatim, the fork tags **2 claims** (continuous
monitoring, risk management), both engine claims; the Core below is
the records substrate those engines' outputs land in, plus the
Group 33 category union carried up under the Merge Rule. The full
account — claims, near-misses, the core-boundary decision — is in
[`UNION-SPEC.md`](UNION-SPEC.md).

A deliberate scoping note: this build is the **records substrate**,
not a GRC automation suite, and not an AI platform. It records what
people and external processes report; it contains **no validation
engine, no scanner, no evidence-collection connector, no model or
inference machinery of any kind, and no scoring model**. Those
engines are the Extended tail, listed plainly in the honesty
section below.

## The 10 core functions

1. **Framework & control catalog registry** — framework records
   (`id` / `name` / `version`) and the controls within them (control
   id like `AC-2`, family, title). A fresh store is seeded with a
   modest, generic 800-53-style catalog (one framework, 21 controls,
   in `src/grc/catalog.py`); callers may register further frameworks
   and controls.
2. **Governed-system registry** — systems under governance, keyed by
   opaque caller-supplied references. Free-text names are labels
   only; no real agency or system names are required.
3. **Indicator (KSI) registry** — indicator definitions linked to
   controls, plus recorded validation **results** (indicator, system,
   result status, timestamp, recorded-by). Results are records; no
   automated validation is performed, and a result status is stored
   verbatim exactly as recorded.
4. **Evidence registry** — artifacts as metadata records plus the
   SHA-256 checksum of the supplied content (the content itself is
   not retained), linked to controls and systems, with
   verify-by-content: re-supply content and the checksum comparison
   answers True/False. An artifact's validation status is a recorded
   field set by an authorized reviewer (never the user who filed
   it), never computed.
5. **Finding / remediation (POA&M-style) records** — findings with a
   severity recorded verbatim, a source, a due date, and a lifecycle
   enforced by a transition table (`open → in_progress → remediated →
   validated → closed`, plus `open / in_progress → accepted_risk`,
   which requires a recorded rationale). Any date-based status such
   as **overdue is derived at read time** from due date + lifecycle
   state + an as-of date — it is never stored on the record.
6. **Assessment & authorization-readiness records** — assessment
   records against a system/framework (scope, assessor reference,
   date, result recorded verbatim) and authorization status records
   whose transitions are guarded by a transition table
   (`not_started → in_progress → authorized / denied`, `authorized →
   expired / revoked`, with reopen paths), each keeping a full
   transition history.
7. **Posture reporting** — computed on read from the records: counts
   by framework/system/status (open findings, overdue findings,
   evidence counts by recorded validation status, indicator results
   summary by recorded status). **Counts and summaries only: no
   computed risk score or aggregate rating anywhere** — this fork's
   risk claim is an AI prediction engine (Extended); it does not
   license a score here.
8. **REST API** — the service layer over HTTP exposing all of the
   above, JSON throughout, standard error shape `{"error": "..."}`
   with 400 / 401 / 403 / 404; denied attempts are audited.
   **[L3]** adds `GET /audit/verify`, filtered `GET /audit`, and
   logon lockout.
9. **RBAC** — a role permission matrix (admin / member / viewer,
   **[L3]** plus auditor = `audit_read` only) enforced on every
   operation, in the store and over HTTP.
10. **Append-only audit log** — every mutation and every denied
    attempt recorded (actor, action, target, UTC timestamp), with
    optional JSONL file persistence. **[L3]** the log is
    **hash-chained and tamper-evident** (`verify_chain()`),
    **fail-closed** (a failed audit write rolls the operation
    back), and **queryable** (audit reduction). There is no update
    or delete API for the log.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Sequential ids are issued per object type: `ev-`, `find-`, `result-`,
`asmt-`, `auth-`. Frameworks, controls, systems, and indicators are
keyed by caller-supplied ids/references. Dates are ISO
(`YYYY-MM-DD`); timestamps are UTC ISO-8601. No monetary field
appears anywhere in this group.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m grc serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--max-failed-logins N` / `--lockout-seconds S` **[L3]** (AC-7
logon lockout; defaults 3 / 300), and `--certfile FILE
--keyfile FILE` to serve over TLS (standard library `ssl`). A
startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401). **[L3]** consecutive authentication
failures are tracked per username; at `--max-failed-logins` the
username locks for `--lockout-seconds` and further attempts (even
with the correct role) get 403, audited as `auth:locked`.

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, manage_frameworks, manage_systems, manage_indicators, record_results, manage_evidence, review_evidence, manage_findings, manage_assessments, manage_authorizations, audit_read, admin |
| `bob`   | member  | read, manage_systems, manage_indicators, record_results, manage_evidence, manage_findings, manage_assessments |
| `carol` | viewer  | read |
| `dana`  | auditor | audit_read **[L3]** |

Note the deliberate separations: a member may file evidence but may
not review it, may record work but may not register frameworks or set
authorization status, and may not read the audit log. The
**auditor** role **[L3]** (AC-5) holds `audit_read` and *nothing
else* — dana cannot read a single registry record; audit review
exists as a duty separable from administration. A permitted role
performing a forbidden action gets 403; validation failures get 400;
unknown objects get 404. Errors are always JSON `{"error": "..."}`
and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/frameworks` | read | List framework records → `{"frameworks": [...]}` |
| POST | `/frameworks` | manage_frameworks | Body `{"id", "name", "version", "description"?}` → 201 framework dict |
| GET | `/frameworks/{id}` | read | One framework dict |
| GET | `/frameworks/{id}/controls` | read | Controls in the framework → `{"controls": [...]}` |
| POST | `/frameworks/{id}/controls` | manage_frameworks | Body `{"id", "title", "family"?}` (family defaults to the id prefix) → 201 control dict |
| GET | `/frameworks/{id}/controls/{control_id}` | read | One control dict |
| GET | `/controls` | read | All registered controls across frameworks → `{"controls": [...]}` |
| GET | `/systems` | read | List governed systems → `{"systems": [...]}` |
| POST | `/systems` | manage_systems | Body `{"ref", "name", "description"?}` → 201 system dict |
| GET | `/systems/{ref}` | read | One system dict |
| GET | `/indicators` | read | List indicator definitions → `{"indicators": [...]}` |
| POST | `/indicators` | manage_indicators | Body `{"id", "name", "control_ids", "description"?}` → 201 indicator dict |
| GET | `/indicators/{id}` | read | One indicator dict |
| GET | `/indicators/{id}/results` | read | Recorded results for the indicator → `{"results": [...]}` |
| POST | `/indicators/{id}/results` | record_results | Body `{"system_ref", "status", "timestamp"?, "note"?}` → 201 result dict (status recorded verbatim) |
| GET | `/results?system={ref}` | read | Recorded results, optionally filtered by system → `{"results": [...]}` |
| GET | `/evidence?system=&control=` | read | List evidence records → `{"evidence": [...]}` |
| POST | `/evidence` | manage_evidence | Body `{"name", "content", "control_ids", "system_refs", "description"?}` → 201 evidence record (SHA-256 of `content`) |
| GET | `/evidence/{id}` | read | One evidence record |
| POST | `/evidence/{id}/verify` | read | Body `{"content"}` → `{"verified": true\|false}` (checksum comparison by content) |
| POST | `/evidence/{id}/review` | review_evidence | Body `{"validation_status", "note"?}` → updated evidence record (status recorded verbatim) |
| GET | `/findings?system=&status=&as_of=` | read | List findings → `{"findings": [...]}` (with `as_of`, each copy gains a read-time `derived_status`) |
| POST | `/findings` | manage_findings | Body `{"title", "system_ref", "severity", "source", "due_date", "description"?, "control_ids"?}` → 201 finding dict |
| GET | `/findings/{id}?as_of=` | read | One finding dict (with `as_of`, gains `derived_status`) |
| POST | `/findings/{id}/transition` | manage_findings | Body `{"status", "rationale"?}` → updated finding dict (`accepted_risk` requires `rationale`) |
| GET | `/assessments?system=&framework=` | read | List assessment records → `{"assessments": [...]}` |
| POST | `/assessments` | manage_assessments | Body `{"system_ref", "framework_id", "scope", "assessor", "date", "result", "notes"?}` → 201 assessment dict (result recorded verbatim) |
| GET | `/assessments/{id}` | read | One assessment dict |
| GET | `/authorizations?system=&status=` | read | List authorization records → `{"authorizations": [...]}` |
| POST | `/authorizations` | manage_authorizations | Body `{"system_ref", "framework_id", "status"?, "note"?}` → 201 authorization dict |
| GET | `/authorizations/{id}` | read | One authorization dict (includes transition `history`) |
| POST | `/authorizations/{id}/transition` | manage_authorizations | Body `{"status", "note"?}` → updated authorization dict |
| GET | `/posture?as_of=` | read | The posture summary dict (counts only) |
| GET | `/audit` | audit_read | `{"entries": [...]}`; **[L3]** optional `actor` / `action` / `target` / `since` / `until` filters (AU-7) |
| GET | `/audit/verify` **[L3]** | audit_read | `{"ok": bool, "entries": n, "first_bad_index": i\|null}` — hash-chain verification (AU-9) |

## How to run tests

Tests live in `tests/` (standard library `unittest`):

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**166 tests, OK** at delivery (118 inherited from Group 33, 7 added
inside inherited files for the uplifts, 41 in new uplift files),
including two mutation-verified negative controls — the status
derivation and the audit-chain verifier (see `tests/README.md`).

## Remainder addition (unit `addition:grc-l3`)

The group now specs **2 forks**: the remainder census added
**Exiger Federal Cloud (EFC) - High** (Covergent Solutions Inc
dba Exiger Government Solutions (EGS), FedRAMP High / Certified)
as a second spec sheet. Under the group's 14-family taxonomy
applied verbatim it claims **0 functions** — a zero-claim fork:
its entire marketplace description is one sentence naming its
own product and four modules (Due Diligence Intelligence, Third
Party Management, Supply Dynamics, Analytics), and no functional
pattern phrase of any family appears in it. The group total
stays **2 claims** (1 of 2 forks claiming); the named absence
`policy_management` survives at this tier (0 of 2). The core is
unchanged (`src/` byte-identical); the addition brings 14 new
spec-integrity and substrate tests — **180 tests, OK** — and
both signature drills were re-run in this tree (derivation:
exactly 9 failures under mutation; audit verifier: exactly 4).
Full account in [`ADDENDUM.md`](ADDENDUM.md).

## Control mapping summary

Against the NIST SP 800-53 Rev. 5 **High** baseline families (this
group sits at the High / L3-adjacent tier of the DeadRamp crosswalk —
a planning equivalence only; see the honesty section):

- **CA** — framework & control registry, assessments, findings as
  POA&M records, continuous-monitoring records: CA-2 (control
  assessments), CA-5 (plan of action and milestones), CA-6
  (authorization records), CA-7 (continuous monitoring — indicator
  results and posture are the monitoring record).
- **CM** — governed-system registry: CM-8 (system component
  inventory — systems are keyed by caller references, names are
  labels).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-5 **[L3]** (fail-closed writes with rollback), AU-6
  (audit review), AU-7 **[L3]** (audit reduction & search), AU-9
  **[L3]** (protection of audit information — hash-chained,
  tamper-evident, append-only; audit-read restricted to the
  `audit_read` permission).
- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement), AC-5 **[L3]** (separation of duties — the
  auditor role), AC-6 (least privilege — the member/viewer/auditor
  separations above), AC-7 **[L3]** (unsuccessful logon lockout);
  IA-2 (identification & authentication — identity is supplied by
  the embedding organization via user/role headers; this service
  ships hooks, not an IdP).
- **RA / SI** — findings: RA-3 / RA-5 (risk and vulnerability
  records — recorded, never scored), SI-2 (flaw remediation
  lifecycle), SI-7 (SHA-256 evidence integrity), SI-10 (input
  validation — malformed input rejected whole).
- **SC** — transmission: SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here). **SC-13 gap**: Python's standard library is not a
  FIPS-validated cryptographic module, and no FIPS claim is made.

Baseline gaps at High, named not implied closed: MFA / authenticator
management (IA-2(1)/(2), IA-5 — IdP layer), FIPS-validated
cryptography (SC-13), encryption at rest (SC-28), audit retention
enforcement (AU-11), session lock/termination (AC-11/AC-12).

## Honesty: what is NOT in this build

This build is a **records substrate**. The following engines and
platform machinery are **Extended** and are NOT implemented here —
where an engine's *output* is a record, that record is fully
supported by the core above:

- **Every AI / ML function the fork asserts** — accreditation and
  compliance prediction, vulnerability and breach prediction, risk
  prediction, disease prediction, responder matching, price and
  fraud insight: **no model, no inference, no prediction of any
  kind exists in this build.** The fork's two tagged claims are
  engine claims; their engines are the gap, their records are the
  core.
- **Automated validation / scanning / monitoring engines and
  feeds** — indicator results and finding records are recorded
  here; nothing in this build checks a system, watches a device
  log, runs a test, or evaluates a control.
- **Evidence-collection connectors and feeds** — evidence arrives as
  caller-supplied content whose checksum is recorded; no connector
  pulls artifacts from any external system, and no feed is
  ingested.
- **Scoring and rating engines** — vendor or assessor scores,
  severities, results, and statuses are **recorded verbatim, never
  computed**. There is no computed risk score, no aggregate rating,
  no coverage percentage, and no roll-up grade anywhere in this
  build or its output (test-enforced); posture reporting is counts
  and summaries only.
- **The fork's other eight suites** — software factory / app store
  and multi-cloud Kubernetes hosting, the ML data-lake platform,
  the traceability platform, the process designer, grants
  automation, the supply-chain and healthcare ecosystems, and
  emergency-response coordination are named in the union spec's
  long tail and gaps; none is built here. Blockchain and RPA
  machinery asserted across the suite is likewise not built.
- **Workflow automation** — reminders, escalations, notifications,
  ticket sync, and auditor collaboration workflows are not
  implemented; the lifecycle transition tables and the audit log
  are the record of work, not an engine that performs it.
- **Identity providers** — the demo identities (`alice`, `bob`,
  `carol`, `dana`) are **hooks, not an identity provider**.
  Production identity, authentication strength (MFA at this tier),
  and account lifecycle belong to the embedding organization (IA-2
  hooks, not an IdP).

Further, plainly:

- The seeded catalog is **modest and generic seed data** (21
  controls), not a complete baseline, and registering a control here
  says nothing about whether it is implemented anywhere.
- An authorization status record records a status a person set; this
  build **grants no authorization** and is not itself an
  authorization or certification of anything, and it does not claim
  to be.
- The fork operates multi-tenant in reality; this build is a
  **single-tenant reference deployment**. Multi-tenancy is a
  platform property, named as a gap in the union spec.
- The DeadRamp crosswalk (FedRAMP High ↔ CMMC L3-adjacent) is a
  planning and matching equivalence for the map only; nothing in
  this build confers or evidences either regime's standing.
- "Overdue" is a read-time derivation, not a stored fact: change the
  as-of date and the same record derives differently, by design.
