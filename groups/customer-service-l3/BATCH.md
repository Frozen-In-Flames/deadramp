# Final GAPS batch — Singleton 41, Customer Service L3-adjacent

Unit: the 7 entries in GAPS.md under "Singleton 41 — Customer
Service L3-adjacent (1 fork)" (3 `build-extension`, 4
`stub-engine` in `../../gaps-batch/inventory.json`, idx 408–414).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07). **One entry required re-judgment** (the hosted
third-party application ecosystem, build-extension → reference;
grounds below). The other six fit their drafted dispositions on a
close reading of this group's spec, in the forms stated below.

This singleton's entries are the fork's own platform substance
(a virtualized-environment hosting platform's operations), named
from its prose in `UNION-SPEC.md` — not the Group 26/27 category
union's extended families, which are registered under Groups 26
and 27 and were closed by the Group 27 batch unit
(`../customer-service-l2/BATCH.md`). Where an L2 form carried up
under the Merge Rule unchanged it is named; the new surface
otherwise follows the same records discipline at the High
baseline.

All extension code is in one new module,
`src/custsvc/extensions.py` (`CustsvcExtensions`, wrapping the
core `CustsvcStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified against the pre-work
baseline; `store.py` still `40c4d9c6…`, `audit.py` still
`3d096577…`, the shipped hashes recorded in `tests/README.md`).
Full suite: 126 tests before, **168 tests after, OK** (42 new in
`tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines and the High apparatus:

- RBAC is enforced through the core `custsvc.access` matrix — the
  extension maps each operation onto an existing core action (the
  core action set is fixed; the mapping is documented in the
  module docstring) and checks it before any state change or id
  allocation; denied attempts are recorded on the core audit log
  as `ext_<action>:denied` and every successful mutation as
  `ext_<action>`. The **auditor role is denied every operation on
  this surface, reads included** (its only permission is
  `audit_read`, which no extension operation maps to) — audit
  review stays separable from operations at this tier, and a test
  pins it.
- Audit-before-commit (AU-5): extension mutations are recorded on
  the core's hash-chained audit log; if the audit write raises,
  the record insertion and its id roll back before the error
  propagates (pinned by test for both a reference family and a
  built family). After extension operations the chain still
  verifies (`verify_chain()` → `(True, None)`, pinned by test).
- Privacy discipline (structural): every reference to a system, a
  hosted customer, an asset or an application is an opaque
  `*_ref` string. No parameter on this surface can accept
  conversation content, message text, a transcript, a body or a
  comment — content-shaped arguments raise `TypeError` (pinned),
  and a recursive scan over every extension record and derived
  view finds no content-shaped key. There are no free-text fields
  on this surface at all beyond operator labels (names, framework
  and vendor labels) held as data.
- Nothing is scored, routed, matched or inferred: severity and
  outcome values are caller-reported labels held as data, and the
  recursive scan also pins that no score-shaped key (score,
  rating, sentiment, intent, CSAT) and no float exists on any
  extension record or view.
- Derived values are derived at read and never stored: a
  vulnerability's remediation state (from its recorded event
  stream, at the single seam `_derive_vulnerability_state`), a
  migration project's current phase (from its recorded steps),
  and every summary count. Stored records carry no derived key;
  exact stored key sets are pinned by tests.
- Nothing here executes against an external system, and nothing
  is hosted, operated, monitored, scanned, patched, migrated or
  responded to by this build. The stub-engine families ship as
  labeled reference implementations: every record they create
  carries `reference_stub: True`. The built families are the
  records layer in front of operations that happen elsewhere,
  and their operation-facing records say so on their face
  (`scanned_here` / `applied_here` / `migrated_here`: False).

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `custsvc/extensions.py`) |
|---|---|---|
| Virtualization & cloud hosting platform (IaaS / PaaS / SaaS in one High boundary; the product itself) | reference (stub-engine) | `register_hosting_environment` (`env-`, opaque `environment_ref`, delivery-model label held as data; `hosted_here: False`), `record_environment_report` (`envr-`, platform state stored verbatim as reported; `operated_here: False`) — every record carries `reference_stub: True`; no environment is provisioned or hosted, and no record shape can hold a credential or a network address |
| Authorization acceleration & control inheritance (assessment reuse across hosted customers) | reference (stub-engine) | `record_control_inheritance` (`inh-`, hosted customer by opaque ref; framework label and control labels held as data — registering a record named for a framework asserts no support for it; `assessed_here: False`, `authorized_here: False`), `record_assessment_report` (`asr-`, an assessor's outcome and reported reuse label stored verbatim) — `reference_stub: True` throughout; assessment belongs to assessors and authorization to authorizing officials, neither happens here (PLATFORM-LAYER.md decisions 1 and 6) |
| Continuous monitoring & SOC operations (24/7 SOC) | reference (stub-engine) | `register_monitoring_source` (`mon-`, opaque `source_ref`; `monitors_here: False`), `record_monitoring_observation` (`obs-`, a monitoring system's reported outcome stored verbatim; `detected_here: False`; may reference an existing core alert, and only an existing one) — `reference_stub: True` throughout; a test pins that observation records create no core alert: the core's alert ingest remains the only path by which an alert record comes to exist. A SOC is a staffed operation; what lands here is its reported-observation paper trail |
| Vulnerability management & patching operations | built | `register_vulnerability` (`vuln-`, opaque `asset_ref`/`source_ref`, optional `cve_ref` label held as data with no lookup; `scanned_here: False`; severity is a caller-reported label, never combined or computed), `record_vulnerability_event` (`vulne-`, an append-only event stream — triage / patch_report / verification / risk_acceptance — with (kind, outcome) pairs validated against the recorded vocabulary and outcomes stored verbatim), `vulnerability_view` — remediation state derived at read from the event stream at the single seam `_derive_vulnerability_state` (the batch's fresh negative control), never stored (the stored record's exact key set is pinned: no state key), `create_patch_campaign` (`patch-`, a named record over registered vulnerabilities; `applied_here: False`), `record_patch_report` (`patchr-`, a patching system's reported outcome verbatim; `applied_here: False`), `vulnerability_summary` — counts by severity label and by derived state, derived at read. Scanning and patch application happen in other systems; this is the registry and tracking layer they report into |
| Incident response operations (hosting boundary) | reference (stub-engine) | `record_incident_response` (`inc-`, bound to an existing core case — the response operation's paper trail lives on the case — with an optional link to an existing core alert; `responded_here: False`), `record_response_report` (`incr-`, the responding organization's reported outcome stored verbatim) — `reference_stub: True` throughout; a test pins that recording an incident and its reports leaves the core case view byte-identical: response happens on the hosting boundary, elsewhere |
| Migration & lift-and-shift services (legacy / COTS, hybrid cloud) | built | `create_migration_project` (`mig-`, opaque `system_ref`, source/target environment labels held as data; `migrated_here: False`; the stored record's exact key set is pinned: no phase or status key), `record_migration_step` (`migs-`, steps in the service's workflow shape — assessment / planning / wave_scheduling / cutover / validation / closure — with the migration team's reported outcome stored verbatim; `executed_here: False`: recording a cutover step performs no cutover), `migration_view` — current phase derived at read from the recorded steps at the seam `_derive_migration_phase`, with step count and latest outcome, `migration_summary` — project counts by derived phase. This surface is the tracking registry a migration service reports into; no system is migrated by this build |
| Hosted third-party application ecosystem (each catalogue application is its own vendor's product) | reference — **re-judged** from build-extension | `register_hosted_application` (`app-`, opaque `app_ref`, vendor and category labels held as data; `hosted_here: False`, `operated_here: False`), `record_hosting_report` (`appr-`, a hosting platform's reported state stored verbatim) — `reference_stub: True` throughout; no application is hosted, run or operated here, and each remains its vendor's product |

## Re-judgment (DECISION.md qualification 1)

**Hosted third-party application ecosystem** — drafted
`build-extension`, closed `reference`. Grounds, on a close
reading of the owning group's spec:

1. The entry's own parenthetical bounds it: each catalogue
   application is its own vendor's product. `UNION-SPEC.md` says
   the same in its gap list — the ecosystem's applications are
   "each its own vendor's product belonging to its own category's
   build". There is no function of this group to build: the
   deliverable named is the hosting of other builds' products.
2. `PLATFORM-LAYER.md` decision 6 (hosting substrate and platform
   umbrella): hosting surfaces are deployment properties unless a
   group's own spec claims a records function for them. This
   group's spec claims no records function for the ecosystem; it
   names it platform substance, the umbrella over the catalogue.
3. The form that honestly remains — declaration records of
   applications hosted elsewhere, plus verbatim hosting reports —
   is the form the Group 27 batch unit closed as `reference` for
   the commerce sibling's hosted platform (registration + reported
   state). Same form, same token.

Nothing is lost by the re-judgment: the registration and report
surface exists, is RBAC- and audit-bound, and is fully tested;
only the closure token differs from the draft.

## Long-tail enumeration

Against `UNION-SPEC.md`'s gap list — this singleton's own platform
substance, item for item:

| Spec gap | Where it lands |
|---|---|
| Virtualization & cloud hosting (the product itself) | The hosting-environment entry |
| Authorization acceleration & control inheritance | The inheritance entry |
| Continuous monitoring & SOC operations | The monitoring entry |
| Vulnerability management & patching | The vulnerability entry |
| Incident response operations | The incident entry |
| Migration & lift-and-shift services | The migration entry |
| Hosted third-party application ecosystem | The ecosystem entry |

The Group 26/27 category union's extended families (event
detection & orchestration engines, automation execution engines,
GRC platform, real-time channels, AI assistance, SLA policy
engine, notification delivery, reporting / analytics engines) are
registered under the Group 26 and Group 27 sections of GAPS.md,
not re-registered here, and are **not covered by this unit** —
they were closed by the Group 27 batch unit at the Moderate tier
in the forms its BATCH.md records; the Merge Rule carries those
forms up, and this unit adds no second surface for them.

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Operations themselves**, in every family that names one: no
  environment is hosted, no control is assessed, nothing is
  monitored, scanned, patched or migrated, and no incident is
  responded to. The batch closes the records layer in front of
  those operations; the operations remain other systems' and
  other organizations' work, and the records say so on their face
  (`*_here: False`).
- **The section's baseline and platform-layer prose** (MFA /
  authenticator management IA-2(1)/(2), IA-5; FIPS-validated
  cryptography SC-13; encryption at rest SC-28; audit retention
  enforcement AU-11; session lock / termination AC-11/AC-12;
  multi-tenancy) — not among the 7 entries; they stand on
  `PLATFORM-LAYER.md`, and no entry in this unit absorbs them.
- **The remainder addition's two registered entries** (survey &
  feedback-collection engine, idx 663; platform connectors &
  integration API surface, idx 664, from the Medallia addition's
  claims) — registered under their own remainder-addition section
  of GAPS.md, not this unit's section, and not covered here.
- **Knowledge base articles and satisfaction / CSAT surveys** —
  named absences at every tier of this category in this
  singleton's section (the Medallia addition retired the survey
  absence at this tier with a claim; its engine entry is idx 663
  above, in its own section).

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
