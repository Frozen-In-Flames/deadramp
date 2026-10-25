const fs = require('fs');
const dump = JSON.parse(fs.readFileSync('raw/data_dump.json', 'utf8'));
const fd = dump[3].data.fedRAMPData.data;
const P = fd.Products;
const TAXONOMY = fd.Filters.product.business_categories;
const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
const slug2name = {};
for (const c of TAXONOMY) slug2name[slug(c)] = c;

function categoryOf(p) {
  if (p.business_categories && p.business_categories.length) return p.business_categories[0];
  const m = String(p.filter_classes || '').match(/filter-business-function-([A-Za-z0-9\-]+?)(?= filter-|$)/);
  if (m) { const name = slug2name[slug(m[1])]; if (name) return name; }
  return 'Uncategorized (none in source)';
}
function tierOf(impact) {
  switch (impact) {
    case 'Low': return 'L1';
    case 'LI-SaaS': return 'L1'; // LI-SaaS is FedRAMP's Low-baseline tailoring for SaaS
    case 'Moderate': return 'L2';
    case 'High': return 'L3-adjacent';
    default: return null; // 'Unknown' — no baseline assigned in source
  }
}
const entries = P.map(p => ({
  vendor: p.csp,
  product: p.cso,
  service_model: (() => { const parts = (Array.isArray(p.service_model) ? p.service_model : [p.service_model]).filter(x => x && String(x).trim()); return parts.length ? parts.join(', ') : null; })(),
  fedramp_impact_level: p.impact_level,
  authorization_status: p.status,
  category: categoryOf(p),
  cmmc_tier: tierOf(p.impact_level),
  source_url: 'https://www.fedramp.gov/marketplace/products/' + p.id + '/'
}));
entries.sort((a, b) =>
  a.vendor.localeCompare(b.vendor) || a.product.localeCompare(b.product) ||
  a.fedramp_impact_level.localeCompare(b.fedramp_impact_level));
fs.writeFileSync('forks.json', JSON.stringify(entries, null, 1));
console.log('wrote forks.json with', entries.length, 'entries');
