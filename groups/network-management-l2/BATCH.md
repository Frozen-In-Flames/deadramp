# Final GAPS batch — Network Management L2 (Singleton 51)

Batch note for the eleven open entries of the repo-root `GAPS.md`
section "Singleton 51 — Network Management L2 (1 fork, new
category)", closed under the ratified triage in
`gaps-batch/DECISION.md`. The section's twelfth entry,
FIPS-validated cryptography (SC-13), is already closed as
`re-scoped` under `PLATFORM-LAYER.md` decision 2 and is not
touched by this unit. The founding discipline binds throughout:
this build manages no live network, pushes no configuration,
provisions no device, and collects no telemetry — every surface
below is records over the core's organization / network /
device / change / automation / alert records, and nothing
reaches a device or a network.

## What was added

- `src/netmgmt/extensions.py` (one new module):
  `NetmgmtExtensions`, a records register wrapping the core
  `NetmgmtStore`. In-memory collections with the founding
  conventions — validation before mutation (failed operations
  consume no id), the core's own scoped access check (role
  permission + organization membership) reused point-for-point,
  denied extension writes audited in the core audit log under a
  `:denied` suffix, extension mutations audited under `ext_*`
  action names, opaque references only, derived-never-stored
  views, counts-only rollups. No new permission actions exist;
  the founding vocabulary is reused (`enter` for creates and
  registrations, `record` for outcome / state / receipt records,
  `read` for reads).
- `tests/test_gaps_batch.py`: 42 tests pinning the extension
  surface entry by entry, including the stub labels, the
  core-untouched pins, the access boundary, a recursive
  no-score/rating/health/optimization key scan over the whole
  surface, and the batch's fresh negative control (below).
- A "Final GAPS batch" section appended to `tests/README.md`,
  recording the batch's fresh mutation-verified negative
  control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the pre-batch accounting before and after the build:
`store.py` still `5b1e861c…`, all 7 of 7 unchanged). No core
change was needed, and none was made. Suite: **72 tests before →
114 tests after, OK**.

## Per-entry disposition

**Build-extension (7)** — each closed by its in-substrate records
form: records plus deterministic derivations over this group's
own core records.

1. **Network optimization engine** — recorded *recommendation*
   records (`create_recommendation` / `list_recommendations`).
   **Form choice, stated per the brief:** recommendations-as-
   records, not derivations over telemetry. A recommendation is
   advice with a stated basis (`telemetry_review`,
   `manual_review`, `external_analysis`) and an opaque detail
   reference; every record carries `computed_here: False` and
   `applied_here: False`. The fork's "optimize" is a real verb
   and the family is claimed, but an optimizer is an engine over
   live network state; deriving pseudo-recommendations from the
   registry's caller-supplied telemetry snapshots would dress a
   records substrate up as one. The summary surface counts
   recommendation records; no record or view holds an
   optimization value (the extension respects the core's
   recursive forbidden-key scan, including the `optimization`
   substring, on every key — the surface's count key is
   `recommendations`).
2. **Network intelligence / AI engine** — model-profile records
   (`create_model_profile`, kinds anomaly_detection /
   insight_generation / classification / other) carrying
   `reference_stub: True` and `inference_here: False`, plus
   reported-output records (`record_model_observation`) whose
   labels are held verbatim with `computed_here: False`.
   `find_model_profiles` is a deterministic exact-match record
   lookup (network and/or kind filters, registration order);
   observation counts are derived at read on the profile view.
   No model is trained, run, or inferred from.
3. **Network configuration push / control plane** — push records
   linked to core change records (`create_config_push`), with
   outcome records (`record_push_outcome`) holding reported
   states verbatim (`reported_applied` / `reported_failed` /
   `reported_partial`). Every push record carries
   `applied_here: False`. The push's current state is derived at
   read by `_derive_push_state` (latest outcome wins; none →
   `recorded`) and is never stored — the stored record provably
   lacks the derived keys. Pinned by test: recording a push and
   its outcomes leaves the raw core device, network, and change
   records byte-identical, and the core change remains in
   whatever lifecycle state the core put it in (a push record
   neither decides nor closes it).
