# Union Spec — Analytics, CMMC L3-adjacent (DeadRamp Phase 2, Group 3)

The merged functional spec for the **Analytics L3-adjacent** sibling group:
**54 forks**, category **Analytics**, CMMC tier **L3-adjacent** (every member
is FedRAMP **High** in `forks.json` — verified, so the group is single-tier
and the merge takes the group baseline in full, per Merge Rule 2). The member
list was reconciled against `MAP.md`'s "Analytics — L3-adjacent (54)"
section with **zero diffs** in both directions.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 54 entries,
each with the offering's full public marketplace description and its function
claims tagged from that description, every claim carrying the source sentence
as evidence. Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services Administration,
last change 2026-10-22), product records joined by FedRAMP ID.

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 1 merged build** (`../analytics-l2/`) — itself the union of
   the 128 Analytics L2 (FedRAMP Moderate) forks, shipped as a working
   clean-room analytics service.
2. This group's **54 High forks**, via the spec sheets in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the merge takes
the **union** of the parents' baselines (Rule 1), the merged fork inherits
the **highest** tier — FedRAMP **High** / CMMC **L3-adjacent** — and must
satisfy it **in full** (Rule 2), this document plus the spec sheets are the
**traceability** record (Rule 3), and the build followed the SSDF-shaped
process of provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was re-run
independently by the coordinator, and the negative control was
mutation-verified by patching the implementation (see Verification below).

**Reuse, stated explicitly:** where functions overlap, this build reuses
Group 1's own open-source code (Apache-2.0, ours). Four modules are
byte-identical to Group 1 (`__init__.py`, `charts.py`, `query.py`,
`reports.py`); six are modified for the tier uplift (`audit.py`,
`access.py`, `service.py`, `store.py`, `errors.py`, `__main__.py`). The
uplift analysis below names what the High baseline demanded beyond the L2
core and what was done about each item — implemented, or gap-listed by name.

## How functions were counted

The same fixed 24-function taxonomy as Group 1 (verbatim — same ids, labels,
and matching patterns) was matched against each offering's own public
description. A function is claimed for a fork **only** when the description
contains matching text; the matching sentence is stored as the claim's
evidence in the spec sheet. 51 of 54 offerings carry at least one tagged
claim (276 claims in total); 3 descriptions (Andesite Azimuth for
Government, Appian Government Cloud - High, Palantir Federal Cloud
Service – Supporting Services) contain no functional claim in taxonomy
terms — their full text is still in the spec sheets, and no function was
invented for them. Counts below are therefore a **floor**, not a ceiling.

## Function ranking — all 54 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | Statistical / predictive / ML & AI analysis | 34 | 63% | **Core slice**: descriptive statistics & aggregation (see below). Predictive/ML remainder: Extended |
| 2 | Alerts, monitoring & detection | 27 | 50% | Extended — the group's largest Extended function; see the note below |
| 3 | Visualization & dashboards | 20 | 37% | **Core** |
| 4 | Data storage / warehouse / lake | 18 | 33% | **Core** |
| 5 | Real-time & streaming analytics | 18 | 33% | Extended |
| 6 | Query & search | 18 | 33% | **Core** |
| 7 | Sharing & collaboration | 17 | 31% | Extended |
| 8 | Connectors & source integration | 17 | 31% | **Core slice**: open-format file ingest (CSV/JSON). Proprietary-source connectors: Extended |
| 9 | Reporting | 14 | 26% | **Core** |
| 10 | Access control & authentication | 13 | 24% | **Core** (High baseline hooks, uplifted — see below) |
| 11 | Data ingest & collection | 11 | 20% | **Core** |
| 12 | API access | 11 | 20% | **Core** (the service is API-first) |
| 13 | Data governance, catalog & metadata | 11 | 20% | Extended (dataset registry in Core storage is the seed) |
| 14 | Data transformation & preparation | 10 | 19% | Extended |
| 15 | Audit logging & trails | 7 | 13% | **Core** (High baseline hooks, uplifted — see below) |
| 16 | Text & natural-language analytics | 6 | 11% | Extended |
| 17 | Encryption | 5 | 9% | Platform note (TLS supported; FIPS caveat below) |
| 18 | Data export | 5 | 9% | **Core** (delivered with Reporting; low tag count is a description-wording artifact, as in Group 1) |
| 19 | Archiving & retention | 4 | 7% | Extended |
| 20 | Scheduling & workflow automation | 3 | 6% | Extended |
| 21 | Geospatial analysis | 3 | 6% | Extended |
| 22 | Image / video / media analytics | 2 | 4% | Extended |
| 23 | Business intelligence / self-service | 2 | 4% | Extended |
| 24 | KPI & performance management | 0 | 0% | Extended (zero claims in this group; retained in the taxonomy for cross-group comparability) |

