# Final GAPS batch — Untiered Set 15, Fleet Management (2 forks, tier null)

Date: 2026-11-07. This section of `../../GAPS.md` listed 8
entries; 1 (Platform layer, idx 882, drafted rescope-platform)
was already closed `re-scoped` in writing at batch foundation
under `../../PLATFORM-LAYER.md`, and the remaining **7 open
entries are closed by this unit** under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/fleet/extensions.py`
(`FleetUntieredExtensions`, wrapping the core `FleetStore`;
all seven core modules byte-identical, SHA-256 verified
against the group's README accounting — store.py still
`c1fd0b1c…`, the shipped hash), and
`tests/test_gaps_batch.py` (28 tests). Full suite:
**83 → 111 tests**, all passing.

**Tier discipline binds every shape built here:** this set is
untiered — the source publishes no FedRAMP impact level for
either fork — so nothing here asserts a tier, a baseline, or a
CMMC equivalence, and a recursive scan pins that no
tier/baseline/impact/CMMC-shaped key exists anywhere on the
extension surface. The founding group's RBAC and audit hooks
ride as baseline-neutral substrate, claimed against no
baseline.

**The founding discipline binds every shape built here:** this
build holds records about fleet operations. It streams no
telemetry, senses no position, ingests no device data,
analyzes no video, connects to no external system, executes
no workflow, renders no front-end, and moves no money.
**The category's defining inverse invariant holds on this
surface too: there is no charge-control surface anywhere** —
no method in this module can start, stop, limit, or otherwise
command a charging session (pinned by test); charging here
remains the core's custody accounting, and this unit adds no
command path to it. Records carry metadata and opaque
caller-supplied references only, plus figures and outcomes
stored exactly as reported by the external systems and people
who actually did the work. That is pinned by exact key-set
assertions per record type, by `TypeError` on any unexpected
keyword argument (including any coordinate kwarg — no
coordinate field exists in any shape), and by a recursive scan
pinning that no score/rating/rank/grade/index-shaped key
exists anywhere on the extension surface. Every "engine"
below is its in-substrate form: records over the group's OWN
records (core records and extension records), plus
deterministic derivations at read.

## Per-entry disposition

| Entry (GAPS.md text) | Inventory idx / drafted triage | Disposition | Built as |
|---|---|---|---|
| Live telematics & GPS streaming (two claimants in this set; the founding named absence gains claimants) | 875 / stub-engine | reference | Labeled reference records, the same form the Fleet Management L1 batch unit adjudicated for the identical entry in its tier: stream-subscription records (`tlm-`) against a core vehicle, holding an opaque `source_ref` (`reference_stub: True`, `streamed_here: False` — no stream is opened), plus caller-REPORTED position/status records (`tlr-`) holding the reported position label verbatim (`tracked_here` / `sensed_here: False`). Each report is standalone — no track/trail/history structure exists (pinned by exact key set), and no coordinate field exists: a `latitude=` or `longitude=` kwarg raises `TypeError`. `telematics_stream_view` derives the report count at read; the stored stream carries no count. |
| Integration engines & external connectors | 876 / stub-engine | reference | Labeled reference records: connector records (`con-`) naming an external system by label, direction label, and opaque `endpoint_ref` (`reference_stub: True`, `connected_here` / `invoked_here: False` — nothing connects to, authenticates against, or exchanges data with the named system), plus reported invocation/sync outcome records (`cno-`) with labels verbatim. `connector_view` derives the outcome count at read. Stated on the records' face: the build's own REST API is its contract, not a connector, and is not what this entry closes. |
| Video-based safety & dash-camera analytics engines | 877 / stub-engine | reference | Labeled reference records: camera-binding records (`cam-`) binding a core vehicle to an opaque `device_ref` (`reference_stub: True`, `connected_here` / `footage_held_here: False`), plus reported safety-event records (`vse-`) holding the event kind (hard brake, distraction, collision, near miss, speeding — all in `reported_*` form) and severity label verbatim as classified by the external video system that actually analyzed the footage (`analyzed_here` / `detected_here` / `footage_held_here: False`). No frame, clip, or image can exist in any shape: a `footage=` kwarg raises `TypeError`. `camera_binding_view` derives the event count at read. |
| IoT device telemetry ingestion & equipment/environmental monitoring engines | 878 / stub-engine | reference | Labeled reference records: device records (`iot-`) in the recorded kinds (vehicle gateway, dash camera, environmental sensor, equipment monitor) holding an opaque `device_ref` and a subject label (`reference_stub: True`, `connected_here` / `ingested_here: False`), plus reported observation records (`obs-`) holding the metric label and the reported value label verbatim, as reported by the device platform that actually sensed them (`sensed_here` / `ingested_here: False`). Each observation is standalone — no stream, series, or history structure exists. `iot_device_view` derives the observation count at read. |
| Alerting & notification engines | 879 / build-extension | built | Records form: alert-rule records (`alr-`) holding a condition label as data, never evaluated (`evaluated_here: False`); alert records (`alt-`) raised by reporters against a rule with the severity label verbatim (`detected_here: False` — the detection happened in the system that reported it); and notification records (`ntf-`) in the house delivery-attempt form — channel kind and opaque recipient reference, outcome label verbatim, `reference_transport: True`, `delivered_here: False`, and no message field in the shape, so no message content can be held (a `message=` kwarg raises `TypeError`). `alerts_view` derives counts of rules, alerts by severity, and notifications by outcome at read — counts only. The engine halves (condition detection against live telemetry, message transmission) are stated absent on the records themselves. |
| Driver workflow & compliance applications | 880 / stub-engine | reference | Labeled reference records: workflow-task records (`dwf-`) bound to core operator records, holding the task label and the reported status label verbatim (`reference_stub: True`, `executed_here: False` — nothing assigns, routes, or executes a workflow step), plus compliance-application records (`cmp-`) holding the application-area label and the reported compliance label verbatim (`evaluated_here: False` — no compliance status is determined here). Stated in the module and here: the descriptions' "regulatory compliance" phrase names an application area, not a control family (the founding set's recorded adjudication); nothing in this surface converts it into a control claim. `workflow_view` derives task counts by reported status at read. |
| Dashboarding front-ends beyond registry reporting | 881 / build-extension | built | Dashboard-definition records (`dsh-`): panel kinds held as data from a fixed set (`record_counts`, `charging_energy`, `maintenance_completed_share`, `latest_odometer`; unknown kinds refused at the boundary), `rendered_here: False` — no front-end is rendered. `dashboard_view` derives exactly the named panels' figures at read over the substrate's own core records: counts per core record set carried from the core summary, aggregate recorded charging energy (integer watt-hours), the maintenance completed share via the seam `_maintenance_completed_share` rendered as an exact int/`"num/den"` fraction (`None` when no maintenance records exist), and the latest recorded odometer (maximum recorded reading, or `None`). Figures derive at read and are stored nowhere — a test proves a dashboard recorded earlier reports registry state recorded after it. No score, rating, ranking, or index exists anywhere on the surface (recursive scan). |

Closure tokens: the drafted split for the 7 open entries was
2 build-extension / 5 stub-engine, and it held with **no
re-judgments**: **2 built** (alerting & notification engines,
dashboarding front-ends beyond registry reporting) and
**5 reference** (live telematics & GPS streaming, integration
engines & external connectors, video-based safety &
dash-camera analytics engines, IoT device telemetry ingestion
& equipment/environmental monitoring engines, driver workflow
& compliance applications). The parent closes the tokens in
GAPS.md; this unit's count line is stated so the two agree.

## Re-judgments

None. The two drafted build-extension entries both have a
genuine in-substrate records form (rules/alerts/delivery
attempts; definitions plus read-time derivation), and the
five drafted stub-engine entries are all engines over
external systems — telemetry streams, external integrations,
video analytics, device telemetry, workflow execution — whose
honest form in this substrate is the labeled reference form.
Two calls nearest the line are stated plainly:

- **Alerting & notification** closes `built` in the records
  form: the rule is a definition, the alert is a reporter's
  record, and the notification is a delivery-attempt record.
  Nothing here detects a condition or transmits a message,
  and the records say so (`evaluated_here` / `detected_here`
  / `delivered_here: False`). This matches the batch's
  standing adjudication of notification-shaped surfaces
  (delivery attempts are records; delivery is not claimed).
- **Dashboarding** closes `built` as definitions plus
  derivation, not as a rendered front-end: `rendered_here` is
  False on the definition and on the view, and the view is
  data in the same shape as every other read in this build.
  The front-end half of the entry (a rendered UI) is a
  deployment surface, not a records function; the records
  function the entry names beyond registry reporting — panel
  figures over the registry — is what is built.

## Negative control

Fresh, for the new code: the dashboard derivation seam
(`_maintenance_completed_share` in `src/fleet/extensions.py`
— the exact share of core maintenance views whose
core-derived status is `completed`, or `None` when there are
no maintenance records). In-suite control in
`tests/test_gaps_batch.py`
(`TestCompletedShareNegativeControl`: the canonical views —
two completed, one past-due uncompleted — yield `2/3` from
the seam; a local overdue-counting mutant yields `1/3`, and
treating the mutant's outcome as the expectation fails via
`assertRaises(AssertionError)`), plus a live drill on the
real file: the seam's status comparison was patched from
`"completed"` to `"overdue"`, and the full suite ran **111
tests with exactly 3 failures**, all in the batch's own new
tests (`TestCompletedShareNegativeControl.test_canonical_share_exact`,
`TestCompletedShareNegativeControl.test_overdue_counting_mutant_is_rejected`,
`TestDashboardingBuilt.test_view_derives_figures_at_read`) —
no core or spec test failed. The file was restored from
`scratch/extensions.py.premutation`, verified byte-identical
by SHA-256 (`scratch/extensions.py.sha256`), and the suite
re-ran green at 111. Recorded in tests/README.md; drill
output in `scratch/gaps_mutation_run.txt`.

## Not covered / honesty notes

- Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the core service layer is
  untouched and all seven core modules are byte-identical.
- No record in this unit streams telemetry, senses a
  position, ingests device data, analyzes video, connects to
  an external system, evaluates an alert condition, detects
  an alert, transmits a notification, executes a workflow,
  evaluates a compliance status, renders a dashboard, or
  commands a charging session; the `*_here: False` labels
  are on the records themselves, not only in this document.
- Position data exists here only as caller-reported labels
  held verbatim; there is no coordinate field in any shape,
  and the recursive scan pins latitude/longitude/coordinate
  keys absent alongside the score-shaped keys and the
  tier-shaped keys.
- Operator privacy carries from the core unchanged:
  extension records bind operators and vehicles by core
  record id or opaque caller-supplied reference only; no
  shape here can hold a real name, a license number, a
  message body, or footage.
- The set's named absences stand as recorded in the union
  spec: ELD / hours-of-service was not part of this section's
  entries (it stands registered from the founding group) and
  nothing in this unit builds or claims it; the compliance
  records here are reported application outcomes, not an ELD
  integration and not a control claim.
