# System Administration — L2 singleton (DeadRamp Phase 2, Group 54)

A clean-room, open-source records substrate for the **System
Administration** category's single FedRAMP fork at the Moderate
tier: **AgCloud Managed Platform Services (AMPS)**, U.S.
Department of Agriculture (FedRAMP ID FR2415334644, PaaS,
Government Community Cloud, FedRAMP Certified).

The fork is a General Support System of operating systems and
services, run on third-party cloud hosting, whose operator
maintains the full management of the OS and services for
contracting customer organizations. This build is the records
substrate those claims presuppose — customer organizations,
managed systems, applications, service requests, changes, and
control inheritance records. **It administers no live system,
patches nothing, provisions nothing, and performs no management
work.** The full reasoning lives in
[`UNION-SPEC.md`](UNION-SPEC.md); the per-fork spec sheet is
[`specs/specs.json`](specs/specs.json).

## Core functions (12)

1. Customer organizations & membership (the records form of the
   fork's contract-gated access)
2. Managed system registry — pinned nine-key records, opaque
   references only (no hostname, address, or credential field
   exists)
3. Application registry — applications hosted on managed systems
4. Service request records — lifecycle `open → in_progress →
   resolved / cancelled`
5. Derived request status — `overdue` derived at read from the
   due date, never stored
6. Change records — approval lifecycle with separation of
   duties (the decider is never the requester); closing a
   change alters no system or application record
7. Control inheritance records — each control's recorded source
   (`inherited` / `local` / `shared`) per system, carried
   verbatim; no posture is derived
8. Registry search — literal substring search over accessible
   records
9. Registry summary — counts only, never scores
10. REST API (JSON) for every function above
11. Role-based access control (`admin` / `member` / `viewer`)
    layered with organization membership
12. Append-only audit log, including denied attempts

## Run

Python 3, standard library only.

```bash
cd groups/system-administration-l2
PYTHONPATH=src python3 -m sysadmin serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile` / `--keyfile` (serve over TLS).

Demo users (demo identities, not an identity provider —
production identity belongs to the embedding organization):

| User | Role |
|---|---|
| `alice` | admin |
| `bob` | member |
| `carol` | viewer |

Authenticate with `X-User` / `X-Role` headers matching the
registry. Example flow:

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

## Endpoints

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
| `POST /changes/{id}/decide` · `/close` · `/cancel` | Change lifecycle (decide enforces AC-5) |
| `POST /organizations/{id}/controls` · `GET …/controls` | Record / list control dispositions |
| `GET /controls/{id}` | Read a control record |

Errors are JSON `{"error": …}` with 400 (validation), 401
(authentication), 403 (permission), or 404 (not found).

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests   # 71 tests
```

See [`tests/README.md`](tests/README.md) for the coverage map
and the mutation-verified negative control (the derived-overdue
drill: patching the derivation to always report not overdue
fails exactly 6 named tests; the store was restored
SHA-256-verified).

## Honesty section

- **Claims.** 8 function claims, one per taxonomy family, each
  with its source sentence from the fork's own marketplace
  description stored as evidence in `specs/specs.json`. The
  taxonomy was defined from that description (new category,
  Group 1 method); counts are a floor. One of the description's
  nine sentences tags nothing (offering positioning).
- **What is not built.** The managed-services work itself —
  administering, patching, provisioning, and tending operating
  systems and services — plus the application delivery/hosting
  runtime, the virtualization engine, high-availability network
  operation, and the third-party CSP hosting platforms are
  **gaps**, named in `UNION-SPEC.md` and registered in the repo's
  `GAPS.md` for the final batch. Nothing in this build performs
  or claims any of them.
- **Tier honesty.** The fork's prose says its operator's
  controls are maintained "at the High baseline level"; the
  offering's own FedRAMP impact level is Moderate and the
  registry tiers it L2. This build builds to Moderate/L2 and
  makes no High-baseline claim.
- **No scores.** Nothing in the build computes a score, rating,
  health, posture, or compliance value; control records carry
  recorded dispositions verbatim, and summaries are counts only.
  A recursive key scan over every view enforces this in tests.
- **Privacy.** Managed systems and applications are known only
  by opaque caller-chosen references; their pinned record
  shapes have no field that could hold a hostname, IP address,
  credential, or any live-system identifier.
- **Compliance.** The baseline mapping in `UNION-SPEC.md`
  states which NIST SP 800-53 families the features answer to
  at the Moderate baseline (CMMC L2 per the repo crosswalk). It
  is not a FedRAMP authorization and not a CMMC certification,
  and it claims neither: FedRAMP authorizes products, CMMC
  certifies organizations; the tier is a planning and matching
  equivalence.
- **Identity.** Demo users are hooks. The build ships no
  identity provider; IA-2 stays with the embedding
  organization.
