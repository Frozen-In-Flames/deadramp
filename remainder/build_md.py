import json
R = json.load(open('remainder.json'))
F = {f['fork_id']: f for f in R['forks']}
U = {u['unit_id']: u for u in R['build_units']}
def forkline(fid):
    f = F[fid]
    return f"- `{fid}` — {f['vendor']} / {f['product']}"
def unit_forks(uid):
    return '\n'.join(forkline(x) for x in U[uid]['fork_ids'])
L = []
L.append('# Operation DeadRamp — Phase 2 Remainder Census')
L.append('')
L.append('The worklist for everything Phase 2 has not built yet: every fork not covered by the 36 sibling groups and 19 singletons already shipped. Classification pass only — nothing here is built, and no category in this document is a claim: each proposed category is assigned from the fork\'s own marketplace description, with the evidencing sentence(s) quoted verbatim in `remainder.json`, or the fork is recorded as carrying no functional signal.')
L.append('')
L.append('## Reconciliation')
L.append('')
L.append('| Count | Forks |')
L.append('|---|---:|')
L.append('| Marketplace total (forks.json) | 781 |')
L.append('| Covered by the 55 shipped groups (fork ID present in a shipped `specs/specs.json`) | 498 |')
L.append('| **Uncovered — this census** | **283** |')
L.append('| Classified to a proposed category | 260 |')
L.append('| No functional signal in the cached description | 23 |')
L.append('| Descriptions missing from the cache entirely | 0 |')
L.append('')
L.append('Uncovered composition: 142 tiered forks with no source category, 102 untiered forks with a source category, 39 untiered and uncategorized. Buckets: **107** category additions to shipped groups, **6** forks in new sibling groups, **10** new singletons, **137** forks in untiered sets, **23** no-signal.')
L.append('')
L.append('## Method')
L.append('')
L.append('- Coverage is mechanical: a fork is covered iff its FedRAMP ID (from its `forks.json` source URL) appears in some shipped group\'s spec sheet. 498 covered / 283 uncovered, zero duplicates.')
L.append('- Each uncovered fork\'s description was read from the cached GSA dataset (`raw/data_dump.json`, `service_desc`, joined by FedRAMP ID). Every one of the 283 has a cached description; none had to be fetched.')
L.append('- A proposed category names the fork\'s **primary function in its own description sentences**, quoted verbatim as citations in `remainder.json`. Precedents from the shipped builds bind throughout: a filing label (`business_categories`) is not a claim; catalogue prose about other products or hosted third-party applications does not categorize the fork; sentences placing a capability out of scope do not count; assurance/hosting prose alone is no signal.')
L.append('- Coordinator verification: all 283 fork IDs present exactly once; every citation re-checked programmatically as a verbatim substring of its description after whitespace normalization — **0 failures**; every proposed category is in the 36-category marketplace vocabulary or is one of the 4 new-category proposals below.')
L.append('- Tier is never invented: untiered forks (impact Unknown in the source) stay tier-null and build to documented control claims, per PIPELINE.md.')
L.append('')
L.append('## Proposed build order')
L.append('')
L.append('Tiered units first, largest first (the Phase 2 pattern); then untiered sets, largest first; the no-signal set last, because those forks need live documentation checks before any category can be assigned honestly.')
L.append('')
n = 0
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'addition':
        n += 1; L.append(f"{n}. **Addition** — {u['category']} | {u['tier']} ({u['size']} forks) extends `groups/{u['extends_group']}/`")
    elif u['kind'] == 'new_sibling_group':
        n += 1; L.append(f"{n}. **New sibling group** — {u['category']} | {u['tier']} ({u['size']} forks)")
    elif u['kind'] == 'new_singleton':
        n += 1; L.append(f"{n}. **New singleton** — {u['category']} | {u['tier']} (1 fork)")
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'untiered_set':
        n += 1; L.append(f"{n}. **Untiered set** — {u['category']} ({u['size']} forks, tier null)")
L.append(f"{n+1}. **No-signal set** — 23 forks; live documentation check required before classification (flagged, not fetched).")
L.append('')
L.append('## Category additions (extend a shipped group\'s union spec)')
L.append('')
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'addition':
        L.append(f"### {u['category']} | {u['tier']} → `groups/{u['extends_group']}/` ({u['size']})")
        L.append(''); L.append(unit_forks(uid)); L.append('')
L.append('## New sibling groups')
L.append('')
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'new_sibling_group':
        L.append(f"### {u['category']} | {u['tier']} ({u['size']})")
        L.append(''); L.append(unit_forks(uid)); L.append('')
L.append('## New singletons')
L.append('')
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'new_singleton':
        f = F[u['fork_ids'][0]]
        L.append(f"- **{u['category']} | {u['tier']}** — `{f['fork_id']}` {f['vendor']} / {f['product']}")
L.append('')
L.append('## Untiered sets (proposed category, tier null — build to documented control claims)')
L.append('')
for uid in R['build_order']:
    u = U[uid]
    if u['kind'] == 'untiered_set':
        L.append(f"### {u['category']} ({u['size']})")
        L.append(''); L.append(unit_forks(uid)); L.append('')
