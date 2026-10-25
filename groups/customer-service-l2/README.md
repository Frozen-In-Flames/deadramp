# Customer Service L2 — DeadRamp Group 27

A clean-room, open-source build of the merged Customer Service
sibling group at the CMMC L2 tier: **2 forks, both FedRAMP
Moderate** — NCR VOYIX GOVERNMENT CLOUD (NCR Government, LLC) and
Virtual Employee Network (VEN) (Relocation Management Worldwide
(RMW)). One merged implementation per the Merge Rule: union of the
parent baselines at the group's tier (here, NIST SP 800-53 Rev. 5
Moderate ⇔ CMMC L2 / NIST SP 800-171).

What it is: the customer-service **records substrate** this
category's union defines — cases with a lifecycle, requesters keyed
by opaque references only, assignment, priority/due records with
breach derived at read, alert records, on-call rotations with a
derived current on-call, a derived public status view, an automation
rule registry that never executes, registry reporting and search,
RBAC, and an append-only audit log. The implementation is Group
26's shipped L1 code reused byte-identical (SHA-256 verified, 21 of
21 files); the baseline is written fresh for Moderate. Python
standard library only; zero third-party dependencies.

What it is not: a point-of-sale commerce platform, a relocation /
PCS finance system, an incident-detection or event-orchestration
engine, a workflow execution engine, a GRC platform, a chat/voice
channel, or an AI deflection bot. Those are Extended functions,
specified in `UNION-SPEC.md` and registered in the repo-level
`GAPS.md` for the final batch.

## Run it

From this directory:

```
PYTHONPATH=src python3 -m custsvc serve            # http://127.0.0.1:8799
PYTHONPATH=src python3 -m custsvc serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m custsvc serve --certfile cert.pem --keyfile key.pem
```

Demo users (hooks, not an identity provider — production identity
belongs to the embedding organization):

| User | Role | Can |
|---|---|---|
| `alice` | admin | everything, incl. rule writes and audit read |
| `bob` | agent | all reads except audit; writes cases, requesters, responders, alerts, schedules |
| `carol` | viewer | reads only (no audit) |

Authenticate with `X-User` / `X-Role` headers matching a row above.

## Tests

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

69 tests, all passing, including one mutation-verified negative
control. See `tests/README.md` for the coverage map and the mutation
record.

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
| `GET /audit` | audit_read (admin) | append-only audit entries |

Errors: validation → 400, not found → 404, permission denied → 403,
unauthenticated → 401. Denied attempts are audited as
`<action>:denied`.

## Control mapping (summary)

Full traceability in `UNION-SPEC.md`. At the Moderate baseline:
access hooks → AC / IA (identity supplied by the embedding
organization; hooks, not an IdP; 800-171 families 3.1 / 3.5 on the
CMMC side); audit log → AU (AU-2/AU-3/AU-6) — and unlike at L1, the
audit claim holds on both sides of the crosswalk, because 800-171
carries an audit family (3.3) where FAR 52.204-21 carries none;
records and derivations → SI (SI-10 input validation) and SC (SC-8:
TLS when a certificate is configured). Encryption at rest is a
deployment-layer control and is not claimed. This mapping is not a
FedRAMP authorization and not a CMMC certification.

## Honesty section

- **Group character.** This sibling group is a source-category
  artifact, more completely than its L1 sibling. NCR VOYIX
  Government Cloud is a commerce point-of-sale hosting environment;
  it claims **zero functions in any taxonomy family**, and its
  source record carries an empty business_categories list — the
  source does not self-categorize it at all. VEN is a PCS employee
  relocation system that claims exactly one family (reporting).
  **Neither fork claims any core customer-service function.** The
  build implements the category substrate at this tier under a
  recorded core-boundary decision; both forks' actual domains are
  Extended gaps. Nothing was invented to make either look like a
  helpdesk.
- **Claims discipline.** 1 raw keyword hit → 1 surviving claim, the
  thinnest claim mass in the category. No corrections were needed
  (no raw hit described vendor posture). Six near-misses are
  recorded in `scratch/ARTIFACTS.md` — including VEN's pervasive
  "Fully automates…" prose, which does not tag `automation_workflows`
  under the verbatim Group 26 regex and was not promoted. The
  taxonomy and its regexes were deliberately not re-tuned for this
  group, preserving cross-tier comparability.
- **Zero-claim families.** 15 of 16 taxonomy families tag 0 claims.
  Nine of the ten Core functions are carried, not claimed, at this
  tier; the exception is registry reporting (function 9), which
  VEN's "runs real-time reports" claims outright. Knowledge base
  articles and satisfaction surveys are named absences — claimed by
  neither sibling at either tier, not built, not implied.
- **Reuse, stated plainly.** The code is Group 26's, byte-identical
  (21 of 21 files, SHA-256 verified; store.py `05c749f3…` in both
  trees). What this group adds is its own specs, its own
  Moderate-baseline spec, its own mutation drill and smoke — not
  new code, because these forks' claims demand none.
- **Derivations, not engines.** Breach state, on-call assignment
  and the public status view are computed at read time from
  records. Automation rules are stored and never executed; a test
  pins that a matching rule changes no state. Alert records are
  stored and triaged; no detection happens here.
- **Privacy.** Requester records hold an opaque caller-supplied
  reference and a label, nothing else — the exact record shape is
  pinned by tests so no identifier field can slip in. Alert sources
  are opaque references too. This matters at this tier in
  particular: the one claiming fork's domain is employee relocation
  records, and the substrate still holds no real identifier for
  anyone.
- **Tier precision.** The baseline is written fresh for
  Moderate/L2. High-tier apparatus (hash-chained audit, lockout,
  auditor role) is deliberately not inherited sideways and not
  claimed; Group 26's Low-tier framing is not imported either.
- **Deployment.** Single-tenant reference deployment; multi-tenancy
  is a deployment property, not implemented. TLS only when a
  certificate is configured.

## Layout

- `specs/specs.json` — 2 spec sheets with evidence sentences
- `UNION-SPEC.md` — the merged spec: ranking, core, baseline,
  contract, gaps
- `src/custsvc/` — errors, access, audit, store, service, `__main__`
  (byte-identical to Group 26's; SHA-256 verified)
- `tests/` — 14 files incl. helpers and the negative control;
  `tests/README.md` carries the coverage map and mutation record
- `scratch/` — extractor, raw descriptions, function counts,
  artifact log, pre-mutation store copy + hash, mutation output,
  smoke script + log

License: Apache-2.0 (repo-level). Copyright 2026 Aries Hilton.
