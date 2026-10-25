# Union Spec — Analytics, CMMC L2 (DeadRamp Phase 2, Group 1)

The merged functional spec for the largest sibling group on the map: **128 forks**,
category **Analytics**, CMMC tier **L2** (every member is FedRAMP **Moderate** in
`forks.json` — verified, so the group is single-tier and the merge takes the
group baseline in full, per Merge Rule 2).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 128 entries, each
with the offering's full public marketplace description and its function claims
tagged from that description, every claim carrying the source sentence as
evidence. Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services Administration,
last change 2026-10-22), product records joined by FedRAMP ID.

## How functions were counted

A fixed 24-function taxonomy was matched against each offering's own public
description. A function is claimed for a fork **only** when the description
contains matching text; the matching sentence is stored as the claim's evidence
in the spec sheet. 115 of 128 offerings carry at least one tagged claim; 13
descriptions are deployment/marketing prose with no functional claim in
taxonomy terms (their full text is still in the spec sheets — nothing is
hidden, and no function was invented for them). Counts below are therefore a
**floor**, not a ceiling, on what these products do.

## Function ranking — all 128 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Statistical / predictive / ML & AI analysis | 45 | 35% | **Core slice**: descriptive statistics & aggregation (see below). Predictive/ML remainder: Extended |
| 2 | Reporting | 37 | 29% | **Core** |
| 3 | Alerts, monitoring & detection | 36 | 28% | Extended |
| 4 | Visualization & dashboards | 33 | 26% | **Core** |
| 5 | Real-time & streaming analytics | 29 | 23% | Extended |
| 6 | Data storage / warehouse / lake | 27 | 21% | **Core** |
| 7 | Sharing & collaboration | 21 | 16% | Extended |
| 8 | Connectors & source integration | 20 | 16% | **Core slice**: open-format file ingest (CSV/JSON). Proprietary-source connectors: Extended |
| 9 | Data ingest & collection | 19 | 15% | **Core** |
| 10 | Access control & authentication | 19 | 15% | **Core** (L2 baseline hooks) |
| 11 | Audit logging & trails | 18 | 14% | **Core** (L2 baseline hooks) |
| 12 | Query & search | 16 | 13% | **Core** |
| 13 | Data transformation & preparation | 14 | 11% | Extended |
| 14 | Data governance, catalog & metadata | 13 | 10% | Extended (dataset registry in Core storage is the seed) |
| 15 | Geospatial analysis | 13 | 10% | Extended |
| 16 | API access | 12 | 9% | **Core** (the service is API-first) |
| 17 | Encryption | 11 | 9% | Platform note (TLS supported; see below) |
| 18 | Text & natural-language analytics | 9 | 7% | Extended |
| 19 | Archiving & retention | 7 | 5% | Extended |
| 20 | Business intelligence / self-service | 7 | 5% | Extended |
| 21 | KPI & performance management | 6 | 5% | Extended |
| 22 | Data export | 5 | 4% | **Core** (delivered with Reporting; low tag count is a description-wording artifact — siblings say "share"/"deliver" where this build says export) |
| 23 | Scheduling & workflow automation | 2 | 2% | Extended |
| 24 | Image / video / media analytics | 1 | 1% | Extended |

**Differences are preserved, not averaged away**: the long tail above (geospatial,
text analytics, media analytics, KPI scorecards, streaming, alerting) is the
record of how the siblings differ. Each Extended function names the claim family
and its sibling count; the per-fork spec sheets name which siblings claim it.

## The Core — what the merged build implements (10 functions)

One coherent, standards-based analytics service that every sibling's platform
presupposes, built clean-room from this spec:

1. **Ingest** — load datasets from open formats (CSV, JSON) into the store.
2. **Storage** — a dataset registry: named datasets with inferred schema,
   row counts, and provenance (who loaded it, when).
3. **Query & search** — tabular query over a dataset: column selection,
   filters (`eq, ne, lt, le, gt, ge, in, contains`), grouping, ordering, limit.
