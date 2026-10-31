# Tests — Law Enforcement L1 singleton build (Group 47)

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

This suite is the shipped Group 34 (Law Enforcement L2) suite,
reused: 12 of 14 files are byte-identical to Group 34's;
`lawenf_helpers.py` and `test_negative_control.py` differ by
docstring group references only (zero test-logic changes,
diff-verified; per-file SHA-256 in `../scratch/reuse-note.md`). The
code under test carries no tier strings — what changed at L1 is the
baseline claim in the spec and README, not the suite.

## Run

```bash
cd groups/law-enforcement-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 82 tests
```

Status at delivery: **82 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/member/viewer over the 9 contract actions, `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, copies-are-copies, JSONL persistence + reload (in group `scratch/`), the store recording every contract mutation action name, failed ops recording nothing |
| `test_matters.py` | Matter registry — creation shape pinned, duplicate/empty ref rejected (no id consumed), viewer cannot create; the membership boundary (outsider read/write denied, outsider lists empty, admin bypass, unknown matter 404-class); add-member rule (creator or admin only, duplicates rejected); close/reopen guards and closed-matter write rejection |
| `test_sources.py` | Source registry — shape pinned, all six kinds accepted, unknown kind rejected (no id consumed), per-matter ref uniqueness, cross-matter get is NotFound, kind filter, outsider denied |
| `test_documents.py` | Document registry — shape pinned, checksum must be 64 lowercase hex, size must be a non-negative int (bool/float rejected), duplicate ref rejected; review lifecycle `registered → in_review → reviewed` with skip/terminal transitions rejected; verify-by-content: exact bytes match, str is UTF-8-encoded, tampered bytes do not match, verify is non-mutating |
| `test_searches_annotations.py` | Saved searches & annotations — digest-only shapes (no `query`/`note` keys exist), store signatures contain no text parameter, digest/count validation, duplicate refs rejected, all three annotation target kinds, unknown kind / missing target / cross-matter target rejected, target filter |
| `test_citation_checks.py` | Citation checks — shape pinned, treatment stored **verbatim** (casing/punctuation preserved), no score/status/valid field exists, empty treatment rejected, source link must exist in the matter, repeat checks allowed |
| `test_reports_search.py` | Reporting & registry search — counts by kind/status, treatment counts keyed verbatim (`followed` ≠ `Followed`), empty-matter report; literal (non-regex) search over refs/kinds/treatments, **digests are not searchable**, outsider sees nothing, empty query rejected |
| `test_privacy.py` | The hard privacy rule — every entity's exact key set pinned; no field named for a person, subject, or content; smuggled fields (`subject_name`, `content`, `query_text`, `note_text`) rejected by the store signatures themselves; returned records are copies |
| `test_service.py` | REST API — live HTTP server: health without auth, 401 unknown user / role mismatch, 404 envelope, viewer write → 403 audited `matter_write:denied`; full flow (matter → member → source → document → review lifecycle → verify match/mismatch/bad-base64 → saved search with `query_text` hashed by the service and never stored → annotation digest → citation check verbatim → report → audit admin-only → registry search scoped by membership → closed matter rejects writes with 400) |
| `test_main_cli.py` | `python -m lawenf serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative controls (below) |
| `lawenf_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `USERS` registry, canonical digests, `fresh_store()`, and `make_store()` building a LawEnfStore + AuditLog + one matter (MEMBER's, VIEWER added as a member) |

## Negative controls

`test_negative_control.py` implements the contract's two required
mutants as store subclasses:

1. **Membership-guard mutant** (`MutantMembershipStore`):
   `_require_matter_access` performs no check, so any authenticated
   actor can read any matter. The canonical test asserts the real
   store denies the outsider (`PermissionDenied`, empty lists, empty
   search), that the mutant waves the read through, and that treating
   the mutant's outcome as the expectation raises `AssertionError`.
2. **Verify mutant** (`MutantVerifyStore`): `verify_document` reports
   `matches: True` for any content. The canonical test asserts the
   real store reports altered bytes as `matches: False`, that the
   mutant waves the tampering through, and that treating the mutant's
   outcome as the expectation raises `AssertionError`.

### Mutation verification (the drill, performed on this tree)

The first mutant was additionally drilled against the real source in
**this** tree: `LawEnfStore._require_matter_access` in
`src/lawenf/store.py` was patched to a no-op (`return`), and the
suite was run:

```
Ran 82 tests — FAILED (failures=5)
  test_matters.TestMembershipBoundary.test_outsider_read_denied
  test_matters.TestMembershipBoundary.test_outsider_scoped_write_denied
  test_sources.TestSources.test_outsider_cannot_list
  test_negative_control.TestMembershipGuardNegativeControl
      .test_canonical_denial_and_mutant_rejection
  test_service.TestFullFlow.test_flow
```

The same five failures as Group 34's drill. `store.py` was then
restored from `scratch/store.py.premutation` and verified
**SHA-256-identical** (`7e2bcade…`, recorded in
`scratch/store.py.sha256`); the suite is green again (82, OK). Raw
drill output: `scratch/mutation-run.txt`.
