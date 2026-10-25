# Development Tools L2 — merged build (Operation DeadRamp, Phase 2, Group 29)

This is the merged, clean-room implementation of the **Development
Tools L2** sibling group: **2 forks / vendor platforms** from the
FedRAMP Marketplace that share the same function (Development Tools)
and the same trust tier (L2 = FedRAMP Moderate), built as one
open-source service.

The 2 forks: **AutoRABIT for Public Sector - CodeScan, Guard, &
ARMOR** (AutoRABIT Holding, Inc.) · **LaunchDarkly** (LaunchDarkly).
**Both are FedRAMP Moderate and FedRAMP Certified.**

It was written from the group contract only: original code, no
vendor code, assets, or branding from any sibling offering. Python
3, **standard library only**, no external dependencies (verified
programmatically: every import in `src/` is in
`sys.stdlib_module_names`; see `scratch/verify_deps.py`).

**Reuse, stated explicitly:** the implementation is Group 17's
(Development Tools L1) code — our own Apache-2.0 code — reused in
full. All 7 modules under `src/devtools/` are **byte-identical** to
`../development-tools-l1/src/devtools/` (SHA-256 per module in
`UNION-SPEC.md`'s implementation contract), and the test suite is
Group 17's copied byte-identical. The substrate is tier-neutral;
only the baseline claim is new (Moderate, written fresh in
`UNION-SPEC.md`). The mutation-verification drill was performed
fresh in this tree.

## What the group is: a records substrate

This group is a **records substrate**, not a development platform:
projects held in a registry, issues tracked through a lifecycle,
code-review outcomes recorded, builds and releases recorded,
artifacts registered by checksum, environments and deployments
recorded, and search over those records. Each vendor's execution
engines on top of that substrate are Extended functions (see
Honesty).

Honest note on the category: both forks **are** genuine development
platforms — the contrast with L1, where only two of five were — but
of specialized kinds. AutoRABIT is a Salesforce DevSecOps suite
(static code analysis, security monitoring/remediation, release
management); LaunchDarkly is a feature-management platform (feature
flags, targeting, rollouts, experimentation). Under Group 17's
taxonomy applied **verbatim**, their descriptions tag **4 claims
total** (AutoRABIT: integrations, audit; LaunchDarkly: CI pipeline,
access control — the two forks share no claimed family), and both
products' dominant functions sit **outside** the taxonomy's families
entirely, recorded as near-misses and Extended gaps in
`UNION-SPEC.md` / `scratch/ARTIFACTS.md` rather than forced into
families their prose does not phrase. This build implements the
development-records substrate both products' record forms
presuppose; their engines are named in the Extended gap list, not
pretended into the Core. Of the 10 Core functions, 3 carry claim
support in this group (build records as the CI slice, RBAC, audit)
and 7 are carried substrate, flagged as such in the union spec.

## The 10 core functions

1. **Project registry** — projects as records (`prj-`) with
   description, repository URL, and provenance.
2. **Issue tracking w/ lifecycle** — issue records (`iss-`) with
   kind, priority, and a lifecycle: `open → {in_progress, closed}`,
   `in_progress → {resolved, open}`, `resolved → {closed, open}`,
   `closed → {open}`. Any other transition (including same-state and
   unknown status) is rejected and leaves the state unchanged.
3. **Code-review records** — review records (`rev-`) with a state
   machine: `open → {approved, changes_requested, closed}`,
   `changes_requested → {open, closed}`, `approved → {merged,
   closed}`; `merged`/`closed` are terminal. Records only — no merge
   engine.
4. **Build records** — build records (`bld-`) with ref, status
   (`queued` / `running` / `succeeded` / `failed`), and config held
   as a record. Records only — nothing executes.
5. **Release records** — release records (`rel-`) with version,
   notes, and an optional build link; a duplicate version within the
   same project is rejected (the same version in a different project
   is fine).
6. **Artifact registry w/ checksums** — artifact records (`art-`)
   holding a SHA-256 checksum and size, never the content itself;
   `verify_artifact` recomputes the hash of supplied content and
   compares. A registration with mismatched checksum + content, or
   with neither, is rejected.
7. **Environment & deployment records** — environment records
   (`env-`) and deployment records (`dep-`) linking an environment
   and a project to an optional release and artifact, with status
   (`deployed` / `failed` / `rolled_back`). Records only.
8. **Search** — case-insensitive substring search over project
   names, issue/review titles, release versions, and artifact
   names/versions, returning all five families.
9. **RBAC** — `admin` / `developer` / `viewer` roles with a
   permission matrix enforced before any state change.
10. **Append-only audit log** — every mutation and every denied
    attempt recorded with actor, action, target, and UTC timestamp.
    Optional JSONL file persistence. There is no mutation or
    deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `prj-`, `iss-`, `rev-`, `bld-`,
`rel-`, `art-`, `env-`, `dep-`. Permission is checked before any
state change or id allocation.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m devtools serve --host 127.0.0.1 --port 8793
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

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
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

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

## How to run tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

66 tests, all passing at delivery. See `tests/README.md` for the
coverage table, the negative control, and the mutation-verification
drill record (performed fresh in this tree: lifecycle-gate mutant →
8 failures; store restored SHA-256-verified; suite green). A live
smoke (`scratch/smoke.py`) drives the store and the HTTP service end
to end: project → issue → lifecycle to `resolved` → review → build
record → release → artifact with checksum verify → environment →
deployment → search hit; a viewer write attempt returns 403 over
HTTP and the denied attempt is present in the audit log.

## Control-family mapping (summary)

Against the **NIST SP 800-53 Rev. 5 Moderate baseline** (the
FedRAMP Moderate tailoring), cross-walked to the **110 requirements
of NIST SP 800-171** that define CMMC L2, **at the Moderate
baseline** (written fresh for this tier in `UNION-SPEC.md`):

| Core function | Control families | How the build answers |
|---|---|---|
| Project registry, issue/review/build/release/artifact/environment/deployment records | AC / IA hooks, AU, CM, SI-10 | Records are explicit and configuration-controlled; identity is supplied by the embedding organization via user/role headers (AC-2, AC-3; IA-2 hooks — this service ships hooks, not an IdP) |
| RBAC (admin/developer/viewer) | AC-2, AC-3, AC-6, IA-2 (hooks) | Role matrix enforced pre-mutation, before any id allocation; role header must match the registry exactly or 401. On the 800-171 side: 3.1 (access control), 3.5 (identification & authentication). Claim-supported in this group (LaunchDarkly's feature-level RBAC) |
| Audit log | AU-2, AU-3, AU-6 | Append-only log including denied attempts; no mutation API; audit-read restricted to `audit_read` (admin only). **Both sides at this tier:** unlike L1 (FAR 52.204-21 carries no audit practice), 800-171 carries an audit family (3.3), so the mapping holds on the CMMC side too. Claim-supported in this group (AutoRABIT's "immutable audit trails") |
| Records integrity | SI-7, SI-10, CM-2/CM-3 (family level) | Malformed input rejected, never partially applied, no id consumed; lifecycle/state gates and checksum agreement validated before any record changes; SHA-256 verify-by-content is an integrity check (SI-7 is a Moderate selection, citable here); release versions unique per project and build configuration held as record (800-171 3.4) |
| Transport | SC-8 | The server runs over TLS when a certificate is configured (`--certfile`/`--keyfile`); the default serve mode is plain HTTP for local/demo use (800-171 3.13) |

## Honesty: what is Core, what is Extended, what is NOT in this build

**Records only.** This build is a records substrate: **no CI
execution, no git hosting internals, no compilers, no merge
engine — and, new at this tier, no feature-flag evaluation, no
static code analysis, no security monitoring or remediation, and no
release automation**. A build record does not run a build, a review
record does not merge anything, a deployment record does not deploy
anything, and no feature flag is evaluated anywhere in this build.

**Artifact registry holds checksums, not binaries.** An artifact
record carries a SHA-256 checksum and a size. The content supplied
at registration is hashed and discarded; it is never stored, and
there is no binary storage backend in this build.

**Extended gap list, by name, exactly as registered** — the
following are **NOT implemented** here:

Carried from the Group 17 union:

1. CI/CD execution engines
2. Code hosting internals (git storage, branching & merging engines)
3. Compilers & build toolchains
4. Configuration-as-code execution & orchestration
5. Compliance assessment & KSI status automation engines
6. Business modeling & automation engines
7. Course & content authoring tools
8. Landing-zone / tenant provisioning & hosted platform operations
9. Artifact binary storage backends

New in this group:

10. Feature-flag & feature-management runtime
11. Experimentation engine
12. Static code analysis engine
13. Security posture monitoring & automated remediation engine
14. Release automation, environment management & data migration engine
15. External-system integration engines

**Platform-layer notes.** Encryption at rest is a deployment-layer
control, not claimed here. TLS applies only when configured
(`--certfile`/`--keyfile`); the default serve mode is plain HTTP
for local/demo use. The merged build is a **single-tenant
reference deployment**; multi-tenancy is a deployment property, not
a development-tools function. The demo identities (`alice`, `bob`,
`carol`) are **hooks, not an IdP**: IA-2 (identification &
authentication) stays with the embedding organization, which
supplies production identity, authentication strength, and account
lifecycle.

**Tier caveat.** This build is **not a FedRAMP authorization and
confers no CMMC certification**, and it claims neither. The L2 /
FedRAMP Moderate equivalence used here is a planning/matching
equivalence only; FedRAMP authorizes products and CMMC certifies
organizations.
