# Union Spec — Law Enforcement, CMMC L1 singleton (DeadRamp Phase 2, Group 47)

The functional spec for the **Law Enforcement L1 singleton**: a
sibling group of **one fork** — **Flock Safety Platform** (Flock
Safety), SaaS, Public Cloud deployment, FedRAMP **Low**, FedRAMP
Certified (FedRAMP ID FR2527955211). Per PIPELINE.md, singletons
build after the sibling groups with the same pipeline at group size
one: this spec is the one fork's claims under the category taxonomy,
and the build is the category substrate those claims presuppose, at
this fork's own tier.

**Reconciliation (zero diffs).** `forks.json` carries exactly one
Law Enforcement / L1 entry (the fork above; its registry fields match
the raw marketplace record field for field). MAP.md omits groups of
one from its sibling-group sections by design; the reconciliation
therefore runs through the category total: MAP.md's category table
gives Law Enforcement **6** offerings, the sibling sections account
for L2 (2) + L3-adjacent (2) = 4, `forks.json` records one further
untiered offering, and 6 − 4 − 1 = **1** — this singleton. The fork's
source record carries `business_categories: []` (empty in the
source); its DeadRamp category comes from the listing's
business-function filter tags, per the Phase 1 category rule. The
empty field is preserved in the spec sheet, not repaired.

## Singleton character — read this first

**This fork is not a legal research platform, and it is not a
records platform of any kind.** It is a public-safety camera network:
the description's whole functional content is that the vendor
"develops and manufactures license plate reading (LPR) technology,
audio recognition sensors, video cameras, and accompanying software
to capture objective evidence required by law enforcement to solve
crimes." The category taxonomy (Group 34's, below) was defined from
the L2 group's two legal research platforms, and this fork's
vocabulary intersects it **nowhere**: **0 of 9 families tag**, with
every near-miss itemized in `scratch/ARTIFACTS.md`. The taxonomy was
not re-tuned.

