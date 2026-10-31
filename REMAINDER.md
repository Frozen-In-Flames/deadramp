# Operation DeadRamp — Phase 2 Remainder Census

The worklist for everything Phase 2 has not built yet: every fork not covered by the 36 sibling groups and 19 singletons already shipped. Classification pass only — nothing here is built, and no category in this document is a claim: each proposed category is assigned from the fork's own marketplace description, with the evidencing sentence(s) quoted verbatim in `remainder.json`, or the fork is recorded as carrying no functional signal.

## Reconciliation

| Count | Forks |
|---|---:|
| Marketplace total (forks.json) | 781 |
| Covered by the 55 shipped groups (fork ID present in a shipped `specs/specs.json`) | 498 |
| **Uncovered — this census** | **283** |
| Classified to a proposed category | 260 |
| No functional signal in the cached description | 23 |
| Descriptions missing from the cache entirely | 0 |

Uncovered composition: 142 tiered forks with no source category, 102 untiered forks with a source category, 39 untiered and uncategorized. Buckets: **107** category additions to shipped groups, **6** forks in new sibling groups, **10** new singletons, **137** forks in untiered sets, **23** no-signal.

## Method

- Coverage is mechanical: a fork is covered iff its FedRAMP ID (from its `forks.json` source URL) appears in some shipped group's spec sheet. 498 covered / 283 uncovered, zero duplicates.
- Each uncovered fork's description was read from the cached GSA dataset (`raw/data_dump.json`, `service_desc`, joined by FedRAMP ID). Every one of the 283 has a cached description; none had to be fetched.
- A proposed category names the fork's **primary function in its own description sentences**, quoted verbatim as citations in `remainder.json`. Precedents from the shipped builds bind throughout: a filing label (`business_categories`) is not a claim; catalogue prose about other products or hosted third-party applications does not categorize the fork; sentences placing a capability out of scope do not count; assurance/hosting prose alone is no signal.
- Coordinator verification: all 283 fork IDs present exactly once; every citation re-checked programmatically as a verbatim substring of its description after whitespace normalization — **0 failures**; every proposed category is in the 36-category marketplace vocabulary or is one of the 4 new-category proposals below.
- Tier is never invented: untiered forks (impact Unknown in the source) stay tier-null and build to documented control claims, per PIPELINE.md.

## Proposed build order

Tiered units first, largest first (the Phase 2 pattern); then untiered sets, largest first; the no-signal set last, because those forks need live documentation checks before any category can be assigned honestly.

