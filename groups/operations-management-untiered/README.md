# Operations Management — Untiered Set

DeadRamp Phase 2 **untiered set**: the 20 Operations Management forks
whose FedRAMP impact level is **"Unknown"** in the GSA FedRAMP
Marketplace dataset. An untiered set is built to its forks' documented
control claims only: **the tier is null**. No FedRAMP baseline
(Low / Moderate / High / LI-SaaS) is asserted for these forks because
the source publishes none, and no CMMC tier equivalence is drawn.
Every spec sheet records the source's impact level ("Unknown") and
`cmmc_tier: null`, pinned by tests. A fork's documented control
language is that fork's claim, never this build's attainment.

Membership is exactly census build unit `untiered:Operations
Management` in `remainder.json`, verified mechanically by the spec
tests. Nine of the twenty were filed in the source under other
categories (five Artificial Intelligence (AI), one Data Management)
or none (five Uncategorized); the census classified them here from
their own descriptions, and the sheets record that assignment.

## The 20 forks

| Fork | Claims |
|---|---|
| AtomAI Solutions Inc. / AtomAI Platform | 0 |
| Concourse Tech Inc. / Concourse Platform | 0 |
| Fulcrum / Fulcrum | 0 |
| Globality Inc / Globality Platform | 0 |
| International Vending Management, Inc. / SmartHub | 1 (`inspections_field_ops`) |
| MaintainX / MaintainX for Government | 0 |
| Nastro Technologies, Inc. / BitRip | 0 |
| NavigatorCRE / NavigatorCRE | 0 |
| NEXGEN Asset Management / NEXGEN Asset Management | 0 |
| Partos Inc. / Partos for Government | 0 |
| Pincus Technologies Inc / Tarly Cowork | 0 |
| Rohirrim, Inc. / Unified Acquisition Platform | 0 |
| Siemens AG / DepotFinity | 0 |
| Signifi Solutions Inc. / SignifiVISION | 0 |
| Silkline, Inc. / Silkline | 0 |
| Standard Technology Inc. / Contract Management Planning and Surveillance System (COMPASS) | 0 |
| Stoke Space Technologies, Inc. / Boltline | 1 (`integrations`) |
| Tansi LLC / Tansi | 0 |
| USU Solutions Inc. / USU IT Asset Management | 0 |
| Xfinion Inc. / Continuously Aware Realtime Tracking Network (CARTN) | 0 |

**2 claims total; 18 of 20 forks are zero-claim.** That is reported
plainly, not repaired: the category taxonomy was applied verbatim
(proof below), 7 raw hits were removed under the founding group's
recorded scoping discipline (6 authorization boundary/status prose,
1 name-only token), and no substance was promoted to a claim. The
set's centre of gravity — asset and maintenance operations, asserted
in substance by at least six forks — matches no taxonomy phrase; it
is registered as gaps and named absences in `UNION-SPEC.md`, with the
full near-miss record in `scratch/ARTIFACTS.md`.

## What the build does (12 core functions)

The founding Operations Management substrate, carried whole:

1. Directory of people and organizations keyed by opaque external
   references (never real identifiers).
2. Projects belonging to organizations, with member roles.
3. Assets with lifecycle status, under projects.
4. Work orders on projects and assets — **overdue derived at read
   time, never stored** (single seam `OpsStore._is_overdue`).
5. Inspections — immutable once recorded, outcomes verbatim, **no
   score computed**.
6. Usage records — integer quantities only (floats/bools rejected),
   sign unconstrained, immutable.
7. Workflow registry — versioned automation definitions; the
   registry **never executes** them.
8. Reports — substrate counts, overdue derived at the requested
   instant.
9. Search across projects, assets, work orders, inspections.
10. REST API (JSON over HTTP, stdlib only), default port 8797.
11. RBAC — fixed 16-action matrix, three roles; `workflow_write` and
    `audit_read` are admin-only.
12. Append-only audit log recording denied attempts as well as
    permitted ones; update/delete refused by the store.

**Core-boundary decision (stated once, here as in UNION-SPEC):** no
core function in this set is claim-supported. The substrate is
carried as the category's merged records machinery, re-anchored to
tier null — carried, not claimed. The forks are in this category
because their own descriptions describe operational work, not because
their vocabulary matches the founding pair's phrases.

## How to run

```bash
cd groups/operations-management-untiered
PYTHONPATH=src python -m opsmgmt serve --port 8797
```

(`serve` is the CLI's only subcommand; `--audit-log`, `--certfile`,
and `--keyfile` are its options, unchanged from the founding build.)

Demo users (hooks, not an IdP — see Honesty):

| User | Role | Access |
|---|---|---|
| alice | admin | all 16 actions, incl. `workflow_write` and `audit_read` |
| bob | operator | all reads except `audit_read`; all writes except `workflow_write` |
| carol | viewer | reads except `audit_read`; no writes |

API surface (JSON, paths as routed by the carried service):
`/health`, `/persons`, `/organizations`, `/projects` (plus
`/{id}/members`), `/assets` (plus `/{id}/transition`),
`/work-orders` (plus `/{id}/assign`, `/{id}/transition`),
`/inspections`, `/usage`, `/workflows`, `/report`, `/search`,
`/audit` — the same endpoints as the founding group's build,
unchanged.

## How to run the tests

