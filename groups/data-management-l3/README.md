# Data Management L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 28)

This is the merged, clean-room implementation of the **Data
Management L3-adjacent** sibling group: **2 forks / vendor
platforms** from the FedRAMP Marketplace that share the same
function (Data Management) and the same trust tier (CMMC
L3-adjacent, equivalent to FedRAMP High), built as one open-source
service from the group's union contract (`UNION-SPEC.md`).

The group: **US Axon FedCloud - High** (Axon) and **Kiteworks Secure
Gov Cloud** (Kiteworks USA, LLC).

It is a **cross-tier merge**: the merged build of Group 12 (Data
Management L2, 8 forks) carried up whole under the Merge Rule —
union of baselines, highest tier inherited in full — and uplifted to
the High baseline. It was written from the two groups' contracts
only: original code, no vendor code, assets, or branding from any
sibling offering. Python 3, **standard library only**, no external
dependencies.

## The 12 core functions

1. **Dataset registry** — datasets (`ds-`) with owner, classification
   (`public` / `internal` / `cui` / `phi`), tags, and a versioned
   schema (each field: name, type, required, sensitive). Updating
   the schema increments `schema_version`.
2. **Catalog search** — literal, case-insensitive substring search
   over datasets (name, description, tags, schema field names),
   sources, and quality rules.
3. **Source registry** — data sources (`src-`) by kind (`file`,
   `database`, `api`, `stream`, `manual`) with a location.
4. **Ingestion records** — ingestion runs (`ing-`) recording dataset,
   source, mode (`full` / `incremental` / `stream`), record counts,
   checksum, and `completed` / `failed` status.
5. **Provenance view** — for any dataset: the sources that fed it,
   its ingestion runs, and its total records over completed runs.
6. **Data quality** — quality rules (`qr-`) of five kinds
   (`completeness`, `uniqueness`, `format`, `range`, `freshness`)
   and check runs (`qc-`) evaluating a rule against a supplied batch
   of records with deterministic violation semantics.
7. **Access governance** — purpose-bound access requests (`ar-`),
   decisions by someone who is never the requester, time-boxed
   grants (`gr-`) on approval, active-grant queries, and revocation.
8. **Retention schedules** — one retention policy (`rp-`) per dataset
   (retention days, disposition `delete` / `archive` / `review`,
   legal hold) plus a due evaluation against the dataset's latest
   completed ingestion (or its creation).
9. **Export manifests** — export records (`ex-`) with format, record
   count, schema version, and a SHA-256 checksum of the canonical
   record set when records are supplied.
10. **REST API** — every function above over a JSON REST API, with
    unsuccessful-logon lockout (AC-7, below).
11. **RBAC** — roles `admin`, `steward`, `viewer`, and `auditor`
    with a permission matrix enforced on every operation (see
    below).
12. **Append-only, hash-chained audit log** — every mutation, every
    search, and every denied attempt, with actor, action, target,
    and UTC timestamp, plus a SHA-256 hash chain (`seq`, `prev_hash`,
    `hash`) over every entry: tamper-evident, verifiable via
    `GET /audit/verify`, searchable via `GET /audit` filters, and
    fail-closed (a failed audit write rolls the operation back).
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

## High-baseline uplifts (over the Group 12 L2 build)

- **Hash-chained tamper-evident audit (AU-9/AU-3)** — every entry is
  chained to its predecessor; `verify_chain()` localizes the first
  bad entry; exposed as `GET /audit/verify`.
- **Fail-closed audit writes (AU-5)** — if the audit write fails,
  the audit append rolls back, the store rolls the whole operation
  back (no object, no change, no id consumed), and the error
  propagates: the operation does not proceed.
- **Audit query / reduction (AU-7)** — `GET /audit` accepts
  `actor`, `action`, `target`, `since`, and `until` filters.
- **Logon lockout (AC-7)** — per-username consecutive-failure
  tracking; at `--max-failed-logins` (default 3) the username locks
  for `--lockout-seconds` (default 300); locked attempts get 403
  and are audited as `auth:locked`; a success resets the counter.
- **Auditor role (AC-5)** — `auditor` holds `audit_read` and
  nothing else, so audit review is a duty separable from
  administration and stewardship.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `ds-`, `src-`,
`ing-`, `qr-`, `qc-`, `ar-`, `gr-`, `rp-`, `ex-`.

## Run

