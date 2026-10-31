# Customer Service L3-adjacent — DeadRamp Group 41 singleton

A clean-room, open-source build of the Customer Service singleton
at the CMMC L3-adjacent tier: **1 fork, FedRAMP High** — Federal
High Impact Virtualized Environment (FedHIVE) (Human Resources
Technologies, Inc. (HRTec)). One merged implementation per the
Merge Rule: the category substrate defined at L1/L2 (Groups 26/27)
carried up whole and uplifted to the High baseline (NIST SP 800-53
Rev. 5 High ⇔ CMMC L3-adjacent: 800-171 plus selected 800-172
enhanced requirements).

What it is: the customer-service **records substrate** this
category's union defines — cases with a lifecycle, requesters keyed
by opaque references only, assignment, priority/due records with
breach derived at read, alert records, on-call rotations with a
derived current on-call, a derived public status view, an
automation rule registry that never executes, registry reporting
and search, RBAC, and an append-only, **hash-chained, fail-closed,
queryable** audit log with logon lockout and a dedicated auditor
role [L3 uplifts]. The implementation is the Group 26/27 code
uplifted (all seven modules modified for the tier; per-file
SHA-256 in `scratch/reuse-note.md`). Python standard library only;
zero third-party dependencies.

What it is not: a virtualization or cloud hosting platform, an
authorization-acceleration or control-inheritance service, a SOC,
a migration service, an incident-detection or event-orchestration
engine, a workflow execution engine, a GRC platform, a chat/voice
channel, or any of the ~20 third-party applications FedHIVE hosts.
Those are Extended functions / platform-layer gaps, specified in
`UNION-SPEC.md` and registered in the repo-level `GAPS.md` for the
final batch.

## Run it

From this directory:

```
PYTHONPATH=src python3 -m custsvc serve            # http://127.0.0.1:8799
PYTHONPATH=src python3 -m custsvc serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m custsvc serve --certfile cert.pem --keyfile key.pem
PYTHONPATH=src python3 -m custsvc serve --max-failed-logins 3 --lockout-seconds 300
```

Demo users (hooks, not an identity provider — production identity
belongs to the embedding organization):

| User | Role | Can |
|---|---|---|
| `alice` | admin | everything, incl. rule writes and audit read |
| `bob` | agent | all reads except audit; writes cases, requesters, responders, alerts, schedules |
| `carol` | viewer | reads only (no audit) |
| `dana` | auditor | audit read only (AC-5) [L3] |

Authenticate with `X-User` / `X-Role` headers matching a row above.
Consecutive failed logons lock a username (AC-7): at
`--max-failed-logins` (default 3) the account locks for
`--lockout-seconds` (default 300) and further attempts get 403.

## Tests

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

126 tests, all passing (112 shipped + 14 remainder-addition),
including two mutation-verified negative controls. See
`tests/README.md` for the coverage map and the mutation records.

## Remainder addition (Oct 31, 2026)

One previously uncategorized fork joined this group under census
unit `addition:customer-service-l3`: **Medallia GovCloud**
(Medallia, Inc., FedRAMP High / Certified) — see
[`ADDENDUM.md`](ADDENDUM.md). It is the first fork at this tier to
claim anything: **2 claims** under the verbatim taxonomy
(satisfaction surveys — retiring the category's standing named
absence at this tier — and AI assistance, giving the registered
AI gap a claimant here). The core is unchanged (`src/`
byte-identical; all 10 functions remain carried, not claimed, for
both forks), FedHIVE's sheet stands at zero claims, and the
enlarged suite is **126 tests, green**, with both signature
drills re-run in this tree (8 and 3 failures under mutation, each
exactly the shipped set plus one additions case).

## Endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | open, no auth |
| `POST /requesters` · `GET /requesters` · `GET /requesters/{id}` | requester_write / _read | body: `{ref, label}` — opaque ref only |
| `POST /responders` · `GET /responders` | responder_write / _read | body: `{label, team}` |
| `POST /cases` · `GET /cases` · `GET /cases/{id}` | case_write / case_read | filters: `status`, `priority`, `assignee`; `now` pins derivation time |
| `POST /cases/{id}/status` | case_write | body: `{status}`; lifecycle-guarded |
| `POST /cases/{id}/assign` | case_write | body: `{responder_id}` |
| `POST /cases/{id}/updates` · `GET /cases/{id}/updates` | case_write / case_read | body: `{body, public}` |
| `POST /alerts` · `POST /alerts/bulk` · `GET /alerts` | alert_write / alert_read | bulk body: `{alerts: [...]}`; atomic |
| `POST /alerts/{id}/acknowledge` · `/resolve` · `/link` | alert_write | link body: `{case_id}` |
| `POST /schedules` · `GET /schedules` · `GET /schedules/{id}/on-call?at=` | schedule_write / _read | rotation records; on-call derived |
| `POST /rules` · `GET /rules` · `POST /rules/{id}/enabled` | rule_write (admin) / rule_read | registry only — never executed |
| `GET /status` | case_read | derived public status view (public updates only) |
| `GET /reports/summary` | report_read | registry counts + derived breach count |
| `GET /search?q=` | case_read | substring over titles, bodies, requester labels |
| `GET /audit` | audit_read (admin, auditor) | append-only, hash-chained entries; optional filters `actor`, `action`, `target`, `since`, `until` [L3] |
| `GET /audit/verify` | audit_read (admin, auditor) | `{ok, entries, first_bad_index}` — hash-chain verification [L3] |

