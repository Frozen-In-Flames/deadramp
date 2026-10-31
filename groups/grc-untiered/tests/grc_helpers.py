"""Shared helpers for the GRC untiered-set test suite.

Traces to: the group's core contract — the suite is runnable with
``PYTHONPATH=src`` from the group directory; these helpers additionally
put ``src/`` (and the tests directory itself) on the path so the tests
also run standalone, mirroring ``cyber_helpers.py`` in the
Cybersecurity untiered-set group.

Canonical fixture (used across the suite): one governed system with
the opaque caller-supplied reference ``SYS-001`` (free-text label
``example portal``) created by MEMBER, plus one indicator ``KSI-1``
linked to control ``IA-2``. The store is seeded with the built-in
framework ``NIST-SP-800-53`` and its 21 controls. ADMIN (alice,
``admin``), MEMBER (bob, ``member``) and VIEWER (carol, ``viewer``)
are the documented demo identities.
"""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from grc.access import User  # noqa: E402
from grc.audit import AuditLog  # noqa: E402
from grc.store import GrcStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")

# Registry as the HTTP layer / CLI sees it (demo identities per contract).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
}

SEED_FRAMEWORK_ID = "NIST-SP-800-53"
SYSTEM_REF = "SYS-001"
SYSTEM_NAME = "example portal"
INDICATOR_ID = "KSI-1"


def fresh_store(audit=None):
    """A bare GrcStore (seeded catalog only; no systems or records)."""
    return GrcStore(audit=audit)


def make_system(store, actor=MEMBER, ref=SYSTEM_REF, name=SYSTEM_NAME, **kwargs):
    """Register the canonical governed system (or a variant)."""
    return store.create_system(ref, name, actor=actor, **kwargs)


def make_indicator(store, actor=MEMBER, indicator_id=INDICATOR_ID,
                   name="MFA coverage indicator", control_ids=None, **kwargs):
    """Register the canonical indicator definition (or a variant)."""
    if control_ids is None:
        control_ids = ["IA-2"]
    return store.create_indicator(
        indicator_id, name, control_ids, actor=actor, **kwargs
    )


def make_finding(store, actor=MEMBER, system_ref=SYSTEM_REF,
                 title="Unpatched component", severity="high",
                 source="assessment", due_date="2026-06-30", **kwargs):
    """Create a finding on a system; defaults are the happy path."""
    return store.create_finding(
        title, system_ref, severity, source, due_date, actor=actor, **kwargs
    )


def make_store(audit=None):
    """Fresh store + audit log + one system + one indicator.

    Returns ``(store, system, indicator)``.
    """
    if audit is None:
        audit = AuditLog()
    store = GrcStore(audit=audit)
    system = make_system(store)
    indicator = make_indicator(store)
    return store, system, indicator
