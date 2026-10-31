# Energy Management — CMMC L1 (DeadRamp Phase 2 remainder singleton)

A clean-room, open-source implementation of the records substrate
for **energy supply procurement**: customer and provider
registries keyed by opaque references, reverse-auction and bid
records with the outcome **derived at read**, price observations,
alert subscriptions and alert records, and advisory engagement
records. It exists because the FedRAMP marketplace contains
exactly **1 offering** in this category at this tier, and DeadRamp
builds the open substrate underneath it.

This is a **brand-new category**: the remainder census proposed
Energy Management for this fork from its own description (energy
procurement via reverse auction for energy supply — a function
none of the 36 Phase 1 categories covers). `forks.json` files the
fork "Uncategorized (none in source)"; its source record carries
an empty business-categories list. The category here is the census
proposal, not a source field — recorded as such in the spec.

## The fork

| Fork | Tier | Status |
|---|---|---|
| **Exchange Platform** — Enel X North America (FR2014363920) | LI-SaaS → CMMC **L1**, SaaS, Public Cloud | FedRAMP Certified |

Full spec sheet, with every function claim carrying its source
sentence as evidence: [`specs/specs.json`](specs/specs.json).
Union contract, claim ranking, control traceability, and gaps:
[`UNION-SPEC.md`](UNION-SPEC.md).

**What the fork's own description supports: 9 claims, one per
family of a 9-family taxonomy defined from its own vocabulary** —
reverse auction conduct, energy provider choice, budgeting
consulting, market intelligence, risk management consulting,
price-change trigger alerts, contract change notifications,
market update notifications, and customer price charts. The
description contains **no demand-response, curtailment,
EV-charging, storage, renewables, metering, billing, or
grid-services vocabulary at all**: the category as this fork's own
words define it is energy supply procurement, and nothing else was
claimed, so nothing else is owed (full absence list in
`scratch/ARTIFACTS.md`).

## The build

The core is the records form of what those claims presuppose,
built at the LI-SaaS/L1 baseline:

- **Customer & provider registries** — opaque `ref` + label only;
  the pinned record shape has no field that could hold a real
  identifier.
- **Auction records** — commodity, region, unit, quantity, and an
  open/close window. Status (`upcoming`/`open`/`closed`) is
  **derived at read**, never stored; an operator may record an
  early close.
- **Bid records** — integer cents per the auction's unit (floats
  and booleans rejected at the boundary), recorded only while the
  auction is open, immutable once recorded.
- **Outcome derivation (signature invariant)** — the winning bid
  is the lowest-priced bid, ties by earliest sequence, computed on
  read from the bid records alone; **no outcome field is ever
  stored**, and the outcome view returns the single winning
  selection plus counts — never a provider ranking or score.
- **Price observations** — the records price charts are drawn
  from; the latest per series is derived at read.
- **Alert subscriptions & alert records** — subscriptions by
  notification kind with optional price thresholds; alerts
  recorded, never delivered (delivery and trigger evaluation are
  Extended).
- **Advisory engagements** — records for the three claimed
  consulting kinds, notes verbatim, open → closed lifecycle (the
  advice itself is Extended).
- **Search & summary** — literal substring search; counts and
  recorded values computed on read, no computed scores anywhere.
- **REST API + CLI**, role-based access (admin / member / viewer),
  and an append-only audit log recording mutations and denied
  attempts.

## Run it

```sh
PYTHONPATH=src python3 -m energy serve --port 8765
# demo users: alice=admin, bob=member, carol=viewer (X-User / X-Role headers)
PYTHONPATH=src python3 -m unittest discover -s tests   # 74 tests
```

Python 3 standard library only; there is nothing to install.

## Control mapping (summary)

Built to the **FedRAMP LI-SaaS / CMMC L1** baseline (NIST SP
800-53 Rev. 5 Low, cross-walked to the FAR 52.204-21 practices):
access enforcement on every operation (AC-2/AC-3), audit of
mutations and denied attempts (AU-2/AU-3, claimed on the FedRAMP
Low side only — FAR 52.204-21 has no audit practice, and AU-6/AU-9
are Moderate selections, not claimed here), integer-price and
input validation at the boundary (SI-10), and all status and
outcomes derived from retained records (CM-6). Full traceability
table in [`UNION-SPEC.md`](UNION-SPEC.md).

## Honesty

- **Nothing here is a FedRAMP authorization or a CMMC
  certification.** FedRAMP authorizes products; CMMC certifies
  organizations. The tier mapping is a planning equivalence. The
  fork's FedRAMP Certified status, and any property of the fork's
  own platform (including its hosting posture), belong to the
  fork and do **not** transfer to this build.
- **This build controls nothing physical.** It holds records
  about energy procurement. It operates no grid, charging,
  building, metering, or market system, and no record in it can
  actuate anything.
- **Extended functions are specified, not implemented** (see
  UNION-SPEC gaps): the live auction execution engine, the
  price-trigger evaluation engine, alert delivery transport, the
  market intelligence engine, the advisory practice itself, chart
  rendering, supply contract lifecycle and settlement, payment
  execution, an identity provider, and energy data integrations.
  The build records subscriptions and alerts; it evaluates no
  triggers and sends nothing.
- **Demo identities are hooks, not an IdP.** `alice` / `bob` /
  `carol` exist so the permission matrix can be exercised; IA-2
  stays with the embedding organization.
- **Prices are records, not money movement.** Bids and
  observations carry integer-cent prices as record fields; no
  payment or settlement occurs in this build.
- Claims in the spec are a **floor**: a function is claimed only
  where the offering's own marketplace description states it,
  with the sentence stored as evidence. Both census citations
  verify verbatim and both happen to be claim-bearing sentences
  for the auction family — recorded as the coincidence direction;
  no citation was load-bearing.
