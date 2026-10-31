"""Shared helpers for the Mobile Device Management (MDM) L2
merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring
``grants_helpers.py`` in the Grant Management L2 group.

Canonical fixture (used across the suite): a customer organization
``AGENCY-1`` created by MEMBER (bob, platform role ``member``).
STAFF (erin, platform role ``member``) is added as a second
organization member by ADMIN — she is the canonical order decider,
because orders are requested by bob and the decider is never the
requester (AC-5). ADMIN (alice) is deliberately *not* an
organization member — she reaches organizations through the
platform admin role. OUTSIDER (dave, platform role ``member``)
belongs to no fixture organization. VIEWER (carol, platform role
``viewer``) is added as an organization member in the access tests
to prove read-only members stay read-only.

Money fixture: the canonical budget is 1,000,000 cents for period
2026-06; the canonical obligations are 300,000 obligated and
200,000 spent, so derived availability is 500,000 cents.
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

from mdm.access import User  # noqa: E402
from mdm.audit import AuditLog  # noqa: E402
from mdm.store import MdmStore  # noqa: E402

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
BUDGET_CENTS = 1_000_000
BUDGET_PERIOD = "2026-06"
OBLIGATED_CENTS = 300_000
SPENT_CENTS = 200_000
AVAILABLE_CENTS = BUDGET_CENTS - OBLIGATED_CENTS - SPENT_CENTS


def fresh_store(audit=None):
    """A bare MdmStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return MdmStore(audit=audit)


def make_org(store, actor=MEMBER, **overrides):
    """Create the canonical customer organization (or a variant)."""
    kwargs = {"ref": ORG_REF, "label": "Agency One Telecom"}
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


def make_inventory(store, org, actor=MEMBER, **overrides):
    """Create the canonical wireline inventory item (or a variant)."""
    kwargs = {
        "ref": "SVC-100",
        "service_kind": "wireline",
        "label": "HQ voice circuit",
        "plan_ref": "PLAN-VOICE-1",
        "monthly_recurring_cents": 50_000,
    }
    kwargs.update(overrides)
    return store.create_inventory_item(actor, org["id"], **kwargs)


def make_contract(store, org, actor=MEMBER, **overrides):
    """Create the canonical contract (or a variant)."""
    kwargs = {
        "ref": "CON-1",
        "label": "Master telecom agreement",
        "starts_on": "2026-01-01",
        "ends_on": "2026-12-31",
    }
    kwargs.update(overrides)
    return store.create_contract(actor, org["id"], **kwargs)


def make_bill(store, org, contract, actor=MEMBER, **overrides):
    """Create the canonical bill (or a variant)."""
    kwargs = {"period": "2026-06", "stated_cents": 50_000}
    kwargs.update(overrides)
    return store.create_bill(actor, org["id"], contract["id"], **kwargs)


def make_budget(store, org, actor=MEMBER, **overrides):
    """Create the canonical budget (or a variant), no obligations."""
    kwargs = {"period": BUDGET_PERIOD, "budget_cents": BUDGET_CENTS}
    kwargs.update(overrides)
    return store.create_budget(actor, org["id"], **kwargs)


def make_funded_budget(store, org, actor=MEMBER):
    """Canonical budget plus the canonical obligations.

    Returns the budget view: obligated 300,000, spent 200,000,
    available 500,000.
    """
    budget = make_budget(store, org, actor=actor)
    store.record_obligation(actor, budget["id"], "obligated", OBLIGATED_CENTS)
    store.record_obligation(actor, budget["id"], "spent", SPENT_CENTS)
    return store.get_budget(actor, budget["id"])
