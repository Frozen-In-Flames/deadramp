# Legal & Policy L2 — merged build (Operation DeadRamp, Phase 2, Group 49)

This is the merged, clean-room implementation of the **Legal &
Policy L2** singleton: **1 fork** from the FedRAMP Marketplace
(**FR2619254906**, VulcanGov (Justinian for Government), Vulcan
Technologies, Inc., **FedRAMP Moderate / CMMC L2**, Legacy FedRAMP
Ready), built as one open-source service from the group's union
contract (`UNION-SPEC.md`). Legal & Policy is a brand-new category —
no group exists at any other tier — so the function taxonomy was
defined from the fork's own marketplace description (the Group 1
method): **11 claims**, each carrying its source sentence as
evidence.

**This category is not the Law Enforcement category.** Group 34's
Law Enforcement L2 build is a legal *research records* substrate.
This fork is a different kind of product: an **AI agent workspace**
grounded in a curated legal library, with an administration console.
House patterns from the legal-records substrate are reused where
they genuinely fit (digest-only search records, metadata + checksum
document records, opaque references); the taxonomy, core, and spec
here are this fork's own.

It was written from that contract only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**, no
external dependencies.

## Additions (remainder unit `addition:legal-policy-l2`)

Six previously uncategorized forks joined this group in the
remainder pass — CDS Federal Cloud, Deloitte Evidence Management
System, DocuSign IAM eSignature, DocuSign CLM, Innovative Driven
Government Cloud, and RelativityOne Government (all FedRAMP
Moderate) — spec'd in `specs/specs.json` (7 sheets) under this
group's taxonomy applied **verbatim**. What joined: six
eDiscovery, evidence-management, e-signature, and
contract-lifecycle platforms the census filed under Legal &
Policy from their own descriptions. What changed: the spec only —
the newcomers claim **zero** of the 11 taxonomy families (the
taxonomy is the original fork's own phrases; see `ADDENDUM.md`
for the per-fork near-misses), and their engines are registered
as 10 new gaps for the final batch. What did not change: the
core — `src/` is byte-identical, the tier baseline is untouched,
and the group's signature single-use drill was re-run against
the enlarged suite (106 tests; exactly 5 fail under the mutant).
Full record: [`ADDENDUM.md`](ADDENDUM.md).

## The 13 core functions

1. **Agency registry & membership** — agencies (`agy-`) keyed by an
   opaque `agency_ref` with a label and a member list. Membership is
   the boundary every agency-scoped function enforces; only the
   agency's creator or a platform admin may add members.
2. **Workspace registry** — workspaces (`wsp-`) inside an agency,
   keyed by an opaque `workspace_ref` (unique within the agency)
   with a title.
3. **Agent session records** — sessions (`ses-`) in a workspace with
   an optional purpose label, a `sandbox` flag, an optional
   `expires_at`, and a guarded lifecycle (`active` → `closed`).
   Read views derive `expired` and `sandbox_consumed`; the stored
   record carries neither key.
4. **Execution records** — executions (`exe-`) against a session
   with a kind (`code` / `document`) and an optional language label.
   **The single-use rule is the signature invariant:** a sandbox
   session accepts exactly one execution. Executions against closed
   sessions are rejected.
5. **Library source registry** — the curated library as metadata
   records (`lib-`): statutes, regulations, guidance, datasets. No
   content — the corpus itself is Extended.
6. **Saved-search records** — saved searches (`sea-`) holding the
   query's SHA-256 digest (never the query) and a result count. The
   store has no parameter that can accept query text.
7. **Document registry** — documents (`doc-`) in a workspace:
   metadata + SHA-256 checksum (validated lowercase hex) and a byte
   count, kind `generated` / `uploaded`. Content is never stored.
8. **Verify-by-content** — given bytes, recompute the SHA-256 and
   compare it to the registered checksum; returns the comparison,
   stores nothing.
9. **Usage records** — usage (`use-`) per agency (optionally per
   workspace/session) with a kind and a quantity that must be a
   positive integer — booleans, floats, and strings are rejected at
   the boundary.
