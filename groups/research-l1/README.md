# Research L1 — singleton build (Operation DeadRamp, Phase 2 remainder)

This is the clean-room implementation of the **Research L1
singleton**: **1 fork** from the FedRAMP Marketplace at the
lightest tier — **Laser AI** (Evidence Prime), FedRAMP
**LI-SaaS**, FedRAMP Certified — built per the group's union
spec ([`UNION-SPEC.md`](UNION-SPEC.md)) under the singleton
pipeline (same pipeline, group size one). LI-SaaS is FedRAMP's
tailored subset of the Low baseline for SaaS offerings; the
group's union baseline is the Low baseline ⇔ CMMC L1
(FAR 52.204-21).

**Read the honesty section before the function list.** This
fork's public description evidences **zero** function families
under the category taxonomy (applied verbatim from Group 53) —
0 raw hits across all 9 families — so the build below is the
category's research-data records substrate **carried** at this
tier under an explicit core-boundary decision, not a set of
functions this fork was found to claim. The decision, its
reasoning, and its price (full disclosure) are in
`UNION-SPEC.md`. Membership provenance is also recorded there:
`forks.json` files this fork Uncategorized; the Research
category is the remainder census proposal, taken from the fork's
own description (census note: "AI/NLP is the technique; the
function performed is systematic-review research synthesis.").

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

**Reuse, stated plainly:** the implementation and test suite are
the shipped Group 53 (Research L2) build's code, reused — this
project's own Apache-2.0 code. A per-file hash comparison is
recorded in `scratch/reuse-note.md`: 6 of 7 `src/` modules and
12 of 14 carried test files are byte-identical to Group 53's;
`__init__.py` and `research_helpers.py` differ in documentation
wording only, and one test file is new (the singleton spec pins).
Group 53's `test_additions.py` is deliberately not carried — it
pins that group's L2 additions, not this singleton. **The
baseline claim is not reused.** Everything Group 53 says about
Moderate / NIST SP 800-171 stays in Group 53. This group's
claims are the Low baseline's and FAR 52.204-21's only, as
written in `UNION-SPEC.md`.

## The 11 core functions (carried substrate)

1. **Data commons registry & membership** — commons (`com-`)
   with kind (`commons` / `ecosystem` / `mesh`), title, opaque
   sponsor reference, an owner and a member list. Membership is
   the boundary every other function enforces. The lifecycle is
   event-driven: `draft → active → retired`.
2. **Organization registry** — organizations (`org-`) known only
   by an opaque caller-supplied `ref` and a label; the record
   shape is pinned, so no field can hold a real identifier.
3. **Workspace registry** — workspaces (`ws-`) inside a commons,
   with a name and a stated purpose.
4. **Dataset registry (metadata + checksums only)** — datasets
   (`ds-`) with name, description, an access tier (`open` /
   `controlled`), a SHA-256 checksum, and a byte size. **No
   content is ever stored, and no field exists that could hold
   research subject data or a dataset payload** — the shape is
   pinned by test. Caller-supplied content can be verified
   against the checksum (hashed transiently, compared,
   discarded).
5. **Access request records** — requests (`ar-`) against
   controlled datasets, with a stated purpose and a duration in
   days. A request against an open dataset is rejected: open
   data needs no gate, and a request record for one would be a
   false one.
6. **Decision records** — decisions (`dec-`) on pending
   requests. The decider is never the requester (separation of
   duties — traced to AC-3 at this tier, AC-5 named as lineage;
   see the spec's precision notes), enforced in the store.
7. **Access grant records** — approvals mint time-boxed grants
   (`gr-`). A grant's status (`scheduled` / `active` / `expired`
   / `revoked`) is **derived at read** from its start, expiry,
   and revocation timestamp — never stored; the stored record
   carries no status key. Grants are records: they confer
   nothing by themselves, and no data moves in this build.
8. **Search & summary reporting** — substring search across
   accessible commons, organizations, and datasets; per-commons
   summaries computed on read as counts (workspaces, datasets by
   tier, requests by status, grants by derived status). Never
   scores.
9. **REST API** — every function above over a JSON REST API.
10. **RBAC** — roles `admin`, `member`, `viewer` with a
    permission matrix enforced on every operation, layered with
    commons membership.
11. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial record, no id
consumed). Durations are whole days: booleans, floats, and
strings are rejected at the boundary.

## Run

