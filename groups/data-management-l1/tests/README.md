# Tests — Data Management L1 singleton build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to. The suite is Group 12's (Data
Management L2), reused: 12 of 14 test files are byte-identical to
Group 12's, and the 2 differing files differ in documentation wording
only (see `../scratch/reuse-note.md`). No test logic changed. What the
suite verifies does not change with the tier — the substrate's
behavior is identical; what changes at L1 is the baseline the
behavior is claimed against (UNION-SPEC.md), not the code.

## Run

```bash
cd groups/data-management-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 196 tests
```

Status at delivery: **196 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/steward/viewer stated over `PERMISSIONS`/`ACTIONS` (admin = all actions; steward = all except `audit_read`; viewer = all `*_read` except `audit_read`, plus `access_request` only), the nine pinned write actions, `permissions_for()`, `can()`, `require()`, unknown role/action denied, None user denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording each mutation action (dataset_create … export_create, search), failed ops record nothing |
| `test_datasets.py` | Datasets — creation shape/provenance/defaults, `ds-` ids, all classifications, schema validation (bad type, duplicate field names, all pinned types), `update_dataset`, `update_schema` version bump, viewer/None write denied with no id consumed, get/list sorted, unknown id → `NotFoundError`, plain-string actor identity |
| `test_sources_ingestion.py` | Sources + ingestion + provenance — `src-` creation and kind validation, `ing-` happy path/defaults/modes/statuses, unknown dataset/source → `NotFoundError`, bad mode/status/record_count (incl. bool and negative) → `ValidationError` with no id consumed, provenance totals over completed ingestions only |
| `test_quality.py` | Quality rules + checks — `qr-` creation and per-kind params validation (format pattern required and compiling, range min and/or max numeric, freshness `max_age_hours > 0`); one hand-computed check run per kind (completeness, uniqueness, format `^[A-Z]{2}\d{4}$` under fullmatch, range with inclusive edges, freshness at a fixed ISO `now` incl. the exactly-max-age pass), `passed` flag, `qc-` ids, viewer run denied |
| `test_access_governance.py` | Access requests + grants — `ar-` request flow and duration bounds, duplicate pending rejected, self-decision → `PermissionDenied` (request still `requested`, no grant; also for an admin requester), steward approves another's request → `gr-` grant fields + expiry math (expires = created + duration_days), deny path consuming no grant id, deciding a non-pending request → `ValidationError`, revoke + double-revoke, `active_grants` expiry/revocation filtering with explicit `now` |
| `test_retention.py` | Retention policies — `rp-` set/get/list, duplicate policy per dataset rejected with no id consumed, update (full/partial/invalid), dispositions, `retention_policy_for` → None, due computation with explicit `now` (reference = latest completed ingestion, else dataset creation; failed ingestion is not a reference; exactly-at-retention not due; `legal_hold` excluded) |
| `test_export.py` | Exports — `ex-` manifest with records (record_count + checksum equal to the locally computed sha256 of the canonical JSON), key-order independence, csv, empty records; without records (count from completed ingestions, checksum None, current schema_version); bad format and viewer export denied with no id consumed; get/list |
| `test_search.py` | Search — datasets by name/description/tag/schema field name, sources by name/kind/location, quality rules by name/field/kind; case-insensitive; literal (regex metacharacters neither match nor explode); blank query → all empty; non-string query → `ValidationError` |
| `test_service.py` | REST API — live HTTP server: health (no auth), 401 unknown user + role mismatch, 403 viewer dataset create (denied attempt audited `<action>:denied`), full flow (dataset → source → ingestion → quality rule → check → access request by carol → decide by bob → grants list → retention policy → retention-due → export → search → audit as alice; audit as bob/carol → 403), 400/404 error envelopes |
| `test_main_cli.py` | `python -m datamgmt serve --port <free>` subprocess (PYTHONPATH=src), waits for health, answers alice on `/audit` and carol/bob on `/datasets`, terminates |
| `test_negative_control.py` | Negative control (below) |
| `datamgmt_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, STEWARD=bob/steward, VIEWER=carol/viewer), `USERS` registry, `fresh_store()`, and `make_store()` building a DataMgmtStore + AuditLog + the canonical dataset ("Claims Extract", cui, tags [claims, nightly], schema patient_id/amount, created by STEWARD) + the canonical source ("ehr-feed", api, ehr.internal, registered by STEWARD) |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `DataMgmtStore` subclass (`MutantDataMgmtStore`) whose
`_check_decider_not_requester` is a no-op — the separation-of-duties
check is skipped. The traced claim, named in the module's docstrings,
is that **access decisions are never self-approved** (control family
AC-3 access enforcement; the never-self-approve rule is a design
property of the carried substrate — at L2 it traced to a sibling's
evidenced governance claim, but no sibling exists in this singleton
group, so here it stands as the substrate's own rule; AC-5 is named
as the separation-of-duties family home, as design lineage only —
AC-5 is not itself a Low-baseline selection). For each canonical
case (viewer requester, steward requester) the test asserts three
things: the canonical expectation (`PermissionDenied` from the real
implementation, the request staying `"requested"`, and no grant
existing), that the mutant would NOT produce that expectation (it
approves the self-decision and creates the grant), and — via a
literal `assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails.