1. **Addition** — Operations Management | L2 (20 forks) extends `groups/operations-management-l2/`
2. **Addition** — Cybersecurity & Risk Management | L2 (18 forks) extends `groups/cybersecurity-l2/`
3. **Addition** — System Administration | L2 (8 forks) extends `groups/system-administration-l2/`
4. **Addition** — Legal & Policy | L2 (6 forks) extends `groups/legal-policy-l2/`
5. **Addition** — Data Management | L2 (5 forks) extends `groups/data-management-l2/`
6. **Addition** — Governance, Risk, and Compliance (GRC) | L2 (5 forks) extends `groups/grc-l2/`
7. **Addition** — Research | L2 (5 forks) extends `groups/research-l2/`
8. **Addition** — Development Tools | L2 (4 forks) extends `groups/development-tools-l2/`
9. **Addition** — Finance | L2 (4 forks) extends `groups/finance-l2/`
10. **Addition** — Collaboration | L2 (3 forks) extends `groups/collaboration-l2/`
11. **Addition** — Health & Wellness | L2 (3 forks) extends `groups/health-wellness-l2/`
12. **Addition** — Human Resources | L2 (3 forks) extends `groups/human-resources-l2/`
13. **Addition** — Operations Management | L1 (3 forks) extends `groups/operations-management-l1/`
14. **Addition** — Cybersecurity & Risk Management | L3-adjacent (2 forks) extends `groups/cybersecurity-l3/`
15. **New sibling group** — Contract Management | L2 (2 forks)
16. **New sibling group** — Learning Management | L1 (2 forks)
17. **New sibling group** — Talent Management | L2 (2 forks)
18. **Addition** — Analytics | L1 (1 forks) extends `groups/analytics-l1/`
19. **Addition** — Analytics | L2 (1 forks) extends `groups/analytics-l2/`
20. **Addition** — Artificial Intelligence (AI) | L2 (1 forks) extends `groups/ai-l2/`
21. **Addition** — Collaboration | L3-adjacent (1 forks) extends `groups/collaboration-l3/`
22. **Addition** — Communication | L2 (1 forks) extends `groups/communication-l2/`
23. **Addition** — Communication | L3-adjacent (1 forks) extends `groups/communication-l3/`
24. **Addition** — Content Management System (CMS) | L2 (1 forks) extends `groups/cms-l2/`
25. **Addition** — Customer Service | L1 (1 forks) extends `groups/customer-service-l1/`
26. **Addition** — Customer Service | L3-adjacent (1 forks) extends `groups/customer-service-l3/`
27. **Addition** — Cybersecurity & Risk Management | L1 (1 forks) extends `groups/cybersecurity-l1/`
28. **Addition** — Data Management | L1 (1 forks) extends `groups/data-management-l1/`
29. **Addition** — Education & Training | L2 (1 forks) extends `groups/education-training-l2/`
30. **Addition** — Finance | L3-adjacent (1 forks) extends `groups/finance-l3/`
31. **Addition** — Governance, Risk, and Compliance (GRC) | L3-adjacent (1 forks) extends `groups/grc-l3/`
32. **Addition** — Law Enforcement | L3-adjacent (1 forks) extends `groups/law-enforcement-l3/`
33. **Addition** — Learning Management | L2 (1 forks) extends `groups/learning-management-l2/`
34. **Addition** — Mobile Device Management (MDM) | L2 (1 forks) extends `groups/mobile-device-management-l2/`
35. **Addition** — Travel Management | L2 (1 forks) extends `groups/travel-management-l2/`
36. **New singleton** — Customer Relations Management (CRM) | L1 (1 fork)
37. **New singleton** — Development Tools | L3-adjacent (1 fork)
38. **New singleton** — Energy Management | L1 (1 fork)
39. **New singleton** — Event Management | L1 (1 fork)
40. **New singleton** — Fleet Management | L2 (1 fork)
41. **New singleton** — Health & Wellness | L1 (1 fork)
42. **New singleton** — Human Resources | L1 (1 fork)
43. **New singleton** — Research | L1 (1 fork)
44. **New singleton** — Storage | L2 (1 fork)
45. **New singleton** — Storage | L3-adjacent (1 fork)
46. **Untiered set** — Cybersecurity & Risk Management (27 forks, tier null)
47. **Untiered set** — Operations Management (20 forks, tier null)
48. **Untiered set** — Governance, Risk, and Compliance (GRC) (15 forks, tier null)
49. **Untiered set** — Artificial Intelligence (AI) (9 forks, tier null)
50. **Untiered set** — Data Management (8 forks, tier null)
51. **Untiered set** — Development Tools (7 forks, tier null)
52. **Untiered set** — Construction (6 forks, tier null)
53. **Untiered set** — Education & Training (6 forks, tier null)
54. **Untiered set** — Research (4 forks, tier null)
55. **Untiered set** — System Administration (4 forks, tier null)
56. **Untiered set** — Health & Wellness (3 forks, tier null)
57. **Untiered set** — Legal & Policy (3 forks, tier null)
58. **Untiered set** — Communication (2 forks, tier null)
59. **Untiered set** — Content Management System (CMS) (2 forks, tier null)
60. **Untiered set** — Fleet Management (2 forks, tier null)
61. **Untiered set** — Human Resources (2 forks, tier null)
62. **Untiered set** — Law Enforcement (2 forks, tier null)
63. **Untiered set** — Marketing & Sales (2 forks, tier null)
64. **Untiered set** — Network Management (2 forks, tier null)
65. **Untiered set** — Talent Development (2 forks, tier null)
66. **Untiered set** — Talent Management (2 forks, tier null)
67. **Untiered set** — Accounting (1 forks, tier null)
68. **Untiered set** — Customer Relations Management (CRM) (1 forks, tier null)
69. **Untiered set** — Finance (1 forks, tier null)
70. **Untiered set** — Learning Management (1 forks, tier null)
71. **Untiered set** — Manufacturing (1 forks, tier null)
72. **Untiered set** — Media (1 forks, tier null)
73. **Untiered set** — Travel Management (1 forks, tier null)
74. **No-signal set** — 23 forks; live documentation check required before classification (flagged, not fetched).

## Category additions (extend a shipped group's union spec)

### Operations Management | L2 → `groups/operations-management-l2/` (20)

- `F1404043549` — Accenture Federal Services / Accenture Federal Cloud ERP
- `AGENCYHUDSAAS` — AINS dba OPEXUS / AINS dba OPEXUS - eCase
- `FR1918442180` — Bizagi Corp. / Bizagi Cloud for US Government
- `FR1923039219` — Canon U.S.A., Inc. / Canon Office Cloud – Managed Print Services
- `FR2324454026` — FM:Systems / OpenBlue Workplace
- `FR1728053006` — IBM / IBM Automation Services for Government
- `FR1816364586` — Ivanti / Ivanti Neurons for ITSM (Formerly Service Manager)
- `FR1927682057` — M.C. Dean, Inc. / InfraLink
- `FR2129953050` — Manhattan Associates, Inc. / Manhattan Government Cloud
- `F1506256801` — MSM Group, Inc. / iSite Contract Management Portal
- `FR2102577114` — Pitney Bowes / SendPro 360
- `F1608097919` — PTC / PTC Cloud Services
- `FR1733061545` — R&K Solutions, Inc / GoRPM
- `FR1730866868` — Smartsheet / Smartsheet Gov
- `FR2000945223` — Software AG Government Solutions / ARIS Government Cloud
- `FR1722532017` — stackArmor / Clarity
- `FR2130949241` — StackArmor / Rally
- `FR2108649352` — Tyler Federal, LLC / Tyler Federal Product Suite
- `FR2132958724` — UiPath / Automation Cloud Public Sector
- `FR1730334049` — Xerox Corporation / Xerox Managed Print Services for US Government

### Cybersecurity & Risk Management | L2 → `groups/cybersecurity-l2/` (18)

