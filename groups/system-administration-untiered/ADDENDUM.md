# Addendum — System Administration, untiered set: the 1 no-signal addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the
one fork that joins the set after the census: **CloudFit**
(`FR2700754078`), resolved by the live-docs research pass. The
original union spec stands as written: its taxonomy, its
twelve-function core, its tier discipline (**tier null** — no
baseline asserted, no CMMC equivalence drawn), and its
documented-control-claims accounting are **unchanged**. This
document records what joined, on what classification basis,
what it claims under the set's existing taxonomy, the
core-delta decision, and the updated union statement.

**Headline: forks spec'd 1 / 1; 0 claims — the newcomer is a
zero-claim fork under the taxonomy applied verbatim (0 raw
hits, 0 removed), exactly the set's founding pattern; core
delta — zero, `src/` byte-identical; tests 82 → 93, all
passing.** The set's totals are unchanged in kind: **0 claims
across 5 forks**, every fork zero-claim. One classification is
new; no documented control claim is added; no new gap function
is registered — four already-registered gaps gain a claimant
in substance (§6).

## 1. Membership and classification basis

| Fork | Vendor / product |
|---|---|
| `FR2700754078` | CloudFit Software, LLC / CloudFit Federal Platform |

**Why it was not in a census build unit.** This fork sat in
the remainder census's **`no-signal-set`**: the census
recorded **no citations and a `no_signal` flag** (reason
"prose_only", `platform_general` true) — its cached
marketplace description is managed-platform prose ("Managed
general cloud hosting environment for customer
applications/workloads; description lists security,
governance, compliance, monitoring, identity, operational
support and hosting with no single primary function of its
own", per the classifier note), so no build unit proposed a
category for it. After the census, it could join only a set
whose *tier* matches its record: its source record publishes
no impact level (`fedramp_impact_level` "Unknown"), so it
joins this untiered set and its sheet records **"Unknown" /
`cmmc_tier: null`**, exactly like the set's four sheets.

**Classification basis (live-docs research pass).** The
category was resolved afterwards from the vendor's own public
pages (`../../remainder/nosignal_report.json`, entry
`FR2700754078`, status "resolved", existing category — not a
new one):

> "At CloudFit, we provide a comprehensive suite of managed
> services tailored to optimize and secure your Microsoft
> Cloud environment."
> — https://cloudfitsoftware.com/

The research note records that the vendor's homepage and
About page both carry this Managed Services sentence, and
that the prose emphasizes managed services **performed by the
vendor** — which meets the census's recorded **managed-platform
boundary**: managed-hosting prose emphasizing administration
services performed → System Administration; pure platform
prose → no-signal. That sentence is recorded on the fork's
spec sheet as `classification_evidence`, with
`classification_source_url` alongside it. **It is a
classification citation, not claim evidence**: it does not
occur in the fork's cached marketplace description (asserted
in the tests), and no claim below rests on it. Claims are
tagged from the cached description only, exactly as in the
set's original pass.

As filed in `forks.json` the fork's category is
Cybersecurity & Risk Management; its source record's business
categories include System Administration among eight. The
resolution assigns System Administration, and the sheet
records the assignment.

**Method.** Identical to the set's original pass, with the
house strengthening: the spec sheet was produced by
`scratch/nosignal_extract.py`, which imports the set
extractor's own functions (taxonomy AST-parsed out of the
founding group's `scratch/extract.py` — parsed, never
executed, never re-typed) and, before tagging the newcomer,
**re-runs both taxonomy-verbatim proofs**: the founding
singleton's shipped claim table reproduced exactly (8 of 8
claims, deep-equal) and this set's 4 shipped sheets' claim
tables reproduced exactly (0 each, deep-equal). The sheet is
**appended** to `specs/specs.json` after the 4 shipped
sheets, which are verified deep-equal against git HEAD (both
in the extractor and in `tests/test_nosignal_addition.py`);
its description is verified identical in both cached sources
(`raw/data_dump.json` and `remainder/uncovered.json`, under
the founding normalization). **No exclusion trap applies:**
the record's `certified_services` field is empty (asserted
in the extractor); only `service_desc` was matched. Census
citations for this fork: **none existed** (the no-signal
flag) — nothing to verify, and the two evidence streams
never mix (pinned).

