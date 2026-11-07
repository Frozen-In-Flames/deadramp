# Final GAPS batch — Group 36, Operations Management L2

Unit: the 13 OPEN entries of this group's section in the repo-root
GAPS.md ("Group 36 — Operations Management L2 (2 forks)"). The
separate "Remainder Addition — Operations Management L2" and
"No-Signal Addition — Operations Management L2" sections are
different units; nothing in them is touched or absorbed here, and
their spec sheets and tests are unchanged (one disclosed era
rescope in `tests/test_nosignal.py` aside — see below).

Batch pattern: gaps-batch/DECISION.md (ratified 2026-11-07).
Everything below lands in ONE new module,
`src/opsmgmt/extensions.py` (class `OpsExtensions`, wrapping the
core `OpsStore`), plus `tests/test_gaps_batch.py`. **No existing
core module was changed** — all seven pre-existing
`src/opsmgmt/*.py` files verified byte-identical by SHA-256
before and after (`store.py` remains
`8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`,
the group's recorded shipped hash).

Group discipline, applied to every entry: this build is the
shared records substrate only. Nothing in the extension executes,
enforces, deploys, syncs, collects, hosts, monitors, or provides
identity. Engine/plane entries are built in their **records
form**: registries of the thing, records of its reported state,
and deterministic derivations over the group's own records.
Identity stays with the embedding organization
(PLATFORM-LAYER.md decision 1): the authorization-service entry
is hook records only. All `*_ref` parameters are opaque tokens —
whitespace, URL, hostname, and IP-shaped values are rejected at
the boundary — and links into the core substrate use core ids
validated through the core store. RBAC reuses the founding
16-action matrix with no new actions (mapping table in the
module docstring); successful mutations audit as `ext_*` actions
on the core log, denied attempts as `ext_*:denied`.

## Per-entry dispositions

### Build-extension (6) — records form in `opsmgmt.extensions`

1. **Low-code application builder & deployment engine** —
   `create_application` / `update_application` /
   `get_application` / `list_applications` /
   `record_deployment_intent` / `list_deployment_intents` /
   `application_view`. Application definition records whose
   components are held verbatim as data (each an object with a
   non-empty `kind`), versioned on update, carrying
   `built_here: False` and `deployed_here: False`; deployment
   intents are records against opaque environment references,
   carrying `status: "recorded"`, `executed: False`,
   `deployed_here: False`. Nothing is built, rendered, or
   deployed. The view's deployment-intent count is derived at
   read and never stored (pinned by test). Definitions are
   configuration, so writes ride `workflow_write` (admin-only),
   exactly as the core workflow registry.
2. **Mobile applications & offline sync** —
   `start_sync_session` / `record_sync_conflict` /
   `resolve_sync_conflict` / `close_sync_session` /
   `get_sync_session` / `list_sync_sessions` /
   `list_sync_conflicts` / `sync_summary`. Sync-session records
   (open → closed with a recorded outcome) and conflict records
   storing both reported values verbatim; a recorded resolution
   is data and is applied nowhere (`applied_here: False` on
   every conflict record; `synced_here: False` on sessions and
   the summary). No device syncs with this build. Summary
   counts are derived at read.
3. **Common security services enforcement plane** —
   `register_security_service_point` /
   `record_security_service_state` /
   `retire_security_service_point` /
   `get_security_service_point` / `list_security_service_points`
   / `list_security_service_states` /
   `security_service_coverage`. The cybersecurity units'
   enforcement-point precedent transposed: a registry of
   enforcement points (access gateway, endpoint protection,
   vulnerability scanning, logging forwarding, encryption
   service, other) over opaque scope/policy references, plus
   state records stored exactly as reported by the external
   services. Every record carries `enforced_here: False` —
   nothing is enforced. Coverage is a derived counts view,
   never stored (the stored point shape is pinned by test).
4. **Policy enforcement plane (runtime enforcement across
   projects)** — `create_policy` / `assign_policy` /
   `record_policy_evaluation` / `get_policy` / `list_policies` /
   `list_policy_assignments` / `list_policy_evaluations` /
   `policy_summary`. Policy definition records (`rule_text`
   held verbatim, never evaluated) and project assignment
   records as configuration (`workflow_write`); evaluation
   records store outcomes exactly as reported by an external
   enforcement plane, under a separation-of-duties seam
   (`_check_evaluator_not_creator`: the evaluator may never be
   the policy's creator). Every record carries
   `enforced_here: False`. Summary counts are derived at read.
5. **Scheduling & rostering (0 of 2; named absence)** —
   `create_roster` / `create_shift` / `assign_shift` /
   `withdraw_shift_assignment` / `get_roster` / `list_rosters` /
   `list_shifts` / `list_shift_assignments` /
   `roster_coverage`. Roster, shift, and assignment records
   over the core directory (assignees are core person ids,
   validated through the core store). Coverage — per-shift
   active assignee count against required count, covered flag,
   shortfall — is derived at read; the stored shift carries no
   count (pinned by test). Load-bearing guard: a person may
   not hold two ACTIVE assignments whose windows overlap
   (half-open windows; adjacent shifts are allowed; withdrawn
   assignments free the window), enforced at the named seam
   `_check_shift_overlap` — the batch's fresh negative
   control. The build schedules no one and notifies no one.
6. **IoT / telematics data collection (0 of 2; named
   absence)** — `register_device` /
   `record_telemetry_reading` / `get_device` / `list_devices` /
   `list_telemetry_readings` / `telemetry_summary`.
   Device-registration records keyed by an opaque
   `device_ref`; the record shape is pinned by test to exactly
   eight keys with no field that can hold an identifier (no
   IMEI/serial/VIN/MAC/phone-shaped key exists). Reading
   records store metric and value verbatim as reported by an
   external collection path; every record carries
   `collected_here: False` — the build collects nothing.
   Non-scalar values (bool, None, containers) are rejected.
   Summary counts are derived at read.

### Stub-engine (7) — labeled reference implementations

7. **Workflow automation execution engine (the registry is
   Core; execution is the engine)** —
   `register_workflow_run_reference` /
   `list_workflow_run_references`. House precedent: a run
   reference copies the core workflow's current definition
   (name, work type, version, trigger/action text, enabled)
   into the record as data and carries `reference_stub: True`
   and `executed: False`. A test pins that registering a run
   reference changes no core work order — the registry never
   executes, here exactly as in the core.
8. **Real-time intelligence & analytics engine (streaming
   intelligence, outcome analytics beyond registry
   reporting)** — `register_stream_reference` /
   `record_stream_snapshot_reference` /
   `list_stream_references` / `list_stream_snapshots`. Stream
   references (`streamed_here: False`) plus snapshot references
   carrying counts exactly as reported, with
   `reference_stub: True`, `reference_transport: True`, and
   `computed_here: False`. Nothing streams through this build
   and no analytics is computed.
9. **AI models (1 claim)** — `register_model_reference` /
   `record_model_output_reference` / `list_model_references` /
   `list_model_output_references`. Model references
   (`trained_here: False`, `inference_here: False`) plus
   output references whose label is stored exactly as the
   external model reported it. The output record shape has no
   score or confidence field — pinned by test.
10. **Integration connector engines & catalog** —
    `register_connector_reference` /
    `record_connector_run_reference` /
    `list_connector_references` /
    `list_connector_run_references`. Catalog references
    (`connected_here: False`) plus run references carrying
    `reference_stub: True`, `reference_transport: True`, and
    `executed_here: False`. Nothing connects and no record
    moves through this build.
11. **Network connectivity services & cloud platform
    operations (platform-layer; one sibling's own service)** —
    `register_platform_service_reference` /
    `record_platform_operation_reference` /
    `list_platform_service_references` /
    `list_platform_operation_references`. Service references
    (`hosted_here: False`, `operated_here: False`) plus
    operation references (`performed_here: False`), all
    carrying `reference_stub: True`. Per PLATFORM-LAYER.md
    decision 6, the sibling's hosting substrate does not
    transfer to the build.
12. **Authorization service / identity provider (the build
    ships RBAC hooks, not an IdP)** — `register_identity_hook`
    / `list_identity_hooks`. Hook records only, per
    PLATFORM-LAYER.md decision 1: every record carries
    `hook_only: True`, `identity_provider: False`, and
    `reference_stub: True` in its own shape. No identity is
    provided, proofed, or asserted here.
13. **Governance / compliance console engine (continuous
    compliance monitoring depth)** —
    `register_governance_framework_reference` /
    `record_compliance_snapshot_reference` /
    `list_governance_frameworks` / `list_compliance_snapshots`
    / `governance_summary`. Framework references with control
    references held as data (`monitored_here: False`) plus
    snapshot references carrying counts exactly as reported
    (`computed_here: False`). The summary is counts only — a
    test pins that no score/rate/grade/percent key appears in
    it. No continuous monitoring happens here.

## Re-judgments

None among the 13 entries. Every entry fit its drafted
disposition on a close reading of UNION-SPEC.md: the six
build-extension entries all have an honest records form
consistent with how the founding spec already drew their
Core/Extended lines (its function table marks authorization,
common security services, and policy enforcement as Core *hooks*
with the planes Extended — the records form above is exactly
that line), and the seven stub-engine entries are the families
whose records form would still imply an engine (execution,
streaming, inference, connection/transport, hosting/operation,
identity provision, continuous monitoring), so they ship
labeled.

## Disclosed test-only change outside the extension surface

`tests/test_nosignal.py` arrived RED at this unit's baseline
(134 tests, 1 failure, before any unit work): its git-HEAD pin
asserted HEAD held exactly 22 spec sheets, true only before
that unit's own ship committed the 23rd. Following the
established era-rescope accommodation (the same fix the LMS L2
and H&W untiered batch units took, disclosed the same way),
the pin is scoped to its own era's slice — HEAD's first 22
sheets, which the working file's first 22 must still deep-equal
exactly. `specs/specs.json` itself is untouched, and the pin's
strength over the pre-existing sheets is unchanged. Recorded
here and in the test's docstring for the parent's adjudication.

## Tests and negative control

- Suite: **134 before → 184 after, OK** (50 new tests in
  `tests/test_gaps_batch.py`, at least one per entry, plus
  cross-cutting RBAC/audit, no-id-on-failure, and
  copies-are-copies pins). The 134 before includes the
  era-rescope fix above; before that fix the delivered tree
  ran 134 with 1 failure (the stale HEAD pin).
- Fresh mutation-verified negative control: the shift-overlap
  guard `_check_shift_overlap` in `src/opsmgmt/extensions.py`.
  The in-test control (`TestShiftOverlapNegativeControl`)
  asserts the canonical expectation, that a no-op mutant of
  the seam would not produce it, and that treating the
  mutant's outcome as expected fails. Live drill on the real
  file: the guard's overlap condition was patched to `False`
  (guard disabled); the full suite ran: **184 tests, exactly
  2 failures** —
  `test_gaps_batch.TestScheduling.test_overlap_rejected_canonical`
  and
  `test_gaps_batch.TestShiftOverlapNegativeControl.test_overlap_guard_canonical_but_mutant_not`.
  The file was restored from `scratch/extensions.py.premutation`
  and verified SHA-256 identical
  (`3c2da202bb3eca5d91f8f37c4376ca4acf84d1980c451d70626ba24d28333db7`)
  and the suite re-ran green. Recorded in tests/README.md;
  raw drill output in `scratch/gaps_mutation_run.txt`.

## Unresolved

Nothing unresolved within this unit. The extension surface is a
store-level surface only, matching the batch pattern for sibling
units: no HTTP routes were added (the founding `service.py` is a
core module and stays byte-identical), so the extension is
consumed in-process, like the other groups' batch extensions.
