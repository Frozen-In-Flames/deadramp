# Operation DeadRamp — Phase 1: The Fork Map

Every FedRAMP Marketplace product listing, mapped on two axes: FUNCTION (marketplace business category + service model) and TRUST TIER (FedRAMP impact level crosswalked to a CMMC tier). Registry: `forks.json` (781 entries). Crosswalk: `crosswalk.md`.

## Totals

- **Offerings (forks): 781**
- **Vendors: 674** (distinct provider names, verbatim from the source)
- Authorized today (status "FedRAMP Certified"): 547. The remaining 234 are pipeline listings (in process / ready / initial implementation) — included because the map covers the whole marketplace, each with its status recorded.

### By authorization status

| Status | Count |
|---|---:|
| FedRAMP Certified | 547 |
| Initial Implementation | 102 |
| Legacy FedRAMP Ready | 53 |
| Agency Authorization In Process | 46 |
| FedRAMP In Process | 33 |

### By FedRAMP impact level

| Impact level | Count |
|---|---:|
| Low | 24 |
| LI-SaaS | 42 |
| Moderate | 450 |
| High | 124 |
| Unknown | 141 |

### By CMMC tier (crosswalk)

| CMMC tier | Count | FedRAMP levels feeding it |
|---|---:|---|
| L1 | 66 | Low (24) + LI-SaaS (42) |
| L2 | 450 | Moderate (450) |
| L3-adjacent | 124 | High (124) |
| (none — impact Unknown) | 141 | no baseline assigned in source yet |

### By service model

An offering that lists several models counts in each (membership); 767 offerings state a model, 14 state none, 63 span more than one layer.

| Service model | Offerings (membership) |
|---|---:|
| IaaS | 23 |
| PaaS | 82 |
| SaaS | 734 |

## Categories

The category axis is the FedRAMP Marketplace's own business-category taxonomy (36 categories). Each offering takes the first business function declared in its source listing (see Coverage note).

| Category | Offerings |
|---|---:|
| Analytics | 206 |
| Uncategorized (none in source) | 181 |
| Cybersecurity & Risk Management | 96 |
| Collaboration | 86 |
| Artificial Intelligence (AI) | 38 |
| Accounting | 24 |
| Communication | 17 |
| Data Management | 16 |
| Operations Management | 15 |
| Education & Training | 12 |
| Governance, Risk, and Compliance (GRC) | 11 |
| Health & Wellness | 10 |
| Development Tools | 9 |
| Content Management System (CMS) | 8 |
| Construction | 6 |
| Customer Service | 6 |
| Law Enforcement | 6 |
| Contact Center | 5 |
| Fleet Management | 5 |
| Human Resources | 5 |
| Customer Relations Management (CRM) | 4 |
| Finance | 4 |
| Legal & Policy | 2 |
| Travel Management | 2 |
| Grant Management | 1 |
| Learning Management | 1 |
| Mobile Device Management (MDM) | 1 |
| Network Management | 1 |
| Research | 1 |
| System Administration | 1 |
| Talent Development | 1 |

## Sibling groups (merge candidates)

Siblings = same category + same CMMC tier: direct substitutes for each other. Under the Merge Rule (see `crosswalk.md`), **sibling groups are the merge candidates** — forks in a group are the natural parents of a merged fork, which would take the union of their control baselines at the group's tier. Groups of one are omitted; the "Uncategorized (none in source)" bucket and untiered (impact Unknown) offerings cannot form sibling groups because they share no declared function or tier.

**36 sibling groups covering 479 forks.**

### Analytics — L2 (128)

