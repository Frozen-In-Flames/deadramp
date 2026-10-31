# System Administration — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **4 untiered forks** of System
Administration — census unit `untiered:System Administration`
in `../../remainder.json`, Untiered Set 10. **This is an
untiered set, and that means something specific:** every
member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for these offerings,
so **tier stays null**: no tier is assigned, no CMMC
equivalence is drawn, and this build asserts **no control
baseline**. Per PIPELINE.md, untiered offerings "build to
their documented control claims; tier stays null in the
registry until the source publishes a baseline." The union
contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec
sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier:
null`, pinned by tests.

The 4 forks were spec'd under the category's existing
8-function taxonomy **verbatim** (AST-parsed out of the
founding group's extractor, never re-tuned). This taxonomy is
unusual: the founding group is a singleton new category, so
its families are the founding fork's own exact phrases.
Taxonomy-verbatim proof: the extractor first reproduced the
founding System Administration L2 group's original shipped
claim table exactly — **1 of 1 forks, 8 of 8 claims,
deep-equal** — before tagging this set. Result here: **0
claims across the set; all 4 forks claim zero families.** The
mechanical pass produced no raw hits at all — no taxonomy
phrase occurs in any of the four descriptions — and the
near-misses are itemized in `scratch/ARTIFACTS.md`, not rounded
up. The zeros are recorded under Named absences in the union
spec, not hidden or repaired.

The build implements the category's **twelve-function
substrate** — the records machinery a managed system
administration service acts on — carried **byte-identical**
from the founding System Administration L2 build
(`../system-administration-l2/src/sysadmin/`, 7 of 7 modules;
SHA-256 accounting below). **In this set the substrate is
carried, not claimed:** no core function is claim-supported by
any of these forks, because their descriptions fire no family.
That is stated plainly in the union spec's core-boundary
decision. Where the founding contract's text (and the carried
`__init__.py` docstring) says "L2", read it here as the
founding group's label on carried code: at tier null the
access-control and audit hooks are baseline-neutral substrate,
claimed against no baseline.

## The 4 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2700555848 | Dynatrace | Dynatrace Platform for FedRAMP Class D (High) | 0 |
| FR2630354491 | Freshworks | Freshworks for Government | 0 |
| FR2217348295 | NetApp | Cloud Insights | 0 |
| FR2701457585 | PDQ | PDQ for Government | 0 |

In `forks.json` the set is mixed as filed: Dynatrace and
NetApp are filed "Uncategorized (none in source)", Freshworks
under Operations Management, and PDQ under Cybersecurity &
Risk Management; the census assigned all 4 to System
Administration from their own descriptions, and the spec
sheets record the assignment. Authorization statuses as
recorded span Initial Implementation (3) and FedRAMP In
Process (1) — a status is record data, not a claim.
Dynatrace's product **name** carries "(High)" while its
record's impact level is Unknown: a name does not move a tier,
and none is inferred (the mirror of the founding group's
artifact, where the fork's prose said "High baseline level"
and its record said Moderate).

## The 12 core functions

1. **Customer organizations & membership** — customer
   organizations (`org-`): an opaque caller-supplied `ref`, a
   label, an owner, and a member list. Membership is the
   boundary every other core function enforces.
2. **Managed system registry** — managed systems (`sys-`)
   belonging to an organization: an opaque `ref` (unique per
   organization), a label, a `kind` from the description
   vocabulary (`operating_system` / `platform_service`), and
   an opaque `platform_ref` for the hosting platform. The
   record shape is **pinned** — exactly nine keys, none of
   which can hold a hostname, address, or credential of a live
   system. Lifecycle `state` (`registered` / `retired`) is
   event-driven and stored.
3. **Application registry** — applications (`app-`) hosted on
   a managed system: an opaque `ref` (unique per
   organization), a label, and the hosting system. The record
   shape is **pinned** — exactly eight keys.
4. **Service request records** — requests (`req-`) against a
   managed system (optionally an application on it), of kinds
   `support`, `maintenance`, `access`, `other`, with a
   verbatim summary, a due date, and the lifecycle
   `open → in_progress → resolved`, plus `cancelled`.
   Cancellation is restricted to the requester or a platform
   admin. Recording a request performs no work.
5. **Derived request status** — a request's read view derives
   `overdue` (still open or in progress, and its due date is
   before the read date; resolved and cancelled requests are
   never overdue, and a request due today is not overdue) at
   read time. It is never stored — the stored request record
   carries no such key, pinned by test.
6. **Change records** — changes (`chg-`) against a managed
   system (optionally an application on it), of kinds `patch`,
   `configure`, `provision`, `decommission`, with a verbatim
   summary and the lifecycle `requested → approved → closed`,
   plus `rejected` and `cancelled`. The decider is never the
   requester (**separation of duties**, enforced in the
   store), and closing a change alters no system or
   application record — both pinned by test.
7. **Control inheritance records** — control records (`ctl-`)
   per managed system: a control reference and its recorded
   `source` — `inherited` (satisfied by the underlying hosting
   platform), `local`, or `shared` — with an optional note,
   one record per control per system. Dispositions are carried
   verbatim; **no posture, score, or health value is derived
   from them**, enforced by a recursive key scan over every
   view.
8. **Registry search** — literal case-insensitive substring
   search over accessible systems, applications, requests, and
   changes. An empty query returns no records (the adjudicated
   reading, recorded in `tests/README.md`).
9. **Registry summary** — a per-organization summary computed
   on read from records only: system counts by kind and state,
   application count, request counts by status plus the
   derived overdue count, change counts by status, and control
   counts by source. Counts — never scores.
10. **API access** — every function above is exposed over a
    REST API (JSON), so the service composes with anything
    that speaks HTTP.
11. **Access control** — role-based access hooks: platform
    roles `admin`, `member`, `viewer` with a permission matrix
    enforced on every operation, layered with organization
    membership (non-members can neither read nor write an
    organization's content; the platform `admin` role can).
12. **Audit log** — an append-only audit trail: every
    organization, membership, system, application, request,
    change, and control mutation, and every denied attempt,
    recorded with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `org-`, `sys-`,
`app-`, `req-`, `chg-`, `ctl-`. Records carry opaque
references only — no entity shape has a field for a hostname,
IP address, or credential, so none can be stored, leaked, or
transmitted by this build.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m sysadmin serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

Example flow:

```bash
curl -s -X POST localhost:8000/organizations \
  -H 'X-User: bob' -H 'X-Role: member' \
  -d '{"ref":"AGENCY-1","label":"Agency One Systems"}'
