# Analytics L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 3)

This is the merged, clean-room implementation of the **Analytics
L3-adjacent** sibling group: **54 forks** from the FedRAMP Marketplace
that share the same function (Analytics) and the same trust tier (CMMC
L3-adjacent, equivalent to FedRAMP **High**), built as one open-source
service per the group's union spec, [`UNION-SPEC.md`](UNION-SPEC.md).

## Lineage and reuse (read this first)

This build is a **cross-tier merge** under Operation DeadRamp's Merge
Rule. One parent is the shipped Group 1 build
([`../analytics-l2/`](../analytics-l2/)), itself the union of the 128
Analytics L2 (FedRAMP Moderate) forks. The other parent is this group's
54 High forks. The merge takes the union of the baselines and inherits
the **highest tier in full** — so this tree is Group 1's service,
**uplifted to the FedRAMP High baseline**, extended by this group's spec
sheets.

Reuse is explicit: Group 1's code is our own (Apache-2.0). Four modules
are byte-identical to Group 1 (`__init__.py`, `charts.py`, `query.py`,
`reports.py`); six are modified for the uplift (`audit.py`, `access.py`,
`service.py`, `store.py`, `errors.py`, `__main__.py`). No vendor code,
assets, or branding from any of the 54 sibling offerings is used.
Python 3, **standard library only**, no external dependencies.

## The 10 core functions (at the High baseline)

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
   `analyst`, `viewer`, plus the High-baseline `auditor` role, with a
   permission matrix enforced on every operation and unsuccessful-logon
   lockout at the service layer.
10. **Audit log** — an append-only, **hash-chained, tamper-evident**
    audit trail: every ingest, query, describe, export, and chart
    operation, and every denied attempt (recorded with the action
    suffixed `:denied`), with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence.

## What the High baseline added (the uplifts)

- **Hash-chained audit (AU-9, AU-3)** — each entry carries a sequence
  number and a SHA-256 hash linked to the previous entry's hash.
  `GET /audit/verify` (or `AuditLog.verify_chain()`) recomputes the
  chain and localizes the first tampered entry.
- **Fail-closed audit writes (AU-5)** — if the audit file write fails,
  the operation fails with it: the in-memory append is rolled back, the
  dataset commit is rolled back, and `AuditWriteError` propagates. The
  service never proceeds unaudited.
- **Audit search & reduction (AU-7)** — `GET /audit` accepts `actor`,
  `action`, `since`, and `until` filter parameters.
- **Logon lockout (AC-7)** — consecutive authentication failures are
  tracked per username; at the threshold (default 3) the username locks
  for a window (default 300 s), locked attempts get 403 and are audited
  as `auth:locked`, and a success resets the counter.
- **Separation of duties (AC-5, technical slice)** — the `auditor` role
  holds `audit_read` and nothing else: audit review is a duty separable
  from administration.

Malformed ingest input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no dataset id
consumed) — as in Group 1.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m analytics serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), `--certfile FILE
--keyfile FILE` to serve over TLS (standard library `ssl`), and
`--max-failed-logins N` / `--lockout-seconds S` for the AC-7 lockout. A
startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | ingest, query, export, audit_read, admin     |
| `bob`   | analyst | ingest, query, export                        |
| `carol` | viewer  | query, export                                |
| `dana`  | auditor | audit_read                                   |

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
| GET | `/audit` | audit_read | `{"entries": [...]}`; optional filters `?actor=&action=&since=&until=` |
| GET | `/audit/verify` | audit_read | `{"ok": bool, "entries": n, "first_bad_index": int\|null}` |

Query dict keys: `select`, `where` (`{column, op, value}`), `group_by`,
`aggregates` (`{func, column, alias}`), `order_by`
(`{column, direction}`), `limit`. When aggregates or `group_by` are
present, `select` is ignored and the output columns are the group-by
columns plus the aggregate aliases. Numeric comparisons coerce both
sides to float when both look numeric.

