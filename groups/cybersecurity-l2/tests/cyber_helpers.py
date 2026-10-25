"""Shared helpers for the Cybersecurity & Risk Management L2 test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is runnable
with ``PYTHONPATH=src`` from the group directory; these helpers additionally
put ``src/`` (and the tests directory itself) on the path so the tests also
run standalone, mirroring ``collab_helpers.py`` in the Collaboration L2
group.

Canonical fixture (used across the suite): one asset named
``core-server-01`` (kind ``server``, owner ``it-ops``, criticality
``high``) created by ANALYST, plus one ingested finding on it —
``Unpatched OpenSSL`` with severity ``high`` from source ``scanner`` —
so its score is 4 * 1.5 = 6.0 with band ``high`` under
``score_finding``. ADMIN (alice, ``admin``) and VIEWER (carol,
``viewer``) hold no fixture objects of their own.
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

from cyber.access import User  # noqa: E402
from cyber.audit import AuditLog  # noqa: E402
from cyber.store import CyberStore  # noqa: E402

ADMIN = User("alice", "admin")
ANALYST = User("bob", "analyst")
VIEWER = User("carol", "viewer")

# Registry as the HTTP layer / CLI sees it (demo identities per contract).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "analyst",
    "carol": "viewer",
}

ASSET_NAME = "core-server-01"
ASSET_OWNER = "it-ops"
FINDING_TITLE = "Unpatched OpenSSL"
FINDING_SOURCE = "scanner"


def fresh_store(audit=None):
    """A bare CyberStore with no assets (for id-sequence tests)."""
    return CyberStore(audit=audit)


def make_asset(store, actor=ANALYST, name=ASSET_NAME, kind="server",
               owner=ASSET_OWNER, criticality="high", tags=None):
    """Create the canonical asset (or a variant via keyword overrides)."""
    kwargs = {}
    if tags is not None:
        kwargs["tags"] = tags
    return store.create_asset(
        name, kind, owner, criticality, actor=actor, **kwargs
    )


def sample_finding_item(asset_id, title=FINDING_TITLE, severity="high",
                        source=FINDING_SOURCE, **extra):
    """A valid finding ingest item for ``asset_id`` (contract keys)."""
    item = {
        "title": title,
        "severity": severity,
        "asset_id": asset_id,
        "source": source,
    }
    item.update(extra)
    return item


def ingest_sample_finding(store, asset_id, actor=ANALYST, **overrides):
    """Ingest one finding on ``asset_id``; defaults are the happy path."""
    return store.ingest_finding(
        sample_finding_item(asset_id, **overrides), actor=actor
    )


def make_store(audit=None):
    """Fresh store + audit log + one asset + one ingested finding.

    Returns ``(store, asset, finding)``: a CyberStore with an AuditLog
    attached (the one passed in, or a new one), the canonical asset
    created by ANALYST, and the canonical finding ingested on it.
    """
    if audit is None:
        audit = AuditLog()
    store = CyberStore(audit=audit)
    asset = make_asset(store)
    finding = ingest_sample_finding(store, asset["id"])
    return store, asset, finding


def create_sample_risk(store, actor=ANALYST, title="Ransomware exposure",
                       description="Unpatched edge systems",
                       likelihood=4, impact=5, **kwargs):
    """Create a risk; the defaults score 4 * 5 = 20, band ``critical``."""
    return store.create_risk(
        title, description, likelihood, impact, actor=actor, **kwargs
    )
