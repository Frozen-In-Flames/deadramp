# Research — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **4 untiered forks** of Research —
census unit `untiered:Research` in `../../remainder.json`,
Untiered Set 9. **This is an untiered set, and that means
something specific:** every member's FedRAMP impact level is
**Unknown** in the source dataset. The source publishes no
baseline for these offerings, so **tier stays null**: no tier is
assigned, no CMMC equivalence is drawn, and this build asserts
**no control baseline**. Per PIPELINE.md, untiered offerings
"build to their documented control claims; tier stays null in
the registry until the source publishes a baseline." The union
contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and
`cmmc_tier: null`, pinned by tests.

The 4 forks were spec'd under the category's existing 9-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding Research L2 group's
original shipped claim table exactly — **1 of 1 forks, 9 of 9
claims, deep-equal** against the sheet at the original ship
commit — before tagging this set. Result here: **0 claims across
the set; all 4 forks are zero-claim forks**, recorded under Named
absences in the union spec, not hidden or repaired. The taxonomy
was defined from the founding fork's single platform sentence
and its patterns are that sentence's literal phrases; these four
research-adjacent offerings (market/policy intelligence, an
eClinical platform, identity intelligence, supplier discovery)
use none of them — the same outcome the category's Research L1
singleton recorded under the same taxonomy.

The build implements the category's **eleven-function substrate**
— the research-data records machinery — carried from the founding
Research L2 build (`../research-l2/src/research/`, 6 of 7 modules
byte-identical; `__init__.py` differs by its docstring only,
which named the founding baseline there and names tier null
here; SHA-256 accounting below). The substrate is
tier-independent records code: the founding source contains no
tier or baseline machinery beyond that docstring. Where the
founding contract's text says access control and audit are L2
baseline hooks, read it here as **baseline-neutral hooks**: at
tier null they are substrate, claimed against no baseline. **No
core function is claim-supported in this set** — every function
is carried, not claimed.

## The 4 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2632054521 | Leadership Connect, Inc. | Leadership Connect | 0 |
| FR2632054491 | OpenClinica LLC | OpenClinica4 (OC4) | 0 |
| FR2701557049 | Sixtyfourai | Sixtyfour Identity Intelligence Platform | 0 |
| FR2631747315 | Sustainment Technologies Inc. | Sustainment Digital Manufacturing Hub | 0 |

In `forks.json` the set is mixed as filed: Leadership Connect
carries Analytics, OpenClinica Health & Wellness, Sixtyfour
Artificial Intelligence (AI), and Sustainment Operations
Management; the census assigned all four to Research from their
own descriptions, and the spec sheets record the assignment.
Three of the four carry "Research" among their source business
categories; Sustainment does not — its assignment rests on its
description's market-research function alone. Authorization
status as recorded is Initial Implementation for all four — a
status is record data, not a claim.

## The 11 core functions

1. **Data commons registry & membership** — commons records
   (`com-`): name, title, kind (`commons` / `ecosystem` / `mesh`
   — the founding description's own nouns), an opaque sponsor
   reference, an owner and a member list. Membership is the
   boundary every other commons-scoped function enforces. The
   lifecycle is event-driven: `draft → active → retired`, changed
   only through recorded lifecycle actions.
2. **Organization registry (opaque references)** — organizations
   (`org-`) known only by a caller-supplied opaque `ref` and a
   label. The record shape is pinned: no field can hold a real
   identifier.
3. **Workspace registry** — workspaces (`ws-`) inside a commons:
   name and a stated purpose — the records form of the workspaces
   the category's founding description names.
4. **Dataset registry (metadata + checksums only)** — datasets
   (`ds-`) inside a commons: name, description, an access tier
   (`open` / `controlled`), a SHA-256 checksum, and a byte size.
   **Content is never stored**, and the record shape is pinned to
   exactly 9 keys, so no field exists that could hold research
   subject data or a dataset payload. A dataset can be verified
   against caller-supplied content (hashed transiently, compared,
   discarded).
5. **Access request records** — requests (`ar-`) for controlled
   datasets: the requester, a stated purpose, and a requested
   duration in days. **Requests against open datasets are
   rejected by design** — open data needs no request, and a
   request record for one would be a false gate. Lifecycle:
   `pending → approved / denied`, plus `withdrawn` while pending.
6. **Decision records** — a decision (`dec-`) on a pending
   request records the decider's outcome and note. One seam is
   enforced in the store: the decider is never the requester
   (separation of duties).
7. **Access grant records** — an approval mints a grant (`gr-`):
   the dataset, the grantee, a start, and an expiry computed from
   the requested duration. A grant's status (`scheduled` /
   `active` / `expired` / `revoked`) is **derived at read** from
   the start, expiry, and revocation timestamp against the read
   clock — **never stored**; the stored record carries no
   `status` key. Grants are time-boxed and **confer nothing by
   themselves**; actual data delivery is Extended.
