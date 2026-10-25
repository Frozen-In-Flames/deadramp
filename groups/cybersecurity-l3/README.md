# Cybersecurity & Risk Management — L3-adjacent (FedRAMP High)

A clean-room, standard-library-only implementation of the merged core
of the **16 FedRAMP High** offerings in the Cybersecurity & Risk
Management category — the defensive substrate they share: asset
inventory, finding ingestion and triage, deterministic risk scoring,
a risk register, NIST SP 800-53 control mapping, posture reporting,
role-based access, and an audit log.

**This group is a cross-tier merge.** Its code parent is the shipped
Cybersecurity L2 merged build (`../cybersecurity-l2/src`); per
DeadRamp's Merge Rule (union of baselines, highest tier wins), the
L2 core is carried upward whole and the platform layer is uplifted to
satisfy the **FedRAMP High** baseline in full. `UNION-SPEC.md` has
the full spec: member list, claim counts (16 forks → 60 claims), the
function ranking, the uplift analysis, and the baseline gaps.

**Reuse, stated plainly:** this package started as a copy of
`groups/cybersecurity-l2/src/cyber` (DeadRamp's own Apache-2.0 code).
Two modules are byte-identical to the parent (`__init__.py`,
`catalog.py`); six carry the High uplifts (`errors`, `audit`,
`access`, `store`, `service`, `__main__`). No vendor code, text, or
branding appears anywhere.

## The core (11 functions, at High)

1. **Asset inventory** — systems under management with owner, labels,
   lifecycle status, and a criticality rating that feeds scoring.
2. **Finding ingestion** — findings from scanners, sensors, audits,
   and humans; single, bulk, and CSV paths, bulk/CSV atomic.
3. **Finding triage & lifecycle** — fixed lifecycle with legal
   transitions enforced; assignment only to known users.
4. **Deterministic risk scoring** — severity weight × asset
   criticality weight, banded; same inputs, same score, always.
5. **Risk register** — likelihood × impact (1–25) risks with their
   own lifecycle.
6. **Control mapping & assessment** — a built-in 34-control NIST SP
   800-53 Rev. 5 catalog; per-control assessment state and evidence
   notes.
7. **Search & filtering** — full-text + faceted search across
   findings, assets, and risks with deterministic ranking.
8. **Posture reporting** — computed rollups (never stored opinions),
   JSON from the API, plain text from the CLI.
9. **API access** — the full substrate over REST JSON.
10. **Access control** — admin / analyst / viewer, plus the High
    tier's **auditor** role (audit reads only).
11. **Audit log** — append-only, and at High **hash-chained and
    tamper-evident**, **fail-closed**, and **queryable**.

## What High added (the uplift)

- **Hash-chained audit (AU-9 / AU-3)** — each entry carries `seq`,
  `prev_hash`, and `hash` (SHA-256 of the entry's canonical JSON);
  `AuditLog.verify_chain()` detects edits at the exact index;
  `GET /audit/verify` exposes it.
- **Fail-closed audit writes (AU-5)** — if the audit write fails, the
  operation rolls back entirely: no object created, no id consumed,
  no state moved. An unauditable operation does not happen.
- **Audit query / reduction (AU-7)** — `AuditLog.query(actor, action,
  target, since, until)`; `GET /audit` accepts the same filters.
- **Logon lockout (AC-7)** — per-username failure counting; locked
  after `--max-failed-logins` (default 3) for `--lockout-seconds`
  (default 300); locked attempts are audited as `auth:locked`.
- **Auditor role (AC-5)** — `dana`, holding `audit_read` and nothing
  else.

Named gaps at High (not silently skipped): MFA / authenticator
management (IA-2(1)/(2), IA-5), FIPS-validated cryptography (SC-13),
encryption at rest (SC-28), audit retention (AU-11), session lock /
termination (AC-11/AC-12). See the honesty section below.

## Run it

Python 3, standard library only. From this directory:

```sh
PYTHONPATH=src python3 -m cyber serve --host 127.0.0.1 --port 8000
PYTHONPATH=src python3 -m cyber serve --port 8443 --certfile cert.pem --keyfile key.pem
PYTHONPATH=src python3 -m cyber serve --max-failed-logins 5 --lockout-seconds 600
```

`serve` runs the API until interrupted (the CLI has no other
subcommand). TLS applies **when configured** (deployment layer).

Demo users (header auth: `X-User` + `X-Role`):

| User | Role | Permissions |
|------|------|-------------|
| `alice` | admin | all eight actions |
| `bob` | analyst | read, ingest, triage, manage_assets, manage_risks, assess_controls |
| `carol` | viewer | read |
| `dana` | auditor | audit_read |

Header auth is a documented test-harness trust model (identity is
asserted by the caller; see `UNION-SPEC.md`) — it is not an
authentication product, and at High the missing real authentication
(MFA, authenticator management) is a named gap, not a hidden one.

## API endpoints

| Method & path | Action | Permission |
|---------------|--------|------------|
| `GET /assets` · `POST /assets` | list / create assets | read / manage_assets |
| `GET /assets/{id}` · `PATCH /assets/{id}` | fetch / update one asset | read / manage_assets |
| `GET /findings` · `POST /findings` | list / ingest one finding | read / ingest |
| `POST /findings/bulk` · `POST /findings/csv` | atomic bulk ingest (JSON list / CSV text) | ingest |
| `GET /findings/{id}` | fetch one finding | read |
| `POST /findings/{id}/transition` · `POST /findings/{id}/assign` | lifecycle move / assignment | triage |
| `GET /controls` · `GET /controls/{id}` | control catalog / one control + state | read |
| `POST /controls/{id}/assess` | record an assessment | assess_controls |
| `GET /risks` · `POST /risks` | list / create risks | read / manage_risks |
| `GET /risks/{id}` · `POST /risks/{id}/transition` | fetch / lifecycle move | read / manage_risks |
| `GET /search` | full-text + faceted search (`q`, `kind`, …) | read |
| `GET /posture` · `GET /posture/text` | posture rollup (JSON / plain text) | read |
| `GET /audit` | audit entries, filterable (`actor`, `action`, `target`, `since`, `until`) | audit_read |
| `GET /audit/verify` | hash-chain verification: `{ok, entries, first_bad_index}` | audit_read |

Errors are JSON `{"error": message}` with the matching status:
400 validation, 401 authentication, 403 permission, 404 not found,
409 conflict / illegal transition. Every operation — including denied
ones — is audit-logged (and at High, an audit write that fails rolls
the operation back; see AU-5 above).

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**236 tests, all passing** — the L2 parent's 194-test suite (carried
up; three files adapted where the uplift changed behavior, listed in
`tests/README.md`) plus 42 new tests for the High uplift: the audit
hash chain and tamper detection, fail-closed writes, audit query,
and logon lockout. `tests/README.md` documents the layout, the
negative controls, and the mutation verification record (the
severity-blind scoring mutant was run against this suite: 30
failures, file restored byte-identical).

## Control families

Asset inventory → CM-8; finding ingestion/triage → RA-5, SI-2, SI-4,
IR-4; scoring & register → RA-3; control mapping → CA-2; reporting →
CA-7; access control → AC-2/3/6, AC-5 (auditor), AC-7 (lockout);
audit → AU-2/3/6/12, AU-9 (chain), AU-5 (fail-closed), AU-7 (query).
Full traceability, including which tests cite which family, is in
`UNION-SPEC.md` and `tests/README.md`.

## Honesty section — what this is not

- **Not the engines.** No vulnerability scanning, no EDR agents, no
  DLP enforcement, no SOAR, no identity products, no ML detection.
  Engines produce findings; this substrate ingests, scores, tracks,
  and reports them. The extended functions (identity products,
  endpoint management agents, DLP engines, AI/ML detection models,
  network enforcement, backup & recovery, automation engines,
  threat-intel feeds, EDR agents, cloud/SaaS posture engines,
  phishing content, fraud/identity proofing, AppSec engines, log
  pipelines, CUI enclaves/VDI, scanners) are named in `UNION-SPEC.md`
  and are **not implemented** here.
- **Not High-complete at the platform layer.** MFA / authenticator
  management (IA-2(1)/(2), IA-5), FIPS-validated cryptography
  (SC-13), encryption at rest (SC-28), audit retention (AU-11), and
  session lock/termination (AC-11/AC-12) are baseline gaps at this
  tier, registered for DeadRamp's final gap batch — named, not
  papered over. Header-asserted identity is a test-harness trust
  model, documented as such since Group 4.
- **Data lives in memory** (plus the optional JSONL audit file);
  there is no database and no persistence guarantee beyond the audit
  file. TLS applies when the operator configures certificates.
- **Not a certification.** Implementing controls drawn from the
  FedRAMP High / NIST SP 800-53 baseline does not make this software
  FedRAMP-authorized or CMMC-certified; FedRAMP authorizes products
  through its own process and CMMC certifies organizations. Tier
  labels here are planning/matching equivalences (`crosswalk.md`).
- Counts are a **floor**: functions a sibling offers but its
  marketplace description never mentions are not claimed and not
  invented (`UNION-SPEC.md`, counting method; one sibling —
  NetCloud Federal — claims zero functions in the taxonomy, and its
  sheet says so).

## Layout

```
specs/specs.json    one sheet per fork (16), claims with evidence
UNION-SPEC.md       ranking, core definition, baseline, traceability
src/cyber/          the package (stdlib only)
tests/              unittest suite + tests/README.md
scratch/            the claim extractor used to build the spec sheets
```
