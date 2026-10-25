"""Shared helpers for the Construction L2 merged-build test suite.

Traces to: the contract for Group 19 (Construction L2) -- the suite
is runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, a project transitioned
to active, a prime org (tier 1 participant) and a sub org (tier 2
participant), all created by ADMIN.
ADMIN=alice/admin, OPERATOR=bob/operator, VIEWER=carol/viewer.
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

from construct.access import User  # noqa: E402
from construct.audit import AuditLog  # noqa: E402
from construct.store import ConstructStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare ConstructStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return ConstructStore(audit=audit)


def make_store(audit=None):
    """Fresh store + active project + prime org + sub org.

    The prime org is a tier 1 participant and the sub org a tier 2
    participant of the project. Returns
    (store, project, prime_org, sub_org).
    """
    if audit is None:
        audit = AuditLog()
    store = ConstructStore(audit=audit)
    prime_org = store.create_org(
        "Prime Builders", ADMIN, reference="PRIME-1", attributes={"hq": "tx"}
    )
    sub_org = store.create_org("Sub Trades", ADMIN, reference="SUB-1")
    project = store.create_project("Tower One", ADMIN, location="Dallas")
    store.transition_project(project["id"], ADMIN, "active")
    store.add_participant(project["id"], prime_org["id"], ADMIN, tier=1, role="prime")
    store.add_participant(project["id"], sub_org["id"], ADMIN, tier=2, role="sub")
    project = store.get_project(project["id"], ADMIN)
    return store, project, prime_org, sub_org
