# Governance, Risk, and Compliance (GRC) — untiered set

**Untiered Set 3** of the DeadRamp remainder build. This group
covers the **15 forks** of census unit
`untiered:Governance, Risk, and Compliance (GRC)` whose FedRAMP
impact level in the source data is **Unknown**.

An untiered set is a census category whose forks carry **no FedRAMP
impact level and no CMMC tier**. Its tier is therefore **null**: the
group is not built to any baseline. It is built only to what the
forks' own descriptions document — the **documented control
claims** below. Nothing is inferred from a tier, and no CMMC
equivalence is drawn anywhere.

The Core is the GRC category's records substrate, carried whole
from the founding group (groups/grc-l2) — see "Core accounting"
below. The full claim ranking, dispositions, and gap list are in
[UNION-SPEC.md](UNION-SPEC.md); the extraction record (verbatim
proof, exclusion pass, wording artifacts, near-misses) is in
`scratch/ARTIFACTS.md`.

## The 15 forks

Spec'd under the founding group's 14-family GRC taxonomy, verbatim
(see UNION-SPEC.md, "Counting method"). **25 claims total.**

| Fork | Vendor / Product | Claims |
|---|---|---|
| FR2701557058 | 38North Security, LLC / Northwatch | 3 |
| FR2628647239 | Advent Business Company Inc. / Enablement® | 4 |
| FR2635930439 | Advent Business Company Inc. / Enablement® | 4 |
| FR2628943633 | Boundera / Boundera SaaS | 2 |
| FR2631258122 | Cahill Swift, LLC / Cahill Swift Compliance Management Platform | 1 |
| FR2631258125 | Certivo, Inc. / Certivo Compliance Platform | 0 |
| FR2630354485 | ComplianceAid INC. / ComplianceAide Government Cloud | 1 |
| FR2633957422 | MediaLab Solutions LLC / Vastian (MediaLab by Vastian) | 0 |
| FR2631054539 | Mycroft Technologies Inc / Mycroft GRC Platform | 5 |
| FR2632558735 | Ocasio Convergence Holdings LLC / Axiom Convergence Engine (ACE) | 0 |
| FR2700754082 | PlatformOne Group Inc / ComplianceONE | 2 |
| FR2700137045 | RegScale, Inc. / RegScale Trust Center 20x (Class C) | 0 |
| FR2629068830 | SunStone Secure, LLC / SunStone Artemis Platform | 0 |
| FR2633053629 | TGuardAI Inc. / TrustGuard AI Compliance Platform | 3 |
| FR2630354484 | VisualVault LLC / VisualVault Cloud | 0 |

Six forks claim **zero** functions under the verbatim taxonomy and
are reported plainly — among them RegScale's Trust Center, a
flagship GRC product whose "continuous controls monitoring" is an
adjacency, not the family's phrase. One raw hit was removed by the
exclusion pass (ComplianceAide's `assessment_authorization`: its
only `assessor` evidence sits inside the sentence where the
offering states it does not replace an independent assessor).
Details in `scratch/ARTIFACTS.md`.

## The Core (10 functions)

Python standard library only. Statuses that depend on dates are
**derived at read time, never stored**; records hold opaque
references only (no names, emails, or other PII); the audit log is
append-only and records denied attempts too.

1. **Framework & control catalog registry** — frameworks and their
   controls, seeded with the NIST SP 800-53 catalog (21 controls).
2. **Governed-system registry** — systems keyed by opaque
   caller-supplied references; names are labels, never keys.
3. **Indicator registry + recorded results** — security indicators
   (KSI-style) linked to controls, with results recorded verbatim
   (status written by the recorder, never computed).
4. **Evidence registry** — evidence records with metadata and a
   SHA-256 of supplied content; verification is by content, and an
   artifact's validation status is a recorded field set by an
   authorized reviewer, never computed.
5. **Finding / remediation (POA&M-style) records** — findings with
   a severity recorded verbatim, a source, a due date, and a
   lifecycle enforced by a transition table (`open → in_progress →
   remediated → validated → closed`, plus `open / in_progress →
   accepted_risk`, which requires a recorded rationale). Any
   date-based status such as **overdue is derived at read time**
   from due date + lifecycle state + an as-of date — it is never
   stored on the record.
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

