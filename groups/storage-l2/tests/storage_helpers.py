"""Shared fixtures for the storage tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (operator), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from storage.access import User  # noqa: E402
from storage.audit import AuditLog  # noqa: E402
from storage.store import StorageStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

ORG_REF = "ORG-0001"
ORG_LABEL = "Agency records office (records label)"
POLICY_LABEL = "Standard correspondence retention"
RETENTION_DAYS = 30
COLLECTION_LABEL = "Executive correspondence archive"
FORMAT_LABEL = "native"

ARCHIVED = "2024-01-01T00:00:00+00:00"
BEFORE_BOUNDARY = "2024-01-15T00:00:00+00:00"
AT_BOUNDARY = "2024-01-31T00:00:00+00:00"
AFTER_BOUNDARY = "2024-03-01T00:00:00+00:00"


def make_store():
    audit = AuditLog()
    return StorageStore(audit=audit), audit


def make_org(store, actor=ADMIN):
    return store.create_organization(actor, ORG_REF, ORG_LABEL)


def make_policy(store, actor=ADMIN, days=RETENTION_DAYS):
    return store.create_policy(actor, POLICY_LABEL, days)


def make_collection(store, org, policy, actor=ADMIN):
    return store.create_collection(actor, org["id"], COLLECTION_LABEL,
                                   policy["id"], FORMAT_LABEL)


def make_archive(store, actor=ADMIN):
    """org + policy + collection, returned as a triple."""
    org = make_org(store, actor)
    policy = make_policy(store, actor)
    collection = make_collection(store, org, policy, actor)
    return org, policy, collection


def make_message(store, collection, actor=OPERATOR, ref="MSG-REF-0001",
                 custody_id=None):
    return store.archive_message(
        actor, collection["id"], ref, "SENDER-REF-1",
        ["RECIP-REF-1", "RECIP-REF-2"], ARCHIVED, 2048, FORMAT_LABEL,
        custody_id=custody_id)


def make_custody(store, org, collection, actor=OPERATOR):
    return store.create_custody(actor, org["id"], collection["id"],
                                "CUSTODIAN-REF-1", "KEY-LABEL-1")
