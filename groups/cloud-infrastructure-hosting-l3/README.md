# Cloud Infrastructure & Hosting L3-adjacent — DeadRamp Phase 2

The High-tier sibling group of the category founded at Moderate
by Remainder Group 4 (`groups/cloud-infrastructure-hosting-l2/`).
The no-signal live-doc research pass resolved 13 forks into
**Cloud Infrastructure & Hosting** — vendors whose public
function is the cloud platform itself — and the six FedRAMP High
forks are this group: one spec sheet per fork under the founding
group's 17-family taxonomy **verbatim**, and the founding
clean-room records core in `src/cloudinfra/` carried up whole and
uplifted to the High baseline (hash-chained fail-closed audit,
audit query, auditor role, logon lockout). See `UNION-SPEC.md`
for the full union spec: the taxonomy-verbatim proof, claim
ranking with dispositions, the core-boundary decision stated
once, the uplift analysis, and the High baseline traceability.

**These are records about infrastructure.** The core records
tenancies, environments, deployments, templates, service
arrangements, operations tasks, accounts, utilization, and
recommendations. It provisions nothing, orchestrates nothing, and
operates no network.

## The six forks

| Fork | Vendor / Product | Claims |
|---|---|---|
| FR1801046750 | United States Department of the Treasury / Treasury Cloud (TCloud) (IaaS + PaaS) | 10 |
| F1208031461A | IBM / IBM Platform Services for Government (SaaS + PaaS) | 5 |
| F1303221956 | IT-CNP / GovDataHosting Cloud Platform (PaaS + IaaS) | 3 |
| F1206081363 | IBM / SmartCloud for Government (IaaS) | 1 |
| F1211011660 | IBM / IBM Cloud for Government (IaaS + PaaS) | 0 |
| FR1900048743 | Oracle / Oracle Cloud Infrastructure-Government Cloud (IaaS + PaaS) | 0 |

19 claims total; two zero-claim forks (IBM Cloud for Government
and Oracle OCI-Gov — flagship infrastructure offerings whose
cached descriptions are posture/overview prose carrying none of
the taxonomy's phrases; their substance is recorded as
near-misses in `UNION-SPEC.md`, not repaired into claims). Five
forks are FedRAMP Certified at High in the marketplace record;
Platform Services (A) is Agency Authorization In Process. The
tier on every sheet comes from the marketplace record.
Category in the source is "Uncategorized (none in source)" for
every one — the category exists because the live-doc research
pass founded it.

Two duplicate-authorization pairs, stated plainly:
F1208031461A is the High sibling of the founding group's
F1208031461 — the two records carry the same description (so the
claim tables match) and differ in tier and status; both stand as
separate offerings. FR1801046750 (TCloud-H) and the founding
AGENCYWC2 (Treasury Cloud Moderate) carry *different*
descriptions; the High table is smaller (10 vs 12) for recorded
reasons (an unhyphenated "multitenant" the tenancy pattern does
not fire on; no CDN named). Neither sheet is adjusted toward the
other.

## Taxonomy — verbatim from the founding group

The 17 families are the founding group's, taken from its
extractor by `ast` parsing (never executed, never re-typed,
never re-tuned). The proof is mechanical and pinned by test:
re-applying the taxonomy to the founding group's six cached
descriptions reproduces its shipped claim tables exactly (34
claims, deep-equal against the founding specs at git HEAD).
Claims fire only on this group's cached descriptions; the
classification sentences place the forks in the category and are
never claim evidence (for all six forks the classification
sentence does not even occur in the cached description — pinned
by test).

One deliberate absence in the build, unchanged from founding:
**there is no money shape anywhere.** No fork at this tier
states an amount, rate, or fee schedule either (IT-CNP names
billing *models*, not amounts), so utilization is recorded in
integer service units and invoicing is an Extended gap.

## Core functions (src/cloudinfra/)

The founding 16, carried up whole:

1. Organization registry & membership (carried substrate)
2. Cloud tenancy records — hosting models in the forks' own words
   (`boundary_protected`, `managed`, `enclave`, `shared`);
   deployment counts derived at read, never stored
3. Hosting environment records — caller-stated residency label,
   guarded lifecycle provisioned → active → retired
