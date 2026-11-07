# Tests — Marketing & Sales, untiered (DeadRamp Phase 2, Untiered Set 18)

Run everything from this directory:

    cd groups/marketing-sales-untiered
    PYTHONPATH=src python3 -m unittest discover -s tests

`marketsales_helpers.py` builds a fresh store wired to an in-memory
audit log, with one actor per role — alice (admin), bob (operator),
carol (viewer) — and the shared fixtures (one organization, one
opportunity, one contact list, one segment, one campaign).

## Layout

- `test_access.py` — the roles/permissions matrix (core function 15):
  admin, operator, viewer; unknown roles/users denied; the store
  enforces it on writes and on `audit_read`.
- `test_audit.py` — the audit log (core function 15): mutations
  recorded with actor/action/target; entries returned as copies;
  JSONL persistence round-trips.
- `test_opportunities.py` — opportunity and evaluation records (core
  functions 2 and 3): references unique per organization; moments
  validated, failed writes consume no id; decisions from the fixed
  vocabulary; a recursive shape check proves no score/grade/fit
  field exists on an evaluation record.
- `test_pipeline.py` — pipeline and content records (core functions
  4 and 5): the legal stage path to `awarded`; illegal jumps and
  terminal-stage moves refused with the record unchanged; versions
  unique per (opportunity, item); version/size types validated
  (bools rejected); the content record's key set is pinned exactly —
  no field can hold proposal text.
- `test_workflows.py` — the workflow registry (core function 6):
  registering or toggling a workflow changes nothing but the
  registry and the audit log, and the package exposes no execution
  entry point — records only, never executes.
- `test_campaigns.py` — list/segment/campaign records (core
  functions 7, 8, 9): list records hold counts only; campaign status
  is derived at read through the `_derive_campaign_status` seam and
  the stored record provably has no `status` key; derivation order
  reported > delivered > scheduled > draft; segment and list must
  belong to the campaign's organization; the status filter uses the
  derivation.
- `test_suppression_gate.py` — THE signature invariant (core
  functions 10 and 11): a `delivered` outcome is refused for a
  contact under an active suppression on the campaign's list, and
  the refused attempt records nothing and consumes no id; `bounced`
  and `deferred` remain recordable; release re-opens delivery; a
  suppression recorded after a delivery does not rewrite it;
  suppression is per-list; at most one active suppression per
  (list, contact); reasons from the fixed vocabulary; contact
  references cannot be email addresses or carry whitespace.
- `test_engagement.py` — engagement records, the report, search,
  and the summary (core functions 12 and 13): the report carries
  counts only — no key names a rate, score, or percentage.
- `test_negative_control.py` — the mutation-verified negative
  control (below).
- `test_shapes.py` — pinned record shapes: a recursive scan over a
  fully populated store proves no forbidden key part exists
  anywhere (score, grade, rank, rate, email, body, content text,
  ssn, password, secret).
- `test_service.py` — the REST API over real HTTP (core function
  14): health is public; unknown users and mismatched roles are
  401; the full flow exercises the suppression gate end to end (a
  `delivered` attempt for a suppressed contact is a 400 naming the
  suppression); viewer writes are 403 and audited with a `:denied`
  suffix; audit reads are themselves audited; 404/400 mapping.
- `test_main_cli.py` — the CLI entry point: demo-user wiring; a
  missing command and a bad port are errors.
- `test_specs.py` — spec integrity: membership exactly the census
  unit `untiered:Marketing & Sales` ({FR2700857472, FR2700857469});
  tier null on every sheet (`cmmc_tier` None,
  `fedramp_impact_level` "Unknown"); recorded vendor/product/status
  match forks.json; the claim tables equal the expected tables
  (CLEATUS 6, Zeta 7, total 13) under the set's own 13-family
  taxonomy; every claim's evidence sentence appears in the fork's
  description (whitespace-normalized); both census citations per
  fork verify; the checked-absence tokens are absent from both
  descriptions at token level; no CMMC equivalence language appears
  in any sheet.

## Negative control — the suppression-gate drill

