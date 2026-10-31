# Data Management L1 — singleton build (Operation DeadRamp, Phase 2, Group 38)

This is the clean-room implementation of the **Data Management L1
singleton**: **1 fork** from the FedRAMP Marketplace — **Pagefreezer
Website Archiving** (Pagefreezer Software Inc.), FedRAMP **LI-SaaS**,
FedRAMP Certified — built per the group's union spec
([`UNION-SPEC.md`](UNION-SPEC.md)) under the singleton pipeline (same
pipeline, group size one). LI-SaaS is FedRAMP's tailored subset of
the Low baseline for SaaS offerings; the group's union baseline is
the Low baseline ⇔ CMMC L1 (FAR 52.204-21).

**Read the honesty section before the function list.** This fork's
public description evidences **zero** functions under the category
taxonomy (applied verbatim from Group 12), so the build below is the
category's governance substrate **carried** at this tier under an
explicit core-boundary decision — not a set of functions this fork
was found to claim. The decision, its reasoning, and its price
(full disclosure) are in `UNION-SPEC.md`.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

**Reuse, stated plainly:** the implementation and test suite are the
shipped Group 12 (Data Management L2) build's code, reused — this
project's own Apache-2.0 code. A per-file hash comparison is
recorded in `scratch/reuse-note.md`: all 7 `src/` modules and 12 of
14 test files are byte-identical to Group 12's; the two differing
files are documentation wording only. **The baseline claim is not
reused.** Everything Group 12 says about Moderate / NIST SP 800-171
stays in Group 12. This group's claims are the Low baseline's and
FAR 52.204-21's only, as written in `UNION-SPEC.md`.

## Remainder addition (unit `addition:data-management-l1`)

One previously uncategorized fork has since joined the group:
**DevResults** (DevResults, FR2100845343), FedRAMP **LI-SaaS**,
FedRAMP Certified — see [`ADDENDUM.md`](ADDENDUM.md). It claims
**zero** functions under the verbatim taxonomy, exactly as the
original fork does, so the group now stands at **2 forks, 0
claims, 0 of 2 claiming**, and the honesty section below applies
to both forks unchanged. The core is unchanged — `src/`
byte-identical to the shipped build — and the suite grew from
196 to **207 tests**, all passing, including a re-run of the
self-approval guard drill in this tree (exactly 5 failures
under mutation; see `tests/README.md`). Two new gap functions
(the fork's M&E results-management platform functions and its
data-capture tooling) and two substance memberships in existing
gaps are recorded in the addendum for the GAPS.md registry at
ship.

## The 12 core functions (carried substrate)

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
cd groups/data-management-l1
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
cd groups/data-management-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 196 tests
```

**196 tests, all passing**, including the mutation-verified negative
control: disabling the self-approval guard in the real store makes
exactly 4 tests fail (see `tests/README.md` for this group's drill
record — the drill was performed against this tree, not inherited
from Group 12's record).

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the **NIST SP 800-53 Rev. 5 Low
baseline** (LI-SaaS is its FedRAMP tailoring for this fork),
cross-walked to the **FAR 52.204-21** practices that define CMMC L1:

- **AC / IA** — dataset registry and RBAC: CM-6, AC-2, AC-3, SI-10;
  IA-2 (identification & authentication — identity is supplied by
  the embedding organization via user/role headers; this service
  ships hooks, not an IdP). Access governance adds purpose-bound,
  time-boxed grants on the same AC-3 enforcement. **Precision
  notes:** the never-self-approve guard is a design property of the
  substrate; its family home AC-5 (and AC-6) are not Low-baseline
  selections, so at this tier the guard is traced to AC-3 and the
  FAR access-limitation practices only. Group 12's AC-5/AC-6
  citations do not carry down.
- **AU** — audit log: AU-2, AU-3; append-only store, audit-read
  restricted to the `audit_read` permission. **This mapping is
  FedRAMP-Low-side only:** FAR 52.204-21 / CMMC L1 has no audit
  practice, so no audit claim is made on the CMMC side, and Group
  12's AU-6/AU-9 citations are not imported.
- **SI / CA / SC** — ingestion, provenance, retention: SI-12;
  quality rules and checks: SI-10, CA-2; export manifests: SC-8
  (transmission confidentiality — the server runs over TLS when a
  certificate is configured; encryption at rest is a
  deployment-layer control, stated plainly and not claimed here).

## Honesty

- **Zero evidenced claims.** The fork's spec sheet
  (`specs/specs.json`) carries 0 tagged functions out of the
  category's 19 families. Its three-sentence description is
  boundary prose; the near-misses (archiving vs. retention,
  captured vs. ingestion, monitoring, automated, scalable, the
  website archive vs. registry) are itemized in
  `scratch/ARTIFACTS.md`. The taxonomy was not re-tuned to change
  this, and no function was invented for the fork.
- **Core carried, not claimed.** The 12 functions above are the Data
  Management category substrate (Group 12's core), carried at this
  tier under the core-boundary decision recorded in
  `UNION-SPEC.md`: the substrate is what an archiving service's
  operation presupposes (held collections, recorded captures,
  retention, governed access, export), stated as interpretation.
  The engines that make the product itself — web crawling and
  snapshot capture, page rendering, change detection/dynamic
  monitoring, archive storage and replay, full-content archive
  search — are **not in this build**; they are Extended gaps in
  `UNION-SPEC.md` for the final batch, alongside the category's
  carried Extended list.
- Provenance is at ingestion granularity — which sources fed which
  dataset, when, and how much. Field-level or transformation
  lineage is not claimed; no Data Management description at any
  tier built so far claims it either.
- Retention is scheduled and reported, not executed: the build
  computes what is due; deletion/archival belongs to the embedding
  deployment.
- Quality check runs evaluate the records supplied in the call
  against registered rules. The build does not reach into any live
  dataset store — there is none in it.
- Demo identities are hooks, not an identity provider. IA-2 stays
  with the embedding organization. Encryption is TLS when a
  certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The Moderate/High
  apparatus of the sibling Data Management groups (800-171 depth,
  the L3 audit-chain uplift, 800-172-derived enhancements) is **not**
  inherited downward into this tier.