- Aconex for Defense — Oracle
- Adaptiva Onesite Platform — Adaptive Protocols, Inc. (Adaptiva)
- Administrative Data Research Facility (ADRF) — The Coleridge Initiative, Inc.
- Advantage eClinical — Veridix, LLC
- AEON — Distributed Solutions, Inc.
- Alation Cloud Service — Alation
- AppDynamics GovAPM — Cisco AppDynamics
- Appian Government Cloud - Moderate — Appian
- AQtive Guard — SandboxAQ
- ArcGIS Online (AGO) — ESRI
- Archibus — Eptura, Inc
- Armedia Content Cloud — Armedia, LLC
- Atlas by LMI — LMI Solutions
- Axonius Asset Cloud — Axonius Federal Systems
- Aztec Learning System — Aztec Software
- Bizzdesign GovCloud — Bizzdesign US
- Bugcrowd for Government (BCGOV) — Bugcrowd Inc.
- Butterfly Network Ultrasound — Butterfly Network Inc.
- Case Management & Tracking System (CMTS) — WingSwept
- ChatGPT Enterprise and API Platform — OpenAI
- Cisco ThousandEyes for Government — Cisco Systems, Inc.
- Civis Platform — Civis Analytics, Inc.
- Clarivate Intellectual Property AI & Image Search Platform (CIPAI-ISP) — Clarivate Analytics US LLC
- CLEAR1 Gov — Alclear Healthcare LLC (d/b/a CLEAR)
- Cloudera for Government — Cloudera Government Solutions, Inc
- Confluent Cloud for Government (CCG) — Confluent
- Connect.gov — USDA DISC
- Content Delivery Services — Akamai
- Coralogix U.S. GovOps — Coralogix Inc.
- Corelight Open NDR Platform — Corelight
- CorityOne — Cority Software Inc.
- Cornerstone Galaxy — Cornerstone OnDemand
- CrestPoint Environmental Management Service (CEMS) — CrestPoint Solutions, Inc
- Data Enclave Gov — NORC
- Data Integrity Suite for Government — Precisely Software
- Databricks on AWS US East/West — Databricks, Inc.
- Decision Lens Software — Decision Lens Inc.
- Digital.ai Government Cloud — Digital.ai
- Diligent One Platform (D1P) — Diligent, Inc.
- Docebo Learning Platform for Gov (DCBO-GOV) — Docebo
- DocketScope® — DocketScope, Inc.
- eGain Suite — eGain Corporation
- Everlaw Platform — Everlaw, Inc.
- Exiger Federal Cloud (EFC) — Covergent Solutions Inc dba Exiger Government Solutions (EGS)
- Exterro E-Discovery and Legal Software Platform — Exterro, Inc.
- ExtraHop RevealX Federal — ExtraHop Networks
- Federal ZenGRC — Steel Patriot Partners
- Get A-Head (Keel Mind) — Get A-Head
- Glassbeam Clinsights — Glassbeam, Inc.
- Glucommander — Glytec, LLC
- Healthcare Safeware — HB Healthcare Safety, SBC
- IBM Data Services for Government — IBM
- IBM Federal HR Cloud — IBM
- Ideagen Government Cloud — Ideagen
- Incode Platform — Incode Technologies Inc.
- Incydr Gov — Mimecast
- Intelligent Technology Management System (ITMS) — WidePoint Integrated Solutions Corp.
- Issio Information System — Issio Solutions, Inc.
- Judi® — Judi Health™
- Juniper Mist — Juniper Networks
- Kahua Government Network — Kahua, Inc.
- Knox Systems — Knox Systems, Inc.
- LexisNexis Risk Enterprise Platform — LexisNexis Risk Solutions
- Lifebit Platform — Lifebit Biotech
- MARi — MARi, LLC
- Meridian LMS — Meridian Knowledge Solutions, LLC
- Microsoft 365 Government Community Cloud & Supporting Services — Microsoft
- MicroStrategy Cloud for Government — MicroStrategy
- Minsky No-code ML/NLP Knowledge Graphing Platform — dMetrics
- Minuet — Inteum Company
- MongoDB Atlas for Government — MongoDB
- Moodle for Government — Moodle US LLC
- Moveworks GovCloud — Moveworks
- Movius MultiLine and Movius Decentralized Distributed Secure Communications — Movius Interactive Corporation
- Mystic Message Archival — 3rd Eye Technologies LLC.
- Net-Inspect Enterprise Quality Management (EQM) — Net-Inspect LLC
- NetDocuments Document Management System (DMS) — NetDocuments Software, Inc.
- New Relic — New Relic
- NiCE CXone — NICE CXone
- OneScan — LSPedia
- Onspring GovCloud — Onspring Technologies, LLC
- Ontario Cloud Federal (OCF) — Ontario Systems, LLC d/b/a Finvi
- Ontic for Government — Ontic Technologies
- OrbusInfinity Government — Orbus Software
- Patlytics AI Platform — Patlytics, Inc.
- Persona for Government — Persona Identities, LLC
- Phenom for Government (PHGOV) — Phenom People, Inc. (Phenom)
- Privacy Preserving Records Linkage (PPRL) — HealthVerity
- ProjectTeam for Government (Construction Project and Program Management) — ProjectTeam, Inc.
- Qlik Cloud Government — Qlik Technologies Inc.
- Quality Excellence Gov (Qx Gov) — MasterControl
- Questionmark Government — QuestionMark
- QuestionPro Research GovCloud — QuestionPro, Inc.
- Repario Government Solutions (RGS) — Repario
- Rescale Platform — Rescale
- RingMD Telemedicine — RingMD USA Inc.
- Rubrik Security Cloud - Government (RSC-G) — Rubrik
- RunCyberAssurance — Noblis
- SailPoint Identity Security Cloud — SailPoint Technologies, Inc.
- SAS AI and Analytics for Government on FedRAMP — SAS Institute, Inc.
- ScienceLogic Government Cloud — ScienceLogic, Inc.
- SecurityScorecard Security Ratings — SecurityScorecard, LLC
- Singularity — End To End Computing
- Siteimprove Federal Platform — Siteimprove Inc
- Spaces for Government — Cisco
- Spider Impact for Government — Spider Strategies
- Splunk Cloud Platform for FedRAMP Moderate — Splunk
- SPROUT — MDRC
- Sumo Logic — Sumo Logic
- Supply Chain Command — BlueVoyant Government Services
- T-Metrics Cloud Contact Center (TCCC) — T-Metrics, Inc.
- TalaTek intelligent Governance and Risk Integrated Solution (TiGRIS) — TalaTek, LLC
- TechnoMile GovCloud Platform — TechnoMile
- The Data Cloud on AWS US East/West — Snowflake Inc.
- Third-Party Risk Intelligence System (TRIS)'s — NormShield, Inc. DBA Black Kite
- ThreatConnect For Government — ThreatConnect
- Tracers with AMP® — Joint Commission Resources
- TransAccess GovCloud Records (GCR) — Peniel Solutions, LLC
- Tyler Data Platform, powered by Socrata — Tyler Technologies Data & Insights
- UKG Government Cloud — UKG Inc.
- Vantage for Government — Nozomi Networks Inc.
- Verily Pre — Verily Health
- Veritone Intelligent Digital Evidence Management System (iDEMS) for Government — Veritone, Inc.
- Verkada Command Platform — Verkada Inc
- VisibleThread — VisibleThread
- WordPress VIP — Automattic, Inc.
- Workday Government Cloud (WGC) — Workday Inc.
- ZEF — ZeroEyes Inc

