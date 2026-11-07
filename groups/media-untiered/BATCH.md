# Final GAPS batch — Media, Untiered Set 27

Batch note for the five open entries of the repo-root `GAPS.md`
section "Untiered Set 27 — Media (1 fork, tier null; NEW
CATEGORY)", closed under the ratified triage in
`gaps-batch/DECISION.md`. This set is untiered: tier stays null
everywhere — no baseline is asserted, no CMMC equivalence is
drawn, and nothing in this batch adds a tier, baseline,
impact-level, or equivalence key or language to any record,
view, or document. The founding discipline binds throughout:
the substrate holds records about media, never media; nothing
transports, encrypts, sends, adapts, or collects here.

## What was added

- `src/media/extensions.py` (one new module): `MediaExtensions`,
  a records register wrapping the core `MediaStore`. In-memory
  collections with the founding conventions — validation before
  mutation (failed operations consume no id), founding-permission
  RBAC with denials audited in the core audit log under a
  `:denied` suffix, opaque references only, derived-never-stored
  views, counts-only summaries. RBAC reuses the founding action
  vocabulary (no new actions): transport runs and encryption
  references write under `routes`; control dispatches under
  `control`; optimization assignments under `optimize`;
  telemetry collection references under `monitor`; all reads
  under `read`. The action mapping is documented in the module
  docstring.
- `tests/test_gaps_batch.py`: 35 tests pinning the extension
  surface entry by entry, including the stub labels, the
  untouched-core pins, a recursive tier/baseline/score key scan
  over the whole new surface, and the batch's fresh negative
  control (below).
- A "Final GAPS batch coverage" section appended to
  `tests/README.md`, recording the batch's fresh
  mutation-verified negative control.
- A batch note appended to the group `README.md`.

Existing core modules are byte-identical (SHA-256 verified
against the pre-build baseline: `store.py` still `6162c8c0…`,
all 7 of 7 unchanged). No core change was needed, and none was
made. Suite: **67 tests before → 102 tests after, OK**.

## Per-entry disposition

**Build-extension (2)** — each closed by its in-substrate
records form: records bound to this set's own core registry,
plus deterministic derivations over the recorded values.

1. **Device control channel (control actions are recorded,
   never sent)** (idx 962) — dispatch records
   (`record_control_dispatch`) bound one-to-one to core
   control-action records: a dispatch names the action and its
   device exactly as the core recorded them, and a second
   dispatch of the same action is refused with no id consumed.
   Delivery outcome records (`record_delivery_outcome`) hold
   the channel's reported outcome labels verbatim, and
   `device_dispatch_view` derives a device's dispatch count,
   outcome counts by reported label, outcome-less dispatch
   count, and latest reported label at read time — none of it
   stored. Every dispatch/outcome record carries
   `reference_transport: True` with `sent_here: False` and
   `delivered_here: False`: the entry's own text bounds the
   family — control actions are recorded, never sent — and what
   is built is the records layer over the core's control
   registry through which a channel's operation is named,
   attributed, and audited. A test pins that dispatching and
   reporting change nothing in the core (summary and device
   record identical before and after).
2. **Stream optimization engine** (idx 963) — assignment
   records (`record_optimization_assignment`) binding a core
   optimization profile to a core route of the same
   organization (cross-organization bindings and duplicate
   assignments refused with no id consumed), outcome records
   holding the engine's reported outcome labels verbatim, and
   `route_optimization_view` deriving at read time the
   assignment count, the recorded profile ids, the enabled
   count joined from the core profiles' recorded flags, the
   outcome count, and the latest reported label. **The honest
   form is narrower than the entry's name, stated plainly:** no
   stream is adapted, no profile is applied, and no figure of
   any kind (bitrate, latency, quality) is computed or stored —
   every assignment and outcome record carries
   `applied_here: False`, `adapted_here: False`, and
   `optimized_here: False`. What is built is the
   records-and-derivation layer — assignments over the core's
   own profile and route registries, and deterministic
   derivations over them — which is the part of the family this
   substrate can honestly hold. The disposition stays
   build-extension on that stated scope, on the CMS set's
   personalization precedent (records plus deterministic
   derivations, the engine itself not built, the bound stated
   rather than smoothed over).