L.append('## New category proposals')
L.append('')
L.append('Four proposals, each justified from the fork\'s own description (full text in `remainder.json`). Accepting or folding each is a decision for the build phase; the forks sit in the buckets above under their proposed names in the meantime.')
L.append('')
for p in R['new_category_proposals']:
    L.append(f"### NEW: {p['name']} ({len(p['fork_ids'])} fork(s), tiers: {', '.join(str(t) for t in p['tiers'])})")
    L.append('')
    L.append(p['justification'])
    L.append('')
    for fid in p['fork_ids']: L.append(forkline(fid))
    L.append('')
L.append('Coordinator note on **Contract Management**: two chunk passes independently placed procurement *operations* (AI sourcing, RFP tooling) in Operations Management. The Unison pair is different in kind — the contract lifecycle system of record for federal acquisition — which is why it is proposed as its own category rather than folded into Operations Management. If the build phase prefers fewer categories, Operations Management L2 is the fold target; the two forks would become additions there.')
L.append('')
L.append('## No-signal set (23 forks)')
L.append('')
L.append('Every one of the 23 has a cached description; the reason is **prose-only** in all 23 cases (no description is missing). 17 of the 23 are general-platform offerings (`platform_general`) whose prose covers many functions with no primary one. These forks need a live documentation check before classification — flagged here, not fetched, per census scope.')
L.append('')
for f in R['forks']:
    if f['no_signal']:
        pg = ' — general platform' if f['platform_general'] else ''
        L.append(f"- `{f['fork_id']}` — {f['vendor']} / {f['product']} (tier: {f['current_tier'] or 'null'}{pg}) — {f['classifier_note'] or 'prose only'}")
L.append('')
L.append('Two of the 23 deserve a specific flag: `F1305132147` (Ex Libris Higher-Ed Platform) and `FR1818459251` (SirsiDynix EOS.Web) are both library-system offerings whose descriptions never state the library function in a citable sentence — one lists component product names only, the other speaks generically about the vendor\'s ILS offerings. A "Library Systems" category may well be the honest home for both, but under the citation rule that requires the live product documentation, so both stay no-signal in this census.')
L.append('')
L.append('Boundary set, recorded rather than silently resolved: managed-hosting platforms whose descriptions emphasize administration services actually performed (setup, configuration, patching, hardening, support) were classified System Administration, while pure infrastructure/platform prose (the IBM platform bundles, Elastic Cloud, Oracle Cloud Infrastructure-Government Cloud, the Treasury/USDA hosting environments) was marked no-signal. The line is thin and the build phase may redraw it; every fork on both sides of it is flagged `platform_general` in `remainder.json`.')
L.append('')
L.append('## Judgment patterns worth knowing')
L.append('')
L.append('- **Filed category vs description:** of the 102 categorized uncovered forks, the description-based proposal agrees with the filed category for 56 and differs for 46 (2 of the 46 are no-signal). The largest single flow is forks filed under Artificial Intelligence (AI) whose own descriptions describe an operational tool — AI as technique, not function — landing in Operations Management, Development Tools, Data Management, GRC, Cybersecurity, Construction, and Research. The second flow is Cybersecurity-filed forks whose descriptions center on compliance and evidence automation, landing in GRC. Each reclassification carries its citation in `remainder.json`.')
L.append('- **Duplicate authorization pairs** (same product, two FedRAMP IDs, identical descriptions) were classified identically: Enablement® (FR2628647239 / FR2635930439), Symantec Gov Cloud Security (FR2232465502 / FR2232465502A), Cisco Security Cloud for Government (FR2304757473 / FR2304757473A), IBM Platform Services for Government (F1208031461 / F1208031461A, both no-signal), Samsara (FR2633153272 / FR2700857493), Specset (FR2631258135 / FR2631747321 — its own description states the second ID is a duplicate pending retirement).')
L.append('- **Truncated or anomalous descriptions**, classification made from intact sentences and flagged in entry notes: Symantec GCS pair (text ends mid-word), Concourse Platform (ends promising a capability list that does not follow), Replit for Government (a gap where the agent\'s name should be), Silkline (one anomalous scope sentence, ignored under the catalogue/scope precedents).')
L.append('')
L.append('## Files')
L.append('')
L.append('- `remainder.json` — the machine-readable census: all 283 forks with registry fields, proposed category, verbatim citations, bucket and build unit; the 74 build units; the proposed build order. All counts in this document are reproducible from it (`remainder/aggregate.py`).')
L.append('- `remainder/` — census scratch: `uncovered.json` (the 283 with descriptions), `chunk_1..6.json` (classifier inputs), `class_chunk_1..6.json` (classifier outputs), `class_all.json` (merged), `raw_products.json` (extracted raw records), `aggregate.py`, `build_md.py`.')
L.append('')
open('REMAINDER.md', 'w').write('\n'.join(L) + '\n')
print('REMAINDER.md written:', len(L), 'lines')