### Collaboration — L2 (57)

- 911inform — 911inform
- Adobe Acrobat Sign for Government — Adobe
- Adobe Connect Managed Services (ACMS-GC) — Adobe
- Adobe Experience Manager Managed Services (AEMMS-GC) — Adobe
- ArcSuite AI — ArcSuite AI (Formerly ArcProcure)
- Asana — Asana Inc.
- Atlassian Government Cloud — Atlassian
- Autodesk for Government — Autodesk
- Avaya Government Cloud — Avaya Federal Solutions, Inc.
- AvePoint Online Services for US Government (AOS-UG) — AvePoint Inc.
- Bentley for Government — Bentley Systems, Incorporated
- Bluescape with n8n for Government — Bluescape
- BMC Helix — BMC Helix, Inc.
- Chronus for Government — Chronus LLC
- Cloud Contact Center — Lumen
- CyberSTAR™ — WillCo Tech
- Dejero Control and Concentrator — Dejero Labs, Inc.
- EgnyteGov — Egnyte
- Entratus Conversational AI Platform — Entratus
- ESChat — San Luis Aviation, Inc.
- Federal Immersive Learning Management System (FED-ILMS) — Creative Veteran Productions
- Figma for Government — Figma
- Filevine Platform — Filevine
- GitLab Dedicated for Government — GitLab
- GovDash — GovDash
- HP Managed Services for Government — HP Inc.
- Humanify Enterprise - Government (Humanify Enterprise - G) — TeleTech (TTEC) Services Corporation
- Icertis Contract Intelligence (ICI) for Government — Icertis Inc.
- IRBNet on GovCloud — Research Dataware LLC
- Ironclad CLM — Ironclad Inc.
- Kernos — Valley IT Solutions, LLC
- LabArchives for Government (LG) — LabArchives
- Lucid GovSuite — Lucid Software, Inc.
- Managed Access Gateway with Managed Microsoft 365 — Exostar
- MAXIMUS Cloud — MAXIMUS Inc.
- Midwatch — Defense Cybersecurity Group
- MuleSoft Government Cloud — MuleSoft
- NetSfere Enterprise — Infinite Convergence Solutions, Inc.
- Nintex Automation GE Platform — Nintex
- Nuance Dragon — Nuance
- OnSolve Platform for Critical Event Management — OnSolve LLC
- OpenText Cloud for Government — OpenText
- Paramify Cloud — Paramify
- Pexip Government Cloud (PGC) — Pexip Inc.
- Rave Safety Platform — Rave Mobile Safety
- ReadyOp — Cleartronic, Inc. dba. ReadyOp Communications, Inc.
- RegDOX Cloud Security Solutions — RegDOX Solutions
- RMA iQ™ — Feith Sytems and Software, Inc.
- RSA® ID Plus for Government — RSA Security LLC
- Slack — Slack Technologies
- Talkdesk CX Cloud™ Government Edition — Talkdesk
- Thomson Reuters Risk & Fraud (TR R&F) — Thomson Reuters
- TMS Gov Cloud Suite — Gallery Systems
- Totara Talent Development Government Cloud Platform — Totara Learning Inc.
- Virtru Data Security Platform — Virtru
- Visionlink COS2 — Visionlink, Inc.
- Zoom for Government — Zoom Video Communications, LLC

