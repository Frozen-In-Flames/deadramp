# Analytics L2 — merged build (Operation DeadRamp, Phase 2, Group 1)

This is the merged, clean-room implementation of the **Analytics L2**
sibling group: **128 forks** from the FedRAMP Marketplace that share the
same function (Analytics) and the same trust tier (CMMC L2, equivalent
to FedRAMP Moderate), built as one open-source service per the group's
union spec, [`UNION-SPEC.md`](UNION-SPEC.md).

It was written from the contract in that spec only: original code, no
vendor code, assets, or branding from any of the 128 sibling offerings.
Python 3, **standard library only**, no external dependencies.

## The 10 core functions

1. **Ingest** — load datasets from open formats (CSV, JSON) into the store.
2. **Storage** — a dataset registry: named datasets with inferred schema,
   row counts, and provenance (who loaded it, when).
3. **Query & search** — column selection, filters (`eq, ne, lt, le, gt,
   ge, in, contains`), grouping, ordering, and limit over a dataset.
4. **Descriptive statistics** — aggregations `count, sum, avg, min, max,
   stddev` (population) in queries, plus a per-column `describe`
   (count, mean, median, min, max, stddev) over numeric values.
5. **Visualization** — charts rendered from query results as standalone
   SVG (bar, line, pie). No JavaScript, no external assets.
6. **Reporting** — an HTML report composed of titled sections, each with
   an optional table and an optional chart.
7. **Export** — datasets and query results out as CSV or JSON.
8. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
9. **Access control** — role-based access hooks: roles `admin`,
   `analyst`, `viewer`, with a permission matrix enforced on every
   operation.
10. **Audit log** — an append-only audit trail: every ingest, query,
    describe, export, and chart operation, and every denied attempt
    (recorded with the action suffixed `:denied`), with actor, action,
    target, and UTC timestamp. Optional JSONL file persistence.

Malformed ingest input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no dataset id
consumed).

## How to run

From this directory:

```sh
PYTHONPATH=src python -m analytics serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | ingest, query, export, audit_read, admin     |
| `bob`   | analyst | ingest, query, export                        |
| `carol` | viewer  | query, export                                |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown datasets get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/datasets` | query | List datasets |
| POST | `/datasets` | ingest | Body `{"name", "format": "csv"\|"json", "data"}` → 201 dataset dict |
| GET | `/datasets/{id}` | query | One dataset dict |
| POST | `/datasets/{id}/query` | query | Body is the query dict → `{columns, rows, row_count}` |
| POST | `/datasets/{id}/describe` | query | Body `{"column"}` → descriptive statistics |
| GET | `/datasets/{id}/export?format=csv\|json` | export | `text/csv` or `application/json` |
| GET | `/datasets/{id}/chart?kind=bar\|line\|pie&label=COL&value=COL` | export | `image/svg+xml` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Query dict keys: `select`, `where` (`{column, op, value}`), `group_by`,
`aggregates` (`{func, column, alias}`), `order_by`
(`{column, direction}`), `limit`. When aggregates or `group_by` are
present, `select` is ignored and the output columns are the group-by
columns plus the aggregate aliases. Numeric comparisons coerce both
sides to float when both look numeric.

Dataset dicts are `{id, name, columns, row_count, created_by,
created_utc}` with sequential ids `ds-1`, `ds-2`, …

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are maintained
separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 Moderate baseline
cross-walked to the NIST SP 800-171 Rev. 2 practices that define CMMC L2:

- **AC / IA** — access control hooks: AC-2 (account management), AC-3
  (access enforcement), AC-6 (least privilege); IA-2 (identification &
  authentication — identity is supplied by the embedding organization
  via user/role headers; this service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit information —
  append-only store, audit-read restricted to the `audit_read`
  permission).
- **SI / SC** — ingest / query / export: SI-10 (information input
  validation — malformed input is rejected, never partially applied);
  SC-8 (transmission confidentiality — the server runs over TLS when a
  certificate is configured; encryption at rest is a deployment-layer
  control, stated plainly and not claimed here).

## Honesty: what is NOT in this build

The union spec ranks 24 functions across the 128 siblings; 10 are
implemented here. The following **Extended functions are specified and
ranked in `UNION-SPEC.md` but are NOT implemented** in this build:

- Predictive modeling / ML & AI analysis (the remainder of the largest
  claim family beyond descriptive statistics)
- Alerts, monitoring & detection
- Real-time & streaming analytics
- Sharing & collaboration
- Proprietary-source connectors (core ingest covers open CSV/JSON only)
- Data transformation & preparation
- Data governance, catalog & metadata (beyond the core dataset registry)
- Geospatial analysis
- Text & natural-language analytics
- Archiving & retention
- Business intelligence / self-service
- KPI & performance management
- Scheduling & workflow automation
- Image / video / media analytics

Further, plainly:

- The demo identities (`alice`, `bob`, `carol`) are **hooks, not an
  identity provider**. Production identity, authentication strength, and
  account lifecycle belong to the embedding organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which baseline families the build's features answer to;
  nothing more.

## Remainder additions (unit `addition:analytics-l2`)

One previously uncategorized offering — **NetComm / Beacon** — was
spec'd into this group under its existing taxonomy, applied verbatim
(see `ADDENDUM.md`). What changed: `specs/specs.json` grew from 128
to 129 sheets (the original 128 byte-for-byte untouched), adding
**2 claims**: visualization & dashboards (the toolset's named
function, a Core family) and sharing & collaboration (Extended,
fired inside the fork's own service catalogue and recorded at
catalogue weight, not counted as a gap enlargement). What did
**not** change: the implementation. The core is the same 10
functions, `src/` is byte-identical, and the tier baseline is
unchanged; the fork's remaining described surface is a back-office
service catalogue (HR / finance / property automation tools,
digital signatures, e-workflows, mobile capabilities) named as
Extended gaps in the addendum for the final batch.
