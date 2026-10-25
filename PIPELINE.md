# Phase 2: the build pipeline

Phase 1 mapped all 781 forks. Phase 2 builds them, open source, one merged implementation per sibling group.

## Why sibling groups first

781 vendor offerings collapse into 36 sibling groups (same function, same tier) plus singletons. Building one open implementation per sibling group, under the Merge Rule, covers every fork in the group at once: the merged build takes the union of the group's control baselines at the group's tier. Largest group first, so coverage per build is maximized from day one.

Build order (by group size): Analytics L2 (128 forks) is group one. The full order is computed from MAP.md sibling groups, descending.

## The per-group pipeline (reusable system, then instances)

1. **Spec.** For each fork in the group, extract the public functional surface: marketplace listing, public documentation, public APIs, underlying open standards. One spec sheet per fork, all sources cited. Where forks in the group differ in function, the differences are listed, not averaged away.
2. **Merge design.** The union spec for the group: every function any sibling ships, organized once. Control baseline = union of the group's baselines at the group's tier, with traceability back to the contributing forks.
3. **Build.** Clean-room implementation of the union spec on open standards. No proprietary code, assets, or branding from any vendor fork.
4. **Verify.** Tests against the spec sheet of every fork in the group (a function claimed by any sibling must demonstrably work), control-baseline check against the tier, and the standard DeadRamp verification pass: independent re-verification before anything is called shipped.
5. **Ship.** The group build lands in this repo as a directory per group, tagged, with release notes stating what it covers and why (which forks, which tier, which controls), per the project's release-notes rule.

## The remainder

- Singleton categories (groups of one) build after the sibling groups, same pipeline, group size one.
- The 181 uncategorized offerings get spec work from their own public documentation; a fork with no declared function gets its category from its docs, cited, never guessed.
- The 141 untiered offerings build to their documented control claims; tier stays null in the registry until the source publishes a baseline.

## Standing rules

Public sources only. Clean room always. Every claim in a release traces to a spec sheet, a test, or a control. Coverage is reported as forks covered out of 781, updated at every ship.

## The gap batch (Aries, Oct 25, 2026)

All gaps from all groups — extended functions specified but not implemented, and baseline requirements gap-listed at the platform layer — are registered in GAPS.md at the repo root when each group ships, and worked as ONE final batch at the very end of the repo, after the last sibling group and the remainder forks. Groups name their gaps precisely and keep moving; nothing closes a gap except the final batch, and the registry is the batch's worklist.