One isolation detail, documented in the test itself: a viewer decider
is also independently barred by the `access_decide` permission, so the
viewer case's mutant leg presents the requester's own identity (the
name "carol", which is what the name-based self-decision check
compares) in a role holding `access_decide` — `User("carol",
"steward")` — making `_check_decider_not_requester` the only gate
that can deny. The canonical legs assert `PermissionDenied` for both
the plain `VIEWER` decider and that name-identical decider on the
real store, and a third test confirms a *different* steward deciding
carol's request succeeds on the real store, so the denial is the
self-decision check firing rather than a blanket refusal.

Mutation verification: VERIFIED for this group (2026-10-25). The
self-approval guard in `DataMgmtStore._check_decider_not_requester`
(`src/datamgmt/store.py`) was patched to a no-op (`return None`), the
exact live counterpart of the mutant in `test_negative_control.py`,
so a requester could approve their own access request and mint their
own grant. The full suite was run: **196 tests ran, exactly 4
failed** — the same four as Group 12's drill:

- `test_access_governance.TestDecideAccess.test_admin_self_decision_also_denied`
- `test_access_governance.TestDecideAccess.test_self_decision_denied_request_stays_requested_no_grant`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_steward_self_decision_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_viewer_self_decision_denied_canonical_but_mutant_approves`

`store.py` was then restored from a pre-mutation copy (SHA-256
`dc35677ccdaf4d416a10a5364128f54bb1b1802fd8a99c00271ad081caf2774e` —
identical to Group 12's recorded hash, since the file is
byte-identical to Group 12's) and the suite re-run: **196 tests,
OK**. Full drill output: `../scratch/mutation-run.txt`; pre-mutation
copy and hash: `../scratch/store.py.premutation`,
`../scratch/store.py.sha256`. The suite catches this defect class;
the negative control is not decorative.

## Remainder addition — unit `addition:data-management-l1`

`test_additions.py` (11 tests) pins the addition of DevResults /
DevResults (FR2100845343) under the group's 19-family taxonomy
applied verbatim (parsed via `ast` from `../scratch/extract.py`
and asserted equal to the Group 12 parent's taxonomy in
`../scratch/additions_extract.py`, which also reproduces the
original fork's shipped sheet deep-equal before tagging): sheet
count and append order (2 sheets, original first), unit
membership against `../../remainder.json`, the literal claim
tables (the newcomer's is empty and the original's is exactly as
shipped — the group is 0 claims across 2 forks), the zero-claim
set (all 19 families), the census citations (2 / 2 verbatim in
the description; both tag nothing — verification is not a
claim), registry fields as published, the near-miss pins
("data capture" vs. `ingestion_collection`; "analysis,
reporting, visualizations" vs. `query_reporting`; consolidation
prose vs. `integration_exchange`), and the group totals (2 forks
/ 0 claims / 0 of 2 claiming / LI-SaaS 2). Two substrate cases
exercise the shipped Core in the newcomer's shape: a
partner-results flow (indicator/value dataset, manual
field-reports source, completed 1,200-record and failed
50-record ingestions, provenance over completed runs only, a
checksummed export manifest, catalog search by tag and by
schema field name) and an access-governance flow (carol's
request for the results dataset, the self-decision denial, the
steward's approval minting exactly one grant). Both are
carried-substrate cases: the fork claims no family.

**Drill re-run in this tree (additions).** The core is
unchanged, so the group's signature drill was re-run: the
self-approval guard in `DataMgmtStore._check_decider_not_requester`
(`../src/datamgmt/store.py`) was patched to a no-op
(`return None`) — the exact mutation recorded above, applied as
a scoped replacement of the guard's body with the target text
asserted to occur exactly once — and the full suite ran:
**207 tests, exactly 5 failures** — the shipped drill's 4 plus
exactly 1 from the additions module:

- `test_access_governance.TestDecideAccess.test_admin_self_decision_also_denied`
- `test_access_governance.TestDecideAccess.test_self_decision_denied_request_stays_requested_no_grant`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_steward_self_decision_denied_canonical_but_mutant_approves`
- `test_negative_control.TestNegativeControlMutantSelfApproval.test_viewer_self_decision_denied_canonical_but_mutant_approves`
- `test_additions.TestDevResultsSubstrate.test_access_to_results_dataset_is_never_self_approved`