8. **Search & summary reporting** — literal case-insensitive
   substring search over accessible commons, organizations, and
   datasets in accessible commons; and a per-commons summary
   computed on read from records only: workspace count, dataset
   counts by tier, request counts by status, grant counts by
   derived status. Counts — never scores; no record shape carries
   a field for a score.
9. **API access** — every function above is exposed over a REST
   API (JSON), so the service composes with anything that speaks
   HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with commons membership
    (non-members cannot read or write a commons' content; the
    platform `admin` role can).
11. **Audit log** — an append-only audit trail: every commons,
    membership, organization, workspace, dataset, request,
    decision, grant, and revocation mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `com-`, `org-`,
`ws-`, `ds-`, `ar-`, `dec-`, `gr-`. Durations are whole days:
booleans, floats, and strings are rejected at the boundary.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m research serve --host 127.0.0.1 --port 8798
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening. (Default port is 8798.)

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | read, create_commons, enter, decide, record, manage_members, audit_read, admin |
| `bob`   | member | read, create_commons, enter, decide, record |
| `carol` | viewer | read |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client. Denied attempts are audited with the action
suffixed `:denied`.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |
| GET | `/search?q=` | read | `{"commons": [...], "organizations": [...], "datasets": [...]}` |
| POST | `/commons` | create_commons | Body `{"name", "title", "kind", "sponsor_ref"}` → 201 commons view |
| GET | `/commons` | read | Commons the actor belongs to (all for admin) |
| GET | `/commons/{id}` | read | One commons view |
| POST | `/commons/{id}/members` | manage_members | Body `{"username"}` |
| POST | `/commons/{id}/activate` | record | From `draft` only |
| POST | `/commons/{id}/retire` | record | From `draft` or `active` |
| GET | `/commons/{id}/summary` | read | Counts computed on read; accepts `?now=` |
| POST | `/organizations` | enter | Body `{"ref", "label"}` → 201 record |
| GET | `/organizations` | read | List organizations |
| GET | `/organizations/{id}` | read | One record |
| POST | `/organizations/{id}` | enter | Update the label |
| POST | `/commons/{id}/workspaces` | record | Body `{"name", "purpose"}` → 201 record |
| GET | `/commons/{id}/workspaces` | read | List workspaces in a commons |
| GET | `/workspaces/{id}` | read | One record |
| POST | `/commons/{id}/datasets` | record | Body `{"name", "description", "access_tier", "sha256", "size_bytes"}` → 201 record (metadata + checksum only) |
| GET | `/commons/{id}/datasets` | read | List datasets; `?access_tier=` filter |
| GET | `/datasets/{id}` | read | One record |
| POST | `/datasets/{id}/verify` | read | Body `{"content": "..."}` — UTF-8-encoded, hashed transiently, compared, discarded |
| POST | `/datasets/{id}/access-requests` | enter | Body `{"purpose", "duration_days"}` → 201; controlled datasets only |
| GET | `/datasets/{id}/access-requests` | read | List requests for a dataset |
| GET | `/access-requests/{id}` | read | One record |
| POST | `/access-requests/{id}/decide` | decide | Body `{"approve", "note"?, "starts_at"?}`; never the requester; approval returns the minted grant view |
| POST | `/access-requests/{id}/withdraw` | enter | From `pending` only |
| GET | `/commons/{id}/grants` | read | List grants; `?status=` filters on the derived status; `?now=` |
| GET | `/grants/{id}` | read | Grant view with derived `status`; `?now=` |
| POST | `/grants/{id}/revoke` | decide | Records the revocation event |

