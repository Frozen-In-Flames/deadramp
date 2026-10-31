# Legal & Policy — Untiered Set (DeadRamp Phase 2, remainder)

**Tier: null. This set asserts no FedRAMP baseline and no CMMC
tier.** The 3 forks in this build have FedRAMP impact level
**Unknown** in the source dataset — the source publishes no
baseline for them — so no tier is assigned and no equivalence is
drawn, here or anywhere in this group. Per the pipeline rule for
untiered offerings, they build to their documented control
claims only. The full contract is [`UNION-SPEC.md`](UNION-SPEC.md).

**This category is not the Law Enforcement category.** Legal &
Policy is its own registry category (founded by the VulcanGov AI
agent workspace build, `legal-policy-l2/`); this set's members are
a legal data-discovery platform, a litigation legal-AI platform,
and a FOIA case-management platform that the remainder census
assigned to Legal & Policy from their own descriptions.

An **untiered set** is the remainder phase's group for forks of
one category whose source records carry no impact level. The set
follows the same pipeline as every tiered group — per-fork spec
sheets under the category's fixed taxonomy, a union spec, one
merged clean-room implementation — with the tier left null and a
Documented control claims section in place of a baseline.

## The forks (3)

Membership is exactly census unit `untiered:Legal & Policy` in
`../../remainder.json`.

| Fork | Vendor | Filed as | Claims |
|---|---|---|---:|
| Casepoint Government | Casepoint LLC | Uncategorized (none in source) | 0 |
| Litmas AI | Litmas, Inc. | Legal & Policy | 0 |
| Alira | Skyward IT Solutions | Analytics | 0 |

**All three forks claim zero functions, and the set total is
0 claims.** The taxonomy is the founding fork's own phrases
(defined from the founding VulcanGov description: an AI agent
workspace with a curated federal legal library, secure
single-use sandboxes, and an agency administration console).
Applied verbatim it fired on none of the three descriptions:
these forks describe eDiscovery and legal-hold processing
(Casepoint), a litigation agent with legal research and drafting
(Litmas), and FOIA case management (Alira) — a different
functional surface in different words. The zeros are recorded,
not repaired; the taxonomy was not re-tuned for this set. This is
the same outcome the founding group's six tiered additions
recorded under the same taxonomy. Verbatim-taxonomy proof: the
extractor reproduced the founding group's original shipped claim
table exactly (1 of 1 fork, 11 of 11 claims, from the original
ship commit's specs) before tagging this set. Full per-fork
specs: [`specs/specs.json`](specs/specs.json). Census citations:
4 of 4 verify verbatim; 0 of 4 serve as claim evidence (there
are no claims).

## The core (13 functions)

Carried **whole** from the founding Legal & Policy build
(`groups/legal-policy-l2/src/legalpol/`), because the substrate
is records machinery and tier-independent: the founding source
contains no tier or baseline machinery, so there was nothing
tier-shaped to strip. **No core function is claim-supported by
this set** (0 claims across all 3 forks) — every function is
**carried, not claimed**, stated plainly. The build implements
records, not legal work: it stores no document content, executes
no code, runs no agent, and answers no legal question.

| # | Function | Contract |
|---|---|---|
| 1 | Agency registry & membership | agency registry with at most one live membership per (agency, user); roles validated independently of agency roles |
| 2 | Workspace registry | per-agency workspaces; at most one live workspace of a kind per agency |
| 3 | Agent session records | immutable past session records; the record is never mutated |
| 4 | Execution records | append-only; a sandbox session accepts exactly one execution (the signature invariant) |
| 5 | Library source registry | declared sources with declared refresh cadence; the cadence is a declaration, rechecked syntactically at read |
| 6 | Saved-search records | **query text is stored as a SHA-256 digest only — the store has no parameter that can accept query text** |
| 7 | Document registry | metadata + SHA-256 checksums; no content fields exist |
| 8 | Verify-by-content | the only integrity check: a caller-supplied candidate string matches the stored checksum → boolean answer |
| 9 | Usage records | positive-integer quantities only, recorded against live objects |
| 10 | Usage export manifests | a manifest over already-recorded usage; creating one never changes usage |
| 11 | Registry reporting | deterministic counts of registry state; nothing is scored |
| 12 | Registry search | caller-scoped, name-ordered; a token matching nothing returns an empty list, never an error |
| 13 | Access control & audit | role × membership permission matrix; append-only audit log; denied attempts recorded |

**The signature invariant, carried exactly: sandbox single-use.**
A sandbox session accepts exactly one execution record; a second
attempt fails, consumes no id, and changes nothing. Enforced in
the store by the `_check_sandbox_unused` seam, and mutation-
verified in this tree (see Tests).

**The privacy discipline, carried exactly:** records hold
metadata and digests, not content — documents are metadata +
checksum, search queries are SHA-256 digests only (the store's
`save_search` has no parameter that can accept query text, pinned
by test), no entity shape can hold a real identifier of a person
or a matter's substance, and nothing is scored. Date-derived
status (`expired`, `sandbox_consumed`) is derived at read, never
stored.

## How to run

```bash
cd groups/legal-policy-untiered
PYTHONPATH=src python3 -m legalpol serve            # HTTP on 127.0.0.1:8799
PYTHONPATH=src python3 -m unittest discover -s tests # full suite
PYTHONPATH=src python3 tests/smoke.py                # live-server smoke
```

Demo users are included for local use; they are hooks for an
embedding organization's identity provider, not an identity
provider themselves:

| User | Role | Can do (role layer) |
|---|---|---|
| `alice` | admin | everything, including agency administration, membership, usage export, audit read |
| `bob` | member | workspaces, sessions, executions, library sources, searches, documents, usage writes |
| `carol` | viewer | read-only listings, registry search and reporting |

Agency-scoped actions additionally require agency membership as
recorded — an admin who is not a member of an agency cannot act
inside it (only membership granting is global).

## Documented control claims

**No NIST SP 800-53 control family is documented by any fork in
this set.** No description asserts a control family in control
language; the union spec records the two nearest prose items
(Alira's "auditable release packages" — auditability of outputs;
Litmas's fact-to-source tracing — the product's provenance
function) and why neither is a control claim, plus Casepoint's
"highest level of security" posture prose. Alira's source record
names "Audit Logging and Monitoring" and "Authentication and
Access Management" among its *certified services* — those are
record fields, never matched against description text, and they
assert nothing here. Every documented claim would in any case be
a **fork's claim about itself**, never this build's attainment;
nothing is filled in from a baseline.

## Tests

**103 tests, all green** (`PYTHONPATH=src python3 -m unittest
discover -s tests`): the 94 tests of the founding build's suite
carried with the code (the founding group's 12-test additions
module is not carried — it pins the founding group's tiered
addition unit, not this set), plus 9 new spec tests pinning this
set's census membership, tier discipline (every sheet
`"Unknown"` / `null`), registry agreement, recorded business
categories, verbatim descriptions, the literal zero-claim table,
the certified-services exclusion, and the 4 census citations.

