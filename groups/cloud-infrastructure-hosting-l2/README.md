# Cloud Infrastructure & Hosting L2 — DeadRamp Phase 2, Remainder Group 4

The founding build of a new category. The remainder census left 23
forks unclassified; the no-signal live-doc research pass resolved
13 of them into **Cloud Infrastructure & Hosting** — vendors whose
public function is the cloud platform itself. This group founds the
category at the Moderate tier (FedRAMP Moderate ≈ CMMC L2) with six
forks, a fresh 17-family taxonomy derived from the forks' own
words, one spec sheet per fork, and a clean-room records core in
`src/cloudinfra/` (Python standard library only).

**These are records about infrastructure.** The core records
tenancies, environments, deployments, templates, service
arrangements, operations tasks, accounts, utilization, and
recommendations. It provisions nothing, orchestrates nothing, and
operates no network. See `UNION-SPEC.md` for the full union spec:
taxonomy derivation, claim ranking with dispositions, the
core-boundary decision, and the Moderate baseline traceability.

## The six forks

| Fork | Vendor / Product | Claims |
|---|---|---|
| AGENCYWC2 | United States Department of the Treasury / Treasury Cloud Moderate (PaaS + SaaS) | 12 |
| F1510137547 | Rackspace Government Solutions / Rackspace Government Cloud (PaaS) | 9 |
| FR2004446306 | Elastic / Elastic Cloud (SaaS) | 5 |
| F1208031461 | IBM / IBM Platform Services for Government (SaaS + PaaS) | 5 |
| FR1719841002 | SAP NS2 / SAP NS2 Cloud Intelligent Enterprise (PaaS + SaaS) | 2 |
| F1602257856 | SAP NS2 / DoD Cloud Intelligent Enterprise – DD-CIE (SaaS) | 1 |

34 claims total, no zero-claim forks. All six are FedRAMP
Certified at Moderate in the marketplace record; category in the
source is "Uncategorized (none in source)" for every one — the
category exists because the live-doc research pass founded it.

## Taxonomy derivation (new category)

The 17 families were derived fresh for this build from two of the
forks' own text sources: their cached marketplace descriptions and
their live-doc classification sentences. Nothing was imported from
another category — in particular not from System Administration:
the census's managed-platform boundary puts administration-services
prose there and pure platform/hosting prose here, and this build
keeps that boundary. Claims fire only on the cached descriptions;
the classification sentences place the forks in the category and
are never claim evidence (for all six forks the classification
sentence does not even occur in the cached description — pinned by
test).

One deliberate absence in the build: **there is no money shape
anywhere.** No fork states an amount, rate, or fee schedule, so
utilization is recorded in integer service units and invoicing is
an Extended gap. This is the one founding build with no cents
discipline, because there is nothing in the forks' words to
denominate.

## Core functions (src/cloudinfra/)

1. Organization registry & membership (carried substrate)
2. Cloud tenancy records — hosting models in the forks' own words
   (`boundary_protected`, `managed`, `enclave`, `shared`);
   deployment counts derived at read, never stored
3. Hosting environment records — caller-stated residency label,
   guarded lifecycle provisioned → active → retired
4. Infrastructure provider registry
5. Hosted deployment records — the **deployment slot rule**: at
   most one active deployment per workload per tenancy, enforced
   on activation by the `_check_deployment_slot` seam (the group's
   negative control); caller-stated encryption label; the build
   performs no cryptography
6. Deployment template registry — settings stored verbatim, never
   executed (test-pinned: no execute/apply/launch operation exists)
7. Monitoring records (continuous / network / log ingestion /
   observability) — records only, no telemetry
8. Platform security service records (IPS/IDS, WAF, endpoint
   protection/EDR, anti-virus, file integrity monitoring)
9. Backup & recovery records — nothing is backed up or restored
10. Identity configuration records — **no field can hold a
    credential** (shape-pinned); the IdP stays with the embedding
    organization (IA-2)
11. Operations task records — patching / scanning / configuration /
    support, due dates required, `overdue` derived at read
12. Cloud account & utilization records — one record per account
    per period, integer units only (floats, booleans, strings
    rejected at the boundary)
13. Recommendation records — issued elsewhere, stored verbatim;
    the build generates none
14. Registry reporting — counts and unit sums; no scores, no money
15. Registry search — membership-scoped substring search
16. RBAC + append-only audit (carried substrate)

## Layout

```
specs/specs.json    one sheet per fork (claims + classification fields)
src/cloudinfra/     the clean-room core (stdlib only)
tests/              unittest suite + negative control + smoke driver
scratch/extract.py  the spec extractor (gitignored scratch)
UNION-SPEC.md       taxonomy, ranking, core boundary, baseline
ARTIFACTS.md        build provenance and recorded artifacts
```