Record shapes are pinned (see `UNION-SPEC.md` for every dict
shape); the stored grant record is `{id, dataset_id, commons_id,
request_id, grantee, starts_at, expires_at, revoked_at,
created_by, created_utc}` — no `status` key, by design.

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**93 tests, OK** at delivery: the founding group's 85-test core
suite carried with the code (its additions module, which pins a
different census unit, is not carried), plus 8 spec tests pinning
this set (exactly 4 sheets; membership exact against
`remainder.json`; every sheet's tier null / impact "Unknown";
descriptions exact-equal to the census record; the literal claim
table — 0 claims, all four forks zero-claim; census citations 6/6
verbatim). The category's signature grant-derivation mutation
drill was re-run in this tree — exactly 7 failures under the
mutant, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/research/` is carried from the founding group
`../research-l2/src/research/` — **6 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__main__.py` | `8f9a3225707966b7bb5b930bd9f2051fec8e9939697ba0071c44d7b0b927b79f` |
| `access.py` | `5a40a8dd9c454963589a8a4d9aa8357065eace597c0b91ae028bc8632eaa08fe` |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` |
| `errors.py` | `322d770d2816d95a8efe3f0e55b89d6b566e699d19264f369a23f7b24efdfcae` |
| `service.py` | `0c262cbbb9f69b773ac19f5def3ae425ebb93e03f28dc635ca57bd655e51594a` |
| `store.py` | `ff43a9acc78d6a65b527632c69923c91c5cfdb3716bc63d9efe56103d04bb417` |

`__init__.py` differs from the founding module by its docstring
only: the founding text named the FedRAMP Moderate / CMMC L2
baseline; this tree's text names the untiered set and tier null.
No code differs. (SHA-256 in this tree:
`83eefe19e186861519a9c9c4a2767ce191c957ab8ac633103a3e0d4c40a66778`.)

The test suite is likewise carried (the founding suite minus its
additions module), with one labeling fix in
`tests/research_helpers.py` (its docstring now names this
untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 4 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline.

**Taxonomy tier: none** — no taxonomy family fires in this set,
so no documented control claim stands at that tier.

Documented at the **prose tier** (control language in sentences
that fired no family, traced and quoted, never converted to
claims):

- **Identification & authentication (IA)** — 1 fork: Leadership
  Connect — "agency user account and profile records,
  authentication and session data, single sign-on identity
  assertions where an agency has configured federated access".
- **Audit (AU)** — 1 fork: Leadership Connect — "usage and audit
  records associated with individual agency users" (the founding
  taxonomy has no audit family; the language stands at prose
  weight only).

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AC (no sentence asserts access
control or enforcement) and SC (no encryption language occurs
anywhere in the set) — is asserted by no description here.
Sustainment's "purpose-built for federal security and compliance
requirements" is posture prose and is explicitly **not** a
documented control claim. If the source later publishes an impact
level for any of these offerings, the tier is recorded then and
not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **Carried, not claimed — stated once, plainly.** Zero taxonomy
  claims stand in this set, so **none** of the eleven core
  functions is claim-supported here. The substrate is the
  category's records machinery carried whole from the founding
  build; carrying it asserts nothing about what these four forks
  do. Their own described engines are Extended, below.
- **Extended functions are specified, not implemented** (see
  `UNION-SPEC.md` for the full register): the forks' own engines
  — market & policy intelligence, contract-award analysis,
  relationship-graph analytics, saved-search/alerting, clinical
  EDC, eConsent/eCOA, clinical reporting, identity resolution &
  investigation, ongoing identity monitoring, supplier discovery,
  supplier intelligence — and the category's standing tail: the
  data commons runtime, ingestion/ETL, harmonization, indexing
  over dataset contents, query & analysis engines, cohort
  building, cross-commons federation, data delivery, enforcement
  on actual data reads, and an identity provider.
- **Privacy is structural, not procedural.** Records carry opaque
  references and metadata only; dataset records are metadata +
  checksum with a pinned 9-key shape — there is no field in
  which research subject data, a genomic or clinical payload, or
  dataset content could be placed — and verification content is
  hashed in transit through the call and discarded. Nothing is
  scored or ranked anywhere, and no record shape has a field for
  a score — pinned by tests.
- **Grants are records.** A grant's status is derived at read and
  never stored; grants are time-boxed and confer nothing by
  themselves. No data moves in this build. Requests against open
  datasets are rejected by design — the build does not create
  false gates.
- **The build performs no cryptography of its own.** No fork in
  this set documents an encryption claim; the substrate does no
  encryption — TLS is a deployment-layer option when a
  certificate is configured, encryption at rest is
  deployment-layer, and FIPS-validated crypto (SC-13) is not
  claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix and commons
  membership on those hooks and ships no identity provider, no
  credential store, and no authentication of its own. (Leadership
  Connect's documented SSO assertions are that fork's own
  federation surface, recorded as its claim — not implemented
  here.)
- **Named absences stand.** All nine taxonomy families have 0
  claimants in this set and all four forks are zero-claim.
  Nothing was back-filled to make the set look complete.
