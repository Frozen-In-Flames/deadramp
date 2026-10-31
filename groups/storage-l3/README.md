# Storage — CMMC L3-adjacent (DeadRamp Phase 2 remainder singleton)

The Storage category's substrate, carried up to the High
baseline: organization, retention-policy, and archive-collection
registries keyed by opaque references; message archive records
holding **metadata only** (this build stores no message
payloads, no subjects, no bodies); retention state **derived at
read** with a gated disposition; and discovery, supervision,
enforcement, retrieval, key-custody, and integration records —
now with a hash-chained, fail-closed audit trail, a separated
auditor role, and logon lockout. It exists because the FedRAMP
marketplace contains exactly **1 offering** in this category at
this tier, and DeadRamp builds the open substrate underneath
it.

This singleton's fork is a genuinely different kind of storage
offering from the category's founder: a backup and recovery
service, not a message archive. Spec'd under the founding
taxonomy verbatim, **its description claims none of the 11
families** — the honest zero, recorded in the union spec with
the near-miss accounting. Under the Merge Rule the L2 substrate
is therefore carried up **whole** and uplifted to High, with
every function flagged **carried, not claimed** for this fork;
the fork's own substance (backup & recovery, anomaly alerting,
remediation, workload connectors, its console, SaaS automation,
hybrid synchronization) is registered as named gaps, not built.

## The fork

| Fork | Tier | Status |
|---|---|---|
| **Commvault Cloud for Government** — Commvault Systems, Inc. (FR2115384377) | High → CMMC **L3-adjacent**, SaaS, Government Community Cloud | FedRAMP Certified |

Full spec sheet: [`specs/specs.json`](specs/specs.json). Union
contract, the zero-claim accounting, claim ranking, control
traceability, and gaps: [`UNION-SPEC.md`](UNION-SPEC.md).

**What the fork's own description supports: 0 claims.** Its five
fragments include a workloads catalogue (Microsoft 365,
Dynamics 365, Salesforce, Active Directory, VM & Kubernetes,
Endpoint, File & Object, Database, Air Gap Protection), excluded
before matching as a third-party catalogue; the description's
only raw taxonomy hit — "Active Directory" — sits inside that
catalogue as a protected-workload label and was removed by the
exclusion. Two of the parent group's named absences retire here
**in substance**, on this fork's own words: **backup** (its
headline function, with recovery) and **audit** ("integrated
audit reports") — both retire as substrate observations, not
claims. The signature family of the founding fork, retention,
does not occur in this fork's prose at all; the retention
substrate below is carried, and is labelled as such.

## The build

The parent core, carried up whole (14 functions):

- **Organization, policy & collection registries** — opaque
  `ref` + label only; retention policies are immutable records
  with integer-day periods, so every derivation is reproducible
  against the policy a collection named.
- **Message archive records** — an opaque message reference,
  opaque sender/recipient references, an archived-at moment, a
  recorded size, a format label. The pinned shape has **no
  field that could hold a subject, a body, or any content**.
- **Retention derivation & disposition gate (signature
  invariant)** — a message's retention state (`retained` /
  `disposition_eligible` / `disposed`) is computed on read from
  the archived-at moment, the policy period, and the presence
  of a disposition record; **no state field is ever stored**. A
  disposition may be recorded only once the derived state is
  `disposition_eligible` — inside retention the gate refuses.
- **Discovery records** — a recorded matter, collection, and
  metadata scope, with the result set computed from the archive
  records. There is deliberately **no free-text query field**.
- **Supervision & enforcement records** — review records with a
  recorded-action lifecycle, and enforcement action records from
  a fixed vocabulary. Records only: nothing executes.
- **Retrieval & export records** — realtime or batch, to an
  inbox, a data file, or the interface; delivery itself is
  Extended transport.
- **Key custody records** — a custodian by opaque reference and
  a key by opaque label; **no key material exists in any
  shape**, and at most one custody record per collection may be
  active.
- **Integration registry** — records of integrations. The
  registry **never executes**: registering one connects nothing
  and moves no message.
- **Search & summary** — literal substring search over record
  metadata; counts and recorded values computed on read, no
  computed scores anywhere.
- **REST API + CLI**, role-based access, and the audit log —
  uplifted at this tier, below.

## High-baseline uplifts (what changed from the L2 build)

