# Development Tools L3-adjacent — singleton build (Operation DeadRamp, Phase 2 remainder)

This is the clean-room implementation of the **Development Tools
L3-adjacent singleton**: **1 fork** from the FedRAMP Marketplace at
the High tier — **Red Hat OpenShift Service on AWS (ROSA)**
(Red Hat), FedRAMP Certified — built under the Merge Rule as the
cross-tier merge of that fork with the shipped Development Tools
L2 build: the L2 category substrate carried up whole and uplifted
to the FedRAMP High baseline.

Two honesty notes up front. First, **the singleton tags exactly 1
claim** under the category's verbatim taxonomy: `hosted_platform`,
on the description's own "Platform-as-a-Service (PaaS)" sentence —
and in this category that family is a *platform note* (it describes
the fork's delivery model), not a core function. **No core
function is claim-supported by this fork**; the 10 core functions
below are **carried, not claimed**, for this tier — they stand
because the Merge Rule carries the L2 union upward whole and
thinner prose at the higher tier is not a downgrade (the
core-boundary decision in `UNION-SPEC.md`). The census citation
for this fork verifies verbatim and tags no family at all;
verification and claiming are different events, and both facts are
pinned in the spec tests. Second, **ROSA's own platform is not in
this build**: the Kubernetes container orchestration, the
integrated development environment, the build-pipeline execution,
and the 24/7 managed operations that make ROSA ROSA are Extended
gaps, named in `UNION-SPEC.md` for the final batch. This build is
the records substrate at the High baseline — not a claim that a
managed container platform and a records service are the same
product. The fork's platform properties (its FedRAMP High
baseline posture, its AWS GovCloud hosting, its joint Red Hat/AWS
management) are properties of the fork's deployment and **do not
transfer** to this build.

It was written from the union contract only: original code, no
vendor code, assets, or branding. Python 3, **standard library
only**, no external dependencies. Where functions overlap it
reuses the L2 group's own Apache-2.0 code: `__init__.py` is
byte-identical; the other six modules are the L2 group's, modified
only for the High uplifts marked **[L3]** below.

## The 10 core functions (carried from the L2 build, at High)

1. **Project & repository records** — projects (`prj-`) with a
   name, optional description and repository URL, and
   created-by/at provenance. Records only — no code is hosted,
   cloned, or served.
2. **Issue tracking** — issues (`iss-`) under a project with kind,
   priority, and a guarded lifecycle
   `open → in_progress → resolved → closed` (reopen paths
   included). Illegal transitions are rejected with the state
   unchanged; the lifecycle gate is this group's signature guard
   and is mutation-drilled (tests/README.md).
3. **Code-review records** — reviews (`rev-`) with a state machine
   `open → approved / changes_requested → merged / closed`.
   Records only — there is no merge engine.
4. **Build records** — builds (`bld-`) with a ref, a status
   (queued / running / succeeded / failed), and a free-form config
   stored verbatim. Records only — **no build ever runs**;
   configuration text is never executed.
5. **Release records** — releases (`rel-`) with a version unique
   per project, notes, and an optional link to a build record.
6. **Artifact registry** — artifacts (`art-`) registered with a
   SHA-256 checksum computed from supplied content or supplied
   directly (the two must agree). Content itself is never stored;
   `verify_artifact` checks candidate content against the stored
   checksum and answers False on tampered content.
7. **Environment & deployment records** — environments (`env-`)
   and deployments (`dep-`) linking an environment and a project,
   with optional release/artifact references that must exist, and
   a status (deployed / failed / rolled_back).
8. **Search** — literal, case-insensitive substring search (not
   regex) over project names, issue titles, review titles,
   release versions, and artifact names.
9. **REST API** — every function above over a JSON REST API.
   **[L3]** Unsuccessful logons lock the username out (AC-7,
   below).
10. **RBAC + audit log** — platform roles `admin`, `developer`,
    `viewer`, **[L3]** plus `auditor`, with a permission matrix
    enforced on every operation; every mutation and every denied
    attempt is recorded with actor, action, target, and UTC
    timestamp. **[L3]** The audit log is **hash-chained and
    tamper-evident** with chain verification, **fail-closed** on
    write failure, and **queryable** (AU-9/AU-5/AU-7). Optional
    JSONL file persistence. There is no mutation or deletion API
    for audit entries.

Malformed input is rejected with a validation error and leaves
the store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `prj-`, `iss-`,
`rev-`, `bld-`, `rel-`, `art-`, `env-`, `dep-`. Permission is
checked before any state change or id allocation. **[L3]** An
operation whose audit write fails is rolled back in full —
records and id counters — and the error propagates (AU-5).

## How to run

From this directory:

```sh
PYTHONPATH=src python -m devtools serve --host 127.0.0.1 --port 8792
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`), **[L3]** `--max-failed-logins N` (default 3) and
`--lockout-seconds S` (default 300) for the AC-7 lockout. A
startup line is printed once the server is listening.