## Run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 118 tests
PYTHONPATH=src python3 tests/smoke.py                       # live smoke
PYTHONPATH=src python3 -m cloudinfra serve                  # http://127.0.0.1:8819
PYTHONPATH=src python3 -m cloudinfra serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cloudinfra serve --certfile cert.pem --keyfile key.pem   # TLS
```

Demo users (hooks for the embedding organization's identity
system, not an IdP): `alice` = admin, `bob` = member,
`carol` = viewer, via `X-User` / `X-Role` headers. Admin holds
every action including `org_write` and `audit_read`; member holds
every working action; viewer is read-only (`org_read`,
`report_read`). Org-scoped operations additionally require
membership in the organization (or admin).

## Control traceability (summary)

Moderate baseline (NIST SP 800-53), CMMC L2 planning equivalence —
with the standing caveat: **FedRAMP authorizes products; CMMC
certifies organizations; the tier is a planning/matching
equivalence, never a credential claim.** AC/IA/AU are answered by
the substrate (role ladder + membership boundary, identity
*configuration* records with no credential field, append-only
audit including denied attempts at the HTTP layer). CM is answered
by tenancy/environment/deployment/template records with guarded
lifecycles and the slot rule as SI-10 validation. CP, SI-2/RA-5,
SI-3/SI-4 are answered at records weight (arrangements and tasks
recorded; the engines are Extended). SC is answered honestly:
encryption and residency exist in this build only as caller-stated
labels on records — the build performs no cryptography, Python's
stdlib is not FIPS-validated, and no FIPS claim is made. CA is
documented in part by Rackspace's own A&A-support claim, an
Extended service. Full table in `UNION-SPEC.md`.

## Honesty

- **Evidence split.** Category membership rests on live vendor
  pages (`classification_evidence` / `classification_source_url`
  on every sheet, pinned against `remainder/nosignal_report.json`);
  claims rest only on the cached marketplace descriptions. The two
  streams never mix, and the spec tests pin that mechanically.
- **SAP caveats.** DD-CIE's classification evidence names SAP IBP
  as the hosted example — recorded at suite weight; CIE's names
  the Government Cloud portfolio. Both SAP descriptions enumerate
  hosted business applications (ERP, payroll, HCM, supply chain);
  those catalogue units were excluded before matching because they
  are other categories' functions riding on this platform. Checked
  result: the exclusion changed no final claim table (each
  catalogue's one would-be hit duplicates an environment sentence
  that precedes it), and it is pinned by test so it cannot quietly
  change one later.
- **Treasury caveat.** No agency page states a distinct Treasury
  Cloud "Moderate" variant — neither confirmed nor refuted; the
  Moderate tier on the sheet comes from the marketplace record
  itself.
- **Tier prose.** Both SAP records assert impact levels in prose
  (IL4/IL5; a DISA PA at IL2 dated 17 March 2026) that differ from
  their marketplace Moderate tier. The tier comes from the record;
  the prose is recorded, and moves nothing.
- **DD-CIE artifact.** DD-CIE's description carries its
  U.S.-citizen operations sentence verbatim, but the house
  sentence split cuts it after "U.S.", so it claims hosting only
  (1 claim). Recorded as an artifact, not repaired — counts are a
  floor.
- **Extended functions** (the hosting platform and provisioning
  engines themselves, the Elastic Stack hosting engine, template
  execution, monitoring/observability engines, security service
  engines, backup/DR execution, the identity provider, encryption
  implementation, operations execution engines, the invoicing and
  FinOps engine, the AI recommendation and resource-management
  engines, CDN operation, A&A support services, residency
  verification) are named in `UNION-SPEC.md` and registered as gaps
  for the repo's final GAPS batch. Nothing in the core performs
  any of them.
- **Demo identities are hooks, not an IdP** (IA-2 stays with the
  embedding organization), here as everywhere in this repo.

## Final GAPS batch (2026-11-07)

The group's 14 open gap entries are closed by
`src/cloudinfra/extensions.py` (`CloudInfraExtensions`, a wrapper
over the core store; core modules byte-identical): 6 built as
records plus read-time derivations (deployment intents referencing
the verbatim template registry, security-service configurations
and reported check results, operation request records, invoice
records and the derived FinOps summary — still no money shape
anywhere, pinned by a recursive key scan — resource allocation
records, and residency/personnel verification cases whose outcomes
are reported, never verified here, under a decider-not-opener
separation-of-duties seam) and 8 shipped as labeled reference
implementations (`reference_stub: true`). Per-entry dispositions
are in `BATCH.md`; the suite is now 150 tests (118 + 32 in
`tests/test_gaps_batch.py`), including the batch's fresh
mutation-verified negative control on the verification seam,
recorded in `tests/README.md`.