## 2. What the newcomer claims

**0 claims.** The mechanical pass over its cached description
produced **0 raw hits** — no taxonomy pattern occurs in any
of its sentences — so the exclusion pass removed nothing,
because nothing fired. The taxonomy's 8 patterns are the
founding fork's own exact phrases ("full management of the
OS and services", "General Support System (GSS)",
"inherits controls from the CSP", "Highly Available (HA)",
…), matched case-sensitively, and CloudFit asserts its
managed-platform substance in other vocabulary:

- "a **managed federal cloud environment** for hosting
  customer SaaS applications", "a standardized
  **CloudFit-managed service boundary**", enabling CloudFit
  "to **onboard, operate, monitor, and support** customer
  applications" — managed services in substance; the
  *full management* family is the founding fork's exact
  phrase and does not occur.
- "**application hosting capabilities**" and "hosting
  customer SaaS applications" — hosting in substance;
  `application_delivery` requires "application delivery".
- "hosted within **Microsoft Azure Government**" — a named
  third-party host in substance; the family requires
  "third-party cloud hosting platforms".
- "**monitoring**" and "**identity management**" among the
  delivered capabilities — monitoring is the founding spec's
  deliberate named absence (no family), and the taxonomy
  holds no identity family.

The zeros are recorded, not repaired; the taxonomy was not
re-tuned. Full per-family counts: `scratch/
nosignal_function_counts.json`; the adjudication record is
appended to `scratch/ARTIFACTS.md`.

## 3. Documented control claims — effect: none added

Tier discipline is unchanged (no baseline asserted, nothing
converted to a tier), and this fork **adds no documented
control claim** — by adjudication, stated plainly:

- The description's capability sentence ("The platform
  delivers security, governance, compliance, monitoring,
  identity management, operational support, platform
  services, and application hosting capabilities within a
  standardized CloudFit-managed service boundary") lists
  services the platform **delivers to customers** —
  **function prose** under this set's recorded rule (the
  Freshworks "built-in security, compliance, and governance
  controls" general-terms precedent; the Dynatrace
  "application security" precedent). "Identity management"
  as a delivered capability is not a control the offering
  asserts **about itself** with a mechanism — contrast PDQ's
  "includes security features such as MFA, role-based access
  controls, encryption, and audit logging", which names
  mechanisms of its own platform and is documented. CloudFit
  names no mechanism, so **IA is recorded here but not
  traced** to the documented set.
- "maintaining a consistent security and compliance posture
  across hosted services" asserts a posture in general terms
  and names no control — general-terms prose, not traced.
- The framework names (FedRAMP, NIST 800-53, RMF, CMMC) are
  alignment prose — "designed to support regulated workloads
  requiring alignment with" them — not control claims.

The documented set therefore stands as shipped: **IA, AC,
SC, AU — all by PDQ alone** — and every other NIST SP 800-53
family remains **not documented** by any fork in this set,
CloudFit included.

## 4. Core-delta decision

No family is claimed, and no records form the newcomer's
described surfaces presuppose is missing from the carried
substrate:

| Newcomer surface | Records form it presupposes | Core delta |
|---|---|---|
| Managed platform environment on a named host | **Core 2** managed system records (`platform_ref` opaque — "AZURE-GOV" is a caller-chosen reference; no hostname or credential field exists) | **Carried** |
| Hosted customer SaaS applications | **Core 3** application registry (an application record on its hosting system) | **Carried** |
| Operational support for hosted applications | **Core 4** service request records (the support *work* itself is a gap, §6 — recording a request performs no work) | **Carried** |
| Onboard / operate / monitor as performed operations | None in the substrate — performed administration is Extended by construction | **Gap** (§6) |

