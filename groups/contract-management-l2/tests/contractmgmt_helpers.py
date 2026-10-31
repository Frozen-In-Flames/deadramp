"""Shared helpers for the Contract Management L2 merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring the sibling
groups' helpers.

Canonical fixture: a store with an AuditLog and one organization
created by ADMIN (alice, platform role ``admin`` — organization
creation takes ``org_write``, which only admin holds). MEMBER (bob)
and VIEWER (carol) are added as organization members by ADMIN.
MEMBER2 (erin, platform role ``member``) is a second platform
member who is *not* added unless a test adds her. OUTSIDER (dave,
platform role ``member``) belongs to no fixture organization — the
membership-boundary fixture. ADMIN reaches organizations through
the platform admin role as well as through creating this one.
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

from contractmgmt.access import User  # noqa: E402
from contractmgmt.audit import AuditLog  # noqa: E402
from contractmgmt.store import ContractMgmtStore  # noqa: E402

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

ORG_REF = "ORG-REF-001"
ORG_LABEL = "Office of Acquisition"
CONTRACT_REF = "CON-REF-001"
CONTRACT_TITLE = "Commercial Services Contract"
COUNTERPARTY_REF = "VENDOR-REF-001"
PARTICIPANT_REF = "PAR-REF-001"
PARTICIPANT_LABEL = "Registered Vendor One"
PARTICIPANT2_REF = "PAR-REF-002"

CEILING = 1_000_000
AWARD = 400_000


def fresh_store(audit=None):
    """A bare ContractMgmtStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return ContractMgmtStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit + canonical organization.

    Returns (store, audit, org). The organization is created by
    ADMIN; MEMBER and VIEWER are organization members.
    """
    if audit is None:
        audit = AuditLog()
    store = ContractMgmtStore(audit=audit)
    org = store.create_organization(ORG_REF, ORG_LABEL, ADMIN)
    store.add_member(org["id"], MEMBER.name, ADMIN)
    store.add_member(org["id"], VIEWER.name, ADMIN)
    org = store.get_organization(org["id"], ADMIN)
    return store, audit, org


def make_contract(store, org, actor=MEMBER, **overrides):
    """Create the canonical contract in ``org``."""
    kwargs = {
        "contract_ref": CONTRACT_REF,
        "title": CONTRACT_TITLE,
        "counterparty_ref": COUNTERPARTY_REF,
        "ceiling_cents": CEILING,
        "award_cents": AWARD,
    }
    kwargs.update(overrides)
    return store.create_contract(org["id"], actor=actor, **kwargs)


def make_participant(store, actor=MEMBER, **overrides):
    """Register the canonical participant."""
    kwargs = {"participant_ref": PARTICIPANT_REF, "label": PARTICIPANT_LABEL}
    kwargs.update(overrides)
    return store.register_participant(actor=actor, **kwargs)


def make_opportunity(store, org, actor=MEMBER, **overrides):
    """Create a canonical public eRFX opportunity in ``org``."""
    kwargs = {
        "opportunity_ref": "OPP-REF-001",
        "title": "Office Supplies eRFX",
        "kind": "erfx",
    }
    kwargs.update(overrides)
    return store.create_opportunity(org["id"], actor=actor, **kwargs)
