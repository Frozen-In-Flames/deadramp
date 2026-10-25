"""Shared helpers for the Communication L1 singleton-build test suite.

Traces to: the contract for Group 37 (Communication L1 singleton) -- the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these helpers
additionally put ``src/`` on the path so tests also run standalone.

Canonical fixture: a store with an AuditLog, one contact (Dana, with an
email address), one group containing that contact, and one enabled
email channel (created by ADMIN, since channel_write is admin-only).
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

from comm.access import User  # noqa: E402
from comm.audit import AuditLog  # noqa: E402
from comm.store import CommStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer"}
# Alias matching other groups' naming.
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare CommStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return CommStore(audit=audit)


def make_store(audit=None):
    """Fresh store + contact + group + enabled email channel.

    Returns (store, contact, group, channel).
    """
    if audit is None:
        audit = AuditLog()
    store = CommStore(audit=audit)
    contact = store.create_contact(
        "Dana Example", {"email": "dana@example.com", "sms": "+1-555-0100"}, OPERATOR
    )
    group = store.create_group("team", OPERATOR)
    store.add_to_group(group["id"], contact["id"], OPERATOR)
    channel = store.create_channel("email", "primary-email", ADMIN, enabled=True)
    return store, contact, group, channel


def compose_simple(store, actor=OPERATOR, **kwargs):
    """Compose a message to the canonical contact via email."""
    # Caller supplies contact via kwargs or defaults are filled by tests;
    # this helper expects contact_ids in kwargs.
    kwargs.setdefault("subject", "Hello")
    kwargs.setdefault("body", "Hello body")
    kwargs.setdefault("channel_kinds", ["email"])
    return store.compose_message(actor, **kwargs)
