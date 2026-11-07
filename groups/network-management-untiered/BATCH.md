# Final GAPS batch — Untiered Set 19, Network Management (2 forks, tier null)

Unit: the 8 open entries in GAPS.md under "Untiered Set 19 —
Network Management (2 forks, tier null)" (idx 921–928 in
`../../gaps-batch/inventory.json`; 5 `build-extension`,
3 `stub-engine`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **Two
entries are re-judged** under qualification 1 (idx 923 and
idx 926, build-extension → reference), grounds below. The
section's ninth entry, idx 929 "Platform layer", was already
closed `re-scoped` under `../../PLATFORM-LAYER.md` before this
unit and is not part of it.

All extension code is in one new module,
`src/netmgmt/extensions.py` (`NetmgmtExtensions`, wrapping the
core `NetmgmtStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified against
the accounting in this group's README; `store.py` still
`5b1e861c…`). Full suite: 83 tests before, **124 tests after,
OK** (41 new in `tests/test_gaps_batch.py`), including the
fresh mutation-verified negative control recorded in
`tests/README.md`. Store-level surface only; no HTTP routes
were added, matching the sibling batch units' pattern.

**Tier discipline binds the extension surface exactly as it
binds the core.** No record or view asserts or carries a tier,
a baseline, or an equivalence: a test scans every extension
record and derived view recursively for tier/baseline/
equivalence/score/coordinate/identifier-shaped field names,
floats, and numeric lists. The forks' documented control
claims remain where `UNION-SPEC.md` put them — the forks'
claims about themselves, recorded in the spec.

Cross-cutting, per the substrate's doctrines: RBAC and
organization membership are enforced through the core
`netmgmt.access` matrix and the core store before any state
change or id allocation; denied attempts are recorded on the
core audit log as `ext_<action>:denied` and every successful
mutation as `ext_<action>`; failed operations consume no id
and change nothing. Every party, asset, and output is an
opaque `*_ref` string or a core record id. No record shape
can hold a credential, certificate material, packet content,
or a geographic coordinate — for each such shape there is no
parameter that could accept one, pinned by TypeError tests.
Lifecycle states (certificate, guest window, incident,
terminal, GPU job) are derived at read from the recorded
event/outcome streams and never stored; the stored incident
record carries no state key at all, pinned by exact key set.
Outcomes, severities, and states reported by callers are
stored verbatim as reports — counts describing an external
engine's work are never computed here, and summaries are
counts only.

## Per-entry dispositions

| Entry (GAPS.md text, verbatim) | Disposition | Built (module: `netmgmt/extensions.py`) |
|---|---|---|
| Network access authentication / RADIUS & 802.1X engine | built (build-extension, as drafted) | `record_auth_event` (`aev-`, method enum eap_tls / eap_ttls / peap / mac_auth / other, outcome enum authenticated / rejected / failed, opaque `subject_ref`, optional core network/device binding validated against the org), `list_auth_events`, `auth_summary` (counts by method and outcome, derived at read). The build authenticates no one — `authenticated_here: False` on every record; the outcome is the caller's report. No credential can be recorded: `password=` / `shared_secret=` raise TypeError (pinned) |
| Cloud PKI & certificate lifecycle engine | reference (stub-engine, as drafted) | `register_certificate` (`crt-`, certificate named by opaque `certificate_ref`, validity window validated, optional core device binding; `reference_stub: True`, `issued_here: False`), `record_certificate_event` (`cev-`, reported kinds issued / renewed / revoked / expired / suspended / reinstated; `executed_here: False`), `get_certificate` / `list_certificates` — `reported_lifecycle_state` derived at read from the event stream, never stored. No certificate material exists: `certificate_bytes=` / `private_key=` raise TypeError (pinned) |
| Wi-Fi ITDR engine | reference (stub-engine by re-judgment — see note 1) | `record_itdr_finding` (`itd-`, kind enum credential_misuse / anomalous_access / rogue_client / certificate_anomaly / other; the reporter's `severity_label` stored verbatim; optional core network/device binding; `reference_stub: True`, `detected_here: False`), `list_itdr_findings`, `itdr_summary` (counts by kind and by reported label) |
| Captive portal & guest / roaming access services | built (build-extension, as drafted) | `create_guest_access` (`gst-`, kinds voucher / sponsored / open_roaming / portal_self_register, bound to a core network, validity window validated, sponsor/guest/voucher as opaque refs; `portal_served_here: False`, `admitted_here: False`), `get_guest_access` / `list_guest_access` — window state (`scheduled` / `active` / `expired`) derived at read against a caller-supplied read clock, never stored |
| Satellite terminal provisioning & connectivity management | reference (stub-engine, as drafted) | `register_terminal_provisioning` (`trm-`, terminal by opaque `terminal_ref` unique per org, optional core network binding and plan ref; `reference_stub: True`, `provisioned_here: False`, `connected_here: False`), `record_terminal_outcome` (`tro-`, reported outcomes provisioned / activated / deactivated / failed / suspended; `executed_here: False`), `get_terminal_provisioning` / `list_terminal_provisionings` — `reported_state` derived at read from the outcome stream |
| Fleet mapping & geospatial awareness platform | reference (stub-engine by re-judgment — see note 2) | `record_asset_position` (`pos-`, a position *report*: opaque `asset_ref` + coarse caller-chosen `region_ref` + reported timestamp; `reference_stub: True`, `located_here: False`, `mapped_here: False`), `record_asset_link` (`lnk-`, recorded links between opaque refs, self-links rejected), `list_asset_positions`, `list_asset_links`, `fleet_view` — distinct-asset count, report count, per-region counts, and per-ref link degrees derived at read. No coordinate exists: `latitude=` / `longitude=` / `coordinates=` raise TypeError (pinned) |
| Incident lifecycle management engine | built (build-extension, as drafted) | `open_incident` (`inc-`, bound optionally to a core network/device; the stored record carries exactly seven keys and **no state key**), `record_incident_event` (`iev-`, kinds acknowledged / escalated / mitigated / resolved / closed / reopened / note), `get_incident` / `list_incidents` / `list_incident_events`, `incident_summary` (counts by derived state) — state derived at read by the seam `_derive_incident_state` (latest state-changing event; `note` events never change it), the batch's fresh negative control. Recording an incident mutates no core device, network, or change record (pinned by before/after equality) |
| GPU orchestration (fork excess) | reference (stub-engine, as drafted) | `register_gpu_job` (`gpu-`, job and workload by opaque refs, `requested_units` a non-negative integer — floats and bools rejected; `reference_stub: True`, `orchestrated_here: False`, `scheduled_here: False`), `record_gpu_outcome` (`guo-`, reported outcomes scheduled / running / completed / failed / cancelled, reported units as reported; `executed_here: False`), `get_gpu_job` / `list_gpu_jobs` — `reported_state` derived at read from the outcome stream |

## Re-judgment notes (DECISION.md qualification 1)

**1. idx 923, Wi-Fi ITDR engine — build-extension →
reference.** A threat-detection finding is a verdict rendered
by a running detector over live authentication traffic: that
an access pattern *is* credential misuse or an anomaly is the
detector's inference, and a records substrate has no detector
to render it with. Building "detection" here would either
fabricate verdicts or relabel caller reports as the build's
own findings. The entry therefore lands in the batch's
standing form for detector-shaped entries (the Ops Mgmt AI
assistants and LE AI investigation models precedents):
findings are recorded as *reported* by an external detector,
the severity label is the reporter's and is stored verbatim,
and every record carries `reference_stub: True` and
`detected_here: False`. The records surface itself — kinds,
bindings to core networks/devices, counts by kind and label —
is genuinely built and tested; only the closure token
changes.

**2. idx 926, Fleet mapping & geospatial awareness platform —
build-extension → reference.** The entry's substance is a
geospatial platform: live asset positions on a map. A position
is a sensed fact, and this substrate's privacy discipline —
the founding invariant of the category — holds that no record
shape can carry a live-network identifier or location: the
core has no coordinate field anywhere, by design and by test.
There is no records-only form of "mapping" that is not a
label for a sensing/rendering engine the build does not have.
The entry lands as reported position records at the coarsest
honest grain: an opaque asset reference plus a caller-chosen
region label (never a coordinate — no parameter can accept
one, pinned), recorded links between references, and a fleet
view of counts and link degrees derived at read, every record
labeled `reference_stub: True`, `located_here: False`,
`mapped_here: False`.

Two near-the-line calls were **not** re-judged, stated here so
the record shows them: idx 921's authentication *engine*
authenticates against live supplicants and identity stores,
and idx 924's portal *services* serve pages and admit guests;
both close `built` because what this substrate can honestly
deliver for them — the outcome records of the one and the
grant records of the other — is genuinely built over the
substrate's own networks and devices, with the boundary
carried on every record (`authenticated_here: False`;
`portal_served_here` / `admitted_here: False`). If the parent
prefers `reference` for either, only the token changes; the
code is identical either way.

## Not covered by this unit

- idx 929, "Platform layer" — already closed `re-scoped`
  under `../../PLATFORM-LAYER.md` before this unit; untouched.
- The founding group's twelve engine gaps (network
  optimization engine; network intelligence / AI engine;
  device provisioning & deployment engine; network
  configuration push / control plane; firmware management
  engine; traffic control & SD-WAN policy engine; telemetry
  collection & polling engine; alert evaluation & delivery
  transport; integration connectors; automation execution
  engine; cloud management web application; FIPS-validated
  cryptography, SC-13) — registered under the founding group,
  not re-registered here, and not part of this unit. This
  unit's alert-shaped surface is records-only for the same
  reason the core's is: delivery transport is an engine over
  external systems, and nothing here sends.
- No HTTP routes: the extension surface is store-level, as in
  the sibling batch units.
