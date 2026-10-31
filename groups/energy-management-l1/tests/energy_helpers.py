"""Shared fixtures for the energy tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (member), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy.access import User  # noqa: E402
from energy.audit import AuditLog  # noqa: E402
from energy.store import EnergyStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")

OWNER_REF = "CUST-0001"
CUSTOMER_LABEL = "Municipal utility (records label)"
PROVIDER_REF_A = "PROV-0001"
PROVIDER_REF_B = "PROV-0002"
PROVIDER_LABEL = "SupplyCo (records label)"

OPENS = "2024-06-01T00:00:00+00:00"
CLOSES = "2024-06-10T00:00:00+00:00"
BEFORE = "2024-05-20T00:00:00+00:00"
IN_WINDOW = "2024-06-05T12:00:00+00:00"
IN_WINDOW_LATE = "2024-06-06T12:00:00+00:00"
AFTER = "2024-06-20T00:00:00+00:00"


def make_store():
    audit = AuditLog()
    return EnergyStore(audit=audit), audit


def make_customer(store, actor=ADMIN):
    return store.create_customer(actor, OWNER_REF, CUSTOMER_LABEL)


def make_providers(store, actor=ADMIN):
    a = store.create_provider(actor, PROVIDER_REF_A, PROVIDER_LABEL)
    b = store.create_provider(actor, PROVIDER_REF_B, PROVIDER_LABEL)
    return a, b


def make_open_auction(store, customer, actor=ADMIN):
    return store.create_auction(actor, customer["id"], "electricity",
                                "ERCOT-North", "kWh", 100000, OPENS, CLOSES)
