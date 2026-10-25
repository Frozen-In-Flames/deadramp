# Law Enforcement L2 — merged build (DeadRamp Phase 2, Group 34)

A clean-room **legal research records substrate**: the merged open
implementation for the Law Enforcement L2 sibling group (2 forks,
FedRAMP Moderate ⇔ CMMC L2). Spec: [UNION-SPEC.md](UNION-SPEC.md);
per-fork spec sheets: [specs/specs.json](specs/specs.json).

**Group character, stated plainly:** neither sibling is a
law-enforcement operational platform. Lexis+® for Government
(LexisNexis) and Thomson Reuters Legal Research are legal research
platforms for government attorneys, filed under "Law Enforcement" in
the source (both source records carry no business categories at all).
The build is therefore the substrate their claimed functions jointly
presuppose — matters, sources, documents, saved searches, annotations,
citation checks — and the category's anticipated operational
functions (incident/case management, evidence custody, criminal
records) are recorded in the union spec as named absences: unclaimed,
not built, not gaps.

**Privacy is the hard rule of this build.** Records are keyed by
opaque caller-supplied references only; no entity shape can hold a
real name, a case subject, or any content. Documents are registry
metadata + SHA-256 checksums, never content. Search queries and
annotation notes are stored as SHA-256 digests only — the store has
no parameter that could accept the text. Citation treatments are
recorded verbatim and never computed, normalized, or scored.

## Run

```bash
cd groups/law-enforcement-l2
PYTHONPATH=src python3 -m unittest discover -s tests     # 82 tests
PYTHONPATH=src python3 -m lawenf serve --port 8797       # HTTP service
```

Demo users (demo identities, not an IdP — production identity is the
embedding organization's): `alice=admin`, `bob=member`,
`carol=viewer`. Authenticate with `X-User` / `X-Role` headers. Add
`--certfile` / `--keyfile` to serve over TLS; `--audit-log PATH` to
persist the audit trail as JSONL.

## What it does (the core, 11 functions)

1. **Matter registry & members** — matters keyed by opaque refs,
   guarded open/closed lifecycle; membership is the boundary on
   every matter-scoped operation.
2. **Source registry** — legal sources (statute, case law,
   regulation, secondary, guidance, standard document) as metadata
   records. No content.
3. **Document registry** — metadata + SHA-256, guarded review
   lifecycle (`registered → in_review → reviewed`).
4. **Verify-by-content** — re-hash caller-supplied bytes and compare;
   stores nothing.
5. **Saved-search records** — query stored as a SHA-256 digest plus a
   result count.
6. **Annotation records** — note stored as a SHA-256 digest, targeted
   at a document, search, or source.
7. **Citation-check records** — treatment recorded verbatim.
8. **Registry reporting** — counts on read, treatment keys verbatim.
9. **Registry search** — literal search over registry metadata,
   membership-scoped; digests are never searchable.
10. **RBAC** — admin / member / viewer over nine actions, layered
    with matter membership.
11. **Audit log** — append-only; every mutation and every denied
    attempt recorded.

## Endpoints

`GET /health` (no auth) · `GET /audit` (admin) · `GET|POST /matters` ·
`GET /matters/{id}` · `POST /matters/{id}/members|close|reopen` ·
`GET|POST /matters/{id}/sources` · `GET /matters/{id}/sources/{sid}` ·
`GET|POST /matters/{id}/documents` · `GET /matters/{id}/documents/{did}` ·
`POST /matters/{id}/documents/{did}/begin-review|complete-review|verify`
(`{content_b64}`) · `GET|POST /matters/{id}/searches` (`query_text` is
hashed by the service; `query_sha256` may be supplied directly) ·
`GET|POST /matters/{id}/annotations` (same digest discipline for
`note_text`) · `GET|POST /matters/{id}/citation-checks` ·
`GET /matters/{id}/report` · `GET /search?q=`

Permission matrix: admin = all nine actions; member = all except
`audit_read`; viewer = `matter_read` + `report_read` only. Matter
membership is additionally required for every matter-scoped route
(platform admin excepted).

## Honesty section

- Claims: 13 tagged across the two spec sheets under a fixed 9-family
  taxonomy, every claim carrying its source sentence verbatim. Five
  wording-artifact corrections and one near-miss are logged in
  `scratch/ARTIFACTS.md` and in the extractor; the taxonomy was not
  tuned to manufacture claims, and counts are a stated floor.
- Access control is **claimed for one fork, carried for the other**
  (baseline substrate), and is flagged as such in the spec.
- No score, status, or validity is ever computed from a recorded
  citation treatment; the recorded strings are the record.
- Nothing here surveils, identifies, predicts, or ingests any feed:
  the category-discipline exclusions (surveillance, facial
  recognition, predictive policing, real-time intelligence) are named
  Extended gaps in the union spec and are not built.
- Platform-layer, stated not claimed: encryption at rest is a
  deployment-layer control (TLS when configured); the build is a
  single-tenant reference deployment; demo identities are hooks, not
  an IdP (IA-2 stays with the embedding organization).
- The baseline mapping (800-53 Moderate ⇔ 800-171) is a planning
  equivalence per the project crosswalk — not a FedRAMP
  authorization and not a CMMC certification.
- Tests: 82, all passing, including two negative controls; the
  membership-guard mutant was drilled against the real source
  (5 failures), restored, and SHA-256-verified — see
  [tests/README.md](tests/README.md).
