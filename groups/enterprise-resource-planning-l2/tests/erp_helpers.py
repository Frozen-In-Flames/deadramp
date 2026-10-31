"""Shared fixtures for the erp tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (operator), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from erp.access import User  # noqa: E402
from erp.audit import AuditLog  # noqa: E402
from erp.store import ErpStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

ORG_REF = "ORG-0001"
ORG_LABEL = "Agency headquarters (records label)"
PERSON_REF = "PERSON-0001"
DEPARTMENT_LABEL = "Finance"
ROLE_LABEL = "Accountant"

BALANCED_LINES = [
    {"account_ref": "ACCT-1000", "debit_cents": 12500, "credit_cents": 0},
    {"account_ref": "ACCT-2000", "debit_cents": 0, "credit_cents": 12500},
]
UNBALANCED_LINES = [
    {"account_ref": "ACCT-1000", "debit_cents": 10000, "credit_cents": 0},
    {"account_ref": "ACCT-2000", "debit_cents": 0, "credit_cents": 9000},
]


def make_store():
    audit = AuditLog()
    return ErpStore(audit=audit), audit


def make_org(store, actor=ADMIN):
    return store.create_organization(actor, ORG_REF, ORG_LABEL)


def make_person(store, org, actor=OPERATOR, ref=PERSON_REF):
    return store.create_person(actor, org["id"], ref, DEPARTMENT_LABEL,
                               ROLE_LABEL)


def make_entry(store, org, actor=OPERATOR, ref="JE-0001", lines=None):
    return store.create_ledger_entry(
        actor, org["id"], ref, "Month-end close",
        BALANCED_LINES if lines is None else lines)
