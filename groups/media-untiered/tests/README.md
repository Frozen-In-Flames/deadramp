# Tests — Media, untiered (DeadRamp Phase 2, Untiered Set 27)

Run everything from this directory:

    cd groups/media-untiered
    PYTHONPATH=src python3 -m unittest discover -s tests

`media_helpers.py` builds a fresh store wired to an in-memory
audit log, with one actor per role — alice (admin), bob
(operator), carol (viewer) — and the shared fixtures (one
organization, one endpoint pair, one route, one device).

## Layout

- `test_access.py` — the roles/permissions matrix (core function
  11): admin, operator, viewer; unknown roles/users denied; the
  store enforces it on writes and on `audit_read`; a plain string
  actor carries identity without a role.
- `test_audit.py` — the audit log (core function 11): mutations
  recorded with actor/action/target; entries returned as copies;
  no update or delete API; JSONL persistence round-trips.
- `test_routes.py` — endpoint and route records (core functions
  2 and 3): reference uniqueness per organization (not across);
  references cannot be email addresses; route records hold no
  stored `state` key; route state is derived from the open
  session through the seam; endpoints must be distinct and of
  one organization; the encryption label vocabulary.
- `test_sessions.py` — stream sessions (core function 4): the
  stored record holds no `state` key; state is derived from the
  stop moment; stopping an ended session and stopping before the
  start are refused and change nothing; list filters use the
  derivation.
- `test_session_guard.py` — THE signature invariant (core
  function 4): a second start while a session is live on the
  route is refused; the refusal records nothing and consumes no
  id (the next session is `ses-2`); stopping frees the route;
  the guard is per-route.
- `test_devices.py` — devices and control actions (core
  functions 5 and 6): device shapes and org-scoped references;
  recording a control action changes nothing else — the device
  record is byte-identical afterwards and no session appears;
  the action vocabulary and filters.
- `test_profiles.py` — optimization profiles (core function 7):
  settings stored verbatim; route must share the organization;
  `enabled` must be a real boolean; toggling applies nothing to
  any route or session; the package exposes no execution entry
  point.
- `test_monitoring.py` — status snapshots and derived views
  (core functions 8 and 9): vocabularies enforced; current
  status is None without snapshots; the derivation follows
  **recording order**, so a later-recorded snapshot wins even
  with an earlier stated moment; device subjects carry their own
  status; the network status view joins derived route state with
  derived current status.
- `test_shapes.py` — pinned record shapes: a recursive scan over
  a fully populated store proves no forbidden key part exists on
  any record (score, grade, rank, email, payload, video, audio,
  ssn, password, secret, price, money, cents, latency, bitrate) —
  no field can hold media content, a score, money, or a real
  identifier; the summary is counts only.
- `test_negative_control.py` — the mutation-verified negative
  control (below).
- `test_service.py` — the REST API over real HTTP (core function
  10): health is public; unknown users and mismatched roles are
  401; the full flow exercises the session guard end to end (a
  second start is a 400 naming the live session); viewer writes
  are 403 and audited with a `:denied` suffix; audit reads are
  admin-only and themselves audited; 404/400 mapping.
- `test_main_cli.py` — the CLI entry point: demo-user wiring; a
  missing command and a bad port are errors.
- `test_specs.py` — spec integrity: membership exactly the
  census unit `untiered:Media` ({FR2218359666}); tier null on
  the sheet (`cmmc_tier` None, `fedramp_impact_level`
  "Unknown"); recorded vendor/product/status/deployment match
  forks.json and the raw cache; the claim table equals the
  expected table (6 claims) under the set's own 6-family
  taxonomy; every claim's evidence sentence appears in the
  fork's description (whitespace-normalized); the single census
  citation verifies and is the transport claim's evidence; the
  checked-absence tokens are absent from the description at
  token level; the "on-demand" token's presence in the
  network-availability sense is pinned in the other direction;
  no CMMC equivalence language appears in the sheet.

## Negative control — the one-live-session-guard drill

The signature invariant is the session guard: a route carries at
most one live session, and a second start is refused without
recording anything or consuming an id. An oracle that passes
whether or not the guard enforces would be testing that code
ran, not that the guard holds. The drill mutates the guard seam
in the real `src/media/store.py`:

    def _check_route_available(open_session):   # becomes
        return None  # MUTANT (drill): the guard never refuses

(the body that raises `ValidationError` for a start on a route
with a live session is replaced with a no-op, via
`scratch/apply_mutant.py`), then the full suite is re-run.
Result: exactly 4 failures, all guard-dependent —

- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`
- `test_session_guard.SessionGuardTests.test_second_start_refused_while_live`
- `test_session_guard.SessionGuardTests.test_refused_start_records_nothing_and_consumes_no_id`
- `test_service.ServiceTests.test_full_flow_with_session_guard`

No other test moved: the guard's other arms (stopping frees the
route, the guard is per-route) do not depend on the seam's
refusal and correctly kept passing.

After the drill, `store.py` is restored byte-identical
(SHA-256 verified:
`6162c8c0f8ce0b6615187bbc6bf1fcf211020de592c3955ff4be96d91bb92af1`,
kept at `scratch/store-pre-drill.sha256`) and the suite is fully
green again, 67/67. `test_negative_control.py` also carries the
drill's in-tree form: the same mutant applied by monkeypatch,
with the canonical check asserted to fail against it — plus the
discriminating other arm (a start on a different route IS
recorded on the real store while the first route's session is
live, so the invariant is per-route, not store-wide).