```bash
cd groups/data-management-l3
PYTHONPATH=src python3 -m datamgmt serve            # http://127.0.0.1:8792
PYTHONPATH=src python3 -m datamgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m datamgmt serve --certfile cert.pem --keyfile key.pem   # TLS
PYTHONPATH=src python3 -m datamgmt serve --max-failed-logins 3 --lockout-seconds 300   # AC-7 knobs
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | steward | all reads except the audit log; all writes incl. access decisions |
| `carol` | viewer | reads (except the audit log) and requesting access |
| `dana` | auditor | read the audit log and verify its chain — nothing else |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin/auditor; `{"entries": [...]}`; optional `?actor=&action=&target=&since=&until=` filters (AU-7) |
| `GET /audit/verify` | audit_read | admin/auditor; `{"ok": bool, "entries": n, "first_bad_index": i\|null}` (AU-9) |
| `GET /search?q=` | catalog_read | `{"datasets": [...], "sources": [...], "quality_rules": [...]}` |
| `GET /datasets` · `POST /datasets` | dataset_read / dataset_write | create → 201 |
| `GET /datasets/{id}` · `POST /datasets/{id}` | dataset_read / dataset_write | POST updates metadata |
| `POST /datasets/{id}/schema` | dataset_write | bumps `schema_version` |
| `GET /datasets/{id}/ingestions` · `POST` | ingest_read / ingest_record | |
| `GET /datasets/{id}/provenance` | ingest_read | sources + runs + total records |
| `GET /datasets/{id}/quality-rules` · `POST` | quality_read / quality_write | |
| `GET /datasets/{id}/access-requests` · `POST` | access_read / access_request | |
| `GET /datasets/{id}/exports` · `POST` | dataset_read / export | |
| `GET /datasets/{id}/retention-policy` · `POST` | retention_read / retention_write | GET 404s when no policy set |
| `GET /sources` · `POST /sources` · `GET /sources/{id}` | source_read / source_write | |
| `GET /ingestions/{id}` | ingest_read | |
| `GET /quality-rules/{id}` | quality_read | |
| `POST /quality-rules/{id}/checks` · `GET` | quality_run / quality_read | body `{"records": [...], "now": ...}` |
| `GET /quality-checks/{id}` | quality_read | |
| `GET /access-requests` · `GET /access-requests/{id}` | access_read | |
| `POST /access-requests/{id}/decide` | access_decide | body `{"approve": true, "reason": ...}`; never the requester |
| `GET /grants` (`?dataset_id=`, `?grantee=`) · `GET /grants/{id}` | access_read | |
| `POST /grants/{id}/revoke` | access_decide | |
| `GET /retention-policies` · `GET /retention-policies/{id}` · `POST /retention-policies/{id}` | retention_read / retention_write | POST updates |
| `GET /retention-due` (`?now=`) | retention_read | `{"due": [...]}` |
| `GET /exports/{id}` | dataset_read | |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission (and for a locked account, AC-7),
404 not found. Denied attempts are audited with the action suffixed
`:denied`; locked attempts are audited as `auth:locked`.

## Tests

```bash
cd groups/data-management-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 239 tests
```

**239 tests, all passing**, including two mutation-verified
negative controls: disabling the self-approval guard in the real
store makes exactly 4 tests fail, and mutating a stored audit entry
in place makes `verify_chain()` fail at exactly that entry's index
(see `tests/README.md` for the drill records).

## Honesty

- The build implements the governance substrate the two groups'
  public descriptions actually share. The engines are not in it: no
  storage or database engine, no integration runtime, no
  record-linkage cryptography, no search index, no OCR, no cluster
  provisioning, no hosting, and neither member's domain depth
  (Axon's evidence platform and device fleet control; Kiteworks'
  transfer transports and possessionless editing). Each is named as
  an Extended gap in `UNION-SPEC.md` for the final batch.
- Provenance is at ingestion granularity — which sources fed which
  dataset, when, and how much. Field-level or transformation
  lineage is not claimed; no sibling description at either tier
  claims it either.
- Retention is scheduled and reported, not executed: the build
  computes what is due; deletion/archival belongs to the embedding
  deployment. Audit-log retention (AU-11) is likewise not enforced
  in this build and is gap-listed, not implied.
- Quality check runs evaluate the records supplied in the call
  against registered rules. The build does not reach into any live
  dataset store — there is none in it.
- Demo identities are hooks, not an identity provider. IA-2 (and
  MFA-grade authentication, IA-2(1)/(2) / IA-5) stays with the
  embedding organization. Python's standard library is not a
  FIPS-validated cryptographic module (SC-13), and FIPS validation
  is **not claimed** — one sibling claims FIPS 140-3 validated
  modules as a product feature; this build does not inherit that
  claim. Encryption is TLS when a certificate is configured;
  encryption at rest is a deployment-layer property. The deployment
  is a single-tenant reference deployment.
- Claims discipline: every function above traces to a sibling claim
  in `specs/specs.json` (6 evidenced claims across 2 forks, after 1
  documented wording-artifact correction, with 6 near-misses
  recorded in `scratch/ARTIFACTS.md`) or to the High/L3-adjacent
  control families in `UNION-SPEC.md`. Thirteen taxonomy families
  tag zero claims in this group and stand in the union under the
  recorded core-boundary decision (the Merge Rule carries the L2
  union upward whole). Counts are a floor, stated as such.
