# Tests — Cybersecurity & Risk Management L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/cybersecurity-l2
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **194 tests, OK** against the implementation in
`../src/`, verified by the coordinator's own run (2026-10-25).
(Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers (UNION-SPEC Core) |
|---|---|
| `test_access.py` | 10 Access control — exact permission matrix for admin/analyst/viewer (8 actions; analyst = 6, viewer = read only), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | 11 Audit log — entry keys, append-only, JSONL file + reload on construction, and the store recording each mutation action (`asset_create`, `asset_update`, `finding_ingest`, `finding_transition`, `finding_assign`, `risk_create`, `risk_transition`, `control_assess`, `search`), incl. ingest/transition/assess/search `details` payloads and posture_summary not auditing |
| `test_assets.py` | 1 Asset inventory — creation shape/provenance, every kind accepted, kind/criticality/tags validation, `q` filter over name/owner, update + criticality change rescoring that asset's findings only, failed ops consume no ids |
| `test_ingest.py` | 2 Finding ingestion — single finding shape + score/band from `score_finding`, defaults cve None/control_ids [], unknown asset → `ValidationError`, bad severity/control id → `ValidationError`, bulk atomicity (one bad item creates nothing, consumes no ids, one audit entry), empty bulk → `ValidationError`, CSV ingest incl. semicolon `control_ids` parsing and malformed CSV → `ValidationError` |
| `test_lifecycle.py` | 3 Finding triage & lifecycle — the exact `FINDING_TRANSITIONS` map, every allowed transition succeeds, a representative forbidden set → `ValidationError` incl. closed terminal and same-status, assign/unassign |
| `test_scoring.py` | 4 Risk scoring — the full 5×4 `score_finding` table written out literally, canonical pairs (critical,critical)=(10.0, critical) and (info,critical)=(2.0, low), band edges 8/5/2.5, published constants, `risk_score`/`risk_band` edges 15/10/5 |
| `test_risks.py` | 5 Risk register — create shape and 1–25 scoring, likelihood/impact validation incl. booleans rejected and out-of-range, unknown `finding_ids` → `ValidationError`, the exact `RISK_TRANSITIONS` map incl. closed→open reopen, list filters and sort by score desc / id asc |
| `test_controls.py` | 6 Control mapping & assessment — catalog has exactly 34 controls with pinned titles, `CONTROL_IDS`/`control_by_id`, `list_controls` initial state, `finding_count` reflects linked findings, `assess_control` happy path + unknown id → `NotFoundError` + `"not_assessed"` → `ValidationError`, posture controls coverage math (assessed/implemented/coverage_pct) |
| `test_search.py` | 7 Search & filtering — cross-object substring search over findings/assets/risks, case-insensitivity, per-field matching, and `list_findings` filter scoping (severity/status/asset_id/source/q, combined as intersection) with sort score desc / id asc |
| `test_posture.py` | 8 Posture reporting — summary shape with every `by_*` bucket present with zeros on an empty store, open count excludes closed/false_positive, `top_open` limited to 5 and sorted, risk/asset bucket counting |
| `test_service.py` | 9 API access — live HTTP server on an ephemeral port: `/health`, 401 unknown user and role mismatch, 403 viewer ingesting, full flow (asset → finding → bulk → CSV → transition → assign → risk → risk transition → control assess → posture → search → audit), `audit_read` admin-only over HTTP, denied attempts audited with `:denied` |
| `test_main_cli.py` | `python -m cyber serve` subprocess with demo users alice/bob/carol answering `/health`, `/assets`, `/posture` and `/audit` |
| `test_negative_control.py` | Negative control (below) |
| `cyber_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, ANALYST=bob/analyst, VIEWER=carol/viewer), `make_store()` building a CyberStore + AuditLog + one asset (`core-server-01`, criticality high) + one ingested finding (high severity, score 6.0/high), plus `fresh_store()`, `make_asset()`, `sample_finding_item()`, `ingest_sample_finding()` and `create_sample_risk()` |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a severity-blind scoring function that weights **every** severity 1,
so a finding's score depends only on asset criticality. The traced
claim, named in the module's docstrings, is that severity must move
the score: a critical finding and an informational finding on the same
asset cannot score alike. For the canonical pair the test asserts the
real `score_finding` separates them (`("critical","critical")` →
`(10.0, "critical")`; `("info","critical")` → `(2.0, "low")`), that
the mutant collapses both to 2.0, and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's output as
the expected output fails. An end-to-end arm repeats the separation
through the store: findings ingested on the same (critical) asset with
severities critical vs info carry different scores and bands in the
store, and the mutant's prediction for the critical finding is shown
to fail as an expectation.

## Mutation verification

VERIFIED by the coordinator (2026-10-25). The scoring line in
`CyberStore`'s module (`src/cyber/store.py`, function
`score_finding`) was patched to `score = 1 *
CRITICALITY_WEIGHTS[criticality]` — the exact live counterpart of the
severity-blind mutant in `test_negative_control.py` — and the full
suite was run: **194 tests ran, 30 failed**. The failures span every
score-dependent surface: the literal 5×4 table in test_scoring (16
subTest failures), the band-edge cases, the negative control itself,
ingest score assertions, asset-criticality rescoring (both the
rescored asset and the untouched-other-asset arm), finding sort
order, posture `top_open`, and the HTTP full flow. `store.py` was
then restored from a pre-mutation copy (SHA-256
f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de,
verified identical to the pre-mutation hash) and the suite re-run:
**194 tests, OK**. The suite catches this defect class; the negative
control is not decorative.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite follows the
contract's most literal reading and stays tolerant of the remaining
freedom:

- `make_store()` returns `(store, asset, finding)`: the asset and the
  finding are returned as dicts so tests can assert on their ids and
  scores without a second lookup.
- Audit `details` defaults are accepted as `None` or `{}` (the
  contract types the parameter `details=None`).
- An empty CSV `cve` cell leaves the finding's `cve` unset: `None` is
  asserted as the primary reading (the JSON-ingest default), with the
  raw empty string also accepted — the contract pins an empty-cell
  rule explicitly only for `control_ids` (empty cell = `[]`), which
  the CSV tests assert exactly.
- Unknown-role handling in `permissions_for()` / `can()` is accepted
  either as a denying raise or as an empty/`False` result;
  `require()` must raise `PermissionDenied`. Unknown actions must be
  denied to everyone, admin included (asserted exactly).
- Over HTTP, statuses the contract does not pin (finding transition,
  assign, risk transition, control assess, asset update) are accepted
  as 200 or 201; creation endpoints the contract does pin to 201 are
  asserted as 201, and auth failures are asserted as exactly 401 per
  the contract ("unknown user or mismatched role → 401").
- List/read endpoints over HTTP are asserted with the wrappers the
  contract pins (`{"assets": [...]}`, `{"findings": [...]}`,
  `{"risks": [...]}`, `{"controls": [...]}`, `{"entries": [...]}`),
  and `/search` / `/posture` as the bare summary/result dicts the
  contract specifies.
