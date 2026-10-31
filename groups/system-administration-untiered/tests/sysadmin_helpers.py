"""Shared helpers for the System Administration untiered-set
test suite (the founding L2 group's suite, carried).

Traces to: UNION-SPEC.md "Implementation contract" -- the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring
``netmgmt_helpers.py`` in the Network Management L2 group.

Canonical fixture (used across the suite): a customer organization
``AGENCY-1`` created by MEMBER (bob, platform role ``member``).
STAFF (erin, platform role ``member``) is added as a second
organization member by ADMIN -- she is the canonical change
decider, because changes are requested by bob and the decider is
never the requester (AC-5). ADMIN (alice) is deliberately *not* an
organization member -- she reaches organizations through the
platform admin role. OUTSIDER (dave, platform role ``member``)
belongs to no fixture organization. VIEWER (carol, platform role
``viewer``) is added as an organization member in the access tests
to prove read-only members stay read-only.

System / application fixture: managed system ``SYS-OS-1`` of kind
``operating_system`` on opaque platform reference ``PLAT-A``, and
application ``APP-PORTAL`` hosted on it.

Overdue fixture: the canonical service request is due
2026-06-10, so a read clock (``as_of``) of 2026-06-05 derives
``overdue == False`` (before the due date) and 2026-06-15 derives
``overdue == True`` (after it, while the request is unresolved).
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

from sysadmin.access import User  # noqa: E402
from sysadmin.audit import AuditLog  # noqa: E402
from sysadmin.store import SysadminStore  # noqa: E402

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

ORG_REF = "AGENCY-1"
REQUEST_DUE_DATE = "2026-06-10"
AS_OF_BEFORE_DUE = "2026-06-05"
AS_OF_AFTER_DUE = "2026-06-15"


def fresh_store(audit=None):
    """A bare SysadminStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return SysadminStore(audit=audit)


def make_org(store, actor=MEMBER, **overrides):
    """Create the canonical customer organization (or a variant)."""
    kwargs = {"ref": ORG_REF, "label": "Agency One Systems"}
    kwargs.update(overrides)
    return store.create_organization(actor, **kwargs)


def make_store(audit=None):
    """Fresh store + canonical organization.

    Returns (store, org). STAFF is an organization member.
    """
    store = fresh_store(audit=audit)
    org = make_org(store)
    store.add_member(ADMIN, org["id"], STAFF.name)
    return store, org


def make_system(store, org, actor=MEMBER, **overrides):
    """Create the canonical managed system (or a variant)."""
    kwargs = {
        "ref": "SYS-OS-1",
        "label": "Primary OS instance",
        "kind": "operating_system",
        "platform_ref": "PLAT-A",
    }
    kwargs.update(overrides)
    return store.create_system(actor, org["id"], **kwargs)


def make_application(store, org, system, actor=MEMBER, **overrides):
    """Create the canonical application (or a variant)."""
    kwargs = {"ref": "APP-PORTAL", "label": "Agency portal"}
    kwargs.update(overrides)
    return store.create_application(actor, org["id"], system["id"], **kwargs)


def make_request(store, org, system, actor=MEMBER, **overrides):
    """Create the canonical service request (or a variant)."""
    kwargs = {
        "request_kind": "maintenance",
        "summary": "Apply monthly OS maintenance",
        "due_date": REQUEST_DUE_DATE,
    }
    kwargs.update(overrides)
    return store.create_request(actor, org["id"], system["id"], **kwargs)


def make_change(store, org, system, actor=MEMBER, **overrides):
    """Create the canonical change request (or a variant)."""
    kwargs = {"change_kind": "patch", "summary": "Patch SYS-OS-1 kernel"}
    kwargs.update(overrides)
    return store.create_change(actor, org["id"], system["id"], **kwargs)


def make_control(store, org, system, actor=MEMBER, **overrides):
    """Create the canonical control record (or a variant)."""
    kwargs = {
        "control_ref": "SC-7",
        "source": "inherited",
        "note": "Boundary protection from the hosting platform",
    }
    kwargs.update(overrides)
    return store.create_control(actor, org["id"], system["id"], **kwargs)


def make_estate(store, org, actor=MEMBER):
    """Canonical system + application. Returns (system, application)."""
    system = make_system(store, org, actor=actor)
    application = make_application(store, org, system, actor=actor)
    return system, application
