"""Shared helpers for the Health & Wellness untiered-set test suite.

Traces to: the contract for the founding group (Health & Wellness
L2), carried whole and re-anchored to tier null -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one program
("Diabetes Care", created by ADMIN since program_write is admin-only)
and one participant registered under the opaque reference "carol"
(created by ADMIN since participant_write is admin-only).
ADMIN=alice/admin, CLINICIAN=bob/clinician, MEMBER=carol/member,
AUDITOR=dana/auditor. Member-scoped records for the MEMBER actor use
the participant whose ``participant_ref`` is "carol" (the actor's own
name).
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

from health.access import User  # noqa: E402
from health.audit import AuditLog  # noqa: E402
from health.store import HealthStore  # noqa: E402

ADMIN = User("alice", "admin")
CLINICIAN = User("bob", "clinician")
MEMBER = User("carol", "member")
AUDITOR = User("dana", "auditor")

USERS = {
    "alice": "admin",
    "bob": "clinician",
    "carol": "member",
    "dana": "auditor",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare HealthStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return HealthStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one program + one participant.

    Returns (store, program, participant) where the participant's
    opaque reference is "carol".
    """
    store = fresh_store(audit=audit)
    program = store.create_program("Diabetes Care", ADMIN, code="DIA-101")
    participant = store.create_participant("carol", ADMIN)
    return store, program, participant
