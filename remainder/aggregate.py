"""Remainder census aggregation: class_all.json + uncovered.json -> remainder.json.
Buckets: addition (extends a shipped group) / new sibling group / new singleton /
untiered set / no-signal set. Deterministic; counts reproducible from output."""
import json, glob, re
from collections import defaultdict, Counter

unc = json.load(open('remainder/uncovered.json'))
cls = {e['fork_id']: e for e in json.load(open('remainder/class_all.json'))}

# shipped groups: (spec category, tier) -> dir; normalize official CRM name to spec form
shipped = {}
for f in glob.glob('groups/*/specs/specs.json'):
    d = json.load(open(f))
    for r in (d if isinstance(d, list) else d.get('specs', d)):
        shipped.setdefault((r['deadramp_category'], r['cmmc_tier']), f.split('/')[1])
def norm_cat(c):
    return 'CRM' if c == 'Customer Relations Management (CRM)' else c

forks_out = []
for u in unc:
    e = cls[u['fork_id']]
    pc = e.get('proposed_category')
    is_new = bool(pc and pc.startswith('NEW: '))
    cat = pc[5:] if is_new else pc
    forks_out.append({
        'fork_id': u['fork_id'], 'vendor': u['vendor'], 'product': u['product'],
        'service_model': u['service_model'], 'authorization_status': u['authorization_status'],
        'fedramp_impact_level': u['fedramp_impact_level'],
        'current_category': u['category'], 'current_tier': u['cmmc_tier'],
        'proposed_category': cat, 'proposed_category_is_new': is_new,
        'new_category_reason': e.get('new_category_reason'),
        'citations': e.get('citations', []),
        'no_signal': bool(e.get('no_signal')), 'no_signal_reason': e.get('no_signal_reason'),
        'platform_general': bool(e.get('platform_general')),
        'classifier_note': e.get('note') or None,
        'source_url': u['source_url'],
    })

# bucket assignment
groups_by_key = defaultdict(list)
for fo in forks_out:
    if fo['no_signal']:
        fo['bucket'] = 'no_signal'; fo['build_unit'] = 'no-signal-set'; continue
    key = (fo['proposed_category'], fo['current_tier'])
    groups_by_key[key].append(fo)
for (cat, tier), members in groups_by_key.items():
    if tier is None:
        bucket, unit = 'untiered_set', f"untiered:{cat}"
    elif (norm_cat(cat), tier) in shipped and not any(m['proposed_category_is_new'] for m in members):
        bucket, unit = 'addition', f"addition:{shipped[(norm_cat(cat), tier)]}"
    elif len(members) >= 2:
        bucket, unit = 'new_sibling_group', f"new-group:{cat}|{tier}"
    else:
        bucket, unit = 'new_singleton', f"new-singleton:{cat}|{tier}"
    for m in members:
        m['bucket'] = bucket; m['build_unit'] = unit

units = {}
for fo in forks_out:
    u = units.setdefault(fo['build_unit'], {
        'unit_id': fo['build_unit'], 'kind': fo['bucket'],
        'category': fo['proposed_category'], 'tier': fo['current_tier'],
        'extends_group': None, 'fork_ids': []})
    u['fork_ids'].append(fo['fork_id'])
for u in units.values():
    u['size'] = len(u['fork_ids'])
    if u['kind'] == 'addition':
        u['extends_group'] = u['unit_id'].split(':', 1)[1]
    if u['kind'] == 'no_signal':
        u['category'] = None; u['tier'] = None

kind_rank = {'addition': 0, 'new_sibling_group': 1, 'new_singleton': 2}
tiered_units = sorted([u for u in units.values() if u['kind'] in kind_rank],
                      key=lambda u: (-u['size'], kind_rank[u['kind']], u['category'], u['tier']))
untiered_units = sorted([u for u in units.values() if u['kind'] == 'untiered_set'],
                        key=lambda u: (-u['size'], u['category']))
nosignal_units = [u for u in units.values() if u['kind'] == 'no_signal']
build_order = [u['unit_id'] for u in tiered_units + untiered_units + nosignal_units]

counts = Counter(fo['bucket'] for fo in forks_out)
out = {
    'census': 'Operation DeadRamp Phase 2 remainder census',
    'generated_from': 'forks.json + groups/*/specs/specs.json (coverage) + raw/data_dump.json service_desc via remainder/uncovered.json; classifications in remainder/class_chunk_1..6.json',
    'reconciliation': {'total_forks': 781, 'covered_by_shipped_groups': 498,
                       'uncovered': len(forks_out),
                       'classified': counts['addition'] + counts['new_sibling_group'] + counts['new_singleton'] + counts['untiered_set'],
                       'no_signal': counts['no_signal']},
    'bucket_counts': dict(counts),
    'missing_descriptions': [fo['fork_id'] for fo in forks_out if fo['no_signal_reason'] == 'missing'],
    'new_category_proposals': [],
    'build_units': tiered_units + untiered_units + nosignal_units,
    'build_order': build_order,
    'forks': forks_out,
}
newprops = defaultdict(list)
for fo in forks_out:
    if fo['proposed_category_is_new']:
        newprops[fo['proposed_category']].append(fo)
for name, members in sorted(newprops.items()):
    out['new_category_proposals'].append({
        'name': name, 'fork_ids': [m['fork_id'] for m in members],
        'tiers': sorted({m['current_tier'] for m in members}, key=lambda t: str(t)),
        'justification': members[0]['new_category_reason']})
json.dump(out, open('remainder.json', 'w'), indent=1)
print('buckets:', dict(counts))
print('units:', len(out['build_units']), '| tiered units:', len(tiered_units), '| untiered sets:', len(untiered_units))
print('new category proposals:', [(p['name'], len(p['fork_ids'])) for p in out['new_category_proposals']])
print('missing descriptions:', out['missing_descriptions'])
add = [u for u in tiered_units if u['kind'] == 'addition']
print('additions extend', len(add), 'shipped groups, forks:', sum(u['size'] for u in add))