- `FR2104942200` — Acuant, Inc. / Connect, Ozone, & Facial Recognition System (COFRS)
- `FR2031936863` — Armis Federal LLC / Armis FedRAMP Edition (AFE)
- `FR1814168113` — Authentic8, Inc. / Silo
- `F1605107897` — Cisco Systems Inc. / Cisco Cloudlock for Government
- `FR1823149273` — Duo Security (a Cisco Company) / Duo Federal
- `FR1829538820` — General Services Administration / Login.gov
- `FR1718334757` — ID.me / ID.me Identity Gateway
- `F1511167634` — Kiteworks USA, LLC / Kiteworks Federal Cloud
- `F1512167750` — Okta / Okta IDaaS Regulated Cloud
- `F1301101857` — OpenText / OpenText™ Core Application Security (Fortify On Demand)
- `FR2301844932` — Orca Security / Orca Cloud Security Platform
- `FR1913470600` — Palo Alto Networks, Inc. / Palo Alto Networks Government Cloud Services
- `FR1720461312` — Proofpoint, Inc. / Proofpoint Email and Information Protection Service
- `FR1819168894` — Proofpoint, Inc. / Proofpoint Targeted Attack Protection
- `F1508207205` — Qualys / Qualys Cloud Platform
- `FR1821062403` — Saviynt, Inc. / Saviynt Enterprise Identity Cloud (EIC)
- `FR2110342613` — Tanium / Tanium Cloud for US Government (TC-USG)
- `FR1731347234` — Zimperium / Zimperium Mobile Endpoint Cyber Security

### System Administration | L2 → `groups/system-administration-l2/` (8)

- `FR1819254092` — Citrix / Citrix for Government
- `FR1833967442` — Contegix / Valiantys Federal (Formerly Contegix)
- `FR2000951694` — DLH Corporation / DLH Infinibyte Cloud
- `FR2016131254` — Dynatrace / Dynatrace Platform
- `F1311252651` — ESRI / Esri Managed Cloud Services Advanced Plus
- `FR2215946050` — OpenText / ITMX Platform featuring Service & Asset Management, Universal Discovery, CMDB and Project & Portfolio Management
- `F1209041518` — Oracle / Federal Managed Cloud Services
- `FR2624215150` — TeamViewer / TeamViewer DEX Platform

### Legal & Policy | L2 → `groups/legal-policy-l2/` (6)

- `F1506246782` — Complete Discovery Source / Complete Discovery Source Federal Cloud (CDS-F)
- `F1210161615` — Deloitte / Evidence Management System (EMS)
- `F1609267945` — DocuSign / Docusign - IAM eSignature
- `F1605027893` — DocuSign / DocuSign CLM
- `FR1800263217` — Innovative Discovery, LLC / Innovative Driven Government Cloud (IDGC)
- `FR2004753002` — Relativity ODA LLC / RelativityOne Government

### Data Management | L2 → `groups/data-management-l2/` (5)

- `FR1706403967` — Collibra / Collibra Platform for Government (CPG)
- `FR1814557199` — DNAnexus, Inc. / DNAnexus Platform
- `FR2029331613` — Informatica LLC / Informatica Intelligent Cloud Services (IICS)
- `FR1901136437` — Synergetics Incorporated / Open Federal Logistics Information System (OpenFLIS)
- `FR2025456731` — Vaultara, LLC / Vaultara Flare Services

### Governance, Risk, and Compliance (GRC) | L2 → `groups/grc-l2/` (5)

- `FR2620235600` — Anecdotes / Anecdotes
- `FR2621445678` — Halo / Halo
- `FR2607537684` — Kovr.ai / Kovr Nova
- `FR2004146362` — MediaLab, Inc. / MediaLab Federal
- `FR1726564822` — Workiva / Workiva Platform

### Research | L2 → `groups/research-l2/` (5)

- `FR2000939520` — Broad Institute, Inc. / Terra
- `FR2104636677` — Ipsos America, Inc. / Ipsos Research
- `FR2204842850` — Rosalind, Inc. / ROSALIND
- `FR2033152148` — Seven Bridges Genomics, Inc / Seven Bridges Platform
- `FR1924344515` — Wellspring Worldwide, Inc. / Wellspring Tech Transfer and IP Management Suite (WTIMS)

### Development Tools | L2 → `groups/development-tools-l2/` (4)

- `F1607067912` — 18F - 18F Cloud.gov / CG-TTS - Cloud.Gov
- `FR2200507410` — Copado / Copado GovCloud
- `FR1912051231` — TechTrend, Inc. / Federal GovCloud (FGC) DevSecOps
- `FR2125561001` — Unqork, Inc. / Unqork for Government

### Finance | L2 → `groups/finance-l2/` (4)

- `F1603157879` — Apptio an IBM company / Apptio for Technology Business Management and Cloud Financial Management (TBM)
- `FR2022243058` — CGI Federal / Momentum Enterprise Suite
- `F1308202329` — Coupa Software Inc / Coupa Spend Management for Federal
- `FR1821933307` — Innovest Systems, LLC / Trust & Wealth Management Solutions

### Collaboration | L2 → `groups/collaboration-l2/` (3)

- `F1511207635` — Cisco Systems Inc. / Webex for Government
- `F1408115175` — Huddle US / Huddle Enterprise Cloud Content Collaboration and File Sharing Portal for Government
- `F1512017638` — IdeaScale / IdeaScale Gov

### Health & Wellness | L2 → `groups/health-wellness-l2/` (3)

- `FR2035860874` — Global Telehealth Services, inc. / GTS VirtualHealth Platform (GTS-VP)
- `FR2135915901` — Solventum / Solventum RevCycle Health Services Platform
- `FR2002367706` — Somnoware Healthcare Systems / Somnoware

### Human Resources | L2 → `groups/human-resources-l2/` (3)

- `FR1834348080` — GDC Integration, Inc. / General Support System (GSS)
- `FR2002757173` — Government Retirement & Benefits, Inc. / GRB Platform
- `FR1818240234` — Perceptyx / Perceptyx Insights Platform

