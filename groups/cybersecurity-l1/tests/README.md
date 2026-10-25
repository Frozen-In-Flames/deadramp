# Tests — Cybersecurity & Risk Management L1 merged build (Group 16)

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Reuse

This build is an explicit, in-full reuse of our own shipped Group 4
(Cybersecurity & Risk Management L2) code — Operation DeadRamp,
Apache-2.0, ours. The implementation is functionally tier-neutral, so
the same code ships here unchanged. The **code** is reused in full;
the **baseline claim is NOT reused**. Everything Group 4 says about
Moderate / NIST SP 800-171 stays in Group 4. This group's claims are
the **Low baseline (NIST SP 800-53 Rev. 5 Low) / FAR 52.204-21**
only, as written fresh for CMMC L1 in the group `README.md`.

### SHA-256 byte-identical summary

Computed file by file against Group 4
(`groups/cybersecurity-l2/`) after the copy, before any other work:

- **`src/` — 8 of 8 `.py` files byte-identical.** No `src/` file was
  changed at all.

  | File | SHA-256 (identical in L1 and L2) |
  |---|---|
  | `src/cyber/__init__.py` | `8066a9eff6250bd8079dde87585401c9b78e835875db3d9b6a0d38ba109f05c2` |
  | `src/cyber/__main__.py` | `660a9196cb404b7e02101d5a0a0438f6f922b015406040a67f93cc2e29459a9b` |
  | `src/cyber/access.py` | `c9d4559e85fa8d62fdf33fffbd2f0437bd314a04bfdcab1711f5a1f9228d9e88` |
  | `src/cyber/audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
  | `src/cyber/catalog.py` | `a9afe439050d36ab4e5b26309d63ee8ec0c6cf38bd286acb893eab68084afd3e` |
  | `src/cyber/errors.py` | `4540b5f56b7eb2883bf1e28aa8819aaea0369fe8f4a766b7e448c762e3c2cd1f` |
  | `src/cyber/service.py` | `1e79939470a51a1a3a3a990b81335c386fdd1b0785fbbcbf4d388c332144bec5` |
  | `src/cyber/store.py` | `f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de` |

  The only tier word found in Group 4's `src/` is the generic
  caveat in `catalog.py` ("it is not a FedRAMP authorization or a
  CMMC certification"), which stays true at L1 and is kept verbatim.

- **`tests/` — 14 of 15 `.py` files byte-identical.** The one
  differing file is documentation wording only, no code changed:

  - `tests/cyber_helpers.py` differs (L1 SHA-256
    `bd0eddb272ed039d73e7e39d33bb1072fface81b1013e18c3fc9e80937eeda51`
    vs. L2 `73875e9d6239039d2b4279773856cdc586da99017712669199553623945818d1`):
    its module docstring said "Cybersecurity & Risk Management L2
    test suite" and "Collaboration L2 group"; both were changed to
    L1. That was the only L2/Moderate-specific text found in any
    copied test file — a grep of all other `tests/*.py` for
    L2/Moderate/CMMC/FedRAMP text found none, and none was changed.
  - All other test files, including `tests/__init__.py` (empty) and
    all 13 `test_*.py` files, are byte-identical to Group 4's.

  The full per-file hash table for both trees is kept at
  `../scratch/reuse-hashes.txt`.

High-only apparatus check (Group 8, cybersecurity-l3): a grep of
this tree's `src/` and `tests/*.py` for `prev_hash`, `verify_chain`,
hash-chained audit, fail-closed audit, lockout, and auditor role
found **none**. The roles in `access.py` are exactly
`admin`/`analyst`/`viewer`, the demo users are exactly
alice/bob/carol, and the service layer's audit helper explicitly
never breaks the request path on an audit error (the opposite of
fail-closed). (The string `dana` appears once in `test_access.py`
only as an arbitrary `User("dana", "analyst")` name fixture — no
auditor role or user exists in this build.)

## Run

```bash
cd groups/cybersecurity-l1
PYTHONPATH=src python3 -m unittest discover -s tests
```

Status at delivery: **194 tests, OK** against the implementation in
`../src/`, verified by a run in this tree (2026-10-25).
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

VERIFIED in this Group 16 tree (2026-10-25), as a fresh drill, not
copied from Group 4's record:

1. **Backup:** `src/cyber/store.py` was copied to
   `scratch/store.py.premutation` (SHA-256
   `f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de`,
   identical to the L2 original at backup time).
2. **Mutant applied:** in `score_finding` (`src/cyber/store.py`),
   the scoring line was replaced, signature kept, with a
   severity-blind constant:

   ```python
   score = 3 * CRITICALITY_WEIGHTS[criticality]
   ```

   Every severity is weighted 3 regardless of its actual severity,
   so a finding's score depends only on asset criticality.
3. **Mutant run:** the full suite was run exactly as in *Run*
   above and the output kept at `../scratch/mutation-run.txt`:
   **194 tests ran, 31 failed** (`FAILED (failures=31)`). The
   failures span every score-dependent surface: test_scoring (the
   canonical pair, the three band edges, the just-below-edges case,
   and 16 subTests of the literal 5×4 table — every severity except
   medium, whose real weight happens to be 3), the negative control
   itself (3), asset-criticality rescoring in test_assets (2),
   ingest score assertions (1), finding sort order in test_search
   (1), posture `top_open` (1), and the HTTP full flow in
   test_service (1).
4. **Restore verified:** `store.py` was restored from
   `scratch/store.py.premutation`; its SHA-256 is again
   `f692fc74e9366e8fcdf2ba1d869632492676bf55c30fb3dc921bc0c60cedc5de`,
   verified identical to the pre-mutation hash and to the Group 4
   L2 original (`diff` empty).
5. **Re-run green:** **194 tests, OK**.

For comparison, Group 4's record for the weight-1 live mutant
(`score = 1 * CRITICALITY_WEIGHTS[criticality]`) was 30 failures.
The count differs here (31) because this drill used the constant-3
mutant specified for this group, not because the suite differs —
apart from the `cyber_helpers.py` docstring, the suite is
byte-identical to Group 4's. The suite catches this defect class;
the negative control is not decorative.

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
  contract pins (`{"assets": [...]}`, `{"findings": [...]}`, `{"risks": [...]}`, `{"controls": [...]}`, `{"entries": [...]}`),
  and `/search` / `/posture` as the bare summary/result dicts the
  contract specifies.
