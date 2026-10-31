"""Shared fixtures for the manufacturing test suite.

Builds a fresh store wired to an in-memory audit log, with one
actor per role — alice (admin), bob (operator), carol (viewer) —
and one registered organization. Run with ``PYTHONPATH=src`` so
the ``manufacturing`` package imports.
"""

from manufacturing.access import User
from manufacturing.audit import AuditLog
from manufacturing.store import ManufacturingStore

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")
OUTSIDER = User("mallory", "superuser")


def make_store():
    """Return (store, audit, organization) with one org registered."""
    audit = AuditLog()
    store = ManufacturingStore(audit=audit)
    org = store.create_organization(
        ADMIN, "acme-aerospace", "Acme Aerospace Team")
    return store, audit, org


def make_intent(store, org, actor=OPERATOR, label="Bracket intent",
                statement="Bracket must hold the shear load.",
                author_ref="eng-1"):
    return store.record_intent(actor, org["id"], label, statement,
                               author_ref)


def make_decision(store, org, intent, actor=OPERATOR,
                  label="Bracket decision",
                  statement="Bracket is a machined rib, 6 mm web.",
                  decided_by_ref="eng-2"):
    return store.record_decision(
        actor, org["id"], label, statement, [intent["id"]],
        decided_by_ref)
