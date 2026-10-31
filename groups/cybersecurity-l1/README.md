# Cybersecurity & Risk Management L1 — merged build (Operation DeadRamp, Phase 2, Group 16)

This is the merged, clean-room implementation of the **Cybersecurity
& Risk Management L1** sibling group: **5 forks** from the FedRAMP
Marketplace that share the same function (Cybersecurity & Risk
Management) and the same trust tier (CMMC L1, equivalent to FedRAMP
Low / LI-SaaS), built as one open-source service per the group's
union spec.

The 5 forks are:

| Fork | FedRAMP impact level |
|---|---|
| Anitian FedFlex | Low |
| Drata Trust Management Platform | Low |
| IntelliGRC | Low |
| MapLarge | Low |
| Valimail Enforce Platform | LI-SaaS |

LI-SaaS is FedRAMP's tailored subset of the Low baseline for SaaS.
The group's union baseline is the Low baseline, taken in full:
**CMMC L1 ⇔ FedRAMP Low / LI-SaaS**, with the baseline written as
**NIST SP 800-53 Rev. 5 Low ⇔ FAR 52.204-21** (the FAR clause whose
basic safeguarding practices define CMMC L1). That baseline claim is
written fresh for this group.

It was written as original code: no vendor code, assets, or branding
from any of the 5 sibling offerings. Python 3, **standard library
only**, no external dependencies.

**Reuse, stated plainly:** the implementation and test suite are the
shipped Group 4 (Cybersecurity & Risk Management L2) build's code,
reused in full — this project's own Apache-2.0 code. Per the tier
rule established by Groups 7 and 10, the baseline claim is written
fresh for L1, but the build reuses Group 4's defensive substrate.
A per-file SHA-256 comparison is recorded in `tests/README.md`:
all 8 `src/` modules are byte-identical to Group 4's, and 14 of 15
test `.py` files are byte-identical (the one differing file,
`tests/cyber_helpers.py`, differs in its module docstring only —
L2 wording changed to L1; no code changed). The copied code was
verified to contain no tier or baseline language, except the
generic "not a CMMC certification" caveat in `catalog.py`, which
stays true at L1. **The baseline claim is not reused.** Everything
Group 4 says about Moderate / NIST SP 800-171 stays in Group 4.

A deliberate scoping note for a security-tools group: this build is
the **defensive platform substrate** the siblings share — the asset
register, the findings those tools produce, their triage, the risk
register, and the control map. It contains **no offensive tooling
and no detection or enforcement engine**: no scanner, no endpoint
agent, no firewall, no phishing simulator. Those engines are the
Extended tail, listed plainly in the honesty section below.

## The 11 core functions

1. **Asset inventory** — a register of assets (name, kind, owner,
   criticality, tags) with provenance (who created it, when). Changing
   an asset's criticality recomputes the scores of its findings.
2. **Finding ingestion** — findings (scanner, posture-engine,
   detection-platform, and test output) enter one at a time, in bulk
   (JSON), or as CSV scan results. A batch is atomic: one bad row
   rejects the whole batch, nothing is partially applied, no ids are
   consumed, and an empty batch is an error.
3. **Finding triage & lifecycle** — findings move through a fixed
   lifecycle (`new → triaged → in_progress → mitigated / accepted`,
   plus `false_positive` and terminal `closed`, per the contract's
   transition map) with assignment. Invalid transitions are rejected
   with a validation error, never silently applied.
4. **Risk scoring** — a deterministic, published score per finding:
   severity weight (critical 5 … info 1) × asset criticality weight
   (critical 2.0 … low 0.5), banded at 8 / 5 / 2.5. Same inputs, same
   score, always. No ML, no hidden model.
5. **Risk register** — standing risks with likelihood × impact
   scoring (1–25, banded at 15 / 10 / 5), an owner, a lifecycle
   (including `closed → open` reopen), and links to the findings
   that evidence them.
6. **Control mapping & assessment** — a built-in catalog of 34
   NIST SP 800-53 Rev. 5 controls; findings link to controls at
   ingest, and each control carries an assessment status and an
   evidence note, so coverage is a query (`coverage_pct`), not a
   spreadsheet.
7. **Search & filtering** — findings filtered by
   severity/status/asset/source and substring, sorted by score;
   assets and risks by substring; one cross-object search over all
   three.
8. **Posture reporting** — a summary: assets by criticality,
   findings by severity and status (every bucket present, zeros
   included), the top 5 open findings by score, risks by band and
   status, and control coverage.
9. **API access** — every function above is exposed over a REST API
   (JSON), so the service composes with anything that speaks HTTP.