As a library:

```python
import sys; sys.path.insert(0, "src")
from devtools.access import User
from devtools.audit import AuditLog
from devtools.store import DevToolsStore

audit = AuditLog()
store = DevToolsStore(audit=audit)
admin, bob = User("alice", "admin"), User("bob", "developer")
project = store.create_project("Widget Service", admin, description="demo")
issue = store.create_issue(project["id"], "Crash on empty config", bob)
store.set_issue_status(issue["id"], "in_progress", bob)
build = store.record_build(project["id"], bob, ref="main", status="succeeded")
release = store.create_release(project["id"], "1.0.0", admin, build_id=build["id"])
artifact = store.register_artifact(project["id"], "widget.tar", admin,
                                   version="1.0.0", content=b"payload")
print(store.verify_artifact(artifact["id"], b"payload"))    # True
print(store.verify_artifact(artifact["id"], b"tampered"))   # False
print(audit.verify_chain())  # (True, None) — the trail is hash-chained [L3]
```

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is
rejected with 401 (an unknown user is also 401). **[L3]** After
`--max-failed-logins` consecutive failures a username locks for
`--lockout-seconds`; attempts during the lock get 403 and are
audited as `auth:locked`.

| User    | Role      | Permissions |
|---------|-----------|-------------|
| `alice` | admin     | all 16 actions |
| `bob`   | developer | all reads and writes plus `search` (15 actions; NOT `audit_read`) |
| `carol` | viewer    | the 8 read actions except `audit_read`, plus `search` (8 actions) |
| `dana`  | auditor   | **[L3]** `audit_read` only (AC-5: audit review separated from administration; no operational read or write) |

Read actions: `project_read`, `issue_read`, `review_read`,
`build_read`, `release_read`, `artifact_read`, `deployment_read`,
`audit_read`. Write actions: `project_write`, `issue_write`,
`review_write`, `build_write`, `release_write`, `artifact_write`,
`deployment_write`. Plus `search`. Unknown roles hold no
permissions.

Plain-string actors: store functions accept `User` objects; a
plain string carries identity but no role, so the service layer —
which knows the registry and always passes `User` objects — is
responsible for enforcement in that case (the shipped groups'
convention).

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever
returned to a client. **[L3]** If an audit write fails, a mutation
request returns 500 `{"error": "audit write failed"}` exactly,
and the operation is rolled back — it is never reported as a
success.

## API endpoints

