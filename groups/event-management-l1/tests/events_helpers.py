"""Shared fixtures for the events tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (member), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from events.access import User  # noqa: E402
from events.audit import AuditLog  # noqa: E402
from events.store import EventsStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")

ORGANIZER_REF = "ORG-0001"
ORGANIZER_LABEL = "Agency events office (records label)"
VENDOR_REF_A = "VEN-0001"
VENDOR_REF_B = "VEN-0002"
VENDOR_REF_C = "VEN-0003"
VENDOR_LABEL = "Vendor Co (records label)"

STARTS = "2026-03-10T09:00:00+00:00"
ENDS = "2026-03-10T17:00:00+00:00"
BEFORE = "2026-03-01T00:00:00+00:00"
DURING = "2026-03-10T12:00:00+00:00"
AFTER = "2026-03-20T00:00:00+00:00"
SESS_STARTS = "2026-03-10T10:00:00+00:00"
SESS_ENDS = "2026-03-10T11:00:00+00:00"
SESS_DURING = "2026-03-10T10:30:00+00:00"


def make_store():
    audit = AuditLog()
    return EventsStore(audit=audit), audit


def make_organizer(store, actor=ADMIN):
    return store.create_organizer(actor, ORGANIZER_REF, ORGANIZER_LABEL)


def make_vendors(store, actor=ADMIN):
    a = store.create_vendor(actor, VENDOR_REF_A, VENDOR_LABEL)
    b = store.create_vendor(actor, VENDOR_REF_B, VENDOR_LABEL)
    c = store.create_vendor(actor, VENDOR_REF_C, VENDOR_LABEL)
    return a, b, c


def make_event(store, organizer, actor=ADMIN):
    return store.create_event(actor, organizer["id"],
                              "Spring Vendor Day", "hybrid", STARTS, ENDS)


def make_round(store, event, actor=ADMIN, required_tags=("cloud", "security")):
    return store.create_round(actor, event["id"], list(required_tags))
