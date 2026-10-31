# Build artifacts & provenance — Cloud Infrastructure & Hosting L2

How `specs/specs.json` was produced, and the artifacts recorded
along the way. Extractor: `scratch/extract.py` (scratch is
gitignored; the shipped spec is `specs/specs.json`).

## Sources joined

- `raw/data_dump.json` — the GSA FedRAMP Marketplace dataset cache
  (produced by the General Services Administration, last change
  2026-10-22). Product records joined by FedRAMP ID; the cached
  `service_desc` is the claim-evidence source.
- `remainder/uncovered.json` — the remainder census's description
  copies. The extractor asserts each sheet's description is
  byte-equal to the census copy **and** the cache's `service_desc`
  (all six pass).
- `forks.json` — the Phase 1 registry: vendor, product, service
  model, impact level, status, CMMC tier, source URL. The
  extractor asserts Moderate / L2 for all six.
- `remainder/nosignal_report.json` — the no-signal research pass:
  classification sentence + source URL per fork. The extractor
  asserts each row is `resolved`, proposes Cloud Infrastructure &
  Hosting, and flags `is_new_category` true.

## Assertions that ran at extraction

- `certified_services` is empty for all six raw records (asserted;
  the field is never matched in any case).
- Every claim's evidence is a verbatim substring of the fork's
  cached description (asserted per claim).
- `business_categories` is empty in all six raw records — the
  census's "Uncategorized (none in source)" state, carried onto
  the sheets as `business_categories_in_source: []`.

## The catalogue check (SAP NS2 forks)

The extractor ran the taxonomy twice for the two SAP forks — once
with the hosted-application catalogue units excluded, once without
— and compared. Result: each catalogue contains exactly one
would-be hit (the S/4HANA Private Cloud Edition unit's "managed
cloud service" → `hosting_platform`), and in both forks the
family's first-match evidence is an environment sentence that
precedes the catalogue, so **the exclusion changed no final claim
table**. The exclusion stands as method (the catalogue's functions
are other categories') and is pinned by test so a future
description edit cannot quietly move a claim onto catalogue prose.

## Recorded artifacts

- **DD-CIE sentence-split artifact.** "SAP NS2 DDCIE is operated
  exclusively by U.S. citizens with operations and data restricted
  to U.S. soil" is cut by the house sentence splitter after "U.S.",
  so no residency pattern survives whole; DD-CIE claims
  `hosting_platform` only. Pinned by test
  (`test_ddcie_residency_sentence_artifact`); recorded in
  UNION-SPEC as a near-miss. Not repaired — counts are a floor.
- **Disclaimer boilerplate.** Both SAP descriptions open with the
  FedRAMP disclaimer paragraph ("FedRAMP does not review or
  endorse vendor-submitted content..."). It fires no family and
  needed no exclusion; noted so the zero is understood.
- **Elastic feature-list nouns.** "security, alerting, monitoring
  and machine learning" in the ESS sentence are hosted-stack
  capability names. `monitoring_observability`'s patterns are the
  forks' specific phrases and fire none of them; `machine
  learning` fires nothing either (no inference family exists).
  Both recorded as near-misses, not claims.
- **Treasury bullet granularity.** Treasury's two model lists are
  semicolon-delimited bullets; the splitter treats each bullet as
  one unit, so several Treasury evidences are whole bullet lists
  stored verbatim (e.g. the Managed model's security bullet). The
  evidence is verbatim either way; granularity is the source's.
- **Duplicate-ID note.** The Treasury pair in the research report
  shares one research pass; this group's fork (AGENCYWC2) is the
  Moderate record, and its sheet stands on its own marketplace
  record and description.

## Verification state

- Extractor run: clean, 34 claims (5 / 5 / 9 / 1 / 2 / 12 by fork
  in member order FR2004446306, F1208031461, F1510137547,
  F1602257856, FR1719841002, AGENCYWC2).
- Suite: 118 tests, all green (spec tests re-derive nothing — the
  claim tables are pinned literally in `test_specs.py`).
- Negative control: mutation drill recorded in
  `tests/mutation-run.txt` — exactly 4 failures with the
  `_check_deployment_slot` seam removed; store restored
  byte-identical (SHA-256 in `tests/store.py.sha256`).
- Live checks: `tests/smoke.py` prints SMOKE OK; a mediated curl
  session against `python -m cloudinfra serve` (health, org
  create, tenancy create with derived counts in the response,
  report, 401 unauthenticated) passed at build time.
