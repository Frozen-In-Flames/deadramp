# Law Enforcement — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **2 untiered forks** of Law Enforcement —
census unit `untiered:Law Enforcement` in `../../remainder.json`,
Untiered Set 17. **This is an untiered set, and that means something
specific:** every member's FedRAMP impact level is **Unknown** in
the source dataset. The source publishes no baseline for these
offerings, so **tier stays null**: no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to their
documented control claims; tier stays null in the registry until
the source publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec sheets are in
[`specs/specs.json`](specs/specs.json), each recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The 2 forks were spec'd under the category's existing 9-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Law Enforcement L2 group's original
shipped claim tables exactly — **2 of 2 forks, 13 of 13 claims,
deep-equal** — before tagging this set. Result here: **0 claims** —
**both forks are zero-claim**. The founding taxonomy is a
legal-research taxonomy, defined from the founding group's two
legal-research descriptions; these two operational descriptions (a
public-safety command-and-control platform and a
blockchain-intelligence investigation platform) fire none of its
phrases. The zeros are recorded in the union spec under Named
absences, not hidden or repaired — the same outcome this category
recorded at its L1 singleton (0 claims) and its L3-adjacent
addition (0 claims).

The build implements the category's **eleven-function substrate**
— the legal-research records machinery the founding group built —
carried **byte-identical** from the founding Law Enforcement L2
build (`../law-enforcement-l2/src/lawenf/`, 7 of 7 modules;
SHA-256 accounting below). The substrate is tier-independent
records code: the founding source contains no tier or baseline
machinery, so there was nothing tier-shaped to strip. **No core
function is claim-supported in this set** (the set carries 0
claims); every function is carried as substrate, not claimed, and
no function is claimed to be *attained* by either fork.

**Privacy is the hard rule of this build** (the founding group's
discipline, preserved exactly): records are keyed by opaque
caller-supplied references only; no entity shape can hold a real
name, a case subject, a party, an address, or any content.
Documents are registry metadata + SHA-256 checksums, never content.
Search queries and annotation notes are stored as SHA-256 digests
only — the store has no parameter that could accept the text.
Citation treatments are recorded verbatim and never computed,
normalized, or scored.

## The 2 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2628943632 | Pryme Infil, Inc. | Pryme Infil | 0 |
| FR2631258113 | TRM Labs, Inc. | TRM Labs on GovCloud | 0 |

In `forks.json` the set is mixed as filed: Pryme Infil is filed
under Law Enforcement, and TRM Labs on GovCloud is filed under
Cybersecurity & Risk Management; the census assigned both to this
category from their own descriptions (TRM's source business
categories include Law Enforcement), and the spec sheets record
the assignment. Authorization statuses as recorded are Legacy
FedRAMP Ready (Pryme Infil) and Initial Implementation (TRM
Labs) — a status is record data, not a claim.

## The 11 core functions

1. **Matter registry & members** — matters (the organizing
   container for a body of research) keyed by an opaque
   `matter_ref`, with a guarded lifecycle (`open` → `closed` →
   reopen) and a member list. Membership is the boundary every
   matter-scoped function enforces; writes to a closed matter are
   rejected.
2. **Source registry** — legal sources as metadata records inside
   a matter: opaque `source_ref`, a kind (`statute`, `case_law`,
   `regulation`, `secondary`, `guidance`, `standard_document`), and
   optional opaque jurisdiction / citation references. No content.
3. **Document registry** — uploaded documents as metadata +
   SHA-256: opaque `doc_ref`, checksum (validated lowercase hex),
   byte count, and a guarded review lifecycle (`registered` →
   `in_review` → `reviewed`). Content is never stored.
4. **Verify-by-content** — given bytes, recompute the SHA-256 and
   compare it to the registered checksum; returns the comparison,
   stores nothing.
5. **Saved-search records** — a saved search is a record: opaque
   `search_ref`, the query's SHA-256 digest (never the query), and
   a result count.
6. **Annotation records** — an annotation on a document, search,
   or source is a record: opaque `annotation_ref`, target, and the
   note's SHA-256 digest (never the note).
7. **Citation-check records** — a citation check is a record:
   opaque `citation_ref`, an optional link to a registered source,
   and the treatment **recorded verbatim** from the caller.
8. **Registry reporting** — counts computed on read: sources by
   kind, documents by status, saved searches, annotations,
   citation checks by recorded treatment (verbatim keys). No
   analytics engine, no computed score.
9. **Registry search** — literal substring search over registry
   metadata (references, kinds, statuses, recorded treatments),
   scoped to matters the actor may see. Never over content —
   there is none — and digests are never searchable.
