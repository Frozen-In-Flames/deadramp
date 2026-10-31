# Law Enforcement L1 — singleton build (DeadRamp Phase 2, Group 47)

A clean-room **legal research records substrate** at the lightest
tier: the open implementation for the Law Enforcement L1 singleton
(1 fork, FedRAMP Low ⇔ CMMC L1). Spec:
[UNION-SPEC.md](UNION-SPEC.md); the fork's spec sheet:
[specs/specs.json](specs/specs.json).

**Singleton character, stated plainly:** the one fork is the Flock
Safety Platform (Flock Safety), a public-safety camera network —
license plate reading technology, audio recognition sensors, video
cameras, and software to capture evidence. Under the category
taxonomy (defined at L2 from two legal research platforms, applied
here **verbatim**), it tags **zero claims**: its vocabulary and the
taxonomy's intersect nowhere, and the taxonomy was not re-tuned. Its
own engines are specified as Extended gaps in the union spec, and
under this category's standing discipline **no surveillance
function of any kind is built** — not LPR, not audio detection, not
video, not evidence capture. The build is the category's records
substrate, carried in full at L1 under the explicit core-boundary
decision recorded in the spec (carried, not claimed; precedents
Groups 10, 24, 30 and Singletons 37, 38).

**Privacy is the hard rule of this build, unchanged from L2.**
Records are keyed by opaque caller-supplied references only; no
entity shape can hold a real name, a case subject, or any content.
Documents are registry metadata + SHA-256 checksums, never content.
Search queries and annotation notes are stored as SHA-256 digests
only — the store has no parameter that could accept the text.
Citation treatments are recorded verbatim and never computed,
normalized, or scored.

## Run

```bash
cd groups/law-enforcement-l1
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
   No score field anywhere.
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

## Baseline — Low / L1

NIST SP 800-53 Rev. 5 **Low** (the FedRAMP Low tailoring) ⇔ the 17
practices of **FAR 52.204-21** (CMMC L1), per the project crosswalk.
Audit traces to AU-2/AU-3 on the **FedRAMP Low side only** — FAR
carries no audit practice, so no audit claim is made on the CMMC
side. Group 34's Moderate citations are deliberately **not**
imported: SI-7 and AU-6 are not Low selections; at this tier the
checksum/verify mechanics and the admin-gated audit read are stated
as implementation properties. No Moderate/High apparatus (hash
chains, lockout, auditor role) is inherited downward. Feature →
control-family traceability is in UNION-SPEC.md.

## Honesty section

- Claims: **0 tagged** on the fork's spec sheet under Group 34's
  fixed 9-family taxonomy, applied verbatim and verified identical
  programmatically. Near-misses are itemized in
  `scratch/ARTIFACTS.md` ("collaboratively" is not the collaboration
  family; "capture objective evidence" is not document management);
  the taxonomy was not tuned to manufacture claims.
- All 11 core functions are **carried, not claimed** for this fork,
  under the core-boundary decision in the union spec. The fork's own
  engines (LPR, audio recognition, video/evidence capture, the
  device hardware) are Extended gaps, named from its own verbs.
- Nothing here surveils, identifies, predicts, or ingests any feed:
  the category-discipline exclusions (surveillance, facial
  recognition, predictive policing, real-time intelligence) stand at
  this tier exactly as at L2/L3. Facial recognition and predictive
  policing appear nowhere in this fork's description and are not
  attributed to it.
- No score, status, or validity is ever computed from a recorded
  citation treatment; the recorded strings are the record.
- Reuse: Group 34's code (this project's own Apache-2.0), 5 of 7
  `src/` modules byte-identical, the rest docstring-only; the
  Moderate baseline claim is **not** reused — see UNION-SPEC.md and
  `scratch/reuse-note.md`.
- Platform-layer, stated not claimed: encryption at rest is a
  deployment-layer control (TLS when configured); the build is a
  single-tenant reference deployment; demo identities are hooks, not
  an IdP (IA-2 stays with the embedding organization).
- The baseline mapping (800-53 Low ⇔ FAR 52.204-21) is a planning
  equivalence per the project crosswalk — not a FedRAMP
  authorization and not a CMMC certification.
- Tests: 82, all passing, including two negative controls; the
  membership-guard mutant was drilled against the real source in
  this tree (5 failures), restored, and SHA-256-verified — see
  [tests/README.md](tests/README.md).