- **Hash-chained audit (AU-9/AU-3)** — every audit entry carries
  `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical
  JSON; `AuditLog.verify_chain()` localizes the first bad
  entry; `GET /audit/verify` exposes the result.
- **Fail-closed audit writes (AU-5)** — if the audit write
  fails, the operation rolls back entirely (records and id
  counters) and the service answers exactly 500
  `{"error": "audit write failed"}`. An operation whose audit
  write fails does not proceed.
- **Audit reduction (AU-7)** — `AuditLog.query(actor, action,
  target, since, until)` and matching `GET /audit` filters.
- **Auditor role (AC-5)** — `dana=auditor` holds `audit_read`
  and nothing else: audit review is a duty separable from
  administration.
- **Logon lockout (AC-7)** — per-username consecutive
  authentication-failure tracking; lockout at 3 failures for
  300 s (configurable); locked attempts are answered 403 and
  audited `auth:locked`; permission denials do not count.

**Byte-identity accounting vs the parent:** 0 of 7 source
modules are byte-identical to `groups/storage-l2/` — every
module changed, six for the uplifts above and `__init__.py` for
the tier re-anchor of its docstring alone. The full SHA-256
table and per-file change reasons are in
`scratch/reuse-note.md`. The carried behavior is the parent's:
the parent's test files are carried and pass unchanged except
where the uplifts extend them.

**Not taken at High (named gaps, not silent omissions):** MFA &
authenticator management (IA-2(1)/(2), IA-5), FIPS-validated
cryptography (SC-13), encryption at rest (SC-28), audit
retention (AU-11), session lock/termination (AC-11/AC-12).

## Run it

```sh
PYTHONPATH=src python3 -m storage serve --port 8765
# demo users: alice=admin, bob=operator, carol=viewer, dana=auditor
# (X-User / X-Role headers; dana holds audit_read only)
PYTHONPATH=src python3 -m unittest discover -s tests   # 127 tests
```

Python 3 standard library only; there is nothing to install.

## Control mapping (summary)

Built to the **FedRAMP High / CMMC L3-adjacent** baseline (NIST
SP 800-53 Rev. 5 High, cross-walked to the NIST SP 800-171
practices plus selected SP 800-172 enhancements): access
enforcement on every operation (AC-2/AC-3/AC-6) with separation
of audit review (AC-5) and logon lockout (AC-7); audit of
mutations and denied attempts (AU-2/AU-3/AU-6/AU-9 — append-only
and hash-chained, fail-closed under AU-5, reducible under
AU-7, with audit reads gated on the `audit_read` permission);
input validation at the boundary (SI-10); and all
date-dependent state derived from retained records through a
single seam (CM-6). **No SC-12/SC-13 claim is made**: this build
holds no keys and claims no FIPS-validated cryptography — the
fork's IL4/IL5 platform posture is the fork's property and does
not transfer. Full traceability table, uplift analysis, and
precision notes in [`UNION-SPEC.md`](UNION-SPEC.md).

## Honesty

- **Nothing here is a FedRAMP authorization or a CMMC
  certification.** FedRAMP authorizes products; CMMC certifies
  organizations. The tier mapping is a planning equivalence.
  The fork's FedRAMP Certified status, and any property of the
  fork's own platform — including its IL4/IL5 posture, its air
  gap offering, and its hosting — belong to the fork and do
  **not** transfer to this build.
- **Zero claims means zero.** This fork's description supports
  no taxonomy family; every function in this build is carried
  substrate from the L2 union, labelled carried-not-claimed.
  Nothing in this README or the union spec should be read as
  "Commvault claims the retention gate" — its prose never says
  "retention" at all.
- **This build stores no actual data payloads.** It holds
  metadata records about archived messages. There is no subject,
  body, attachment, or content field on any record shape, and
  no key material anywhere: a custody record is a custodian
  reference and a key label, nothing more. Despite this fork
  being a backup product, this build **backs up nothing**: the
  backup & recovery engine is a named gap.
- **Extended functions are specified, not implemented** (see
  UNION-SPEC gaps): the backup & recovery engine, the anomaly
  detection & alerting engine, the granular remediation engine,
  workload protection connectors, the Command Center console,
  SaaS operations automation, the hybrid synchronization
  engine, and — referenced from the parent union — the payload
  storage plane, the ingest pipeline, the full-text content
  search engine, the encryption/decryption engine, key
  management hardware, retrieval delivery, the supervision
  console, enforcement execution, the live connectors, and
  disposition execution.
- **Demo identities are hooks, not an IdP.** `alice` / `bob` /
  `carol` / `dana` exist so the permission matrix — including
  the separated auditor — can be exercised; IA-2 stays with the
  embedding organization, and at this tier that organization
  must supply MFA-grade authentication (a named gap here).
- Claims in the spec are a **floor**: a function is claimed
  only where the offering's own marketplace description states
  it, with the sentence stored as evidence. This fork states
  none of the taxonomy's functions, so the floor here is zero —
  recorded, not rounded up.