10. **Access control** — role-based access hooks: platform roles
    `admin`, `analyst`, `viewer` with a permission matrix enforced
    on every operation.
11. **Audit log** — an append-only audit trail: every asset,
    finding, risk, and control-assessment mutation, every search,
    and every denied attempt is recorded with actor, action, target,
    and UTC timestamp. Optional JSONL file persistence.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id consumed).
Ids are sequential per object type: `asset-`, `find-`, `risk-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m cyber serve --host 127.0.0.1 --port 8000
```

(Also spelled `PYTHONPATH=src python -m cyber serve` where `python`
is Python 3.) Options: `--audit-log PATH` (JSONL audit persistence),
and `--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401). **There is no auditor user at this
tier** — no `dana`, no auditor role.

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, ingest, triage, manage_assets, manage_risks, assess_controls, audit_read, admin |
| `bob`   | analyst | read, ingest, triage, manage_assets, manage_risks, assess_controls |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/assets` | read | List assets (optional `?q=` over name/owner) → `{"assets": [...]}` |
| POST | `/assets` | manage_assets | Body `{"name", "kind", "owner", "criticality", "tags"?}` → 201 asset dict |
| GET | `/assets/{id}` | read | One asset dict |
| POST | `/assets/{id}/update` | manage_assets | Body `{"owner"?, "criticality"?, "tags"?}` → updated asset dict (criticality rescores its findings) |
| GET | `/findings` | read | List findings (`?severity=&status=&asset_id=&source=&q=`), score desc → `{"findings": [...]}` |
| POST | `/findings` | ingest | Body: one finding item → 201 finding dict |
| POST | `/findings/bulk` | ingest | Body `{"findings": [...]}` → 201 `{"findings": [...]}` (atomic) |
| POST | `/findings/csv` | ingest | Body `{"csv": "..."}` → 201 `{"findings": [...]}` (atomic; `control_ids` cell is semicolon-separated) |
| GET | `/findings/{id}` | read | One finding dict |
| POST | `/findings/{id}/transition` | triage | Body `{"status"}` → updated finding dict |
| POST | `/findings/{id}/assign` | triage | Body `{"assignee"}` (or `null` to unassign) → updated finding dict |
| GET | `/risks` | read | List risks (`?status=&q=`), score desc → `{"risks": [...]}` |
| POST | `/risks` | manage_risks | Body `{"title", "description", "likelihood", "impact", "owner"?, "finding_ids"?}` → 201 risk dict |
| GET | `/risks/{id}` | read | One risk dict |
| POST | `/risks/{id}/transition` | manage_risks | Body `{"status"}` → updated risk dict |
| GET | `/controls` | read | The 34-control catalog with assessment state → `{"controls": [...]}` |
| POST | `/controls/{id}/assess` | assess_controls | Body `{"status", "evidence"?}` → updated control dict |
| GET | `/posture` | read | The posture summary dict |
| GET | `/search?q=` | read | `{findings, assets, risks}` substring matches |
| GET | `/audit` | audit_read | `{"entries": [...]}` |

Asset dicts are `{id, name, kind, owner, criticality, tags,
created_by, created_utc, updated_utc}` with sequential ids `asset-1`,
`asset-2`, …; finding and risk dicts follow the same pattern with
their own prefixes.

## How to run tests

Tests live in `tests/` (standard library `unittest`):

```sh
cd groups/cybersecurity-l1
PYTHONPATH=src python3 -m unittest discover -s tests
```

**194 tests, OK** at delivery, including a mutation-verified
negative control on the risk-scoring function (see
`tests/README.md`: the severity-blind constant-3 mutant run in
this tree failed 31 tests, the file was restored byte-identical,
and the suite re-ran green).

## Control-family mapping (summary)

Against the NIST SP 800-53 Rev. 5 **Low** baseline cross-walked to
the FAR 52.204-21 basic safeguarding practices that define CMMC L1:

- **CM / RA** — asset inventory: CM-8 (system component inventory);
  RA-3 (risk assessment — criticality is the scoring input).
- **RA / IR / SI** — finding ingestion & triage: RA-5 (vulnerability
  monitoring and scanning — the register is where scan output lands);
  IR-4 / IR-5 (incident handling / monitoring — the lifecycle is the
  handling record); SI-10 (information input validation — malformed
  batches are rejected whole).
- **RA / CA** — risk scoring & register: RA-3; CA-2 (control
  assessments), CA-5 (plan of action and milestones — the register is
  the POA&M-shaped record).
- **CA** — control mapping & assessment: CA-2, CA-5, CA-7
  (continuous monitoring — assessment status is the monitoring
  record).