### Analytics — L3-adjacent (54)

- 2F Game Warden — Second Front Systems
- Altana Product Network — Altana
- Andesite Azimuth for Government AAG — Andesite AI, Inc.
- Appian Government Cloud - High — Appian
- Aqua Platform for Government — Aqua Security Software Inc.
- Ark.ai — Govini
- Ask Sage — Ask Sage, Inc.
- Azure Commercial Cloud — Microsoft
- Azure Government (includes Dynamics 365) — Microsoft
- Casepoint Government — Casepoint LLC
- Clearview GovCloud — Clearview AI, Inc.
- Cloudflare for Government — Cloudflare, Inc.
- CORAS Federal — CORAS
- Coretsu Government Suite — Coretsu Inc.
- Critical Event Management - GovCloud — Everbridge
- CrowdStrike Falcon Platform for Government — CrowdStrike, Inc.
- CrowdStrike Falcon Platform IL5 SaaS — CrowdStrike, Inc.
- Cyber AI Mission Defense and Email Protection — Darktrace Federal Inc.
- Databricks on AWS GovCloud — Databricks, Inc.
- Databricks on Azure Commercial — Databricks, Inc.
- Datadog for Government — Datadog, Inc.
- DSS Health Cloud (DSSHC) — Document Storage Systems, Inc. (DSS, Inc.)
- Elastic Cloud Hosted - High — Elastic Cloud Hosted
- Elevate Intelligent Automation Platform (IAP) — SMX
- Forescout for Government — Forescout Technologies, Inc.
- GCS-HIGH — Palo Alto Networks, Inc.
- Google Services (Google Cloud Platform Products and underlying Infrastructure) — Google
- Grok for Government — xAI
- H2O.AI — H2O.AI for Government
- IAM Advantage — UberEther
- IBM Federal ATOM — IBM
- Island Enterprise Platform — Island
- Juvare Federal Cloud — Juvare, LLC
- Kaseware Investigative Case Management System — Kaseware, Inc
- Knox Systems FedRAMP High Managed Platform — Knox Systems, Inc.
- Mark43 Public Safety Platform (PSP) — Mark43, Inc.
- Microsoft 365 Government Community Cloud-High — Microsoft
- Netskope NewEdge Government. — Netskope, Inc.
- Omnissa Government Services — Omnissa
- Palantir Federal Cloud Service — Palantir Technologies Inc.
- Palantir Federal Cloud Service – Supporting Services (PFCS-SS) — Palantir Technologies
- Qualtrics XM Platform - High — Qualtrics, LLC
- Quzara Cybertorch (SOC-as-a-Service) — Quzara, LLC.
- Riverbed Platform for Government (RP4G) — Riverbed Technology
- Scale AI Data Platform — Scale AI, Inc
- SentinelOne Singularity Platform High — SentinelOne
- Skyhigh Security Service Edge (SSE) Government Cloud Services (Cloud Access Security Broker (CASB) & Secure Web Gateway (SWG) for Cloud) — Skyhigh Security
- Splunk Cloud Platform for FedRAMP High — Splunk
- The Data Cloud on AWS GovCloud (High) — Snowflake Inc.
- The Data Cloud on Azure Government (High) — Snowflake Inc.
- Trellix GovCloud Security Platform — Trellix
- Vasion Automate Fed (VAF) — Vasion
- WellHive — WellHive Holdings, LLC
- Wiz for U.S. Government — Wiz, Inc.

### Cybersecurity & Risk Management — L2 (54)