### Operations Management | L1 → `groups/operations-management-l1/` (3)

- `FR2017462201` — Booz Allen Hamilton / Supply Chain Master Catalog (SCMC) Government Cloud Solution
- `FR1828574469` — FM:Systems / OpenBlue Employee
- `FR2100740435` — Tango / Tango

### Cybersecurity & Risk Management | L3-adjacent → `groups/cybersecurity-l3/` (2)

- `FR2304757473A` — Cisco Systems Inc. / Cisco Security Cloud for Government
- `FR1714261912` — XTec, Incorporated / AuthentX Cloud

### Analytics | L1 → `groups/analytics-l1/` (1)

- `FR2017459185` — HP Inc. / Workforce Experience Platform Collaboration

### Analytics | L2 → `groups/analytics-l2/` (1)

- `F1508127183` — NetComm / Beacon

### Artificial Intelligence (AI) | L2 → `groups/ai-l2/` (1)

- `FR2214346691` — Secunetics, Inc. / Gobo Framework (Gobo)

### Collaboration | L3-adjacent → `groups/collaboration-l3/` (1)

- `MSO365MTA` — Microsoft / Microsoft 365 Government Community Cloud & Supporting Services

### Communication | L2 → `groups/communication-l2/` (1)

- `F1311252652` — Granicus / GovDelivery Communications Cloud

### Communication | L3-adjacent → `groups/communication-l3/` (1)

- `FR2230252267` — Slack Technologies / GovSlack

### Content Management System (CMS) | L2 → `groups/cms-l2/` (1)

- `FR2031155471` — Iron Mountain / Iron Mountain InSight

### Customer Service | L1 → `groups/customer-service-l1/` (1)

- `FR1821856903` — Zendesk / Zendesk Customer Support and Help Desk Platform

### Customer Service | L3-adjacent → `groups/customer-service-l3/` (1)

- `FR1711262842` — Medallia, Inc. / Medallia GovCloud

### Cybersecurity & Risk Management | L1 → `groups/cybersecurity-l1/` (1)

- `FR1919750997` — HackerOne / HackerOne Continuous Security Testing Platform

### Data Management | L1 → `groups/data-management-l1/` (1)

- `FR2100845343` — DevResults / DevResults

### Education & Training | L2 → `groups/education-training-l2/` (1)

- `FR2135637226` — Pearson VUE / Pearson Federal Cloud System

### Finance | L3-adjacent → `groups/finance-l3/` (1)

- `FR1721059275A` — OneStream Software / OneStream Cloud - High

### Governance, Risk, and Compliance (GRC) | L3-adjacent → `groups/grc-l3/` (1)

- `FR2122140784A` — Covergent Solutions Inc dba Exiger Government Solutions (EGS) / Exiger Federal Cloud (EFC) - High

### Law Enforcement | L3-adjacent → `groups/law-enforcement-l3/` (1)

- `F1602057825A` — TRAPWIRE / TRAPWIRE Threat Detection and Analysis System

### Learning Management | L2 → `groups/learning-management-l2/` (1)

- `FR2118043605` — Skillsoft / Percipio

### Mobile Device Management (MDM) | L2 → `groups/mobile-device-management-l2/` (1)

- `F1507116930` — Ivanti / Ivanti Neurons for MDM (Formerly MobileIron)

### Travel Management | L2 → `groups/travel-management-l2/` (1)

- `F1610037949` — mLINQS / mLINQS Hosting Service

## New sibling groups

### Contract Management | L2 (2)

- `F1506046707` — Unison / Contracting SaaS
- `F1510017461` — Unison / FedConnect

### Learning Management | L1 (2)

- `FR2113157410` — Public Health Foundation / TRAIN Learning Network
- `FR2135043135` — SRR International,Inc. / CloudLCMS

### Talent Management | L2 (2)

- `FR1831429369` — HireVue / Recruitment Assessments and Video Interviewing
- `FR2113557839` — Yello Dba Recsolu Inc / Yello Government Recruiting Solution

## New singletons

- **Customer Relations Management (CRM) | L1** — `FR2035740126` Sprinklr, Inc. / Sprinklr CXM for Government (CXM)
- **Development Tools | L3-adjacent** — `FR2102031769` Red Hat / Red Hat OpenShift Service on AWS (ROSA)
- **Energy Management | L1** — `FR2014363920` Enel X North America / Exchange Platform
- **Event Management | L1** — `FR2304546222` My Business Matches / Vendor Event & Business Matchmaking Platform
- **Fleet Management | L2** — `FR1918150046` Geotab / Geotab Telematics Platform Government (GTP Gov)
- **Health & Wellness | L1** — `FR2212912561` Itamar Medical / Itamar Dispatcher Cloud (IDC)
- **Human Resources | L1** — `FR1924942935` Qgenda, LLC / QGenda
- **Research | L1** — `FR2207359708` Evidence Prime / Laser AI
- **Storage | L2** — `F1304222071` Proofpoint, Inc. / Proofpoint Email Archive
- **Storage | L3-adjacent** — `FR2115384377` Commvault Systems, Inc. / Commvault Cloud for Government

## Untiered sets (proposed category, tier null — build to documented control claims)

### Cybersecurity & Risk Management (27)

