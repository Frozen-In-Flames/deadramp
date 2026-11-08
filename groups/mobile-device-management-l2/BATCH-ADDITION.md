# Final GAPS batch — second unit: Remainder Addition — Mobile Device Management (MDM) L2

Unit: the open entries of the GAPS.md section
**`## Remainder Addition — Mobile Device Management (MDM) L2 (+1 fork)`**
(the +1 fork is Ivanti Neurons for MDM (Formerly MobileIron),
F1507116930, added to this group by the remainder census; its
spec sheet's `ADDENDUM.md` §5 registered these gaps).
Dispositions follow `../../gaps-batch/DECISION.md`;
platform-layer closures follow `../../PLATFORM-LAYER.md`.

**Entry count — no discrepancy.** The build brief described 2
OPEN entries; GAPS.md's section lists exactly 2 `- [ ] open`
entries, and `gaps-batch/inventory.json` assigns exactly idx
679–680 to this section (679 build-extension, 680
stub-engine). This unit built and closes those 2.

Everything landed as ONE new module,
`src/mdm/extensions_addition.py` (`MdmExtensionsAddition`,
wrapping the core `MdmStore`), with audit actions prefixed
`exta_` (the second-unit convention; the first unit's are
`ext_`). All 8 pre-existing `src/mdm/` modules — the 7 core
modules plus the first batch unit's `extensions.py`
(`5407a60f…`) — are byte-identical to the pre-build state
(SHA-256 verified against `scratch/prebatch-addition-src.sha256`;
`store.py` still `8c0c787a…`). No core extension was needed,
and none was made: the addition fork claims zero taxonomy
families (ADDENDUM §2), so per the core-delta decision recorded
in ADDENDUM §3 these entries are Extended-surface records work,
not claim-driven core work. Tests:
`tests/test_gaps_batch_addition.py`. Suite: **132 → 157**, all
passing, including the unit's fresh mutation-verified negative
control recorded in `tests/README.md`.

**The founding constraint, carried into both entries.** The
ADDENDUM §3 boundary condition binds this unit exactly as it
bound the first: devices are held by **opaque caller-supplied
`device_ref` strings only** — no record shape in the new module
has a field that could hold an IMEI, serial, phone number, MAC
address, or any location data. That invariant is pinned by a
recursive key scan over every stored addition record in
`tests/test_gaps_batch_addition.py`, using the first unit's
`FORBIDDEN_KEYS` set verbatim (imported, not re-typed). No
money moves on this surface, so no amount field exists in it.

## Per-entry disposition

### idx 679 — built (build-extension, as drafted)

> Zero-trust access validation engine: device validation, identity / context / privacy evaluation, and per-request access-level decisions (the fork describes a validation plane, not records)

Built in records form, and the entry's own parenthetical is
the ground for the form, stated plainly: the fork describes a
validation *plane*, and a records substrate does not evaluate
requests. What is built is the decision-record layer, in the
first unit's adjudicated forms — the device-command plane
(idx 481: a request, a confirmation seam, an outcome recorded
as reported, `executed_here: False` throughout) and the
compliance records (idx 482: results as reported, state
derived at read, nothing enforced):

- **Validation profiles** (`zvp-`) — definitions as data: a
  per-organization-unique `profile_ref`, a name, the declared
  evaluation dimensions validated against the entry's own
  vocabulary (`device` / `identity` / `context` / `privacy`,
  no repeats), and the access-level labels the plane may
  report. `evaluated_here: False`, `decided_here: False` on
  every profile.
- **Validation decision records** (`zvd-`) — one validation
  outcome as reported by the external plane: the device and
  the subject as opaque references only (`device_ref`,
  `subject_ref` — IA-2 and all identity data stay with the
  embedding organization, PLATFORM-LAYER decision 1; there is
  no identity field of any kind), dimension results validated
  against the profile's declared dimensions with `pass` /
  `fail` labels, and the plane's access-level decision label
  recorded **verbatim**, validated against the profile's
  declared levels. `validated_here: False`,
  `decided_here: False` on every record: recording a decision
  grants and denies nothing here.
- **`access_view`** — derives one device's current reported
  access level at read from the latest recorded decision for
  that profile and device (no decisions reads `unreported`
  with a null level), with the decision count and latest
  decision id; `method: derived_from_recorded_decisions`,
  `derived: True`, `stored: False`. The seam behind it
  (`_current_decision`) is the unit's fresh negative control.

This is not a re-judgment: the drafted build-extension
disposition stands, and the records form is the same judgment
the first unit recorded for idx 481 — a build that claimed to
validate devices per request would be a fake validation plane;
the decision *records* such a plane produces are what a
records substrate honestly ships. Had the entry required this
build to evaluate a live request, it would have been
re-judged to reference.

### idx 680 — reference (stub-engine, as drafted)

> Mobile threat defense engine: continual detection and remediation of device, network, and app-level threats including zero-day, on and off connectivity, with silent deployment

Labeled reference implementation, per the drafted disposition
and the house precedent for engines over external systems
(this group's first unit: workflow execution, carrier
integration, alert delivery, enrollment). Continual detection
and remediation happen *on devices*, by an engine this build
does not contain; what lands is the records surface that
engine's activity leaves:

- **Threat deployment records** (`mtd-`) — a device (opaque
  `device_ref` only) and the reported deployment mode,
  `silent` or `announced` (`silent` is the fork's own word
  for its activation). Every record carries
  `reference_stub: True`, status `recorded_reference_only`,
  and `deployed_here: False`: nothing is deployed to any
  device here.
- **Threat event records** (`mte-`) — one detection and its
  remediation, as reported: scope from the fork's own three
  (`device` / `network` / `app`), a threat label verbatim,
  the connectivity label (`on_connectivity` /
  `off_connectivity` — the entry's "on and off
  connectivity"), and the reported remediation label. The
  device reference is taken **from the deployment record**,
  never supplied separately, so an event cannot name a device
  its deployment does not. Every record carries
  `reference_stub: True`, `detected_here: False`, and
  `remediated_here: False`.
- **`threat_summary`** — counts of deployments and reported
  events, by scope and by reported remediation, derived at
  read over the module's own records and stored nowhere; the
  summary itself carries `reference_stub: True`, because it
  summarizes reference records.

Pinned by test: creating deployment and event records leaves
the core organization summary deep-equal before and after —
the reference surface changes no core record.

## Re-judgments

None. Both entries closed at their drafted dispositions; the
build form for idx 679 is stated above with its grounds, in
the first unit's own precedent, rather than smoothed over.

## Unresolved

Nothing within the unit. Expected parent ship arithmetic: 2
entries closed (**1 `built` (idx 679), 1 `reference`
(idx 680)**), exactly the drafted split — no token overrides
needed.
