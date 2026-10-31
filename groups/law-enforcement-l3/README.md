# Law Enforcement L3-adjacent — merged build (DeadRamp Phase 2, Group 35)

A clean-room **records substrate at the High baseline**: the merged
open implementation for the Law Enforcement L3-adjacent sibling group
(2 forks, FedRAMP High ⇔ CMMC L3-adjacent), carried up whole from the
Group 34 L2 build under the Merge Rule and uplifted to High. Spec:
[UNION-SPEC.md](UNION-SPEC.md); per-fork spec sheets:
[specs/specs.json](specs/specs.json).

**Group character, stated plainly — starting with the zero-claim
honesty:** under Group 34's 9-family taxonomy, applied verbatim
(ids, labels, and patterns byte-identical, not re-tuned), this group
tags **0 claims in total — both spec sheets are zero-claim sheets**,
with the full descriptions preserved. That is a vocabulary mismatch,
not an absence of function: unlike the L2 pair (Lexis+® for
Government and Thomson Reuters Legal Research — legal research
platforms for government attorneys), both L3 siblings are genuine
digital-forensics platforms. Cellebrite Government Cloud (CGC)
extracts and analyzes forensic evidence from mobile devices; Magnet
One ingests, processes, analyzes, and reviews digital evidence.
The functions their descriptions claim in their own words — device
unlocking, evidence extraction, forensic analysis, evidence ingest
& processing, evidence review, chain-of-custody enforcement over
evidence, information sharing / collaboration over evidence, and
forensic reporting — are this group's own verticals, and every one
is **Extended**: each is a processing engine over evidence content,
which this records substrate never holds. The core below is Group
34's L2 core (11 functions), **carried, not claimed** by this
group's forks, under the core-boundary decision recorded in the
union spec: 0 of 11 core functions are claimed here, and a
wording/taxonomy artifact is not a downgrade.

**Privacy is the hard rule of this build, unchanged from Group 34.**
Records are keyed by opaque caller-supplied references only; no
entity shape can hold a real name, a case subject, evidence content,
or any content. Documents are registry metadata + SHA-256 checksums,
never content. Search queries and annotation notes are stored as
SHA-256 digests only — the store has no parameter that could accept
the text. Citation treatments are recorded verbatim and never
computed, normalized, or scored.

## Run

```bash
cd groups/law-enforcement-l3
PYTHONPATH=src python3 -m unittest discover -s tests     # the test suite
PYTHONPATH=src python3 -m lawenf serve --port 8797       # HTTP service
```

Demo users (demo identities, not an IdP — production identity is
the embedding organization's): `alice=admin`, `bob=member`,
`carol=viewer`, `dana=auditor`. Authenticate with `X-User` /
`X-Role` headers. Add `--certfile` / `--keyfile` to serve over TLS;
`--audit-log PATH` to persist the audit trail as JSONL;
`--max-failed-logins N` / `--lockout-seconds S` to tune the logon
lockout (defaults 3 failures / 300 s).

## What it does (the core, 11 functions, at the High baseline)

1. **Matter registry & members** — matters keyed by opaque refs,
   guarded open/closed lifecycle; membership is the boundary on
   every matter-scoped operation.
2. **Source registry** — legal sources (statute, case law,
   regulation, secondary, guidance, standard document) as metadata
   records. No content.
3. **Document registry** — metadata + SHA-256, guarded review
   lifecycle (`registered → in_review → reviewed`).
4. **Verify-by-content** — re-hash caller-supplied bytes and
   compare; stores nothing.
5. **Saved-search records** — query stored as a SHA-256 digest plus
   a result count.
6. **Annotation records** — note stored as a SHA-256 digest,
   targeted at a document, search, or source.
7. **Citation-check records** — treatment recorded verbatim.
8. **Registry reporting** — counts on read, treatment keys verbatim.
9. **Registry search** — literal search over registry metadata,
   membership-scoped; digests are never searchable.
10. **RBAC** — admin / member / viewer plus the High-baseline
    **auditor** role, over nine actions, layered with matter
    membership; unsuccessful-logon lockout at the service layer
    (AC-7 uplift).
11. **Audit log** — append-only, **hash-chained and tamper-evident**
    (AU-9/AU-3 uplift): every mutation and every denied attempt
    recorded, with fail-closed writes (AU-5), audit query/reduction
    (AU-6/AU-7), and chain verification via `GET /audit/verify`.

The six High uplifts in full: hash-chained audit, fail-closed audit
writes, audit query/reduction, chain verification endpoint, logon
lockout, and the auditor role — analysis in
[UNION-SPEC.md](UNION-SPEC.md).

## Endpoints

`GET /health` (no auth) · `GET /audit` (audit_read; optional filter
params `actor`, `action`, `target`, `since`, `until`) ·
`GET /audit/verify` (audit_read) · `GET|POST /matters` ·
`GET /matters/{id}` · `POST /matters/{id}/members|close|reopen` ·
`GET|POST /matters/{id}/sources` · `GET /matters/{id}/sources/{sid}` ·
`GET|POST /matters/{id}/documents` · `GET /matters/{id}/documents/{did}` ·
`POST /matters/{id}/documents/{did}/begin-review|complete-review|verify`
(`{content_b64}`) · `GET|POST /matters/{id}/searches` (`query_text` is
hashed by the service; `query_sha256` may be supplied directly) ·
`GET|POST /matters/{id}/annotations` (same digest discipline for
`note_text`) · `GET|POST /matters/{id}/citation-checks` ·
`GET /matters/{id}/report` · `GET /search?q=`

Permission matrix: admin = all nine actions, including `audit_read`;
member = all except `audit_read`; viewer = `matter_read` +
`report_read` only; auditor = `audit_read` only. Matter membership
is additionally required for every matter-scoped route (platform
admin excepted).

## Honesty section

- Claims: **0 tagged** across the two spec sheets under Group 34's
  fixed 9-family taxonomy, applied verbatim and not re-tuned. Both
  descriptions are preserved in full in the spec sheets. The
  near-misses (collaboration ×2, hosting_platform, access_control,
  legal_search, document_management) and corrections — Cellebrite's
  chain-of-custody sentence tags nothing; Magnet's
  security-controls sentence is assurance prose — are logged in
  `scratch/ARTIFACTS.md`. Zero is the honest result of a
  legal-research taxonomy meeting digital-forensics descriptions.
- The core is **carried, not claimed**: 0 of 11 core functions are
  claimed by this group's forks. Group 34's L2 core is carried up
  whole under the Merge Rule (union of baselines, highest tier
  wins) and uplifted to High, under the core-boundary decision
  recorded in the union spec — a wording/taxonomy artifact is not
  a downgrade.
- This group's own verticals (device unlocking; evidence
  extraction from mobile devices; forensic analysis engines;
  evidence ingest & processing pipelines; evidence review;
  chain-of-custody enforcement over evidence; information sharing /
  collaboration over evidence; forensic reporting) are **Extended** —
  specified and ranked in the union spec, not implemented. The
  substrate's checksums, verify-by-content, and hash chain are
  records-side analogues of chain-of-custody enforcement, stated as
  analogues, not equivalents.
