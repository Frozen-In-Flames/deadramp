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
