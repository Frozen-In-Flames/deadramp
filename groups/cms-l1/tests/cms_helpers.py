"""Shared helpers for the Content Management System L1 test suite.

Traces to: the contract for Group 24 (CMS L1) -- runnable with
``PYTHONPATH=src`` from the group directory; helpers also put ``src/``
on the path so tests run standalone.

Demo users: ADMIN=alice/admin, PUBLISHER=bob/publisher,
EDITOR=carol/editor, AUTHOR=dave/author, VIEWER=erin/viewer.
Canonical fixture: a store with one site ("Main Site", slug
"main-site") created by PUBLISHER and one section ("News", slug
"news") created by EDITOR.
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

from cms.access import User  # noqa: E402
from cms.audit import AuditLog  # noqa: E402
from cms.store import CmsStore  # noqa: E402

ADMIN = User("alice", "admin")
PUBLISHER = User("bob", "publisher")
EDITOR = User("carol", "editor")
AUTHOR = User("dave", "author")
VIEWER = User("erin", "viewer")

USERS = {
    "alice": "admin", "bob": "publisher", "carol": "editor",
    "dave": "author", "erin": "viewer",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare CmsStore (built-in types only)."""
    if audit is None:
        audit = AuditLog()
    return CmsStore(audit=audit)


def make_store(audit=None):
    """Fresh store + canonical site + canonical section.

    Returns (store, site, section).
    """
    if audit is None:
        audit = AuditLog()
    store = CmsStore(audit=audit)
    site = store.create_site(PUBLISHER, "Main Site", "main-site", "Primary site")
    section = store.create_section(EDITOR, site["id"], "News", "news")
    return store, site, section


def make_item(store, site, actor=None, slug="hello-world", title="Hello World",
              type_id="ct-article", body="First body", **kwargs):
    """Create a draft item (default author dave)."""
    return store.create_item(actor or AUTHOR, site["id"], type_id, title, slug,
                             body=body, **kwargs)


def drive_to_approved(store, item, submitter=None, approver=None):
    """Submit (by submitter/author) and approve (by a non-author editor)."""
    store.submit_item(submitter or AUTHOR, item["id"])
    return store.approve_item(approver or EDITOR, item["id"])


def drive_to_published(store, item, publisher=None, **publish_kwargs):
    """Approve then publish an item; returns the published item."""
    drive_to_approved(store, item)
    return store.publish_item(publisher or PUBLISHER, item["id"], **publish_kwargs)
