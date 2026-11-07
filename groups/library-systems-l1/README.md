# Library Systems — CMMC L1 (DeadRamp Phase 2, no-signal new sibling group)

A clean-room, open-source records substrate for the **Library
Systems** category at CMMC tier **L1** (FedRAMP Low / LI-SaaS):
catalogue, holdings, and circulation records, integration and
workflow registries, reporting, and search. Records only — no
engines. Python standard library only.

## The group

A **new category**, founded from the no-signal resolution. The
remainder census held both forks unclassified — their marketplace
descriptions never state the library function in a citable
sentence — while flagging them as probable library systems. The
live-docs research pass confirmed the hypothesis on the vendors'
own words, and this group is the build that followed.

| Fork | Vendor | Product | Impact |
|---|---|---|---|
| F1305132147 | Ex Libris | Higher-Ed Platform (Alma, Primo, Leganto, Esploro) | LI-SaaS |
| FR1818459251 | Sirsi Corporation (SirsiDynix) | EOS.Web | Low |

Both are FedRAMP Certified SaaS offerings; both map to L1 per the
crosswalk (Low and LI-SaaS share the Low-baseline family). Full
spec: [`UNION-SPEC.md`](UNION-SPEC.md). Per-fork sheets:
[`specs/specs.json`](specs/specs.json).

## Taxonomy

A fresh 10-family taxonomy derived from the forks' own words in
**both** derivation sources — their cached marketplace descriptions
and their classification sentences from the vendors' live pages —
with per-family sources recorded in the UNION-SPEC. Claims fire
only on the cached descriptions: **6 claims total** (Ex Libris 2:
platform services, integration; SirsiDynix 4: library management,
integration, library automation, accessibility). The five
classification-only families (discovery & delivery, digital
preservation, course resource lists, research activities,
knowledge management) carry zero claims and stand as named gaps.

## Core functions (10)

1. Library registry & membership
2. Catalogue item records
3. Holdings records (derived `available_copies`, never stored)
4. Loan records (availability seam; derived `overdue`)
5. Hold records (derived `queue_position`)
6. Integration registry (records only, never transports)
7. Workflow registry (records only, never executes)
8. Registry reporting (counts only, no scores)
9. Registry search (membership-scoped)
10. Access control & audit (append-only, denied attempts recorded)

## How to run

```sh
PYTHONPATH=src python3 -m librarysys serve --host 127.0.0.1 --port 8821
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 tests/smoke.py
```

Demo users: `alice` (admin), `bob` (member), `carol` (viewer),
sent as `X-User` / `X-Role` headers. Demo identities are hooks,
not an IdP — production identity is the embedding organization's.

## Control traceability (summary)

CMMC L1 ⇔ FedRAMP Low / LI-SaaS; NIST SP 800-53 Rev. 5 Low
baseline, cross-walked to the 17 FAR 52.204-21 practices. Access
control → AC, IA; audit → AU; validation, guards, and the
availability seam → SI, SC. Full mapping and the standing caveat
(FedRAMP authorizes products, CMMC certifies organizations; the
tier is a planning/matching equivalence, never a credential claim)
are in the UNION-SPEC. No documented control claims are drawn from
the forks' descriptions: their security and compliance sentences
are posture prose, and none is converted into a claim.

## Honesty

- **The classification-vs-claims evidence split is the group's
  founding discipline.** The vendors' live sentences classified
  these forks into Library Systems; they are pinned on every sheet
  as `classification_evidence` / `classification_source_url`,
  test-pinned against `remainder/nosignal_report.json`, and
  test-pinned as **not** occurring in the cached descriptions.
  Claims come only from the cached descriptions, each with its
  source sentence. The two streams never mix.
- **Zero-claim forks: none** — but five of ten families are
  zero-claim across the whole group, and they are gaps, not
  functions.
- **Catalogue, holdings, and circulation records are the
  core-boundary decision**, stated once in the UNION-SPEC: neither
  description contains catalogue or circulation vocabulary; the
  records are the machinery the single integrated-library-system
  claim presupposes.
- **Extended functions, by name:** discovery & delivery service,
  digital preservation system, course resource list management,
  research activities platform, knowledge management system,
  accessible delivery & rendering, automation engine, integration
  transport, identity provider. None is implemented; all are
  registered for the GAPS.md final batch.
- **No money shape exists anywhere in the build** (no description
  grounds one), patrons are opaque references only, and no record
  can hold a real name or contact detail.
- The negative control is mutation-verified: patching the
  availability seam makes exactly 2 tests fail (see
  `tests/README.md`); the restored store is SHA-256-verified
  byte-identical and the suite is green (47 tests).

## Final GAPS batch note

`src/librarysys/extensions.py` adds records surfaces for the
group's Extended functions (per-entry dispositions in
`BATCH.md`): discovery queries as digests + result references
(built), preservation metadata + fixity reports (built), course
resource lists over core items (built), knowledge records linked
to core items (built), and labeled reference records for the
research activities platform, accessible delivery & rendering
(re-judged: delivery/rendering is a delivery layer, not records),
the automation engine, and integration transport — nothing here
executes, renders, delivers, connects, or transmits. Suite: 66
tests, including a fresh mutation-verified negative control on
the course-list entry guard (exactly 1 failure under the mutant).
