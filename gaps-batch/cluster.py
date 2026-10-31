import re, json, collections
entries = json.load(open('gaps-batch/entries.json'))

def head(t):
    return re.split(r'\(|—|;|,', t)[0].strip()

# Ordered families: (cluster_id, canonical name, regex over full entry text)
FAMILIES = [
 ("platform-mfa", "Platform: MFA / authenticator management (IA-2, IA-5)", r"\bIA-2\b|\bIA-5\b|\bMFA\b|authenticator management|stronger authentication"),
 ("platform-fips", "Platform: FIPS-validated cryptography (SC-13)", r"\bSC-13\b|FIPS[-\s]validated|FIPS-validated cryptography"),
 ("platform-encryption-rest", "Platform: encryption at rest (SC-28)", r"\bSC-28\b|encryption at rest"),
 ("platform-audit-retention", "Platform: audit retention enforcement (AU-11)", r"\bAU-11\b|audit retention"),
 ("platform-session", "Platform: session lock / termination (AC-11/AC-12)", r"\bAC-11\b|\bAC-12\b|session lock"),
 ("platform-umbrella", "Platform layer umbrella entries", r"^Platform layer"),
 ("proctoring", "Remote proctoring & identity proofing", r"proctoring"),
 ("identity-provider", "Identity provider / SSO / federation / directory", r"identity provider|single sign-on|\bSSO\b|federated identity|identity federation|directory service|identity management service|identity and access management layer"),
 ("esignature", "E-signature", r"e-signature|esignature"),
 ("file-transfer", "Managed file transfer transport", r"file transfer"),
 ("key-management", "Encryption implementation & key / certificate lifecycle", r"key management|key & certificate|certificate lifecycle|encryption implementation|key lifecycle"),
 ("media-transport", "Media transport (voice / video / telephony / streaming)", r"media transport|telephony|video|voice|streaming|contact center"),
 ("assessment-automation", "Compliance assessment & KSI automation", r"assessment|ksi"),
 ("workflow-execution", "Workflow / process execution & automation engines", r"workflow|process-automation|process automation|automation engine"),
 ("integration-transport", "Integration transport / connector engines / API runtime", r"integration|connector|api gateway|integrations"),
 ("search-engine", "Search & indexing engines", r"search|indexing"),
 ("notifications", "Notification & reminder engines", r"notification|reminder"),
 ("monitoring", "Monitoring / observability / detection / telemetry", r"monitoring|observability|detection|telemetry|alerting|alerts"),
 ("ml-engines", "AI / ML model engines & inference", r"ai/ml|machine learning|predictive ml|learned inference|ml model|ai model|ai assistance|ai recommendation|ai grading|ai/ analytics"),
 ("scoring", "Scoring & grading engines", r"scoring|grading"),
 ("billing", "Billing / invoicing / payment engines", r"billing|invoicing|payment|finops"),
 ("backup-dr", "Backup & disaster-recovery execution", r"backup|disaster.recovery|recovery product|recovery orchestration"),
 ("retention-execution", "Retention / archiving / preservation execution", r"retention|archiving|preservation"),
 ("audit-engines", "Audit management & workbench engines", r"audit management|audit workbench"),
 ("hosting-platform", "Hosting platform / provisioning / orchestration operations", r"hosting|landing.zone|tenant provisioning|provisioning|orchestration|platform operation|platform layer"),
 ("knowledge", "Knowledge management & knowledge base", r"knowledge"),
 ("content-engines", "Content / document processing & generation engines", r"content processing|document processing|document generation|content authoring|course.*authoring|authoring tool"),
 ("cdn", "CDN / delivery network / runtime serving", r"\bCDN\b|delivery network|runtime site serving"),
 ("reporting-bi", "Reporting / BI / analytics engines beyond records", r"business intelligence|reporting|analytics|visualization|forecasting"),
]
compiled = [(cid, name, re.compile(rx, re.I)) for cid, name, rx in FAMILIES]

def classify(e):
    t = e['text']
    for cid, name, rx in compiled:
        if rx.search(t):
            return cid, name
    h = head(t)
    return 'single:' + h, h

out = []
clusters = collections.defaultdict(list)
for i, e in enumerate(entries):
    cid, name = classify(e)
    row = {'idx': i, 'section': e['section'], 'text': e['text'], 'cluster': cid, 'cluster_name': name}
    out.append(row)
    clusters[cid].append(row)

json.dump(out, open('gaps-batch/inventory.json','w'), indent=1)
multi = {k: v for k, v in clusters.items() if not k.startswith('single:')}
singles = {k: v for k, v in clusters.items() if k.startswith('single:')}
print('total entries:', len(out))
print('family clusters:', len(multi), 'covering', sum(len(v) for v in multi.values()), 'entries')
print('singleton clusters:', len(singles), 'covering', sum(len(v) for v in singles.values()), 'entries')
print('total clusters:', len(clusters))
print()
for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1])):
    secs = len(set(x['section'] for x in v))
    print(f'{len(v):4d} entries / {secs:3d} sections  {v[0]["cluster_name"]}')
