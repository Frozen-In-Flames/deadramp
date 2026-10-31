"""Shared helpers for the CRM untiered set's test suite.

Traces to: the contract for Group 25 (CRM L2), whose suite this is,
carried whole -- the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one account, and one
contact under it (created by ADMIN/OPERATOR).
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

from crm.access import User  # noqa: E402
from crm.audit import AuditLog  # noqa: E402
from crm.store import CrmStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare CrmStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return CrmStore(audit=audit)


def make_store(audit=None):
    """Fresh store + account + contact under it.

    Returns (store, account, contact).
    """
    if audit is None:
        audit = AuditLog()
    store = CrmStore(audit=audit)
    account = store.create_account(
        ADMIN, "ACCT-100", label="Agency Alpha", attributes={"segment": "federal"}
    )
    contact = store.create_contact(
        OPERATOR, account["id"], "PERSON-200", label="Casey (role: liaison)",
        attributes={"channel_pref": "email"},
    )
    return store, account, contact