The L2 surface, plus the two **[L3]** audit endpoints:

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/projects` | project_read | `{"projects": [...]}` |
| POST | `/projects` | project_write | Body `{"name", "description"?, "repo_url"?}` → 201 project |
| GET | `/projects/{id}` | project_read | One project |
| GET | `/issues` | issue_read | `{"issues": [...]}` — accepts `?project_id=`, `?status=` |
| POST | `/issues` | issue_write | Body `{"project_id", "title", "description"?, "kind"?, "priority"?}` → 201 issue |
| GET | `/issues/{id}` | issue_read | One issue |
| POST | `/issues/{id}/status` | issue_write | Body `{"status"}` → issue (lifecycle-guarded) |
| GET | `/reviews` | review_read | `{"reviews": [...]}` — accepts `?project_id=` |
| POST | `/reviews` | review_write | Body `{"project_id", "title", "source_ref"?}` → 201 review |
| GET | `/reviews/{id}` | review_read | One review |
| POST | `/reviews/{id}/state` | review_write | Body `{"state"}` → review (state-guarded) |
| GET | `/builds` | build_read | `{"builds": [...]}` — accepts `?project_id=` |
| POST | `/builds` | build_write | Body `{"project_id", "ref"?, "status"?, "config"?}` → 201 build record |
| GET | `/builds/{id}` | build_read | One build record |
| GET | `/releases` | release_read | `{"releases": [...]}` — accepts `?project_id=` |
| POST | `/releases` | release_write | Body `{"project_id", "version", "notes"?, "build_id"?}` → 201 release |
| GET | `/releases/{id}` | release_read | One release |
| GET | `/artifacts` | artifact_read | `{"artifacts": [...]}` — accepts `?project_id=` |
| POST | `/artifacts` | artifact_write | Body `{"project_id", "name", "version"?, "checksum"?, "content"?}` → 201 artifact (content hashed, never stored) |
| GET | `/artifacts/{id}` | artifact_read | One artifact |
| POST | `/artifacts/{id}/verify` | artifact_read | Body `{"content"}` → `{"match": bool}` |
| GET | `/environments` | deployment_read | `{"environments": [...]}` |
| POST | `/environments` | deployment_write | Body `{"name", "tier"?}` → 201 environment |
| GET | `/deployments` | deployment_read | `{"deployments": [...]}` — accepts `?environment_id=`, `?project_id=` |
| POST | `/deployments` | deployment_write | Body `{"environment_id", "project_id", "release_id"?, "artifact_id"?, "status"?}` → 201 deployment |
| GET | `/search?q=...` | search | `{projects, issues, reviews, releases, artifacts}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` — **[L3]** accepts `?actor=`, `?action=`, `?target=`, `?since=`, `?until=` filters (AU-7) |
| GET | `/audit/verify` | audit_read | **[L3]** `{"ok", "entries", "first_bad_index"}` — hash-chain verification (AU-9) |

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

122 tests. See `tests/README.md` for the coverage table, the
three negative controls, and the two mutation-verification drill
records.

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **High** baseline (the FedRAMP
High baseline for this tier), with the L2 mapping carried up and
the **[L3]** uplifts added:

- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement — the RBAC matrix, enforced in the store
  and again at the API), **AC-5 [L3]** (separation of duties —
  the `auditor` role holds `audit_read` and nothing else), AC-6
  (least privilege — reads for all operational roles, writes for
  developer and admin, audit read for admin and auditor alone),
  **AC-7 [L3]** (unsuccessful logon lockout in the service
  layer); IA-2 (identification & authentication — identity is
  supplied by the embedding organization via user/role headers;
  this service ships hooks, not an IdP; MFA-grade authentication
  at High is the IdP layer's, gap-listed in `UNION-SPEC.md`).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of
  audit records, incl. the **[L3]** chain fields), **AU-5 [L3]**
  (audit failure response — fail-closed writes with full
  rollback), AU-6 (audit review — `audit_read` restricted to
  admin and auditor), **AU-7 [L3]** (audit reduction — filtered
  query), **AU-9 [L3]** (protection of audit information —
  append-only, hash-chained, tamper-evident store with
  `verify_chain()`; no mutation API). AU-11 (retention) is
  gap-listed, not claimed.
- **SI / SA / SC** — SI-10 (information input validation —
  malformed input is rejected, never partially applied, and
  consumes no ids); SI-12 / SC-12 (partial — artifact checksums
  with verify-by-content; content itself is never retained);
  SA / system acquisition honesty in this README; SC-8
  (transmission confidentiality — TLS when a certificate is
  configured; encryption at rest is a deployment-layer control,
  stated plainly and not claimed here); SC-13 (FIPS-validated
  cryptography) is gap-listed — Python's standard library is not
  a validated module and this build does not claim it is.

## Honesty: what is NOT in this build

- **One claim at this tier, and it is a platform note.** The
  singleton's description tags `hosted_platform` and nothing
  else; the core is the L2 category substrate carried up under
  the Merge Rule and flagged carried, not claimed, throughout
  `UNION-SPEC.md`. The fork's census citation verifies verbatim
  and tags no family — cited text is not automatically claimed
  text.
- **ROSA's platform is NOT implemented.** No container
  orchestration (Kubernetes), no integrated development
  environment or developer workspace, no build-pipeline
  execution, no platform monitoring/logging or networking, and
  no 24/7 managed operations. Those are the singleton's Extended
  gaps, named in `UNION-SPEC.md`.
- **Extended capabilities from the L2 union are NOT
  implemented.** No CI/CD execution engines, no code hosting
  internals, no compilers or toolchains, no config-as-code
  execution, no compliance/KSI automation, no feature-flag or
  experimentation runtime, no static analysis, no integration
  connector engines. Build records are *records*: stored
  configuration text is never executed, by design.
- **Records, not engines — throughout.** Reviews are records
  with a state machine, not a merge tool; deployments are
  records of deployments, not a deployment pipeline; the
  artifact registry stores checksums, not binaries.
- **No personal-identifier field classes exist — by design.**
  Record shapes carry project/work-item metadata and
  caller-supplied free text; there is no field for an email,
  phone number, SSN, date of birth, or address in any entity.
- **No scores exist — by design.** Nothing in the build
  computes, stores, or ranks by a score.
- This build is **single-tenant**: one store, one audit log, no
  tenant isolation.
- The demo identities (`alice`, `bob`, `carol`, `dana`) are
  **hooks, not an identity provider**. Production identity,
  authentication strength (including MFA at this tier), and
  account lifecycle belong to the embedding organization.
- **Encryption at rest is a deployment-layer control**, not
  claimed here. **FIPS-validated cryptography is not claimed**
  (stdlib only) — and the fork's own compliance posture does not
  transfer to this build. **TLS is available only when a
  certificate is configured**; the default serve mode is plain
  HTTP for local/demo use.
- This build is **not a FedRAMP authorization**, and it does not
  claim one. The control mapping above states which baseline
  families the build's features answer to; nothing more. FedRAMP
  authorizes products; CMMC certifies organizations — neither
  regime accepts the other as evidence.
