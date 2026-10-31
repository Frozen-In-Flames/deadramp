"""Shared fixtures for the marketsales tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (operator), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marketsales.access import User  # noqa: E402
from marketsales.audit import AuditLog  # noqa: E402
from marketsales.store import MarketSalesStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

ORG_REF = "ORG-0001"
ORG_LABEL = "Agency outreach office (records label)"
OPP_REF = "OPP-REF-0001"
AGENCY_LABEL = "Department of Examples"
TITLE_LABEL = "Widget services IDIQ recompete"
POSTED = "2026-01-05T00:00:00+00:00"
DUE = "2026-03-01T00:00:00+00:00"
LIST_LABEL = "Agency contacts, January load"
SEGMENT_LABEL = "Program managers"
CAMPAIGN_LABEL = "January newsletter"
SCHEDULED_FOR = "2026-01-10T09:00:00+00:00"
OCCURRED = "2026-01-10T10:00:00+00:00"
CONTACT_A = "CONTACT-REF-1"
CONTACT_B = "CONTACT-REF-2"


def make_store():
    audit = AuditLog()
    return MarketSalesStore(audit=audit), audit


def make_org(store, actor=ADMIN):
    return store.create_organization(actor, ORG_REF, ORG_LABEL)


def make_opportunity(store, org, actor=OPERATOR):
    return store.create_opportunity(
        actor, org["id"], OPP_REF, AGENCY_LABEL, TITLE_LABEL,
        POSTED, due_at=DUE, kind_label="IDIQ")


def make_list(store, org, actor=OPERATOR, count=1250):
    return store.create_contact_list(
        actor, org["id"], LIST_LABEL, count, loaded_at="2026-01-02")


def make_segment(store, org, actor=OPERATOR, count=300):
    return store.create_segment(
        actor, org["id"], SEGMENT_LABEL, "role label on loaded list",
        count)


def make_campaign(store, org, actor=OPERATOR, scheduled_for=SCHEDULED_FOR):
    contact_list = make_list(store, org, actor)
    segment = make_segment(store, org, actor)
    campaign = store.create_campaign(
        actor, org["id"], CAMPAIGN_LABEL, segment["id"],
        contact_list["id"], scheduled_for=scheduled_for)
    return campaign, contact_list, segment
