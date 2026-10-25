# Union Spec — Analytics, CMMC L1 (DeadRamp Phase 2, Group 7)

The merged functional spec for the Analytics **L1** sibling group: **16 forks**,
category **Analytics**, CMMC tier **L1**. This is the map's lightest tier, and
the only group so far that mixes two FedRAMP impact levels: **6 forks are
FedRAMP Low** and **10 are LI-SaaS**. Both map to L1 on the crosswalk
(`../../crosswalk.md`): LI-SaaS is FedRAMP's own tailored **subset** of the
Low baseline for SaaS offerings, so the union of the group's parent baselines
is the Low baseline itself, and the highest tier any parent carries is the
Low family. The group baseline is therefore the **NIST SP 800-53 Rev. 5 Low
baseline** ⇔ **CMMC L1** (the FAR 52.204-21 practice set), taken in full
(Merge Rules 1 and 2). Every member is FedRAMP Certified in `forks.json` —
verified.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 16 entries in
exactly the Group 1 schema, each with the offering's full public marketplace
description, its **actual** impact level (Low or LI-SaaS) recorded per fork,
and its function claims tagged from that description, every claim carrying
the source sentence as evidence. Sources: GSA FedRAMP Marketplace dataset
(cached at `../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by FedRAMP
ID. The member list reconciles against `MAP.md`'s "Analytics — L1 (16)"
section with zero diffs.

## How functions were counted

The fixed 24-function taxonomy from Group 1 was applied **unchanged** (same
function ids, labels, and matchers — verified byte-identical), so counts are
comparable across the Analytics groups. A function is claimed for a fork
**only** when the description contains matching text; the matching sentence
is stored as the claim's evidence. **14 of 16** offerings carry at least one
tagged claim (**54 claims** total). Two descriptions carry no functional
claim in taxonomy terms — **Melissa GovCloud Address Suite** (LI-SaaS) and
**zLinkFM** (Low); their full text is in the spec sheets, nothing is hidden,
and no function was invented for them. Counts below are a **floor**, not a
ceiling.

## Function ranking — all 16 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Reporting | 8 | 50% | **Core** |
| 1 | Real-time & streaming analytics | 8 | 50% | Extended (this group's joint-largest family; see gaps) |
| 3 | Connectors & source integration | 5 | 31% | **Core slice**: open-format file ingest (CSV/JSON). Proprietary-source connectors: Extended |
| 3 | Statistical / predictive / ML & AI analysis | 5 | 31% | **Core slice**: descriptive statistics & aggregation. Predictive/ML remainder: Extended |
| 5 | Query & search | 4 | 25% | **Core** |
| 6 | Visualization & dashboards | 3 | 19% | **Core** |
| 6 | Alerts, monitoring & detection | 3 | 19% | Extended |
| 6 | Sharing & collaboration | 3 | 19% | Extended |
| 6 | Audit logging & trails | 3 | 19% | **Core** (Low-baseline hooks; see traceability note) |
| 10 | Data ingest & collection | 2 | 13% | **Core** |
| 10 | Data export | 2 | 13% | **Core** (delivered with Reporting) |
| 10 | Access control & authentication | 2 | 13% | **Core** (Low-baseline hooks) |
| 10 | Archiving & retention | 2 | 13% | Extended |
| 14 | Data storage / warehouse / lake | 1 | 6% | **Core** (the dataset registry every sibling's platform presupposes; the low tag count is a description-wording artifact, as in Group 1) |
| 14 | API access | 1 | 6% | **Core** (the service is API-first; the single tag is Perplexity's explicit API claim — the rest of the group simply doesn't word it) |
| 14 | Data transformation & preparation | 1 | 6% | Extended |
| 14 | Text & natural-language analytics | 1 | 6% | Extended |
| 18 | Geospatial analysis | 0 | 0% | **Not claimed by any sibling in this group** — absent from this group's union (it is a Group 1/3 family, not this one's) |
| 18 | Data governance, catalog & metadata | 0 | 0% | Not claimed by any sibling in this group |
| 18 | Encryption | 0 | 0% | Not claimed by any sibling in this group (TLS support is a platform property of the service, not a sibling claim; see baseline section) |
| 18 | KPI & performance management | 0 | 0% | Not claimed by any sibling in this group |
| 18 | Business intelligence / self-service | 0 | 0% | Not claimed by any sibling in this group |
| 18 | Scheduling & workflow automation | 0 | 0% | Not claimed by any sibling in this group |
| 18 | Image / video / media analytics | 0 | 0% | Not claimed by any sibling in this group |

**Differences are preserved, not averaged away**: the Extended rows and the
zero-claim rows are the record of how this small, light-tier group differs
from its Moderate and High siblings — dominated by reporting and real-time
operational dashboards (energy, facilities, EV charging, social listening),
plus two frontier-AI platforms (Gemini for Government, Perplexity) whose
claims land in the statistics/ML and query families. The per-fork spec
sheets name which siblings claim what.

## The Core — what the merged build implements (10 functions)

The same coherent, standards-based analytics platform the other Analytics
groups are built on — every sibling's platform presupposes it:

1. **Ingest** — load datasets from open formats (CSV, JSON) into the store.
2. **Storage** — a dataset registry: named datasets with inferred schema,
   row counts, and provenance (who loaded it, when).
3. **Query & search** — tabular query over a dataset: column selection,
   filters (`eq, ne, lt, le, gt, ge, in, contains`), grouping, ordering, limit.
4. **Descriptive statistics** (core slice of the statistics/ML claim
   family) — aggregations `count, sum, avg, min, max, stddev` in queries,
   plus a per-column `describe` (count, mean, median, min, max, stddev).
   Predictive modeling and ML are Extended, not silently implied — this
   matters here, where the family's claimants are AI platforms: the build
   does not pretend to be one.
5. **Visualization** — charts rendered from query results as standalone SVG
   (bar, line, pie). No JavaScript, no external assets.
6. **Reporting** — a report bundle: an HTML report composed of titled
   sections (tables and charts), generatable from query results.
7. **Export** — datasets and query results out as CSV or JSON.
8. **API access** — every function above is exposed over a REST API (JSON),
   so the service composes with anything that speaks HTTP.
9. **Access control** — role-based access hooks: roles `admin`, `analyst`,
   `viewer` with a permission matrix enforced on every operation
   (ingest / query / export / audit-read / admin).
10. **Audit log** — an append-only audit trail: every ingest, query, export,
    chart, report, and denied attempt is recorded with actor, action,
    target, and UTC timestamp.

**Reuse, stated explicitly (per the build order for this group):** the
implementation in `src/` and the suite in `tests/` are the shipped Group 1
(Analytics L2) code, reused in full — it is this project's own Apache-2.0
code, and a per-file hash comparison (recorded in
`scratch/reuse-note.md`) shows all 10 `src/` modules and 11 of 13 test
files byte-identical to Group 1's; the two differing files are
documentation wording only (the helpers' module docstring and
`tests/README.md`). **What is NOT reused is the baseline claim.** Group 1's
Moderate / 800-171 framing does not carry over: this group's spec, traceability,
and README are written against the Low baseline and FAR 52.204-21 only, and
no control is claimed here on the strength of Group 1's spec.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** and **LI-SaaS** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the FedRAMP
  Low tailoring; LI-SaaS is a tailored subset of it), cross-walked to the
  FAR 52.204-21 practices that define CMMC L1. Derivation per the Merge
  Rule: union of parent baselines = Low (the LI-SaaS subset adds nothing
  beyond it), inherited in full.
- **Feature → control family mapping (this build, at the Low baseline):**
  - Access control hooks → **AC** (AC-2 account management, AC-3 access
    enforcement; FAR 52.204-21's access-limitation practices: limit system
    access to authorized users and to the transactions and functions they
    are authorized to execute), **IA** (IA-2 identification &
    authentication — identity is supplied by the embedding organization via
    user/role headers; the service ships hooks, not an identity provider;
    FAR's practices: identify system users, processes, and devices, and
    authenticate them before allowing access).
  - Audit log → **AU**, **on the FedRAMP Low side of the crosswalk only**
    (AU-2 event logging, AU-3 content of audit records; the append-only
    store and permission-gated read are implementation properties).
    **Precision note:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side, and none of
    Group 1's Moderate-level audit citations are imported here. The audit
    log is carried because the FedRAMP Low baseline carries the AU family
    and 3 siblings claim audit trails — not because L1 asks for it.
  - Ingest / query / export → **SI** (SI-10 information input validation —
    malformed input is rejected, never partially applied) and **SC**
    (SC-8 transmission confidentiality — the server runs over TLS when a
    certificate is configured; FAR's system-and-communications-protection
    practices cover boundary protection and protecting transmitted
    information at the family level). Encryption at rest is a
    deployment-layer control, stated plainly, not claimed here. No sibling
    in this group claims an encryption function (0 of 16); TLS support is
    a property of the reused service, recorded as such, not as a claim.
- **What this tier does not carry, and this build does not claim:** the
  Moderate/High apparatus from the sibling groups (e.g. the L3 group's
  audit-chain uplift, lockout machinery, and 800-172-derived enhancements)
  is out of scope for a Low/L1 merge and is not inherited downward.
- **Caveat, same as the crosswalk's:** this mapping states which baseline
  families the build's features answer to. It is not a FedRAMP
  authorization and not a CMMC certification, and it does not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Identical to Group 1's contract — Python 3, **standard library only**,
package `analytics` under `src/`, runnable and testable with
`PYTHONPATH=src`:

- `analytics/access.py` — `User(name, role)`; roles `admin|analyst|viewer`;
  `PERMISSIONS`: admin ⊇ {ingest, query, export, audit_read, admin},
  analyst = {ingest, query, export}, viewer = {query, export};
  `require(user, action)` raises `PermissionDenied`.
- `analytics/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)`; `.entries()` returns entry dicts with keys
  `ts, actor, action, target, details`. Append-only; optional JSONL file.
- `analytics/store.py` — `DatasetStore(audit=None)`; `.ingest_csv(name,
  text, actor)`, `.ingest_json(name, text, actor)` → dataset dict
  `{id, name, columns, row_count, created_by, created_utc}`; sequential ids
  `"ds-1"`, `"ds-2"`, …; `.get(dataset_id)`, `.list()`, `.rows(dataset_id)`.
  Malformed input raises `ValidationError` and changes nothing.
- `analytics/query.py` — `run_query(store, dataset_id, query, actor)` →
  `{columns, rows, row_count}`; query keys `select`, `where`
  (`{column, op, value}`), `group_by`, `aggregates` (`{func, column,
  alias}`, funcs `count|sum|avg|min|max|stddev`), `order_by`
  (`{column, direction}`), `limit`. `describe(store, dataset_id, column,
  actor)` → `{column, count, mean, median, min, max, stddev}` over the
  numeric values of the column.
- `analytics/charts.py` — `chart_svg(result, label_column, value_column,
  kind="bar", title="")` → standalone SVG string; kinds `bar|line|pie`.
- `analytics/reports.py` — `result_to_csv(result)`, `result_to_json(result)`,
  `report_html(title, sections)`; each section is
  `{heading, table: result|None, chart_svg: str|None}` → HTML string.
- `analytics/service.py` — `make_server(host, port, store, audit, users)` →
  `http.server.ThreadingHTTPServer`; `users` maps name → role. Auth via
  `X-User` / `X-Role` headers (role must match the registry). Endpoints:
  `GET /health`, `GET /datasets`, `POST /datasets`
  `{name, format: csv|json, data}`, `GET /datasets/{id}`,
  `POST /datasets/{id}/query`, `POST /datasets/{id}/describe` `{column}`,
  `GET /datasets/{id}/export?format=csv|json`,
  `GET /datasets/{id}/chart?kind=&label=&value=`,
  `GET /audit`. Errors are JSON `{error}` with 400/401/403/404 as
  applicable. Denied attempts are audited.
- `analytics/__main__.py` — `python -m analytics serve --host --port
  [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=analyst, carol=viewer` (documented as demo identities;
  production identity is the embedding organization's, per IA-2 above).
- `analytics/errors.py` — `AnalyticsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`.

Tests live in `tests/` (stdlib `unittest`, 136 tests), each test docstring
naming the core function / spec claim it traces to, including the
**negative control**: a mutant aggregation (avg computed as sum, ignoring
the divisor) that the canonical expectation is shown to reject. The
mutation drill was performed against this tree (12 failures under the
mutant; suite green after byte-identical restoration) and is recorded in
`tests/README.md`.

## Coverage statement (for this build)

- Specs: 16 / 16 forks spec'd (Low 6, LI-SaaS 10; each fork's actual impact
  level recorded in its spec sheet).
- Core: 10 core functions implemented, each with tracing tests.
- Extended: 8 functions specified and ranked, **not** implemented in this
  build — real-time/streaming (this group's joint-largest family),
  alerts/monitoring, collaboration, proprietary-source connectors,
  the predictive ML remainder, transformation, archiving, and text/NLP —
  named here rather than implied done, and registered in the repo's
  GAPS.md final batch when this group ships.
- Absent from this group's union (0 claims, so neither Core nor Extended):
  geospatial, governance, encryption-as-a-function, KPI, BI/self-service,
  scheduling, media analytics.
