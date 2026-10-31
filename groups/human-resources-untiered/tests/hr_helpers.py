"""Shared helpers for the Human Resources untiered-set test suite.

Traces to: the contract carried from Group 21 (Human Resources L2)
and re-anchored to tier null for this untiered set -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one position
("Program Analyst", series "0343", grade "13", created by ADMIN) and
one person (person_ref "carol", kind "employee", created by ADMIN).
ADMIN=alice/admin, SPECIALIST=bob/hr_specialist, EMPLOYEE=carol/
employee, AUDITOR=dana/auditor. Employee-scoped records for the
EMPLOYEE actor use person_ref "carol" (the actor's own name).
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

from hr.access import User  # noqa: E402
from hr.audit import AuditLog  # noqa: E402
from hr.store import HrStore  # noqa: E402

ADMIN = User("alice", "admin")
SPECIALIST = User("bob", "hr_specialist")
EMPLOYEE = User("carol", "employee")
AUDITOR = User("dana", "auditor")

USERS = {
    "alice": "admin",
    "bob": "hr_specialist",
    "carol": "employee",
    "dana": "auditor",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare HrStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return HrStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one position + one person. Returns (store, position, person)."""
    store = fresh_store(audit=audit)
    position = store.create_position(
        "Program Analyst", ADMIN, series="0343", grade="13"
    )
    person = store.create_person("carol", ADMIN, kind="employee")
    return store, position, person
