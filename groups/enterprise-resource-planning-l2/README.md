# Enterprise Resource Planning — CMMC L2 (DeadRamp Phase 2 remainder singleton)

A clean-room, open-source implementation of the records
substrate for an **integrated enterprise application suite**:
organization and application registries keyed by opaque
references; general-ledger records under a **balanced-entry
rule**; procurement, expense, person, time, absence, payroll,
asset, work-order, inventory, and document records; and
integration, workflow, and access-configuration registries that
record and **never execute**. It exists because the FedRAMP
marketplace contains exactly **1 offering** in this category at
this tier, and DeadRamp builds the open substrate underneath it.

This is a **brand-new category**, founded by the no-signal
resolution: no shipped group exists for Enterprise Resource
Planning at any tier. The fork sat in the remainder census's
no-signal set — its marketplace description states no single
primary function the census could cite — and the live-docs
research pass resolved it here on the vendor's own suite-level
sentence ("Infor Government Solutions offers a comprehensive
suite of 20+ fully integrated business applications.",
infor.com). `forks.json` files the fork "Uncategorized (none in
source)"; its source record carries an empty business-categories
list. The suite-level framing is the vendor's own, stated
plainly in the union spec: the suite's components span the
ground of the Finance, Human Resources, and Operations
Management categories, and the fork is **not** split across
them — the vendor frames one integrated offering, and the census
classifier recorded no single primary function.

## The fork

| Fork | Tier | Status |
|---|---|---|
| **Infor Government Solutions (IGS) Software as a Service** — Infor (FR1710033970) | Moderate → CMMC **L2**, SaaS, Government Community Cloud | FedRAMP Certified |

Full spec sheet, with every function claim carrying its source
sentence as evidence, plus the classification citation recorded
as its own fields: [`specs/specs.json`](specs/specs.json).
Union contract, claim ranking, control traceability, and gaps:
[`UNION-SPEC.md`](UNION-SPEC.md).

**What the fork's own description supports: 24 claims, one per
family of a 24-family taxonomy defined from its own words** —
an integrated application suite; federated security & single
sign-on; role-based access; an enterprise portal; configurable
homepages; integration & process orchestration; an API gateway;
document management; a data lake; financial management; supply
management; expense management; manufacturing ERP; a supplier
exchange; human capital management; core HR; talent management;
workforce management; payroll; asset management; maintenance
management; business intelligence; enterprise performance
management; and governance, risk & compliance. The description
never says **"enterprise resource planning"** in full, and
contains **no CRM, sales-order, tax, budgeting, grants,
training, or scoring vocabulary, and no stated amount, rate, or
fee** — the category rests on the suite framing, and the money
records below carry caller-recorded values (full absence list
in `scratch/ARTIFACTS.md`).

## The build

The core is the records form of what those claims presuppose,
built at the Moderate/L2 baseline:

- **Organization & application registries** — opaque `ref` +
  label only; the suite's applications registered per
  organization. Registering one installs nothing and runs
  nothing.
- **Access configuration records** — the identity provider and
  MFA arrangement the suite federates with, named by label.
  Records only: identity itself stays with the embedding
  organization (IA-2).
- **General ledger records (signature invariant)** — debit/
  credit lines in **integer cents**; an entry records only when
  it **balances** through the single seam
  `_check_entry_balanced` (every line one-sided, debits equal
  credits, total positive). Unbalanced entries are refused
  whole — no record, no id consumed.
- **Procurement & expense records** — purchase orders and
  expense reports whose **totals are derived at read** from
  their lines and never stored; lifecycles change only through
  recorded actions and outcomes.
- **Person, time, absence & payroll records** — the person
  system of record holds an opaque reference and two labels:
  the pinned shape has **no field that could hold a name or any
  real identifier**. Payroll runs record a caller-stated gross
  amount; no pay calculation is performed.
- **Asset, work-order & inventory records** — caller-stated
  criticality labels (never computed), work orders in the
  fork's own preventive/corrective vocabulary, integer
  quantities that can never go negative.
- **Document records** — metadata only; the pinned shape has
  **no field that could hold content**.
- **Integration & workflow registries** — records of the
  integration platform, the API gateway, and business-process
  workflows. The registries **never execute**: there is no run,
  fire, execute, or connect operation anywhere in the build,
  pinned by test.
- **Search & summary** — literal substring search over record
  metadata; counts and recorded values computed on read, no
  computed scores anywhere.
