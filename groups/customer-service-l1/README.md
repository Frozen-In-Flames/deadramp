# Customer Service L1 — DeadRamp Group 26

A clean-room, open-source build of the merged Customer Service
sibling group at the CMMC L1 tier: **2 forks, both FedRAMP Low** —
PagerDuty Operations Cloud (PagerDuty) and Riskuity (Longevity
Consulting). One merged implementation per the Merge Rule: union of
the parent baselines at the group's tier (here, NIST SP 800-53 Rev. 5
Low ⇔ CMMC L1 / FAR 52.204-21).

What it is: the customer-service **records substrate** the group's
claimed functions presuppose — cases with a lifecycle, requesters
keyed by opaque references only, assignment, priority/due records
with breach derived at read, alert records, on-call rotations with a
derived current on-call, a derived public status view, an automation
rule registry that never executes, registry reporting and search,
RBAC, and an append-only audit log. Python standard library only;
zero third-party dependencies.

What it is not: an incident-detection or event-orchestration engine,
a workflow execution engine, a GRC platform, a chat/voice channel, or
an AI deflection bot. Those are Extended functions, specified in
`UNION-SPEC.md` and registered in the repo-level `GAPS.md` for the
final batch.

## Remainder addition (Oct 31, 2026)

One previously uncategorized fork joined the group under census
unit `addition:customer-service-l1`: **Zendesk / Zendesk Customer
Support and Help Desk Platform** (`FR1821856903`, FedRAMP LI-SaaS /
Certified) — see `ADDENDUM.md`. It is a **zero-claim fork**: its
three-sentence marketplace description contains no taxonomy token,
so it adds **0 claims** (group total unchanged at 8; now 2 of 3
forks claiming) and **no core change** (`src/` byte-identical).
Its substance — self-service and proactive engagement — is
registered as gap material in the addendum, not claimed. The group
composition is now Low 2 + LI-SaaS 1 (the Low union baseline is
unchanged; LI-SaaS adds nothing). Tests are now **80, all passing**,
including a re-run of the breach-derivation drill (exactly 8
failures under the mutant; see `tests/README.md`).

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

80 tests, all passing, including one mutation-verified negative
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

Full traceability in `UNION-SPEC.md`. At the Low baseline: access
hooks → AC / IA (identity supplied by the embedding organization;
hooks, not an IdP); audit log → AU **on the FedRAMP Low side only**
(FAR 52.204-21 carries no audit practice — no CMMC-side audit claim
is made); records and derivations → SI (SI-10 input validation) and
SC (SC-8: TLS when a certificate is configured). Encryption at rest
is a deployment-layer control and is not claimed. This mapping is not
a FedRAMP authorization and not a CMMC certification.

## Honesty section

- **Group character.** This sibling group is largely a
  source-category artifact. PagerDuty Operations Cloud claims 7
  function families, all on the operations/incident side of customer
  service. Riskuity is a GRC platform that claims exactly one family
  (GRC) and **zero customer-service functions**; its source record
  carries an empty business_categories list. The build implements the
  substrate PagerDuty's claims presuppose; Riskuity's GRC platform is
  an Extended gap. Nothing was invented to make the two look alike.
- **Claims discipline.** 9 raw keyword hits → 8 surviving claims. One
  claim was removed as a documented wording artifact (Riskuity's
  NIST/RMF/ATO sentence describes the vendor's experience, not the
  product). Four near-misses are recorded in `scratch/ARTIFACTS.md`,
  including "intelligent aggregation," which is not tagged as AI.
- **Zero-claim families.** 8 of 16 taxonomy families tag 0 claims.
  Access control and audit logging enter the Core only as baseline
  substrate, recorded as carried, not claimed. Knowledge base
  articles and satisfaction surveys are named absences — claimed by
  neither sibling, not built, not implied.
- **Derivations, not engines.** Breach state, on-call assignment and
  the public status view are computed at read time from records.
  Automation rules are stored and never executed; a test pins that a
  matching rule changes no state. Alert records are stored and
  triaged; no detection happens here.
- **Privacy.** Requester records hold an opaque caller-supplied
  reference and a label, nothing else — the exact record shape is
  pinned by tests so no identifier field can slip in. Alert sources
  are opaque references too.
- **Tier precision.** The baseline is written fresh for Low/L1.
  Moderate/High apparatus (hash-chained audit, lockout, auditor role)
  is deliberately not inherited downward and not claimed.
- **Deployment.** Single-tenant reference deployment; multi-tenancy
  is a deployment property, not implemented. TLS only when a
  certificate is configured.

## Layout

- `specs/specs.json` — 3 spec sheets with evidence sentences
- `ADDENDUM.md` — the remainder addition (Zendesk): zero claims,
  core-delta decision, gaps
- `UNION-SPEC.md` — the merged spec: ranking, core, baseline,
  contract, gaps
- `src/custsvc/` — errors, access, audit, store, service, `__main__`
- `tests/` — 12 files incl. helpers and the negative control;
  `tests/README.md` carries the coverage map and mutation record
- `scratch/` — extractor, raw descriptions, function counts,
  artifact log, pre-mutation store copy + hash

License: Apache-2.0 (repo-level). Copyright 2026 Aries Hilton.