4. **Descriptive statistics** (core slice of the #1 claim family) — aggregations
   `count, sum, avg, min, max, stddev` in queries, plus a per-column
   `describe` (count, mean, median, min, max, stddev). Predictive modeling and
   ML are Extended, not silently implied.
5. **Visualization** — charts rendered from query results as standalone SVG
   (bar, line, pie). No JavaScript, no external assets.
6. **Reporting** — a report bundle: an HTML report composed of titled sections
   (tables and charts), generatable from query results.
7. **Export** — datasets and query results out as CSV or JSON.
8. **API access** — every function above is exposed over a REST API (JSON),
   so the service composes with anything that speaks HTTP.
9. **Access control** — role-based access hooks: roles `admin`, `analyst`,
   `viewer` with a permission matrix enforced on every operation
   (ingest / query / export / audit-read / admin).
10. **Audit log** — an append-only audit trail: every ingest, query, export,
    chart, report, and denied attempt is recorded with actor, action, target,
    and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline (the FedRAMP
  Moderate tailoring), cross-walked to the 110 practices of NIST SP 800-171
  Rev. 2 that define CMMC L2. All 128 parent forks sit at Moderate, so the
  union baseline is the Moderate baseline, un-diluted (Merge Rule 1) and
  inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control hooks → **AC** (AC-2 account management, AC-3 access
    enforcement, AC-6 least privilege), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity provider).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit records,
    AU-6 audit review, AU-9 protection of audit information — append-only
    store, admin-only read).
  - Ingest / query / export → **SI** (SI-10 information input validation —
    malformed input is rejected, never partially applied) and **SC** (SC-8
    transmission confidentiality — the server runs over TLS when a
    certificate is configured; encryption at rest is a deployment-layer
    control, stated plainly, not claimed here).
- **Caveat, same as the crosswalk's:** this mapping states which baseline
  families the build's features answer to. It is not a FedRAMP authorization
  and not a CMMC certification, and it does not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `analytics` under `src/`,
runnable and testable with `PYTHONPATH=src`.

- `analytics/access.py` — `User(name, role)`; roles `admin|analyst|viewer`;
  `PERMISSIONS`: admin ⊇ {ingest, query, export, audit_read, admin},
  analyst = {ingest, query, export}, viewer = {query, export};
  `require(user, action)` raises `PermissionDenied`.
- `analytics/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns the list of entry dicts with
  keys `ts, actor, action, target, details`. Append-only; optional JSONL file.
- `analytics/store.py` — `DatasetStore(audit=None)`; `.ingest_csv(name, text,
  actor)`, `.ingest_json(name, text, actor)` → dataset dict
  `{id, name, columns, row_count, created_by, created_utc}`; ids are
  sequential strings `"ds-1"`, `"ds-2"`, …; `.get(dataset_id)`,
  `.list()`, `.rows(dataset_id)`. Malformed input raises `ValidationError`
  and changes nothing.
- `analytics/query.py` — `run_query(store, dataset_id, query, actor)` →
  `{columns, rows, row_count}` where `query` may contain `select`,
  `where` (`{column, op, value}`), `group_by`, `aggregates`
  (`{func, column, alias}`, funcs `count|sum|avg|min|max|stddev`),
  `order_by` (`{column, direction}`), `limit`.
  `describe(store, dataset_id, column, actor)` →
  `{column, count, mean, median, min, max, stddev}` over the numeric values
  of the column.
- `analytics/charts.py` — `chart_svg(result, label_column, value_column,
  kind="bar", title="")` → standalone SVG string; kinds `bar|line|pie`.
- `analytics/reports.py` — `result_to_csv(result)`, `result_to_json(result)`,
  `report_html(title, sections)` where each section is
  `{heading, table: result|None, chart_svg: str|None}` → HTML string.
- `analytics/service.py` — `make_server(host, port, store, audit, users)` →
  `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth via
  `X-User` / `X-Role` headers (role must match the registry). Endpoints:
  `GET /health`, `GET /datasets`, `POST /datasets`
  `{name, format: csv|json, data}`, `GET /datasets/{id}`,
  `POST /datasets/{id}/query`, `POST /datasets/{id}/describe` `{column}`,
  `GET /datasets/{id}/export?format=csv|json`,
  `GET /datasets/{id}/chart?kind=&label=&value=`,
  `GET /audit`. Errors are JSON `{error}` with 400/401/403/404 as applicable.
  Denied attempts are audited.
- `analytics/__main__.py` — `python -m analytics serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=analyst, carol=viewer` (documented as demo identities;
  production identity is the embedding organization's, per IA-2 above).
- `analytics/errors.py` — `AnalyticsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`), each test docstring naming the
core function / spec claim it traces to, and include a **negative control**:
a mutant aggregation (avg computed as sum, ignoring the divisor) that the
canonical expectation is shown to reject — proving the suite catches that
defect class rather than merely passing.

## Coverage statement (for this build)

- Specs: 128 / 128 forks spec'd.
- Core: 10 core functions implemented, each with tracing tests.
- Extended: 14 functions specified and ranked, **not** implemented in this
  build; predictive ML (the remainder of the #1 claim family), streaming,
  alerting, collaboration, transformation, governance beyond the registry,
  geospatial, text, media, KPI, archiving, and scheduling remain open work,
  named here rather than implied done.
