# GRC L1 singleton — build (Operation DeadRamp, Phase 2, Group 43)

The singleton build for the **Governance, Risk, and Compliance
(GRC)** category at the lightest tier: one fork — **Vanta - Trust
Management Platform** (Vanta Inc., FedRAMP **Low**, FedRAMP
Certified) — spec'd under the category taxonomy from Group 33
(GRC L2), and built as the category's **GRC records substrate** at
the Low / L1 baseline: the registers a governance, risk, and
compliance program keeps — frameworks and their controls, the
systems under governance, indicators and their recorded results,
evidence artifacts, findings and their remediation lifecycle,
assessments, and authorization status records — exposed over a
REST API with role-based access control and an append-only audit
log.

The fork is a genuine GRC platform (unlike Group 33's enclave
sibling, which claimed zero GRC families), and its description
carries **4 evidenced claims**: continuous monitoring, control &
framework compliance management, risk management ("vendor risk
management" — the family that was a named absence at L2 is claimed
here, on the fork's own words), and workflow & automation. The
remaining core functions are **carried, not claimed**, under the
explicit core-boundary decision recorded in `UNION-SPEC.md`.

Written from the group's contract only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**,
zero third-party dependencies. The implementation is the shipped
Group 33 code, reused byte-identical (see
`scratch/reuse-note.md`); what is new at this tier is the spec and
the baseline claim — the Low baseline and FAR 52.204-21 only.

A deliberate scoping note: this build is the **records substrate**,
not a GRC automation suite. It records what people and external
processes report; it contains **no validation engine, no scanner,
no evidence-collection connector, and no scoring model**. Those
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
   field set by an authorized reviewer, never computed.
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
   computed risk score or aggregate rating anywhere** — including
   under this tier's claimed risk-management family, whose records
   are held verbatim and never scored.
8. **REST API** — the service layer over HTTP exposing all of the
   above, JSON throughout, standard error shape `{"error": "..."}`
   with 400 / 401 / 403 / 404; denied attempts are audited.
9. **RBAC** — a role permission matrix (admin / member / viewer)
   enforced on every operation, in the store and over HTTP.
10. **Append-only audit log** — every mutation and every denied
    attempt recorded (actor, action, target, UTC timestamp), with
    optional JSONL file persistence. There is no update or delete
    API for the log.

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

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | read, manage_frameworks, manage_systems, manage_indicators, record_results, manage_evidence, review_evidence, manage_findings, manage_assessments, manage_authorizations, audit_read, admin |
| `bob`   | member | read, manage_systems, manage_indicators, record_results, manage_evidence, manage_findings, manage_assessments |
| `carol` | viewer | read |

Note the deliberate separations: a member may file evidence but may
not review it, may record work but may not register frameworks or set
authorization status, and may not read the audit log. A permitted role
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
| GET | `/frameworks/{id}/controls` | read | Controls in a framework → `{"controls": [...]}` |
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
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

Tests live in `tests/` (standard library `unittest`):

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**118 tests, OK** at delivery, including a mutation-verified
negative control on the status derivation, performed fresh in this
tree (see `tests/README.md`).

## Control mapping summary (Low / L1)

Against the NIST SP 800-53 Rev. 5 **Low** baseline families (this
group sits at the Low / L1 tier of the DeadRamp crosswalk — a
planning equivalence only; see the honesty section), cross-walked
to the FAR 52.204-21 practices:

- **CA** — framework & control registry, assessments, findings as
  POA&M records, continuous-monitoring records: CA-2 (control
  assessments), CA-5 (plan of action and milestones), CA-7
  (continuous monitoring — indicator results and posture are the
  monitoring record).
- **CM** — governed-system registry: CM-8 (system component
  inventory — systems are keyed by caller references, names are
  labels).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records) — **on the FedRAMP Low side of the crosswalk only**.
  FAR 52.204-21 contains no audit practice, so no audit claim is
  made on the CMMC side; Group 33's Moderate-level AU-6 / AU-9
  citations are **not** imported at this tier, and the append-only
  store with the admin-gated audit read is an implementation
  property. The Moderate/High apparatus (hash-chained audit,
  lockout, auditor role) is not inherited downward.
- **AC / IA** — access control: AC-3 (access enforcement), AC-6
  (least privilege — the member/viewer separations above); IA-2
  (identification & authentication — identity is supplied by the
  embedding organization via user/role headers; this service ships
  hooks, not an IdP). FAR side: limit system access to authorized
  users, personnel, and transactions.
- **SC** — transmission: SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here).
- **SI** — input validation (SI-10: malformed input rejected
  whole) and the flaw-remediation lifecycle (SI-2, via findings).
  No SI-7 claim is made at this tier (SI-7 is a Moderate
  selection); the evidence SHA-256 discipline is an implementation
  property.

## Honesty: what is NOT in this build

This build is a **records substrate**. The following product-side
engines and feeds are **Extended** and are NOT implemented here —
where an engine's *output* is a record, that record is fully
supported by the core above:

- **Continuous-monitoring and evidence-collection engines** — the
  fork's claimed monitoring and automation functions run as engines
  in the real product (automated checks, evidence pulled from
  connected systems). Nothing in this build checks a system,
  collects an artifact, or validates evidence automatically;
  results and artifacts are recorded as supplied.
- **Vendor risk assessment and scoring engines** — the fork claims
  vendor risk management; this build holds the risk-bearing
  *records* (governed parties, findings) verbatim. It evaluates no
  vendor and computes no risk score.
- **Questionnaire automation** — a named activity in the fork's
  prose; no questionnaire intake or response workflow is built.
- **Trust Center publication** — the fork displays an up-to-date
  security program description on a customer-facing Trust Center;
  this build's posture reporting is internal counts over records
  and publishes nothing.
- **Scoring and rating engines** — vendor or assessor scores,
  severities, results, and statuses are **recorded verbatim, never
  computed**. There is no computed risk score, no aggregate rating,
  no coverage percentage, and no roll-up grade anywhere in this
  build; posture reporting is counts and summaries only.
- **Workflow automation engines** — reminders, escalations,
  notifications, ticket sync, and auditor collaboration workflows
  are not implemented; the lifecycle transition tables and the
  audit log are the record of work, not an engine that performs it.
- **Identity providers** — the demo identities (`alice`, `bob`,
  `carol`) are **hooks, not an identity provider**. Production
  identity, authentication strength, and account lifecycle belong
  to the embedding organization (IA-2 hooks, not an IdP).

Further, plainly:

- **Claims discipline for this singleton:** 4 of the category's 14
  families are claimed by the fork's own prose; the rest of the
  core is carried under the boundary decision in `UNION-SPEC.md`,
  and the spec says which is which, function by function.
  `policy_management` is a **named absence** — the fork's prose
  contains no policy vocabulary — not a gap and not built.
- The seeded catalog is **modest and generic seed data** (21
  controls), not a complete baseline, and registering a control
  here says nothing about whether it is implemented anywhere.
- An authorization status record records a status a person set;
  this build **grants no authorization** and is not itself an
  authorization or certification of anything, and it does not
  claim to be.
- The DeadRamp crosswalk (FedRAMP Low ↔ CMMC L1) is a planning and
  matching equivalence for the map only; nothing in this build
  confers or evidences either regime's standing.
- "Overdue" is a read-time derivation, not a stored fact: change
  the as-of date and the same record derives differently, by
  design.
