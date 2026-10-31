# Addendum — Content Management System (CMS), CMMC L2: the 1 remainder addition

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 1
previously uncategorized fork of remainder build unit
**`addition:cms-l2`** (see `../../REMAINDER.md`). The original
union spec stands as written: its taxonomy, its 12-function core,
and its control baseline are **unchanged**. This document records
what joined, what the newcomer claims under the group's existing
taxonomy, the core-delta decision, and the updated union
statement.

**Headline: fork spec'd 1 / 1; 0 new claims — the newcomer is a
zero-claim fork under the taxonomy applied verbatim; core delta —
zero functions extended, `src/` byte-identical; tests 98 → 108,
all passing.** The fork's entire marketplace description is one
sentence, and the census citation for it is that sentence: it
verifies verbatim and tags no family. One consequence is stated
plainly in §2: the union spec's "no fork has zero claims" floor
does **not** survive this addition. **1 new gap function** is
named in §5, and no already-registered gap gains a claimant.

## 1. Membership and method

The 1 fork, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR2031155471` | Iron Mountain / Iron Mountain InSight |

Method, identical to the original pass:

- The spec sheet was produced by `scratch/additions_extract.py`,
  which **parses the `TAXONOMY` literal out of the original
  `scratch/extract.py` via `ast` (parsed, never executed, never
  re-typed) and tags with those exact 13 (id, label, regex)
  triples** — the taxonomy was applied verbatim, not re-tuned for
  the newcomer. Same sentence splitting, same evidence rule (first
  matching sentence per family, stored verbatim), same sheet
  schema. Before tagging the newcomer, the extractor
  **reproduces the original 4 forks' shipped claim tables exactly
  from the raw cache** (same algorithm, same evidence rule) and
  asserts deep-equality against the shipped sheets. The sheet is
  **appended** to `specs/specs.json` after the original 4, which
  are deep-equal to git HEAD and byte-preserved through the
  fourth sheet's closing brace (asserted in the extractor).
- Source is the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. The
  description was present; no live fetching. The fork is FedRAMP
  **Moderate / Certified** (SaaS, Government Community Cloud), so
  the group stays single-tier and the L2 baseline is inherited in
  full (Merge Rules 1–2), unchanged. In the source the fork was
  **uncategorized** (`business_categories` empty; `forks.json`
  category "Uncategorized (none in source)"); the census proposed
  Content Management System (CMS), recorded on the sheet as the
  DeadRamp category.
- The census starting point was verified, not trusted: the fork's
  **1 census citation** was re-checked against its own cached
  description and **verifies** as a verbatim substring — with the
  twist recorded in §2: the citation is the description's only
  sentence, and it tags no family.
- **No exclusion trap applies to the newcomer.** Its record's
  `certified_services` field is empty (asserted in the
  extractor), and its single-sentence description contains no
  catalogue of third-party hosted applications and no
  scope-exclusion segment. Only `service_desc` was matched, per
  house method.

## 2. What the addition claims

**0 claims.** The fork's description is one sentence long; the
per-sentence map is `scratch/additions_sentence_map.json` (one
sentence, zero families). The sentence, in full: "The Iron
Mountain InSight system is a cloud-based Software-as-a-Service
(SaaS) solution that provides customers with a content services
platform that leverages Machine Learning (ML) and Artificial
Intelligence (AI) to automatically classify, extract, and enrich
physical and digital content."

**The floor finding, stated plainly.** UNION-SPEC records of the
original four: "**No fork has zero claims.**" That was true of
the original group and is no longer true of the enlarged one:
the newcomer carries zero claims, the group total stays **19**,
and 4 of 5 forks now carry at least one claim. The zero-claim
outcome is pinned in `tests/test_additions.py`
(`EXPECTED_CLAIMS`, and the group-totals test pinning exactly one
zero-claim fork — this one), not hidden.

### Near-misses, itemized per phrase

The description is a single sentence, so the near-misses are
itemized per phrase within it:

- **"content services platform"** — not `content_registry`: the
  family requires "content management system" or "digital
  content management", and neither phrase appears. This is the
  phrase the census classified the fork on ("Content services
  platform."), and it does assert a content platform in
  substance; but a census classification is not a claim, and the
  family's operative text is absent. Verification is not a
  claim, and classification is not a claim either.
- **"cloud-based Software-as-a-Service (SaaS) solution"** — not
  `platform_hosting`: the family requires "cloud platform for
  building" or "leading cloud platform" (Acquia's own platform
  assertions). A delivery-model mention tags nothing, per the
  original calibration (Tyler TFCP's AWS GovCloud substrate and
  the generic "SaaS Platform" mentions for Tyler and Vibrent tag
  no hosting function). The fork's Government Community Cloud
  hosting posture is its own platform property; it does not
  transfer to the build.
- **"automatically classify, extract, and enrich"** — no family
  keys on classify / extract / enrich. `metadata_taxonomy`
  requires the literal token "metadata" (absent — enrichment is
  metadata work in substance, but the token is not there), and
  `ingestion_repository` requires ingest / index-in-place /
  single repository (absent — and extraction moves data *out of*
  content, the reverse direction from ingestion into a
  repository). This is the fork's headline function and it has
  no family — it becomes the gap in §5.
- **"physical and digital content"** — not `media_assets`: the
  family requires "types of digital documents" / "digital
  documents" / "images, videos"; "digital content" is not
  "digital documents".
- **"Machine Learning (ML) and Artificial Intelligence (AI)"** —
  this taxonomy has no AI/ML family at all; the tokens tag
  nothing.
- **Whole-description absences** — no "search" token (so no
  `search_discovery`), no "editor" token (so no
  `authoring_editing`), no "records management", no "reporting".
  The description is 38 words of platform framing around one
  engine claim; everything else the product may do in the world
  is not in its marketplace text, and reputation is not
  evidence.

No wording-artifact corrections were needed: there are zero raw
hits, so there is nothing to correct and nothing was
manufactured.

## 3. Core-delta decision

| Family / substance (addition) | Disposition | Core delta |
|---|---|---|
| *(no claimed families)* | The fork claims nothing, so no core extension is presupposed by any claim | **None** |
| Content registry (asserted in substance by "content services platform"; no claim) | Core 1–3, 7, 8 — the registry substrate is where the fork's content records, and the metadata/tag records its enrichment would write, already live | **Carried** — no change |
| ML/AI classification, extraction & enrichment (asserted in substance; no family) | Extended — an engine; engines are Extended throughout this group | **Gap** (§5) — not an extension |

**Result: the core is unchanged.** The newcomer claims no
function, and the one substrate its described surface presupposes
(content records with metadata and tags, asset registrations,
metadata search) is the build as shipped. `src/` is
byte-identical to the shipped build (`src/cms/store.py` SHA-256
`e1d05424812f17b5bf1de6023bde72e08983a1790854d36df50d3ef2ad232de1`
before and after this addendum's work, the mutation drill
included; the full `src/` tree diff against HEAD is empty). The
tier baseline does not change: same tier by construction.

## 4. Updated union statement

The group now covers **5 forks** (4 original siblings + 1
remainder addition), **19 claims** in total (19 + 0), with
**4 of 5** forks carrying at least one claim. The merged build
remains the same content substrate — site/section and type
registries, the content registry with revisions, the editorial
lifecycle, publishing records with derived windows, the asset
registry, taxonomy and metadata, metadata search, registry
reporting, the REST API, RBAC, and the append-only audit log —
now spec'd against 5 marketplace offerings instead of 4. The
group was already heterogeneous (a Drupal platform, a library
system, a BPM platform, a health-research platform on one
substrate); the newcomer adds an ML/AI content-services platform
in the thinnest textual form in the group — a single sentence —
whose substance is an engine of exactly the kind this group
registers as Extended rather than builds as substrate.

## 5. Gaps — for the registry at ship

**New gap function** (1):

- **ML/AI content classification, extraction & enrichment
  engine** (automated classification of physical and digital
  content, structured-data extraction from content, and metadata
  enrichment) — Iron Mountain InSight, from its own headline
  self-description ("leverages Machine Learning (ML) and
  Artificial Intelligence (AI) to automatically classify,
  extract, and enrich physical and digital content"). The
  records such an engine's outputs would write — item metadata
  and tags, asset registrations — are Core; the engine itself
  is Extended. The taxonomy has no family for it (no claim
  fired), so this gap is registered from the fork's described
  function, not from a claim.

**Existing gaps gaining claimants:** none — itemized, because
three were plausible:

- **Bulk ingestion & index-in-place engines** gains **no**
  claimant: the fork's "extract" moves data out of content, the
  reverse direction from ingesting data into a single
  repository (Bibliovation's claim rests on that ingestion
  phrasing in its own words). Assigning extraction here would
  blur a boundary this addendum keeps.
- **Platform hosting itself** gains **no** claimant:
  "cloud-based SaaS solution" is delivery-model prose, the
  exact class the original calibration excluded (Tyler /
  Vibrent).
- **Enterprise search indexing engines** gains **no** claimant:
  the description contains no search token at all.

**Named absences:** the union spec's six named absences —
editorial review/approval workflow, content versioning/revision
history, publish scheduling, WYSIWYG/visual editing,
templating/rendering, and personalization — are claimed by the
newcomer no more than by the original four. All six **survive**,
now standing at 0 of 5 forks.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and append
  order, membership against `remainder.json`, the literal
  zero-claim table, the group totals (19 claims; exactly 1
  zero-claim fork, the newcomer), registry fields as published,
  the verbatim description, the census citation (the whole
  description, verifying and tagging nothing), and the near-miss
  pins — see `tests/test_additions.py`.
- The fork is exercised against the substrate in the same file:
  a content item carrying classification/extraction metadata and
  a tag, a physical-content asset registration whose checksum is
  computed and whose bytes are discarded, metadata search over
  both; and an editorial-lifecycle case in which the
  editor-author cannot approve their own item.
- **Tests: 98 → 108, all passing.**
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: the
  separation-of-duties guard in `CmsStore._check_approver_not_author`
  (`src/cms/store.py`) was patched to a no-op (`return None`) —
  the guard line occurs exactly once in the file and the patch
  was scoped to it, count asserted — and the full suite ran:
  **108 tests, exactly 5 failures**: the shipped drill's 4 plus
  1 from the new additions module (the InSight lifecycle
  author-guard case), tripping exactly as designed. `store.py`
  was restored from the pre-mutation copy and verified
  SHA-256-identical to the shipped hash; the suite re-ran green.
  Recorded in `tests/README.md`; the raw failure list is in
  `scratch/additions_mutation_run.txt`.
