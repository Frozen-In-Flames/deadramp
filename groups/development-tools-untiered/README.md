# Development Tools — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **7 untiered forks** of Development Tools
— census unit `untiered:Development Tools` in `../../remainder.json`,
the sixth untiered set built under the remainder pipeline. **This
is an untiered set, and that means something specific:** every
member's FedRAMP impact level is **Unknown** in the source dataset.
The source publishes no baseline for these offerings, so **tier
stays null**: no tier is assigned, no CMMC equivalence is drawn,
and this build asserts **no control baseline**. Per PIPELINE.md,
untiered offerings "build to their documented control claims; tier
stays null in the registry until the source publishes a baseline."
The union contract is [`UNION-SPEC.md`](UNION-SPEC.md); per-fork
spec sheets are in [`specs/specs.json`](specs/specs.json), each
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`,
pinned by tests.

The 7 forks were spec'd under the category's existing 17-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Development Tools L2 group's
**original shipped claim tables exactly — 2 of 2 forks, 4 of 4
claims, deep-equal** against the sheets at the original ship commit
(`a72b99a`, before the remainder additions were appended), with the
parent's one recorded wording-artifact correction applied on the
proof path — before tagging this set. Result here: **14 claims**
across the set, **6 of 7 forks claiming at least one**; the one
zero-claim fork (FR2701457600, Elixium) is recorded under Named
absences in the union spec, not hidden or repaired.

The build implements the category's **ten-function substrate** —
the development-lifecycle records machinery every sibling's output
presupposes — carried **byte-identical** from the founding
Development Tools L2 build (`../development-tools-l2/src/devtools/`,
7 of 7 modules; SHA-256 accounting below), and through that group
from Group 17's original L1 implementation: the substrate has now
been carried unchanged across three builds. It is tier-independent
records code: the founding source contains no tier or baseline
machinery, so there was nothing tier-shaped to strip. Where the
founding contract's text ties access control and audit to a tier
baseline, read it here as **baseline-neutral hooks**: at tier null
they are substrate, claimed against no baseline.

**This build records lifecycle decisions; it executes no
toolchains.** It is a records substrate, not a development
platform: projects held in a registry, issues tracked through a
lifecycle gate, code-review outcomes recorded, builds and releases
recorded, artifacts registered by checksum, environments and
deployments recorded, and search over those records. Each vendor's
execution engines on top of that substrate — CI/CD runners, AI code
generation, hosted IDE workspaces, conversion pipelines — are
Extended functions (see Honesty).

## The 7 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2701557054 | Aequitas Cyber Labs | KineticCode | 5 |
| FR2631054484 | Anysphere, Inc. | Cursor | 1 |
| FR2701557044 | Business Integra Technology Solutions, Inc. | Moderniza | 1 |
| FR2631258132 | Harness, Inc. | Harness for Government | 2 |
| FR2701457600 | IndirectTek LLC | Elixium | 0 |
| FR2700555844 | Linear Orbit, Inc. | Linear | 4 |
| FR2701457579 | Replit, Inc. | Replit for Government | 1 |

In `forks.json` the set is mixed as filed: 2 forks carry the
Development Tools category (KineticCode, Moderniza), 2 are filed
under Artificial Intelligence (AI) (Cursor, Replit for
Government), 2 are filed "Uncategorized (none in source)" (Harness
for Government, Elixium), and 1 is filed under Operations
Management (Linear); the census assigned all 7 to this category
from their own descriptions, and the spec sheets record the
assignment. Authorization statuses as recorded span Initial
Implementation (5), FedRAMP In Process (1), and FedRAMP Certified
(1 — Harness for Government, whose record pairs a Certified status
with an Unknown impact level; both strings are recorded as-is) — a
status is record data, not a claim.

**The set's character, recorded honestly:** no two forks claim the
same substantive profile. KineticCode is a CI/CD governance wrapper
whose five claims ride on its governance sentences while its CI/CD
substance tags nothing (the spelled-out family phrases never
occur); Harness, the canonical CI/CD platform, tags the pipeline
family directly; Linear tags issue tracking outright; Cursor and
Replit are AI development platforms whose AI engines match no
family in a taxonomy written before them; Moderniza's only tag is
its audit ledger; Elixium tags nothing. Two of the 14 claims are
recorded at **artifact weight** (both `landing_zones` hits are the
word "multi-tenant") and one at **product-noun weight**
(Harness's `deployment_release` on "delivery platform") — see
`UNION-SPEC.md` and `scratch/ARTIFACTS.md`.

## The 10 core functions

1. **Project registry** — projects as records (`prj-`) with
   description, repository URL, and provenance. *Claim-supported
   in this set: Replit's `project_collaboration`.*
2. **Issue tracking w/ lifecycle** — issue records (`iss-`) with
   kind, priority, and a lifecycle gate: `open → {in_progress,
   closed}`, `in_progress → {resolved, open}`, `resolved →
   {closed, open}`, `closed → {open}`. Any other transition
   (including same-state and unknown status) is rejected and
   leaves the state unchanged. *Claim-supported: Linear's
   `issue_tracking`.*
3. **Code-review records** — review records (`rev-`) with a state
   machine: `open → {approved, changes_requested, closed}`,
   `changes_requested → {open, closed}`, `approved → {merged,
   closed}`; `merged`/`closed` are terminal. Records only — no
   merge engine, no AI review. *Claim-supported: Cursor's and
   KineticCode's `code_review`.*
4. **Build records** — build records (`bld-`) with ref, status
   (`queued` / `running` / `succeeded` / `failed`), and config
   held as a record. Records only — nothing executes.
   *Claim-supported (the records slice): Harness's `ci_pipeline`.*
5. **Release records** — release records (`rel-`) with version,
   notes, and an optional build link; a duplicate version within
   the same project is rejected (the same version in a different
   project is fine). *Claim-supported at product-noun weight:
   Harness's `deployment_release`.*
6. **Artifact registry w/ checksums** — artifact records (`art-`)
   holding a SHA-256 checksum and size, never the content itself;
   `verify_artifact` recomputes the hash of supplied content and
   compares. A registration with mismatched checksum + content, or
   with neither, is rejected. *Carried in this set:
   `artifact_registry` has 0 claimants.*
7. **Environment & deployment records** — environment records
   (`env-`) and deployment records (`dep-`) linking an environment
   and a project to an optional release and artifact, with status
   (`deployed` / `failed` / `rolled_back`). Records only — nothing
   is provisioned or deployed. *Carried in this set: the family's
   2 hits are "multi-tenant" at artifact weight, which is tenancy
   prose, not environment prose.*
8. **Search** — case-insensitive substring search over project
   names, issue/review titles, release versions, and artifact
   names/versions, returning all five families. *Carried: `search`
   has 0 claimants at every tier so far; it is a substrate
   operation over the build's own records.*
9. **RBAC** — `admin` / `developer` / `viewer` roles with a
   permission matrix enforced before any state change.
   *Claim-supported: KineticCode's `access_control`.*
10. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.
    *Claim-supported: KineticCode's and Moderniza's
    `audit_logging`.*

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `prj-`, `iss-`,
`rev-`, `bld-`, `rel-`, `art-`, `env-`, `dep-`. Permission is
checked before any state change or id allocation.

Six of the ten functions carry claim support in this set under the
category's standing dispositions (Core 5 at product-noun weight);
Cores 6, 7, and 8 are carried substrate here, flagged as such in
the union spec. Functions are **carried** as substrate; no function
is claimed to be *attained* by any fork — the build is the merged
open implementation, not any fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m devtools serve --host 127.0.0.1 --port 8797
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from devtools.access import User
from devtools.audit import AuditLog
from devtools.store import DevToolsStore

audit = AuditLog()
store = DevToolsStore(audit=audit)
admin = User("alice", "admin"); dev = User("bob", "developer")
project = store.create_project("Widget Service", admin)
issue = store.create_issue(project["id"], "Crash on start", dev)
store.set_issue_status(issue["id"], "in_progress", dev)
art = store.register_artifact(project["id"], "widget-pkg", dev, content="payload")
print(store.verify_artifact(art["id"], "payload", admin))  # True
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role      | Permissions |
|---------|-----------|-------------|
| `alice` | admin     | all actions, including `audit_read` |
| `bob`   | developer | all reads + all writes + `search`; **not** `audit_read` |
| `carol` | viewer    | all reads + `search` only; no writes, no `audit_read` |

Read actions: `project_read`, `issue_read`, `review_read`,
`build_read`, `release_read`, `artifact_read`, `deployment_read`.
Write actions: `project_write`, `issue_write`, `review_write`,
`build_write`, `release_write`, `artifact_write`,
`deployment_write`. Plus `search` (all roles) and `audit_read`
(admin only). Unknown roles hold no permissions.

Plain-string actors: store functions accept `User` objects; a plain
string carries identity but no role, so the service layer — which
knows the registry and always passes `User` objects — is responsible
for enforcement in that case.

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/projects` | project_read | `{"projects": [...]}` |
| POST | `/projects` | project_write | Body `{"name", "description"?, "repo_url"?}` → 201 project |
| GET | `/projects/{id}` | project_read | One project |
| GET | `/issues?project_id=&status=` | issue_read | `{"issues": [...]}` |
| POST | `/issues` | issue_write | Body `{"project_id", "title", "description"?, "kind"?, "priority"?}` → 201 issue |
| GET | `/issues/{id}` | issue_read | One issue |
| POST | `/issues/{id}/status` | issue_write | Body `{"status"}` → issue (lifecycle-gated) |
| GET | `/reviews?project_id=` | review_read | `{"reviews": [...]}` |
| POST | `/reviews` | review_write | Body `{"project_id", "title", "source_ref"?}` → 201 review |
| GET | `/reviews/{id}` | review_read | One review record |
| POST | `/reviews/{id}/state` | review_write | Body `{"state"}` → review (transition-gated) |
| GET | `/builds?project_id=` | build_read | `{"builds": [...]}` |
| POST | `/builds` | build_write | Body `{"project_id", "ref"?, "status"?, "config"?}` → 201 build record |
| GET | `/builds/{id}` | build_read | One build record |
| GET | `/releases?project_id=` | release_read | `{"releases": [...]}` |
| POST | `/releases` | release_write | Body `{"project_id", "version", "notes"?, "build_id"?}` → 201 release |
| GET | `/releases/{id}` | release_read | One release record |
| GET | `/artifacts?project_id=` | artifact_read | `{"artifacts": [...]}` |
| POST | `/artifacts` | artifact_write | Body `{"project_id", "name", "version"?, "checksum"?, "content"?}` → 201 artifact record |
| GET | `/artifacts/{id}` | artifact_read | One artifact record |
| POST | `/artifacts/{id}/verify` | artifact_read | Body `{"content"}` → `{"match": bool}` |
| GET | `/environments` | deployment_read | `{"environments": [...]}` |
| POST | `/environments` | deployment_write | Body `{"name", "tier"?}` → 201 environment |
| GET | `/deployments?environment_id=&project_id=` | deployment_read | `{"deployments": [...]}` |
| POST | `/deployments` | deployment_write | Body `{"environment_id", "project_id", "release_id"?, "artifact_id"?, "status"?}` → 201 deployment record |
| GET | `/search?q=` | search | `{"projects": [...], "issues": [...], "reviews": [...], "releases": [...], "artifacts": [...]}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

(The `/environments` POST body's `tier` field is the founding
record schema's environment label — a free-text record field, not
this set's tier, which is null.)

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**74 tests, OK** at delivery: the founding group's 66-test core
suite carried with the code (byte-identical; its additions module,
which pins a different census unit, is not carried), plus 8 spec
tests pinning this set (exactly 7 sheets; membership exact against
`remainder.json`; every sheet's tier null / impact "Unknown"; every
claim's evidence verbatim in its description; 14 claims total with
the exact per-fork claim table and exactly one zero-claim fork; no
claim's evidence resting on scope-exclusion prose). The category's
signature lifecycle-gate mutation drill was re-run in this tree —
exactly 8 failures under the mutant, the founding drill's identical
failing set, store restored and SHA-256 verified (see
`tests/README.md`). A live smoke drives the store and the HTTP
service end to end (see `tests/README.md`).

## Byte-identity accounting

`src/devtools/` is carried from the founding group
`../development-tools-l2/src/devtools/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees, and through the
founding group identical to Group 17's originals):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `b55a40a77630d2e1019fc51586e3ade5fc7a79b0d0ed740e58190c2403e3ff3c` |
| `__main__.py` | `9cf786b62f0ab5dda96b967b3e733167b8805ac7e12859a4e0970d1fffc2a092` |
| `access.py` | `9880ba510e8e07b52d10851ea320a71b19f4cb9efbd28e5d55bab2a1cb185aaf` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `b33b6959002a76cc15258f7c3760d4510e14addd05601ce8b949f7c1912f2947` |
| `service.py` | `7404a8edf1ed22ffea5fe363a7f2678cd0410436e6b7f113b0d5584a062b8021` |
| `store.py` | `36b04bd5b46d5c550800575ec7dc7239654fa469338a8e1652ff611ad41925e0` |