```bash
cd groups/research-l1
PYTHONPATH=src python3 -m research serve            # http://127.0.0.1:8798
PYTHONPATH=src python3 -m research serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m research serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including reading the audit log |
| `bob` | member | commons, records, requests, decisions (never on his own requests) |
| `carol` | viewer | reads only |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | read | `{"commons": [...], "organizations": [...], "datasets": [...]}` |
| `GET /commons` · `POST /commons` | read / create_commons | create → 201 |
| `GET /commons/{id}` | read | |
| `POST /commons/{id}/members` | manage_members | body `{"username": ...}` |
| `POST /commons/{id}/activate` · `/retire` | record | event-driven lifecycle transitions |
| `GET /commons/{id}/summary` | read | counts computed on read; `?now=` |
| `GET /organizations` · `POST /organizations` | read / enter | create → 201 |
| `GET /organizations/{id}` · `POST /organizations/{id}` | read / enter | POST updates the label |
| `GET /commons/{id}/workspaces` · `POST` | read / record | create → 201 |
| `GET /workspaces/{id}` | read | |
| `GET /commons/{id}/datasets` · `POST` | read / record | `?access_tier=` filter; metadata + checksum only |
| `GET /datasets/{id}` | read | |
| `POST /datasets/{id}/verify` | read | body `{"content": "..."}` — hashed transiently, never stored |
| `GET /datasets/{id}/access-requests` · `POST` | read / enter | controlled datasets only; create → 201 |
| `GET /access-requests/{id}` | read | |
| `POST /access-requests/{id}/decide` | decide | body `{"approve": bool, "note": ..., "starts_at": ...}`; never the requester; approval → 201 with the minted grant |
| `POST /access-requests/{id}/withdraw` | enter | from `pending` only |
| `GET /commons/{id}/grants` | read | `?status=` filters on the derived status; `?now=` |
| `GET /grants/{id}` | read | derived `status`; `?now=` |
| `POST /grants/{id}/revoke` | decide | records the revocation event |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Tests

```bash
cd groups/research-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 96 tests
```

**96 tests, all passing**, including the mutation-verified
negative control: removing the grant-status derivation from the
real store makes exactly 7 tests fail — the identical set to the
parent group's original drill (see `tests/README.md` for the
drill record).

## Honesty: what is NOT in this build

- **Zero claims at this tier.** The singleton's description tags
  no function family under the category taxonomy — 0 raw hits
  across all 9 families and all 6 sentences, with the
  near-misses itemized in `scratch/ARTIFACTS.md` rather than
  repaired. The 11 core functions are the Group 53 category
  substrate carried at this tier and flagged carried, not
  claimed, throughout `UNION-SPEC.md`.
- **Laser AI's engines are NOT implemented.** No living
  systematic review automation (no NLP/AI synthesis pipeline),
  no search-strategy construction or execution, no screening, no
  data extraction from full texts, no review quality assessment
  or verification, no protocol authoring, no meta-analysis
  export, no shared dictionaries, no review project/team
  administration, no workflow engine, and no AI suggestion
  interface. Those are the singleton's Extended gaps, named in
  `UNION-SPEC.md` for the final batch.
- **Extended capabilities from the L2 union are NOT
  implemented.** No commons runtime, no ingestion or
  harmonization, no indexing over dataset contents, no query or
  analysis computation, no cohort builder, no federation
  protocol, no data delivery, no enforcement on actual data
  reads. Each is named as an Extended gap in `UNION-SPEC.md`.
- **Privacy is structural, not procedural.** Records carry
  opaque references and metadata only. Dataset records are
  metadata + checksum with a pinned key set — there is no field
  in which research subject data, a genomic or clinical payload,
  dataset content, or — pointedly for this fork — review
  contents, protocol text, screening results, or extracted study
  data could be placed, and verification content is hashed in
  transit through the call and discarded. Nothing is scored or
  ranked anywhere, and no record shape has a field for a score —
  pinned by tests.
- Grant status is derived at read time and never stored; the
  stored grant record carries no `status` key — pinned by tests.
  A commons' lifecycle status *is* stored, because it is
  event-driven, not date-driven; the distinction is deliberate
  and stated in the store's module docstring.
- Grants are records. No data moves in this build, and a grant
  confers nothing by itself; delivery and delivery-side
  enforcement belong to the engines named as gaps.
- Demo identities are hooks, not an identity provider. IA-2
  stays with the embedding organization. Encryption is TLS when
  a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping in `UNION-SPEC.md` states which
  Low/L1 baseline families the build's features answer to;
  nothing more. FedRAMP authorizes products; CMMC certifies
  organizations — neither regime accepts the other as evidence.
