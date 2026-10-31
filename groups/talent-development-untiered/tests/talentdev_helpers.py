"""Shared fixtures for the talentdev test suite.

Ensures the package under test is imported from the sibling
``src/`` directory of this repository checkout.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"),
)

from talentdev.access import User  # noqa: E402
from talentdev.audit import AuditLog  # noqa: E402
from talentdev.store import TalentDevStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")


def make_store(with_audit=True):
    audit = AuditLog() if with_audit else None
    store = TalentDevStore(audit=audit)
    return store, audit


def make_org(store, actor=ADMIN, ref="agency-alpha", label="Agency Alpha"):
    return store.create_organization(actor, ref, label)


def make_program(store, actor=ADMIN, org_id=None, label="Leadership Path",
                 kind="behavioral_mindset_development",
                 goal_label="mission-readiness"):
    if org_id is None:
        org_id = make_org(store, actor=actor)["id"]
    return store.create_program(actor, org_id, label, kind,
                                goal_label=goal_label)
