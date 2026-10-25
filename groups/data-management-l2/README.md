# Data Management L2 — merged build (Operation DeadRamp, Phase 2, Group 12)

This is the merged, clean-room implementation of the **Data Management
L2** sibling group: **8 forks / vendor platforms** from the FedRAMP
Marketplace that share the same function (Data Management) and the
same trust tier (CMMC L2, equivalent to FedRAMP Moderate), built as
one open-source service from the group's union contract
(`UNION-SPEC.md`).

It was written from that contract only: original code, no vendor
code, assets, or branding from any sibling offering. Python 3,
**standard library only**, no external dependencies.

## The 12 core functions

1. **Dataset registry** — datasets (`ds-`) with owner, classification
   (`public` / `internal` / `cui` / `phi`), tags, and a versioned
   schema (each field: name, type, required, sensitive). Updating the
   schema increments `schema_version`.
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
   decisions by someone who is never the requester, time-boxed grants
   (`gr-`) on approval, active-grant queries, and revocation.
8. **Retention schedules** — one retention policy (`rp-`) per dataset
   (retention days, disposition `delete` / `archive` / `review`,
   legal hold) plus a due evaluation against the dataset's latest
   completed ingestion (or its creation).
9. **Export manifests** — export records (`ex-`) with format, record
   count, schema version, and a SHA-256 checksum of the canonical
   record set when records are supplied.
10. **REST API** — every function above over a JSON REST API.
11. **RBAC** — roles `admin`, `steward`, `viewer` with a permission
    matrix enforced on every operation (see below).
12. **Append-only audit log** — every mutation, every search, and
    every denied attempt, with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no mutation
    or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `ds-`, `src-`, `ing-`, `qr-`,
`qc-`, `ar-`, `gr-`, `rp-`, `ex-`.

## Run

```bash
cd groups/data-management-l2
PYTHONPATH=src python3 -m datamgmt serve            # http://127.0.0.1:8792
PYTHONPATH=src python3 -m datamgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m datamgmt serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | steward | all reads except the audit log; all writes incl. access decisions |
| `carol` | viewer | reads (except the audit log) and requesting access |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
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
or role mismatch, 403 permission, 404 not found. Denied attempts are
audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/data-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 196 tests
```

**196 tests, all passing**, including the mutation-verified negative
control: disabling the self-approval guard in the real store makes
exactly 4 tests fail (see `tests/README.md` for the drill record).

## Honesty

- The build implements the governance substrate the group's public
  descriptions actually share. The engines are not in it: no storage
  or database engine, no integration runtime, no record-linkage
  cryptography, no search index, no OCR, no cluster provisioning, no
  hosting. Each is named as an Extended gap in `UNION-SPEC.md` for
  the final batch.
- Provenance is at ingestion granularity — which sources fed which
  dataset, when, and how much. Field-level or transformation lineage
  is not claimed; no sibling description claims it either.
- Retention is scheduled and reported, not executed: the build
  computes what is due; deletion/archival belongs to the embedding
  deployment.
- Quality check runs evaluate the records supplied in the call
  against registered rules. The build does not reach into any live
  dataset store — there is none in it.
- Demo identities are hooks, not an identity provider. IA-2 stays
  with the embedding organization. Encryption is TLS when a
  certificate is configured; encryption at rest is a deployment-layer
  property. The deployment is a single-tenant reference deployment.
- Claims discipline: every function above traces to a sibling claim
  in `specs/specs.json` (28 evidenced claims across 8 forks, after 6
  documented wording-artifact corrections) or to the Moderate/L2
  control families in `UNION-SPEC.md`. Counts are a floor, stated
  as such.