4. Infrastructure provider registry
5. Hosted deployment records — the **deployment slot rule**: at
   most one active deployment per workload per tenancy, enforced
   on activation by the `_check_deployment_slot` seam (this
   tier's carried negative control); caller-stated encryption
   label; the build performs no cryptography
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
16. RBAC + append-only audit (carried substrate, uplifted below)

**High uplifts [L3]** (the repo's established High set): the
audit log is **hash-chained** (AU-9/AU-3; `GET /audit/verify`),
**fail-closed** (AU-5; a failed audit write rolls the whole
operation back and the service answers exactly 500), and
**queryable** (AU-7; `GET /audit` reduction parameters); a fourth
role, **auditor**, holds `audit_read` and nothing else (AC-5,
technical slice); the service enforces **logon lockout** after
consecutive authentication failures (AC-7). Byte-identity
accounting against the founding package: 0 of 7 modules
byte-identical — every module differs for a stated uplift reason
(itemized in `UNION-SPEC.md`); no founding behavior is removed.

## Layout

```
specs/specs.json    one sheet per fork (claims + classification fields)
src/cloudinfra/     the founding core, carried up + High uplifts
tests/              unittest suite + two negative controls + smoke driver
scratch/extract.py  the spec extractor (gitignored scratch)
UNION-SPEC.md       taxonomy proof, ranking, core boundary, baseline
ARTIFACTS.md        build provenance and recorded artifacts
```

## Run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests        # 166 tests
PYTHONPATH=src python3 tests/smoke.py                       # live smoke
PYTHONPATH=src python3 -m cloudinfra serve                  # http://127.0.0.1:8819
PYTHONPATH=src python3 -m cloudinfra serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m cloudinfra serve --certfile cert.pem --keyfile key.pem   # TLS
PYTHONPATH=src python3 -m cloudinfra serve --max-failed-logins 5 --lockout-seconds 60   # AC-7 tuning
```

Demo users (hooks for the embedding organization's identity
system, not an IdP): `alice` = admin, `bob` = member,
`carol` = viewer, `dana` = auditor, via `X-User` / `X-Role`
headers. Admin holds every action including `org_write` and
`audit_read`; member holds every working action; viewer is
read-only (`org_read`, `report_read`); auditor holds `audit_read`
only. Org-scoped operations additionally require membership in
the organization (or admin).

## Control traceability (summary)

High baseline (NIST SP 800-53), CMMC L3-adjacent planning
equivalence — with the standing caveat: **FedRAMP authorizes
products; CMMC certifies organizations; the tier is a
planning/matching equivalence, never a credential claim.** The
founding Moderate table carries up whole; the rows that change
are the substrate rows: AC/IA/AU are answered by the four-role
ladder + membership boundary, identity *configuration* records
with no credential field, and the uplifted audit (hash-chained,
fail-closed, queryable, verifiable); AC-7 is answered by the
service-layer lockout. CM is answered by
tenancy/environment/deployment/template records with guarded
lifecycles and the slot rule as SI-10 validation. CP, SI-2/RA-5,
SI-3/SI-4 are answered at records weight (arrangements and tasks
recorded; the engines are Extended). SC is answered honestly:
encryption and residency exist in this build only as
caller-stated labels on records — the build performs no
cryptography beyond the audit chain's SHA-256 (an integrity
mechanism), Python's stdlib is not FIPS-validated, and no FIPS
claim is made; SC-13 and SC-28 are named gaps, not taken. CA is
carried by the baseline only at this tier — no fork here claims
A&A support (the founding tier's Rackspace claim does not
transfer). Full table and uplift analysis in `UNION-SPEC.md`.

## Honesty

- **Evidence split.** Category membership rests on live vendor
  pages (`classification_evidence` / `classification_source_url`
  on every sheet, pinned against `remainder/nosignal_report.json`);
  claims rest only on the cached marketplace descriptions. The two
  streams never mix, and the spec tests pin that mechanically.
- **Taxonomy verbatim, proven.** The founding claim tables are
  reproduced exactly under the ast-parsed taxonomy before this
  group's forks were tagged; the reproduction is a test, not a
  claim in prose.
- **Zero-claim forks stand as zero.** IBM Cloud for Government
  describes provisioning and orchestration in its own words and
  claims nothing, because the family's phrases are the founding
  forks' phrases. Oracle likewise. Counts are a floor; the
  near-misses are itemized in `UNION-SPEC.md` and pinned by test.
- **Duplicate pairs stand as filed.** Platform Services (A)
  shares its Moderate sibling's description and table and differs
  in tier and status; TCloud-H's table is smaller than its
  Moderate sibling's for recorded textual reasons. No sheet was
  adjusted toward its sibling.
- **Source weights.** SmartCloud's classification evidence is a
  legacy IBM-hosted GSA schedule document (rev. January 25,
  2017) — no current product page exists; IBM Cloud for
  Government's is a Service Description updated December 12,
  2018. Both are the vendors' own words, recorded at that weight.
- **Tier prose.** IT-CNP's prose asserts a "FedRAMP Class D
  (High)" certification and inheritable FedRAMP High compliance;
  the tier comes from the marketplace record, the prose is
  recorded as the fork's assertion, and no fork's posture (IL,
  FIPS, or otherwise) transfers to this build.
- **Uplift gaps named, not taken:** stronger authentication
  (IA-2(1)/(2), IA-5 — the IdP layer's, not this build's),
  FIPS-validated cryptography (SC-13), encryption at rest
  (SC-28), audit retention (AU-11), session lock/termination
  (AC-11, AC-12). The AC-5 claim is a technical slice (a role
  that can review the trail and do nothing else); organizational
  separation of duties remains the embedding organization's.
- **Extended functions** (the hosting platform and provisioning
  engines themselves, template execution, monitoring/observability
  engines, security service engines, backup/DR execution, the
  identity provider, encryption implementation, operations
  execution engines, the invoicing and FinOps engine, the AI
  recommendation and resource-management engines, CDN operation,
  A&A support services, residency verification) are named in
  `UNION-SPEC.md` with their claimant state at this tier; the
  founding registrations stand and are not re-registered.
  Nothing in the core performs any of them.
- **Demo identities are hooks, not an IdP** (IA-2 stays with the
  embedding organization), here as everywhere in this repo.