`store.py` was then restored from the pre-mutation copy
(`../scratch/store.py.premutation-additions`) and verified
SHA-256-identical to the shipped hash
(`dc35677ccdaf4d416a10a5364128f54bb1b1802fd8a99c00271ad081caf2774e`);
the suite re-ran green: **207 tests, OK**. All 7 `datamgmt`
modules are SHA-256-identical to their pre-addition hashes
(`../scratch/additions_src_hashes_before.txt` /
`additions_src_hashes_after.txt` — diff empty). Raw drill
output: `../scratch/additions_mutation_run.txt`.

## Final GAPS batch — unit `Singleton 38` (this group's own section)

`test_gaps_batch.py` (32 tests) pins the extension surface in
`../src/datamgmt/extensions.py` (`DataMgmtExtensions` wrapping the
core store; dispositions in `../BATCH.md`). Per entry: crawl
targets as definitions (`captured_here: False`, unknown
dataset/source rejected with no id consumed, viewer denied with
the denial audited `ext_crawl_target_define:denied`); captures
bound to exactly one core ingestion of the target's dataset
(cross-dataset and duplicate bindings rejected; the capture's key
set pinned — no counts, no checksum, no content); the archive
summary derived at read (counts from the extension records, the
record total from core provenance over completed ingestions only);
render profiles and reports as a labeled reference
(`reference_stub: True`, `rendered_here: False`, bad mode rejected
with no id consumed); monitors and change reports as a labeled
reference (outcomes verbatim, `detected_here: False`); seals
carrying the core ingestion's checksum read at seal time (`None`
stated when the core recorded none; duplicate seal rejected);
replay requests as labeled transport records
(`reference_transport: True`, `replayed_here: False`); content
indexes and snapshots as a labeled reference (latest reported
figure derived at read; a pin that the core's metadata search
still runs and the extension exposes no content-search method).

### Negative control (fresh, for the new code)

`test_gaps_batch.py`'s `TestSealingNegativeControl` implements
this unit's mutant: a `DataMgmtExtensions` subclass
(`MutantExtensions`) whose `_check_sealer_not_recorder` is a
no-op — the separation-of-duties check is skipped, so a capture's
recorder could seal their own capture. The traced claim is this
unit's separation-of-duties rule in its new surface (AC-3 access
enforcement at this tier; AC-5 named as the separation-of-duties
family home, as design lineage only — AC-5 is not a Low-baseline
selection), mirroring the core's signature
`_check_decider_not_requester` guard. The test asserts the
canonical expectation (`PermissionDenied` from the real
implementation, no seal created, a different actor's seal then
succeeding with the core checksum), that the mutant would NOT
produce that expectation (it seals, as the recorder), and — via a
literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails.

Mutation verification: VERIFIED for this unit (2026-11-07). The
sealer/recorder seam in `DataMgmtExtensions._check_sealer_not_recorder`
(`src/datamgmt/extensions.py`) was patched to a no-op
(`return None`) — the exact live counterpart of the mutant in
`test_gaps_batch.py` — with the target text asserted to occur
exactly once. The full suite was run: **239 tests ran, exactly 2
failed**, both in the new module:

- `test_gaps_batch.TestArchiveSealing.test_recorder_cannot_seal_own_capture`
- `test_gaps_batch.TestSealingNegativeControl.test_canonical_recorder_denied_other_seals`