curl -s -X POST localhost:8000/organizations/org-1/systems \
  -H 'X-User: bob' -H 'X-Role: member' \
  -d '{"ref":"SYS-OS-1","label":"Primary OS instance","kind":"operating_system","platform_ref":"PLAT-A"}'
curl -s -X POST localhost:8000/organizations/org-1/requests \
  -H 'X-User: bob' -H 'X-Role: member' \
  -d '{"system_id":"sys-1","request_kind":"maintenance","summary":"Apply monthly OS maintenance","due_date":"2026-06-10"}'
curl -s 'localhost:8000/requests/req-1?as_of=2026-06-15' \
  -H 'X-User: bob' -H 'X-Role: member'   # -> "overdue": true, derived at read
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**,
supplied per request with the `X-User` and `X-Role` headers.
The role header must match the registry exactly, or the
request is rejected with 401 (an unknown user is also 401).

| User    | Role   | Permissions |
|---------|--------|-------------|
| `alice` | admin  | read, create_org, enter, decide, record, manage_members, audit_read, admin |
| `bob`   | member | read, create_org, enter, decide, record |
| `carol` | viewer | read |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors
are always JSON `{"error": "..."}` and no stack trace is ever
returned to a client.

## API endpoints

| Method & path | Function |
|---|---|
| `GET /health` | Liveness (unauthenticated) |
| `GET /audit` | Audit entries (`audit_read`, admin only) |
| `GET /search?q=` | Substring search over accessible records |
| `POST /organizations` · `GET /organizations` | Create / list organizations |
| `GET /organizations/{id}` · `POST /organizations/{id}` | Read / relabel an organization |
| `POST /organizations/{id}/members` | Add a member |
| `GET /organizations/{id}/summary` | Counts-only summary |
| `POST /organizations/{id}/systems` · `GET …/systems` | Register / list managed systems |
| `GET /systems/{id}` · `POST /systems/{id}/retire` | Read / retire a system |
| `POST /organizations/{id}/applications` · `GET …/applications` | Register / list applications |
| `GET /applications/{id}` · `POST /applications/{id}/retire` | Read / retire an application |
| `POST /organizations/{id}/requests` · `GET …/requests` | Record / list service requests (`?as_of=`, `?status=`, `?system_id=`) |
| `GET /requests/{id}` | Read a request (`?as_of=` drives the overdue derivation) |
| `POST /requests/{id}/start` · `/resolve` · `/cancel` | Request lifecycle |
| `POST /organizations/{id}/changes` · `GET …/changes` | Record / list changes |
| `GET /changes/{id}` | Read a change |
| `POST /changes/{id}/decide` · `/close` · `/cancel` | Change lifecycle (decide enforces separation of duties) |
| `POST /organizations/{id}/controls` · `GET …/controls` | Record / list control dispositions |
| `GET /controls/{id}` | Read a control record |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**82 tests, OK** at delivery: the founding group's 71-test
core suite carried with the code, plus spec tests pinning this
set (exactly 4 sheets; membership exact against
`remainder.json`; every sheet's tier null / impact "Unknown";
every sheet at zero claims with the per-family counts pinned
at 0; descriptions equal to the census descriptions under the
founding normalization; no tier inferred from a product name).
The category's signature derived-overdue mutation drill was
re-run in this tree — exactly 6 failures under the mutant, the
founding drill's identical set, store restored and SHA-256
verified (see `tests/README.md`).

## Byte-identity accounting