```bash
cd groups/operations-management-untiered
PYTHONPATH=src python -m unittest discover -s tests
```

**127 tests, all green** (119 carried core tests + 8 spec tests).
The suite includes a mutation-verified negative control: the
`_is_overdue` subclass mutant in `test_negative_control.py`, plus the
full drill record in `tests/README.md` (exactly 9 failures with the
derivation body replaced by `return False`, store restored
SHA-256-identical).

## Byte-identity accounting

`src/opsmgmt/` is carried whole from
`groups/operations-management-l2/src/opsmgmt/` — **7 of 7 modules
byte-identical** (SHA-256):

| Module | SHA-256 |
|---|---|
| `__init__.py` | c00e2bfe66207932ed1fcbbb7ed99d44fe5b4d2d9c867040147f0cd302ace376 |
| `__main__.py` | b500c5e49dfe5ac3746a2a7c7c6fdf594755f451bcdc29f0fe02f82c1932c044 |
| `access.py` | c23a7ba33330b42d84711c0f8ea0353010f2ad9176561874e580f8eb67eaa96a |
| `audit.py` | e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e |
| `errors.py` | 874a8f52f736655a34e5b2b1e68118b323a4b58dd4bbba32213134a9a1998141 |
| `service.py` | 6c8f07bbb113a10d9739a454e59ee1f3de484f5a26f83d7267fa75e7814b445c |
| `store.py` | 8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6 |

No baseline text had to be edited out of the code: the parent modules
contain no tier references, so the carry needed no modification at
all. The docs (this README, `UNION-SPEC.md`) are re-anchored to tier
null; no Moderate baseline was copied from the parent anywhere.
Taxonomy-verbatim proof: the extractor AST-parsed the parent's
19-family taxonomy (never executing the parent file) and reproduced
the founding group's original 2 sheets / 20 claims (commit `497e8a6`)
deep-equal before tagging this set.

## Documented control claims (summary)

From the forks' own descriptions (full tracing in `UNION-SPEC.md`):
**IA** documented by 4 forks (CAC/PIV via a dedicated IdP — MaintainX;
CAC with X.509 certificates and Duo Federal MFA — COMPASS; multiple
IdPs, SSO, SCIM — Partos; MFA — CARTN). **AC** by 4 (RBAC enforcement
— COMPASS; granular role/group/permission access and dynamically
controlled access — Partos; strictly controlled authentication/
authorization — Globality; network-level controls — CARTN). **SC** by
3 (encryption at rest and in transit — Globality; TLS 1.2+ —
MaintainX; two-way encryption at feature-list weight — Silkline).
**CA** by 3 (vulnerability scanning and configuration drift
detection — MaintainX; SCAP configuration compliance scanning at
catalogue weight — COMPASS; compliance monitoring across ITAR, EAR,
and DFARS — Partos). **AU** by 2, both at records/readiness weight
(audit logs stored — Boltline; audit readiness — IVM). **CM** and
**SI** by 1 each (MaintainX's CIS/STIG container hardening; its
malware scanning and continuous monitoring). **Not documented:**
AT, CP, IR, MA, MP, PE, PL, PM, PS, RA, SA — listed as not
documented, never filled from a baseline. Assertions inside removed
boundary/status prose (Rohirrim's identity plane) and inherited-
platform assertions (COMPASS on Azure Government; USU on its host
provider) are not counted.

## Honesty

- **Tier null, plainly:** these forks have no FedRAMP impact level
  in the source — "Unknown" — so this set asserts no baseline, no
  CMMC tier, and no authorization of any kind. 17 forks are at
  "Initial Implementation" and 3 at "FedRAMP In Process" in the
  source; neither status is an authorization, and nothing here
  claims otherwise.
- **Claims are a floor.** Counts derive only from the forks' own
  cached descriptions under the founding taxonomy's exact phrases.
  18 zero-claim forks include offerings (a CMMS, an AI-native ERP, an
  IT asset management suite) whose substance is real and recorded as
  near-misses and gaps — the zero is a vocabulary result, not a
  capability judgment, and it is not dressed up in either direction.
  Concourse's cached description is visibly truncated mid-listing;
  its floor is over incomplete text.
- **Extended functions, by name:** workflow execution, real-time
  intelligence/analytics engines, AI models, low-code app building,
  integration connector engines, mobile apps and offline sync,
  network/platform operations, authorization services and identity
  providers, security-services and policy enforcement planes,
  governance consoles, scheduling, IoT/telematics collection, and
  this set's own engines (CMMS/EAM depth, manufacturing execution and
  ERP/MRP, procurement and sourcing, contract execution, EV charging
  network management, real-estate portfolio platforms, kiosk/locker
  access management, AI assistants, supply-chain risk and payments)
  are **not built** — they are registered as gaps in `UNION-SPEC.md`.
- **The build performs no cryptography of its own.** The encryption
  language in the Documented control claims section is the forks'
  documented language about themselves, traced to their sentences.
- **Demo identities are hooks, not an IdP.** alice/bob/carol exercise
  the RBAC matrix; identity proofing, credential issuance, and the
  CAC/PIV/MFA mechanisms the forks' prose documents stay with the
  embedding organization.
- **Records, not operations.** The build stores operational records
  keyed by opaque references; it operates no fleet, facility,
  network, kiosk, or charging station, and holds no real personal or
  operational data.