Errors: validation → 400, not found → 404, permission denied → 403,
unauthenticated → 401, locked account → 403. Denied attempts are
audited as `<action>:denied`; locked attempts as `auth:locked`. An
operation whose audit write fails does not proceed (AU-5 fail
closed).

## Control mapping (summary)

Full traceability in `UNION-SPEC.md`. At the High baseline: access
hooks → AC / IA (identity supplied by the embedding organization;
hooks, not an IdP), with the auditor role separating audit review
(AC-5) and service-layer logon lockout (AC-7); audit log → AU
(AU-2/AU-3 content, AU-9 hash-chain protection, AU-5 fail-closed
writes, AU-6/AU-7 review and reduction); records and derivations →
SI (SI-10 input validation) and SC (SC-8: TLS when a certificate is
configured). Gap-listed, never implied closed: MFA / authenticator
management (IA-2(1)/(2), IA-5), FIPS-validated cryptography
(SC-13), encryption at rest (SC-28), audit retention (AU-11),
session lock / termination (AC-11/AC-12). This mapping is not a
FedRAMP authorization and not a CMMC certification: FedRAMP
authorizes products; CMMC certifies organizations.

## Honesty section

- **Group character.** This singleton is a source-category
  artifact of the purest kind in the category: FedHIVE is a
  FedRAMP High virtualized-environment hosting platform (IaaS /
  PaaS / SaaS inside one authorization boundary) filed under
  Customer Service, and its source record carries an **empty**
  business_categories list — the source does not self-categorize
  it at all. Its description claims **zero functions in any of the
  category's 16 taxonomy families**. The build implements the
  category substrate at this tier under a recorded core-boundary
  decision; the fork's actual domain is Extended / platform-layer
  gaps. Nothing was invented to make it look like a helpdesk.
- **Claims discipline.** 0 raw hits in the fork's own prose → 0
  surviving claims. Two recorded scoping facts: (1) the
  description's trailing catalogue of ~20 third-party hosted
  applications was excluded before matching — matching the full
  text would have manufactured 6 family hits, every one from
  another vendor's blurb (full accounting in
  `scratch/ARTIFACTS.md`); (2) the closest genuine approach,
  compliance-framework prose ("NIST SP 800-53", "(P-ATO)"), misses
  the verbatim patterns on wording alone and is recorded as a
  near-miss. Nine near-misses are itemized; the taxonomy was not
  re-tuned.
- **Zero-claim families.** All 16. All ten Core functions are
  carried, not claimed, at this tier — flagged once, plainly, in
  the spec's core-boundary decision (the Merge Rule carries the
  category union upward whole; a wording artifact is not a
  downgrade). Knowledge base articles and satisfaction surveys
  remain named absences at every tier of this category.
- **Reuse, stated plainly.** The code is the Group 26/27 build's,
  uplifted: all 7 `src/custsvc/` modules modified for High (hash
  chain, fail-closed writes, audit query, lockout, auditor role);
  no core behavior changed — the inherited suite passes with only
  the documented adaptations listed in `tests/README.md`.
- **Derivations, not engines.** Breach state, on-call assignment
  and the public status view are computed at read time from
  records. Automation rules are stored and never executed; a test
  pins that a matching rule changes no state. Alert records are
  stored and triaged; no detection happens here.
- **Privacy.** Requester records hold an opaque caller-supplied
  reference and a label, nothing else — the exact record shape is
  pinned by tests so no identifier field can slip in. Alert
  sources are opaque references too. The fork's stated purpose is
  protecting CUI and PII inside its boundary; the substrate still
  holds no real identifier for anyone.
- **Deployment.** Single-tenant reference deployment (the fork
  itself is a multi-agency environment; tenant isolation is a
  deployment property, not implemented). TLS only when a
  certificate is configured. Demo identities are hooks, not an
  IdP (IA-2 stays with the embedding organization).

## Layout

- `specs/specs.json` — 1 spec sheet with the full description
- `UNION-SPEC.md` — the merged spec: ranking, core, baseline,
  uplift analysis, contract, gaps
- `src/custsvc/` — errors, access, audit, store, service, `__main__`
  (Group 26/27 code, uplifted to High; see `scratch/reuse-note.md`)
- `tests/` — 18 files incl. helpers and two negative controls;
  `tests/README.md` carries the coverage map and mutation records
- `scratch/` — extractor, raw descriptions, function counts,
  artifact log, reuse note, pre-mutation store/audit copies +
  hashes, mutation outputs, patch scripts

License: Apache-2.0 (repo-level). Copyright 2026 Aries Hilton.