4. **Firmware management engine** — firmware records
   (`create_firmware`: a version label per device class, classes
   from the core's own vocabulary) and assignment records
   (`assign_firmware`) binding a firmware record to a core
   device, with the device's class required to match the
   firmware record's class. Reported install states
   (`record_assignment_state`) are recorded verbatim; the
   assignment view derives the current state at read. Every
   assignment carries `deployed_here: False`.
5. **Traffic control & SD-WAN policy engine** — policy
   *definition* records (`create_traffic_policy`): rules held as
   data (each exactly `name` / `action` / `match_ref`, actions
   allow / deny / shape / prioritize), deep-copied at the
   boundary in both directions. Definitions are never evaluated
   against traffic and never enforced — `evaluated_here: False`,
   `enforced_here: False` on every record. Reported states
   (`record_policy_state`) are recorded verbatim and the current
   state is derived at read (`unreported` until one exists).
   The family stays named from the device gloss, as the spec
   records it; nothing here upgrades the gloss into a claim.
6. **Automation execution engine** — run *reference* records
   (`record_automation_run`) against core automation
   definitions: a reported status held verbatim, every record
   carrying `reference_stub: True` and `executed_here: False`.
   Pinned by test: recording a run leaves the core organization
   summary and the raw automation definition record unchanged —
   the registry-never-executes doctrine is not repealed, it is
   exactly what the records form records around.
7. **Cloud management web application** — page *configuration*
   records (`create_page_config`): an organization-unique
   `page_ref`, a title, and widget definitions held as data
   (each exactly `kind` / `title`, kinds from a fixed
   vocabulary). Nothing is rendered and nothing is served —
   `rendered_here: False`, `served_here: False` on every
   record; widget count and the sorted kind set are derived at
   read on the view and never stored. A browser UI is a client
   surface, not a records function; the records form is the
   configuration layer such a UI would read, and that bound is
   stated rather than smoothed over.

**Stub-engine (4)** — each shipped as a labeled reference
implementation inside the same extension surface, records only,
never execution.

8. **Device provisioning & deployment engine** — provisioning
   reference records (`create_provisioning_reference`) keyed by
   an opaque caller-chosen `device_ref` for a device *not yet*
   in the inventory, carrying `reference_stub: True` and
   `provisioned_here: False`; reported states
   (`record_provisioning_state`) recorded verbatim, current
   state derived at read. Pinned by test: creating a reference
   creates no core device record.
9. **Telemetry collection & polling engine** — collection
   reference records (`create_collection_reference`) naming a
   core device, metric, and interval label, plus receipt records
   (`record_collection_receipt`) holding a record count and a
   window label **as reported**. Every record carries
   `reference_stub: True`, `reference_transport: True`, and
   `collected_here: False`. Receipt counts are validated as
   non-negative integers under the core's integer discipline.
   Pinned by test: a receipt creates no core telemetry record —
   core telemetry remains caller-supplied records only.
10. **Alert evaluation & delivery transport** — evaluation
    records (`record_alert_evaluation`) holding a verdict label
    verbatim against a core alert (`evaluated_here: False` —
    the verdict was reached elsewhere), and delivery receipts
    (`record_alert_delivery`) holding a channel and a reported
    state, carrying `reference_stub: True`,
    `reference_transport: True`, `delivered_here: False`.
    Pinned by test: recording either leaves the raw core alert
    record byte-identical.
11. **Integration connectors** — connector reference records
    (`create_connector_reference`) naming an external system by
    opaque reference, carrying `reference_stub: True`,
    `reference_transport: True`, `connected_here: False`.
    Nothing connects; the build's own answer to the open-APIs
    claim remains the core REST API, unchanged.

## Re-judgments

None. Every entry fit its drafted disposition on a close reading
of the union spec. The one form choice the brief left open —
optimization as recorded recommendations versus derivations over
recorded telemetry — is resolved in favor of recorded
recommendations with the grounds stated at entry 1 above; the
closure token is unchanged (`built`), so this is a form
statement, not a re-judgment.

## Negative control

Fresh mutation-verified control for the new code, recorded in
`tests/README.md`: the config-push state derivation
(`_derive_push_state`, latest outcome wins). An in-suite mutant
subclass derives from the earliest outcome; the external drill
patched the real `extensions.py` seam the same way and the suite
ran **114 tests with exactly 3 failures**
(`TestConfigPush.test_outcome_states_derive_latest`,
`TestPushStateNegativeControl.test_canonical_expectation`,
`TestPushStateNegativeControl.test_implementation_matches_canonical`).
The file was restored from `scratch/extensions.py.premutation`,
SHA-256 verified identical (`2142c66b…`), and the suite re-ran
green.

## Not covered by this unit

- The FIPS-validated cryptography entry (already `re-scoped`;
  stands on PLATFORM-LAYER.md decision 2, not absorbed here).
- The section's platform-layer paragraph (U.S. data residency,
  scalability, encryption at rest, demo identities as hooks)
  stands on PLATFORM-LAYER.md, not absorbed.
- The Untiered Set 19 Network Management entries are a
  different unit in a different directory and are untouched.
- HTTP exposure of the extension surface: none was added. The
  core service layer is a core module and stays byte-identical;
  the extension surface is store-level, matching the sibling
  batch units' pattern.
