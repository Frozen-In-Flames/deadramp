# Learning Management L1 — merged build (Operation DeadRamp, Phase 2, remainder new sibling group)

This is the merged, clean-room implementation of the **Learning
Management L1** sibling group: **2 forks** from the FedRAMP
Marketplace — **FR2113157410** (Public Health Foundation TRAIN
Learning Network, FedRAMP Low) and **FR2135043135** (SRR
International CloudLCMS, FedRAMP LI-SaaS), both **CMMC L1**,
FedRAMP Certified — built as one open-source service from the
group's union spec (`UNION-SPEC.md`).

**Relationship to the L2 build, stated once.** Learning Management
already has a shipped build at L2 (`groups/learning-management-l2/`,
the PowerTrain singleton, FedRAMP Moderate). This is a **separate
build at the Low baseline in its own directory**, not an addition
to the L2 directory. The two builds share the category substrate:
the L2 core's records forms are carried down whole and flagged
*carried, not claimed*, and this build's baseline is authored fresh
at Low (AU-2/AU-3 only; the Moderate build's AU-6/AU-9 mappings are
deliberately not imported).

**The taxonomy outcome, stated plainly.** The L2 taxonomy (26
families defined from the L2 fork's own description) is applied
**verbatim** here — the extractor proves pattern equality by
parsing the L2 extractor, never re-tuning. Measured result:
**TRAIN claims 0 families** (it asserts multi-tenancy, branded
portals, tracking, continuing education, and certificates in its
own verbs, none of which is the L2 fork's literal phrasing) and
**CloudLCMS claims 1** (content standards & distribution, on
"SCORM 1.2"). Every asserted-but-unnamed function is itemized in
the union spec with a disposition; three of TRAIN's asserted
functions (organizations & portals, certificate awards, continuing
education) enter the core as records forms by explicit
core-boundary decision, and the rest are named gaps.

It was written from the union spec only: original code, no vendor
code, assets, or branding. Python 3, **standard library only**, no
external dependencies.

## The 17 core functions

Functions 1–14 are the carried category substrate; 15–17 are new
at this tier on this tier's own evidence.

1. **Learner registry (opaque references)** — learners (`lrn-`)
   known only by an opaque `ref` and a label, with an optional
   organization reference. No field can hold a real identifier.
2. **Course, content & lesson-plan catalog** — courses (`crs-`),
   content items (`cnt-`) whose `standard` takes the union of both
   tiers' own lists (the enum gains the `html` token on
   CloudLCMS's evidence), lesson plans (`les-`). Content may carry
   an external reference (linked external training); courses and
   content may carry an owning organization and a visibility.
3. **Events & registration management** — events (`evt-`) with
   optional capacity; registrations (`reg-`) whose seat counts
   are **derived at read**, never stored.
4. **Training authorization (SF-182) records** — authorizations
   (`aut-`) with recorded decisions; the decider is never the
   record's creator.
5. **Individual development plan records** — IDPs (`idp-`).
6. **Competency records** — definitions (`cpt-`) and learner
   competency records (`lcr-`) with levels recorded **verbatim**.
7. **Learner progress records** — progress (`prg-`) per learner
   and course. Records only; no content delivery.
8. **Learning experience records** — LRS statements (`stm-`) in an
   exact 8-key shape with **no score field**; result text verbatim.
9. **Compliance & derived status** — assignments (`asg-`) whose
   status (`current`/`overdue`/`completed`) is **derived at read**
   from the due date, progress records, and an explicit `as_of`.
   This is the signature invariant and the negative control.
10. **Workflow & notification registries** — workflow definitions
    (`wfl-`) registered as data that **never execute**;
    notification records (`ntf-`).
11. **Search & summary reporting** — substring search (now
    including organizations) and counts-only summary reporting.
    Counts — never scores.
12. **API access** — every function over REST/JSON.
13. **Access control** — roles `admin`, `instructor`, `learner`,
    `auditor`; learner scope (a learner reads only their own
    records and the catalog visible to them). Demo identities are
    hooks, not an IdP (IA-2 stays with the embedding organization).
14. **Audit log** — append-only; every mutation, report read, and
    denied attempt.
15. **Organization & portal registry** — organizations (`org-`):
    opaque ref, label, portal label. Anchor for learner membership
    and catalog visibility: an item is `community` (available to
    all) or `organization` (restricted internally), enforced for
    learner-role catalog reads. Portal rendering is a gap.
16. **Certificate award records** — certificates (`crt-`):
    append-only award facts (learner, course, title, award date).
    Rendering, delivery, and verification are gaps.
17. **Continuing education records** — CE records (`ceu-`) with
    the credit text recorded **verbatim**, never parsed, summed,
    or converted. Credit accounting beyond records is a gap.

## Run it

```
PYTHONPATH=src python3 -m lms serve --host 127.0.0.1 --port 8794
```

Demo users: `alice` (admin), `bob` (instructor), `carol`
(learner), `dana` (auditor), via `X-User` / `X-Role` headers.
Endpoints mirror the L2 build's, plus `/organizations`,
`/certificates`, and `/continuing-education`.

## Tests

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**137 tests, all passing**, including spec-integrity pins (census
membership, taxonomy-verbatim, the literal claim table) and the
mutation-verified compliance-derivation negative control: patching
the overdue branch of `_derive_status` to return `"current"` fails
exactly **9** tests; the store was restored SHA-256-identical.
Full record in `tests/README.md`.

## Gaps

The union spec names 23 extended functions (the carried L2 Extended
set plus this tier's own: the LCMS authoring environment, course
posting workflow, branded portal rendering, CE management engine,
certificate issuance & verification service, system integration
engines). They are specified, not implemented, and are registered
in the repo-root `GAPS.md` for the final batch when this group
ships.