The signature invariant is the delivery gate: a `delivered`
outcome may not be recorded for a contact under an active
suppression. An oracle that passes whether or not the gate
enforces would be testing that code ran, not that the gate holds.
The drill mutates the gate seam in the real
`src/marketsales/store.py`:

    def _check_delivery_allowed(active_suppression, outcome):   # becomes
        return None

(the body that raises `ValidationError` for a `delivered` outcome
under an active suppression is replaced with a no-op), then the
full suite is re-run. Result: exactly 3 failures, all
gate-dependent —

- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`
- `test_suppression_gate.SuppressionGateTests.test_delivered_refused_for_suppressed_contact`
- `test_service.ServiceTests.test_full_flow_with_suppression_gate`

No other test moved: the gate's other arms (bounced/deferred
recordable, release re-opens, per-list scope) do not depend on the
seam's refusal and correctly kept passing.

After the drill, `store.py` is restored byte-identical
(SHA-256 verified) and the suite is fully green again.
`test_negative_control.py` also carries the drill's in-tree form:
the same mutant applied by monkeypatch, with the canonical check
asserted to fail against it — plus the discriminating other arm
(a `bounced` outcome for the same suppressed contact IS recorded
on the real store, so the invariant is outcome-specific, not
contact-wide).

## Final GAPS batch additions

- `test_gaps_batch.py` — the batch extension surface
  (`src/marketsales/extensions.py`, `MarketSalesExtensions`):
  per-entry pins for the section's eight entries (idx 912–919).
  Reference families (AI requests/reports/evaluations and agent
  definitions; discovery feeds and their reported counts;
  proposal-generation requests and reports; workflow-execution
  requests and reports; segmentation requests and reports; send
  requests and transport receipts) are pinned stub-labeled
  (`reference_stub: True`, transports also
  `reference_transport: True`), with result content and drafted
  text refused by signature (`TypeError`), core records pinned
  deep-equal where a request or report binds one (workflow,
  segment, content versions), and receipts pinned to create no
  core delivery and move no campaign status. Built families
  (intelligence/forecast reports and the derived market view;
  handling rules, the derived handling queue, handling records,
  template metadata, preferences with the current value derived
  at read) are pinned as records and derivations over the core's
  own records. Cross-cutting pins: a recursive scan proves no
  tier / baseline / equivalence key and none of the core's
  forbidden key parts exists anywhere on the extension surface;
  RBAC rides the core matrix (a viewer's denied write consumes
  no id); extension mutations land on the core audit log as
  `ext_*`; and a failed audit write rolls the record and its id
  back.

## Negative control — the handling-coverage drill (batch)

The batch's fresh invariant is the derived handling queue: a
bounced delivery (or an active complaint suppression) stays in
the queue until a handling record covers its (list, contact,
trigger) key. An oracle that passes whether or not coverage is
read would be testing that code ran, not that the queue drains.
The drill mutates the coverage seam in the real
`src/marketsales/extensions.py`:

    def _handling_covered(covered_keys, key):   # becomes
        return True

(the membership check is replaced with a constant, so every
candidate counts as handled and the queue is always empty), then
the full suite is re-run. Result: exactly 5 failures, all
queue-dependent —

- `test_gaps_batch.NegativeControlTests.test_canonical_check_passes_on_the_real_surface`
- `test_gaps_batch.HandlingTests.test_bounced_delivery_enters_the_queue`
- `test_gaps_batch.HandlingTests.test_complaint_suppression_enters_the_queue`
- `test_gaps_batch.HandlingTests.test_handling_record_drains_only_its_own_item`
- `test_gaps_batch.NegativeControlTests.test_queue_is_trigger_specific_on_the_real_surface`

No other test moved: the queue's other arms (a handling record
creates no core suppression; preferences derive through their
own seam) do not depend on the coverage check and correctly kept
passing.

After the drill, `extensions.py` is restored byte-identical
(SHA-256 verified) and the suite is fully green again.
`test_gaps_batch.py` also carries the drill's in-tree form: the
same mutant applied by monkeypatch, with the canonical check
asserted to fail against it — plus the discriminating other arm
(a `delivered` outcome raises no queue item, and releasing a
complaint suppression removes its item, so the queue tracks
unhandled bounce/complaint facts, not contacts).