- **REST API + CLI**, role-based access (admin / operator /
  viewer), and an append-only audit log recording mutations and
  denied attempts.

## Run it

```sh
PYTHONPATH=src python3 -m erp serve --port 8765
# demo users: alice=admin, bob=operator, carol=viewer (X-User / X-Role headers)
PYTHONPATH=src python3 -m unittest discover -s tests   # 118 tests
```

Python 3 standard library only; there is nothing to install.

## Control mapping (summary)

Built to the **FedRAMP Moderate / CMMC L2** baseline (NIST SP
800-53 Rev. 5 Moderate, cross-walked to the NIST SP 800-171
practices): access enforcement on every operation (AC-2/AC-3/
AC-6), audit of mutations and denied attempts (AU-2/AU-3/AU-6/
AU-9 — append-only, with audit reads restricted to the
admin-only `audit_read` permission), input validation at the
boundary (SI-10), and every derived value computed from retained
records through a single seam (CM-6). **No SC-13 claim is made**
and no IA-2 satisfaction is claimed: the fork's federation and
hosting posture are its own platform properties. Full
traceability table and precision notes in
[`UNION-SPEC.md`](UNION-SPEC.md).

## Honesty

- **Nothing here is a FedRAMP authorization or a CMMC
  certification.** FedRAMP authorizes products; CMMC certifies
  organizations. The tier mapping is a planning equivalence. The
  fork's FedRAMP Certified status, and any property of the
  fork's own platform — including its GovCloud hosting, its
  ITAR/CJIS/HIPAA posture, and its federation service — belong
  to the fork and do **not** transfer to this build.
- **The classification and the claims run on different
  evidence, and the streams never mix.** The category rests on
  the vendor's brochure sentence (recorded on the sheet as
  classification fields, at brochure weight — its "20+"
  application count is not verified against the description).
  Every claim rests on the fork's own marketplace description,
  sentence by sentence. The census recorded zero citations for
  this fork; nothing was load-bearing.
- **This build stores records, not business data.** Ledger,
  order, expense, and payroll amounts are caller-recorded
  integer cents in a reference substrate; person records hold
  opaque references and labels only; document records hold
  metadata only. No engine the fork names — orchestration,
  gateways, close, production, scheduling, pay calculation, BI,
  planning, GRC — is implemented here; each is a named gap.
- **Extended functions are specified, not implemented** (see
  UNION-SPEC gaps): the portal/presentation layer, the
  federation service, the integration and gateway runtimes, the
  data lake engine, the close and source-to-settle engines,
  expense enforcement and fraud detection, the production
  engine, the supplier exchange network, the talent engine, the
  scheduling optimizer, the payroll calculation engine, the BI
  platform, the performance-management engine, and the GRC
  engine.
- **Demo identities are hooks, not an IdP.** `alice` / `bob` /
  `carol` exist so the permission matrix can be exercised; IA-2
  stays with the embedding organization.
- Claims in the spec are a **floor**: a function is claimed
  only where the offering's own marketplace description states
  it, with the sentence stored as evidence.

## Final GAPS batch (2026-11-07)

The 16 open GAPS.md entries for this group are closed by the
batch in `src/erp/extensions.py` (`ErpExtensions`, a wrapper
around the core store; every core module is byte-identical to
its pre-batch state). See `BATCH.md` for the per-entry
disposition. In short: the portal presentation layer, data
lake, close & consolidation, source-to-settle, production,
supplier exchange, talent, scheduling, payroll calculation,
business intelligence, performance management, and GRC entries
are built as in-substrate records plus deterministic
derivations over this build's own records (payment instructions
capped by a guard seam at the purchase order's derived total;
payroll gross/net, close balances, plan variance, and risk
exposure all derived at read and never stored; the scheduling
surface computes deterministic coverage and claims no
optimization), and the federation service, the orchestration
runtime, the API gateway runtime, and the expense policy /
fraud detection entry ship as labeled reference
implementations (`reference_stub: True` on every record;
federation records also carry `hook_only: True` — this
substrate is never an IdP, routes nothing, executes nothing,
and determines no fraud; expense-policy findings state
recorded limit breaches only). The section's 17th entry, the
platform-layer entry, was already closed as re-scoped under
the repo's PLATFORM-LAYER.md and is untouched here. Full suite
after the batch: **118 tests, OK**, including a fresh
mutation-verified negative control on the settlement guard
(exactly 1 failure under the mutant; drill record in
`tests/README.md`).
