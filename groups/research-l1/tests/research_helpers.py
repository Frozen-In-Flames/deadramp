"""Shared helpers for the Research L1 singleton test suite
(carried from the Research L2 build's suite; documentation
re-anchored to this group, fixture unchanged).

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring
``grants_helpers.py`` in the Grant Management L2 group.

Canonical fixture (used across the suite): a data commons named
``gen3-commons`` created by MEMBER (bob, platform role ``member``)
with kind ``commons`` and sponsor reference ``SPONSOR-1``, and an
organization ``ORG-100``. STAFF (erin, platform role ``member``)
is added as a second commons member by ADMIN — she is the
canonical decider, because the fixture's access requests are made
by bob and the decider is never the requester (AC-5). ADMIN
(alice) is deliberately *not* a commons member — she reaches
commons through the platform admin role. OUTSIDER (dave, platform
role ``member``) belongs to no fixture commons. VIEWER (carol,
platform role ``viewer``) holds the read-only platform role.
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

from research.access import User  # noqa: E402
from research.audit import AuditLog  # noqa: E402
from research.store import ResearchStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
STAFF = User("erin", "member")
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

COMMONS_NAME = "gen3-commons"
COMMONS_TITLE = "Gen3 Research Commons"
ORG_REF = "ORG-100"
ORG_LABEL = "Northstar Research Alliance"

# Fixed timestamps. T0 is the canonical grant start; a 30-day grant
# starting at T0 expires at EXPIRES_AT.
T0 = "2026-06-01T00:00:00+00:00"
BEFORE_T0 = "2026-05-15T00:00:00+00:00"
INSIDE_WINDOW = "2026-06-15T00:00:00+00:00"
EXPIRES_AT = "2026-07-01T00:00:00+00:00"
AFTER_EXPIRY = "2026-07-02T00:00:00+00:00"
FUTURE_START = "2026-08-01T00:00:00+00:00"

SHA256_A = "a" * 64
SHA256_B = "0123456789abcdef" * 4


def fresh_store(audit=None):
    """A bare ResearchStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return ResearchStore(audit=audit)


def make_commons(store, actor=MEMBER, **overrides):
    """Create the canonical data commons (or a variant)."""
    kwargs = {
        "name": COMMONS_NAME,
        "title": COMMONS_TITLE,
        "kind": "commons",
        "sponsor_ref": "SPONSOR-1",
    }
    kwargs.update(overrides)
    return store.create_commons(actor, **kwargs)


def make_store(audit=None):
    """Fresh store + canonical commons + canonical organization.

    Returns (store, commons, org). STAFF is a commons member.
    """
    store = fresh_store(audit=audit)
    commons = make_commons(store)
    store.add_member(ADMIN, commons["id"], STAFF.name)
    org = store.create_organization(MEMBER, ORG_REF, ORG_LABEL)
    return store, commons, org


def _commons_id(commons):
    return commons["id"] if isinstance(commons, dict) else commons


def _dataset_id(dataset):
    return dataset["id"] if isinstance(dataset, dict) else dataset


def make_workspace(store, commons, actor=MEMBER, **overrides):
    """Create a workspace inside ``commons`` (a record or its id)."""
    kwargs = {
        "name": "analysis-workspace",
        "purpose": "Workspace for managing and analyzing shared data",
    }
    kwargs.update(overrides)
    return store.create_workspace(actor, _commons_id(commons), **kwargs)


def make_dataset(store, commons, actor=MEMBER, **overrides):
    """Register the canonical controlled dataset (or a variant).

    The record is metadata + checksum only — no content is ever
    supplied to, or stored by, the registry.
    """
    kwargs = {
        "name": "trial-registry",
        "description": "Registry of shared trial metadata",
        "access_tier": "controlled",
        "sha256": SHA256_A,
        "size_bytes": 2048,
    }
    kwargs.update(overrides)
    return store.register_dataset(actor, _commons_id(commons), **kwargs)


def make_access_request(store, dataset, actor=MEMBER, **overrides):
    """Create an access request by ``actor`` (default bob)."""
    kwargs = {
        "purpose": "Access for planned analysis",
        "duration_days": 30,
    }
    kwargs.update(overrides)
    return store.create_access_request(actor, _dataset_id(dataset), **kwargs)


def make_grant(store, commons, dataset=None, decider=STAFF,
               starts_at=T0, duration_days=30, **request_overrides):
    """A decided (approved) request and its grant view.

    The request is made by MEMBER (bob) and decided by STAFF
    (erin) — the decider is never the requester (AC-5). Returns
    the grant view from the decision result.
    """
    if dataset is None:
        dataset = make_dataset(store, commons)
    request = make_access_request(store, dataset,
                                  duration_days=duration_days,
                                  **request_overrides)
    result = store.decide_access_request(
        decider, request["id"], True, note="Approved as reviewed",
        starts_at=starts_at)
    return result["grant"]