- `F1602167854` — BlackBerry / BlackBerry CylanceProtect & CylanceOptics
- `FR2232465502` — Broadcom / Symantec Gov Cloud Security (GCS)
- `FR2232465502A` — Broadcom / Symantec Gov Cloud Security (GCS) - High
- `FR2304757473` — Cisco Systems Inc. / Cisco Security Cloud for Government
- `FR2000863987` — Cloudflare / Cloudflare for Government
- `FR2633734912` — ConnectSecure LLC / ConnectSecure Vulnerability and Compliance Manager
- `FR2134254227` — Devo / Devo.Gov-US
- `FR2635050845` — DigiCert, Inc. / DigiCert for Government
- `FR2630354482` — Dispel LLC / Dispel Zero Trust Engine
- `FR2628647233` — Dispel, LLC / Dispel Zero Trust Engine (DZTE) For Government
- `FR2632054495` — JupiterOne, Inc. / JupiterOne GovCloud
- `FR2116544598` — Keeper Security / Keeper Security Government Cloud Password Manager and Privileged Access Manager
- `FR2527245282` — Mimic Networks, Inc. / Mimic Enterprise Ransomware Defense Platform (ERDP)
- `FR2630354494` — NextgenID, Inc. / NextgenID User Interface as a Service (UIaaS)
- `FR2701857797` — Optimal Labs / 9line
- `FR2631054533` — Portal26, Inc. / AI Security, Governance, & Telemetry Platform
- `FR2634436150` — Remedio Technologies Inc / Remedio
- `FR2001938710` — SailPoint Technologies, Inc. (Pre SCR review) / SailPoint Identity Security Cloud
- `FR2700857464` — Securin, Inc. / Securin Preemptive Exposure Management Platform
- `FR1919071020` — SentinelOne / SentinelOne Singularity Platform Moderate
- `FR2635050855` — SuperGov, Inc / SuperFile
- `FR2634659091` — Tactical Takedown LLC / TNT Business Resilience Platform
- `FR2632731472` — Transmittr, Inc. / Casco for Government
- `FR2516140413` — TransUnion LLC / TransUnion TruValidate
- `FR1935245314` — Trellix / Trellix GovCloud Security Platform
- `FR2633058240` — Ultra Security, Inc. / Ultra Agentic Security Platform
- `FR2308034636` — Wiz, Inc. / Wiz Moderate for U.S. Government

### Operations Management (20)

- `FR2701457595` — AtomAI Solutions Inc. / AtomAI Platform
- `FR2631054482` — Concourse Tech Inc. / Concourse Platform
- `FR2701256060` — Fulcrum / Fulcrum
- `FR2630354487` — Globality Inc / Globality Platform
- `FR2628943629` — International Vending Management, Inc. / SmartHub
- `FR2630354492` — MaintainX / MaintainX for Government
- `FR2631054487` — Nastro Technologies, Inc. / BitRip
- `FR2634659083` — NavigatorCRE / NavigatorCRE
- `FR2631258127` — NEXGEN Asset Management / NEXGEN Asset Management
- `FR2628647241` — Partos Inc. / Partos for Government
- `FR2628650874` — Pincus Technologies Inc / Tarly Cowork
- `FR2632436493` — Rohirrim, Inc. / Unified Acquisition Platform
- `FR2428039108` — Siemens AG / DepotFinity
- `FR2634659087` — Signifi Solutions Inc. / SignifiVISION
- `FR2633841585` — Silkline, Inc. / Silkline
- `FR2310051488` — Standard Technology Inc. / Contract Management Planning and Surveillance System
- `FR2630447318` — Stoke Space Technologies, Inc. / Boltline
- `FR2701247935` — Tansi LLC / Tansi
- `FR2316433331` — USU Solutions Inc. / USU IT Asset Management
- `FR2628943630` — Xfinion Inc. / Continuously Aware Realtime Tracking Network (CARTN)

### Governance, Risk, and Compliance (GRC) (15)

- `FR2701557058` — 38North Security, LLC / Northwatch
- `FR2628647239` — Advent Business Company Inc. / Enablement®
- `FR2635930439` — Advent Business Company Inc. / Enablement®
- `FR2628943633` — Boundera / Boundera SaaS
- `FR2631258122` — Cahill Swift, LLC / Cahill Swift Compliance Management Platform
- `FR2631258125` — Certivo, Inc. / Certivo Compliance Platform
- `FR2630354485` — ComplianceAid INC. / ComplianceAide Government Cloud
- `FR2633957422` — MediaLab Solutions LLC / Vastian (MediaLab by Vastian)
- `FR2631054539` — Mycroft Technologies Inc / Mycroft GRC Platform
- `FR2632558735` — Ocasio Convergence Holdings LLC / Axiom Convergence Engine (ACE)
- `FR2700754082` — PlatformOne Group Inc / ComplianceONE
- `FR2700137045` — RegScale, Inc. / RegScale Trust Center 20x (Class C)
- `FR2629068830` — SunStone Secure, LLC / SunStone Artemis Platform
- `FR2633053629` — TGuardAI Inc. / TrustGuard AI Compliance Platform
- `FR2630354484` — VisualVault LLC / VisualVault Cloud

### Artificial Intelligence (AI) (9)

- `FR2633053633` — Anthropic / Claude
- `FR2633153276` — Anyreach, Inc. / Anyreach App Software Application
- `FR2632558748` — Baseten Labs, Inc. / Baseten Inference Platform
- `FR2632054530` — Beam Up Ltd / Beam
- `FR2628647242` — Bland AI / Bland
- `FR2700137035` — Caldera AI Inc. / Mesa
- `FR2628647238` — Eleven Labs Inc. / ElevenLabs Platform
- `FR2634659079` — ThinkTrends LLC / ThinkTrends AI Platform
- `FR2632054534` — Thread AI, Inc. / Lemma (GovCloud)

