# GRC L2 — build (Operation DeadRamp, Phase 2, Group 33)

A clean-room **GRC records substrate**: the registers a governance,
risk, and compliance program keeps — frameworks and their controls,
the systems under governance, indicators and their recorded results,
evidence artifacts, findings and their remediation lifecycle,
assessments, and authorization status records — exposed over a REST
API with role-based access control and an append-only audit log.

Written from the group's contract only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**, zero
third-party dependencies.

A deliberate scoping note: this build is the **records substrate**,
not a GRC automation suite. It records what people and external
processes report; it contains **no validation engine, no scanner, no
evidence-collection connector, and no scoring model**. Those engines
are the Extended tail, listed plainly in the honesty section below.

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
   computed risk score or aggregate rating anywhere.**
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
| GET | `/audit` | audit_read | `{"entries": [...]}` |

## How to run tests

Tests live in `tests/` (standard library `unittest`):

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**118 tests, OK** at delivery, including a mutation-verified
negative control on the status derivation (see `tests/README.md`).
After the remainder additions below: **132 tests, OK**.

## Remainder additions (unit `addition:grc-l2`)

Five previously uncategorized offerings — **Anecdotes**, **Halo**,
**Kovr Nova**, **MediaLab Federal**, and the **Workiva Platform** —
were spec'd into this group under its existing taxonomy, applied
verbatim (see `ADDENDUM.md`). What changed: `specs/specs.json`
grew from 2 to 7 sheets (the original 2 byte-for-byte untouched),
adding **13 claims**; the group's two former named absences,
risk management and policy management, are now claimed and are
carried as records (assessment/finding records; catalog and
evidence records) — with no score computed anywhere, as before.
What did **not** change: the implementation. The core is the same
10 functions, `src/` is byte-identical, and the tier baseline is
unchanged; the new surfaces the additions actually run (policy
lifecycle, agentic execution, AI narrative generation, ITSM,
healthcare quality, connected reporting) are named as Extended
gaps in the addendum for the final batch.

## Control mapping summary

Against the NIST SP 800-53 Rev. 5 families the seeded catalog draws
from (baseline note: this group sits at the Moderate / L2 tier of the
DeadRamp crosswalk — a planning equivalence only; see the honesty
section):

- **CA** — framework & control registry, assessments, findings as
  POA&M records, continuous-monitoring records: CA-2 (control
  assessments), CA-5 (plan of action and milestones), CA-7
  (continuous monitoring — indicator results and posture are the
  monitoring record).
- **CM** — governed-system registry: CM-8 (system component
  inventory — systems are keyed by caller references, names are
  labels).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit
  information — append-only store, audit-read restricted to the
  `audit_read` permission).
- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement), AC-6 (least privilege — the member/viewer
  separations above); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **SC** — transmission: SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here).

## Honesty: what is NOT in this build

This build is a **records substrate**. The following product-side
engines and feeds are **Extended** and are NOT implemented here —
where an engine's *output* is a record, that record is fully
supported by the core above:

- **Automated validation / scanning engines** — indicator results
  and finding records are recorded here; nothing in this build
  checks a system, runs a test, or evaluates a control.
- **Evidence-collection connectors and feeds** — evidence arrives as
  caller-supplied content whose checksum is recorded; no connector
  pulls artifacts from any external system, and no feed is ingested.
- **Scoring and rating engines** — vendor or assessor scores,
  severities, results, and statuses are **recorded verbatim, never
  computed**. There is no computed risk score, no aggregate rating,
  no coverage percentage, and no roll-up grade anywhere in this
  build; posture reporting is counts and summaries only.
- **Workflow automation** — reminders, escalations, notifications,
  ticket sync, and auditor collaboration workflows are not
  implemented; the lifecycle transition tables and the audit log are
  the record of work, not an engine that performs it.
- **Identity providers** — the demo identities (`alice`, `bob`,
  `carol`) are **hooks, not an identity provider**. Production
  identity, authentication strength, and account lifecycle belong to
  the embedding organization (IA-2 hooks, not an IdP).

Further, plainly:

- The seeded catalog is **modest and generic seed data** (21
  controls), not a complete baseline, and registering a control here
  says nothing about whether it is implemented anywhere.
- An authorization status record records a status a person set; this
  build **grants no authorization** and is not itself an
  authorization or certification of anything, and it does not claim
  to be.
- The DeadRamp crosswalk (FedRAMP Moderate ↔ CMMC L2) is a planning
  and matching equivalence for the map only; nothing in this build
  confers or evidences either regime's standing.
- "Overdue" is a read-time derivation, not a stored fact: change the
  as-of date and the same record derives differently, by design.