That makes this the category's limiting case, and the spec treats it
the way the recorded precedents treat it (Singleton 38's zero-claim
sheet; Groups 23, 35, and 40's carried cores):

- The fork's own engines — the camera/sensor network and its
  detection and evidence-capture functions — are **Extended gaps**,
  named from the description's own verbs. Under this category's
  standing discipline they are unclaimed-by-design exclusions for
  the substrate: the build contains **no surveillance function of
  any kind**, and none is implied.
- The **legal research records substrate** the category established
  at L2 is carried in full at L1 under an explicit core-boundary
  decision (below). It is what the category's records layer is; a
  singleton inherits its category's substrate at its own tier
  rather than re-deriving a lesser one, and a wording artifact is
  not a downgrade.
- The **hard privacy rule** is intact and unchanged: documents are
  registry metadata + SHA-256 only, verified by content; saved
  searches and annotations are stored as SHA-256 digests only;
  citation treatments are recorded verbatim; no entity shape can
  hold a real name, a case subject, or any content of any kind.

## How functions were counted

The fixed **9-family taxonomy from Group 34** (Law Enforcement L2)
was applied **unchanged** — ids, labels, and matchers verified
identical against Group 34's extractor programmatically (see
`scratch/extract.py`). A family is claimed only when the fork's own
public description contains matching text; the first matching
sentence would be stored in `specs/specs.json` as evidence. Group
34's five wording-artifact corrections are inherited with the
taxonomy and were not re-opened. **0 claims** survive (0 raw hits —
no pattern fires on either of the description's two sentences).
Counts are a **floor**, not a ceiling. Near-misses are itemized in
`scratch/ARTIFACTS.md`.

## Function ranking — the singleton fork under the category taxonomy

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 0 | Legal research corpus (primary & secondary law) | 0 claims — absent; the source registry is carried as substrate (boundary decision below) |
| 1 | 0 | Legal search tools | 0 claims — absent as a family; saved-search records (digests only) carried as substrate |
| 1 | 0 | Citation validation | 0 claims — absent; citation-check records (treatment verbatim) carried as substrate; the validation engines are Extended at every tier |
| 1 | 0 | Document management (upload, review, document features) | 0 claims — "capture objective evidence" is a recorded near-miss (ARTIFACTS.md #3); the document registry (metadata + checksums) is carried as substrate |
| 1 | 0 | Save, annotate, share & collaborate on research | 0 claims — "collaboratively" is a recorded near-miss (ARTIFACTS.md #2); membership + annotation records (digests only) carried as substrate |
| 1 | 0 | Editorial enhancement (taxonomies & editorial features) | 0 claims — absent; Extended at every tier (the vendors' proprietary editorial systems) |
| 1 | 0 | Practice guidance & standard documents | 0 claims — absent; guidance kinds in the source registry carried as substrate |
| 1 | 0 | Secure access controls | 0 claims — absent; RBAC is carried as Low-baseline hooks |
| 1 | 0 | SaaS / cloud delivery (platform note) | 0 claims under the verbatim pattern; the fork is SaaS per its source record, and the build is a single-tenant reference deployment, as at L2 |

**The fork's excess over the substrate** (functions its description
asserts that no taxonomy family names, because the category taxonomy
was defined from the L2 group's legal research descriptions):
**license plate reading**, **audio recognition**, **video camera
networking**, and **objective-evidence capture**. These are
specified as Extended gaps below — named from the fork's own verbs,
not forced into families, and not built.

**Named absences — anticipated by the category, claimed by neither
this fork nor the L2 siblings** (carried from Group 34, unchanged;
unclaimed → not built, not gaps): incident / case management for
law-enforcement operations; evidence management & chain of custody
over physical evidence *(note: this fork asserts evidence
**capture** by its devices — an Extended gap below — which is a
different function from custody records over physical evidence, and
neither is built)*; criminal records / records-management systems
(RMS) and criminal-history data of any kind; investigative case
files and case subjects.

## The Core — what the build implements (11 functions)

The same legal research records substrate the category's L2 merged
build implements (full contract in Group 34's UNION-SPEC.md, which
this build's `src/` implements unchanged):

1. **Matter registry & members** — matters keyed by an opaque
   `matter_ref`, guarded lifecycle (`open` → `closed` → reopen);
   membership is the boundary every matter-scoped function enforces.
2. **Source registry** — legal sources as metadata records (six
   kinds: statute, case law, regulation, secondary, guidance,
   standard document). No content.
3. **Document registry** — metadata + SHA-256 checksums, guarded
   review lifecycle (`registered` → `in_review` → `reviewed`).
   Content is never stored.
4. **Verify-by-content** — given bytes, recompute the SHA-256 and
   compare; returns the comparison, stores nothing.
5. **Saved-search records** — opaque ref, the query's SHA-256 digest
   (never the query), and a result count. The store has no parameter
   that can accept query text.
6. **Annotation records** — opaque ref, target, and the note's
   SHA-256 digest (never the note).
7. **Citation-check records** — the caller's treatment string
   recorded **verbatim**; never normalized, scored, or aggregated
   into a computed status.
8. **Registry reporting** — counts computed on read, treatment keys
   verbatim. No analytics engine, no score field anywhere.
9. **Registry search** — literal substring search over registry
   metadata, scoped to matters the actor may see; digests are never
   matched or returned as searchable text.
10. **Access control (RBAC)** — platform roles `admin`, `member`,
    `viewer` over nine actions, layered with matter membership
    (non-members cannot read or write a matter's records; the
    platform `admin` role can), enforced on every operation.
11. **Audit log** — append-only; every mutation and every denied
    attempt recorded with actor, action, target, and UTC timestamp.

**Core-boundary decision (explicit).** All 11 core functions tag
**zero** claims in this group and are **carried, not claimed**: they
stand because (a) the category union at L2 established this records
substrate as the Law Enforcement core, and a singleton inherits its
category's substrate at its own tier rather than re-deriving a
lesser one (the singleton method; precedents: the core-boundary
decisions in Groups 10, 24, and 30, and Singletons 37 and 38); and
(b) the Merge Rule takes a union
upward whole — thinner prose at a different tier is not a downgrade
of the substrate. What the fork itself adds to the union is
exclusively Extended (below). Nothing in the carried substrate
performs, assists, or ingests any function of the fork's camera
network: the substrate holds records about research matters, and
the hard privacy rule forbids it from holding anything about any
person.

**Reuse, stated explicitly.** The implementation in `src/` and the
suite in `tests/` are the shipped Group 34 (Law Enforcement L2)
code, reused — this project's own Apache-2.0 code. 5 of 7 `src/`
modules are byte-identical to Group 34's; `__init__.py` and
`store.py` differ by exactly one docstring line each (the group
reference; diff-verified, zero logic changes). 12 of 14 test files
are byte-identical; `lawenf_helpers.py` and
`test_negative_control.py` differ by docstring group references only
(per-file SHA-256 in `scratch/reuse-note.md`). **What is NOT reused
is the baseline claim** — Group 34's Moderate / 800-171 framing does
not carry over; this group's spec, traceability, and README are
written against the Low baseline and FAR 52.204-21 only.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **Low** (this fork) on the
  crosswalk (`../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline (the
  FedRAMP Low tailoring), cross-walked to the 17 practices of **FAR
  52.204-21** that define CMMC L1. Derivation per the Merge Rule:
  the union of the Low and LI-SaaS parent baselines is the Low
  baseline itself (the LI-SaaS subset adds nothing beyond it),
  inherited in full. This tier mixes Low and LI-SaaS forks across
  the map; this fork is **Low**, recorded in its spec sheet.

| Core function | Control families | How the build answers |
|---|---|---|
| Matter registry, membership, RBAC | AC-3, AC-6, IA-2 (hooks) | Membership is enforced before any matter-scoped read or write; the three-role matrix is enforced pre-mutation at two layers. FAR side: limit system access to authorized users and transactions. IA-2: identity is supplied by the embedding organization via user/role headers; the service ships hooks, not an identity provider |
| Source, document, search, annotation, citation registries | SI-10 | Every reference, checksum, and count is validated before any record or id exists; malformed input is rejected whole, never partially applied |
| Document checksums & verify-by-content | (implementation property) | SHA-256 via the standard library; see precision note (2) — no control is claimed for this at Low |
| Registry reporting & search | AU-2, AU-3 (Low side only) | Records are reviewable; reporting computes counts on read and nothing else |
| Audit log | AU-2, AU-3 (Low side only) | Append-only log including denied attempts; audit read restricted to the `audit_read` permission (admin only); no mutation API |
| Transport | SC-8 (partial) | TLS when a certificate is configured; encryption at rest is a deployment-layer control, stated plainly, not claimed here |

**Precision notes (this tier).** (1) Audit traces to the AU family
**on the FedRAMP Low side of the crosswalk only**: FAR 52.204-21
contains no audit practice, so no audit claim is made on the CMMC
side (and unlike at L2, the claim does **not** hold on both sides —
800-171's audit family 3.3 belongs to the Moderate tier). (2) Group
34's **SI-7** citation is deliberately **not** imported here: SI-7
is a Moderate selection, not a Low one. At this tier the checksum
and verify-by-content mechanics are stated as implementation
properties of the registry, exactly as Group 38 stated its
separation-of-duties precision. Group 34's AU-6 citation is likewise
not imported (not a Low selection); the append-only store and the
admin-gated audit read are implementation properties beyond AU-2 /
AU-3. (3) The Moderate/High apparatus from the sibling tiers
(hash-chained audit, fail-closed audit writes, logon lockout, the
auditor role) is out of scope for a Low/L1 build and is **not
inherited downward**.

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source
implementation whose features trace to the Low/L1 control families.

## Implementation contract (summary)

Identical to Group 34's contract — Python 3, **standard library
only**, package `lawenf` under `src/`, runnable and testable with
`PYTHONPATH=src`: `errors` (`LawEnfError`, `ValidationError`,
`NotFoundError`, `PermissionDenied`), `access` (User; roles
admin/member/viewer; nine actions), `audit` (append-only AuditLog),
`store` (LawEnfStore: the 11 core functions; ids sequential per
type — `mat-`, `src-`, `doc-`, `sea-`, `ann-`, `cit-`; failed
operations consume no id and change nothing), `service` (HTTP layer;
the only place query/note text may appear, SHA-256-hashed before the
store ever sees a value), `__main__` (`python -m lawenf serve`,
default port 8797; demo users alice=admin / bob=member /
carol=viewer). `tests/`: 82 unittest tests across 12 modules, every
test docstring tracing to a core function, a claim family, or a
control family; the negative controls and their live mutation
verification **in this tree** are recorded in `tests/README.md`
(membership-guard mutant → 5 failures; restored SHA-256-identical,
suite green).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Flock Safety Platform, FedRAMP Low; 0
  evidenced claims — the sheet is preserved in full regardless).
- Core implemented: **11 / 11** functions above, carried not
  claimed, at the Low/L1 baseline, privacy rule intact.
- Tests: **82 run, 82 passed**, including the mutation-verified
  negative controls (drill performed fresh in this tree).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions (this fork's own engines, named from its
description's own verbs):

- **License plate recognition engine & camera network** — LPR
  technology and the video camera network that feeds it, including
  plate reads and vehicle matching. Named as this fork's gap
  because its prose asserts it; under the category discipline it is
  an unclaimed-by-design exclusion for the substrate and is not
  built, in whole or in part.
- **Audio recognition sensors & detection** — the audio sensor
  layer and its recognition/detection function.
- **Video management & evidence-capture pipeline** — the
  accompanying software that captures, stores, and serves
  "objective evidence" from the camera/audio network. (The
  substrate's document registry is metadata + checksums over
  callers' own records; it captures nothing and stores no content.)
- **Camera/sensor hardware** — the manufactured devices themselves
  (cameras, sensors, readers); hardware is outside a software
  build entirely.
- **Public-safety collaboration & crime-analysis platform** — the
  inter-agency collaboration and community-safety layer the
  description's first sentence gestures at, as a platform function
  beyond this fork's devices.

Extended functions carried from the Group 34 category union
(specified in `../law-enforcement-l2/UNION-SPEC.md`, not
implemented): the legal corpora themselves; citation-validation
engines; editorial enhancement systems; corpus search & relevance
engines; AI/ML research assistance (0 claims at every tier of this
category); document content storage, rendering & redaction.

Category-discipline exclusions (standing, Groups 34/35 — 0 claims,
out of scope for a records substrate, none built): **surveillance,
facial recognition, predictive policing, real-time intelligence
feeds**. Of these, only surveillance-class function is asserted by
this fork's prose (as the LPR/camera/audio engines above); facial
recognition, predictive policing, and intelligence feeds appear
nowhere in its description and are not attributed to it.

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment);
demo identities are hooks, not an IdP — IA-2 stays with the
embedding organization.
