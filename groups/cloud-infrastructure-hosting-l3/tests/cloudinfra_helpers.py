"""Shared fixtures for the cloudinfra test suite (not a test module)."""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from cloudinfra.access import User  # noqa: E402
from cloudinfra.audit import AuditLog  # noqa: E402
from cloudinfra.store import CloudInfraStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
AUDITOR = User("dana", "auditor")
OUTSIDER = User("mallory", "member")

ORG_REF = "org-acme"
ORG_LABEL = "Acme Agency"


def make_store():
    audit = AuditLog()
    return CloudInfraStore(audit=audit), audit


def make_org(store, actor=ADMIN):
    """An organization created by ADMIN with MEMBER and VIEWER added."""
    org = store.create_organization(ORG_REF, ORG_LABEL, actor)
    store.add_member(org["id"], MEMBER.name, actor)
    store.add_member(org["id"], VIEWER.name, actor)
    return org
