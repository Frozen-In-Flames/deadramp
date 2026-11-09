# Final GAPS batch — third unit: No-Signal Addition — Learning Management L2

Unit: the 1 OPEN entry in GAPS.md under the exact section header
**`## No-Signal Addition — Learning Management L2 (Skillsoft Private Cloud, F1207261443)`**
(idx 971 in `../../gaps-batch/inventory.json`). Entry count
verified against both sources: GAPS.md lists exactly 1
`- [ ] open` entry in this section and the inventory assigns
exactly idx 971 to it — **no discrepancy**. The section holds no
pre-closed entries. Disposition per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07): the entry
was drafted **stub-engine** and closes **reference** exactly as
drafted — **no re-judgment**.

This is the THIRD batch unit in this group directory: the first
unit (the founding Singleton 48 section) shipped in
`src/lms/extensions.py` and the second (the Remainder Addition
section) in `src/lms/extensions_addition.py`. The tree was
verified before building and matches that description. All
extension code here is in one new module,
`src/lms/extensions_nosignal.py` (`LmsExtensionsNoSignal`,
wrapping the core `LmsStore`, audit prefix `extn_`). Every
existing module — the 7 core modules, the first batch unit's
`extensions.py` (`833ca1c9…`), and the second batch unit's
`extensions_addition.py` (`daaa1554…`) — is byte-identical to
its pre-build state (SHA-256 verified against the pre-work
baseline in `scratch/prebatch-nosignal-src.sha256`; `store.py`
still hashes to the shipped `820d9712…`). No core extension was
needed. Full suite: 185 tests before, **201 tests after, OK**,
including the fresh mutation-verified negative control recorded
in `tests/README.md`.

**No-signal discipline.** This fork (Skillsoft / Private Cloud,
F1207261443, FedRAMP Moderate / Certified, SaaS) sat in the
remainder census's no-signal set: its cached marketplace
description is a 339-character company profile of Skillsoft
only, and the census recorded no citations and a `no_signal`
flag. Its category was resolved afterwards from the vendor's
own public pages — Skillsoft's Percipio platform documentation,
the platform this Private Cloud offering delivers — with the
caveat recorded at exactly its strength in ADDENDUM.md sections
7–9 (no Private Cloud-specific sentence exists on the official
pages checked; the group's remainder-addition fork *is*
Percipio under a different offering record, and both records
stand). The fork claims **zero families** under the group's
taxonomy applied verbatim; the surface below is built ONLY from
what the section's registered entry and the addendum's gap note
(§9) name — a vendor-operated dedicated/private-cloud
deployment of the learning platform — nothing inferred from the
vendor's reputation.

## Per-entry disposition

### idx 971 — reference (stub-engine, as drafted)

> Private-cloud hosting & managed delivery service (a vendor-operated dedicated deployment of the learning platform; the offering's entire classified function, registered from the classified function, not from a claim)

The entry names the hosting *service* itself: a vendor-operated
dedicated deployment of the learning platform. Hosting and
managed delivery are deployment-layer acts performed by the
vendor's platform; this substrate is a single-tenant reference
deployment that an embedding organization runs — it operates no
hosting service, provisions no cloud, hosts no platform, and
delivers no learning (ADDENDUM.md §8 draws exactly this line:
the vendor-operated private-cloud hosting & managed delivery
itself presupposes no records form in Core and is booked as a
Gap). Building a hosting or delivery engine here would be a
fake engine. What ships is the labeled reference form, in the
house pattern for a hosted service:

- `create_hosting_deployment` (`hst-`, Action: catalog_write) —
  a record ABOUT one vendor-operated deployment: title,
  `deployment_kind` from the offering's own kinds
  (`private_cloud`, `dedicated_private_cloud`), and the
  operating vendor and the delivered platform named by opaque
  `provider_ref` / `platform_ref`. An optional binding to a
  core course is **by id only** and must resolve (the hosted
  platform's catalogue records are Core 2 records; the binding
  is a cross-reference, never a copy). Every record carries
  `reference_stub: True`, `reference_transport: True`, state
  `recorded_reference_only`, and `hosted_here` /
  `provisioned_here` / `managed_here` / `delivered_here` /
  `content_held: False` on its face; the stored record's exact
  key set is pinned by test. A full no-signal flow is pinned to
  leave the bound core course record **byte-identical**.
- `record_delivery_report` (`dlr-`, Action: catalog_write) — a
  managed delivery report held **verbatim**: the delivered
  platform's access channels (`web_browser`, `mobile_app`,
  `hosted_platform`), the outcome label stored exactly as
  reported (`outcome_basis: vendor_reported`), and an optional
  `reported_learner_count` held exactly as reported
  (non-negative integers only; bools, floats, negatives, and
  numeric strings are rejected with no id consumed).
  `transmitted_here: False` — nothing is fetched, checked,
  hosted, or delivered here.
