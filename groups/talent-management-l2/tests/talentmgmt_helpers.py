"""Shared helpers for the Talent Management L2 merged-build test suite.

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

from talentmgmt.access import User  # noqa: E402
from talentmgmt.audit import AuditLog  # noqa: E402
from talentmgmt.store import TalentMgmtStore  # noqa: E402

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
ORG_LABEL = "Office of Talent Acquisition"
CANDIDATE_REF = "CAN-REF-001"
CANDIDATE_LABEL = "Candidate One"
CANDIDATE2_REF = "CAN-REF-002"
REQUISITION_REF = "REQ-REF-001"
REQUISITION_TITLE = "Program Analyst"
PIPELINE_REF = "PIP-REF-001"
STAGES = ["Applied", "Screen", "Interview", "Decision"]
PLACEMENT_REF = "PLC-REF-001"
EVENT_REF = "EVT-REF-001"
EVENT_TITLE = "Spring Recruiting Fair"
EVENT_START = "2030-04-01T15:00:00+00:00"


def fresh_store(audit=None):
    """A bare TalentMgmtStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return TalentMgmtStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit + canonical organization.

    Returns (store, audit, org). The organization is created by
    ADMIN; MEMBER and VIEWER are organization members.
    """
    if audit is None:
        audit = AuditLog()
    store = TalentMgmtStore(audit=audit)
    org = store.create_organization(ORG_REF, ORG_LABEL, ADMIN)
    store.add_member(org["id"], MEMBER.name, ADMIN)
    store.add_member(org["id"], VIEWER.name, ADMIN)
    org = store.get_organization(org["id"], ADMIN)
    return store, audit, org


def make_candidate(store, org, actor=MEMBER, **overrides):
    """Register the canonical candidate in ``org``."""
    kwargs = {"candidate_ref": CANDIDATE_REF, "label": CANDIDATE_LABEL}
    kwargs.update(overrides)
    return store.register_candidate(org["id"], actor=actor, **kwargs)


def make_requisition(store, org, actor=MEMBER, **overrides):
    """Create the canonical requisition in ``org``."""
    kwargs = {"requisition_ref": REQUISITION_REF, "title": REQUISITION_TITLE}
    kwargs.update(overrides)
    return store.create_requisition(org["id"], actor=actor, **kwargs)


def make_pipeline(store, org, requisition, actor=MEMBER, **overrides):
    """Create the canonical four-stage pipeline in ``org``."""
    kwargs = {
        "pipeline_ref": PIPELINE_REF,
        "requisition_id": requisition["id"],
        "stages": list(STAGES),
    }
    kwargs.update(overrides)
    return store.create_pipeline(org["id"], actor=actor, **kwargs)


def make_placement(store, org, pipeline, actor=MEMBER, **overrides):
    """Place the canonical candidate into ``pipeline``."""
    kwargs = {"placement_ref": PLACEMENT_REF, "candidate_ref": CANDIDATE_REF}
    kwargs.update(overrides)
    return store.place_candidate(org["id"], pipeline["id"], actor=actor,
                                 **kwargs)


def make_event(store, org, actor=MEMBER, **overrides):
    """Create the canonical in-person recruitment event in ``org``."""
    kwargs = {
        "event_ref": EVENT_REF,
        "title": EVENT_TITLE,
        "kind": "in_person",
        "starts_at": EVENT_START,
    }
    kwargs.update(overrides)
    return store.create_event(org["id"], actor=actor, **kwargs)
