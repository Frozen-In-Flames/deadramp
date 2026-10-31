# Artifacts — Cloud Infrastructure & Hosting, untiered set

Build provenance and recorded artifacts for the untiered set's
single fork, F1403283529 (Project Hosts Inc. / GSS One - Azure).
The extractor is `scratch/extract.py` (gitignored scratch); this
file is the durable record of what it did.

## Taxonomy-verbatim proof (run before tagging)

The TAXONOMY literal was AST-parsed out of the founding group's
extractor (`../cloud-infrastructure-hosting-l2/scratch/extract.py`,
parsed, never executed, never re-typed) — 17 families. Re-applying
it by the founding method (the founding `split_units` +
`claims_for`, including the SAP catalogue exclusions) to the
founding group's six cached descriptions reproduced the founding
claim tables exactly:

```
taxonomy-verbatim proof: founding group 6 of 6 forks, 34 of 34
claims reproduced exactly (deep-equal vs git HEAD)
```

The proof is also pinned inside the suite
(`tests/test_specs.py::test_taxonomy_verbatim_reproduction_proof`).

## The tagging pass

```
F1403283529 exclusion removed would-be claims: []
F1403283529 Project Hosts Inc. / GSS One - Azure: 4 claims
   - multi_tenancy
   - monitoring_observability
   - backup_disaster_recovery
   - managed_operations
```

Raw pass: **4 hits, 0 removed.** The fork's description splits
into 79 units under the founding split.

**Third-party catalogue exclusion (checked both ways).** The
description's final section is a partial list of third-party
applications hosted ON the platform — 52 units after the lead-in
unit ("Following is a partial list of applications for which
Project Hosts is providing these services over and above the GSS
One-Azure platform:"), ~50 entries (1E, Archive360, AvePoint,
Microsoft, Veritas, WordPress, …). Those applications' functions
belong to other categories, so the units after the lead-in were
excluded before matching, the house analogue of the founding
group's SAP catalogue exclusion. The pass was run with and
without the exclusion: **the exclusion removed nothing** (no
catalogue unit fires any family — e.g. the list's "Disaster
Recovery for Identities" is title-case where the family's
patterns are "disaster recovery" / "Disaster recovery", and no
list unit carries any other family phrase). The equality is
pinned by test so the exclusion cannot quietly change the table
later. The fork's own three SaaS components (GSS One
Portal/Admin Page, GSS One Console, GSS One Ticketing System)
are first-party composition and stayed matchable, exactly as the
founding group's IBM bundle components stayed matchable.