**Stub-engine (3)** — each closed as a labeled reference
implementation: registry records only, never execution, each
carrying `reference_stub: True` and its family's not-here
flags.

3. **Live video transport & routing engine (the network
   itself)** (idx 960) — transport run records
   (`record_transport_run`) naming a core route and optionally
   one of that route's core sessions, plus outcome records
   (`record_transport_outcome`) holding the transport service's
   reported outcome labels verbatim. Every record carries
   `reference_transport: True` and `transported_here: False`.
   The network itself — contribution feeds, transport
   protocols, inter-agency connectivity — is an external
   system; a test pins that recording a run starts no session
   and leaves the route record identical.
4. **Stream encryption implementation (the build performs no
   cryptography; route records carry a caller-stated label
   only)** (idx 961) — encryption reference records
   (`record_encryption_reference`) naming a core route and
   holding the mechanism label verbatim as the fork documents
   it (e.g. "AES-256"), plus reported status records
   (`record_encryption_status`) holding key-lifecycle and
   provisioning reports verbatim. A reference record snapshots
   the route's caller-stated encryption label as a recorded
   value and never changes it — pinned by a test that the route
   record is identical before and after references and status
   reports. Every record carries
   `cryptography_performed_here: False` and
   `encrypted_here: False`; no key material is held in any
   field. Per PLATFORM-LAYER.md decision 2, no validated-
   cryptography claim is made or transferred: the fork's
   AES-256 assertion remains the fork's, traced in the union
   spec's Documented control claims.
5. **Status & monitoring telemetry collection** (idx 964) —
   collection source records (`record_collection_source`)
   naming a core route or device subject and holding a probe
   label as data, plus collection outcome records
   (`record_collection_outcome`) holding reported outcome
   labels and reported snapshot counts exactly as reported
   (non-negative integers only; booleans and floats refused).
   Every record carries `collected_here: False`: no probe runs
   here. `collection_view` derives the outcome count, the
   latest reported label, and the total of the *reported*
   counts at read — a sum of reports, stated as such, not a
   measurement. A test pins that recording collection sources
   and outcomes creates no core status snapshot (the core's
   snapshot registry stays empty): the core snapshots remain
   what callers record, and the collection that would produce
   them in operation stays external.

## Re-judgments

**None.** All five entries landed at their drafted triage
dispositions (2 build-extension, 3 stub-engine). The two
build-extension entries carry the scope bounds stated in their
dispositions above — dispatch records that send nothing, and
assignment records that apply nothing — which are the
records forms the unit's brief specifies for delivery-shaped
and engine-shaped entries in this substrate, not corrected
dispositions.

## Negative control (fresh, for the new code)

The latest-label seam `MediaExtensions._latest_label` is the
load-bearing derivation behind every family's derived view (a
view's "latest" label is the most recently recorded record's
label). `tests/test_gaps_batch.py` carries the in-suite control
in three-legged form (canonical / mutant-reports-earliest /
mutant-as-expectation fails), and the live drill was performed
on the real module: the seam's body patched from
`records[-1][key]` to `records[0][key]` (occurrence count
asserted = 1 before patching) made **exactly 6 of 102 tests
fail** — one per family's latest-label derivation (transport,
encryption, dispatch, optimization, telemetry) plus the
control's canonical leg, all in the new batch module. The
module was restored from `scratch/extensions.py.premutation`
and verified SHA-256 identical (`ccabf122…`), suite re-ran
green. Full record in `tests/README.md`; raw mutated run in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / unchanged

- The already-closed platform-layer entry (idx 965, "Platform
  layer (hosting and the single-browser-window console)",
  closed `re-scoped` under PLATFORM-LAYER.md) is untouched, as
  are `specs/specs.json`, the core service layer, and the REST
  API — the extension surface is store-level only, following
  the sibling batch units' pattern.
- The founding negative control (the one-live-session guard
  drill on `store.py`) is untouched and still recorded in
  `tests/README.md`; this batch's control is fresh, on the new
  code only.
