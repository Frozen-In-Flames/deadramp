# Storage — CMMC L2 (DeadRamp Phase 2 remainder singleton)

A clean-room, open-source implementation of the records
substrate for **message archiving storage**: organization,
retention-policy, and archive-collection registries keyed by
opaque references; message archive records holding **metadata
only** (this build stores no message payloads, no subjects, no
bodies); retention state **derived at read** with a gated
disposition; and discovery, supervision, enforcement, retrieval,
key-custody, and integration records. It exists because the
FedRAMP marketplace contains exactly **1 offering** in this
category at this tier, and DeadRamp builds the open substrate
underneath it.

This is a **brand-new category**: no shipped group exists for
Storage at any tier. The remainder census proposed Storage for
this fork from its own description (classifier note: "Email
archiving, retention, search and retrieval"). `forks.json` files
the fork "Uncategorized (none in source)"; its source record
carries an empty business-categories list. The category here is
the census proposal, not a source field — recorded as such in
the spec. A sibling singleton at L3-adjacent will later carry
this group's substrate up a tier.

## The fork

| Fork | Tier | Status |
|---|---|---|
| **Proofpoint Email Archive** — Proofpoint, Inc. (F1304222071) | Moderate → CMMC **L2**, SaaS, Government Community Cloud | FedRAMP Certified |

Full spec sheet, with every function claim carrying its source
sentence as evidence: [`specs/specs.json`](specs/specs.json).
Union contract, claim ranking, control traceability, and gaps:
[`UNION-SPEC.md`](UNION-SPEC.md).

**What the fork's own description supports: 11 claims, one per
family of an 11-family taxonomy defined from its own
vocabulary** — message archiving, email storage management,
retention, search & discovery, supervision, policy enforcement,
retrieval & export, mail platform integration, directory
integration & unified login, message encryption & decryption,
and customer-held key custody. The description contains **no
object/block/file storage, backup, replication, tiering,
versioning, immutability, legal-hold, or FIPS vocabulary at
all**: the category as this fork's own words define it is
message archiving storage, and nothing else was claimed, so
nothing else is owed (full absence list in
`scratch/ARTIFACTS.md`).

## The build

The core is the records form of what those claims presuppose,
built at the Moderate/L2 baseline:

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
  the archived-at moment, the policy period, and the presence of
  a disposition record; **no state field is ever stored**. A
  disposition may be recorded only once the derived state is
  `disposition_eligible` — inside retention the gate refuses.
- **Discovery records** — a recorded matter, collection, and
  metadata scope, with the result set computed from the archive
  records. There is deliberately **no free-text query field**:
  there is no content here for a query to name.
- **Supervision & enforcement records** — review records with a
  recorded-action lifecycle (an `extend_retention` enforcement
  record provably does not change the derivation), and
  enforcement action records from a fixed vocabulary.
- **Retrieval & export records** — realtime or batch, to an
  inbox, a data file, or the interface; delivery itself is
  Extended transport.
- **Key custody records** — a custodian by opaque reference and
  a key by opaque label; **no key material exists in any
  shape**, and at most one custody record per collection may be
  active — the fork's own statement is that a single holder
  holds the keys.
- **Integration registry** — records of the mail-platform and
  directory integrations. The registry **never executes**:
  registering one connects nothing and moves no message.
- **Search & summary** — literal substring search over record
  metadata; counts and recorded values computed on read, no
  computed scores anywhere.
- **REST API + CLI**, role-based access (admin / operator /
  viewer), and an append-only audit log recording mutations and
  denied attempts.

## Run it

```sh
PYTHONPATH=src python3 -m storage serve --port 8765
# demo users: alice=admin, bob=operator, carol=viewer (X-User / X-Role headers)
PYTHONPATH=src python3 -m unittest discover -s tests   # 79 tests
```

Python 3 standard library only; there is nothing to install.

## Control mapping (summary)

Built to the **FedRAMP Moderate / CMMC L2** baseline (NIST SP
800-53 Rev. 5 Moderate, cross-walked to the NIST SP 800-171
practices): access enforcement on every operation (AC-2/AC-3/
AC-6), audit of mutations and denied attempts (AU-2/AU-3/AU-6/
AU-9 — append-only, with audit reads restricted to the
admin-only `audit_read` permission), input validation at the
boundary (SI-10), and all date-dependent state derived from
retained records through a single seam (CM-6). **No SC-12/SC-13
claim is made**: this build holds no keys and performs no
cryptography. Full traceability table and precision notes in
[`UNION-SPEC.md`](UNION-SPEC.md).

## Honesty

- **Nothing here is a FedRAMP authorization or a CMMC
  certification.** FedRAMP authorizes products; CMMC certifies
  organizations. The tier mapping is a planning equivalence. The
  fork's FedRAMP Certified status, and any property of the fork's
  own platform — including its encryption technology, its key
  custody arrangement, and its hosting posture — belong to the
  fork and do **not** transfer to this build.
- **This build stores no actual data payloads.** It holds
  metadata records about archived messages. There is no subject,
  body, attachment, or content field on any record shape, and no
  key material anywhere: a custody record is a custodian
  reference and a key label, nothing more. The build performs no
  cryptography.
- **Extended functions are specified, not implemented** (see
  UNION-SPEC gaps): the payload storage plane, the ingest
  pipeline, the full-text content search engine, the
  encryption/decryption engine, key management hardware and
  premise equipment, retrieval delivery and export file
  production, the supervision console, enforcement execution,
  the live connectors, and disposition execution (payload
  destruction).
- **Demo identities are hooks, not an IdP.** `alice` / `bob` /
  `carol` exist so the permission matrix can be exercised; IA-2
  stays with the embedding organization.
- Claims in the spec are a **floor**: a function is claimed
  only where the offering's own marketplace description states
  it, with the sentence stored as evidence. Both census
  citations verify verbatim and both happen to be claim-bearing
  sentences (for the archiving/storage-management and
  retention/retrieval families) — recorded as the coincidence
  direction; no citation was load-bearing.