**Result: the core is unchanged.** `src/` is byte-identical
to the shipped build — all 7 `src/sysadmin/` modules match
the SHA-256 accounting in the group README (`store.py`
`46c4f2dc…`, the founding group's shipped hash), before and
after this addendum's work, the mutation drill included.
Tier discipline does not change: tier null by construction.

## 5. Updated union statement

The set now covers **5 forks** (4 census-unit members + 1
no-signal addition), **0 claims** in total, with **5 of 5**
forks at zero claims. The merged build remains the same
twelve-function records substrate — customer organizations
with membership as the access boundary, managed system and
application registries, service request records with derived
overdue status, change records under separation of duties,
control inheritance records carrying dispositions verbatim,
search, counts-only summary, REST API, RBAC, append-only
audit — now spec'd against 5 marketplace offerings instead
of 4. The set's character is unchanged in kind: the substrate
is **carried, not claimed** for every member, and the
newcomer repeats the founding pattern — a managed-platform
offering whose substance (a vendor-operated environment
hosting customer applications) the taxonomy's
founding-phrase families do not hold. It administers
nothing, for the newcomer exactly as for the original four.

## 6. Gaps — for the registry at ship

**New gap functions: none.** Everything the newcomer asserts
in substance maps to a gap already registered for this set.

**Existing gaps gaining a claimant in substance** (taxonomy
claimants remain 0 — no family fired; recorded as such):

- **Managed OS & services administration operations** — +1
  in substance: CloudFit (a CloudFit-operated managed
  environment; CloudFit onboards, operates, monitors, and
  supports customer applications inside a managed service
  boundary — the performed administration itself).
- **Application delivery & hosting runtime** — +1 in
  substance: CloudFit ("application hosting capabilities";
  "hosting customer SaaS applications and cloud workloads" —
  the hosting environment applications run in).
- **Observability & monitoring engines** — +1 in substance:
  CloudFit (monitoring named among its delivered
  capabilities).
- **Third-party CSP hosting platforms** — +1 in substance:
  CloudFit (hosted within Microsoft Azure Government — the
  platform is outside its own boundary as described; the
  substrate records only an opaque `platform_ref`).
- **Platform layer** — gains a note: CloudFit's deployment
  model is recorded as Government-Only Cloud with a
  standardized managed service boundary; deployment-layer
  concerns stay platform-layer, as shipped.

## 7. Verification

- Spec integrity is pinned by tests
  (`tests/test_nosignal_addition.py`): sheet count and order,
  the 4 shipped sheets deep-equal to git HEAD, membership
  against the census `no-signal-set` (with its `no_signal`
  flag and empty citations pinned), the literal zero-claim
  table, set totals unchanged (0 claims, 5 of 5 zero-claim),
  tier discipline on the new sheet ("Unknown" / null /
  System Administration), the description verbatim against
  both cached sources under the founding normalization, the
  classification fields pinned against
  `remainder/nosignal_report.json` (with the classification
  sentence asserted **not** to occur in the cached
  description), and the per-fork near-miss pins (substance
  tokens present, family phrases absent).
- The newcomer is exercised against the substrate in the
  same module: a managed-platform system record with its
  exact pinned nine-key shape (the hosting platform an
  opaque reference only), a hosted customer application on
  it, and an operational-support request deriving not
  overdue before its due date and overdue after it, with
  the summary's derived overdue count at 1.
- **Tests: 82 → 93, all passing.**
- **Negative control:** the core is unchanged, so the set's
  signature drill was re-run in this tree: `_is_overdue` in
  `src/sysadmin/store.py` was patched to return `False`
  unconditionally and the full suite ran — **93 tests,
  exactly 7 failures**: the shipped drill's 6 plus the new
  no-signal substrate case, tripping exactly as designed;
  no spec test tripped. `store.py` was restored from the
  pre-mutation copy and verified SHA-256-identical to the
  shipped hash; the suite re-ran green. Recorded in
  `tests/README.md`; raw output in
  `scratch/nosignal_drill_output.txt`.
- **Scoping disclosure:** three unit-scoped pins in
  `tests/test_specs.py` (the two membership tests and the
  zero-claim list) now read the unit's first-four slice,
  since a fifth sheet follows; every fact they pin about
  the untiered unit is unchanged, and the scoping is
  disclosed in that module's docstring. Its tier,
  totals, and description tests iterate all 5 sheets and
  pass unchanged in strength.