- **AC / IA** — access control: AC-2 (account management), AC-3
  (access enforcement), AC-6 (least privilege); IA-2
  (identification & authentication — identity is supplied by the
  embedding organization via user/role headers; this service ships
  hooks, not an IdP).
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit
  information — append-only store, audit-read restricted to the
  `audit_read` permission). **This AU trace is on the FedRAMP Low
  side of the crosswalk only: FAR 52.204-21 contains no audit
  practice, so no audit claim is made on the CMMC / FAR side.**
- **SC** — transmission: SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly and not
  claimed here).

Nothing from the Moderate/High apparatus of the sibling groups is
claimed at this tier (see the honesty section).

## Honesty: what is NOT in this build

This build implements the defensive substrate behind the 11 core
functions above. The product-side engines the siblings sell are
**NOT implemented** — in every case the engine is what is missing;
where an engine's *output* is a finding, that output is ingestible
by the core above:

- No offensive tooling of any kind, and no detection or
  enforcement engines
- AI/ML-powered analytics & anomaly detection — risk scoring here
  is a published deterministic formula, not a model
- Automation & orchestration engines / SOAR
- Detection engines and staffed SOC / managed-response services —
  ingestion, triage, and tracking of their output is Core;
  detecting is not
- Network security enforcement: segmentation, firewall/WAF,
  ZTNA/SSE, browser isolation
- Threat-intelligence feeds, curation, and research
- Backup, recovery & data-protection products
- Full GRC automation suites — control mapping & assessment is
  Core; framework automation, evidence-collection connectors, and
  auditor workflows are not
- Identity, authentication & privileged-access products — the
  build ships access-control hooks, not an IdP
- Endpoint security agents, EDR & XDR platforms
- Phishing simulation & security-awareness training
- Insider-risk, DLP & data-security monitoring engines — their
  alerts arrive in Core as findings
- Application-security testing engines: SAST/DAST/SCA, penetration
  testing — their results are ingested by Core
- Cloud & SaaS posture engines: CSPM/CNAPP/SSPM — their
  misconfiguration findings are ingested by Core
- Log & telemetry pipelines and security data lakes
- Vulnerability scanners — ingestion, consolidation, and tracking
  of scanner output is Core; scanning is not
- Secure enclaves / VDI, identity proofing & fraud prevention, and
  endpoint management / patching agents

Further, plainly:

- **High/Moderate apparatus is deliberately not present and not
  claimed at this tier:** no hash-chained audit, no fail-closed
  audit writes, no logon lockout, and no auditor role (Group 8's
  High-tier `dana`). Verified absent by grep in this tree — the
  audit log here is the plain append-only log, roles are exactly
  `admin`/`analyst`/`viewer`, and demo users are exactly
  alice/bob/carol. See `tests/README.md`.
- **Audit traces to AU on the FedRAMP Low side only.** FAR
  52.204-21 has no audit practice, so no audit claim is made on
  the CMMC side.
- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured; encryption
  at rest is a deployment-layer control, stated plainly, and not
  claimed here. No key-management service is implemented.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not an
  identity provider**. IA-2 stays with the embedding organization:
  production identity, authentication strength, and account
  lifecycle belong to that organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control mapping
  above states which baseline families the build's features answer
  to; nothing more.

## Remainder addition

**Unit `addition:cybersecurity-l1`** (see
[`ADDENDUM.md`](ADDENDUM.md)): **HackerOne / HackerOne Continuous
Security Testing Platform** (`FR1919750997`, LI-SaaS / FedRAMP
Certified, previously uncategorized in the source) is appended as
the group's **6th spec sheet**. Under the group's 25-family
taxonomy applied verbatim it is a **zero-claim fork** — its
three-sentence vulnerability-disclosure / bug-bounty description
produces no raw hit in any family (the word "testing" appears
only in its product name, which is never matched) — so the group
total stays **13 claims**, **5 of 6** forks claim, the union
spec's "no zero-claim forks" floor no longer holds (recorded
plainly in the addendum), and the composition is now Low 4 +
LI-SaaS 2 with the baseline unchanged. Its described function —
a crowdsourced security testing & disclosure coordination
platform — is registered as a new gap in the addendum; no
existing gap gains a claimant. The core is unchanged: `src/` is
byte-identical to the shipped build (all 8 modules
SHA-256-verified), and the suite is now **205 tests, OK**,
including the additions module; the severity-blind scoring drill
was re-run in this tree and failed exactly 32 tests (the shipped
31 plus 1 additions case), with `store.py` restored
byte-identical.