- No score, status, or validity is ever computed from a recorded
  citation treatment; the recorded strings are the record.
- Nothing here surveils, identifies, predicts, or ingests any feed:
  the category-discipline exclusions (surveillance, facial
  recognition, predictive policing, real-time intelligence) are
  named Extended gaps in the union spec and are not built (0 claims).
- The Extended list carried from Group 34 (the legal corpora
  themselves, citation-validation engines, editorial enhancement
  systems, corpus search & relevance engines, AI/ML research
  assistance — 0 claims at either tier — and document content
  storage, rendering & redaction) remains Extended at this tier.
- Platform-layer, stated not claimed: MFA / authenticator
  management (IA-2(1)/(2), IA-5) is an IdP property — demo
  identities are hooks, not an IdP; FIPS-validated cryptography
  (SC-13) is not claimed — Python's standard library is not a
  FIPS-validated module; encryption at rest (SC-28) is a
  deployment-layer control (TLS only when configured); audit
  retention enforcement (AU-11) is not implemented; session
  lock/termination (AC-11/AC-12) is not implemented — per-request
  header auth, no session state; the build is a single-tenant
  reference deployment.
- The baseline mapping (800-53 High ⇔ 800-171's 110 practices plus
  selected SP 800-172 enhanced requirements) is a planning
  equivalence per the project crosswalk — not a FedRAMP
  authorization and not a CMMC certification. FedRAMP authorizes
  products; CMMC certifies organizations.
- Tests: the inherited Group 34 suite, adapted for the uplift, plus
  new uplift tests, including the negative controls: the inherited
  membership-guard and verify mutants (in-suite), and the new
  audit-tamper control at High (mutating a stored entry makes
  `verify_chain` report failure at exactly that index; a JSONL line
  edited on disk is detected after reload). The membership-guard
  mutation drill was performed against the real source in this
  tree, with results recorded in [tests/README.md](tests/README.md).

## Remainder addition

Per [`ADDENDUM.md`](ADDENDUM.md) (unit `addition:law-enforcement-l3`):
**TRAPWIRE Threat Detection and Analysis System** (TRAPWIRE, FedRAMP
High / Certified) joins the group as its third fork — previously
uncategorized in the source, assigned to Law Enforcement by the
remainder census from its own description. Under the group's
verbatim taxonomy it is the group's **third zero-claim sheet**
(0 raw hits across all 9 families; the group total stays 0 claims
across 3 forks): its vocabulary is physical threat detection over
human incident reports, a third vocabulary the legal-research
taxonomy does not reach. The functions its description asserts in
its own words — real-time threat detection and alerting, incident
reporting, pattern analysis, originator-controlled information
sharing, mass warning and notification, and an integration API —
are registered in the addendum as this fork's own verticals, all
Extended and not implemented. Category discipline is pinned at the
token level in the addendum: no facial-recognition, surveillance,
camera/sensor, or predictive-policing token exists in its text and
none is attributed; real-time detection and alerting *is* its own
described function and is booked as such. The original pair's
sheets stand exactly as shipped, and the core is unchanged
(`src/` byte-identical; tests 102 → 110).