- Absolute Secure Endpoint Product Suite — Absolute Security
- Accenture Extended Detection and Response (XDR) for government — Accenture Federal Services
- Anomali Security Operations Platform — Anomali Inc
- AppOmni SaaS Security for Government — AppOmni
- Axiad Conductor — Axiad IDS Inc.
- Check Point Infinity Platform for Government — Check Point Software Technologies, Inc.
- Checkmarx One for Government (CXG) — Checkmarx
- Cisco Catalyst SD-WAN for Government (SDWAN-G) — Cisco Systems, Inc.
- Cloud Security Platform powered by Isolation Core — Menlo Security
- CMMC Space — ATX Defense
- Cofense PhishMe — Cofense
- Cohesity Cloud Services for Government — Cohesity
- Commvault Clumio Data Protection Platform — Commvault Systems, Inc.
- ComplySyncATO — ASSYST
- Cribl.Cloud Government — Cribl Inc.
- Druva Data Resiliency Cloud — Druva, Inc.
- DTEX InTERCEPT for Government — DTEX Systems, Inc.
- Everfox ULTRA — Everfox
- F5 Distributed Cloud — F5, Inc.
- FedRAMP Compliant CloudPlus — DataBank Holdings
- GreyMatter for Government — ReliaQuest
- Halcyon — Halcyon Tech, Inc.
- iboss Government Cloud Platform (IGCP) — iBoss
- IDCommand — Lastwall Corp
- Illumio Government Cloud — Illumio, Inc.
- Infinity for Government (NXT-G) — Nexthink
- Infoblox Government Cloud — Infoblox
- InsightGovCloud — Rapid7
- IntelliGRC — IntelliGRC, Inc.
- ITAM — ContinuumGRC, Inc.
- KnowBe4 Platform — KnowBe4, Inc.
- LevelBlue Threat Detection and Response for Government — LevelBlue
- Lookout Security Platform — Lookout, Inc.
- NinjaOne for Government — NinjaOne
- Nucleus for Government (NucleusGov) — Nucleus Security, Inc
- On-Demand Security Testing Platform — Synack
- Own Government Cloud — OwnBackup
- Privoro Fulcrum Cloud — Privoro LLC
- Secureframe Platform — Secureframe
- SentiLink — SentiLink Corp
- Snyk for Government — Snyk
- Socure for Government (SocureGov) — Socure, Inc.
- Tenable Cloud Security for US Government - Ermetic — Tenable
- Tenable Government Solutions — Tenable Public Sector (TPS)
- Trend Cloud One for Government — Trend Micro Inc.
- Trend Vision One for Government — Trend Micro Inc.
- Trustwave Fusion — Trustwave Government Solutions
- Vanta Government Cloud — Vanta
- Varonis Data Security Platform — Varonis
- Varonis DatAdvantage Cloud — Varonis
- Veracode Online Security Platform for Government — Veracode
- Wallarm Federal Cloud — Wallarm, Inc.
- Zscaler Internet Access - Government (Secure Web Gateway - vTIC) — Zscaler, Inc.
- Zscaler Private Access - Government (Zero Trust Exchange - VPN Replacement) — Zscaler, Inc.

### Accounting — L2 (21)

- Actus — Paperless Innovations, Inc.
- BlackLine Government Solution — BlackLine Systems, Inc.
- Concur Cloud for Public Sector — Concur Technologies, Inc.
- Costpoint GovCon Cloud Moderate (CP GCCM) — Deltek, Inc.
- Elite Enterprise Solutions — Tecsys, Inc.
- Footprint — Booz Allen Hamilton
- Fusion Cloud — Oracle
- Masterworks Cloud Platform — Aurigo Software Technologies, Inc.
- MCG Applications and Hosting — MCG Energy Solutions, LLC
- OneSpan Sign, E-Signature and Digital Signature Service — OneSpan Inc.
- Oracle Enterprise Performance Management (EPM) — Oracle
- Oracle Primavera Cloud for Government — Oracle Corporation
- PowerCore™ (PC-GOV) — Power Settlements Consulting and Software, LLC (PSCS), a subsidiary of Yes Energy, LLC
- Procore for Government — Procore Technologies, Inc
- Reactor — Chainalysis
- Replicon Cloud Platform (Enterprise Time Tracking Platform) — Deltek - Replicon
- S.M.A.R.T. - Federal Editions — Quadient inc.
- Sunflower Asset Management Cloud (SAMC) — CGI Federal
- TeamMate FedRAMP — Wolters Kluwer
- Total Visibility Anywhere — Tactical Edge
- Valid8 Financial GovCloud — Valid8 Financial

### Collaboration — L3-adjacent (17)

- AvePoint Online Services for US Government (AOS-UG) - High — AvePoint Inc.
- BlackBerry Cloud - AtHoc Services for Government (High) — BlackBerry
- Box Enterprise Cloud Content Collaboration Platform — Box Inc.
- CoLab AI Inc — CoLab
- CyCloud for VMware Cloud Foundation — CyLogic
- ESChat - High — San Luis Aviation, Inc.
- Google Workspace — Google
- Government Community Cloud — ServiceNow
- GSS One AWS — Project Hosts Inc.
- GSS One Azure — Project Hosts Inc.
- Intrepid Networks Government Platform (INGP) — Intrepid Networks LLC
- Koniag Government Services Electronic Health Record System (KGS EHRS) — Koniag Government Services
- Okta IDaaS Government High Cloud (GHC) — Okta
- Paramify Cloud — Paramify
- RegScale CCM — RegScale
- Salesforce Government Cloud Plus — Salesforce
- Storm Cloud Contact Center — Content Guru

### Analytics — L1 (16)