Dataset dicts are `{id, name, columns, row_count, created_by,
created_utc}` with sequential ids `ds-1`, `ds-2`, …

Audit entries are `{ts, actor, action, target, details, seq, prev_hash,
hash}` — the last three are the High-baseline hash chain.

## How to run tests

Tests live in `tests/` (standard library `unittest`), maintained against
the contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

183 tests: the 136 Group 1 tests (four files minimally adapted for the
uplift — see `tests/README.md` for the adaptation list) plus 47 new
tests for the chain, audit query, fail-closed behavior, lockout, and
auditor role. Two negative controls: the avg-as-sum mutant (also
mutation-verified independently for this group: patching `avg` to
return the bare sum fails the suite) and audit-tamper detection
(mutating a stored entry makes chain verification fail at that index).

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 **High** baseline
— the CMMC L3 basis of NIST SP 800-171 Rev. 2 plus selected NIST SP
800-172 enhanced requirements:

- **AC / IA** — access control hooks: AC-2 (account management), AC-3
  (access enforcement), AC-5 (separation of duties — the `auditor`
  role), AC-6 (least privilege), AC-7 (unsuccessful logon attempts —
  lockout); IA-2 (identification & authentication — identity is
  supplied by the embedding organization via user/role headers; this
  service ships hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-5 (response to audit processing failure — fail closed),
  AU-6 (audit review), AU-7 (audit reduction & search), AU-9
  (protection of audit information — append-only, hash-chained,
  audit-read restricted to the `audit_read` permission).
- **SI / SC** — ingest / query / export: SI-10 (information input
  validation — malformed input is rejected, never partially applied);
  SC-8 (transmission confidentiality — the server runs over TLS when a
  certificate is configured; encryption at rest is a deployment-layer
  control, stated plainly and not claimed here).

## Honesty: what is NOT in this build

The union spec ranks 24 functions across the 54 siblings; 10 are
implemented here. The following **Extended functions are specified and
ranked in `UNION-SPEC.md` but are NOT implemented** in this build:

- Alerts, monitoring & detection — at 27 of 54 siblings (50%) this is
  the group's largest Extended function and the named first candidate
  for the next increment. It is Extended, not Core, because each
  sibling's alerting is bound to its own domain telemetry rather than
  to a shared dataset surface; see `UNION-SPEC.md` for the reasoning
- Predictive modeling / ML & AI analysis (the remainder of the largest
  claim family beyond descriptive statistics)
- Real-time & streaming analytics
- Sharing & collaboration
- Proprietary-source connectors (core ingest covers open CSV/JSON only)
- Data transformation & preparation
- Data governance, catalog & metadata (beyond the core dataset registry)
- Geospatial analysis
- Text & natural-language analytics
- Archiving & retention
- Business intelligence / self-service
- KPI & performance management (zero claims in this group)
- Scheduling & workflow automation
- Image / video / media analytics

Baseline gaps at High, named plainly (full analysis in
`UNION-SPEC.md`):

- **MFA and authenticator management (IA-2(1)/(2), IA-5)** are
  identity-provider properties. The demo identities (`alice`, `bob`,
  `carol`, `dana`) are **hooks, not an identity provider**; the
  embedding organization must supply MFA-grade authentication,
  account lifecycle, and authenticator management.
- **FIPS-validated cryptography (SC-13)** is **not claimed**: Python's
  standard library is not a FIPS-validated module; validated crypto is
  a platform/deployment property.
- **Encryption at rest (SC-28)** remains a deployment-layer control.
- **Audit retention enforcement (AU-11)** is not implemented; retention
  rides with the Extended archiving function.
- **Session lock / termination (AC-11, AC-12)** are not implemented:
  the service authenticates per request and holds no session state;
  session management belongs to the embedding layer.
- Separation of duties is implemented only as its technical slice (the
  `auditor` role); who may hold which role is the embedding
  organization's policy.

This build is **not a FedRAMP authorization and not a CMMC
certification**, and it does not claim either. The control mapping
above states which baseline families the build's features answer to;
nothing more.
