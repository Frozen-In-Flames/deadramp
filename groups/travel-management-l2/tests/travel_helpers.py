"""Shared fixtures for the travel test suite.

Demo identities: ADMIN=alice/admin, MEMBER=bob/member,
VIEWER=carol/viewer, DECIDER=dana/member (an organization member who
decides records bob created), OUTSIDER=erin/member (a member-role
user who belongs to no organization).
"""

from travel.access import User
from travel.audit import AuditLog
from travel.store import TravelStore

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
DECIDER = User("dana", "member")
OUTSIDER = User("erin", "member")

ORG_REF = "ORG-100"
TRAVELER_REF = "TRV-100"
AUTHORIZED_CENTS = 500_000
DEPART = "2026-06-10"
RETURN = "2026-06-12"


def fresh_store(audit=None):
    """A bare TravelStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return TravelStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one organization.

    Returns (store, org). ADMIN created the org; MEMBER, VIEWER and
    DECIDER are organization members. OUTSIDER is not.
    """
    store = fresh_store(audit=audit)
    org = store.create_organization(ADMIN, ORG_REF, "Agency One")
    store.add_member(ADMIN, org["id"], MEMBER.name)
    store.add_member(ADMIN, org["id"], VIEWER.name)
    store.add_member(ADMIN, org["id"], DECIDER.name)
    return store, org


def make_traveler(store, org, actor=MEMBER, **overrides):
    kwargs = {"traveler_ref": TRAVELER_REF, "label": "Traveler One"}
    kwargs.update(overrides)
    return store.create_traveler(actor, org["id"], **kwargs)


def make_authorization(store, org, traveler, actor=MEMBER, **overrides):
    kwargs = {
        "destination_label": "Denver, CO",
        "purpose": "Site review",
        "depart_date": DEPART,
        "return_date": RETURN,
        "authorized_cents": AUTHORIZED_CENTS,
    }
    kwargs.update(overrides)
    return store.create_authorization(actor, org["id"], traveler["id"], **kwargs)


def make_approved_authorization(store, org, traveler, **overrides):
    """An authorization created by MEMBER, submitted, approved by DECIDER."""
    auth = make_authorization(store, org, traveler, **overrides)
    store.submit_authorization(MEMBER, auth["id"])
    store.decide_authorization(DECIDER, auth["id"], True, note="Approved")
    return store.get_authorization(MEMBER, auth["id"], as_of=DEPART)


def make_report(store, auth, actor=MEMBER, title="Denver expenses"):
    return store.create_expense_report(actor, auth["id"], title)


def make_report_with_items(store, auth, items=(("lodging", 120_000),
                                               ("meals", 30_000))):
    """A draft report by MEMBER with the given (category, cents) items."""
    report = make_report(store, auth)
    for category, cents in items:
        store.add_expense_item(MEMBER, report["id"], category, cents,
                               "2026-06-10")
    return store.get_expense_report(MEMBER, report["id"])


def make_approved_report(store, auth, items=(("lodging", 120_000),
                                             ("meals", 30_000))):
    """A submitted report approved by DECIDER. Total = item sum."""
    report = make_report_with_items(store, auth, items=items)
    store.submit_expense_report(MEMBER, report["id"])
    store.decide_expense_report(DECIDER, report["id"], True, note="Approved")
    return store.get_expense_report(MEMBER, report["id"])
