# Travel Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **1 untiered fork** of Travel
Management — census unit `untiered:Travel Management` in
`../../remainder.json`, Untiered Set 28, the last untiered set.
**This is an untiered set, and that means something specific:**
the member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for this offering, so
**tier stays null**: no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented
control claims; tier stays null in the registry until the source
publishes a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); the per-fork spec sheet is in
[`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned
by tests.

The fork was spec'd under the category's existing 9-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the
extractor first reproduced the founding Travel Management L2
group's original shipped claim tables exactly — **both sheets
deep-equal: GO.gov 9 of 9 claims, and the group's remainder
addition fork (mLINQS) 0 of 0** — before tagging this set.
Result here: **0 claims** — the set's only fork is a
**zero-claim fork**. Its entire marketplace description is one
sentence ("Aggregation of travel data to support comprehensive
reporting and analysis."), and none of the taxonomy's nine
verbatim patterns, all defined from the founding fork's
suite-list vocabulary, appears in it. The zero is recorded in
the union spec under Named absences, not hidden or repaired;
the fork's described function is registered as a gap in its own
name.

The build implements the category's **thirteen-function
substrate** — the travel records machinery the category's
claimed surfaces presuppose — carried **byte-identical** from
the founding Travel Management L2 build
(`../travel-management-l2/src/travel/`, 7 of 7 modules; SHA-256
accounting below). The substrate is tier-independent records
code: the founding source contains no tier or baseline machinery
of its own, so there was nothing tier-shaped to strip. Where the
founding contract's text rests a function on the Moderate
baseline's control families, read it here as **baseline-neutral
substrate**: at tier null the hooks are carried, claimed against
no baseline. **Claim support, stated honestly: none of the
thirteen functions is claim-supported by this set** — the set's
only fork claims no family. The functions are carried, not
claimed, exactly as they stood for the founding group's own
zero-claim addition fork.

## The 1 fork

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2632558740 | Cornerstone Information Systems | Upstream Gov | 0 |

In `forks.json` the fork is filed "Travel Management" (source
business categories [Travel Management, Accounting, Analytics]),
SaaS, Government Community Cloud, authorization status Initial
Implementation — a status is record data, not a claim. Two
cached records carry this ID with byte-identical descriptions;
one spec sheet stands. With this set, every Travel Management
fork in the registry is spec'd: the founding fork at L2
(9 claims), its addition fork (0), and this untiered fork (0).

## The 13 core functions

1. **Organization registry & membership** — organizations
   (`org-`) that scope every other record; membership is
   enforced on every organization-scoped operation, on top of
   the role matrix.
2. **Traveler registry** — travelers (`trv-`) known only by an
   opaque caller-supplied reference and a label; the record
   shape is pinned to exactly 6 keys, so no field can hold real
   personal data.
3. **Trip authorization records** — authorizations (`auth-`)
   with a destination label, purpose, depart/return dates, and
   an authorized amount in integer cents. Lifecycle
   `draft → submitted → approved / declined` is event-driven and
   stored; the trip **phase** (`upcoming` / `in_progress` /
   `completed`) is derived at read from the dates, never stored.
4. **Authorization decision records** — decisions (`dec-`); the
   decider is never the requester (separation of duties).
5. **Expense report records** — reports (`exp-`) against an
   approved authorization, with the same lifecycle and decision
   discipline.
6. **Expense line item records** — items (`itm-`) in generic
   substrate categories (lodging, meals, transport,
   incidentals, other), integer cents, addable only while the
   report is a draft. The report total is derived from its
   items, never stored.
7. **Expense decision records** — the decider is never the
   report's creator.
8. **Voucher records** — vouchers (`vou-`) against an approved
   report, under the **voucher-cap invariant**: cumulative
   vouchers never exceed the report's total. A second cap
   stands at report submission: cumulative submitted/approved
   report totals never exceed the authorization's authorized
   amount. Vouchers are records; no money moves.
9. **Notification records** — notifications (`ntf-`), recorded,
   not delivered.
10. **Integration definition registry** — integration
    definitions (`int-`) registered as data. The registry
    **never executes** a definition; that is pinned by test.
11. **Search & summary reporting** — substring search across
    travelers, authorizations, and reports; per-organization
    summaries computed on read as counts and money sums. Never
    scores.
12. **REST API** — every function above over a JSON REST API.
13. **Append-only audit log** — every mutation and every denied
    attempt, with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial record, no id
consumed). All money is integer cents: floats, booleans, and
strings are rejected at the boundary.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m travel serve             # http://127.0.0.1:8799
PYTHONPATH=src python3 -m travel serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m travel serve --certfile cert.pem --keyfile key.pem   # TLS
```

## Demo users, roles, and permissions

The server ships documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role   | Can do |
|---------|--------|--------|
| `alice` | admin  | everything, including reading the audit log |
| `bob`   | member | enter, decide (never his own records), record |
| `carol` | viewer | reads only |

(The test fixtures add `dana`, a second member who decides
records bob created, and `erin`, a member of no organization.)
A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client. Denied attempts are audited with the
action suffixed `:denied`.

## API endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?org_id=&q=` | read | `{"travelers": [...], "authorizations": [...], "expense_reports": [...]}` |
| `GET /organizations` · `POST /organizations` | read / enter | create → 201 |
| `GET /organizations/{id}` | read | membership required |
| `GET /organizations/{id}/members` · `POST` | read / manage_members | POST body `{"username": ...}` |
| `GET /organizations/{id}/summary` | read | counts and sums, computed on read |
| `GET /organizations/{id}/travelers` · `POST` | read / enter | create → 201 |
| `GET /travelers/{id}` | read | |
| `GET /organizations/{id}/authorizations` · `POST` | read / enter | create → 201; `?now=` on reads |
| `GET /authorizations/{id}` | read | derived `phase`, `claimed_cents`, `reimbursed_cents` |
| `POST /authorizations/{id}/submit` · `/decide` | enter / decide | decide body `{"approve": bool, "note": ...}`; never the creator |
| `GET /authorizations/{id}/decisions` | read | |
| `GET /authorizations/{id}/expense-reports` · `POST` | read / enter | create → 201; authorization must be approved |
| `GET /expense-reports/{id}` | read | derived `total_cents`, `reimbursed_cents`, `remaining_cents` |
| `GET /expense-reports/{id}/items` · `POST` | read / enter | POST → 201; draft reports only |
| `POST /expense-reports/{id}/submit` · `/decide` | enter / decide | submit checks the authorization cap |
| `GET /expense-reports/{id}/vouchers` · `POST` | read / record | POST → 201; voucher cap enforced |
| `GET /organizations/{id}/notifications` · `POST` | read / record | recorded, not delivered |
| `GET /organizations/{id}/integrations` · `POST` | read / record | definitions only; never executed |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**107 tests, OK** at delivery: the founding group's 96-test core
suite carried with the code (its additions module, which pins a
different census unit, was not carried), plus 11 spec tests
pinning this set (exactly 1 sheet; membership exact against
`remainder.json`; the sheet's tier null / impact "Unknown"; the
literal 0-claim table and whole-taxonomy zero set; the
description verbatim against both cached records; census
citation accounting; the empty-catalogue pin; the founding five
absences at the token level; near-miss and control-language
pins). The category's signature voucher-cap mutation drill was
re-run in this tree — exactly 5 failures under the mutant, the
founding shipped drill's identical set, store restored and
SHA-256 verified (see `tests/README.md`).

## Byte-identity accounting

`src/travel/` is carried from the founding group
`../travel-management-l2/src/travel/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `8cbe7e0472952522ee28fbff76be8b0c6272f271fc24e3f98505a8fc6838b9f2` |
| `__main__.py` | `0e003fa47fc45b3d5263cbbb27fdfd71484d355784d27275c56216f9a15c0ac0` |
| `access.py` | `469946bc9f3bc6db3fdd709183b2d6a60bb63f1d7f0dbec1ddc21fb687d18da0` |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` |
| `errors.py` | `688a6f8c8bee02935264a9a9af7fd28ec6fb1db32427d3b32ad4fa7b4cd20d79` |
| `service.py` | `ae438f4ea12dcc598f8e926a2cd5de09f8d8a4ba21b262822f221e15ae9ebf43` |
| `store.py` | `a4098ea612bbffa7fed89323e39752c79f28e08ce1e343f3ece92d5517da61ce` |

The tree contains exactly the package — no files sit flat at
`src/` root. The test suite is likewise carried (the founding
suite minus its additions module); no carried test file needed a
labeling change (none names the founding tier). Full accounting
is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. A documented control claim would be the fork's
claim about itself, recorded with its evidence in
`UNION-SPEC.md` and `specs/specs.json`.

**Documented by this set: none.** The fork's one-sentence
description contains no control language of any family —
token-verified: "security", "privacy", "compliance", "access
control", "audit", "encrypt", "authentication", "single
sign-on", "sso", "multi-factor", "mfa", "role-based" — none
occurs (recorded in `scratch/absence_check.json`).

**Not documented:** every NIST SP 800-53 control family — AC,
AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PM, PS, RA, SA, SC,
SI — is asserted by no sentence in the description, and nothing
is filled in from any baseline. The record's deployment model,
"Government Community Cloud", is record metadata outside the
description — platform metadata, not a control claim. If the
source later publishes an impact level for this offering, the
tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP
  baseline, no CMMC tier, and no authorization — for the fork
  or for itself. The fork's recorded authorization status is
  source data, not a claim by this build.
- **Zero claims, plainly.** The set's only fork claims none of
  the category's 9 functions. Nothing was back-filled to make
  the set look complete, and the taxonomy was not re-tuned to
  catch the fork's sentence.
- **Extended functions are specified, not implemented.** NOT
  implemented: the travel data aggregation & analytics engine
  (this fork's described function entire, registered as a new
  gap in its own name); the travel booking & reservation
  engine; carrier, hotel & GDS reservation integrations;
  payment & disbursement execution (vouchers are records; no
  money moves); receipt capture & imaging / OCR; integration
  connector engines (the registry holds definitions and never
  executes them); notification delivery transport; report
  generation engines & dashboards beyond registry summaries;
  employee relocation processing and policy-automation
  engines; identity provider / identity management service.
- **The founding build's five checked absences stand on this
  fork's words too.** No booking, per-diem, reimbursement,
  approval, or receipt vocabulary appears in this description
  either — all five survive, token-verified. Authorization and
  decision records and voucher records are in the Core only as
  the records forms the category's claimed surfaces
  presuppose, under the founding core-boundary decisions, not
  dressed up as this fork's claims.
- **Records of trips and authorizations are Core; travel
  itself is not performed.** Statuses that depend on dates or
  other records (trip phase, report totals and balances) are
  derived at read time and never stored — pinned by tests.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  and `carol` are documented demo identities supplied by
  header; the service enforces the role permission matrix and
  organization membership on those hooks and ships no identity
  provider, no credential store, and no authentication of its
  own. IA-2 stays with the embedding organization. Encryption
  is TLS when a certificate is configured; encryption at rest
  is a deployment-layer property; the deployment is a
  single-tenant reference deployment.
