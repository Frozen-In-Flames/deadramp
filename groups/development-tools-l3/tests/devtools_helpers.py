"""Shared helpers for the Development Tools L1 test suite.

Traces to: the contract for Group 17 (Development Tools L1) -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

ADMIN=alice/admin, DEVELOPER=bob/developer, VIEWER=carol/viewer,
AUDITOR=dana/auditor [L3].
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

from devtools.access import User  # noqa: E402
from devtools.audit import AuditLog  # noqa: E402
from devtools.store import DevToolsStore  # noqa: E402

ADMIN = User("alice", "admin")
DEVELOPER = User("bob", "developer")
VIEWER = User("carol", "viewer")
AUDITOR = User("dana", "auditor")

USERS = {
    "alice": "admin",
    "bob": "developer",
    "carol": "viewer",
    "dana": "auditor",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare DevToolsStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return DevToolsStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one project. Returns (store, project)."""
    store = fresh_store(audit=audit)
    project = store.create_project("Widget Service", ADMIN, description="demo")
    return store, project