10. **Usage export manifests** — exports (`exp-`) over an agency's
    usage records in an optional time window: the record count, the
    total quantity, and a SHA-256 checksum of the canonical exported
    set, computed at export time from the records.
11. **Registry reporting** — an agency report computed on read:
    workspace, session, execution, search, document and export
    counts, sessions by lifecycle status, sandbox sessions consumed
    (derived), and usage sums by kind. No analytics engine, no
    scores.
12. **Registry search** — literal case-insensitive substring search
    over registry metadata (references, titles, labels, kinds),
    scoped to agencies the actor belongs to (or all for a platform
    admin), plus the platform library. Digests are never matched.
13. **Access control & audit** — platform roles `admin`, `member`,
    `viewer` with a permission matrix enforced on every operation,
    layered with agency membership; and an append-only audit log
    recording every mutation and every denied attempt.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Validation always precedes mutation.

## Run

```bash
cd groups/legal-policy-l2
PYTHONPATH=src python3 -m legalpol serve            # http://127.0.0.1:8799
PYTHONPATH=src python3 -m legalpol serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m legalpol serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo identities (documented demo users, not an identity provider —
production identity belongs to the embedding organization). Callers
authenticate with `X-User` / `X-Role` headers matching these:

| User | Role | Can do |
|---|---|---|
| `alice` | admin | everything, including creating agencies and reading the audit log |
| `bob` | member | workspaces, sessions, executions, library, searches, documents, usage, exports, reports (in agencies he belongs to) |
| `carol` | viewer | reads and reports only, in agencies she belongs to |

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | agency_read | registry search dict (membership-scoped + library) |
| `GET /agencies` · `POST /agencies` | agency_read / agency_write | create → 201; body `{agency_ref, label}` |
| `GET /agencies/{id}` | agency_read | |
| `POST /agencies/{id}/members` | creator-or-admin (store) | body `{"username": ...}` → agency dict |
| `GET /agencies/{id}/workspaces` · `POST` | agency_read / workspace_write | create → 201; body `{workspace_ref, title}` |
| `GET /agencies/{id}/sessions?workspace_id=` · `POST` | agency_read / session_write | GET returns derived views; POST → 201 stored-shape session; body `{workspace_id, session_ref, purpose?, sandbox?, expires_at?}` |
| `POST /agencies/{id}/sessions/{sid}/close` | session_write | `active` → `closed` |
| `GET /agencies/{id}/sessions/{sid}/executions` · `POST` | agency_read / session_write | create → 201; body `{execution_ref, kind?, language?}`; second execution on a sandbox session → 400 |
| `GET /library?kind=` · `POST /library` | open read / library_write | platform registry; create → 201; body `{source_ref, kind, title?, jurisdiction_ref?}` |
| `GET /agencies/{id}/searches?workspace_id=` · `POST` | agency_read / search_write | create → 201; body `{search_ref, query_text \| query_sha256, result_count, workspace_id?}` — `query_text` is hashed by the service, never stored |
| `GET /agencies/{id}/documents?workspace_id=` · `POST` | agency_read / document_write | create → 201; body `{workspace_id, doc_ref, sha256, size_bytes, kind?, session_id?}` |
| `POST /agencies/{id}/documents/{did}/verify` | agency_read | body `{content_b64}` → verify dict; malformed base64 → 400 |
| `GET /agencies/{id}/usage?kind=` · `POST` | agency_read / usage_write | create → 201; body `{usage_ref, kind, quantity, session_id?, workspace_id?}` |
| `GET /agencies/{id}/exports` · `POST` | agency_read / export | create → 201; body `{export_ref, since?, until?}` |
| `GET /agencies/{id}/report` | report_read | counts and sums, computed on read |

Errors are JSON `{"error": msg}`: 400 validation, 401 unknown user
or role mismatch, 403 permission, 404 not found. Denied attempts
are audited with the action suffixed `:denied`.

## Permission matrix

Eleven actions: `agency_read`, `agency_write`, `workspace_write`,
`session_write`, `library_write`, `search_write`, `document_write`,
`usage_write`, `export`, `report_read`, `audit_read`.

| Role | Permissions |
|---|---|
| `admin` | all eleven |
| `member` | all except `agency_write` and `audit_read` (9) |
| `viewer` | `agency_read`, `report_read` |

Agency membership is layered on top: every agency-scoped operation
additionally requires the actor to be a member of that agency (a
platform admin is the exception). The platform library is not
agency-scoped: writes require `library_write`; reads are open to
any actor.

## Control mapping summary

Group tier CMMC **L2** ⇔ FedRAMP **Moderate** (per the project
crosswalk); baseline NIST SP 800-53 Rev. 5 Moderate, cross-walked
to the 110 practices of NIST SP 800-171 Rev. 2.

- Access control (platform roles + agency membership) → **AC**
  (AC-2, AC-3, AC-6), **IA** (IA-2 — identity is supplied by the
  embedding organization via user/role headers; the build ships
  hooks, not an identity provider. The fork's own description
  federates identity to an external IdP with enforced MFA; that is
  the embedding organization's layer).
- Audit log → **AU** (AU-2, AU-3, AU-6 — append-only store;
  audit-read restricted to `audit_read`, held by admin only).
- Document checksums & verify-by-content → **SI** (SI-7, a Moderate
  selection; hashes computed with the standard library).
- Registries, lifecycle guards, the single-use seam, digest
  discipline → **SI** (SI-10 — malformed input, including any
  non-integer quantity, bad checksum, duplicate reference, or
  second sandbox execution, is rejected whole) and **SC** (SC-8 —
  TLS when a certificate is configured; encryption at rest is a
  deployment-layer control, stated plainly, not claimed here. The
  fork's description claims FIPS-validated modules of its own
  platform; this build claims none — Python's standard library is
  not a FIPS-validated cryptographic module).

## Tests

```bash
cd groups/legal-policy-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 106 tests
```

**106 tests, all passing** (94 at delivery + 12 additions
tests), including the mutation-verified negative control:
removing the single-use sandbox check from the real store makes
exactly 4 tests fail at delivery scope and exactly 5 against the
enlarged suite (the additions module's sandbox case is the fifth;
see `tests/README.md` for both drill records).

## Honesty

- This build is the **records substrate only**. The agent runtime
  (LLM inference, agent orchestration), the legal corpus content,
  the full-text and semantic search engines, the sandbox runtime,
  the code execution engine, and the document generation engine are
  **Extended** — named as gaps in `UNION-SPEC.md`, not implemented
  here. The core records workspaces, sessions, and executions; it
  runs no agent, executes no code, and generates no documents.
- **Content is never stored.** Documents are metadata + checksums;
  the corpus is registered as source records only. **Queries are
  digest-only:** the service layer hashes `query_text` before the
  store ever sees a value, and the store's `save_search` signature
  has no parameter that could accept query text — pinned by tests.
- **Nothing is scored.** No record shape carries a score, rating,
  or computed status of a legal question. Usage totals are sums of
  recorded quantities — counts, not judgments.
- Date-derived status is derived at read, never stored: a session's
  `expired` and `sandbox_consumed` flags are computed by the read
  views, and the stored session record carries neither key —
  pinned by tests that read the store's internal records.
- Demo identities are hooks, not an IdP; identity federation and
  MFA stay with the embedding organization (IA-2). Encryption is
  TLS when a certificate is configured; encryption at rest is a
  deployment-layer property. The deployment is a **single-tenant
  reference deployment**.
- The baseline mapping (800-53 Moderate ⇔ 800-171) is a planning
  equivalence per the project crosswalk — **not a FedRAMP
  authorization and not a CMMC certification**, and this build
  claims neither. FedRAMP authorizes products; CMMC certifies
  organizations.
- Claims discipline: every function above traces to the fork's
  claims in `specs/specs.json` (11 evidenced claims from the single
  fork, taxonomy defined from its own description) or to the
  Moderate/L2 control families in `UNION-SPEC.md`. Counts are a
  floor, stated as such.
