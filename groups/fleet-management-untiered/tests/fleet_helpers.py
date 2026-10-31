"""Shared helpers for the Fleet Management untiered set test suite.

Traces to: the contract for the Fleet Management untiered set
(Untiered Set 15; the founding Group 32 suite, carried whole) -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

ADMIN=alice/admin, MANAGER=bob/manager, VIEWER=carol/viewer.
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

from fleet.access import User  # noqa: E402
from fleet.audit import AuditLog  # noqa: E402
from fleet.store import FleetStore  # noqa: E402

ADMIN = User("alice", "admin")
MANAGER = User("bob", "manager")
VIEWER = User("carol", "viewer")

USERS = {
    "alice": "admin",
    "bob": "manager",
    "carol": "viewer",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare FleetStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return FleetStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one vehicle + one operator. Returns (store, vehicle, operator)."""
    store = fresh_store(audit=audit)
    vehicle = store.create_vehicle("Pool Sedan 1", "sedan", ADMIN)
    operator = store.create_operator("OP-REF-001", "license", ADMIN)
    return store, vehicle, operator