- Accessibility Management Platform (AMP) — Level Access
- AchieveIt — AchieveIt Online, LLC
- Adobe Analytics — Adobe
- Agile RTLS Suite (A-RTLS) — AgileRank
- American Heart Association Precision Medicine Platform(AHA-PMP) — American Heart Association, Inc.
- Configurable Case Management Application Platform (CMAP) — Syneren Technologies Corporation
- Electric Vehicle Infrastructure Platform for Government — Chargie, LLC
- EnergyCAP — EnergyCAP LLC.
- Gemini for Government — Google
- Hootsuite Enterprise — Hootsuite
- IBM Envizi ESG Reporting — IBM
- Melissa GovCloud Address Suite — Melissa
- Omega Charge Management System — BP Pulse
- Perplexity Enterprise and API Platform — Perplexity AI
- VLogicFM — VLogic Systems, Inc.
- zLinkFM — zLink, Inc.

### Cybersecurity & Risk Management — L3-adjacent (16)

- Caveonix — Caveonix, Inc.
- Cyera for Government — Cyera
- Idira Endpoint Privilege Manager for Government — Palo Alto Networks, Inc.
- Idira Identity Security Government Services Platform — Palo Alto Networks, Inc.
- Keeper ICAM & Identity Security Platform for Government — Keeper Security
- NetCloud Federal — Ericsson
- NinjaOne for Government – FedRAMP High — NinjaOne
- Optum Serve Federal Platform — Optum Serve
- Qualys Government Platform — Qualys, Inc.
- Saviynt High Security Identity Platform — Saviynt
- The Armory — stackArmor
- Wraithwatch Government — Wraithwatch Corporation
- Xacta SaaS — Telos Corporation
- xDome for Government — Claroty
- Zscaler Internet Access - Government (Secure Web Gateway - vTIC) - High — Zscaler, Inc.
- Zscaler Private Access - Government (Zero Trust Networking - VPN Replacement) — Zscaler, Inc.

### Artificial Intelligence (AI) — L2 (11)

- Aeroplicity — Aeroplicity Inc.
- asato.ai — Asato Corporation
- AWS US East/West — Amazon Web Services, Inc.
- Bidscale — Unison
- CabletequeGov — Cableteque Corp.
- Consus Gateway — Consus Industries, Inc.
- Genesys Cloud CX — Genesys
- GroundControl — Ground Control Software Inc.
- Magenta — Magenta
- Praxon Arc — Praxon Labs Inc.
- Stell Requirements Management System — Stell Engineering

### Collaboration — L1 (10)

- A-SCEND — A-LIGN
- Adobe Creative Cloud for Enterprise — Adobe
- Adobe Document Cloud including Adobe Acrobat, Adobe Acrobat Sign, Adobe Acrobat AI Assistant, Adobe Acrobat Analyzer, and Adobe Acrobat Services (APIs) — Adobe
- Adobe Learning Manager — Adobe
- Aprimo — Aprimo US, LLC
- Overleaf — Digital Science UK Limited
- Point Blue Science Cloud — Point Blue Conservation Science
- Vbrick Enterprise Video Platform — Vbrick Systems, Inc.
- Vyond for Government — Vyond
- Vyond for Government — Vyond

### Communication — L2 (10)

- Abnormal AI for Government — Abnormal AI
- Archive360 Platform — Archive360 platform
- Critical Event Management Suite — Everbridge
- GetEKKO — Red Rock Group Holdings
- IQ FedCloud — Leidos Digital Solutions, Inc.
- Keyfactor for Government — Keyfactor
- Maximus Intelligent Virtual Assistant (MIVA) (formerly MIA) — MAXIMUS Inc.
- Omega Platform — BlackOhm
- RecAccess — RecAccess
- Trellix Email Security GovCloud — Trellix

### Data Management — L2 (8)

- Asset Management Suite (AMS) — Bridge Intelligence LLC. dba AssetIntel
- Boomi Enterprise Platform — Boomi, Inc.
- Collabspace — Collabware
- Datavant Cloud — Datavant
- GovPoint Cloud Services — MIS Sciences Corporation
- Intelliworx Cloud Workflow Platform — Intelliworx
- Palette VerteX — Spectro Cloud
- PMP Government-Gateway — Bamboo Health, Inc.

### Education & Training — L2 (8)

- Acadis Readiness Suite — Envisage Technologies LLC
- Blackboard LMS — Blackboard
- Gov Secure Cloud — PSI Services LLC
- Laerdal -- SimCapture Cloud Government — Laerdal Labs D.C.
- NEOGOV Cloud — NEOGOV
- Next Generation Cloud Platform — Peraton Corporation
- Palladium — PDRI by Pearson
- Pepelwerk Government — Pepelwerk LLC

### Communication — L3-adjacent (6)

- Akamai Cloud — Akamai
- Artera Harmony Federal Edition — Artera
- Enterprise Cloud Fax Government (ECFax) — Consensus Cloud Solutions
- ETHERFAX GovCloud — ETHERFAX
- Hypori Government Cloud — Hypori, Inc.
- Motorola Solutions Federal Cloud (MSFC) — Motorola Solutions

