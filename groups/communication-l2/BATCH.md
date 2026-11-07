# Final GAPS batch — Group 11, Communication L2

Unit: the 12 OPEN entries of GAPS.md section "Group 11 — Communication
L2 (10 forks)" (inventory idx 113–124), worked under
`gaps-batch/DECISION.md` (ratified 2026-11-07) and
`PLATFORM-LAYER.md`. Extension code: `src/comm/extensions.py`
(`CommExtensions` wrapping `CommStore`); the 5 core modules are
byte-identical (parent-verifiable via `git diff HEAD -- src`).
Tests: `tests/test_gaps_batch.py`; suite 92 → 113, all passing.

Doctrines held: opaque `*_ref` strings only; derived-never-stored
(disposition eligibility, case status, tracking current state,
permit status, survey tallies, payment totals — stored records carry
no derived key, pinned by tests); RBAC through the core `access`
module with denied attempts audited (`:denied`); every mutation
audited with an `ext_` prefix; failed operations consume no ids.

## Per-entry disposition

| idx | Entry | Drafted | Final | What was built |
|---|---|---|---|---|
| 113 | Email security & threat-detection engines | stub | reference | Engine profile records (`reference_stub: True`, `detection_performed: False`) + detection report records with verbatim reported verdicts. No baselining, detonation, or quarantine occurs. |
| 114 | AI/ML models and virtual-assistant intelligence | stub | reference | Assistant profile records (`reference_stub: True`, `inference_here: False`, `generated_text_held: False`) + reported interaction records. No model runs; no generated text is held. |
| 115 | Voice / telephony media, IVR engines, carrier integration | stub | reference | Telephony profile records + session report records carrying `reference_transport: True`, `media_here: False`. No media, no carrier connection. |
| 116 | Video / media transport (0 of 10 claims) | stub | reference | Video profile records with `claimed_by_descriptions: 0` recorded on the record itself; report records `reference_transport: True`, `media_here: False`. The standing absence is preserved, not repaired. |
| 117 | Archiving & eDiscovery engines | build | **reference (re-judged)** | Capture RECORDS (metadata + checksum ref, `content_held: False` — no shape can hold content); retention policy records; legal-hold records (place/release); disposition **DECISION** records with eligibility derived at the seam `_check_disposition_eligible` (retention window elapsed AND no active hold); FOIA production as recorded reported states (`produced_here`/`released_here: False`). See re-judgment grounds below. |
| 118 | Correspondence / casework depth (incl. inter-organization exchange) | build | built | Case records (foia/grants/correspondence/general) with verbatim step records; status derived at read (open / overdue from `suspense_at` / closed; stored record has no status key); inter-organization exchange receipts labeled `reference_transport: True`, `transmitted_here: False`. |
| 119 | Key & certificate lifecycle automation | stub | reference | Certificate metadata records with an exact shape — no parameter can carry key material (`key_material_held: False`, `issued_here: False`; a `key_material=` call raises TypeError, pinned) + lifecycle report records. No CA connection, no issuance, no cryptography (PLATFORM-LAYER decisions 2–3). |
| 120 | End-to-end encrypted message transport and identity proofing | build | built (records form) | Envelope records over core messages (`reference_transport: True`, `transmitted_here: False`, `cryptography_performed: False`; the algorithm is a reported label only) + proofing cases with reported outcomes stored verbatim, `current_outcome` derived at read, `decision_made: False`, `identity_provider: False` (PLATFORM-LAYER decision 1). |
| 121 | Personnel / asset tracking platform | build | built (MDM adjudicated form) | Tracking-service configuration records + tracked-asset records keyed by opaque `asset_ref` (exact shapes pinned) + reported state records; current state derived at read. NO coordinate, address, or geofence-geometry data anywhere: `location_data_held: False` on every record and a recursive key scan pins the absence. |
| 122 | Permits / passes / surveys and payment processing | build | built | Permit applications with decision records and status derived at read; passes issuable only from approved permits; survey instruments (questions are opaque refs) with numeric-only responses and tallies derived at read; payment RECORDS with recorded states, integer cents (floats/bools rejected, no id consumed), `charged_here`/`settled_here: False`, totals derived at read. Nothing is charged or settled. |
| 123 | E-signature execution | stub | reference | Signature-request records with an exact shape (no signature bytes can be held) + reported outcome records (`reported_signed`/`reported_declined`/`reported_expired`), `signed_here: False`. |
| 124 | Workflow / BPM engines and reporting / analytics engines beyond the records substrate | stub | reference | Workflow definition records copied as data (`reference_stub: True`, `executed_here: False`, pinned to change no core record — registry-never-executes) + a deterministic-counts report summary derived over core + extension records (`method: deterministic_counts`; no stored results). |

## Re-judgment — idx 117 (archiving & eDiscovery): build → reference

Grounds (DECISION.md qualification 1; the adjudicated Data
Management L2/L3 precedent): the entry bundles four functions. Two
are honestly buildable in this substrate and were built as records
(capture metadata, legal holds). The other two are execution against
systems this substrate does not hold: **disposition** destroys
records held in content stores (this build holds metadata and
checksums, not content), and its execution belongs to the embedding
organization's records schedule under PLATFORM-LAYER.md decision 4 —
exactly the adjudication both Data Management units recorded.
**FOIA production** assembles and releases records to a requester;
nothing here is produced or released. The honest build is therefore
the decisions-and-reported-states form, every record labeled
`reference_stub: True` / `disposition_executed: False`, and the entry
closes as `reference`, not `built`.

No other entry was re-judged. The tracking entry (121) closes as
built in the MDM unit's adjudicated form, and the encrypted
transport entry (120) closes as built in envelope-records form, per
the unit brief's settled forms.

## Negative control (fresh, mutation-verified)

Seam: `_check_disposition_eligible` in `src/comm/extensions.py` —
a capture under an active legal hold is never disposition-eligible.
Mutation (`if holds_active:` → `if False:`): suite ran 113 tests,
**exactly 3 failures** (the eligibility/hold-gate test, the canonical
hold-blocks test, the direct seam test). Restored from backup;
suite re-ran 113, OK. Recorded in `tests/README.md`.

## Not covered

Nothing outside the 12 entries of this section. The section's
platform-layer paragraph stands on PLATFORM-LAYER.md and was not
absorbed. The "Remainder Addition — Communication L2" section's
marketing-automation entry (idx 657) is a different unit and was not
touched.
