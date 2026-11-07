# Final GAPS batch — Untiered Set 12, Legal & Policy (tier null)

Date: 2026-11-07. This unit's section of `../../GAPS.md` is
headed, verbatim, **`## Untiered Set 12 — Legal & Policy (3
forks, tier null)`**, and it lists exactly **3 open entries**
(inventory idx 862–864) — the three new gaps this set's own
descriptions named in `UNION-SPEC.md`. GAPS.md and
`gaps-batch/inventory.json` agree on the count and on the entry
texts; **no discrepancy** (the brief's stated count of 3 is the
count both sources carry). All 3 are closed by this unit under
the decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`.

What landed: one new module, `src/legalpol/extensions.py`
(`LegalPolExtensions`, wrapping the core `LegalPolStore`; all
seven core modules byte-identical, SHA-256 verified against the
pre-build baseline in `scratch/prebatch-src.sha256` — store.py
still `7030f9fde2aafbd76e653d6805fe7b2f8509ed9108600f91d4c0aacefff85093`,
the shipped hash), and `tests/test_gaps_batch.py` (27 tests).
Full suite: **103 → 130 tests**, all passing.

**Tier discipline binds the extension as it binds the set:** no
record shape has a tier, baseline, impact-level, or CMMC field —
those fields do not exist — and nothing computes a compliance
posture. The union spec recorded **no documented control claims**
for this set, and the extension fills none in; a recursive key
scan over every extension record and view pins the absence of
tier/baseline/score-shaped keys (see Negative control and the
test module). **The founding privacy rule binds absolutely:**
documents exist in this substrate ONLY as metadata + SHA-256
records in the core document registry; no extension shape has a
field for document content, research text, a draft, a summary, or
query text. A research query enters only as its SHA-256 digest —
the extension's request method has no parameter that can accept
query text, mirroring the core's `save_search` design. Requesters
and sources are opaque references. Extension writes map to the
core `document_write` RBAC action; reads resolve the agency
through the core store, so the membership boundary binds every
operation. Nothing is scored.

## Per-entry disposition

| # | Entry (GAPS.md text, verbatim) | Drafted triage | Disposition | Built as |
|---|---|---|---|---|
| 862 | Legal research, evidence mapping & citation-validation engine | stub-engine | reference | Labeled reference records: research requests (`rsq-`; query named by SHA-256 digest ONLY, `reference_stub: True`, state `recorded_reference_only`, `researched_here: False`) + evidence-map entries (`evm-`; fact and source as opaque refs, page/line locators recorded verbatim — the tracing is recorded, the tracing engine is not; `validated_here: False`) + citation outcome records (`cto-`; reported outcome labels verbatim; `validated_here: False`) + draft link records (`rdl-`) binding a request to a core document record in the request's workspace (`drafted_here: False`). `research_request_view` derives map/outcome/link counts and the latest reported outcome label at read; the stored record carries none of them. The research itself is performed by the fork's engine on the fork's corpus, never here. |
| 863 | FOIA case management system of record | build-extension | built | One case record per request (`foi-`; request and requester are opaque references — no request text exists in any shape; receipt date and statutory period recorded as data; `released_here: False`) + append-only reported state records (`fos-`, this unit's intake-lifecycle vocabulary) with current state derived at read by the `_latest_state_label` seam + exemption application records (`fxa-`; labels verbatim, optional core document in the case's workspace) + release records (`frl-`; counts as reported). `foia_case_view` derives current state, the **statutory due date (receipt + recorded period, never stored)**, overdue (against an explicit `as_of`, retired by a terminal recorded state), and exemption tallies at read. The fork's portal surfaces land as derived read views: `foia_requester_view` (the requester's own case state) and `foia_agency_view` (portfolio counts by current state, overdue count, agency-wide exemption tallies — the consistency surface — `method: deterministic_counts`). Operated portals are not built; nothing is released here. |
| 864 | Discovery platform app builder / extensibility | build-extension | built | An application-definition registry: definitions (`app-`) in a core workspace holding the component manifest as DATA (`definition_only: True`, `executed_here`/`runtime_here: False`) + append-only reported state records (`aps-`) with current state derived at read + binding records (`apb-`) attaching a definition to another core workspace of the same agency. Pinned behaviorally: registering definitions, states, and bindings leaves core records byte-identical — the registry holds data and runs nothing. The builder interface and the application runtime are not built and not claimed. |

Closure tokens: 2 entries close as `built` (863, 864) and 1 as
`reference` (862) — exactly the drafted split.

## Re-judgments

None. The drafted dispositions held on close reading against
this set's union spec. Two calls nearest the line are stated
plainly rather than re-judged:

- **App builder (864)** closes `built` as a definition registry,
  where the tiered sibling's agreement-workflow definitions
  closed `reference`. The difference is the entry's own shape:
  the sibling entry named an *automation engine* whose whole
  substance is executing agreements, so its definition records
  were the remainder of an engine. This entry names the
  platform's *extensibility surface* — customer-built
  applications on the discovery platform — whose in-substrate
  substance is the registry itself: definitions, manifests, and
  workspace bindings as records. What is NOT built is stated on
  every record (`executed_here`/`runtime_here: False`) and here:
  the builder interface and the app runtime. The parent may
  re-token to `reference` if it reads the registry as remainder;
  the build is identical either way.
- **FOIA portals (863):** the fork's prose names requester /
  analyst / stakeholder portals. Portals as operated web
  surfaces are presentation layer, not records; what the system
  of record honestly carries is the derived read views over the
  case records, and those are what landed. The entry closes
  `built` on the system-of-record substance (intake, deadline
  derivation, exemption application, lifecycle states), with the
  portal surfaces present as views and named as such.

## Negative control

Fresh, for the new code: the latest-state derivation
(`LegalPolExtensions._latest_state_label` — latest recorded
label wins), the single seam every current-state derivation in
the extension reads through. Its canonical return line,
`return states[-1]["state_label"]`, occurs **exactly once** in
the module (line 274; count verified before patching — this
module was written with one shared seam, so the line-scoping
the sibling L2 drill needed was not required here). In-suite
three-leg control in `tests/test_gaps_batch.py`
(`TestLatestStateNegativeControl`: canonical latest /
earliest-reading mutant subclass / `assertRaises`, plus the
mutant's flip of the overdue derivation and the agency-view
counts), plus a live drill on the real file: the seam was
patched to `return states[0]["state_label"]`, the full suite ran
**130 tests with exactly 4 failures**, all in the new batch
module (the FOIA current-state test, the app-state test, and
the control's canonical and agency-count arms), then the file
was restored from `scratch/extensions.py.premutation` and
verified SHA-256 identical (`690895ea…`); suite green again.
Full record in `tests/README.md`.

## Core integrity

No core module was modified: `src/legalpol/*.py` SHA-256 sums
match the pre-build baseline recorded in
`scratch/prebatch-src.sha256` exactly (all seven modules,
including store.py `7030f9fd…`, the shipped hash). The extension
is store-level only (no HTTP routes), matching the sibling batch
units' pattern — the core `service.py` is byte-identical and
untouched. No era rescope was needed: the set's spec pins (3
sheets, tier null on every sheet, the zero-claim table, the
certified-services exclusion) are untouched and still pass as
written.