`src/sysadmin/` is carried from the founding group
`../system-administration-l2/src/sysadmin/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `b65138dabca988ef8ed54ac5b0718a739904fef3b764dbc0044e0869a0efca77` |
| `__main__.py` | `7f6027b11643c7d4b893269513565763d707705a9b98217a5d99ddad0a1ea82d` |
| `access.py` | `8272711e42619a77c179e6b247d527ddde14d658a161b920de21f7e9c6557079` |
| `audit.py` | `7de3b7dd5fdda70a173c45578dce48be90dfd3a69e147c5dd996a4516229e557` |
| `errors.py` | `ee029ad6f7bdb2df36b671cdb1df21223a2f780a2fa47dd4d3f20be71900ba91` |
| `service.py` | `8fac6fad2016a1f660c1ee9b185c47a1f3fd9739437106512dc3c178320828c3` |
| `store.py` | `46c4f2dcc182d4ae288b5430c54f05478a81f937eb761d4f63270e7ed2a26719` |

The one carried text that still names the founding tier is
the `__init__.py` docstring's label line ("System
Administration L2 singleton") — it is the founding group's own
label inside byte-identical code, retained so the accounting
above is exact; this group's docs carry the tier-null
anchoring. The test suite is likewise carried (the founding
suite minus its additions module, which pins a different
census unit), with one labeling fix in
`tests/sysadmin_helpers.py` (its docstring now names this
untiered set instead of L2) and the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 4 offerings (all "Unknown"),
so this build asserts **no FedRAMP baseline, no CMMC tier,
and no equivalence**. What follows is only what the forks'
own marketplace descriptions assert, in their own words. A
documented control claim is a **fork's claim about itself**,
recorded with its evidence in `UNION-SPEC.md` and
`specs/specs.json`; it is not the build's control attainment,
and nothing here fills a family in from any baseline.

Documented by at least one fork in this set — all four areas
by a single fork, PDQ (FR2701457585), in a single sentence
("PDQ is SOC 2 certified and includes security features such
as MFA, role-based access controls, encryption, and audit
logging to support compliance requirements"):

- **Identification & authentication (IA)** — PDQ:
  multi-factor authentication among its platform's security
  features.
- **Access control (AC)** — PDQ: "role-based access controls"
  on its platform.
- **Cryptographic protection (SC)** — PDQ: "encryption" among
  its security features. (The build performs no cryptography
  of its own; this is the fork's claim about itself.)
- **Audit (AU)** — PDQ: "audit logging" among its security
  features.

The sentence's "SOC 2 certified" is the fork's own
certification statement about itself, recorded as such.
Freshworks' "built-in security, compliance, and governance
controls" asserts governance in general terms and names no
control; it is recorded in the union spec as general-terms
prose, not traced to a family. Freshworks' incident/change
management and Dynatrace's "application security" are
function prose — services those offerings sell — not control
claims about themselves.

**Not documented** by any fork in this set: every other NIST
SP 800-53 control family — including AT, CA, CM, CP, IR, MA,
MP, PE, PL, PM, PS, RA, SA, and SI **as control claims** — is
asserted by no description in the set. If the source later
publishes an impact level for any of these offerings, the tier
is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP
  baseline, no CMMC tier, and no authorization — for any fork
  or for itself. The forks' recorded authorization statuses
  are source data, not claims by this build, and a fork's
  documented control language is recorded as *its* claim,
  never as the build's control attainment.
- **Zero claims, plainly.** Under the category's taxonomy
  applied verbatim, this set's four forks claim **no**
  function family. The substrate below them is the founding
  group's merged build, carried whole; nothing was back-filled
  or re-tuned to make the set look claimed.
- **The build performs no administration operations.**
  Extended functions are specified, not implemented (see
  `UNION-SPEC.md`): the managed OS & services administration
  operations themselves; system provisioning & deployment;
  the application delivery & hosting runtime; the
  virtualization engine; high-availability network operation;
  the third-party CSP hosting platforms; and the engines this
  set's forks assert in substance — observability & monitoring
  engines, AI root-cause & predictive analytics, IT service
  management systems, IT operations & asset discovery,
  endpoint management operations, vulnerability detection &
  remediation prioritization, and capacity/chargeback
  reporting engines. Recording a service request performs no
  work; closing a change alters no system.
- **The build holds records, never live systems.** Managed
  systems and applications are known only by opaque
  caller-chosen references; their pinned record shapes have
  no field that could hold a hostname, IP address, credential,
  or any live-system identifier.
- **No scores.** Nothing in the build computes a score,
  rating, health, posture, or compliance value; control
  records carry recorded dispositions verbatim, and summaries
  are counts only.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`,
  and `carol` are documented demo identities supplied by
  header; the service enforces the role permission matrix on
  those hooks and ships no identity provider, no credential
  store, and no authentication of its own. IA-2 stays with the
  embedding organization.
- **Named absences stand.** All eight taxonomy families have
  0 claimants in this set; monitoring, incident management,
  and ticketing are asserted in substance by these forks and
  remain claimless because the taxonomy holds no family for
  them. Nothing was back-filled to make the set look complete.
