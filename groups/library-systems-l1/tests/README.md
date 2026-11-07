# Tests — Library Systems L1

Run: `PYTHONPATH=src python3 -m unittest discover -s tests`
Result at build: **47 tests, all green.**

Each test module's docstring names the core function, spec claim, or
control family it traces to. Spec tests pin membership (exactly
F1305132147 and FR1818459251), tier fields as recorded (LI-SaaS→L1,
Low→L1), the literal claim tables (2 and 4; 6 total), verbatim claim
evidence in the cached descriptions, and the classification fields
against `remainder/nosignal_report.json` — including that each
classification sentence does NOT occur in its fork's cached
description (the two evidence streams never mix).

## Negative control (mutation-verified)

Signature invariant: a holding's active loans never exceed its
quantity, enforced by `_check_holding_availability` in
`src/librarysys/store.py`. `test_negative_control.py` carries a
mutant store whose seam performs no check: the mutant accepts an
over-quantity loan while the canonical store rejects it.

Mutation verification run: the real seam in `src/` was patched with
the mutant body (`return None`) and the full suite run. Result:
**exactly 2 failures** —
`test_circulation.CirculationTests.test_availability_seam_blocks_second_loan`
and
`test_negative_control.NegativeControlTests.test_canonical_rejects_over_quantity_loan`
(47 tests run, FAILED (failures=2); full output in
`tests/mutation-run.txt`). The store was then restored from
`tests/store.py.premutation` and verified byte-identical by SHA-256
(`tests/store.py.sha256`: b7e6dc890470afc7157c4df1a873861ac80648155859946d6b8059526f85ef63);
the restored suite is fully green.

## Final GAPS batch (test_gaps_batch.py, 19 tests; suite now 66)

Pins the extension surface of `src/librarysys/extensions.py` per
GAPS.md entry: discovery queries hold digests + result refs only
(no query-text parameter exists; `result_count` derived, never
stored); preservation records hold metadata + validated digests
with `bytes_held: False`; course lists compose core items with
`entry_count` derived; research, automation, and transport are
labeled reference records pinned to leave core workflow and
integration records deep-equal; accessibility requests are
reference records with `rendered_here`/`delivered_here: False`;
recursive scan finds no score-shaped or money-shaped key and no
float anywhere on the surface.

Fresh negative control (mutation-verified): the course-list entry
guard `_check_course_entry_absent` in `extensions.py`.
`test_gaps_batch.NegativeControlTests` carries the three-leg
control (canonical rejects a duplicate entry / no-guard mutant
subclass accepts it / mutant-as-expectation fails). Live drill:
the guard condition in the real file was patched to `if False:`
and the full suite run — **exactly 1 failure**
(`NegativeControlTests.test_canonical_rejects_duplicate_entry`;
66 tests run, FAILED (failures=1); output in
`scratch/gaps_batch_mutation_run.txt`). The module was restored
from `scratch/extensions.py.premutation`, SHA-256 verified
identical, and the suite re-ran fully green.