### Data Management (8)

- `FR2700429895` — Ardoq Inc / Ardoq
- `FR2630354495` — Files.com / Files.com
- `FR2629068833` — Immuta / Immuta Federal
- `FR2702058502` — Ocient Inc. / OcientAIQ
- `FR2629068832` — Open Access Technology International, Inc. / OATI Marketplace
- `FR2634450946` — Pinecone Systems, Inc. / Pinecone
- `FR2631654537` — Wisedocs USA Inc. / Wisedocs for Government
- `FR2504771625` — ZL Technologies, Inc. / ZL Unified Archive (ZL UA)

### Development Tools (7)

- `FR2701557054` — Aequitas Cyber Labs / KineticCode
- `FR2631054484` — Anysphere, Inc. / Cursor
- `FR2701557044` — Business Integra Technology Solutions, Inc. / Moderniza
- `FR2631258132` — Harness, Inc. / Harness for Government
- `FR2701457600` — IndirectTek LLC / Elixium
- `FR2700555844` — Linear Orbit, Inc. / Linear
- `FR2701457579` — Replit, Inc. / Replit for Government

### Construction (6)

- `FR2701557038` — Facility Grid, LLC / Facility Grid
- `FR2633734906` — Four BT, LLC / Four BT Benchmark Construction Estimator
- `FR2520254824` — InEight, Inc. / InEight Document US Government
- `FR2631258135` — Specset / Specset Cloud Platform
- `FR2631747321` — Specset / Specset Cloud Platform
- `FR2701247929` — Trimble Inc. / Trimble for Government

### Education & Training (6)

- `FR2700137041` — Dossier / Dossier for Government
- `FR1912662229` — KnowBe4, Inc. / KnowBe4 Security Awareness Training
- `FR2635447609` — MyEvaluations.com Inc. / MyEvaluations
- `FR1916744879` — Proofpoint, Inc. / Proofpoint Security Awareness Training
- `FR2633734917` — Simuhealth Technologies Inc. / Simuhealth
- `FR2635050850` — Toonimo Inc. / Toonimo Digital Adoption Platform

### Research (4)

- `FR2632054521` — Leadership Connect, Inc. / Leadership Connect
- `FR2632054491` — OpenClinica LLC / OpenClinica4 (OC4)
- `FR2701557049` — Sixtyfourai / Sixtyfour Identity Intelligence Platform
- `FR2631747315` — Sustainment Technologies Inc. / Sustainment Digital Manufacturing Hub

### System Administration (4)

- `FR2700555848` — Dynatrace / Dynatrace Platform for FedRAMP Class D (High)
- `FR2630354491` — Freshworks / Freshworks for Government
- `FR2217348295` — NetApp / Cloud Insights
- `FR2701457585` — PDQ / PDQ for Government

### Health & Wellness (3)

- `FR2634047811` — 86Borders LLC / 86Borders ConnectAllCare
- `FR2633734921` — Elvo / Elvo
- `FR1825232355` — WellHive Holdings, LLC / WellHive

### Legal & Policy (3)

- `FR2009476860` — Casepoint LLC / Casepoint Government
- `FR2701247925` — Litmas, Inc. / Litmas AI
- `FR2633734932` — Skyward IT Solutions / Alira

### Communication (2)

- `F1302271924` — BlackBerry / BlackBerry Cloud - AtHoc Services for Government
- `F1604017885` — Cisco Systems Inc. / Cisco Unified Communications Manager Cloud for Government (Cisco UCM Cloud for Government)

### Content Management System (CMS) (2)

- `FR2701857792` — Liferay, Inc. / Liferay SaaS
- `FR2001462460` — Nintex / Nintex Drawloop DocGen

### Fleet Management (2)

- `FR2633153272` — Samsara Inc. / Samsara Connected Operations Cloud
- `FR2700857493` — Samsara Inc. / Samsara Connected Operations Cloud

### Human Resources (2)

- `FR2633957417` — Dayforce / Dayforce HCM, Public Sector
- `F1606087903` — Deltek - Replicon / Replicon Cloud Platform (Enterprise Time Tracking Platform)

### Law Enforcement (2)

- `FR2628943632` — Pryme Infil, Inc. / Pryme Infil
- `FR2631258113` — TRM Labs, Inc. / TRM Labs on GovCloud

### Marketing & Sales (2)

- `FR2700857472` — CLEATUS, Inc. / CLEATUS
- `FR2700857469` — Zeta Global Corp. / Zeta Marketing Platform for Government

### Network Management (2)

- `FR2632755834` — Armada / Armada Platform
- `FR2631154499` — IronWiFi, LLC / IronWiFi Cloud RADIUS and Wi-Fi Authentication Platform

### Talent Development (2)

- `FR2318956176` — BetterUp, Inc. / BetterUp for Government
- `FR2635930421` — SOFware LLC / FORGE

### Talent Management (2)

- `FR2635930425` — CodeSignal, Inc. / CodeSignal
- `FR2631747327` — Geographic Solutions Inc. / VOS Sapphire

### Accounting (1)

- `FR2633734927` — Meterbox Inc. / Meterbox

### Customer Relations Management (CRM) (1)

- `FR2635050861` — VirtualDojo, Inc. / VirtualDojo AI CRM

