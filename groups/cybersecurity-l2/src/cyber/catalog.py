"""Built-in NIST SP 800-53 Rev. 5 control catalog.

Clean-room data table fixed by the union spec: 34 controls, each a
dict ``{id, family, title}`` where ``family`` is the alphabetic prefix
of the control id. This is a reference catalog for mapping and
assessment -- it is not a FedRAMP authorization or a CMMC
certification, and it does not claim either.
"""

_CONTROLS = [
    ("AC-2", "Account Management"),
    ("AC-3", "Access Enforcement"),
    ("AC-6", "Least Privilege"),
    ("AC-17", "Remote Access"),
    ("AT-2", "Literacy Training and Awareness"),
    ("AU-2", "Event Logging"),
    ("AU-3", "Content of Audit Records"),
    ("AU-6", "Audit Record Review, Analysis, and Reporting"),
    ("AU-9", "Protection of Audit Information"),
    ("CA-2", "Control Assessments"),
    ("CA-5", "Plan of Action and Milestones"),
    ("CA-7", "Continuous Monitoring"),
    ("CM-6", "Configuration Settings"),
    ("CM-7", "Least Functionality"),
    ("CM-8", "System Component Inventory"),
    ("CP-9", "System Backup"),
    ("IA-2", "Identification and Authentication"),
    ("IA-5", "Authenticator Management"),
    ("IR-4", "Incident Handling"),
    ("IR-5", "Incident Monitoring"),
    ("MP-6", "Media Sanitization"),
    ("RA-3", "Risk Assessment"),
    ("RA-5", "Vulnerability Monitoring and Scanning"),
    ("SA-10", "Developer Configuration Management"),
    ("SC-7", "Boundary Protection"),
    ("SC-8", "Transmission Confidentiality and Integrity"),
    ("SC-12", "Cryptographic Key Establishment and Management"),
    ("SC-13", "Cryptographic Protection"),
    ("SC-28", "Protection of Information at Rest"),
    ("SI-2", "Flaw Remediation"),
    ("SI-3", "Malicious Code Protection"),
    ("SI-4", "System Monitoring"),
    ("SI-10", "Information Input Validation"),
    ("SI-16", "Memory Protection"),
]

CONTROL_CATALOG = [
    {"id": control_id, "family": control_id.split("-", 1)[0], "title": title}
    for control_id, title in _CONTROLS
]

CONTROL_IDS = frozenset(entry["id"] for entry in CONTROL_CATALOG)

_BY_ID = {entry["id"]: entry for entry in CONTROL_CATALOG}


def control_by_id(control_id):
    """Return the catalog dict for ``control_id``, or ``None``."""
    entry = _BY_ID.get(control_id)
    if entry is None:
        return None
    return dict(entry)