The test suite is likewise carried (the founding suite minus its
additions module, which pins a different census unit), byte-identical
to the founding group's files, with the new `tests/test_specs.py`
added. Full accounting is in `tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 7 offerings (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words. A documented control claim
is a **fork's claim about itself**, recorded with its evidence in
`UNION-SPEC.md` and `specs/specs.json`; it is not the build's
control attainment, and nothing here fills a family in from any
baseline.

Documented by at least one fork in the set, via a taxonomy family:

- **Access control (AC)** — 1 fork, via `access_control`:
  KineticCode ("business-unit and role-based views, with detection
  and flagging of access-policy violations for human remediation").
- **Audit & accountability (AU)** — 2 forks, via `audit_logging`:
  KineticCode ("persistent audit trail of scans, approvals, merges
  and promotions," stated outright; its first-hit evidence rests on
  "auditable controls") and Moderniza ("Every step leaves a ledger
  the customer can audit").

Documented at **prose weight** (asserted in a fork's own sentences,
captured by no family phrase, recorded as prose, not claims):

- **Configuration management / change control (CM)** — KineticCode:
  build checksums re-verified at each environment promotion; strict
  sequential Dev, Test, Stage, Prod promotion.
- **System & information integrity (SI)** — KineticCode:
  detection of secrets, tokens and credentials in checked-in code,
  risky code patterns, CUI/FCI marking assistance; Harness:
  "security testing" in its capability list.
- **Assessment & authorization (CA)** — Cursor: an independent
  assessment by A-LIGN named, FedRAMP 20x Class A under review and
  Class C pursued, with the fork's own words "Certification has not
  yet been granted" — an assessment underway for the fork itself,
  not an authorization.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, CP, IR, MA, MP, PE, PL, PM,
PS, RA, SA, and SC — is asserted by no description in the set.
Identification & authentication (IA) is pointedly among them: no
description carries an SSO / identity-provider / authentication
phrase. If the source later publishes an impact level for any of
these offerings, the tier is recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **Records only — no toolchains are executed.** This build runs
  no CI/CD pipeline, compiles nothing, hosts no git internals,
  merges nothing, deploys nothing, and evaluates no feature flag.
  A build record does not run a build, a review record does not
  review code, and a deployment record does not deploy anything.
- **No AI anywhere in this build.** Four of the seven forks are AI
  products (Cursor, Replit, Elixium's agents, Linear's agent
  workflows). The substrate contains no model, no inference, and
  no agent runtime; the forks' AI engines are Extended gaps, named
  in the union spec.
- **Extended functions are specified, not implemented.** The union
  spec ranks 17 functions; the substrate behind 10 is implemented
  here. NOT implemented (claimant counts are this set's): CI/CD
  execution engines (1); code hosting internals (0 — and Cursor's
  git hosting product is expressly outside its own offering's
  scope); compilers & build toolchains (0); configuration-as-code
  execution & orchestration (0); compliance assessment & KSI
  automation engines (0); business modeling & automation engines
  (0); course & content authoring tools (0); landing-zone / tenant
  provisioning & hosted platform operations (2 forks document
  multi-tenant platforms about themselves); artifact binary
  storage backends (0); feature-flag runtime and experimentation
  engine (0 in this set, carried from the category union);
  static code analysis engine (0 in this set, carried); security
  posture monitoring & remediation engine (0 in this set,
  carried); release automation & data migration engine (0 at
  substance weight); external-system integration engines (1); AI
  code-generation & AI-agent development engines (new in this
  set); cloud development environments / hosted IDE workspaces
  (new); legacy modernization & code-conversion engines (new);
  CI/CD governance & promotion-gating engines (new); secrets &
  sensitive-data detection engines (new); pipeline governance
  configuration records (new — the category's standing
  records-configuration gap); fork excess — customer support
  platform (new, Elixium).
- **Artifact registry holds checksums, not binaries.** An artifact
  record carries a SHA-256 checksum and a size. The content
  supplied at registration is hashed and discarded; it is never
  stored, and there is no binary storage backend in this build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own.
- **Named absences stand.** Configuration as code, artifact
  registry, compliance/KSI, visual modeling, business automation,
  content authoring, and search all have 0 claimants in this set;
  Elixium has 0 claims. Nothing was back-filled to make the set
  look complete, and the taxonomy was not re-tuned for any fork.
