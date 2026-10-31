"""Shared helpers for the Operations Management L1 singleton-build test suite.

Traces to: the contract for Group 52 (Operations Management L1 singleton) -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one person, one
organization, and one project (owned by the organization) with the
person as a member (created by ADMIN).
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

from opsmgmt.access import User  # noqa: E402
from opsmgmt.audit import AuditLog  # noqa: E402
from opsmgmt.store import OpsStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare OpsStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return OpsStore(audit=audit)


def make_store(audit=None):
    """Fresh store + person + organization + project with person as member.

    Returns (store, person, organization, project).
    """
    if audit is None:
        audit = AuditLog()
    store = OpsStore(audit=audit)
    person = store.create_person(
        "Pat Person", ADMIN, reference="EXT-1001", attributes={"team": "ops"}
    )
    organization = store.create_organization(
        "Acme Vendor", OPERATOR, reference="ORG-1001", attributes={"kind": "vendor"}
    )
    project = store.create_project(
        "Alpha Project", OPERATOR, org_id=organization["id"], attributes={"phase": "1"}
    )
    store.add_person_to_project(project["id"], person["id"], OPERATOR)
    # Re-read so the returned project carries the member list.
    project = store.get_project(project["id"], OPERATOR)
    return store, person, organization, project