**Scope-exclusion adjudication (1 item, kept).** The
`monitoring_observability` evidence sentence ("Namely, Project
Hosts deploys, secures, manages, and provides continuous
monitoring for applications that are compatible with the GSS1-AZ
architecture, …") sits in the paragraph the fork introduces as
services "over and above the PaaS offering described in the
GSS1-AZ FedRAMP package". Adjudicated **kept**: the sentence
itself is a plain first-party functional assertion carrying no
exclusion or disclaimer phrasing; the paragraph framing concerns
the authorization package's scope, and claims in this repo
measure the fork's described functions. No other raw hit's
evidence sentence carries scope-exclusion phrasing. The
adjudication is recorded here so the decision is visible, not
buried.

`certified_services` is empty for this record (asserted at
extraction) and was never matched.

## Near-misses (itemized, not repaired)

- **hosting_platform — the category's centre fires nothing.**
  "multi-tenant PaaS cloud computing environment" is not the
  family's "cloud environment" phrase ("cloud computing
  environment" ≠ "cloud environment"); "hybrid offering" and
  "Government Only General Support System (GSS) deployed on
  Azure Government" carry no family pattern.
- **security_services — a case artifact.** "intrusion
  prevention" occurs twice, both lowercase; the family's
  patterns are the founding forks' title-case phrases
  ("Intrusion Prevention"), so nothing fires. "malware
  prevention" is not a pattern; "Network Security Group firewall
  access controls" is not "Web Application Firewall". The
  taxonomy was not re-tuned for case.
- **identity_access.** "access control, authentication" are
  bare nouns in the composed-of list; the Portal's user
  administration ("create and manage non privileged users …
  including revoking access", "account creation and JIT access")
  names no family phrase ("Single Sign-On", "IAM policies",
  "Directory services" all absent).
- **infrastructure_providers.** "deployed on Azure Government"
  and "FedRAMP-authorized Azure PaaS services" name the host;
  none of the family's provider phrases occurs.
- **managed_operations rests on one sentence.** "patching" in
  the composed-of list is not "level patching"; "configuration
  management" is not "Configuration management for OS". The
  claim fires only on "monthly vulnerability scanning include
  ACAS scans, dynamic web app scans and container image scans"
  (the family's lowercase "vulnerability scanning" pattern).
- **compliance_authorization_support.** The A&A substance is
  the densest in the category outside the founding group (ATO,
  3PAO annual assessments, POA&M, SSP, "speed up ATO times"),
  but the exact phrases "Assessment & Authorization" /
  "Assessment and Authorization" occur 0 times (token-pinned).
- **dedicated_environments.** "customer-dedicated virtual
  servers", "customer-dedicated subnets", "deploying dedicated
  applications just for their agency" — substance present; the
  family's phrases ("dedicated application stacks", "cloud
  hosting models") absent.
- **us_operations_residency.** "Government Only" + Azure
  Government is residency substance; the family's phrases are
  the founding forks' own words (U.S. soil, U.S. citizens,
  U.S.-based environment) and none occurs.
- **account_provisioning.** "account creation" (Portal/Admin
  prose) is not "account provisioning and invoicing"; the
  "FinOps" token occurs 0 times.
- **encryption.** The token "encrypt" occurs 0 times in the
  description.

## Census citations

The census recorded **0 citations** for this fork
(`remainder.json`: `citations: []`, `no_signal: true`, reason
"prose_only") — no function sentence could be cited from the
cached description, which is why the fork sat in the
no-signal-set until the live-doc research pass classified it.
0 of 0 verify; 0 serve as claim evidence. Verification is not a
claim, in either direction.

## Documented-control tracing (for UNION-SPEC)

All traced sentences were verified as verbatim substrings of
the sheet's description at build time and are pinned by
`tests/test_specs.py::test_documented_control_sentences_present`:

- The composed-of sentence: "GSS1-AZ is composed of systems and
  services that manage access control, authentication, auditing,
  monitoring, scanning, patching, configuration management,
  malware prevention, intrusion prevention, incident response,
  backup, and disaster recovery for each application leveraging
  the GSS1-AZ."
- "Project Hosts security compliance team also performs monthly
  vulnerability scanning include ACAS scans, dynamic web app
  scans and container image scans and documents and tracks these
  findings in accordance with continuous monitoring
  requirements."
- "…as well as all SOC review and analysis of audit logs and
  responding/investigating alerts for suspicious activity."
- "…incident response reporting, analysis, eradication, and
  recovery…"
- "For CSP customers, Project Hosts also creates their SaaS-level
  FedRAMP package, helps them throughout the agency authorization
  process, and manages their 3PAO annual assessments."
- "…link controls to artifacts and evidence to speed up ATO
  times…" (GSS One Console).
- Bounds checked: "communicate with PH staff through a secure
  channel" (Ticketing System) names no mechanism — "encrypt"
  occurs 0 times, no TLS/FIPS token occurs — so SC is not
  documented; the Console's "allows them to manage training" is
  a customer-facing product function, so AT is not documented.

## Core carry accounting

`src/cloudinfra/` was copied from the founding group and verified
byte-identical per module (SHA-256; table in README.md): **7 of
7 modules byte-identical.** The only tier text in the carried
code is the founding label line in two docstrings
(`__init__.py` line 3 and `store.py` line 3, each naming the
"Cloud Infrastructure & Hosting L2 union spec") — retained so
the accounting is exact, and re-anchored in this group's docs:
at tier null the hooks are baseline-neutral substrate, claimed
against no baseline.

## Negative control (recorded drill)

The founding signature drill was re-run in this tree: the body
of `CloudInfraStore._check_deployment_slot` in
`src/cloudinfra/store.py` was replaced with `return None` and
the full suite re-run — **exactly 4 failures**, the founding
drill's identical set (the slot functional test, the canonical
expectation test, the HTTP end-to-end flow, and the
byte-identical pin), plus the one expected error
(`test_mutation_run_recorded`, the record not existing during
the drill). The store was restored from
`tests/store.py.premutation` and verified byte-identical
(SHA-256 `95d39967…`, matching `tests/store.py.sha256`), and
the suite re-verified at 119/119 green. Full record:
`tests/mutation-run.txt`; summary in `tests/README.md`.
