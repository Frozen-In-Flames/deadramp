"""Shared helpers for the Law Enforcement untiered-set test suite.

Traces to: the contract carried whole from the founding group
(Law Enforcement L2) -- the suite is runnable with ``PYTHONPATH=src``
from the group directory; these helpers additionally put ``src/`` on
the path so tests also run standalone. (Only this docstring was
relabeled for the untiered set; the code is the founding helpers
unchanged.)

Canonical fixture: a store with an AuditLog and one matter created by
MEMBER (bob), with VIEWER (carol) added as a matter member.
ADMIN=alice/admin, MEMBER=bob/member, VIEWER=carol/viewer,
OUTSIDER=mallory/member (a platform member who is NOT a matter
member -- the membership-guard fixture).
"""

import hashlib
import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from lawenf.access import User  # noqa: E402
from lawenf.audit import AuditLog  # noqa: E402
from lawenf.store import LawEnfStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
OUTSIDER = User("mallory", "member")

USERS = {"alice": "admin", "bob": "member", "carol": "viewer", "mallory": "member"}
USERS_REGISTRY = USERS

MATTER_REF = "MATTER-REF-001"
DOC_CONTENT = b"motion brief content, filed under seal in the caller's system"
DOC_SHA256 = hashlib.sha256(DOC_CONTENT).hexdigest()
QUERY_TEXT = "qualified immunity certiorari standards"
QUERY_SHA256 = hashlib.sha256(QUERY_TEXT.encode("utf-8")).hexdigest()
NOTE_TEXT = "check the 2024 amendment before relying on this"
NOTE_SHA256 = hashlib.sha256(NOTE_TEXT.encode("utf-8")).hexdigest()


def fresh_store(audit=None):
    """A bare LawEnfStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return LawEnfStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit + one matter (MEMBER's, VIEWER a member).

    Returns (store, audit, matter).
    """
    if audit is None:
        audit = AuditLog()
    store = LawEnfStore(audit=audit)
    matter = store.create_matter(MATTER_REF, MEMBER)
    store.add_member(matter["id"], VIEWER.name, MEMBER)
    return store, audit, matter
