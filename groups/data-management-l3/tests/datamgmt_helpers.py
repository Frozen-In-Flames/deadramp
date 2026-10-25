"""Shared helpers for the Data Management L3-adjacent merged-build suite.

Traces to: the contract for Group 28 (Data Management L3-adjacent) --
inherited from Group 12 (Data Management L2) and uplifted to the High
baseline. The suite is runnable with ``PYTHONPATH=src`` from the group
directory; these helpers additionally put ``src/`` on the path so tests
also run standalone.

Canonical fixture: a store with an AuditLog, one dataset ("Claims
Extract", classification "cui", tags ["claims", "nightly"], schema
patient_id/amount) and one source ("ehr-feed", kind "api", location
"ehr.internal"), both created by STEWARD.
ADMIN=alice/admin, STEWARD=bob/steward, VIEWER=carol/viewer,
AUDITOR=dana/auditor (audit_read only; AC-5).
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

from datamgmt.access import User  # noqa: E402
from datamgmt.audit import AuditLog  # noqa: E402
from datamgmt.store import DataMgmtStore  # noqa: E402

ADMIN = User("alice", "admin")
STEWARD = User("bob", "steward")
VIEWER = User("carol", "viewer")
AUDITOR = User("dana", "auditor")

USERS = {"alice": "admin", "bob": "steward", "carol": "viewer", "dana": "auditor"}
# Alias matching other groups' naming.
USERS_REGISTRY = USERS

CANONICAL_SCHEMA = [
    {"name": "patient_id", "type": "string", "required": True, "sensitive": True},
    {"name": "amount", "type": "number", "required": True, "sensitive": False},
]


def fresh_store(audit=None):
    """A bare DataMgmtStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return DataMgmtStore(audit=audit)


def make_store(audit=None):
    """Fresh store + canonical dataset + canonical source.

    Returns (store, dataset, source). Both objects are created by
    STEWARD, per the pinned contract fixture.
    """
    if audit is None:
        audit = AuditLog()
    store = DataMgmtStore(audit=audit)
    dataset = store.create_dataset(
        "Claims Extract",
        "Nightly extract of claims records",
        STEWARD,
        classification="cui",
        tags=["claims", "nightly"],
        schema=[dict(field) for field in CANONICAL_SCHEMA],
    )
    source = store.register_source(
        "ehr-feed", "api", STEWARD, location="ehr.internal"
    )
    return store, dataset, source
