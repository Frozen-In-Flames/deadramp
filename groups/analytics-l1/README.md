# Analytics L1 — merged build (Operation DeadRamp, Phase 2, Group 7)

This is the merged, clean-room implementation of the **Analytics L1**
sibling group: **16 forks** from the FedRAMP Marketplace that share the
same function (Analytics) and the same trust tier (CMMC L1), built as one
open-source service per the group's union spec,
[`UNION-SPEC.md`](UNION-SPEC.md).

This is the map's lightest tier, and the only group that mixes two FedRAMP
impact levels: **6 forks are FedRAMP Low** (AchieveIt, the AHA Precision
Medicine Platform, Gemini for Government, Perplexity Enterprise, CMAP,
zLinkFM) and **10 are LI-SaaS** — FedRAMP's tailored subset of the Low
baseline for SaaS. Each fork's actual impact level is recorded in its spec
sheet ([`specs/specs.json`](specs/specs.json)). The group's union baseline
is the Low baseline, taken in full.

It was written from the contract in the union spec: original code, no
vendor code, assets, or branding from any of the 16 sibling offerings.
Python 3, **standard library only**, no external dependencies.

**Reuse, stated plainly:** the implementation and test suite are the
shipped Group 1 (Analytics L2) build's code, reused in full — this
project's own Apache-2.0 code. A per-file hash comparison is recorded in
`scratch/reuse-note.md`: all 10 `src/` modules and 11 of 13 test files are
byte-identical to Group 1's; the two differing files are documentation
wording only. **The baseline claim is not reused.** Everything Group 1
says about Moderate / NIST SP 800-171 stays in Group 1. This group's
claims are the Low baseline's and FAR 52.204-21's only, as written in
`UNION-SPEC.md`.

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

Tests live in `tests/` (standard library `unittest`), maintained against
the contract in `UNION-SPEC.md`, and include the mutation-verified
negative control (see `tests/README.md` for the drill record):

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

136 tests.

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the **NIST SP 800-53 Rev. 5 Low baseline**
(the FedRAMP Low tailoring; LI-SaaS is its tailored subset), cross-walked
to the **FAR 52.204-21** practices that define CMMC L1:

- **AC / IA** — access control hooks: AC-2 (account management), AC-3
  (access enforcement); IA-2 (identification & authentication — identity
  is supplied by the embedding organization via user/role headers; this
  service ships hooks, not an IdP). On the FAR side: limit system access
  to authorized users, transactions, and functions; identify and
  authenticate users, processes, and devices.
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records); append-only store, audit-read restricted to the `audit_read`
  permission. **This mapping is FedRAMP-Low-side only:** FAR 52.204-21 /
  CMMC L1 has no audit practice, so no audit claim is made on the CMMC
  side, and Group 1's Moderate-level audit citations are not imported.
- **SI / SC** — ingest / query / export: SI-10 (information input
  validation — malformed input is rejected, never partially applied);
  SC-8 (transmission confidentiality — the server runs over TLS when a
  certificate is configured; encryption at rest is a deployment-layer
  control, stated plainly and not claimed here).

## Honesty: what is NOT in this build

The union spec ranks the group's claimed functions from
`specs/specs.json`; 10 platform functions are implemented here. The
following **Extended functions are specified and ranked in
`UNION-SPEC.md` but are NOT implemented** in this build (registered in
the repo's `GAPS.md` final batch when this group ships):

- Real-time & streaming analytics (8 of 16 siblings claim it — this
  group's joint-largest family, and its largest gap)
- Alerts, monitoring & detection (3)
- Sharing & collaboration (3)
- Proprietary-source connectors (5 claim the connectors family; core
  ingest covers open CSV/JSON only)
- Predictive modeling / ML & AI analysis (the remainder of the
  statistics/ML family, 5 claimants, beyond descriptive statistics —
  claimed here by frontier-AI platforms; this build does not pretend
  to be one)
- Archiving & retention (2)
- Data transformation & preparation (1)
- Text & natural-language analytics (1)

Also, plainly:

- **Two spec sheets carry zero tagged claims** (Melissa GovCloud Address
  Suite, zLinkFM): their marketplace descriptions contain no functional
  claim in taxonomy terms. Their full text is in the spec sheets and no
  function was invented for them; all function counts are a floor.
- **Seven taxonomy functions are claimed by no sibling in this group**
  (geospatial, governance, encryption, KPI, BI/self-service, scheduling,
  media analytics). They are absent from this group's union entirely —
  they belong to the Moderate/High Analytics groups' unions, not this
  one's, and are not gaps here. TLS support is a property of the service;
  no sibling in this group claims an encryption function and none is
  claimed for it.
- **Platform-layer baseline items gap-listed, not claimed:** encryption
  at rest (deployment layer); production identity and authentication
  strength (the demo identities `alice`, `bob`, `carol` are **hooks, not
  an identity provider** — account lifecycle belongs to the embedding
  organization); TLS only when a certificate is configured.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which Low-baseline families the build's features answer
  to; nothing more. The Moderate/High apparatus of the sibling Analytics
  groups (800-171 depth, the L3 audit-chain uplift, 800-172-derived
  enhancements) is **not** inherited downward into this tier.
