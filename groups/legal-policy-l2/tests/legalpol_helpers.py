"""Shared helpers for the Legal & Policy L2 merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring the sibling
groups' helpers.

Canonical fixture: a store with an AuditLog and one agency created
by ADMIN (alice, platform role ``admin`` — agency creation takes
``agency_write``, which only admin holds). MEMBER (bob) and VIEWER
(carol) are added as agency members by ADMIN. MEMBER2 (erin,
platform role ``member``) is a second platform member who is *not*
added unless a test adds her. OUTSIDER (dave, platform role
``member``) belongs to no fixture agency — the membership-boundary
fixture. ADMIN reaches agencies through the platform admin role as
well as through creating this one.
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

from legalpol.access import User  # noqa: E402
from legalpol.audit import AuditLog  # noqa: E402
from legalpol.store import LegalPolStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
MEMBER2 = User("erin", "member")
VIEWER = User("carol", "viewer")
OUTSIDER = User("dave", "member")

# Registry as the HTTP layer / CLI sees it (demo identities per
# contract, plus erin and dave for member-role checks).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "erin": "member",
    "dave": "member",
}

AGENCY_REF = "AGY-REF-001"
AGENCY_LABEL = "Office of Legal Policy"
WORKSPACE_REF = "WSP-REF-001"
WORKSPACE_TITLE = "Rulemaking Workspace"

DOC_CONTENT = b"draft guidance memo, held in the caller's own system"
DOC_SHA256 = hashlib.sha256(DOC_CONTENT).hexdigest()
QUERY_TEXT = "administrative procedure act notice and comment"
QUERY_SHA256 = hashlib.sha256(QUERY_TEXT.encode("utf-8")).hexdigest()
SHA256_A = "a" * 64
SHA256_B = "0123456789abcdef" * 4


def fresh_store(audit=None):
    """A bare LegalPolStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return LegalPolStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit + canonical agency.

    Returns (store, audit, agency). The agency is created by ADMIN;
    MEMBER and VIEWER are agency members.
    """
    if audit is None:
        audit = AuditLog()
    store = LegalPolStore(audit=audit)
    agency = store.create_agency(AGENCY_REF, AGENCY_LABEL, ADMIN)
    store.add_member(agency["id"], MEMBER.name, ADMIN)
    store.add_member(agency["id"], VIEWER.name, ADMIN)
    agency = store.get_agency(agency["id"], ADMIN)
    return store, audit, agency


def make_workspace(store, agency, actor=MEMBER, **overrides):
    """Create the canonical workspace in ``agency``."""
    kwargs = {"workspace_ref": WORKSPACE_REF, "title": WORKSPACE_TITLE}
    kwargs.update(overrides)
    return store.create_workspace(agency["id"], actor=actor, **kwargs)


def make_session(store, agency, workspace, actor=MEMBER, **overrides):
    """Create a canonical (non-sandbox) session in ``workspace``."""
    kwargs = {"session_ref": "SES-REF-001"}
    kwargs.update(overrides)
    return store.create_session(
        agency["id"], workspace["id"], actor=actor, **kwargs)