### Finance (1)

- `FR2633058235` — Emburse / Emburse Enterprise

### Learning Management (1)

- `FR2634357692` — Progressive Expert Consulting / Collaborative Learning Environment

### Manufacturing (1)

- `FR2632054516` — Neuramill, Inc. / NeuraBridge

### Media (1)

- `FR2218359666` — Haivision Systems, Inc. / Haivision Hub for Government (HUB-GOV)

### Travel Management (1)

- `FR2632558740` — Cornerstone Information Systems / Upstream Gov

## New category proposals

Four proposals, each justified from the fork's own description (full text in `remainder.json`). Accepting or folding each is a decision for the build phase; the forks sit in the buckets above under their proposed names in the meantime.

### NEW: Contract Management (2 fork(s), tiers: L2)

No existing vocabulary category names contract management: Legal & Policy is law/policy work, Finance/Accounting are financial functions, and Operations Management is generic operations rather than the contracts lifecycle the description centres on.

- `F1506046707` — Unison / Contracting SaaS
- `F1510017461` — Unison / FedConnect

### NEW: Energy Management (1 fork(s), tiers: L1)

Primary function is energy procurement via reverse auction for energy supply. None of the 36 categories covers energy sourcing/procurement: Finance is general money/expense management, and Marketing & Sales, Operations Management and Analytics only describe supporting consulting/alerts, not the auction itself.

- `FR2014363920` — Enel X North America / Exchange Platform

### NEW: Event Management (1 fork(s), tiers: L1)

No existing category covers event/conference management and business-matchmaking gatherings; Collaboration covers collaborative work tools and Marketing & Sales does not cover event preparation or conference management.

- `FR2304546222` — My Business Matches / Vendor Event & Business Matchmaking Platform

### NEW: Manufacturing (1 fork(s), tiers: None)

No existing category covers manufacturing/engineering-intent conversion; Operations Management covers running operations, not transforming engineering intent into manufacturable decisions, and Design & Multimedia does not cover manufacturing.

- `FR2632054516` — Neuramill, Inc. / NeuraBridge

Coordinator note on **Contract Management**: two chunk passes independently placed procurement *operations* (AI sourcing, RFP tooling) in Operations Management. The Unison pair is different in kind — the contract lifecycle system of record for federal acquisition — which is why it is proposed as its own category rather than folded into Operations Management. If the build phase prefers fewer categories, Operations Management L2 is the fold target; the two forks would become additions there.

## No-signal set (23 forks)

Every one of the 23 has a cached description; the reason is **prose-only** in all 23 cases (no description is missing). 17 of the 23 are general-platform offerings (`platform_general`) whose prose covers many functions with no primary one. These forks need a live documentation check before classification — flagged here, not fetched, per census scope.

- `FR2220549818` — CirrusMD / CirrusMD Virtual Health Chat for Government (tier: L2) — Description is generic SaaS/security/hosting boilerplate (agile computing, fiscal savings, HIPAA/GDPR compliance, trusted-path event collection) with no sentence describing the health-chat function beyond the product name and a vague 'increases access to Agency Care' phrase.
- `FR2700754078` — CloudFit Software, LLC / CloudFit Federal Platform (tier: null — general platform) — Managed general cloud hosting environment for customer applications/workloads; description lists security, governance, compliance, monitoring, identity, operational support and hosting with no single primary function of its own.
- `FR2004446306` — Elastic / Elastic Cloud (tier: L2 — general platform) — Family of hosted SaaS products / managed Elastic Stack hosting prose with a feature list (security, alerting, monitoring, reporting, machine learning, graphing); no single primary function for this fork is stated.
- `F1305132147` — Ex Libris / Higher-Ed Platform (Alma, Primo, Leganto, Esploro) (tier: L1) — Description is a single generic platform sentence listing component product names (Alma, Primo, Leganto, Esploro, Rialto) and cross-product services/reliability/security/integration, with no function stated for any component or for this fork. Appears truncated/anomalous.
- `FR2700137029` — HealthEdge Software, Inc. / HealthEdge Integrated Solution Suite (tier: null) — Description is a single vague sentence about an agentic operational/financial platform for payers and agencies; no specific function named.
- `F1211011660` — IBM / IBM Cloud for Government (tier: L3-adjacent — general platform) — General IaaS/PaaS hyperscaler-style platform covering servers, networking, storage, VMware and developer tools with no single primary function emphasized.
- `F1208031461A` — IBM / IBM Platform Services for Government (tier: L3-adjacent — general platform) — Bundle of unrelated platform services (endpoint management, IAM, observability, resource management) with no single primary function.
- `F1208031461` — IBM / IBM Platform Services for Government (tier: L2 — general platform) — Duplicate description of the Moderate variant; bundle of unrelated platform services with no single primary function.
- `F1206081363` — IBM / SmartCloud for Government (tier: L3-adjacent — general platform) — General IaaS environment provisioning compute, memory, network, OS and storage; no single primary function emphasized.
- `FR1710033970` — Infor / Infor Government Solutions (IGS) Software as a Service (tier: L2 — general platform) — Integrated multi-suite ERP bundle spanning finance, supply, manufacturing, HCM, asset management and analytics with no single primary function.
- `F1303221956` — IT-CNP / GovDataHosting Cloud Platform (tier: L3-adjacent — general platform) — Fully managed general PaaS hosting platform bundling infrastructure, runtime, security operations and compliance; no single primary function of its own.
- `FR1900048743` — Oracle / Oracle Cloud Infrastructure-Government Cloud (tier: L3-adjacent — general platform) — General government cloud infrastructure/platform covering many workloads with no single primary function emphasized.
- `F1403283529` — Project Hosts Inc. / GSS One - Azure (tier: null — general platform) — General Support System PaaS composed of many general support/security services with no single primary function for this offering.
- `F1510137547` — Rackspace Government Solutions / Rackspace Government Cloud (tier: L2 — general platform) — General managed cloud foundation wrapping VMware/AWS; hosting/compliance prose, no single primary function.
- `F1602257856` — SAP National Security Services Inc. (SAP NS2) / DoD Cloud Intelligent Enterprise – DD-CIE (tier: L2 — general platform) — Secure hosting environment whose description is a catalogue of hosted SAP suites (S/4HANA, SuccessFactors, IBP); no primary function of this fork itself.
- `FR1719841002` — SAP National Security Services Inc. (SAP NS2) / SAP NS2 Cloud Intelligent Enterprise (tier: L2 — general platform) — Secure hosting environment whose description is a catalogue of hosted SAP solutions across CIE/CRE; no primary function of this fork itself.
- `FR1818459251` — Sirsi Corporation (SirsiDynix) / EOS.Web (tier: L1) — Description speaks generically about vendor ILS offerings, security and FedRAMP usability; no sentence states EOS.Web's own specific function.
- `F1207261443` — Skillsoft / Private Cloud (tier: L2) — Description is a company profile of Skillsoft only; no function stated for this Private Cloud offering.
- `F1603077867` — SMX (Formerly Smartronix) / Elevate Intelligent Automation Platform (IAP) (tier: L2 — general platform) — General automation PaaS for cloud adoption plus a catalogue of third-party ISV products (ignored per rules); no single primary function.
- `FR1901852210` — TERIDA / Terida RegTech Framework - CLASsoft (tier: null) — General RegTech framework described for infinite applications across many unrelated objects and use cases; no single primary function.
- `AGENCYNITCIAAS` — United States Department of Agriculture / vGov (tier: L2 — general platform) — General IaaS/PaaS hosting platform catalogue with many infrastructure options and no single primary function.
- `FR1801046750` — United States Department of the Treasury / Treasury Cloud (TCloud) (tier: L3-adjacent — general platform) — Multi-cloud IaaS/PaaS hosting environment listing many unrelated services; no single primary function.
- `AGENCYWC2` — United States Department of the Treasury / Treasury Cloud Moderate (tier: L2 — general platform) — Multi-tenant IaaS/PaaS hosting environment listing many unrelated services; no single primary function.