**Negative control, re-run in this tree:** the founding group's
recorded signature drill — the store's `_check_sandbox_unused`
seam patched to a no-op body, byte-identical restore verified by
SHA-256 — makes **exactly 4 tests fail** (the same 4 the founding
drill fails at founding scope): the two
`test_negative_control` canonical/mutant cases,
`test_sessions_executions`' single-use rule, and
`test_service`'s full flow. The drill fails precisely where the
single-use rule lives and nowhere else. Full record:
[`tests/README.md`](tests/README.md).

**Substrate accounting:** 6 of 7 `src/legalpol/` modules are
byte-identical to the founding build (SHA-256s in
`tests/README.md`), including `store.py`, whose module docstring
still names the founding group — it is carried verbatim as part
of the identical file. `__init__.py` differs by its docstring's
first line only, re-anchored to name this untiered set. The
founding group's spec-extraction taxonomy reproduction proof
travels with this set's own extractor
(`scratch/extract.py`, gitignored).

## Honesty

- **Tier null, plainly.** No tier is assigned to any fork in
  this set and no CMMC equivalence is drawn. If the source
  later publishes an impact level for one of these offerings,
  the tier is recorded then.
- 0 claims across 3 forks; every taxonomy family is a named
  absence at 0 of 3. No claim was manufactured to make the set
  look covered, and the taxonomy was not widened to catch these
  forks' vocabulary.
- **The store accepts no query text by design.** Search queries
  exist in this build only as SHA-256 digests; the absence of a
  query-text parameter is the privacy guarantee, not a missing
  feature.
- This build executes no code and runs no agent. Sandbox
  sessions and execution records are *records about* sandboxed
  work, enforced over the registry — the sandbox runtime, the
  agent runtime, the search engines, and the document generation
  engine are Extended gaps, named in the union spec alongside
  this set's three new gaps (legal research & citation-validation
  engine; FOIA case management system of record; discovery
  platform app builder).
- Extended functions attested in substance by this set's forks
  in their own words: eDiscovery processing, review and
  production; legal hold management; FOIA release workflows; an
  agentic litigation associate; legal drafting — each registered
  under its own gap name in `../../GAPS.md` (founding and
  additions gaps) or named in this group's union spec (new
  gaps), and built in no part here beyond the records substrate.
- Demo identities are hooks, not an IdP: identity federation
  stays with the embedding organization.
- Nothing here claims a FedRAMP authorization, a CMMC
  certification, or a control baseline for any fork or for this
  build.
