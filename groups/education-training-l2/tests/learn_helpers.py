"""Shared helpers for the Education & Training L2 merged-build test suite.

Traces to: the contract for Group 13 (Education & Training L2) -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog and one course
("Safety Basics", created by ADMIN since catalog_write is admin-only).
ADMIN=alice/admin, INSTRUCTOR=bob/instructor, LEARNER=carol/learner,
AUDITOR=dana/auditor. Learner-scoped records for the LEARNER actor use
learner_id "carol" (the actor's own name).
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

from learn.access import User  # noqa: E402
from learn.audit import AuditLog  # noqa: E402
from learn.store import LearnStore  # noqa: E402

ADMIN = User("alice", "admin")
INSTRUCTOR = User("bob", "instructor")
LEARNER = User("carol", "learner")
AUDITOR = User("dana", "auditor")

USERS = {
    "alice": "admin",
    "bob": "instructor",
    "carol": "learner",
    "dana": "auditor",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare LearnStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return LearnStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one course. Returns (store, course)."""
    store = fresh_store(audit=audit)
    course = store.create_course("Safety Basics", ADMIN, code="SAFE-101")
    return store, course