Two of the 23 deserve a specific flag: `F1305132147` (Ex Libris Higher-Ed Platform) and `FR1818459251` (SirsiDynix EOS.Web) are both library-system offerings whose descriptions never state the library function in a citable sentence — one lists component product names only, the other speaks generically about the vendor's ILS offerings. A "Library Systems" category may well be the honest home for both, but under the citation rule that requires the live product documentation, so both stay no-signal in this census.

Boundary set, recorded rather than silently resolved: managed-hosting platforms whose descriptions emphasize administration services actually performed (setup, configuration, patching, hardening, support) were classified System Administration, while pure infrastructure/platform prose (the IBM platform bundles, Elastic Cloud, Oracle Cloud Infrastructure-Government Cloud, the Treasury/USDA hosting environments) was marked no-signal. The line is thin and the build phase may redraw it; every fork on both sides of it is flagged `platform_general` in `remainder.json`.

## Judgment patterns worth knowing

- **Filed category vs description:** of the 102 categorized uncovered forks, the description-based proposal agrees with the filed category for 56 and differs for 46 (2 of the 46 are no-signal). The largest single flow is forks filed under Artificial Intelligence (AI) whose own descriptions describe an operational tool — AI as technique, not function — landing in Operations Management, Development Tools, Data Management, GRC, Cybersecurity, Construction, and Research. The second flow is Cybersecurity-filed forks whose descriptions center on compliance and evidence automation, landing in GRC. Each reclassification carries its citation in `remainder.json`.
- **Duplicate authorization pairs** (same product, two FedRAMP IDs, identical descriptions) were classified identically: Enablement® (FR2628647239 / FR2635930439), Symantec Gov Cloud Security (FR2232465502 / FR2232465502A), Cisco Security Cloud for Government (FR2304757473 / FR2304757473A), IBM Platform Services for Government (F1208031461 / F1208031461A, both no-signal), Samsara (FR2633153272 / FR2700857493), Specset (FR2631258135 / FR2631747321 — its own description states the second ID is a duplicate pending retirement).
- **Truncated or anomalous descriptions**, classification made from intact sentences and flagged in entry notes: Symantec GCS pair (text ends mid-word), Concourse Platform (ends promising a capability list that does not follow), Replit for Government (a gap where the agent's name should be), Silkline (one anomalous scope sentence, ignored under the catalogue/scope precedents).

## Files

- `remainder.json` — the machine-readable census: all 283 forks with registry fields, proposed category, verbatim citations, bucket and build unit; the 74 build units; the proposed build order. All counts in this document are reproducible from it (`remainder/aggregate.py`).
- `remainder/` — census scratch: `uncovered.json` (the 283 with descriptions), `chunk_1..6.json` (classifier inputs), `class_chunk_1..6.json` (classifier outputs), `class_all.json` (merged), `raw_products.json` (extracted raw records), `aggregate.py`, `build_md.py`.

