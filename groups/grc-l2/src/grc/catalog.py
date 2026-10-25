"""Seed catalog: one generic 800-53-style framework and its controls.

Clean-room seed data for the framework & control registry. The seed
is deliberately modest and generic: one framework record and 21
controls, each a dict ``{id, family, title}`` where ``family`` is the
alphabetic prefix of the control id. The registry in
:mod:`grc.store` is seeded from this data at construction, and
callers may register further frameworks and controls of their own.
This is reference data for mapping and record-keeping -- it is not an
authorization or a certification, and it does not claim either.
"""

SEED_FRAMEWORK = {
    "id": "NIST-SP-800-53",
    "name": "NIST SP 800-53",
    "version": "Rev. 5",
    "description": "Security and Privacy Controls for Information Systems and Organizations (seed catalog, generic subset).",
}

_CONTROLS = [
    ("AC-2", "Account Management"),
    ("AC-3", "Access Enforcement"),
    ("AC-6", "Least Privilege"),
    ("AT-2", "Literacy Training and Awareness"),
    ("AU-2", "Event Logging"),
    ("AU-6", "Audit Record Review, Analysis, and Reporting"),
    ("CA-2", "Control Assessments"),
    ("CA-5", "Plan of Action and Milestones"),
    ("CA-7", "Continuous Monitoring"),
    ("CM-6", "Configuration Settings"),
    ("CM-8", "System Component Inventory"),
    ("CP-9", "System Backup"),
    ("IA-2", "Identification and Authentication"),
    ("IA-5", "Authenticator Management"),
    ("IR-4", "Incident Handling"),
    ("RA-3", "Risk Assessment"),
    ("RA-5", "Vulnerability Monitoring and Scanning"),
    ("SC-7", "Boundary Protection"),
    ("SC-28", "Protection of Information at Rest"),
    ("SI-2", "Flaw Remediation"),
    ("SI-4", "System Monitoring"),
]

CONTROL_CATALOG = [
    {"id": control_id, "family": control_id.split("-", 1)[0], "title": title}
    for control_id, title in _CONTROLS
]

CONTROL_IDS = frozenset(entry["id"] for entry in CONTROL_CATALOG)

_BY_ID = {entry["id"]: entry for entry in CONTROL_CATALOG}


def control_by_id(control_id):
    """Return the seed catalog dict for ``control_id``, or ``None``."""
    entry = _BY_ID.get(control_id)
    if entry is None:
        return None
    return dict(entry)