### Contact Center — L2 (5)

- BeyondTrust Identity Security For Government — BeyondTrust
- ClaimsXM — Signature Performance, Inc.
- LM for Gov — LogicMonitor
- Mindful by Medallia — Medallia Inc.
- Security Control Cloud Software Platform (SCCP) — Security Control LLC (an ISI Company)

### Cybersecurity & Risk Management — L1 (5)

- Drata Trust Management Platform — Drata
- FedFlex — Anitian
- IntelliGRC — IntelliGRC, Inc.
- MapLarge — MapLarge Inc.
- Valimail Enforce Platform — Valimail

### Development Tools — L1 (5)

- Articulate 360 — Articulate Global LLC
- CircleCI Cloud — CircleCI
- Digital Enterprise Suite FedRAMP Edition — Trisotech
- GitHub Enterprise Cloud — GitHub
- The Armory20x — stackArmor

### Health & Wellness — L2 (5)

- Composite Apps/ CuraPatient — CuraPatient
- Dexcom Clarity for Government — Dexcom Inc.
- Elekta ProKnow Federal — Elekta Solutions
- GetWellNetwork  - Get Well Anywhere - Federal — GetWellNetwork
- LibreView for US Government — Abbott, Inc.

### Construction — L2 (4)

- Actsoft Workforce Manager for Gov. — Actsoft, Inc
- Contract Insight — CobbleStone Software
- Gordian Federal Cloud powered by RSMeans Data — Gordian
- LCPtracker Pro — LCptracker Inc

### Content Management System (CMS) — L2 (4)

- Acquia Cloud — Acquia Inc.
- Bibliovation/Knowvation — PTFS/Liblime
- Digital Health Research Platform — Vibrent Health
- Tyler Federal Cloud Platform (TFCP) — Tyler Federal, LLC

### Human Resources — L2 (4)

- Avature Limited — Avature Federal Platform
- Economic Systems Federal Human Resources Navigator — Economic Systems
- Eightfold Talent Intelligence Platform (TIP) — Eightfold AI Inc.
- FedHire — Apply Government Solutions

### Artificial Intelligence (AI) — L3-adjacent (3)

- Canopy — Ripcord
- Cognition Platform — Cognition USG, Inc.
- DataRobot for Government — DataRobot

### Accounting — L3-adjacent (2)

- AI for Federal Acquisitions (ACQBOT) — Trenchant Analytics
- Citrix for Government - High — Citrix Systems, Inc.

### Content Management System (CMS) — L1 (2)

- TimeLooper Inc. — TimeLooper Xplore
- WorldShare Management Services — OCLC Incorporated

### Customer Relations Management (CRM) — L2 (2)

- Oracle Service Cloud (OSvC) — Oracle
- WalkMe DAP — WalkMe, Inc

### Customer Service — L1 (2)

- PagerDuty Operations Cloud — PagerDuty
- Riskuity — Longevity Consulting

### Customer Service — L2 (2)

- NCR VOYIX GOVERNMENT CLOUD — NCR Government, LLC
- Virtual Employee Network (VEN) — Relocation Management Worldwide (RMW)

### Data Management — L3-adjacent (2)

- Kiteworks Secure Gov Cloud — Kiteworks USA, LLC
- US Axon FedCloud - High — Axon

### Development Tools — L2 (2)

- AutoRABIT for Public Sector - CodeScan, Guard, & ARMOR — AutoRABIT Holding, Inc.
- LaunchDarkly — LaunchDarkly

### Education & Training — L1 (2)

- Amplifire — Amplifire
- RQI1Stop — RQI Partners LLC

### Finance — L2 (2)

- DailyPay for Government — DailyPay
- Groupize — Groupize, Inc.

### Fleet Management — L1 (2)

- CP Fed Cloud — ChargePoint, Inc.
- FleetCommander — Agile Fleet

### Governance, Risk, and Compliance (GRC) — L2 (2)

- Constellation GovCloud (CGC) — Merlin International
- XBU40 — InfusionPoints

### Law Enforcement — L2 (2)

- Lexis+® for Government — LexisNexis Legal and Professional
- Thomson Reuters Legal Research (TR LR) — Thomson Reuters

### Law Enforcement — L3-adjacent (2)

- Cellebrite Government Cloud (CGC) — Cellebrite
- Magnet One — Magnet Forensics

### Operations Management — L2 (2)

- Mathematica Cloud Support System — Mathematica Inc.
- TrackVia Government — TrackVia, Inc.

## Stack relations

Stack rule (from the concept brief): IaaS forks sit under PaaS forks, which sit under SaaS forks. Read off the service-model data:

- **Layer 1 — IaaS (foundation): 23 offerings** list IaaS.
- **Layer 2 — PaaS (platform): 82 offerings** list PaaS.
- **Layer 3 — SaaS (application): 734 offerings** list SaaS.
- 63 offerings span layers (they list 2–3 models) and 14 list no model in the source.

Which categories live at which layer (membership counts; a multi-model offering appears in each of its layers):

| Category | IaaS | PaaS | SaaS | No model stated |
|---|---:|---:|---:|---:|
| Analytics | 4 | 26 | 197 | 4 |
| Uncategorized (none in source) | 7 | 25 | 162 | 1 |
| Cybersecurity & Risk Management | 1 | 6 | 92 | 2 |
| Collaboration | 3 | 8 | 83 | 1 |
| Artificial Intelligence (AI) | 1 | 3 | 31 | 6 |
| Accounting | 1 | 2 | 24 | 0 |
| Communication | 2 | 1 | 15 | 0 |
| Data Management | 1 | 1 | 16 | 0 |
| Operations Management | 0 | 1 | 15 | 0 |
| Education & Training | 0 | 1 | 12 | 0 |
| Governance, Risk, and Compliance (GRC) | 0 | 2 | 10 | 0 |
| Health & Wellness | 0 | 0 | 10 | 0 |
| Development Tools | 0 | 0 | 9 | 0 |
| Content Management System (CMS) | 0 | 1 | 7 | 0 |
| Construction | 0 | 0 | 6 | 0 |
| Customer Service | 1 | 1 | 6 | 0 |
| Law Enforcement | 0 | 0 | 6 | 0 |
| Contact Center | 0 | 0 | 5 | 0 |
| Fleet Management | 0 | 0 | 5 | 0 |
| Human Resources | 0 | 0 | 5 | 0 |
| Customer Relations Management (CRM) | 1 | 2 | 4 | 0 |
| Finance | 1 | 1 | 4 | 0 |
| Legal & Policy | 0 | 0 | 2 | 0 |
| Travel Management | 0 | 0 | 2 | 0 |
| Grant Management | 0 | 0 | 1 | 0 |
| Learning Management | 0 | 0 | 1 | 0 |
| Mobile Device Management (MDM) | 0 | 0 | 1 | 0 |
| Network Management | 0 | 0 | 1 | 0 |
| Research | 0 | 0 | 1 | 0 |
| System Administration | 0 | 1 | 0 | 0 |
| Talent Development | 0 | 0 | 1 | 0 |

Reading: pure-infrastructure categories (Storage, Network Management, System Administration) hold most of the true IaaS/PaaS layer; the SaaS layer carries nearly everything else. A DeadRamp build order that respects the stack builds Layer 1 categories first, because PaaS and SaaS forks sit on them.

## Coverage note (honest)

- **Source.** The official FedRAMP Marketplace product dataset published by the General Services Administration, embedded in the marketplace products page at https://www.fedramp.gov/marketplace/products/ (the old marketplace.fedramp.gov now redirects there). The dataset's own metadata: produced by GSA, last changed 2026-10-22. Fetched 2026-10-25; raw page and extracted dataset are cached in `raw/`. Every registry entry's `source_url` is that offering's live marketplace product page.
- **Completeness.** The registry contains all 781 product records in the source dataset — classic Rev5 authorizations (659), FedRAMP 20x (95), and 20x Pilot (27) listings alike, at every status from Certified to Initial Implementation. Two vendor submissions (FedRAMP IDs FR2634659095 and FR2635930482) are absent because GSA's own indexer skipped them for validation errors in the vendor-submitted data; they appear in the source's SkippedEntities list and cannot be mapped until the source includes them.
- **Verification.** All headline counts were recounted by an independent method (regex over the raw page text) and matched forks.json exactly for every impact level and every status; the Certified count (547) also matches the marketplace's own published Metrics figure.
- **Known gaps in the source data itself.** 181 offerings declare no business function, so their category is recorded as "Uncategorized (none in source)" rather than guessed. 141 offerings have impact level "Unknown" in the source (no baseline assigned yet), so they carry no CMMC tier. 14 offerings state no service model. 13 vendor+product name pairs appear twice under different FedRAMP IDs (e.g., the same product authorized on two paths); each ID is a separate marketplace offering, so each is a separate registry entry.
- **Category rule.** Category = the first business function in the offering's marketplace listing (from its `business_categories` field when present, otherwise the first business-function filter tag in the same listing). Multi-function offerings exist (some declare up to 10 functions); only the first is used as the primary category so every fork has exactly one sibling group.
- **LI-SaaS.** FedRAMP's LI-SaaS is a tailored subset of the Low baseline for SaaS offerings; it is crosswalked to CMMC tier L1 with Low, and its source value "LI-SaaS" is preserved in the registry.