**130 tests, OK** at delivery (118 carried from the founding group +
12 new spec tests), including a mutation-verified negative control:
the category's signature derivation drill (finding overdue status
derived at read time) was re-run in this tree — patching the
derivation so the overdue branch never fires produced **exactly 8
failures**, all in the derivation chain, and `store.py` was restored
byte-identical (SHA-256 verified) with the suite green again. Full
record in [tests/README.md](tests/README.md).

## Core accounting

The substrate is carried from the founding group, **groups/grc-l2**:

| Component | Carried | Byte-identical |
|---|---|---|
| `src/grc/` (8 modules: `__init__`, `__main__`, access, audit, catalog, errors, service, store) | yes | **8/8** (SHA-256 verified against the founding group) |
| Test modules (13) + `grc_helpers.py` + `tests/__init__.py` + `store.py.premutation` | yes | identical except the `grc_helpers.py` docstring, relabeled to this set |
| `test_additions.py` (founding group) | **no** — it pins the `addition:grc-l2` unit specifically | — |
| `tests/test_specs.py` | new | pins this set: membership, tier discipline, 25 claims, family counts, zero-claim set, the one exclusion removal, the duplicate pair |

Docs (this README, UNION-SPEC.md, tests/README.md) are re-anchored
to tier-null; the code is untouched.

## Documented control claims

This set has **no baseline**. What its forks' own descriptions
document, traced per fork in UNION-SPEC.md:

- **CA (Security Assessment and Authorization) — documented** via
  continuous monitoring (Enablement ×2, Mycroft), assessor-facing
  authorization support (Northwatch, Boundera), framework
  compliance management (Mycroft, TrustGuard AI), and KSI tracking
  (Northwatch, Enablement ×2, Boundera). Posture reporting is
  **not** documented.
- **RA (Risk Assessment) — documented in part** via risk
  management (Mycroft only). Vulnerability & remediation
  management is **not** documented.
- **AU (Audit and Accountability) — documented** via audit support
  (TrustGuard AI, "audit-ready" outputs). Evidence management is
  **not** documented as a family, despite evidence prose in nearly
  every description.
- **PM (Program Management) — documented** via policy management
  (6 forks: Northwatch, Enablement ×2, Cahill Swift,
  ComplianceAide, ComplianceONE).
- **AC / IA — not documented.** Identity & access hooks have zero
  claims in this set.
- **Not documented:** AT, CM, CP, IR, MA, MP, PE, PL, PS, SA, SC,
  SI. Nothing is filled in from any baseline.

## Honesty

- **Tier is null, plainly.** Every sheet records
  `fedramp_impact_level: "Unknown"` exactly as the source has it
  and `cmmc_tier: null`, pinned by tests. No tier is assigned, no
  baseline is claimed, no CMMC equivalence is drawn. One fork
  (Mycroft) holds FedRAMP Certified status in the source; that is
  its authorization status, recorded as such — it changes no tier.
- **Every claim traces to a fork's own sentence.** Claims exist
  only where a description fires a taxonomy family; the evidence
  sentence is stored verbatim in `specs/specs.json`. Census
  citations verifying (20/20) are not claims — only 6 of the 20
  are themselves claim evidence — and claims stand whether or not
  the census cited their sentence.
- **Wording artifacts are recorded, not corrected.** Enablement's
  `api_integrations` claim fires on the word "integration" in "No
  coding, no integration team, no consultants" and stands at that
  weight. The founding addendum's two famous artifacts (a framework
  name firing risk_management; "Authorization to Operate") were
  checked and do not arise in this set.
- **A fork's documented control language is its claim, never this
  build's attainment.** Forks in this set document scores of their
  own (Northwatch's PAIN rating, Boundera's score history,
  TrustGuard's vendor scoring); this build computes **no score
  anywhere** — posture is counts only, enforced by a recursive
  key-scan test.
- **Extended functions are named, not built:** automated evidence
  collection & validation, continuous-monitoring feeds and scanner
  integrations, vulnerability scanning, automated KSI validation,
  posture & risk scoring engines, hosted enclave & PaaS operations,
  FedRAMP package generation, policy lifecycle engine, agentic
  workflow execution, AI control-narrative generation, and a
  data-integration connector engine — plus fork excess (healthcare
  quality suite, AI/ML governance evaluation, digital-twin OSCAL
  analysis, no-code BPM platforms). Full list in UNION-SPEC.md.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo users for the RBAC matrix; there is
  no identity provider, no credential store, and no real
  authentication in this build.