**How this group differs from Group 1 (L2)** — preserved, not averaged
away: the High group skews hard toward AI-driven detection. Statistical /
ML claims jump from 35% (L2) to 63%, alerts & monitoring from 28% to 50%,
collaboration from 16% to 31%, while plain reporting drops from 29% to
26% and query stays a platform constant. The alerting claimants are the
detection platforms (e.g. CrowdStrike Falcon, Datadog for Government,
Elastic Cloud Hosted - High, Darktrace, Forescout — per the spec sheets).
That is the group's character: at the High baseline, "analytics"
predominantly means watching data for threats, not just summarizing it.

**Note on alerts & monitoring (the core-boundary decision):** at 27 of 54
(50%) it is this group's largest non-core function, and it is named here as
the first candidate for the next build increment. It is **not** in this
build's core: each sibling's alerting is bound to its own domain telemetry
(endpoint events, network flows, mission data) rather than to a shared
dataset surface the descriptions jointly presuppose, so a generic
threshold-alert slice would claim a commonality the evidence does not
establish. It stays Extended — specified, ranked, and counted, not silently
implied and not silently dropped.

## The Core — what the merged build implements (10 functions, at the High baseline)

The same 10 platform functions as Group 1 (the platform substrate every
sibling presupposes), carried up to the High baseline:

1. **Ingest** — load datasets from open formats (CSV, JSON) into the store.
2. **Storage** — a dataset registry: named datasets with inferred schema,
   row counts, and provenance (who loaded it, when).
3. **Query & search** — tabular query over a dataset: column selection,
   filters (`eq, ne, lt, le, gt, ge, in, contains`), grouping, ordering,
   limit.
4. **Descriptive statistics** (core slice of the #1 claim family) —
   aggregations `count, sum, avg, min, max, stddev` in queries, plus a
   per-column `describe` (count, mean, median, min, max, stddev).
   Predictive modeling and ML are Extended, not silently implied.
5. **Visualization** — charts rendered from query results as standalone SVG
   (bar, line, pie). No JavaScript, no external assets.
6. **Reporting** — a report bundle: an HTML report composed of titled
   sections (tables and charts), generatable from query results.
7. **Export** — datasets and query results out as CSV or JSON.
8. **API access** — every function above is exposed over a REST API (JSON).
9. **Access control** — role-based access hooks: roles `admin`, `analyst`,
   `viewer` (as Group 1) plus **`auditor`** (audit review only), with the
   permission matrix enforced on every operation, and unsuccessful-logon
   lockout at the service layer (uplift, below).
10. **Audit log** — an append-only, **hash-chained, tamper-evident** audit
    trail with audit search/reduction, chain verification, and fail-closed
    write behavior (uplifts, below).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the FedRAMP
  High tailoring) ⇔ the CMMC L3 basis: the 110 practices of NIST SP
  800-171 Rev. 2 **plus** the selected NIST SP 800-172 enhanced
  requirements. All 54 parent forks sit at High, and the cross-tier parent
  (Group 1's build) sat at Moderate; the union baseline is therefore the
  High baseline, un-diluted (Merge Rule 1), inherited in full (Rule 2).
  "Adjacent" remains deliberate wording, as in the crosswalk: L3 is not
  identical to FedRAMP High; it is the same assurance weight class.
- **Feature → control family mapping (carried from Group 1):**
  - Access control → **AC** (AC-2, AC-3, AC-6), **IA** (IA-2 — identity is
    supplied by the embedding organization via user/role headers; hooks,
    not an identity provider).
  - Audit log → **AU** (AU-2, AU-3, AU-6, AU-9 — append-only store,
    audit-read restricted to the `audit_read` permission).
  - Ingest / query / export → **SI** (SI-10 input validation — malformed
    input is rejected, never partially applied) and **SC** (SC-8 — TLS
    when a certificate is configured).

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3; 800-172 audit requirements) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store rolls back the whole dataset commit and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role holds `audit_read` and nothing else — audit review exists as a duty separable from administration. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 1, restated because High demands more of the IdP layer). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement in this build; retention rides with the Extended archiving function (4 siblings claim archiving/retention) |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which baseline
  families the build's features answer to. It is not a FedRAMP
  authorization and not a CMMC certification, and it does not claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `analytics` under `src/`,
runnable and testable with `PYTHONPATH=src`. The contract is Group 1's,
unchanged except for the uplift deltas marked **[L3]**:

- `analytics/access.py` — `User(name, role)`; roles
  `admin|analyst|viewer|auditor` **[L3]**; `PERMISSIONS`: admin ⊇ {ingest,
  query, export, audit_read, admin}, analyst = {ingest, query, export},
  viewer = {query, export}, **auditor = {audit_read}** **[L3]**;
  `require(user, action)` raises `PermissionDenied`.
- `analytics/audit.py` — `AuditLog(path=None)`; `.record(actor, action,
  target, details=None)` → entry dict with keys `ts, actor, action,
  target, details` plus **[L3]** `seq, prev_hash, hash` (SHA-256 of the
  canonical JSON of `{seq, ts, actor, action, target, details,
  prev_hash}`); raises **[L3]** `AuditWriteError` and rolls back if the
  JSONL write fails. `.entries()` returns all entries. **[L3]**
  `.query(actor=None, action=None, target=None, since=None, until=None)`
  returns filtered entries; `.verify_chain()` returns
  `(ok, first_bad_index_or_None)`. Append-only; optional JSONL file;
  loaded entries participate in chain verification.
- `analytics/store.py` — as Group 1; **[L3]** a failed audit write rolls
  back the dataset commit in full (no dataset, no id consumed) and the
  `AuditWriteError` propagates.
- `analytics/query.py`, `analytics/charts.py`, `analytics/reports.py` —
  **byte-identical to Group 1** (same signatures and behavior).
- `analytics/service.py` — `make_server(host, port, store, audit, users,
  max_failures=3, lockout_seconds=300)` **[L3 kwargs]** →
  `http.server.ThreadingHTTPServer`. Auth via `X-User` / `X-Role` headers
  (role must match the registry). **[L3]** consecutive auth failures are
  tracked per username; at `max_failures` the username locks for
  `lockout_seconds` (403, audited `auth:locked`); success resets.
  Endpoints as Group 1 (`GET /health`, `GET /datasets`, `POST /datasets`,
  `GET /datasets/{id}`, `POST /datasets/{id}/query`,
  `POST /datasets/{id}/describe`, `GET /datasets/{id}/export`,
  `GET /datasets/{id}/chart`, `GET /audit`) plus **[L3]**
  `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) and
  `GET /audit` filter params `actor, action, since, until`. Errors are
  JSON `{error}` with 400/401/403/404 as applicable. Denied attempts are
  audited.
- `analytics/__main__.py` — `python -m analytics serve --host --port
  [--audit-log PATH] [--certfile --keyfile] [--max-failed-logins N]
  [--lockout-seconds S]` **[L3 flags]** with demo users `alice=admin,
  bob=analyst, carol=viewer, dana=auditor` **[L3]** (documented as demo
  identities; production identity is the embedding organization's).
- `analytics/errors.py` — `AnalyticsError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`, plus **[L3]** `AuditWriteError`.

Tests live in `tests/` (stdlib `unittest`), each test docstring naming the
core function / spec claim / control family it traces to. 183 tests: the
136 Group 1 tests (inherited; four files minimally adapted for the uplift —
adaptations listed in `tests/README.md`) plus 47 new tests covering the
chain, audit query, fail-closed behavior, lockout, and the auditor role.
Two **negative controls**:

1. The avg-as-sum mutant (carried from Group 1): the canonical expectation
   is shown to reject an `avg` that never divides. Independently
   mutation-verified by the coordinator for this group: patching `avg` to
   return the bare sum made the suite fail (4 failures); restoring the
   original returned it to green.
2. **[L3]** Audit tamper: mutating a stored audit entry in place makes
   `verify_chain()` report failure at exactly that entry's index, and
   editing one line of the JSONL file is detected after reload — proving
   the chain catches the tampering defect class rather than merely
   existing.

## Coverage statement (for this build)

- Specs: 54 / 54 forks spec'd (51 with at least one tagged claim; 276
  claims total).
- Core: 10 core functions implemented, at the High baseline, each with
  tracing tests; 6 tier uplifts implemented (hash-chained audit, fail-
  closed audit writes, audit query/reduction, chain verification
  endpoint, logon lockout, auditor role).
- Extended: 14 functions specified and ranked, **not** implemented in this
  build: alerts & monitoring (the group's largest, 27 siblings),
  real-time/streaming, collaboration, proprietary-source connectors,
  governance beyond the registry, transformation, text/NLP, archiving &
  retention, scheduling, geospatial, media analytics, self-service BI,
  KPI (0 claims here), and the predictive/ML remainder of the #1 family.
- Baseline gaps named, not implied closed: MFA/authenticator management
  (IA-2(1)/(2), IA-5 — IdP layer), FIPS-validated crypto (SC-13),
  encryption at rest (SC-28), audit retention enforcement (AU-11),
  session lock/termination (AC-11/AC-12).
