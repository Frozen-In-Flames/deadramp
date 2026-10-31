"""Shared helpers for the Network Management untiered set's
merged-build test suite (carried from the founding L2 build).

Traces to: UNION-SPEC.md "Implementation contract" -- the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring
``mdm_helpers.py`` in the Mobile Device Management L2 group.

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

Network / device fixture: network ``NET-HQ`` at ``SITE-HQ`` and
device ``DEV-SW-1`` of class ``switching``.

Freshness fixture: the canonical telemetry reading is recorded
2026-06-01T08:00:00+00:00, so a read clock (``as_of``) of
2026-06-01T20:00:00+00:00 derives ``fresh`` (12 hours later, within
the 24-hour window) and 2026-06-03T08:00:00+00:00 derives ``stale``
(48 hours later, outside the window).
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

from netmgmt.access import User  # noqa: E402
from netmgmt.audit import AuditLog  # noqa: E402
from netmgmt.store import NetmgmtStore  # noqa: E402

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
TELEMETRY_RECORDED_UTC = "2026-06-01T08:00:00+00:00"
AS_OF_FRESH = "2026-06-01T20:00:00+00:00"
AS_OF_STALE = "2026-06-03T08:00:00+00:00"


def fresh_store(audit=None):
    """A bare NetmgmtStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return NetmgmtStore(audit=audit)


def make_org(store, actor=MEMBER, **overrides):
    """Create the canonical customer organization (or a variant)."""
    kwargs = {"ref": ORG_REF, "label": "Agency One Networks"}
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


def make_network(store, org, actor=MEMBER, **overrides):
    """Create the canonical network (or a variant)."""
    kwargs = {"ref": "NET-HQ", "label": "HQ network", "site_ref": "SITE-HQ"}
    kwargs.update(overrides)
    return store.create_network(actor, org["id"], **kwargs)


def make_device(store, org, network, actor=MEMBER, **overrides):
    """Create the canonical switching device (or a variant)."""
    kwargs = {
        "ref": "DEV-SW-1",
        "device_class": "switching",
        "model_ref": "MODEL-SW-1",
    }
    kwargs.update(overrides)
    return store.create_device(actor, org["id"], network["id"], **kwargs)


def make_telemetry(store, org, device, actor=MEMBER, **overrides):
    """Record the canonical telemetry reading (or a variant)."""
    kwargs = {
        "metric": "throughput",
        "value": 100,
        "unit": "mbps",
        "recorded_utc": TELEMETRY_RECORDED_UTC,
    }
    kwargs.update(overrides)
    return store.record_telemetry(actor, org["id"], device["id"], **kwargs)


def make_change(store, org, network, actor=MEMBER, **overrides):
    """Create the canonical change request (or a variant)."""
    kwargs = {"change_kind": "update", "summary": "Tune HQ policy"}
    kwargs.update(overrides)
    return store.create_change(actor, org["id"], network["id"], **kwargs)


def make_automation(store, org, actor=MEMBER, **overrides):
    """Register the canonical automation definition (or a variant)."""
    kwargs = {"name": "Nightly review", "steps": ["collect", "review"]}
    kwargs.update(overrides)
    return store.create_automation(actor, org["id"], **kwargs)


def make_alert(store, org, actor=MEMBER, **overrides):
    """Create the canonical alert record (or a variant)."""
    kwargs = {"kind": "general", "message": "Review HQ network"}
    kwargs.update(overrides)
    return store.create_alert(actor, org["id"], **kwargs)


def make_estate(store, org, actor=MEMBER):
    """Canonical network + device. Returns (network, device)."""
    network = make_network(store, org, actor=actor)
    device = make_device(store, org, network, actor=actor)
    return network, device
