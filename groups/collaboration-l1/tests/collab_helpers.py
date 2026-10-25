"""Shared helpers for the Collaboration L1 (Group 10) test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is runnable
with ``PYTHONPATH=src`` from the group directory; these helpers additionally
put ``src/`` (and the tests directory itself) on the path so the tests also
run standalone, mirroring ``analytics_helpers.py`` in the Analytics L2
group.

Canonical fixture (used across the suite): a workspace named ``team-room``
owned by MEMBER (bob, platform role ``member``) with VIEWER (carol,
platform role ``viewer``) added as a second workspace member. ADMIN
(alice, platform role ``admin``) is deliberately *not* a workspace member
— she reaches workspaces through the platform admin role. OUTSIDER (dave,
platform role ``member``) belongs to no fixture workspace, which makes
him the canonical non-member for membership-boundary tests.
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

from collab.access import User  # noqa: E402
from collab.audit import AuditLog  # noqa: E402
from collab.store import CollabStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
OUTSIDER = User("dave", "member")
OUTSIDER_VIEWER = User("erin", "viewer")

# Registry as the HTTP layer / CLI sees it (demo identities per contract).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "dave": "member",
}

WORKSPACE_NAME = "team-room"

# Canonical event window (ISO-8601, UTC).
EVENT_START = "2026-11-02T15:00:00+00:00"
EVENT_END = "2026-11-02T16:00:00+00:00"


def fresh_store(audit=None):
    """A bare CollabStore with no workspaces (for id-sequence tests)."""
    return CollabStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit log + the canonical workspace.

    Returns ``(store, workspace_id)``: a CollabStore with an AuditLog
    attached (the one passed in, or a new one), a workspace owned by
    MEMBER, and VIEWER added as a second member by the owner.
    """
    if audit is None:
        audit = AuditLog()
    store = CollabStore(audit=audit)
    workspace = store.create_workspace(WORKSPACE_NAME, MEMBER)
    store.add_member(workspace["id"], VIEWER.name, MEMBER)
    return store, workspace["id"]


def make_channel(store, workspace_id, name="general", actor=MEMBER):
    """Create a channel in the workspace (default actor: the owner)."""
    return store.create_channel(workspace_id, name, actor)


def post_sample_message(store, workspace_id, channel_id, text="hello team",
                        actor=MEMBER, parent_id=None):
    """Post a message; defaults trace the contract's happy path."""
    return store.post_message(
        workspace_id, channel_id, text, actor, parent_id=parent_id
    )


def share_sample_file(store, workspace_id, name="notes.txt",
                      content="hello files", actor=MEMBER,
                      content_type="text/plain"):
    """Share a text file into the workspace."""
    return store.share_file(
        workspace_id, name, content, actor, content_type=content_type
    )


def create_sample_event(store, workspace_id, title="Team sync",
                        attendees=None, actor=MEMBER, location="",
                        start=EVENT_START, end=EVENT_END):
    """Create an event over the canonical one-hour window."""
    return store.create_event(
        workspace_id, title, start, end, list(attendees or []), actor,
        location=location,
    )


def create_sample_board(store, workspace_id, name="Sprint board",
                        actor=MEMBER):
    """Create a board in the workspace."""
    return store.create_board(workspace_id, name, actor)


def add_sample_card(store, workspace_id, board_id, text="First card",
                    x=10, y=20, actor=MEMBER):
    """Add a positioned text card to a board."""
    return store.add_card(workspace_id, board_id, text, x, y, actor)
