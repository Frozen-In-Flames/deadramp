const fs = require('fs');
const F = JSON.parse(fs.readFileSync('forks.json', 'utf8'));
const N = F.length;
const count = (fn) => { const m = new Map(); for (const f of F) { const k = fn(f); m.set(k, (m.get(k) || 0) + 1); } return m; };
const byImpact = count(f => f.fedramp_impact_level);
const byTier = count(f => f.cmmc_tier === null ? '(none — impact Unknown)' : f.cmmc_tier);
const byStatus = count(f => f.authorization_status);
const byCat = count(f => f.category);
const vendors = new Set(F.map(f => f.vendor));
const models = ['IaaS', 'PaaS', 'SaaS'];
const mem = { IaaS: 0, PaaS: 0, SaaS: 0 };
let multi = 0, noModel = 0;
for (const f of F) {
  if (!f.service_model) { noModel++; continue; }
  const parts = f.service_model.split(', ');
  if (parts.length > 1) multi++;
  for (const p of parts) mem[p]++;
}
const L = [];
L.push('# Operation DeadRamp — Phase 1: The Fork Map');
L.push('');
L.push('Every FedRAMP Marketplace product listing, mapped on two axes: FUNCTION (marketplace business category + service model) and TRUST TIER (FedRAMP impact level crosswalked to a CMMC tier). Registry: `forks.json` (781 entries). Crosswalk: `crosswalk.md`.');
L.push('');
L.push('## Totals');
L.push('');
L.push(`- **Offerings (forks): ${N}**`);
L.push(`- **Vendors: ${vendors.size}** (distinct provider names, verbatim from the source)`);
L.push(`- Authorized today (status "FedRAMP Certified"): ${byStatus.get('FedRAMP Certified')}. The remaining ${N - byStatus.get('FedRAMP Certified')} are pipeline listings (in process / ready / initial implementation) — included because the map covers the whole marketplace, each with its status recorded.`);
L.push('');
L.push('### By authorization status');
L.push('');
L.push('| Status | Count |');
L.push('|---|---:|');
for (const [k, v] of [...byStatus.entries()].sort((a, b) => b[1] - a[1])) L.push(`| ${k} | ${v} |`);
L.push('');
L.push('### By FedRAMP impact level');
L.push('');
L.push('| Impact level | Count |');
L.push('|---|---:|');
for (const k of ['Low', 'LI-SaaS', 'Moderate', 'High', 'Unknown']) if (byImpact.has(k)) L.push(`| ${k} | ${byImpact.get(k)} |`);
L.push('');
L.push('### By CMMC tier (crosswalk)');
L.push('');
L.push('| CMMC tier | Count | FedRAMP levels feeding it |');
L.push('|---|---:|---|');
L.push(`| L1 | ${byTier.get('L1')} | Low (${byImpact.get('Low')}) + LI-SaaS (${byImpact.get('LI-SaaS')}) |`);
L.push(`| L2 | ${byTier.get('L2')} | Moderate (${byImpact.get('Moderate')}) |`);
L.push(`| L3-adjacent | ${byTier.get('L3-adjacent')} | High (${byImpact.get('High')}) |`);
L.push(`| (none — impact Unknown) | ${byTier.get('(none — impact Unknown)')} | no baseline assigned in source yet |`);
L.push('');
L.push('### By service model');
L.push('');
L.push('An offering that lists several models counts in each (membership); 767 offerings state a model, ' + noModel + ' state none, ' + multi + ' span more than one layer.');
L.push('');
L.push('| Service model | Offerings (membership) |');
L.push('|---|---:|');
for (const m of models) L.push(`| ${m} | ${mem[m]} |`);
L.push('');
L.push('## Categories');
L.push('');
L.push('The category axis is the FedRAMP Marketplace\'s own business-category taxonomy (36 categories). Each offering takes the first business function declared in its source listing (see Coverage note).');
L.push('');
L.push('| Category | Offerings |');
L.push('|---|---:|');
for (const [k, v] of [...byCat.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))) L.push(`| ${k} | ${v} |`);
L.push('');
// Sibling groups
L.push('## Sibling groups (merge candidates)');
L.push('');
L.push('Siblings = same category + same CMMC tier: direct substitutes for each other. Under the Merge Rule (see `crosswalk.md`), **sibling groups are the merge candidates** — forks in a group are the natural parents of a merged fork, which would take the union of their control baselines at the group\'s tier. Groups of one are omitted; the "Uncategorized (none in source)" bucket and untiered (impact Unknown) offerings cannot form sibling groups because they share no declared function or tier.');
L.push('');
const groups = new Map();
for (const f of F) {
  if (f.category === 'Uncategorized (none in source)' || f.cmmc_tier === null) continue;
  const k = f.category + ' || ' + f.cmmc_tier;
  if (!groups.has(k)) groups.set(k, []);
  groups.get(k).push(f);
}
const sib = [...groups.entries()].filter(([, v]) => v.length >= 2).sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
const sibForks = sib.reduce((s, [, v]) => s + v.length, 0);
L.push(`**${sib.length} sibling groups covering ${sibForks} forks.**`);
L.push('');
for (const [k, members] of sib) {
  const [cat, tier] = k.split(' || ');
  L.push(`### ${cat} — ${tier} (${members.length})`);
  L.push('');
  for (const m of members.sort((a, b) => a.product.localeCompare(b.product) || a.vendor.localeCompare(b.vendor))) {
    L.push(`- ${m.product} — ${m.vendor}`);
  }
  L.push('');
}
// Stack relations
L.push('## Stack relations');
L.push('');
L.push('Stack rule (from the concept brief): IaaS forks sit under PaaS forks, which sit under SaaS forks. Read off the service-model data:');
L.push('');
L.push(`- **Layer 1 — IaaS (foundation): ${mem.IaaS} offerings** list IaaS.`);
L.push(`- **Layer 2 — PaaS (platform): ${mem.PaaS} offerings** list PaaS.`);
L.push(`- **Layer 3 — SaaS (application): ${mem.SaaS} offerings** list SaaS.`);
L.push(`- ${multi} offerings span layers (they list 2–3 models) and ${noModel} list no model in the source.`);
L.push('');
L.push('Which categories live at which layer (membership counts; a multi-model offering appears in each of its layers):');
L.push('');
L.push('| Category | IaaS | PaaS | SaaS | No model stated |');
L.push('|---|---:|---:|---:|---:|');
const cats = [...byCat.keys()].sort((a, b) => byCat.get(b) - byCat.get(a) || a.localeCompare(b));
for (const c of cats) {
  const rows = F.filter(f => f.category === c);
  const cm = { IaaS: 0, PaaS: 0, SaaS: 0, none: 0 };
  for (const f of rows) {
    if (!f.service_model) { cm.none++; continue; }
    for (const p of f.service_model.split(', ')) cm[p]++;
  }
  L.push(`| ${c} | ${cm.IaaS} | ${cm.PaaS} | ${cm.SaaS} | ${cm.none} |`);
}
L.push('');
L.push('Reading: pure-infrastructure categories (Storage, Network Management, System Administration) hold most of the true IaaS/PaaS layer; the SaaS layer carries nearly everything else. A DeadRamp build order that respects the stack builds Layer 1 categories first, because PaaS and SaaS forks sit on them.');
L.push('');
L.push('## Coverage note (honest)');
L.push('');
L.push('- **Source.** The official FedRAMP Marketplace product dataset published by the General Services Administration, embedded in the marketplace products page at https://www.fedramp.gov/marketplace/products/ (the old marketplace.fedramp.gov now redirects there). The dataset\'s own metadata: produced by GSA, last changed 2026-10-22. Fetched 2026-10-25; raw page and extracted dataset are cached in `raw/`. Every registry entry\'s `source_url` is that offering\'s live marketplace product page.');
L.push('- **Completeness.** The registry contains all 781 product records in the source dataset — classic Rev5 authorizations (659), FedRAMP 20x (95), and 20x Pilot (27) listings alike, at every status from Certified to Initial Implementation. Two vendor submissions (FedRAMP IDs FR2634659095 and FR2635930482) are absent because GSA\'s own indexer skipped them for validation errors in the vendor-submitted data; they appear in the source\'s SkippedEntities list and cannot be mapped until the source includes them.');
L.push('- **Verification.** All headline counts were recounted by an independent method (regex over the raw page text) and matched forks.json exactly for every impact level and every status; the Certified count (547) also matches the marketplace\'s own published Metrics figure.');
L.push('- **Known gaps in the source data itself.** 181 offerings declare no business function, so their category is recorded as "Uncategorized (none in source)" rather than guessed. 141 offerings have impact level "Unknown" in the source (no baseline assigned yet), so they carry no CMMC tier. 14 offerings state no service model. 13 vendor+product name pairs appear twice under different FedRAMP IDs (e.g., the same product authorized on two paths); each ID is a separate marketplace offering, so each is a separate registry entry.');
L.push('- **Category rule.** Category = the first business function in the offering\'s marketplace listing (from its `business_categories` field when present, otherwise the first business-function filter tag in the same listing). Multi-function offerings exist (some declare up to 10 functions); only the first is used as the primary category so every fork has exactly one sibling group.');
L.push('- **LI-SaaS.** FedRAMP\'s LI-SaaS is a tailored subset of the Low baseline for SaaS offerings; it is crosswalked to CMMC tier L1 with Low, and its source value "LI-SaaS" is preserved in the registry.');
L.push('');
fs.writeFileSync('MAP.md', L.join('\n'));
console.log('MAP.md written,', L.length, 'lines; sibling groups:', sib.length, 'forks in groups:', sibForks);
