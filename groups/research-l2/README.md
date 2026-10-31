# Research L2 — merged build (Operation DeadRamp, Phase 2, Group 53)

This is the merged, clean-room implementation of the **Research
L2** singleton: **1 fork / vendor platform** from the FedRAMP
Marketplace (Gen3 Data Ecosystems Platform, Center for
Translational Data Science (CTDS)), built as one open-source
service from the group's union contract (`UNION-SPEC.md`).
Research is a brand-new category with no parent group at any
tier — and this fork is the entire category — so the function
taxonomy was defined from the fork's own marketplace description
(the Group 1 method): **9 claims**, each carrying its source
sentence as evidence. The description is two sentences long;
sentence 1 is a baseline determination and tags nothing, so all
nine claims come from the single platform sentence. Counts are a
floor, stated as such.

It was written from that contract only: original code, no vendor
code, assets, or branding from the sibling offering. Python 3,
**standard library only**, no external dependencies.

## Remainder additions

Five previously uncategorized forks joined this group in the
remainder census (unit `addition:research-l2`; see
[`ADDENDUM.md`](ADDENDUM.md)): **Terra** (Broad Institute),
**Ipsos Research**, **ROSALIND**, **Seven Bridges Platform**,
and **Wellspring WTIMS** — three genomics data platforms, a
survey-research platform, and a technology-transfer suite, all
FedRAMP Moderate. Spec'd under the group's existing taxonomy
applied verbatim, they add **2 claims** (both `data_sharing`:
Terra and ROSALIND) and three zero-claim sheets — the taxonomy's
patterns are the Gen3 sentence's literal phrases, and the
near-misses are itemized in the addendum rather than tuned for.
**The core did not change**: `src/` is byte-identical to the
singleton build, and the newcomers' own engines (analysis
pipelines, the survey platform, the tech-transfer suite) are
named as Extended gaps in the addendum. The group now covers
**6 forks and 11 claims**; the privacy discipline is unchanged
— dataset records are metadata + checksum only, and grants are
records that confer nothing.

## The 11 core functions

1. **Data commons registry & membership** — commons (`com-`)
   with kind (`commons` / `ecosystem` / `mesh` — the
   description's own nouns), title, opaque sponsor reference, an
   owner and a member list. Membership is the boundary every
   other function enforces. The lifecycle is event-driven:
   `draft → active → retired`.
2. **Organization registry** — organizations (`org-`) known only
   by an opaque caller-supplied `ref` and a label; the record
   shape is pinned, so no field can hold a real identifier.
3. **Workspace registry** — workspaces (`ws-`) inside a commons,
   with a name and a stated purpose: the records form of the
   workspaces the description claims.
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
   days. A request against an open dataset is rejected: open data
   needs no gate, and a request record for one would be a false
   one.
6. **Decision records** — decisions (`dec-`) on pending
   requests. The decider is never the requester (separation of
   duties, AC-5), enforced in the store.
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
cd groups/research-l2
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
cd groups/research-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 97 tests
```

**97 tests, all passing**, including the mutation-verified
negative control: removing the grant-status derivation from the
real store makes exactly 9 tests fail in the enlarged suite
(7 in the original singleton suite; see `tests/README.md` for
both drill records).

## Honesty

- The build implements the records substrate the fork's public
  description actually presupposes. The engines are not in it:
  no commons runtime, no ingestion or harmonization, no indexing
  over dataset contents, no query or analysis computation, no
  cohort builder, no federation protocol, no data delivery, no
  enforcement on actual data reads. Each is named as an Extended
  gap in `UNION-SPEC.md` for the final batch.
- **Privacy is structural, not procedural.** Records carry opaque
  references and metadata only. Dataset records are metadata +
  checksum with a pinned key set — there is no field in which
  research subject data, a genomic or clinical payload, or
  dataset content could be placed, and verification content is
  hashed in transit through the call and discarded. Nothing is
  scored or ranked anywhere, and no record shape has a field for
  a score — pinned by tests.
- Grant status is derived at read time and never stored; the
  stored grant record carries no `status` key — pinned by tests.
  A commons' lifecycle status *is* stored, because it is
  event-driven, not date-driven; the distinction is deliberate
  and stated in the store's module docstring.
- Grants are records. No data moves in this build, and a grant
  confers nothing by itself; delivery and delivery-side
  enforcement belong to the engines named as gaps.
- Demo identities are hooks, not an identity provider. IA-2 stays
  with the embedding organization. Encryption is TLS when a
  certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a single-tenant
  reference deployment (the fork claims multi-tenancy of its own
  platform; that claim is recorded with a platform disposition,
  not reproduced as a build claim).
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (9 evidenced claims from the
  single fork, taxonomy defined from its own description) or to
  the Moderate/L2 control families in `UNION-SPEC.md`. Counts are
  a floor, stated as such.