10. **Access control (RBAC)** — platform roles `admin`, `member`,
    `viewer` with a permission matrix enforced on every operation,
    layered with matter membership (non-members cannot read or
    write a matter's records; the platform `admin` role can).
11. **Audit log** — an append-only audit trail: every matter,
    membership, source, document, search, annotation, and
    citation-check mutation, and every denied attempt, recorded
    with actor, action, target, and UTC timestamp. Optional JSONL
    file persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `mat-`, `src-`,
`doc-`, `sea-`, `ann-`, `cit-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m lawenf serve --host 127.0.0.1 --port 8797
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | all nine actions, including `audit_read` |
| `bob`   | member | all except `audit_read` |
| `carol` | viewer | `matter_read`, `report_read` |

Actions: `matter_read, matter_write, source_write, document_write,
search_write, annotation_write, citation_write, report_read,
audit_read`. Matter membership is additionally required for every
matter-scoped route (platform admin excepted). A permitted role
performing a forbidden action gets 403; validation failures get
400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a
client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |
| GET | `/matters` | matter_read | `{"matters": [...]}` (membership-scoped) |
| POST | `/matters` | matter_write | Body `{"matter_ref"}` → 201 matter dict |
| GET | `/matters/{id}` | matter_read | One matter dict |
| POST | `/matters/{id}/members` | (creator or admin) | Body `{"username"}` → matter dict |
| POST | `/matters/{id}/close` · `/reopen` | matter_write | → matter dict |
| GET | `/matters/{id}/sources?kind=` | matter_read | `{"sources": [...]}` |
| POST | `/matters/{id}/sources` | source_write | Body `{"source_ref", "kind", "jurisdiction_ref"?, "citation_ref"?}` → 201 |
| GET | `/matters/{id}/documents?status=` | matter_read | `{"documents": [...]}` |
| POST | `/matters/{id}/documents` | document_write | Body `{"doc_ref", "sha256", "size_bytes"}` → 201 |
| POST | `/matters/{id}/documents/{did}/begin-review` · `/complete-review` | document_write | → document dict |
| POST | `/matters/{id}/documents/{did}/verify` | matter_read | Body `{"content_b64"}` → verify dict (malformed base64 → 400) |
| GET | `/matters/{id}/searches` | matter_read | `{"searches": [...]}` |
| POST | `/matters/{id}/searches` | search_write | Body `{"search_ref", "query_text" \| "query_sha256", "result_count"}` → 201 (the service hashes `query_text`; the text is never stored) |
| GET | `/matters/{id}/annotations?target_id=` | matter_read | `{"annotations": [...]}` |
| POST | `/matters/{id}/annotations` | annotation_write | Body `{"target_kind", "target_id", "annotation_ref", "note_text" \| "note_sha256"}` → 201 (same digest discipline) |
| GET | `/matters/{id}/citation-checks` | matter_read | `{"citation_checks": [...]}` |
| POST | `/matters/{id}/citation-checks` | citation_write | Body `{"citation_ref", "treatment", "source_id"?}` → 201 |
| GET | `/matters/{id}/report` | report_read | The report dict |
| GET | `/search?q=` | matter_read | Registry search dict (membership-scoped) |

Entity dict shapes follow the founding contract exactly (see
`UNION-SPEC.md` of the founding group for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**91 tests, OK** at delivery: the founding group's 82-test core
suite carried with the code, plus 9 spec tests pinning this set
(exactly 2 sheets; membership exact against `remainder.json`; every
sheet's tier null / impact "Unknown"; the literal 0-claim total
with both forks zero-claim; the category-discipline tokens absent
from both descriptions; descriptions exact against the census
record; census citations verified verbatim). The category's
signature membership-guard mutation drill was re-run in this tree
— exactly 5 failures under the mutant, store restored and SHA-256
verified (see `tests/README.md`).

## Byte-identity accounting

`src/lawenf/` is carried from the founding group
`../law-enforcement-l2/src/lawenf/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `161220b0e2c1910a6c0dac9f15b017df11ceca7bc28ae621e9069830adc5907a` |
| `__main__.py` | `2cc842a0eaa5c724fb5c92ef067ecf11ad9dbbe8f4075b979f3132b484743a9e` |
| `access.py` | `34018d9c8510617b9c83b304266695924db1f684cfc0501d4c9096ca1df3f215` |
| `audit.py` | `88125ccc695306ddeb734e3768da52c026be0411eb8cafc95eb2f078162d08c9` |
| `errors.py` | `f523ffa9f6a7bf07511326efc5ae183ac3636b9affc9e90942f3d3740e5af5b3` |
| `service.py` | `8eb0013314e26792fb14ea8f1ee4eb26cb270f2db4dee27fab63a2ccb77358e6` |
| `store.py` | `13c8649dd24ee8372b6aa699cd47d9d5071eecdeb08bc31e204f0528ae4d3366` |

One honest note on the carry: the `__init__.py` docstring's first
line names the founding build ("DeadRamp Phase 2, Group 34 — Law
Enforcement L2 merged build"). It is carried verbatim — the code is
the founding group's code, and the label says whose it was; this
group's own docs (this README, the union spec) carry the tier-null
anchoring. The test suite is likewise carried (the founding suite
in full — the founding L2 group has no additions module), with one
labeling fix in `tests/lawenf_helpers.py` (its docstring now names
this untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 2 offerings (both "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family in
from any baseline.

Documented by at least one fork in this set (all at the prose
tier — control language in the descriptions, traced and quoted,
never converted into taxonomy claims):

- **Identification & authentication (IA)** — TRM Labs on
  GovCloud: "a common identity and access management layer." An
  identity layer is asserted; no authentication mechanism (no
  MFA, SSO, or credential phrase) is named.
- **Access control (AC)** — documented **in part**, via the same
  TRM Labs sentence: an access *management* layer is asserted.
  The founding taxonomy family's exact phrase ("secure access
  controls") does not occur, so this stands at prose weight only.
- **Cryptographic protection (SC)** — documented at **prose
  weight**, via Pryme Infil: "encrypted messaging" asserts
  encryption of the offering's messaging function. No algorithm,
  standard, or FIPS claim is made by the fork or recorded here,
  and the build performs no cryptography of its own.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, AU, CA, CM, CP, IR, MA, MP,
PE, PL, PM, PS, RA, SA, and SI **as control claims** — is asserted
by no description in the set. Two bounds, stated explicitly
because the words occur: Pryme Infil's "risk assessments" names
an operational function offered to agencies, not RA/CA language
about the offering itself; and its "after-action documentation"
is operational documentation, not audit logging (AU). If the
source later publishes an impact level for either of these
offerings, the tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for either fork or for
  itself. The forks' recorded authorization statuses are source
  data, not claims by this build, and a fork's documented control
  language is recorded as *its* claim, never as the build's
  control attainment.
- **Zero claims, recorded not repaired.** The founding taxonomy is
  a legal-research taxonomy; neither operational description
  fires any of its phrases, so both forks stand at 0 claims and no
  core function is claim-supported. The substrate is carried
  whole anyway. Nothing was back-filled, and the taxonomy was not
  re-tuned, to make the set look complete.
- **Category discipline held.** Surveillance, facial recognition,
  predictive policing, real-time intelligence feeds, and
  camera/sensor monitoring are attributed to **neither** fork:
  the tokens `facial`, `predictive`, `surveillance`, `camera`,
  `sensor` and the phrase `real-time intelligence` occur 0 times
  in each description, counted on the descriptions themselves and
  pinned by test. Pryme Infil's own words are "GPS mapping" and
  "real-time team coordination" (mapping and coordination
  substance, Extended gaps); TRM's is "glass-box attribution" for
  cryptocurrency flows. This build surveils nothing, identifies
  no one, predicts nothing, and ingests no feed.
- **Extended functions are specified, not implemented.** The union
  spec ranks 9 functions; the substrate behind the Core slices is
  implemented here. NOT implemented (new gaps from this set):
  command-and-control & operational planning platform;
  real-time team coordination & encrypted messaging engines and
  real channel transports; GPS mapping & location services;
  operational risk-assessment tooling; after-action documentation
  & reporting engine; blockchain intelligence & multi-chain
  investigation graph engine; all-source intelligence fusion &
  lead/identity resolution; AI investigation models; workspace
  multi-tenancy. The founding group's engine gaps (the legal
  corpora themselves, citation-validation engines, editorial
  enhancement systems, corpus search & relevance engines, document
  content storage/rendering) remain registered under the founding
  group.
- **The build performs no cryptography of its own.** One fork
  documents an encryption claim about its own messaging function;
  the substrate does no encryption — TLS is a deployment-layer
  option when a certificate is configured, and FIPS-validated
  crypto (SC-13) is not claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix and matter
  membership on those hooks and ships no identity provider, no
  credential store, and no authentication of its own (IA-2 stays
  with the embedding organization).