- Derived views: `deployment_view` adds `delivery_report_count`
  and `latest_outcome_label` derived at read from the recorded
  reports via the `_latest_outcome_label` seam (the stored
  record carries neither key, pinned); `hosting_summary`
  (Action: report_read) is deterministic counts over the
  recorded reference records only (`counts_basis:
  recorded_reference_records_only`) — no hosting capacity,
  usage, uptime, or learner figure is computed or claimed.

This surface is distinct from the surfaces the prior units
built, and the distinction is the addendum's own: the first
unit closed the delivery *runtime* as session records over core
progress, and the second unit closed the licensed content
*library* as catalogue records; this entry is neither — it is
the hosting service the platform runs on, which is why it ships
labeled while its neighbours' records forms stand in the
substrate. The already-registered learning delivery engine gap
gains substance from this fork through its classification
citation (ADDENDUM.md §9) — noted in the addendum, not
re-registered, and not part of this unit; the licensed content
library and identity gaps explicitly gain no claimant from this
fork and are not touched here.

Cross-cutting, per the group's doctrines: the founding
**no-score invariant binds the no-signal surface exactly as it
binds the core** — a recursive key scan over every no-signal
record, view, list, and the summary finds no `score` /
`score_*` / `*_score` / grade-shaped key, and no content-,
body-, payload-, URL-, password-, or credential-shaped key
(pinned in `test_gaps_batch_nosignal.TestCrossCutting`); no
public method accepts `**kwargs` (signature scan, pinned), so
no content or credential argument can be smuggled in (a
`content=` or `password=` call raises TypeError, pinned); no
float value appears anywhere on the surface (pinned); no
provision- or execute-shaped method exists on the surface
(pinned); all parties are opaque `*_ref` strings; RBAC reuses
the core permission actions (catalog for deployments/reports,
report for the summary) with the core's matrix applied as
shipped — at this tier `catalog_write` is admin-only, so the
write surface is admin-operated, the same note the prior units
recorded for their tier; denied writes consume no id (pinned);
every successful mutation is recorded on the core audit log
with an `extn_`-prefixed action.

**Fresh mutation-verified negative control:** the
`_latest_outcome_label` seam in `extensions_nosignal.py` —
patching its return to read the FIRST recorded report
(`reports[0]` instead of `reports[-1]`, occurrence count
asserted = 1 before patching) made exactly **4** of 201 tests
fail, all in the new module (the delivery view-derivation test,
the summary test, and the control's canonical and seam-direct
legs), with all 185 pre-existing tests still passing. The
module was restored from
`scratch/extensions_nosignal.py.premutation` and verified
SHA-256-identical (`8c2ac492…`); the suite re-ran green. Full
record in `tests/README.md`; raw output in
`scratch/gaps_batch_nosignal_mutation_run.txt`.

Left unresolved: nothing in this unit. HTTP exposure of the
no-signal surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