`extensions.py` was then restored from the pre-mutation copy
(`../scratch/extensions.py.premutation`) and verified
SHA-256-identical (`092befdc0ad14a131138e2acf7d9fef445f4977be5eb6838caff57fcf97ac767`;
hash recorded in `../scratch/extensions.py.sha256`); the suite
re-ran green: **239 tests, OK**. Full drill output:
`../scratch/gaps_batch_mutation_run.txt`. All 7 pre-existing
`datamgmt` modules are SHA-256-identical to their pre-batch
hashes (`../scratch/gaps_batch_src_hashes_before.txt`).

## Final GAPS batch — second unit: Remainder Addition — Data Management L1

`test_gaps_batch_addition.py` (33 tests) pins the second
extension surface in `../src/datamgmt/extensions_addition.py`
(`DataMgmtExtensionsAddition` wrapping the core store; audit
actions prefixed `exta_`; dispositions in
`../BATCH-ADDITION.md`). Per entry: results frameworks as
definitions (`measured_here: False`, `values_held: False`; the
stored record's key set pinned — no count, total, or status;
unknown dataset refused with no id consumed; viewer refused
with the denial audited `exta_framework_define:denied`);
indicators as definitions (name unique per framework,
baseline/target figures held verbatim as declared, bool figures
refused); progress reports bound to exactly one core ingestion
of the framework's dataset (cross-dataset and duplicate
bindings refused; outcome and reported value stored verbatim,
`measured_here` / `computed_here`: False); the results summary
derived at read (counts, per-outcome tallies, latest reported
outcome/value, and the core provenance total over completed
ingestions only — a failed ingestion contributes nothing);
collection instruments as definitions (kind enum, bad kind
refused with no id consumed); instrument fields as shapes (the
field record's key set pinned — no value slot; duplicate names
and bad kinds refused); capture runs binding an instrument to
a core ingestion, taking dataset and source from the core
record (duplicate binding refused; negative reported counts
refused); the instrument summary derived at read (the reported
total stated as a sum of reported counts, count-less runs
tallied separately). The substrate's hard privacy rule is
pinned over the whole surface: a recursive scan finds no
content-shaped key (`content`, `payload`, `response`,
`response_value`, `answer`, `records`, `respondent`, …) on any
record or view, and no collection, submission, rendering,
measurement, or execution method exists on the class.

### Negative control (fresh, for the new code)

`test_gaps_batch_addition.py`'s
`TestLatestReportNegativeControl` implements this unit's
mutant: a `DataMgmtExtensionsAddition` subclass
(`MutantExtensionsAddition`) whose `_latest_progress_report`
returns the *earliest* report (`reports[0]`) instead of the
latest. The traced claim is that the results summary's latest
reported outcome and value are the most recent progress
report's — the derivation the M&E surface's honesty rests on,
since a summary silently reading the earliest report would
misstate reported progress while looking well-formed. The test
asserts the canonical expectation (latest outcome
`reported_on_track`, latest value 2750, from the real
implementation), that the mutant would NOT produce it (it
reads `reported_progressing` / 1900), and — via literal
`assertRaises(AssertionError)` legs — that treating the
mutant's outcome as the expected outcome fails.

Mutation verification: VERIFIED for this unit (2026-11-07).
The latest-report seam in
`DataMgmtExtensionsAddition._latest_progress_report`
(`src/datamgmt/extensions_addition.py`) was patched live to
return `reports[0]` — the exact live counterpart of the mutant
in `test_gaps_batch_addition.py` — with the target text
asserted to occur exactly once. The full suite was run:
**272 tests ran, exactly 2 failed**, both in the new module:

- `test_gaps_batch_addition.TestResultsSummary.test_summary_derives_counts_latest_and_core_total`
- `test_gaps_batch_addition.TestLatestReportNegativeControl.test_canonical_summary_reads_latest_report`

`extensions_addition.py` was then restored from the
pre-mutation copy (`../scratch/extensions_addition.py.premutation`)
and verified SHA-256-identical
(`446adcc7f4132432534a5e38674f3f7000c1ecb50ce24b4b48f073ffa7cef844`;
hash recorded in `../scratch/extensions_addition.py.sha256`);
the suite re-ran green: **272 tests, OK**. Full drill output:
`../scratch/gaps_batch_addition_mutation_run.txt`. All 8
pre-existing `datamgmt` modules (the 7 core modules and the
first unit's `extensions.py`) are SHA-256-identical to their
pre-build hashes (`../scratch/prebatch-addition-src.sha256`).
