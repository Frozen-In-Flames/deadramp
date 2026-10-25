"""Shared helpers for the Contact Center L2 merged-build test suite.

Traces to: the contract for Group 15 (Contact Center L2) -- the suite
is runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one agent, one contact,
and one queue with the agent in it (created by ADMIN).
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

from contact.access import User  # noqa: E402
from contact.audit import AuditLog  # noqa: E402
from contact.store import ContactStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare ContactStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return ContactStore(audit=audit)


def make_store(audit=None):
    """Fresh store + agent + contact + queue with the agent in it.

    Returns (store, agent, contact, queue).
    """
    if audit is None:
        audit = AuditLog()
    store = ContactStore(audit=audit)
    agent = store.create_agent(
        "Dana Agent", ADMIN, skills=["billing"], attributes={"team": "support"}
    )
    contact = store.create_contact(
        "Casey Citizen", OPERATOR, reference="EXT-1001", attributes={"lang": "en"}
    )
    queue = store.create_queue("support", OPERATOR)
    store.add_agent_to_queue(queue["id"], agent["id"], OPERATOR)
    return store, agent, contact, queue
